# A1 仿真证据包：可复现退化数据生成器

**技术验收结论**：`PASS_WITH_CHANGES`

**复核时间**：2026-08-11 15:59 CST

**依赖任务**：G0-R PASS（NMC + CALCE INR18650-20R 参考边界）

**范围**：仅 G1 生成器、测试、合成 CSV、数据字典和四类合理性图；不含预测器、RUL 或编组优化

`PASS_WITH_CHANGES` 的原因不是代码失败，而是科学证据边界：本包没有读取或拟合 CALCE 原始数据，所有退化系数仍为 `ASSUMED`。因此只能支撑“可复现的仿真实验”，不能支撑“经过实测校准或外部验证”的表述。

## 1. 版本状态

| 项 | 当前事实 |
|---|---|
| 分支 | `main` |
| 修订前 HEAD | `6d8dd478150f` |
| 当前修订 | 本文件所在 `origin/main` commit；`study_output/run_manifest.json` 记录实现提交前置 HEAD |
| Python | 3.13.13 |
| 生成器依赖 | Python 标准库 |
| 测试依赖 | pytest |

旧 A1 中的 `model/g0-g1 @ 0aac11c`、`X:\test`、Python 3.13.12 和 `12 passed` 均不是当前仓库事实，已作废。

## 2. 可复现命令

从仓库根目录执行：

```bash
PYTHONPATH=code python -m g1_generator.cli \
  --config configs/g1_smoke.json \
  --out g1_output

python -m pytest code/tests/test_generator.py -q
```

本次实际结果：

```text
41 passed, 0 failed
12 cells / 12000 rows
seed = 42
```

CLI 不带 `--config` 时也会定位到仓库根目录的 `configs/g1_smoke.json`。`run_manifest.json` 只记录相对路径，不再写入贡献者的盘符或主目录。

## 3. 代码与配置

| 路径 | 用途 |
|---|---|
| `code/g1_generator/config.py` | JSON 加载、G0 冻结边界和完整配置校验 |
| `code/g1_generator/degradation.py` | 分段平方根退化、受边界约束的个体随机效应和测量噪声 |
| `code/g1_generator/simulate.py` | 数据生成、LF CSV、数据字典和动态图表编排 |
| `code/g1_generator/plots.py` | 确定性 SVG 输出和 XML 文本转义 |
| `code/g1_generator/cli.py` | 根目录 CLI、相对路径运行清单和 SHA-256 |
| `code/tests/test_generator.py` | G1 回归、边界、复现性、标签和证据链测试 |
| `configs/g1_smoke.json` | seed=42；4 工况 x 3 电芯 x 1000 循环 |
| `.gitattributes` | 固定 G1 文本产物为 LF，避免 Windows/Linux 哈希漂移 |

配置校验会直接拒绝越界值，不再静默 clamp：

- chemistry 只能为 NMC；Q_nom 固定 2.0 Ah；CC-CV；knee_gain 固定 2.0；SOH_EOL 固定 80%。
- 25--50 degC、0.5--2C、DOD 50--100%、1--1000 cycles。
- R0、alpha、beta、k_T、k_C、k_D、sigma_Q、sigma_R、sigma_cell 和 n_k 必须在 `evidence/parameter_ledger.txt` 的冻结范围内。
- scenario id 必须唯一，n_cells 必须为正整数，并满足 baseline + 至少 3 个非基准工况、总计至少 3 颗电芯。
- 电芯级 R0_i、alpha_i、beta_i 通过受限采样留在冻结范围内，不用越界兜底值伪装成有效参数。

## 4. 测试覆盖

41 项测试覆盖：

1. 同配置和 seed 的 CSV、数据字典与四个 SVG 逐字节一致。
2. seed=42 与 seed=99 产生不同电芯轨迹，同时保持合理方向。
3. 每颗电芯 `capacity_true` 严格下降、`resistance_true` 严格上升，膝点后容量衰减斜率绝对值更大。
4. 高温、高倍率和高 DOD 工况的末期平均 SOH 均低于 baseline。
5. 温度、倍率、DOD、化学体系、协议、全局参数、周期数、重复场景和电芯数越界均被拒绝。
6. 每颗电芯 cycle 为完整的 1..1000 序列，未做训练/测试拆分。
7. CSV 字段完整，使用显式 LF；数据字典不再把仿真输入标成 `OBSERVED`。
8. 图标题随配置中的电芯数变化，膝点图使用 baseline 均值和 `SOH=capacity_true/Q0_i`，不再硬编码 `baseline_0`。
9. manifest 中配置、CSV、字典和 SVG 均为可移植相对路径。

