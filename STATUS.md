# STATUS

Status of the study. Read this with `docs/PLAN.md`, `docs/DEVIATIONS.md`, and the sections of
`docs/SPECIFICATION.md` for the current milestone.

- **Current milestone:** M6 (confirmatory runs). G5 passed: validation 612/612 verified; `python -m nycemis select`
  gave alpha*_reactive = alpha*_ml = 0.75 and eta = 1 (`results/validation/selection.json`). The preregistration is
  frozen (commit 0a020b3, tag `prereg-v1`, analysis-code hash 09dbec7a, the same in a clean clone of the tag;
  `verify-all --only prereg` passes). The confirmatory experiment (1,080 runs, test seeds 200-259) is paused at
  20/1080; resume it first.
- **Last updated:** 2026-11-16 23:33.

## Running jobs (detached; they survive a session restart)

Long batches are launched through WMI so they are not children of the interactive session:

```powershell
$root = (Get-Location).Path   # run from the repository root
$cmd = "cmd.exe /c `"cd /d $root && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe -m nycemis experiment run --exp <EXP> >> results\logs\<EXP>.log 2>&1`""
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $root }
```

| Job | Started | Log | Notes |
|---|---|---|---|
| confirmatory, 6 conditions x 3 levels x 60 seeds (1,080 runs) | 2026-11-16 23:25, **paused 23:32** on request (PC shut down overnight), 20/1080 DONE | `results/logs/confirmatory.log` | resume with the command above and `--exp confirmatory`; about 5 h; CPU-heavy |

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

0. Resume the confirmatory batch (WMI command above, `<EXP>` = confirmatory); runs started after the tag, so
   resuming keeps the prereg check valid.
1. When the confirmatory batch ends: `python -m nycemis experiment verify --exp confirmatory` (G6) and
   `python -m nycemis verify-all --only prereg` (the tag predates every confirmatory run).
2. `python -m nycemis analyze` (M7; rehearsed end to end on relabelled pilot runs, Pareto plot included), then an
   independent adversarial review, G7.
3. M9: `python -m nycemis paper` (tectonic into `tools/`), application materials, `RESEARCH_AGENDA.md`,
   `verify-all`, tag v1.0.
4. Any change to `src/nycemis/analysis/*.py` or `configs/base.yaml` from here on changes the frozen hash: record
   it in `docs/DEVIATIONS.md` with the new hash, or `verify-all` fails.

## Gates

| Gate | Status | Evidence |
|---|---|---|
| G0 | done except doctor's Overpass check (server-side, intermittent) | `docs/LEGACY_AUDIT.md`; `python -m nycemis doctor` |
| G1 | done: Flushing, smoke, Midtown and dtbk validated; dtbk misses bbox_match (89.6% inside, minimum 90%), accepted as a documented Tier-2 limitation (DEVIATIONS #16, LIMITATIONS 13) | `data/networks/<s>/network_report.md` |
| G2 | done | `configs/demand_levels.yaml`, `results/calibration/flushing/` |
| G3 | done | 62 tests pass (`pytest`), including API contract, determinism, libsumo vs TraCI, reconciliation, shadow parity, alpha = 0 sanity on smoke, poison test, statistics |
| G4 | done | `results/pilot/pilot_report.md`: alpha = 0 sanity passes at every level, all C2/C3 runs valid, n = 60 |
| G5 | done | dataset verified (432 runs); `models/flushing/gbm_v1/model_card.md` (tag `model-freeze-v1`); validation verified (612 runs); `results/validation/selection.json` |
| G6 | in progress | `docs/PREREGISTRATION.md` (tag `prereg-v1`); confirmatory running |

## Decisions so far

`docs/DEVIATIONS.md` #1-#15. Most important: `--ignore-junction-blocker 30` in the protocol (#6), junction join
20 m (#7), levels on the relative speed ratio (#8), reconciliation tolerance 0.5% for pilot runs (#9),
device-equivalent travel time (#12) and the travel-time-weights router (#13) in the effort controllers, r and v
forecast on their own scale (#14).
