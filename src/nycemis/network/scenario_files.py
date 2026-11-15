"""Ready-to-run scenario folder: GUI settings, default demand, ``.sumocfg``, smoke run, OpenDRIVE check.

``scenarios/<s>/`` holds only relative paths, so ``sumo-gui -c scenarios/<s>/<s>.sumocfg`` opens the scenario
from any checkout. The default demand uses the OSM Web Wizard's default car settings (12 vehicles per hour per km,
fringe factor 5, its common randomTrips options, seed 42) until M2 replaces it with the calibrated moderate level.
Experiment runs never use the default demand; they pass their own route files.
"""

from __future__ import annotations

import gzip
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from nycemis import env
from nycemis.config import base_config
from nycemis.network.build import net_path, report_dir
from nycemis.paths import rel, scenarios_dir

# Colour-scheme indices in sumo-gui 1.28, checked by the snapshot test (see docs/SUMO_API_NOTES.md):
# lane scheme 11 = "by NOx emissions", vehicle scheme 8 = "by speed".
GUI_LANE_SCHEME_NOX = 11
GUI_VEHICLE_SCHEME_SPEED = 8

# OSM Web Wizard defaults for cars (tools/webWizard/script.js: Settings("Cars", "passenger", 5, 12, true)) and its
# common randomTrips parameters (osmWebWizard.py: CP and vehicleParameters["passenger"]).
WIZARD_CAR_FRINGE_FACTOR = 5
WIZARD_CAR_COUNT_PER_H_KM = 12
WIZARD_VIA_EDGE_TYPES = ",".join(["highway.motorway", "highway.motorway_link", "highway.trunk_link",
                                  "highway.primary_link", "highway.secondary_link", "highway.tertiary_link"])
WIZARD_COMMON = ["--trip-attributes", 'departLane="best"', "--fringe-start-attributes", 'departSpeed="max"',
                 "--validate", "--remove-loops", "--via-edge-types", WIZARD_VIA_EDGE_TYPES]
WIZARD_PASSENGER = ["--vehicle-class", "passenger", "--vclass", "passenger", "--prefix", "veh",
                    "--min-distance", "300", "--min-distance.fringe", "10", "--allow-fringe.min-length", "1000",
                    "--lanes"]
WIZARD_DEFAULT_SEED = 42
TLS_ACTUATED_JAM_THRESHOLD = 30  # osmWebWizard.py makeConfigFile
MIN_SNAPSHOT_BYTES = 5000  # a blank render (screen asleep or locked) gives a PNG of a few dozen bytes


def folder(scenario: str) -> Path:
    return scenarios_dir() / scenario


def gui_settings_path(scenario: str) -> Path:
    return folder(scenario) / "gui-settings.xml"


def default_routes_path(scenario: str) -> Path:
    return folder(scenario) / f"{scenario}.default.rou.xml.gz"


def sumocfg_path(scenario: str) -> Path:
    return folder(scenario) / f"{scenario}.sumocfg"


def gui_settings_xml(snapshot: tuple[str, int] | None = None) -> str:
    snap = f'    <snapshot file="{snapshot[0]}" time="{snapshot[1]}"/>\n' if snapshot else ""
    return (
        "<viewsettings>\n"
        '    <scheme name="nycemis NOx">\n'
        f'        <edges laneEdgeMode="{GUI_LANE_SCHEME_NOX}"/>\n'
        f'        <vehicles vehicleMode="{GUI_VEHICLE_SCHEME_SPEED}"/>\n'
        '        <legend showSizeLegend="1" showColorLegend="1" showVehicleColorLegend="1"/>\n'
        "    </scheme>\n"
        '    <delay value="20"/>\n'
        f"{snap}"
        "</viewsettings>\n"
    )


def write_gui_settings(scenario: str) -> Path:
    path = gui_settings_path(scenario)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(gui_settings_xml(), encoding="utf-8")
    return path


