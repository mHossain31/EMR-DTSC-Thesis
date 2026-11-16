"""Figures required by docs/SPECIFICATION.md 4.7, drawn only from results files (never edited by hand)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from nycemis.analysis.pilot import paired_deltas  # noqa: E402
from nycemis.experiments.plan import exp_dir  # noqa: E402
from nycemis.sim.netinfo import NetInfo  # noqa: E402

LEVELS = ("light", "moderate", "heavy")
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def slope_plot(df: pd.DataFrame, cond: str, ref: str, path: Path, metric: str = "total_nox_g",
               unit: str = "total NOx (g)") -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.2), sharey=False)
    for ax, level in zip(axes, LEVELS, strict=True):
        pdf = paired_deltas(df, cond, ref, metric)
        g = pdf[pdf.level == level]
        for _, r in g.iterrows():
            color = "#2166ac" if r[f"{metric}_a"] < r[f"{metric}_b"] else "#b2182b"
            ax.plot([0, 1], [r[f"{metric}_b"], r[f"{metric}_a"]], color=color, lw=0.8, alpha=0.7)
        ax.set_xticks([0, 1], [ref, cond], rotation=15)
        ax.set_title(f"{level} (n = {len(g)})")
    axes[0].set_ylabel(unit)
    fig.suptitle(f"{cond} vs {ref}: paired by seed (blue: lower, red: higher)")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def forest_plot(rows: list[dict], path: Path, title: str, margin: float | None = 2.0) -> Path:
    rows = list(rows)
    fig, ax = plt.subplots(figsize=(7, 0.32 * len(rows) + 1.2))
    for i, r in enumerate(rows):
        y = len(rows) - i
        ax.plot([r["ci95_low"], r["ci95_high"]], [y, y], color="#333333", lw=1.2)
        ax.plot(r["mean_pct"], y, "o", color="#2166ac", ms=4)
    ax.set_yticks(range(len(rows), 0, -1), [r["label"] for r in rows])
    ax.axvline(0, color="#999999", lw=0.8)
    if margin:
        for m in (-margin, margin):
            ax.axvline(m, color="#999999", lw=0.6, ls="--")
    ax.set_xlabel("change in total NOx vs reference (%), mean and 95% BCa CI")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def pareto_plot(per_level: dict[str, list[dict]], path: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.2), sharey=True)
    colors = {"eco_reactive": "#1b9e77", "eco_ml": "#d95f02"}
    for ax, level in zip(axes, LEVELS, strict=True):
        for ctl, rows in per_level.items():
            t = pd.DataFrame(rows)
            t = t[t.level == level].sort_values("alpha")
            ax.plot(100 * (t.tt_ratio - 1), 100 * (t.nox_ratio - 1), "o-", color=colors.get(ctl, "k"), ms=3,
                    label=ctl)
            for _, r in t.iterrows():
                ax.annotate(f"{r.alpha:g}", (100 * (r.tt_ratio - 1), 100 * (r.nox_ratio - 1)), fontsize=6)
        ax.axvline(5, color="#999999", lw=0.6, ls="--")
        ax.axhline(0, color="#999999", lw=0.6)
        ax.set_title(level)
        ax.set_xlabel("mean travel time vs tt_adaptive (%)")
    axes[0].set_ylabel("total NOx vs tt_adaptive (%)")
    axes[0].legend(fontsize=7)
    fig.suptitle("alpha sweep on validation seeds (labels: alpha)")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def skill_plot(bootstrap: dict, path: Path) -> Path:
    keys = sorted(bootstrap)
    fig, ax = plt.subplots(figsize=(7, 0.3 * len(keys) + 1.2))
    for i, k in enumerate(keys):
        lo, hi = bootstrap[k]["ci95_low"], bootstrap[k]["ci95_high"]
        ax.plot([lo, hi], [i, i], color="#333333", lw=2)
    ax.set_yticks(range(len(keys)), [k.replace("_mae_skill_vs_", " vs ") for k in keys])
    ax.axvline(0, color="#999999", lw=0.8)
    ax.set_xlabel("MAE skill = 1 - MAE(model) / MAE(baseline), 95% cluster-bootstrap interval")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def road_class_bars(tab: pd.DataFrame, labels: list[str], path: Path) -> Path:
    cols = [c for c in tab.columns if c.startswith("share_")]
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.2), sharey=True)
    for ax, level in zip(axes, LEVELS, strict=True):
        m = tab[tab.level == level].groupby("label")[cols].mean().reindex(labels)
        bottom = np.zeros(len(m))
        for c in cols:
            ax.bar(range(len(m)), 100 * m[c].to_numpy(), bottom=bottom, label=c.replace("share_", ""))
            bottom += 100 * m[c].to_numpy()
        ax.set_xticks(range(len(m)), m.index, rotation=30, ha="right")
        ax.set_title(level)
    axes[0].set_ylabel("share of edge NOx (%)")
    axes[-1].legend(fontsize=6, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def edge_difference_map(experiment: str, runs: pd.DataFrame, cond: str, ref: str, level: str, info: NetInfo,
                        net, path: Path) -> Path:
    """Mean over seeds of per-edge cumulative NOx (cond - ref), in g per lane-km, drawn on the network."""
    def mean_edge(label: str) -> np.ndarray:
        acc = np.zeros(info.n)
        sel = runs[(runs.label == label) & (runs.level == level)]
        for rid in sel.run_id:
            cum = pd.read_parquet(exp_dir(experiment) / rid / "edge_cumulative.parquet")
            acc[cum.edge_idx.to_numpy()] += cum.nox_mg.to_numpy()
        return acc / max(1, len(sel))

    diff = (mean_edge(cond) - mean_edge(ref)) / 1000.0 / (info.lane_m / 1000.0)
    lim = np.percentile(np.abs(diff), 99) or 1.0
    cmap = plt.get_cmap("RdBu_r")
    fig, ax = plt.subplots(figsize=(7, 7))
    for i, eid in enumerate(info.edge_ids):
        xs, ys = zip(*net.getEdge(eid).getShape(), strict=True)
        ax.plot(xs, ys, color=cmap(0.5 + 0.5 * np.clip(diff[i] / lim, -1, 1)), lw=0.6 + 0.3 * info.lanes[i])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(-lim, lim))
    fig.colorbar(sm, ax=ax, shrink=0.6, label=f"NOx {cond} - {ref} (g per lane-km)")
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(f"{level}: mean per-edge NOx difference over seeds")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path
