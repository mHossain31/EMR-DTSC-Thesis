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
