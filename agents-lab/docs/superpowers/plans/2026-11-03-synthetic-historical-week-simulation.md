# Synthetic Historical Week Simulation Implementation Plan

> **For agentic workers:** Execute inline with `superpowers:executing-plans`; steps use checkbox syntax for tracking.

**Goal:** Demonstrate the Ticket 03 and Ticket 04 workflow on a clearly synthetic historical week without treating either real-data ticket as complete.

**Architecture:** Add an isolated fixture and contract, then run the existing validation, source-audit, draft, review, and decision-verification CLIs. Track the simulation as Ticket 14 in the parent repository; keep generated evidence and drafts in ignored local paths. The original standalone tracker used Ticket 11, which the parent repository assigns to ISO-week and output-redaction hardening.

**Tech Stack:** Python 3.9+ standard library, existing repository CLIs, Git-tracked Markdown task records.

**Spec:** `docs/superpowers/specs/2026-11-03-synthetic-historical-week-simulation-design.md`

## Global Constraints

- Use synthetic `2026-W43` data only; no live export or actual owner approval.
- Leave Ticket 03 and Ticket 04 open and incomplete.
- Do not create a committed acceptance record for the generated draft or send/publish anything.
- Skip Windows validation at the user's direction.
- Preserve pre-existing worktree changes; commit only files created or changed for this simulation.

## Review Focus

- A simulated approval must be clearly labeled fictional and must not imply authority to process real data.
- A missing synthetic source must produce a blocked task with a locatable diagnostic.
- A ready draft or passing review must not be described as a real human acceptance.
- Generated evidence and drafts must remain in Git-ignored directories.

---

### Task 1: Add the synthetic intake and historical-week fixture

**Files:**
- Create: `docs/superpowers/specs/2026-11-03-synthetic-historical-week-simulation-design.md`
- Create: `docs/superpowers/plans/2026-11-03-synthetic-historical-week-simulation.md`
- Create: `fixtures/historical-simulation/README.md`
- Create: `fixtures/historical-simulation/intake-simulation.md`
- Create: `fixtures/historical-simulation/mes.csv`
- Create: `fixtures/historical-simulation/ai_ehs.csv`
- Create: `fixtures/historical-simulation/expected.json`
- Create: `contracts/historical-simulation.v1.json`
- Create: `.scratch/weekly-report-pilot/issues/14-synthetic-historical-week-simulation.md`

- [x] Write the fixture metadata first. It must say `SIMULATION ONLY`, identify approval as fictional, name period `2026-W43`, and state that no real data or real approval is included.
- [x] Add two small CSVs and a contract using the existing `load_contract` schema; expected totals are `output_qty=40 pieces` and `case_count=3 cases`.
- [x] Add Ticket 14 with `Status: ready-for-agent`, `State: open`, synthetic-only scope, and independently verifiable acceptance criteria.
- [x] Run `python3 scripts/check_inputs.py --period 2026-W43 --contract contracts/historical-simulation.v1.json --input-dir fixtures/historical-simulation --out runs/historical-simulation-2026-W43/evidence.json`.
- [x] Confirm exit `0`, status `pass`, and exact expected totals. Run `python3 scripts/codex_check.py` and `git diff --check`.
- [x] Commit only the new fixture, contract, design, plan, and standalone Ticket 11 file (`b833cb9`). The parent repository tracks this issue as Ticket 14. The intake detail was added during final review and will be committed with the simulation completion record.

### Task 2: Run and record the source audit

**Files:**
- Create: `tasks/sim-historical-2026-W43-source.md`
- Create locally: source review JSON under `runs/historical-simulation-2026-W43/`

- [x] Start a source task with a unique ID and commit its `working` state.
- [x] Finalize it against the synthetic contract, fixture directory, and deterministic evidence; verify the task is `ready` and its fingerprints match.
- [x] In a temporary copy, remove one source and run validation/source finalization with a fresh ID. Confirm the validator and finalizer return `2` and the blocked record names the missing file.
- [x] Commit the `ready` source task (`8d04b86`). Keep temporary blocked-run artifacts outside tracked task paths unless a distinct blocked example is needed for audit.

### Task 3: Draft and independently review the synthetic report

**Files:**
- Create: `tasks/sim-historical-2026-W43-draft.md`
- Create locally: generated draft and draft-review JSON under ignored directories

- [x] Generate the draft from the ready source task and commit the draft task's `working` state.
- [x] Hand the task path to a separate read-only reviewer Codex session using `docs/agents/demo-reviewer.md`; it returned `PASS`. Then run the deterministic review CLI in the writer session and verify the final task.
- [x] Confirm the draft contains only the expected synthetic totals and reaches `ready`.
- [x] Commit the ready draft task. Do not record a real decision for it.

**Ruling:** The separate reviewer ran read-only and could not write the task ledger. The reviewer supplied a separate `PASS`; the writer session ran the repository review CLI and committed its verified `ready` transition, preserving the separation of judgment and writes.

### Task 4: Close the simulation record and refresh project status

**Files:**
- Modify: `README.md`
- Modify: `STATUS.md`
- Modify: Ticket 03 and Ticket 04 comments
- Modify: Ticket 14 state and completion evidence

- [x] Add a README entry point for the fixture and state that it is not real approval or data.
- [x] Record simulation commands/results in Ticket 14 and close that ticket; state explicitly that real Tickets 03/04 remain open.
- [x] Remove Windows validation from the active checklist and record it as skipped at the user's direction.
- [x] Record the next real-data actions and their prerequisites in `STATUS.md`.
- [x] Run `python3 scripts/codex_check.py` (`codex-check: PASS`) and `git diff --check` (exit `0`); capture the exact outputs from the source, draft, review, and temporary decision CLI runs.
- [x] Commit the standalone Ticket 11 `open` → `closed` transition, intake simulation, and plan progress (`bf91d3e`); its parent-repository identifier is Ticket 14. Keep the pre-existing dirty README/STATUS/Ticket 03/04 files out of that commit to preserve their earlier edits.

## Final review

- Independent read-only review covered the committed simulation range and the current README, STATUS, Ticket 03/04 comments, simulation spec, and fixture README updates.
- Result: Ready; no Critical, Important, or Minor findings. The review confirmed that Tickets 03/04 remain open, Windows is not claimed tested, and temporary decision records do not imply real acceptance.
- Pre-existing dirty implementation/test changes were excluded from the review and left unchanged.
