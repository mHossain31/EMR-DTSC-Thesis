# STATUS

Status of the study. Read this with `docs/PLAN.md`, `docs/DEVIATIONS.md`, and the sections of
`docs/SPECIFICATION.md` for the current milestone.

- **Current milestone:** M5 (forecaster and alpha*). G4 passed (pilot complete, n = 60). The dataset experiment
  is complete (432/432, verified). The forecaster gbm_v1 is frozen (tag `model-freeze-v1`; r and v on their own
  scale, DEVIATIONS #14; the first, log1p version is kept as `models/flushing/gbm_v1_rejected_log1p/`). The
  validation experiment (alpha sweeps, placebo eta) is running.
- **Last updated:** 2026-11-16 22:10.

## Running jobs (detached; they survive a session restart)

Long batches are launched through WMI so they are not children of the interactive session:

```powershell
$root = (Get-Location).Path   # run from the repository root
$cmd = "cmd.exe /c `"cd /d $root && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe -m nycemis experiment run --exp <EXP> >> results\logs\<EXP>.log 2>&1`""
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $root }
```

| Job | Started | Log | Notes |
|---|---|---|---|
| validation, all controllers (370 of 612 runs left) | 2026-11-16 22:05 | `results/logs/validation.log` | memory gate, budget 16.5 GB |
| dtbk OSM download, enlarged box (DEVIATIONS #15) | 2026-11-16 22:07 | `results/logs/fetch_dtbk3.log` | network only |

The 19:30 dtbk download did not happen: the fetch reused the old extract because it checked only the file hash; it
now also compares the box (`network/osm_fetch.py`).

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

1. When validation ends: `python -m nycemis experiment verify --exp validation`; `python -m nycemis select`
   (alpha*_reactive, alpha*_ml, eta). G5.
2. `python -m nycemis prereg` (writes `configs/experiments/confirmatory.yaml` and the frozen
   `docs/PREREGISTRATION.md`); review, commit, tag `prereg-v1`.
3. `python -m nycemis experiment plan --exp confirmatory`; run detached (1,080 runs, overnight); verify (G6).
4. `python -m nycemis analyze` (M7), adversarial review, G7; then M9.
5. dtbk: when the download ends, `python -m nycemis net build --scenario dtbk` and check G1.

## Gates

| Gate | Status | Evidence |
|---|---|---|
| G0 | done except doctor's Overpass check (server-side, intermittent) | `docs/LEGACY_AUDIT.md`; `python -m nycemis doctor` |
| G1 | Flushing, smoke and Midtown done; dtbk box enlarged (DEVIATIONS #15), download running | `data/networks/<s>/network_report.md` |
| G2 | done | `configs/demand_levels.yaml`, `results/calibration/flushing/` |
| G3 | done | 62 tests pass (`pytest`), including API contract, determinism, libsumo vs TraCI, reconciliation, shadow parity, alpha = 0 sanity on smoke, poison test, statistics |
| G4 | done | `results/pilot/pilot_report.md`: alpha = 0 sanity passes at every level, all C2/C3 runs valid, n = 60 |
| G5 | in progress | dataset verified (432 runs); `models/flushing/gbm_v1/model_card.md` (tag `model-freeze-v1`); validation running |

## Decisions so far

`docs/DEVIATIONS.md` #1-#15. Most important: `--ignore-junction-blocker 30` in the protocol (#6), junction join
20 m (#7), levels on the relative speed ratio (#8), reconciliation tolerance 0.5% for pilot runs (#9),
device-equivalent travel time (#12) and the travel-time-weights router (#13) in the effort controllers, r and v
forecast on their own scale (#14).
