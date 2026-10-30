# Research Workflow Control: Evidence Tiers, Triggers and the Task Record

How a research request is carried to its deliverable with the evidence it needs: the evidence tier and execution mode
of each deliverable, which rules to load, the task contract, the transition-period task record, the control-layer
helper (whose rules did not pass review), human decisions and the completion report. This page is shared by every skill (a
reconstruction study, a fit, a training run or a numerical prediction use the same tiers and records); the
reconstruction method content is in hep-detector ([event reconstruction](../../hep-detector/references/event-reconstruction.md),
[calibration and alignment](../../hep-detector/references/calibration-and-alignment.md)).

> **Status.** Source: the reconstruction v12 specification, v12.2 spec copy (`evals/reconstruction-v12/spec/` in
> the source repository; Core, Methods, Delivery and the transition-period part of Control). S0 (recorded spec review,
> hep-review R2) passed for the routing, transition, statistics and method obligations; **the control-layer
> obligation (contract format, strictness order, derivation, admission; Control §1–§6 and the reference model) did not
> pass**: violated in all eight review rounds; round 8 left three open defects, listed in every report of the
> helper. The control-layer helper (`control_layer.py`, stages C1 and C2 — resumption, reconciliation,
> lease lock) ships by the maintainer's decision of 2026-10-30, with the control rules stated as **not through S0**
> (section below). It implements the spec copy's Control part and agrees with its reference model on the tested fact sequences, but it is **not reviewed or validated**: its
> derivations are mechanical consequences of unreviewed rules, not established results, and it gives no autonomous
> reconstruction capability. The transition-period procedure below remains the reviewed one. Placing this page in
> hep-computing (DEC-11) and the task-record location (DEC-08/DEC-09) were approved by the maintainer on 2026-10-30.

## Always-on rules

These hold for every task, whatever its tier:

1. The final text cannot override a fail or an inconclusive.
2. Do not deliberately hit a failure first and then ask for confirmation at every step.
3. not-applicable comes with the task type and a reason; it is never a waiver granted after a failure.
4. Do not deliver a plan in place of work that was asked to be executed; do not stop after every skill switch.
5. Do not claim capabilities, APIs or validations that do not exist.
6. No computed artifact with insufficient checks is accepted automatically.
7. Never fall back silently to “latest” conditions.
8. Never move failures out of the required denominator after seeing the measured quantity.
9. Authorization, blinding and human-decision boundaries follow the host, project and existing tools; nothing here loosens them.
10. Never loosen the rules that judge your own work: a loosened contract waits for a human; if the target tier cannot be reached, report partial completion — never rewrite the target.

## Evidence tier and execution mode

Decide both for every deliverable in the first reply (T0/T1) or the first task contract (T2 and above), from the
request and the intended use, never from the wording of the report.

| Tier | Typical deliverable | Required evidence |
|---|---|---|
| T0 answer | concept, single fact | general answering discipline |
| T1 method or feasibility | method explanation, source survey, feasibility conclusion | reasoning, sources, scope and limits; **no computational run is forced** |
| T2-code | implementation, fix, script | diff or commit digest and a test-execution receipt (command, exit code, tested commit, output summary); the project's own test framework suffices |
| T2-numeric | numbers, tables, figures | attested artifacts (below), at least one required check on the owning step, every required check pass |
| T3-E exploratory claim | “roughly how much”, “is a trend visible”, no confirmation asked | T2-numeric, sample roles recorded, every number marked **exploratory, unconfirmed**; supports no confirmatory claim |
| T3-C confirmatory claim | performance or physics conclusions, numbers reported externally, threshold comparisons | T2-numeric plus sample roles and exposure, frozen criteria and confirmation, four-valued checks, scope and exposure accounts |

Determination rules:
- A confirmatory conclusion, external reporting, a claim that holds for **data** (or input to one), or a comparison of
  a computed number with a threshold → T3-C.
- A performance number on synthetic or simulated samples, internal, delivered **without any statement about it** →
  T2-numeric with the limitation “supports only performance in simulation”; any assessment, trend or comparison → T3-E.
