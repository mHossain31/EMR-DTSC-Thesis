"""Typed configuration (pydantic v2) loaded from ``configs/*.yaml``.

The seed roles of docs/SPECIFICATION.md 4.6 are validated here: ranges must be disjoint, and the test range is derived from
``test_start`` and the n fixed by the power analysis.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from nycemis.paths import configs_dir


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Validity(Strict):
    completion_min: float = Field(gt=0, le=1)
    teleport_max_frac: float = Field(ge=0, lt=1)


class Protocol(Strict):
    step_length_s: float = Field(gt=0)
    depart_begin_s: int = Field(ge=0)
    depart_end_s: int
    cap_s: int
    time_to_teleport_s: int = Field(gt=0)
    collision_action: str
    control_tick_s: int = Field(gt=0)
    feature_window_s: int = Field(gt=0)
    horizon_s: int = Field(gt=0)
    reroute_period_s: int = Field(gt=0)
    v_min_mps: float = Field(gt=0)
    validity: Validity

    @model_validator(mode="after")
    def _check(self) -> Protocol:
        if not self.depart_begin_s < self.depart_end_s < self.cap_s:
            raise ValueError("need depart_begin_s < depart_end_s < cap_s")
        if self.collision_action not in {"none", "warn", "teleport", "remove"}:
            raise ValueError(f"unknown collision action {self.collision_action!r}")
        return self


class Seeds(Strict):
    pilot: tuple[int, int]
    train: tuple[int, int]
    validation: tuple[int, int]
    test_start: int
    test_n_min: int = Field(gt=0)
    test_n_max: int = Field(gt=0)
    tier2_start: int
    demo: tuple[int, int]

    @staticmethod
    def expand(r: tuple[int, int]) -> list[int]:
        lo, hi = r
        if hi < lo:
            raise ValueError(f"empty seed range {r}")
        return list(range(lo, hi + 1))

    def pilot_seeds(self) -> list[int]:
        return self.expand(self.pilot)

    def train_seeds(self) -> list[int]:
        return self.expand(self.train)

    def validation_seeds(self) -> list[int]:
        return self.expand(self.validation)

    def test_seeds(self, n: int) -> list[int]:
        if not self.test_n_min <= n <= self.test_n_max:
            raise ValueError(f"test n={n} outside [{self.test_n_min}, {self.test_n_max}]")
        return list(range(self.test_start, self.test_start + n))

    def demo_seeds(self) -> list[int]:
        return self.expand(self.demo)

    def role_ranges(self) -> dict[str, tuple[int, int]]:
        """Inclusive ranges per role, with test at its maximum size and tier 2 up to the pilot block."""
        return {
            "pilot": self.pilot,
            "train": self.train,
            "validation": self.validation,
            "test": (self.test_start, self.test_start + self.test_n_max - 1),
            "tier2": (self.tier2_start, self.tier2_start + 999),
            "demo": self.demo,
        }

    @model_validator(mode="after")
    def _disjoint(self) -> Seeds:
        ranges = sorted(self.role_ranges().items(), key=lambda kv: kv[1][0])
        for (name_a, (_, hi_a)), (name_b, (lo_b, _)) in zip(ranges, ranges[1:], strict=False):
            if lo_b <= hi_a:
                raise ValueError(f"seed roles overlap: {name_a} and {name_b}")
        return self


class Analysis(Strict):
    sesoi_pct: float = Field(gt=0)
    familywise_alpha: float = Field(gt=0, lt=1)
    n_confirmatory_tests: int = Field(gt=0)
    bootstrap_resamples: int = Field(gt=0)
    bootstrap_seed: int
    alpha_grid: tuple[float, ...]
    alpha_star_tt_budget_pct: float = Field(gt=0)

    @model_validator(mode="after")
    def _grid(self) -> Analysis:
        if any(not 0.0 <= a <= 1.0 for a in self.alpha_grid):
            raise ValueError("alpha grid values must lie in [0, 1]")
        return self


class Execution(Strict):
    workers: int | None = None
    run_timeout_min_floor: int = Field(gt=0)
    max_retries: int = Field(ge=0)
    disk_max_frac_of_free: float = Field(gt=0, le=1)


class BaseConfig(Strict):
    protocol_version: int
    protocol: Protocol
    seeds: Seeds
    analysis: Analysis
    execution: Execution


class GridSpec(Strict):
    number: int = Field(ge=2)
    length_m: float = Field(gt=0)
    attach_length_m: float = Field(ge=0)
    lanes: int = Field(ge=1)
    speed_mps: float = Field(gt=0)


class ScenarioConfig(Strict):
    id: str
    name: str
    role: str
    source: str
    bbox: tuple[float, float, float, float] | None = None  # west, south, east, north
    grid: GridSpec | None = None

    @model_validator(mode="after")
    def _source(self) -> ScenarioConfig:
        if self.role not in {"primary", "tier2", "smoke"}:
            raise ValueError(f"unknown role {self.role!r}")
        if self.source == "osm":
            if self.bbox is None:
                raise ValueError("an OSM scenario needs a bbox")
            w, s, e, n = self.bbox
            if not (w < e and s < n):
                raise ValueError("bbox must be west < east and south < north")
        elif self.source == "netgenerate":
            if self.grid is None:
                raise ValueError("a netgenerate scenario needs a grid spec")
        else:
            raise ValueError(f"unknown source {self.source!r}")
        return self


def scenario_config(scenario: str) -> ScenarioConfig:
    path = configs_dir() / "scenarios" / f"{scenario}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"no scenario config {path}")
    cfg = ScenarioConfig.model_validate(load_yaml(path))
    if cfg.id != scenario:
        raise ValueError(f"{path} has id {cfg.id!r}")
    return cfg


def load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not hold a mapping")
    return data


@lru_cache(maxsize=1)
def base_config() -> BaseConfig:
    return BaseConfig.model_validate(load_yaml(configs_dir() / "base.yaml"))
