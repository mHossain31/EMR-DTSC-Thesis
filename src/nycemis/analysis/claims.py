"""Claims ledger (docs/SPECIFICATION.md M7, M9): every claim, its result file, its numbers and its status.

Sentences are generated from ``results/<experiment>/analysis.json`` with wording fixed by the test outcome, so a
claim can never say more than its interval and Holm-adjusted p-value allow. Confirmatory claims are PC1-PC4;
everything else is labelled exploratory.

Added after the adversarial review (docs/DEVIATIONS.md #17; all exploratory): where a failed equivalence test's
90% interval lies relative to the margin; spatial side effects (RQ5) with intervals and the composition
decomposition; tail travel time and departure delay (with absolute seconds); forecast skill on the test seeds (RQ2);
the legacy-metric replication on the test seeds and the recounted route changes (RQ1).
"""

from __future__ import annotations

import json

import pandas as pd

from nycemis.paths import docs_dir, rel, repo_root, results_dir

NAMES = {"static": "no rerouting (static)", "tt_adaptive": "travel-time rerouting (tt_adaptive)",
         "random_reroute": "the random-rerouting placebo", "eco_reactive": "measured-emission rerouting (eco_reactive)",
         "eco_ml": "forecast-driven eco-rerouting (eco_ml)", "legacy_ml": "the legacy rule (legacy_ml)"}
LEVELS = ("light", "moderate", "heavy")
RESID = "residential/service"


def confirmatory_sentence(r: dict) -> str:
    cond, ref, lvl = NAMES[r["condition"]], NAMES[r["reference"]], r["level"]
    ci95 = f"95% CI {r['ci95_low']:+.2f}% to {r['ci95_high']:+.2f}%"
    if r["kind"] == "equivalence":
        ci90 = f"90% CI {r['ci90_low']:+.2f}% to {r['ci90_high']:+.2f}%"
        margin = f"+-{r['margin_pct']:g}%"
        if r["reject_holm"]:
            return (f"At {lvl} demand, total NOx under {cond} is equivalent to {ref} within {margin} (mean "
                    f"{r['mean_pct']:+.2f}%, {ci90}; Holm-adjusted TOST p = {r['p_holm']:.3g}).")
        return (f"At {lvl} demand, equivalence of {cond} and {ref} within {margin} is not shown (mean "
                f"{r['mean_pct']:+.2f}%, {ci90}; Holm-adjusted TOST p = {r['p_holm']:.3g}).")
    if r["reject_holm"]:
        verb = "lower" if r["mean_pct"] < 0 else "higher"
        return (f"At {lvl} demand, total NOx under {cond} is {verb} than under {ref} by {abs(r['mean_pct']):.2f}% "
                f"on average ({ci95}; Holm-adjusted p = {r['p_holm']:.3g}).")
    return (f"At {lvl} demand, total NOx under {cond} does not differ significantly from {ref} (mean "
            f"{r['mean_pct']:+.2f}%, {ci95}; Holm-adjusted p = {r['p_holm']:.3g}).")


def equivalence_direction(r: dict) -> str | None:
    """For an equivalence test that did not reject: where its 90% interval lies relative to the margin. Exploratory:
    the preregistered test is TOST, and this reads its interval, nothing more."""
    if r["kind"] != "equivalence" or r["reject_holm"]:
        return None
    m, lo, hi = r["margin_pct"], r["ci90_low"], r["ci90_high"]
    span = f"{lo:+.2f}% to {hi:+.2f}%"
    head = (f"Exploratory: at {r['level']} demand, the 90% CI of {NAMES[r['condition']]} vs {NAMES[r['reference']]} "
            f"({span})")
    if hi < -m:
        return f"{head} lies entirely below -{m:g}%: lower NOx by more than the equivalence margin."
    if lo > m:
        return f"{head} lies entirely above +{m:g}%: higher NOx by more than the equivalence margin."
    return f"{head} crosses the margin: neither equivalence nor a difference beyond the margin is shown."


def exploratory_sentence(r: dict) -> str:
    metric = r["metric"].replace("_", " ")
    return (f"Exploratory: at {r['level']} demand, {metric} under {NAMES[r['condition']]} changed by "
            f"{r['mean_pct']:+.2f}% vs {NAMES[r['reference']]} (95% CI {r['ci95_low']:+.2f}% to "
            f"{r['ci95_high']:+.2f}%, n = {r['n']}).")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _ci(r: dict, unit: str = "%") -> str:
    return f"95% CI {r['ci95_low']:+.1f}{unit} to {r['ci95_high']:+.1f}{unit}"


