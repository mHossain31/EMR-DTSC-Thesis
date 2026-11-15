"""``RunSpec``: everything that identifies one simulation run (docs/SPECIFICATION.md 5.3).

The 12-character ``run_id`` hashes only the fields that can change results (scenario, level, seed, controller and
its parameters, protocol version, demand density and the route file's SHA-256, and the dataset/vehicle-record
logging flags). Logging-only options (reconciliation, backend, keep_raw) and the experiment name do not change it.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field

from nycemis.config import Strict

ID_FIELDS = ("scenario", "level", "seed", "controller", "params", "protocol_version", "density_per_h_km",
             "route_sha256", "dataset", "log_vehicle_records")


class RunSpec(Strict):
    experiment: str
    scenario: str
    level: str
    seed: int
    controller: str
    params: dict[str, Any] = Field(default_factory=dict)
    protocol_version: int
    density_per_h_km: float
    route_sha256: str
    dataset: bool = False  # write edge_window features and targets (training data)
    log_vehicle_records: bool = False  # write per-vehicle-step emission records (legacy RF training data)
    reconcile: bool = False  # sum per-step vehicle NOx and compare with tripinfo
    backend: str = "libsumo"
    keep_raw: bool = False

    def identity(self) -> dict:
        data = self.model_dump()
        return {k: data[k] for k in ID_FIELDS}

    def run_id(self) -> str:
        canon = json.dumps(self.identity(), sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canon.encode()).hexdigest()[:12]
