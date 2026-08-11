# A题论文 Agent 入口

> 适用对象：负责在线文档论文的主笔及其 Agent。代码、配置、实验输出和技术证据保存在 GitHub；论文正文仍以在线文档为唯一写作场所。
>
> 基线不固定 commit。每次启动先执行 git pull --ff-only origin main，再以 git rev-parse --short HEAD 的输出作为本次读取基线。

## 0. 任务定义

题面是 [试题 A.pdf](试题%20%20A.pdf)：锂电池剩余寿命预测与梯次利用筛选优化。论文要回答四个问题：

1. 性能退化特征与影响因子辨识。
2. SOH 评估与 RUL 预测。
3. 退役筛选与储能编组多目标优化。
4. 多工况仿真、鲁棒性分析与工程建议。

本仓库当前交付的是一条可复跑的 NMC 合成仿真研究链，不是 CALCE 实测校准报告。论文的目标是把“题面问题 → 假设 → 模型 → 实验 → 条件化结论”讲成一条可审计的证据链。

如果 Agent 环境提供 academic-research-suite，使用 academic-paper 的 plan 模式完成配置和论证，再依次进入 outline、draft、citation-check、peer-review；没有完成配置确认和大纲确认时，不进入整篇正文生成。

## 1. 你先做什么

在仓库根目录执行：

~~~bash
git pull --ff-only origin main
git rev-parse --short HEAD
git status --short --branch
~~~

