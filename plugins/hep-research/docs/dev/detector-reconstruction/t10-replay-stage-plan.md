# T10: the destriping reference replay, stage plan (stages 1-3, stage 4 drafted)

Finish-plan Task E1, option B2 of `t10-options.md` (section "Option B"), chosen by the user in `decisions.md` ("The user's answer to
U7", 2026-11-12): "B2 Python destriper", "Counts; freeze tolerance later". Written before any code of this stage; every tolerance and
expectation below is fixed here, before the test that uses it. Synthetic fixtures only; no quality claim (R14, R23, §12.1).

Sources read for this plan: plan v9.2 R14, R37, §9.6, §10.3, §14.1, A34, W7; `t10-options.md` sections 1-3; `t11-cells.md` F38 (the
method, null-mode and signature rows); `decisions.md` K02, K03, K09, U12 A, U7; `contract-map.md` W7; plugin
`contracts/reconstruction.py` (`_check_global_scan`, `_check_reported_values`, `_check_scan`), `contracts/schemas/reconstruction_product.json`
(scan block), `tests/contracts/reconstruction_fixtures.py` (`global_scan`, `scan_product`), `contracts/validate.py` (artifacts_dir),
`core/status.py`, and the layout of `adapters/calo-cluster` and `adapters/photon-likelihood`. Statements marked **unsourced** are the
agent's own derivation or knowledge, not taken from a source read.

## 1. What is built

- `adapters/destriper`, a development binding in Python (env/py313: NumPy, standard library), **not a native backend**; the native
  scan or global solver stays a recorded gap, as U12 A did for T08 and T09. Status `proposed` until a job of record runs it.
- Recipe `reco.scan.destriper/1`: F38's destriping as `t11-cells.md` records it ("joint fit of map and baselines, conjugate gradient for
  amplitudes, then binning"; null space "one-dimensional" for "baselines sufficiently connected"; "an explicit zero-sum condition").
- Data side `assets/destriper.py` (CLI) and `assets/destripe_recipe/` (reader, solver, product). Scoring side
  `assets/fixture_tools/` (generator, negative variants, the exact reference, the comparator, the replay helpers), never imported by the
  data side.
- Model (W7 global grown to a real operator, `t10-options.md` option B): `y_t = m_{p(t)} + a_{b(t)} + n_t`, `t = 0..N_t-1`, baseline
  `b(t) = floor(t / L)`, pointing `p(t)`, white noise of one variance. Null mode: `m + c`, `a - c` for any `c` (connected scan).

## 2. Stage 1: the fixture generator (`fixture_tools/t10_fixture.py`)

Fixture `t10-destripe/1`, seed **20260** (recorded in the truth file and the job, never in the data-side file). Streams: pointing
`numpy.random.default_rng(seed)`, signal `default_rng(seed + 1)`, noise `default_rng(seed + 2)`.

- Geometry: 16 pixels, 32 baselines of `L = 8` samples, `N_t = 256`. Baseline `b` sweeps a contiguous arc of `arc_b` pixels from a
  start `s_b`: `p = (s_b + floor(j arc_b / L)) mod 16`, `j = 0..7`; `s_b = rng.integers(0, 16, 32)`, then `arc_b = rng.choice([2, 4], 32)`.
- Signal: map `m_p` integers in `[-19, -1] U [1, 19]` (magnitude `rng.integers(1, 20)`, sign `rng.choice([-1, 1])`, per pixel in that
  order); baselines in 16 pairs `(v, -v)`, `v = rng.integers(1, 10)`, then permuted by `rng.permutation(32)`. So `sum a = 0` exactly and
  every `|m_p|, |a_b| >= 1`: in the noiseless variant the zero-sum constrained solution **is** the truth, and no value is near zero (the
  contract's value check is relative to each value's size, section 4).
- Variants: `noiseless` (`y = m_p + a_b`, exact integers as floats); `noisy` (plus `sigma = 1` white Gaussian noise, artificial units);
  `disconnected` (baselines 0-15 see pixels `p mod 8`, baselines 16-31 see `8 + (p mod 8)`; signal and noise as `noisy`): two connected
  components, so two null modes, and one zero-sum constraint leaves one undetermined.
- Files: `destriper-timestream/1` (data side: format, role `reconstruction-input`, unit, pixels, baseline_length, noise premise,
  `pixel` and `value` arrays; no seed, truth or variant name) and `destriper-truth/1` (scoring side: seed, variant, sigma, map, baselines).
  JSON with sorted keys, shortest round-trip floats.
- Negative variants (`NEGATIVE_VARIANTS`), each one change to a global scan block, each refused by `contracts.reconstruction.read_sidecar`
  with the named code: `jitter` (regularization `jitter`, no constraint) -> `reconstruction.scan.jitter_precision`; `chunk-average`
  (merging `chunk-average`) -> `reconstruction.scan.chunk_average`; `unique-without-constraint` (uniqueness claim, no constraint) ->
  `reconstruction.scan.unique_claim`; and the `disconnected` input (stage 2: the solver refuses it; a product that claims it determined
  is refused with `reconstruction.scan.unidentifiable_unnamed` and `reconstruction.scan.unique_claim`).

Expectations, fixed (login, pointing-only numbers measured with a scratch copy of this rule before the generator was written,
`jobs/t10-replay/tdd-logs/login-geometry-numbers.log`):

| ID | Expectation | Tolerance |
| --- | --- | --- |
| F1 | Same seed and variant: byte-identical files; seed 20261: different pointing | exact |
| F2 | The timestream file has exactly the data-side keys; no seed, truth or variant | exact |
| F3 | Every pixel observed: hits min 6, max 28; one connected component (pixels and baselines) | exact |
| F4 | Reduced baseline operator on `1-perp`: `kappa = 24.47`; `G = ||M^-1 P^T F||_2 = 0.8757`; one zero eigenvalue | `kappa` within 0.01, `G` within 1e-4, zero eigenvalue below 1e-10 |
| F5 | Noiseless: `y` equals `m_p + a_b` exactly; `sum a = 0`; all values integers with magnitude >= 1 | exact |
| F6 | Noisy: residual `y - m - a` has sample standard deviation in [0.85, 1.15] and mean within 0.25 | as stated (about 3.4 sd and 4 sd at n = 256) |
| F7 | Disconnected: exactly two components, {pixels 0-7, baselines 0-15} and {pixels 8-15, baselines 16-31}; every pixel observed | exact |
| F8 | Each negative variant applied to the contract fixture's global scan (with a null mode) is refused with its code; the unmodified one passes | exact codes |

## 3. Stage 2: the solver and its product (`destripe_recipe/`, `destriper.py`)

- Reader of `destriper-timestream/1`: refuses (exit 2, `rejected`) a wrong format, missing or extra keys, a length not a multiple of
  `L`, a pixel index out of range or not an integer, a non-finite value. An unobserved pixel, or a scan with more than one connected
  component, is refused (exit 1, `refused`): the tool ran its check and the map is not determined by the data and the one constraint;
  the disconnected refusal names the components and the remaining null mode. No product is written on a refusal.
- Solver (**unsourced** in its details: the standard reduced destriping system, written by the agent; the method is F38's): with
  `M = P^T P`, `Z = I - P M^-1 P^T`, solve `D a = F^T Z y`, `D = F^T Z F`, by conjugate gradient restricted to `1-perp` (the zero-sum
  constraint): start `a = 0`, project every residual and direction onto `1-perp` (`v - mean(v)`), stop when the **recomputed**
  relative residual `||Pi(F^T Z y - D a)||_2 / ||F^T Z y||_2 <= eps`; budget 320 iterations (10 x baselines); then `a <- Pi a` and the
  map by binning, `m = M^-1 P^T (y - F a)`. Stopping value `eps` is a recipe setting, recorded in the product: default `1e-10`.
  Budget exhausted: `not-converged`, exit 1, no product. Iterations and the final recomputed relative residual are recorded.
- `--constraint zero-sum` (default): the scan block states the constraint (`statement` "zero-sum of the baselines", weights 0 on the map
  and 1 on each baseline, value 0), `unidentifiable` `[]`, `uniqueness_claim` true, `regularization` "none", `merging` "joint-model",
  and reports every map value and baseline as a unit-weight component.
  `--constraint none`: no constraint, `unidentifiable` names every parameter (each has a component along the offset mode),
  `uniqueness_claim` false, and only identifiable combinations are reported: `m_p - m_0` (p >= 1), `a_b - a_0` (b >= 1), `m_0 + a_0`.
- Product `destriper-product/1`: header (format, recipe, label `synthetic; development binding, not native`, input SHA-256, solver
  record, method card path and SHA-256), the map and baselines, and the embedded `reconstruction-product/1` with
  `reconstruction:scan-v1`, subcase `global` (design `[P F]` row by row, observation `y`). `check-product` reads it back, refuses a
  malformed or incomplete product (exit 2), checks the method card hash and runs `read_sidecar` on the embedded product (exit 1 on an
  error). A product is never overwritten.
- Method card `assets/destriper.method-card.json` (§9.6, A34): the unconstrained mode (common offset `m + c, a - c`), the named
  constraint that fixes it (zero-sum of the baselines, astro-ph/0501504 as `t11-cells.md` records it), the precondition (one connected
  component; otherwise a further mode per component, refused), the data that constrain it (none: the timestream cannot), independent
  observables that could confirm it (an external absolute calibration of one pixel or baseline; none in this fixture), and the label
  development binding, not native.
- `contracts/validate.py`: a reconstruction product is a sidecar, not an artifact (its schema says "Read by contracts/reconstruction.py,
  not an artifact type"), so validate.py does not run `_check_global_scan`. Reading used: the product passes `read_sidecar`, and an
  artifacts_dir holding the extracted product and a `computational-run` artifact that refers to it by path passes
  `contracts/validate.py <dir>` (written by `fixture_tools/t10_replay.py records`).

Expectations, fixed:

| ID | Expectation | Tolerance |
| --- | --- | --- |
| S1 | Each malformed timestream above: exit 2, no product; unobserved pixel and disconnected scan: exit 1, no product, components named | exact |
| S2 | Hand-made consistent system (4 pixels, 8 baselines, L 4): map and baselines equal the constrained solution by a second coding in the test (NumPy KKT solve) | 1e-12 absolute, at `eps` 1e-14 |
| S3 | Hand-made noisy system: `||a - a_ref||_2 <= 10 kappa eps ||a_ref||_2` and `||m - m_ref||_2 <= 10 G kappa eps ||a_ref||_2`, `a_ref` by the second coding, `kappa`, `G` computed in the test | as stated, `eps` 1e-10 |
| S4 | Recorded relative residual `<= eps`, recomputed by the test from the product's values; iterations `<=` 320; budget 1 on a system that needs more: `not-converged`, exit 1, no product | exact comparisons |
| S5 | `|sum a| <= 1e-13 sum |a|`; the operator's null mode: `||D 1||_2 <= 1e-12` | as stated |
| S6 | The constrained product passes `read_sidecar` with no error; the unconstrained one too, with every parameter named unidentifiable | exact |
| S7 | Negative variants on the solver's own product: refused with the stage 1 codes; a noiseless product with one value moved by 1e-6 is refused with `reconstruction.scan.reported_mismatch` (the contract's own value check ran) | exact codes |
| S8 | Method card: the keys above; the product names it by SHA-256; `check-product` refuses a product whose card hash differs | exact |
| S9 | The data side (`destriper.py`, `destripe_recipe/**`) imports no `fixture_tools` module and no truth reader | AST scan |
| S10 | CLI: `solve` refuses an existing target; `check-product` exit 0 on a good product, 1 on a sidecar error, 2 on a malformed one. **Fix round 1 (m1):** also exit 2, no traceback, for a map that is not a list, a non-number `stopping` or `relative_residual`, a `method_card` that is not an object | exact |
| S11 | `records`: the artifacts_dir passes `contracts/validate.py` (exit 0, `ok` true), the product listed under `sidecars`. Reading (m7): validate.py lists the sidecar and does not open it, so its pass covers the run record; the W7 global checks come from `read_sidecar` (`check-product`, exit 0) | exact |
| S12 | **Fix round 1 (m2).** `check-product` refuses (exit 2) a product whose top-level `map` and `baselines` are not exactly the embedded reported values: with the constraint, `reported` = `map + baselines`; without it, the reported differences and sum computed from them as the writer does | exact float equality |
| S13 | **Fix round 1 (m8), runtime null-mode drift without the constraint.** `t10_replay.py null-mode-drift`: plain conjugate gradient on `D a = F^T Z y` with **no** projection (the recipe's operator, a scoring-side loop), started at `a0 = c 1` for `c = 0` and `c = 7`. Both stop at the recomputed relative residual `<= 1e-10` (unprojected); their baseline means differ by 7 (the start, not the data, sets the offset: the null mode); after removing each mean the two agree. The recipe's own zero-sum run started anywhere returns mean 0 | mean difference `7` within `1e-9`; demeaned difference `<= 1e-8 ||a||_2`; recipe mean `<= 1e-13 sum |a|` |

## 4. Stage 3: the exact reference and the comparator

- `fixture_tools/t10_exact_reference.py`, written independently of the solver and **hashed before any run** (the hash is in the ledger
  below and pinned in the stage 4 job): standard library only (`fractions`, `json`, `hashlib`, `argparse`, `sys`), its own reader of
  the timestream, no import of `destripe_recipe`, NumPy or any other fixture tool. Method different from the solver's: the joint KKT
  system in exact rationals, `[A^T A, c; c^T, 0] [x; lambda] = [A^T y; 0]` with `A = [P F]`, `x = (m, a)`, `c` the zero-sum weights,
  solved by Gauss-Jordan elimination on `Fraction`s (every float of the input is read as its exact binary value). Singular KKT matrix
  (disconnected scan): `refused`, exit 1, no values. Output `t10-exact-reference/1`: each value as an exact `p/q` string and its
  nearest float, the input SHA-256, the reference's own SHA-256.
- `fixture_tools/t10_comparator.py`: exact differences `Fraction(x_cg) - x_ref`, compared in squared 2-norms exactly.
  Tolerance record `assets/t10-replay.tolerance.json`, state **drafted** (K09; the user freezes it before the run). With a drafted
  record the comparator prints `DRAFT READING` lines and exits 3 (`incomplete`); a verdict (exit 0 or 1) only with state `frozen`.

Drafted tolerance (section 6 is the question for the user). Derivation, for the baselines (**unsourced**: standard linear algebra, the
agent's derivation): on `S = 1-perp`, `D` is symmetric positive definite with eigenvalues `lambda_max >= ... >= lambda_min > 0`; the
error `e = a_k - a*` lies in `S` and `D e = -r`, so `||e||_2 <= ||r||_2 / lambda_min <= eps ||b||_2 / lambda_min <= eps kappa ||a*||_2`,
`kappa = lambda_max / lambda_min`, since `||b||_2 = ||D a*||_2 <= lambda_max ||a*||_2`. The map follows by binning:
`delta m = -M^-1 P^T F delta a`, so `||delta m||_2 <= G ||delta a||_2`. A factor `s = 10` covers the rounding of the recomputed
residual and of the binning. So:

    ||a_cg - a_ref||_2 <= tau_a ||a_ref||_2,   tau_a = s kappa eps          = 10 x 24.47 x 1e-10          = 2.447e-8 -> 2.5e-8
    ||m_cg - m_ref||_2 <= tau_m ||a_ref||_2,   tau_m = s G kappa eps        = 10 x 0.8757 x 24.47 x 1e-10 = 2.143e-8 -> 2.2e-8

at `eps = 1e-10`. Precondition: `kappa eps >= 1e3 u` (`u = 2^-53`), so the bound is far above rounding: `2.4e-9` against `1.1e-13`.

| ID | Expectation | Tolerance |
| --- | --- | --- |
| R1 | The reference imports only the standard library modules above (AST scan) | exact |
| R2 | Hand-made 2 pixels, 2 baselines, L 2, consistent: values equal the hand derivation in the test | exact `Fraction` |
| R3 | Hand-made noisy dyadic input: the output satisfies `A^T (y - A x) = c lambda` and `c^T x = 0` exactly (checked by the test's own sums) | exact |
| R4 | Disconnected hand-made input: `refused`, exit 1, no values | exact |
| R5 | Each float in the output is the nearest float of its exact value; the record carries the input's and its own SHA-256 | exact |
| R6 | (added before the job was drafted) The noiseless reference equals the truth exactly (`t10_replay.py reference-equals-truth`); one changed value or a short list is not equal | exact `Fraction` |
| R-n1 | **Fix round 1, note (review n1).** The reference is pinned and unchanged: a `baseline_length` of 0 gives an uncaught ZeroDivisionError and a boolean pixel index is accepted. Its only inputs in the job are the generator's files (`baseline_length` 8, integer pixels), so neither case can arise there; recorded, not fixed | none |
| C1 | Frozen tolerance, product within it: exit 0 `passed`; one baseline moved by `2 tau_a ||a_ref||_2`: exit 1 `failed` | exact |
| C2 | Drafted tolerance: exit 3, `DRAFT READING` lines, no verdict word | exact |
| C3 | The comparator recomputes `kappa` and `G` from the timestream (NumPy, scoring side) and refuses (exit 2) a tolerance below `s kappa eps` or `s G kappa eps`, or a product whose `eps` is not the record's, or `kappa eps < 1e3 u`. **Fix round 1 (m8):** also a record with `s < 10`, or whose `kappa` or `map_gain` differ from the recomputed values by more than 0.01 or 1e-4 (F4's tolerances), and a reference whose multiplier is not exactly 0 (n3: `b` lies in `1-perp`, so `lambda = 0` exactly) | exact comparisons |
| C4 | **Fix round 1 (I1): the stopping ladder**, replacing the `eps / 2` gate. Five more solver runs at `eps_j` in {1e-2, 1e-3, 1e-4, 1e-5, 1e-6}. Gates: each run's baseline difference within `s kappa eps_j ||a_ref||_2` and map difference within `s G kappa eps_j ||a_ref||_2` (`s`, `kappa`, `G` the record's, checked by C3); for consecutive rungs, the baseline difference strictly smaller whenever the iteration count rises and equal when it does not; fewer iterations at a smaller `eps_j` fails. At least 2 strictly smaller steps are required, else the comparator reports `incomplete` (exit 3), not passed. Readings, not gates: whether the map difference shrinks at each step (no cited theory guarantees it, review m4), and `||delta m||_2 / (G ||delta a||_2)` | exact comparisons |
| C4r | **Fix round 1, readings.** The `eps / 2` run stays a recorded determinism reading (bit-identical values when it takes no extra iteration; within `tau / 2`). The a-posteriori bound `s max(r_n, 1e4 u) ||b||_2 / lambda_min` (`b`, `lambda_min` recomputed from the timestream) is recorded beside the measured `||a_cg - a_ref||_2`, as a reading, not a gate | none (readings) |
| C5 | `|sum a_cg| <= 1e-13 sum |a_cg|` and the reference's `sum a = 0` exactly | as stated |

Prediction (**unsourced**: CG's error in the 2-norm decreases monotonically, a property of the method the agent recalls, not read
here): C4 passes on the fixture; a failure is a reading to report, not a result to tune. Whether it is informative (more iterations)
is not predicted: see the amendment.

**Amendment C4-1 (login, hand-made systems, before any fixture run; superseded by fix round 1, below).** The first form, `eps_h = min(eps, r_n) / 2`, was meant to force
one more iteration. On hand-made systems conjugate gradient terminates in as many steps as `D` has distinct eigenvalues on `1-perp`,
and the last step takes the residual from about 1e-3 to the rounding floor (about 1e-15): `r_n` was 1.3e-15 and 2.2e-15 on two seeded
6-pixel, 12-baseline systems, so `eps_h` fell below rounding, and the halving run met a collapsed recurrence (a division by zero,
`stage3-green-1.log`; the solver now restarts from the recomputed residual and stops at its budget, test S4). The fixture's `D` has 15
distinct eigenvalues on `1-perp` (`login-geometry-numbers.log`), so the same finite termination can happen there. The check is
therefore at `eps_h = eps / 2`, far above rounding, with the conditions in C4 above; a non-informative halving is a recorded reading,
not a pass of the shrinking clause, and is put to the user with the tolerance (section 6).

**Fix round 1 (review `t10-replay-review.md`, I1; the coordinator's ruling).** The reviewer ran the solver on the fixture's pointing with
55 synthetic data sets (other values, never the fixture's): conjugate gradient terminates at iteration 15 every time, the residual
falling from about 1e-7..1e-8 to about 2e-16, so `eps` and `eps / 2` stop on one iterate and C4 tested determinism only. The stopping
ladder (C4 above) is informative on that pointing (239 of 320 ladder pairs in the review, no non-shrinking baseline step, no bound
violation). Expected size of the replay's differences, a prediction from those synthetic data sets, not a fixture reading: about 3e-16
to 3e-15 of `||a_ref||_2`, seven orders below `tau_a`; so a comparator PASS means only "below tau". The noiseless product (eps 1e-13)
is compared too, under its own record `assets/t10-replay-noiseless.tolerance.json` (the comparator refuses a stopping value other than
its record's): `tau_a = 10 x 24.47 x 1e-13 = 2.447e-11 -> 2.5e-11`, `tau_m = 10 x 0.8757 x 24.47 x 1e-13 = 2.143e-11 -> 2.2e-11`
(`kappa eps = 2.4e-12 >= 1.1e-13`), with no ladder (the ladder is the noisy replay's).

## 5. Stage 4 (drafted, not submitted): one job

`jobs/t10-replay/t10-replay.sh`, snapshot rule (copy the manifest's files, check every entry in the copy, run every later step from the
copy, as `jobs/d4-e6c/e6c.sh`). **Fix round 1 (I2):** the script is not in its own manifest (as e6c.sh): its SHA-256 is recorded from
`$0` in the receipt and the script is copied into `sources/`. Opening checks: manifest hash, interpreter SHA-256, Python 3.13.18, NumPy
2.4.6, the reference's SHA-256 against the ledger, both tolerance records' state `frozen` and their SHA-256 (exit 2 otherwise). Steps:
units (the three destriper test modules and `test_adapter_declarations`; a skip is a failure); fixtures; reference on noiseless and
noisy (disconnected: refused); the noiseless reference equal to the truth exactly; solver on noiseless at `eps = 1e-13`, noisy at
`1e-10`, the `eps / 2` reading run, the five ladder runs, noisy unconstrained, disconnected refused; `check-product` on every product;
the negative variants on every product (constrained and unconstrained); the null-mode drift case (S13) on the noisy timestream;
comparator on noisy (with the ladder and the `eps / 2` reading) and on noiseless (its own record); records and `contracts/validate.py`;
`read_sidecar` timing. Resources 1 CPU x 4,000 MB, 1 h limit; predictions in the report. Order after the user freezes: set `state` and
`frozen_by` in both records, pin both `TOLERANCE*_SHA256` in the script, rebuild the manifest (`build_manifest.sh`), pin its hash.

## 6. The tolerance question (for the user, K09)

The question, as put to the user, is in `t10-replay-report.md` ("Fix round 1", final tolerance question). Values: noisy replay
`eps = 1e-10`, `s = 10`, `tau_a = 2.5e-8`, `tau_m = 2.2e-8` (relative to `||a_ref||_2`, 2-norms), zero-sum `1e-13`, the stopping ladder
C4 with at least 2 informative steps; noiseless `eps = 1e-13`, `tau_a = 2.5e-11`, `tau_m = 2.2e-11`. Expected differences about 3e-16
to 3e-15 (a prediction from synthetic data on the fixture's pointing): a PASS means only "below tau". The job does not start until both
records are `frozen` (section 5 gives the order).

## 7. Login measurements behind the sizes

`_check_global_scan` through `read_sidecar` on a global scan of 16 pixels, 32 baselines, L 8 (256 rows, 48 parameters, every value
reported), login node (`jobs/t10-replay/tdd-logs/login-validator-cost.log`; a design of the same shape, not the fixture): consistent observations 30.9 s,
noisy 0.70 s. The exact reference on the same geometry with seeds 1 and 2 (not the fixture's): 0.14 s each
(`login-reference-cost.log`). The cost is
in `_check_reported_values`, which runs an exact `Fraction` rank twice per reported component when the observations are consistent; it
grows about as rows x parameters^3, so the next size (32 x 64) was stopped after 3 min. The fixture keeps this size; unit tests use
hand-made systems of at most 8 baselines.

## 8. Ledger

| Item | SHA-256 | When |
| --- | --- | --- |
| `fixture_tools/t10_exact_reference.py` | `440a1e0d1a7bf169f5e1f8281d45b34739d37e4a0ea56c945a53501f694701db` | stage 3, written and hashed before its first run (not yet run on the fixture) |
