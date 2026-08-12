# A题论文技术过渡包

> 文档类型：技术过渡层；不是论文成稿，不提供修辞包装。
>
> 用途：把题面、代码、配置、实验输出转换为论文可用的结构化材料。
>
> 状态：`READY_FOR_DRAFT_WITH_LIMITATIONS`。

## 0. 版本与事实源

| 项 | 当前值 |
|---|---|
| 赛题 | 锂电池剩余寿命预测与梯次利用筛选优化（A题） |
| 最新论文骨架 | `/home/jerry/Downloads/Documents/数模论文模板总结.docx` |
| 骨架 SHA-256 | `55468c073dc248dacbd91f84f06cc4070a99acbccba913907ad6efc57a6eddff` |
| 骨架结构 | 375 段、10 表、1 个内嵌图形对象 |
| 仓库根目录未跟踪同名文件 | `数模论文模板总结.docx`；SHA-256=`e3d40561da14c988531413c9d2069ec4a3ae97e4d19eeebedc6a12ce01d42dc2` |
| 仓库内同名模板 | `template/paper/数模论文模板总结.docx`；SHA-256=`6812912987ecad46a4a452ad55a32cce2332221bf4b038d1a3ecb8ab18bcfdfe` |
| 模板一致性 | 两个仓库副本均与最新下载版哈希不同；论文内容以最新下载版为准 |
| Git 基线 | 不固定；论文 Agent 每次先拉取 `origin/main` 并记录当次 `git rev-parse HEAD` |
| 实验编号 | `A_NMC_G2_G4_v1` |
| 主运行命令 | `PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output` |
| 数据性质 | 全部为 NMC 合成仿真；不是 CALCE、NASA 或企业实测数据 |
| 当前论文阶段 | Stage 2 WRITE；未通过 Stage 2.5 INTEGRITY |
| 最近流水线验证 | 9/9 validation gates PASS；`python -m pytest code/tests -q` = 56 passed |

事实源优先级：

1. 题面、`.codex/DECISIONS.md`、已签署闸门。
2. `handoffs/A0_Task_Contract.md`、`handoffs/A1-A4*.md`。
3. `study_output/*.json`、`study_output/*.csv`、`study_output/run_manifest.json`。
4. `technical/*.md`、图表和论文骨架。
5. 聊天、Agent 记忆、模板示例。

## 1. 标签与写作动作

| 标签 | 技术含义 | 论文动作 |
|---|---|---|
| `[CONFIRMED]` | 题面、代码、配置或可复跑结构已确定 | 可直接写，但不能扩展为真实世界效果 |
| `[RESULT]` | 当前固定仿真实验的输出 | 必须带“本合成仿真/留组实验中”限定语 |
| `[ASSUMED]` | 研究者设定，不是观测值 | 明示为假设 |
| `[UPDATEABLE]` | 真实数据、规范或评分细则到位后应替换 | 保留参数入口，不写成行业标准 |
| `[UNCERTAIN]` | 当前证据无法确定 | 写入局限，不用常识或模型输出填空 |
| `[OOD/ABSTAIN]` | 超出支持域，禁止数值外推 | 只报告弃权和需要补充的数据 |
| `[PAPER_GAP]` | 技术链没有完全覆盖题面或论文栏目 | 限定范围或补做，不伪装成已完成 |
| `[EVIDENCE_REQUIRED]` | 外部文献尚未完成全文/页码核验 | 核验前不得作为关键结论依据 |

硬禁止：

- 不写“基于 CALCE 实测完成参数校准”。
- 不写“NASA 数据验证了退化趋势”。
- 不写“真实车辆预测精度”“真实安全失效概率”。
- 不写“80% SOH 是普适安全阈值”。
- 不写人民币成本、利润、投资回报或行业收益。
- 不给低温、过充、过放、3C 数值预测。
- 不用结构匹配模型的结果证明生成器真实有效。

## 2. 论文骨架映射

### 2.1 章节映射

| DOCX 位置 | 当前内容状态 | 技术输入 | 论文手动作 |
|---|---|---|---|
| 段 1--9：标题、摘要、关键词 | 模板说明为主 | 本文件第 13 节“摘要要素” | 最后写；删除全部教学文字 |
| 段 70--83：问题重述 | 已有初稿 | 题面 + 第 3 节全局边界 | 保留题面信息；删除安全/成本的确定性语气 |
| 段 89--119：问题分析 | 已有初稿 | 本文件第 4--7 节 | 替换 CALCE/NASA 错误表述 |
| 段 120--125：模型假设 | 部分完成 | 本文件 3.2 | 按标签拆分确定、假设、不确定项 |
| 段 127--132：符号说明 | 部分完成 | 本文件 3.3 | 补 RUL、删失、优化变量和评价指标 |
| 段 135--182：问题一 | 方法部分已成形 | 本文件第 4 节 | 加实验设计、结果、限制和图表 |
| 段 199--204：问题二 | 实质为空 | 本文件第 5 节 | 填 SOH、RUL、验证和结果 |
| 段 207--214：问题三 | 实质为空 | 本文件第 6 节 | 填门槛、组生成、MILP、对照和限制 |
| 问题四正文 | 缺失 | 本文件第 7 节 | 新增完整小节 |
| 段 215--244：分析评价推广 | 模板教学文字 | 本文件第 8、9 节 | 全量替换 |
| 段 246--284：参考文献 | 无关示例 | 本文件第 12 节 | 删除示例；仅放人工核验条目 |
| 段 285--374：附录 | 通用示例代码 | 本文件第 14 节 | 删除 jieba/AHP；换成支撑材料索引 |

### 2.2 最新 DOCX 原文冲突登记（不可直接复制）

以下登记针对 SHA-256=`55468c073dc248dacbd91f84f06cc4070a99acbccba913907ad6efc57a6eddff` 的下载版 DOCX。原文中的 `EVIDENCE REQUIRED` 标记也不能被整体删除；每条主张仍需人工核验或降级。

| DOCX 段落 | 原文信号（摘要） | 当前事实 | 必须动作 | 状态 |
|---:|---|---|---|---|
| 101、137、141 | “CALCE ... 核心参数校准依据” | 未下载、解析或拟合 CALCE 原始循环；CALCE 仅用于选择 NMC 对象和尺度参考；全部退化系数为仿真设定 | 改为“参考对象/尺度边界”，删除“校准依据/实测校准” | `P0_REPLACE` |
| 141 | “NASA ... 容量退化趋势辅助对照” | NASA 未进入 G1-G4 的生成、训练、验证或参数估计 | 删除“辅助对照”；写入“未使用，未来可做独立外部对照” | `P0_REPLACE` |
| 115--116 | “安全失效边界、检测成本、串并联编组” | Q3 只有自设门槛、无量纲成本/收益和 4 芯 module-level set-packing；无安全概率、货币成本或串并联拓扑 | 改为“条件化筛选与兼容编组”；明确 `[ASSUMED][UPDATEABLE]` 和 `[PAPER_GAP]` | `P0_REPLACE` |
| 120 | “四类工程场景，对已有编组方案开展长周期验证” | 数值实验是 5 个支持域运行场景；另有 3 个批次代理、7 参数 OAT；每个场景重新筛选/编组，未纵向延续 Q3 同组电芯 | 改为“5 场景下重新筛选/编组比较 + 批次代理 + OAT + OOD/ABSTAIN”；删除“已有编组已验证” | `P0_REPLACE` |
| 149 | “范围外仅作为未校准压力测试” | 当前代码不对范围外输入给数值；低温、过充、过放、3C 均 `numeric_prediction=null` | 改为支持域控制和显式弃权；不得从生成器外推 | `P0_REPLACE` |
| 172 | “截断后重新缩放初始容量和内阻，确保仍在台账范围” | Q0 只做正值检查；R0、alpha、beta 受冻结边界约束；不存在统一“重新缩放”步骤 | 按 `code/g1_generator/degradation.py` 的实际采样规则改写 | `P1_REPLACE` |
| 182 | “如 seed=42” | 正式全因子 seed=`20260811`；Q4 seeds=`42,123,2026,4096,8110`；42 是 G1 冒烟/其中一个鲁棒性 seed | 按实验阶段列出 seed，不把示例 seed 当正式唯一 seed | `P1_REPLACE` |
| 200--214 | Q2、Q3 小节为空/公式占位 | Q2/Q3 已有完整实现和结果接口 | 用本包第 5、6 节填充；删除二次方程等模板占位 | `P1_REPLACE` |
| 234--245 | `XXX`、通用模型教学文字 | 非研究内容 | 全部删除，替换为本包第 8、9 节的模型评价、限制和更新接口 | `P1_REPLACE` |
| 247--284 | 文本情感分析示例参考文献/教学说明 | 与 A 题无关；候选来源尚未逐条全文核验 | 删除示例；仅保留人工核验后的 A 题来源 | `P0_REPLACE` |
| 303--374 | jieba 诗词统计、AHP MATLAB 示例 | 与当前电池流水线无关，不能作为支撑代码 | 删除；改为 A1-A4 文件、运行命令、manifest 和哈希索引 | `P1_REPLACE` |

