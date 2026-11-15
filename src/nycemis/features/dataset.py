"""Record training rows during dataset runs (docs/SPECIFICATION.md 5.5 ``edge_window``, 7.1-7.3).

At each tick k the F2 features (a superset of F1) are computed online from windows k, k-1, k-2 with the same
``FeatureBuilder`` the live controller uses; when window k+1 closes, its targets are attached. Rows are kept for
edges with any vehicle-seconds in windows k-2 ... k+1; every other edge-window is an explicit zero (empty edge,
no NOx), and their count is recorded so the share of rows dropped is reported.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from nycemis.features.builder import FeatureBuilder, targets
from nycemis.sim.logger import Window
from nycemis.sim.netinfo import NetInfo


class DatasetRecorder:
    def __init__(self, info: NetInfo, window_s: float, depart_end_s: float):
        self.info = info
        self.builder = FeatureBuilder(info, window_s, depart_end_s, "F2")
        self.pending: tuple[Window, np.ndarray, np.ndarray] | None = None  # (window k, features, active k-2..k)
        self.recent_active: list[np.ndarray] = []
        self.chunks: list[pd.DataFrame] = []
        self.dropped_edge_windows = 0
        self.kept_edge_windows = 0

    def on_window(self, w: Window) -> None:
        active_now = w.veh_s > 0
        if self.pending is not None:
            wk, x, active_hist = self.pending
            keep = active_hist | active_now
            tg = targets(w, self.info)
            idx = np.flatnonzero(keep)
            df = pd.DataFrame(x[idx], columns=self.builder.names)
            df.insert(0, "edge_idx", idx.astype(np.int32))
            df.insert(0, "t_s", np.float32(wk.t_end_s))
            df.insert(0, "k", np.int32(wk.k))
            for name, values in tg.items():
                df[name] = values[idx].astype(np.float32)
            self.chunks.append(df)
            self.kept_edge_windows += len(idx)
            self.dropped_edge_windows += int((~keep).sum())
        self.builder.push(w)
        self.recent_active = (self.recent_active + [active_now])[-3:]
        active_hist = np.logical_or.reduce(self.recent_active)
        self.pending = (w, self.builder.features(), active_hist)

    def frame(self) -> pd.DataFrame:
        if not self.chunks:
            return pd.DataFrame()
        return pd.concat(self.chunks, ignore_index=True)
