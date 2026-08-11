"""问题2：按电芯留组的 SOH 预测及右删失感知 RUL 建模。"""
from __future__ import annotations

import math
import os
import statistics
from collections import defaultdict

import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from g1_generator import degradation as g1deg

from . import common, data


FEATURE_NAMES = (
    "soh_observed",
    "capacity_obs",
    "resistance_growth",
    "capacity_slope",
    "resistance_slope",
    "cycle",
    "efc",
    "temperature",
    "c_rate",
    "dod",
)


def _matrix(records: list[dict]) -> np.ndarray:
    return np.asarray([[float(row[name]) for name in FEATURE_NAMES] for row in records], dtype=float)


def make_soh_samples(grouped: dict[str, list[dict]], study_cfg) -> list[dict]:
    q2 = study_cfg.q2
    samples = []
    for cell_id, records in grouped.items():
        last_snapshot = len(records) - q2.forecast_horizon_cycles
        for cycle in range(q2.history_window_cycles, last_snapshot + 1, q2.snapshot_step_cycles):
            feature = data.feature_at_cycle(records, cycle, q2.history_window_cycles)
            feature["target_soh"] = float(records[cycle + q2.forecast_horizon_cycles - 1]["soh"])
            feature["forecast_cycle"] = cycle + q2.forecast_horizon_cycles
            samples.append(feature)
    return samples


def _soh_models(seed: int, trees: int):
    return {
        "ridge": Pipeline([
            ("scale", StandardScaler()),
            ("model", Ridge(alpha=1.0)),
        ]),
        "random_forest": RandomForestRegressor(
            n_estimators=trees,
            min_samples_leaf=3,
            max_features=0.8,
            n_jobs=1,
            random_state=seed,
        ),
    }


def cross_validated_soh_predictions(samples: list[dict], study_cfg):
    x = _matrix(samples)
    y = np.asarray([row["target_soh"] for row in samples], dtype=float)
    groups = np.asarray([row["cell_id"] for row in samples])
    splitter = GroupKFold(n_splits=study_cfg.q2.cv_splits)
    predictions = []
    audit = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(x, y, groups), start=1):
        train_cells = sorted(set(groups[train_idx]))
        test_cells = sorted(set(groups[test_idx]))
        data.assert_group_disjoint(train_cells, test_cells)
        audit.append({
            "fold": fold,
            "n_train_rows": len(train_idx),
            "n_test_rows": len(test_idx),
            "n_train_cells": len(train_cells),
            "n_test_cells": len(test_cells),
            "cell_overlap": [],
        })
        model_predictions = {
            "persistence": np.asarray([samples[index]["soh_observed"] for index in test_idx]),
            "local_linear": np.asarray([
                samples[index]["soh_observed"]
                + samples[index]["capacity_slope"] * study_cfg.q2.forecast_horizon_cycles
                for index in test_idx
            ]),
        }
        for name, model in _soh_models(study_cfg.study_seed + fold, study_cfg.q2.random_forest_trees).items():
            model.fit(x[train_idx], y[train_idx])
            model_predictions[name] = model.predict(x[test_idx])
        for local_index, sample_index in enumerate(test_idx):
            sample = samples[sample_index]
            for name, values in model_predictions.items():
                predictions.append({
                    "cell_id": sample["cell_id"],
                    "condition_id": sample["condition_id"],
                    "fold": fold,
                    "cycle": sample["cycle"],
                    "forecast_cycle": sample["forecast_cycle"],
                    "model": name,
                    "target_soh": sample["target_soh"],
                    "predicted_soh": float(values[local_index]),
                })
    return predictions, audit


