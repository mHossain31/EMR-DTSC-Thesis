# Citation ledger

Every work cited in `paper/refs.bib`, the README or `application/` must appear in part A with a verified
identifier (DOI, arXiv id or stable URL), the date it was checked, what was read, and the exact claim it supports.
A work may only be cited for what was read. `tests/unit/test_hygiene.py` checks that every `refs.bib` key
appears here.

## A. Verified citations used in this project

| Key | Work | Identifier | Checked | Read | Supports |
|---|---|---|---|---|---|
| lopez2018sumo | Lopez, Wiessner, Behrisch, Bieker-Walz, Erdmann, Flotterod et al., "Microscopic Traffic Simulation using SUMO", IEEE ITSC 2018, pp. 2575-2582 | doi:10.1109/ITSC.2018.8569938 | 2026-11-15 (Crossref) | metadata | SUMO is the simulator used |
| ahn2008route | Ahn and Rakha, "The effects of route choice decisions on vehicle energy consumption and emissions", Transp. Res. D 13(3):151-167, 2008 | doi:10.1016/j.trd.2008.01.005 | 2026-11-15 (Crossref; abstract-level summaries at swov.nl and peeref.com) | abstract-level summary | route choice changes energy use and emissions; the faster route is not always the lower-emission one |
| ahn2013ecorouting | Ahn and Rakha, "Network-wide impacts of eco-routing strategies: A large-scale case study", Transp. Res. D 25:119-130, 2013 | doi:10.1016/j.trd.2013.09.006 | 2026-11-15 (Crossref; summary in a Rakha project report found by web search) | summary only | eco-routing has been evaluated network-wide in simulation (INTEGRATION; Cleveland and Columbus); savings depend on network and market penetration |
| fazzini2022signals | Fazzini, Torre, Rizza, Petracchini, "Effects of Smart Traffic Signal Control on Air Quality", Front. Sustain. Cities 4:756539, 2022 | doi:10.3389/frsc.2022.756539 | 2026-11-15 (Crossref abstract) | abstract | multi-agent RL signal control evaluated for its effect on air quality |
| haydari2021signals | Haydari, Zhang, Chuah, Ghosal, "Impact of Deep RL-based Traffic Signal Control on Air Quality", IEEE VTC2021-Spring, pp. 1-6 | doi:10.1109/VTC2021-Spring51267.2021.9448639 | 2026-11-15 (Crossref; abstract at itspubs.ucdavis.edu, id 3693) | abstract | deep RL signal control compared with max-pressure on fuel and CO2 in simulated networks |
| du2021rerouting | Du, Chen, Dong, Chen, Fu, Labi, "Urban traffic dynamic rerouting framework: A DRL-based model with fog-cloud architecture", arXiv:2110.05532, 2021 | arXiv:2110.05532 | 2026-11-14 (arXiv abstract page) | abstract | learning-based dynamic rerouting aimed at travel efficiency (speed), not emissions |
| wilcoxon1945 | Wilcoxon, "Individual Comparisons by Ranking Methods", Biometrics Bulletin 1(6):80-83, 1945 | doi:10.2307/3001968 | 2026-11-15 (Crossref) | metadata | the signed-rank test |
| schuirmann1987tost | Schuirmann, "A comparison of the Two One-Sided Tests Procedure and the Power Approach for assessing the equivalence of average bioavailability", J. Pharmacokinet. Biopharm. 15(6):657-680, 1987 | doi:10.1007/BF01068419 | 2026-11-15 (Crossref) | metadata | the two one-sided tests (TOST) procedure for equivalence |
| efron1987bca | Efron, "Better Bootstrap Confidence Intervals", JASA 82(397):171-185, 1987 | doi:10.1080/01621459.1987.10478410 | 2026-11-15 (Crossref) | metadata | BCa bootstrap intervals |
| holm1979 | Holm, "A Simple Sequentially Rejective Multiple Test Procedure", Scand. J. Stat. 6(2):65-70, 1979 | https://www.jstor.org/stable/4615733 (no DOI resolves on Crossref) | 2026-11-15 (JSTOR record and catalogue entries found by web search) | abstract-level summary | the Holm step-down procedure controls the familywise error rate |
| ke2017lightgbm | Ke, Meng, Finley, Wang, Chen, Ma, Ye, Liu, "LightGBM: A Highly Efficient Gradient Boosting Decision Tree", NeurIPS 2017 | https://papers.nips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html | 2026-11-15 (proceedings page metadata) | metadata | the gradient-boosting library used |

