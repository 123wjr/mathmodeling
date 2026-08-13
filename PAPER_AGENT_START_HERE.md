# A题论文 Agent 入口

> 适用对象：负责论文的主笔及其 Agent。`论文初稿.md` 是当前 Git 编辑骨架；`论文草稿.md` 仅保留历史，不再编辑。在线文档是协作/提交副本。代码、配置、实验输出和技术证据保存在 GitHub。
>
> 基线不固定 commit。每次启动先执行 git pull --ff-only origin main，再以 git rev-parse --short HEAD 的输出作为本次读取基线。

## 0. 任务定义

题面是 [试题 A.pdf](试题%20%20A.pdf)：锂电池剩余寿命预测与梯次利用筛选优化。论文要回答四个问题：

1. 性能退化特征与影响因子辨识。
2. SOH 评估与 RUL 预测。
3. 退役筛选与储能编组多目标优化。
4. 多工况仿真、鲁棒性分析与仿真条件下的触发规则。

本仓库当前交付的是一条可复跑的 NMC 合成仿真研究链，不是 CALCE 实测校准报告。论文的目标是把“题面问题 → 假设 → 模型 → 实验 → 条件化结论”讲成一条可审计的证据链。

如果 Agent 环境提供 academic-research-suite，使用 academic-paper 的 plan 模式完成配置和论证，再依次进入 outline、draft、citation-check、peer-review；没有完成配置确认和大纲确认时，不进入整篇正文生成。

## 1. 你先做什么

在仓库根目录执行：

~~~bash
git pull --ff-only origin main
git rev-parse --short HEAD
git status --short --branch
~~~

