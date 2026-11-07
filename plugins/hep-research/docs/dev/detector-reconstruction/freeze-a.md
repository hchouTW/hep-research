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

## Not in this freeze

- T07's generator. It depends on the ACTS driver, and its hash is an addendum on the user's word, before any T07 development run (section 2.1).
- The `element_sim` spec for K16, frozen by hash before T15b (section 13).
- K12 targets, drafted after P2 from recorded costs (U10). No speed or cost claim until then.
- Recipes, configuration, budgets, T07's recipe-dependent negative-case inputs and `r_dev`: Freeze B (section 2.2).

## Choices the generators make where version 4 is silent

None changes a number in version 4. All freeze with the generator hashes. Rows 1, 16 and 19 were closed by edits to sections 2.1, 4.3 and 18.

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
