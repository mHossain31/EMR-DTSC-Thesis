# Street-coding sensitivity experiment: plan

Written before any test-seed run of the experiment and frozen with the git tag `sensitivity-v1`. Exploratory: it was
added after the confirmatory results were known (adversarial review, docs/DEVIATIONS.md #17 and #21) and is not part
of the preregistration (`prereg-v1`), whose PC1-PC4 it does not change.

## Question

On the original Flushing network, emission-aware rerouting lowers simulated NOx mostly by moving vehicle-hours from
tertiary and arterial roads onto residential and service streets (docs/CLAIMS.md, RQ5 section). That network keeps
SUMO's default speed for each OpenStreetMap road type where OSM has no speed tag (arterials at 80-100 km/h,
residential streets at 50 km/h) and has no stop-controlled junction (docs/LIMITATIONS.md item 14). Does the reduction,
and the shift onto residential streets, persist when the network is coded the way New York City streets are
regulated?

## Network: `flushing_posted`

`configs/scenarios/flushing_posted.yaml`, built by `src/nycemis/network/build.py` (`build_patch`) as a netconvert patch
of the built `flushing` network, so edges, lanes, junction joins, connections and signals are identical:

- **Speeds.** Every edge of type primary, secondary, tertiary (and their links), residential or unclassified whose speed
  is still the typemap default (OSM had no maxspeed tag) gets 25 mph (11.176 m/s): New York City's default limit,
  which applies to "all streets which do not have a posted speed limit" since 2014-11-07 (NYC DOT press release
  #14-085, 2014-10-15). Edges with an OSM speed tag, motorways and trunks keep their speeds; service roads and living
  streets already default below 25 mph.
- **Stop control.** Every unsignalised junction (priority or right-before-left) that a residential, unclassified or
  service edge enters becomes a SUMO `priority_stop` junction: vehicles on its lower-priority approaches stop before
  entering (a two-way stop, the commonest control at New York minor-street intersections). This is a modelling
  assumption; New York's actual stop-sign inventory is not used.

Counts of changed edges and junctions: `data/networks/flushing_posted/network_build.json`.

## Demand

The same procedure as the main study (docs/DEVIATIONS.md #8): densities calibrated on pilot seeds 9000-9004 to the same
relative speed ratio targets (light 0.95, moderate 0.85, heavy 0.72 of the near-empty network's ratio),
`python -m nycemis calibrate --scenario flushing_posted`; result in `configs/demand_levels.yaml`. Routes are generated
for this network as in the main study (`randomTrips.py` plus `duarouter`), so the demand differs from the original
network's for the same seed number.

**Calibration outcome (2026-11-19, before this plan was frozen).** Light and moderate reach their targets. Heavy does
not: above the heavy density chosen, pilot runs exceed the validity limit on teleports (the stop-controlled minor
approaches jam), so the calibration's existing rule (unchanged since the main study: when no valid density reaches the
target, use the most congested valid one and record the shortfall) gives a heavy level less congested than on the
original network. Densities and achieved ratios for both networks: `configs/demand_levels.yaml`
(`target_reached: false` for `flushing_posted` heavy) and `results/calibration/flushing_posted/`. Consequences fixed
here: at heavy demand the two networks are compared at different congestion, so the between-network difference at
heavy demand is reported but not read as an effect of the coding alone; and heavy runs on this network may fail the
validity rule more often (valid pairs only, invalid counts reported).

## Conditions and seeds

`configs/experiments/sensitivity_posted.yaml`: `static`, `tt_adaptive` and `eco_reactive` with the main study's
alpha*_reactive (0.75, `tau_avg_s` 180, `traveltime_weights` router), at light, moderate and heavy demand on test
seeds 200-259 (n = 60), 540 runs. The controller is held fixed: alpha is not reselected on this network, because the
question is whether the same controller's effect depends on the coding.

`eco_ml` is not run: its forecaster was trained on the original network's features, which include the speed limits,
so on this network it would be out of distribution; retraining would need a new dataset, tuning and alpha selection.
`eco_reactive` shows the same shift onto residential streets on the original network (paper, Figure 2), so it carries
the question.

## Outcomes and analysis

All exploratory; code in `src/nycemis/sensitivity.py` (`python -m nycemis sensitivity`), frozen with this plan. Valid
pairs only (the main study's validity rule); invalid-run counts reported.

1. **Total NOx**, `eco_reactive` vs `tt_adaptive` and vs `static`, per level: mean paired percent change, 95% BCa
   interval, two-sided Wilcoxon p-value, no multiplicity correction.
2. The same contrast on the original network (the confirmatory runs) beside it, and the difference between networks
   (posted-limit minus original mean change; independent samples, since the demand differs) with a 95% percentile
   bootstrap interval.
3. **Side effects:** NOx and vehicle-hours on residential/service streets and their share of edge NOx, and the
   composition decomposition (share of the edge-NOx change explained by the road-class mix of vehicle-hours), on both
   networks.
4. **Cost:** mean and 95th-percentile travel time, departure delay, vehicle-km and CO2, same contrasts.

**Reading, fixed in advance.** The reduction "persists" at a level if the 95% interval of outcome 1 (`eco_reactive`
vs `tt_adaptive`) lies below zero; it is "smaller on the posted-limit network" if the between-network interval of
outcome 2 lies above zero, "larger" if below, and "not clearly different" otherwise. The same rules phrase the
generated sentences (`nox_sentence`). Results are reported whatever they are, in the paper (a sensitivity section),
`docs/CLAIMS_SENSITIVITY.md` and the one-page summary.