然后按以下顺序阅读。不要跳过前四项，也不要先从 study_output/*.csv 猜结论。论文以下载版 DOCX 的栏目骨架为参考，但内容编辑以仓库内 `论文初稿.md` 为准。

| 顺序 | 文件 | 你要得到的内容 |
|---:|---|---|
| 1 | [试题 A.pdf](试题%20%20A.pdf) | 原题、四个问题和题面约束；题面是问题定义的事实源 |
| 2 | [论文初稿.md](论文初稿.md) | 最新 G12/V2 对齐骨架；Q3/Q4 仍需按 V3 整体替换，数字必须回指证据 |
| 3 | 外部 DOCX 格式参考（SHA-256=`55468c073dc248dacbd91f84f06cc4070a99acbccba913907ad6efc57a6eddff`） | 可选的格式/栏目比较记录；不是仓库接口，不要因本机路径不可用而中断 |
| 4 | [handoffs/PROJECT_COMMAND_CENTER.md](handoffs/PROJECT_COMMAND_CENTER.md) | 当前闸门、责任人、截止时间、停止规则和唯一事实源顺序 |
| 5 | [technical/PAPER_WRITING_FACT_SHEET.md](technical/PAPER_WRITING_FACT_SHEET.md) | 论文可直接使用的数字及 CONFIRMED/RESULT/UPDATEABLE 标签 |
| 6 | [technical/PAPER_TECHNICAL_BRIDGE.md](technical/PAPER_TECHNICAL_BRIDGE.md) | 与 `论文初稿.md` 章节对齐的技术填充层；逐问列出模型、实验、数字、限制和证据 |
| 7 | [technical/TECHNICAL_REPORT_MINIMAL.md](technical/TECHNICAL_REPORT_MINIMAL.md) | 假设、公式、实验设计、结果解释和四部分最小技术文档 |
| 8 | [technical/V3_VALIDATION_REPORT.md](technical/V3_VALIDATION_REPORT.md) | 12 个 V3 自动闸门、统计完整性和不能声称的内容 |
| 9 | [A1](handoffs/A1_simulation_package.md)、[A2](handoffs/A2_prediction_package.md)、[A3](handoffs/A3_optimization_package.md)、[A4](handoffs/A4_robustness_package.md) | 每个阶段的接口、限制和证据路径 |
| 10 | [study_output/run_manifest.json](study_output/run_manifest.json) | 源码/配置/产物 SHA-256 和生成时的 Git HEAD；用于最终回检 |
| 11 | [V2 真实数据候选报告](technical/V2_REAL_DATA_CANDIDATE_REPORT.md) | 独立 Zenodo NMC532/NMC811 候选层；当前 `NEEDS_CHANGES/HOLD_FOR_PAPER`，禁止引用或覆盖 V1 |
| 12 | [V2 技术方案](technical/TECHNICAL_SOLUTION_V2.md) | V2 历史技术层；`论文初稿.md` 已对齐其可写边界，候选数字仍 HOLD |
| 13 | [V3 技术方案](technical/TECHNICAL_SOLUTION_V3.md) | cycle=750 条件 RUL、双决策 MILP、稳定性/消融、固定编组压力追踪；按第 0 节逐节替换 V1 的 Q3/Q4 口径 |
| 14 | [V3 验证报告](technical/V3_VALIDATION_REPORT.md) | 12 个自动闸门、当前可写 V3 数字、删失与外部效度边界；精确证据在 `study_output_v3/` |

technical/EXPERIMENT_PLAN.md 可用于补写方法和实验小节；technical/SUPPORTING_MATERIALS_README.md 说明支撑材料如何复跑。

模板处理硬规则：先读 `technical/PAPER_TECHNICAL_BRIDGE.md` 第 2.2 节的 DOCX 冲突登记，再以第 2.0 节的草稿逐节映射为执行清单。DOCX 只作格式比较；不因本机绝对路径、仓库同名旧版本或在线文档访问问题而中断。

先做 Markdown 与技术桥接文档的逐节对齐审计，再直接编辑 `论文初稿.md`；不编辑代码、CSV、JSON、SVG。

## 2. 事实源优先级

发生冲突时按这个顺序裁决，低优先级内容不能覆盖高优先级内容：

1. 总负责人签署的闸门结论和 .codex/DECISIONS.md。
2. 已验收的 A0-A5 证据包与总控台。
3. technical/PAPER_WRITING_FACT_SHEET.md、study_output/*.json/csv、验证闸门和 manifest。
4. 可复跑代码、配置和图表。
5. `论文初稿.md` 中尚未回指的文字、在线文档副本、Agent 汇报和聊天内容。

题面只定义研究问题，不提供实验数字。任何“聊天中出现过但文件中找不到”的数字都视为不可用。

## 3. 证据标签与硬边界

每个结果性句子在写入 `论文初稿.md` 前，先在证据表中登记：claim_id、原句、标签、来源文件、精确字段/行或图号、核验人/日期、核验状态。

| 标签 | 可以怎么写 | 不能怎么写 |
|---|---|---|
| CONFIRMED | 题面、代码、配置或可复跑结构已确定的事实 | 把结构事实扩展成真实世界效果 |
| RESULT | “在本合成仿真/留组实验中……”并给出回指 | “实测证明”“真实车辆精度” |
| ASSUMED + UPDATEABLE | 明确是自设参数、阈值、代理或权重，并说明可替换 | 写成 CALCE 实测估计、行业标准或安全规范 |
| UNCERTAIN | 明确列为未知或限制 | 用常识、模型输出或 Agent 猜测填空 |
| OOD/ABSTAIN | 说明支持域外弃权、不给数值 | 从趋势图外推低温、过充、过放、3C 或安全概率 |
| PAPER_GAP | 明确写为当前技术链未覆盖，或补做后再更新 | 用论文措辞、常识或相邻场景结果伪装成已完成 |
| EVIDENCE_REQUIRED | 保留标记，等待人工全文与页码核验 | 猜作者、DOI、页码，或把候选来源写成已核验 |

当前不可越过的科学边界：

- 所有 G1-G4 数字来自合成数据；没有读取或拟合 CALCE 原始循环数据。
- V2 候选层已读取 Zenodo NMC/Graphite 容量循环，但当前仍是 `HOLD_FOR_PAPER`；只能写归一化容量的来源特定候选验证，不能把它改名为 CALCE 或绝对容量实测结果。
- V2 的 `run_status=PASS` 只表示代码运行成功；必须同时检查 `evidence_status` 和 `paper_eligible`。当前两套口径均为 `HOLD_RPT_SENSITIVITY`、`paper_eligible=false`，不得进入论文数字表。
- 支持域为 25--50 degC、0.5--2C、DOD 50--100%、CC-CV；协议效应不可辨识。
- 80% SOH 是建模终点/筛选阈值，不是普适安全阈值。
- 不写真实车辆泛化、货币收益、真实安全失效概率或范围外寿命。
- 结构匹配 RUL 是 simulator ceiling，不能反向证明生成器真实有效。

题面覆盖状态必须如实保留：Q1 的 CC-CV 协议效应不可辨识；Q2 的低温/过充/过放/>2C 只弃权；Q3 仅完成 4 芯 module-level set-packing，没有阵列拓扑/货币损耗。V1 的 Q3 使用 cycle=300 寿命换算、Q4 每场景重新筛选/编组；V3 已新增 cycle=750 条件 RUL 和固定同一编组的纵向压力追踪。论文采用 V3 时必须整体替换这两处旧口径，不能混用 V1 数字与 V3 方法。

## 4. 当前 V3 临时交付口径

当前 V3 已通过代码与产物闸门，可用于搭建论文大纲、模型方程、实验设计、表格结构和限制段。团队仍会补强参数依据与真实观测偏差说明，因此本节数字均视为 `RESULT_CANDIDATE_UPDATEABLE`：可以写入带证据标签的工作稿，不得进行最终润色、删除标签或冻结摘要/结论。后续以新 commit 的事实表和 manifest 覆盖。

以下数字必须保留标签和限定语；更详细的定义以事实表和对应 CSV/JSON 为准。

| ID | 可写事实 | 标签 | 回指 |
|---|---|---|---|
| F1 | 27 工况、108 电芯、108000 行、每芯 1000 cycles | CONFIRMED | study_output/factorial_design.csv |
| F2 | 72 个膝点可观测、36 个右删失；内部膝点恢复误差中位数 13.40 EFC | RESULT 仿真自检 | study_output/q1_knee_detection.csv |
| F3 | 50-cycle SOH 的 Ridge RMSE=0.004206，cell-bootstrap 90% CI=0.003962--0.004447 | RESULT 仿真留组 | study_output/q2_soh_metrics.csv |
| F4 | RUL 为 43 个事件 + 65 个右删失；log-normal AFT 事件 RMSE=38.39 cycles，90% 区间覆盖=0.9070 | RESULT 仿真留组 | study_output/q2_rul_metrics.csv |
| F5 | cycle=750 风险集 92 芯：27 事件、65 右删失；750 前排除 16 芯 | RESULT 仿真留组 | study_output_v3/q3_retirement_summary.json |
| F6 | 条件 RUL 事件 RMSE=39.7665 cycles；嵌套留组校准区间经验覆盖=0.8889 | RESULT 仿真留组；不是 90% 保证 | study_output_v3/q3_retirement_summary.json |
| F7 | POINT 入选 89 芯、INTERVAL_RISK 入选 41 芯；均选 8 个四芯组（区间宽度门槛=3000 cycles，可更新） | RESULT + UPDATEABLE | study_output_v3/q3_decision_comparison.csv、configs/study_pipeline_v3.json |
| F8 | 45 行 OAT 稳定性扫描；入选率=0.1489--0.3511，Jaccard=0.5714--1.0000；44/45 参数点不可行 | RESULT + UPDATEABLE | study_output_v3/q3_stability_sweep.csv、q3_stability_summary.json |
| F9 | Q2 消融 48 个配置；Q4 固定同一 8 组跨 5 场景追踪，cycle 750 连续；16/40 稳定、5/40 复检、19/40 强制拒绝 | RESULT + CONFIRMED | study_output_v3/q2_ablation_metrics.csv、q4_fixed_group_summary.csv |

写数字时同时写三件事：数据是仿真、验证如何分组、结论适用范围。例如：

> 在本合成数据的 GroupKFold(cell_id) 留组实验中，Ridge 的 50-cycle SOH RMSE 为 0.004206；该数值不代表真实电芯或车辆精度。

## 5. 推荐论文骨架

竞赛模板优先于通用 IMRaD；下面的内容顺序可映射到模板栏目，不要为了套期刊格式改变题目要求：

1. 摘要、关键词：问题、方法链、最重要的条件化结果、限制。V2 数字只有在 `technical/V2_REAL_DATA_CANDIDATE_REPORT.md` 由总负责人放行后才能进入摘要或正文。
2. 问题重述与符号说明：只引用题面；列出 cycle/EFC、SOH、RUL、DOD、倍率、温度和删失符号。
3. 模型假设与数据生成：NMC 主线、分段平方根退化、工况边界、个体差异、噪声和标签。
4. 问题一：阶段/膝点定义、主效应权重和协议不可辨识说明。
5. 问题二：SOH 特征、GroupKFold、右删失 AFT、对照模型、区间覆盖和压力测试。
6. 问题三：cycle=750 条件 RUL、点/区间风险门、set-packing MILP 和 5 seed OAT 稳定性。
7. 问题四：固定同一 8 组的多工况压力追踪、删失感知变化、OOD/ABSTAIN 和触发规则。
8. 模型评价、局限与推广：区分仿真内一致性、统计不确定性和真实外部有效性。
9. 结论与工程建议：只写支持域内、可回指的结论；给出需要真实数据后更新的项。
10. 参考文献、附录/支撑材料：参数台账、运行命令、图表索引和 AI 使用披露。

## 6. Agent 工作协议

### 阶段 A：启动与配置（必须先完成）

先建立 Paper Configuration Record，至少确认：

- 论文类型：数学建模竞赛论文/会议型短文（以模板为准）。
- 正文语言、摘要语言、目标字数/页数、引用格式。
- 三位作者与贡献；无经费/无利益冲突也要显式记录。
- 当前 `论文初稿.md` 版本、在线文档链接（如有）、模板限制。
- 是否已有人工核验的参考文献；没有就不要假装已有文献库。

配置不完整时，Agent 只问缺失项，不直接生成整篇论文。

### 阶段 B：证据台账（先于正文）

建立与当前 `论文初稿.md` 版本配套的“主张-证据表”，推荐字段：

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
- 图表编号先在 `论文初稿.md` 中占位，再同步在线文档；本轮不冻结最终图号，改图后同步更新图注和证据表。

### 阶段 E：引用与诚信审查

引用只接受 DOI、出版社/期刊官网、官方数据页或可人工核验的原文。禁止编造作者、年份、卷期、页码和 DOI。正文引用与参考文献必须双向零孤儿；无法核验的来源标 UNVERIFIED，不用于关键结论。

当前 A5 预审为 `NOT_READY_FOR_STAGE_2_5_PASS`：`论文初稿.md` 中候选文献尚未逐条完成全文、页码与主张范围核验，参数依据与观测偏差补强也未闭环。可以继续搭建 V3 大纲和方法段，但不得标记为完整性通过或最终完整题解。

### 阶段 F：交接报告

每次交接使用总控台的六行协议：

~~~text
状态：DONE / IN_PROGRESS / BLOCKED
Owner：论文主笔 Agent / 论文主笔
产物：`论文初稿.md` 版本/commit + 章节/证据表版本 + 在线文档链接（如有）
验证：事实表条目数；已回指数字/图数；人工核验引用数
阻塞：缺失信息 + 等谁决定；无则 NONE
下一步：动作 + CST 截止
~~~

## 7. 可直接复制给论文 Agent 的启动提示

~~~text
你是 A 题数学建模论文主笔 Agent。你的内容编辑目标是仓库根目录的 `论文初稿.md`；`论文草稿.md` 只作历史参考，不得编辑。编辑完成后再同步在线文档。不修改代码或数字证据。

工作目录：仓库根目录。先只读，不写正文、不改 CSV/JSON/SVG、不运行会覆盖结果的命令、不提交 Git。

按顺序阅读：
1. PAPER_AGENT_START_HERE.md
2. 试题  A.pdf
3. `论文初稿.md`（当前 Git 编辑骨架，已对齐 V2）
4. handoffs/PROJECT_COMMAND_CENTER.md
5. technical/PAPER_WRITING_FACT_SHEET.md
6. technical/PAPER_TECHNICAL_BRIDGE.md
7. technical/TECHNICAL_REPORT_MINIMAL.md
8. technical/V3_VALIDATION_REPORT.md（V3 当前验收；V1 历史报告仅作对照）
9. handoffs/A1_simulation_package.md、A2_prediction_package.md、A3_optimization_package.md、A4_robustness_package.md
10. study_output/run_manifest.json
11. technical/V2_REAL_DATA_CANDIDATE_REPORT.md
12. technical/TECHNICAL_SOLUTION_V2.md
13. technical/TECHNICAL_SOLUTION_V3.md
14. technical/V3_VALIDATION_REPORT.md
15. study_output_v3/run_manifest.json

第一轮只输出四块（优先使用技术过渡包和 V3 技术方案的章节与证据索引，不从单个 CSV 猜结论）：
A. 已读文件清单与当前 HEAD；
B. Paper Configuration Record（缺失项留空并列问题）；
C. 主张-证据表（每个数字/比较/因果句一行）；
D. 论文大纲，逐节标出模型、实验、结果、限制和证据路径。

硬规则：
- 只从 PAPER_WRITING_FACT_SHEET.md 和对应 study_output 文件取结果数字；聊天数字无效。
- Q3/Q4 只使用 `study_output_v3/` 当前口径；V1 的 85/108、3167 组和场景重优化数字仅作历史对照，不得与 V3 方法混用。
- `study_output_v3/run_manifest.json` 必须验证为 PASS；若失效则暂停复制 V3 数字并回报总负责人。
- 所有结果句必须写“本合成仿真/留组实验”限定语，并保留证据标签。
- 不得写 CALCE 实测校准、外部验证、真实车辆精度、普适安全阈值、货币收益或 OOD 数值。
- 不得把 capacity_obs/resistance_obs 误写为外部实测；它们是合成观测。
- 未核验引用写 UNVERIFIED 或 EVIDENCE REQUIRED，禁止猜 DOI/作者/年份。
- 模板要求优先于通用论文模板；格式缺口只向人提问，不自行推断。

完成四块后，直接在 `论文初稿.md` 中建立 V3 大纲、方法段、表图占位和限制段。当前数字保留 `RESULT_CANDIDATE_UPDATEABLE` 标记；不要做最终摘要、结论、图号和措辞冻结。等待建模负责人下一 commit 后再核对数字并收尾。在线文档只是同步副本。
~~~

### V2 增量更新提示（配置和大纲已确认后使用）

~~~text
只编辑 `论文初稿.md`，不得修改代码、CSV、JSON 或 SVG。

先读取 `technical/PAPER_TECHNICAL_BRIDGE.md` 第 1.1 节，再读取
`technical/V2_REAL_DATA_CANDIDATE_REPORT.md`。按三态更新：

1. `[已确定/CONFIRMED]`：只把数据来源、规模、分层方法、缺失字段和当前 HOLD 判定写入 1.2、6.2、6.3；每个新增段落末尾保留 `[已确定/CONFIRMED]` 内部编辑标记和“未进入主结果”的限制。
2. `[可能更新/UPDATEABLE]`：在 5.1.3、5.2.3 插入 `V2_UPDATEABLE` Markdown 注释，不写候选数字。
3. `[暂缓写入/HOLD]`：V2 RMSE、相对改善、膝点和覆盖率不得进入摘要、结果表、图注或结论；不得写成 CALCE 校准或外部验证。

只有 `evidence_status` 不再为 HOLD、`paper_eligible=true` 且总负责人批准三项同时满足，才可替换占位。内部标签只在总负责人终审后统一隐藏或删除，论文 Agent 不得提前清理。完成后只汇报：修改章节、CONFIRMED 主张、UPDATEABLE 占位、HOLD 清单；不要提交或推送。
~~~

## 8. 最终交稿前验收

- [ ] 摘要、正文、图表、结论中的数字全部能回指 F1-F9 或对应结果文件；Q3/Q4 不采用 V1 历史数字。
- [ ] 每个问题都有假设、模型、实验、指标、结果和限制，且没有把仿真写成实测。
- [ ] GroupKFold(cell_id)、右删失、OOD/ABSTAIN 和协议不可辨识均被准确描述。
- [ ] 图注包含工况/数据类型/seed 或折分；`论文初稿.md` 与在线文档副本的图号一致。
- [ ] 引用通过 DOI/官方来源核验；正文与参考文献无孤儿；未知来源显式标记。
- [ ] 包含限制、数据可得性、作者贡献、利益冲突、经费和 AI 使用披露。
- [ ] 最终版本由总负责人做 G6 红队复核后才进入 PDF/支撑材料打包。

## 9. 不要做的事

- `论文初稿.md` 是当前编辑骨架，但不是数字证据源；所有结果必须回指技术桥接文档和 `study_output/`。
- 不要直接编辑 study_output、g1_output 或配置来“让数字好看”。
- 不要删除失败记录、限制、UNCERTAIN 或 OOD/ABSTAIN 标签。
- 不要在没有人工核验的情况下新增文献或声称“已查证”。
- 不要在同一电芯记录上随机拆分训练/测试。

需要扩展研究或替换真实数据时，先回到总控台的停止规则，由建模负责人提交新 commit，再重新生成事实表。
