# T10 timing lane: stage plan (R35, CAI-T10-1, CAI-T10-2)

Finish-plan Task E1 step 2, the part of T10 that does not wait for U7 (`t10-options.md` section 4). The scan or global replay
(U7, option B2) is the other T10 lane and is not planned here. Read for this plan: plan v9.2 R34, R35, R37 (T10 item), §16.1 row
T10, BP07, BP15, A37; `t10-options.md`; `decisions.md` (U7 answer, U12 A, K02); `contract-map.md` (W6, W7); `t11-cells.md` (F12);
`t05-task-sheets.md` (T10 row); `calibration-alignment-interfaces.md` (R34, R35 rows, `calo-gain-payload/1`); the T07 product reader
`adapters/acts-tracking/assets/fixture_tools/acts_native_product.py` and `native/native_product.hpp`. Anything not taken from these is
marked **derived here** or **fixture choice**.

Everything below is fixed before the code is written (R37: "All tolerances are fixed and recorded before the test runs"). Synthetic
fixtures only; no timing, TOF or PID quality claim; no K09 threshold is used or needed (R37: T10's checks are deterministic interface
tests).

## 1. Where the code goes

A new development binding, `adapters/timing-pid`, recipe `reco.timing.time-chain/1`, Python on env/py313, laid out as
`adapters/calo-cluster` and `adapters/photon-likelihood`: the recipe in `assets/timing_recipe/`, the scoring-side check in
`assets/fixture_tools/t10_cai.py` (the recipe never imports it), tests in `tests/adapters/`. Status `proposed` until a job runs it.
Not a native backend; as for T08 and T09 (U12 A), the native timing backend is a gap to record when T10 closes.

Formats introduced (names are proposals of this stage):

- `timing-channel-map/1`: the text `timing-channel-map/1\ncounters N\nends E\nchannel = counter * E + end, counter in [0, N), end in
  [0, E)\n`; its identity is the SHA-256 of that text. E is 1 (single-ended) or 2 (two-ended).
- `timing-payload/1`: one conditions payload per chain step, the shape of `calo-gain-payload/1` (sorted-key JSON, identity the SHA-256 of
  its bytes, `origin`, `producer`, `derived_against`, `derived_from`, `round`), with `step` one of `offset`, `walk`, `propagation`,
  the channel map identity, one value per channel and the step's unit (`ns`, `ns`, `cm/ns`). `derive()` writes a payload with some
  channels changed, its own identity and its source; a derived payload is never nominal (R32).
- The hit record (`timing-hit-record/1`), the event-time record (`timing-event-time/1`) and the TOF record (`timing-tof/1`) are Python
  dicts that serialise to JSON, as listed in rows R35-1 to R35-5.

## 2. Conventions, stated before the run

- **Time chain** (fixture choice of form; order from R35): for a channel c and a hit of raw time `t_raw` [ns] and amplitude `A`
  [arbitrary amplitude unit, a.u.],
  1. offset: `t_1 = t_raw - o_c` (payload `offset`, `o_c` in ns);
  2. walk: `t_2 = t_1 - a_c / sqrt(A)` (payload `walk`, `a_c` in ns·sqrt(a.u.)); the walk depends on amplitude only;
  3. propagation: single-ended, `t_3 = t_2 - d / v_c` with `d` [cm] the distance from the hit position to the read-out end, the
     position taken from the track and recorded with source `track`; two-ended, see below.
  The `1/sqrt(A)` form is a fixture choice for an amplitude-dependent walk (F12: "leading edge plus walk curve"); no physical shape
  is claimed.
- **Offset sign:** raising channel c's offset by Δ lowers every offset-corrected time of c by Δ (R37's "−Δ"). `Δt_k` is then the
  change of the fully corrected time of hit k; for a single-ended hit it is `−Δ`, because walk and propagation do not depend on time.
