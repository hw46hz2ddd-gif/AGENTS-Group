#!/usr/bin/env python3
"""Independently check a synthetic weekly draft against its evidence."""

import argparse
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

from check_inputs import load_contract
from report_task import task_text
from source_audit import read_task, sha256, verify_task


def draft_fields(lines, errors):
    fields = {}
    for number, line in enumerate(lines, start=1):
        for name in ("来源任务", "证据文件", "证据 SHA-256", "口径版本", "口径 SHA-256", "上周产量", "产量环比"):
            prefix = name + "："
            if line.startswith(prefix):
                if name in fields:
                    errors.append("line {}: repeated {}".format(number, name))
                fields[name] = (line[len(prefix):], number)
    return fields


def metric_rows(lines, errors):
    rows = {}
    for number, line in enumerate(lines, start=1):
        if not line.startswith("|"):
            continue
        columns = [part.strip() for part in line.strip().strip("|").split("|")]
        if columns[0] in ("指标", "---"):
            continue
        if len(columns) != 5:
            errors.append("line {}: metric row must have five columns".format(number))
            continue
        if columns[0] in rows:
            errors.append("line {}: repeated metric {}".format(number, columns[0]))
        rows[columns[0]] = (columns, number)
    return rows


def check_draft(content, task, source_task, evidence, contract, errors):
    lines = content.splitlines()
    expected_heading = "# 合成周报草稿：{}".format(task["period"])
    if not lines or lines[0] != expected_heading:
        errors.append("line 1: draft period heading differs from task")
    metadata = draft_fields(lines, errors)
    expected_fields = {
        "来源任务": source_task["id"],
        "证据文件": source_task["evidence"],
        "证据 SHA-256": source_task["evidence_sha256"],
        "口径版本": source_task["contract_version"],
        "口径 SHA-256": source_task["contract_sha256"],
        "上周产量": "—",
        "产量环比": "—",
    }
    for name, expected in expected_fields.items():
        if name not in metadata:
            errors.append("missing {} in draft".format(name))
        elif metadata[name][0] != expected:
            errors.append("line {}: {} is {!r}; expected {!r}".format(metadata[name][1], name, metadata[name][0], expected))

    rows = metric_rows(lines, errors)
    recorded_inputs = {item["path"]: item["sha256"] for item in evidence["inputs"]}
    expected_metrics = set()
    for source in contract["sources"]:
        metric = source["metric"]
        expected_metrics.add(metric)
        if metric not in rows:
            errors.append("missing metric {} in draft".format(metric))
            continue
        columns, number = rows[metric]
        metric_value = evidence["metrics"].get(metric)
        expected = (
            metric,
            str(metric_value) if metric_value is not None else "—",
            source["unit"],
            source["file"],
            recorded_inputs[source["file"]],
        )
        for label, actual, wanted in zip(("metric", "value", "unit", "source", "source fingerprint"), columns, expected):
            if actual != wanted:
                errors.append("line {}: {} {} is {!r}; expected {!r}".format(number, metric, label, actual, wanted))
    for extra in sorted(set(rows) - expected_metrics):
        errors.append("line {}: unexpected metric {}".format(rows[extra][1], extra))
    known_fields = ("来源任务：", "证据文件：", "证据 SHA-256：", "口径版本：", "口径 SHA-256：", "上周产量：", "产量环比：")
    for number, line in enumerate(lines, start=1):
        if number == 1 or line.startswith("|") or line.startswith(known_fields):
            continue
        if re.search(r"\d", line):
            errors.append("line {}: unreviewed numeric claim outside metric table".format(number))


