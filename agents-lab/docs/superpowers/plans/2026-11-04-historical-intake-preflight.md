# Historical Intake Approval Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block non-synthetic weekly input runs before CSV reads unless a complete local approval manifest matches the approved period, contract, path, and source inventory.

**Architecture:** Add one standard-library manifest validator and call it from `check_inputs.py` before its source loop. Pass the same explicit `--approval-manifest` through source finalization and deterministic revalidation; bind evidence and source-task records to the manifest hash without copying owner names or local paths into tracked tasks. Preserve synthetic runs only for contracts marked `simulation_only: true` whose input directory is under `fixtures/` or contains a `simulation-only` path component.

**Tech Stack:** Python 3.9+ standard library, existing unittest CLI tests, JSON approval manifests, existing source and draft task CLIs.

**Spec:** `docs/superpowers/specs/2026-11-04-historical-intake-preflight-design.md`

## Global Constraints

- Do not create or simulate a real data-owner approval, user authorization, or export.
- Do not claim cryptographic identity verification; the CLI checks declarations and consistency, while a human verifies the approver.
- Do not read real data or run this workflow on Windows as part of implementation.
- Do not send, publish, or automatically accept a report.
- Keep the Python 3.9+ standard-library-only runtime.
- Keep completed manifests, approval forms, raw inputs, evidence, reviews, and generated drafts in ignored local paths. The tracked example contains placeholders only.
- Leave Tickets 03 and 04 open for real-data work; do not treat synthetic approval as satisfying them.

## Review Focus

- Missing or unapproved manifest must produce blocked evidence before source hashes or row counts appear. Test in Task 2 with a non-synthetic contract and existing synthetic CSVs.
- Approval-record, contract, or source hash changes must invalidate a real-mode run. Test in Tasks 1 and 3 using raw-byte mutations.
- Extra files, nested directories, or symlinks in a real input directory must block rather than be silently ignored. Test in Task 1; synthetic fixture metadata remains allowed in Task 2.
- A `simulation_only` contract outside `fixtures/` or a `simulation-only` path must require a real manifest or block. Test in Task 1.
- Preflight diagnostics must not echo CSV values, record keys, approver names, or full local paths. Test in Tasks 1 and 2 with sentinel strings.
- A source changed between approval checks and CSV parsing must be blocked without parsing an unapproved byte snapshot. Test in Tasks 1 and 2.

---

### Task 1: Implement the approval manifest validator

**Files:**
- Create: `scripts/intake_preflight.py`
- Create: `tests/test_intake_preflight.py`
- Test data: generated in temporary directories by the tests; no fictional approval fixture is committed.

**Interfaces:**
- Produces: `validate_preflight(manifest_path: Optional[Path], contract: dict, contract_sha256: str, period: str, input_dir: Path, project_root: Path) -> dict` in `scripts/intake_preflight.py`.
- Successful return fields: `run_mode` (`simulation` or `real`), `approval_manifest_sha256` (null in simulation mode), `source_hashes` (filename to SHA-256), and `source_contents` (the exact approved bytes to parse). Invalid preflight raises `PreflightError` with a safe, path-free message.
- Exact top-level manifest keys: `schema_version`, `approval_state`, `simulation_only`, `data_owner`, `approver`, `approved_at`, `approval_record`, `user_processing_authorized`, `user_processing_authorized_at`, `scope`, `sources`, and `handling`. Reject missing and unknown keys.
- `schema_version` is integer `1`; `approval_state` is `approved`; real manifests set `simulation_only: false`; `data_owner` and `approver` each have non-empty `name` and `title`; both dates use ISO `YYYY-MM-DD`.
- `approval_record` has exactly `path` and `sha256`. `path` is a safe relative path resolved from the manifest's directory, with no `..`, absolute paths, or symlink; it identifies the completed approval copy whose raw bytes match `sha256`.
- `scope` has exactly `period`, `contract_version`, `contract_sha256`, and `input_dir`; all must match the CLI request and loaded contract. `input_dir` is the exact resolved approved directory.
- Each `sources` item has exactly `file` and raw-byte `sha256`; require one item for every distinct contract filename and no duplicates or extras.
- `handling` has exactly `read_only`, `codex_visibility`, `evidence_policy`, `external_sharing`, `retention_days`, and `cleanup_owner`; require the exact supported policy values from the spec, positive integer retention, and a non-empty cleanup owner.
- Validate manifest and approval metadata before opening source CSVs. Real-mode directories must contain exactly the listed regular source files; simulation directories may also contain regular fixture metadata, but must contain every contract source and reject symlinks or nested directories. After validation, read each contract source once, hash those bytes, compare the real-mode approved hash, and return the same byte snapshots for CSV parsing to avoid a check/use race.