## 5. 固定种子输出与 SHA-256

| 文件 | SHA-256 |
|---|---|
| `configs/g1_smoke.json` | `2ae8e9ead7600ae67a8f76c7c44af02d154a656a2e4b91dd1306cf4b5c932192` |
| `g1_output/degradation_data.csv` | `c1e2d05b5b51a9a1860a0d9a359b10e5b9f988df900a8e8954c55391c6940eb2` |
| `g1_output/data_dictionary.md` | `af9bd11b15603fb86d8b894dc294067c05174f7b7e621088c5dca6838a4e3eb0` |
| `g1_output/fig_capacity_trajectories.svg` | `91ec63e561b14c32525b03453229b8a3a39a073210a0e95c9efd43be022d4628` |
| `g1_output/fig_resistance_trajectories.svg` | `9161d1df125ea2e64103296559034b60e894e9902a0e524298f9ca9b6b1f0815` |
| `g1_output/fig_knee_slope.svg` | `639fd09f3b74e64f97a1aab2677a1ca34dec6df6fde3cc797b0f34a7c2f49f69` |
| `g1_output/fig_scenario_comparison.svg` | `4e60b0db880533eb1becc52f0ae3414dbfaf7db17aea43e3a60cdfecadada0d9` |
| `g1_output/run_manifest.json` | `04607ee1668fd03f69bb756e40373f7a54af0e44c45e45f9accaf04b0e4addf8` |

旧 CSV 哈希 `9d2cc...` 是 CRLF 工作区字节，不能作为跨平台证据；本版统一使用 Git 固定的 LF 字节。

## 6. 直接产物检查

SVG 已使用 XML 解析器直接读取，不依赖截图判断：

| 图 | 尺寸 | polyline | 每条点数 | 关键标题 |
|---|---:|---:|---:|---|
| capacity | 860 x 540 | 12 | 1000 | 12 电芯容量轨迹 |
| resistance | 860 x 540 | 12 | 1000 | 12 电芯内阻轨迹 |
| knee | 860 x 540 | 1 | 1000 | baseline SOH 均值；Q0_i 口径 |
| scenario | 860 x 540 | 4 | 1000 | 四工况 SOH 均值 |

末周期平均 SOH 合理性检查：

| 场景 | cycle=1000 平均 SOH |
|---|---:|
| baseline | 0.847996 |
| stress_highT | 0.783639 |
| stress_highC | 0.834928 |
| stress_highDOD | 0.800977 |

这些数值只用于检查生成器内部方向是否符合设定，不能解释为真实电芯寿命或实验结论。

## 7. 来源与诚信边界

### 已确认

- 代码和配置遵守已批准的 NMC、CC-CV、分段平方根结构及参数台账范围。
- 生成器只读取本地 JSON 配置，不下载、上传或读取外部实验数据。
- NASA 数据未进入 G1，也未与 CALCE 合并拟合。
- `capacity_obs` 和 `resistance_obs` 是加噪后的合成观测；字段名中的 `obs` 不表示外部实测。
- `capacity_true` 和 `resistance_true` 表示仿真器内部无噪声真值，不表示现实真值。

### 未完成，正文不得越界表述

- 未下载、解析或拟合 CALCE 原始循环数据。
- 未证明参数范围能定量复现 INR18650-20R。
- 未进行外部验证、预测精度验证或真实车辆泛化验证。
- 未证明 80% SOH 是普适安全阈值。

因此论文允许写“在 G0 冻结边界内构建可复现的半机理随机仿真”，不允许写“基于 CALCE 实测完成校准”“实验验证有效”或“准确预测真实寿命”。

## 8. G1 闸门结论

| 验收项 | 结论 |
|---|---|
| 公式、单位和冻结边界 | PASS |
| 配置、seed、CSV、字典、图、命令和哈希一致 | PASS |
| 趋势、膝点、压力方向和输入边界 | PASS |
| 与 G2 预测器和数据划分隔离 | PASS |
| `OBSERVED` / `LITERATURE_FIXED` / `ASSUMED` 诚信标记 | PASS |
| 实测校准与外部验证 | NOT DONE；不得声称已完成 |
| Git commit | 本文件所在 `origin/main` commit；实现提交与产物哈希已回填 |

**最终结论**：G1 技术接口已达到冻结条件，状态为 `PASS_WITH_CHANGES`；实现提交与产物哈希已形成，本证据包随本文件所在 `origin/main` commit 发布。后续论文必须始终把数据称为仿真数据，不得用 G2 的预测效果反向证明 G1 生成器真实有效。