- A number measured on data for internal use, not wanted as a claim that holds for data → T3-E.
- Other statements resting on numbers the task computes → at least T3-E. A feasibility conclusion from reasoning and
  sources, with expected performance stated as an attributed expectation, stays T1.
- Wording such as “approximately” or “preliminary” never lowers a tier; when two rules apply, take the higher. What is
  required follows the original request; when unclear it is required.
- The target tier never changes. Falling short of it is **partial completion**, reported with the achieved tier.

| Execution mode | When | Needs |
|---|---|---|
| M1 interactive, bounded local | done in this session, locally, in the foreground | host limits and a bounded plan; T2-numeric and above use the transition rules below |
| M2 resumable | a T2-numeric+ deliverable expected to exceed a session, moved to the background, or resumed after an interruption | persisted identities and state (G1, G2, G5): only with the control-layer helper (G5 qualified on its record; rules not through S0), otherwise M1 segmented execution and a resumption summary |
| M3 unattended or remote | remote submission or no one present (local metered cost alone does not make M3) | executor guarantees G1–G5: **not available**; remote work follows the existing campaign rules and manual boundary |

Lacking a guarantee is reported as a weaker, stated process; a capability is never simulated by a written policy.
Which guarantees the local runner actually provides is established by `executor_capabilities.py qualify` (fault
injection: G1 output isolation, G2 termination and G5 persistent state — restart recovery and stale lock takeover
of the helper's task record — pass on Linux; G3 submission reconciliation, G4 metering with atomic reservation and
G6 conditions evidence are unsupported); `admit --mode M2` accepts only with that G5 record; M3 cannot be claimed.
A qualified G5 shows the record survives restarts, not that its rules were reviewed.

## Trigger matrix (what to load)

Load a row only when its condition holds; when it does not, no fact log, manifest or ledger is required.

| Module | Trigger | Load |
|---|---|---|
| Task contract | T2 and above, or the user asks for records | this page (contract below); T0/T1 state goal, scope and limits in a sentence |
| Physics semantics, conditions, uncertainties, association and counting, iteration, selection bias, simulation to data | producing, converting or comparing physical quantities; versioned conditions; uncertainty claims; many-to-many candidates or counts; a calibration fed back into reconstruction; trigger/DQ/exposure; MC-truth or simulation-trained performance | hep-detector [event reconstruction](../../hep-detector/references/event-reconstruction.md) (method contract), [calibration and alignment](../../hep-detector/references/calibration-and-alignment.md) (iteration loops) |
| Sample roles, criteria changes, four-valued checks, freeze, decision rules, blinding | T3 (roles); T2-numeric+ with checks; T3-C (freeze and decision rules); a blinding policy | hep-detector [performance and truth matching](../../hep-detector/references/reconstruction-performance-and-truth-matching.md); statistical judgement in hep-statistics |
| Writing a task record | any fact log | the task record section below |
| Output freshness, producer edge | any numeric output delivered or used downstream | the runner rules below; otherwise mark it **unattested** |
| Termination, resources | a timeout, cancel or surviving child process; meterable costs | the runner rules below; the budget is not enforced against actual usage without metering |
| Resumption summary | a T2-numeric+ deliverable spanning sessions or run in segments | the resumption section below; T0/T1 and T2-code use a short handover note |
| Completion report | always, scaled by tier | the report section below |

## Task contract

- **T2-code**: record the scope of code to change, the acceptance tests (commands and the set that must pass), the
  tested commit and required/optional. Loosening — deleting or weakening a test, marking it skip/xfail, making a
  required item optional — needs a human; adding tests or changing the implementation is free.
- **T2-numeric and above**: the deliverables (required/optional, target tier), the steps (method, program, upstream,
  required checks and criteria, iteration family and final round), sample roles (T3) and the budget when limited;
  outside the contract, the original goal, usable data, assumptions, baseline and alternative methods, triggered
  modules and execution scope (existing project documents may be cited, not copied). The closed contract format and
  its strictness order are specified in Control §1 of the spec copy, which **did not pass S0**: until it does, a
  change that only adds (a required check, a deliverable, a sample, a lower budget) may be applied, and **any other
  change waits for a human**, listed in the report. `control_layer.py contract --dry-run` says whether a contract
  would take effect under that (unreviewed) order.
