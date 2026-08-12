from __future__ import annotations

import csv
from pathlib import Path

import pytest

from technical.prepare_nmc_rpt import preprocess_csv


def _write_input(path: Path, cycles: int = 100) -> list[dict[str, str]]:
    rows = []
    for cell_id, offset in (("cell_a", 0.0), ("cell_b", 0.01)):
        for cycle in range(1, cycles + 1):
            seasonal = 0.08 if cycle % 50 == 0 else 0.0
            rows.append({
                "source_id": "zenodo_test",
                "chemistry": "NMC532",
                "cell_id": cell_id,
                "cycle": str(cycle),
                "capacity": str(1.0 + offset - 0.001 * cycle + seasonal),
                "condition_id": "P_TEST_NMC532_R1_1C_CC-CV",
            })
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def test_period50_preprocessing_preserves_cells_and_marks_retrospective(tmp_path):
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "output.csv"
    source_rows = _write_input(input_csv)

    pytest.importorskip("statsmodels")
    result = preprocess_csv(input_csv, output_csv, period=50)

    with output_csv.open(newline="", encoding="utf-8") as handle:
        output_rows = list(csv.DictReader(handle))
    assert len(output_rows) == len(source_rows)
    assert {row["cell_id"] for row in output_rows} == {"cell_a", "cell_b"}
    assert all(row["rpt_preprocessing"] == "SOURCE_PERIOD50_RETROSPECTIVE" for row in output_rows)
    assert all(row["rpt_method"] == "seasonal_decompose.trend" for row in output_rows)
    assert all(row["rpt_period"] == "50" for row in output_rows)
    assert all(row["future_points_used"] == "true" for row in output_rows)
    assert all(row["prediction_eligible"] == "false" for row in output_rows)
    assert any(float(row["capacity_raw"]) != float(row["capacity"]) for row in output_rows)
    assert result["n_cells"] == 2
    assert result["n_rows"] == len(source_rows)
    assert result["paper_eligible"] is False
