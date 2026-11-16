"""Pilot analysis (docs/SPECIFICATION.md M4): runtimes, validity, paired variance, power, budget, alpha = 0 sanity, and the
legacy-protocol replication that completes the audit. Writes ``results/pilot/pilot_summary.json`` and
``results/legacy_audit/replication.json``; the documents that cite these numbers are rendered from them.
"""

from __future__ import annotations

import json
import math
import shutil

import numpy as np
import pandas as pd

from nycemis.analysis.stats import pct_change
from nycemis.config import base_config
from nycemis.experiments.plan import exp_dir, load_plan
from nycemis.experiments.power import confirmatory_n, n_required
from nycemis.legacy.replicate import LEGACY_HORIZON_S, legacy_metric_drop_pct, matched_drop_pct
from nycemis.paths import results_dir

REF = "static"
LEVELS = ("light", "moderate", "heavy")
POWER_COMPARISONS = (("eco_reactive", "static"), ("eco_reactive", "tt_adaptive"), ("legacy_ml", "static"),
                     ("random_reroute", "static"), ("tt_adaptive", "static"), ("eco_reactive_a0", "static"),
                     ("eco_reactive", "random_reroute"))
ALPHA0_TOLERANCE = 0.05
RECON_TOLERANCE_PILOT = 0.005  # DEVIATIONS #9


def load_runs(experiment: str) -> pd.DataFrame:
    doc = load_plan(experiment)
    rows = []
    for r in doc["runs"]:
        d = exp_dir(experiment) / r["run_id"]
        if not (d / "DONE").is_file():
            continue
        m = json.loads((d / "run_metrics.json").read_text(encoding="utf-8"))
        spec = r["spec"]
        rows.append({"run_id": r["run_id"], "label": r["label"], "level": spec["level"], "seed": spec["seed"],
                     "controller": spec["controller"], **{k: v for k, v in m.items() if not isinstance(v, dict)}})
    return pd.DataFrame(rows)


def paired_deltas(df: pd.DataFrame, a: str, b: str, metric: str = "total_nox_g", valid_only: bool = True
                  ) -> pd.DataFrame:
    x = df[df.label == a].set_index(["level", "seed"])
    y = df[df.label == b].set_index(["level", "seed"])
    j = x[[metric, "valid"]].join(y[[metric, "valid"]], lsuffix="_a", rsuffix="_b", how="inner")
    if valid_only:
        j = j[j.valid_a & j.valid_b]
    j["delta_pct"] = pct_change(j[f"{metric}_a"].to_numpy(), j[f"{metric}_b"].to_numpy())
    return j.reset_index()


def _legacy_replication(df: pd.DataFrame, experiment: str) -> dict:
    rows = []
    for label in ("legacy_ml", "legacy_ml_literal"):
        for (level, seed), g in df[df.label == label].groupby(["level", "seed"]):
            base = df[(df.label == REF) & (df.level == level) & (df.seed == seed)]
            if base.empty:
                continue
            b_series = pd.read_parquet(exp_dir(experiment) / base.run_id.iloc[0] / "network_series.parquet")
            c_series = pd.read_parquet(exp_dir(experiment) / g.run_id.iloc[0] / "network_series.parquet")
            rows.append({
                "label": label, "level": level, "seed": int(seed),
                "legacy_metric_drop_pct": legacy_metric_drop_pct(b_series, c_series, LEGACY_HORIZON_S),
                "matched_drop_pct": matched_drop_pct(float(base.total_nox_g.iloc[0]), float(g.total_nox_g.iloc[0])),
                "route_change_rate": float(g.route_change_rate.iloc[0]),
                "reroute_calls": int(g.n_reroutes.iloc[0]),
                "flag_share": float(g.legacy_flag_share.iloc[0]) if "legacy_flag_share" in g else float("nan"),
                "static_sim_end_s": float(base.sim_end_s.iloc[0]),
            })
    tab = pd.DataFrame(rows)
    summary = {}
    for (label, level), g in tab.groupby(["label", "level"]):
        summary[f"{label}/{level}"] = {
            "n": int(len(g)),
            "legacy_metric_drop_pct_mean": float(g.legacy_metric_drop_pct.mean()),
            "legacy_metric_drop_pct_min": float(g.legacy_metric_drop_pct.min()),
            "legacy_metric_drop_pct_max": float(g.legacy_metric_drop_pct.max()),
            "matched_drop_pct_mean": float(g.matched_drop_pct.mean()),
            "matched_drop_pct_min": float(g.matched_drop_pct.min()),
            "matched_drop_pct_max": float(g.matched_drop_pct.max()),
            "route_change_rate_mean": float(g.route_change_rate.mean()),
            "flag_share_mean": float(g.flag_share.mean()),
        }
    legacy_eval = json.loads((results_dir() / "legacy_audit" / "legacy_rf_eval.json").read_text(encoding="utf-8"))
    return {"horizon_s": LEGACY_HORIZON_S, "per_run": rows, "summary": summary, "legacy_rf": legacy_eval}


