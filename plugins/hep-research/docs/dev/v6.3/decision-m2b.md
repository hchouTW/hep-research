# Decision record after M2b (ratio) and D11b (v6.3 analysis-check programme)

Status: **decided 2026-10-16: M3 for the chain and ratio suites, D09 first** (see Decision). Written 2026-10-16 after the ratio part of M2b (D07 ratio, D08 ratio
cases) and D11b, as decided at G-M2a (`decision-m2a.md`). Labels: **Confirmed**, **Inferred**, **Unresolved**.

## Analysis question

The ratio subset and snapshots exist. What comes next: the model-card part of M2b, shadow integration and the gate
(M3), or a pause?

## What exists now (Confirmed, committed tests)

- **Ratio subset** (`ratio-subset/v1`, `contracts/analysis_checks/rules.py`): V28, V44 and V45 pass. On RATIO-FACTORS,
  a common scalar factor cancels exactly, and a selection efficiency taken from different bins of one table leaves a
  residual in every bin. That residual equals a hand-computed oracle (`test_v63_d07.test_v44_factors`). Bare
  independence claims stay unverified; a validation record binding both operands, or a sourced declaration, satisfies
  them.
- **The AMS example's ratio claims**, with two ratio roots added to CASE-CHAIN:
  - the operands are compatible;
  - `livetime_and_cutoff` "cancels" is unsupported, because the term is not defined in the catalog;
  - `trigger_efficiency` "cancels" is unverified, because no calibration binds the factor on either side;
  - the three "independent" claims are unverified, because they are bare text.

  This is the O12 behaviour: the original example keeps these items unverified.
- **Snapshots and migration** (D11b): V19 and V57 pass.
  - A complete old snapshot reproduces the old verdicts after new definitions are installed.
  - A missing snapshot keeps the subject unverified, and a rewritten snapshot is invalid input.
  - A migration writes its completion marker last, and only after the new bundle verifies.
- **Registry:** 50 of 80 V-case parts pass (M1, M2a, the ratio parts of M2b, D11b). The rest belong to the model
  part of M2b, M2c and M3.

## Remaining options

| Option | Content | Precondition |
| --- | --- | --- |
| **M3 for chain and ratio** | D09 shadow integration and the reader refusal matrix (V31, V59), then D10: the advisory `permit.py` check and a written requirement for the custodian gate (V26, V32, V60, V65, V66) | approval of M3; D10 must not change the attestation or permit schemas without G-SCHEMA |
| M2b model part | D07 model-card subset (V06, V07, V08, V46, V47 and the model parts of six cases), CASE-MODEL | an answer to O03: which modifier–constraint pairings of the pyhf-combine adapter are supported |
| M2c run lineage | D05d (11 V cases) | a concrete analysis that cites a campaign result (none in the checkout, `decision-m2a.md`) |
| Pause | keep everything opt-in and unenforced | none |

## Recommendation (Inferred)

**Approve M3 for the chain and ratio suites, starting with D09.**

- D09 is unblocked: its dependencies D08, D11a and D12a are done. It turns the opt-in checker into reviewed shadow
  sidecars on the existing examples, which is the evidence G-ENFORCE asks for.
- D10 follows; with chain and ratio only, it checks the pre-execution report (C15).
- The model part waits for O03 and M2c waits for a concrete need. Neither blocks M3 for the suites that exist.

## Owner

Programme owner: **Requires Confirmation** (still unnamed). Before D10, O04 and O14 apply: the reviewers other than
the author, and the roles that may accept reports as evidence. Until they are named, D10 can only be built and
self-reviewed; no new gate condition is enabled.

## Decision

**M3 for chain and ratio, starting with D09**, 2026-10-16: the maintainer's instruction in the session was to follow
the recommendation. D10 follows D09; it may be built and self-reviewed, but no new gate condition is enabled while
O04 and O14 are open, and the permit and attestation schemas stay unchanged (G-SCHEMA). The model part waits for O03,
and M2c stays paused.