- [x] **Step 1: Write failing validator tests** for a complete fabricated approval manifest bound to temporary synthetic CSVs, missing/unapproved manifest rejected before any source `read_bytes`, missing user authorization, invalid handling values, contract/period mismatch, approval-record hash mismatch, input path mismatch, source inventory mismatch, extra files, nested directories, symlinks, and changed source hash. Assert errors contain no sentinel names, paths, or CSV values.
- [x] **Step 2: Run `python3 tests/test_intake_preflight.py` and confirm the new behavior tests fail** because the validator module/interface is absent.
- [x] **Step 3: Implement `PreflightError` and `validate_preflight(...)`** in `scripts/intake_preflight.py`. Validate exact schema/types, contract and period bindings, approval-copy fingerprint, allowed path, and exact real-mode source inventory before opening source CSVs. Read and hash contract source bytes once and return those exact bytes for parsing.
- [x] **Step 4: Run `python3 tests/test_intake_preflight.py` and confirm all validator cases pass.**
- [x] **Step 5: Commit** `feat: add historical intake manifest validator`.

### Task 2: Enforce preflight before CSV parsing

**Files:**
- Modify: `scripts/check_inputs.py`
- Modify: `contracts/demo.v1.json`
- Modify: `tests/test_check_inputs.py`
- Modify: `tests/test_source_audit.py` (keep temporary synthetic input paths inside the allowed simulation boundary)
- Test: `tests/test_intake_preflight.py`

**Interfaces:**
- Consumes: Task 1 `validate_preflight(...)` and `PreflightError`.
- Produces: `check_inputs.py --approval-manifest PATH`; evidence fields `run_mode` and `approval_manifest_sha256`.
- Both tracked synthetic contracts have `simulation_only: true` (the historical simulation contract already has this marker); only input directories inside the repository `fixtures/` tree or with a `simulation-only` path component may use that mode. Other contracts require an explicit valid manifest.

- [x] **Step 1: Write failing CLI tests** proving a non-synthetic contract without a manifest exits `2`, writes `status: blocked`, and records no inputs, row counts, metrics, or source hashes; a complete temporary manifest bound to a non-simulation contract and synthetic CSVs passes; both synthetic contracts pass under allowed paths and block outside them; the parser consumes the exact preflight byte snapshots; and CSV errors do not echo record keys or source values.
- [x] **Step 2: Run `python3 tests/test_check_inputs.py` and confirm the new gate cases fail** before integration.
- [x] **Step 3: Integrate preflight after contract loading and before the source loop.** Parse only byte snapshots returned by preflight. On failure, write safe blocked evidence with an empty `inputs` list, no metrics, and no source hashes. Add `simulation_only: true` to the demo contract and retain the existing historical-simulation marker. Require exact directory inventory only in real mode; allow extra regular fixture metadata in simulation mode while rejecting symlinks and nested directories in both modes. Place temporary source-audit test inputs under a `simulation-only` path component. Replace raw record-key/date/value/path/approver details in diagnostics with safe field and error categories.
- [x] **Step 4: Run `python3 tests/test_check_inputs.py` and confirm the full input-validator suite passes.**
- [x] **Step 5: Commit** `feat: gate input validation on approved intake`.

### Task 3: Bind source audit to the same manifest

**Files:**
- Modify: `scripts/source_audit.py`
- Modify: `tests/test_source_audit.py`

**Interfaces:**
- Consumes: Task 2 `check_inputs.py --approval-manifest PATH` and evidence fields.
- Produces: `source_audit.py finalize --approval-manifest PATH` for real runs; review artifacts carry the ignored local manifest path and hash; tracked source tasks carry only `run_mode` and `approval_manifest_sha256`.
- For simulation runs, the manifest path is omitted and the task records a null-equivalent hash.

