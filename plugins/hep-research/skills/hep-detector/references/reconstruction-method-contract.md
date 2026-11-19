# Reconstruction Method Contract

What to decide and record before choosing a reconstruction algorithm: method semantics, conditions as observation
context, uncertainties carried with the quantity, association versus counting, method routing by subsystem, selection
bias and exposure, and partitioning. Its summary, at the point of the chain where it applies, is in
[event reconstruction](event-reconstruction.md#planning-a-reconstruction-the-method-contract).

Before choosing an algorithm, decide what the request needs and record it; this applies to any detection technology,
online or offline, event-based or continuous readout, raw or derived data, data or simulation, one subsystem or a
cross-subsystem combination. Which evidence and records each deliverable needs (evidence tier, task record, checks
and completion report) is in hep-computing
[research workflow control](../../hep-computing/references/research-workflow-control.md). Values, algorithms and
working points of a named experiment come from its profile or project sources, never from this page.

**Record the method semantics when the result depends on them.**

| Semantics | Record | Failure it prevents |
|---|---|---|
| Target state and assumptions | quantity, unit, sign, reference surface, particle or topology hypothesis | rigidity taken as momentum; entry and exit states mixed up |
| Object–observation relations | object scope; legitimate many-to-many, shared, split or competing candidates | one deposit counted twice; candidates counted as particles |
| Passes and information consumption | order, what a mask or removal applies to, whether it is recoverable | an early pass removes later signal and only the survivors are validated |
| Calibration dependencies | sample, period, derivation method, assumptions, reference, shared uncertainties | the calibration absorbs the signal; mutual consistency taken as absolute scale |
| Redoable scope | retained level per branch, selection, conditions, raw or reference availability | pretending deleted raw data can be rerun |

After conditions or methods change, first classify what can be redone — reconstructable, downstream recomputation
only, needs more raw or reference data, unrecoverable — then schedule; the last two block only the claims that depend
on them. Events not recorded by the trigger are unrecoverable.

**Conditions are observation context, not a version label.** For a step that depends on calibration, geometry, field,
simulation settings or model versions, keep the observation key (run, time or an experiment key), the identity and
interval of validity of the payload actually resolved, and overrides; a mutable alias alone does not support reuse,
so keep a snapshot or digest. A chunk spanning an IOV boundary must not share the first or last set of conditions;
continuous conditions keep their model; ambiguous or missing conditions are resolved by the project's rules and
**never by falling back to “latest”**. The global tag or resolution rule is fixed before execution; what was actually
resolved is recorded after it. Simulation settings (geometry and material version, physics list, generator and tune,
digitization and noise, pileup) are conditions too; a run-dependent MC mixture keeps its mapping and weights; a
data/MC comparison states how the two condition contexts correspond.

**Propagate uncertainties with the quantity.** Record parameter order, units, coordinate basis and surface, the
uncertainty representation (covariance, asymmetric interval, samples, mixture) and what it is conditional on. Shared
tracks, clocks, alignment and calibration make combined quantities correlated: never assume zero, never invent a
coefficient — do a founded sensitivity study or state the limitation. Transform uncertainties with coordinates,
without double-counting process noise; use local linear propagation only where valid. A singular matrix is not fixed
by adding jitter; find whether the cause is an unidentifiable direction, the coordinates or numerics. Keep per-object
fit uncertainties apart from calibration uncertainties shared across events. A deliverable that needs a precision
claim cannot be completed by omitting the uncertainties; combined inference goes to hep-statistics.

**Keep association and counting apart.** Distinguish measurement, candidate, association and selected object; say
whether an association is a hard assignment, a set of compatible candidates, normalized probabilities or an
uncalibrated score (a score has no probability meaning by itself). With several candidates kept, yields and event
sums need an explicit deduplication or marginalization; duplicate rows are not particles, and genuine sharing must
not be crudely deduplicated.

**Method routing: questions to resolve before choosing a method.** Load only the rows the task needs; this is a
planning list, not a set of executable algorithms.

| Observation or subsystem | Questions to resolve |
|---|---|
| Trigger and online selection | irreversible sampling; efficiency from orthogonal triggers, tag-and-probe or other data-driven methods with their premises checked; online vs offline differences; trigger bias of calibration samples |
| Waveform and photosensor readout | baseline, saturation, pileup, noise, readout window, pulse separability |
| Dedicated calibration runs | non-event inputs keyed by time or run; IOV correspondence with physics runs |
| Tracking | geometry, field, material, surface, charge hypothesis, pattern ambiguity, alignment weak modes |
| Vertexing and decay topology | shared tracks, primary selection, constraints, error propagation |
| Calorimetry | response domain, leakage, nonlinearity, sharing, track matching |
| Composite objects (jets, MET) | shared uncertainties of constituents, pileup mitigation, in-situ scale from data |
| TOF and precision timing | clock and t0, path- and track-related uncertainties, compatible multiple solutions |
| RICH and Cherenkov (incl. water-Cherenkov rings) | radiator, optics, track hypothesis, background light, ring ambiguity |
| dE/dx, TRD and other PID | sample conditions, shared path or momentum information, calibration domain of the score |
| Muon and outer-detector matching | material, matching, non-prompt hypothesis, fake matches |
| TPC, LArTPC, continuous readout | **t0 per interaction**: per event or trigger only when one interaction occupies the drift window; with continuous readout or pileup in the drift window, per track or interaction (light matching, cathode/anode crossings, a matched external trigger), never one trigger t0 for out-of-time tracks; drift velocity measured separately (its error scales the drift coordinate); lifetime attenuation, recombination, gain, distortion, plane matching, frame boundaries. **Without a track's own t0, report no absolute drift position and apply no drift-time correction**: mark charge and energy uncorrected |
| Scintillation, rare-event, thermal readout | signal formation, quenching or thermal response, low-threshold selection domain |
| Air-shower, radio and other arrays | geometry and timing, medium and model dependence, trigger and exposure |
| Neutrino energy | interaction-model dependence, invisible final-state parts |
| Learned (ML, GNN) reconstruction | the model version is a condition; training vs application domain (hep-ml) |
| Exposure, luminosity, live time | consistency with numerator exclusions; time of DQ certification |
| Cross-subsystem combination | ownership, compatibility hypotheses, shared uncertainties, missing information |

A target cannot always be reconstructed uniquely: report the identifiable part, the external constraints relied on,
or a feasibility conclusion, rather than filling in an unvalidated prior to manufacture a unique value.

**Selection bias and exposure.** Record trigger conditions, prescales and online/offline differences; measure trigger
efficiency from data with an uncertainty; state the trigger bias of calibration samples. DQ exclusions based on
detector state may be certified after data taking, with criteria and version recorded and the **exposure reduced at
the same time**; exclusions based on the result are forbidden. For a flux, cross section or rate, time-based
exclusions leave the exposure, event-based selections go into efficiency × acceptance, and exclusions depending on
both time and the measured quantity (e.g. a geomagnetic-cutoff exposure per rigidity bin) are treated one way,
consistently in numerator and denominator — never twice, never omitted. DQ criteria are defined without reference to
the estimand distribution; quality flags correlated with it are declared and their impact evaluated.

**Partitioning is part of the method.** A chunk is a scheduling unit, not a physical unit: state whether the unit is
independent events, observations with a neighborhood, state across frames, or a full-sample estimate; reread halos
and preceding state as needed, give outputs an explicit owner, build full-sample calibrations as a common estimate
(never average already-normalized chunks), merge with weights and the applicable statistics, and record the RNG
streams. After changing chunking or parallelism, check equivalence (partitioned vs unpartitioned, boundaries, order)
against a tolerance the target justifies. Keep a processing account per stable key (to do, done, excluded with
reason, failed, unconfirmed); failures are never dropped afterwards from the denominator. A pilot covers the periods,
occupancies, boundaries and difficult topologies that affect the method; before scaling up, look at science checks
and runtime, memory, I/O and output volume together.

**Representative cases** (illustrations; the rules above govern):

<!-- example: representative reconstruction cases -->
- *AMS-style mass from rigidity and β*: list signed rigidity, charge and mass hypothesis, β domain, surface and
  calibration dependencies; m = Z·R·√(1/β² − 1), so δm/m ≈ γ²·δβ/β ⊕ δR/R (⊕ assumes uncorrelated β and R, which a
  TOF β using the tracker path length is not); a scale derived with a known mass cannot be validated by the same mass
  peak — validate with another species; agreement of two β measurements is internal consistency only.
- *CMS-style signal fusion and multiple passes*: record track–cluster relations and what each pass removed; compare at
  a fixed working point; shared-cluster and mask failures are not caught by file hashes.
- *Online, compressed or LArTPC data*: first confirm what was retained. Without an external t0, first check qualified
  internal or joint constraints. Restrict delivery to no absolute position only if the information remains insufficient.
  A control without tail sensitivity is inconclusive — do not scale up or publish that performance claim.
- *Iterative alignment*: see [calibration and alignment](calibration-and-alignment.md#iterative-loops-as-contract-steps).
<!-- /example -->

**Check:** Semantics, conditions context, uncertainty representation and association type are recorded for each
delivered quantity; the routing rows used are named; redoability is classified after any change.
