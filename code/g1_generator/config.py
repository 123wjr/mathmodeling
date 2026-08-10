"""G1 配置：冻结参数与工况。

所有仿真系数均来自 evidence/parameter_ledger.txt 的 ASSUMED 边界，
不在代码中改写成 CALCE 实测估计。本模块只负责加载与结构化。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class Scenario:
    id: str
    temperature_C: float
    c_rate: float
    dod_pct: float
    n_cells: int
    protocol: str = "CC-CV"


@dataclass
class Config:
    seed: int = 42
    chemistry: str = "NMC"
    Q_nom_Ah: float = 2.0          # OBSERVED: CALCE INR18650-20R 额定容量
    R0_nom_Ohm: float = 0.05       # OBSERVED: 首循环阻抗量级（台账 0.03-0.10 中段）
    N_cycles: int = 1000           # OBSERVED: 循环次数上限
    n_k_EFC: float = 700.0         # ASSUMED: 膝点位置（台账 600-850）
    knee_gain: float = 2.0         # ASSUMED/FIXED: 膝点后斜率倍数
    SOH_EOL_pct: float = 80.0      # LITERATURE_FIXED: 可调 RUL/退役阈值
    alpha: float = 0.004           # ASSUMED: 容量衰减系数（0.003-0.006）
    beta: float = 0.010            # ASSUMED: 内阻增长系数（0.005-0.020）
    k_T: float = 0.020             # ASSUMED: 温度加速系数（0.010-0.030）
    k_C: float = 0.100             # ASSUMED: 倍率加速系数（0.05-0.20）
    k_D: float = 0.500             # ASSUMED: DOD 加速系数（0.20-0.80）
    sigma_Q_pct: float = 0.6       # ASSUMED: 容量测量噪声（% of Q_nom, 0.2-1.0）
    sigma_R_pct: float = 1.5       # ASSUMED: 内阻测量噪声（% of R_true, 0.5-3.0）
    sigma_cell: float = 0.05       # ASSUMED: 电芯个体差异相对 SD（0.03-0.10）
    protocol: str = "CC-CV"
    scenarios: list = field(default_factory=list)


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    scen = [Scenario(**s) for s in data.pop("scenarios", [])]
    cfg = Config(**data)
    cfg.scenarios = scen
    return cfg


DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "configs", "g1_smoke.json",
)
