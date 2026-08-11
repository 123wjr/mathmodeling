"""问题1：退化阶段、膝点可观测性与全因子主效应分解。"""
from __future__ import annotations

import math
import os
import statistics
from collections import Counter, defaultdict

import numpy as np

from . import common, data


FACTOR_SPECS = (
    ("temperature", "temperature_C"),
    ("c_rate", "c_rate_C"),
    ("dod", "dod_pct"),
)


def main_effect_decomposition(summaries: list[dict], response_key: str) -> list[dict]:
    """Balanced-factorial marginal sum-of-squares decomposition.

    Main-effect weights are normalized only among the three estimable main
    effects. The residual share retains interactions and cell variability.
    """
    response = np.asarray([row[response_key] for row in summaries], dtype=float)
    grand_mean = float(np.mean(response))
    total_ss = float(np.sum((response - grand_mean) ** 2))
    raw = []
    for key, label in FACTOR_SPECS:
        levels = sorted({float(row[key]) for row in summaries})
        level_means = {}
        ss = 0.0
        for level in levels:
            values = [float(row[response_key]) for row in summaries if float(row[key]) == level]
            mean = float(np.mean(values))
            level_means[level] = mean
            ss += len(values) * (mean - grand_mean) ** 2
        raw.append({
            "response": response_key,
            "factor": label,
            "sum_squares": ss,
            "share_total_variance": ss / total_ss if total_ss else 0.0,
            "effect_range": max(level_means.values()) - min(level_means.values()),
            "marginal_means": level_means,
        })
    main_ss = sum(row["sum_squares"] for row in raw)
    for row in raw:
        row["normalized_main_effect_weight"] = row["sum_squares"] / main_ss if main_ss else 0.0
        row["interaction_and_cell_share"] = max(0.0, 1.0 - main_ss / total_ss) if total_ss else 0.0
    return raw


def detect_piecewise_knee(records: list[dict], q1_cfg, nominal_knee_efc: float) -> dict:
    """Fit a continuous hinge regression to normalized observed capacity."""
    q0_est = statistics.median(float(row["capacity_obs"]) for row in records[:10])
    sampled = records[::5]
    x = np.asarray([float(row["efc"]) for row in sampled], dtype=float)
    transformed_x = np.sqrt(x)
    y = np.asarray([float(row["capacity_obs"]) / q0_est for row in sampled], dtype=float)
    max_observed_efc = float(records[-1]["efc"])
    if max_observed_efc < nominal_knee_efc:
        return {
            "status": "RIGHT_CENSORED",
            "detected_knee_efc": None,
            "nominal_knee_efc": nominal_knee_efc,
            "max_observed_efc": max_observed_efc,
            "sse": None,
            "slope_before": None,
            "slope_after": None,
        }
    min_sampled = max(5, math.ceil(q1_cfg.knee_min_points_each_side / 5))
    candidates = [
        index for index in range(min_sampled, len(x) - min_sampled)
        if x[index] >= q1_cfg.knee_search_min_efc
    ]
    best = None
    for index in candidates:
        knee = float(x[index])
        transformed_knee = math.sqrt(knee)
        design = np.column_stack([
            np.ones(x.size),
            transformed_x,
            np.maximum(0.0, transformed_x - transformed_knee),
        ])
        coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
        residual = y - design @ coefficients
        sse = float(residual @ residual)
        if best is None or sse < best[0]:
            best = (sse, knee, coefficients)
    if best is None:
        raise RuntimeError("膝点搜索没有有效候选")
    sse, knee, coefficients = best
    return {
        "status": "DETECTED_IN_SIMULATION",
        "detected_knee_efc": knee,
        "nominal_knee_efc": nominal_knee_efc,
        "max_observed_efc": max_observed_efc,
        "sse": sse,
        "slope_before": float(coefficients[1]),
        "slope_after": float(coefficients[1] + coefficients[2]),
        "slope_axis": "sqrt(EFC)",
        "absolute_error_efc": abs(knee - nominal_knee_efc),
    }


