"""Controller interface and the effort-routing mechanics shared by C2-C4 (docs/SPECIFICATION.md 4.3, 5.4).

A controller never reads files during a run; models and priors are loaded before the simulation starts. Stochastic
choices use a ``numpy.random.Generator`` seeded from (run seed, controller name).

Effort routing: at every control tick the controller computes one effort per non-internal edge and sets it with
``edge.setEffort`` without begin/end (valid for the whole simulation; repeated calls overwrite). After every update
it checks ``edge.getEffort >= 0`` on all edges (-1 means unset, and an unset edge would look free). Vehicles are
rerouted with ``vehicle.rerouteEffort`` once per reroute period, at a deterministic per-vehicle offset, starting
only after the first effort update. Vehicles on internal edges or on their last two edges are skipped. No
rerouting device is attached to these vehicles: device vehicles ignore efforts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from nycemis.demand.generate import derived_seed
from nycemis.sim.logger import Window
from nycemis.sim.netinfo import NetInfo


@dataclass
class ControlLog:
    t_s: float
    reroute_calls: int = 0
    route_changes: int = 0
    failures: int = 0
    ctl_ms: float = 0.0
    extra: dict = field(default_factory=dict)


@dataclass
class SimContext:
    traci: object
    info: NetInfo
    seed: int
    step_s: float
    tick_s: int
    depart_end_s: float
    v_min_mps: float
    vehicle_logger: object | None = None


class Controller:
    name = "base"
    needs_edge_state = False
    needs_vehicle_emissions = False

    def __init__(self, params: dict | None = None):
        self.params = dict(params or {})
        self.reroute_calls = 0
        self.route_changes = 0
        self.failures = 0
        self.ctl_s = 0.0
        self.ticks = 0
        self.tick_logs: list[ControlLog] = []

    def sumo_options(self) -> list[str]:
        return []

    def rng(self, ctx: SimContext) -> np.random.Generator:
        return np.random.Generator(np.random.PCG64(derived_seed(ctx.seed, self.name, "controller")))

    def reset(self, ctx: SimContext) -> None:
        self.ctx = ctx

    def on_step(self, t: float, ctx: SimContext) -> None:
        """Called after every simulation step."""

    def on_tick(self, t: float, window: Window | None, ctx: SimContext) -> None:
        """Called at every control tick (after on_step of that step)."""

    def _log_tick(self, log: ControlLog) -> None:
        self.tick_logs.append(log)
        self.ticks += 1

    def summary(self) -> dict:
        return {
            "controller": self.name,
            "n_reroutes": self.reroute_calls,
            "route_changes": self.route_changes,
            "route_change_rate": self.route_changes / self.reroute_calls if self.reroute_calls else float("nan"),
            "reroute_failures": self.failures,
            "ctl_ms_per_tick": 1000.0 * self.ctl_s / self.ticks if self.ticks else 0.0,
        }


def compliant(vid: str, seed: int, p: float) -> bool:
    """Deterministic compliance: the same vehicles comply under every controller for a given (seed, p)."""
    if p >= 1.0:
        return True
    return derived_seed(vid, seed, f"compliance:{p:g}") / float(2**31 - 1) < p


class EffortController(Controller):
    """Common mechanics of C2-C4: efforts on all edges at each tick, staggered ``rerouteEffort`` per vehicle."""

    needs_edge_state = True

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.alpha = float(self.params.get("alpha", 0.0))
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError(f"alpha must lie in [0, 1], got {self.alpha}")
        self.period = int(self.params.get("reroute_period_s", 60))
        self.compliance = float(self.params.get("compliance", 1.0))
        self.efforts_set = False
        self.buckets: dict[int, set[str]] = {k: set() for k in range(self.period)}
        self.offset: dict[str, int] = {}
        self.last_effort: np.ndarray | None = None

    def reset(self, ctx: SimContext) -> None:
        super().reset(ctx)
        self._rng = self.rng(ctx)

    # ---- per-step bookkeeping and staggered rerouting
    def on_step(self, t: float, ctx: SimContext) -> None:
        tr = ctx.traci
        for vid in tr.simulation.getDepartedIDList():
            if compliant(vid, ctx.seed, self.compliance):
                off = derived_seed(vid, "stagger") % self.period
                self.offset[vid] = off
                self.buckets[off].add(vid)
        for vid in tr.simulation.getArrivedIDList():
            off = self.offset.pop(vid, None)
            if off is not None:
                self.buckets[off].discard(vid)
        if not self.efforts_set:
            return
        t0 = time.perf_counter()
        for vid in sorted(self.buckets[int(round(t)) % self.period]):
            self._reroute(tr, vid)
        self.ctl_s += time.perf_counter() - t0

    def _reroute(self, tr, vid: str) -> None:
        road = tr.vehicle.getRoadID(vid)
        if not road or road.startswith(":"):
            return
        route = tr.vehicle.getRoute(vid)
        idx = tr.vehicle.getRouteIndex(vid)
        if idx < 0 or idx >= len(route) - 2:
            return
        before = route[idx:]
        tr.vehicle.rerouteEffort(vid)
        after_route = tr.vehicle.getRoute(vid)
        after = after_route[tr.vehicle.getRouteIndex(vid):]
        self.reroute_calls += 1
        if tuple(after) != tuple(before):
            self.route_changes += 1

    # ---- per-tick effort update
    def edge_costs(self, window: Window, ctx: SimContext) -> tuple[np.ndarray, np.ndarray]:
        """Return (tau_s, m_mg): travel time and per-vehicle NOx traversal cost per edge. Subclasses override."""
        raise NotImplementedError

    def travel_time(self, window: Window, ctx: SimContext) -> np.ndarray:
        """Window-mean travel time L / max(v, v_min), floored at free-flow time L / v_limit."""
        info = ctx.info
        v = window.mean_speed_mps(info.speed_limit_mps)
        tau = info.length_m / np.maximum(v, ctx.v_min_mps)
        return np.maximum(tau, info.freeflow_tt_s)

    def efforts(self, tau: np.ndarray, m: np.ndarray) -> np.ndarray:
        tau_bar = float(tau.mean())
        if self.alpha == 0.0:
            return tau.copy()
        m_bar = float(m.mean())
        if m_bar <= 0:
            return tau.copy()  # no emission information yet: pure travel time
        return (1.0 - self.alpha) * tau + self.alpha * tau_bar * (m / m_bar)

    def on_tick(self, t: float, window: Window | None, ctx: SimContext) -> None:
        if window is None:
            return
        t0 = time.perf_counter()
        tau, m = self.edge_costs(window, ctx)
        eff = self.efforts(tau, m)
        if not np.all(np.isfinite(eff)) or (eff < 0).any():
            raise ValueError(f"{self.name}: invalid efforts at t={t}")
        tr = ctx.traci
        for eid, value in zip(ctx.info.edge_ids, eff, strict=True):
            tr.edge.setEffort(eid, float(value))
        unset = [eid for eid in ctx.info.edge_ids if tr.edge.getEffort(eid, t) < 0]
        if unset:
            raise RuntimeError(f"{self.name}: {len(unset)} edges without effort after update (e.g. {unset[:3]})")
        self.efforts_set = True
        self.last_effort = eff
        dt = time.perf_counter() - t0
        self.ctl_s += dt
        self._log_tick(ControlLog(t_s=t, ctl_ms=1000 * dt,
                                  extra={"effort_mean": float(eff.mean()), "m_mean_mg": float(m.mean())}))
