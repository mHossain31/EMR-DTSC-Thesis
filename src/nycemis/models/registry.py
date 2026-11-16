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


def load_legacy_rf(scenario: str, model_id: str | None):
    model = joblib.load(_model_file(scenario, model_id or "legacy_rf"))
    model.set_params(n_jobs=1)
    return model


def load_forecaster(scenario: str, model_id: str | None):
    """A frozen forecaster object exposing ``feature_set`` and ``predict(x) -> (r_hat, v_hat)`` (see models.gbm)."""
    if not model_id:
        raise ValueError("eco_ml needs params.model_id")
    return joblib.load(_model_file(scenario, model_id))
