"""G1 配置、冻结边界和输入校验。

数值边界与 ``evidence/parameter_ledger.txt`` 和
``docs/Simulation_Protocol.md`` 对齐。这里的校验是 G1 的闸门：
配置一旦越界就失败，而不是在生成阶段静默截断成另一个实验。
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Any


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 冻结的 G0 边界。边界值包含端点；Q_nom 和 knee_gain 在台账中是固定值。
PARAMETER_BOUNDS = {
    "R0_nom_Ohm": (0.03, 0.10),
    "alpha": (0.003, 0.006),
    "beta": (0.005, 0.020),
    "k_T": (0.010, 0.030),
    "k_C": (0.05, 0.20),
    "k_D": (0.20, 0.80),
    "sigma_Q_pct": (0.2, 1.0),
    "sigma_R_pct": (0.5, 3.0),
    "sigma_cell": (0.03, 0.10),
    "n_k_EFC": (600.0, 850.0),
}
TEMPERATURE_RANGE = (25.0, 50.0)
C_RATE_RANGE = (0.5, 2.0)
DOD_RANGE = (50.0, 100.0)
MAX_CYCLES = 1000
Q_NOM_FIXED_AH = 2.0
KNEE_GAIN_FIXED = 2.0
SOH_EOL_FIXED_PCT = 80.0


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
    Q_nom_Ah: float = 2.0          # G0 ledger OBSERVED boundary; not loaded from raw data
    R0_nom_Ohm: float = 0.05       # G0 ledger OBSERVED range; not fitted in G1
    N_cycles: int = 1000           # CONFIGURED within the ledger's 0-1000 boundary
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
    scenarios: list[Scenario] = field(default_factory=list)


def load_config(path: str) -> Config:
    """Load and validate a JSON configuration.

    Validation also runs in :func:`g1_generator.simulate.generate_dataset` so
    callers that mutate a loaded dataclass cannot bypass the G1 boundary.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("配置根节点必须是 JSON object")

    scenarios_data = data.pop("scenarios", None)
    if scenarios_data is None:
        raise ValueError("配置缺少 scenarios")
    if not isinstance(scenarios_data, list):
        raise ValueError("scenarios 必须是 JSON array")

    scen = []
    for index, raw in enumerate(scenarios_data):
        if not isinstance(raw, dict):
            raise ValueError(f"scenario[{index}] 必须是 JSON object")
        try:
            scen.append(Scenario(**raw))
        except TypeError as exc:
            raise ValueError(f"scenario[{index}] 字段无效: {exc}") from exc
    try:
        cfg = Config(**data)
    except TypeError as exc:
        raise ValueError(f"配置字段无效: {exc}") from exc
    cfg.scenarios = scen
    validate_config(cfg)
    return cfg


DEFAULT_CONFIG_PATH = os.path.join(
    PROJECT_ROOT,
    "configs", "g1_smoke.json",
)


def _is_number(value: Any) -> bool:
    """Return true for finite real numbers, excluding booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_range(errors: list[str], name: str, value: Any, low: float, high: float) -> None:
    if not _is_number(value):
        errors.append(f"{name} 必须是有限数值")
    elif not (low <= float(value) <= high):
        errors.append(f"{name}={value} 超出冻结范围 [{low}, {high}]")


def validate_config(cfg: Config) -> None:
    """Validate the complete G1 smoke contract.

    The function deliberately reports all discovered errors together. This
    makes malformed hand-edited JSON actionable and prevents accidental
    fallback/clamping of a parameter outside the approved ledger.
    """
    errors: list[str] = []

    if not _is_int(cfg.seed):
        errors.append("seed 必须是整数")
    if cfg.chemistry != "NMC":
        errors.append(f"chemistry={cfg.chemistry!r} 不支持，G1 仅允许 NMC")
    if not _is_number(cfg.Q_nom_Ah) or not math.isclose(
        float(cfg.Q_nom_Ah), Q_NOM_FIXED_AH, rel_tol=0.0, abs_tol=1e-12
    ):
        errors.append(f"Q_nom_Ah 必须固定为 {Q_NOM_FIXED_AH} Ah")

    for name, (low, high) in PARAMETER_BOUNDS.items():
        _check_range(errors, name, getattr(cfg, name, None), low, high)

    if not _is_int(cfg.N_cycles) or not (1 <= cfg.N_cycles <= MAX_CYCLES):
        errors.append(f"N_cycles 必须是 [{1}, {MAX_CYCLES}] 内的整数")
    if not _is_number(cfg.knee_gain) or not math.isclose(
        float(cfg.knee_gain), KNEE_GAIN_FIXED, rel_tol=0.0, abs_tol=1e-12
    ):
        errors.append(f"knee_gain 必须固定为 {KNEE_GAIN_FIXED}")
    if not _is_number(cfg.SOH_EOL_pct) or not math.isclose(
        float(cfg.SOH_EOL_pct), SOH_EOL_FIXED_PCT, rel_tol=0.0, abs_tol=1e-12
    ):
        errors.append(f"SOH_EOL_pct 必须固定为 {SOH_EOL_FIXED_PCT}")
    if cfg.protocol != "CC-CV":
        errors.append(f"protocol={cfg.protocol!r} 不支持，G1 仅允许 CC-CV")

    if not isinstance(cfg.scenarios, list) or not cfg.scenarios:
        errors.append("至少需要一个 scenario")
        scenarios = []
    else:
        scenarios = cfg.scenarios

    ids: list[str] = []
    total_cells = 0
    for index, scenario in enumerate(scenarios):
        prefix = f"scenario[{index}]"
        if not isinstance(scenario, Scenario):
            errors.append(f"{prefix} 必须是 Scenario")
            continue
        if not isinstance(scenario.id, str) or not scenario.id.strip():
            errors.append(f"{prefix}.id 必须是非空字符串")
        else:
            if scenario.id in ids:
                errors.append(f"scenario id 重复: {scenario.id!r}")
            ids.append(scenario.id)
        _check_range(errors, f"{prefix}.temperature_C", scenario.temperature_C, *TEMPERATURE_RANGE)
        _check_range(errors, f"{prefix}.c_rate", scenario.c_rate, *C_RATE_RANGE)
        _check_range(errors, f"{prefix}.dod_pct", scenario.dod_pct, *DOD_RANGE)
        if not _is_int(scenario.n_cells) or scenario.n_cells < 1:
            errors.append(f"{prefix}.n_cells 必须是正整数")
        else:
            total_cells += scenario.n_cells
        if scenario.protocol != cfg.protocol:
            errors.append(
                f"{prefix}.protocol={scenario.protocol!r} 必须与全局 protocol={cfg.protocol!r} 一致"
            )

    # G1 交付契约：至少一个基准工况和三个压力/对照工况，合计至少三颗电芯。
    if scenarios:
        if "baseline" not in ids:
            errors.append("G1 必须包含 id='baseline' 的基准工况")
        if len(scenarios) < 4 or len([sid for sid in ids if sid != "baseline"]) < 3:
            errors.append("G1 至少需要 baseline + 3 个非基准工况")
    if total_cells < 3:
        errors.append("G1 至少需要 3 颗电芯")

    if errors:
        raise ValueError("配置校验失败: " + "; ".join(errors))
