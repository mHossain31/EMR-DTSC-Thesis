"""The preregistration freeze (docs/SPECIFICATION.md M6): analysis-code hash and the generated confirmatory conditions."""

from __future__ import annotations

import yaml

from nycemis.experiments.prereg import _flow, analysis_code_files, analysis_code_sha256


def test_analysis_code_hash_is_stable_and_covers_the_analysis() -> None:
    a, b = analysis_code_sha256(), analysis_code_sha256()
    assert a == b and len(a) == 64
    names = {p.name for p in analysis_code_files()}
    assert {"confirmatory.py", "stats.py", "base.yaml"} <= names


def test_condition_lines_round_trip() -> None:
    cond = {"controller": "eco_ml", "params": {"alpha": 0.25, "model_id": "gbm_v1", "tau_avg_s": 180,
                                               "router": "traveltime_weights"}, "dataset": True}
    assert yaml.safe_load(_flow(cond)) == cond
