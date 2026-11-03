# Synthetic draft acceptance gate

## Intent

Add an explicit, auditable human decision after a synthetic report draft passes its independent review. The current draft workflow ends at `ready`; this gate will record whether a specific reviewed version was accepted or returned, without treating a passing review as acceptance.

## Goals

- Record an explicit `accepted` or `returned` decision for a reviewed draft.
- Bind the decision to the draft task, draft SHA-256, and evidence SHA-256.
- Verify the decision record against the current draft and evidence so changed artifacts cannot retain a valid acceptance.
- Exercise the workflow with the existing synthetic `2026-W44` artifacts.

## Non-goals and anti-goals

- Do not read or import real historical data; Ticket 03 remains `needs-info`.
- Do not create an acceptance decision for the existing demo draft as part of implementation. Tests may exercise both decisions using temporary records.
- Do not send, publish, or automatically accept any report.
- Do not mark Ticket 04 complete; its real historical-week demonstration remains blocked by Ticket 03.

## Constraints

- Keep the existing reviewed draft task immutable and retain its `ready` status.
- Keep decision metadata in tracked task records; generated evidence and drafts remain in the existing Git-ignored locations.
- A returned decision must include a human-readable reason. A decision record must not overwrite an earlier record.
- The repository's existing CLI and standard-library Python conventions apply.

## Approaches

1. Change a draft task's `ready` status to `accepted` or `returned`. This is small, but it mutates the record whose status and hashes are verified by the existing independent review workflow.
2. Create a separate immutable decision record linked to the reviewed draft and its fingerprints. This preserves the review record and makes the human decision independently verifiable. **Chosen:** the user selected a synthetic-data acceptance gate while keeping real-data acceptance unfinished; this approach fits that scope and the existing task ledger.
3. Add an interactive desktop UI or external approval service. This adds dependencies and external side effects without helping the current local synthetic trial.

## Proposed behavior

Provide a local CLI operation to record `accepted` or `returned` for a `ready` draft after running the existing draft verification. Write a new tracked decision record containing the draft task path and ID, the decision, the current draft and evidence fingerprints, and a return reason when applicable. Provide a verification operation that checks the record and confirms the linked task and artifacts still match. Reject blocked or unreviewed drafts, missing return reasons, mismatched artifacts, and attempts to reuse an existing decision-record path.

The CLI invocation is the explicit human decision; implementation and tests must not create an accepted record for the committed demo draft. Git history supplies author and commit time for a recorded decision.

## Remaining for implementation

Choose concrete CLI names and record format consistently with the existing scripts and `tasks/` records. Add automated coverage for acceptance, return, invalid states, immutable paths, and fingerprint changes. Document the synthetic-only example and keep Ticket 04 blocked until an approved real-data intake exists.
