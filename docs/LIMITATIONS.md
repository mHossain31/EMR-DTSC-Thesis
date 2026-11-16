# Limitations and threats to validity

These statements bound every result in this repository (docs/SPECIFICATION.md 4.9). The paper's limitations section repeats
them. No result here is a claim about health, exposure or air quality: the outcome measured is **simulated
tailpipe emission mass**, per trip and in total.

1. **Synthetic demand.** Origin-destination demand comes from `randomTrips.py` on the OSM network, calibrated
   only to target congestion levels (mean-speed ratios). It is not calibrated to traffic counts in New York City.
2. **European emission models.** The emission classes are SUMO's HBEFA (and, where noted, PHEMlight) models, whose
   factors are based largely on European fleets and test cycles. They are not a model of the US fleet.
3. **Emissions are not concentrations.** There is no weather and no atmospheric dispersion, so emission mass cannot
   be read as pollutant concentration or human exposure.
4. **OSM-derived geometry and signals.** Lanes, speed limits, turn restrictions and traffic-signal locations come
   from OpenStreetMap and netconvert heuristics (guessed signals, default programs). They are imperfect.
5. **No pedestrians or transit.** Buses, pedestrians, cyclists and parking search are not simulated.
6. **Fixed compliance model.** Rerouted drivers follow advice exactly (100% compliance in the primary analysis);
   sensitivity to partial compliance is Tier 2.
7. **Single-hour demand profile.** Departures fall in one hour with a flat insertion rate; peak shapes, day-to-day
   variation and induced demand are not modelled.
8. **No field validation.** The simulator and the emission models are not validated against measurements in the
   study areas.
9. **Simulation-specific effects.** Results hold for one SUMO version (recorded per run) and one platform; SUMO
   documents platform-dependent differences in some numerical routines.
10. **Deadlock mitigation.** All runs use `--ignore-junction-blocker 30` (DEVIATIONS #6): a vehicle stuck inside a
    junction for 30 s no longer blocks others. This keeps congested runs from gridlocking at a few OSM junction
    clusters, at the cost of some physically implausible passing in those situations.
11. **Spatial tables exclude junction lanes.** Per-edge NOx (road-class shares, maps, Gini, peak density) covers
    non-internal edges only; emissions on internal junction lanes (their share is 1 - edge_logger_total_nox_mg /
    tripinfo NOx in each run's run_metrics.json) count in
    run totals but are not attributed to a road class.
12. **Fleet shares are assumed.** The mix of emission classes in `configs/fleet.yaml` is a modelling choice, not
    New York registration data; diesel vehicles emit far more NOx per kilometre than petrol ones in HBEFA, so the
    mix strongly affects absolute NOx.
