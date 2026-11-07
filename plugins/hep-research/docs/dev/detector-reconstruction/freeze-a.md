# Freeze A: what is frozen

Candidate for the user's word (R02, finish-plan B4, decision U5). Not frozen until decisions.md holds that word. After it, any change is a section 2.3 amendment, labelled "after development", except Amendment 1 and the addendum it names, below. Paths are under the records folder or `<private>/evidence/t04-v4/`.

## Documents

| File | SHA-256 |
| --- | --- |
| t04-values-v4.md, as amended by Amendment 1 | `92f71f561ea14b59034ba68fc52f69773d31262e44b371e9ee47110f0ad2edb6` |
| t04-prereg.md | `39495c3f7db0cded7f88b45711a9457f438be0cbd4113370880d69866448a151` |
| t07-t09-task-sheets.md | `01f3509156734372a725eba77b3604935bf420b74fc5f9670fed4348269906f0` |

## Amendment 1, before development

The user's word: decisions.md, "Freeze A amendment 1: direction", "Freeze A amendment 1: choices" and the word on this text that follows them. Made before any T07 development run, so section 2.3's label does not apply. It changed t04-values-v4.md from `c55ff22fee9268e5cf245aee43ae673920baf002086946071cba5b5920789105` to the hash above. t04-prereg.md and t07-t09-task-sheets.md did not change. This file's own hash is in decisions.md. T07's generators, check and job log follow as an addendum, after T07's job of record.

## Generators and check

| File | SHA-256 |
| --- | --- |
| generators/gen_t08_grid.py | `d901362c62431282ce37eeaac88efb864339aec9eb6915aa9e7d69808f7946f9` |
| generators/gen_t09_sphere.py | `2657f56bfc1fc7f68a93e205b2c66f80b52018494a78346bcd4e955a9be7da76` |
| generators/check_generators.py | `a9f7f4af3cccc860863f62e9b3acf392a7489bbeea3225cb6ce167af60e7a50f` |

`GOLDEN` digests: 61 lines of `job-generators-7477787/check_generators.log`, numpy 2.4.6, scipy 1.17.1, node `hpa-wn28`. Byte equality across other nodes is untested.

T07, the addendum Amendment 1 names, on the user's word: job 7492427, commit adf2d051. One row per item of section 2.1's T07 table. `native/` and `fixture_tools/` are under `adapters/acts-tracking/assets/`, and `build/` is `<private>/evidence/t07-record-7492427/build/`.

