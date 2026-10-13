# Routing Contract

Status: M1 `[Proposal]`, enforced statically by skill descriptions (`skills/*/SKILL.md`) and tested with routing cases in M5 (`tests/routing/cases.json`, English and Traditional Chinese).

## Rule

Choose the primary skill by the **deliverable**, never by an experiment, model, or tool name. Profiles add knowledge to the chosen skill; they never become entry points. There is no coordinator skill and no dispatch API: a skill names the next skill and the artifact path in its answer, and Claude or the researcher continues from there.

## Per-skill triggers

| Skill | Direct (primary) | Neighboring (routes elsewhere) | Negative (not this plugin, or not this skill) |
|---|---|---|---|
| hep-analysis | "Design the selection and background estimate for my flux measurement"; "Review this measurement spec"; "Which systematics should I evaluate?" | "What is the tracker resolution?" → detector-response; "Set a CLs limit" → hep-statistics | "Fix the segfault in my analysis code" → hep-computing |
| detector-response | "Measure the trigger efficiency with tag-and-probe"; "Build the response matrix"; "RICH velocity resolution vs charge" | "Unfold with this matrix" → hep-statistics | "Design the full measurement" → hep-analysis |
| hep-theory | "Derive the tree-level cross section with these conventions"; "Compare my model with the published flux"; "Recast this search for my model" | "Fit my model's coupling to the data" → hep-statistics after the prediction; "Fold my prediction through the response" → detector-response | "Write the paper section" → research-communication |
| hep-statistics | "Feldman–Cousins interval for zero observed events"; "Combine these two measurements with shared systematics"; "Bayesian posterior with these priors" | "Which correlation should I assume?" → evidence owner (hep-analysis / detector-response / hep-theory) | "Choose my selection cuts" → hep-analysis |
| hep-computing | "Memory leak in my ROOT macro"; "Batch submission with resubmission and merge"; "Convergence study of this integral" | "Is this result physically right?" → owning physics skill | General non-physics software questions outside research code: no special handling |
| physics-ml | "Train a classifier with grouped splits"; "Train a BDT for my event selection"; "ECAL energy regression with a neural network"; "Surrogate for my simulation"; "Domain shift between MC and data" | "What physics should the surrogate respect?" → hep-theory; "Is my SBI posterior's coverage valid?" → hep-statistics; "Validate the fast simulation against Geant4" → detector-response | TensorFlow/JAX-only questions: plugin gives general advice only |
| research-communication | "Check that this citation supports the number"; "Draft the results section"; "Draw the analysis workflow" | "Is this Feynman diagram physically correct?" → hep-theory | "Run the fit for the paper" → hep-statistics |

## Topic ownership (single source)

One owner per topic. This table is the source the skill "Owns" lines, descriptions, the README skill table and the
capability matrix follow; `tools/check_ownership.py` fails when another skill claims a topic's terms in its "Owns"
line, in the "Use when" part of its description or in its README row, when the owner does not claim the topic, or
when the named capability-matrix row lists a different owner. Terms are matched case-insensitively with hyphens read
as spaces.

<!-- ownership-table: read by tools/check_ownership.py -->
| Topic | Owner | Claim terms | Capability-matrix row |
|---|---|---|---|
| Response objects: definition, orientation, normalization, what sits inside the matrix | detector-response | `response matrices`, `response matrix` | Response objects, forward folding, double-counting checks |
| Forward folding a prediction through a response | detector-response | `forward folding`, `folding a prediction` | Response objects, forward folding, double-counting checks |
| Double-counting checks of corrections inside and outside the response | detector-response | `double counting checks` | Response objects, forward folding, double-counting checks |
| Unfolding algorithms, regularization and their coverage | hep-statistics | `unfolding` | Unfolding |
| Fits that use a response or a folded prediction | hep-statistics | `fits that use a folded prediction`, `fits that use a response` | — |
| BDTs and classical MVA in an analysis: training, weights, working points | physics-ml | `BDT`, `classical MVA` | — |
| Training networks for ML-assisted or simulation-based inference | physics-ml | `ML-assisted inference` | — |
| Training generative fast simulation | physics-ml | `fast simulation training` | — |
| Calibration of ML model outputs (temperature, isotonic, reliability) | physics-ml | `calibration of model outputs` | — |
| Validity and coverage of an inference built on an ML model | hep-statistics | `coverage` | — |
| Detector calibration (energy scale, alignment constants, conditions) | detector-response | `detector calibration` | — |
| Validation of a fast or learned simulation against full detector simulation | detector-response | `detector simulation` | — |
<!-- /ownership-table -->

hep-analysis keeps the measurement-design view (which level to publish, which corrections the response carries) in
`skills/hep-analysis/references/measurements-and-unfolding.md` and links out; it claims none of these topics.

ML topics split by deliverable. physics-ml owns the model: training a BDT or network for a selection, a regression
(including an ML energy calibration such as an ECAL regression), a generative fast simulation, or the networks of a
simulation-based inference, and the calibration of the model's outputs. The neighbours own what is built on it or
checked against it: hep-statistics the validity and coverage of the inference, detector-response the detector
calibration chain and the validation of a fast simulation against full simulation, hep-analysis the selection,
normalization and systematics around a score.

## Deliverable-based rules

- Detector subsystem performance study → detector-response + the experiment profile's subsystem module.
- Measurement design for a named experiment → hep-analysis + that experiment profile.
- Symbolic derivation → hep-theory with no experiment.
- Theory request that mentions an experiment's **published** data → hep-theory with a dataset record, not hep-analysis.
- Recasting → hep-theory (predictions in the published observable space), then hep-statistics for the limit.
- Code problem in an experiment's script → hep-computing; the profile is read only if a data format or convention matters.
- Domain outside v1 → closest core owner with an explicit "no validated domain profile" notice (stanza step 4).
- Underspecified cross-experiment request (for example "compare the two experiments") → ask which datasets and observables; never pick experiments from vague wording.

## Handoff chains (must terminate)

```text
J1  hep-analysis -> detector-response -> hep-statistics -> research-communication   (ends: report)
J3  hep-analysis -> detector-response -> hep-statistics                            (ends: corrected distribution)
J4  hep-theory <-> hep-computing                                                   (ends: prediction + checks; at most one round trip per check)
J5  hep-theory -> detector-response -> hep-statistics -> research-communication   (ends: fit result + note)
J7  hep-theory -> detector-response -> hep-statistics                               (ends: limit)
J9  physics-ml -> hep-statistics                                                    (ends: validated inference)
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
(detector-response, case `j05`); the follow-up "now fit the normalization" is a fit that uses a folded prediction and
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
