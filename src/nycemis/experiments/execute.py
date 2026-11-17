"""Execute a planned experiment: one subprocess per run, in parallel, resumable (docs/SPECIFICATION.md 5.3, 8).

Each run is ``python -m nycemis sim run --spec <run dir>/spec.json`` in its own process (libsumo allows one
simulation per process), launched by a pool of worker threads that only wait on subprocesses. A run already marked
``DONE`` is skipped. A run gets a timeout and at most ``max_retries`` retries; a run that still fails is recorded in
``failed_runs.csv`` with the last error lines, and ``experiment verify`` reports it.

Before a batch starts, two guards run (docs/SPECIFICATION.md 6.6 and the memory incidents of 2026-11-15 and 2026-11-16,
docs/DESIGN.md): the expected disk use must stay below ``disk_max_frac_of_free`` of the free space (else the batch
aborts), and the worker pools are trimmed so that their expected memory fits in the available physical RAM minus
``memory_reserve_gb`` (and in 80% of the available commit memory). While the batch runs, a memory gate holds back
each new run until the free physical RAM exceeds the reserve plus the run's expected use, and spaces launches a few
seconds apart, so other programs that grow or start during a batch pause it instead of pushing the machine into
paging. (On 2026-11-16 a pool sized on commit memory, which counts the page file, plus a concurrent training job
paged the machine until the display driver failed: bugcheck 0x116 with STATUS_INSUFFICIENT_RESOURCES.)
"""

from __future__ import annotations

import csv
import logging
import os
import shutil
import subprocess
import sys
import threading
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


COMMIT_GB_PER_RUN = 1.1  # measured: one simulation process commits about 1.0 GB
COMMIT_GB_BY_CONTROLLER = {"legacy_ml": 4.5}  # measured: 4.2 GB with the legacy RF loaded
DEFAULT_RUN_DISK_MB = 60.0


LAUNCH_SPACING_S = 5.0  # a new simulation reaches most of its memory within seconds of starting
GATE_POLL_S = 15.0


def available_commit_gb() -> float | None:
    """Available commit memory (RAM + page file not yet committed), Windows only; None elsewhere."""
    st = _memory_status()
    return None if st is None else st[1]


def available_phys_gb() -> float | None:
    """Available physical RAM, Windows only; None elsewhere."""
    st = _memory_status()
    return None if st is None else st[0]


def _memory_status() -> tuple[float, float] | None:
    """(available physical RAM, available commit memory) in GB from GlobalMemoryStatusEx; None off Windows."""
    if os.name != "nt":
        return None
    import ctypes

    class MemoryStatus(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    st = MemoryStatus()
    st.dwLength = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
        return None
    return st.ullAvailPhys / 1e9, st.ullAvailPageFile / 1e9


class MemoryGate:
    """Holds back each launch until free physical RAM exceeds the reserve plus the run's expected use."""

    def __init__(self, reserve_gb: float) -> None:
        self.reserve_gb = reserve_gb
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self, need_gb: float) -> None:
        with self._lock:
            warned = False
            while True:
                avail = available_phys_gb()
                if avail is None or avail - self.reserve_gb >= need_gb:
                    break
                if not warned:
                    log.warning("memory gate: %.1f GB RAM free, reserve %.1f GB: holding new runs", avail,
                                self.reserve_gb)
                    warned = True
                time.sleep(GATE_POLL_S)
            if warned:
                log.info("memory gate: %.1f GB RAM free again; resuming launches", available_phys_gb() or 0.0)
            pause = LAUNCH_SPACING_S - (time.monotonic() - self._last)
            if pause > 0:
                time.sleep(pause)
            self._last = time.monotonic()


