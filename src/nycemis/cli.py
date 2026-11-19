"""Command-line interface: ``python -m nycemis <command>`` (docs/SPECIFICATION.md 5.2). Every stage is idempotent."""

from __future__ import annotations

import json
import logging

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True, help="SUMO + ML NYC emissions study")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v", help="debug logging")) -> None:
    _setup_logging(verbose)


@app.command()
def doctor(
    offline: bool = typer.Option(False, help="skip the Overpass reachability check"),
    as_json: bool = typer.Option(False, "--json", help="print the checks as JSON"),
) -> None:
    """Check Python, OS, cores, disk, SUMO, libsumo, TeX, Overpass, git and CARLA readiness."""
    from nycemis.doctor import format_report, run_checks

    checks = run_checks(include_network=not offline)
    if as_json:
        typer.echo(json.dumps([c.__dict__ for c in checks], indent=2))
    else:
        typer.echo(format_report(checks))
    if any(c.required and not c.ok for c in checks):
        raise typer.Exit(code=1)


net_app = typer.Typer(no_args_is_help=True, help="OSM download, network build and validation")
app.add_typer(net_app, name="net")


@net_app.command("fetch")
def net_fetch(
    scenario: str = typer.Option(..., help="scenario id (flushing, midtown, dtbk)"),
    max_wait_min: float = typer.Option(180.0, help="keep retrying the Overpass mirrors for this long"),
    force: bool = typer.Option(False, help="download again even if a frozen extract exists"),
) -> None:
    """Download and freeze the OSM extract for a scenario's bounding box."""
    from nycemis.config import scenario_config
    from nycemis.network.osm_fetch import fetch

    cfg = scenario_config(scenario)
    if cfg.source != "osm" or cfg.bbox is None:
        raise typer.BadParameter(f"{scenario} is not an OSM scenario")
    meta = fetch(scenario, cfg.bbox, max_wait_min=max_wait_min, force=force)
    typer.echo(json.dumps(meta, indent=2))


@net_app.command("build")
def net_build(
    scenario: str = typer.Option(..., help="scenario id (flushing, midtown, dtbk, smoke)"),
    snapshot: bool = typer.Option(False, help="also open sumo-gui once and save a screenshot (visual check)"),
) -> None:
    """Build, export-check, populate and validate a scenario folder; write network_report.md."""
    from nycemis.config import scenario_config
    from nycemis.network import build as nb
    from nycemis.network import scenario_files as sf
    from nycemis.network.validate import summary, validate

    cfg = scenario_config(scenario)
    nb.build(cfg)
    od = sf.opendrive_check(scenario)
    sf.write_gui_settings(scenario)
    demand = sf.write_default_demand(scenario)
    if demand["unroutable"] != 0:
        raise RuntimeError(f"default demand has {demand['unroutable']} unroutable trips")
    sf.write_sumocfg(scenario)
    smoke = sf.smoke_run(scenario)
    if snapshot:
        typer.echo(f"snapshot: {sf.gui_snapshot(scenario)}")
    result = validate(cfg)
    typer.echo(summary(result))
    typer.echo(f"opendrive export: {'ok' if od['ok'] else 'FAILED'}; default demand: {demand['vehicles_routed']} "
               f"vehicles; smoke run: {smoke['vehicles_inserted']} inserted, {smoke['errors']} errors")
    if not (result.ok and od["ok"]):
        raise typer.Exit(code=1)


demand_app = typer.Typer(no_args_is_help=True, help="fleet, demand generation and calibration")
app.add_typer(demand_app, name="demand")


@demand_app.command("probe-classes")
def demand_probe(scenario: str = typer.Option("smoke", help="network to probe on")) -> None:
    """Run one short simulation per emission class in configs/fleet.yaml; fail if any is rejected."""
    from nycemis.demand.fleet import check_probe, probe_classes
    from nycemis.network.build import net_path

    results = probe_classes(net_path(scenario))
    typer.echo(json.dumps(results, indent=2))
    if check_probe(results):
        raise typer.Exit(code=1)


@demand_app.command("gen")
def demand_gen(
    scenario: str = typer.Option(...),
    level: str = typer.Option(..., help="light, moderate or heavy (from configs/demand_levels.yaml)"),
    seed: int = typer.Option(...),
) -> None:
    """Generate the route file for (scenario, level, seed)."""
    from nycemis.demand.generate import generate, routes_path
    from nycemis.demand.levels import level_density

    summary = generate(scenario, level_density(scenario, level), seed, routes_path(scenario, level, seed), level)
    typer.echo(json.dumps(summary, indent=2))


@app.command("calibrate")
def calibrate_cmd(
    scenario: str = typer.Option(...),
    workers: int = typer.Option(0, help="parallel processes (0 = cores - 1)"),
) -> None:
    """Calibrate light/moderate/heavy demand on the pilot seeds; writes configs/demand_levels.yaml."""
    from nycemis.demand.calibrate import calibrate, clean_calibration_routes, default_workers, summary_table
    from nycemis.network import scenario_files as sf

    entry = calibrate(scenario, workers or default_workers())
    clean_calibration_routes(scenario)
    typer.echo(summary_table(entry))
    typer.echo(f"default demand: {sf.write_default_demand(scenario)['source']}")
    sf.write_sumocfg(scenario)


