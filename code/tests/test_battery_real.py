from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from battery_real import core


def make_rows(cells=6, cycles=24, *, chemistry="NMC", with_conditions=True):
    rows = []
    for cell in range(cells):
        condition = f"T{25 + cell % 3}" if with_conditions else ""
        for cycle in range(1, cycles + 1):
            rows.append({
                "source_id": "TEST_ONLY_source",
                "chemistry": chemistry,
                "cell_id": f"cell_{cell}",
                "cycle": cycle,
                "capacity": 1.02 - 0.003 * cycle - 0.0004 * cell + 0.0001 * np.sin(cycle),
                "resistance": 1.0 + 0.01 * cycle + 0.001 * cell,
                "temperature": 25 + cell % 3,
                "c_rate": 1.0,
                "dod": 80.0,
                "protocol": "CC-CV",
                "condition_id": condition,
            })
    return rows


def write_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_validator_rejects_duplicate_nonmonotonic_and_mixed_chemistry():
    rows = make_rows(cells=2, cycles=4)
    with pytest.raises(ValueError, match="重复"):
        core.validate_records(rows + [rows[0]])
    broken = make_rows(cells=1, cycles=4)
    broken[2], broken[3] = broken[3], broken[2]
    with pytest.raises(ValueError, match="单调"):
        core.validate_records(broken)
    mixed = make_rows(cells=2, cycles=4)
    mixed[-1]["chemistry"] = "NCA"
    with pytest.raises(ValueError, match="化学体系"):
        core.validate_records(mixed)
    efc_bad = make_rows(cells=1, cycles=4)
    for row in efc_bad:
        row["efc"] = row["cycle"]
    efc_bad[2]["efc"] = 1
    with pytest.raises(ValueError, match="efc"):
        core.validate_records(efc_bad)


def test_normalization_and_knee_are_explicit_about_censoring():
    rows = make_rows(cells=1, cycles=24)
    records = core.prepare_records(rows)
    one = records["cell_0"]
    assert one[0]["capacity_norm"] == pytest.approx(1.0, abs=0.02)
    result = core.analyze_cell(one, knee_min_points=4, endpoint_soh=0.90)
    assert result["trend_slope"] < 0
    assert result["knee_status"] in {"DETECTED", "RIGHT_CENSORED", "NOT_DETECTED"}


def test_factor_without_replication_abstains():
    rows = make_rows(cells=4, cycles=8)
    for row in rows:
        row["c_rate"] = 1.0
    prepared = core.prepare_records(rows)
    report = core.factor_analysis(prepared, "c_rate")
    assert report["status"] == "ABSTAIN"
    assert "levels" in report["reason"] or "replication" in report["reason"]


def test_constant_target_reports_r2_as_null_not_nan():
    rows = make_rows(cells=6, cycles=12)
    for row in rows:
        row["capacity"] = 1.0
    report = core.evaluate(rows, horizon=2, history_window=4, n_splits=3, bootstrap_reps=20, seed=5)
    assert report["models"]["persistence"]["r2"] is None


def test_historical_features_do_not_read_future_rows():
    rows = make_rows(cells=6, cycles=24)
    base = core.prepare_records(rows)
    altered = make_rows(cells=6, cycles=24)
    for row in altered:
        if row["cycle"] > 12 and row["cell_id"] == "cell_0":
            row["capacity"] = 9.0
    changed = core.prepare_records(altered)
    assert core.historical_feature(base["cell_0"], 12, 6) == core.historical_feature(changed["cell_0"], 12, 6)
    altered_cycle = make_rows(cells=6, cycles=24)
    altered_cycle[-1]["cycle"] = 240
    changed_cycle = core.prepare_records(altered_cycle)
    assert core.historical_feature(base["cell_0"], 12, 6) == core.historical_feature(changed_cycle["cell_0"], 12, 6)
    early_altered = make_rows(cells=6, cycles=24)
    for row in early_altered:
        if row["cycle"] > 6 and row["cell_id"] == "cell_0":
            row["capacity"] = 9.0
    early_changed = core.prepare_records(early_altered)
    assert core.historical_feature(base["cell_0"], 6, 6) == core.historical_feature(early_changed["cell_0"], 6, 6)


def test_grouped_evaluation_and_label_shuffle_sanity():
    report = core.evaluate(make_rows(cells=8, cycles=24), horizon=4, history_window=6, n_splits=4, bootstrap_reps=80, seed=7)
    assert report["scope"] == "TEST_ONLY"
    assert report["leakage_audit"]["max_cell_overlap"] == 0
    assert report["interval"]["coverage"] is not None
    assert report["interval"]["mean_width"] > 0
    assert report["label_shuffle_sanity"]["status"] == "PASS"
    assert report["bootstrap"]["unit"] == "cell_id"


def test_leave_condition_out_requires_condition_field():
    rows = make_rows(cells=6, cycles=16, with_conditions=False)
    report = core.evaluate(rows, horizon=3, history_window=5, n_splits=3, bootstrap_reps=40, seed=3, leave_condition_out=True)
    assert report["leave_condition_out"]["status"] == "ABSTAIN"


def test_cli_smoke_marks_fixture_and_writes_artifacts(tmp_path):
    input_csv = tmp_path / "input.csv"
    out_dir = tmp_path / "out"
    write_csv(input_csv, make_rows(cells=8, cycles=16))
    command = [sys.executable, "-m", "battery_real.cli", str(input_csv), "--out", str(out_dir), "--test-only", "--history-window", "5", "--horizon", "3", "--splits", "4"]
    result = subprocess.run(command, env={"PYTHONPATH": "code"}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert report["scope"] == "TEST_ONLY"
    assert (out_dir / "predictions.csv").exists()
    assert (out_dir / "metrics_by_cell.csv").exists()
    assert (out_dir / "metrics_by_condition.csv").exists()
