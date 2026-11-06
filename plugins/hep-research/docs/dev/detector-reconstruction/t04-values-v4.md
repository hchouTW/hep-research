# T04: values, version 4 (Freeze A candidate)

Updated after jobs 7474461, 7474462, 7477066, 7477126, 7477787, 7478606, 7478897 and 7479146, under the rules of section 18 and the user's decisions of 2026-11-06 (decisions.md). Results: section 18.1.

Replaces t04-values-v3.md, after the third review (`<private>/evidence/20261106T102310Z-b3-review/verdict.md`) and the rechecks of round 1 and 2 (`<private>/evidence/t04-v4/recheck.md`, `recheck2.md`). This document stands alone. K09, K12 and K16 freeze only on the user's word (R02). Until then, no pass or fail claim.

Plain numbers in brackets refer to the verdict; R-numbers in square brackets to the first recheck; S-numbers to the second; M-numbers to a minor finding of either recheck, in the dispositions' Round 2 and Round 3 tables. R-numbers in round brackets or plain text (R02, R11, R37) are requirements of plan v9.2, `hep-research-detector-reconstruction-plan-v9.2-en.md`. So are capital "Section" numbers, "plan 11.4" and bare numbers such as 11.3.1. Lower-case "section" means this document. t04-v4-dispositions.md lists each finding and the edits other documents need.

Labels on numbers:

- **Closed form:** deterministic arithmetic, no random numbers: `<private>/evidence/t04-v4/calc-closed-form.py` (`d73ed58fcd64b344…`), `calc-t08-closed.py` (`7dd0b289f98a9b9a…`), `calc-round2-small.py` (`8c204a41a95d8469…`). `calc-t08-closed.py` evaluates the expected image only, with independent-cell moments. Where calc-closed-form.py still prints round-1 T07 or T08 fixture values, the later scripts govern.
- **Earlier rule:** simulated in v2 or v3 under a rule that has since changed. Kept for history only.
- **Design choice:** an arbitrary synthetic value. Not an instrument fact and not from a source.

## 1. What these gates can show

All inputs for now are synthetic. These are **closure gates**: did the recipe recover what the fixture generated?

A pass supports exactly this statement [14]:

> In each gated bin, the robust centre, core width, tail fraction and listed rates showed no departure beyond their limits, on this fixture. Departures that cancel within a bin, or lie outside these statistics, are not excluded.

A pass does not show the code is correct. It is not a performance claim, an instrument result or T3-C (R23). Uncertainties are tested in the core and by the tail rate only. "Found at least 95 % of the time" (section 5.5) holds for a shift or scale across a whole bin. Every fixture shares something with its reconstruction: geometry in T07, geometry and shower profile in T08, the light model as well in T09. A shared model error cannot be seen here. T08's near gate tests thresholds and membership only: sharing in near is untested. A recipe with a constant derived from pulls would pass on any seed; section 2.2 forbids this.

## 2. Two-step freeze

Each freeze is the user's word, recorded verbatim in decisions.md with the SHA-256 of each frozen document [22].

### 2.1 Freeze A, before any development run

Frozen by hash:

- this document, including the fixture table, every edge, tolerance, cap, floor, range and the clustering definition;
- t04-prereg.md and t07-t09-task-sheets.md, after the edits listed in t04-v4-dispositions.md [16]. Prereg's sample roles, failure classes, negative cases and critical false-success table are in force through this hash;
- these job logs, and the T08 target tables they give: job 7474461's `calc-t09-lowmu.py`, `calc-pull-table.py` and `calc-rate-rule.py`; job 7474462's `calc-t09-null-h2.py` and `calc-fake-reference.py`; diagnostic job 7477066; round 4 job 7477126; the generator check, job 7477787; the two T08 width jobs, 7478606 and 7478897; and round 5 job 7479146's `calc-t08-reference.py`, which replaces job 7474461's T08 log;
- each fixture generator [R11]. A generator needs no recipe output. T08 and T09 generators are frozen with this document. T07's depends on the ACTS driver: if it is not ready, its hash is an addendum to Freeze A, on the user's word, before any T07 development run. After that, a generator change is a section 2.3 amendment.

A deterministic check ties each generator to the fixture text [R11, S8], on a fixed seed block (block 6), 1,000 events at each of 3 energies or `N_exp` values, and 3,000 events per stratum for draws.

- T08: the reference is `E g_c(x, y)` and its variance `q E g_c + sigma_n^2`, not one draw. Per energy, over cells with mean above 1 MeV, for mean and variance: every `|z|` below 5, and the sum of `z^2` within its 99.9 % chi-square range.
- T09: hit fraction against `calc-t09-lowmu.py`'s `generate()`, over every channel with both a hit and a miss. Over channels with `mu_i` at least 0.1: mean first time against the same `generate()`; charge moments against the analytic `mu_i + 0.002` and `1.09 (mu_i + 0.002)`, dark counts included, because `generate()` has integer charge and the fixture does not. Same two criteria.
- Both: drawn distributions, control constants, `E_vis` truth and golden digests, as `check_generators.py` prints them on `DRAW`, `SMOKE`, `TRUTH` and `GOLDEN` lines.

Events must be byte-identical under the recorded NumPy version on the same partition. Any digest difference goes to the user. This job ran on one node, `hpa-wn28`, so equality across the partition's nodes is untested.

The scripts must have run first. What each result forces is fixed in section 18, before the job. No recipe result exists at that point, so revision is allowed.

### 2.2 Freeze B, after the Freeze-B run, before any evaluation sample exists

Only these items, each by its rule [2]:

| Item | Rule |
| --- | --- |
| Recipe identity | Commit of each named recipe, by hash |
| Configuration | Full effective configuration, by hash |
| Algorithmic budgets | Seeds, branches, multistart count, iterations (K10), by hash |
| `r_dev` | Per noise bin, recorded for test F2 (section 8.3). `C` and `tau` are not set here |

Bin edges and valid ranges are not in this list. All are fixed at Freeze A (sections 3.3, 4), so none depends on recipe output, and none can change at any Freeze B.

**Forbidden in configuration [R12].** Configuration may not contain any scale, offset or inflation derived from pulls or from T08 targets. Any such constant found makes the gate result void for that parameter, and void counts as fail. Constants written in this document (`q`, `sigma_n`, `W`, thresholds, section 7.1) are not derived and are allowed.

The **Freeze-B run** is one run at the recipe hash to be frozen, on a reserved seed block (section 3.2). Only this run feeds Freeze-B records. Tuning runs feed nothing. A new Freeze-B block needs a recorded functional change of the recipe [M7]; a change of hash alone does not earn one. Every such run is kept and reported, and only the last counts, because it matches what is evaluated.

### 2.3 What development may show

If a recipe believed correct falls outside the conditions in section 5.4, or a Freeze-A value proves unreachable, the agent changes nothing [11]. The result stands and is reported. Only the user can amend Freeze A. Such an amendment is labelled "after development", the hash changes, and results are reported under both rules (Section 1.3 items 6 and 8).

## 3. Sample roles and attempts

### 3.1 Roles

Tuning, Freeze-B and evaluation samples use different seeds, generated from the same fixture. They share geometry, conditions and generator, so they are independent only at the level of random seed (Section 11.3.2). These results support no claim beyond the fixture. Tuning on an evaluation sample uses it up (A54).

### 3.2 Seeds and development size

Each event's generator state is `numpy.random.SeedSequence([fixture_id, block, stratum, event_index])`, or the same four integers hashed by the C++ driver.

| Fixture | `fixture_id` |
| --- | --- |
| T07 clean, T07 noise | 7001, 7002 |
| T08 main, edge, dead, saturation | 8001, 8002, 8003, 8004 |
| T09 main, dead, saturation, two-source | 9001, 9002, 9003, 9004 |

| Block | Role |
| --- | --- |
| 1 | Tuning, any size within approved jobs |
| 2, 3, 4 | Freeze-B runs before attempt 1, in order, each after a recorded functional change. When they are used up, the workflow is `blocked-by-decision` until the user answers |
| 5 | The Freeze-B run before attempt 2 |
| 6 | Generator checks (section 2.1) and the fixed likelihood points (section 9.3) |
| 11, 12 | Evaluation attempts 1 and 2 |

| Freeze-B run size, events per bin | Value | Reason |
| --- | --- | --- |
| T07 noise | 12,000 | Same as evaluation, so the two-sample test has equal samples |
| All others, and each control | 3,000 | Cost record and smoke check only. Nothing else depends on them |

Totals, closed form: T07 180,000 events (noise 144,000, clean 36,000); T08 45,000; T09 45,000 (15 samples of 3,000 each).

### 3.3 Valid ranges

Outside a range a pull is ungated (section 10). Every range is fixed at Freeze A. **No range changes at any Freeze B** [R2]: E2 and B2 are required, and a method limit there fails the workflow until the user amends Freeze A (section 16).

| Range | Quantity, truth only | Value | Rule behind the value |
| --- | --- | --- | --- |
| T07 `q/p` | `sigma(q/p)/|q/p|`, closed form, at each bin's upper edge | At most 0.10. 24 GeV gives 0.0988, so all 4 momentum bins are inside | Closed form from the fixture |
| T08 pulls | Seed reference `p` at the bin's lower edge | `p` at least 0.99: E2-E4 gated, E1 ungated | Below this, a pull is conditional on the same cells firing the seed, so its target is not `E_ref`. Closed form: sub-cell mean `p` is 0.84 at E1's lower edge, 0.77 at a cell corner (Poisson-exact, recheck), 1.000 at 0.25 GeV [R10, S4] |
| T09 pulls | Truth expected photons `N_exp` | At least 120: B2-B4 gated, B1 ungated | Seven-parameter check, job 7477126: 80 does not clear (`E_vis` centre -0.062 pooled, -0.111 at `r/R_s` [0.4, 0.7)), 120 clears, so the rule of section 18.1, row T09 range, sets 120. The toy alone had suggested 80: in a one-parameter toy with Hessian uncertainty, trimmed centre `-0.3125/sqrt(mu)` reaches 0.0356 at mu = 77 [18]. Mean bias `-0.5/sqrt(mu)` would reach it at 197. Trimmed values at 20, 50, 80, 200: -0.070, -0.044, -0.035, -0.022. |

### 3.4 Attempts [6]

| Rule | Value |
| --- | --- |
| Attempts | At most 2 evaluation attempts per workflow. See section 16 for the cap |
| Run | One run per attempt, on its declared block. A failure stands (finish-plan D4, step 4) |
| Between attempts | Only after a recorded method change (R11). A change returns to Freeze B: new recipe hash, new Freeze-B run on block 5, the user's word |
| On that return [R1] | Valid ranges stay as frozen, and any outcome stays final. Only recipe, configuration and budget hashes and `r_dev` renew. No required test can leave the required set |
| Attempt 2 level | Pass bounds use 99 %, `z = 2.326`, in place of 95 %, on every test. Closed form: a bin at true error 0.10 passes 5 % then 1 %, at most 5.95 % over both, against 9.75 % plain. Five plain attempts would give 22.6 % |
| Top-up | Never. A short bin stays short |
| Counted | An inconclusive attempt counts as an attempt |
| Reported | The attempt count appears with any pass |
| After attempt 2 | `failed` stands. Anything further needs a Freeze A amendment by the user |

Attempt 2's slack, closed form: 0.0369 at `se` 0.0095, 0.0283 at the cap.

## 4. Fixture table

Every value below is a **design choice**, for synthetic data. Units are named GeV, mm, ns for convenience, and no detector is implied [1]. Nothing here is a physics or instrument claim. The only outside number is the unit conversion 0.299792458 GeV/(T m), from the defined speed of light.

Each event belongs to one stratum, fixed by the generator before any random draw. Stratified generation: exactly 12,000 events per bin. Every object in an event takes that event's bin, so no reconstructed object can fall outside all bins [5].

### 4.1 T07 telescope

