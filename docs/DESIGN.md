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

## Demand and fleet (M2)

- **Emission model family: HBEFA 4.2** (`HBEFA4/...`), the default family of SUMO 1.28 (`DEFAULT_VEHTYPE` is
  `HBEFA4/PC_petrol_Euro-4`; docs/SPECIFICATION.md Appendix C names the older default). Class names were read from the installed
  binary and each one is confirmed by a probe run (`python -m nycemis demand probe-classes`; an invalid name is
  rejected). Shares are in `configs/fleet.yaml`; vehicle dimensions and dynamics are SUMO's vClass defaults
  (passenger, delivery, truck).
- **Explicit vehicle types.** Each vehicle's type is drawn once per (scenario, level, seed) with a seeded generator
  and written into the route file, so every controller sees the same fleet; route files are byte-identical when
  regenerated (gzip with mtime 0).
- **Demand** follows the Web Wizard's per-class randomTrips options (fringe factor 5, `departLane="best"`,
  fringe `departSpeed="max"`, `--validate`, `--remove-loops`, via-edge types, class minimum distances; cars also
  `--lanes` and `--allow-fringe.min-length 1000`); groups are generated separately and merged by departure.
- **Calibration response**: speed ratio = sum(duration - timeLoss) / sum(duration) of finished trips departing in
  [900, 3600] s, in static runs, averaged over the pilot seeds; levels are set on its ratio to the near-empty value
  (DEVIATIONS #8).

## Harness (M3)

- **One process per run**: `python -m nycemis sim run --spec <spec.json>`, launched by the experiment executor
  from a thread pool that only waits on subprocesses (timeouts, two retries, resume by `DONE` markers).
- **Run identity**: `RunSpec.run_id()` hashes only result-relevant fields; logging options do not change it, and
  `tests/integration/test_harness.py` shows that logging does not change results.
- **Edge state** is logged in every run through edge subscriptions on the non-internal edges (60 s windows); the
  per-edge tables (`edge_cumulative`, `edge_5min`) come from it. SUMO's `edgeData` emissions output differed from
  it by 1.5% on the smoke grid (attribution at lane boundaries), above the 0.1% the protocol allows, so it is not
  used. Junction (internal) lanes are not attributed to edges; run totals come from tripinfo and include them.
- **Per-vehicle emissions** (reconciliation, the legacy controller's inputs, legacy RF records) come from vehicle
  subscriptions made on departure; the departure step is read with direct getters.
- **Controllers** follow docs/SPECIFICATION.md 4.3; efforts are set on every non-internal edge without begin/end and checked
  after each update; rerouting starts after the first effort update (t = 60 s). Travel time per edge is the
  window-mean L / max(v, v_min), floored at free-flow time, for every effort controller, so alpha = 0 is the same
  objective in C2-C4.
- **C3 smoothing**: EMA weight 0.5 per tick; shrinkage toward an online road-class prior (vehicle-second weighted
  mean of everything observed so far in the run), weight vs / (vs + 30).
- **C1 route changes** are counted by sampling every vehicle's remaining route at each tick; `n_reroutes` is the
  sum of tripinfo `rerouteNo`.
- **C5** (`legacy_ml`): the legacy RF (100 trees, unbounded depth, as the notebook) holds about 2.6 GB resident
  (4 GB committed) per process; the executor runs at most 5 C5 runs at a time (`execution.max_concurrent`) in their
  own pool. On 2026-11-15 an earlier pilot attempt without the limit ran out of commit memory (exit code
  0xC000012D) and those runs were rerun.
- **Long batches** are launched as detached processes (WMI `Win32_Process.Create`) so they survive the end of an
  interactive session; logs are in `results/logs/`.

## Models (M4, M5)

- **Frozen binaries are not committed** (`models/**/*.joblib`): the legacy RF is 556 MB. Each model directory
  commits its `metrics.json`, `model_card.md` and `train_manifest.json` (training runs and data hashes); the binary
  is rebuilt deterministically by `python -m nycemis train-legacy` / `train` (fixed seeds).
- **Legacy RF training data**: 642,472 rows (the legacy data frame's size) drawn at random (seed 42) from the
  per-vehicle-step records of static runs on train seeds 0-1, all three levels.
- **Forecaster**: LightGBM per target (r and d on log1p, v raw), random search of 30 trials with early stopping
  on validation seeds; training rows subsampled uniformly per run (fraction in the manifest).
- **alpha* rule** (fixed before test seeds; `src/nycemis/experiments/select.py`): feasible if mean travel time is
  at most 5% above tt_adaptive's at every level; among feasible alphas, minimise the mean over levels of total NOx
  relative to tt_adaptive. The eta rule matches eco_ml's route-change rate at alpha*_ml.