sim_app = typer.Typer(no_args_is_help=True, help="single simulation runs")
app.add_typer(sim_app, name="sim")


@sim_app.command("run")
def sim_run(spec: str = typer.Option(..., help="path to a RunSpec JSON file")) -> None:
    """Run one simulation from a RunSpec JSON file (used by the experiment executor, one process per run)."""
    from pathlib import Path

    from nycemis.sim.run_spec import RunSpec
    from nycemis.sim.runner import execute, run_dir

    rs = RunSpec.model_validate_json(Path(spec).read_text(encoding="utf-8"))
    metrics = execute(rs)
    typer.echo(json.dumps({"run_id": rs.run_id(), "dir": str(run_dir(rs)), "valid": metrics["valid"],
                           "total_nox_g": metrics["total_nox_g"], "wall_s": metrics["wall_s"]}))


exp_app = typer.Typer(no_args_is_help=True, help="plan, run, check and verify experiments")
app.add_typer(exp_app, name="experiment")


@exp_app.command("plan")
def exp_plan(exp: str = typer.Option(..., "--exp")) -> None:
    """Generate the demand and write results/runs/<exp>/plan.json."""
    from nycemis.experiments.plan import plan

    specs = plan(exp)
    typer.echo(f"{exp}: {len(specs)} runs planned")


@exp_app.command("run")
def exp_run(exp: str = typer.Option(..., "--exp"), workers: int = typer.Option(0),
            controllers: str = typer.Option("", help="comma-separated controllers to run in this pass")) -> None:
    """Run every planned run that is not DONE (resumable)."""
    from nycemis.experiments.execute import run_experiment

    only = {c.strip() for c in controllers.split(",") if c.strip()} or None
    typer.echo(json.dumps(run_experiment(exp, workers or None, controllers=only)))


@exp_app.command("status")
def exp_status(exp: str = typer.Option(..., "--exp")) -> None:
    """Count DONE runs."""
    from nycemis.experiments.plan import exp_dir, load_plan

    doc = load_plan(exp)
    done = sum((exp_dir(exp) / r["run_id"] / "DONE").is_file() for r in doc["runs"])
    typer.echo(f"{exp}: {done}/{len(doc['runs'])} DONE")


@exp_app.command("verify")
def exp_verify(exp: str = typer.Option(..., "--exp")) -> None:
    """Fail unless every planned run is DONE or documented-failed and pairing holds."""
    from nycemis.experiments.verify import verify

    res = verify(exp)
    typer.echo(json.dumps(res, indent=2))
    if not res["ok"]:
        raise typer.Exit(code=1)


@app.command("export-legacy-compact")
def export_legacy_compact_cmd(scenario: str = typer.Option("flushing")) -> None:
    """Write the memory-mapped copy of the legacy RF that legacy_ml runs load (identical predictions)."""
    from nycemis.models.registry import export_legacy_compact

    typer.echo(json.dumps(export_legacy_compact(scenario), indent=2))


@app.command("train-legacy")
def train_legacy(scenario: str = typer.Option("flushing")) -> None:
    """Train and test the legacy RF (C5) on the legacy_train records; writes models/<scenario>/legacy_rf/."""
    from nycemis.models.legacy import train

    typer.echo(json.dumps(train(scenario), indent=2))


@app.command("train")
def train_cmd(
    scenario: str = typer.Option("flushing"), model_id: str = typer.Option("gbm_v1"),
    exp: str = typer.Option("dataset", "--exp"), sample_frac: float = typer.Option(0.10),
    trials: int = typer.Option(30), n_jobs: int = typer.Option(-1),
) -> None:
    """Fit, tune (validation seeds) and freeze the forecaster; evaluate it on validation rows; write its card."""
    from nycemis.models.card import write_card
    from nycemis.models.evaluate import evaluate
    from nycemis.models.registry import load_forecaster
    from nycemis.models.train import freeze, load_windows

    manifest = freeze(scenario, model_id, [exp], sample_frac, trials, n_jobs=n_jobs)
    s = __import__("nycemis.config", fromlist=["base_config"]).base_config().seeds
    train = load_windows([exp], set(s.train_seeds()), sample_frac, 1)
    val = load_windows([exp], set(s.validation_seeds()), sample_frac, 2).reset_index(drop=True)
    ev = evaluate(load_forecaster(scenario, model_id), val, train)
    typer.echo(f"wrote {write_card(scenario, model_id, manifest, ev, 'validation seeds')}")


@app.command("forecast-test")
def forecast_test(scenario: str = typer.Option("flushing"), model_id: str = typer.Option("gbm_v1"),
                  exp: str = typer.Option("confirmatory", "--exp")) -> None:
    """Held-out forecast evaluation of the frozen model on the test seeds' edge windows (RQ2; DEVIATIONS #20)."""
    from nycemis.models.test_eval import evaluate_on_test

    typer.echo(f"wrote {evaluate_on_test(scenario, model_id, exp)}")


