"""Application artifacts (docs/SPECIFICATION.md M9): the one-page research summary and the project page.

This module sits outside ``nycemis.analysis`` on purpose: the preregistration froze the hash of that package, and
these files only arrange results the frozen analysis already produced. Numbers come from
``nycemis.analysis.paper.macros()`` (the strings the paper prints) and from ``results/confirmatory/analysis.json``;
result wording follows the outcome of each Holm-adjusted test (``confirmatory_sentence`` for full sentences), so
neither file can say more than the intervals allow. The wording was written before the confirmatory results existed.
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
BYLINE = ("Mohammed Y. Hossain. Rebuilds a 2024 NYIT DTSC 870 project co-authored with Billy M. Kyaw and supervised "
          "by Prof. X. Huang.")
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
LIMITS_SHORT = ("Synthetic demand (not calibrated to New York counts), European HBEFA emission factors, no dispersion, "
                "full compliance, no field validation. Simulated tailpipe emissions only: not air quality, exposure "
                "or health.")


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


def _matched_txt(m: dict) -> str:
    matched = float(m["LegacyMlModerateMatchedMetric"])  # a drop: positive means less NOx than no rerouting
    return f"a {abs(matched):.2f}% {'drop' if matched > 0 else 'rise'}"


def _legacy_short(m: dict) -> str:
    return (f"The original project reported a {m['LegacyNOxDropRF']}% NOx drop. Its baseline ran about "
            f"{m['LegacyBaselineHorizon']} s and its rerouting runs {m['LegacyControlledSteps']} s "
            f"({m['LegacyRowRatioRF']}% as many vehicle-steps); {m['LegacyRepeatUnchanged']} of "
            f"{m['LegacyRepeatCalls']} repeated reroute calls returned the unchanged route. Replicated with matched "
            f"runs at moderate demand, its rule shows a {m['LegacyMlModerateLegacyMetric']}% drop by the legacy "
            f"metric, {_matched_txt(m)} by the matched one.")


def _legacy_sentence(m: dict) -> str:
    return (f"The original project reported a {m['LegacyNOxDropRF']}% NOx drop. Its notebook compared a baseline of "
            f"about {m['LegacyBaselineHorizon']} s against rerouting runs stopped after {m['LegacyControlledSteps']} s "
            f"(the rerouting runs held {m['LegacyRowRatioRF']}% as many vehicle-steps), and "
            f"{m['LegacyRepeatUnchanged']} of {m['LegacyRepeatCalls']} repeated reroute calls returned the unchanged "
            "route. Replicating its rule under a matched protocol at moderate demand, the legacy metric still shows a "
            f"{m['LegacyMlModerateLegacyMetric']}% drop; the matched comparison shows {_matched_txt(m)}.")


def _method_short(m: dict) -> str:
    return ("In SUMO, all conditions share network, route file, fleet and seed, run until every vehicle arrives, and "
            "are paired by seed. Controllers: none, travel-time rerouting, a random placebo, eco-rerouting on "
            f"measured or on {m['HorizonS']}-second forecast emissions (gradient-boosted trees, traffic-state "
            f"features), and the legacy rule. Eco-routing weight (alpha = {m['AlphaStarML']}) tuned on validation "
            f"seeds; comparisons, n = {m['ConfirmatoryN']} seeds per level and analysis code frozen by git tag before "
            "the test seeds ran.")


def _method_sentence(m: dict) -> str:
    return ("I rebuilt the study in SUMO under a matched protocol: every condition shares the network, a "
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


def render_summary(m: dict, res: dict) -> str:
    rows = res["confirmatory"]
    findings = [pc_finding([r for r in rows if r["pc"] == pc], SHORT_LABEL) for pc in PC_LABEL]
    tt = _tt_values(res)
    lines = [
        f"# {TITLE}", "", BYLINE, "",
        "**Question.** Does rerouting traffic away from streets forecast to emit the most NOx in the next minute "
        "lower simulated NOx, compared with no rerouting, travel-time rerouting and rerouting on measured emissions?",
        "",
        f"**What was wrong with version 1.** {_legacy_short(m)}", "",
        f"**What I did.** {_method_short(m)}", "",
        f"**Results** (simulated total NOx; mean change per seed [95% BCa CI]; * significant, Holm over "
        f"{m['TestsInFamily']} tests; PC1, PC4: equivalence within +-{m['SESOI']}%):", "",
        *results_table(rows, SHORT_LABEL), "",
        *[f"- {f}" for f in findings],
        f"- Power at n = {m['ConfirmatoryN']} was {m['PowerAtNSup']}% for a true {m['SESOI']}% change; "
        "non-significant results do not rule one out.",
        *([f"- Exploratory: mean travel time vs travel-time rerouting: {tt}."] if tt else []), "",
        f"**Limits.** {LIMITS_SHORT}", "",
        "**Reproduce.** Code, frozen inputs and results are in the repository; `python -m nycemis verify-all` "
        "rechecks everything.",
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
        "A 2024 student project reported that machine-learning-triggered rerouting cut simulated NOx in Flushing, "
        f"Queens, by {m['LegacyNOxDropRF']}%. I audited it, found that the drop came from comparing runs of different "
        "length, and rebuilt the study as a preregistered, paired, multi-seed experiment in SUMO. The question it now "
        "answers: does rerouting on a one-minute emission forecast lower simulated NOx compared with no rerouting, "
        "travel-time rerouting and rerouting on measured emissions?", "",
        "## Why the original result did not hold", "", _legacy_sentence(m), "",
        "## What I rebuilt", "", _method_sentence(m), "",
        "## Results", "",
        f"Simulated total NOx, mean change per seed with 95% BCa interval; * = significant in one Holm family of "
        f"{m['TestsInFamily']} tests (for PC1 and PC4, equivalence within +-{m['SESOI']}% shown).", "",
        *results_table(rows), "",
        *[f"- {confirmatory_sentence(r)}" for r in rows],
        f"- {_power_sentence(m)}",
        *([f"- Exploratory: mean travel time under forecast eco-rerouting vs travel-time rerouting changed by {tt} "
           "(intervals in the claims ledger)."] if tt else []), "",
        "![Preregistered comparisons](../paper/figures/forest_confirmatory.png)", "",
        "![NOx and travel time over the eco-routing weight, validation seeds](../paper/figures/pareto_alpha.png)", "",
        "## Limits", "", LIMITS, "",
        "## Reproduce", "",
        "```bash", "python -m nycemis doctor", "python -m nycemis analyze", "python -m nycemis paper",
        "python -m nycemis verify-all", "```", "",
        "The preregistration (`docs/PREREGISTRATION.md`, git tag `prereg-v1`), every deviation from it "
        "(`docs/DEVIATIONS.md`) and the claims ledger (`application/claims_ledger.md`) are in the repository.", "",
        "## Credits", "",
        "The original project was co-authored by Mohammed Y. Hossain and Billy M. Kyaw and supervised by "
        "Prof. X. Huang (NYIT). Map data (c) OpenStreetMap contributors, ODbL.",
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
    return written
