# A 题技术方案 V2（论文填充用）

> 文档性质：技术事实到论文语言之间的过渡层。它不是润色稿，也不是最终论文。
>
> 版本状态：`V2_CANDIDATE / V1_MAINLINE_UNCHANGED / REAL_DATA_HOLD`。
>
> 标签：`[CONFIRMED]` 结构或输入事实；`[RESULT]` 已复跑结果；`[ASSUMED]` 自设模型条件；`[UPDATEABLE]` 可由新数据/评分细则替换；`[UNCERTAIN]` 当前证据不足；`[OOD/ABSTAIN]` 支持域外，禁止数值外推；`[PAPER_GAP]` 题面尚未被当前技术链完整覆盖。

## 0. 论文对齐接口

| `论文草稿.md` 小节 | 技术填充位置 | 当前可写层 |
|---|---|---|
| 摘要 | 8.1 | V1 合成结果；V2 仅可写“候选分析未放行” |
| 2.1--2.2 问题分析 | 2--4 | 题面、数据流和验证协议 |
| 三、模型假设 | 2 | `[ASSUMED]` 与 `[UPDATEABLE]` |
| 5.1 问题一 | 3 | V1 机制自检；V2 膝点保持 HOLD |
| 5.2 问题二 | 4、6 | V1 SOH/RUL；V2 归一化容量候选 Q2 |
| 5.3 问题三 | 5 | V1 module-level set-packing；不受 V2 覆盖 |
| 5.4 问题四 | 6 | V1 支持域场景、OAT、OOD |
| 六、模型评价与推广 | 7 | 统计、外部效度和工程边界 |
| 七、结论 | 8 | 只写有证据且带范围限定的结论 |

**硬边界：** V2 Zenodo 数据不能覆盖或改写 V1 的 Q3/Q4；不能称 CALCE 实测校准；不能称绝对容量精度；不能将 `evidence_status=HOLD_*` 的数字写入 `论文草稿.md`。

## 1. 研究对象与数据层

### 1.1 V1 主线（论文主体）

- `[CONFIRMED]` 研究对象为 NMC（LiNiMnCo/graphite）参考体系；CALCE INR18650-20R 只用于对象和尺度背景，未读取、解析或拟合 CALCE 原始循环。
- `[CONFIRMED]` 主数据为合成仿真：3 个温度水平、3 个倍率水平、3 个 DOD 水平、每工况 4 芯、每芯 1000 cycles，共 27 工况、108 芯、108000 行。
- `[ASSUMED][UPDATEABLE]` 额定容量、初始内阻、退化系数、个体差异、噪声、80% SOH 终点、Q3 门槛与权重均来自配置，不是实测估计或安全规范。

### 1.2 V2 候选层（独立验证，不进入当前论文）

- `[CONFIRMED]` 来源为 Zenodo `10.5281/zenodo.7250553`，CC BY 4.0；44 芯、24,525 行，NMC532=26 芯、NMC811=18 芯，summary 对齐 44/44。
- `[CONFIRMED]` 解析无循环断裂、缺失或非正容量；原始文件不入 Git，provenance 保存 DOI、许可、输入哈希和字段映射。
- `[UNCERTAIN]` 容量单位仍为 `UNVERIFIED`；温度、DOD、EFC、内阻缺失，不能写 Ah/mAh 精度、温度因果或安全结论。
- `[CONFIRMED]` NMC532 与 NMC811 分开运行，禁止混合拟合或跨化学体系平均掩盖方向差异。

## 2. 假设与符号

### 2.1 可写假设

| 编号 | 假设 | 标签 | 更新条件 |
|---|---|---|---|
| H1 | 支持域内温度、倍率、DOD 增大使退化加速 | `[ASSUMED][UPDATEABLE]` | 同体系实测方向不一致 |
| H2 | 容量和内阻共享分段平方根累计退化量 | `[ASSUMED][UPDATEABLE]` | 真实轨迹不支持分段结构 |
| H3 | 电芯存在截断正态个体差异和观测噪声 | `[ASSUMED][UPDATEABLE]` | 获得真实批次分布 |
| H4 | 80% SOH 是本研究 RUL 终点和临界阶段阈值 | `[ASSUMED][UPDATEABLE]` | 题目/规范给出新终点 |
| H5 | 同一 `cell_id` 的记录不可跨训练测试折 | `[CONFIRMED]` | 不应取消 |
| H6 | 观测窗内未达终点的寿命为右删失 | `[CONFIRMED]` | 观测窗延长后更新 |
| H7 | 支持域外请求直接弃权 | `[CONFIRMED]` | 取得匹配外部数据并重训 |

### 2.2 符号

