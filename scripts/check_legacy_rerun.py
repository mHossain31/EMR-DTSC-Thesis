"""Rerun one pilot legacy_ml run with the current code and require identical results (after a change to how the legacy
RF is loaded or evaluated). Records the process's peak working set. Writes results/legacy_audit/rerun_check.json.

Usage: python scripts/check_legacy_rerun.py [--level moderate] [--seed 9000]
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import tempfile
from pathlib import Path

from nycemis.experiments.plan import exp_dir, load_plan
from nycemis.paths import rel, results_dir
from nycemis.sim.run_spec import RunSpec
from nycemis.sim.runner import execute

KEYS = ("total_nox_g", "total_co2_kg", "mean_tt_s", "p95_tt_s", "vkm_total", "arrived", "teleports",
        "mean_timeloss_s", "last_arrival_s", "n_reroutes", "route_change_rate", "valid")


def peak_working_set_gb() -> float | None:
    if os.name != "nt":
        return None

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    c = Counters()
    c.cb = ctypes.sizeof(Counters)
    k32 = ctypes.windll.kernel32
    k32.GetCurrentProcess.restype = ctypes.c_void_p  # a pseudo-handle (-1): must not be truncated to a C int
    k32.K32GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    if not k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb):
        return None
    return c.PeakWorkingSetSize / 1e9, c.PeakPagefileUsage / 1e9


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="moderate")
    ap.add_argument("--seed", type=int, default=9000)
    a = ap.parse_args()
    run = next(r for r in load_plan("pilot")["runs"]
               if r["label"] == "legacy_ml" and r["spec"]["level"] == a.level and r["spec"]["seed"] == a.seed)
    before = json.loads((exp_dir("pilot") / run["run_id"] / "run_metrics.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="legacy_rerun_") as tmp:
        after = execute(RunSpec.model_validate(run["spec"]), Path(tmp) / "run")
    peak = peak_working_set_gb()
    diffs = {k: [before.get(k), after.get(k)] for k in KEYS if before.get(k) != after.get(k)}
    out = {"run_id": run["run_id"], "level": a.level, "seed": a.seed, "identical": not diffs, "differences": diffs,
           "peak_working_set_gb": None if peak is None else round(peak[0], 2),
           "peak_commit_gb": None if peak is None else round(peak[1], 2),
           "compared": list(KEYS)}
    path = results_dir() / "legacy_audit" / "rerun_check.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"wrote {rel(path)}")
    if diffs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
