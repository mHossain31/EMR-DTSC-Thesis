"""Evidence for DEVIATIONS #14: the objective of the r forecaster (NOx mg per vehicle-second), on validation seeds.

Compares the first gbm_v1 (r fitted on log1p, kept as ``models/flushing/gbm_v1_rejected_log1p``) with squared error
on the raw scale and with Poisson and Tweedie objectives (log link, mean-estimating), each refitted with the rejected
model's tuned parameters, and with the per-edge historical mean. Same 10% per-run samples as ``nycemis train``.
Test seeds are not read. Writes ``results/forecaster/r_objective_comparison.json``.

Usage: python scripts/compare_r_objective.py
"""

from __future__ import annotations

import json

import lightgbm as lgb
import numpy as np

from nycemis.config import base_config
from nycemis.features.builder import feature_names
from nycemis.models.evaluate import _reg_metrics
from nycemis.models.registry import load_forecaster
from nycemis.models.train import load_windows
from nycemis.paths import rel, results_dir

SEED = 20261115  # the sampling seeds of models.train.freeze (train: SEED, validation: SEED + 1)


def main() -> None:
    s = base_config().seeds
    tr = load_windows(["dataset"], set(s.train_seeds()), 0.10, SEED)
    va = load_windows(["dataset"], set(s.validation_seeds()), 0.10, SEED + 1)
    names = feature_names("F1")
    m_tr, m_va = tr.r_next.notna().to_numpy(), va.r_next.notna().to_numpy()
    x_tr, y_tr = tr.loc[m_tr, names].to_numpy(np.float32), tr.loc[m_tr, "r_next"].to_numpy()
    x_va, y_va = va.loc[m_va, names].to_numpy(np.float32), va.loc[m_va, "r_next"].to_numpy()
    old = load_forecaster("flushing", "gbm_v1_rejected_log1p")
    out = {"rows_train": int(len(y_tr)), "rows_validation": int(len(y_va)),
           "validation_mean_r": float(y_va.mean()), "results": {}}
    out["results"]["log1p_squared_error (rejected gbm_v1)"] = _reg_metrics(y_va, old.predict(x_va)[0])
    hist = tr[m_tr].groupby("edge_idx").r_next.mean()
    out["results"]["historical_mean"] = _reg_metrics(
        y_va, hist.reindex(va.loc[m_va, "edge_idx"]).fillna(y_tr.mean()).to_numpy())
    p = {k: v for k, v in old.params["r"].items() if k not in ("best_iteration", "n_jobs")}
    for objective in ("regression", "poisson", "tweedie"):
        model = lgb.LGBMRegressor(objective=objective, n_estimators=2000, subsample_freq=1, random_state=1,
                                  n_jobs=-1, verbose=-1, **p)
        model.fit(x_tr, y_tr, eval_set=[(x_va, y_va)], eval_metric="l2",
                  callbacks=[lgb.early_stopping(50, verbose=False)])
        key = "raw_squared_error" if objective == "regression" else objective
        out["results"][key] = {**_reg_metrics(y_va, model.predict(x_va)), "best_iteration": int(model.best_iteration_)}
    path = results_dir() / "forecaster" / "r_objective_comparison.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    for k, v in out["results"].items():
        print(f"{k:40s} MAE {v['mae']:.3f} R2 {v['r2']:.3f} mean ratio {v['mean_ratio']:.3f} "
              f"calib slope {v['calib_slope']:.3f}")
    print(f"wrote {rel(path)}")


if __name__ == "__main__":
    main()
