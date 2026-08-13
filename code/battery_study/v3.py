"""V3 retirement-landmark decision loop and fixed-group stress tracking."""
from __future__ import annotations

import copy
import json
import math
import os
import random
import subprocess
from collections import defaultdict

import numpy as np
from sklearn.model_selection import GroupKFold

from g1_generator import degradation as g1deg

from . import common, data, q2, q3


def load_settings(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    try:
        settings = raw["v3"]
        if settings["decision_modes"] != ["POINT", "INTERVAL_RISK"]:
            raise ValueError("decision_modes 必须固定为 POINT 和 INTERVAL_RISK")
        ablation = settings["ablation"]
        if sorted(ablation["history_windows"]) != [25, 50, 100]:
            raise ValueError("消融历史窗口必须为 25/50/100")
        if ablation["common_start_cycle"] < max(ablation["history_windows"]):
            raise ValueError("消融共同起点不得早于最大历史窗口")
        if ablation["bootstrap_repetitions"] < 100:
            raise ValueError("消融 bootstrap 至少 100 次")
        allowed = set(q2.FEATURE_NAMES)
        for name, features in ablation["feature_groups"].items():
            if not features or not set(features) <= allowed:
                raise ValueError(f"消融特征组 {name} 含非法字段")
        stability = settings["stability"]
        if len(set(stability["seeds"])) != 5:
            raise ValueError("稳定性必须使用 5 个不同 seed")
        capacity_seeds = settings["capacity_seed_study"]["seeds"]
        if len(capacity_seeds) != 30 or len(set(capacity_seeds)) != 30:
            raise ValueError("容量种子研究必须使用 30 个不同 seed")
        scenarios = settings["pressure_scenarios"]
        if not scenarios or scenarios[0]["name"] != "baseline_use":
            raise ValueError("首个压力场景必须是 baseline_use")
        for scenario in scenarios:
            status = data.supported_domain_status(
                float(scenario["temperature_C"]),
                float(scenario["c_rate_C"]),
                float(scenario["dod_pct"]),
                "CC-CV",
            )
            if not status["numeric_prediction_allowed"]:
                raise ValueError(f"压力场景超出支持域: {scenario['name']}")
        triggers = settings["triggers"]
        if any(float(value) <= 0 for value in triggers.values()):
            raise ValueError("触发阈值必须为正")
        observation = settings["observation_pressure"]
        if [row["name"] for row in observation["regimes"]] != ["none", "light", "heavy"]:
            raise ValueError("观测压力必须按 none/light/heavy 冻结")
        for regime in observation["regimes"]:
            values = (
                regime["rpt_period_cycles"], regime["capacity_recovery_pct"],
                regime["resistance_recovery_pct"], regime["outlier_fraction"],
                regime["outlier_scale"],
            )
            if any(float(value) < 0 for value in values):
                raise ValueError("观测压力参数不得为负")
            if float(regime["outlier_fraction"]) > 0.01:
                raise ValueError("局部异常比例不得超过 1%")
    except (KeyError, TypeError) as exc:
        raise ValueError(f"V3 配置字段无效: {exc}") from exc
    return settings


def apply_observation_pressure(rows: list[dict], regime: dict, *, seed: int):
    """Add deterministic protocol/recovery artifacts only to observed channels."""
    required = {
        "name", "rpt_period_cycles", "capacity_recovery_pct",
        "resistance_recovery_pct", "outlier_fraction", "outlier_scale",
    }
    if not required <= set(regime):
        raise ValueError(f"观测压力缺字段: {sorted(required - set(regime))}")
    period = int(regime["rpt_period_cycles"])
    cap_recovery = float(regime["capacity_recovery_pct"]) / 100.0
    resistance_recovery = float(regime["resistance_recovery_pct"]) / 100.0
    outlier_fraction = float(regime["outlier_fraction"])
    outlier_scale = float(regime["outlier_scale"])
    if period < 0 or min(cap_recovery, resistance_recovery, outlier_fraction, outlier_scale) < 0:
        raise ValueError("观测压力参数不得为负")
    if outlier_fraction > 0.01:
        raise ValueError("局部异常比例不得超过 1%")
    if period == 0 and not any((cap_recovery, resistance_recovery, outlier_fraction, outlier_scale)):
        return copy.deepcopy(rows), {
            "regime": regime["name"], "changed_measurement_rows": 0,
            "rpt_affected_rows": 0, "outlier_rows": 0, "latent_state_unchanged": True,
        }

    output, changed, rpt_rows, outliers = [], 0, 0, 0
    for index, source in enumerate(rows):
        row = dict(source)
        cycle = int(row["cycle"])
        pulse = period > 0 and cycle >= period and cycle % period in (0, 1, 2)
        decay = (1.0, 0.55, 0.25)[cycle % period] if pulse else 0.0
        capacity_shift = float(row["capacity_true"]) * cap_recovery * decay
        resistance_shift = -float(row["resistance_true"]) * resistance_recovery * decay
        rng = random.Random(seed * 1000003 + index * 101)
        is_outlier = rng.random() < outlier_fraction
        if is_outlier:
            capacity_shift += rng.choice((-1.0, 1.0)) * outlier_scale * abs(
                float(row["capacity_obs"]) - float(row["capacity_true"])
            )
            resistance_shift += rng.choice((-1.0, 1.0)) * outlier_scale * abs(
                float(row["resistance_obs"]) - float(row["resistance_true"])
            )
            outliers += 1
        if pulse:
            rpt_rows += 1
        if capacity_shift or resistance_shift:
            row["capacity_obs"] = round(max(1e-4, float(row["capacity_obs"]) + capacity_shift), 6)
            row["resistance_obs"] = round(max(1e-4, float(row["resistance_obs"]) + resistance_shift), 6)
            changed += 1
        output.append(row)
    latent_keys = ("capacity_true", "resistance_true", "soh")
    latent_unchanged = all(
        all(before[key] == after[key] for key in latent_keys)
        for before, after in zip(rows, output)
    )
    if not latent_unchanged:
        raise RuntimeError("观测压力不得改变潜在退化状态")
    return output, {
        "regime": regime["name"], "changed_measurement_rows": changed,
        "rpt_affected_rows": rpt_rows, "outlier_rows": outliers,
        "latent_state_unchanged": latent_unchanged,
    }


def retirement_risk_set(rows, study_cfg, retirement_cycle: int, threshold: float) -> list[dict]:
    risk_rows = []
    for records in data.group_cells(rows).values():
        crossing = data.first_threshold_crossing(records, threshold)
        if crossing is not None and crossing <= retirement_cycle:
            continue
        feature = data.feature_at_cycle(
            records, retirement_cycle, study_cfg.q2.history_window_cycles
        )
        event = crossing is not None
        duration = crossing - retirement_cycle if event else len(records) - retirement_cycle
        if duration <= 0:
            raise RuntimeError("退役风险集出现非正条件时长")
        feature.update({
            "retirement_cycle": retirement_cycle,
            "event_observed": event,
            "conditional_duration": int(duration),
            "observed_or_censor_cycle": int(crossing if event else len(records)),
            "censor_duration": int(len(records) - retirement_cycle),
        })
        risk_rows.append(feature)
    return risk_rows


def cross_validated_retirement_predictions(
    risk_set: list[dict], study_cfg, *, retirement_cycle: int = 750
) -> tuple[list[dict], list[dict]]:
    """Fit censoring-aware AFT on conditional durations at one landmark."""
    if not risk_set:
        raise ValueError("退役风险集不能为空")
    x = q2._matrix(risk_set)
    duration = np.asarray([row["conditional_duration"] for row in risk_set], dtype=float)
    event = np.asarray([row["event_observed"] for row in risk_set], dtype=bool)
    groups = np.asarray([row["cell_id"] for row in risk_set])
    n_splits = min(study_cfg.q2.cv_splits, len(risk_set))
    if n_splits < 2:
        raise ValueError("退役风险集至少需要两折留组预测")
    splitter = GroupKFold(n_splits=n_splits)
    predictions: list[dict] = []
    audit: list[dict] = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(x, duration, groups), start=1):
        data.assert_group_disjoint(groups[train_idx], groups[test_idx])
        aft = q2.CensoredLogNormalAFT(
            confidence=study_cfg.q2.confidence_level,
            calibration_confidence=study_cfg.q2.interval_calibration_confidence,
        ).fit(x[train_idx], duration[train_idx], event[train_idx])
        inner_residuals = []
        inner_splits = min(4, len(set(groups[train_idx])))
        if inner_splits >= 2:
            inner_splitter = GroupKFold(n_splits=inner_splits)
            for inner_train, inner_valid in inner_splitter.split(
                x[train_idx], duration[train_idx], groups[train_idx]
            ):
                inner_model = q2.CensoredLogNormalAFT(
                    confidence=study_cfg.q2.confidence_level,
                    calibration_confidence=study_cfg.q2.interval_calibration_confidence,
                ).fit(
                    x[train_idx][inner_train], duration[train_idx][inner_train],
                    event[train_idx][inner_train],
                )
                inner_median, _, _ = inner_model.predict_lifetime(x[train_idx][inner_valid])
                valid_events = event[train_idx][inner_valid]
                if valid_events.any():
                    inner_residuals.extend(
                        np.abs(
                            np.log(duration[train_idx][inner_valid][valid_events])
                            - np.log(inner_median[valid_events])
                        ).tolist()
                    )
        if inner_residuals:
            ordered = np.sort(np.asarray(inner_residuals, dtype=float))
            rank = min(len(ordered) - 1, max(
                0, int(np.ceil((len(ordered) + 1) * study_cfg.q2.confidence_level)) - 1
            ))
            aft.interval_log_radius_ = max(aft.interval_log_radius_, float(ordered[rank]))
        median, lower, upper = aft.predict_lifetime(x[test_idx])
        train_ids = set(groups[train_idx])
        test_ids = set(groups[test_idx])
        for local_index, sample_index in enumerate(test_idx):
            row = risk_set[sample_index]
            predictions.append({
                "cell_id": row["cell_id"],
                "condition_id": row["condition_id"],
                "fold": fold,
                "landmark_cycle": retirement_cycle,
                "event_observed": bool(row["event_observed"]),
                "conditional_duration": int(row["conditional_duration"]),
                "censored_duration_lower_bound": (
                    None if row["event_observed"] else int(row["censor_duration"])
                ),
                # Keep the fitted interval intact. A 3000-cycle display cap would
                # collapse upper/lower bounds and understate screening risk.
                "predicted_rul": float(max(median[local_index], 1e-6)),
                "rul_lower_90": float(max(lower[local_index], 1e-6)),
                "rul_upper_90": float(max(upper[local_index], 1e-6)),
                "interval_calibration_method": "nested_group_oof",
                "train_test_overlap": bool(train_ids & test_ids),
            })
        audit.append({
            "fold": fold,
            "n_train_cells": len(train_ids),
            "n_test_cells": len(test_ids),
            "n_train_events": int(event[train_idx].sum()),
            "n_test_events": int(event[test_idx].sum()),
            "train_test_overlap": sorted(train_ids & test_ids),
            "n_test_cells": len(test_ids),
        })
    predictions.sort(key=lambda row: row["cell_id"])
    if len({row["cell_id"] for row in predictions}) != len(predictions):
        raise RuntimeError("退役 AFT OOF 必须每颗电芯恰好一条")
    return predictions, audit


