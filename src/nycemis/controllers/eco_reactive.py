"""C3 ``eco_reactive``: effort from the measured per-vehicle NOx traversal cost (docs/SPECIFICATION.md 4.3).

r_e (mg per vehicle-second) and v_e (m/s) are measured over the last window, smoothed by an exponential moving
average across ticks (weight ``ema`` on the new window, 0.5 by default, edges with no vehicles keep their previous
value), then shrunk toward a road-class prior with weight w = vs / (vs + 30), vs = vehicle-seconds observed in the
window. The prior of a road class is its vehicle-second weighted mean over everything observed so far in this run
(online, no files); before any observation the all-edge mean is used, and before that the cost is zero, which
makes the effort pure travel time.
m_e = r_e * L_e / max(v_e, v_min) (mg per vehicle traversal).
"""

from __future__ import annotations

import numpy as np

from nycemis.controllers.base import EffortController, SimContext
from nycemis.sim.logger import Window

SHRINK_VS = 30.0


class EcoReactiveController(EffortController):
    name = "eco_reactive"

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.ema = float(self.params.get("ema", 0.5))
        self.r_ema: np.ndarray | None = None
        self.v_ema: np.ndarray | None = None
        self.class_nox = np.zeros(5)
        self.class_vs = np.zeros(5)
        self.class_dist = np.zeros(5)  # vehicle-metres, for the class mean speed

    def measured(self, window: Window, ctx: SimContext) -> tuple[np.ndarray, np.ndarray]:
        info = ctx.info
        vs = window.veh_s
        seen = vs > 0
        r = np.where(seen, window.nox_mg / np.maximum(vs, 1e-12), np.nan)
        v = np.where(seen, window.speed_x_veh_s / np.maximum(vs, 1e-12), np.nan)
        if self.r_ema is None:
            self.r_ema = np.full(info.n, np.nan)
            self.v_ema = np.full(info.n, np.nan)
        a = self.ema
        self.r_ema = np.where(seen, np.where(np.isnan(self.r_ema), r, a * r + (1 - a) * self.r_ema), self.r_ema)
        self.v_ema = np.where(seen, np.where(np.isnan(self.v_ema), v, a * v + (1 - a) * self.v_ema), self.v_ema)
        cls = info.road_class.astype(int)
        np.add.at(self.class_nox, cls, window.nox_mg)
        np.add.at(self.class_vs, cls, vs)
        np.add.at(self.class_dist, cls, window.speed_x_veh_s)
        total_vs = self.class_vs.sum()
        if total_vs > 0:
            global_r = self.class_nox.sum() / total_vs
            global_v = self.class_dist.sum() / total_vs
        else:
            global_r, global_v = 0.0, float(np.mean(info.speed_limit_mps))
        prior_r = np.where(self.class_vs > 0, self.class_nox / np.maximum(self.class_vs, 1e-12), global_r)[cls]
        prior_v = np.where(self.class_vs > 0, self.class_dist / np.maximum(self.class_vs, 1e-12), global_v)[cls]
        w = vs / (vs + SHRINK_VS)
        r_hat = np.where(np.isnan(self.r_ema), prior_r, w * self.r_ema + (1 - w) * prior_r)
        v_hat = np.where(np.isnan(self.v_ema), prior_v, w * self.v_ema + (1 - w) * prior_v)
        return r_hat, v_hat

    def edge_costs(self, window: Window, ctx: SimContext) -> tuple[np.ndarray, np.ndarray]:
        tau = self.travel_time(window, ctx)
        r_hat, v_hat = self.measured(window, ctx)
        m = r_hat * ctx.info.length_m / np.maximum(v_hat, ctx.v_min_mps)
        return tau, m
