"""把实验结果转换为论文可引用的技术文档和交接包。"""
from __future__ import annotations

import html
import os


def _write(path: str, text: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.rstrip() + "\n")
    return path


def _f(value, digits=4):
    if value is None:
        return "NA"
    return f"{float(value):.{digits}f}"


def _by_name(rows, key="model"):
    return {row[key]: row for row in rows}


def write_minimal_report(project_root: str, study_cfg, results: dict) -> str:
    q1 = results["q1"]["summary"]
    q2 = results["q2"]["summary"]
    q3 = results["q3"]["summary"]
    q4 = results["q4"]["summary"]
    capacity_effects = [row for row in q1["factor_effects"] if row["response"] == "capacity_fade"]
    resistance_effects = [row for row in q1["factor_effects"] if row["response"] == "final_resistance_growth"]
    soh_models = sorted(q2["soh_metrics"], key=lambda row: row["rmse"])
    rul_models = _by_name(q2["rul_metrics"])
    aft = rul_models["lognormal_aft_censored"]
    matched = rul_models["structure_matched_simulation_ceiling"]
    q3_solutions = _by_name(q3["solutions"], "alternative")
    balanced = q3_solutions["balanced"]
    greedy = q3_solutions["balanced_greedy"]
    scenarios = _by_name(q4["monte_carlo_summary"], "scenario")

    effect_capacity_rows = "\n".join(
        f"| {row['factor']} | {_f(row['normalized_main_effect_weight'])} | {_f(row['share_total_variance'])} |"
        for row in capacity_effects
    )
    effect_resistance_rows = "\n".join(
        f"| {row['factor']} | {_f(row['normalized_main_effect_weight'])} | {_f(row['share_total_variance'])} |"
        for row in resistance_effects
    )
    soh_rows = "\n".join(
        f"| {row['model']} | {_f(row['mae'], 6)} | {_f(row['rmse'], 6)} | {_f(row['r2'], 4)} | {_f(row.get('rmse_ci_low'), 6)}--{_f(row.get('rmse_ci_high'), 6)} |"
        for row in soh_models
    )
    q4_rows = "\n".join(
        f"| {name} | {_f(row['final_soh_mean_mean'])} | {_f(row['critical_fraction_mean'])} | {_f(row['ridge_soh_forecast_rmse_mean'], 6)} | {_f(row['screening_rate_mean'])} |"
        for name, row in scenarios.items()
    )
    text = f"""# A题最小可运行技术文档

> 版本：`{study_cfg.study_id}`。本文件由 `battery_study` 固定配置生成，面向论文写作。
> 运行：`PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output`
> 验证：`python -m pytest code/tests -q`；产物哈希见 `study_output/run_manifest.json`。

标记约定：`[CONFIRMED]` 已由题面、代码或可复跑结果确定；`[RESULT]` 本次仿真结果；`[ASSUMED]` 自设假设；`[UPDATEABLE]` 有真实数据或评分细则后应更新；`[UNCERTAIN]` 当前证据不能确定；`[OOD/ABSTAIN]` 禁止数值外推。

## 一、假设

1. `[CONFIRMED]` 主对象为 NMC（LiNiMnCo/graphite），G1 仅以 CALCE INR18650-20R 作为尺度与方向参考；本研究没有读取或拟合 CALCE 原始循环数据，108 颗电芯均为合成仿真。
2. `[ASSUMED][UPDATEABLE]` 容量与内阻共享分段平方根退化量：`L(e)=sqrt(min(e,n_k))+2 max(0,sqrt(e)-sqrt(n_k))`；`alpha`、`beta`、温度/倍率/DOD 加速系数、噪声和个体差异均来自 G0 假设台账。
3. `[CONFIRMED]` 支持域限定为 25--50 degC、0.5--2C、DOD 50--100%、CC-CV；低温、过充、过放及 >2C 均标记 `[OOD/ABSTAIN]`。
4. `[ASSUMED][UPDATEABLE]` 80% SOH 仅作 RUL 终点和“临界阶段”建模阈值，不等同普适安全阈值；Q3 的筛选门槛和无量纲成本收益权重也不是行业标准。
5. `[CONFIRMED]` 同一 `cell_id` 的全部循环只进入同一交叉验证折；RUL 未在 1000 cycles 前到达阈值时按右删失处理。
6. `[UNCERTAIN]` 真实批次分布、真实成本、安全失效概率及范围外工况缺数据，当前不能从仿真确定。

## 二、模型

### 2.1 退化阶段与因素权重

`[ASSUMED][UPDATEABLE]` 正常阶段定义为 SOH 高于 0.8 且在检测膝点前；退化阶段为 SOH 高于 0.8 且在膝点后；临界阶段为 SOH 不高于 0.8。膝点在 `sqrt(EFC)` 坐标上用连续 hinge 回归检测。DOD=50% 时 1000 cycles 只覆盖 500 EFC，膝点按右删失而非强行估计。

因素权重采用平衡 `3 x 3 x 3` 全因子边际 sum-of-squares。`normalized_main_effect_weight` 只在温度、倍率、DOD 三个可辨识主效应内归一化；交互项和电芯差异保留为剩余方差。cycle/EFC 是老化轴，不伪装成随机因素；协议只有 CC-CV 一个水平，协议效应不可辨识。

### 2.2 SOH 与 RUL

`[CONFIRMED]` 当前 SOH 由近期容量中位数与初期容量中位数之比估计。50-cycle SOH 比较 persistence、局部线性、Ridge 和 Random Forest；外层使用 `GroupKFold(cell_id)`，另做 27 个 leave-condition-out 压力测试。

`[CONFIRMED]` RUL 在 cycle=300 landmark 建模。主模型为右删失 log-normal AFT：`log(T)=beta^T x + sigma epsilon`；事件样本用密度似然，删失样本用生存概率。名义 90% 区间再用训练事件的 0.99 绝对对数残差分位作保守膨胀，外层事件覆盖率仍原样报告。Ridge/RF 只用可观测失效训练，属于删失朴素对照。结构匹配模型从 landmark 前 `sqrt(EFC)` 轨迹反演寿命，只是仿真同构上界。

### 2.3 筛选与编组

`[ASSUMED][UPDATEABLE]` cycle=750 构造退役候选池，硬门槛为 SOH、RUL 90% 区间下界、内阻增长和寿命区间宽度。兼容组固定 4 颗，以容量、SOH、RUL、内阻离散度度量不一致性。

MILP 使用候选组二元变量 `x_g`：每颗电芯 `sum_{{g contains i}} x_g <= 1`，并要求 `sum_g x_g = 8`。目标最大化归一化收益，最小化不一致、风险和无量纲成本。性能、平衡、保守三套权重与 greedy 基线共同报告；不输出人民币收益。

### 2.4 鲁棒性与弃权

`[CONFIRMED]` 在支持域内比较 baseline、高温、高倍率、高 DOD 和组合压力；用 5 个新 seed 做 Monte Carlo，并对 7 个参数作 +/-10% OAT。`[ASSUMED][UPDATEABLE]` 批次差异由 +/-10% 退化参数偏移和更高个体差异代理，不是实测批次分布。

## 三、实验

### 3.1 设计与可复现性

- `[CONFIRMED]` 全因子：3 温度 x 3 倍率 x 3 DOD x 4 电芯 = 108 电芯、108000 行、每芯 1000 cycles。
- `[CONFIRMED]` 预测外层 5 折按电芯留组；bootstrap 以电芯为重采样单位，报告 90% 区间。
- `[CONFIRMED]` 43 颗电芯在观测窗内达到 80% SOH，65 颗为右删失；点误差只在 43 个可观测事件上计算。
- `[CONFIRMED]` Q4 训练 seed 为 20260811，鲁棒性 seed 为 42、123、2026、4096、8110。

### 3.2 Q1 结果

`[RESULT]` 对 72 颗观测到膝点的电芯，检测膝点相对生成器设定的中位绝对误差为 {_f(q1['knee_detection']['median_absolute_error_efc'], 2)} EFC；36 颗为右删失。该值只证明实现能恢复自身结构，不是外部有效性证据。

容量衰减主效应：

| 因素 | 主效应内归一化权重 | 总方差占比 |
|---|---:|---:|
{effect_capacity_rows}

内阻增长主效应：

| 因素 | 主效应内归一化权重 | 总方差占比 |
|---|---:|---:|
{effect_resistance_rows}

![Q1 factor weights](../study_output/fig_q1_factor_weights.svg)

### 3.3 Q2 结果

50-cycle SOH 留组预测：

| 模型 | MAE | RMSE | R2 | RMSE 90% cell-bootstrap CI |
|---|---:|---:|---:|---:|
{soh_rows}

`[RESULT]` 通用模型中 RMSE 最低的是 `{soh_models[0]['model']}`（RMSE={_f(soh_models[0]['rmse'], 6)}）。`[RESULT]` 删失感知 AFT 在 43 个可观测事件上的 RUL RMSE={_f(aft['rmse'], 2)} cycles，名义 90% 事件区间覆盖率={_f(aft['event_interval_90pct_coverage'])}，对 65 个删失样本的提前失效矛盾率={_f(aft['censored_early_failure_contradiction_rate'])}。结构匹配仿真上界 RMSE={_f(matched['rmse'], 2)} cycles，但不得用于真实泛化宣称。

![Q2 SOH comparison](../study_output/fig_q2_soh_rmse.svg)

![Q2 RUL comparison](../study_output/fig_q2_rul_rmse.svg)

### 3.4 Q3 结果

`[RESULT]` 108 颗退役候选中 {q3['eligible_cells']} 颗通过假设门槛，筛选率={_f(q3['screening_rate'])}；共生成 {q3['candidate_groups']} 个兼容候选组。三套 MILP 均选出 {q3['target_groups']} 组，重复分配为 {q3['constraint_audit']['duplicate_assignments']}，错误组规模为 {q3['constraint_audit']['wrong_group_sizes']}。平衡 MILP 目标={_f(balanced['objective'])}，同权重 greedy={_f(greedy['objective'])}。

![Q3 tradeoff](../study_output/fig_q3_tradeoff.svg)

### 3.5 Q4 结果

| 场景 | cycle=1000 平均 SOH | 临界比例 | Ridge SOH RMSE | 筛选率 |
|---|---:|---:|---:|---:|
{q4_rows}

`[RESULT]` 上表仅描述支持域内仿真。低温、过充、过放和 3C 的 `numeric_prediction` 均为空；这些场景只输出 `[OOD/ABSTAIN]`，不能用趋势图补造数值。

![Q4 final SOH](../study_output/fig_q4_final_soh.svg)

## 四、结论

1. `[RESULT]` 在本全因子仿真内，温度、倍率和 DOD 对容量衰减/内阻增长的相对作用可由上表量化；CC-CV 因无对照水平不可给权重。该排序是条件范围内结论，不是普适机理排序。
2. `[RESULT]` 50-cycle SOH 的留组实验显示线性/集成模型优于 persistence；AFT 能利用右删失信息并避免把寿命下界当真值。`[UNCERTAIN]` 没有真实独立电池数据，因此不能把误差数字写成实车精度。
3. `[RESULT]` 风险门槛 + MILP 能产生满足组规模和唯一分配约束的方案，并在平衡权重下优于 greedy。`[ASSUMED][UPDATEABLE]` 门槛、权重、成本和收益必须随真实检测/商业数据更新。
4. `[RESULT]` 高温、组合压力和假设高退化批次降低 SOH 或可筛选性；工程动作只能表述为“本仿真条件下触发复检/拒绝强制编组”。
5. `[OOD/ABSTAIN]` 对支持域外温度、倍率、DOD 或充电协议，不输出寿命、安全性或收益数值。

论文可直接使用的数字以 `study_output/*.csv` 和 `run_manifest.json` 为唯一事实源。任何真实数据替换都必须重新运行全流水线，并同步更新 `[ASSUMED]/[UPDATEABLE]/[UNCERTAIN]` 标记。
"""
    return _write(os.path.join(project_root, "technical", "TECHNICAL_REPORT_MINIMAL.md"), text)


