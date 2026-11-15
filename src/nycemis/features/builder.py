"""One ``FeatureBuilder`` for dataset generation and live control (docs/SPECIFICATION.md 7.1-7.2).

At decision time t_k the builder sees only windows k, k-1 and k-2 (each 60 s, ending at t_k, t_k - 60, t_k - 120).
F1 is sensor-realistic traffic state with no emission information; F2 adds lagged emission density and per-vehicle
emission rate. Targets for window k+1 are computed by ``targets()`` from that later window and are never an input.
"""

from __future__ import annotations

from collections import deque

import numpy as np

from nycemis.sim.logger import Window
from nycemis.sim.netinfo import NetInfo

LAGS = (0, 1, 2)  # windows k, k-1, k-2
TT_RATIO_CAP = 20.0
R_MASK_MIN_VEH_S = 10.0  # r_next is masked where the next window has fewer vehicle-seconds


def _window_state(w: Window | None, info: NetInfo, window_s: float) -> dict[str, np.ndarray]:
    n = info.n
    if w is None:  # before the third window exists: an empty network
        zeros = np.zeros(n)
        return {"cnt_mean": zeros, "cnt_max": zeros, "speed_ratio": np.ones(n), "halt_mean": zeros,
                "wait_mean": zeros, "tt_ratio": np.ones(n), "nox_dens": zeros, "nox_rate": zeros}
    speed = w.mean_speed_mps(info.speed_limit_mps)
    ratio = speed / info.speed_limit_mps
    return {
        "cnt_mean": w.veh_s / window_s,
        "cnt_max": w.max_count,
        "speed_ratio": ratio,
        "halt_mean": w.halting_s / window_s,
        "wait_mean": w.waiting_sum_s / window_s,
        "tt_ratio": np.minimum(1.0 / np.maximum(ratio, 1.0 / TT_RATIO_CAP), TT_RATIO_CAP),
        "nox_dens": w.nox_mg / info.lane_m,  # mg per lane-metre in the window
        "nox_rate": np.where(w.veh_s > 0, w.nox_mg / np.maximum(w.veh_s, 1e-12), 0.0),  # mg per vehicle-second
    }


TRAFFIC_KEYS = ("cnt_mean", "cnt_max", "speed_ratio", "halt_mean", "wait_mean", "tt_ratio")
EMISSION_KEYS = ("nox_dens", "nox_rate")


def feature_names(feature_set: str = "F1") -> list[str]:
    names = [f"{key}_l{lag}" for lag in LAGS for key in TRAFFIC_KEYS]
    names += ["up_cnt_mean", "up_speed_ratio", "down_cnt_mean", "down_speed_ratio"]
    names += ["length_m", "lanes", "speed_limit_mps", "road_class", "tls_downstream", "in_degree", "out_degree"]
    names += ["t_hours", "after_departures"]
    if feature_set == "F2":
        names += [f"{key}_l{lag}" for lag in LAGS for key in EMISSION_KEYS]
    elif feature_set != "F1":
        raise ValueError(f"unknown feature set {feature_set!r}")
    return names


class FeatureBuilder:
    """Keeps the last three windows and turns them into a feature matrix (edges x features)."""

    def __init__(self, info: NetInfo, window_s: float, depart_end_s: float, feature_set: str = "F1"):
        self.info = info
        self.window_s = window_s
        self.depart_end_s = depart_end_s
        self.feature_set = feature_set
        self.names = feature_names(feature_set)
        self.history: deque[Window] = deque(maxlen=len(LAGS))

    def push(self, w: Window) -> None:
        if self.history and w.k != self.history[-1].k + 1:
            raise ValueError(f"window {w.k} pushed after {self.history[-1].k}")
        self.history.append(w)

    def features(self) -> np.ndarray:
        """Features at the decision time that ends the most recent window."""
        if not self.history:
            raise ValueError("no window pushed yet")
        info = self.info
        latest = list(self.history)[::-1]  # k, k-1, k-2
        states = [_window_state(latest[i] if i < len(latest) else None, info, self.window_s) for i in LAGS]
        cols = []
        for lag in LAGS:
            cols += [states[lag][key] for key in TRAFFIC_KEYS]
        s0 = states[0]
        cols += [info.upstream_mean @ s0["cnt_mean"], info.upstream_mean @ s0["speed_ratio"],
                 info.downstream_mean @ s0["cnt_mean"], info.downstream_mean @ s0["speed_ratio"]]
        cols += [info.length_m, info.lanes, info.speed_limit_mps, info.road_class.astype(float),
                 info.tls_downstream.astype(float), info.in_degree, info.out_degree]
        t_k = latest[0].t_end_s
        cols += [np.full(info.n, t_k / 3600.0), np.full(info.n, float(t_k > self.depart_end_s))]
        if self.feature_set == "F2":
            for lag in LAGS:
                cols += [states[lag][key] for key in EMISSION_KEYS]
        x = np.column_stack(cols).astype(np.float32)
        if x.shape[1] != len(self.names):
            raise AssertionError("feature count does not match feature_names")
        return x


def targets(next_window: Window, info: NetInfo) -> dict[str, np.ndarray]:
    """Targets for window k+1 with masks (docs/SPECIFICATION.md 7.1)."""
    veh_s = next_window.veh_s
    return {
        "d_next": next_window.nox_mg / info.lane_m,  # mg per lane-metre in the 60 s window
        "r_next": np.where(veh_s >= R_MASK_MIN_VEH_S, next_window.nox_mg / np.maximum(veh_s, 1e-12), np.nan),
        "v_next": np.where(veh_s > 0, next_window.speed_x_veh_s / np.maximum(veh_s, 1e-12), np.nan),
        "veh_s_next": veh_s,
    }
