# G2 总负责人验收记录

**验收时间**：2026-08-12 08:35 CST（总负责人复跑核验）
**输入材料**：`handoffs/G2_TASK_DISPATCH.md`、`handoffs/A2_prediction_package.md`、
`configs/study_pipeline.json`、`study_output/run_manifest.json`（旧基线）与
`study_output_rerun/`（本次复跑产物）、`technical/PAPER_WRITING_FACT_SHEET.md`、
`docs/Simulation_Protocol.md`、`evidence/parameter_ledger.txt`、`evidence/source_ledger.txt`、
`code/battery_study/`（q1–q4）、`code/tests/test_study.py`
**复跑环境**：分支 `main` @ `4d69c9a`；`.venv`（Python 3.11.9、numpy 2.4.5、
scipy 1.17.1、scikit-learn 1.8.0，与 `run_manifest.json` 记录一致）
**结论**：`PASS_WITH_LIMITATIONS`（与 A2 自报一致；"LIMITATIONS"指科学证据边界，不指代码失败）

## 1. 结论解释

G2 阶段辨识（Q1）与寿命预测（Q2）证据包已达到 G2 任务书第六节全部 5 道验收门：
公式/边界、电芯级留组划分、删失诚实性、产物互相一致、外部验证隔离、标签区分
**全部 PASS**（详见第 2 节）。本记录由总负责人**亲自复跑**得出，不是沿用建模手自述。

`PASS_WITH_LIMITATIONS` 的"LIMITATIONS"边界与 A2 一致：
- 全部 Q1/Q2 数字来自**合成数据上的留组模型比较**，不是实测校准或外部验证；
- 80% SOH 仅是 `[ASSUMED][UPDATEABLE]` 建模终点，不是普适安全阈值；
- structure-matched ceiling 是 simulator ceiling，不构成生成器正确性或真实泛化的证据；
- 删失处理（43 事件 + 65 右删失）诚实入账；90% 覆盖为经验值（名义/事件混合校准），
  是"报告值"而非"保证值"。

## 2. 五项验收结论

| 验收问题 | 状态 | 依据与结论 |
|---|---|---|
| Q1/Q2 公式、边界与阈值是否遵守仿真协议与参数台账；`critical_soh=0.8` 是否仅作 `[ASSUMED][UPDATEABLE]` 建模终点 | `PASS` | `q2.py` AFT 用删失对数似然（`log_ndtr` 右删失项）+ L-BFGS-B，公式与 `Simulation_Protocol.md` 一致；参数取值均在 `parameter_ledger.txt` 冻结边界内；`q2_summary.json` 中 `rul_endpoint.status = "[ASSUMED][UPDATEABLE] modeling endpoint"`、`threshold=0.8`，未写成普适安全阈值。 |
| 数据划分是否以电芯为单位、5 折零重叠；RUL 删失处理是否诚实（43 事件 + 65 右删失、删失矛盾率、90% 覆盖为经验值） | `PASS` | `q2_split_audit.json` 5 折 `cell_overlap=[]` 全空，折内训练 86/87 电芯、测试 21/22 电芯零重叠（`split_integrity.cell_overlap_all_folds=0`）；`q2_rul_metrics.csv` AFT 行 `n_observed_events=43`、`n_right_censored=65`、`censored_early_failure_contradiction_rate=0.0`、`event_interval_90pct_coverage=0.9070`；覆盖率按事件区间经验计算并明确"reported not assumed"（`q2_summary.json` 原文）。 |
| CSV/字典/图/配置/seed/哈希/运行命令是否互相一致（对照 `study_output/run_manifest.json` 与 `technical/PAPER_WRITING_FACT_SHEET.md` F1–F4） | `PASS` | 复跑 `PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output_rerun`（54s）→ 9 道 `validation_gates.json` 全 PASS；F1–F4 论文级数字新旧产物**完全一致**（F1 108 电芯/108000 行、F2 72 可检测/36 右删失/13.4 EFC、F3 ridge RMSE=0.004206、F4 AFT 38.39/0.9070/矛盾 0.0/43+65）；seed 20260811 + q4 五种子一致；14/32 产物字节级一致（LF 归一化），其余 18/32 仅为 numpy/BLAS 浮点尾数级微差（如 AFT RMSE 38.39115 vs 38.39039，~1e-3），不影响任何论文可写数字。 |
| 是否与外部验证隔离：无 CALCE/NASA 实测数据混入拟合；ceiling 模型是否仅作 simulator ceiling 不作外部验证 | `PASS` | grep 全 `code/battery_study/` 无 `read_csv/loadtxt/urlopen/requests/.mat` 等外部读取（仅 reporting.py 文档性提及"未读取或拟合 CALCE 原始循环数据"）；`g1_generator` 无反向 import `battery_study`；`run_manifest.json` scope=`synthetic NMC study; no external calibration or validation`；`q2_rul_metrics.csv` 中 `structure_matched_simulation_ceiling` 单独成行且 `q2_summary.json` 注明"reuses the simulator functional form and is not evidence of real-world generalization"。 |
| A2 是否明确区分 `OBSERVED` / `LITERATURE_FIXED` / `ASSUMED` / `RESULT`，并列出限制与"未完成"项 | `PASS` | A2 写作边界节明确：`[RESULT]` 只能称"仿真留组性能"；structure-matched 是 simulator ceiling；80% SOH 是 `[ASSUMED][UPDATEABLE]` 终点；`q2_summary.json` 单独列出 `interpretation_limits`（5 条，含"结构匹配 ceiling 不作外部验证"、"ridge/RF 对照为删失朴素"、"leave-condition-out 仅限冻结支持域内"）；未完成项（无真实 CALCE 数据、无外部验证）已在 A2 与 `run_manifest.json` `uncertainty_status` 如实列出。 |

