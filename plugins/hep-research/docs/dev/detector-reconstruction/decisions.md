# Detector reconstruction plan v9.2: decisions

User's answer, 2026-11-06, verbatim: "Q2, Q3, please choose ceph space. Q6 yes, Q7 try with best setting. other questions, please give me suggestion."

Earlier, 2026-11-06, verbatim: "choose best version for this task"; "go ahead with the R27 first reply".

| ID | Decision | Basis |
| --- | --- | --- |
| Q1 | Baseline `580dc79e` (plugin 0.56.0, contracts 3.19.0), by clone without network | Latest release; differs from the tag only by a custodian record |
| Q2 | `<private>` is a dedicated folder on the group file system, ACLs removed, mode 700 | User chose ceph. The parent's default ACLs would have shared a plain folder, so they were removed and the result checked with `getfacl` |
| Q3 | `<workdir>` is a separate folder in the group space; not yet created. Every write there is asked each time (R03) | User chose ceph |
| Q6 | Tiny confirmation job: yes, as the first job, after Q4 and Q5 | User |
| Q7 | Delegated to the agent ("try with best setting"). Tiny job: account ams, `edr2-al9_short_serial`, no QoS, 1 CPU, 2000 MB, 10 min. Unit-suite job: same partition, 6 CPUs, default memory per CPU, 2 h. Re-checked live before each submission | Partition on a node set the running g4sim array does not use; unit-suite size from the recorded 25 min at `--jobs 6` |
| Q4 | Option (b): environment `<workdir>/env/py313`, built from `requirements-ci.lock`, recorded as a deviation; also ask the site for Python >= 3.13 (option a) | Agent's suggestion, accepted by the user |
| Q5 | Yes: this account counts as a disposable test environment for agent-written jobs, on synthetic data only, each job approved by SHA-256. Known exposure: SSH key and GitHub token are reachable from any job | Agent's suggestion, accepted by the user |
| Q8 | Login node allowed: `freeze`, `verify-bundle`, dry-run `submit`/`resubmit`, `report`; short single test modules; `run_all_checks.py --part static` with `--jobs 2`. Not allowed for now: `executor_capabilities.py qualify` | Agent's suggestion, accepted by the user |
| D1 | Re-baseline onto 0.57.0 before T06, once it is released | Agent's suggestion, accepted by the user |
| D2 | Reconstruction defines conditions and alignment payloads and reuses g4sim's `geometry_id`; if g4sim S9 is triggered it uses those payloads, which changes a g4sim card and needs the user's approval then | Agent's suggestion, accepted by the user |

User's answer, 2026-11-06, verbatim: "as suggested, approve the commands, kill the bfs search". The approval covers the five commands listed in that reply, and no others.

## K01-K18 drafts

Drafted 2026-11-06 on contracts 3.19.0. Everything here is provisional. "Fixed" means the agent may fix it under R02. "Needs the user" stays Unresolved, and its default applies meanwhile. No threshold, target or budget value is set here.

### K01 scope (agent; hep-detector)

- **Basis:** Section 6, coverage.md (corrected after T11: no family has full documentation; 27 have partial text; 11 have no text, tool or run).
- **Options:** keep all F01-F38; or narrow to families with existing text.
- **Fixed:** keep all, with variants. Not-applicable only with a physical or readout reason. Support levels are coverage.md's six columns; the BP crosswalk is there.
- **Rationale:** narrowing is ruled out by Section 1.3 item 6.
- **Scope, unresolved:** T11 owns the gaps. coverage.md's judgement calls stay open for review.
- **Impact:** T11 is the largest writing task; the 11 families need sources first (R14: without network approval those cells stay `source-unverified`).

### K02 stack (agent for probes; user for the rest)

- **Basis, read-only probes:** Geant4 11.4.3 (conda env, login node). ROOT 6.32.10 (conda env) and 6.40.02 (module, confirmed in job 7470150). `simreco` in the tree, simulated events only. No ACTS, DD4hep or EDM4hep in the conda envs or modules.
- **CVMFS:** `/cvmfs/sft.cern.ch` is mounted, but listings of `lcg/views` and `lcg/releases/acts` stalled on the login node and past 240 s in job 7470680. Not a dependable route.
- **conda-forge (read-only queries):** `acts-core` 48.2.0, MPL-2.0, core library only as far as its dependencies show. See t03-selection.md.
- **Options:** decided per workflow in T03 (R16): existing tool, library adapter, native executable.
- **Fixed:** no reconstruction backend is confirmed. Geant4 and ROOT are simulation and I/O tools, not reconstruction backends. On Slurm a backend is confirmed only after an approved job has run it.
- **Needs the user:** installation, network, GPU, each submission, the backend's environment.
- **Default:** unavailable; T03 is `blocked-by-decision` with a ranked option list.
- **Impact:** blocks T07-T09 and every native workflow. This is the main blocker of P2.

### K03 data (agent for synthetic; user for the rest)

- **Basis:** no reconstruction fixture exists at the F-family level. g4sim's hit format (`simulation_hits`) arrives at S4, not yet.
- **Options:** agent-generated synthetic fixtures; simulated events from installed Geant4; public open data (download); private data.
- **Fixed:** synthetic fixtures, role labelled in every record.
- **Needs the user:** downloads, private or production data.
- **Default:** synthetic only, so the data-control layer stays incomplete (R14). Simulation never stands in for data (Section 12.1).
- **Impact:** without an obtainable dataset, no data-control claim is possible.

### K04 contract map (agent)

See contract-map.md. Fixed provisionally: `recipe`, `qualification_record` and `decision_record` get distinct names; `operator_semantics` is reused in part; `tool_contract` stays unchanged. Exit condition: T02 with W1-W7.

### K05 quantities (agent; hep-detector)

- **Basis:** Sections 8.2, 8.4.
- **Options:** free-text quantities; a closed vocabulary; a vocabulary with required semantics fields.
- **Fixed:** every port states quantity kind, unit, basis or surface, reference hypothesis and observation level. Energy kinds stay separate: deposited, visible, calibrated, recoil, incident. Periodic angles state period and axis or vector. Electron counts are not energy; spectral power is not counts.
- **Rationale:** matching units do not establish matching meaning.
- **Scope, unresolved:** the vocabulary's exact list comes with T02.
- **Impact:** positive and negative cases: same unit with different kind refused; rank-deficient targets delivered as identifiable components only.

### K06 model (agent; hep-detector)

- **Basis:** Sections 8.4, 11, BP01-BP15.
- **Options:** model assumptions as free notes; as checked necessary conditions.
- **Fixed:** each recipe declares noise, threshold or selection, censoring, correlations, template or response. An undeclared necessary assumption counts as unknown, never true (SEL05). Summaries from one source are not assumed independent.
- **Scope, unresolved:** per-method models come with T03 and T11.
- **Impact:** every required recipe needs a model-incompatible fixture that ends out-of-domain or failed.

### K07 conditions (agent; detector and computing)

- **Basis:** Section 9, R32, D2.
- **Options:** tags; resolved payload identities; a conditions service (ruled out by Section 3.1).
- **Fixed:** runs record resolved payload identities, not tags. R32's fields are the payload shape. Validity on one time axis is the intersection of dependency IOVs; different coordinates are predicates that must all hold. A work unit crossing an IOV binds separately, subdivides or uses a time-varying model. Unknown dependencies disable caching at that level. Nominal geometry identity is g4sim's `geometry_id`.
- **Rationale:** a floating tag cannot reproduce a run.
- **Scope, unresolved:** G06 stays: the fixed final-round rule does not change.
- **Impact:** CAI-T06-1 to 4; A37 and Section 9.6 stay required in T10 and T12.

### K08 evidence (agent; user for confirmation grouping)

- **Basis:** Sections 11.1, 12.1.
- **Options:** one evidence level; separate scopes.
- **Fixed:** synthetic, simulation and data-control evidence each state their own scope. Sample roles (tuning, calibration, selection, confirmation) stay separate. Grouping keys include run, conditions source, noise realization and fixture derivation.
- **Needs the user:** confirmation-role grouping, with K18.
- **Default:** no confirmation claim.

### K09 quality (agent drafts; user freezes)

- **Basis:** Sections 11.3, 11.4. No universal value exists (Section 14.3).
- **Options:** freeze per recipe at T04; or per family at T11.
- **Fixed:** metric families and denominators only, per Section 11.3.1. Thresholds are written per recipe in T04, after T03 names the recipes.
- **Needs the user:** freezing thresholds.
- **Default:** no pass/fail scientific-quality claim.
- **Impact:** low-statistics bins cannot pass; zero observed failures is not a pass.

