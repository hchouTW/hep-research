# Part II — Methods

> This part is the **scientific method module** of the reconstruction (layer A): physical semantics, conditions, uncertainties, association and counting, subdetector routing, iterative calibration, selection bias, simulation to data, validation discipline, partitioning and scope, representative cases, and the division of labor with profiles.
> **Read the Core part first**; read the sections of this part on demand according to the “Load” column of the Core §5.3 trigger matrix. Its normative force is the same as that of the other three parts.

## 0. Purpose of this part

- During research execution, this part is the main scientific basis; T3 claims (Core §5.1) almost always need Methods §1 and Methods §2.
- This part does not contain execution and control details (those are in the Control part and the Delivery part). Concise definitions of “checked artifact”, “effective validation identity”, “derivation state”, “target and achieved tier” and “human approval” are in Core §3.1; the formal definitions are in the Control part.
- For review status, see Core §0.5.
- Values, algorithms and parameters of specific experiments are not in this part; they come from the experiment profile or from project sources (Methods §5).

---

## 1. Method layer A: scientific method contract

Supplement as needed from existing topic modules and profiles; do not build a new general-purpose event class or graph engine.

### 1.1 Summary table of method semantics

| Method semantics | Must be recorded when needed | Corresponding failure mode |
|---|---|---|
| Target state/assumptions | physical quantity, unit, sign, reference surface, particle/topology hypothesis | rigidity taken as momentum; entry and exit states mixed up |
| Object–observation relations | object scope; legitimate many-to-many/shared/split/competing candidates and their definitions | the same deposit counted twice in the energy; the number of candidates taken as the number of particles |
| Passes and information consumption | order, whom a mask/removal applies to, whether it can be recovered and on what basis | an earlier pass wrongly removes later signal, yet only the successful subsample is validated |
| Calibration dependencies | sample/period, derivation method, physics assumptions, reference and shared uncertainties | the calibration absorbs the target signal; mutual consistency mistaken for an absolute scale |
| Redoable scope of the data | retained level per branch, selection/conditions, availability of raw/reference | after cache invalidation, pretending that raw data that no longer exist can be rerun |

- A sound source and sound assumptions do not mean that all of its parameters are portable. CMS-style signal fusion, ATLAS-style merged clusters, AMS-style rigidity/β and the LArTPC t0 each need different essential information; what is shared is the discipline of decisions and evidence.
- **After conditions or methods change, first do a redoability check, then schedule**; the result falls into four classes: reconstructable / downstream recomputation only / needs additional raw or reference / unrecoverable. The last two classes block the corresponding claims but do not block other independent work. Keeping raw data does not guarantee that the environment and models are reproducible either. **Events not recorded by the trigger are “unrecoverable”.**

### 1.2 Conditions are observation context, not just a version label

> Basis: the CMS [IOV explanation](https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideIOVAndIOVMetaDataInANutshell) distinguishes the interval of validity from the payload. Only that concept is adopted; its historical storage implementation is not treated as a current API.

For steps affected by conditions, the adapter must be able to trace: the semantics of the observation key (run/time/other experiment-defined key); the identity and validity range of the payload actually resolved; overrides and the necessary resolution rules.

- Referencing them through the existing framework's receipt/manifest is sufficient; copying constants per event is not required.
- When a mutable service is used, keep a snapshot/digest or equivalent evidence sufficient to re-find the content resolved at the time; **a mutable alias alone does not support reliable reuse**.
- A chunk spanning IOVs must not by default share the first or the last set of conditions; when different periods are processed concurrently or rerun out of order, context and cache must not contaminate each other. How boundaries are included and the time base are defined by the experiment.
- If the conditions are a continuous function within a timeframe, keep their model and evaluation method; do not force them into constant IOVs.
- Missing conditions/ambiguous overlaps: first resolve them according to the effective project rules; **must not silently fall back to "latest"**; block only the affected results.
- What this design adds is only **resolution and applicability evidence**; the existing conditions service remains the sole authority.
- **Resolution time**: what is fixed before execution is the global tag/resolution rules (part of the declared computational identity); many frameworks resolve only when they reach an IOV boundary during execution, so the actual resolution result is supplied after execution by the receipt (G6) and verified before reuse.

**Simulation settings are conditions too**: geometry/material version, physics list, generator and tune, digitization/noise model, pileup settings, etc., are recorded the same way.
- The context of run-dependent MC may be a luminosity-weighted **mixture distribution**; record the mapping and the weights.
- Pileup reweighting is a correction weight with an uncertainty, not conditions in itself.
- A data/MC comparison must state how the condition contexts of the two sides correspond; where they do not correspond, state the differences explicitly and do not assume comparability.

### 1.3 Uncertainties, constraints and physical quantities propagate together

