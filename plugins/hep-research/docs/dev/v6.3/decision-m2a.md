# Decision record G-M2a (v6.3 analysis-check programme)

Status: **awaiting the maintainer's decision.** Written 2026-10-16 at the end of Phase M2a (D05a, D05b, D05c, D06,
D11a, D17, D08 chain). Labels: **Confirmed**, **Inferred**, **Unresolved**. Convention: `README.md`.

## Analysis question

Is the chain slice (suite `counting-chain/v1`) affordable in context and maintenance cost, and does a model (M2b) or
run-lineage (M2c) slice have a concrete need, so that the programme continues past the chain slice?

## What the chain slice now catches (Confirmed, committed tests)

All 40 M2a V-case parts pass (`contracts/rules/registry.json`, status `passing`, each naming its tests). The M0
counterexamples are caught by the new suite while the old entry points still pass them:

| Counterexample | Old entry points | Chain suite |
| --- | --- | --- |
| V34: spec says unfolding, responses are for unfolding, recipe has no unfold step | all pass | `r-resp.response_use` violated (`check.response_use_conflict`) and `r-real.description` violated (`check.unrealized_correction`) |
| V21: same slot, two calibrations on one path | L2 catches it only inside one recipe | `r-rep.repetition` violated within a recipe and across `input_of` instances (V03, V49) |
| V37: scope-less correction against four instances | not expressible | unverified (`check.applicability_unbound`) until a spec `target_scope` or an `instance_mapping` declaration binds it; never broadcast |

The reduced synthetic positive case (O12) is complete and consistent (exit 0). CASE-CHAIN built from the
`ams-flux-ratio` example is partial (44 of 64 obligations decided, exit 3); its open items are real gaps in the
definitions, not checker failures: the effective-exposure operator's efficiency members are undefined in the coverage
contract (8), so their stage cannot be located (8), and the response use the spec claims (forward folding) is bound
nowhere (4).

## Measured context cost (Confirmed; method below)

| Quantity | CASE-CHAIN (4 instances) | Positive case (1 instance) |
| --- | ---: | ---: |
| hand-written context entries (roots / instances / bindings / declarations) | 4 / 4 / 0 / 4 | 1 / 1 / 0 / 0 |
| hand-written leaf fields | 96 | 15 |
| duplicated facts (root scope repeating its instance's scope) | 4 | 1 |
| obligations generated | 64 | 13 |
| declaration-based outcomes | 8 | 0 |
| draft context / frozen context (with inventory) / lock, bytes | 4140 / 28261 / 3255 | 810 / 5652 / 3255 |
| full report / one agent-summary page, bytes | 30529 / 4682 | 9668 / 546 |

Change propagation, adding a third period to CASE-CHAIN: 2 new instances, 2 new roots, 4 declarations edited (each
`instance_mapping` lists its instances), 1 scope-axis value; 35 leaf fields added.

Method: `measure_cost.py` (kept outside the repository; run with the case builders of `tests/contracts/v63_cases.py`)
counts the entries and JSON leaves of the draft context, compares root and instance scopes, freezes, evaluates, and
takes byte lengths of the written context and lock and of the indent-1 JSON of the report and of the first summary
page.

**Inferred.** Only the summary page reaches an agent's context (4.7 KB for CASE-CHAIN, under the 8 KiB page cap); the
report and the frozen inventory stay in files. Hand-written cost grows linearly with instances, and the declaration
fan-out (one list of instances per correction) is the part that grows fastest; a finite scope-set mapping in
`instance_mapping` would cut it, but needs its own case before it is added (A11).

## Maintenance cost (Inferred)

M2a added about 1,600 lines of checker code (`contracts/analysis_check.py` and nine files under `contracts/analysis_checks/`), four schemas (`analysis_bundle_v2`,
`check_context`, `semantic_lock`, `check_report`), one suite file and eight registered rules with 40 reason codes.
The D12a registry check, the reason-code test (every code a rule returns is registered) and the impact map keep
them aligned. The checker reads `contracts/recipe_semantics.py`, `contracts/validate.py` and the effect catalog: a
change there now also runs the six chain test modules (impact map).

## Concrete needs beyond the chain

- **Ratio (M2b, R-RATIO): concrete.** The `ams-flux-ratio` example's actual result is a ratio. Its cancellation claims
  (`livetime_and_cutoff`, `trigger_efficiency` "cancels", `background_subtraction` "independent") are exactly what
  R-RATIO checks, and the chain suite reports the ratio root as outside its mode (Confirmed: the spec's
  `extension.ratio`). Model cards are a second, independent need that depends on O03 (pyhf pairings).
- **Run lineage (M2c): not yet concrete.** M0 showed null bundle digests in the batch example and the
  `provenance_unrecorded` path, but no analysis in the checkout cites a campaign result through a result binding.

## Options

| Option | Do | Scope dropped |
| --- | --- | --- |
| **Continue to M2b** (ratio subset first) | D07 R-RATIO with the RATIO-FACTORS and RATIO-EVIDENCE cases on the AMS example; model-card part only once O03 is answered | M2c until a campaign-based analysis needs it |
| Continue to M2b and M2c | as above plus D05d run lineage | nothing |
| **Chain only** | stop slices here; D11b and M3 for the chain suite | ratio and model suites (never claimed as supported); run lineage |

## Recommendation (Inferred)

**Continue to M2b, ratio subset first; keep M2c paused.** The chain slice's cost is bounded (one summary page, linear
hand-written context), and the AMS example gives R-RATIO a concrete, testable need. Run lineage waits for an analysis
that cites a campaign result. D11b (snapshots) follows M2a in the plan whatever is chosen here.

## Owner

Programme owner: **Requires Confirmation** (still unnamed). Implementer: Claude Code session, 2026-10-16. This record
is not reviewed; author-only review would be `self-reviewed` (C15).

## Open questions touched in M2a

| ID | State |
| --- | --- |
| O05 | summary page cap 8 KiB (product default); measured pages 0.5–4.7 KB |
| O06 | bundle 2.0.0, check-context 1.0.0, semantic-lock 1.0.0, report 1.0.0 are proposals; the v1 bundle reader's refusal of v2 is tested, other readers are D09 |
| O09 | the coverage contract leaves undefined member sets unverified; CASE-CHAIN keeps them as negative cases |
| O12 | the original example stays unverified where its definitions are missing; the reduced positive case validates the mechanism |
| O16 | answered in `o16-agent-interface.md` |
| Contracts version | the spec keys use the capability `measurement:correction-keys-v1` instead of a contracts version change; the maintainer may still bump the minor at release |

## Decision

*(maintainer)* Option: — · Date: — · Conditions: —