### K10 budgets (agent for algorithmic; user for Slurm)

- **Basis:** Sections 10.5, 14.2.
- **Fixed:** algorithmic budgets (seeds, branches, components, iterations) come from each method's sources or existing recipe, with their physics effect evaluated. Calibration rounds do not change.
- **Needs the user:** anything that becomes a Slurm request or campaign limit. No default: user must choose.
- **Default:** a limit-driven shrink makes the result inconclusive.

### K11 AI evaluation (agent for development set; user for holdout)

- **Basis:** Sections 14.2-14.5, R22.
- **Fixed:** four task groups (executable, insufficient information, missing dependency or out of domain, runtime or quality failure), stratified by family, deliverable, executability and risk. Distinct tasks are the statistical unit; repeats measure variability only. Near-duplicates are grouped.
- **Needs the user:** holdout custody, system under test, harness, reference-answer rules, false-success definition.
- **Recommended:** a person or a session with no access to this worktree writes and holds the holdout, with only SHA-256 values recorded. False success means reporting execution, a pass or a capability without the evidence for it.
- **Default:** holdout not established. T13 and T16 are `blocked-by-decision`, and every report says "holdout independence not established".

### K12 performance (agent drafts; user sets targets)

- **Basis:** Section 14.2.
- **Fixed:** comparisons fix the same scientific work and stage, count initialization, I/O, probes and failed trials, and separate cold from warm. Workload units fit the task (event, frame, scan setting).
- **Needs the user:** the targets.
- **Default:** no speed or cost claim. A13 stays `blocked-by-resource` until a GPU is chosen (R30).

### K13 compatibility (agent)

- **Basis:** Section 17.3.
- **Fixed:** strictest option. Old recipes, contracts and validators keep their behaviour. An unknown required extension stops the reader. Breaking changes need a version boundary, migration and comparison fixtures. Scientific fields are never dropped silently.
- **Impact:** every contract task includes an old-recipe check.

### K14 task readiness (agent)

- **Basis:** Section 16.
- **Fixed:** T05 writes the task sheets, with the A-ID to T-ID table (R20) and the `CAI-` table (R37). P1 sheets can be complete now; P2 sheets list blockers and options until K02 is decided.

### K15 recognition (agent)

- **Basis:** Sections 5.5, 5.6, R19.
- **Fixed:** signatures are per product and scope, multi-label, with each fact keeping value, scope, source, method and validity. File names, array shapes and model confidence are not evidence. Values an LLM extracts stay unconfirmed until checked. Conflicts stay visible.
- **Scope, unresolved:** first known readers are the plugin's own JSON and CSV products. `uproot` is not in the locked environment, so ROOT files are not readable by the runtime until the user approves that extra. No recognition is claimed without a runtime reader.
- **Impact:** A43-A49, A59; unknown formats end in restricted delivery.

### K16 selection (agent for rules; user for gates)

- **Basis:** Sections 5.9, 5.11.
- **Fixed:** select at dataset, run or conditions-stratum level. Keep the Pareto set when no candidate dominates. On insufficient evidence use a predeclared conservative baseline, called a "qualified default choice". No invented weights.
- **Needs the user:** hard gates and the quality objective.
- **Default:** no claim beyond the declared baseline.
- **Impact:** a per-event policy would be a separate recipe, tested as a whole.

### K17 search budget (agent; user for Slurm)

- **Basis:** Section 5.10.
- **Fixed:** only parameters and ranges in the method card are tunable. Trials are never production quality. All trials and failures are kept and costed. Lower fidelity is not assumed to be the same problem.
- **Needs the user:** trial budgets that become Slurm requests. Same default as K10.

### K18 selection evidence (agent for rules; user for data)

- **Basis:** Sections 5.10, 14.5.
- **Fixed:** development, selection and confirmation are split by group, and the selector is fixed before confirmation. An optional ML ranker adds nothing required.
- **Needs the user:** confirmation data.
- **Default:** no post-selection quality claim.
- **Impact:** A50-A60 and DS1-DS3 can run on artificial fixtures, which test rules only.

## Pending for the user

| Item | Needed by | Recommended | Default meanwhile |
| --- | --- | --- | --- |
| K11 holdout and harness | T13, T16 | See K11 | Not established |
| K09 thresholds | T04 | Freeze per recipe | No pass/fail claim |
| K16 gates, objective | T15b | With K09 | Declared baseline only |
| K12 targets | P5 | After P2 | No speed claim |
| K08, K18 confirmation | P6 | With K03 | No confirmation claim |
| K10, K17 Slurm limits | First campaign. No default: user must choose | Asked at that campaign's approval | None submitted |

## Execution method

User's answer, 2026-11-06, verbatim: "use subagent-driven, show the backup commands". The finish plan runs by subagent-driven development, and the backup commands are shown before they run (Task A1).

## K02 and K03 decision

User's answer, 2026-11-06, verbatim: "approve K02 as recommended, show the install commands". Recommendation accepted: `acts-core` in a new environment under `<workdir>/env/`, confirmed by one approved job; calorimetry and photon likelihood as labelled development bindings; data synthetic or Geant4-simulated. Consequences recorded: no native backend for those two workflows, a gap in required delivery; no data-control evidence. This approves the direction. Install commands and the confirmation job each need their own approval (R03, R15).

Install approved, verbatim: "approve the install commands". Job 7470886 approved, verbatim: "approve the submission".

Result: `acts-core` 48.2.0 is confirmed at backend-smoke level on `hpa-wn28` (Section 12.1): built in 24 s with conda gcc 15.3.0, version check, surface round trip and off-surface refusal passed. Confirmed scope: it builds, links and runs here. Nothing about tracking quality. `libActsCore.so` SHA-256 `d1ac87d045b0a055301a30b14b003f876dde8bbdcd2b3b984b0559363b0297a7`.

## T04 draft

User's answer, 2026-11-06, verbatim: "accept the draft, use a fresh reviewer". t04-values-draft.md is accepted as the working draft. Nothing is frozen: each workflow's gates are frozen just before its first run, once bin edges exist. A fresh reviewer checks the statistical design first.

## T04 version 3

User's answer, 2026-11-06, verbatim: "accept version 3, third review before the freeze". t04-values-v3.md is the working draft. Nothing is frozen. A third fresh review of the then-current draft happens before Freeze A, which comes before any development run.

## T04 section 18 stops

User's answer, 2026-11-06, verbatim: "go ahead with 1, 2, 3(a) and 4 as recommended". Meaning, from the options then shown: (1) the exact sum becomes T08's efficiency reference and section 4.2's values are recomputed; (2) direction enters pulls through mapped angles and the tangent plane; (3a) a corrected rerun with new events and about 4 times as many at `N_exp` 80 and 120, keeping 80 if it clears and otherwise raising the edge to 120; (4) `PATCH` becomes 200. Nothing is frozen. Rule and results: t04-v4-dispositions.md.


## T04 section 16

User's answer, 2026-11-06, verbatim: "accept the section 16 recommendations, vertex floor 0.95". Each recommendation of section 16 of t04-values-v4.md is accepted, and the vertex finding floor is 0.95. This is not Freeze A, which needs the user's own word on the final text. The `element_sim` spec for K16 was not named.

## T08 width stop

User's answers, 2026-11-06, verbatim: "give me best suggestion. I want correct method and right result." then "go ahead with the T08 diagnostic". The third section 18 stop, iso E2 position width, is to be diagnosed, not accepted. Freeze A waits.

User's answer, 2026-11-06, verbatim: "go ahead with option A". The position uncertainty of section 7.1 is to be tested with an added variance term; the estimator is kept.

User's answer, 2026-11-06, verbatim: "adopt the new uncertainty in section 7.1". Section 7.1's one-peak position uncertainty is replaced by the tested form. T08's reference reruns against the unchanged section 18 rule.

## Freeze A

User's answer, 2026-11-06, verbatim: "freeze A as listed". Frozen by hash, with the generators, check and job logs listed in freeze-a.md:

| File | SHA-256 |
| --- | --- |
| t04-values-v4.md | `c55ff22fee9268e5cf245aee43ae673920baf002086946071cba5b5920789105` |
| t04-prereg.md | `39495c3f7db0cded7f88b45711a9457f438be0cbd4113370880d69866448a151` |
| t07-t09-task-sheets.md | `01f3509156734372a725eba77b3604935bf420b74fc5f9670fed4348269906f0` |
| freeze-a.md | `d1befec78733523619e29deac7588fb6a06129b98c4d87c9535abd3110468243` |

