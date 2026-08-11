"""问题3：风险约束筛选、候选组生成与 set-packing MILP。"""
from __future__ import annotations

import itertools
import math
import os
from collections import Counter

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_array

from . import common, data


def aft_prediction_map(cell_summaries: list[dict], aft_model) -> dict[str, dict]:
    from .q2 import _matrix

    median, lower, upper = aft_model.predict_lifetime(_matrix(cell_summaries))
    return {
        row["cell_id"]: {
            "predicted_lifetime": float(median[index]),
            "lifetime_lower_90": float(lower[index]),
            "lifetime_upper_90": float(upper[index]),
        }
        for index, row in enumerate(cell_summaries)
    }


def oof_aft_prediction_map(rul_predictions: list[dict]) -> dict[str, dict]:
    rows = [row for row in rul_predictions if row["model"] == "lognormal_aft_censored"]
    if len({row["cell_id"] for row in rows}) != len(rows):
        raise ValueError("AFT OOF 预测必须每颗电芯恰好一条")
    return {
        row["cell_id"]: {
            "predicted_lifetime": float(row["predicted_lifetime"]),
            "lifetime_lower_90": float(row["lifetime_lower_90"]),
            "lifetime_upper_90": float(row["lifetime_upper_90"]),
        }
        for row in rows
    }


def build_candidate_pool(grouped: dict[str, list[dict]], predictions: dict[str, dict], study_cfg) -> list[dict]:
    q3 = study_cfg.q3
    candidates = []
    for cell_id, records in grouped.items():
        feature = data.feature_at_cycle(records, q3.retirement_cycle, study_cfg.q2.history_window_cycles)
        prediction = predictions[cell_id]
        lower_rul = prediction["lifetime_lower_90"] - q3.retirement_cycle
        median_rul = prediction["predicted_lifetime"] - q3.retirement_cycle
        interval_width = prediction["lifetime_upper_90"] - prediction["lifetime_lower_90"]
        failures = []
        if feature["soh_observed"] < q3.min_soh:
            failures.append("SOH_BELOW_MIN")
        if lower_rul < q3.min_rul_lower_cycles:
            failures.append("RUL_LOWER_BELOW_MIN")
        if feature["resistance_growth"] > q3.max_resistance_growth:
            failures.append("RESISTANCE_GROWTH_ABOVE_MAX")
        if interval_width > q3.max_lifetime_interval_width:
            failures.append("UNCERTAINTY_ABOVE_MAX")
        if not failures and feature["soh_observed"] >= 0.85 and lower_rul >= 250:
            grade = "A"
        elif not failures:
            grade = "B"
        else:
            grade = "REJECT"
        candidates.append({
            "cell_id": cell_id,
            "condition_id": feature["condition_id"],
            "capacity_Ah": feature["capacity_obs"],
            "soh_estimate": feature["soh_observed"],
            "resistance_growth": feature["resistance_growth"],
            "predicted_rul_cycles": median_rul,
            "rul_lower_cycles": lower_rul,
            "lifetime_interval_width": interval_width,
            "eligible": not failures,
            "grade": grade,
            "gate_failures": ";".join(failures) if failures else "NONE",
        })
    return candidates


def _coefficient_of_variation(values) -> float:
    array = np.asarray(values, dtype=float)
    mean = float(np.mean(array))
    return float(np.std(array) / abs(mean)) if not math.isclose(mean, 0.0) else math.inf


def enumerate_candidate_groups(candidates: list[dict], group_size: int, neighbor_pool: int) -> list[dict]:
    eligible = sorted((row for row in candidates if row["eligible"]), key=lambda row: row["cell_id"])
    if len(eligible) < group_size:
        return []
    raw_features = np.asarray([
        [row["capacity_Ah"], row["soh_estimate"], row["predicted_rul_cycles"], row["resistance_growth"]]
        for row in eligible
    ])
    scale = raw_features.std(axis=0)
    scale[scale < 1e-12] = 1.0
    standardized = (raw_features - raw_features.mean(axis=0)) / scale
    group_indices: set[tuple[int, ...]] = set()
    pool_size = min(neighbor_pool, len(eligible))
    for anchor in range(len(eligible)):
        distances = np.sum((standardized - standardized[anchor]) ** 2, axis=1)
        neighbors = sorted(np.argsort(distances)[:pool_size].tolist())
        for combination in itertools.combinations(neighbors, group_size):
            if anchor in combination:
                group_indices.add(tuple(combination))
    groups = []
    for indices in sorted(group_indices):
        members = [eligible[index] for index in indices]
        capacity = [row["capacity_Ah"] for row in members]
        soh = [row["soh_estimate"] for row in members]
        rul = [row["predicted_rul_cycles"] for row in members]
        resistance = [row["resistance_growth"] for row in members]
        uncertainty = [row["lifetime_interval_width"] for row in members]
        capacity_cv = _coefficient_of_variation(capacity)
        soh_range = max(soh) - min(soh)
        rul_cv = _coefficient_of_variation(rul)
        resistance_range = max(resistance) - min(resistance)
        groups.append({
            "members": tuple(row["cell_id"] for row in members),
            "mean_capacity_Ah": float(np.mean(capacity)),
            "min_soh": min(soh),
            "min_predicted_rul": min(rul),
            "capacity_cv": capacity_cv,
            "soh_range": soh_range,
            "rul_cv": rul_cv,
            "resistance_range": resistance_range,
            "raw_benefit": float(np.mean(capacity) * min(rul) * np.mean(soh)),
            "raw_inconsistency": capacity_cv + 2.0 * soh_range + 0.5 * rul_cv + resistance_range,
            "raw_risk": float(np.mean(uncertainty) / max(min(rul), 1.0)),
            "raw_cost": float(group_size + 20.0 * capacity_cv + 10.0 * soh_range + 5.0 * resistance_range),
        })
    if not groups:
        return groups
    for source, target in (
        ("raw_benefit", "benefit_index"),
        ("raw_inconsistency", "inconsistency_index"),
        ("raw_risk", "risk_index"),
        ("raw_cost", "cost_index"),
    ):
        normalized = common.minmax([row[source] for row in groups])
        for row, value in zip(groups, normalized):
            row[target] = value
    for index, row in enumerate(groups):
        row["group_id"] = f"candidate_{index:05d}"
    return groups


