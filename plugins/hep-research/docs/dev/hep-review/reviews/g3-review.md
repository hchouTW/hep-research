# Independent review: hep-review G3, range 77d88233..1c2846b8 (branch hep-review-g3)

Paths are relative to plugins/hep-research. I ran `python3 -m unittest tests.skills.hep_review.test_claims tests.skills.hep_review.test_regression`: 16 tests, all OK.

Counts: blocker 0, major 4, minor 7, nit 2.

## Numbers checked against g3/evidence/score.json (no discrepancy found)

I checked these against the evidence and found every one consistent:
- Defect detection: 71/72 overall, interacting 71/72, numerical 26/27, convention 18/18.
- Intervals: [0.925, 0.9996], [0.8103, 0.9991], [0.8147, 1.0].
- Controls and gaps: C02 0/15 [0, 0.218]; C03 6/6 [0.5407, 1]; C04 3/3 [0.2924, 1].
- Miss rate: 1/72, CI [0.0004, 0.075].
- Engineering gate: 60/60.
- Task level: 59 successful; C01 all scheduled 11/12.
- Findings: 94 findings = 71 matched + 19 outside the gold + 4 disagreements. 166 items = 72 defect + 94 finding, and all 4 unadjudicated items are finding items.
- Custody: 52 commitments, 20 gold files.

The same numbers appear, consistently, in g3-report.md, support-matrix.md, SKILL.md, evaluation-and-claims.md, claims.json, CHANGELOG, capability-matrix/map and README.

I compared the Clopper-Pearson code (run_g3.py:28-49) with scipy beta.ppf. It is correct to the 4 printed decimals.

## Major

### M1. The state machine lets a claim skip pilot-checked-scope through needs-reassessment, and upgrades need no new evidence
- **Where:** skills/hep-review/scripts/hep_review_support/evaluation.py:86-91
- **Defect:** `allowed_from` adds `needs-reassessment` as a source for both upgrade targets. needs-reassessment can be entered from any state, including experimental.
- **Failure scenario (reproduced):**
  - A new claim goes `experimental -> needs-reassessment (fingerprint-changed) -> evaluated-scope` with one evidence dict. It reaches evaluated-scope without ever being pilot-checked.
  - Likewise `pilot-checked-scope -> needs-reassessment -> evaluated-scope` with the pilot's own report.
  - Separately, `transition` accepts the same evidence object for consecutive upgrades. make_claims.py:76-78 does exactly that: the G3 report is cited as the evidence for both the pilot-checked and the evaluated step.
  - PLAN.md WP1 "Done when" says transitions refuse an upgrade that has no new evidence; that rule is not implemented.
- **Fix:**
  - From needs-reassessment, allow only a return to the state held before reassessment (read it from history), or require the next state upward from that one.
  - Refuse needs-reassessment from experimental.
  - Require upgrade evidence that is distinct from the previous step's evidence: a different report, or a held-out/evaluation marker for evaluated-scope.
  - Add tests for each case.

### M2. check_registry does not enforce the lifecycle, so it accepts claims that transition() would refuse
- **Where:** evaluation.py:117-147 (`_replayed_state` and the check at 141)
- **Defect:** the replay checks only that each step's `from` equals the previous `to`. The evidence check needs only a truthy `report`.
- **Failure scenario (reproduced, `check_registry(..., current=True)` returned `[]`):**
  - A hand-edited claims.json with `history=[{"from":"experimental","to":"evaluated-scope","evidence":{"report":"x"}}]`.
  - A claim whose evidence has `"engineering_gate": false, "graders_calibrated": false`.
  - Because the fingerprint is self-referential (recomputed from the stored parts), a forger can also recompute it.
  - The docs say claims are "checked only through the lifecycle"; the CI guard does not do that.
- **Fix:** have check_registry replay the history through `transition()` itself, starting from `make_claim` state with each step's evidence and reason, and report any ClaimError. Add a skip-in-history case and a false-gate case to test_registry_check_flags_bad_claims.

### M3. Fingerprints are minted when claims.json is written, not when the capability was measured; the pilot claim binds a configuration no pilot ran
- **Where:** docs/dev/hep-review/g3/make_claims.py:46 and :75 (`parts=E.fingerprint_parts(**MODEL)`, computed from the tree at write time)
- **Defect:** the single-page claim's evidence is G2, g2h and g2x, all committed before:
  - 1dfb15fa, which changed the packet text in coordinator.py;
  - 0bea7326, which froze validator 1.0.0 (the pilots ran under 0.1.0);
  - 5e8d847b, which edited host_profile.json.
- Its `packet_template_digest`, `validator_version` and `host_profile_digest` therefore describe a configuration that was never measured. The changes that the lifecycle says force needs-reassessment were absorbed silently at minting.
- **Failure scenario (forward-looking):** the same path launders any future change. Edit the packet or the host profile; test_shipped_registry_is_valid_and_current fails; re-run `make_claims.py g3`. The claim is rebuilt with the new fingerprint and walked back to evaluated-scope with no new measurement.
- **Fix:**
  - Record the fingerprint parts in the evidence at dispatch time (for example in results.json or commitments) and have make_claims read them from there, refusing if they differ from the current tree. Alternatively, make make_claims refuse to re-create an existing claim id.
  - Then the pilot claim should either be marked needs-reassessment (packet and validator changed after the pilots) or carry the pilot-era parts honestly. Since G3 ran on the current packet and validator, the G3 claim's parts look correct: coordinator.py and contracts are unchanged between d992bcaf and 1c2846b8.

