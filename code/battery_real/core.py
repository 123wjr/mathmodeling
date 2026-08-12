"""Source-neutral measured-data validation for the battery study.

The module intentionally has no dataset-specific knowledge.  A source adapter
must produce the canonical records described in the handoff document before
this code is called.
"""
from __future__ import annotations

import csv
import math
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import theilslopes
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from battery_study import common as study_common

REQUIRED_COLUMNS = ("source_id", "chemistry", "cell_id", "cycle", "capacity")
OPTIONAL_COLUMNS = (
    "efc", "resistance", "temperature", "c_rate", "dod", "protocol", "condition_id"
)
METADATA_COLUMNS = ("rpt_preprocessing", "rpt_method", "rpt_period", "future_points_used", "prediction_eligible")
_POSITIVE_OPTIONALS = {"efc", "resistance", "c_rate"}
_FEATURE_BASE = ("capacity_norm", "slope_cycle", "progress")
_FEATURE_OPTIONALS = ("temperature", "c_rate", "dod")


def _float(value, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须为数值") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} 必须为有限值")
    return result


def validate_records(rows: list[dict]) -> list[dict]:
    """Validate canonical rows and return shallow copies with normalized types."""
    if not rows:
        raise ValueError("输入记录为空")
    missing = sorted(set(REQUIRED_COLUMNS) - set(rows[0]))
    if missing:
        raise ValueError(f"缺少必需字段: {','.join(missing)}")
    output = []
    seen_keys = set()
    cell_sources = {}
    chemistries = set()
    previous_cycle = {}
    previous_efc = {}
    metadata = {name: str(rows[0].get(name, "")).strip() for name in METADATA_COLUMNS}
    for name, value in metadata.items():
        if not value:
            metadata[name] = {
                "rpt_preprocessing": "UNKNOWN",
                "rpt_method": "UNKNOWN",
                "rpt_period": "",
                "future_points_used": "unknown",
                "prediction_eligible": "unknown",
            }[name]
    for index, original in enumerate(rows):
        missing = sorted(set(REQUIRED_COLUMNS) - set(original))
        if missing:
            raise ValueError(f"第 {index + 1} 行缺少必需字段: {','.join(missing)}")
        row = dict(original)
        for name in METADATA_COLUMNS:
            value = str(row.get(name, metadata[name])).strip()
            if value != metadata[name]:
                raise ValueError(f"{name} 必须在一次运行内保持一致")
            row[name] = metadata[name]
        for key in ("source_id", "chemistry", "cell_id"):
            value = str(row.get(key, "")).strip()
            if not value:
                raise ValueError(f"{key} 不能为空")
            row[key] = value
        source, cell = row["source_id"], row["cell_id"]
        chemistry = row["chemistry"]
        chemistries.add(chemistry)
        if cell in cell_sources and cell_sources[cell] != source:
            raise ValueError(f"cell_id 在多个 source_id 中重复: {cell}")
        cell_sources[cell] = source
        cycle_value = _float(row["cycle"], "cycle")
        if cycle_value <= 0 or not cycle_value.is_integer():
            raise ValueError("cycle 必须为正整数")
        cycle = int(cycle_value)
        row["cycle"] = cycle
        capacity = _float(row["capacity"], "capacity")
        if capacity <= 0:
            raise ValueError("capacity 必须为正")
        row["capacity"] = capacity
        key = (source, cell, cycle)
        if key in seen_keys:
            raise ValueError(f"重复键: {key}")
        if cell in previous_cycle and cycle <= previous_cycle[cell]:
            raise ValueError(f"{cell} 的 cycle 不单调递增")
        seen_keys.add(key)
        previous_cycle[cell] = cycle
        for name in OPTIONAL_COLUMNS:
            if name not in row or row[name] in (None, ""):
                row[name] = None
                continue
            if name in ("protocol", "condition_id"):
                row[name] = str(row[name]).strip() or None
                continue
            value = _float(row[name], name)
            if name in _POSITIVE_OPTIONALS and value <= 0:
                raise ValueError(f"{name} 必须为正")
            if name == "dod" and not 0 < value <= 100:
                raise ValueError("dod 必须在 (0,100] 内")
            row[name] = value
        if row["efc"] is not None and cell in previous_efc and row["efc"] < previous_efc[cell]:
            raise ValueError(f"{cell} 的 efc 不单调递增")
        if row["efc"] is not None:
            previous_efc[cell] = row["efc"]
        output.append(row)
    if len(chemistries) != 1:
        raise ValueError(f"一次运行禁止混合化学体系: {sorted(chemistries)}")
    return output


