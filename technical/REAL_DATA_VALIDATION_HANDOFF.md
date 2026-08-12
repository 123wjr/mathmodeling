# V2 真实数据验证技术交接

> 状态：`CANDIDATE_NON_MAINLINE`。本包只在隔离分支开发，未替换 V1。
> 目标：为真实电池循环数据提供可复跑的 Q1/Q2 证据接口。Zenodo NMC 数据已用于候选分析，但未获论文放行；原始文件不入库。

## 1. 与 V1 的证据增益

| 层 | V1 当前能力 | V2 增益（接入真实数据后才生效） |
|---|---|---|
| 数据 | 公开机理方向 + 可复现 NMC 合成时序 | `source_id`、版本、化学体系和逐电芯实测记录可追溯 |
| Q1 | 合成生成器内的阶段/因素恢复检查 | 实测归一化容量趋势、可辨识因素的描述性验证；膝点待来源一致 RPT 预处理 |
| Q2 | 同一仿真家族内按电芯留组比较 | 独立来源逐电芯 GroupKFold/LOCO，透明基线与 Ridge 对照 |
| 不确定性 | 仿真内 cell-bootstrap/AFT 区间 | 训练电芯校准的描述性残差包络 + 按电芯 bootstrap CI |
| 诚信 | V1 输出标记为合成、非外部验证 | 程序化泄漏审计、label-shuffle sanity check、ABSTAIN 闸门 |

V2 不会把 V1 的仿真数字“校准”为实测数字；两套结果必须分开报告。只有在真实来源完成字段映射、化学体系核验、许可记录、文件 SHA-256 和独立复跑后，才能在论文中称“真实数据验证”。

## 2. Canonical CSV 输入契约

必需字段：

```text
source_id, chemistry, cell_id, cycle, capacity
```

可选字段：

```text
efc, resistance, temperature, c_rate, dod, protocol, condition_id
```

约束：

1. `source_id`、`chemistry`、`cell_id` 非空；一次运行只能有一个 `chemistry` 标签。不同化学体系必须分开运行，禁止字符串拼接后合并。
2. `(source_id, cell_id, cycle)` 不得重复；每个电芯的 cycle 必须严格递增正整数。
3. `capacity` 必须有限且为正；`efc`、`resistance`、`c_rate`（若存在）为有限正数；`dod` 在 `(0,100]`。
4. 本包不猜单位、不做额定容量换算。容量先按每芯前最多 10 个观测的中位数归一化：

   `capacity_norm(i,t) = capacity(i,t) / median(capacity(i,1:min(10,n_i)))`。

5. `condition_id` 用于 LOCO；若缺失、不恒定或少于两个水平，LOCO 返回 `ABSTAIN`。
6. V2 适配器写入 `condition_fields=pack_id,chemistry,design,c_rate,protocol` 与 RPT provenance；当前原始口径为 `RAW_UNPROCESSED`，回顾性敏感性口径为 `SOURCE_PERIOD50_RETROSPECTIVE`。

建议 source adapter 在仓库外完成原始文件解析，然后只输出上述 CSV，并同时保存原始 URL/DOI、版本、下载日期、许可、原始文件 SHA-256、字段单位和筛选规则。

## 3. Q1 协议

每芯以 `efc` 为老化横轴；缺失时退回 cycle，并在报告中保留该事实。Theil-Sen 斜率用于稳健净退化趋势。候选膝点原拟采用连续 hinge 模型

`q(t) = a + b x + c max(0, x - k)`

上枚举候选 `k`，但当前 Zenodo 原始容量含 RPT 尖峰且尚未完成来源一致去趋势，因此报告强制输出 `HOLD_RPT_UNPROCESSED`、`paper_eligible=false`，不发布精确膝点或分类计数。完成独立预处理与敏感性审计前，本段模型仅保留为未放行接口。

可选因素只有在字段完整、每个电芯内恒定、至少两个水平且每水平至少 2 芯时，才在所有电芯共同观测到的最大 cycle 比较边际均值/效应范围；结果是 `PASS_DESCRIPTIVE` 且 `causal=false`。否则为 `ABSTAIN`。一个水平的协议（例如全是 CC-CV）不生成协议权重。

## 4. Q2 协议与公式

在 landmark `t` 构造历史特征，只读取 `cycle <= t`：当前归一化容量、最近窗口 Theil-Sen 斜率、当前 cycle，以及完整可用的温度/倍率/DOD。目标是 `t+h` 的归一化容量。比较：

- persistence：`q_hat(t+h)=q(t)`；
- local-linear：`q_hat(t+h)=q(t)+h * slope_recent`；
- Ridge：标准化特征后 `L2` 正则线性模型（`alpha=1`，无调参搜索）。

