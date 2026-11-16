"""Train and freeze the forecaster (docs/SPECIFICATION.md 7.3, 7.5).

Data: ``edge_window`` rows of the dataset experiments (mixed behaviour policies), train seeds for fitting and
validation seeds for early stopping and the random search; test seeds are never read here (asserted). Rows are
subsampled uniformly per run with a fixed seed to bound memory; the fraction is recorded.
Targets: r_next (masked below 10 vehicle-seconds), v_next (masked on empty windows), d_next (all rows; log1p).
The hotspot threshold is the 95th percentile of d_next over non-empty training edge-windows.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from nycemis.config import base_config
from nycemis.experiments.plan import exp_dir, load_plan
from nycemis.features.builder import feature_names
from nycemis.manifest import sha256_file
from nycemis.models.gbm import HAVE_LGB, GBMForecaster, fit_regressor
from nycemis.paths import models_dir, rel
from nycemis.sim.runner import git_state

log = logging.getLogger(__name__)

SEARCH_TRIALS = 30
HOTSPOT_QUANTILE = 0.95
TARGETS = ("r", "v", "d")


def load_windows(experiments: list[str], seeds: set[int], sample_frac: float, seed: int) -> pd.DataFrame:
    test = set(base_config().seeds.test_seeds(base_config().seeds.test_n_max))
    if seeds & test:
        raise ValueError("test seeds must not be used for training or tuning")
    rng = np.random.default_rng(seed)
    parts = []
    for exp in experiments:
        for r in load_plan(exp)["runs"]:
            spec = r["spec"]
            if spec["seed"] not in seeds or not spec["dataset"]:
                continue
            path = exp_dir(exp) / r["run_id"] / "edge_window.parquet"
            if not path.is_file():
                raise FileNotFoundError(f"{path} missing (run not DONE?)")
            df = pd.read_parquet(path)
            if sample_frac < 1.0:
                df = df.iloc[np.sort(rng.choice(len(df), size=int(round(sample_frac * len(df))), replace=False))]
            df = df.assign(level=spec["level"], seed=spec["seed"], policy=r["label"])
            parts.append(df)
    if not parts:
        raise ValueError(f"no dataset rows for seeds {sorted(seeds)} in {experiments}")
    return pd.concat(parts, ignore_index=True)


def target_arrays(df: pd.DataFrame, target: str) -> tuple[np.ndarray, np.ndarray]:
    names = feature_names("F1")
    if target == "r":
        m = df.r_next.notna().to_numpy()
        return df.loc[m, names].to_numpy(np.float32), np.log1p(df.loc[m, "r_next"].to_numpy())
    if target == "v":
        m = df.v_next.notna().to_numpy()
        return df.loc[m, names].to_numpy(np.float32), df.loc[m, "v_next"].to_numpy()
    if target == "d":
        return df[names].to_numpy(np.float32), np.log1p(df.d_next.to_numpy())
    raise ValueError(target)


def sample_params(rng: np.random.Generator) -> dict:
    return {
        "learning_rate": float(10 ** rng.uniform(-2.0, -0.8)),
        "num_leaves": int(rng.choice([15, 31, 63, 127, 255])),
        "min_child_samples": int(rng.choice([20, 50, 100, 200, 500])),
        "colsample_bytree": float(rng.uniform(0.5, 1.0)),
        "subsample": float(rng.uniform(0.5, 1.0)),
        "reg_lambda": float(10 ** rng.uniform(-3, 1)),
    }


def _val_loss(model, x, y) -> float:
    return float(np.mean((model.predict(x) - y) ** 2))


def search_and_fit(train: pd.DataFrame, val: pd.DataFrame, trials: int, seed: int,
                   n_jobs: int = -1) -> tuple[dict, dict, list]:
    rng = np.random.default_rng(seed)
    candidates = [{**sample_params(rng), "n_jobs": n_jobs} for _ in range(trials)]
    best: dict = {}
    models: dict = {}
    history = []
    for target in TARGETS:
        x_tr, y_tr = target_arrays(train, target)
        x_va, y_va = target_arrays(val, target)
        best_loss = np.inf
        log.info("target %s: %d training rows, %d validation rows", target, len(y_tr), len(y_va))
        for i, params in enumerate(candidates):
            t0 = time.perf_counter()
            model = fit_regressor(params, seed + i, x_tr, y_tr, x_va, y_va)
            loss = _val_loss(model, x_va, y_va)
            n_iter = int(getattr(model, "best_iteration_", 0) or 0)
            log.info("target %s trial %d/%d: val_mse %.5f, %d iterations, %.0f s", target, i + 1, len(candidates),
                     loss, n_iter, time.perf_counter() - t0)
            history.append({"target": target, "trial": i, "val_mse": loss, "best_iteration": n_iter, **params})
            if loss < best_loss:
                best_loss, best[target], models[target] = loss, {**params, "best_iteration": n_iter}, model
    return best, models, history


def freeze(scenario: str, model_id: str, experiments: list[str], sample_frac: float, trials: int = SEARCH_TRIALS,
           seed: int = 20261115, n_jobs: int = -1) -> dict:
    t0 = time.perf_counter()
    s = base_config().seeds
    train = load_windows(experiments, set(s.train_seeds()), sample_frac, seed)
    log.info("loaded %d training edge-windows", len(train))
    val = load_windows(experiments, set(s.validation_seeds()), sample_frac, seed + 1)
    best, models, history = search_and_fit(train, val, trials, seed, n_jobs)
    nonempty = train.veh_s_next.to_numpy() > 0
    threshold = float(np.quantile(train.d_next.to_numpy()[nonempty], HOTSPOT_QUANTILE))
    names = feature_names("F1")
    for m in models.values():
        if hasattr(m, "set_params"):
            m.set_params(n_jobs=1)  # serving: one core per simulation process
    fc = GBMForecaster(feature_set="F1", feature_names=names, models=models, params=best,
                       backend="lightgbm" if HAVE_LGB else "sklearn-hgb", hotspot_threshold=threshold)
    out = models_dir() / scenario / model_id
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(fc, out / "model.joblib", compress=3)
    (out / "features.json").write_text(json.dumps({"feature_set": "F1", "names": names}, indent=2) + "\n",
                                       encoding="utf-8")
    pd.DataFrame(history).to_csv(out / "search_history.csv", index=False)
    data_files = []
    for exp in experiments:
        for r in load_plan(exp)["runs"]:
            if r["spec"]["dataset"] and r["spec"]["seed"] in set(s.train_seeds()) | set(s.validation_seeds()):
                p = exp_dir(exp) / r["run_id"] / "edge_window.parquet"
                data_files.append({"run_id": r["run_id"], "seed": r["spec"]["seed"], "file": rel(p),
                                   "sha256": sha256_file(p)})
    manifest = {"experiments": experiments, "train_seeds": s.train_seeds(), "validation_seeds": s.validation_seeds(),
                "sample_frac": sample_frac, "rows_train": int(len(train)), "rows_validation": int(len(val)),
                "search_trials": trials, "seed": seed, "git": git_state(), "data": data_files,
                "hotspot_threshold_mg_per_lane_m": threshold, "best_params": best,
                "backend": fc.backend, "seconds": round(time.perf_counter() - t0, 1)}
    (out / "train_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def model_path(scenario: str, model_id: str) -> Path:
    return models_dir() / scenario / model_id / "model.joblib"
