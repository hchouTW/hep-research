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

## T09, D3 stage 4: topology and the controls

2026-11-11, coordinator. Job chain of record: main 7575617, H2 array 7576269 (13 tasks) and collection 7576270, all PASS.

**H2 model.** H2 has 14 parameters, 7 per source, each source with its own t0, exactly as the frozen calc-t09-null-h2.py that set v4's penalty. The coordinator ruled against the implementer's 13-parameter shared-t0 H2. A smaller H2, or a weaker search, lowers 2(lnL_2 - lnL_1) under H1 truth, which is the unsafe direction for the mis-ID test.

**H2 search.**
- 8 data-side starts, in `t09-topology-2.budget.json` by hash (K10).
- The reported H2 point is the highest ln L among the starts, with H1 as the boundary.
- Where H1 failed there is no H2 fit; such events are counted.

**Choice.** H2 is chosen if and only if 2(lnL_2 - lnL_1) >= 30. The penalty is frozen from v4 section 7, and the reader refuses any other value.

**Readings.**
- Mis-ID with H1 truth in the main strata, and with H2 truth in the two-source control.
- Mirrored and reversed, by v4's definitions, pooled over B2-B4.
- D_bar, as v4 defines it: charge-only, on expected data, 8 starts, reported only.

**Results.** All readings only:

| Reading | Result |
| --- | --- |
| H1-truth mis-ID | 6 of 3,000 |
| H2-truth mis-ID | 0 of 500 (smallest statistic 586) |
| Reversed and mirrored | 0 |
| D_bar median | 38 |

**Job layout.** The H2 work runs as a Slurm array behind the main job (afterok), with a collection step that runs only when every task has passed.

**Script fix.** The first array failed before any compute: an apostrophe inside `${1:?...}` swallowed the variable assignments. The coordinator fixed the usage lines and resubmitted. No code changed.

**For K09 (user item).** Whether an undecided two-source event counts as a miss.

## T09, D3 stage 5: example, close-out and adapter record

2026-11-11, coordinator. Job of record: 7578442, PASS (10 min 02 s).

**Built.** `examples/reconstruction-photon-likelihood/` (2 main events and 1 two-source event through fit, topology and check-product, offline replay with 9 checks), `t09-closeout.md` (38 rows: 20 met, 13 met with readings, 4 open, 1 gap), adapter 0.2.0 `demonstrated-on-synthetic-data` (lowest tool status; no reference output from outside the plugin, so not `tested-in-declared-environment`), VALIDATION PHOTON-LIKELIHOOD-T09, the matrix row, and `test_photon_likelihood_records.py` pinning the declared files to the jobs of record.

