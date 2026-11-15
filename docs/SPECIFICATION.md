# Specification: rebuild and complete the SUMO + ML urban-emissions study (New York City), research-grade

## 1. Mission

This repository rebuilds, from scratch and to a research standard, a student project: *"Air Pollution Prediction and Reduction Strategies in Urban Areas using SUMO and Machine Learning"* (NYIT DTSC 870 Project I, Flushing, Queens). The original contained methodological problems (section 3) that make its headline result unreliable. It delivers:

1. **A ready-to-run SUMO setup for New York City**: Flushing, Queens as the primary scenario; Midtown Manhattan and Downtown Brooklyn as secondary scenarios. Each opens in `sumo-gui` and runs headless with one command.
2. **A rigorous, reproducible, pre-registered experiment** that asks whether machine-learning-forecast, emission-aware dynamic rerouting reduces simulated traffic emissions, measured against proper baselines and controls.
3. **Research artifacts** (code, results, figures, a technical report, a claims ledger, a one-page summary) that the author will use in graduate applications (deadlines in December 2026).
4. **Optional, only after the core is finished (milestone M10):** a CARLA 3D live-visualization layer driven by the same SUMO network and trajectories. It is a demonstration layer only; SUMO stays the sole source of traffic dynamics and emissions, and no result or claim may rely on CARLA output.

**Definition of success.** Success is a *valid, falsifiable, honestly reported answer* to well-posed questions, in whichever direction the data point. A small or null effect, honestly measured, is a successful outcome. An inflated, unverified, or placeholder-based effect is a failure. Never optimize for a large percentage.

---

## 2. Non-negotiable principles

- **P1 Honesty and provenance.** Never fabricate numbers, citations, results, or file contents. No placeholder values anywhere (the original notebook contained "replace with actual values" cells; this must not recur). Every number in any report traces to a results file produced by code in this repo. Numbers in the paper and summaries are injected programmatically (LaTeX macros / templating), never typed by hand.
- **P2 Matched protocol.** Any compared conditions share identical network, demand (byte-identical route files), SUMO seed, fleet, emission model, and stopping rule (run until all trips complete). No comparison may differ in simulation horizon.
- **P3 Baselines and controls.** No causal claim without the required baselines/placebos in section 4.3.
- **P4 No leakage.** Train/validation/test splits are by *run (seed)*, never by row. Features are strictly causal (use only information available at decision time). Test seeds are not touched until the freeze in M6.
- **P5 Pre-registration.** The analysis plan, α-selection rule, model identity, seed lists, and analysis code are frozen by git tag before confirmatory runs. Any later deviation is written to `docs/DEVIATIONS.md` with a reason.
- **P6 Reproducibility.** Pinned dependencies; seeded everything; one command per stage; portable relative paths (no `D:\...`); works on Windows, macOS, Linux. Use `pathlib`; no bash-only constructs in the primary workflow (the primary entry point is a Python CLI, `python -m nycemis ...`; a `Makefile` is optional convenience).
- **P7 Verify, don't assume.** Before using any SUMO command-line option, tool, or TraCI function, verify it against the *installed* version (`--help`, `help(...)`, bundled docs, official docs) and record it in `docs/SUMO_API_NOTES.md` together with a passing "API contract" test. Never invent flags. If unsure, test on the toy network.
- **P8 No silent fallbacks.** Every fallback logs a WARNING and is recorded in `docs/DEVIATIONS.md`. No bare `except`, no swallowed errors, no `try/except: pass`.
- **P9 Completeness.** Every planned run is `DONE` or explicitly failed with a documented root cause. The final tree contains no `TODO`, `FIXME`, `XXX`, `placeholder`, `replace with`, or `lorem`. `docs/OPEN_ITEMS.md` is empty or contains only items labeled out-of-scope-by-design (or, for the paper build only, environment-limited, see M9).
- **P10 Units.** Units are explicit in names/columns (`nox_mg`, `co2_g`, `tt_s`, `vkm`). Never mix mg and g. Unit-tested.
- **P11 Scope control.** Tier 1 (milestones M0-M7 and M9 in section 10) is mandatory and finishes first. Tier 2 (M8) starts only after the M7 gate passes. The optional CARLA layer (M10) is Tier 3: it starts only after G7 and the go/no-go check in 10.1. Do not add features outside this specification without recording them in `docs/DEVIATIONS.md`.
- **P12 Attribution.** The original project was co-authored by Mohammed Y. Hossain (team leader) and Billy M. Kyaw, supervised by Prof. X. Huang (NYIT). Credit them in `README.md` and the paper's acknowledgments. Include the OpenStreetMap attribution ("Contains data © OpenStreetMap contributors, ODbL") in `NOTICE.md`, README, and paper.

---

## 3. Legacy inputs and mandatory audit

### 3.1 Files
Locate the three legacy files (search the working directory; if absent, stop and ask). Copy them, read-only, to `legacy/`. Extract the notebook code to `legacy/notebook_code.py` (strip outputs; the `.ipynb` is ~34 MB because of embedded outputs). Extract PDF text and verify completeness against page counts (48 and 31 pages). Never modify `legacy/`.

### 3.2 What the legacy project did (my reading, verify it yourself)
- SUMO network of Flushing built with OSM Web Wizard; TraCI control; single run.
- Emissions per vehicle-step (CO2, CO, NOx, HC, PMx, x, y) written to `emissions.xml` and parsed into a DataFrame. A min-max normalized copy (`normalized_df`, a manual formula in notebook cell 12, no `MinMaxScaler`) is created, but the model cells appear to use the raw `df` (verify which frame the reported MSEs refer to; MSEs near 1e-4 suggest either a normalized target or a nearly deterministic relation between the pollutants).
- Eight models compared (RF, XGBoost, GB, LinearRegression, Ridge, KNN, ElasticNet, MLP). Target: **NOx**; features: **CO2, CO, HC, PMx** (the model comparison also used X, Y), **random 80/20 row split**. Reported test MSE: RF 0.000105, XGBoost 0.000533, NN 0.016439 (units unstated in the report).
- "Rerouting": for every vehicle at every step, predict NOx with the RF/XGB; if predicted NOx > 1.88, call `traci.simulation.findRoute(currentEdge, lastRouteEdge)` with default routing and `traci.vehicle.setRoute`. Controlled runs loop `while ... and step < 1000`.
- "Percentage drop" = (sum of all rows in baseline emissions XML, minus sum of all rows in controlled-run XML) / baseline sum, per pollutant. Reported drops: RF 72.0 / 64.0 / 71.5 / 65.3 / 70.4 % and XGBoost 73.7 / 70.2 / 73.4 / 70.7 / 72.8 % for CO2 / CO / NOx / HC / PMx.
- The report claims multiple runs were averaged and settings were held constant.

