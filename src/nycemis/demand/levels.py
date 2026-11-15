"""Read the calibrated demand levels from ``configs/demand_levels.yaml``."""

from __future__ import annotations

from nycemis.config import load_yaml
from nycemis.paths import configs_dir

LEVELS = ("light", "moderate", "heavy")


def level_density(scenario: str, level: str) -> float:
    path = configs_dir() / "demand_levels.yaml"
    if not path.is_file():
        raise FileNotFoundError("configs/demand_levels.yaml missing; run `python -m nycemis calibrate` first")
    doc = load_yaml(path)
    try:
        return float(doc["scenarios"][scenario]["levels"][level]["density_per_h_km"])
    except KeyError as exc:
        raise KeyError(f"no calibrated level {level!r} for scenario {scenario!r}") from exc