- In M1 the first contract takes effect when it is listed in the first reply, where the user can correct it (DEC-12,
  approved).

## Transition period: running and recording without a control layer

While the control rules have not passed review, a task that keeps its record by hand (without the helper below)
completes T2-numeric and T3 deliverables as **transitional attested (declared inputs)**:

1. **Execution**: artifacts go through `run_workflow.py`, **one step per invocation**, each in a **fresh output
   directory** with its upstream outputs staged in as declared inputs. The attempt registration line (below) stands
   in for the control layer's intent; the run record is the receipt. A multi-step invocation is exploration only.
   Another framework (including the partition campaign) needs a field-mapping table in the task record first;
   otherwise its outputs are unattested. Using the campaign does not make the task M3.
2. **Checks** also run through the runner: the check program writes (check digest, criterion digest, target artifact
   digest, four-valued result, sample) into an output file. A result counts only when bound to its run: the check
   digest equals the program's hash in the run record, the criterion digest equals a criteria file in its input
   manifest, the target's outputs are staged as inputs with the hashes their run record holds, and all three equal
   the check identity declared in the attempt registration line, with every sample used in its read list.
3. **Known runner gaps**: cite their tests when fixed in the target checkout (`tests/skills/hep_computing/
   test_workflow_b1.py`); where they are not, follow the workarounds of Control §7.4 of the spec copy (no incremental
   skip; outputs absent before execution; relative paths only; confirm no child processes remain).
4. **Task record**: one persistent directory per task, separate from every output directory and outside the project
   config — default `hep-research-artifacts/<task>/task-log/task-log.jsonl` in the project (DEC-08/DEC-09,
   approved). It is a **single append-only file**; each line carries a sequence number, a kind, a writer (main Agent,
   human, or main-Agent transcription) and the SHA-256 of the previous line. Before appending, read the last line and
   check its hash; never edit or delete a line — correct with a new one. The main Agent writes only these kinds:
   contract, freeze, exposure, attempt registration, run registration, field-mapping table, transcribed human decision.
   - **Attempt registration** (before execution): attempt = output directory + step id; the contract step; the read
     list; for a check, its declared check identity; the declared cost when there is a budget. Then one **exposure**
     line per sample in the read list (and one for any other look at a sample).
   - **Run registration** (after execution): the run record path and SHA-256; the artifact digest (SHA-256 of the
     canonical output manifest: sorted keys, no whitespace, UTF-8); termination from the record's `termination`
     field (`unconfirmed` → the attempt is **unknown**); “not started” when the runner refused the step before
     starting any process (then failed, termination confirmed, no outputs); usage as a labelled statement.
   - **Identity must be complete**: list as inputs the code other than the `.py` in argv (code manifest), an
     `environment_manifest.py` output produced or checked in the same environment just before the attempt
     registration, and versioned conditions snapshots; a `plugin_release` digest of `unknown` with plugin code
     imported makes the identity incomplete. An incomplete identity supports no “still current” or reuse claim.
5. **Admission** is the main Agent's check before each attempt registration, stated item by item in the report:
   effective contract, cost within the budget, reads (confirmation samples only by check runs after a freeze that
   lists them; blinded samples only after a human unblind), upstream versions, no unknown attempt on the same step,
   no rerun of an identity that already failed a required check, and every earlier artifact of a checked step checked
   before another computation of it.
6. **Unknown**: while a step has an attempt whose termination is unconfirmed, start nothing else on it until a human
   abandons it. There is no reconcile in the transition period.
7. **Confirmation and blinded samples**: a run that reads one cites the freeze (or unblind) record digest in its
   argv; confirmation samples are read only by check runs.
8. **No M2/M3 claim**: work longer than a session is split into M1 segments, each following these rules, with a
   resumption summary.
9. **No publish**: the report states each deliverable's derivation at a named task-record sequence number, labelled
   “stated, transition period, not published”.

