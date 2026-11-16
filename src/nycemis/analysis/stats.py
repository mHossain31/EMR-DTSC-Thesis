"""Paired statistics of docs/SPECIFICATION.md 4.2 and 4.7.

Per seed: delta% = 100 * (Y_cond - Y_ref) / Y_ref. Superiority: two-sided paired Wilcoxon signed-rank on delta%.
Equivalence (TOST against +-margin): two one-sided Wilcoxon tests on delta% + margin (alternative greater) and
delta% - margin (alternative less); the TOST p-value is the larger. Multiplicity: Holm over the confirmatory family.
Intervals: BCa bootstrap of the mean delta% (fixed seed). Effect size: d_z = mean / SD of delta%.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests


def pct_change(y: np.ndarray, ref: np.ndarray) -> np.ndarray:
    y, ref = np.asarray(y, float), np.asarray(ref, float)
    if (ref <= 0).any():
        raise ValueError("reference values must be positive")
    return 100.0 * (y - ref) / ref


def wilcoxon_two_sided(d: np.ndarray) -> float:
    d = np.asarray(d, float)
    if np.allclose(d, 0):
        return 1.0
    return float(stats.wilcoxon(d, alternative="two-sided", zero_method="wilcox").pvalue)


def tost_wilcoxon(d: np.ndarray, margin: float) -> float:
    d = np.asarray(d, float)
    p_low = stats.wilcoxon(d + margin, alternative="greater", zero_method="wilcox").pvalue
    p_high = stats.wilcoxon(d - margin, alternative="less", zero_method="wilcox").pvalue
    return float(max(p_low, p_high))


def bca_ci(d: np.ndarray, level: float, n_resamples: int, seed: int) -> tuple[float, float]:
    d = np.asarray(d, float)
    if np.allclose(d, d[0]):
        return float(d[0]), float(d[0])
    res = stats.bootstrap((d,), np.mean, confidence_level=level, n_resamples=n_resamples, method="BCa",
                          random_state=np.random.default_rng(seed))
    return float(res.confidence_interval.low), float(res.confidence_interval.high)


@dataclass
class PairedResult:
    n: int
    mean_pct: float
    median_pct: float
    sd_pct: float
    ci95_low: float
    ci95_high: float
    ci90_low: float
    ci90_high: float
    d_z: float
    p_wilcoxon: float
    p_tost: float | None

    def as_dict(self) -> dict:
        return asdict(self)


def paired(d: np.ndarray, margin: float | None, n_resamples: int, seed: int) -> PairedResult:
    d = np.asarray(d, float)
    sd = float(d.std(ddof=1)) if len(d) > 1 else float("nan")
    lo95, hi95 = bca_ci(d, 0.95, n_resamples, seed)
    lo90, hi90 = bca_ci(d, 0.90, n_resamples, seed)
    return PairedResult(n=len(d), mean_pct=float(d.mean()), median_pct=float(np.median(d)), sd_pct=sd,
                        ci95_low=lo95, ci95_high=hi95, ci90_low=lo90, ci90_high=hi90,
                        d_z=float(d.mean() / sd) if sd and sd > 0 else float("nan"),
                        p_wilcoxon=wilcoxon_two_sided(d),
                        p_tost=tost_wilcoxon(d, margin) if margin is not None else None)


def holm(pvalues: list[float], alpha: float) -> tuple[list[bool], list[float]]:
    reject, adj, _, _ = multipletests(pvalues, alpha=alpha, method="holm")
    return [bool(r) for r in reject], [float(p) for p in adj]