def leave_condition_out(samples: list[dict], study_cfg) -> list[dict]:
    x = _matrix(samples)
    y = np.asarray([row["target_soh"] for row in samples], dtype=float)
    conditions = np.asarray([row["condition_id"] for row in samples])
    output = []
    for condition_index, held_out in enumerate(sorted(set(conditions))):
        train_idx = np.flatnonzero(conditions != held_out)
        test_idx = np.flatnonzero(conditions == held_out)
        model_predictions = {
            "persistence": np.asarray([samples[index]["soh_observed"] for index in test_idx]),
            "local_linear": np.asarray([
                samples[index]["soh_observed"]
                + samples[index]["capacity_slope"] * study_cfg.q2.forecast_horizon_cycles
                for index in test_idx
            ]),
        }
        trees = max(60, study_cfg.q2.random_forest_trees // 2)
        for name, model in _soh_models(study_cfg.study_seed + condition_index, trees).items():
            model.fit(x[train_idx], y[train_idx])
            model_predictions[name] = model.predict(x[test_idx])
        for name, pred in model_predictions.items():
            metrics = common.regression_metrics(y[test_idx], pred)
            output.append({
                "held_out_condition": str(held_out),
                "model": name,
                "n_test": len(test_idx),
                **metrics,
            })
    return output


class CensoredLogNormalAFT:
    """Small deterministic log-normal AFT with right-censored likelihood."""

    def __init__(
        self,
        regularization: float = 1e-3,
        confidence: float = 0.9,
        calibration_confidence: float | None = None,
    ):
        self.regularization = regularization
        self.confidence = confidence
        self.calibration_confidence = (
            min(0.99, confidence + 0.09)
            if calibration_confidence is None else calibration_confidence
        )

    def fit(self, x, duration, event):
        x = np.asarray(x, dtype=float)
        duration = np.asarray(duration, dtype=float)
        event = np.asarray(event, dtype=bool)
        self.mean_ = x.mean(axis=0)
        self.scale_ = x.std(axis=0)
        self.scale_[self.scale_ < 1e-12] = 1.0
        z_x = (x - self.mean_) / self.scale_
        design = np.column_stack([np.ones(x.shape[0]), z_x])
        log_t = np.log(np.maximum(duration, 1e-9))
        initial = np.zeros(design.shape[1] + 1)
        initial[0] = float(np.median(log_t))
        initial[-1] = math.log(max(float(np.std(log_t)), 0.2))

        def objective(parameters):
            beta = parameters[:-1]
            sigma = math.exp(float(parameters[-1]))
            standardized = (log_t - design @ beta) / sigma
            observed_ll = -log_t - math.log(sigma) - 0.5 * math.log(2.0 * math.pi) - 0.5 * standardized**2
            censored_ll = log_ndtr(-standardized)
            log_likelihood = np.where(event, observed_ll, censored_ll)
            penalty = self.regularization * float(beta[1:] @ beta[1:])
            return -float(np.sum(log_likelihood)) + penalty

        bounds = [(None, None)] * (len(initial) - 1) + [(-4.0, 2.0)]
        result = minimize(objective, initial, method="L-BFGS-B", bounds=bounds)
        if not result.success or not np.all(np.isfinite(result.x)):
            raise RuntimeError(f"AFT 优化失败: {result.message}")
        self.beta_ = result.x[:-1]
        self.sigma_ = math.exp(float(result.x[-1]))
        fitted_median = np.exp(design @ self.beta_)
        observed_log_residual = np.abs(log_t[event] - np.log(fitted_median[event]))
        parametric_radius = statistics.NormalDist().inv_cdf(
            (1.0 + self.confidence) / 2.0
        ) * self.sigma_
        # A small pre-registered conservatism margin compensates for fitting
        # residuals being optimistic relative to held-out cells. It uses only
        # training events and never reads the outer test outcomes.
        empirical_radius = (
            float(np.quantile(observed_log_residual, self.calibration_confidence))
            if observed_log_residual.size else 0.0
        )
        # Never narrow the nominal log-normal interval. The empirical radius
        # protects the downstream screening bound against likelihood underfit.
        self.interval_log_radius_ = max(parametric_radius, empirical_radius)
        self.optimization_ = {"success": True, "iterations": int(result.nit), "objective": float(result.fun)}
        return self

    def predict_lifetime(self, x):
        x = np.asarray(x, dtype=float)
        standardized = (x - self.mean_) / self.scale_
        design = np.column_stack([np.ones(x.shape[0]), standardized])
        location = design @ self.beta_
        median = np.exp(location)
        lower = np.exp(location - self.interval_log_radius_)
        upper = np.exp(location + self.interval_log_radius_)
        return median, lower, upper


def _local_linear_lifetime(row: dict, threshold: float) -> float:
    slope = float(row["capacity_slope"])
    if slope >= -1e-7:
        return 3000.0
    remaining = max(0.0, float(row["soh_observed"]) - threshold)
    return float(np.clip(float(row["cycle"]) + remaining / -slope, row["cycle"], 3000.0))


def _structure_matched_lifetime(row: dict, threshold: float, g1_cfg) -> float:
    # G1 pre-knee history obeys SOH = 1 - alpha*u*sqrt(EFC). Estimate
    # alpha*u from history only, then invert the registered piecewise form.
    target_l = (1.0 - threshold) / float(row["structure_fade_per_sqrt_efc"])
    root_knee = math.sqrt(g1_cfg.n_k_EFC)
    if target_l <= root_knee:
        target_efc = target_l**2
    else:
        target_efc = (root_knee + (target_l - root_knee) / g1_cfg.knee_gain) ** 2
    return float(np.clip(target_efc / (row["dod"] / 100.0), row["cycle"], 3000.0))


def cross_validated_rul_predictions(cell_summaries: list[dict], study_cfg, g1_cfg):
    x = _matrix(cell_summaries)
    duration = np.asarray([row["lifetime_cycle"] for row in cell_summaries], dtype=float)
    event = np.asarray([row["event_observed"] for row in cell_summaries], dtype=bool)
    groups = np.asarray([row["cell_id"] for row in cell_summaries])
    splitter = GroupKFold(n_splits=study_cfg.q2.cv_splits)
    output = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(x, duration, groups), start=1):
        data.assert_group_disjoint(groups[train_idx], groups[test_idx])
        aft = CensoredLogNormalAFT(
            confidence=study_cfg.q2.confidence_level,
            calibration_confidence=study_cfg.q2.interval_calibration_confidence,
        ).fit(
            x[train_idx], duration[train_idx], event[train_idx]
        )
        aft_pred, aft_lower, aft_upper = aft.predict_lifetime(x[test_idx])
        observed_train = train_idx[event[train_idx]]
        ridge = Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=2.0))])
        ridge.fit(x[observed_train], duration[observed_train])
        ridge_pred = ridge.predict(x[test_idx])
        forest = RandomForestRegressor(
            n_estimators=study_cfg.q2.random_forest_trees,
            min_samples_leaf=3,
            max_features=0.8,
            n_jobs=1,
            random_state=study_cfg.study_seed + 100 + fold,
        )
        forest.fit(x[observed_train], duration[observed_train])
        forest_pred = forest.predict(x[test_idx])
        for local_index, sample_index in enumerate(test_idx):
            row = cell_summaries[sample_index]
            predictions = {
                "local_linear": (_local_linear_lifetime(row, study_cfg.q1.critical_soh), None, None),
                "ridge_observed_only": (float(ridge_pred[local_index]), None, None),
                "random_forest_observed_only": (float(forest_pred[local_index]), None, None),
                "lognormal_aft_censored": (
                    float(aft_pred[local_index]), float(aft_lower[local_index]), float(aft_upper[local_index])
                ),
                "structure_matched_simulation_ceiling": (
                    _structure_matched_lifetime(row, study_cfg.q1.critical_soh, g1_cfg), None, None
                ),
            }
            for name, (predicted_lifetime, lower, upper) in predictions.items():
                predicted_lifetime = float(np.clip(predicted_lifetime, row["cycle"], 3000.0))
                output.append({
                    "cell_id": row["cell_id"],
                    "condition_id": row["condition_id"],
                    "fold": fold,
                    "model": name,
                    "landmark_cycle": row["cycle"],
                    "event_observed": bool(row["event_observed"]),
                    "observed_or_censor_lifetime": row["lifetime_cycle"],
                    "true_rul_if_observed": (
                        row["lifetime_cycle"] - row["cycle"] if row["event_observed"] else None
                    ),
                    "censored_rul_lower_bound": (
                        None if row["event_observed"] else row["censor_cycle"] - row["cycle"]
                    ),
                    "predicted_lifetime": predicted_lifetime,
                    "predicted_rul": predicted_lifetime - row["cycle"],
                    "lifetime_lower_90": lower,
                    "lifetime_upper_90": upper,
                })
    return output


