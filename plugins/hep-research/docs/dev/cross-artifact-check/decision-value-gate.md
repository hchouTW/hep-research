# Decision record: value gate (DR-13)

Status: **design adopted 2026-10-22 (DR-13); thresholds proposed, awaiting the maintainer's confirmation before any
measurement.** Architecture `cross-artifact-check-architecture.en.md` section 10. Labels: **Confirmed**, **Inferred**,
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

*(To be filled in by the maintainer: confirm or change the thresholds above, with the date. No measurement starts
before this entry.)*
