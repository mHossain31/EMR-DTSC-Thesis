# STATUS

Status of the study. Read this with `docs/PLAN.md`, `docs/DEVIATIONS.md`, and the sections of
`docs/SPECIFICATION.md` for the current milestone.

- **Current milestone:** M5 (forecaster and alpha*). G4 passed (pilot complete, n = 60). The dataset experiment
  is complete (432/432, verified); the forecaster `gbm_v1` is training.
- **Last updated:** 2026-11-15 21:35.

## Running jobs (detached; they survive a session restart)

Long batches are launched through WMI so they are not children of the interactive session:

```powershell
$root = (Get-Location).Path   # run from the repository root
$cmd = "cmd.exe /c `"cd /d $root && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe -m nycemis experiment run --exp <EXP> --workers <N> >> results\logs\<EXP>.log 2>&1`""
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $root }
```

| Job | Started | Log | Notes |
|---|---|---|---|
| train gbm_v1 | 2026-11-15 21:30 | `results/logs/train_gbm_v1.log` | `python -m nycemis train --model-id gbm_v1 --exp dataset`; 30 trials x 3 targets, about 1 h; not resumable (rerun from scratch) |
| net fetch dtbk | 2026-11-15 19:26 | `results/logs/fetch_dtbk.log` | Overpass returns 502/504; retries for up to 240 min |

Progress: `python -m nycemis experiment status --exp <EXP>`. A stopped executor resumes where it left off (runs
with a `DONE` marker are skipped; partial run directories are removed and rerun).

## Machine facts that matter for scheduling

- One simulation process commits about 1.1 GB; a legacy_ml process about 4.5 GB. The executor trims its pools to
  the available commit memory and runs at most 5 legacy_ml at a time.
- With the Windows "Balanced" power plan, 15 of 24 logical processors were parked under load (2026-11-15 19:38):
  about 9 cores do the work, whatever the worker count. Switching Windows to the "Best performance" power mode would
  likely unpark them; that is a Windows power setting.
- E: is a spinning disk; I/O was not a bottleneck (under 1% busy).

## Next steps (in order)

1. When training ends: read `models/flushing/gbm_v1/model_card.md`, commit, tag `model-freeze-v1`.
2. `python -m nycemis experiment run --exp validation` (planned: 612 runs), detached; then
   `python -m nycemis select` (alpha*_reactive, alpha*_ml, eta). G5.
3. `python -m nycemis prereg` (writes `configs/experiments/confirmatory.yaml` and the frozen
   `docs/PREREGISTRATION.md`); commit, tag `prereg-v1`.
4. `python -m nycemis experiment plan --exp confirmatory`, run detached, verify (G6); `python -m nycemis analyze` (M7).

## Gates

| Gate | Status | Evidence |
|---|---|---|
| G0 | done except doctor's Overpass check (server-side, intermittent) | `docs/LEGACY_AUDIT.md`; `python -m nycemis doctor` |
| G1 | Flushing, smoke and Midtown done; dtbk waits for the Overpass API | `data/networks/<s>/network_report.md` |
| G2 | done | `configs/demand_levels.yaml`, `results/calibration/flushing/` |
| G3 | done | 62 tests pass (`pytest`), including API contract, determinism, libsumo vs TraCI, reconciliation, shadow parity, alpha = 0 sanity on smoke, poison test, statistics |
| G4 | done | `results/pilot/pilot_report.md`: alpha = 0 sanity passes at every level, all C2/C3 runs valid, n = 60 |
| G5 | in progress | dataset verified (432 runs); forecaster training |

## Decisions so far

`docs/DEVIATIONS.md` #1-#13. Most important: `--ignore-junction-blocker 30` in the protocol (#6), junction join
20 m (#7), levels on the relative speed ratio (#8), reconciliation tolerance 0.5% for pilot runs (#9), device-equivalent travel time (#12) and the travel-time-weights router (#13) in the effort controllers.
