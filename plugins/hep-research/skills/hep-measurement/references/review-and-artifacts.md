# Measurement review and deliverables

How to review an existing analysis, note, spec or code, and which deliverable to produce for a request. Use the
template [measurement-review-template.md](../assets/measurement-review-template.md). An experiment profile may add
its own checks and evidence labels on top of this procedure; it does not replace it.

## Which deliverable

| The user | Produce |
|---|---|
| asks one question (is `sqrt(N)` right, which denominator, how to treat a background) | a quick answer: the correction first, then the reason, then the check |
| describes an analysis idea | a measurement brief (below), one page |
| asks for a spec or a handoff to another skill | a full `measurement-spec` from [the template](../assets/measurement_spec.template.json), validated with `contracts/validate.py` |
| supplies an analysis, note, spec or code and asks what is wrong, whether it is ready, or for a review | a review: verdict first, on the scale below |

## Verdict scale

Three values, spelled as here in every review, template and tool output (an experiment profile's auditor may print
the same values with spaces):

- `blocked`: a defect changes the result beyond its quoted uncertainty (a correction applied twice or not at all, a
  wrong unit or normalization, a background left out, a biased denominator), or the blinding is broken (no mask, an
  unblinded value seen or used, an agent asked to unblind).
- `needs-work`: defects that change the uncertainties or cannot be verified from what was supplied (a systematic
  without its propagation path, a closure test that was not run, a correlation asserted without evidence), and no
  `blocked` defect.
- `acceptable-with-open-inputs`: no defect left; only inputs marked `unresolved` remain, each named with the change it
  could make to the verdict.

A validator error is a defect, but its rank comes from the physics: a misspelled key is `needs-work`, a double-counted
luminosity is `blocked`. A passing validator is not `acceptable-with-open-inputs` by itself: it checks consistency,
not physical validity.

## Output order

1. **Verdict** in the first sentence, with the one reason that sets it.
2. **Defects ranked by impact on the result**, largest first. Each: the evidence (file and field or line, or a quote),
   why it moves the result and in which direction if known, the smallest fix, and the owning skill when the fix is
   not hep-measurement (response: hep-detector; likelihood and correlations encoded in it: hep-statistics; code:
   hep-computing).
3. **Proposals**, labelled `[Proposal]`, kept apart from defects.
4. **Unresolved inputs** and which of them would change the verdict.
5. What was not reviewed (files not supplied, checks not run).

## Checklist

One line each; every item maps to an invariant of the skill and, where one exists, to a validator code.

- Estimand in one sentence: quantity, species or process, variable and range, level, frame, what is held fixed
  (`measurement.estimand_missing`).
- Observable complete: units, binning, phase space, level, frame, normalization kind, bin semantics
  (`measurement.variable_incomplete`, `measurement.phase_space_missing`, `measurement.frame_missing`).
- Every selection has its conditional denominator (`measurement.denominator_blank`).
- Every correction appears once; its normalization kind is declared and not applied again
  (`measurement.duplicate_correction`, `measurement.correction_category_repeated`,
  `measurement.normalization_double_counted`).
- Each background has an estimator, a control region or constraint, and a closure test
  (`measurement.background_constraint_missing`, `measurement.background_closure_missing`).
