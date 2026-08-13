"""V3 contract tests: written before implementation (RED phase)."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys

import pytest

CODE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(CODE_ROOT)
sys.path.insert(0, CODE_ROOT)

from battery_study import config, data, v3


@pytest.fixture(scope="module")
def inputs():
    study_cfg = config.load_config(os.path.join(REPO_ROOT, "configs", "study_pipeline.json"))
    g1_cfg, dataset = data.generate_factorial_dataset(study_cfg)
    return study_cfg, g1_cfg, dataset


def test_retirement_risk_set_uses_conditional_duration(inputs):
    study_cfg, _, dataset = inputs
    rows = v3.retirement_risk_set(
        dataset["rows"], study_cfg, retirement_cycle=750, threshold=study_cfg.q1.critical_soh
    )
    assert len(rows) == 92
    assert sum(row["event_observed"] for row in rows) == 27
    assert sum(not row["event_observed"] for row in rows) == 65
    assert {row["retirement_cycle"] for row in rows} == {750}
    assert all(row["conditional_duration"] <= 250 for row in rows)
    assert all(row["cycle"] == 750 for row in rows)


def test_pressure_track_keeps_cycle_750_continuous(inputs):
    study_cfg, g1_cfg, dataset = inputs
    grouped = data.group_cells(dataset["rows"])
    cell_id = "baseline_0"
    tracked = v3.track_fixed_cell(
        cell_id=cell_id,
        records=grouped[cell_id],
        g1_cfg=g1_cfg,
        stress=(45.0, 2.0, 100.0),
        retirement_cycle=750,
    )
    assert tracked[0]["cycle"] == 750
    assert tracked[-1]["cycle"] == 1000
    assert tracked[0]["soh"] == pytest.approx(grouped[cell_id][749]["soh"], abs=1e-9)
    assert tracked[0]["resistance_true"] == pytest.approx(
        grouped[cell_id][749]["resistance_true"], abs=1e-9
    )
    assert tracked[0]["temperature"] == grouped[cell_id][749]["temperature"]
    assert tracked[0]["c_rate"] == grouped[cell_id][749]["c_rate"]
    assert tracked[0]["dod"] == grouped[cell_id][749]["dod"]
    assert tracked[1]["cycle"] == 751
    assert tracked[1]["temperature"] == 45.0
    assert tracked[1]["c_rate"] == 2.0
    assert tracked[1]["dod"] == 100.0
    assert tracked[0]["formula_continuity_error"] <= 1e-6


def test_pressure_track_rejects_corrupted_boundary(inputs):
    _, g1_cfg, dataset = inputs
    records = copy.deepcopy(data.group_cells(dataset["rows"])["baseline_0"])
    records[749]["soh"] += 0.01
    with pytest.raises(RuntimeError, match="cycle 750 状态无法由原电芯参数重建"):
        v3.track_fixed_cell(
            cell_id="baseline_0", records=records, g1_cfg=g1_cfg,
            stress=(45.0, 2.0, 100.0), retirement_cycle=750,
        )


def test_decision_modes_use_distinct_rul_gates():
    candidate = {
        "cell_id": "c1",
        "condition_id": "baseline",
        "capacity_Ah": 1.8,
        "soh_estimate": 0.82,
        "resistance_growth": 0.10,
        "predicted_rul_cycles": 80.0,
        "rul_lower_cycles": 20.0,
        "lifetime_interval_width": 100.0,
    }
    point = v3.apply_decision_gate(candidate, "POINT", min_rul_cycles=60.0, min_rul_lower_cycles=40.0)
    interval = v3.apply_decision_gate(
        candidate, "INTERVAL_RISK", min_rul_cycles=60.0, min_rul_lower_cycles=40.0
    )
    assert point["eligible"] is True
    assert interval["eligible"] is False
    assert "RUL_LOWER_BELOW_MIN" in interval["gate_failures"]


def test_observation_pressure_changes_measurements_not_latent_state(inputs):
    _, _, dataset = inputs
    regime = {
        "name": "light",
        "rpt_period_cycles": 50,
        "capacity_recovery_pct": 0.4,
        "resistance_recovery_pct": 0.8,
        "outlier_fraction": 0.002,
        "outlier_scale": 3.0,
    }
    first, first_audit = v3.apply_observation_pressure(dataset["rows"], regime, seed=17)
    second, second_audit = v3.apply_observation_pressure(dataset["rows"], regime, seed=17)
    assert first == second
    assert first_audit == second_audit
    assert any(a["capacity_obs"] != b["capacity_obs"] for a, b in zip(dataset["rows"], first))
    assert all(a["capacity_true"] == b["capacity_true"] for a, b in zip(dataset["rows"], first))
    assert all(a["resistance_true"] == b["resistance_true"] for a, b in zip(dataset["rows"], first))
    assert first[:2] == dataset["rows"][:2]
    assert first_audit["latent_state_unchanged"] is True
    assert first_audit["rpt_affected_rows"] > 0


def test_observation_pressure_off_is_exact_identity(inputs):
    _, _, dataset = inputs
    regime = {
        "name": "none",
        "rpt_period_cycles": 0,
        "capacity_recovery_pct": 0.0,
        "resistance_recovery_pct": 0.0,
        "outlier_fraction": 0.0,
        "outlier_scale": 0.0,
    }
    rows, audit = v3.apply_observation_pressure(dataset["rows"], regime, seed=17)
    assert rows == dataset["rows"]
    assert audit["changed_measurement_rows"] == 0


def test_jaccard_is_bounded_and_empty_is_defined():
    assert v3.jaccard({"a"}, {"a", "b"}) == pytest.approx(0.5)
    assert v3.jaccard(set(), set()) == 1.0
    assert v3.jaccard(set(), {"a"}) == 0.0


def test_retirement_oof_predictions_are_unique_and_disjoint(inputs):
    study_cfg, _, dataset = inputs
    risk_set = v3.retirement_risk_set(
        dataset["rows"], study_cfg, retirement_cycle=750, threshold=study_cfg.q1.critical_soh
    )
    predictions, audit = v3.cross_validated_retirement_predictions(risk_set, study_cfg)
    assert len(predictions) == len(risk_set) == 92
    assert len({row["cell_id"] for row in predictions}) == 92
    assert all(row["rul_lower_90"] <= row["predicted_rul"] <= row["rul_upper_90"] for row in predictions)
    assert any(row["rul_upper_90"] > 3000.0 for row in predictions)
    assert all(not row["train_test_overlap"] for row in audit)
    assert {row["interval_calibration_method"] for row in predictions} == {"nested_group_oof"}
    assert sum(row["n_test_cells"] for row in audit) == 92
    assert sum(row["event_observed"] for row in predictions) == 27


def test_point_and_interval_decisions_share_raw_risk_set(inputs):
    study_cfg, _, dataset = inputs
    risk_set = v3.retirement_risk_set(
        dataset["rows"], study_cfg, retirement_cycle=750, threshold=study_cfg.q1.critical_soh
    )
    predictions, _ = v3.cross_validated_retirement_predictions(risk_set, study_cfg)
    decisions = v3.build_decision_pools(risk_set, predictions, study_cfg)
    assert all(row["actual_interval_width"] > 0.0 for rows in decisions.values() for row in rows)
    point_ids = {row["cell_id"] for row in decisions["POINT"]}
    interval_ids = {row["cell_id"] for row in decisions["INTERVAL_RISK"]}
    assert point_ids == interval_ids == {row["cell_id"] for row in risk_set}
    assert sum(row["eligible"] for row in decisions["INTERVAL_RISK"]) <= sum(
        row["eligible"] for row in decisions["POINT"]
    )
    for mode in ("POINT", "INTERVAL_RISK"):
        solution = v3.optimize_decision(
            decisions[mode], study_cfg, tuple(study_cfg.q3.weights["balanced"])
        )
        selected = [
            row for row in decisions[mode]
            if row["cell_id"] in solution["selected_cell_ids"]
        ]
        assert solution["weakest_selected_soh"] == min(row["soh_estimate"] for row in selected)
        assert solution["weakest_selected_rul_lower_cycles"] == min(
            row["rul_lower_cycles"] for row in selected
        )
        assert solution["largest_selected_resistance_growth"] == max(
            row["resistance_growth"] for row in selected
        )
        assert solution["largest_selected_interval_width"] == max(
            row["actual_interval_width"] for row in selected
        )


def test_interval_risk_milp_uses_rul_lower_bound_in_group_metrics(inputs):
    study_cfg, _, _ = inputs
    candidates = []
    for index in range(4):
        candidates.append({
            "cell_id": f"cell_{index}",
            "eligible": True,
            "capacity_Ah": 2.0 + index * 0.01,
            "soh_estimate": 0.9 - index * 0.01,
            "resistance_growth": 0.1 + index * 0.01,
            "predicted_rul_cycles": 1000.0 + index * 100.0,
            "rul_lower_cycles": 100.0 + index * 10.0,
            "decision_rul_cycles": 100.0 + index * 10.0,
            "lifetime_interval_width": 500.0,
            "actual_interval_width": 500.0,
        })
    solution = v3.optimize_decision(
        candidates,
        study_cfg,
        tuple(study_cfg.q3.weights["balanced"]),
        target_groups=1,
    )
    assert solution["selected"][0]["min_predicted_rul"] == 100.0


def test_decision_abstains_instead_of_relaxing_gates_when_target_is_unreachable(inputs):
    study_cfg, _, _ = inputs
    candidates = []
    for index in range(20):
        candidates.append({
            "cell_id": f"cell_{index}",
            "eligible": index < 12,
            "capacity_Ah": 2.0 + index * 0.001,
            "soh_estimate": 0.9,
            "resistance_growth": 0.1,
            "predicted_rul_cycles": 100.0,
            "rul_lower_cycles": 80.0,
            "decision_rul_cycles": 80.0,
            "lifetime_interval_width": 100.0,
            "actual_interval_width": 100.0,
            "gate_failures": "NONE" if index < 12 else "SOH_BELOW_MIN",
        })
    solution = v3.optimize_decision(
        candidates, study_cfg, tuple(study_cfg.q3.weights["balanced"]), target_groups=8
    )
    assert solution["decision_status"] == "ABSTAIN_INSUFFICIENT_FEASIBILITY"
    assert solution["requested_groups"] == 8
    assert solution["max_feasible_groups"] == solution["n_groups"] == 3
    assert solution["group_shortfall"] == 5
    assert solution["thresholds_relaxed"] is False
    assert solution["abstention_reasons"] == "INSUFFICIENT_ELIGIBLE_CELLS"


def test_decision_abstains_when_group_overlap_limits_capacity(inputs, monkeypatch):
    study_cfg, _, _ = inputs
    candidates = [{
        "cell_id": f"cell_{index}", "eligible": True,
        "capacity_Ah": 2.0, "soh_estimate": 0.9, "resistance_growth": 0.1,
        "predicted_rul_cycles": 100.0, "rul_lower_cycles": 80.0,
        "decision_rul_cycles": 80.0, "lifetime_interval_width": 100.0,
        "actual_interval_width": 100.0, "gate_failures": "NONE",
    } for index in range(32)]
    groups = []
    for index in range(8):
        groups.append({
            "members": ("cell_0", f"cell_{1 + 3 * index}",
                        f"cell_{2 + 3 * index}", f"cell_{3 + 3 * index}"),
            "mean_capacity_Ah": 2.0, "min_soh": 0.9, "min_predicted_rul": 80.0,
            "capacity_cv": 0.0, "soh_range": 0.0, "rul_cv": 0.0,
            "resistance_range": 0.0, "raw_benefit": 1.0,
            "raw_inconsistency": 0.0, "raw_risk": 0.0, "raw_cost": 1.0,
            "benefit_index": 0.5, "inconsistency_index": 0.5,
            "risk_index": 0.5, "cost_index": 0.5,
        })
    monkeypatch.setattr(v3.q3, "enumerate_candidate_groups", lambda *args, **kwargs: groups)
    solution = v3.optimize_decision(
        candidates, study_cfg, tuple(study_cfg.q3.weights["balanced"]), target_groups=8
    )
    assert solution["eligible_cells"] == 32
    assert solution["max_feasible_groups"] == solution["n_groups"] == 1
    assert solution["group_shortfall"] == 7
    assert solution["decision_status"] == "ABSTAIN_INSUFFICIENT_FEASIBILITY"
    assert solution["abstention_reasons"] == "GROUP_COMPATIBILITY_LIMIT"
    assert solution["thresholds_relaxed"] is False


def test_stability_sweep_is_oat_and_reports_jaccard(inputs):
    study_cfg, _, dataset = inputs
    settings = v3.load_settings(os.path.join(REPO_ROOT, "configs", "study_pipeline_v3.json"))
    result = v3.stability_sweep(study_cfg, settings, seeds=(42,))
    assert result
    assert all(0.0 <= row["selected_cell_jaccard"] <= 1.0 for row in result)
    assert {row["parameter"] for row in result} >= {
        "baseline", "min_soh", "min_rul_lower_cycles", "max_resistance_growth", "weights"
    }
    assert all(row["changed_parameter_count"] <= 1 for row in result)
    assert all(row["eligible_rate"] == pytest.approx(
        row["eligible_cells"] / row["risk_set_cells"]
    ) for row in result)
    assert all(row["thresholds_relaxed"] is False for row in result)
    assert all(row["decision_status"] == (
        "ABSTAIN_INSUFFICIENT_FEASIBILITY" if row["group_shortfall"] else
        "ACCEPT_FIXED_GROUPS"
    ) for row in result)


def test_stability_summary_reports_registered_aggregates():
    rows = [
        {
            "objective": 1.0,
            "objective_delta": 0.0,
            "infeasible": False,
            "selected_cell_jaccard": 1.0,
            "eligible_rate": 0.5,
            "worst_selected_soh_margin": 0.2,
            "worst_selected_rul_lower_margin_cycles": 10.0,
            "worst_selected_resistance_growth_margin": 0.1,
            "worst_selected_interval_width_margin_cycles": 50.0,
        },
        {
            "objective": None,
            "objective_delta": None,
            "infeasible": True,
            "selected_cell_jaccard": 0.75,
            "eligible_rate": 0.25,
            "worst_selected_soh_margin": None,
            "worst_selected_rul_lower_margin_cycles": None,
            "worst_selected_resistance_growth_margin": None,
            "worst_selected_interval_width_margin_cycles": None,
        },
    ]
    summary = v3.summarize_stability(rows)
    assert summary == {
            "jaccard_min": 0.75,
            "jaccard_max": 1.0,
            "eligible_rate_min": 0.25,
            "eligible_rate_max": 0.5,
            "objective_delta_min": 0.0,
            "objective_delta_max": 0.0,
            "worst_selected_soh_margin_min": 0.2,
            "worst_selected_rul_lower_margin_cycles_min": 10.0,
            "worst_selected_resistance_growth_margin_min": 0.1,
            "worst_selected_interval_width_margin_cycles_min": 50.0,
            "infeasible_count": 1,
            "abstention_count": 0,
            "group_shortfall_max": 0,
            "threshold_relaxation_count": 0,
        }


def test_ablation_matrix_has_registered_windows_and_features(inputs):
    study_cfg, _, dataset = inputs
    settings = v3.load_settings(os.path.join(REPO_ROOT, "configs", "study_pipeline_v3.json"))
    rows = v3.run_ablation(study_cfg, settings, dataset["rows"])
    assert {row["history_window"] for row in rows} == {25, 50, 100}
    assert {row["feature_group"] for row in rows} == {
        "capacity", "capacity_resistance", "capacity_operating", "all"
    }
    forbidden = {"soh_true", "lifetime_cycle", "event_observed", "capacity_true"}
    assert all(not forbidden.intersection(row["feature_names"].split(";")) for row in rows)


def test_ablation_summary_reports_best_and_full_vs_capacity_comparisons():
    rows = [
        {"history_window": 25, "feature_group": "capacity", "model": "ridge", "rmse": 0.02},
        {"history_window": 25, "feature_group": "all", "model": "ridge", "rmse": 0.01},
        {
            "history_window": 25,
            "feature_group": "capacity",
            "model": "random_forest",
            "rmse": 0.03,
        },
        {
            "history_window": 25,
            "feature_group": "all",
            "model": "random_forest",
            "rmse": 0.024,
        },
    ]
    summary = v3.summarize_ablation(rows)
    assert summary["best_configuration"] == rows[1]
    assert summary["all_vs_capacity_only"] == [
        {
            "model": "random_forest",
            "history_window": 25,
            "capacity_only_rmse": 0.03,
            "all_features_rmse": 0.024,
            "relative_rmse_reduction": pytest.approx(0.2),
        },
        {
            "model": "ridge",
            "history_window": 25,
            "capacity_only_rmse": 0.02,
            "all_features_rmse": 0.01,
            "relative_rmse_reduction": pytest.approx(0.5),
        },
    ]


def test_fixed_group_tracking_reuses_exact_group_signature(inputs):
    study_cfg, g1_cfg, dataset = inputs
    settings = v3.load_settings(os.path.join(REPO_ROOT, "configs", "study_pipeline_v3.json"))
    risk_set = v3.retirement_risk_set(
        dataset["rows"], study_cfg, retirement_cycle=750, threshold=study_cfg.q1.critical_soh
    )
    predictions, _ = v3.cross_validated_retirement_predictions(risk_set, study_cfg)
    decisions = v3.build_decision_pools(risk_set, predictions, study_cfg)
    tracked = v3.track_fixed_groups(
        dataset["rows"], g1_cfg, study_cfg, settings, decisions["INTERVAL_RISK"]
    )
    signatures = {row["scenario"]: row["group_signature"] for row in tracked["group_summary"]}
    assert len(set(signatures.values())) == 1
    assert all(row["cycle_750_continuity_error"] <= 1e-6 for row in tracked["cell_rows"])
    for summary in tracked["group_summary"]:
        cells = [row for row in tracked["cell_rows"] if (
            row["scenario"] == summary["scenario"]
            and row["group_number"] == summary["group_number"]
        )]
        growth = [row["resistance_growth_increment"] for row in cells]
        assert summary["mean_soh_change"] == pytest.approx(
            sum(row["soh_change"] for row in cells) / len(cells)
        )
        assert summary["mean_resistance_growth_increment"] == pytest.approx(sum(growth) / len(growth))
        assert summary["resistance_range"] == pytest.approx(max(growth) - min(growth))
        if summary["right_censored_cell_count"]:
            assert summary["rul_cv"] is None
            assert summary["rul_consistency_status"] == "RIGHT_CENSORED_NOT_IDENTIFIABLE"
    baseline = {
        row["cell_id"]: row for row in tracked["cell_rows"] if row["scenario"] == "baseline_use"
    }
    for row in tracked["cell_rows"]:
        if row["scenario"] == "baseline_use":
            assert row["rul_change_status"] == "REFERENCE"
            assert row["rul_change_cycles"] == 0.0
        elif not baseline[row["cell_id"]]["post_750_event_observed"] and row["post_750_event_observed"]:
            assert row["rul_change_status"] == "UPPER_BOUND"
            assert row["rul_change_cycles"] is None
            assert row["rul_change_upper_bound_cycles"] <= 0.0
        elif not baseline[row["cell_id"]]["post_750_event_observed"]:
            assert row["rul_change_status"] == "NOT_IDENTIFIABLE_BOTH_RIGHT_CENSORED"
            assert row["rul_change_cycles"] is None
    assert all("group_rul_change_status" in row for row in tracked["group_summary"])
    scenario_names = [row["name"] for row in settings["pressure_scenarios"]]
    assert v3.fixed_group_membership_is_constant(tracked, scenario_names)
    corrupted = copy.deepcopy(tracked)
    corrupted["cell_rows"][0]["cell_id"] = "different_cell"
    assert not v3.fixed_group_membership_is_constant(corrupted, scenario_names)


def test_trigger_rejects_endpoint_breach_before_dispersion_rules():
    triggers = {
        "max_capacity_cv": 0.03,
        "max_soh_range": 0.03,
        "max_rul_cv": 0.25,
        "max_resistance_growth_range": 0.1,
    }
    base = {
        "capacity_cv": 0.0,
        "soh_range": 0.0,
        "rul_cv": None,
        "resistance_range": 0.0,
        "weakest_soh": 0.8,
        "post_750_event_count": 0,
    }
    assert v3._trigger_status(base, triggers) == "REJECT_FORCED_ASSIGNMENT"
    base["weakest_soh"] = 0.9
    base["post_750_event_count"] = 1
    assert v3._trigger_status(base, triggers) == "REJECT_FORCED_ASSIGNMENT"


def test_track_fixed_cell_marks_boundary_as_historical_and_751_as_stress(inputs):
    study_cfg, g1_cfg, dataset = inputs
    records = data.group_cells(dataset["rows"])["T45_C2_D100_0"]
    tracked = v3.track_fixed_cell(
        cell_id="T45_C2_D100_0",
        records=records,
        g1_cfg=g1_cfg,
        stress=(25.0, 0.5, 50.0),
        retirement_cycle=750,
    )
    assert tracked[0]["temperature"] == records[749]["temperature"]
    assert tracked[0]["c_rate"] == records[749]["c_rate"]
    assert tracked[0]["dod"] == records[749]["dod"]
    assert tracked[1]["temperature"] == 25.0
    assert tracked[1]["c_rate"] == 0.5
    assert tracked[1]["dod"] == 50.0


def test_v3_output_path_rejects_protected_directories(tmp_path):
    project_root = REPO_ROOT
    for path in (os.path.join(project_root, "study_output"),
                 os.path.join(project_root, "g1_output"), project_root):
        with pytest.raises(ValueError, match="V3 输出目录受保护"):
            v3.validate_output_dir(project_root, path)
    v3.validate_output_dir(project_root, str(tmp_path / "v3-out"))


def test_manifest_command_records_actual_config_and_output_paths():
    command = v3._manifest_command(
        REPO_ROOT,
        os.path.join(REPO_ROOT, "configs", "study_pipeline_v3.json"),
        os.path.join(REPO_ROOT, "study_output_v3_repro_a"),
    )
    assert command == (
        "PYTHONPATH=code python -m battery_study.v3_cli "
        "--config configs/study_pipeline_v3.json --out study_output_v3_repro_a"
    )


def test_manifest_verifier_checks_relative_files_and_excludes_manifest(tmp_path):
    source = tmp_path / "source.txt"
    artifact = tmp_path / "artifact.csv"
    source.write_text("source\n", encoding="utf-8")
    artifact.write_text("a,b\n1,2\n", encoding="utf-8")

    def entry(path):
        data_bytes = path.read_bytes()
        return {"path": path.name, "bytes": len(data_bytes),
                "sha256": hashlib.sha256(data_bytes).hexdigest()}

    manifest_path = tmp_path / "run_manifest.json"
    (tmp_path / "technical").mkdir()
    (tmp_path / "technical" / "v2_evidence_status.json").write_text(json.dumps({
        "run_status": "PASS",
        "evidence_status": "HOLD_RPT_SENSITIVITY",
        "paper_eligible": False,
    }), encoding="utf-8")
    manifest_path.write_text(json.dumps({
        "v2_status": {"evidence_status": "HOLD_RPT_SENSITIVITY", "paper_eligible": False},
        "source_files": [entry(source)],
        "artifacts": [entry(artifact)],
    }), encoding="utf-8")
    result = v3.verify_manifest(str(manifest_path), project_root=str(tmp_path))
    assert result["status"] == "PASS"
    assert result["checked_files"] == 2


def test_manifest_source_paths_include_v3_and_g1_configs():
    v3_config = os.path.join(REPO_ROOT, "configs", "study_pipeline_v3.json")
    g1_config = os.path.join(REPO_ROOT, "configs", "g1_smoke.json")
    paths = v3._source_paths(
        REPO_ROOT,
        source_config_path=v3_config,
        source_g1_config_path=g1_config,
    )
    assert v3_config in paths
    assert g1_config in paths
    assert os.path.join(REPO_ROOT, "requirements-study.txt") in paths
    assert os.path.join(REPO_ROOT, "technical", "v2_evidence_status.json") in paths
    assert os.path.join(REPO_ROOT, "evidence", "parameter_ledger.txt") in paths
    assert os.path.join(REPO_ROOT, "evidence", "source_ledger.txt") in paths


def test_v3_document_paths_cover_technical_and_paper_handoffs():
    report = os.path.join(REPO_ROOT, "technical", "V3_VALIDATION_REPORT.md")
    paths = set(v3._v3_document_paths(REPO_ROOT, report))
    assert paths == {
        os.path.join(REPO_ROOT, "README.md"),
        os.path.join(REPO_ROOT, "PAPER_AGENT_START_HERE.md"),
        os.path.join(REPO_ROOT, "论文初稿.md"),
        os.path.join(REPO_ROOT, "handoffs", "A5_paper_technical_bridge.md"),
        os.path.join(REPO_ROOT, "handoffs", "PROJECT_COMMAND_CENTER.md"),
        os.path.join(REPO_ROOT, "technical", "PAPER_TECHNICAL_BRIDGE.md"),
        os.path.join(REPO_ROOT, "technical", "PAPER_WRITING_FACT_SHEET.md"),
        os.path.join(REPO_ROOT, "technical", "TECHNICAL_SOLUTION_FINAL.md"),
        os.path.join(REPO_ROOT, "technical", "FINAL_VALIDATION_REPORT.md"),
        os.path.join(REPO_ROOT, "technical", "FINAL_CHANGELOG_FOR_PAPER.md"),
        os.path.join(REPO_ROOT, "technical", "TECHNICAL_SOLUTION_V3.md"),
        os.path.join(REPO_ROOT, "technical", "V3_EXPERIMENT_PLAN.md"),
        report,
    }


def test_upstream_v1_evidence_paths_exclude_legacy_manifest():
    paths = set(v3._upstream_v1_evidence_paths(REPO_ROOT))
    assert os.path.join(REPO_ROOT, "study_output", "q2_soh_metrics.csv") in paths
    assert os.path.join(REPO_ROOT, "study_output", "q2_rul_metrics.csv") in paths
    assert os.path.join(REPO_ROOT, "study_output", "q4_ood_abstention.csv") in paths
    assert os.path.join(REPO_ROOT, "study_output", "run_manifest.json") not in paths


def test_manifest_verifier_rejects_stale_hash_and_self_reference(tmp_path):
    artifact = tmp_path / "artifact.csv"
    artifact.write_text("a,b\n1,2\n", encoding="utf-8")
    manifest_path = tmp_path / "run_manifest.json"
    manifest_path.write_text(json.dumps({
        "v2_status": {"evidence_status": "HOLD_RPT_SENSITIVITY", "paper_eligible": False},
        "source_files": [],
        "artifacts": [
            {"path": "artifact.csv", "bytes": 0, "sha256": "stale"},
            {"path": "run_manifest.json", "bytes": 1, "sha256": "self"},
        ],
    }), encoding="utf-8")
    result = v3.verify_manifest(str(manifest_path), project_root=str(tmp_path))
    assert result["status"] == "FAIL"
    assert any("字节数" in error or "SHA-256" in error for error in result["errors"])
    assert any("自身" in error for error in result["errors"])
