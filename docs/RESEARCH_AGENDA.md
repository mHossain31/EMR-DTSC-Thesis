# Research agenda

Follow-up questions, each motivated by a result of this study (docs/SPECIFICATION.md M9). Numbers are in the files cited, not
here: `docs/CLAIMS.md` (section and claim IDs), `paper/main.tex` (section names), `docs/LIMITATIONS.md`. Nothing
below has been run; each question would need its own preregistered comparison.

## 1. Does the eco-routing reduction survive realistic street coding?

**Motivated by:** the RQ5 section of `docs/CLAIMS.md` (NOx on residential and service streets roughly doubles under
forecast eco-rerouting, and the road-class shift of vehicle-hours explains most of the edge-NOx reduction) together
with the network's coding (paper, Methods: arterials carry SUMO's type-default speeds and signals, residential
streets have no stop control; `docs/LIMITATIONS.md` item 14).

**Study:** rebuild Flushing with posted speed limits where OpenStreetMap lacks them and stop control at unsignalised
residential junctions, recalibrate demand to the same congestion levels, and repeat PC2 and PC3. If the reduction
shrinks in proportion to the cost of residential detours, the original effect is largely a property of the network
coding, not of eco-routing.

## 2. Can eco-routing keep its benefit without displacing emissions onto residential streets?

**Motivated by:** the same RQ5 result. A routing objective that counts only total network NOx rewards moving
traffic onto the streets where people live.

**Study:** add a road-class or exposure weight to the emission cost (for example, NOx on residential edges counted
at a multiple of its mass) and trace the Pareto front between total NOx, residential NOx and travel time across that
weight, with the same paired seeds. With a dispersion model and population data, the weight can become an exposure
estimate instead of a policy choice.

## 3. What information does the controller actually use?

**Motivated by:** the RQ2 section of `docs/CLAIMS.md` (on the test seeds the forecaster is compared with a per-edge
historical average of NOx per vehicle-second, the quantity the controller uses) and PC4's 90% intervals (forecast
eco-rerouting emits less than measured-emission eco-rerouting by more than the margin at some levels).

**Study:** run the Tier-2 negative control C7 (forecasts shuffled across edges each tick) and a controller that uses
the per-edge historical mean as its emission cost, against eco_ml and eco_reactive on fresh test seeds. This
separates the value of the next-minute forecast from that of a learned per-edge prior and from the smoothing of the
cost.

## 4. Does the result transfer to other street grids?

**Motivated by:** every effect here comes from one network whose road-class mix and signal layout drive the
mechanism (RQ5). Midtown Manhattan (a dense one-way grid with signals at nearly every junction) and Downtown Brooklyn
are built and validated in `data/networks/` but were not used.

**Study:** repeat PC2, PC3 and the RQ5 analysis on both networks (docs/SPECIFICATION.md 4.8, Tier 2), including
leave-one-network-out forecaster transfer.

## 5. How do the benefit and the displacement scale with compliance?

**Motivated by:** all results assume that every driver follows the eco-route (`docs/LIMITATIONS.md` item 6), and the
reduction comes from moving many vehicle-hours between road classes (RQ5).

**Study:** the compliance sweep of docs/SPECIFICATION.md 4.8 (10, 25, 50 and 100 percent), reporting total NOx, residential NOx
and travel time for compliant and non-compliant drivers separately.
