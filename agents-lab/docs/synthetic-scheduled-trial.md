# Mac 合成数据定时试运行

## 边界

本试运行只使用 `contracts/demo.v1.json` 和 `fixtures/demo/`。Codex 桌面端定时任务负责启动来源核对与生成待复核草稿；草稿复核必须由另一个 Codex 会话完成。`ready` 只表示可供人审阅，不代表 Accepted。不得读取真实历史导出、修改第 03/04 票、对外发送或自动验收。

定时任务使用本机的 `Agents Group` 项目，实际仓库位于其下的 `agents-lab/`。选择本地项目模式，让任务在同一仓库留下任务账本；Mac 需保持开机，桌面端需运行。使用一次性试运行，验收后不保留活动的周期计划。

## 定时任务提示词

创建独立的项目级定时任务时，使用下面的提示词。先在普通会话手动验证命令，再启用定时触发。

```text
在 /Users/louiswang/Documents/ChatGPT/Agents Group/agents-lab 执行一次 Mac 合成周报试运行。先读取该仓库的 AGENTS.md、CONTEXT.md、STATUS.md 和 docs/synthetic-scheduled-trial.md。只使用 contracts/demo.v1.json、fixtures/demo 和 2026-W44；不要读取真实历史数据。为本次运行生成此前未使用的 trial-scheduled-<本地日期时间>-<短随机串> ID，所有命令都在该仓库根目录执行。

按 README.md 的现有 CLI 顺序：source_audit.py start 创建 tasks/<ID>.md；只提交这一任务文件的 working 状态；check_inputs.py 写入 runs/<ID>/evidence.json；source_audit.py finalize 写入 runs/<ID>/source-review.json；核对任务状态。若为 blocked，验证链接并只提交这一任务文件的 blocked 状态，报告具体原因后停止。verify 返回 0 也可能对应 blocked，不得因此进入成稿。若为 ready，运行 source_audit.py verify，且只有任务 frontmatter 的 status 是 ready 才继续；只提交这一任务文件的 ready 状态。然后 draft_demo_report.py 创建 tasks/<ID>-draft.md 和 reports/generated/<ID>-draft.md，并只提交草稿任务的 working 状态。

在结果中报告运行 ID、每步退出码、来源任务状态、草稿任务及文件路径、相关 Git 提交和下一步独立复核命令。草稿复核应由另一个 Codex 会话执行；本次会话不要代替独立复核，不要标记 Accepted，不要发送报告。若任何步骤中断或 Git 提交失败，保留已经生成的任务和本地证据，报告最后成功步骤与失败原因；重试必须使用新 ID，不覆盖旧文件。
```

## 失败与恢复

使用不完整的本地合成输入演练阻塞：`inputs/demo-blocked-2026-W44/` 只有 `mes.csv`。来源复核会把缺少的 `ai_ehs.csv` 写入 `blocked` 任务。`source_audit.py verify` 对一致的阻塞记录也返回 `0`，因此必须检查任务 frontmatter 的状态。恢复时使用新的 ID 和完整的 `fixtures/demo/`；旧任务、证据和草稿保持原样。若中断后留下 `working`，也使用新 ID 重试并在结果中注明旧 ID。

## 查阅与独立复核

在桌面端 **Scheduled** 查看定时运行结果。仓库中查看 `tasks/<ID>.md` 和 `git log -p -- tasks/<ID>.md`；此处 `<ID>` 已包含 `trial-scheduled-` 前缀。本地证据见任务 frontmatter 引用的 `runs/` 路径。独立复核会话读取 `docs/agents/demo-reviewer.md`，再执行：

```sh
python3 scripts/review_demo_report.py --task "tasks/<ID>-draft.md" --out "runs/<ID>-draft/draft-review.json"
python3 scripts/review_demo_report.py verify --task "tasks/<ID>-draft.md"
git add "tasks/<ID>-draft.md"
git diff --cached --check
git commit -m "chore: record <ID> draft review"
```

复核后的 `ready` 草稿仍待人审阅。若证据或草稿发生变化，重新运行对应的 `verify`；不能沿用旧复核结论。真实周报的正式人工验收门禁属于第 04 票。