def review_task(args):
    task = read_task(args.task)
    if task["status"] != "working":
        raise ValueError("draft task is not working; reviewed versions are immutable")
    if args.out.resolve() in (args.task.resolve(), Path(task["draft"]).resolve()):
        raise ValueError("review path must differ from task and draft paths")

    errors = []
    source_path = Path(task["source_task"])
    source_task = read_task(source_path)
    if source_task["status"] != "ready":
        errors.append("source task is not ready")
    try:
        verify_task(SimpleNamespace(task=source_path))
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        errors.append("source task verification failed: {}".format(error))
    if task.get("source_task_id") != source_task["id"] or task["period"] != source_task["period"]:
        errors.append("draft task identity differs from source task")
    if task.get("evidence") != source_task.get("evidence") or task.get("evidence_sha256") != source_task.get("evidence_sha256"):
        errors.append("draft task evidence reference differs from source task")
    if task.get("contract_sha256") != source_task.get("contract_sha256"):
        errors.append("draft task contract fingerprint differs from source task")

    try:
        evidence = json.loads(Path(source_task["evidence"]).read_text(encoding="utf-8"))
        if not isinstance(evidence, dict):
            raise ValueError("expected a JSON object")
    except (OSError, UnicodeError, ValueError) as error:
        evidence = None
        errors.append("evidence missing or unreadable: {}".format(error))
    try:
        source_review = json.loads(Path(source_task["review"]).read_text(encoding="utf-8"))
        if not isinstance(source_review, dict):
            raise ValueError("expected a JSON object")
    except (OSError, UnicodeError, ValueError) as error:
        source_review = None
        errors.append("source review missing or unreadable: {}".format(error))
    contract = None
    if source_review is not None:
        try:
            contract, _, _, contract_hash = load_contract(Path(source_review["contract"]))
            if contract_hash != source_task["contract_sha256"]:
                errors.append("source contract fingerprint mismatch")
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
            errors.append("contract missing or unreadable: {}".format(error))
    if evidence is not None and evidence.get("status") != "pass":
        errors.append("source evidence is not pass")
    if source_review is not None and source_review.get("status") != "pass":
        errors.append("source review is not pass")

    draft_path = Path(task["draft"])
    try:
        draft_bytes = draft_path.read_bytes()
        draft_content = draft_bytes.decode("utf-8")
        draft_hash = sha256(draft_bytes)
    except (OSError, UnicodeError) as error:
        draft_content = None
        draft_hash = None
        errors.append("draft {}: {}".format(draft_path, error))
    if draft_content is not None and evidence is not None and contract is not None:
        check_draft(draft_content, task, source_task, evidence, contract, errors)

    finding = {
        "schema_version": 1,
        "task_id": task["id"],
        "source_task_id": source_task["id"],
        "period": task["period"],
        "status": "blocked" if errors else "pass",
        "draft_sha256": draft_hash,
        "evidence_sha256": source_task["evidence_sha256"],
        "errors": errors,
    }
    content = (json.dumps(finding, indent=2, sort_keys=True) + "\n").encode("utf-8")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("xb") as stream:
        stream.write(content)
    task["status"] = "blocked" if errors else "ready"
    task["generated_draft_sha256"] = task["draft_sha256"]
    task["draft_sha256"] = draft_hash or "missing"
    task["review"] = str(args.out)
    task["review_sha256"] = sha256(content)
    args.task.write_text(task_text(task, errors), encoding="utf-8")
    return 2 if errors else 0


def verify_draft_task(args):
    task = read_task(args.task)
    if task["status"] not in ("ready", "blocked"):
        raise ValueError("draft task has no completed review")
    review_bytes = Path(task["review"]).read_bytes()
    if sha256(review_bytes) != task["review_sha256"]:
        raise ValueError("review fingerprint mismatch")
    review = json.loads(review_bytes.decode("utf-8"))
    expected_status = "pass" if task["status"] == "ready" else "blocked"
    if not isinstance(review, dict) or review.get("status") != expected_status:
        raise ValueError("draft task status contradicts review")
    if review.get("task_id") != task["id"] or review.get("period") != task["period"]:
        raise ValueError("draft review identity mismatch")
    if review.get("draft_sha256") != task["draft_sha256"]:
        raise ValueError("draft review fingerprint differs from task")
    try:
        current_draft_hash = sha256(Path(task["draft"]).read_bytes())
    except OSError:
        raise ValueError("draft fingerprint mismatch")
    if current_draft_hash != task["draft_sha256"]:
        raise ValueError("draft fingerprint mismatch")
    source_path = Path(task["source_task"])
    source_task = read_task(source_path)
    if source_task["status"] != "ready":
        raise ValueError("source task is not ready")
    verify_task(SimpleNamespace(task=source_path))
    if task["evidence_sha256"] != source_task["evidence_sha256"] or review.get("evidence_sha256") != source_task["evidence_sha256"]:
        raise ValueError("evidence fingerprint differs from source task")
    print("{}: {} (draft and evidence links verified)".format(task["id"], task["status"]))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("finalize", "verify"), default="finalize")
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.command == "finalize" and args.out is None:
        parser.error("finalize requires --out")
    try:
        return verify_draft_task(args) if args.command == "verify" else review_task(args)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        print("review-demo-report: {}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