- **Two-ended counter (derived here, not from a source):** a counter of length `L` along x in [−L/2, +L/2], end 0 at −L/2, end 1 at
  +L/2, effective speed v. A hit at x and time `t_0` gives, after offset and walk per end, `t_e0 = t_0 + (L/2 + x)/v` and `t_e1 =
  t_0 + (L/2 − x)/v`. Hence `t_0 = (t_e0 + t_e1)/2 − L/(2v)` (the propagation-corrected time) and `x = v (t_e0 − t_e1)/2`. Raising
  end 0's offset by Δ: `t_e0` changes by −Δ, so the mean `(t_e0 + t_e1)/2` and `t_0` change by −Δ/2 and x by −vΔ/2 (the hit appears
  nearer end 0); raising end 1's offset by Δ: mean and `t_0` by −Δ/2, x by +vΔ/2. Hence `Δt_k = −Δ/2` for that hit. Both ends' times
  and x are kept (R35). `t10-options.md` section 4.2 gave the same sizes "sign by the convention"; this is the convention.
- **TOF and β:** per hit h of track j, `TOF_h = t_h − T_0`, `β_h = L_h / (c TOF_h)`, `L_h` [cm] the track's path length to that timing
  hit (supplied by the fixture, recorded), `c = 29.9792458 cm/ns`. A track may have several timing hits (several planes) and a channel
  may hold several hits (of different tracks) in one event (fix round 1, I1 and M7).
