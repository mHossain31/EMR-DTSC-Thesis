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
13. **Downtown Brooklyn overhangs its box.** The Tier-2 Downtown Brooklyn network keeps whole the roads that cross its
    box edge, so 10.4% of its lane-km (mostly the Manhattan and Brooklyn Bridges and the Gowanus Expressway) lie
    outside the box, against the 90% inside share the other networks meet (DEVIATIONS #16). It is used in no
    experiment.
14. **Speed coding and junction control favour residential detours.** Where OpenStreetMap has no speed tag,
    netconvert assigns SUMO's default speed for the road type, as the OSM Web Wizard does, so most arterial lane-km in
    Flushing carry type defaults rather than posted limits; most signals sit at junctions with a tertiary or larger
    road, and no junction is stop-controlled (paper macros `SpeedPrimSec`, `SpeedResid`, `JunctionsSignal`, `JunctionsStop`, computed from the
    network file). Emission-aware rerouting lowers NOx largely by moving vehicle-hours from signalised arterials onto
    residential and service streets (docs/CLAIMS.md, RQ5 section). How cheap those detours are depends on this coding.
    The street-coding sensitivity experiment (docs/SENSITIVITY_PLAN.md, docs/CLAIMS_SENSITIVITY.md) recoded the
    network with New York City's default 25 mph limit and minor-road stops: there the measured-emission controller
    emitted more NOx than travel-time rerouting at every level and the residential shift disappeared. The PC2 and PC3
    reductions therefore describe the network as built, not Flushing; forecast-driven rerouting was not run on the
    recoded network, and its stop control is an assumption, not the city's sign inventory.
15. **Displacement is not exposure.** RQ5 measures where tailpipe NOx is emitted, by road class. Residential streets
    are where people live, but without dispersion and population data nothing follows about exposure or health,
    in either direction.
16. **Departure delay sits outside travel time.** Travel-time metrics run from departure; the wait to enter the
    network is reported separately (`mean_depart_delay_s`, in seconds in the claims ledger).
17. **The forecast is not isolated.** No confirmatory condition separates the forecast from the rest of the eco_ml
    controller (the shuffled-forecast control C7 is Tier 2), and the forecaster's skill against a per-edge
    historical mean is reported in docs/CLAIMS.md (RQ2 section). Differences between eco_ml and eco_reactive (PC4) are
    therefore not attributed to forecasting.