### M4. PR CI does not run the new claim and regression tests for the files they guard
- **Where:** contracts/rules/registry.json impact map; no group covers the new dependencies.
- **Defect:** `contracts.rule_registry.impact` gives:
  - `skills/hep-review/assets/host_profile.json` and `skills/hep-review/assets/claims.json`: group agent-text. That group selects no tests.skills.hep_review module.
  - `docs/dev/hep-review/pilot/g2x/run_g2x.py`, `docs/dev/hep-review/g3/run_g3.py` and the evidence JSON: group docs-records, also no hep_review module.
- **Failure scenario:**
  - A PR that hand-edits claims.json, or changes host_profile.json (for example when recording H5/H6, which STATE says are pending), passes the required PR checks. test_claims' "registry check in CI" (g3-report section 4) does not run.
  - A PR that changes a scoring driver or committed evidence passes without test_regression running.
  - Both failures appear only on the post-merge full run on main. Merges go on required PR jobs only.
- **Fix:** add an impact group mapping `skills/hep-review/assets/**`, `docs/dev/hep-review/**/*.py` and `docs/dev/hep-review/**/evidence/**` to `tests.skills.hep_review.test_claims` and `tests.skills.hep_review.test_regression`. Also add a test in tests/tools/test_ci_plan.py.

## Minor

### m1. check_registry crashes on a malformed claim instead of reporting it
- **Where:** evaluation.py:144
- **Defect:** `c["fingerprint_parts"]["model"]` raises KeyError when a live claim lacks `fingerprint_parts` or `model`. The fingerprint mismatch for that claim has already been recorded, and the crash then loses every other problem.
- **Scenario:** reproduced, `crash KeyError 'model'`.
- **Fix:** use `.get` and append a problem.

### m2. A claim cannot be rebound after a fingerprint-changed reassessment
- **Where:** evaluation.py:78-100
- **Defect:** `transition` cannot attach new fingerprint parts. A claim re-upgraded after `fingerprint-changed` keeps the stale fingerprint, so `check_registry(current=True)` flags it forever and `reassess_if_changed` drops it again immediately. There is no legitimate path back except a new claim, and that path is what M3 launders.
- **Fix:** an upgrade out of needs-reassessment takes new parts, captured at the re-evaluation's dispatch, plus the evidence.

### m3. The model part of the fingerprint is never compared with anything live
- **Where:** evaluation.py:144-145
- **Defect:** the current check rebuilds the parts from the model alias and date stored in the claim, so a change of session model is never detected.
- **Overstatement:** evaluation-and-claims.md says a changed fingerprint covering "the model alias with its date" forces reassessment, and support-matrix.md:5-6 makes the same kind of statement.
- **Fix:** state in the docs that the model is recorded, not checked (unpinned alias), or pass the current alias in explicitly.

### m4. The fingerprint misses some code the capability depends on, and includes volatile prose
- **Where:** evaluation.py:47, 56-62
- **Misses:**
  - `reader_profile` and `hash_profile` are hard-coded labels, not digests. A behaviour change in materials.py (controlled reading) or in the hashing code leaves the fingerprint unchanged.
  - The obligation criterion text that reviewers actually receive (STAT_CRITERION, set by the dev driver run_g2h.py) is not covered.
  - The PLAN's 15.6 "prompt / tool" profile is not covered either.
- **Volatile:** `host_profile_digest` hashes the whole host_profile.json, including the free-text `evidence` notes. Editing a note, as 5e8d847b did, moves every live claim to needs-reassessment.
- **Fix:**
  - Hash the source of materials.py and the hashing helpers, and the obligation/criterion text.
  - Restrict the host digest to `{name: value, basis}` of the capabilities.

### m5. g3-report.md:16-17 says all three graders calibrated 12/12, but the two Claude graders share one calibration run
- **Evidence:** grader-runs/grades/calibration-claude-forward.json and calibration-claude-reverse.json are byte-identical to calibration-claude.json.
- **Defect:** there was one Claude calibration run and one Codex run. g2x-report.md:94 disclosed the same sharing; g3-report does not.
- **Fix:** add the same disclosure line to g3-report section 1 and the grading row.

### m6. Some tests do not cover what they claim
- **Fingerprint test (test_claims.py:51-56):** `test_any_part_change_changes_the_fingerprint` varies only 3 of the 6 parts (not model, reader_profile or hash_profile).
- **Registry test (test_claims.py:105-116):** `test_registry_check_flags_bad_claims` has no skip-in-history or false-gate case, so M2 passes unnoticed.
- **Regression test:** compares parsed JSON (`roundtrip`), not bytes, while PLAN.md WP2 says "byte for byte". This is acceptable, but the PLAN wording should match.
- **Fix:** extend the cases as described in M1 and M2.

### m7. Capability-matrix row does not cite the G3 report
- **Where:** docs/capability-matrix.md:226
- **Defect:** the row now states the G3 evaluated-scope numbers, but its evidence column still lists only g2-report.md, g2h-report.md and g2x-report.md.
- **Fix:** add `g3-report.md` and `assets/claims.json`.

## Nits

- **Interval rounding (run_g3.py:49):** the bounds are rounded to the nearest value rather than outward. The upper bound 0.99965 is printed as 0.9996, which is non-conservative by 5e-5. Use floor for the lower bound and ceil for the upper.
- **Import side effect (run_g3.py:22):** importing run_g3 sets `run_pilot.CONTEXT_PREFIX = "g3"` for the whole process. In test_regression's process, run_g2x/run_g2h prepare would then use g3 contexts. Scoring is unaffected and the tests pass, but the mutation is a trap for any future test of prepare/assign.
