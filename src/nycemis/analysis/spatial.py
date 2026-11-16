"""Spatial side effects (RQ5, docs/SPECIFICATION.md 4.5): NOx share by road class, p99 5-minute edge NOx density, and the Gini
coefficient of per-edge cumulative NOx, per run; then paired changes against a reference condition.

The per-edge tables cover non-internal edges only (junction lanes are not attributed to any edge).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from nycemis.analysis.stats import pct_change
from nycemis.experiments.plan import exp_dir
from nycemis.sim.netinfo import ROAD_CLASS_CODES

CLASSES = [c for c in ROAD_CLASS_CODES if c != "other"]


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
    shares = cum.groupby("road_class").nox_mg.sum() / total
    per_edge = np.zeros(n_edges)
    per_edge[cum.edge_idx.to_numpy()] = cum.nox_mg.to_numpy()
    return {**{f"share_{c}": float(shares.get(c, 0.0)) for c in CLASSES},
            "p99_5min_nox_dens_mg_per_lane_m": float(np.percentile(five.nox_dens_mg_per_lane_m, 99)),
            "gini_edge_nox": gini(per_edge), "edge_nox_total_g": float(total / 1000.0)}


def spatial_table(experiment: str, runs: pd.DataFrame, n_edges: int) -> pd.DataFrame:
    rows = [{"run_id": r.run_id, "label": r.label, "level": r.level, "seed": r.seed,
             **run_spatial(experiment, r.run_id, n_edges)} for r in runs.itertuples()]
    return pd.DataFrame(rows)


def paired_spatial(tab: pd.DataFrame, cond: str, ref: str) -> pd.DataFrame:
    """Paired differences: shares in percentage points, the p99 density and Gini in percent change."""
    a = tab[tab.label == cond].set_index(["level", "seed"])
    b = tab[tab.label == ref].set_index(["level", "seed"])
    j = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
    out = pd.DataFrame(index=j.index)
    for c in CLASSES:
        out[f"share_{c}_pp"] = 100 * (j[f"share_{c}_a"] - j[f"share_{c}_b"])
    out["p99_density_pct"] = pct_change(j["p99_5min_nox_dens_mg_per_lane_m_a"], j["p99_5min_nox_dens_mg_per_lane_m_b"])
    out["gini_pct"] = pct_change(j["gini_edge_nox_a"], j["gini_edge_nox_b"])
    return out.reset_index()
