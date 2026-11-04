"""Behavior checks through the report-input validator's CLI boundary."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_inputs.py"
CONTRACT = ROOT / "contracts" / "demo.v1.json"
FIXTURES = ROOT / "fixtures" / "demo"
sys.path.insert(0, str(ROOT / "scripts"))
from check_inputs import PreflightError, ensure_safe_evidence_path


class CheckInputsCliTests(unittest.TestCase):
    def copy_to_simulation_path(self, parent):
        input_dir = Path(parent) / "simulation-only" / "input"
        input_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(FIXTURES, input_dir)
        return input_dir

    def copy_contract_sources_only(self, parent):
        input_dir = Path(parent) / "synthetic-real-mode-input"
        input_dir.mkdir(parents=True)
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        for source in contract["sources"]:
            shutil.copyfile(FIXTURES / source["file"], input_dir / source["file"])
        return input_dir

    def write_non_simulation_contract(self, root):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        contract.pop("simulation_only", None)
        content = (json.dumps(contract, indent=2, sort_keys=True) + "\n").encode("utf-8")
        contract_path = Path(root) / "real-contract.json"
        contract_path.write_bytes(content)
        return contract, contract_path, hashlib.sha256(content).hexdigest()

    def write_test_approval_manifest(self, root, input_dir, contract, contract_sha256):
        root = Path(root)
        approval_dir = root / "approval"
        approval_dir.mkdir(parents=True, exist_ok=True)
        approval_bytes = b"Synthetic test approval record; not a real authorization.\n"
        (approval_dir / "approval-record.md").write_bytes(approval_bytes)
        sources = []
        for source in contract["sources"]:
            content = (Path(input_dir) / source["file"]).read_bytes()
            sources.append({"file": source["file"], "sha256": hashlib.sha256(content).hexdigest()})
        manifest = {
            "schema_version": 1,
            "approval_state": "approved",
            "simulation_only": False,
            "data_owner": {"name": "Synthetic Test Owner", "title": "Fixture only"},
            "approver": {"name": "Synthetic Test Approver", "title": "Fixture only"},
            "approved_at": "2026-11-04",
            "approval_record": {
                "path": "approval-record.md",
                "sha256": hashlib.sha256(approval_bytes).hexdigest(),
            },
            "user_processing_authorized": True,
            "user_processing_authorized_at": "2026-11-04",
            "scope": {
                "period": contract["period"],
                "contract_version": contract["contract_version"],
                "contract_sha256": contract_sha256,
                "input_dir": str(Path(input_dir).resolve()),
            },
            "sources": sources,
            "handling": {
                "read_only": True,
                "codex_visibility": "aggregates_only",
                "evidence_policy": "safe_metadata_and_aggregates",
                "external_sharing": False,
                "retention_days": 30,
                "cleanup_owner": "Synthetic Test Cleanup Owner",
            },
        }
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        manifest_path = approval_dir / "manifest.json"
        manifest_path.write_bytes(manifest_bytes)
        return manifest_path, hashlib.sha256(manifest_bytes).hexdigest()

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
            self.assertEqual(evidence["run_mode"], "simulation")
            self.assertIsNone(evidence["approval_manifest_sha256"])
            self.assertEqual(evidence["period"], "2026-W44")
            self.assertEqual(evidence["contract_version"], "demo-v1")
            self.assertEqual(evidence.get("contract_sha256"), hashlib.sha256(CONTRACT.read_bytes()).hexdigest())
            self.assertEqual(evidence["metrics"], {"output_qty": 30, "case_count": 1})
            self.assertEqual({item["path"]: item["rows"] for item in evidence["inputs"]}, {"mes.csv": 2, "ai_ehs.csv": 2})
            self.assertTrue(all(len(item["sha256"]) == 64 for item in evidence["inputs"]))
            self.assertEqual(evidence["errors"], [])

    def test_out_of_period_row_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = self.copy_to_simulation_path(temp_dir)
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
            self.assertNotIn("2026-11-02", json.dumps(evidence))

    def test_duplicate_record_id_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = self.copy_to_simulation_path(temp_dir)
            (input_dir / "mes.csv").write_text(
                "date,record_id,output_qty\n"
                "2026-10-26,KEY-PRIVATE-SENTINEL,123456789\n"
                "2026-10-27,KEY-PRIVATE-SENTINEL,987654321\n",
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
            self.assertTrue(any("mes.csv:3" in error and "duplicate key" in error for error in evidence["errors"]))
            serialized = json.dumps(evidence)
            self.assertNotIn("KEY-PRIVATE-SENTINEL", serialized)
            self.assertNotIn("123456789", serialized)
            self.assertNotIn("987654321", serialized)

    def test_empty_record_id_blocks_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = self.copy_to_simulation_path(temp_dir)
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
            input_dir = self.copy_to_simulation_path(temp_dir)
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
            input_dir = self.copy_to_simulation_path(temp_dir)
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
            input_dir = self.copy_to_simulation_path(temp_dir)
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
            input_dir = self.copy_to_simulation_path(temp_dir)
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
            self.assertEqual(evidence["inputs"], [])
            self.assertTrue(any("approval scope" in error for error in evidence["errors"]))

    def test_fractional_count_is_not_silently_truncated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = self.copy_to_simulation_path(temp_dir)
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
            input_dir = self.copy_to_simulation_path(temp_dir)
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

    def test_contract_period_must_be_a_valid_iso_week_matching_its_dates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            invalid_week = json.loads(CONTRACT.read_text(encoding="utf-8"))
            invalid_week["period"] = "2026-W99"
            invalid_week_path = root / "invalid-week.json"
            invalid_week_path.write_text(json.dumps(invalid_week), encoding="utf-8")
            invalid_week_evidence = root / "invalid-week-evidence.json"
            invalid_week_result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W99", "--contract", str(invalid_week_path),
                 "--input-dir", str(FIXTURES), "--out", str(invalid_week_evidence)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(invalid_week_result.returncode, 2)
            invalid_week_payload = json.loads(invalid_week_evidence.read_text(encoding="utf-8"))
            self.assertEqual(invalid_week_payload["inputs"], [])
            self.assertTrue(any("valid ISO week" in error for error in invalid_week_payload["errors"]))

            input_dir = self.copy_contract_sources_only(root)
            mismatched = json.loads(CONTRACT.read_text(encoding="utf-8"))
            mismatched.pop("simulation_only", None)
            mismatched["start_date"] = "2026-10-19"
            mismatched["end_date"] = "2026-10-25"
            contract_bytes = (json.dumps(mismatched, indent=2, sort_keys=True) + "\n").encode("utf-8")
            contract_path = root / "mismatched-week-contract.json"
            contract_path.write_bytes(contract_bytes)
            manifest_path, _ = self.write_test_approval_manifest(
                root, input_dir, mismatched, hashlib.sha256(contract_bytes).hexdigest(),
            )
            evidence_path = root / "mismatched-week-evidence.json"
            mismatch_result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(contract_path),
                 "--input-dir", str(input_dir), "--approval-manifest", str(manifest_path), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(mismatch_result.returncode, 2)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["inputs"], [])
            self.assertEqual(evidence["metrics"], {})
            self.assertTrue(any("does not match its ISO week" in error for error in evidence["errors"]))

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
            input_dir = self.copy_to_simulation_path(temp_dir)
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

    def test_real_contract_without_manifest_blocks_before_recording_source_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, contract_path, _ = self.write_non_simulation_contract(root)
            evidence_path = root / "evidence.json"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(contract_path),
                 "--input-dir", str(FIXTURES), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertEqual(evidence["run_mode"], "real")
            self.assertIsNone(evidence["approval_manifest_sha256"])
            self.assertEqual(evidence["inputs"], [])
            self.assertEqual(evidence["metrics"], {})
            self.assertTrue(any("approval manifest is required" in error for error in evidence["errors"]))
            self.assertNotIn("KEY-SENTINEL", json.dumps(evidence))

    def test_complete_manifest_allows_a_non_simulation_contract_with_synthetic_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.copy_contract_sources_only(root)
            contract, contract_path, _ = self.write_non_simulation_contract(root)
            manifest_path, manifest_hash = self.write_test_approval_manifest(
                root, input_dir, contract, hashlib.sha256(contract_path.read_bytes()).hexdigest(),
            )
            evidence_path = root / "evidence.json"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(contract_path),
                 "--input-dir", str(input_dir), "--approval-manifest", str(manifest_path), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "pass")
            self.assertEqual(evidence["run_mode"], "real")
            self.assertEqual(evidence["approval_manifest_sha256"], manifest_hash)
            self.assertEqual(evidence["metrics"], {"output_qty": 30, "case_count": 1})

    def test_evidence_output_cannot_overwrite_approved_inputs_or_approval_artifacts(self):
        for target_kind in ("source", "contract", "manifest", "approval-record"):
            with self.subTest(target=target_kind), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                input_dir = self.copy_contract_sources_only(root)
                contract, contract_path, _ = self.write_non_simulation_contract(root)
                manifest_path, _ = self.write_test_approval_manifest(
                    root, input_dir, contract, hashlib.sha256(contract_path.read_bytes()).hexdigest(),
                )
                targets = {
                    "source": input_dir / "mes.csv",
                    "contract": contract_path,
                    "manifest": manifest_path,
                    "approval-record": manifest_path.parent / "approval-record.md",
                }
                output_path = targets[target_kind]
                original = output_path.read_bytes()

                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(contract_path),
                     "--input-dir", str(input_dir), "--approval-manifest", str(manifest_path), "--out", str(output_path)],
                    cwd=str(ROOT), capture_output=True, text=True,
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn("evidence output", result.stderr)
                self.assertNotIn(str(root), result.stderr)
                self.assertEqual(output_path.read_bytes(), original)

    def test_evidence_output_rejects_hard_link_aliases_to_other_fixture_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "project"
            fixture_dir = project / "fixtures"
            fixture_dir.mkdir(parents=True)
            protected_fixture = fixture_dir / "other-synthetic-fixture.csv"
            protected_fixture.write_bytes(b"synthetic fixture must remain unchanged\n")
            input_dir = root / "external-input"
            input_dir.mkdir()
            contract_path = root / "contract.json"
            contract_path.write_text("{}\n", encoding="utf-8")
            output_dir = root / "external-output"
            output_dir.mkdir()
            output_path = output_dir / "evidence.json"
            os.link(protected_fixture, output_path)

            with self.assertRaisesRegex(PreflightError, "evidence output"):
                ensure_safe_evidence_path(
                    output_path, input_dir, contract_path, None, project,
                )

    def test_both_synthetic_contracts_pass_under_fixture_paths_without_a_manifest(self):
        cases = (
            (CONTRACT, FIXTURES, "2026-W44"),
            (ROOT / "contracts" / "historical-simulation.v1.json",
             ROOT / "fixtures" / "historical-simulation", "2026-W43"),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for index, (contract_path, input_dir, period) in enumerate(cases):
                with self.subTest(contract=contract_path.name):
                    evidence_path = root / ("evidence-{}.json".format(index))
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), "--period", period, "--contract", str(contract_path),
                         "--input-dir", str(input_dir), "--out", str(evidence_path)],
                        cwd=str(ROOT), capture_output=True, text=True,
                    )

                    self.assertEqual(result.returncode, 0, result.stderr)
                    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                    self.assertEqual(evidence["status"], "pass")
                    self.assertEqual(evidence["run_mode"], "simulation")
                    self.assertIsNone(evidence["approval_manifest_sha256"])

    def test_synthetic_contract_outside_simulation_paths_blocks_without_source_hashes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "outside" / "input"
            input_dir.parent.mkdir()
            shutil.copytree(FIXTURES, input_dir)
            evidence_path = root / "evidence.json"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT),
                 "--input-dir", str(input_dir), "--out", str(evidence_path)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "blocked")
            self.assertEqual(evidence["run_mode"], "simulation")
            self.assertEqual(evidence["inputs"], [])
            self.assertEqual(evidence["metrics"], {})
            self.assertTrue(any("outside the allowed simulation paths" in error for error in evidence["errors"]))

    def test_validator_parses_the_exact_bytes_returned_by_preflight(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = self.copy_to_simulation_path(root)
            snapshots = {path.name: path.read_bytes() for path in input_dir.iterdir()}
            approved_hashes = {
                filename: hashlib.sha256(content).hexdigest()
                for filename, content in snapshots.items()
            }
            (input_dir / "mes.csv").write_text(
                "date,record_id,output_qty\n2026-10-26,CHANGED-ROW,999999\n",
                encoding="utf-8",
            )
            evidence_path = root / "evidence.json"

            sys.path.insert(0, str(ROOT / "scripts"))
            spec = importlib.util.spec_from_file_location("check_inputs_preflight_test", SCRIPT)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with patch.object(
                module,
                "validate_preflight",
                return_value={
                    "run_mode": "simulation",
                    "approval_manifest_sha256": None,
                    "source_hashes": approved_hashes,
                    "source_contents": snapshots,
                },
                create=True,
            ), patch.object(
                sys,
                "argv",
                [str(SCRIPT), "--period", "2026-W44", "--contract", str(CONTRACT),
                 "--input-dir", str(input_dir), "--out", str(evidence_path)],
            ):
                result = module.main()

            self.assertEqual(result, 0)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["metrics"], {"output_qty": 30, "case_count": 1})
            mes_evidence = next(item for item in evidence["inputs"] if item["path"] == "mes.csv")
            self.assertEqual(mes_evidence["sha256"], approved_hashes["mes.csv"])



if __name__ == "__main__":
    unittest.main()
