# G0 论文证据接口

**建立时间**：2026-08-10 12:42 CST

## 目的

`g0.docx` 是论文主笔草稿；GitHub 是来源、参数、仿真配置和结果的事实源。
论文中的每个外部论断、数字、公式和图表必须能回指一个证据 ID。该接口不把
Agent 找到的条目自动视为已核验材料。

## 证据 ID 规则

| ID 范围 | 内容 | 当前状态 | 事实源 |
|---|---|---|---|
| A0 | 研究问题、输入输出、禁止声称 | `APPROVED` | `handoffs/A0_Task_Contract.md` |
| A1 | 退化机理和影响因素来源 | `PENDING_HUMAN_FULLTEXT` | `g0.docx` A1 候选条目 + `evidence/source_ledger.txt` |
| A2 | SOH/RUL 方法来源 | `PENDING_HUMAN_FULLTEXT` | `g0.docx` A2 候选条目 + `evidence/source_ledger.txt` |
| A3 | 梯次筛选与编组来源 | `PENDING_HUMAN_FULLTEXT` | `g0.docx` A3 候选条目 + `evidence/source_ledger.txt` |
| A4 | 鲁棒性、安全和工程建议来源 | `PENDING_HUMAN_FULLTEXT` | `g0.docx` A4 候选条目 + `evidence/source_ledger.txt` |
| S1 | 仿真参数和配置 | `G0_APPROVED_BOUNDARY` | `evidence/parameter_ledger.txt`, `docs/Simulation_Protocol.md` |
| R1 | 仿真运行结果 | `NOT_YET_GENERATED` | G1 输出目录（待建立） |

## 草稿标记规则

`[[EVIDENCE REQUIRED:Ax-ID]]` 表示该论断尚未完成“人工打开全文、核对原始实验/量化数据/参数”的
最后一步。它是有意保留的核验闸门，不是来源缺失。论文主笔删除标记的前提是：填写来源 URL/DOI、
核验人、核验日期、原文页码或表格位置，并确认论断没有超出原文范围。

在 `R1` 结果文件和运行记录产生前，论文不得写入任何预测精度、成本收益、寿命数值或“显著提高”
等结果性结论。

## 通过条件

G1 可使用 `S1` 的边界和协议生成模拟数据；A1-A4 仍需在正式论文定稿前逐条转为
`HUMAN_VERIFIED`，否则对应论断必须删除或改为明确的研究假设。
