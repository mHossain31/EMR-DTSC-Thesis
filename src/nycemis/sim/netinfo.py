"""Static edge table of a network: fixed edge order, attributes, and 1-hop neighbour matrices.

Every per-edge array in the harness (logger windows, features, efforts) uses the order of ``NetInfo.edge_ids``:
the network's non-internal edges sorted by id.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import sumolib

from nycemis.network.validate import road_class

ROAD_CLASS_CODES = {"motorway/trunk": 0, "primary/secondary": 1, "tertiary": 2, "residential/service": 3, "other": 4}
ROAD_CLASS_NAMES = {v: k for k, v in ROAD_CLASS_CODES.items()}


@dataclass(frozen=True)
class NetInfo:
    net_file: str
    edge_ids: tuple[str, ...]
    index: dict[str, int]
    length_m: np.ndarray
    lanes: np.ndarray
    speed_limit_mps: np.ndarray
    road_class: np.ndarray  # int codes, ROAD_CLASS_CODES
    tls_downstream: np.ndarray  # bool: the edge ends at a traffic light
    in_degree: np.ndarray
    out_degree: np.ndarray
    upstream_mean: sp.csr_matrix  # row i averages over edges that feed edge i
    downstream_mean: sp.csr_matrix  # row i averages over edges that edge i feeds

    @property
    def n(self) -> int:
        return len(self.edge_ids)

    @property
    def freeflow_tt_s(self) -> np.ndarray:
        return self.length_m / self.speed_limit_mps

    @property
    def lane_m(self) -> np.ndarray:
        return self.length_m * self.lanes


def _row_mean(rows: list[int], cols: list[int], n: int) -> sp.csr_matrix:
    m = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    deg = np.asarray(m.sum(axis=1)).ravel()
    inv = np.divide(1.0, deg, out=np.zeros_like(deg), where=deg > 0)
    return sp.diags(inv) @ m


@lru_cache(maxsize=4)
def load_netinfo(net_file: str) -> NetInfo:
    net = sumolib.net.readNet(str(Path(net_file)))
    edges = sorted((e for e in net.getEdges() if e.getFunction() != "internal"), key=lambda e: e.getID())
    ids = tuple(e.getID() for e in edges)
    index = {eid: i for i, eid in enumerate(ids)}
    up_r, up_c, dn_r, dn_c = [], [], [], []
    for i, e in enumerate(edges):
        for succ in e.getOutgoing():
            j = index.get(succ.getID())
            if j is not None and j != i:
                dn_r.append(i)
                dn_c.append(j)
                up_r.append(j)
                up_c.append(i)
    n = len(ids)
    return NetInfo(
        net_file=str(net_file),
        edge_ids=ids,
        index=index,
        length_m=np.array([e.getLength() for e in edges], dtype=float),
        lanes=np.array([e.getLaneNumber() for e in edges], dtype=float),
        speed_limit_mps=np.array([e.getSpeed() for e in edges], dtype=float),
        road_class=np.array([ROAD_CLASS_CODES[road_class(e.getType())] for e in edges], dtype=np.int8),
        tls_downstream=np.array([e.getToNode().getType().startswith("traffic_light") for e in edges], dtype=bool),
        in_degree=np.bincount(up_r, minlength=n).astype(float) if up_r else np.zeros(n),
        out_degree=np.bincount(dn_r, minlength=n).astype(float) if dn_r else np.zeros(n),
        upstream_mean=_row_mean(up_r, up_c, n),
        downstream_mean=_row_mean(dn_r, dn_c, n),
    )