From here, a change to any of these is a section 2.3 amendment by the user, labelled "after development", reported under both rules. Outside this freeze: T07's generator, an addendum on the user's word before any T07 development run; the `element_sim` spec, before T15b; K12 targets, after P2; Freeze B items.


## T06 readings, by the coordinator

Rulings under the finish plan, each reversible by the user.

- **Evidence stage for routine use.** The plan names no minimum stage. Passed `simulation-pilot` evidence may support `routine`, only where Section 8.4 check 6 holds: the tested domain covers the request, and required checks match and are constructible. Section 5.10, Section 12.1, R14 and R21 still apply, and K09 thresholds may narrow this.
- **Limits accepted, not defects.** Without a declared estimator, `reported` values are compared on exactly consistent data only, and under a prior only for rows the data alone fix, so a wrong value elsewhere is not caught. `constructible` is a declared boolean the plugin cannot yet verify.
- **Owners of items outside T06's contract scope.** Section 8.5 forms and learned ports: T11. Section 10.4 fields: T12. Section 8.7 hashes and the method index: T15a.
- **Connection roles.** Refused only for truth into a data-side port (Section 8.4 check 3) and for `training-calibration` with `validation`, either direction. The second applies K08's separation to port roles, as a reading.
- **Name-based and silent limits.** `track_as_spatial` is a name check on free-text axes. `iov_intersection` returns `None` for mixed closures without the reason.
- **Comparator floor.** `relative_tolerance` has a floor of 1e-15 beside its ceiling, by Sections 14.1 and 9.5.
- **Degenerate components.** A component on a design degenerate at the tolerance but not exactly, or with weights in the row space at the tolerance but not exactly, gets the warning `reconstruction.estimate.component_unchecked` and is not checked. A float comparison was rejected because its parameter error can exceed the tolerance. Accepted limit.
- **Numerical rank.** Judged on unit-norm columns, so parameter units do not matter. Rows in different units are not scaled. Accepted limit.
- **Energy loss.** dE/dx is read as a per-length track quantity, not a per-event energy a sensor delivers, so it does not trigger `capability_mismatch`.
- **`affected_payloads`.** Returns `None` when its input holds anything other than payload documents with a string `payload_id`, and `[]` only for a declared empty set or no change (Section 9.4).
- **Zero designs.** On an all-zero design only the zero combination is determined (W2, A34).
- **Global scans.** They have no comparator, so rank is judged at the tolerance ceiling. Column scaling removes units, not an offset, so an uncentred polynomial coordinate can read rank-deficient, failing towards "not determined". Centring is the accepted form. Accepted limit.
- **Constraint rows.** A constraint row is a row at its own scale, and rows are not scaled: state a constraint at the design's scale. Accepted limit.
- **Float32 probability operators.** Refused at the ceiling, a true reading of the stored numbers: renormalize in double. `yr` is not in `UNIT_SCALES`, because a year needs a choice.
- **Row-normalized operators.** `_check_operator` reads columns, so a row-normalized operator with `interpretation: probability` is refused unless its columns also sum to at most 1. Ruling: keep this, the cautious reading. If wrong, an honest operator is refused loudly and the rule is widened later; no wrong result passes.

## T14 rulings

User's answer, 2026-11-07, verbatim: "A and A, record it as a reading, kill the bfs". Meaning, from the options then shown: K15's "plugin's own JSON" includes real plugin artifacts, so T14 reads envelope artifacts such as `response` through their existing validators and reports `container`, `product_schema` and `artifact_type`, with no physics inferred. A conflict on any branch of an OR gives `conflicting`, even if another branch would pass. `CANDIDATES_BY_CLUE` is a reading from Sections 5.15, W1-W5 and W7, not an owner's sign-off, and is to be rechecked before anything depends on it.

### T14 readings, by the coordinator

Rulings under the finish plan, each reversible by the user.

- **Budget.** Holds probes, bytes, seconds, memory and tools, all required (Section 5.6 item 5).
- **Limits of that budget, accepted.** Seconds are enforced between Python calls during a probe, so one C call or a hung file system runs to its end and is caught on return; a hard stop would need a separate process. The watch makes reads about 5 times slower, and that cost is charged. Memory is the rise of the process's peak resident size, so an earlier higher peak hides a rise below it. Memory stops are tested with a mocked peak.
- **Probe sizes.** JSON 16 MiB, CSV 64 KiB, 1024 documents per file: named fixed parameters, not physics.
- **`state: complete`.** Means no open conflict.
- **Caller's label.** Must match `product_id` for a single product, or it is a conflict.
- **CSV stops.** `no-rows-in-window`, `no-header`, `not-comma-separated`.
- **Declarations.** A declaration must state its `kind`.
- **Runtime probes.** None is required yet, so a conflict is named but none resolves automatically.
- **Keeping `container`.** A file of no known schema that parsed keeps `container: json`. A K13 stop, or a known schema refused on its rules, keeps nothing.
- **Artifacts needing a project.** 16 real artifacts in `profiles/` and `examples/ams-flux-ratio` stop at `vocab.unknown_term`: they use profile terms, which the validator gets only from a project, and the inspector is given none. Fails closed. Passing a project in is later work. Accepted limit.
- **Survey of tracked JSON, once, 2,084 files.** 1,900 give a fact: 515 artifact facts in 14 kinds, 1,385 `container` only. 184 give none: 167 invalid fixtures, refused by design, the 16 above, and one skill asset refused on its own rules.
- **Import cost.** The readers' one-time import is outside the budget, and a stop waits for any import to end, so nothing is left half loaded.
- **Hostile strings.** A quadratic regex in `contracts/validate.py`, an existing statistical rule outside T14, can hold the validator for a very long time on a hostile string, about a day at 7 MB by the reviewer's extrapolation. It falls in the accepted limit on one C call. Open, reported to the user.
- **Project lookup.** An artifact's result depends on any project found above the working directory, and those reads are not charged to `bytes`. Fails closed.
- **Stop reasons.** `required_extensions` on an artifact stops it with the K13 code. A K13 or rule refusal outranks "no known schema" in a mixed list. `readers-unavailable` is a new stop reason. A 600-product file needs a seconds budget near 6.

### Changes to T14 from T15a's review

`judge_candidates` changed after commit b5dbb788. No T14 test changed, and 9 were added. Conflict outranks unsatisfied at every level, as the user's ruling requires. A fact outside the signature's product counts for nothing. `product_schema` has no rule of its own: two files under one label stay two labels (K15), and a schema conflict is what `_conflicts` names, two values in one scope or a statement about the product that nothing read in it matches. Two values of a `constraint.` key in scopes of one product conflict; the inspector keeps those facts at owner scope, so the prefix test acts only on a hand-written window. All other keys stay multi-label. A product beside its payload or an envelope artifact stays `satisfied`. A top-level AND holding a conflict and an unsatisfied item is `conflicting`, so the state can be `needs-evidence` though the unsatisfied item remains; the candidate is out either way, and the key stays in the reason.

## T15a readings, by the coordinator

Rulings under the finish plan, each reversible by the user.

- **Baseline.** Must itself be routine-eligible (glossary, "Qualified / unqualified"; Section 5.9 item 5). An eligible baseline is used outside a tie, per Section 5.9 item 4.
- **`runtime_evidence: null`.** Counts as no available backend: the plan is silent, K02 states it, and Sections 5.5 and 8.7 fit. `no-available-backend` is an open block, per Section 8.7.
- **`needs-evidence` against `abstained`.** Follows whether information could lift the block, as SEL08 and Section 5.3 step 7 fit; `abstained` stays for failed checks, unsatisfied conditions and limits.
- **`role`.** Both sidecars fix it to `artificial-witness`, a self-label, so a real index or policy is refused for now. T15b must gate the witness exception in `_quality` on that role when widening it.
- **`quality_contract`.** Is `{contract_id, required_checks}`. What a contract contains stays K16's. The tolerance is a stand-in, open for K16.
- **Other.** Qualification candidates are widened by Section 5.10. `sample_groups` is added to the policy and the record. Rule and reader hashes digest source files, so a later edit makes earlier records stale, as Sections 8.7, 9.4 and 9.8 require: store no golden record.
- **Failure against missing evidence (DS1, Section 8.4 check 6).** Excluded: evidence stating `failed`, or a `fail` row on a check the recipe or the contract requires. A qualification candidate: evidence stating `inconclusive` or `unvalidated`, or a required row inconclusive, skipped, not applicable or absent.
- **No listed checks.** A recipe with `checks: []` stays `insufficient-evidence`, even if it covers the contract. This is the coordinator's ruling: the cautious one.
- **Change to T06.** `_check_evidence` refuses two rows for one check (`reconstruction.evidence.duplicate_check`). It only refuses more, and no T06 test changed.
- **For K16.** A contract with a check only the whole can pass empties `expert_support`.


