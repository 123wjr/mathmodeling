# 论文写作数字事实表

写作入口：[PAPER_AGENT_START_HERE.md](../PAPER_AGENT_START_HERE.md)。本页只提供已验收的论文数字，不替代入口中的阅读顺序、标签规则和交接协议。

> 只复制本页已标记数字；不得把“仿真结果”改写为“实测结果”。详细定义见 `TECHNICAL_REPORT_MINIMAL.md`。

| 编号 | 可写事实 | 标签 | 回指 |
|---|---|---|---|
| F1 | 全因子 27 工况、108 电芯、108000 行 | `[CONFIRMED]` | `study_output/factorial_design.csv` |
| F2 | 膝点可检测 72 电芯，右删失 36；内部恢复误差中位数 13.40 EFC | `[RESULT]` 仿真自检 | `q1_knee_detection.csv` |
| F3 | 50-cycle SOH 最低 RMSE 模型 `ridge`，RMSE=0.004206 | `[RESULT]` 仿真留组 | `q2_soh_metrics.csv` |
| F4 | RUL 事件 43、右删失 65；AFT 事件 RMSE=38.39 cycles，90% 区间覆盖=0.9070，删失矛盾率=0.0000 | `[RESULT]` 仿真留组 | `q2_rul_metrics.csv` |
| F5 | Q3 过门槛 85/108，MILP 8 组、重复分配 0 | `[RESULT][UPDATEABLE]` | `q3_solution_summary.csv` |
| F6 | Q4 使用 5 个独立 seed；OOD 四类均无数值 | `[CONFIRMED]` | `q4_monte_carlo_summary.csv`、`q4_ood_abstention.csv` |

禁止写入正文：真实车辆精度、普适安全阈值、人民币收益、低温/过充/过放寿命、CALCE 实测校准成功。
