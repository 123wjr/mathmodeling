# 论文手最终变更清单

> 当前骨架：`论文初稿.md`。只按本表增量更新；不要重写 Q1，不要复制 V2 候选指标。

## 1. 必改位置

| `论文初稿.md` 位置 | 删除/降级 | 写入最终口径 |
|---|---|---|
| 摘要 Q3 | cycle=300 换算、108 芯直接筛选、V1 85/108 与 3167 组 | cycle=750 风险集 92 芯；POINT 89、区间风险 41；最大可行 22/10；均选择 8 组 |
| 摘要 Q4 | 每个场景重新生成/筛选/优化；组合应力筛选率 0 | 固定同一 8 组追踪；16 稳定、5 复检、19 拒绝 |
| 3 模型假设 | 只有高斯测量噪声 | 增加潜在状态/观测层分离及 none/light/heavy 参数；标 `[ASSUMED][UPDATEABLE]` |
| 5.2 | 仅 cycle=300 RUL | 保留原 Q2；新增 cycle=750 条件 RUL：92 芯、27 事件、65 删失、RMSE 39.7665、覆盖 0.8889 |
| 5.3 | 固定 8 组必达、三权重普遍可行 | 写最大可信产能 `G_max` 与弃权；OAT 44/45 达不到 8 组 |
| 5.4 | 场景重优化与仅支持域 OOD 弃权 | 写固定组纵向追踪 + 组级复检/拒绝 + 目标产能不足弃权 |
| 局限性 | 仅写缺真实数据 | 增加 V2 RPT 口径方向翻转；观测三档不是实测标定；决策成员 Jaccard 0.829/0.778 |
| 结论 | V1 Q3/Q4 数字 | 使用本表第 2 节事实；保留“合成仿真”限定 |

## 2. 可直接进入正文的最终事实

1. `[RESULT]` cycle=750 前排除 16 芯，风险集 92 芯：27 事件、65 右删失；条件 RUL 事件 RMSE=39.7665 cycles，90% 经验覆盖=0.8889。
2. `[RESULT]` POINT 入选 89 芯、最大可行 22 组；INTERVAL_RISK 入选 41 芯、最大可行 10 组；目标均为 8 组，状态均为 `ACCEPT_FIXED_GROUPS`。45 行 OAT 中 44 行显式弃权，最大组数缺口为 5，门槛放宽次数为 0。
3. `[RESULT]` 观测压力 none/light/heavy 下 Ridge RMSE 分别为 0.004206/0.004224/0.004344，模型排序未翻转；入选分别为 41/39/40，最大可行组数 10/9/10。
4. `[RESULT]` 轻度/重度观测压力相对 none 的选中成员 Jaccard 为 0.829/0.778；说明排名稳定不等于决策成员稳定。
5. `[RESULT]` 固定 8 组跨 5 场景的 40 条组级记录中，16 稳定、5 复检、19 拒绝强制编组。

## 3. 必须原样保留的限定

- 所有上述数字是自主构建 NMC 合成仿真结果，不是 CALCE 校准或真实车辆精度。
- 观测三档是冻结的仿真压力假设，不是真实 RPT 幅度估计。
- 90% 覆盖是本次留组仿真的经验覆盖，不是有限样本或安全保证。
- 最大可行组数只对应当前候选组生成规则、门槛和四芯模块演示。
- V2 仍 `HOLD_RPT_SENSITIVITY / paper_eligible=false`，数字不得进入主结果。

## 4. 禁止继续使用

- V1 `85/108` 作为当前 Q3 入选数。
- V1 `3167` 候选组和 `MILP 1.2048 vs greedy 1.0828` 作为当前 Q3 主结果。
- Q4 “每场景重新筛选/重新优化”作为当前方法。
- “组合应力筛选率 0”作为当前固定组压力结论。
- “参数扫描全部可行”“真实数据外部验证通过”“CALCE 实测标定”。

## 5. 回指

- 方法总层：`technical/TECHNICAL_SOLUTION_FINAL.md`
- 参数：`evidence/parameter_ledger.txt`
- 观测结果：`study_output_v3/observation_model_metrics.csv`、`observation_decision_sensitivity.csv`
- Q3：`study_output_v3/q3_decision_comparison.csv`、`q3_stability_summary.json`
- Q4：`study_output_v3/q4_fixed_group_summary.csv`
- 验证：`technical/FINAL_VALIDATION_REPORT.md`、`study_output_v3/validation_gates.json`