### 2.3 技术完成状态与未完成项

| 项目 | 当前状态 | 可否在论文中写成已完成 |
|---|---|---|
| G1-G4 合成仿真、预测、编组、鲁棒性流水线 | `DONE`；9/9 gates、56 tests、manifest 可回算 | 可以，但必须带合成/支持域限定 |
| Q1-Q4 技术过渡材料（假设、公式、协议、数字、证据回指） | `DONE_WITH_LIMITATIONS`；本文件第 4--9 节 | 可以按标签使用 |
| 最新 DOCX 到在线文档的逐段替换 | `PENDING_PAPER_AGENT` | 不可；模板原文仍含冲突和占位 |
| 外部文献逐条全文、页码/表号核验 | `PENDING_HUMAN_VERIFICATION` | 不可把候选引用写成已核验 |
| CALCE 原始数据拟合、NASA 外部验证 | `NOT_DONE / OUT_OF_SCOPE` | 不可 |
| 低温/过充/过放/3C 数值实验 | `NOT_DONE / OOD_ABSTAIN` | 不可；只能写弃权 |
| 完整储能系统串并联拓扑、功率/能量约束、货币收益 | `NOT_DONE / PAPER_GAP` | 不可；只能写 module-level 相容编组 |

上述 `PENDING`/`NOT_DONE` 是交付边界，不是可由文字补齐的空白；只有取得新数据或完成论文人工核验后才能改变状态。

### 2.4 必须覆盖的四问

| 问题 | 输入 | 技术输出 | 当前覆盖状态 |
|---|---|---|---|
| Q1 退化特征与因素辨识 | cycle、EFC、容量、内阻、T、C-rate、DOD、协议 | 阶段、膝点、因素权重、协议不可辨识 | `PARTIAL_SYNTHETIC_PROTOCOL_UNIDENTIFIED` |
| Q2 SOH 与 RUL | 历史观测、工况、右删失信息 | 当前 SOH、50-cycle SOH、RUL 点预测与区间 | `PARTIAL_IN_DOMAIN_EXTREMES_ABSTAINED` |
| Q3 筛选与编组 | SOH、RUL、区间、容量、内阻 | 硬门槛、分级、4 芯兼容组、8 组 MILP | `PARTIAL_MODULE_GROUPING_ONLY` |
| Q4 多工况与鲁棒性 | 5 个支持域场景、5 seeds、7 参数 | Monte Carlo、OAT、批次代理、弃权规则 | `PARTIAL_SCENARIO_REOPTIMIZATION_ONLY` |

`[PAPER_GAP]`：Q3 当前是电芯到 4 芯兼容组的 module-level set-packing，不包含给定电压、功率、容量需求下的串并联阵列拓扑；论文不得称为完整储能系统电气设计。

`[PAPER_GAP]`：Q4 对每个新场景重新生成电芯、筛选并优化，没有把 Q3 已选定的同一组 `cell_id` 沿压力工况继续演化。因此只能写“场景下重新筛选/编组的稳健性比较”，不能写“原 Q3 编组经长期压力验证仍稳定”。

## 3. 全局假设、数据与符号

### 3.1 数据生成边界

| 项 | 当前设定 | 标签 | 来源 |
|---|---:|---|---|
| 化学体系 | NMC / LiNiMnCo-graphite | `[CONFIRMED]` 研究对象 | `configs/g1_smoke.json` |
| 额定容量尺度 | 2.0 Ah | `[ASSUMED][UPDATEABLE]` 尺度参考 | `configs/g1_smoke.json` |
| 初始内阻基准 | 0.05 Ohm | `[ASSUMED][UPDATEABLE]` | `configs/g1_smoke.json` |
| 循环长度 | 1000 cycles | `[CONFIRMED]` 配置 | `configs/g1_smoke.json` |
| 温度支持域 | 25--50 degC；实验水平 25/35/45 | `[CONFIRMED]` 配置边界 | `configs/study_pipeline.json` |
| 倍率支持域 | 0.5--2C；实验水平 0.5/1/2C | `[CONFIRMED]` 配置边界 | 同上 |
| DOD 支持域 | 50--100%；实验水平 50/80/100% | `[CONFIRMED]` 配置边界 | 同上 |
| 协议 | 仅 CC-CV | `[CONFIRMED]` 单一水平 | 同上 |
| 全因子规模 | 27 工况 x 4 电芯 x 1000 cycles = 108000 行 | `[CONFIRMED]` | `study_output/factorial_generation_meta.json` |
| 正式仿真 seed | 20260811 | `[CONFIRMED]` | `configs/study_pipeline.json` |

CALCE/NASA 边界：

- CALCE INR18650-20R：只允许写“用于选定 NMC 对象及容量/内阻尺度参考”。
- CALCE 原始循环文件：未下载、未解析、未拟合。
- NASA：未进入 G1-G4 代码、训练、验证或参数估计。
- 参数 `alpha/beta/k_T/k_C/k_D/n_k/sigma_*`：全部为仿真配置，不是实验估计。

### 3.2 假设清单

| ID | 假设 | 标签 | 推翻/更新条件 |
|---|---|---|---|
| H1 | 支持域内温度、倍率、DOD 增大时退化加速 | `[ASSUMED][UPDATEABLE]` | 独立同体系数据显示方向不一致 |
| H2 | 容量与内阻共享分段平方根累计退化量 | `[ASSUMED][UPDATEABLE]` | 真实轨迹不支持该阶段结构 |
| H3 | 电芯初值和退化速率含截断正态个体差异 | `[ASSUMED][UPDATEABLE]` | 获得真实批次分布 |
| H4 | 80% SOH 作为 RUL 终点和临界阶段建模阈值 | `[ASSUMED][UPDATEABLE]` | 题目/规范/业务定义给出其他终点 |
| H5 | 同一 `cell_id` 的全部记录只能进入同一外层折 | `[CONFIRMED]` 数据隔离规则 | 不应取消 |
| H6 | 1000 cycles 内未过 80% SOH 的寿命为右删失 | `[CONFIRMED]` 统计定义 | 观测窗延长后更新事件状态 |
| H7 | Q3 门槛、权重、成本收益均为无量纲决策设定 | `[ASSUMED][UPDATEABLE]` | 获得检测误差、规范和商业数据 |
| H8 | 支持域外请求直接弃权 | `[CONFIRMED]` 风险控制规则 | 获得匹配数据并重新训练后才可解除 |

### 3.3 核心符号

