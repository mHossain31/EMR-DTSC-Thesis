"""The memory-mapped legacy RF that legacy_ml runs load predicts exactly what the frozen scikit-learn model does."""

from __future__ import annotations

import joblib
import numpy as np
import pytest

from nycemis.models.legacy import FEATURES, load_records
from nycemis.models.registry import _model_file, load_legacy_rf

pytestmark = [pytest.mark.flushing, pytest.mark.slow]


def test_compact_legacy_rf_equals_scikit_learn() -> None:
    try:
        source = _model_file("flushing", "legacy_rf")
    except FileNotFoundError:
        pytest.skip("legacy RF not trained here (python -m nycemis train-legacy)")
    rf = joblib.load(source)
    rf.set_params(n_jobs=1)
    compact = load_legacy_rf("flushing", "legacy_rf")
    rec = load_records()
    rng = np.random.default_rng(7)
    x = rec[FEATURES].to_numpy(dtype=float)[rng.choice(len(rec), size=100_000, replace=False)]
    assert np.array_equal(compact.predict(x), rf.predict(x))
