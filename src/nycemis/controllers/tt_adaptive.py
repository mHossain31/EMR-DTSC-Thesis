"""C1 ``tt_adaptive``: SUMO's rerouting device, travel-time based (docs/SPECIFICATION.md 4.3).

Every vehicle gets the device (probability 1), rerouting period 60 s (the control tick). The edge-speed
adaptation uses the OSM Web Wizard's configuration (interval 10 s, 18 steps, i.e. a 180 s moving average). The device
reroutes inside SUMO; the controller samples the vehicles' remaining routes at each tick to count route changes.
``n_reroutes`` for this controller comes from tripinfo ``rerouteNo`` (filled in by the runner).
"""

from __future__ import annotations

import time

from nycemis.controllers.base import Controller, ControlLog, SimContext
from nycemis.sim.logger import Window


class TTAdaptiveController(Controller):
    name = "tt_adaptive"

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.period = int(self.params.get("reroute_period_s", 60))
        self.adapt_interval = int(self.params.get("adaptation_interval_s", 10))
        self.adapt_steps = int(self.params.get("adaptation_steps", 18))
        self.remaining: dict[str, tuple[str, ...]] = {}

    def sumo_options(self) -> list[str]:
        return ["--device.rerouting.probability", "1",
                "--device.rerouting.period", str(self.period),
                "--device.rerouting.adaptation-interval", str(self.adapt_interval),
                "--device.rerouting.adaptation-steps", str(self.adapt_steps)]

    def on_tick(self, t: float, window: Window | None, ctx: SimContext) -> None:
        t0 = time.perf_counter()
        tr = ctx.traci
        changes = 0
        current = {}
        for vid in tr.vehicle.getIDList():
            route = tr.vehicle.getRoute(vid)
            rem = tuple(route[max(tr.vehicle.getRouteIndex(vid), 0):])
            current[vid] = rem
            prev = self.remaining.get(vid)
            if prev is not None and not (len(rem) <= len(prev) and prev[len(prev) - len(rem):] == rem):
                changes += 1
        self.remaining = current
        self.route_changes += changes
        dt = time.perf_counter() - t0
        self.ctl_s += dt
        self._log_tick(ControlLog(t_s=t, route_changes=changes, ctl_ms=1000 * dt))
