"""C5 ``legacy_ml``: the legacy rerouting rule under the matched protocol (docs/SPECIFICATION.md 7.4).

Every step, the NOx emission rate of every vehicle is predicted from its CO2, CO, HC and PMx rates (mg/s, the
legacy RF's features) in one batched call. Each vehicle whose prediction exceeds the threshold gets the legacy
treatment: ``simulation.findRoute(current edge, last edge of its route)`` with default arguments, then
``vehicle.setRoute``. No rerouting device is attached. A failed call is counted (the legacy code printed it) and
the run continues. A call "changes the route" when the new edge list differs from the vehicle's remaining route.

The threshold is given in mg/s. The primary C5 uses the quantile of training NOx at which the legacy run flagged
vehicle-steps (``docs/LEGACY_AUDIT.md``, D6); the literal 1.88 (mg/s) is a variant.
"""

from __future__ import annotations

import time
from typing import Protocol

import numpy as np

from nycemis.controllers.base import Controller, ControlLog, SimContext

FEATURES = ("co2", "co", "hc", "pmx")


class NoxPredictor(Protocol):
    def predict(self, x: np.ndarray) -> np.ndarray:
        """NOx rate (mg/s) per row of [CO2, CO, HC, PMx] rates (mg/s)."""


class LegacyMLController(Controller):
    name = "legacy_ml"
    needs_vehicle_emissions = True

    def __init__(self, params: dict | None = None, predictor: NoxPredictor | None = None):
        super().__init__(params)
        if "threshold_mg_s" not in self.params:
            raise ValueError("legacy_ml needs threshold_mg_s")
        self.threshold = float(self.params["threshold_mg_s"])
        self.predictor = predictor
        self.steps_flagged = 0
        self.vehicle_steps = 0
        self.failure_messages: dict[str, int] = {}

    def reset(self, ctx: SimContext) -> None:
        super().reset(ctx)
        if self.predictor is None:
            raise ValueError("legacy_ml needs a trained predictor")
        if ctx.vehicle_logger is None or not ctx.vehicle_logger.extra_pollutants:
            raise ValueError("legacy_ml needs the vehicle logger with all pollutants")

    def on_step(self, t: float, ctx: SimContext) -> None:
        t0 = time.perf_counter()
        vl = ctx.vehicle_logger
        rows, vids = [], []
        for vid, vals in vl.last.items():
            feats = (vals[vl.v_co2], vals[vl.v_co], vals[vl.v_hc], vals[vl.v_pmx])
            if min(feats) <= -(2**30):  # unavailable (vehicle not on a lane); counted by the logger
                continue
            rows.append(feats)
            vids.append(vid)
        self.vehicle_steps += len(vids)
        if not rows:
            self.ctl_s += time.perf_counter() - t0
            return
        pred = np.asarray(self.predictor.predict(np.asarray(rows, dtype=float)))
        flagged = [vid for vid, p in zip(vids, pred, strict=True) if p > self.threshold]
        self.steps_flagged += len(flagged)
        tr = ctx.traci
        exc_type = getattr(tr, "TraCIException", Exception)
        for vid in flagged:
            try:
                current = tr.vehicle.getRoadID(vid)
                route = tr.vehicle.getRoute(vid)
                idx = max(tr.vehicle.getRouteIndex(vid), 0)
                new = tr.simulation.findRoute(current, route[-1]).edges
                self.reroute_calls += 1
                if new:
                    tr.vehicle.setRoute(vid, new)
                    remaining = tuple(e for e in route[idx:] if not e.startswith(":"))
                    if tuple(e for e in new if not e.startswith(":")) != remaining:
                        self.route_changes += 1
            except exc_type as exc:  # the legacy code printed and continued; here it is counted
                self.failures += 1
                key = str(exc).split("'")[0][:80]
                self.failure_messages[key] = self.failure_messages.get(key, 0) + 1
        dt = time.perf_counter() - t0
        self.ctl_s += dt

    def on_tick(self, t: float, window, ctx: SimContext) -> None:
        self._log_tick(ControlLog(t_s=t, reroute_calls=self.reroute_calls, route_changes=self.route_changes,
                                  failures=self.failures))

    def summary(self) -> dict:
        s = super().summary()
        s.update({"legacy_flagged_vehicle_steps": self.steps_flagged, "legacy_vehicle_steps": self.vehicle_steps,
                  "legacy_flag_share": self.steps_flagged / self.vehicle_steps if self.vehicle_steps else 0.0,
                  "legacy_failure_messages": self.failure_messages})
        return s
