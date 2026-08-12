# V2 真实 NMC 数据候选验证报告

状态：`CANDIDATE_REAL_DATA / NEEDS_CHANGES / HOLD_FOR_PAPER`
运行日期：2026-08-12
来源：Zenodo `10.5281/zenodo.7250553`，CC BY 4.0

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Verification Status: `ANALYZED`
- Version Label: `v2_nmc_candidate_validation_v1`
- Reproducibility: `REPRODUCIBLE`；原始口径与 period=50 回顾性敏感性各在两个全新目录复跑，16/16 验证输出文件逐字节一致。准备层的内容输出也在两个新目录复跑一致；`provenance.json` 含运行者绝对路径，哈希仅作单次运行记录。

## 1. 结论先行

这批数据已经完成无损解析、逐电芯质量审计和分层 Q1/Q2 候选分析，但区间保证口径与 RPT 膝点预处理仍未通过论文闸门。当前只作为**真实数据候选分析层**，不替换 V1 合成主线，也不改写 `论文草稿.md` 的结果表。

允许写入技术过渡层的表述是：

> 在独立公开的 NMC/Graphite 逐循环容量数据上，按 NMC532 与 NMC811 分层，并以 `cell_id` 做 GroupKFold 和工况留出。在当前 30-cycle 预测窗、每芯前最多 10 个观测归一化、容量单位未确认的条件下，NMC811 的 Ridge RMSE 低于 persistence，而 NMC532 的 Ridge RMSE 略高于 persistence。结果表明模型收益依赖化学体系和数据分层，不能用单一平均精度代替来源特定验证；该结果不是 CALCE 校准、跨化学体系泛化或绝对容量精度证明。

暂不允许写：实测 CALCE 校准、真实安全概率、绝对容量误差、跨 NMC532/NMC811 的统一退化参数、Q3 编组验证或 Q4 压力结论。

## 2. 数据质量闸门

| 项目 | 结果 | 标签 |
|---|---:|---|
| 容量文件 | 44 | `[CONFIRMED]` |
| 电芯 | 44（NMC532=26，NMC811=18） | `[CONFIRMED]` |
| 容量观测行 | 24,525 | `[CONFIRMED]` |
| summary 对齐 | 44/44 | `[CONFIRMED]` |
| 循环断裂 | 0 | `[CONFIRMED]` |
| summary EOL 不一致 | 0 | `[CONFIRMED]` |
| 缺失/非正容量 | 0 | `[CONFIRMED]` |
| 协议 | 全部 CC-CV，只有一个水平 | `[CONFIRMED]` |
| 容量单位 | `UNVERIFIED`，保留原始数值 | `[UNCERTAIN]` |
| 温度、DOD、EFC、内阻 | 当前输入缺失 | `[OOD/ABSTAIN]` |

原始文件不进 Git。准备层输出目录由运行者指定；其 provenance、质量报告和输入文件 SHA-256 由 `technical/prepare_nmc_modes.py` 生成。

Zenodo 官方 API 核对：记录创建于 `2022-10-26T03:17:13Z`、更新于 `2022-10-26T14:26:18Z`；`Battery raw data.zip`、`Pouch cell_summary.xlsx`、`README.txt` 的官方 MD5 分别为 `a0ee7ee69285f23489e1f02b66114bc5`、`5730d75ec215f751c6b1f6911422e787`、`c5c9455a196f407b5e7413a1c6ad8c59`，与本地输入一致。官方仓库代码把容量列直接读取为 `capacity`，图轴出现 `mA-h`，但没有给出足以消除歧义的字段单位契约，因此本包仍保持 `capacity_unit=UNVERIFIED`。

## 3. 分层验证配置

- 输入：`canonical_capacity.csv`，按 `chemistry` 分成 NMC532/NMC811；禁止混合拟合同一退化参数。
- 归一化：每芯前最多 10 个容量观测的中位数；这是相对容量，不是 Ah/mAh。
- 特征：当前归一化容量、最近 30-cycle Theil-Sen 斜率、当前 cycle、可用 C-rate。
- 目标：未来 30-cycle 的归一化容量。
- 外层：5 折 `GroupKFold(cell_id)`；另做完整 `condition_id` 留出。
- 不确定性：训练电芯校准的描述性残差包络，以及 100 次电芯 bootstrap。NMC532 每折 6--7 个、NMC811 每折 4--5 个校准电芯，不构成名义 90% 的电芯级有限样本保证。
- 反捷径：训练标签置乱 sanity check；训练/测试电芯交集必须为 0。

上述 30/30/5/100 是本次候选验证设计，属于 `[UPDATEABLE]`，不能伪装成题面或行业标准。

## 4. 验证结果：原始口径

| 化学体系 | 电芯 | 样本行 | Persistence RMSE | Ridge RMSE | Ridge 相对变化 | Ridge RMSE 90% cell-bootstrap CI | 逐行覆盖 | 整芯同时覆盖 | 平均宽度 | LOCO RMSE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| NMC532 | 26 | 13,166 | 0.016107 | 0.017227 | +6.95%（较差） | 0.011073--0.023106 | 0.9865 | 23/26 = 0.8846 | 0.2835 | 0.015828 |
| NMC811 | 18 | 8,763 | 0.004555 | 0.002865 | -37.11%（较好） | 0.001995--0.003605 | 0.9965 | 15/18 = 0.8333 | 0.0508 | 0.002813 |

