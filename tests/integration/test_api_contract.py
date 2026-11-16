"""API-contract tests (docs/SPECIFICATION.md P7, 9.2): every SUMO call the harness relies on behaves as documented.

Findings are recorded in docs/SUMO_API_NOTES.md.
"""

from __future__ import annotations

import pytest

from nycemis.sim.metrics import parse_tripinfo
from tests.integration.conftest import start_libsumo

pytestmark = pytest.mark.sumo


def _advance_until_long_route(tr, min_remaining: int = 5) -> tuple[str, list[str], int]:
    for _ in range(600):
        tr.simulationStep()
        for vid in tr.vehicle.getIDList():
            route = list(tr.vehicle.getRoute(vid))
            idx = tr.vehicle.getRouteIndex(vid)
            if not tr.vehicle.getRoadID(vid).startswith(":") and len(route) - idx >= min_remaining:
                return vid, route, idx
    raise AssertionError("no vehicle with a long remaining route found")


def _set_all_efforts(tr, value_of) -> None:
    for e in tr.edge.getIDList():
        if not e.startswith(":"):
            tr.edge.setEffort(e, value_of(e))


def test_effort_unset_is_minus_one_and_set_overwrites(libsumo_smoke) -> None:
    tr = libsumo_smoke
    tr.simulationStep()
    edge = next(e for e in tr.edge.getIDList() if not e.startswith(":"))
    assert tr.edge.getEffort(edge, 0.0) == -1.0
    tr.edge.setEffort(edge, 7.0)
    assert tr.edge.getEffort(edge, 1.0) == 7.0
    assert tr.edge.getEffort(edge, 100000.0) == 7.0  # no begin/end: valid for the whole simulation
    tr.edge.setEffort(edge, 3.0)
    assert tr.edge.getEffort(edge, 1.0) == 3.0  # overwritten, not accumulated


def test_reroute_effort_avoids_expensive_edge(libsumo_smoke) -> None:
    tr = libsumo_smoke
    vid, route, idx = _advance_until_long_route(tr)
    _set_all_efforts(tr, lambda e: tr.lane.getLength(f"{e}_0"))
    target = route[idx + 2]
    tr.edge.setEffort(target, 1e9)
    tr.vehicle.rerouteEffort(vid)
    new = tr.vehicle.getRoute(vid)[tr.vehicle.getRouteIndex(vid):]
    assert target not in new


def test_adapted_traveltime_weights_and_reroute_traveltime(libsumo_smoke) -> None:
    """Global travel-time weights (edge.adaptTraveltime without begin/end) are honoured by
    vehicle.rerouteTraveltime(currentTravelTimes=False); an unset weight reads -1 and a new value overwrites."""
    tr = libsumo_smoke
    vid, route, idx = _advance_until_long_route(tr)
    edge = route[idx + 2]
    assert tr.edge.getAdaptedTraveltime(edge, 0.0) == -1.0
    for e in tr.edge.getIDList():
        if not e.startswith(":"):
            tr.edge.adaptTraveltime(e, tr.lane.getLength(f"{e}_0") / tr.lane.getMaxSpeed(f"{e}_0"))
    tr.edge.adaptTraveltime(edge, 1e9)
    assert tr.edge.getAdaptedTraveltime(edge, 100000.0) == 1e9
    tr.vehicle.rerouteTraveltime(vid, False)
    new = tr.vehicle.getRoute(vid)[tr.vehicle.getRouteIndex(vid):]
    assert edge not in new
    tr.edge.adaptTraveltime(edge, 2.0)
    assert tr.edge.getAdaptedTraveltime(edge, 1.0) == 2.0


def test_device_vehicle_reroute_effort_behaviour() -> None:
    """Record what rerouteEffort does for a vehicle that carries a rerouting device."""
    tr, _ = start_libsumo(["--device.rerouting.probability", "1"])
    try:
        vid, route, idx = _advance_until_long_route(tr)
        assert tr.vehicle.getParameter(vid, "has.rerouting.device") == "true"
        _set_all_efforts(tr, lambda e: tr.lane.getLength(f"{e}_0"))
        target = route[idx + 2]
        tr.edge.setEffort(target, 1e9)
        tr.vehicle.rerouteEffort(vid)
        new = tr.vehicle.getRoute(vid)[tr.vehicle.getRouteIndex(vid):]
        # SUMO 1.28: an explicit rerouteEffort call uses the global efforts even for a device vehicle (the device's
        # own periodic rerouting minimises travel time and never reads efforts). C2-C4 attach no device anyway.
        assert new and new[0] == tr.vehicle.getRoadID(vid)
        assert target not in new
    finally:
        tr.close()


