# Frozen pilot protocol: target G5-V2 (reply wording for pending work, second attempt)

Frozen 2026-10-29, before any change for this target. Evidence level sought: `authoring-pilot`.

## Target and basis

- Gap: G5, verification part. Defect: reply drafts for pending work written as completed-voice templates. Basis: G5-V
  pilot (`../g5v/result.json`): confirmed in 2/3 and 3/3 baseline runs of two cases; exploration case
  `ax-11-referee-reply-t10` re-scored with scorer 1.2.0: 4/4 base runs. The G5-V candidate (a SKILL.md Never clause)
  showed no difference and was withdrawn; the G5-V gold hit a ceiling (11-12 of 12 on both sides).
- This attempt: the gold writer was asked for one F item per pending request (templates included), so the per-item
  score measures the defect directly.

## Cases

- ctrl_det_zhHant_decline (control, zh-Hant)
- ctrl_meas_en_allcomplete (control, en)
- fail_det_en_calo (failure, en)
- fail_meas_en_xsec (failure, en)
- fail_theo_zhHant_zprime (failure, zh-Hant)

`cases.json` and `fixtures/` hold prompts and inputs; `commitments.json` holds SHA-256(nonce || file) of every file the
gold writer wrote. Nonces stay outside the repository until every planned run is graded.

## Versions, runs and grading

As in `../g5v/frozen-protocol.md` (sections "Versions and runs" and "Grading"), with this pilot's case file
`authoring-items/pilot/g5v2/cases.json`: baseline = the plugin at the commit that adds this protocol; candidate =
baseline plus only the target's change; 3 runs per version per case in the order base, cand / cand, base / base, cand;
two calibrated fresh-context claude-opus-5-5 graders (grader 2 with reversed item and output order), de-identified and
shuffled outputs, `../../tools/permutation_test.py`.

## Decision rule (runbook C3.6, verbatim)

**Freeze:** this rule, case list, commitments, pairing order, the permutation statistic and calibration items are committed before the target's change. A correction before any candidate result is seen → recommit; after → report results under both old and new rules.

**Denominators (report all three):** task level (cases, runs, completions; first-attempt, at-least-once, all-scheduled success); gold-item level (held / total over (run, item)); predicted-finding level for review tasks (findings matched to gold defects; others unadjudicated).

**Output score:** number of `held` items in one output (`undeterminable` counts as not held; also report a sensitivity run excluding undeterminable items). Behavioural failure (timeout, unfinished) → all items not held.

**Main test — within-case permutation test, output as unit:** for each failure case, 6 outputs (3 baseline, 3 candidate). T = Σ_cases (Σ candidate scores − Σ baseline scores). Null: within each case re-split its outputs into the original group sizes in every possible way (20 per case; 8,000 for 3 cases); one-sided p = share of null T ≥ observed T. Implemented in `permutation_test.py` (C3.9).

**Target improved** ⇔ all of:
1. p(candidate better) ≤ 0.05;
2. leave-one-case-out: removing the case with the largest contribution, the remaining T > 0;
3. no critical-failure regression;
4. no correct-control regression.
("Candidate higher in ≥ 2 of 3 cases" is reported, not required.)

**Target regressed** ⇔ any of: p(baseline better) ≤ 0.05 with the reversed leave-one-case-out remaining T < 0; a critical-failure regression; a correct-control regression.

**Otherwise:** no difference / inconclusive.

**Critical-failure rule:** trigger when the candidate has a **confirmed** critical failure in a case where the baseline had none in 3 runs. Decide on **fresh reruns only**: default 3 new runs per version, regression if candidate ≥ 1 and baseline = 0; if budget allows 6 + 6, regression if candidate − baseline ≥ 2. Otherwise record a "pre-existing non-deterministic problem" in known issues (address or explain before delivery; not attributed to the change). Unconfirmed → unadjudicated, no rerun.

**Correct controls** (only "no regression / regression"): regression if a confirmed new major false alarm or F violation appears in ≥ 2 of 3 candidate runs and 0 of 3 baseline runs, or if the pooled F items of all controls give permutation p ≤ 0.05 in the direction "candidate violates more".

**Missing runs:** one-sided infrastructure failure (tool error, connection, plugin not loaded) → that side reruns once; both sides → each reruns once; if still missing, compute the case from the outputs present (permute only among them); a version with < 2 outputs → case "not completed", excluded from the main test, reported.

**Report:** by task type — the three denominators; improved / no difference / regressed / not completed; critical failures (including pre-existing); unadjudicated count; both sensitivity analyses; the result restricted to runs that loaded hep-authoring; never one combined score.

## Calibration numbers (runbook C3.10, verbatim)

Setup: 3 failure cases, 10–12 items, 3 runs per version, item difficulty shared by both versions (logit SD 1), per-output shared effect SD s; "0.6" = held probability of a median-difficulty item. Two independent simulations agree.

| Scenario | Per-item paired sign test (rejected) | Within-case permutation test (used) |
|---|---|---|
| no difference, s = 0 | 0.03–0.05 | 0.03–0.04 |
| no difference, s = 0.5 | 0.07–0.09 | ≈ 0.04 |
| no difference, s = 1.0 | ≈ 0.13 | ≈ 0.04 |
| no difference, 30% of outputs load no skill | ≈ 0.19 | ≈ 0.04 |
| moderate improvement 0.6 → 0.75, s = 0 | 0.57–0.67 | 0.53 (10 items) – 0.63 (12 items) |
| strong improvement 0.6 → 0.85, s = 0 | 0.97–0.99 | 0.95–0.98 |
| moderate / strong, s = 0.5, 12 items | — | ≈ 0.45 / 0.91 |

Critical-failure rule, overall false regression when both versions fail at rate r (triggering included): r = 0.05 → 0.015 (3+3) / 0.003 (6+6, diff ≥ 2); r = 0.1 → 0.04 / 0.013; r = 0.2 → 0.06 / 0.033. Correct-control first rule: ≈ 0.02 (r = 0.1) to 0.05 (r = 0.2).

These rules detect only moderate or larger effects; graders' systematic bias is reduced by de-identification but not excluded.