| File | SHA-256 |
| --- | --- |
| native/t07_generators.cmake | `cd057420f8bc12b35a7c6b6f2de2fe14b0c55fc1d44e60c498deee0f558fde39` |
| native/telescope_geometry.cpp | `20909da4ab246bd82316ac557a0b6cf05d1dedc6da5461404efa8b927dd8bfd6` |
| native/telescope_geometry.hpp | `9060ffc252dbe7671eca6bf2942e3048349303de9de27bf792442195b7f5f247` |
| native/plane_propagation.cpp | `eb0188c2a1db53c067465fb75ec39a8653b9167cbeb95c68cb63f2997ed5815e` |
| native/plane_propagation.hpp | `dbbaf9f994e57609d570528b7a71d13226cfdef0de052e0953d6b2311325876f` |
| native/t07_seed_stream.cpp | `53b58eaa40e74ac6cc2357a80e68dfa1f5e9bdf25b1f766a77bfb0694874fa83` |
| native/t07_seed_stream.hpp | `5857d705d99beb516ee72c8d9c52e3ac3f1c7038d2a2db4a5c960130af41e1cf` |
| native/t07_data_file.cpp | `853581212292448bcff603923ac96b687793a1274336ca3b9483500c6785898e` |
| native/t07_data_file.hpp | `c366cc2ad8a521aa11dfd1bcff28f965d72f3816b0f34d03ffdfcdc94b8ca2d8` |
| native/t07_truth_file.cpp | `902cef9cce0732afc01aab4bea2fa46f9fccf96fef9ce4d89021052ffdfcef9c` |
| native/t07_truth_file.hpp | `a178ce64a19b4145c03b596252921a8df355aef5f45bfd2e3868fff8dfee792f` |
| native/sha256.cpp | `b05b177a84d686c10291ce792d770b379ac7fa968e8706eb6fbaa0047ae74dae` |
| native/sha256.hpp | `1ec4cedd3989a767105bf36e1fb5e75b2d5c31decdb8600d095c25dd006483c2` |
| native/t07_fixture_constants.hpp | `47b85f612f7753be466bbb791d96f13229c1428a19ad1550672b8072e7491c04` |
| native/t07_generation_constants.hpp | `3b6c52398ac7820a51ccfe5f6d3cd1afa31320749bdd240e5042627bb530a0bf` |
| native/t07_event_generator.hpp | `b3af519534dec359b4423e130fbf91612681dde529490a2dbe65408612d4b8f9` |
| native/t07_event_generator.cpp | `9a912b2ce99a585382a45e7393bb4a5fd1b436423ab235ce3057210905b6b2bf` |
| native/t07_fixture_generator.cpp | `e22682ea20a55546aeec87ee77b3b92747fe9a6e68caf522d0fa498bc121ac0f` |
| native/t07_cai_constants.hpp | `ff006195a29bb74dad071b8076f4fe773d85ab2e363f51804fc3bba6cb281b99` |
| native/t07_cai_event_generator.cpp | `eccc7c8f3708bc6ab03db40d73af2603bcc04a1c17ae676607a85528d11c956a` |
| native/t07_cai_event_generator.hpp | `fef531d5ec42a3933e5fb780d7c9c4ecd40803669ff5a45d5f5f00635e1ed656` |
| native/t07_cai_fixture_generator.cpp | `701ca62016421a78fafca9967ab35358b5c358268d26e5736e6c264a129ddc10` |
| fixture_tools/check_t07_generator.py | `6d6b87ee3e3b5d4666dd14e2e2d7e2aa34d57f3f89f3c8fc71dbf89570db89da` |
| fixture_tools/t07_fixture_files.py | `c4cf5b870d8be9735143b3e8b2439e8f90fd227185d9533f4641e708b98a00ac` |
| fixture_tools/t07_truth_files.py | `e421f2f3e677f801024b9752ec3f7b7d383685e5dfdf14d19be2a4c7da3f4741` |
| build/t07_fixture_generator | `9c659896533aee1a324e6a8c4c808021f6cf45c2697ba3c0b72f3a4c88d54a47` |
| build/t07_cai_fixture_generator | `f1c7309a804ba71a8e54a1ff55f16685a4255703142e130624fe290e77888931` |
| ld-linux-x86-64.so.2 (system) | `47a5ee38bf8b4a04d125f0da8420a78ce4b6fff0bde9a7cf49cb9aefd1f69548` |
| libActsCore.so (ACTS environment) | `d1ac87d045b0a055301a30b14b003f876dde8bbdcd2b3b984b0559363b0297a7` |
| libc.so.6 (system) | `c369ef07996c64bebe781176323170fe42e0cf83d4bcb4e7bce2860bcb8f9ae8` |
| libdl.so.2 (system) | `e36bd87e03dc6dd015d64b809734d27e9e8d4d1698b27d0a21f4a9e075c8aed4` |
| libgcc_s.so.1 (ACTS environment) | `5444fbe71e8cfe3bd05cdf2b44bd8c2e553e6e7e276977089b5e4e1a1ceed531` |
| libm.so.6 (system) | `a4ba3d1c54d209fc3541fac47f8de8ea2293bb95b876dd4820b430af61833d7e` |
| libstdc++.so.6 (ACTS environment) | `10f0d3c46c070acd4abea2ccf2500ff0ec77e9b90154b82ea2720dba05510cb9` |
| <private>/evidence/acts48-explicit.txt | `485767780ded1dbd4daa5f2cd43ec844e84831f8016689b2ee8e36c83a226952` |