### 3.3 Suspected defects (hypotheses to confirm or refute from the files, not conclusions)
- **D1 Unmatched horizon.** The controlled run is stopped at 1000 steps; the baseline XML may cover a much longer run. Summing all rows then yields a spurious "drop" (roughly one minus the ratio of horizons). The reported 64-74% is of the magnitude such a mismatch could produce; confirm or refute with data.
- **D2 No-op intervention.** Default `findRoute` takes edge travel times from the vehicle's own data, global weight files, or global TraCI weights if any exist, and otherwise falls back to free-flow times (length / allowed speed). The original routes were likely generated with the same free-flow metric, so "rerouting" may often reproduce the same route. Measure how many route changes actually occur.
- **D3 No baselines or controls.** No no-reroute control at matched horizon, no random-reroute placebo, no SUMO-native adaptive-routing baseline.
- **D4 Circular prediction task.** NOx is predicted from other pollutants emitted by the same SUMO emission model at the same instant; SUMO also reports NOx directly (`getNOxEmission`). The tiny MSE therefore says little about hotspot forecasting. Random row splits also leak across time within a vehicle.
- **D5 Single run, no uncertainty**; "averaged multiple runs" is not evidenced in the notebook.
- **D6 Unclear threshold.** 1.88 is labeled "bpm"/"ppm" for NYC (a concentration-like unit), but the models predict SUMO's per-vehicle emission rate (mg/s); the unit relationship and the origin of 1.88 are unexplained. Determine which quantity was actually compared to the threshold.
- **D7 Placeholders.** Notebook cells hard-code MSE values with "replace with actual values", and the "real map" cell uses invented example drops (15, 25). Hard-coded `D:\` paths. The data-collection loop in the first simulation cell (notebook cell 2) contains no `step += 1`, so it cannot end by its own counter (confirm what stopped it). That cell also logs only CO2 via TraCI; the other pollutants come from `emissions_data.xml`.
- **D8 References.** Several cited papers could not be located and are inconsistently cited between slides and report (e.g., "Dong & Javid 2022" vs. separate "Dong 2021" and "Javid 2022"). One plausible match for the legacy "Dong 2021" is Du, Chen, Dong et al., arXiv:2110.05532 (a dynamic-rerouting paper; Dong is a co-author): compare it with the legacy bibliography entry before assuming anything. Do not reuse any legacy reference unless verified from a primary source.

### 3.4 Deliverable of M0: `docs/LEGACY_AUDIT.md`
A table: *claim -> evidence (file/line/page) -> status (confirmed / refuted / unverifiable) -> how the new design addresses it*. If `legacy/sumo_files/` exists, compute directly: number of timesteps and records and last timestamp in each emissions XML, and whether horizons differ. Later (M3/M4) the audit is completed with the legacy-protocol replication in 7.4.

---

## 4. Research design

### 4.1 Research questions
- **RQ1 (measurement validity).** How much of a legacy-style reported emission reduction is explained by protocol artifacts (unmatched horizon, non-informative intervention) rather than a real effect?
- **RQ2 (forecasting).** Can edge-level emission rate and emission hotspots be forecast 60 s ahead from sensor-realistic traffic state, better than persistence and historical baselines, on held-out runs and (Tier 2) held-out NYC neighborhoods?
- **RQ3 (control).** Does emission-aware rerouting driven by those forecasts reduce network NOx (and CO2) compared with (a) no rerouting, (b) travel-time rerouting, (c) a random-rerouting placebo, and at what cost in travel time and distance?
- **RQ4 (value of prediction; Tier 2).** How close does forecast-driven control come to control using true measurements, and how does benefit degrade as measurement/prediction error grows?
- **RQ5 (side effects).** Does emission-aware rerouting displace emissions onto lower-class (residential/service) streets or raise peak edge emissions?

### 4.2 Pre-registered confirmatory comparisons (primary scenario: Flushing; each at three demand levels)
All comparisons are paired by seed (test types under "Multiplicity" below). Practical significance threshold (SESOI) = **2%** of the baseline's total NOx.
- **PC1 (audit)**: `legacy_ml` vs `static`: equivalence within ±2% (hypothesis: near zero under a matched protocol; report whatever is found).
- **PC2**: `eco_ml` vs `static`: difference in total NOx.
- **PC3**: `eco_ml` vs `tt_adaptive`: difference in total NOx.
- **PC4**: `eco_ml` vs `eco_reactive`: equivalence within ±2% (does forecasting add value over measurement?).

**Multiplicity:** all 12 confirmatory tests (PC1-PC4 x 3 demand levels) form one Holm family at familywise α = 0.05. PC2 and PC3 are superiority tests (two-sided paired Wilcoxon signed-rank on per-seed Δ%). PC1 and PC4 are equivalence tests by TOST against ±2% (two one-sided paired Wilcoxon tests, on Δ%+2 and Δ%-2; the test's p-value is the larger of the two one-sided p-values). Report unadjusted and Holm-adjusted p-values. Everything else is labeled *exploratory* in all outputs. The write-up must state the outcome of every PC, including nulls.

### 4.3 Conditions (controllers)
| ID | Name | Mechanism | Purpose |
|---|---|---|---|
| C0 | `static` | Initial free-flow-shortest explicit routes; no rerouting | Reference |
| C1 | `tt_adaptive` | SUMO-native rerouting devices (travel-time based), period matched to the 60 s control tick (verify options) | Standard congestion-aware baseline |
| C2 | `random_reroute` | Same cadence/compliance as C4; effort = travel time x seeded noise U(1, 1+η), η chosen so route-change rate matches C4's on validation seeds | Placebo: "any rerouting" |
| C3 | `eco_reactive` | Effort from *measured* current per-vehicle NOx traversal cost | Measurement-based eco-routing |
| C4 | `eco_ml` | Same effort form, cost from the *frozen ML forecast* (traffic-only features) | Proposed method |
| C5 | `legacy_ml` | Faithful replication of the legacy rule (7.4) under the proper protocol | Audit (RQ1) |
| C6* | `eco_noisy_oracle` | C3 with lognormal multiplicative noise σ in {0.1, 0.25, 0.5} | RQ4 curve |
| C7* | `eco_ml_shuffled` | C4 with predictions permuted across edges each tick | Negative control (information content) |
| C8* | `eco_ml_emislag` | C4 with emission-lag features (F2) | Feature ablation |

(* = Tier 2.)

**Routing cost (C2-C4).** At every control tick *t* (60 s), for every non-internal edge *e*:
- `tau_e`: current travel-time estimate (verify the semantics of `edge.getTraveltime`; floor at free-flow time).
- `m_e`: per-vehicle NOx cost of traversing *e* in mg = `r_e * L_e / max(v_e, v_min)`, where `r_e` = NOx rate per vehicle-second (mg/veh-s), `v_e` = mean speed, `L_e` = length, `v_min = 1.0 m/s`. C3 measures `r_e`, `v_e` over the last window and smooths them (EMA, then shrinkage toward a road-class prior with weight `w = vs/(vs+30)`, `vs` = vehicle-seconds observed). C4 uses model forecasts `r_hat_e`, `v_hat_e` for the next window.
- `effort_e = tau_bar * [ (1-α) * tau_e/tau_bar + α * m_e/m_bar ]`, with `tau_bar`, `m_bar` the means over non-internal edges at that tick. α in [0,1].
- Apply with `traci.edge.setEffort` for **all** non-internal edges, then reroute compliant vehicles with `traci.vehicle.rerouteEffort`. Do **not** attach rerouting devices to vehicles in C2-C4 (devices use aggregated routing and ignore `setEffort`; confirmed in a SUMO user-list reply by Jakob Erdmann). Effort pitfalls to guard and test (record in `SUMO_API_NOTES.md`): (i) the default effort is 0, so any edge left unset looks free and attracts traffic: after every update assert `traci.edge.getEffort(e, t) >= 0` for all non-internal edges (it returns -1 when unset); (ii) call `setEffort` without begin/end so each value is valid for the whole simulation (a time-windowed value leaves later arrival times unset), and verify that repeated calls overwrite rather than accumulate; (iii) toy-network tests: a very large effort on an edge of a vehicle's route makes `rerouteEffort` avoid it, and a vehicle with a rerouting device ignores the same effort.
- Per-vehicle reroute period 60 s (staggered deterministically), skip vehicles on their last two edges or on internal edges. Primary compliance = 100% (a full-compliance upper bound); sensitivity at 10/25/50% in Tier 2 with the *same* compliant subset (deterministic hash of vehicle id, seed, p) across controllers.
- **Sanity gate:** `eco_reactive` with α = 0 must reproduce `tt_adaptive` mean travel time within 5% (mechanisms differ, objective is the same). If not, investigate; proceed only with a documented explanation (for example, different smoothing of travel times) and a recorded deviation.

### 4.4 Matched simulation protocol
- Step length 1 s (explicit). Departures in [0, 3600] s. Run until all vehicles have arrived; hard cap 14,400 s. `--time-to-teleport` set explicitly (document value). Collisions: `warn` and counted.
- **Valid run** = completion >= 99.5% of route-file vehicles AND teleports <= 0.5% of trips AND no crash/timeout. Confirmatory analysis uses pairs where both runs are valid; sensitivity analysis uses all pairs. Report invalid-run counts per condition.
- Same route file per (scenario, level, seed) across all conditions (assert by SHA-256 in the manifest).
- `--device.emissions.probability 1` and `--tripinfo-output` (per-trip emissions in mg; tripinfo is written on arrival, so also enable `--tripinfo-output.write-unfinished` and flag any unfinished vehicles).
- Do **not** use `--emission-output` (unaggregated, enormous).

### 4.5 Metrics (units explicit)
**Primary:** `total_nox_g` = sum over all trips of tripinfo `NOx_abs` (mg) / 1000.
**Secondary:** `total_co2_kg`; `nox_mg_per_vkm`; `mean_tt_s`, `p95_tt_s`, `mean_timeloss_s`, `mean_wait_s`; `vkm_total` (sum of routeLength); `mean_depart_delay_s`; `n_reroutes`, `route_change_rate` (reroute calls that actually changed the route / all reroute calls); `ctl_ms_per_tick` (controller wall-clock); `teleports`, `collisions`, `completion_rate`.
**Spatial / side-effect (RQ5):** NOx share by OSM road class (motorway/trunk, primary/secondary, tertiary, residential/service); peak (p99) 5-min edge NOx density; Gini coefficient of per-edge cumulative NOx; per-edge cumulative NOx table for maps.
**Pareto:** (`total_nox_g` change, `mean_tt_s` change) across α grid.
**Reconciliation check:** the sum of per-trip tripinfo NOx must equal the sum of per-step network NOx accumulated in-process (SUMO's vehicle and edge emission getters return rates in mg/s, so multiply by the step length; treat the -2^30 "unavailable" value as an error) within 0.1% on the smoke scenario (unit test) and on all pilot runs, and within 0.5% on a seeded random 5% audit sample of production runs. Document any internal-edge discrepancy. Per-step accumulation on every production run is optional if profiling shows it is too costly.

### 4.6 Seeds and splits (disjoint, asserted by test)
| Role | Seeds | Use |
|---|---|---|
| Pilot | 9000-9004 | Calibration, runtime, power analysis. Never reused. |
| Train | 0-23 | Predictor training data |
| Validation | 100-111 | Hyperparameters, α* selection |
| Test (confirmatory) | 200-(200+n-1) | n = max(30, ceil(1.2 * n_power)) capped at 60 |
| Tier 2 | 300+ | Other scenarios and sensitivities |
| Demo (M10) | 9100-9199 | Visualization runs only; never analyzed |

`n_power`: from the pilot's SD of paired percent differences, for 80% power to detect the 2% SESOI (superiority) and to establish equivalence within ±2% (TOST), at the most stringent Holm threshold (α = 0.05/12). Use the larger of the two requirements at the noisiest demand level. Record the calculation in the preregistration. The floor of 30 may drop to 20 only through the scope-cut ladder in section 8, and only if the recomputed power at n = 20 is at least 80%.

### 4.7 Statistical analysis plan
Per seed compute percent change `Δ% = 100 * (Y_cond - Y_ref) / Y_ref`. Report mean and median Δ%, 95% BCa bootstrap CI (10,000 resamples, fixed seed), the paired Wilcoxon signed-rank p-value (two-sided), the Holm-adjusted p-value (family defined in 4.2), and d_z. Equivalence (PC1, PC4): declare equivalence only if the Holm-adjusted TOST p-value is below 0.05 (equivalently, the matching (1 - 2·α_adj) interval lies inside ±2%); also show the unadjusted 90% CI. Forecast metrics use cluster bootstrap over runs. Required figures: paired slope plots, forest plot of all comparisons, Pareto plot, forecast-skill plots, spatial emission maps (baseline vs. eco_ml difference), road-class share bars. No figure or table is edited by hand.

### 4.8 Tier 2 (only after the M7 gate)
Second and third scenarios; leave-one-network-out forecast transfer and controller transfer; compliance sweep {10, 25, 50, 100}%; forecast horizons {60, 180, 300} s; C6-C8; MLP and optional graph-structured model.

### 4.9 Threats to validity (must appear in the report and `docs/LIMITATIONS.md`)
Synthetic origin-destination demand (not calibrated to NYC counts); HBEFA and PHEMlight emission factors are largely based on European fleets and test cycles; no weather, no atmospheric dispersion, so emissions are not concentrations or exposure; OSM-derived signals and geometry are imperfect; no pedestrians/transit; fixed driver compliance model; single-hour demand profile; simulator not validated against field measurements. Never claim health or air-quality improvements, only *simulated tailpipe emission totals*.

---

## 5. Architecture

### 5.1 Repository layout (create exactly; adjust only with a note in `docs/DESIGN.md`)
```
nyc-emissions-sumo/
  README.md  STATUS.md  NOTICE.md  LICENSE(MIT)  pyproject.toml  requirements.lock  .python-version
  configs/            base.yaml  fleet.yaml  demand_levels.yaml  controllers.yaml  models.yaml
                      scenarios/{flushing,midtown,dtbk}.yaml   experiments/{smoke,pilot,confirmatory,tier2}.yaml
  docs/               PLAN.md  DESIGN.md  LEGACY_AUDIT.md  PREREGISTRATION.md  DEVIATIONS.md  OPEN_ITEMS.md
                      LIMITATIONS.md  SUMO_API_NOTES.md  CITATION_LEDGER.md  CLAIMS.md  RESEARCH_AGENDA.md  CARLA_NOTES.md (optional)
  legacy/             (read-only copies + extracted code/text)
  data/               osm/ networks/ demand/ (large files gitignored; MANIFEST.json with SHA-256 committed)
  scenarios/          flushing/ midtown/ dtbk/   (net, vtypes, .sumocfg, gui-settings.xml; relative paths only)
  src/nycemis/
    cli.py  config.py  env.py (SUMO discovery, libsumo/TraCI adapter, versions)
    network/ (osm_fetch.py build.py validate.py)   demand/ (generate.py calibrate.py fleet.py)
    sim/ (runner.py run_spec.py metrics.py logger.py)   controllers/ (base.py static.py tt_adaptive.py random_reroute.py eco_reactive.py eco_ml.py legacy_ml.py + tier-2 files)
    features/ (builder.py)   models/ (baselines.py gbm.py train.py evaluate.py registry.py)
    experiments/ (plan.py execute.py manifest.py verify.py power.py)
    analysis/ (stats.py figures.py tables.py maps.py claims.py)   legacy/ (replicate.py)
    carla_bridge/ (optional, M10: export_xodr.py align.py replay.py live.py)
  tests/              unit/ integration/ regression/
  results/            (raw per-run outputs gitignored; summary parquet/json committed)
  models/             frozen model artifacts
  paper/              main.tex  refs.bib  figures/ tables/ macros.tex  (all generated from results)
  application/        interim_note.md  research_summary_1page.md  claims_ledger.md  interview_faq.md  project_page.md  demo/ (optional, M10)
  scripts/            (thin wrappers only)   notebooks/ (exploration only; never source of truth)
