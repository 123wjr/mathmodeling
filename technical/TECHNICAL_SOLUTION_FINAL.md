# A 题最终技术方案：观测—预测—决策闭环

> 状态：`FINAL_TECHNICAL_HANDOFF / VERIFIED_SYNTHETIC_EVIDENCE`
> 编辑骨架：`论文初稿.md`。本文是论文与代码结果之间的最终技术过渡层，不作修辞包装。
> 证据边界：主结果均来自自主构建的 NMC 合成仿真；不是 CALCE 拟合、真实车辆验证或安全认证。V2 仍为 `HOLD_RPT_SENSITIVITY / paper_eligible=false`。

## 0. 标签、入口与运行

- `[CONFIRMED]`：代码接口、数学定义、支持域、留组协议或自动闸门已确认。
- `[RESULT]`：本次固定配置复跑结果；仅适用于本合成仿真。
- `[ASSUMED][UPDATEABLE]`：退化系数、观测扰动、阈值、权重和目标产能。
- `[UNCERTAIN]`：对真实电芯、批次、车辆和安全事件的外部有效性。
- `[OOD/ABSTAIN]`：不支持数值外推，或硬门槛后无法达到目标产能。

最小复跑：

```bash
PYTHONPATH=code python -m battery_study.v3_cli \
  --config configs/study_pipeline_v3.json --out study_output_v3
PYTHONPATH=.:code python -m pytest code/tests -q
```

核心配置：`configs/g1_smoke.json`、`configs/study_pipeline_v3.json`。完整参数依据：`evidence/parameter_ledger.txt`。核心结果：`study_output_v3/`。

# 一、假设

## 1.1 研究对象与支持域

| 编号 | 假设/约束 | 状态 | 更新条件 |
|---|---|---|---|
| H1 | 研究对象为 NMC/graphite 单体电芯；2.0 Ah 只作参考尺度 | `[CONFIRMED][UNCERTAIN]` | 更换体系或取得匹配原始数据 |
| H2 | 数值支持域为 25--50 degC、0.5--2C、DOD 50--100%、CC-CV | `[CONFIRMED]` | 新数据覆盖新域并重新验证 |
| H3 | 低温、过充、过放、>2C 不输出寿命数值 | `[OOD/ABSTAIN]` | 建立对应机理和匹配数据 |
| H4 | 单一 CC-CV 水平不能辨识协议效应 | `[CONFIRMED]` | 增加多协议平衡试验 |

## 1.2 退化与观测假设

| 编号 | 假设 | 状态 | 后果 |
|---|---|---|---|
| H5 | 潜在容量衰减与内阻增长共享连续分段平方根累计退化量 | `[ASSUMED][UPDATEABLE]` | 保证方向和膝点连续，但不是唯一真实退化律 |
| H6 | 温度、倍率和 DOD 修正可乘性分离 | `[ASSUMED][UPDATEABLE]` | 不能表示未建模的强交互或失效模式切换 |
| H7 | 电芯初值与退化率具有截断正态随机效应 | `[ASSUMED][UPDATEABLE]` | 避免非物理尾部；真实分布未标定 |
| H8 | 基础观测误差为高斯噪声；RPT/恢复脉冲和稀疏异常作为独立观测压力层 | `[ASSUMED][UPDATEABLE]` | 可检验预处理敏感性，但不等于真实 RPT 协议校准 |
| H9 | 观测压力只修改 `capacity_obs/resistance_obs`，不修改潜在 SOH、真容量和真内阻 | `[CONFIRMED]` | 保持“物理退化变化”和“测量协议变化”可区分 |

## 1.3 预测与决策假设

| 编号 | 假设/规则 | 状态 | 更新条件 |
|---|---|---|---|
| H10 | SOH=0.80 为本研究寿命终点 | `[ASSUMED][UPDATEABLE]` | 应用规范给出其他终点 |
| H11 | cycle=750 前已到终点的电芯退出风险集 | `[CONFIRMED]` | 退役时点或终点改变 |
| H12 | 风险集条件 RUL 服从带协变量的 log-normal AFT | `[ASSUMED][UPDATEABLE]` | 独立模型比较否定分布 |
| H13 | 同一电芯的循环记录不得跨训练/测试折 | `[CONFIRMED]` | 不更新；属于泄漏硬门 |
| H14 | SOH、RUL 下界、内阻增长和区间宽度为硬门槛 | `[ASSUMED][UPDATEABLE]` | 标准或风险偏好改变 |
| H15 | 目标 8 组是产能目标，不是必须完成的安全要求 | `[CONFIRMED]` | 目标可改，但不得反向放宽硬门槛 |