The report's limitations paragraph says: the runner gaps not fixed in the target checkout; that transitional
attested (declared inputs) was used; that derivation and admission were stated by the main Agent, not guaranteed
mechanically; incomplete identities; transcribed decisions; the no-child-process statements; that reads outside the
runner cannot be detected (so neither the order of confirmation access nor the blinded region not being read is
proven).

## Control-layer helper (C1, C2; control rules not through S0)

`<plugin root>/skills/hep-computing/scripts/control_layer.py` keeps the task record and derives from it (DEC-02,
approved 2026-10-30). It implements Control §1–§6 of the spec copy and is tested against its reference model (92
scenarios, 44 mutations, the same derivation on scenario and random fact sequences) — agreement with **rules that
did not pass review**, not a validation.

- **Record**: one append-only `task-log.jsonl` (default `hep-research-artifacts/<task>/task-log/task-log.jsonl`,
  DEC-01/08/09, approved); each line carries sequence number, batch, kind, writer, fields and the previous
  line's SHA-256; every load verifies the chain and replays the facts. Never edit it: every fact goes through a
  command with `--expect-head` (compare-and-set), optionally `--expect-digest`; `--op` makes a retry idempotent. Keep
  the printed `head_digest` outside the record: the chain cannot catch an edit of its last line.
- **Writers**: the agent writes `contract`, `freeze`, `exposure`; the helper writes session, intents, rejections,
  reuse, publish; `receipt` turns a `run_workflow.py --receipt-dir` receipt (and bound check result) into adapter
  facts — run each admitted attempt as one step with `--attempt-prefix P`, P plus step id being the attempt id; an
  unconfirmed termination becomes **unknown**; `--not-started` records a step the runner refused.
- **Admission** (`admit`) computes the identity and the consumed inputs itself, applies the budget, read, unknown,
  rerun and check-before-recompute rules, and compares the executor's qualified capabilities with the mode
  (`executor_capabilities.py`): M2 needs G5 (qualified with this helper), M3 also G3/G4 (unsupported, refused). A
  check attempt names only check, criterion and target; the helper resolves declared check inputs.
- **Human decisions**: `decide` is for humans only, in their own terminal; it refuses in a shell with an agent
  marker (`CLAUDECODE` and similar) and needs `--confirm-human` — a guard, **not an enforcement**: the agent never
  runs or works around it and asks instead; the record cannot prove who wrote a decision.
- **Reports**: `status` and `report` (paragraphs 1–7) derive at one head; the limitations always say the rules did
  not pass S0. Report results as “derived by the control-layer helper at sequence N (control rules not through
  S0)”; “attested (declared inputs)” describes the mechanism (helper intent, runner receipt, reads not observable),
  not the rules.
- **Resumption (C2)**: a new session runs `resume` first (the summary below from the record alone, with what never
  to resubmit and what to do next). Settle every admitted, running or unknown attempt before anything else: take its
  receipt, `receipt --lost` when the run left none, `reconcile` from a receipt that proves the outcome, or ask a
  human to abandon it; `cancel` records C's cancel request. Then `lock acquire --owner NAME` (an expired lease is
  taken over only after that; a live one never; takeovers are recorded beside the record). Under M2 every
  write but a human decision passes `--owner` holding a live lease. `recover` removes a torn, unacknowledged line.
- **Not provided**: M3, conditions evidence (G6), typed-source checks of `contracts/dependencies.py` (PROV-02),
  partition scope accounts (stage D).

## Checks: roles, types, results and the freeze record

`<plugin root>/skills/hep-computing/scripts/check_definitions.py` applies the check definitions (statistical choices
are made with hep-statistics; the script only applies them):

- **Roles**: closure (internal consistency; catches bugs, never confirmation), confirmation-holdout (guards against
  tuning bias: a fresh, unexposed sample of the same kind), confirmation-independent (guards against shared
  systematics: a methodologically independent test). Statistical independence is not systematic independence.
- **Types**: threshold validation (an acceptance region with a basis; no basis, no freeze) and performance estimate
  (value ± uncertainty with validity checks; never invent a threshold).