- [x] **Step 1: Write failing source-audit tests** for a valid real-mode run using a fabricated manifest, a non-simulation temporary contract, and temporary synthetic files; a missing manifest (blocked); changed manifest after validation; changed manifest after finalization (verify fails); and unchanged simulation run. Assert no owner name or local manifest path enters the tracked task. Also prove source changes after finalization invalidate the task and simulation finalization rejects a manifest argument.
- [x] **Step 2: Run `python3 tests/test_source_audit.py` and confirm the new propagation tests fail.**
- [x] **Step 3: Pass the manifest to deterministic regeneration and source review.** Record the ignored local manifest reference and raw-byte hash in the ignored review artifact; verify the hash and rerun preflight when verifying finalized source artifacts. Derive source fingerprints from successful deterministic evidence instead of reading source files outside preflight. Do not place the manifest path or approval names in tracked task frontmatter. Preserve legacy verification only for explicitly synthetic contracts and allowed paths.
- [x] **Step 4: Run `python3 tests/test_source_audit.py` and confirm the full source-audit suite passes.**
- [x] **Step 5: Commit** `feat: bind source audits to approval manifests`.

### Task 4: Track, document, and verify the implementation

**Files:**
- Create: `docs/historical-week-intake.manifest.example.json` with placeholders only.
- Modify: `docs/historical-week-intake.md`
- Modify: `README.md`
- Modify: `STATUS.md`
- Create: `.scratch/weekly-report-pilot/issues/13-enforce-intake-approval-preflight.md`

- [x] **Step 1: Before changing implementation code, publish Ticket 13** with the design's acceptance criteria, `Status: ready-for-agent`, and `State: open`; update `STATUS.md` to point to Ticket 13 and commit this task-state transition.
- [x] **Step 2: Create** `docs/historical-week-intake.manifest.example.json` with placeholders only. Update the intake and README docs with required fields, ignored local storage, the synthetic-only no-manifest command, and the warning that approval identity is not cryptographically verified.
- [x] **Step 3: Run the complete suite** `python3 -m unittest discover -s tests -v`, structural check `python3 scripts/codex_check.py`, and `git diff --check`. The standalone implementation worktree passed 85 tests; the parent-repository port preserved its path-redaction checks and now passes 92 tests. Structural checker and diff check exited `0` on the parent-repository port.
- [x] **Step 4: Run the existing synthetic artifact verifications** from the repository root:

```bash
python3 scripts/source_audit.py verify --task tasks/sim-localpath-20261104-source.md
python3 scripts/review_demo_report.py verify --task tasks/sim-localpath-20261104-draft.md
python3 scripts/record_draft_decision.py verify --record runs/sim-localpath-20261104/decisions/synthetic-accepted.md
python3 scripts/record_draft_decision.py verify --record runs/sim-localpath-20261104/decisions/synthetic-returned.md
```

Expected: source/draft remain `ready`; both decisions verify and remain explicitly simulation-only.
These task records and their Git-ignored evidence were verified in the implementation worktree and are not included in the parent-repository PR.
- [x] **Step 5: Update Ticket 13 and `STATUS.md`** with exact commands/results and mark Ticket 13 `State: closed`; keep Tickets 03/04 open and Windows Ticket 12 pending user-run. Commit the final task-state transition separately.
- [x] **Step 6: Commit** the implementation documentation and verified closeout as `feat: document and verify historical intake preflight`.

### Final review follow-up before closeout

- [x] Add failing CLI tests for evidence output collisions with source files, contract, manifest, approval copy, and a hard-link alias to a tracked fixture; add source-audit tests proving evidence/review artifacts cannot be placed under protected inputs.
- [x] Add failing tests for an invalid ISO week, contract dates that do not cover the labeled week, and sensitive strings in tampered evidence diagnostics.
- [x] Fix output-path overlap checks before reading evidence or writing outputs. Reject unsafe destinations without writing evidence there.
- [x] Enforce a valid ISO week and exact Monday-through-Sunday contract dates at preflight.
- [x] Use validator-generated diagnostics only; keep evidence-supplied text and local OS error paths out of tracked task bodies.
- [x] Run the focused regressions and full suite; all 85 tests pass in the implementation worktree and all 92 tests pass in the parent-repository port.
- [x] Re-run Task 4 artifact verifications, structural checker, diff check, JSON-template parse, and ignored-path check; close Ticket 13 and record the final documentation/closeout.
- [x] Fix independent-review regression: missing or unreadable contracts remain blocked and their finalized tasks verify deterministically; two focused cases failed before the fix and passed after it.
- [x] Defer minor polish: the duplicate unreachable `unittest.main()` entry point in `tests/test_check_inputs.py` has no runtime impact and is recorded for a future cleanup.