def _budget(df: pd.DataFrame, n_conf: int, workers: int) -> dict:
    med = df.groupby("label").wall_s.median().to_dict()
    eco = med.get("eco_reactive", float("nan"))
    plan = {
        "M5 dataset (4 policies x 3 levels x 24 train seeds)": (288, np.mean([med.get("static"), med.get("tt_adaptive"),
                                                                              med.get("random_reroute"), eco])),
        "M5 alpha sweep (5 alpha x 2 controllers x 3 levels x 12 validation seeds)": (360, eco),
        "M5 references and placebo calibration (validation seeds)": (180, eco),
        f"M6 confirmatory (6 conditions x 3 levels x n={n_conf})": (
            18 * n_conf, np.mean([med.get(k, eco) for k in ("static", "tt_adaptive", "random_reroute",
                                                              "eco_reactive", "eco_reactive", "legacy_ml")])),
    }
    rows = {k: {"runs": n, "median_s_per_run": float(s), "core_hours": n * float(s) / 3600} for k, (n, s) in plan.items()}
    core_h = sum(v["core_hours"] for v in rows.values())
    run_dirs = [d for d in exp_dir("pilot").iterdir() if d.is_dir()]
    disk_mb_per_run = np.median([sum(f.stat().st_size for f in d.iterdir()) for d in run_dirs]) / 1e6
    n_runs = sum(v["runs"] for v in rows.values())
    return {"median_wall_s_by_condition": {k: float(v) for k, v in med.items()}, "plan": rows,
            "total_core_hours": core_h, "workers": workers, "wall_clock_hours": core_h / workers,
            "disk_gb_estimate": float(n_runs * disk_mb_per_run / 1e3 + 288 * 0.03),
            "free_disk_gb": shutil.disk_usage(results_dir()).free / 1e9}


def analyze(experiment: str = "pilot") -> dict:
    cfg = base_config()
    df = load_runs(experiment)
    out: dict = {"experiment": experiment, "runs_done": int(len(df)), "planned": len(load_plan(experiment)["runs"])}
    out["validity"] = (df.groupby(["label", "level"]).valid.agg(["sum", "count"]).reset_index()
                       .rename(columns={"sum": "valid", "count": "runs"}).to_dict("records"))
    out["recon_max_abs"] = float(df.recon_rel_diff.abs().max())
    out["recon_within_pilot_tolerance"] = bool(out["recon_max_abs"] <= RECON_TOLERANCE_PILOT)

    deltas = {}
    sds = []
    for a, b in POWER_COMPARISONS:
        for metric in ("total_nox_g", "mean_tt_s"):
            pdf = paired_deltas(df, a, b, metric)
            for level in LEVELS:
                d = pdf[pdf.level == level].delta_pct.to_numpy()
                if len(d) < 2:
                    continue
                entry = {"n": int(len(d)), "mean_pct": float(d.mean()), "sd_pct": float(d.std(ddof=1)),
                         "min_pct": float(d.min()), "max_pct": float(d.max())}
                deltas[f"{a} vs {b} | {metric} | {level}"] = entry
                if metric == "total_nox_g":
                    sds.append(entry["sd_pct"])
    out["paired_deltas"] = deltas
    sd_max = float(max(sds))
    alpha_adj = cfg.analysis.familywise_alpha / cfg.analysis.n_confirmatory_tests
    n_sup, curve_sup = n_required("superiority", sd_max, cfg.analysis.sesoi_pct, alpha_adj)
    n_eq, curve_eq = n_required("equivalence", sd_max, cfg.analysis.sesoi_pct, alpha_adj)
    n_power = None if (n_sup is None or n_eq is None) else max(n_sup, n_eq)
    n_conf = confirmatory_n(n_power, cfg.seeds.test_n_min, cfg.seeds.test_n_max)
    out["power"] = {"sd_pct_used": sd_max, "alpha_adjusted": alpha_adj, "sesoi_pct": cfg.analysis.sesoi_pct,
                    "n_superiority": n_sup, "n_equivalence": n_eq, "n_power": n_power, "n_confirmatory": n_conf,
                    "curve_superiority": curve_sup, "curve_equivalence": curve_eq,
                    "sims_per_n": 2000, "seed": 20261115}

    a0 = {}
    for level in LEVELS:
        x = df[(df.label == "eco_reactive_a0") & (df.level == level)].mean_tt_s.mean()
        y = df[(df.label == "tt_adaptive") & (df.level == level)].mean_tt_s.mean()
        a0[level] = {"eco_reactive_a0_mean_tt_s": float(x), "tt_adaptive_mean_tt_s": float(y),
                     "rel_diff": float((x - y) / y), "within_5pct": bool(abs(x - y) / y <= ALPHA0_TOLERANCE)}
    out["alpha0_sanity"] = a0
    workers = cfg.execution.workers or 23
    out["budget"] = _budget(df, n_conf, workers)
    rep = _legacy_replication(df, experiment)
    pdir = results_dir() / "pilot"
    pdir.mkdir(parents=True, exist_ok=True)
    df.to_csv(pdir / "pilot_runs.csv", index=False)
    (pdir / "pilot_summary.json").write_text(json.dumps(out, indent=2, default=float) + "\n", encoding="utf-8")
    (results_dir() / "legacy_audit" / "replication.json").write_text(json.dumps(rep, indent=2, default=float) + "\n",
                                                                    encoding="utf-8")
    return out


def ceil_hours(h: float) -> int:
    return int(math.ceil(h))
