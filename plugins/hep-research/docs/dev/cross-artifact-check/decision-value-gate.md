# Decision record: value gate (DR-13)

Status: **design adopted 2026-10-22 (DR-13); thresholds confirmed 2026-10-22 before any measurement.** Architecture `cross-artifact-check-architecture.en.md` section 10. Labels: **Confirmed**, **Inferred**,
**Unresolved**.

## Analysis question

Does the checker catch enough errors that the existing defences miss to justify Phase 2 (rule fixes, the entry
path, new suites), and at what false-positive and authoring cost?

## Protocol (section 10, adopted)

1. **Subject.** The ams-flux-ratio spec and responses with a hand-written recipe that truthfully describes its TSVD
   unfolding: subtract_background → unfold → correct_efficiency → divide_exposure → divide_bin_width.
2. **Definition-induced results.** With the current coverage this recipe gives 4 `unrealized_correction` outcomes for
   `trigger_efficiency` (`correct_efficiency` covers only `selection_efficiency`; **Confirmed** in the architecture
   review). They count in the false-positive arm under "definition-induced". A sensitivity run uses a bundle-supplied
   coverage that lists both members (flagged by A3). Neither counts as a detection.
3. **Error taxonomy** frozen before planting, by category, from T3, `crflux-review.md` and published errata.
4. **Planting.** A non-author plants at least 20 errors, each in the code and in the descriptions, without seeing
   the rules (O04). If an agent stands in, the results are labelled "AI-planted".
5. **Scoring** layer by layer: closure tests → `validate.py` and L2 → the checker (suite 1.0.0 on R1). Main metric:
   the checker's incremental detections, i.e. planted errors the checker flags (violated, or unverified with a reason
   that names the planted defect) that no earlier layer flagged.
6. **False-positive arm.** Legitimate refactors, plus the definition-induced category.
7. **Cost.** Hand-written fields per bundle, and which could in principle be derived (input to DR-14).
8. **Reproducibility.** The measurement script is committed.
9. **Thresholds** pre-registered below; they never change after measuring.

## Proposed thresholds (Inferred; the maintainer confirms or changes them before measuring)

Let N ≥ 20 be the planted errors, I the incremental detections, R ≥ 10 the legitimate refactors and F the
refactors on which the checker reports a violation (definition-induced results are reported separately and never
count as F).

| Outcome | Condition |
| --- | --- |
| **Pass** | I ≥ 0.25 N (at least 5 of 20) and F ≤ 1 |
| **Shrink** | 0.10 N ≤ I < 0.25 N, or I ≥ 0.25 N with F = 2 |
| **Stop** | I < 0.10 N (at most 1 of 20), or F ≥ 3 |

AI-planted results are discounted: with no human-planted subset, an AI-planted measurement can support at most
**Shrink**; **Pass** needs at least 10 human-planted errors that meet the pass condition on their own.

Rationale (Inferred): the checker costs about 4,000 lines and every bundle is hand-written today, so a pass should
show a clear, not marginal, gain over the existing layers. One false positive in ten refactors is the most a reviewer
aid can afford before reviewers learn to ignore it.

## Cost per phase

Phase 1: 4–10 sessions (gate 3–4, optional spike 0–4, assurance-plane design 1–2), section 9.2.

## Owner

hchouTW. The error planter is to be named (O04), never a rule author.

## Decision

**2026-10-22, maintainer instruction in the session ("thresholds confirmed").** The thresholds above are confirmed
as written, before any measurement: Pass I ≥ 0.25 N and F ≤ 1; Shrink 0.10 N ≤ I < 0.25 N, or I ≥ 0.25 N with F = 2;
Stop I < 0.10 N or F ≥ 3; AI-planted results alone support at most Shrink. They do not change after measuring.

## 2026-10-22, measurement details fixed before planting (implementer)

Written and committed before any error was planted or measured. The thresholds above are unchanged. Harness:
`evals/cross-artifact-value-gate/` at the repository root (`measure.py`, `taxonomy.md`, `planter-brief.md`,
`subject/`).

