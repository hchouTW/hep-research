---
role: Senior experimental physicist editing a collaboration draft
skill: hep-authoring
archetype: contrast
use_case: a results paragraph for a preliminary spectral break in a synthetic cosmic-ray proton flux
---

Illustrative example: the experiment, the result record and every number are invented and name no collaboration. The
rules it applies are in [scientific style](../../references/scientific-style.md) (hedging and significance language) and
[linked writing](../../references/evidence-linked-writing.md) (numbers from artifacts, status labels).

## Scenario

A postdoc asks for "a strong Results paragraph" on a break in a proton flux. The material is one statistical-result
record, status `preliminary`, and the analysis notes. The record gives a double-power-law fit above 60 GV: break
rigidity R_b = 410 +/- 60 GV, index change Delta gamma = 0.09 +/- 0.04, a local significance of 2.3 sigma for the break
against a single power law, and 1.6 sigma when the lower edge of the fit range is varied between 40 and 80 GV. The notes
add that the rigidity-scale uncertainty above 1 TV is not final and that the 1-3 TV bins are therefore excluded from the
fit.

## Common Weak Approach

> We report the first observation of a new spectral feature in the proton flux. The data may possibly suggest that the
> spectrum could perhaps harden at around 400 GV, which might indicate a change in the propagation of cosmic rays. The
> hardening is significant and robust, and it is likely that it reflects a universal property of Galactic cosmic rays.

What goes wrong:

- "First observation" and "significant" promote a 2.3 sigma local, 1.6 sigma range-varied result to the 5 sigma
  vocabulary; "robust" contradicts the drop under the fit-range variation.
- The stacked hedges ("may possibly suggest", "could perhaps", "might indicate") soften the one thing the record does
  establish (the fitted break and its uncertainty) and say nothing about the real limitations.
- The numbers are rounded away ("around 400 GV"), the uncertainty is gone, the `preliminary` status is dropped, and the
  excluded 1-3 TV range is not mentioned.
- "Universal property of Galactic cosmic rays" generalizes beyond a single species and a fitted range.

## Expert-Level Best Practice

Reasoning before writing. Every number goes to the record field it comes from (`audit_claims.py` lists the draft-ready
facts): R_b, Delta gamma and both significances. The significance table puts 2.3 sigma in "an excess, a mild tension"
territory, and 1.6 sigma under the range variation is below it, so the claim is a mild tension with a single power
law, not an observation of a feature. Two limitations
change the meaning and must survive: the significance depends on the fit range, and the 1-3 TV bins are excluded.
These are the hedges worth keeping, because each states a real uncertainty with its size.

> Above 60 GV the proton flux shows a mild tension with a single power law (preliminary). A double-power-law fit gives a break at
> R_b = 410 +/- 60 GV with an index change Delta gamma = 0.09 +/- 0.04, a local significance of 2.3 sigma for the break
> against a single power law. When the lower edge of the fit range is varied between 40 and 80 GV, the significance
> falls to 1.6 sigma, so the break is not yet established. The 1-3 TV bins are excluded until the rigidity-scale
> uncertainty above 1 TV is final; a change in propagation is one possible interpretation that this result does not
> test.

Verification after writing:

- each of 60, 410, 60, 0.09, 0.04, 2.3, 40, 80 and 1.6 matches the record or the notes, and the word "preliminary" is in
  the text and in the figure caption;
- the significance wording matches the table, and the exact number stands next to the word;
- the interpretation sentence names its status ("one possible interpretation ... does not test") rather than borrowing
  certainty from the fit.

Limits of this example: it shows wording for one fitted feature; it does not decide whether the fit model, the range
variation or the significance definition is right (hep-statistics), and a recorded review of that fit is hep-review's.

## Key Takeaways

- Keep the hedges that state a real uncertainty or limitation and give their size (here the fit-range dependence and the
  excluded TV bins); remove the ones that only soften.
- Significance words follow the number: 2.3 sigma local and 1.6 sigma under a range variation is a mild tension at
  most, never "observation" or "evidence".
- Numbers, uncertainties and the `preliminary` label come from the record field by field; rounding "410 +/- 60 GV" to
  "around 400 GV" loses the result.
- Interpretation is labelled as interpretation and kept inside the tested regime (one species, the fitted range).
