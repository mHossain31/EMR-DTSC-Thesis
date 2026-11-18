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


# ---- added after the adversarial review (docs/DEVIATIONS.md #17); all exploratory
LEVELS = ("light", "moderate", "heavy")
EXPLORATORY_MACROS = (  # (metric, condition, reference, macro stem)
    ("mean_tt_s", "eco_ml", "tt_adaptive", "EcoTTvsTT"), ("p95_tt_s", "eco_ml", "tt_adaptive", "EcoPTTvsTT"),
    ("mean_tt_s", "eco_ml", "static", "EcoTTvsStatic"), ("total_nox_g", "eco_ml", "random_reroute", "EcoNOxVsPlacebo"),
    ("total_co2_kg", "eco_ml", "static", "EcoCOTwoVsStatic"), ("vkm_total", "eco_ml", "static", "EcoVkmVsStatic"),
    ("total_nox_g", "eco_reactive", "static", "ReactiveNOxVsStatic"),
    ("total_nox_g", "tt_adaptive", "static", "TTNOxVsStatic"),
    ("total_nox_g", "random_reroute", "static", "PlaceboNOxVsStatic"),
)


def _review_macros(c: dict) -> dict[str, str]:
    from nycemis.analysis.claims import equivalence_direction

    m: dict[str, str] = {}
    sds = [r["sd_pct"] for r in c["confirmatory"]]
    m["ObservedSDMin"], m["ObservedSDMax"] = f"{min(sds):.2f}", f"{max(sds):.2f}"
    notes = [equivalence_direction(r) for r in c["confirmatory"] if r["pc"] == "PC4"]
    m["PCFourDirection"] = _tex(" ".join(n for n in notes if n))
    expl = {(r["metric"], r["condition"], r["reference"], r["level"]): r for r in c["exploratory"]}
    for metric, cond, ref, stem in EXPLORATORY_MACROS:
        for lvl in LEVELS:
            r = expl.get((metric, cond, ref, lvl))
            if r:
                m[_name(stem, lvl)] = f"{r['mean_pct']:+.1f}"
    runs = results_dir() / "confirmatory" / "runs.csv"
    if runs.is_file():
        import pandas as pd

        delay = pd.read_csv(runs).groupby(["label", "level"]).mean_depart_delay_s.mean()
        for (label, lvl), v in delay.items():
            m[_name("DepartDelay", label, lvl)] = f"{v:.1f}"
    return m


def _spatial_macros() -> dict[str, str]:
    s = _load(results_dir() / "confirmatory" / "spatial_summary.json")
    tab = results_dir() / "confirmatory" / "spatial.csv"
    if not s or not tab.is_file():
        return {}
    import pandas as pd

    m: dict[str, str] = {}
    rows = {(r["condition"], r["reference"], r["level"], r["metric"]): r for r in s["paired"]}
    shares = pd.read_csv(tab).groupby(["label", "level"])["share_residential/service"].mean()
    stems = {"nox_residential/service_pct": "ResidNOx", "veh_h_residential/service_pct": "ResidVehH",
             "nox_tertiary_pct": "TertiaryNOx", "nox_primary/secondary_pct": "PrimSecNOx",
             "nox_motorway/trunk_pct": "MotorwayNOx", "share_residential/service_pp": "ResidSharePP",
             "edge_nox_pct": "EdgeNOx", "gini_pct": "Gini", "p99_density_pct": "PeakDensity"}
    for ref, tag in (("static", ""), ("tt_adaptive", "VsTT")):
        for lvl in LEVELS:
            for metric, stem in stems.items():
                r = rows.get(("eco_ml", ref, lvl, metric))
                if r:
                    m[_name(stem + tag, lvl)] = f"{r['mean']:+.0f}" if metric.startswith(("nox_", "veh_h_")) \
                        else f"{r['mean']:+.1f}"
                    m[_name(stem + tag, "CI", lvl)] = f"{r['ci95_low']:+.1f} to {r['ci95_high']:+.1f}"
    for lvl in LEVELS:
        for label in ("static", "tt_adaptive", "eco_ml"):
            if (label, lvl) in shares:
                m[_name("ResidShare", label, lvl)] = f"{100 * shares[(label, lvl)]:.0f}"
    low = [c["ci95_low"] for c in s["composition"] if c["reference"] == "static"]
    if low:  # wording by the lowest 95% bound over levels: above one half -> mostly
        m["CompositionWord"] = "mostly" if min(low) > 0.5 else "partly" if min(low) > 0 else "not clearly"
    for c in s["composition"]:
        tag = "" if c["reference"] == "static" else "VsTT"
        m[_name("Composition" + tag, c["level"])] = f"{100 * c['explained_share']:.0f}"
        m[_name("Composition" + tag, "CI", c["level"])] = (f"{100 * c['ci95_low']:.0f} to "
                                                          f"{100 * c['ci95_high']:.0f}")
    return m