def spatial_sentences(experiment: str) -> list[tuple[str, str]]:
    """(claim, source) pairs for RQ5: residential/service NOx and share, tertiary NOx, the composition share."""
    d = results_dir() / experiment
    s, tab = _load(d / "spatial_summary.json"), d / "spatial.csv"
    if not s or not tab.is_file():
        return []
    shares = pd.read_csv(tab).groupby(["label", "level"])[f"share_{RESID}"].mean()
    rows = {(r["condition"], r["reference"], r["level"], r["metric"]): r for r in s["paired"]}
    src, out = rel(d / "spatial_summary.json"), []
    for ref in ("static", "tt_adaptive"):
        for lvl in LEVELS:
            nox, pp = rows.get(("eco_ml", ref, lvl, f"nox_{RESID}_pct")), rows.get(("eco_ml", ref, lvl, f"share_{RESID}_pp"))
            vh, ter = rows.get(("eco_ml", ref, lvl, f"veh_h_{RESID}_pct")), rows.get(("eco_ml", ref, lvl, "nox_tertiary_pct"))
            if not (nox and pp and vh and ter):
                continue
            out.append((f"Exploratory (RQ5): at {lvl} demand, under {NAMES['eco_ml']} vs {NAMES[ref]}, NOx on "
                        f"residential/service streets changed by {nox['mean']:+.1f}% ({_ci(nox)}) and vehicle-hours "
                        f"there by {vh['mean']:+.1f}% ({_ci(vh)}); their share of edge NOx went from "
                        f"{100 * shares[(ref, lvl)]:.1f}% to {100 * shares[('eco_ml', lvl)]:.1f}% "
                        f"({pp['mean']:+.1f} percentage points, {_ci(pp, ' pp')}); NOx on tertiary roads changed by "
                        f"{ter['mean']:+.1f}% ({_ci(ter)}).", src))
    for c in s["composition"]:
        out.append((f"Exploratory (RQ5): at {c['level']} demand, the road-class mix of vehicle-hours under "
                    f"{NAMES[c['condition']]} explains {100 * c['explained_share']:.0f}% (95% CI "
                    f"{100 * c['ci95_low']:.0f}% to {100 * c['ci95_high']:.0f}%) of its edge-NOx change vs "
                    f"{NAMES[c['reference']]}, holding each road class's NOx per vehicle-hour at the reference "
                    "run's value.", src))
    return out


def timing_sentences(experiment: str, res: dict) -> list[tuple[str, str]]:
    """Tail travel time and departure delay of eco_ml, with absolute departure delays in seconds."""
    d = results_dir() / experiment
    src, out = rel(d / "analysis.json"), []
    rows = {(r["metric"], r["condition"], r["reference"], r["level"]): r for r in res["exploratory"]}
    runs = d / "runs.csv"
    delay = pd.read_csv(runs).groupby(["label", "level"]).mean_depart_delay_s.mean() if runs.is_file() else None
    for lvl in LEVELS:
        p95 = rows.get(("p95_tt_s", "eco_ml", "tt_adaptive", lvl))
        dd = rows.get(("mean_depart_delay_s", "eco_ml", "tt_adaptive", lvl))
        if p95:
            out.append((exploratory_sentence(p95), src))
        if dd and delay is not None:
            out.append((f"Exploratory: at {lvl} demand, mean departure delay was {delay[('eco_ml', lvl)]:.1f} s "
                        f"under {NAMES['eco_ml']} and {delay[('tt_adaptive', lvl)]:.1f} s under "
                        f"{NAMES['tt_adaptive']} (paired change {dd['mean_pct']:+.0f}%, 95% CI "
                        f"{dd['ci95_low']:+.0f}% to {dd['ci95_high']:+.0f}%); mean travel time excludes it.",
                        rel(runs)))
    return out


def forecast_sentences(experiment: str) -> list[tuple[str, str]]:
    path = results_dir() / experiment / "forecast_test.json"
    f = _load(path)
    if not f:
        return []
    reg, boot, meta = f["regression"], f["bootstrap"], f["meta"]
    out = []
    for t, what in (("r", "NOx per vehicle-second"), ("v", "mean speed"), ("d", "NOx density")):
        sk = boot[f"{t}_mae_skill_vs_historical_mean"]
        sp = boot[f"{t}_mae_skill_vs_persistence"]
        out.append((f"Exploratory (RQ2, test seeds, {meta['runs_test']} runs): for the next-minute {what}, the "
                    f"forecaster's MAE is {reg['model'][t]['mae']:.3f} against {reg['historical_mean'][t]['mae']:.3f} "
                    f"for the per-edge historical mean (skill {sk['ci95_low']:+.3f} to {sk['ci95_high']:+.3f}, 95% "
                    f"cluster-bootstrap interval) and {reg['persistence'][t]['mae']:.3f} for persistence (skill "
                    f"{sp['ci95_low']:+.3f} to {sp['ci95_high']:+.3f}).", rel(path)))
    return out


