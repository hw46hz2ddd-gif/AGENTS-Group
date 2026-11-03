#!/usr/bin/env python3
"""Produce deterministic evidence for the synthetic weekly-report inputs."""

import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re


def write_evidence(path: Path, evidence: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_contract(path: Path):
    content = path.read_bytes()
    contract = json.loads(content.decode("utf-8"))
    if not isinstance(contract, dict):
        raise ValueError("expected a JSON object")
    for key in ("contract_version", "period", "start_date", "end_date"):
        if not isinstance(contract.get(key), str) or not contract[key]:
            raise ValueError("missing or invalid " + key)
    try:
        start_date = date.fromisoformat(contract["start_date"])
        end_date = date.fromisoformat(contract["end_date"])
    except ValueError:
        raise ValueError("start_date and end_date must be ISO dates")
    if start_date > end_date:
        raise ValueError("start_date is after end_date")
    match = re.fullmatch(r"(\d{4})-W(\d{2})", contract["period"])
    if match is None:
        raise ValueError("period must be an ISO week in YYYY-Www form")
    try:
        expected_start = date.fromisocalendar(int(match.group(1)), int(match.group(2)), 1)
        expected_end = date.fromisocalendar(int(match.group(1)), int(match.group(2)), 7)
    except ValueError:
        raise ValueError("period must be a valid ISO week")
    if start_date != expected_start or end_date != expected_end:
        raise ValueError("start_date and end_date do not match the declared ISO week")
    sources = contract.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources must be a non-empty list")
    seen_metrics = set()
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            raise ValueError("source {} must be an object".format(index))
        for key in ("file", "key_column", "date_column", "value_column", "metric"):
            if not isinstance(source.get(key), str) or not source[key]:
                raise ValueError("source {} missing or invalid {}".format(index, key))
        if source["metric"] in seen_metrics:
            raise ValueError("source {} duplicate metric {}".format(index, source["metric"]))
        seen_metrics.add(source["metric"])
        if not isinstance(source.get("unit"), str) or not source["unit"].strip():
            raise ValueError("source {} missing or invalid unit".format(index))
        if Path(source["file"]).name != source["file"]:
            raise ValueError("source {} file must be a filename".format(index))
        columns = source.get("required_columns")
        if not isinstance(columns, list) or not columns or not all(isinstance(column, str) for column in columns):
            raise ValueError("source {} required_columns must be a list of names".format(index))
        if any(source[key] not in columns for key in ("key_column", "date_column", "value_column")):
            raise ValueError("source {} required_columns omits a used column".format(index))
    return contract, start_date, end_date, hashlib.sha256(content).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--period", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        contract, start_date, end_date, contract_hash = load_contract(args.contract)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        write_evidence(args.out, {
            "schema_version": 1,
            "period": args.period,
            "contract_version": None,
            "contract_sha256": None,
            "status": "blocked",
            "inputs": [],
            "metrics": {},
            "errors": ["contract {}: {}".format(args.contract.name, error)],
        })
        return 2

    inputs = []
    metrics = {}
    errors = []
    if args.period != contract["period"]:
        errors.append("requested period {} differs from contract period {}".format(args.period, contract["period"]))
    for source in contract["sources"]:
        path = args.input_dir / source["file"]
        if not path.is_file():
            errors.append("{}: missing source".format(source["file"]))
            continue
        content = path.read_bytes()
        source_hash = hashlib.sha256(content).hexdigest()
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError:
            inputs.append({"path": source["file"], "sha256": source_hash, "rows": None})
            errors.append("{}: invalid UTF-8".format(source["file"]))
            continue
        with io.StringIO(decoded, newline="") as stream:
            reader = csv.DictReader(stream)
            fieldnames = reader.fieldnames or []
            rows = list(reader)
        inputs.append({"path": source["file"], "sha256": source_hash, "rows": len(rows)})
        seen_columns = set()
        duplicate_columns = set()
        for column in fieldnames:
            if column in seen_columns:
                duplicate_columns.add(column)
            seen_columns.add(column)
        if duplicate_columns:
            errors.extend(
                "{}:1: duplicate column {}".format(source["file"], column)
                for column in sorted(duplicate_columns)
            )
            continue
        missing_columns = [column for column in source["required_columns"] if column not in fieldnames]
        if missing_columns:
            errors.extend("{}: missing column {}".format(source["file"], column) for column in missing_columns)
            continue
        seen_keys = set()
        values = []
        for line_number, row in enumerate(rows, start=2):
            record_id = row[source["key_column"]]
            if not isinstance(record_id, str) or not record_id.strip():
                errors.append("{}:{}: blank key {}".format(source["file"], line_number, source["key_column"]))
            else:
                if record_id in seen_keys:
                    errors.append("{}:{}: duplicate record_id".format(source["file"], line_number))
                seen_keys.add(record_id)
            try:
                row_date = date.fromisoformat(row[source["date_column"]])
            except (TypeError, ValueError):
                errors.append("{}:{}: invalid date".format(source["file"], line_number))
                continue
            if not start_date <= row_date <= end_date:
                errors.append("{}:{}: date outside requested period {}".format(source["file"], line_number, args.period))
            try:
                value = Decimal(row[source["value_column"]])
            except (InvalidOperation, TypeError):
                errors.append("{}:{}: invalid integer value".format(source["file"], line_number))
                continue
            if not value.is_finite() or value != value.to_integral_value():
                errors.append("{}:{}: value must be an integer".format(source["file"], line_number))
                continue
            values.append(value)
        total = sum(values, Decimal(0))
        metrics[source["metric"]] = int(total)

    evidence = {
        "schema_version": 1,
        "period": args.period,
        "contract_version": contract["contract_version"],
        "contract_sha256": contract_hash,
        "status": "blocked" if errors else "pass",
        "inputs": inputs,
        "metrics": {} if errors else metrics,
        "errors": errors,
    }
    write_evidence(args.out, evidence)
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
