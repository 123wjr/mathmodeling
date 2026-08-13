# 最终技术验证报告

> 判定：`PASS_WITH_SIMULATION_LIMITS`
> 技术主线：可进入论文；外部真实数据层 V2 继续 HOLD。

## 1. 要求—证据矩阵

| 要求 | 权威证据 | 判定 |
|---|---|---|
| 观测层区分潜在状态与测量 | `apply_observation_pressure`；`observation_sensitivity_summary.json` | PASS |
| none/light/heavy 三档全报告 | `observation_model_metrics.csv`、`observation_decision_sensitivity.csv` | PASS |
| 观测关闭复现原 V3 | none 档 `changed_measurement_rows=0`；原 Q2/Q3 数字一致 | PASS |
| 不选择性报告排序翻转 | 汇总登记 `ranking_flip_regimes=[]`，12 条模型指标完整 | PASS |
| 参数有单位、等级、理由、敏感性、更新条件 | `evidence/parameter_ledger.txt` | PASS |
| 未拟合参数不冒充 OBSERVED/CALCE 标定 | 台账使用 `REFERENCE_SCALE_NOT_FITTED` / `ASSUMED_UPDATEABLE` | PASS |
| 最大可行组数考虑互斥约束 | `maximum_disjoint_group_count` set-packing MILP | PASS |
| 产能不足时显式弃权 | 定向测试：目标 8、最大 3、缺口 5、不放宽门槛 | PASS |
| Q4 固定同一组追踪 | `fixed_group_signature`、`cycle_750_continuity` | PASS |
| V2 保持 HOLD | `technical/v2_evidence_status.json` + manifest 验证 | PASS |
| 最终文档标记确定/不确定 | `TECHNICAL_SOLUTION_FINAL.md` 四部分及标签 | PASS |

## 2. 最终结果核对

### 2.1 观测层

| 档位 | Ridge RMSE | 模型排序翻转 | 入选芯 | 最大可行组 | Jaccard | 状态 |
|---|---:|---|---:|---:|---:|---|
| none | 0.004206 | 否 | 41 | 10 | 1.000 | ACCEPT |
| light | 0.004224 | 否 | 39 | 9 | 0.829 | ACCEPT |
| heavy | 0.004344 | 否 | 40 | 10 | 0.778 | ACCEPT |

三档均保持 Ridge 第一、persistence 第四。成员集合变化大于预测排名变化；应报告二者，不可只报告 RMSE。

### 2.2 退役决策

- POINT：89 芯，最大可行 22 组，选择 8 组，`ACCEPT_FIXED_GROUPS`。
- INTERVAL_RISK：41 芯，最大可行 10 组，选择 8 组，`ACCEPT_FIXED_GROUPS`。
- 45 行 OAT 中 44 行显式弃权，最大组数缺口为 5，门槛放宽次数为 0；必须写成参数/产能敏感，不能写普遍稳定。
- 定向不可行情形：最大 3 组、缺口 5，返回 `ABSTAIN_INSUFFICIENT_FEASIBILITY`。
- `[RESULT][UPDATEABLE]` 30 个独立 seed 的基线 `INTERVAL_RISK`：`G_max=1--17`，中位数 5.5；至少达到 4/5/6/7/8 组的经验比例为 86.7%/70.0%/50.0%/40.0%/30.0%，9/30 接受 8 组，21/30 显式弃权。该经验分布只属于合成生成器，不是真实电芯批次概率。

### 2.3 压力追踪

- 固定 8 组、32 芯、5 场景；成员不变。
- 40 条组级记录：16 稳定、5 复检、19 拒绝强制编组。
- 右删失时不输出不可识别的精确 RUL CV。
- `[RESULT][UPDATEABLE]` P1 在相同 5 场景下让 POINT 与 INTERVAL_RISK 各自固定 Q3 选出的 8 组：POINT=20 稳定、10 复检、10 拒绝；INTERVAL_RISK=16 稳定、5 复检、19 拒绝。区间风险更保守，不能写成无条件更优。

### 2.4 V4 留一压力场景盲测

- `[CONFIRMED]` 30 seeds x 5 留出场景 x 2 策略，共 300 条策略折；bootstrap 独立单位是 seed，不把折或编组当独立样本。
- `[RESULT][UPDATEABLE]` 参考/严格鲁棒策略每折平均选择 5.667/1.160 组；配对差 -4.507，90% 区间 `[-5.020,-3.980]`。
- `[RESULT][UPDATEABLE]` 最坏安全裕量差 +0.332，90% 区间 `[0.181,0.496]`；稳定组目标比例差 -0.078，区间 `[-0.106,-0.050]`。
- `[RESULT][UPDATEABLE]` 已选组拒绝率差 +0.028，90% 区间 `[-0.080,0.134]`；没有证据证明严格鲁棒策略降低拒绝率。
- 判定：`PASS_NEGATIVE_RESULT / RISK_CAPACITY_TRADEOFF`。只能写“识别严格鲁棒策略的产能代价”，不能写“鲁棒优化显著提升安全性”。

## 3. 自动验证

- V3/V4 gates：19/19 PASS。
- manifest：PASS。
- V2 canonical 状态：`PASS / HOLD_RPT_SENSITIVITY / false`。
- 完整测试数与最终 Git 状态以本次提交前命令输出和 `run_manifest.json` 为准。

## 4. 仍不能证明

- `[UNCERTAIN]` 真实电芯预测精度、真实 RPT 参数、真实安全概率。
- `[UNCERTAIN]` 温度/DOD/倍率真实主效应权重。
- `[UNCERTAIN]` 系统串并联、热耦合、功率与经济收益。
- `[OOD/ABSTAIN]` 低温、过充、过放、>2C。
- V2 不得称外部验证；其方向翻转作为局限性证据保留。