## Phase D start

User's answer, 2026-11-07, verbatim: "approve the backup, U12 A, U9 later, start T07". U12: no native backend for calorimetry or photon likelihood is sought; T08 and T09 use development bindings, and the lack is a recorded gap. U9: the K11 holdout owner stays open until the user names one, needed by Phase G.

## T07 stage 1 build

User's answer, 2026-11-07, verbatim: "approve the T07 stage 1 build", which accepted the reading shown with it: this job is not a T07 development run, since it uses seed block 6 and a hand-set straight-line case only. A later build under the same reading needs no new ruling while that stays true.

## Freeze A amendment 1: direction

User's answer, 2026-11-07, verbatim: "A, A, A, one amendment before development". Meaning, from the options shown: (1) CAI fixtures get a separate generator, `t07-telescope-cai/1`, with new `fixture_id` rows; (2) section 18's generator-check rows extend to T07, stating that a correct generator reaches the statistical-excess stop about 7 % of the time; (3) how a corrected payload is applied (`CAI-T07-3`) is probed before the addendum, so any geometry change happens first; one combined amendment, labelled "before development". The exact text and hashes come to the user before any frozen file changes. No frozen file has changed.

User's answer, 2026-11-07, verbatim: "approve the stage 1c build, seed limit A". The amendment adds a rule, for T07, T08 and T09: a recipe may never link or import a generator, checked in the build, and the scoring harness hands out files, so bins stay on its side. The seed search section 3.2 allows, and one file per stratum, are recorded limits. The full-size check in job stage 1c is read as a rehearsal, not as the section 2.1 check of record.

## T07 stage 1 readings, by the coordinator

Rulings under the finish plan, each reversible by the user. Reviews `<private>/evidence/d1-stage1-*.md`; jobs 7489042, 7489159, 7489656, 7490165.

- **Hits.** All hits are rounded to one grid, 2^-30 mm, by one code path, so low bits do not tell noise from track hits. The data file holds no seed, stratum, block, event index, `fixture_id` or generator name.
- **Separation is tested, not proven.** The tests cover low bits, residues, mantissa tail, decimal form, order and counts. A learned model on joint hits was not tried, nor recovery of the generator's state from noise hits. Enumerating the four seed integers needs SHA-256 only. All assume recipes are reviewed code, as the user's seed ruling does; none holds against code the user does not control.
- **T08, T09.** Read for the same class of leak: seeds sit outside `event["data"]`. T09 times measured on 300 events, dark-only and signal-only agree in low bits; a gross effect is excluded, not a subtle one. T08 has no noise-versus-signal hits to separate.
- **Import rule.** Covers the adapter's folder only, and a dynamic import would pass it: a review rule, not a sandbox.

User's answer, 2026-11-07, verbatim: "approve the T07 stage 2 build", which accepted the reading shown with it: this job, with the field on and a new generator, is still not a T07 development run, since no fixture event reaches a recipe.

## Freeze A amendment 1: choices

User's answer, 2026-11-07, verbatim: "take all 16 recommendations". The choices as shown: (1) state 9.16 % for the whole T07 check and 7.45 % for clean and noise, no pooling; (2) add `fixture_id` 7003 and 7004 only; (3) CAI-T07-4 amplitude 5 sigma(q/p), with the stated 0.00412; (4) `k` below 4.6 against that sigma; (5) CAI blocks 1 and 6, block 1 stated as used for interface runs; (6) four strata, a parabolic mode along +u, bending-coordinate bins stated as expected flat, with R37's wording noted; (7) CAI charge drawn at random, not by parity; (8) the generator targets split into their own CMake file, which is what is hashed; (9) a later regeneration only on the user's word, with a new id and version, labelled "after development" if any development run has happened; (10) section 11's negative-case inputs derived from block 1 files, recipe-dependent inputs fixed at Freeze B; (11) a recipe may not link or import a generator, seed code or truth readers; (12) one more full-size job after the amendment is the check of record; (13) `freeze-a.md` records "Amendment 1, before development"; (14) hash table and clause text for T07 only, T08 and T09's clause unchanged; (15) the job of record pins `hpa-wn28`; (16) later stages use the placement route. The exact text and hashes still come to the user before any frozen file changes.

User's answer, 2026-11-07, verbatim: "approve the stage 3 build, accept both rulings". Section 2.1's T07 bullet is two sentences, with T07's detailed limits in the hashed `check_t07_generator.py`. The three v4 sentences on "hashed by the C++ driver" are corrected in the amendment.

## Freeze A amendment 1: applied

User's answer, 2026-11-07, verbatim: "apply Amendment 1 as listed". Label: before development. Applied exactly as shown; copy kept at `<private>/evidence/t04-v4/amendment-1-as-applied.md`.

| File | SHA-256 |
| --- | --- |
| t04-values-v4.md | `92f71f561ea14b59034ba68fc52f69773d31262e44b371e9ee47110f0ad2edb6` |
| freeze-a.md | `cf76e7dac05eede759883f51074ab1cccd8ec5cebb06a8d8f0703dfddf93b0e9` |
| t04-prereg.md | `39495c3f7db0cded7f88b45711a9457f438be0cbd4113370880d69866448a151`, unchanged |
| t07-t09-task-sheets.md | `01f3509156734372a725eba77b3604935bf420b74fc5f9670fed4348269906f0`, unchanged |

Next: the check of record, then the addendum, part C, on the user's word, before any T07 development run. `freeze-a.md`'s hash changes at that addendum, and that change is recorded here then.

## Freeze A addendum: T07 generators

User's answer, 2026-11-07, verbatim: "apply the addendum as listed". Applied as shown, on the check of record, job 7492427, commit `adf2d051`. `t07-telescope-clean/1`, `t07-telescope-noise/1` and `t07-telescope-cai/1` are frozen by hash. A later generator change is a section 2.3 amendment.

| File | SHA-256 |
| --- | --- |
| freeze-a.md | `669fc90426419f3e691c6b09113b792a64f03d4bdf7c097e3fe3ab6f23423570` |
| t04-values-v4.md | `92f71f561ea14b59034ba68fc52f69773d31262e44b371e9ee47110f0ad2edb6`, unchanged |
| t04-prereg.md | `39495c3f7db0cded7f88b45711a9457f438be0cbd4113370880d69866448a151`, unchanged |
| t07-t09-task-sheets.md | `01f3509156734372a725eba77b3604935bf420b74fc5f9670fed4348269906f0`, unchanged |

T07 development runs may start. The field stays closed until the refit's q/p prior is settled (evidence/d1-stage2-review.md, C-M1).

## First T07 development run

User's answer, 2026-11-07, verbatim: "approve the first T07 development run, accept the field limit". Job 7493368, on block 1, tuning. From this job on, a generator regeneration is labelled "after development". The driver accepts only zero field or the fixture's 1 T: a reading from the prior being settled at 1 T, reversible.

### First development run: result

Job 7493368, block 1, 12,000 events, 72,000 tracks at 1 T, refit truth-assisted and counted apart. The field is open for the refit: the prior is one absolute width, 1.0 per GeV, so an assumed q/p within 10 % is a start, not a constraint, and otherwise the fit is repeated from its own result, up to the single pass: per the stage 4 review, an assumed value at a bin edge moves a pull by up to 0.06 sigma through linearisation, and by 0.003 sigma at 10 % off. This replaces the earlier "field stays closed" note. Cost: about 11 s per 3,000 events. The job's one failed step was the naming check on two test names, since renamed; no physics step failed.


## T07 stage 5

User's answer, 2026-11-07, verbatim: "approve the stage 5 development run, truth-seeded route as recommended". Job 7493849, block 1, development readings. Section 7's truth-seeded run gets a separate scoring-side program: the finder stays truth-free, and the truth-seeded run is labelled and never reported as finding.

### Stage 5, noise efficiency: cause

