# 11 — Enforce ISO-week bounds and redact validation output

**What to build:** Keep the synthetic validation path safe and internally consistent by requiring the contract dates to be the exact inclusive dates of its ISO week, and by excluding raw record keys, row dates, and absolute local paths from generated evidence, review, and task text.

**Blocked by:** None. Use only the tracked synthetic fixtures and temporary synthetic rows.

**Category:** enhancement

**Status:** ready-for-agent

**State:** closed

- [x] Reject a contract whose `start_date` or `end_date` does not match the Monday/Sunday of its declared ISO week.
- [x] Keep diagnostics useful by file and row while omitting raw keys, row dates, absolute references, and arbitrary path text copied from tampered evidence or draft metadata.
- [x] Store verifiable local artifact references without absolute filesystem paths in review JSON and task records.
- [x] Add CLI regression cases and document the synthetic-only behavior.
- [x] Preserve Ticket 03 as `needs-info`; do not access real inputs.

## Verification

- Run focused validator and source-audit regression tests first.
- Run `python3 -m unittest discover -s tests -v`, `python3 scripts/codex_check.py`, and the W44 demo validator.

## Completion

- Focused validator and source-audit regression cases passed after first failing against the prior implementation.
- Missing evidence/draft and validator-failure cases first exposed absolute paths in failure diagnostics; those cases pass after sanitizing serialized errors.
- `python3 -m unittest discover -s tests -v`: 56 tests passed.
- W44 demo validator: exit 0, `status: pass`, `output_qty=30`, `case_count=1`, no errors.
- `python3 scripts/codex_check.py` and `git diff --check`: passed.
- `Ticket 03` remains `needs-info`; no real input was read.

## Comments

- 2026-11-03: Started at the user's request to continue within synthetic-only scope; the filled metric-card example remains a local ignored artifact and is not treated as an approved real contract.
