"""问题4：支持域内多工况、批次代理、OAT 灵敏度和多 seed 鲁棒性。"""
from __future__ import annotations

import copy
import os
from collections import defaultdict

import numpy as np

from g1_generator import config as g1cfg
from g1_generator import degradation as g1deg
from g1_generator import simulate

from . import common, data, q2, q3


OPERATING_SCENARIOS = (
    ("baseline", 25.0, 1.0, 80.0),
    ("high_temperature", 45.0, 1.0, 80.0),
    ("high_c_rate", 25.0, 2.0, 80.0),
    ("high_dod", 25.0, 1.0, 100.0),
    ("combined_stress", 45.0, 2.0, 100.0),
)

BATCH_PROXIES = {
    "batch_low_degradation_proxy": {"alpha": 0.9, "beta": 0.9, "R0_nom_Ohm": 0.95, "sigma_cell": 1.0},
    "batch_reference_proxy": {"alpha": 1.0, "beta": 1.0, "R0_nom_Ohm": 1.0, "sigma_cell": 1.0},
    "batch_high_degradation_proxy": {"alpha": 1.1, "beta": 1.1, "R0_nom_Ohm": 1.05, "sigma_cell": 2.0},
}

SENSITIVITY_PARAMETERS = ("alpha", "beta", "k_T", "k_C", "k_D", "n_k_EFC", "sigma_cell")


def _scenario_config(base_g1_cfg, study_cfg, seed: int):
    cfg = copy.deepcopy(base_g1_cfg)
    cfg.seed = int(seed)
    cfg.scenarios = [
        g1cfg.Scenario(
            id=name,
            temperature_C=temperature,
            c_rate=c_rate,
            dod_pct=dod,
            n_cells=study_cfg.q4.n_cells_per_scenario,
            protocol="CC-CV",
        )
        for name, temperature, c_rate, dod in OPERATING_SCENARIOS
    ]
    g1cfg.validate_config(cfg)
    return cfg


def _single_scenario_rows(cfg, scenario_index: int = 0):
    scenario = cfg.scenarios[scenario_index]
    rows = []
    for cell_index in range(scenario.n_cells):
        rows.extend(g1deg.generate_cell(cfg, scenario, scenario_index, cell_index))
    return rows


def _batch_rows(base_cfg, study_cfg, seed: int, label: str, multipliers: dict):
    cfg = _scenario_config(base_cfg, study_cfg, seed)
    cfg.alpha = base_cfg.alpha * multipliers["alpha"]
    cfg.beta = base_cfg.beta * multipliers["beta"]
    cfg.R0_nom_Ohm = base_cfg.R0_nom_Ohm * multipliers["R0_nom_Ohm"]
    cfg.sigma_cell = base_cfg.sigma_cell * multipliers["sigma_cell"]
    g1cfg.validate_config(cfg)
    rows = _single_scenario_rows(cfg, 0)
    for row in rows:
        cell_index = str(row["cell_id"]).rsplit("_", 1)[-1]
        row["cell_id"] = f"{label}_{cell_index}"
    return rows


