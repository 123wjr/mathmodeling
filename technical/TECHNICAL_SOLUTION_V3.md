# A 题技术方案 V3：退役决策闭环

> 状态：`INTERIM_PAPER_HANDOFF / VERIFIED_WITH_SIMULATION_LIMITS`
> 用途：`论文初稿.md` 与实验产物之间的技术层，不是论文正文。本版先供论文手搭建大纲、方法和表图占位；参数依据与观测偏差补强后再冻结结果。
> 主线：V3 独立增量；不覆盖 V1，不解除 V2 的 `HOLD_RPT_SENSITIVITY`。

## 0. 与 `论文初稿.md` 对齐接口

| `论文初稿.md` 位置 | V3 填充内容 | 动作 |
|---|---|---|
| 摘要 | 退役时点条件 RUL、区间风险编组、固定编组追踪 | 总负责人放行后替换 V1 的 Q3/Q4 方法摘要；保留“合成仿真”限定 |
| 三、模型假设 | 本文 H1--H5 | 新增退役风险集、增量压力和可更新门槛假设 |
| 5.2.2 | 3.1、3.5 | 补充 cycle 750 条件 AFT 与 Q2 消融设计 |
| 5.2.3 | 6 | 补充 92 芯风险集、事件 RMSE、经验覆盖和 48 项消融；不得替换 cycle 300 的 Q2 原任务结果 |
| 5.3.1 | 3.1--3.2 | 将“108 芯均进入退役候选”改为先排除 750 前终点电芯，再建立风险集 |
| 5.3.2 | 3.2 | 增加 POINT 与 INTERVAL_RISK 同约束对照 |
| 5.3.3 | 6 | 增加双决策结果与 45 行 OAT 稳定性；不同候选集的归一化目标值不直接比较优劣 |
| 5.4.1--5.4.2 | 3.3--3.4、6 | 用固定 Q3 编组的 750--1000 压力追踪替换“每场景重新生成、筛选、优化”的主结果叙事 |
| 5.4.4 | 3.3、4 | 写删失感知 RUL 变化、连续性闸门和三态触发；无事件时不得写精确 RUL CV |
| 6.1--6.3 | 1、5--6 | 创新写同领域闭环融合；跨领域迁移只作推广，不写实验结果 |
| 七、结论 | 6 | 只复制 `[RESULT]` 且保留适用范围；V2 数字继续禁止进入 |

V3 不删除 Q1 和 cycle=300 的 Q2 结果。它替换的是 V1 的退役决策口径与 Q4 场景重优化口径。

## 1. 研究问题与创新边界

V3 回答一个闭环问题：在退役时点重新估计仍存活电芯的条件剩余寿命，如何把预测不确定性传入编组，并验证同一编组在后续压力工况中的稳定性？

创新按证据强度分层：

1. `[CONFIRMED]` 同领域融合：半机理退化、右删失生存分析、区间风险筛选、set-packing MILP、固定编组纵向压力追踪。
2. `[UPDATEABLE]` 参数鲁棒性：门槛、目标权重和随机种子扫描；不称在线自适应学习。
3. `[CONFIRMED]` 多模型比较：保留 Q2 基线模型，增加特征组和历史窗口消融。
4. `[UPDATEABLE]` 求解模型对照：点预测决策与区间风险决策使用相同原始电芯池和编组约束；不新增启发式优化器。
5. `[PAPER_GAP]` 跨领域迁移：当前无数据和机制证据，只能列为推广方向，不能进入结果。

## 2. 假设

| 编号 | 假设 | 状态 | 更新条件 |
|---|---|---|---|
| H1 | cycle 750 前观测可用于估计该时点的条件剩余寿命 | `[ASSUMED][UPDATEABLE]` | 真实退役快照协议改变 |
| H2 | 750 前已达到 80% SOH 终点的电芯不属于风险集 | `[CONFIRMED]` | 终点定义改变 |
| H3 | 风险集内剩余寿命服从带协变量的 log-normal AFT | `[ASSUMED][UPDATEABLE]` | 模型比较否定该分布 |
| H4 | Q4 保持电芯个体参数和 750 前历史，只改变 750 后工况 | `[CONFIRMED]` | 压力实验设计改变 |
| H5 | 80% SOH、筛选门槛、目标权重和触发阈值均为场景参数 | `[ASSUMED][UPDATEABLE]` | 获得正式标准或实测标定 |

