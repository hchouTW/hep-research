# Detector system design workflow

How a detector system is designed with this plugin: a requirement-centred loop in which the agent decides what
evidence to produce next and `contracts/design.py`, never the agent, decides compliance, maturity and staleness.
Read only the section of the current stage. The principles behind it (requirement flow-down, fidelity ladder,
trade-offs) are in [detector design principles](detector-design-principles.md).

Contents: [Usage levels](#usage-levels) · [Artifacts](#artifacts) · [D0 Framing](#d0-framing) ·
[D1 Allocation](#d1-allocation) · [D2 Exploration loop](#d2-exploration-loop) · [D3 Convergence](#d3-convergence) ·
[D4 Review](#d4-review) · [Verdicts and reason codes](#verdicts-and-reason-codes) · [Never](#never)

## Usage levels

Choose the level from the user's intent and say in the reply which one you chose (LVL-01).

| Level | When | What to do |
|---|---|---|
| L0 quick estimate | "Roughly what is the MDR of this layout?" | Run the tool directly (`tracker_resolution.py`, `multiple_scattering.py`, `calorimeter_resolution.py`, ...) and answer. Write no artifact. State the bound nature of the number (an optimistic bound, or an estimate) and never use the words compliant or non-compliant |
| L1 single-chain study | One requirement, one or two candidates, must be reproducible | A slim design-spec, the candidates, `evaluate_design.py run` per figure of merit, then `evaluate_design.py report` |
| L2 full design | Several requirements and candidates, review needed | All stages below and the four review gates |

## Artifacts

Three artifact types (contracts 3.11.0), all in the project's artifacts_dir; decision records live outside it
(e.g. `decisions/`).

| Type | One file per | Holds |
|---|---|---|
| `design-spec` | version (never modified: a change is a new file `design-spec.vN.json`) | goals (`PHY-*`), requirements (`REQ-*`) with comparator, target, unit, denominator (each value with a tolerance), kind (driving or derived), allocation and verification; allocations (`ALC-*`, quadrature only with declared independence); constraints (`CON-*`, hard or soft); `comparison_basis` |
| `design-candidate` | candidate | subsystems keyed by `DES-*` id: role (core `subsystem_roles`), technology, parameters (value, unit, source, status), interfaces, calibration (required); budgets per subsystem for mass, power, channel count, data rate; `derived_from` plus `overrides` for a variant |
| `design-evaluation` | candidate x figure of merit x fidelity | written only by `evaluate_design.py`: value, bound, fidelity, uncertainty, parameter_refs, run_ref, all set from the tool contract and the tool output |

Ids are namespaced by the spec's `design_id` (`<design_id>:REQ-TRK-001`). Parameters cite their source: a public
fact through a profile's evidence ledger claim id, otherwise `proposal` or `user-supplied-internal`.

## D0 Framing

Goal: the physics goals, the operating environment, the hard constraints.

- hep-measurement drafts the goals (observable, range, precision goal); hand off through a `measurement-spec` file
  when one exists.
- List the hard constraints (mass, power, envelope, channel count, data rate, radiation, cost) now, not at the end.
- Missing inputs are `not-provided`, never guessed.
- Gate H1 (`design-scope`): prepare the decision record for a human to approve; until then the report shows
  `gate.H1_missing`. A missing gate never blocks computation.

## D1 Allocation

Goal: driving requirements a design can be checked against.

- Each requirement names its figure of merit (`quantity`, an id of `contracts/rules/design_adequacy.json`) and its
  denominator: the conditions under which the number holds (rigidity and species for a resolution; charge sign and
  curvature offset for charge confusion; the MDR definition, intrinsic or total; the separation convention for PID;
  the working-point efficiency for a rejection). The denominator fields follow the tool contract of that figure of
  merit; `contracts/design.py` refuses a requirement whose denominator lacks a field the adequacy table needs.
- Each driving requirement has an allocation (budget items, `quadrature` with `independent: true` or a correlation
  matrix, else `linear`) and a margin.
- Declare `comparison_basis` (for example equal mass within 5%): without it no comparison or ranking is given.
- Gate H2 (`requirements-baseline`).

## D2 Exploration loop

Goal: candidates screened against the requirements at the lowest adequate fidelity.

1. Write candidates; a variant names its base in `derived_from` and lists only `overrides`.
2. Evaluate, one figure of merit at a time:

   ```sh
   python3 <plugin root>/skills/hep-detector/scripts/evaluate_design.py run --artifacts A \
       --candidate <design_id>:cand-B --requirement REQ-TRK-001
   python3 <plugin root>/skills/hep-detector/scripts/evaluate_design.py run --artifacts A \
       --candidate <design_id>:cand-B --requirement REQ-CC-001 --upstream evaluations/<resolution evaluation>.json
   python3 <plugin root>/skills/hep-detector/scripts/evaluate_design.py budget --artifacts A \
       --candidate <design_id>:cand-B --quantity mass
   ```

   `run` picks the tool contract operation for the figure of merit at `--fidelity` (default F1), recomputes its
   inputs from the candidate, the denominator and the upstream evaluations, runs the tool and writes the output, the
   computational-run and the evaluation. With no evaluator at that fidelity it writes a `capability.unavailable`
   evaluation (no value). Shipped F1 operations: momentum resolution and MDR (`tracker_resolution`), MDR with the
   Gluckstern estimate (`multiple_scattering`), Gaussian-core charge confusion (`charge_confusion_rate`), TOF and
   RICH separation power (`pid_separation_power`, `cherenkov_angle`), rejection from a separation power and a
   working-point efficiency, straight-line acceptance of coaxial apertures and budget sums (`design_estimates`).
3. `evaluate_design.py plan` lists what is missing; `evaluate_design.py report` derives the compliance matrix.
4. Screening is derived: a candidate whose hard constraint or driving requirement fails is screened out; an F0
   estimate only raises an `at-risk` flag.
5. If no candidate can meet the requirements, write a new design-spec version and a `requirement-change` record and
   return to D1.

Gate H3 (`architecture-selection`): the candidates entering convergence plus every `capability.unavailable`
evaluation; each listed candidate needs a screening-level or unavailable evaluation for every requirement.

## D3 Convergence

Goal: the evidence each driving requirement needs for compliance.

- The adequacy table gives per figure of merit the compliance fidelity (resolution F3; charge confusion F4 with tails
  validated by data; PID rejection F4; acceptance F2 in-field) and the upstreams compliance needs. An F1 result can
  exclude a candidate but never approve a physics requirement.
- Candidates are finally compared on expected measurement precision through the forward chain response ->
  measurement-spec -> Asimov statistical-result (hep-statistics); a chain built on optimistic F1 inputs can only
  exclude.
- Every inconclusive driving requirement gets a proposed disposition in the report (accept risk or next study).

## D4 Review

- The compliance matrix, the risk table and the maturity per requirement come from `evaluate_design.py report`; no
  verdict is written by hand.
- Independent review of the derived report: hep-authoring.
- Gate H4 (`design-baseline`): a human approves the report, the evaluations it covers and one disposition per
  inconclusive driving requirement. An infeasible design is an allowed outcome; return to D1 or stop.

## Verdicts and reason codes

Per evaluation the first matching row of an 18-row table decides; per requirement and effective candidate the
evaluations are aggregated (the report lists used and skipped ones; a skipped unfavorable evaluation still blocks a
pass). Codes the report uses:

| Code | Meaning | Next step |
|---|---|---|
| `bound.excludes` | an optimistic bound misses the target: fail | change the candidate or the requirement |
| `bound.direction` | the bound cannot decide (an optimistic bound meets the target) | higher fidelity |
| `fidelity.insufficient` | below the screening or compliance fidelity | higher fidelity |
| `estimate.decides`, `margin.within_uncertainty`, `uncertainty.missing` | an estimate clears the target at the coverage CL, straddles it, or has no usable uncertainty | more precise evidence |
| `chain.incomplete`, `domain.mismatch`, `budget.incomplete` | a required upstream, the validity domain or a budget row is missing | supply it |
| `evidence.stale`, `evidence.unresolved`, `evidence.invalid` | an input changed, is unbound or invalid | rerun with a new evaluation id |
| `evidence.conflict`, `evidence.excluded_adverse`, `evidence.orphan_run` | contradicting evidence, unfavorable evidence excluded, a run without its evaluation | inspect the contracts and validity domains |
| `capability.unavailable` | no evaluator at that fidelity | record it; never estimate a number |

The adequacy table is an initial default until physics review: every pass is reported as provisional.

## Never

- Write or edit a verdict, a maturity, a stale marker, `screened_out` or `at-risk` into any file.
- Fill in fidelity, bound, parameter_refs or a value by hand; edit an evaluation, run or output after it is written.
- Put a number on a figure of merit without an evaluator (`capability.unavailable` instead).
- Rank candidates or draw a Pareto front without a holding `comparison_basis` and non-optimistic evaluations of the
  same fidelity vector and denominator; claim a global optimum.
- Treat a decision record written by an agent as approval: gates need a human actor.

<!-- example -->
Example: `examples/design-space-spectrometer` designs an AMS-like space spectrometer (public facts from the
`experiment:ams-02` profile ledger) with three candidates at F1: the probe with a too-short lever arm fails the
resolution requirement, the two reasonable candidates are inconclusive on resolution and charge confusion, and the
equal-mass basis holds for the two that survive screening.
<!-- /example -->
