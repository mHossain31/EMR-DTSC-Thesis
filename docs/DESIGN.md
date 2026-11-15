# Design notes

Decisions that docs/SPECIFICATION.md leaves to the implementation, and every adjustment to its layout (section 5.1).

## Repository

- **Root folder name.** The repository root is the project folder `EMR-DTSC-THESIS`, not `nyc-emissions-sumo/`.
  The layout under it follows docs/SPECIFICATION.md 5.1 exactly. The name only matters if a remote is added later.
- **Extra modules beyond 5.1.** `src/nycemis/paths.py` (repository paths), `src/nycemis/doctor.py` (the `doctor`
  checks), `src/nycemis/legacy/audit.py` and `src/nycemis/legacy/report.py` (the M0 audit; `replicate.py` follows
  in M4).
- **Legacy extracts.** `legacy/notebook_code.py`, `legacy/notebook_outputs.txt`, `legacy/report_text.md` and
  `legacy/slides_text.md` are generated next to the read-only originals by `python -m nycemis legacy-audit`. The
  full extracted notebook (34 MB) goes to the gitignored `legacy/extracted/`.

## Environment

- **Python 3.12** (3.11 also supported), in `.venv` created with uv; `requirements.lock` is `uv pip freeze` of
  that environment. Plain `pip install -r requirements.lock` reproduces it.
- **SUMO 1.28.0 from PyPI** (`eclipse-sumo`, `libsumo`, `traci`, `sumolib`, `sumo-data`), plus
  `$SUMO_HOME/tools/requirements.txt`. No system install.
- **pyarrow is pinned to 23.x.** libsumo 1.28 is compiled against libarrow 23.00 and warns on import when another
  pyarrow major version is installed. Both load into one process here (libsumo for the simulation, pyarrow for
  parquet output), so the versions are kept matched.
- **libsumo DLL loading on Windows.** libsumo 1.28's `__init__.py` calls `os.add_dll_directory` itself; its
  `simulation` class has no `preloadLibraries` attribute in this version (checked with `dir()`), so nothing extra is
  needed. Recorded in `docs/SUMO_API_NOTES.md`.

## Legacy audit

- Numbers in `docs/LEGACY_AUDIT.md` are computed from the legacy files by code and injected by a renderer; the
  document is regenerated, never hand-edited.
- The hygiene scan (the marker list in `tests/unit/test_hygiene.py`) exempts
  `legacy/`, `docs/SPECIFICATION.md`, `docs/LEGACY_AUDIT.md`, `src/nycemis/legacy/audit.py`, `src/nycemis/legacy/report.py` and
  `results/legacy_audit/`, because those quote the legacy material or the specification. Everything else is scanned.

## Networks (M1)

- **Download.** `osmGet.py` with the Web Wizard's "Highway" road-type category (`--road-types`, the list in
  `src/nycemis/network/osm_fetch.py`), no polygons. osmGet then returns those ways, their nodes and the relations
  they belong to (turn restrictions included). The full, unfiltered bbox query timed out (HTTP 504) on every
  Overpass mirror on 2026-11-15; the filtered query is also what the Web Wizard sends when only roads are wanted.
  Extracts are frozen in `data/osm/` with SHA-256 in `data/MANIFEST.json` and `<scenario>.download_meta.json`.
- **netconvert options** are read at build time from the installed `osmBuild.py` (`DEFAULT_NETCONVERT_OPTS`,
  `vclassRemove["passenger"]`) and checked against the installed `osmWebWizard.py` (typemap
  `osmNetconvert.typ.xml`, `--tls.default-type actuated`, the car-only network choice). The exact command is in
  `data/networks/<s>/network_build.json`.
- **Added to the Web Wizard's options** (docs/SPECIFICATION.md 6.2 requirements): `--keep-edges.components 1` (largest
  weakly connected component) and `--keep-edges.in-geo-boundary <bbox>` (clip to the scenario box; an edge with
  any part inside is kept, so some long fringe edges reach outside).
- **Bounding-box match** is measured as: the network covers the box shrunk by 5% on each side, and at least 90%
  of lane-km (segment midpoints) lies inside the box. Raw extents are reported too.
- **Strong connectivity** is gated at 90% of edges in the largest strongly connected component; the rest are
  reported. Demand generation (`randomTrips.py --validate`) only keeps routable trips.
- **Scenario folders** (`scenarios/<s>/`): net, `gui-settings.xml`, a default route file and `<s>.sumocfg`, all with
  relative paths. The default demand is the Web Wizard's default car demand (12 vehicles per hour per km, fringe
  factor 5, its common randomTrips options, seed 42) until M2 replaces it with the calibrated moderate level.
  The sumocfg also carries the Web Wizard's `--tls.actuated.jam-threshold 30`.
- **GUI colour schemes.** `gui-settings.xml` sets lane scheme 11 ("by NOx emissions") and vehicle scheme 8
  ("by speed") and shows the colour legends. The indices were read from the order of the scheme names in
  `sumo-gui.exe` 1.28; the visual check with a sumo-gui snapshot is in `docs/SUMO_API_NOTES.md`.
