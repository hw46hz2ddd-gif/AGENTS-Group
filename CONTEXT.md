# Project Context

## Purpose

Host the Agents Group work in one Git repository. The repository currently contains the `agents-lab/` synthetic weekly-report pilot alongside the existing root README and license.

## Scope

### In scope

- Parent-level guidance and status for this repository.
- The `agents-lab/` workflow for deterministic checks, source review, synthetic draft review, and explicit human decisions on reviewed synthetic drafts.

### Out of scope

- Connecting to live business systems or reading real historical exports without the approvals recorded in `agents-lab/docs/historical-week-intake.md`.
- Sending or automatically publishing reports.
- Claiming Windows compatibility before Windows validation.

## Technical shape

- Repository boundary: this Git repository; `agents-lab/` is a subdirectory, not a nested Git repository.
- Language/runtime: Python 3.9+ standard library for the nested pilot; Codex CLI for orchestration.
- Main entry points: `agents-lab/scripts/check_inputs.py`, `agents-lab/scripts/source_audit.py`, `agents-lab/scripts/draft_demo_report.py`, `agents-lab/scripts/review_demo_report.py`, and `agents-lab/scripts/record_draft_decision.py`.
- Parent structural check: `./scripts/codex-check`.
- Nested structural check: `python3 agents-lab/scripts/codex_check.py`.
- Nested unit suite: `python3 -m unittest discover -s tests -v`, run from `agents-lab/`.

## Domain vocabulary

The weekly-report terms and data model are defined in `agents-lab/CONTEXT.md`. Use that document as the source of truth for the nested project.

## Durable decisions

- The existing `agents-lab/` project is integrated under that path; the repository root README and license remain in place.
- Ticket tracking for the pilot stays under `agents-lab/.scratch/weekly-report-pilot/issues/`.
- Stage A uses synthetic data. Ticket 03 remains `needs-info`, Ticket 04 remains blocked by Ticket 03, and Windows validation is deferred.
