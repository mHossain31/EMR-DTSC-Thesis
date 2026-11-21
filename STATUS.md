# STATUS

Status of the study. Read this with `docs/PLAN.md`, `docs/DEVIATIONS.md`, and the sections of
`docs/SPECIFICATION.md` for the current milestone.

- **Current milestone:** M9 complete except the v1.0 tag, held for one decision (doctor's Overpass check,
  Definition of Done item 1). The street-coding sensitivity experiment ran (540/540, verified; plan tagged
  `sensitivity-v1` before the runs): with NYC's default 25 mph limit and minor-road stops, measured-emission rerouting
  emitted more NOx than travel-time rerouting at every level (docs/CLAIMS_SENSITIVITY.md); the paper, summary,
  project page, FAQ, LIMITATIONS 14 and RESEARCH_AGENDA question 1 report it. `verify-all` passes. Nothing running.
- **2026-11-18:** paper proofread (8 pages; three wording fixes), README brought up to date, guard so
  `analyze-pilot` cannot overwrite the frozen `docs/PREREGISTRATION.md`, `RESEARCH_BREAKDOWN.md` kept out of git
  (decision). `doctor` passes except the Overpass check (all four servers timed out: an outside outage; the
  OSM extracts are frozen in `data/`, so no stage needs Overpass now): retry before release.
- **Done 2026-11-17:** confirmatory 1,080/1,080 runs, `experiment verify` clean (G6); frozen analysis run and committed
  unedited (12c18b3); independent adversarial review (docs/SPECIFICATION.md 9.11). Its findings and the responses are in
  `docs/DEVIATIONS.md` #17-#20: RQ5 side effects and the composition decomposition, the network's speed coding as a
  threat to validity, PC4 direction and observed SDs, tail travel time and departure delay, the legacy replication
  on the test seeds, and the legacy_ml route-change counter bug (fixed; recount `legacy_recount`, 15 runs, NOx
  identical: 136 of 4,443,027 calls changed a path). PC1-PC4 are identical before and after. New analysis-code hash
  3b97c291 is recorded in DEVIATIONS #17; `verify-all --only prereg` passes.
- **Last updated:** 2026-11-20 21:55.

## Running jobs (detached; they survive a session restart)

Long batches are launched through WMI so they are not children of the interactive session:

```powershell
$root = (Get-Location).Path   # run from the repository root
$cmd = "cmd.exe /c `"cd /d $root && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe -m nycemis experiment run --exp <EXP> >> results\logs\<EXP>.log 2>&1`""
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $root }
```

| Job | Status | Log | Notes |
|---|---|---|---|
| confirmatory (1,080 runs) | done 2026-11-17 23:01, verified | `results/logs/confirmatory.log` | |
| legacy_recount (15 runs) | done 2026-11-17, NOx identical to the pilot's legacy_ml runs | `results/logs/legacy_recount.log` | DEVIATIONS #18 |
| `python -m nycemis forecast-test` | done 2026-11-19 22:00 (65 min while the sensitivity batch ran) | `results/logs/forecast_test.log` | `results/confirmatory/forecast_test.json`; DEVIATIONS #20 |
| sensitivity_posted, 3 conditions x 3 levels x 60 seeds (540 runs) | done 2026-11-20 21:38 (resumed 21:04 after the overnight pause), verified, 5 invalid runs | `results/logs/sensitivity_posted.log` | analysed: `results/sensitivity_posted/analysis.json` |

The dtbk extract for the enlarged box was downloaded at 22:44 after 12 failed Overpass attempts (commit 256eabb).

If a job is stopped, run the same command again: DONE runs are skipped, partial run directories are removed and
rerun. Progress: `python -m nycemis experiment status --exp <EXP>`.

## Machine facts that matter for scheduling

- One simulation process commits about 1.1 GB, a legacy_ml process the same (the legacy RF is a memory-mapped
  forest shared by all of them; `results/legacy_audit/rerun_check.json`: 1.1 GB committed, 1.27 GB peak working
  set). A batch gets a memory budget of free physical RAM minus a 6 GB reserve (`execution.memory_reserve_gb`); a
  gate admits each run only while the admitted runs fit the budget and free RAM stays above the reserve. legacy_ml
  runs are CPU-bound (400-900 s) and run in their own pool of at most 8.
- 2026-11-16 19:14: the PC crashed (bugcheck 0x116, display driver timeout with STATUS_INSUFFICIENT_RESOURCES)
  while forecaster training (8 threads) ran beside 10 simulations and about 17 GB of other programs; the old guard
  counted the page file as available memory. Do not run training beside a simulation batch.
- Pause CPU-heavy batches when the machine is in use; they resume where they
  stopped.
- With the Windows "Balanced" power plan, 15 of 24 logical processors were parked under load (2026-11-15 19:38):
  about 9 cores do the work, whatever the worker count. Switching Windows to the "Best performance" power mode would
  likely unpark them; that is a Windows power setting.
- E: is a spinning disk; I/O was not a bottleneck (under 1% busy).

## Next steps (in order)

1. Decision on `doctor`'s Overpass check (see the Definition of Done below); then tag `v1.0`.
2. Optional, not started: M10 (CARLA; the multi-GB download has not been fetched) and the follow-ups of `docs/RESEARCH_AGENDA.md`.
3. Any change to `src/nycemis/analysis/*.py` or `configs/base.yaml` changes the frozen hash (record it in
   `docs/DEVIATIONS.md`); any change to `src/nycemis/sensitivity.py` goes in `docs/SENSITIVITY_PLAN.md` as a dated
   amendment. `RESEARCH_BREAKDOWN.md` stays out of git (decision 2026-11-18).

## Definition of Done (docs/SPECIFICATION.md section 11), ticked with evidence

- [ ] `doctor` and `verify-all` pass on a clean clone using only the README commands. `verify-all` passes (2026-11-20
      21:46, `results/logs/verify_all.log`: pytest 89 passed, ruff, six experiments 2,784 runs verified, prereg,
      paper, open items, space path). `doctor` passes every required check except Overpass reachability: the
      overpass-api.de status endpoint answers some User-Agents at once with HTTP 406 or 502 and does not answer
      `doctor`'s (`nycemis-doctor/0.1`) within 15 s, on 2026-11-19 and 2026-11-20; no stage needs Overpass, since the
      OSM extracts are frozen in `data/osm/` with hashes in `data/MANIFEST.json`. Open decision: keep the
      check failing, or make it informational while every frozen extract verifies (would be DEVIATIONS #22).
      `verify-all` check 6 clones the committed tree into a path with a space and runs the smoke reconciliation
      and determinism tests there. A full clean-clone rebuild repeats every experiment (the run folders under
      `results/runs/` are not in git) and was not repeated.
- [x] Three validated NYC scenario folders that open in `sumo-gui` and run headless:
      `data/networks/{flushing,midtown,dtbk}/network_report.md` (dtbk misses bbox_match narrowly, accepted as a
      documented limitation: DEVIATIONS #16, LIMITATIONS 13); `python -m nycemis gui --scenario S --level L --seed N
      --controller C` (checked 2026-11-20 with eco_reactive on Flushing).
- [x] Legacy audit complete; replication reported; mechanism demonstrated with data: `docs/LEGACY_AUDIT.md`
      (section 5, including the test seeds: legacy metric 77-79% drop vs matched metric within +-0.4%; route changes
      recounted, DEVIATIONS #18).
- [x] Forecasters evaluated against baselines on held-out seeds; model frozen with a card:
      `models/flushing/gbm_v1/model_card.md` (tag `model-freeze-v1`); `results/confirmatory/forecast_test.json`
      (test seeds, DEVIATIONS #20).
- [x] Preregistration tagged before the test seeds; PC1-PC4 reported with CIs; deviations documented: tag `prereg-v1`
      (`verify-all` prereg check); `docs/CLAIMS.md`; `docs/DEVIATIONS.md` #1-#21.
- [x] Every planned run DONE or documented-failed; invalid-run counts reported: `experiment verify` for pilot,
      dataset, validation, confirmatory, legacy_recount and sensitivity_posted; invalid counts in
      `results/confirmatory/analysis.json` and `results/sensitivity_posted/analysis.json`.
- [x] Reconciliation, pairing, determinism, leakage, parity and alpha = 0 tests green: `verify-all` pytest check.
- [x] Figures, tables, paper numbers and the one-page summary generated from results; claims ledger complete:
      `verify-all` paper check (every macro generated, no typed numbers); `docs/CLAIMS.md`,
      `docs/CLAIMS_SENSITIVITY.md`, `application/claims_ledger.md`.
- [x] Every citation verified and logged: `docs/CITATION_LEDGER.md` (hygiene test checks every `refs.bib` key); no
      legacy reference reused.
- [x] LIMITATIONS and the paper's limitations state the threats of 4.9; no health or air-quality claim:
      `docs/LIMITATIONS.md` items 1-17; paper section 6.
- [x] OPEN_ITEMS holds only out-of-scope-by-design items; no unfinished-work markers; no absolute paths:
      `verify-all` open_items and hygiene checks.
- [x] Attribution to the original co-author and supervisor, and OSM attribution: README credits, `NOTICE.md`, the
      paper's acknowledgments.
- [x] Optional M10 (CARLA): not started. It is not part of the Definition of Done, needs a multi-GB download that has not been fetched, and the priority was the paper by 2026-11-24.

## Gates

| Gate | Status | Evidence |
|---|---|---|
| G0 | done except doctor's Overpass check (server-side, intermittent) | `docs/LEGACY_AUDIT.md`; `python -m nycemis doctor` |
| G1 | done: Flushing, smoke, Midtown and dtbk validated; dtbk misses bbox_match (89.6% inside, minimum 90%), accepted as a documented Tier-2 limitation (DEVIATIONS #16, LIMITATIONS 13) | `data/networks/<s>/network_report.md` |
| G2 | done | `configs/demand_levels.yaml`, `results/calibration/flushing/` |
| G3 | done | 62 tests pass (`pytest`), including API contract, determinism, libsumo vs TraCI, reconciliation, shadow parity, alpha = 0 sanity on smoke, poison test, statistics |
| G4 | done | `results/pilot/pilot_report.md`: alpha = 0 sanity passes at every level, all C2/C3 runs valid, n = 60 |
| G5 | done | dataset verified (432 runs); `models/flushing/gbm_v1/model_card.md` (tag `model-freeze-v1`); validation verified (612 runs); `results/validation/selection.json` |
| G6 | done | `experiment verify --exp confirmatory`: 1,080/1,080, 0 problems; tag `prereg-v1` predates every run |
| G7 | done: every PC reported with its CI; claims ledger complete; adversarial review answered (DEVIATIONS #17-#20) | `docs/CLAIMS.md`, `results/confirmatory/` |
| M8 (sensitivity) | done: plan tagged `sensitivity-v1` before the runs; 540/540 verified; analysed | `docs/SENSITIVITY_PLAN.md`, `docs/CLAIMS_SENSITIVITY.md` |
| M9 | done except the v1.0 tag (one decision) | `paper/build/main.pdf` (9 pages), `application/`, `verify-all` |

## Decisions so far

`docs/DEVIATIONS.md` #1-#20. Most important: `--ignore-junction-blocker 30` in the protocol (#6), junction join
20 m (#7), levels on the relative speed ratio (#8), reconciliation tolerance 0.5% for pilot runs (#9),
device-equivalent travel time (#12) and the travel-time-weights router (#13) in the effort controllers, r and v
forecast on their own scale (#14).
