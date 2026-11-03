#!/usr/bin/env python3
"""Record and verify a person's decision for a reviewed weekly-report draft."""

import argparse
from contextlib import redirect_stdout
import io
from pathlib import Path
import re
import sys
from types import SimpleNamespace

from review_demo_report import verify_draft_task
from source_audit import read_task, sha256


def read_decision(path):
    content = path.read_text(encoding="utf-8")
    fields = read_task(path)
    lines = content.splitlines()
    end = lines.index("---", 1)
    body = "\n".join(lines[end + 1:]).strip()
    return fields, body


def verified_ready_draft(path):
    task_path = Path(path)
    task_bytes = task_path.read_bytes()
    task = read_task(task_path)
    if task["status"] != "ready":
        raise ValueError("draft task is {}: ready draft required".format(task["status"]))
    with redirect_stdout(io.StringIO()):
        verify_draft_task(SimpleNamespace(task=task_path))
    if task_path.read_bytes() != task_bytes:
        raise ValueError("draft task changed during verification")
    source_task = read_task(Path(task["source_task"]))
    if source_task["status"] != "ready":
        raise ValueError("source task changed during verification")
    if task.get("source_task_id") != source_task["id"] or task["period"] != source_task["period"]:
        raise ValueError("draft task identity changed during verification")
    if task["evidence"] != source_task["evidence"]:
        raise ValueError("draft evidence path differs from source task")
    if task["evidence_sha256"] != source_task["evidence_sha256"]:
        raise ValueError("draft evidence fingerprint differs from source task")
    if task["contract_sha256"] != source_task["contract_sha256"]:
        raise ValueError("draft contract fingerprint differs from source task")
    return task


def decision_text(fields, reason=None):
    lines = ["---"]
    lines.extend("{}: {}".format(key, value) for key, value in fields.items())
    lines.extend(["---", "", "# Draft decision: {}".format(fields["id"]), ""])
    if reason is not None:
        lines.extend(["## Reason", "", reason, ""])
    return "\n".join(lines)


def decision_reason(body):
    lines = body.splitlines()
    start = next((index for index, line in enumerate(lines) if line.strip() == "## Reason"), None)
    if start is None:
        return ""
    end = next((
        index for index in range(start + 1, len(lines))
        if re.match(r"^\s{0,3}#{1,6}(?:\s|$)", lines[index])
    ), len(lines))
    return "\n".join(lines[start + 1:end]).strip()


def record_decision(args):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.out.stem):
        raise ValueError("decision record name must contain only letters, digits, dots, hyphens, or underscores")
    if args.out.exists():
        raise ValueError("decision record already exists: {}".format(args.out))
    task = verified_ready_draft(args.draft_task)
    reason = args.reason.strip() if args.reason is not None else None
    if args.decision == "returned" and not reason:
        raise ValueError("returned decisions require a nonblank reason")

    draft_path = Path(task["draft"])
    evidence_path = task["evidence"]
    review_path = Path(task["review"])
    draft_hash = task["draft_sha256"]
    if sha256(draft_path.read_bytes()) != draft_hash:
        raise ValueError("draft fingerprint changed during verification")
    if sha256(Path(evidence_path).read_bytes()) != task["evidence_sha256"]:
        raise ValueError("evidence fingerprint changed during verification")
    if sha256(review_path.read_bytes()) != task["review_sha256"]:
        raise ValueError("review fingerprint changed during verification")
    fields = {
        "id": args.out.stem,
        "period": task["period"],
        "status": "decided",
        "decision": args.decision,
        "draft_task": str(args.draft_task),
        "draft_task_id": task["id"],
        "draft_sha256": draft_hash,
        "evidence": evidence_path,
        "evidence_sha256": task["evidence_sha256"],
    }
    content = decision_text(fields, reason)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(content)
    except FileExistsError:
        raise ValueError("decision record already exists: {}".format(args.out))
    print("decision record {}: {}".format(args.out, args.decision))
    return 0


def verify_decision(args):
    record, body = read_decision(args.record)
    if record["status"] != "decided":
        raise ValueError("decision record status must be decided")
    if record.get("decision") not in ("accepted", "returned"):
        raise ValueError("decision must be accepted or returned")
    if record["decision"] == "returned" and not decision_reason(body):
        raise ValueError("returned decision record requires a nonblank reason")

    draft_task_path = Path(record["draft_task"])
    task = verified_ready_draft(draft_task_path)
    if record["draft_task_id"] != task["id"] or record["period"] != task["period"]:
        raise ValueError("decision record draft identity mismatch")
    if record["draft_sha256"] != task["draft_sha256"]:
        raise ValueError("decision record draft fingerprint mismatch")
    if record["evidence"] != task["evidence"] or record["evidence_sha256"] != task["evidence_sha256"]:
        raise ValueError("decision record evidence fingerprint mismatch")
    print("decision {}: {} (draft and evidence verified)".format(record["id"], record["decision"]))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    record = commands.add_parser("record", help="record an explicit decision for a ready draft")
    record.add_argument("--draft-task", type=Path, required=True)
    record.add_argument("--decision", choices=("accepted", "returned"), required=True)
    record.add_argument("--out", type=Path, required=True)
    record.add_argument("--reason")

    verify = commands.add_parser("verify", help="verify a decision record and its linked artifacts")
    verify.add_argument("--record", type=Path, required=True)

    args = parser.parse_args()
    try:
        return record_decision(args) if args.command == "record" else verify_decision(args)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        print("record-draft-decision: {}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