Generator and version field: `t07-telescope-clean/1`, `t07-telescope-noise/1`. C++ driver using the ACTS 48.2.0 propagator through the same geometry, as the sheet says. Generator hash: section 2.1. Fixture frame: z along the telescope, u bending, v along the field. In the ACTS frame the telescope runs along x and the field along z, so fixture v is ACTS z, the axis of the vertex seeder [R14].

| Parameter | Clean | Noise |
| --- | --- | --- |
| Planes | 8, at z = 0, 50, ..., 350 mm | Same |
| Active area | 300 x 300 mm | Same |
| Material | None. Material comes after the first pass (sheet), so this axis is an open obligation | Same |
| Measurement | Two-dimensional, Gaussian, `sigma` 0.020 mm in each coordinate | Same |
| Field | Uniform 1 T, along local v, so u bends | Same |
| Particle | One species, mass 0.1 GeV, charge +1 or -1. Mass has no effect with no material | Same |
| Momentum bins, GeV | [1.5, 3), [3, 6), [6, 12), [12, 24), uniform in ln p. All tracks in an event share the bin | Same |
| Occupancy levels | o1, o2, o3: exactly 6, 12, 36 truth tracks per event | Same, plus noise below |
| Noise hits per plane per event, Poisson mean | 0 | 100, 300, 1000 at o1, o2, o3 |
| Noise hit position | None | Uniform over the plane |
| Hit efficiency | 1.0 | 0.98 per plane, independent |
| Charge | Exactly half positive, half negative in each event | Same |
| Vertices per event | 2, 2, 3 at o1, o2, o3. So 3, 6, 12 tracks per vertex | Same |
| Vertex position | First vertex: u uniform +-0.05 mm, z uniform -100 +- 0.2 mm, v uniform +-30 mm. Further vertices share u and z with small independent draws from the same u and z ranges, and differ in v | Same |
| Vertex separation | Along v, in one direction, so the third vertex lies beyond the second. 80 % of events (`event_index mod 5 != 0`): "far", each step uniform [5, 25) `u_v`. 20 %: "near", each step uniform [1, 5) `u_v` | Same |
| `u_v`, the resolution unit | 0.0184 mm: single-track v uncertainty at z = -100 mm, closed form, a constant of the fixture | Same |
| Track slopes at the vertex | Uniform +-0.15 in each view | Same |
| Fiducial | All tracks cross all planes, by construction: largest excursion about 120 mm against a half-width of 150 mm. No resampling | Same |
| Beam constraint | None in the recipe (BP04). Nominal u, z is a design constant for a perigee reference, not per-event truth | Same |

| Expected per event | o1 | o2 | o3 |
| --- | --- | --- | --- |
| Truth tracks, per charge | 6, 3 | 12, 6 | 36, 18 |
| Truth vertices | 2 | 2 | 3 |
| Noise hits per plane (noise fixture) | 100 | 300 | 1000 |

Closed-form facts of this fixture:

| Quantity | Value |
| --- | --- |
| `sigma(q/p)` | 0.00412 per GeV, so `sigma(q/p)/|q/p|` is 0.0062 at 1.5 GeV, 0.0988 at 24 GeV |
| Reconstructable, noise fixture | P(at least 6 of 8 hits) = 0.99958 |
| `p_w`: chance that a noise hit falls in a 0.15 mm circle, per plane, at o1, o2, o3 | 7.9e-5, 2.4e-4, 7.9e-4 |
| Clean overlap bound | At most 0.0024 of tracks at o3 have another track's hit within 0.15 mm on some plane, taking tracks spread over 90 x 90 mm. An estimate |
| Ideal wrong assignment, Gaussian, midpoint rule | 0.62 % at exactly 5 `u_v`; 0.020 % averaged over [5, 25); 0.027 % at o3, where the middle vertex has two neighbours [R13]. Vertices lie on a line, so non-neighbours are at least 10 `u_v` apart |
| Largest offset from the nominal line | 0.08 mm: 1.9 single-track sigma, inside the seeder's default d0 significance cut of 3.5 (read from the installed header, not run) |

**Analytic references**

| Gate | Clean | Noise |
| --- | --- | --- |
| Track efficiency | `R = 1`. No noise, no missing hits; overlap bound above | No exact value. Closed-form lower limit `R_floor(o) = (1 - p_w)^8` = 0.99937, 0.99812, 0.99374: a reconstructable track with no noise hit in its window is unambiguous. Plus the paired truth-seeded comparator |
| Fakes | Expected 0 | `f_ref(o)`, section 8.3 |
| Vertex finding | **None exists.** A floor applies instead, on far vertices. This is a design requirement, not closure against a reference (section 8.5) | Same |

A recipe that seeds only from planes 1-3 loses 5.9 % on the noise fixture by construction (`1 - 0.98^3`), and fails the floor. That is intended: the denominator is the fixture's, not the recipe's.

**CAI items.** The sheet requires them. `CAI-T07-1`, `-2` and `-3` use the clean geometry with one track per event: 16 measurements, so the fit stays overdetermined without the tested hit in both views. `CAI-T07-4` uses its own sagitta-like deformed variant of that geometry. Tolerances are recorded before each run (R37). They are interface checks, outside these gates and the budget.

### 4.2 T08 grid

Generator and version field: `t08-grid/1`, NumPy `Generator` with PCG64. Round 1 used noise 1 MeV and cell threshold 3 MeV. These gave a threshold loss of 17 MeV, up to 1.9 sigma, and a noise-driven excess in the energy spread (model over true 0.85 at 0.25 GeV). The values below remove both, by arithmetic, with no gate widened [R4]. The price is stated in Known limits: noise becomes nearly invisible to these gates [S5].

| Parameter | Main | Edge control | Dead control | Saturation control |
| --- | --- | --- | --- | --- |
| Grid | 40 x 40 cells, cell width 1 unit, analog, one longitudinal layer | Same | Same | Same |
| Shower profile | Two-dimensional Gaussian, width `W` = 1 cell, integrated per cell: `g_c(x, y)` | Same | Same | Same |
| Cell deposit | `q x Poisson(E g_c / q)`, `q` = 0.2 MeV | Same | Same | Same |
| Electronics noise | Gaussian, `sigma_n` = 0.2 MeV per cell | Same | Same | Same |
| Cell threshold, seed threshold | `T_c` = 0.6 MeV, `T_s` = 10 MeV | Same | Same | Same |
| Gain, pedestal chain | Gain 1, pedestal 0 in the gated fixture, kept as separate fields. CAI tests vary them | Same | Same | Same |
| Energy bins, GeV | E1 [0.08, 0.25), E2 [0.25, 1), E3 [1, 4), E4 [4, 16), uniform in ln E | E3 | E3 | E4 |
| Separation strata | iso: one shower. far: two showers, `d` uniform [3, 8) `W`. near: two showers, `d` uniform [1.5, 3) `W`. Both showers share `E` | iso | iso | iso |
| Shower position | At least 6 `W` from any edge, uniform | Distance to one edge exactly `t` = 0.5, 1, 1.5, 2 `W`, a quarter of events each. The edge is a cell edge. Other axis uniform | Uniform within the dead cell | As main |
| Dead cells | None | None | One: the cell containing the shower centre | None |
| Saturation | None | None | None | Cell clips at 0.4 GeV after noise is added, so every E4 shower clips [M1]. The readout carries a per-cell saturation flag, set at that point, before gain |
| Two-shower geometry | Azimuth of the pair uniform in [0, 2 pi). The midpoint is uniform, subject to both showers lying at least 6 `W` from any edge, by choosing the midpoint range for the largest `d`; no resampling [S11] | | | |
| Events | 12,000 per bin, 144,000 | 12,000 | 12,000 | 12,000 |

Expected objects per event: 1 shower (iso, controls), 2 (far, near).

**Targets.** Each is an explicit function of named truth quantities [R3]. Constants `b` come from the reference clusterer of section 7.1, and are frozen with the job log. The frozen log is job 7479146's. Its `b`, `se`, `sd` and `model` values equal job 7474461's, so a value labelled job 7474461 here is the same in both. `b` uses the trimmed mean, as the gate does [S12]. `b_iso`, `b_edge(t)`, `b_dead` are unweighted means of node values over gated nodes: `E` at or above 0.25 GeV for iso, E3 nodes for the controls [S11]. Closed form values are the independent-cell estimate, a check on the script.

