"""End-to-end checks for source review and the local task ledger."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
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
    def run_command(self, script, *arguments):
        return subprocess.run(
            [sys.executable, str(script), *map(str, arguments)],
            cwd=str(ROOT), capture_output=True, text=True,
        )

    def start(self, task, task_id="demo-pass"):
        return self.run_command(
            AUDIT, "start", "--task", task, "--id", task_id, "--period", "2026-W44",
        )

    def validate(self, input_dir, evidence):
        return self.run_command(
            VALIDATOR, "--period", "2026-W44", "--contract", CONTRACT,
            "--input-dir", input_dir, "--out", evidence,
        )

    def finalize(self, task, input_dir, evidence, review, contract=CONTRACT):
        return self.run_command(
            AUDIT, "finalize", "--task", task, "--contract", contract,
            "--input-dir", input_dir, "--evidence", evidence, "--review", review,
        )

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
            self.assertEqual(ledger["evidence"], str(evidence))
            self.assertEqual(ledger["evidence_sha256"], hashlib.sha256(evidence.read_bytes()).hexdigest())
            self.assertEqual(ledger["review"], str(review))
            self.assertEqual(ledger["review_sha256"], hashlib.sha256(review.read_bytes()).hexdigest())
            self.assertEqual(finding["status"], "pass")
            self.assertEqual(finding["errors"], [])
            self.assertEqual({item["path"]: item["status"] for item in finding["sources"]}, {"mes.csv": "pass", "ai_ehs.csv": "pass"})
            self.assertEqual(self.run_command(AUDIT, "verify", "--task", task).returncode, 0)

    def test_missing_source_blocks_task_with_locatable_reason(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs = root / "inputs"
            shutil.copytree(FIXTURES, inputs)
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
            inputs = root / "inputs"
            shutil.copytree(FIXTURES, inputs)
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
            inputs = root / "inputs"
            shutil.copytree(FIXTURES, inputs)
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
