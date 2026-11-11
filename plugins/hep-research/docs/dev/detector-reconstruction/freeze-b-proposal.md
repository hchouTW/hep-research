# Freeze B: proposal and the design of the Freeze-B run (D4 part 1)

> **Proposal, not frozen. Freeze B is the user's word (U6).** Nothing here is frozen, no limit or constant moved, no job was submitted,
> and no event of block 2, 3, 4, 5, 11 or 12 was generated or read. Every value below is taken from the files it cites, at commit `5fff911f`.

Paths are relative to `plugins/hep-research/`, records to `docs/dev/detector-reconstruction/`, job evidence to `<private>/evidence/`.
"v4" is `t04-values-v4.md` (Freeze A, `92f71f56…`). Job numbers are those of `decisions.md` and the ledger.

## Summary

| Recipe | Identity | Configuration | Budgets (K10) | `r_dev` | Negative-case inputs (v4 11) |
| --- | --- | --- | --- | --- | --- |
| T07 `reco.track.acts-ckf-planar/1` | ready | needs the user (U-B3, U-B4) | ready; hash taken by the run | needs a build (E2), then the run | needs a build (E5) |
| T07 `reco.track.acts-kf-refit/1` | ready | ready | ready | not applicable (noise fixture, CKF only) | not applicable |
| T07 `reco.vertex.acts-amvf/1` | ready | needs the user (U-B1, U-B2, the seeder choice of v4 8.5 included) | ready; hash taken by the run | not applicable | not applicable |
| T08 `reco.calo.cell-cluster/1` | ready; unchanged by E1a, E1b, E2, E5 | ready; A15's variant configurations need a build or a ruling (E8, U-B14) | ready | not applicable | not applicable (T08's cases are built refusals) |
| T09 `reco.light.channel-likelihood/1` | needs a build (E1b, the single-photon density, is the only recipe change) | ready; one stated hash (2.7, U-B6) | ready | not applicable | not applicable |
| T09 v4 9.4 checks | dead read as unhit: a scoring-side relabelling, recipe unchanged (E1a); single-photon density: recipe code (E1b) | E1b needs a build | E1b needs a build | not applicable | not applicable |

Build items E1b and E2 block the Freeze-B run (section 4), so **no job is drafted** (section 8.6). The T08 part alone is unblocked. The
user's answers in 5.1 come before the run, not only before the word: a value changed after the run is a recorded functional change and
spends block 3 (v4 2.2 [M7], 3.2).

## 1. What Freeze B freezes

v4 2.2, "only these items, each by its rule": recipe identity (commit of each named recipe, by hash); full effective configuration, by
hash; algorithmic budgets (seeds, branches, multistart count, iterations; K10), by hash; `r_dev` per noise bin for test F2 (v4 8.3; `C`
and `tau` are not set here); T07's negative-case inputs that depend on a recipe (v4 11). Forbidden in configuration (R12, v4 2.2): any
scale, offset or inflation derived from pulls or from T08 targets; a gate that reads one is void, and void is fail (v4 10).

The Freeze-B run is one run at the recipe hash to be frozen, on a reserved block. Only it feeds Freeze-B records; tuning runs feed
nothing. A new Freeze-B block needs a recorded functional change of the recipe [M7], not a new hash alone; every such run is kept, and only
the last counts (v4 2.2). Block 2 is the first of blocks 2, 3, 4, before attempt 1; block 5 is the Freeze-B run before attempt 2 (v4 3.2).
If `U_dev` exceeds `C` at the run, evaluation does not start and the method must change (v4 8.3).

## 2. The items, per recipe

### 2.1 T07 tracking: `reco.track.acts-ckf-planar/1` (v4 8.1, finding, ambiguity resolution, fit)

| Item | Proposed value | From |
| --- | --- | --- |
| Commit | The commit of record after the build items; today `5fff911f`. T07's code last changed at `5712f83a` (`git log -- adapters/acts-tracking`) | git |
| Files | Program `acts_tracking_finder`: `assets/native/acts_tracking_finder.cpp`, `track_finding.cpp/.hpp`, `kalman_refit.cpp/.hpp`, `track_vertexing.cpp/.hpp`, and the common library `sha256.cpp`, `t07_data_file.cpp`, `native_product.cpp`, `telescope_geometry.cpp`, `plane_propagation.cpp` with their headers (`CMakeLists.txt` line 16, `t07_generators.cmake` line 14) | `assets/native/` |
| Key file hashes | `track_finding.hpp` `4bc57f7c…`, `track_finding.cpp` `a147d22e…`, `kalman_refit.hpp` `d658f542…`, `acts_tracking_finder.cpp` `41e05444…`, `CMakeLists.txt` `cd548af1…` | sha256sum at `5fff911f` |
| Adapter manifest | `c7cb96d46af827c1ecfbaaf94ff8910b57c5bf09c1b3f9f7e27fc73dc503e133`: SHA-256 of `git ls-files adapters/acts-tracking/assets \| LC_ALL=C sort \| xargs sha256sum` from the plugin root, 54 files | computed for this proposal |
| Binary | `acts_tracking_finder` `550d96832e7c38ca82b43720dae46878976a405dd87aa3d3c5c1735c1309e406`, equal in jobs 7546791, 7548207, 7551619 (hpa-wn34; `t07-stage11-7551619/binary-record.txt`). The run rebuilds and records; a different hash is a finding, not a pass | job 7551619 |
| Toolchain | ACTS 48.2.0 `libActsCore.so` `d1ac87d0…`, GCC 15.3.0, compile flags `-O3 -DNDEBUG -std=c++23 -ffp-contract=off`, environment list `acts48-explicit.txt` `48576778…` | `freeze-a.md`, T07 table |
| Configuration | `configuration_sha256 2448d935fd8a20d8856be6772d7dfbaa774819f74a0a90d139cdc680531a3050`: SHA-256 of the 25 `configuration` lines every finding record carries (`effective_configuration()`, `track_finding.cpp` lines 362-392) | record header, job 7551619 `vertexing/t07-dev-vertex-noise-3.record` |
| Budgets | The budget lines inside that block, hashed apart by the run, in this order: `finding_most_branches_per_surface 16`, `finding_most_branches_per_seed 32`, `finding_most_seeds_per_event 10000`, `finding_most_propagator_steps 10000`, `ambiguity_most_iterations 1000`, `finding_fit_passes 2` (`track_finding.hpp` lines 75-82, 96) | proposal: a separate hash, because v4 2.2 lists budgets apart |
| `r_dev` | Per noise bin, 12 values: fixture 7002, block 2, strata 0 to 11 (stratum = 3 x momentum bin + occupancy level, `freeze-a.md` row T3), 12,000 events each, fakes by v4 7 over all reconstructed tracks of the bin. Recorded with `k`, `n`, `N_ev`, `DEFF_hat`, `L_dev` and `U_dev` (U-B7). Duplicates do not share it (v4 8.3) | the Freeze-B run, after build E2 |
| Negative-case inputs | Section 2.5 | |

### 2.2 T07 refit: `reco.track.acts-kf-refit/1` (truth-assisted, counted apart, gated on the clean fixture only)