解释边界：指标针对归一化容量，不能换写成 Ah、mAh 或车辆 RUL 精度。NMC532 不支持“Ridge 普遍优于简单基线”的主张，且一个高倍率工况误差明显偏高；这些反例保留在逐工况 CSV 中，不删除、不跨体系平均掩盖。逐行覆盖的独立单位不是预测行，且整芯同时覆盖低于 0.90；加之每折校准芯数很少，以上区间只能称“描述性残差包络”，不能称 90% 电芯级保证。两层的标签置乱 sanity 均通过，训练/测试电芯交集均为 0。

## 4.1 period=50 回顾性敏感性

按来源代码 `seasonal_decompose(period=50).trend` 生成第二口径；双侧趋势使用未来观测，故仍为 `paper_eligible=false`，只用于敏感性，不替代在线无泄漏预处理。

| 化学体系 | 电芯 | 样本行 | Persistence RMSE | Ridge RMSE | Ridge 相对变化 | Ridge RMSE 90% cell-bootstrap CI | 逐行覆盖 | 整芯同时覆盖 | 平均宽度 | LOCO RMSE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| NMC532 | 26 | 13,166 | 0.009211 | 0.005267 | -42.82%（较好） | 0.004437--0.005872 | 0.9977 | 23/26 = 0.8846 | 0.0726 | 0.005286 |
| NMC811 | 18 | 8,763 | 0.004065 | 0.001486 | -63.45%（较好） | 0.000901--0.002051 | 0.9344 | 15/18 = 0.8333 | 0.0127 | 0.001572 |

原始与回顾性口径方向不一致（NMC532 的原始 Ridge 较 persistence 差，去趋势后较好），因此任何 Q2 headline 均标记 `HOLD_RPT_SENSITIVITY`，不得选择性引用单一口径。

Q1 膝点状态：`HOLD_RPT_UNPROCESSED / paper_eligible=false`。原始容量含 RPT 尖峰，来源代码采用约 50-cycle 周期去趋势；当前候选层尚未实现并验证来源一致预处理，因此撤下上一版所有精确膝点计数，不得进入论文。

可辨识因素：NMC811 的 C-rate 有 5 个水平，在所有电芯共同观测到的 cycle=425 比较，报告为 `PASS_DESCRIPTIVE` 且 `causal=false`；NMC532 的当前每水平 replication 闸门未通过。温度、DOD 和协议效应均 `ABSTAIN`。

## 5. 统计完整性审计

整体信心：`CAUTION`。11/11 类统计谬误已检查：

| 检查 | 判定 | 处置 |
|---|---|---|
| Simpson's paradox | CAUTION | 不合并 NMC532/NMC811；分别报告正反结果，避免总体均值掩盖分层方向 |
| Ecological fallacy | CAUTION | 不从 pack 或倍率组均值推断任一单芯因果效应 |
| Berkson's paradox | NOTE | 数据集来自特定老化实验设计的选定样本，不能代表所有 NMC 电芯 |
| Collider bias | NOTE | 当前未加入可能同时受工况和退化影响的控制变量作因果回归 |
| Base-rate neglect | N/A | 本轮不是安全筛查/分类，不报告敏感度或阳性预测值 |
| Regression to mean | NOTE | 未按极端 SOH 选组比较改善；每芯用固定早期窗口归一化 |
| Survivorship bias | CAUTION | 44 个来源电芯全部保留；未处理 RPT 前不发布膝点分类或计数 |
| Look-elsewhere | CAUTION | 温度、DOD、协议缺证据即弃权；完整报告 Ridge 胜出和未胜出体系，不选择性报告 |
| Garden of forking paths | CAUTION | 30-cycle 窗口和 100 次 bootstrap 属 `[UPDATEABLE]`；尚无预注册或多窗口稳健性，hinge 结果已撤下 |
| Correlation != causation | CAUTION | C-rate 只标 `PASS_DESCRIPTIVE, causal=false`，禁止写“倍率导致” |
| Reverse causality | NOTE | 预测使用时间先行历史窗口，但倍率关联仍可能被 pack/design 混杂 |

本轮没有 p-value 或多重显著性检验，不使用“统计显著”措辞。bootstrap CI 描述跨电芯重采样的不确定性；不能用行数 13,166/8,763 代替独立样本量，独立单位仍是 26/18 个电芯。

确定性复现：用相同输入、代码、seed 和参数在两个全新目录独立运行；两个化学体系的 `report.json`、`predictions.csv`、`metrics_by_cell.csv`、`metrics_by_condition.csv` 共 8 个文件逐字节一致。

准备层已在两个新的临时目录独立复跑；`canonical_capacity.csv`、按化学体系拆分的两个 CSV、`cell_metadata.csv` 和 `quality_report.json` 的 SHA-256 均逐项一致。`provenance.json` 含输入绝对路径，因此不纳入跨目录内容一致性判断。

