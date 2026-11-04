# Historical Intake Approval Preflight

## Intent

Add a machine-checkable preflight to the weekly input path so a real source run cannot start from a contract and directory alone. The check must fail before opening source CSV contents when required approval, processing authorization, handling, or scope information is missing or inconsistent.

The synthetic Stage A workflow must remain runnable without a real owner approval. Tickets 03 and 04 remain real-data work and stay open until actual approved materials are provided.

## Goals

- Require a local machine-readable approval manifest for every non-synthetic input run.
- Bind the manifest to the approved week, contract version and fingerprint, exact input directory, and source file inventory.
- Require declared data-owner approval, user processing authorization, read-only handling, Codex visibility, allowed evidence/output fields, retention, and external-sharing policy.
- Reject missing, incomplete, stale, or mismatched approval before reading source CSV contents.
- Include the manifest fingerprint in generated evidence and make source finalization revalidate the same manifest.
- Keep the manifest, completed human-readable approval form, raw inputs, and generated run artifacts in ignored local paths.
- Exercise both the rejected and accepted preflight paths with synthetic data only.

## Non-goals

- Do not create or simulate a real data-owner approval, user authorization, or export.
- Do not claim cryptographic identity verification. The CLI checks a declared approval record and its consistency; a human still verifies who approved it.
- Do not read real data or run this workflow on Windows as part of implementation.
- Do not send, publish, or automatically accept a report.
- Do not change the report metrics or the existing synthetic result values.

## Approaches

1. **Keep the current manual checklist.** This preserves the current CLI but leaves direct calls to `check_inputs.py` able to read any supplied CSV. It does not meet the selected goal of a CLI preflight.
2. **Add a separate wrapper command.** This can check approval before invoking the validator, but callers can bypass it by calling `check_inputs.py` or `source_audit.py` directly. Rejected for this flow.
3. **Enforce the manifest at the existing input-validation boundary.** Chosen. `check_inputs.py` validates the approval manifest before reading CSVs, and `source_audit.py finalize` passes the same manifest through deterministic revalidation. Existing synthetic contracts opt into an explicit simulation mode; real contracts require approval.

## Proposed design

### Approval manifest

Add a documented JSON manifest format, stored as a Git-ignored local copy next to the completed `docs/historical-week-intake.md` form. The manifest is the machine-readable projection of that human approval record. It contains:

- schema version and `approval_state: approved`;
- `simulation_only: false` for real runs;
- data-owner and approver names/titles, approval date, and a reference plus SHA-256 for the completed human-readable approval record;
- explicit user processing authorization and date;
- target ISO week, contract version and SHA-256, and the exact approved input directory;
- an exact list of approved source filenames and their SHA-256 values;
- handling declarations: source read-only, Codex/model visibility, fields allowed in evidence/output, retention, and external sharing.

The blank manifest template and schema documentation contain placeholders only. The Markdown template remains blank and tracked. Completed approval copies and manifests stay in ignored local paths.

For this pilot, the accepted handling values are deliberately narrow: `read_only: true`, `user_processing_authorized: true`, `codex_visibility: aggregates_only`, `evidence_policy: safe_metadata_and_aggregates`, and `external_sharing: false`. Retention duration and cleanup owner must be present. A manifest requesting raw-row model visibility, external sharing, or a different evidence policy is blocked and requires a separately reviewed project change.

### Validation order and CLI behavior

1. Parse the contract and manifest metadata without opening source CSVs.
2. If the contract is not explicitly marked `simulation_only: true`, require the manifest. Reject a missing manifest, non-approved state, missing required authorization/handling fields, period/version/hash mismatch, unapproved input directory, or source-list mismatch. Write blocked evidence containing only safe diagnostics; do not include raw rows, values, or unapproved paths.
3. After the preflight passes, resolve and compare the approved input directory and contract source filenames. The directory must contain exactly the contract-listed regular files: no extra files, nested directories, or symlinks. Then read the approved files, verify their declared fingerprints, and run the existing deterministic CSV checks.
4. Add the approval-manifest fingerprint and an explicit simulation/real mode marker to evidence. Do not copy owner names, approval references, or local paths into the tracked task ledger.
5. Extend source finalization to take the same manifest path, include its fingerprint in the ignored review evidence, and pass it to deterministic regeneration. Verification checks that the manifest fingerprint still matches.
6. Keep downstream draft review and decision interfaces unchanged; they remain bound to the verified source evidence.

Contracts used for synthetic fixtures will set `simulation_only: true`. To avoid an accidental bypass, the simulation path is accepted only when the input directory is inside the repository's `fixtures/` tree or contains a `simulation-only` path component. Synthetic evidence will say it is simulated and will not claim owner approval. This remains an explicit declaration, not proof that data is synthetic. A non-synthetic contract without a valid manifest exits `2` and produces `status: blocked` before source CSV contents are read.

### Error and privacy rules

- Preflight errors identify the failed field or scope rule, not row contents or raw business values.
- Do not print owner names, approval references, local paths, or CSV rows in command output or tracked task records.
- Evidence records only the approval manifest fingerprint, mode, allowed source filenames, file fingerprints, row counts, approved metrics, and safe diagnostics.
- A successful preflight is evidence that the manifest is complete and internally consistent, not proof that the named approver is authentic.
- Hash contract, approval-record, manifest, and source files as their raw bytes. Formatting-only changes therefore require a fresh approval fingerprint.
- Pass the manifest path explicitly as `--approval-manifest` to `check_inputs.py` and `source_audit.py finalize`; do not auto-discover a file from a default directory. Finalization must use the same manifest whose fingerprint appears in the evidence.
- Use safe diagnostics for both real and synthetic runs. Identify filename, row number, field, and error category without printing cell values, record keys, or full local paths.

## Constraints

- Python 3.9+ standard library only.
- The current synthetic demo and historical simulation continue to run on Mac.
- The new real-run gate is tested with fabricated approval metadata and synthetic CSVs only.
- Use existing task phase CLIs and commit each tracked task-state transition.
- Windows validation remains assigned to Ticket 12 and is not part of this implementation.

## Acceptance criteria

- A non-synthetic contract with no manifest is blocked before any source CSV is opened; evidence contains no source hashes or row counts.
- Synthetic contracts still pass without real approval and are explicitly marked simulated in evidence.
- A complete synthetic approval manifest bound to a synthetic non-simulation contract and fixture files passes.
- Unapproved state, missing user authorization, incomplete handling rules, wrong period, changed contract, unapproved path, missing/extra source file, and changed source fingerprint each block with a locatable safe diagnostic.
- `source_audit.py finalize` rejects or blocks a missing, changed, or mismatched manifest and `verify` detects manifest changes after finalization.
- Existing draft review and decision tests pass with no behavior change to downstream artifacts.
- Full Mac unit suite, structural checker, and artifact verification pass. Ticket 03/04 remain open; no real data is accessed.

## Implementation choices left to the builder

- Exact JSON key spelling and helper-module boundaries, provided the documented required fields and validation order above are preserved.
- Whether a reusable manifest helper is placed in a new module or in `check_inputs.py`, provided source-audit regeneration shares the same validation code.
- The precise safe diagnostic wording, provided it never exposes names, paths, row values, or source contents before approval.