def analyze(study_cfg, g1_cfg, rows: list[dict], out_dir: str) -> dict:
    grouped = data.group_cells(rows)
    summaries = data.make_cell_summaries(
        rows,
        study_cfg.q1.critical_soh,
        study_cfg.q2.landmark_cycle,
        study_cfg.q2.history_window_cycles,
    )
    effects = []
    for response in ("capacity_fade", "final_resistance_growth"):
        effects.extend(main_effect_decomposition(summaries, response))

    knee_rows = []
    stage_counter = Counter()
    stage_by_condition = defaultdict(Counter)
    for cell_id, records in grouped.items():
        knee = detect_piecewise_knee(records, study_cfg.q1, g1_cfg.n_k_EFC)
        knee_row = {
            "cell_id": cell_id,
            "condition_id": data.condition_id(cell_id),
            "dod_pct": records[0]["dod"],
            **knee,
        }
        knee_rows.append(knee_row)
        boundary = knee["detected_knee_efc"] if knee["detected_knee_efc"] is not None else math.inf
        for row in records:
            if float(row["soh"]) <= study_cfg.q1.critical_soh:
                stage = "critical"
            elif float(row["efc"]) >= boundary:
                stage = "degradation"
            else:
                stage = "normal"
            stage_counter[stage] += 1
            stage_by_condition[data.condition_id(cell_id)][stage] += 1

    factor_rows = []
    for item in effects:
        base = {key: value for key, value in item.items() if key != "marginal_means"}
        base["marginal_means"] = ";".join(
            f"{level:g}:{mean:.8f}" for level, mean in sorted(item["marginal_means"].items())
        )
        factor_rows.append(base)
    stage_rows = [
        {
            "condition_id": condition,
            "normal_rows": counts["normal"],
            "degradation_rows": counts["degradation"],
            "critical_rows": counts["critical"],
        }
        for condition, counts in sorted(stage_by_condition.items())
    ]
    common.write_csv(os.path.join(out_dir, "q1_factor_effects.csv"), factor_rows)
    common.write_csv(os.path.join(out_dir, "q1_knee_detection.csv"), knee_rows)
    common.write_csv(os.path.join(out_dir, "q1_stage_counts.csv"), stage_rows)

    detected = [row for row in knee_rows if row["status"] == "DETECTED_IN_SIMULATION"]
    result = {
        "scope": "SYNTHETIC_INTERNAL_ANALYSIS_ONLY",
        "n_cells": len(grouped),
        "n_conditions": len({data.condition_id(cell_id) for cell_id in grouped}),
        "stage_definition": {
            "normal": "SOH > critical_soh and EFC before detected knee",
            "degradation": "SOH > critical_soh and EFC at/after detected knee",
            "critical": "simulator-internal SOH <= critical_soh",
            "critical_soh": study_cfg.q1.critical_soh,
            "status": "[ASSUMED][UPDATEABLE] modeling convention; not a universal safety standard",
        },
        "stage_counts": dict(stage_counter),
        "knee_detection": {
            "detected_cells": len(detected),
            "right_censored_cells": len(knee_rows) - len(detected),
            "median_absolute_error_efc": float(statistics.median(
                row["absolute_error_efc"] for row in detected
            )) if detected else None,
            "interpretation": "generator recovery check, not external validation",
        },
        "factor_effects": effects,
        "cycle_efc_role": "aging axes analyzed through trajectories; not treated as independent randomized factors",
        "protocol_identifiability": {
            "status": "NOT_IDENTIFIABLE",
            "reason": "all scenarios use one frozen CC-CV level",
            "weight": None,
        },
    }
    common.write_json(os.path.join(out_dir, "q1_summary.json"), result)
    return {"summary": result, "cell_summaries": summaries, "knee_rows": knee_rows}
