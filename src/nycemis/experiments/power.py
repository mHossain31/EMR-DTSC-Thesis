"""Sample size for the confirmatory runs (docs/SPECIFICATION.md 4.6).

n_power is the smallest n with at least 80% power, at the most stringent Holm threshold (alpha = 0.05 / 12), for
(a) superiority: a true paired effect of 2% (the SESOI) detected by the two-sided Wilcoxon signed-rank test, and
(b) equivalence: a true effect of 0 declared equivalent within +-2% by TOST with two one-sided Wilcoxon tests.
Paired percent differences are simulated as normal with the pilot's SD (the largest SD over the pilot's paired
comparisons and demand levels, the noisiest case). Power is estimated by Monte Carlo with a fixed seed.
n = max(30, ceil(1.2 * n_power)), capped at 60.
"""

from __future__ import annotations

import math

import numpy as np

from nycemis.analysis.stats import tost_wilcoxon, wilcoxon_two_sided

TARGET_POWER = 0.80


def _power(kind: str, n: int, sd: float, sesoi: float, alpha: float, sims: int, rng: np.random.Generator) -> float:
    hits = 0
    for _ in range(sims):
        if kind == "superiority":
            d = rng.normal(sesoi, sd, n)
            hits += wilcoxon_two_sided(d) < alpha
        else:
            d = rng.normal(0.0, sd, n)
            hits += tost_wilcoxon(d, sesoi) < alpha
    return hits / sims


def n_required(kind: str, sd: float, sesoi: float, alpha: float, sims: int = 2000, seed: int = 20261115,
               n_max: int = 400) -> tuple[int | None, list[tuple[int, float]]]:
    """Smallest n with power >= 0.8 (doubling search, then bisection); None if above n_max."""
    rng = np.random.default_rng(seed)
    curve: list[tuple[int, float]] = []

    def pw(n: int) -> float:
        p = _power(kind, n, sd, sesoi, alpha, sims, rng)
        curve.append((n, p))
        return p

    lo, hi = 5, 10
    while pw(hi) < TARGET_POWER:
        lo, hi = hi, hi * 2
        if hi > n_max:
            return None, curve
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if pw(mid) >= TARGET_POWER:
            hi = mid
        else:
            lo = mid
    return hi, sorted(curve)


def confirmatory_n(n_power: int | None, n_min: int, n_max: int) -> int:
    if n_power is None:
        return n_max
    return int(min(n_max, max(n_min, math.ceil(1.2 * n_power))))
