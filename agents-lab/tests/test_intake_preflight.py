"""Behavior tests for the historical-intake approval preflight."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.intake_preflight import PreflightError, validate_preflight


DEFAULT_MANIFEST = object()


def sha256(content):
    return hashlib.sha256(content).hexdigest()


class IntakePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.project_root = Path(self.temp_dir.name) / "repo"
        self.input_dir = self.project_root / "inputs" / "2026-W44"
        self.input_dir.mkdir(parents=True)

        self.source_contents = {
            "mes.csv": b"date,record_id,qty\n2026-10-26,KEY-SENTINEL,VALUE-SENTINEL\n",
            "ehs.csv": b"date,record_id,cases\n2026-10-27,CASE-SENTINEL,3\n",
        }
        for filename, content in self.source_contents.items():
            (self.input_dir / filename).write_bytes(content)

        self.contract = {
            "contract_version": "metrics-v7",
            "period": "2026-W44",
            "start_date": "2026-10-26",
            "end_date": "2026-11-01",
            "sources": [{"file": "mes.csv"}, {"file": "ehs.csv"}],
        }
        self.contract_sha256 = sha256(json.dumps(self.contract, sort_keys=True).encode("utf-8"))
        self.manifest_dir = self.project_root / "approval"
        self.manifest_dir.mkdir(parents=True)
        self.approval_path = self.manifest_dir / "approval-record.md"
        self.approval_bytes = b"OWNER-SENTINEL approved this synthetic test scope.\n"
        self.approval_path.write_bytes(self.approval_bytes)
        self.manifest_path = self.manifest_dir / "manifest.json"
        self.manifest = self.complete_manifest()

    def complete_manifest(self):
        return {
            "schema_version": 1,
            "approval_state": "approved",
            "simulation_only": False,
            "data_owner": {"name": "OWNER-SENTINEL", "title": "Synthetic test owner"},
            "approver": {"name": "APPROVER-SENTINEL", "title": "Synthetic test approver"},
            "approved_at": "2026-11-04",
            "approval_record": {
                "path": "approval-record.md",
                "sha256": sha256(self.approval_bytes),
            },
            "user_processing_authorized": True,
            "user_processing_authorized_at": "2026-11-04",
            "scope": {
                "period": "2026-W44",
                "contract_version": "metrics-v7",
                "contract_sha256": self.contract_sha256,
                "input_dir": str(self.input_dir.resolve()),
            },
            "sources": [
                {"file": filename, "sha256": sha256(content)}
                for filename, content in sorted(self.source_contents.items())
            ],
            "handling": {
                "read_only": True,
                "codex_visibility": "aggregates_only",
                "evidence_policy": "safe_metadata_and_aggregates",
                "external_sharing": False,
                "retention_days": 30,
                "cleanup_owner": "CLEANUP-SENTINEL",
            },
        }

    def write_manifest(self, manifest=None):
        value = self.manifest if manifest is None else manifest
        content = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
        self.manifest_path.write_bytes(content)
        return content

    def validate(self, manifest_path=DEFAULT_MANIFEST, period="2026-W44", input_dir=None, contract=None, contract_sha256=None):
        if manifest_path is DEFAULT_MANIFEST:
            manifest_path = self.manifest_path
        if input_dir is None:
            input_dir = self.input_dir
        if contract is None:
            contract = self.contract
        if contract_sha256 is None:
            contract_sha256 = self.contract_sha256
        return validate_preflight(
            manifest_path,
            contract,
            contract_sha256,
            period,
            input_dir,
            self.project_root,
        )

    def assert_safe_error(self, error):
        message = str(error)
        for secret in (
            "OWNER-SENTINEL",
            "APPROVER-SENTINEL",
            "CLEANUP-SENTINEL",
            "KEY-SENTINEL",
            "CASE-SENTINEL",
            "VALUE-SENTINEL",
            str(self.project_root),
            str(self.input_dir),
        ):
            self.assertNotIn(secret, message)

    def test_complete_manifest_returns_hashes_and_the_approved_byte_snapshots(self):
        manifest_bytes = self.write_manifest()

        result = self.validate()

        self.assertEqual(result["run_mode"], "real")
        self.assertEqual(result["approval_manifest_sha256"], sha256(manifest_bytes))
        self.assertEqual(result["source_hashes"], {
            filename: sha256(content) for filename, content in self.source_contents.items()
        })
        self.assertEqual(result["source_contents"], self.source_contents)

    def test_missing_manifest_is_rejected_before_any_source_file_is_opened(self):
        with patch.object(Path, "read_bytes", side_effect=AssertionError("a source file was opened")):
            with self.assertRaises(PreflightError) as raised:
                self.validate(manifest_path=None)

        self.assert_safe_error(raised.exception)

    def test_unapproved_manifest_state_is_rejected_without_leaking_identity(self):
        manifest = dict(self.manifest)
        manifest["approval_state"] = "pending"
        self.write_manifest(manifest)

        with self.assertRaises(PreflightError) as raised:
            self.validate()

        self.assert_safe_error(raised.exception)

    def test_missing_user_processing_authorization_is_rejected(self):
        manifest = dict(self.manifest)
        manifest["user_processing_authorized"] = False
        self.write_manifest(manifest)

        with self.assertRaises(PreflightError) as raised:
            self.validate()

        self.assert_safe_error(raised.exception)

    def test_unsupported_handling_policy_is_rejected(self):
        manifest = dict(self.manifest)
        manifest["handling"] = dict(self.manifest["handling"], codex_visibility="raw_rows")
        self.write_manifest(manifest)

        with self.assertRaises(PreflightError) as raised:
            self.validate()

        self.assert_safe_error(raised.exception)

    def test_wrong_period_contract_version_or_contract_hash_is_rejected(self):
        cases = (
            ("period", lambda manifest: manifest["scope"].update(period="2026-W43"), "2026-W44"),
            ("version", lambda manifest: manifest["scope"].update(contract_version="metrics-v8"), "2026-W44"),
            ("contract hash", lambda manifest: manifest["scope"].update(contract_sha256="0" * 64), "2026-W44"),
            ("requested period", lambda manifest: None, "2026-W43"),
        )
        for label, mutate, period in cases:
            with self.subTest(label=label):
                manifest = json.loads(json.dumps(self.manifest))
                mutate(manifest)
                self.write_manifest(manifest)

                with self.assertRaises(PreflightError) as raised:
                    self.validate(period=period)

                self.assert_safe_error(raised.exception)

    def test_modified_human_approval_copy_invalidates_manifest(self):
        self.write_manifest()
        self.approval_path.write_bytes(self.approval_bytes + b"changed\n")

        with self.assertRaises(PreflightError) as raised:
            self.validate()

        self.assert_safe_error(raised.exception)

    def test_unapproved_input_directory_is_rejected_without_echoing_path(self):
        self.write_manifest()
        other_input_dir = self.project_root / "PRIVATE-PATH-SENTINEL"
        other_input_dir.mkdir()

        with self.assertRaises(PreflightError) as raised:
            self.validate(input_dir=other_input_dir)

        self.assert_safe_error(raised.exception)
        self.assertNotIn("PRIVATE-PATH-SENTINEL", str(raised.exception))

    def test_missing_or_duplicate_approved_source_is_rejected(self):
        cases = ("missing", "duplicate")
        for case in cases:
            with self.subTest(case=case):
                manifest = json.loads(json.dumps(self.manifest))
                if case == "missing":
                    manifest["sources"].pop()
                else:
                    manifest["sources"].append(dict(manifest["sources"][0]))
                self.write_manifest(manifest)

                with self.assertRaises(PreflightError) as raised:
                    self.validate()

                self.assert_safe_error(raised.exception)

    def test_extra_input_file_is_rejected_before_source_bytes_are_read(self):
        self.write_manifest()
        (self.input_dir / "unexpected.csv").write_bytes(b"VALUE-SENTINEL\n")

        with self.assertRaises(PreflightError) as raised:
            self.validate()

        self.assert_safe_error(raised.exception)

    def test_nested_input_directory_is_rejected(self):
        self.write_manifest()
        (self.input_dir / "nested").mkdir()

        with self.assertRaises(PreflightError) as raised:
            self.validate()

        self.assert_safe_error(raised.exception)

    def test_symlinked_source_is_rejected(self):
        self.write_manifest()
        source = self.input_dir / "mes.csv"
        linked_source = self.input_dir / "mes-link.csv"
        source.rename(linked_source)
        source.symlink_to(linked_source.name)

        with self.assertRaises(PreflightError) as raised:
            self.validate()

        self.assert_safe_error(raised.exception)

    def test_changed_source_fingerprint_is_rejected_without_echoing_contents(self):
        self.write_manifest()
        (self.input_dir / "mes.csv").write_bytes(b"VALUE-SENTINEL-CHANGED\n")

        with self.assertRaises(PreflightError) as raised:
            self.validate()

        self.assert_safe_error(raised.exception)
        self.assertNotIn("VALUE-SENTINEL-CHANGED", str(raised.exception))

    def test_manifest_rejects_unknown_top_level_fields(self):
        manifest = dict(self.manifest, unexpected="not allowed")
        self.write_manifest(manifest)

        with self.assertRaises(PreflightError) as raised:
            self.validate()

        self.assert_safe_error(raised.exception)

    def test_contract_source_name_with_control_characters_is_rejected(self):
        contract = json.loads(json.dumps(self.contract))
        unsafe_name = "mes.csv\nOWNER-SENTINEL"
        unsafe_bytes = b"date,record_id,qty\n2026-10-26,K-001,1\n"
        (self.input_dir / "mes.csv").unlink()
        (self.input_dir / unsafe_name).write_bytes(unsafe_bytes)
        contract["sources"][0]["file"] = unsafe_name
        contract_sha256 = sha256(json.dumps(contract, sort_keys=True).encode("utf-8"))
        manifest = json.loads(json.dumps(self.manifest))
        manifest["scope"]["contract_sha256"] = contract_sha256
        manifest["sources"] = [
            {"file": "ehs.csv", "sha256": sha256(self.source_contents["ehs.csv"])},
            {"file": unsafe_name, "sha256": sha256(unsafe_bytes)},
        ]
        self.write_manifest(manifest)

        with self.assertRaises(PreflightError) as raised:
            self.validate(contract=contract, contract_sha256=contract_sha256)

        self.assert_safe_error(raised.exception)

    def test_unsafe_approval_record_path_is_rejected(self):
        manifest = dict(self.manifest)
        manifest["approval_record"] = dict(self.manifest["approval_record"], path="../approval-record.md")
        self.write_manifest(manifest)

        with self.assertRaises(PreflightError) as raised:
            self.validate()

        self.assert_safe_error(raised.exception)

    def test_simulation_contract_is_allowed_under_fixtures_without_manifest(self):
        simulation_dir = self.project_root / "fixtures" / "historical"
        simulation_dir.mkdir(parents=True)
        for filename, content in self.source_contents.items():
            (simulation_dir / filename).write_bytes(content)
        (simulation_dir / "expected.json").write_text("{\"test_only\": true}\n", encoding="utf-8")
        contract = dict(self.contract, simulation_only=True)

        result = self.validate(
            manifest_path=None,
            input_dir=simulation_dir,
            contract=contract,
        )

        self.assertEqual(result["run_mode"], "simulation")
        self.assertIsNone(result["approval_manifest_sha256"])
        self.assertEqual(result["source_contents"], self.source_contents)

    def test_simulation_contract_outside_allowed_path_is_rejected(self):
        contract = dict(self.contract, simulation_only=True)

        with self.assertRaises(PreflightError) as raised:
            self.validate(manifest_path=None, contract=contract)

        self.assert_safe_error(raised.exception)

    def test_simulation_contract_rejects_an_approval_manifest_argument(self):
        simulation_dir = self.project_root / "fixtures" / "historical"
        simulation_dir.mkdir(parents=True)
        for filename, content in self.source_contents.items():
            (simulation_dir / filename).write_bytes(content)
        self.write_manifest()

        with self.assertRaises(PreflightError) as raised:
            self.validate(input_dir=simulation_dir, contract=dict(self.contract, simulation_only=True))

        self.assert_safe_error(raised.exception)


if __name__ == "__main__":
    unittest.main()
