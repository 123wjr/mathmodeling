#!/usr/bin/env python3
"""Audit frozen study outputs for mechanism consistency and shortcut risk.

This is an argument-strengthening check, not a second model and not external
validation.  It uses only stdlib so it can run in the submission environment.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _marginals(raw: str) -> list[float]:
    return [float(item.split(":", 1)[1]) for item in raw.split(";") if ":" in item]


def _monotone(values: list[float]) -> dict[str, object]:
    deltas = [b - a for a, b in zip(values, values[1:])]
    return {
        "n_levels": len(values),
        "increasing": bool(deltas) and all(delta >= -1e-12 for delta in deltas),
        "min_adjacent_delta": min(deltas) if deltas else None,
        "max_adjacent_delta": max(deltas) if deltas else None,
    }


def build_argument(study_output: Path) -> dict[str, object]:
    effects = _read_csv(study_output / "q1_factor_effects.csv")
    mechanism: dict[str, dict[str, dict[str, object]]] = {}
    for row in effects:
        response = row["response"]
        factor = row["factor"]
        mechanism.setdefault(response, {})[factor] = {
            **_monotone(_marginals(row["marginal_means"])),
            "share_total_variance": float(row["share_total_variance"]),
            "normalized_main_effect_weight": float(row["normalized_main_effect_weight"]),
        }

    lco = _read_csv(study_output / "q2_leave_condition_out.csv")
    models = sorted({row["model"] for row in lco})
    summary: dict[str, dict[str, float | int | None]] = {}
    for model in models:
        rows = [row for row in lco if row["model"] == model]
        rmses = [float(row["rmse"]) for row in rows]
        summary[model] = {
            "n_conditions": len(rows),
            "mean_rmse": sum(rmses) / len(rmses),
            "worst_rmse": max(rmses),
            "best_rmse": min(rmses),
            "wins_vs_persistence": None,
        }
    persistence = {row["held_out_condition"]: float(row["rmse"]) for row in lco if row["model"] == "persistence"}
    for model in models:
        if model == "persistence":
            continue
        rows = [row for row in lco if row["model"] == model]
        summary[model]["wins_vs_persistence"] = sum(
            float(row["rmse"]) < persistence[row["held_out_condition"]] for row in rows
        )

    return {
        "status": "[RESULT][SYNTHETIC_ONLY]",
        "purpose": "Mechanism consistency and anti-shortcut audit; not external validation.",
        "source_files": ["q1_factor_effects.csv", "q2_leave_condition_out.csv"],
        "mechanism_monotonicity": mechanism,
        "leave_condition_out": summary,
        "interpretation": [
            "Monotone marginal means support consistency with the frozen generator over its 3x3x3 support, but do not identify real electrochemical causality.",
            "Condition-held-out metrics test interpolation across the frozen synthetic design; they are not independent-cell validation.",
            "A model winning against persistence is evidence of incremental signal in this simulation, not evidence of deployment accuracy.",
        ],
        "unknowns": [
            "External chemistry/protocol transfer remains untested until the independent V2 real-data package is accepted.",
            "No claim about safety probability, monetary benefit, or out-of-domain conditions is made.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-output", type=Path, default=Path("study_output"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    result = build_argument(args.study_output)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
