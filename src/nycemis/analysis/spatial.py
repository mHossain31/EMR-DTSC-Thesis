"""Spatial side effects (RQ5, docs/SPECIFICATION.md 4.5): NOx share by road class, p99 5-minute edge NOx density, and the Gini
coefficient of per-edge cumulative NOx, per run; then paired changes against a reference condition.

The per-edge tables cover non-internal edges only (junction lanes are not attributed to any edge).

Added after the adversarial review (docs/DEVIATIONS.md #17; exploratory, not preregistered): NOx grams and
vehicle-hours per road class with their paired changes, BCa intervals for every paired spatial quantity, and a
composition decomposition: the share of the edge-NOx change that the road-class mix of vehicle-hours explains, with
each class's NOx per vehicle-hour held at the reference run's value (same level and seed).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from nycemis.analysis.stats import bca_ci, pct_change
from nycemis.experiments.plan import exp_dir
from nycemis.sim.netinfo import ROAD_CLASS_CODES

CLASSES = [c for c in ROAD_CLASS_CODES if c != "other"]
ALL_CLASSES = list(ROAD_CLASS_CODES)


def gini(x: np.ndarray) -> float:
    x = np.sort(np.asarray(x, float))
    if x.sum() <= 0:
        return float("nan")
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))


def run_spatial(experiment: str, run_id: str, n_edges: int) -> dict:
    d = exp_dir(experiment) / run_id
    cum = pd.read_parquet(d / "edge_cumulative.parquet")
    five = pd.read_parquet(d / "edge_5min.parquet")
    total = cum.nox_mg.sum()
    by = cum.groupby("road_class").agg(nox_mg=("nox_mg", "sum"), veh_s=("veh_s", "sum"))
    shares = by.nox_mg / total
    per_edge = np.zeros(n_edges)
    per_edge[cum.edge_idx.to_numpy()] = cum.nox_mg.to_numpy()
    return {**{f"share_{c}": float(shares.get(c, 0.0)) for c in CLASSES},
            "p99_5min_nox_dens_mg_per_lane_m": float(np.percentile(five.nox_dens_mg_per_lane_m, 99)),
            "gini_edge_nox": gini(per_edge), "edge_nox_total_g": float(total / 1000.0),
            **{f"nox_g_{c}": float(by.nox_mg.get(c, 0.0) / 1000.0) for c in ALL_CLASSES},
            **{f"veh_h_{c}": float(by.veh_s.get(c, 0.0) / 3600.0) for c in ALL_CLASSES}}


def spatial_table(experiment: str, runs: pd.DataFrame, n_edges: int) -> pd.DataFrame:
    rows = [{"run_id": r.run_id, "label": r.label, "level": r.level, "seed": r.seed,
             **run_spatial(experiment, r.run_id, n_edges)} for r in runs.itertuples()]
    return pd.DataFrame(rows)


def _join(tab: pd.DataFrame, cond: str, ref: str) -> pd.DataFrame:
    a = tab[tab.label == cond].drop(columns=["run_id", "label"])
    b = tab[tab.label == ref].drop(columns=["run_id", "label"])
    return a.merge(b, on=["level", "seed"], how="inner", suffixes=("_a", "_b")).set_index(["level", "seed"])


def paired_spatial(tab: pd.DataFrame, cond: str, ref: str) -> pd.DataFrame:
    """Paired differences: shares in percentage points; the p99 density, Gini, class NOx and class vehicle-hours in
    percent change."""
    j = _join(tab, cond, ref)
    out = pd.DataFrame(index=j.index)
    for c in CLASSES:
        out[f"share_{c}_pp"] = 100 * (j[f"share_{c}_a"] - j[f"share_{c}_b"])
    out["p99_density_pct"] = pct_change(j["p99_5min_nox_dens_mg_per_lane_m_a"], j["p99_5min_nox_dens_mg_per_lane_m_b"])
    out["gini_pct"] = pct_change(j["gini_edge_nox_a"], j["gini_edge_nox_b"])
    if f"nox_g_{CLASSES[0]}_a" in j:
        out["edge_nox_pct"] = pct_change(j["edge_nox_total_g_a"], j["edge_nox_total_g_b"])
        for c in CLASSES:
            out[f"nox_{c}_pct"] = pct_change(j[f"nox_g_{c}_a"], j[f"nox_g_{c}_b"])
            out[f"veh_h_{c}_pct"] = pct_change(j[f"veh_h_{c}_a"], j[f"veh_h_{c}_b"])
    return out.reset_index()


SUMMARY_METRICS = ["edge_nox_pct", *(f"nox_{c}_pct" for c in CLASSES), *(f"share_{c}_pp" for c in CLASSES),
                   *(f"veh_h_{c}_pct" for c in CLASSES), "p99_density_pct", "gini_pct"]


def spatial_summary(tab: pd.DataFrame, comparisons: list[tuple[str, str]], n_resamples: int,
                    seed: int) -> list[dict]:
    """Mean paired change per level with a 95% BCa interval, for every summary metric and comparison."""
    rows = []
    for cond, ref in comparisons:
        p = paired_spatial(tab, cond, ref)
        for level, g in p.groupby("level"):
            for metric in SUMMARY_METRICS:
                d = g[metric].to_numpy(float)
                d = d[np.isfinite(d)]  # a class with no NOx in the reference run has no percent change
                if len(d) < 3:
                    continue
                lo, hi = bca_ci(d, 0.95, n_resamples, seed)
                rows.append({"condition": cond, "reference": ref, "level": level, "metric": metric,
                             "unit": "pp" if metric.endswith("_pp") else "pct", "n": int(len(d)),
                             "mean": float(d.mean()), "ci95_low": lo, "ci95_high": hi})
    return rows


def composition_share(tab: pd.DataFrame, cond: str, ref: str, n_resamples: int, seed: int) -> list[dict]:
    """Share of the edge-NOx change from ``ref`` to ``cond`` explained by the road-class mix of vehicle-hours:
    counterfactual NOx = sum over classes of cond's vehicle-hours x ref's NOx per vehicle-hour (same level, seed).
    Ratio of level means, with a percentile bootstrap interval over seeds."""
    j = _join(tab, cond, ref)
    cf = np.zeros(len(j))
    for c in ALL_CLASSES:
        vh_b = j[f"veh_h_{c}_b"].to_numpy()
        rate = np.divide(j[f"nox_g_{c}_b"].to_numpy(), vh_b, out=np.zeros(len(j)), where=vh_b > 0)
        cf += j[f"veh_h_{c}_a"].to_numpy() * rate
    j = j.assign(explained_g=j["edge_nox_total_g_b"] - cf,
                 change_g=j["edge_nox_total_g_b"] - j["edge_nox_total_g_a"])
    rng = np.random.default_rng(seed)
    rows = []
    for level, g in j.groupby(level="level"):
        num, den = g.explained_g.to_numpy(), g.change_g.to_numpy()
        boot = []
        for _ in range(n_resamples):
            k = rng.integers(0, len(g), len(g))
            boot.append(num[k].mean() / den[k].mean())
        lo, hi = np.percentile(boot, [2.5, 97.5])
        rows.append({"condition": cond, "reference": ref, "level": level, "n": int(len(g)),
                     "explained_share": float(num.mean() / den.mean()), "ci95_low": float(lo), "ci95_high": float(hi),
                     "edge_nox_change_g_mean": float(den.mean()), "explained_g_mean": float(num.mean())})
    return rows