| 符号 | 含义 | 单位/范围 |
|---|---|---|
| `c` | 循环次数 | cycle |
| `e` | 等效完整循环数 `EFC = sum(DOD/100)` | EFC |
| `Q0_i` | 电芯 i 的初始容量 | Ah |
| `R0_i` | 电芯 i 的初始内阻 | Ohm |
| `Q_i(e)` | 无噪声合成容量 | Ah |
| `R_i(e)` | 无噪声合成内阻 | Ohm |
| `SOH_i(e)` | `Q_i(e)/Q0_i` | 0--1 |
| `T_i` | 电芯 i 到达终点的寿命 | cycle |
| `delta_i` | 寿命事件指示；1=已达到终点，0=右删失 | 0/1 |
| `RUL_i(c)` | `T_i-c` | cycle |
| `n_k` | 仿真膝点位置 | EFC |
| `alpha_i` | 电芯容量衰减系数 | SOH/sqrt(EFC) |
| `beta_i` | 电芯内阻增长系数 | relative/sqrt(EFC) |
| `x_g` | 是否选择候选组 g | 0/1 |
| `B_g/I_g/R_g/C_g` | 组 g 的归一化收益/不一致/风险/成本指数 | 0--1 |

### 3.4 生成模型

工况修正：

```text
u_T = exp(k_T * (T - 25))
u_C = 1 + k_C * (C_rate - 0.5)
u_D = 1 + k_D * (DOD/100 - 0.5)
u   = u_T * u_C * u_D
```

分段累计退化量：

```text
L(e) = sqrt(min(e, n_k))
     + knee_gain * max(0, sqrt(e) - sqrt(n_k))
```

当前配置：

| 参数 | 当前值 | 冻结范围 | 标签 |
|---|---:|---:|---|
| `alpha` | 0.004 | 0.003--0.006 | `[ASSUMED][UPDATEABLE]` |
| `beta` | 0.010 | 0.005--0.020 | `[ASSUMED][UPDATEABLE]` |
| `k_T` | 0.020 | 0.010--0.030 | `[ASSUMED][UPDATEABLE]` |
| `k_C` | 0.10 | 0.05--0.20 | `[ASSUMED][UPDATEABLE]` |
| `k_D` | 0.50 | 0.20--0.80 | `[ASSUMED][UPDATEABLE]` |
| `n_k` | 700 EFC | 600--850 | `[ASSUMED][UPDATEABLE]` |
| `knee_gain` | 2.0 | 固定 | `[ASSUMED][UPDATEABLE]` |
| `sigma_Q` | 0.6% of `Q_nom` | 0.2--1.0% | `[ASSUMED][UPDATEABLE]` |
| `sigma_R` | 1.5% of `R_true` | 0.5--3.0% | `[ASSUMED][UPDATEABLE]` |
| `sigma_cell` | 0.05 | 0.03--0.10 | `[ASSUMED][UPDATEABLE]` |

电芯参数与轨迹：

```text
theta_i = theta_0 * (1 + epsilon_i)
epsilon_i ~ TruncatedNormal(0, sigma_cell, [-2*sigma_cell, 2*sigma_cell])

SOH_i(e) = 1 - alpha_i * u * L(e)
Q_i(e)   = Q0_i * SOH_i(e)
R_i(e)   = R0_i * [1 + beta_i * u * L(e)]

Q_obs = Q_i(e) + Normal(0, sigma_Q * Q_nom)
R_obs = R_i(e) + Normal(0, sigma_R * R_i(e))
```

`capacity_true`、`resistance_true` 是仿真内部无噪声量；不是现实真值。`capacity_obs`、`resistance_obs` 是加噪合成观测；不是外部实测。

## 4. Q1 技术块：退化阶段与因素辨识

### 4.1 输入、输出、模型

| 项 | 技术定义 |
|---|---|
| 输入 | 每颗电芯 1--1000 cycle 的容量、内阻、EFC、T、C-rate、DOD、协议 |
| 输出 1 | normal / degradation / critical 三阶段 |
| 输出 2 | 检测膝点、右删失状态、膝点恢复误差 |
| 输出 3 | 温度、倍率、DOD 对容量衰减/内阻增长的主效应权重 |
| 不输出 | 单一 CC-CV 协议的影响权重；cycle/EFC 的随机因素权重 |

阶段定义：

```text
normal      : SOH > 0.8 且 EFC < detected_knee
degradation : SOH > 0.8 且 EFC >= detected_knee
critical    : SOH <= 0.8
```

三阶段是 `[ASSUMED][UPDATEABLE]` 建模划分；`critical` 不等于安全失效。

膝点检测：对每颗电芯每 5 个 cycle 抽样，在 `sqrt(EFC)` 坐标上搜索连续 hinge 回归的最小 SSE：

```text
y(e) = b0 + b1*sqrt(e) + b2*max(0, sqrt(e)-sqrt(k))
k_hat = argmin_k SSE(k)
```

若最大 EFC 小于生成器名义 `n_k`，写 `RIGHT_CENSORED`，不强行给膝点。

主效应分解：对响应 `Y` 分别使用末期容量衰减和末期内阻增长。

```text
SS_j = sum_l n_l * (mean(Y | factor_j=l) - mean(Y))^2
w_j  = SS_j / sum_{j in {T,C,DOD}} SS_j
share_j = SS_j / SS_total
```

`w_j` 只在三个可估主效应内归一化；交互和电芯差异保留在剩余方差，不被分摊给主效应。

### 4.2 实验协议

| 项 | 值 |
|---|---|
| 设计 | `3 x 3 x 3` 平衡全因子 |
| 每格电芯 | 4 |
| 响应 | `1-final_soh`、`final_resistance/initial_resistance-1` |
| 膝点搜索下限 | 300 EFC |
| 两侧最小点数 | 80 cycle 原始点 |
| 右删失原因 | DOD=50% 时 1000 cycles 仅覆盖 500 EFC，小于 `n_k=700 EFC` |

### 4.3 结果

膝点：

| 指标 | 结果 | 标签 |
|---|---:|---|
| 可检测电芯 | 72 | `[RESULT]` |
| 右删失电芯 | 36 | `[RESULT]` |
| 对可检测电芯的膝点绝对误差中位数 | 13.40 EFC | `[RESULT]` 仿真内部恢复检查 |

容量衰减：

| 因素 | 主效应内权重 | 总方差占比 | 边际均值范围 |
|---|---:|---:|---:|
| 温度 | 0.2378 | 0.2289 | 0.1476--0.2195 |
| 倍率 | 0.0373 | 0.0359 | 0.1697--0.1978 |
| DOD | 0.7249 | 0.6979 | 0.1191--0.2449 |

内阻增长：

| 因素 | 主效应内权重 | 总方差占比 | 边际均值范围 |
|---|---:|---:|---:|
| 温度 | 0.2346 | 0.2264 | 0.3514--0.5194 |
| 倍率 | 0.0337 | 0.0325 | 0.4072--0.4691 |
| DOD | 0.7317 | 0.7060 | 0.2832--0.5800 |

分层方向审计（固定另两个因素，在 9 个分层内比较第三因素的三级均值）：

| 响应/因素 | 单调增加分层 | 局部反转分层 | 解释 |
|---|---:|---:|---|
| 容量衰减/温度 | 9/9 | 0 | 仅为生成器内方向检查 |
| 容量衰减/倍率 | 9/9 | 0 | 同上 |
| 容量衰减/DOD | 9/9 | 0 | 同上 |
| 内阻增长/温度 | 9/9 | 0 | 同上 |
| 内阻增长/倍率 | 8/9 | 1 | T=25 degC、DOD=80% 时，0.5/1/2C 均值为 0.3383/0.3334/0.3898；个体随机效应使 0.5C 到 1C 出现局部反转 |
| 内阻增长/DOD | 9/9 | 0 | 仅为生成器内方向检查 |

因此主效应排序描述总体边际均值，不等于每个工况分层或每颗电芯都严格单调。

协议：`NOT_IDENTIFIABLE`；所有样本均为 CC-CV，权重必须为空。

### 4.4 可转入论文的结论原子

- `[RESULT]` 本全因子仿真中，DOD 的主效应内权重最高，温度次之，倍率最低。
- `[RESULT]` 该排序由生成器设定和冻结支持域共同决定，只能用于仿真内因素辨识演示。
- `[RESULT]` 内阻增长的倍率效应在 1/9 个分层出现局部反转；总体主效应不能扩展成逐分层严格单调。
- `[RESULT]` 72 颗电芯的膝点可在观测窗内检测；36 颗因 EFC 覆盖不足按右删失处理。
- `[UNCERTAIN]` 没有独立实测数据，不能把权重解释为真实 NMC 电池的普适机理贡献。

