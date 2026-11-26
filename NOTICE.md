# Notices

## Map data

Contains data © OpenStreetMap contributors, ODbL.
OpenStreetMap data is available under the Open Database License (https://opendatacommons.org/licenses/odbl/).
The OSM extracts used to build the scenario networks are frozen in `data/osm/` and listed with their SHA-256
hashes in `data/MANIFEST.json`. Networks, routes and results derived from them are produced works of that data.

The MIT License in `LICENSE` covers the code, configuration and documentation only. The OSM extracts in
`data/osm/` and the SUMO network files built from them (`scenarios/*/*.net.xml.gz`) are distributed under the
Open Database License 1.0, the license of the data they derive from, with the attribution above.

## Simulation software

Eclipse SUMO (https://eclipse.dev/sumo/) is distributed under the Eclipse Public License 2.0 or GPL 2.0 or later.
It is installed from PyPI (`eclipse-sumo`, `libsumo`, `traci`, `sumolib`); exact versions are pinned in
`requirements.lock` and recorded in every run's `run.json`.

## Original project

This repository rebuilds the NYIT DTSC 870 Project I "Air Pollution Prediction and Reduction Strategies in Urban
Areas using SUMO and Machine Learning" by Mohammed Y. Hossain (team leader) and Billy M. Kyaw, supervised by
Prof. X. Huang (NYIT). Read-only copies of the original report, slides and notebook are kept in `legacy/` for the
audit in `docs/LEGACY_AUDIT.md`. They are the authors' own work. The student ID numbers on the report's title page and
in its text extract were redacted on 2026-11-25 (`docs/DEVIATIONS.md` #28).