def load_csv(path: str | os.PathLike) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return validate_records(list(csv.DictReader(handle)))


def prepare_records(rows: list[dict]) -> dict[str, list[dict]]:
    """Sort validated rows and add fixed early-window capacity normalization."""
    checked = validate_records(rows)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in checked:
        grouped[row["cell_id"]].append(row)
    prepared = {}
    for cell_id, records in sorted(grouped.items()):
        records.sort(key=lambda item: item["cycle"])
        baseline = float(np.median([row["capacity"] for row in records[: min(10, len(records))]]))
        if baseline <= 0 or not math.isfinite(baseline):
            raise ValueError(f"{cell_id} 的初始容量无效")
        for row in records:
            row["capacity_norm"] = row["capacity"] / baseline
            row["x_axis"] = row["efc"] if row["efc"] is not None else float(row["cycle"])
        prepared[cell_id] = records
    return prepared


def _robust_slope(x, y) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.allclose(x, x[0]):
        return 0.0
    return float(theilslopes(y, x).slope)


def _hinge(records: list[dict], knee_min_points: int) -> tuple[float | None, float | None, float | None]:
    if len(records) < knee_min_points * 2:
        return None, None, None
    x = np.asarray([row["x_axis"] for row in records], dtype=float)
    y = np.asarray([row["capacity_norm"] for row in records], dtype=float)
    candidates = range(knee_min_points - 1, len(records) - knee_min_points + 1)
    best = None
    for index in candidates:
        knot = float(x[index])
        z = np.column_stack([np.ones(len(x)), x, np.maximum(0.0, x - knot)])
        coef, *_ = np.linalg.lstsq(z, y, rcond=None)
        residual = y - z @ coef
        score = float(residual @ residual)
        if best is None or score < best[0]:
            best = score, knot, float(coef[1]), float(coef[1] + coef[2])
    if best is None:
        return None, None, None
    _, knot, before, after = best
    # A knee is only supported when the post-knee slope is meaningfully steeper.
    if not (after < before - max(1e-5, 0.10 * abs(before))):
        return None, before, after
    return knot, before, after


def analyze_cell(records: list[dict], knee_min_points: int = 10, endpoint_soh: float = 0.8) -> dict:
    if not records:
        raise ValueError("电芯记录为空")
    x = np.asarray([row["x_axis"] for row in records], dtype=float)
    y = np.asarray([row["capacity_norm"] for row in records], dtype=float)
    trend = _robust_slope(x, y)
    knee, before, after = _hinge(records, knee_min_points)
    endpoint_reached = float(y[-1]) <= endpoint_soh
    if knee is not None:
        status = "DETECTED"
    elif not endpoint_reached:
        status = "RIGHT_CENSORED"
    else:
        status = "NOT_DETECTED"
    return {
        "cell_id": records[0]["cell_id"],
        "source_id": records[0]["source_id"],
        "chemistry": records[0]["chemistry"],
        "n_cycles": len(records),
        "final_capacity_norm": float(y[-1]),
        "trend_slope": trend,
        "knee_status": status,
        "knee_x": knee,
        "slope_before": before,
        "slope_after": after,
        "endpoint_soh": endpoint_soh,
        "endpoint_reached": endpoint_reached,
    }


