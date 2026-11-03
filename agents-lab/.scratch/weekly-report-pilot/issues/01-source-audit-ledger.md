# 01 — 来源审查与任务账本

**What to build:** 用户对一轮合成数据核对能看到来源审查结论、证据引用和任务状态；遇到来源问题时，该轮任务停在可解释的阻塞状态。

**Blocked by:** None — completed baseline `ISSUE-001` already provides deterministic input evidence.

**Category:** enhancement

**Status:** ready-for-agent

**State:** closed

- [x] 一轮有效合成输入有可追溯的来源审查结论、证据引用和任务状态，用户可以从账本定位对应证据。
- [x] 来源缺失、指纹不一致或校验阻塞时，账本记录原因，且不能显示为已完成。
- [x] 任务状态变更可以由 Git 历史回放；同一轮运行的状态与证据不会互相矛盾。
- [x] 在 Mac 上演示一次通过和一次阻塞的完整流转，并记录命令与结果。
