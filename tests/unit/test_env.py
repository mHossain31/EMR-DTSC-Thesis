"""SUMO discovery and backend loading (docs/SPECIFICATION.md 6.1)."""

from __future__ import annotations

import re

import pytest

from nycemis import env
from nycemis.doctor import run_checks

pytestmark = pytest.mark.sumo


def test_sumo_home_from_wheel() -> None:
    home = env.sumo_home()
    assert (home / "bin").is_dir()
    assert (home / "tools").is_dir()
    assert (home / "data" / "typemap").is_dir()


def test_sumo_version_parses() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+.*", env.sumo_version())


def test_binaries_and_tools_present() -> None:
    for name in ("sumo", "sumo-gui", "netconvert", "netgenerate", "duarouter"):
        assert env.sumo_binary(name).is_file()
    for tool in ("osmGet.py", "osmBuild.py", "osmWebWizard.py", "randomTrips.py"):
        assert env.sumo_tool(tool).is_file()


def test_libsumo_backend_loads() -> None:
    backend = env.load_backend("libsumo")
    assert backend.name == "libsumo"
    assert hasattr(backend.module.vehicle, "rerouteEffort")


def test_traci_backend_loads() -> None:
    backend = env.load_backend("traci")
    assert backend.name == "traci"


def test_unknown_backend_rejected() -> None:
    with pytest.raises(ValueError):
        env.load_backend("sumo-rpc")


def test_doctor_required_checks_pass_offline() -> None:
    failed = [c for c in run_checks(include_network=False) if c.required and not c.ok]
    assert not failed, failed
