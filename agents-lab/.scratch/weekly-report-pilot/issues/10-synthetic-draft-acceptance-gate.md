# 10 — Synthetic draft acceptance gate

**What to build:** Let a person record an explicit accepted or returned decision for a reviewed synthetic draft, bound to its exact draft and evidence fingerprints.

**Blocked by:** None — use the existing synthetic `2026-W44` workflow. Ticket 04's real historical-week demonstration remains blocked by Ticket 03.

**Category:** enhancement

**Status:** ready-for-agent

**State:** closed

- [x] A decision can be recorded only for a `ready` draft whose review verification passes.
- [x] `accepted` and `returned` are explicit decisions in a separate immutable task record; `returned` requires a nonblank reason.
- [x] The record captures draft and evidence fingerprints; verification fails if either linked artifact changes.
- [x] Recording rejects changes to the ready draft task, draft, evidence, or review that occur after review verification and before the decision is written.
- [x] Existing draft tasks remain `ready` and unchanged; record creation never sends or publishes a report.
- [x] The automated demonstration uses temporary synthetic artifacts and creates no acceptance record for the committed demo draft.

## Verification

- Run `python3 tests/test_demo_report.py` and confirm the decision workflow cases pass.
- Run `python3 -m unittest discover -s tests -v`.
- Run `python3 scripts/codex_check.py`.
- Run `git diff --check`.

## Non-goals

- Do not read or import real historical data.
- Do not mark Ticket 03 complete or unblock Ticket 04.
- Do not accept the committed `2026-W44` demo draft as part of implementation.

## Comments

- 2026-11-03: At the user's direction, skip Ticket 03's data validation and proceed with a synthetic-only acceptance gate. This does not satisfy or close Ticket 03.

## Completion

- `python3 tests/test_demo_report.py`: 26 tests passed, including the decision workflow and post-verification race cases.
- `python3 -m unittest discover -s tests -v`: 48 tests passed.
- `python3 scripts/codex_check.py`: passed.
- `git diff --check`: passed.
