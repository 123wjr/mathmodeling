"""复用 G1 生成器构造全因子数据，并提取只使用历史的电芯特征。"""
from __future__ import annotations

import copy
import itertools
import math
import statistics
from collections import defaultdict

import numpy as np

from g1_generator import config as g1cfg
from g1_generator import simulate


def _level_text(value: float) -> str:
    return f"{value:g}".replace(".", "p")


def scenario_id(temperature: float, c_rate: float, dod: float) -> str:
    if (temperature, c_rate, dod) == (25.0, 1.0, 80.0):
        return "baseline"
    return f"T{_level_text(temperature)}_C{_level_text(c_rate)}_D{_level_text(dod)}"


def build_factorial_g1_config(study_cfg, seed: int | None = None):
    base = copy.deepcopy(g1cfg.load_config(study_cfg.source_g1_path))
    base.seed = study_cfg.study_seed if seed is None else int(seed)
    scenarios = []
    for temperature, c_rate, dod in itertools.product(
        study_cfg.factorial.temperatures_C,
        study_cfg.factorial.c_rates_C,
        study_cfg.factorial.dod_pct,
    ):
        scenarios.append(g1cfg.Scenario(
            id=scenario_id(temperature, c_rate, dod),
            temperature_C=temperature,
            c_rate=c_rate,
            dod_pct=dod,
            n_cells=study_cfg.factorial.n_cells_per_condition,
            protocol="CC-CV",
        ))
    base.scenarios = scenarios
    g1cfg.validate_config(base)
    return base


def generate_factorial_dataset(study_cfg, seed: int | None = None):
    cfg = build_factorial_g1_config(study_cfg, seed=seed)
    dataset = simulate.generate_dataset(cfg)
    expected_cells = (
        len(study_cfg.factorial.temperatures_C)
        * len(study_cfg.factorial.c_rates_C)
        * len(study_cfg.factorial.dod_pct)
        * study_cfg.factorial.n_cells_per_condition
    )
    if dataset["meta"]["n_cells"] != expected_cells:
        raise RuntimeError("全因子数据电芯数与预注册设计不一致")
    return cfg, dataset


def group_cells(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["cell_id"])].append(row)
    for cell_id, records in grouped.items():
        records.sort(key=lambda row: int(row["cycle"]))
        cycles = [int(row["cycle"]) for row in records]
        if cycles != list(range(1, len(records) + 1)):
            raise ValueError(f"{cell_id} 的循环序列不连续")
    return dict(sorted(grouped.items()))


def condition_id(cell_id: str) -> str:
    head, separator, tail = cell_id.rpartition("_")
    if not separator or not tail.isdigit():
        raise ValueError(f"无法从 cell_id 解析工况: {cell_id}")
    return head


def linear_slope(x, y) -> float:
    x_array = np.asarray(x, dtype=float)
    y_array = np.asarray(y, dtype=float)
    if x_array.size < 2 or np.allclose(x_array, x_array[0]):
        return 0.0
    design = np.column_stack([np.ones(x_array.size), x_array])
    return float(np.linalg.lstsq(design, y_array, rcond=None)[0][1])


def _initial_estimates(records: list[dict], window: int = 10) -> tuple[float, float]:
    early = records[:window]
    q0_est = statistics.median(float(row["capacity_obs"]) for row in early)
    r0_est = statistics.median(float(row["resistance_obs"]) for row in early)
    return q0_est, r0_est


