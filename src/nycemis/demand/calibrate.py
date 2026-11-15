"""Calibrate the three demand levels on the pilot seeds (docs/SPECIFICATION.md 6.5).

The level variable is the total insertion density (vehicles per hour per km of road, randomTrips'
``--insertion-density``). The response is the speed ratio of static (C0) runs, sum(duration - timeLoss) /
sum(duration) over finished trips departing in the loaded period (``metrics.speed_ratio``), averaged over the pilot
seeds. A coarse sweep brackets each target; bisection then refines it. A level is valid only if every pilot seed
meets the validity rule (teleports <= 0.5% of trips, completion >= 99.5%). If a target cannot be reached by a valid
density, the most congested valid density is used and the shortfall is recorded.
"""

from __future__ import annotations

import json
import logging
import multiprocessing as mp
import shutil
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
import yaml

from nycemis.config import base_config
from nycemis.demand.generate import generate, routes_path, vtypes_path
from nycemis.network.build import net_path
from nycemis.paths import configs_dir, rel, results_dir
from nycemis.sim.metrics import parse_statistics, parse_tripinfo, run_metrics
from nycemis.sim.protocol import sumo_command

log = logging.getLogger(__name__)

TARGETS = {"light": 0.80, "moderate": 0.60, "heavy": 0.45}
SWEEP_DENSITIES = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0)
SR_TOLERANCE = 0.01
MIN_BRACKET = 0.05  # vehicles per hour per km
MAX_BISECTION_STEPS = 10


def _level_name(density: float) -> str:
    return f"calib_d{density:.4f}"


def evaluate(scenario: str, density: float, seed: int) -> dict:
    """Generate the demand (if needed), run a static simulation, return run metrics. One process per call."""
    level = _level_name(density)
    routes = routes_path(scenario, level, seed)
    if not routes.is_file():
        generate(scenario, density, seed, routes, level=level)
    summary = json.loads(routes.with_name(routes.name.replace(".rou.xml.gz", ".summary.json")).read_text())
    with tempfile.TemporaryDirectory(prefix="calib_") as tmp:
        out = Path(tmp)
        cmd = sumo_command(net_path(scenario), routes, vtypes_path(scenario), seed, out)
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"sumo failed for density {density} seed {seed}: {proc.stderr[-1000:]}")
        trips = parse_tripinfo(out / "tripinfo.xml")
        stats = parse_statistics(out / "stats.xml")
    m = run_metrics(trips, stats, summary["vehicles"], base_config().protocol.depart_end_s)
    m.update({"density": density, "seed": seed, "route_sha256": summary["sha256"]})
    return m


def _valid(m: dict) -> bool:
    v = base_config().protocol.validity
    return m["completion_rate"] >= v.completion_min and m["teleport_frac"] <= v.teleport_max_frac


def evaluate_density(pool: ProcessPoolExecutor, scenario: str, density: float, seeds: list[int]) -> pd.DataFrame:
    futures = [pool.submit(evaluate, scenario, density, s) for s in seeds]
    return pd.DataFrame([f.result() for f in futures])


def _aggregate(df: pd.DataFrame) -> pd.DataFrame:
    df = df.assign(valid=df.apply(lambda r: _valid(r.to_dict()), axis=1))
    return df.groupby("density").agg(
        sr_mean=("speed_ratio", "mean"), sr_sd=("speed_ratio", "std"), teleport_frac_max=("teleport_frac", "max"),
        completion_min=("completion_rate", "min"), all_valid=("valid", "all"), vehicles_mean=("n_route_vehicles", "mean"),
        last_arrival_max_s=("last_arrival_s", "max"), runs=("seed", "count")).reset_index()


def calibrate(scenario: str, workers: int) -> dict:
    seeds = base_config().seeds.pilot_seeds()
    ctx = mp.get_context("spawn")
    records: list[pd.DataFrame] = []
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        futures = {(d, s): pool.submit(evaluate, scenario, d, s) for d in SWEEP_DENSITIES for s in seeds}
        records.append(pd.DataFrame([f.result() for f in futures.values()]))
        sweep = _aggregate(pd.concat(records))
        log.info("sweep:\n%s", sweep.to_string())
        levels = {}
        for name, target in TARGETS.items():
            levels[name] = _bisect(pool, scenario, seeds, target, records)
    allruns = pd.concat(records, ignore_index=True)
    return _write(scenario, levels, allruns, seeds)


