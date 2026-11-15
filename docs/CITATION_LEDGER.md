# Citation ledger

Every work cited in `paper/refs.bib`, the README or `application/` must appear in part A with a verified
identifier (DOI, arXiv id or stable URL), the date it was checked, what was read, and the exact claim it supports.
A work may only be cited for what was read. `tests/unit/test_hygiene.py` checks that every `refs.bib` key
appears here.

## A. Verified citations used in this project

| Key | Work | Identifier | Checked | Read | Supports |
|---|---|---|---|---|---|

Part A is empty until sources are read for the paper (M9). Candidates from docs/SPECIFICATION.md Appendix D (Du et al. 2021;
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

## C. Candidates to read before citing (docs/SPECIFICATION.md Appendix D; existence noted, not yet read)

| Work | Identifier |
|---|---|
| Du, Chen, Dong, Chen, Fu, Labi (2021), urban traffic dynamic rerouting with fog-cloud DRL | arXiv:2110.05532 (abstract read on 2026-11-14 for the legacy comparison only) |
| Fazzini, Torre, Rizza, Petracchini (2022), smart traffic signal control and air quality | doi:10.3389/frsc.2022.756539 |
| Haydari, Zhang, Chuah, Ghosal (2021), deep RL signal control and air quality | doi:10.1109/VTC2021-Spring51267.2021.9448639 |
| Ahn and Rakha (2008), route choice, energy and emissions | doi:10.1016/j.trd.2008.01.005 |
| Ahn and Rakha (2013), network-wide eco-routing case study | doi:10.1016/j.trd.2013.09.006 |