# 二、模型

## 2.1 潜在退化状态

令等效满循环为 `e`，膝点为 `n_k`：

```text
L(e) = sqrt(min(e,n_k))
     + knee_gain * max(0, sqrt(e)-sqrt(n_k))

u_T = exp[k_T(T-25)]
u_C = 1 + k_C(C-0.5)
u_D = 1 + k_D(DOD/100-0.5)
u   = u_T * u_C * u_D

X_Q,i(e) = Q0_i * [1-alpha_i*u*L(e)]
X_R,i(e) = R0_i * [1+beta_i*u*L(e)]
SOH_i(e) = X_Q,i(e)/Q0_i
```

`[CONFIRMED]` 公式实现和膝点连续性已测试。`[ASSUMED][UPDATEABLE]` `alpha/beta/k_T/k_C/k_D/n_k/knee_gain` 的数值不是实测拟合。公开资料只支持参考对象、尺度和机理方向；冻结值、敏感性和更新条件逐项见参数台账。

## 2.2 观测层

基础观测：

```text
Y_Q,i(c) = X_Q,i(c) + epsilon_Q,i(c)
Y_R,i(c) = X_R,i(c) + epsilon_R,i(c)
```

其中 `epsilon_Q ~ N(0, sigma_Q*Q_nom)`，`epsilon_R ~ N(0, sigma_R*X_R)`。观测压力实验再加入：

```text
Y*_Q(c) = Y_Q(c) + a_Q * X_Q(c) * d(c;p) + z_Q(c)
Y*_R(c) = Y_R(c) - a_R * X_R(c) * d(c;p) + z_R(c)
```

`d(c;p)` 在每个周期 `p` 的 3 个脉冲点取 `1, 0.55, 0.25`，其他循环为 0；`z` 为概率 `p_out` 的稀疏异常，幅度以基础测量残差的 `m_out` 倍定义。

三档预注册参数：

| 档位 | RPT 周期 | 容量恢复 | 内阻恢复 | 异常比例 | 异常倍数 | 标签 |
|---|---:|---:|---:|---:|---:|---|
| none | 0 | 0 | 0 | 0 | 0 | `[CONFIRMED]` 基线回归 |
| light | 50 cycles | 0.4% | 0.8% | 0.2% | 3 | `[ASSUMED][UPDATEABLE]` |
| heavy | 25 cycles | 1.0% | 2.0% | 0.5% | 5 | `[ASSUMED][UPDATEABLE]` |

这些档位只回答“结论对可能的观测协议偏差有多敏感”，不回答“真实 RPT 幅度是多少”。

## 2.3 SOH 与退役时点条件 RUL

SOH 短期预测比较 Ridge、Random Forest、local linear 和 persistence；按 `cell_id` GroupKFold，预测窗口 50 cycles。所有特征只读取预测时点以前的容量、内阻、工况和时间信息；`soh_true/capacity_true/lifetime_cycle` 不进入特征。

退役时点 `t0=750`，终点 `T`：

```text
T <= t0       -> 排除，不进入风险集
t0 < T <=1000 -> Y=T-t0, delta=1
T > 1000      -> Y=250, delta=0（右删失）

log(Y_i) = beta_0 + beta^T x_i(t0) + sigma*epsilon_i
```

AFT 似然同时包含事件密度与右删失生存概率。90% 区间使用训练折事件残差膨胀，并在外层留组样本报告经验覆盖；覆盖不是有限样本保证。

## 2.4 风险筛选、最大可信产能与弃权

两种决策共享风险集和硬门槛：

- `POINT`：使用 RUL 中位数；
- `INTERVAL_RISK`：使用 90% RUL 下界，并限制区间宽度。

通过硬门槛后枚举四芯候选组。令 `z_g` 表示选择候选组 `g`：

```text
max sum_g score_g*z_g
s.t. sum_{g contains i} z_g <= 1, for every cell i
     sum_g z_g = G
     z_g in {0,1}
```

先用相同 set-packing MILP 求最大互斥组数 `G_max`，再令 `G=min(G_target,G_max)` 求组质量最优解。决策状态：

