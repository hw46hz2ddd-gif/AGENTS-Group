# 09 — Reject duplicate metric names in contracts

**What to build:** Contract validation blocks repeated metric names so one source cannot silently overwrite another source's aggregate in the evidence.

**Blocked by:** None — each source already declares its output metric in the contract.

**Category:** bug

**Status:** ready-for-agent

**State:** closed

- [x] Each metric name appears in at most one source definition in a contract.
- [x] A repeated metric name blocks the CLI with exit `2`, blocked evidence, empty `metrics`, and a locatable contract error naming the metric.
- [x] The valid demo contract still passes and reports `output_qty=30` and `case_count=1`.
- [x] CLI regression coverage proves a later source cannot overwrite an earlier source's metric value.

## Verification

- Run `python3 -m unittest discover -s tests -v` and confirm the existing suite and duplicate-metric case pass.
- Run `python3 scripts/codex_check.py`.

## Notes

This ticket enforces uniqueness of the contract's output metric names only. It does not change source-file identity or aggregation rules.

## Completion

- The new CLI case first failed because a duplicate metric contract exited `0`; it passed after contract validation was updated.
- `python3 -m unittest discover -s tests -v`: 32 tests passed on Mac.
- `python3 scripts/codex_check.py`: passed after updating `STATUS.md`.
