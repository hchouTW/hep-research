# Routing Contract

Status: M1 `[Proposal]`, enforced statically by skill descriptions (`skills/*/SKILL.md`) and tested with routing cases in M5 (`tests/routing/cases.json`, English and Traditional Chinese).

## Rule

Choose the primary skill by the **deliverable**, never by an experiment, model, or tool name. Profiles add knowledge to the chosen skill; they never become entry points. There is no coordinator skill and no dispatch API: a skill names the next skill and the artifact path in its answer, and Claude or the researcher continues from there. The independent review driver (`skills/hep-authoring/scripts/review.py`) is not one: it sequences one review inside hep-authoring, dispatches no agent and routes no work between skills (docs/dev/decision-independent-review.md).

## Per-skill triggers

| Skill | Direct (primary) | Neighboring (routes elsewhere) | Negative (not this plugin, or not this skill) |
|---|---|---|---|
| hep-measurement | "Design the selection and background estimate for my flux measurement"; "Review this measurement spec"; "Which systematics should I evaluate?" | "What is the tracker resolution?" → hep-detector; "Set a CLs limit" → hep-statistics | "Fix the segfault in my analysis code" → hep-computing |
| hep-detector | "Measure the trigger efficiency with tag-and-probe"; "Build the response matrix"; "RICH velocity resolution vs charge"; "Compare these spectrometer layouts against my resolution and charge-confusion requirements"; "Set up the design loop: requirements, candidates, evaluations, derived compliance matrix" | "Unfold with this matrix" → hep-statistics; "Expected precision of each design with Asimov data" → hep-statistics; "Physics goals of the design" → hep-measurement | "Design the full measurement" → hep-measurement |
| hep-theory | "Derive the tree-level cross section with these conventions"; "Compare my model with the published flux"; "Recast this search for my model" | "Fit my model's coupling to the data" → hep-statistics after the prediction; "Fold my prediction through the response" → hep-detector | "Write the paper section" → hep-authoring |
| hep-statistics | "Feldman–Cousins interval for zero observed events"; "Combine these two measurements with shared systematics"; "Bayesian posterior with these priors" | "Which correlation should I assume?" → evidence owner (hep-measurement / hep-detector / hep-theory) | "Choose my selection cuts" → hep-measurement |
| hep-computing | "Memory leak in my ROOT macro"; "Batch submission with resubmission and merge"; "Convergence study of this integral" | "Is this result physically right?" → owning physics skill | General non-physics software questions outside research code: no special handling |
| hep-ml | "Train a classifier with grouped splits"; "Train a BDT for my event selection"; "ECAL energy regression with a neural network"; "Surrogate for my simulation"; "Domain shift between MC and data" | "What physics should the surrogate respect?" → hep-theory; "Is my SBI posterior's coverage valid?" → hep-statistics; "Validate the fast simulation against Geant4" → hep-detector | TensorFlow/JAX-only questions: plugin gives general advice only |
| hep-citations | "Check that this citation supports the number"; "What did the collaboration publish on this, latest first?"; "Collect the literature on this topic into a table" | "Import the published table and compare it with my model" → hep-theory; "Have agents who did not write my draft review it, with a checkable record" → hep-authoring | "Are these two published fluxes compatible?" → hep-statistics |
| hep-authoring | "Draft the results section"; "Draw the analysis workflow"; "Write the referee report"; "Run an independent review of this design note" | "Is this Feynman diagram physically correct?" → hep-theory; "Has every citation in my draft been verified?" → hep-citations | "Run the fit for the paper" → hep-statistics |

## Topic ownership (single source)

One owner per topic. This table is the source the skill "Owns" lines, descriptions, the README skill table and the
capability matrix follow; `tools/check_ownership.py` fails when another skill claims a topic's terms in its "Owns"
line, in the "Use when" part of its description or in its README row, when the owner does not claim the topic, or
when the named capability-matrix row lists a different owner. Terms are matched case-insensitively with hyphens read
as spaces.

Correlations: hep-measurement supplies the physical correlation evidence and a proposed scheme with its justification; hep-statistics encodes it in the likelihood and checks positive semidefiniteness.

