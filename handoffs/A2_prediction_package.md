# A2 Q1/Q2 阶段辨识与预测证据包

**状态**：`PASS_WITH_LIMITATIONS`
**事实源**：`configs/study_pipeline.json` + `study_output/run_manifest.json`

## 已交付

- Q1：27 工况全因子主效应、阶段计数、膝点检测与右删失；协议效应明确 `NOT_IDENTIFIABLE`。
- Q2：SOH 四模型、5 折 `GroupKFold(cell_id)`、27 工况留一压力测试、cell-bootstrap 90% CI。
- RUL：43 事件 + 65 右删失；主模型 log-normal AFT，名义 90% 事件覆盖率=0.9070。

## 写作边界

`[RESULT]` 只能称仿真留组性能。结构匹配模型是 simulator ceiling；不得声称外部验证。80% SOH 是 `[ASSUMED][UPDATEABLE]` 终点。

## 关键文件

`q1_summary.json`、`q1_factor_effects.csv`、`q1_knee_detection.csv`、`q2_soh_metrics.csv`、`q2_rul_metrics.csv`、`q2_leave_condition_out.csv`。
