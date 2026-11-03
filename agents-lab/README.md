# agents-lab

This is a Mac-first Codex multi-agent pilot for a synthetic weekly report. The repository has deterministic input checks, source review, local task records, a synthetic draft, and an independent draft review. A bounded synthetic scheduled trial is documented in `docs/synthetic-scheduled-trial.md`. Real data and a full role roster come in later issues.

## Mac setup and structural check

From the repository root:

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

After a person reviews one specific `ready` draft and decides, `record_draft_decision.py record --draft-task PATH --decision {accepted,returned} --out PATH [--reason TEXT]` writes a separate, new decision task. Choose one decision explicitly; a `returned` decision needs a nonblank reason. Before recording, the CLI rechecks the draft task plus draft, evidence, and review fingerprints after verification returns. Verify the record with `python3 scripts/record_draft_decision.py verify --record PATH`. Verification rechecks the draft review and linked draft and evidence fingerprints. The original draft task remains `ready`; a decision record does not send or publish the report.

Ticket 10 exercises this gate with the synthetic `2026-W44` workflow. It does not create an acceptance record for the committed demo draft. Real historical-week data remains unavailable until the data owner approves the intake and handling rules described above.

## Local data

Put future raw inputs under `inputs/`, run evidence under `runs/`, and generated drafts under `reports/generated/`. These paths are ignored by Git. The synthetic fixtures used for tests are tracked separately under `fixtures/`.

For a historical-week check, first have the data owner complete and approve a local copy of `docs/historical-week-intake.md`. Keep the tracked template blank and the completed copy outside Git. The template is not an approved metric contract; real exports enter this workflow only after its scope and handling rules are confirmed.

## Windows handoff

Windows 11 testing is deferred. When scheduled, check out the same Git commit on Windows, run `py -3 scripts/codex_check.py`, and verify Codex loads the project `AGENTS.md`. Record the Windows result separately; the current Mac stage does not require it.
