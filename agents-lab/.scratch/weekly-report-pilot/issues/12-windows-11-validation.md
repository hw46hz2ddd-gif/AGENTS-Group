# 12 — Windows 11 compatibility validation

**What to do:** Run the synthetic checks on the user's Windows 11 machine and record compatibility evidence for the same project commit. No real data is required or permitted for this ticket.

**Blocked by:** None. Requires a Windows 11 checkout of the commit under test and the Python launcher (`py`).

**Category:** enhancement

**Status:** ready-for-human

**State:** open

- [ ] Record the tested Git commit, Windows version, `py -3 --version`, `git --version`, and `codex --version`.
- [ ] From `agents-lab/`, run `py -3 scripts/codex_check.py` and `py -3 -m unittest discover -s tests -v`; record exact results.
- [ ] Run the synthetic input validator and confirm `status: pass`, `output_qty=30`, and `case_count=1`.
- [ ] Start Codex from the project directory and confirm it loads the project `AGENTS.md` guidance using a read-only prompt.
- [ ] Record any Windows-specific failures without claiming compatibility until all checks pass.

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

- Tested commit: pending
- Windows version: pending
- Python / Git / Codex versions: pending
- Structural check: pending
- Unit suite: pending
- Synthetic validator: pending
- Codex loaded project guidance: pending

## Comments

- 2026-11-04：用户表示 Windows 验证暂时跳过，并会在 Windows 上另行测试；本票交由用户执行，当前没有 Windows 结果或兼容性声明。