> Basis: the [track uncertainty transport study](https://arxiv.org/html/2403.16720v2) demonstrates checks of Jacobians and covariances between coordinate frames and lists the limitations of the material and linear approximations; the [official Ceres documentation](https://ceres-solver.readthedocs.io/latest/nnls_covariance.html) explains residual weighting and rank issues. Both support the discipline below, but they do not prove that the uncertainties of an arbitrary reconstructor are calibrated.

Record, according to how the result is used: parameter order, units/coordinate basis/surface, the uncertainty or likelihood representation, which calibration constants/particle hypotheses/constraints it is conditional on, and how shared sources are handled. Covariances, asymmetric intervals, samples, mixture models or other suitable representations may be used; no new global schema is imposed.

- **Correlations:** When combining multiple subdetectors or derived physical quantities, correlations caused by shared tracks, clocks, alignment and calibration must not be assumed to be zero by default; when they are unknown, do a well-founded sensitivity analysis or state the limitation explicitly; do not invent correlation coefficients.
- **Coordinate transformations:** When transforming coordinates or surfaces, transform the uncertainties and correlation terms at the same time; process noise and shared systematics must not be added twice. Local linear propagation is used only within its domain of validity; strong nonlinearity, tails or multimodality need numerical/distribution checks.
- **Matrix sanity:** Dimension, symmetry, finiteness and, where admissible, positive semi-definiteness are only basic checks; with constraints, a matrix can legitimately be singular. When inversion fails, **must not uniformly “fix” it by adding jitter**; first determine whether the cause is an unidentifiable degree of freedom, the coordinates or a numerical problem. A zero-eigenvalue direction of a pseudo-inverse does not mean that the uncertainty of that physical degree of freedom is zero.
- **Keep the two kinds of uncertainty separate:** per-object fit uncertainties under fixed conditions vs. calibration uncertainties shared across events; the latter can be kept as external nuisances/variations and need not be packed into each object's small matrix. Scientific uncertainty estimation and combined inference go to `hep-statistics`.

Small residuals, a converged fit or an invertible covariance are not enough to prove the absolute scale or identifiability. When only central values are delivered, the limitation must be stated explicitly; **a deliverable that requires an uncertainty/precision claim cannot be completed by omitting the uncertainties**.

### 1.4 Keep association and counting separate

> Basis: ALICE's official [track-to-collision documentation](https://aliceo2group.github.io/analysis-framework/docs/advanced-specifics/trackToCollAssoc.html) allows a track to be associated with multiple time-compatible collisions and distinguishes box-like from Gaussian-like time uncertainties. The window width in that document must not be taken unconditionally as a standard deviation, and “compatible” must not be taken as the unique true assignment.

- Distinguish four layers: measurement/candidate/association/selected object.
- An association must state clearly which kind it is: hard assignment, a set of compatible candidates, normalized probabilities, or an uncalibrated score. **A score does not automatically carry probability semantics** (the same holds for pile-up mitigation weights).
- With hard assignment: record the rule, and how ambiguity enters the performance evaluation.
- When multiple candidates are kept: downstream yield/energy/event statistics need an explicit deduplication, marginalization over hypotheses, or another applicable rule.
- The number of table rows from duplicate associations ≠ the number of particles; but genuine sharing or splitting must not be crudely deduplicated either.
- Implement this through existing data tables/framework mappings; do not build a separate general-purpose graph.

### 1.5 Method routing by subdetector and physical quantity

This is a general **list of planning questions** put forward by the overall v8 design; it is not a specification table for each experiment, nor does it imply that the plugin already has a full set of executable algorithms. Load only the rows the task needs; the concrete methods are determined by the data, the profile and the sources.

| Observation/subsystem | Possible target quantities | Questions to resolve before choosing a method | Main handover |
|---|---|---|---|
| Trigger/online selection | trigger decision, online objects, prescale | irreversible sampling; trigger efficiency must be measured with orthogonal/unbiased triggers, tag-and-probe or other data-driven methods, and their premises (correlations between triggers, tag bias, background subtraction) must be recorded and checked; differences between online and offline conditions/algorithms; trigger bias of the calibration samples | detector + measurement |
| Waveform/front-end and photosensor readout | amplitude, charge, time, pulse | baseline, saturation, pileup, noise, readout window; whether pulses can be separated | detector front end/computing |
| Dedicated calibration runs | pedestal, gain, laser/source response | non-event inputs; keyed by time or run; IOV correspondence with physics runs | detector/calibration |
| Position measurement/tracking | hits, trajectory, momentum or rigidity | geometry/field/material, surface, charge hypothesis, pattern ambiguity; alignment weak modes | tracking/alignment |
| Vertex/decay topology | vertex, direction, decay length | shared tracks, primary selection, constraints and error propagation | detector + measurement/statistics |
| Electromagnetic/hadronic calorimetry | deposit, cluster, energy, direction | response domain, leakage, nonlinearity, sharing, track matching | calorimetry/data-MC |
| Composite objects (jets, MET, etc.) | object scale and resolution | shared uncertainties of the constituent objects; pile-up mitigation; data-driven derivation of the in-situ scale | detector + statistics |
| TOF/precision timing | time, path length, β | clock/t0, path- and track-related uncertainties, compatible multiple solutions | timing/PID |
| RICH/Cherenkov (including water Cherenkov rings and vertex fitting) | angle, β, charge/PID, vertex | radiator/optics/track hypothesis, background light, ring ambiguity | PID/calibration |
| dE/dx/TRD and other PID | energy-loss features, LLR/species | sample conditions, shared path/momentum information, calibration domain of the score | PID; learned methods go to ML |
| Muon/outer-detector matching | segment, global track, muon candidate | material, matching, non-prompt hypothesis, fake matches | tracking/PID |
| TPC/LArTPC/continuous readout | drift position, 3D topology, charge/energy | t0 is a time offset **per interaction**: per event or per trigger only when a single interaction occupies the drift window; with continuous readout, or with cosmic or beam pileup inside the drift window, t0 is determined **per track or per interaction** (light-signal matching, cathode/anode crossings, an external trigger matched to the track), and one trigger t0 must not be applied to out-of-time tracks — a track whose own t0 is not determined is treated as having no t0; the drift velocity (electric field, temperature) is measured separately, and its uncertainty produces a scale bias in the drift coordinate proportional to distance; attenuation from electron lifetime/purity; recombination (LAr); gain; distortion; time/plane matching; frame boundaries. **Without t0, do not report a unique absolute drift position, and do not apply attenuation corrections that depend on drift time: mark charge/energy as uncorrected, or do not use them calorimetrically** | tracking/signal/calibration |
| Scintillation/rare-event/calorimetric thermal readout | pulse, energy, position, topology/PID | signal formation, quenching or thermal response model, low-threshold selection domain | detector; where no corresponding topic module exists, state the gap explicitly |
| Air-shower/radio and other arrays | arrival direction, energy proxy, shower parameters | geometry/timing, medium and model dependence, trigger/exposure | detector + theory/measurement |
| Neutrino energy reconstruction | incident energy, topology | dependence on interaction models; invisible parts of the final state | detector + theory |
| Learned (ML/GNN) end-to-end reconstruction | any target quantity | the model version is part of the conditions; differences between the training domain and the application domain (Methods §1.8) | ML + detector |
| Exposure/luminosity/live time | normalization quantities | consistency with the numerator exclusions; time of DQ certification | measurement |
| Cross-subsystem/event combination | mass, particle sets, event-level quantities | ownership, compatibility hypotheses, shared uncertainties, missing information | detector; inference goes to statistics |

A reconstruction target cannot always be determined uniquely. **Reporting the identifiable part, the external constraints relied upon, or a feasibility conclusion is better than automatically filling in an unvalidated prior to manufacture a unique value.** Authorized, well-founded constraints may be used, but their conditional nature must be preserved.

### 1.6 Iterative steps: calibration ↔ reconstruction loops

**Scope:** loops such as calibration/alignment, in which constants are derived from reconstruction results and then fed back into the reconstruction. The number of iterations in iterative unfolding is a regularization parameter that is deliberately not run to convergence; it goes to `hep-statistics`, and this section does not apply to it.

- **Each round is one or more steps in the task contract** (a round may be partitioned, e.g. per-chunk reconstruction with the previous round's constants and a global solve for this round's constants); the steps of the same loop belong to the same family and are labeled with their round number; the computational identity therefore includes the owning step (including the round) and the inputs actually consumed (Control §4.2). The output is treated as a new conditions payload, with a producer edge.
- **The number of rounds is fixed in the first contract**: the family declares the final round and (by check digest) its **convergence check** and **unconstrained-mode check**; the rounds are exactly 1…final round, each with at least one step, and **chained**: a step consumes in-family steps only of its own or the previous round, and every round after the first consumes the previous one (Control §1.1). Every step of a round after the first consumes the previous round, directly or through steps of its own round; only the final round's single checked step, the family's **final step**, is checked; its required checks must include both of these checks, and neither of them may be not-applicable — format validation rejects a contract that lacks either one. There is no “maximum number of rounds”: the final round is the cap.
- **Changing the number of rounds requires human approval** (Control §1.2), whether adding a round or removing one, so that the passing round cannot be picked after seeing validation results. If the loop has still not converged at the final round, it is held (next item); to run more, attach the convergence record and ask a human to approve a contract that adds rounds: that contract makes the old final step an unchecked member, gives the new final step the two checks and points out-of-loop consumers at it, and the old non-convergence stays in the history of the dependency chain (Control §4.7). If it converges early, it may either run on to the final round anyway, or attach the convergence record and ask a human to approve shortening.
- Members other than the final step (intermediate rounds, and the unchecked members of the final round) are not checked artifacts and are exempt from checks; their derivation label is `iteration_internal`, and `superseded_by_iteration` once a later round has produced output. These labels do not invalidate **consumers inside the loop** (same or next round); **steps outside the loop must consume only the final step** (the derivation judges any other member stale, Control §4.2), because the other members have not been fully validated.
- When the criteria change with approval, results go back to “awaiting checks” and need not be recomputed; only changes to the program, the environment, task-bound conditions, the upstream list or the consumed upstream artifacts invalidate results (Control §4.7).
- The convergence criteria and the number of rounds are fixed before starting and are bounded by the task's overall limits; non-convergence is reported as non-convergence (the convergence check of the final round is fail and the derivation is held), and the last round is not passed off as the result. Adjusting the iteration plan after seeing the convergence behavior must be recorded; loosening the convergence criteria requires human approval, and **a “not converged” under the original criteria must not be rewritten as “converged”**.
- **Convergence only indicates numerical stability; it does not constitute scientific validation.**
- **Every iterative calibration — and every single-pass alignment or intercalibration solve, which has the same modes — must list its unconstrained global modes and the external information that constrains them**; for a single-pass solve the mode check is a required check of that step. Alignment weak modes (global deformations such as twist, sagitta and telescope that leave χ² nearly unchanged) are the most typical example; calorimeter intercalibration has modes of the same kind: φ-symmetry constrains only the relative constants of the φ positions within the same η ring — it **assumes** that the energy flow is uniform in φ, so the relative scale between η rings and the global scale are unconstrained and must be fixed by external information (π⁰/η mass, E/p, Z→ee); genuine φ dependence (material, magnetic field, dead regions) is absorbed into the constants, which is a bias caused by the method assumption and must be evaluated as a systematic uncertainty, not as a free mode. π⁰ intercalibration constrains the relative scale of neighboring crystals, but transferring the absolute scale to the high-energy region needs separate validation (nonlinearity). Looking at residuals with the other half of tracks of the same kind cannot detect weak modes. It is required to:
  - list the possible unconstrained modes and the information that constrains them (cosmics, overlaps, vertex/mass constraints, external scale, etc.);
  - validate with observables sensitive to these modes (e.g. the variation of a resonance mass with η/φ/charge, E/p);
  - sample splitting is downgraded to optional.
- If the derivation used a known value of the target physical quantity (e.g. a known mass), that quantity can no longer serve as an independent validation of this calibration.
- Which round's constants a downstream artifact depends on must be traceable.

### 1.7 Selection bias and exposure

- **Trigger/online:** record the trigger conditions, prescales, and differences between online and offline conditions; measure the trigger efficiency with data-driven methods, with an uncertainty; samples used for calibration must state their trigger bias.
- **DQ/good-run exclusions come in two kinds:**
  - **Exclusions based on detector state** (not depending on the measured quantity) may be certified after data taking, but the criteria and their version must be recorded, and **the exposure must be reduced accordingly at the same time**;
  - **Result-based exclusions** are always forbidden (Core §0.4 item 8).
- When a deliverable includes a flux, cross-section or rate, every exclusion in the numerator must have a corresponding treatment in the denominator, with the following distinguished:
  - **Time-based exclusions** (runs, lumi sections, live-time intervals) are subtracted from the exposure;
  - **Event-based selections** go into efficiency × acceptance;
  - **Exclusions that depend both on time and on the measured quantity** (e.g. a geomagnetic cutoff selection: the exposure time T(R) per rigidity bin): choose one treatment — fold it into the per-bin exposure, or treat it as a per-bin efficiency — and use it consistently in the numerator and the denominator.
  None of the three may be subtracted twice or left out.
- DQ criteria “based on detector state” must be defined **without reference to the estimand distribution**. Flags derived from reconstruction-quality monitoring may be correlated with the estimand (e.g. alignment quality and high rigidity); when they are used, this must be declared and its impact evaluated.

### 1.8 Simulation to data

- A check whose reference is MC truth by default **supports only “performance in simulation”**.
- To claim performance on data **from MC-derived performance**, a separate data/MC comparison (tag-and-probe, standard candles, etc.) is required, giving a scale factor and its uncertainty. Performance measured **directly on data** by a data-driven method (e.g. a tag-and-probe efficiency in data) needs no scale factor; the method's premises are recorded and checked (Methods §1.5), and its confirmation follows Methods §2.1.
- ML reconstruction must list the training domain and the application domain explicitly and check the difference between them (domain shift); the model version is recorded as conditions.

---

## 2. Method layer A: scientific validation and automatic-repair discipline

### 2.1 Definitions of sample role, exposure and confirmation

**A T3 deliverable always records**: the purpose of each sample/control; the grouping basis (event/run/period, etc.); which results have already been used to choose methods, cuts, calibrations, hyperparameters or simulation tuning. Sample roles are written into the task contract (Control §1.1); a registered role cannot be changed unilaterally, and changing it requires human approval (Control §1.2). Existing task/ML/check data may be referenced; no new central database is needed.

**Purposes and exposure:**

| Purpose | Meaning | Does it count as exposure |
|---|---|---|
| **Data-driven derived quantity** | corrections, constants or measured values derived from data (in-situ scale, tag-and-probe efficiency, a flux that can only use the full dataset, etc.), with their uncertainties propagated | if the derivation procedure is declared before looking at **the derived value and the consistency metrics the claim relies on**, it **does not count as exposure**; this is a legitimate standard practice (details below) |
| **Tuning/model selection** | choosing methods, cuts or hyperparameters based on results, or **tuning the simulation** with data (material, noise, shower parameters, etc.) | the samples used are thereby exposed; data/MC validation must use observables or samples not used in the tuning |
| **Confirmation** | tests used to support a confirmatory claim; there are two types, see the table below | must be unexposed |

**Details of data-driven derivation:**

- “Results” means **the derived value itself** and the consistency metrics the claim relies on; quality information such as fit quality, convergence and bin statistics may be looked at.
- A **conditional procedure** may be declared in advance, e.g. “if χ²/ndf > a, switch to functional form b”; the decision must be based on quality information, not on the derived value.
- **Value blinding** (hiding an offset or a scale) may optionally be used, so that the derived value is not seen until the procedure is finalized.
- Any change to the procedure after seeing the derived value must be recorded; the difference before and after the change is taken as a systematic or disclosed in the report. Changing the procedure according to whether the derived value “looks good” is the bias this rule guards against. **Such a change makes the quantity tuned**: the data used are exposed, the quantity loses the status of an untuned quantity derived by a pre-declared procedure (the third bullet under “The claim type determines …” below, Core §7.2), and its confirmation follows the rules for tuned quantities; taking the before/after difference as a systematic does not remove this selection effect.

**The two types of confirmation:**

| Type | What it guards against | What it requires | Typical examples |
|---|---|---|---|
| **Holdout confirmation** | optimization bias caused by model selection and tuning | a statistically fresh, identically distributed, **unexposed** sample | an ML held-out test set; an independent sample of the same kind of MC; a data subsample set aside in advance |
| **Method-independent confirmation** | bias caused by shared systematics | a test that is **methodologically independent** of the derivation path | different observables, a different resonance, an orthogonal control region, cross-species validation |

**The claim type determines which type is needed:**

- “Performance in simulation” (Methods §1.8) and ML generalization: holdout confirmation is sufficient.
- Absolute-scale or performance claims on data: method-independent confirmation is required. Replacing it with a complete systematic evaluation amounts to dropping the confirmation requirement and requires human approval (Control §1.1); without approval, the deliverable is reported as partially complete, and the report states explicitly “not independently confirmed”.
- Threshold validation may apply the threshold **directly to an untuned data-driven quantity derived by a procedure declared in advance**: such a quantity needs no holdout confirmation (it was not tuned); if it has been tuned, an unexposed holdout confirmation is required. **In both cases, when the claim is an absolute-scale or performance claim on data, the method-independent confirmation of the previous bullet is still required** (shared systematics bias a threshold decision exactly as they bias the value); replacing it needs the same human approval.

Other rules:

- **Statistical independence ≠ systematic independence.** Splitting the same run into two halves gives statistically independent halves that can serve for holdout confirmation, but they share alignment, MC and calibration and cannot serve as method-independent confirmation.
- If the original confirmation sample has already been involved in a repair or in model selection, **it can no longer serve as confirmation**. Switch to suitable unexposed data, or use a method that correctly handles the selection bias (e.g. nested cross-validation, selection-adjusted inference), to be judged by `hep-statistics`; if neither is possible, limit the conclusion to T3-E. Keeping the history and the criteria versions **does not restore independence that has been lost**.

### 2.2 Three kinds of criteria change, with different decisions

| Change type | What the Agent may do | How evidence is handled |
|---|---|---|
| Fixing check code so that it conforms to an **unchanged, well-founded definition** (e.g. a unit bug) | fix the new version of the check and run positive and negative tests; **a contract that replaces the old check with the new check requires human approval**, and the Agent attaches the positive/negative test receipts when asking for approval (Control §6). Before approval, the new check may be added first (add-only, takes effect automatically), but failures of the old check still make the artifact held | the old failures are kept in the history; after approval, the corresponding artifacts are revalidated with the new check (revalidation only, Control §4.7) |
| Switching to another reconstruction method or algorithm (code, parameters, upstream) | compare within a bounded plan/policy without asking at each step; this is a change to a content field, which takes effect automatically but invalidates the corresponding artifacts | update the method and the affected dependencies; handle the tuning exposure; rebuild the required evidence; the required checks are not reduced as a result |
| Changing the estimand, a required scientific claim or the acceptance standard | propose it under existing explicit authorization; the corresponding change in the contract requires human approval | failures of the original claim under the original criteria are not rewritten; the new claim has its own scope and evidence |

**Forbidden**: drawing more seeds **and reporting only the passing ones** (estimating the variance from multiple seeds is legitimate practice; this covers MC regeneration, bootstrap and ML training seeds, and the aggregation method must be declared in advance), repeatedly looking at the same control until a passing option is found, and removing failed cases from the denominator — as ways of obtaining the originally claimed performance.

### 2.3 Roles, types and four-valued results of checks

**Roles:**
- **Closure/internal consistency**: a self-consistency check on the samples used in the derivation; it is a necessary condition (it can catch bugs), but it does not constitute confirmation.
- **Independent confirmation**: see the definition in Methods §2.1.

**Types:**
- **Threshold validation**: a requirement with an acceptance threshold (“is the resolution better than X”).
- **Performance estimate**: an estimate without a threshold (“what is the resolution”). It is delivered as “value ± uncertainty”, together with the four-valued results of validity checks (closure, pull, stability); **must not fabricate a threshold in order to apply one**.

**Four-valued result:** pass/fail/inconclusive/not-applicable, with a reason. This is a check result, not a new artifact source status.

- When the reference does not apply, the control does not cover the phase space, the statistical sensitivity was determined **before execution** to be insufficient (the power design of Methods §2.4 is not met), or — for **threshold validation** — the interval straddles the decision boundary, the result **must** be judged inconclusive (the corresponding claim is not established); exit 0 must not be treated as a physics pass. A fail whose interval lies entirely outside the acceptance region stays fail even when power is low (Methods §2.4). Validity checks of performance estimates and data-driven measurements are decided instead by their frozen tolerance rule (Methods §2.4: pass, pass with a transferred systematic, or fail); for them inconclusive arises only from the conditions above other than the straddling interval; a check whose own precision is too coarse is handled by the non-closure rule of the Methods §2.4 table (the systematic is set to at least the check's precision), not by inconclusive.
- Observing zero tail events does not automatically prove the tail negligible; when 0 are observed in N events, report a 95% CL upper limit of about 3/N (rule of three), rather than only writing “none seen”.
- When a required scientific claim is inconclusive, **it cannot satisfy the acceptance of that claim**; but this does not necessarily prevent another, completed code deliverable, or a feasibility conclusion allowed by the original contract.
- A T3-C claim spanning periods includes by default validity checks for time stability/aging.

### 2.4 Freeze the criteria first; controlled access to confirmation samples

**Freeze time:** every criterion, tolerance (k, δ_phys) and decision rule is frozen before the first result it will judge is seen, on any sample (including closure, pull and stability results on simulation or control samples); and the whole record is frozen before **the results the claim relies on** are obtained for the first time — the results on the confirmation sample or, when there is no confirmation sample, the derived value on data. The freeze record (DEC-03) always includes:

1. the criteria version, the check code digest, and the **effective validation identity** of this task (Control §4.4);
2. the **complete list of confirmation samples and controls**, whether each confirmation sample is of the holdout or the method-independent type (Methods §2.1; recorded in the freeze fact so that the derivation can check a required method-independent confirmation, Control §2, Control §4.4), and a commitment to report the results of all confirmation evaluations (must not report only the passing ones);
3. the **feasibility determination for independent confirmation, with reasons**: if it is feasible, it must be performed and reported; if it is determined infeasible, state under what conditions it would be feasible, and the report must state explicitly “the claim is supported only by closure, cross-checks and systematics, and has not been independently confirmed”. This determination is made and recorded by the main Agent, but it **does not remove the confirmation requirement in the contract**: the deliverable still requires confirmation and is therefore reported as partially complete; completing it with unconfirmed results requires human approval to remove the confirmation requirement (Control §1.1). **Feasibility must not be redetermined after seeing the results.**
4. the **multiple-testing treatment**, stating three things (to be judged by `hep-statistics`):
   - the error type controlled: false pass, or false fail;
   - the combination logic: pass only if all pass, fail if any one does not conform, or a global statistic;
   - the treatment of correlations: when bins share systematics, use methods such as a global χ² with the full covariance.

   Note: whether a multiple-testing correction is needed depends on **which outcome of each bin's test constitutes rejection of the null hypothesis**, not on the name of the combination rule — with only pass/fail, “pass only if all bins pass” and “fail if any one does not conform” are the same rule.
   - When each bin's **pass is the rejection of the null hypothesis “non-compliant”** (e.g. the interval lies entirely inside the acceptance region), pass-only-if-all-pass is an intersection-union test; deciding each bin at α already controls false passes, and no correction is needed.
   - When each bin's **fail is the rejection of the null hypothesis “compatible”** (a compatibility test), controlling false fails requires per-bin α/n (or Šidák), or a single global test with the full covariance instead. Example: if each of 20 mutually independent bins gets a 95% CL compatibility test and fail is declared if any one fails, even a correct method has a probability of about 1 − 0.95²⁰ ≈ 64% that at least one bin fails.
   - How inconclusive is counted follows the rule declared at freeze (usually it is treated as not passed).
   FDR is usually not a suitable error rate for claims of the “overall consistent” or “all pass” kind.
5. **cross-round error control**, declared at freeze (Core §7.1). At freeze, a **ceiling on the overall false-pass rate** across all rounds of the claim is frozen (by default α for threshold validation and p_total = 0.2 for compatibility-type confirmations, or other values with a stated reason); a confirmation round whose use would let the implied overall rate exceed the ceiling cannot support T3-C (the claim stops at T3-E and is reported as partial completion). Which rule bounds the rate depends, as in item 4, on **which outcome of a confirmation round rejects a null hypothesis**:
   - **Pass rejects “non-compliant”** (threshold validation: interval entirely inside the acceptance region): α is the per-round false-pass rate. One of two options: (a) α allocation across rounds, Σᵣ αᵣ ≤ α, where round r's decision rule uses the interval level 1 − αᵣ (one-sided) and its power design is evaluated at that level — an allocation the frozen decision rule does not implement does not count; (b) a cap R on the number of rounds, with the implied overall false-pass rate written in the report: **when every round uses a statistically independent fresh sample**, it is 1 − (1 − α)ᴿ (the worst case, when the method sits at the threshold boundary; for α = 0.025, R = 2, 3, 5 give about 0.049, 0.073, 0.119 respectively); **when any round is a re-evaluation on the same sample**, the rounds are not independent and only the Bonferroni upper bound min(1, Rα) can be reported. The two are not equivalent: only (a) controls the overall false-pass rate at α; under (b) a round may be used only while the implied rate stays within the frozen ceiling.
   - **The method-independent confirmation of a threshold claim on data** is decided like the threshold itself (the independent method's interval entirely inside the acceptance region → pass), so it belongs to the first category, with its own rounds counted against the same ceiling; the method-independent agreement of a performance estimate belongs to the next one.
   - **Pass is the failure to reject “compatible”** (compatibility-type confirmations: validity checks under the tolerance rule — closure, pull, stability — and method-independent agreement for performance estimates and data-driven measurements): α (or the tolerance) is the false-**fail** rate, and the per-round false-pass rate is the pass probability p under the frozen unfavourable alternative of the power design (a bias at the size of the claimed total uncertainty). **Splitting α across rounds is forbidden here**, because a smaller αᵣ makes a later round easier to pass: every round uses the frozen per-round test unchanged or tightened (the same or a smaller tolerance, never widened). The analogue of (a) is a split of the frozen budget p_total as per-round pass probabilities under the unfavourable alternative, Σᵣ pᵣ ≤ p_total, each pᵣ reached by the power design of that round (a larger sample or a tighter test); a round with no remaining budget cannot confirm. The report gives the allocation and the implied overall rate (at most Σᵣ pᵣ).
   - When returning to freeze after a failed confirmation (Core §7.1), unexposed confirmation samples may be added in a new freeze record, but the error control is **not reset**: under (a) only α not yet allocated may be used, and under (b) and for compatibility-type confirmations the rounds keep being counted; adding samples does not open new α and does not widen the per-round test.
   - Re-evaluating the same artifact on the same sample with a corrected check (the post-hoc correction rule below) also counts as a round.

Additionally frozen, by check type:

| Check type | Additionally frozen content |
|---|---|
| **Threshold validation** (VAL-04) | the threshold and its basis; the **interval form** (one-sided or two-sided; using a two-sided 95% interval for a one-sided threshold is equivalent to 97.5% one-sided), the method of incorporating systematics (quadrature, profile nuisance, envelope), the treatment of the uncertainty of the threshold itself; the **decision rule**: interval entirely inside the acceptance region → pass; entirely outside the acceptance region → fail; straddling the boundary → inconclusive; and the **a priori power design** (see below) |
| **Performance estimate**/**data-driven measurement** | the measurement method and the derivation procedure; the **tolerances** of the validity checks (closure, pull, stability, time stability), written as \|deviation\| < max(k·σ_stat, δ_phys), with both k and δ_phys frozen, and **the tolerance max(k·σ_stat, δ_phys) must not exceed the claimed total uncertainty**; the precision of the check itself must be smaller than the claimed uncertainty, and where this cannot be achieved the non-closure systematic is taken to be at least the precision of the check; **on pass, an observed deviation that is incompatible with zero must still be converted into a systematic according to the frozen rule** (it must not be absorbed by the tolerance), in which case the result is pass with the transferred amount attached; only a deviation beyond the absorbable range is fail |

**Power is an a priori design requirement, not a post-hoc condition:**

- At freeze, declare an **alternative value away from the threshold boundary** (e.g. the true value equals the expected performance, or threshold ∓ δ), and estimate with Asimov or toys the expected interval half-width and the probabilities of judging pass and fail under that alternative. Power evaluated at the threshold boundary is essentially equal to α and cannot serve as a design target.
- **The design target is frozen as numbers**: by default, P(pass) ≥ 0.8 under the declared favourable alternative, and — for compatibility-type checks — P(pass) ≤ 0.2 under the declared unfavourable alternative (a bias at the size of the claimed total uncertainty); other values may be frozen with a stated reason. The requirement is met when the estimates of the previous item reach the frozen target, **evaluated on the combined decision rule actually used** (after any multiplicity adjustment of item 4: per-bin α/n, Šidák or a global χ²), not per bin before adjustment.
- If the design requirement is not met, mark the check **before execution** as “at most inconclusive or fail”, or enlarge the sample.
- After execution, decide threshold validations only with the three-region rule (validity checks under tolerance with their frozen tolerance rule); **a fail in which the interval lies entirely outside the acceptance region is not changed because of insufficient power.** Post-hoc observed power must not be computed to change the decision.

Rules:

- **If the threshold of a threshold validation has no basis, the check cannot be frozen**, and the corresponding claim is blocked before freeze; a marginal failure must not afterwards be reclassified as inconclusive on the grounds that “the threshold has no basis”. A performance estimate needs no threshold and is not blocked by this rule.
- Before freeze, only the metadata of confirmation samples may be viewed; viewing their content is recorded as exposure.
- A confirmation sample may be read only by a check attempt; at admission there must be a freeze record that **predates it** and includes that sample; for each confirmation sample, the sequence number of “the freeze record that included it” governs (Control §4.4, Control §5.1). For the practice during the transition period, see Core §5.4.
- **A confirmation sample can confirm only once**: once a confirmation result for some artifact exists on that sample, **another artifact** (e.g. a new artifact after the reconstruction code is modified) cannot be confirmed on the same sample and must use another, unused sample from the freeze list (Core §7.1). Multiple required checks of the same artifact may share a sample; re-evaluating **the same artifact** on the same sample with a corrected check follows the “post-hoc correction” rule below.
- Confirmation samples for T3-C are accessed only through the attested path; known bypass access is treated as exposure.
- **Limitation (must be stated explicitly in the completion report):** reads by ad-hoc commands cannot be detected mechanically; the rules above can only prove that “access through the controlled path” happened in the correct order.
- Changes to the criteria after freeze are handled according to Methods §2.2; a threshold must not be loosened in the name of “fixing a bug”.
- **Correcting check code after seeing confirmation results:**
  1. the results both before and after the correction **must be reported**;
  2. the reason for the correction must be demonstrated by positive and negative tests that do not depend on the confirmation data;
  3. the report states explicitly “confirmation results were corrected post hoc”. Only when **the trigger for the correction is unrelated to the confirmation results** can the new result for the same artifact on the same sample support T3-C: for example, the error was found by a test or review that was scheduled before the confirmation and is unrelated to its results. **If the error was found because someone went looking after the confirmation failed**, then even if the error is real and the fix is correct, the fix is result-triggered: the new result on the same sample supports at most T3-E, and T3-C must be reconfirmed on another, unused confirmation sample from the freeze list.
  4. Replacing the check itself requires human approval (Methods §2.2); approval is a necessary condition and does not restore the confirmatory force of a result-triggered correction.
- The number and the targets of confirmation evaluations are limited to the freeze list; evaluations outside the list can only be T3-E and are listed in the report.
- The check code itself needs positive and negative tests (able to make known-bad inputs fail); a check that can only pass does not constitute evidence.

For high-risk claims, following existing practice, a reviewer who did not take part in the writing may be asked to review the criteria or the check code; whether this is needed is decided by authorization and risk, not as a fixed process.

### 2.5 Check execution and provenance chain

A check is executed through layer B as an attempt and produces a receipt; a check result must reference the check code digest, the criteria digest, the target artifact digest and the check execution receipt (Delivery §1.1). Layer C accepts only check results that have a complete provenance chain and belong to the effective validation identity (Control §4.3). During the transition period, checks must also be executed through the runner (Core §5.4 item 2).

### 2.6 Blinding

When the project or the user has a blinding policy:

- Sample roles must mark the blinded/unblinded regions.
- Freezing the criteria is a necessary condition for unblinding; unblinding itself is left to a human decision according to existing rules (Core §6.3).
- Checks and plotting must not read the blinded region; this is checked at admission.
- During the transition period (Core §5.4) there is no admission check; the limitations section of the report must note that “the blinded region was not read” cannot be proven mechanically.

---

## 3. Partitioning and scope

### 3.1 Partitioning is part of the scientific method

> Basis: ALICE's [frame/readout boundary documentation](https://aliceo2group.github.io/analysis-framework/docs/analysis-tools/EventSelection.html) records missing boundary information, dependent selection rules and period differences — an instance of “a complete file can still have boundary effects”. Its cuts or the current `sel8` definition are not ported as general rules for other experiments.

First determine whether the unit of computation is: independent events, observations with a temporal/spatial neighborhood, state across frames, or a full-sample estimate. **A chunk is a scheduling unit and cannot automatically replace the physical unit.** The merge, equivalence and RNG rules below **apply to all partitioning** (including independent events); the neighborhood and state rules apply to non-independent units.

| Aspect | Requirement |
|---|---|
| Read range vs. output range | required halos/adjacent frames/preceding state can be reread; the output is determined by explicit ownership; legitimately overlapping input is not erroneous duplication. When the raw data already lack the boundary information, adding a halo afterwards cannot conjure it back |
| State recoverability | non-independent steps are handled with framework-supported state, ordering or a deterministic staging method. A full-sample calibration/normalization first builds a common estimate; **averaging the already-normalized results of the chunks must not be passed off as the whole**; if online updating is used, the version and the order are part of the method |
| Merge semantics | object identity, multiple candidates for the same observation, weights and the required statistics need corresponding merge rules; means/efficiencies/resolutions are not averaged directly without weights; where denominators differ or there are correlations, use the applicable statistical method |
| Equivalence defined by the target | compare partitioned vs. unpartitioned, chunk boundaries, input order and degree of parallelism under the same physical scope and conditions. Where applicable, use per-object agreement or well-founded numerical/distribution tolerances; bitwise identity is not always required; physically different sampling schemes cannot be required to give identical output |
| RNG has real semantics | record the actual generator, stream/substream and the observation mapping, or framework-equivalent information. Filling every worker with the same seed may duplicate streams; where results should be partition-invariant, a corresponding mapping or a validated alternative is needed. **Unknown invariance must not be silently reused across partitions via cache** |
| MC overlay reuse | reusing a pileup overlay library across chunks makes MC events correlated; record how it is reused, and do not assume that events are independent |

### 3.2 Scope, exposure accounting and grounds for scaling up

- Within an input range that can be inventoried, record the processing state with stable keys: **to do/done/excluded with reason/failed/unconfirmed**. The key may be a dataset/observation, or a time or lumi section. It can be expressed with existing manifests.
- When normalizing, the accounting also records the exposure, ensuring that numerator exclusions and denominator subtractions are consistent (Methods §1.7).
- **Many-to-many candidates cannot be used for event-completeness accounting.**
- An unbounded stream uses explicit window/watermark and late-data rules instead, and does not claim that the whole stream is complete.
- High efficiency on the completed subset cannot hide the failed subset. Predefined legitimate selections may be used, but their losses and their impact on the domain of validity/acceptance must be kept. Post-hoc exclusions based on detector state follow Methods §1.7; **failures must not be removed afterwards from the required denominator under the name of “bad events” on the basis of results.**
- Parts that cannot be inventoried limit the claims; do not fabricate totals.
- The **pilot** covers the necessary periods, occupancy, boundaries and difficult topologies according to the conditions that affect the method, not just easy-to-reconstruct events; the sampling strategy and statistical power are decided by the target, and a full Cartesian product is not imposed.
- **Before scaling up**, look at both the science checks and runtime/memory/I/O/output volume; the average time at low occupancy cannot be extrapolated linearly to guarantee the cost at high occupancy. Scale up in stages within the authorized limits, update the estimates and keep the in-flight commitments; unsupported hard caps must not be promised.

---

## 4. Representative reconstruction cases (for design acceptance)

> Design acceptance inspired by public methods; this is **not** a claim of having run on CMS/AMS or other collaboration data. Concrete values and configurations still require experiment/project sources.
> This section consists of **illustrative examples**; its norms are written in Methods §1–3, which take precedence.

### 4.1 AMS-style mass/rigidity study

- First list: p/signed rigidity, charge/mass hypothesis, β measurement domain, reference surface, calibration dependencies.
- Specify which independent reference supports the rigidity and β scales. If the calibration used a known mass/species or information from the same track, **the same mass peak cannot then independently validate that hypothesis**. **Cross-species validation** is allowed (e.g. deriving the scale with one nuclide and validating it with another).
- Note for planning: m = Z·R·√(1/β² − 1), hence δm/m ≈ γ²·δβ/β ⊕ δR/R (⊕ assumes that β and R are uncorrelated; when the TOF β uses the tracker path length, the two are correlated and are handled according to Methods §1.3); at high energy the reconstructable mass domain is limited mainly by the β resolution, and the pilot and the binning should be arranged accordingly. (Standard kinematic relation provided by the reviewer.)
- Evaluate scale, core, tails and the efficiency denominators by the method-relevant radiator, track pattern, period and β domain; do not always split on every dimension.
- Agreement between two β measurements supports only internal consistency and cannot exclude a shared bias; without an absolute reference, do not claim that the absolute mass scale is confirmed.

### 4.2 CMS-style signal fusion and multiple passes

- Record, with their semantics, the track/cluster relations, the assigned/shared/split information, and the effects of removal by passes.
- Compare local quantities and event-level quantities at a fixed working point and in common/newly added phase space.
- Failure cases involving shared clusters or masks from preceding passes **cannot be caught by file-hash checks alone**.

### 4.3 Online/compressed or LArTPC data

- First confirm the retained content, the trigger conditions and the conditions; after raw data are deleted, new hit finding/alignment may not be redoable; events not recorded by the trigger are unrecoverable.
- Without t0, do not report a unique absolute position.
- Control executed but lacking tail sensitivity → inconclusive; do not scale up automatically, and do not publish that performance claim.

### 4.4 Iterative alignment

- Each round is one or more steps in the contract (for example per-chunk track refits and a global alignment solve), with a family and a round number; the convergence criteria, the final round and the final step's convergence and weak-mode checks are fixed in advance; the derivation labels of the other members are `iteration_internal`/`superseded_by_iteration` (Methods §1.6, Control §4.6).
- Validation focuses on weak modes: list the possible weak modes and the constraining information, and test with observables sensitive to them; splitting the sample of tracks of the same kind is only an optional closure.
- Convergence only indicates numerical stability.
- After the constants are updated, artifacts that consumed the old constants are judged invalidated (not current) by the derivation, without separate marking; **when the contract deliberately pins the old constants, these artifacts remain current** (Control §4.7). Artifacts outside the loop may consume only the constants of the final step (Methods §1.6).

---

## 5. Division of labor between the general contract and experiment-specific profiles

| In the general spec (this document) | In the experiment profile/topic module |
|---|---|
| Semantic recording requirements, trigger conditions, evidence and completion rules | concrete geometry, field, material, conditions services and tag rules |
| The “questions to resolve” of subdetector method routing | the experiment's current algorithms, parameters, working points and period definitions |
| Check roles, types, four-valued semantics and criteria freeze | the experiment's reference samples, controls, in-situ conventions and existing validation practices |

- Experiment-specific content is supplied through the existing profile mechanism (e.g. an experiment with access-controlled data will have a corresponding companion profile); the general layer hard-codes no experiment's values.
- When a profile is missing, the general layer operates as usual, but the corresponding claims are limited to what public sources or information supplied by the user can support, and this is stated explicitly in the completion report.
- **Conflict handling:**
  - Safety, authorization and blinding rules → take the stricter one.
  - Validation-method rules (whose strictness cannot be compared along a single dimension) → adopt the **source-backed profile convention**, record the conflict, and refer it to a human decision when necessary; do not let general rules automatically override conventions endorsed by the collaboration.
  - All conflicts are recorded so that they can be corrected at the corresponding source.

