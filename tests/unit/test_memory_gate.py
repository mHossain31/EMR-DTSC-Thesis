"""The executor's memory gate: admitted runs stay within the batch budget; the first run is always admitted."""

from __future__ import annotations

import threading
import time

from nycemis.experiments import execute


def test_gate_holds_a_run_that_would_exceed_the_budget(monkeypatch) -> None:
    monkeypatch.setattr(execute, "available_phys_gb", lambda: 100.0)
    monkeypatch.setattr(execute, "LAUNCH_SPACING_S", 0.0)
    monkeypatch.setattr(execute, "GATE_POLL_S", 0.01)
    gate = execute.MemoryGate(budget_gb=2.0, reserve_gb=6.0)
    gate.acquire(1.5)
    admitted = threading.Event()
    th = threading.Thread(target=lambda: (gate.acquire(1.0), admitted.set()))
    th.start()
    time.sleep(0.1)
    assert not admitted.is_set()  # 1.5 + 1.0 > 2.0
    gate.release(1.5)
    th.join(timeout=2)
    assert admitted.is_set() and abs(gate.in_use_gb - 1.0) < 1e-9


def test_gate_holds_when_free_ram_drops_below_the_reserve(monkeypatch) -> None:
    free = {"gb": 6.5}
    monkeypatch.setattr(execute, "available_phys_gb", lambda: free["gb"])
    monkeypatch.setattr(execute, "LAUNCH_SPACING_S", 0.0)
    monkeypatch.setattr(execute, "GATE_POLL_S", 0.01)
    gate = execute.MemoryGate(budget_gb=50.0, reserve_gb=6.0)
    gate.acquire(1.0)  # the first run is admitted whatever the free RAM
    admitted = threading.Event()
    th = threading.Thread(target=lambda: (gate.acquire(1.0), admitted.set()))
    th.start()
    time.sleep(0.1)
    assert not admitted.is_set()  # 6.5 - 6.0 < 1.0: another program took the memory
    free["gb"] = 9.0
    th.join(timeout=2)
    assert admitted.is_set()