## 3. 复跑关键证据

**测试**：`PYTHONPATH=code python -m pytest code/tests -q` → **56 passed**（G1 41 + G2–G4 15），10.9s。

**复跑命令**（与 `run_manifest.json` 一致）：

```text
PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output_rerun
```

**复跑产物**：`study_output_rerun/`（27 文件 + run_manifest）：
- `validation_gates.json`：**9 门全 PASS**（factorial_shape、q1_weights×2、q1_protocol_honesty、
  q2_cell_group_split、q2_censor_accounting、q3_milp_constraints、q4_ood_abstention、q4_seed_completeness）
- 图 6 张：fig_q1_factor_weights / fig_q2_soh_rmse / fig_q2_rul_rmse / fig_q3_tradeoff /
  fig_q4_final_soh / fig_q4_sensitivity
- 文档 9 份（A2–A4 证据包等，由 `reporting.write_all` 生成）

**论文级数字核验（F1–F4 新旧一致）**：

| 事实 | 值 | 判定 |
|---|---|---|
| F1 全因子 | 27 工况 / 108 电芯 / 108000 行 | ✅ |
| F2 膝点 | 72 可检测 / 36 右删失 / 恢复误差中位 13.40 EFC | ✅ |
| F3 SOH | 最优 ridge，RMSE=0.004206 | ✅ |
| F4 RUL | AFT 事件 RMSE=38.39，90% 覆盖=0.9070，删失矛盾率=0.0000，43 事件+65 右删失 | ✅ |

**哈希说明**：磁盘 `study_output/`（CRLF）与 manifest（LF）哈希不同的原因是
`git autocrlf=true` 检出行尾符，LF 归一化后 32/32 与 manifest 一致；本次复跑
产物 14/32 字节级一致，其余为浮点尾数级环境微差，非内容差异。

## 4. 进入 G3/G4 与论文整合的硬性要求

- **论文主笔**：Q1/Q2 全部数字必须标注"仿真留组性能"；不得写"实测验证/外部验证/
  CALCE 实测校准成功/真实安全概率"；80% SOH 只能作为建模终点表述；未打开全文
  核验的 A2 候选文献不得作为已验证引用。
- **G3/G4 建模**：梯次筛选/编组与鲁棒性分析继续以 G1 冻结输入为唯一数据源；
  门槛与权重保持 `[ASSUMED][UPDATEABLE]`；OOD 弃权不得被绕过。
- **复现性**：G2 之后所有产物继续记录配置、seed、运行命令与文件 SHA-256；
  建议补 `.gitattributes` 对 `/study_output/*` 的 `eol=lf` 规则，避免提交/检出
  后哈希"过期"（本次已确认 CRLF 是哈希漂移唯一原因）。
- **停止规则**：G2 验收通过后进入 G5 论文数字/图冻结，不再新增模型范围。

## 5. 当前状态

`G2 APPROVED FOR G3/G4 & G5`（带上述条件）。Q1/Q2 证据链（A2 + study_output +
validation_gates + F1–F4）达到冻结条件。本记录不代表任何实测校准或外部验证已完成；
`structure_matched_simulation_ceiling` 仅作生成器自检上限，不构成外部验证。
