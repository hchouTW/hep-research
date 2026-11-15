# T10: solver options for the scan or global reference replay (draft for U7)

Finish-plan Task E1, step 1. Documents only: no job, install or network access was used. Read for this draft: plan v9.2
(R14, R20, R35, R37, §0.5.8, §3.3, §9.6, §10.3, W6, W7, §12.1, A34, A37, §15.1 K02/K03/K09, §16.1 row T10, BP07, BP13, BP14);
in `plugins/hep-research/docs/dev/detector-reconstruction/`: `finish-plan.md`, `t05-task-sheets.md`, `decisions.md` (K02, K03, K09,
U12 A, T09 D3 stage 1, parallel lanes), `contract-map.md` (W6, W7), `t11-cells.md` (F12, F36, F38), `coverage.md`,
`calibration-alignment-interfaces.md`, `t03-selection.md`, `STATE.md`; plugin `contracts/reconstruction.py` (scan checks) and
`tests/contracts/reconstruction_fixtures.py`; the installed files of `env/acts48` and `env/py313` (listings and headers only).
Anything not taken from these is marked **unsourced**.

## 1. What the plan asks for

- **§3.3, layer 2:** "Required executable workflows: Tracking/vertexing, calorimetry, photon likelihood, timing/PID, and at least one
  cross-system workflow; also a native non-hit input example and a scan/global reference replay."
- **§16.1, row T10:** "Timing/PID, cross-system and native non-hit examples; scan/global reference replay", acceptance "BP07/BP15 and
  selected BP; shared clock/nuisances, partial delivery, W7 subcases and A37".
- **R14:** "No native scan/global solver: T10's reference replay (one K02 solver on one K03 input against a fixed reference with a K09
  comparator; W7 alone does not count) is blocked."
- **§10.3** separates four kinds of input: "independent events, frames with local neighborhoods, mergeable scan summaries, and global
  estimation requiring a shared normal operator/correlation model." "Mapmaking or coherent estimates are handed to native solvers,
  preserving constrainable modes, transfer/noise, convergence, and mergeable sufficient summaries; do not average normalized results or
  discard cross-detector dependencies." Scan context "retains setting order, dwell/settling/effective time, RF/IF/LO or retarding
  coordinates, overlap, noise/response, rescan roles, and combination rules".
- **W7 (§12):** three subcases (RF scan, retarding scan, global `y_i = s + b`); "passing W7 cannot replace execution of their three
  native backends." **§12.1:** no automatic promotion from an artificial witness to backend smoke or higher.
- **A34:** "Null modes in global maps/fits: state unidentifiable components explicitly; do not fabricate information with jitter or naive
  chunk averages."
- **BP14:** "Mapmaking identifies shared noise/offsets, scan geometry, transfer/null modes, and the native solver; modes after projection or
  regularization must be named."

Reading used below: a **scan** replay runs a solver that combines settings of a scan (BP13: setting-time-counts, overlap, transmission); a
**global** replay runs a solver on a shared normal operator over many observations with its null modes (§10.3, BP14, W7 global). The
replay needs, together: one solver from the K02 stack, one K03 input, a fixed reference produced before the run, and a K09 comparator.

Where the plugin stands. T06 (done, Gate C job 7487578) implemented W7 as contract checks: `contracts/reconstruction.py`
`_check_global_scan`, `_check_overlaps`, with fixtures `radio_frequency_scan`, `retarding_scan`, `global_scan`. These check a stated
product; they produce no estimate. Their docstring says so: "Section 10.3 leaves the estimate to a native solver, so a value is compared
only when every estimator agrees", and "a scan has no comparator". The value check runs only when the observations are exactly
consistent, so a noisy input needs its own comparator. `coverage.md`: F36 and F38 have no plugin text and no binding; `t11-cells.md`
F38 and F36 cells have `Binding: none`, `Run evidence: none`.

What is installed (checked in the files, not from memory):

