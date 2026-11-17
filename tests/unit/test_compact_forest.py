"""The compact legacy-forest predictor reproduces RandomForestRegressor.predict bit for bit."""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.ensemble import RandomForestRegressor

from nycemis.models.compact_forest import CompactForest, export


def _data(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = rng.lognormal(mean=1.0, sigma=1.5, size=(n, 4))  # skewed, like emission rates
    y = 0.3 * x[:, 0] + np.sqrt(x[:, 1]) + rng.normal(0, 0.5, n)
    return x, y


def test_exact_predictions_on_a_deep_forest(tmp_path) -> None:
    x, y = _data(5000, 1)
    rf = RandomForestRegressor(n_estimators=12, random_state=42, n_jobs=1).fit(x, y)
    export(rf, tmp_path)
    cf = CompactForest.load(tmp_path)
    x_test, _ = _data(4000, 2)
    x_test = np.vstack([x_test, x[:500], x[:50] + 1e-7])  # unseen rows, training rows, values next to splits
    assert np.array_equal(cf.predict(x_test), rf.predict(x_test))


def test_float64_inputs_are_cast_like_scikit_learn(tmp_path) -> None:
    x, y = _data(2000, 3)
    rf = RandomForestRegressor(n_estimators=5, random_state=0, n_jobs=1).fit(x, y)
    export(rf, tmp_path)
    cf = CompactForest.load(tmp_path)
    x_test = np.asarray(_data(1000, 4)[0], dtype=np.float64)
    assert np.array_equal(cf.predict(x_test), rf.predict(x_test))


def test_non_finite_input_rejected(tmp_path) -> None:
    x, y = _data(500, 5)
    export(RandomForestRegressor(n_estimators=2, random_state=0).fit(x, y), tmp_path)
    with pytest.raises(ValueError):
        CompactForest.load(tmp_path).predict(np.array([[1.0, np.nan, 1.0, 1.0]]))
