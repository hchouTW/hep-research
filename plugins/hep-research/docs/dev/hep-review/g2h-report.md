# G2 held-out follow-up report ("g2h")

Date: 2026-10-29. Protocol frozen at `862de947` before the suite existed (`pilot/g2h/frozen-protocol.md`). Gold
commitments `cacae2a4` (before any dispatch). All 45 results committed at `596b88e9` before the seed was revealed.
Evidence: `pilot/g2h/evidence/`. Raw run: `~/.local/state/hep-research/hep-review/g2h-store` and `.../g2h-pilot/`.

## 1. Result

**Both gates pass on all 45 planned trials.** The harder, uncued suite, held out for the gold, reproduced the G2
result.

| Gate | Criterion (pre-registered) | Result |
|---|---|---|
| Engineering | every trial completed, digest-bound or file-transfer, layer 1 recomputed from the export, continuity verified, no quarantine | 45/45 on every item; 45/45 at R2 |
| Scientific | C01 ≥ 12/15 trials and ≥ 4/5 instances; C02 false alarms ≤ 3/15; C03 ≥ 7/9; C04 6/6 | C01 15/15 (5/5 instances); C02 0/15 false alarms (0/6 on the differently written methods); C03 9/9; C04 6/6 |

Three denominators (spec 15.3):
- **Task level**: 15 cases, 45 trials planned, started, completed and successful. Per instance, first-attempt,
  at-least-once and all-scheduled success are all at the maximum for every type.
- **Known-defect level**: 15 C01 defect-trials, 15 identified with a valid reason. This is known-defect detection,
  not full recall.
- **Predicted-finding level**: 15 C01 finding groups graded, 15 verified correct, 0 wrong, 0 unadjudicated. There
  were no findings on any C02, C03 or C04 trial.

Per family, C01 and C02 were 3/3 for asymmetry, weighted yield, combination, line fit and count limit.

| Check | Result |
|---|---|
| Custody | `reveal` re-derived the gold from the user's seed and matched 15/15 commitments. The generator digest matches the frozen `e3136b55…`, and both salted calibration commitments verify |
| Grader | calibrated 10/10 (all four spec 15.4 categories). Forward and reversed scoring agreed on 15/15 |

## 2. Claim

**pilot-checked-scope, held out for the per-instance gold.** It is limited to:
- **Domain**: five statistics families (correlated propagation in an asymmetry, the uncertainty of a weighted yield,
  combination with a shared systematic, degrees of freedom of a weighted line fit, a classical Poisson upper limit),
  each with recomputation at 0.1%.
- **Format**: text + JSON.
- **Host**: the Claude Code CLI on macOS, with the session model as of 2026-10-29 (alias not pinned).
- **Tier**: R2, with "no other evaluations seen" advisory.

Together with G2 (`g2-report.md`), that makes 93 trials over 31 cases with no failure.

## 3. What the follow-up changed, and what it did not

**Removed, compared with G2:**
- **The criterion no longer cues the reviewer.** It names no defect class.
- **The topic no longer gives the answer away.** Each family appeared as both defect and control.
- **Equivalent forms were tested.** Six control trials used a correct but differently written method
  (2 sqrt(N1 N2/S^3); (sum w)/sqrt(N_eff)), and none raised a false alarm.
- **Claude did not hold the gold.** The user held the seed until after the trials. The outcomes were committed
  before the reveal.

**Still true:**
1. **Still at the ceiling.** 45/45 means this suite still does not separate a strong reviewer from a perfect one. The
   subtler defects (a one-count change in a Poisson limit, D and S treated as independent) were found 3/3 each. The
   honest reading: on single-defect, single-page statistical reviews of this size, the reviewers do not miss. Measuring
   a failure rate needs longer material, several interacting defects or a domain without a closed-form check.
2. **Authored on one side.** Claude wrote the generator, its oracles, the defect statements and the calibration
   labels. Reviewers and graders are the same model family. The user held the seed, not the problem design.
3. **The generator and calibration files were on the host** (outside the repository) during the trials. Reviewers
   were told to read only their packet, so their compliance was advisory. No report mentions reading anything else.
4. **Trials are not independent cases.** There are 3 per instance with identical packets: 45 trials, 15 cases.
5. **Protocol deviation:** the calibration grader and both scoring graders were dispatched together, not calibration
   first. The scoring grades would have been discarded had calibration failed. It passed 10/10, so nothing changes.

## 4. Record vocabulary (the schema-freeze rule, frozen protocol section 5)

No trial needed something the records cannot express:
- **0 invalid submissions.**
- **Defect plus missing input.** Combination-defect reviewers recorded `violated` with a finding and also listed the
  missing correlation under `missing_inputs`. The verdict did not depend on it, and the record held both.
- **Back-solving kept as a check.** C03 reviewers back-solved the missing input (rho ≈ 0.54) as a consistency check
  and still recorded `undetermined`. Nothing was adopted.
- **Remarks routed as suggestions.** Control reviewers raised curvature (line fit) and a sensitivity to rho as
  suggested obligations, not findings.
- **Two self-reported limits.** Reviewers noted an approximate `ended_at` and a wording slip they could not fix under
  write-once. Both are disclosures, and the submission fields carried them.

**Both freeze conditions hold.** The engineering gate passes, and nothing was forced into the wrong outcome.

## 5. Recommendation

- **Freeze `hep-review/1` / schema `1.0.0`**, as the separate, reviewed step the protocols require: a commit that
  changes the version constants and fixtures, then an independent review of the diff.
- **State the capability claim with caveat 1 attached.** The evidence supports "no misses on this class at this
  size", not a measured miss rate.