| Stratum | Target | Closed-form check |
| --- | --- | --- |
| iso | `E_ref = E - b_iso` | `b_iso` 2.907 MeV (job 7474461; largest node departure 0.0128 sigma, inside section 18's limit), so one constant serves. Sub-cell spread at most 0.018 sigma |
| far, per shower | `E_ref = E - b_far(E, d)`, bilinear in (ln E, d) on the script's nodes | `b_far` 1.3-3.0 MeV on the 63 gated nodes, mean 2.05 (job 7479146). The independent-cell estimate 2.3-3.3 is high by up to 0.5 MeV at small `d`, at 250 MeV. The log's table governs. Spread over azimuth and sub-cell about 0.09 sigma at 0.25 GeV and 0.04 sigma at 2 GeV or more (recheck, 5 azimuths and 3 sub-cells [M5]), against round 1's 2.2 sigma, with 30 sharing iterations. Added width about 1.004 |
| near, event | `E_ref = 2E - b_near(E, d)`, same interpolation | `b_near` 3.3-3.9 MeV over `d` 1.5 to 3, spread at most 0.008 sigma |
| Dead | `E_ref = E (1 - f(x, y)) - b_dead`, `f = g_c` of the dead cell at truth `x, y`, closed form | Unconditioned, `f` has sd 0.0061, which would give pull width about 1.4 at 4 GeV. Conditioned, residual spread at most 0.014 sigma, `b_dead` 2.855 MeV (job 7474461) |
| Edge | `E_ref = E Phi(t) - b_edge(t)`, for each of the four exact `t` | `b_edge` 1.503, 1.633, 1.701, 1.967 MeV at `t` 0.5, 1, 1.5, 2 (job 7474461), spread at most 0.013 sigma. Discrete `t` removes round 1's interpolation error. `Phi(t)`: 0.6915, 0.8413, 0.9332, 0.9773 |

Interpolation error is under 0.002 sigma on the iso grid (recheck, closed form). Below 0.25 GeV pulls are ungated, so no target is needed.

**Other references**

| Quantity | Reference |
| --- | --- |
| Contained energy, main | `E`, to better than 1e-8: 6 `W` from any edge |
| Efficiency, iso and far | Closed form per shower, exact cell response: `p = 1 - prod_c P(cell c < T_s)`, each cell `q x Poisson(E g_c/q)` plus Gaussian noise `sigma_n`. The Gaussian form used before overstated `p` by 0.0031 at 80 MeV (job 7477066). `R` is the integral over ln E and sub-cell position, not a node sum: 0.992 in E1 (`p` 0.84 at the lower edge, 0.77 at a cell corner), 1.000 in E2-E4 [S4]. The far case takes each shower alone, checked by a section 18 row |
| Efficiency, near | **None exists.** Reported only |
| Reference's own uncertainty [M6] | Statistical error of `b` at a node at most 0.011 sigma (8,000-event control nodes), usually less. The 7 gated far nodes at `d` = 3 print more, 0.013 to 0.040 sigma, because the printed `se` is `sd/sqrt(n)` and rare far outliers make `sd` 2 to 6 times `model`. `b` is a trimmed mean, which those outliers do not reach: from the core width, `1.03 s_68/sqrt(n)` gives at most 0.0067 sigma over all 63 gated far nodes (job 7479146), so 0.011 stands. It enters section 5.4 |

This is closure of the recipe against an independent coding of the same clustering definition. It is not a test of that definition. The sheet's open item on Geant4 tuning is closed for this fixture: none. Any tuned profile would be a new version.

### 4.3 T09 sphere

Generator and version field: `t09-sphere/1`, NumPy `Generator` with PCG64. Events follow a stated analytic light model. This is shared-model closure (Section 11.1): it tests the code, not the model.

| Parameter | Value |
| --- | --- |
| Sphere radius `R_s` | 5 m |
| Sensors | 1,000, Fibonacci lattice: for i = 0..999, polar angle `arccos(1 - 2(i + 0.5)/1000)`, azimuth `pi (1 + sqrt 5)(i + 0.5)`. Area 0.094 m2 each |
| Medium | One, uniform. Photon speed 0.22 m/ns, attenuation length 30 m. A second medium is an open obligation |
| Emission density | `g(c) = (1-f)/(4 pi) + f k exp(k c)/(4 pi sinh k)`, `c` = cosine to the direction, `f` 0.6, `k` 5 |
| Expected signal, channel i | `mu_i` proportional to `area x cos(incidence)/d^2 x exp(-d/30 m) x g(c)`, scaled so that `sum_i mu_i = N_exp`. With `S` the sum of the unscaled shape at that vertex and direction, `E_vis = N_exp / (1000 S)`, so `N_exp` sets `E_vis` |
| Signal count | Poisson(`mu_i`) per channel |
| Dark noise | Mean 0.002 per channel per 200 ns window, uniform in time |
| Time spread | Gaussian, 1.5 ns, per photon. Instant emission |
| Readout | Charge: sum over photons of Gaussian(1, 0.3). First-arrival time of the channel |
| Charge threshold | 0.25 |
| Saturation | None in main. Control: 5, censored. The readout carries a per-channel `saturated` flag |
| `N_exp` bins | B1 [20, 120), B2 [120, 200), B3 [200, 500), B4 [500, 2000), uniform in ln N |
| Radial bins, `r/R_s` | [0, 0.4), [0.4, 0.7), [0.7, 0.9), uniform in volume within the bin |
| Direction | Isotropic |
| `t0` | Uniform [10, 30] ns |
| Events | 12,000 per bin, 144,000 |

| Control | Change from main | Events |
| --- | --- | --- |
| Dead | The 200 channels nearest the +z axis dead. `N_exp` B3, `r/R_s` [0.4, 0.7) | 12,000 |
| Saturation | Clip at 5. `N_exp` B3, `r/R_s` [0.7, 0.9) | 12,000 |
| Two-source | Two sources, each `N_exp` B3 independently. Midpoint uniform in the ball of radius 0.3 `R_s`; separation uniform [0.4, 1.2] `R_s` along an isotropic axis, so radii stay under 0.9 `R_s`. Directions independent, isotropic. Same `t0` | 12,000 |

Expected objects per event: 1 fit of each hypothesis. Two sources in that control.

**Analytic references.** Truth parameters are exact. `N_exp` and `mu_i` are closed form. No analytic efficiency applies, because T09 fits every event: fit failure takes its place. No analytic reference exists for wrong minima or topology. The rates are judged against limits and a truth-start comparator (section 9).

### 4.4 Recheck of statistical claims against the fixtures

Findings 7, 8, 10, 11. Closed form. "Worst" means fully correlated objects, `n_eff` = events. `se` constants: 1.03 and 0.962 over `sqrt(n)`. Retention is an assumption, shown so it can be checked.

| Sample, per bin | Retention assumed | `n`, independent objects | Centre `se` | `n`, worst | Centre `se`, worst | Width `se`, worst | Under cap 0.0108? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T07 tracks, o1 | 0.98 | 70,560 | 0.0039 | 11,760 | 0.0095 | 0.0089 | Yes |
| T07 `q/p` per charge, o1 | 0.98 | 35,280 | 0.0055 | 11,760 | 0.0095 | 0.0089 | Yes [8] |
| T07 vertices, far, o1 | 0.95 | 18,240 | 0.0076 | 9,120 | 0.0108 | 0.0101 | Yes, just. Needs retention at least 0.948 at worst. See Known limits [M8] |
| T07 angle slice, pooled | 0.98 | 211,680 | 0.0022 | 35,280 | 0.0055 | 0.0051 | Yes |
| T08 iso | 0.98 | 11,760 | 0.0095 | 11,760 | 0.0095 | 0.0089 | Yes |
| T08 far | 0.98 | 23,520 | 0.0067 | 11,760 | 0.0095 | 0.0089 | Yes |
| T09 bin | 0.99 | 11,880 | 0.0094 | 11,880 | 0.0094 | 0.0088 | Yes |
| Controls | 0.95 | 11,400 | 0.0096 | 11,400 | 0.0096 | 0.0090 | Yes |

So no bin is inconclusive by construction, for any correlation, at these retentions. Generating per charge is unnecessary [8]: every event carries at least 3 tracks of each charge, and even if they were fully correlated each charge would have 12,000 events.

## 5. Statistical design

### 5.1 Core

| Item | Proposal |
| --- | --- |
| Statistical unit | The event. Every uncertainty comes from a bootstrap over events, or the effective count below |
| Bins | 12 per fixture (4 x 3), in truth, by event stratum. Edges fixed in section 4 |
| Generation | Stratified, 12,000 events per bin |
| Robust centre | Trimmed mean of pulls, 10 % cut from each side [19]. Not the mean: mean and RMS are always reported beside it. Design `se` `1.03/sqrt(n)` |
| Core width | `sigma_68`, half the central 68.27 % interval. Design `se` `0.962/sqrt(n)` [20] |
| `se` in a gate | Event bootstrap of that statistic in that bin, B = 1,000 replicates, seeded from the bin's identity. Design formulas are for design only |
| Precision cap | 0.0108 for centre and width. This is `n` of about 9,100 and 7,900, and keeps slack at least 0.035 at the cap [7]. It replaces v3's 0.0129 and 0.0119 |
| Pull population | All primary matched objects, wrong minima included. Objects with no result count in a failure rate |
| Tolerance | 0.10 on centre and on `sigma_68 - 1`. See section 16 |
| Target | Centre 0, width 1 |

### 5.2 Test results

**Pull tests.** With `e` = |estimate - target|, in this order [17]:

| Step | Condition | Result |
| --- | --- | --- |
| 1 | `e - 1.645 se > 0.10` | fail, whatever the cap says |
| 2 | `se > 0.0108` | inconclusive |
| 3 | `e + 1.645 se <= 0.10` | pass |
| 4 | Otherwise | fail |

With `sigma_68` scaling its own `se`, a width near 1.12 at n = 10,000 reaches the cap, and step 1 catches it. Closed form: `se` reaches the cap at width 1.123 at n = 10,000, where step 1 reads 0.105.

**Rate tests with an upper limit `L`.** `k` failures, `n` objects, `N_ev` events, `m = n/N_ev`, `N_min = 30/L` events. One rule for all `k` [9]:

| Quantity | Definition |
| --- | --- |
| `DEFF_hat` | Between-event ratio estimator: `var = N_ev/(N_ev - 1) x sum_e (y_e - p m_e)^2 / n^2`, `p = k/n`, and `DEFF_hat = var / (p(1-p)/n)`. `y_e`, `m_e`: failures and objects in event e. Equals 1 by definition at `k` = 0 |
| `U_A` | Clopper-Pearson upper bound on effective counts: `D = max(1, DEFF_hat)`, `n_eff = n/D`, `k_eff = k/D` |
| `U_B` | Clopper-Pearson upper bound with events as the unit: `n_eff = N_ev`, `k_eff = min(k, 30)/m` |
| `U` | `max(U_A, U_B)`. At `k` = 0 this is `1 - 0.05^(1/N_ev)`, as in v3 |

| Step | Condition | Result |
| --- | --- | --- |
| 1 | Clopper-Pearson lower bound on set A's effective counts (`k/D`, `n/D`) above `L` | fail, whatever the count |
| 2 | `N_ev < N_min` | inconclusive |
| 3 | `U <= L` | pass |
| 4 | Otherwise | fail |

Closed form, at `DEFF_hat` = 1: `U` is non-decreasing in `k` for `N_ev` 300 to 12,000 and `m` 1 to 100, with `k` up to 400. On v3's example, 200 events of 10: 1.49 %, 1.58 %, 1.67 %, 1.76 % at `k` = 0, 1, 2, 3. v3 gave 1.49 %, then 0.24 %.

| `L` | `N_min`, events | Zero-failure bound there |
| --- | --- | --- |
| 1 % | 3,000 | 0.10 % |
| 0.5 % | 6,000 | 0.05 % |

The rule's rate with varying objects per event, `calc-rate-rule.py`, job 7474461: pass at `L` at most 7.0 % in 132 scenarios, pass at slack at least 99.7 % in all. It replaces the reviewer's `calc-deff-unequal.py`, because the zero rule changed. Earlier rule: at exactly 10 objects per event and a true rate at the limit, it passed 4.2-5.7 %, against 4.3-24.7 % for plain Clopper-Pearson on objects.

**Efficiency tests.** The failure rate is `1 - efficiency`, on the same rule. The lower bound on efficiency is `1 - U`, and `L` is `1 - (R - delta)`. `N_min` is 3,000 events.

Margin, frozen as a formula of the reference [10]:

`delta(R) = max(0.01, 5.961 sqrt(R(1-R)/10000))`

| `R` | `delta` | False failure per test, `n` = 10,000, closed form |
| --- | --- | --- |
| 1 - 1e-4 | 0.0100 | under 1e-20 |
| 0.98 | 0.0100 | 1.9e-8 |
| 0.975 | 0.0100 | 9.7e-7 |
| 0.97 | 0.0102 | 7.9e-6 |
| 0.95 | 0.0130 | 7.9e-6 |
| 0.90 | 0.0179 | 7.9e-6 |

No reference in these fixtures falls below 0.98 as a bin mean (0.992 is the lowest, section 4), so `delta` is 0.01 throughout. The formula covers a changed fixture.

**Paired comparisons.** Bootstrap over events of the paired difference, one-sided 95 %, B = 1,000.

### 5.3 Error budget

Every gate counts. The budget is a union bound: `alpha = 0.01/M`, with no independence needed [19]. Failure is one-sided for a true error of one sign, so `z` is one-sided: `z1`. All T07-T09 gates use T07's count.

| Workflow | Tests | Composition |
| --- | --- | --- |
| T07 | 1,260 | 360 track pulls (12 bins x 2 fixtures x 5 x 3) + 144 `q/p` per charge (12 x 2 x 2 x 3) + 216 vertex pulls (12 x 2 x 3 x 3) + 72 clean rates (12 x 6) + 96 noise rates (12 x 8) + 252 refit (12 x 21, clean) + 120 angle (4 x 2 x 5 x 3) |
| T08 | 101 | 40 iso (4 x 10) + 43 far (4 x 10 + 3 merge) + 12 near (4 x 3) + 6 controls |
| T09 | 333 | 288 main (12 x 24) + 45 controls (21 + 21 + 1 + 1 + 1) |

Closed form, M = 1,260: `alpha` 7.94e-6, `z1` 4.316, `1.645 + z1` = 5.961. These numbers do not enter any pass rule. They enter slack only.

`slack(se) = 0.10 - 5.961 se`

| `se` | Where | Slack |
| --- | --- | --- |
| 0.0095 | 12,000 generated, 0.98 retained, centre | 0.0434 |
| 0.0103 | `n` = 10,000, centre | 0.0386 |
| 0.0096 | `n` = 10,000, width | 0.0427 |
| 0.0108 | The cap | 0.0356 |

### 5.4 Conditions for the 1 % family target

The target is at most 1 % false failure per workflow, **if all of these hold** [11]:

| Condition | Stated value |
| --- | --- |
| True centre and width error in every gated bin | Within `slack(se)`: 0.0356 at the cap, 0.043 near design. T08 energy: less the reference's own error, 0.011 sigma, so 0.0246 and 0.0324 [M6] |
| T08 pull model | Model over true sd at least 0.983 (closed form), so added width at most 0.017, inside the slack. Job 7479146: 0.979 at node level, at the iso nodes of 250 and 297 MeV. Sharing spread about 0.09 sigma at most. Pulls with sharing near `d` = 3 are checked only by `calc-t08-reference.py` [11] |
| T08 far position | Asymmetric truncation pulls each two-peak centroid inward. Expected image, hard threshold, rms bias against the Fisher sigma: 0.36, 0.34, 0.32, 0.31, 0.15 at `d` = 3, 3.5, 4, 5, 6 at 0.25 GeV; 0.23-0.16 at 1 GeV; about 0.12 at 4 GeV. Closed-form bin-level width about 1.026 (E2), 1.010 (E3), 1.004 (E4), inside the position slack of 0.0356, by 0.01 in E2. Coarse [S3]. Job 7479146, `|s68 - 1|` x and y on `BIN` lines. Far from `d` 3: 0.0069, 0.0097 (E2), 0.0035, 0.0017 (E3), 0.0005, 0.0003 (E4). Iso: 0.0078, 0.0080 (E2), 0.0015, 0.0005 (E3), 0.0020, 0.0018 (E4). So E2 widths are 1.007-1.010 in far and 1.008 in iso, under the coarse 1.026. The tightest T08 position width is far E2 y, 0.0097 against the slack of 0.0356. The tightest T08 width of any kind is iso E2 energy, 0.0117 against 0.0246 |
| T09 penalty | The H1-truth tail above 30: 3 of 600 at `N_exp` 50, exactly at 0.5 %, and 0 of 600 at 1,000 (job 7474462). The penalty stays 30, with no margin at 50 [R8] |
| `se` | At or under the cap |
| True rate under a limit | Under the rate slack, below |
| Skew of pulls | The trimmed centre moves by about `-0.0937 gamma` (Cornish-Fisher). So `|gamma|` at most 0.38 at the cap, 0.46 at `se` 0.0095 |
| True efficiency | At or above the reference |
| Noise fake rate | Under the limits in section 8.3 |

Rate slack: the largest true rate with false failure at most `alpha`, closed form, exact binomial at known DEFF.

| `L` | `n_eff` | `r_slack` | `r_slack / L` |
| --- | --- | --- | --- |
| 1 % | 3,000 (minimum) | 0.224 % | 0.22 |
| 1 % | 9,600 | 0.491 % | 0.49 |
| 1 % | 12,000 | 0.535 % | 0.54 |
| 1 % | 72,000 | 0.791 % | 0.79 |
| 0.5 % | 6,000 (minimum) | 0.112 % | 0.22 |
| 0.5 % | 12,000 | 0.198 % | 0.40 |
| 0.5 % | 72,000 | 0.356 % | 0.71 |

For objects of equal number per event, `n_eff` cannot fall below the event count. So 12,000 events give a rate slack of 0.54 L at `L` = 1 % and 0.40 L at `L` = 0.5 %, at any correlation. The tail gate's Gaussian 0.27 % is inside this. v3's "74 % at half the limit" came from 1,000 events of 10 (earlier rule) and does not describe these samples.

Outside these conditions a correct recipe may fail. Section 2.3 says what follows.

### 5.5 Behaviour of one bin

Closed form, Gaussian pulls, one bad bin, pass probability.

| True error | `se` 0.0095 | `se` 0.0103 | `se` 0.0108 |
| --- | --- | --- | --- |
| 0.04 | 1.0000 | 0.9999 | 0.9999 |
| 0.06 | 0.995 | 0.987 | 0.980 |
| 0.08 | 0.677 | 0.617 | 0.582 |
| 0.10 | 0.050 | 0.050 | 0.050 |
| 0.12 | 0.0001 | 0.0002 | 0.0002 |

So an error of 0.10 or more across a whole bin is found at least 95 % of the time. Errors within `slack(se)` pass. Between them the outcome is uncertain. That band is accepted, not hidden.

Table with the gate's own bootstrap, fail and inconclusive labels: `calc-pull-table.py`, job 7474461 [20]. At a true error of 0.10 a single bin passes 4.0 % (centre) and 4.8 % (width), under the rule's 7.9 %; no fail at state `none`. Earlier rule: v3's "directly simulated" table (3,000 trials, `t04_v2_b.py`, fixed design `se`, limits from 1.012). "100 % in 3,000" bounds failure only at about 0.1 %. So the family target is a Gaussian extrapolation, not a measurement. Width 1.10: 5.0 % is the closed form with a scale-aware `se`; the gate's bootstrap measured 4.8 %, job 7474461.

## 6. Common gates

| Gate | Rule |
| --- | --- |
| Location | Pull test on the trimmed centre |
| Width | Pull test on `sigma_68 - 1` |
| Tail | Rate test, `P(|pull| > 3)`, `L` = 1 %. For 10,000 independent objects this is at most 83. Gaussian 0.27 %, leaving room for about 0.55 % of other entries. Unit-variance Student-t (5 d.o.f.) pulls fail the width gate (`sigma_68` 0.86) |
| Reported beside every gate | Mean and RMS of pulls. A skewed distribution, or 0.5 % of entries at pull 20 (mean 0.10, RMS 1.73), can pass; a reader must not treat a pass as Gaussian behaviour |

## 7. Definitions

Blocker 5. Quantities are fixed here. Each recipe's output must supply them.

| Item | Definition |
| --- | --- |
| Occupancy | Number of truth tracks in the event, 6, 12 or 36, a generator field. On the noise fixture the level also sets the noise rate. Never measured from reconstruction |
| Reconstructable track | Truth particle with at least 6 hits on distinct planes in the generator record. No recipe setting enters [10] |
| Track match | A track matches a particle if more than 50 % of the track's measurements, noise hits included in the count, come from it. A track can match one particle at most, so ties cannot arise in this direction |
| Primary, one-to-one rule | A particle with several matched tracks keeps one primary: highest matched fraction, then most hits, then lowest chi2/ndf, then lowest track index. Efficiency and pulls use primaries only |
| Efficiency, tracks | Reconstructable particles with a primary, over reconstructable particles |
| Fake | A reconstructed track matching no particle. Denominator: all reconstructed tracks in the bin's events |
| Duplicate convention | Reconstructed convention (11.3.1): matched tracks that are not primary, over all matched tracks. Applies to both fixtures |
| Track state, surface | **Smoothed** state at plane 1, bound parameters `loc0, loc1, phi, theta, q/p`, against truth at plane 1. Covariance from the same smoothed state. A track with no plane-1 measurement, or starting at a later seed, has its first smoothed state propagated to plane 1 with its covariance, and stays in the pull population [R16]. Predicted and filtered states and unbiased residuals are reported apart and never mixed (BP03) |
| Truth-seeded run | CKF started from the exact truth state at plane 1, with covariance diag(0.1 mm, 0.1 mm, 0.01, 0.01, 0.1 |q/p|) squared, and no seed finder. Comparator only, never reported as finding |
| Bin of `q/p` range and charge split | Valid range: per bin, from truth `|q/p|` at the bin's upper edge. Charge split: per object, by the truth charge of the matched particle |
| Charge sign | Wrong sign: primary track whose fitted `q/p` has the opposite sign to truth. Denominator: primary tracks |
| Angle slices | Pooled over the 12 bins, per fixture. Truth u-slope at the vertex: [-0.15, -0.075), [-0.075, 0), [0, 0.075), [0.075, 0.15]. They are sign-aware on purpose |
| Vertex bins | The event's stratum, momentum x occupancy. This resolves v3's conflict between "event-level quantities" and momentum x occupancy |
| Reconstructable vertex | Truth vertex with at least 3 reconstructable tracks. "The fixture's minimum track count" is this 3 |
| Vertex match | A reconstructed vertex matches a truth vertex if that vertex supplies more than 50 % of the summed track weights. Weights of tracks with no truth match stay in the denominator |
| Vertex primary | Highest share, then most tracks, then smallest distance to truth, then lowest index |
| Vertex pull | Fitted x, y, z in the global frame, primaries, far events only. Near events are reported |
| Wrong assignment | A primary track with weight at least 0.5 in a matched vertex that is not its truth vertex. Denominator: primary tracks with weight at least 0.5 in matched vertices. Far events only |
| Cluster match | A shower's energy in an object is `sum_c f_kc d_sc`, `d_sc` its truth deposit, noise excluded [S11]. A cluster matches the shower supplying more than 50 % of that energy. A cluster can match one shower at most. Primary: highest energy share of that shower, then highest cluster energy, then lowest index |
| Shower efficiency | Showers with a primary cluster, over showers in the bin |
| Merge | Two-shower event in which both showers give their largest energy share to one object. Denominator: far events, E2-E4. The event is the object |
| Split | Showers with more than one matched cluster. Reported |
| T08 parameters, 3 | Named energy "clustered deposited energy", and x, y of the object. Truth x, y: shower axis. Never called incident energy. Clustering, estimators and uncertainties: section 7.1 |
| T09 parameters, 7 | Vertex x, y, z; time `t0`; two direction components in the tangent plane at the truth direction; visible energy `E_vis`. Frame at truth direction `d`: `e_1 = a x d`, normalised, `e_2 = d x e_1`, with `a` the z axis, or the x axis where `|d_z|` exceeds 0.9, so it is defined at the poles. Residuals are `(d_fit - d) . e_k`; uncertainties come from the covariance in those local coordinates. Fitted angles never enter a pull directly |
| Fit failure | Fit returned no result, no finite covariance, or hit its iteration budget. Denominator: all generated events |
| Truth-start fit | The same recipe started at truth, scoring side only. Never reaches the data side (A09), never reported as a result |
| Wrong minimum | Either: (a) truth-start fit reaches `lnL` at least 0.5 higher than the reported fit; or (b) any of the 7 parameters more than 5 of its truth-start uncertainties from truth. Clause (b) is any-parameter, not chi2: for a correct fit it has rate 4.0e-6, while chi2 with 7 d.o.f. above 25 has 7.6e-4 [5]. Clause (b) applies exactly where pulls are gated, B2-B4 [M5]. In B1 only clause (a) is gated, and (b) is reported |
| Reversed, mirrored | Reversed: cosine of fitted to truth direction below -0.5. Mirrored: fitted vertex closer to `-x_true` than `x_true`, for `r/R_s` at least 0.4 |
| Topology hypotheses | H1: one source, 7 parameters. H2: two sources, 14 parameters. H2 is chosen if and only if `2(lnL_2 - lnL_1) >= 30`. The 30 is a penalty, so more parameters and a higher raw likelihood are not enough. Design choice, not tuned on any recipe sample. H1 is H2 at zero second-source yield, so Wilks does not apply under H1 truth: the tail is measured, job 7474462 [R8] |
| Mis-ID | H1 truth: H2 chosen, in each main bin. H2 truth: H1 chosen, in the two-source control |
| `D_bar`, expected difference | Charge-only `lnL` difference on expected data, truth H2 against the best H1 fit, 8 starts. A reported design figure only. No rule reads it: charge alone gives 0.5-2 at the corner, median 44 (job 7474461), while the statistic also uses time [S1] |
| Fixed likelihood points | 50 parameter points drawn from block 6, frozen with the generator |
| DEFF, bootstrap, seeds, development size | Sections 5.2, 5.1, 3.2 |
| Weighted data | None. All fixtures are unweighted |

### 7.1 T08 clustering definition

The recipe and the reference clusterer both follow this text [R3]. They share no code. Every constant is in section 4.2.

| Step | Rule |
| --- | --- |
| Cells | Read value `e_c`, computed by the recipe from the readout's raw value, gain and pedestal. Cell `ix` has centre `x_c = ix + 0.5`, in the frame of truth x, y. Dead or absent cells have no value and are never in a cluster |
| Components | Cells with `e_c >= T_c`, 8-connected. A component is kept if it has a cell at or above `T_s`. All others are unclustered |
| Peaks | In a kept component: a cell at or above `T_s`, with `e_c` at least that of all 8 neighbours. Candidates in ascending flat index `ix x 40 + iy`; a candidate adjacent to one already kept is dropped [M1]. Keep the two highest. The fixture has at most two showers, so no more are used |
| One peak, or none kept | One object: `A = sum e_c` over the component. `x = sum e_c x_c / A`, likewise `y` |
| Two peaks | Two objects, by 30 iterations of sharing, no early stop. Start: `c_k` = centre of peak cell k, `A_k` = that cell's value. Each iteration: `f_kc = A_k g_c(c_k) / sum_j A_j g_c(c_j)`, then `A_k = sum_c f_kc e_c`, `c_k = sum_c f_kc e_c x_c / A_k`. `g_c` is the cell-integrated profile of width `W`. All sums over the component |
| Sharing fractions | `f_kc` from the last iteration, kept per object. 1 for one-peak objects |
| Uncertainty, one peak | `sigma_A^2 = sum_c v_c` over the component, with `v_c = q max(e_c, 0) + sigma_n^2`. `sigma_x^2 = sum_c (x_c - x)^2 V_c / A^2`, likewise y, over the component and its 8-connected ring, absent and dead cells left out. `V_c` is the variance of `e 1(e >= T_c)`, for `e` Gaussian with mean `mu_c = A g_c(x, y)`, at the estimate, and variance `s_c^2 = q mu_c + sigma_n^2`: with `a = (T_c - mu_c)/s_c`, `V_c = M_2 - M_1^2`, `M_1 = mu_c Q(a) + s_c phi(a)`, `M_2 = (mu_c^2 + s_c^2) Q(a) + s_c (mu_c + T_c) phi(a)`, `Q` the upper normal tail and `phi` the standard normal density. The term carries cells near `T_c` entering and leaving the sum, which a sum over kept cells alone omits: pull width 1.07 at 0.25 GeV without it, 1.01 with it (job 7478897) |
| Uncertainty, two peaks | Fisher matrix on the component's cells, `theta = (A_1, A_2, x_1, y_1, x_2, y_2)`, `I_ij = sum_c (d mu_c/d theta_i)(d mu_c/d theta_j)/v_c`, `mu_c = sum_k A_k g_c(c_k)`, `v_c = q mu_c + sigma_n^2`, evaluated at the estimate. `sigma_j^2 = (I^-1)_jj`. This is needed: at `d` = 3, `sigma_A` is 1.17 `sqrt(q E)`, closed form, so the plain sum would fail the width gate. A singular `I`, or a non-positive or non-finite variance, leaves that shower with no primary: it counts against shower efficiency and enters no pull [S11] |
| Event sum | Sum of `A` over all objects = sum of `e_c` over all kept components. `sigma^2 = q S + n sigma_n^2`, `S` the event sum, `n` its cells |
| Which sum enters | iso, edge, dead, near: the event sum. A split in iso or dead cannot move energy, and a hole at a dead cell may give two peaks. far: per-shower primary object. Position in iso: the largest object |

**One-peak position uncertainty: what has been shown.** Job 7478897 tested it on new iso showers, 0.25 to 16 GeV, all objects one-peak. Job 7479146 used it on job 7474461's events. That log prints position pulls for iso and far only. Its near nodes print total energy, and its edge, dead and saturation nodes print energy. So the uncertainty has not been shown for near, edge, dead or saturation objects, or with absent or dead cells in the ring. No gate reads those positions (section 9). The log does not separate one-peak from two-peak objects in far. Only the one-peak form changed, so a changed far line shows one-peak objects there. In gated bins, `s68` moved at `d` 8 up to 4 GeV and at `d` 6 at 0.25 GeV. At `d` 3 at every energy and at `d` 3.25 at 0.25 GeV, only mean and rms moved (`d` 3, 0.25 GeV: rms 2.56, 2.45 to 3.56, 3.27).

Interpolation of tables: linear in ln E and in `d`, on the nodes in the job log. No extrapolation: every gated value lies inside the nodes.

**Matching sensitivity [22].** Repeated at 70 % for tracks and clusters. 50 % stays primary. A change of more than 0.005 in any gated rate, or more than 0.02 in any centre or width, is recorded. It blocks nothing, except the sentence "not sensitive to the matching threshold". The threshold never changes (11.3.1).

## 8. T07 tracking and vertexing

### 8.1 Recipes [12]

| Gate family | Recipe | Quality kind |
| --- | --- | --- |
| Efficiency, fakes, duplicates, charge sign | `reco.track.acts-ckf-planar/1`, all stages | Full chain |
| Track pulls, `q/p` per charge, angle | Same, primaries | Matched-conditional, reported with efficiency |
| Refit pulls | `reco.track.acts-kf-refit/1`, known hit set | Truth-assisted, counted apart, never reported as finding |
| Vertex finding, assignment | `reco.vertex.acts-amvf/1` on the CKF tracks | Full chain |
| Vertex pulls | Same, primaries | Matched-conditional, reported with finding |

### 8.2 Gates

| Gate | Rule | Tests per bin |
| --- | --- | --- |
| Track pulls | Location, width, tail, 5 parameters, both fixtures | 15 |
| `q/p` per charge | Same, each sign, both fixtures. A charge-dependent bias of plus or minus 0.40 cancels in the mixed sample and passed the width gate 66 % (earlier rule, `t04_v3.out`) | 6 |
| Vertex pulls | Same, 3 parameters, both fixtures | 9 |
| Refit pulls | Track pulls plus `q/p` per charge, clean only. On the noise fixture the known hit set has the same distribution, so it adds nothing. See section 16 | 21 |
| Angle | 5 track parameters x 3 in 4 pooled slices per fixture. This closes the sign-odd hole [14] for the sign of the slope only | 60 per fixture, not per bin |
| Efficiency, clean | Lower bound at least `R - delta` = 0.99 | 1 |
| Efficiency, noise (a) | Paired against the truth-seeded run of the same recipe (section 7): lower bound of the difference at least -0.01 | 1 |
| Efficiency, noise (b) | Floor: lower bound at least `R_floor(o) - 0.01` = 0.9894, 0.9881, 0.9837 [10] | 1 |
| Fakes, clean | Rate test, `L` = 1 % | 1 |
| Fakes, noise | Section 8.3 | 2 |
| Duplicates | Rate test, `L` = 1 %, both fixtures. v3's noise ceiling does not apply: noise adds no particle to duplicate, and ambiguity resolution is under test | 1 |
| Charge sign | Rate test, `L` = 1 %, all bins | 1 |
| Vertex finding | Section 8.5 | 1 |
| Vertex assignment | Rate test, `L` = 1 %, far events | 1 |

Per-bin rate count: 6 clean, 8 noise. Earlier rule, simulated at reference 0.98: a paired true loss of 0.01 passes 6.1 %, 0.015 passes 0 of 2,000, 0.005 passes all (`t04_v3.out`).

### 8.3 Noise-fixture fake limit [3]

**Why not a plain number, and why not the recipe's own rate.** v3's "development rate plus 0.01" tests stability, not fakes: a true 30 % gets a 31 % ceiling and passes 65 %. A plain 1 % has no link to the fixture, which is the second review's objection: it is a floor-like target that a correct recipe might not meet if noise itself makes fakes. So the limit is derived from the fixture, then capped.

**Fixture-derived rate.** `f_ref(o)` is the chance rate with no recipe under test. Closed-form estimate, for a candidate needing 6 hits: about 1e-7 per reconstructed track at o3, by the script's own formula `2 p_w^2 x 0.13 x 14 x 1.6 / 36`, and less at the others [M2]. For comparison, a 4-hit requirement gives about 0.03 candidates per event at o3 per triple. So at these noise levels a correct recipe with the fixture's reconstructable definition has almost no chance fakes, and the objection does not bite. `calc-fake-reference.py`, job 7474462: upper bounds 7.7e-12, 3.6e-10 and 1.0e-7 per reconstructed track at the three levels. Chance 6-hit candidates are too rare to count, and it searches 4 of 56 plane triples, so its result is an extrapolation from a 4-hit count: a 95 % upper bound, scaled by `2 p_w^2 x 14 x 1.6` [M4].

| Item | Value |
| --- | --- |
| Absolute cap `C(o)` | `max(0.005, 5 f_ref(o))`, fixed at Freeze A, at most 0.01. Rule in section 18 |
| Value at Freeze A | 0.005 at all three levels (job 7474462) |
| Stability tolerance `tau` | 0.0025, fixed at Freeze A |
| Recipe | CKF at the Freeze-B hash |
| `r_dev` | Per bin, from the Freeze-B run, 12,000 events per bin. Duplicates do not share it |

Two tests per noise bin. Both must pass.

| Test | Rule |
| --- | --- |
| F1, absolute | Rate test, `L = C(o)`, on the evaluation sample |
| F2, stability | `(r_eval - r_dev) + sqrt((U_eval - r_eval)^2 + (r_dev - L_dev)^2) <= tau`, with `U_eval` and `L_dev` the 95 % bounds of section 5.2 on each sample. This counts the development uncertainty and stays defined at zero counts |

If `U_dev` exceeds `C` at the Freeze-B run, evaluation does not start: the recipe has failed in development and the method must change.

Closed form:

- A true 30 % fails F1 with certainty. A true rate equal to `C` passes F1 about 5 % of the time.
- F1 rate slack, `L` = 0.5 %: 0.198 % at worst correlation, 0.356 % at `n_eff` 72,000.
- F2 false failure per test, equal samples, 12,000 effective: 3.8e-6 at `r` = 0.1 %, 0.36 % at 0.2 %, 2.9 % at 0.3 %. At 72,000 effective: 1.6e-19 at 0.2 %, 2.4e-9 at 0.4 %.
- So the family target for F2 needs `r` at most 0.106 % under full correlation. A correct recipe is expected far below this, but that is a claim about the recipe. It goes in Known limits.

`N_min` for `L` = 0.5 % is 6,000 events, met by 12,000.

### 8.4 Reported, not gated

Split and merged vertices; near vertices; predicted and filtered states; unbiased residuals; pulls by sign of local position; failure classes (seed or finding, fit, ambiguity, truncation); search-truncated candidates.

### 8.5 Vertex finding

No analytic reference exists [10]. Rule: efficiency over reconstructable vertices, far events, lower bound at least 0.95. Accepted by the user (section 16), a design requirement. Reason: at 5 `u_v` or more, with 3 or more tracks, the fixture makes finding nearly unambiguous, but no formula gives a value. It carries none of the "fixture-known" meaning of a reference. A correct finder below it fails, and section 2.3 applies.

Seeding [R14]. The installed headers describe a seeder that models tracks by d0/z0 and finds a z seed, and a default split check on z distance. So the fixture separates vertices along that axis and keeps them near one line. Read from headers, not run: `seedFinder` is a configuration choice, frozen at Freeze B.

AMVF uses adaptive weights, so Gaussian vertex pulls are not guaranteed by anything in this design. Development will show it. If they fall outside the conditions, section 2.3 applies.

## 9. T08 and T09 gates

### 9.1 T08

Recipe: `reco.calo.cell-cluster/1`, following section 7.1.

| Gate | Rule | Stratum |
| --- | --- | --- |
| Energy pulls | Location, width, tail, target section 4.2 | iso, far, E2-E4 |
| Position pulls | Same, x and y, truth shower axis | iso, far, E2-E4 |
| Total energy | Same, event sum, target `2E - b_near` | near, E2-E4 |
| Efficiency | Against the closed-form reference, margin `delta` | iso, far, E1-E4 |
| Merge | Rate test, `L` = 1 %, event as object | far, E2-E4 |
| Conservation | Clustered plus unclustered energy equals the input, within 1e-9 relative. Fractions sum to 1 for clustered cells, 0 for unclustered. Deterministic | All |

Per-shower pulls in near bins are reported, not gated. Below 2.08 `W` the two-shower sum is unimodal (39 % of the stratum), so a correct recipe merges many, and a matched object then holds two showers' energy: the per-shower pull has no closure meaning. The near total-energy gate tests thresholds and membership only; **sharing in near is untested** [R15]. A recipe that never splits passes it. Evidence for overlap comes from far, where the crossing fraction at `d` = 3 is 6.7 %. The obligation stays open.

Merge in E1 is reported, not gated: at E1 a seed may not fire (`p` 0.84 at the lower edge), so about 1.5 % of events lose a seed, above `L`: a gated merge would fail correct code. That loss is an efficiency loss, already gated. Efficiency bounds merge only to a rate of about 2 % [S13].

### 9.2 T08 sheet and prereg items [13]

| Item | Treatment |
| --- | --- |
| Low thresholds | E1: efficiency gated against the closed-form reference, whose bin mean is 0.992 (0.84 at the lower edge, 0.77 at a cell corner). Energy pulls ungated in E1 by the rule in section 3.3, obligation open |
| Same selection as the response | The targets carry the same thresholds as the recipe, through `b` |
| Saturation | Control. Deterministic: every object with a clipped cell carries a flag, and its energy is marked a lower bound. Zero exceptions required. Energy reported, obligation open. A truth-side target exists, as for dead cells: `sum_c min(E g_c(x, y), 400 MeV) - b_sat`, with uncertainty over unclipped cells. It is not gated in this version: choice, not impossibility [S6]. A recipe that flags correctly but drops or wraps clipped cells passes. Section 16 |
| Edges | Control, 3 tests, event sum, target `E Phi(t) - b_edge(t)`. Position reported: a truncated centroid is biased by design |
| Dead cells | Control, 3 tests, event sum, target conditioned on truth `x, y`. Position reported. Deterministic: a dead cell is never in a cluster |
| Containment | Covered by the edge control. In main it is 1 by construction |
| Linearity | Covered by the centre gate per energy bin: a slope in scale moves some bin's centre. No separate test |
| Angle, particle type | Not varied: this fixture has one layer and an analytic profile. Not tested. Obligation open |
| Split | Reported. No closure reference exists: its correct value depends on the fixture's splitting definition |
| Negative cases | Digital read as analog: typed refusal or recorded error. The fixture has no digital readout, so the test builds its own digital-typed input. Deposited energy used as incident: the named-energy check rejects it. Deterministic |

### 9.3 T09

Recipe: `reco.light.channel-likelihood/1`.

| Gate | Rule | Bins |
| --- | --- | --- |
| Parameter pulls | Location, width, tail, 7 parameters | B2-B4 |
| Fit failure | Rate test, `L` = 1 %, all generated events | All 12 |
| Wrong minimum | Rate test, `L` = 0.5 %. Consistent with the tail gate: 38 of 10,000 independent | All 12; clause (b) only where pulls are gated |
| Mis-ID, H1 truth | Rate test, `L` = 1 % | All 12 |
| Likelihood check | Coded likelihood agrees with an independently written evaluation, within 1e-9. Deterministic. Sum-to-1 alone could pass by construction | Fixed points, section 7 |
| Per-channel sum | Hit and no-hit probabilities sum to 1. Deterministic. A failure is the sheet's stop | All channels at fixed points |

### 9.4 T09 sheet and prereg items [13]

| Item | Treatment |
| --- | --- |
| Few photons | B1, required by the sheet and plan. Gated on fit failure, wrong minimum clause (a) and mis-ID, none of which needs Gaussian pulls. Pulls ungated in B1, because no result shows a correct fit has unit pulls there. Obligation open for pulls |
| Live-unhit against dead | Dead control: 21 pull tests with dead channels masked. Negative check [R7]: the same 12,000 events, same fit, dead read as unhit. It fires if at least one of x, y, z, `t0` gives `|centre| - 1.645 se > 0.10`, at 95 %. Screen at n = 500, job 7474461: 0.120 at 100 channels, 0.486 at 200, so the patch is 200 by section 18's rule. Masked control at 200 clears, job 7477126 |
| Saturation | Saturation control: 21 pull tests with censoring |
| Mirrored, reversed | 2 rate tests, `L` = 0.5 %, pooled over B2-B4, from the main sample |
| Two simultaneous events | Two-source control: H2-truth mis-ID, `L` = 1 %, 1 test, all events of the control. See below |
| First-time under a single-photon density | Negative check [R7]: main B4 events, `r/R_s` [0.4, 0.7), 12,000 events, refit with a single-photon density in place of first-arrival. It fires if the `t0` centre gives `|centre| - 1.645 se > 0.10`, at 95 %. Sensitivity, closed form: at about 1 photon per channel the first arrival is early by 0.28 of the time spread, 0.41 ns, about 7 times `sigma(t0)`. Required, outside the budget. A check that does not fire is `failed` |
| Position | Radial bins |
| Medium | One medium. Not tested. Obligation open |

**Two-source region [R9, S1].** The region is a truth function: the control's whole stratum, separation at least 0.4 `R_s`, both yields B3. The miss rate is tested directly, with time, at the stratum's corner: separation 0.4 `R_s`, 200 + 200 photons, parallel directions along and across, 600 events (`calc-t09-null-h2.py`). H2 is started at truth there, a scoring-side study, so its count is a lower limit on the miss rate. 0 of 600 below the penalty gives a 95 % bound of 0.50 %, under the slack of 0.535 %. Otherwise section 18 raises the separation's lower edge. At v3's 10 and a penalty of 30, the Wilks-type miss rate would be 65 %. The test stays required, for all events of the stratum.

## 10. From test results to R11 state

**Fail** is defined in section 5.2: a pull or rate test whose bound lies wholly outside its limit, or that has enough precision and no bound inside the limit.

**Required** means: a test in a gated bin. Gated bins are fixed at Freeze A. A required bin cannot lose its status at any Freeze B or later [R1].

**Ungated** means: outside a valid range, or listed as "Reported" here. An ungated bin's check value is `inconclusive`, with `required: no`, the reason, and the obligation open [4]. It is never `not-applicable`, because that would hide unfinished coverage (Section 1.3 item 6, R11), and it never counts as pass. `not-applicable` is used only for a combination that cannot exist: for example merge rate in an iso bin.

| Test or check result | Gate result | Workflow | R11 state |
| --- | --- | --- | --- |
| All tests pass in all required bins; deterministic, negative and CAI checks pass; required set intact | pass | pass, with open obligations listed | `done`, reported as `done (narrowed claim)` whenever an obligation is open [R18] |
| Any test fail in a required bin | fail | fail | `failed`, record in `failures/<T-ID>.md` |
| Any test inconclusive in a required bin | inconclusive | fail: a required check was inconclusive (R11) | `failed` |
| Deterministic or negative check does not pass | fail | fail | `failed`. A sheet Stop condition stops the task |
| Ungated bin | `inconclusive`, `required: no` | No effect on the result. The claim narrows. The obligation stays open in every report | No effect |
| Required set not intact | No gate result | fail | `failed` |
| `CAI-` check fails (R37) | fail | fail | `failed`. A recorded unsupported gap (R37) does not block `done` and stays open |
| Configuration holds a forbidden constant (section 2.2) | Void for that parameter, read as fail | fail | `failed` |
| Freeze-B blocks used up | No gate result | Not judged | `blocked-by-decision` |
| Critical false success observed (prereg) | Named capability blocked | fail for that capability, whatever the tests say | `failed` |
| Required output missing, so the test cannot be computed | inconclusive | fail | `failed`. Missing implementation is never `not-applicable` |
| Resources shrink a sample (K10) | Affected tests inconclusive | fail | `failed`; if evaluation cannot run at all, `blocked-by-resource` |
| Failed, method changed and recorded | New attempt, section 3.4 | Per that attempt | Back to `in-progress`, attempt count kept |
| Matching sensitivity disagrees | No effect | No effect | No effect. Recorded |

A workflow's result is the worst of its gates. A mean over bins cannot make up for a failed bin (11.3.2).

**Required set.** Fixed at Freeze A [4]. Nothing can leave it [R2].

| Workflow | Required, cannot be ungated | Tests | Ungated at Freeze A |
| --- | --- | --- | --- |
| T07 | All tests | 1,260 | Nothing |
| T08 | E2-E4 pulls in iso, far (54); near total energy E2-E4 (9); efficiency (8); merge E2-E4 (3); controls (6) | 80 | E1 pulls: 21 tests |
| T09 | B2-B4 pulls (189); all rates in 12 bins (36); controls (45) | 270 | B1 pulls: 63 tests |

**Open obligations [R18].** Recorded in a new table `obligations` in coverage.md, one row each, with the owner below, and listed in every report. 11.3.2: narrowed claim, obligation unfinished.

| Obligation | Owner |
| --- | --- |
| T07 material; T08 angle and particle type; T09 medium | No owner: the user's decision at Freeze A against plan 11.4 (section 16) |
| T07 particle type, timing, displaced vertices, near vertices | T07 later pass (sheet: material comes after the first pass), or the user |
| T07 A01 | T15b, if `simreco` qualifies on the shared domain (sheet) |
| T08 E1 pulls, E1 merge, near per-shower pulls and near sharing, saturated energy, split rate, unequal sharing, noise-dominated regime | No owner, user's decision |
| T09 B1 pulls | No owner, user's decision |

## 11. Deterministic and negative checks

Required checks with no statistics. They are outside the budget. A pass here means "the check fired on this case", no more.

| Workflow | Check |
| --- | --- |
| T07 | Wrong hits; branch explosion; seed failure. Limits reached are marked search-truncated. Each recorded in its failure class. Scenarios A01, A05, A07, A17, A39. Refit never reported as finding |
| T08 | Section 9.1, 9.2. Scenarios A15, A32, A38. Double counting of a cell is the sheet's stop |
| T09 | Section 9.3, 9.4. No data-side truth (A09) |

## 12. K12: performance

**No targets yet.** With no recorded cost, a target would be a guess. T07-T09 record cost per stage, cold and warm. Targets are drafted from those records after P2.

## 13. K16: selection, for T15b [15]

K16 does not use the T07 gates. `simreco` has no vertexing, runs on `element_sim` events, and returns one candidate per particle with inverse rigidity, its uncertainty, `n_hits`, `n_fake_hits` and `charge_flip` (read from `simreco.cc` at this base). So only tracking gates can apply, on this domain.

| Item | Proposal |
| --- | --- |
| Candidates | `simreco-pr-a`: code defaults, window 1 mm, `chi2_per_ndof_cut` 50, minimum 4 hits. `simreco-pr-b`: window 0.5 mm, otherwise the same |
| Event sample | One shared `element_sim` sample, spec frozen by hash before T15b. Open: no spec is named yet. 4 true rigidity bins at the generator's equal-population quartiles, a function of truth, 12,000 events per bin per charge. No development results enter. The spec must keep `rho_sigma/|rho|` at most 0.1 at the top bin's upper edge, from truth, or that bin is ungated with the obligation open |
| Comparator | The same `simreco` with pattern recognition off, on the same events. A comparator only |
| Hard gates, per bin, per candidate | `rho_pull` location, width, tail, mixed and per charge: 9 tests. Efficiency (`fit_ok` and selected, over particles with at least 4 true planes), paired against the comparator, lower bound at least -0.01. `charge_flip`: `L` = 1 %. Fake: tracks with `n_fake_hits` more than half of `n_hits`, `L` = 1 % |
| Not applicable | Duplicates: one candidate per particle by construction. Vertex gates: no vertexing. Track parameters other than rigidity: not in the output |
| Budget | 4 x 12 x 2 = 96 tests. `alpha` 1.04e-4, `z1` 3.71, slack 0.049 at `se` 0.0095, closed form |
| Result rules | Sections 5.2 and 10 |
| Objective | Lowest total CPU time per event subject to the gates, failed events and I/O included |
| CPU measurement | Process user plus system time, both candidates in one job on one node, chunks of 100 events in alternating order, first chunk of each discarded as cold and reported apart. If per-event timing is not available, the chunk is the unit |
| Comparison | Paired events, one population and denominator |
| Tie rule | If the two-sided 95 % bootstrap interval of the mean paired cost difference, resampling events or chunks, includes 0, keep `simreco-pr-a`, called a "qualified default choice" |
| None passes | "No qualified candidate"; gates are not lowered |

## 14. K10 budgets

Wall time, memory and retries become Slurm requests, set at each job's approval. Algorithmic budgets are frozen at Freeze B (section 2.2). Reaching one is recorded. `CAI-` tolerances are set from fixture statistics and recorded before each run (R37).

## 15. Sample sizes and recomputed numbers

Evaluation, per attempt, closed form. Cost is unknown until a recipe has run.

| Workflow | Events | Objects |
| --- | --- | --- |
| T07 | 288,000 (24 bins x 12,000) | 5.18 million truth tracks; 12,000 x 4 x (2 + 2 + 3) x 2 = 672,000 vertices |
| T08 | 180,000 (12 bins + 3 controls) | 276,000 showers |
| T09 | 180,000 (12 bins + 3 controls) | 192,000 sources |

| Quantity | v3 | v4 | Label |
| --- | --- | --- | --- |
| T07 tests | 864 | 1,260 | Closed form |
| T08 tests | 132 | 101 | Closed form |
| T09 tests | 288 | 333 | Closed form |
| Per-test `alpha` | 1.16e-5 (Sidak) | 7.94e-6 (union) | Closed form |
| `z` | 4.38 two-sided | 4.316 one-sided | Closed form |
| `sigma_68` constant | 0.953 | 0.962 | Closed form |
| Cap, centre and width | 0.0129, 0.0119 | 0.0108 both | Closed form |
| Slack at cap | 0.0223 | 0.0356 | Closed form |
| Slack at `n` = 10,000 | 0.0379, 0.0426 | 0.0386, 0.0427 | Closed form |
| T09 range | 200 (mean) | 120 (trimmed) | Seven-parameter check, job 7477126 |
| Wrong-minimum clause | "5 sigma" | Any of 7 parameters, 4.0e-6 | Closed form |
| Topology gate region | `D_bar` 10 | Separation at least 0.4 `R_s`, miss rate tested directly | Corner: 0 of 600, job 7474462 |
| T08 noise, cell threshold | Not stated | 0.2, 0.6 MeV (round 1: 1, 3) | Design choice; closed form shows why |
| T07 vertex separation | Transverse, `u_v` 0.043 | Along v, `u_v` 0.0184, on a line | Design choice; closed form |
| T07 ideal wrong assignment at o3 | Not stated (round 1: 0.02 %) | 0.027 % | Closed form |
| Freeze-B run, T08, T09 | Not stated | 45,000 each | Closed form |
| Rate minimum | None | 3,000 and 6,000 events | Design choice |
| Clustered rate pass at limit | 4.2-5.7 % | At most 7.0 %, job 7474461 | Earlier rule for the old number |
| Charge-bias 66 % | 66 % | Unchanged | Earlier rule; unaffected, not rerun |
| Paired efficiency 6.1 % | 6.1 % | Unchanged | Earlier rule; unaffected, not rerun |

`t04_v2_a.py` has no saved output, and r2.py was never among the cited hashes. Their numbers are not cited here [20].

## 16. Choices for the user

Each is genuinely the maintainer's. The rest of this document assumes the recommendation. All were accepted by the user on 2026-11-06, with the vertex finding floor at 0.95 (decisions.md, "T04 section 16"). The `element_sim` spec was not named. "Proposal" and "recommendation" in sections 5.1, 13 and 16 now mean those accepted values.

| Choice | Recommendation | What changes otherwise |
| --- | --- | --- |
| **Tolerance and size** | 0.10 with 10,000 retained objects, 12,000 events per bin | See table below |
| **Evaluation attempts** | Cap 2, second at 99 %. A method change is expected at least once on new code. False pass at most 5.95 % | Cap 1: 5 %, and any failure ends T07-T09 at `failed` until an amendment. Cap 3 at 95 %, 99 %, 99.9 %: at most 6.1 %, slack lower still |
| **Absolute fake cap** | `max(0.005, 5 f_ref)`, at most 0.01, `tau` 0.0025 | 0.0025: `N_min` becomes 12,000 events, exactly the sample, and slack halves. 0.01: true fakes up to 1 % pass, and F1 gets looser than the clean limit's meaning |
| **Required set** | Section 10: T07 all; T08 80 tests; T09 270 tests | Fewer required tests narrow the claim. Set before results only |
| **Method limit in E2 or B2** | Accept: all ranges fixed at Freeze A, E2 and B2 required. A method limit there fails the workflow until the user amends Freeze A (section 2.3). This is the only route with no new review | Alternative: freeze complete reference estimators by hash at Freeze A, with positions and uncertainties, before any development run. A range then moves if and only if the recipe and the reference show the same departure in at least two of the bin's three strata. Maximum one bin. This needs a further review, and does not exclude a defect shared by both codings |
| **Material, particle type, medium** | Accept as open obligations for the first pass, the user's decision at Freeze A against plan 11.4 | Otherwise the fixtures must vary them, a new version of the design. Without this decision a task reaches `done` with those dimensions never judged |
| **T08 saturated energy** | Keep reported, for the simpler design | Gate 3 tests with `b_sat`, which `calc-t08-reference.py` prints. M does not change, since all T07-T09 gates use T07's count |
| **T08 noise regime** | Accept as an open obligation | One reported iso sample at `sigma_n` 1, `T_c` 3. It would show behaviour, not gate it |
| **Refit** | Gated, clean fixture only: 252 tests, M = 1,260 | Reported only, with a reason: M = 1,008, `z1` 4.267, slack at cap 0.0362, and the sheet's "counted separately" rests on reporting. Gated on both fixtures: M = 1,512, `z1` 4.356, slack at cap 0.0352, for no new information |
| **Vertex finding floor** | 0.95 | No reference exists, so this is a value judgment. A higher floor risks failing a correct finder, a lower one tests little |
| **K16 hard gates and sample** | Section 13. Name the `element_sim` spec | R02: these are the user's. Without them, no claim beyond the declared baseline |

Tolerance alternatives. "Size" is retained objects per bin. Generated events are 1.2 times that. M = 1,260, closed form. Slack at the design `se`, location then width.

| Tolerance | Size | Generated events per bin | Slack, location | Slack, width |
| --- | --- | --- | --- | --- |
| 0.05 | 15,000 | 18,000 | -0.0001 | 0.0032 |
| 0.05 | 30,000 | 36,000 | 0.0146 | 0.0169 |
| 0.075 | 15,000 | 18,000 | 0.0249 | 0.0282 |
| 0.075 | 30,000 | 36,000 | 0.0396 | 0.0419 |
| **0.10** | **10,000** | **12,000** | **0.0386** | **0.0427** |
| 0.10 | 30,000 | 36,000 | 0.0646 | 0.0669 |

If 0.075 with 30,000: tolerance 0.075, cap 0.0067, which keeps slack 0.035 (`n` at least 23,600). Events: T07 864,000, T08 540,000, T09 540,000 per attempt, three times the proposal. The T07 sample could stay at 12,000 events only if pulls prove nearly independent, and that cannot be promised before a run. A 0.075 bin finds an error of 0.075 at 95 %. The cost is unknown until a recipe has run, so the recommendation is 0.10 now. Changing later is an amendment (section 2.3).

## 17. Known limits

- Family target: holds only under section 5.4. For true errors above the slack, failure is the intended outcome.
- The family target's tiny per-test rate is a Gaussian extrapolation. Nothing has measured it. `calc-rate-rule.py` at 1,000 reps bounds a failure rate at 0.3 % only.
- Rates: the `alpha` slack is computed at known DEFF. With DEFF estimated, the pass rate at the limit reached 7.0 % at most in 132 scenarios (job 7474461), above the nominal 5 % and under the rule's 7.1 %.
- Gates apply where the task is easy [18]. Charge sign is gated where `sigma(q/p)/|q/p|` is at most 0.1, so a Gaussian wrong sign is a 10-sigma event: the gate catches gross errors only. Assignment at 5 `u_v`, merge at 3 `W` and mis-ID at separation 0.4 `R_s` follow the same pattern. Where confusion really happens, results are reported only.
- Skewed pulls can pass or fail for reasons other than bias.
- Sign-odd bias inside a bin cancels, except by charge and by slope sign. Position sign is reported only.
- F2 can fail a correct recipe with a fake rate above 0.1 % under strong correlation (section 8.3).
- T07 has no material, one species and no timing. Vertices lie near one line, separated along the seeder's axis only. Vertex-finding at 0.95 is untested for this seeder: nothing has run.
- T08 noise is 0.2 MeV, chosen so the pull model closes. Noise is at most 2.2 % of the variance in gated bins, so an omitted or wrong `sigma_n` passes every gate. Threshold handling is sensed only in E2, to about 1 MeV of `b`. Round 1's noise-dominated regime is not tested [S5].
- T08 saturated energy is reported by choice: a truth-side target exists (section 16).
- T08 E1 merge is reported: only efficiency bounds it, to a merge rate of about 2 % [S13].
- T08 far position has an inward centroid bias, section 5.4. The expected image, coarse, puts it at most of the slack in E2 [S3]. Job 7479146 gives far E2 width 1.007-1.010, at most 0.0097 of the slack of 0.0356.
- T08 one-peak position uncertainty: shown for iso and far only, section 7.1.
- H1-truth tail: 600 events per `N_exp` cannot show a tail under the slack. 3 of 600 clears the rule with a 95 % bound of 1.29 %, and a true 1 % clears it 15 % of the time. Only false failure follows, not false pass. The tail is also a lower limit through search [M6].
- T08 far showers have equal energies, so unequal sharing is untested. Sharing in near is untested. Saturated energy has no target. Targets depend on an independent coding of the same clustering definition, by the same author, so a defect in the definition is shared and a defect repeated in both codings is possible.
- T09's valid range rests on `calc-t09-range.py`, n = 4,800 per `N_exp`, `se` about 0.015. Its reference fit is simplified: integer charge, no threshold, no saturation. At 120 the `E_vis` centre is -0.044 and the `N_exp` centre -0.042: inside the rule's 0.0601 (section 18.1, row T09 range), but not clearly inside the slack of 0.0356 that section 5.4 assumes, and B2's lower edge sits there. The bin's mean over [120, 200) should be smaller; that is not measured. If a correct fit departs in B2 by more than the gate allows, T09 fails (section 16).
- Near the +z axis the masked control, with 200 dead channels, had one reversed fit in 500 and a largest pull of 9.45 (job 7477126). No rule reads it at that size; the 12,000-event control will.
- Vertex pulls at worst-case correlation sit exactly at the cap with retention 0.95. There, B = 1,000 jitter of 2.2 % gives about even odds of inconclusive, which is `failed`. Expected correlation is far lower [M8].
- Adaptive vertex weights may give pull widths away from 1 for a correct fit.
- No fixture number has been run through a recipe. Retentions in section 4.4 are assumptions.

## 18. Scripts and decision rules

All in `<private>/evidence/t04-v4/`. All have now run; results in section 18.1. All were **required** for Freeze A [R6]. numpy and scipy only, fixed seeds. Every script writes results to stdout as they appear, flushed, so a crash keeps earlier output, and sets one BLAS thread per worker. Each runs on 6 CPUs, one after another in its job; a script's failure does not stop the next. The table's runtimes are the recheck's estimates with assumed unit costs, kept as history. Measured, from the receipts: job A 874 s, job B 1,062 s.

| Job | Script | SHA-256 prefix | Estimate | Claim |
| --- | --- | --- | --- | --- |
| A | `calc-t08-reference.py` | `8bf8939e378aabd3` | 15 min | `b` constants and tables; efficiency; far merge; pulls; `b_sat` |
| A | `calc-t09-lowmu.py` | `2cebdd8a71b89b2f` | 12-19 min, patch rerun included | Range 80, gross check; rates; dead sensitivity |
| A | `calc-pull-table.py` | `5c3c7dd3de32df59` | 6 min | One-bin table with the frozen rule |
| A | `calc-rate-rule.py` | `a70704dcd6aa6df6` | 2-3 min | Rate rule at varying objects per event |
| B | `calc-t09-null-h2.py` | `c09b80082d9d7576` | 19-31 min: null 17-20, corner 2 per separation, up to 5 | H1-truth tail; two-source miss rate |
| B | `calc-fake-reference.py` | `5790d57b71d528e7` | 6-11 min | `f_ref(o)` |

| Job | Upper estimate | Slurm limit | Ratio |
| --- | --- | --- | --- |
| A | 43 min | 1 h 50 min | 2.6 |
| B | 42 min | 1 h 50 min | 2.6 |

**Decision rules [R6, S1-S3].** Fixed now. An outcome not listed leaves v4 unchanged. No rule may be chosen after seeing output. **"Stop" means: return to the user, and no number moves until the user answers.** An agent does not choose what follows. Where a rule needs a rerun, the script does it and logs it, except where stated. Bin values are those printed on `BIN` lines: node values weighted as the fixture draws them (trapezoid in ln E, and in `d` or uniformly over `t`), `se` from the total events, per gated bin and stratum. Limits there are printed beside each value. A value within 1e-4 of a limit is recomputed from its node values before it is read, because the prints have 4 decimals. This rule was fixed in the dispositions before job 7479146, and written here after it.

| Script | Result | Forced action, before Freeze A |
| --- | --- | --- |
| Fake | `f_ref(o)` bound at most 1e-3 | `C` = 0.005 |
| Fake | Above 1e-3, at most 2e-3 | `C = max(0.005, 5 f_ref)` |
| Fake | Above 2e-3 | Halve that level's noise mean, rerun. At most twice, then stop |
| T08 | `fired` differs from closed form by more than `3 se + 3/n` at any node (`dev` against `limit`) | Stop |
| T08 | `|b - b_iso|` above 0.02 sigma + 3 `se` at an iso node in E2-E4 (`CONST worst node`) | Replace the constant by the node table in ln E |
| T08 | iso, edge, dead, near, per `BIN` line: energy `|s68 - 1|` above 0.0246 + 3 `se`, tail above 0.535 % + 3 `se`, position centre above 0.0246 + 3 `se`, position `|s68 - 1|` above 0.0356 + 3 `se` | Stop. The model in section 7.1 may miss a term |
| T08 | far, the same limits, on `BIN far ... from d` lines | Raise far's lower edge to the lowest `d` node such that the bin values computed from `d` upward meet them, at most 5. None: stop |
| T08 | Far merge, E2-E4, above 0.535 % + 3 `se` on those lines | Same raise, same exit |
| T08 | Far efficiency, bin value, below the closed-form bin mean by more than 0.005 + 3 `se` | Stop |
| T08 | Largest iso `split` in E2-E4 above 0.5 % + 3 `se` | Stop: section 7.1's peak rule makes spurious peaks |
| T09 | At `N_exp` 80 or 120, pooled (n = 1,200): any parameter with `|centre|` above 0.085, or `|sigma_68 - 1|` above 0.082. Or, in any radial bin (n = 400): `|centre|` above 0.120 or `|sigma_68 - 1|` above 0.115 | Raise the range and the B1/B2 edge to the first tested `N_exp` that clears, at most 200. Not clear at 200: stop |
| T09 | Fit failure or wrong minimum at `N_exp` 80 or more, above 0.5 `L` + 3 `se` | Stop |
| T09 | Dead read as unhit: no centre among x, y, z, `t0` with `|centre|` at least 0.14 at n = 500. This is a screen, not firing power, which at 12,000 events needs 0.1155: a true 0.10 reads 0.14 with 19 % chance. The script doubles the patch to 200 channels once | Patch 200 clears: `PATCH` becomes 200 in the fixture. Neither clears: the negative check becomes `required: no`, with obligation open |
| H2 | Tail above the penalty, above 0.5 %, at `N_exp` 50 or 1,000 | The script takes the first of 30, 35, 40 that clears both, and uses it. None: stop |
| H2 | Two-source corner, 600 events: any event below the penalty | The script raises the separation's lower edge by 0.1 `R_s`, reruns, at most 0.8. Still short: stop |
| Rate | Pass at `L` above 7.1 % in any scenario | The script reruns it at 4,000 reps with a new seed. Above 6 % there: stop, the DEFF estimate is the suspect |
| Rate | Pass at slack below 99.7 % | The script reruns at `slack x 0.8`, repeating until met. Write that value in the `r_slack` table |
| Pull | m = 1 jobs only: pass at true error 0.10 above 7.9 % | Revise section 5.5 and the 93-95 % of section 1 to the measured value |
| Pull | `POOLED` line, six m = 1 jobs at states `none` and `bias`, 3,000 reps, relative `se` 1.3 %: differs by over 9 %, centre or width | Stop. No number moves until the cause is known |
| Pull | Any fail at state `none` | Stop |
| Generator check, row 1 | A hash check stops the job, the job stops with no `RESULT` line, or a traceback or `ran to its end` line appears | No criterion of that run is read. Remove the cause; if code changes, new hash. New approval either way |
| Generator check, row 2 | Any `FAIL` on a T08 or T09 `|z|` line (limit 5), a `defined` line, a `DRAW-RANGE`, `SMOKE` or `TRUTH` line (`TRUTH` deposit limit 6: 72,000 values), or a `DRAW-DIST` line with non-finite values | Defect in the generator or the check: fix, new hash, new approval. Block 6 is reused, since the fix is not a redraw |
| Generator check, row 3 | Nothing in rows 1 and 2, and a sum of `z^2` outside its range, or a `DRAW-DIST` p-value below 1e-4 | Stop. A correct generator reaches this row with about 3.7 % chance, and block 6 cannot be redrawn. No generator changes until the user answers |
| Generator check, row 4 | Nothing in rows 1 to 3, and stderr not empty | Goes to the user, whatever the lines say |
| Generator check, row 5 | `RESULT PASS`, stderr empty, job exit 0 | Hashes and `GOLDEN` digests go into Freeze A |

For the generator check, the first matching row applies.

`calc-t08-reference.py`'s frozen log is round 5's: job 7479146, `round5/calc-t08-reference.py` (`5f096622f3bbe1b3`). The prefix in the table above is round 3's, run in job A. Round 5 changes section 7.1's uncertainty and the form in `p_closed`, exact up to 250 MeV and Gaussian above, where both give 1 to six places, with the same seeds. The T08 rows stay as fixed, and round 5 was read against them.

The T09 range row is as fixed before job A, at n = 1,200 and 400. Job 7477126 ran at n = 4,800 and 1,600, with the limits in section 18.1, row T09 range. A reader must not apply this row's limits to that job.

A script result that moves a required test to reported goes in the scope-change table for the maintainer.

### 18.1 Results

Jobs 7474461 and 7474462 ran the scripts above. They gave three stops. Two were seen at once, and the user's decisions of 2026-11-06 answered them, using diagnostic job 7477066 and round 4 job 7477126. The full read before Freeze A found the third. Jobs 7478606, 7478897 and 7479146 resolved it. Job 7477787 is the generator check. This section states what binds. t04-v4-dispositions.md keeps the full tables and the rules as fixed before each job, as a record. Evidence: `<private>/evidence/t04-v4/`, folders `job-diag-7477066/`, `job-round4-7477126/`, `job-generators-7477787/`, `job-diag-t08b-7478606/`, `job-diag-t08c-7478897/`, `job-round5-7479146/`.

| Item | Result | Action taken |
| --- | --- | --- |
| T08 `fired` at 80 MeV, first stop | Stop. Job 7474461: 0.83670 against 0.84327, `dev` 0.00657, limit 0.00640. Cause: the Gaussian cell response. Job 7477066: 300,000 events give 0.84086, exact 0.84020, Gaussian 0.84327 | Exact form in section 4.2, by the user's decision. Job 7477126: all six nodes up to 250 MeV within limits against it. Job 7479146: all 30 iso nodes within |
| T08 quoted values | `R(E1)` 0.9924, `p` 0.8402 at 80 MeV, 0.7671 at a cell corner, far E1 node mean 0.96006 | Rounded values in sections 4.2 and 9.2 unchanged: 0.992, 0.84, 0.77 |
| T09 `theta`, `phi`, second stop | Stop, not clear at 200. Cause, from job 7477066: `calc-t09-lowmu.py` departed from section 7: it gated angles, not tangent components, left `theta` out of range in 23 % of fits, used `N_exp` for `E_vis` and did not draw isotropic directions | `calc-t09-range.py` follows sections 4.3 and 7, by the user's decision, on new events (job 7477126) |
| T09 range | Rule, fixed before job 7477126: 80 clear on the pooled and all three radial rows keeps 80; 80 not clear and 120 clear on the same four rows sets 120; neither clear is a stop. Limits keep section 18's form, 0.0356 + 1.645 `se`, `se` 1.03 and 0.962 over `sqrt(n)`, at the new n: centre 0.0601 and width 0.0584 pooled (n = 4,800), 0.0780 and 0.0752 radial (n = 1,600). Section 18's row is as fixed before job A. Job 7477126: 80 over on `E_vis` centre, -0.062 pooled, -0.111 at `r/R_s` from 0.4. 120 clear on all four rows | Range and B1/B2 edge 120 |
| T09 fit failure, wrong minimum | Limits at n = 4,800, section 18's `0.5 L + 3 se`: fit failure 0.00805, wrong minimum, clause (a) or (b), 0.00466. Job 7477126: all 0 at `N_exp` 80 and 120 | No action |
| T09 dead | Screen 0.486 at 200 channels. Masked control clear at n = 500, limits as in row T09 range at that n, 0.1114 and 0.1064, an excess going to the user; clauses (a) and (b) 1 of 500, under 0.0092 (job 7477126) | `PATCH` 200 |
| T08 iso E2 position width, third stop | Stop. Job 7474461 `BIN iso E2` y printed 0.0412, limit 0.0412. From node values: 0.041206 against 0.041154, over by 5.2e-5. It was first recorded as none over, from 4-decimal prints. Job 7478606, 540,000 new showers, limit 0.039527, x and y: `raw` 0.040374, 0.039683, so the excess is reproduced; `cross`, the measured sub-cell shift removed, 0.040737, 0.039370, so a fixed shift is not the cause; `oracle`, a threshold-free centroid, 0.024994, 0.025769. `cross` split across the limit, so the job's reading table did not apply and the outcome went to the user. Cause, as tested: section 7.1's one-peak sum over kept cells left out cells near `T_c` entering and leaving the sum | The user asked for the cause, then adopted the tested form (decisions.md, "T08 width stop"). Section 7.1 replaced. Job 7478897, new showers: `BIN E2` 0.008351, 0.009338, limit 0.039527; all 30 `NODE` lines within 0.0474. Job 7479146 reran the T08 reference with it and the exact efficiency, on job 7474461's events. Every energy, `b` and `CONST` line is unchanged. No section 18 row fires. Iso E2 position 0.0078, 0.0080, before 0.0410, 0.0412. Far E2 from `d` 3: 0.0069, 0.0097, before 0.0130, 0.0156. This log replaces job 7474461's T08 log |
| T08 other rows, job 7479146 | Constant: worst node E 2378.4, 0.0128 sigma, limit 0.0374. `BIN` limits, iso, edge, dead, near, far: 154 values, none over, none within 1e-4. Position tails print with no limit, at most 0.00309; position values exist on iso and far lines only. Largest ratio to its limit: 0.53, far E2 energy tail; 0.39, iso E2 energy width; 0.25, far E2 y position width. Far merge: 21 values, largest 0.00012, limit 0.00574. Far efficiency: 22 values, largest deficit 0.00006, limit 0.00526. Iso `split` in E2-E4: 0.00000 | No action. One `b_iso`, far's lower edge stays 3 |
| Generator check, job 7477787 | `RESULT PASS`, stderr empty, exit 0. No `FAIL` line | Row 5: hashes and 61 `GOLDEN` lines go into Freeze A |
| H2, Rate, Pull, Fake | No rule triggered. The Pull row quotes section 1's former 93-95 %. Section 1 now reads at least 95 %, as section 5.5 does | Penalty 30, `C` 0.005 |