证据：`study_output/q1_summary.json`、`study_output/q1_factor_effects.csv`、`study_output/q1_knee_detection.csv`、`study_output/q1_stage_counts.csv`、`study_output/fig_q1_factor_weights.svg`。

## 5. Q2 技术块：SOH 与 RUL

### 5.1 SOH 定义与特征

当前 SOH 观测估计：

```text
Q0_hat = median(capacity_obs at cycles 1..10)
Qcur_hat(c) = median(last 5 capacity_obs values at cycle c)
SOH_obs(c) = Qcur_hat(c) / Q0_hat
```

特征向量：

```text
x = [SOH_obs, capacity_obs, resistance_growth,
     capacity_slope, resistance_slope,
     cycle, EFC, temperature, C_rate, DOD]
```

50-cycle 预测样本：

| 项 | 值 |
|---|---|
| 历史窗口 | 100 cycles |
| 预测步长 | 50 cycles |
| 快照间隔 | 50 cycles |
| 每芯样本 | 18 |
| 总样本 | 1944 |
| 目标 | cycle `c+50` 的仿真内部 `SOH_true` |

对照模型：

- persistence：`SOH_hat(c+50)=SOH_obs(c)`。
- local linear：近期容量斜率线性外推。
- Ridge：标准化 + `alpha=1.0`。
- Random Forest：160 trees、`min_samples_leaf=3`、`max_features=0.8`。

### 5.2 数据隔离与不确定性

| 项 | 协议 |
|---|---|
| 外层验证 | 5 折 `GroupKFold(cell_id)` |
| 电芯泄漏 | 每折 `cell_id` 交集为 0 |
| 折规模 | 22/22/22/21/21 个测试电芯 |
| 置信区间 | 以电芯为单位 bootstrap 300 次，90% CI |
| 压力测试 | 27 次 leave-one-condition-out |

leave-condition-out 的 RMSE 范围：

| 模型 | 27 工况最小 RMSE | 最大 RMSE | 平均 RMSE |
|---|---:|---:|---:|
| persistence | 0.010619 | 0.030895 | 0.018632 |
| local linear | 0.007137 | 0.017073 | 0.010947 |
| Ridge | 0.003271 | 0.006305 | 0.004180 |
| Random Forest | 0.003413 | 0.011721 | 0.004775 |

该压力测试仍在生成器定义的 27 工况集合内；不是外部数据验证。

### 5.3 RUL 定义与删失模型

| 项 | 值 |
|---|---|
| landmark | cycle 300 |
| 终点 | 首次 `SOH_true <= 0.8` |
| 事件 | 43 电芯 |
| 右删失 | 65 电芯 |
| 删失时点 | cycle 1000 |

log-normal AFT：

```text
log(T_i) = beta_0 + beta^T z(x_i) + sigma * epsilon_i
epsilon_i ~ Normal(0,1)

event contribution    : log f(T_i | x_i)
censored contribution : log S(C_i | x_i)
```

名义 90% 区间半径：

```text
r = max(z_0.95 * sigma,
        quantile_0.99(|log(T_event)-log(T_hat_event)| on training events))
[T_lower, T_upper] = [exp(mu-r), exp(mu+r)]
```

Ridge/RF RUL 对照只用训练折中已观测事件，属于 censoring-naive；结构匹配模型使用生成器同构公式，只是 simulator ceiling。

### 5.4 结果

当前 SOH 估计：

| MAE | RMSE | R2 |
|---:|---:|---:|
| 0.010891 | 0.011887 | 0.9461 |

50-cycle SOH：

| 模型 | MAE | RMSE | R2 | RMSE 90% cell-bootstrap CI |
|---|---:|---:|---:|---:|
| Ridge | 0.003345 | 0.004206 | 0.9936 | 0.003962--0.004447 |
| Random Forest | 0.003583 | 0.004531 | 0.9925 | 0.004303--0.004761 |
| local linear | 0.009982 | 0.011243 | 0.9541 | 0.010731--0.011752 |
| persistence | 0.018056 | 0.019355 | 0.8640 | 0.018463--0.020227 |

RUL：

| 模型 | 事件 MAE | 事件 RMSE | R2 | 删失提前失效矛盾率 | 事件区间覆盖 |
|---|---:|---:|---:|---:|---:|
| local linear | 82.57 | 99.65 | 0.5028 | 0.1077 | NA |
| log-normal AFT | 31.80 | 38.39 | 0.9262 | 0.0000 | 0.9070 |
| Ridge observed-only | 30.21 | 36.88 | 0.9319 | 0.0154 | NA |
| Random Forest observed-only | 45.14 | 54.84 | 0.8494 | 1.0000 | NA |
| structure-matched ceiling | 9.68 | 11.89 | 0.9929 | 0.0000 | NA |

模型选择口径：

- SOH 主模型：Ridge；理由是留组 RMSE 最低且 leave-condition-out 均值最低。
- RUL 主模型：log-normal AFT；理由是使用全部事件/删失样本并输出寿命区间。
- 不得写“AFT 点误差最低”；Ridge observed-only 的事件 RMSE 数值略低，但统计上忽略删失机制。
- 结构匹配 ceiling 不参加现实模型优劣排序。

### 5.5 可转入论文的结论原子

- `[RESULT]` 本合成数据的 5 折电芯留组实验中，Ridge 的 50-cycle SOH RMSE 为 0.004206。
- `[RESULT]` 43 个可观测事件上，AFT RUL RMSE 为 38.39 cycles，90% 事件区间覆盖率为 0.9070。
- `[RESULT]` AFT 对 65 个右删失样本的提前失效矛盾率为 0；该指标只检查预测是否违反删失下界。
- `[UNCERTAIN]` 误差数字不代表真实电芯、车辆或外部数据精度。
- `[OOD/ABSTAIN]` 低温、过充、过放和 3C 不给寿命数字。

证据：`study_output/q2_soh_metrics.csv`、`study_output/q2_rul_metrics.csv`、`study_output/q2_split_audit.json`、`study_output/q2_leave_condition_out.csv`、`study_output/fig_q2_soh_rmse.svg`、`study_output/fig_q2_rul_rmse.svg`。

## 6. Q3 技术块：筛选、分级与编组

### 6.1 候选池与预测接口

| 项 | 当前设定 | 标签 |
|---|---:|---|
| 退役快照 | cycle 750 | `[ASSUMED][UPDATEABLE]` |
| 候选电芯 | 108 | `[CONFIRMED]` |
| SOH 来源 | cycle 750 最近观测窗口 | `[CONFIRMED]` |
| RUL 来源 | cycle 300 的 OOF AFT 寿命预测减去 750 | `[CONFIRMED][PAPER_GAP]` |
| 分组大小 | 4 cells/group | `[ASSUMED][UPDATEABLE]` |
| 目标组数 | 8 | `[ASSUMED][UPDATEABLE]` |

`[PAPER_GAP]`：RUL 未在 cycle 750 重新估计。论文应写“使用 landmark 预测寿命在退役快照处换算剩余寿命”，不能写“cycle 750 在线更新的 RUL”。

### 6.2 硬门槛与分级

| 门槛 | 值 | 状态 |
|---|---:|---|
| 最低 SOH | 0.76 | `[ASSUMED][UPDATEABLE]` |
| 最低 RUL 90% 下界 | 40 cycles | `[ASSUMED][UPDATEABLE]` |
| 最大内阻增长 | 0.45 | `[ASSUMED][UPDATEABLE]` |
| 最大寿命区间宽度 | 650 cycles | `[ASSUMED][UPDATEABLE]` |

分级：

```text
A: 全部硬门槛通过 AND SOH >= 0.85 AND RUL lower bound >= 250
B: 全部硬门槛通过，但不满足 A
REJECT: 任一硬门槛失败
```

