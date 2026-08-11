"""G2-G4 科学契约与算法回归测试。"""
from __future__ import annotations

import dataclasses
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pytest


CODE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(CODE_ROOT)
sys.path.insert(0, CODE_ROOT)

from battery_study import config, data, q1, q2, q3, q4, visualization


@pytest.fixture(scope="module")
def study_cfg():
    return config.load_config(os.path.join(REPO_ROOT, "configs", "study_pipeline.json"))


@pytest.fixture(scope="module")
def factorial(study_cfg):
    return data.generate_factorial_dataset(study_cfg)


def test_registered_factorial_shape(study_cfg, factorial):
    _, dataset = factorial
    assert dataset["meta"]["n_cells"] == 108
    assert dataset["meta"]["n_rows"] == 108000
    assert len(dataset["meta"]["scenarios"]) == 27


def test_study_config_rejects_out_of_domain_temperature(study_cfg):
    bad_factorial = dataclasses.replace(study_cfg.factorial, temperatures_C=(0.0, 25.0, 35.0))
    bad = dataclasses.replace(study_cfg, factorial=bad_factorial)
    with pytest.raises(ValueError, match="支持域"):
        config.validate_config(bad)


def test_cell_records_are_complete_and_grouped(factorial):
    grouped = data.group_cells(factorial[1]["rows"])
    assert len(grouped) == 108
    assert all(len(records) == 1000 for records in grouped.values())
    assert all(records[0]["cycle"] == 1 and records[-1]["cycle"] == 1000 for records in grouped.values())


def test_split_overlap_is_a_hard_failure():
    data.assert_group_disjoint(["a", "b"], ["c"])
    with pytest.raises(AssertionError, match="跨训练/测试"):
        data.assert_group_disjoint(["a", "b"], ["b", "c"])


@pytest.mark.parametrize(
    ("temperature", "c_rate", "dod", "protocol"),
    [(0, 1, 80, "CC-CV"), (25, 3, 80, "CC-CV"), (25, 1, 110, "CC-CV"), (25, 1, 80, "overcharge")],
)
def test_ood_status_never_allows_numeric_prediction(temperature, c_rate, dod, protocol):
    status = data.supported_domain_status(temperature, c_rate, dod, protocol)
    assert status["status"] == "[OOD/ABSTAIN]"
    assert status["numeric_prediction_allowed"] is False


def test_factor_weights_normalize_with_residual_kept():
    summaries = []
    for temperature in (25.0, 45.0):
        for c_rate in (0.5, 2.0):
            for dod in (50.0, 100.0):
                for replicate in range(3):
                    summaries.append({
                        "temperature": temperature,
                        "c_rate": c_rate,
                        "dod": dod,
                        "response": 0.01 * temperature + 0.1 * c_rate + 0.001 * dod + replicate * 0.001,
                    })
    effects = q1.main_effect_decomposition(summaries, "response")
    assert sum(row["normalized_main_effect_weight"] for row in effects) == pytest.approx(1.0)
    assert all(0.0 <= row["share_total_variance"] <= 1.0 for row in effects)
    assert all("interaction_and_cell_share" in row for row in effects)


def test_knee_is_right_censored_when_efc_does_not_reach_nominal(study_cfg, factorial):
    g1_cfg, dataset = factorial
    grouped = data.group_cells(dataset["rows"])
    dod50 = next(records for records in grouped.values() if records[0]["dod"] == 50.0)
    result = q1.detect_piecewise_knee(dod50, study_cfg.q1, g1_cfg.n_k_EFC)
    assert result["status"] == "RIGHT_CENSORED"
    assert result["detected_knee_efc"] is None
    assert result["max_observed_efc"] == 500.0


def test_knee_hinge_uses_sqrt_efc_and_recovers_simulated_boundary(study_cfg, factorial):
    g1_cfg, dataset = factorial
    grouped = data.group_cells(dataset["rows"])
    dod100 = next(records for records in grouped.values() if records[0]["dod"] == 100.0)
    result = q1.detect_piecewise_knee(dod100, study_cfg.q1, g1_cfg.n_k_EFC)
    assert result["status"] == "DETECTED_IN_SIMULATION"
    assert result["slope_axis"] == "sqrt(EFC)"
    assert abs(result["detected_knee_efc"] - g1_cfg.n_k_EFC) < 80


def test_censored_aft_fits_and_orders_risk():
    rng = np.random.default_rng(7)
    x = np.linspace(-1.0, 1.0, 80).reshape(-1, 1)
    latent = np.exp(6.5 - 0.6 * x[:, 0] + rng.normal(0, 0.08, len(x)))
    censor_at = 700.0
    event = latent <= censor_at
    duration = np.minimum(latent, censor_at)
    model = q2.CensoredLogNormalAFT().fit(x, duration, event)
    predicted, p10, p90 = model.predict_lifetime(np.asarray([[-1.0], [1.0]]))
    assert model.optimization_["success"]
    assert predicted[0] > predicted[1]
    assert np.all(p10 < predicted)
    assert np.all(predicted < p90)


def _candidate(index: int):
    return {
        "cell_id": f"cell_{index}",
        "condition_id": "test",
        "capacity_Ah": 1.7 + 0.01 * index,
        "soh_estimate": 0.82 + 0.002 * index,
        "resistance_growth": 0.2 + 0.004 * index,
        "predicted_rul_cycles": 250.0 + 8.0 * index,
        "rul_lower_cycles": 100.0 + index,
        "lifetime_interval_width": 100.0 + index,
        "eligible": True,
        "grade": "B",
        "gate_failures": "NONE",
    }


def test_milp_enforces_fixed_group_size_and_unique_cells(study_cfg):
    candidates = [_candidate(index) for index in range(12)]
    groups = q3.enumerate_candidate_groups(candidates, group_size=4, neighbor_pool=8)
    solution = q3.solve_milp(groups, study_cfg.q3.weights["balanced"], target_groups=2)
    members = [cell for group in solution["selected"] for cell in group["members"]]
    assert len(solution["selected"]) == 2
    assert all(len(group["members"]) == 4 for group in solution["selected"])
    assert len(members) == len(set(members)) == 8


def test_q4_ood_table_has_no_values():
    rows = q4._ood_cases()
    assert len(rows) == 4
    assert all(row["status"] == "[OOD/ABSTAIN]" for row in rows)
    assert all(row["numeric_prediction"] is None for row in rows)


def test_svg_output_is_parseable(tmp_path):
    path = tmp_path / "chart.svg"
    visualization.horizontal_bar_chart("test", "value", ["a", "b"], [0.2, 0.7], str(path))
    root = ET.parse(path).getroot()
    assert root.tag.endswith("svg")
    assert len(root.findall("{http://www.w3.org/2000/svg}rect")) >= 3