def feature_at_cycle(records: list[dict], cycle: int, history_window: int) -> dict:
    if cycle < history_window or cycle > len(records):
        raise ValueError("特征时点必须覆盖完整历史窗口并位于观测内")
    q0_est, r0_est = _initial_estimates(records)
    recent = records[cycle - history_window:cycle]
    current_window = recent[-5:]
    current_capacity = statistics.median(float(row["capacity_obs"]) for row in current_window)
    current_resistance = statistics.median(float(row["resistance_obs"]) for row in current_window)
    soh_observed = current_capacity / q0_est
    normalized_capacity = [float(row["capacity_obs"]) / q0_est for row in recent]
    normalized_resistance = [float(row["resistance_obs"]) / r0_est for row in recent]
    # Landmark 前均位于最早允许膝点（600 EFC）之前。按 G1 的 sqrt(EFC)
    # 坐标回归只供“结构匹配仿真基线”使用，不送入通用 ML 特征。
    history = records[:cycle]
    sqrt_efc = np.sqrt([float(row["efc"]) for row in history])
    capacity_history = np.asarray([float(row["capacity_obs"]) for row in history])
    structure_design = np.column_stack([np.ones(len(history)), sqrt_efc])
    structure_intercept, structure_slope = np.linalg.lstsq(
        structure_design, capacity_history, rcond=None
    )[0]
    structure_fade_rate = max(1e-8, float(-structure_slope / structure_intercept))
    current = records[cycle - 1]
    return {
        "cell_id": str(current["cell_id"]),
        "condition_id": condition_id(str(current["cell_id"])),
        "cycle": int(cycle),
        "efc": float(current["efc"]),
        "temperature": float(current["temperature"]),
        "c_rate": float(current["c_rate"]),
        "dod": float(current["dod"]),
        "soh_observed": float(soh_observed),
        "capacity_obs": float(current_capacity),
        "resistance_growth": float(current_resistance / r0_est - 1.0),
        "capacity_slope": linear_slope(
            [float(row["cycle"]) for row in recent], normalized_capacity
        ),
        "resistance_slope": linear_slope(
            [float(row["cycle"]) for row in recent], normalized_resistance
        ),
        "structure_q0_est": float(structure_intercept),
        "structure_fade_per_sqrt_efc": structure_fade_rate,
        "soh_true": float(current["soh"]),
    }


def first_threshold_crossing(records: list[dict], threshold: float) -> int | None:
    for row in records:
        if float(row["soh"]) <= threshold:
            return int(row["cycle"])
    return None


def cell_summary(records: list[dict], threshold: float, landmark_cycle: int, history_window: int) -> dict:
    feature = feature_at_cycle(records, landmark_cycle, history_window)
    crossing = first_threshold_crossing(records, threshold)
    first = records[0]
    final = records[-1]
    initial_resistance = float(first["resistance_true"])
    feature.update({
        "final_soh": float(final["soh"]),
        "capacity_fade": float(1.0 - float(final["soh"])),
        "final_resistance_growth": float(float(final["resistance_true"]) / initial_resistance - 1.0),
        "event_observed": crossing is not None,
        "lifetime_cycle": int(crossing if crossing is not None else len(records)),
        "censor_cycle": int(len(records)),
    })
    return feature


def make_cell_summaries(rows, threshold: float, landmark_cycle: int, history_window: int) -> list[dict]:
    return [
        cell_summary(records, threshold, landmark_cycle, history_window)
        for records in group_cells(rows).values()
    ]


def assert_group_disjoint(train_cell_ids, test_cell_ids) -> None:
    overlap = set(train_cell_ids) & set(test_cell_ids)
    if overlap:
        raise AssertionError(f"发现同一电芯跨训练/测试组: {sorted(overlap)[:3]}")


def supported_domain_status(temperature: float, c_rate: float, dod: float, protocol: str) -> dict:
    reasons = []
    if not g1cfg.TEMPERATURE_RANGE[0] <= temperature <= g1cfg.TEMPERATURE_RANGE[1]:
        reasons.append("temperature outside 25-50 degC")
    if not g1cfg.C_RATE_RANGE[0] <= c_rate <= g1cfg.C_RATE_RANGE[1]:
        reasons.append("c_rate outside 0.5-2C")
    if not g1cfg.DOD_RANGE[0] <= dod <= g1cfg.DOD_RANGE[1]:
        reasons.append("DOD outside 50-100%")
    if protocol != "CC-CV":
        reasons.append("protocol is not frozen CC-CV")
    return {
        "status": "[CONFIRMED] IN_DOMAIN" if not reasons else "[OOD/ABSTAIN]",
        "reasons": reasons,
        "numeric_prediction_allowed": not reasons,
    }