def _prediction_metrics(predictions: list[dict], truth_key: str, pred_key: str, study_cfg):
    output = []
    for model in sorted({row["model"] for row in predictions}):
        records = [row for row in predictions if row["model"] == model]
        metrics = common.regression_metrics(
            [row[truth_key] for row in records], [row[pred_key] for row in records]
        )
        intervals = common.grouped_bootstrap_interval(
            records, truth_key, pred_key, "cell_id",
            study_cfg.q2.bootstrap_repetitions,
            study_cfg.q2.confidence_level,
            study_cfg.study_seed + len(output),
        )
        output.append({
            "model": model,
            "n_records": len(records),
            **metrics,
            **{
                f"{name}_{bound}": value
                for name, bounds in intervals.items()
                for bound, value in zip(("ci_low", "ci_high"), bounds)
            },
        })
    return output


def _rul_metrics(predictions: list[dict], study_cfg):
    output = []
    for model in sorted({row["model"] for row in predictions}):
        all_records = [row for row in predictions if row["model"] == model]
        observed = [row for row in all_records if row["event_observed"]]
        censored = [row for row in all_records if not row["event_observed"]]
        metrics = common.regression_metrics(
            [row["true_rul_if_observed"] for row in observed],
            [row["predicted_rul"] for row in observed],
        )
        intervals = common.grouped_bootstrap_interval(
            observed, "true_rul_if_observed", "predicted_rul", "cell_id",
            study_cfg.q2.bootstrap_repetitions,
            study_cfg.q2.confidence_level,
            study_cfg.study_seed + 200 + len(output),
        )
        contradictions = sum(
            row["predicted_lifetime"] < row["observed_or_censor_lifetime"] for row in censored
        )
        interval_records = [row for row in observed if row["lifetime_lower_90"] is not None]
        coverage = None
        if interval_records:
            coverage = sum(
                row["lifetime_lower_90"] <= row["observed_or_censor_lifetime"] <= row["lifetime_upper_90"]
                for row in interval_records
            ) / len(interval_records)
        output.append({
            "model": model,
            "n_observed_events": len(observed),
            "n_right_censored": len(censored),
            **metrics,
            "censored_early_failure_contradiction_rate": contradictions / len(censored),
            "event_interval_90pct_coverage": coverage,
            **{
                f"{name}_{bound}": value
                for name, bounds in intervals.items()
                for bound, value in zip(("ci_low", "ci_high"), bounds)
            },
        })
    return output