- `env/acts48` (`conda-meta`): `acts-core` 48.2.0, `eigen` 5.0.1, boost, gcc/gxx, cmake; no Python. ACTS headers contain no scan,
  mapmaking or alignment solver (`include/Acts/` holds AmbiguityResolution, Clusterization, ... TrackFitting, Vertexing). The one
  "global" class is `Acts::Experimental::Gx2Fitter` in `Acts/TrackFitting/GlobalChiSquareFitter.hpp`; its normal system is solved in
  `computeGx2fDeltaParams` (`Acts/TrackFitting/GlobalChiSquareFitterBackend.hpp`, "column-pivoting Householder QR"), per track.
  Eigen headers present: `Eigen/src/IterativeLinearSolvers/ConjugateGradient.h`, `LeastSquareConjugateGradient.h`, `BiCGSTAB.h`;
  `Eigen/src/QR/CompleteOrthogonalDecomposition.h` (has `rank()`); `Eigen/src/SVD/JacobiSVD.h`, `BDCSVD.h`. Note: the package is
  5.0.1 by `conda-meta`, but `include/eigen3/Eigen/Version` defines `EIGEN_WORLD_VERSION 3`, `EIGEN_MAJOR_VERSION 5`,
  `EIGEN_MINOR_VERSION 0`; not resolved here.
- `env/py313` (the job interpreter, `STATE.md`): NumPy 2.4.6, SciPy 1.17.1, SymPy 1.14.0, mpmath. `scipy/sparse/linalg/_isolve/`
  (`iterative.py`, `lsqr.py`, `lsmr.py`, `minres.py`) is Python source over NumPy; `scipy/linalg/_flapack*.so` (LAPACK) and
  `scipy/sparse/linalg/_dsolve/_superlu*.so` are compiled.
- No domain scan or mapmaking package (for example a destriper) in either environment.

So no installed K02 component is a native scan or global solver in §10.3's sense. Eigen, LAPACK and SciPy are general linear algebra.

## 2. Options

Common to A, B and D: K03 is synthetic, generated by the agent, role labelled (`decisions.md`, K03 "Fixed"). The comparator's tolerance
is a K09 value, and K09 thresholds are frozen by the user (`decisions.md`, K09 "Needs the user"). R37's rule that deterministic checks
"none of them waits for frozen K09 thresholds" covers `CAI-` items only; the replay is not one. So under every option the comparator's
tolerance is drafted with the stage and frozen by the user before the run (part of the question in section 3).

Cost basis (recorded jobs, not T10 measurements): a Python development-binding job with unit modules and a small run, 14 min 31 s (job
7565328, T09 D3 stage 1) and 20 min 37 s (job 7584387, D4 E1); E6c job 7592360, 17 min; a C++ build against acts-core, 24 s in job
7470886 (27 s elapsed); a login compile check of the T07 driver, 101 s (`decisions.md`, 2026-11-09); static check 327 s
(`STATE.md`, `baseline_static`), 5-9 min in `finish-plan.md`. The solve itself on a fixture of a few thousand samples is expected to
take seconds: **unsourced estimate**, to be measured on login before the job.

### Option A: ACTS `Gx2Fitter` on a track fixture

- **Runs on:** a T07-style synthetic telescope fixture (K03), for example the weak-mode fixture 7004 against 7003 (`CAI-T07-4`,
  job 7546791), refitted with `Acts::Experimental::Gx2Fitter` in place of the Kalman refit.
- **Comparator (K09):** fitted parameters and covariance against a fixed closed-form least-squares reference for straight or helical
  tracks, deterministic tolerance.
- **Proves:** a native normal-equation solver from the K02 stack runs on K03 input and reproduces a fixed reference.
- **Does not prove:** anything about scan or global estimation. A track fit is per track: by §10.3 it is the "independent events"
  kind, with no normal operator shared across observations. It also cannot show A37's weak mode as a solver null mode: the weak mode of
  fixture 7004 is an alignment mode outside the per-track system (χ²/ndf unchanged while `q/p` is biased).
