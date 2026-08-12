# A题 G1 材料包索引

**适用排期**：2026-08-10 16:17 CST 发布的 G1 任务书
**使用方式**：先读“共同材料”，再按角色读取对应材料；不要把模板脚本或未验收结果当作项目事实源。

## 一、共同材料

| 优先级 | 材料 | 用途 |
|---|---|---|
| 必读 | [G1_TASK_DISPATCH.md](G1_TASK_DISPATCH.md) | 当前任务、角色分工、时间节点和交付格式 |
| 必读 | [G0_OWNER_REVIEW.md](G0_OWNER_REVIEW.md) | G0 验收结论和 G1 放行条件 |
| 必读 | [A0_Task_Contract.md](A0_Task_Contract.md) | 四问输入输出、研究假设和禁止声称 |
| 必读 | [parameter_ledger.txt](../evidence/parameter_ledger.txt) | 参数单位、范围、来源和标签 |
| 必读 | [Simulation_Protocol.md](../docs/Simulation_Protocol.md) | 容量/内阻生成公式、噪声、随机效应和测试规则 |
| 参考 | [Data_Strategy.md](../docs/Data_Strategy.md) | 主化学体系、数据来源边界和模拟数据限制 |
| 参考 | [source_ledger.txt](../evidence/source_ledger.txt) | 候选公开来源及其当前核验状态 |

## 二、建模手材料包

### 先读

1. [G1_TASK_DISPATCH.md](G1_TASK_DISPATCH.md) 的“队友 2”部分。
2. [G0_OWNER_REVIEW.md](G0_OWNER_REVIEW.md) 第 3、4 节。
3. [parameter_ledger.txt](../evidence/parameter_ledger.txt) 全文。
4. [Simulation_Protocol.md](../docs/Simulation_Protocol.md) 第 3--14 节。

### 实现时必须遵守

- 只实现 G0 批准的分段平方根生成器，不实现 SOH/RUL 预测器。
- 主线为 NMC；所有仿真系数为 `ASSUMED`，不得改写为实测值。
- 输出字段、固定 seed、边界拒绝规则和同 seed 一致性必须写入 A1。
- 不使用 `template/scripts/` 中未经审查的大型模型脚本。

### 交付回指

- 代码、配置、测试和图表放 GitHub。
- 运行摘要写入 `handoffs/A1_simulation_package.md`。
- 论文只引用验收后的 A1 文件，不引用聊天中的运行描述。

## 三、论文手材料包

论文手的内容编辑源是仓库根目录 `论文草稿.md`；在线文档是协作/提交副本。论文手无需操作代码或结果文件。

### 先读

1. [G1_TASK_DISPATCH.md](G1_TASK_DISPATCH.md) 的“队友 1”部分。
2. [论文草稿.md](../论文草稿.md) 作为当前唯一可编辑论文源；`g0.docx` 仅是历史交接草稿。
3. [G0_EVIDENCE_INTERFACE.md](G0_EVIDENCE_INTERFACE.md) 的证据 ID 和标记规则。
4. [A0_Task_Contract.md](A0_Task_Contract.md) 的禁止声称结论。
5. [Data_Strategy.md](../docs/Data_Strategy.md) 和 [Simulation_Protocol.md](../docs/Simulation_Protocol.md) 的方法边界。
6. [论文模板目录](../template/paper/) 的格式材料。

### 写作时必须遵守

- `[[EVIDENCE REQUIRED:Ax-ID]]` 是待人工全文核验闸门，未核验前不要删除。
- A1 验收前不得填入预测精度、寿命、成本收益或模型优越性数字。
- 将“仿真数据”“公开资料支持方向”和“本研究假设”分开表述。
- 80% SOH 只能写作可调整退役/RUL阈值，不能写成普适安全失效阈值。

### 交付回指

- 正文先保存在 `论文草稿.md`，再同步到在线文档；证据表和修订记录与对应版本一起维护。
- 论文数字必须回指 A1 输出文件或已人工核验的 A1-A4 来源。
- 不把豆包生成的未核验引用直接放入参考文献。

## 四、当前不可使用材料

- `试题 B.pdf` 和 B 题资料：与当前 A 题 G1 无关。
- `template/scripts/` 中未经负责人批准的模型脚本：只能作为语法参考。
- 尚未生成的 R1 结果：在 A1 验收前不存在，不能预写论文结果。
