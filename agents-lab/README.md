# agents-lab

This is a Mac-first Codex multi-agent pilot for a synthetic weekly report. The repository has deterministic input checks, source review, local task records, a synthetic draft, and an independent draft review. A bounded synthetic scheduled trial is documented in `docs/synthetic-scheduled-trial.md`. Real data and a full role roster come in later issues.

## Mac setup and structural check

From the `agents-lab/` project directory (the subdirectory in `AGENTS-Group`):

```sh
codex --version
python3 --version
git --version
python3 scripts/codex_check.py
./scripts/codex-check
```

`STATUS.md` records the latest observed results. Read `CONTEXT.md` and the issue named in `STATUS.md` before feature work.

## Synthetic input validation on Mac

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_inputs.py --period 2026-W44 --contract contracts/demo.v1.json --input-dir fixtures/demo --out runs/demo-2026-W44/evidence.json
```

The command exits `0` with `status: pass` for the fixed demo sample. An invalid input or contract exits `2` and writes `status: blocked` with locatable errors. The evidence includes the contract and source SHA-256 hashes, row counts, and aggregate metrics. It has no timestamp, so identical inputs produce identical output bytes. The generated evidence stays under the Git-ignored `runs/` directory.

The contract's inclusive `start_date` and `end_date` must be the Monday and Sunday of its declared ISO week. Row-level diagnostics identify the source file and row but omit raw record keys and dates. Contract date errors also avoid echoing the supplied date value.

## Source review and task ledger on Mac

For a fresh synthetic run in a macOS shell, create a tracked task before validating inputs. The generated ID prevents reuse of an immutable task:

```sh
run_id="demo-$(date +%Y%m%d-%H%M%S)-$$"
python3 scripts/source_audit.py start --task "tasks/$run_id.md" --id "$run_id" --period 2026-W44
git add "tasks/$run_id.md"
git commit -m "chore: start $run_id task"
python3 scripts/check_inputs.py --period 2026-W44 --contract contracts/demo.v1.json --input-dir fixtures/demo --out "runs/$run_id/evidence.json"
python3 scripts/source_audit.py finalize --task "tasks/$run_id.md" --contract contracts/demo.v1.json --input-dir fixtures/demo --evidence "runs/$run_id/evidence.json" --review "runs/$run_id/source-review.json"
python3 scripts/source_audit.py verify --task "tasks/$run_id.md"
git add "tasks/$run_id.md"
git commit -m "chore: record $run_id source review"
git log -p -- "tasks/$run_id.md"
```

`finalize` returns `0` for a `ready` task and `2` for a `blocked` task; both paths write a source-review file and update the task. A finalized task is immutable. Start a new task for a corrected run. Commit each state change to preserve who changed it and when. The task's artifact paths point to local files under `runs/`; verify them before downstream work.

Generated task links are relative to the task record. The review stores repository files as `project:` references and external local files relative to the review artifact. `verify` resolves those references and supports earlier task records. Review errors are copied from deterministic validation only when the evidence matches the current inputs, so edited evidence cannot inject raw values into task text.

Older tasks with absolute artifact links remain readable. Draft creation normalizes those links before writing new draft content and task records.

## Synthetic draft and independent review on Mac

Use a source task whose status is `ready`; the writer also verifies its local evidence before drafting. The committed demo source task below needs its Git-ignored local evidence. On a new checkout, first run the source workflow above and substitute the new source task path. Run the writer and reviewer steps in separate Codex sessions using `docs/agents/demo-writer.md` and `docs/agents/demo-reviewer.md`. The commands below show the handoff in one shell; use a fresh ID on each run:

```sh
draft_id="draft-$(date +%Y%m%d-%H%M%S)-$$"
python3 scripts/draft_demo_report.py --source-task tasks/demo-pass-2026-W44.md --task "tasks/$draft_id.md" --draft "reports/generated/$draft_id.md" --id "$draft_id"
git add "tasks/$draft_id.md"
git commit -m "chore: start $draft_id review"
python3 scripts/review_demo_report.py --task "tasks/$draft_id.md" --out "runs/$draft_id/draft-review.json"
python3 scripts/review_demo_report.py verify --task "tasks/$draft_id.md"
git add "tasks/$draft_id.md"
git commit -m "chore: record $draft_id review"
git log -p -- "tasks/$draft_id.md"
```

The draft cites the exact evidence and source fingerprints. Missing historical values display `—`. The independent reviewer checks values, units, source names, evidence references, and any numeric claim outside the metric table; it returns `0` with a `ready` task or `2` with a `blocked` task and locatable findings. Run the draft `verify` command again before handing a reviewed version to a person. `ready` means the draft can be presented to a person. It never means Accepted or sent.

## Human decision on a reviewed draft

After a person reviews one specific `ready` draft and decides, `record_draft_decision.py record --draft-task PATH --decision {accepted,returned} --out PATH [--reason TEXT]` writes a separate, new decision task. Choose one decision explicitly; a `returned` decision needs a nonblank reason. Immediately before opening the new decision file, the CLI rechecks the complete draft-task bytes and draft, evidence, and review fingerprints against the verified snapshot. It refuses to write if any differ. Verify the record with `python3 scripts/record_draft_decision.py verify --record PATH`. Verification rechecks the draft review and linked draft and evidence fingerprints. The original draft task remains `ready`; a decision record does not send or publish the report.

Ticket 10 exercises this gate with the synthetic `2026-W44` workflow. It does not create an acceptance record for the committed demo draft. Real historical-week data remains unavailable until the data owner approves the intake and handling rules described above.

## Local data

Put future raw inputs under `inputs/`, run evidence under `runs/`, and generated drafts under `reports/generated/`. These paths are ignored by Git. The synthetic fixtures used for tests are tracked separately under `fixtures/`.

For a historical-week check, first have the data owner complete and approve a local copy of `docs/historical-week-intake.md`. Keep the tracked template blank and the completed copy outside Git. The template is not an approved metric contract; real exports enter this workflow only after its scope and handling rules are confirmed.

## Historical intake approval preflight

Every contract without `simulation_only: true` now requires an explicit machine-readable approval manifest before the validator opens source CSV contents. Start from `docs/historical-week-intake.manifest.example.json`; it contains placeholders and deliberately unapproved values. After the data owner and approver complete the intake, keep the approved Markdown copy, completed manifest, and manifest-referenced approval record in a Git-ignored local directory such as `inputs/historical-week/approval/`. Keep the source CSVs in the separately approved input directory; it must contain exactly the approved contract files, with no extra entries, subdirectories, or symlinks. Check a chosen local path with `git check-ignore -- <path>` before storing approval material under the repository.

The manifest binds a valid ISO week and its exact Monday-to-Sunday contract date range, contract version and raw-byte fingerprint, exact resolved input directory, source filenames and fingerprints, user processing authorization, and the allowed handling policy. The pilot accepts only read-only processing, `aggregates_only` Codex visibility, `safe_metadata_and_aggregates` evidence, and no external sharing. The validator checks that the declared fields and fingerprints agree; it does not cryptographically authenticate the named owner or approver. A person must verify the actual approval and handling scope before running real data. No real owner approval or export is included in this repository.

Evidence output must be outside all protected input, fixture, contract, manifest, and approval-record paths, including hard-link aliases to those files. An unsafe `--out` target exits `2` without writing evidence there. Source finalization applies the same path boundary to its task, evidence, and review files; this prevents a source CSV from being read as evidence or overwritten as a review artifact. Task diagnostics are regenerated from the validator and never copy raw error text from a supplied evidence file.

For a future approved real run, pass the same local manifest explicitly to both validation and source finalization:

```sh
# Replace these values using the approved intake before running any command.
RUN_ID="approved-2026-WNN-001"
PERIOD="YYYY-Www"
APPROVED_CONTRACT="contracts/approved-contract.v1.json"
APPROVED_INPUT_DIR="/absolute/approved/input/directory"
APPROVAL_MANIFEST="/absolute/ignored/approval/manifest.json"