def _candidate_from_prediction(feature: dict, prediction: dict) -> dict:
    return {
        "cell_id": feature["cell_id"],
        "condition_id": feature["condition_id"],
        "capacity_Ah": feature["capacity_obs"],
        "soh_estimate": feature["soh_observed"],
        "resistance_growth": feature["resistance_growth"],
        "predicted_rul_cycles": prediction["predicted_rul"],
        "rul_lower_cycles": prediction["rul_lower_90"],
        "lifetime_interval_width": prediction["rul_upper_90"] - prediction["rul_lower_90"],
        "event_observed": feature["event_observed"],
        "conditional_duration": feature["conditional_duration"],
    }


def build_decision_pools(
    risk_set: list[dict], predictions: list[dict], study_cfg
) -> dict[str, list[dict]]:
    by_id = {row["cell_id"]: row for row in predictions}
    if set(by_id) != {row["cell_id"] for row in risk_set}:
        raise ValueError("风险集与退役预测电芯集合不一致")
    output: dict[str, list[dict]] = {"POINT": [], "INTERVAL_RISK": []}
    q3_cfg = study_cfg.q3
    for feature in risk_set:
        base = _candidate_from_prediction(feature, by_id[feature["cell_id"]])
        output["POINT"].append(apply_decision_gate(
            base, "POINT", min_rul_cycles=q3_cfg.min_rul_lower_cycles,
            min_rul_lower_cycles=q3_cfg.min_rul_lower_cycles,
            min_soh=q3_cfg.min_soh, max_resistance_growth=q3_cfg.max_resistance_growth,
        ))
        output["INTERVAL_RISK"].append(apply_decision_gate(
            base, "INTERVAL_RISK", min_rul_cycles=q3_cfg.min_rul_lower_cycles,
            min_rul_lower_cycles=q3_cfg.min_rul_lower_cycles,
            min_soh=q3_cfg.min_soh, max_resistance_growth=q3_cfg.max_resistance_growth,
            max_interval_width=q3_cfg.max_lifetime_interval_width,
        ))
    return output


def apply_decision_gate(
    candidate: dict,
    mode: str,
    *,
    min_rul_cycles: float,
    min_rul_lower_cycles: float,
    min_soh: float = -math.inf,
    max_resistance_growth: float = math.inf,
    max_interval_width: float = math.inf,
) -> dict:
    if mode not in {"POINT", "INTERVAL_RISK"}:
        raise ValueError(f"未知决策模式: {mode}")
    output = dict(candidate)
    failures = []
    if output["soh_estimate"] < min_soh:
        failures.append("SOH_BELOW_MIN")
    if output["resistance_growth"] > max_resistance_growth:
        failures.append("RESISTANCE_GROWTH_ABOVE_MAX")
    if mode == "POINT":
        if output["predicted_rul_cycles"] < min_rul_cycles:
            failures.append("RUL_POINT_BELOW_MIN")
        output["decision_rul_cycles"] = output["predicted_rul_cycles"]
        output["actual_interval_width"] = output["lifetime_interval_width"]
        output["lifetime_interval_width"] = 0.0
    else:
        if output["rul_lower_cycles"] < min_rul_lower_cycles:
            failures.append("RUL_LOWER_BELOW_MIN")
        if output["lifetime_interval_width"] > max_interval_width:
            failures.append("UNCERTAINTY_ABOVE_MAX")
        output["decision_rul_cycles"] = output["rul_lower_cycles"]
        output["actual_interval_width"] = output["lifetime_interval_width"]
    output["decision_mode"] = mode
    output["eligible"] = not failures
    output["grade"] = "A" if not failures and output["soh_estimate"] >= 0.85 else (
        "B" if not failures else "REJECT"
    )
    output["gate_failures"] = ";".join(failures) if failures else "NONE"
    return output


def jaccard(left, right) -> float:
    left, right = set(left), set(right)
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _cell_identity(cell_id: str, g1_cfg) -> tuple[int, int]:
    scenario_name, separator, cell_text = cell_id.rpartition("_")
    if not separator or not cell_text.isdigit():
        raise ValueError(f"无法解析电芯标识: {cell_id}")
    matches = [index for index, scenario in enumerate(g1_cfg.scenarios) if scenario.id == scenario_name]
    if len(matches) != 1:
        raise ValueError(f"无法定位电芯原工况: {cell_id}")
    return matches[0], int(cell_text)


def track_fixed_cell(
    *,
    cell_id: str,
    records: list[dict],
    g1_cfg,
    stress: tuple[float, float, float],
    retirement_cycle: int,
) -> list[dict]:
    temperature, c_rate, dod = map(float, stress)
    domain = data.supported_domain_status(temperature, c_rate, dod, "CC-CV")
    if not domain["numeric_prediction_allowed"]:
        raise ValueError(f"压力追踪超出支持域: {domain['reasons']}")
    scenario_index, cell_index = _cell_identity(cell_id, g1_cfg)
    rng = random.Random(g1deg.cell_seed(g1_cfg.seed, scenario_index, cell_index))
    params = g1deg.make_cell_params(rng, g1_cfg)
    historical = g1_cfg.scenarios[scenario_index]
    historical_u = math.prod(g1deg.u_factors(
        historical.temperature_C, historical.c_rate, historical.dod_pct, g1_cfg
    ))
    stress_u = math.prod(g1deg.u_factors(temperature, c_rate, dod, g1_cfg))
    boundary = records[retirement_cycle - 1]
    boundary_efc = float(boundary["efc"])
    boundary_accumulated = historical_u * g1deg.L(boundary_efc, g1_cfg)
    reconstructed_soh = 1.0 - params["alpha"] * boundary_accumulated
    reconstructed_capacity = params["Q0"] * reconstructed_soh
    reconstructed_resistance = params["R0"] * (1.0 + params["beta"] * boundary_accumulated)
    formula_error = max(
        abs(reconstructed_soh - float(boundary["soh"])),
        abs(reconstructed_capacity - float(boundary["capacity_true"])),
        abs(reconstructed_resistance - float(boundary["resistance_true"])),
    )
    if formula_error > 1e-6:
        raise RuntimeError(f"{cell_id} cycle 750 状态无法由原电芯参数重建")
    output = [{
        "cell_id": cell_id,
        "cycle": retirement_cycle,
        "efc": boundary_efc,
        # cycle=750 remains part of the observed historical trajectory.  The
        # requested stress scene starts at cycle=751.
        "temperature": float(boundary["temperature"]),
        "c_rate": float(boundary["c_rate"]),
        "dod": float(boundary["dod"]),
        "capacity_true": float(boundary["capacity_true"]),
        "soh": float(boundary["soh"]),
        "resistance_true": float(boundary["resistance_true"]),
        "formula_continuity_error": formula_error,
    }]
    for cycle in range(retirement_cycle + 1, len(records) + 1):
        efc = boundary_efc + (cycle - retirement_cycle) * dod / 100.0
        accumulated = (
            historical_u * g1deg.L(boundary_efc, g1_cfg)
            + stress_u * (g1deg.L(efc, g1_cfg) - g1deg.L(boundary_efc, g1_cfg))
        )
        soh = 1.0 - params["alpha"] * accumulated
        capacity = params["Q0"] * soh
        resistance = params["R0"] * (1.0 + params["beta"] * accumulated)
        if not all(math.isfinite(value) and value > 0 for value in (soh, capacity, resistance)):
            raise RuntimeError(f"{cell_id} 压力追踪生成非物理状态")
        output.append({
            "cell_id": cell_id,
            "cycle": cycle,
            "efc": float(efc),
            "temperature": temperature,
            "c_rate": c_rate,
            "dod": dod,
            "capacity_true": float(capacity),
            "soh": float(soh),
            "resistance_true": float(resistance),
            "formula_continuity_error": None,
        })
    return output


def _decision_candidates_for_config(risk_set, predictions, study_cfg, *, mode, min_soh=None,
                                    min_rul_lower_cycles=None, max_resistance_growth=None,
                                    weights_name="balanced"):
    q3_cfg = study_cfg.q3
    by_id = {row["cell_id"]: row for row in predictions}
    candidates = []
    for feature in risk_set:
        prediction = by_id[feature["cell_id"]]
        base = _candidate_from_prediction(feature, prediction)
        candidates.append(apply_decision_gate(
            base, mode,
            min_rul_cycles=q3_cfg.min_rul_lower_cycles,
            min_rul_lower_cycles=(q3_cfg.min_rul_lower_cycles
                                  if min_rul_lower_cycles is None else min_rul_lower_cycles),
            min_soh=q3_cfg.min_soh if min_soh is None else min_soh,
            max_resistance_growth=(q3_cfg.max_resistance_growth
                                   if max_resistance_growth is None else max_resistance_growth),
            max_interval_width=q3_cfg.max_lifetime_interval_width,
        ))
    return candidates, tuple(q3_cfg.weights[weights_name])


def optimize_decision(
    candidates,
    study_cfg,
    weights,
    *,
    target_groups=None,
    normalization_bounds=None,
):
    eligible = [row for row in candidates if row["eligible"]]
    requested = study_cfg.q3.target_groups if target_groups is None else target_groups
    empty = {
        "groups": [], "selected": [], "objective": None, "n_groups": 0,
        "eligible_cells": len(eligible), "selected_cell_ids": [],
        "weakest_selected_soh": None, "weakest_selected_rul_lower_cycles": None,
        "largest_selected_resistance_growth": None, "largest_selected_interval_width": None,
        "target_groups": 0, "requested_groups": requested, "max_feasible_groups": 0,
        "group_shortfall": requested, "thresholds_relaxed": False,
        "decision_status": "ABSTAIN_INSUFFICIENT_FEASIBILITY",
    }
    if len(eligible) < study_cfg.q3.group_size:
        return {
            **empty, "solver_status": "NO_FEASIBLE_GROUP_TARGET",
            "abstention_reasons": "INSUFFICIENT_ELIGIBLE_CELLS",
        }
    decision_candidates = [
        {
            **row,
            "predicted_rul_cycles": row.get(
                "decision_rul_cycles", row["predicted_rul_cycles"]
            ),
        }
        for row in candidates
    ]
    groups = q3.enumerate_candidate_groups(
        decision_candidates,
        study_cfg.q3.group_size,
        study_cfg.q3.neighbor_pool,
        normalization_bounds=normalization_bounds,
    )
    if not groups:
        return {
            **empty, "solver_status": "NO_CANDIDATE_GROUPS",
            "abstention_reasons": "NO_COMPATIBLE_CANDIDATE_GROUPS",
            "normalization_bounds": normalization_bounds,
        }
    maximum = q3.maximum_disjoint_group_count(groups)
    target = min(requested, maximum)
    if target < 1:
        return {
            **empty, "groups": groups, "solver_status": "NO_DISJOINT_GROUPS",
            "abstention_reasons": "NO_MUTUALLY_DISJOINT_GROUPS",
            "normalization_bounds": normalization_bounds,
        }
    solution = q3.solve_milp(groups, weights, target)
    members = [cell for group in solution["selected"] for cell in group["members"]]
    selected_ids = set(members)
    selected_candidates = [row for row in eligible if row["cell_id"] in selected_ids]
    return {
        "groups": groups,
        "selected": solution["selected"],
        "objective": solution["objective"],
        "n_groups": len(solution["selected"]),
        "solver_status": solution["solver_status"],
        "eligible_cells": len(eligible),
        "selected_cell_ids": sorted(members),
        "weakest_selected_soh": min(row["soh_estimate"] for row in selected_candidates),
        "weakest_selected_rul_lower_cycles": min(
            row["rul_lower_cycles"] for row in selected_candidates
        ),
        "largest_selected_resistance_growth": max(
            row["resistance_growth"] for row in selected_candidates
        ),
        "largest_selected_interval_width": max(
            row["actual_interval_width"] for row in selected_candidates
        ),
        "target_groups": target,
        "requested_groups": requested,
        "max_feasible_groups": maximum,
        "group_shortfall": requested - target,
        "thresholds_relaxed": False,
        "decision_status": (
            "ACCEPT_FIXED_GROUPS" if target == requested
            else "ABSTAIN_INSUFFICIENT_FEASIBILITY"
        ),
        "abstention_reasons": (
            "NONE" if target == requested else
            ("INSUFFICIENT_ELIGIBLE_CELLS" if len(eligible) < requested * study_cfg.q3.group_size
             else "GROUP_COMPATIBILITY_LIMIT")
        ),
        "weights": list(weights),
        "normalization_bounds": q3.group_normalization_bounds(groups)
        if normalization_bounds is None else normalization_bounds,
    }