def legacy_sentences(experiment: str) -> list[tuple[str, str]]:
    out = []
    path = results_dir() / "legacy_audit" / f"replication_{experiment}.json"
    rep = _load(path)
    if rep:
        for lvl in LEVELS:
            v = rep["summary"].get(f"legacy_ml/{lvl}")
            if v:
                out.append((f"Exploratory (RQ1, {v['n']} test seeds): at {lvl} demand, the legacy metric (all records "
                            f"of a full static run against the legacy rule's first {rep['horizon_s']} s) reports a "
                            f"{v['legacy_metric_drop_pct_mean']:.1f}% drop (range {v['legacy_metric_drop_pct_min']:.1f}% "
                            f"to {v['legacy_metric_drop_pct_max']:.1f}%); the matched metric's change is "
                            f"{-v['matched_drop_pct_mean']:+.2f}% (range {-v['matched_drop_pct_max']:+.2f}% to "
                            f"{-v['matched_drop_pct_min']:+.2f}%).", rel(path)))
    path = results_dir() / "legacy_audit" / "route_change_recount.json"
    rc = _load(path)
    if rc:
        calls = sum(v["reroute_calls"] for v in rc["per_level"].values())
        changes = sum(v["route_changes"] for v in rc["per_level"].values())
        same = "identical to" if rc["nox_identical_to_pilot"] else "DIFFERENT from"
        out.append((f"Exploratory (RQ1, pilot seeds, {rc['runs']} runs, corrected counter): {changes:,} of {calls:,} "
                    f"calls of the legacy rule changed the vehicle's path ({100 * rc['route_change_rate_all']:.3f}%); "
                    f"total NOx is {same} the pilot runs made with the old counter.", rel(path)))
    return out


def write_claims(experiment: str = "confirmatory") -> list[str]:
    path = results_dir() / experiment / "analysis.json"
    res = json.loads(path.read_text(encoding="utf-8"))
    src = rel(path)
    lines = ["# Claims ledger", "",
             "Generated by `python -m nycemis analyze`; do not edit by hand. Every claim states the simulated "
             "quantity, the comparison, the interval and the result file. No claim concerns health, exposure or air "
             "quality (docs/LIMITATIONS.md).", "",
             "## Confirmatory (preregistered PC1-PC4; one Holm family of 12 tests)", "",
             "| ID | Claim | Source |", "|---|---|---|"]
    for r in res["confirmatory"]:
        lines.append(f"| {r['pc']}-{r['level']} | {confirmatory_sentence(r)} | `{src}` (confirmatory) |")
    lines += ["", "## Sensitivity (all pairs, including invalid runs)", "", "| ID | Claim | Source |", "|---|---|---|"]
    for r in res["sensitivity_all_pairs"]:
        lines.append(f"| {r['pc']}-{r['level']}-all | {confirmatory_sentence(r)} | `{src}` (sensitivity_all_pairs) |")
    key = {("total_nox_g", "eco_ml", "static"), ("mean_tt_s", "eco_ml", "static"), ("mean_tt_s", "eco_ml", "tt_adaptive"),
           ("total_co2_kg", "eco_ml", "static"), ("total_nox_g", "random_reroute", "static"),
           ("total_nox_g", "tt_adaptive", "static"), ("vkm_total", "eco_ml", "static"),
           ("total_nox_g", "eco_ml", "random_reroute")}
    explo = [(exploratory_sentence(r), src) for r in res["exploratory"]
             if (r["metric"], r["condition"], r["reference"]) in key]
    explo += [(s, src) for s in map(equivalence_direction, res["confirmatory"]) if s]
    sections = [("Exploratory (selected)", "E", explo),
                ("Exploratory: travel-time tail and departure delay", "T", timing_sentences(experiment, res)),
                ("Exploratory: side effects by road class (RQ5)", "S", spatial_sentences(experiment)),
                ("Exploratory: forecast skill on the test seeds (RQ2)", "F", forecast_sentences(experiment)),
                ("Exploratory: legacy replication (RQ1)", "L", legacy_sentences(experiment))]
    for title, prefix, items in sections:
        if not items:
            continue
        lines += ["", f"## {title}", "", "| ID | Claim | Source |", "|---|---|---|"]
        lines += [f"| {prefix}{i + 1} | {claim} | `{source}` |" for i, (claim, source) in enumerate(items)]
    text = "\n".join(lines) + "\n"
    out = [docs_dir() / "CLAIMS.md", repo_root() / "application" / "claims_ledger.md"]
    for p in out:
        p.parent.mkdir(exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return [rel(p) for p in out]
