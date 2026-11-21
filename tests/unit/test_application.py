"""Application artifacts (docs/SPECIFICATION.md M9): the research summary stays within 450 words for every outcome pattern, and
its wording follows each Holm-adjusted test."""

from __future__ import annotations

import itertools

import pytest

from nycemis.analysis.paper import macros
from nycemis.application import (
    LEVELS,
    MAX_SUMMARY_WORDS,
    PC_LABEL,
    SHORT_LABEL,
    pc_finding,
    render_project_page,
    render_summary,
    word_count,
)

KINDS = {"PC1": "equivalence", "PC2": "superiority", "PC3": "superiority", "PC4": "equivalence"}


def _row(pc: str, level: str, mean: float, reject: bool) -> dict:
    kind = KINDS[pc]
    return {"pc": pc, "condition": "eco_ml", "reference": "static", "kind": kind, "level": level,
            "margin_pct": 2.0 if kind == "equivalence" else None, "mean_pct": mean, "ci95_low": mean - 1.234,
            "ci95_high": mean + 1.234, "ci90_low": mean - 1.0, "ci90_high": mean + 1.0, "p_holm": 0.0123,
            "reject_holm": reject, "n": 60}


def _res(means: dict, rejects: dict) -> dict:
    rows = [_row(pc, lvl, means[pc], rejects[pc][i]) for pc in PC_LABEL for i, lvl in enumerate(LEVELS)]
    explo = [{"metric": "mean_tt_s", "condition": "eco_ml", "reference": "tt_adaptive", "level": lvl,
              "mean_pct": 1.5, "ci95_low": 1.0, "ci95_high": 2.0, "n": 60} for lvl in LEVELS]
    return {"confirmatory": rows, "exploratory": explo}


@pytest.fixture(scope="module")
def m() -> dict:
    return macros()


@pytest.mark.parametrize("pattern", list(itertools.product([True, False], repeat=3)))
def test_summary_fits_one_page_for_every_outcome_pattern(m, pattern) -> None:
    res = _res({"PC1": 0.31, "PC2": -12.345, "PC3": -10.5, "PC4": -3.21}, dict.fromkeys(PC_LABEL, list(pattern)))
    text = render_summary(m, res)
    assert word_count(text) <= MAX_SUMMARY_WORDS
    assert "health" in text and "not air quality" in text  # the limits sentence is always there


def test_summary_fits_with_three_outcomes_per_comparison(m) -> None:
    # the longest findings: lower, no difference and higher NOx at the three levels of PC2 and PC3
    res = _res({"PC1": 0.31, "PC2": -12.345, "PC3": -10.5, "PC4": -3.21}, dict.fromkeys(PC_LABEL, [True, False, True]))
    for r in res["confirmatory"]:
        if r["kind"] == "superiority" and r["level"] == "heavy":
            r["mean_pct"] = 1.234
    assert word_count(render_summary(m, res)) <= MAX_SUMMARY_WORDS


def test_finding_groups_levels_by_outcome() -> None:
    rows = [_row("PC2", "light", -3.0, True), _row("PC2", "moderate", -2.0, True), _row("PC2", "heavy", 0.5, False)]
    assert pc_finding(rows) == ("PC2 forecast eco-rerouting vs no rerouting: lower NOx at light and moderate demand; "
                                "no significant difference at heavy demand.")
    assert pc_finding(rows, SHORT_LABEL).startswith("PC2 forecast vs none: lower NOx")
    eq = [_row("PC4", lvl, 0.1, False) for lvl in LEVELS]
    assert pc_finding(eq) == ("PC4 forecast vs measured-emission eco-rerouting: equivalence not shown at all three "
                              "demand levels.")


def test_project_page_has_every_test_sentence(m) -> None:
    res = _res({"PC1": 0.3, "PC2": -5.0, "PC3": -4.0, "PC4": -2.5}, dict.fromkeys(PC_LABEL, [True, False, True]))
    page = render_project_page(m, res)
    # the four PC sentences per level ("At <level> demand, ..."); the sensitivity sentences continue "on the ..."
    assert page.count("At light demand,") == 4 and page.count("At heavy demand,") == 4


def test_word_count_ignores_table_rules() -> None:
    assert word_count("| a | b |\n|---|---|\n| +1.2% [-0.3, +2.0]* | x |") == 6