Job 7493849: clean efficiency 0.9998 to 0.99997; no fakes or duplicates in either fixture; noise efficiency about 0.9945, 0.990, 0.981 at o1, o2, o3, under the floors 0.99937, 0.99812, 0.99374. A development reading, not a gate. Cause, shown on stand-in events and to be confirmed on block 1 by job 5b: on a plane where a track has no hit of its own, the CKF takes a foreign hit inside the window, because ACTS makes a hole only when no measurement passes; the seed prior's windows at plane 1 were far too wide; the intruders are mostly other tracks' hits. Fix: the correlated seed prior, and `seed_prior_inflation` from 2 to 1.5, a development value for Freeze B, not derived from pulls or T08 targets. The floors and all test limits are unchanged. The floor counts noise hits only, and assumes a 0.15 mm window, which is worth knowing when reading it.

Fix round 2, job 7494285 then job 7494405: the correlated prior was centred off the track, because the start was a parabola, missing a 6-7-8 seed's own hits by up to 0.5 mm at 1.5 GeV. A seed now starts on the helix through its hits, along u only, with the covariance of that function, which job 7496491 shows lacks a term. No configuration value changed. The estimate 0.34 was wrong in form: the seven pairs share one seed per track, so one failed seed can count seven; the limit stays 3. Job 7494405 is a development reading on block 1: noise about 0.9996, 0.9995, 0.9982 by occupancy, clean 0.9999 or better, no duplicates, no noise fakes, 2 clean fakes at o3 against a prediction of 0. Corrected after the stage 5 review. On identical events, job 7494405 made o3 noise worse than job 7494285: lost tracks 640 to 781, efficiency 0.99852 to 0.99819, a single missed plane 1 from 4.8 % to 6.4 %, including at high momentum. Its cause is not shown, and the prediction that this class would not change missed. 92 % of o3 losses miss plane 1, and a single missed plane 1 is 484 of the 781, so it is the largest class, not only plane-1 pairs. All of this is inside the floors, and no section 8 gate reads it. That only a two-way search would remove it is unshown, and may be false. The 2 clean fakes are in stratum 2; all three jobs read the same events, so they are a deterministic effect of the code change, not chance; job 7496491 shows the cause below. `ambiguity_most_shared_hits = 1` means no shared hit, and the stated reason for it is wrong: to be corrected.

### Stage 5d diagnostic: results

Job 7496491, block 1, five finders on identical events, development readings. Every stated prediction held, or stated no prediction, except part of the seed probe. Exit 32 is a real defect, not a limit error: the seed covariance lacks a first-order phi term along u (worst disagreement 53 %, 2.7 % with the term), and the limit stands. The o3 change has a measured cause: `estimateTrackParamsFromSeed` takes the v slope from the last two hits, which cost +197 lost tracks, while the helix centre helped by -56; with a chord slope, single plane 1 is 365 and all lost 584, and the 6-7-8 patterns stay cured. The 2 clean fakes are a close-pair tie at a crossing, one event, `fit_chi2/ndf` 0.858 and 1.156, four hits from each owner; the true candidates were evicted, so the resolver took a slightly worse pair. `ambiguity_most_shared_hits` is 1, which means no shared hit; value 2 recovers 163 of 174 o3 ambiguity losses, none lost in exchange. "No configuration value changed" is shown by hash. Diagnostic builds stay in the code until the user's choice on the recipe.


### Recipe choice after stage 5d

User, 2026-11-07, on the two changes put after job 7496491: "take both changes". (1) Seed start: the slope along v from the first and last hit, plus the first-order phi term missing from the seed covariance. (2) `ambiguity_most_shared_hits` 2, so two delivered tracks may share a hit; a development value, for Freeze B. The combined effect is unmeasured, and about 440 lost at o3 is an estimate. One block 1 job follows, its predictions fixed first. The two diagnostic builds of stage 5d come out.

### Stage 5e: results

Job 7502411, block 1, development readings, every step passed. Both changes in: the seed's v slope is the chord of the first and last hit, and the seed covariance carries the phi term, +w (T . m) with w = (q/p) k B the rate phi falls per unit path; the stage 5d report wrote the same term as the shipped covariance's error, -w (T . m). Shared hits 2 is a development value for Freeze B. At o3 noise, lost tracks 781 to 437 over the four strata (efficiency 0.998988; predicted 400 to 475), ambiguity losses 8, hits on two delivered tracks 151 in about 431,000, noise fakes 1, duplicates 0. Clean stratum 2: lost 6 to 1, fakes 2 to 1. The probe passes its 2 % limit, worst along u 0.0093. The phi term's own effect is 2 tracks lost at o3, 0 on clean: it is kept because the covariance is otherwise wrong, not for efficiency. The clean fake left, event 2169, is a new one: a 4 + 4 mixture of a close pair, fit_chi2/ndf 2.09, delivered over particle 31's own candidates; none of the three earlier builds makes it, so it needs both changes together. Its cause is not shown yet. The stage 5d reading that ACTS's slope uses the transverse distance alone was incomplete; no conclusion rested on it.

Event 2169, from the records of jobs 7502411 and 7496491, no new run: the fake comes from the order of ACTS's ambiguity rules (largest shared share, then fewest hits, then largest search chi2) acting on a pair 0.04 to 0.26 mm apart. A Python copy of that order picks exactly the finder's tracks on every event checked (clean stratum 2, all five finders; noise stratum 11, three); the order of removal is the copy's, inferred, since ACTS does not print it. The chord makes the last crossed pair; value 2 keeps both of it, value 1 kept one. The share rule removes a close pair's true candidate at either value; value 2 adds the fake. Same pattern: noise stratum 11 event 654, its one noise fake; 2 fakes and 4 shared mixtures in 539,824 tracks over the five strata. For Freeze B's choice of the value. To settle the order, the finder may print the resolver's removal sequence in a later job.

## T07 stage 6: truth-seeded run

User's answer, 2026-11-07, verbatim: "approve the stage 6 job". Job 7503215, block 1. Section 7's truth-seeded run is its own program, sharing the finder's search, resolve and fit code; it starts the CKF from the exact truth state at plane 1 with section 7's covariance, diag(0.1 mm, 0.1 mm, 0.01, 0.01, 0.1|q/p|)², has no seed finder, and is a comparator only, never reported as finding. ACTS's own ambiguity trace equals the Python copy of the rule order on events 2169 and 654, so that order is now shown, not inferred. The paired bound of section 8.2 "Efficiency, noise (a)" is read as estimate - 1.645 x event-bootstrap se (B = 1,000), the 5 % percentile printed as a reading; a coordinator's ruling the user may overrule before Freeze B. Every step passed but truth-seeded: clean losses over the module's tolerance in 9 of 12 strata (36 in all). Noise truth-seeded losses come from section 7's wide angle start (about 540 per o3 stratum missing plane 2 alone). The stage's predictions P1 to P3 were wrong, since section 7's direction sigma was not carried to plane 2; recorded as refuted.

### Stage 6b diagnostic: results

User's answer, 2026-11-08, verbatim: "approve the stage 6b job". Job 7512409, block 1, ACTS's own VERBOSE trace of every lost start, and a reading at a narrower start angle sigma, 5.657e-4 centred on truth, labelled not section 7 and for no gate. Finder, truth-seeded and traced outputs are byte-equal to jobs 7502411 and 7503215 and to the untraced run. It failed on the truth-seeded step only, as predicted. Predictions: H1 refuted (a plane-2 split in 8 of 36 clean losses, limit 50 %); H2, H3, N1, N2, V1, V2, V4 hold (V2's mechanism not decided, the variant was not traced); H4 refuted (no ACTS error); V3 refuted (variant o3 losses 28 to 45, under 50). Cause of the clean losses: in 35 of 36 the own branch takes its own plane-1 and plane-2 hits, then finds nothing under chi2 16 at three planes and stops. An independent linear Kalman replica on the job's files reproduces ACTS's chi2 to about three decimals and loses the same 35 particles; the hits are Gaussian at 0.020 mm and the plane-3 covariance is consistent or conservative (mean chi2 1.63 to 1.97); Gaussian toys lose about 29 to 31. So these losses are the expected Gaussian tail of a start whose angle comes from two hits, with one start per particle, not a code fault; no fix is indicated. The narrow variant removes 32 of 36 by adding truth to the start, not by removing a split. The module's clean tolerance (0, 0, 3 per stratum by occupancy) was set on the belief that only close pairs lose clean tracks; that basis is refuted. The tolerance has not been changed; what replaces it is the user's to decide, with R1 (section 7's start sigma, frozen).

### After stage 6b: the user's choices

User, 2026-11-08, verbatim: "exact replica check, keep §7, approve the backup". (1) The module's clean tolerance (0, 0, 3) is replaced by an exact check: on every clean stratum the particles ACTS's truth-seeded run loses as seed-or-finding equal, as a set, the particles an independent linear Kalman replica loses under the same start, cut (chi2 16) and hole stop (3); ambiguity losses stay bounded by close pairs, at most 3 per o3 stratum and none at o1 and o2. The old tolerance's text stays, with its refuted basis. (2) Section 7 stays as frozen, including its start covariance. (3) A backup of cb4be047.

