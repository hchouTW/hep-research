# Claim–evidence mapping

Use when checking whether a paper's conclusions follow from its evidence. For
external reference checks, use `citation-verification.md`; for actual reruns, use
`reproducibility-auditing.md`; for a contradiction or fallacy in the argument's
logical structure itself, independent of whether evidence is strong enough, use
`logical-consistency-and-argument-uniformity.md`.

## Table of contents
- [Extracting claims](#extracting-claims)
- [Building the evidence matrix](#building-the-evidence-matrix)
- [Checking evidence against claim type](#checking-evidence-against-claim-type)
- [Verdicts and reporting](#verdicts-and-reporting)

## Extracting claims

Extract the central claims from the title, abstract, contribution statements,
results, and conclusion. Split compound claims when their parts need different
evidence. Preserve qualifiers, dataset/regime, comparison, and uncertainty rather
than paraphrasing a narrow claim into a universal one.

## Building the evidence matrix

Build a matrix with: claim ID and location; claim text; type (empirical,
theoretical, methodological, or interpretive); evidence locator; conditions and
assumptions; support verdict; gap; proposed action. Evidence may be a figure,
table, derivation, controlled comparison, or external source. Its mere presence
does not establish that it tests the claim.

## Checking evidence against claim type

Check whether the evidence addresses the exact claim:

- A benchmark improvement needs the relevant metric, comparator, evaluation
  conditions, and uncertainty; one dataset does not establish universal superiority.
- A mechanism or causal claim needs evidence that separates plausible competing
  explanations; correlation alone supports an association.
- A theoretical claim depends on its assumptions and domain. Empirical examples
  illustrate a theorem but do not prove it. Use
  `../../hep-theory/references/mathematical-reasoning-and-proof.md`'s proof-status ladder to state how
  strong the theoretical evidence actually is (formal/analytic/perturbative/
  asymptotic/heuristic/numerical/empirical/conjecture) as a companion to the
  verdict below, which on its own doesn't say how strong the evidence is.
- A statistical claim (a significance, an exclusion, a correlation) needs the
  inference actually behind it, not just the reported number — check it
  against `../../hep-statistics/references/statistical-inference-for-physics.md`'s claim-calibration table
  before accepting the paper's own characterization of its result.
- A robustness/generalization claim needs tests over the variation named in the
  claim. Several plots from the same sample are not independent confirmations.
- An exclusion, null result, or absence-of-effect claim must retain its sensitivity,
  confidence/credible-level convention, and tested range.

## Verdicts and reporting

Use supported, partially supported, unsupported, or unresolved. Missing evidence
is not proof that a claim is false. For each gap, propose either narrower wording,
an existing evidence link, or a specific additional analysis; do not fabricate
results or perform new experiments merely to complete the matrix. Prioritize gaps
that affect the central conclusion and state the mapping's coverage.