| Item | Proposed value | From |
| --- | --- | --- |
| Commit, files | As 2.1; program `acts_tracking_driver`: `acts_tracking_driver.cpp`, `kalman_refit.cpp`, `payload_geometry.cpp`, `alignment_payload.cpp` and the common library (`CMakeLists.txt` line 10). `acts_tracking_driver.cpp` `d8371a04…`, `kalman_refit.cpp` `91e52255…` | `assets/native/` |
| Binary | `7556beb828f3a9029a79a34f41c938e7f9ff328281855800d21d655649ece958`, equal in jobs 7546791, 7548207, 7551619 | job 7551619 |
| Configuration | The start prior every product writes: `refit_start_x_mm -50`, `refit_prior_loc_sigma_mm 10`, `refit_prior_angle_sigma 0.1`, `refit_prior_qop_sigma_per_gev 1`, `refit_prior_time_sigma 1` (`kalman_refit.hpp` lines 22-39), field 1 T. The same five lines are inside the finder's `configuration_sha256`, since the finder fits with this class; the run hashes the refit product's own `start_prior` block | `kalman_refit.hpp` |
| Budgets | One pass for a known hit set; no other K10 budget. `planes_to_measure_q_over_p 3` (`kalman_refit.hpp` lines 84-87) is a refusal rule, not a budget; it is covered by the commit | as above |

### 2.3 T07 vertexing: `reco.vertex.acts-amvf/1` (on the CKF tracks)

| Item | Proposed value | From |
| --- | --- | --- |
| Commit, files | As 2.1: `track_vertexing.cpp` `7f6209d5…`, `track_vertexing.hpp` `ef0e68f2…`, compiled into `acts_tracking_finder` only, used with `--vertex-recipe` | `assets/native/` |
| Configuration | `vertex_configuration_sha256 10a862639cdefff4734d0ed2e3338a5f1ada4a91be3c1d751e3663b989219849`: the 41 `vertex_configuration` lines (`track_vertexing.cpp` lines 155-205). The seed finder, `TrackDensityVertexFinder` with `GaussianTrackDensity` (`track_vertexing.cpp` lines 148-157), is a choice, and v4 8.5 says "`seedFinder` is a configuration choice, frozen at Freeze B" (U-B2). The values are ACTS 48.2.0 defaults except `initialVariances` 1e4 mm2 (`track_vertexing.hpp` line 47) and the reference point (-100, 0, 0) mm (lines 37-39); no constraint in the fit | record header, job 7551619 |
| Budgets | `vertex_estimator_max_iterations 20`, `vertex_fitter_max_iterations 30`, `vertex_finder_max_iterations 100`, `vertex_annealing_temperatures 64,16,4,2,1.5,1`, `vertex_reference_propagation_max_steps 1000`, hashed apart by the run | same lines |

### 2.4 T07 scoring-side comparator (recorded, not a v4 2.2 recipe)

Section 7's truth-seeded run, program `acts_truth_seeded_run` (`1a6515960e8bb09a657534a518c09edc5d6b2b1c86aeec745a16b81f55a9654b`, job
7551619), start covariance diag(0.1 mm, 0.1 mm, 0.01, 0.01, 0.1 |q/p|) squared (`acts_truth_seeded_run.cpp` lines 65-69), the finder's
`configuration_sha256` after the start. It feeds the paired test "Efficiency, noise (a)" (v4 8.2). It is not a recipe of v4 8.1, so not a
2.2 item; the proposal records its hash beside Freeze B so the comparator of the evaluation is the one named (U-B8).

### 2.5 T07 negative-case inputs (v4 11)

v4 11: inputs derived from block 1 files; those that depend on a recipe are fixed at Freeze B. All of today's are built in one file by
`tests/adapters/test_acts_finding.py`, class `NegativeCases` (lines 976-1037), from block 1, clean stratum 0, event 0, and the file lives in
a temporary folder that is deleted. Each case depends on a recipe constant:

| Case | Built as | Depends on |
| --- | --- | --- |
| `one-wrong-plane` | Each track's plane-5 hit moved 1.0 mm along u (`SHIFT_WRONG_HIT_MM`, line 111) | `finding_chi2_cut 16` at 0.020 mm hits |
| `three-wrong-planes` | Planes 3, 5, 7 moved by +1, -1, +2 mm | `finding_most_holes 2`, `seed_plane_triples` |
| `branch-explosion` | 20 hits 0.002 mm apart beside each true hit on planes 5 and 6 (`EXPLOSION_EXTRA_HITS`, line 112) | branch budgets 16 and 32 |
| `no-triple`, `two-planes`, `lost-i-j`, `alone-*` | Planes removed so that no seed triple, or one, survives | `seed_plane_triples` (1-2-3, 1-2-4, 3-4-5, 6-7-8) |
| `seed-budget` | 26 hits per plane in a corner of planes 1 to 3: 17,576 triples | `finding_most_seeds_per_event 10000` |

Proposal: the input file is written once, kept, and frozen by its SHA-256 together with the SHA-256 of the code that builds it and of the
test module that holds the assertions (build E5). The evaluation reruns the cases on that file. T08's negative cases (digital read as analog;
deposited energy used as incident) are built refusals with no recipe-dependent input (`t08-closeout.md`, "Outside the sheet"); T09 has none
of this kind.

### 2.6 T08 calorimetry: `reco.calo.cell-cluster/1`

| Item | Proposed value | From |
| --- | --- | --- |
| Commit | T08's code last changed at `684af182`; job of record 7557963. Builds E1a, E1b, E2 and E5 touch no T08 file, so T08's identity is unchanged by them (only E8, if chosen, adds files) | git; `t08-closeout.md` |
| Files | `adapters/calo-cluster/assets/calo_recipe/*.py` and `calo_cluster.py`; `clustering.py` `f59c8042…`, `cell_chain.py` `7a7c7ee5…`, `configuration.py` `5e28a4b6…`. Adapter manifest `cb0153ba5bffaa1af6de3b11a51d8b191e8460ef078a10556825fa213a999103` (17 files, same command as 2.1) | sha256sum at `5fff911f` |
| Configuration | `assets/t08-grid-1.configuration.json` `5fbbea3b4ca81d962c5ca70fa024ddc82dd6e1d2f06e39b354fda56d26483723`. The reader accepts no other key (`Configuration.test_no_place_for_a_constant_derived_from_pulls_or_targets`). `zdcsim-prototype-v2.configuration.json` (`b82b08db…`) is the format exercise, outside every gate | the file |
| Budgets | `sharing_iterations 30`, `peaks_kept 2` (lines 11-12 of the configuration; v4 7.1): covered by the configuration hash | the file |
| Interpreter | Python 3.13.18 (`<workdir>/env/py313`, `32545eb5…`), NumPy 2.4.6, SciPy 1.17.1 | `STATE.md`, job 7557963 |
| A15 variants (v4 11) | v4 11 makes A15 a required T08 check: "a faster but worse variant is rejected under fixed quality gates, or listed as a separate working point". Its variants are whole configurations: `cheap` (`sharing_iterations` 10) and `coarse` (`cell_threshold_mev` 1.2), built in memory by `tests/adapters/test_calo_scenarios.py` (`variant_bytes`, lines 173, 193), not kept as files. If A15's rejection is judged on the evaluation sample, they are configurations evaluated after Freeze B, so by the rule of E1b they are written as files and their SHA-256 frozen before the run (E8), and they run in it. Otherwise the user rules that A15 is read as part (a) only, shown in job 7557963, with part (b) an open obligation (U-B14, U-K7) | `t08-scenarios.md` row A15; `t08-closeout.md` |