- **Event times** (R35 records source, estimator, hit identifiers and weights):
  - external: `T_0` supplied (source `external`), no hit used;
  - internal, common, linear: each hit gives `T_0,i = t_i − L_i/(c β_hyp)` (β_hyp the fixture's species hypothesis, recorded),
    `T_0 = Σ_i w_i T_0,i` with fixed recorded weights, `Σ w_i = 1` (checked to 1e-12, else refused);
  - internal, per-track leave-one-out, linear: for track j, every hit of track j is excluded (fix round 1, I1: the exclusion is keyed
    by `track_id`, and the record names the excluded track and its excluded hit IDs): `T_0^(−j) = Σ_{i∉j} w_i^(−j) T_0,i`, with
    `w_i^(−j) = w_i / Σ_{l∉j} w_l` recorded; no hit of the track has a weight; a TOF is formed against it only for a hit of track j;
  - internal, median of the `T_0,i` (non-linear): change recorded, no assertion (R37).
- **General form of the expectations (fix round 1, M7; it reduces to R37's statements for one affected hit).** Let K be the hits on
  the changed channel and `Δt_k` their changes. Common linear: `ΔT_0 = Σ_{k∈K} w_k Δt_k` and `ΔTOF_h = Δt_h − ΔT_0` with `Δt_h = 0`
  for h ∉ K. Leave-one-out for track j: `ΔT_0^(−j) = Σ_{k∈K, k∉j} w_k^(−j) Δt_k` and `ΔTOF_h = Δt_h − ΔT_0^(−j)` for each hit h of
  track j. External: `ΔTOF_h = Δt_h`. With one affected hit k this is R37's `w_kΔt_k`, `−w_kΔt_k`, `(1 − w_k)Δt_k`, `−w_k^(−j)Δt_k`
  and `Δt_k`.
- **TOF record (fix round 1, M8):** it names its event time: the value, the hit IDs used, the excluded track and hits, and the
  SHA-256 of the event-time record's canonical JSON, so a TOF against a stale event time is distinguishable from a good one.

## 3. Tolerances and steps (fixed now)

Fixture times are within |t| < 200 ns, positions within |x| < 100 cm, path lengths 50 to 500 cm, v 10 to 20 cm/ns. Double precision:
the unit roundoff is 1.1e-16, so a time near 200 ns carries about 3e-14 ns per rounding; each checked change has at most about ten
roundings.

| Quantity | Tolerance | Reason |
| --- | --- | --- |
| A time change (corrected time, event time, TOF) against its expectation | 1e-12 ns absolute | about 30 times the worst rounding above |
| "Changes by 0" (other channels' hits; other tracks under an external event time) | exactly 0.0 | the arithmetic of those values is unchanged |
| Position change x (two-ended) | 1e-10 cm absolute | v ≤ 20 cm/ns times 1e-12 ns, with a margin of 5 |
| β of the affected track against `L/(c (TOF_old + Δt_k))` | 1e-12 relative | one division and one sum |
| Linear step halving: `q(h) = change(h)/h` at h = Δ and Δ/2 | `|q(Δ) − q(Δ/2)| ≤ 4 tol / Δ` (time 4e-11, position 4e-9 cm/ns) | two changes each within tol, divided by Δ/2 |
| β step halving: error `e(h) = |(β(h) − β_0)/h − dβ/dh|` of the forward difference, `dβ/dh = β_0/TOF_0` for `TOF = TOF_0 − h` | `0.45 ≤ e(Δ/2)/e(Δ) ≤ 0.55` and `e(Δ) > 0` | first-order difference: the ratio is `(TOF_0 − Δ)/(2 TOF_0 − Δ)`, within 0.006 of 0.5 for TOF_0 ≥ 5 ns, Δ = 0.1 ns (fix round 1, M5: 0.49495 at 5 ns) |

Finite step recorded: Δ = 0.1 ns, halved to 0.05 ns. Both are offsets of one channel at a time.

## 4. Obligations

Stage 1 is this stage. Stages 2 to 4 follow `t10-options.md` section 4's order (1 and 2 together, then 5, then 4, then 3); PID is
stage 5, after them (fix round 1, I2).

| ID | Source | Acceptance | Negative case | Prerequisite | Stage |
| --- | --- | --- | --- | --- | --- |
| R35-1 | R35, R34 | each hit records, per step in chain order (offset 1, walk 2, propagation 3), the value before and after, the value the step applied, and that step's payload identity; each step's before equals the previous step's after | a record whose steps are out of order, repeated or missing, whose before does not equal the previous after, whose applied value does not follow from the step's parameter (offset `o_c`, walk `a_c/sqrt(A)`, propagation `d/v`), whose position source is not `track` for a single-ended hit, or (given the payloads) whose payload identity or parameter is not the payload's for that channel, is refused by the reader (fix round 1, M3) | `timing-payload/1` (this stage) | 1 |
| R35-2 | R35 | each hit keeps its amplitude | a hit without a finite positive amplitude is refused (never walk-corrected with an invented one) | none | 1 |
| R35-3 | R35 | a two-ended hit keeps both ends' times (raw and per step) and its position; a single-ended hit keeps its position along the counter with source `track` | a two-ended hit with one end missing is refused, never zero-filled; a single-ended hit with no track position is refused | none | 1 |
| R35-4 | R35 | each hit keeps the path length of its track to the timing hit | no path length: refused | fixture-supplied path (cross-system path is R35-X below) | 1 |
| R35-5 | R35 | each event time records source, estimator, the hit identifiers and their weights; a leave-one-out time records the excluded track and every excluded hit, none of which has a weight | weights that do not sum to 1, a negative weight, a leave-one-out time that uses a hit of its own track (two hits on one track: both excluded), or an internal time with no hit: refused | none | 1 |
| R35-6 | R35 | dE/dx keeps per-measurement samples and path lengths before truncation and normalization | a truncated value without its samples | a dE/dx fixture | 2 |
| CAI-T10-1a | R37 T10 | single-ended counters only; changing one channel's offset by Δ changes that channel's offset-corrected times by −Δ (1e-12 ns) and every other hit's by exactly 0; the offset step is applied once and first; `Δt_k = −Δ` | controls that must FAIL the check: the offset applied twice (−2Δ); the sign flipped (+Δ); recipe-side, the recipe's offset step applying it twice; also a channel holding two hits of different tracks, each moving by −Δ (M7) | R35-1 | 1 |
| CAI-T10-1b | R37 T10 | external event time: only the affected track's TOF (by `Δt_k`, 1e-12 ns) and β (1e-12 relative) change; every other TOF and β exactly unchanged | control: an event time that silently uses the hits instead of the external value FAILs | R35-5 | 1 |
| CAI-T10-1c | R37 T10 | common linear event time: changes by `w_k Δt_k`; every other track's TOF by `−w_k Δt_k`; the affected track's by `(1 − w_k) Δt_k` | control: the TOF taken against the event time from before the change (stale) FAILs | R35-5 | 1 |
| CAI-T10-1d | R37 T10 | per-track leave-one-out: track j ≠ k changes by `−w_k^(−j) Δt_k`; track k by `Δt_k` | control: a leave-one-out that keeps the own hit (the common time used per track) FAILs, on the check side and recipe-side; a track with two hits has both excluded (I1) | R35-5 | 1 |
| CAI-T10-1e | R37 T10 | median event time: the change of `T_0` and each TOF recorded, with no numeric assertion | none (a record) | R35-5 | 1 |
| CAI-T10-1f | R37 (deterministic checks) | the step Δ and its half are recorded; every linear expectation holds at both and the step-halving bound of section 3 holds; β's forward difference passes the ratio window | none beyond 1a-1d | section 3 | 1 |
| CAI-T10-2 | R37 T10, derived here (section 2) | two-ended counter: raising one end's offset by Δ moves the mean time and `t_0` by −Δ/2 and x by ∓vΔ/2 (end 0: −, end 1: +); other counters exactly 0; under an external event time the affected track's TOF changes by −Δ/2; step halving as section 3 | controls that must FAIL item CAI-T10-2: the position change without the 1/2 (check side and recipe-side); the mean taken as one end's time | R35-3 | 1 |
| A37-T10 | A37, §9.6, §0.5.8 | artificial g×E degeneracy and the T07 weak-mode fixture (7004 vs 7003) reused, with the method card naming the unconstrained mode and its external constraint | a convergence or same-type holdout cited as absolute calibration | T07 fixtures (closed out) | 2 |
| W6-T10 | §3.3, W6, BP12, R20 (A19-A24) | a native non-hit (counts with thresholds and exposure) example through a recipe: a valid zero, an absent interval, per-channel valid exposure | absent filled with zero; run time as both denominators | T06 `count_witness` | 2 (moved from 3 by the stage 2 scope) |
| R35-X / BP15 | §16.1 T10, BP07, BP15 | TOF/β with path and momentum from the T07 ACTS recipe and times from this chain, with a shared-clock nuisance and partial delivery (a missing subsystem by a validated missing-input method, never zeros) | missing clock alignment read as zero offset | **Open.** Checked in the records for this plan: the T07 product keeps per track state `path_length_mm` (ACTS `pathLength()`, `kalman_refit.cpp`; read by `acts_native_product.py`) on the eight telescope planes, and `q/p` among the parameters. There is no timing plane in the T07 geometry, and the origin of `pathLength()` (from which point it counts) is not stated in the records read. So a flight path to a timing plane is not available; a difference between two telescope planes is formable but its use as a flight path is undecided. `t10-options.md` concern 5 stands | 4 |
| PID-T10 | §16.1 T10 "Timing/PID", BP07 | BP07's deliverables: β (this stage), and charge or species likelihoods or classification scores with their support domains, from TOF with a supplied path and momentum (a TOF hypothesis residual `t_meas − t_pred(p, m, L)`, F12), with the final working point and the species or charge priors kept. BP07's diagnostics, each a case: shared-clock shifts (a common offset of all channels moves an external-time TOF, cancels in an internal one); wrong bunch or wrong path; few samples; saturation; overlapping species and migration; `P(selected as B | true A)` reported apart from `P(true A | selected as B)`, the latter with its population composition stated | a score or LLR labelled a probability; the two conditional probabilities exchanged; a common-clock term averaged away; a missing subsystem filled with zeros instead of a validated missing-input method | stage 1's TOF and β; momentum and path from the fixture (from T07 only through R35-X) | 2 (moved from 5 by the stage 2 scope; fix round 1, I2) |
| W7 subcases | §16.1 T10 "W7 subcases", W7, R14 | the global subcase (`y_i = s + b`) at run time is the other lane's replay (U7 B2, destriping with its stated constraint); the RF and retarding subcases stay W7 contract checks (T06), recorded in that lane as not run at run time (`t10-options.md`, option B "does not prove") | a W7 contract pass read as a native backend run (W7, §12.1) | U7 answer (B2) | other lane (fix round 1, I2) |
| R14 replay | R14, U7 | the other T10 lane (U7 B2) | | | other lane |

## 5. Stage 1 deliverables

1. Tests first, kept red with logs: `tests/adapters/test_timing_chain.py` (R35-1 to R35-5, payload reading) and
   `tests/adapters/test_timing_cai.py` (CAI-T10-1a to f, CAI-T10-2, every expectation computed in the test from section 2, not by the
   recipe; the controls by planted defects that must make the check FAIL).
2. The recipe (`timing_recipe`: payload, time chain, event time and TOF) and the check (`t10_cai.py`, exit codes of `core/status.py`).
3. A stage job, drafted and not submitted, that runs both test modules and `t10_cai.py` on a seeded synthetic fixture from a checked
   copy (the snapshot rule of `jobs/d4-e6c/e6c.sh`), with predictions fixed in the lane report.
4. `calibration-alignment-interfaces.md`, R35 row: from Designed to written in stage 1 (login unit tests only; tested after the job).

## 6. Stage 2 (branch `t10/stage2` from `4c08da43`; written before its tests and code)

Scope given by the coordinator (2026-11-13): the carried re-review item R1; R35's dE/dx part (row R35-6); the PID rows (PID-T10);
A37 for T10 (row A37-T10); the W6 native non-hit example (row W6-T10) if its prerequisites are met. Rows R35-6, A37-T10, W6-T10 and
PID-T10 move to stage 2. The cross-system example (R35-X) stays **open**: no record read for this stage settles a flight-path length
to a timing plane (searched: `docs/dev/detector-reconstruction/`, `adapters/acts-tracking/`; only this plan, `t10-options.md`,
`t11-cells.md` and `coverage.md` mention one). Synthetic data only; no PID, dE/dx, calibration or counting quality claim.
Sources read for this stage: plan v9.2 R35, R37, §9.6, BP07, A19-A24, A37; `skills/hep-detector/references/particle-identification.md`
(common principle, TOF, dE/dx, combining many samples, combining measurements, deliverables) and `calibration-and-alignment.md`
(alignment and weak modes, calibration standards, outer loops); the T07 record `calibration-alignment-interfaces.md` rows
`CAI-T07-4`; `tests/contracts/reconstruction_fixtures.py` `count_witness` and `contracts/reconstruction.py` counts checks.

### 6.1 Conventions (fixed now; marked where they are fixture choices)

- **R1 (re-review of stage 1).** Every hit entry of an event-time record carries its `track_id`. A leave-one-out record lists no
  hit of its excluded track (checked by `track_id`, not only against `excluded_hits`), and `tof()` refuses a leave-one-out start
  that lists the record's own hit or whose `excluded_hits` does not contain it (re-review R2). A common or median start lists the
  hit's own hit by definition (R37's `(1 − w_k)Δt_k`) and stays allowed.
- **dE/dx (R35; particle-identification.md "Ionization energy loss").** Each sample keeps its identifier, layer, deposit [MeV],
  path length [cm] and saturation flag; per sample `dE/dx_i = deposit_i / path_i`. Truncation (fixture rule): sort ascending by
  `dE/dx_i` (ties by sample identifier), drop the highest `floor(f·n)` samples (the reference: "discard the highest-loss fraction"),
  keep the rest, at least one; the truncated mean is the mean of the kept values. Normalization divides by a stated reference value
  with its source (a fixture constant; the reference names MIP calibration on the most probable value). The record keeps every
  sample, the kept and dropped identifiers, `f`, `n`, the truncated mean and the normalized value, and a reader recomputes all of it
  from the samples. Flags (fixture thresholds): `few-samples` when `n < 4`; `saturated-in-kept` when a kept sample is saturated (its
  deposit is a lower bound, so the mean is biased low); a saturated sample is never silently treated as a value.
- **TOF species hypotheses (particle-identification.md "The common principle", "Time of flight").** For a hypothesis of mass `m`
  and a supplied momentum `p` (fixture value with its source and that source's unconstrained modes, see A37):
  `β_h = p / sqrt(p² + m²)`, `t_pred = L / (c β_h)`, residual `r = TOF − t_pred`, a Gaussian time likelihood with a stated
  `σ_t` (fixture choice): `ln L_h = −r²/(2σ_t²) − ln(σ_t sqrt(2π))`. LLR between two hypotheses is `ln L_a − ln L_b`, recorded as
  "log-likelihood ratio, not a probability" (the reference: "A likelihood ratio becomes a probability only with a prior"). A
  probability is written only with stated priors (summing to 1): `P(h) = π_h L_h / Σ π L`. Support: for each hypothesis pair the
  separation `|t_pred,a − t_pred,b| / σ_t` and whether it reaches `k = 3` (fixture choice); a pair below it is outside support (the
  momentum ceiling). Working point (kept in the record): select B over A when `ln L_B − ln L_A ≥ x`, with `x` stated.
- **Migration and composition.** From a labelled synthetic population: `P(selected as B | true A) = n(A→B) / n(A)` per true species;
  `P(true A | selected as B) = P(sel B | A) π_A / Σ_A' P(sel B | A') π_A'`, with the composition `π` stated. The two are separate
  fields and never exchanged (BP07).
- **Missing input.** A track without a TOF gives a PID record with status `missing-input` and no likelihood numbers (null), never
  zeros (BP07: "A missing subsystem permits only a validated missing-input method, not zeros").
- **Diagnostics, derived here from stage 1's chain (not from a source):** raising every channel's offset by `δ` (a shared clock)
  changes every corrected time by `−δ`; under an external event time every TOF changes by `−δ`; under a common or leave-one-out
  linear internal time the event time also changes by `−δ` (weights sum to 1), so every TOF changes by 0. A wrong bunch (the
  external time late by the bunch spacing `b`, fixture `b = 2 ns`) changes every TOF and residual by `−b`. A wrong path `L(1+ε)`
  scales every `t_pred` by `(1+ε)` and changes each residual by `−ε t_pred` (the TOF is unchanged).
- **A37 and §9.6, g×E (artificial, §9.6's own example).** Amplitudes `A_ce = g_c E_e` (channel gain times event energy, the
  amplitude stage 1's walk step uses). In logarithms the design has one exact null vector (+1 on every `ln g`, −1 on every `ln E`),
  so `(a g, E/a)` gives the same amplitudes for every `a > 0`. The check shows: the exact (rational) rank is `C + E − 1`; two gauges
  give identical amplitudes; a least-squares fit converges to zero residual in both gauges and a same-type holdout (other events'
  amplitudes) fits both equally, so neither convergence nor the holdout fixes the scale (A37); the identifiable combinations
  (`g_c / g_c'`, `g_c E_e`) are equal in both gauges; one named external constraint (a reference event of known energy, the
  reference's "an absolute scale still needs a reference") makes the rank full and the scale unique. In stage 1's chain the walk
  coefficient is defined against the amplitude scale in use (`a_c / sqrt(A)` with `A → λA` equals `(a_c / sqrt(λ)) / sqrt(A)`): the
  same gauge, recorded on the method card.
- **A37, the weak-mode witness reused.** T07's record of `CAI-T07-4` (job 7546791, `cai-refit.log`, SHA-256 `0f60e9ac…16a90`) is
  read, not rerun: in each of its 8 cells the change in `q/p` is at least `k = 4.5` per-track σ while the change in mean χ²/ndf is
  within 4.5 of its standard error (R37's self-check, T07's threshold). The PID record carries the momentum source's unconstrained
  mode, because a curvature offset biases `p` and so every `t_pred` and mass hypothesis.
- **Method card** (`timing-method-card/1`, an asset): for each unconstrained mode its name, its witness, the named external
  information that constrains it, the independent observables that can confirm it, and the constraints used in the derivation, which
  are never independent observables (§9.6; CAI-T06-3 carries the contract part). Modes on the card: the amplitude scale (g×E), the
  common time offset under an internal event time (constrained by an external start time), and the momentum source's curvature
  offset (constrained by information beyond the track residuals: a resonance of known mass, E/p of electrons and positrons, cosmic
  or halo tracks, independent subdetectors, field reversal; and a vertex or beam constraint, which R37 names as constraining the
  T07 mode). A placeholder convergence or unconstrained-mode check (T12's loop fixture) never satisfies A37 here.
- **W6 native non-hit (prerequisites met: T06 `reconstruction:counts-v1` and its checks exist).** Native input: per channel, a
  threshold selection, readout intervals each read or not read with start, end and dead time [s], and pulse amplitudes and times.
  The recipe counts pulses at or above the channel's threshold in each read interval (a zero is a count), marks an unread interval
  `absent` with no count, sets each channel's valid exposure to the sum over its read intervals of (end − start − dead time), the run
  time to the span of all intervals, and each rate's denominator to the channel's own valid exposure; it delivers no per-event
  energy (A19). The product must pass `contracts.reconstruction.read_sidecar`. Rate readings `Σ counts / valid exposure` are
  recorded beside the product. A20 to A24 other than A19 are not covered by this class (no coded image, Compton, acoustic, prompt-
  delayed or energy-resolving sensor): recorded gaps.

### 6.2 Tolerances (fixed now)

| Quantity | Tolerance |
| --- | --- |
| dE/dx truncated mean and normalized value against the test's own computation | 1e-12 relative; the reader recomputes with the same formula, exact |
| `t_pred`, residuals, TOF changes in the diagnostics | 1e-12 ns absolute |
| `ln L`, LLR | 1e-12 absolute |
| posterior sum | within 1e-12 of 1 |
| migration fractions and composition-weighted purity | exact integer counts; fractions within 1e-15 |
| g×E: amplitudes under two gauges; holdout residuals; identifiable combinations | 1e-12 relative; rank exact (rational arithmetic) |
| fitted residual "converged" | sum of squared log residuals ≤ 1e-20 |
| W6 counts, exposures | exact |

### 6.3 Stage 2 obligations

| ID | Acceptance | Negative case (each a control that must FAIL or a refusal) |
| --- | --- | --- |
| R1 | hit entries carry `track_id`; a forged leave-one-out record listing a hit of its own track is refused; `tof()` refuses a leave-one-out start listing its own hit or not excluding it | the re-review's forged record |
| R35-6 | every sample, path, flag, the kept and dropped sets, `f`, the truncated mean and the normalized value retained and recomputable | a truncated value without its samples; a mean that does not follow from them; a missing or non-positive path |
| PID-T10a | hypothesis likelihoods, LLR labelled not a probability, support per pair, working point kept, probability only with priors | `llr-as-probability` |
| PID-T10b | diagnostics: shared clock (external −δ, internal 0), wrong bunch, wrong path, few samples, saturation | `clock-not-cancelled` (internal time not recomputed) |
| PID-T10c | `P(sel B | true A)` and `P(true A | sel B)` kept apart, the latter with its composition; overlapping species flagged outside support | `purity-as-efficiency` |
| PID-T10d | missing input: status `missing-input`, no numbers | `zero-filled-missing` |
| A37-T10 | g×E: rank `C+E−1`, gauge invariance, convergence and holdout equal in both gauges, identifiable combinations equal, the named constraint fixes the scale; weak-mode witness from T07's record in all 8 cells; method card complete, no constraint used as validation | `holdout-as-proof`, `no-constraint`, `validation-is-constraint`, `placeholder-witness` |
| W6-T10 | product passes `read_sidecar`; zero kept, absent without count, per-channel valid exposure denominators, no per-event energy | `absent-as-zero`, `run-time-denominator` (the contract codes) |

The stage job (`jobs/t10-stage2/`) runs the timing modules, the stage 1 check tool as a regression, the stage 2 tool on seeded
synthetic data and on T07's pinned log, every control, and the full suite, judged as `jobs/t12-stage1/t12-stage1.sh` judges it.

### 6.4 Stage 2 fix round 1 (review `jobs/t10-stage2/REVIEW.md`, 0/5/9/4; fixed before its tests and code)

- **I1.** `event_time.check(record, event)` and `event_time.tof(record, start, event)` take the event's hit records. For an internal
  start the event is required: every listed hit and its `track_id` must be the event's, `excluded_hits` must equal all hits of
  `excluded_track`, the listed hits must be all the event's hits (common, median) or all but the excluded track's (leave-one-out), and
  `estimates_ns` and `value_ns` are recomputed exactly from the event (same formulas as the recipe). A stale start (computed on other
  times) is therefore refused. The review's forgery (hit 11 relabelled as track 3, `excluded_hits` [10], weights 1/3, value edited) is a
  test. The scoring tools count a refused start as a failure of the item that used it.
- **I2.** `t10_a37.py` pins T07's record itself: SHA-256 `0f60e9ac0ebe9114c0ba1f64369926027b7b130d9c43884ddcd458bf73316a90`, job
  7546791; any other text fails on the witness's `source` sub-item, and `--expected-sha256`, if given, must repeat the pin (else
  rejected, exit 2). The `placeholder-witness` control feeds a real placeholder text (eight valid-looking cell lines that are not T07's
  record). M9: the record must also show its own outcome (`test_cai_t07_4_self_check` followed by `ok`, and `OK` at the end).
- **I3.** Method card `timing-method-card/2`: every item of `constraining_information` (ids `constraint.*`) and of
  `independent_observables` (ids `observable.*`) has an identifier and a text; the two id sets are disjoint per mode, so information used
  to constrain a mode is never offered as its validation (§9.6); `constraints_used` lists ids of that mode's constraints and may not name
  an observable. The curvature-offset mode keeps the vertex or beam constraint, cosmic or halo tracks and field reversal as constraints,
  and a resonance mass versus charge, direction and momentum, electron and positron E/p and independent subdetectors as observables.
- **I4.** The job requires, for every control, the tool's RESULT line with exactly its failed items, and exactly 10 stage 1 and 11 stage 2
  `PASS control` lines. Stage 1's exact failed sets, fixed now from its rules (`t10_cai.py`, section 3): offset-twice, offset-sign and
  recipe-offset-twice fail 1a and 1f (β's forward-difference derivative presumes Δt_k = −Δ); external-uses-hits fails 1b and 1f; the
  others only their own item. **Corrected after its first run:** recipe-offset-twice fails 1a, 1b, 1c, 1d and 1f, because the reader
  refuses its records, so 1b to 1d are not formed from them and report FAIL with no checks (the stage 1 re-review's R3); the
  prediction above for it was wrong. `t10_cai.py`'s RESULT line gains its failed-items field (`items ...`).
- **I5.** Red is rerun on the final test files against stubs in a scratch copy, with hashes.
- **Minors and nits.** M2: a chain-level gauge test (amplitudes ×λ with walk coefficients ×√λ give identical corrected times). M3: a
  claim of identification by holdout or convergence is judged and refused (item `claims`). M4: a missing-input record has exactly its
  keys and a non-empty reason. M5: the momentum's `unconstrained_modes` is a non-empty list of names and `source` a name; the PID record
  keeps the TOF record's β, which must equal `L/(c TOF)`. M6: the record marks whether the working-point pair is within support, and the
  tool keeps the migration inside and outside support separately. M7: the counts controls print their contract codes (`PLANT-CODES`),
  which the job requires exactly. M8: every control command reads `/dev/null`, and the cases are counted. N1: the adapter declarations'
  test count is required. N2: `-s` on the bytecode step. N3: the dE/dx record carries its `track_id`. N4: priors that weigh nothing are
  refused, never a division by zero.
