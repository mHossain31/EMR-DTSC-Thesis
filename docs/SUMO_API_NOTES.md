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

All in `tests/integration/test_api_contract.py` on the smoke grid, SUMO 1.28.0, libsumo (2026-11-15).

| Behaviour | Result | Test |
|---|---|---|
| `edge.getEffort` of an edge never set | returns -1 | `test_effort_unset_is_minus_one_and_set_overwrites` |
| `edge.setEffort(e, v)` without begin/end | value valid at t = 1 s and t = 100,000 s; a second call overwrites (no accumulation) | same |
| `vehicle.rerouteEffort` with a 1e9 effort on an edge of the remaining route | the new route avoids it | `test_reroute_effort_avoids_expensive_edge` |
| `vehicle.rerouteEffort` on a vehicle with a rerouting device | also avoids it (15/15 in a probe): an explicit TraCI call uses the global efforts; the "devices ignore efforts" statement applies to the device's periodic rerouting | `test_device_vehicle_reroute_effort_behaviour`, `test_device_periodic_rerouting_is_travel_time_based` |
| `edge.adaptTraveltime` + `vehicle.rerouteTraveltime(vid, False)` | an unset weight reads -1 (`getAdaptedTraveltime`); a value set without begin/end holds at t = 100,000 s and is overwritten by the next set; rerouting avoids an edge with weight 1e9; the router adds SUMO's defaults `--weights.minor-penalty 1.5` and `--weights.turnaround-penalty 5` (read from `sumo --save-template`), which effort routing does not; used by C2-C4 (DEVIATIONS #13) | `test_adapted_traveltime_weights_and_reroute_traveltime` |
| `vehicle.getNOxEmission` units | mg/s for the last step: sum of rate x 1 s over all vehicles and steps equals tripinfo `NOx_abs` (mg) within 0.1% (0.078% on the smoke grid); per vehicle the two differ by a few mg in both directions | `test_vehicle_emission_getters_are_mg_per_s` |
| `edge.getTraveltime` | length / last-step mean speed on an occupied edge; length / lane max speed on an empty edge (not a smoothed or adapted value) | `test_edge_traveltime_semantics` |
| `simulation.findRoute(from, to)` with defaults, no weights, no device | equals the duarouter (free-flow) route of the vehicle for 403/403 departing vehicles on the smoke grid (legacy defect D2) | `test_find_route_default_reproduces_static_route` |
| tripinfo `<emissions>` child | carries `NOx_abs`, `CO2_abs`, `CO_abs`, `HC_abs`, `PMx_abs`, `fuel_abs` (mg) with the emissions device | `test_tripinfo_emission_attributes` |
| -2^30 (unavailable) from emission getters | never added; counted per run (`recon_invalid_values`, `edge_logger_invalid_values`) | runner |
| Arrived vehicles | not readable: with `--keep-after-arrival 1` the emission getters of an arrived vehicle return -2^30; the partial arrival step is therefore missing from per-step sums (about -0.16% of NOx on Flushing; DEVIATIONS #9) | probe 2026-11-15 |
| A new vehicle subscription | reports from the step after `subscribe`; the departure step is read with direct getters | `VehicleEmissionLogger` |
| Default emission class | `HBEFA4/PC_petrol_Euro-4` (not `HBEFA3/PC_G_EU4` as docs/SPECIFICATION.md Appendix C states for older versions) | `vehicletype.getEmissionClass("DEFAULT_VEHTYPE")`, 2026-11-15 |
| sumo-gui scheme indices | lane scheme 11 = "by NOx emissions", vehicle scheme 8 = "by speed", inferred from the order of the scheme names in `sumo-gui.exe`; a snapshot showed NOx-scheme grey lanes on an empty grid; the legend-based visual check is pending an active display | `network/scenario_files.py` |
| netconvert patching of a built network (sensitivity experiment) | `netconvert --sumo-net-file <net> --edge-files <patch.edg.xml> --node-files <patch.nod.xml>`: an edge given only `id` and `speed` takes the new speed on all its lanes; a node given only `id` and `type` takes the new junction type; edge ids, node ids, lane counts and successor links are unchanged (checked on `flushing_posted`: 2,316 edges, 6,699 links, 0 lane-count changes; junction shapes are recomputed, largest edge-length change 1.15 m) | 2026-11-19 | `data/networks/flushing_posted/network_build.json` |
| `priority_stop` junction type | listed by `netconvert --help` (`--default.junctions.type`); vehicles on lower-priority approaches stop before entering | 2026-11-19 | `flushing_posted` build and smoke run (0 errors) |
