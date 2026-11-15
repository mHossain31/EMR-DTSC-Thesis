# NYC emissions in SUMO: forecast-driven, emission-aware rerouting

A reproducible SUMO + machine-learning study of whether forecast-driven, emission-aware dynamic rerouting reduces
**simulated** tailpipe emissions in New York City, measured against proper baselines and a placebo under a
preregistered, paired, multi-seed protocol. It rebuilds and audits an earlier student project; see
`docs/LEGACY_AUDIT.md` for what was wrong with that version and how this one addresses it.

Status: work in progress. `STATUS.md` lists what is done and what is next. Results are not yet available, and
nothing here is a claim about health or air quality (`docs/LIMITATIONS.md`).

## Scenarios

| ID | Area | Role |
|---|---|---|
| `flushing` | Downtown Flushing, Queens | primary |
| `midtown` | Midtown Manhattan | secondary (Tier 2) |
| `dtbk` | Downtown Brooklyn | secondary (Tier 2) |

## Quick start

Python 3.11 or 3.12. SUMO comes from PyPI, so no system install is needed.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock      # macOS/Linux: .venv/bin/python
.venv/Scripts/python.exe -m pip install -e . --no-deps
.venv/Scripts/python.exe -m nycemis doctor
.venv/Scripts/python.exe -m pytest
```

`python -m nycemis --help` lists the stages available so far.

## Repository map

- `docs/SPECIFICATION.md`: the full specification of the study.
- `docs/`: the plan, design notes, legacy audit, deviations, limitations, SUMO API notes, citation ledger.
- `src/nycemis/`: the package (CLI, configuration, SUMO environment, legacy audit, and the later stages).
- `configs/`: protocol, seeds and analysis constants (`base.yaml`).
- `legacy/`: read-only copies of the original report, slides and notebook, plus text extracts.

## Credits

The original project, "Air Pollution Prediction and Reduction Strategies in Urban Areas using SUMO and Machine
Learning" (NYIT DTSC 870 Project I), was co-authored by **Mohammed Y. Hossain** (team leader) and
**Billy M. Kyaw**, supervised by **Prof. X. Huang** (NYIT).

Map data: Contains data © OpenStreetMap contributors, ODbL. See `NOTICE.md`.

License: MIT (`LICENSE`).