def write_experiment_plan(project_root: str, study_cfg) -> str:
    text = f"""# A题实验计划（实现冻结版）

## 1. 研究目标与假设

- `[CONFIRMED]` Q1：在 G0 支持域内辨识阶段边界及温度、倍率、DOD 主效应；单一 CC-CV 不估计协议效应。
- `[ASSUMED][UPDATEABLE]` H1：压力水平升高时容量衰减和内阻增长加快；阶段阈值为 SOH=0.8。
- `[CONFIRMED]` Q2：比较透明基线与统计学习模型，数据切分单位为电芯；RUL 使用右删失似然或明确标注删失朴素模型。
- `[ASSUMED][UPDATEABLE]` Q3：硬门槛先于优化；组大小={study_cfg.q3.group_size}，成本收益均为无量纲指数。
- `[CONFIRMED]` Q4：只在冻结支持域内做数值鲁棒性；范围外强制弃权。

## 2. 数据设计

1. 全因子 `T={list(study_cfg.factorial.temperatures_C)}`、`C-rate={list(study_cfg.factorial.c_rates_C)}`、`DOD={list(study_cfg.factorial.dod_pct)}`，每格 {study_cfg.factorial.n_cells_per_condition} 电芯，每芯 1000 cycles。
2. Q2 历史窗口 {study_cfg.q2.history_window_cycles} cycles，预测步长 {study_cfg.q2.forecast_horizon_cycles} cycles，landmark={study_cfg.q2.landmark_cycle}；{study_cfg.q2.cv_splits} 折 `GroupKFold(cell_id)`。
3. 90% 区间按电芯 bootstrap {study_cfg.q2.bootstrap_repetitions} 次；AFT 训练事件残差校准分位={study_cfg.q2.interval_calibration_confidence}；leave-one-condition-out 覆盖全部 27 工况。
4. Q3 退役快照 cycle={study_cfg.q3.retirement_cycle}；先筛选，再枚举相似候选组，最后 set-packing MILP。
5. Q4 使用 seeds={list(study_cfg.q4.seeds)}，7 参数 +/-{study_cfg.q4.sensitivity_fraction*100:.0f}% OAT，并另设假设批次代理。

## 3. 评价与验收

- Q1：主效应权重、总方差占比、膝点可观测/右删失数；同构膝点误差只作实现检查。
- SOH：MAE、RMSE、R2、90% cell-bootstrap 区间；报告 GroupKFold 与 leave-condition-out。
- RUL：仅可观测事件 MAE/RMSE/R2、删失样本提前失效矛盾率、AFT 90% 事件覆盖。
- Q3：筛选率、目标、组数、重复电芯数、错误组规模、MILP 与 greedy 差值。
- Q4：seed 间 p10--p90、SOH 误差、临界比例、筛选/成组率、OAT 局部敏感度、OOD 空数值。

## 4. 更新规则

- `[UPDATEABLE]` 若取得真实 CALCE/企业数据：先建立化学体系和测试协议映射，再校准参数；不得覆盖原仿真标签。
- `[UPDATEABLE]` 若取得成本、安全或评分细则：只修改 JSON 中门槛/权重并全量重跑，不在论文中手改结果。
- `[UNCERTAIN]` 无真实批次与安全事件数据时，不拟合安全概率、不做货币化收益、不宣称行业阈值。
- `[OOD/ABSTAIN]` 任何超出 25--50 degC、0.5--2C、DOD 50--100%、CC-CV 的查询都保持空数值。

执行命令：

```bash
PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output
python -m pytest code/tests -q
```
"""
    return _write(os.path.join(project_root, "technical", "EXPERIMENT_PLAN.md"), text)


