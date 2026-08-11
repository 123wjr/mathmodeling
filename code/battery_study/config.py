"""研究流水线配置及科学边界校验。"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass

from g1_generator import config as g1cfg


PROJECT_ROOT = g1cfg.PROJECT_ROOT
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "study_pipeline.json")


@dataclass(frozen=True)
class FactorialSpec:
    temperatures_C: tuple[float, ...]
    c_rates_C: tuple[float, ...]
    dod_pct: tuple[float, ...]
    n_cells_per_condition: int


@dataclass(frozen=True)
class Q1Spec:
    critical_soh: float
    knee_search_min_efc: float
    knee_min_points_each_side: int


@dataclass(frozen=True)
class Q2Spec:
    history_window_cycles: int
    forecast_horizon_cycles: int
    snapshot_step_cycles: int
    landmark_cycle: int
    cv_splits: int
    bootstrap_repetitions: int
    confidence_level: float
    interval_calibration_confidence: float
    random_forest_trees: int


@dataclass(frozen=True)
class Q3Spec:
    retirement_cycle: int
    group_size: int
    target_groups: int
    min_soh: float
    min_rul_lower_cycles: float
    max_resistance_growth: float
    max_lifetime_interval_width: float
    neighbor_pool: int
    weights: dict[str, tuple[float, float, float, float]]


@dataclass(frozen=True)
class Q4Spec:
    seeds: tuple[int, ...]
    n_cells_per_scenario: int
    sensitivity_fraction: float


@dataclass(frozen=True)
class StudyConfig:
    study_id: str
    study_seed: int
    source_g1_config: str
    factorial: FactorialSpec
    q1: Q1Spec
    q2: Q2Spec
    q3: Q3Spec
    q4: Q4Spec

    @property
    def source_g1_path(self) -> str:
        if os.path.isabs(self.source_g1_config):
            return self.source_g1_config
        return os.path.join(PROJECT_ROOT, self.source_g1_config)


def _tuple_numbers(values, name):
    if not isinstance(values, list) or not values:
        raise ValueError(f"{name} 必须是非空数组")
    result = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} 必须只包含有限数值")
        result.append(float(value))
    if len(set(result)) != len(result):
        raise ValueError(f"{name} 不得包含重复水平")
    return tuple(result)


def load_config(path: str = DEFAULT_CONFIG_PATH) -> StudyConfig:
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    try:
        factorial_raw = raw["factorial"]
        q1_raw = raw["q1"]
        q2_raw = raw["q2"]
        q3_raw = raw["q3"]
        q4_raw = raw["q4"]
        weights = {
            name: tuple(float(value) for value in values)
            for name, values in q3_raw["weights"].items()
        }
        cfg = StudyConfig(
            study_id=str(raw["study_id"]),
            study_seed=int(raw["study_seed"]),
            source_g1_config=str(raw["source_g1_config"]),
            factorial=FactorialSpec(
                temperatures_C=_tuple_numbers(factorial_raw["temperatures_C"], "temperatures_C"),
                c_rates_C=_tuple_numbers(factorial_raw["c_rates_C"], "c_rates_C"),
                dod_pct=_tuple_numbers(factorial_raw["dod_pct"], "dod_pct"),
                n_cells_per_condition=int(factorial_raw["n_cells_per_condition"]),
            ),
            q1=Q1Spec(**q1_raw),
            q2=Q2Spec(**q2_raw),
            q3=Q3Spec(**{**q3_raw, "weights": weights}),
            q4=Q4Spec(
                seeds=tuple(int(value) for value in q4_raw["seeds"]),
                n_cells_per_scenario=int(q4_raw["n_cells_per_scenario"]),
                sensitivity_fraction=float(q4_raw["sensitivity_fraction"]),
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"研究配置字段无效: {exc}") from exc
    validate_config(cfg)
    return cfg


def validate_config(cfg: StudyConfig) -> None:
    errors: list[str] = []
    if not cfg.study_id.strip():
        errors.append("study_id 不得为空")
    if not os.path.isfile(cfg.source_g1_path):
        errors.append(f"source_g1_config 不存在: {cfg.source_g1_path}")

    for name, values, bounds in (
        ("temperature", cfg.factorial.temperatures_C, g1cfg.TEMPERATURE_RANGE),
        ("c_rate", cfg.factorial.c_rates_C, g1cfg.C_RATE_RANGE),
        ("dod", cfg.factorial.dod_pct, g1cfg.DOD_RANGE),
    ):
        for value in values:
            if not bounds[0] <= value <= bounds[1]:
                errors.append(f"{name}={value} 超出 G0 支持域 {bounds}")
    if cfg.factorial.n_cells_per_condition < 4:
        errors.append("全因子实验每工况至少 4 颗电芯")
    if not 0.5 < cfg.q1.critical_soh < 1.0:
        errors.append("critical_soh 必须在 (0.5, 1.0)")
    if cfg.q1.knee_min_points_each_side < 20:
        errors.append("膝点两侧至少需要 20 个观测")

    q2 = cfg.q2
    if not 20 <= q2.history_window_cycles < g1cfg.MAX_CYCLES:
        errors.append("history_window_cycles 无效")
    if q2.forecast_horizon_cycles < 1:
        errors.append("forecast_horizon_cycles 必须为正")
    if q2.history_window_cycles + q2.forecast_horizon_cycles > g1cfg.MAX_CYCLES:
        errors.append("历史窗口与预测步长超过生成范围")
    if not q2.history_window_cycles <= q2.landmark_cycle < g1cfg.MAX_CYCLES:
        errors.append("landmark_cycle 必须晚于历史窗口且早于观测终点")
    if q2.cv_splits < 3 or q2.bootstrap_repetitions < 100:
        errors.append("交叉验证至少 3 折且 bootstrap 至少 100 次")
    if not 0.5 < q2.confidence_level < 1.0:
        errors.append("confidence_level 必须在 (0.5, 1.0)")
    if not q2.confidence_level < q2.interval_calibration_confidence <= 0.999:
        errors.append("interval_calibration_confidence 必须高于目标区间置信度且不超过 0.999")

    q3 = cfg.q3
    if not q2.landmark_cycle < q3.retirement_cycle < g1cfg.MAX_CYCLES:
        errors.append("retirement_cycle 必须晚于 landmark 且早于观测终点")
    if q3.group_size < 2 or q3.target_groups < 1 or q3.neighbor_pool < q3.group_size:
        errors.append("编组规模、目标组数或近邻池无效")
    for name, weights in q3.weights.items():
        if len(weights) != 4 or any(value < 0 for value in weights):
            errors.append(f"权重方案 {name} 必须含 4 个非负权重")
        elif not math.isclose(sum(weights), 1.0, abs_tol=1e-9):
            errors.append(f"权重方案 {name} 之和必须为 1")

    if len(set(cfg.q4.seeds)) < 3:
        errors.append("鲁棒性实验至少需要 3 个不同 seed")
    if cfg.q4.n_cells_per_scenario < cfg.q3.group_size * 2:
        errors.append("Q4 每场景电芯数不足以评估编组")
    if not 0.01 <= cfg.q4.sensitivity_fraction <= 0.25:
        errors.append("sensitivity_fraction 必须在 [0.01, 0.25]")
    if errors:
        raise ValueError("研究配置校验失败: " + "; ".join(errors))