def factor_analysis(grouped: dict[str, list[dict]], factor: str, response: str = "capacity_norm") -> dict:
    common_cycles = set.intersection(*({row["cycle"] for row in records} for records in grouped.values()))
    if not common_cycles:
        return {"factor": factor, "status": "ABSTAIN", "reason": "电芯之间没有共同 cycle"}
    comparison_cycle = max(common_cycles)
    values = {}
    for cell_id, records in grouped.items():
        observed = [row.get(factor) for row in records]
        if not observed or any(value is None for value in observed):
            return {"factor": factor, "status": "ABSTAIN", "reason": f"{factor} 缺失"}
        if len(set(observed)) != 1:
            return {"factor": factor, "status": "ABSTAIN", "reason": f"{factor} 在单电芯内不恒定"}
        comparison = next(row for row in records if row["cycle"] == comparison_cycle)
        values[cell_id] = (observed[0], float(comparison[response]))
    by_level = defaultdict(list)
    for level, response_value in values.values():
        by_level[str(level)].append(response_value)
    if len(by_level) < 2:
        return {"factor": factor, "status": "ABSTAIN", "reason": f"levels={len(by_level)}，不足两个水平"}
    if min(map(len, by_level.values())) < 2:
        return {"factor": factor, "status": "ABSTAIN", "reason": "每个水平缺少电芯 replication"}
    means = {level: float(np.mean(vals)) for level, vals in sorted(by_level.items())}
    return {
        "factor": factor,
        "status": "PASS_DESCRIPTIVE",
        "causal": False,
        "n_cells": len(values),
        "comparison_cycle": comparison_cycle,
        "levels": means,
        "effect_range": max(means.values()) - min(means.values()),
    }


def historical_feature(records: list[dict], landmark_cycle: int, history_window: int) -> dict:
    history = [row for row in records if row["cycle"] <= landmark_cycle]
    if len(history) < history_window:
        raise ValueError("历史窗口不足")
    recent = history[-history_window:]
    baseline = float(np.median([row["capacity"] for row in history[: min(10, len(history))]]))
    normalized_recent = [row["capacity"] / baseline for row in recent]
    slope = _robust_slope([row["cycle"] for row in recent], normalized_recent)
    current = recent[-1]
    result = {
        "cell_id": current["cell_id"],
        "condition_id": current.get("condition_id"),
        "condition_fields": current.get("condition_fields"),
        "cycle": int(current["cycle"]),
        "capacity_norm": float(current["capacity"] / baseline),
        "slope_cycle": slope,
        # Do not normalize by the final observed cycle: that would read the
        # future record count/length while constructing a historical feature.
        "progress": float(current["cycle"]),
        "temperature": current.get("temperature"),
        "c_rate": current.get("c_rate"),
        "dod": current.get("dod"),
    }
    return result


def _feature_names(samples: list[dict]) -> tuple[str, ...]:
    names = list(_FEATURE_BASE)
    for name in _FEATURE_OPTIONALS:
        if all(row.get(name) is not None and math.isfinite(float(row[name])) for row in samples):
            names.append(name)
    return tuple(names)


def _matrix(samples: list[dict], names: tuple[str, ...]) -> np.ndarray:
    return np.asarray([[float(row[name]) for name in names] for row in samples], dtype=float)


def _samples(grouped: dict[str, list[dict]], horizon: int, history_window: int) -> list[dict]:
    result = []
    for cell_id, records in grouped.items():
        by_cycle = {row["cycle"]: row for row in records}
        for index in range(history_window - 1, len(records)):
            target_record = by_cycle.get(records[index]["cycle"] + horizon)
            if target_record is None:
                continue
            feature = historical_feature(records, records[index]["cycle"], history_window)
            baseline = float(np.median([row["capacity"] for row in records[: min(10, index + 1)]]))
            target = target_record["capacity"] / baseline
            result.append({**feature, "target": float(target), "target_cycle": int(target_record["cycle"])})
    return result


def _metrics(records: list[dict], truth="target", pred="prediction") -> dict:
    if not records:
        return {"status": "ABSTAIN", "n": 0, "reason": "没有可评分记录"}
    values = study_common.regression_metrics([row[truth] for row in records], [row[pred] for row in records])
    if not math.isfinite(values["r2"]):
        values["r2"] = None
    return {"status": "PASS", "n": len(records), **values}


