# V2 真实数据验证技术交接

> 状态：`CANDIDATE_NON_MAINLINE`。本包只在隔离分支开发，未替换 V1。
> 目标：为真实电池循环数据提供可复跑的 Q1/Q2 证据接口；当前仓库没有把任何来源数据当作已使用数据。

## 1. 与 V1 的证据增益

| 层 | V1 当前能力 | V2 增益（接入真实数据后才生效） |
|---|---|---|
| 数据 | 公开机理方向 + 可复现 NMC 合成时序 | `source_id`、版本、化学体系和逐电芯实测记录可追溯 |
| Q1 | 合成生成器内的阶段/因素恢复检查 | 实测归一化容量趋势、右删失膝点、可辨识因素的描述性验证 |
| Q2 | 同一仿真家族内按电芯留组比较 | 独立来源逐电芯 GroupKFold/LOCO，透明基线与 Ridge 对照 |
| 不确定性 | 仿真内 cell-bootstrap/AFT 区间 | 训练电芯 split-conformal 90% 预测区间 + 按电芯 bootstrap CI |
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

建议 source adapter 在仓库外完成原始文件解析，然后只输出上述 CSV，并同时保存原始 URL/DOI、版本、下载日期、许可、原始文件 SHA-256、字段单位和筛选规则。

## 3. Q1 协议

每芯以 `efc` 为老化横轴；缺失时退回 cycle，并在报告中保留该事实。Theil-Sen 斜率用于稳健净退化趋势。膝点在连续 hinge 模型

`q(t) = a + b x + c max(0, x - k)`

上枚举候选 `k`，要求两侧至少 `knee_min_points` 条记录，且 `b+c` 相比 `b` 有至少 10% 的额外下降。输出：`DETECTED`、`RIGHT_CENSORED` 或 `NOT_DETECTED`。未达到 SOH endpoint 且没有足够后段记录时不得强行报膝点。

可选因素只有在字段完整、每个电芯内恒定、至少两个水平且每水平至少 2 芯时做边际均值/效应范围；结果是 `PASS_DESCRIPTIVE` 且 `causal=false`。否则为 `ABSTAIN`。一个水平的协议（例如全是 CC-CV）不生成协议权重。

## 4. Q2 协议与公式

在 landmark `t` 构造历史特征，只读取 `cycle <= t`：当前归一化容量、最近窗口 Theil-Sen 斜率、当前 cycle，以及完整可用的温度/倍率/DOD。目标是 `t+h` 的归一化容量。比较：

- persistence：`q_hat(t+h)=q(t)`；
- local-linear：`q_hat(t+h)=q(t)+h * slope_recent`；
- Ridge：标准化特征后 `L2` 正则线性模型（`alpha=1`，无调参搜索）。

外层使用 `GroupKFold(cell_id)`；每折保存 train/test cell 清单并断言交集为空。LOCO 按完整 `condition_id` 留出，同样断言 cell 不重叠。训练集内部再按电芯分为 proper-train/calibration cells；每个校准电芯先取最大绝对残差，再对电芯级残差取有限样本 90% 分位，得到

`[q_hat-r, q_hat+r]`。

报告 `MAE`、`RMSE`，在真值方差非零时报告 `R2`；区间报告 coverage 与 mean width。每芯和每工况分别报告 Ridge 指标，不能只给行级总体均值。

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

测试构造的数据必须使用 `--test-only`；此时 `report.json.scope=TEST_ONLY`。任何 `TEST_ONLY` 数字禁止复制到 `论文草稿.md` 或 `technical/PAPER_TECHNICAL_BRIDGE.md`。

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

`CANDIDATE_NON_MAINLINE / NO_REAL_DATA_LOADED`。代码和 TEST_ONLY smoke 只证明接口与协议可运行，不提供论文数字。接入真实数据前需补充 source-specific provenance manifest，运行完整测试和独立复跑，并由总负责人重新验收。
