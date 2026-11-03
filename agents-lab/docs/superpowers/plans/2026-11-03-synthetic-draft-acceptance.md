# Synthetic Draft Acceptance Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Let a person record and verify an explicit accepted or returned decision for a reviewed synthetic draft, tied to its exact draft and evidence fingerprints.

**Architecture:** Add a small CLI with `record` and `verify` commands. It writes a separate immutable Markdown decision task so existing `ready` draft tasks and review hashes remain unchanged. A decision can be recorded only after the existing draft verifier passes.

**Tech Stack:** Python 3.9+ standard library; `unittest`; existing task frontmatter and artifact verification conventions.

**Spec:** `docs/superpowers/specs/2026-11-03-synthetic-draft-acceptance-design.md`

## Global Constraints

- Use synthetic `2026-W44` artifacts only; do not read or import real historical data.
- Do not create an acceptance record for the committed demo draft as part of implementation.
- Do not send or publish a report; keep Ticket 04 blocked by Ticket 03.
- Keep reviewed draft tasks immutable and `ready`; decision records use a new tracked task path.
- A `returned` decision requires a human-readable reason; an existing output path is never overwritten.

## File Map

- Create `scripts/record_draft_decision.py` for decision creation and verification.
- Extend `tests/test_demo_report.py` with CLI coverage using its existing temporary synthetic workflow.
- Update `README.md` and `tasks/README.md` with the explicit decision workflow.
- Create `.scratch/weekly-report-pilot/issues/10-synthetic-draft-acceptance-gate.md` and update `STATUS.md` to keep the real-data blockers clear.

## Review Focus

- A draft task that is `working` or `blocked`, or whose review verification fails, must not produce a decision record; cover ready-state enforcement and verification.
- A changed draft or evidence artifact must invalidate a previously recorded decision; cover both artifact mutations.
- A `returned` decision without a nonblank reason must fail without creating a record; cover missing and whitespace-only reasons.
- An existing decision record must remain byte-for-byte unchanged; cover refusal to overwrite.
- Invalid decision values and malformed decision records must fail with a nonzero exit; cover invalid choice and record parsing.

---

### Task 1: Record and verify synthetic draft decisions

**Files:**
- Create: `scripts/record_draft_decision.py`
- Modify: `tests/test_demo_report.py`
- Modify: `README.md`, `tasks/README.md`, `STATUS.md`
- Create: `.scratch/weekly-report-pilot/issues/10-synthetic-draft-acceptance-gate.md`

**Interfaces:**
- Consumes: `review_demo_report.verify_draft_task(args)` and `source_audit.read_task(path)`.
- Produces: CLI `record --draft-task PATH --decision accepted|returned --out PATH [--reason TEXT]` and `verify --record PATH`.
- Decision frontmatter fields: `id`, `period`, `status: decided`, `decision`, `draft_task`, `draft_task_id`, `draft_sha256`, `evidence`, `evidence_sha256`; returned records include a reason in the Markdown body.

- [x] **Step 1: Add failing CLI tests** to `DemoReportCliTests`:
  - `test_acceptance_record_binds_reviewed_draft_and_evidence`: record `accepted`; assert `status == decided`, `decision == accepted`, draft/evidence hashes match current bytes, original draft task remains `ready`, and `verify` exits `0`.
  - `test_returned_decision_requires_and_records_reason`: missing or whitespace-only reason exits `2` and creates no record; a nonblank reason records `returned` and verifies.
  - `test_unreviewed_draft_cannot_be_accepted` and `test_blocked_draft_cannot_be_accepted`: both states exit `2` and create no record.
  - `test_changed_draft_invalidates_decision` and `test_changed_evidence_invalidates_decision`: after a valid decision, changing either linked artifact makes `verify` exit `2`.
  - `test_existing_decision_record_is_not_overwritten`: a second record attempt exits `2` and leaves original bytes unchanged.
  - `test_invalid_decision_and_malformed_record_fail`: invalid decision and malformed frontmatter exit `2`.

- [x] **Step 2: Run the draft-decision tests and observe the failures**

  Run: `python3 tests/test_demo_report.py`

  Expected: existing draft tests pass; each new decision test fails on the missing decision CLI or its required decision-specific result. Fix any test setup errors before implementing the CLI.

- [x] **Step 3: Implement the CLI** in `scripts/record_draft_decision.py`.

  `record` must require a `ready` draft, call the existing draft verifier, require a nonblank reason for `returned`, capture the current draft and evidence SHA-256 values, and create the output with exclusive-create semantics. `verify` must parse one decision record, re-run draft verification, compare all linked identities and fingerprints, and return `2` on invalid or changed artifacts.

- [x] **Step 4: Run the focused decision tests**

  Run: `python3 tests/test_demo_report.py`

  Expected: all demo report and decision CLI tests pass; invalid inputs return `2`, valid record and verify operations return `0`.

- [x] **Step 5: Document and track the bounded task**

  Document the command shape and explicit human-decision boundary in `README.md` and `tasks/README.md`. Add Ticket 10 with the synthetic-only acceptance scope, close it with exact verification results, and update `STATUS.md` to show Ticket 03 still `needs-info` and Ticket 04 still blocked.

- [x] **Step 6: Run the full repository checks**

  Run: `python3 -m unittest discover -s tests -v`

  Expected: all tests pass.

  Run: `python3 scripts/codex_check.py`

  Expected: `codex-check: PASS`.

  Run: `git diff --check`

  Expected: exit `0` with no output.

- [x] **Step 7: Commit the implementation**

  Commit the CLI, tests, docs, status, and Ticket 10 together as one bounded outcome: `feat: record explicit synthetic draft decisions`.

## Final review fix pass

- Add regression coverage for a draft-task evidence path that differs from its verified source, a draft edited immediately after verification, a returned record with an empty reason section followed by another heading, and a `ready` draft whose review artifact no longer verifies.
- Make decision recording use the fingerprint from the verified task snapshot and reject artifact identity mismatches.
- Parse only the standalone `## Reason` section up to the next Markdown heading.
- Mark Ticket 10 `State: closed` and refresh the documented test counts after the fix pass.
- Fix pass verification: 22 draft/decision tests and 44 full-suite tests pass; `codex_check.py` and `git diff --check` pass.
