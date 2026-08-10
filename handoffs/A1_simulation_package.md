# A1 仿真证据包：可复现退化数据生成器

**状态**：DONE_WITH_CONCERNS
**生成时间**：2026-08-10（G1 8/10 19:00–21:00 冒烟窗口）
**依赖任务**：G0-R PASS（NMC + CALCE INR18650-20R 冻结）
**总负责人验收门**：见第六节，待 8/11 15:00 复跑签署

---

## 一、分支 / 提交

| 项 | 值 |
|---|---|
| 分支 | `model/g0-g1` |
| 代码提交 | `0aac11c`（SOH 基准修正 + 复跑 + 刷新 SHA；前序 f55c0cd / 10e6683） |
| 基线 | 自本地 `main` 的 G0-R 状态起分支（仓库无远端，本地以当前工作区作为 G0-R clean line） |
| Python | 3.13.12（managed venv）；运行时仅依赖标准库 + pytest |

> 注：本仓库此前在 `X:\test` 不是 git 仓库。已 `git init`，以当前 G0-R 文档/台账状态作为 `main` 基线提交，再从 `main` 拉出 `model/g0-g1` 分支承载 G1 实现。

---

## 二、代码与配置

| 路径 | 用途 |
|---|---|
| `g1_generator/config.py` | 冻结参数与工况加载（均来自 `parameter_ledger.txt` 边界） |
| `g1_generator/degradation.py` | 分段平方根容量/内阻退化、截断正态随机效应、测量噪声、输入校验 |
| `g1_generator/simulate.py` | 数据集生成、CSV、数据字典、4 类图编排、SHA-256 |
| `g1_generator/plots.py` | 纯标准库 SVG 折线图（零第三方绘图依赖，完全可复现） |
| `g1_generator/cli.py` | 命令行入口，写出 `run_manifest.json` |
| `tests/test_generator.py` | pytest 套件（12 项），覆盖 G1 必测规则 |
| `configs/g1_smoke.json` | 冒烟配置：seed=42，4 工况 × 3 电芯 = 12 电芯 |

### 冻结系数标签（与台账一致）

| 符号 | 取值 | 标签 |
|---|---|---|
| Q_nom | 2.0 Ah | OBSERVED |
| R0_nom | 0.05 Ω | OBSERVED（台账 0.03–0.10 中段） |
| alpha | 0.004 | ASSUMED |
| beta | 0.010 | ASSUMED |
| k_T | 0.020 | ASSUMED |
| k_C | 0.100 | ASSUMED |
| k_D | 0.500 | ASSUMED |
| sigma_Q | 0.6 % | ASSUMED |
| sigma_R | 1.5 % | ASSUMED |
| sigma_cell | 0.05 | ASSUMED |
| n_k | 700 EFC | ASSUMED |
| knee_gain | 2.0 | ASSUMED/FIXED |
| SOH_EOL | 80 % | LITERATURE_FIXED（可调 RUL/退役阈值，非普适安全阈值） |

所有 `ASSUMED` 系数均为仿真设定，**未在论文中写成 CALCE 直接实测估计**。

---

## 三、运行命令

```bash
# 依赖（仅测试需要 pytest；生成器本体仅用标准库）
python -m pip install pytest        # 已装于 managed venv

# 生成冒烟产物
python -m g1_generator.cli --config configs/g1_smoke.json --out g1_output
```

复现验证命令（同 seed 逐字节一致）：

```bash
python -m g1_generator.cli --config configs/g1_smoke.json --out g1_output
python -m pytest tests/ -q
```

---

## 四、测试结果

`pytest tests/ -q` → **12 passed**。覆盖 G1 必测规则：