- **Effort:** 1 stage (C++ driver, reference, job); new API surface in an `Experimental` namespace.
- **Resources:** build about 0.5 min (7470886), job of the 7551619 kind, 17 min 05 s; under 0.5 CPU-h.
- **Risk:** reviewers, or the user, reading it as satisfying R14 when it does not meet §10.3. Not recommended; listed because the brief
  asks whether an ACTS component fits. None does.

### Option B: a destriping solver written in the plugin as a development binding (recommended)

The method is the one `t11-cells.md` F38 records from sources read: "destriping: joint fit of map and baselines, conjugate gradient for
amplitudes, then binning" (astro-ph/0412517, astro-ph/0501504, 0904.3623, sections as listed there); "destriping's matrix is singular.
astro-ph/0501504 states an explicit zero-sum condition; 0904.3623 solves orthogonal to the null space"; "a stated constraint is what
fixes the offset, not added data. This agrees with W7." It is the W7 global subcase grown to a real operator: `y = P m + F a + n`
(pointing `P`, map `m`, baselines `a`, white noise `n`), whose null mode is the common offset `m + c, a − c`.

- **Runs on (K03):** a synthetic timestream generated by the agent, seed recorded: a few pixels, baselines of fixed length, pointing with
  enough crossings (F38 "baselines sufficiently connected: null space is one-dimensional"), white noise. Variants: (1) noiseless, where
  the contract's own value check applies; (2) noisy, the replay case; (3) negatives: jitter regularization, a naive chunk average, a
  uniqueness claim without a constraint, and a disconnected scan with a second null mode, each refused.
- **Solver:** conjugate gradient on the normal equations with the zero-sum constraint on the baselines, written in this plugin, labelled
  a development binding, not a native backend (as `decisions.md` records for T08 and T09, U12 A). Two forms, one to choose:
  - **B1, C++ with Eigen** in `env/acts48` (`ConjugateGradient.h` or `LeastSquareConjugateGradient.h`): the solver library lives in
    the K02 backend environment and is compiled.
  - **B2, Python with NumPy and SciPy** in `env/py313`, the T08 and T09 pattern: one interpreter for solver, reference and checks.
  Neither is more "native" than the other in R14's sense; B2 is simpler to review, B1 keeps the solve in the K02 environment.
