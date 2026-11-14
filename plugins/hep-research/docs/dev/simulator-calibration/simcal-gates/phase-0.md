# Simulator calibration gate record: phase 0

**Phase 0 (Abstract model and contracts): both gates pass.** The exhaustive Appendix C tests ran as a registered Slurm campaign at the fixed code. The named cases of §15.3 and the P4 negative test pass in the unit suite. The three fixtures derive candidate methods and reachability. An independent review found 4 major and 11 minor defects; all were fixed before the gate run, without a change to Part B.

| Field | Value |
| --- | --- |
| Phase | 0 (Abstract model and contracts) |
| Worktree | `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/hep-research-simcal-phase-0` (moved from `../hep-research-simcal-phase-0` at the user's choice; execution log) |
| Branch | `simcal/phase-0`, from `origin/main` 5c2d1c7c (hep-research 0.65.1) |
| Commit | Gate campaign at `c3b8eeae`; unit tests and repository checks at `652d0ddf`. Between the two only documentation changed (`core-stats-guide.md`, `docs/reference-inventory.*`). Every campaign item records the SHA-256 of the files that decide it, and these equal the files at `652d0ddf` |
| Task-card SHA-256 (as registered) | `06fb186030ea143b53c413514f81c35a69d97baf379e84e234f2c136fe47f5ee` (registered before the gate run; later registrations change the execution log only) |
| Environment | Login host: Python 3.13.2 (conda env `ml`), `TMPDIR` on the private ceph folder. Batch: NSTCCore Slurm, partition `edr1-al9_short_serial`, account `ams`, interpreter `/ceph/work/AMS/hsinyichou/hep-detector-reco/env/py313/bin/python3.13` (3.13.18). Phase 0 code uses the standard library only |
| hep-research and g4sim versions | hep-research 0.65.1 base (`CORE_VERSION` 1.13.0, contracts 3.27.0); g4sim not used (§17: phases 0–2 do not depend on g4sim) |
| Date | 2026-11-10 |

| Gate (§17, split at semicolons) | Threshold as registered | Observed | Verdict | Evidence |
| --- | --- | --- | --- | --- |
| The negative tests of the contract, use and grade rules (the exhaustive tests of Appendix C and the named cases of §15.3) and of P4 pass | Appendix C: all 69 campaign items present once and `ok`, with the reference's hash and identical provenance. **agree**: zero disagreements over 31,593,216 cases. **invariants**: zero violations. **lookup**: zero disagreements over 2,754,048 cases. **mutants**: all 24 reference mutants caught, and mutant 25 caught at least once. Named cases: every test listed in the card's case-by-case list passes, each negative test showing its expected code or grade | agree 31,593,216 cases, 0 disagreements; invariants 26,647,296 combinations checked, 0 violations; lookup 2,754,048 cases, 0 disagreements; 24/24 mutants caught; mutant 25 caught on 408,576 cases; `--summarize` status `ok`. Named cases: 128 tests in the seven calibration modules pass | pass | Campaign `campaigns/phase0-appendix-c-2/` (private ceph folder): array 7554757 (69 jobs, all COMPLETED, ≤ 58 s, ≤ 39 MB, 0.44 core-hours), `gate-summary.json` (SHA-256 `13e2faaf…`), item outputs `campaign/outputs/c00NN/`; unit modules `tests/core/test_calibration_{use,deps,chain,data,contract}.py`, `tests/contracts/test_calibration_schemas.py`, `tests/skills/test_calib_scripts.py` |
| the three fixtures can derive candidate methods and reachability | ECAL, RICH and tracker give a candidate method for every parameter, and P4 passes | All three: every parameter has a candidate, P4 `passed`; the §15.3.18 P4 item (both modules) holds on ECAL and tracker | pass | `tests.core.test_calibration_chain.Fixtures`, `tests.skills.test_calib_scripts.Scripts.test_calib_chain`; fixtures `core/calibration/data/{ecal,rich,tracker}.json` |

## This phase's tests

| Test (§15) | Kind | Caught / passed | Evidence |
| --- | --- | --- | --- |
| Appendix C exhaustive (agree, invariants, lookup) | positive, exhaustive | passed, as above | campaign 2 |
| Appendix C mutants 1–24 (reference) and 25 (lookup with C.2 only) | negative | each caught | campaign 2 item `mutants 1/2000`; lookup items |
| §15.3.1 P4 (subgraph, only single-photoelectron injection) | negative | caught: P4 `failed`, light yield and PDE unconstrainable, remedy level contract | `chain.ReferenceCoverage.test_15_3_1_p4_subgraph` |
| §15.3.1 P7 alternative in parameter-shift form | negative | caught: `validation.alternative_shift` | `contract.OtherClauses.test_15_3_1_p7_parameter_shift_alternative` |
| §15.3.2, 15 contract rules | negative | each caught by its finding code | `contract.ContractRulesSection15dot3dot2` (card list) |
| §15.3.3, 3 cases | negative | caught | `data.IngestionAndSealing`, `contract.DataReleaseAndSharing.test_15_3_3_observed_only_statistical` |
| §15.3.11, 7 cases | negative | caught: not opened, no read and no record, the right C.1 inputs | `data.OpeningPreconditions` |
| §15.3.12, 11 phase-0 cases and the exhaustive lookup | negative and positive | caught / passed | `use.NamedCases.test_outcome_already_determined_cases`, `use.OutcomeAlreadyDetermined` |
| §15.3.13, 7 cases | negative | caught | `data.ReadsAndEligibility`, `contract.DataReleaseAndSharing` |
| §15.3.14, phase-0 cases | negative | caught | `data.FailureRecords`, `use.IncompleteAggregation` |
| §15.3.15, 5 cases | negative | caught | `use.NamedCases.test_grade_rule_cases`, `use.IncompleteAggregation.test_15_3_15_g8_fails_later_stages_not_applicable` |
| §15.3.17, hash citation and the four use cases | negative | caught | `deps.Roles.test_15_3_17_numbers_instead_of_hashes`, `use.NamedCases.test_use_rule_cases` |
| §15.3.18, P4 of both modules | positive | passed | `chain.Fixtures.test_15_3_18_p4_both_modules` |
| §15.3a, phase-0 cases (lineage, failure records, acyclic ids, `incomplete` aggregation) | negative and positive | caught / passed | `data.Lineage`, `data.FailureRecords`, `deps.Versions`, `use.IncompleteAggregation` |
| Schemas (the seven objects, contract, release, plan, result with D11, ledger, fixtures) | negative and positive | passed | `tests.contracts.test_calibration_schemas` |

Cases that §17 or the owning script place in a later phase are listed with their phase in the card ("Thresholds and test designs", item 2).

## This phase's thresholds (§8.7)

| Row | Calibrated value or `provisional-thresholds` | Evidence |
| --- | --- | --- |
| none | §8.7 has no row for phase 0; the gate has no tolerance to calibrate | card |

## Review (Section E4, step 10)

- **Reviewer:** one fresh-context subagent, approved by the user ("Yes, one reviewer"), working under hep-review/1 and aiming at tier R2. It read the diff at `24a8bf6a` and Part B, and ran the unit tests read-only. Date 2026-11-10. Report: `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/review/phase-0-review.md` (SHA-256 `1e6ebf7c119ae4199e7d41197a615937e070c3168ac0176a3a71b19b3121ff94`).
- **Findings:** 4 major, 11 minor, 5 notes.
  - Majors: F1, the "outcome already determined" lookup accepted inconsistent undecided inputs. F2, the rule-0 `incomplete` aggregation was missing. F3, the D5 rule could be bypassed and its test was inconsistent with §2.1. F4, the §15.3 named cases were not enumerated, and some tests were missing or could not fail.
  - Minors: F5, no sharing recheck before opening. F6, the mutant evidence was outside the campaign. F7, nested fields were dropped from version payloads. F8, ownership of the N_decl and has-value decisions. F9, recomputation was refused. F10, no provenance or totals in campaign items. F11, variation flags not compared. F12, a declared release hash was trusted. F13, lineage was not derived in a §15.3a test. F14, ECAL and tracker lacked per-module parameters. F15, the result schema allowed a missing own grade without its resolutions.
- **Resolution:** all 15 fixed in `c0870a0a` (and the card's design tightened, registered `06fb1860…`), none changing Part B. Notes N1 and N2 are stated in the card's test design. N3 is kept as a recorded reading and reported to the author. N4 and N5 are recorded, and `--vmode` is now validated. Campaign 1 (at `24a8bf6a`, all items `ok`) is superseded by campaign 2 at the fixed code.
- The achieved review tier is stated by the coordinator of the record, not by this gate record.

## Repository checks (E4 step 7)

- `tools/check_layering.py`, `tools/check_wiring.py` (also `--since origin/main`), `tools/check_packaging.py`, `tools/check_naming.py`: pass at `652d0ddf`.
- `tools/run_all_checks.py --jobs 4 --no-cli` at `652d0ddf`: 7,319 unit tests in 547 modules: 7,018 passed, 298 skipped (slow or optional dependencies), 3 failed, all three listed below; of the 34 checks 30 pass, 2 fail (`unittest` with those 3 tests, and `ams_optional`, the same `test_revocation` failure), 2 skipped (`--no-cli`). Run record `.simcal-work/checks3/check-run-2026-11-10T124918Z.json` (worktree, untracked), 75 minutes.
- Failing also on a clean `origin/main` snapshot, so not caused by this phase:
  - `tests.contracts.test_revocation` (2 tests): group-writable and sticky-directory checks under ceph's ACL semantics. This is also the failure of `ams_optional`.
  - `tests.skills.hep_computing.test_event_display_templates.PythonPipeline.test_export_bundle_check` (1 test).
- `contracts/validate.py`: phase 0 writes no `artifacts_dir` artifact; its records are checked against their schemas by `test_calibration_schemas`.

## Open items carried to the next phase

- **Phase 2 (§17 placement bullets):**
  - the locking-stage checks that need model quantities (clause 9 items 2, 3, 4 for N_exp, 8, 12, 13; the standardized N_d and N_d,c decisions), listed under `deferred` by `calib_contract check`;
  - the `calib_validate.py` cases of §15.3.14;
  - the data-side and has-value checks at opening;
  - propagation (§15.3.17);
  - the P7 decision over alternatives (§15.3.12 case 10);
  - the P3 part of §15.3.18;
  - Poisson and binomial blocks (refused until the phase-2 engine);
  - registering `calibration-result` as an envelope artifact type (a contracts minor version).
- **Phase 1:** `calib_contract.py preflight` (A0); the 0.1σ_tot^design bound of D37 (A7).
- **Phase 3:** the g4sim model identity in `calib_contract check`; candidate methods from §11.4 Table 2.
- **Phase 4:** upstream invalidation, including the §15.3.14 "re-judged upstream" case.
- **For the author** (not blocking):
  - the D41 residue (the determining region of tail functionals);
  - review note N3 (the methods of a parameter acting on several nodes are those every node allows);
  - the lookup tests that Appendix C says are "added to the reference implementation" live in `test_calibration_use.py`, because the reference is fixed by its hash;
  - applying approvals A6 and A7 in Part B (a new part of Appendix E).
- **For the maintainer:**
  - the naming waivers for the copied package tools (`tools/naming_known_gaps.json`, pending maintainer approval);
  - the guide trim in `core-stats-guide.md` (the user's choice);
  - the local timings of the seven new test modules until the next CI refresh.
