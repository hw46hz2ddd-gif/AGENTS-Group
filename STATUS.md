# Project Status

Status: synthetic-only-stage-complete; awaiting-external-prerequisites
Last updated: 2026-11-05

## Current baseline

- GitHub repository: `hw46hz2ddd-gif/AGENTS-Group`.
- PR #1 was merged as `ddf4cd118b290fca0e9352fbaed8d297ce17314f`, importing `agents-lab/` while preserving the original root README and license.
- PR #2 was merged as `51fcbdd25ab94249b9197124834368f304a27502`, adding parent-repository guidance and structural checks.
- PR #4's Ticket 10 race hardening was merged as `e9d19d3`; PR #5's synthetic-only scope update was merged as `2fa0f3a`; PR #7's Ticket 11 hardening was merged as `4880920`.
- `agents-lab/` contains the Mac-first synthetic weekly-report pilot and its own guidance, context, status, and ticket tracker.
- Tickets 10–11's synthetic acceptance and redaction gates are implemented. The latest recorded Mac suite has 56 passing tests (PR #7); PR #5 and PR #6 are documentation-only and did not rerun the suite.
- No real export was read. The committed demonstration uses synthetic fixtures only.

## Next task

There is no executable ticket within the current synthetic-only scope. The full ticket inventory is in `agents-lab/.scratch/weekly-report-pilot/issues/`:

- **Tickets 01, 02, 05–13:** closed; synthetic-stage work is complete.
- **Ticket 03 — historical metric validation:** `open` / `needs-info`; skipped for this scope and remains incomplete. Resume only after the data owner approves the metric contract and handling rules, provides one historical export, and the user authorizes processing. Do not read or import real data before then.
- **Ticket 04 — real draft acceptance:** `open` / `needs-info`; blocked by Ticket 03. Keep it incomplete until Ticket 03 and its real-data prerequisites are complete. Acceptance remains a user decision on a specific draft version.
- **Windows validation:** complete for the tested scope under Ticket 12 (Windows 11 build 10.0.26100.8037, commit `eb138f7`). All checks passed; no broader compatibility claim is made.

No other open TODO/FIXME or executable ticket was found. Do not treat synthetic acceptance or scheduling as completing Ticket 03 or unblocking Ticket 04.

## Blockers

- Ticket 03 needs data-owner approval of the metric contract and handling rules, one export, and user authorization before real-data work can start.
- Ticket 04 depends on Ticket 03 and remains `needs-info` while that dependency is open.
- Windows validation passed all Ticket 12 checks for the tested Windows 11 build and commit. Compatibility outside that scope is not claimed.

## Verification

- GitHub confirmed PR #1 and PR #2 merge commits recorded above, PR #4 merged as `e9d19d3`, PR #5 merged as `2fa0f3a`, and PR #7 merged as `4880920`.
- PR #1's recorded checks: 44 nested unit tests passed, `python3 scripts/codex_check.py` passed, and `git diff --check` passed before integration.
- The latest recorded nested suite is 56 tests passing on Mac in PR #7; no unit tests were rerun for the documentation-only PR #5 or PR #6.
- `./scripts/codex-check`: PASS.
- `python3 agents-lab/scripts/codex_check.py`: PASS after the checker was updated to recognize this initialized parent-repository layout.
- `git diff --check`: PASS.