A source is cited only for the claim in its row; rows marked "summary" or "metadata" support no claim about the
source's results beyond what is written there. Candidates from docs/SPECIFICATION.md Appendix D (Du et al. 2021;
Fazzini et al. 2022; Haydari et al. 2021; Ahn and Rakha 2008, 2013) are listed in part C until read.

## B. Legacy references (checked 2026-11-14; none reused)

The legacy report (PDF page 48) lists four works and the slides (PDF page 7) cite "Dong & Javid et al. (2022)".
Each was searched by exact title in the Crossref API (`query.bibliographic`), by title and author in a web
search, and, where the entry gives a volume and article or page locator, by looking up what Crossref lists at
that locator.

| Legacy entry | Title search | Locator check | Status |
|---|---|---|---|
| Jiang, D., et al. (2022). "A Bibliometric Study of Machine Learning Applications in Air Pollution Research." *Environmental Monitoring and Assessment*, 192(1), 101. | No match in Crossref or web search. The closest bibliometric work found is Guo et al. 2022, *Frontiers in Public Health*, doi:10.3389/fpubh.2022.933665 (not read; not a match). | Crossref lists *EMA* vol. 192 article 101 as "Dynamics of (total and methyl) mercury in sediment, fish, and crocodiles in an Amazonian Lake ..." (Gomes et al., doi:10.1007/s10661-020-8066-z). Volume 192 is a 2020 volume, not 2022. | not found; locator points to an unrelated paper |
| Lin, H., et al. (2020). "Predicting Urban Traffic Emissions using SUMO and Taxi Trajectory Data." *Transportation Research Part D*, 85, 102416. | No match. The closest topical work is Liu, Han, Chen and Ong (TR-C 2019; arXiv:1809.10834), which uses taxi GPS data but not SUMO. | Article number 102416 in *TR-D* is doi:10.1016/j.trd.2020.102416, "Evaluating impacts of intelligent transit priority on intersection energy and emissions" (Liu et al.), in volume 86, not 85. | not found; locator points to an unrelated paper |
| Javid, A., et al. (2022). "Traffic Signal Optimization for Air Pollution Control in Urban Areas." *Sustainable Cities and Society*, 72, 103045. | No match. | doi:10.1016/j.scs.2021.103045 is "Influence of urban morphological characteristics on thermal environment" (Yang et al.), *SCS* vol. 72 (2021). | not found; locator points to an unrelated paper |
| Dong, X., et al. (2021). "Dynamic Vehicle Rerouting for Urban Pollution Reduction Using Reinforcement Learning." *Journal of Intelligent Transportation Systems*, 25(3), 235-251. | No match. The nearest work is Du, Chen, Dong, Chen, Fu, Labi, "Urban traffic dynamic rerouting framework: A DRL-based model with fog-cloud architecture", arXiv:2110.05532 (2021). Its abstract concerns congestion and travel speed, not pollution; its first author is Du, and its co-author is Jiqian Dong, not "X. Dong". | Crossref lists *JITS* 25(3) articles at pp. 249-262, 263-280 and 293-312 (none on rerouting or pollution); the cited range 235-251 overlaps pp. 249-262 (Yao et al., "Clustering driver behavior using dynamic time warping and hidden Markov model"). | not found; arXiv:2110.05532 is a different paper on a different objective |
| Slides: "Dong & Javid et al. (2022)" credited with "reduction in pollutant levels by up to 20%" | Merges two report entries with different years; the report attributes 15% (rerouting) to Dong 2021 and 20% (signals plus rerouting) to Javid 2022. | - | inconsistent with the report; neither source found |

The report's text also carries "(MDPI)" and "(SpringerLink)" tags after these citations (PDF page 7), which match
no entry in its reference list.

## C. Appendix D candidates (all now in part A)

| Work | Identifier |
|---|---|
| Du, Chen, Dong, Chen, Fu, Labi (2021), urban traffic dynamic rerouting with fog-cloud DRL | arXiv:2110.05532 (abstract read on 2026-11-14 for the legacy comparison only) |
| Fazzini, Torre, Rizza, Petracchini (2022), smart traffic signal control and air quality | doi:10.3389/frsc.2022.756539 |
| Haydari, Zhang, Chuah, Ghosal (2021), deep RL signal control and air quality | doi:10.1109/VTC2021-Spring51267.2021.9448639 |
| Ahn and Rakha (2008), route choice, energy and emissions | doi:10.1016/j.trd.2008.01.005 |
| Ahn and Rakha (2013), network-wide eco-routing case study | doi:10.1016/j.trd.2013.09.006 |
