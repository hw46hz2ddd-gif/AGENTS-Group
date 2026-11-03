# Local task ledger

One weekly-report run has a tracked source task and, when inputs pass, a separate tracked draft task. Each phase's CLI writes its own task record. `working` means that phase awaits review, `ready` means its review passed, and `blocked` means the record lists reasons that must be resolved in a new task version. A ready draft awaits human review; it is not Accepted.

Raw inputs and generated evidence stay in Git-ignored local directories. A task records their paths and SHA-256 fingerprints. Source finalization re-runs deterministic input validation and compares its evidence with the supplied result. Run `source_audit.py verify` for a source task and `review_demo_report.py verify` for a draft task before trusting either final status. These checks report changes to linked local artifacts. Git can replay task metadata and its author and commit time, but cannot reconstruct ignored evidence or draft bytes.

Commit each task's `working` record before review, then commit its `ready` or `blocked` record after review. Keep source-review and draft-review output under `runs/` alongside validator evidence; keep generated drafts under `reports/generated/`.

A human decision is a separate immutable task record with `status: decided` and `decision: accepted` or `decision: returned`. Create it only after a person chooses for a specific `ready` draft. Returned decisions require a reason. `record_draft_decision.py verify` revalidates the draft review and its linked draft and evidence fingerprints; a changed artifact invalidates the decision record. A ready draft or passing review alone is never acceptance.
