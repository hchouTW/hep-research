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
**pilot-checked-scope** for single-page statistical analyses with up to three planted defects, reviewed at R2 on the
measured host (three pilots, `docs/dev/hep-review/g2*-report.md`); no other scope is claimed, and 0.x records stay
experimental. R3 needs a committed claim-binding object with the evaluation chain
segment from the checkpoint the plan states, and the plan's capability fingerprint; layer 2 re-checks that the claim's
current state equals the bound state.
