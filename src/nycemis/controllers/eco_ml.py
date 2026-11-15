"""C4 ``eco_ml``: the C3 effort form with costs from the frozen ML forecast (docs/SPECIFICATION.md 4.3, 7.5).

At each tick the shared ``FeatureBuilder`` turns windows k, k-1, k-2 into F1 features; the forecaster returns
r_hat (mg per vehicle-second) and v_hat (m/s) for window k+1. The model is loaded before the run starts. In shadow
mode the controller computes and logs features and forecasts but applies nothing (train/serve parity test).
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from nycemis.controllers.base import EffortController, SimContext
from nycemis.features.builder import FeatureBuilder
from nycemis.sim.logger import Window


class Forecaster(Protocol):
    feature_set: str

    def predict(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (r_hat mg/veh-s, v_hat m/s) for each row of ``x``."""


class ToyForecaster:
    """Deterministic stand-in used only by tests until the real model is frozen in M5.

    r_hat = 1 + 2 * halting share (a monotone congestion proxy), v_hat = persistence of the window speed ratio.
    """

    feature_set = "F1"

    def __init__(self, names: list[str]):
        self.i_halt = names.index("halt_mean_l0")
        self.i_cnt = names.index("cnt_mean_l0")
        self.i_ratio = names.index("speed_ratio_l0")
        self.i_limit = names.index("speed_limit_mps")

    def predict(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        halt_share = x[:, self.i_halt] / np.maximum(x[:, self.i_cnt], 1.0)
        return 1.0 + 2.0 * halt_share, x[:, self.i_ratio] * x[:, self.i_limit]


class EcoMLController(EffortController):
    name = "eco_ml"

    def __init__(self, params: dict | None = None, forecaster: Forecaster | None = None):
        super().__init__(params)
        self.forecaster = forecaster
        self.shadow = bool(self.params.get("shadow", False))
        self.builder: FeatureBuilder | None = None
        self.feature_log: list[tuple[int, np.ndarray]] = []

    def reset(self, ctx: SimContext) -> None:
        super().reset(ctx)
        if self.forecaster is None:
            raise ValueError("eco_ml needs a forecaster (frozen model or, in tests, ToyForecaster)")
        self.builder = FeatureBuilder(ctx.info, ctx.tick_s, ctx.depart_end_s, self.forecaster.feature_set)

    def edge_costs(self, window: Window, ctx: SimContext) -> tuple[np.ndarray, np.ndarray]:
        tau = self.travel_time(window, ctx)
        self.builder.push(window)
        x = self.builder.features()
        if self.shadow:
            self.feature_log.append((window.k, x))
        r_hat, v_hat = self.forecaster.predict(x)
        r_hat = np.maximum(np.asarray(r_hat, dtype=float), 0.0)
        v_hat = np.asarray(v_hat, dtype=float)
        m = r_hat * ctx.info.length_m / np.maximum(v_hat, ctx.v_min_mps)
        return tau, m

    def on_tick(self, t: float, window: Window | None, ctx: SimContext) -> None:
        if self.shadow:
            if window is not None:
                self.edge_costs(window, ctx)
            return
        super().on_tick(t, window, ctx)