当前未出现 SOH/区间宽度门槛失败；失败计数为：

| 原因 | 电芯数 |
|---|---:|
| `RUL_LOWER_BELOW_MIN` | 23 |
| `RESISTANCE_GROWTH_ABOVE_MAX` | 11 |

同一电芯可能同时触发多个失败原因，原因计数不用于直接反推拒绝电芯总数。

### 6.3 候选组指标

对标准化特征空间中的近邻电芯枚举 4 芯组。原始组指标：

```text
benefit_raw = mean(capacity) * min(predicted_RUL) * mean(SOH)

inconsistency_raw = CV(capacity)
                  + 2*range(SOH)
                  + 0.5*CV(predicted_RUL)
                  + range(resistance_growth)

risk_raw = mean(lifetime_interval_width) / max(min(predicted_RUL), 1)

cost_raw = group_size
         + 20*CV(capacity)
         + 10*range(SOH)
         + 5*range(resistance_growth)
```

四项在全部候选组内做 min-max 归一化，得到 `B_g/I_g/R_g/C_g`。成本与收益均为相对指数，不是货币量。

### 6.4 MILP

```text
decision: x_g in {0,1}

maximize sum_g (w_B*B_g - w_I*I_g - w_R*R_g - w_C*C_g) * x_g

subject to:
  sum_{g contains cell i} x_g <= 1, for every cell i
  sum_g x_g = 8
```

权重：

| 方案 | `w_B/w_I/w_R/w_C` | 解释状态 |
|---|---|---|
| performance | 0.60/0.15/0.15/0.10 | `[ASSUMED][UPDATEABLE]` 偏收益 |
| balanced | 0.35/0.25/0.25/0.15 | `[ASSUMED][UPDATEABLE]` 均衡 |
| conservative | 0.20/0.25/0.45/0.10 | `[ASSUMED][UPDATEABLE]` 偏风险 |

greedy 使用 balanced 权重，按组分数降序、跳过重复电芯，作为可行启发式对照。

### 6.5 结果

| 指标 | 结果 |
|---|---:|
| 候选电芯 | 108 |
| 通过门槛 | 85 |
| 筛选率 | 0.7870 |
| 兼容候选组 | 3167 |
| 每个 MILP 方案组数 | 8 |
| 每个方案使用电芯 | 32 |
| MILP 重复分配 | 0 |
| 错误组规模 | 0 |

| 方案 | 方法 | 目标值 | 平均收益 | 平均不一致 | 平均风险 | 平均成本 |
|---|---|---:|---:|---:|---:|---:|
| performance | MILP | 2.7419 | 0.6614 | 0.0821 | 0.0363 | 0.3637 |
| balanced | MILP | 1.2048 | 0.6317 | 0.0679 | 0.0449 | 0.2818 |
| conservative | MILP | 0.4929 | 0.6340 | 0.0618 | 0.0440 | 0.2993 |
| balanced greedy | greedy | 1.0828 | 0.5950 | 0.0809 | 0.0489 | 0.2696 |

balanced MILP 与同权重 greedy 的目标差为 `1.2048-1.0828=0.1220`；该差值是当前归一化目标，不是经济收益增幅。

### 6.6 可转入论文的结论原子

- `[RESULT]` 当前假设门槛下，108 颗候选中 85 颗通过，形成 3167 个兼容 4 芯候选组。
- `[RESULT]` 三组权重下的 MILP 均满足 8 组、每组 4 芯、单芯最多使用一次的约束。
- `[RESULT]` balanced 权重下 MILP 目标高于 greedy；不能转换为百分比收益或货币价值。
- `[ASSUMED][UPDATEABLE]` 分级门槛和场景权重必须由实际检测误差、安全规范和应用需求替换。
- `[PAPER_GAP]` 当前没有储能系统电压、功率、能量、串并联拓扑及损耗约束；结论限定为 module-level 兼容编组。

证据：`study_output/q3_candidate_screening.csv`、`study_output/q3_selected_groups.csv`、`study_output/q3_assignments.csv`、`study_output/q3_solution_summary.csv`、`study_output/fig_q3_tradeoff.svg`。

## 7. Q4 技术块：多工况、鲁棒性与弃权

### 7.1 支持域内场景

| 场景 | T | C-rate | DOD | 类型 |
|---|---:|---:|---:|---|
| baseline | 25 degC | 1C | 80% | 支持域 |
| high_temperature | 45 degC | 1C | 80% | 支持域 |
| high_c_rate | 25 degC | 2C | 80% | 支持域 |
| high_dod | 25 degC | 1C | 100% | 支持域 |
| combined_stress | 45 degC | 2C | 100% | 支持域 |

每场景每 seed 24 电芯；seeds=`42,123,2026,4096,8110`。

场景流程：用 Q1/Q2 全因子数据训练的完整 Ridge/AFT 模型评估每个新场景；随后在该场景内重新筛选并求 balanced MILP。场景之间的 `cell_id` 不是 Q3 原始候选的纵向延续。

批次代理：

| 代理 | 参数变化 | 标签 |
|---|---|---|
| low degradation | `alpha*0.9, beta*0.9, R0*0.95` | `[ASSUMED][UPDATEABLE]` |
| reference | 参数不变 | `[ASSUMED][UPDATEABLE]` |
| high degradation | `alpha*1.1, beta*1.1, R0*1.05, sigma_cell*2` | `[ASSUMED][UPDATEABLE]` |

批次代理不是实测批次分布。

### 7.2 Monte Carlo 结果

以下均为 5 seeds 的均值：

| 场景 | cycle=1000 SOH | 临界比例 | Ridge 50-cycle RMSE | 筛选率 |
|---|---:|---:|---:|---:|
| baseline | 0.8541 | 0.0000 | 0.003756 | 1.0000 |
| batch_low_degradation_proxy | 0.8687 | 0.0000 | 0.004218 | 1.0000 |
| batch_reference_proxy | 0.8541 | 0.0000 | 0.003756 | 1.0000 |
| batch_high_degradation_proxy | 0.8391 | 0.0000 | 0.004615 | 1.0000 |
| high_c_rate | 0.8409 | 0.0000 | 0.003876 | 1.0000 |
| high_dod | 0.8069 | 0.1917 | 0.004034 | 1.0000 |
| high_temperature | 0.7833 | 0.9667 | 0.003959 | 0.9167 |
| combined_stress | 0.6857 | 1.0000 | 0.004608 | 0.0000 |

`critical_fraction` 仍使用仿真阈值 `SOH<=0.8`，不能改写为真实安全事故概率。

### 7.3 OAT 灵敏度

参数：`alpha, beta, k_T, k_C, k_D, n_k_EFC, sigma_cell`；每项 `-10%/base/+10%`，其余固定。

跨场景最大绝对归一化响应：

| 参数 | `final_soh_mean` | `resistance_growth_mean` |
|---|---:|---:|
| alpha | 0.462064 | 0.000000 |
| beta | 0.000000 | 0.989315 |
| k_T | 0.184875 | 0.393688 |
| k_C | 0.060269 | 0.128958 |
| k_D | 0.092414 | 0.197403 |
| n_k_EFC | 0.166364 | 0.453379 |
| sigma_cell | 0.005163 | 0.004844 |

这些响应是当前公式的局部机械敏感度，不是参数可辨识性、因果贡献或真实置信区间。

### 7.4 OOD 弃权

| case | 输入 | 输出 | 原因 |
|---|---|---|---|
| low_temperature | 0 degC, 1C, 80%, CC-CV | `numeric_prediction=null` | T 超出 25--50 degC |
| overcharge_protocol | 25 degC, 1C, 80%, CC-CV-overcharge | `null` | 协议不匹配 |
| overdischarge | 25 degC, 1C, DOD=110% | `null` | DOD 超出 50--100% |
| rate_above_support | 25 degC, 3C, 80% | `null` | C-rate 超出 0.5--2C |

### 7.5 工程触发规则

