"""The matched simulation protocol (docs/SPECIFICATION.md 4.4): one function builds the SUMO options for every run.

Every condition of a (scenario, level, seed) shares the network, the byte-identical route file, the vType file,
the SUMO seed, the emission model and this option list; controllers add only their own options (C1's rerouting
device). Runs continue until every vehicle has arrived, with a hard cap. ``--emission-output`` is never used.
"""

from __future__ import annotations

from pathlib import Path

from nycemis import env
from nycemis.config import base_config
from nycemis.network.scenario_files import TLS_ACTUATED_JAM_THRESHOLD


def sumo_options(net: Path, routes: Path, vtypes: Path, seed: int, outdir: Path,
                 extra: list[str] | None = None) -> list[str]:
    """Options (without the binary) for one run; outputs go to ``outdir``."""
    p = base_config().protocol
    return [
        "--net-file", str(net),
        "--route-files", str(routes),
        "--additional-files", str(vtypes),
        "--begin", str(p.depart_begin_s),
        "--end", str(p.cap_s),
        "--step-length", f"{p.step_length_s:g}",
        "--seed", str(seed),
        "--time-to-teleport", str(p.time_to_teleport_s),
        "--collision.action", p.collision_action,
        "--tls.actuated.jam-threshold", str(TLS_ACTUATED_JAM_THRESHOLD),
        "--device.emissions.probability", "1",
        "--tripinfo-output", str(outdir / "tripinfo.xml"),
        "--tripinfo-output.write-unfinished", "true",
        "--statistic-output", str(outdir / "stats.xml"),
        "--no-step-log", "true",
        "--duration-log.statistics", "true",
        *(extra or []),
    ]


def sumo_command(net: Path, routes: Path, vtypes: Path, seed: int, outdir: Path, gui: bool = False,
                 extra: list[str] | None = None) -> list[str]:
    binary = env.sumo_binary("sumo-gui" if gui else "sumo")
    return [str(binary), *sumo_options(net, routes, vtypes, seed, outdir, extra)]
