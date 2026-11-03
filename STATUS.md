# Project Status

Status: parent-context-established; agents-lab-integrated
Last updated: 2026-11-03

## Current baseline

- GitHub repository: `hw46hz2ddd-gif/AGENTS-Group`.
- PR #1 was merged as `ddf4cd118b290fca0e9352fbaed8d297ce17314f`, importing `agents-lab/` while preserving the original root README and license.
- PR #2 was merged as `51fcbdd25ab94249b9197124834368f304a27502`, adding parent-repository guidance and structural checks.
- `agents-lab/` contains the Mac-first synthetic weekly-report pilot and its own guidance, context, status, and ticket tracker.
- Ticket 10's synthetic acceptance gate is implemented. The nested project's Mac suite has 49 passing tests on the current branch.
- No real export was read. The committed demonstration uses synthetic fixtures only.

## Next task

There is no executable parent-level ticket. Continue the nested pilot only when its next prerequisite is available:

- Ticket 03 remains `needs-info` until the data owner approves the metric contract and handling rules and provides one historical export.
- Ticket 04 remains blocked by Ticket 03.
- Windows validation is deferred until a Windows environment is available.

Do not treat the synthetic acceptance gate as completing Ticket 03 or unblocking Ticket 04.

## Blockers

- Ticket 03 needs data-owner approval, handling rules, and an export before real-data work can start.
- Ticket 04 depends on Ticket 03.
- Windows validation has not been performed.

## Verification

- GitHub confirmed the PR #1 and PR #2 merge commits recorded above.
- PR #1's recorded checks: 44 nested unit tests passed, `python3 scripts/codex_check.py` passed, and `git diff --check` passed before integration.
- `./scripts/codex-check`: PASS.
- `python3 agents-lab/scripts/codex_check.py`: PASS after the checker was updated to recognize this initialized parent-repository layout.
- `git diff --check`: PASS.
- The nested 44-test suite is the recorded pre-integration result; it was not rerun during this documentation and structural-check update.