<!-- ownership-table: read by tools/check_ownership.py -->
| Topic | Owner | Claim terms | Capability-matrix row |
|---|---|---|---|
| Response objects: definition, orientation, normalization, what sits inside the matrix | hep-detector | `response matrices`, `response matrix` | Response objects, forward folding, double-counting checks |
| Forward folding a prediction through a response | hep-detector | `forward folding`, `folding a prediction` | Response objects, forward folding, double-counting checks |
| Double-counting checks of corrections inside and outside the response | hep-detector | `double counting checks` | Response objects, forward folding, double-counting checks |
| Unfolding algorithms, regularization and their coverage | hep-statistics | `unfolding` | Unfolding |
| Fits that use a response or a folded prediction | hep-statistics | `fits that use a folded prediction`, `fits that use a response` | — |
| BDTs and classical MVA in an analysis: training, weights, working points | hep-ml | `BDT`, `classical MVA` | — |
| Training networks for ML-assisted or simulation-based inference | hep-ml | `ML-assisted inference` | — |
| Training generative fast simulation | hep-ml | `fast simulation training` | — |
| Calibration of ML model outputs (temperature, isotonic, reliability) | hep-ml | `calibration of model outputs` | — |
| Validity and coverage of an inference built on an ML model | hep-statistics | `coverage` | — |
| Correlation evidence and a proposed correlation scheme for systematics | hep-measurement | `correlation evidence` | — |
| Detector calibration (energy scale, alignment constants, conditions) | hep-detector | `detector calibration` | — |
| Validation of a fast or learned simulation against full detector simulation | hep-detector | `detector simulation` | — |
| Instrument design: requirements flow-down, trade-offs, figures of merit, layout optimization | hep-detector | `detector design principles` | Detector design principles and tracker resolution |
| Sourced facts on named experiments' detectors (design, achieved, operating values with claim ids) | hep-detector | `sourced detector atlas` | Sourced detector atlas |
| Citation verification and read levels of sources | hep-citations | `literature discovery and verification`, `read levels` | Literature and citation verification online |
| Source and claim ledgers in a project; planned claims to recheck | hep-citations | `source and claim ledgers` | Planned claims (Com1): `kind: planned` with `recheck_by` in evidence ledgers |
| Literature matrices with identifiers and read levels | hep-citations | `literature matrices` | — |
| Claim-to-result links in a manuscript or a packaged result | hep-authoring | `claim-to-result links` | Claims linked to results, status preserved in text |
| Writing a literature review or a related-work section from the sources | hep-authoring | `related-work and review sections` | — |
| Independent review packets, review records and the review log | hep-authoring | `independent review`, `review packet` | — |
| Semantic naming of identifiers, files and named objects: charter, engine, contract levels, change sets | hep-computing | `semantic naming` | Semantic naming governance (charter, engine, extractors for all 17 surfaces, cross-surface names, plugin gate) |
<!-- /ownership-table -->

hep-measurement keeps the measurement-design view (which level to publish, which corrections the response carries) in
`skills/hep-measurement/references/measurements-and-unfolding.md` and links out; it claims none of these topics.

ML topics split by deliverable. hep-ml owns the model: training a BDT or network for a selection, a regression
(including an ML energy calibration such as an ECAL regression), a generative fast simulation, or the networks of a
simulation-based inference, and the calibration of the model's outputs. The neighbours own what is built on it or
checked against it: hep-statistics the validity and coverage of the inference, hep-detector the detector
calibration chain and the validation of a fast simulation against full simulation, hep-measurement the selection,
normalization and systematics around a score.

## Deliverable-based rules

- Detector subsystem performance study → hep-detector + the experiment profile's subsystem module.
- Measurement design for a named experiment → hep-measurement + that experiment profile.
- Instrument design (layers, field, material, granularity, a layout meeting a resolution) → hep-detector; the design of the measurement or analysis that uses the instrument → hep-measurement.
- Symbolic derivation → hep-theory with no experiment.
- Theory request that mentions an experiment's **published** data → hep-theory with a dataset record, not hep-measurement.
- Recasting → hep-theory (predictions in the published observable space), then hep-statistics for the limit.
- Code problem in an experiment's script → hep-computing; the profile is read only if a data format or convention matters.
- ROOT histogram and TEfficiency objects: using the objects (Sumw2, errors, Divide, flow bins, TEfficiency construction, RooWorkspace imports) → hep-computing; which interval to quote → hep-statistics; measuring an efficiency (tag-and-probe, truth matching) → hep-detector.
- Domain outside v1 → closest core owner with an explicit "no validated domain profile" notice (stanza step 4). The domains are listed under "Scope of v1" below.
- Underspecified cross-experiment request (for example "compare the two experiments") → ask which datasets and observables; never pick experiments from vague wording.

## Scope of v1

Generated from the [capability map](capability-map.md) by `python3 tools/capability_map.py --write` (X1); edit the
map, not this list. A domain moves into v1 with the item named here (neutrino oscillations entered with Th4, dark-matter
phenomenology conventions with Th5); interpreting an excess with a dark-matter model stays outside v1, and its cases
`wp11-bound-dm-1` and `-2` stay limited-support.

<!-- v1-scope: generated by tools/capability_map.py -->
In v1 (capability IDs of the map, by owner; the state of each is in the map):

- hep-measurement: measurement-design, cosmic-ray-flux, systematic-scaling, collection-time, spectral-transform, acceptance-from-generation
- hep-detector: response-folding, resolution-efficiency, fast-spectrometer-simulation, scale-distortion, response-construction, species-migration, multisample-pid, stability-monitoring, detector-design, geomagnetic-backtracing, full-detector-simulation
- hep-statistics: fits-and-limits, covariance-and-combinations, unfolding, bayesian, time-series, split-consistency, roofit-status, pdf-reweighting-and-profiling, global-pdf-fits
- hep-theory: theory-predictions, recasting, physical-data, relativistic-kinematics, cosmic-ray-propagation, nuclear-physics-entry, neutrino-oscillations, dark-matter-phenomenology, dis-structure-functions, drell-yan, nuclear-parton-effects, polarized-dis, sidis-and-tmd, small-x-saturation, exclusive-and-gpd
- hep-computing: partition-and-batch, root-and-columnar-io, reproducibility, task-authoring, semantic-naming
- hep-ml: ml-training, bdt-pipeline, ml-eras
- hep-citations: literature-verification
- hep-authoring: claims-to-results, terminology, papers-and-numbers
- hep-review: recorded-review