def _run_decision_for_seed(study_cfg, seed, mode="INTERVAL_RISK", *, min_soh=None,
                           min_rul_lower_cycles=None, max_resistance_growth=None,
                           weights_name="balanced"):
    from . import data as study_data

    local_cfg, dataset = study_data.generate_factorial_dataset(study_cfg, seed=seed)
    risk_set = retirement_risk_set(
        dataset["rows"], study_cfg, study_cfg.q3.retirement_cycle, study_cfg.q1.critical_soh
    )
    predictions, audit = cross_validated_retirement_predictions(risk_set, study_cfg)
    candidates, weights = _decision_candidates_for_config(
        risk_set, predictions, study_cfg, mode=mode,
        min_soh=min_soh, min_rul_lower_cycles=min_rul_lower_cycles,
        max_resistance_growth=max_resistance_growth, weights_name=weights_name,
    )
    solution = optimize_decision(candidates, study_cfg, weights)
    return {
        "g1_cfg": local_cfg,
        "dataset": dataset,
        "risk_set": risk_set,
        "predictions": predictions,
        "audit": audit,
        "candidates": candidates,
        "solution": solution,
    }


def stability_sweep(study_cfg, settings, *, seeds=None) -> list[dict]:
    """OAT decision scan; all rows compare with same-seed balanced baseline."""
    stability = settings["stability"]
    scan_seeds = tuple(stability["seeds"] if seeds is None else seeds)
    rows = []
    for seed in scan_seeds:
        base = _run_decision_for_seed(study_cfg, seed)
        base_ids = set(base["solution"].get("selected_cell_ids", []))
        scenarios = [("baseline", {}, "balanced")]
        scenarios.extend(("min_soh", {"min_soh": value}, "balanced")
                         for value in stability["min_soh"] if value != study_cfg.q3.min_soh)
        scenarios.extend(("min_rul_lower_cycles", {"min_rul_lower_cycles": value}, "balanced")
                         for value in stability["min_rul_lower_cycles"]
                         if value != study_cfg.q3.min_rul_lower_cycles)
        scenarios.extend(("max_resistance_growth", {"max_resistance_growth": value}, "balanced")
                         for value in stability["max_resistance_growth"]
                         if value != study_cfg.q3.max_resistance_growth)
        scenarios.extend(("weights", {}, name) for name in ("performance", "conservative"))
        for parameter, overrides, weight_name in scenarios:
            if parameter == "baseline":
                candidates = base["candidates"]
                solution = base["solution"]
            else:
                candidates, weights = _decision_candidates_for_config(
                    base["risk_set"], base["predictions"], study_cfg,
                    mode="INTERVAL_RISK",
                    min_soh=overrides.get("min_soh"),
                    min_rul_lower_cycles=overrides.get("min_rul_lower_cycles"),
                    max_resistance_growth=overrides.get("max_resistance_growth"),
                    weights_name=weight_name,
                )
                solution = optimize_decision(
                    candidates, study_cfg, weights,
                    normalization_bounds=base["solution"].get("normalization_bounds"),
                )
            selected = set(solution.get("selected_cell_ids", []))
            selected_candidates = [row for row in candidates if row["cell_id"] in selected]
            min_soh = overrides.get("min_soh", study_cfg.q3.min_soh)
            min_rul = overrides.get(
                "min_rul_lower_cycles", study_cfg.q3.min_rul_lower_cycles
            )
            max_resistance = overrides.get(
                "max_resistance_growth", study_cfg.q3.max_resistance_growth
            )
            actual_margins = {
                "worst_selected_soh_margin": [],
                "worst_selected_rul_lower_margin_cycles": [],
                "worst_selected_resistance_growth_margin": [],
                "worst_selected_interval_width_margin_cycles": [],
            }
            for row in selected_candidates:
                actual_margins["worst_selected_soh_margin"].append(
                    row["soh_estimate"] - min_soh
                )
                actual_margins["worst_selected_rul_lower_margin_cycles"].append(
                    row["rul_lower_cycles"] - min_rul
                )
                actual_margins["worst_selected_resistance_growth_margin"].append(
                    max_resistance - row["resistance_growth"]
                )
                actual_margins["worst_selected_interval_width_margin_cycles"].append(
                    study_cfg.q3.max_lifetime_interval_width - row["actual_interval_width"]
                )
            changed = len(overrides) + (0 if weight_name == "balanced" else 1)
            reference_solution = base["solution"]
            if weight_name != "balanced":
                reference_candidates, reference_weights = _decision_candidates_for_config(
                    base["risk_set"], base["predictions"], study_cfg,
                    mode="INTERVAL_RISK", weights_name=weight_name,
                )
                reference_solution = optimize_decision(
                    reference_candidates, study_cfg, reference_weights,
                    normalization_bounds=base["solution"].get("normalization_bounds"),
                )
            objective_delta = (
                solution["objective"] - reference_solution["objective"]
                if solution["objective"] is not None
                and reference_solution["objective"] is not None else None
            )
            rows.append({
                "seed": seed,
                "parameter": parameter,
                "parameter_value": (None if parameter == "weights" else next(iter(overrides.values()), None)),
                "weights_name": weight_name,
                "changed_parameter_count": changed,
                "risk_set_cells": len(base["risk_set"]),
                "eligible_cells": solution["eligible_cells"],
                "eligible_rate": solution["eligible_cells"] / len(base["risk_set"]),
                "n_groups": solution["n_groups"],
                "infeasible": solution["n_groups"] < study_cfg.q3.target_groups,
                "decision_status": solution["decision_status"],
                "requested_groups": solution["requested_groups"],
                "max_feasible_groups": solution["max_feasible_groups"],
                "group_shortfall": solution["group_shortfall"],
                "abstention_reasons": solution["abstention_reasons"],
                "thresholds_relaxed": solution["thresholds_relaxed"],
                "objective": solution["objective"],
                "objective_delta": objective_delta,
                "selected_cell_jaccard": jaccard(base_ids, selected),
                "selected_cell_count": len(selected),
                "selected_cell_ids": sorted(selected),
                **{
                    name: (min(values) if values else None)
                    for name, values in actual_margins.items()
                },
                "solver_status": solution["solver_status"],
            })
    return rows


def capacity_seed_study(study_cfg, settings, *, seeds=None) -> tuple[list[dict], dict]:
    """Estimate credible capacity from independent baseline decision seeds."""
    study_seeds = tuple(
        settings["capacity_seed_study"]["seeds"] if seeds is None else seeds
    )
    if not study_seeds or len(set(study_seeds)) != len(study_seeds):
        raise ValueError("容量种子研究 seed 必须非空且唯一")
    rows = []
    for seed in study_seeds:
        result = _run_decision_for_seed(study_cfg, seed, mode="INTERVAL_RISK")
        solution = result["solution"]
        rows.append({
            "seed": int(seed),
            "decision_mode": "INTERVAL_RISK",
            "risk_set_cells": len(result["risk_set"]),
            "eligible_cells": solution["eligible_cells"],
            "eligible_rate": solution["eligible_cells"] / len(result["risk_set"]),
            "n_groups": solution["n_groups"],
            "max_feasible_groups": solution["max_feasible_groups"],
            "requested_groups": solution["requested_groups"],
            "group_shortfall": solution["group_shortfall"],
            "decision_status": solution["decision_status"],
            "thresholds_relaxed": solution["thresholds_relaxed"],
            "abstention_reasons": solution["abstention_reasons"],
            "selected_cell_count": len(solution.get("selected_cell_ids", [])),
            "selected_cell_ids": sorted(solution.get("selected_cell_ids", [])),
            "solver_status": solution["solver_status"],
        })
    max_groups = [row["max_feasible_groups"] for row in rows]
    requested = rows[0]["requested_groups"]
    summary = {
        "scope": "CROSS_SEED_BASELINE_INTERVAL_RISK_CAPACITY",
        "decision_mode": "INTERVAL_RISK",
        "n_seeds": len(rows),
        "seeds": [row["seed"] for row in rows],
        "max_feasible_groups_min": min(max_groups),
        "max_feasible_groups_median": float(np.median(max_groups)),
        "max_feasible_groups_max": max(max_groups),
        "at_least_group_rates": {
            str(group): sum(value >= group for value in max_groups) / len(max_groups)
            for group in range(4, requested + 1)
        },
        "accept_count": sum(row["decision_status"] == "ACCEPT_FIXED_GROUPS" for row in rows),
        "abstention_count": sum(row["decision_status"] != "ACCEPT_FIXED_GROUPS" for row in rows),
        "thresholds_relaxed_count": sum(row["thresholds_relaxed"] for row in rows),
        "evidence_label": "[RESULT][UPDATEABLE] synthetic cross-seed empirical distribution",
    }
    return rows, summary


def summarize_stability(rows: list[dict]) -> dict:
    objective_deltas = [row["objective_delta"] for row in rows if row["objective_delta"] is not None]
    jaccards = [row["selected_cell_jaccard"] for row in rows]
    eligible_rates = [row["eligible_rate"] for row in rows]
    margin_names = (
        "worst_selected_soh_margin",
        "worst_selected_rul_lower_margin_cycles",
        "worst_selected_resistance_growth_margin",
        "worst_selected_interval_width_margin_cycles",
    )
    return {
        "jaccard_min": min(jaccards) if jaccards else None,
        "jaccard_max": max(jaccards) if jaccards else None,
        "eligible_rate_min": min(eligible_rates) if eligible_rates else None,
        "eligible_rate_max": max(eligible_rates) if eligible_rates else None,
        "objective_delta_min": min(objective_deltas) if objective_deltas else None,
        "objective_delta_max": max(objective_deltas) if objective_deltas else None,
        **{
            f"{name}_min": min(
                row[name] for row in rows if row[name] is not None
            ) if any(row[name] is not None for row in rows) else None
            for name in margin_names
        },
        "infeasible_count": sum(row["infeasible"] for row in rows),
        "abstention_count": sum(
            row.get("decision_status") == "ABSTAIN_INSUFFICIENT_FEASIBILITY"
            for row in rows
        ),
        "group_shortfall_max": max(
            (row.get("group_shortfall", 0) for row in rows), default=0
        ),
        "threshold_relaxation_count": sum(row.get("thresholds_relaxed", False) for row in rows),
    }


