# 07 — Reject duplicate CSV header columns

**What to build:** The synthetic input validator blocks a CSV source whose header repeats a column name, preventing `DictReader` from silently collapsing duplicate fields into one value.

**Blocked by:** None — the input validator and contract-based source list already exist.

**Category:** bug

**Status:** ready-for-agent

**State:** closed

- [x] A duplicate header name in a contracted source blocks validation and identifies the source file, header line, and duplicated column.
- [x] The CLI exits `2` and writes evidence with `status: blocked` and empty `metrics` when a required metric column is duplicated.
- [x] Valid demo fixtures and missing-required-column handling remain unchanged.
- [x] A CLI regression test proves a duplicated metric header cannot silently determine the reported value.

## Verification

- Run `python3 -m unittest discover -s tests -v` and confirm the existing suite and new duplicate-header case pass.
- Run `python3 scripts/codex_check.py`.

## Notes

The check applies to duplicate names in a CSV header, before row values are interpreted by `csv.DictReader`.

## Completion

- The new CLI case first failed because a duplicated `output_qty` header exited `0`; it passed after the validator change.
- `python3 -m unittest discover -s tests -v`: 30 tests passed on Mac.
- `python3 scripts/codex_check.py`: passed after updating `STATUS.md`.
