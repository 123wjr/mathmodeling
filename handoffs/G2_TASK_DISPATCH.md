# A题 G2 任务书：Q1/Q2 阶段辨识与寿命预测证据包（A2）

**发布时间**：2026-08-11（G1 验收后派工；2026-08-12 存档复核，内容与现有实现及 A2 证据包一致）
**G1 状态**：`PASS_WITH_CHANGES` / `APPROVED FOR G2`（见 [G1_OWNER_REVIEW.md](G1_OWNER_REVIEW.md)）
**比赛截止**：2026-08-13 20:00 CST

## 一、G2 目标

完成两个研究问题并产出 A2 证据包：

- **Q1 阶段辨识**：在 G0 冻结支持域内，对合成数据做退化阶段（正常/退化/临界）、膝点可观测性与温度/倍率/DOD 全因子主效应分解。
- **Q2 寿命预测**：以电芯为单位留组，比较透明基线（persistence、局部线性）与统计学习模型（ridge、随机森林）的 50-cycle SOH 预测；对 80% SOH 终点做**右删失感知**的 RUL 建模（主模型 log-normal AFT），并报告 90% 区间覆盖与删失矛盾率。

G2 只使用 G1 生成器（`code/g1_generator`）在冻结支持域内确定性再生的**仿真数据**，不引入外部实测数据，不声称外部验证。

## 二、事实源与冻结输入

- [参数台账](../evidence/parameter_ledger.txt)（系数边界；`ASSUMED` 标签沿用到 G2 全部阈值）
- [仿真协议](../docs/Simulation_Protocol.md)（第 6/7 节退化公式、第 11 节支持域）
- [A1 仿真证据包](A1_simulation_package.md)（R1 数据接口：字段、seed=42、哈希）
- [研究配置](../configs/study_pipeline.json)（Q1/Q2 参数：27 工况、历史窗 100、预测步长 50、landmark 300、5 折、bootstrap 300、CI 0.9）
- [实验计划](../technical/EXPERIMENT_PLAN.md)（Q1/Q2 设计冻结版）

冻结输入（R1 接口，来自 G1）：全因子 `T=[25,35,45] × C=[0.5,1.0,2.0] × DOD=[50,80,100]`，每格 4 电芯，每芯 1000 cycles → **27 工况 / 108 电芯 / 108000 行**，由运行命令确定性再生（原始行不落盘，防重复）。

## 三、时间表（恢复排期，来自总控台 §3）

| 时间（CST） | 责任人 | 交付/检查点 | 状态 |
|---|---|---|---|
| 8/11 15:00 | 总负责人 | G1 验收通过，冻结 R1 数据接口，派工 G2 | 已完成 |
| 8/11 18:00 | 建模手 | 确认研究配置与数据接口可用，报告阻塞 | 已完成 |
| 8/11 23:30 | 建模手 | 提交 `handoffs/A2_prediction_package.md` 与 `study_output/` 全部 Q1/Q2 产物 | **GREEN：PASS_WITH_LIMITATIONS** |
| 8/11 起 | 论文手 | 按 A2 写作边界写 Q1/Q2 方法段；验收前不写结果数字 | 进行中 |
| 8/12 08:30 | 总负责人 | G2 复核结论并入总控台；论文回指事实表 F1–F4 与 A2 | 待执行 |

## 四、队友 2：建模与代码负责人

### 人必须完成

1. 在 `main`（或仓库现行等价分支）维护 `code/battery_study` G2 代码，并亲自复跑最终命令。
2. 检查 Agent 生成的公式、单位、边界和 CSV 字段，不接受“代码能跑”作为唯一验收依据。
3. 确认所有输出来自固定配置与固定 seed；记录 Git commit、配置文件、运行命令和文件 SHA-256（`study_output/run_manifest.json`）。
4. 不下载或上传私密材料；外部数据只使用 `source_ledger.txt` 已列入口；未核验字段写 `UNVERIFIED`；仿真结果不称实测。

### Agent 可执行

