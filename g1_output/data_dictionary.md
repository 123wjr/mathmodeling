# G1 数据字典（Data Dictionary）

> 由 `g1_generator` 自动生成。所有仿真系数为 `ASSUMED`，完整范围见 `evidence/parameter_ledger.txt`。

- 化学体系: NMC（NMC / LiNiMnCo-graphite）
- 主校准对象: CALCE INR18650-20R（仅作仿真边界，非拟合来源）
- 随机种子 seed: 42（冒烟固定值）
- 电芯数: 12；总行数: 12000
- 工况: baseline, stress_highT, stress_highC, stress_highDOD

## 字段说明

| 字段 | 类型 | 单位 | 含义 | 来源标签 |
|---|---|---|---|---|
| cell_id | str | - | 电芯标识 = 场景id_序号 | LITERATURE_FIXED |
| cycle | int | cycle | 循环次数（时间轴） | OBSERVED |
| efc | float | EFC | 等效完整循环数 = Σ DOD/100 | OBSERVED |
| temperature | float | degC | 环境温度 | OBSERVED |
| c_rate | float | C | 充放电倍率 | OBSERVED |
| dod | float | % | 放电深度 | OBSERVED |
| protocol | str | - | 充电协议（仅 CC-CV） | OBSERVED |
| capacity_true | float | Ah | 真实可用容量 = Q0·(1-α·u·L(e)) | ASSUMED |
| capacity_obs | float | Ah | 观测容量 = true + N(0,σ_Q·Q_nom) | ASSUMED |
| soh | float | - | 健康状态 = capacity_true / Q0_i = 1 - alpha_i·u·L(e)（起点=1） | ASSUMED/DERIVED |
| resistance_true | float | Ohm | 真实内阻 = R0·(1+β·u·L(e)) | ASSUMED |
| resistance_obs | float | Ohm | 观测内阻 = true + N(0,σ_R·R_true) | ASSUMED |
| seed | int | - | 本运行主随机种子 | ASSUMED |

## 公式与边界

- EFC = Σ(DODᵢ/100)；本数据为恒定 DOD，故 efc = cycle·DOD/100。
- L(e)=√min(e,nₖ) + knee_gain·max(0,√e−√nₖ)，knee_gain=2.0，nₖ=700 EFC。
- u_T=exp(k_T·(T−25))，u_C=1+k_C·(C_rate−0.5)，u_D=1+k_D·(DOD/100−0.5)。
- 随机效应：截断正态 N(0,σ_cell) 截断于 [−2σ,2σ]，作用于初始容量/内阻与退化速率。
- 观测噪声仅加在 obs 字段，不改变总体退化方向。
- 同配置 + 同 seed → CSV 逐字节一致；不同 seed → 合理电芯差异。
- 模拟数据非实测数据，不声称复现真实电芯或电池内部机理。
