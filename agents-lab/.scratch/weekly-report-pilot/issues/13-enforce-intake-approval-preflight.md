# 13 — Historical intake approval preflight

**What to build:** Require a machine-readable local approval manifest before a non-synthetic weekly input run can read CSV contents. Bind input validation and source finalization to the same period, contract, approved directory, source inventory, processing authorization, and handling declarations.

**Blocked by:** None. Tests use fabricated approval metadata and synthetic CSVs only. External prerequisite for future real-data work: an actual data-owner-approved contract, handling rules, export, and permitted local path remain required by Ticket 03.

**Category:** enhancement

**Status:** ready-for-agent

**State:** closed

- [x] A non-synthetic contract without a valid `--approval-manifest` exits `2` before CSV reads; blocked evidence contains no source fingerprints, row counts, or metrics.
- [x] The manifest must explicitly declare approval, user processing authorization, ISO week, contract version and raw-byte fingerprint, exact resolved input directory, exact source filenames and raw-byte fingerprints, and the allowed handling policy.
- [x] A changed or missing approval-record copy, contract, input path, manifest, or source file blocks the run with diagnostics that do not disclose approver identity, local paths, record keys, or source values.
- [x] Extra files, nested directories, and symlinks in the approved source directory block the run.
- [x] Explicitly synthetic contracts work without real approval only under `fixtures/` or a path containing `simulation-only`; evidence is labeled as simulated.
- [x] `source_audit.py finalize` passes the same explicit manifest to deterministic revalidation; `verify` detects manifest changes after finalization.
- [x] All new behavior is tested with synthetic CSVs and fabricated temporary metadata; the full Mac suite and structural check pass.
- [x] Tickets 03/04 remain open for real data. Windows validation remains assigned to user-run Ticket 12.
- [x] Evidence outputs and source finalization artifacts cannot overwrite or hard-link alias protected inputs, fixtures, contracts, manifests, or approval records.
- [x] The contract period is a valid ISO week and its start/end dates exactly match that week.
- [x] Tracked task diagnostics do not echo evidence-supplied error text or local paths.

## Verification

- `python3 tests/test_intake_preflight.py`
- `python3 tests/test_check_inputs.py`
- `python3 tests/test_source_audit.py`
- `python3 -m unittest discover -s tests -v`
- `python3 scripts/codex_check.py`
- `git diff --check`
- Synthetic source, draft, and temporary decision verification commands are recorded below.

## Comments

- 2026-11-04: User approved the design and implementation plan. Tests use only synthetic CSVs and fabricated temporary metadata; they do not simulate a data-owner approval or export. The user's separate Ticket 03 processing authorization remains recorded, but no real data was read. No Windows result is created.
- 2026-11-04: Final independent review found that finalized tasks with a missing or unreadable contract were blocked but could not pass `verify`. Two regression cases failed before the fix and pass after it; unchanged blocked artifacts verify, and a changed review is rejected. The duplicate unreachable `unittest.main()` block in `tests/test_check_inputs.py` was removed in follow-up closeout maintenance.

## Completion

- `python3 -m unittest discover -s tests -q`: 92 tests passed in the final parent-repository port. Focused suites: intake preflight 19, input validation 23, source audit 20, and draft/decision 30 tests passed. The original standalone implementation worktree passed 85 tests before the parent-repository port.
- `python3 tests/test_source_audit.py SourceAuditCliTests.test_unreadable_contract_blocked_task_can_be_verified SourceAuditCliTests.test_missing_contract_blocked_task_can_be_verified`: 2 tests passed after the review fix; both failed first with `task run mode contradicts review`.
- `python3 scripts/codex_check.py`: `codex-check: PASS`; `git diff --check`: exit `0`.
- The tracked manifest example parsed with `python3 -m json.tool docs/historical-week-intake.manifest.example.json`; `git check-ignore -- inputs/historical-week/approval/manifest.json` confirmed the local approval path is ignored.
- In the implementation worktree, `source_audit.py verify --task tasks/sim-localpath-20261104-source.md` exited `0` with source `ready`; `review_demo_report.py verify --task tasks/sim-localpath-20261104-draft.md` exited `0` with draft `ready`. These task files and their Git-ignored evidence are local-only and are not included in the parent-repository PR.
- Both temporary decision records (`synthetic-accepted.md` and `synthetic-returned.md`) verified with exit `0`; they are explicitly simulation-only and do not record a real human decision.
- Review regressions cover protected output paths and hard-link aliases, ISO week/date binding, safe diagnostics, and verification of blocked tasks with invalid contracts. The Important review finding is fixed and covered by tests; the duplicate test entry point was removed in follow-up closeout maintenance.
- Follow-up closeout verification: `python3 -m unittest discover -s tests -q` passed all 92 tests; nested and root `codex-check` passed; `git diff --check` passed.
- No real data, owner approval, or export was accessed or created. Tickets 03/04 remain open for real-data work; Windows validation remains assigned to user-run Ticket 12.
