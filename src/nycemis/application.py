"""Application artifacts (docs/SPECIFICATION.md M9): the one-page research summary and the project page.

This module sits outside ``nycemis.analysis`` on purpose: the preregistration froze the hash of that package, and
these files only arrange results the frozen analysis already produced. Numbers come from
``nycemis.analysis.paper.macros()`` (the strings the paper prints) and from ``results/confirmatory/analysis.json``;
result wording follows the outcome of each Holm-adjusted test (``confirmatory_sentence`` for full sentences), so
neither file can say more than the intervals allow. The wording was written before the confirmatory results existed;
after the adversarial review (docs/DEVIATIONS.md #17) the summary also reports, each sentence phrased by the data:
the direction of a failed equivalence test, the road-class side effect (RQ5) with the network's speed coding, the
forecaster's skill on the test seeds (RQ2), tail travel time and departure delay; the power sentence appears only
when a superiority test is not significant; the legacy replication uses the test seeds when available.
"""

from __future__ import annotations

import json
import logging
import re

from nycemis.paths import rel, repo_root, results_dir

log = logging.getLogger(__name__)

MAX_SUMMARY_WORDS = 450
LEVELS = ("light", "moderate", "heavy")
TITLE = ("Does forecast-driven eco-rerouting reduce simulated traffic emissions? An audited, preregistered SUMO "
         "study of Flushing, Queens")
BYLINE = ("Mohammed Y. Hossain and Billy M. Kyaw (NYIT). Rebuild of their 2024 NYIT DTSC 870 course project, "
          "supervised by Prof. X. Huang.")
PC_LABEL = {
    "PC1": "PC1 legacy rule vs no rerouting",
    "PC2": "PC2 forecast eco-rerouting vs no rerouting",
    "PC3": "PC3 forecast eco-rerouting vs travel-time rerouting",
    "PC4": "PC4 forecast vs measured-emission eco-rerouting",
}
SHORT_LABEL = {"PC1": "PC1 legacy rule vs none", "PC2": "PC2 forecast vs none",
               "PC3": "PC3 forecast vs travel-time", "PC4": "PC4 forecast vs measured"}
LIMITS = ("Demand is synthetic and not calibrated to New York counts; emission factors are European (HBEFA); there "
          "is no dispersion; drivers comply fully; nothing is validated against field measurements. All quantities "
          "are simulated tailpipe emissions, not air quality, exposure or health.")
LIMITS_SHORT = ("Synthetic demand not calibrated to counts, European HBEFA factors, no dispersion, full compliance, "
                "no field validation. Simulated tailpipe emissions only: not air quality, exposure or health.")


def word_count(text: str) -> int:
    """Words as a reader counts them: runs that contain a letter or digit (table pipes and dashes do not count)."""
    return len(re.findall(r"[^\s|]*[A-Za-z0-9][^\s|]*", text))


def _levels_phrase(levels: list[str]) -> str:
    if len(levels) == len(LEVELS):
        return "all three demand levels"
    if len(levels) == 1:
        return f"{levels[0]} demand"
    return f"{' and '.join(levels)} demand"


def pc_finding(rows: list[dict], labels: dict[str, str] = PC_LABEL) -> str:
    """One sentence per comparison, grouping the levels by the outcome of their Holm-adjusted test."""
    pc, kind = rows[0]["pc"], rows[0]["kind"]
    groups: dict[str, list[str]] = {}
    for r in sorted(rows, key=lambda r: LEVELS.index(r["level"])):
        if kind == "equivalence":
            key = f"equivalent within +-{r['margin_pct']:g}%" if r["reject_holm"] else "equivalence not shown"
        elif r["reject_holm"]:
            key = "lower NOx" if r["mean_pct"] < 0 else "higher NOx"
        else:
            key = "no significant difference"
        groups.setdefault(key, []).append(r["level"])
    parts = [f"{key} at {_levels_phrase(lv)}" for key, lv in groups.items()]
    return f"{labels[pc]}: {'; '.join(parts)}."