def _scenario_metrics(label: str, rows: list[dict], study_cfg, trained_q2: dict) -> dict:
    grouped = data.group_cells(rows)
    samples = q2.make_soh_samples(grouped, study_cfg)
    ridge = trained_q2["full_soh_models"]["ridge"]
    soh_prediction = ridge.predict(q2._matrix(samples))
    soh_metrics = common.regression_metrics(
        [row["target_soh"] for row in samples], soh_prediction
    )
    summaries = data.make_cell_summaries(
        rows, study_cfg.q1.critical_soh,
        study_cfg.q2.landmark_cycle, study_cfg.q2.history_window_cycles,
    )
    predictions = q3.aft_prediction_map(summaries, trained_q2["full_aft"])
    candidates = q3.build_candidate_pool(grouped, predictions, study_cfg)
    eligible = sum(row["eligible"] for row in candidates)
    target_groups = min(4, eligible // study_cfg.q3.group_size)
    group_inconsistency = None
    grouping_rate = 0.0
    normalized_objective = None
    solver_status = "NO_FEASIBLE_GROUP_TARGET"
    if target_groups:
        groups = q3.enumerate_candidate_groups(
            candidates, study_cfg.q3.group_size, study_cfg.q3.neighbor_pool
        )
        solution = q3.solve_milp(groups, study_cfg.q3.weights["balanced"], target_groups)
        selected = solution["selected"]
        group_inconsistency = float(np.mean([
            group["raw_inconsistency"] for group in selected
        ]))
        grouping_rate = target_groups * study_cfg.q3.group_size / eligible
        normalized_objective = solution["objective"] / target_groups
        solver_status = solution["solver_status"]
    final_rows = [records[-1] for records in grouped.values()]
    first_rows = [records[0] for records in grouped.values()]
    resistance_growth = [
        float(final["resistance_true"]) / float(first["resistance_true"]) - 1.0
        for first, final in zip(first_rows, final_rows)
    ]
    return {
        "scenario": label,
        "n_cells": len(grouped),
        "final_soh_mean": float(np.mean([float(row["soh"]) for row in final_rows])),
        "final_soh_sd": float(np.std([float(row["soh"]) for row in final_rows])),
        "final_resistance_growth_mean": float(np.mean(resistance_growth)),
        "critical_fraction": float(np.mean([
            float(row["soh"]) <= study_cfg.q1.critical_soh for row in final_rows
        ])),
        "ridge_soh_forecast_rmse": soh_metrics["rmse"],
        "screening_rate": eligible / len(candidates),
        "eligible_cells": eligible,
        "grouping_rate_among_eligible": grouping_rate,
        "mean_group_inconsistency_raw": group_inconsistency,
        "balanced_objective_per_group": normalized_objective,
        "group_solver_status": solver_status,
    }


def _aggregate_seed_metrics(rows: list[dict], seeds: tuple[int, ...]) -> list[dict]:
    by_scenario = defaultdict(list)
    for row in rows:
        by_scenario[row["scenario"]].append(row)
    metrics = (
        "final_soh_mean",
        "final_soh_sd",
        "final_resistance_growth_mean",
        "critical_fraction",
        "ridge_soh_forecast_rmse",
        "screening_rate",
        "grouping_rate_among_eligible",
        "mean_group_inconsistency_raw",
        "balanced_objective_per_group",
    )
    output = []
    for scenario, records in sorted(by_scenario.items()):
        summary = {"scenario": scenario, "n_seeds": len(records), "registered_seed_count": len(seeds)}
        for metric in metrics:
            values = [float(row[metric]) for row in records if row[metric] is not None]
            summary[f"{metric}_mean"] = float(np.mean(values)) if values else None
            summary[f"{metric}_p10"] = float(np.quantile(values, 0.1)) if values else None
            summary[f"{metric}_p90"] = float(np.quantile(values, 0.9)) if values else None
        output.append(summary)
    return output


def _end_metrics(rows: list[dict], threshold: float) -> dict[str, dict]:
    grouped = data.group_cells(rows)
    by_condition = defaultdict(list)
    for cell_id, records in grouped.items():
        first, final = records[0], records[-1]
        by_condition[data.condition_id(cell_id)].append({
            "final_soh": float(final["soh"]),
            "resistance_growth": float(final["resistance_true"]) / float(first["resistance_true"]) - 1.0,
            "critical": float(final["soh"]) <= threshold,
        })
    return {
        condition: {
            "final_soh_mean": float(np.mean([row["final_soh"] for row in values])),
            "resistance_growth_mean": float(np.mean([row["resistance_growth"] for row in values])),
            "critical_fraction": float(np.mean([row["critical"] for row in values])),
        }
        for condition, values in by_condition.items()
    }


def _sensitivity(base_g1_cfg, study_cfg) -> tuple[list[dict], list[dict]]:
    fraction = study_cfg.q4.sensitivity_fraction
    base_cfg = _scenario_config(base_g1_cfg, study_cfg, study_cfg.study_seed + 404)
    base_metrics = _end_metrics(simulate.generate_dataset(base_cfg)["rows"], study_cfg.q1.critical_soh)
    raw_rows = []
    rank_rows = []
    for parameter in SENSITIVITY_PARAMETERS:
        base_value = float(getattr(base_cfg, parameter))
        level_metrics = {"base": base_metrics}
        values = {"base": base_value}
        for level, multiplier in (("low", 1.0 - fraction), ("high", 1.0 + fraction)):
            cfg = copy.deepcopy(base_cfg)
            setattr(cfg, parameter, base_value * multiplier)
            g1cfg.validate_config(cfg)
            values[level] = float(getattr(cfg, parameter))
            level_metrics[level] = _end_metrics(
                simulate.generate_dataset(cfg)["rows"], study_cfg.q1.critical_soh
            )
        for level in ("low", "base", "high"):
            for scenario, metrics in sorted(level_metrics[level].items()):
                raw_rows.append({
                    "parameter": parameter,
                    "level": level,
                    "parameter_value": values[level],
                    "scenario": scenario,
                    **metrics,
                })
        parameter_span = (values["high"] - values["low"]) / base_value
        for scenario in sorted(base_metrics):
            rank = {"parameter": parameter, "scenario": scenario}
            for metric in ("final_soh_mean", "resistance_growth_mean"):
                base_outcome = base_metrics[scenario][metric]
                change = level_metrics["high"][scenario][metric] - level_metrics["low"][scenario][metric]
                rank[f"normalized_{metric}_change"] = (
                    change / abs(base_outcome) / parameter_span if abs(base_outcome) > 1e-12 else None
                )
            rank_rows.append(rank)
    return raw_rows, rank_rows


def _ood_cases() -> list[dict]:
    cases = (
        ("low_temperature", 0.0, 1.0, 80.0, "CC-CV"),
        ("overcharge_protocol", 25.0, 1.0, 80.0, "CC-CV-overcharge"),
        ("overdischarge", 25.0, 1.0, 110.0, "CC-CV"),
        ("rate_above_support", 25.0, 3.0, 80.0, "CC-CV"),
    )
    output = []
    for name, temperature, c_rate, dod, protocol in cases:
        status = data.supported_domain_status(temperature, c_rate, dod, protocol)
        output.append({
            "case": name,
            "temperature_C": temperature,
            "c_rate_C": c_rate,
            "dod_pct": dod,
            "protocol": protocol,
            "status": status["status"],
            "reason": "; ".join(status["reasons"]),
            "numeric_prediction": None,
        })
    return output


def analyze(study_cfg, base_g1_cfg, trained_q2: dict, out_dir: str) -> dict:
    raw_monte_carlo = []
    for seed in study_cfg.q4.seeds:
        cfg = _scenario_config(base_g1_cfg, study_cfg, seed)
        dataset = simulate.generate_dataset(cfg)
        grouped_by_scenario = defaultdict(list)
        for row in dataset["rows"]:
            grouped_by_scenario[data.condition_id(row["cell_id"])].append(row)
        for scenario, _, _, _ in OPERATING_SCENARIOS:
            metrics = _scenario_metrics(scenario, grouped_by_scenario[scenario], study_cfg, trained_q2)
            raw_monte_carlo.append({"seed": seed, "scenario_class": "operating_condition", **metrics})
        for label, multipliers in BATCH_PROXIES.items():
            batch_rows = _batch_rows(base_g1_cfg, study_cfg, seed, label, multipliers)
            metrics = _scenario_metrics(label, batch_rows, study_cfg, trained_q2)
            raw_monte_carlo.append({"seed": seed, "scenario_class": "assumed_batch_proxy", **metrics})

    aggregate = _aggregate_seed_metrics(raw_monte_carlo, study_cfg.q4.seeds)
    sensitivity_raw, sensitivity_rank = _sensitivity(base_g1_cfg, study_cfg)
    ood = _ood_cases()
    common.write_csv(os.path.join(out_dir, "q4_monte_carlo_raw.csv"), raw_monte_carlo)
    common.write_csv(os.path.join(out_dir, "q4_monte_carlo_summary.csv"), aggregate)
    common.write_csv(os.path.join(out_dir, "q4_sensitivity_oat.csv"), sensitivity_raw)
    common.write_csv(os.path.join(out_dir, "q4_sensitivity_rank.csv"), sensitivity_rank)
    common.write_csv(os.path.join(out_dir, "q4_ood_abstention.csv"), ood)

    by_name = {row["scenario"]: row for row in aggregate}
    result = {
        "scope": "SUPPORTED_DOMAIN_SIMULATION_AND_EXPLICIT_ABSTENTION",
        "seeds": list(study_cfg.q4.seeds),
        "operating_scenarios": [name for name, _, _, _ in OPERATING_SCENARIOS],
        "batch_proxy_status": "[ASSUMED][UPDATEABLE] parameter shifts and higher cell variability; not measured batch data",
        "monte_carlo_summary": aggregate,
        "sensitivity_design": {
            "method": "one-at-a-time",
            "fraction": study_cfg.q4.sensitivity_fraction,
            "parameters": list(SENSITIVITY_PARAMETERS),
            "interpretation": "local sensitivity inside the G0 ledger, not global identifiability",
        },
        "ood_cases": ood,
        "engineering_triggers": [
            {
                "condition": "45 degC or 2C in this simulation support",
                "action": "increase inspection frequency and re-estimate SOH/RUL before regrouping",
                "status": "[RESULT][UPDATEABLE] simulation-conditioned rule, not industry standard",
            },
            {
                "condition": "screening gate or uncertainty gate fails",
                "action": "do not force assignment; route to additional testing or non-second-life disposition",
                "status": "[CONFIRMED] decision logic; thresholds remain updateable",
            },
            {
                "condition": "any OOD marker",
                "action": "abstain from numeric prediction and require an applicable model/data source",
                "status": "[CONFIRMED] scope control",
            },
        ],
        "baseline_reference": by_name.get("baseline"),
    }
    common.write_json(os.path.join(out_dir, "q4_summary.json"), result)
    return {
        "summary": result,
        "raw": raw_monte_carlo,
        "aggregate": aggregate,
        "sensitivity_raw": sensitivity_raw,
        "sensitivity_rank": sensitivity_rank,
    }