- **Results** are pass, fail, inconclusive or not-applicable, each with a reason; not-applicable needs the task type
  and must have been allowed in advance; exit 0 is never a physics pass; 0 events in N gives a 95 % upper limit of
  about 3/N, not “none seen”.
- **Decisions** (`decide`): the three-region threshold rule (inside → pass, outside → fail, straddling →
  inconclusive; a pass is capped at inconclusive when the frozen power design was not met before execution, a fail
  stays fail); the tolerance rule for validity checks (|deviation| < max(k·σ_stat, δ_phys) ≤ claimed total
  uncertainty; a deviation incompatible with zero becomes a systematic); per-bin levels (unchanged when pass rejects
  “non-compliant”, α/n or Šidák when fail rejects “compatible”); cross-round control against a frozen ceiling
  (threshold: α allocation at level 1 − αᵣ, or a cap R; compatibility: never split α or widen the tolerance).
- **Freeze record** (`validate-freeze`, `verify-chain`; DEC-03 default): written before the first result it judges,
  as one line of an append-only JSON-lines log whose lines carry the previous line's SHA-256. Closed fields: step,
  effective validation identity (check digest, criterion digest pairs), criteria version, confirmation samples and
  which are method-independent, controls, the commitment to report every confirmation result, the feasibility of
  independent confirmation with reasons (and conditions when infeasible), the multiple-testing treatment (error
  type, combination, correlations), cross-round control (kind, ceiling, option), each check's role, type and rule,
  and the power design evaluated on the combined rule.
- A check program that can only pass is no evidence: give each check a positive and a negative test.

## Human decisions

With the control-layer helper, decisions enter the record only through its `decide` command, run by the human
(above). No gate is needed for authorized local reading, fixing and verification, contract changes that only add or tighten,
or changing the method or code (which invalidates its artifacts). A human decides: approving a contract that is not
at least as strict, identity continuation, producer attribution, unblinding, abandoning an unknown attempt, loosening
a T2-code contract, changing the estimand or required claims, submission/installation/publication beyond
authorization, irreversible deletion or overwriting, and the maintainer's open design decisions. Raise necessary
decisions in one batch, each with its basis and a recommended default, and keep doing the work that does not depend
on them. Decisions are written by the human, or given in the conversation and transcribed verbatim, marked as
transcribed.

## Resumption summary

For a T2-numeric+ deliverable spanning sessions, the task record must let a new session without the chat take over:
the effective and pending contracts and the authorization in force; each deliverable's target and achieved tier and
state (done, in progress, blocked with its diagnostic label, not started); unconfirmed actions and committed
resources; exposed samples, blinding state and frozen criteria; pending human decisions; the next step. The successor
checks the actual state first; when it differs from the summary, the actual state wins and the difference is recorded.

## Completion report

Report execution success, check results, whether the scientific claim holds, and whether authorization was obtained
separately; none stands in for another.

| Paragraph | Content | T0/T1 | T2 | T3 |
|---|---|---|---|---|
| 1. Deliverables | each deliverable's target and achieved tier, done/partial/blocked/not done with the reason; the stated derivation (transition period) | one sentence | ✓ | ✓ |
| 2. Computation | main steps and their state; attested kind (only: attested, attested (declared inputs), transitional attested (declared inputs)); unattested listed separately | — | ✓ | ✓ |
| 3. Scientific evidence | tier of each claim, four-valued check results, decision rule, sample roles and exposure, every historical fail/inconclusive, failed draws, check attempts without a result and artifacts on the dependency chain | — | if numeric | ✓ |
| 4. Contracts and authorization | each contract's state, every human decision (and its transcriber), authorization used, pending decisions | if present | ✓ | ✓ |
| 5. Scope and limitations | scope, conditions context, known biases, uncovered regions, transition-period limitations | one sentence | ✓ | ✓ |
| 6. Unconfirmed risks | unknown attempts, unconfirmed terminations, committed resources | — | if present | if present |
| 7. Reproduction | where the contract, task record, artifacts and receipts are | — | ✓ | ✓ |

“Complete” is said only when every required deliverable reaches its target tier; inconclusive is never presented as
holding; deleting a claim does not remove frozen confirmation results already obtained from paragraph 3.