def results_table(rows: list[dict], labels: dict[str, str] = PC_LABEL) -> list[str]:
    """PC x level table: mean change per seed and 95% BCa interval; * marks a Holm-adjusted rejection."""
    by = {(r["pc"], r["level"]): r for r in rows}
    lines = ["| Comparison | light | moderate | heavy |", "|---|---|---|---|"]
    for pc in PC_LABEL:
        cells = []
        for lvl in LEVELS:
            r = by[(pc, lvl)]
            star = "*" if r["reject_holm"] else ""
            cells.append(f"{r['mean_pct']:+.1f}% [{r['ci95_low']:+.1f}, {r['ci95_high']:+.1f}]{star}")
        lines.append(f"| {labels[pc]} | {' | '.join(cells)} |")
    return lines


def _tt_values(res: dict) -> str | None:
    """Exploratory mean travel time of eco_ml vs tt_adaptive per level, or None if the analysis lacks a level."""
    rows = {r["level"]: r for r in res["exploratory"]
            if (r["metric"], r["condition"], r["reference"]) == ("mean_tt_s", "eco_ml", "tt_adaptive")}
    if set(rows) != set(LEVELS):
        return None
    return ", ".join(f"{lvl} {rows[lvl]['mean_pct']:+.1f}%" for lvl in LEVELS)


def _legacy_replication_txt(m: dict) -> str:
    """The legacy-vs-matched comparison at moderate demand: test seeds when available, else the pilot's five."""
    if "LegacyTestModerateLegacyMetric" in m:
        return (f"on {m['LegacyTestN']} test seeds at moderate demand its rule shows a "
                f"{m['LegacyTestModerateLegacyMetric']}% drop by the legacy metric and a "
                f"{m['LegacyTestModerateMatchedChange']}% change by the matched one")
    matched = float(m["LegacyMlModerateMatchedMetric"])  # a drop: positive means less NOx than no rerouting
    return (f"on five pilot seeds at moderate demand its rule shows a {m['LegacyMlModerateLegacyMetric']}% drop by "
            f"the legacy metric and a {-matched:+.2f}% change by the matched one")


def _legacy_short(m: dict) -> str:
    if "LegacyTestModerateLegacyMetric" in m:
        rep = (f"Replicated on {m['LegacyTestN']} test seeds (moderate demand): a "
               f"{m['LegacyTestModerateLegacyMetric']}% drop by its metric, a {m['LegacyTestModerateMatchedChange']}% "
               "change by a matched one.")
    else:
        rep = f"Replicated, {_legacy_replication_txt(m)}."
    return (f"A {m['LegacyNOxDropRF']}% NOx drop was reported from a {m['LegacyBaselineHorizon']} s baseline against "
            f"{m['LegacyControlledSteps']} s rerouting runs ({m['LegacyRowRatioRF']}% of the vehicle-steps); "
            f"{m['LegacyRepeatUnchanged']} of {m['LegacyRepeatCalls']} repeat reroute calls changed nothing. {rep}")


def _legacy_sentence(m: dict) -> str:
    return (f"The original project reported a {m['LegacyNOxDropRF']}% NOx drop. Its notebook compared a baseline of "
            f"about {m['LegacyBaselineHorizon']} s against rerouting runs stopped after {m['LegacyControlledSteps']} s "
            f"(the rerouting runs held {m['LegacyRowRatioRF']}% as many vehicle-steps), and "
            f"{m['LegacyRepeatUnchanged']} of {m['LegacyRepeatCalls']} repeated reroute calls returned the unchanged "
            f"route. Replicating its rule under a matched protocol, {_legacy_replication_txt(m)} (negative = lower "
            "NOx).")


def _method_short(m: dict) -> str:
    return ("Paired SUMO runs share network, route file, fleet and seed and run to completion. Controllers: none, "
            f"travel-time, random placebo, eco-rerouting on measured or {m['HorizonS']}-second forecast emissions, "
            f"legacy rule. Comparisons, n = {m['ConfirmatoryN']} seeds per level, alpha = {m['AlphaStarML']} and "
            "analysis code were frozen by git tag first.")


def _compact_outcomes(rows: list[dict]) -> str:
    """All Holm outcomes in one line: 'PC1: equivalent ... at all three demand levels. PC2: ...'."""
    parts = []
    for pc in PC_LABEL:
        finding = pc_finding([r for r in rows if r["pc"] == pc], {pc: pc})
        parts.append(finding)
    return " ".join(parts)


