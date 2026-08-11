# G1 数据字典（Data Dictionary）

> 由 `g1_generator` 自动生成。本文件描述的是合成仿真数据，不是 CALCE 或其他实验实测数据。

- 化学体系: NMC（NMC / LiNiMnCo-graphite）
- 参考边界对象: CALCE INR18650-20R（未读取原始数据、未做参数拟合）
- 随机种子 seed: 42
- 电芯数: 12；总行数: 12000
- 工况: baseline, stress_highT, stress_highC, stress_highDOD

## 来源标签

- `OBSERVED`: 外部真实测量。本 G1 CSV 不包含此类字段。
- `LITERATURE_FIXED`: 文献或 G0 冻结的建模约定；本配置中的 80% SOH 仅为可调退役/RUL 阈值，不是普适安全阈值。
- `ASSUMED/CONFIGURED`: 仿真者设定的参数或工况；不是实测。
- `DERIVED_FROM_ASSUMED`: 由仿真设定和模型公式计算出的合成量。

## 字段说明

| 字段 | 类型 | 单位 | 含义 | 来源标签 |
|---|---|---|---|---|
| cell_id | str | - | 仿真电芯标识 = 场景 id + 序号 | DERIVED_FROM_ASSUMED |
| cycle | int | cycle | 配置的循环序号（时间轴） | ASSUMED/CONFIGURED |
| efc | float | EFC | 等效完整循环数 = Σ DOD/100 | DERIVED_FROM_ASSUMED |
| temperature | float | degC | 仿真环境温度 | ASSUMED/CONFIGURED |
| c_rate | float | C | 仿真充放电倍率 | ASSUMED/CONFIGURED |
| dod | float | % | 仿真放电深度 | ASSUMED/CONFIGURED |
| protocol | str | - | 仿真充电协议（仅 CC-CV） | LITERATURE_FIXED/CONFIGURED |
| capacity_true | float | Ah | 模型内部无噪声容量 = Q0_i·(1-α_i·u·L(e)) | DERIVED_FROM_ASSUMED |
| capacity_obs | float | Ah | 合成观测容量 = capacity_true + N(0,σ_Q·Q_nom) | DERIVED_FROM_ASSUMED |
| soh | float | 1 | capacity_true / Q0_i = 1-alpha_i·u·L(e) | DERIVED_FROM_ASSUMED |
| resistance_true | float | Ohm | 模型内部无噪声内阻 = R0_i·(1+β_i·u·L(e)) | DERIVED_FROM_ASSUMED |
| resistance_obs | float | Ohm | 合成观测内阻 = resistance_true + N(0,σ_R·R_true) | DERIVED_FROM_ASSUMED |
| seed | int | - | 本运行主随机种子 | ASSUMED/CONFIGURED |

## 公式与边界

- EFC = Σ(DODᵢ/100)；本数据为恒定 DOD，故 efc = cycle·DOD/100。
- L(e)=√min(e,nₖ) + knee_gain·max(0,√e−√nₖ)，knee_gain=2.0，nₖ=700 EFC。
- u_T=exp(k_T·(T−25))，u_C=1+k_C·(C_rate−0.5)，u_D=1+k_D·(DOD/100−0.5)。
- 随机效应：截断正态 N(0,σ_cell) 截断于 [−2σ,2σ]，作用于初始容量/内阻与退化速率。
- 观测噪声仅加在 obs 字段，不改变总体退化方向。
- 同配置 + 同 seed → CSV 逐字节一致；不同 seed → 合理电芯差异。
- 模拟数据非实测数据，不声称复现真实电芯或电池内部机理。
