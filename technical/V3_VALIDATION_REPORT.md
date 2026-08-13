# V3 验证报告

> 状态：`V3_RESULT_READY_WITH_SIMULATION_LIMITS`。本文档只描述本次 V3 合成仿真和固定编组压力追踪；不构成真实外部验证。

## 结果摘要

- `[RESULT]` 退役风险集：92 芯；事件 27；右删失 65。
- `[RESULT]` 条件 RUL 事件 RMSE：39.7665 cycles；嵌套留组校准区间经验覆盖：0.8889。
- `[RESULT]` POINT 入选 89 芯；INTERVAL_RISK 入选 41 芯。
- `[RESULT]` POINT 选中电芯的最小 RUL 下界为 73.8340 cycles、最大实际区间宽度为 228366.8650；INTERVAL_RISK 对应为 76.9064 和 2969.2436。两模式候选组归一化范围不同，目标值不得直接横向比较。
- `[RESULT]` 稳定性扫描行数：45；Jaccard=0.5714--1.0000；入选率=0.1489--0.3511；相对同 seed 基准目标差范围=-0.6628--0.4326；最小 SOH 裕度=0.0464、最小 RUL 下界裕度=0.0534 cycles、最小内阻增长裕度=0.0019、最小区间宽度裕度=39.0109 cycles；不可行 OAT 点 44/45；消融配置：48。
- `[RESULT]` Q2 消融最低 RMSE 配置为 ridge + all + 100-cycle，RMSE=0.004206；同为 100-cycle Ridge 时，全部特征较容量-only RMSE 下降 12.52%。这是仿真内消融，不构成真实因果贡献。
- `[RESULT]` Q4 固定组级记录 40 行；16 行 `STABLE_UNDER_SCENARIO`，5 行 `REINSPECT`，19 行 `REJECT_FORCED_ASSIGNMENT`；终点突破/事件触发强制拒绝。

## 验收闸门

- [x] v3_factorial_shape: 108 cells regenerated
- [x] retirement_risk_accounting: 92 risk cells = 27 events + 65 right-censored; 16 pre-750 exclusions
- [x] retirement_landmark_only: all features use cycle=750
- [x] retirement_group_split: OOF cell IDs unique; train/test overlap empty
- [x] decision_comparison_complete: common risk set; point uses median RUL, interval-risk uses RUL lower bound
- [x] stability_oat_complete: exact 5-seed x 9-point OAT set, bounded Jaccard, one changed parameter
- [x] ablation_complete: 3 windows x 4 feature groups x 4 models
- [x] fixed_group_signature: same (group_number, cell_id) membership across pressure scenarios
- [x] cycle_750_continuity: pressure trajectories match baseline at cycle 750
- [x] fixed_group_shape: 5 scenarios x 8 groups x 4 cells
- [x] fixed_group_summary_complete: group summaries contain SOH, resistance, and censor-aware RUL change fields
- [x] stress_trigger_endpoint_guard: endpoint breach or post-750 event always rejects forced assignment

## 边界

- `[CONFIRMED]` Q3 特征只读取 cycle<=750；750 前已达终点电芯排除。
- `[CONFIRMED]` Q4 固定 Q3 编组，不重新筛选、不重新优化；cycle 750 状态连续。
- `[ASSUMED][UPDATEABLE]` SOH 终点、筛选阈值、权重和触发规则来自配置。
- `[UNCERTAIN]` 真实电芯、车辆和安全事件外部有效性。
- `[OOD/ABSTAIN]` 低温、过充、过放、大于 2C 不输出数值。
- `V2 evidence_status=HOLD_RPT_SENSITIVITY; paper_eligible=false`，V2 不进入 V3 论文数字。

## 复跑命令

```bash
PYTHONPATH=code python -m battery_study.v3_cli --config configs/study_pipeline_v3.json --out study_output_v3
```
