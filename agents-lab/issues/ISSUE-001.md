# ISSUE-001: Validate synthetic weekly-report inputs on Mac

## Goal

Produce deterministic evidence from a small synthetic production and AI/EHS dataset.

## In scope

- Add a versioned demo metric contract and fixed CSV fixtures for ISO week 2026-W44.
- Add a Python 3.9+ standard-library validator that records source hashes, row counts, aggregate values, and errors.
- Run the validator and meaningful input tests on the current Mac.

## Out of scope

- Real business data and external data connections.
- Agent role configuration, draft generation, scheduling, and Windows testing.

## Completion criteria

- The valid synthetic sample produces `output_qty=30` and `case_count=1` with status `pass`.
- Out-of-period rows, duplicate record IDs, a missing required column, and a missing source each produce status `blocked` and a locatable error.
- Re-running identical inputs on Mac produces the same metrics and error conclusion.
- `STATUS.md` records the actual commands and results; Windows remains `deferred`.

## Verification

- Run the feature's unit tests and demo validator command after they exist; record their exact commands in `README.md`.
- Run `python3 scripts/codex_check.py` after updating project guidance or status.

## Blocking edges

- If the current Python or Codex environment cannot run the intended workflow, record the observed failure in `STATUS.md` rather than claiming this issue complete.

## Notes

Expected command: `python3 scripts/check_inputs.py --period 2026-W44 --contract contracts/demo.v1.json --input-dir fixtures/demo --out runs/demo-2026-W44/evidence.json`. The output JSON should contain the period, contract version, status, per-source SHA-256 and row counts, aggregate metrics, and errors. This interface is part of the issue; the implementation may refine it before code is written if a concrete conflict is recorded.
