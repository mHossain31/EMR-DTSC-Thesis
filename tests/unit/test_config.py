"""Configuration validation and seed-role disjointness (docs/SPECIFICATION.md 4.6, 9.1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nycemis.config import BaseConfig, Seeds, base_config, load_yaml
from nycemis.paths import configs_dir


def test_base_config_loads() -> None:
    cfg = base_config()
    assert cfg.protocol.step_length_s == 1.0
    assert cfg.protocol.depart_end_s == 3600
    assert cfg.protocol.cap_s == 14400
    assert cfg.analysis.sesoi_pct == 2.0
    assert cfg.analysis.alpha_grid == (0.0, 0.25, 0.5, 0.75, 1.0)


def test_seed_roles_match_specification() -> None:
    s = base_config().seeds
    assert s.pilot_seeds() == list(range(9000, 9005))
    assert s.train_seeds() == list(range(0, 24))
    assert s.validation_seeds() == list(range(100, 112))
    assert s.test_seeds(30) == list(range(200, 230))
    assert s.demo_seeds()[0] == 9100 and s.demo_seeds()[-1] == 9199


def test_seed_roles_disjoint() -> None:
    s = base_config().seeds
    sets = {
        "pilot": set(s.pilot_seeds()),
        "train": set(s.train_seeds()),
        "validation": set(s.validation_seeds()),
        "test": set(s.test_seeds(s.test_n_max)),
        "demo": set(s.demo_seeds()),
    }
    names = list(sets)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            assert not sets[a] & sets[b], f"{a} and {b} overlap"


def test_overlapping_roles_rejected() -> None:
    raw = load_yaml(configs_dir() / "base.yaml")
    raw["seeds"]["validation"] = [20, 30]  # overlaps train 0-23
    with pytest.raises(ValidationError):
        BaseConfig.model_validate(raw)


def test_test_n_bounds() -> None:
    s = base_config().seeds
    with pytest.raises(ValueError):
        s.test_seeds(29)
    with pytest.raises(ValueError):
        s.test_seeds(61)


def test_unknown_keys_rejected() -> None:
    raw = load_yaml(configs_dir() / "base.yaml")
    raw["protocol"]["step_lenght_s"] = 1.0
    with pytest.raises(ValidationError):
        BaseConfig.model_validate(raw)


def test_seeds_expand_rejects_empty() -> None:
    with pytest.raises(ValueError):
        Seeds.expand((5, 4))


def test_no_model_manifest_reads_a_test_seed() -> None:
    """docs/SPECIFICATION.md 9.6: test seeds are absent from every training and tuning artifact, checked via the manifests."""
    import json

    from nycemis.paths import models_dir

    s = base_config().seeds
    test = set(range(s.test_start, s.test_start + s.test_n_max))
    for path in models_dir().glob("*/*/train_manifest.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        used = set(doc.get("train_seeds", [])) | set(doc.get("validation_seeds", []))
        used |= {d["seed"] for d in doc.get("data", []) if "seed" in d}
        if "runs" in doc:  # run ids of one experiment (legacy RF): resolve them through the experiment's plan
            from nycemis.experiments.plan import load_plan

            seeds = {r["run_id"]: r["spec"]["seed"] for r in load_plan(doc["experiment"])["runs"]}
            used |= {seeds[rid] for rid in doc["runs"]}
        assert not used & test, f"{path}: test seeds {sorted(used & test)}"
