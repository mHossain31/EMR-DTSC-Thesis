"""C2 ``random_reroute`` (placebo): effort = travel time x U(1, 1 + eta), drawn per edge per tick (docs/SPECIFICATION.md 4.3).

Same cadence and compliance as C4; eta is calibrated on validation seeds so that the route-change rate matches
``eco_ml``'s.
"""

from __future__ import annotations

import numpy as np

from nycemis.controllers.base import EffortController, SimContext
from nycemis.sim.logger import Window


class RandomRerouteController(EffortController):
    name = "random_reroute"

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.eta = float(self.params.get("eta", 0.3))
        if self.eta < 0:
            raise ValueError("eta must be >= 0")
        self.alpha = 0.0  # effort is travel time times noise

    def edge_costs(self, window: Window, ctx: SimContext) -> tuple[np.ndarray, np.ndarray]:
        tau = self.travel_time(window, ctx)
        noise = self._rng.uniform(1.0, 1.0 + self.eta, size=tau.shape)
        return tau * noise, np.zeros_like(tau)