1. **Q1**：平衡全因子边际平方和分解，输出温度/倍率/DOD 对 `capacity_fade` 与 `final_resistance_growth` 的主效应权重与总方差占比；残差项显式保留交互与电芯变异。
2. **Q1 膝点**：min_efc=300 起搜索、每侧至少 80 点；输出可检测/右删失电芯数与恢复误差（仅作生成器自检）；阶段定义 `normal / degradation / critical`，`critical_soh=0.8` 必须标 `[ASSUMED][UPDATEABLE]`。
3. **Q1 协议效应**：单一 CC-CV 水平下必须输出 `NOT_IDENTIFIABLE`（null 权重），不得硬造协议效应。
4. **Q2 SOH**：历史窗 100 cycles、预测步长 50、landmark 300；四模型对比（persistence / local_linear / ridge / random_forest）；**5 折 `GroupKFold(cell_id)`**；cell-bootstrap 300 次 90% CI；输出 `q2_split_audit.json` 证明各折电芯零重叠。
5. **Q2 RUL**：80% SOH 终点；43 事件 + 65 右删失必须如实入账；主模型 log-normal AFT（删失似然 + 训练事件残差校准分位 0.99）；ridge/RF 仅用观测事件作删失朴素对照；structure-matched ceiling 仅作上限参照。
6. **leave-one-condition-out**：覆盖全部 27 工况，只测冻结支持域内插/外推，不越域。
7. 产出图（`fig_q1_factor_weights.svg`、`fig_q2_soh_rmse.svg`、`fig_q2_rul_rmse.svg`）、`validation_gates.json`（硬闸门）与 `A2_prediction_package.md`。

### 必测规则（验收硬指标）

- `GroupKFold(cell_id)` 各折训练/测试电芯集合**零重叠**（`cell_overlap=[]`）。
- Q1 每个响应的主效应权重归一化后和为 1（残差单独报告）。
- Q1 协议效应状态必须为 `NOT_IDENTIFIABLE`。
- RUL 事件数 + 右删失数 = 108 电芯（43 + 65）。
- Q2 SOH/RUL 每个数字必须带 90% cell-bootstrap 区间；删失矛盾率必须报告。
- 所有 `[RESULT]` 只允许标“仿真留组性能”；所有门槛/终点标 `[ASSUMED][UPDATEABLE]`。

### 交付格式

```text
状态：DONE / DONE_WITH_CONCERNS / BLOCKED
分支/commit：
代码与配置：
运行命令：
测试结果：
输出文件与SHA-256：
已核验来源：
未核验来源：
失败项与已知限制：
需要总负责人决定：
```

## 五、队友 1：论文主笔与豆包 Agent

### 人必须完成

1. 在腾讯文档维护唯一正文；Q1/Q2 方法与变量段可先行撰写，**A2 验收前不写任何预测精度、寿命数字或模型优越性**。
2. 保留 `[[EVIDENCE REQUIRED:A2-ID]]`，直到本人打开全文并填写证据表（URL/DOI、页码/表号、核验人、日期、状态）。
3. 将 Q1/Q2 描述为“仿真数据上的模型比较”，不得改写为实测验证。

### 豆包 Agent 可执行

- 按 G0/G1 已批准术语整理 Q1/Q2 方法段、符号表与流程图文字。
- 将每个外部论断映射到 A2 证据 ID；不自行补 DOI、实验数字或结果。
- 根据 A2 候选结果预留图表位置，不填入虚构数值。

### 交付格式

```text
状态：DONE / BLOCKED
腾讯文档链接：
完成章节：
新增证据表条目：
已人工核验来源：
保留的EVIDENCE REQUIRED标记：
待A2结果：
需要总负责人决定：
```

## 六、总负责人 G2 验收门

1. Q1/Q2 公式、边界与阈值是否遵守仿真协议和参数台账；`critical_soh=0.8` 是否仅作 `[ASSUMED][UPDATEABLE]` 建模终点。
2. 数据划分是否以电芯为单位、5 折零重叠；RUL 删失处理是否诚实（43 事件 + 65 右删失、删失矛盾率、90% 覆盖为经验值）。
3. CSV/字典/图/配置/seed/哈希/运行命令是否互相一致（对照 `study_output/run_manifest.json` 与 `technical/PAPER_WRITING_FACT_SHEET.md` F1–F4）。
4. 是否与外部验证隔离：无 CALCE/NASA 实测数据混入拟合；ceiling 模型是否仅作 simulator ceiling 不作外部验证。
5. A2 是否明确区分 `OBSERVED` / `LITERATURE_FIXED` / `ASSUMED` / `RESULT`，并列出限制与“未完成”项。

验收结论只能是：`PASS`、`PASS_WITH_CHANGES` 或 `BLOCKED`。未通过时只降级范围，不增加模型复杂度。

## 七、禁止事项

- 不引入 LSTM、Transformer、GAN、PINN、SHAP 或超参数搜索；Q2 只允许透明基线与统计学习模型。
- 不把 80% SOH 写成普适安全失效阈值。
- 不把“仿真留组性能”写成外部验证或真实精度；structure-matched ceiling 不得作为生成器正确性的反证。
- 不把模拟数据写成实测数据；不用 Q2 预测精度反向证明 G1 生成器正确。
- 不越过冻结支持域（25–50 degC、0.5–2C、DOD 50–100%、CC-CV）给出数值预测。
- 不将未完成全文核验的 A1–A4 条目当作正式论文引用。