def run_observation_sensitivity(study_cfg, settings, rows: list[dict]) -> dict:
    """Stress observable channels while preserving the registered latent paths."""
    metric_rows, decision_rows, audits = [], [], []
    baseline_selected: set[str] | None = None
    baseline_ranking: list[str] | None = None
    seed = int(settings["observation_pressure"]["seed"])
    for regime in settings["observation_pressure"]["regimes"]:
        observed_rows, observation_audit = apply_observation_pressure(rows, regime, seed=seed)
        grouped = data.group_cells(observed_rows)
        samples = q2.make_soh_samples(grouped, study_cfg)
        soh_predictions, split_audit = q2.cross_validated_soh_predictions(samples, study_cfg)
        metrics = q2._prediction_metrics(
            soh_predictions, "target_soh", "predicted_soh", study_cfg
        )
        ordered = sorted(metrics, key=lambda row: (row["rmse"], row["model"]))
        ranking = [row["model"] for row in ordered]
        if baseline_ranking is None:
            baseline_ranking = ranking
        persistence_rmse = next(row["rmse"] for row in metrics if row["model"] == "persistence")
        for rank, metric in enumerate(ordered, start=1):
            metric_rows.append({
                "regime": regime["name"], "rank": rank,
                "ranking_changed_vs_none": ranking != baseline_ranking,
                "relative_rmse_vs_persistence": metric["rmse"] / persistence_rmse - 1.0,
                **{key: regime[key] for key in (
                    "rpt_period_cycles", "capacity_recovery_pct",
                    "resistance_recovery_pct", "outlier_fraction", "outlier_scale",
                )},
                **metric,
            })
        risk_set = retirement_risk_set(
            observed_rows, study_cfg, study_cfg.q3.retirement_cycle,
            study_cfg.q1.critical_soh,
        )
        retirement_predictions, retirement_audit = cross_validated_retirement_predictions(
            risk_set, study_cfg
        )
        candidates = build_decision_pools(
            risk_set, retirement_predictions, study_cfg
        )["INTERVAL_RISK"]
        solution = optimize_decision(
            candidates, study_cfg, tuple(study_cfg.q3.weights["balanced"])
        )
        selected = set(solution.get("selected_cell_ids", []))
        if baseline_selected is None:
            baseline_selected = selected
        decision_rows.append({
            "regime": regime["name"],
            "risk_set_cells": len(risk_set),
            "eligible_cells": solution["eligible_cells"],
            "requested_groups": solution["requested_groups"],
            "max_feasible_groups": solution["max_feasible_groups"],
            "selected_groups": solution["n_groups"],
            "group_shortfall": solution["group_shortfall"],
            "decision_status": solution["decision_status"],
            "abstention_reasons": solution["abstention_reasons"],
            "thresholds_relaxed": solution["thresholds_relaxed"],
            "selected_cell_jaccard_vs_none": jaccard(baseline_selected, selected),
            "selected_cell_ids": ";".join(sorted(selected)),
        })
        audits.append({
            **observation_audit,
            "q2_split_overlap": sum(len(row["cell_overlap"]) for row in split_audit),
            "retirement_split_overlap": sum(
                len(row["train_test_overlap"]) for row in retirement_audit
            ),
        })
    return {
        "model_metrics": metric_rows,
        "decision_rows": decision_rows,
        "audits": audits,
        "ranking_flip_regimes": sorted({
            row["regime"] for row in metric_rows if row["ranking_changed_vs_none"]
        }),
    }


def _ablation_matrix(samples, feature_names):
    return np.asarray([[float(row[name]) for name in feature_names] for row in samples], dtype=float)


def _ablation_samples(grouped, study_cfg, window, start_cycle):
    samples = []
    horizon = study_cfg.q2.forecast_horizon_cycles
    for records in grouped.values():
        for cycle in range(start_cycle, len(records) - horizon + 1, study_cfg.q2.snapshot_step_cycles):
            feature = data.feature_at_cycle(records, cycle, window)
            feature["target_soh"] = float(records[cycle + horizon - 1]["soh"])
            feature["forecast_cycle"] = cycle + horizon
            samples.append(feature)
    return samples


