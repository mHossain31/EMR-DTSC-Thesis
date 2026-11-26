# NYC emissions in SUMO: forecast-driven, emission-aware rerouting

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24570057.svg)](https://doi.org/10.5281/zenodo.24570057)

A reproducible SUMO + machine-learning study of whether forecast-driven, emission-aware dynamic rerouting reduces
**simulated** tailpipe emissions in New York City, measured against proper baselines and a placebo under a
preregistered, paired, multi-seed protocol. It rebuilds and audits an earlier student project; see
`docs/LEGACY_AUDIT.md` for what was wrong with that version and how this one addresses it.

**Authors:** Mohammed Y. Hossain and Billy M. Kyaw (New York Institute of Technology). To cite this work, use
the Zenodo DOI [10.5281/zenodo.24570057](https://doi.org/10.5281/zenodo.24570057), which resolves to the latest
archived version, or see `CITATION.cff`. The paper is archived as a preprint on Zenodo:
[10.5281/zenodo.24570718](https://doi.org/10.5281/zenodo.24570718).

Status: the confirmatory study has run and been analysed (milestones M0-M7; the paper and the summary documents
of M9 are generated from the results). Where to read the results:

- `docs/CLAIMS.md`: every claim with its comparison, interval and result file; preregistered (PC1-PC4) and
  exploratory claims are kept apart.
- The paper in three layouts: the journal-style preprint `paper/journal/journal_preprint.pdf`, the two-column
  IEEE conference version `paper/ieee/ieee_conference.pdf` (both built by `python -m nycemis report`), and the
  technical report `paper/main.tex` (`python -m nycemis paper`; the v1.0 rendering is archived in
  `paper/archive/technical_report_v1.0/`).
- `docs/PREREGISTRATION.md` (git tag `prereg-v1`), `docs/DEVIATIONS.md`, `docs/LIMITATIONS.md`,
  `docs/LEGACY_AUDIT.md`, `docs/RESEARCH_AGENDA.md`; the street-coding sensitivity experiment:
  `docs/SENSITIVITY_PLAN.md` (git tag `sensitivity-v1`) and `docs/CLAIMS_SENSITIVITY.md`.

All quantities are simulated tailpipe emissions in SUMO. Nothing here is a claim about health or air quality.

## Project history

- **2024: the original course project.** "Air Pollution Prediction and Reduction Strategies in Urban Areas using
  SUMO and Machine Learning" (NYIT DTSC 870 Project I), by Mohammed Y. Hossain and Billy M. Kyaw, supervised by
  Prof. X. Huang. A machine-learning model triggered rerouting in a SUMO model of Flushing, Queens, and the project
  reported a large cut in emissions. Its report, slides and notebook are kept unchanged in `legacy/` (the notebook
  archive is dated October 2024).
- **November 2026: the audit.** Re-reading the notebook showed that the reported reduction came from how it was
  measured, not from the rerouting: the baseline and the controlled runs covered different lengths of simulated
  time, and most reroute calls returned the route the vehicle already had. Replicating the old rule under a matched
  protocol confirmed this (`docs/LEGACY_AUDIT.md`).
- **November 2026: the rebuild.** The study was redone as a preregistered experiment with a matched protocol,
  baselines and a random-rerouting placebo. Networks of three New York City areas were built and validated; the
  experiments use Flushing. The forecaster (tag `model-freeze-v1`) and the analysis plan (tag `prereg-v1`) were
  frozen before any test-seed run. The confirmatory runs, the frozen analysis and an adversarial review of the code,
  protocol and results followed (`docs/PREREGISTRATION.md`, `docs/CLAIMS.md`, `docs/DEVIATIONS.md`).
- **November 2026: the network-coding check.** The analysis showed that the reduction depends on moving traffic
  onto residential streets. A follow-up experiment, fixed before its runs (tag `sensitivity-v1`), recoded Flushing
  with the city's default speed limit and stop signs where minor streets meet unsignalised junctions. On that
  network, measured-emission rerouting emitted more NOx than travel-time rerouting at every demand level
  (`docs/CLAIMS_SENSITIVITY.md`).
- **Release.** Tag `v1.0`, then the paper as a journal-style preprint and an IEEE conference version, all generated
  from the same result files.

The exact date of each step is in the git tags and in `docs/DEVIATIONS.md`.

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
.venv/Scripts/python.exe -m nycemis experiment run --exp sensitivity_posted  # street-coding sensitivity
.venv/Scripts/python.exe -m nycemis sensitivity                      # its analysis (docs/SENSITIVITY_PLAN.md)
.venv/Scripts/python.exe -m nycemis paper                            # macros, documents, PDF
.venv/Scripts/python.exe -m nycemis report                           # journal and IEEE versions
.venv/Scripts/python.exe scripts/make_arxiv_bundle.py --variant journal  # arXiv package of the preprint
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
- `paper/`: `main.tex`, generated `macros.tex`, figures; `application/` (not tracked): summary documents that `python -m nycemis paper` generates locally.

## Credits

The original project, "Air Pollution Prediction and Reduction Strategies in Urban Areas using SUMO and Machine
Learning" (NYIT DTSC 870 Project I), was co-authored by **Mohammed Y. Hossain** (team leader) and
**Billy M. Kyaw**, supervised by **Prof. X. Huang** (NYIT). This rebuild, its paper versions and the summary
documents are the joint work of Mohammed Y. Hossain and Billy M. Kyaw.

Map data: Contains data © OpenStreetMap contributors, ODbL. See `NOTICE.md`.

## Use of AI tools

The code of this rebuild (everything outside `legacy/`) and the drafts of the paper and summary documents were
developed with the assistance of Claude (Anthropic), an AI coding assistant used through Claude Code, under the
authors' direction. The authors set the research questions, approved the preregistered protocol, and defined the
checks every result must pass (`python -m nycemis verify-all`: the test suite, run verification, the
preregistration hash, and a check that the paper contains no hand-typed numbers). The assistant is what made a
study of this scope practical for two people: a full audit of the 2024 project, three demand levels, six
controllers, 60 paired seeds per condition and level, and a sensitivity experiment. The authors are responsible for
all content.

## License

Code, configuration and documentation: MIT (`LICENSE`). The OpenStreetMap extracts in `data/osm/` and the SUMO
networks built from them in `scenarios/` are distributed under the Open Database License 1.0, the license of the
data they derive from. See `NOTICE.md`.