def _method_sentence(m: dict) -> str:
    return ("We rebuilt the study in SUMO under a matched protocol: every condition shares the network, a "
            "byte-identical route file, the fleet and the seed; runs continue until every vehicle arrives; results are "
            "paired by seed. Six controllers: no rerouting, travel-time rerouting, a random-rerouting placebo, "
            f"eco-rerouting on measured emissions, eco-rerouting on a {m['HorizonS']}-second forecast from "
            "traffic-state features (gradient-boosted trees), and the legacy rule. The eco-routing weight "
            f"(alpha = {m['AlphaStarML']}) was tuned on validation seeds; the comparisons, the sample size "
            f"(n = {m['ConfirmatoryN']} test seeds per demand level) and the analysis code were frozen by git tag "
            "before the test seeds ran.")


def _power_sentence(m: dict) -> str:
    return (f"At n = {m['ConfirmatoryN']} the tests had {m['PowerAtNSup']}% power for a true {m['SESOI']}% change, "
            f"so a non-significant result does not rule out an effect of that size.")


def _needs_power_caveat(rows: list[dict]) -> bool:
    """The power caveat bears on non-significant superiority tests only."""
    return any(r["kind"] == "superiority" and not r["reject_holm"] for r in rows)


def _direction_lines(rows: list[dict], labels: dict[str, str]) -> list[str]:
    """Exploratory reading of each failed equivalence test: levels whose 90% CI lies wholly beyond the margin."""
    out = []
    for pc in PC_LABEL:
        rs = [r for r in rows if r["pc"] == pc and r["kind"] == "equivalence" and not r["reject_holm"]]
        if not rs:
            continue
        margin = rs[0]["margin_pct"]
        below = [r["level"] for r in rs if r["ci90_high"] < -margin]
        above = [r["level"] for r in rs if r["ci90_low"] > margin]
        parts = ([f"below -{margin:g}% at {_levels_phrase(below)}"] if below else []) + \
                ([f"above +{margin:g}% at {_levels_phrase(above)}"] if above else [])
        if parts:
            out.append(f"Exploratory: for {labels[pc]} the 90% CI lies {' and '.join(parts)}, a difference "
                       "larger than the margin.")
    return out


def _span(m: dict, stem: str, unit: str = "%") -> str | None:
    vals = [m.get(f"{stem}{lvl.capitalize()}") for lvl in LEVELS]
    return None if None in vals else ", ".join(f"{v}{unit}" for v in vals)


def _side_effect_line(m: dict) -> str | None:
    resid, comp = _span(m, "ResidNOx"), [m.get(f"Composition{lvl.capitalize()}") for lvl in LEVELS]
    shares = [m.get(f"ResidShareEcoMl{lvl.capitalize()}") for lvl in LEVELS]
    base = [m.get(f"ResidShareStatic{lvl.capitalize()}") for lvl in LEVELS]
    if not resid or None in comp or None in shares or None in base:
        return None
    nums = sorted(int(c) for c in comp)
    return (f"Side effect (exploratory, RQ5): vs no rerouting, NOx on residential/service streets changed by {resid} "
            f"(light, moderate, heavy), their share of edge NOx rising from {min(base, key=int)}-{max(base, key=int)}% to "
            f"{min(shares, key=int)}-{max(shares, key=int)}%; the shift of vehicle-hours between road classes explains "
            f"{nums[0]}-{nums[-1]}% of the edge-NOx change.")


def _network_line(m: dict) -> str | None:
    keys = ("SpeedPrimSec", "SpeedResid", "JunctionsSignal", "JunctionsStop")
    if not all(k in m for k in keys):
        return None
    return (f"The network keeps SUMO's speed defaults by road type (primary/secondary {m['SpeedPrimSec']} km/h, "
            f"residential {m['SpeedResid']} km/h; {m['JunctionsSignal']} signalised and {m['JunctionsStop']} "
            "stop-controlled junctions), which makes such detours cheap.")


def _forecast_line(experiment: str = "confirmatory") -> str | None:
    path = results_dir() / experiment / "forecast_test.json"
    if not path.is_file():
        return None
    b = json.loads(path.read_text(encoding="utf-8"))["bootstrap"]["r_mae_skill_vs_historical_mean"]
    verdict = ("beat" if b["ci95_low"] > 0 else "was worse than" if b["ci95_high"] < 0 else "did not clearly beat")
    tail = "" if b["ci95_low"] > 0 else "; gains are not attributed to forecasting"
    return (f"On test seeds the forecaster {verdict} a per-edge historical average for NOx per vehicle-second "
            f"(skill {b['ci95_low']:+.3f} to {b['ci95_high']:+.3f}){tail}.")


