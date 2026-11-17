"""Load frozen models before a run starts (controllers never read files during a run)."""

from __future__ import annotations

from pathlib import Path

import joblib

from nycemis.paths import models_dir


def _model_file(scenario: str, model_id: str) -> Path:
    path = models_dir() / scenario / model_id / "model.joblib"
    if not path.is_file():
        raise FileNotFoundError(f"no frozen model at {path}")
    return path


def legacy_compact_dir(scenario: str, model_id: str | None) -> Path:
    return models_dir() / scenario / (model_id or "legacy_rf") / "compact"


def load_legacy_rf(scenario: str, model_id: str | None):
    """The legacy RF as a memory-mapped CompactForest (identical predictions; one shared copy across processes)."""
    from nycemis.models.compact_forest import CompactForest

    source = _model_file(scenario, model_id or "legacy_rf")
    compact = legacy_compact_dir(scenario, model_id)
    if not (compact / "meta.json").is_file():
        raise FileNotFoundError(f"no compact export at {compact}; run `python -m nycemis export-legacy-compact`")
    return CompactForest.load(compact, source=source)


def export_legacy_compact(scenario: str, model_id: str | None = None) -> dict:
    from nycemis.models.compact_forest import export

    source = _model_file(scenario, model_id or "legacy_rf")
    return export(joblib.load(source), legacy_compact_dir(scenario, model_id), source=source)


def load_forecaster(scenario: str, model_id: str | None):
    """A frozen forecaster object exposing ``feature_set`` and ``predict(x) -> (r_hat, v_hat)`` (see models.gbm)."""
    if not model_id:
        raise ValueError("eco_ml needs params.model_id")
    return joblib.load(_model_file(scenario, model_id))
