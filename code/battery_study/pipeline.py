"""G2-G4 端到端实验、验证、图表、文档和证据清单。"""
from __future__ import annotations

import importlib.metadata
import os
import subprocess

from . import common, config, data, q1, q2, q3, q4, reporting, visualization


def _gate(gates: list[dict], condition: bool, name: str, evidence: str) -> None:
    if not condition:
        raise RuntimeError(f"验证闸门失败: {name} ({evidence})")
    gates.append({"gate": name, "status": "PASS", "evidence": evidence})


def validate_results(study_cfg, dataset, results) -> list[dict]:
    gates = []
    expected_conditions = (
        len(study_cfg.factorial.temperatures_C)
        * len(study_cfg.factorial.c_rates_C)
        * len(study_cfg.factorial.dod_pct)
    )
    expected_cells = expected_conditions * study_cfg.factorial.n_cells_per_condition
    _gate(
        gates,
        dataset["meta"]["n_cells"] == expected_cells and dataset["meta"]["n_rows"] == expected_cells * 1000,
        "factorial_shape",
        f"{expected_conditions} conditions, {expected_cells} cells, {expected_cells*1000} rows",
    )
    q1_summary = results["q1"]["summary"]
    for response in ("capacity_fade", "final_resistance_growth"):
        weights = [
            row["normalized_main_effect_weight"]
            for row in q1_summary["factor_effects"] if row["response"] == response
        ]
        _gate(gates, abs(sum(weights) - 1.0) < 1e-9, f"q1_weights_{response}", "three main-effect weights sum to 1")
    _gate(
        gates,
        q1_summary["protocol_identifiability"]["status"] == "NOT_IDENTIFIABLE",
        "q1_protocol_honesty",
        "one CC-CV level produces no fabricated protocol weight",
    )
    q2_summary = results["q2"]["summary"]
    _gate(
        gates,
        q2_summary["split_integrity"]["cell_overlap_all_folds"] == 0,
        "q2_cell_group_split",
        "GroupKFold cell overlap = 0",
    )
    endpoint = q2_summary["rul_endpoint"]
    _gate(
        gates,
        endpoint["observed_events"] + endpoint["right_censored"] == expected_cells,
        "q2_censor_accounting",
        f"{endpoint['observed_events']} events + {endpoint['right_censored']} censored = {expected_cells}",
    )
    q3_audit = results["q3"]["summary"]["constraint_audit"]
    _gate(
        gates,
        q3_audit["all_milp_solutions_exact_group_count"]
        and q3_audit["duplicate_assignments"] == 0
        and q3_audit["wrong_group_sizes"] == 0,
        "q3_milp_constraints",
        "exact target groups; duplicate cells = 0; wrong group sizes = 0",
    )
    q4_result = results["q4"]
    _gate(
        gates,
        all(row["numeric_prediction"] is None for row in q4_result["summary"]["ood_cases"]),
        "q4_ood_abstention",
        "four OOD cases have null numeric predictions",
    )
    _gate(
        gates,
        all(row["n_seeds"] == len(study_cfg.q4.seeds) for row in q4_result["aggregate"]),
        "q4_seed_completeness",
        f"all scenarios include {len(study_cfg.q4.seeds)} seeds",
    )
    return gates


def _write_design_and_summaries(out_dir, g1_cfg, dataset, q1_result):
    design_rows = dataset["meta"]["scenario_specs"]
    common.write_csv(os.path.join(out_dir, "factorial_design.csv"), design_rows)
    common.write_csv(os.path.join(out_dir, "factorial_cell_summary.csv"), q1_result["cell_summaries"])
    common.write_json(os.path.join(out_dir, "factorial_generation_meta.json"), {
        "chemistry": g1_cfg.chemistry,
        "protocol": g1_cfg.protocol,
        "seed": g1_cfg.seed,
        "n_cells": dataset["meta"]["n_cells"],
        "n_rows": dataset["meta"]["n_rows"],
        "raw_rows_persisted": False,
        "reason": "108000 synthetic rows are deterministically regenerated from the manifest command",
    })


def _write_figures(out_dir: str, results: dict) -> list[str]:
    q1_effects = results["q1"]["summary"]["factor_effects"]
    figures = []
    figures.append(visualization.horizontal_bar_chart(
        "Q1 factorial main-effect weights",
        "normalized weight within estimable main effects",
        [f"{row['response']} / {row['factor']}" for row in q1_effects],
        [row["normalized_main_effect_weight"] for row in q1_effects],
        os.path.join(out_dir, "fig_q1_factor_weights.svg"),
    ))
    soh_metrics = results["q2"]["summary"]["soh_metrics"]
    figures.append(visualization.horizontal_bar_chart(
        "Q2 50-cycle SOH forecast",
        "RMSE (SOH)",
        [row["model"] for row in soh_metrics],
        [row["rmse"] for row in soh_metrics],
        os.path.join(out_dir, "fig_q2_soh_rmse.svg"),
        value_format=".6f",
    ))
    rul_metrics = results["q2"]["summary"]["rul_metrics"]
    figures.append(visualization.horizontal_bar_chart(
        "Q2 RUL on observed events",
        "RMSE (cycles; censored cells excluded from point error)",
        [row["model"] for row in rul_metrics],
        [row["rmse"] for row in rul_metrics],
        os.path.join(out_dir, "fig_q2_rul_rmse.svg"),
        value_format=".2f",
    ))
    q3_summaries = results["q3"]["summary"]["solutions"]
    figures.append(visualization.scatter_chart(
        "Q3 solution trade-off",
        "mean inconsistency index (lower is better)",
        "mean benefit index (higher is better)",
        [{
            "label": row["alternative"],
            "x": row["mean_inconsistency_index"],
            "y": row["mean_benefit_index"],
        } for row in q3_summaries],
        os.path.join(out_dir, "fig_q3_tradeoff.svg"),
    ))
    q4_summary = results["q4"]["aggregate"]
    figures.append(visualization.horizontal_bar_chart(
        "Q4 end-of-observation SOH across seeds",
        "mean SOH at cycle 1000",
        [row["scenario"] for row in q4_summary],
        [row["final_soh_mean_mean"] for row in q4_summary],
        os.path.join(out_dir, "fig_q4_final_soh.svg"),
    ))
    importance = {}
    for row in results["q4"]["sensitivity_rank"]:
        value = row["normalized_final_soh_mean_change"]
        if value is not None:
            importance[row["parameter"]] = max(importance.get(row["parameter"], 0.0), abs(value))
    figures.append(visualization.horizontal_bar_chart(
        "Q4 local OAT sensitivity",
        "max absolute normalized SOH response",
        sorted(importance),
        [importance[name] for name in sorted(importance)],
        os.path.join(out_dir, "fig_q4_sensitivity.svg"),
    ))
    return figures