Coordinator's rulings on the check, fixed before its job (the user may overrule): a particle the replica loses and ACTS keeps passes only if ACTS's track for it holds a foreign hit the replica listed under the cut on that plane (any foreign hit would excuse about 19 % of o3 particles); a disagreement whose deciding replica chi2 is within 0.15 of the cut is printed as borderline and does not fail, at most 2 over the 12 strata (ACTS and the replica agree to 0.0128 near the cut, about 1e-3 relative; an earlier 0.01 on a wrong basis is superseded); a clean loss of any category other than seed-or-finding or ambiguity fails; a particle both lose with ACTS in another category is bounded by those limits, not by the replica. The code's hole stop is "more than 2 holes", so a branch stops at its third.

### Stage 6c: results

User's answer, 2026-11-08, verbatim: "approve the stage 6c job". Job 7515600, block 1, every step passed, 13 min 19 s. The truth-seeded step passes for the first time, under the exact replica check: over the 12 clean strata ACTS loses 35 particles as seed-or-finding and the replica 36; the 35 are the same particles; the one extra, stratum 8 event 2884 particle 22, ACTS keeps through the split its track took (plane-1 hit 15). No borderline case, no other category, one ambiguity loss (stratum 2, event 2169, the close pair). Strata 3 and 6, unread before, lose none in either. Frame residual at most 2.93e-7 mm; the regression particle agrees with ACTS within 0.025 in chi2. Finder and truth-seeded outputs stay byte-equal to jobs 7502411 and 7503215. Every prediction P1 to P11 held; run time was over the expected 11 to 13 minutes by 19 s, inside its limit of 20.

## T07 stage 7: vertexing

User, 2026-11-08, verbatim: "do it" (start stage 7). `reco.vertex.acts-amvf/1` runs ACTS's AdaptiveMultiVertexFinder on the delivered CKF tracks, the finder staying truth-free. Coordinator's rulings, before any job: the vertices go in finding record `/2`, not in the product, because the product holds only the first K events and vertex readings need every event; a product-level vertex block waits for a contract-map entry. The installed header fixes AMVF's fitter as AdaptiveMultiVertexFitter (`using VertexFitter = AdaptiveMultiVertexFitter;`), so FullBilloirVertexFitter, which the frozen task sheet lists, is not used; correcting the sheet is the user's. Section 7's "most tracks" in the vertex primary is read as the tracks a vertex lists, whatever their weight; the user may fix it at Freeze B (listed tracks, or weight at least 0.5).

### Stage 7: results

User's answer, 2026-11-08, verbatim: "approve the stage 7 job". Job 7522969, block 1, FAILED 40 after 12 min 56 s. The vertex C++ built; every step before vertexing passed, with every byte-equality check. The scoring refused the vertex records because ACTS returned vertex covariances that are not positive definite: 11.6 % of 3-track vertices, 2.4 % at 6, 0.6 % at 12 (coordinator's count over all kept records). Cause, from the 48.2.0 headers, the library and a numerical copy (high confidence): with no fit constraint the fit starts from AMVF's default `initialVariances` 1e8 mm², and KalmanVertexUpdater inverts the vertex covariance to a weight and back at every track; against track weights of about 3e3 per mm² the prior's weight is lost to rounding. The copy reproduces the rate by track count; our packing, frame, weights and linearization point are ruled out. Readings from a non-refusing copy of the scoring (development, every one resting on the corrupted fits): P1 refuted (far efficiency 0.76 to 0.78 at o1 noise, 0.96 to 0.97 at o2, 0.98 to 0.99 at o3; at o2 and o3 almost all the loss is in 20 to 493 events per stratum whose vertex step failed, stderr not kept); P2 refuted at o1 (0.8 %), held at o2, o3; P3 refuted (118 to 138 far merges at o1); P6 refuted (failed events); P4, P5, P7, P9 hold; P8, P10 not decided. Four clean strata never ran.

Coordinator's ruling (the user may overrule): `initialVariances` set to 1e4 mm² on all four components, a printed, hashed development value for Freeze B, chosen for the numerics, not against a gate. A prior of 100 mm against a vertex region of at most 30 mm carries about 3e-8 of a fit's information across the tracks (y, z, track weights about 3e3 per mm²) and 2e-6 to 4.5e-5 along them (x, about 2 to 50 per mm² at 3 tracks; corrected after the stage 7b review); it is not a beam constraint (none enters any fit). The next job changes only that value, keeps the failed events' messages, and counts bad vertices; the limits of P1 to P10 do not move.

### Stage 7b: results

