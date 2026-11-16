"""Execute a planned experiment: one subprocess per run, in parallel, resumable (docs/SPECIFICATION.md 5.3, 8).

Each run is ``python -m nycemis sim run --spec <run dir>/spec.json`` in its own process (libsumo allows one
simulation per process), launched by a pool of worker threads that only wait on subprocesses. A run already marked
``DONE`` is skipped. A run gets a timeout and at most ``max_retries`` retries; a run that still fails is recorded in
``failed_runs.csv`` with the last error lines, and ``experiment verify`` reports it.
"""

from __future__ import annotations

import csv
import logging
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from nycemis.config import base_config
from nycemis.experiments.plan import exp_dir, load_plan
from nycemis.sim.run_spec import RunSpec

log = logging.getLogger(__name__)


def _run_once(spec: RunSpec, rdir: Path, timeout_s: float) -> tuple[bool, str]:
    rdir.mkdir(parents=True, exist_ok=True)
    spec_file = rdir / "spec.json"
    spec_file.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    with (rdir / "run.log").open("a", encoding="utf-8") as logf:
        try:
            proc = subprocess.run([sys.executable, "-m", "nycemis", "sim", "run", "--spec", str(spec_file)],
                                  stdout=logf, stderr=subprocess.STDOUT, timeout=timeout_s, check=False)
        except subprocess.TimeoutExpired:
            return False, f"timeout after {timeout_s:.0f} s"
    if proc.returncode == 0 and (rdir / "DONE").is_file():
        return True, ""
    tail = (rdir / "run.log").read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]
    return False, f"exit {proc.returncode}: {' | '.join(tail)}"


def run_experiment(name: str, workers: int | None = None, timeout_s: float | None = None) -> dict:
    cfg = base_config().execution
    workers = workers or cfg.workers or max(1, (os.cpu_count() or 2) - 1)
    timeout_s = timeout_s or 60.0 * max(cfg.run_timeout_min_floor, 60)
    doc = load_plan(name)
    d = exp_dir(name)
    todo = []
    for r in doc["runs"]:
        rdir = d / r["run_id"]
        if (rdir / "DONE").is_file():
            continue
        if rdir.exists():  # a partial earlier attempt: start clean
            shutil.rmtree(rdir)
        todo.append((RunSpec.model_validate(r["spec"]), rdir))
    log.info("%s: %d planned, %d to run, %d workers", name, len(doc["runs"]), len(todo), workers)
    failures: dict[str, str] = {}
    t0 = time.perf_counter()

    def job(spec: RunSpec, rdir: Path) -> tuple[str, bool, str]:
        msg = ""
        for attempt in range(cfg.max_retries + 1):
            ok, msg = _run_once(spec, rdir, timeout_s)
            if ok:
                return spec.run_id(), True, ""
            log.warning("run %s attempt %d failed: %s", spec.run_id(), attempt + 1, msg)
        return spec.run_id(), False, msg

    # Memory-heavy controllers get their own small pool (configs/base.yaml execution.max_concurrent); the rest of
    # the workers run everything else, so the fast runs never wait behind them.
    limited = {c: n for c, n in cfg.max_concurrent.items() if any(s.controller == c for s, _ in todo)}
    pools = {c: ThreadPoolExecutor(max_workers=n) for c, n in limited.items()}
    general = ThreadPoolExecutor(max_workers=max(1, workers - sum(limited.values())))
    done = 0
    try:
        futures = [(pools.get(s.controller, general)).submit(job, s, r) for s, r in todo]
        for fut in as_completed(futures):
            rid, ok, msg = fut.result()
            done += 1
            if not ok:
                failures[rid] = msg
            if done % max(1, len(todo) // 20) == 0 or done == len(todo):
                log.info("%s: %d/%d finished (%d failed), %.0f s", name, done, len(todo), len(failures),
                         time.perf_counter() - t0)
    finally:
        for p in [*pools.values(), general]:
            p.shutdown(wait=True)
    _write_failures(d, failures)
    return {"planned": len(doc["runs"]), "ran": len(todo), "failed": len(failures),
            "wall_s": round(time.perf_counter() - t0, 1)}


def _write_failures(d: Path, failures: dict[str, str]) -> None:
    path = d / "failed_runs.csv"
    existing = {}
    if path.is_file():
        with path.open(encoding="utf-8") as fh:
            existing = {row["run_id"]: row for row in csv.DictReader(fh)}
    for rid in list(existing):
        if (d / rid / "DONE").is_file():
            existing.pop(rid)
    for rid, msg in failures.items():
        existing[rid] = {"run_id": rid, "error": msg, "root_cause": existing.get(rid, {}).get("root_cause", "")}
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["run_id", "error", "root_cause"])
        w.writeheader()
        for row in existing.values():
            w.writerow(row)