def random_trips(net: Path, route_out: Path, seed: int, begin: int, end: int, insertion_density: float,
                 fringe_factor: float, class_args: list[str], extra: list[str] | None = None) -> dict:
    """Call SUMO's randomTrips.py (with duarouter via --validate) and return a summary of the routes written."""
    with tempfile.TemporaryDirectory(prefix="rtrips_") as tmp:
        trips = Path(tmp) / "trips.xml"
        routes = Path(tmp) / "routes.rou.xml"
        cmd = [sys.executable, str(env.sumo_tool("randomTrips.py")), "--net-file", str(net),
               "--output-trip-file", str(trips), "--route-file", str(routes), "--seed", str(seed),
               "--begin", str(begin), "--end", str(end), "--insertion-density", f"{insertion_density:g}",
               "--fringe-factor", f"{fringe_factor:g}", *WIZARD_COMMON, *class_args, *(extra or [])]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env.subprocess_env(), cwd=tmp, check=False)
        if proc.returncode != 0 or not routes.is_file():
            raise RuntimeError(f"randomTrips failed (exit {proc.returncode}):\n{(proc.stdout + proc.stderr)[-3000:]}")
        n_trips = trips.read_text(encoding="utf-8").count("<trip ")
        text = routes.read_text(encoding="utf-8")
        n_routes = text.count("<vehicle ")
        route_out.parent.mkdir(parents=True, exist_ok=True)
        if route_out.suffix == ".gz":
            with routes.open("rb") as src, gzip.open(route_out, "wb", compresslevel=9) as dst:
                shutil.copyfileobj(src, dst)
        else:
            shutil.copyfile(routes, route_out)
    return {"trips": n_trips, "vehicles_routed": n_routes, "unroutable": n_trips - n_routes,
            "stderr_tail": proc.stderr.strip().splitlines()[-5:]}


def write_default_demand(scenario: str) -> dict:
    cfg = base_config().protocol
    return random_trips(net_path(scenario), default_routes_path(scenario), seed=WIZARD_DEFAULT_SEED,
                        begin=cfg.depart_begin_s, end=cfg.depart_end_s,
                        insertion_density=WIZARD_CAR_COUNT_PER_H_KM, fringe_factor=WIZARD_CAR_FRINGE_FACTOR,
                        class_args=WIZARD_PASSENGER)


def sumocfg_xml(scenario: str) -> str:
    p = base_config().protocol
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- {scenario}: ready-to-run SUMO configuration (relative paths). Generated by `python -m nycemis net build`.
     The route file is the default demand; experiments pass their own route files and options. -->
<configuration>
    <input>
        <net-file value="{scenario}.net.xml.gz"/>
        <route-files value="{default_routes_path(scenario).name}"/>
    </input>
    <time>
        <begin value="{p.depart_begin_s}"/>
        <step-length value="{p.step_length_s:g}"/>
    </time>
    <processing>
        <time-to-teleport value="{p.time_to_teleport_s}"/>
        <collision.action value="{p.collision_action}"/>
        <tls.actuated.jam-threshold value="{TLS_ACTUATED_JAM_THRESHOLD}"/>
    </processing>
    <random_number>
        <seed value="{WIZARD_DEFAULT_SEED}"/>
    </random_number>
    <report>
        <no-step-log value="true"/>
        <duration-log.statistics value="true"/>
    </report>
    <gui_only>
        <gui-settings-file value="gui-settings.xml"/>
    </gui_only>