def _forecast_test_macros() -> dict[str, str]:
    f = _load(results_dir() / "confirmatory" / "forecast_test.json")
    if not f:
        return {}
    m: dict[str, str] = {"TestRuns": f"{f['meta']['runs_test']}"}
    for t in ("r", "v", "d"):
        for name, stem in (("model", "TestModelMAE"), ("historical_mean", "TestHistMAE"),
                           ("persistence", "TestPersistMAE")):
            m[_name(stem, t)] = f"{f['regression'][name][t]['mae']:.3f}"
        for base, stem in (("historical_mean", "TestSkillHist"), ("persistence", "TestSkillPersist")):
            b = f["bootstrap"][f"{t}_mae_skill_vs_{base}"]
            m[_name(stem, t)] = f"{b['ci95_low']:+.3f} to {b['ci95_high']:+.3f}"
        b = f["bootstrap"][f"{t}_mae_skill_vs_historical_mean"]
        m[_name("ForecastVerdict", t)] = ("beats" if b["ci95_low"] > 0 else "is worse than" if b["ci95_high"] < 0
                                          else "does not clearly beat")
    return m


def _legacy_test_macros() -> dict[str, str]:
    m: dict[str, str] = {}
    rep = _load(results_dir() / "legacy_audit" / "replication_confirmatory.json")
    if rep:
        for lvl in LEVELS:
            v = rep["summary"].get(f"legacy_ml/{lvl}")
            if v:
                m[_name("LegacyTest", lvl, "LegacyMetric")] = f"{v['legacy_metric_drop_pct_mean']:.1f}"
                m[_name("LegacyTest", lvl, "MatchedChange")] = f"{-v['matched_drop_pct_mean']:+.2f}"
                m["LegacyTestN"] = f"{v['n']}"
    rc = _load(results_dir() / "legacy_audit" / "route_change_recount.json")
    if rc:
        calls = sum(v["reroute_calls"] for v in rc["per_level"].values())
        changes = sum(v["route_changes"] for v in rc["per_level"].values())
        old = [v["old_counter_rate_mean"] for v in rc["per_level"].values()]
        m["LegacyRecountCalls"] = f"{calls:,}"
        m["LegacyRecountChanges"] = f"{changes:,}"
        m["LegacyRecountRate"] = f"{100 * rc['route_change_rate_all']:.3f}"
        m["LegacyOldCounterRate"] = f"{100 * sum(old) / len(old):.1f}"
    return m


def _network_macros(scenario: str) -> dict[str, str]:
    """Speed coding and junction control of the network (threat to validity): the modal speed per road class with
    its share of lane-km, and junction counts by type."""
    from collections import Counter

    import sumolib

    from nycemis.network.build import net_path
    from nycemis.sim.netinfo import road_class

    path = net_path(scenario)
    if not path.is_file():
        return {}
    net = sumolib.net.readNet(str(path), withInternal=False)
    km: dict[str, Counter] = {}
    for e in net.getEdges():
        cls = road_class(e.getType())
        km.setdefault(cls, Counter())[round(e.getSpeed() * 3.6)] += e.getLength() * e.getLaneNumber() / 1000.0
    m: dict[str, str] = {}
    for cls, stem in (("primary/secondary", "PrimSec"), ("tertiary", "Tertiary"), ("residential/service", "Resid")):
        if cls in km:
            speed, lane_km = km[cls].most_common(1)[0]
            m[_name("Speed", stem)] = f"{speed}"
            m[_name("SpeedShare", stem)] = f"{100 * lane_km / sum(km[cls].values()):.0f}"
    nodes = Counter(n.getType() for n in net.getNodes())
    m["JunctionsPriority"] = f"{nodes.get('priority', 0)}"
    m["JunctionsSignal"] = f"{nodes.get('traffic_light', 0)}"
    m["JunctionsStop"] = f"{nodes.get('allway_stop', 0) + nodes.get('priority_stop', 0)}"
    return m


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
    fz = _load(results_dir() / "validation" / "prereg_freeze.json")
    if fz and fz.get("power_at_n"):
        pw = fz["power_at_n"]
        m["PowerAtNSup"] = f"{100 * pw['superiority']:.0f}"
        m["PowerAtNEq"] = f"{100 * pw['equivalence']:.0f}"
        m["DetectableEffect"] = f"{pw['detectable_effect_pct']:.1f}"
        m["DetectableMargin"] = f"{pw['detectable_margin_pct']:.1f}"
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
        m.update(_review_macros(c))
    m.update(_spatial_macros())
    m.update(_forecast_test_macros())
    m.update(_legacy_test_macros())
    m.update(_network_macros("flushing"))
    if fm:
        for t in ("r", "v"):
            m[_name("HistMAE", t)] = f"{fm['regression']['historical_mean'][t]['mae']:.3f}"
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