```

### 5.2 CLI (all stages; each idempotent and resumable)
`python -m nycemis doctor | setup | legacy-audit | net build --scenario S | demand gen --scenario S --level L | calibrate --scenario S | sim run --spec JSON | data build | train | experiment plan|run|status|verify --exp E | analyze --exp E | figures | paper | verify-all | gui --scenario S --level L --seed N --controller C | carla export-xodr|align|replay|live (optional, M10)`.
`doctor` checks: Python, OS, CPU cores, free disk, SUMO version, `netconvert`/`sumo`/tools present, libsumo import, TeX engine, Overpass reachability, git state, and (informational only) whether a CARLA-capable machine is present: OS, NVIDIA GPU, `CARLA_ROOT`. `verify-all` runs section 9 end to end.

### 5.3 Config and run identity
YAML configs validated with pydantic v2. A `RunSpec` (scenario, level, seed, controller, params, protocol_version) hashes to a 12-char `run_id`. Each run directory holds `run.json` (resolved config, git commit, package versions, SUMO version, OS, timings), parsed parquet outputs, a log, and a `DONE` marker written last via atomic rename. Raw XML is deleted after parsing unless `--keep-raw`. Workers use the `spawn` start method (Windows/macOS safe), each in its own output directory; libsumo requires one simulation per process, so use multiprocessing, not threads.

### 5.4 Controller interface
`Controller.reset(ctx)`, `Controller.on_tick(t, sim) -> ControlLog`, plus `Controller.params` for the manifest. Controllers never read the filesystem during a run (preload models/priors). All stochastic choices use a `numpy.random.Generator` seeded from (run seed, controller name).

### 5.5 Data contracts (parquet; schema-validated)
- `run_metrics`: one row per run, all section 4.5 metrics, validity flags.
- `trip_metrics`: one row per trip (id, vtype, depart, duration, routeLength, timeLoss, waiting, nox_mg, co2_mg, ...).
- `edge_window` (dataset runs only): one row per (run, tick, edge) with features, targets, and masks.
- `edge_cumulative`: one row per (run, edge): cumulative NOx/CO2, vehicle-seconds, road class.
- `tick_log`: controller diagnostics per tick.
Write explicit dtypes; validate ranges, nulls, units with a schema check run by `verify`.

---

## 6. SUMO and NYC setup

### 6.1 Environment
Create `.venv`. Install the latest stable `eclipse-sumo`, `traci`, `sumolib`, `libsumo` from PyPI (these wheels support Windows, macOS, and Linux), then `pip install -r $SUMO_HOME/tools/requirements.txt`. Get `SUMO_HOME` in code via `import sumo; sumo.SUMO_HOME` (discovered in code, not from a manually exported variable). Pin exact versions into `requirements.lock` and `run.json`. Python 3.11 or 3.12. Other dependencies: numpy, pandas, pyarrow, scipy, scikit-learn, lightgbm, statsmodels, matplotlib, networkx, pyyaml, pydantic, typer, tqdm, joblib, lxml, pytest, pytest-cov, ruff, nbformat, pypdf (or pdfplumber). If a wheel is unavailable for the platform, fall back to Homebrew/installer, A system package is a separate decision.
Use `libsumo` for speed with an adapter that can fall back to TraCI sockets with the same interface (record which was used). libsumo limits (per the SUMO docs): parallel runs need multiprocessing (one simulation per process); `traci.init/connect` are unsupported (use `start`); and GUI support is experimental (not working on Windows), so the `gui` command must launch the `sumo-gui` binary through TraCI, never libsumo. A unit test must show both backends give identical summary metrics on the smoke scenario. On Windows, libraries may need preloading from SUMO 1.16 (wrapped as `Simulation.preloadLibraries()` since 1.24; verify on the installed version); if libsumo still fails to import, use TraCI and log it.
SUMO is documented to give identical results for the same version, arguments and inputs, with known exceptions (Proj and `log` differences across platforms or versions). To stay safe, compare conditions only within one platform and SUMO version, record both, and keep routing single-threaded (no `--device.rerouting.threads`, no other multi-threaded options).

### 6.2 Network build (replicates what OSM Web Wizard does, headless and scripted)
1. Download OSM for a bounding box with `osmGet.py` (`--bbox` takes west,south,east,north; check `--help` for the output-name option, and use `--tiles` if a request is too large). Retry with backoff; fall back to alternative Overpass mirrors; as a last resort cut the box from a Geofabrik New York extract with `osmium` (a separate install decision). Store the extract as `data/osm/<scenario>.osm.xml.gz` with SHA-256 and `download_meta.json` (UTC timestamp, endpoint, bbox, tool versions). The OSM extract is frozen in the repo manifest so results do not drift as OSM changes.
2. Build the network with `osmBuild.py` or `netconvert`, using the typemaps in `$SUMO_HOME/data/typemap/`. **Read the installed `osmWebWizard.py` and copy its exact netconvert options and typemap choices** (do not guess; the Web Wizard only applies recommended options, and doing the steps by hand gives the same results). Keep roads usable by passenger cars, delivery vans, and trucks (osmBuild.py `--vehicle-classes` accepts values such as `road` and `passenger`; choose to match the Web Wizard's vehicle-class handling and record it); remove pedestrian/bicycle/rail-only infrastructure; keep the largest connected component (verify the option name); keep guessed traffic lights, with the signal type that the Web Wizard's options set (read it, record it). Save the exact options to `network_build.json`.
3. Validate (`validate.py`): bounding-box match; edge count within [1,500, 20,000] (else adjust the bbox and record why); lane-km; traffic-light count; strong connectivity of the retained component; share of dead-end edges; speed-limit and road-class distributions; no zero-length edges. Emit `network_report.md` and `network_map.png` (sumolib + matplotlib).
4. Headless smoke: `sumo -c scenarios/<s>/<s>.sumocfg` for 300 s with no errors, then confirm `sumo-gui` opens it (document the command; GUI cannot be automated).
5. OpenDRIVE export check (needed only for the optional CARLA layer, but cheap to do now): `netconvert -s <net.xml> --opendrive-output <file>.xodr --output.original-names`, also trying `--junctions.scurve-stretch 1.0`. It must succeed; record any warnings in `network_report.md`. Never alter the experimental network to make this pass.

### 6.3 Scenarios (initial bounding boxes as `W,S,E,N`; adjust only per the validation rule and record)
| ID | Area | Initial bbox | Role |
|---|---|---|---|
| `flushing` | Downtown Flushing, Queens (may include parts of the Van Wyck / Whitestone expressways; report which road classes are present) | `-73.845,40.745,-73.805,40.775` | Primary (continuity with the original) |
| `midtown` | Midtown Manhattan (dense one-way grid) | `-73.995,40.745,-73.965,40.765` | Tier 2 |
| `dtbk` | Downtown Brooklyn | `-74.005,40.685,-73.975,40.705` | Tier 2 |

All three networks are *built and validated in M1* (so the "NYC SUMO config map" is ready to go), even though only Flushing runs in Tier 1 experiments. If the Flushing box is too heavy to meet runtime budgets, shrink it (recorded).

### 6.4 Fleet and emission classes
`configs/fleet.yaml` defines a `vTypeDistribution`: passenger cars (about 85%, mixed petrol/diesel Euro classes), light commercial vans (about 10%), heavy trucks (about 5%), each mapped to an emission class. SUMO's documented default is `HBEFA3/PC_G_EU4`. **Do not guess class names**: enumerate the classes available in the installed version (model description pages and a probe run per candidate), choose a documented set, and record the choice in `docs/DESIGN.md`. State clearly in `LIMITATIONS.md` that these are European-based emission models.

### 6.5 Demand and calibration
- Generate trips with `randomTrips.py` (fixed `--seed`; `-b 0 -e 3600`; `--fringe-factor`, `--min-distance`, lane-count (`-L`) and `--speed-exponent` weighting; `--validate`; fleet via vTypes; departure attributes via `--trip-attributes` / `--fringe-start-attributes`, mirroring those that `osmWebWizard.py` passes (read it and record the choice)), then `duarouter` to explicit routes. Zero unroutable trips allowed. One route file per (scenario, level, seed); write `demand_summary.json` (trips, mean length, fringe share, hash).
- **Calibrate three demand levels** (light / moderate / heavy) on pilot seeds by bisection on insertion period (or scale): choose levels so that the demand-weighted mean-speed ratio (mean speed over mean speed limit, loaded period) hits explicit targets (record them, e.g., about 0.8 / 0.6 / 0.45), teleports stay <= 0.5% of trips, completion >= 99.5%, and the heavy level is congested but not gridlocked. Save `configs/demand_levels.yaml` with evidence plots. Calibration seeds never overlap analysis seeds.

### 6.6 Simulation configuration and outputs
`scenarios/<s>/<s>.sumocfg` plus `vtypes.add.xml`, using only relative paths. Options set explicitly: step length, teleport time, collision action, `--no-step-log`, seed, output files (tripinfo with emissions device, summary or `--statistic-output`). Per-tick features and controller inputs, and the per-step network totals used for reconciliation, come from the in-process logger (not XML). For per-edge cumulative emissions and 5-minute edge series in evaluation runs, an alternative is to use SUMO `edgeData type="emissions"` output (C++ aggregation, `excludeEmpty`, period 300 s), parsed to parquet and then deleted, provided a test shows it agrees with the in-process logger within 0.1% on the smoke scenario; choose whichever meets the runtime budget and document it. Before launching a batch, compute and print the expected disk use and abort if it exceeds 50% of free space.

### 6.7 "Ready to go" GUI
Provide `scenarios/<s>/gui-settings.xml` coloring edges by NOx emission and vehicles by speed (verify attribute names in the installed version), and `python -m nycemis gui ...` to launch `sumo-gui` with a chosen level/seed/controller.

### 6.8 Verified SUMO facts (checked against official docs while drafting this specification; re-verify on the installed version)
See Appendix C for the list and source URLs. In short: tripinfo emissions come from the emissions device (`--device.emissions.probability 1`) in mg; edge/lane emission output exists with `_abs`, `_normed`, `_perVeh` attributes; the edge and vehicle emission getters return rates in mg/s; `rerouteEffort` uses `setEffort`/weight-file efforts, and rerouting-device vehicles ignore efforts; SUMO is deterministic for a given seed (`--seed`), default 23423; default `findRoute` routing depends on device/weights, falling back to free-flow travel times.

---

## 7. Machine-learning pipeline

### 7.1 Prediction tasks (causal, non-circular)
Decision time *t_k* (every 60 s). Window k = [t_k - 60, t_k). Targets are for window k+1 = [t_k, t_k + 60):
- `d_next`: NOx density = NOx mg on edge / (length x lanes) over the window (model `log1p`).
- `r_next`: NOx per vehicle-second (mg/veh-s); masked where vehicle-seconds < 10.
- `v_next`: mean speed (m/s); masked where no vehicles.
Hotspot label: `d_next` above the 95th percentile of non-empty training edge-windows for that scenario (threshold fixed from training data).

### 7.2 Feature sets (computed by one `FeatureBuilder` used in both dataset generation and live control)
- **F1 (primary; sensor-realistic, no emission information):** per edge: mean/max vehicle count, mean speed, speed ratio (to limit), halting count, waiting time, travel-time ratio; lags k-1, k-2; 1-hop upstream and downstream aggregates; static: length, lanes, speed limit, road class, downstream-signal flag, in/out degree; demand-ramp phase.
- **F2 (ablation):** F1 plus lagged emission density and per-vehicle emission rate (k, k-1, k-2).
No feature may use information from window k+1 or later. A "poison test" must inject sentinel values into post-t_k data and show features are unchanged. Sample at every 1 s step unless profiling shows an unacceptable cost; any subsampling rule must be identical in dataset generation and live control, and documented.

### 7.3 Models and protocol
Baselines: persistence, EMA, per-edge historical mean (from training), Ridge. Main: LightGBM (fall back to scikit-learn `HistGradientBoostingRegressor`, logged). Tier 2: MLP, optional graph model. Dataset runs use mixed behavior policies (`static`, `tt_adaptive`, `random_reroute` at the pilot's initial η, and `eco_reactive` with α drawn per run from the α grid) on train seeds so the predictor sees controller-induced traffic states, reducing distribution shift. Hyperparameter random search (30 trials, early stopping) on validation seeds only. Metrics: MAE, RMSE, R², Spearman per target; hotspot PR-AUC, F1 at the frozen threshold, precision@top-1% and top-5% edges per tick; calibration; stratified by demand level and road class; cluster-bootstrap CIs by run. Report skill relative to each baseline.

### 7.4 Legacy-protocol replication (completes the audit; condition C5)
Reproduce the legacy logic as faithfully as the evidence allows: RF (100 trees, `random_state=42`) trained to predict NOx from [CO2, CO, HC, PMx] with a random 80/20 row split, on the same representation (raw or normalized) the notebook actually used; rule "predicted NOx > threshold -> default `findRoute` -> `setRoute`", with no rerouting devices attached (unless the legacy configuration shows otherwise). Express the legacy threshold as a quantile of training NOx (and also run the literal 1.88 in the units the audit establishes), and document why the original value cannot be interpreted. Training data for the legacy RF are per-vehicle-step records (CO2, CO, HC, PMx, NOx, x, y) logged in-process from baseline runs on train seeds 0-1 only. At run time, batch the RF predictions of all vehicles in a step into one call (identical results, much faster) and call `findRoute`/`setRoute` per above-threshold vehicle at each step, as the original did; if that cadence proves too slow in the pilot, record a deviation and the cadence used. Then report: (i) the legacy predictor's score vs. a single-feature monotone baseline and vs. a split-by-run evaluation (triviality and leakage test); (ii) `route_change_rate` (are routes actually changed?); (iii) **the legacy metric** (sum of all records with unmatched horizons, emulated cheaply from per-step cumulative NOx) vs. **the matched metric**, on the same seeds. Report whatever is found.

### 7.5 Freeze and serving
Frozen artifacts in `models/<scenario>/<model_id>/`: `model.joblib`, `features.json`, `metrics.json`, `model_card.md`, `train_manifest.json` (data hashes, seeds, git commit). Tag `model-freeze-v1`. A **shadow-mode test**: run the controller computing but not applying predictions and assert logged features equal the dataset-generation features for the same run (guards against train/serve skew).

---

## 8. Experiment execution

- **Profiles:** `smoke` (3x3 grid from `netgenerate`, 2 seeds, a few minutes, runs in CI), `pilot` (Flushing, pilot seeds), `confirmatory`, `tier2`.
- **Budgeting:** after the pilot, print per-condition median runtime, planned run counts, total core-hours, wall-clock at the chosen worker count (default: cores - 1), and disk. If the estimate exceeds 24 h wall-clock, apply this scope-cut ladder one rung at a time, in order, recording each rung in `docs/DEVIATIONS.md` (and in `PREREGISTRATION.md` when it changes the confirmatory design): (1) drop or shrink Tier 2 (fewer seeds, sensitivity cells, scenarios); (2) α grid 5 -> 3 values {0, 0.5, 1}; (3) training seeds 24 -> 12 and validation seeds 12 -> 8; (4) departure window 3600 s -> 1800 s, or a smaller Flushing box (this needs re-calibration, so decide it at M2/M4, not later); (5) only as a last resort, confirmatory n from 30 down to 20, and only if the recomputed power at n = 20 is at least 80%. Never drop the audit arm (C5), the placebo (C2), or the matched-horizon protocol.
- **Resilience:** per-run timeout (3x pilot median, minimum 10 min), at most 2 retries, resume skips `DONE` runs, atomic writes, `failed_runs.csv` with root causes. `experiment verify` exits non-zero unless every planned run is `DONE` or documented-failed.
- Rough scale (Flushing, Tier 1): dataset about 3 levels x 4 policies x 24 seeds; validation α-sweep about 5 α x 2 controllers x 3 levels x 12 seeds; confirmatory 3 levels x 6 conditions x n seeds. The pilot decides final counts.

---

## 9. Verification (tests and gates)

Automated (`pytest`; run in `verify-all`):
1. **Unit:** config validation; unit conversions; metric parsers on fixtures; stats code against known results (scipy reference values); seed-disjointness; feature builder on a hand-derived toy network.
2. **API contract:** every SUMO option/TraCI call used exists on the installed version and behaves as documented (exercise each on the toy network); recorded in `SUMO_API_NOTES.md`.
3. **Determinism:** the same RunSpec twice gives byte-identical tripinfo-derived metrics; libsumo vs TraCI agree.
4. **Pairing:** route-file hashes identical across conditions for each (scenario, level, seed).
5. **Conservation/reconciliation:** per-trip vs per-step NOx, with the tolerances and sampling of section 4.5.
6. **No leakage:** poison test; split-by-run assertion; test seeds absent from any training/tuning artifact (checked via manifests).
7. **Train/serve parity:** shadow-mode test (7.5).
8. **α = 0 sanity:** `eco_reactive(α=0)` vs `tt_adaptive` travel time within 5%.
9. **Artifact-demonstration test:** a synthetic pair of runs with different horizons produces a spurious reduction under the legacy metric and none under the matched metric.
10. **Hygiene:** `ruff`; the smoke profile also passes when the project lives in a path containing spaces; no absolute paths; no TODO/FIXME/placeholder strings; every paper number comes from a macro; every bibliography entry is in `CITATION_LEDGER.md` with a verified URL/DOI and the claim it supports.
11. **Adversarial review:** before M7 closes, run an independent review to audit code, protocol, and results against sections 2-4 and try to falsify the headline claim. Fix or document every finding in `docs/DEVIATIONS.md`.

---

## 10. Milestones and gates

Commit at each gate; update `STATUS.md` (done / tests / open issues / next); tag as noted.

- **M0 Preflight and audit.** Create the repo, `docs/PLAN.md`; run `doctor`; audit the legacy files (section 3). **Gate G0:** doctor green; `LEGACY_AUDIT.md` complete; plan written. Blocking questions are recorded once, at most five, and only when they change the design; otherwise the documented defaults stand.
- **M1 Networks.** Build and validate all three scenario networks (6.2-6.3); GUI settings. **G1:** `network_report.md` for each; headless run clean; GUI-launch command documented.
- **M2 Demand and calibration.** Fleet, route generation, calibrated levels for Flushing (pilot seeds); generation scripts ready for other scenarios. **G2:** `demand_levels.yaml` with evidence; unroutable trips = 0.
- **M3 Harness, controllers, tests.** Runner, logger, metrics, controllers C0-C3 and C5, and C4 written against a model interface (tested with a toy model until the real one is frozen in M5), tests 1-9 above (the α = 0 sanity test runs on smoke at G3 and on Flushing at G4). **G3:** all tests green on smoke and on one real Flushing run; `SUMO_API_NOTES.md` complete.
- **M4 Pilot and protocol freeze.** Run pilot seeds for C0, C1, C2 (initial η = 0.3), C3 (untuned α = 0.5) and C5 at all three levels. C4 needs the frozen model from M5, so use C3 as the proxy for runtime and variance, and measure model-inference cost separately. (Train the legacy RF for C5 on baseline runs from train seeds 0-1, never on pilot seeds.) Compute runtimes, the SD of paired Δ%, and the power analysis. Draft `PREREGISTRATION.md` (Appendix B). **G4:** budget printed; n determined; α = 0 sanity passes; `application/interim_note.md` written (audit findings and pilot results only, labeled interim and non-confirmatory).
- **M5 Data, predictor, α selection.** Generate training data; train and evaluate forecasters (7.3); evaluate legacy-task triviality (7.4 i); run the α-sweep on validation seeds for `eco_reactive` and `eco_ml` and pick **α\*_reactive and α\*_ml separately** by the same rule: *minimize mean total NOx subject to mean travel time <= +5% over `tt_adaptive`*. Calibrate the placebo noise η so `random_reroute`'s route-change rate matches `eco_ml`'s on validation seeds. **G5:** forecast skill report; model frozen (`model-freeze-v1`); α\*s and η recorded.
- **M6 Preregistration freeze and confirmatory runs.** Finalize `PREREGISTRATION.md` (seed lists, α*, model id, analysis code hash); commit and tag `prereg-v1`; then run the test seeds. **G6:** `experiment verify` clean; no code changed since the tag except documented bug fixes (any such fix is logged and the affected analysis re-run).
- **M7 Analysis and reporting inputs.** Run the frozen analysis; figures/tables; spatial and road-class analysis; `CLAIMS.md` (every claim -> result file -> CI); adversarial review (section 9, item 11). **G7:** every PC reported with its result; claims ledger complete.
- **M8 Tier 2 (optional, after G7).** Scenarios 2-3, transfer, compliance and horizon sweeps, C6-C8. Same freeze discipline (a separate `prereg-tier2-v1` tag). Label all outputs exploratory unless preregistered.
- **M9 Paper, application artifacts, release.** `paper/main.tex` (article class, about 8 pages plus appendix: abstract, introduction, related work using only verified citations, methods, results, discussion, limitations, reproducibility statement); compile with `tectonic` or `latexmk` (try to obtain a TeX engine without admin rights; if impossible, deliver `.tex` plus a Markdown rendering and record the environment limitation); also add `scripts/make_arxiv_bundle.py`, which packages the sources for an optional arXiv upload (the author decides whether to post, and with which co-authors). `application/`: `research_summary_1page.md` (<= 450 words, numbers injected from results, hedged exactly as the CIs allow), `claims_ledger.md`, `interview_faq.md` (including "what was wrong with version 1 and how did you find out?"), `project_page.md` for a personal website, and `docs/RESEARCH_AGENDA.md` (3-5 follow-up questions, each motivated by an observed result). Final `verify-all`; tag `v1.0`.
- **M10 CARLA live-visualization layer (optional, Tier 3).** Starts only after G7 and the go/no-go in 10.1. Purpose: a 3D live view and exact replays of the same Flushing simulation, for demonstration. It adds no scientific evidence: SUMO remains the only source of traffic dynamics and emissions, and nothing in the paper, the summary or `CLAIMS.md` may cite CARLA output. Read Appendix E first, then:
  1. **Environment.** CARLA 0.9.16 (Unreal Engine 4.26 line), not 0.10.0. Use a separate virtualenv (`.venv-carla`) with the `carla` wheel that matches the installed release (look in its `PythonAPI/carla/dist`); never modify the research environment. Use the same SUMO version as the research environment where possible and record both versions. CARLA needs Windows or Linux and an NVIDIA GPU; if `doctor` finds none, write "M10 skipped: no CARLA-capable machine" in `STATUS.md` and stop. The multi-GB CARLA package is downloaded only after a separate decision.
  2. **Map pipeline (SUMO net to CARLA).** Per scenario: `netconvert -s <net.xml> --opendrive-output <out.xodr> --output.original-names`, then `client.generate_opendrive_world(xodr_text, carla.OpendriveGenerationParameters(...))` (OpenDRIVE standalone mode; expect road meshes without detailed buildings, and check visually). Map size is limited by the engine, so start with a crop of about 1 km x 1 km (`netconvert --keep-edges.in-boundary ...`; verify the option name) and grow it until generation fails; record the largest size that works. If the alignment gate below cannot be met, document it and skip the live layer. Never change the experimental network.
  3. **Alignment gate (before any rendering work).** Use the co-simulation package's own SUMO-to-CARLA coordinate transform (read the code under `Co-Simulation/Sumo/` in the installed release; do not hand-roll the axis flip and offset). Take at least 500 random points on SUMO lane centerlines, transform them, and call `world.get_map().get_waypoint(location, project_to_road=True)`. Initial thresholds: median offset <= 1.0 m, 95th percentile <= 3.0 m, and at least 99% of points on a driving lane. Write `alignment_report.md` with a plot.
  4. **Replay mode (exact).** Re-run one chosen (scenario, level, seed, condition) with trajectory output added and nothing else changed (use `--fcd-output` or in-process recording restricted to the crop; limit file size with options verified in `--help`). Assert that the tripinfo hash equals the original run's (the determinism check of section 9, item 3). Interpolate positions and headings between 1 s steps to the render rate, set actor transforms with physics off, and spawn and destroy actors as vehicles enter and leave the crop. Produce clips of two conditions on the same seed (for example `static` vs `eco_ml`), side by side if ffmpeg is available.
  5. **Live mode.** Use the co-simulation scripts (read the installed `run_synchronization.py --help`; options include `--step-length`, `--tls-manager`, `--sync-vehicle-lights`). The live run is a separate demo at CARLA's step length (default 0.05 s), so its numbers differ from the 1 s experiments: label it "demo run, not part of the results", use demo seeds 9100-9199, and write outputs under `application/demo/`. Traffic-light synchronization defaults to off, and an exported map carries no signal objects; say so in the README and on screen.
  6. **Fleet and performance.** Map SUMO vTypes to CARLA blueprints in `configs/carla_vtypes.yaml` by enumerating the installed blueprint library (never guess blueprint IDs). Spawn only vehicles inside the crop or within a radius of the spectator. Measure sustained FPS against visible-actor count on the demo machine and record the cap in `CARLA_NOTES.md` (target at least 15 FPS; reduce render quality, resolution, or demand level before cutting the area).
  7. **Overlay (optional).** A HUD with simulated time, active vehicles, cumulative NOx in g and controller name, plus `world.debug` markers colored by recent per-edge NOx from the same run's data.

  **G10:** alignment gate passed; one replay clip of at least 60 s with a matching tripinfo hash; one live-mode run of at least 5 simulated minutes without desynchronization; `docs/CARLA_NOTES.md` complete (versions, exact commands, limits, failures); no entry in `CLAIMS.md` depends on CARLA. Time-box: 3 working days; if the alignment gate is not passed after 1 day, stop and record why. Artifacts live under `application/demo/`; tag `v1.1` if finished after `v1.0`.

### 10.1 Calendar, time-boxes, and early hand-overs
The application deadlines are fixed (Dec 1 and Dec 15, 2026) and this work starts about Nov 14-15, 2026, so schedule backwards. These are targets, not promises; replace them with real estimates once the pilot gives runtimes, and record changes in `STATUS.md`.

| Target date | Gate | Hand-over |
|---|---|---|
| Nov 16-17 | G0-G2 (repo, audit, networks, demand) | `docs/LEGACY_AUDIT.md` |
| Nov 19 | G3 (harness, controllers, tests green) | |
| Nov 21 | G4 (pilot, power analysis, n fixed) | `application/interim_note.md`: audit findings and pilot results only, labeled interim and non-confirmatory, usable in the Dec 1 materials |
| Nov 25 | G5 (forecaster and α* frozen) | |
| Nov 26 | G6 (prereg tag; confirmatory runs launched) | |
| Nov 30 | confirmatory runs complete; G7 analysis | first full draft of `application/research_summary_1page.md` |
| Dec 2-4 (optional) | M10 (CARLA layer) | `application/demo/` clips, only if the go/no-go below passes |
| Dec 5 | M9 (paper and application folder) | final one-page summary, claims ledger, FAQ |
| Dec 8 | freeze of everything used in the application | |

Stop-loss rule: if a gate is more than 2 days late, apply the scope-cut ladder (section 8) immediately, in order, instead of working around the delay. If confirmatory runs cannot finish by Dec 5, report the completed share and label the rest "not run". A smaller, finished, honestly reported study beats a larger unfinished one. Never fabricate or extrapolate missing results.

M10 go/no-go (Nov 30): start M10 only if G7 has passed, the OpenDRIVE export check (6.2, step 5) passed, and `doctor` found a CARLA-capable machine. Otherwise skip M10 and record that in `STATUS.md`; no further discussion is needed. M10 is not part of the Definition of Done.

---

## 11. Definition of Done (all must be true; list the evidence in `STATUS.md`)

- [ ] `python -m nycemis doctor` and `verify-all` pass on a clean clone using only the README commands.
- [ ] Three validated NYC scenario folders open in `sumo-gui` and run headless.
- [ ] Legacy audit complete; legacy-protocol replication reported; spurious-reduction mechanism demonstrated or refuted with data.
- [ ] Forecasters evaluated against baselines on held-out seeds; model frozen with a model card.
- [ ] Preregistration tagged before test seeds ran; PC1-PC4 each reported with CIs; deviations documented.
- [ ] Every planned run DONE or documented-failed; invalid-run counts reported.
- [ ] Reconciliation, pairing, determinism, leakage, parity, and α = 0 tests green.
- [ ] Figures, tables, paper numbers, and the one-page summary all generated from results; claims ledger complete.
- [ ] Every citation verified from a primary source and logged in the citation ledger; legacy references reused only if verified.
- [ ] `LIMITATIONS.md` and the paper's limitations section state the 4.9 threats; no claim of health or air-quality benefit.
- [ ] `OPEN_ITEMS.md` empty (or only out-of-scope-by-design, plus the TeX-engine limitation if it applies); no TODO/FIXME/placeholder text; no absolute paths.
- [ ] Attribution to the original co-author and supervisor, and OSM attribution, present.
- [ ] Optional: M10 acceptance (G10) passed, or `STATUS.md` records why M10 was skipped. CARLA is never required for completion.

---

## 12. Working agreements

- Work in the project folder only. Do not delete or modify `legacy/`. System-level software and any action outside the project directory are recorded before they happen. Commits are small, with messages like `M3: add eco_reactive controller + reconciliation test`.
- `STATUS.md` records the current milestone, commands to resume, running jobs, and known issues.
- Before a milestone is called done, each requirement in `STATUS.md` is ticked with evidence (command output summary or file path). Unticked means not done.
- Never hide or smooth a bad result. If a gate fails, fix the cause; do not relax the gate. If a gate truly cannot be met, stop and record the evidence.
- Use plain, precise language in all prose. No hype words; no claims beyond what the CIs support.
- The release note covers what was completed per milestone; the headline results for PC1-PC4 with CIs in plain words; what differed from the preregistration; anything in OPEN_ITEMS; exact commands to reproduce; the three most important caveats; and a reminder to share the corrected results with Prof. Huang (and Billy, as co-author) before letters are submitted.

## Appendix A: initial parameter table (change only with a recorded reason)

| Parameter | Value |
|---|---|
| Step length | 1 s |
| Departure window | 0-3600 s; run to completion; cap 14,400 s |
| Control tick / feature window / horizon | 60 s / 60 s / 60 s (Tier 2: 180, 300) |
| Feature lags | k, k-1, k-2 |
| Hotspot threshold | 95th percentile of non-empty training edge-windows |
| `v_min` in cost | 1.0 m/s |
| Reroute period per vehicle | 60 s (staggered) |
| α grid | 0, 0.25, 0.5, 0.75, 1.0 |
| α* rule | minimize NOx s.t. mean travel time <= +5% vs `tt_adaptive` (validation seeds), chosen separately for `eco_reactive` and `eco_ml` |
| Compliance (primary) | 100% |
| Validity | completion >= 99.5%, teleports <= 0.5% |
| SESOI | 2% of baseline NOx |
| Bootstrap | 10,000 resamples, fixed seed |
| Multiplicity | One Holm family over the 12 confirmatory tests (PC1-PC4 x 3 levels), familywise α = 0.05; TOST for PC1 and PC4 |
| Workers | cores - 1 |

## Appendix B: preregistration template (`docs/PREREGISTRATION.md`)
Title and date; frozen git commit and tag; research questions; hypotheses (PC1-PC4 with direction and SESOI); conditions and parameters (incl. α*, model id/hash); scenario/network/OSM-extract hashes; demand levels and seed lists; protocol and validity/exclusion rules; primary and secondary metrics with formulas and units; statistical plan (tests, intervals, multiplicity, equivalence margins, power calculation inputs and result); what is exploratory; planned deviations policy; known limitations.

## Appendix C: SUMO facts verified from official documentation (re-verify on the installed version)
- Install via PyPI: `eclipse-sumo`, `traci`, `libsumo`, `sumolib`; `import sumo; sumo.SUMO_HOME`. https://sumo.dlr.de/Download
- libsumo: `import libsumo as traci`; parallel runs need multiprocessing (one simulation per process); `traci.init/connect` unsupported (use `start`); GUI use is experimental and not working on Windows; some libraries need preloading on Windows from SUMO 1.16 (`Simulation.preloadLibraries()` since 1.24); pip install is supported. https://sumo.dlr.de/wiki/Libsumo
- Tripinfo emissions: options `--tripinfo-output` + `--device.emissions.probability 1.0`; child `<emissions CO_abs CO2_abs HC_abs PMx_abs NOx_abs fuel_abs electricity_abs>`; units mg (Wh for electricity); written on arrival only (option `--tripinfo-output.write-unfinished` exists). https://sumo.dlr.de/docs/Simulation/Output/TripInfo.html
- Edge emissions output: `<edgeData id=".." type="emissions" period="60" file=".." excludeEmpty="true"/>` with `_abs` (mg), `_normed` (g/km/h), `_perVeh` (mg, can blow up for standing traffic); attributes include `minSamples`, `maxTraveltime`, `vTypes`, `withInternal`; fuel in mg since 1.14. https://sumo.dlr.de/docs/Simulation/Output/Lane-_or_Edge-based_Emissions_Measures.html
- Emission models and default class `HBEFA3/PC_G_EU4`; model families HBEFA (v2.1, v3.1, v4.2), PHEMlight and PHEMlight5, two electric-vehicle models, and a zero-emission model; each model's page lists its classes. https://sumo.dlr.de/docs/Models/Emissions.html
- TraCI edge getters used: `getNOxEmission` (a rate in mg/s for the current step; multiply by the step length), `getLastStepMeanSpeed` (m/s), `getLastStepHaltingNumber` (speed below 0.1 m/s counts as halting), `getLastStepVehicleNumber`, `getTraveltime` (length / mean speed; the docs flag this definition as needing re-verification), `getWaitingTime` (sum over the vehicles on the edge, s), `getEffort` (-1 if unset), `setEffort`. https://sumo.dlr.de/pydoc/traci._edge.html ; https://sumo.dlr.de/docs/TraCI/Edge_Value_Retrieval.html
- Vehicle `getCO2Emission`, `getCOEmission`, `getHCEmission`, `getPMxEmission`, `getNOxEmission`, `getFuelConsumption`: rates in mg/s for the current step (multiply by the step length); the value -2^30 means unavailable. https://sumo.dlr.de/docs/TraCI/Vehicle_Value_Retrieval.html
- `rerouteEffort` minimizes effort using the vehicle's internal and the global edge effort; the routing docs say the default effort is 0, so unset edges look free; vehicles with rerouting devices use aggregated routing and ignore `setEffort` (SUMO user-list reply by Jakob Erdmann). https://sumo.dlr.de/wiki/TraCI/Change_Vehicle_State ; https://www.eclipse.org/lists/sumo-user/msg12916.html
- `findRoute` with the default mode and no rerouting device takes each edge's travel time from, in order, the vehicle's own data, global weight files, global TraCI edge weights, and finally the minimum travel time (length / allowed speed); effort is a separate criterion used by reroute-by-effort. https://sumo.dlr.de/docs/Simulation/Routing.html
- Randomness: default seed 23423; `--seed` sets it, `--random` takes it from the clock; results are expected to be identical for the same version, arguments and inputs, with documented exceptions (Proj and `log` differences across platforms or versions); the page does not discuss multi-threaded routing, so keep routing single-threaded. https://sumo.dlr.de/docs/Simulation/Randomness.html
- OSM import: `osmGet.py --bbox W,S,E,N [--tiles]` (also `--area`, `--polygon`; check `--help` for the output-name option), `osmBuild.py --osm-file [--vehicle-classes all|road|publicTransport|passenger] [--type-file] [--netconvert-options] [--polyconvert-options]`, typemaps in `$SUMO_HOME/data/typemap/`; the Web Wizard (`osmWebWizard.py`) builds scenarios from the same tools. https://sumo.dlr.de/docs/Tools/Import/OSM.html ; https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html
- `randomTrips.py` options: `--fringe-factor`, `--min-distance`, `--weights-prefix`, `--speed-exponent`, `-L` (lane-count weighting), `--validate`, `--trip-attributes`, `--fringe-start-attributes`, `--vehicle-class`, `--prefix`, `-b`/`-e` (defaults 0 and 3600), `-p` (period, default 1 s), `--seed`. https://sumo.dlr.de/wiki/Tools/Trip

## Appendix D: related-work seeds (existence confirmed before citation; each source is read before it is cited, and a citation does not go beyond what was read)
- Du, Chen, Dong, Chen, Fu, Labi, "Urban traffic dynamic rerouting framework: A DRL-based model with fog-cloud architecture", arXiv:2110.05532 (2021). Possible source of the legacy "Dong 2021" citation; compare.
- Fazzini, Torre, Rizza, Petracchini, "Effects of Smart Traffic Signal Control on Air Quality", Frontiers in Sustainable Cities 4, 2022, doi:10.3389/frsc.2022.756539 (signal control and pollutants, Bologna).
- Haydari, Zhang, Chuah, Ghosal, "Impact of Deep RL-based Traffic Signal Control on Air Quality", IEEE VTC2021-Spring, doi:10.1109/VTC2021-Spring51267.2021.9448639.
- Ahn and Rakha, "The effects of route choice decisions on vehicle energy consumption and emissions", Transportation Research Part D 13(3):151-167, 2008, doi:10.1016/j.trd.2008.01.005.
- Ahn and Rakha, "Network-wide impacts of eco-routing strategies: A large-scale case study", Transportation Research Part D, vol. 25, 2013 (starts p. 119), doi:10.1016/j.trd.2013.09.006.
Further literature on eco-routing, emission forecasting, and simulation-based evaluation methodology is cited only after the source has been read and verified.

## Appendix E: CARLA facts verified while drafting this specification (re-verify on the installed release)
- Platforms and GPU: CARLA is built for Windows and Linux. The UE4-based 0.9.x quick start asks for at least a 6 GB GPU and recommends 8 GB; the UE5-based 0.10.0 recommends 16 GB of VRAM and warns that less than 12 GB may fail to load its default map. https://carla.readthedocs.io/start_quickstart/ ; https://carla.readthedocs.io/en/0.9.14/start_quickstart/ ; https://carla.org/2024/12/19/release-0.10.0
- Version choice: 0.10.0 (Unreal Engine 5.5, Dec 2024) lists OpenDRIVE import, OpenStreetMap import and SUMO co-simulation as unsupported or untested. 0.9.16 (Sept 2025) is a release of the Unreal Engine 4.26 line. https://carla.org/2024/12/19/release-0.10.0 ; https://carla.org/2025/09/16/release-0.9.16
- Co-simulation: scripts under `Co-Simulation/Sumo`; `run_synchronization.py <sumocfg>` options include `--step-length` (default 0.05 s), `--tls-manager carla|sumo|none` (default none), `--sync-vehicle-lights`, `--sync-vehicle-color`, `--sync-vehicle-all`. The documented way to make a matching net is CARLA map -> `netconvert_carla.py`, the opposite direction from this project. https://carla.readthedocs.io/en/latest/adv_sumo/
- OpenDRIVE standalone mode: `client.generate_opendrive_world()` takes the .xodr content as a string; CARLA can ingest only maps of limited size because of engine limits. https://carla.readthedocs.io/en/0.9.10/tuto_G_openstreetmap/
- SUMO to OpenDRIVE: `netconvert --opendrive-output FILE` writes OpenDRIVE 1.4 and is flagged as under implementation. Documented limits: every road is typed "town", roads are one-directional, lane widenings and signals/objects are not modeled. Recommended options: `--junctions.scurve-stretch 1.0`, `--output.original-names`. A reply on the SUMO user list notes that the generated .xodr has no mesh information. https://sumo.dlr.de/docs/Networks/Export.html ; https://www.eclipse.org/lists/sumo-user/msg14605.html