def _cell_bootstrap(records: list[dict], truth: str, pred: str, reps: int, confidence: float, seed: int) -> dict:
    if not records:
        return {"status": "ABSTAIN", "unit": "cell_id", "reason": "没有记录"}
    cells = sorted({row["cell_id"] for row in records})
    if len(cells) < 3:
        return {"status": "ABSTAIN", "unit": "cell_id", "reason": "电芯数少于 3"}
    by_cell = {cell: [row for row in records if row["cell_id"] == cell] for cell in cells}
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(reps):
        selected = rng.choice(cells, len(cells), replace=True)
        sampled = [row for cell in selected for row in by_cell[str(cell)]]
        draws.append(study_common.regression_metrics(
            [row[truth] for row in sampled], [row[pred] for row in sampled]))
    alpha = (1 - confidence) / 2
    r2_values = [d["r2"] for d in draws]
    r2_ci = (
        [float(np.quantile(r2_values, alpha)), float(np.quantile(r2_values, 1 - alpha))]
        if all(math.isfinite(value) for value in r2_values) else None
    )
    return {
        "status": "PASS",
        "unit": "cell_id",
        "n_cells": len(cells),
        "repetitions": reps,
        "confidence": confidence,
        "mae_ci": [float(np.quantile([d["mae"] for d in draws], alpha)), float(np.quantile([d["mae"] for d in draws], 1 - alpha))],
        "rmse_ci": [float(np.quantile([d["rmse"] for d in draws], alpha)), float(np.quantile([d["rmse"] for d in draws], 1 - alpha))],
        "r2_ci": r2_ci,
    }


def _fit_ridge(x_train, y_train, x_pred):
    model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
    model.fit(x_train, y_train)
    return model.predict(x_pred), model


def _condition_eval(samples, names, n_splits, seed):
    conditions = [row.get("condition_id") for row in samples]
    if any(value in (None, "") for value in conditions) or len(set(conditions)) < 2:
        return {"status": "ABSTAIN", "reason": "condition_id 缺失或不足两个水平"}
    rows = []
    raw_fields = next((str(row.get("condition_fields", "")).strip() for row in samples if str(row.get("condition_fields", "")).strip()), "")
    condition_fields = [field.strip() for field in raw_fields.split(",") if field.strip()] or ["pack_id", "chemistry", "design", "c_rate", "protocol"]
    condition_cells = {
        str(condition): sorted({samples[i]["cell_id"] for i, value in enumerate(conditions) if value == condition})
        for condition in sorted(set(conditions))
    }
    for held_out in sorted(set(conditions)):
        train = [i for i, value in enumerate(conditions) if value != held_out]
        test = [i for i, value in enumerate(conditions) if value == held_out]
        train_cells = {samples[i]["cell_id"] for i in train}
        test_cells = {samples[i]["cell_id"] for i in test}
        overlap = train_cells & test_cells
        if overlap:
            return {"status": "ABSTAIN", "reason": f"condition_id 与 cell_id 交叉，无法保持 LOCO 电芯隔离: {sorted(overlap)[:3]}"}
        pred, _ = _fit_ridge(_matrix([samples[i] for i in train], names), np.asarray([samples[i]["target"] for i in train]), _matrix([samples[i] for i in test], names))
        rows.extend({**samples[i], "model": "ridge", "prediction": float(pred[j]), "split": f"LOCO:{held_out}"} for j, i in enumerate(test))
    return {
        "status": "PASS",
        "n_folds": len(set(conditions)),
        "condition_definition": {
            "fields": condition_fields,
            "source_adapter_field": "condition_id",
            "interpretation": "复合实验层留出，不等同单因素或普遍工况泛化",
            "cells_per_condition": {key: len(value) for key, value in condition_cells.items()},
            "condition_cells": condition_cells,
        },
        "metrics": _metrics(rows),
        "rows": rows,
    }


