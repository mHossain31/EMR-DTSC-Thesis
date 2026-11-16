"""The legacy NOx predictor, replicated and tested (docs/SPECIFICATION.md 7.4).

Training data: per-vehicle-step emission rates (mg/s) from static runs on train seeds 0-1 (experiment
``legacy_train``). The legacy notebook trained on 642,472 rows; the same number of rows is drawn at random
(seed 42) from the pooled records, then split 80/20 by row with ``random_state=42`` exactly as the notebook did.
Model: ``RandomForestRegressor(n_estimators=100, random_state=42)`` on [CO2, CO, HC, PMx] -> NOx, raw (not
normalized) values, as the audit established.

Tests of the task (7.4 i): the RF's random-split score against (a) a single-feature monotone baseline (isotonic
regression of NOx on CO2 alone) and (b) a split by run (train on seed 0, test on seed 1).

Threshold: the legacy rule fired on a share of vehicle-steps that the audit measured (detections / rows of the RF
run). The primary C5 threshold is the training-NOx quantile that leaves that share above it; the literal 1.88 is
also reported with the quantile it corresponds to.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from nycemis.config import base_config
from nycemis.experiments.plan import exp_dir, load_plan
from nycemis.paths import models_dir, rel, results_dir

FEATURES = ["co2_mg_s", "co_mg_s", "hc_mg_s", "pmx_mg_s"]
TARGET = "nox_mg_s"
LEGACY_ROWS = 642_472  # rows of the legacy training data frame (cell 6 output; checked in the audit numbers)
LEGACY_LITERAL_THRESHOLD = 1.88
TRAIN_EXPERIMENT = "legacy_train"


def model_dir(scenario: str) -> Path:
    return models_dir() / scenario / "legacy_rf"


def load_records(experiment: str = TRAIN_EXPERIMENT) -> pd.DataFrame:
    doc = load_plan(experiment)
    train = set(base_config().seeds.train_seeds())
    parts = []
    for r in doc["runs"]:
        spec = r["spec"]
        if spec["seed"] not in train:
            raise ValueError(f"{experiment}: seed {spec['seed']} is not a train seed")
        path = exp_dir(experiment) / r["run_id"] / "vehicle_records.parquet"
        df = pd.read_parquet(path)
        df["seed"] = spec["seed"]
        df["level"] = spec["level"]
        parts.append(df)
    return pd.concat(parts, ignore_index=True)


def _scores(y_true, y_pred) -> dict:
    return {"mse": float(mean_squared_error(y_true, y_pred)), "mae": float(mean_absolute_error(y_true, y_pred)),
            "r2": float(r2_score(y_true, y_pred)), "n": int(len(y_true))}


def legacy_flag_share() -> float:
    audit = json.loads((results_dir() / "legacy_audit" / "audit_numbers.json").read_text(encoding="utf-8"))
    if audit["d1_horizon"]["baseline_rows_notebook"] != LEGACY_ROWS:
        raise ValueError("audit row count differs from LEGACY_ROWS")
    return audit["d2_reroutes"]["rf"]["detections"] / audit["d1_horizon"]["rf_controlled_rows"]


def train(scenario: str) -> dict:
    t0 = time.perf_counter()
    rec = load_records()
    rng = np.random.default_rng(42)
    sample = rec.iloc[np.sort(rng.choice(len(rec), size=min(LEGACY_ROWS, len(rec)), replace=False))]
    x, y = sample[FEATURES].to_numpy(), sample[TARGET].to_numpy()
    x_tr, x_te, y_tr, y_te = train_test_split(x, y, test_size=0.2, random_state=42)
    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1).fit(x_tr, y_tr)
    rf_scores = _scores(y_te, rf.predict(x_te))

    iso = IsotonicRegression(out_of_bounds="clip").fit(x_tr[:, 0], y_tr)
    iso_scores = _scores(y_te, iso.predict(x_te[:, 0]))

    s0, s1 = sample[sample.seed == 0], sample[sample.seed == 1]
    rf_run = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1).fit(s0[FEATURES].to_numpy(),
                                                                                      s0[TARGET].to_numpy())
    run_scores = _scores(s1[TARGET].to_numpy(), rf_run.predict(s1[FEATURES].to_numpy()))

    share = legacy_flag_share()
    q = 1.0 - share
    threshold = float(np.quantile(y_tr, q))
    literal_q = float((y_tr <= LEGACY_LITERAL_THRESHOLD).mean())
    rf.set_params(n_jobs=1)  # serving: one core per simulation process
    out = model_dir(scenario)
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(rf, out / "model.joblib", compress=3)
    metrics = {
        "model": "RandomForestRegressor(n_estimators=100, random_state=42)", "features_mg_s": FEATURES,
        "target_mg_s": TARGET, "records_pooled": int(len(rec)), "rows_used": int(len(sample)),
        "split": "random 80/20 by row, random_state=42",
        "rf_random_split": rf_scores, "isotonic_co2_only_random_split": iso_scores,
        "rf_split_by_run_seed0_to_seed1": run_scores,
        "legacy_flag_share": share, "threshold_quantile": q, "threshold_quantile_mg_s": threshold,
        "literal_threshold_mg_s": LEGACY_LITERAL_THRESHOLD, "literal_threshold_training_quantile": literal_q,
        "train_seeds": sorted(int(s) for s in rec.seed.unique()), "levels": sorted(rec.level.unique().tolist()),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (out / "train_manifest.json").write_text(json.dumps({
        "experiment": TRAIN_EXPERIMENT, "runs": [r["run_id"] for r in load_plan(TRAIN_EXPERIMENT)["runs"]],
        "model_file": rel(out / "model.joblib")}, indent=2) + "\n", encoding="utf-8")
    (out / "model_card.md").write_text(_card(metrics), encoding="utf-8")
    res = results_dir() / "legacy_audit" / "legacy_rf_eval.json"
    res.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def _card(m: dict) -> str:
    return (
        "# Model card: legacy RF (replication)\n\n"
        "Generated by `python -m nycemis train-legacy`; do not edit by hand.\n\n"
        f"- Purpose: replicate the legacy notebook's NOx predictor for condition C5 (`legacy_ml`); not a "
        "forecaster and not used by any other controller.\n"
        f"- Model: {m['model']}; features {', '.join(m['features_mg_s'])} (mg/s); target {m['target_mg_s']}.\n"
        f"- Data: {m['rows_used']:,} of {m['records_pooled']:,} per-vehicle-step records from static runs, train "
        f"seeds {m['train_seeds']}, levels {', '.join(m['levels'])}; {m['split']}.\n"
        f"- Random-split test: MSE {m['rf_random_split']['mse']:.4g}, R2 {m['rf_random_split']['r2']:.4f}.\n"
        f"- Single-feature monotone baseline (isotonic on CO2): MSE {m['isotonic_co2_only_random_split']['mse']:.4g}, "
        f"R2 {m['isotonic_co2_only_random_split']['r2']:.4f}.\n"
        f"- Split by run (seed 0 -> seed 1): MSE {m['rf_split_by_run_seed0_to_seed1']['mse']:.4g}, "
        f"R2 {m['rf_split_by_run_seed0_to_seed1']['r2']:.4f}.\n"
        f"- Threshold: training-NOx quantile {m['threshold_quantile']:.4f} = {m['threshold_quantile_mg_s']:.4g} mg/s "
        f"(the legacy run flagged {100 * m['legacy_flag_share']:.2f}% of vehicle-steps); the literal 1.88 mg/s is "
        f"the {100 * m['literal_threshold_training_quantile']:.1f}th percentile of training NOx.\n"
        "- Limitations: the inputs are outputs of the same emission model at the same instant (docs/SPECIFICATION.md D4).\n"
    )
