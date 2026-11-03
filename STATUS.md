# Project Status

Status: synthetic-only-stage-complete; awaiting-external-prerequisites
Last updated: 2026-11-03

## Current baseline

- GitHub repository: `hw46hz2ddd-gif/AGENTS-Group`.
- PR #1 was merged as `ddf4cd118b290fca0e9352fbaed8d297ce17314f`, importing `agents-lab/` while preserving the original root README and license.
- PR #2 was merged as `51fcbdd25ab94249b9197124834368f304a27502`, adding parent-repository guidance and structural checks.
- PR #4's Ticket 10 race hardening was merged as `e9d19d3`; PR #5's synthetic-only scope update was merged as `2fa0f3a`, the current `main` head confirmed during this review.
- `agents-lab/` contains the Mac-first synthetic weekly-report pilot and its own guidance, context, status, and ticket tracker.
- Ticket 10's synthetic acceptance gate is implemented. The latest recorded Mac suite has 49 passing tests (PR #4); PR #5 was documentation-only and did not rerun the suite.
- No real export was read. The committed demonstration uses synthetic fixtures only.

## Next task

There is no executable ticket within the current synthetic-only scope. The full ticket inventory is in `agents-lab/.scratch/weekly-report-pilot/issues/`:

- **Tickets 01, 02, 05–10:** closed; synthetic-stage work is complete.
- **Ticket 03 — historical metric validation:** `open` / `needs-info`; skipped for this scope and remains incomplete. Resume only after the data owner approves the metric contract and handling rules, provides one historical export, and the user authorizes processing. Do not read or import real data before then.
- **Ticket 04 — real draft acceptance:** `open` / `needs-info`; blocked by Ticket 03. Keep it incomplete until Ticket 03 and its real-data prerequisites are complete. Acceptance remains a user decision on a specific draft version.
- **Windows validation:** deferred until a Windows environment is available; report Mac verification only until it is actually tested.

No other open TODO/FIXME or executable ticket was found. Do not treat synthetic acceptance or scheduling as completing Ticket 03 or unblocking Ticket 04.

## Blockers

- Ticket 03 needs data-owner approval of the metric contract and handling rules, one export, and user authorization before real-data work can start.
- Ticket 04 depends on Ticket 03 and remains `needs-info` while that dependency is open.
- Windows validation has not been performed.

## Verification

- GitHub confirmed PR #1 and PR #2 merge commits recorded above, PR #4 merged as `e9d19d3`, and PR #5 merged as `2fa0f3a`.
- PR #1's recorded checks: 44 nested unit tests passed, `python3 scripts/codex_check.py` passed, and `git diff --check` passed before integration.
- The latest recorded nested suite is 49 tests passing on Mac in PR #4; no unit tests were rerun for the documentation-only PR #5 or this status update.
- `./scripts/codex-check`: PASS.
- `python3 agents-lab/scripts/codex_check.py`: PASS after the checker was updated to recognize this initialized parent-repository layout.
- `git diff --check`: PASS.
