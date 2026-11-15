"""Plan an experiment from ``configs/experiments/<name>.yaml`` (docs/SPECIFICATION.md 8).

Planning generates the route file of every (scenario, level, seed) once, before any run starts, so every condition
of a seed shares one byte-identical file (P2). The plan is written to ``results/runs/<experiment>/plan.json``.
"""

from __future__ import annotations

import json
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from pydantic import Field

from nycemis.config import Strict, base_config, load_yaml
from nycemis.demand.generate import generate, routes_path
from nycemis.demand.levels import level_density
from nycemis.manifest import sha256_file
from nycemis.paths import configs_dir, results_dir
from nycemis.sim.run_spec import RunSpec


class Condition(Strict):
    controller: str
    params: dict = Field(default_factory=dict)
    label: str | None = None
    dataset: bool = False
    log_vehicle_records: bool = False


class ExperimentConfig(Strict):
    name: str
    scenario: str
    levels: list[str]
    level_densities: dict[str, float] = Field(default_factory=dict)  # overrides (smoke only)
    seeds: list[int] | None = None
    seed_role: str | None = None  # pilot, train, validation, test
    test_n: int | None = None
    conditions: list[Condition]
    reconcile: bool = False
    reconcile_sample_frac: float = 0.0  # seeded random share of runs with the reconciliation logger
    backend: str = "libsumo"

    def seed_list(self) -> list[int]:
        if self.seeds is not None:
            return list(self.seeds)
        s = base_config().seeds
        if self.seed_role == "pilot":
            return s.pilot_seeds()
        if self.seed_role == "train":
            return s.train_seeds()
        if self.seed_role == "validation":
            return s.validation_seeds()
        if self.seed_role == "test":
            if self.test_n is None:
                raise ValueError("seed_role test needs test_n")
            return s.test_seeds(self.test_n)
        raise ValueError("give seeds or seed_role")


def load_experiment(name: str) -> ExperimentConfig:
    return ExperimentConfig.model_validate(load_yaml(configs_dir() / "experiments" / f"{name}.yaml"))


def exp_dir(name: str) -> Path:
    return results_dir() / "runs" / name


def _density(cfg: ExperimentConfig, level: str) -> float:
    if level in cfg.level_densities:
        return float(cfg.level_densities[level])
    return level_density(cfg.scenario, level)


def _ensure_routes(scenario: str, level: str, seed: int, density: float) -> str:
    out = routes_path(scenario, level, seed)
    summary = out.with_name(out.name.replace(".rou.xml.gz", ".summary.json"))
    if out.is_file() and summary.is_file():
        meta = json.loads(summary.read_text(encoding="utf-8"))
        if abs(meta["density_per_h_km"] - density) < 1e-9 and meta["sha256"] == sha256_file(out):
            return meta["sha256"]
    return generate(scenario, density, seed, out, level=level)["sha256"]


def _sampled(run_id: str, frac: float) -> bool:
    from nycemis.demand.generate import derived_seed

    return frac > 0 and derived_seed(run_id, "reconcile-audit") / float(2**31 - 1) < frac


def plan(name: str, workers: int = 8) -> list[RunSpec]:
    cfg = load_experiment(name)
    seeds = cfg.seed_list()
    pv = base_config().protocol_version
    jobs = [(lv, s, _density(cfg, lv)) for lv in cfg.levels for s in seeds]
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as pool:
        hashes = dict(zip([(lv, s) for lv, s, _ in jobs],
                          pool.map(_ensure_routes, *zip(*[(cfg.scenario, lv, s, d) for lv, s, d in jobs], strict=True)),
                          strict=True))
    specs = []
    for lv, s, d in jobs:
        for c in cfg.conditions:
            spec = RunSpec(experiment=name, scenario=cfg.scenario, level=lv, seed=s, controller=c.controller,
                           params=c.params, protocol_version=pv, density_per_h_km=d, route_sha256=hashes[(lv, s)],
                           dataset=c.dataset, log_vehicle_records=c.log_vehicle_records, backend=cfg.backend)
            rec = cfg.reconcile or _sampled(spec.run_id(), cfg.reconcile_sample_frac)
            specs.append(spec.model_copy(update={"reconcile": rec}))
    ids = [sp.run_id() for sp in specs]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{name}: duplicate run ids in the plan (two identical conditions?)")
    d = exp_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    labels = {sp.run_id(): (c.label or c.controller) for sp, c in
              zip(specs, [c for _ in jobs for c in cfg.conditions], strict=True)}
    doc = {"experiment": name, "scenario": cfg.scenario, "levels": cfg.levels, "seeds": seeds,
           "runs": [{"run_id": sp.run_id(), "label": labels[sp.run_id()], "spec": sp.model_dump()} for sp in specs]}
    (d / "plan.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return specs


def load_plan(name: str) -> dict:
    return json.loads((exp_dir(name) / "plan.json").read_text(encoding="utf-8"))
