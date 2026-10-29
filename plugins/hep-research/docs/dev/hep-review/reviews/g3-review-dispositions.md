# G3 review: dispositions

An independent, fresh-context reviewer that is not the author read `77d88233..1c2846b8` (`g3-review.md`). It found 0
blockers, 4 majors, 7 minors and 2 nits, and confirmed that every published number matches `g3/evidence/score.json`.
Every finding was accepted. The fixes were written test-first in `tests/skills/hep_review/test_claims.py` (14 tests)
and `test_regression.py`.

| ID | Finding | Disposition |
|---|---|---|
| M1 | States could be skipped (experimental → needs-reassessment → evaluated-scope), and the same evidence was usable twice | Fixed. Only a live claim can need reassessment. It comes back no higher than it was. Every upgrade needs a report this claim has not used. Upgrade evidence has a `kind`: evaluated-scope needs `held-out-evaluation`, which may lift an experimental claim directly (the G3 claim now takes that one step) |
| M2 | `check_registry` did not apply the state machine | Fixed. Every claim is replayed from `initial_fingerprint_parts` through `transition()`, so a skipped state, a false gate, reused evidence or a fingerprint the history does not reach is reported. The docstring states that a fully self-consistent forged history cannot be detected from the file alone |
| M3 | Fingerprints were computed when the claims file was written, not when the claim was measured | Fixed. `make_claims.py` reads the host profile, packet text, validator and reader code from git at the commit each claim was measured on (`measured_at`): `9c499a24` for the single-page claim and `9fd4faca` for G3. As a result **the single-page claim is now needs-reassessment**: the packet text (`1dfb15fa`) and the validator (`0bea7326`) changed after its pilots. The G3 claim stays evaluated-scope, and its measurement-time fingerprint equals the current one |
| M4 | PR CI did not select the claim or regression tests for the files they guard | Fixed. New impact group `hep-review-claims-evidence` (`skills/hep-review/assets/**`, `support-matrix.md`, `docs/dev/hep-review/**`) selects `test_claims`, `test_regression` and `test_pilot_generator` |
| m1 | KeyError on a malformed claim | Fixed: reported as a malformed claim |
| m2 | No way back after a fingerprint change except a new claim | Fixed: `transition(..., parts=)` sets the new fingerprint when returning from a fingerprint-changed reassessment, and requires it |
| m3 | A model change is never detected | Documented. The check cannot observe the model, so a model change must be declared. The reference text says so |
| m4 | The fingerprint missed reader code and hashed host-profile notes | Fixed. `reader_digest` covers `materials.py` and `submissions.py`; `host_capabilities_digest` takes only capability values, their basis and settings. The criterion text is part of each suite's binding (its frozen protocol), not of the product fingerprint |
| m5 | The G3 report said three graders calibrated, but the Claude calibration was one shared run | Fixed: the report now says so |
| m6 | Test gaps: only 3 of 6 fingerprint parts varied, no forged registry cases, regression compared parsed JSON | Fixed: all 6 parts are varied, forged registry cases are tested (skipped state, false gate, re-fingerprinted, missing model), and the regression compares the printed bytes |
| m7 | The capability-matrix evidence column lacked `g3-report.md` | Fixed |
| n1 | Interval bounds were rounded to nearest | Fixed: they are rounded outward. G3 was re-scored: detection [0.925, 0.9997], false alarms [0, 0.2181]; the documents were updated |
| n2 | Importing `run_g3` changes the shared `CONTEXT_PREFIX` | Not changed. It is a development driver that sets its prefix on import, scoring does not read the prefix, and each pilot runs in its own process |