| 条件 | 当前动作 | 状态 |
|---|---|---|
| 支持域内 45 degC 或 2C | 增加检测频率；重新估计 SOH/RUL 后再编组 | `[RESULT][UPDATEABLE]` 仿真条件规则 |
| 任一筛选/不确定性门槛失败 | 不强制编组；转附加检测或其他处置 | `[CONFIRMED]` 决策逻辑 |
| 任一 OOD 标记 | 停止数值预测；要求适用模型或数据 | `[CONFIRMED]` 风险控制 |

### 7.6 可转入论文的结论原子

- `[RESULT]` 支持域内组合压力的 cycle=1000 平均 SOH 最低，筛选率为 0。
- `[RESULT]` 高温场景的临界比例和筛选率变化大于单独高倍率场景；结论仅适用于当前公式和参数。
- `[RESULT]` `alpha/beta/n_k/k_T` 分别主导对应输出的局部敏感度；不能解释成实测机理权重。
- `[OOD/ABSTAIN]` 题面中的低温、过充、过放和 >2C 只报告弃权，不提供寿命扰动数值。
- `[PAPER_GAP]` 当前结果不构成对 Q3 同一已选编组的纵向压力验证；它比较的是各场景重新筛选/编组后的结果。

证据：`study_output/q4_monte_carlo_raw.csv`、`study_output/q4_monte_carlo_summary.csv`、`study_output/q4_sensitivity_oat.csv`、`study_output/q4_sensitivity_rank.csv`、`study_output/q4_ood_abstention.csv`、`study_output/fig_q4_final_soh.svg`、`study_output/fig_q4_sensitivity.svg`。

## 8. 模型评价技术块

### 8.1 可写优点

| 优点 | 证据 |
|---|---|
| 全链可复跑 | 固定配置、seed、命令、源码/产物哈希 |
| 数据泄漏控制 | 5 折 `GroupKFold(cell_id)`，折间重叠为 0 |
| 寿命删失处理 | AFT 对 43 事件 + 65 右删失建模 |
| 优化约束可回算 | 重复电芯 0、错误组规模 0、HiGHS optimal |
| 不确定性显式 | cell-bootstrap CI、AFT 区间、5 seeds、OAT |
| 范围控制 | OOD 输入输出空数值而不是强行外推 |
| 解释性 | 生成方程、因素权重、门槛和目标项均可拆解 |

### 8.2 必须写入的局限

| ID | 局限 | 影响 |
|---|---|---|
| L1 | 全部数据来自同一合成生成器 | 不能证明现实泛化或真实预测精度 |
| L2 | 因素方向和相对强弱写入生成公式 | Q1 权重主要是生成设定的恢复，不是经验发现 |
| L3 | 未读取 CALCE 原始循环数据 | 不存在实测校准和外部验证 |
| L4 | 仅 CC-CV 一个协议水平 | 无法估计充电策略影响 |
| L5 | 支持域不含低温、过充、过放、3C | Q2 极端工况只完成弃权，不完成数值扰动分析 |
| L6 | Q3 RUL 来自 cycle 300 预测并换算到 750 | 不是退役快照处重新拟合的在线预测 |
| L7 | Q3 只有无量纲成本/收益和 4 芯兼容组 | 无货币经济性、系统损耗或串并联阵列设计 |
| L8 | 批次场景是参数代理 | 不能解释为真实制造批次差异 |
| L9 | OAT 是局部单因素扰动 | 不覆盖参数交互、全局敏感度或联合不确定性 |
| L10 | 外部参考文献未完成逐条全文页码核验 | 机理和行业背景主张仍需人工闭环 |
| L11 | AFT 的 log-normal、线性协变量和独立删失假设未在真实数据上检验 | 事件覆盖和误差只说明本合成留组实验 |
| L12 | Q1 报告总体边际主效应；内阻倍率在 1/9 分层有局部反转 | 不得写成所有工况/电芯都严格单调 |
| L13 | Q4 每个场景重新生成、筛选和编组，没有延续 Q3 同一组电芯 | 不得称“已有编组通过长期多工况验证” |

### 8.3 统计解释与 11 类谬误扫描

扫描口径来自 academic-research-suite experiment-agent validate mode；覆盖 `11/11`。当前没有 p 值或显著性检验，所有 CI、权重和 OAT 均按描述性结果解释。

| 类型 | 判定 | 技术处置 |
|---|---|---|
| 1 Simpson's paradox | `CAUTION` | 平衡全因子总体方向已分层复核；内阻倍率 1/9 分层局部反转，正文同时报告总体与例外 |
| 2 Ecological fallacy | `NOT_TRIGGERED` | 不从工况均值推断真实单体或行业规律 |
| 3 Berkson's paradox | `CAUTION` | Q3 对过门槛电芯筛选；筛选后组内关系不外推到全部退役电芯 |
| 4 Collider bias | `CAUTION` | Q3 同时按 SOH、RUL、内阻、不确定性筛选；不对筛选后特征相关性作因果解释 |
| 5 Base-rate neglect | `CONTROLLED` | 85/108 和场景筛选率仅是当前仿真假设分布，不称行业合格率 |
| 6 Regression to mean | `NOT_APPLICABLE` | 无按极端结果选组后的前后改善主张 |
| 7 Survivorship bias | `CAUTION` | RUL 点误差只对 43 个事件；65 个右删失单列，主模型用删失似然 |
| 8 Look-elsewhere effect | `CONTROLLED_EXPLORATORY` | 7 参数 x 5 场景 x 2 输出全部报告；不做选择性显著性主张 |
| 9 Garden of forking paths | `CAUTION` | 配置和 seed 已冻结，但无外部预注册；门槛、权重和模型选择按探索性分析处理 |
| 10 Correlation != causation | `CAUTION` | Q1 因素方向写入生成器；只称仿真主效应，不称真实电化学因果贡献 |
| 11 Reverse causality | `NOT_APPLICABLE` | 当前是前向生成和预测任务；不据此建立真实世界反向因果结论 |

额外统计假设边界：90% cell-bootstrap CI 是预测指标在电芯重采样下的区间，不是模型参数 CI；AFT 90% 覆盖只在 43 个事件上经验评估；OAT 是局部机械敏感度，不是全局不确定性或因果效应。

### 8.4 AI 研究失败模式预审

本节按 academic-research-suite 的 7 类 AI 研究失败模式执行 Stage 2.5 前预审。它核对技术产物与运行证据，不等于论文已通过引用、原创性和主张完整性审查。

| 模式 | 判定 | 当前证据 | 论文/下一步处置 |
|---|---|---|---|
| 1 实现缺陷通过自审 | `CLEAR_WITHIN_CURRENT_SCOPE` | 56 项测试、9 个自动闸门、连续两次确定性重跑、43/43 产物哈希一致；关键公式已与 `q1.py`--`q4.py` 对照 | 仍保留独立代码红队风险；代码或配置改变后判定失效 |
| 2 虚构或错配引用 | `INSUFFICIENT_EVIDENCE` | 最新 DOCX 有 33 个 `EVIDENCE REQUIRED`；候选 DOI 尚未逐条核验全文、页码和主张范围 | `BLOCKING_FOR_STAGE_2_5`；人工核验或删除对应主张 |
| 3 虚构实验结果 | `CLEAR_WITHIN_CURRENT_SCOPE` | C05--C24 数字均回指保存的 CSV/JSON；manifest 可回算且双跑一致 | 新增或改写数字时重新核对，不允许从聊天或摘要反推 |
| 4 依赖捷径而非预期泛化 | `INSUFFICIENT_EVIDENCE` | 生成、训练和验证均来自同一仿真家族；structure-matched 模型已隔离为 ceiling，但没有真实外部集或去捷径消融 | 只支持“仿真内比较”；Stage 4.5 前需外部证据或继续保持限制性结论 |
| 5 将缺陷包装为新发现 | `CLEAR_WITHIN_CURRENT_SCOPE` | 没有使用“意外/反常/新机理”叙事；内阻倍率 1/9 分层反转明确归因于个体随机效应，并按限制报告 | 不得把局部反转升级为电化学新发现 |
| 6 方法描述与实际运行不一致 | `CLEAR_WITHIN_CURRENT_SCOPE` | seed、折分、模型、门槛、求解器、场景和 OOD 规则均可在配置/代码/结果中对照；DOCX 冲突句已列为 `P0_REPLACE` | 论文方法段逐项从本包填充；不得沿用模板中的 CALCE/NASA/范围外旧表述 |
| 7 早期框架锁定 | `SUSPECTED` | 合成单协议主线使 Q1 协议不可辨识、Q2 极端工况无数值、Q3 无系统拓扑、Q4 非同组纵向验证 | `BLOCKING_FOR_STAGE_2_5`；总负责人必须选择补做，或以题面覆盖不足为限制并记录接受理由 |

