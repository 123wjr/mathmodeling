# G1 总负责人验收记录

**验收时间**：2026-08-12 05:00 CST（总负责人复跑）
**输入材料**：`handoffs/G1_TASK_DISPATCH.md`、`handoffs/A0_Task_Contract.md`、
`handoffs/A1_simulation_package.md`、`docs/Simulation_Protocol.md`、
`evidence/parameter_ledger.txt`、`evidence/source_ledger.txt`、
`code/g1_generator/`、`code/tests/test_generator.py`、`configs/g1_smoke.json`、
`g1_output/`（CSV、数据字典、4 类图、运行清单）
**复跑环境**：分支 `main` @ `79c6c07`；Python 3.13（stdlib 生成器 + pytest）
**结论**：`PASS_WITH_CHANGES`

## 1. 结论解释

G1 可复现退化数据生成器已达到 G0 冻结协议与 G1 任务书的全部技术验收条件：
公式、边界、产物一致性、趋势/膝点/输入边界测试、与后续预测器的隔离、
来源诚信标签 5 道验收门**全部 PASS**（详见第 2 节）。本记录由总负责人
**亲自复跑**得出，不是沿用建模手的自述。

`PASS_WITH_CHANGES` 的"CHANGES"不指向代码失败，而是科学证据边界：
- 本包未下载、解析或拟合 CALCE 原始循环数据，退化系数仍为 `ASSUMED`，
  因此只能支撑"在 G0 冻结边界内构建可复现的半机理随机仿真"，不能支撑
  "实测校准"或"外部验证"表述；
- 论文必须始终把 `g1_output/degradation_data.csv` 等产物称为**仿真数据**，
  不得当作真实电芯测试结果；
- 本验收不豁免第 4 节中"进入 G2 前的硬性要求"。

## 2. 五项验收结论

| 验收问题 | 状态 | 依据与结论 |
|---|---|---|
| 生成器是否严格遵守 G0 协议与参数台账 | `PASS` | `code/g1_generator/degradation.py` 公式与 `docs/Simulation_Protocol.md` 第6/7节逐条一致：`u_T=exp(k_T(T-25))`、`u_C=1+k_C(C-0.5)`、`u_D=1+k_D(DOD/100-0.5)`、`L(e)=√min(e,n_k)+knee_gain·max(0,√e-√n_k)`、`SOH_i=1-α_i·u·L(e)` 且 `SOH=capacity_true/Q0_i`（起点恒为 1）。`code/g1_generator/config.py` 的 `PARAMETER_BOUNDS` 与 `evidence/parameter_ledger.txt` 边界完全对齐；`validate_config` 对越界**拒绝**而非静默截断。 |
| CSV、数据字典、图表、配置、seed、哈希和运行命令是否互相一致 | `PASS` | 复跑后 8 项 G1 产物哈希与 A1 第五节**逐项 MATCH**（见第 3 节哈希表）；seed=42 固定；CLI 命令与 A1 第2节一致；同 seed 逐字节复现（`test_reproducibility_same_seed` / `test_all_core_outputs_are_byte_identical_across_runs` 通过）。 |
| 容量/内阻趋势、膝点和输入边界测试是否通过 | `PASS` | pytest **41 passed, 0 failed**。覆盖：容量单调降、内阻单调升、膝点后容量衰减斜率绝对值更大、压力工况末期平均 SOH 低于 baseline、温度/DOD/倍率/协议/全局参数越界拒绝、不拆分同一电芯循环、CSV 字段完整、显式 LF。 |
| 生成器是否与未来预测器、留组划分、外部验证隔离 | `PASS` | grep 确认 `code/g1_generator` 不含 `sklearn/torch/LSTM/Transformer/GAN/train_test_split/leave_one/cross_val/fit( /predict(`，且不 import `battery_study` 或 `study_output`。G1 仅作为 `code/battery_study` 研究管线的**冻结输入**被消费，作用域分离；G1 内不存在任何训练/测试拆分。 |
| A1 是否明确区分 OBSERVED / LITERATURE_FIXED / ASSUMED 并列出限制 | `PASS` | A1 第7节三类标签分明：`OBSERVED`（Q_nom、R0 范围、工况边界、协议、循环上限）、`LITERATURE_FIXED`（SOH_EOL=80%）、`ASSUMED`（α/β/k_T/k_C/k_D/σ_Q/σ_R/σ_cell/n_k/knee_gain/seed）；并明确列出"未完成"项：未拟合 CALCE、未外部验证、未证明 80% SOH 普适。数据字典测试同时拒绝把仿真输入标成 `OBSERVED`。 |

## 3. 复跑关键证据

**测试**：`PYTHONPATH=code python -m pytest code/tests/test_generator.py -q` → `41 passed`。

**哈希核验**（磁盘实际 SHA-256 = A1 第五节，逐项 MATCH）：

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

**数据规模**：12 电芯 × 1000 循环 = 12000 行；4 工况 = baseline(25°C/1C/80%DOD) +
stress_highT(45°C) + stress_highC(2C) + stress_highDOD(100%DOD)，满足"≥3 电芯、
≥1 基准 + 3 压力工况"。

**复跑修订动作**（已提交 `79c6c07`）：
1. 修复 `code/g1_generator/cli.py` 跨盘符 `os.path.relpath` Bug：输出目录与仓库
   不同盘符（本机 pytest 临时目录在 `C:`、仓库在 `X:`）时抛 `ValueError`，
   现回退为去盘符可移植片段，`test_manifest_contains_only_portable_relative_paths`
   由失败转为通过（40+1 fail → 41 passed）。
2. 用当前 `code/g1_generator` 重新生成 `g1_output/`：此前磁盘为陈旧旧产物
   （CSV 仍带 CRLF 旧哈希 `9d2cc5b3`、SVG 为旧版），与 A1 哈希不符；重生成后
   8 项 G1 产物哈希与 A1 第五节完全一致。

## 4. 进入 G2 前的硬性要求

- **论文主笔**：任何 G1 结果必须标注"仿真数据（seed=42，固定配置）"；不得把
  生成轨迹当实测结果；未打开全文核验的 A1–A4 候选文献不得作为已验证引用；
  在 `R1` 结果文件冻结前不得写入预测精度、成本收益或寿命数字。
- **G2 建模**：SOH/RUL 预测器、留组划分、外部验证必须以 G1 输出为**冻结输入**，
  不得反向用预测精度反证或改动 G1 生成器；80% SOH 仅是可调建模阈值，不是普适
  安全阈值；不得引入 LSTM/Transformer/GAN/NSGA-II/PSO 等超出任务书范围的模型。
- **数据隔离**：`code/g1_generator` 保持与 `code/battery_study` 无导入依赖；
  外部数据只使用 `evidence/source_ledger.txt` 已列入口，未核验字段写 `UNVERIFIED`。
- **复现性**：所有下游产物继续记录配置、seed、运行命令与文件 SHA-256；禁止
  把输出目录的盘符或贡献者主目录写入证据链（已由 `.gitattributes` LF 与清单
  相对路径保证）。

## 5. 当前状态

`G1 APPROVED FOR G2`（带上述条件）。G1 技术接口达到冻结条件，R1 接口可进入冻结流程。
本记录不代表任何实测校准或外部验证已完成；`study_output/` 中 G2–G4 研究产物
（`code/battery_study`，含 scikit-learn 依赖）属另一验收范围，不在本记录覆盖内。