```text
G_max >= G_target -> ACCEPT_FIXED_GROUPS
0 < G_max < target -> ABSTAIN_INSUFFICIENT_FEASIBILITY
G_max = 0          -> ABSTAIN_INSUFFICIENT_FEASIBILITY
压力追踪触发终点  -> REJECT_FORCED_ASSIGNMENT
边缘一致性超限    -> DEFER_REINSPECT / REINSPECT
```

`[CONFIRMED]` 无论哪种状态均有 `thresholds_relaxed=false`。不足时输出最大可信组数、缺口和原因，不通过降低 SOH/RUL 门槛凑够 8 组。

## 2.5 固定编组压力追踪

Q4 固定基线 `INTERVAL_RISK + balanced` 选出的同一 8 组、32 芯，不重新筛选或换芯。cycle=750 前保留历史工况和个体参数，之后只替换温度、倍率和 DOD；在 750 处要求数值连续。输出 SOH 变化、内阻增长、删失感知 RUL 变化与三态触发。

# 三、实验

## 3.1 主实验与验证协议

- `[CONFIRMED]` 3 温度 x 3 倍率 x 3 DOD x 4 电芯，108 芯、108000 行、1000 cycles。
- `[CONFIRMED]` 所有预测按电芯留组；V3 退役风险集 92 芯，训练/测试电芯零重叠。
- `[CONFIRMED]` 观测档必须全部报告；不得只选择对模型有利的档位。
- `[CONFIRMED]` Q3 比较 POINT/INTERVAL_RISK；Q4 固定同一编组追踪。
- `[CONFIRMED]` 15 个自动闸门全部通过，manifest 校验通过。

## 3.2 观测压力结果

| 档位 | Ridge RMSE | persistence RMSE | Ridge 相对 persistence | 模型排序翻转 | 入选芯 | `G_max` | 选中组 | Jaccard vs none | 决策 |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| none | 0.004206 | 0.019355 | -78.27% | 否 | 41 | 10 | 8 | 1.000 | ACCEPT |
| light | 0.004224 | 0.020004 | -78.89% | 否 | 39 | 9 | 8 | 0.829 | ACCEPT |
| heavy | 0.004344 | 0.020703 | -79.02% | 否 | 40 | 10 | 8 | 0.778 | ACCEPT |

解释：

1. `[RESULT]` 三档排序均为 Ridge、Random Forest、local linear、persistence，未发生方向翻转。
2. `[RESULT]` 模型排序稳定不等于决策成员稳定；重度档选中成员 Jaccard 降至 0.778。
3. `[RESULT]` 轻度档最大可行组数由 10 降至 9，重度档仍为 10；均高于目标 8，因此本次未实际触发 Q3 弃权。该非单调变化说明观测扰动会改变门槛附近成员，不能把“重度”解释为所有决策指标必然单调恶化。
4. `[CONFIRMED]` 代码定向测试构造 `G_max=3 < G_target=8` 的情形，返回缺口 5、`ABSTAIN_INSUFFICIENT_FEASIBILITY` 且不放宽门槛。
5. `[UNCERTAIN]` 三档不是真实 RPT 标定，因此不能据此声称模型已通过真实观测协议验证。

## 3.3 条件 RUL 与决策结果

- `[RESULT]` 750 前排除 16 芯；风险集 92 芯，其中 27 事件、65 右删失。
- `[RESULT]` 事件样本条件 RUL RMSE=39.7665 cycles；90% 区间经验覆盖=0.8889。
- `[RESULT]` POINT 入选 89 芯，`G_max=22`；INTERVAL_RISK 入选 41 芯，`G_max=10`；两者均选择 8 组，状态 `ACCEPT_FIXED_GROUPS`。
- `[RESULT]` INTERVAL_RISK 选中组最弱 RUL 下界 76.9064 cycles，最大区间宽度 2969.2436 cycles。
- `[RESULT]` 45 行 OAT 中 44 行显式返回 `ABSTAIN_INSUFFICIENT_FEASIBILITY`，最大组数缺口为 5，门槛放宽次数为 0。该结果说明固定产能目标对参数敏感，不能写成“方案普遍可行”。

### 3.3.1 跨种子可信产能（P0）

