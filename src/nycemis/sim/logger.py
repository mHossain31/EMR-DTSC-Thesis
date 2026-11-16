"""In-process logging through libsumo/TraCI subscriptions (docs/SPECIFICATION.md 4.5, 6.6, 7.2).

``EdgeStateLogger`` reads every non-internal edge each step and aggregates 60 s windows: window k is the set of
states observed after the steps at times t_k - 59 ... t_k, so a decision taken at tick t_k uses window k only.
``VehicleEmissionLogger`` sums each vehicle's NOx (and other pollutants for the legacy controller) per step for the
reconciliation check. SUMO's emission getters return rates in mg/s; a step of ``dt`` seconds adds rate * dt mg.
The value -2^30 marks "unavailable" (a vehicle not on a lane, e.g. while teleporting); it is never added, and each
occurrence is counted and reported.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from nycemis.sim.netinfo import NetInfo

INVALID = -(2**30)


@dataclass
class Window:
    """Aggregates of one 60 s window over all edges (arrays in NetInfo order)."""

    k: int  # window index; it ends at time t_end_s
    t_end_s: float
    steps: int
    veh_s: np.ndarray  # vehicle-seconds
    speed_x_veh_s: np.ndarray  # sum over steps of (vehicle count * mean speed), m
    max_count: np.ndarray
    halting_s: np.ndarray  # sum over steps of halting vehicles
    waiting_sum_s: np.ndarray  # sum over steps of the summed waiting time of vehicles on the edge
    nox_mg: np.ndarray
    co2_mg: np.ndarray
    speed_time_sum: np.ndarray | None = None  # sum over steps of the edge mean speed (the limit when empty), m/s

    def time_mean_speed_mps(self) -> np.ndarray:
        """Edge mean speed averaged over time (the speed limit while the edge is empty), as SUMO's rerouting
        device samples it."""
        if self.speed_time_sum is None or self.steps == 0:
            raise ValueError("window has no time-mean speed")
        return self.speed_time_sum / self.steps

    def mean_speed_mps(self, limit_mps: np.ndarray) -> np.ndarray:
        """Vehicle-second weighted mean speed; the speed limit where the edge was empty."""
        return np.where(self.veh_s > 0, self.speed_x_veh_s / np.maximum(self.veh_s, 1e-12), limit_mps)


class EdgeStateLogger:
    """Subscribe to all non-internal edges and aggregate per-step states into windows."""

    def __init__(self, traci, info: NetInfo, window_s: int, step_s: float):
        self.traci = traci
        self.info = info
        self.window_s = window_s
        self.step_s = step_s
        c = traci.constants
        self.vars = (c.LAST_STEP_VEHICLE_NUMBER, c.LAST_STEP_MEAN_SPEED, c.LAST_STEP_VEHICLE_HALTING_NUMBER,
                     c.VAR_WAITING_TIME, c.VAR_NOXEMISSION, c.VAR_CO2EMISSION)
        for eid in info.edge_ids:
            traci.edge.subscribe(eid, list(self.vars))
        self._k = 0
        self._reset()
        self.cum_nox_mg = np.zeros(info.n)
        self.cum_co2_mg = np.zeros(info.n)
        self.cum_veh_s = np.zeros(info.n)
        self.window_nox: list[np.ndarray] = []
        self.window_co2: list[np.ndarray] = []
        self.window_veh_s: list[np.ndarray] = []
        self.invalid_values = 0

    @property
    def open_steps(self) -> int:
        return self._steps

    def _reset(self) -> None:
        n = self.info.n
        self._veh_s = np.zeros(n)
        self._spd = np.zeros(n)
        self._max = np.zeros(n)
        self._halt = np.zeros(n)
        self._wait = np.zeros(n)
        self._nox = np.zeros(n)
        self._co2 = np.zeros(n)
        self._spd_t = np.zeros(n)
        self._steps = 0

    def on_step(self) -> None:
        res = self.traci.edge.getAllSubscriptionResults()
        ids = self.info.edge_ids
        vn, ms, hn, wt, nx, cx = self.vars
        n = self.info.n
        cnt = np.fromiter((res[e][vn] for e in ids), float, n)
        spd = np.fromiter((res[e][ms] for e in ids), float, n)
        halt = np.fromiter((res[e][hn] for e in ids), float, n)
        wait = np.fromiter((res[e][wt] for e in ids), float, n)
        nox = np.fromiter((res[e][nx] for e in ids), float, n)
        co2 = np.fromiter((res[e][cx] for e in ids), float, n)
        bad = (nox <= INVALID) | (co2 <= INVALID)
        if bad.any():
            self.invalid_values += int(bad.sum())
            nox = np.where(bad, 0.0, nox)
            co2 = np.where(bad, 0.0, co2)
        dt = self.step_s
        self._veh_s += cnt * dt
        self._spd += cnt * spd * dt
        np.maximum(self._max, cnt, out=self._max)
        self._halt += halt * dt
        self._wait += wait * dt
        self._nox += nox * dt
        self._co2 += co2 * dt
        self._spd_t += spd
        self._steps += 1

    def close_window(self, t_end_s: float) -> Window:
        w = Window(k=self._k, t_end_s=t_end_s, steps=self._steps, veh_s=self._veh_s, speed_x_veh_s=self._spd,
                   max_count=self._max, halting_s=self._halt, waiting_sum_s=self._wait, nox_mg=self._nox,
                   co2_mg=self._co2, speed_time_sum=self._spd_t)
        self.cum_nox_mg += w.nox_mg
        self.cum_co2_mg += w.co2_mg
        self.cum_veh_s += w.veh_s
        self.window_nox.append(w.nox_mg)
        self.window_co2.append(w.co2_mg)
        self.window_veh_s.append(w.veh_s)
        self._k += 1
        self._reset()
        return w


@dataclass
class VehicleEmissionLogger:
    """Per-vehicle emission sums from vehicle subscriptions (subscribed on departure)."""

    traci: object
    step_s: float
    extra_pollutants: bool = False  # also CO2, CO, HC, PMx (the legacy controller's features)
    total_nox_mg: float = 0.0
    invalid_values: int = 0
    per_vehicle_nox_mg: dict = field(default_factory=dict)
    last: dict = field(default_factory=dict)  # vehicle -> {var: rate mg/s} of the current step

    def __post_init__(self) -> None:
        c = self.traci.constants
        self.v_nox = c.VAR_NOXEMISSION
        self.vars = [c.VAR_NOXEMISSION]
        if self.extra_pollutants:
            self.v_co2, self.v_co, self.v_hc, self.v_pmx = (c.VAR_CO2EMISSION, c.VAR_COEMISSION,
                                                            c.VAR_HCEMISSION, c.VAR_PMXEMISSION)
            self.vars += [self.v_co2, self.v_co, self.v_hc, self.v_pmx]

    def on_step(self) -> None:
        departed = self.traci.simulation.getDepartedIDList()
        for vid in departed:
            self.traci.vehicle.subscribe(vid, self.vars)
        # A new subscription reports from the next step on; read the departure step directly.
        res = dict(self.traci.vehicle.getAllSubscriptionResults())
        getters = {self.v_nox: self.traci.vehicle.getNOxEmission}
        if self.extra_pollutants:
            getters.update({self.v_co2: self.traci.vehicle.getCO2Emission, self.v_co: self.traci.vehicle.getCOEmission,
                            self.v_hc: self.traci.vehicle.getHCEmission, self.v_pmx: self.traci.vehicle.getPMxEmission})
        for vid in departed:
            if vid not in res:
                res[vid] = {var: get(vid) for var, get in getters.items()}
        self.last = res
        dt = self.step_s
        for vid, vals in res.items():
            rate = vals[self.v_nox]
            if rate <= INVALID:
                self.invalid_values += 1
                continue
            self.total_nox_mg += rate * dt
            self.per_vehicle_nox_mg[vid] = self.per_vehicle_nox_mg.get(vid, 0.0) + rate * dt
