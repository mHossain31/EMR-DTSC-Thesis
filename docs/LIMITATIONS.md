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