def _cost_line(m: dict, res: dict) -> str | None:
    tt = _tt_values(res)
    rows = {r["level"]: r for r in res["exploratory"]
            if (r["metric"], r["condition"], r["reference"]) == ("p95_tt_s", "eco_ml", "tt_adaptive")}
    delay = [(m.get(f"DepartDelayEcoMl{lvl.capitalize()}"), m.get(f"DepartDelayTtAdaptive{lvl.capitalize()}"))
             for lvl in LEVELS]
    if not tt or set(rows) != set(LEVELS) or any(None in d for d in delay):
        return None
    p95 = ", ".join(f"{rows[lvl]['mean_pct']:+.1f}%" for lvl in LEVELS)
    dd = ", ".join(f"{a} vs {b} s" for a, b in delay)
    return (f"Cost vs travel-time rerouting (exploratory): mean travel time {tt}; 95th percentile {p95}; "
            f"departure delay {dd}.")


SENSITIVITY = "sensitivity_posted"
SENS_HEADING = "## Does the reduction hold with New York street coding?"


def _sensitivity() -> dict | None:
    path = results_dir() / SENSITIVITY / "analysis.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _sens_rows(s: dict, cond: str, ref: str, metric: str) -> list[dict] | None:
    rows = {r["level"]: r for r in s["contrasts"] if (r["condition"], r["reference"], r["metric"]) == (cond, ref, metric)}
    return [rows[lvl] for lvl in LEVELS] if set(rows) >= set(LEVELS) else None


def _sens_resid(s: dict) -> str | None:
    rows = {x["level"]: x for x in s["spatial"]["posted"]["paired"]
            if (x["condition"], x["reference"], x["metric"]) == ("eco_reactive", "static", "nox_residential/service_pct")}
    return ", ".join(f"{rows[lvl]['mean']:+.0f}%" for lvl in LEVELS) if set(rows) >= set(LEVELS) else None


def _sensitivity_short() -> str | None:
    """One compact sentence for the summary (docs/SENSITIVITY_PLAN.md); numbers and signs from the result file."""
    s = _sensitivity()
    rows = _sens_rows(s, "eco_reactive", "tt_adaptive", "total_nox_g") if s else None
    resid = _sens_resid(s) if s else None
    if not rows or not resid:
        return None
    posted = ", ".join(f"{r['posted']['mean_pct']:+.1f}%" for r in rows)
    orig = ", ".join(f"{r['original']['mean_pct']:+.1f}%" for r in rows)
    return (f"With NYC's 25 mph default and minor-road stops (exploratory), measured-emission rerouting changed NOx "
            f"{posted} vs travel-time rerouting (original network {orig}); residential NOx {resid}.")


def _sensitivity_section() -> list[str]:
    """Project page and FAQ: the street-coding sensitivity experiment, in the generated claim sentences."""
    from nycemis.sensitivity import nox_sentence

    s = _sensitivity()
    if not s:
        return []
    lines = ["The study's main network keeps SUMO's default speed for each OpenStreetMap road type where OSM has no "
             "speed tag, and has no stop-controlled junction. A follow-up experiment, specified and tagged before its "
             "runs (`docs/SENSITIVITY_PLAN.md`), recoded the network with New York City's default 25 mph limit and a "
             "stop on the minor approaches of unsignalised junctions entered by a minor street, and reran no "
             "rerouting, travel-time rerouting and measured-emission rerouting (forecast-driven rerouting was not run: "
             "its forecaster takes the speed limits as inputs). Exploratory results:", ""]
    for cond, ref in (("eco_reactive", "tt_adaptive"), ("eco_reactive", "static")):
        for r in _sens_rows(s, cond, ref, "total_nox_g") or []:
            lines.append(f"- {nox_sentence(r)}")
    resid = _sens_resid(s)
    if resid:
        lines.append(f"- NOx on residential/service streets under measured-emission rerouting vs no rerouting, light, "
                     f"moderate, heavy: {resid} on the recoded network.")
    lines += ["", "Heavy demand on the recoded network is less congested than on the original (its calibration target "
              "could not be reached without jams), so heavy-demand comparisons mix coding and congestion; light and "
              "moderate demand are matched. Details: `docs/CLAIMS_SENSITIVITY.md`.", ""]
    return lines


