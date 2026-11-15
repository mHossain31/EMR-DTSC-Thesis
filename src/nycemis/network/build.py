"""Build a scenario network the way SUMO's OSM Web Wizard does, headless (docs/SPECIFICATION.md 6.2 step 2).

The options are not retyped from memory: ``DEFAULT_NETCONVERT_OPTS`` and the vehicle-class filter are read from
the installed ``osmBuild.py``, and the installed ``osmWebWizard.py`` is checked for the two additions it makes
(the base typemap ``osmNetconvert.typ.xml`` and ``--tls.default-type actuated``). The wizard's "Car-only Network"
choice maps to osmBuild's ``passenger`` filter (``--keep-edges.by-vclass passenger``); that is the mode used here,
because trucks and vans are routed only on edges that allow them. docs/SPECIFICATION.md additionally asks for the largest
connected component, which netconvert provides as ``--keep-edges.components 1`` (weakly connected; strong
connectivity is measured by ``validate.py``).

The smoke scenario is a 3x3 signalised grid from ``netgenerate`` instead.
"""

from __future__ import annotations

import importlib
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

from nycemis import env, manifest
from nycemis.config import ScenarioConfig
from nycemis.network.osm_fetch import osm_path
from nycemis.paths import data_dir, rel, repo_root, scenarios_dir

log = logging.getLogger(__name__)

WIZARD_TYPEMAP = "osmNetconvert.typ.xml"
WIZARD_TLS_SNIPPET = ",--tls.default-type,actuated"
WIZARD_VCLASS_MODE = "passenger"
EXTRA_OPTIONS = ["--keep-edges.components", "1"]
# Network repair (docs/DEVIATIONS.md #7): join junctions up to 20 m apart (netconvert default 10 m). The OSM import
# otherwise leaves clusters of signalised nodes a few metres apart, joined by edges of 0.2 m, which deadlock.
REPAIR_OPTIONS = ["--junctions.join-dist", "20"]


def net_path(scenario: str) -> Path:
    return scenarios_dir() / scenario / f"{scenario}.net.xml.gz"


def report_dir(scenario: str) -> Path:
    return data_dir() / "networks" / scenario


def _osm_build_module():
    tools = str(env.sumo_tools_dir())
    if tools not in sys.path:
        sys.path.insert(0, tools)
    return importlib.import_module("osmBuild")


def wizard_netconvert_options() -> dict:
    """Read the Web Wizard's netconvert options from the installed SUMO tools and check its additions."""
    osm_build = _osm_build_module()
    wizard_src = env.sumo_tool("osmWebWizard.py").read_text(encoding="utf-8")
    for needle in (WIZARD_TYPEMAP, WIZARD_TLS_SNIPPET, "osmBuild.DEFAULT_NETCONVERT_OPTS",
                   '"--vehicle-classes", "passenger"'):
        if needle not in wizard_src:
            raise RuntimeError(f"installed osmWebWizard.py no longer contains {needle!r}; re-read it")
    base = [o for o in osm_build.DEFAULT_NETCONVERT_OPTS.split(",") if o]
    tls = [o for o in WIZARD_TLS_SNIPPET.split(",") if o]
    vclass = list(osm_build.vclassRemove[WIZARD_VCLASS_MODE])
    return {
        "typemap": WIZARD_TYPEMAP,
        "osmBuild_DEFAULT_NETCONVERT_OPTS": base,
        "wizard_additions": tls,
        "vehicle_class_mode": WIZARD_VCLASS_MODE,
        "vehicle_class_options": vclass,
        "extra_options": EXTRA_OPTIONS,
        "repair_options": REPAIR_OPTIONS,
    }


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env.subprocess_env(), check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"{Path(cmd[0]).name} failed (exit {proc.returncode}):\n{proc.stderr[-3000:]}")
    return proc


def _relcmd(cmd: list[str]) -> list[str]:
    """Command with repo paths made relative and SUMO paths shown as ${SUMO_HOME}/..., for the build record."""
    root, home = str(repo_root()), str(env.sumo_home())
    out = []
    for part in cmd:
        p = part.replace(home, "${SUMO_HOME}").replace(root + "\\", "").replace(root + "/", "")
        out.append(p.replace("\\", "/"))
    return out


def build_osm(cfg: ScenarioConfig) -> dict:
    src = osm_path(cfg.id)
    if not manifest.verify(src):
        raise FileNotFoundError(f"{rel(src)} missing or not matching data/MANIFEST.json; run `net fetch` first")
    opts = wizard_netconvert_options()
    out = net_path(cfg.id)
    out.parent.mkdir(parents=True, exist_ok=True)
    typemap = env.sumo_home() / "data" / "typemap" / opts["typemap"]
    cmd = [
        str(env.sumo_binary("netconvert")),
        "--type-files", str(typemap),
        *opts["osmBuild_DEFAULT_NETCONVERT_OPTS"],
        *opts["wizard_additions"],
        "--osm-files", str(src),
        *opts["vehicle_class_options"],
        *opts["extra_options"],
        *opts["repair_options"],
        # Clip to the scenario box (edges with any part inside are kept); see docs/DESIGN.md, network build.
        "--keep-edges.in-geo-boundary", ",".join(f"{v:.6f}" for v in cfg.bbox),
        "--output-file", str(out),
    ]
    opts = {**opts, "clip_option": ["--keep-edges.in-geo-boundary", "bbox of the scenario config"]}
    return _finish(cfg, cmd, out, {"osm_extract": rel(src), "osm_sha256": manifest.sha256_file(src), **opts})


def build_grid(cfg: ScenarioConfig) -> dict:
    grid = cfg.grid
    if grid is None:
        raise ValueError(f"{cfg.id} has no grid spec")
    out = net_path(cfg.id)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(env.sumo_binary("netgenerate")),
        "--grid",
        "--grid.number", str(grid.number),
        "--grid.length", f"{grid.length_m:g}",
        "--grid.attach-length", f"{grid.attach_length_m:g}",
        "--default.lanenumber", str(grid.lanes),
        "--default.speed", f"{grid.speed_mps:g}",
        "--default-junction-type", "traffic_light",
        "--tls.default-type", "actuated",
        "--output-file", str(out),
    ]
    return _finish(cfg, cmd, out, {"grid": grid.model_dump()})


def _finish(cfg: ScenarioConfig, cmd: list[str], out: Path, extra: dict) -> dict:
    t0 = time.perf_counter()
    proc = _run(cmd, cwd=repo_root())
    warnings = [ln for ln in (proc.stderr + proc.stdout).splitlines() if ln.startswith("Warning")]
    record = {
        "scenario": cfg.id,
        "command": _relcmd(cmd),
        "sumo_version": env.sumo_version(),
        "seconds": round(time.perf_counter() - t0, 2),
        "net_file": rel(out),
        "net_sha256": manifest.sha256_file(out),
        "warnings_count": len(warnings),
        "warnings_sample": warnings[:20],
        **extra,
    }
    rdir = report_dir(cfg.id)
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "network_build.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    manifest.record(out, kind="network", scenario=cfg.id, sumo_version=record["sumo_version"])
    log.info("built %s in %.1f s (%d warnings)", rel(out), record["seconds"], len(warnings))
    return record


def build(cfg: ScenarioConfig) -> dict:
    if cfg.source == "osm":
        return build_osm(cfg)
    if cfg.source == "netgenerate":
        return build_grid(cfg)
    raise ValueError(f"unknown source {cfg.source!r}")
