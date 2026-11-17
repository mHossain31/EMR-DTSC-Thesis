# STATUS

Status of the study. Read this with `docs/PLAN.md`, `docs/DEVIATIONS.md`, and the sections of
`docs/SPECIFICATION.md` for the current milestone.

- **Current milestone:** M5 (forecaster and alpha*). G4 passed (pilot complete, n = 60). The dataset experiment
  is complete (432/432, verified). The first gbm_v1 (r on log1p) was set aside before use (DEVIATIONS #14) and is
  being retrained; the validation runs that do not need it are running.
- **Last updated:** 2026-11-16 19:35 (PC crash at 19:14; training relaunched alone).

## Running jobs (detached; they survive a session restart)

Long batches are launched through WMI so they are not children of the interactive session:

```powershell
$root = (Get-Location).Path   # run from the repository root
$cmd = "cmd.exe /c `"cd /d $root && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe -m nycemis experiment run --exp <EXP> --workers <N> >> results\logs\<EXP>.log 2>&1`""
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $root }
```

After the crash of 2026-11-16 19:14 (see machine facts), training runs alone:

| Job | Started | Log | Notes |
|---|---|---|---|
| train gbm_v1 (r on its own scale, DEVIATIONS #14) | 2026-11-16 19:29 | `results/logs/train_gbm_v1_r_raw.log` | all cores, alone; memory sampled to `results/logs/train_gbm_v1_memory.log`; about 1 h |

Waiting: validation pass 1 (232 of 612 DONE; resumable) and the dtbk network build (OSM extract downloaded
2026-11-16). Start them after training, not beside it.

If they are stopped again, resume with the commands below (DONE validation runs are skipped; training restarts).

To resume, from the repository root in PowerShell (the same three jobs, detached):

```powershell
$root = (Get-Location).Path
function Start-Detached($args_, $log) {
  $cmd = "cmd.exe /c `"cd /d $root && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe -m nycemis $args_ >> results\logs\$log 2>&1`""
  Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $root }
}
Start-Detached "train --scenario flushing --model-id gbm_v1 --exp dataset --n-jobs 8" "train_gbm_v1_r_raw.log"
Start-Detached "experiment run --exp validation --workers 14 --controllers static,tt_adaptive,eco_reactive,random_reroute" "validation.log"
Start-Detached "net fetch --scenario dtbk --max-wait-min 240" "fetch_dtbk.log"
```

Progress: `python -m nycemis experiment status --exp <EXP>`. A stopped executor resumes where it left off (runs
with a `DONE` marker are skipped; partial run directories are removed and rerun).

## Machine facts that matter for scheduling

- One simulation process commits about 1.1 GB; a legacy_ml process about 4.5 GB. The executor sizes its pools to
  the free physical RAM minus a 6 GB reserve (`execution.memory_reserve_gb`), runs at most 5 legacy_ml at a time,
  and holds new runs while free RAM is below the reserve.
- 2026-11-16 19:14: the PC crashed (bugcheck 0x116, display driver timeout with STATUS_INSUFFICIENT_RESOURCES)
  while forecaster training (8 threads) ran beside 10 simulations and about 17 GB of other programs; the old guard
  counted the page file as available memory. Do not run training beside a simulation batch.
- With the Windows "Balanced" power plan, 15 of 24 logical processors were parked under load (2026-11-15 19:38):
  about 9 cores do the work, whatever the worker count. Switching Windows to the "Best performance" power mode would
  likely unpark them; that is a Windows power setting.
- E: is a spinning disk; I/O was not a bottleneck (under 1% busy).

## Next steps (in order)

1. When training ends: read `models/flushing/gbm_v1/model_card.md` (check the r calibration), commit, tag
   `model-freeze-v1`.
2. `python -m nycemis experiment run --exp validation --controllers eco_ml` (180 runs), detached; verify; then
   `python -m nycemis select` (alpha*_reactive, alpha*_ml, eta). G5.
3. `python -m nycemis prereg` (writes `configs/experiments/confirmatory.yaml` and the frozen
   `docs/PREREGISTRATION.md`); commit, tag `prereg-v1`.
4. `python -m nycemis experiment plan --exp confirmatory`, run detached, verify (G6); `python -m nycemis analyze` (M7).

## Gates

| Gate | Status | Evidence |
|---|---|---|
| G0 | done except doctor's Overpass check (server-side, intermittent) | `docs/LEGACY_AUDIT.md`; `python -m nycemis doctor` |
| G1 | Flushing, smoke and Midtown done; dtbk extract downloaded, network build pending | `data/networks/<s>/network_report.md` |
| G2 | done | `configs/demand_levels.yaml`, `results/calibration/flushing/` |
| G3 | done | 62 tests pass (`pytest`), including API contract, determinism, libsumo vs TraCI, reconciliation, shadow parity, alpha = 0 sanity on smoke, poison test, statistics |
| G4 | done | `results/pilot/pilot_report.md`: alpha = 0 sanity passes at every level, all C2/C3 runs valid, n = 60 |
| G5 | in progress | dataset verified (432 runs); forecaster training |

## Decisions so far

`docs/DEVIATIONS.md` #1-#13. Most important: `--ignore-junction-blocker 30` in the protocol (#6), junction join
20 m (#7), levels on the relative speed ratio (#8), reconciliation tolerance 0.5% for pilot runs (#9), device-equivalent travel time (#12) and the travel-time-weights router (#13) in the effort controllers.
