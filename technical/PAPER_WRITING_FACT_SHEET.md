# 论文写作数字事实表

写作入口：[PAPER_AGENT_START_HERE.md](../PAPER_AGENT_START_HERE.md)；当前编辑骨架：[论文初稿.md](../论文初稿.md)；技术过渡层：[PAPER_TECHNICAL_BRIDGE.md](PAPER_TECHNICAL_BRIDGE.md)。本页为临时 V3 交付：数字可用于带标签工作稿，参数依据与观测偏差补强后再冻结。

> 只复制本页已标记数字；不得把“仿真结果”改写为“实测结果”。Q3/Q4 以 V3 为当前口径；V1 的 85/108、3167 组及场景重优化结果仅作历史对照。详细定义见 `TECHNICAL_SOLUTION_V3.md`。

| 编号 | 可写事实 | 标签 | 回指 |
|---|---|---|---|
| F1 | 全因子 27 工况、108 电芯、108000 行 | `[CONFIRMED]` | `study_output/factorial_design.csv` |
| F2 | 膝点可检测 72 电芯，右删失 36；内部恢复误差中位数 13.40 EFC | `[RESULT]` 仿真自检 | `q1_knee_detection.csv` |
| F3 | 50-cycle SOH 最低 RMSE 模型 `ridge`，RMSE=0.004206 | `[RESULT]` 仿真留组 | `q2_soh_metrics.csv` |
| F4 | RUL 事件 43、右删失 65；AFT 事件 RMSE=38.39 cycles，90% 区间覆盖=0.9070，删失矛盾率=0.0000 | `[RESULT]` 仿真留组 | `q2_rul_metrics.csv` |
| F5 | cycle=750 风险集 92 芯：27 事件、65 右删失；750 前排除 16 芯 | `[RESULT]` 仿真留组 | `study_output_v3/q3_retirement_summary.json` |
| F6 | cycle=750 条件 RUL 事件 RMSE=39.7665 cycles；嵌套留组区间经验覆盖=0.8889 | `[RESULT]` 仿真留组；覆盖不是 90% 保证 | `study_output_v3/q3_retirement_summary.json` |
| F7 | POINT 入选 89 芯、INTERVAL_RISK 入选 41 芯；两者均求得 8 个四芯组（区间宽度门槛=3000 cycles，具体值可更新） | `[RESULT][UPDATEABLE]` | `study_output_v3/q3_decision_comparison.csv`、`configs/study_pipeline_v3.json` |
| F8 | 5 seed、45 行 OAT 决策稳定性扫描；入选率=0.1489--0.3511，选中电芯 Jaccard=0.5714--1.0000；44/45 无法达到 8 组目标 | `[RESULT][UPDATEABLE]` | `study_output_v3/q3_stability_sweep.csv`、`q3_stability_summary.json` |
| F9 | Q2 消融共 48 个预注册配置：3 个历史窗口 x 4 个特征组 x 4 个模型 | `[CONFIRMED][RESULT]` 仿真留组 | `study_output_v3/q2_ablation_metrics.csv` |
| F10 | 固定同一 8 组跨 5 个压力场景追踪，cycle 750 连续；40 个组级记录中 16 个稳定、5 个复检、19 个强制拒绝 | `[RESULT][CONFIRMED]` 仿真固定编组追踪 | `study_output_v3/q4_fixed_group_summary.csv` |
| F11 | 低温、过充、过放、>2C 仍为 `[OOD/ABSTAIN]`；V2 仍为 `HOLD_RPT_SENSITIVITY`、`paper_eligible=false` | `[CONFIRMED][OOD/ABSTAIN]` | `configs/study_pipeline_v3.json`、`study_output_v3/run_manifest.json` |

禁止写入正文：V1 Q3/Q4 历史数字作为当前主结果、真实车辆精度、普适安全阈值、人民币收益、低温/过充/过放寿命、CALCE 实测校准成功、V2 候选指标。
