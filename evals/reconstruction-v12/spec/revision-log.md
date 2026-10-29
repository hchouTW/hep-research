# v12.1 spec copy — revision log

The spec copy in this folder (`v12-en-0-core.md`, `v12-en-1-methods.md`, `v12-en-2-control.md`,
`v12-en-3-delivery.md`, `v12-en-reference-model.py`) starts from Parts I–IV and Appendix A of the task file
`hep-research-reconstruction-v12-en-task.md` (SHA-256 `3c041bc1…ac15b`) and revises them for the findings of the first S0
round (runbook 0.5.2 item 6). For later stages this copy governs (runbook 0.5.2 item 6). This log contains evaluations
and is **not given to S0 reviewers**.

S0 round 1: hep-review context `s0-reconstruction-v12`, target R2, achieved R2; N1–N5 all violated; 34 findings
(8 major). Finding ids below are `<obligation>-F<n>` as the reviewers numbered them (records `rec-asg-<k>-F1-<n>`).

No fix loosens an acceptance condition, gate, or rule that judges the Agent's own work (runbook 0.5.2 item 6, Core §0.4
item 10), with the two items marked **for human attention** below, which change a structure rather than a judging rule
and are listed as open decisions in the final report.

## N1 — control layer and model

| Finding | Sev. | Change | Where |
|---|---|---|---|
| N1-F1 | major | A step added by a later contract may not carry confirmation-not-required, same-identity reruns, allowed not-applicable, nor join an existing family; otherwise the contract is not at least as strict. Model: `contract_at_least_as_strict`; scenario t72; mutation “added step may take reserved values” | Control §1.1 (confirmation required), §1.2 (new row “each step N adds”, family row), §6 |
| N1-F2 | major | **Check before recompute**: for a checked step, admission rejects another computation while any earlier artifact of the step lacks a counted result for a required check; publish and the deliverable status record the number of artifacts on the dependency chain. Model: `unchecked_artifacts`, `step_artifacts`, publish `chain_artifacts`; scenario t73; mutation “recompute before checking the earlier artifact”; scenarios t28 (`_chain`), t34, t60, t66 reordered to check each copy before the next (their assertions unchanged in intent) | Control §1.2, §4.5, §5.1 item 6, §5.4; Delivery §5.1 |
| N1-F3 | minor | Attempt ids are unique across intents and admission rejections. Model: `attempt_id_taken`; scenario t74; t67 uses a fresh id after its rejected admission; mutation “rejected attempt id reusable” | Control §2 (intent) |
| N1-F4 | minor | “Under-reporting cannot buy quota” limited to receipts that carry usage; under M1 without metering the report states the budget was not enforced against actual usage | Control §5.1 item 2 |
| N1-F5 | minor | t44 comment corrected (infeasibility at freeze does not set the field to no) | model t44 |

## N2 — transition period and Delivery

| Finding | Sev. | Change | Where |
|---|---|---|---|
| N2-F1 | major | A transition check-result counts only when its check, criterion and target digests are bound to the check run's record (program hash, criteria file in the input manifest, target outputs staged with their recorded hashes) and equal the declared check identity of the attempt registration line | Control §7.2 (new row “declared check identity”, check-result row), §7.4; Core §5.4 item 2; Delivery §5.1 |
| N2-F2 | minor | The attempt registration line carries the read list | Control §7.2 (new row) |
| N2-F3 | minor | One canonical JSON form for every digest of a JSON object | Control §4, §7.2 output row |
| N2-F4 | minor | Termination: the runner's own termination field governs once BUG-04 is fixed (`unconfirmed` → unknown); a step the runner refused before starting is “not started” = failed with termination confirmed, no outputs (as `not-submitted`), citing the runner's output digest. **For human attention**: this replaces a literal reading under which such attempts were unknown until a human abandon; it matches Delivery §3.1 `not-submitted` | Control §7.2 termination row; Core §5.4 item 4; Delivery §5.1 |
| N2-F5 | minor | Usage and (while BUG-04 is unfixed) the no-child-process statement are named in Control §2 and Core §5.4 item 4 as labelled Agent statements, the only further transition loosenings | Control §2, §7.2, §7.4; Core §5.4 item 4 |
| N2-F6 | minor | Campaign = equivalent framework in the transition period (needs a mapping table); Delivery §3.1's table is the stage-D adapter mapping; in the transition period only rows needing no reconcile/cancel-request fact are used, ambiguous submissions stay unknown | Control §7.1, §7.4; Delivery §3.1 |
| N2-F7 | minor | No publish in the transition period; the report states the derivation at a named sequence number, labelled “stated, transition period, not published” | Control §7.3; Core §7.4 paragraph 1 |
| N2-F8 | minor | One step per `run_workflow.py` invocation for steps supporting T2-numeric+ deliverables and for check runs | Control §7.1; Core §5.4 item 1 |
| N2-F9 | minor | The fixed per-step deadline: steps expected to exceed it are split or run through the campaign with a mapping table | Control §7.4; Core §5.4 item 3 |
| N2-F10 | minor | Environment manifest produced or verified (`environment_manifest.py check`) in the same environment no earlier than the attempt registration; `plugin_release` digest `unknown` with plugin code imported → identity incomplete | Control §7.2 identity row |
| N2-F11 | minor | Core §5.4 item 1: the attempt registration line stands in for the intent; the run record is the receipt content | Core §5.4 item 1 |

