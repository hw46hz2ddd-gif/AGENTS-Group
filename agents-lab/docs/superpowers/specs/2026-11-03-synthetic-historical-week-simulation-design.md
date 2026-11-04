# Synthetic Historical Week Simulation

## Intent

Exercise the project path that would follow Ticket 03's approval and export prerequisites, then carry its synthetic evidence through Ticket 04's draft review and decision gate. This gives the user a reproducible end-to-end demonstration without accessing business data.

## Goals

- Provide a clearly fictional intake record, metric contract, and one-week CSV export.
- Run the existing validator and source audit against that synthetic week, including one blocked-input case.
- Draft and independently review a report from the passing synthetic evidence.
- Exercise accepted/returned decision recording only with temporary simulation artifacts.
- Preserve Ticket 03 and Ticket 04 as open real-data work, and skip Windows validation at the user's direction.

## Non-goals

- Do not present fictional approval as a data-owner approval or close either real-data ticket.
- Do not read, import, or create any real historical data.
- Do not create an acceptance decision for a committed report or send/publish a report.
- Do not change validator behavior or enable scheduling.

## Constraints

- Use the existing Python standard-library CLIs and task-ledger format.
- Keep all added fixtures visibly labeled synthetic; keep generated evidence and drafts in Git-ignored paths.
- Record the blocked run with a new temporary run ID and never overwrite a finalized task.
- Keep the existing worktree changes intact.

## Approaches

1. Reuse `fixtures/demo` and its `2026-W44` contract. This is quick but would not model a separately approved historical-week intake or keep the simulation distinct from the existing demo.
2. Add a self-contained synthetic historical-week fixture and run it through the existing pipeline. **Chosen:** it is auditable, keeps simulated prerequisites distinct from real approvals, and requires no new runtime behavior.
3. Close Ticket 03/04 using a mock approval and export. Rejected because both tickets explicitly require real historical data; that would misstate project completion.

## Proposed artifacts and flow

- Add `fixtures/historical-simulation/` with an explicitly fictional `intake-simulation.md`, `mes.csv`, `ai_ehs.csv`, and expected totals.
- Add `contracts/historical-simulation.v1.json` for `2026-W43` using the current contract schema.
- Create a tracked source task and draft task with the existing CLIs; keep evidence and generated draft in ignored `runs/` and `reports/generated/` paths.
- Exercise the missing-source failure in a temporary directory and the decision gate using temporary decision artifacts.
- Add Ticket 14 in the parent repository for this bounded simulation. The standalone repository used Ticket 11; the parent repository already assigns that number to ISO-week and output-redaction hardening. Record the simulation evidence, mark it complete, and leave Tickets 03/04 open with the simulation explicitly distinguished from real-data completion.

## Completion criteria

- The validator and source audit produce a verified `ready` source task with the expected synthetic totals, and the missing-source variant is `blocked` with a locatable reason.
- The generated synthetic draft passes independent review and remains `ready` pending a real human decision.
- Temporary decision-gate checks cover accepted and returned outcomes without creating a committed acceptance for the generated draft.
- Ticket 14 closes with commands and observed results; Ticket 03/04 remain open; Windows is marked skipped at the user's direction.
