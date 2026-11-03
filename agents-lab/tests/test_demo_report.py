"""CLI behavior for synthetic weekly draft and independent review."""

import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stderr
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SOURCE_AUDIT = ROOT / "scripts" / "source_audit.py"
INPUT_CHECK = ROOT / "scripts" / "check_inputs.py"
WRITER = ROOT / "scripts" / "draft_demo_report.py"
REVIEWER = ROOT / "scripts" / "review_demo_report.py"
DECISION = ROOT / "scripts" / "record_draft_decision.py"
CONTRACT = ROOT / "contracts" / "demo.v1.json"
FIXTURES = ROOT / "fixtures" / "demo"


def task_fields(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    end = lines.index("---", 1)
    return dict(line.split(": ", 1) for line in lines[1:end])


class DemoReportCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source_task = self.root / "source-task.md"
        self.evidence = self.root / "source-evidence.json"
        self.source_review = self.root / "source-review.json"
        self.draft_task = self.root / "draft-task.md"
        self.draft = self.root / "draft.md"
        self.draft_review = self.root / "draft-review.json"

    def run_cli(self, script, *args):
        return subprocess.run(
            [sys.executable, str(script), *map(str, args)],
            cwd=str(ROOT), capture_output=True, text=True,
        )

    def source_run(self, input_dir=FIXTURES):
        self.assertEqual(self.run_cli(
            SOURCE_AUDIT, "start", "--task", self.source_task,
            "--id", "demo-source", "--period", "2026-W44",
        ).returncode, 0)
        checked = self.run_cli(
            INPUT_CHECK, "--period", "2026-W44", "--contract", CONTRACT,
            "--input-dir", input_dir, "--out", self.evidence,
        )
        reviewed = self.run_cli(
            SOURCE_AUDIT, "finalize", "--task", self.source_task,
            "--contract", CONTRACT, "--input-dir", input_dir,
            "--evidence", self.evidence, "--review", self.source_review,
        )
        return checked, reviewed

    def write_draft(self):
        return self.run_cli(
            WRITER, "--source-task", self.source_task, "--task", self.draft_task,
            "--draft", self.draft, "--id", "demo-draft",
        )

    def review_draft(self):
        return self.run_cli(
            REVIEWER, "--task", self.draft_task, "--out", self.draft_review,
        )

    def record_decision(self, decision="accepted", out=None, reason=None, draft_task=None):
        out = out or (self.root / "draft-decision.md")
        args = [
            "record", "--draft-task", draft_task or self.draft_task,
            "--decision", decision, "--out", out,
        ]
        if reason is not None:
            args.extend(("--reason", reason))
        return self.run_cli(DECISION, *args)

    def verify_decision(self, record):
        return self.run_cli(DECISION, "verify", "--record", record)

    def set_task_field(self, path, name, value):
        lines = path.read_text(encoding="utf-8").splitlines()
        prefix = name + ": "
        for index, line in enumerate(lines):
            if line.startswith(prefix):
                lines[index] = prefix + str(value)
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return
        self.fail("task field {!r} is missing".format(name))

    def load_decision_module(self):
        scripts_dir = str(ROOT / "scripts")
        sys.path.insert(0, scripts_dir)
        try:
            spec = importlib.util.spec_from_file_location("decision_cli_for_test", DECISION)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        finally:
            sys.path.remove(scripts_dir)

    def test_ready_source_produces_evidence_bound_draft_with_missing_values(self):
        checked, reviewed = self.source_run()
        self.assertEqual((checked.returncode, reviewed.returncode), (0, 0))

        result = self.write_draft()
        self.assertEqual(result.returncode, 0, result.stderr)
        content = self.draft.read_text(encoding="utf-8")
        self.assertIn("| output_qty | 30 | pieces | mes.csv |", content)
        self.assertIn("| case_count | 1 | cases | ai_ehs.csv |", content)
        self.assertIn("上周产量：—", content)
        self.assertIn("产量环比：—", content)
        self.assertIn("证据文件：{}".format(self.evidence), content)
        self.assertIn("证据 SHA-256：{}".format(hashlib.sha256(self.evidence.read_bytes()).hexdigest()), content)
        self.assertEqual(task_fields(self.draft_task)["status"], "working")

    def test_consistent_draft_review_becomes_ready_but_not_accepted(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)

        result = self.review_draft()
        self.assertEqual(result.returncode, 0, result.stderr)
        fields = task_fields(self.draft_task)
        finding = json.loads(self.draft_review.read_text(encoding="utf-8"))
        self.assertEqual(fields["status"], "ready")
        self.assertEqual(fields["draft_sha256"], hashlib.sha256(self.draft.read_bytes()).hexdigest())
        self.assertEqual(fields["review_sha256"], hashlib.sha256(self.draft_review.read_bytes()).hexdigest())
        self.assertEqual(finding["status"], "pass")
        self.assertEqual(finding["errors"], [])
        self.assertNotIn("Accepted", self.draft_task.read_text(encoding="utf-8"))

    def test_wrong_number_is_returned_with_metric_and_line(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        content = self.draft.read_text(encoding="utf-8")
        self.draft.write_text(content.replace("| output_qty | 30 |", "| output_qty | 31 |", 1), encoding="utf-8")

        result = self.review_draft()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(task_fields(self.draft_task)["status"], "blocked")
        finding = json.loads(self.draft_review.read_text(encoding="utf-8"))
        self.assertTrue(any("output_qty" in error and "line" in error and "31" in error for error in finding["errors"]))

    def test_wrong_unit_is_returned_with_metric_and_line(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        content = self.draft.read_text(encoding="utf-8")
        self.draft.write_text(content.replace("| output_qty | 30 | pieces |", "| output_qty | 30 | cases |", 1), encoding="utf-8")

        result = self.review_draft()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(task_fields(self.draft_task)["status"], "blocked")
        finding = json.loads(self.draft_review.read_text(encoding="utf-8"))
        self.assertTrue(any("output_qty unit" in error and "line" in error for error in finding["errors"]))

    def test_unreviewed_numeric_claim_outside_metric_table_is_returned(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        with self.draft.open("a", encoding="utf-8") as stream:
            stream.write("本周另有 999 件。\n")

        result = self.review_draft()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(task_fields(self.draft_task)["status"], "blocked")
        finding = json.loads(self.draft_review.read_text(encoding="utf-8"))
        self.assertTrue(any("line" in error and "unreviewed numeric claim" in error for error in finding["errors"]))

    def test_changed_draft_after_passing_review_invalidates_ready_record(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        self.assertEqual(self.run_cli(REVIEWER, "verify", "--task", self.draft_task).returncode, 0)
        with self.draft.open("a", encoding="utf-8") as stream:
            stream.write("Changed after review.\n")

        result = self.run_cli(REVIEWER, "verify", "--task", self.draft_task)
        self.assertEqual(result.returncode, 2)
        self.assertIn("draft fingerprint mismatch", result.stderr)

    def test_missing_evidence_reference_is_returned(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        content = self.draft.read_text(encoding="utf-8")
        self.draft.write_text("\n".join(line for line in content.splitlines() if not line.startswith("证据文件：")) + "\n", encoding="utf-8")

        result = self.review_draft()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(task_fields(self.draft_task)["status"], "blocked")
        finding = json.loads(self.draft_review.read_text(encoding="utf-8"))
        self.assertTrue(any("证据文件" in error for error in finding["errors"]))

    def test_evidence_removed_after_drafting_blocks_review_with_record(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.evidence.unlink()

        result = self.review_draft()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(task_fields(self.draft_task)["status"], "blocked")
        finding = json.loads(self.draft_review.read_text(encoding="utf-8"))
        self.assertTrue(any("evidence" in error and "missing" in error for error in finding["errors"]))

    def test_invented_previous_week_value_is_returned(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        content = self.draft.read_text(encoding="utf-8")
        self.draft.write_text(content.replace("上周产量：—", "上周产量：25", 1), encoding="utf-8")

        result = self.review_draft()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertTrue(self.draft_review.exists())
        finding = json.loads(self.draft_review.read_text(encoding="utf-8"))
        self.assertTrue(any("上周产量" in error for error in finding["errors"]))

    def test_blocked_source_task_cannot_generate_a_draft(self):
        inputs = self.root / "inputs"
        shutil.copytree(FIXTURES, inputs)
        (inputs / "ai_ehs.csv").unlink()
        checked, reviewed = self.source_run(inputs)
        self.assertEqual((checked.returncode, reviewed.returncode), (2, 2))
        self.assertEqual(self.run_cli(SOURCE_AUDIT, "verify", "--task", self.source_task).returncode, 0)

        result = self.write_draft()
        self.assertEqual(result.returncode, 2)
        self.assertIn("source task is blocked", result.stderr)
        self.assertFalse(self.draft.exists())
        self.assertFalse(self.draft_task.exists())

    def test_acceptance_record_binds_reviewed_draft_and_evidence(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        record = self.root / "draft-decision.md"

        result = self.record_decision(out=record)

        self.assertEqual(result.returncode, 0, result.stderr)
        fields = task_fields(record)
        self.assertEqual(fields["status"], "decided")
        self.assertEqual(fields["decision"], "accepted")
        self.assertEqual(fields["draft_task_id"], "demo-draft")
        self.assertEqual(fields["draft_sha256"], hashlib.sha256(self.draft.read_bytes()).hexdigest())
        self.assertEqual(fields["evidence_sha256"], hashlib.sha256(self.evidence.read_bytes()).hexdigest())
        self.assertEqual(task_fields(self.draft_task)["status"], "ready")
        self.assertEqual(self.verify_decision(record).returncode, 0)

    def test_returned_decision_requires_and_records_reason(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)

        for reason in (None, " \t "):
            record = self.root / ("missing-reason-{}.md".format("none" if reason is None else "blank"))
            result = self.record_decision("returned", out=record, reason=reason)
            self.assertEqual(result.returncode, 2)
            self.assertIn("reason", result.stderr)
            self.assertFalse(record.exists())

        record = self.root / "returned-decision.md"
        result = self.record_decision("returned", out=record, reason="Metric needs owner review.")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Metric needs owner review.", record.read_text(encoding="utf-8"))
        self.assertEqual(task_fields(record)["decision"], "returned")
        self.assertEqual(self.verify_decision(record).returncode, 0)

    def test_unreviewed_draft_cannot_be_accepted(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        record = self.root / "unreviewed-decision.md"

        result = self.record_decision(out=record)

        self.assertEqual(result.returncode, 2)
        self.assertIn("ready draft required", result.stderr)
        self.assertFalse(record.exists())

    def test_blocked_draft_cannot_be_accepted(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        content = self.draft.read_text(encoding="utf-8")
        self.draft.write_text(content.replace("| output_qty | 30 |", "| output_qty | 31 |", 1), encoding="utf-8")
        self.assertEqual(self.review_draft().returncode, 2)
        self.assertEqual(task_fields(self.draft_task)["status"], "blocked")
        record = self.root / "blocked-decision.md"

        result = self.record_decision(out=record)

        self.assertEqual(result.returncode, 2)
        self.assertIn("ready draft required", result.stderr)
        self.assertFalse(record.exists())

    def test_changed_draft_invalidates_decision(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        record = self.root / "draft-decision.md"
        self.assertEqual(self.record_decision(out=record).returncode, 0)
        with self.draft.open("a", encoding="utf-8") as stream:
            stream.write("Changed after decision.\n")

        result = self.verify_decision(record)

        self.assertEqual(result.returncode, 2)
        self.assertIn("fingerprint", result.stderr)

    def test_changed_evidence_invalidates_decision(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        record = self.root / "draft-decision.md"
        self.assertEqual(self.record_decision(out=record).returncode, 0)
        self.evidence.write_bytes(self.evidence.read_bytes() + b" ")

        result = self.verify_decision(record)

        self.assertEqual(result.returncode, 2)
        self.assertIn("fingerprint", result.stderr)

    def test_draft_evidence_path_mismatch_blocks_decision_record(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        self.set_task_field(self.draft_task, "evidence", self.root / "unrelated-evidence.json")
        record = self.root / "mismatched-evidence-decision.md"

        result = self.record_decision(out=record)

        self.assertEqual(result.returncode, 2)
        self.assertIn("evidence", result.stderr)
        self.assertFalse(record.exists())

    def test_draft_changed_after_verification_is_not_accepted(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        record = self.root / "racing-decision.md"
        module = self.load_decision_module()
        real_verify = module.verify_draft_task

        def verify_then_save(args):
            real_verify(args)
            with self.draft.open("a", encoding="utf-8") as stream:
                stream.write("Saved after review.\n")

        with mock.patch.object(module, "verify_draft_task", side_effect=verify_then_save):
            with mock.patch.object(sys, "argv", [str(DECISION), "record", "--draft-task", str(self.draft_task), "--decision", "accepted", "--out", str(record)]):
                error = io.StringIO()
                with redirect_stderr(error):
                    exit_code = module.main()

        self.assertEqual(exit_code, 2, error.getvalue())
        self.assertIn("draft fingerprint", error.getvalue())
        self.assertFalse(record.exists())

    def test_evidence_changed_after_verification_is_not_accepted(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        record = self.root / "evidence-race-decision.md"
        module = self.load_decision_module()
        real_verify = module.verify_draft_task

        def verify_then_change_evidence(args):
            real_verify(args)
            self.evidence.write_bytes(self.evidence.read_bytes() + b" ")

        with mock.patch.object(module, "verify_draft_task", side_effect=verify_then_change_evidence):
            with mock.patch.object(sys, "argv", [str(DECISION), "record", "--draft-task", str(self.draft_task), "--decision", "accepted", "--out", str(record)]):
                error = io.StringIO()
                with redirect_stderr(error):
                    exit_code = module.main()

        self.assertEqual(exit_code, 2, error.getvalue())
        self.assertIn("evidence fingerprint", error.getvalue())
        self.assertFalse(record.exists())

    def test_review_changed_after_verification_is_not_accepted(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        record = self.root / "review-race-decision.md"
        module = self.load_decision_module()
        real_verify = module.verify_draft_task

        def verify_then_change_review(args):
            real_verify(args)
            self.draft_review.write_bytes(self.draft_review.read_bytes() + b" ")

        with mock.patch.object(module, "verify_draft_task", side_effect=verify_then_change_review):
            with mock.patch.object(sys, "argv", [str(DECISION), "record", "--draft-task", str(self.draft_task), "--decision", "accepted", "--out", str(record)]):
                error = io.StringIO()
                with redirect_stderr(error):
                    exit_code = module.main()

        self.assertEqual(exit_code, 2, error.getvalue())
        self.assertIn("review fingerprint", error.getvalue())
        self.assertFalse(record.exists())

    def test_draft_task_changed_after_verification_is_not_accepted(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        record = self.root / "task-race-decision.md"
        module = self.load_decision_module()
        real_verify = module.verify_draft_task

        def verify_then_block_task(args):
            real_verify(args)
            self.set_task_field(self.draft_task, "status", "blocked")

        with mock.patch.object(module, "verify_draft_task", side_effect=verify_then_block_task):
            with mock.patch.object(sys, "argv", [str(DECISION), "record", "--draft-task", str(self.draft_task), "--decision", "accepted", "--out", str(record)]):
                error = io.StringIO()
                with redirect_stderr(error):
                    exit_code = module.main()

        self.assertEqual(exit_code, 2, error.getvalue())
        self.assertIn("draft task changed during verification", error.getvalue())
        self.assertFalse(record.exists())

    def test_draft_task_body_changed_after_verification_is_not_accepted(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        record = self.root / "task-body-race-decision.md"
        module = self.load_decision_module()
        real_verify = module.verify_draft_task

        def verify_then_edit_task_body(args):
            real_verify(args)
            with self.draft_task.open("a", encoding="utf-8") as stream:
                stream.write("\n## Notes\nChanged after verification.\n")

        with mock.patch.object(module, "verify_draft_task", side_effect=verify_then_edit_task_body):
            with mock.patch.object(sys, "argv", [str(DECISION), "record", "--draft-task", str(self.draft_task), "--decision", "accepted", "--out", str(record)]):
                error = io.StringIO()
                with redirect_stderr(error):
                    exit_code = module.main()

        self.assertEqual(exit_code, 2, error.getvalue())
        self.assertIn("draft task changed during verification", error.getvalue())
        self.assertFalse(record.exists())

    def test_returned_record_with_empty_reason_section_does_not_verify(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        record = self.root / "returned-decision.md"
        self.assertEqual(self.record_decision("returned", out=record, reason="Needs owner review.").returncode, 0)
        content = record.read_text(encoding="utf-8")
        content = content.replace(
            "## Reason\n\nNeeds owner review.\n",
            "## Reason\n\n## Notes\nNo reason was supplied.\n",
        )
        record.write_text(content, encoding="utf-8")

        result = self.verify_decision(record)

        self.assertEqual(result.returncode, 2)
        self.assertIn("reason", result.stderr)

    def test_ready_draft_with_invalidated_review_cannot_be_accepted(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        with self.draft_review.open("a", encoding="utf-8") as stream:
            stream.write("Changed after review.\n")
        record = self.root / "invalid-review-decision.md"

        result = self.record_decision(out=record)

        self.assertEqual(result.returncode, 2)
        self.assertIn("review fingerprint mismatch", result.stderr)
        self.assertFalse(record.exists())

    def test_existing_decision_record_is_not_overwritten(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        record = self.root / "draft-decision.md"
        self.assertEqual(self.record_decision(out=record).returncode, 0)
        original = record.read_bytes()

        result = self.record_decision(out=record)

        self.assertEqual(result.returncode, 2)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(record.read_bytes(), original)

    def test_invalid_decision_and_malformed_record_fail(self):
        self.source_run()
        self.assertEqual(self.write_draft().returncode, 0)
        self.assertEqual(self.review_draft().returncode, 0)
        invalid = self.record_decision("approved", out=self.root / "invalid.md")
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("invalid choice", invalid.stderr)
        self.assertFalse((self.root / "invalid.md").exists())

        malformed = self.root / "malformed.md"
        malformed.write_text("not a decision record\n", encoding="utf-8")
        result = self.verify_decision(malformed)
        self.assertEqual(result.returncode, 2)
        self.assertIn("frontmatter", result.stderr)


if __name__ == "__main__":
    unittest.main()
