#!/usr/bin/env python3
"""Apply the source-repository RPT detrending rule to a canonical CSV.

The source code uses ``seasonal_decompose(..., period=50)`` and keeps the
trend component.  The resulting trend is retrospective: the two-sided
decomposition can use observations after the prediction landmark, so this
adapter deliberately marks its output as unsuitable for online prediction.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


METHOD = "seasonal_decompose.trend"
STATUS = "SOURCE_PERIOD50_RETROSPECTIVE"


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("输入 CSV 为空")
    required = {"cell_id", "cycle", "capacity"}
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"输入 CSV 缺少字段: {','.join(missing)}")
    return rows


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def preprocess_csv(
    input_csv: str | Path,
    output_csv: str | Path,
    *,
    period: int = 50,
    report_path: str | Path | None = None,
) -> dict[str, object]:
    if period < 2:
        raise ValueError("period 必须至少为 2")
    try:
        from statsmodels.tsa.seasonal import seasonal_decompose
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("RPT 预处理需要 statsmodels；请安装 requirements-study.txt") from exc

    rows = _load_rows(Path(input_csv))
    grouped: dict[str, list[tuple[int, int, dict[str, str]]]] = defaultdict(list)
    for index, row in enumerate(rows):
        try:
            cycle = int(float(row["cycle"]))
            capacity = float(row["capacity"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"第 {index + 2} 行 cycle/capacity 无法解析") from exc
        grouped[str(row["cell_id"])].append((cycle, index, row))
        row["capacity_raw"] = row["capacity"]
        row["_capacity_float"] = str(capacity)

    output = [dict(row) for row in rows]
    for cell_id, entries in grouped.items():
        entries.sort(key=lambda item: item[0])
        series = [float(item[2]["capacity"]) for item in entries]
        if len(series) < 2 * period:
            raise ValueError(f"{cell_id} 记录数 {len(series)} 小于 period={period} 所需的 {2 * period}")
        trend = seasonal_decompose(series, period=period, extrapolate_trend="freq").trend
        for (_, original_index, row), value in zip(entries, trend):
            if value != value:  # defensive NaN check; extrapolate_trend should fill edges
                raise ValueError(f"{cell_id} 的 period={period} 趋势包含 NaN")
            result = output[original_index]
            result["capacity"] = f"{float(value):.17g}"
            result["rpt_preprocessing"] = STATUS
            result["rpt_method"] = METHOD
            result["rpt_period"] = str(period)
            result["future_points_used"] = "true"
            result["prediction_eligible"] = "false"
            result.pop("_capacity_float", None)

    output.sort(key=lambda row: (str(row["cell_id"]), int(float(row["cycle"]))))
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_rows(output_path, output)
    report = {
        "status": "ANALYZED",
        "paper_eligible": False,
        "rpt_preprocessing": STATUS,
        "rpt_method": METHOD,
        "rpt_period": period,
        "future_points_used": True,
        "prediction_eligible": False,
        "n_cells": len(grouped),
        "n_rows": len(output),
        "input_csv": str(Path(input_csv).resolve()),
        "output_csv": str(output_path.resolve()),
    }
    if report_path is not None:
        report_file = Path(report_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--period", type=int, default=50)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    print(json.dumps(preprocess_csv(args.input_csv, args.output_csv, period=args.period, report_path=args.report), ensure_ascii=False))


if __name__ == "__main__":
    main()