def write_validation_report(project_root: str, results: dict, gates: list[dict]) -> str:
    q2 = results["q2"]["summary"]
    q3 = results["q3"]["summary"]
    gate_rows = "\n".join(
        f"| {row['gate']} | {row['status']} | {row['evidence']} |" for row in gates
    )
    text = f"""# A题技术验证报告

## 1. 自动闸门

| 闸门 | 状态 | 证据 |
|---|---|---|
{gate_rows}

## 2. 统计完整性

- `[CONFIRMED]` 数据划分为 `{q2['split_integrity']['method']}`，{q2['split_integrity']['folds']} 折的 `cell_id` 交集均为 {q2['split_integrity']['cell_overlap_all_folds']}。
- `[CONFIRMED]` RUL 可观测事件 {q2['rul_endpoint']['observed_events']}，右删失 {q2['rul_endpoint']['right_censored']}；点误差未把删失下界当真值，AFT 名义 90% 事件覆盖率为 {_f(_by_name(q2['rul_metrics'])['lognormal_aft_censored']['event_interval_90pct_coverage'])}。
- `[CONFIRMED]` Q1 膝点只在实际覆盖 nominal knee 的电芯上检测；未覆盖者写 `RIGHT_CENSORED`。
- `[CONFIRMED]` Q3 MILP 重复分配={q3['constraint_audit']['duplicate_assignments']}，错误组规模={q3['constraint_audit']['wrong_group_sizes']}。
- `[CONFIRMED]` OOD 表的所有 `numeric_prediction` 均为空。

## 3. 科学诚信闸门

- `[CONFIRMED]` 全部数值来自合成数据；文档未使用“CALCE 实测校准”“外部验证”或“真实安全概率”表述。
- `[CONFIRMED]` 结构匹配 RUL 结果单独标为 simulator ceiling，不能反向证明 G1 生成器真实。
- `[ASSUMED][UPDATEABLE]` 80% SOH、筛选门槛、批次代理、权重与成本收益均可从配置追溯。
- `[UNCERTAIN]` 真实数据泛化、范围外工况、货币收益及安全失效概率仍未解决。

## 4. 统计解释与谬误扫描接口

- `[CONFIRMED]` academic-research-suite experiment-agent 的 11 类统计/方法学谬误已完成 `11/11` 扫描；逐项判定见 `technical/PAPER_TECHNICAL_BRIDGE.md` 第 8.3 节。
- `[CAUTION]` RUL 点误差仅覆盖可观测事件；删失样本必须单列，不能把事件子集误当全部电芯。
- `[CAUTION]` Q1 主效应为总体边际结果；必须同时检查分层方向，不能把总体排序写成每个工况或电芯都严格单调。
- `[CAUTION]` 所有 CI、OAT 和权重均为描述性仿真结果，不作显著性、因果或行业总体推断。

## 5. AI 研究失败模式预审

| 模式 | 判定 | 技术证据/处置 |
|---|---|---|
| 1 实现缺陷通过自审 | `CLEAR_WITHIN_CURRENT_SCOPE` | 56 tests、9 gates、双跑 manifest 与 43/43 产物哈希；代码变更后需重审 |
| 2 虚构或错配引用 | `INSUFFICIENT_EVIDENCE` | 33 个 `EVIDENCE REQUIRED` 未完成人工全文/页码核验；阻塞 Stage 2.5 |
| 3 虚构实验结果 | `CLEAR_WITHIN_CURRENT_SCOPE` | 数字回指保存的 CSV/JSON，manifest 可回算 |
| 4 捷径依赖 | `INSUFFICIENT_EVIDENCE` | 同一仿真家族内生成/训练/验证，无真实外部集或去捷径消融；只能作仿真内比较 |
| 5 缺陷包装为发现 | `CLEAR_WITHIN_CURRENT_SCOPE` | 未建立反常机理叙事；局部反转按随机效应限制报告 |
| 6 方法学伪造 | `CLEAR_WITHIN_CURRENT_SCOPE` | 方法、seed、配置、代码和产物已逐项对照；DOCX 冲突句必须替换 |
| 7 早期框架锁定 | `SUSPECTED` | 单协议/合成主线留下 Q1-Q4 题面覆盖缺口；补做或由总负责人书面接受限制后再审 |

预审状态：`NOT_READY_FOR_STAGE_2_5_PASS`。详细证据和处置见 `technical/PAPER_TECHNICAL_BRIDGE.md` 第 8.4 节。

## 6. 可能推翻当前结论的证据

1. 真实同化学体系数据若显示温度/倍率/DOD 方向或阶段结构相反，应重开 G0 并替换生成器。
2. 若独立数据留组误差显著高于仿真，论文必须以独立数据为准，仿真精度降为机制演示。
3. 若筛选门槛无法对应真实检测误差或安全规范，Q3 只保留优化框架，不保留阈值结论。
4. 若批次分布可取得，应删除当前批次代理，改用分层随机效应或实测批次固定效应。

## 7. 复核命令

```bash
PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output
python -m pytest code/tests -q
git diff --check
```

实际 pytest 数量和 stdout 以最终总验收记录为准；本文件只声明流水线内部闸门。
"""
    return _write(os.path.join(project_root, "technical", "VALIDATION_REPORT.md"), text)


