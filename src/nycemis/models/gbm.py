"""The forecaster served to C4 (docs/SPECIFICATION.md 7.3, 7.5): LightGBM regressors on F1 features.

``r`` (NOx mg per vehicle-second in window k+1) and ``d`` (NOx mg per lane-metre in window k+1) are modelled on the
log1p scale; ``v`` (mean speed, m/s) on its own scale. ``predict`` returns (r_hat, v_hat) for the controller;
``predict_density`` returns d_hat for the hotspot evaluation. If LightGBM cannot be imported, scikit-learn's
HistGradientBoostingRegressor is used and a WARNING is logged (docs/SPECIFICATION.md 7.3).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

log = logging.getLogger(__name__)

try:
    import lightgbm as lgb

    HAVE_LGB = True
except ImportError:  # recorded fallback
    HAVE_LGB = False


@dataclass
class GBMForecaster:
    feature_set: str
    feature_names: list[str]
    models: dict = field(default_factory=dict)  # "r", "v", "d" -> fitted regressors
    params: dict = field(default_factory=dict)
    backend: str = "lightgbm"
    hotspot_threshold: float | None = None  # d_next value (mg per lane-metre) above which an edge-window is a hotspot

    def _x(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float32)
        if x.shape[1] != len(self.feature_names):
            raise ValueError(f"expected {len(self.feature_names)} features, got {x.shape[1]}")
        return x

    def predict(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x = self._x(x)
        r = np.expm1(self.models["r"].predict(x))
        v = self.models["v"].predict(x)
        return np.maximum(r, 0.0), np.maximum(v, 0.1)

    def predict_density(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(np.expm1(self.models["d"].predict(self._x(x))), 0.0)


def make_regressor(params: dict, seed: int):
    if HAVE_LGB:
        return lgb.LGBMRegressor(objective="regression", n_estimators=params.get("n_estimators", 2000),
                                 learning_rate=params["learning_rate"], num_leaves=params["num_leaves"],
                                 min_child_samples=params["min_child_samples"],
                                 colsample_bytree=params["colsample_bytree"], subsample=params["subsample"],
                                 subsample_freq=1, reg_lambda=params["reg_lambda"], random_state=seed,
                                 n_jobs=params.get("n_jobs", -1), verbose=-1)
    from sklearn.ensemble import HistGradientBoostingRegressor

    log.warning("lightgbm unavailable: using HistGradientBoostingRegressor (record in docs/DEVIATIONS.md)")
    return HistGradientBoostingRegressor(learning_rate=params["learning_rate"], max_leaf_nodes=params["num_leaves"],
                                         min_samples_leaf=params["min_child_samples"], random_state=seed,
                                         early_stopping=True)


def fit_regressor(params: dict, seed: int, x_tr, y_tr, x_va, y_va, early_stopping: int = 50):
    model = make_regressor(params, seed)
    if HAVE_LGB:
        model.fit(x_tr, y_tr, eval_set=[(x_va, y_va)], callbacks=[lgb.early_stopping(early_stopping, verbose=False)])
    else:
        model.fit(x_tr, y_tr)
    return model