预审总判定：`READY_FOR_DRAFT_WITH_LIMITATIONS`，但 `NOT_READY_FOR_STAGE_2_5_PASS`。Mode 2 和 Mode 7 未闭环；Mode 4 只能以范围限制暂时控制。该结论不阻止论文手按现有证据起草方法和仿真结果，但禁止把草稿状态写成最终完整题解。

### 8.5 改进接口

| 取得的新输入 | 修改位置 | 必须重跑 |
|---|---|---|
| CALCE/企业原始循环数据 | 参数估计、真实/仿真分层、外部测试集 | G1-G4 全量 |
| 多协议数据 | `factorial.protocol` 与 Q1 因素分解 | Q1-G4 |
| 真实检测误差/安全规范 | Q3 硬门槛和不确定性门槛 | Q3-Q4 |
| 场景功率/电压/容量需求 | 新增串并联拓扑和能量/功率约束 | Q3-Q4 |
| 成本、损耗、收益数据 | 替换无量纲 cost/benefit | Q3-Q4 |
| 低温/过充/过放/3C 数据 | 扩展支持域并重新训练 | Q1-Q4 |
| 真实批次标签 | 分层随机效应/批次固定效应 | Q1-Q4 |

## 9. 结论技术块

| 问题 | 支持的结论 | 必带限制 |
|---|---|---|
| Q1 | 当前全因子仿真中 DOD 主效应最高，温度次之，倍率最低；72 膝点可检测、36 右删失 | 生成器内部恢复；协议不可辨识；内阻倍率 1/9 分层局部反转；非普适机理排序 |
| Q2 | Ridge 的 50-cycle SOH 留组 RMSE=0.004206；AFT 的事件 RUL RMSE=38.39 cycles、覆盖=0.9070 | 合成数据；AFT 点误差不是最低；无真实外部验证 |
| Q3 | 85/108 过门槛，3167 候选组，三套 MILP 均满足约束，balanced 目标高于 greedy | 门槛/权重/成本收益均为假设；仅 module-level |
| Q4 | 支持域内组合压力退化最强；5 seeds 和 7 参数 OAT 已执行；4 类 OOD 全弃权 | 场景内重新筛选/编组，不是 Q3 同组纵向验证；批次为代理；OAT 局部 |

全文总限制：当前研究证明的是“合成仿真链可运行、可复现、可比较、可约束”，不是“真实电池模型已校准并验证”。

## 10. 主张-证据矩阵

| ID | 主张原子 | 标签 | 精确回指 | 禁止扩展 |
|---|---|---|---|---|
| C01 | 题面不提供原始实测数据，要求自主构建仿真 | `[CONFIRMED]` | `试题  A.pdf` | 不写成题面提供了参数 |
| C02 | 数据为 27 工况、108 电芯、108000 行 | `[CONFIRMED]` | `study_output/factorial_generation_meta.json` | 不写成实测样本量 |
| C03 | 退化模型为分段平方根 + 工况修正 + 个体差异 + 噪声 | `[CONFIRMED]` 实现结构 | `degradation.py`、`g1_smoke.json` | 不写完整电化学机理 |
| C04 | 参数未由 CALCE 原始数据拟合 | `[CONFIRMED]` | `A1_simulation_package.md` | 不写 CALCE 校准成功 |
| C05 | 72 膝点可检测、36 右删失、误差中位数 13.40 EFC | `[RESULT]` | `study_output/q1_summary.json:knee_detection` | 不写外部膝点精度 |
| C06 | 容量主效应权重 T/C/DOD=0.2378/0.0373/0.7249 | `[RESULT]` | `study_output/q1_factor_effects.csv` | 不写真实因果权重 |
| C07 | 内阻主效应权重 T/C/DOD=0.2346/0.0337/0.7317 | `[RESULT]` | 同上 | 同上 |
| C08 | CC-CV 协议效应不可辨识 | `[CONFIRMED]` | `study_output/q1_summary.json:protocol_identifiability` | 不给协议权重 |
| C09 | 5 折按 cell 留组，重叠为 0 | `[CONFIRMED]` | `study_output/q2_split_audit.json` | 不写随机行划分 |
| C10 | Ridge 50-cycle SOH RMSE=0.004206 | `[RESULT]` | `study_output/q2_soh_metrics.csv:model=ridge` | 不写实车精度 |
| C11 | Ridge RMSE 90% CI=0.003962--0.004447 | `[RESULT]` | 同上 | 不写参数置信区间 |
| C12 | RUL 为 43 事件 + 65 右删失 | `[CONFIRMED]` | `study_output/q2_summary.json:rul_endpoint` | 不把删失下界当真值 |
| C13 | AFT 事件 RMSE=38.39、覆盖=0.9070、删失矛盾率=0 | `[RESULT]` | `study_output/q2_rul_metrics.csv` | 不写 AFT 点误差最低 |
| C14 | structure-matched RMSE=11.89 | `[RESULT]` simulator ceiling | 同上 | 不用于泛化结论 |
| C15 | 85/108 通过 Q3 假设门槛 | `[RESULT][UPDATEABLE]` | `study_output/q3_summary.json` | 不写行业合格率 |
| C16 | 3167 个候选组，MILP 选 8 组，重复=0 | `[RESULT]` | `study_output/q3_solution_summary.csv` | 不写完整储能阵列 |
| C17 | balanced MILP=1.2048，greedy=1.0828 | `[RESULT]` | 同上 | 不写 12.20% 经济增益 |
| C18 | Q4 使用 5 seeds、7 参数 OAT | `[CONFIRMED]` | `study_output/q4_summary.json` | 不写全局敏感度 |
| C19 | combined stress SOH=0.6857、筛选率=0 | `[RESULT]` | `study_output/q4_monte_carlo_summary.csv` | 不外推范围外工况 |
| C20 | 低温/过充/过放/3C 数值为空 | `[OOD/ABSTAIN]` | `study_output/q4_ood_abstention.csv` | 不补造趋势数字 |
| C21 | 门槛、权重、成本收益为假设 | `[ASSUMED][UPDATEABLE]` | `configs/study_pipeline.json`、`study_output/q3_summary.json` | 不写规范/货币值 |
| C22 | 真实泛化、安全概率、货币收益未知 | `[UNCERTAIN]` | `run_manifest.json:uncertainty_status` | 不用模型内部结果替代 |
| C23 | 内阻倍率效应在 1/9 分层局部反转；总体边际排序不等于逐层单调 | `[RESULT]` | `factorial_cell_summary.csv` + 分层方向复核 | 不写所有工况严格单调 |
| C24 | Q4 在各场景重新生成、筛选和优化，未纵向复用 Q3 同组电芯 | `[CONFIRMED][PAPER_GAP]` | `code/battery_study/q4.py:_scenario_metrics` | 不写已有编组已通过压力验证 |

## 11. 图表与表格接口

### 11.1 图

