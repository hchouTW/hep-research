# Evaluation, gold commitments and capability claims

Spec v9 section 15. Code: `scripts/hep_review_support/evaluation.py`. Pilot design draft:
`docs/dev/hep-review/pilot/protocol-draft.md` (development record).

## Four activities, never mixed

The exploratory spike (field needs, failure modes, cost, host behaviour) gives no capability claim and its instances
are exposed forever. Engineering regression tests the contracts. Review capability is measured on frozen, held-out
cases. Repeated trials measure variance; they are not new cases.

## Salted gold commitments

Before the first trial, for each gold or rubric: a random nonce of 32 bytes (`secrets.token_bytes(32)`) and the
commitment `SHA-256(nonce ‖ gold bytes)` written to the evaluation log. The gold and nonce are kept where reviewers
cannot read them (on this host that means off the host, held by the user); otherwise held-out isolation is recorded
unmet and the scores' use is limited. Scoring is private; the nonce is published only after every planned trial using
that gold has finished; a nonce published early makes later trials no longer held-out. A mismatch between gold and
commitment makes that batch unscorable (outputs kept). An unsalted digest of low-entropy gold is binding but not
hiding: candidate answers can be hashed one by one.

## Scoring rules

Report task-level, known-defect-level and predicted-finding-level denominators; keep every planned trial (timeouts and
invalid runs are not successes); report first-attempt, at-least-once and all-scheduled success separately. Author
self-assessment or an unverified model answer is not ground truth. A grader must pass calibration (a defect, a correct
control, insufficient information, a correct but different solution) before its scores count.

## Capability claims

States: experimental, pilot-checked-scope, evaluated-scope, needs-reassessment, retired. Today hep-review is
**evaluated-scope** for multi-step statistical analyses (up to 2,000 words, two interacting planted defects; G3:
detection 71/72, 95% CI 0.925-0.9997, false alarms 0/15) at R2 on the measured host; the single-page **pilot-checked-scope** claim is in **needs-reassessment** because
the packet text and validator changed after its pilots (`docs/dev/hep-review/g2*-report.md`, `g3-report.md`). No other scope is claimed, and 0.x
records stay experimental. R3 needs a committed claim-binding object with the evaluation chain
segment from the checkpoint the plan states, and the plan's capability fingerprint; layer 2 re-checks that the claim's
current state equals the bound state.

Claims are written and checked only through the lifecycle in `scripts/hep_review_support/evaluation.py`
(`make_claim`, `transition`, `reassess_if_changed`, `check_registry`):
- **Upgrades need new evidence of the right kind.** The engineering gate passed, the graders calibrated, and a
  report this claim has not used before. evaluated-scope needs a held-out evaluation, which may also lift an
  experimental claim directly.
- **Reassessment.** A changed fingerprint or a new failure type moves a claim to needs-reassessment. It comes back
  no higher than it was, with new evidence and, after a fingerprint change, the new fingerprint. The fingerprint is
  taken at the commit the claim was measured on. It covers the host capabilities (values and basis, not notes),
  the packet text, the validator, the code that reads material and submissions, the hash profiles, and the model
  alias with its date. The registry check replays every history through the state machine; it cannot observe a
  model change, which has to be declared.
- **Retired** is final.

The shipped claims are in `assets/claims.json`. What each scope supports, on what evidence, is in the
[support matrix](support-matrix.md).
