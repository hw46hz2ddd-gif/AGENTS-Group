# Simulated historical-week intake

> **SIMULATION ONLY — this is not a real approval.**

| Field | Simulated value |
| --- | --- |
| Data owner | Fictional example owner |
| Approver | Fictional example approver |
| Approval state | Simulated for workflow exercise only |
| Contract version | `historical-simulation-v1` |
| Period and timezone | `2026-W43`, `Asia/Shanghai`, 2026-10-19 through 2026-10-25 |
| Allowed purpose | Exercise the local synthetic source and draft workflow |
| Export files | `mes.csv` and `ai_ehs.csv` in this directory |
| Metric definitions | `output_qty` is an integer sum in pieces; `case_count` is an integer sum in cases |
| Handling | Read fixture files unchanged; record fingerprints; missing source or invalid rows block the run; never infer missing values |
| Model visibility | Synthetic values only; no real records or business data |
| External sharing | Not part of this simulation |

Every identity and value above is fictional. This file cannot authorize access to, copying of, or processing any actual business export. A real Ticket 03 still requires the data owner's actual approved intake, a real export, handling rules, and the user's authorization.