| Bridge ID | 文件 | 正文用途 | 图注必须包含 |
|---|---|---|---|
| FIG-00 | DOCX 现有总流程图 | 四问数据流 | “题面-仿真-预测-筛选-鲁棒性” |
| FIG-Q1 | `study_output/fig_q1_factor_weights.svg` | Q1 主效应权重 | 合成全因子；仅三个可辨识主效应内归一化 |
| FIG-Q2A | `study_output/fig_q2_soh_rmse.svg` | 50-cycle SOH 模型比较 | GroupKFold(cell_id)；RMSE；合成数据 |
| FIG-Q2B | `study_output/fig_q2_rul_rmse.svg` | RUL 事件点误差 | 只对 43 个事件计算；删失样本未进入点误差 |
| FIG-Q3 | `study_output/fig_q3_tradeoff.svg` | 四方案收益-一致性权衡 | 无量纲归一化；权重可更新 |
| FIG-Q4A | `study_output/fig_q4_final_soh.svg` | 多工况末期 SOH | 5 seeds 均值；支持域内 |
| FIG-Q4B | `study_output/fig_q4_sensitivity.svg` | OAT 局部敏感度 | +/-10%；局部；非因果权重 |

`g1_output/*.svg` 可用于说明生成器合理性，不与 `study_output/*.svg` 的正式结果图混用。

### 11.2 表

| 建议表 | 数据来源 | 放置位置 |
|---|---|---|
| 参数与标签表 | `configs/g1_smoke.json` + `parameter_ledger.txt` | 数据生成方法 |
| Q1 因素权重表 | `study_output/q1_factor_effects.csv` | Q1 结果 |
| Q2 SOH 模型表 | `study_output/q2_soh_metrics.csv` | Q2 结果 |
| Q2 RUL 模型表 | `study_output/q2_rul_metrics.csv` | Q2 结果 |
| Q3 门槛/权重表 | `study_pipeline.json` | Q3 方法 |
| Q3 解汇总表 | `study_output/q3_solution_summary.csv` | Q3 结果 |
| Q4 场景表 | `study_output/q4_monte_carlo_summary.csv` | Q4 结果 |
| OOD 弃权表 | `study_output/q4_ood_abstention.csv` | Q4 局限 |

图号由在线文档最终固定；Bridge ID 不等于最终论文图号。

## 12. 引用与外部证据状态

| 材料 | 当前可用范围 | 状态 |
|---|---|---|
| 题面 PDF | 问题背景、四问要求、无原始实测数据 | 可直接回指题面 |
| CALCE 数据入口 | 数据库存在、NMC 对象/尺度参考 | 不支持“已下载/拟合/校准” |
| NASA 数据入口 | 候选外部来源存在 | 未进入当前实验；正文不写已对照 |
| `source_ledger.txt` 的论文 DOI | 候选机理/方法/梯次利用来源 | `[EVIDENCE_REQUIRED]` 全文、页码、主张范围待人工核验 |

正式参考文献进入论文前，每条必须记录：

```text
citation_id | DOI/官方URL | 作者/年份/题名 | 正文主张 | 原文页码/表号
核验人 | 核验日期 | VERIFIED / NOT_FOUND / MISMATCH
```

当前 DOCX 的 33 个 `EVIDENCE REQUIRED` 不得整体删除；只能逐条核验、降级为假设或删除对应主张。

## 13. 标题与摘要要素

本节只给信息槽，不给成稿。

### 13.1 标题要素

```text
对象：退役 NMC 锂电池
方法链：半机理随机退化仿真 + 留组 SOH/RUL + 删失 AFT + 风险约束 MILP
任务：剩余寿命预测与梯次编组
限制：不在标题中写 CALCE 校准、实测验证、真实最优
```

### 13.2 摘要要素

| 槽位 | 必填技术内容 |
|---|---|
| 背景/问题 | 题面无实测数据；需完成退化、预测、筛选编组、鲁棒性四问 |
| 数据 | 27 工况、108 电芯、108000 行合成仿真；支持域和 seed |
| Q1 方法/结果 | hinge 膝点 + 主效应分解；72/36；T/C/DOD 权重 |
| Q2 方法/结果 | GroupKFold；Ridge SOH；删失 AFT RUL；关键误差与覆盖 |
| Q3 方法/结果 | 硬门槛 + 兼容组 + set-packing MILP；85/108、3167、8 组 |
| Q4 方法/结果 | 5 seeds + 7 参数 OAT + OOD；组合压力和弃权 |
| 总限制 | 全部为合成仿真；无 CALCE 拟合、外部验证、真实经济/安全结论 |

关键词候选：`退役动力锂电池`、`SOH`、`右删失 RUL`、`混合整数线性规划`、`鲁棒性分析`。

## 14. 附录与支撑材料接口

删除 DOCX 中：

- `XXX`、模板教学说明、通用二次方程示例。
- “这里插入公式”占位表。
- 文本情感分析参考文献。
- jieba 诗词词频代码。
- MATLAB AHP 示例代码。
- “附录某某语言/作用是什么”占位说明。

替换为：

| 附录 | 内容 | 路径 |
|---|---|---|
| A | 参数、支持域、seed、阈值、权重 | `configs/*.json`、`evidence/parameter_ledger.txt` |
| B | 数据字典与仿真协议 | `g1_output/data_dictionary.md`、`docs/Simulation_Protocol.md` |
| C | Q1-Q4 关键算法伪代码 | `code/battery_study/q1.py`--`q4.py` |
| D | 完整结果表 | `study_output/*.csv`、`*.json` |
| E | 验证闸门和运行清单 | `validation_gates.json`、`run_manifest.json` |
| F | 复跑说明 | `technical/SUPPORTING_MATERIALS_README.md` |

最小复跑：

```bash
python -m pip install -r requirements-study.txt
PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output
python -m pytest code/tests -q
git diff --check
```

## 15. 更新注册表

| ID | 当前状态 | 触发条件 | 更新动作 | 影响章节 |
|---|---|---|---|---|
| U01 | CALCE 未拟合 | 获得匹配原始数据 | 新建真实数据层，重估参数，全量重跑 | 全文 |
| U02 | NASA 未使用 | 完成化学体系/协议核验并决定加入 | 建立独立外部对照，不合并混杂体系 | Q1/Q2/Q4 |
| U03 | 80% SOH 自设终点 | 获得规范/题目定义 | 改配置并全量重跑 | Q1-Q4 |
| U04 | Q3 门槛/权重自设 | 获得检测/规范/场景数据 | 改 JSON，重跑 Q3-Q4 | Q3/Q4 |
| U05 | 无系统拓扑 | 获得电压/功率/能量需求 | 增加串并联与损耗约束 | Q3/Q4 |
| U06 | OOD 极端工况 | 获得匹配数据 | 扩域、重训、重新验证 | Q2/Q4 |
| U07 | 引用待全文核验 | 人工取得原文 | 填页码/表号，保留或删除主张 | 背景/假设/讨论 |
| U08 | 评分细则缺失 | 官方发布 | 只调整呈现优先级；模型变更需重开闸门 | 全文 |
| U09 | Q4 未纵向验证 Q3 同组电芯 | 决定扩展技术范围并定义工况迁移规则 | 固定 Q3 分组，跨场景演化同一电芯并回算组内离散/损耗/可行性 | Q3/Q4 |

## 16. 论文手验收条件

- [ ] DOCX/在线文档中的每个结果数字均在 C01--C24 或结果文件中有回指。
- [ ] 每个 Q 都包含输入、假设、模型、实验、指标、结果、限制。
- [ ] CALCE/NASA 表述符合第 3.1 节，不出现实测校准/已对照。
- [ ] Q2 明确 `GroupKFold(cell_id)`、右删失、AFT 与 ceiling 边界。
- [ ] Q3 明确门槛/权重/成本收益可更新，并限定 module-level。
- [ ] Q4 明确 5 seeds、OAT 局部性、批次代理和 OOD 弃权。
- [ ] Q4 不把场景内重新筛选/编组写成 Q3 同组电芯的纵向压力验证。
- [ ] 图注包含数据类型、工况/seed/折分、指标和限制。
- [ ] 参考文献逐条完成人工全文核验；无孤立引用或孤立文献。
- [ ] 删除所有模板示例、`XXX`、无关代码和无关参考文献。
- [ ] 最终摘要、正文、图表和结论数字一致。