## N1 — round 4 (fixed after user approval; re-reviewed in round 5)

Context `s0-reconstruction-v12-r4`, R2, N1 violated; reproduced by the coordinator with `s0/round4-attack.py` against the
unmodified model. The user approved the three design changes proposed for the majors (2026-10-29); the two minors are
local corrections. Model after the changes: 86/86 scenarios, 39/39 mutations killed; replaying `round4-attack.py`:
A1 revert pending approval (X2 stays bound, `confirmation_results` = 2 in publish), A2/A2b closed by the field move
(scenario t84), A3 gives T3E, A4 counts the five side-step variants (`task_artifacts`).

| Id | Severity | Finding | Change | Where |
|---|---|---|---|---|
| N1-R4-F1 | major | Re-binding a confirmed draw by reverting the program (confirm X1 on S1, X2 on S2, revert to X1) without a pin or human, contrary to Control §4.2 | A contract whose content change makes an earlier attempt's identity current again (a revert) is not at least as strict and needs human approval. Every confirmation-sample result on the chain is reported and counted in publish (`confirmation_results`), so keeping one of several confirmed draws is visible. Model: `revives` in `_contracts`, `confirmation_results`; scenario t83; mutations “content revert re-binds without a human”, “confirmation results not reported” | Control §1.2 (row “content changes”, paragraph below the table), §2 (publish), §4.2 (binding), §4.5, §5.4; Delivery §5.2 C1 row |
| N1-R4-F2 | major | Confirmation fields on the step: a T3C deliverable added later inherits “confirmation required = no” / “independent = no” | The two confirmation fields move from the step to the **deliverable**. A deliverable that becomes T3C by a later contract (added, or target raised) must carry yes for both, otherwise the contract needs approval; existing deliverables cannot change them to no. Model: `Deliverable.confirmation_required`, `Deliverable.independent_confirmation`, `contract_at_least_as_strict`, `freeze_ok(…, conf_req, indep_req)`; scenario t84; t44, t72, t79, t82 moved to deliverable fields; mutation “added T3C deliverable inherits no” | Control §1.1 (deliverables row, step table, paragraph), §1.2, §4.4 item 5, §4.5 table |
| N1-R4-F3 | major | Check extra inputs outside the check identity, unresolved, unmodelled | New step field **check inputs** (check digest, step). C resolves them at admission (an upstream of the target's step to the version the target consumed, otherwise bound or latest current; unresolvable → reject); they are written in the intent and part of the check attempt's identity. A result counts only when its inputs are exactly the declared ones and upstream inputs equal the consumed versions. Changing them needs approval. Model: `StepSpec.check_inputs`, `check_identity(…, extra)`, `check_inputs_for`, `check_inputs_hold`, `check_attempt_of`; scenario t85; mutation “check inputs not resolved by C” | Control §1.1, §1.2, §2 (intent), §4.3, §5.2, §7.2 (declared check identity) |
| N1-R4-F4 | minor | An agent-written exposure labelled with an existing check-attempt id satisfies freeze item 3 | Only exposures C wrote at that attempt's admission are attributed to a check attempt; in the transition period, only the exposure lines written for a registered check attempt's read list. Model: `freeze_ok` (writer); scenario t86; mutation “agent exposure attributed to a check attempt” | Control §2 (exposure), §4.4 item 3, §7.2 (exposure) |
| N1-R4-F5 | minor | Task-wide history omits successful draws on unchecked off-chain steps | The task-wide history counts the artifacts of every step, and publish records the total (`task_artifacts`). Model: `task_history` `artifacts`; scenario t87 | Control §4.5, §2, §5.4 |

Also: Core §0.5 review-status row updated (counts, revision after round 4); Control §8 counts and lists.

## N1 — round 5 (fixed after user approval; re-reviewed in round 6)

Context `s0-reconstruction-v12-r5`, R2, N1 violated; reproduced by the coordinator with `s0/round5-attack.py`. The user
approved both proposed directions (2026-10-29). Model after the changes: 89/89 scenarios, 42/42 mutations killed;
replaying `round5-attack.py`: all five attacks fail (a1, a2 not met / not bound; a3 admission rejects; a4 check missing;
a5 admission rejects).

| Id | Severity | Finding | Change | Where |
|---|---|---|---|---|
| N1-R5-F1 | major | A cosmetic change reproducing an already-seen digest re-binds it (also through an unchecked upstream) | New derived property **reproduced**: the representative producer's identity differs from the first producer's in the step. A reproduced artifact is not bound unless pinned (human approval); new label `reproduced`. Model: `reproduced`, `bound`, `label`; scenario t88; mutation “reproduced digest binds without a human”. **Behaviour change:** scenario t24 used to accept a refactor that reproduced R1 automatically; it now needs an approved pin (assertion updated, stricter) | Control §4.2, §4.6, §4.7; Delivery §5.2 C1 row |
| N1-R5-F2 | major | A held or later-invalidated non-upstream check input still counts | A non-upstream check input resolves only to its step's bound version (admission rejects otherwise), and the result counts only while it is still bound. Upstreams and check inputs form an acyclic graph, so a check input never depends on the target's step; a check that needs data processed with the target does that processing inside the check attempt (the §5.2 mode-check example changed accordingly). Model: `check_inputs_for`, `check_inputs_hold`, `validate_contract` (cycle visit); scenario t89; mutation “check input need not stay bound” | Control §1.1, §4.3, §4.7, §5.2 |
| N1-R5-F3 | minor | Same side effect of check attempts keyed on the full identity in the model | Admission compares check × criterion × target (`same_side_effect`), as Control §3 says; §3 text made explicit. Scenario t90; mutation “check side effect not recognised across check inputs” | model `admit`; Control §3 |

Also: Core §0.5 and Control §8 counts and lists.

## N3 — statistics

| Finding | Sev. | Change | Where |
|---|---|---|---|
| N3-F1 | major | Cross-round error control split by which outcome rejects: threshold (pass rejects non-compliant) keeps options (a)/(b); compatibility-type confirmations must not split α, keep the per-round test as frozen, cap R and report 1 − (1 − p)ᴿ or min(1, Rp) with p the pass probability under the frozen unfavourable alternative | Methods §2.4 item 5; Core §7.1 |
| N3-F2 | major | A threshold claim that is an absolute-scale or performance claim on data also needs method-independent confirmation; the untuned carve-out waives only holdout confirmation; “confirmation required = no” only when the claim needs neither type | Methods §2.1; Core §7.2 threshold row; Control §1.1 |
| N3-F3 | minor | Core §7.1 states the independence condition and min(1, Rα) | Core §7.1 |
| N3-F4 | minor | Inconclusive for insufficient sensitivity only when determined before execution (power design not met) or when the interval straddles the boundary; a fail fully outside stays fail | Methods §2.3 |
| N3-F5 | minor | A procedure change after seeing the derived value makes the quantity tuned (exposed; loses the untuned carve-out) | Methods §2.1 |
| N3-F6 | minor | Numeric power target frozen (default P(pass) ≥ 0.8 under the favourable alternative; for compatibility checks P(pass) ≤ 0.2 under the unfavourable one) | Methods §2.4 |

## N4 — detector methods

| Finding | Sev. | Change | Where |
|---|---|---|---|
| N4-F1 | major | t0 per interaction: per track/interaction with continuous readout or pileup in the drift window; no trigger t0 for out-of-time tracks | Methods §1.5 TPC row |
| N4-F2 | major | Partitioned rounds: a round holds one or more steps; the final round has exactly one checked step (the final step); out-of-loop consumers only the final step; adding a step to an existing family needs approval. Model: `validate_contract` families, `intermediate_round`; t59 adapted (checked twins in the final round still rejected in either order; an unchecked member is a partitioned round); scenario t75. **For human attention**: DEC-06 was recorded as decided (“one step per round”); this copy reopens it as pending maintainer re-confirmation | Control §1.1, §1.2, §4.2, §4.6, §4.7; Methods §1.6, §4.4; Delivery DEC-06, SCI-06 |
| N4-F3 | minor | Add-round path: the approved contract demotes the old final step and moves the two checks; the old fail stays in the history. Scenario t76 | Methods §1.6; Control §4.7 |
| N4-F4 | minor | Rounds are chained (in-family upstreams only from the same or previous round; each round after the first consumes the previous). Model: `family_chain_problem`; scenario t75; mutation “rounds need not be chained” | Control §1.1; Methods §1.6 |
| N4-F5 | minor | Family checks are named by check digest; changing them is a family change (approval). Scenario t77 (also kills the mutation “family final round can change”, which the N1-F1 rule had masked) | Control §1.1, §1.2 |
| N4-F6 | minor | Methods §1.6 invalidation list aligned with Control §4.7 | Methods §1.6 |
| N4-F7 | minor | Scale factor only when MC-derived performance is transferred to data; direct data-driven performance measurement allowed | Methods §1.8 |

## N5 — Core routing

| Finding | Sev. | Change | Where |
|---|---|---|---|
| N5-F1 | major | Missing Methods part → no deliverables at T2-numeric or above | Core §0.2 |
| N5-F2 | minor | Fast path includes Core §5.2 and §5.3 | Core front matter |
| N5-F3 | minor | Determinate selector: a bare simulated number → T2-numeric; any statement about it → T3-E | Core §5.1 rule 1 |
| N5-F4 | minor | Implementing layer C loads the Control part as the code's specification; its T2-code contract still does not use the Control format | Core §0.2, §5.3 |
| N5-F5 | minor | Core §6.3 lists approval of a loosened T2-code contract | Core §6.3 |

## Reference model

Derivation version `v12.1`; after round 1: `76/76 scenarios passed`, `29/29 mutations killed`; after round 2 (below):
`80/80 scenarios passed`, `32/32 mutations killed`; after round 3 (below): `python3 -I v12-en-reference-model.py` →
`81/81 scenarios passed`, `34/34 mutations killed`.
The original model (Appendix A, SHA-256 `d5e0a186…dc9c`) is unchanged in the task file.

## Differences between the task file's current-state statements and the code (runbook 0.3 item 2)

None found at preflight (plugin 0.49.1; the named code is byte-identical to 0.49.0 as the task file describes).

# Round 2 (S0 rerun on the v12.1 spec copy)

hep-review context `s0-reconstruction-v12-r2`, target R2, achieved R2; all five violated. Majors: N1 1, N3 1, N5 1; N2 (7
minor) and N4 (4 minor) have no major finding, so per runbook 0.5.2 item 7 they pass once every minor finding is fixed
in the copy and recorded here (no re-review). N1, N3 and N5 go to round 3 (the last round allowed).

| Finding | Sev. | Change | Where |
|---|---|---|---|
| r2 N1-F1 | major | Failed draws: every computation attempt of a chain step that ended without a usable artifact (failed, cancelled, unknown, abandoned, computed but unattested) is listed in the deliverable status and counted in publish (`failed_draws`); the “impossible” claim is restated as “cannot be done without trace”. Model: `failed_draws`, publish field; scenario t78; mutation “failed draws not counted” | Control §4.5, §5.1 item 6, §5.4, §2 publish row |
| r2 N1-F2 | minor | Control §2 publish row lists the artifact and failed-draw counts | Control §2 |
| r2 N1-F3 | minor | Model validates the fields of B, adapter and human facts (`fact_field_problem`); scenario t80; mutation “fact fields not validated” | model |
| r2 N2-F1 | minor | = r2 N1-F2 | Control §2 |
| r2 N2-F2 | minor | `run_workflow.py` has no cancel: a signal-killed run is failed, an interrupted invocation without a record is unknown; no cancel lines | Control §7.4 |
| r2 N2-F3 | minor | Environment verification run precedes the attempt registration (same session and environment, after the last change) and is cited, not staged as an upstream; declared inputs vs consumed upstream artifacts distinguished | Control §7.2 identity row |
| r2 N2-F4 | minor | A failed parameter-digest command started a process: “not started” only with its termination confirmed, else unknown | Control §7.2 termination (c) |
| r2 N2-F5 | minor | B1 writes the termination field on every record (a record without it identifies an unfixed runner) | Control §7.2 (a); Delivery §4.1 B1 row |
| r2 N2-F6 | minor | Exposure lines in the transition period: one per read-list sample right after the attempt registration line, plus any other access | Control §7.2 (new exposure row) |
| r2 N2-F7 | minor | Campaign use in the transition period does not make the task M3: reported as M1 with M3 guarantees absent | Control §7.1 |
| r2 N3-F1 | major | A frozen ceiling on the overall false-pass rate (default α for thresholds, p_total = 0.2 for compatibility); rounds that would exceed it cannot support T3-C; compatibility-type budget split as Σ pᵣ ≤ p_total via the per-round power design | Methods §2.4 item 5; Core §7.1 |
| r2 N3-F2 | minor | Power target evaluated on the combined (multiplicity-adjusted) decision rule | Methods §2.4 |
| r2 N3-F3 | minor | Straddling-interval inconclusive applies to threshold validation; validity checks under tolerance use their frozen tolerance rule (inconclusive only when the check's precision is not below the tolerance, etc.) | Methods §2.3, §2.4 |
| r2 N3-F4 | minor | The exploratory pilot subsample is excluded from the confirmatory derivation, otherwise the quantity is tuned | Core §7.1 |
| r2 N4-F1 | minor | Every step of round r > 1 consumes round r − 1 directly or through same-round steps. Model `_reaches_previous`; scenario t81 | Control §1.1; Methods §1.6 |
| r2 N4-F2 | minor | Only the final step of a family is checked (format). Model; scenario t81; t50's add-round proposal now demotes the old final step | Control §1.1; Methods §1.6 |
| r2 N4-F3 | minor | Single-pass alignment/intercalibration solves list and check their unconstrained modes too | Methods §1.6 |
| r2 N4-F4 | minor | A check may read further artifacts as declared inputs (previous constants, data reconstructed with final constants), recorded in its receipt; identity unchanged | Control §5.2 |
| r2 N5-F1 | major | New requirement field “independent confirmation required” (first contract, from the claim type; dropping it is a loosening); the freeze names the method-independent confirmation samples; T3C needs a pass on such a sample when required. Model: `StepSpec.independent_confirmation`, freeze `independent`, `independent_ok`; scenario t79; mutation “method-independent confirmation not checked” | Control §1.1, §1.2, §2, §4.4; Methods §2.4 item 2; Core §7.2 |
| r2 N5-F2 | minor | TASK-03 and M2 scoped to T2-numeric and above; T0/T1 and T2-code spanning sessions use a short handover note | Core §5.2, §5.3 |
| r2 N5-F3 | minor | T2-code typical loading lists Core §0.4, §2.4, §5.1, §6.1, §6.3, §7.2–7.4, §8.2 and defers to the table | Core §5.3 |
| r2 N5-F4 | minor | A number measured on data for internal use → T3-E | Core §5.1 rule 1 |
| r2 N5-F5 | minor | Fast path reads Core §0.1–0.5, §2.1–2.3 and §8.4 | Core front matter |
| r2 N5-F6 | minor | AUTH-01 and the missing-Control limit scoped to contracts of T2-numeric and above | Core §0.2, §5.3 |

None of these loosens an acceptance condition, gate or judging rule; r2 N3-F1, N5-F1 and N1-F1 tighten.

# Round 3 (last S0 round; N1, N3, N5)

hep-review context `s0-reconstruction-v12-r3`, target R2, achieved R2; all three violated. N3 (4 minor) and N5 (2 minor)
have no major finding: they pass with the fixes below. **N1 has 2 major findings and does not pass**: S0 has reached its
three-round limit (runbook 0.5.2 item 7), so C1 and C2, whose entry conditions require N1, are blocked. The N1 fixes
below are recorded in this copy but **not re-reviewed**.

| Finding | Sev. | Change | Where |
|---|---|---|---|
| r3 N1-F1 | major | Only a freeze that precedes a sample's first exposure can label it method-independent. Model `independent_sample`; scenario t82; mutation “independent label from any freeze”. Not re-reviewed | Control §4.4 item 5 |
| r3 N1-F2 | major | Task-wide history (fail/inconclusive results and failed draws on every step of the contract) in the report and a task-wide failure count in publish, so a selection made on an off-chain step is visible. Model `task_history`; scenario t82; mutation “task-wide history omitted”. Disclosure, not prevention; not re-reviewed | Control §2, §4.5, §5.4 |
| r3 N3-F1 | minor | A too-coarse check is handled by the non-closure rule of the Methods §2.4 table, not by inconclusive | Methods §2.3 |
| r3 N3-F2 | minor | Option (a): round r's decision rule uses level 1 − αᵣ and its power design is evaluated there | Methods §2.4 item 5 |
| r3 N3-F3 | minor | Every criterion and tolerance is frozen before the first result it judges, on any sample | Methods §2.4 (freeze time) |
| r3 N3-F4 | minor | The method-independent confirmation of a threshold claim on data is in the threshold category (same ceiling, rounds counted) | Methods §2.4 item 5 |
| r3 N5-F1 | minor | Rule 1's “at least T3-E” limited to statements resting on numbers the task computes; a sourced feasibility conclusion stays T1 | Core §5.1 rule 1 |
| r3 N5-F2 | minor | VAL-02 also loads the tolerance row and power paragraphs of Methods §2.4 when such checks exist; typical loading aligned with the matrix | Core §5.3 |
