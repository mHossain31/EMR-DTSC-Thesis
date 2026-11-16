"""Frozen confirmatory analysis (docs/SPECIFICATION.md 4.2, 4.7).

PC1 legacy_ml vs static (TOST +-2%), PC2 eco_ml vs static (Wilcoxon), PC3 eco_ml vs tt_adaptive (Wilcoxon),
PC4 eco_ml vs eco_reactive (TOST +-2%), each at the three demand levels: one Holm family of 12 tests. Primary
analysis on pairs where both runs are valid; sensitivity analysis on all pairs. Everything else is exploratory.
"""

from __future__ import annotations

import json

import pandas as pd

from nycemis.analysis.pilot import load_runs, paired_deltas
from nycemis.analysis.stats import holm, paired
from nycemis.config import base_config
from nycemis.paths import results_dir

LEVELS = ("light", "moderate", "heavy")
PCS = (
    ("PC1", "legacy_ml", "static", "equivalence"),
    ("PC2", "eco_ml", "static", "superiority"),
    ("PC3", "eco_ml", "tt_adaptive", "superiority"),
    ("PC4", "eco_ml", "eco_reactive", "equivalence"),
)
EXPLORATORY_METRICS = ("total_nox_g", "total_co2_kg", "mean_tt_s", "p95_tt_s", "mean_timeloss_s", "vkm_total",
                       "nox_mg_per_vkm", "mean_depart_delay_s")
EXPLORATORY_COMPARISONS = (("tt_adaptive", "static"), ("random_reroute", "static"), ("eco_reactive", "static"),
                           ("eco_ml", "static"), ("legacy_ml", "static"), ("eco_ml", "random_reroute"),
                           ("eco_reactive", "tt_adaptive"), ("eco_ml", "tt_adaptive"), ("eco_ml", "eco_reactive"))


def _tests(df: pd.DataFrame, valid_only: bool) -> list[dict]:
    a = base_config().analysis
    rows = []
    for pc, cond, ref, kind in PCS:
        pdf = paired_deltas(df, cond, ref, "total_nox_g", valid_only=valid_only)
        for level in LEVELS:
            d = pdf[pdf.level == level].delta_pct.to_numpy()
            res = paired(d, a.sesoi_pct if kind == "equivalence" else None, a.bootstrap_resamples,
                         a.bootstrap_seed)
            p = res.p_tost if kind == "equivalence" else res.p_wilcoxon
            rows.append({"pc": pc, "condition": cond, "reference": ref, "kind": kind, "level": level,
                         "p_test": p, **res.as_dict()})
    reject, adj = holm([r["p_test"] for r in rows], a.familywise_alpha)
    for r, rej, pa in zip(rows, reject, adj, strict=True):
        r["p_holm"] = pa
        r["reject_holm"] = rej
        if r["kind"] == "equivalence":
            r["outcome"] = "equivalent within +-2%" if rej else "equivalence not shown"
        else:
            r["outcome"] = ("reduction" if r["mean_pct"] < 0 else "increase") if rej else "no significant difference"
    return rows


def _exploratory(df: pd.DataFrame) -> list[dict]:
    a = base_config().analysis
    rows = []
    for cond, ref in EXPLORATORY_COMPARISONS:
        for metric in EXPLORATORY_METRICS:
            pdf = paired_deltas(df, cond, ref, metric)
            for level in LEVELS:
                d = pdf[pdf.level == level].delta_pct.to_numpy()
                if len(d) < 3:
                    continue
                res = paired(d, None, a.bootstrap_resamples, a.bootstrap_seed)
                rows.append({"condition": cond, "reference": ref, "metric": metric, "level": level,
                             **res.as_dict()})
    return rows


def _invalid_counts(df: pd.DataFrame) -> list[dict]:
    g = df.groupby(["label", "level"])
    return (g.valid.agg(lambda s: int((~s.astype(bool)).sum())).rename("invalid").to_frame()
            .join(g.size().rename("runs")).reset_index().to_dict("records"))


def analyze(experiment: str = "confirmatory") -> dict:
    df = load_runs(experiment)
    out = {"experiment": experiment, "runs": int(len(df)),
           "confirmatory": _tests(df, valid_only=True),
           "sensitivity_all_pairs": _tests(df, valid_only=False),
           "exploratory": _exploratory(df), "invalid_runs": _invalid_counts(df),
           "route_change_rate": df.groupby(["label", "level"]).route_change_rate.mean().reset_index()
           .to_dict("records")}
    d = results_dir() / experiment
    d.mkdir(parents=True, exist_ok=True)
    (d / "analysis.json").write_text(json.dumps(out, indent=2, default=float) + "\n", encoding="utf-8")
    pd.DataFrame(out["confirmatory"]).to_csv(d / "confirmatory_tests.csv", index=False)
    pd.DataFrame(out["exploratory"]).to_csv(d / "exploratory.csv", index=False)
    df.to_csv(d / "runs.csv", index=False)
    return out