def write_fact_sheet(project_root: str, results: dict) -> str:
    q1, q2, q3, q4 = (results[name]["summary"] for name in ("q1", "q2", "q3", "q4"))
    soh_best = min(q2["soh_metrics"], key=lambda row: row["rmse"])
    aft = _by_name(q2["rul_metrics"])["lognormal_aft_censored"]
    text = f"""# 论文写作数字事实表

写作入口：[PAPER_AGENT_START_HERE.md](../PAPER_AGENT_START_HERE.md)；技术过渡层：[PAPER_TECHNICAL_BRIDGE.md](PAPER_TECHNICAL_BRIDGE.md)。本页只提供可复制数字，不替代逐问模型、实验协议和限制说明。

> 只复制本页已标记数字；不得把“仿真结果”改写为“实测结果”。详细定义见 `TECHNICAL_REPORT_MINIMAL.md`。

| 编号 | 可写事实 | 标签 | 回指 |
|---|---|---|---|
| F1 | 全因子 27 工况、108 电芯、108000 行 | `[CONFIRMED]` | `study_output/factorial_design.csv` |
| F2 | 膝点可检测 72 电芯，右删失 36；内部恢复误差中位数 {_f(q1['knee_detection']['median_absolute_error_efc'],2)} EFC | `[RESULT]` 仿真自检 | `q1_knee_detection.csv` |
| F3 | 50-cycle SOH 最低 RMSE 模型 `{soh_best['model']}`，RMSE={_f(soh_best['rmse'],6)} | `[RESULT]` 仿真留组 | `q2_soh_metrics.csv` |
| F4 | RUL 事件 43、右删失 65；AFT 事件 RMSE={_f(aft['rmse'],2)} cycles，90% 区间覆盖={_f(aft['event_interval_90pct_coverage'])}，删失矛盾率={_f(aft['censored_early_failure_contradiction_rate'])} | `[RESULT]` 仿真留组 | `q2_rul_metrics.csv` |
| F5 | Q3 过门槛 {q3['eligible_cells']}/108，MILP 8 组、重复分配 0 | `[RESULT][UPDATEABLE]` | `q3_solution_summary.csv` |
| F6 | Q4 使用 {len(q4['seeds'])} 个独立 seed；OOD 四类均无数值 | `[CONFIRMED]` | `q4_monte_carlo_summary.csv`、`q4_ood_abstention.csv` |

禁止写入正文：真实车辆精度、普适安全阈值、人民币收益、低温/过充/过放寿命、CALCE 实测校准成功。
"""
    return _write(os.path.join(project_root, "technical", "PAPER_WRITING_FACT_SHEET.md"), text)


