"""确定性输出、统计指标与哈希工具。"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os

import numpy as np


def write_csv(path: str, rows: list[dict], fieldnames: list[str] | None = None) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows and not fieldnames:
        raise ValueError("空 CSV 必须显式提供 fieldnames")
    columns = fieldnames or list(rows[0])
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_json(path: str, value) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return path


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    truth = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    if truth.size == 0 or truth.shape != pred.shape:
        raise ValueError("指标输入为空或形状不一致")
    residual = truth - pred
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(residual**2)))
    denominator = float(np.sum((truth - np.mean(truth)) ** 2))
    r2 = float(1.0 - np.sum(residual**2) / denominator) if denominator > 0 else math.nan
    return {"mae": mae, "rmse": rmse, "r2": r2}


def grouped_bootstrap_interval(
    records: list[dict],
    truth_key: str,
    pred_key: str,
    group_key: str,
    repetitions: int,
    confidence: float,
    seed: int,
) -> dict[str, tuple[float, float]]:
    groups = sorted({str(row[group_key]) for row in records})
    by_group = {group: [row for row in records if str(row[group_key]) == group] for group in groups}
    rng = np.random.default_rng(seed)
    draws = {"mae": [], "rmse": [], "r2": []}
    for _ in range(repetitions):
        sampled = rng.choice(groups, size=len(groups), replace=True)
        rows = [row for group in sampled for row in by_group[str(group)]]
        metrics = regression_metrics(
            [row[truth_key] for row in rows],
            [row[pred_key] for row in rows],
        )
        for name, value in metrics.items():
            if math.isfinite(value):
                draws[name].append(value)
    alpha = (1.0 - confidence) / 2.0
    return {
        name: (
            float(np.quantile(values, alpha)),
            float(np.quantile(values, 1.0 - alpha)),
        )
        for name, values in draws.items()
        if values
    }


def minmax(values: list[float]) -> list[float]:
    array = np.asarray(values, dtype=float)
    low, high = float(np.min(array)), float(np.max(array))
    if math.isclose(low, high):
        return [0.5] * len(values)
    return ((array - low) / (high - low)).tolist()