def group_score(group: dict, weights) -> float:
    benefit, consistency, risk, cost = weights
    return float(
        benefit * group["benefit_index"]
        - consistency * group["inconsistency_index"]
        - risk * group["risk_index"]
        - cost * group["cost_index"]
    )


def solve_milp(groups: list[dict], weights, target_groups: int) -> dict:
    if target_groups < 1:
        raise ValueError("target_groups 必须为正")
    cells = sorted({cell for group in groups for cell in group["members"]})
    cell_index = {cell: index for index, cell in enumerate(cells)}
    matrix_rows, matrix_columns, matrix_values = [], [], []
    for column, group in enumerate(groups):
        for cell in group["members"]:
            matrix_rows.append(cell_index[cell])
            matrix_columns.append(column)
            matrix_values.append(1.0)
        matrix_rows.append(len(cells))
        matrix_columns.append(column)
        matrix_values.append(1.0)
    constraint_matrix = coo_array(
        (matrix_values, (matrix_rows, matrix_columns)),
        shape=(len(cells) + 1, len(groups)),
    ).tocsc()
    lower = np.concatenate([np.full(len(cells), -np.inf), [target_groups]])
    upper = np.concatenate([np.ones(len(cells)), [target_groups]])
    scores = np.asarray([group_score(group, weights) for group in groups])
    result = milp(
        c=-scores,
        integrality=np.ones(len(groups)),
        bounds=Bounds(0.0, 1.0),
        constraints=LinearConstraint(constraint_matrix, lower, upper),
        options={"time_limit": 60.0, "mip_rel_gap": 0.0},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"MILP 未得到可行最优解: {result.message}")
    selected = [groups[index] for index, value in enumerate(result.x) if value > 0.5]
    return {
        "method": "MILP",
        "selected": selected,
        "solver_status": str(result.message),
        "objective": float(sum(group_score(group, weights) for group in selected)),
        "mip_gap": float(getattr(result, "mip_gap", 0.0) or 0.0),
    }


def solve_greedy(groups: list[dict], weights, target_groups: int) -> dict:
    selected, used = [], set()
    ranked = sorted(groups, key=lambda group: (-group_score(group, weights), group["members"]))
    for group in ranked:
        if not used.intersection(group["members"]):
            selected.append(group)
            used.update(group["members"])
            if len(selected) == target_groups:
                break
    if len(selected) != target_groups:
        raise RuntimeError("greedy 基线未能构造目标数量的互斥编组")
    return {
        "method": "greedy",
        "selected": selected,
        "solver_status": "FEASIBLE_HEURISTIC",
        "objective": float(sum(group_score(group, weights) for group in selected)),
        "mip_gap": None,
    }


def _solution_summary(name: str, solution: dict, weights, group_size: int) -> dict:
    selected = solution["selected"]
    members = [cell for group in selected for cell in group["members"]]
    counts = Counter(members)
    return {
        "alternative": name,
        "method": solution["method"],
        "n_groups": len(selected),
        "n_cells_used": len(members),
        "duplicate_cell_assignments": sum(count - 1 for count in counts.values() if count > 1),
        "wrong_group_sizes": sum(len(group["members"]) != group_size for group in selected),
        "objective": solution["objective"],
        "mean_benefit_index": float(np.mean([group["benefit_index"] for group in selected])),
        "mean_inconsistency_index": float(np.mean([group["inconsistency_index"] for group in selected])),
        "mean_risk_index": float(np.mean([group["risk_index"] for group in selected])),
        "mean_cost_index": float(np.mean([group["cost_index"] for group in selected])),
        "weights_benefit_consistency_risk_cost": "/".join(f"{value:g}" for value in weights),
        "solver_status": solution["solver_status"],
        "mip_gap": solution["mip_gap"],
    }


