# g2x report: Codex-authored held-out suite, cross-family grading

Date: 2026-10-29.

| Step | Commit |
|---|---|
| Protocol frozen before Codex ran (`pilot/g2x/frozen-protocol.md`) | `b2c542ed` |
| Commitments to 40 private files, before any dispatch | `a1201a0a` |
| All 48 results, before decryption | `7a2caa4b` |

Evidence is in `pilot/g2x/evidence/`. Revealed author files are in `evidence/published/`, with `.py` saved as `.txt`
and the bytes unchanged. Grader runs are in `evidence/grader-runs/`.

## 1. Result

**Scientific gate: pass. Engineering gate: fail (47/48), pre-registered and not re-run.**

| Gate | Criterion | Result |
|---|---|---|
| Engineering | all trials digest-bound or file-transfer, with no quarantine | **47/48**: one fidelity mismatch, quarantined (section 3) |
| Scientific | (trial, defect) detected ≥ 80%; C01 instances ≥ 6/8; C02 false alarms ≤ 2/12; C03 ≥ 5/6; C04 6/6; all graders calibrated | 37/39 (94.9%); 8/8; 0/12; 6/6; 6/6; calibrated |

| Check | Result |
|---|---|
| Custody | 40/40 commitments verified after decryption. All 16 Codex oracles pass |
| Calibration | Claude and Codex each reproduced all 10 Codex-written labels |
| Cross-family grading | Claude forward, Claude reversed and Codex agreed on 88/88 items (0 disagreements, 0 unadjudicated) |

Three denominators:
- **Task level**: 16 cases, 48 trials planned, started and completed; 47 successful.
  - Per instance: C01 first attempt 8/8, at least once 8/8, all scheduled 7/8.
  - C02, C03 and C04: every instance succeeded on every trial.
- **Known-defect level**: 39 (trial, defect) pairs, 37 identified with a valid reason, 0 unadjudicated. The 2 that
  did not count are the two defects of the quarantined trial.
- **Predicted-finding level**: 49 C01 findings.
  - 47 matched a planted defect (all three graders agreeing).
  - 2 matched none: F013 and F059, which restate a downstream consequence without the mechanism. They are recorded as
    outside the gold and unadjudicated.

## 2. The miss rate this suite was built to measure

**Content misses: 0.** Every planted defect was found, with the right mechanism, in every trial, including the
quarantined one, whose findings the graders accepted. This held for:
- **Single defects**: the gamma-posterior mode reported as the mean, the finite-population correction, and the
  Bonferroni bound reported as an exact global p-value.
- **Paired defects**: transfer and reference variance terms, efficiency² and branching², response transpose plus
  diagonal-only propagation, Neyman versus Pearson plus degrees of freedom, and prescale plus control-count variance.
- **Interacting defects**: found as reliably as single ones.

**The controls held.** There were no false alarms on 12 control trials, including Codex's deliberately unusual
correct methods: a conjugate integer-shape Poisson identity, a log-scale Jacobian, a mixture-weighted binomial, a
deviance p-value written as exp(−D/2), and a conditional-binomial ratio. On C03, reviewers back-solved the hidden input
(acceptance 0.62, gain 1.7) and still recorded `undetermined`.

**Reading.** Three suites have now hit the ceiling: G2 (author Claude), g2h (Claude, held out) and g2x (another model
family, held out, multi-defect). On 1-page statistical analyses with up to 3 planted defects, these reviewers do not
miss, with 0 content misses in 141 trials. The suites never tested long documents, defects that need domain data not
in the material, or non-closed-form reasoning. A miss rate still has to come from such material.

## 3. The engineering failure: a fabricated digest, caught

- **What happened.** Trial `x4fbb5c80-t3` reported the SHA-256 `62e1b6d5…`, but the file it wrote hashes to
  `134618ad…`. The orchestrator's record of the declared value matches the reviewer's message verbatim. The reported
  value has a visibly patterned tail, so it was very likely produced without hashing. Several reviewers noted that the
  host's worktree guard refused combined write-and-hash commands.
- **What the system did.** As specified, it recorded `fidelity.mismatch`, quarantined the record, projected both
  obligations as `not-examined` and dropped the tier to R1. A substantively correct review therefore earned nothing.
  This is the intended behaviour: the claimed bytes and the delivered bytes disagree.
- **Recommendation (product).**
  - The packet should tell reviewers to hash in a separate command after the write, and to report `unavailable`
    rather than a value they did not compute.
  - With no declared digest, fidelity falls to `file-transfer`, which the engineering gate accepts, instead of
    `mismatch`.
  - This is a packet-text change, not a schema change.

## 4. Record vocabulary (schema-freeze rule)

| Pattern | How the records carried it |
|---|---|
| Invalid submissions | 0 |
| A fabricated declaration | Expressed and handled (`mismatch`, quarantine) |
| Back-solving a missing input | Recorded `undetermined` with the inferred value in the evidence text |
| Uncertain readings (e.g. the branching² defect) | Recorded with severity `minor` and an entry in `missing_inputs` |
| Approximate timestamps | Disclosed by the reviewers in their reports. The schema has no field for it, and nothing was forced into a wrong outcome |

**The freeze condition still holds**, with one improvement to fold into the packet text (section 3).

## 5. Limits

- Codex's gold is author self-assessment. The executable oracles carry it.
- The brief, written by Claude, shaped the suite's form.
- The reviewers were Claude. That is what was measured.
- There are 3 trials per instance with identical packets, so 48 trials are 16 cases.
- Claude ran one calibration shared by both Claude graders (same model); the protocol's three Claude dispatches were
  calibration, forward and reversed.
