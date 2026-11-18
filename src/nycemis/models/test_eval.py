"""Held-out forecast evaluation on the test seeds (docs/SPECIFICATION.md 4.1 RQ2, 7.3; docs/DEVIATIONS.md #20).

The confirmatory plan records the edge-window dataset in its static and eco_ml runs for this evaluation
(``configs/experiments/confirmatory.yaml``). The frozen forecaster is scored against the same baselines as on the
validation seeds (``nycemis.models.evaluate``); the historical-mean and Ridge baselines are refitted on the training
subsample the model was frozen with (experiments, seeds, fraction and sampling seed from its train manifest), so no
test row informs any predictor. Test rows are subsampled per run with the manifest's fraction. Nothing is tuned here.
Writes ``results/<experiment>/forecast_test.json``.
"""

from __future__ import annotations

import json
import logging

import joblib
import numpy as np
import pandas as pd

from nycemis.config import base_config
from nycemis.experiments.plan import exp_dir, load_plan
from nycemis.features.builder import feature_names
from nycemis.models.evaluate import _reg_metrics, baseline_predictions, evaluate
from nycemis.models.train import load_windows, model_path
from nycemis.paths import models_dir, rel, results_dir

log = logging.getLogger(__name__)


def load_test_windows(experiment: str, sample_frac: float, seed: int) -> pd.DataFrame:
    s = base_config().seeds
    test = set(s.test_seeds(s.test_n_max))
    rng = np.random.default_rng(seed)
    parts = []
    for r in load_plan(experiment)["runs"]:
        spec = r["spec"]
        if not spec["dataset"]:
            continue
        if spec["seed"] not in test:
            raise ValueError(f"{experiment} run {r['run_id']} has non-test seed {spec['seed']}")
        df = pd.read_parquet(exp_dir(experiment) / r["run_id"] / "edge_window.parquet")
        if sample_frac < 1.0:
            df = df.iloc[np.sort(rng.choice(len(df), size=int(round(sample_frac * len(df))), replace=False))]
        parts.append(df.assign(level=spec["level"], seed=spec["seed"], policy=r["label"]))
    if not parts:
        raise ValueError(f"{experiment} recorded no edge-window dataset")
    return pd.concat(parts, ignore_index=True)


def evaluate_on_test(scenario: str = "flushing", model_id: str = "gbm_v1", experiment: str = "confirmatory") -> str:
    mdir = models_dir() / scenario / model_id
    man = json.loads((mdir / "train_manifest.json").read_text(encoding="utf-8"))
    train = load_windows(man["experiments"], set(man["train_seeds"]), man["sample_frac"], man["seed"])
    if len(train) != man["rows_train"]:
        raise ValueError(f"training subsample has {len(train)} rows, the manifest {man['rows_train']}")
    test = load_test_windows(experiment, man["sample_frac"], man["seed"] + 2)
    log.info("evaluating %s on %d test edge-windows (%d runs)", model_id, len(test), test.run_id.nunique())
    fc = joblib.load(model_path(scenario, model_id))
    res = evaluate(fc, test, train)
    # by controlling policy: does skill hold under the controller that uses the forecasts?
    r_hat, v_hat = fc.predict(test[feature_names("F1")].to_numpy(np.float32))
    base = baseline_predictions(test, train)
    res["by_policy"] = {}
    for policy, g in test.groupby("policy"):
        idx = g.index.to_numpy()
        out = {}
        for t, pred in (("r", r_hat), ("v", v_hat)):
            y = test[f"{t}_next"].to_numpy()[idx]
            m = ~np.isnan(y)
            out[t] = {"model": _reg_metrics(y[m], pred[idx][m]),
                      "historical_mean": _reg_metrics(y[m], base["historical_mean"][t][idx][m]),
                      "persistence": _reg_metrics(y[m], base["persistence"][t][idx][m])}
        res["by_policy"][policy] = out
    res["meta"] = {"experiment": experiment, "model_id": model_id, "rows_test": int(len(test)),
                   "runs_test": int(test.run_id.nunique()), "rows_train_baselines": int(len(train)),
                   "sample_frac": man["sample_frac"], "test_seeds": sorted(int(x) for x in test.seed.unique())}
    out_path = results_dir() / experiment / "forecast_test.json"
    out_path.write_text(json.dumps(res, indent=2, default=float) + "\n", encoding="utf-8")
    return rel(out_path)
