# A5 论文技术过渡包

**状态**：`INTERIM_V3_HANDOFF / READY_FOR_OUTLINE_WITH_LIMITATIONS`；论文初稿仍为 `CANDIDATE_DRAFT / NOT_READY_FOR_STAGE_2_5_PASS`

**Owner**：总负责人；论文主笔负责按本包填充 `../论文初稿.md`，再同步在线文档。

## 事实锁定

| 项 | 值 |
|---|---|
| 当前论文编辑骨架 | `../论文初稿.md`（G12、已对齐 V2；旧 `../论文草稿.md` 不再编辑） |
| 外部格式参考 | 人工确认 DOCX，SHA-256=`55468c073dc248dacbd91f84f06cc4070a99acbccba913907ad6efc57a6eddff`；仅作比较，不要求 Agent 读取 |
| 桥接文档 | `../technical/PAPER_TECHNICAL_BRIDGE.md`；与草稿逐节对齐 |
| 技术过渡文档 | `../technical/PAPER_TECHNICAL_BRIDGE.md` |
| 技术过渡文档 SHA-256 | `ea2a0b691f297c03a9a9011ca3ff9d426e58b1fc6eb99598f269c196fee8783d` |
| 生成结果事实源 | Q1/Q2：`study_output/`；当前 Q3/Q4：`study_output_v3/`；各目录 `run_manifest.json` |
| 当前范围 | NMC 合成仿真；Q1-Q4；支持域 25--50 degC、0.5--2C、DOD 50--100%、CC-CV |
| V3 当前状态 | 临时论文交付；技术复跑通过后可写大纲/方法/带标签候选结果；参数依据与观测偏差补强后再冻结数字 |

## 交付内容

- 逐问输入/输出、假设、公式、算法和实验协议。
- Q1-Q4 可引用数字及精确结果文件回指。
- `[CONFIRMED]`、`[RESULT]`、`[ASSUMED][UPDATEABLE]`、`[UNCERTAIN]`、`[OOD/ABSTAIN]`、`[PAPER_GAP]` 标签。
- 草稿章节映射、图表接口、主张-证据矩阵、附录索引和更新注册表。
- 11/11 统计谬误扫描与 7 类 AI 研究失败模式预审；预审不等于论文完整性通过。

## 最新骨架冲突闸门

下载版 DOCX 的以下原文不能直接带入论文：

- “CALCE 核心参数校准依据”：当前没有 CALCE 原始循环下载、解析或拟合。
- “NASA 容量退化趋势辅助对照”：NASA 未进入当前实验、训练、验证或参数估计。
- “安全失效边界、检测成本、串并联编组”：当前只有自设门槛、无量纲目标和 4 芯 module-level set-packing。
- “范围外未校准压力测试”：当前范围外统一 `[OOD/ABSTAIN]`，不提供数值。
- 模板中的 `XXX`、二次方程、jieba/AHP 示例和无关参考文献：全部删除。

逐段替换表、段落号和技术替代内容见 `../technical/PAPER_TECHNICAL_BRIDGE.md` 第 2.2 节。

## 未完成项（不可用文字伪造）

1. `论文初稿.md` 的 V3 大纲、方法和表图占位：`PENDING_PAPER_AGENT`；最终图号与摘要结论暂不冻结。
2. 外部文献全文、页码/表号人工核验：`PENDING_HUMAN_VERIFICATION`。
3. CALCE 实测拟合、NASA 外部验证、OOD 数值、完整储能拓扑/货币收益：`NOT_DONE` 或 `PAPER_GAP`。
4. V2 真实数据候选结果：`HOLD_RPT_SENSITIVITY / paper_eligible=false`，不得进入论文数字表。
5. Stage 2.5 完整性闸门：`NOT_READY_FOR_STAGE_2_5_PASS`；外部引用核验和真实外部效度仍未闭环。

## 必须保留的限制

- 未下载/解析/拟合 CALCE 原始循环数据；不得写实测校准。
- NASA 未进入当前实验；不得写已完成外部对照。
- Q3 是 4 芯 module-level set-packing；没有完整串并联储能阵列拓扑。
- Q3 当前使用 cycle=750 条件 RUL；V1 的 cycle=300 换算口径已由 V3 取代，不得混用。
- 低温、过充、过放和 3C 只弃权，不给数值。
- Q4 固定 V3 INTERVAL_RISK + balanced 的同一 8 组，从 cycle 751 开始改变工况；只能称“仿真条件下固定编组压力追踪”，不得写真实安全验证。
- 门槛、权重、无量纲成本收益和 80% SOH 终点均可更新。

## 交接动作

论文主笔只需：

1. 以 `../论文初稿.md` 为编辑骨架，按 `../technical/TECHNICAL_SOLUTION_V3.md` 第 0 节替换 Q3/Q4，并建立 V3 大纲、方法和表图占位。
2. 每个结果句回填主张-证据表；未核验文献保留 `EVIDENCE_REQUIRED`。
3. 删除模板示例、无关参考文献和示例代码；不编辑代码、CSV、JSON、SVG。
4. 所有 V3 结果保留 `RESULT_CANDIDATE_UPDATEABLE`；本轮不冻结摘要、结论和最终图号。回报正文章节、已回指数字/图数、人工核验引用数和剩余阻塞。

复跑命令：

```bash
PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output
PYTHONPATH=code python -m battery_study.v3_cli --config configs/study_pipeline_v3.json --out study_output_v3
PYTHONPATH=.:code python -m pytest code/tests -q
```

## 最后验证记录

```text
status: VERIFIED_WITH_SIMULATION_LIMITS
evidence: V3 gates=12 PASS; full pytest=93 passed, 1 skipped; manifest=PASS
paper rule: V3 数字只可按最新 study_output_v3 和本包限定语写入；不称真实外部验证
```
