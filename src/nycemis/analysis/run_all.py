"""M7 in one call: confirmatory analysis, spatial side effects, figures, claims ledger.

Added after the adversarial review (docs/DEVIATIONS.md #17, all exploratory): the spatial summary with intervals and
the composition decomposition (``spatial_summary.json``); the legacy-metric replication on this experiment's seeds
(``results/legacy_audit/replication_<experiment>.json``, baseline sum from the static run's tripinfo total); the recount of the legacy rule's route changes
(``results/legacy_audit/route_change_recount.json``, DEVIATIONS #18).
"""

from __future__ import annotations

import json

import pandas as pd
import sumolib

from nycemis.analysis import figures as fg
from nycemis.analysis.claims import write_claims
from nycemis.analysis.confirmatory import PCS, analyze
from nycemis.analysis.pilot import load_runs
from nycemis.analysis.spatial import composition_share, paired_spatial, spatial_summary, spatial_table
from nycemis.config import base_config
from nycemis.experiments.plan import exp_dir
from nycemis.legacy.replicate import LEGACY_HORIZON_S, legacy_metric_drop_pct, matched_drop_pct
from nycemis.network.build import net_path
from nycemis.paths import models_dir, rel, repo_root, results_dir
from nycemis.sim.netinfo import load_netinfo

CONDITIONS = ["static", "tt_adaptive", "random_reroute", "eco_reactive", "eco_ml", "legacy_ml"]
SPATIAL_COMPARISONS = [("eco_ml", "static"), ("eco_ml", "tt_adaptive"), ("eco_reactive", "static"),
                       ("tt_adaptive", "static"), ("random_reroute", "static")]


def legacy_replication_test(runs: pd.DataFrame, experiment: str) -> dict:
    """The legacy-metric replication (``pilot._legacy_replication``) on this experiment's seeds. Static test runs do
    not record the per-step series, so the legacy metric's baseline sum (all of the static run's NOx) is the static
    run's tripinfo total, which the reconciliation audit matches to the per-step total within its tolerance; the
    controlled run's sum up to the legacy horizon comes from the legacy_ml run's per-step series as before."""
    rows = []
    for (level, seed), g in runs[runs.label == "legacy_ml"].groupby(["level", "seed"]):
        base = runs[(runs.label == "static") & (runs.level == level) & (runs.seed == seed)]
        if base.empty:
            continue
        base_mg = 1000.0 * float(base.total_nox_g.iloc[0])
        c_series = pd.read_parquet(exp_dir(experiment) / g.run_id.iloc[0] / "network_series.parquet")
        rows.append({"label": "legacy_ml", "level": level, "seed": int(seed),
                     "legacy_metric_drop_pct": legacy_metric_drop_pct(pd.DataFrame({"nox_mg": [base_mg]}), c_series,
                                                                      LEGACY_HORIZON_S),
                     "matched_drop_pct": matched_drop_pct(float(base.total_nox_g.iloc[0]),
                                                          float(g.total_nox_g.iloc[0]))})
    tab = pd.DataFrame(rows)
    summary = {}
    for level, g in tab.groupby("level"):
        summary[f"legacy_ml/{level}"] = {
            "n": int(len(g)),
            **{f"{k}_{f}": float(getattr(g[k], f)()) for k in ("legacy_metric_drop_pct", "matched_drop_pct")
               for f in ("mean", "min", "max")}}
    return {"horizon_s": LEGACY_HORIZON_S, "baseline_sum": "static tripinfo total", "per_run": rows,
            "summary": summary}


def legacy_recount_summary() -> dict | None:
    """Route-change rate of the legacy rule with the corrected counter (``legacy_recount``: the pilot's C5 runs
    again); the NOx totals must equal the pilot's, since only the counter changed."""
    if not (exp_dir("legacy_recount") / "plan.json").is_file():
        return None
    rc = load_runs("legacy_recount")
    pilot = load_runs("pilot")
    p = pilot[pilot.label == "legacy_ml"][["level", "seed", "total_nox_g", "route_change_rate"]]
    j = rc.merge(p, on=["level", "seed"], how="inner", suffixes=("", "_pilot"))
    out = {"runs": int(len(rc)), "matched_to_pilot": int(len(j)),
           "nox_identical_to_pilot": bool(len(j) == len(rc) and (j.total_nox_g == j.total_nox_g_pilot).all()),
           "per_level": {}}
    for level, g in j.groupby("level"):
        out["per_level"][level] = {
            "n": int(len(g)), "reroute_calls": int(g.n_reroutes.sum()), "route_changes": int(g.route_changes.sum()),
            "route_change_rate": float(g.route_changes.sum() / g.n_reroutes.sum()),
            "old_counter_rate_mean": float(g.route_change_rate_pilot.mean())}
    calls = sum(v["reroute_calls"] for v in out["per_level"].values())
    out["route_change_rate_all"] = (sum(v["route_changes"] for v in out["per_level"].values()) / calls
                                    if calls else float("nan"))
    return out


