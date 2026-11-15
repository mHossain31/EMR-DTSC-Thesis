"""``experiment verify``: completeness, pairing and output schema (docs/SPECIFICATION.md 8, 9.4).

Every planned run must be DONE, or listed in ``failed_runs.csv`` with a documented root cause. Every condition of a
(scenario, level, seed) must have used the same route file (SHA-256 in each run.json). Outputs must exist with the
expected columns and units.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict

import pandas as pd

from nycemis.experiments.plan import exp_dir, load_plan
from nycemis.sim.metrics import TRIP_COLUMNS

REQUIRED_FILES = ("run.json", "run_metrics.json", "trip_metrics.parquet", "edge_cumulative.parquet",
                  "edge_5min.parquet", "tick_log.parquet")
REQUIRED_METRICS = ("total_nox_g", "total_co2_kg", "mean_tt_s", "completion_rate", "teleport_frac", "valid")


def verify(name: str) -> dict:
    doc = load_plan(name)
    d = exp_dir(name)
    failed = {}
    fpath = d / "failed_runs.csv"
    if fpath.is_file():
        with fpath.open(encoding="utf-8") as fh:
            failed = {row["run_id"]: row for row in csv.DictReader(fh)}
    problems: list[str] = []
    done = 0
    hashes: dict[tuple, set] = defaultdict(set)
    for r in doc["runs"]:
        rid, rdir = r["run_id"], d / r["run_id"]
        if not (rdir / "DONE").is_file():
            row = failed.get(rid)
            if row is None:
                problems.append(f"{rid}: not DONE and not in failed_runs.csv")
            elif not row.get("root_cause", "").strip():
                problems.append(f"{rid}: failed without a documented root cause ({row.get('error', '')[:80]})")
            continue
        done += 1
        for f in REQUIRED_FILES:
            if not (rdir / f).is_file():
                problems.append(f"{rid}: missing {f}")
        run = json.loads((rdir / "run.json").read_text(encoding="utf-8"))
        spec = run["spec"]
        hashes[(spec["scenario"], spec["level"], spec["seed"])].add(run["input_sha256"]["routes"])
        if run["input_sha256"]["routes"] != spec["route_sha256"]:
            problems.append(f"{rid}: route hash differs from its spec")
        metrics = json.loads((rdir / "run_metrics.json").read_text(encoding="utf-8"))
        problems += [f"{rid}: metric {m} missing" for m in REQUIRED_METRICS if m not in metrics]
        trips = pd.read_parquet(rdir / "trip_metrics.parquet")
        if list(trips.columns) != list(TRIP_COLUMNS):
            problems.append(f"{rid}: trip_metrics columns differ from the schema")
        elif (trips[["nox_mg", "co2_mg", "duration_s", "route_length_m"]] < 0).any().any():
            problems.append(f"{rid}: negative emissions, durations or lengths")
    for key, hs in hashes.items():
        if len(hs) != 1:
            problems.append(f"pairing: {key} used {len(hs)} different route files")
    return {"experiment": name, "planned": len(doc["runs"]), "done": done, "failed_documented":
            sum(1 for r in doc["runs"] if r["run_id"] in failed and failed[r["run_id"]].get("root_cause")),
            "problems": problems, "ok": not problems}