`c` 为 cycle，`e` 为 EFC，`Q_0` 为初始容量，`R_0` 为初始内阻，`SOH=Q/Q_0`，`T` 为达到终点的寿命，`delta=1` 表示事件、`delta=0` 表示右删失，`RUL=T-c`，`x_g` 表示候选组 g 是否被选择。

## 3. Q1：退化特征与影响因子

### 3.1 V1 生成模型

工况修正：

```text
u_T = exp(k_T * (temperature_C - 25))
u_C = 1 + k_C * (c_rate - 0.5)
u_D = 1 + k_D * (DOD/100 - 0.5)
u   = u_T * u_C * u_D
```

分段平方根累计老化量：

```text
L(e) = sqrt(min(e, n_k))
       + knee_gain * max(0, sqrt(e) - sqrt(n_k))
```

```text
Q_true_i(e) = Q0_i * (1 - alpha_i * u * L(e))
R_true_i(e) = R0_i * (1 + beta_i  * u * L(e))
```

观测值为真值叠加配置噪声；`capacity_obs` 和 `resistance_obs` 是合成观测，不是 CALCE/NASA 实测值。

### 3.2 阶段与因素

- 膝点：在 `sqrt(EFC)` 坐标上做连续 hinge 回归；正常/退化/临界阶段分别由膝点和 SOH=0.8 规则定义。
- 影响因子：对温度、倍率、DOD 的平衡 `3 x 3 x 3` 全因子计算主效应平方和；在可辨识主效应内归一化。CC-CV 只有一个协议水平，协议效应 `NOT_IDENTIFIABLE`。
- `[RESULT]` V1 内部自检：72 芯检测到膝点，36 芯右删失，内部膝点恢复误差中位数 13.40 EFC；这只验证生成器与检测器的结构一致，不是外部精度。
- `[RESULT]` V1 容量衰减主效应内权重：DOD 0.7249、温度 0.2378、倍率 0.0373；内阻增长分别为 0.7317、0.2346、0.0337。排序只适用于当前生成器支持域。

### 3.3 V2 Q1 放行状态

- 原始容量口径：`RAW_UNPROCESSED`，膝点 `HOLD_RPT_SENSITIVITY`。
- 官方来源 `seasonal_decompose(period=50).trend` 口径：`SOURCE_PERIOD50_RETROSPECTIVE`，因双侧趋势使用未来点，只能作回顾性敏感性。
- 两种口径均 `paper_eligible=false`；精确膝点计数已撤下。

## 4. Q2：SOH 与 RUL

### 4.1 V1 预测模型

- SOH：近期容量中位数 / 初始窗口容量中位数。
- SOH 对照：persistence、local-linear、Ridge、Random Forest；外层 `GroupKFold(cell_id)`。
- RUL：右删失 log-normal AFT。事件记录使用密度项，右删失记录使用生存项；删失朴素 Ridge/Random Forest 只作为对照。
- `[RESULT]` V1：Ridge 的 50-cycle SOH RMSE=0.004206，cell-bootstrap 90% CI 为 0.003962--0.004447；AFT 在 43 个事件上 RMSE=38.39 cycles，经验区间覆盖=0.9070，删失矛盾率=0。
- 结构匹配 RUL 仅为 simulator ceiling，不可用于真实泛化宣称。

### 4.2 V2 统一验证协议

1. 每芯前最多 10 个容量观测的中位数作归一化基线；容量单位不做猜测。
2. 以最近 30-cycle Theil-Sen 斜率、当前归一化容量、cycle 和可用 C-rate 预测未来 30-cycle 归一化容量。
3. 外层 5 折 `GroupKFold(cell_id)`；另做完整复合实验层 LOCO。LOCO 字段固定为 `pack + chemistry + design + c_rate + protocol`，每折披露芯数。
4. 不确定性是训练电芯校准的描述性残差包络；逐预测行 coverage 与整芯同时 coverage 分开报告；`finite_sample_guarantee=false`。

### 4.3 V2 双口径结果（候选，不入论文）

| 口径/体系 | Persistence RMSE | Ridge RMSE | 相对变化 | 逐行 coverage | 整芯 coverage | LOCO RMSE |
|---|---:|---:|---:|---:|---:|---:|
| 原始/NMC532 | 0.016107 | 0.017227 | +6.95% | 0.9865 | 23/26=0.8846 | 0.015828 |
| 原始/NMC811 | 0.004555 | 0.002865 | -37.11% | 0.9965 | 15/18=0.8333 | 0.002813 |
| period=50/NMC532 | 0.009211 | 0.005267 | -42.82% | 0.9977 | 23/26=0.8846 | 0.005286 |
| period=50/NMC811 | 0.004065 | 0.001486 | -63.45% | 0.9344 | 15/18=0.8333 | 0.001572 |