def run(experiment: str, scenario: str, model_id: str | None) -> list[str]:
    written: list[str] = []
    res = analyze(experiment)
    runs = load_runs(experiment)
    info = load_netinfo(str(net_path(scenario)))
    out = results_dir() / experiment
    figdir = repo_root() / "paper" / "figures"
    figdir.mkdir(parents=True, exist_ok=True)

    tab = spatial_table(experiment, runs, info.n)
    tab.to_csv(out / "spatial.csv", index=False)
    present = [c for c in CONDITIONS if c in set(runs.label)]
    sp = {c: paired_spatial(tab, c, "static").assign(condition=c) for c in present if c != "static"}
    if sp:
        pd.concat(sp.values()).to_csv(out / "spatial_paired_vs_static.csv", index=False)
    written += [rel(out / "analysis.json"), rel(out / "spatial.csv")]
    a = base_config().analysis
    comps = [(c, r) for c, r in SPATIAL_COMPARISONS if {c, r} <= set(present)]
    summary = {"paired": spatial_summary(tab, comps, a.bootstrap_resamples, a.bootstrap_seed),
               "composition": [row for c, r in comps if c == "eco_ml"
                               for row in composition_share(tab, c, r, a.bootstrap_resamples, a.bootstrap_seed)]}
    (out / "spatial_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    written.append(rel(out / "spatial_summary.json"))
    legacy_dir = results_dir() / "legacy_audit"
    if {"legacy_ml", "static"} <= set(present):
        rep = legacy_replication_test(runs, experiment)
        path = legacy_dir / f"replication_{experiment}.json"
        path.write_text(json.dumps(rep, indent=2, default=float) + "\n", encoding="utf-8")
        written.append(rel(path))
    recount = legacy_recount_summary()
    if recount:
        path = legacy_dir / "route_change_recount.json"
        path.write_text(json.dumps(recount, indent=2) + "\n", encoding="utf-8")
        written.append(rel(path))

    for pc, cond, ref, _ in PCS:
        if cond in present and ref in present:
            written.append(rel(fg.slope_plot(runs, cond, ref, figdir / f"slope_{pc}_{cond}_vs_{ref}.png")))
    rows = [{**r, "label": f"{r['pc']} {r['condition']} vs {r['reference']} ({r['level']})"}
            for r in res["confirmatory"]]
    written.append(rel(fg.forest_plot(rows, figdir / "forest_confirmatory.png",
                                      "Confirmatory comparisons: total NOx (valid pairs)")))
    expl = [{**r, "label": f"{r['condition']} vs {r['reference']} ({r['level']})"} for r in res["exploratory"]
            if r["metric"] == "total_nox_g" and r["reference"] == "static"]
    if expl:
        written.append(rel(fg.forest_plot(expl, figdir / "forest_vs_static.png",
                                          "All conditions vs static: total NOx (exploratory)")))
    written.append(rel(fg.road_class_bars(tab, present, figdir / "road_class_shares.png")))
    net = sumolib.net.readNet(str(net_path(scenario)))
    for level in ("moderate", "heavy"):
        if {"eco_ml", "static"} <= set(present):
            written.append(rel(fg.edge_difference_map(experiment, runs, "eco_ml", "static", level, info, net,
                                                      figdir / f"map_eco_ml_minus_static_{level}.png")))
    sel = results_dir() / "validation" / "selection.json"
    if sel.is_file():
        s = json.loads(sel.read_text(encoding="utf-8"))
        written.append(rel(fg.pareto_plot({c: s[c]["per_level"] for c in ("eco_reactive", "eco_ml")},
                                          figdir / "pareto_alpha.png")))
    if model_id:
        mpath = models_dir() / scenario / model_id / "metrics.json"
        if mpath.is_file():
            m = json.loads(mpath.read_text(encoding="utf-8"))
            written.append(rel(fg.skill_plot(m["bootstrap"], figdir / "forecast_skill.png")))
    written += write_claims(experiment)
    return written