def append_faq_sensitivity() -> str | None:
    """Add (or replace) the FAQ's street-coding answer. ``render_faq`` (frozen analysis package) writes the FAQ first."""
    section = _sensitivity_section()
    path = repo_root() / "application" / "interview_faq.md"
    if not section or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if SENS_HEADING in text:
        text = text[:text.index(SENS_HEADING)]
    path.write_text(text.rstrip("\n") + "\n\n" + "\n".join([SENS_HEADING, "", *section]).rstrip("\n") + "\n",
                    encoding="utf-8")
    return rel(path)


def _summary_extra(m: dict, res: dict) -> list[str]:
    """Compact exploratory lines for the one-page summary (the project page uses the full sentences)."""
    out = []
    resid, comp = _span(m, "ResidNOx"), [m.get(f"Composition{lvl.capitalize()}") for lvl in LEVELS]
    if resid and None not in comp:
        nums = sorted(int(c) for c in comp)
        side = (f"Side effect (exploratory): residential-street NOx changed {resid} vs no rerouting; the road-class "
                f"shift of vehicle-hours explains {nums[0]}-{nums[-1]}% of the edge-NOx change.")
        sens = _sensitivity_short()
        if sens:
            side += f" {sens}"
        elif all(k in m for k in ("SpeedPrimSec", "SpeedResid", "JunctionsStop")):
            side += (f" SUMO default speeds (arterials {m['SpeedPrimSec']}, residential {m['SpeedResid']} km/h) and "
                     f"{m['JunctionsStop']} stop-controlled junctions make such detours cheap.")
        out.append(side)
    fc = _forecast_line()
    if fc:
        out.append(fc.replace("On test seeds the forecaster", "Test seeds: the forecaster")
                   .replace(" for NOx per vehicle-second", " for NOx per vehicle-s"))
    tt = _tt_values(res)
    p95 = {r["level"]: r for r in res["exploratory"]
           if (r["metric"], r["condition"], r["reference"]) == ("p95_tt_s", "eco_ml", "tt_adaptive")}
    if tt and set(p95) == set(LEVELS):
        tail = ", ".join(f"{p95[lvl]['mean_pct']:+.1f}%" for lvl in LEVELS)
        out.append(f"Cost vs travel-time rerouting: mean travel time {tt}; 95th percentile {tail}.")
    elif tt:
        out.append(f"Cost vs travel-time rerouting: mean travel time {tt}.")
    return out


def render_summary(m: dict, res: dict) -> str:
    rows = res["confirmatory"]
    direction = [x.replace(f"for {SHORT_LABEL[pc]} the", f"{pc}'s")
                 for pc in PC_LABEL for x in _direction_lines([r for r in rows if r["pc"] == pc], SHORT_LABEL)]
    lines = [
        f"# {TITLE}", "", BYLINE, "",
        "**Question.** Does rerouting on a forecast of each street's next-minute NOx cost lower simulated NOx "
        "versus no, travel-time and measured-emission rerouting?",
        "",
        f"**Version 1.** {_legacy_short(m)}", "",
        f"**What we did.** {_method_short(m)}", "",
        f"**Results** (total NOx, mean change per seed [95% BCa CI]; * Holm-significant of {m['TestsInFamily']}; "
        f"PC1, PC4 test equivalence within +-{m['SESOI']}%):", "",
        *results_table(rows, SHORT_LABEL), "",
        f"- {_compact_outcomes(rows)}",
        *[f"- {x}" for x in direction],
        *([f"- Power at n = {m['ConfirmatoryN']} was {m['PowerAtNSup']}% for a true {m['SESOI']}% change; "
           "non-significant results do not rule one out."] if _needs_power_caveat(rows) else []),
        *[f"- {x}" for x in _summary_extra(m, res)], "",
        f"**Limits.** {LIMITS_SHORT}",
    ]
    text = "\n".join(lines) + "\n"
    n = word_count(text)
    if n > MAX_SUMMARY_WORDS:
        raise ValueError(f"research summary has {n} words (limit {MAX_SUMMARY_WORDS})")
    return text


