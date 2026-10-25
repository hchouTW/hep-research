# Detector system design workflow

How a detector system is designed with this plugin: a requirement-centred loop in which the agent decides what
evidence to produce next and `contracts/design.py`, never the agent, decides compliance, maturity and staleness.
Read only the section of the current stage. The principles behind it (requirement flow-down, fidelity ladder,
trade-offs) are in [detector design principles](detector-design-principles.md).

Contents: [Usage levels](#usage-levels) · [Artifacts](#artifacts) · [D0 Framing](#d0-framing) ·
[D1 Allocation](#d1-allocation) · [D2 Exploration loop](#d2-exploration-loop) ·
[D2 Automated candidate generation](#d2-automated-candidate-generation) · [D3 Convergence](#d3-convergence) ·
[D4 Review](#d4-review) · [Engineering couplings and calibration](#engineering-couplings-and-calibration) ·
[Verdicts and reason codes](#verdicts-and-reason-codes) · [Never](#never)

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
| `design-spec` | version (never modified: a change is a new file `design-spec.vN.json`) | goals (`objectives`, ids `PHY-*`), requirements (`REQ-*`) with comparator, target, unit, denominator (each value with a tolerance), kind (driving or derived), allocation and verification; allocations (`ALC-*`, quadrature only with declared independence; a correlation matrix is accepted
but not yet used in the sum, so do not rely on it); constraints (`CON-*`, hard or soft); `comparison_basis` |
| `design-candidate` | candidate | subsystems keyed by `DES-*` id: role (core `subsystem_roles`), technology, parameters (value, unit, source, status), interfaces, calibration (required); budgets per subsystem for mass, power, channel count, data rate; `derived_from` plus `overrides` for a variant |
| `design-evaluation` | candidate x figure of merit x fidelity | written by `evaluate_design.py` (F0 heuristic arguments are written by hand and accepted by `design.py`): value, bound, fidelity, uncertainty, parameter_refs, run_ref, set from the tool contract and the tool output; exceptions: F3 expected precision from its input statistical-result, F4 from the study record (`study_ref`, bound from the tail-source rule), F5 from the dataset record's `design_measurement` (`dataset_ref`) |

Ids are namespaced by the spec's `design_id` (`<design_id>:REQ-TRK-001`). Parameters cite their source and carry a status: the
source is a profile's evidence ledger claim id for a public fact, otherwise free text; the status is an evidence status
(`proposal`, `user-supplied-internal`, `general-method`, `derived-result`, ...).

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
- Each driving requirement has an allocation (budget items, `quadrature` with `independent: true`, else `linear`;
  a correlation matrix is accepted but not yet used in the sum) and a margin.
- Declare `comparison_basis` (for example equal mass within 5%): without it no comparison or ranking is given. A budget
  item cancels in the difference only when both candidates carry the same subsystem with the same budget row.
- Gate H2 (`requirements-baseline`): the report flags `gate.H2_missing` until a human `requirements-baseline` record
  lists exactly the current design-spec, every driving requirement has a denominator and an allocation with a
  margin, and `comparison_basis` is declared (the tool checks that an allocation and a margin exist, not that the
  allocation is the requirement's own or that the margin is positive: check both).

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
   working-point efficiency, straight-line acceptance of coaxial apertures and budget sums including the material
   budget (`design_estimates`), calorimeter energy resolution (`calorimeter_resolution`). Survival probability and expected
   precision have F1 screening in the adequacy table but no F1 operation (expected precision is F3 only): a
   default-fidelity `run` writes a `capability.unavailable` record for them.
3. `evaluate_design.py plan` lists what is missing; `evaluate_design.py report` derives the compliance matrix.
4. Screening is derived: a candidate whose hard constraint or driving requirement fails is screened out; an F0
   estimate only raises an `at-risk` flag.
5. If no candidate can meet the requirements, write a new design-spec version and a `requirement-change` record and
   return to D1.

Gate H3 (`architecture-selection`): the candidates entering convergence plus every `capability.unavailable`
evaluation; each listed candidate needs a screening-level or unavailable evaluation for every requirement.

## D2 Automated candidate generation

Use `search` at L2 when there are more parameters or topologies than can be compared by hand (which subsystems,
how many planes, where they sit). It only proposes candidates; `contracts/design.py` still derives every verdict.

1. Design brief (you): from the current design-spec, list the candidate roles, two to six seed topologies with a
   physics reason each, and the search ranges, all inside the role rules
   (`assets/design-search/roles.json`, rules 1.1.0: per role the parameters the search may change, their ranges, the
   derived parameters (per-plane x/X0, the TOF flight path from its plane positions, a calorimeter's template
   sampling structure from `depth_x0` and its passive material), the calibration template and an assumed budget
   model; the TOF and calorimeter geometry use the design-geometry mapping's names, so a subsystem the search sets
   can be realized in Geant4. An earlier rules version stays as `roles-<version>.json`, so a recorded search
   replays; `materials.json`: Geant4 NIST values).
2. Search spec (`design-search-spec/1`, `contracts/schemas/design_search_spec.json`; a JSON file in the
   artifacts_dir): `design_spec` (path and sha256 of the current version), `base_candidate`, up to four `objectives`
   and any `constraints` (a requirement or constraint id, or a figure of merit with its denominator; each needs an
   F1 tool contract, so a `capability.unavailable` quantity cannot be one), `free_parameters` (`ref`, `range`,
   `kind`: `positions` with `n` and `min_spacing_m`, `continuous`, `integer`, `categorical` with `choices`). Required:
   `search_spec_version`, `design_spec`, `base_candidate`, `objectives`, `free_parameters`, `rules_version`,
   `materials_version`, `budget`, `optimizer` (`nsga2`, population, generations, seed) and `finalists`. Optional: `constraints`,
   `slots` (roles the search may add or drop, at most one subsystem per role), `envelope` (without it the
   envelope check is off: give it whenever the design-spec has an envelope constraint), `regenerate_budgets`
   (replaces the base subsystems' budget rows by the role-rule model, which changes the budget basis),
   `stopping`, `description`, `consistency_samples`, `inline_points_max`, and your seed designs as `proposals`
   (each with its `reason`; the tool checks only that it is not empty, so give the physics reason).

   ```sh
   python3 <plugin root>/skills/hep-detector/scripts/evaluate_design.py search --artifacts A \
       --spec search/SEARCH-1.spec.json --id SEARCH-1
   python3 <plugin root>/skills/hep-detector/scripts/evaluate_design.py expand --artifacts A \
       --search runs/SEARCH-1.computational-run.json --point K --candidate-id cand-K
   ```

3. `search` decodes each genome into overrides on the base candidate (an independent candidate when it drops a
   subsystem), skips invalid designs (spacing, envelope, overlap including TOF planes against the other extents and the tracking planes, nesting; they compete through their violation),
   computes F1 search values in process with the tool contracts' own tools, runs NSGA-II from Sobol designs and your
   proposals (flagged `proposer: llm`), and fixes the finalists before any official evaluation. It writes only
   `runs/SEARCH-*.computational-run.json` (`search_summary`): the search size (designs, topologies), the search
   front, the finalists, and a check that the finalists' search values equal `run`'s.
4. Search values are not evaluations: they inherit the F1 bound (mostly optimistic), support no verdict and are
   never reported as performance. `expand --search` accepts only finalists; then `run`, `budget`, `plan` and
   `report` as for any candidate; `report` lists each expanded finalist's search value minus its official value.
   Explain a large gap.
5. The best of many noisy or optimistic values is optimistic in expectation (winner's curse): never reselect among
   finalists after seeing official results, list every finalist, and add budget only as a new search (new id).
   A requirement change is a new design-spec version and a new search.
6. Geant4 search values (S2, adapter 0.5.0): `budget.geant4 > 0` with a `geant4` block (`realization` profile,
   `reco` simreco fields, `events`, `blocks`, `targets`: objective label -> simreco observable and beam particle,
   `top_k`, `generations`, `offspring`, optional `paired_threshold`, `threads`), run with `--geant4-work DIR` and
   `HEP_GEANT4_CONFIG`. The top_k designs of distinct topologies of the S1 front are refined on short element_sim and
   simreco runs (tail sources off, so the values are optimistic): each generation re-evaluates the survivors with
   mutated offspring (continuous genes) in one seed_group (S = H(search id, "search", gen-g)), so comparisons within a
   generation are paired; gate G-C2a measures Var(independent) / Var(paired) on the first generation and switches to
   independent seeds below the threshold (noted). One survivor per topology; the last survivors are the finalists
   (`fixed_from: geant4`). The runs stay in the work folder; `search_summary.seeds.geant4_search` lists every S.
   Only subsystems that carry geometry-mapping fields vary in Geant4. With rules 1.1.0 a TOF or calorimeter the
   search sets carries them (rules 1.0.0 gave such a subsystem F1 parameters only); the realization profile must
   still have the matching elements: `from-geometry` refuses a TOF plane count other than the profile's and needs one
   calorimeter with one passive and one active daughter.
7. F4 confirmation (C2.4): for each finalist and (figure of merit, denominator), `geometry`, then a Geant4 study whose
   runs are seeded S = H(study_id, role, point_id) with study_id = `confirmation_study_id(search id, design digest,
   figure of merit, denominator)` (`core/simulation/seeds.py`), `check_geant4_study.py label --upgrade` and `f4`.
   An evaluation whose run or study reuses a search seed is `design.contract_mismatch`, a search run (evidence role
   `search`) is never study evidence, and a seed repeated outside one seed_group is `design.seed_reuse` (CV-C2).
   `search --diagnose RUN` writes `runs/DIAG-*.computational-run.json`: each expanded finalist's F1 and Geant4 search
   values minus its official evaluation or F4 value (a diagnostic; it changes no verdict).

You may not invent parameters outside the role rules, skip the validity checks, edit any output, or report search
values or rank finalists yourself. The reply states the search size (and the Geant4 runs), that the search front is
non-binding, which finalists have official evaluations and which an F4 confirmation, and that no optimum is claimed.

## D3 Convergence

Goal: the evidence each driving requirement needs for compliance.

Higher fidelity, each through `evaluate_design.py`:

| Fidelity | Command | What it is |
|---|---|---|
| F2 | `run --fidelity F2` | `toy_spectrometer.py` resolution (config generated from the candidate; an estimate); in-field acceptance toy (`design_estimates.py infield-acceptance`: exact helices through offset apertures, seeded) |
| F3 | `response --upstream <core evaluation>` | resolution core with the candidate's alignment term and declared tail, and a parametrized `response` (forward folding) bound to it; assembled from an F1 core it stays optimistic |
| F3 | `run --figure-of-merit expected-precision --fidelity F3 --upstream <resolution> --upstream <charge confusion> --input-artifact <statistical-result>` | the expected precision written back from the hep-statistics Asimov fit (status asimov, `results.expected_relative_uncertainty`); its bound and fidelity vector follow the whole chain |
| F4 | `geometry --figure-of-merit F --denominator ... --id G`, then the Geant4 study (`geant4_run.py from-geometry` on `studies/G.geometry.json` and a realization profile, `element_sim`, `reco`, `table --f4-results`), then `f4 --study <record> --id SIM-...` | the geometry file of the study is generated from the candidate (`geometry` writes `geometry_ref` into the candidate, so run it before the candidate's other evaluations or they go stale; `contracts/rules/design_geometry.json`, mapping 1.1.0: optional TOF, calorimeter, field-extent and tracker-size fields) and sets `geometry_ref`; the evaluation records its own `geometry_ref` and its denominator must equal the geometry file's (CV-B2); only a record re-issued `validated-in-scope` by `check_geant4_study.py label --upgrade --results F4RESULTS --geometry G` (or `f4 --label-spec S --label-benchmarks B --label-convergence C --label-run-record R ... --label-results F4RESULTS --label-geometry G`, with `--label-reference-record` and `--label-variations` passed on too) counts as F4, and `f4` writes nothing for a record whose upgrade was refused (exit 3, `upgrade-refused`); a resolution qualifies only through the four conditions of the qualification path (material definition, field, reconstruction closure, the multiple-scattering reference; `geant4-study-protocol.md` section 5), charge confusion not until a tail reference exists (D0-b), shower containment not at all; a refused upgrade, or a validated record without `results.<figure of merit>`, makes `f4` incomplete (exit 3) with the reasons and gaps; the uncertainty is the study's coverage-0.90 object, statistical (+) replica spread (+) the qualifying reference's tolerance (D0-c), exact for a counting figure of merit, and a qualified F4 resolution is judged against the floor of its qualification path (adequacy `f4_qualified_min_relative_uncertainty`, provisional) instead of the F1-bias floor; without alignment, calibration non-uniformity, noise and digitization and pattern recognition simulated a resolution or confusion rate stays optimistic; the physics-list spread is a model envelope whose ends are compared separately |

- The adequacy table gives per figure of merit the compliance fidelity (resolution F3; charge confusion F4 with tails
  validated by data; PID rejection F4; acceptance F2 in-field) and the upstreams compliance needs. An F1 result can
  exclude a candidate but never approve a physics requirement.
- Candidates are finally compared on expected measurement precision through the forward chain response ->
  measurement-spec -> Asimov statistical-result (hep-statistics); a chain built on optimistic F1 inputs can only
  exclude.
- Every inconclusive requirement of a candidate that survives screening gets a proposed disposition in the report
  (accept risk or next study); a derived requirement names in `covered_by` the driving requirement whose H4
  disposition covers it, and a screened-out candidate shows why it has none.
- A hard constraint lists the subsystems it covers (`subsystems`); a candidate that lacks one cannot pass it
  (`chain.incomplete`, the subsystem listed as missing), and the report shows the scope.
- Charge-confusion compliance needs a rigidity-scale-offset evaluation whose measured offset covers the offset the
  requirement assumes: |measured - assumed| + z sigma within the assumed tolerance (a zero or omitted tolerance is covered only
  by a measured offset exactly equal to the assumed one with no uncertainty, which no real measurement gives:
  declare a realistic tolerance; an offset evaluation without an uncertainty counts with sigma 0, so give it one).
- The report ranks candidates on expected precision only when the comparison basis holds and every candidate that
  survives screening has a non-optimistic expected-precision evaluation with the same fidelity vector and
  denominator; otherwise it states every reason the ranking is refused. A ranking is never a global optimum.
- Pareto front (M4): declare the axes in `comparison_basis.pareto_axes` (expected-precision and, for example,
  mass-budget). The report gives the non-dominated candidates among those that survive screening under the same gates
  as the ranking; a candidate is dominated only by one no worse on every axis and better on one beyond the combined
  1-sigma uncertainties. Not a global optimum.

Design space (M4). `scan --candidate C --figure-of-merit F --denominator ... --vary SID.parameters.NAME=V1,V2,...
--id SCAN-...` runs the operation over a grid (the candidate's own values included) in a scratch copy and stores every
point in one `runs/SCAN-*.computational-run.json` (`scan_summary`) with the local elasticities d ln F / d ln parameter
at the candidate's own values. It writes no evaluation: a point takes part in no aggregation, supports no verdict and
is exempt from the orphan-run rule (an evaluation that names a scan summary as its run is
`design.scan_point_not_expanded`). Bring a point into comparison with `expand --scan <run> --point K --candidate-id N`
(a candidate derived from the scanned one) and evaluate it with `run` like any candidate. Operations with required
upstreams are not scanned: scan their upstream figure of merit.

Reruns. Evaluations bind the candidate by the parameters they read (`binding: parameters`, `parameter_digest`): a
change to another parameter leaves them current, a change to a parameter they read makes them stale (and everything
downstream of them). Rerun a stale one with `--replace` (`run` and `budget`; `response --replace` currently stops on its existing
  response file, so rerun a response under a new id; a current one is never
  replaced); `f4`, `f5` and `calibration` have no `--replace`, so a stale F4 or F5 evaluation or a calibration is
  rerun under a new id. For a whole chain use
`hep-computing/scripts/run_workflow.py --incremental` with one step per evaluation: give each step a
`parameter_digest` command (the same `evaluate_design.py` call with `--digest-only`) that replaces the candidate
file in its skip key, and a step id different from the evaluation id (run_workflow writes
`runs/<step id>.computational-run.json`). A step is skipped only when argv, scripts, plugin release digest,
environment and inputs are unchanged; never when the release digest is unknown.

## D4 Review

- The compliance matrix with its proposed dispositions, the at-risk flags of screening and the maturity per
  requirement come from `evaluate_design.py report`; no
  verdict is written by hand.
- Independent review of the derived report: hep-authoring (`references/independent-review.md`); a closed agent review
  is advisory input to the human reviewer, not a review record by a reviewer other than the author.
- Gate H4 (`design-baseline`), after H1-H3 are clear: a human approves the report, the evaluations it covers and one
  disposition per inconclusive driving requirement of a candidate that survives screening (`dispositions[]`:
  `accept-risk` or `next-study`, with a note). Only such a record sets the review axis, and only while no earlier gate
  flag is open, the report it lists still equals the one recomputed now and no hash changed;
  the report then says `baseline: baselined`. The axis is advisory: the actor is self-declared, and formal approval
  is a trusted gate outside the agent. An infeasible design is an allowed outcome; return to D1 or stop.
- Measurements (F5): a prototype or test-beam dataset-record carries a `design_measurement` (figure of merit,
  denominator, value, uncertainty, and the configuration it was measured in; an empty configuration binds
  nothing, so list the configuration parameters). `evaluate_design.py f5 --dataset ...`
  writes the evaluation; it decides only after a `measurement-acceptance` record by a human (as for every gate, `actor.kind`
  is declared by the writer and trusted, not verified by the tool) lists the dataset and binds the
  candidate by the digest of those configuration parameters (`binding: parameters`, `parameter_digest`); a measured
  configuration that differs from the candidate is `domain.mismatch`.

## Engineering couplings and calibration

- Couplings between subsystems are evaluations whose parameters span them: `run --figure-of-merit material-budget`
  sums the measuring layers, passive material and every subsystem's `services_x_over_x0`, so a change to another
  subsystem's services makes it stale and a change elsewhere does not.
- Every subsystem declares its in-situ calibration (method and at least one control sample;
  `design.calibration_incomplete` otherwise). The rigidity-scale and alignment residuals a calibration leaves enter the
  expected precision as nuisances: `evaluate_design.py calibration --candidate C --residual SID.parameters.NAME
  --mode scale|inverse-offset --model <spectrum model> --id CAL-... --measurement-spec <spec> --out-spec <new spec>`
  runs `propagate_scale_distortion.py` on the candidate's residual (binned yield shifts, up/down variations and
  covariance blocks; its run records the residual's parameter digest; `calibration` has no `--digest-only` and no
  `--replace`, so a rerun needs a new `--id`) and writes a new measurement-spec version with that shape systematic; the
  hep-statistics Asimov fit then gives its effect on the expected precision.

## Verdicts and reason codes

Per evaluation the first matching row of an 18-row table decides; per requirement and effective candidate the
evaluations are aggregated (the report lists used and skipped ones; a skipped unfavorable evaluation still blocks a
pass). Codes the report uses:

| Code | Meaning | Next step |
|---|---|---|
| `bound.excludes` | an optimistic bound misses the target: fail | change the candidate or the requirement |
| `bound.direction` | the bound cannot decide (an optimistic bound meets the target, or a conservative bound misses it) | higher fidelity |
| `bound.confirms` | a conservative bound meets the target: pass | none |
| `bound.mixed` | one evaluation's own bound and its upstreams' bounds combine to both optimistic and conservative, or a non-monotonic input meets a bound that is not an estimate | evaluate with consistent bounds |
| `rule.unmatched` | no verdict rule matches the evaluation's state | report it; never decide by hand |
| `fidelity.insufficient` | below the screening or compliance fidelity | higher fidelity |
| `estimate.decides`, `margin.within_uncertainty`, `uncertainty.missing` | an estimate decides (pass or fail) at the coverage CL, straddles the target, or has no usable uncertainty | decided pass: none; decided fail: change the candidate or the requirement; otherwise more precise evidence |
| `chain.incomplete`, `domain.mismatch`, `budget.incomplete` | a required upstream is missing or fails its check, or a hard constraint's subsystem is absent; a validity condition fails, the denominator differs from the requirement's, or the measured or simulated configuration differs from the candidate; a budget row is missing or lacks an estimate or an uncertainty | supply or correct it |
| `evidence.stale`, `evidence.unresolved`, `evidence.invalid` | an input changed, is unbound or invalid | stale: rerun with `--replace` (same id) for `run` and `budget`, else under a new id; unresolved or invalid: fix the input, then rerun under a new id |
| `evidence.conflict`, `evidence.excluded_adverse`, `evidence.orphan_run` | contradicting evidence (also several evaluations of one requirement that disagree), unfavorable evidence excluded, a run without its evaluation | inspect the contracts and validity domains |
| `evidence.unreviewed` | an F5 evaluation no `measurement-acceptance` record has approved | the human acceptance record |
| `capability.unavailable` | no evaluator at that fidelity | record it; never estimate a number; it never replaces an available lower-fidelity evaluation: run the screening fidelity first (`design.py`
does not yet flag such a record, so the report can otherwise propose accept-risk) |
| `design.derived_uncovered`, `design.constraint_scope_missing` (error) | a derived requirement without a driving `covered_by`; a hard constraint without `subsystems` | complete the design-spec (a new version) |
| `design.scan_point_not_expanded` (error) | an evaluation that names a scan summary as its run | `expand` the point and evaluate the new candidate |
| `design.search_point_not_expanded` (error) | an evaluation that names a search summary as its run | `expand --search` a finalist and evaluate the new candidate |
| `design.contract_mismatch` (error) | an evaluation, run, output, config file, geometry or study that does not match its contract or candidate | regenerate it with `evaluate_design.py`; never edit it |

The adequacy table is an initial default until physics review: every pass is reported as provisional.

## Never

- Write or edit a verdict, a maturity, a stale marker, `screened_out` or `at-risk` into any file.
- Fill in fidelity, bound, parameter_refs or a value by hand; edit an evaluation, run or output after it is written.
- Put a number on a figure of merit without an evaluator (`capability.unavailable` instead).
- Report a search value as a result, or write the search population as candidates (only expanded finalists are).
- Rank candidates or draw a Pareto front without a holding `comparison_basis` and non-optimistic evaluations of the
  same fidelity vector and denominator; claim a global optimum.
- Treat a decision record written by an agent as approval: gates need a human actor.

<!-- example -->
Example: `examples/design-space-spectrometer` designs an AMS-like space spectrometer (public facts from the
`experiment:ams-02` profile ledger) with three candidates at F1: the probe with a too-short lever arm fails the
resolution and charge-confusion requirements, the two reasonable candidates are inconclusive on resolution and charge
confusion (its REQ-CC-001 declares a zero offset tolerance, so charge confusion cannot reach compliance there
with any real offset measurement), and the
equal-mass basis holds for the two that survive screening; ranking and Pareto front are refused until expected-precision
evaluations exist.
`examples/design-minimal-spectrometer` (J15, synthetic) takes three candidates from F1 to F4 with Geant4: the 1 GV
resolution studies qualify through the four conditions and decide, the 100 GV ones are refused on a recorded
reference-control gap, charge confusion waits for D0-b and shower containment has no reference.
`examples/design-search-j16` (J16, synthetic) runs the search on Examples A and B: the finalists go through the
report gates (basis, refused ranking, `capability.unavailable` rows), and one Example A finalist's F4 confirmation
is shown as recorded (its upgrade refused on a reference control).
<!-- /example -->