- `[RESULT][UPDATEABLE]` 在预注册 30 个独立随机种子下，固定 `INTERVAL_RISK + balanced` 决策的 `G_max` 范围为 1--17 组，中位数 5.5 组。
- `[RESULT][UPDATEABLE]` 达到至少 4/5/6/7/8 组的经验比例分别为 86.7%/70.0%/50.0%/40.0%/30.0%；30 个种子中 9 个达到 8 组、21 个显式弃权，阈值放宽次数为 0。
- 该分布是当前合成生成器下的经验稳定性，不是真实电芯可靠性概率；因此主种子可形成 8 组不应写成跨批次普遍保证。

## 3.4 消融与固定组压力追踪

- `[RESULT]` Q2 消融 48 个配置：3 窗口 x 4 特征组 x 4 模型；100-cycle Ridge 全特征 RMSE 比容量-only 下降 12.52%。
- `[RESULT]` Q4 固定 8 组跨 5 场景，共 40 条组级记录：16 `STABLE_UNDER_SCENARIO`、5 `REINSPECT`、19 `REJECT_FORCED_ASSIGNMENT`。
- `[CONFIRMED]` 所有场景成员和组号一致；cycle=750 连续；右删失组不虚构精确 RUL CV。

### 3.4.1 点预测与区间风险配对追踪（P1）

- `[RESULT][UPDATEABLE]` 在完全相同的 5 个压力场景下，POINT 固定编组得到 20 个稳定、10 个复检、10 个拒绝强制编组；INTERVAL_RISK 得到 16 个稳定、5 个复检、19 个拒绝强制编组。
- 区间风险策略减少复检但增加拒绝，表现为更保守的弃权策略，不能宣称其无条件优于点预测。
- 两种策略均各自固定 cycle=750 选出的 8 组，不重新筛选、不重新优化；配对明细见 `q4_paired_decision_mode_summary.csv` 和 `q4_paired_decision_mode_cell_tracking.csv`。

## 3.5 外部证据状态

V2 读取 Zenodo NMC/Graphite 候选数据，但 NMC532 的 Ridge 相对 persistence 会随 RPT 处理口径发生方向翻转，且 period=50 双侧趋势使用未来观测。因此：

```text
run_status=PASS
evidence_status=HOLD_RPT_SENSITIVITY
paper_eligible=false
```

`[CONFIRMED]` V2 只能进入“外部效度与局限”，不能提供论文主结果数字或“真实校准成功”主张。

# 四、结论

## 4.1 已确定结论

1. `[CONFIRMED]` 已形成潜在退化、观测偏差、留组预测、区间风险筛选、最大可信产能、MILP 编组和固定组追踪的完整技术闭环。
2. `[RESULT]` 当前合成仿真中 Ridge 的 SOH 预测排序在三档观测压力下未翻转，但选中成员对观测层敏感；工程决策不能只看平均 RMSE。
3. `[RESULT]` 基线区间风险决策可形成最多 10 组并接受目标 8 组；轻度/重度观测压力下最多 9/10 组，均接受。
4. `[CONFIRMED]` 当最大可信组数不足时，系统显式弃权并报告缺口，不通过放宽风险门槛维持产能。
5. `[RESULT]` 固定编组后续压力追踪出现稳定、复检和拒绝三类结果，说明“一次筛选后永久可用”不成立。

## 4.2 不确定和可更新部分

- `[ASSUMED][UPDATEABLE]` 半机理系数、随机效应、观测脉冲、SOH/RUL/内阻门槛、区间宽度、目标组数和权重。
- `[UNCERTAIN]` 对真实 NMC 电芯、不同批次、系统热耦合和真实安全事件的外部有效性。
- `[UNCERTAIN]` 当前模型不含电压拓扑、热失控概率、均衡器、功率需求和经济收益，不能称系统级安全/经济最优。
- `[OOD/ABSTAIN]` 低温、过充、过放、>2C 和新化学体系均不做数值外推。
- 更新顺序固定为：核验协议与来源 -> 训练数据校准观测/退化参数 -> 留组外部验证 -> 重设决策门槛 -> 全量复跑 manifest。

## 4.3 论文可用的一句技术主张

> 本文在自主构建的 NMC 合成仿真中，将潜在退化与观测协议扰动分层建模，以电芯留组的删失感知条件 RUL 区间驱动风险筛选和 set-packing MILP，并在固定编组压力追踪中设置最大可信产能与显式弃权；结果表明预测排序在预注册观测压力下保持稳定，但编组成员发生明显变化，因此模型精度与决策稳定性必须同时验证。

该句必须保留“自主构建的合成仿真”和“不构成真实外部验证”的上下文。
