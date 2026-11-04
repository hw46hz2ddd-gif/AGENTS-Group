# 03 — 真实历史周的数据口径与只读核对

**What to build:** 数据所有者提供一周历史导出和批准的指标口径后，用户能对该周数据做只读核对，并得到可追溯的证据和待人工确认的异常清单。

**Blocked by:** None — completed baseline `ISSUE-001` provides the input-checking pattern. External prerequisite: data owner supplies an approved metric contract, one historical export, and handling rules.

**Category:** enhancement

**Status:** needs-info

**State:** open

## 前置条件跟踪

- [x] 用户处理授权：2026-11-04 用户明确授权按本票范围推进真实数据只读核对；仅在获批口径、处理规则和指定导出交付并核对后执行。
- [ ] 数据所有者批准的指标口径及处理规则：尚未提供。
- [ ] 获批的一周历史导出及允许披露的本机路径或中性别名：尚未提供；当前未检查或导入真实数据。

- [ ] 获得数据所有者批准的指标定义、来源、周期、单位、计算方法和处理规则后，才开始真实数据核对。
- [ ] 原始导出保持只读并留在本地受忽略的目录；证据记录来源指纹、校验结果和口径版本。
- [ ] 缺失、口径不符或异常值有可定位的阻塞或人工确认项，不以推测填补。
- [ ] 在 Mac 上对一周历史数据完成一次核对，记录实际命令、结果和待解决事项。

## Comments

- 2026-11-02：用户确认先准备口径模板；真实数据使用尚未获批准。填写并批准 `docs/historical-week-intake.md` 后，再提供本机导出路径和处理规则。本票保持 `needs-info`。
- 2026-11-03：用户指示跳过当前项目范围内的 Ticket 03 验证，并完成合成数据阶段。本票仍保持 `needs-info` 和 `open`，不视为已验证或完成；真实数据核对须等获批 intake、导出及处理授权齐备后另行启动。
- 2026-11-03：用户随后授权模拟前置条件。Ticket 14 用虚构 intake 和合成 `2026-W43` 导出验证了通过及缺失来源阻塞路径；这不满足本票的真实数据验收条件。保持本票 `needs-info` / `open`，直至真实口径、导出、处理规则和用户授权齐备。
- 2026-11-04：用户明确授权推进真实数据只读核对，已记录为用户处理授权；这不代表数据所有者已批准指标口径或处理规则。完成版获批 intake 与一周导出路径仍未提供，故本票继续 `needs-info` / `open`，且未读取或导入真实数据。
- 2026-11-04：复跑 Ticket 14 合成闭环，49 项测试通过；`2026-W43` 合成数据通过（`output_qty=40`、`case_count=3`），缺少 `ai_ehs.csv` 的变体按预期阻塞。流程审查确认 CLI 不认证数据所有者批准、用户授权、处理规则、数据可见级别或获准路径；真实数据运行前必须由人核对完成版获批 intake。Ticket 03 仍为 `needs-info` / `open`。
- 2026-11-04：按用户要求将合成批准单和 CSV 复制到 Git 忽略的 `inputs/historical-week/simulation-only/2026-W43/`，新任务 `sim-localpath-20261104` 的 source 与 draft 均通过验证；独立复核为 PASS。草稿为 `ready`，临时 accepted/returned 决策记录均以 `SIMULATION ONLY` 原因完成并验证；未形成真实用户验收。这是本机合成演练，不满足真实数据验收条件，本票仍 `needs-info` / `open`。
