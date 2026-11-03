# Project Status

Status: issue-10-synthetic-draft-acceptance-gate-complete
Last updated: 2026-11-03
Windows validation: deferred

## Current baseline

- Local Git repository; no remote selected.
- Mac: Codex CLI 0.166.0-alpha.5.1, Python 3.9.6, Git 2.54.0 (Apple Git-157).
- Project guidance and a Python structural check are present and committed in `6f96ba9`.
- The synthetic input validator, source review, Git-tracked task ledger, draft writer, and independent draft reviewer are available on Mac. The full agent roster and real data are not present.

## Next task

Tickets 01, 02, 05, 06, 07, 08, 09, and 10 are closed. Ticket 05 completed a Mac-only synthetic-data scheduled trial; its one-time Codex desktop automation `mac` ran on 2026-11-02 and is paused. No recurring schedule is active.

- [ ] **Ticket 03 — historical metric validation (`needs-info`):** wait for the data owner to approve the metric contract and handling rules and provide one historical export. Do not read or import real data before those prerequisites and authorization are in place. Intake template: `docs/historical-week-intake.md`.
- [ ] **Ticket 04 — real draft acceptance:** remains open and blocked by Ticket 03; Ticket 02 is already closed. Start only after Ticket 03 is complete. Human acceptance must remain an explicit decision on a specific draft version.
- [ ] **Windows validation — deferred:** the user is arranging this separately. Report only Mac verification until Windows is actually tested.

Ticket 06 rejects empty and whitespace-only keys with a file, row, and column diagnostic. Ticket 07 rejects duplicate CSV headers before row values are interpreted. Ticket 08 requires each metric source to define a non-empty string unit. Ticket 09 rejects duplicate metric names in a contract, preventing aggregate overwrite. Ticket 10 adds explicit accepted/returned decisions for reviewed synthetic drafts, with draft and evidence fingerprint verification and post-verification race checks. The Mac suite passed with 47 tests. No open ticket is currently executable: Ticket 03 still requires the approved historical-week intake, Ticket 04 remains blocked by Ticket 03, and Windows validation is separately deferred. Do not treat Ticket 10 or recurring scheduling as unblocking Ticket 04.

## Blockers

- The synthetic draft-and-review issue has no open blocker.
- Ticket 05 used only tracked synthetic fixtures and had no real-data prerequisite. The actual scheduled run successfully made scoped Git commits in its local sandbox.
- Real historical-week work still needs the data owner's approved metric contract, one export, and handling rules.
- No real export was opened or imported while preparing the intake form.
- Windows validation is separately scheduled by the user and is not a Mac gate.
- The local Markdown issue tracker and default triage vocabulary are configured in `docs/agents/`. The prior ISSUE-001 reviews used its original issue as the spec.
- Ticket 10's acceptance gate was tested with temporary synthetic artifacts only. No decision was recorded for the committed demo draft, and no real data was read.

## Verification