Outside v1 (the closest owner answers with the limited-support notice):

- Lattice QCD and its global analyses (lattice-qcd) → hep-theory
- EFT global fits (eft-global-fits) → hep-theory
- CKM global fits (ckm-global-fits) → hep-theory
- Global cosmic-ray propagation fits that run a propagation code (propagation-global-fits) → hep-statistics
- Interpreting an excess with a dark-matter model (which model explains a signal) (dark-matter-excess-interpretation) → hep-theory
- Heavy-ion physics (quark-gluon plasma, collective flow) (heavy-ions) → hep-theory
- Nuclear-structure calculations (shell model, density functionals) (nuclear-structure) → hep-theory
- Full relic-density Boltzmann solvers (relic-density-solvers) → hep-theory
- Model calculations of PDFs, TMDs and GPDs (quark models, chiral quark soliton, AdS/QCD) (hadron-models) → hep-theory
- Quarkonium production and absorption (NRQCD, J/psi in pA and eA) (quarkonium-production) → hep-theory
- Jets and jet substructure in lepton-hadron scattering, resolved-photon photoproduction (jets-in-dis) → hep-theory
<!-- /v1-scope -->

## Handoff chains (must terminate)

```text
J1  hep-measurement -> hep-detector -> hep-statistics -> hep-authoring   (ends: report)
J3  hep-measurement -> hep-detector -> hep-statistics                            (ends: corrected distribution)
J4  hep-theory <-> hep-computing                                                   (ends: prediction + checks; at most one round trip per check)
J5  hep-theory -> hep-detector -> hep-statistics -> hep-authoring   (ends: fit result + note)
J13 hep-citations -> hep-theory -> hep-statistics -> hep-authoring   (ends: published-data comparison written up)
J7  hep-theory -> hep-detector -> hep-statistics                               (ends: limit)
J9  hep-ml -> hep-statistics                                                    (ends: validated inference)
```

A chain stops at the user's deliverable or at a blocker reported to the user. A skill never hands an artifact back to the skill that produced it for the same purpose.

## Reminder hook (evaluated, not shipped)

An evaluation of a `UserPromptSubmit` hook that adds one line ("load the owning hep-research skill
before answering") when a prompt names an experiment or a quantity such as a cross section, limit or resolution
found the following, so it is not shipped:

- it fires on 41 of 118 routing cases and adds about 46 tokens to each of those prompts, every session;
- of the three quick questions live runs answered without a skill, it does not fire on `co-direct-1` (a ROOT memory
  leak names no quantity), so the measured gap would stay partly open;
- it cannot name the right skill without duplicating the descriptions, so it only nudges; whether the nudge changes
  live routing is unmeasured (no live run);
- hooks are host-specific: the Claude Code hook format does not carry to Codex or the Claude apps, while the plugin
  keeps every skill host-neutral (`tools/check_host_neutral.py`).

Revisit if a live round shows quick-question misses that a reminder fixes.

J5 ownership of the fit half (STH-T4.6, order question Q9): when the prediction exists, the case starts at the fold
(hep-detector, case `j05`); the follow-up "now fit the normalization" is a fit that uses a folded prediction and
loads hep-statistics (multi-turn case `j05-turn-fit`), consistent with the topic table above.

## Language

Routing cases include Traditional Chinese requests (AC20). At runtime the plugin answers end users in the language they use; artifacts and field names stay in English.

Non-English cases need no English trigger terms: a real request does not quote the description, so a case may be
written as a natural prompt (`"natural": true`), which `tools/check_routing_static.py` checks reuses no run of four or
more consecutive words of the expected skill's description. What keeps routing anchored for those prompts is that each
owned topic below stays named in the "Use when" part of the owner's description; the checker fails when one is
removed. Skills may add their rows.

<!-- description-topics: read by tools/check_routing_static.py -->
| Skill | Topics the description must name |
|---|---|
| hep-statistics | likelihoods; binned and unbinned fits; template fits; published data points; intervals and limits; Feldman-Cousins; CLs; profile likelihood; Bayesian posteriors; significance and look-elsewhere effects; low or zero counts; nuisance parameters; covariance assembly; unfolding; folded prediction; toys and Asimov datasets; goodness of fit; model comparison; combinations |
| hep-citations | what a named experiment published; whether a paper exists; which result is the latest; what a paper states; whether a result supports a claim; finding and verifying literature and citations; source and claim ledgers; planned claims to recheck; literature matrices and reviews |
| hep-authoring | drafting or revising paper sections; abstracts and captions; figures and tables; diagrams as editable sources; talks and posters; referee reports; theses; proposals; handover notes; claim-to-result links; never cites from memory |
