#!/usr/bin/env python3
"""Review input provenance and advance one local weekly-report task."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

from check_inputs import ensure_safe_evidence_path, load_contract

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def task_reference(path, task_path):
    return Path(os.path.relpath(Path(path).resolve(), Path(task_path).resolve().parent)).as_posix()


def review_reference(path, review_path):
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        return "relative:" + Path(os.path.relpath(resolved, Path(review_path).resolve().parent)).as_posix()
    return "project:" + relative.as_posix()


def resolve_task_reference(reference, task_path):
    path = Path(reference)
    if path.is_absolute():
        return path
    task_relative = Path(task_path).resolve().parent / path
    if task_relative.exists():
        return task_relative
    project_relative = PROJECT_ROOT / path
    if project_relative.exists():
        return project_relative
    return task_relative


def resolve_review_reference(reference, review_path):
    if reference.startswith("project:"):
        return PROJECT_ROOT / reference[len("project:"):]
    if reference.startswith("relative:"):
        return Path(review_path).resolve().parent / reference[len("relative:"):]
    path = Path(reference)
    if path.is_absolute():
        return path
    review_relative = Path(review_path).resolve().parent / path
    if review_relative.exists():
        return review_relative
    project_relative = PROJECT_ROOT / path
    if project_relative.exists():
        return project_relative
    return path


def canonicalize_review_references(review, review_path):
    normalized = dict(review)
    for key in ("contract", "input_dir"):
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = review_reference(
                resolve_review_reference(value, review_path), review_path,
            )
    manifest = normalized.get("approval_manifest")
    if isinstance(manifest, str):
        normalized["approval_manifest"] = str(
            resolve_review_reference(manifest, review_path)
        )
    return normalized


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
    except (OSError, UnicodeError, ValueError):
        errors.append("evidence is unavailable or invalid")
        return None, None
    if not isinstance(evidence, dict):
        errors.append("evidence must be a JSON object")
        return None, sha256(content)
    return evidence, sha256(content)


def regenerated_evidence(period, contract_path, input_dir, errors, manifest_path=None):
    with tempfile.TemporaryDirectory() as temp_dir:
        out = Path(temp_dir) / "evidence.json"
        command = [
            sys.executable, str(Path(__file__).with_name("check_inputs.py")),
            "--period", period, "--contract", str(contract_path),
            "--input-dir", str(input_dir), "--out", str(out),
        ]
        if manifest_path is not None:
            command.extend(("--approval-manifest", str(manifest_path)))
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode not in (0, 2) or not out.is_file():
            errors.append("deterministic validation could not reproduce evidence")
            return None
        return json.loads(out.read_text(encoding="utf-8"))


def regular_file_hash(path):
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            return None
        return sha256(path.read_bytes())
    except OSError:
        return None


def review_run(task, contract_path, input_dir, evidence_path, manifest_path=None, review_path=None):
    errors = []
    # Keep symlink components visible to preflight; resolve only lexically to
    # make review links stable across later verify invocations.
    contract_path = contract_path.absolute()
    input_dir = input_dir.absolute()
    if manifest_path is not None:
        manifest_path = manifest_path.absolute()
    evidence, evidence_hash = read_evidence(evidence_path, errors)
    try:
        contract, _, _, contract_hash = load_contract(contract_path)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        contract = None
        contract_hash = None
        errors.append("contract is unavailable or invalid")

    run_mode = (
        "simulation" if contract is not None and contract.get("simulation_only") is True
        else "real" if contract is not None else None
    )
    manifest_hash = (
        regular_file_hash(manifest_path)
        if run_mode == "real" and manifest_path is not None else None
    )
    if run_mode == "simulation" and manifest_path is not None:
        errors.append("simulation runs must not use an approval manifest")

    sources = []
    regenerated = None
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
            evidence_errors = None
        if evidence.get("status") == "blocked":
            errors.append("input validation blocked")
        elif evidence_errors:
            errors.append("evidence status pass contradicts nonempty errors")
        if evidence.get("status") == "pass" and not isinstance(evidence.get("metrics"), dict):
            errors.append("evidence pass requires metrics")

    if contract is not None and evidence is not None:
        regenerated = regenerated_evidence(
            task["period"], contract_path, input_dir, errors, manifest_path,
        )
        if evidence != regenerated:
            errors.append("evidence differs from deterministic validation")
        if isinstance(regenerated, dict) and regenerated.get("status") == "blocked":
            validation_errors = regenerated.get("errors")
            if isinstance(validation_errors, list) and all(isinstance(item, str) for item in validation_errors):
                errors.extend("validation: " + item for item in validation_errors)
            else:
                errors.append("deterministic validation returned invalid diagnostics")
        if (
            run_mode == "real"
            and evidence.get("status") == "pass"
            and evidence.get("approval_manifest_sha256") != manifest_hash
        ):
            errors.append("approval manifest fingerprint mismatch")
        if evidence.get("contract_version") != contract["contract_version"]:
            errors.append("contract version differs from evidence")
        if evidence.get("contract_sha256") != contract_hash:
            errors.append("contract fingerprint mismatch")

        recorded = {}
        current = {}
        inputs = evidence.get("inputs")
        if not isinstance(inputs, list):
            errors.append("evidence inputs must be a list")
            inputs = []
        current_inputs = regenerated.get("inputs") if isinstance(regenerated, dict) else []
        if not isinstance(current_inputs, list):
            current_inputs = []
        for collection, destination, description in (
            (inputs, recorded, "evidence"),
            (current_inputs, current, "deterministic validation"),
        ):
            for item in collection:
                if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                    if description == "evidence":
                        errors.append("evidence contains an invalid input entry")
                    continue
                if item["path"] in destination:
                    if description == "evidence":
                        errors.append("evidence repeats a source entry")
                    continue
                destination[item["path"]] = item.get("sha256")

        expected_names = {source["file"] for source in contract["sources"]}
        if set(recorded) - expected_names:
            errors.append("evidence contains an unexpected source entry")
        # Only hashes emitted by deterministic preflight are used as observed
        # fingerprints. This avoids reopening input files outside that gate.
        for source in contract["sources"]:
            name = source["file"]
            expected_hash = recorded.get(name)
            observed_hash = current.get(name)
            if expected_hash is None and observed_hash is None:
                continue
            if expected_hash is None:
                errors.append("{}: missing fingerprint in evidence".format(name))
            elif observed_hash is None:
                errors.append("{}: missing source during review".format(name))
            elif expected_hash != observed_hash:
                errors.append("{}: fingerprint mismatch".format(name))
            sources.append({
                "path": name,
                "expected_sha256": expected_hash,
                "observed_sha256": observed_hash,
                "status": "pass" if expected_hash is not None and expected_hash == observed_hash else "blocked",
            })

    review_path = review_path or (PROJECT_ROOT / "runs" / "source-review.json")
    result = {
        "schema_version": 1,
        "task_id": task["id"],
        "period": task["period"],
        "status": "blocked" if errors else "pass",
        "run_mode": run_mode,
        "approval_manifest": (
            str(manifest_path)
            if run_mode == "real" and manifest_path is not None else None
        ),
        "approval_manifest_sha256": manifest_hash,
        "contract": review_reference(contract_path, review_path),
        "contract_version": contract["contract_version"] if contract is not None else None,
        "contract_sha256": contract_hash,
        "input_dir": review_reference(input_dir, review_path),
        "evidence_sha256": evidence_hash,
        "sources": sources,
        "errors": errors,
    }
    return result


def finalize_task(args):
    project_root = Path(__file__).resolve().parent.parent
    artifact_paths = (args.task, args.evidence, args.review)
    for path in artifact_paths:
        ensure_safe_evidence_path(
            path,
            args.input_dir,
            args.contract,
            args.approval_manifest,
            project_root,
            artifact_label="source audit artifact",
        )
    for index, path in enumerate(artifact_paths):
        for other in artifact_paths[index + 1:]:
            try:
                overlaps = path.resolve(strict=False) == other.resolve(strict=False)
                if not overlaps and path.exists() and other.exists():
                    overlaps = os.path.samefile(path, other)
            except (OSError, RuntimeError, ValueError):
                raise ValueError("task, evidence, and review paths must be distinct")
            if overlaps:
                raise ValueError("task, evidence, and review paths must be distinct")

    task = read_task(args.task)
    if task["status"] != "working":
        raise ValueError("task is not working; finalized tasks are immutable")

    try:
        contract, _, _, _ = load_contract(args.contract)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        contract = None
    if contract is not None and contract.get("simulation_only") is True and args.approval_manifest is not None:
        raise ValueError("simulation runs must not use an approval manifest")

    result = review_run(
        task, args.contract, args.input_dir, args.evidence,
        args.approval_manifest, args.review,
    )
    content = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    args.review.parent.mkdir(parents=True, exist_ok=True)
    with args.review.open("xb") as stream:
        stream.write(content)

    links = {
        "evidence": task_reference(args.evidence, args.task),
        "evidence_sha256": result["evidence_sha256"] or "missing",
        "review": task_reference(args.review, args.task),
        "review_sha256": sha256(content),
        "contract_version": result["contract_version"] or "unknown",
        "contract_sha256": result["contract_sha256"] or "missing",
        "run_mode": result["run_mode"] or "unknown",
        "approval_manifest_sha256": result["approval_manifest_sha256"] or "none",
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
    review_path = resolve_task_reference(task["review"], args.task)
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
        if resolve_task_reference(task["evidence"], args.task).exists() or review.get("evidence_sha256") is not None:
            raise ValueError("evidence fingerprint mismatch")
    else:
        try:
            evidence_hash = sha256(resolve_task_reference(task["evidence"], args.task).read_bytes())
        except OSError:
            raise ValueError("evidence fingerprint mismatch")
        if evidence_hash != task["evidence_sha256"] or evidence_hash != review.get("evidence_sha256"):
            raise ValueError("evidence fingerprint mismatch")
    if task.get("contract_sha256") != "missing":
        try:
            contract_path = resolve_review_reference(review["contract"], review_path)
            contract_hash = sha256(contract_path.read_bytes())
        except OSError:
            raise ValueError("contract fingerprint mismatch")
        if contract_hash != task["contract_sha256"] or contract_hash != review.get("contract_sha256"):
            raise ValueError("contract fingerprint mismatch")

    # Older simulation tasks predate approval-preflight fields. They remain
    # verifiable only through the explicitly synthetic contract and path gate.
    if "run_mode" not in task and "run_mode" not in review:
        contract_path = resolve_review_reference(review["contract"], review_path)
        input_dir = resolve_review_reference(review["input_dir"], review_path)
        evidence_path = resolve_task_reference(task["evidence"], args.task)
        contract, _, _, _ = load_contract(contract_path)
        if contract.get("simulation_only") is not True:
            raise ValueError("legacy task is not explicitly simulation-only")
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        current = regenerated_evidence(
            task["period"], contract_path, input_dir, [],
        )
        if isinstance(current, dict):
            current.pop("run_mode", None)
            current.pop("approval_manifest_sha256", None)
        if evidence != current:
            raise ValueError("legacy evidence differs from deterministic validation")
        current_hashes = {
            item.get("path"): item.get("sha256")
            for item in current.get("inputs", []) if isinstance(item, dict)
        }
        for source in review.get("sources", []):
            if current_hashes.get(source.get("path")) != source.get("observed_sha256"):
                raise ValueError("{}: source fingerprint changed since review".format(source.get("path")))
    elif task.get("run_mode") == "unknown" and review.get("run_mode") is None:
        if (
            task.get("approval_manifest_sha256") != "none"
            or review.get("approval_manifest") is not None
            or review.get("approval_manifest_sha256") is not None
        ):
            raise ValueError("task run mode contradicts review")
        fresh_review = review_run(
            task,
            resolve_review_reference(review["contract"], review_path),
            resolve_review_reference(review["input_dir"], review_path),
            resolve_task_reference(task["evidence"], args.task),
            None,
            review_path,
        )
        if fresh_review != canonicalize_review_references(review, review_path):
            raise ValueError("source review differs from deterministic validation")
    else:
        if task.get("run_mode") not in ("real", "simulation") or review.get("run_mode") != task.get("run_mode"):
            raise ValueError("task run mode contradicts review")
        expected_manifest_hash = task.get("approval_manifest_sha256")
        review_manifest_hash = review.get("approval_manifest_sha256")
        if expected_manifest_hash != (review_manifest_hash or "none"):
            raise ValueError("approval manifest fingerprint mismatch")
        manifest_path = (
            resolve_review_reference(review["approval_manifest"], review_path)
            if review.get("approval_manifest") is not None else None
        )
        if task["run_mode"] == "simulation":
            if manifest_path is not None or review_manifest_hash is not None or expected_manifest_hash != "none":
                raise ValueError("simulation task contains approval manifest metadata")
        elif manifest_path is not None:
            if regular_file_hash(Path(manifest_path)) != review_manifest_hash:
                raise ValueError("approval manifest fingerprint mismatch")
        elif review_manifest_hash is not None:
            raise ValueError("approval manifest fingerprint mismatch")

        fresh_review = review_run(
            task,
            resolve_review_reference(review["contract"], review_path),
            resolve_review_reference(review["input_dir"], review_path),
            resolve_task_reference(task["evidence"], args.task),
            manifest_path,
            review_path,
        )
        if fresh_review != canonicalize_review_references(review, review_path):
            changed = [
                error for error in fresh_review.get("errors", [])
                if error.endswith("fingerprint mismatch") or error.endswith("missing source during review")
            ]
            raise ValueError(changed[0] if changed else "source review differs from deterministic validation")
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
    finish.add_argument("--approval-manifest", type=Path)
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
