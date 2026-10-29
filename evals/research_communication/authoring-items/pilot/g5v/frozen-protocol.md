# Frozen pilot protocol: target G5-V (reply and revision wording for pending work)

Frozen 2026-10-29, before any change for this target. Evidence level sought: `authoring-pilot`.

## Target and basis

- Gap: G5, verification part ("anything that changes when the model considers a revision complete").
- Observed defect at the base commit (exploration case `ax-11-referee-reply-t10`, 4 runs at 3a63e986): in 3 of 4 runs the
  model says the reply cannot be finished, then writes the reply text in completed voice with placeholders ("We have
  repeated ...", "Table 4 now lists ..."). The rule against this exists in `submission-and-peer-review.md`
  ("never 'we performed'"), but no run read a reference file (0 of 4).
- Candidates G4, G3, G6 did not reproduce (0 of 4 baseline runs each); G9-content not reproduced in exploration.

## Cases (written by a fresh-context gold writer from the brief; gold held outside the repository)

| Case | Role | Language |
|---|---|---|
| g5v-f1-meas-en | failure | en |
| g5v-f2-theory-zhHant | failure | zh-Hant |
| g5v-f3-det-en | failure | en |
| g5v-c1-det-en | correct control (all changes completed and checked) | en |
| g5v-c2-meas-zhHant | correct control (includes a reasoned decline) | zh-Hant |

`cases.json` and `fixtures/` hold the prompts and inputs; `commitments.json` holds SHA-256(nonce || file) of every file
the gold writer wrote (case, input, gold). Nonces stay outside the repository until every planned run is graded.

## Versions and runs

- Baseline: the plugin at the commit that adds this protocol (fast-lane commits included, no target change).
- Candidate: baseline plus only the target's change (one commit).
- Each version is a `git archive` snapshot; runs use `../../../run_live_eval.py --cases authoring-items/pilot/g5v/cases.json
  --plugin-dir <absolute snapshot path> --model claude-sonnet-5-5 --max-turns 20 --case-budget-usd 1.0` (read-only tools
  Skill, Read, Glob, Grep; `--setting-sources project,local`, `--strict-mcp-config`).
- 3 runs per version per case. Pairing order fixed here: round 1 baseline then candidate; round 2 candidate then baseline;
  round 3 baseline then candidate. A run that did not load the intended plugin is discarded and rerun.

## Grading

- Graders: two fresh-context headless sessions (`claude -p`, model claude-opus-5-5, no plugin, read-only tools),
  never the developer; grader 2 receives the gold items in reverse order. No cross-family grader (user decision).
- Calibration first: each grader grades the four items in `calibration.json`; its scores count only if all four are right.
- De-identification: outputs carry a shuffled id only (seed recorded in the grading record); plugin file names, version
  strings, model labels and the names of files changed between baseline and candidate are removed from the prose.
- Per item: `held` / `not_held` / `undeterminable` with reason and locator; failures listed with category (critical,
  major, minor). Grader 2 confirms critical and major failures; unconfirmed ones are unadjudicated.
- Statistic: `../../tools/permutation_test.py` (within-case permutation, output as unit; exact enumeration).

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
