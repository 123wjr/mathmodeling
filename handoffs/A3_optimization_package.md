# A3 筛选与编组优化证据包

**状态**：`PASS_WITH_ASSUMED_THRESHOLDS`

- 候选 108，过门槛 85，候选组 3167。
- MILP 固定 8 组 x 4 电芯；重复分配=0，错误组规模=0。
- 性能/平衡/保守三权重 + greedy 对照；只使用归一化无量纲成本收益。

`[ASSUMED][UPDATEABLE]` 所有门槛和权重待真实检测误差、安全规范和商业数据更新。没有货币化收益结论。

关键文件：`q3_candidate_screening.csv`、`q3_selected_groups.csv`、`q3_assignments.csv`、`q3_solution_summary.csv`。
