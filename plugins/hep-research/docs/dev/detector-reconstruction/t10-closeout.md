# T10 close-out against its obligations

T10 is timing, PID, the native non-hit input example and the scan/global reference replay (plan v9.2 §16.1 row T10, P3). It has two
development bindings in Python: `adapters/timing-pid` (recipe `reco.timing.time-chain/1`) and `adapters/destriper` (recipe
`reco.scan.destriper/1`, the replay chosen at U7). Paths are relative to `plugins/hep-research/`. Job evidence is in
`<private>/evidence/<folder>/`, and the job IDs are the ones `decisions.md`, `STATE.md` and the ledger record.

**Scope of this file.** One row per T10 obligation: §16.1 row T10 ("Timing/PID, cross-system and native non-hit examples; scan/global
reference replay"; acceptance "BP07/BP15 and selected BP; shared clock/nuisances, partial delivery, W7 subcases and A37"), R35, R37's T10
item (CAI-T10-1, CAI-T10-2), BP07 and BP15, A37 and §9.6, W6 with R20's A19 to A24, and the U7 replay (R14). T10 has no task sheet of its
own beyond `t05-task-sheets.md` (row T10, CAI table, A-ID table), so the plan's text is the list. Each row has its status and evidence;
anything not met says why and what would close it.

**Not judged here.** No timing, TOF, PID, dE/dx, calibration, counting or map-making quality is claimed (R31). Every number is from synthetic
fixtures or hand-made inputs; the PID figures (mis-ID, purity) are development readings, not gates. T10 has no frozen quality target of
its own; the replay's comparator tolerance is the one K09 value, frozen by the user.

**Status words** (as `t07-closeout.md` to `t09-closeout.md`).
- `met`: the evidence shows the obligation as the plan states it.
- `met with readings`: met, with a limit or a departure stated beside it.
- `open`: work, or a decision, is still owed.
- `gap`: it cannot be provided, on a recorded probe or a recorded decision (R37, K02, U7).

**Evidence jobs.**
- **Stage 1, timing:** job 7593003 (`jobs/t10-timing/t10-timing.sh` cc701385, manifest 90e0925b, 4,951 files; hpa-wn33, 2026-11-12,
  4 min 56 s, JOB RESULT PASS), evidence `t10-timing-s1-7593003/`.
- **Stage 2, timing:** job 7627284 (`jobs/t10-stage2/t10-stage2-r1.sh` 7f31e360, manifest SOURCES-r1 333aef85, 5,636 files; hpa-wn34,
  2026-11-13, 26 min 17 s, JOB RESULT PASS), evidence `t10-stage2-r1-7627284/`. It reran stage 1's CAI check on 10,000 events and its ten
  controls, and ran the full suite (units failing only on the LCG ID and the held `test_no_bytecode` on base 4c08da43; static 31 pass).
  The round 0 job 7627104 is a reading only.
- **Replay:** job 7596623, attempt 3 (`jobs/t10-replay/t10-replay.sh` 73587671, manifest cd29f627, 2,575 files; hpa-wn33, 2026-11-12,
  JOB RESULT PASS), evidence `t10-replay-7596623/`, with comparator values bit-identical to attempt 2, job 7594892.

**Adapter records (this close-out).**
- `adapters/timing-pid` 0.2.0, `demonstrated-on-synthetic-data` (VALIDATION TIMING-PID-T10).
- `adapters/destriper` 0.2.0, `demonstrated-on-synthetic-data` (VALIDATION DESTRIPER-T10).
- The jobs ran both `adapter.json` files at 0.1.0, `proposed`; 0.2.0 changes records only.

## Summary

The obligations table has 29 rows, each with a status.

| Status | Rows |
| --- | --- |
| met | 13 |
| met with readings | 12 |
| open | 2 (the cross-system TOF example; the native timing backend's record) |
| gap | 2 (A20 to A24; the native scan or global solver, U7 B2) |

Each row that is not met, in one line:

- **Cross-system TOF example, BP15 (open):** no record settles a flight-path length to a timing plane. The T07 product keeps
  `path_length_mm` on its eight telescope planes; the geometry has no timing plane, and the origin of `pathLength()` is not recorded. It
  closes when a timing plane, or an agreed flight-path definition from the T07 recipe, exists.
- **Native timing backend (open):** U12 A's decision (no native backend sought; a recorded gap) names calorimetry and photon likelihood.
  Applying it to timing is a reading of this file, not a recorded decision. It closes on the user's word.
- **A20 to A24 (gap):** this T10 example covers only counting with thresholds (A19). There is no coded or response image (A20), no
  multisite Compton (A21), no acoustic and optical association (A22), no prompt-delayed counts (A23), and no energy-resolving sensor
  (A24): recorded gaps per R20.
- **Native scan or global solver (gap):** none is installed (`t10-options.md` section 1). The user chose a development binding for the
  replay (U7 B2), answered "Counts" to whether it is R14's "one K02 solver", and the native lack stays recorded beside it.

Every row marked met with readings states its reading in its last column.

## Obligations

| Obligation | Status | Evidence | If not met, or the reading: why, and what closes it |
| --- | --- | --- | --- |
| §3.3 and §16.1: an executable timing/PID workflow | met with readings | `adapters/timing-pid`: the time chain, event times, TOF and β, TOF species hypotheses and dE/dx; jobs 7593003 and 7627284 PASS | A development binding on synthetic data, not a native backend |
| §16.1: cross-system example (TOF with path and momentum from T07, times from the timing chain), BP15 | open | Stage plan row R35-X; the T07 product reader `acts_native_product.py` (`path_length_mm` per telescope-plane state) | No flight-path length to a timing plane in the records (see Summary). The stage 2 PID uses a fixture momentum and path, labelled so (momentum source "fixture value (the T07 path stays open: R35-X)") |
| §16.1: native non-hit input example (W6, BP12) | met | `timing_recipe/counts.py`: native counter channels to a T06 `reconstruction:counts-v1` product that `contracts.reconstruction.read_sidecar` accepts; job 7627284 `counts.log` "RESULT t10-counts PASS" (2,000 events), the controls `absent-as-zero` and `run-time-denominator` fail with exactly `reconstruction.counts.absent_filled` and `.run_time_denominator`; `test_timing_counts` 7 OK | |
| §16.1 and R14: scan/global reference replay (one K02 solver on one K03 input against a fixed reference with a K09 comparator) | met with readings | `adapters/destriper` (U7 B2); job 7596623: comparator PASS, noisy baselines 6.847e-16 and map 4.666e-16 of ‖a_ref‖₂ in 15 iterations, noiseless 3.136e-16 and 1.729e-16, the stopping ladder with 4 informative steps, the zero sum, the exact rational reference equal to the truth; tolerance frozen by the user (decisions.md, 2026-11-12) | A development binding counted as R14's solver by the user's word ("Counts"). PASS means "below τ": the expected differences are about 1e-15 of ‖a_ref‖₂ |
| R14 and U7: a native scan or global solver | gap | `t10-options.md` section 1 (no native scan or global solver in env/acts48 or env/py313); decisions.md, the user's answer to U7 ("Counts": the development binding counts as R14's solver, the native lack recorded beside it) | Recorded gap, as U12 A. Closes only with a native solver to integrate, on the user's word |
| §16.1: W7 subcases | met with readings | Global subcase at run time: the replay (job 7596623; the product's `reconstruction:scan-v1` global block, the constraint named; every negative variant refused with its codes). RF and retarding: the T06 contract checks (Gate C job 7487578) | RF and retarding stay contract checks, not run at run time (`t10-options.md`, option B, "does not prove"); W7 alone never replaces a native backend (§12.1) |
| §16.1: shared clock and nuisances | met with readings | Stage 2 diagnostic: a common offset of every channel moves an external-time TOF by −δ and an internal one (common, leave-one-out) by 0; job 7627284 pid item shared-clock PASS (largest 3.55e-15 ns), control `clock-not-cancelled` fails only that item | Derived here, not from a source (STATE.md `r37_uncovered_cases`). The cross-system shared-clock nuisance waits for R35-X |
| §16.1 and BP07: partial delivery (a missing subsystem by a validated missing-input method, never zeros) | met with readings | `pid.missing`: status `missing-input`, exactly its keys, no numbers, a reason; the reader refuses zeros; job 7627284 pid item missing-input PASS, control `zero-filled-missing` fails only that item | Within the timing binding only; partial delivery across subsystems waits for R35-X |
| A37: the artificial g×E degeneracy | met | `fixture_tools/t10_a37.py` `gxe_check`, at run time: exact rational rank C+E−1; two gauges with identical amplitudes; convergence and a same-type holdout equal in both; gain ratios and products g·E equal; only the named constraint (an event of known energy) makes the rank full; a claim of identification by holdout or convergence refused. Job 7627284 a37 PASS (rank 9 without, 10 with), control `holdout-as-proof` fails only `gxe`; `test_timing_a37` ChainGauge (stage 1's walk follows the same gauge) | |
| A37: the weak-mode witness (T07's fixture reused) | met with readings | `t10_a37.py` `witness_check` reads T07's run record of CAI-T07-4 (job 7546791, `cai-refit.log`, SHA-256 0f60e9ac… pinned in the tool, its own outcome required): 8 cells, smallest q/p change 4.9543 per-track σ, largest \|Δχ²/ndf\|/se 1.753; control `placeholder-witness` (a real placeholder text) fails only `witness` | Read, not rerun: T07's run is reused as recorded (R37 "reused in T10 and T12"). A placeholder never satisfies A37 here; T12's placeholder checks are not used |
| §9.6: the method card lists unconstrained modes, their named constraints and independent observables; a used constraint is never validation | met | `assets/timing-method-card.json` (`timing-method-card/2`): the amplitude scale, the common time offset and the momentum source's curvature offset, each with a witness, `constraint.*` and `observable.*` items, disjoint by identifier; `method_card.check`; controls `no-constraint` and `validation-is-constraint` fail only `card`; CAI-T06-3 carries the contract part (`test_timing_a37`) | |
| R35: each time hit keeps its value before and after each step, with each step's payload, in chain order | met | `timing_recipe/time_chain.py`; the reader recomputes every applied value from its parameter and checks payload identities; `test_timing_chain` (36 in job 7627284; 29 in job 7593003) | |
| R35: amplitude or charge; both ends' times or the position; the path length | met | Hit records keep the amplitude, both ends (two-ended) or the track position with its source (single-ended), and the path length; refusals for missing ones (`SingleEndedChain`, `TwoEndedChain`) | |
| R35: each event time records source, estimator, hit identifiers and weights, so a calibration can exclude a channel's own hit | met | `timing_recipe/event_time.py`: source, estimator, hits with `track_id` and weights; leave-one-out excludes every hit of the track; `check(record, event)` and `tof(record, start, event)` verify against the event's hits and recompute the value (stage 2 fix round 1, I1); `LeaveOneOutByTrack` including the review's forgery | |
| R35: dE/dx keeps per-measurement samples and path lengths before truncation and normalization | met | `timing_recipe/dedx.py` (`timing-dedx/1`, with `track_id`); the reader recomputes everything from the samples; job 7627284 pid item dedx PASS, control `dedx-without-samples` fails only `dedx` | |
| R37 T10 (CAI-T10-1): single-ended counters; offset −Δ once and first; external, common linear and leave-one-out event-time expectations; non-linear recorded | met | `fixture_tools/t10_cai.py`; job 7593003 `cai.log` PASS on 10,000 events (largest time deviation 5.690e-15 ns against 1e-12) and the ten controls; job 7627284 regression PASS with the controls' exact failed items | |
| R37 T10 (CAI-T10-1f): finite step and step halving recorded | met with readings | Δ = 0.1 ns and Δ/2; quotients within 4 tol/Δ; β's forward-difference error ratio 0.4962 to 0.4988 in [0.45, 0.55] (job 7593003) | The coordinator-accepted reading of R37's step halving for exact linear checks (STATE.md `r37_uncovered_cases`) |
| R37 T10 (CAI-T10-2): a two-ended counter, a one-end offset moving the mean time and the position, expectations stated | met with readings | Job 7593003: CAI-T10-2 PASS (position 5.829e-14 cm against 1e-10; halving within bounds); controls `position-no-half`, `mean-one-end`, `recipe-position-no-half` | The expectations (−Δ/2 and ∓vΔ/2) are derived here, not from a source; recorded before the job (STATE.md, `calibration-alignment-interfaces.md`) |
| R37: fixture choices and derived expectations recorded before the run | met | STATE.md `r37_uncovered_cases` (stage 1, stage 2); `calibration-alignment-interfaces.md`, "T10 acceptance items" and "T10 stage 2 additions"; `t10-timing-stage-plan.md` sections 2, 3, 6 | |
| BP07: TOF separates path, event time and channel offset | met | The chain separates channel offset, walk and propagation; event times are separate records; TOF and β take the path from the hit record (CAI-T10-1, the diagnostics) | |
| BP07 deliverables: β and species likelihoods or scores with support domains; working point and priors kept | met with readings | `timing_recipe/pid.py` (`timing-pid/1`): Gaussian time likelihoods per hypothesis, LLRs, support per pair (k = 3), the working point with `selected_within_support`, probabilities only with priors; job 7627284 pid item hypotheses PASS (largest deviation 5.97e-13) | Fixture choices (STATE.md): masses 0.14 and 0.94 GeV, σ_t 0.1 ns, the Gaussian form; the momentum is a fixture value (R35-X open) |
| BP07: an LLR or score never a probability | met | `pid.check` refuses probabilities without priors and an LLR not labelled "log-likelihood ratio, not a probability"; control `llr-as-probability` fails only `hypotheses` | |
| BP07 diagnostics: shared-clock shifts, wrong bunch or path | met with readings | Job 7627284 pid items shared-clock, wrong-bunch (largest 3.55e-15 ns) and path (4.33e-15) PASS | Derived expectations (STATE.md); bunch spacing 2 ns a fixture choice |
| BP07 diagnostics: few samples and saturation | met | dE/dx flags `few-samples` (n < 4) and `saturated-in-kept`, recomputed by the reader (`DedxRetention`; job 7627284 item dedx) | |
| BP07 diagnostics: overlapping species and migration; P(sel B \| true A) kept apart from P(true A \| sel B), the latter with its composition | met with readings | `pid.migration` and `pid.purity`; the tool keeps them inside and outside support; job 7627284 migration PASS; control `purity-as-efficiency` fails only `migration`. Readings: 8,942 tracks, 722 outside support, P(sel b \| true b) 0.9826, P(true b \| sel b) 0.9823 and 0.7445 at the two compositions | Development readings, no working-point quality claim |
| W6 and R20: A19, count or threshold only, no fabricated per-event energy | met | The counts product: `capability` counting, observables `count`, `per_event_energy` false, `count_model.inferred_from` null; zero kept, absent with no count, per-channel valid exposure (`test_timing_counts`, job 7627284) | |
| R20: A20 to A24 at runtime if covered, else a recorded gap | gap | `t10_stage2.py counts` record `gaps` (A20 to A24); `t10-timing-stage-plan.md` section 6.1 | Not covered by this class (see Summary); the T06 contract parts stand |
| Native timing backend | open | The stage plan (section 1) records the timing binding as a development binding, as U12 A; no recorded decision names timing | The user's word: extend U12 A to timing (then a gap) or name a backend |
| Failing check first (stage 1, stage 2 and its fix round) | met with readings | Red logs with file hashes: `jobs/t10-timing/red/`, `jobs/t10-stage2/red/`, `jobs/t10-stage2/red-r1/` (red-2 on the final test files against stubs, I5); green logs beside them | Some first reds are import or stub errors. Tests that pass at red test existing behaviour (stage 1's chain, T06's CAI-T06-3) and are named in the reports. Round 0's post-red renames are disclosed in `jobs/t10-stage2/REPORT.md` |

## Outside the obligations, recorded for the next reader

- **Interface change in stage 2.** `event_time.tof()` needs the event's hit records for an internal start. Stage 1's job of record ran
  the earlier signature; its CAI check was rerun on the new one in job 7627284.
- **K12.** No cost target is set for T10. The jobs' times are recorded above.
- **Reproducibility.** The stage 1 repeat was byte-equal (job 7593003). The replay's comparator values were bit-identical across attempts
  2 and 3. These are readings for these runs, not a general claim.