def run_ablation(study_cfg, settings, rows) -> list[dict]:
    """Run fixed-window, fixed-feature-group SOH comparisons."""
    grouped = data.group_cells(rows)
    ablation = settings["ablation"]
    output = []
    for window in ablation["history_windows"]:
        samples = _ablation_samples(grouped, study_cfg, window, ablation["common_start_cycle"])
        groups = np.asarray([row["cell_id"] for row in samples])
        y = np.asarray([row["target_soh"] for row in samples], dtype=float)
        for feature_group, feature_names in ablation["feature_groups"].items():
            x = _ablation_matrix(samples, feature_names)
            model_records = defaultdict(list)
            for fold, (train_idx, test_idx) in enumerate(
                GroupKFold(n_splits=study_cfg.q2.cv_splits).split(x, y, groups), start=1
            ):
                data.assert_group_disjoint(groups[train_idx], groups[test_idx])
                models = {
                    "persistence": np.asarray([samples[index]["soh_observed"] for index in test_idx]),
                    "local_linear": np.asarray([
                        samples[index]["soh_observed"]
                        + samples[index]["capacity_slope"] * study_cfg.q2.forecast_horizon_cycles
                        for index in test_idx
                    ]),
                }
                for name, model in q2._soh_models(
                    study_cfg.study_seed + window + fold, max(60, study_cfg.q2.random_forest_trees // 2)
                ).items():
                    model.fit(x[train_idx], y[train_idx])
                    models[name] = model.predict(x[test_idx])
                for model_name, prediction in models.items():
                    for local_index, sample_index in enumerate(test_idx):
                        model_records[model_name].append({
                            "cell_id": samples[sample_index]["cell_id"],
                            "target_soh": float(y[sample_index]),
                            "predicted_soh": float(prediction[local_index]),
                        })
            for model_name, records in sorted(model_records.items()):
                metrics = common.regression_metrics(
                    [row["target_soh"] for row in records],
                    [row["predicted_soh"] for row in records],
                )
                intervals = common.grouped_bootstrap_interval(
                    records, "target_soh", "predicted_soh", "cell_id",
                    ablation["bootstrap_repetitions"], study_cfg.q2.confidence_level,
                    study_cfg.study_seed + window + len(output),
                )
                output.append({
                    "history_window": window,
                    "feature_group": feature_group,
                    "feature_names": ";".join(feature_names),
                    "model": model_name,
                    "n_rows": len(records),
                    "n_cells": len({row["cell_id"] for row in records}),
                    **metrics,
                    **{
                        f"{name}_{bound}": value
                        for name, bounds in intervals.items()
                        for bound, value in zip(("ci_low", "ci_high"), bounds)
                    },
                })
    return output


def summarize_ablation(rows: list[dict]) -> dict:
    best = min(rows, key=lambda row: (row["rmse"], row["model"], row["feature_group"]))
    lookup = {
        (row["model"], row["history_window"], row["feature_group"]): row
        for row in rows
    }
    comparisons = []
    for model in ("random_forest", "ridge"):
        windows = sorted({
            row["history_window"] for row in rows
            if row["model"] == model
        })
        for window in windows:
            capacity = lookup.get((model, window, "capacity"))
            full = lookup.get((model, window, "all"))
            if capacity is None or full is None:
                continue
            capacity_rmse = float(capacity["rmse"])
            full_rmse = float(full["rmse"])
            comparisons.append({
                "model": model,
                "history_window": window,
                "capacity_only_rmse": capacity_rmse,
                "all_features_rmse": full_rmse,
                "relative_rmse_reduction": (
                    (capacity_rmse - full_rmse) / capacity_rmse
                    if capacity_rmse else None
                ),
            })
    return {
        "best_configuration": dict(best),
        "all_vs_capacity_only": comparisons,
    }


def _trigger_status(group, triggers, endpoint_soh: float = 0.8):
    if (
        float(group.get("weakest_soh", math.inf)) <= endpoint_soh
        or int(group.get("post_750_event_count", 0)) > 0
    ):
        return "REJECT_FORCED_ASSIGNMENT"
    if group["soh_range"] > triggers["max_soh_range"] or group["resistance_range"] > triggers["max_resistance_growth_range"]:
        return "REJECT_FORCED_ASSIGNMENT"
    if group["capacity_cv"] > triggers["max_capacity_cv"]:
        return "REINSPECT"
    if group["rul_cv"] is not None and group["rul_cv"] > triggers["max_rul_cv"]:
        return "REINSPECT"
    return "STABLE_UNDER_SCENARIO"


def _add_rul_change_bounds(cell_rows):
    baseline = {
        row["cell_id"]: row for row in cell_rows if row["scenario"] == "baseline_use"
    }
    if not baseline:
        raise RuntimeError("固定编组压力追踪缺少 baseline_use RUL 参考")
    for row in cell_rows:
        reference = baseline[row["cell_id"]]
        if row["scenario"] == "baseline_use":
            row.update({
                "rul_change_status": "REFERENCE",
                "rul_change_cycles": 0.0,
                "rul_change_lower_bound_cycles": 0.0,
                "rul_change_upper_bound_cycles": 0.0,
            })
        elif reference["post_750_event_observed"] and row["post_750_event_observed"]:
            change = (
                row["post_750_observed_or_censor_duration"]
                - reference["post_750_observed_or_censor_duration"]
            )
            row.update({
                "rul_change_status": "EXACT_BOTH_EVENTS",
                "rul_change_cycles": change,
                "rul_change_lower_bound_cycles": change,
                "rul_change_upper_bound_cycles": change,
            })
        elif not reference["post_750_event_observed"] and row["post_750_event_observed"]:
            row.update({
                "rul_change_status": "UPPER_BOUND",
                "rul_change_cycles": None,
                "rul_change_lower_bound_cycles": None,
                "rul_change_upper_bound_cycles": (
                    row["post_750_observed_or_censor_duration"]
                    - reference["post_750_observed_or_censor_duration"]
                ),
            })
        elif reference["post_750_event_observed"] and not row["post_750_event_observed"]:
            row.update({
                "rul_change_status": "LOWER_BOUND",
                "rul_change_cycles": None,
                "rul_change_lower_bound_cycles": (
                    row["post_750_observed_or_censor_duration"]
                    - reference["post_750_observed_or_censor_duration"]
                ),
                "rul_change_upper_bound_cycles": None,
            })
        else:
            row.update({
                "rul_change_status": "NOT_IDENTIFIABLE_BOTH_RIGHT_CENSORED",
                "rul_change_cycles": None,
                "rul_change_lower_bound_cycles": None,
                "rul_change_upper_bound_cycles": None,
            })


def _group_rul_change_status(statuses: list[str]) -> str:
    unique = set(statuses)
    if not unique:
        return "NOT_IDENTIFIABLE_BOTH_RIGHT_CENSORED"
    if unique == {"REFERENCE"}:
        return "REFERENCE"
    if unique == {"EXACT_BOTH_EVENTS"}:
        return "EXACT_BOTH_EVENTS"
    if unique == {"NOT_IDENTIFIABLE_BOTH_RIGHT_CENSORED"}:
        return "NOT_IDENTIFIABLE_BOTH_RIGHT_CENSORED"
    if unique <= {"EXACT_BOTH_EVENTS", "UPPER_BOUND"} and "UPPER_BOUND" in unique:
        return "UPPER_BOUND"
    if unique <= {"EXACT_BOTH_EVENTS", "LOWER_BOUND"} and "LOWER_BOUND" in unique:
        return "LOWER_BOUND"
    return "CENSORING_MIXED_NOT_IDENTIFIABLE"


def _add_group_change_summary(group_summary: list[dict], cell_rows: list[dict]) -> None:
    for summary in group_summary:
        cells = [
            row for row in cell_rows
            if row["scenario"] == summary["scenario"]
            and row["group_number"] == summary["group_number"]
        ]
        if not cells:
            raise RuntimeError("组级摘要找不到对应单芯记录")
        soh_changes = [float(row["soh_change"]) for row in cells]
        resistance_changes = [
            float(row["resistance_growth_increment"]) for row in cells
        ]
        statuses = [row["rul_change_status"] for row in cells]
        exact_changes = [
            float(row["rul_change_cycles"])
            for row in cells
            if row["rul_change_status"] == "EXACT_BOTH_EVENTS"
        ]
        summary.update({
            "mean_soh_change": float(np.mean(soh_changes)),
            "mean_resistance_growth_increment": float(np.mean(resistance_changes)),
            "group_rul_change_status": _group_rul_change_status(statuses),
            "mean_rul_change_cycles": (
                float(np.mean(exact_changes))
                if len(exact_changes) == len(cells) else None
            ),
        })


def track_fixed_groups(
    rows, g1_cfg, study_cfg, settings, candidates, *, decision_mode="INTERVAL_RISK"
) -> dict:
    """Track one selected group signature through all registered stress scenes."""
    if decision_mode not in {"POINT", "INTERVAL_RISK"}:
        raise ValueError(f"未知固定编组决策模式: {decision_mode}")
    solution = optimize_decision(candidates, study_cfg, tuple(study_cfg.q3.weights["balanced"]))
    if solution["n_groups"] < 1:
        raise RuntimeError("固定编组压力追踪没有可用编组")
    selected_groups = solution["selected"]
    grouped = data.group_cells(rows)
    baseline_lookup = {cell_id: records for cell_id, records in grouped.items()}
    cell_rows, group_summary = [], []
    for scenario in settings["pressure_scenarios"]:
        scenario_name = scenario["name"]
        stress = (scenario["temperature_C"], scenario["c_rate_C"], scenario["dod_pct"])
        signature = "|".join(
            ",".join(group["members"])
            for group in selected_groups
        )
        tracked_by_cell = {}
        for group_number, group in enumerate(selected_groups, start=1):
            for cell_id in group["members"]:
                tracked = track_fixed_cell(
                    cell_id=cell_id, records=baseline_lookup[cell_id], g1_cfg=g1_cfg,
                    stress=stress, retirement_cycle=study_cfg.q3.retirement_cycle,
                )
                tracked_by_cell[cell_id] = tracked
                first = tracked[0]
                final = tracked[-1]
                original = baseline_lookup[cell_id][study_cfg.q3.retirement_cycle - 1]
                crossing = next(
                    (row["cycle"] for row in tracked[1:] if row["soh"] <= study_cfg.q1.critical_soh),
                    None,
                )
                conditional_duration = (
                    crossing - study_cfg.q3.retirement_cycle
                    if crossing is not None else len(tracked) - 1
                )
                cell_rows.append({
                    "decision_mode": decision_mode,
                    "scenario": scenario_name,
                    "group_number": group_number,
                    "group_signature": signature,
                    "cell_id": cell_id,
                    "cycle_750_soh": first["soh"],
                    "cycle_1000_soh": final["soh"],
                    "soh_change": final["soh"] - first["soh"],
                    "cycle_750_resistance": first["resistance_true"],
                    "cycle_1000_resistance": final["resistance_true"],
                    "resistance_growth_increment": final["resistance_true"] / first["resistance_true"] - 1.0,
                    "post_750_event_observed": crossing is not None,
                    "post_750_observed_or_censor_duration": conditional_duration,
                    "post_750_censor_duration": None if crossing is not None else len(tracked) - 1,
                    "cycle_750_continuity_error": max(
                        first["formula_continuity_error"],
                        abs(first["soh"] - float(original["soh"])),
                        abs(first["resistance_true"] - float(original["resistance_true"])),
                    ),
                    "post_750_cycles": len(tracked) - 1,
                })
        for group_number, group in enumerate(selected_groups, start=1):
            final_cells = [tracked_by_cell[cell_id][-1] for cell_id in group["members"]]
            group_cell_rows = [
                row for row in cell_rows
                if row["scenario"] == scenario_name and row["group_number"] == group_number
            ]
            soh_values = [row["soh"] for row in final_cells]
            capacity_values = [row["capacity_true"] for row in final_cells]
            resistance_values = [row["resistance_true"] for row in final_cells]
            capacity_cv = float(np.std(capacity_values) / abs(np.mean(capacity_values)))
            rul_values = [row["post_750_observed_or_censor_duration"] for row in group_cell_rows]
            censored_count = sum(not row["post_750_event_observed"] for row in group_cell_rows)
            resistance_growth_values = [row["resistance_growth_increment"] for row in group_cell_rows]
            summary = {
                "decision_mode": decision_mode,
                "scenario": scenario_name,
                "group_number": group_number,
                "group_signature": signature,
                "capacity_cv": capacity_cv,
                "soh_range": float(max(soh_values) - min(soh_values)),
                "rul_cv": (
                    None if censored_count else
                    float(np.std(rul_values) / abs(np.mean(rul_values))) if np.mean(rul_values) else 0.0
                ),
                "rul_consistency_status": (
                    "RIGHT_CENSORED_NOT_IDENTIFIABLE" if censored_count else "OBSERVED_EVENTS"
                ),
                "right_censored_cell_count": censored_count,
                "resistance_range": float(max(resistance_growth_values) - min(resistance_growth_values)),
                "weakest_soh": float(min(soh_values)),
                "weakest_observed_or_censor_rul": float(min(rul_values)),
                "post_750_event_count": sum(row["post_750_event_observed"] for row in group_cell_rows),
                "rul_interpretation": "observed event duration or 250-cycle right-censor lower bound",
            }
            summary["trigger"] = _trigger_status(
                summary, settings["triggers"], study_cfg.q1.critical_soh
            )
            group_summary.append(summary)
    _add_rul_change_bounds(cell_rows)
    _add_group_change_summary(group_summary, cell_rows)
    return {"cell_rows": cell_rows, "group_summary": group_summary, "selected_groups": selected_groups}


def paired_fixed_group_tracking(rows, g1_cfg, study_cfg, settings, decisions) -> dict:
    """Track both decision modes under the same registered stress scenarios."""
    tracking = {}
    for mode in ("POINT", "INTERVAL_RISK"):
        tracking[mode] = track_fixed_groups(
            rows, g1_cfg, study_cfg, settings, decisions[mode], decision_mode=mode
        )
    scenario_names = [row["name"] for row in settings["pressure_scenarios"]]
    for mode, result in tracking.items():
        if not fixed_group_membership_is_constant(result, scenario_names):
            raise RuntimeError(f"{mode} 固定编组成员在压力场景间发生变化")
    summary_rows = []
    for mode, result in tracking.items():
        for scenario in scenario_names:
            rows_for_scenario = [
                row for row in result["group_summary"] if row["scenario"] == scenario
            ]
            counts = defaultdict(int)
            for row in rows_for_scenario:
                counts[row["trigger"]] += 1
            summary_rows.append({
                "decision_mode": mode,
                "scenario": scenario,
                "group_count": len(rows_for_scenario),
                "stable_count": counts["STABLE_UNDER_SCENARIO"],
                "reinspect_count": counts["REINSPECT"],
                "reject_count": counts["REJECT_FORCED_ASSIGNMENT"],
                "weakest_soh": min(row["weakest_soh"] for row in rows_for_scenario),
                "largest_resistance_range": max(row["resistance_range"] for row in rows_for_scenario),
                "group_signature": rows_for_scenario[0]["group_signature"],
            })
    return {
        "by_mode": tracking,
        "summary_rows": summary_rows,
        "scenario_names": scenario_names,
    }


def _git_head(project_root: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project_root, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNAVAILABLE"


def _relative(project_root: str, path: str) -> str:
    return os.path.relpath(os.path.abspath(path), project_root).replace(os.sep, "/")


def _manifest_command(project_root: str, config_path: str, out_dir: str) -> str:
    return (
        "PYTHONPATH=code python -m battery_study.v3_cli "
        f"--config {_relative(project_root, config_path)} "
        f"--out {_relative(project_root, out_dir)}"
    )


def _source_paths(
    project_root: str,
    source_config_path: str | None = None,
    source_g1_config_path: str | None = None,
) -> list[str]:
    paths = []
    for root in ("code/battery_study", "code/g1_generator", "code/tests"):
        absolute = os.path.join(project_root, root)
        for directory, _, filenames in os.walk(absolute):
            paths.extend(os.path.join(directory, name) for name in filenames if name.endswith(".py"))
    paths.append(os.path.join(project_root, "configs", "study_pipeline_v3.json"))
    paths.append(os.path.join(project_root, "requirements-study.txt"))
    paths.append(os.path.join(project_root, "technical", "v2_evidence_status.json"))
    paths.append(os.path.join(project_root, "evidence", "parameter_ledger.txt"))
    paths.append(os.path.join(project_root, "evidence", "source_ledger.txt"))
    paths.append(os.path.join(project_root, "technical", "plot_final_figures.py"))
    if source_config_path:
        paths.append(os.path.abspath(source_config_path))
    if source_g1_config_path:
        paths.append(os.path.abspath(source_g1_config_path))
    return sorted(paths)


def _v2_evidence_status(project_root: str) -> dict:
    path = os.path.join(project_root, "technical", "v2_evidence_status.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            status = json.load(handle)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"V2 canonical status 无法读取: {path}: {exc}") from exc
    expected = {
        "run_status": "PASS",
        "evidence_status": "HOLD_RPT_SENSITIVITY",
        "paper_eligible": False,
    }
    if {key: status.get(key) for key in expected} != expected:
        raise RuntimeError("V2 canonical status 必须保持 PASS/HOLD_RPT_SENSITIVITY/false")
    return status


def _v3_document_paths(project_root: str, report_path: str) -> list[str]:
    return [
        os.path.join(project_root, "README.md"),
        os.path.join(project_root, "PAPER_AGENT_START_HERE.md"),
        os.path.join(project_root, "论文初稿.md"),
        os.path.join(project_root, "handoffs", "A5_paper_technical_bridge.md"),
        os.path.join(project_root, "handoffs", "PROJECT_COMMAND_CENTER.md"),
        os.path.join(project_root, "technical", "PAPER_TECHNICAL_BRIDGE.md"),
        os.path.join(project_root, "technical", "PAPER_WRITING_FACT_SHEET.md"),
        os.path.join(project_root, "technical", "TECHNICAL_SOLUTION_FINAL.md"),
        os.path.join(project_root, "technical", "FINAL_VALIDATION_REPORT.md"),
        os.path.join(project_root, "technical", "FINAL_CHANGELOG_FOR_PAPER.md"),
        os.path.join(project_root, "technical", "TECHNICAL_SOLUTION_V3.md"),
        os.path.join(project_root, "technical", "V3_EXPERIMENT_PLAN.md"),
        report_path,
    ]


def _upstream_v1_evidence_paths(project_root: str) -> list[str]:
    evidence_root = os.path.join(project_root, "study_output")
    paths = []
    for directory, _, filenames in os.walk(evidence_root):
        paths.extend(
            os.path.join(directory, name)
            for name in filenames
            if name != "run_manifest.json"
        )
    return sorted(paths)


def _artifact_manifest(project_root: str, paths: list[str]) -> list[dict]:
    return [
        {
            "path": _relative(project_root, path),
            "bytes": os.path.getsize(path),
            "sha256": common.sha256_file(path),
        }
        for path in sorted({os.path.abspath(path) for path in paths if os.path.isfile(path)})
    ]


def validate_output_dir(project_root: str, out_dir: str) -> str:
    """Reject paths that could overwrite V1/G1 evidence or the repository root."""
    root = os.path.realpath(os.path.abspath(project_root))
    candidate = os.path.realpath(os.path.abspath(out_dir))
    protected_exact = {root}
    protected_trees = {
        os.path.join(root, "study_output"),
        os.path.join(root, "g1_output"),
    }
    if candidate in protected_exact:
        raise ValueError(f"V3 输出目录受保护: {out_dir}")
    for path in protected_trees:
        try:
            inside = os.path.commonpath((candidate, path)) == path
        except ValueError:
            inside = False
        if inside:
            raise ValueError(f"V3 输出目录受保护: {out_dir}")
    return candidate


def verify_manifest(manifest_path: str, *, project_root: str | None = None) -> dict:
    """Recompute every listed hash without trusting the manifest itself."""
    manifest_abs = os.path.realpath(os.path.abspath(manifest_path))
    root = os.path.realpath(os.path.abspath(project_root or os.path.dirname(os.path.dirname(manifest_abs))))
    errors = []
    checked = set()
    try:
        with open(manifest_abs, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        return {"status": "FAIL", "checked_files": 0, "errors": [str(exc)]}

    v2_path = os.path.join(root, "technical", "v2_evidence_status.json")
    try:
        with open(v2_path, "r", encoding="utf-8") as handle:
            canonical_v2 = json.load(handle)
        if {
            key: canonical_v2.get(key)
            for key in ("run_status", "evidence_status", "paper_eligible")
        } != {
            "run_status": "PASS",
            "evidence_status": "HOLD_RPT_SENSITIVITY",
            "paper_eligible": False,
        }:
            errors.append("V2 canonical status 未保持 PASS/HOLD_RPT_SENSITIVITY/false")
        expected_v2 = {
            "evidence_status": canonical_v2["evidence_status"],
            "paper_eligible": canonical_v2["paper_eligible"],
        }
    except (OSError, ValueError, KeyError) as exc:
        expected_v2 = None
        errors.append(f"V2 canonical status 无法读取: {exc}")
    if expected_v2 is not None and manifest.get("v2_status") != expected_v2:
        errors.append("V2 manifest 状态与 canonical status 不一致")
    for section in ("source_files", "artifacts"):
        entries = manifest.get(section)
        if not isinstance(entries, list):
            errors.append(f"manifest.{section} 不是数组")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"manifest.{section} 含非对象条目")
                continue
            relative = entry.get("path")
            if not isinstance(relative, str) or not relative or os.path.isabs(relative):
                errors.append(f"manifest.{section} 含绝对或空路径: {relative!r}")
                continue
            resolved = os.path.realpath(os.path.abspath(os.path.join(root, relative)))
            try:
                within_root = os.path.commonpath((resolved, root)) == root
            except ValueError:
                within_root = False
            if not within_root:
                errors.append(f"manifest 路径越出 project_root: {relative}")
                continue
            if resolved == manifest_abs:
                errors.append("manifest 不得列出自身")
                continue
            if resolved in checked:
                errors.append(f"manifest 重复列出路径: {relative}")
                continue
            checked.add(resolved)
            if not os.path.isfile(resolved):
                errors.append(f"manifest 文件不存在: {relative}")
                continue
            if entry.get("bytes") != os.path.getsize(resolved):
                errors.append(f"manifest 字节数不匹配: {relative}")
            if entry.get("sha256") != common.sha256_file(resolved):
                errors.append(f"manifest SHA-256 不匹配: {relative}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "checked_files": len(checked),
        "errors": errors,
    }


def _prediction_metrics(predictions: list[dict], study_cfg) -> dict:
    observed = [row for row in predictions if row["event_observed"]]
    metrics = common.regression_metrics(
        [row["conditional_duration"] for row in observed],
        [row["predicted_rul"] for row in observed],
    )
    covered = sum(
        row["rul_lower_90"] <= row["conditional_duration"] <= row["rul_upper_90"]
        for row in observed
    ) / len(observed) if observed else None
    return {
        **metrics,
        "n_risk_cells": len(predictions),
        "n_events": len(observed),
        "n_right_censored": len(predictions) - len(observed),
        "event_interval_90pct_coverage": covered,
        "landmark_cycle": 750,
        "conditional_target": "T - 750; right-censored at 250 cycles",
        "cell_bootstrap_repetitions": study_cfg.q2.bootstrap_repetitions,
    }


def fixed_group_membership_is_constant(tracking: dict, scenario_names: list[str]) -> bool:
    memberships = {}
    for scenario in scenario_names:
        memberships[scenario] = {
            (int(row["group_number"]), str(row["cell_id"]))
            for row in tracking["cell_rows"]
            if row["scenario"] == scenario
        }
    if any(not membership for membership in memberships.values()):
        return False
    return len({frozenset(membership) for membership in memberships.values()}) == 1


def _validate_v3(study_cfg, settings, dataset, risk_set, audit, decisions,
                 comparison, stability_rows, capacity_rows, capacity_summary,
                 ablation_rows, tracking, paired_tracking, observation) -> list[dict]:
    gates = []
    def gate(name, condition, evidence):
        if not condition:
            raise RuntimeError(f"V3 验证闸门失败: {name} ({evidence})")
        gates.append({"gate": name, "status": "PASS", "evidence": evidence})

    expected_cells = (
        len(study_cfg.factorial.temperatures_C)
        * len(study_cfg.factorial.c_rates_C)
        * len(study_cfg.factorial.dod_pct)
        * study_cfg.factorial.n_cells_per_condition
    )
    gate("v3_factorial_shape", dataset["meta"]["n_cells"] == expected_cells,
         f"{expected_cells} cells regenerated")
    gate("retirement_risk_accounting", len(risk_set) == 92 and
         sum(row["event_observed"] for row in risk_set) == 27 and
         sum(not row["event_observed"] for row in risk_set) == 65,
         "92 risk cells = 27 events + 65 right-censored; 16 pre-750 exclusions")
    gate("retirement_landmark_only", {row["cycle"] for row in risk_set} == {750} and
         {row["retirement_cycle"] for row in risk_set} == {750},
         "all features use cycle=750")
    gate("retirement_group_split", all(not row["train_test_overlap"] for row in audit) and
         len({row["cell_id"] for row in decisions["INTERVAL_RISK"]}) == len(risk_set),
         "OOF cell IDs unique; train/test overlap empty")
    gate(
        "decision_comparison_complete",
        set(comparison) == {"POINT", "INTERVAL_RISK"}
        and all(
            row["decision_rul_cycles"] == row["predicted_rul_cycles"]
            for row in decisions["POINT"]
        )
        and all(
            row["decision_rul_cycles"] == row["rul_lower_cycles"]
            for row in decisions["INTERVAL_RISK"]
        ),
        "common risk set; point uses median RUL, interval-risk uses RUL lower bound",
    )
    expected_stability = {
        (seed, parameter, value, weight_name)
        for seed in settings["stability"]["seeds"]
        for parameter, values, weight_name in (
            ("baseline", (None,), "balanced"),
            ("min_soh", tuple(value for value in settings["stability"]["min_soh"]
                              if value != study_cfg.q3.min_soh), "balanced"),
            ("min_rul_lower_cycles", tuple(value for value in settings["stability"]["min_rul_lower_cycles"]
                                            if value != study_cfg.q3.min_rul_lower_cycles), "balanced"),
            ("max_resistance_growth", tuple(value for value in settings["stability"]["max_resistance_growth"]
                                             if value != study_cfg.q3.max_resistance_growth), "balanced"),
            ("weights", (None,), "performance"),
            ("weights", (None,), "conservative"),
        )
        for value in values
    }
    actual_stability = {
        (row["seed"], row["parameter"], row["parameter_value"], row["weights_name"])
        for row in stability_rows
    }
    gate("stability_oat_complete", actual_stability == expected_stability and
         len(stability_rows) == 45 and
         all(0.0 <= row["selected_cell_jaccard"] <= 1.0 for row in stability_rows) and
         all(row["changed_parameter_count"] <= 1 for row in stability_rows),
         "exact 5-seed x 9-point OAT set, bounded Jaccard, one changed parameter")
    gate(
        "capacity_seed_distribution_complete",
        len(capacity_rows) == len(settings["capacity_seed_study"]["seeds"])
        and capacity_summary["n_seeds"] == len(capacity_rows)
        and set(capacity_summary["at_least_group_rates"]) == {
            str(group) for group in range(4, study_cfg.q3.target_groups + 1)
        }
        and all(not row["thresholds_relaxed"] for row in capacity_rows),
        f"{len(capacity_rows)} baseline INTERVAL_RISK seeds; empirical G_max rates reported",
    )
    expected_ablation = {
        (window, feature_group, model)
        for window in settings["ablation"]["history_windows"]
        for feature_group in settings["ablation"]["feature_groups"]
        for model in ("local_linear", "persistence", "random_forest", "ridge")
    }
    actual_ablation = {
        (row["history_window"], row["feature_group"], row["model"])
        for row in ablation_rows
    }
    gate("ablation_complete", actual_ablation == expected_ablation and len(ablation_rows) == 48,
         "3 windows x 4 feature groups x 4 models")
    scenario_names = [row["name"] for row in settings["pressure_scenarios"]]
    gate("fixed_group_signature", fixed_group_membership_is_constant(tracking, scenario_names),
         "same (group_number, cell_id) membership across pressure scenarios")
    gate("cycle_750_continuity", all(row["cycle_750_continuity_error"] <= 1e-6
                                      for row in tracking["cell_rows"]),
         "pressure trajectories match baseline at cycle 750")
    expected_tracking = len(settings["pressure_scenarios"]) * study_cfg.q3.target_groups
    gate("fixed_group_shape", len(tracking["group_summary"]) == expected_tracking and
         len(tracking["cell_rows"]) == expected_tracking * study_cfg.q3.group_size,
         f"{len(settings['pressure_scenarios'])} scenarios x {study_cfg.q3.target_groups} groups x "
         f"{study_cfg.q3.group_size} cells")
    paired_rows = paired_tracking["summary_rows"]
    gate(
        "paired_fixed_group_modes",
        set(paired_tracking["by_mode"]) == {"POINT", "INTERVAL_RISK"}
        and len(paired_rows) == len(settings["pressure_scenarios"]) * 2
        and all(row["group_count"] == study_cfg.q3.target_groups for row in paired_rows)
        and all(
            fixed_group_membership_is_constant(result, scenario_names)
            for result in paired_tracking["by_mode"].values()
        ),
        "POINT and INTERVAL_RISK each track fixed groups through identical scenarios",
    )
    gate(
        "fixed_group_summary_complete",
        all(
            {
                "mean_soh_change",
                "mean_resistance_growth_increment",
                "group_rul_change_status",
            } <= set(row)
            for row in tracking["group_summary"]
        ),
        "group summaries contain SOH, resistance, and censor-aware RUL change fields",
    )
    gate(
        "stress_trigger_endpoint_guard",
        all(
            row["trigger"] == "REJECT_FORCED_ASSIGNMENT"
            for row in tracking["group_summary"]
            if row["weakest_soh"] <= study_cfg.q1.critical_soh
            or row["post_750_event_count"] > 0
        ),
        "endpoint breach or post-750 event always rejects forced assignment",
    )
    expected_regimes = {"none", "light", "heavy"}
    actual_regimes = {row["regime"] for row in observation["decision_rows"]}
    gate(
        "observation_pressure_complete",
        actual_regimes == expected_regimes
        and {row["regime"] for row in observation["model_metrics"]} == expected_regimes
        and len(observation["model_metrics"]) == 12,
        "none/light/heavy all report four Q2 models and Q3 decision outcomes",
    )
    gate(
        "observation_latent_state_preserved",
        all(row["latent_state_unchanged"] for row in observation["audits"])
        and all(row["q2_split_overlap"] == 0 for row in observation["audits"])
        and all(row["retirement_split_overlap"] == 0 for row in observation["audits"]),
        "only observed channels changed; grouped split overlap remains zero",
    )
    gate(
        "decision_abstention_enforced",
        all(not row["thresholds_relaxed"] for row in observation["decision_rows"])
        and all(
            row["decision_status"] == (
                "ACCEPT_FIXED_GROUPS" if row["group_shortfall"] == 0
                else "ABSTAIN_INSUFFICIENT_FEASIBILITY"
            )
            for row in observation["decision_rows"]
        ),
        "shortfall returns explicit abstention; screening thresholds never relax",
    )
    return gates


def _write_validation_report(project_root, out_dir, summary, gates):
    path = os.path.join(project_root, "technical", "V3_VALIDATION_REPORT.md")
    stability = summarize_stability(summary["stability_rows"])
    ablation = summarize_ablation(summary["ablation_rows"])
    ridge_full = next(
        row for row in ablation["all_vs_capacity_only"]
        if row["model"] == "ridge" and row["history_window"] == 100
    )
    point = summary["decisions"]["POINT"]
    interval = summary["decisions"]["INTERVAL_RISK"]
    best = ablation["best_configuration"]
    capacity = summary["capacity_seed_summary"]
    paired_rows = summary["paired_tracking"]["summary_rows"]
    paired_counts = {
        mode: {
            name: sum(row[name] for row in paired_rows if row["decision_mode"] == mode)
            for name in ("stable_count", "reinspect_count", "reject_count")
        }
        for mode in ("POINT", "INTERVAL_RISK")
    }
    lines = [
        "# V3 验证报告",
        "",
        "> 状态：`V3_RESULT_READY_WITH_SIMULATION_LIMITS`。本文档只描述本次 V3 合成仿真和固定编组压力追踪；不构成真实外部验证。",
        "",
        "## 结果摘要",
        "",
        f"- `[RESULT]` 退役风险集：{summary['risk_set']['n_risk_cells']} 芯；事件 {summary['risk_set']['n_events']}；右删失 {summary['risk_set']['n_right_censored']}。",
        f"- `[RESULT]` 条件 RUL 事件 RMSE：{summary['risk_metrics']['rmse']:.4f} cycles；嵌套留组校准区间经验覆盖：{summary['risk_metrics']['event_interval_90pct_coverage']:.4f}。",
        f"- `[RESULT]` POINT 入选 {summary['decisions']['POINT']['eligible_cells']} 芯；INTERVAL_RISK 入选 {summary['decisions']['INTERVAL_RISK']['eligible_cells']} 芯。",
        (
            f"- `[RESULT]` POINT 最大可行 {point['max_feasible_groups']} 组、"
            f"INTERVAL_RISK 最大可行 {interval['max_feasible_groups']} 组；"
            f"目标均为 {point['requested_groups']} 组，状态分别为 "
            f"`{point['decision_status']}` / `{interval['decision_status']}`；"
            "筛选门槛均未放宽。"
        ),
        (
            f"- `[RESULT]` POINT 选中电芯的最小 RUL 下界为 "
            f"{point['weakest_selected_rul_lower_cycles']:.4f} cycles、最大实际区间宽度为 "
            f"{point['largest_selected_interval_width']:.4f}；INTERVAL_RISK 对应为 "
            f"{interval['weakest_selected_rul_lower_cycles']:.4f} 和 "
            f"{interval['largest_selected_interval_width']:.4f}。两模式候选组归一化范围不同，"
            "目标值不得直接横向比较。"
        ),
        (
            f"- `[RESULT]` 稳定性扫描行数：{len(summary['stability_rows'])}；"
            f"Jaccard={stability['jaccard_min']:.4f}--{stability['jaccard_max']:.4f}；"
            f"入选率={stability['eligible_rate_min']:.4f}--"
            f"{stability['eligible_rate_max']:.4f}；"
            f"相对同 seed 基准目标差范围={stability['objective_delta_min']:.4f}--"
            f"{stability['objective_delta_max']:.4f}；"
            f"最小 SOH 裕度={stability['worst_selected_soh_margin_min']:.4f}、"
            f"最小 RUL 下界裕度={stability['worst_selected_rul_lower_margin_cycles_min']:.4f} cycles、"
            f"最小内阻增长裕度={stability['worst_selected_resistance_growth_margin_min']:.4f}、"
            f"最小区间宽度裕度={stability['worst_selected_interval_width_margin_cycles_min']:.4f} cycles；"
            f"显式弃权 OAT 点 {stability['abstention_count']}/"
            f"{len(summary['stability_rows'])}，最大组数缺口={stability['group_shortfall_max']}，"
            f"门槛放宽次数={stability['threshold_relaxation_count']}；"
            f"消融配置：{len(summary['ablation_rows'])}。"
        ),
        (
            f"- `[RESULT][UPDATEABLE]` 30 个独立 seed 的基线区间风险产能："
            f"G_max={capacity['max_feasible_groups_min']}--{capacity['max_feasible_groups_max']}，"
            f"中位数={capacity['max_feasible_groups_median']:.1f}；"
            f"达到至少 8 组={capacity['at_least_group_rates']['8']:.1%} "
            f"({capacity['accept_count']}/{capacity['n_seeds']})。这是合成跨种子经验分布，"
            "不是实际批次概率，也不把单次 8 组结果扩展为普遍保证。"
        ),
        (
            f"- `[RESULT]` Q2 消融最低 RMSE 配置为 {best['model']} + "
            f"{best['feature_group']} + {best['history_window']}-cycle，RMSE="
            f"{best['rmse']:.6f}；同为 100-cycle Ridge 时，全部特征较容量-only "
            f"RMSE 下降 {ridge_full['relative_rmse_reduction']:.2%}。这是仿真内消融，"
            "不构成真实因果贡献。"
        ),
        (
            f"- `[RESULT]` Q4 固定组级记录 {len(summary['tracking_rows'])} 行；"
            f"{sum(row['trigger'] == 'STABLE_UNDER_SCENARIO' for row in summary['tracking_rows'])} 行 "
            "`STABLE_UNDER_SCENARIO`，"
            f"{sum(row['trigger'] == 'REINSPECT' for row in summary['tracking_rows'])} 行 `REINSPECT`，"
            f"{sum(row['trigger'] == 'REJECT_FORCED_ASSIGNMENT' for row in summary['tracking_rows'])} 行 "
            "`REJECT_FORCED_ASSIGNMENT`；终点突破/事件触发强制拒绝。"
        ),
        (
            "- `[RESULT][UPDATEABLE]` 同一五场景的模式配对固定追踪："
            f"POINT={paired_counts['POINT']['stable_count']} 稳定/"
            f"{paired_counts['POINT']['reinspect_count']} 复检/"
            f"{paired_counts['POINT']['reject_count']} 拒绝；"
            f"INTERVAL_RISK={paired_counts['INTERVAL_RISK']['stable_count']} 稳定/"
            f"{paired_counts['INTERVAL_RISK']['reinspect_count']} 复检/"
            f"{paired_counts['INTERVAL_RISK']['reject_count']} 拒绝。"
            "区间风险减少复检但增加拒绝，只支持更保守的弃权描述。"
        ),
        (
            "- `[RESULT][ASSUMED]` 观测压力 none/light/heavy 的 Ridge RMSE 为 "
            + "/".join(
                f"{row['rmse']:.6f}" for row in summary["observation"]["model_metrics"]
                if row["model"] == "ridge"
            )
            + "；模型排序翻转档位="
            + (", ".join(summary["observation"]["ranking_flip_regimes"]) or "none")
            + "；选中成员 Jaccard="
            + "/".join(
                f"{row['selected_cell_jaccard_vs_none']:.3f}"
                for row in summary["observation"]["decision_rows"]
            )
            + "。观测档是仿真压力，不是真实 RPT 标定。"
        ),
        "",
        "## 验收闸门",
        "",
    ]
    lines.extend(f"- [x] {row['gate']}: {row['evidence']}" for row in gates)
    lines.extend([
        "",
        "## 边界",
        "",
        "- `[CONFIRMED]` Q3 特征只读取 cycle<=750；750 前已达终点电芯排除。",
        "- `[CONFIRMED]` Q4 固定 Q3 编组，不重新筛选、不重新优化；cycle 750 状态连续。",
        "- `[ASSUMED][UPDATEABLE]` SOH 终点、筛选阈值、权重和触发规则来自配置。",
        "- `[UNCERTAIN]` 真实电芯、车辆和安全事件外部有效性。",
        "- `[OOD/ABSTAIN]` 低温、过充、过放、大于 2C 不输出数值。",
        "- `V2 evidence_status=HOLD_RPT_SENSITIVITY; paper_eligible=false`，V2 不进入 V3 论文数字。",
        "",
        "## 复跑命令",
        "",
        "```bash",
        "PYTHONPATH=code python -m battery_study.v3_cli --config configs/study_pipeline_v3.json --out study_output_v3",
        "```",
    ])
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


def run(study_cfg, settings, out_dir: str) -> dict:
    """Run all V3 experiments and write only independent V3 artifacts."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_dir = validate_output_dir(project_root, out_dir)
    os.makedirs(out_dir, exist_ok=True)
    g1_cfg, dataset = data.generate_factorial_dataset(study_cfg)
    risk_set = retirement_risk_set(
        dataset["rows"], study_cfg, study_cfg.q3.retirement_cycle, study_cfg.q1.critical_soh
    )
    predictions, audit = cross_validated_retirement_predictions(risk_set, study_cfg)
    decisions = build_decision_pools(risk_set, predictions, study_cfg)
    comparison = {}
    for mode in ("POINT", "INTERVAL_RISK"):
        solution = optimize_decision(decisions[mode], study_cfg, tuple(study_cfg.q3.weights["balanced"]))
        comparison[mode] = {
            "eligible_cells": solution["eligible_cells"],
            "n_groups": solution["n_groups"],
            "target_groups": solution.get("target_groups", 0),
            "objective": solution["objective"],
            "selected_cell_ids": solution.get("selected_cell_ids", []),
            "solver_status": solution["solver_status"],
            "decision_status": solution["decision_status"],
            "requested_groups": solution["requested_groups"],
            "max_feasible_groups": solution["max_feasible_groups"],
            "group_shortfall": solution["group_shortfall"],
            "abstention_reasons": solution["abstention_reasons"],
            "thresholds_relaxed": solution["thresholds_relaxed"],
            "weakest_selected_soh": solution["weakest_selected_soh"],
            "weakest_selected_rul_lower_cycles": solution[
                "weakest_selected_rul_lower_cycles"
            ],
            "largest_selected_resistance_growth": solution[
                "largest_selected_resistance_growth"
            ],
            "largest_selected_interval_width": solution[
                "largest_selected_interval_width"
            ],
            "decision_rul_basis": (
                "predicted_rul_median" if mode == "POINT" else "rul_lower_90"
            ),
            "objective_comparability": "WITHIN_MODE_ONLY_MODE_SPECIFIC_NORMALIZATION",
            "mode": mode,
        }
    capacity_rows, capacity_summary = capacity_seed_study(study_cfg, settings)
    stability_rows = stability_sweep(study_cfg, settings)
    ablation_rows = run_ablation(study_cfg, settings, dataset["rows"])
    observation = run_observation_sensitivity(study_cfg, settings, dataset["rows"])
    paired_tracking = paired_fixed_group_tracking(
        dataset["rows"], g1_cfg, study_cfg, settings, decisions
    )
    tracking = paired_tracking["by_mode"]["INTERVAL_RISK"]
    gates = _validate_v3(
        study_cfg, settings, dataset, risk_set, audit, decisions,
        comparison, stability_rows, capacity_rows, capacity_summary,
        ablation_rows, tracking, paired_tracking, observation,
    )

    common.write_csv(os.path.join(out_dir, "q3_retirement_landmark_predictions.csv"), predictions)
    screening = []
    for mode, rows in decisions.items():
        screening.extend({"decision_mode": mode, **row} for row in rows)
    common.write_csv(os.path.join(out_dir, "q3_retirement_screening.csv"), screening)
    common.write_json(os.path.join(out_dir, "q3_retirement_summary.json"), {
        "scope": "SYNTHETIC_CONDITIONAL_RUL_AT_RETIREMENT_LANDMARK",
        "risk_set": {
            "n_risk_cells": len(risk_set),
            "n_events": sum(row["event_observed"] for row in risk_set),
            "n_right_censored": sum(not row["event_observed"] for row in risk_set),
            "n_pre_750_excluded": dataset["meta"]["n_cells"] - len(risk_set),
            "retirement_cycle": study_cfg.q3.retirement_cycle,
        },
        "prediction_metrics": _prediction_metrics(predictions, study_cfg),
        "split_audit": audit,
        "evidence_labels": {
            "risk_set": "[RESULT][UPDATEABLE]",
            "external_validity": "[UNCERTAIN]",
        },
    })
    common.write_csv(os.path.join(out_dir, "q3_decision_comparison.csv"), [
        {key: value for key, value in row.items() if key != "selected_cell_ids"}
        | {"selected_cell_ids": ";".join(row["selected_cell_ids"])}
        for row in comparison.values()
    ])
    common.write_csv(os.path.join(out_dir, "q3_stability_sweep.csv"), [
        {key: value for key, value in row.items() if key != "selected_cell_ids"}
        | {"selected_cell_ids": ";".join(row["selected_cell_ids"])}
        for row in stability_rows
    ])
    common.write_json(os.path.join(out_dir, "q3_stability_summary.json"), {
        "scope": "OAT_DECISION_STABILITY",
        "n_rows": len(stability_rows),
        "seeds": settings["stability"]["seeds"],
        "jaccard_reference": "same-seed INTERVAL_RISK balanced solution",
        **summarize_stability(stability_rows),
        "rows": stability_rows,
    })
    common.write_csv(os.path.join(out_dir, "q3_capacity_seed_runs.csv"), [
        {key: value for key, value in row.items() if key != "selected_cell_ids"}
        | {"selected_cell_ids": ";".join(row["selected_cell_ids"])}
        for row in capacity_rows
    ])
    common.write_json(os.path.join(out_dir, "q3_capacity_seed_summary.json"), {
        **capacity_summary,
        "rows": capacity_rows,
    })
    common.write_csv(os.path.join(out_dir, "q2_ablation_metrics.csv"), ablation_rows)
    common.write_json(os.path.join(out_dir, "q2_ablation_summary.json"), {
        "scope": "SYNTHETIC_GROUPED_SOH_ABLATION",
        "windows": settings["ablation"]["history_windows"],
        "feature_groups": sorted(settings["ablation"]["feature_groups"]),
        "models": sorted({row["model"] for row in ablation_rows}),
        "rows": len(ablation_rows),
        "leakage_exclusions": ["soh_true", "lifetime_cycle", "event_observed", "capacity_true"],
        **summarize_ablation(ablation_rows),
    })
    common.write_csv(
        os.path.join(out_dir, "observation_model_metrics.csv"),
        observation["model_metrics"],
    )
    common.write_csv(
        os.path.join(out_dir, "observation_decision_sensitivity.csv"),
        observation["decision_rows"],
    )
    common.write_json(os.path.join(out_dir, "observation_sensitivity_summary.json"), {
        "scope": "ASSUMED_OBSERVATION_PROCESS_STRESS_NOT_REAL_CALIBRATION",
        "latent_model": "X(c)=registered semi-mechanistic latent degradation",
        "observation_model": "Y(c)=X(c)+Gaussian measurement noise+RPT/recovery pulse+sparse outlier",
        "parameter_status": "[ASSUMED][UPDATEABLE]",
        "ranking_flip_regimes": observation["ranking_flip_regimes"],
        "audits": observation["audits"],
        "decision_rows": observation["decision_rows"],
    })
    common.write_csv(os.path.join(out_dir, "q4_fixed_group_cell_tracking.csv"), tracking["cell_rows"])
    common.write_csv(os.path.join(out_dir, "q4_fixed_group_summary.csv"), tracking["group_summary"])
    common.write_json(os.path.join(out_dir, "q4_fixed_group_summary.json"), {
        "scope": "FIXED_Q3_GROUP_LONGITUDINAL_STRESS_TRACKING",
        "selected_group_signature": "|".join(
            ",".join(group["members"]) for group in tracking["selected_groups"]
        ),
        "scenario_count": len(settings["pressure_scenarios"]),
        "rows": tracking["group_summary"],
        "interpretation": "simulation-conditioned fixed-group pressure tracking; not real safety validation",
    })
    common.write_csv(
        os.path.join(out_dir, "q4_paired_decision_mode_summary.csv"),
        paired_tracking["summary_rows"],
    )
    common.write_csv(
        os.path.join(out_dir, "q4_paired_decision_mode_cell_tracking.csv"),
        [row for result in paired_tracking["by_mode"].values() for row in result["cell_rows"]],
    )
    common.write_json(os.path.join(out_dir, "q4_paired_decision_mode_summary.json"), {
        "scope": "PAIRED_FIXED_GROUP_TRACKING_POINT_VS_INTERVAL_RISK",
        "scenario_names": paired_tracking["scenario_names"],
        "rows": paired_tracking["summary_rows"],
        "interpretation": "same synthetic data and same stress scenarios; each mode fixes its own Q3 groups without re-selection",
    })
    gates_path = common.write_json(os.path.join(out_dir, "validation_gates.json"), gates)
    summary = {
        "risk_set": {
            "n_risk_cells": len(risk_set),
            "n_events": sum(row["event_observed"] for row in risk_set),
            "n_right_censored": sum(not row["event_observed"] for row in risk_set),
        },
        "risk_metrics": _prediction_metrics(predictions, study_cfg),
        "decisions": comparison,
        "stability_rows": stability_rows,
        "capacity_seed_rows": capacity_rows,
        "capacity_seed_summary": capacity_summary,
        "ablation_rows": ablation_rows,
        "tracking_rows": tracking["group_summary"],
        "paired_tracking": paired_tracking,
        "observation": observation,
    }
    report_path = _write_validation_report(project_root, out_dir, summary, gates)
    artifact_paths = []
    for root, _, filenames in os.walk(out_dir):
        artifact_paths.extend(
            os.path.join(root, name) for name in filenames if name != "run_manifest.json"
        )
    artifact_paths.extend(_v3_document_paths(project_root, report_path))
    artifact_paths.extend(_upstream_v1_evidence_paths(project_root))
    source_config_path = getattr(
        study_cfg, "_loaded_path", os.path.join(project_root, "configs", "study_pipeline_v3.json")
    )
    manifest = {
        "manifest_version": 1,
        "study_id": study_cfg.study_id,
        "scope": "synthetic NMC V3; no external calibration or validation",
        "git_head_before_commit": _git_head(project_root),
        "command": _manifest_command(project_root, source_config_path, out_dir),
        "v2_status": {
            "evidence_status": _v2_evidence_status(project_root)["evidence_status"],
            "paper_eligible": _v2_evidence_status(project_root)["paper_eligible"],
        },
        "dataset": {"cells": dataset["meta"]["n_cells"], "rows_regenerated": dataset["meta"]["n_rows"]},
        "validation": gates,
        "source_files": _artifact_manifest(
            project_root,
            _source_paths(project_root, source_config_path, study_cfg.source_g1_path),
        ),
        "artifacts": _artifact_manifest(project_root, artifact_paths),
        "labels": {
            "confirmed": "landmark, split, fixed group signature, continuity gates",
            "result_updateable": "predictions, thresholds, weights, stress outcomes",
            "uncertain": "real-world external validity",
            "ood_abstain": "outside 25-50 degC, 0.5-2C, 50-100% DOD, CC-CV",
        },
    }
    manifest_path = common.write_json(os.path.join(out_dir, "run_manifest.json"), manifest)
    manifest_verification = verify_manifest(manifest_path, project_root=project_root)
    if manifest_verification["status"] != "PASS":
        raise RuntimeError(f"V3 manifest 验证失败: {manifest_verification['errors']}")
    return {
        "manifest": manifest_path,
        "manifest_verification": manifest_verification,
        "gates": gates,
        "report": report_path,
        "summary": summary,
    }