- Each systematic names its physical effect and `applied_via` (`measurement.applied_via_missing`).
- The blinding mask is defined and respected in plots, ratios, logs, caches and reports
  (`measurement.blinding_mask_missing`); rules in [analysis design](analysis-design.md#blinding).
- Status labels (synthetic, Asimov, observed) are carried on everything derived.
- Unknowns are `unknown` or `not-provided` and listed, never zero (`measurement.zero_value`,
  `measurement.unresolved_not_listed`).

## Spec against implementation

The checklist above reads the spec on its own; these questions compare it with what the recipe, the code and the
outputs actually do. Ask them when the code or recipe is supplied. Name the element (spec field, recipe step, line)
for every defect. If an input a question needs is missing, the answer is undetermined with that input named, never a
pass. In a recorded review (hep-review), each row becomes one obligation with `domain_refs: ["hep-measurement"]`, the
question and criterion as written, and the methods "assumption and convention check" (plus "numerical
recomputation" for factor values).

| ID | Question | Criterion | Missing input |
|---|---|---|---|
| M-ROOT | Does each reported result have the same estimand, binning, scope and output in spec, code and output files? | edges, units, scope (species, period, selection) and output agree | which output file holds the result |
| M-CLASS | Is each correction's category an effect of `<plugin root>/contracts/vocab/effects.json`? | a catalog effect; a name that only looks like `*_efficiency` is not a classification | the category of a correction |
| M-REALIZED | Is each spec correction applied exactly once, by a compatible step, in every instance it applies to? | one application per instance; a declaration that narrows where it applies is itself checked against the code | which instances a correction applies to |
| M-DESCRIBED | Is every effect the code applies described in the spec? | a correction of exactly that category (bin width excepted); a background only through a non-empty `backgrounds` block; "no backgrounds" while one is subtracted is a contradiction | none: an undescribed applied effect is a defect |
| M-STAGE | Is each correction applied where the spec's `applied_in` says? | the step that realizes it is at that stage | the step that applies it |
| M-REPEAT | Is any effect applied twice on one computation path with overlapping scope? | never, unless a declared exclusive partition separates the scopes; read every such declaration, one that contradicts decides, and the answer must not depend on reading order | how two scopes relate |
| M-COMPOSITION | Are a parent factor and its parts (for example exposure and acceptance × live time) both applied? | never on one path; the parts are the catalog's compositions | which composition the factor table follows |
| M-FACTOR-VALUES | Do per-bin factor values equal the product of their parts? | relative tolerance 1e-9, or Σ\|power\| · ½·10^(1−d) when every value is quoted to d significant digits; a tolerance written in the table is not used | the parts' per-bin values |
| M-RESPONSE | Is the response use the spec describes realized in the chain, or bound to a prediction? | the response named in the spec is the one used | which response a step or prediction uses |

## Measurement brief (one page)

Estimand (one sentence) · observable (variables, units, binning, level, frame) · data and periods · selection outline
with denominators · backgrounds with their estimators and control regions · correction chain (each factor once) ·
leading systematics and how each is propagated · blinding (mask, who unblinds) · open inputs · handoffs (which skill
receives which artifact).

## Worked review (synthetic)

Input: [review-example.synthetic.json](../assets/review-example.synthetic.json), a deliberately defective spec with
invented values. `python3 "<plugin root>/contracts/validate.py" <plugin root>/skills/hep-measurement/assets/review-example.synthetic.json`
exits 1 with six errors and one unresolved finding; the review ranks them.

<!-- worked-review-codes: measurement.normalization_double_counted measurement.blinding_mask_missing measurement.background_constraint_missing measurement.unresolved_not_listed measurement.zero_value measurement.applied_via_missing measurement.background_closure_missing -->

**Verdict: `blocked`.** The luminosity enters twice, so every cross section is off by the luminosity factor itself,
and a blinded spec defines no mask.

1. `corrections[1]` (`lumi-scale`, category `luminosity`) next to the `integrated-luminosity` normalization
   (`measurement.normalization_double_counted`): the luminosity is divided out twice, moving every bin by a factor of
   order the luminosity. Fix: delete the correction; the normalization already carries it.
2. `blinding` is `blinded: true` without `mask` (`measurement.blinding_mask_missing`): nothing defines which bins stay
   hidden, so any plot or table can reveal them. Fix: copy the mask from the collaboration's blinding policy.
3. `backgrounds[0]` has neither control region nor constraint (`measurement.background_constraint_missing`), and no
   closure (`measurement.background_closure_missing`, unresolved): a fake factor taken from simulation alone is
   unconstrained, so the background can be biased in either direction. Fix: measure the fake factor in a control region
   and add a closure test in a validation region.
4. `selections[0].conditional_denominator` is `unknown` and not listed in `unresolved_inputs`
   (`measurement.unresolved_not_listed`): the efficiency cannot be defined against an unknown denominator. Fix: name
   the denominator or list it as unresolved.
5. `corrections[2].value` is `0` (`measurement.zero_value`): a zero fake-rate correction is either exact (say so with
   `exact_zero`) or unknown (write `unknown`); as written it may hide the background in item 3.
6. `systematics[0].applied_via` is blank (`measurement.applied_via_missing`): the energy-scale variation has no
   propagation path, so its migration effect cannot be checked (`needs-work` on its own).

Unresolved inputs: the closure test (item 3) and the denominator (item 4) would each change the verdict only after
items 1 and 2 are fixed. Not reviewed: the analysis code and the response (hand to hep-computing and hep-detector).
