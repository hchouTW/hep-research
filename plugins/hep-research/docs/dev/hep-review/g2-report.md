# G2 gate report: hep-review narrow pilot (spec v9 §15.5, §18.3)

Date: 2026-10-29. Protocol frozen at commit `d987d4e2` before the first trial (`pilot/frozen-protocol.md`). Evidence
in `pilot/g2/`; the raw run (store, packets, drop files, host dispatch records) in
`~/.local/state/hep-research/hep-review/g2-store` and `.../g2-pilot/`.

## 1. Result

**Both gates pass on all 48 planned trials.**

| Gate | Criterion | Result |
|---|---|---|
| Engineering | every trial completed; fidelity ≥ file-transfer; layer 1 recomputed byte for byte from the export; head continuity verified; no quarantine | 48/48 completed, 48/48 digest-bound, 48/48 export recompute, 48/48 verified, 0 quarantined, 48/48 at R2 |
| Scientific | C01 ≥ 10/12 trials and ≥ 3/4 instances; C02 false alarms ≤ 2/12; C03 ≥ 10/12; C04 12/12 | C01 12/12 (4/4 instances), C02 0/12 false alarms, C03 12/12, C04 12/12 |

Three denominators (spec 15.3):
- **Task level**: 16 cases, 48 trials planned, started, completed and successful; 0 not started, timed out, tool
  error, invalid, abstained or unscorable. Per instance, first-attempt, at-least-once and all-scheduled success are 4/4
  for every type.
- **Known-defect level**: 12 C01 defect-trials, 12 identified with a valid reason. This is known-defect detection,
  not full recall.
- **Predicted-finding level**: 12 C01 finding groups graded, 12 verified correct, 0 wrong, 0 unadjudicated. Findings on
  other instances: none on C02, C03 or C04.

Grader: calibrated 8/8 on the committed labels before scoring; the scoring was done twice, in forward and reversed
order, and the two runs agreed on 12/12 items (no grader instability). Salted commitments: 19/19 verified after the
trials, and the nonces are published in `pilot/g2/nonces.json`.

## 2. Claim

**pilot-checked-scope**, limited to:
- **Domain and method**: statistical treatment of inverse-variance weighted means, binomial efficiency uncertainties
  and propagation for products of anticorrelated quantities, with recomputation of the stated numbers (0.1% tolerance).
- **Format**: text + JSON.
- **Host and model**: the Claude Code CLI on macOS, with the session model as of 2026-10-29 (the alias was not pinned).
- **Tiers**: R2 records under the recorded conditions. "No other evaluations seen" was advisory: the reviewers were
  instructed not to read other evaluations, and this was neither observed nor enforced.
- **Custody** (U1 option b): gold was oracle-checked but **not held out**.

No capability is claimed beyond this. In particular, the result says nothing about other domains, harder defects or
other hosts, and nothing about held-out performance.

## 3. Caveats the result does not hide

1. **The suite was at the ceiling.** 48/48 shows the pipeline and the reviewers handle this narrow family. It does not
   measure difficulty or discriminate between reviewers. The defects are textbook-level, and the `O-stat` criterion
   text lists the classes to check (estimator, weights, correlations, degrees of freedom, propagation), which primes
   the reviewer. A harder or less-cued suite is needed before any broader claim.
2. **Not held out, and authored on one side.** Claude generated the instances, wrote the oracles, held the gold, wrote
   the 8 calibration items and labels, and ran the reviewers and graders. All of these were the same model family on a
   shared filesystem, and author self-assessment is not ground truth (spec 15.4). The deterministic oracles, which the
   user approved, carry the gold.
3. **C04 is mechanical by construction.** REQ-2 is unmapped in every C04 plan, so 12/12 checks the projection, not the
   reviewers. In practice the reviewers noticed nothing about REQ-2, because the packet does not show the intent.
4. **Trials are not independent cases.** There are 3 trials per instance with identical packets, so the 48 trials
   amount to 16 cases.
5. **C03 success rests on a keyword match** (pre-registered): every C03 trial named sigma_3 under `missing_inputs`.
6. **Observed reviewer behaviour worth keeping.** Several C02 reviewers raised near-boundary interval concerns
   (Wilson or Clopper-Pearson) as suggested obligations rather than findings, so no false alarm resulted. Several C03
   reviewers back-solved the missing sigma, explicitly as a consistency check only, and did not adopt it.

## 4. What was found and fixed by running the pilot

The live R2 path exposed one product bug before the first trial: snapshot capture times in nanoseconds exceeded the
metadata integer range, so a manifest built from a snapshot could not be committed. The fix stores them as decimal
strings (commit `6f7936a7`, with the test written first). The packet also gained an instruction to use the
obligations' exact method and evidence names (in the frozen-protocol commit).

## 5. Schema 1.0.0

Spec §5.3 and the task file allow freezing `hep-review/1` / `1.0.0` after G2 passes. The frozen protocol made this
**a separate, reviewed step**, so it is not done here. Given caveat 1, freezing it is a decision for the maintainer.