User's answer, 2026-11-08, verbatim: "approve the stage 7b job". Job 7524096, block 1, FAILED 40 after 13 min 4 s, on refuted predictions only; every other step passed. With `initialVariances` 1e4 mm², all 24 strata have no vertex covariance that is not positive definite, no chi2 < 0 and no failed event; finder, truth-seeded, replica, track and product checks are byte-equal. Development readings, before K09: far vertex-finding efficiency 0.983 to 0.989 at o1, 0.998 or more at o2, 0.9997 or more at o3, every lower bound at least 0.980 against section 8.5's floor 0.95; far wrong assignment 0.36 to 0.62 % at o1, under 0.2 % at o2 and o3; far pull widths 0.971 to 1.036; near efficiency 0.56 to 0.66, reported. Refuted predictions, limits unchanged: P1 and P2 at o1; P3 (o1 merges 54 to 96, o2 merges 8 to 18 in 6 of 8 strata, o3 ghosts 5 to 8 in 3 strata); P15 in 4 o1 strata (6 to 8 vertices; not prior-dominated: var_xx 1 to 12 mm² on 2- and 3-track vertices with nearly parallel tracks; the limit's basis used the wrong resolution for the u view). Causes, from the records (high confidence; no code fault found): at o1, a single vertex fitted between two clusters 5 to 7 u_v apart holds tracks of both (90 of 135 lost vertices; none beyond 8 u_v), which P1's closed form did not model; and AMVF's z-only merge check deletes a separated vertex whose sigma along v is inflated by the x-z correlation of a 3-track fit with small slope spread (45 of 135); at o3, a ghost vertex between the closest pair holds many shared tracks at low weight while all three real vertices are found. Every AMVF option is at its ACTS default except initialVariances and the reference point. Options such as `doFullSplitting`, `maxMergeVertexSignificance` and `tracksMaxSignificance` might change this, each at a cost this job cannot measure; none is tuned against a gate, and the choice is for Freeze B.

### After stage 7b: the user's choices

User, 2026-11-08, verbatim: "make them readings, defaults until Freeze B, approve the backup". (1) The vertex prediction tests that job 7524096 refuted (P1, P2, P3, P15) become printed readings, their refutations kept on record; the checks of correctness stay enforced (no failed event, byte equality, positive-definite covariances, no chi2 < 0, P16). (2) AMVF stays at ACTS's defaults, but for `initialVariances` 1e4 mm² and the reference point, until Freeze B. (3) A backup of a82396e4.

## T07 stage 8: execution node and job submission (2026-11-09)

- **Submission.** User, 2026-11-09, verbatim: "allow auto summit slurm jobs", and later "auto continue after the job finishes". From here, this task's Slurm jobs are submitted once the script and manifest hashes are checked, the reviews are done and the static gate passes, without a per-job approval of the SHA-256. Decisions reserved for the user (freezes, amendments, section 18 stops, backups) still go to the user.
- **Node, a change to choice (15) of 2026-11-07 ("the job of record pins `hpa-wn28`").** Job 7534957 (build.sh e333ac11) was pending with an estimated start of 2026-11-23: one other user's 14-day job held all 192 CPUs of hpa-wn28. Asked whether to move it, the user chose "Move to hpa-wn33 (Recommended)", the option described as: cancel 7534957 and resubmit with `--nodelist=hpa-wn33` (idle, same CPU count, memory and kernel); the build runs inside the job, so it compiles on wn33; build.sh's hash changes; a deviation from decision 15 is recorded for stage 8 and later T07 jobs. Not checked: whether wn33's CPU model matches wn28's (nodes report no features). The earlier jobs of record stay on wn28; a result compared across the two nodes is compared across hosts.
- **Done.** 7534957 cancelled before it started. build.sh changed in lines 7 (`--nodelist`) and 40 (comment) only: e333ac11 to 736b1fa3; manifest 139986bd unchanged and matching the worktree. Job 7536797 submitted.
- **Build fix and node, later the same day.** Job 7536797 (wn33) failed at build: `check_r33_product` in `acts_tracking_driver.cpp` declared `version_one` twice; the second is renamed `r33_as_version_one` (lines 601 to 603 only); manifest 139986bd to 7bf0d0f0. The rerun 7537118 was then blocked: another user's job took all of wn33 for about 2.8 days. Asked again, the user chose "Any edr2 node (Recommended)": no node pin for stage 8 and later T07 jobs, any `edr2-al9_short_serial` node, the host logged by each job. This replaces choice (15) and the wn33 pin above. 7537118 cancelled before start; job 7537235 submitted (build.sh 96ae190c, manifest 7bf0d0f0).
- **Login compile.** User, 2026-11-09: "it is good that run it in local". Read as allowing a compile check on the login node beyond Q8; the driver target built there without error (101 s). Asked whether the whole job should also run on login, the user chose "Keep the queued job (Recommended)": 7537235 stays the job of record.
- **Job 7537235 (hpa-wn34).** FAILED 43 after 20 min 18 s on one test: mean unbiased covariance against the closed form σ²(1+h), stratum 0 (1.5 to 3 GeV) plane 8 loc0 1.002027 against the 2e-3 tolerance; P8 ([0.999, 1.001]) also refuted at plane 1 (0.998478). Every other step passed, CAI-T07-2 included: the product's unbiased state equals ACTS's and a leave-one-out refit. Reading `d1-stage8-reading.md`: the closed form's fixed design misses a term roughly second order in curvature at the end planes; no code fault. No limit moved; the choice is the user's.
- **After job 7537235: the user's choice on P8.** Asked what should happen to the closed-form check, the user chose "Make it a reading (Recommended)", described as: as with stage 7b, P8 and the 2e-3 closed-form comparison print as readings, their refutation kept on record; correctness stays enforced through the checks against ACTS and the leave-one-out refit; no new job; the change runs in stage 9's job.

## T07 stage 9: CAI-T07-3, CAI-T07-4, R33 for found tracks

Job 7546791 (hpa-wn34, build.sh fd5a1a88, manifest 9cc6895e), auto-submitted under the user's word of 2026-11-09, PASS. CAI-T07-3: the payload refit equals the unshifted fit to 1e-14; every wrong payload refused. CAI-T07-4: self-check passes in all 8 cells (k 4.5, smallest stated 4.835); flatness (17.0 on 7, p 0.017) and a charge difference of 3.0 se are readings, unexplained. R33 outputs written for the finder's and the truth-seeded tracks (first K product events), existing records unchanged. Coordinator rulings on the implementer's concerns and the review are in the ledger; the nominal geometry identity `t07-telescope-nominal/1` departs from D2 and is a user item in STATE.md. Reading `d1-stage9-reading.md`.

## T07 stage 10: the wrapper, adapter manifest and tool contract carry the stage 8 and 9 interfaces

User, 2026-11-10, verbatim: "approve the backup, continue with sidecars"; read as T07's open item from stage 9 (concern 8), since the finish-plan's Sidecars item is Phase C's and done. Job 7548207 (hpa-wn34, build.sh 49c6d2f9, manifest 87ae043c, 236 files), auto-submitted, PASS in 19 min 03 s: the wrapper forwards `--alignment-payload` and `--r33-outputs` and its products are byte-equal to the driver's (no payload, parent and two derived payloads; finder with and without R33 outputs); every refusal passes through with the driver's stderr; every stage 9 output equals job 7546791's (97 files byte for byte, 26 logs' reading lines, the finder's symbols by name and type and, as a reading, by byte). The tool contract describes the payload input and the conditional output formats in constraint prose (schema limit, a user item for K04). Deviation 10 records the manifest scope of earlier jobs. Adapter version, status and VALIDATION.md are left to T07's close-out.

## T07 stage 11: close-out

User, 2026-11-10, verbatim: "start the close-out". Job 7551619 (hpa-wn34, build.sh 66f6e12f, manifest 6a3b9479, 241 files), auto-submitted, PASS in 17 min 05 s: every earlier step's reading lines equal job 7548207's; A05 (400 interleaved events, 1200 tracks forward and reversed) 0 defects; the example's recording equal in two live runs. `t07-closeout.md`: 36 rows, 18 met, 12 met with readings, 4 open (failing-first for stages 1 to 7 and 10; quality at K09; material effects; A01), 2 gap (stage 8 probes). A17 found and fixed a defect: a payload refit was mapped to sidecars saying no payload. Adapter 0.2.0, `demonstrated-on-synthetic-data` (coordinator, by docs/adapter-authoring.md; synthetic only, no external reference), job of record 7551619. After the job the coordinator wrote its ID into `VALIDATION.md` (manifest 9f10d001, committed 8e047aa7), `adapter.json` (c124c4ba, efd9a803) and the capability matrix, and copied the example's recording from its evidence (host-path grep empty); claims test, example test, scenario test and static gate rerun on login, all pass. T07 stays `in-progress` until Freeze B: its quality verdict waits for K09.

## T08, D2 stage 1: cell chain and clustering

User, 2026-11-10, verbatim: "auto continue next" (after the T07 close-out). U12 A (2026-11-07): development binding. `adapters/calo-cluster`, `proposed`. The ten section 7.1 cases the definition leaves open were coded by the implementer without reading the reference, then compared by the coordinator with the frozen reference clusterer (`evidence/t04-v4/round5/calc-t08-reference.py`, behind job 7479146's log): every choice that can move a number matches; the singular-fit rule was then aligned with the reference (neither object kept). Job 7552825 (hpa-wn34, build.sh dbacc342, manifest 8f628036), auto-submitted, PASS: 0 double-counted cells in 15 strata, conservation to 1e-15, no singular fit; pulls and efficiencies are development readings (`d2-stage1-reading.md`), no verdict before K09.

## T08, D2 stage 2: gain payload, CAI-T08-1 and CAI-T08-2

2026-11-10, coordinator, under the user's "auto continue next". Job of record 7554028 (hpa-wn34, 7 min 29 s, PASS).

- **Gain payload.** A new format `calo-gain-payload/1` beside stage 1's `calo-calibration-payload/1`, which is unchanged, so that stage 1 products stay byte-equal (checked against job 7552825, 127 comparisons). It holds the channel map identity, per-channel gains, the role, and for a derived payload its source and changed channels (R32).
- **Product format.** Products consuming `calo-gain-payload/1` are `calo-cluster-product/2`; `/1` is still read. Why: new fields mean a version bump (stage 9 rule). Older readers refuse `/2` (they fail closed).
- **CAI-T08-1 rules, fixed before the job.**
  - Well above threshold: min(E_old, E_new) ≥ 2 T_c.
  - Changed channels: ix % 8 == 3 and iy % 8 == 3, gain ×1.25.
  - Tolerance: 1e-12 of scale.
  - Floors: at least 100 asserted objects per run, and at least 100 asserted one-peak objects per role over the three strata.
  - Strata: main E3 iso, far and near.
  - Two-peak objects are asserted with their fractions held at the product's values (R37's f fixed); the recipe's re-sharing is recorded.
  - The job's nominal gain is 1; a non-unit old gain is covered by hand-made tests only (review F1).
- **Limits recorded.** The overwrite refusal is a check before writing (sequential writers). There is no CLI re-evaluation operation (a gap for the C&A plan).
- **Readings.** Two predicted readings were refuted and explained in the coordinator's reading:
  - near one-peak components that split into two peaks under the changed gain keep their channel set;
  - the changed cells hold about 2 % of an object's energy, not 10–15 %.
  
  CAI-T08-2 has no numeric assertion (R37).

## T08, D2 stage 3: zdcsim input, simulated-unvalidated

2026-11-10, coordinator, with the user's decision. Job of record 7555555 (hpa-wn25, 12 min 10 s, PASS).

- **Input.** zdcsim.cc, user-supplied (SHA-256 28018224…), is built in the job from the supplied file, never modified or copied. The build route is g++ with geant4-config, reconstructed from S3's binary, because S3 kept no build record and the supplied CMakeLists cannot configure on E5. The job ran 1,000 events, e+ at 500 MeV on crystal (4, 2) of prototype v2 (6 × 6 crystals), seed 930001, one thread. The converter sums edep over zbin per cell. Products are `calo-cluster-product/3`, labelled `simulated-unvalidated` (the T08 sheet), with the input's provenance. The readout is an identity readout of deposited energy: no pedestal, gain 1, no noise, no saturation.
- **Thresholds (user, 2026-11-10: "Carry over, Unresolved (Recommended)").** T_c 0.6 and T_s 10 MeV are carried over from t08-grid/1 for this format exercise only. They are Unresolved per plan 1.1; the owner is the user, and the exit condition is a sourced ZDC prototype threshold before any physics use. The coordinator's question said "8×8"; the geometry is 6 × 6, which does not change the question.
- **Departure from "clustering follows section 7.1 exactly" (review F6).**
  - For this input W, q and σ_n are null: no source exists, and the brief forbids an invented noise model. Each kept component is one object, with fraction 1 and no uncertainty; two kept peaks give an `unsplit` object.
  - Components, peaks and sums follow section 7.1.
  - The question the user answered stated this rule. The coordinator reads "exactly" as binding for t08-grid/1, where section 7.1 is defined. If the user holds it binding for the zdcsim format exercise too, a section 2.3 amendment or a sourced W, q and σ_n is needed (a user item).
- **Environment.** uproot is read from S3's reduce venv. Its RECORD files and their contents are pinned before compute (ruling 3); installing into env/py313 would need the user. CAI-T08-1 and -2 do not apply to `/3` products.
- **Readings.** Two bookkeeping predictions were refuted: cells with a deposit (median 11) and entries per event (median 127). S3's own 1-event file agrees with the job. No performance number.

## T08, D2 stage 4: scenarios A15, A32, A38 and examples/reconstruction-calorimetry

2026-11-10, coordinator. Job of record 7557963 (hpa-wn34, 14 min 03 s, PASS); 7557508 (PASS) superseded and 7557888 (FAIL, the coordinator's incomplete rename in build.sh) before it: the example product is named events.product, because the package forbids *.jsonl (packaging_scan).

- **Defects found while showing the scenarios, fixed (A32, A38):**
  - the readings scored a product of any configuration against job 7479146's constants;
  - CAI-T08-1 took T_c from `--configuration` rather than refusing a product of another configuration;
  - a readout already calibrated could be calibrated again with ADC payloads.

  Payload units must now be the readout's raw unit. Two stage 3 tests now declare MeV readouts, with their intent unchanged. The product reader refuses an event whose kept, unclustered and dead cells do not account for the grid. Stage 1 to 3 products stay byte-equal (job 7557963, 233 comparisons).
- **Statuses** (`t08-scenarios.md`, set after the PASS):
  - **A15: open.** Variants are kept apart by configuration identity; rejecting one under fixed quality gates, or listing it as a working point, needs K09 and T12, or a format change.
  - **A32: met, T08's part.**
  - **A38: open, by part A38.3 (exposure).** t08-grid/1 has no live time or trigger. The plan says a missing implementation is never "not applicable", so the coordinator reworded the implementer's "not applicable". The other six parts are shown, three with readings: the reference-selection literals; no response histogram in T08; and a second correction whose unit matches, which units cannot show.
- **The example** is met. The recording made by the job was copied by the coordinator after the PASS, as T07's was.

## T08, D2 stage 5: close-out and adapter record

2026-11-10, coordinator. `t08-closeout.md` checks T08 against every line of its sheet. Of its 41 rows, 40 carry a status: 22 met, 11 met with readings, 6 open and 1 gap. The six open rows are the zdcsim thresholds, the zdcsim section 7.1 departure, stage 1's failing-first evidence (by mutation only; the user's waiver would close it), quality at K09, A15 and A38. The gap is the native backend (U12 A).

`adapters/calo-cluster` is 0.2.0, `demonstrated-on-synthetic-data`, with section CALO-CLUSTER-T08 in `VALIDATION.md`. Its job of record is 7557963. That job ran the 0.2.0 code under `adapter.json` 0.1.0; only records changed after it (adapter.json, the matrix row, t08-scenarios.md), checked against its manifest c176ffb4. So no stage 5 job was run: T07's stage 11 needed one because its new code first ran there.

`test_calo_records` pins the SHA-256 of every declared asset and test module to that manifest. A later code change therefore needs a new job of record.

## T09, D3 stage 1: charge-only all-channel likelihood

2026-11-11, coordinator. Job of record 7565328 (hpa-wn25, 14 min 31 s, PASS).

- **adapters/photon-likelihood** is a development binding (U12 A), `proposed`, labelled shared-model closure. Live, dead and unhit are three explicit channel states; dead channels contribute nothing.
- **Open cases ruled before any job.** The frozen reference fit (calc-t09-lowmu.py) is "simplified against the fixture" and cannot settle them.
  - Charge: exact compound Poisson-Gaussian of signal plus dark 0.002, with each photon Gaussian(1, 0.3), as v4 4.3's readout.
  - Threshold: one sharp threshold at 0.25 for both the hit and the no-hit term.
  - Saturation: censored at 5.
  - Seed: a single charge-centroid seed, reading no truth.
  - Uncertainty: the inverse observed Hessian.
  - Direction covariance: projected to v4's frame on the scoring side.
- **Optimizer.** Convergence is decided by the Newton decrement (at most 1e-8). Outside the domain the objective returns -inf, so trust-exact rejects the step.
- **Domain.** The domain margin is 5 mm and the total expected yield is capped at 1e5. Neither touches the fixture's range.
- **Probability-sum tolerance.** 64 eps (1 + m|ln m|), set from floating-point arithmetic before the job.
- **Exit codes (core/status.py).** The probability-sum stop exits 1 with its record. An error exits 2 with status "error". The coordinator's earlier ruling for a separate code was withdrawn, because the plugin convention allows no other code.
- **Readings.** 6 of 7,000 fits did not converge. Pull tails come from the single seed. These are readings only.

## T09, D3 stage 2: time term and v4 9.3's fixed-point checks

2026-11-11, coordinator. Job of record 7566770 (hpa-wn34, 33 min 29 s, PASS).

- **Time term.** The first-arrival density of signal (Gaussian 1.5 ns about t0 + d / 0.22 m/ns) and dark hits (uniform over the 200 ns window) is conditioned on the channel's charge. Charge and time are modelled jointly, exactly for this fixture.
- **t0** is the seventh parameter. Its seed comes from the charge-only prefit and the median of t_i - d_i/v; no truth is read. Its domain is (-200, 400) ns.
- **Fit safeguards** found before the job:
  - a chart exit at a 45 degree direction step (status 99, never convergence);
  - log-space products;
  - charge and time domain bounds refused as rejected.
- **Products.** Charge-only stays the default, and its products are byte-equal to stage 1's. The joint fit writes light-likelihood-product/2.
- **v4 9.3.** The likelihood check is an independent harness-side evaluation, sharing no code with the recipe. It runs at 150 evaluations: block 6, each fixed point's own stratum, plus the dead and saturation controls. The limit is 1e-9 absolute. The per-channel sum is also checked at the fixed points.
- **Tool contract.** contract_version stays 1.0.0: it is the schema's version, as in T08.
- **Readings.**
  - Pull widths: 0.92 to 1.11.
  - Failures: 23 of 7,000; the prediction of at most 5 per stratum was refuted in two B1 strata (7 each).

## T09, D3 stage 3: multistart seeds and the truth-start comparator

2026-11-11, coordinator. Job of record 7571207 (hpa-wn26, 1 h 21 min 37 s, PASS).

- **Data-side starts.** There are eight, all from the data only: stage 2's start, reversed, turned plus and minus e1 and e2, mirrored, and the charge seed. Their count and rule are in `t09-multistart-1.budget.json`, recorded by hash (K10), so products /1 and /2 stay byte-equal.
- **Choosing the result.** The highest ln L among the converged starts is reported. A tie within 1e-6 goes to the lowest index. If every start fails, the fit fails as `all-starts-failed`. Every start is recorded in product /3.
- **Truth-start fit.** It runs on the scoring side only, with the same recipe started at truth, and is never written into a data-side product.
- **Wrong-minimum clauses**, as v4 section 7:
  - clause (b) divides by the truth-start fit's sigmas;
  - in B1, clause (b) is reported but not counted;
  - a failed truth-start fit is counted as "comparator unavailable", and the subset whose last point already proves clause (a) is reported separately.
- **Event counts.** The multistart and truth-start runs use the first 250 events of each stratum, from a second harness run tied to the first 250 events of the 500-event run. This keeps the job well inside the partition's 4 h.
- **Readings.** On 3,500 events, one seed gave 11 failures and 21 clause (a) wrong minima; multistart gave 0 of each. No rate test runs before K09.
