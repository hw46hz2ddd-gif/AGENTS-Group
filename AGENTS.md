# AGENTS-Group project instructions

Global Codex working agreements apply. This file describes the parent repository.

## Repository layout

- The current working subproject is `agents-lab/`. Before changing it, read `agents-lab/AGENTS.md`, `agents-lab/CONTEXT.md`, and `agents-lab/STATUS.md`.
- The `agents-lab/` directory owns its implementation tickets and issue tracker. Read `agents-lab/docs/agents/issue-tracker.md`; do not duplicate those tickets at the repository root.
- Keep parent-level changes limited to repository organization and shared context unless a separate project task says otherwise.

## Data and verification boundaries

- Use only the tracked synthetic fixtures for the current pilot.
- Do not read or import real historical data until the data owner approves the metric contract and handling rules, provides one export, and authorizes the processing scope.
- Ticket 03 remains `needs-info`; synthetic work does not complete it or unblock Ticket 04.
- Windows validation remains deferred until it is run on Windows.

## Verification

- Run `./scripts/codex-check` after changing parent-level project guidance or status.
- Run `python3 agents-lab/scripts/codex_check.py` after changing the nested project's guidance or status.
- Use the tests and checks documented under `agents-lab/README.md` when a code change requires them. Report the exact commands and results.