def fit_full_aft(cell_summaries: list[dict], confidence: float, calibration_confidence: float):
    x = _matrix(cell_summaries)
    duration = [row["lifetime_cycle"] for row in cell_summaries]
    event = [row["event_observed"] for row in cell_summaries]
    return CensoredLogNormalAFT(
        confidence=confidence,
        calibration_confidence=calibration_confidence,
    ).fit(x, duration, event)


def fit_full_soh_models(samples: list[dict], study_cfg):
    x = _matrix(samples)
    y = np.asarray([row["target_soh"] for row in samples], dtype=float)
    models = _soh_models(study_cfg.study_seed + 900, study_cfg.q2.random_forest_trees)
    for model in models.values():
        model.fit(x, y)
    return models


def analyze(study_cfg, g1_cfg, rows: list[dict], out_dir: str) -> dict:
    grouped = data.group_cells(rows)
    samples = make_soh_samples(grouped, study_cfg)
    soh_predictions, split_audit = cross_validated_soh_predictions(samples, study_cfg)
    soh_metrics = _prediction_metrics(soh_predictions, "target_soh", "predicted_soh", study_cfg)
    lco_metrics = leave_condition_out(samples, study_cfg)

    current_records = [{
        "cell_id": row["cell_id"],
        "model": "rolling_capacity_ratio",
        "soh_true": row["soh_true"],
        "soh_estimate": row["soh_observed"],
    } for row in samples]
    current_metrics = common.regression_metrics(
        [row["soh_true"] for row in current_records],
        [row["soh_estimate"] for row in current_records],
    )

    cell_summaries = data.make_cell_summaries(
        rows, study_cfg.q1.critical_soh,
        study_cfg.q2.landmark_cycle, study_cfg.q2.history_window_cycles,
    )
    rul_predictions = cross_validated_rul_predictions(cell_summaries, study_cfg, g1_cfg)
    rul_metrics = _rul_metrics(rul_predictions, study_cfg)
    common.write_csv(os.path.join(out_dir, "q2_soh_predictions.csv"), soh_predictions)
    common.write_csv(os.path.join(out_dir, "q2_soh_metrics.csv"), soh_metrics)
    common.write_csv(os.path.join(out_dir, "q2_leave_condition_out.csv"), lco_metrics)
    common.write_csv(os.path.join(out_dir, "q2_rul_predictions.csv"), rul_predictions)
    common.write_csv(os.path.join(out_dir, "q2_rul_metrics.csv"), rul_metrics)
    common.write_json(os.path.join(out_dir, "q2_split_audit.json"), split_audit)

    event_count = sum(row["event_observed"] for row in cell_summaries)
    result = {
        "scope": "SYNTHETIC_MODEL_COMPARISON_NOT_EXTERNAL_VALIDATION",
        "current_soh_estimator": {
            "method": "rolling median capacity / initial-window median capacity",
            "metrics": current_metrics,
        },
        "forecast_horizon_cycles": study_cfg.q2.forecast_horizon_cycles,
        "soh_metrics": soh_metrics,
        "rul_endpoint": {
            "threshold": study_cfg.q1.critical_soh,
            "status": "[ASSUMED][UPDATEABLE] modeling endpoint",
            "observed_events": event_count,
            "right_censored": len(cell_summaries) - event_count,
        },
        "rul_interval": {
            "nominal_confidence": study_cfg.q2.confidence_level,
            "training_event_calibration_confidence": study_cfg.q2.interval_calibration_confidence,
            "outer_event_coverage_is_reported_not_assumed": True,
        },
        "rul_metrics": rul_metrics,
        "split_integrity": {
            "method": "GroupKFold(cell_id)",
            "folds": study_cfg.q2.cv_splits,
            "cell_overlap_all_folds": 0,
        },
        "interpretation_limits": [
            "RUL point errors use observed failures only; censored cells are lower bounds.",
            "AFT interval uses a conservative training-event residual calibration; reported outer coverage is empirical, not guaranteed.",
            "ridge/RF RUL comparators train on observed failures only and are censoring-naive.",
            "structure-matched ceiling reuses the simulator functional form and is not evidence of real-world generalization.",
            "leave-condition-out tests interpolation/extrapolation inside the frozen support domain only.",
        ],
    }
    common.write_json(os.path.join(out_dir, "q2_summary.json"), result)
    return {
        "summary": result,
        "samples": samples,
        "cell_summaries": cell_summaries,
        "soh_predictions": soh_predictions,
        "rul_predictions": rul_predictions,
        "full_aft": fit_full_aft(
            cell_summaries,
            study_cfg.q2.confidence_level,
            study_cfg.q2.interval_calibration_confidence,
        ),
        "full_soh_models": fit_full_soh_models(samples, study_cfg),
    }
