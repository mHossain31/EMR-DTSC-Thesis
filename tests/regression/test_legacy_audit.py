"""Regression test of the legacy audit numbers (docs/SPECIFICATION.md 3.4).

The expected values were read from the legacy notebook's saved outputs; if any of them changes, the legacy inputs
or the extraction changed and docs/LEGACY_AUDIT.md must be regenerated and re-read.
"""

from __future__ import annotations

import pytest

from nycemis.legacy.audit import compute_numbers, load_inputs


@pytest.fixture(scope="module")
def numbers() -> dict:
    return compute_numbers(load_inputs())


def test_page_counts(numbers: dict) -> None:
    assert numbers["pages"] == {"ML_SUMO_ProjectReport.pdf": 48, "SUMO_ML_Project.pdf": 31}
    assert numbers["notebook"]["cells"] == 59


def test_d1_horizon_evidence(numbers: dict) -> None:
    d1 = numbers["d1_horizon"]
    assert d1["baseline_rows_notebook"] == 642472
    assert d1["baseline_rows_report"] == 638367
    lo, hi = d1["baseline_t_max_bounds_s"]
    assert 4120 < lo <= hi < 4140
    assert d1["controlled_step_bound"] == 1000
    assert (d1["rf_controlled_rows"], d1["xgb_controlled_rows"]) == (195640, 174518)
    assert d1["reported_drops_pct"]["RF"]["NOx"] == 71.53
    assert d1["reported_drops_pct"]["XGBoost"]["CO2"] == 73.65


def test_d2_reroute_evidence(numbers: dict) -> None:
    rf, xgb = numbers["d2_reroutes"]["rf"], numbers["d2_reroutes"]["xgb"]
    assert rf["reroute_calls"] == 38810 and rf["vehicles"] == 832
    assert xgb["reroute_calls"] == 41323 and xgb["vehicles"] == 829
    assert rf["repeat_changed"] == 0 and xgb["repeat_changed"] == 0
    assert rf["repeat_unchanged_share"] == 1.0


def test_d4_models(numbers: dict) -> None:
    d4 = numbers["d4_models"]
    assert d4["model_compare_cell_18"]["Random Forest"]["test_mse"] == 0.000105
    assert d4["normalized_df_used_after_cell_12"] == []
    assert round(d4["rf_reroute_model_cell_30_test_mse"], 6) == 0.000206


def test_d7_collect_loop_never_increments(numbers: dict) -> None:
    d7 = numbers["d7_hardcoded"]
    assert d7["collect_loop"] == {"step_bound": "simulation_time", "increments_step": False}
    assert d7["sample_cell_4_steps"] == [0.0]
    assert len(d7["replace_with_actual"]) == 4
    assert len(d7["hardcoded_drive_paths"]) == 6