外层使用 `GroupKFold(cell_id)`；每折保存 train/test cell 清单并断言交集为空。LOCO 按完整 `condition_id` 留出，同样断言 cell 不重叠。训练集内部再按电芯分为 proper-train/calibration cells；每个校准电芯先取最大绝对残差，再按目标 0.90 分位取训练电芯残差半径，得到描述性包络

`[q_hat-r, q_hat+r]`。

当前两层每折仅有 4--7 个校准电芯，无法支持名义 90% 的电芯级有限样本保证。报告必须写 `status=WARN`、`coverage_unit=prediction_row`、`row_coverage`、`whole_cell_simultaneous_coverage`、`calibration_cells_per_fold` 和 `finite_sample_guarantee=false`；不得简称“90% 预测区间”。同时报告 `MAE`、`RMSE`，在真值方差非零时报告 `R2`；每芯和每工况分别报告 Ridge 指标，不能只给行级总体均值。

### 按电芯 bootstrap CI

固定随机种子后从 `cell_id` 集合有放回抽样，每次把被抽中的电芯全部预测行带入指标计算；重复 `B` 次后取 5%/95% 分位得到 90% CI。绝不能按循环行抽样，否则同芯相关性被破坏。

### Label-shuffle sanity check

每个 GroupKFold 折内只打乱训练目标，重新拟合 Ridge；记录正常 RMSE 与打乱 RMSE。默认要求打乱 RMSE 至少比正常 RMSE 高 1%，否则状态为 `WARN`，提示特征可能无信号或数据量不足。该检查不是论文结果，也不证明因果关系。

## 5. CLI 与产物

运行：

```bash
PYTHONPATH=code python -m battery_real.cli data/canonical.csv \
  --out real_validation_output --history-window 100 --horizon 50 \
  --splits 5 --bootstrap-reps 300 --leave-condition-out
```

输出：

```text
real_validation_output/report.json
real_validation_output/predictions.csv
real_validation_output/metrics_by_cell.csv
real_validation_output/metrics_by_condition.csv
```

测试构造的数据必须使用 `--test-only`；此时 `report.json.scope=TEST_ONLY`。成功运行看 `run_status`，论文闸门看 `evidence_status` 与 `paper_eligible`；不要读取已删除的顶层 `status`。任何 `TEST_ONLY` 数字禁止复制到 `论文草稿.md` 或 `technical/PAPER_TECHNICAL_BRIDGE.md`。

## 6. 接入真实候选的最小流程

1. 只选择一个化学体系和一个来源，记录官方 DOI/URL、版本、许可、检索日期与 SHA-256。
2. 原始解析器在包外把 cycle、capacity 和单位映射到 canonical CSV；保留一份字段字典和丢弃行统计。
3. 先用 `--splits` 与数据电芯数检查是否可做 GroupKFold；再运行 `--leave-condition-out`（字段允许时）。
4. 人工审阅 `report.json` 的 `scope`、`chemistry`、`leakage_audit`、`label_shuffle_sanity`、区间 coverage/width 与每芯指标；异常只能标记为 `ABSTAIN/WARN`，不能手改成 PASS。
5. 单独生成 V2 证据包并由总负责人批准后，论文才可引用 V2 数字；V1 产物继续保留用于机制和可复现性对照。

## 7. 仍不可主张

- 没有真实来源记录时：不可称 CALCE/Stanford/Poznan 实测校准或外部验证。
- 单一化学体系之外：不可宣称跨 NMC/NCA/LFP/LCO 泛化。
- 只有容量循环数据时：不可估计真实安全失效概率、热失控风险或货币收益。
- 只有汇总 SOH 表时：不可伪装成逐循环原始时序。
- V2 Q1/Q2 不覆盖 Q3 编组或 Q4 压力场景；相关结论仍属于 V1 条件仿真。
- 任何 OOD 温度、倍率、DOD、协议请求应弃权，不外推数值。

## 8. 当前状态

`CANDIDATE_REAL_DATA / NEEDS_CHANGES / HOLD_FOR_PAPER`。Zenodo `10.5281/zenodo.7250553` 已完成 44 个电芯的无损容量解析，并按 NMC532/NMC811 分层完成 GroupKFold、LOCO、描述性残差包络、cell-bootstrap 和 label-shuffle 候选分析；RPT 膝点结果已撤下。完整边界与待更新哈希见 `technical/V2_REAL_DATA_CANDIDATE_REPORT.md`。

这不是 V1 的替换，也不是 CALCE 实测校准。容量单位、温度、DOD、EFC 和内阻仍未确认或缺失；因此 V2 当前只支持归一化容量 Q1/Q2 的来源特定候选验证，不能支撑 Q3/Q4、绝对容量单位、安全概率、货币收益或跨化学体系统一拟合。总负责人批准前，论文 Agent 不得把该报告数字复制进 `论文草稿.md`。
