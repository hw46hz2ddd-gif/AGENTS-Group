#!/usr/bin/env python3
"""Review input provenance and advance one local weekly-report task."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from check_inputs import load_contract


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def task_text(task_id, period, status, links=None, errors=None):
    fields = {"id": task_id, "period": period, "status": status}
    fields.update(links or {})
    lines = ["---"] + ["{}: {}".format(key, value) for key, value in fields.items()] + [
        "---", "", "# Source audit: {}".format(task_id), "", "## Findings", "",
    ]
    if errors:
        lines.extend("- {}".format(error.replace("\n", " ")) for error in errors)
    elif status == "working":
        lines.append("- Awaiting input evidence and source review.")
    else:
        lines.append("- Input evidence and all source fingerprints passed review.")
    return "\n".join(lines) + "\n"


def read_task(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("task has no frontmatter")
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        if ": " not in line:
            raise ValueError("invalid task field")
        key, value = line.split(": ", 1)
        if key in fields:
            raise ValueError("duplicate task field " + key)
        fields[key] = value
    if not fields.get("id") or not fields.get("period") or not fields.get("status"):
        raise ValueError("task is missing id, period, or status")
    return fields


def start_task(args):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.id):
        raise ValueError("id must contain only letters, digits, dots, hyphens, or underscores")
    if not re.fullmatch(r"\d{4}-W\d{2}", args.period):
        raise ValueError("period must look like YYYY-WNN")
    args.task.parent.mkdir(parents=True, exist_ok=True)
    with args.task.open("x", encoding="utf-8") as stream:
        stream.write(task_text(args.id, args.period, "working"))
    return 0


def read_evidence(path, errors):
    try:
        content = path.read_bytes()
        evidence = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        errors.append("evidence {}: {}".format(path, error))
        return None, None
    if not isinstance(evidence, dict):
        errors.append("evidence must be a JSON object")
        return None, sha256(content)
    return evidence, sha256(content)


def regenerated_evidence(period, contract_path, input_dir, errors):
    with tempfile.TemporaryDirectory() as temp_dir:
        out = Path(temp_dir) / "evidence.json"
        command = [
            sys.executable, str(Path(__file__).with_name("check_inputs.py")),
            "--period", period, "--contract", str(contract_path),
            "--input-dir", str(input_dir), "--out", str(out),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode not in (0, 2) or not out.is_file():
            errors.append("deterministic validation could not reproduce evidence: {}".format(completed.stderr.strip()))
            return None
        return json.loads(out.read_text(encoding="utf-8"))


def review_run(task, contract_path, input_dir, evidence_path):
    errors = []
    evidence, evidence_hash = read_evidence(evidence_path, errors)
    try:
        contract, _, _, contract_hash = load_contract(contract_path)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as error:
        contract = None
        contract_hash = None
        errors.append("contract {}: {}".format(contract_path, error))

    sources = []
    if evidence is not None:
        if evidence.get("schema_version") != 1:
            errors.append("evidence schema_version must be 1")
        if evidence.get("period") != task["period"]:
            errors.append("evidence period differs from task period")
        if evidence.get("status") not in ("pass", "blocked"):
            errors.append("evidence status must be pass or blocked")
        evidence_errors = evidence.get("errors")
        if not isinstance(evidence_errors, list) or not all(isinstance(item, str) for item in evidence_errors):
            errors.append("evidence errors must be a list of strings")
            evidence_errors = []
        if evidence.get("status") == "blocked":
            errors.append("input validation blocked")
            errors.extend("evidence: " + item for item in evidence_errors)
        elif evidence_errors:
            errors.append("evidence status pass contradicts nonempty errors")
        if evidence.get("status") == "pass" and not isinstance(evidence.get("metrics"), dict):
            errors.append("evidence pass requires metrics")

    if contract is not None and evidence is not None:
        if evidence != regenerated_evidence(task["period"], contract_path, input_dir, errors):
            errors.append("evidence differs from deterministic validation")
        if evidence.get("contract_version") != contract["contract_version"]:
            errors.append("contract version differs from evidence")
        if evidence.get("contract_sha256") != contract_hash:
            errors.append("contract fingerprint mismatch")

        recorded = {}
        inputs = evidence.get("inputs")
        if not isinstance(inputs, list):
            errors.append("evidence inputs must be a list")
            inputs = []
        for item in inputs:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                errors.append("evidence contains an invalid input entry")
                continue
            if item["path"] in recorded:
                errors.append("evidence repeats source " + item["path"])
            recorded[item["path"]] = item.get("sha256")

        expected_names = {source["file"] for source in contract["sources"]}
        for extra in sorted(set(recorded) - expected_names):
            errors.append("evidence contains unexpected source " + extra)
        for source in contract["sources"]:
            name = source["file"]
            expected_hash = recorded.get(name)
            source_path = input_dir / name
            try:
                observed_hash = sha256(source_path.read_bytes())
            except OSError:
                observed_hash = None
            if observed_hash is None:
                errors.append("{}: missing source during review".format(name))
            if expected_hash is None:
                errors.append("{}: missing fingerprint in evidence".format(name))
            elif observed_hash is not None and expected_hash != observed_hash:
                errors.append("{}: fingerprint mismatch".format(name))
            sources.append({
                "path": name,
                "expected_sha256": expected_hash,
                "observed_sha256": observed_hash,
                "status": "pass" if expected_hash is not None and expected_hash == observed_hash else "blocked",
            })

    result = {
        "schema_version": 1,
        "task_id": task["id"],
        "period": task["period"],
        "status": "blocked" if errors else "pass",
        "contract": str(contract_path),
        "contract_version": contract["contract_version"] if contract is not None else None,
        "contract_sha256": contract_hash,
        "input_dir": str(input_dir),
        "evidence_sha256": evidence_hash,
        "sources": sources,
        "errors": errors,
    }
    return result


def finalize_task(args):
    task = read_task(args.task)
    if task["status"] != "working":
        raise ValueError("task is not working; finalized tasks are immutable")
    if args.review.resolve() in (args.task.resolve(), args.evidence.resolve()):
        raise ValueError("review path must differ from task and evidence paths")

    result = review_run(task, args.contract, args.input_dir, args.evidence)
    content = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    args.review.parent.mkdir(parents=True, exist_ok=True)
    with args.review.open("xb") as stream:
        stream.write(content)

    links = {
        "evidence": str(args.evidence),
        "evidence_sha256": result["evidence_sha256"] or "missing",
        "review": str(args.review),
        "review_sha256": sha256(content),
        "contract_version": result["contract_version"] or "unknown",
        "contract_sha256": result["contract_sha256"] or "missing",
    }
    args.task.write_text(
        task_text(task["id"], task["period"], "blocked" if result["errors"] else "ready", links, result["errors"]),
        encoding="utf-8",
    )
    return 2 if result["errors"] else 0


def verify_task(args):
    task = read_task(args.task)
    if task["status"] not in ("ready", "blocked"):
        raise ValueError("task has no finalized source review")
    review_path = Path(task["review"])
    review_bytes = review_path.read_bytes()
    if sha256(review_bytes) != task["review_sha256"]:
        raise ValueError("review fingerprint mismatch")
    review = json.loads(review_bytes.decode("utf-8"))
    if not isinstance(review, dict):
        raise ValueError("review must be a JSON object")
    if review.get("task_id") != task["id"] or review.get("period") != task["period"]:
        raise ValueError("review task identity mismatch")
    expected_status = "pass" if task["status"] == "ready" else "blocked"
    if review.get("status") != expected_status:
        raise ValueError("task status contradicts review status")
    if task.get("evidence_sha256") == "missing":
        if Path(task["evidence"]).exists() or review.get("evidence_sha256") is not None:
            raise ValueError("evidence fingerprint mismatch")
    else:
        try:
            evidence_hash = sha256(Path(task["evidence"]).read_bytes())
        except OSError:
            raise ValueError("evidence fingerprint mismatch")
        if evidence_hash != task["evidence_sha256"] or evidence_hash != review.get("evidence_sha256"):
            raise ValueError("evidence fingerprint mismatch")
    if task.get("contract_sha256") != "missing":
        try:
            contract_hash = sha256(Path(review["contract"]).read_bytes())
        except OSError:
            raise ValueError("contract fingerprint mismatch")
        if contract_hash != task["contract_sha256"] or contract_hash != review.get("contract_sha256"):
            raise ValueError("contract fingerprint mismatch")
    for source in review.get("sources", []):
        try:
            observed_hash = sha256((Path(review["input_dir"]) / source["path"]).read_bytes())
        except OSError:
            observed_hash = None
        if observed_hash != source.get("observed_sha256"):
            raise ValueError("{}: source fingerprint changed since review".format(source["path"]))
    print("{}: {} (artifact links verified)".format(task["id"], task["status"]))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="create a working task record")
    start.add_argument("--task", type=Path, required=True)
    start.add_argument("--id", required=True)
    start.add_argument("--period", required=True)
    finish = commands.add_parser("finalize", help="review evidence and sources, then update the task")
    finish.add_argument("--task", type=Path, required=True)
    finish.add_argument("--contract", type=Path, required=True)
    finish.add_argument("--input-dir", type=Path, required=True)
    finish.add_argument("--evidence", type=Path, required=True)
    finish.add_argument("--review", type=Path, required=True)
    verify = commands.add_parser("verify", help="check a final task against its local artifacts")
    verify.add_argument("--task", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "start":
            return start_task(args)
        if args.command == "finalize":
            return finalize_task(args)
        return verify_task(args)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        print("source-audit: {}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