然后按以下顺序阅读。不要跳过前四项，也不要先从 study_output/*.csv 猜结论。

| 顺序 | 文件 | 你要得到的内容 |
|---:|---|---|
| 1 | [试题 A.pdf](试题%20%20A.pdf) | 原题、四个问题和题面约束；题面是问题定义的事实源 |
| 2 | [template/paper/数模论文模板总结.docx](<template/paper/数模论文模板总结.docx>) | 论文格式、栏目和排版要求；若在线文档有新模板，以总负责人确认的版本为准 |
| 3 | [handoffs/PROJECT_COMMAND_CENTER.md](handoffs/PROJECT_COMMAND_CENTER.md) | 当前闸门、责任人、截止时间、停止规则和唯一事实源顺序 |
| 4 | [technical/PAPER_WRITING_FACT_SHEET.md](technical/PAPER_WRITING_FACT_SHEET.md) | 论文可直接使用的数字及 CONFIRMED/RESULT/UPDATEABLE 标签 |
| 5 | [technical/TECHNICAL_REPORT_MINIMAL.md](technical/TECHNICAL_REPORT_MINIMAL.md) | 假设、公式、实验设计、结果解释和四部分最小技术文档 |
| 6 | [technical/VALIDATION_REPORT.md](technical/VALIDATION_REPORT.md) | 9 个自动闸门、统计完整性和不能声称的内容 |
| 7 | [A1](handoffs/A1_simulation_package.md)、[A2](handoffs/A2_prediction_package.md)、[A3](handoffs/A3_optimization_package.md)、[A4](handoffs/A4_robustness_package.md) | 每个阶段的接口、限制和证据路径 |
| 8 | [study_output/run_manifest.json](study_output/run_manifest.json) | 源码/配置/产物 SHA-256 和生成时的 Git HEAD；用于最终回检 |

technical/EXPERIMENT_PLAN.md 可用于补写方法和实验小节；technical/SUPPORTING_MATERIALS_README.md 说明支撑材料如何复跑。

## 2. 事实源优先级

发生冲突时按这个顺序裁决，低优先级内容不能覆盖高优先级内容：

1. 总负责人签署的闸门结论和 .codex/DECISIONS.md。
2. 已验收的 A0-A4 证据包与总控台。
3. technical/PAPER_WRITING_FACT_SHEET.md、study_output/*.json/csv、验证闸门和 manifest。
4. 可复跑代码、配置和图表。
5. 在线文档草稿、Agent 汇报和聊天内容。

题面只定义研究问题，不提供实验数字。任何“聊天中出现过但文件中找不到”的数字都视为不可用。

## 3. 证据标签与硬边界

每个结果性句子在写入在线文档前，先在证据表中登记：claim_id、原句、标签、来源文件、精确字段/行或图号、核验人/日期、核验状态。

| 标签 | 可以怎么写 | 不能怎么写 |
|---|---|---|
| CONFIRMED | 题面、代码、配置或可复跑结构已确定的事实 | 把结构事实扩展成真实世界效果 |
| RESULT | “在本合成仿真/留组实验中……”并给出回指 | “实测证明”“真实车辆精度” |
| ASSUMED + UPDATEABLE | 明确是自设参数、阈值、代理或权重，并说明可替换 | 写成 CALCE 实测估计、行业标准或安全规范 |
| UNCERTAIN | 明确列为未知或限制 | 用常识、模型输出或 Agent 猜测填空 |
| OOD/ABSTAIN | 说明支持域外弃权、不给数值 | 从趋势图外推低温、过充、过放、3C 或安全概率 |

当前不可越过的科学边界：

- 所有 G1-G4 数字来自合成数据；没有读取或拟合 CALCE 原始循环数据。
- 支持域为 25--50 degC、0.5--2C、DOD 50--100%、CC-CV；协议效应不可辨识。
- 80% SOH 是建模终点/筛选阈值，不是普适安全阈值。
- 不写真实车辆泛化、货币收益、真实安全失效概率或范围外寿命。
- 结构匹配 RUL 是 simulator ceiling，不能反向证明生成器真实有效。

## 4. 当前可写数字（只从这里复制）

以下数字必须保留标签和限定语；更详细的定义以事实表和对应 CSV/JSON 为准。

| ID | 可写事实 | 标签 | 回指 |
|---|---|---|---|
| F1 | 27 工况、108 电芯、108000 行、每芯 1000 cycles | CONFIRMED | study_output/factorial_design.csv |
| F2 | 72 个膝点可观测、36 个右删失；内部膝点恢复误差中位数 13.40 EFC | RESULT 仿真自检 | study_output/q1_knee_detection.csv |
| F3 | 50-cycle SOH 的 Ridge RMSE=0.004206，cell-bootstrap 90% CI=0.003962--0.004447 | RESULT 仿真留组 | study_output/q2_soh_metrics.csv |
| F4 | RUL 为 43 个事件 + 65 个右删失；log-normal AFT 事件 RMSE=38.39 cycles，90% 区间覆盖=0.9070 | RESULT 仿真留组 | study_output/q2_rul_metrics.csv |
| F5 | 108 个候选中 85 个过门槛；3167 个兼容候选组；MILP 选 8 组、重复分配 0 | RESULT + UPDATEABLE | study_output/q3_solution_summary.csv |
| F6 | 5 个鲁棒性 seed；7 个参数 OAT；4 类 OOD 全部弃权 | CONFIRMED + OOD/ABSTAIN | study_output/q4_*.csv |

写数字时同时写三件事：数据是仿真、验证如何分组、结论适用范围。例如：

> 在本合成数据的 GroupKFold(cell_id) 留组实验中，Ridge 的 50-cycle SOH RMSE 为 0.004206；该数值不代表真实电芯或车辆精度。

## 5. 推荐论文骨架

竞赛模板优先于通用 IMRaD；下面的内容顺序可映射到模板栏目，不要为了套期刊格式改变题目要求：

1. 摘要、关键词：问题、方法链、最重要的条件化结果、限制。
2. 问题重述与符号说明：只引用题面；列出 cycle/EFC、SOH、RUL、DOD、倍率、温度和删失符号。
3. 模型假设与数据生成：NMC 主线、分段平方根退化、工况边界、个体差异、噪声和标签。
4. 问题一：阶段/膝点定义、主效应权重和协议不可辨识说明。
5. 问题二：SOH 特征、GroupKFold、右删失 AFT、对照模型、区间覆盖和压力测试。
6. 问题三：硬门槛、兼容组、set-packing MILP、三套权重、约束回算和 greedy 对照。
7. 问题四：多工况、5 seed、OAT、批次代理、OOD/ABSTAIN 和工程触发规则。
8. 模型评价、局限与推广：区分仿真内一致性、统计不确定性和真实外部有效性。
9. 结论与工程建议：只写支持域内、可回指的结论；给出需要真实数据后更新的项。
10. 参考文献、附录/支撑材料：参数台账、运行命令、图表索引和 AI 使用披露。

## 6. Agent 工作协议

### 阶段 A：启动与配置（必须先完成）

先建立 Paper Configuration Record，至少确认：

- 论文类型：数学建模竞赛论文/会议型短文（以模板为准）。
- 正文语言、摘要语言、目标字数/页数、引用格式。
- 三位作者与贡献；无经费/无利益冲突也要显式记录。
- 在线文档链接、当前草稿版本、模板限制。
- 是否已有人工核验的参考文献；没有就不要假装已有文献库。

配置不完整时，Agent 只问缺失项，不直接生成整篇论文。

### 阶段 B：证据台账（先于正文）

在在线文档建立“主张-证据表”，推荐字段：

~~~text
claim_id | 章节/段落 | 主张原句 | 标签 | 来源文件 | 字段/行/图号 | 核验人/日期 | 状态
~~~

每个数字、比较、因果句和工程建议都要有一行；没有来源就标 EVIDENCE REQUIRED，不能由 Agent 猜补。

### 阶段 C：结构与论证

先交付章节大纲和“主张 → 模型 → 实验 → 证据 → 限制”映射，等待总负责人确认后再大段写作。每个问题至少包含：输入、假设、变量、方程/算法、评价指标、结果、失败边界。

### 阶段 D：写作与图表

- 方法先写，结果只引用已存在的 CSV/JSON/SVG。
- 图注必须写数据类型（合成仿真）、工况、seed/折分和回指路径。
- 每个模型选择都写“为什么采用 + 用什么对照 + 局限是什么”。
- 不把代码名直接当结论；先解释统计对象和评价口径。
- 图表编号在在线文档中固定，改图后同步更新图注和证据表。

### 阶段 E：引用与诚信审查

引用只接受 DOI、出版社/期刊官网、官方数据页或可人工核验的原文。禁止编造作者、年份、卷期、页码和 DOI。正文引用与参考文献必须双向零孤儿；无法核验的来源标 UNVERIFIED，不用于关键结论。

### 阶段 F：交接报告

每次交接使用总控台的六行协议：

~~~text
状态：DONE / IN_PROGRESS / BLOCKED
Owner：论文主笔 Agent / 论文主笔
产物：在线文档链接 + 章节/证据表版本
验证：事实表条目数；已回指数字/图数；人工核验引用数
阻塞：缺失信息 + 等谁决定；无则 NONE
下一步：动作 + CST 截止
~~~

## 7. 可直接复制给论文 Agent 的启动提示

~~~text
你是 A 题数学建模论文主笔 Agent。你的写作目标是在线文档，不是修改 GitHub 代码。

工作目录：仓库根目录。先只读，不写正文、不改 CSV/JSON/SVG、不运行会覆盖结果的命令、不提交 Git。

按顺序阅读：
1. PAPER_AGENT_START_HERE.md
2. 试题  A.pdf
3. template/paper/数模论文模板总结.docx
4. handoffs/PROJECT_COMMAND_CENTER.md
5. technical/PAPER_WRITING_FACT_SHEET.md
6. technical/TECHNICAL_REPORT_MINIMAL.md
7. technical/VALIDATION_REPORT.md
8. handoffs/A1_simulation_package.md、A2_prediction_package.md、A3_optimization_package.md、A4_robustness_package.md
9. study_output/run_manifest.json

第一轮只输出四块：
A. 已读文件清单与当前 HEAD；
B. Paper Configuration Record（缺失项留空并列问题）；
C. 主张-证据表（每个数字/比较/因果句一行）；
D. 论文大纲，逐节标出模型、实验、结果、限制和证据路径。

硬规则：
- 只从 PAPER_WRITING_FACT_SHEET.md 和对应 study_output 文件取结果数字；聊天数字无效。
- 所有结果句必须写“本合成仿真/留组实验”限定语，并保留证据标签。
- 不得写 CALCE 实测校准、外部验证、真实车辆精度、普适安全阈值、货币收益或 OOD 数值。
- 不得把 capacity_obs/resistance_obs 误写为外部实测；它们是合成观测。
- 未核验引用写 UNVERIFIED 或 EVIDENCE REQUIRED，禁止猜 DOI/作者/年份。
- 模板要求优先于通用论文模板；格式缺口只向人提问，不自行推断。

完成四块后停止，等待总负责人确认配置和大纲，再进入逐节写作。
~~~

## 8. 最终交稿前验收

- [ ] 摘要、正文、图表、结论中的数字全部能回指 F1-F6 或对应结果文件。
- [ ] 每个问题都有假设、模型、实验、指标、结果和限制，且没有把仿真写成实测。
- [ ] GroupKFold(cell_id)、右删失、OOD/ABSTAIN 和协议不可辨识均被准确描述。
- [ ] 图注包含工况/数据类型/seed 或折分；图号与在线文档一致。
- [ ] 引用通过 DOI/官方来源核验；正文与参考文献无孤儿；未知来源显式标记。
- [ ] 包含限制、数据可得性、作者贡献、利益冲突、经费和 AI 使用披露。
- [ ] 最终版本由总负责人做 G6 红队复核后才进入 PDF/支撑材料打包。

## 9. 不要做的事

- 不要把论文草稿、模板副本或聊天记录当作 GitHub 事实源。
- 不要直接编辑 study_output、g1_output 或配置来“让数字好看”。
- 不要删除失败记录、限制、UNCERTAIN 或 OOD/ABSTAIN 标签。
- 不要在没有人工核验的情况下新增文献或声称“已查证”。
- 不要在同一电芯记录上随机拆分训练/测试。

需要扩展研究或替换真实数据时，先回到总控台的停止规则，由建模负责人提交新 commit，再重新生成事实表。
