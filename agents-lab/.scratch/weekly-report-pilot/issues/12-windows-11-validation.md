# 12 — Windows 11 compatibility validation

**What to do:** Run the synthetic checks on the user's Windows 11 machine and record compatibility evidence for the same project commit. No real data is required or permitted for this ticket.

**Blocked by:** None. Requires a Windows 11 checkout of the commit under test and the Python launcher (`py`).

**Category:** enhancement

**Status:** ready-for-human

**State:** open

- [x] Record the tested Git commit, Windows version, `py -3 --version`, `git --version`, and `codex --version`.
- [x] From `agents-lab/`, run `py -3 scripts/codex_check.py` and `py -3 -m unittest discover -s tests -v`; record exact results.
- [x] Run the synthetic input validator and confirm `status: pass`, `output_qty=30`, and `case_count=1`.
- [ ] Start Codex from the project directory and confirm it loads the project `AGENTS.md` guidance using a read-only prompt.
- [x] Record any Windows-specific failures without claiming compatibility until all checks pass.

## Windows commands

Run these from the `agents-lab/` project directory in PowerShell:

```powershell
py -3 --version
git --version
codex --version
py -3 scripts/codex_check.py
py -3 -m unittest discover -s tests -v
py -3 scripts/check_inputs.py --period 2026-W44 --contract contracts/demo.v1.json --input-dir fixtures/demo --out runs/windows-smoke-2026-W44/evidence.json
Get-Content -Raw runs/windows-smoke-2026-W44/evidence.json | ConvertFrom-Json | Format-List status,period,metrics
git status --short
```

The final Codex check is read-only: start Codex in this project directory and ask it to summarize the Stage A data boundary from `AGENTS.md`. Use only the tracked synthetic fixture in these checks.

## Results

- Tested commit: baseline `30668800542ec3d255baa4cb50faf0386eb78978` (branch `main`); the test-portability fix is in the commit that contains this ticket update.
- Windows version: Windows 11, build 10.0.26100.8037
- Python / Git / Codex versions: Python 3.14.6 (`py -3`) / git 2.56.0.windows.4 (recheck; the initial run recorded 2.55.0.windows.3) / codex-cli 0.166.0-alpha.6 (`C:\Users\wangzilong\AppData\Local\OpenAI\Codex\bin\a159911ff70742e9\codex.exe`; on PATH during the recheck, while the initial run recorded it as not on PATH)
- Structural check: `py -3 scripts/codex_check.py` → `codex-check: PASS (D:\Agents Group\agents-lab)`, exit 0
- Unit suite after the test-portability fix: `py -3 -m unittest discover -s tests -v` → Ran 92 tests in 72.873s, OK (skipped=1), exit 0.
  - `test_symlinked_source_is_rejected`: skipped on Windows when symlink creation raises `WinError 1314`; the macOS/POSIX symlink fixture is unchanged.
  - `test_contract_source_name_with_control_characters_is_rejected`: the Windows branch asserts the contract-name rejection without creating a filename containing `\n`; the POSIX branch still creates the real file.
- Synthetic validator: `py -3 scripts/check_inputs.py --period 2026-W44 --contract contracts/demo.v1.json --input-dir fixtures/demo --out runs/windows-smoke-2026-W44/evidence.json` → exit 0, `status: pass`, `period: 2026-W44`, `output_qty: 30`, `case_count: 1`. Evidence written under Git-ignored `runs/windows-smoke-2026-W44/evidence.json`.
- Codex loaded project guidance: **incomplete.** The CLI launches correctly from `agents-lab/` (read-only sandbox, session created, workdir detected), but the model call fails before a response: the local `~/.codex/config.toml` uses `model_provider = "custom"` with `base_url = http://127.0.0.1:57321/v1`, and port 57321 is not listening on this machine, so `codex exec` ends with 502/connection-refused. Re-run this check once the local model gateway is up. No compatibility claim is made.
- Codex recheck command (Git Bash, once the local gateway is listening): `codex exec --sandbox read-only --skip-git-repo-check "Summarize the Stage A data boundary from AGENTS.md in one sentence." < /dev/null` from `agents-lab/`.
- `git status --short` immediately after the checks (before recording these results): clean. Evidence stays under ignored `runs/`; this ticket update is the only tracked change until it is committed.

## Comments

- 2026-11-04：用户表示 Windows 验证暂时跳过，并会在 Windows 上另行测试；本票交由用户执行，当前没有 Windows 结果或兼容性声明。
- 2026-11-04：用户在 Windows 11 机器（`D:\Agents Group` 检出同一 commit）上通过 WorkBuddy 执行了本票的命令清单并记录上述结果。命令通过 Git Bash 调用 `py -3`（Windows Python launcher）。单元测试有 2 个 Windows 专属的夹具构造错误（symlink 权限、控制字符文件名），属测试环境差异，未改任何代码。Codex 加载检查因本地模型网关（127.0.0.1:57321）未运行而未完成；网关启动后重跑该单项即可。在全部检查通过前不声明 Windows 兼容性。
- 2026-11-04：在 Windows 11 上复验并修正测试夹具。完整套件 92 项通过（1 项 Windows symlink 跳过），结构检查与合成验证器仍通过；未改产品脚本，macOS/POSIX 测试路径保持不变。Codex 加载检查仍因本地模型网关（127.0.0.1:57321）未监听而未完成，继续不声明 Windows 兼容性。