</configuration>
"""


def write_sumocfg(scenario: str) -> Path:
    path = sumocfg_path(scenario)
    path.write_text(sumocfg_xml(scenario), encoding="utf-8")
    return path


def gui_command(scenario: str) -> str:
    return f"sumo-gui -c {rel(sumocfg_path(scenario))}   (or: python -m nycemis gui --scenario {scenario})"


def smoke_run(scenario: str, seconds: int = 300) -> dict:
    """Run the scenario headless for ``seconds``; fail on any SUMO error."""
    with tempfile.TemporaryDirectory(prefix="smoke_") as tmp:
        stats = Path(tmp) / "stats.xml"
        cmd = [str(env.sumo_binary("sumo")), "-c", str(sumocfg_path(scenario)), "--end", str(seconds),
               "--statistic-output", str(stats)]
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env.subprocess_env(), check=False)
        wall = time.perf_counter() - t0
        out = proc.stdout + proc.stderr
        errors = [ln for ln in out.splitlines() if ln.startswith("Error")]
        warnings = [ln for ln in out.splitlines() if ln.startswith("Warning")]
        inserted = None
        if stats.is_file():
            m = re.search(r'<vehicles [^>]*inserted="(\d+)"', stats.read_text(encoding="utf-8"))
            inserted = int(m.group(1)) if m else None
    result = {"seconds_simulated": seconds, "exit_code": proc.returncode, "errors": len(errors),
              "errors_sample": errors[:10], "warnings_count": len(warnings), "warnings_sample": warnings[:10],
              "vehicles_inserted": inserted, "wall_s": round(wall, 2), "gui_command": gui_command(scenario)}
    (report_dir(scenario) / "smoke_run.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if proc.returncode != 0 or errors:
        raise RuntimeError(f"smoke run of {scenario} failed: {errors[:3] or out[-1000:]}")
    return result


def opendrive_check(scenario: str) -> dict:
    """Export to OpenDRIVE with and without --junctions.scurve-stretch 1.0 (docs/SPECIFICATION.md 6.2 step 5)."""
    variants = []
    rdir = report_dir(scenario)
    for name, extra in (("plain", []), ("scurve", ["--junctions.scurve-stretch", "1.0"])):
        out = rdir / f"{scenario}.{name}.xodr"
        opts = ["--output.original-names", *extra]
        cmd = [str(env.sumo_binary("netconvert")), "--sumo-net-file", str(net_path(scenario)),
               "--opendrive-output", str(out), *opts]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env.subprocess_env(), check=False)
        lines = (proc.stdout + proc.stderr).splitlines()
        variants.append({"variant": name, "options": opts, "ok": proc.returncode == 0 and out.is_file(),
                         "exit_code": proc.returncode, "bytes": out.stat().st_size if out.is_file() else 0,
                         "warnings_count": sum(ln.startswith("Warning") for ln in lines),
                         "errors": [ln for ln in lines if ln.startswith("Error")][:5],
                         "file": rel(out) if out.is_file() else None})
    result = {"scenario": scenario, "variants": variants, "ok": all(v["ok"] for v in variants)}
    (rdir / "opendrive_check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def gui_snapshot(scenario: str, at_s: int = 600, out_name: str = "gui_snapshot.png") -> Path:
    """Open sumo-gui with the scenario's settings, save a screenshot at ``at_s`` and quit (visual check)."""
    rdir = report_dir(scenario)
    shot = (rdir / out_name).resolve()
    with tempfile.TemporaryDirectory(prefix="gui_") as tmp:
        settings = Path(tmp) / "settings.xml"
        settings.write_text(gui_settings_xml(snapshot=(shot.as_posix(), at_s)), encoding="utf-8")
        cmd = [str(env.sumo_binary("sumo-gui")), "-c", str(sumocfg_path(scenario)), "--gui-settings-file",
               str(settings), "--start", "--quit-on-end", "--end", str(at_s + 2), "--window-size", "1400,1000"]
        subprocess.run(cmd, capture_output=True, text=True, env=env.subprocess_env(), timeout=300, check=False)
    if not shot.is_file():
        raise RuntimeError(f"sumo-gui did not write {shot}")
    if shot.stat().st_size < MIN_SNAPSHOT_BYTES:
        raise RuntimeError(f"{shot} is blank ({shot.stat().st_size} bytes); the display is probably asleep or locked")
    return shot