- Template `./scripts/codex-check` before customization: FAIL because `CONTEXT.md` and `STATUS.md` still contained initialization placeholders.
- `python3 scripts/codex_check.py`: PASS on Mac.
- `./scripts/codex-check`: PASS on Mac.
- `git diff --cached --check` before the initial commit: PASS; only the 11 intended initialization files were staged.
- Read-only `codex exec` in this repository: exit 0. It quoted the Stage A rule from project `AGENTS.md`; the session record contained both the global and project guidance. The model connection timed out on WebSockets before succeeding via HTTPS fallback.
- ISSUE-001 full suite: `python3 -m unittest discover -s tests -v` — 10 tests passed on Mac, including the four required invalid-input classes.
- Demo validator: exit 0; repeated runs produced identical evidence bytes with `output_qty=30` and `case_count=1`.
- AST syntax parse: PASS for the validator and its tests. `mypy` is not installed. A separate `py_compile` attempt could not write to macOS's Python cache path in the current sandbox; the executable CLI tests passed.
- Independent review: source hash/parse consistency, invalid-contract handling, and stale README text were corrected. Repeated CLI setup in tests remains a minor maintainability note, not a behavioral blocker.
- Structural checker: the completed-issue status first failed its hard-coded `ISSUE-001` next-task check; after changing the check to require a nonempty next-task description, both Python and shell entry points passed.
- Local ticket publication: `python3 scripts/codex_check.py` and `git diff --check` passed on Mac; the five tickets and their dependency/status claims received a read-only review.
- Issue 01 Mac suite: `python3 -m unittest discover -s tests -v` — 17 tests passed, including source fingerprint, contract fingerprint, missing source, blocked input evidence, and changed artifact cases.
- Passing demo: `check_inputs.py` exit `0`, `source_audit.py finalize` exit `0`, and `source_audit.py verify --task tasks/demo-pass-2026-W44.md` exit `0` with `ready`.
- Blocked demo: `check_inputs.py` exit `2`, `source_audit.py finalize` exit `2`, and `source_audit.py verify --task tasks/demo-blocked-2026-W44.md` exit `0` with `blocked` and a locatable missing `ai_ehs.csv` reason.
- `git log -p -- tasks/demo-pass-2026-W44.md tasks/demo-blocked-2026-W44.md` showed both `working` → final transitions, with author and commit time. Raw inputs and evidence remain local and Git-ignored.
- Independent spec and standards reviews found a tampered-evidence promotion path and a stale README command. The promotion path was reproduced by a failing test and fixed with deterministic revalidation; the README now uses a fresh run ID.
- Issue 02 Mac suite: `python3 -m unittest discover -s tests -v` — 27 tests passed, including wrong metric value, wrong unit, missing evidence, invented historical value, numeric prose outside the metric table, and changed draft after review.
- Passing draft demo: `draft_demo_report.py` exit `0`; a separate reviewer session ran `review_demo_report.py` exit `0`, with `status: pass` and draft task `ready` (not Accepted). `review_demo_report.py verify --task tasks/demo-pass-2026-W44-draft.md` exited `0`.
- Wrong-number demo: a separate reviewer session ran `review_demo_report.py` exit `2`, with `status: blocked` and `line 13: output_qty value is '31'; expected '30'`. `review_demo_report.py verify --task tasks/demo-wrong-number-2026-W44-draft.md` exited `0` for that blocked version.
- `git log -p -- tasks/demo-pass-2026-W44-draft.md tasks/demo-wrong-number-2026-W44-draft.md` showed `working` → `ready` and `working` → `blocked` transitions with author and commit time. Drafts and review JSON remain local and Git-ignored; task records keep their paths and hashes.
- Independent spec and standards reviews identified an unchecked numeric prose claim, a stale-draft handoff risk, and an incorrect generic verify instruction. Failing tests reproduced the first two; the review rule, draft verification command, and task documentation were corrected.
- Issue 03 intake-only step: `docs/historical-week-intake.md` was prepared as an unapproved blank template; a read-only review confirmed that it covers owner approval, metric definitions, export inventory, anomaly handling, Codex visibility, and local retention. No real export was read.
- `git check-ignore -- inputs/historical-week/intake.md` and `git check-ignore -- inputs/historical-week/export.csv`: both exited `0` for hypothetical local paths. `python3 scripts/codex_check.py` and `git diff --check`: PASS after the template and status edits.
- Ticket 05 scope revision: `a64b0f8` changed the dependency to closed ticket 02; `python3 scripts/codex_check.py` and `git diff --check` passed before that commit.
- Manual blocked synthetic attempt `trial-20261102-blocked-a`: `start` exit 0, validator exit 2, source `finalize` exit 2, `verify` exit 0 for a consistent `blocked` task. `ai_ehs.csv: missing source` is in the task and review. Working and blocked states were committed as `c999dea` and `c7411c8`.
- Manual retry with a new ID `trial-20261102-retry-b` and complete `fixtures/demo`: source start, validator, finalize, and verify exited 0; source state commits were `d521158` and `9e4d118`. Draft creation exited 0 and committed its working state as `d79318b`. A separate Codex reviewer session finalized and verified the draft with exit 0, review status `pass`, no errors; its ready-state commit was `4b9c3b9`. The draft is not Accepted.
- Actual desktop scheduled invocation: started at 2026-11-02 16:25:06 Asia/Shanghai and produced run `trial-scheduled-20261102-162717-ada15b`. Source start, validation, source finalization, source verification, and draft creation all exited 0. Scoped task transitions were committed as `af0d400` (source working), `b32592a` (source ready), and `fbc1b89` (draft working). A separate Codex reviewer session ran `review_demo_report.py` and its `verify` with exit 0, `status: pass`, `errors: []`, then committed draft ready as `8595f07`. `source_audit.py verify` passed again; Git ignores the run evidence and generated draft. No Accepted state or external send occurred. Automation `mac` is paused after the single run.
- Interrupted-start simulation in a temporary directory: two distinct `source_audit.py start` calls both exited 0; the original and retry tasks both remained `working` without overwriting either file. The first ad hoc harness attempt failed because it imported a script module without adding `scripts/` to Python's module path; the corrected CLI-based check passed.
- Final read-only review found no blocking issue; it caught a doubled run-ID prefix in the lookup instructions, which was corrected in `docs/synthetic-scheduled-trial.md`. Final Mac checks: 27 unit tests passed, `python3 scripts/codex_check.py` passed, source and draft artifact verification passed, and `git diff --check` passed.
- Ticket 06: the two new CLI cases first failed because empty and whitespace-only keys exited `0`; after the validator fix, `python3 tests/test_check_inputs.py CheckInputsCliTests.test_empty_record_id_blocks_evidence CheckInputsCliTests.test_whitespace_only_record_id_blocks_evidence` passed. Full Mac suite: `python3 -m unittest discover -s tests -v` — 29 tests passed.
- Ticket 07: `python3 tests/test_check_inputs.py CheckInputsCliTests.test_duplicate_metric_header_blocks_evidence` first failed because a duplicate `output_qty` header exited `0`; it passed after the validator fix. Full Mac suite: `python3 -m unittest discover -s tests -v` — 30 tests passed.
- Ticket 08: `python3 tests/test_check_inputs.py CheckInputsCliTests.test_missing_or_invalid_metric_unit_blocks_evidence` first failed for missing, empty, whitespace-only, and non-string units; it passed after contract validation was tightened. Full Mac suite: `python3 -m unittest discover -s tests -v` — 31 tests passed.
- Ticket 09: `python3 tests/test_check_inputs.py CheckInputsCliTests.test_duplicate_contract_metric_blocks_evidence` first failed because duplicate `output_qty` declarations exited `0`; it passed after duplicate metric validation. Full Mac suite: `python3 -m unittest discover -s tests -v` — 32 tests passed.
- Ticket 10: `python3 tests/test_demo_report.py` — 22 tests passed. Full Mac suite: `python3 -m unittest discover -s tests -v` — 44 tests passed. `python3 scripts/codex_check.py` and `git diff --check` passed. The decision CLI verified temporary accepted/returned records and rejected invalid task/review states, evidence path mismatches, missing return reasons, overwritten paths, post-review edits, and changed artifacts.
- Ticket 10 race hardening: three new regression cases first failed because decision recording accepted a task, evidence, or review changed immediately after verification. The CLI now rechecks the task snapshot and draft, evidence, and review fingerprints before writing. Focused race tests and the existing draft race test passed; final counts: 25 draft/decision tests and 47 full-suite tests, with `codex_check.py` and `git diff --check` passing.