def _bisect(pool: ProcessPoolExecutor, scenario: str, seeds: list[int], target: float,
            records: list[pd.DataFrame]) -> dict:
    agg = _aggregate(pd.concat(records))
    valid = agg[agg.all_valid]
    if valid.empty:
        raise RuntimeError(f"{scenario}: no valid density in the sweep")
    above = agg[agg.sr_mean >= target]
    below = agg[(agg.sr_mean < target) & agg.all_valid]
    if below.empty:
        # target not reached by any valid density: use the most congested valid density (recorded shortfall)
        best = valid.sort_values("sr_mean").iloc[0]
        return {"density": float(best.density), "sr_mean": float(best.sr_mean), "target": target,
                "reached": False, "steps": 0}
    lo = float(above.density.max()) if not above.empty else float(agg.density.min())  # sr >= target
    hi = float(below.density.min())  # sr < target, valid
    best = None
    for step in range(1, MAX_BISECTION_STEPS + 1):
        mid = round((lo + hi) / 2, 4)
        df = evaluate_density(pool, scenario, mid, seeds)
        records.append(df)
        sr = float(df.speed_ratio.mean())
        ok = all(_valid(r) for r in df.to_dict("records"))
        log.info("target %.2f step %d: density %.4f -> sr %.4f valid %s", target, step, mid, sr, ok)
        if ok and (best is None or abs(sr - target) < abs(best[1] - target)):
            best = (mid, sr)
        if abs(sr - target) <= SR_TOLERANCE and ok:
            break
        if sr >= target:
            lo = mid
        else:
            hi = mid
        if hi - lo < MIN_BRACKET:
            break
    if best is None:
        raise RuntimeError(f"{scenario}: bisection for target {target} found no valid density")
    for cand_d in (lo, hi):  # the bracket ends may be closer than the last midpoint
        sub = _aggregate(pd.concat(records))
        row = sub[sub.density == cand_d]
        if not row.empty and bool(row.all_valid.iloc[0]) and abs(row.sr_mean.iloc[0] - target) < abs(best[1] - target):
            best = (cand_d, float(row.sr_mean.iloc[0]))
    return {"density": best[0], "sr_mean": best[1], "target": target,
            "reached": abs(best[1] - target) <= SR_TOLERANCE, "steps": step}


def _write(scenario: str, levels: dict, runs: pd.DataFrame, seeds: list[int]) -> dict:
    outdir = results_dir() / "calibration" / scenario
    outdir.mkdir(parents=True, exist_ok=True)
    runs.to_csv(outdir / "calibration_runs.csv", index=False)
    agg = _aggregate(runs)
    agg.to_csv(outdir / "calibration_by_density.csv", index=False)
    _plot(agg, levels, outdir / "speed_ratio_vs_density.png", scenario)

    path = configs_dir() / "demand_levels.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    doc = doc or {}
    doc.setdefault("scenarios", {})
    entry = {"pilot_seeds": seeds, "response": "speed_ratio = sum(duration - timeLoss) / sum(duration), "
             "finished trips departing in [900, 3600] s, static runs, mean over pilot seeds", "levels": {}}
    for name, lv in levels.items():
        row = agg[agg.density == lv["density"]].iloc[0]
        entry["levels"][name] = {
            "density_per_h_km": float(lv["density"]), "target_speed_ratio": lv["target"],
            "achieved_speed_ratio_mean": round(float(row.sr_mean), 4), "achieved_speed_ratio_sd": round(float(row.sr_sd), 4),
            "target_reached": bool(lv["reached"]), "max_teleport_frac": round(float(row.teleport_frac_max), 5),
            "min_completion": round(float(row.completion_min), 5), "mean_vehicles": round(float(row.vehicles_mean), 1),
            "max_last_arrival_s": float(row.last_arrival_max_s)}
    entry["evidence"] = [rel(outdir / "calibration_by_density.csv"), rel(outdir / "calibration_runs.csv"),
                         rel(outdir / "speed_ratio_vs_density.png")]
    doc["scenarios"][scenario] = entry
    header = ("# Calibrated demand levels (docs/SPECIFICATION.md 6.5). Generated by `python -m nycemis calibrate`; do not edit "
              "by hand.\n# Density = total insertion density (vehicles per hour per km), split across fleet groups "
              "by share.\n")
    path.write_text(header + yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return entry


def _plot(agg: pd.DataFrame, levels: dict, path: Path, scenario: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    agg = agg.sort_values("density")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.errorbar(agg.density, agg.sr_mean, yerr=agg.sr_sd.fillna(0), fmt="o-", ms=3, lw=1, color="#333333",
                label="mean over pilot seeds (SD bars)")
    bad = agg[~agg.all_valid]
    ax.scatter(bad.density, bad.sr_mean, color="#d73027", zorder=3, label="invalid (teleports or completion)")
    for name, lv in levels.items():
        ax.axhline(lv["target"], color="#999999", lw=0.6, ls="--")
        ax.scatter([lv["density"]], [lv["sr_mean"]], marker="s", s=40, zorder=4, label=f"{name}: {lv['density']:.2f}")
    ax.set_xlabel("insertion density (vehicles per hour per km)")
    ax.set_ylabel("speed ratio (ideal / actual travel time)")
    ax.set_title(f"{scenario}: demand calibration on pilot seeds")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def clean_calibration_routes(scenario: str) -> None:
    """Remove the calibration route files (they are reproducible from the seed and density)."""
    base = routes_path(scenario, "x", 0).parent.parent
    for d in base.glob("calib_d*"):
        shutil.rmtree(d)


def summary_table(entry: dict) -> str:
    rows = ["level     density  target  achieved(sd)   max_tele  min_compl"]
    for name, lv in entry["levels"].items():
        rows.append(f"{name:<9} {lv['density_per_h_km']:>7.3f}  {lv['target_speed_ratio']:.2f}    "
                    f"{lv['achieved_speed_ratio_mean']:.3f}({lv['achieved_speed_ratio_sd']:.3f})  "
                    f"{lv['max_teleport_frac']:.4f}    {lv['min_completion']:.4f}")
    return "\n".join(rows)


def default_workers() -> int:
    configured = base_config().execution.workers
    import os

    return configured or max(1, (os.cpu_count() or 2) - 1)