- **Planter (O04).** The maintainer named an AI agent as the planter ("use an AI agent as the planter", 2026-10-22).
  It is a fresh agent that did not write the rules and works from a kit holding only `run.py`, its reference
  output, the subject descriptions, the operator table and the taxonomy; it is told not to read anything else. Every
  result is labelled **AI-planted**, so under the confirmed thresholds this measurement can support at most
  **Shrink**.
- **Subject.** `examples/ams-flux-ratio/run.py` (the code, which also writes the spec, responses and dataset
  records) plus hand-written `subject/recipe.json` (subtract_background → unfold → correct_efficiency →
  divide_exposure → divide_bin_width) and `subject/context.json`: four flux roots, two He/p ratio roots over the
  species axis, suites counting-chain and ratio-subset 1.0.0, four `response_used_by` bindings, instance mappings
  for the spec corrections; no calibration items and no validation records.
- **Baseline (Confirmed, R1 = 0.25.0).** Layer 1 and layer 2 pass. The checker reports `inconsistent`: 58
  satisfied, 4 violated, 8 not applicable, 12 unverified, 2 unsupported. The 4 violated are the definition-induced
  `unrealized_correction` of `trigger_efficiency` (protocol step 2) and 4 of the unverified are the matching
  `stage_unlocated`; the other 8 unverified and the 2 unsupported are ratio obligations with no bound factor. All
  of them are in the baseline and never count. In the sensitivity arm (bundle-supplied coverage with both
  efficiency members, A3) the baseline is `incomplete` with 0 violated.