python3 scripts/source_audit.py start --task "tasks/$RUN_ID.md" --id "$RUN_ID" --period "$PERIOD"
git add "tasks/$RUN_ID.md"
git commit -m "chore: start $RUN_ID task"
python3 scripts/check_inputs.py --period "$PERIOD" --contract "$APPROVED_CONTRACT" --input-dir "$APPROVED_INPUT_DIR" --approval-manifest "$APPROVAL_MANIFEST" --out "runs/$RUN_ID/evidence.json"
python3 scripts/source_audit.py finalize --task "tasks/$RUN_ID.md" --contract "$APPROVED_CONTRACT" --input-dir "$APPROVED_INPUT_DIR" --evidence "runs/$RUN_ID/evidence.json" --review "runs/$RUN_ID/source-review.json" --approval-manifest "$APPROVAL_MANIFEST"
python3 scripts/source_audit.py verify --task "tasks/$RUN_ID.md"
git add "tasks/$RUN_ID.md"
git commit -m "chore: record $RUN_ID source review"
```

Use this sequence only after Ticket 03's actual owner-approved metric and handling rules, contract, export, and permitted local path have been supplied and checked. The local review artifact records the manifest path and fingerprint; the tracked task contains only run mode and fingerprint. The synthetic commands earlier in this README intentionally omit the manifest and use only explicitly marked fixtures or `simulation-only` paths. Tickets 03 and 04 remain open; Windows validation remains the user-run Ticket 12.

## Windows handoff

Windows 11 compatibility validation is user-run Ticket 12. On Windows, check out the same Git commit, run `py -3 scripts/codex_check.py`, `py -3 -m unittest discover -s tests -v`, and the synthetic validator command listed in `.scratch/weekly-report-pilot/issues/12-windows-11-validation.md`; then record the tested commit and exact results there. No Windows result or compatibility claim is recorded here.