def _disk_guard(d: Path, n_todo: int, frac: float) -> None:
    sizes = [sum(f.stat().st_size for f in r.iterdir()) / 1e6 for r in d.iterdir()
             if r.is_dir() and (r / "DONE").is_file()]
    per_run = sorted(sizes)[len(sizes) // 2] if sizes else DEFAULT_RUN_DISK_MB
    need_gb = n_todo * per_run / 1e3
    free_gb = shutil.disk_usage(d).free / 1e9
    log.info("disk: about %.1f GB needed for %d runs (%.0f MB each), %.0f GB free", need_gb, n_todo, per_run, free_gb)
    if need_gb > frac * free_gb:
        raise RuntimeError(f"expected disk use {need_gb:.1f} GB exceeds {frac:.0%} of free space ({free_gb:.0f} GB)")


def _memory_guard(general: int, limited: dict[str, int], reserve_gb: float) -> int:
    st = _memory_status()
    if st is None:
        log.warning("cannot read available memory on this platform; worker pools not checked")
        return general
    phys, commit = st
    fixed = sum(n * COMMIT_GB_BY_CONTROLLER.get(c, COMMIT_GB_PER_RUN) for c, n in limited.items())
    budget = min(phys - reserve_gb, 0.8 * commit) - fixed
    fit = max(1, int(budget // COMMIT_GB_PER_RUN))
    if fit < general:
        log.warning("memory: %.1f GB RAM free (reserve %.1f GB), %.1f GB commit; general pool trimmed from %d to %d "
                    "workers", phys, reserve_gb, commit, general, fit)
        return fit
    log.info("memory: %.1f GB RAM free (reserve %.1f GB), %.1f GB commit; pools fit (%d general workers)", phys,
             reserve_gb, commit, general)
    return general


def run_experiment(name: str, workers: int | None = None, timeout_s: float | None = None,
                   controllers: set[str] | None = None) -> dict:
    """Run every planned run that is not DONE; ``controllers`` restricts this pass to those controllers (the rest
    stay planned for a later pass)."""
    cfg = base_config().execution
    workers = workers or cfg.workers or max(1, (os.cpu_count() or 2) - 1)
    timeout_s = timeout_s or 60.0 * max(cfg.run_timeout_min_floor, 60)
    doc = load_plan(name)
    d = exp_dir(name)
    todo = []
    for r in doc["runs"]:
        rdir = d / r["run_id"]
        if (rdir / "DONE").is_file() or (controllers and r["spec"]["controller"] not in controllers):
            continue
        if rdir.exists():  # a partial earlier attempt: start clean
            shutil.rmtree(rdir)
        todo.append((RunSpec.model_validate(r["spec"]), rdir))
    log.info("%s: %d planned, %d to run, %d workers", name, len(doc["runs"]), len(todo), workers)
    failures: dict[str, str] = {}
    t0 = time.perf_counter()

    gate = MemoryGate(cfg.memory_reserve_gb)

    def job(spec: RunSpec, rdir: Path) -> tuple[str, bool, str]:
        msg = ""
        need = COMMIT_GB_BY_CONTROLLER.get(spec.controller, COMMIT_GB_PER_RUN)
        for attempt in range(cfg.max_retries + 1):
            gate.wait(need)
            ok, msg = _run_once(spec, rdir, timeout_s)
            if ok:
                return spec.run_id(), True, ""
            log.warning("run %s attempt %d failed: %s", spec.run_id(), attempt + 1, msg)
        return spec.run_id(), False, msg

    # Memory-heavy controllers get their own small pool (configs/base.yaml execution.max_concurrent); the rest of
    # the workers run everything else, so the fast runs never wait behind them.
    limited = {c: n for c, n in cfg.max_concurrent.items() if any(s.controller == c for s, _ in todo)}
    _disk_guard(d, len(todo), cfg.disk_max_frac_of_free)
    n_general = _memory_guard(max(1, workers - sum(limited.values())), limited, cfg.memory_reserve_gb)
    pools = {c: ThreadPoolExecutor(max_workers=n) for c, n in limited.items()}
    general = ThreadPoolExecutor(max_workers=n_general)
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
