"""A memory-mapped, prediction-identical copy of the legacy random forest (C5).

The legacy RF (100 trees, 36 million nodes) takes about 4 GB per process in scikit-learn's own format, and every
legacy_ml simulation loads it. Here the same trees are stored once as flat arrays (child indices, split feature,
threshold, leaf value; about 0.9 GB) that each process memory-maps read-only, so concurrent runs share one physical
copy through the operating system's file cache.

Predictions reproduce ``RandomForestRegressor.predict`` bit for bit: inputs are cast to float32 as scikit-learn
does, each split compares the float32 value with the float64 threshold (``x <= threshold`` goes left), and the trees'
leaf values are added in estimator order into a float64 accumulator that is then divided by the number of trees.
``tests/unit/test_compact_forest.py`` and the regression test on the frozen legacy RF check exact equality.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ARRAYS = ("left", "right", "feature", "threshold", "value", "roots")


def export(model, outdir: Path, source: Path | None = None) -> dict:
    """Write the flat arrays of a fitted single-output RandomForestRegressor (or DecisionTreeRegressor list)."""
    trees = [e.tree_ for e in model.estimators_]
    if any(t.n_outputs != 1 or t.value.shape[1:] != (1, 1) for t in trees):
        raise ValueError("only single-output regression forests are supported")
    counts = np.array([t.node_count for t in trees], dtype=np.int64)
    offsets = np.concatenate([[0], np.cumsum(counts)[:-1]])
    total = int(counts.sum())
    if total >= np.iinfo(np.int32).max:
        raise ValueError("too many nodes for int32 indices")
    left = np.empty(total, np.int32)
    right = np.empty(total, np.int32)
    feature = np.empty(total, np.int16)
    threshold = np.empty(total, np.float64)
    value = np.empty(total, np.float64)
    for t, off, n in zip(trees, offsets, counts, strict=True):
        sl = slice(off, off + n)
        cl, cr = t.children_left, t.children_right
        left[sl] = np.where(cl >= 0, cl + off, -1)
        right[sl] = np.where(cr >= 0, cr + off, -1)
        feature[sl] = np.where(cl >= 0, t.feature, -1)
        threshold[sl] = t.threshold
        value[sl] = t.value[:, 0, 0]
    outdir.mkdir(parents=True, exist_ok=True)
    arrays = {"left": left, "right": right, "feature": feature, "threshold": threshold, "value": value,
              "roots": offsets.astype(np.int64)}
    for name, arr in arrays.items():
        np.save(outdir / f"{name}.npy", arr)
    meta = {"n_trees": len(trees), "n_nodes": total, "max_depth": int(max(t.max_depth for t in trees)),
            "n_features": int(model.n_features_in_)}
    if source is not None:
        st = source.stat()
        meta["source"] = {"name": source.name, "size": st.st_size, "mtime_ns": st.st_mtime_ns}
    (outdir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


class CompactForest:
    def __init__(self, arrays: dict[str, np.ndarray], meta: dict) -> None:
        self.left, self.right = arrays["left"], arrays["right"]
        self.feature, self.threshold = arrays["feature"], arrays["threshold"]
        self.value, self.roots = arrays["value"], np.asarray(arrays["roots"])
        self.meta = meta
        self.n_trees = len(self.roots)

    @classmethod
    def load(cls, outdir: Path, source: Path | None = None) -> CompactForest:
        meta = json.loads((outdir / "meta.json").read_text(encoding="utf-8"))
        if source is not None:
            st, rec = source.stat(), meta.get("source", {})
            if (rec.get("size"), rec.get("mtime_ns")) != (st.st_size, st.st_mtime_ns):
                raise ValueError(f"{outdir} was exported from a different {source.name}; run "
                                 "`python -m nycemis export-legacy-compact`")
        arrays = {name: np.load(outdir / f"{name}.npy", mmap_mode="r") for name in ARRAYS}
        return cls(arrays, meta)

    def predict(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float32)  # scikit-learn's tree input dtype
        if x.ndim != 2 or x.shape[1] != self.meta["n_features"]:
            raise ValueError(f"expected shape (n, {self.meta['n_features']}), got {x.shape}")
        if not np.isfinite(x).all():
            raise ValueError("non-finite input (scikit-learn's missing-value routing is not reproduced)")
        n, n_trees = len(x), self.n_trees
        node = np.tile(self.roots, n)  # pair p = (row p // n_trees, tree p % n_trees)
        row = np.repeat(np.arange(n), n_trees)
        active = np.arange(n * n_trees)
        while active.size:
            nd = node[active]
            lc = self.left[nd]
            internal = lc >= 0
            active, nd, lc = active[internal], nd[internal], lc[internal]
            go_left = x[row[active], self.feature[nd]] <= self.threshold[nd]
            node[active] = np.where(go_left, lc, self.right[nd])
        leaf_values = self.value[node].reshape(n, n_trees)
        out = np.zeros(n, dtype=np.float64)
        for t in range(n_trees):  # estimator order, as RandomForestRegressor accumulates
            out += leaf_values[:, t]
        out /= n_trees
        return out
