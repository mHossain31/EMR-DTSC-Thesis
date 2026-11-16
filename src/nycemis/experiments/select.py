"""Select alpha* (per controller) and the placebo eta on validation seeds (docs/SPECIFICATION.md 4.3, M5).

alpha* rule, fixed before any test seed runs: an alpha is feasible if, at every demand level, the mean travel time
over the validation seeds is at most 5% above tt_adaptive's at that level. Among feasible alphas, alpha* minimises
the mean over levels of (mean total NOx at alpha) / (mean total NOx of tt_adaptive). The ratio puts the three
levels on one scale, so the heavy level's larger totals do not decide alone. alpha* is chosen separately for
eco_reactive and eco_ml.

eta rule: among the eta grid, the eta whose route-change rate (mean over validation runs) is closest to eco_ml's at
alpha*_ml, by the mean over levels of the absolute difference.
"""

from __future__ import annotations

import json
import re

import pandas as pd

from nycemis.analysis.pilot import load_runs
from nycemis.config import base_config
from nycemis.paths import results_dir

LEVELS = ("light", "moderate", "heavy")


def _alpha_table(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    ref = df[df.label == "tt_adaptive"].groupby("level")[["total_nox_g", "mean_tt_s"]].mean()
    rows = []
    for label, g in df[df.label.str.startswith(prefix + "_a")].groupby("label"):
        alpha = float(re.search(r"_a([0-9.]+)$", label).group(1))
        m = g.groupby("level")[["total_nox_g", "mean_tt_s", "route_change_rate", "valid"]].mean()
        for level in LEVELS:
            if level not in m.index:
                continue
            rows.append({"controller": prefix, "alpha": alpha, "level": level,
                         "nox_ratio": float(m.loc[level, "total_nox_g"] / ref.loc[level, "total_nox_g"]),
                         "tt_ratio": float(m.loc[level, "mean_tt_s"] / ref.loc[level, "mean_tt_s"]),
                         "route_change_rate": float(m.loc[level, "route_change_rate"]),
                         "valid_share": float(m.loc[level, "valid"]), "runs": int((g.level == level).sum())})
    return pd.DataFrame(rows)


def choose_alpha(tab: pd.DataFrame, tt_budget: float) -> dict:
    agg = tab.groupby("alpha").agg(nox_ratio_mean=("nox_ratio", "mean"), tt_ratio_max=("tt_ratio", "max"),
                                   levels=("level", "count")).reset_index()
    agg["feasible"] = (agg.tt_ratio_max <= 1.0 + tt_budget) & (agg.levels == len(LEVELS))
    feas = agg[agg.feasible]
    if feas.empty:
        raise RuntimeError("no alpha satisfies the travel-time budget at every level")
    best = feas.sort_values(["nox_ratio_mean", "alpha"]).iloc[0]
    return {"alpha_star": float(best.alpha), "table": agg.to_dict("records")}


def select(experiment: str = "validation") -> dict:
    df = load_runs(experiment)
    budget = base_config().analysis.alpha_star_tt_budget_pct / 100.0
    out = {"experiment": experiment, "tt_budget": budget}
    tabs = {}
    for prefix in ("eco_reactive", "eco_ml"):
        tabs[prefix] = _alpha_table(df, prefix)
        out[prefix] = choose_alpha(tabs[prefix], budget)
        out[prefix]["per_level"] = tabs[prefix].to_dict("records")
    a_ml = out["eco_ml"]["alpha_star"]
    target = tabs["eco_ml"][tabs["eco_ml"].alpha == a_ml].set_index("level").route_change_rate
    rows = []
    for label, g in df[df.label.str.startswith("random_reroute_e")].groupby("label"):
        eta = float(label.rsplit("_e", 1)[1])
        rate = g.groupby("level").route_change_rate.mean()
        diff = float((rate - target).abs().reindex(LEVELS).mean())
        rows.append({"eta": eta, "mean_abs_diff": diff, **{f"rate_{lv}": float(rate.get(lv, float("nan")))
                                                          for lv in LEVELS}})
    eta_tab = pd.DataFrame(rows).sort_values(["mean_abs_diff", "eta"])
    out["random_reroute"] = {"eta_star": float(eta_tab.iloc[0].eta), "target_rates": target.to_dict(),
                             "table": eta_tab.to_dict("records")}
    path = results_dir() / "validation" / "selection.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, default=float) + "\n", encoding="utf-8")
    return out
