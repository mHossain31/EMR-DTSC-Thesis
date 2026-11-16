"""Forecast skill against baselines (docs/SPECIFICATION.md 7.3, 4.7).

Baselines (all use only information available at decision time):
- persistence: the value observed in window k (r and d from F2's emission lags, r falling back to the edge's
  historical mean when window k was empty; v from the window speed, the limit when empty),
- EMA: weights 0.5, 0.3, 0.2 on windows k, k-1, k-2,
- historical mean: the per-edge mean of the training rows,
- Ridge: linear regression on F1 (standardised), fitted on the training rows (r and v raw, d on log1p, as the model).
Metrics: MAE, RMSE, R2, Spearman per target; calibration as the mean ratio (mean prediction / mean truth) and the
calibration slope (least-squares slope of truth on prediction; 1 is calibrated, above 1 means too little spread); hotspot PR-AUC, F1 at the frozen threshold, precision at the top 1%
and 5% of edges per tick. Intervals: cluster bootstrap over runs (1,000 resamples, fixed seed).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.metrics import average_precision_score, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from nycemis.features.builder import feature_names
from nycemis.sim.netinfo import ROAD_CLASS_NAMES

EMA_W = (0.5, 0.3, 0.2)
BOOT = 1000


def _lag_cols(df: pd.DataFrame, key: str) -> np.ndarray:
    return np.column_stack([df[f"{key}_l{lag}"].to_numpy() for lag in (0, 1, 2)])


def baseline_predictions(df: pd.DataFrame, train: pd.DataFrame) -> dict[str, dict[str, np.ndarray]]:
    limit = df.speed_limit_mps.to_numpy()
    v_lags = _lag_cols(df, "speed_ratio") * limit[:, None]
    r_lags, d_lags = _lag_cols(df, "nox_rate"), _lag_cols(df, "nox_dens")
    w = np.array(EMA_W)
    hist = train.groupby("edge_idx").agg(r=("r_next", "mean"), v=("v_next", "mean"), d=("d_next", "mean"))
    glob = {"r": float(train.r_next.mean()), "v": float(train.v_next.mean()), "d": float(train.d_next.mean())}
    h = hist.reindex(df.edge_idx.to_numpy())
    h_r = h["r"].fillna(glob["r"]).to_numpy()
    # A per-vehicle rate is undefined on an empty window: persistence and EMA fall back to the edge's history.
    seen = _lag_cols(df, "cnt_mean") > 0
    r_pers = np.where(seen[:, 0], r_lags[:, 0], h_r)
    w_seen = seen * w
    w_sum = w_seen.sum(axis=1)
    r_ema = np.where(w_sum > 0, (r_lags * w_seen).sum(axis=1) / np.maximum(w_sum, 1e-12), h_r)
    names = feature_names("F1")
    ridge = {}
    for t, col in (("r", "r_next"), ("v", "v_next"), ("d", "d_next")):
        m = train[col].notna()
        y = np.log1p(train.loc[m, col]) if t == "d" else train.loc[m, col]
        model = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(train.loc[m, names].to_numpy(np.float32), y)
        pred = model.predict(df[names].to_numpy(np.float32))
        ridge[t] = np.maximum(np.expm1(pred), 0) if t == "d" else pred
    return {
        "persistence": {"r": r_pers, "v": v_lags[:, 0], "d": d_lags[:, 0]},
        "ema": {"r": r_ema, "v": v_lags @ w, "d": d_lags @ w},
        "historical_mean": {t: h[t].fillna(glob[t]).to_numpy() for t in ("r", "v", "d")},
        "ridge": ridge,
    }


def _reg_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    err = p - y
    ss = float(((y - y.mean()) ** 2).sum())
    var_p = float(((p - p.mean()) ** 2).sum())
    return {"mae": float(np.abs(err).mean()), "rmse": float(np.sqrt((err ** 2).mean())),
            "r2": float(1 - (err ** 2).sum() / ss) if ss > 0 else float("nan"),
            "mean_ratio": float(p.mean() / y.mean()) if y.mean() != 0 else float("nan"),
            "calib_slope": float(((p - p.mean()) * (y - y.mean())).sum() / var_p) if var_p > 0 else float("nan"),
            "spearman": float(stats.spearmanr(y, p).statistic) if len(y) > 2 else float("nan"), "n": int(len(y))}


def _precision_at(df: pd.DataFrame, score: np.ndarray, label: np.ndarray, frac: float) -> float:
    tmp = pd.DataFrame({"g": df.run_id.astype(str) + ":" + df.k.astype(str), "s": score, "y": label})
    hits = total = 0
    for _, g in tmp.groupby("g"):
        top = max(1, int(round(frac * len(g))))
        sel = g.nlargest(top, "s")
        hits += int(sel.y.sum())
        total += top
    return hits / total if total else float("nan")


def evaluate(forecaster, df: pd.DataFrame, train: pd.DataFrame) -> dict:
    names = feature_names("F1")
    x = df[names].to_numpy(np.float32)
    r_hat, v_hat = forecaster.predict(x)
    preds = {"model": {"r": r_hat, "v": v_hat, "d": forecaster.predict_density(x)}}
    preds.update(baseline_predictions(df, train))
    masks = {"r": df.r_next.notna().to_numpy(), "v": df.v_next.notna().to_numpy(), "d": np.ones(len(df), bool)}
    truth = {"r": df.r_next.to_numpy(), "v": df.v_next.to_numpy(), "d": df.d_next.to_numpy()}
    out: dict = {"regression": {}, "hotspot": {}, "by_level": {}, "by_road_class": {}}
    for name, p in preds.items():
        out["regression"][name] = {t: _reg_metrics(truth[t][masks[t]], p[t][masks[t]]) for t in ("r", "v", "d")}
    label = (df.d_next.to_numpy() > forecaster.hotspot_threshold).astype(int)
    for name, p in preds.items():
        score = p["d"]
        out["hotspot"][name] = {
            "pr_auc": float(average_precision_score(label, score)) if label.any() else float("nan"),
            "f1_at_threshold": float(f1_score(label, (score > forecaster.hotspot_threshold).astype(int))),
            "precision_top1pct": _precision_at(df, score, label, 0.01),
            "precision_top5pct": _precision_at(df, score, label, 0.05),
            "base_rate": float(label.mean()),
        }
    for level, g in df.groupby("level"):
        idx = g.index.to_numpy()
        out["by_level"][level] = {n: {t: _reg_metrics(truth[t][idx][masks[t][idx]], p[t][idx][masks[t][idx]])
                                      for t in ("r", "v")} for n, p in preds.items() if n in ("model", "persistence")}
    for code, g in df.groupby(df.road_class.astype(int)):
        idx = g.index.to_numpy()
        out["by_road_class"][ROAD_CLASS_NAMES[int(code)]] = {
            n: {t: _reg_metrics(truth[t][idx][masks[t][idx]], p[t][idx][masks[t][idx]]) for t in ("r", "v")}
            for n, p in preds.items() if n in ("model", "persistence")}
    out["bootstrap"] = cluster_bootstrap(df, preds, truth, masks)
    return out


def cluster_bootstrap(df: pd.DataFrame, preds: dict, truth: dict, masks: dict, seed: int = 20261115) -> dict:
    """95% intervals of the MAE skill of the model relative to each baseline, resampling runs."""
    runs = df.run_id.to_numpy()
    uniq = np.unique(runs)
    rng = np.random.default_rng(seed)
    idx_by_run = {u: np.flatnonzero(runs == u) for u in uniq}
    res = {}
    for base in [n for n in preds if n != "model"]:
        for t in ("r", "v", "d"):
            skills = []
            for _ in range(BOOT):
                pick = np.concatenate([idx_by_run[u] for u in rng.choice(uniq, size=len(uniq), replace=True)])
                m = masks[t][pick]
                y = truth[t][pick][m]
                mae_model = np.abs(preds["model"][t][pick][m] - y).mean()
                mae_base = np.abs(preds[base][t][pick][m] - y).mean()
                skills.append(1.0 - mae_model / mae_base)
            lo, hi = np.percentile(skills, [2.5, 97.5])
            res[f"{t}_mae_skill_vs_{base}"] = {"ci95_low": float(lo), "ci95_high": float(hi),
                                               "runs": int(len(uniq))}
    return res