所有 V3 数值仍来自合成仿真，不代表 CALCE 实测校准、真实车辆精度、安全概率或货币收益。

## 3. 模型

### 3.1 cycle 750 条件 RUL

设退役时点为 `t0=750`，寿命终点为首次 `SOH <= 0.8` 的循环 `T`。

- 若 `T <= t0`，电芯排除，不进入风险集。
- 若 `t0 < T <= 1000`，条件剩余寿命 `Y=T-t0`，事件指示 `delta=1`。
- 若观测期内未达到终点，`Y=1000-t0=250`，`delta=0`，作为右删失。

仅用 `cycle <= t0` 的容量、内阻、近期斜率、EFC 和工况特征。模型为：

```text
log(Y_i) = beta_0 + beta^T x_i(t0) + sigma * epsilon_i
```

外层按 `cell_id` 留组。训练折拟合 AFT 并校准区间，测试折只做预测。输出中必须登记每折训练/测试电芯零重叠。

### 3.2 点预测与区间风险决策

两种决策共享同一原始风险集、SOH/内阻门槛、候选组生成和互斥编组约束：

- `POINT`：以条件 RUL 中位数通过 RUL 门槛，不使用区间宽度拒绝。
- `INTERVAL_RISK`：以条件 RUL 90% 下界通过门槛，并限制区间宽度；当前配置上限为 3000 cycles。该上限是可更新筛选参数，不是把 AFT 区间截断到 3000 cycles。

两者分别生成可行候选组并求解相同 set-packing MILP。结果用于比较可行电芯数、组数、最弱单体 RUL、风险指标和目标值；因归一化集合可能不同，目标值只作同口径描述，不作跨集合绝对优劣证明。

### 3.3 固定编组压力追踪

固定 `INTERVAL_RISK + balanced` 选出的同一批电芯。每颗电芯保留原始 Q3 历史工况与个体参数。设退役时 EFC 为 `e0`，原历史工况因子为 `u_hist`，750 后场景因子为 `u_s`：

```text
D(e) = u_hist * L(e0) + u_s * [L(e) - L(e0)]
SOH(e) = 1 - alpha_i * D(e)
R(e) = R0_i * [1 + beta_i * D(e)]
```

其中 750 后 EFC 按新场景 DOD 累积。该式在 `e=e0` 时严格回到原轨迹，压力工况不会倒灌到历史阶段。

场景只在冻结支持域内：基准续航、高温、高倍率、高 DOD、组合压力。各场景不重新筛选、不更换电芯、不重新优化。

### 3.4 决策稳定性

采用 OAT 扫描，避免 405 组全因子参数组合造成无必要计算与多重比较：

- `min_soh`: 0.74 / 0.76 / 0.78；
- `min_rul_lower_cycles`: 20 / 40 / 60；
- `max_resistance_growth`: 0.40 / 0.45 / 0.50；
- 权重：performance / balanced / conservative；
- 数据 seed：42 / 123 / 2026 / 4096 / 8110。

每个 seed 的所有参数方案与该 seed 的 balanced 基准比较选中电芯集合 Jaccard；同时报告入选率、组数、不可行状态、目标范围和最差约束裕度。

### 3.5 Q2 消融

固定 50-cycle 预测步长和按电芯 GroupKFold。扫描历史窗口 25/50/100 cycles，以及四个可观测特征组：容量、容量+内阻、容量+工况、全部特征。Ridge 与 Random Forest 参加每个组合；persistence 与 local linear 作为各窗口无训练基线。

消融目的不是只挑最低 RMSE，而是检查性能是否来自可解释状态/工况信息，且没有使用 `soh_true`、未来轨迹、寿命标签或生成器参数。

