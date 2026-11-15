"""Run one simulation for a ``RunSpec`` and write its outputs (docs/SPECIFICATION.md 4.4, 5.3).

One simulation per process (libsumo). The loop steps until no vehicle is expected any more or the cap is hit. At
every step: loggers, then the controller's per-step work; at every control tick (every ``control_tick_s``) the
edge window closes, the dataset recorder and the controller's tick work run.

Outputs in the run directory: ``run.json`` (spec, versions, hashes, timings), ``run_metrics.json``,
``trip_metrics.parquet``, ``edge_5min.parquet``, ``edge_cumulative.parquet``, ``tick_log.parquet``, optional
``network_series.parquet`` (per-step network NOx, when the vehicle logger runs), ``edge_window.parquet`` (dataset
runs) and ``vehicle_records.parquet`` (legacy RF training data). ``DONE`` is written last by an atomic rename.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from nycemis import env
from nycemis.config import base_config
from nycemis.controllers import make_controller
from nycemis.controllers.base import SimContext
from nycemis.demand.generate import routes_path, vtypes_path
from nycemis.features.dataset import DatasetRecorder
from nycemis.manifest import sha256_file
from nycemis.network.build import net_path
from nycemis.paths import rel, repo_root, results_dir
from nycemis.sim.edge_tables import edge_tables
from nycemis.sim.logger import EdgeStateLogger, VehicleEmissionLogger
from nycemis.sim.metrics import parse_statistics, parse_tripinfo, run_metrics
from nycemis.sim.netinfo import load_netinfo
from nycemis.sim.protocol import sumo_command
from nycemis.sim.run_spec import RunSpec

log = logging.getLogger(__name__)


def run_dir(spec: RunSpec) -> Path:
    return results_dir() / "runs" / spec.experiment / spec.run_id()


def git_state() -> dict:
    root = str(repo_root())
    head = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    dirty = subprocess.run(["git", "-C", root, "status", "--porcelain", "--", "src", "configs"],
                           capture_output=True, text=True, check=False)
    return {"commit": head.stdout.strip() or None, "src_or_configs_dirty": bool(dirty.stdout.strip())}


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def execute(spec: RunSpec, outdir: Path | None = None) -> dict:
    """Run the simulation and write all outputs; returns the run metrics. Skips if DONE exists."""
    outdir = outdir or run_dir(spec)
    done = outdir / "DONE"
    if done.is_file():
        return json.loads((outdir / "run_metrics.json").read_text(encoding="utf-8"))
    outdir.mkdir(parents=True, exist_ok=True)
    cfg = base_config()
    proto = cfg.protocol
    if spec.protocol_version != cfg.protocol_version:
        raise ValueError(f"spec protocol {spec.protocol_version} != configured {cfg.protocol_version}")

    net, routes, vtypes = net_path(spec.scenario), routes_path(spec.scenario, spec.level, spec.seed), \
        vtypes_path(spec.scenario)
    route_sha = sha256_file(routes)
    if route_sha != spec.route_sha256:
        raise ValueError(f"route file {rel(routes)} hash {route_sha[:12]} != spec {spec.route_sha256[:12]}")
    n_route_vehicles = json.loads(routes.with_name(routes.name.replace(".rou.xml.gz", ".summary.json"))
                                  .read_text(encoding="utf-8"))["vehicles"]

    controller = make_controller(spec.controller, spec.params, spec.scenario)
    backend = env.load_backend(spec.backend)
    tr = backend.module
    cmd = sumo_command(net, routes, vtypes, spec.seed, outdir,
                       extra=[*controller.sumo_options(), "--log", str(outdir / "sumo.log")])
    info = load_netinfo(str(net))
    wall0 = time.perf_counter()
    if backend.name == "traci":
        tr.start(cmd, label=f"run_{spec.run_id()}")
    else:
        tr.start(cmd)
    need_vehicles = spec.reconcile or controller.needs_vehicle_emissions or spec.log_vehicle_records
    vlog = VehicleEmissionLogger(tr, proto.step_length_s,
                                 extra_pollutants=controller.needs_vehicle_emissions or spec.log_vehicle_records) \
        if need_vehicles else None
    elog = EdgeStateLogger(tr, info, proto.control_tick_s, proto.step_length_s)  # every run: edge tables
    recorder = DatasetRecorder(info, proto.control_tick_s, proto.depart_end_s) if spec.dataset else None
    ctx = SimContext(traci=tr, info=info, seed=spec.seed, step_s=proto.step_length_s, tick_s=proto.control_tick_s,
                     depart_end_s=proto.depart_end_s, v_min_mps=proto.v_min_mps, vehicle_logger=vlog)
    controller.reset(ctx)
    series_t, series_nox, series_running = [], [], []
    records: list[np.ndarray] = []
    t = 0.0
    try:
        while tr.simulation.getMinExpectedNumber() > 0 and t < proto.cap_s:
            tr.simulationStep()
            t = tr.simulation.getTime()
            if vlog is not None:
                before = vlog.total_nox_mg
                vlog.on_step()
                series_t.append(t)
                series_nox.append(vlog.total_nox_mg - before)
                series_running.append(len(vlog.last))
                if spec.log_vehicle_records:
                    records.append(_vehicle_rows(vlog, t))
            elog.on_step()
            controller.on_step(t, ctx)
            if int(round(t)) % proto.control_tick_s == 0:
                window = elog.close_window(t)
                if recorder is not None and window is not None:
                    recorder.on_window(window)
                controller.on_tick(t, window, ctx)
        if elog.open_steps:  # the last, partial window counts for the edge tables only
            elog.close_window(t)
    finally:
        tr.close()
    wall = time.perf_counter() - wall0
    return _finish(spec, outdir, controller, info, t, wall, backend.name, n_route_vehicles, vlog, elog, recorder,
                   (series_t, series_nox, series_running), records, {"net": sha256_file(net), "routes": route_sha,
                                                                     "vtypes": sha256_file(vtypes)})


def _vehicle_rows(vlog: VehicleEmissionLogger, t: float) -> np.ndarray:
    rows = []
    for vals in vlog.last.values():
        r = (vals[vlog.v_co2], vals[vlog.v_co], vals[vlog.v_hc], vals[vlog.v_pmx], vals[vlog.v_nox])
        if min(r) > -(2**30):
            rows.append((t, *r))
    return np.asarray(rows, dtype=np.float32).reshape(-1, 6)


def _finish(spec, outdir, controller, info, sim_end_s, wall, backend_name, n_route_vehicles, vlog, elog, recorder,
            series, records, hashes) -> dict:
    proto = base_config().protocol
    trips = parse_tripinfo(outdir / "tripinfo.xml")
    stats = parse_statistics(outdir / "stats.xml")
    metrics = run_metrics(trips, stats, n_route_vehicles, proto.depart_end_s)
    summ = controller.summary()
    if spec.controller == "tt_adaptive":  # the device's reroutes are counted by SUMO
        summ["n_reroutes"] = int(trips.reroutes.sum())
        summ["route_change_rate"] = controller.route_changes / summ["n_reroutes"] if summ["n_reroutes"] else float("nan")
    metrics.update({k: v for k, v in summ.items() if not isinstance(v, dict)})
    v = proto.validity
    metrics["timed_out"] = bool(sim_end_s >= proto.cap_s)
    metrics["valid"] = bool(metrics["completion_rate"] >= v.completion_min and metrics["teleport_frac"]
                            <= v.teleport_max_frac and not metrics["timed_out"])
    metrics["sim_end_s"] = float(sim_end_s)
    metrics["wall_s"] = round(wall, 2)
    if vlog is not None:
        trip_total = float(trips.nox_mg.sum())
        metrics["recon_step_nox_mg"] = vlog.total_nox_mg
        metrics["recon_rel_diff"] = (vlog.total_nox_mg - trip_total) / trip_total if trip_total else float("nan")
        metrics["recon_invalid_values"] = vlog.invalid_values
        pd.DataFrame({"t_s": series[0], "nox_mg": series[1], "running": series[2]}).astype(
            {"t_s": "float32", "nox_mg": "float64", "running": "int32"}).to_parquet(outdir / "network_series.parquet")
    if elog is not None:
        metrics["edge_logger_invalid_values"] = elog.invalid_values
        metrics["edge_logger_total_nox_mg"] = float(elog.cum_nox_mg.sum())

    trips.to_parquet(outdir / "trip_metrics.parquet", index=False)
    five, cum = edge_tables(elog, info)
    five.to_parquet(outdir / "edge_5min.parquet", index=False)
    cum.to_parquet(outdir / "edge_cumulative.parquet", index=False)
    ticks = pd.DataFrame([{"t_s": tl.t_s, "reroute_calls": tl.reroute_calls, "route_changes": tl.route_changes,
                           "failures": tl.failures, "ctl_ms": tl.ctl_ms, **tl.extra} for tl in controller.tick_logs])
    ticks.to_parquet(outdir / "tick_log.parquet", index=False)
    if recorder is not None:
        frame = recorder.frame()
        frame.insert(0, "run_id", spec.run_id())
        frame.to_parquet(outdir / "edge_window.parquet", index=False)
        metrics["dataset_rows"] = int(len(frame))
        metrics["dataset_dropped_edge_windows"] = recorder.dropped_edge_windows
    feature_log = getattr(controller, "feature_log", None)
    if feature_log:  # eco_ml shadow mode: the features it computed live (train/serve parity test)
        names = controller.builder.names
        parts = []
        for k, x in feature_log:
            part = pd.DataFrame(x, columns=names)
            part.insert(0, "edge_idx", np.arange(len(x), dtype=np.int32))
            part.insert(0, "k", np.int32(k))
            parts.append(part)
        pd.concat(parts, ignore_index=True).to_parquet(outdir / "shadow_features.parquet", index=False)
    if records:
        rec = pd.DataFrame(np.concatenate(records), columns=["t_s", "co2_mg_s", "co_mg_s", "hc_mg_s", "pmx_mg_s",
                                                              "nox_mg_s"])
        rec.to_parquet(outdir / "vehicle_records.parquet", index=False)
    if not spec.keep_raw:
        for name in ("tripinfo.xml",):
            (outdir / name).unlink(missing_ok=True)

    run_json = {
        "run_id": spec.run_id(), "spec": spec.model_dump(), "backend": backend_name,
        "sumo_version": env.sumo_version(), "packages": env.package_versions(), "platform": env.platform_info(),
        "git": git_state(), "input_sha256": hashes, "controller_summary": summ,
        "timings": {"wall_s": round(wall, 2), "sim_end_s": float(sim_end_s)},
    }
    (outdir / "run.json").write_text(json.dumps(run_json, indent=2, default=str) + "\n", encoding="utf-8")
    (outdir / "run_metrics.json").write_text(json.dumps(metrics, indent=2, default=float) + "\n", encoding="utf-8")
    _atomic_write(outdir / "DONE", f"{spec.run_id()}\n")
    return metrics