`GOLDEN` digests: 32 lines of `<private>/evidence/t07-record-7492427/generator-check-full.log`, numpy 2.4.6, scipy 1.17.1, node `hpa-wn28`, glibc 2.34. Compile flags `-fmax-errors=40 -O3 -DNDEBUG -std=c++23 -ffp-contract=off`, no definitions. `-fmax-errors=40` comes from the job's command line and does not change code. Byte equality across other nodes is untested.

## Job logs

| Log | SHA-256 |
| --- | --- |
| job-a-7474461/calc-pull-table.log | `a3ccbf2851825b770c8adaea6bb4868c621165c4940e92c24b2f9badc2cf8e38` |
| job-a-7474461/calc-rate-rule.log | `1987316771b3595d7d37730a5fc2b60ca0da3271cb2057a28256f9560c9faace` |
| job-a-7474461/calc-t08-reference.log (history: replaced by job-round5-7479146; first numbers of the third stop) | `b009ab7d073a9be37d42cc147ad2b29b7439b353d5735fbefba37c49cb1cd490` |
| job-a-7474461/calc-t09-lowmu.log | `22330f0678a76ecef8916c4415d1c17f29aeddfe14f8a878a61a393b8e9cc47b` |
| job-b-7474462/calc-fake-reference.log | `01cdc90f9736ca2299700ee71fe1838a60a13d2044d4ff7e5f08d1619a69d15f` |
| job-b-7474462/calc-t09-null-h2.log | `f9a1c3cad67c638d25f4c45c0f4a88114293d80220ff4cab89ada167bf768948` |
| job-diag-7477066/diag-t08.log | `7cfd1d7f12224b1fc241f1b387af78b0cb8877ec03e956a057350f0fc5f83e1e` |
| job-diag-7477066/diag-t09.log | `3b4b3b4ffb2c4c7c7f741fbb248a7263d64686a54e44f6eb14f35b025454f688` |
| job-round4-7477126/calc-t08-exact.log | `ca10b2b31c375ce0f2136725d6c638bf913dd1c01992e7df2e4319b261ceae5b` |
| job-round4-7477126/calc-t09-range.log | `978c95d65d98a5588cb08c8ecf1f3e732c388aaf297bb813b8e583c336ea9f1c` |
| job-generators-7477787/check_generators.log | `1514b37372614b8552ebb4edfe761124c7543546aabaa03885ac270e1ef55022` |
| job-diag-t08b-7478606/diag-t08-width.log | `519c2628ca9b17caf35dc1272aaf78ff9b07eb35d0f4cdb64273e0e6a02a7f93` |
| job-diag-t08c-7478897/test-t08-sigma.log | `a478ad84b444154c70e9942b20796e115a28a073c94d910faeb52563dba2d02b` |
| job-round5-7479146/calc-t08-reference.log | `325e070b5a929a8d77d2cb88d00767e2ab5daa985a2d567c096486249835d0c8` |
| job-diag-t08d-7480930/test-t08-far-gap.log | `b7e01f066ca02a12f9d68ded5a61562f521a6f0252282690ac593ee154fc4d98` |
| <private>/evidence/t07-record-7492427/generator-check-full.log (T07's check of record) | `210b0073567140d65735bc42b89cfdf2676e2eda45171ca638d355643157487e` |

## Not in this freeze

- The `element_sim` spec for K16, frozen by hash before T15b (section 13).
- K12 targets, drafted after P2 from recorded costs (U10). No speed or cost claim until then.
- Recipes, configuration, budgets, T07's recipe-dependent negative-case inputs and `r_dev`: Freeze B (section 2.2).

## Choices the generators make where version 4 is silent

None changes a number in version 4. All freeze with the generator hashes. Rows 1, 16 and 19 were closed by edits to sections 2.1, 4.3 and 18. Rows C1 to C5 and T1 to T26 are T07's: they describe the code at its hash, and no row is a new decision.

| # | Section | Gap | Assumed |
| --- | --- | --- | --- |
| 1 | 2.1 | **Defect.** The charge reference `mu_i`, `1.09 mu_i` leaves out dark noise, which the fixture has, and the threshold. True moments are near `mu_i + 0.002` and `1.09 (mu_i + 0.002)`. Section 2.1 also names no channel set for T09, though "same two criteria" needs one: on back-facing channels `mu_i` is small enough that the z are not Gaussian and dark counts are comparable to the standard error | Closed: section 2.1 now states the dark term and the channel sets |
| 2 | 2.1 | Threshold also separates fixture from `generate()` in hit fraction: `generate()` has none | Accepted, as the text compares them. Single photons below 0.25 are 0.62 %; the sum of z^2 rises by at most about 12 at 1,000 channels, against a half-range near 147. Job 7477787 used 1,000, 1,000 and 987 channels, every channel with a hit and a miss. The check therefore cannot see a missing threshold |
| 3 | 2.1 | T09 reference sample size | 1,000 `generate()` events per `N_exp`, own stream: `default_rng([9001, 6, 1000 + stratum, i])` |
| 4 | 2.1 | Position in the T08 and T09 check | One fixed position per energy or `N_exp`: the one the generator draws for event 0 of that stratum, with T09's direction and `t0` too |
| 5 | 3.2 | Stratum integers are not defined | Main: `3 x bin + stratum` (T08: E1-E4, iso, far, near; T09: B1-B4, radial). Controls: 0 |
| 6 | 4.2 | Coordinate origin | Grid is [0, 40) on each axis; section 7.1's flat index is C order |
| 7 | 4.2 | Does the generator apply `T_c`? | No. Section 7.1 applies it, and the section 2.1 reference (mean down to 1 MeV, near 0.6) needs unthresholded values |
| 8 | 4.2 | "The largest `d`" | 8 `W`, for far and near both, as the row covers both. Midpoint [10, 30]. Near alone could use [7.5, 32.5]; only position range differs |
| 9 | 4.2 | Edge: which edge, what range for the other axis, how quarters are drawn | Low-x edge at x = 0. `y` uniform on [6, 34], because `E Phi(t)` needs no second truncation. `t` from `event_index mod 4`, as T07's `mod 5`, so exact quarters |
| 10 | 4.2 | Which cell is dead | One fixed cell (20, 20), shower uniform inside it, as the script fixes its central cell |
| 11 | 4.2 | Raw and calibrated fields | `raw = value/gain + pedestal`; the recipe forms `e_c` itself. No `gain` argument: CAI tests would change the constants or transform `raw` |
| 12 | 4.3 | Does a dark count carry charge? | Yes, one photon: Gaussian(1, 0.3), as `generate()` counts it in `n` |
| 13 | 4.3 | Dark window origin | [0, 200) ns, as the script |
| 14 | 4.3 | What the threshold does | Applied to the summed charge of the channel. Below: unhit, charge 0, no time. Time stays the earliest photon of a passing channel |
| 15 | 4.3 | Dead channels and `N_exp`, `S`, `E_vis` | Sums over all 1,000, dead included, as the script. Their photons exist in truth and are not read |
| 16 | 4.3 | Saturation flag | Closed: section 4.3 now names it. Data field `saturated` for charge at 5. Censoring itself belongs to the likelihood |
| 17 | 4.3 | "Nearest the +z axis" | Largest cos(polar angle): channels 0 to 199, as the script |
| 18 | 7, 3.2 | How the 50 fixed likelihood points are drawn | Not asked explicitly, but section 7 freezes them with the generator, so a later addition would be an amendment. `likelihood_points()`: reserved stratum 100 of fixture 9001, block 6, index k, main bin `k mod 12`, same draws as main truth |
| 19 | 2.1 | What a FAIL forces. Section 18 fixes outcomes, but this check has no row, and block 6 is fixed, so no redraw | Closed: section 18, generator check rows 1 to 5 |
| C1 | 4.1 | CAI event indices | From 0 per (fixture, block, stratum) |
| C2 | 4.1 | CAI draw order | Vertex u, z, v; charge; ln p, u slope, v slope; per plane two Gaussians, loc0 before loc1. No efficiency draw |
| C3 | 4.1 | How the deformation enters | Subtracted from the local crossing of the frozen geometry, in truth and hit. Exact for a shift inside the plane; a tilt or normal shift would need a displaced geometry |
| C4 | 3.2 | File format of the CAI fixtures | The same two formats. Neither file states the deformation: the truth header's `fixture_id` names it, and the check holds the table |
| C5 | 3.2 | CAI file order | Seed-digest order, as for clean and noise |
| T1 | 3.2 | How the four integers are hashed | SHA-256 of four little-endian u64, order fixture_id, block, stratum, event_index |
| T2 | 3.2 | Stream | xoshiro256**, state = digest as four little-endian u64. Uniform from the top 53 bits. Gaussian: Box-Muller, one value from two uniforms. Poisson: arrivals of a unit-rate process in [0, mean), exact and safe at mean 1000 |
| T3 | 3.2 | Stratum integers | 3 x momentum bin + occupancy level, as T08's row 5. Event indices start at 0 per (fixture, block, stratum) |
| T4 | 4.1 | Sign of u | Right-handed cyclic map: ACTS x = z, y = u, z = v. loc0 = u, loc1 = v, normal +x |
| T5 | 4.1 | Sign of the field along v | +v (ACTS +z). A positive track bends to -u |
| T6 | 4.1 | World volume | x in [-150, 400] mm, y and z within 200 mm, layer envelope 1 mm. Geometry only |
| T7 | 4.1 | "share u and z with small independent draws" | Each vertex draws u and z independently from the stated ranges, not as offsets from the first |
| T8 | 4.1 | "in one direction" | +v, always |
| T9 | 4.1 | Range of further vertices in v | Only the first is held within 30 mm; further ones may pass it by up to 2 x 25 `u_v` |
| T10 | 4.1 | Which tracks belong to which vertex | Contiguous blocks of track index: 3, 6, 12 per vertex |
| T11 | 4.1 | Charge split | Fisher-Yates over the event; balanced per event only, since o1 has 3 tracks per vertex |
| T12 | 4.1 | Slope meaning | du/dz and dv/dz at the vertex, direction (1, u, v) normalised; bending follows after the vertex |
| T13 | 4.1 | Endpoints | All uniform draws half-open, [lower, upper) |
| T14 | 4.1 | Hit efficiency draw | Per track and plane, always drawn; smearing also drawn for a lost hit, so draws do not shift. Draw order is in `t07_event_generator.hpp` |
| T15 | 4.1 | Noise hits | No smearing, no efficiency, after all tracks, per plane count then positions |
| T16 | 4.1 | Hit near the edge | Fiducial is tested on the truth crossing; a crossing at or past 150 mm stops the generator, no resampling. A smeared hit is not clipped |
| T17 | sheet | Hit order | Every hit on one grid, 2^-30 mm, by one code path, then sorted by plane, loc0, loc1; hit key = position. Corrected by N1 |
| T18 | sheet | What the data file may hold | Header: magic, role, event count, two sigmas. Event: hit count. Hit: key, plane, loc0, loc1. No digest, generator name, fixture id, block or stratum; an event is its position in the file, and the truth file holds the map. Corrected by M1 |
| T19 | 4.1 | Propagator settings | ACTS defaults (stepTolerance 1e-4, resolveSensitive on). On-plane tolerance 1e-3 mm for the local read. Mass passes as a 32-bit float; no effect with no material |
| T20 | 4.1 | Truth at a plane | Crossing loc0, loc1, phi, theta per plane; q/p once per track, constant with no material |
| T21 | 4.1 | Nominal u, z for a perigee | Not used by the generator; it is a later stage's constant |
| T22 | sheet | Word "role `truth`" | Native file role is `truth`, as the sheet says; the contract vocabulary's term is `truth-reference`. No truth sidecar exists at this stage |
| T23 | 2.1 | "3 energies or `N_exp` values": T07 has no fixed-momentum path | Every stratum, the first 1,000 of its 3,000 events |
| T24 | 2.1 | The helix tolerance | 1e-3 mm and 1e-5 rad, a twentieth of the hit sigma; 1e-4 mm for CAI |
| T25 | 2.1 | Golden event list | Events 0 and 1, by analogy |
| T26 | 2.1 | Sample in the KS test | A cap of 100,000 noise hits per stratum, for memory |
