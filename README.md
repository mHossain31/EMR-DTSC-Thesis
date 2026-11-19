# NYC emissions in SUMO: forecast-driven, emission-aware rerouting

A reproducible SUMO + machine-learning study of whether forecast-driven, emission-aware dynamic rerouting reduces
**simulated** tailpipe emissions in New York City, measured against proper baselines and a placebo under a
preregistered, paired, multi-seed protocol. It rebuilds and audits an earlier student project; see
`docs/LEGACY_AUDIT.md` for what was wrong with that version and how this one addresses it.

Status: the confirmatory study has run and been analysed (milestones M0-M7; the paper and application materials
of M9 are generated from the results). Where to read the results:

- `application/research_summary_1page.md`: one page, every number generated from result files.
- `docs/CLAIMS.md`: every claim with its comparison, interval and result file; preregistered (PC1-PC4) and
  exploratory claims are kept apart.
- `paper/main.tex`, compiled to `paper/build/main.pdf` by `python -m nycemis paper`.
- `docs/PREREGISTRATION.md` (git tag `prereg-v1`), `docs/DEVIATIONS.md`, `docs/LIMITATIONS.md`,
  `docs/LEGACY_AUDIT.md`, `docs/RESEARCH_AGENDA.md`.

All quantities are simulated tailpipe emissions in SUMO. Nothing here is a claim about health or air quality.

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

The full pipeline, in order (each stage is idempotent; `python -m nycemis <stage> --help` gives the options):

```bash
.venv/Scripts/python.exe -m nycemis legacy-audit                     # audit of the 2024 project
.venv/Scripts/python.exe -m nycemis net --help                       # OSM download, network build, validation
.venv/Scripts/python.exe -m nycemis demand --help                    # fleet, demand generation
.venv/Scripts/python.exe -m nycemis calibrate                        # demand levels on pilot seeds
.venv/Scripts/python.exe -m nycemis experiment run --exp pilot       # then: analyze-pilot
.venv/Scripts/python.exe -m nycemis experiment run --exp dataset     # then: train (forecaster freeze)
.venv/Scripts/python.exe -m nycemis experiment run --exp validation  # then: select, prereg
.venv/Scripts/python.exe -m nycemis experiment run --exp confirmatory
.venv/Scripts/python.exe -m nycemis experiment verify --exp confirmatory
.venv/Scripts/python.exe -m nycemis forecast-test                    # held-out forecast evaluation
.venv/Scripts/python.exe -m nycemis analyze                          # frozen analysis, figures, claims
.venv/Scripts/python.exe -m nycemis paper                            # macros, documents, PDF
.venv/Scripts/python.exe -m nycemis verify-all                       # every automated check
```

Batches are long (hours for the confirmatory experiment on a 24-thread machine); `STATUS.md` records how they
were run. The paper needs a TeX engine: tectonic at `tools/tectonic.exe` or on PATH, or latexmk (`docs/DESIGN.md`).

## Repository map

- `docs/SPECIFICATION.md`: the full specification of the study.
- `docs/`: the plan, design notes, legacy audit, deviations, limitations, SUMO API notes, citation ledger.
- `src/nycemis/`: the package (CLI, configuration, SUMO environment, legacy audit, and the later stages).
- `configs/`: protocol, seeds and analysis constants (`base.yaml`).
- `legacy/`: read-only copies of the original report, slides and notebook, plus text extracts.
- `results/`: result files of every experiment (run folders under `results/runs/` are not in git).
- `models/`: the frozen forecaster and the legacy random forest, with model cards.
- `paper/`: `main.tex`, generated `macros.tex`, figures; `application/`: summary, claims ledger, FAQ, project page.

## Credits

The original project, "Air Pollution Prediction and Reduction Strategies in Urban Areas using SUMO and Machine
Learning" (NYIT DTSC 870 Project I), was co-authored by **Mohammed Y. Hossain** (team leader) and
**Billy M. Kyaw**, supervised by **Prof. X. Huang** (NYIT).

Map data: Contains data © OpenStreetMap contributors, ODbL. See `NOTICE.md`.

License: MIT (`LICENSE`).
