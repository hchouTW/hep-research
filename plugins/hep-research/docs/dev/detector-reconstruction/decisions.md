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