def _mark_nondominated(rows: list[dict]) -> None:
    for candidate in rows:
        dominated = False
        for other in rows:
            if candidate is other:
                continue
            no_worse = (
                other["mean_benefit_index"] >= candidate["mean_benefit_index"]
                and other["mean_inconsistency_index"] <= candidate["mean_inconsistency_index"]
                and other["mean_risk_index"] <= candidate["mean_risk_index"]
                and other["mean_cost_index"] <= candidate["mean_cost_index"]
            )
            strictly_better = (
                other["mean_benefit_index"] > candidate["mean_benefit_index"]
                or other["mean_inconsistency_index"] < candidate["mean_inconsistency_index"]
                or other["mean_risk_index"] < candidate["mean_risk_index"]
                or other["mean_cost_index"] < candidate["mean_cost_index"]
            )
            if no_worse and strictly_better:
                dominated = True
                break
        candidate["nondominated_in_weight_sweep"] = not dominated


def optimize_pool(candidates: list[dict], study_cfg, target_groups: int | None = None) -> dict:
    eligible_count = sum(row["eligible"] for row in candidates)
    requested = study_cfg.q3.target_groups if target_groups is None else target_groups
    target = min(requested, eligible_count // study_cfg.q3.group_size)
    if target < 1:
        return {"groups": [], "solutions": {}, "summaries": [], "target_groups": 0}
    groups = enumerate_candidate_groups(
        candidates, study_cfg.q3.group_size, study_cfg.q3.neighbor_pool
    )
    solutions = {}
    summaries = []
    for name, weights in study_cfg.q3.weights.items():
        milp_solution = solve_milp(groups, weights, target)
        solutions[name] = milp_solution
        summaries.append(_solution_summary(name, milp_solution, weights, study_cfg.q3.group_size))
    balanced_weights = study_cfg.q3.weights["balanced"]
    greedy = solve_greedy(groups, balanced_weights, target)
    solutions["balanced_greedy"] = greedy
    summaries.append(_solution_summary(
        "balanced_greedy", greedy, balanced_weights, study_cfg.q3.group_size
    ))
    _mark_nondominated(summaries)
    return {"groups": groups, "solutions": solutions, "summaries": summaries, "target_groups": target}


def analyze(study_cfg, rows: list[dict], q2_result: dict, out_dir: str) -> dict:
    grouped = data.group_cells(rows)
    predictions = oof_aft_prediction_map(q2_result["rul_predictions"])
    candidates = build_candidate_pool(grouped, predictions, study_cfg)
    optimization = optimize_pool(candidates, study_cfg)

    assignments = []
    selected_group_rows = []
    for alternative, solution in optimization["solutions"].items():
        for group_number, group in enumerate(solution["selected"], start=1):
            selected_group_rows.append({
                "alternative": alternative,
                "selected_group": group_number,
                **{key: value for key, value in group.items() if key != "members"},
                "members": ";".join(group["members"]),
            })
            for cell_id in group["members"]:
                assignments.append({
                    "alternative": alternative,
                    "selected_group": group_number,
                    "cell_id": cell_id,
                })
    common.write_csv(os.path.join(out_dir, "q3_candidate_screening.csv"), candidates)
    common.write_csv(os.path.join(out_dir, "q3_selected_groups.csv"), selected_group_rows)
    common.write_csv(os.path.join(out_dir, "q3_assignments.csv"), assignments)
    common.write_csv(os.path.join(out_dir, "q3_solution_summary.csv"), optimization["summaries"])

    failure_counts = Counter()
    for candidate in candidates:
        if candidate["gate_failures"] != "NONE":
            failure_counts.update(candidate["gate_failures"].split(";"))
    milp_rows = [row for row in optimization["summaries"] if row["method"] == "MILP"]
    result = {
        "scope": "DIMENSIONLESS_SIMULATION_DECISION_ANALYSIS",
        "candidate_cells": len(candidates),
        "eligible_cells": sum(row["eligible"] for row in candidates),
        "screening_rate": sum(row["eligible"] for row in candidates) / len(candidates),
        "gate_failure_counts": dict(failure_counts),
        "hard_gates": {
            "min_soh": study_cfg.q3.min_soh,
            "min_rul_lower_cycles": study_cfg.q3.min_rul_lower_cycles,
            "max_resistance_growth": study_cfg.q3.max_resistance_growth,
            "max_lifetime_interval_width": study_cfg.q3.max_lifetime_interval_width,
            "status": "[ASSUMED][UPDATEABLE] scenario thresholds",
        },
        "candidate_groups": len(optimization["groups"]),
        "target_groups": optimization["target_groups"],
        "solutions": optimization["summaries"],
        "constraint_audit": {
            "all_milp_solutions_exact_group_count": all(
                row["n_groups"] == optimization["target_groups"] for row in milp_rows
            ),
            "duplicate_assignments": sum(row["duplicate_cell_assignments"] for row in milp_rows),
            "wrong_group_sizes": sum(row["wrong_group_sizes"] for row in milp_rows),
        },
        "economics_boundary": "cost and benefit are normalized dimensionless indices; no currency claim",
    }
    common.write_json(os.path.join(out_dir, "q3_summary.json"), result)
    return {"summary": result, "candidates": candidates, **optimization}