**Cite, not rerun.** The job cites the stage 1-4 strata, fixed points and H2 array (T08 stage 5's rule): it shows 820 of 822 files of job 7575617's manifest unchanged, the 2 changed being records no code reads; it runs the new code and the unit modules (T07 stage 11's rule for new code).

**Replay across platforms (review I1).** Byte equality on the recording's platform; elsewhere ln L 1e-6, the statistic 4e-6, parameters 1e-3 sigma, discrete values exact, fixed before any run. The committed tests also run in CI (ubuntu-latest, macOS arm64), where nothing has run yet: a failure there needs a new decision, the tolerances do not move.

**Version gate (review M2).** The job exits 2 unless Python 3.13.18, NumPy 2.4.6, SciPy 1.17.1 and the interpreter hash of job 7575617.

**Open, for Freeze B.** v4 9.4's two negative checks (dead read as unhit; single-photon density for the first arrival) have no recipe variant: to be written failing first and run after Freeze B. BP06's original method sources stay `source-unverified` (no network approval for a literature check). Quality, the topology score's calibration and the undecided two-source rule go to K09. The native-backend gap stays open (U12 A).

## Freeze B proposal: the user's answers to section 5.1 (2026-11-11)

Proposal `freeze-b-proposal.md` at commit fd5abbf7 (not frozen). The user's answers, verbatim:

- Builds (U-B5): "Start E1b and E2 (Recommended)". E1b (T09 single-photon timing density) and E2 (T07 `r_dev` scorer) are built now; E1a and E5 before evaluation and Freeze B.
- `seed_prior_inflation` (U-B4, with R12-3): "Keep 1.5 (Recommended)". Kept as a Freeze B value, an allowed constant not derived from pulls (basis: a linear model's refusal rate at the chi2 cut, `track_finding.hpp:61-64`; `d1-stage5-review.md:181-182`).
- A15 (U-B14): "Part (a) only, (b) open (Recommended)". A15 is read as part (a), shown in job 7557963; part (b), rejection of the `cheap` and `coarse` variants, stays an open obligation. No E8; T08's part is unblocked.
- U-B1, U-B2, U-B3, U-B6, U-B7, U-B10, U-B11, U-B12, U-B13: "Accept all proposals (Recommended)". Each is recorded as section 5.1 proposes it: `initialVariances` 1e4 mm2 and the vertex reference point (-100, 0, 0) mm; `TrackDensityVertexFinder` with `GaussianTrackDensity` and AMVF at ACTS defaults otherwise; `ambiguity_most_shared_hits` 2; the hash forms of sections 2.1, 2.3 and 2.7; `L_dev` with its counts recorded beside `r_dev`; every check and comparator runs in the Freeze-B run as cost and smoke, no new sample; T07's noise data files deleted after their SHA-256 matches the record; a run that fails for infrastructure reasons before any output is read may be repeated on block 2 at the same hash, both kept and reported; the three workflows' parts run together after E1b and E2.

Still the user's: U-B9 (the run's resources) and the Freeze-B run's submission, when the builds are done; Freeze B itself (U6), with U-B8 and U-B15; the K09 items of section 5.3.

## The user's answers to the remaining Freeze B, K09 and later items (2026-11-11)

The coordinator's suggestions for each open item (session message, 2026-11-11, "What still needs you"); the user: "accept the suggestions". Recorded as accepted:

- **U-B9** (the Freeze-B run's resources): approved, about 30 to 41 CPU-hours as about 30 serial tasks on `edr2-al9_short_serial`, each under 4 h; T07 noise data deleted after its hash check.
- **Freeze-B run**: submitted once both builds (E1, E2) have passed their block-1 jobs; if any recipe's job fails, it is fixed on block 1 first; block 2 is used only once every part passes. The coordinator confirms with the user before submitting it (the coordinator's own statement in the same message).
- **U6** (Freeze B): the user's word, to be given only if the run passes its checks and `U_dev <= C` in every noise bin; the frozen hashes come from the run's own source manifest. Freeze B is not given by this answer.
- **U-B8**: yes, with the evaluation harness E6 built before Freeze B, so that its hash goes with the word. Order: E1, E2; U-B9 and the Freeze-B run; E6 with E1a and E5; Freeze B with U-B8, U-B15 and the K09 answers; evaluation on blocks 11 and 12.
- **U-B15** (failing check first, T07 stages 1-7 and 10, T08 stage 1): waived, recorded as "waived by the user, not shown".
- **U-K1**: a vertex's primary "most tracks" counts tracks with weight >= 0.5.
- **U-K2**: the paired bound is the estimate - 1.645 x the event-bootstrap `se` (B = 1,000); the percentile is printed as a reading.
- **U-K3**: the scorer marks an event search-truncated if any delivered track is marked truncated (scoring side; the recipe and its hash unchanged).
- **U-K4**: an undecided two-source event (H1 failed, no H2 fit, no choice) counts as a miss.
- **U-K5**: T08 efficiency is gated on the seed-firing efficiency, the quantity of the closed-form reference; the matched-primary-with-ok-uncertainty rate is reported beside it as a reading.
- **U-K6**: T08 leakage and threshold failure classes are judged through the edge control and the efficiency gates, with the claim narrowed and stated.
- **U-K7**: A01, A38.3 and A15 (b) are open obligations with the claim narrowed, stated in every report and never counted as a pass; A01's owner is T15b (v4 10).
- **U-W1**: the sheet corrections (F1, m6, stage 11) are approved, applied together in one amendment labelled "after development", after evaluation.
- **U-W2**: the departure accepted: T07's nominal geometry identity is `t07-telescope-nominal/1`.
- **U-W3**: the K04 schema limit accepted for now; a typed file-input field in a later contract version.
- **U-W5**: the zdcsim thresholds stay Unresolved, outside every gate.
- **U-W6**: a read-only literature check of BP06's original method sources (INSPIRE, arXiv, through hep-citations) is approved.
- **U-W7**: the evaluation runs on the same CPU class as the Freeze-B run (AMD EPYC 9645, as recorded).
- **U9** (K11): a separate session with no access to this worktree writes and holds the holdout tasks and their reference answers; the user keeps the files; only their SHA-256 is recorded here; false success means reporting an execution, a pass or a capability without the evidence for it. The harness and system under test are fixed when T13 starts.
- **U10, U11**: at Gate D and Phase G.

## D4 builds E1 and E2 (2026-11-11/12)

Coordinator. Built in parallel after the user's "Start E1b and E2"; each with a fresh review, a fix round and one scoped re-review of both.

**E1, T09 v4 9.4 negative checks (adapter photon-likelihood 0.3.0).** Job of record 7584387 PASS (hpa-wn33, 20 min 37 s), block 1, 250 events per sample.
- E1b: the single-photon-density variant is a whole configuration (`t09-sphere-1-single-photon.configuration.json`, its own product format `/3-single-photon`); only the hit channel's time term differs. The main recipe's products are byte-equal to job 7575617's.
- E1a: dead channels relabelled as live-unhit on the scoring side; the frozen recipe unchanged.
- Readings (no verdict before K09): E1b fires (t0 centre -7.71); E1a fires on z (-0.42) and t0 (+0.31); neither baseline fires.
- Close-out: 20 met, 15 met with readings, 2 open, 1 gap (the BP06 sources row met with readings from `t09-sources.md`, the user's approved literature check, U-W6).
- MaxRSS 1.09 GB, above the predicted 500 MB refutation bound: a cost reading; the Freeze-B run logs MaxRSS per step.

**E2, T07 Freeze-B scorer and E5 (adapter acts-tracking 0.3.0).** Job of record 7584388 PASS (hpa-wn33, 7 min 36 s), block 1.
- The scorer implements v4 5.2's rate rule and v4 7's fake definition; it equals the frozen `calc-rate-rule.py` exactly (difference 0.0 in all 12 bins). `L_dev` one-sided 95 %, as Freeze A's closed form (`calc-closed-form.py` lines 194-199); `N_ev` counts every generated event, events without tracks reported.
- Block-1 `U_dev` 9.98e-4 in 11 bins and 1.016e-3 in stratum 11, all within `C` = 0.005: a reading, not the Freeze-B record.
- E5: the negative-case file kept in `tests/adapters/data/t07-negative-cases/` (`*.t07data` binary), byte-equal to the earlier construction.

**Not met by these builds.** The evaluation harness (E6), E1a's and E5's use at evaluation, and Freeze B itself. The Freeze-B run job is drafted next and goes to the user before submission.

## The user's go-ahead for the Freeze-B run (2026-11-12)

The user: "go-ahead", to the coordinator's statement that the Freeze-B run on block 2 would be brought for submission after its jobs are drafted and reviewed. The coordinator submits the run once its jobs pass a fresh review, its fixes and a re-review, and their manifests are verified; it asks again if the review changes the scope, the sizes, the resources (U-B9) or the block.

## The Freeze-B run on block 2: results (2026-11-12)

Coordinator. Jobs T07 7585954, T08 7585955, T09 step-1 array 7585956 (0-14), step-2 array 7585957 (0-12), collection 7585958: all 31
COMPLETED, collection `JOB RESULT PASS` (hpa-wn33, AMD EPYC 9645). Recipe commit 5228a3e2, manifest `915042c4…` (898 files). Readings and
records only; no gate verdict, no tuning, no evaluation block.

- **`r_dev` (v4 8.3), per noise bin at 12,000 events:** `U_dev <= C` (0.005) in all 12 bins. `k` 0 in 10 bins (`r_dev` 0, `U_dev`
  2.496e-4); stratum 5 `k` 2 of 431,431 (`r_dev` 4.64e-6, `L_dev` 8.24e-7, `U_dev` 2.585e-4); stratum 8 `k` 1 of 431,402 (`r_dev`
  2.32e-6, `L_dev` 1.19e-7, `U_dev` 2.541e-4). Events without tracks 0 in every bin. Evaluation may start on this rule.
- **Hashes, equal to the proposal's predictions:** T07 `configuration_sha256` 2448d935…, `vertex_configuration_sha256` 10a86263…, CKF
  budget 55fb16d9…, vertex budget 16cb8224…, refit `start_prior` 25cd896b…; T08 configuration 5fbbea3b…; T09 configuration ea0e6756…,
  budget 03110227…, single-photon variant e3d815ab…. Adapter manifests: acts-tracking fe80f264…, calo-cluster cb0153ba…,
  photon-likelihood 060e967a…. Records beside Freeze B (U-B8): the comparators and E5's files as listed in the collection output.
- **Blocks:** samples from block 2 only (T07 180,000 events, T08 45,000, T09 45,000, as v4 3.2); block 6 only for the 16 + 1
  generator checks and the fixed points, each equal to its job of record.
- **Cost:** billed 39.67 CPU-hours (U-B9: 30 to 41). T07's sacct MaxRSS 16,172,844 kB against 15,800 MB requested is the cgroup's
  memory with page cache (`jobacct_gather/cgroup`); the largest process was the refit at 8.01 GB (predicted 8.0). A cost reading for
  the evaluation's T07 request. Disk 7.0 GB after U-B11's deletion (every noise file's SHA-256 matched first).

Freeze B is not given: it is the user's word (U6), with U-B8 (E6 built first) and U-B15; the record above is what it would freeze.

## The user's choice of parallel work (2026-11-12)

The user, to the coordinator's question of which work runs in parallel with D4, each in its own worktree with its own reviews:
"E6b + E6c together (Recommended), F1: T11 method text (Recommended)". Not chosen now: E1 (T10 solver options draft), F2 (T12 design
draft). E6b and E6c start once E6a's block-1 job passes; F1 starts now, on its own branch; its PRs stay on the user's word (finish-plan
F1 step 4).

## The Freeze-B run's rate check: a defect and its supplement (2026-11-12)

Coordinator. Found while reading E6a's job 7590464: the Freeze-B run's T07 rate-check step (`jobs/freeze-b-run/t07.sh:129-133`) ran
`t07_fake_rate.py check` under `python -I`, which in Python 3.13 leaves the script's folder off the import path; it crashed
(ModuleNotFoundError, `rate-check.log`) and the step accepted the exit code 1 as a negative reading. `U_dev <= C` in all 12 bins stood
on the runner's own result line and on `t07-records`' UDEV-CHECK; the reader's check of the kept record had not run. The run's records
and hashes are unaffected. Supplement, not a repeat: job 7590984 (`jobs/freeze-b-ratecheck/`, read-only, manifest `7f756177…`)
verified the record against the run's `outputs.sha256` and manifest `915042c4…`, then ran the check: "OK U_dev <= C (0.005) in all 12
bins of block 2", PASS. From E6a on, every script step is judged by its own result line and a crash is never read as a negative.

## D4 build E6a: the statistics core and the evaluation layout (2026-11-12)

Coordinator. Built after the user's "go ahead, dispatch the E6a implementer"; fresh review (0 Critical, 7 Important, 14 Minor), three
fix rounds, two scoped re-reviews and a coordinator check. Job 7590464 failed at its T07 memory step (`python -I`, see the rate-check
section above); job of record 7591439 PASS (hpa-wn33, 24 min 42 s, batch MaxRSS 23.8 GB), block 1 only.

- Files: `tests/adapters/t04_evaluation_core.py` and `t04_evaluation_layout.py` with their tests (scoring side; layering keeps them
  out of `core/` and the adapters; no recipe imports them). E2's rate rule is taken by import.
- The core equals the frozen codings: the pull replay reproduces `calc-pull-table.py`'s stream (0 lines differ), the rate replay
  equals `calc-rate-rule.py`. The attempt level comes from the bin's block only (11: 95 %, 12: 99 %). v4 10's fixed obligations and
  U-K7's are built in per workflow. `k = n` fails at step 1; ungated records keep numbers only.
- Layout: T08 and T09 generate each stratum whole and fit it in ranges; T07 uses the generator's `--first-event`. Merged ranges equal a
  full run for T07 (noise and clean, compared by event index), T08 and T09. Collections run on `afterany` with a completeness check;
  a missing range is "required output missing", never a short bin; no repeat on blocks 11 and 12 once a draw or fit has started;
  every script judged by its own result line.
- T07 memory at 12,000 events (readings): refit 31.8 GB and 182.7 s for all 12,000 (12.3 GB product), 8.0 GB for 3,000; runner
  1.3 GB (noise, 296 s); comparator 2.3 GB. So the evaluation splits T07's refit into 4,000-event ranges at 2 CPUs x 7,900 MB.
- Evaluation layout estimate: about 511 tasks, 170 CPU-hours, longest chain about 0.8 h; the user approves the resources before
  evaluation.
- Waiting for the user (K09, with Freeze B): at attempt 2, the paired bound's `z` (2.326 by v4 3.4, against U-K2's literal 1.645) and
  whether step 1 also uses 99 %. Carried: N1 (T07 refit ranges in the completeness check) and the pooled angle-slice identity to E6b;
  N3 (task scripts write `fit-started`) to E6c.

## The user's answers: backup b21 and the F1 group 1 PR (2026-11-12)

To the coordinator's two questions (backup b21 after commit a8388685; open the F1 group 1 PR): the user "yes"; asked to confirm the PR
separately, since it publishes: "Open the PR now (Recommended)". The PR is of branch `t11/method-text-g1` (commit 9359950e) to the
plugin's `main`.

## The user's answers on the attempt-2 levels (K09, 2026-11-12)

The coordinator's suggestions (session message, 2026-11-12: at attempt 2, v4 3.4's 99 % applies to the bounds that decide a pass;
bounds that declare a fail keep 95 %); the user: "accept". Recorded as accepted, before any evaluation result exists:

- **Paired bound (U-K2 at attempt 2):** `z` 2.326 at attempt 2 (v4 3.4, "on every test"); U-K2's 1.645 is the attempt-1 level. The
  form stays U-K2's (estimate - z x the event-bootstrap `se`, B = 1,000; the percentile a reading).
- **Step 1 of the pull and rate tests (the fail-first step):** 95 % (`z` 1.645; the Clopper-Pearson lower bound at 95 %) at both
  attempts: it is a fail bound, and v4 3.4 moves only pass bounds.
- **F2 (v4 8.3) at attempt 2:** the whole bound at 99 %: `U_eval` and `L_dev` both at 99 % (`L_dev` recomputed from the Freeze-B
  record's `k`, `n`, `DEFF_hat`; at a return for attempt 2 from the block-5 Freeze-B run's record); attempt 1 stays v4 8.3's 95 %.
- **E1a and E1b "fires" (v4 9.4 negative checks):** 1.645 at both attempts: they test that a check sees a known defect, are outside
  the 1,260-test family, and their 1.645 is v4's sensitivity-screened value.

## The user's approval of the evaluation's resources (2026-11-12)

The user: "approval of the evaluation's resources", to the estimate the coordinator reported (E6c's closed form on E6a's layout with
T07's measured refit memory): about 513 tasks and 171 CPU-hours on `edr2-al9_short_serial` (T07 87 tasks, 12.9 CPU-hours; T08 32, 1.3;
T09 394, 156.6), longest chain about 0.77 h, each task under 4 h; T07 bin and refit tasks 2 CPUs x 7,900 MB, others 1 CPU x 6,000 MB;
the AMD EPYC 9645 class (U-W7). For attempt 1 on block 11. This approves resources only: evaluation still waits for Freeze B (U6,
the user's word). If the merged E6's final total is higher than this estimate, the coordinator asks again before submitting.

## The user's answers: wrong minimum without a truth-start fit, and the source of the deterministic and CAI checks (K09, 2026-11-12)

- **Wrong minimum when the truth-start comparator fit failed (T09, v4 9.3):** "Count as wrong minimum (Recommended)": such an event
  counts as a wrong minimum (v4 5.1: "Objects with no result count in a failure rate"); the count is printed.
- **Deterministic and CAI checks at evaluation (v4 10, 11; v4 3.2 blocks):** "Rerun at evaluation (Recommended)": they run once inside
  the evaluation submission, at the frozen hash, on their own v4 3.2 blocks (1 and 6), and the summary reads that result.

Coordinator's rulings recorded beside them: T08's efficiency reference is v4 4.2's bin integral R (settled by v4; bilinear only for
`b_far`, `b_near`); U-K5's per-shower seed firing in far credits a cell to the shower with the largest truth deposit (listed for the
user's information with Freeze B); a T07 primary with no plane-1 result counts as a failure in every gated rate (v4 5.1, 7); a failed
T07 refit fit is counted and printed per bin as a reading.

## The user's approval of a ceiling for the evaluation's resources (2026-11-12)

E6c's fix round 1 recomputed the total for attempt 1 on block 11 as 526 tasks and 176.4 CPU-hours (T07 99 tasks, 12.9; T08 33, 2.0;
T09 394, 161.5), longest chain 1.13 h, every task under 4 h: 5.4 CPU-hours above the approved estimate. The user, asked again: "Approve
up to 200 CPU-h (Recommended)". A ceiling of 200 CPU-hours for attempt 1; the coordinator reports the final figure after the merge and
asks again only if it exceeds 200. Evaluation still waits for Freeze B (U6).

## The user's answers: parallel lanes and U8 (2026-11-12)

The user suggested parallel work ("This could allow for highly parallel processing of the all reconstruction task, accelerating its
completion time."). Asked which lanes to start beside the E6 merge and Freeze B, the user chose all four: "Short fake-rate rerun, F1
remaining families, T12 reprocessing, T10 solver options". U8 (GPU for A13): "Use the site GPU partition". Read as: each lane in its
own worktree and branch, fresh review before any commit; PRs, freezes and U7 stay the user's; Slurm jobs auto-submitted and reported
(2026-11-09 rule); Freeze B and evaluation unchanged.

## The user's answer to U7: T10's scan or global reference replay (2026-11-12)

Options in `t10-options.md` (drafted from the records; the coordinator checked that `Acts::Experimental::Gx2Fitter` is in env/acts48's
`Acts/TrackFitting/GlobalChiSquareFitter.hpp` and that the F38 quotes match `t11-cells.md`). The user: "B2 Python destriper
(Recommended)"; asked whether a development binding counts as R14's "one K02 solver" and whether the comparator tolerance is frozen
when drafted: "Counts; freeze tolerance later (Recommended)". Read as: T10's replay is a destriping solver (conjugate gradient with the
zero-sum baseline constraint, from the F38 sources) written in the plugin in Python (env/py313) as a development binding, labelled not
native, run once on a synthetic K03 timestream against an independently written exact rational reference; the native scan/global
solver stays a recorded gap, as U12 A; the comparator tolerance (K09) is drafted by the stage and frozen by the user before the run.

## The user's freeze of T10's replay comparator tolerance (K09, 2026-11-12)

Asked with the values of `t10-replay.tolerance.json` (drafted, SHA-256 cfdf84c4a4584753163ac4a63076a3dad9d1947a0f2fd2f50d3eb4277a4d5c90)
and `t10-replay-noiseless.tolerance.json` (drafted, 44edffe3374a766c2d82bafad51a6e685e95798474222e72ad12cac43ab31b54) in branch
t10/replay, after a fresh review (t10-replay-review.md: tolerance sound with changes; kappa 24.4704 and G 0.87570 recomputed
independently) and fix round 1: the user: "Freeze as proposed (Recommended)". Frozen values: noisy replay at eps 1e-10, baselines
||a_cg - a_ref||_2 <= 2.5e-8 ||a_ref||_2, map <= 2.2e-8 ||a_ref||_2, zero sum |sum a_cg| <= 1e-13 sum |a_cg|; noiseless at eps 1e-13,
2.5e-11 and 2.2e-11, zero sum 1e-13, no ladder; s = 10, kappa 24.47, G 0.8757 (recomputed by the comparator, a mismatched record
refused); the stopping ladder eps_j 1e-2 to 1e-6, each within s kappa eps_j (map within s G kappa eps_j), the baseline difference strictly
smaller when the iteration count rises, at least 2 such steps or incomplete; map shrinking, the eps/2 run and the a-posteriori bound are
readings. Stated with it: expected differences about 1e-15 of ||a_ref||_2, so a PASS means only "below tau". The records are set
frozen with these values, their final hashes entered here, before the job of record; any change after a result is a 2.3 amendment.
Frozen records (only `state` and `frozen_by` changed from the drafts): `t10-replay.tolerance.json` 217a38bc40769da9c750ac347228b120476008b0227f025f4fcbc02ce9d3c35e,
`t10-replay-noiseless.tolerance.json` 12738ebce579ae83057b69d8dca56cd3a626d5c5afe323863a56275de16da698; job manifest
fba1bff9006775a800dd54d5478f47ff7b2b0273a1e8679621e8de2f86f3af52 (2,575 files); the exact reference 440a1e0d1a7bf169f5e1f8281d45b34739d37e4a0ea56c945a53501f694701db, never run on the fixture before the job of record.

## The user's standing word on pushes, PRs and merges (2026-11-12)

The user: "auto push, open PR, merge". Read as: the coordinator pushes reviewed, committed branches, opens their PRs and merges them
without asking each time, each reported; a merge only after every CI check passes (merge commit, as PR #395), never with a failing or
pending check, and only of work that passed its fresh review and job of record. Freezes (Freeze B, K09 values), installs, and new
network sites stay the user's.

## Freeze B (U6, 2026-11-13)

Asked with `freeze-b.md` at commit c328d447, SHA-256 cfea4fc7c906cdcfa9f30b7db562786b4e3a67a51cd01348f376920e5c3b063d (the T07, T08
and T09 recipes by adapter manifest and file hashes, rechecked unchanged at d65323ee; the effective configurations and budgets by hash
(K10); `r_dev` per noise bin; the T07 negative-case inputs; Freeze A unchanged; E6 at 0e310d34 with the evaluation manifest d98f5e6f;
the K09 reading rules), the user: "Freeze B as listed". FREEZE B GIVEN. Any change to a frozen item is a return to Freeze B (v4 3.4: a new
recipe hash, a new Freeze-B run on block 5, the user's word). Evaluation attempt 1 on block 11 may now be submitted (resources approved,
ceiling 200 CPU-hours). In the same answer: backup b22 approved ("Approve the backup (Recommended)").

## Evaluation attempt 1 on block 11: a deviation, two rulings and the outcomes (2026-11-13)

Submitted after Freeze B with jobs/evaluation/submit.sh (2fd84fe9; manifest d98f5e6f; 46 sbatch calls, 454 attempts lines).

- **Deviation (E6, recorded beside Freeze B, not a v4 2.2 item).** The T08 checks task 7613402 (blocks 1 and 6 only) was read as crashed
  (exit 3): `RESULT_LINES["t08_cai.py rereco"]` expected `RESULT RECORDED`, the tool prints `RECORD recorded without a numeric assertion
  (R37)`. The user: "Fix and rerun T08 checks (Recommended)". Fixed on fix/t08-result-line (layout 96a32215, tasks fe4ef1a3), reviewed
  (jobs/evaluation-t08rerun/REVIEW.md), rerun from snapshot evaluation-tree-7dd5982d (d98f5e6f with the two changed files).
- **Ruling.** select_attempt counted a repeat on block 11 only after NO-DRAW or NEVER-RAN; 7613402 had drawn block-1 check events. The user:
  "Count it: block 1/6 only (Recommended)": a check task drawing only from blocks 1 and 6 (T08 checks, T07 checks, T07 negative cases) may
  be repeated after a harness crash and the repeat counted; no block-11 or block-12 event is ever redrawn; recipe tasks never.
- **Outcomes (attempt 1, block 11; a failure stands, v4 3.4):**
  - T07: workflow **fail**, R11 failed. 1,259 of 1,260 records pass, 46 of 47 gates. The fail: fixture 7002, stratum 9, `vertex pull z`,
    tail rate (L 1 %), step 4: k 200 of 18,907 objects in 9,600 events, estimate 1.058 %, CP lower 0.938 %, U 1.189 % (summary 7613452).
  - T08: **pass**, R11 done (narrowed claim), 8 of 8 gates; checks counted from rerun 7620410 (summary of record 7620411; 7613455 read
    incomplete on the frozen code and is kept as evidence).
  - T09: **pass**, R11 done (narrowed claim), 13 of 13 gates (summary 7613459); all 24 sample-10 single-photon refusals read
    `"status": "rejected"` by hand (audit finding 2).
- Carried to attempt 2 or later: audit findings 2 to 4 (e6-result-lines-audit.md), T07 check tasks writing no milestones (review I3), the
  held bytecode line. Attempt 2 for T07 only after a recorded method change, a return to Freeze B (v4 3.4); the user's word.

## After evaluation attempt 1: the user's word, the T07 diagnosis and the harness fixes (2026-11-13)

- The user, on the coordinator's suggestion: "do your recommendation": a bounded T07 diagnosis of the vertex pull z tail on development data
  only, the harness fixes now, the bytecode line held until the T07 decision. Then, after the diagnosis confirmed the merge mechanism on
  fresh block-1 events (job 7623497): "Test candidates on block 1 (Recommended)": C1, C2, C3 in that order, stopping at the first meeting
  every criterion of the pre-registration `jobs/t07-vz-diag/t07-vz-candidates-prereg.md` (SHA-256 ac3cd0b3...), then the user decides on a
  return to Freeze B.
- Diagnosis (t07-vz-diagnosis.md, review t07-vz-diagnosis-review.md): AMVF merges close 3-track vertex pairs (dv 5-7.5 u_v); pure vertices
  have a Gaussian-like z tail (0.23-0.29 %); every occupancy-1 bin sits near 0.9 % on blocks 1 and 2 (the Freeze-B run scored no pulls).
  Process note: the block-2 reading was a Python pass over kept records on the login node (no draw); a strict reading of Q8 is crossed.
- C1 (job 7623624, trial 1 of 3): K8 met, K1 and K2 not met (o1 z tail 0.888 % noise, 0.849 % clean). C2 running.
- Harness fixes (fix/harness-carried, REPORT.md, REVIEW.md, REREVIEW.md; job of record 7624491): the coordinator's ruling 4 is revised: a
  signal or kill is a crash; an ordinary non-zero exit of a frozen program stands. The check-task rule extends to resource, deadline and
  cancellation stops. A refused T07 negative-cases attempt or one with no checks file stays INCOMPLETE and goes to the user. These change
  three E6 modules recorded beside Freeze B: recorded deviations, re-listed at any return to Freeze B.
- Backup b22: backup/20261113T024535Z (bundle at 268e5bd4); tar warned that evidence changed during the read (folders of running jobs).

## T07: failed at attempt 1 (the user, 2026-11-13); D4 closes

The three pre-registered candidates (t07-vz-candidates-prereg.md, SHA-256 ac3cd0b3...), each a valid trial (K8 met), on the same block-1
events (7623497's digests):
- C1, maxVertexChi2 18.42 -> 9 (job 7623624): K1 and K2 not met (o1 z tail 0.888 % noise, 0.849 % clean).
- C2, annealing cutOff 9 -> 4 (job 7624555): K1, K2 (noise s9), K4 and K6 not met (z tail 0.69 %, every pull width narrowed 4-8 %,
  merges rose, vertex finding -0.6 %).
- C3, tracksMaxSignificance 5 -> 3 (job 7625490): K1, K2, K3, K5 met (z tail 0.33-0.37 %); K4, K6 and K7 not met (vertex finding 0.968-0.969,
  x and y widths -6 to -11 %, o3 z tail 0.27 % -> 0.82 %).

By the pre-registration no method change is justified. The user: "T07 failed at attempt 1 (Recommended)". T07's outcome for this plan is
**failed at attempt 1** (v4 3.4: the failure stands; no attempt 2). The cause, from the diagnosis (t07-vz-diagnosis.md and its review):
AMVF merges close 3-track vertex pairs (dv 5-7.5 u_v); about two thirds of the absorbed clusters are never seeded; pure vertices have a
Gaussian-like z tail; every occupancy-1 bin sits near 0.9 % against the 1 % limit. A remedy would need a different vertex seeding or
splitting method, or a Freeze A amendment to the far range: new design work, outside this plan's attempt-2 path, the user's to start.
The candidate switches stay on branch t07/vz-diagnosis only (never merged: they touch a frozen recipe file).

D4 closes: T07 failed at attempt 1; T08 and T09 passed at attempt 1 (narrowed claims). Next: the held bytecode line as a recorded post-D4
change (calo_cluster.py, photon_likelihood.py; T08 and T09 outcomes stay final at their frozen hashes in freeze-b.md), then Gate D.

## The held bytecode line, a recorded post-D4 change (2026-11-13)

Branch fix/bytecode-post-d4, job of record 7626930 PASS (full suite: only the LCG test fails). calo_cluster.py 31b362e5 -> 4119bf47,
photon_likelihood.py 8a4f4fd0 -> 532260bd; adapter manifests calo-cluster cb0153ba -> 9a142a46, photon-likelihood 060e967a -> 9049c337.
freeze-b.md keeps the Freeze B hashes (cb0153ba, 060e967a): T08 and T09 were evaluated at those bytes and their outcomes stay final there.
The records tests check each file as its job-of-record bytes plus exactly the one line.

## Two recorded post-freeze changes (the user, 2026-11-13: "fix 'Two items for you, no rush'")

Branch fix/postfreeze-tests-sidecar (from 28763f50). Both files are in the frozen evaluation manifest (`jobs/evaluation/SOURCES.sha256`,
d98f5e6f). That manifest and freeze-b.md keep their hashes: evaluation attempt 1 ran at those bytes, and its outcomes (T07 failed, T08 and
T09 passed) stay final there. Neither change alters a recipe, a scorer or a product format.

1. `tests/adapters/test_t04_evaluation_layout.py`, TaskDeadline.test_the_timeout_is_the_time_left_to_the_deadline: the test passed a fake
   clock (`now=100`) while `start_task` also read the real `SLURM_JOB_END_TIME`, so inside any Slurm job with less than an hour left it failed
   (3153.7 != 3480 in job 7636529, 2820.7 in 7636499; 476.0 in red log jobs/postfreeze-fix/red/red-1). The test now clears that variable for its own
   duration. `t04_evaluation_layout.py` itself is unchanged.
2. `adapters/acts-tracking/assets/fixture_tools/t07_alignment_payload.py`, `payload_sidecar` (found by T12 stage 6, review I1): a payload
   that moves nothing (the zero payload) got no `alignment` section, which the R32 reader refuses (`conditions.alignment_incomplete`). It now
   states every plane of the nominal geometry with every parameter of the parametrization, and refuses such a payload derived against another
   geometry. A payload that moves something keeps listing only what it moves, so every sidecar built before this change keeps its identity.
   Test: `tests/adapters/test_acts_cai_refit.py` DerivedPayloadIdentity.test_the_zero_payload_sidecar_states_every_plane_at_nominal.

The records test `tests/adapters/test_acts_tracking.py` keeps the job-of-record pins (42ef9fe3, 486cde56) and reads each changed file as its
pinned bytes plus exactly one recorded block of whole lines (POST_FREEZE_CHANGES: 0d415979, 08338c1d), as the bytecode line was recorded.
Red and green logs in jobs/postfreeze-fix/.

## Recorded for the record (2026-11-13)

- K12 (U10): the user, "Adopt the draft (Recommended)": k12-targets-draft.md (SHA-256 679a1a12...) on branch gate-d/prep, frozen by hash.
- F1 steps 2-3: the user allowed read-only lookups on INSPIRE, arXiv and ADS ("Allow read-only lookups (Recommended)").
- A13 (T12 Q1): "Record blocked-by-resource (Recommended)" (R14; CPU measurements recorded; no GPU job).
- Phase G: "Agree with both (Recommended)": U11, no real data for this plan (K03 synthetic only; the data-control layer stays incomplete
  and open, R14, R21); T13 prepared now (writer brief, frozen scorer), the holdout written and kept off this account and host, T13 run last.
- T15b: "Draft spec, digitization off (Recommended)": the K16 element_sim spec drafted for the user's freeze by hash.

## T15b: the K16 element_sim sample spec frozen (the user, 2026-11-13)

Asked with `t15b-element-sim-spec.md` (SHA-256 99a678e5e06ed9d30860a963d86ed170ee78da6a5bb19493bc84054fe44aec99; reviews
jobs/gate-d/T15B-REVIEW.md and T15B-REREVIEW.md; pilot of record 7627279 PASS on block 1: 500 events per bin, chunk-merge equal to the whole
run; Geant4 43.7 and 59.7 CPU-ms per event; ~1.6 CPU-h for the full sample): the user, "Freeze as listed (Recommended)". Frozen with it, as
Choices outside v4 3.2 and not amendments of Freeze A: fixture_id 1601; blocks 21 (sample), 22 (attempt 2), 23 (reserved for K18
confirmation); the per-event seed form S = H("t15b-k16-1601", "block-<b>", species) (deviations.md row 11); noise-digitization off (the
user's earlier "Draft spec, digitization off (Recommended)"). The user also confirmed the K16 reading: "Yes, it covers them (Recommended)":
the 2026-11-06 acceptance of section 16 covers section 13's hard gates, quality objective, tie rule and none-passes rule (R02). Resources
approved with the freeze: about 1.6 CPU-h for the 96,000-event sample on block 21.

## T15b: K16 selection, attempt 1 on block 21 (2026-11-13)

Job of record 7627683 (jobs/t15b-k16/t15b-k16.sh c9a635b0, manifest 015690d6, scorer c3ab9825; reviews REVIEW.md, REREVIEW.md), run as frozen
on the user's word ("Run as frozen (Recommended)"), the fake reading by the user's ruling ("Count them as fakes (Recommended)": a candidate
row with at least 4 hits and no true plane is a reconstructed track and a fake): **K16 SELECTION: no qualified candidate** (no candidate passes
every required gate; gates are not lowered, section 13). Each candidate fails 13 of 96 required tests: the rho_pull tail rate (1.5-2.0 % in bins
0-2, mixed, proton and antiproton; antiproton in bin 3) and the fake rate in bins 1-3 (1.5-2.6 %), against L 1 %. Efficiency, charge flip,
centres and widths pass. The tie interval includes 0 (moot). The claim is scoped to the declared baseline and tested domain (simulated
element_sim events, J15, digitization off); no post-selection quality claim without K18 confirmation data (block 23 untouched). Recorded with
it, for the user's information: the fake reading; the pull and charge-flip population (fit_ok and selected with at least 4 true planes); the
attempt-2 level the scorer would take on block 22 (K09's rule, the user's call if ever needed). The pilot's development readings (7627279)
had shown the same tail and fake pattern.

## Backup b23 and the order of work after Gate D (the user, 2026-11-13)

- 10:34Z, the user: "approve backup b23, auto continue". b23 started when the Gate D checkpoint 7628236 ended (no live writer during the
  read).
- 10:51Z, the user: "do T07 (the seed-finder study) after all works". Order then: Gate D checkpoint, backup b23, close-out records, the T07
  seed-finder study (development only, block 1, a new pre-registration; T07 stays failed at attempt 1 unless the user later chooses a
  Freeze B return). The ledger cites the user's "how about T07" with this word when S1 was submitted (12:35Z).
- 12:00Z, the user: "keep waiting, auto continue" (b23 was reading evaluation-b11, 180 GB, at about 14 MB/s). 12:11Z, the user: "Backup is
  slow": the single-stream archive was stopped (18 of about 240 GB in 66 min) and redone in the same folder in parallel: evaluation-b11 as 8
  size-balanced parts plus one archive of its directories, the rest as 8 balanced parts plus one archive of directories and links, pigz,
  1 MB records. Bundle at 93d95a16 kept. The T07 S1 job was submitted during the rest archive, which read file lists fixed before the
  submission, so S1's new evidence folder could not enter it.
- Result (20:30Z): b23 complete and verified, `<workdir>/backup/20261113T105814Z`: 19 archives and the bundle, the 20 entries of
  `SHA256SUMS` (its own SHA-256 6c2bc806...; the ledger says "20 archives + bundle"; the folder holds 19 .tar.gz files) check, every archive
  read back, 381,724 files and 40,060 directories and links archived, equal to the lists, 0 tar warnings, 92 GB; bundle 73e5b0c9... at
  93d95a16; ledger archive f925dd24... In-progress lane folders were excluded (jobs/t12-stage3, 4, 6, 7, jobs/t13-harness), as in b14. A
  first verify step failed only because coloured `ls` output garbled names; it was rerun with globs.

## T07 seed-finder study, development on block 1 (2026-11-13)

Done on the user's word above, development only; T07's outcome is not changed by it. Prepared in t07-vz-diagnosis.md ("Seed-finder study"):
ACTS 48.2.0 seeders listed from the headers; a truth emulation on 7623497's occupancy-1 events found two density maxima in every merged
event (356/356, 323/323) with the global maximum on a cluster: the merge forms at track admission around a correct seed (median separation
5.4 u_v against the tracksMaxSignificance cut of 5), not at seeding, so the seed-finder premise was not supported at truth level. Still run
as pre-registered (`jobs/t07-vz-diag/t07-seed-prereg.md` 3012f373..., K1-K8 unchanged from ac3cd0b3; S1 AdaptiveGrid 6 um; S2 adds
estimateSeedWidth only if S1 is not null):
- S1 (job 7632710, t07-seed-s1.sh a585707f, SOURCES-s1 976af123): predicted null; **not null**: merged vertices 419/429/391 against
  356/367/323 (+17-21 %, beyond +-15 %); z tail +0.04-0.06 % absolute (within 0.15 %); vertex finding -2.7 points (mostly "seeded, not
  good"); K1-K6 not met, K7 and K8 met. The prediction was refuted, so S2 ran.
- S2 (job 7636593, t07-seed-s2.sh ed15d177..., SOURCES-s2 f284283f, predictions t07-seed-s2-predictions.md 7578ce82): exit 1 at K8
  ("no failed vertexing event" false: 219, 203, 187 failed events in the occupancy-1 bins, 1 in s10; defects 0): estimateSeedWidth makes
  AMVF fail events. Otherwise K1 0/2, K2 0/3, K4 2/5 (finding 0.9515, 0.9527, 0.9553, below S1's), merged 409/426/387.
- **Coordinator's reading of S2** (20:30Z): the pre-registration repairs and reruns a K8 failure that is a run defect; this one is the
  variant's own behaviour, and any repair would be another setting, which section 2 forbids. S2 is not counted and not repairable within the
  pre-registration; the study ends (at most two variants). Conclusion: the seeder is not the lever; both finer-seed variants are worse than
  the frozen seeder. T07 stays failed at attempt 1.

## T13: the holdout session, custody and section 7's readings (the user, 2026-11-13)

- 12:23Z, the user: "fix T13 (your holdout session)". Read as: the holdout writer stays off this account by design (harness spec section 1,
  U9); the agent-side items start now: the harness code (spec 3.1-3.10) tested on a fake CLI and frozen by hash, and the agent-written
  development set (K11). Lane t13h-tree, branch t13/harness. No paid model calls until the user's word on the shakedown.
- 12:24Z, the user: custody "Agree, one account (Recommended)": the custody procedure of harness spec section 1 (no implementer sessions
  during the run window), with its stated limit (one Unix user: the system under test could search the host). Spec section 4's row "User
  agrees to the custody procedure" becomes done in the harness lane.
- 12:24Z, the user: spec section 7's five readings "Adopt all five (Recommended)": (1) under R22 and U9, in R14's no-model-access case T13
  records the frozen scorer, the brief and the holdout hashes; (2) the holdout's confirmation is narrowed to the three required workflows and
  a 12-family sample, the other families staying an open obligation; (3) the holdout carries the brief's counterexample classes, not the
  A-list, and no A-scenario is claimed confirmed by it; (4) a critical fail (including a successful-looking result with the wrong physics
  meaning) blocks a required workflow; (5) section 14.2's timed intervals, warm method-card states and a paired baseline are outside T13.
- Still the user's (as of this word): the holdout itself (written in a session off this account; holdout_id and two SHA-256 sent), the
  system under test, the runner, the budget, the execution resources, and the shakedown's paid calls. The runner and the execution
  resources were answered on 2026-11-14 (below).

## Parallel lanes (the user, 2026-11-13 and 2026-11-14)

The user's parallel-processing remark, twice. 2026-11-13 12:30Z: lanes for T12 stage 3 (t12s3-tree) and stage 4 part A (t12s4-tree), then
(12:31Z) stage 6 (t12s6-tree) and stage 7 (t12s7-tree), all from 28763f50. 2026-11-14 01:32Z: lanes records/after-t12 (rec-tree: these
records, t12-closeout.md, STATE) and t12/carried-minors (t12m-tree: the stage 3, 4A, 5, 6 and 7 review minors), from eb4ef5c9, beside the
T13 round 8 (t13h-tree) and the T07 split job 7649462. As before (2026-11-12): each lane in its own worktree and branch, a fresh review
before any commit, Slurm jobs auto-submitted and reported.

## T12: coordinator rulings (2026-11-13)

- **Q3 (A37 in T12)**, 12:31Z: T12's part runs its own reprocessing of fixtures 7003 and 7004 through the T12 loop machinery, because
  T12-19's acceptance says "inside a T12 reprocessing" and R31 says "reused", not cited; T10's reading of the recorded log is not T12's
  evidence. **Q5 (T10)**: moot, T10 is done.
- **Stage 6, concern 1**, 13:24Z: Q3 is satisfied by a reprocessing through the control-layer machinery (contract, admission, receipts,
  checks by digest, labels, publish, identity-keyed cache) without an outer-round family: a round family would need a fake derivation,
  which R31 does not ask for.
- **OI-8** (stage 4 fix round 1, 20:53Z): T10's frozen replay tolerance holds for a destriper product against a product of the same recipe
  only on the record's pointing (t10-destripe/1, seed 20260): each is within kappa eps of the exact solution, so they differ by at most
  2 kappa eps < tau = safety kappa eps; the 1e-13 record applies to noisy products stopped at 1e-13 too. Every destriper result names the
  ruling. Before the tolerance is applied, T10's own derivation checks run on the reference product's pointing; any other pointing is
  rejected.
- **The A32 label**, 21:14Z: every report of T12 states A32 as "executed, harness-side check" (E32R runs `build_response.py` on frozen and
  variant T08 products; the pairing refusal is the harness's, because the tool records no structured product or configuration identity, an
  open item). A `check_side` field in the runtime record is carried as a minor.
- **Q2 (A13 reproducibility)**, stage 5 fix round 1: the stage 4 numerical comparator with T10's frozen tolerance under OI-8, on the frozen
  pointing only; larger sizes `incomplete` (OI-12). A coordinator ruling for the user to confirm; the user has not ruled on Q2 itself.

## T13 harness review: the user's answers, and T12 OI-6 (the user, 2026-11-13)

At 20:30Z, on the harness review (jobs/t13-harness/REVIEW.md, NOT READY 3/4/6/2) and T12 stage 4's open items:
- C2 (a relative `..` in a command stopped the evaluation): "Follow cd, then flag (Recommended)": the harness follows `cd` within a
  command, then flags non-search references outside the allowed roots (recorded in the run record and `FLAGS.jsonl`); searches, and
  references to the repository, protected roots, `~/.claude`, `~/.claude.json` or anything in `$HOME`, still stop. This departs from spec
  3.8's text (stop), as the user's answer.
- Reading 8 (a max-turns or budget stop): "Count as SUT failure (Recommended)": recorded completed with no valid report (reported null),
  scored fail, never rerun; not "crashed".
- Reading 10 (network beyond the model API is not enforced; Bash has network): "Record departure (Recommended)": network commands are
  flagged, and the departure is stated in the harness spec (section 8). It is a design limit of T13, not a process breach, so it is not a
  row of deviations.md.
- T12 OI-6 (T09's close-out replay tolerance as T09's reproducibility tolerance): "Leave open (Recommended)": T09's numerical and
  statistical comparator forms stay `incomplete`.
- **Coordinator's reading** (fix round 2, 21:56Z): a relative reference into the run root (`ls ..`, `../../C/rep-1/in.csv`) is a flag, as
  the user's C2 answer; an absolute reference into the run root, and any reference into the repository, protected roots, `~/.claude` or
  `$HOME`, stops. Later rulings on single harness rules (fix rounds 3 and 5) are in jobs/t13-harness/REPORT.md.

## A13 reopened: the GPU (the user, 2026-11-13)

21:37Z, the user: "A13: GPU part: allow use GPU". This reopens A13 (R30); the answer to T12 Q1 recorded above ("Record blocked-by-resource
(Recommended)") is superseded and stands only as history; R14's `blocked-by-resource` no longer applies to A13. Asked, the user chose the
subchain "T10 destriper (Recommended)" (the only recipe with a frozen reproducibility tolerance) and the partition "B6000 devel
(Recommended)" (`b6000-al9_devel`, 1 GPU, the existing `torch-gpu/venv-cu130`, nothing installed). U8 ("Use the site GPU partition")
stands. Order: R30's hardware job, then the stage 5 lane, pilot, measurement.
- R30 hardware job 7648670 (hw-check.sh 140cbcbe..., 1:04) PASS: hp-rtx6kp02, NVIDIA RTX PRO 6000 Blackwell Server Edition, driver
  590.48.01, capability 12.0, about 96 GiB; torch 2.14.1+cu130; a float64 2048 solve agreed with the CPU to 1.9e-15 relative.
- Jobs of record (all PASS): CPU job 7649128 (benchmark, T12-14), pilot 7649129, measurement 7649143. On the frozen pointing 6 of 6 GPU runs
  passed the stage 4 comparator at T10's frozen tolerance (15 iterations; differences 4e-16 to 2e-15); the scans (1,048,576 and 16,777,216
  samples) are `incomplete` (OI-12; 78 and 148 iterations equal to the CPU's; differences 6-12e-15 as readings) and their GPU timings stay
  sealed. A13's outcome: the GPU subchain equals the CPU recipe within T10's tolerance where a tolerance exists; no GPU speed number is
  released at the scan sizes (needs a derived tolerance for such a pointing and the user's freeze; proposal in t12-stage-plan.md, stage 5).
- Sandbox fix: the first pilot 7648901 failed because its bwrap made a fresh `/dev` (no `/dev/nvidia*`); both GPU scripts now bind `/dev`
  and check CUDA inside the sandbox (exit 3 if unseen). The pilot rerun 7648934 and round 0's CPU job 7648900 are readings only.

## T13: the stop and flag policy (the user, 2026-11-13T23:33Z)

The user: "go ahead with all of it" (the coordinator's proposed policy for stops and flags; the harness lane's report dates it 2026-11-14,
the local date):
1. Whether a stopped attempt is spent is decided before scoring, from the command log only.
2. Categories: A, a false positive of the guard: not spent, rerun once as a harness cause; B, a real attempt whose output never reached the
   model: not spent, the repetition scored FAIL; C, outside data reached the model: spent (a new holdout is needed).
3. B is recorded as completed with no valid report (scored fail).
4. Harness: `output_reached_model` in the stop record, a resume mode, just-in-time per-session staging of inputs, a task-free stop summary
   for the builders.
5. Flags are reviewed after the run and before scoring, with the same table.
6. The shakedown measures the false-stop rate first. A second account remains the only full closure (a stated limit).
Built as harness spec section 9 and fix round 6.

## T07: attempt 2 by a method change (the user, 2026-11-14)

00:21Z, the user: "do T07: attempt 2 (a method change and a return to Freeze B)". The coordinator: attempt 2 needs a method change that
first meets K1-K8 on block 1 (block 12 is the last evaluation block). Asked, the user chose "Post-fit split test (Recommended)": after AMVF,
each fitted vertex is tested for two vertices by a two-vertex refit of its own tracks, accepted on a likelihood gain beyond a threshold
fixed in advance from statistics, never scanned. Developed in t07diag-tree behind a compile-time switch (the frozen recipe untouched), with a
pre-registration and predictions, a fresh review and one block-1 job. A return to Freeze B only on the user's word after K1-K8 are met; then
attempt 2 on block 12 at 99 %. Until then T07's outcome stays **failed at attempt 1**; the earlier section ("no attempt 2"; "a remedy ... the
user's to start") is not corrected, it is followed by this word.
- Built (SPLIT-REPORT.md, review SPLIT-REVIEW.md READY TO SUBMIT 0/0/4/4): pre-registration `jobs/t07-vz-diag/t07-split-prereg.md` d6151d34,
  deviation 1 `t07-split-deviation-1.md` e6bede81 (the rule is recorded in the vertex_fitter line's value, because the vertex configuration
  keys are fixed), job t07-split.sh cef676f7, SOURCES-split 143a6e5f. Rule: every AMVF vertex with at least 4 own tracks, cut at the largest
  z0 gap, three Billoir fits; split if the chi2 gain on 3 dof exceeds the quantile at alpha 1e-3 / B(n), B(n) = 2^(n-1) - 1 - n
  (thresholds 18.58 to 26.26 for n = 4..8). Predicted: K8 met; K1 likely not met (about 2 in 3); not a confident call.
- Submitted 01:07Z (auto-submit), development job 7649462 on block 1; running when these records were written.

## T13 design: sandbox and Slurm runner, and the shakedown (the user, 2026-11-14)

After a login check (bwrap 0.4.1 works, `$HOME` and `/ceph` hidden inside; API reachable) and a compute-node check (job 7649480, hpa-wn33:
API reachable, bwrap ok; no data, no model call), at 01:16Z the user chose:
- "Add sandbox (Recommended)": bwrap per session: its own folder as home and working folder, the plugin snapshot read-only, system and CLI
  read-only, interpreters and backends read-only, a config folder with credentials only; `$HOME`, `/ceph`, the repository, the run root and
  other tasks' inputs absent.
- "Flag, review later (Recommended)": inside the sandbox an attempt to reach outside its root is a flag reviewed before scoring, never a stop
  or a fail; stops remain for a missing or broken sandbox, isolation and guard errors. This supersedes "B = fail" of the stop and flag policy
  for sandboxed runs.
- "Slurm compute nodes (Recommended)": the runner submits jobs; the run window is away from the login node.
- "Locally in the job (Recommended)": `requires_execution` tasks run inside the session's allocation with backends read-only; no Slurm
  access from the sandbox.
Built as harness round 8 after the final re-review 5.

01:17Z, the user: "go-ahead" (after the plan: round 8 sandbox and Slurm runner, then the paid shakedown "on your go-ahead"). Read as:
proceed with round 8, and the paid shakedown on the development set as described (1 real session on a compute node in the sandbox, then the
6 development groups x 1 repetition; at most 7 paid sessions, each capped by the settings record's session budget), once round 8 is reviewed
and its job of record passes. The SUT model and plugin commit for the shakedown are confirmed with the user before the first paid session.
The holdout is still not established; the SUT, the budget for 3 x (number of tasks) sessions and the holdout remain the user's.

## T07: final at "failed at attempt 1" (the user, 2026-11-14)

The post-fit split study (pre-registration `jobs/t07-vz-diag/t07-split-prereg.md` d6151d34; deviation 1 e6bede81; review SPLIT-REVIEW.md
READY TO SUBMIT) ran as development job 7649462 on block 1 (34 min 7 s, 4.6 GB; valid: K8 6/6, 0 failed vertexing events). K1 NOT MET (o1
pooled z tail 0.929 % noise, 0.898 % clean; maximum 0.50 %), K2 NOT MET (0/3), K3 5/6; K4-K8 met. The test split 18 to 26 of about 4,450
tested vertices per o1 bin; merged vertices 354/364/321 against 356/367/323 (predicted a 45-80 % fall; refuted). With the threshold fixed for
validity, the z0-based two-group test has too little power on the fixture's merged clusters. By the pre-registration (one candidate, no
second value) the study ended. Six principled candidates have now failed on block 1: C1-C3, S1, S2 and the split test.

The user's answer, verbatim: "accept T07 failed at attempt 1, auto continue". T07's outcome is final: failed at attempt 1 on block 11. No
return to Freeze B and no attempt 2; block 12 stays unread. The recorded cause: AMVF at ACTS defaults merges 3-track vertex pairs 5 to 7.5 u_v
apart, which the fixture's far range [5, 25) u_v admits and v4 section 17 lists as "where confusion really happens". A Freeze A amendment
of the far range, the only other route the diagnosis names, was not taken.

## Ledger records copied into the tracked folder (G3, 2026-11-14)

On the coordinator's instruction, two ledger files cited above are now also in this folder, each headed by a note naming its source and
SHA-256: `t07-vz-diagnosis.md` (ledger SHA-256 af11380e1d13a5b4199c36b2e6d726cb7930b6a959336c0a5f4591ce84afed55) and
`e6-result-lines-audit.md` (ledger SHA-256 ba01bb028f60aaeed8f7e5083c80f00fb69c26e0f970738d4bca7da6cf0f573e). Earlier sections that cite
them by name mean these files; the lines above are not edited. `t07-vz-diagnosis-review.md`, also cited, stays in the ledger folder
`<private>/worktree/.superpowers/sdd/finish-plan/` only.

## A13: left as it is (the user, 2026-11-14)

Asked with the mid-size proposal `<private>/jobs/a13-midsize/PROPOSAL.md` (SHA-256
f8ba1460ce19ddcaa8966f509bc560e0eff3a0c6c26bf208efb16b1d4a48a211; branch `a13/midsize-proposal` at 316a097b; nothing frozen, no job), as
relayed by the coordinator, the user: "Leave A13 as is (Recommended)". What the proposal showed, kept as readings:
- At a 4,096-sample pointing (`a13-mid-4k`) T10's exact method is tractable: kappa 9.303845, G 1.028937, so tau 9.4e-9 (baselines) and
  9.6e-9 (map) at T10's stopping 1e-10 and safety 10; the same procedure run on t10-destripe/1 reproduces T10's frozen records exactly.
- The GPU is predicted about 4 times slower than the CPU there in warm compute (slower end to end), with a predicted warm-compute crossover
  near 29,000 samples. These are extrapolations from released timings only (a two-point CPU model), not measurements.
- 65,536 samples (`a13-mid-64k`, predicted about 2 times faster on the GPU) would need a ruling on the reduced-form derivation of kappa
  and G and an in-memory comparator path, since no product of that size can be written (OI-13).
The choice: A13 keeps its released result on the frozen pointing (6 of 6 GPU runs within T10's frozen tolerance, job 7649143); the proposal
and the crossover prediction are recorded as readings; OI-12 stays open and the GPU timings at scan sizes stay sealed; nothing is frozen.

## G3 on the user's word (2026-11-14)

The user's words, verbatim, after the coordinator listed what waited on them (the T13 holdout items, the optional A13 mid-size pointing, G3):
"do \"Waiting on you\"". Read and recorded as: G3 proceeds (final report, final checkpoint, whole-branch review, integration with the
current main, the PR, and the final backup, with merging only after all CI passes); the A13 mid-size pointing prepared as a proposal (the user
then chose "Leave A13 as is (Recommended)", above); the T13 runner brief drafted. The holdout writer session and the runner stay the user's by
design (U9; t13-harness-spec.md section 1), and the holdout budget follows the shakedown's measured cost.
