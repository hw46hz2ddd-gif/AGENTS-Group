# 03 — 真实历史周的数据口径与只读核对

**What to build:** 数据所有者提供一周历史导出和批准的指标口径后，用户能对该周数据做只读核对，并得到可追溯的证据和待人工确认的异常清单。

**Blocked by:** None — completed baseline `ISSUE-001` provides the input-checking pattern. External prerequisite: data owner supplies an approved metric contract, one historical export, and handling rules.

**Category:** enhancement

**Status:** needs-info

**State:** open

- [ ] 获得数据所有者批准的指标定义、来源、周期、单位、计算方法和处理规则后，才开始真实数据核对。
- [ ] 原始导出保持只读并留在本地受忽略的目录；证据记录来源指纹、校验结果和口径版本。
- [ ] 缺失、口径不符或异常值有可定位的阻塞或人工确认项，不以推测填补。
- [ ] 在 Mac 上对一周历史数据完成一次核对，记录实际命令、结果和待解决事项。

## Comments

- 2026-11-02：用户确认先准备口径模板；真实数据使用尚未获批准。填写并批准 `docs/historical-week-intake.md` 后，再提供本机导出路径和处理规则。本票保持 `needs-info`。
- 2026-11-03：用户指示跳过当前项目范围内的 Ticket 03 验证，并完成合成数据阶段。本票仍保持 `needs-info` 和 `open`，不视为已验证或完成；真实数据核对须等获批 intake、导出及处理授权齐备后另行启动。