**关键判定：** NMC532 的 Ridge 相对 persistence 方向随 RPT 口径翻转；因此 V2 Q2 headline 统一标记 `HOLD_RPT_SENSITIVITY`。逐行 coverage 不是整芯 coverage；每折仅 4--7 个校准芯，不能声称 90% 电芯级有限样本保证。

## 5. Q3：退役筛选与编组

- cycle=750 生成候选池；门槛为 SOH、RUL 区间下界、内阻增长和寿命区间宽度。所有门槛为 `[ASSUMED][UPDATEABLE]`。
- 枚举 4 芯兼容组，定义容量、SOH、RUL、内阻离散度和无量纲成本/收益代理。
- 以二元变量 `x_g` 建 set-packing MILP：每芯至多一次，恰好 8 组，目标权衡收益、不一致、风险和成本。
- `[RESULT]` 108 候选中 85 过门槛，生成 3167 个候选组；三套权重均选 8 组、32 芯、重复分配 0；平衡 MILP 目标 1.2048，贪心 1.0828。
- `[PAPER_GAP]` 这是 4 芯 module-level 兼容编组，不包含串并联拓扑、功率/能量约束、热模型或货币收益；V2 不覆盖 Q3。

## 6. Q4：多工况、鲁棒性与弃权

- 支持域内场景：baseline、high_temperature、high_c_rate、high_dod、combined_stress；5 个 seed，7 个参数做 `+/-10%` OAT；批次差异使用参数代理。
- `[RESULT]` V1：baseline 平均末期 SOH 0.8541；high_temperature 0.7833、临界比例 0.9667；combined_stress 0.6857、临界比例 1.0、筛选率 0。
- `[OOD/ABSTAIN]` 低温、过充协议、DOD=110%、3C 均不输出数值预测。
- `[PAPER_GAP]` 每个场景重新生成、筛选和编组；不是 Q3 同一组 cell_id 的纵向压力验证。

## 7. 统计与诚信验收

1. 所有训练/测试划分按 `cell_id`；报告 `max_cell_overlap=0`。
2. 按电芯 bootstrap，不按循环行 bootstrap；不把行数当独立样本量。
3. 不使用“统计显著”措辞；无 p-value/多重检验。
4. V2 成功计算不等于科学放行：读取 `run_status` 判断计算，读取 `evidence_status` 和 `paper_eligible` 判断论文资格。
5. 真实数据、RPT 预处理、容量单位、温度/DOD/EFC/内阻字段必须在 provenance 中可回算；缺失字段标 `UNCERTAIN/OOD/ABSTAIN`。

## 8. 论文可写结论

### 8.1 可以写

- `[RESULT]` 在本合成仿真、`GroupKFold(cell_id)` 留组实验中，Ridge 取得最低 SOH RMSE；AFT 保留右删失信息并提供经验区间。
- `[RESULT]` 在本合成生成器内，DOD 的主效应权重高于温度和倍率；协议因只有 CC-CV 一个水平不可辨识。
- `[RESULT]` 当前候选组集合与权重下，MILP 满足 4 芯组规模和唯一分配约束。
- `[OOD/ABSTAIN]` 支持域外输入不做数值外推。

### 8.2 暂不能写

- CALCE/NASA 实测校准或外部验证已完成。
- V2 Ridge 的单一 RMSE 可代表真实电芯、车辆或跨化学体系精度。
- 80% SOH 是普适安全阈值；Q3 目标值是人民币收益；Q4 是真实安全验证。
- Q3 编组已在 Q4 同一电芯组上完成长期压力验证。

## 9. 复现入口

V1：

```bash
PYTHONPATH=code python -m battery_study.cli \
  --config configs/study_pipeline.json --out study_output
PYTHONPATH=code python -m pytest code/tests -q
```

V2 准备与验证：

```bash
conda run -n normal python technical/prepare_nmc_modes.py \
  --raw-root "/path/to/Battery raw data" \
  --summary "/path/to/Pouch cell_summary.xlsx" \
  --out-dir /tmp/nmc_modes_prepared

PYTHONPATH=code python -m battery_real.cli \
  /tmp/nmc_modes_prepared/canonical_capacity_NMC532.csv \
  --out /tmp/nmc_validation/nmc532 \
  --history-window 30 --horizon 30 --splits 5 \
  --bootstrap-reps 100 --leave-condition-out
```

period=50 只作为回顾性敏感性：

```bash
conda run -n normal python technical/prepare_nmc_rpt.py \
  /tmp/nmc_modes_prepared/canonical_capacity_NMC532.csv \
  /tmp/nmc_modes_prepared/canonical_capacity_NMC532_rpt50.csv \
  --period 50
```

任何输入、代码、依赖、seed 或预处理变化，都必须重新生成报告、哈希和论文主张-证据表。
