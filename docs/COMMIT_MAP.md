# Commit map

The git history was rewritten on 2026-11-23 (`docs/DEVIATIONS.md` #25). File contents, commit dates and tags are
unchanged except as that entry states, but every commit hash changed. Hashes cited before that date (run records
`results/runs/*/*/run.json`, model `train_manifest.json` files, `STATUS.md`, `docs/DEVIATIONS.md`) are the old
ones; the first table maps each to its hash after that rewrite. The second table maps those hashes, and the
last commit of that rewrite, to the hashes in this repository (`docs/DEVIATIONS.md` #26).

| Date | Old | New | Subject |
|---|---|---|---|
| 2026-11-15 | `032a0ec` | `6848b5d` | M0: repo scaffold, environment, doctor, legacy audit and citation check |
| 2026-11-15 | `dd26233` | `c1c4a25` | M1/M2: OSM fetch, Web-Wizard network build and validation, Flushing and smoke scenarios, fleet and demand generation |
| 2026-11-15 | `1009485` | `b757ab3` | M2/M3: calibrated demand levels, simulation harness, six controllers, experiment executor, tests |
| 2026-11-15 | `6edda3b` | `d7ad5a6` | M4/M5: legacy RF replication, pilot and dataset configs, stats and power, forecaster training and evaluation, document renderers |
| 2026-11-15 | `3b7f87f` | `557df78` | M5: forecaster train/select commands, model card, executor memory limits, baseline fallback |
| 2026-11-15 | `ae7078c` | `8c2dac8` | M5-M7: analysis (confirmatory, spatial, figures, claims), paper macros, executor disk/memory guards, CPU time per run, citation ledger |
| 2026-11-15 | `44b6bb6` | `99154da` | M9 skeleton: paper text with generated macros, verified bibliography; status update |
| 2026-11-15 | `32784b8` | `aafca12` | STATUS: relative path in the launch snippet |
| 2026-11-15 | `7a584c7` | `0a3953b` | M9: interview FAQ renderer; precise wording on the legacy routing call |
| 2026-11-15 | `dc63dd1` | `beeb734` | M1: optional largest-SCC pass, Midtown box enlarged (DEVIATIONS 10-11); first Midtown build report |
| 2026-11-15 | `f0ae9a4` | `56b4831` | M4: device-equivalent travel time in the effort controllers (DEVIATIONS 12) after the alpha = 0 sanity gate failed; first pilot analysis outputs |
| 2026-11-15 | `cbd39c0` | `5b405fd` | M4 (G4): travel-time-weights router for the effort controllers (DEVIATIONS 13); alpha = 0 sanity passes; pilot complete, n = 60 |
| 2026-11-15 | `b6bd99f` | `148b117` | M5: prereg freeze command (confirmatory config from the selection, analysis-code hash); training progress log; manifest leakage test; arXiv bundle script |
| 2026-11-15 | `d50f287` | `2031461` | M9: verify-all (section 9 end to end, incl. a clean clone in a path with a space) and paper commands; protocol constants in main.tex come from macros |
| 2026-11-15 | `67ab7ca` | `3348d47` | M5: r forecaster on its own scale (DEVIATIONS 14); calibration metrics in the model card; first gbm_v1 kept as rejected evidence; executor --controllers filter |
| 2026-11-15 | `084fe36` | `5db4052` | M5: STATUS for the retrain and validation pass 1 |
| 2026-11-15 | `6978c10` | `3f99b80` | M5: STATUS: jobs stopped for a PC shutdown; resume commands |
| 2026-11-16 | `a67076b` | `1f8e27d` | M5: STATUS: jobs relaunched |
| 2026-11-16 | `3e491e0` | `7537872` | M5: memory guard on physical RAM with a reserve, and a launch gate that holds runs when RAM is short (after the PC crash of 2026-11-16); dtbk OSM extract |
| 2026-11-16 | `5bc63ae` | `322364c` | M5: legacy RF served as a shared memory-mapped compact forest (identical predictions: synthetic, 100k records, pilot rerun); memory gate with a batch budget shared by all pools; dtbk box enlarged (DEVIATIONS 15) |
| 2026-11-16 | `20fc9c2` | `5f5fb7a` | M5: legacy rerun check with peak memory (identical results, 1.1 GB private); legacy_ml memory estimate 1.4 GB |
| 2026-11-16 | `0d62a40` | `105abea` | M5 (model freeze): gbm_v1 with r on its own scale; calibrated r forecast (mean ratio 1.001, slope 1.007) without skill over the per-edge historical mean; v and hotspot skill over every baseline; frozen binary committed |
| 2026-11-16 | `b72fdad` | `f1568f9` | M5: OSM fetch reuses a frozen extract only for the same box (the dtbk re-fetch had silently kept the old box); DESIGN C5 memory note; STATUS: validation relaunched |
| 2026-11-16 | `fbda0fd` | `241fd5e` | M5: equivalence wording takes the margin from the config (was typed as 2%); analyze rehearsed end to end on relabelled pilot runs before the freeze |
| 2026-11-16 | `4d5b3b5` | `5b12d6d` | M5: preregistration and paper state the power at the chosen n and the effect and margin with 80% power (computed at the freeze with the pilot's simulation) |
| 2026-11-16 | `d014f9b` | `faa8d7e` | M5: analysis-code hash reads CRLF as LF, so a Windows checkout and a clean clone give the same hash |
| 2026-11-16 | `26e9fd1` | `c6f404d` | M5: the freeze is enforced: analysis.json records the analysis-code hash against the frozen one; verify-all checks the prereg tag predates every confirmatory run and that any later analysis change is in DEVIATIONS.md |
| 2026-11-16 | `256eabb` | `b02396d` | M1: dtbk OSM extract re-fetched for the enlarged box (-74.005,40.675,-73.96,40.705); manifest hash updated |
| 2026-11-16 | `0a020b3` | `0a45786` | M6: preregistration frozen: alpha*_reactive = alpha*_ml = 0.75, eta = 1 (validation seeds, 612/612 runs); n = 60; confirmatory.yaml generated; analysis-code hash 09dbec7a |
| 2026-11-16 | `853db38` | `606ecdd` | M1: dtbk rebuilt for the enlarged box: every check passes except bbox_match (89.6% of lane-km inside, minimum 90%; two bridges and the Gowanus kept whole), DEVIATIONS #16; STATUS: prereg frozen, confirmatory running |
| 2026-11-16 | `7108647` | `58f24f2` | M1: dtbk bbox_match near-miss (89.6% inside, minimum 90%) accepted as a documented Tier-2 limitation (DEVIATIONS #16, LIMITATIONS 13); G1 closed |
| 2026-11-16 | `c5ba953` | `cba8d6d` | M6: confirmatory batch paused overnight at 20/1080 ; STATUS gives the resume step |
| 2026-11-17 | `b66be19` | `7f2cdc8` | M6: confirmatory batch resumed (1,060 runs left) |
| 2026-11-17 | `aa1610a` | `efe473c` | M9: one-page research summary and project page generated by `paper` (wording fixed before the confirmatory results; at most 450 words for every outcome pattern, tested); kept outside the frozen analysis package |
| 2026-11-17 | `1d6f06f` | `518b774` | M9: TeX engine in place (tectonic 0.17.0 in the gitignored tools/, hash-checked; bundle cache kept in tools/); arXiv bundler compiles its own main.bbl, which the tectonic build discards |
| 2026-11-17 | `727a0ff` | `2930f07` | M6: STATUS: TeX engine ready for M9 |
| 2026-11-17 | `12c18b3` | `4cd3a93` | M7: frozen analysis of the confirmatory runs (1,080/1,080 done, verified, 0 failed; prereg check passes); generated claims, figures, macros, summary, project page and FAQ, unedited, before the adversarial review |
| 2026-11-17 | `41c87da` | `2bd910a` | M7: adversarial review answered (DEVIATIONS #17-#20); paused overnight before the test-seed forecast evaluation |
| 2026-11-18 | `c1009c7` | `5ae37b9` | M9: paper proofread and README updated; analyze-pilot can no longer overwrite the frozen preregistration; paused again before the forecast evaluation finished |
| 2026-11-19 | `fc892fd` | `ed061ec` | M8: street-coding sensitivity experiment frozen before its runs (DEVIATIONS #21; docs/SENSITIVITY_PLAN.md) |
| 2026-11-19 | `f46d5aa` | `a35ad15` | M7: held-out forecast evaluation on the test seeds (360 runs); claims, paper and documents regenerated |
| 2026-11-19 | `f3f9ac5` | `a388589` | M8: paused the sensitivity batch overnight at 343/540 ; README lists the sensitivity commands; STATUS gives the resume steps |
| 2026-11-20 | `c935078` | `7add258` | M8/M9: street-coding sensitivity results; paper, summary, project page and FAQ report them; gui command; verify-all passes |
| 2026-11-20 | `b8c1da3` | `c836d53` | M9: doctor's Overpass check informational while every OSM extract is frozen and verified (decision; DEVIATIONS #22); Definition of Done complete |
| 2026-11-20 | `e254807` | `0dd36dc` | M9: the paper as a journal-style preprint and as an IEEE conference paper, generated from the same results; technical report v1.0 archived (DEVIATIONS #23) |
| 2026-11-21 | `d4425b5` | `2f462d0` | M9: Billy M. Kyaw added as co-author to every paper version  |
| 2026-11-21 | `40bd44c` | `54b6b3f` | M9: Billy M. Kyaw credited in the application documents; "we" for the joint work ( DEVIATIONS #24) |
| 2026-11-21 | `3a31a7e` | `e5cbc6b` | M9: arXiv package of the journal preprint (not submitted) |
| 2026-11-21 | `289c528` | `e2a0d41` | Initial commit |
| 2026-11-21 | `753fe64` | `9a90662` | M9: LICENSE names both authors; OPEN_ITEMS and STATUS reflect the GitHub remote |
| 2026-11-21 | `deb7759` | `9b44cf2` | M9: merge GitHub's initial commit; keep the project's MIT license (decision, 2026-11-21) |
| 2026-11-21 | `92a2808` | `1a81414` | M9: both authors in the repository metadata: README, pyproject.toml, new CITATION.cff  |
| 2026-11-22 | `2da79ef` | `7382eb2` | M9: IEEE conference version completed to the preprint's standard  |
| 2026-11-23 | `630240d` | `4f9ccdb` | M9: README project history: the 2024 course project, the audit, the rebuild and the network-coding check  |

## Hashes in this repository

Old is the hash after the rewrite in the table above. New is the hash in this repository.

| Date | Old | New | Subject |
|---|---|---|---|
| 2026-11-15 | `d7ad5a6` | `068b239` | M4/M5: legacy RF replication, pilot and dataset configs, stats and power, forecaster training and evaluation, document renderers |
| 2026-11-15 | `5db4052` | `096d8b2` | M5: STATUS for the retrain and validation pass 1 |
| 2026-11-15 | `2031461` | `1e8f6fa` | M9: verify-all (section 9 end to end, incl. a clean clone in a path with a space) and paper commands; protocol constants in main.tex come from macros |
| 2026-11-15 | `aafca12` | `35fd2c2` | STATUS: relative path in the launch snippet |
| 2026-11-15 | `3348d47` | `38ebebe` | M5: r forecaster on its own scale (DEVIATIONS 14); calibration metrics in the model card; first gbm_v1 kept as rejected evidence; executor --controllers filter |
| 2026-11-15 | `5b405fd` | `4de91fd` | M4 (G4): travel-time-weights router for the effort controllers (DEVIATIONS 13); alpha = 0 sanity passes; pilot complete, n = 60 |
| 2026-11-15 | `8c2dac8` | `65bfe0d` | M5-M7: analysis (confirmatory, spatial, figures, claims), paper macros, executor disk/memory guards, CPU time per run, citation ledger |
| 2026-11-15 | `3f99b80` | `84833a9` | M5: STATUS: jobs stopped for a PC shutdown; resume commands |
| 2026-11-15 | `b757ab3` | `99f8abb` | M2/M3: calibrated demand levels, simulation harness, six controllers, experiment executor, tests |
| 2026-11-15 | `56b4831` | `a82b180` | M4: device-equivalent travel time in the effort controllers (DEVIATIONS 12) after the alpha = 0 sanity gate failed; first pilot analysis outputs |
| 2026-11-15 | `beeb734` | `a91bbff` | M1: optional largest-SCC pass, Midtown box enlarged (DEVIATIONS 10-11); first Midtown build report |
| 2026-11-15 | `c1c4a25` | `b184da0` | M1/M2: OSM fetch, Web-Wizard network build and validation, Flushing and smoke scenarios, fleet and demand generation |
| 2026-11-15 | `99154da` | `d6d940a` | M9 skeleton: paper text with generated macros, verified bibliography; status update |
| 2026-11-15 | `0a3953b` | `dd2b8b7` | M9: interview FAQ renderer; precise wording on the legacy routing call |
| 2026-11-15 | `6848b5d` | `e4c59ac` | M0: repo scaffold, environment, doctor, legacy audit and citation check |
| 2026-11-15 | `148b117` | `f4018c1` | M5: prereg freeze command (confirmatory config from the selection, analysis-code hash); training progress log; manifest leakage test; arXiv bundle script |
| 2026-11-15 | `557df78` | `f86bc5a` | M5: forecaster train/select commands, model card, executor memory limits, baseline fallback |
| 2026-11-16 | `b02396d` | `0214e47` | M1: dtbk OSM extract re-fetched for the enlarged box (-74.005,40.675,-73.96,40.705); manifest hash updated |
| 2026-11-16 | `faa8d7e` | `06e7603` | M5: analysis-code hash reads CRLF as LF, so a Windows checkout and a clean clone give the same hash |
| 2026-11-16 | `c6f404d` | `0e84eae` | M5: the freeze is enforced: analysis.json records the analysis-code hash against the frozen one; verify-all checks the prereg tag predates every confirmatory run and that any later analysis change is in DEVIATIONS.md |
| 2026-11-16 | `0a45786` | `0ec8e30` | M6: preregistration frozen: alpha*_reactive = alpha*_ml = 0.75, eta = 1 (validation seeds, 612/612 runs); n = 60; confirmatory.yaml generated; analysis-code hash 09dbec7a |
| 2026-11-16 | `7537872` | `223a0a5` | M5: memory guard on physical RAM with a reserve, and a launch gate that holds runs when RAM is short (after the PC crash of 2026-11-16); dtbk OSM extract |
| 2026-11-16 | `5b12d6d` | `54e3768` | M5: preregistration and paper state the power at the chosen n and the effect and margin with 80% power (computed at the freeze with the pilot's simulation) |
| 2026-11-16 | `f1568f9` | `62bcd58` | M5: OSM fetch reuses a frozen extract only for the same box (the dtbk re-fetch had silently kept the old box); DESIGN C5 memory note; STATUS: validation relaunched |
| 2026-11-16 | `cba8d6d` | `7f4c5a9` | M6: confirmatory batch paused overnight at 20/1080; STATUS gives the resume step |
| 2026-11-16 | `322364c` | `8dfe425` | M5: legacy RF served as a shared memory-mapped compact forest (identical predictions: synthetic, 100k records, pilot rerun); memory gate with a batch budget shared by all pools; dtbk box enlarged (DEVIATIONS 15) |
| 2026-11-16 | `1f8e27d` | `8e292de` | M5: STATUS: jobs relaunched |
| 2026-11-16 | `241fd5e` | `96ab4d9` | M5: equivalence wording takes the margin from the config (was typed as 2%); analyze rehearsed end to end on relabelled pilot runs before the freeze |
| 2026-11-16 | `606ecdd` | `b83de9d` | M1: dtbk rebuilt for the enlarged box: every check passes except bbox_match (89.6% of lane-km inside, minimum 90%; two bridges and the Gowanus kept whole), DEVIATIONS #16; STATUS: prereg frozen, confirmatory running |
| 2026-11-16 | `58f24f2` | `beda7bb` | M1: dtbk bbox_match near-miss (89.6% inside, minimum 90%) accepted as a documented Tier-2 limitation (DEVIATIONS #16, LIMITATIONS 13); G1 closed |
| 2026-11-16 | `5f5fb7a` | `c801b22` | M5: legacy rerun check with peak memory (identical results, 1.1 GB private); legacy_ml memory estimate 1.4 GB |
| 2026-11-16 | `105abea` | `f1cc9c4` | M5 (model freeze): gbm_v1 with r on its own scale; calibrated r forecast (mean ratio 1.001, slope 1.007) without skill over the per-edge historical mean; v and hotspot skill over every baseline; frozen binary committed |
| 2026-11-17 | `4cd3a93` | `25099ce` | M7: frozen analysis of the confirmatory runs (1,080/1,080 done, verified, 0 failed; prereg check passes); generated claims, figures, macros, summary, project page and FAQ, unedited, before the adversarial review |
| 2026-11-17 | `518b774` | `2e257ae` | M9: TeX engine in place (tectonic 0.17.0 in the gitignored tools/, hash-checked; bundle cache kept in tools/); arXiv bundler compiles its own main.bbl, which the tectonic build discards |
| 2026-11-17 | `7f2cdc8` | `53a3ed6` | M6: confirmatory batch resumed (1,060 runs left) |
| 2026-11-17 | `2bd910a` | `5be9e44` | M7: adversarial review answered (DEVIATIONS #17-#20); paused overnight before the test-seed forecast evaluation |
| 2026-11-17 | `efe473c` | `5e0ac52` | M9: one-page research summary and project page generated by `paper` (wording fixed before the confirmatory results; at most 450 words for every outcome pattern, tested); kept outside the frozen analysis package |
| 2026-11-17 | `2930f07` | `eb7d52c` | M6: STATUS: TeX engine ready for M9 |
| 2026-11-18 | `5ae37b9` | `331557f` | M9: paper proofread and README updated; analyze-pilot can no longer overwrite the frozen preregistration; paused again before the forecast evaluation finished |
| 2026-11-19 | `a388589` | `26474c3` | M8: paused the sensitivity batch overnight at 343/540; README lists the sensitivity commands; STATUS gives the resume steps |
| 2026-11-19 | `ed061ec` | `4543592` | M8: street-coding sensitivity experiment frozen before its runs (DEVIATIONS #21; docs/SENSITIVITY_PLAN.md) |
| 2026-11-19 | `a35ad15` | `9867bb6` | M7: held-out forecast evaluation on the test seeds (360 runs); claims, paper and documents regenerated |
| 2026-11-20 | `7add258` | `57c75a6` | M8/M9: street-coding sensitivity results; paper, summary, project page and FAQ report them; gui command; verify-all passes |
| 2026-11-20 | `0dd36dc` | `e76cc5f` | M9: the paper as a journal-style preprint and as an IEEE conference paper, generated from the same results; technical report v1.0 archived (DEVIATIONS #23) |
| 2026-11-20 | `c836d53` | `f71ebd5` | M9: doctor's Overpass check informational while every OSM extract is frozen and verified (decision; DEVIATIONS #22); Definition of Done complete |
| 2026-11-21 | `2f462d0` | `2bb3949` | M9: Billy M. Kyaw added as co-author to every paper version |
| 2026-11-21 | `1a81414` | `332a77f` | M9: both authors in the repository metadata: README, pyproject.toml, new CITATION.cff |
| 2026-11-21 | `54b6b3f` | `8b3b021` | M9: Billy M. Kyaw credited in the application documents; "we" for the joint work (DEVIATIONS #24) |
| 2026-11-21 | `e5cbc6b` | `a5e14fa` | M9: arXiv package of the journal preprint (not submitted) |
| 2026-11-21 | `9a90662` | `b3eb938` | M9: LICENSE names both authors; OPEN_ITEMS and STATUS reflect the GitHub remote |
| 2026-11-21 | `9b44cf2` | `d5a6e11` | M9: merge GitHub's initial commit; keep the project's MIT license (decision, 2026-11-21) |
| 2026-11-21 | `e2a0d41` | `e2a0d41` | Initial commit |
| 2026-11-22 | `7382eb2` | `bc9da4b` | M9: IEEE conference version completed to the preprint's standard |
| 2026-11-23 | `4f9ccdb` | `3283700` | M9: README project history: the 2024 course project, the audit, the rebuild and the network-coding check |
| 2026-11-23 | `48e0f97` | `dbc8730` | M9: history rewritten before the repository is published again; old to new commit hashes in docs/COMMIT_MAP.md (DEVIATIONS #25, requested) |

## Hashes after the 2026-11-25 republication

The history was rewritten a third time on 2026-11-25, when the repository was republished (`docs/DEVIATIONS.md` #30).
Old is the hash before that rewrite and New is the hash in this repository.

| Date | Old | New | Subject |
|---|---|---|---|
| 2026-11-15 | `e4c59ac` | `ed9bcc9` | M0: repo scaffold, environment, doctor, legacy audit and citation check |
| 2026-11-15 | `b184da0` | `81de80c` | M1/M2: OSM fetch, Web-Wizard network build and validation, Flushing and smoke scenarios, fleet and demand generation |
| 2026-11-15 | `99f8abb` | `9533ce0` | M2/M3: calibrated demand levels, simulation harness, six controllers, experiment executor, tests |
| 2026-11-15 | `068b239` | `49f9558` | M4/M5: legacy RF replication, pilot and dataset configs, stats and power, forecaster training and evaluation, document renderers |
| 2026-11-15 | `f86bc5a` | `d599d6c` | M5: forecaster train/select commands, model card, executor memory limits, baseline fallback |
| 2026-11-15 | `65bfe0d` | `d2c01d7` | M5-M7: analysis (confirmatory, spatial, figures, claims), paper macros, executor disk/memory guards, CPU time per run, citation ledger |
| 2026-11-15 | `d6d940a` | `b383c26` | M9 skeleton: paper text with generated macros, verified bibliography; status update |
| 2026-11-15 | `35fd2c2` | `e64b6ca` | STATUS: relative path in the launch snippet |
| 2026-11-15 | `dd2b8b7` | `13b8ea2` | M9: interview FAQ renderer; precise wording on the legacy routing call |
| 2026-11-15 | `a91bbff` | `3b3708e` | M1: optional largest-SCC pass, Midtown box enlarged (DEVIATIONS 10-11); first Midtown build report |
| 2026-11-15 | `a82b180` | `9540b9d` | M4: device-equivalent travel time in the effort controllers (DEVIATIONS 12) after the alpha = 0 sanity gate failed; first pilot analysis outputs |
| 2026-11-15 | `4de91fd` | `cae5f98` | M4 (G4): travel-time-weights router for the effort controllers (DEVIATIONS 13); alpha = 0 sanity passes; pilot complete, n = 60 |
| 2026-11-15 | `f4018c1` | `acab79b` | M5: prereg freeze command (confirmatory config from the selection, analysis-code hash); training progress log; manifest leakage test; arXiv bundle script |
| 2026-11-15 | `1e8f6fa` | `e63eef6` | M9: verify-all (section 9 end to end, incl. a clean clone in a path with a space) and paper commands; protocol constants in main.tex come from macros |
| 2026-11-15 | `38ebebe` | `84e79df` | M5: r forecaster on its own scale (DEVIATIONS 14); calibration metrics in the model card; first gbm_v1 kept as rejected evidence; executor --controllers filter |
| 2026-11-15 | `096d8b2` | `b30ee84` | M5: STATUS for the retrain and validation pass 1 |
| 2026-11-15 | `84833a9` | `e3ff37f` | M5: STATUS: jobs stopped for a PC shutdown; resume commands |
| 2026-11-16 | `8e292de` | `4ea0063` | M5: STATUS: jobs relaunched |
| 2026-11-16 | `223a0a5` | `ead6321` | M5: memory guard on physical RAM with a reserve, and a launch gate that holds runs when RAM is short (after the PC crash of 2026-11-16); dtbk OSM extract |
| 2026-11-16 | `8dfe425` | `96f9129` | M5: legacy RF served as a shared memory-mapped compact forest (identical predictions: synthetic, 100k records, pilot rerun); memory gate with a batch budget shared by all pools; dtbk box enlarged (DEVIATIONS 15) |
| 2026-11-16 | `c801b22` | `5326ace` | M5: legacy rerun check with peak memory (identical results, 1.1 GB private); legacy_ml memory estimate 1.4 GB |
| 2026-11-16 | `f1cc9c4` | `5afce79` | M5 (model freeze): gbm_v1 with r on its own scale; calibrated r forecast (mean ratio 1.001, slope 1.007) without skill over the per-edge historical mean; v and hotspot skill over every baseline; frozen binary committed |
| 2026-11-16 | `62bcd58` | `6f1741b` | M5: OSM fetch reuses a frozen extract only for the same box (the dtbk re-fetch had silently kept the old box); DESIGN C5 memory note; STATUS: validation relaunched |
| 2026-11-16 | `96ab4d9` | `aae78e5` | M5: equivalence wording takes the margin from the config (was typed as 2%); analyze rehearsed end to end on relabelled pilot runs before the freeze |
| 2026-11-16 | `54e3768` | `09c671b` | M5: preregistration and paper state the power at the chosen n and the effect and margin with 80% power (computed at the freeze with the pilot's simulation) |
| 2026-11-16 | `06e7603` | `4b1f634` | M5: analysis-code hash reads CRLF as LF, so a Windows checkout and a clean clone give the same hash |
| 2026-11-16 | `0e84eae` | `6c3fffd` | M5: the freeze is enforced: analysis.json records the analysis-code hash against the frozen one; verify-all checks the prereg tag predates every confirmatory run and that any later analysis change is in DEVIATIONS.md |
| 2026-11-16 | `0214e47` | `d85a63d` | M1: dtbk OSM extract re-fetched for the enlarged box (-74.005,40.675,-73.96,40.705); manifest hash updated |
| 2026-11-16 | `0ec8e30` | `f894735` | M6: preregistration frozen: alpha*_reactive = alpha*_ml = 0.75, eta = 1 (validation seeds, 612/612 runs); n = 60; confirmatory.yaml generated; analysis-code hash 09dbec7a |
| 2026-11-16 | `b83de9d` | `8ea92c8` | M1: dtbk rebuilt for the enlarged box: every check passes except bbox_match (89.6% of lane-km inside, minimum 90%; two bridges and the Gowanus kept whole), DEVIATIONS #16; STATUS: prereg frozen, confirmatory running |
| 2026-11-16 | `beda7bb` | `be4e438` | M1: dtbk bbox_match near-miss (89.6% inside, minimum 90%) accepted as a documented Tier-2 limitation (DEVIATIONS #16, LIMITATIONS 13); G1 closed |
| 2026-11-16 | `7f4c5a9` | `8f2d87e` | M6: confirmatory batch paused overnight at 20/1080 ; STATUS gives the resume step |
| 2026-11-17 | `53a3ed6` | `2dd03bd` | M6: confirmatory batch resumed (1,060 runs left) |
| 2026-11-17 | `5e0ac52` | `ae6544e` | M9: one-page research summary and project page generated by `paper` (wording fixed before the confirmatory results; at most 450 words for every outcome pattern, tested); kept outside the frozen analysis package |
| 2026-11-17 | `2e257ae` | `1e55f76` | M9: TeX engine in place (tectonic 0.17.0 in the gitignored tools/, hash-checked; bundle cache kept in tools/); arXiv bundler compiles its own main.bbl, which the tectonic build discards |
| 2026-11-17 | `eb7d52c` | `c3a81cf` | M6: STATUS: TeX engine ready for M9 |
| 2026-11-17 | `25099ce` | `0fd3c9b` | M7: frozen analysis of the confirmatory runs (1,080/1,080 done, verified, 0 failed; prereg check passes); generated claims, figures, macros, summary, project page and FAQ, unedited, before the adversarial review |
| 2026-11-17 | `5be9e44` | `fbe3042` | M7: adversarial review answered (DEVIATIONS #17-#20); paused overnight before the test-seed forecast evaluation |
| 2026-11-18 | `331557f` | `7306f9f` | M9: paper proofread and README updated; analyze-pilot can no longer overwrite the frozen preregistration; paused again before the forecast evaluation finished |
| 2026-11-19 | `4543592` | `3239b55` | M8: street-coding sensitivity experiment frozen before its runs (DEVIATIONS #21; docs/SENSITIVITY_PLAN.md) |
| 2026-11-19 | `9867bb6` | `3ca67e3` | M7: held-out forecast evaluation on the test seeds (360 runs); claims, paper and documents regenerated |
| 2026-11-19 | `26474c3` | `ad02e87` | M8: paused the sensitivity batch overnight at 343/540 ; README lists the sensitivity commands; STATUS gives the resume steps |
| 2026-11-20 | `57c75a6` | `065480e` | M8/M9: street-coding sensitivity results; paper, summary, project page and FAQ report them; gui command; verify-all passes |
| 2026-11-20 | `f71ebd5` | `1e18308` | M9: doctor's Overpass check informational while every OSM extract is frozen and verified (decision; DEVIATIONS #22); Definition of Done complete |
| 2026-11-20 | `e76cc5f` | `6d7593e` | M9: the paper as a journal-style preprint and as an IEEE conference paper, generated from the same results; technical report v1.0 archived (DEVIATIONS #23) |
| 2026-11-21 | `2bb3949` | `c8ae9ba` | M9: Billy M. Kyaw added as co-author to every paper version |
| 2026-11-21 | `8b3b021` | `398bbdb` | M9: Billy M. Kyaw credited in the application documents; "we" for the joint work ( DEVIATIONS #24) |
| 2026-11-21 | `a5e14fa` | `ce303e5` | M9: arXiv package of the journal preprint (not submitted) |
| 2026-11-21 | `e2a0d41` | `e2a0d41` | Initial commit |
| 2026-11-21 | `b3eb938` | `cb89f4c` | M9: LICENSE names both authors; OPEN_ITEMS and STATUS reflect the GitHub remote |
| 2026-11-21 | `d5a6e11` | `36ee1a7` | M9: merge GitHub's initial commit; keep the project's MIT license (decision, 2026-11-21) |
| 2026-11-21 | `332a77f` | `68cbe33` | M9: both authors in the repository metadata: README, pyproject.toml, new CITATION.cff |
| 2026-11-22 | `bc9da4b` | `e9a4c35` | M9: IEEE conference version completed to the preprint's standard |
| 2026-11-23 | `3283700` | `1bc41ce` | M9: README project history: the 2024 course project, the audit, the rebuild and the network-coding check |
| 2026-11-23 | `dbc8730` | `6751fb1` | M9: history rewritten before the repository is published again; old to new commit hashes in docs/COMMIT_MAP.md (DEVIATIONS #25, requested) |
| 2026-11-23 | `27027e6` | `8f597ab` | M9: record the specification path and the recomputed analysis hashes |
| 2026-11-23 | `6e8b727` | `fbe7cc9` | M9: the remote note matches the unpublished rewrite |
| 2026-11-24 | `12fe30d` | `6b00fc9` | M9: record publication to the recreated repository |
| 2026-11-25 | `ed62613` | `a59805a` | Release cleanup: AI-use disclosure, data license, redactions |
| 2026-11-25 | `3a5fa31` | `25b4a2f` | Stop tracking generated summary documents and the arXiv bundle; rebuild paper PDFs |
