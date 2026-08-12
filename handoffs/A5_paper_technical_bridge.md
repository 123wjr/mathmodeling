# A5 论文技术过渡包

**状态**：`READY_FOR_DRAFT_WITH_LIMITATIONS`；论文草稿仍为 `CANDIDATE_DRAFT / NOT_READY_FOR_STAGE_2_5_PASS`

**Owner**：总负责人；论文主笔负责按本包填充 `../论文草稿.md`，再同步在线文档。

## 事实锁定

| 项 | 值 |
|---|---|
| 论文唯一可编辑源 | `../论文草稿.md` |
| 外部格式参考 | 人工确认 DOCX，SHA-256=`55468c073dc248dacbd91f84f06cc4070a99acbccba913907ad6efc57a6eddff`；仅作比较，不要求 Agent 读取 |
| 桥接文档 | `../technical/PAPER_TECHNICAL_BRIDGE.md`；与草稿逐节对齐 |
| 技术过渡文档 | `../technical/PAPER_TECHNICAL_BRIDGE.md` |
| 技术过渡文档 SHA-256 | `a609508263d468882ca6ce994aa496b3792aa3139f0170ebfa1943d6861fd66b` |
| 生成结果事实源 | `study_output/run_manifest.json` + `study_output/*.csv/*.json` |
| 当前范围 | NMC 合成仿真；Q1-Q4；支持域 25--50 degC、0.5--2C、DOD 50--100%、CC-CV |
| 最近运行验证 | 9/9 validation gates PASS；`python -m pytest code/tests -q`：56 passed |

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

1. `论文草稿.md` 到在线文档副本的同步及图号固定：`PENDING_PAPER_AGENT`。
2. 外部文献全文、页码/表号人工核验：`PENDING_HUMAN_VERIFICATION`。
3. CALCE 实测拟合、NASA 外部验证、OOD 数值、完整储能拓扑/货币收益：`NOT_DONE` 或 `PAPER_GAP`。
4. Q4 对 Q3 同一已选编组的纵向压力验证：`NOT_DONE`；当前是每场景重新生成、筛选和编组。
5. Stage 2.5 完整性闸门：`NOT_READY_FOR_STAGE_2_5_PASS`；引用核验与早期框架锁定尚未闭环。

## 必须保留的限制

- 未下载/解析/拟合 CALCE 原始循环数据；不得写实测校准。
- NASA 未进入当前实验；不得写已完成外部对照。
- Q3 是 4 芯 module-level set-packing；没有完整串并联储能阵列拓扑。
- Q3 RUL 使用 cycle=300 landmark 预测换算到 cycle=750，不是 750 在线重估。
- 低温、过充、过放和 3C 只弃权，不给数值。
- Q4 场景结果不是对 Q3 同一组电芯的纵向验证，不得写“已有编组验证通过”。
- 门槛、权重、无量纲成本收益和 80% SOH 终点均可更新。

## 交接动作

论文主笔只需：

1. 以 `../论文草稿.md` 为编辑骨架，按 `../technical/PAPER_TECHNICAL_BRIDGE.md` 第 2.0 节逐节填充，再同步在线文档。
2. 每个结果句回填主张-证据表；未核验文献保留 `EVIDENCE_REQUIRED`。
3. 删除模板示例、无关参考文献和示例代码；不编辑代码、CSV、JSON、SVG。
4. 回报正文章节、已回指数字/图数、人工核验引用数和剩余阻塞。

复跑命令：

```bash
PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output
python -m pytest code/tests -q
```

## 最后验证记录

```text
pipeline: 9 validation gates PASS
pytest: 56 passed
manifest artifacts: 43（含 A5 bridge + A5 handoff）
deterministic rerun: 连续两次 manifest 逐字节一致；43/43 artifact 哈希一致
git baseline before run: cc135c17ecaaaded4263a25416322fde676c81d6
```