1. 同配置 + 同 seed → CSV 逐字节一致（SHA-256 相等）。
2. 不同 seed（42 vs 99）→ 首行容量不同，且两批均保持容量单调下降（合理差异）。
3. 容量总体下降：每颗电芯 `capacity_true` 严格单调下降。
4. 内阻总体上升：每颗电芯 `resistance_true` 严格单调上升。
5. 膝点后斜率更高：baseline 在 n_k 两侧的 `|dSOH/de|` 满足 after > before。
6. 输入边界拒绝：温度 60°C / DOD 120% / 负倍率 / 非 CC-CV 协议均抛 `ValueError`。
7. 字段完整：13 个必填字段齐全；电芯数 ≥3；含 ≥1 基准 + 3 压力工况。
8. 物理可行域：所有 `capacity_true/resistance_true/obs > 0`，`0 < soh ≤ 1.2`。
9. 不拆分循环：每颗电芯 cycle 为 1..N 连续整段。
10. CSV 表头与各必填字段名一致。

---

## 五、输出文件与 SHA-256（seed=42）

| 文件 | SHA-256 |
|---|---|
| `g1_output/degradation_data.csv` | `9d2cc5b35c5a030ec38ce7d30f1b572c3e2ccbdedbc9fcd5b639d2c5df4de416` |
| `g1_output/data_dictionary.md` | `e6df30e2681cb2e47b7657cbf33197e3ad58a0752b0d95c1002e49234fe07779` |
| `g1_output/fig_capacity_trajectories.svg` | `1374be0066fb6f2a63c0c6792330f0285d88a18a38c6d0e3fa357ce6e5ceadac` |
| `g1_output/fig_resistance_trajectories.svg` | `18aebc181106eaa4c2b2455f00acfec9248f6fd11cf1e5b2c27237ff53cd837d` |
| `g1_output/fig_knee_slope.svg` | `9987ecfa7192d9377020342867828435ca05b086f896382c1b808be72f416525` |
| `g1_output/fig_scenario_comparison.svg` | `d863c7df4d4eed8039519c5fdc14d8e7cda7ef28b87916e7c1c5c0d294c47a7f` |
| `configs/g1_smoke.json` | `2ae8e9ead7600ae67a8f76c7c44af02d154a656a2e4b91dd1306cf4b5c932192` |

> **二阶验收复跑修订（2026-08-10 21:2x）**：相对首版 A1，本次复跑修正了 SOH 计算口径——由 `capacity_true / Q_nom` 改为 `capacity_true / Q0_i`，使 `SOH_i(e) = 1 - alpha_i·u·L(e)` 严格符合 `docs/Simulation_Protocol.md` 第6节（消除原先多余的 `(1+ε_Q)` 个体因子）。knee/scenario 两图哈希随之变化。pytest 仍 **12 passed**，同 seed CSV 逐字节一致。

规模：12 电芯 × 1000 循环 = **12000 行**；工况：baseline(25°C/1C/80%DOD) + stress_highT(45°C) + stress_highC(2C) + stress_highDOD(100%DOD)。

数据字典字段：`cell_id, cycle, efc, temperature, c_rate, dod, protocol, capacity_true, capacity_obs, soh, resistance_true, resistance_obs, seed`（与 G1 任务书要求一致）。

---

## 六、总负责人验收门自检（G1_TASK_DISPATCH 第五节）

1. 生成器严格遵守 G0 协议与参数台账：**是**（分段平方根、CC-CV、NMC、系数均在台账边界）。
2. CSV/字典/图/配置/seed/哈希/命令互相一致：**是**（CLI 同时产出并写入 `run_manifest.json`）。
3. 容量/内阻趋势、膝点与输入边界测试通过：**是**（12 项测试）。
4. 与未来预测器/留组划分/外部验证隔离：**是**（G1 不训练任何预测器；同一 cell_id 循环不拆分）。
5. A1 明确区分 OBSERVED / LITERATURE_FIXED / ASSUMED 并列出限制：**是**（见第二节与第七节）。

验收结论建议：`PASS_WITH_CHANGES`（G1 生成器本身通过；`ASSUMED` 系数与来源核验为 G0 遗留 `PASS_WITH_CHANGES` 条件，不阻塞 G1）。