- **Fixed reference:** an independently written exact solve in rational arithmetic (Python `fractions`, or SymPy 1.14) of the same
  constrained system, sharing no code with the solver (T09's practice: "an independently written evaluation that shares no code with
  the recipe", `adapters/photon-likelihood/adapter.json`), written and hashed before the run.
- **Comparator (K09, drafted, the user freezes):** map and baselines within a tolerance set from the CG stopping rule and the system's
  condition number, with a tolerance-halving check showing the difference shrinks; iterations and final residual recorded; the product
  written as `reconstruction:scan-v1`, subcase `global`, and passing `contracts/validate.py`: `unidentifiable` names the offset mode
  when no constraint is given; with the zero-sum constraint stated in `constraint` (weights, value 0), the map is determined; no
  `uniqueness_claim` without it. The method card lists the unconstrained mode and its named constraint (§9.6, A34).
- **Proves:** one solver from the K02 stack, in the T08/T09 sense of a development binding, runs on one K03 input and reproduces a fixed
  reference under a K09 comparator; the null mode is handled by a stated constraint, not by jitter or data (W7, A34) at run time, not
  only in a contract check. That is R14's replay definition, except for the word "native".
- **Does not prove:** a native backend (the gap stays recorded, as U12 A did for T08 and T09); mapmaking quality on any real scan
  strategy; correlated or cross-detector noise, filtering or transfer function, beam or bandpass (F38 gaps in `t11-cells.md`); the RF
  and retarding subcases at run time (they stay W7 contract checks); any F38 or cosmology claim. Evidence tier T3-E on synthetic data
  only (R23).
- **Effort, stages:** (1) fixture generator and negatives; (2) solver and product; (3) independent reference and comparator, tolerance
  drafted for the user; (4) one job, fresh review, close-out row in a T10 close-out.
- **Resources:** one Slurm job of the 7565328 / 7592360 kind, 15-21 min on 1 CPU, under 0.5 CPU-h; B1 adds a compile of about 0.5 to
  2 min (7470886; 101 s login check). A rerun after a fix round doubles that. No GPU, no install, no network.
- **Risks:** the contract validator computes rank and row space in exact `Fraction` arithmetic (`_check_global_scan`); its cost on a
  design of a few thousand rows is not measured, so the fixture is kept small and the cost measured on login first. CG on a singular
  system needs the constraint or a projection, or it drifts along the null mode: the negative cases must show that. The user may read a
  development binding as not meeting R14's "native"; then option C applies anyway, with B's evidence recorded beside it.

### Option C: declare the replay `blocked-by-resource` (R14)

- **What happens:** finish-plan E1 step 3: "No solver approved: T10's replay stays `blocked-by-resource` (R14). The rest continues."
  The block is recorded with the probe above (no native scan or global solver in `env/acts48` or `env/py313`), and listed open in every
  §18.2 report. `finish-plan.md` (What "Finished" Can Mean): "Without U7 ... the honest end state is incomplete", the scan or global
  replay among the open items.
- **Runs on / comparator:** nothing. **Proves:** nothing new; W7 stays at contract level, which R14 says "does not count".
- **Effort:** a record only. **Resources:** none.
- **Risk:** none technical; T10 cannot be `done`, and layer 2 of §3.3 stays incomplete.

### Option D (variant): a retarding-scan stacking replay as a development binding

- **Runs on:** a synthetic retarding scan (K03) with revisited settings of different dwell, per W7's retarding subcase.
- **Method:** F36 as `t11-cells.md` records from 2101.05253: "sum counts at like steps, average qU over scans", after stability is
  shown, keeping per-scan conditions.
- **Proves:** setting-time-count retention through a combination at run time. **Does not prove:** a solver: stacking is a sum, and the
  spectral fit is handed to statistics and theory (BP13). It is weaker than B as evidence of a "scan/global solver"; listed so the user
  can choose a scan rather than a global replay. Resources as B2.

## 3. Recommendation and the question

**Recommendation: B2, with C recorded beside it for the native part.** Write the destriper as a development binding in Python, run it once on
a synthetic timestream against an exact rational reference, and keep the native scan/global solver recorded as a gap, as U12 A did for
calorimetry and photon likelihood. Reason: no installed component is a scan or global solver (section 1), so a native replay is not
possible without an install; B is the only option that executes the global estimation §10.3 describes, with its null mode and named
constraint, on the method the T11 cells source; it costs one short job; and it adds runtime evidence for A34 and §9.6 that C does not.
B2 over B1 because it follows the T08/T09 route reviewers already checked; B1 gains nothing in R14's "native" sense.

**Question for the user (U7):**

> T10 needs a scan or global reference replay (R14). No installed package is a native scan or global solver. Which do you choose?
> (A) ACTS's `Gx2Fitter` on a track fixture: native, but a per-track fit, not a global solver, so it does not meet Section 10.3.
> (B) A destriping solver written in the plugin as a development binding (B2 Python, or B1 C++ with Eigen), one job of about 20 min,
> labelled not native, with the native-solver gap recorded as with U12 A (Recommended, B2).
> (C) Record the replay `blocked-by-resource` now and do no solver work.
> (D) A retarding-scan stacking replay as a development binding instead of a global one.
> If B or D: does a development binding count as R14's "one K02 solver" for T10's replay, and do you freeze the comparator tolerance
> when the stage drafts it (it is a K09 value)?

## 4. T10 stages that do not wait for U7

Prerequisites common to all: T06 `done` (`STATE.md`; Gate C job 7487578); contracts for W6 and the scan checks exist; R37: "As interface
tests with no quality claim, none of them waits for frozen K09 thresholds" and "All tolerances are fixed and recorded before the test
runs"; jobs run from a checked copy (current practice, `progress.md`, E6b and E6c). No quality claim for any of them before K09.

1. **Timing chain records (R35) and `CAI-T10-1`, single-ended counters.** Each time hit keeps its value before and after each step
   (channel offset, amplitude-dependent time walk, propagation along the counter) with each step's payload, in chain order; amplitude
   or charge; path length; each event time its source, estimator, and hit identifiers and weights. Checks as R37 states them: a channel
   offset change Δ moves that channel's offset-corrected times by exactly −Δ and others by 0, applied once and before time walk; with an
   external event time only the affected track's TOF and β change; for a common linear event time it changes by `w_k·Δt_k`, other
   tracks' TOF by the opposite amount, the affected track's by `(1 − w_k)·Δt_k`; per-track leave-one-out: `−w_k^(−j)·Δt_k` for other
   tracks, `Δt_k` for the affected one; a non-linear estimator recorded without a numeric assertion. dE/dx keeps per-measurement samples
   and path lengths before truncation and normalization (R35). Prerequisites: a payload format for the chain (T08's `calo-gain-payload/1`
   and R34's chain order are the precedent, `calibration-alignment-interfaces.md`); a sign convention stated before the run; method from
   `t11-cells.md` F12 (walk curve, per-channel t0, "keep single-hit, per-track, event-time, system apart"). The interfaces file lists R35
   as "Designed", "Not yet written".
2. **`CAI-T10-2`, two-ended counter.** Its own case, with the expectations stated before the run (R37): a one-end offset moves both the
   mean time and the propagation-corrected position. The expected sizes follow from `t_1,2 = t_0 + (L/2 ± x)/v`: a shift Δ at one end
   moves the mean by Δ/2 and the position by `v·Δ/2`, sign by the convention. **Unsourced:** this is the agent's derivation, not from a
   source read; the stage brief must state and check it.
3. **Cross-system example (BP15).** A TOF/β example that takes path length and momentum from the T07 ACTS recipe and times from the
   timing chain, with a shared-clock nuisance (§16.1 "shared clock/nuisances, partial delivery"; BP07 "TOF separates path, event time,
   and channel offset"; missing subsystem handled by a validated missing-input method, never zeros). Prerequisites: T07's recipe as
   closed out (job 7551619; quality still waits for K09 at Freeze B). **To check first:** R33's record holds per-measurement "incidence and
   path"; a flight-path length to a timing plane is not shown in the records read.
4. **Native non-hit input example.** Counts with thresholds and exposure (W6, BP12) run through a recipe, input in its native form: a
   valid zero, an absent interval, per-channel valid exposure (`count_witness` in `tests/contracts/reconstruction_fixtures.py`; contract
   checks from T06). R20: A19-A24 get their runtime here "if it covers the class, else a recorded gap"; `t05-task-sheets.md` lists
   A19-A24 that way. A23's coincidence contract part (`coincidence_witness`) is available if the example covers prompt-delayed counts.
5. **A37 and §9.6 in T10** (§0.5.8, §16.1, `t05-task-sheets.md` A37 → T10, T12): the artificial g×E degeneracy, and the T07 weak-mode
   fixture reused (fixture 7004 against 7003, `CAI-T07-4`, job 7546791), with the method card listing the unconstrained mode and its
   named external constraint. A37's P1 part is `CAI-T06-3` (`ConstraintIsNotValidation`), already tested in T06.

Order suggested: 1 and 2 together (one timing fixture), then 5 (no new code beyond the method card and a g×E fixture), then 4, then 3
(depends on T07 outputs). Each stage is costed from its own first run; by the jobs above, about 15-21 min on 1 CPU each (**estimate**,
from 7565328, 7584387, 7592360, not a T10 measurement).
