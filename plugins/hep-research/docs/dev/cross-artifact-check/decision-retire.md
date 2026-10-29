# Decision record: retire the cross-artifact check

Status: **decided 2026-10-29: option A (retire)** (see Decision). Labels: **Confirmed**, **Inferred**,
**Unresolved**.

## Analysis question

The value gate found no error the checker catches that closure tests and contract checks miss (I = 0 of 28, measured
twice; `decision-value-gate.md`), and the decision was Shrink: keep `counting-chain` (frozen) and `ratio-subset`. With
hep-review now the plugin's recorded review, should the remaining checker be retired, its review knowledge kept as
review questions, and nothing of hep-review changed? Architecture section 13.4 does not trigger on its own:
`review_measurement_spec.py --check-bundle` is still a non-test caller. Section 13.3 Stop freezes but does not remove.
This is therefore a new decision.

## Evidence (Confirmed unless labelled)

- No workflow, skill or example runs the check (architecture F2, F3). Its only entry is the opt-in
  `--check-bundle` flag. Since 0.28.0 every report is pre-execution, and the custodian requirement's default policy
  refuses pre-execution reports (`custodian-gate-requirement.md`): no report can count toward formal use by default.
- hep-review imports only `contracts.hep_review` and `contracts.schema`. Its capability fingerprint covers the host,
  the packet text, the validator, the reader code, the hash profiles and the model, none of which this change touches.
- Obligation fields (`question`, `criterion`, `applicability`, `required_methods`, `evidence_requirements`,
  relative `tolerances`) are open text, so each of the 12 shadow rules translates into a hep-review obligation
  without schema changes. Reviewers read only the files their packet names, so the questions must be written where
  the coordinator builds obligations from them: the owner skills' references.
- Shared code the checker programme introduced stays: `rule_registry.py` and `contracts/rules/registry.json` (the CI
  impact map of `tools/ci_plan.py`, the legacy L2 rules, the state mapping `naming_registry.py` uses),
  `source_digest.py` (naming predicate digests), `semver.py` and `resolve.py`, `contracts/vocab/effects.json` with
  its catalog check, `validation_record.json` (written by `propagate_scale_distortion.py`), `custody.py` (the profile
  custody inventory), the capability `measurement:correction-keys-v1` and the v2 bundle digest rule in
  `attestation.py` (existing attestations stay verifiable).
- A function-level trace of every test in the 22 checker-named modules separated the tests of shared code (kept,
  renamed) from the tests of the checker (removed).

## Options

| Option | Cost | Recommended |
|---|---|---|
| A. Retire: translate the rules into review questions in hep-measurement and hep-statistics, remove the checker, refuse its entry points with the reason | one release; hep-review unchanged | **yes** |
| B. Stop (section 13.3): freeze, label experimental, add the questions only | keeps the test modules, suites and registry entries | no |
| C. Keep the report as hep-review material | hand-written bundles; the five states cannot be explained on the hep-review side without changing it | no |

## Owner

hchouTW.

## Decision

**2026-10-29, maintainer choice in the session ("A. Retire").** Option A is adopted as written: the checker is
removed, its rules are kept as review questions in hep-measurement and hep-statistics, and its entry points refuse
with the reason. Conditions: hep-review stays unchanged; the last release with the check is 0.47.x; the release that
ships this bumps `CONTRACTS_VERSION` and records the changed assertions in `VALIDATION.md`; the refusing stub, the two
hidden `review_measurement_spec.py` flags and `permit.py check-report` are removed in the following minor release.
