# Project Context

## Purpose

Build a small, reproducible Codex workflow for checking weekly-report inputs, reviewing a draft, and trialing a local schedule with synthetic data before considering real business data.

## Scope

### In scope

- A synthetic weekly-report demonstration on the current Mac.
- Deterministic input checks, evidence, local task records, source review, and a separate synthetic draft review.
- A bounded Codex desktop scheduled trial using only synthetic inputs, with human review of its result.
- A repository layout that can be handed to a separate Windows 11 test later.

### Out of scope for the current stage

- Connecting to MES, AI/EHS, Notion, or other live systems.
- Sending reports, automatic publication, automatic code merging, or scheduling with real business data.
- Claiming Windows compatibility before that machine is tested.

## Technical shape

- Language/runtime: Python 3.9+ standard library for deterministic checks; Codex CLI for orchestration; Git for project guidance and synthetic fixtures.
- Main entry points: `scripts/check_inputs.py` validates the synthetic week; `scripts/source_audit.py` reviews source fingerprints; `scripts/draft_demo_report.py` creates a draft; `scripts/review_demo_report.py` reviews the draft independently.
- Current checks: `python3 -m unittest discover -s tests -v` and `python3 scripts/codex_check.py` on Mac.
- Data: `inputs/`, `runs/`, and `reports/generated/` are local and Git-ignored.
- Task records in `tasks/` are Git-tracked; the source evidence they reference stays local, with fingerprints in each record.

## Domain vocabulary

- **Metric contract:** an approved definition of each report value, its source, period, unit, and calculation.
- **Evidence:** source fingerprints, deterministic check results, and review findings tied to one run.
- **Source review:** a check that the current contract and source fingerprints match a reproducible validator result for one run.
- **Task ledger:** Git-tracked status and artifact fingerprints for a run; the referenced input and evidence files remain local.
- **Draft review:** an independent check of a specific draft version against its source task, evidence, and metric contract.
- **Accepted:** a specific draft version reviewed by a person, never an inferred status from a successful command alone.

## Durable decisions

- The project `AGENTS.md` is the source of project-specific guidance; the existing user-level `AGENTS.md` remains unchanged.
- Mac verification is the current gate. Windows testing is deferred and will be recorded separately.
- The design borrows engineering Bot coordination from Lingxi Li's public Grok Bot account and verification practices from Lauren Tan's PStack. It does not attribute Lingxi's named Bot team to Lauren.
