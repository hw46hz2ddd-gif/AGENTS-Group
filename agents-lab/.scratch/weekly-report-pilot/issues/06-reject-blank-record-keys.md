# 06 — Reject blank source record keys

**What to build:** The synthetic input validator blocks a source row when its configured record key is empty or contains only whitespace, and points to the source file and row.

**Blocked by:** None — the existing demo metric contract defines the key column for each source.

**Category:** bug

**Status:** ready-for-agent

**State:** closed

- [x] An empty or whitespace-only value in a configured key column blocks validation and identifies the source file, 1-based CSV line, and key column.
- [x] The CLI exits `2` and writes evidence with `status: blocked` and empty `metrics` for either invalid-key case.
- [x] Valid demo fixtures still pass with the existing metrics; duplicate-key detection remains intact.
- [x] CLI regression tests cover both an empty key and a whitespace-only key.

## Verification

- Run `python3 -m unittest discover -s tests -v` and confirm the existing suite and new invalid-key cases pass.
- Run `python3 scripts/codex_check.py`.

## Notes

The check applies to the `key_column` named by each source in the metric contract. Whitespace is used only to determine whether the key is blank; this ticket does not change key normalization or duplicate comparison behavior.

## Completion

- `python3 -m unittest discover -s tests -v`: 29 tests passed on Mac.
- `python3 scripts/codex_check.py`: passed after updating `STATUS.md`.
