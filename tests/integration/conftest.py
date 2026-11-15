"""Shared fixtures for integration tests on the smoke scenario (3x3 netgenerate grid)."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from nycemis.config import base_config
from nycemis.demand.generate import generate, routes_path, vtypes_path
from nycemis.network.build import net_path
from nycemis.sim.protocol import sumo_command
from nycemis.sim.run_spec import RunSpec

SMOKE_DENSITY = 60.0
SMOKE_LEVEL = "smoke"


def smoke_routes(seed: int) -> dict:
    out = routes_path("smoke", SMOKE_LEVEL, seed)
    summary = out.with_name(out.name.replace(".rou.xml.gz", ".summary.json"))
    if out.is_file() and summary.is_file():
        meta = json.loads(summary.read_text(encoding="utf-8"))
        if meta["density_per_h_km"] == SMOKE_DENSITY:
            return meta
    return generate("smoke", SMOKE_DENSITY, seed, out, level=SMOKE_LEVEL)


def smoke_spec(controller: str, seed: int = 1, **kw) -> RunSpec:
    meta = smoke_routes(seed)
    return RunSpec(experiment="pytest", scenario="smoke", level=SMOKE_LEVEL, seed=seed, controller=controller,
                   protocol_version=base_config().protocol_version, density_per_h_km=SMOKE_DENSITY,
                   route_sha256=meta["sha256"], **kw)


@pytest.fixture
def libsumo_smoke() -> Iterator:
    """A started libsumo simulation of the smoke scenario (seed 1); closed after the test."""
    import libsumo as traci

    smoke_routes(1)
    out = Path(tempfile.mkdtemp(prefix="pytest_sumo_"))
    traci.start(sumo_command(net_path("smoke"), routes_path("smoke", SMOKE_LEVEL, 1), vtypes_path("smoke"), 1, out))
    traci._outdir = out
    try:
        yield traci
    finally:
        if traci.isLoaded():
            traci.close()


def start_libsumo(extra: list[str] | None = None):
    import libsumo as traci

    smoke_routes(1)
    out = Path(tempfile.mkdtemp(prefix="pytest_sumo_"))
    traci.start(sumo_command(net_path("smoke"), routes_path("smoke", SMOKE_LEVEL, 1), vtypes_path("smoke"), 1, out,
                             extra=extra))
    return traci, out