@app.command("select")
def select_cmd(exp: str = typer.Option("validation", "--exp")) -> None:
    """Choose alpha* for eco_reactive and eco_ml and the placebo eta on validation seeds."""
    from nycemis.experiments.select import select

    res = select(exp)
    typer.echo(json.dumps({"alpha_reactive": res["eco_reactive"]["alpha_star"],
                           "alpha_ml": res["eco_ml"]["alpha_star"], "eta": res["random_reroute"]["eta_star"]}))


@app.command("prereg")
def prereg_cmd() -> None:
    """Freeze the confirmatory design (M6): write confirmatory.yaml and the frozen PREREGISTRATION.md."""
    from nycemis.experiments.prereg import freeze

    out = freeze()
    typer.echo(json.dumps({k: out[k] for k in ("alpha_reactive", "alpha_ml", "eta", "model_id", "n",
                                               "analysis_code_sha256", "confirmatory_config", "preregistration")},
                          indent=2))


@app.command("paper")
def paper_cmd(pdf: bool = typer.Option(True, "--pdf/--no-pdf")) -> None:
    """Regenerate paper/macros.tex, the interview FAQ, the one-page research summary and the project page from results
    files; compile the PDF if a TeX engine exists."""
    import os

    from nycemis.analysis.documents import render_faq
    from nycemis.analysis.paper import build_pdf, write_macros
    from nycemis.application import write_application
    from nycemis.paths import repo_root

    typer.echo(f"wrote {write_macros()}")
    typer.echo(f"wrote {render_faq()}")
    for path in write_application():
        typer.echo(f"wrote {path}")
    if pdf:
        # tectonic downloads its TeX bundle on first use; keep it in the gitignored tools/ rather than the user profile
        os.environ.setdefault("TECTONIC_CACHE_DIR", (repo_root() / "tools" / "tectonic-cache").as_posix())
        out = build_pdf()
        if out is None:
            logging.getLogger(__name__).warning("no TeX engine (tools/tectonic.exe, tectonic or latexmk on PATH): "
                                                "the paper stays as .tex (docs/OPEN_ITEMS.md)")
        else:
            typer.echo(f"wrote {out}")


@app.command("verify-all")
def verify_all_cmd(only: str = typer.Option("", help="comma-separated subset of checks")) -> None:
    """Every automated check of docs/SPECIFICATION.md section 9; exits 1 if any fails."""
    from nycemis.verify_all import verify_all

    res = verify_all([s.strip() for s in only.split(",") if s.strip()] or None)
    for name, r in res["checks"].items():
        typer.echo(f"[{'ok' if r['ok'] else 'FAIL'}] {name}\n    " + r["detail"].replace("\n", "\n    "))
    if not res["ok"]:
        raise typer.Exit(code=1)


@app.command("analyze")
def analyze_cmd(exp: str = typer.Option("confirmatory", "--exp"), scenario: str = typer.Option("flushing"),
                model_id: str = typer.Option("gbm_v1")) -> None:
    """Frozen analysis (M7): PC1-PC4 with Holm, exploratory comparisons, spatial side effects, figures, claims."""
    from nycemis.analysis.run_all import run

    for path in run(exp, scenario, model_id):
        typer.echo(f"wrote {path}")


@app.command("analyze-pilot")
def analyze_pilot(exp: str = typer.Option("pilot", "--exp")) -> None:
    """Pilot analysis: variance, power, budget, alpha = 0 sanity, legacy replication; renders the documents."""
    from nycemis.analysis.documents import render_interim_note, render_pilot_report, render_preregistration
    from nycemis.analysis.pilot import analyze
    from nycemis.legacy.audit import run_audit
    from nycemis.legacy.report import render_audit
    from nycemis.paths import results_dir

    res = analyze(exp)
    numbers, _ = run_audit()
    docs = [render_audit(numbers), render_pilot_report(), render_interim_note()]
    # after the freeze, docs/PREREGISTRATION.md is the frozen document: never overwrite it with a draft
    if (results_dir() / "validation" / "prereg_freeze.json").is_file():
        logging.getLogger(__name__).warning("preregistration is frozen: docs/PREREGISTRATION.md left unchanged")
    else:
        docs.append(render_preregistration("draft (M4)"))
    for path in docs:
        typer.echo(f"wrote {path}")
    typer.echo(json.dumps({"n_confirmatory": res["power"]["n_confirmatory"], "sd_used": res["power"]["sd_pct_used"],
                           "wall_clock_hours": res["budget"]["wall_clock_hours"]}, indent=2))


@app.command("legacy-audit")
def legacy_audit() -> None:
    """Extract the legacy files, recompute the audit numbers and render docs/LEGACY_AUDIT.md."""
    from nycemis.legacy.audit import run_audit
    from nycemis.legacy.report import render_audit

    numbers, written = run_audit()
    written.append(render_audit(numbers))
    for path in written:
        typer.echo(f"wrote {path}")