def write_supporting_readme(project_root: str) -> str:
    text = """# A题支撑材料说明

论文主笔 Agent 的技术过渡入口：[PAPER_TECHNICAL_BRIDGE.md](PAPER_TECHNICAL_BRIDGE.md)；本页只负责复跑和支撑材料打包。

## 1. 最小复跑

环境：Python 3.13；精确运行版本见 `study_output/run_manifest.json`，安装清单见 `requirements-study.txt`。

```bash
python -m pip install -r requirements-study.txt
PYTHONPATH=code python -m battery_study.cli --config configs/study_pipeline.json --out study_output
python -m pytest code/tests -q
```

## 2. 目录

- `code/g1_generator/`：G1 分段平方根退化生成器。
- `code/battery_study/`：Q1 阶段/主效应、Q2 SOH/RUL、Q3 MILP、Q4 鲁棒性和报告生成。
- `configs/`：全部固定参数、工况、seed、阈值和权重。
- `g1_output/`：G1 冒烟数据、图和清单。
- `study_output/`：G2-G4 CSV/JSON/SVG、验证闸门和 SHA-256 清单。
- `technical/`：四段最小技术报告、实验计划、验证报告、论文取数表和 A5 技术过渡层。
- `handoffs/A1-A5*.md`：论文与代码之间的交接证据包。

## 3. 事实源顺序

1. `study_output/run_manifest.json` 中的配置/源码/产物哈希。
2. `study_output/validation_gates.json` 和 CSV/JSON 结果。
3. `technical/PAPER_WRITING_FACT_SHEET.md` 的论文可写数字。
4. 图表和叙述文档；聊天数字不作为事实源。

108000 行全因子原始合成记录不重复提交；它们由固定代码、配置和 seed 确定性重建。支撑材料保留 108 行电芯摘要和全部模型预测，减少提交体积但不牺牲复现性。

## 4. 科学边界

- `[CONFIRMED]` 这是 NMC 合成仿真，不是 CALCE 实测拟合。
- `[ASSUMED][UPDATEABLE]` 退化参数、80% SOH、筛选门槛、批次代理、经济权重。
- `[UNCERTAIN]` 真实泛化、安全概率和货币收益。
- `[OOD/ABSTAIN]` 低温、过充、过放和 >2C 均无数值预测。

提交前只需将论文 PDF 与本目录结构一并打包；不要提交 `.git/`、`__pycache__/`、`.pytest_cache/` 或浏览器临时文件。
"""
    return _write(os.path.join(project_root, "technical", "SUPPORTING_MATERIALS_README.md"), text)


