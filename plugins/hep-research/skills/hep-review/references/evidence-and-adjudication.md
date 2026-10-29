# Evidence, findings, adjudication and carry-over

Spec v9 sections 3.2, 7.2, 7.3, 8.

## Three kinds of valid

Structural validity (JSON, schema, digests, bindings) is mechanical. Evidence admissibility (does it match the current
material and obligation; source, independence, qualification) follows the recorded policy. Scientific judgment needs
qualified judgment records; the schema never produces truth. Free text is never read as a ruling: two reasoning texts
that look opposed are not a conflict until a suspicion is recorded, and a recorded suspicion stays open until a
reasoned `conflict` judgment decides it.

## Findings

`candidate → supported / disputed / refuted`; `stale` when the material or closure changes; `retired-for-current` only
after a verified fix. Adoption follows the obligation's adoption policy, fixed at plan adoption: direct adoption by a
qualified reviewer only when neither verification nor a second method is required. The same policy holds for positive
results and discharges: a required verification needs a current `answer_assessment` from a qualified, non-author
verifier; a required second method needs two completed methods.

- Only qualified, non-author judges in submission, verification or adjudication records can adopt, refute or dispute.
  An author's disagreement is a `response`; submitting a fix is `response=changed`, `fix_check=pending`.
- Structured judgments asserting both supported and violated on the same obligation are a conflict, marked
  mechanically; it stays open until an adjudication rules on every opposing item. Two conflicting adjudications remain
  disputed.

## Disposition (computed, never stored)

| Problem | Effect |
|---|---|
| invalid envelope, role, actor, plan or material binding; locator digest not the snapshot's | whole record quarantined; raw submission kept |
| one evidence item corrupt (blob missing or changed) | that item and everything depending on it quarantined; unrelated findings kept |
| unknown dependency | whole record quarantined |
| fidelity `mismatch` | submission quarantined; its obligations not-examined; integrity partial-invalid |
| discharge for a refused reason, by an author, or on a self-reported basis | the discharge quarantined |

## Revisions and carry-over

Rejected at commit without an authorized change-request (T07, not implemented): deleting a required obligation or
making it optional; removing methods, evidence or independence conditions; decision_required true → false; looser
tolerances or adoption policy; any change of criterion or assumptions without an `equivalent_or_stronger` judgment;
retiring a required obligation or mapping it only to optional ones. A rename through `obligation_map` is checked field
by field; a split needs its targets together to keep every method and evidence requirement and a `scope_coverage`
judgment (a planning gap without it).

A result carries over as current only when its whole dependency closure is identical: the obligation's question,
criterion, assumptions and tolerances; the snapshots of all its targets, cited and located materials; its adoption
policy; the executor's tools and environment (re-observed in the new revision; `tools: []` needs no observation, a
missing tools field is unrecorded); and the closures upstream. Otherwise positives go stale (the obligation returns to
not-examined) and negatives become open follow-ups listed as unverified historical defects.
