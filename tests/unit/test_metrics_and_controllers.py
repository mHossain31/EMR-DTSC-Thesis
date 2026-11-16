"""Metric parsers on fixtures, unit conversions, and controller arithmetic (docs/SPECIFICATION.md 4.3, 4.5, 9.1, P10)."""

from __future__ import annotations

import numpy as np
import pytest

from nycemis.controllers.base import EffortController, compliant
from nycemis.sim.metrics import parse_statistics, parse_tripinfo, run_metrics, speed_ratio
from nycemis.sim.run_spec import RunSpec

TRIPINFO = """<tripinfos>
  <tripinfo id="a" depart="1000.00" departDelay="0.50" arrival="1100.00" duration="100.00" routeLength="1000.00"
     waitingTime="10.00" timeLoss="40.00" rerouteNo="2" vType="PC_petrol_Euro-4">
    <emissions CO_abs="1.00" CO2_abs="200000.00" HC_abs="0.50" PMx_abs="0.10" NOx_abs="300.00" fuel_abs="1.00"
       electricity_abs="0.00"/>
  </tripinfo>
  <tripinfo id="b" depart="2000.00" departDelay="1.50" arrival="2300.00" duration="300.00" routeLength="3000.00"
     waitingTime="30.00" timeLoss="60.00" rerouteNo="0" vType="PC_diesel_Euro-5">
    <emissions CO_abs="2.00" CO2_abs="800000.00" HC_abs="1.50" PMx_abs="0.30" NOx_abs="1700.00" fuel_abs="1.00"
       electricity_abs="0.00"/>
  </tripinfo>
  <tripinfo id="c" depart="3000.00" departDelay="0.00" arrival="-1.00" duration="500.00" routeLength="500.00"
     waitingTime="0.00" timeLoss="0.00" rerouteNo="0" vType="PC_petrol_Euro-4">
    <emissions CO_abs="0" CO2_abs="0" HC_abs="0" PMx_abs="0" NOx_abs="0" fuel_abs="0" electricity_abs="0"/>
  </tripinfo>
</tripinfos>"""

STATS = """<statistics><vehicles loaded="4" inserted="3" running="0" waiting="0"/>
<teleports total="1" jam="1" yield="0" wrongLane="0"/>
<safety collisions="0" emergencyStops="0" emergencyBraking="0"/></statistics>"""


@pytest.fixture
def parsed(tmp_path):
    (tmp_path / "t.xml").write_text(TRIPINFO, encoding="utf-8")
    (tmp_path / "s.xml").write_text(STATS, encoding="utf-8")
    return parse_tripinfo(tmp_path / "t.xml"), parse_statistics(tmp_path / "s.xml")


def test_units_and_totals(parsed) -> None:
    trips, stats = parsed
    m = run_metrics(trips, stats, n_route_vehicles=4, depart_end_s=3600)
    assert m["total_nox_g"] == pytest.approx(2.0)  # 300 + 1700 mg
    assert m["total_co2_kg"] == pytest.approx(1.0)  # 1,000,000 mg
    assert m["vkm_total"] == pytest.approx(4.5)
    assert m["nox_mg_per_vkm"] == pytest.approx(2000 / 4.5)
    assert m["arrived"] == 2 and m["unfinished"] == 1
    assert m["completion_rate"] == pytest.approx(0.5)
    assert m["teleport_frac"] == pytest.approx(0.25)
    assert m["mean_tt_s"] == pytest.approx(200.0)


def test_speed_ratio_formula(parsed) -> None:
    trips, _ = parsed
    assert speed_ratio(trips, 3600) == pytest.approx((60 + 240) / (100 + 300))


class _Fixed(EffortController):
    name = "fixed"


@pytest.mark.parametrize("alpha", [0.0, 0.5, 1.0])
def test_effort_formula(alpha) -> None:
    c = _Fixed({"alpha": alpha, "tau_avg_s": 180, "router": "traveltime_weights"})
    tau = np.array([10.0, 20.0, 30.0])
    m = np.array([1.0, 0.0, 5.0])
    eff = c.efforts(tau, m)
    expected = (1 - alpha) * tau + alpha * tau.mean() * m / m.mean()
    np.testing.assert_allclose(eff, expected)
    if alpha == 0.0:
        np.testing.assert_allclose(eff, tau)


def test_effort_without_emission_information_is_travel_time() -> None:
    c = _Fixed({"alpha": 0.7, "tau_avg_s": 180, "router": "traveltime_weights"})
    np.testing.assert_allclose(c.efforts(np.array([1.0, 2.0]), np.zeros(2)), [1.0, 2.0])


def test_alpha_out_of_range_rejected() -> None:
    with pytest.raises(ValueError):
        _Fixed({"alpha": 1.5, "tau_avg_s": 180, "router": "traveltime_weights"})


def test_compliance_is_deterministic_and_nested_by_vehicle() -> None:
    ids = [f"car{i}" for i in range(4000)]
    share = np.mean([compliant(v, 7, 0.25) for v in ids])
    assert 0.22 < share < 0.28
    assert [compliant(v, 7, 0.25) for v in ids[:50]] == [compliant(v, 7, 0.25) for v in ids[:50]]
    assert all(compliant(v, 7, 1.0) for v in ids[:10])


def test_run_id_ignores_logging_options() -> None:
    base = dict(experiment="x", scenario="s", level="l", seed=1, controller="static", protocol_version=1,
                density_per_h_km=10.0, route_sha256="ab")
    a = RunSpec(**base)
    b = RunSpec(**{**base, "reconcile": True, "backend": "traci", "experiment": "y"})
    c = RunSpec(**{**base, "seed": 2})
    assert a.run_id() == b.run_id() != c.run_id()