def _git_head(project_root: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project_root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNAVAILABLE"


def _relative(project_root: str, path: str) -> str:
    return os.path.relpath(os.path.abspath(path), project_root).replace(os.sep, "/")


def _artifact_manifest(project_root: str, paths: list[str]) -> list[dict]:
    unique_paths = sorted({os.path.abspath(path) for path in paths})
    return [
        {
            "path": _relative(project_root, path),
            "bytes": os.path.getsize(path),
            "sha256": common.sha256_file(path),
        }
        for path in unique_paths
    ]


def _source_manifest(project_root: str) -> list[dict]:
    paths = []
    for relative_root in ("code/battery_study", "code/g1_generator", "code/tests"):
        absolute_root = os.path.join(project_root, relative_root)
        for root, _, filenames in os.walk(absolute_root):
            for filename in filenames:
                if filename.endswith(".py"):
                    paths.append(os.path.join(root, filename))
    paths.append(os.path.join(project_root, "requirements-study.txt"))
    return _artifact_manifest(project_root, paths)


def run(study_cfg, out_dir: str) -> dict:
    project_root = config.PROJECT_ROOT
    os.makedirs(out_dir, exist_ok=True)
    g1_cfg, dataset = data.generate_factorial_dataset(study_cfg)
    q1_result = q1.analyze(study_cfg, g1_cfg, dataset["rows"], out_dir)
    q2_result = q2.analyze(study_cfg, g1_cfg, dataset["rows"], out_dir)
    q3_result = q3.analyze(study_cfg, dataset["rows"], q2_result, out_dir)
    q4_result = q4.analyze(study_cfg, g1_cfg, q2_result, out_dir)
    results = {"q1": q1_result, "q2": q2_result, "q3": q3_result, "q4": q4_result}
    _write_design_and_summaries(out_dir, g1_cfg, dataset, q1_result)
    figure_paths = _write_figures(out_dir, results)
    gates = validate_results(study_cfg, dataset, results)
    gates_path = common.write_json(os.path.join(out_dir, "validation_gates.json"), gates)
    document_paths = reporting.write_all(project_root, study_cfg, results, gates)

    output_paths = []
    for root, _, filenames in os.walk(out_dir):
        for filename in filenames:
            if filename != "run_manifest.json":
                output_paths.append(os.path.join(root, filename))
    output_paths.extend(document_paths)
    output_paths.extend(figure_paths)
    output_paths.append(gates_path)
    source_config_path = study_cfg.source_g1_path
    study_config_path = getattr(study_cfg, "_loaded_path", config.DEFAULT_CONFIG_PATH)
    manifest = {
        "manifest_version": 1,
        "study_id": study_cfg.study_id,
        "scope": "synthetic NMC study; no external calibration or validation",
        "git_head_before_commit": _git_head(project_root),
        "command": (
            f"PYTHONPATH=code python -m battery_study.cli --config "
            f"{_relative(project_root, study_config_path)} --out {_relative(project_root, out_dir)}"
        ),
        "input_configs": [
            {"path": _relative(project_root, study_config_path), "sha256": common.sha256_file(study_config_path)},
            {"path": _relative(project_root, source_config_path), "sha256": common.sha256_file(source_config_path)},
        ],
        "seeds": {"factorial": study_cfg.study_seed, "robustness": list(study_cfg.q4.seeds)},
        "versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
            "scikit-learn": importlib.metadata.version("scikit-learn"),
        },
        "dataset": {
            "conditions": len(g1_cfg.scenarios),
            "cells": dataset["meta"]["n_cells"],
            "rows_regenerated_not_persisted": dataset["meta"]["n_rows"],
        },
        "validation": gates,
        "source_files": _source_manifest(project_root),
        "artifacts": _artifact_manifest(project_root, output_paths),
        "uncertainty_status": {
            "confirmed": "code paths, support bounds, split integrity, optimization constraints",
            "assumed_updateable": "degradation parameters, thresholds, batch proxies, objective weights",
            "uncertain": "real-world generalization, safety probability, monetary value",
            "ood_abstain": "low temperature, overcharge, overdischarge, >2C",
        },
    }
    manifest_path = common.write_json(os.path.join(out_dir, "run_manifest.json"), manifest)
    return {
        "manifest": manifest_path,
        "results": results,
        "gates": gates,
        "documents": document_paths,
        "figures": figure_paths,
    }
