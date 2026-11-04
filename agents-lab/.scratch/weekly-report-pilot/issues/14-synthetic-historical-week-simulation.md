# 14 — Synthetic historical-week simulation

**What to build:** Demonstrate the historical-week source and draft workflow with a fictional approval and a synthetic one-week export, without claiming real-data readiness.

**Blocked by:** None — use only the synthetic fixtures and existing local CLIs.

**Category:** enhancement

**Status:** ready-for-agent

**State:** closed

- [x] The intake note clearly says `SIMULATION ONLY`; it does not imply a real data-owner approval or authorize real-data processing.
- [x] The synthetic `2026-W43` contract and CSVs validate to the documented totals and produce a fingerprinted, verified `ready` source task.
- [x] A missing-source variant produces a locatable blocked result and does not generate a ready task.
- [x] A draft from the ready synthetic source passes independent review and remains `ready` pending a real person's decision.
- [x] Accepted/returned decision paths are exercised only with temporary simulation artifacts; no committed report is accepted or sent.
- [x] Ticket 03 and Ticket 04 remain open for their real-data scope; Windows validation is skipped at the user's direction.

## Verification

- `python3 scripts/check_inputs.py --period 2026-W43 --contract contracts/historical-simulation.v1.json --input-dir fixtures/historical-simulation --out runs/historical-simulation-2026-W43/evidence.json`
- Source audit `start`, `finalize`, and `verify` using a unique `sim-historical-2026-W43` ID.
- Draft writer and independent reviewer using separate sessions and the role guides under `docs/agents/`.
- Temporary accepted and returned decision records verified with `record_draft_decision.py`.
- `python3 scripts/codex_check.py` and `git diff --check`.

## Completion

- Passing input validation: `check_inputs.py` exited `0`; evidence status `pass`, metrics `output_qty=40`, `case_count=3`, no errors.
- Passing source review: `source_audit.py finalize` and `source_audit.py verify --task tasks/sim-historical-2026-W43-source.md` exited `0`; the task is `ready`, with contract, evidence, and source fingerprints verified.
- Missing-source case: validation and source finalization exited `2`; the evidence and verified temporary task are `blocked` with `ai_ehs.csv: missing source`.
- Separate read-only Codex reviewer returned `PASS` for the draft values, units, period, source hashes, evidence hash, and contract hash. The local `review_demo_report.py` finalize and verify commands both exited `0`; the draft task is `ready` and says it is not accepted.
- Temporary `accepted` and `returned` decision records under `runs/historical-simulation-2026-W43/decisions/` each recorded and verified with exit `0`. These ignored simulation artifacts are not a real human decision and are not committed.
- `python3 scripts/codex_check.py`: `codex-check: PASS`; `git diff --check`: exit `0`; `git check-ignore` confirmed the evidence, reviews, generated draft, and temporary decisions remain ignored.
- Task-state commits: `071af90` (source working), `8d04b86` (source ready), `8dde5eb` (draft working), `cdb0823` (draft ready). Fixture/design commit: `b833cb9`.
- At the user's direction, Windows validation was skipped. Ticket 03 and Ticket 04 remain open for real data.

## Comments

- Imported from the standalone `agents-lab` repository, where this simulation was Ticket 11. In the parent repository, Ticket 11 tracks the ISO-week and output-redaction hardening, so this simulation is numbered Ticket 14.
