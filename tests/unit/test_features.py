"""Feature builder on a hand-derived toy network, and the poison test (docs/SPECIFICATION.md 7.2, 9.1, 9.6)."""

from __future__ import annotations

import numpy as np
import pytest
import scipy.sparse as sp

from nycemis.features.builder import FeatureBuilder, feature_names, targets
from nycemis.features.dataset import DatasetRecorder
from nycemis.sim.logger import Window
from nycemis.sim.netinfo import NetInfo


def toy_info() -> NetInfo:
    """Chain a -> b -> c: lengths 100, 200, 300 m; 1, 2, 1 lanes; limits 10, 20, 10 m/s; c ends at a signal."""
    up = sp.csr_matrix(np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float))
    down = sp.csr_matrix(np.array([[0, 1, 0], [0, 0, 1], [0, 0, 0]], dtype=float))
    return NetInfo(net_file="toy", edge_ids=("a", "b", "c"), index={"a": 0, "b": 1, "c": 2},
                   length_m=np.array([100.0, 200.0, 300.0]), lanes=np.array([1.0, 2.0, 1.0]),
                   speed_limit_mps=np.array([10.0, 20.0, 10.0]), road_class=np.array([3, 1, 2], dtype=np.int8),
                   tls_downstream=np.array([False, False, True]), in_degree=np.array([0.0, 1.0, 1.0]),
                   out_degree=np.array([1.0, 1.0, 0.0]), upstream_mean=up, downstream_mean=down)


def window(k: int, veh_s, speed, nox, halting=(0, 0, 0), waiting=(0, 0, 0), max_count=None) -> Window:
    veh_s = np.asarray(veh_s, dtype=float)
    return Window(k=k, t_end_s=60.0 * (k + 1), steps=60, veh_s=veh_s, speed_x_veh_s=veh_s * np.asarray(speed, float),
                  max_count=np.asarray(max_count if max_count is not None else veh_s / 60, float),
                  halting_s=np.asarray(halting, float), waiting_sum_s=np.asarray(waiting, float),
                  nox_mg=np.asarray(nox, float), co2_mg=np.zeros(3))


def test_feature_values_on_toy_network() -> None:
    info = toy_info()
    fb = FeatureBuilder(info, 60.0, 3600.0, "F1")
    fb.push(window(0, [120, 0, 60], [5, 0, 10], [30, 0, 12], halting=[60, 0, 0]))
    x = fb.features()
    col = {n: i for i, n in enumerate(feature_names("F1"))}
    assert x.shape == (3, len(col))
    np.testing.assert_allclose(x[:, col["cnt_mean_l0"]], [2.0, 0.0, 1.0])
    np.testing.assert_allclose(x[:, col["speed_ratio_l0"]], [0.5, 1.0, 1.0])  # empty edge -> limit
    np.testing.assert_allclose(x[:, col["tt_ratio_l0"]], [2.0, 1.0, 1.0])
    np.testing.assert_allclose(x[:, col["halt_mean_l0"]], [1.0, 0.0, 0.0])
    np.testing.assert_allclose(x[:, col["up_cnt_mean"]], [0.0, 2.0, 0.0])  # b is fed by a; c by b
    np.testing.assert_allclose(x[:, col["down_cnt_mean"]], [0.0, 1.0, 0.0])  # a feeds b; b feeds c
    np.testing.assert_allclose(x[:, col["tls_downstream"]], [0, 0, 1])
    # lags k-1 and k-2 are an empty network before the second and third windows exist
    np.testing.assert_allclose(x[:, col["cnt_mean_l1"]], 0.0)
    np.testing.assert_allclose(x[:, col["speed_ratio_l2"]], 1.0)


def test_targets_and_masks() -> None:
    info = toy_info()
    t = targets(window(1, [5, 0, 60], [5, 0, 10], [10, 0, 12]), info)
    np.testing.assert_allclose(t["d_next"], [0.1, 0.0, 0.04])  # mg per lane-metre
    assert np.isnan(t["r_next"][0]) and np.isnan(t["r_next"][1])  # fewer than 10 vehicle-seconds
    assert t["r_next"][2] == pytest.approx(0.2)
    assert np.isnan(t["v_next"][1]) and t["v_next"][0] == pytest.approx(5.0)


def _record(windows: list[Window]):
    rec = DatasetRecorder(toy_info(), 60.0, 3600.0)
    for w in windows:
        rec.on_window(w)
    return rec.frame()


def test_poison_future_windows_do_not_change_features() -> None:
    """Sentinel values in window k+1 change the targets of tick k but none of its features."""
    w0 = window(0, [60, 30, 0], [8, 15, 0], [20, 5, 0])
    w1 = window(1, [90, 60, 30], [6, 12, 9], [25, 9, 4])
    w2 = window(2, [30, 90, 60], [9, 10, 7], [7, 20, 9])
    poisoned = window(2, [1e9, 1e9, 1e9], [1e9, 1e9, 1e9], [1e9, 1e9, 1e9], halting=[1e9] * 3,
                      waiting=[1e9] * 3)
    clean = _record([w0, w1, w2])
    dirty = _record([w0, w1, poisoned])
    feats = feature_names("F2")
    a = clean[clean.k == 1][feats].to_numpy()
    b = dirty[dirty.k == 1][feats].to_numpy()
    np.testing.assert_array_equal(a, b)
    assert not np.allclose(clean[clean.k == 1].d_next.to_numpy(), dirty[dirty.k == 1].d_next.to_numpy())


def test_pushing_out_of_order_fails() -> None:
    fb = FeatureBuilder(toy_info(), 60.0, 3600.0)
    fb.push(window(0, [0, 0, 0], [0, 0, 0], [0, 0, 0]))
    with pytest.raises(ValueError):
        fb.push(window(2, [0, 0, 0], [0, 0, 0], [0, 0, 0]))


def test_f2_extends_f1() -> None:
    assert feature_names("F2")[: len(feature_names("F1"))] == feature_names("F1")
    assert not any(n.startswith("nox") for n in feature_names("F1"))
