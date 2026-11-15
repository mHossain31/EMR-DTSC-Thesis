# SUMO API notes (installed version)

Every SUMO option, tool and TraCI function this project uses, checked against the **installed** SUMO
(docs/SPECIFICATION.md P7). "Exists" was checked with `sumo --help`, the tool's `--help`, or `hasattr` on the libsumo module.
"Behaves" is checked by an API-contract test on a toy network (`tests/integration/test_api_contract.py`, M3),
named in the last column.

Installed: SUMO **1.28.0** (`eclipse-sumo`, `libsumo`, `traci`, `sumolib`, `sumo-data` 1.28.0 from PyPI), Windows 11,
Python 3.12.13. `SUMO_HOME` = `.venv/Lib/site-packages/sumo` (from `import sumo; sumo.SUMO_HOME`).

## Environment and backend

| Item | Finding | Checked | Contract test |
|---|---|---|---|
| `SUMO_HOME` discovery | `import sumo; sumo.SUMO_HOME` returns the wheel's directory with `bin/`, `data/`, `tools/` | 2026-11-14 | `tests/unit/test_env.py` |
| libsumo import on Windows | Imports; its `__init__` calls `os.add_dll_directory` for the wheel's `bin/` itself | 2026-11-14 | `tests/unit/test_env.py` |
| `Simulation.preloadLibraries` | Not present in libsumo 1.28 (`dir(libsumo.simulation)` has no such attribute) | 2026-11-14 | - |
| libsumo and pyarrow | libsumo 1.28 warns unless pyarrow's major version matches its libarrow (23); pyarrow pinned to 23.x | 2026-11-14 | - |

## `sumo` options (exist in `sumo --help`, 1.28.0)

| Option | Use here | Contract test |
|---|---|---|
| `--step-length` | 1 s, explicit | M3 |
| `--seed` | per run | M3 (determinism) |
| `--time-to-teleport` | 300 s, explicit | M3 |
| `--collision.action` | `warn` | M3 |
| `--tripinfo-output`, `--tripinfo-output.write-unfinished` | per-trip emissions; unfinished vehicles flagged | M3 |
| `--device.emissions.probability` | 1 | M3 |
| `--statistic-output` | run summary (teleports, collisions) | M3 |
| `--no-step-log` | quiet runs | M3 |
| `--device.rerouting.probability`, `--device.rerouting.period`, `--device.rerouting.adaptation-interval`, `--device.rerouting.adaptation-steps` | C1 `tt_adaptive` only | M3 |
| `--device.rerouting.threads` | never set (routing stays single-threaded, docs/SPECIFICATION.md 6.1) | - |
| `--emission-output` | never used (docs/SPECIFICATION.md 4.4) | - |
| `--edgedata-output`, `--summary-output`, `--routing-algorithm` | exist; use decided in M3 | - |

## libsumo / TraCI functions (exist via `hasattr`, 1.28.0)

`vehicle`: `rerouteEffort`, `rerouteTraveltime`, `setRoute`, `getRoute`, `getRouteIndex`, `getRoadID`,
`getNOxEmission`, `getCO2Emission`, `getCOEmission`, `getHCEmission`, `getPMxEmission`, `getSpeed`, `getPosition`,
`getLaneIndex`, `setParameter`, `subscribe`, `getAllSubscriptionResults`.
`edge`: `setEffort`, `getEffort`, `adaptTraveltime`, `getAdaptedTraveltime`, `getTraveltime`, `getNOxEmission`,
`getCO2Emission`, `getLastStepMeanSpeed`, `getLastStepVehicleNumber`, `getLastStepHaltingNumber`,
`getWaitingTime`, `getLastStepOccupancy`, `getLaneNumber`, `getIDList`, `subscribe`, `getAllSubscriptionResults`.
`simulation`: `findRoute`, `getMinExpectedNumber`, `getTime`, `getArrivedNumber`, `getStartingTeleportNumber`,
`getCollidingVehiclesNumber`, `getDepartedNumber`, `getLoadedNumber`, `getParameter`, `subscribe`.

Behaviour (units of the emission getters, effort semantics including the -1 for unset efforts and overwrite
versus accumulate, rerouting-device vehicles ignoring efforts, `getTraveltime` semantics) is checked in M3 and
recorded below as each contract test passes.

## Behaviour verified by contract tests

(Filled as the M3 tests pass.)
