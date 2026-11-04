"""End-to-end checks for source review and the local task ledger."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import source_audit

AUDIT = ROOT / "scripts" / "source_audit.py"
VALIDATOR = ROOT / "scripts" / "check_inputs.py"
CONTRACT = ROOT / "contracts" / "demo.v1.json"
FIXTURES = ROOT / "fixtures" / "demo"


def fields(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---"
    end = lines.index("---", 1)
    return dict(line.split(": ", 1) for line in lines[1:end])


class SourceAuditCliTests(unittest.TestCase):
    def copy_to_simulation_path(self, root):
        inputs = root / "simulation-only" / "inputs"
        inputs.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(FIXTURES, inputs)
        return inputs

    def create_real_mode_run(self, root):
        root = Path(root)
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        contract.pop("simulation_only", None)
        contract_bytes = (json.dumps(contract, indent=2, sort_keys=True) + "\n").encode("utf-8")
        contract_path = root / "real-contract.json"
        contract_path.write_bytes(contract_bytes)

        input_dir = root / "real-mode-input"
        input_dir.mkdir()
        for source in contract["sources"]:
            shutil.copyfile(FIXTURES / source["file"], input_dir / source["file"])

        approval_dir = root / "approval"
        approval_dir.mkdir()
        approval_bytes = b"Synthetic approval record for source-audit tests only.\n"
        (approval_dir / "approval-record.md").write_bytes(approval_bytes)
        sources = [
            {"file": source["file"], "sha256": hashlib.sha256((input_dir / source["file"]).read_bytes()).hexdigest()}
            for source in contract["sources"]
        ]
        manifest = {
            "schema_version": 1,
            "approval_state": "approved",
            "simulation_only": False,
            "data_owner": {"name": "OWNER-SENTINEL", "title": "Synthetic test only"},
            "approver": {"name": "APPROVER-SENTINEL", "title": "Synthetic test only"},
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
                "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
                "input_dir": str(input_dir.resolve()),
            },
            "sources": sources,
            "handling": {
                "read_only": True,
                "codex_visibility": "aggregates_only",
                "evidence_policy": "safe_metadata_and_aggregates",
                "external_sharing": False,
                "retention_days": 30,
                "cleanup_owner": "CLEANUP-SENTINEL",
            },
        }
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        manifest_path = approval_dir / "manifest.json"
        manifest_path.write_bytes(manifest_bytes)
        return contract_path, input_dir, manifest_path, hashlib.sha256(manifest_bytes).hexdigest()

    def run_command(self, script, *arguments):
        return subprocess.run(
            [sys.executable, str(script), *map(str, arguments)],
            cwd=str(ROOT), capture_output=True, text=True,
        )

    def start(self, task, task_id="demo-pass"):
        return self.run_command(
            AUDIT, "start", "--task", task, "--id", task_id, "--period", "2026-W44",
        )

    def validate(self, input_dir, evidence, contract=CONTRACT, manifest=None):
        arguments = [
            "--period", "2026-W44", "--contract", contract,
            "--input-dir", input_dir, "--out", evidence,
        ]
        if manifest is not None:
            arguments.extend(("--approval-manifest", manifest))
        return self.run_command(VALIDATOR, *arguments)

    def finalize(self, task, input_dir, evidence, review, contract=CONTRACT, manifest=None):
        arguments = [
            "finalize", "--task", task, "--contract", contract,
            "--input-dir", input_dir, "--evidence", evidence, "--review", review,
        ]
        if manifest is not None:
            arguments.extend(("--approval-manifest", manifest))
        return self.run_command(AUDIT, *arguments)

    def test_valid_run_moves_working_to_ready_with_verifiable_artifact_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task).returncode, 0)
            self.assertEqual(fields(task)["status"], "working")
            self.assertEqual(self.validate(FIXTURES, evidence).returncode, 0)

            result = self.finalize(task, FIXTURES, evidence, review)
            self.assertEqual(result.returncode, 0, result.stderr)
            ledger = fields(task)
            finding = json.loads(review.read_text(encoding="utf-8"))
            self.assertEqual(ledger["status"], "ready")
            self.assertEqual(ledger["run_mode"], "simulation")
            self.assertEqual(ledger["approval_manifest_sha256"], "none")
            self.assertEqual(ledger["evidence"], "evidence.json")
            self.assertEqual(ledger["evidence_sha256"], hashlib.sha256(evidence.read_bytes()).hexdigest())
            self.assertEqual(ledger["review"], "review.json")
            self.assertEqual(ledger["review_sha256"], hashlib.sha256(review.read_bytes()).hexdigest())
            self.assertEqual(finding["status"], "pass")
            self.assertEqual(finding["run_mode"], "simulation")
            self.assertIsNone(finding["approval_manifest_sha256"])
            self.assertIsNone(finding["approval_manifest"])
            self.assertEqual(finding["errors"], [])
            self.assertEqual({item["path"]: item["status"] for item in finding["sources"]}, {"mes.csv": "pass", "ai_ehs.csv": "pass"})
            self.assertEqual(self.run_command(AUDIT, "verify", "--task", task).returncode, 0)

    def test_real_mode_manifest_hash_is_bound_without_tracking_private_details(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            contract, inputs, manifest, manifest_hash = self.create_real_mode_run(root)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "real-manifest").returncode, 0)
            self.assertEqual(self.validate(inputs, evidence, contract, manifest).returncode, 0)

            result = self.finalize(task, inputs, evidence, review, contract, manifest)

            self.assertEqual(result.returncode, 0, result.stderr)
            ledger_text = task.read_text(encoding="utf-8")
            ledger = fields(task)
            finding = json.loads(review.read_text(encoding="utf-8"))
            self.assertEqual(ledger["status"], "ready")
            self.assertEqual(ledger["run_mode"], "real")
            self.assertEqual(ledger["approval_manifest_sha256"], manifest_hash)
            self.assertNotIn(str(manifest), ledger_text)
            self.assertNotIn("OWNER-SENTINEL", ledger_text)
            self.assertNotIn("APPROVER-SENTINEL", ledger_text)
            self.assertEqual(finding["run_mode"], "real")
            self.assertEqual(finding["approval_manifest"], str(manifest.absolute()))
            self.assertEqual(finding["approval_manifest_sha256"], manifest_hash)
            self.assertEqual(self.run_command(AUDIT, "verify", "--task", task).returncode, 0)

    def test_finalize_rejects_evidence_and_review_paths_inside_protected_inputs(self):
        for artifact_kind in ("evidence", "review"):
            with self.subTest(artifact=artifact_kind), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                contract, inputs, manifest, _ = self.create_real_mode_run(root)
                task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
                self.assertEqual(self.start(task, "real-protected-artifact-" + artifact_kind).returncode, 0)
                if artifact_kind == "evidence":
                    self.assertEqual(self.validate(inputs, evidence, contract, manifest).returncode, 0)
                    evidence = inputs / "mes.csv"
                    original = evidence.read_bytes()
                else:
                    self.assertEqual(self.validate(inputs, evidence, contract, manifest).returncode, 0)
                    review = inputs / "source-review.json"
                    original = (inputs / "mes.csv").read_bytes()

                result = self.finalize(task, inputs, evidence, review, contract, manifest)

                self.assertEqual(result.returncode, 2)
                self.assertEqual(fields(task)["status"], "working")
                self.assertFalse(review.exists())
                self.assertEqual((inputs / "mes.csv").read_bytes(), original)
                self.assertNotIn(str(root), result.stderr)

    def test_real_mode_without_manifest_stays_blocked_without_source_review_hashes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            contract, inputs, manifest, _ = self.create_real_mode_run(root)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "real-missing-manifest").returncode, 0)
            self.assertEqual(self.validate(inputs, evidence, contract).returncode, 2)
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertEqual(payload["inputs"], [])
            self.assertEqual(payload["metrics"], {})

            result = self.finalize(task, inputs, evidence, review, contract)

            self.assertEqual(result.returncode, 2, result.stderr)
            ledger_text = task.read_text(encoding="utf-8")
            ledger = fields(task)
            finding = json.loads(review.read_text(encoding="utf-8"))
            self.assertEqual(ledger["status"], "blocked")
            self.assertEqual(ledger["run_mode"], "real")
            self.assertEqual(ledger["approval_manifest_sha256"], "none")
            self.assertNotIn(str(manifest), ledger_text)
            self.assertEqual(finding["sources"], [])
            self.assertEqual(self.run_command(AUDIT, "verify", "--task", task).returncode, 0)

    def test_simulation_finalize_rejects_an_approval_manifest_argument(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs = self.copy_to_simulation_path(root)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            manifest = root / "approval" / "unrelated-manifest.json"
            self.assertEqual(self.start(task, "simulation-with-manifest").returncode, 0)
            self.assertEqual(self.validate(inputs, evidence).returncode, 0)

            result = self.finalize(task, inputs, evidence, review, manifest=manifest)

            self.assertEqual(result.returncode, 2)
            self.assertIn("simulation runs must not use an approval manifest", result.stderr)
            self.assertEqual(fields(task)["status"], "working")
            self.assertFalse(review.exists())

    def test_changed_manifest_after_validation_blocks_source_finalization(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            contract, inputs, manifest, _ = self.create_real_mode_run(root)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "real-changed-manifest").returncode, 0)
            self.assertEqual(self.validate(inputs, evidence, contract, manifest).returncode, 0)
            manifest.write_bytes(manifest.read_bytes() + b"\n")

            result = self.finalize(task, inputs, evidence, review, contract, manifest)

            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(fields(task)["status"], "blocked")
            finding = json.loads(review.read_text(encoding="utf-8"))
            self.assertTrue(any("deterministic validation" in error for error in finding["errors"]))

    def test_changed_manifest_after_finalization_invalidates_source_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            contract, inputs, manifest, _ = self.create_real_mode_run(root)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "real-manifest-changed-later").returncode, 0)
            self.assertEqual(self.validate(inputs, evidence, contract, manifest).returncode, 0)
            self.assertEqual(self.finalize(task, inputs, evidence, review, contract, manifest).returncode, 0)
            manifest.write_bytes(manifest.read_bytes() + b"\n")

            result = self.run_command(AUDIT, "verify", "--task", task)

            self.assertEqual(result.returncode, 2)
            self.assertIn("approval manifest fingerprint mismatch", result.stderr)

    def test_missing_source_blocks_task_with_locatable_reason(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs = self.copy_to_simulation_path(root)
            (inputs / "ai_ehs.csv").unlink()
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "demo-missing").returncode, 0)
            self.assertEqual(self.validate(inputs, evidence).returncode, 2)

            result = self.finalize(task, inputs, evidence, review)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(fields(task)["status"], "blocked")
            finding = json.loads(review.read_text(encoding="utf-8"))
            self.assertEqual(finding["status"], "blocked")
            self.assertTrue(any("ai_ehs.csv" in error and "missing" in error for error in finding["errors"]))
            self.assertIn("ai_ehs.csv", task.read_text(encoding="utf-8"))
            self.assertEqual(self.run_command(AUDIT, "verify", "--task", task).returncode, 0)

    def assert_invalid_contract_task_can_be_verified(self, contract, task_id):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs = self.copy_to_simulation_path(root)
            task = root / "task.md"
            evidence = root / "evidence.json"
            review = root / "review.json"
            self.assertEqual(self.start(task, task_id).returncode, 0)
            self.assertEqual(self.validate(inputs, evidence, contract).returncode, 2)

            result = self.finalize(task, inputs, evidence, review, contract)

            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(fields(task)["status"], "blocked")
            self.assertEqual(fields(task)["run_mode"], "unknown")
            verified = self.run_command(AUDIT, "verify", "--task", task)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            review.write_bytes(review.read_bytes() + b"\n")
            tampered = self.run_command(AUDIT, "verify", "--task", task)
            self.assertEqual(tampered.returncode, 2)
            self.assertIn("review fingerprint mismatch", tampered.stderr)

    def test_unreadable_contract_blocked_task_can_be_verified(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            contract = Path(temp_dir) / "invalid-contract.json"
            contract.write_text("{", encoding="utf-8")
            self.assert_invalid_contract_task_can_be_verified(contract, "invalid-contract")

    def test_missing_contract_blocked_task_can_be_verified(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            contract = Path(temp_dir) / "missing-contract.json"
            self.assert_invalid_contract_task_can_be_verified(contract, "missing-contract")

    def test_changed_evidence_after_finalization_invalidates_task_link(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task).returncode, 0)
            self.assertEqual(self.validate(FIXTURES, evidence).returncode, 0)
            self.assertEqual(self.finalize(task, FIXTURES, evidence, review).returncode, 0)
            evidence.write_bytes(evidence.read_bytes() + b"\n")

            result = self.run_command(AUDIT, "verify", "--task", task)
            self.assertEqual(result.returncode, 2)
            self.assertIn("evidence fingerprint mismatch", result.stderr)

    def test_changed_source_after_validation_blocks_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs = self.copy_to_simulation_path(root)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "demo-changed").returncode, 0)
            self.assertEqual(self.validate(inputs, evidence).returncode, 0)
            with (inputs / "mes.csv").open("a", encoding="utf-8") as stream:
                stream.write("2026-10-28,M-003,5\n")

            result = self.finalize(task, inputs, evidence, review)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(fields(task)["status"], "blocked")
            finding = json.loads(review.read_text(encoding="utf-8"))
            self.assertTrue(any("mes.csv" in error and "fingerprint mismatch" in error for error in finding["errors"]))

    def test_changed_source_after_finalization_invalidates_source_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs = self.copy_to_simulation_path(root)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "demo-changed-after-finalize").returncode, 0)
            self.assertEqual(self.validate(inputs, evidence).returncode, 0)
            self.assertEqual(self.finalize(task, inputs, evidence, review).returncode, 0)
            with (inputs / "mes.csv").open("a", encoding="utf-8") as stream:
                stream.write("2026-10-28,M-003,5\n")

            result = self.run_command(AUDIT, "verify", "--task", task)

            self.assertEqual(result.returncode, 2)
            self.assertIn("mes.csv: fingerprint mismatch", result.stderr)

    def test_changed_contract_with_same_version_blocks_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            contract = root / "contract.json"
            shutil.copy(CONTRACT, contract)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "demo-contract").returncode, 0)
            self.assertEqual(self.validate(FIXTURES, evidence).returncode, 0)
            contract.write_bytes(CONTRACT.read_bytes() + b"\n")

            result = self.finalize(task, FIXTURES, evidence, review, contract)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(fields(task)["status"], "blocked")
            finding = json.loads(review.read_text(encoding="utf-8"))
            self.assertTrue(any("contract" in error and "fingerprint mismatch" in error for error in finding["errors"]))

    def test_blocked_evidence_cannot_be_promoted_by_editing_status_and_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs = self.copy_to_simulation_path(root)
            with (inputs / "mes.csv").open("a", encoding="utf-8") as stream:
                stream.write("2026-11-02,M-003,5\n")
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "demo-tampered").returncode, 0)
            self.assertEqual(self.validate(inputs, evidence).returncode, 2)
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            payload["status"] = "pass"
            payload["errors"] = []
            payload["metrics"] = {}
            evidence.write_text(json.dumps(payload), encoding="utf-8")

            result = self.finalize(task, inputs, evidence, review)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(fields(task)["status"], "blocked")
            finding = json.loads(review.read_text(encoding="utf-8"))
            self.assertTrue(any("evidence" in error and "deterministic validation" in error for error in finding["errors"]))

    def test_untrusted_evidence_error_text_is_not_copied_into_task_or_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs = self.copy_to_simulation_path(root)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "demo-private-evidence-error").returncode, 0)
            self.assertEqual(self.validate(inputs, evidence).returncode, 0)
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            payload["status"] = "blocked"
            payload["errors"] = ["OWNER-SENTINEL /private/approved/manifest.json"]
            payload["inputs"].extend([
                {"path": "/private/approved/OWNER-SENTINEL.csv", "sha256": "0" * 64, "rows": 1},
                {"path": "/private/approved/OWNER-SENTINEL.csv", "sha256": "0" * 64, "rows": 1},
            ])
            evidence.write_text(json.dumps(payload), encoding="utf-8")

            result = self.finalize(task, inputs, evidence, review)

            self.assertEqual(result.returncode, 2)
            task_body = task.read_text(encoding="utf-8").split("# Source audit:", 1)[1]
            review_text = review.read_text(encoding="utf-8")
            for secret in (
                "OWNER-SENTINEL",
                "/private/approved/manifest.json",
                "/private/approved/OWNER-SENTINEL.csv",
            ):
                self.assertNotIn(secret, task_body)
                self.assertNotIn(secret, review_text)

    def test_missing_evidence_error_does_not_echo_local_path_into_task_body(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs = self.copy_to_simulation_path(root)
            task, evidence, review = root / "task.md", root / "missing-private-evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "demo-private-evidence-path").returncode, 0)

            result = self.finalize(task, inputs, evidence, review)

            self.assertEqual(result.returncode, 2)
            task_body = task.read_text(encoding="utf-8").split("# Source audit:", 1)[1]
            self.assertNotIn(str(root), task_body)
            self.assertIn("evidence is unavailable or invalid", task_body)

    def test_validator_failure_does_not_echo_absolute_stderr(self):
        errors = []
        secret_path = "/private/tmp/SYNTHETIC-LOCAL-PATH/check_inputs.py"
        completed = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=secret_path)
        with mock.patch.object(source_audit.subprocess, "run", return_value=completed):
            result = source_audit.regenerated_evidence("2026-W44", CONTRACT, FIXTURES, errors)

        self.assertIsNone(result)
        self.assertTrue(any("could not reproduce evidence" in error for error in errors))
        self.assertNotIn(secret_path, " ".join(errors))

    def test_blocked_outputs_redact_record_key_date_and_absolute_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs = self.copy_to_simulation_path(root)
            with (inputs / "mes.csv").open("a", encoding="utf-8") as stream:
                stream.write("2026-11-02,SYNTHETIC-PRIVATE-KEY,20\n")
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task, "demo-redacted").returncode, 0)
            self.assertEqual(self.validate(inputs, evidence).returncode, 2)

            result = self.finalize(task, inputs, evidence, review)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(fields(task)["status"], "blocked")
            self.assertEqual(self.run_command(AUDIT, "verify", "--task", task).returncode, 0)

            outputs = evidence.read_text(encoding="utf-8") + review.read_text(encoding="utf-8") + task.read_text(encoding="utf-8")
            self.assertNotIn("SYNTHETIC-PRIVATE-KEY", outputs)
            self.assertNotIn("2026-11-02", outputs)
            self.assertNotIn(str(root), outputs)

    def test_finalized_task_cannot_be_rewritten_with_another_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task, evidence, review = root / "task.md", root / "evidence.json", root / "review.json"
            self.assertEqual(self.start(task).returncode, 0)
            self.assertEqual(self.validate(FIXTURES, evidence).returncode, 0)
            self.assertEqual(self.finalize(task, FIXTURES, evidence, review).returncode, 0)
            original_task = task.read_bytes()
            original_review = review.read_bytes()

            result = self.finalize(task, FIXTURES, evidence, review)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(task.read_bytes(), original_task)
            self.assertEqual(review.read_bytes(), original_review)


if __name__ == "__main__":
    unittest.main()
