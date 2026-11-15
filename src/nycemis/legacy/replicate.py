"""Legacy-protocol replication metrics (docs/SPECIFICATION.md 7.4, 9.9).

The legacy "percentage drop" summed every record of the baseline emission file (whole run) and every record of
the controlled file (a run stopped at 1000 steps). With per-step network NOx (``network_series.parquet``) both are
emulated: the legacy metric compares the full baseline sum with the controlled run's sum up to the legacy horizon;
the matched metric compares full-run totals (all trips complete in both runs).
"""

from __future__ import annotations

import pandas as pd

LEGACY_HORIZON_S = 1000


def legacy_metric_drop_pct(base_series: pd.DataFrame, ctl_series: pd.DataFrame,
                           ctl_horizon_s: float = LEGACY_HORIZON_S) -> float:
    """Legacy-style percentage drop: (sum base all - sum ctl up to horizon) / sum base all * 100."""
    base = float(base_series.nox_mg.sum())
    ctl = float(ctl_series.loc[ctl_series.t_s <= ctl_horizon_s, "nox_mg"].sum())
    return 100.0 * (base - ctl) / base


def matched_drop_pct(base_total: float, ctl_total: float) -> float:
    """Matched-protocol percentage drop of totals over complete runs."""
    return 100.0 * (base_total - ctl_total) / base_total
