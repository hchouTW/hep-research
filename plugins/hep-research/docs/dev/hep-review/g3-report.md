# G3 report: evaluation (T08) of hep-review

Date: 2026-10-29.

| Commit | What it fixed in time |
|---|---|
| `63376643` | Protocol frozen, before the suite existed |
| `d992bcaf` | Commitments to 52 private files, before any dispatch |
| `9fd4faca` | All 60 results, before decryption |

Evidence: `g3/evidence/`. The revealed author files are in `published/`, with `.py` saved as `.txt` and `__pycache__`
left out; the grader runs are in `grader-runs/`.

## 1. Result

**Claim rule (`g3/frozen-protocol.md` §5): evaluated-scope**, with no usage warning. The engineering gate passed 60/60,
and the graders calibrated 12/12 on the Codex-written labels: one Claude calibration run (shared by the forward and reversed Claude scorers, the same model) and one Codex run.

| Measured (pre-registered) | k / n | Rate | 95% Clopper-Pearson |
|---|---|---|---|
| Defect detection, all (trial, defect) pairs | 71 / 72 | 0.986 | [0.925, 0.9997] |
| — interacting | 71 / 72 | 0.986 | [0.925, 0.9997] |
| — numerical | 26 / 27 | 0.963 | [0.810, 0.9991] |
| — particle-physics convention | 18 / 18 | 1.000 | [0.8146, 1.000] |
| C02 false alarm (controls) | 0 / 15 | 0.000 | [0.000, 0.2181] |
| C03 gap kept (missing input) | 6 / 6 | 1.000 | [0.541, 1.000] |
| C04 planning gap | 3 / 3 | 1.000 | [0.292, 1.000] |

**Miss rate: 1/72 = 0.014, 95% CI [0.0003, 0.075].** This is the first measured miss in four suites.

| Check | Result |
|---|---|
| Engineering | 60/60 digest-bound (every reviewer hashed with a separate command, and the g2x fabricated digest did not recur), R2, continuity verified, export recompute, no quarantine |
| Custody | 52/52 commitments verified after decryption; 20/20 Codex oracles pass |
| Grading | Claude forward, Claude reversed and Codex disagreed on 4 of 166 items. All 4 are finding items, so they never touch a defect verdict, and they are counted unadjudicated |

**Three denominators**:
- **Task level**: 20 cases, 60 trials, all completed. 59 successful. C01 first attempt 12/12, at least once 12/12, all
  scheduled 11/12.
- **Known defect level**: 72 (trial, defect) pairs, 71 identified with a valid reason, 0 unadjudicated.
- **Predicted finding level**: 94 C01 findings. 71 matched a gold defect unanimously; 19 are outside the gold (mostly
  findings that restate a consequence without a mechanism) and unadjudicated; 4 are grader disagreements.

## 2. The miss

**Trial `g3dd81149-t2`, defect D2.** The note releases an equal-tailed posterior interval while calling it the
shortest one.

- **What t2 did**: it found D1 (the prior Jacobian missing from the log transform) and the wrong probability mass. It
  then stated that the stated interval's endpoints have equal density, so "the shape is right". That is false under
  the note's own posterior. It is a miss with a wrong counter-claim, not an omission.
- **The other trials**: t1 and t3 on the same instance found D2. All three graders independently rejected t2's defect
  item.
- **Lesson**: a reviewer can verify one property against the wrong distribution, here the corrected posterior instead
  of the note's own, and conclude from that that a defect is absent.

## 3. What the claim covers, and what it does not

The claim is **evaluated-scope** (`assets/claims.json`, `hep-review/statistics-multi-step`). It covers:
- **Domain**: statistical analyses of 800–2,000 words, with two interacting planted defects each, including numerical
  and convention defects.
- **Format**: text + JSON.
- **Tier and host**: R2, on the Claude Code CLI on macOS.
- **Model**: the session model inherited by general-purpose subagents (alias recorded, not pinned).

**Limits that stay attached:**
1. **Exactly two defects per instance.** The brief allowed 2–4, and Codex chose two every time. There is no evidence
   beyond two defects.
2. **20 cases.** 60 trials over 20 cases; the intervals treat trials as independent. Per case, 11 of 12 C01 instances
   were fully detected on all three trials.
3. **Author self-assessment.** The Codex gold is carried by executable oracles, and Claude wrote the brief.
4. **Shared scratch folder.** One reviewer reported that its scratch file was overwritten by another reviewer's file.
   It noticed, discarded that output and reran under a unique name. Reviewers share the session scratch folder, so
   "no other evaluations seen" stays advisory (host profile H1). A packet that gives each reviewer a private scratch
   path would close this.
5. **Single-page claim: needs-reassessment.** Its fingerprint is taken at the commit where it was measured
   (`9c499a24`). The packet text (`1dfb15fa`) and the validator (`0bea7326`) changed after that, so the lifecycle
   moves it to needs-reassessment. G3 measured the current packet and validator, but on a different, harder scope;
   it does not re-measure the single-page scope.

## 4. T08 deliverables

| Deliverable | Where |
|---|---|
| Claim lifecycle (objects, fingerprint, transitions, registry check in CI) | `evaluation.py`, `tests/skills/hep_review/test_claims.py`, `assets/claims.json` |
| Regression suite (every published score re-scored from its evidence) | `tests/skills/hep_review/test_regression.py` (G2, g2h, g2x, g3) |
| Support matrix (T05–T07 unsupported, R3 unsupported here, other hosts not-run) | `skills/hep-review/references/support-matrix.md` |
| Held-out repeated evaluation | this report |
| Release | not part of G3: publishing needs external authorization (spec §18.3) |