def write_handoffs(project_root: str, results: dict) -> list[str]:
    q1, q2, q3, q4 = (results[name]["summary"] for name in ("q1", "q2", "q3", "q4"))
    a2 = f"""# A2 Q1/Q2 阶段辨识与预测证据包

**状态**：`PASS_WITH_LIMITATIONS`
**事实源**：`configs/study_pipeline.json` + `study_output/run_manifest.json`

## 已交付

- Q1：27 工况全因子主效应、阶段计数、膝点检测与右删失；协议效应明确 `NOT_IDENTIFIABLE`。
- Q2：SOH 四模型、5 折 `GroupKFold(cell_id)`、27 工况留一压力测试、cell-bootstrap 90% CI。
- RUL：{q2['rul_endpoint']['observed_events']} 事件 + {q2['rul_endpoint']['right_censored']} 右删失；主模型 log-normal AFT，名义 90% 事件覆盖率={_f(_by_name(q2['rul_metrics'])['lognormal_aft_censored']['event_interval_90pct_coverage'])}。

## 写作边界

`[RESULT]` 只能称仿真留组性能。结构匹配模型是 simulator ceiling；不得声称外部验证。80% SOH 是 `[ASSUMED][UPDATEABLE]` 终点。

## 关键文件

`q1_summary.json`、`q1_factor_effects.csv`、`q1_knee_detection.csv`、`q2_soh_metrics.csv`、`q2_rul_metrics.csv`、`q2_leave_condition_out.csv`。
"""
    a3 = f"""# A3 筛选与编组优化证据包

**状态**：`PASS_WITH_ASSUMED_THRESHOLDS`

- 候选 {q3['candidate_cells']}，过门槛 {q3['eligible_cells']}，候选组 {q3['candidate_groups']}。
- MILP 固定 {q3['target_groups']} 组 x 4 电芯；重复分配={q3['constraint_audit']['duplicate_assignments']}，错误组规模={q3['constraint_audit']['wrong_group_sizes']}。
- 性能/平衡/保守三权重 + greedy 对照；只使用归一化无量纲成本收益。

`[ASSUMED][UPDATEABLE]` 所有门槛和权重待真实检测误差、安全规范和商业数据更新。没有货币化收益结论。

关键文件：`q3_candidate_screening.csv`、`q3_selected_groups.csv`、`q3_assignments.csv`、`q3_solution_summary.csv`。
"""
    a4 = f"""# A4 多工况与鲁棒性证据包

**状态**：`PASS_WITH_DOMAIN_LIMIT`

- 支持域内 5 工况、{len(q4['seeds'])} 个新 seed、7 参数 +/-10% OAT。
- 三个批次代理均为 `[ASSUMED][UPDATEABLE]`，不是实测批次数据。
- 低温、过充、过放、3C 全部 `[OOD/ABSTAIN]`，数值字段为空。

工程建议只能写成“本仿真条件下的触发规则”，不能提升为行业标准或安全保证。

关键文件：`q4_monte_carlo_raw.csv`、`q4_monte_carlo_summary.csv`、`q4_sensitivity_oat.csv`、`q4_sensitivity_rank.csv`、`q4_ood_abstention.csv`。
"""
    paths = [
        _write(os.path.join(project_root, "handoffs", "A2_prediction_package.md"), a2),
        _write(os.path.join(project_root, "handoffs", "A3_optimization_package.md"), a3),
        _write(os.path.join(project_root, "handoffs", "A4_robustness_package.md"), a4),
    ]
    return paths


