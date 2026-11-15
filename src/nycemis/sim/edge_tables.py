"""Per-edge emission tables from the in-process edge logger (docs/SPECIFICATION.md 4.5, 5.5, 6.6).

``edge_5min``: one row per 300 s interval and non-empty edge (NOx and CO2 in mg, vehicle-seconds, NOx density).
``edge_cumulative``: one row per edge with any traffic (whole run), with its road class.
SUMO's ``edgeData type="emissions"`` output was the cheaper alternative, but on the smoke grid it differed from the
in-process logger by 1.5% (attribution at lane boundaries), above the 0.1% the protocol allows, so it is not used.
Emissions on internal (junction) lanes are not attributed to any edge in these tables; the run totals come from
tripinfo and include them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from nycemis.sim.logger import EdgeStateLogger
from nycemis.sim.netinfo import ROAD_CLASS_NAMES, NetInfo

WINDOWS_PER_INTERVAL = 5  # 5 x 60 s


def edge_tables(elog: EdgeStateLogger, info: NetInfo) -> tuple[pd.DataFrame, pd.DataFrame]:
    nox = np.vstack(elog.window_nox) if elog.window_nox else np.zeros((0, info.n))
    co2 = np.vstack(elog.window_co2) if elog.window_co2 else np.zeros((0, info.n))
    vs = np.vstack(elog.window_veh_s) if elog.window_veh_s else np.zeros((0, info.n))
    n_int = int(np.ceil(len(nox) / WINDOWS_PER_INTERVAL))
    rows = []
    for j in range(n_int):
        sl = slice(j * WINDOWS_PER_INTERVAL, (j + 1) * WINDOWS_PER_INTERVAL)
        n_j, c_j, v_j = nox[sl].sum(axis=0), co2[sl].sum(axis=0), vs[sl].sum(axis=0)
        idx = np.flatnonzero((v_j > 0) | (n_j > 0))
        rows.append(pd.DataFrame({"begin_s": np.float32(j * WINDOWS_PER_INTERVAL * elog.window_s),
                                  "edge_idx": idx.astype(np.int32), "nox_mg": n_j[idx], "co2_mg": c_j[idx],
                                  "veh_s": v_j[idx]}))
    five = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        columns=["begin_s", "edge_idx", "nox_mg", "co2_mg", "veh_s"])
    five["nox_dens_mg_per_lane_m"] = five.nox_mg / info.lane_m[five.edge_idx.to_numpy(dtype=int)]
    tot_n, tot_c, tot_v = nox.sum(axis=0), co2.sum(axis=0), vs.sum(axis=0)
    idx = np.flatnonzero((tot_v > 0) | (tot_n > 0))
    cum = pd.DataFrame({"edge_idx": idx.astype(np.int32), "edge_id": [info.edge_ids[i] for i in idx],
                        "road_class": [ROAD_CLASS_NAMES[int(info.road_class[i])] for i in idx],
                        "lane_m": info.lane_m[idx], "nox_mg": tot_n[idx], "co2_mg": tot_c[idx], "veh_s": tot_v[idx]})
    return five, cum