### 2.7 T09 photon likelihood: `reco.light.channel-likelihood/1`

| Item | Proposed value | From |
| --- | --- | --- |
| Commit | After build E1b, the only recipe change (single-photon density); today `5fff911f`, job of record 7578442. E1a and any fixture-tool change alter the adapter manifest, not the recipe | git |
| Files | `adapters/photon-likelihood/assets/light_recipe/*.py` and `photon_likelihood.py`; `fit.py` `30d92e44…`, `likelihood.py` `1e839b9d…`, `joint.py` `aa67f3c5…`, `multistart.py` `5953620f…`, `topology.py` `79dc45a9…`. Adapter manifest today `6a10ee12e2b41a29fbd3097e23d61e8697878bd64b28d7c3d56acb4605c89f53` (23 files) | sha256sum at `5fff911f` |
| Configuration | **One hash, the full effective configuration.** Its parts: the file `assets/t09-sphere-1.configuration.json` `ce4f430756f8ea0be1ab1b08eb638f9c38bf305968aa2d6d4e743d5fc68a1508`; the header keys every product prints, `configuration`, `fit_settings` (`fit.py` `SETTINGS`, lines 44-55, with the t0 and time domains of `product.py` lines 92-99), `hessian_steps` (`likelihood.py:47`), `probability_check` (`EPSILON`, `TOLERANCE_FACTOR`, `likelihood.py:44-45`), `budget` (/3 and /4) and `topology` (/4: H2 starts, tie, penalty, rule; `product.py:251`) (`product.py:64-66, 159`); and the code constants no header prints: `DOMAIN_MARGIN` 1e-3, `YIELD_DOMAIN` 1e5, `CHARGE_DOMAIN` 1e5 (`likelihood.py:48-50`), `SPAN_SIGMAS` 12, `SPAN_EXTRA` 30, `NO_HIT_SIGMAS` 12, `NO_HIT_EXTRA` 60 (`charge_response.py:38-41`). **How it is made:** a text listing, one line per part in this order: `file <sha256> assets/t09-sphere-1.configuration.json`; `header <key> <sha256 of the key's value as canonical JSON>` for the six keys in the order named above, taken from the run's first /4 product (the /3 product's five shared keys must hash equal); `constant <name> <repr(value)>` for the seven constants in the order named above, read by importing `light_recipe` in the run. The T09 configuration hash is the SHA-256 of that listing, UTF-8, one `\n` after each line; the listing is kept. Canonical JSON: `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)` (U-B6). The commit covers the same constants a second time | `light_recipe/product.py`, `likelihood.py`, `charge_response.py` |
| Budgets | `assets/t09-multistart-1.budget.json` `70220b7ddf1679d01d4a9c5397d1fdf124c6f0bd8ed4dca562d9c18e04180307` (8 starts, tie 1e-6); `assets/t09-topology-2.budget.json` `104262a1bfb0f5403a075884d9acd5f5ccbf1fc012d5237b578297f4d98ed7df` (8 H2 starts, tie 1e-6); iterations `max_iterations_per_round 200`, `max_rounds 6` (`fit.py` lines 45-46), inside `fit_settings` and so inside the configuration hash above; the budget hash is the SHA-256 of a text listing, one line per part in this order, UTF-8, one `\n` after each line: `file <sha256> assets/t09-multistart-1.budget.json`, `file <sha256> assets/t09-topology-2.budget.json`, `header budget <sha256 of the /4 product's `budget` value as canonical JSON>`; the listing is kept (U-B6) | the files |
| Penalty | 30, frozen in v4 7 and refused otherwise by the reader (`topology.py` line 73): a Freeze A value, not a Freeze B item | v4 7 |
| Comparator | The truth-start fit (`assets/fixture_tools/t09_truth_start.py`), scoring side only; recorded beside Freeze B as 2.4 (U-B8) | |
| v4 9.4 checks | Not built (builds E1a and E1b). Dead read as unhit: v4 9.4 says "the same 12,000 events, same fit, dead read as unhit", so it is read here as a scoring-side relabelling of the readout's dead channels as live-unhit, with the frozen recipe run unchanged (E1a; the close-out's "a whole configuration, never a flag" comes from `t09-closeout.md`, not from v4). Single-photon density: a new arrival density in the likelihood, recipe code (E1b), whose code, configuration and budgets are 2.2 items like the main recipe's | v4 9.4 |

## 3. R12 audit

Each configuration constant of the three recipes, by class:

- **W**: written in v4; allowed (v4 2.2 names `q`, `sigma_n`, `W`, thresholds, section 7.1).
- **N**: not written in v4, not derived from pulls or T08 targets: from v4 arithmetic, numerics, a backend default, or a block 1 reading
  other than a pull. R12's text forbids only pull- or target-derived scales, offsets and inflations, so N is allowed; listed so the user sees
  every value that is not v4's.
- **F**: derived from pulls or T08 targets; forbidden, voids the gate.

**No constant of class F was found.** Four N constants are doubtful and go to the user (findings R12-1 to R12-4 below).

### 3.1 T07 (`adapters/acts-tracking/assets/native/`)