## 4. 实验与验收

独立输出目录为 `study_output_v3/`。核心产物：

- `q2_ablation_metrics.csv`、`q2_ablation_summary.json`
- `q3_retirement_landmark_predictions.csv`、`q3_retirement_screening.csv`、`q3_retirement_summary.json`
- `q3_decision_comparison.csv`
- `q3_stability_sweep.csv`、`q3_stability_summary.json`
- `q4_fixed_group_cell_tracking.csv`、`q4_fixed_group_summary.csv`、`q4_fixed_group_summary.json`
- `validation_gates.json`、`run_manifest.json`

硬闸门：

1. 风险集、事件、右删失、750 前排除数量闭合。
2. Q3 特征时点全部等于 750，外层训练/测试 `cell_id` 零重叠。
3. Q4 所有场景的 `cell_id` 与组号完全相同。
4. Q4 cycle 750 状态与原轨迹在数值容差内连续。
5. 压力场景不触发支持域外数值预测。
6. 消融、稳定性、决策对照均有完整 CSV/JSON。
7. manifest 保存配置、源码、产物 SHA-256。
8. V2 仍为 HOLD，V1 产物未被覆盖。

## 5. 结论接口

在实验通过前，本节只允许写：

- `[CONFIRMED]` V3 的时间口径、数据分组、模型方程、约束和验收规则。
- `[UPDATEABLE]` 门槛、权重、触发值和种子扫描范围。
- `[RESULT]` 已通过 V3 自动闸门的风险集数量、预测指标、筛选率、编组数、压力追踪结果；精确值见第 6 节。
- `[UNCERTAIN]` 对真实电芯、车辆和安全事件的外部有效性。
- `[OOD/ABSTAIN]` 低温、过充、过放和大于 2C 的数值推断。

任一硬闸门失败时，V3 结果不得进入论文，论文继续使用 V1 已验收主线。

## 6. V3 最近复跑结果（2026-08-13）

- `[RESULT]` 退役风险集 92 芯：27 个事件、65 个右删失；750 前排除 16 芯。
- `[RESULT]` cycle=750 条件 RUL 在事件样本上的 RMSE 为 39.7665 cycles；嵌套留组残差校准区间的经验覆盖率为 0.8889。该覆盖率是本次仿真样本的描述性结果，不是有限样本保证。
- `[RESULT]` POINT 决策入选 89 芯；INTERVAL_RISK 决策入选 41 芯；两者均求得 8 个四芯组。未截断的 AFT 区间使 POINT 选中组最大实际区间宽度达到 228366.8650 cycles；INTERVAL_RISK 选中组为 2969.2436 cycles。
- `[RESULT]` 稳定性扫描 45 行，入选率为 0.1489--0.3511，Jaccard 为 0.5714--1.0000，同 seed 基准目标差及四类实际门槛裕度均在 `q3_stability_summary.json` 登记；44/45 个 OAT 参数点无法达到 8 组目标，不能写“参数扫描全部可行”。
- `[RESULT]` Q2 消融包含 48 个配置（3 窗口 x 4 特征组 x 4 模型），全部按 `cell_id` 留组。
- `[RESULT]` Q4 固定 INTERVAL_RISK balanced 编组，5 个压力场景共 40 个组级记录；16 个 `STABLE_UNDER_SCENARIO`、5 个 `REINSPECT`、19 个 `REJECT_FORCED_ASSIGNMENT`。有右删失的组不计算 RUL CV，而标记 `RIGHT_CENSORED_NOT_IDENTIFIABLE`；强制拒绝由终点突破或 post-750 事件触发。

上述数字只能写成“本合成仿真/固定编组压力追踪结果”，不能写成真实数据外部验证。精确回指：`study_output_v3/q3_retirement_summary.json`、`q3_decision_comparison.csv`、`q3_stability_sweep.csv`、`q2_ablation_metrics.csv`、`q4_fixed_group_summary.csv`。
