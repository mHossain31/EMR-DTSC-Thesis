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


@app.command("legacy-audit")
def legacy_audit() -> None:
    """Extract the legacy files, recompute the audit numbers and render docs/LEGACY_AUDIT.md."""
    from nycemis.legacy.audit import run_audit
    from nycemis.legacy.report import render_audit

    numbers, written = run_audit()
    written.append(render_audit(numbers))
    for path in written:
        typer.echo(f"wrote {path}")