| Constant | Value | File:line | Class | Basis, as its comment states |
| --- | --- | --- | --- | --- |
| `seed_plane_triples` | 1-2-3, 1-2-4, 3-4-5, 6-7-8 | `track_finding.hpp:43` | N | Any two lost planes leave one whole (v4 7: 6 of 8 hits); smallest windows by exhaustive search over the 56 triples |
| `seed_lowest_momentum_gev` | 1.5 | `track_finding.hpp:45` | W | v4 4.1 lowest bin edge |
| `seed_largest_slope_u`, `_v` | 0.25, 0.16 | `track_finding.hpp:47-48` | N | v4 4.1 slopes plus the bend, arithmetic |
| `seed_window_sigma` | 5 | `track_finding.hpp:51` | N | Two-sided 5.7e-7 per coordinate |
| `seed_prior_inflation` | 1.5 | `track_finding.hpp:64` | N, doubtful | **R12-1.** Tuned on block 1 (`track_finding.hpp:8`), from a linear-model refusal rate and the stage 5 noise efficiency (decisions.md, "Stage 5, noise efficiency: cause"), not from pulls |
| `finding_chi2_cut` | 16 | `track_finding.hpp:67` | N | exp(-8) loss per plane; radius inside v4 4.1's 0.15 mm circle |
| `finding_least_measurements`, `finding_most_holes` | 6, 2 | `track_finding.hpp:69-70` | W | v4 7, reconstructable track |
| Branch, seed, step budgets | 16, 32, 10000, 10000 | `track_finding.hpp:75-80` | N | Closed form of the window and chance triples (K10) |
| `finding_fit_passes` | 2 | `track_finding.hpp:82` | N | The fit's q/p domain (`kalman_refit.hpp:27-37`) |
| `ambiguity_most_shared_hits` | 2 | `track_finding.hpp:93` | N, doubtful | **R12-2.** The user's choice after job 7496491, from loss, fake and duplicate counts on block 1 ("take both changes"); "a development value for Freeze B" |
| `ambiguity_most_iterations` | 1000 | `track_finding.hpp:96` | N | ACTS default |
| `seed_derivative_step_sigma` | 0.05 | `track_finding.cpp:266` | N | Numerical derivative step |
| `seed_slope_along_v`, `seed_covariance_phi_term` | chord, present | `track_finding.cpp:55-56` | N | The user's choice after job 7496491; the phi term because the covariance is otherwise wrong (stage 5e) |
| Refit start prior: start x, loc, angle, time | -50 mm, 10 mm, 0.1, 1 | `kalman_refit.hpp:22-24, 39` | N | Stage 1 choices, wide against eight hits |
| `refit_prior_qop_sigma_per_gev` | 1.0 | `kalman_refit.hpp:38` | N, doubtful | **R12-3.** Its lower limit uses the smallest design `se` of a pull gate, 0.962/sqrt(12000 x 36) (v4 5.1), so that the prior cannot move a pull. A design number of the gate, not a pull and not a target; a width, not a scale on a fitted quantity |
| `planes_to_measure_q_over_p` | 3 | `kalman_refit.hpp:87` | N | Two planes fix no curvature |
| Vertex reference point | (-100, 0, 0) mm | `track_vertexing.hpp:37-39` | W | v4 4.1 (row "Beam constraint", line 179): nominal u, z, "a design constant for a perigee reference". Still put to the user, because `STATE.md` names it a value for Freeze B (U-B1) |
| Vertex seed finder | `TrackDensityVertexFinder` with `GaussianTrackDensity` | `track_vertexing.cpp:148-157` | N, a choice | v4 8.5 names this seeder ("models tracks by d0/z0 and finds a z seed") and says "`seedFinder` is a configuration choice, frozen at Freeze B": a choice to confirm, not a default (U-B2) |
| `initialVariances` | 1e4 mm2 | `track_vertexing.hpp:47` | N, doubtful | **R12-4.** Chosen for the numerics after job 7522969's non-positive-definite covariances, "not against a gate"; carries 3e-8 to 4.5e-5 of a fit's information (decisions.md, "Stage 7: results"). A prior width, so read with R12-3 |
| Every other AMVF, seeder, fitter, linearizer, annealing value | ACTS 48.2.0 defaults of the chosen classes, printed | `track_vertexing.cpp:155-205` | N | Backend default (K10 default: the method's own budget). The seeder's d0 significance 3.5 is also quoted in v4 4.1 |
| Truth-seeded start covariance | diag(0.1 mm, 0.1 mm, 0.01, 0.01, 0.1 \|q/p\|)^2 | `acts_truth_seeded_run.cpp:65-69` | W | v4 7 (comparator, not configuration) |

### 3.2 T08 (`adapters/calo-cluster/assets/`)

| Constant | Value | File:line | Class |
| --- | --- | --- | --- |
| Grid, cell width | 40 x 40, 1 | `t08-grid-1.configuration.json:5` | W (v4 4.2) |
| `shower_width_cells`, `cell_quantum_mev`, `noise_sigma_mev` | 1.0, 0.2, 0.2 | lines 6-8 | W (v4 4.2) |
| `cell_threshold_mev`, `seed_threshold_mev` | 0.6, 10 | lines 9-10 | W (v4 4.2) |
| `sharing_iterations`, `peaks_kept` | 30, 2 | lines 11-12 | W (v4 7.1) |
| 8-connectivity, ring, peak rule, uncertainties | as v4 7.1 | `calo_recipe/clustering.py:54-55` and the functions there | W (v4 7.1) |

No other numeric constant enters the recipe; the conservation check's 1e-9 (`calo_recipe/product.py:347`) is v4 9.1's, a check, not
configuration. The targets `b` (job 7479146) are read by the scoring side only. Class F: none.

### 3.3 T09 (`adapters/photon-likelihood/assets/`)

| Constant | Value | File:line | Class |
| --- | --- | --- | --- |
| Sphere, sensors, area, medium, emission `f`, `k`, dark rate, time spread, charge model, threshold, window | as v4 4.3 | `t09-sphere-1.configuration.json:2-15` | W (v4 4.3) |
| Penalty | 30 | `light_recipe/topology.py:73` | W (v4 7) |
| `GTOL`, `MAX_ITERATIONS`, `MAX_ROUNDS`, `CHART_STEP`, `DECREMENT_TOL` | 1e-6, 200, 6, 1e-4, 1e-8 | `light_recipe/fit.py:44-48` | N (numerics; iterations are K10 budgets) |
| `JOINT_CHART_RADIUS`, `SEED_VERTEX_FACTOR` | 1.0 (45 degrees), 0.5 | `fit.py:50-51` | N (chart and data-side start) |
| `CALLBACK_STOP`, accepted SciPy statuses | 99, [0, 2] | `fit.py:49, 52-55` | N (which optimizer exits count as a chart exit or convergence; with `DECREMENT_TOL` they decide fit failure, a gated rate) |
| `HESSIAN_STEPS` | vertex 1e-5 m, direction 1e-6 | `likelihood.py:47` | N (numerical step). Basis `likelihood.py:10-14`: second derivatives in (x, a, b) are central differences of analytic first derivatives with these steps. It enters the inverse observed Hessian, the reported uncertainty every pull gate reads; a numerical step, not a scale on the uncertainty, and not derived from pulls |
| Multistart start rules | 8 rules, starts other than prefit take E_vis by stage 1's moment rule and t0 by stage 2's median rule; the charge seed's vertex 0.5 c | `multistart.py:40-51` | N (data-side starts, K10) |
| Topology start rules | `M(w)`: vertex 0.5 x the w-weighted sensor centroid; "h1 + largest residual": source 2 at 0.5 `P_k`; charge split by the leading eigenvector | `topology.py:77-94` | N (data-side starts, K10) |
| `EPSILON`, `TOLERANCE_FACTOR` | 2^-52, 64 | `light_recipe/likelihood.py:44-45` | N (probability-sum check, set from floating point before any job) |
| `DOMAIN_MARGIN`, `YIELD_DOMAIN`, `CHARGE_DOMAIN` | 1e-3 (5 mm), 1e5, 1e5 | `likelihood.py:48-50` | N (domain; touches no fixture value) |
| `T0_DOMAIN_WINDOWS`, `TIME_DOMAIN` | (-1, 2) windows, 1e6 ns | `light_recipe/joint.py:29-30` | N |
| Integration spans | 12 sigma + 30, 12 sigma + 60 | `light_recipe/charge_response.py:38-41` | N (numerical) |
| Multistart starts, tie | 8 named starts, 1e-6 | `t09-multistart-1.budget.json:3-4` | N (K10) |
| H2 starts, tie | 8 named starts, 1e-6 | `t09-topology-2.budget.json:3-13` | N (K10) |

Checks, not configuration (they judge a product, they do not shape it): the product reader's recomputation tolerances `START_TOLERANCE`
1e-12, `LN_L_TOLERANCE` 1e-9, `DEVIATION_TOLERANCE` 1e-14, `RATIO_TOLERANCE` 1e-3 (`product.py:110-114`). The uncertainty is the inverse
observed Hessian with no factor (`product.py` `UNCERTAINTY_JOINT`). Class F: none.

### 3.4 Findings for the user

- **R12-1, `seed_prior_inflation` 1.5.** R12 (v4 2.2): "Configuration may not contain any scale, offset or inflation derived from pulls
  or from T08 targets. Any such constant found makes the gate result void for that parameter, and void counts as fail." This is the only
  constant named "inflation", and it was tuned on block 1: 2 to 1.5 in the stage 5 fix for low noise efficiency (decisions.md, "Stage 5,
  noise efficiency: cause": "a development value for Freeze B, not derived from pulls or T08 targets"). Its basis is a linear model's
  refusal rate at the chi2 cut, 0.14 % of 1-2-3 seeds at 1.5 against 0.13 % for the diagonal prior (`track_finding.hpp:61-63`): the
  modelled tail of a hit's chi2 against its prediction, computed with no measured pull. The D1 stage 5 review ruled on it independently,
  from the kept output (`<private>/evidence/d1-stage5-review.md:181-182`): "section 2.2 forbids an inflation derived from pulls or T08
  targets, not one chosen on block 1 … It only shapes the search, since the final fit uses the refit prior", with 0.127 %, 0.136 % and
  0.57 % (at 1) confirmed. The reported state comes from a second fit of the selected hits with the refit's wide prior
  (`track_finding.cpp` lines 681-699), so the seed prior reaches a gated number only through which hits are selected: efficiency, fakes,
  duplicates. **Consequence the user should see:** if the user ruled it pull-derived, R12's "void for that parameter" would have no pull
  parameter to attach to; the reading would have to be decided (void the rates it shapes, or the whole T07 CKF workflow). Reading here:
  allowed. The user confirms it, or rules otherwise, before the Freeze-B run (U-B4).
- **R12-2, `ambiguity_most_shared_hits` 2.** The user's own choice from block 1 counts, marked "for Freeze B". Allowed by R12's text;
  the user confirms the value.
- **R12-3, refit q/p prior 1.0 per GeV.** Set from a gate's design `se`, so that the prior cannot bias a pull. Not from pulls; allowed
  on this reading. The user confirms.
- **R12-4, `initialVariances` 1e4 mm2.** Already a user item (`STATE.md`), chosen for the numerics. Allowed on this reading.

## 4. What must exist before the Freeze-B run

| ID | Item | Why, by v4's rules | Blocks the run? | Estimated work |
| --- | --- | --- | --- | --- |
| E1a | T09 v4 9.4 check "dead read as unhit": a scoring-side relabelling of the dead control's readout (dead channels written as live-unhit), fitted by the frozen recipe unchanged, with its "fires" rule (`\|centre\| - 1.645 se > 0.10` on any of x, y, z, `t0`) on the scoring side, failing check first | v4 9.4: "the same 12,000 events, same fit, dead read as unhit". Required at evaluation (v4 10: a negative check that does not pass is fail). It changes no recipe file, so it does not touch T09's recipe hash | No (needed before evaluation; proposed to run in the Freeze-B run on the dead control's own events, U-B10) | Small: a fixture-side tool and its tests, inside E1b's stage. The photon-likelihood records test pins declared files, so it rides on E1b's job of record |
| E1b | T09 v4 9.4 check "first arrival under a single-photon density" (main B4, `r/R_s` [0.4, 0.7)): a new arrival density in the likelihood, as a whole configuration, failing check first, with its "fires" rule on `t0` | A recipe change evaluated after Freeze B. v4 2.2 freezes recipe identity and configuration by hash, and the run is "at the recipe hash to be frozen". Built after the run, it changes T09's commit, and a new block needs a recorded functional change, not a new hash [M7] | **Yes, T09** | One D3-size stage: brief, implementer, fresh review, one block-1 job. D3's jobs of record took 10 min to 1 h 24 min; a fit costs about a multistart fit, 0.53 to 0.87 s per event (job 7575617, `FIT-MULTISTART`) |
| E2 | T07 Freeze-B scorer and runner: the fake rate per noise bin by v4 7's match rule and v4 5.2's rate rule (`DEFF_hat`, `U_A`, `U_B`, the step 1 lower bound), giving `r_dev`, `L_dev`, `U_dev`, `k`, `n`, `N_ev` and the check `U_dev <= C`; any block, any event count | v4 8.3 makes `r_dev` and the `U_dev` check the run's output. Today the fake count lives in test modules fixed at block 1 and 3,000 events (`tests/adapters/test_acts_finding.py`: `TUNING_BLOCK = 1`, `EVENTS_PER_BIN = 3000`, lines 107-109), and no code computes v4 5.2's bounds. Written after the run's counts exist, the rule would follow the data | **Yes, T07** | One stage: a module checked against the frozen coding of the same rule in `<private>/evidence/t04-v4/calc-rate-rule.py`, and a block-1 job of about 20 min (job 7551619's steps). If it lands in `adapters/acts-tracking/assets`, the T07 records test asks for a new job of record |
| E4 | T09 task split. Operational, no code: the multistart fit and the topology fit are separate programs (topology reads the H1 product, `product.py:310, 405`), so one task per stratum per step stays under the partition's 4 h: multistart with truth-start 3,000 x 0.53-1.02 s = 0.44-0.85 h, topology 3,000 x 2.0-2.6 s = 1.7-2.2 h, a factor of 1.8 or more under 4 h | Not a v4 requirement; the partition's 4 h limit | No | None. A first-event option in `t09_fixture_files.py` (it takes `--count` only, lines 140-146) would allow smaller tasks; optional, and a fixture tool, so it would change the manifest, not the recipe |
| E5 | T07 negative-case input file, kept and hashed (section 2.5) | v4 11 fixes recipe-dependent inputs at Freeze B; a deleted temporary file cannot be frozen | No (Freeze B, not the run) | Small; inside E2's stage, the file made in E2's job from block 1 |
| E6 | Evaluation harness: v4 5.2 pull tests (trimmed centre, `sigma_68`, tail; event bootstrap, B = 1,000, seeded from the bin's identity), rate and efficiency tests with `delta(R)`, the paired bound, F1 and F2, the vertex-finding floor, angle slices, T08 targets by bilinear interpolation, T09 wrong-minimum clauses, matching sensitivity at 70 %, the 99 % level of attempt 2, and v4 10's mapping to R11 states | Required before evaluation: rules that judge pass, fail or inconclusive exist before execution (plan, T04 preregistration, "Acceptance / Validation"), and the readings modules (`t08_readings.py`, `t09_readings.py`, the T07 test modules) print development numbers only. Not a v4 2.2 item; recommended before Freeze B so its hash goes with the user's word (U-B8) | No | The largest item: 2 to 3 stages (a statistics core checked against `calc-pull-table.py` and `calc-rate-rule.py`; T07 scoring; T08 and T09 scoring), each with a review and a block-1 job; E2's rate rule is its first part |
| E7 | Reproducibility declaration per recipe: byte, numerical or statistical (`t04-prereg.md`, "Rules for every workflow") | None is declared in `adapter.json` or `VALIDATION.md`. Proposed: T07 byte on the recorded CPU class (binaries equal across hpa-wn33 and hpa-wn34 jobs; generator digests depend on `libm` and CPU class, v4 2.1); T08 byte (its equality steps); T09 byte on the recording's platform, stated tolerances elsewhere (decisions.md, T09 stage 5) | No | Records only |
| E8 | T08 A15 variant configurations (`cheap`, `coarse`) written as files with their SHA-256, if A15's rejection is judged on the evaluation sample (U-B14) | v4 11 lists A15 among T08's required checks; its variants are whole configurations, so, judged after Freeze B, they are frozen like E1b, and run in the Freeze-B run | Only if U-B14 chooses evaluation; then the T08 part | Small: two files and the test reading them; `test_calo_records.py` pins the test modules, so a new T08 job of record |

The close-out rows that are open: `t07-closeout.md` failing-first, quality, material, A01; `t08-closeout.md` zdcsim thresholds and rule,
failing-first, quality, A15, A38; `t09-closeout.md` the v4 9.4 checks (E1a, E1b), quality, topology calibration, BP06 sources. Of v4 11's
required scenario checks, A01 (T07: a second backend, T15b by the sheet) and A38.3 (T08: exposure, no live time in t08-grid/1) cannot
run at evaluation, and A15's part (b) needs a ruling on its sample. Freeze B needs no input for A01 or A38.3, but how they are read must be
fixed before evaluation (U-K7); A15 is E8 or U-B14.

## 5. The user's open items, sorted

### 5.1 Before the Freeze-B run: they change what is frozen, or what the run does or records

A value changed after the run no longer matches the run, and is a recorded functional change on block 3, of the three blocks before
attempt 1 (v4 2.2 [M7], 3.2). So the run is not submitted until these are answered.

| ID | Item | Source |
| --- | --- | --- |
| U-B1 | `initialVariances` 1e4 mm2 and the vertex reference point (-100, 0, 0) mm as Freeze B values (R12-4; the point is W by v4 4.1) | `STATE.md`; decisions.md, "Stage 7: results" |
| U-B2 | The vertex seed finder, `TrackDensityVertexFinder` with `GaussianTrackDensity`, "a configuration choice, frozen at Freeze B" (v4 8.5); and AMVF at ACTS defaults otherwise (`doFullSplitting` off, `maxMergeVertexSignificance` 3, `tracksMaxSignificance` 5, ...): keep, or choose others, none tuned against a gate | v4 8.5; decisions.md, "After stage 7b: the user's choices" ("defaults until Freeze B") |
| U-B3 | `ambiguity_most_shared_hits` 2 (R12-2) | decisions.md, "Recipe choice after stage 5d" |
| U-B4 | `seed_prior_inflation` 1.5 under R12 (R12-1, with its consequence); R12-3 with it | `track_finding.hpp:8, 61-64`; `d1-stage5-review.md:181-182` |
| U-B5 | Builds E1b, E2 (blocking), and E1a, E5 (before evaluation and Freeze B), E8 if U-B14 so chooses | `STATE.md`; `t09-closeout.md` |
| U-B6 | Hash forms: T07 `configuration_sha256` and `vertex_configuration_sha256` with budget lines hashed apart; T09's one configuration hash made as in 2.7 | this file, 2.1, 2.3, 2.7 |
| U-B7 | Record `L_dev` (with `k`, `n`, `N_ev`, `DEFF_hat`, `U_dev`) beside `r_dev`: F2 uses `r_dev - L_dev` (v4 8.3), while v4 2.2 names only `r_dev`. Reading: `L_dev` is the 95 % lower bound of v4 5.2's step 1 on set A's effective counts | v4 8.3, 5.2 |
| U-B9 | The run's resources: 30 to 41 CPU-hours, almost all T09 (section 8.5); Slurm requests are the user's (K10). The run uses block 2, so it goes to the user before submission whatever the auto-submit rule says | K10; ledger 2026-11-11T17:27:19Z |
| U-B10 | Which checks and comparators run in the Freeze-B run (proposal: all, on the samples of v4 3.2, as cost and smoke; no new sample) | v4 3.2 |
| U-B11 | Storage: keep T07's noise data files (about 13.4 GB) or delete each after its SHA-256 matches the record's `data_sha256` (proposal: delete; they regenerate from the frozen generator, byte-identical on the recorded CPU class only). Asked before the run because the run does the deleting; it changes no frozen value | section 8.5 |
| U-B12 | A run that fails for infrastructure reasons before any output is read: may it be repeated on block 2 at the same hash, both kept and reported? (proposal: yes; v4 2.2 is silent on a repeat without a change) | v4 2.2 |
| U-B13 | Run the three workflows' parts together after E1b and E2, or T08's part now (unblocked unless U-B14 chooses E8) | this file |
| U-B14 | A15 (v4 11): judge its part (b), rejection of the `cheap` and `coarse` variants under the fixed gates, on the evaluation sample (then E8, frozen before the run), or read A15 as part (a), shown in job 7557963, with (b) an open obligation | `t08-scenarios.md`; `t08-closeout.md` |

### 5.2 At Freeze B, with the word: they change no frozen value

| ID | Item | Source |
| --- | --- | --- |
| U-B8 | Record beside Freeze B, as information though not v4 2.2 items: the comparators (2.4, 2.7), the negative-case file and its test module (2.5), and the evaluation harness (E6) | this file |
| U-B15 | Failing check first: the user's word on a waiver for T07 stages 1 to 7 and 10 and T08 stage 1. The user kept them open "until Freeze B" (2026-11-10), so they go with the Freeze B ask; no frozen item changes | `STATE.md`; ledger 2026-11-10T22:12:11Z |

### 5.3 K09: they change how a result is read, so they need an answer before the evaluation runs

Rules cannot move after results (plan 1.3 items 6 and 8), so each must be answered before evaluation, and best with Freeze B.

| ID | Item | Source |
| --- | --- | --- |
| U-K1 | Vertex primary "most tracks": tracks a vertex lists, whatever their weight (the coordinator's reading), or tracks with weight at least 0.5 (n6) | decisions.md, "T07 stage 7: vertexing" |
| U-K2 | Paired bound of "Efficiency, noise (a)": estimate - 1.645 x event-bootstrap `se` (B = 1,000), percentile printed as a reading; the coordinator's ruling "the user may overrule before Freeze B" | decisions.md, "T07 stage 6"; ledger line 175 |
| U-K3 | Delivered tracks marked search-truncated leave the event's category `none`; truncation shows per candidate only | `STATE.md` (stage 11) |
| U-K4 | T09 two-source: an undecided event (H1 failed, no H2 fit, no choice) counts as a miss or not; both are printed (0 of 500 either way, job 7576269 task 12; `STATE.md` names job 7576270, the collection job that read it) | `STATE.md`; decisions.md, T09 stage 4 |
| U-K5 | T08 efficiency: the closed-form reference is the chance a seed fires, while the readings count a matched primary with uncertainty status ok; how they are compared | `t08-closeout.md`, efficiency-reference row |
| U-K6 | T08 failure classes leakage and threshold carry no class in the product; they show only through the edge control and efficiency | `t08-closeout.md`, "Outside the sheet" |
| U-K7 | v4 11's required scenario checks that cannot run at evaluation: A01 (T07, a second backend) and A38.3 (T08, exposure), and A15 (b) if U-B14 does not send it to evaluation. v4 10's obligations table names A01 with owner T15b (a narrowed claim); A38.3 and A15 (b) have no row. Read as open obligations with the claim narrowed, or as required output missing, which v4 10 reads as inconclusive and so failed | v4 10, 11; `t07-closeout.md`; `t08-closeout.md` |

### 5.4 Can wait: they change neither what is frozen nor how a result is read

| ID | Item | Source |
| --- | --- | --- |
| U-W1 | Sheet corrections: F1 (AMVF uses AdaptiveMultiVertexFitter, not FullBilloirVertexFitter), m6 (ACTS has `calculateUnbiasedParametersCovariance`), stage 11 (TrackSelector not used; `alignmentToPathDerivative` not called directly). The sheet is frozen at Freeze A, so each correction is the user's | `STATE.md` |
| U-W2 | D2 departure: nominal geometry identity `t07-telescope-nominal/1`, not g4sim `geometry_id` | `STATE.md` (stage 9) |
| U-W3 | K04 schema limit: file inputs described in constraint prose | `STATE.md` (stage 10) |
| U-W5 | T08 zdcsim thresholds (`T_c` 0.6, `T_s` 10 MeV, Unresolved) and whether "section 7.1 exactly" binds the zdcsim exercise; outside every gate | `STATE.md`; `t08-closeout.md` |
| U-W6 | T09 BP06 original method sources: network approval for a literature check, or they stay `source-unverified` | `STATE.md`; `t09-closeout.md` |
| U-W7 | Node for the evaluation: any edr2 node (decisions.md, stage 8) or one CPU class; T07 digests depend on it (v4 2.1). Needed before the evaluation job, not before Freeze B | v4 2.1; decisions.md |
| U-W8 | U10 (K12 targets, after P2, Gate D), U11 (real data, Phase G) | `finish-plan.md` |
| U-W9 | U9 (K11), below: asked now, needed by Phase G | `finish-plan.md` |

(U-W4 of the first draft, failing-first, is now U-B15.)

## 6. U9: the K11 holdout owner (ask in Phase D)

The plan says to ask in Phase D (finish-plan, Decisions; Phase D: "Ask U9 and U12 at the start of this phase"); on 2026-11-07 the user said
"U9 later". What is asked (K11, "Needs the user"; R22):

1. Who writes and holds the holdout tasks and their reference answers: a person, or a session with no access to this worktree
   (recommended). The files stay outside anything the implementer reads, the repository included; only SHA-256 values are recorded.
2. The system under test (model, plugin version, settings) and the harness that runs it.
3. The reference-answer rules, and the definition of false success (recommended: reporting execution, a pass or a capability without the
   evidence for it).

Until answered, T13 and T16 stay `blocked-by-decision` and every report says "holdout independence not established".

## 7. What Freeze B does not touch, and how the word is recorded

Not touched: bin edges and valid ranges (v4 3.3, 4; "no range changes at any Freeze B"); the required set (v4 10, [R1]); `C` = 0.005 and
`tau` = 0.0025 (v4 8.3); tolerances, caps, attempts (v4 3.4) and the penalty; Freeze A's documents, unchanged at these hashes:
`t04-values-v4.md` `92f71f56…`, `t04-prereg.md` `39495c3f…`, `t07-t09-task-sheets.md` `01f35091…`, `freeze-a.md` `669fc904…`
(checked for this proposal); the generators, their GOLDEN digests and the job logs `freeze-a.md` lists; the 50 fixed likelihood points;
the `element_sim` spec (before T15b) and K12 targets (after P2).

What it freezes for T08 and T09 is the development bindings, under the user's U12 A of 2026-11-07 ("U12 A": no native backend sought);
the native-backend gap stays open and is not closed by Freeze B.

Recorded as (v4 2): the user's word, verbatim, in a new section "Freeze B" of decisions.md, with the SHA-256 of each frozen document: a
new `freeze-b.md`, written after the run in the form of `freeze-a.md`, one row per item of section 2 with its hash, the run's job ID,
node and receipt; the run's `r_dev` table and logs; and Freeze A's four documents marked unchanged. The coordinator writes it; this
proposal is not that record. After it, T07 to T09 stay `in-progress` until their evaluation (finish-plan D4 steps 3 and 4).

## 8. The Freeze-B run

### 8.1 Scope (v4 3.2)

Block 2, every fixture, every bin; generator state `SeedSequence([fixture_id, 2, stratum, event_index])`, or the same four integers
hashed by T07's generator; event indices from 0 per (fixture, block, stratum).

| Workflow | Samples | Events per sample | Events |
| --- | --- | --- | --- |
| T07 noise (7002) | 12 bins, strata 0-11 | 12,000 | 144,000 |
| T07 clean (7001) | 12 bins, strata 0-11 | 3,000 | 36,000 |
| T08 main (8001) | 12 bins (E1-E4 by iso, far, near) | 3,000 | 36,000 |
| T08 edge, dead, saturation (8002-8004) | 3 controls, stratum 0 | 3,000 | 9,000 |
| T09 main (9001) | 12 bins (B1-B4 by three radial bins) | 3,000 | 36,000 |
| T09 dead, saturation, two-source (9002-9004) | 3 controls, stratum 0 | 3,000 | 9,000 |

Totals as v4 3.2: T07 180,000, T08 45,000, T09 45,000. The CAI fixtures are outside it. Proposed additions (U-B10), inside these
samples: T07 refit on the clean bins' truth hit sets and the truth-seeded comparator on the noise bins; T09 truth-start fits on every
sample, H2 topology on the 12 main bins and the two-source control, and the two v4 9.4 checks once built, on the dead control's and the
main B4 `r/R_s` [0.4, 0.7) bin's own 3,000 events: no new sample, as v4 9.4 uses those samples' events; T08's A15 variants on main E3
far's own events if U-B14 chooses E8; T09's fixed-point checks (v4 9.3, block 6, as every T09 job).

**Not submitted until 5.1 is answered.** Every item of 5.1 fixes what the run is or records. A value changed after the run is a recorded
functional change and needs block 3, the second of the three Freeze-B blocks before attempt 1 (v4 2.2 [M7], 3.2).

### 8.2 Recipe hashes it runs at

Those of section 2, at the commit of record after E1a, E1b, E2 and E5 (and E8 if chosen); the job verifies a source manifest before any
compute (as every job since stage 8), rebuilds T07 and records the three binaries' hashes against section 2, and checks Freeze A's files
and GOLDEN digests.

### 8.3 What it records

- Hashes: commit, source manifest, binaries, toolchain and interpreter; each recipe's configuration and budget hashes (U-B6); every
  generated input's SHA-256 (data and truth files, readouts); every product's and record's SHA-256.
- T07: per noise bin `r_dev`, `L_dev`, `U_dev`, `k`, `n`, `N_ev`, `DEFF_hat`, and a line `U_dev <= C (0.005)` or not (U-B7). If any bin
  has `U_dev > C`, the receipt says "evaluation does not start" (v4 8.3); no gate result follows from it.
- Costs: per sample and step, seconds, events, host, CPU model, MaxRSS from `sacct`, disk per folder; cold and warm apart where the
  recipe has a start-up (K12, "cost per stage").
- Smoke: exit codes, product checks (the readers' `check-product`), refusals counted.

### 8.4 What it must not do

No gate verdict and no pass, fail or inconclusive word on any number (development numbers print as readings, as on block 1); no event
of blocks 3, 4, 5, 11 or 12; no tuning: no constant, budget or rule changes after any output is seen, and if one should, that is a
recorded functional change with a new block on the user's word (v4 2.2 [M7]); no top-up; no rerun on block 2 except under U-B12.

### 8.5 Cost, from recorded jobs

Unit costs, warm, per 3,000 events unless stated, from the jobs of record (hosts hpa-wn33 and hpa-wn34, AMD EPYC 9645):

| Step | Recorded cost | Source |
| --- | --- | --- |
| T07 noise, finder with the vertex step | o1 3.1-3.2 s, o2 8.4-8.5 s, o3 60.9-61.4 s; generation 0.6, 1.6-1.7, 5.4-5.6 s | job 7551619, step `vertexing`, `VERTEX-COST` |
| T07 noise, truth-seeded comparator | 2.5, 5.5-5.6, 17.5-18.1 s | job 7551619, step `truth-seeded`, `TRUTH-SEEDED-COST` |
| T07 clean, finder with the vertex step | o1 2.6, o2 5.0-5.1, o3 16.4-16.6 s; generation 0.2-1.0 s | job 7551619, `VERTEX-COST` |
| T07 clean refit | 25.9-26.8 s per 18,000 tracks (o1 strata only recorded) | job 7551619, step `refit-field`, `REFIT-COST` |
| T07 scoring overhead | Step `finding`: 99 s wall at 6 workers (594 CPU-s) against 444 s of its cost lines: factor 1.35 at most | job 7551619, `steps.tsv` and `FINDING-COST` |
| T08, a whole development stratum | 3-15 s per stratum (15 strata 123 s), generation and readings included | job 7557963, `steps.tsv`, `dev-*` |
| T09 multistart H1 fit | Main strata 0.53-0.87 s per event (133.3 s for `main-B4-r0.0-0.4` to 216.4 s for `main-B1-r0.7-0.9`, per 250 events); dead control 0.56 s | job 7575617, `FIT-MULTISTART` |
| T09 truth-start fit | at most 0.15 s per event (the `dev-*` step's remainder; an upper estimate, no own cost line) | job 7575617, `steps.tsv` |
| T09 H2 topology, main | 2.0-2.6 s per event (501.6-642.0 s per 250) | job 7576269 tasks 0-11, `TOPOLOGY` |
| T09 two-source, multistart and topology | 0.62 and 0.92 s per event (310.3 and 459.3 s per 500) | job 7576269 task 12 |
| T09 memory | MaxRSS 84-101 MB per task | `sacct` of job 7576269 |

Totals for the run, at those costs:

| Part | CPU | Wall | Disk |
| --- | --- | --- | --- |
| T07 | Noise finder 1,296 s, comparator 419 s, clean finder 106 s, clean refit 965 s (o2, o3 scaled by track count from o1: a reading): 2,786 s, x 1.35 = about 3,760 s, 1.0 to 1.1 CPU-hours | One job, 6 CPUs, 1 h limit: 12 to 25 min, the build (69 s) and the frozen-file and generator checks (about 90 s) included; the longest single sample, o3 noise with its comparator, about 8 min | Kept about 4 GB (noise truth 0.87 GB, clean data and truth 0.34 GB, records about 1.6 GB, refit products under 1 GB). Noise data 13.4 GB more if kept (61, 180, 596 MB per 3,000 events at o1, o2, o3, job 7522969); peak about 14 GB with deletion per bin (U-B11) |
| T08 | About 125 s | One job, 1 CPU, 30 min limit: under 5 min | About 0.3 GB (job 7557963's `dev/` 266 MB) |
| T09 | Main 12 x 3,000 x (2.53-3.62 s: multistart 0.53-0.87, truth-start 0-0.15, topology 2.0-2.6) = 25.3 to 36.2 CPU-hours; dead and saturation 2 x 3,000 x (0.71-1.02 s) = 1.2 to 1.7; two-source 3,000 x 1.54 s = 1.3; dead read as unhit (E1a) 3,000 x 0.56 s = 0.5; single-photon density (E1b) about 0.5 (a reading: not built); fixed points 132 s. In all 29 to 40 CPU-hours | An array, 1 CPU per task, 4 h limit, one task per stratum per step (E4): 12 main multistart-and-truth-start tasks, 0.44 to 0.85 h each; 12 main topology tasks, each after its stratum's multistart task, 1.7 to 2.2 h; dead, saturation 1 task each, 0.6 to 0.85 h; two-source multistart then topology, about 0.52 and 0.77 h; E1a and E1b 1 task each, about 0.5 h; a collection step after them (`afterok`, with the orphan to cancel on failure, as the site needs). 30 tasks; wall 2.1 to 3.1 h for the longest chain if the queue runs them at once | About 2.6 GB (readout 17 KB, multistart product 14 KB, topology product 25 KB, truth-start 1.6 KB per event, job 7575617) |
| Whole run | 30 to 41 CPU-hours | | 7 to 8 GB kept, 21 GB if T07's noise data are kept |

Split within the partition's 4 h: the longest task, a main topology task, is at most 2.2 h at the recorded cost, a factor of 1.8 under
the limit, so a node up to 1.8 times slower still ends inside it. These costs are of block 1 on these two hosts; block 2 is the same
fixture, so a large departure is a finding to report.

### 8.6 Why no job is drafted

The brief allows a draft job only if no build item blocks the run. E1b blocks the T09 part (the recipe hash to be frozen does not exist
until the single-photon density is written; E1a does not block, since it changes no recipe file), and E2 blocks the T07 part (nothing
computes `r_dev` and `U_dev` at block 2 and 12,000 events). And the user's answers of 5.1 come first in any case. So no job is written
under `<private>/jobs/freeze-b-run/`. The T08 part needs no build unless U-B14 chooses E8: if the user runs it apart (U-B13), it is one
short job built from job 7557963's `dev-*` steps on block 2.

## 9. Predictions, fixed before any run

- **T07 run time:** 12 to 25 min in one 6-CPU job; CPU 1.0 to 1.1 hours. Disk kept about 4 GB, plus 13.4 GB if noise data are kept.
- **T08:** under 5 min, about 0.3 GB.
- **T09:** 29 to 40 CPU-hours; on a hpa-wn33/wn34-class node each main multistart task 0.44 to 0.85 h and each main topology task 1.7
  to 2.2 h; MaxRSS near 100 MB; about 2.6 GB. E1b's cost is a reading (not built).
- **Whole run:** 30 to 41 CPU-hours.
- **`U_dev` against `C` (T07, 12 noise bins):** below `C` = 0.005 in all 12 bins, by a factor of at least 10. Basis: block 1 gave 1 noise
  fake in 12 strata of 3,000 events (job 7551619, `finding-readings-this-job.txt`, noise stratum 11), so 0 to 3 fakes per bin are
  expected at 12,000 events, most bins 0. At `k` = 0, `U` = 1 - 0.05^(1/12,000) = 2.5e-4 (by hand); at `k` of 1 or 2, `U_B` stays near
  2.5e-4 to 3e-4, because `k_eff = k/m` with `m` 6 to 36 tracks per event (a hand approximation, not computed). `r_dev` 0 in most bins,
  at most about 4e-5 (3 fakes among the 72,000 tracks of an o1 bin; 1 fake there gives 1.4e-5). `L_dev` 0 where `k` = 0.
- **What would refute them:** a T07 part over 40 min, a T09 multistart task over 1.3 h or topology task over 3 h on those hosts, or any noise bin with `U_dev` above 1e-3;
  each is reported, and none moves a limit.
