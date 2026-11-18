"""Legacy-protocol replication metrics (docs/SPECIFICATION.md 7.4, 9.9).

The legacy "percentage drop" summed every record of the baseline emission file (whole run) and every record of
the controlled file (a run stopped at 1000 steps). With per-step network NOx (``network_series.parquet``) both are
emulated: the legacy metric compares the full baseline sum with the controlled run's sum up to the legacy horizon;
the matched metric compares full-run totals (all trips complete in both runs).
"""

from __future__ import annotations

import json

import pandas as pd

from nycemis.paths import results_dir

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


def d1_confirmed(rep: dict) -> bool:
    """The horizon artifact is reproduced if the legacy metric reports a large drop where the matched one does not."""
    s = [v for k, v in rep["summary"].items() if k.startswith("legacy_ml/")]
    return bool(s) and all(v["legacy_metric_drop_pct_min"] >= 50.0 and abs(v["matched_drop_pct_mean"]) < 10.0
                           for v in s)


def recount() -> dict | None:
    """The legacy rule's route changes counted with the corrected counter (DEVIATIONS #18), if available."""
    path = results_dir() / "legacy_audit" / "route_change_recount.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def mean_change_rate(rep: dict, label: str = "legacy_ml") -> float:
    """Share of the legacy rule's calls that changed the vehicle's path. The pilot runs' own count treated every call
    made while the vehicle crossed a junction as a change (DEVIATIONS #18), so the recount is used when it exists."""
    rc = recount() if label == "legacy_ml" else None
    if rc:
        return float(rc["route_change_rate_all"])
    s = [v["route_change_rate_mean"] for k, v in rep["summary"].items() if k.startswith(f"{label}/")]
    return sum(s) / len(s) if s else float("nan")


def rate_text(rate: float) -> str:
    """A share as a percentage with enough digits to show a small value."""
    return f"{100 * rate:.3f}%" if rate < 0.01 else f"{100 * rate:.1f}%"


