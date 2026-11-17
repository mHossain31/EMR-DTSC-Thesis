"""Statistics against reference values (docs/SPECIFICATION.md 9.1)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from nycemis.analysis.spatial import gini
from nycemis.analysis.stats import bca_ci, holm, paired, pct_change, tost_wilcoxon, wilcoxon_two_sided
from nycemis.experiments.power import confirmatory_n, detectable_at, power_at


def test_pct_change() -> None:
    np.testing.assert_allclose(pct_change([98.0, 105.0], [100.0, 100.0]), [-2.0, 5.0])
    with pytest.raises(ValueError):
        pct_change([1.0], [0.0])


def test_wilcoxon_matches_scipy() -> None:
    d = np.array([-3.1, -2.2, -0.5, -1.7, 0.4, -2.9, -1.1, -0.8, -2.5, 0.3])
    assert wilcoxon_two_sided(d) == pytest.approx(stats.wilcoxon(d).pvalue)


def test_tost_declares_equivalence_only_inside_the_margin() -> None:
    rng = np.random.default_rng(1)
    inside = rng.normal(0.0, 0.5, 30)
    outside = rng.normal(3.0, 0.5, 30)
    assert tost_wilcoxon(inside, 2.0) < 0.001
    assert tost_wilcoxon(outside, 2.0) > 0.5
    lo = stats.wilcoxon(inside + 2.0, alternative="greater").pvalue
    hi = stats.wilcoxon(inside - 2.0, alternative="less").pvalue
    assert tost_wilcoxon(inside, 2.0) == pytest.approx(max(lo, hi))


def test_holm_reference() -> None:
    # Holm (1979) step-down: sorted p = 0.01, 0.02, 0.03, 0.04 with 4 tests -> 0.04, 0.06, 0.06, 0.06
    reject, adj = holm([0.04, 0.01, 0.03, 0.02], 0.05)
    np.testing.assert_allclose(adj, [0.06, 0.04, 0.06, 0.06])
    assert reject == [False, True, False, False]


def test_bca_matches_scipy() -> None:
    d = np.random.default_rng(3).normal(-1.0, 1.5, 25)
    lo, hi = bca_ci(d, 0.95, 2000, 7)
    ref = stats.bootstrap((d,), np.mean, confidence_level=0.95, n_resamples=2000, method="BCa",
                          random_state=np.random.default_rng(7)).confidence_interval
    assert (lo, hi) == pytest.approx((ref.low, ref.high))
    assert lo < d.mean() < hi


def test_paired_effect_size() -> None:
    d = np.array([-1.0, -2.0, -3.0, -2.0, -2.0])
    res = paired(d, None, 1000, 1)
    assert res.mean_pct == pytest.approx(-2.0)
    assert res.d_z == pytest.approx(-2.0 / d.std(ddof=1))
    assert res.p_tost is None


def test_confirmatory_n_rule() -> None:
    assert confirmatory_n(10, 30, 60) == 30
    assert confirmatory_n(40, 30, 60) == 48
    assert confirmatory_n(70, 30, 60) == 60
    assert confirmatory_n(None, 30, 60) == 60


@pytest.mark.parametrize("kind", ["superiority", "equivalence"])
def test_detectable_effect_is_the_80_percent_power_point(kind: str) -> None:
    sim = {"alpha": 0.05, "sims": 300, "seed": 3}
    e = detectable_at(kind, 20, 3.0, tol=0.02, **sim)
    assert power_at(kind, 20, 3.0, e, **sim) >= 0.8
    assert power_at(kind, 20, 3.0, e - 0.02, **sim) < 0.8


def test_gini() -> None:
    assert gini(np.array([1.0, 1.0, 1.0, 1.0])) == pytest.approx(0.0)
    assert gini(np.array([0.0, 0.0, 0.0, 4.0])) == pytest.approx(0.75)
