# STATUS

Status of the study. Read this with `docs/PLAN.md`, `docs/DEVIATIONS.md`, and the sections of
`docs/SPECIFICATION.md` for the current milestone.

- **Current milestone:** M7/M9 finishing, plus the street-coding sensitivity experiment the authors asked for on
  2026-11-19 (docs/SENSITIVITY_PLAN.md, DEVIATIONS #21; frozen in fc892fd, tag `sensitivity-v1`, before its runs).
  Running since 2026-11-19 21:11: the `sensitivity_posted` batch (540 runs) and `forecast-test` (since 20:54).
  Target: project and report complete by Tuesday 2026-11-24 (user); expected Friday 2026-11-20 evening.
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
- **Last updated:** 2026-11-19 21:15.

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
| `python -m nycemis forecast-test` | STOPPED twice by user pauses (2026-11-17 after about 10 min; 2026-11-18 after 39 min of evaluation); not resumable, rerun from the start. Expect about 55 min: loading 1 min, then evaluation scaled from the freeze-time validation evaluation (19.4 min for 1.37M rows; the test set has 3.58M rows). Single process, one core, about 4 GB RAM | `results/logs/forecast_test.log` | DEVIATIONS #20; writes `results/confirmatory/forecast_test.json` |
| sensitivity_posted, 3 conditions x 3 levels x 60 seeds (540 runs) | started 2026-11-19 21:11 (detached, pid 29252) | `results/logs/sensitivity_posted.log` | memory gate; about 2 h; resumes after a pause like the other batches |

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

1. `python -m nycemis forecast-test` (held-out forecast evaluation, about 55 min; running since 2026-11-19
   20:54; rerun from the start if stopped).
2. `python -m nycemis analyze` again, so `docs/CLAIMS.md` gains the RQ2 test-seed section (the analysis code is
   final: hash 3b97c291; PC1-PC4 must stay identical).
3. `python -m nycemis paper`: macros (the paper's forecast paragraph, `\ForecastVerdictR`, the abstract's last
   sentence and the summary's forecast line need `forecast_test.json`), FAQ, one-page summary (366 words before the
   forecast line; limit 450), project page, PDF. Read the PDF end to end (new Discussion and RQ5 sections).
4. `python -m nycemis verify-all` (retry `doctor`'s Overpass check too); tick the Definition of Done (docs/SPECIFICATION.md
   section 11) here with evidence; commit (M7/M9) and close G7 (every PC reported; claims ledger complete).
5. Sensitivity experiment (user approved 2026-11-19): when `sensitivity_posted` is DONE, `experiment verify
   --exp sensitivity_posted`, `python -m nycemis sensitivity`, a sensitivity section in `paper/main.tex`
   (`\input{macros_sensitivity.tex}`), summary and agenda updates, then `verify-all` and tag v1.0.
6. `RESEARCH_BREAKDOWN.md` (repository root; personal notes written by another session) is kept out of git by
   `.gitignore`, as decided on 2026-11-18.
7. Any further change to `src/nycemis/analysis/*.py` or `configs/base.yaml` changes the hash again: record the new
   hash in `docs/DEVIATIONS.md`, or `verify-all` fails.

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
| G7 | in progress: analysis run, adversarial review done and answered (DEVIATIONS #17-#20); test-seed forecast evaluation and final documents pending | `docs/CLAIMS.md`, `results/confirmatory/` |

## Decisions so far

`docs/DEVIATIONS.md` #1-#20. Most important: `--ignore-junction-blocker 30` in the protocol (#6), junction join
20 m (#7), levels on the relative speed ratio (#8), reconciliation tolerance 0.5% for pilot runs (#9),
device-equivalent travel time (#12) and the travel-time-weights router (#13) in the effort controllers, r and v
forecast on their own scale (#14).
