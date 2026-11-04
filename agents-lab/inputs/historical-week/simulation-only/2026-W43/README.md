# Synthetic historical-week simulation

> **SIMULATION ONLY — no real business data or real approval is present.**

This fixture includes `intake-simulation.md`, a fictional intake that simulates the prerequisites for Ticket 03. The named approval is not from a real data owner and grants no authority to access or process business data. Use it only with the synthetic CSVs in this directory.

- Simulated period: `2026-W43` (`2026-10-19` through `2026-10-25`), `Asia/Shanghai`.
- Simulated metric contract: `contracts/historical-simulation.v1.json`.
- Simulated export files: `mes.csv` and `ai_ehs.csv`.
- Simulated expected totals: `output_qty=40 pieces`, `case_count=3 cases`.
- Simulated handling: read the fixture files as supplied, preserve them unchanged, and report missing or invalid input as blocked. Do not infer missing values.

The approval, contract, period, data, and totals are all fictional test inputs. They must not be copied into a real intake or treated as approved production definitions.
