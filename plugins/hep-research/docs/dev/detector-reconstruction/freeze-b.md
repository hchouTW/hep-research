# Freeze B: what is frozen

Candidate for the user's word (v4 2.2; finish-plan D4 step 2; decision U6). **Not frozen** until decisions.md holds that word, in a
section "Freeze B" with the SHA-256 of this file. Written by the coordinator from the Freeze-B run's own records (collection job
7585958, `collect-7585958.out`), never from memory. After the word, any change to an item below is a return to Freeze B (v4 3.4: new
recipe hash, a new Freeze-B run on block 5, the user's word).

## The run

| Item | Value |
| --- | --- |
| Freeze-B run, block 2 | T07 7585954, T08 7585955, T09 step-1 array 7585956 (15 tasks), step-2 array 7585957 (13 tasks), collection 7585958; all 31 COMPLETED, collection `JOB RESULT PASS`, 2026-11-12 |
| Rate-check supplement | 7590984, read-only, PASS: "OK U_dev <= C (0.005) in all 12 bins of block 2" (decisions.md, "The Freeze-B run's rate check: a defect and its supplement") |
| Nodes | hpa-wn33 (29 jobs and tasks), hpa-wn34 (2) |
| Node class | AMD EPYC 9645 (U-W7), glibc 2.34, Python 3.13.18, numpy 2.4.6, scipy 1.17.1 (collection receipt) |
| Recipe commit and source manifest | commit of the recipes 5228a3e26655a97fcb9cecc9467c387ec691f5b5; git HEAD 5228a3e26655a97fcb9cecc9467c387ec691f5b5; manifest 915042c4f6521e4054b489e5e03e139ff56ac4b8caf6fc257e6c52f166d94143 (898 files) |
| Blocks | samples from block 2 only (T07 180,000 events, T08 45,000, T09 45,000, as v4 3.2); block 6 only for the generator checks and the fixed points |
| Billed cost | 39.67 CPU-hours (U-B9: 30 to 41) |

## Recipe identity: adapter manifests and recipe files

| Item | SHA-256 |
| --- | --- |
| adapters/acts-tracking manifest (56 files; proposal 2.1's command) | `fe80f264271ea4304e2e64403d41cb38ad2894c27192d169ae65383e135a0bd3` |
| adapters/calo-cluster manifest (17 files; proposal 2.1's command) | `cb0153ba5bffaa1af6de3b11a51d8b191e8460ef078a10556825fa213a999103` |
| adapters/photon-likelihood manifest (26 files; proposal 2.1's command) | `060e967a3e33381a732734181dc0820ad63619799d3ee2d4e77af2f86a7ed4eb` |
| adapters/acts-tracking/assets/native/track_finding.hpp | `4bc57f7c857ddeeb7aae82982204b9dd7cf5b20a45f8f866ed50d7cee1ba9b64` |
| adapters/acts-tracking/assets/native/track_finding.cpp | `a147d22eecf1f36a6aff57a14a7564d22ac0725c1df528c3fcc2cb20674132f3` |
| adapters/acts-tracking/assets/native/kalman_refit.hpp | `d658f54202c602901ec272a0753b983f21ef526fd469e26cc6304652db54b2af` |
| adapters/acts-tracking/assets/native/kalman_refit.cpp | `91e522553c8f17d1729537049edf79237fa8838cd3b0ad4f0fea7cc72682d85c` |
| adapters/acts-tracking/assets/native/acts_tracking_finder.cpp | `41e054448b79959ff1bbf318b30e6e0c32e618d889e8106785e1d70e85fc5130` |
| adapters/acts-tracking/assets/native/acts_tracking_driver.cpp | `d8371a043d5789553c32b094f9a5e542a2cb27e11f3d01cf638dfbeea6b014b2` |
| adapters/acts-tracking/assets/native/track_vertexing.cpp | `7f6209d57f1928ce93943faad9b06030150f30d5419f569cc8a66bd8d310896d` |
| adapters/acts-tracking/assets/native/track_vertexing.hpp | `ef0e68f29380818d2efffeebca75027720974ad412c0b7349b7653ce9969f7f2` |
| adapters/acts-tracking/assets/native/CMakeLists.txt | `cd548af18cb528a33c5a9fcba5595c87ddd176d5f5ab9e84bc3d1f119448f503` |
| adapters/photon-likelihood/assets/light_recipe/arrival_response.py | `fcbb347d6bb3c04e366a0f28cd0a6f95749ffe71213ab25898d370a170feb14a` |
| adapters/photon-likelihood/assets/light_recipe/charge_response.py | `d619b7411ec8b70c24074d2a6fe9ab98c0ab404f4469f70b6f9bbcc5d4d4cda8` |
| adapters/photon-likelihood/assets/light_recipe/configuration.py | `1a3cf42d34a3acd081cc5a15af531b42a900844f112ee999b15ce583b619022f` |
| adapters/photon-likelihood/assets/light_recipe/fit.py | `30d92e448e461084556364e4d2fd4e036c69142dc88b91f08dbf8acfff71a476` |
| adapters/photon-likelihood/assets/light_recipe/__init__.py | `9d16d3ba5ba96a7c0bb2a919b2b9db9ce48020e3f4ef0ccafd358472ac3dbe60` |
| adapters/photon-likelihood/assets/light_recipe/joint.py | `aa67f3c5d35f5eac7f7cf5ec4522fb7379ce705822c3ef61e4d80b89e324806e` |
| adapters/photon-likelihood/assets/light_recipe/light_model.py | `c716d4fccb73b75a711033f8cd45f2fbe9640e4483e3339fa74064fc2814552b` |
| adapters/photon-likelihood/assets/light_recipe/likelihood.py | `1e839b9dbbbe04e5867547b3eb8d86b6cbaef06a2ba2025d41d9acb580e1a084` |
| adapters/photon-likelihood/assets/light_recipe/multistart.py | `5953620f7aa3b3b886b67e440a4b1235f983b2c6dc663e03aaed2ce862461449` |
| adapters/photon-likelihood/assets/light_recipe/product.py | `8642c59a3bb7f4ca65a671ff388b7826b3c906e8e8ebe15e0974169051f1cee7` |
| adapters/photon-likelihood/assets/light_recipe/readout.py | `605debd51cb66dc266e16b56be08df7ef28479df577476d2ad531ea805d205ce` |
| adapters/photon-likelihood/assets/light_recipe/single_photon.py | `dad0238dafeecdfb5ee75e884f540930f3ad512606b06dd6305d7e75beb8b889` |
| adapters/photon-likelihood/assets/light_recipe/topology.py | `79dc45a9b800936dd3f8288ffbca040fa6ed0487eb38da55d290be8ee8ae802e` |
| adapters/photon-likelihood/assets/photon_likelihood.py | `8a4f4fd0e0f24231b56177693defa53c6514f578ded5ba46636c320562df07a6` |
| adapters/photon-likelihood/assets/t09-multistart-1.budget.json | `70220b7ddf1679d01d4a9c5397d1fdf124c6f0bd8ed4dca562d9c18e04180307` |
| adapters/photon-likelihood/assets/t09-sphere-1.configuration.json | `ce4f430756f8ea0be1ab1b08eb638f9c38bf305968aa2d6d4e743d5fc68a1508` |
| adapters/photon-likelihood/assets/t09-sphere-1-single-photon.configuration.json | `5aa052431facfd18c07e05d479b67fcfb717df4e3cd410c781f9d69a29daad98` |
| adapters/photon-likelihood/assets/t09-topology-2.budget.json | `104262a1bfb0f5403a075884d9acd5f5ccbf1fc012d5237b578297f4d98ed7df` |
| adapters/calo-cluster/assets/t08-grid-1.configuration.json | `5fbbea3b4ca81d962c5ca70fa024ddc82dd6e1d2f06e39b354fda56d26483723` |
| adapters/calo-cluster/assets/calo_recipe/clustering.py | `f59c804245d7e7295878fa5276438e3165f8c099d84ec4f80554d46883b066d5` |
| adapters/calo-cluster/assets/calo_recipe/cell_chain.py | `7a7c7ee5a1b713aa3de08ae9af4c3dbfcd3bec66748e78fc5cb924adeeccbc5d` |
| adapters/calo-cluster/assets/calo_recipe/configuration.py | `5e28a4b67f6ebc90faf2d12431a5c7d5dfecdfc39e2f0267063395b782af68ec` |
| T07 built binary acts_tracking_finder | `550d96832e7c38ca82b43720dae46878976a405dd87aa3d3c5c1735c1309e406` |
| T07 built binary acts_tracking_driver | `7556beb828f3a9029a79a34f41c938e7f9ff328281855800d21d655649ece958` |
| T07 built binary acts_truth_seeded_run | `1a6515960e8bb09a657534a518c09edc5d6b2b1c86aeec745a16b81f55a9654b` |
| T07 built binary t07_fixture_generator | `9c659896533aee1a324e6a8c4c808021f6cf45c2697ba3c0b72f3a4c88d54a47` |

## Full effective configuration and budgets (K10), by hash

| Recipe | Item | SHA-256 |
| --- | --- | --- |
| T07 CKF `reco.track.acts-ckf-planar/1` | configuration_sha256 (25 lines) | `2448d935fd8a20d8856be6772d7dfbaa774819f74a0a90d139cdc680531a3050` |
| T07 AMVF `reco.vertex.acts-amvf/1` | vertex_configuration_sha256 (41 lines) | `10a862639cdefff4734d0ed2e3338a5f1ada4a91be3c1d751e3663b989219849` |
| T07 CKF | t07-ckf-budget (listing kept, 6 lines) | `55fb16d9bf5979be63b3808eaa1811bdf4bdde6148e488d79e9a6ecbc906509f` |
| T07 AMVF | t07-vertex-budget (listing kept, 5 lines) | `16cb82242f194b44f1f9281c2687426cc3c747815b20dd6b5370be91339c2271` |
| T07 refit `reco.track.acts-kf-refit/1` | start_prior line (`start_prior -50 10 0.10000000000000001 1 1`) | `25cd896b5774d8ae744e82982240e2d6cc7c76e460be3812f88c11741f57a394` |
| T08 `reco.calo.cell-cluster/1` | configuration t08-grid-1 (budgets sharing_iterations 30, peaks_kept 2 inside) | `5fbbea3b4ca81d962c5ca70fa024ddc82dd6e1d2f06e39b354fda56d26483723` |
| T09 `reco.light.channel-likelihood/1` | configuration (listing kept, 14 lines) | `ea0e6756caf83a7058f948f398292c8b79fb39dc96a91968dd2fabfd54ea7b36` |
| T09 | budget (listing kept, 3 lines) | `031102272f2e6f888f51a1d5a9a82ea0e96f7d1e99556297fcacd81d3492638b` |
| T09 single-photon variant (v4 9.4, E1b) | configuration (listing kept, 13 lines) | `e3d815ab44a2d806071bad995c72b8860d84e4a53c5b9803ee89645b635c9206` |

## `r_dev` per noise bin, for test F2 (v4 8.3)

12,000 events per bin, block 2. `C` = 0.005 and `tau` = 0.0025 are Freeze A's, not set here. `U_dev <= C` in all 12 bins, so evaluation may start (v4 8.3).
The frozen values are the full-precision rate record `noise/noise-b2.rate.record` of job 7585954, SHA-256 `ebf2aa0e54de13c2626c20c4d0d1a997ddf6ea2694d1cbe7354b5e8e3a2deb73` (listed in that job's
`outputs.sha256`), which F2 reads by hash; the table rounds for reading only.

| Stratum | Level | Events | Events without tracks | n | k | DEFF_hat | r_dev | L_dev | U_dev |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | o1 | 12000 | 0 | 71954 | 0 | 1 | 0 | 0 | 0.0002496 |
| 1 | o2 | 12000 | 0 | 143889 | 0 | 1 | 0 | 0 | 0.0002496 |
| 2 | o3 | 12000 | 0 | 431414 | 0 | 1 | 0 | 0 | 0.0002496 |
| 3 | o1 | 12000 | 0 | 71956 | 0 | 1 | 0 | 0 | 0.0002496 |
| 4 | o2 | 12000 | 0 | 143908 | 0 | 1 | 0 | 0 | 0.0002496 |
| 5 | o3 | 12000 | 0 | 431431 | 2 | 0.99993 | 4.636e-06 | 8.237e-07 | 0.0002585 |
| 6 | o1 | 12000 | 0 | 71951 | 0 | 1 | 0 | 0 | 0.0002496 |
| 7 | o2 | 12000 | 0 | 143911 | 0 | 1 | 0 | 0 | 0.0002496 |
| 8 | o3 | 12000 | 0 | 431402 | 1 | 1.00001 | 2.318e-06 | 1.189e-07 | 0.0002541 |
| 9 | o1 | 12000 | 0 | 71952 | 0 | 1 | 0 | 0 | 0.0002496 |
| 10 | o2 | 12000 | 0 | 143885 | 0 | 1 | 0 | 0 | 0.0002496 |
| 11 | o3 | 12000 | 0 | 431429 | 0 | 1 | 0 | 0 | 0.0002496 |

## T07 recipe-dependent negative-case inputs (v4 11)

| File | SHA-256 |
| --- | --- |
| tests/adapters/data/t07-negative-cases/SHA256SUMS | `978853d24c34b15290619d2a8acbad3c2b138b4b142a99a3486f69a9a59207b2` |
| tests/adapters/data/t07-negative-cases/t07-negative-cases-1.json | `ff501223b08221b675e3402bba5e1ea54699c904900a721bf6df5b4bf4ad10c5` |
| tests/adapters/data/t07-negative-cases/t07-negative-cases-1.t07data | `06a7741a4fe0eb89bd412a53bc8c5c1fca668a8ed6cbc18ea129922d23dd6a9d` |
| adapters/acts-tracking/assets/fixture_tools/t07_negative_cases.py | `1146d94b20b3b405b4bb520d5e5cbc0aa0b524114fc70b1dbc4f29a4b889e595` |
| tests/adapters/test_acts_finding.py | `8133b94875b628faf575af552388eef783f69c8795b00d4e5616156d926676e0` |

## Recorded beside Freeze B, as information (U-B8; not v4 2.2 items)

| Item | SHA-256 |
| --- | --- |
| the T07 truth-seeded comparator binary acts_truth_seeded_run | `1a6515960e8bb09a657534a518c09edc5d6b2b1c86aeec745a16b81f55a9654b` |
| the T09 truth-start comparator | `6e49246bcd02d6a2931a0360c5b95cec1639f706ba694767485ba2b2689f275e` |
| The evaluation harness E6 (U-B8: built before Freeze B) | branch commit `0e310d34` (feature/detector-reconstruction; E6 code last changed in `d65323ee`, fix/integration); modules: t04_evaluation_core.py `265eb12426f0e16ce3a0cb0caf9925a816cf3114e5cdf7a80f7638241fce3f6f`; t04_evaluation_layout.py `185574f8e12e0c6b1ee6c5ae8682cc67319eab757ca9c65bff786998782eb7aa`; t04_evaluation_tasks.py `27048b07d9250434a2e0d35fef206c490d5a884da1f5b9fafbf01ab448233f53`; t07_evaluation_scoring.py `6102c2ef3363359c10af13142141940c043a040335ada2e33ea5779b0f1d6ce3`; t08_scoring.py `f1dde545c959b947fa09e4662f3f2ac9aee5b8faa676a2a62ef3fdf42363fa15`; t09_scoring.py `b20bd656e6870889fe85e25e3d9c2d1f14f2e4381d07185bea69b7b527077c39`; evaluation manifest `jobs/evaluation/SOURCES.sha256` `d98f5e6f49f85ea4ba66bc5d5d91b5ee39aa5a5e85c28fd493af4d8940f0768a` (915 files, pinned in the 14 task scripts), `submit.sh` `2fd84fe976cc004af001f903cf661bcab313265db92291af4ffda9e7c24acbfc`, `lib.sh` `bd7c2a98df8017fdf0d285aecab04447f0e325e9f41a3ce7b74c0d2cb4b3724d`; jobs of record 7593002 and 7594893 (E6 merge), 7601521 (integration, PASS; its checked manifest equals d98f5e6f apart from the path prefix); full-suite checkpoint 7606257 PASS at the branch; plan for attempt 1 on block 11: 526 tasks, 174.4 CPU-hours (ceiling 200); fresh reviews d4-e6-merge-review.md, integ-review.md and their re-reviews |

## Changes since this candidate was drafted (2026-11-13, for the user's information)

- Recheck at the branch tip `d65323ee` (proposal 2.1's command): the three adapter manifests, the six recipe and test files above and the
  Freeze A files are unchanged, so the evaluated recipes are byte-identical to the Freeze-B run's.
- E6 changed after its merge, before this word, by review: an errored or skipped check module is a crash, never a fail; the verdict is
  read from unittest's own summary; every subprocess is bounded by min(start + task limit, `SLURM_JOB_END_TIME`) - 120 s and a timeout is
  incomplete (exit 3); a sacct error, empty answer or foreign row is retried, then incomplete, never a guessed state (review C1, which
  would otherwise have turned a completed task into "required output missing"); a deadline stop after draws has its own reason and is
  never repeated on blocks 11 and 12.
- Accepted minors (fail-safe, before any draw): an unreadable `SLURM_JOB_END_TIME` ends the task with exit 3 through a traceback, not
  "rejected"; a `nan` or `inf` value is ignored and a past end gives the 1 s minimum timeout.
- Held by the user until after D4: `sys.dont_write_bytecode` in `calo_cluster.py` and `photon_likelihood.py` (Freeze B items);
  `test_no_bytecode` is the one allowed failing test besides the LCG one, with exactly those two offenders.

## Freeze A, unchanged

| File | SHA-256 |
| --- | --- |
| t04-values-v4.md | `92f71f561ea14b59034ba68fc52f69773d31262e44b371e9ee47110f0ad2edb6` |
| t04-prereg.md | `39495c3f7db0cded7f88b45711a9457f438be0cbd4113370880d69866448a151` |
| t07-t09-task-sheets.md | `01f3509156734372a725eba77b3604935bf420b74fc5f9670fed4348269906f0` |
| freeze-a.md | `669fc90426419f3e691c6b09113b792a64f03d4bdf7c097e3fe3ab6f23423570` |

## Readings and rules that go with the word

- The user's answers that fix how results are read before any result exists (K09), all in decisions.md: U-K1 to U-K7 (2026-11-11);
  the attempt-2 levels (2026-11-12: pass bounds at 99 %, step 1 at 95 % at both attempts, paired bound 2.326 at attempt 2, F2's whole
  bound at 99 % at attempt 2, E1a and E1b "fires" at 1.645 at both attempts); a wrong minimum when the truth-start fit failed counts as
  a wrong minimum; the deterministic and CAI checks rerun at evaluation at the frozen hash.
- For the user's information (coordinator rulings): T08 efficiency reference is v4 4.2's bin integral R; U-K5's per-shower seed firing
  in far credits a cell to the shower with the largest truth deposit; a T07 primary with no plane-1 result counts as a failure in every
  gated rate; a failed T07 refit fit is counted and printed per bin as a reading.
- U-B15 (failing check first, T07 stages 1-7 and 10, T08 stage 1): waived by the user, recorded as "waived by the user, not shown".

## Not in this freeze

Bin edges and valid ranges (v4 3.3, 4); the required set (v4 10); `C`, `tau`, tolerances, caps, attempts and the penalty; Freeze A's
documents (above); the generators and their GOLDEN digests; the 50 fixed likelihood points. T08 and T09 are frozen as development
bindings (U12 A); the native-backend gap stays open. Evaluation resources: approved separately (ceiling 200 CPU-hours, attempt 1).
