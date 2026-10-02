# Routing Contract

Status: M1 `[Proposal]`, enforced statically by skill descriptions (`skills/*/SKILL.md`) and tested with routing cases in M5 (`tests/routing/cases.json`, English and Traditional Chinese).

## Rule

Choose the primary skill by the **deliverable**, never by an experiment, model, or tool name. Profiles add knowledge to the chosen skill; they never become entry points. There is no coordinator skill and no dispatch API: a skill names the next skill and the artifact path in its answer, and Claude or the researcher continues from there.

## Per-skill triggers

| Skill | Direct (primary) | Neighboring (routes elsewhere) | Negative (not this plugin, or not this skill) |
|---|---|---|---|
| hep-analysis | "Design the selection and background estimate for my flux measurement"; "Review this measurement spec"; "Which systematics should I evaluate?" | "What is the tracker resolution?" → detector-response; "Set a CLs limit" → hep-statistics | "Fix the segfault in my analysis code" → hep-computing |
| detector-response | "Measure the trigger efficiency with tag-and-probe"; "Build the response matrix"; "RICH velocity resolution vs charge" | "Unfold with this matrix" → hep-statistics | "Design the full measurement" → hep-analysis |
| hep-theory | "Derive the tree-level cross section with these conventions"; "Compare my model with the published flux"; "Recast this search for my model" | "Fit my model's coupling to the data" → hep-statistics after the prediction | "Write the paper section" → research-communication |
| hep-statistics | "Feldman–Cousins interval for zero observed events"; "Combine these two measurements with shared systematics"; "Bayesian posterior with these priors" | "Which correlation should I assume?" → evidence owner (hep-analysis / detector-response / hep-theory) | "Choose my selection cuts" → hep-analysis |
| hep-computing | "Memory leak in my ROOT macro"; "Batch submission with resubmission and merge"; "Convergence study of this integral" | "Is this result physically right?" → owning physics skill | General non-physics software questions outside research code: no special handling |
| physics-ml | "Train a classifier with grouped splits"; "Surrogate for my simulation"; "Domain shift between MC and data" | "What physics should the surrogate respect?" → hep-theory | TensorFlow/JAX-only questions: plugin gives general advice only |
| research-communication | "Check that this citation supports the number"; "Draft the results section"; "Draw the analysis workflow" | "Is this Feynman diagram physically correct?" → hep-theory | "Run the fit for the paper" → hep-statistics |

## Deliverable-based rules (from task 7.2)

- Detector subsystem performance study → detector-response + the experiment profile's subsystem module.
- Measurement design for a named experiment → hep-analysis + that experiment profile.
- Symbolic derivation → hep-theory with no experiment.
- Theory request that mentions an experiment's **published** data → hep-theory with a dataset record, not hep-analysis.
- Recasting → hep-theory (predictions in the published observable space), then hep-statistics for the limit.
- Code problem in an experiment's script → hep-computing; the profile is read only if a data format or convention matters.
- Domain outside v1 → closest core owner with an explicit "no validated domain profile" notice (stanza step 4).
- Underspecified cross-experiment request (for example "compare the two experiments") → ask which datasets and observables; never pick experiments from vague wording (task 7.8).

## Handoff chains (must terminate)

```text
J1  hep-analysis -> detector-response -> hep-statistics -> research-communication   (ends: report)
J3  hep-analysis -> detector-response -> hep-statistics                            (ends: corrected distribution)
J4  hep-theory <-> hep-computing                                                   (ends: prediction + checks; at most one round trip per check)
J5  hep-theory -> hep-statistics -> research-communication                          (ends: fit result + note)
J7  hep-theory -> detector-response -> hep-statistics                               (ends: limit)
J9  physics-ml -> hep-statistics                                                    (ends: validated inference)
```

A chain stops at the user's deliverable or at a blocker reported to the user. A skill never hands an artifact back to the skill that produced it for the same purpose.

## Language

Routing cases include Traditional Chinese requests (AC20). At runtime the plugin answers end users in the language they use; artifacts and field names stay in English.
