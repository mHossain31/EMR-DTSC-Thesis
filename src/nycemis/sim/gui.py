"""``python -m nycemis gui``: open sumo-gui on a scenario with the route file of one (level, seed), driven by one of
the study's controllers (docs/SPECIFICATION.md 5.2, 6.7).

The controller's parameters are those of the confirmatory experiment (``configs/experiments/confirmatory.yaml``:
alpha*, eta, the legacy threshold), resolved the way the experiment plan resolves them. The window uses the
scenario's ``gui-settings.xml`` (edges coloured by NOx, vehicles by speed). TraCI drives sumo-gui (libsumo has no
GUI); SUMO's outputs go to a temporary folder and nothing is written to ``results/``. Closing the window ends the run.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from nycemis import env
from nycemis.config import base_config
from nycemis.controllers import make_controller
from nycemis.controllers.base import SimContext
from nycemis.demand.generate import routes_path, vtypes_path
from nycemis.demand.levels import level_density
from nycemis.experiments.plan import _ensure_routes, _resolve_params, load_experiment
from nycemis.network.build import net_path
from nycemis.network.scenario_files import gui_settings_path
from nycemis.sim.logger import EdgeStateLogger, VehicleEmissionLogger
from nycemis.sim.netinfo import load_netinfo
from nycemis.sim.protocol import sumo_command

log = logging.getLogger(__name__)


def controller_params(scenario: str, controller: str, level: str, seed: int) -> dict:
    """The confirmatory experiment's parameters for ``controller``, resolved for this scenario, level and seed."""
    conditions = load_experiment("confirmatory").conditions
    match = [c for c in conditions if c.controller == controller]
    if not match:
        raise ValueError(f"unknown controller {controller!r}; one of {sorted({c.controller for c in conditions})}")
    return _resolve_params(scenario, match[0], level, seed)


def gui_command(scenario: str, level: str, seed: int, controller: str, outdir: Path) -> tuple[list[str], dict]:
    _ensure_routes(scenario, level, seed, level_density(scenario, level))
    params = controller_params(scenario, controller, level, seed)
    ctl = make_controller(controller, params, scenario)
    cmd = sumo_command(net_path(scenario), routes_path(scenario, level, seed), vtypes_path(scenario), seed, outdir,
                       gui=True, extra=[*ctl.sumo_options(), "--gui-settings-file", str(gui_settings_path(scenario))])
    return cmd, params


def launch(scenario: str, level: str, seed: int, controller: str) -> None:
    proto = base_config().protocol
    outdir = Path(tempfile.mkdtemp(prefix="nycemis_gui_"))
    cmd, params = gui_command(scenario, level, seed, controller, outdir)
    ctl = make_controller(controller, params, scenario)
    tr = env.load_backend("traci").module
    log.info("sumo-gui: %s, %s demand, seed %d, %s %s; outputs in %s", scenario, level, seed, controller, params,
             outdir)
    tr.start(cmd)
    info = load_netinfo(str(net_path(scenario)))
    vlog = VehicleEmissionLogger(tr, proto.step_length_s, extra_pollutants=True) \
        if ctl.needs_vehicle_emissions else None
    elog = EdgeStateLogger(tr, info, proto.control_tick_s, proto.step_length_s)
    ctx = SimContext(traci=tr, info=info, seed=seed, step_s=proto.step_length_s, tick_s=proto.control_tick_s,
                     depart_end_s=proto.depart_end_s, v_min_mps=proto.v_min_mps, vehicle_logger=vlog)
    ctl.reset(ctx)
    try:
        while tr.simulation.getMinExpectedNumber() > 0:
            tr.simulationStep()
            t = tr.simulation.getTime()
            if vlog is not None:
                vlog.on_step()
            elog.on_step()
            ctl.on_step(t, ctx)
            if int(round(t)) % proto.control_tick_s == 0:
                ctl.on_tick(t, elog.close_window(t), ctx)
    except tr.FatalTraCIError:
        log.info("sumo-gui was closed")
    finally:
        try:
            tr.close()
        except tr.FatalTraCIError:
            log.info("connection already closed")
