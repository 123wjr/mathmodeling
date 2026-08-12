#!/usr/bin/env python3
"""Prepare the public NMC aging-mode dataset into the V2 canonical long table.

The raw archive stays outside Git. This adapter only parses numeric cycle and
capacity fields, joins the public cell summary, and records unresolved units or
protocol semantics instead of guessing them.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

try:
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - only needed by the data CLI
    pd = None


SOURCE_ID = "zenodo_7250553"
DOI = "10.5281/zenodo.7250553"
LICENSE = "CC BY 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/legalcode"
DEFAULT_README_NAME = "nmc_readme.txt"


def _clean_header(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _number(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _c_rate(value: object) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*C", str(value), re.IGNORECASE)
    return float(match.group(1)) if match else None


def _chemistry(title: str) -> str:
    upper = title.upper()
    if "NMC532" in upper:
        return "NMC532"
    if "NMC811" in upper:
        return "NMC811"
    return "UNVERIFIED"


def _design(title: str) -> str:
    lower = title.lower()
    if "moderate" in lower:
        return "R2"
    if "low load" in lower:
        return "R1"
    return "UNVERIFIED"


def _summary_load_label(title: str) -> str:
    lower = title.lower()
    for label in ("high load", "moderate load", "low load"):
        if label in lower:
            return label
    return "UNVERIFIED"


def _summary_records(summary_path: Path) -> dict[tuple[str, int], dict]:
    if pd is None:
        raise RuntimeError("数据准备需要 pandas/openpyxl；请在 normal conda 环境运行")
    records: dict[tuple[str, int], dict] = {}
    workbook = pd.ExcelFile(summary_path)
    for sheet in workbook.sheet_names:
        raw = pd.read_excel(summary_path, sheet_name=sheet, header=None)
        title = str(raw.iloc[0, 1]) if raw.shape[0] and raw.shape[1] > 1 else sheet
        headers = [_clean_header(value) for value in raw.iloc[1].tolist()]
        table = raw.iloc[2:].copy()
        table.columns = headers
        table = table.dropna(axis=1, how="all")
        cell_column = next((column for column in table.columns if column.lower() == "cell number"), None)
        if cell_column is None:
            raise ValueError(f"{sheet}: missing Cell number column")
        table = table.dropna(subset=[cell_column])
        pack_match = re.search(r"P\d+", sheet.upper())
        if not pack_match:
            raise ValueError(f"无法从工作表解析 pack_id: {sheet}")
        pack_id = pack_match.group(0)
        for _, row in table.iterrows():
            cell_number = _number(row[cell_column])
            if cell_number is None or not cell_number.is_integer():
                raise ValueError(f"{sheet}: invalid cell number {row[cell_column]!r}")
            cell_number = int(cell_number)
            c_rate_raw = row.get("C-rate")
            eol_cycles = _number(row.get("End of life cycles"))
            record = {
                "pack_id": pack_id,
                "chemistry": _chemistry(title),
                "design": _design(title),
                "summary_load_label": _summary_load_label(title),
                "cell_number": cell_number,
                "c_rate_raw": "" if pd.isna(c_rate_raw) else str(c_rate_raw).strip(),
                "c_rate": _c_rate(c_rate_raw),
                "protocol": "" if pd.isna(row.get("Protocol")) else str(row.get("Protocol")).strip(),
                "eol_cycles": int(eol_cycles) if eol_cycles is not None and eol_cycles.is_integer() else None,
                "charge_voltage_V": _number(row.get("Charge Voltage (V)")),
                "major_aging_modes": "" if pd.isna(row.get("Major aging modes")) else str(row.get("Major aging modes")).strip(),
                "training_data_suggested": "" if pd.isna(row.get("Suggest to use in training data set")) else str(row.get("Suggest to use in training data set")).strip(),
                "lam_pe_pct": _number(row.get("%LAM_PE (experimental)")),
                "lam_pe_sd_pct": _number(row.get("% LAM_PE Standard deviation")),
                "summary_title": title,
            }
            key = (pack_id, cell_number)
            if key in records:
                raise ValueError(f"重复 summary key: {key}")
            records[key] = record
    return records


def _capacity_column(frame: pd.DataFrame, cycle_column: str) -> str:
    candidates = [
        column for column in frame.columns
        if column != cycle_column and not str(column).startswith("Unnamed")
    ]
    if len(candidates) != 1:
        raise ValueError(f"容量列无法唯一确定: columns={list(frame.columns)!r}")
    return str(candidates[0])


def _folder_metadata(folder: Path) -> tuple[str, str, str]:
    name = folder.name
    pack_match = re.match(r"(P\d+)", name.upper())
    if not pack_match:
        raise ValueError(f"无法从目录解析 pack_id: {name}")
    chemistry_match = re.search(r"(NMC532|NMC811)", name.upper())
    chemistry = chemistry_match.group(1) if chemistry_match else "UNVERIFIED"
    design = "R2" if "_R2" in name.upper() else "R1" if "_R1" in name.upper() else "UNVERIFIED"
    return pack_match.group(1), chemistry, design


def prepare(raw_root: Path, summary_path: Path) -> tuple[list[dict], list[dict], dict]:
    if pd is None:
        raise RuntimeError("数据准备需要 pandas/openpyxl；请在 normal conda 环境运行")
    summaries = _summary_records(summary_path)
    rows: list[dict] = []
    metadata: list[dict] = []
    quality = {
        "status": "CANDIDATE_REAL_DATA_UNVERIFIED_UNITS",
        "source_id": SOURCE_ID,
        "doi": DOI,
        "license": LICENSE,
        "capacity_unit": "UNVERIFIED",
        "cycle_semantics": "cycle index from source capacity CSV; EFC not inferred",
        "raw_preservation": "numeric parsing only; no detrending or outlier deletion",
        "n_capacity_files": 0,
        "n_cells": 0,
        "n_rows": 0,
        "summary_matches": 0,
        "summary_missing": [],
        "summary_eol_mismatches": [],
        "design_label_mismatches": [],
        "cycle_gaps": [],
        "nonpositive_or_missing_capacity": [],
        "by_folder": {},
    }
    for capacity_path in sorted(raw_root.rglob("Capacity_*.csv")):
        pack_id, folder_chemistry, folder_design = _folder_metadata(capacity_path.parent)
        cell_match = re.search(r"Cell(\d+)", capacity_path.stem, re.IGNORECASE)
        if not cell_match:
            raise ValueError(f"无法从文件解析 cell number: {capacity_path}")
        cell_number = int(cell_match.group(1))
        summary = summaries.get((pack_id, cell_number))
        cell_id = f"{pack_id}_Cell{cell_number:02d}"
        if summary is None:
            quality["summary_missing"].append(cell_id)
            summary = {
                "pack_id": pack_id,
                "chemistry": folder_chemistry,
                "design": folder_design,
                "summary_load_label": "UNVERIFIED",
                "cell_number": cell_number,
                "c_rate_raw": "",
                "c_rate": None,
                "protocol": "",
                "eol_cycles": None,
                "charge_voltage_V": None,
                "major_aging_modes": "",
                "training_data_suggested": "",
                "lam_pe_pct": None,
                "lam_pe_sd_pct": None,
                "summary_title": "UNVERIFIED",
            }
        else:
            quality["summary_matches"] += 1
        if summary["chemistry"] != folder_chemistry and folder_chemistry != "UNVERIFIED":
            raise ValueError(f"化学体系元数据冲突: {capacity_path.parent.name} vs summary {summary['summary_title']}")
        if summary["design"] != folder_design and summary["design"] != "UNVERIFIED":
            quality["design_label_mismatches"].append({
                "cell_id": cell_id,
                "folder_design": folder_design,
                "summary_design": summary["design"],
                "summary_load_label": summary["summary_load_label"],
            })
        frame = pd.read_csv(capacity_path)
        cycle_column = "Cycle" if "Cycle" in frame.columns else "CycleReorder" if "CycleReorder" in frame.columns else None
        if cycle_column is None:
            raise ValueError(f"缺少 Cycle/CycleReorder: {capacity_path}")
        value_column = _capacity_column(frame, cycle_column)
        cycles = pd.to_numeric(frame[cycle_column], errors="coerce")
        capacities = pd.to_numeric(frame[value_column], errors="coerce")
        if cycles.isna().any() or capacities.isna().any():
            quality["nonpositive_or_missing_capacity"].append(cell_id)
        cycle_values = [int(value) for value in cycles.dropna() if float(value).is_integer()]
        expected = list(range(1, len(cycle_values) + 1))
        if cycle_values != expected:
            quality["cycle_gaps"].append({"cell_id": cell_id, "first": cycle_values[:3], "last": cycle_values[-3:]})
        max_cycle = max(cycle_values) if cycle_values else None
        if summary["eol_cycles"] is not None and max_cycle != summary["eol_cycles"]:
            quality["summary_eol_mismatches"].append({"cell_id": cell_id, "csv_max_cycle": max_cycle, "summary_eol_cycles": summary["eol_cycles"]})
        condition_id = f"{pack_id}_{folder_chemistry}_{folder_design}_{summary['c_rate_raw'] or 'UNVERIFIED'}_{summary['protocol'] or 'UNVERIFIED'}"
        for cycle, capacity in zip(cycles, capacities):
            if pd.isna(cycle) or pd.isna(capacity):
                continue
            cycle_int = int(cycle)
            capacity_float = float(capacity)
            if capacity_float <= 0:
                quality["nonpositive_or_missing_capacity"].append(cell_id)
            rows.append({
                "source_id": SOURCE_ID,
                "chemistry": summary["chemistry"],
                "cell_id": cell_id,
                "cycle": cycle_int,
                "capacity": capacity_float,
                "capacity_unit": "UNVERIFIED",
                "capacity_unit_status": "UNVERIFIED",
                "capacity_source_column": value_column,
                "efc": "",
                "resistance": "",
                "temperature": "",
                "c_rate": "" if summary["c_rate"] is None else summary["c_rate"],
                "dod": "",
                "protocol": summary["protocol"],
                "condition_id": condition_id,
                "pack_id": pack_id,
                "design": folder_design if summary["design"] == "UNVERIFIED" or folder_design == summary["design"] else "UNVERIFIED",
                "design_folder_label": folder_design,
                "summary_load_label": summary["summary_load_label"],
                "summary_eol_cycles": "" if summary["eol_cycles"] is None else summary["eol_cycles"],
                "condition_fields": "pack_id,chemistry,design,c_rate,protocol",
                "rpt_preprocessing": "RAW_UNPROCESSED",
                "rpt_method": "none",
                "rpt_period": "",
                "future_points_used": "false",
                "prediction_eligible": "false",
            })
        metadata.append({
            "source_id": SOURCE_ID,
            "cell_id": cell_id,
            "pack_id": pack_id,
            "chemistry": summary["chemistry"],
            "design": folder_design if summary["design"] == "UNVERIFIED" or folder_design == summary["design"] else "UNVERIFIED",
            "design_folder_label": folder_design,
            "summary_load_label": summary["summary_load_label"],
            "c_rate_raw": summary["c_rate_raw"],
            "c_rate": "" if summary["c_rate"] is None else summary["c_rate"],
            "protocol": summary["protocol"],
            "summary_eol_cycles": "" if summary["eol_cycles"] is None else summary["eol_cycles"],
            "csv_max_cycle": "" if max_cycle is None else max_cycle,
            "charge_voltage_V": "" if summary["charge_voltage_V"] is None else summary["charge_voltage_V"],
            "major_aging_modes": summary["major_aging_modes"],
            "training_data_suggested": summary["training_data_suggested"],
            "lam_pe_pct": "" if summary["lam_pe_pct"] is None else summary["lam_pe_pct"],
            "lam_pe_sd_pct": "" if summary["lam_pe_sd_pct"] is None else summary["lam_pe_sd_pct"],
            "capacity_unit": "UNVERIFIED",
            "capacity_source_column": value_column,
            "raw_file": str(capacity_path.relative_to(raw_root)),
            "condition_fields": "pack_id,chemistry,design,c_rate,protocol",
            "rpt_preprocessing": "RAW_UNPROCESSED",
            "prediction_eligible": "false",
        })
        folder_quality = quality["by_folder"].setdefault(capacity_path.parent.name, {"n_cells": 0, "n_rows": 0})
        folder_quality["n_cells"] += 1
        folder_quality["n_rows"] += len(frame)
    quality["n_capacity_files"] = len(metadata)
    quality["n_cells"] = len({row["cell_id"] for row in metadata})
    quality["n_rows"] = len(rows)
    quality["summary_missing"] = sorted(set(quality["summary_missing"]))
    quality["cycle_gaps"] = sorted(quality["cycle_gaps"], key=lambda item: item["cell_id"])
    quality["nonpositive_or_missing_capacity"] = sorted(set(quality["nonpositive_or_missing_capacity"]))
    quality["summary_eol_mismatches"] = sorted(quality["summary_eol_mismatches"], key=lambda item: item["cell_id"])
    quality["design_label_mismatches"] = sorted(quality["design_label_mismatches"], key=lambda item: item["cell_id"])
    quality["chemistry_counts"] = dict(Counter(row["chemistry"] for row in metadata))
    quality["c_rate_counts"] = dict(Counter(row["c_rate_raw"] for row in metadata))
    quality["protocol_counts"] = dict(Counter(row["protocol"] for row in metadata))
    return rows, metadata, quality


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_chemistry_csvs(out_dir: Path, rows: list[dict]) -> dict[str, Path]:
    paths = {}
    for chemistry in sorted({row["chemistry"] for row in rows}):
        path = out_dir / f"canonical_capacity_{chemistry}.csv"
        _write_csv(path, [row for row in rows if row["chemistry"] == chemistry])
        paths[chemistry] = path
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True, help="extracted Battery raw data directory")
    parser.add_argument("--summary", type=Path, required=True, help="Pouch cell_summary.xlsx")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--raw-zip", type=Path, default=None)
    parser.add_argument("--readme", type=Path, default=None)
    args = parser.parse_args()
    rows, metadata, quality = prepare(args.raw_root, args.summary)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(args.out_dir / "canonical_capacity.csv", rows)
    chemistry_paths = _write_chemistry_csvs(args.out_dir, rows)
    _write_csv(args.out_dir / "cell_metadata.csv", metadata)
    provenance = {
        "source_id": SOURCE_ID,
        "title": "Battery-aging-modes-across-NMC",
        "doi": DOI,
        "record_url": "https://zenodo.org/records/7250553",
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "related_code": "https://github.com/hypochen/Battery-aging-modes-across-NMC",
        "inputs": {
            "raw_root": str(args.raw_root.resolve()),
            "summary": {"path": str(args.summary.resolve()), "sha256": _sha256(args.summary)},
        },
        "raw_archive": None if args.raw_zip is None else {"path": str(args.raw_zip.resolve()), "sha256": _sha256(args.raw_zip)},
        "readme": None if args.readme is None else {"path": str(args.readme.resolve()), "sha256": _sha256(args.readme)},
        "output_scope": "candidate real-data preparation only; not V1 training or paper result",
        "condition_fields": ["pack_id", "chemistry", "design", "c_rate", "protocol"],
        "rpt_provenance": {
            "rpt_preprocessing": "RAW_UNPROCESSED",
            "rpt_method": "none",
            "rpt_period": None,
            "future_points_used": False,
            "prediction_eligible": False,
        },
    }
    (args.out_dir / "quality_report.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "out_dir": str(args.out_dir),
        "chemistry_files": {key: str(path) for key, path in chemistry_paths.items()},
        **{key: quality[key] for key in ("n_capacity_files", "n_cells", "n_rows", "summary_matches")},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
