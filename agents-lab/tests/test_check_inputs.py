"""Behavior checks through the report-input validator's CLI boundary."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_inputs.py"
CONTRACT = ROOT / "contracts" / "demo.v1.json"
FIXTURES = ROOT / "fixtures" / "demo"


class CheckInputsCliTests(unittest.TestCase):
    def test_valid_synthetic_week_produces_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            evidence_path = Path(temp_dir) / "nested" / "evidence.json"
            command = [
                sys.executable,
                str(SCRIPT),
                "--period", "2026-W44",
                "--contract", str(CONTRACT),
                "--input-dir", str(FIXTURES),
                "--out", str(evidence_path),
            ]
            result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True)

            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "pass")
            self.assertEqual(evidence["period"], "2026-W44")
            self.assertEqual(evidence["contract_version"], "demo-v1")
            self.assertEqual(evidence.get("contract_sha256"), hashlib.sha256(CONTRACT.read_bytes()).hexdigest())
            self.assertEqual(evidence["metrics"], {"output_qty": 30, "case_count": 1})
            self.assertEqual({item["path"]: item["rows"] for item in evidence["inputs"]}, {"mes.csv": 2, "ai_ehs.csv": 2})
            self.assertTrue(all(len(item["sha256"]) == 64 for item in evidence["inputs"]))
            self.assertEqual(evidence["errors"], [])

    def test_out_of_period_row_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            shutil.copytree(FIXTURES, input_dir)
            with (input_dir / "mes.csv").open("a", encoding="utf-8") as stream:
                stream.write("2026-11-02,M-003,5\n")
            evidence_path = Path(temp_dir) / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT), "--input-dir", str(input_dir), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertTrue(any("mes.csv:4" in error and "outside" in error for error in evidence["errors"]))

    def test_duplicate_record_id_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            shutil.copytree(FIXTURES, input_dir)
            with (input_dir / "mes.csv").open("a", encoding="utf-8") as stream:
                stream.write("2026-10-28,M-001,5\n")
            evidence_path = Path(temp_dir) / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT), "--input-dir", str(input_dir), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertTrue(any("mes.csv:4" in error and "duplicate record_id" in error for error in evidence["errors"]))

    def test_empty_record_id_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            shutil.copytree(FIXTURES, input_dir)
            (input_dir / "mes.csv").write_text(
                "date,record_id,output_qty\n2026-10-26,,10\n2026-10-27,M-002,20\n",
                encoding="utf-8",
            )
            evidence_path = Path(temp_dir) / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT), "--input-dir", str(input_dir), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertEqual(evidence["metrics"], {})
            self.assertTrue(any("mes.csv:2" in error and "record_id" in error and "blank" in error for error in evidence["errors"]))

    def test_whitespace_only_record_id_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            shutil.copytree(FIXTURES, input_dir)
            (input_dir / "mes.csv").write_text(
                "date,record_id,output_qty\n2026-10-26, \t ,10\n2026-10-27,M-002,20\n",
                encoding="utf-8",
            )
            evidence_path = Path(temp_dir) / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT), "--input-dir", str(input_dir), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertEqual(evidence["metrics"], {})
            self.assertTrue(any("mes.csv:2" in error and "record_id" in error and "blank" in error for error in evidence["errors"]))

    def test_duplicate_metric_header_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            shutil.copytree(FIXTURES, input_dir)
            (input_dir / "mes.csv").write_text(
                "date,record_id,output_qty,output_qty\n2026-10-26,M-001,10,999\n",
                encoding="utf-8",
            )
            evidence_path = Path(temp_dir) / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT), "--input-dir", str(input_dir), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertEqual(evidence["metrics"], {})
            self.assertTrue(any("mes.csv:1" in error and "duplicate column" in error and "output_qty" in error for error in evidence["errors"]))

    def test_missing_required_column_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            shutil.copytree(FIXTURES, input_dir)
            (input_dir / "mes.csv").write_text("date,record_id\n2026-10-26,M-001\n", encoding="utf-8")
            evidence_path = Path(temp_dir) / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT), "--input-dir", str(input_dir), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertTrue(any("mes.csv" in error and "missing column output_qty" in error for error in evidence["errors"]))

    def test_missing_source_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            shutil.copytree(FIXTURES, input_dir)
            (input_dir / "ai_ehs.csv").unlink()
            evidence_path = Path(temp_dir) / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT), "--input-dir", str(input_dir), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertTrue(any("ai_ehs.csv" in error and "missing source" in error for error in evidence["errors"]))

    def test_requested_period_must_match_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            evidence_path = Path(temp_dir) / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W43", "--contract", str(CONTRACT), "--input-dir", str(FIXTURES), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertTrue(any("2026-W43" in error and "2026-W44" in error for error in evidence["errors"]))

    def test_fractional_count_is_not_silently_truncated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            shutil.copytree(FIXTURES, input_dir)
            (input_dir / "mes.csv").write_text(
                "date,record_id,output_qty\n2026-10-26,M-001,10.5\n2026-10-27,M-002,20\n",
                encoding="utf-8",
            )
            evidence_path = Path(temp_dir) / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT), "--input-dir", str(input_dir), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertTrue(any("mes.csv:2" in error and "integer" in error for error in evidence["errors"]))

    def test_invalid_date_is_reported_as_blocked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            shutil.copytree(FIXTURES, input_dir)
            (input_dir / "mes.csv").write_text(
                "date,record_id,output_qty\nnot-a-date,M-001,10\n2026-10-27,M-002,20\n",
                encoding="utf-8",
            )
            evidence_path = Path(temp_dir) / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT), "--input-dir", str(input_dir), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertTrue(any("mes.csv:2" in error and "invalid date" in error for error in evidence["errors"]))

    def test_invalid_contract_still_writes_blocked_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            malformed = root / "malformed.json"
            malformed.write_text("{not json", encoding="utf-8")
            invalid_dates = root / "invalid-dates.json"
            contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
            contract["start_date"] = "not-a-date"
            invalid_dates.write_text(json.dumps(contract), encoding="utf-8")

            for contract_path in (root / "missing.json", malformed, invalid_dates):
                with self.subTest(contract=contract_path.name):
                    evidence_path = root / (contract_path.stem + "-evidence.json")
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(contract_path), "--input-dir", str(FIXTURES), "--out", str(evidence_path)],
                        cwd=str(ROOT), capture_output=True, text=True,
                    )

                    self.assertEqual(result.returncode, 2, result.stderr)
                    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                    self.assertEqual(evidence["status"], "blocked")
                    self.assertEqual(evidence["metrics"], {})
                    self.assertTrue(any("contract" in error and contract_path.name in error for error in evidence["errors"]))

    def test_missing_or_invalid_metric_unit_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            invalid_units = (("missing", None), ("empty", ""), ("whitespace", " \t "), ("non-string", 7))
            for name, unit in invalid_units:
                with self.subTest(unit=name):
                    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
                    if name == "missing":
                        contract["sources"][0].pop("unit")
                    else:
                        contract["sources"][0]["unit"] = unit
                    contract_path = root / (name + "-contract.json")
                    contract_path.write_text(json.dumps(contract), encoding="utf-8")
                    evidence_path = root / (name + "-evidence.json")
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(contract_path), "--input-dir", str(FIXTURES), "--out", str(evidence_path)],
                        cwd=str(ROOT), capture_output=True, text=True,
                    )

                    self.assertEqual(result.returncode, 2, result.stderr)
                    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                    self.assertEqual(evidence["status"], "blocked")
                    self.assertEqual(evidence["metrics"], {})
                    self.assertTrue(any("contract" in error and "unit" in error for error in evidence["errors"]))

    def test_duplicate_contract_metric_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
            contract["sources"][1]["metric"] = "output_qty"
            contract_path = root / "duplicate-metric-contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            evidence_path = root / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(contract_path), "--input-dir", str(FIXTURES), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertEqual(evidence["metrics"], {})
            self.assertTrue(any("duplicate metric" in error and "output_qty" in error for error in evidence["errors"]))

    def test_unreadable_source_encoding_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            shutil.copytree(FIXTURES, input_dir)
            (input_dir / "mes.csv").write_bytes(b"\xff\xfe\x00")
            evidence_path = Path(temp_dir) / "evidence.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT), "--input-dir", str(input_dir), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertTrue(any("mes.csv" in error and "UTF-8" in error for error in evidence["errors"]))


if __name__ == "__main__":
    unittest.main()