## 6. 证据文件与哈希

以下是当前运行逻辑产物名与 SHA-256；原始数据和派生大文件不纳入 Git。原始口径与 period=50 口径各 8 个产物均已独立复跑逐字节一致：

```text
prepared/canonical_capacity.csv
153a678b65392363c6d9685c4e0a2fe69fa8ec5ceec77a24d59cf5269219e836
prepared/canonical_capacity_NMC532.csv
ccce53ee6b74377e963dc38aa7c0e3c6155d8817f4ca6d62dc17467c4fd3979e
prepared/canonical_capacity_NMC811.csv
cdb0ab48c707798515bb2c6ae178a9fe89b17647862d7a59622b07874704f0e4
prepared/cell_metadata.csv
e6b08541989bafb594b70b998e23ecfb36369e005e5de79adc5a251f4313f44b
prepared/quality_report.json
1e0f75ff1d5cf87a56b191fe7e0935464e9aca84fc0a687e533ec52a018b7248
prepared/provenance.json  # 参考运行哈希；含绝对路径，换运行目录后会变化
af75c6520232f7855a0d2d0a58fcbd32f57c5145f5a14d61817ce725af43b1d6
raw/NMC532/report.json
ca46cc617ce450462505b771f86059ea94fcd2952d987a59972fd31a335a8d6c
raw/NMC532/predictions.csv
d560b7a2d40faa6171134428143ca9e5c0eaf3a2c1d3d07c4852aea4a8f4229f
raw/NMC532/metrics_by_cell.csv
7a6f004f31745f4414b3d09981f6fd7490554726901db0a1e86a978b0263d8ea
raw/NMC532/metrics_by_condition.csv
c030219c08305177a12df5085cb663437b5030cd9a698305dc87265f4542c3fb
raw/NMC811/report.json
eeda578b8af5d6025cb2f7bece305d99486fe27d63faa88c1b7fd0d54ee06c8f
raw/NMC811/predictions.csv
c99690feae064e67a7185c1b6bb14220577a1a72784b114b34bcb3882b5ec687
raw/NMC811/metrics_by_cell.csv
26ac8d24fdf4ece01b74b9db40d8d4c43f9fe964dbd8509aea6c822f930af295
raw/NMC811/metrics_by_condition.csv
74f9a552bb1cc1544a141bfdccf90c3ce8167228744b9fbb9bdcbda52e6e3886
rpt50/NMC532/report.json
204b398fd8de593867be141a28eb8e29d21e4cd781913b6ce5fa807c89b417ba
rpt50/NMC532/predictions.csv
adbd25ce326ec92cce07cc147a2dd530f666ab5234747c358587c33736007b0d
rpt50/NMC532/metrics_by_cell.csv
996f7e746cffda8620877d5dd5b0769fa1ecfbc7d45ef7a1917cccce32c63263
rpt50/NMC532/metrics_by_condition.csv
6482d112af9447b31d506434fb87b9ef332429d65dd1dd2a9bc9a51a13b06b19
rpt50/NMC811/report.json
89eb8d5576656c7b6052c812c7694ae2524ebbfb1640297bd757fc15d26d289f
rpt50/NMC811/predictions.csv
96629b31af32b391a571889d24024d8fe349a2d0b0bda2be994c4675b63cf180
rpt50/NMC811/metrics_by_cell.csv
712105df8da917d521c58d100940572b371d10a362e67837e25cc1d009f92e40
rpt50/NMC811/metrics_by_condition.csv
5a659ecb4cc99ee7439a512927a8f44e14c9513910de5d53b73894180d485386
```

复跑：

```bash
conda run -n normal python technical/prepare_nmc_modes.py \
  --raw-root "/path/to/Battery raw data" \
  --summary "/path/to/Pouch cell_summary.xlsx" \
  --raw-zip "/path/to/Battery raw data.zip" \
  --readme "/path/to/README.txt" \
  --out-dir /tmp/nmc_modes_prepared

PYTHONPATH=code python -m battery_real.cli \
  /tmp/nmc_modes_prepared/canonical_capacity_NMC532.csv \
  --out /tmp/nmc_validation/nmc532 \
  --history-window 30 --horizon 30 --splits 5 \
  --bootstrap-reps 100 --leave-condition-out
```

NMC811 仅把输入改为 `canonical_capacity_NMC811.csv` 并替换输出目录。验证器运行使用具备 `numpy/scipy/sklearn` 的 Python 环境；解析器使用具备 `pandas/openpyxl` 的 `normal` 环境。

## 7. 放行闸门

当前判定：`NEEDS_CHANGES / HOLD_FOR_PAPER`。

放行进入论文前还需：

1. 完成来源一致的 RPT 预处理和敏感性审计，或继续永久撤下 V2 膝点结果。
2. 重新运行当前验证代码，在报告中保留逐行覆盖、整芯同时覆盖、每折校准芯数和 `finite_sample_guarantee=false`。
3. 将结果与 provenance 固化为 V2 证据包，并由总负责人重新审阅；不能只复制数字。
4. V1 Q3/Q4 数字继续保持原样；V2 不覆盖编组和压力场景。
