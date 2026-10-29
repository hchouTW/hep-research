---
role: Theorist writing the related-work section of a review and answering its referee
skill: hep-authoring
archetype: contrast
use_case: a review paragraph comparing three synthetic EFT fits of one Wilson coefficient, and the reply to a referee point about one of them
---

Illustrative example: the three fits, their numbers and the referee report are invented; no published analysis is
meant. The rules it applies are in [scientific style](../../references/scientific-style.md), the review handoffs in
[reviewing](../../references/reviewer-style-assessment.md) and the reply wording in
[revision tracking](../../references/revision-impact-tracking.md).

## Scenario

A review chapter needs one paragraph on what is known about the Wilson coefficient c of a synthetic dimension-6
operator. The author has three literature records, each read in full:

- Fit A: c/Lambda^2 = 0.42 +/- 0.15 TeV^-2, linear in c (dimension-6 interference only), data up to 1 TeV;
- Fit B: c/Lambda^2 = 0.18 +/- 0.09 TeV^-2, linear plus quadratic terms, data up to 2 TeV;
- Fit C: c/Lambda^2 = 0.21 +/- 0.12 TeV^-2, linear plus quadratic terms, data up to 1 TeV, another PDF set.

A referee of the chapter then writes: "Is the uncertainty quoted for Fit B in Table 2 computed correctly? Its
profile-likelihood interval looks narrow." The author's change ledger has one row for this point: "check Fit B
interval, status: pending evidence, blocker: the likelihood scan has not been rerun".

## Common Weak Approach

> Three recent analyses have constrained the operator coefficient. Fit A found 0.42 +/- 0.15 TeV^-2, Fit B found
> 0.18 +/- 0.09 TeV^-2 and Fit C found 0.21 +/- 0.12 TeV^-2. The results are in good agreement, and their average,
> c/Lambda^2 = 0.23 +/- 0.07 TeV^-2, is the current consensus value.

Reply to the referee: "We have re-examined the Fit B interval and confirmed that it is correct; Table 2 has been
updated accordingly."

What goes wrong:

- Source by source instead of by question: the paragraph never says why the values differ.
- "Good agreement" hides the 1.4 sigma tension between A and B (difference 0.24 against a combined uncertainty of
  0.18, treating them as independent, which they are not if the data overlap).
- The average mixes a linear-only fit with linear-plus-quadratic fits and different energy ranges; it is not a
  measurement of one quantity, and a combination with correlations is a statistics task, not a writing one.
- "Consensus" is the author's judgement presented as the literature's.
- The reply asserts a check and a table update that the ledger lists as pending.

## Expert-Level Best Practice

Reasoning before writing. Organize by the question "what sets the spread in c?". The records give two conditions that
differ: whether quadratic (dimension-6 squared) terms are kept, and the highest energy used. Fits B and C share the
quadratic treatment and agree; Fit A drops it and sits higher. The energy range bears on the validity of the EFT
expansion, so it is a limit, not a nuisance. No combined value is written: comparable inputs and their correlations
would be a hep-statistics combination, which this chapter does not have.

> Three fits constrain the coefficient c of the operator, and their spread follows from how the EFT expansion is
> truncated. The two fits that keep the quadratic terms, B (0.18 +/- 0.09 TeV^-2, data up to 2 TeV) and C
> (0.21 +/- 0.12 TeV^-2, up to 1 TeV, another PDF set), agree with each other; Fit A, linear in c with data up to
> 1 TeV, gives 0.42 +/- 0.15 TeV^-2. The difference between A and the quadratic fits therefore measures the size of the
> neglected dimension-8 and squared terms as much as c itself. Fit B also reaches 2 TeV, where the expansion in E/Lambda
> is least controlled, so its smaller uncertainty is partly bought with a stronger validity assumption. We do not
> average the three values: they do not estimate the same quantity under the same truncation. In our judgement the
> quadratic fits are the more reliable guide below 1 TeV.

Reply to the referee, written from the ledger row:

> We thank the referee. The interval for Fit B in Table 2 is taken from the published analysis; we have not
> recomputed it. We will repeat the profile-likelihood scan for Fit B and report the result in the revised version; until
> then Table 2 marks the interval as quoted from the source.

Which handoff, and why:

- The referee asks for a judgement on one interval, so the check goes to hep-statistics (profile-likelihood interval),
  and its result comes back into Table 2 and the reply.
- If the editor asks for a recorded review of the fit, with review obligations and an assurance tier, that goes to
  hep-review; the chapter's own independent review covers the text, not the fit.
- The ledger row stays "pending evidence" until the scan exists; the reply describes completed changes only.

Verification after writing: every value and condition matches its literature record and its read level; the paragraph
says "in our judgement" where the author judges; the reply has no completed-voice sentence for the pending scan.

Limits of this example: it shows how to synthesize and how to word the reply; it does not decide the EFT validity cut
(hep-theory) or recompute the interval (hep-statistics).

## Key Takeaways

- Synthesize by the question the sources answer and name the conditions that make them comparable or not (here the
  truncation and the energy range), instead of listing values source by source.
- Separate consensus, disagreement and the author's own judgement, and label the judgement as such.
- Do not average results that do not estimate the same quantity; a real combination with correlations is hep-statistics
  work.
- Route the referee point by what it needs (a judgement: the owner skill; a recorded review: hep-review) and write the
  reply from the change ledger, so pending work stays pending.
