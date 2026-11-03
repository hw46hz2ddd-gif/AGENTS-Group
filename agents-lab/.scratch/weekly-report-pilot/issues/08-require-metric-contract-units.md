# 08 — Require metric contract units

**What to build:** Contract validation blocks a source whose `unit` is missing, blank, whitespace-only, or not a string, before the contract is used for a source review or report draft.

**Blocked by:** None — the existing demo contract and report reviewer already use per-source units.

**Category:** bug

**Status:** ready-for-agent

**State:** closed

- [x] Every source must define `unit` as a non-empty, non-whitespace string.
- [x] Missing, blank, whitespace-only, and non-string units make the CLI exit `2` and write blocked evidence with empty `metrics` and a locatable contract error.
- [x] The valid demo contract still passes and its report units remain unchanged.
- [x] CLI regression coverage includes each invalid unit form.

## Verification

- Run `python3 -m unittest discover -s tests -v` and confirm the existing suite and new invalid-unit cases pass.
- Run `python3 scripts/codex_check.py`.

## Notes

Units are consumed by the report writer and checked by the independent reviewer. This ticket validates the required contract field only; it does not convert values or change metric calculations.

## Completion

- Before the fix, the CLI accepted all four invalid unit forms and the regression test failed; it passed after the field check was added.
- `python3 -m unittest discover -s tests -v`: 31 tests passed on Mac.
- `python3 scripts/codex_check.py`: passed after updating `STATUS.md`.
