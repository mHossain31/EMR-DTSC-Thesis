"""Generate ``paper/macros.tex`` and ``paper/tables/*.tex`` from results files (docs/SPECIFICATION.md P1, M9).

Every number and every result sentence in the paper is a macro defined here; ``main.tex`` contains no typed result.
A missing input file leaves its macros undefined, so LaTeX stops instead of printing a stale or invented value.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

from nycemis.analysis.claims import confirmatory_sentence
from nycemis.config import base_config, load_yaml
from nycemis.network.build import REPAIR_OPTIONS
from nycemis.paths import configs_dir, models_dir, rel, repo_root, results_dir

PAPER = repo_root() / "paper"


def _name(*parts: str) -> str:
    """LaTeX macro names allow letters only: 'PC1', 'heavy' -> 'PCOneHeavy'."""
    words = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six",
             "7": "Seven", "8": "Eight", "9": "Nine"}
    s = "".join(p[:1].upper() + p[1:] for p in re.split(r"[^A-Za-z0-9]+", "-".join(parts)) if p)
    return "".join(words.get(ch, ch) for ch in s)


def _tex(s: str) -> str:
    return (s.replace("\\", r"\textbackslash{}").replace("%", r"\%").replace("&", r"\&").replace("_", r"\_")
            .replace("#", r"\#").replace("+-", r"$\pm$"))


def _load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def macros() -> dict[str, str]:
    m: dict[str, str] = {}
    a = _load(results_dir() / "legacy_audit" / "audit_numbers.json")
    if a:
        d1 = a["d1_horizon"]
        m["LegacyNOxDropRF"] = f"{d1['reported_drops_pct']['RF']['NOx']:g}"
        m["LegacyNOxDropXGB"] = f"{d1['reported_drops_pct']['XGBoost']['NOx']:g}"
        m["LegacyBaselineHorizon"] = f"{d1['baseline_t_max_mid_s']:,.0f}"
        m["LegacyControlledSteps"] = f"{d1['controlled_step_bound']}"
        m["LegacyRowRatioRF"] = f"{100 * d1['rf_row_ratio']:.1f}"
        m["LegacyRepeatUnchanged"] = f"{a['d2_reroutes']['rf']['repeat_unchanged']:,}"
        m["LegacyRepeatCalls"] = f"{a['d2_reroutes']['rf']['repeat_calls']:,}"
    rep = _load(results_dir() / "legacy_audit" / "replication.json")
    if rep:
        for key, v in rep["summary"].items():
            label, level = key.split("/")
            base = _name(label, level)
            m[f"{base}LegacyMetric"] = f"{v['legacy_metric_drop_pct_mean']:.1f}"
            m[f"{base}MatchedMetric"] = f"{v['matched_drop_pct_mean']:+.2f}"
            m[f"{base}ChangeRate"] = f"{100 * v['route_change_rate_mean']:.1f}"
        rf = rep["legacy_rf"]
        m["LegacyRFRTwo"] = f"{rf['rf_random_split']['r2']:.4f}"
        m["LegacyRFRunSplitRTwo"] = f"{rf['rf_split_by_run_seed0_to_seed1']['r2']:.4f}"
        m["LegacyIsoRTwo"] = f"{rf['isotonic_co2_only_random_split']['r2']:.2f}"
        m["LegacyThreshold"] = f"{rf['threshold_quantile_mg_s']:.2f}"
    lv = load_yaml(configs_dir() / "demand_levels.yaml")["scenarios"].get("flushing") if \
        (configs_dir() / "demand_levels.yaml").is_file() else None
    if lv:
        for name, v in lv["levels"].items():
            m[_name("density", name)] = f"{v['density_per_h_km']:g}"
            m[_name("rsr", name)] = f"{v['achieved_relative_speed_ratio']:.2f}"
            m[_name("vehicles", name)] = f"{v['mean_vehicles']:,.0f}"
    p = _load(results_dir() / "pilot" / "pilot_summary.json")
    if p:
        m["PilotSD"] = f"{p['power']['sd_pct_used']:.2f}"
        m["ConfirmatoryN"] = f"{p['power']['n_confirmatory']}"
        m["NPowerSup"] = f"{p['power']['n_superiority']}"
        m["NPowerEq"] = f"{p['power']['n_equivalence']}"
    sel = _load(results_dir() / "validation" / "selection.json")
    if sel:
        m["AlphaStarReactive"] = f"{sel['eco_reactive']['alpha_star']:g}"
        m["AlphaStarML"] = f"{sel['eco_ml']['alpha_star']:g}"
        m["EtaStar"] = f"{sel['random_reroute']['eta_star']:g}"
    fm = _load(models_dir() / "flushing" / "gbm_v1" / "metrics.json")
    if fm:
        for t in ("r", "v"):
            m[_name("ModelMAE", t)] = f"{fm['regression']['model'][t]['mae']:.3f}"
            m[_name("PersistMAE", t)] = f"{fm['regression']['persistence'][t]['mae']:.3f}"
            m[_name("ModelRTwo", t)] = f"{fm['regression']['model'][t]['r2']:.3f}"
        m["HotspotPRAUCModel"] = f"{fm['hotspot']['model']['pr_auc']:.3f}"
        m["HotspotPRAUCPersistence"] = f"{fm['hotspot']['persistence']['pr_auc']:.3f}"
    c = _load(results_dir() / "confirmatory" / "analysis.json")
    if c:
        for r in c["confirmatory"]:
            base = _name(r["pc"], r["level"])
            m[f"{base}Mean"] = f"{r['mean_pct']:+.2f}"
            m[f"{base}CI"] = f"{r['ci95_low']:+.2f} to {r['ci95_high']:+.2f}"
            m[f"{base}PHolm"] = f"{r['p_holm']:.3g}"
            m[f"{base}Sentence"] = _tex(confirmatory_sentence(r))
    cfg = base_config()
    m["SESOI"] = f"{cfg.analysis.sesoi_pct:g}"
    m["TestsInFamily"] = f"{cfg.analysis.n_confirmatory_tests}"
    m["FamilywiseAlpha"] = f"{cfg.analysis.familywise_alpha:g}"
    m["AlphaTTBudgetPct"] = f"{cfg.analysis.alpha_star_tt_budget_pct:g}"
    m["ValidCompletionPct"] = f"{100 * cfg.protocol.validity.completion_min:g}"
    m["ValidTeleportPct"] = f"{100 * cfg.protocol.validity.teleport_max_frac:g}"
    m["HorizonS"] = f"{cfg.protocol.horizon_s}"
    m["ReroutePeriodS"] = f"{cfg.protocol.reroute_period_s}"
    m["JunctionBlockerS"] = f"{cfg.protocol.ignore_junction_blocker_s}"
    m["JunctionJoinM"] = REPAIR_OPTIONS[REPAIR_OPTIONS.index("--junctions.join-dist") + 1]
    val = load_yaml(configs_dir() / "experiments" / "validation.yaml")
    tau = {c["params"]["tau_avg_s"] for c in val["conditions"] if "tau_avg_s" in c.get("params", {})}
    if len(tau) != 1:
        raise ValueError(f"validation conditions disagree on tau_avg_s: {sorted(tau)}")
    m["TauAvgS"] = f"{tau.pop()}"
    return m


def write_macros() -> str:
    lines = ["% Generated by `python -m nycemis paper`; do not edit by hand."]
    for k, v in sorted(macros().items()):
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    out = PAPER / "macros.tex"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rel(out)


def build_pdf() -> str | None:
    """Compile with tectonic (tools/ or PATH) or latexmk; return the PDF path, or None if no engine exists."""
    local = repo_root() / "tools" / "tectonic.exe"
    engine = str(local) if local.is_file() else shutil.which("tectonic")
    if engine:
        cmd = [engine, "-X", "compile", "main.tex", "--outdir", "build"]
    elif shutil.which("latexmk"):
        cmd = ["latexmk", "-pdf", "-outdir=build", "main.tex"]
    else:
        return None
    (PAPER / "build").mkdir(exist_ok=True)
    proc = subprocess.run(cmd, cwd=PAPER, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"LaTeX build failed:\n{(proc.stdout + proc.stderr)[-3000:]}")
    return rel(PAPER / "build" / "main.pdf")
