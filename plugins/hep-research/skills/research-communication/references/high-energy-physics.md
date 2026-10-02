# HEP Diagrams

Treat every HEP figure as one of: **process** (physics), **detector** (apparatus), **workflow**
(data/simulation), or **statistical** (inference). Do not silently merge them.

## 1. Vocabulary

Collision events, trigger, readout/DAQ, reconstruction, tracks, calorimeter clusters, jets,
electrons, muons, photons, missing transverse momentum (MET, `$E_T^{\rm miss}$`), b-tagging, PID,
event selection, signal/control/validation regions (SR/CR/VR), background estimation, systematic
uncertainties, likelihood fit, limits, significance, cross-section measurement.

## 2. Collider analysis pipeline (conceptual)

```text
Collision data -> Trigger / DAQ -> Event reconstruction -> Object reconstruction & calibration
   -> Event selection -> Background estimation -> Statistical analysis -> Result
```
Parallel branch: simulated events pass the same reconstruction. Show data and simulation as two
inputs merging at "reconstruction" only if the same software applies; mark simulation dashed.
Assumption to state: conceptual, not a specific experiment's software.

Ordering rules to check: trigger precedes offline reconstruction; object calibration precedes
selection cuts that use calibrated quantities; systematic variations propagate from objects to
yields to the likelihood (not the reverse); data-driven background estimation uses CRs, not SRs;
blinding places SR data after analysis freeze.

## 3. Monte Carlo chain

```text
Physics process -> Matrix element (hard process) -> Parton shower -> Hadronization
   -> (+ underlying event, + pileup overlay) -> Detector simulation (full/fast)
   -> Digitization -> Reconstruction -> Analysis
```
Levels: **parton/generator (truth)**, **particle level** (stable particles), **detector level**
(reco). Truth-level quantities never feed a data-like selection except for labeled truth matching or
unfolding. Event weights (generator, pileup, scale factors) attach to simulated events only.
Fast vs full simulation: alternative branches, not sequential stages.

## 4. Detector schematics (conceptual)

Layer order outward from the interaction point (IP): beam pipe -> tracker (inner) -> ECAL -> HCAL ->
(solenoid location depends on the experiment) -> muon system. Show: beam axis, IP, cylindrical
barrel + endcaps, trigger/DAQ as a *readout* path separate from the geometry.

Rules: no dimensions, angles, or radii unless supplied; label "not to scale, conceptual"; the
magnet position and the ordering of the solenoid relative to the calorimeters differ per experiment
(ask or stay generic); do not draw subdetectors the user did not mention.

## 5. Decay trees vs Feynman diagrams

| | Decay tree / process chain | Feynman diagram |
|---|---|---|
| Purpose | topology and final state | perturbative amplitude structure |
| Vertices | not interactions per se | specific couplings |
| Correctness needs | listing of particles | Lagrangian / allowed interactions |

Example decay chain: `pp -> H -> ZZ* -> 4l`, `t tbar -> (W+ b)(W- b-bar)`. Draw as a tree; write
"simplified decay topology, not a Feynman diagram". Charge conservation, lepton number, and
flavor should be checked on every vertex of a listed chain; if a step is not allowed, say so.

### Feynman-style diagrams

Require the process (and preferably model/coupling assumptions) from the user. Do not invent
interactions. Line semantics: fermion = solid with arrow; antifermion = arrow reversed;
photon = wavy; gluon = curly/coil; W/Z = wavy (label the boson); scalar (Higgs) = dashed;
generic propagator = plain line. Label incoming (left), outgoing (right), vertices, internal
propagators; identify s/t/u channel by which Mandelstam variable the propagator carries. Loops
only when asked. Conservation checks at each vertex (charge, fermion-number flow, color).

tikz-feynman (needs `\usepackage[compat=1.1.0]{tikz-feynman}`; automatic layout requires LuaLaTeX, while
pdfLaTeX/XeLaTeX need explicitly placed vertices - see `tikz-patterns.md`).

## 6. Statistical architecture (likelihood)

```text
Observed data ---------------------------\
Signal model  --\                          v
Background model -> Likelihood L(mu, theta) -> Test statistic (profile LR) -> CI / limit (CLs) / significance
Systematics -> nuisance parameters theta (with constraint terms) ----^
```
Checks: parameter of interest `$\mu$` vs nuisance `$\theta$`; constraint terms attach to
nuisances; observed vs expected (Asimov) are different branches; frequentist vs Bayesian (priors)
must not be mixed; correlations between uncertainties drawn as shared nuisances, not as arrows
between systematics; multiple regions enter one **simultaneous** fit with shared parameters.

Signal/control-region workflow: SR and CRs are disjoint selections; CRs constrain background
normalization or shape via a transfer factor to the SR; validation regions test the extrapolation
and are not fitted; state which is which.

## 7. Validation checklist (run every time)

- generator-level vs reconstruction-level quantities separated
- simulation vs real data not merged (or labeled where they meet)
- particle-level vs detector-level objects; truth labels not mixed with reco
- signal vs background; observed vs expected
- selection ordering physically sensible
- systematic propagation direction; nuisance relationships
- CR/SR/VR roles explicit
- "conceptual, not experiment-specific" assumption written down

## 8. Pitfalls

Drawing a decay chain as a Feynman diagram; putting DAQ inside the calorimeter box; showing
"simulation" as a stage after data; connecting systematics directly to the result; using truth
info in a selection; drawing arrows from limit back to likelihood.

For actual analysis code, cutflows, fits, and detector physics see the `hep-analysis` skill;
for AMS-02 specifics use `ams-analysis`.