def evaluate(rows: list[dict], *, horizon: int = 10, history_window: int = 20, n_splits: int = 5, bootstrap_reps: int = 300, seed: int = 20260812, leave_condition_out: bool = False, test_only: bool | None = None) -> dict:
    if horizon < 1 or history_window < 2 or n_splits < 2 or bootstrap_reps < 1:
        raise ValueError("horizon/history_window/n_splits/bootstrap_reps 参数无效")
    grouped = prepare_records(rows)
    samples = _samples(grouped, horizon, history_window)
    if not samples:
        return {"scope": "ABSTAIN", "status": "ABSTAIN", "run_status": "ABSTAIN", "evidence_status": "ABSTAIN", "paper_eligible": False, "reason": "没有足够历史/未来记录"}
    cells = sorted(grouped)
    if len(cells) < n_splits:
        return {"scope": "ABSTAIN", "status": "ABSTAIN", "run_status": "ABSTAIN", "evidence_status": "ABSTAIN", "paper_eligible": False, "reason": f"电芯数 {len(cells)} 小于分组折数 {n_splits}"}
    names = _feature_names(samples)
    x = _matrix(samples, names)
    y = np.asarray([row["target"] for row in samples], dtype=float)
    groups = np.asarray([row["cell_id"] for row in samples])
    splitter = GroupKFold(n_splits=n_splits)
    predictions = []
    audit = []
    sanity_rows = []
    calibration_cells_per_fold = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(x, y, groups), 1):
        train_cells = sorted(set(groups[train_idx]))
        test_cells = sorted(set(groups[test_idx]))
        overlap = sorted(set(train_cells) & set(test_cells))
        if overlap:
            raise AssertionError(f"训练/测试电芯泄漏: {overlap[:3]}")
        audit.append({"split": f"GroupKFold:{fold}", "train_cells": train_cells, "test_cells": test_cells, "cell_overlap": overlap})
        train_x, test_x = x[train_idx], x[test_idx]
        train_y, test_y = y[train_idx], y[test_idx]
        # Calibrate on whole cells disjoint from the proper training fit.
        train_cell_order = np.asarray(train_cells)
        rng = np.random.default_rng(seed + fold)
        rng.shuffle(train_cell_order)
        calibration_count = max(1, len(train_cell_order) // 3) if len(train_cell_order) >= 2 else 0
        calibration_cells = set(train_cell_order[:calibration_count])
        proper_cells = set(train_cell_order[calibration_count:])
        calibration_cells_per_fold.append(len(calibration_cells))
        radius = None
        prediction_model = None
        if proper_cells and calibration_cells:
            proper_idx = np.flatnonzero(np.isin(groups[train_idx], list(proper_cells)))
            cal_idx = np.flatnonzero(np.isin(groups[train_idx], list(calibration_cells)))
            _, calibration_model = _fit_ridge(train_x[proper_idx], train_y[proper_idx], train_x[cal_idx])
            cal_pred = calibration_model.predict(train_x[cal_idx])
            calibration_group_ids = groups[train_idx][cal_idx]
            cell_residuals = [
                float(np.max(np.abs(train_y[cal_idx][calibration_group_ids == cell] - cal_pred[calibration_group_ids == cell])))
                for cell in sorted(set(calibration_group_ids))
            ]
            q = min(1.0, math.ceil((len(cell_residuals) + 1) * 0.90) / len(cell_residuals))
            radius = float(np.quantile(cell_residuals, q, method="higher"))
            prediction_model = calibration_model
        else:
            prediction_model = _fit_ridge(train_x, train_y, test_x)[1]
        ridge_pred = prediction_model.predict(test_x)
        shuffled_y = train_y[proper_idx].copy() if proper_cells and calibration_cells else train_y.copy()
        np.random.default_rng(seed + 1000 + fold).shuffle(shuffled_y)
        shuffled_pred, _ = _fit_ridge(train_x[proper_idx], shuffled_y, test_x) if proper_cells and calibration_cells else _fit_ridge(train_x, shuffled_y, test_x)
        sanity_rows.append({"normal_rmse": float(np.sqrt(np.mean((test_y - ridge_pred) ** 2))), "shuffled_rmse": float(np.sqrt(np.mean((test_y - shuffled_pred) ** 2)))})
        for j, sample_index in enumerate(test_idx):
            sample = samples[sample_index]
            current = float(sample["capacity_norm"])
            local = current + float(sample["slope_cycle"]) * horizon
            predictions.extend([
                {**sample, "model": "persistence", "prediction": current, "split": f"GroupKFold:{fold}"},
                {**sample, "model": "local_linear", "prediction": float(local), "split": f"GroupKFold:{fold}"},
                {**sample, "model": "ridge", "prediction": float(ridge_pred[j]), "interval_radius": radius, "split": f"GroupKFold:{fold}"},
            ])
    by_model = {}
    for model_name in ("persistence", "local_linear", "ridge"):
        model_rows = [row for row in predictions if row["model"] == model_name]
        by_model[model_name] = _metrics(model_rows)
        by_model[model_name]["bootstrap"] = _cell_bootstrap(model_rows, "target", "prediction", bootstrap_reps, 0.90, seed + len(model_name))
    ridge_rows = [row for row in predictions if row["model"] == "ridge"]
    interval_rows = [row for row in ridge_rows if row.get("interval_radius") is not None]
    if interval_rows:
        covered = [abs(row["target"] - row["prediction"]) <= row["interval_radius"] for row in interval_rows]
        covered_by_cell = defaultdict(list)
        for row, is_covered in zip(interval_rows, covered):
            covered_by_cell[row["cell_id"]].append(is_covered)
        width = float(np.mean([2 * row["interval_radius"] for row in interval_rows]))
        interval = {
            "status": "WARN",
            "envelope_type": "descriptive_training_cell_calibrated_residual_envelope",
            "calibration_quantile_target": 0.90,
            "coverage_unit": "prediction_row",
            "n_prediction_rows": len(interval_rows),
            "n_test_cells": len(covered_by_cell),
            "row_coverage": float(np.mean(covered)),
            "whole_cell_simultaneous_coverage": float(np.mean([all(values) for values in covered_by_cell.values()])),
            "calibration_cells_per_fold": calibration_cells_per_fold,
            "finite_sample_guarantee": False,
            "mean_width": width,
            "reason": "每折校准电芯过少；覆盖率仅作描述，不构成 90% 电芯级有限样本保证",
        }
    else:
        interval = {
            "status": "ABSTAIN",
            "envelope_type": "descriptive_training_cell_calibrated_residual_envelope",
            "calibration_quantile_target": 0.90,
            "coverage_unit": "prediction_row",
            "n_prediction_rows": 0,
            "n_test_cells": 0,
            "row_coverage": None,
            "whole_cell_simultaneous_coverage": None,
            "calibration_cells_per_fold": calibration_cells_per_fold,
            "finite_sample_guarantee": False,
            "mean_width": None,
            "reason": "没有独立校准电芯",
        }
    cell_metrics = []
    condition_metrics = []
    for key, group_key in ((cell_metrics, "cell_id"), (condition_metrics, "condition_id")):
        grouped_rows = defaultdict(list)
        for row in ridge_rows:
            grouped_rows[row.get(group_key)].append(row)
        for value, group_rows in sorted(grouped_rows.items(), key=lambda item: str(item[0])):
            key.append({group_key: value, **_metrics(group_rows)})
    sanity_rmse = float(np.mean([row["normal_rmse"] for row in sanity_rows]))
    shuffled_rmse = float(np.mean([row["shuffled_rmse"] for row in sanity_rows]))
    if test_only is True:
        scope = "TEST_ONLY"
    elif test_only is False:
        scope = "REAL_DATA_CANDIDATE"
    else:
        scope = "TEST_ONLY" if all(str(row["source_id"]).startswith("TEST_ONLY") for row in rows) else "REAL_DATA_CANDIDATE"
    metadata_rows = [record for records in grouped.values() for record in records]
    preprocessing = {
        name: next(iter({row.get(name) for row in metadata_rows}), None)
        for name in METADATA_COLUMNS
    }
    if preprocessing["rpt_preprocessing"] == "RAW_UNPROCESSED":
        q1_status = "HOLD_RPT_SENSITIVITY"
        q1_reason = "原始容量含来源报告的 RPT 尖峰；需与 period=50 回顾性口径并列"
    elif preprocessing["rpt_preprocessing"] == "SOURCE_PERIOD50_RETROSPECTIVE":
        q1_status = "HOLD_RPT_SENSITIVITY"
        q1_reason = "period=50 双侧趋势使用未来观测，仅作回顾性敏感性，不能作为在线预测预处理"
    else:
        q1_status = "HOLD_PREPROCESSING_UNVERIFIED"
        q1_reason = "输入未提供可核验的 RPT 预处理状态"
    if test_only is True:
        evidence_status = "TEST_ONLY"
    elif preprocessing["rpt_preprocessing"] == "UNKNOWN":
        evidence_status = "HOLD_PREPROCESSING_UNVERIFIED"
    elif scope == "TEST_ONLY":
        evidence_status = "TEST_ONLY"
    else:
        evidence_status = q1_status
    future_points = str(preprocessing["future_points_used"]).strip().lower()
    preprocessing_future_points_used = True if future_points in {"true", "1", "yes"} else False if future_points in {"false", "0", "no"} else None
    condition_fields_raw = next((str(row.get("condition_fields", "")).strip() for row in samples if str(row.get("condition_fields", "")).strip()), "")
    condition_fields = [field.strip() for field in condition_fields_raw.split(",") if field.strip()] or ["pack_id", "chemistry", "design", "c_rate", "protocol"]
    condition_cells = {
        str(condition): sorted({row["cell_id"] for row in samples if row.get("condition_id") == condition})
        for condition in sorted({row.get("condition_id") for row in samples if row.get("condition_id") not in (None, "")})
    }
    report = {
        "scope": scope,
        "run_status": "PASS",
        "evidence_status": evidence_status,
        "paper_eligible": False,
        "preprocessing": preprocessing,
        "source_ids": sorted({row["source_id"] for row in rows}),
        "chemistry": sorted({row["chemistry"] for row in rows}),
        "n_cells": len(cells),
        "n_samples": len(samples),
        "horizon_cycles": horizon,
        "history_window_cycles": history_window,
        "feature_names": list(names),
        "q1": {
            "cells": [
                {
                    **analyze_cell(records),
                    "knee_status": q1_status,
                    "knee_x": None,
                    "slope_before": None,
                    "slope_after": None,
                    "paper_eligible": False,
                }
                for records in grouped.values()
            ],
            "knee_analysis": {
                "status": q1_status,
                "paper_eligible": False,
                "reason": q1_reason,
            },
            "factors": {factor: factor_analysis(grouped, factor) for factor in ("temperature", "c_rate", "dod", "protocol")},
        },
        "models": by_model,
        "interval": interval,
        "bootstrap": {"unit": "cell_id", "confidence": 0.90},
        "leakage_audit": {
            "max_cell_overlap": max((len(row["cell_overlap"]) for row in audit), default=0),
            "folds": audit,
            "future_rows_used": False,
            "preprocessing_future_points_used": preprocessing_future_points_used,
        },
        "label_shuffle_sanity": {"status": "PASS" if shuffled_rmse > sanity_rmse * 1.01 else "WARN", "normal_rmse": sanity_rmse, "shuffled_rmse": shuffled_rmse, "criterion": "shuffled RMSE > normal RMSE by 1%"},
        "leave_condition_out": _condition_eval(samples, names, n_splits, seed) if leave_condition_out else {
            "status": "NOT_REQUESTED",
            "condition_definition": {
                "fields": condition_fields,
                "source_adapter_field": "condition_id",
                "interpretation": "复合实验层留出，不等同单因素或普遍工况泛化",
                "cells_per_condition": {key: len(value) for key, value in condition_cells.items()},
                "condition_cells": condition_cells,
            },
        },
        "limitations": [
            "Descriptive association only; factor effects are not causal.",
            "Prediction intervals are descriptive residual envelopes, not finite-sample cell-level guarantees.",
            "Knee results are held until source-consistent RPT preprocessing is implemented.",
            "No source-specific unit conversion or chemistry harmonization.",
            "TEST_ONLY metrics are not paper results.",
        ],
    }
    report["_predictions"] = predictions
    report["_metrics_by_cell"] = cell_metrics
    report["_metrics_by_condition"] = condition_metrics
    return report


def write_artifacts(report: dict, out_dir: str | os.PathLike) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    predictions = report.get("_predictions", [])
    by_cell = report.get("_metrics_by_cell", [])
    by_condition = report.get("_metrics_by_condition", [])
    payload = {key: value for key, value in report.items() if not key.startswith("_")}
    report_path = out / "report.json"
    report_path.write_text(__import__("json").dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    paths = {"report": str(report_path)}
    for name, rows in (("predictions", predictions), ("metrics_by_cell", by_cell), ("metrics_by_condition", by_condition)):
        path = out / f"{name}.csv"
        if rows:
            columns = sorted({key for row in rows for key in row})
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
        else:
            path.write_text("\n", encoding="utf-8")
        paths[name] = str(path)
    return paths
