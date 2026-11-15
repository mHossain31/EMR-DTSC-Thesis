# STATUS

Status of the study. Read this with `docs/PLAN.md`, `docs/DEVIATIONS.md`, and the sections of
`docs/SPECIFICATION.md` for the current milestone.

- **Current milestone:** M4 (pilot) starting. M0, M2, M3 done; M1 done for Flushing and smoke, Midtown and Downtown
  Brooklyn waiting on the Overpass API (gateway errors 502/504).
- **Last updated:** 2026-11-15.
- **Running jobs:** `net fetch` for midtown then dtbk (background, retries up to 180 min each; log in
  `results/logs/fetch_<s>.log`). Restart with the command below if it is not running.

## Resume

```bash
.venv/Scripts/python.exe -m nycemis doctor
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m nycemis net fetch --scenario midtown --max-wait-min 180   # then: net build --scenario midtown
.venv/Scripts/python.exe -m nycemis net fetch --scenario dtbk --max-wait-min 180      # then: net build --scenario dtbk
```

## Gates

| Gate | Requirement | Evidence | Done |
|---|---|---|---|
| G0 | doctor green | all required checks green except `overpass`, which is intermittent (server-side 502/504; Flushing downloaded at 00:42 on 2026-11-15) | partly |
| G0 | `docs/LEGACY_AUDIT.md` complete | generated, 12 claims; replication section pending (M4) | yes |
| G1 | `network_report.md` per scenario | `data/networks/flushing/network_report.md` PASS (2,316 edges, 176 signals, 96.2% in the largest SCC, 92.5% of lane-km inside the box); smoke PASS; midtown and dtbk pending download | partly |
| G1 | headless run clean, GUI command documented | 300 s smoke runs: 0 errors; `sumo-gui -c scenarios/flushing/flushing.sumocfg`; the colour-scheme indices await a visual check with an active display | partly |
| G2 | `configs/demand_levels.yaml` with evidence; unroutable trips = 0 | light 10.0, moderate 16.0, heavy 20.75 veh/h/km (relative speed ratio 0.947 / 0.849 / 0.719, all pilot seeds valid); `results/calibration/flushing/`; every route file reports 0 unroutable | yes |
| G3 | tests green on smoke and one Flushing run; `SUMO_API_NOTES.md` complete | `pytest`: 53 passed (API contract, determinism, libsumo vs TraCI, logging neutrality, reconciliation, shadow-mode parity, alpha = 0 sanity on smoke, artifact demonstration, poison test); `results/runs/timing`: one Flushing heavy run per controller type, all valid | yes |

## Key decisions so far (details in docs/DEVIATIONS.md)

1-3 environment; 4-5 OSM download filter and clip; 6 `--ignore-junction-blocker 30` in the protocol;
7 junction join 20 m; 8 levels on the relative speed ratio; 9 reconciliation tolerance 0.5% for pilot runs
(the partial arrival step is not observable through TraCI).

## Measured costs (Flushing heavy, 1 run each, 2026-11-15)

static 80 s; tt_adaptive 96 s; random_reroute, eco_reactive, eco_ml (toy model) about 110 s; legacy_ml 569 s (toy
predictor; 1.6 million findRoute calls).

## Next

M4: legacy RF training data (static, train seeds 0-1), legacy RF and its triviality tests, the pilot (5 pilot seeds x
3 levels), power analysis, budget, preregistration draft, interim note.