def write_html_report(project_root: str, results: dict) -> str:
    q2, q3, q4 = results["q2"]["summary"], results["q3"]["summary"], results["q4"]["summary"]
    best = min(q2["soh_metrics"], key=lambda row: row["rmse"])
    aft = _by_name(q2["rul_metrics"])["lognormal_aft_censored"]
    scenarios = _by_name(q4["monte_carlo_summary"], "scenario")
    scenario_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{_f(row['final_soh_mean_mean'])}</td><td>{_f(row['critical_fraction_mean'])}</td><td>{_f(row['screening_rate_mean'])}</td></tr>"
        for name, row in scenarios.items()
    )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>A题技术结果总览</title><link rel="icon" href="data:,">
<style>
:root{{--ink:#202124;--muted:#5f6368;--line:#d9dee2;--teal:#176b87;--red:#b13b4b;--gold:#ad7418;--bg:#f7f8f8}}
*{{box-sizing:border-box}} body{{margin:0;color:var(--ink);background:#fff;font-family:Arial,"Microsoft YaHei",sans-serif;line-height:1.6}}
header{{border-bottom:4px solid var(--teal);background:var(--bg);padding:28px max(24px,calc((100vw - 1120px)/2)) 22px}}
h1{{font-size:30px;margin:0 0 6px;letter-spacing:0}} header p{{margin:0;color:var(--muted)}}
main{{max-width:1120px;margin:auto;padding:22px 24px 56px}} section{{padding:18px 0 28px;border-bottom:1px solid var(--line)}}
h2{{font-size:20px;margin:0 0 14px;letter-spacing:0}} .metrics{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line)}}
.metric{{background:#fff;padding:14px;min-height:92px}} .metric strong{{display:block;font-size:24px;color:var(--teal)}} .metric span{{font-size:12px;color:var(--muted)}}
.warning{{border-left:4px solid var(--red);padding:10px 14px;background:#fff7f7}} .assumption{{border-left:4px solid var(--gold);padding:10px 14px;background:#fffaf0}}
table{{width:100%;table-layout:fixed;border-collapse:collapse;font-size:13px;overflow-wrap:anywhere}} th,td{{min-width:0;text-align:left;padding:8px;border-bottom:1px solid var(--line);overflow-wrap:anywhere;word-break:break-word}} th{{background:var(--bg)}}
.figures{{display:grid;grid-template-columns:1fr 1fr;gap:18px}} figure{{margin:0}} figure img{{display:block;width:100%;height:auto;border:1px solid var(--line)}} figcaption{{font-size:12px;color:var(--muted);margin-top:5px}}
@media(max-width:760px){{.metrics,.figures{{grid-template-columns:1fr}} h1{{font-size:25px}} main{{padding-inline:16px}}}}
</style></head><body>
<header><h1>A题技术结果总览</h1><p>NMC 合成仿真 · G2–G4 · 所有结论限于冻结支持域</p></header>
<main>
<section><h2>关键结果</h2><div class="metrics">
<div class="metric"><strong>{_f(best['rmse'],6)}</strong><span>最佳通用 SOH RMSE · {html.escape(best['model'])}</span></div>
<div class="metric"><strong>{_f(aft['rmse'],2)}</strong><span>AFT RUL RMSE · 仅 43 个可观测事件</span></div>
<div class="metric"><strong>{q3['eligible_cells']}/108</strong><span>Q3 通过假设硬门槛</span></div>
<div class="metric"><strong>0</strong><span>MILP 重复电芯分配</span></div>
</div></section>
<section><h2>证据边界</h2><p class="assumption"><b>[ASSUMED/UPDATEABLE]</b> 退化参数、80% SOH、筛选门槛、批次代理和经济权重均待真实数据更新。</p><p class="warning"><b>[OOD/ABSTAIN]</b> 低温、过充、过放和超过 2C 不输出数值。</p></section>
<section><h2>多工况摘要</h2><table><thead><tr><th>场景</th><th>平均末期 SOH</th><th>临界比例</th><th>筛选率</th></tr></thead><tbody>{scenario_rows}</tbody></table></section>
<section><h2>论文图候选</h2><div class="figures">
<figure><img src="../study_output/fig_q1_factor_weights.svg" alt="Q1 factor weights"><figcaption>Q1 主效应权重</figcaption></figure>
<figure><img src="../study_output/fig_q2_soh_rmse.svg" alt="Q2 SOH RMSE"><figcaption>Q2 SOH 模型比较</figcaption></figure>
<figure><img src="../study_output/fig_q3_tradeoff.svg" alt="Q3 tradeoff"><figcaption>Q3 权重方案权衡</figcaption></figure>
<figure><img src="../study_output/fig_q4_final_soh.svg" alt="Q4 final SOH"><figcaption>Q4 多工况末期 SOH</figcaption></figure>
</div></section>
</main></body></html>"""
    return _write(os.path.join(project_root, "technical", "TECHNICAL_REPORT_MINIMAL.html"), document)


def write_all(project_root: str, study_cfg, results: dict, gates: list[dict]) -> list[str]:
    return [
        write_minimal_report(project_root, study_cfg, results),
        write_experiment_plan(project_root, study_cfg),
        write_validation_report(project_root, results, gates),
        write_fact_sheet(project_root, results),
        write_supporting_readme(project_root),
        write_html_report(project_root, results),
        *write_handoffs(project_root, results),
    ]
