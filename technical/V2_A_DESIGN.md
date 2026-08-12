# V2-A 第二版技术方案设计契约

状态：`APPROVED_SCOPE / IMPLEMENTING`
分支：`technical-v2-a`

## 目标

把 Zenodo NMC/Graphite 候选层从“单一原始序列分析”升级为可审计的双口径分析：

1. 保留原始容量序列作为未经预处理的敏感性基线。
2. 按来源官方代码执行 `seasonal_decompose(period=50).trend`，生成回顾性去 RPT 序列。
3. 对 NMC532、NMC811 分层重跑 Q2，显式报告预处理导致的方向变化。
4. 任何使用完整双侧趋势的结果标记为回顾性敏感性，禁止当作无泄漏在线预测证据。
5. 交付可直接供论文 Agent 使用的技术过渡文档，不修改 `论文草稿.md`、V1 Q3/Q4 或 CALCE/NASA 状态。

## 不在本版范围

- 不下载、拟合或声称已校准 CALCE 原始循环数据。
- 不把 NASA 写成已使用的外部验证集。
- 不新增 Q3 串并联拓扑、货币收益或系统损耗模型。
- 不把 Q4 场景内重新筛选写成 Q3 同组电芯纵向验证。
- 不为低温、过充、过放或 `>2C` 支持域外输入生成数值。
- 不发布未完成来源一致预处理的 Q1 膝点计数。

## 设计

### 数据层

`technical/prepare_nmc_modes.py` 继续负责无损解析，并在 quality/provenance 中写明
`RAW_UNPROCESSED`。新增 `technical/prepare_nmc_rpt.py`，只接受 canonical CSV，按
`cell_id` 排序后执行来源方法。输出保留原字段，并增加：

```text
rpt_preprocessing
rpt_method
rpt_period
future_points_used
prediction_eligible
```

来源方法固定为：

```text
statsmodels.tsa.seasonal_decompose(series, period=50, extrapolate_trend="freq").trend
```

由于该趋势使用观测序列两侧的信息，输出标记为
`SOURCE_PERIOD50_RETROSPECTIVE`、`future_points_used=true`、
`prediction_eligible=false`。它只能做回顾性敏感性分析，不能替代严格在线预测预处理。

### 验证层

`battery_real.core.evaluate` 不再硬编码“所有来源都有 RPT 尖峰”。它从输入行读取统一的
`rpt_preprocessing` 元数据，并输出：

- `run_status`：代码是否成功完成；
- `evidence_status`：是否满足论文证据闸门；
- `paper_eligible`：当前结果能否进入论文；
- `preprocessing`：方法、周期、是否读取未来点、预测资格；
- `leave_condition_out.condition_definition`：复合实验层的组成字段与每折电芯数。

原始数据和回顾性 `period=50` 数据均保持 `paper_eligible=false`，直到完成无泄漏预处理或总负责人另行放行。CLI 只把计算失败返回非零；不会把科学 HOLD 打印成 `PASS`。

### 结果层

`technical/V2_REAL_DATA_CANDIDATE_REPORT.md` 升级为双口径报告：

- 原始口径：只能作为未经 RPT 处理的基线敏感性；
- `period=50` 口径：只能作为来源一致但回顾性的敏感性；
- 两者若改变 Ridge 与 persistence 的相对方向，结论必须写成“预处理敏感”，不得选择性引用任一口径。

新增 `technical/TECHNICAL_SOLUTION_V2.md`，按论文骨架提供假设、模型、实验、结果、限制和可更新项，所有数字回指报告或 JSON。

## 验收证据

1. `code/tests/test_prepare_nmc_rpt.py` 先失败后通过，验证 period、元数据和逐芯行数保持。
2. `code/tests/test_battery_real.py` 验证 `run_status/evidence_status/paper_eligible`、预处理状态和复合 LOCO 元数据。
3. NMC532/NMC811 原始与 period=50 四组运行均完成，第二次全新目录运行的 8 个产物逐字节一致。
4. 报告列出两个口径的 persistence/Ridge RMSE、相对变化、区间口径与哈希，并明确 Q1 HOLD。
5. `PYTHONPATH=code python -m pytest code/tests -q`、`python -m compileall -q code technical`、`git diff --check` 通过。
6. 范围审计确认未修改 `论文草稿.md`、V1 `study_output`、Q3/Q4 代码或 CALCE/NASA 使用状态。
