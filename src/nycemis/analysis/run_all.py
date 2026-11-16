"""M7 in one call: confirmatory analysis, spatial side effects, figures, claims ledger."""

from __future__ import annotations

import json

import pandas as pd
import sumolib

from nycemis.analysis import figures as fg
from nycemis.analysis.claims import write_claims
from nycemis.analysis.confirmatory import PCS, analyze
from nycemis.analysis.pilot import load_runs
from nycemis.analysis.spatial import paired_spatial, spatial_table
from nycemis.network.build import net_path
from nycemis.paths import models_dir, rel, repo_root, results_dir
from nycemis.sim.netinfo import load_netinfo

CONDITIONS = ["static", "tt_adaptive", "random_reroute", "eco_reactive", "eco_ml", "legacy_ml"]


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