- **Layers.** (1) the case's `run.py`, run from a shadow plugin root, flags when it crashes or exits non-zero (a
  pre-declared closure or self-check criterion failed); 400 toys, seed 20261002 (the example's defaults).
  (2) `contracts/validate.py --strict` on the produced artifacts with experiment:ams-02 bound, and
  `contracts/recipe_semantics.py` (L2) on the recipe; flags when either is not ok. (3) the checker: freeze, then
  check.
- **Checker flag.** Freeze refused, invalid input, an obligation that becomes violated, or an obligation that becomes
  unverified or unsupported (from satisfied, not applicable or absent) whose obligation id names an id the planter
  listed in `key.json` `affected`. The match is mechanical (whole-identifier match); nobody adjudicates by hand.
  Obligations that disappear are not flags.
- **Incremental detection (I).** A checker flag on an error that layers 1 and 2 did not flag.
- **False positive (F).** A refactor on which the checker reports a new violated obligation or refuses the bundle.
  Alarms of layers 1 and 2 on refactors are reported but are not F.
- **Validity.** A case whose change does not match its key is still scored as planted; no case is dropped or
  re-planted after measuring.
- **Sensitivity arm** (protocol step 2): reported beside the main arm, never decides the gate.
- **Deviation.** Published errata were not consulted for the taxonomy (protocol step 3; **Unresolved**).

## 2026-10-22, measurement result (implementer)

Run of `evals/cross-artifact-value-gate/measure.py --sensitivity` on R1 (0.25.0, main ce66dd83 plus the harness),
cases committed in fc4cfa20 before measuring; results in `evals/cross-artifact-value-gate/results/`. **AI-planted**:
28 errors (every category C01–C12, two or three each) and 11 refactors.

| Arm | N | R | I | F | Flagged by layer 1 | Layer 2 only | Checker (any) | Missed by every layer |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| main | 28 | 11 | **0** | 0 (mechanical count 1, see below) | 23 | 0 | 6 | E12, E13, E24, E25, E27 |
| sensitivity | 28 | 11 | 0 | 0 | 23 | 0 | 6 | the same five |

- **Confirmed.** I = 0 < 0.10 N = 2.8, so under the confirmed thresholds the outcome is **Stop**, whatever F is. The
  AI-planted cap limits only Pass, so it does not apply.
- **Confirmed.** The checker flagged 6 errors (E01, E02, E11, E18, E19, E21). The closure tests of `run.py` flagged
  all six, and `validate.py --strict` or L2 flagged three of them (E01, E02, E18). Against layer 2 alone, the checker
  adds three errors (E11 incompatible ratio operands, E19 and E21 ratio cancellation and correlation claims).
- **Confirmed; F counting.** R04 renames the instance ids consistently. The checker then reports the four
  definition-induced `unrealized_correction` results of `trigger_efficiency` under the new ids, and the mechanical
  comparison (by obligation id) counts them as new. They are the baseline's definition-induced results, which the
  confirmed threshold text excludes from F, and the sensitivity arm (where they do not exist) gives F = 0. F = 0 or 1
  does not change the outcome.
- **Confirmed.** E18 crashes `run.py` (the planter's double subtraction reads the masked helium count); it is scored
  as planted, as fixed before measuring.
- **Confirmed; what the checker misses.** A response of the wrong species or period bound to an instance (E14, E15);
  a declaration that narrows a correction to the proton instances, which turns the helium obligations into
  `not_applicable` (E22, the P4 pattern); units, edges and blinding text in the spec that differ from the code
  (E10, E13, E24, E25).
- **Inferred; validity.** The subject's closure tests are stronger than in a real analysis: the simulation and the
  truth live in the same file and the planter changed the analysis side only, so 23 of 28 errors broke Asimov or toy
  closure. A subject whose simulation shares the analyst's mistakes would leave more for the later layers. This
  bears on how far the result generalizes; it does not change the pre-registered outcome.
- **Cost (protocol step 7).** The subject has 152 hand-written leaf fields (recipe 18, context 134) plus about 30 in
  the item list. About 17 plus the item list are derivable without writing intent (versions, suites, scope axes,
  recipe header); about 44 only through a run-record bridge (bindings 16, instance structure 28, the spike's
  question); about 91 are intent that P4 and P10 forbid deriving (roots 28, declarations 40, ratio roots 12, recipe
  steps 10, `not_applied` 1).

**Recommendation (Inferred; the owner decides at the decision point, section 9.3):** **Stop** as section 13.3 defines
it: freeze the checker code; keep `--check-bundle` but mark it experimental; mark the manual freeze and check
instructions in the skill references and the README experimental; no new suites; keep the Phase 0 results. The
optional spike and the entry path (DR-14) lose their purpose under Stop. If the owner wants the validity point above
tested, that is a new measurement with its own pre-registered design, not a rerun of this one.

## Decision (2026-10-22, maintainer instruction in the session)

Asked whether "continue" meant the decision-point outcome "continue" or the recommendation, the maintainer chose
**"Stop (my recommendation)"**. The programme stops at the decision point (architecture section 13.3): the checker
code is frozen; `--check-bundle` stays, marked experimental, and so do the manual freeze and check instructions in the
skill references and the README; no new suites; the Phase 0 results stay. Phase 2, the entry path (DR-14) and the
spike do not start. The AI-planted cap did not bear on this outcome.

## Decision changed (2026-10-22, maintainer instruction in the session)

Shown the Stop decision above, the maintainer asked to change "Stop (my recommendation)" to start, and chose
**"Reverse to Continue"** when asked what that meant. The decision-point outcome is now **Continue**: Phase 2
(architecture section 9.4, releases R2 and R3) may start. "My recommendation" in the section above was the label of
the implementer's option, not the maintainer's words.

- This **overrides the pre-registered outcome**. The measurement stays as recorded (I = 0 of 28, F = 0, AI-planted);
  the thresholds are not changed and the gate is **not passed**.
- Phase 2's other entry condition holds: the post-review revisions of DR-1 to DR-8 were adopted
  (`decision-architecture.md`).
- DR-14 (the entry path) was conditional on the gate passing, so it does not start with Phase 2; it needs its own
  decision.
- Because the gate is not passed, no rule can leave shadow mode (`decision-enforce.md`, section 13.5), whatever
  Phase 2 delivers.
- The experimental labels of 0.25.1 stay until Phase 2 releases its fixes; the code freeze of the Stop decision is
  lifted for Phase 2 work only.

## 2026-10-23, re-measurement on 0.26.0 (implementer; a measurement, not a decision)

The maintainer asked to re-run the value gate after Phase 2 shipped in 0.26.0. Same 39 pre-registered cases (28
AI-planted errors, 11 refactors), same layers, scoring and thresholds; nothing was re-planted. Harness changes,
opt-in (`evals/cross-artifact-value-gate/measure.py`; the Phase 1 defaults and `results/` are unchanged):

- `--suite-version 1.1.0`: every context is converted as `migrate.py context-1.0.0-to-1.1.0` does, so the checker runs
  the stable 1.1.0 suites (all R2 and R3 fixes).
- `--rebase-from <0.25.1 run.py>`: 0.26.0 changed the subject (`examples/ams-flux-ratio/run.py` now describes the
  corrections its recipe applies; one block of 11 inserted lines). Each case's `run.py`, a full copy of the 0.25.1
  example with the planted edit, gets the same block at the same place. **Confirmed for all 39 cases:** each rebased
  case differs from the 0.26.0 example exactly as the original case differed from the 0.25.1 example.
- **Inferred, and stated:** with `--rebase-from`, every context also maps the four corrections the 0.26.0 spec added
  (livetime, cutoff transmission, survival, fragmentation feed-down) to the instances, as the subject's acceptance
  mapping does. The subject description must describe the current subject. Without it, those obligations are
  `applicability_unbound` and the new G1 rule cannot judge them. No mapping a case planted is changed.

Results: `evals/cross-artifact-value-gate/results-0.26.0/`.

| Arm | N | R | I | F (mechanical) | layer 1 | layer 2 only | checker, any flag | outcome by the thresholds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| main | 28 | 11 | 0 | 1 (R04) | 23 | 0 | 7 | Stop |
| sensitivity | 28 | 11 | 0 | 1 (R04) | 23 | 0 | 7 | Stop |

**Confirmed, against the Phase 1 result** (`results/`):
- **E22 is the only change.** It is category C10, the P4 pattern Phase 1 listed as missed: a declaration narrows
  `selection_efficiency` to the proton instances, which under 1.0.0 turned the helium obligations into
  `not_applicable`. Under 1.1.0 the helium steps still apply selection efficiency and no correction describes it for
  them, so `r-real.undescribed` (the G1 fix) reports it violated. Layer 1 (closure) flags it too, so it is not an
  incremental detection. Every other case has the same layer flags as in Phase 1.
- **R04 is the same as in Phase 1.** Renaming the instance IDs re-keys the baseline's definition-induced
  `trigger_efficiency` violations. The Phase 1 record counts it as F = 0 under the confirmed text; the same reading
  applies here.
- **Still missed by every layer:** E12 and E13 (C06, binning or range differing between code and spec), E24 and E25
  (C11, a blinded value released by the code), and E27 (C12, a correlation model of an uncertainty). The checker's
  suites do not describe these:
  - binning is compared only between a ratio's operands;
  - blinding is judged on bound results, which this pre-execution subject has none of;
  - uncertainty correlations are not checked.
- **Definition-induced baseline results** (never counted):
  - the 4 `trigger_efficiency` unrealized corrections of Phase 1;
  - 4 `survival` unrealized corrections. The 0.26.0 example spec describes survival because the plugin's shared
    recipe applies it, but the harness's hand-written recipe uses `divide_exposure`, which does not.

Reading: Phase 2 fixed what the gap probes found, but on this AI-planted set the checker still catches no error the
closure tests and contract checks miss. The planted errors it does flag (E01, E02, E11, E18, E19, E21 and now E22) are all
caught by layer 1 as well. An AI-planted measurement can support at most Shrink. This section changes no decision: the gate stays not
passed, every rule stays in shadow mode, and the experimental label is the maintainer's call.
