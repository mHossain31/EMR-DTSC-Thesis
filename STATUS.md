# STATUS

Status of the study. Read this with `docs/PLAN.md`, `docs/DEVIATIONS.md`, and the sections of
`docs/SPECIFICATION.md` for the current milestone.

- **Current milestone:** M4 (pilot) finishing; M5 dataset runs in progress. Code for M5-M7 and the paper skeleton
  is written and tested on the smoke grid.
- **Last updated:** 2026-11-15 19:45.

## Running jobs (detached; they survive a session restart)

Long batches are launched through WMI so they are not children of the interactive session:

```powershell
$root = "E:\PROJECTS\EMR-DTSC-THESIS"
$cmd = "cmd.exe /c `"cd /d $root && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe -m nycemis experiment run --exp <EXP> --workers <N> >> results\logs\<EXP>.log 2>&1`""
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $root }
```

| Job | Started | Log | Notes |
|---|---|---|---|
| pilot (105 runs) | 2026-11-15 19:26 | `results/logs/pilot.log` | 75/105 at 19:41; the 30 legacy_ml runs remain (at most 5 at a time, about 4 GB each) |
| dataset (432 runs) | 2026-11-15 19:41 | `results/logs/dataset.log` | 6 workers while the pilot finishes |
| net fetch midtown, dtbk | 2026-11-15 19:26 | `results/logs/fetch_<s>.log` | Overpass returns 502/504; retries for up to 240 min each |

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

1. When the pilot is DONE: `python -m nycemis analyze-pilot` (variance, power, budget, alpha = 0 sanity, legacy
   replication; renders the pilot report, the audit's section 5, the interim note and the preregistration draft).
   Check G4, commit.
2. When the dataset is DONE: `python -m nycemis train --model-id gbm_v1` (30-trial search; writes the model card).
   Tag `model-freeze-v1`.
3. `python -m nycemis experiment plan --exp validation` and run it; then `python -m nycemis select`
   (alpha*_reactive, alpha*_ml, eta). G5.
4. Write `configs/experiments/confirmatory.yaml` from the selection, finalise the preregistration, tag
   `prereg-v1`, run the confirmatory seeds (n from the pilot), then `python -m nycemis analyze` (M7).

## Gates

| Gate | Status | Evidence |
|---|---|---|
| G0 | done except doctor's Overpass check (server-side, intermittent) | `docs/LEGACY_AUDIT.md`; `python -m nycemis doctor` |
| G1 | Flushing and smoke done; midtown and dtbk wait for the Overpass API | `data/networks/<s>/network_report.md` |
| G2 | done | `configs/demand_levels.yaml`, `results/calibration/flushing/` |
| G3 | done | 61 tests pass (`pytest`), including API contract, determinism, libsumo vs TraCI, reconciliation, shadow parity, alpha = 0 sanity on smoke, poison test, statistics |
| G4 | pending pilot | `results/pilot/` |

## Decisions so far

`docs/DEVIATIONS.md` #1-#9. Most important: `--ignore-junction-blocker 30` in the protocol (#6), junction join
20 m (#7), levels on the relative speed ratio (#8), reconciliation tolerance 0.5% for pilot runs (#9).