def test_device_periodic_rerouting_is_travel_time_based() -> None:
    """A device vehicle that is never rerouted by TraCI keeps an edge whose effort is huge (efforts unused)."""
    tr, _ = start_libsumo(["--device.rerouting.probability", "1", "--device.rerouting.period", "10"])
    try:
        vid, route, idx = _advance_until_long_route(tr, min_remaining=6)
        _set_all_efforts(tr, lambda e: tr.lane.getLength(f"{e}_0"))
        target = route[idx + 4]
        tr.edge.setEffort(target, 1e9)
        for _ in range(30):  # three device reroutes while the vehicle is still before the target edge
            tr.simulationStep()
            if vid not in tr.vehicle.getIDList() or target in tr.vehicle.getRoute(vid)[:tr.vehicle.getRouteIndex(vid)]:
                break
        if vid in tr.vehicle.getIDList():
            assert target in tr.vehicle.getRoute(vid)
    finally:
        tr.close()


def test_vehicle_emission_getters_are_mg_per_s(libsumo_smoke) -> None:
    tr = libsumo_smoke
    sums: dict[str, float] = {}
    while tr.simulation.getMinExpectedNumber() > 0:
        tr.simulationStep()
        for vid in tr.vehicle.getIDList():
            rate = tr.vehicle.getNOxEmission(vid)
            if rate > -(2**30):
                sums[vid] = sums.get(vid, 0.0) + rate * 1.0  # step length 1 s
    out = tr._outdir
    tr.close()
    trips = parse_tripinfo(out / "tripinfo.xml").set_index("id")
    total_step, total_trip = sum(sums.values()), trips.nox_mg.sum()
    assert abs(total_step - total_trip) / total_trip < 0.001  # rates in mg/s times 1 s add up to tripinfo mg


def test_edge_traveltime_semantics(libsumo_smoke) -> None:
    tr = libsumo_smoke
    for _ in range(300):
        tr.simulationStep()
    checked_busy = checked_empty = 0
    for e in tr.edge.getIDList():
        if e.startswith(":"):
            continue
        length = tr.lane.getLength(f"{e}_0")
        n = tr.edge.getLastStepVehicleNumber(e)
        tt = tr.edge.getTraveltime(e)
        if n > 0 and tr.edge.getLastStepMeanSpeed(e) > 0.1:
            assert tt == pytest.approx(length / tr.edge.getLastStepMeanSpeed(e), rel=1e-6)
            checked_busy += 1
        elif n == 0:
            assert tt == pytest.approx(length / tr.lane.getMaxSpeed(f"{e}_0"), rel=1e-6)
            checked_empty += 1
    assert checked_busy > 0 and checked_empty > 0


def test_find_route_default_reproduces_static_route(libsumo_smoke) -> None:
    """D2: default findRoute (no weights, no device) mostly returns the free-flow route the vehicle already has."""
    tr = libsumo_smoke
    same = total = 0
    for _ in range(900):
        tr.simulationStep()
        for vid in tr.simulation.getDepartedIDList():
            route = tr.vehicle.getRoute(vid)
            found = tr.simulation.findRoute(route[0], route[-1]).edges
            total += 1
            same += tuple(found) == tuple(route)
    assert total > 20
    assert same / total >= 0.9


def test_tripinfo_emission_attributes(libsumo_smoke) -> None:
    tr = libsumo_smoke
    while tr.simulation.getMinExpectedNumber() > 0:
        tr.simulationStep()
    out = tr._outdir
    tr.close()
    text = (out / "tripinfo.xml").read_text(encoding="utf-8")
    for attr in ("NOx_abs", "CO2_abs", "CO_abs", "HC_abs", "PMx_abs", "fuel_abs"):
        assert attr in text
