"""SUMO discovery, the libsumo/TraCI backend adapter, and version capture.

``SUMO_HOME`` comes from the ``eclipse-sumo`` wheel (``import sumo; sumo.SUMO_HOME``), so nobody has to export it.
libsumo is preferred for speed; if it cannot be imported, TraCI over a socket is used with the same interface and a
WARNING is logged (the run records which backend it used). libsumo needs one simulation per process, so parallel
runs use multiprocessing with the ``spawn`` start method, never threads.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import os
import platform
import re
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import ModuleType

log = logging.getLogger(__name__)

EXE_SUFFIX = ".exe" if os.name == "nt" else ""

KEY_PACKAGES = (
    "eclipse-sumo",
    "libsumo",
    "traci",
    "sumolib",
    "numpy",
    "pandas",
    "pyarrow",
    "scipy",
    "scikit-learn",
    "lightgbm",
    "statsmodels",
    "matplotlib",
    "networkx",
    "pydantic",
    "typer",
    "lxml",
)


@lru_cache(maxsize=1)
def sumo_home() -> Path:
    """Return SUMO_HOME from the installed ``eclipse-sumo`` wheel; fall back to the environment variable."""
    try:
        import sumo  # type: ignore[import-not-found]

        home = Path(sumo.SUMO_HOME)
    except ImportError:
        env = os.environ.get("SUMO_HOME")
        if not env:
            raise RuntimeError(
                "SUMO not found: install the eclipse-sumo wheel (pip install eclipse-sumo) or set SUMO_HOME"
            ) from None
        log.warning("eclipse-sumo wheel not importable; using SUMO_HOME=%s from the environment", env)
        home = Path(env)
    if not (home / "bin").is_dir():
        raise RuntimeError(f"SUMO_HOME={home} has no bin/ directory")
    return home


def sumo_binary(name: str) -> Path:
    """Path of a SUMO executable such as ``sumo``, ``sumo-gui``, ``netconvert``, ``duarouter``."""
    path = sumo_home() / "bin" / f"{name}{EXE_SUFFIX}"
    if not path.is_file():
        raise FileNotFoundError(f"SUMO binary not found: {path}")
    return path


def sumo_tools_dir() -> Path:
    return sumo_home() / "tools"


def sumo_tool(relpath: str) -> Path:
    """Path of a SUMO Python tool, e.g. ``osmGet.py`` or ``randomTrips.py``."""
    path = sumo_home() / "tools" / relpath
    if not path.is_file():
        raise FileNotFoundError(f"SUMO tool not found: {path}")
    return path


def subprocess_env() -> dict[str, str]:
    """Environment for SUMO subprocesses: SUMO_HOME set explicitly so the tools find their data."""
    env = dict(os.environ)
    env["SUMO_HOME"] = str(sumo_home())
    return env


@lru_cache(maxsize=1)
def sumo_version() -> str:
    """Version string reported by the ``sumo`` binary (e.g. ``1.28.0``)."""
    out = subprocess.run(
        [str(sumo_binary("sumo")), "--version"], capture_output=True, text=True, check=True
    ).stdout
    # 1.28 prints "Eclipse SUMO sumo 1.28.0"; older releases print "Eclipse SUMO sumo Version 1.x.y".
    match = re.search(r"Eclipse SUMO sumo (?:Version\s+)?(\d+\.\d+\.\d+\S*)", out)
    if not match:
        raise RuntimeError(f"cannot parse SUMO version from: {out[:200]!r}")
    return match.group(1)


def package_versions() -> dict[str, str]:
    """Installed versions of the packages that affect results."""
    versions: dict[str, str] = {}
    for name in KEY_PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def platform_info() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "os": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "machine": platform.machine(),
    }


@dataclass(frozen=True)
class Backend:
    """A TraCI-compatible module plus the name of the backend actually loaded."""

    module: ModuleType
    name: str  # "libsumo" or "traci"


def load_backend(prefer: str = "libsumo") -> Backend:
    """Import libsumo (preferred) or TraCI. A fallback from libsumo to TraCI logs a WARNING."""
    if prefer not in {"libsumo", "traci"}:
        raise ValueError(f"unknown backend {prefer!r}")
    if prefer == "libsumo":
        try:
            module = importlib.import_module("libsumo")
            return Backend(module=module, name="libsumo")
        except ImportError as exc:
            log.warning("libsumo import failed (%s); falling back to TraCI sockets", exc)
    module = importlib.import_module("traci")
    return Backend(module=module, name="traci")