def render_project_page(m: dict, res: dict) -> str:
    from nycemis.analysis.claims import confirmatory_sentence

    rows = res["confirmatory"]
    tt = _tt_values(res)
    lines = [
        f"# {TITLE}", "", BYLINE, "",
        "*Generated by `python -m nycemis paper` from the repository's result files; do not edit by hand.*", "",
        "## In one paragraph", "",
        "Our 2024 student project reported that machine-learning-triggered rerouting cut simulated NOx in Flushing, "
        f"Queens, by {m['LegacyNOxDropRF']}%. We audited it, found that the drop came from comparing runs of different "
        "length, and rebuilt the study as a preregistered, paired, multi-seed experiment in SUMO. The question it now "
        "answers: does rerouting on a one-minute emission forecast lower simulated NOx compared with no rerouting, "
        "travel-time rerouting and rerouting on measured emissions?", "",
        "## Why the original result did not hold", "", _legacy_sentence(m), "",
        "## What we rebuilt", "", _method_sentence(m), "",
        "## Results", "",
        f"Simulated total NOx, mean change per seed with 95% BCa interval; * = significant in one Holm family of "
        f"{m['TestsInFamily']} tests (for PC1 and PC4, equivalence within +-{m['SESOI']}% shown).", "",
        *results_table(rows), "",
        *[f"- {confirmatory_sentence(r)}" for r in rows],
        *[f"- {x}" for x in _direction_lines(rows, PC_LABEL)],
        *([f"- {_power_sentence(m)}"] if _needs_power_caveat(rows) else []), "",
        "![Preregistered comparisons](../paper/figures/forest_confirmatory.png)", "",
        *(["## Where the reduction comes from, and what it costs", "",
           *[f"- {x}" for x in (_side_effect_line(m), _network_line(m), _forecast_line(), _cost_line(m, res)) if x],
           *([f"- Exploratory: mean travel time under forecast eco-rerouting vs travel-time rerouting changed by "
              f"{tt}."] if tt and not _cost_line(m, res) else []), "",
           "![Change in NOx per edge, forecast eco-rerouting minus no rerouting, heavy demand]"
           "(../paper/figures/map_eco_ml_minus_static_heavy.png)", "",
           "Intervals for every statement are in the claims ledger.", ""]),
        *([SENS_HEADING, "", *_sensitivity_section(),
           "![Share of edge NOx by road class on the recoded network](../paper/figures/road_class_shares_posted.png)",
           ""] if _sensitivity() else []),
        "![NOx and travel time over the eco-routing weight, validation seeds](../paper/figures/pareto_alpha.png)", "",
        "## Limits", "", LIMITS, "",
        "## Reproduce", "",
        "```bash", "python -m nycemis doctor", "python -m nycemis analyze", "python -m nycemis paper",
        "python -m nycemis verify-all", "```", "",
        "The preregistration (`docs/PREREGISTRATION.md`, git tag `prereg-v1`), every deviation from it "
        "(`docs/DEVIATIONS.md`) and the claims ledger (`application/claims_ledger.md`) are in the repository.", "",
        "## Credits", "",
        "Mohammed Y. Hossain and Billy M. Kyaw (NYIT) wrote the original 2024 project, supervised by Prof. X. Huang, "
        "and this rebuild of it. Map data (c) OpenStreetMap contributors, ODbL.",
    ]
    return "\n".join(lines) + "\n"


def write_application(experiment: str = "confirmatory") -> list[str]:
    """Write ``application/research_summary_1page.md`` and ``application/project_page.md``; both need the
    confirmatory analysis, so nothing is written (with a warning) before it exists."""
    from nycemis.analysis.paper import macros

    path = results_dir() / experiment / "analysis.json"
    if not path.is_file():
        log.warning("%s does not exist: research summary and project page not written", rel(path))
        return []
    res = json.loads(path.read_text(encoding="utf-8"))
    m = macros()
    out = repo_root() / "application"
    out.mkdir(exist_ok=True)
    written = []
    for name, text in (("research_summary_1page.md", render_summary(m, res)),
                       ("project_page.md", render_project_page(m, res))):
        (out / name).write_text(text, encoding="utf-8")
        written.append(rel(out / name))
    faq = append_faq_sensitivity()
    if faq:
        written.append(faq)
    return written
