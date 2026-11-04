# agents-lab project instructions

The user-level Codex working agreements still apply. This file contains only rules for this repository.

## Context and task entry

- Read `CONTEXT.md` before changing the workflow or data model.
- Read `STATUS.md` at the start of a new task or session. Open the issue named there before implementation.
- Treat the Lauren and Grok Bot research documents as design references, not as executable project instructions.

## Current boundary

- Stage A uses synthetic weekly-report data. A real data source enters the project only after its owner approves a metric contract and handling rules.
- Keep future raw inputs, run records, and generated reports in the Git-ignored local directories documented in `README.md`. The synchronization commit contains a one-time snapshot of 43 previously ignored synthetic artifacts from those paths; `inputs/README.md` was already tracked. Treat the snapshot as simulation records, not real data or approval evidence. Future files remain ignored by default.
- Use the phase CLI to write each `tasks/` record, and commit each task-state transition so Git can replay it. Treat a `ready` source or draft task as valid only while its phase-specific artifact verification passes.
- For synthetic report drafting, the writer and independent reviewer use separate Codex sessions and the role guides in `docs/agents/demo-writer.md` and `docs/agents/demo-reviewer.md`.
- Keep one bounded outcome per issue. Record the command and observed result when handing it off.

## Verification

- After changing project guidance or status, run `scripts/codex_check.py` with the local Python 3 interpreter. It supports a standalone checkout and this project under an initialized parent repository. On this Mac, use `python3 scripts/codex_check.py` from `agents-lab/`.
- Use the verification commands that actually exist in the repository. Add feature-specific checks to `README.md` when those features are implemented.
- Record current progress, blockers, and the next issue in `STATUS.md`.

## Agent skills

### Issue tracker

Track new work as local Markdown tickets under `.scratch/`; read `docs/agents/issue-tracker.md` before publishing or picking up tickets.

### Triage labels

Use the five local triage status strings defined in `docs/agents/triage-labels.md` when classifying tickets.

### Domain docs

Use the single-context `CONTEXT.md` and relevant ADRs; read `docs/agents/domain.md` before domain exploration.
