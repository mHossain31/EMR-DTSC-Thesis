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

    entry = calibrate(scenario, workers or default_workers())
    clean_calibration_routes(scenario)
    typer.echo(summary_table(entry))


@app.command("legacy-audit")
def legacy_audit() -> None:
    """Extract the legacy files, recompute the audit numbers and render docs/LEGACY_AUDIT.md."""
    from nycemis.legacy.audit import run_audit
    from nycemis.legacy.report import render_audit

    numbers, written = run_audit()
    written.append(render_audit(numbers))
    for path in written:
        typer.echo(f"wrote {path}")
