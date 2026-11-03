#!/usr/bin/env python3
"""Create a synthetic weekly-report draft from a ready source task."""

import argparse
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

from check_inputs import load_contract
from report_task import task_text
from source_audit import (
    read_task, resolve_review_reference, resolve_task_reference,
    review_reference, sha256, task_reference, verify_task,
)


def draft_text(source_task, evidence, contract):
    input_hashes = {item["path"]: item["sha256"] for item in evidence["inputs"]}
    metrics = evidence["metrics"]
    lines = [
        "# 合成周报草稿：{}".format(source_task["period"]),
        "",
        "来源任务：{}".format(source_task["id"]),
        "证据文件：{}".format(source_task["evidence"]),
        "证据 SHA-256：{}".format(source_task["evidence_sha256"]),
        "口径版本：{}".format(source_task["contract_version"]),
        "口径 SHA-256：{}".format(source_task["contract_sha256"]),
        "",
        "## 本周指标",
        "",
        "| 指标 | 本周值 | 单位 | 来源文件 | 来源 SHA-256 |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for source in contract["sources"]:
        metric = source["metric"]
        value = metrics.get(metric)
        lines.append("| {} | {} | {} | {} | {} |".format(
            metric, str(value) if value is not None else "—", source["unit"],
            source["file"], input_hashes[source["file"]],
        ))
    lines.extend([
        "", "## 历史对比", "", "上周产量：—", "产量环比：—", "",
        "历史周数据未提供；这两个值不作推算。", "",
        "草稿仅供人工审阅，尚未验收。", "",
    ])
    return "\n".join(lines)


def create_draft(args):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.id):
        raise ValueError("id must contain only letters, digits, dots, hyphens, or underscores")
    source_task = read_task(args.source_task)
    if source_task["status"] != "ready":
        raise ValueError("source task is {}: ready source required".format(source_task["status"]))
    verify_task(SimpleNamespace(task=args.source_task))
    evidence_path = resolve_task_reference(source_task["evidence"], args.source_task)
    source_task["evidence"] = task_reference(evidence_path, args.source_task)
    source_review_path = resolve_task_reference(source_task["review"], args.source_task)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    source_review = json.loads(source_review_path.read_text(encoding="utf-8"))
    if evidence.get("status") != "pass" or source_review.get("status") != "pass":
        raise ValueError("source task lacks passing evidence and source review")
    contract_path = resolve_review_reference(source_review["contract"], source_review_path)
    contract, _, _, contract_hash = load_contract(contract_path)
    if contract_hash != source_task["contract_sha256"]:
        raise ValueError("contract fingerprint mismatch")
    if args.task.exists() or args.draft.exists():
        raise ValueError("draft or task already exists; use a new run id")

    content = draft_text(source_task, evidence, contract)
    args.draft.parent.mkdir(parents=True, exist_ok=True)
    with args.draft.open("x", encoding="utf-8") as stream:
        stream.write(content)
    fields = {
        "id": args.id,
        "period": source_task["period"],
        "status": "working",
        "source_task": task_reference(args.source_task, args.task),
        "source_task_id": source_task["id"],
        "evidence": task_reference(evidence_path, args.task),
        "evidence_sha256": source_task["evidence_sha256"],
        "contract": review_reference(contract_path, source_review_path),
        "contract_sha256": source_task["contract_sha256"],
        "draft": task_reference(args.draft, args.task),
        "draft_sha256": sha256(args.draft.read_bytes()),
    }
    args.task.parent.mkdir(parents=True, exist_ok=True)
    with args.task.open("x", encoding="utf-8") as stream:
        stream.write(task_text(fields))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-task", type=Path, required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--id", required=True)
    args = parser.parse_args()
    try:
        return create_draft(args)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        print("draft-demo-report: {}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