def render_replication_section(rep: dict) -> str:
    rf = rep["legacy_rf"]
    lines = [
        "## 5. Legacy-protocol replication (M4)",
        "",
        "Condition C5 (`legacy_ml`) reproduces the legacy rule under the matched protocol on the five pilot seeds at "
        "three demand levels (Flushing). Numbers come from `results/legacy_audit/replication.json` and "
        "`results/legacy_audit/legacy_rf_eval.json`.",
        "",
        "### The legacy predictor (7.4 i)",
        "",
        f"- RF ({rf['model']}) on {rf['rows_used']:,} per-vehicle-step records from static runs on train seeds "
        f"{rf['train_seeds']}, random 80/20 row split: R2 {rf['rf_random_split']['r2']:.4f}, MSE "
        f"{rf['rf_random_split']['mse']:.4g} (mg/s)^2.",
        f"- Split by run (train seed 0, test seed 1): R2 {rf['rf_split_by_run_seed0_to_seed1']['r2']:.4f}. The score "
        "does not depend on the row split: the task is nearly deterministic because the inputs and the target are "
        "outputs of the same emission model at the same instant.",
        f"- Single-feature monotone baseline (isotonic NOx on CO2 alone): R2 "
        f"{rf['isotonic_co2_only_random_split']['r2']:.4f}. With a mixed fleet one pollutant is not enough; the four "
        "pollutants together identify the emission class.",
        f"- Threshold: the legacy run flagged {100 * rf['legacy_flag_share']:.2f}% of vehicle-steps; the matching "
        f"training-NOx quantile is {rf['threshold_quantile_mg_s']:.3f} mg/s (primary C5). The literal 1.88 mg/s is "
        f"the {100 * rf['literal_threshold_training_quantile']:.1f}th percentile (variant `legacy_ml_literal`).",
        "",
        f"### Legacy metric vs matched metric (horizon {rep['horizon_s']:.0f} s)",
        "",
        "The legacy metric sums the static run's NOx over its whole duration and the C5 run's NOx over the first "
        f"{rep['horizon_s']:.0f} s, as the legacy notebook did. The matched metric compares complete runs.",
        "",
        "| Condition / level | Seeds | Legacy metric: drop % (min to max) | Matched metric: drop % (min to max) "
        "| Route-change rate | Flagged vehicle-steps |",
        "|---|---|---|---|---|---|",
    ]
    rc = recount()
    for key, v in rep["summary"].items():
        level = key.split("/")[1]
        recounted = bool(rc) and key.startswith("legacy_ml/") and level in rc["per_level"]
        rate = (f"{rc['per_level'][level]['route_change_rate']:.5f}" if recounted else
                f"{v['route_change_rate_mean']:.3f}" + (" (old counter, overstated; DEVIATIONS #18)" if rc else ""))
        lines.append(f"| {key} | {v['n']} | {v['legacy_metric_drop_pct_mean']:.1f} ({v['legacy_metric_drop_pct_min']:.1f}"
                     f" to {v['legacy_metric_drop_pct_max']:.1f}) | {v['matched_drop_pct_mean']:.2f} "
                     f"({v['matched_drop_pct_min']:.2f} to {v['matched_drop_pct_max']:.2f}) | "
                     f"{rate} | {100 * v['flag_share_mean']:.1f}% |")
    verdict = ("reproduced: the legacy metric reports a large drop on every seed and level while the matched "
               "metric does not" if d1_confirmed(rep) else
               "not reproduced in the form stated; see the table")
    if rc:
        calls = sum(v["reroute_calls"] for v in rc["per_level"].values())
        changes = sum(v["route_changes"] for v in rc["per_level"].values())
        old = sum(v["old_counter_rate_mean"] for v in rc["per_level"].values()) / len(rc["per_level"])
        d2 = (f"- D2 (no-op intervention): {changes:,} of {calls:,} findRoute/setRoute calls of the legacy rule "
              f"({rate_text(mean_change_rate(rep))}) changed the vehicle's path (C5 at the quantile threshold; "
              "`legacy_ml` rows of the route-change column; recounted on the pilot seeds with the corrected counter, "
              "`results/legacy_audit/route_change_recount.json`; total NOx "
              f"{'identical to' if rc['nox_identical_to_pilot'] else 'DIFFERENT from'} the original pilot runs). "
              f"The first count, {100 * old:.1f}%, treated every call made while the vehicle crossed a junction "
              "as a change (docs/DEVIATIONS.md #18). As in the legacy notebook, the rule leaves routes unchanged.")
    else:
        d2 = (f"- D2 (no-op intervention): across levels, {rate_text(mean_change_rate(rep))} of the legacy rule's "
              "findRoute/setRoute calls changed the vehicle's remaining route (C5 at the quantile threshold).")
    lines += [
        "",
        f"- D1 (unmatched horizon): {verdict}.",
        d2,
        "- PC1 (C5 vs C0, equivalence within 2%) is tested on the confirmatory seeds; the pilot numbers here are "
        "interim and not confirmatory.",
        "",
    ]
    path = results_dir() / "legacy_audit" / "replication_confirmatory.json"
    if path.is_file():
        test = json.loads(path.read_text(encoding="utf-8"))
        lines += ["### On the test seeds", "",
                  "The same comparison on the confirmatory test seeds (`results/legacy_audit/"
                  "replication_confirmatory.json`; exploratory). Matched metric as a change (negative = lower NOx).",
                  "", "| Level | Seeds | Legacy metric: drop % (min to max) | Matched metric: change % (min to max) |",
                  "|---|---|---|---|"]
        for key, v in test["summary"].items():
            if key.startswith("legacy_ml/"):
                lines.append(f"| {key.split('/')[1]} | {v['n']} | {v['legacy_metric_drop_pct_mean']:.1f} "
                             f"({v['legacy_metric_drop_pct_min']:.1f} to {v['legacy_metric_drop_pct_max']:.1f}) | "
                             f"{-v['matched_drop_pct_mean']:+.2f} ({-v['matched_drop_pct_max']:+.2f} to "
                             f"{-v['matched_drop_pct_min']:+.2f}) |")
        lines.append("")
    return "\n".join(lines)