---

## 七、已核验来源 / 未核验来源 / 失败项 / 限制

### 已核验来源（OBSERVED / LITERATURE_FIXED）
- NMC（LiNiMnCo/graphite）主化学体系与 CALCE INR18650-20R 主校准对象：来自 G0 冻结决策（OBSERVED 边界）。
- CC-CV 为唯一充电协议：OBSERVED。
- 参数单位/范围/标签：`evidence/parameter_ledger.txt` 已列（G0 PASS）。
- 分段平方根退化形式与工况修正：`docs/Simulation_Protocol.md`（G0 批准）。

### 未核验来源（UNVERIFIED / 待人工全文核验）
- CALCE 原始 `.mat`/数据文件：**尚未下载或解析**，系数未做实测拟合；所有 `ASSUMED` 仅作仿真场景设定。
- NASA PCoE 数据：仅 `SECONDARY_ONLY` 外部/归一化对照，未合并寿命拟合。
- `g0.docx` 中 52 个 `[[EVIDENCE REQUIRED:Ax-ID]]` 标记：论文手待人工打开全文核验，A1 不引用未核验条目。

### 外部数据入口核验（验收④：仅用 source_ledger 已列入口，未核验字段标 UNVERIFIED）
- 代码仅 `open` 本地配置文件（`configs/g1_smoke.json`）与输出文件；**无任何网络下载/上传、无读取外部实测数据**（grep 确认：`http` 仅出现在 SVG 命名空间，`CALCE`/`NASA` 仅出现在注释与数据字典文本，未被代码读取）。不触碰任何私密材料。
- 所有 `ASSUMED` 系数硬编码于 `g1_generator/config.py` 默认值，且均落在 `evidence/parameter_ledger.txt` 边界内；未从 `source_ledger.txt` 或任何外部文件动态载入数值。
- `source_ledger.txt` 已列入口中，NASA 为"部分核验"；本生成器未使用 NASA 数据（仅作 SECONDARY_ONLY 外部对照，未合并拟合），故当前产物中**无 UNVERIFIED 字段**。若后续接入 CALCE/NASA 原始数据作校准，须在数据字典与 A1 中对相关字段显式标注 `UNVERIFIED`。

### 失败项
- 无代码/测试失败（pytest 12 passed）。

### 已知限制（明确写入 A1，避免误读）
- 本生成器是**可解释仿真模型**，非完整电化学机理模型；不声称复现 SEI 增长、锂析出、热失控或真实电芯。
- 系数均为 `ASSUMED`，未用 CALCE 原始数据校准；模拟轨迹**不是实测结果**，论文中须表述为“仿真数据”。
- 轻度工况（如 baseline 80% DOD）在 1000 循环内未必降至 SOH_EOL=80%；属正常仿真范围，不代表真实寿命。
- 图表为 SVG 矢量图（纯标准库生成，零依赖、可复现）；若评审要求位图（PNG），可后续补充 matplotlib 渲染。
- 未引入任何预测器、编组优化或深度模型（符合 G1 禁止事项）。

---

## 八、需要总负责人决定

1. 是否需将 CALCE 原始数据接入以校准 `ASSUMED` 系数（否则保持透明假设生成器）。
2. 是否扩展循环数/DOD 使部分工况达到 SOH_EOL，以支撑后续 RUL/退役阈值演示。
3. 图表格式是否接受 SVG，或要求 PNG/matplotlib。
4. 本地仓库无远端：是否建立远端并推送 `model/g0-g1` 供队友拉取。

---

## 九、下一步（不属 G1）
- G2（Q1/Q2 健康评估与 RUL）：待 A1 接口冻结后开始，使用本 CSV 作为输入，**不反向用预测精度证明生成器**。
- 论文手：A1 验收前不写预测精度/寿命/收益数字；方法段可引用本 A1 文件与哈希。
