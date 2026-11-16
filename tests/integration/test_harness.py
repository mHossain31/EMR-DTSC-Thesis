"""Harness tests on the smoke grid (docs/SPECIFICATION.md 9.3, 9.5, 9.7, 9.8, 9.9, 6.6)."""

from __future__ import annotations

import pandas as pd
import pytest

from nycemis.features.builder import feature_names
from nycemis.legacy.replicate import legacy_metric_drop_pct, matched_drop_pct
from nycemis.sim.runner import execute
from tests.integration.conftest import smoke_spec

pytestmark = pytest.mark.sumo

RESULT_KEYS = ("total_nox_g", "total_co2_kg", "mean_tt_s", "p95_tt_s", "vkm_total", "arrived", "teleports",
               "mean_timeloss_s", "last_arrival_s")


def _same(a: dict, b: dict) -> None:
    for k in RESULT_KEYS:
        assert a[k] == b[k], f"{k}: {a[k]} != {b[k]}"


def test_determinism_same_spec_twice(tmp_path) -> None:
    spec = smoke_spec("eco_reactive", params={"alpha": 0.5, "tau_avg_s": 180})
    a = execute(spec, tmp_path / "a")
    b = execute(spec, tmp_path / "b")
    _same(a, b)
    ta = pd.read_parquet(tmp_path / "a" / "trip_metrics.parquet")
    tb = pd.read_parquet(tmp_path / "b" / "trip_metrics.parquet")
    pd.testing.assert_frame_equal(ta, tb)


@pytest.mark.parametrize("controller,params", [("static", {}), ("eco_reactive", {"alpha": 0.5, "tau_avg_s": 180})])
def test_libsumo_and_traci_agree(tmp_path, controller, params) -> None:
    a = execute(smoke_spec(controller, params=params, backend="libsumo"), tmp_path / "libsumo")
    b = execute(smoke_spec(controller, params=params, backend="traci"), tmp_path / "traci")
    _same(a, b)


def test_logging_does_not_change_results(tmp_path) -> None:
    plain = execute(smoke_spec("static"), tmp_path / "plain")
    logged = execute(smoke_spec("static", reconcile=True, dataset=True), tmp_path / "logged")
    _same(plain, logged)


def test_reconciliation_within_tolerance(tmp_path) -> None:
    m = execute(smoke_spec("static", reconcile=True), tmp_path / "r")
    assert abs(m["recon_rel_diff"]) < 0.001
    assert m["recon_invalid_values"] == 0


def test_edge_tables_are_consistent(tmp_path) -> None:
    """edge_5min and edge_cumulative add up to the logger total, and stay below the tripinfo total (internal
    junction lanes are not attributed to edges)."""
    m = execute(smoke_spec("static"), tmp_path / "e")
    cum = pd.read_parquet(tmp_path / "e" / "edge_cumulative.parquet")
    five = pd.read_parquet(tmp_path / "e" / "edge_5min.parquet")
    total = m["edge_logger_total_nox_mg"]
    assert cum.nox_mg.sum() == pytest.approx(total, rel=1e-9)
    assert five.nox_mg.sum() == pytest.approx(total, rel=1e-9)
    assert 0.7 * 1000 * m["total_nox_g"] < total < 1000 * m["total_nox_g"]


def test_shadow_mode_features_equal_dataset_features(tmp_path) -> None:
    spec = smoke_spec("eco_ml", params={"alpha": 0.5, "model_id": "toy", "shadow": True, "tau_avg_s": 180}, dataset=True)
    execute(spec, tmp_path / "s")
    shadow = pd.read_parquet(tmp_path / "s" / "shadow_features.parquet")
    data = pd.read_parquet(tmp_path / "s" / "edge_window.parquet")
    f1 = feature_names("F1")
    merged = data[["k", "edge_idx", *f1]].merge(shadow[["k", "edge_idx", *f1]], on=["k", "edge_idx"],
                                                suffixes=("_d", "_s"))
    assert len(merged) == len(data) > 0
    for name in f1:
        pd.testing.assert_series_equal(merged[f"{name}_d"], merged[f"{name}_s"], check_names=False)


def test_shadow_mode_applies_nothing(tmp_path) -> None:
    static = execute(smoke_spec("static"), tmp_path / "static")
    shadow = execute(smoke_spec("eco_ml", params={"alpha": 0.5, "model_id": "toy", "shadow": True, "tau_avg_s": 180}),
                     tmp_path / "shadow")
    _same(static, shadow)
    assert shadow["n_reroutes"] == 0


@pytest.mark.slow
def test_alpha_zero_sanity(tmp_path) -> None:
    """eco_reactive with alpha = 0 (pure travel time) reproduces tt_adaptive's mean travel time within 5%."""
    for seed in (1, 2):
        a0 = execute(smoke_spec("eco_reactive", seed=seed, params={"alpha": 0.0, "tau_avg_s": 180}), tmp_path / f"a0_{seed}")
        tt = execute(smoke_spec("tt_adaptive", seed=seed), tmp_path / f"tt_{seed}")
        assert abs(a0["mean_tt_s"] - tt["mean_tt_s"]) / tt["mean_tt_s"] < 0.05


def test_artifact_demonstration(tmp_path) -> None:
    """Two identical runs: the legacy metric with a truncated horizon reports a large spurious drop; the matched
    metric reports none (docs/SPECIFICATION.md 9.9)."""
    base = execute(smoke_spec("static", reconcile=True), tmp_path / "base")
    ctl = execute(smoke_spec("static", reconcile=True), tmp_path / "ctl")
    s_base = pd.read_parquet(tmp_path / "base" / "network_series.parquet")
    s_ctl = pd.read_parquet(tmp_path / "ctl" / "network_series.parquet")
    assert matched_drop_pct(base["total_nox_g"], ctl["total_nox_g"]) == 0.0
    spurious = legacy_metric_drop_pct(s_base, s_ctl, ctl_horizon_s=1000)
    assert spurious > 50.0  # the smoke run lasts about an hour; 1000 s of it hold well under half of the NOx
