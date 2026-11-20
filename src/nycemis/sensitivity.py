"""Street-coding sensitivity experiment (docs/SENSITIVITY_PLAN.md; docs/DEVIATIONS.md #21). Exploratory.

Question: does emission-aware rerouting still lower simulated NOx, and still move it onto residential streets, when
Flushing carries New York City's default 25 mph limit and two-way stops at unsignalised minor-street junctions?

The analysis was written and tagged (``sensitivity-v1``) before the test-seed runs of ``sensitivity_posted``. It sits
outside ``nycemis.analysis`` (whose hash the main preregistration froze) and only calls that package's functions:
paired percent changes on valid pairs with 95% BCa intervals and two-sided Wilcoxon p-values (no multiplicity
correction: the experiment is exploratory), the road-class side effects and the composition decomposition. Each
contrast is set beside the same contrast on the original network (the confirmatory runs, same seed numbers); the
difference between networks is a difference of means of independent samples (the demand differs), with a percentile
bootstrap interval. Wording follows the intervals.

Writes ``results/sensitivity_posted/analysis.json``, ``paper/macros_sensitivity.tex``, ``docs/CLAIMS_SENSITIVITY.md``
and ``paper/figures/road_class_shares_posted.png``.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

from nycemis.config import base_config
from nycemis.paths import docs_dir, rel, repo_root, results_dir

EXPERIMENT = "sensitivity_posted"
SCENARIO = "flushing_posted"
ORIGINAL = "confirmatory"
LEVELS = ("light", "moderate", "heavy")
COMPARISONS = (("eco_reactive", "tt_adaptive"), ("eco_reactive", "static"), ("tt_adaptive", "static"))
METRICS = ("total_nox_g", "total_co2_kg", "mean_tt_s", "p95_tt_s", "vkm_total", "mean_depart_delay_s")
SPATIAL_COMPARISONS = [("eco_reactive", "static"), ("eco_reactive", "tt_adaptive")]
NAMES = {"static": "no rerouting", "tt_adaptive": "travel-time rerouting", "eco_reactive": "measured-emission rerouting"}
RESID = "residential/service"


def between_networks(d_new: np.ndarray, d_old: np.ndarray, n_resamples: int, seed: int) -> dict:
    """Mean paired change on the patched network minus that on the original, with a 95% percentile bootstrap
    interval (independent resampling of the two sets of seeds)."""
    rng = np.random.default_rng(seed)
    boot = [rng.choice(d_new, len(d_new)).mean() - rng.choice(d_old, len(d_old)).mean() for _ in range(n_resamples)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"diff": float(d_new.mean() - d_old.mean()), "ci95_low": float(lo), "ci95_high": float(hi)}


def contrasts(new: pd.DataFrame, old: pd.DataFrame) -> list[dict]:
    from nycemis.analysis.pilot import paired_deltas
    from nycemis.analysis.stats import paired

    a = base_config().analysis
    rows = []
    for cond, ref in COMPARISONS:
        for metric in METRICS:
            pn, po = paired_deltas(new, cond, ref, metric), paired_deltas(old, cond, ref, metric)
            for level in LEVELS:
                dn = pn[pn.level == level].delta_pct.to_numpy()
                do = po[po.level == level].delta_pct.to_numpy()
                if len(dn) < 3 or len(do) < 3:
                    continue
                rn = paired(dn, None, a.bootstrap_resamples, a.bootstrap_seed).as_dict()
                ro = paired(do, None, a.bootstrap_resamples, a.bootstrap_seed).as_dict()
                rows.append({"condition": cond, "reference": ref, "metric": metric, "level": level,
                             "posted": rn, "original": ro,
                             "between": between_networks(dn, do, a.bootstrap_resamples, a.bootstrap_seed)})
    return rows


def spatial(new: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    from nycemis.analysis.spatial import composition_share, spatial_summary, spatial_table
    from nycemis.network.build import net_path
    from nycemis.sim.netinfo import load_netinfo

    a = base_config().analysis
    info = load_netinfo(str(net_path(SCENARIO)))
    tab_new = spatial_table(EXPERIMENT, new, info.n)
    tab_new.to_csv(results_dir() / EXPERIMENT / "spatial.csv", index=False)
    tab_old = pd.read_csv(results_dir() / ORIGINAL / "spatial.csv")
    out = {}
    for name, tab in (("posted", tab_new), ("original", tab_old)):
        out[name] = {
            "paired": spatial_summary(tab, SPATIAL_COMPARISONS, a.bootstrap_resamples, a.bootstrap_seed),
            "composition": [r for c, ref in SPATIAL_COMPARISONS
                            for r in composition_share(tab, c, ref, a.bootstrap_resamples, a.bootstrap_seed)],
            "resid_share": {f"{lab}/{lvl}": float(v) for (lab, lvl), v in
                            tab.groupby(["label", "level"])[f"share_{RESID}"].mean().items()},
        }
    return out, tab_new


def _find(rows: list[dict], cond: str, ref: str, metric: str, level: str) -> dict | None:
    return next((r for r in rows if (r["condition"], r["reference"], r["metric"], r["level"])
                 == (cond, ref, metric, level)), None)


def nox_sentence(r: dict) -> str:
    """Wording by the intervals: on the patched network, the change and whether its 95% CI excludes zero; then how
    it compares with the original network."""
    p, o, b = r["posted"], r["original"], r["between"]
    if p["ci95_high"] < 0:
        head = f"lower by {abs(p['mean_pct']):.2f}%"
    elif p["ci95_low"] > 0:
        head = f"higher by {p['mean_pct']:.2f}%"
    else:
        head = f"not clearly different (mean {p['mean_pct']:+.2f}%)"
    if b["ci95_high"] < 0:
        tail = "below zero: the change is more negative on the posted-limit network"
    elif b["ci95_low"] > 0:
        tail = "above zero: the change is less negative (or more positive) on the posted-limit network"
    else:
        tail = "an interval that includes zero"
    return (f"At {r['level']} demand on the posted-limit network, total NOx under {NAMES[r['condition']]} is {head} "
            f"vs {NAMES[r['reference']]} (95% CI {p['ci95_low']:+.2f}% to {p['ci95_high']:+.2f}%, n = {p['n']}); "
            f"on the original network the change was {o['mean_pct']:+.2f}% ({o['ci95_low']:+.2f}% to "
            f"{o['ci95_high']:+.2f}%). Posted-limit minus original: {b['diff']:+.2f} points (95% CI "
            f"{b['ci95_low']:+.2f} to {b['ci95_high']:+.2f}), {tail}.")


def _name(*parts: str) -> str:
    words = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six",
             "7": "Seven", "8": "Eight", "9": "Nine"}
    s = "".join(p[:1].upper() + p[1:] for p in re.split(r"[^A-Za-z0-9]+", "-".join(parts)) if p)
    return "".join(words.get(ch, ch) for ch in s)


def write_macros(res: dict) -> str:
    m: dict[str, str] = {}
    for r in res["contrasts"]:
        stem = _name("Sens", r["condition"], "vs", r["reference"], r["metric"], r["level"])
        m[stem + "Posted"] = f"{r['posted']['mean_pct']:+.1f}"
        m[stem + "PostedCI"] = f"{r['posted']['ci95_low']:+.1f} to {r['posted']['ci95_high']:+.1f}"
        m[stem + "Original"] = f"{r['original']['mean_pct']:+.1f}"
        m[stem + "Diff"] = f"{r['between']['diff']:+.1f}"
        m[stem + "DiffCI"] = f"{r['between']['ci95_low']:+.1f} to {r['between']['ci95_high']:+.1f}"
    for net in ("posted", "original"):
        sp = res["spatial"][net]
        for x in sp["paired"]:
            if x["metric"] in (f"nox_{RESID}_pct", f"share_{RESID}_pp", "edge_nox_pct"):
                key = _name("Sens", net, x["condition"], "vs", x["reference"], x["metric"], x["level"])
                m[key] = f"{x['mean']:+.0f}" if x["metric"] != f"share_{RESID}_pp" else f"{x['mean']:+.1f}"
        for c in sp["composition"]:
            m[_name("Sens", net, "composition", c["condition"], "vs", c["reference"], c["level"])] = \
                f"{100 * c['explained_share']:.0f}"
    lv = res["levels"]
    for level, v in lv.items():
        m[_name("SensDensity", level)] = f"{v['density_per_h_km']:g}"
    m["SensJunctionsStop"] = f"{res['network']['junctions_stop_controlled']}"
    m["SensEdgesSpeedChanged"] = f"{res['network']['edges_speed_changed']}"
    m["SensEdgesTagged"] = f"{res['network']['edges_kept_osm_tagged_speed']}"
    m["SensInvalidRuns"] = f"{sum(x['invalid'] for x in res['invalid_runs'])}"
    lines = ["% Generated by `python -m nycemis sensitivity`; do not edit by hand."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(m.items())]
    out = repo_root() / "paper" / "macros_sensitivity.tex"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rel(out)


def write_claims(res: dict) -> str:
    src = rel(results_dir() / EXPERIMENT / "analysis.json")
    lines = ["# Claims ledger: street-coding sensitivity experiment", "",
             "Generated by `python -m nycemis sensitivity`; do not edit by hand. Exploratory, specified before the runs "
             "(docs/SENSITIVITY_PLAN.md, tag `sensitivity-v1`). Simulated tailpipe emissions only.", "",
             "| ID | Claim | Source |", "|---|---|---|"]
    i = 0
    for cond, ref in COMPARISONS[:2]:
        for level in LEVELS:
            r = _find(res["contrasts"], cond, ref, "total_nox_g", level)
            if r:
                i += 1
                lines.append(f"| SN{i} | {nox_sentence(r)} | `{src}` |")
    for level in LEVELS:
        r = _find(res["contrasts"], "eco_reactive", "tt_adaptive", "mean_tt_s", level)
        if r:
            i += 1
            p = r["posted"]
            lines.append(f"| SN{i} | At {level} demand on the posted-limit network, mean travel time under measured-"
                         f"emission rerouting changed by {p['mean_pct']:+.2f}% vs travel-time rerouting (95% CI "
                         f"{p['ci95_low']:+.2f}% to {p['ci95_high']:+.2f}%; original network "
                         f"{r['original']['mean_pct']:+.2f}%). | `{src}` |")
    for net in ("posted", "original"):
        for x in res["spatial"][net]["paired"]:
            if x["metric"] == f"nox_{RESID}_pct" and x["reference"] == "static":
                i += 1
                lines.append(f"| SN{i} | At {x['level']} demand on the {net} network, NOx on residential/service "
                             f"streets under measured-emission rerouting changed by {x['mean']:+.1f}% vs no rerouting "
                             f"(95% CI {x['ci95_low']:+.1f}% to {x['ci95_high']:+.1f}%). | `{src}` |")
    out = docs_dir() / "CLAIMS_SENSITIVITY.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rel(out)


def analyze_sensitivity() -> list[str]:
    from nycemis.analysis import figures as fg
    from nycemis.analysis.pilot import load_runs
    from nycemis.config import load_yaml
    from nycemis.paths import configs_dir, data_dir

    new, old = load_runs(EXPERIMENT), load_runs(ORIGINAL)
    out_dir = results_dir() / EXPERIMENT
    out_dir.mkdir(parents=True, exist_ok=True)
    sp, tab_new = spatial(new)
    build = json.loads((data_dir() / "networks" / SCENARIO / "network_build.json").read_text(encoding="utf-8"))
    levels = load_yaml(configs_dir() / "demand_levels.yaml")["scenarios"][SCENARIO]["levels"]
    invalid = (new.groupby(["label", "level"]).valid.agg(lambda s: int((~s.astype(bool)).sum()))
               .rename("invalid").reset_index().to_dict("records"))
    res = {"experiment": EXPERIMENT, "original": ORIGINAL, "runs": int(len(new)),
           "network": {k: build[k] for k in ("patch_of", "edges_speed_changed", "edges_kept_osm_tagged_speed",
                                             "junctions_stop_controlled", "net_sha256")},
           "levels": {k: {"density_per_h_km": v["density_per_h_km"]} for k, v in levels.items()},
           "invalid_runs": invalid, "contrasts": contrasts(new, old), "spatial": sp}
    path = out_dir / "analysis.json"
    path.write_text(json.dumps(res, indent=2, default=float) + "\n", encoding="utf-8")
    present = [c for c in ("static", "tt_adaptive", "eco_reactive") if c in set(new.label)]
    fig = fg.road_class_bars(tab_new, present, repo_root() / "paper" / "figures" / "road_class_shares_posted.png")
    return [rel(path), rel(fig), write_macros(res), write_claims(res)]
