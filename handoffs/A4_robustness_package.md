# A4 多工况与鲁棒性证据包

**状态**：`PASS_WITH_DOMAIN_LIMIT`

- 支持域内 5 工况、5 个新 seed、7 参数 +/-10% OAT。
- 三个批次代理均为 `[ASSUMED][UPDATEABLE]`，不是实测批次数据。
- 低温、过充、过放、3C 全部 `[OOD/ABSTAIN]`，数值字段为空。

工程建议只能写成“本仿真条件下的触发规则”，不能提升为行业标准或安全保证。

关键文件：`q4_monte_carlo_raw.csv`、`q4_monte_carlo_summary.csv`、`q4_sensitivity_oat.csv`、`q4_sensitivity_rank.csv`、`q4_ood_abstention.csv`。
