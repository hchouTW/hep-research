# hep-research Cross-Artifact Analysis Check — Final Architecture Specification

## 0. About this document

### 0.1 Basic information

| Item | Content |
| --- | --- |
| Subject | The cross-artifact analysis check of hep-research (hereafter **the checker**) and the components around it |
| Version | Finalized 2026-10-22; second clean-up edition (same content as before the clean-up; only organisation and wording changed) |
| Status | **The only valid architecture document.** All other plans and memos are superseded (§16) |
| Languages | The Chinese version `cross-artifact-check-architecture.zh.md` and this English version have the same content; if they ever differ, the Chinese version prevails |
| Audience | The maintainer, reviewers, and the agent doing the implementation (for example Claude) |
| Rule status | Every checker rule stays in **shadow mode**; this document **enables no** gate condition |

### 0.2 Measurement baseline

| Item | Content |
| --- | --- |
| First measured on | hep-research 0.21.0 (contracts 3.2.0) |
| Current baseline | hep-research **0.24.1** (contracts 3.6.0), fully re-measured on 2026-10-22; `plugin_release()` verifies it as 0.24.1 (a released build) |
| Checker changes from 0.21.0 to 0.24.1 | **None.** The checker's code, suites, registry, catalog, coverage contracts, relevant schemas and `docs/dev/v6.3/` are byte-identical. The 0.24.x changes concern the independent review's expert role, advisories and sci-fixes, not the checker |
| Results re-run on 0.24.1 | F1–F9 (§1), the compatibility facts of §8.1, the 205 existing tests, `rule_registry.py check` (23 rules, 71 V cases) and the 10 gap probes are unchanged; a bundle frozen with the earlier version still checks complete on 0.24.1 |
| Correction | The baseline this document earlier called "0.23.0" was in fact an unreleased development build after 0.23.0 (`plugin.json` said 0.23.0, but the CHANGELOG had an `Unreleased` section and `plugin_release()` returned `unreleased`) |
| How releases are written | This programme's releases are always referred to by the relative labels R1–R3 (§8.2), never by absolute version numbers |

### 0.3 One-page summary

- **What the checker is:** a cross-artifact consistency check of a frozen analysis (a bundle), producing advisory diagnostics.
- **Current state:** the rule layer is designed correctly, but it has 22 reproduced gaps (G1–G22), and **no real workflow runs it** (F2, F3).
- **Core judgement:** obtain evidence of value first (the value gate, §10), then decide whether to fix and extend.
- **Architecture:** two planes (§5.1; DR-11 open). Diagnostic plane A is built now; assurance plane B is design only.
- **Route:** Phase 0 (foundations; no rule outcome changes) → Phase 1 (value gate) → decision point (continue, shrink or stop) → Phase 2 (fix the gaps).
- **Decided:** the adopted texts of DR-1 to DR-8; their post-review revisions are still **pending confirmation**.
- **Open:** DR-9 to DR-15.
- **Separate work package WP-R:** rename the code name "v6.3 / v63" to descriptive names. The tool is finished, and on 0.24.1 the full suite gives identical results before and after the rename (§8.3); adoption depends on DR-15.
- **Next step:** the programme owner decides DR-9, DR-11, DR-12 and DR-13 (the entry conditions of Phase 0).

### 0.4 Where to look

| To find | See |
| --- | --- |
| Current state and evidence | §1 |
| Terms and IDs | §2 |
| Scope (what is and is not done) | §3 |
| Normative principles | §4 |
| Architecture, planes and components | §5 |
| Gaps | §6 |
| Whether something is decided | §7. **Anything marked "open" or "pending confirmation" MUST NOT be implemented as if decided** |
| Versions, compatibility, releases | §8.1, §8.2 |
| The rename (WP-R) | §8.3 |
| What to do and when | §9; each phase lists entry conditions → work → prohibitions → exit conditions |
| Value gate, entry path, spike | §10, §11, §12 |
| Owners, record convention, retirement | §13 |
| Risks and open items | §14 |
| Rules for implementing | §15 (**read before implementing**) |
| Which documents are valid | §16 |
| How to reproduce the evidence | Appendix A |

### 0.5 Conventions and evidence levels

| Term | Meaning |
| --- | --- |
| **MUST** | Mandatory requirement |
| **MUST NOT** | Mandatory prohibition |
| **SHOULD** | Recommended; any deviation needs a stated reason |
| **Confirmed** | Measured or read in code on the 0.21.0 copy and re-checked on 0.24.1, with evidence |
| **Inferred** | Derived from confirmed facts, not measured directly |
| **Unresolved** | The answer is not known yet |
| **Open** | A decision item not yet decided (§7) |
| **Pending confirmation** | A revision that has been proposed but takes effect only when the programme owner confirms it in a dated section (§7.1) |

**Easily confused labels:** `R1`–`R3` are this programme's releases (§8.2); `RN-1`–`RN-7` are the rename safety rules (§8.3.3); `R-AUX`, `r-real.*` and the like are checker rule names. The three are unrelated.

---

## 1. Background and current state (all Confirmed)

| # | Fact | Evidence |
| --- | --- | --- |
| F1 | The analysis-check programme added about 4,000 lines of checker code and 205 tests (not counting the separately added `test_cross_artifact_check_gap_probes.py`) | `wc -l`; `tests/contracts/test_v63_*.py` |
| F2 | **No real programmatic workflow runs the checker.** The only programmatic entry point is the optional flag `review_measurement_spec.py --check-bundle` | grep for callers |
| F3 | None of the 8 `SKILL.md` files mentions the checker; no routing test case calls it (415 cases in 0.21, 419 in 0.24.1); none of the 20 examples runs it | `skills/*/SKILL.md`; `tests/routing/cases.json`; `examples/*/run.py` |
| F4 | Five skill references and the plugin README teach the agent to run `freeze` and `check` **by hand** | `preservation-checklist.md`, `analysis-workflows.md`, `time-series-inference.md`, `nuisance-modeling.md`, `review-and-artifacts.md`; README lines 275–312 |
| F5 | `freeze` needs a recipe and a check-context. The whole plugin has one reference recipe, and no tool produces recipes or check-contexts | `contracts/semantics/recipes/flux_from_counts.json` |
| F6 | No role may currently accept a check report as evidence | `docs/dev/v6.3/decision-enforce.md:69` |
| F7 | No host configuration is currently qualified for private or blinded data | `docs/protected-data-architecture.md:5` |
| F8 | By design, a fixed recipe plus a bounded operator-semantics table "never omits scientific review"; closure tests are a T3 control | `protected-data-architecture.md:379`, `:358` |
| F9 | S3 execution and formal use are distinct scopes; the gate lives outside the plugin's agent-run code | `protected-data-architecture.md:433` |
| F10 | All known gaps G1–G22 (§6) have been reproduced by tests or scripts | `final/test_cross_artifact_check_gap_probes.py` (G1–G10) and `archive/evidence/` |

**Conclusion:** the checker's rule layer is designed correctly. It needs fixes, not a rewrite. What is missing is **evidence of value**; whether a more convenient entry path should be built depends on that evidence.

---

## 2. Definitions

### 2.1 Checker concepts

| Term | Definition |
| --- | --- |
| analysis-check programme | The plugin's development programme with the internal code name "v6.3" (from 2026-10-16), which built the checker. Its records are in `docs/dev/v6.3/` and its tests are `tests/contracts/test_v63_*.py`; if DR-15 is adopted they become `docs/dev/cross-artifact-check/` and `test_analysis_check_*` (§8.3). This document calls it the "analysis-check programme" |
| checker | `contracts/analysis_check.py` and `contracts/analysis_checks/`: cross-artifact checks of a frozen analysis |
| bundle (v2) | The frozen analysis produced by `freeze`, format `hep-research-analysis-bundle/2`; it holds the items, a check-context and a semantic-lock |
| check-context | The bundle document that states the analysis intent: roots, recipe instances, bindings, declarations, and the frozen obligation inventory |
| suite | A set of rules plus an obligation generator, for example `counting-chain/1.0.0`, `ratio-subset`, `model-card`, `run-lineage` |
| obligation | One check of one rule on one subject; its result is one of five states |
| five states | `satisfied`, `violated`, `not_applicable`, `unverified`, `unsupported`. Coverage counts only the first three (decided states); it is not a pass rate |
| declaration-based | An outcome that depends on an agent-written declaration; the formal-use view treats it as unverified |
| semantic-lock | The digests of the definitions used at freeze time (suite, registry, coverage, table, catalog) |
| snapshot | A content-addressed copy of definitions, so an old subject can be reproduced under its old semantics (D11b) |
| `lock_differences` / `installed_differences` | The frozen definitions differ from the current ones: the former without a snapshot; the latter recorded while reproducing from a snapshot |
| version guard | When a rule, the generator or an input check has a different version from the one the suite names, it is not evaluated and gives `rule_not_run` |
| L1 / L2 | `validate.py` (single artifact) / `recipe_semantics.py` (recipe semantics); both predate the analysis-check programme |

### 2.2 Concepts of this architecture

| Term | Definition |
| --- | --- |
| diagnostic plane (A) | The checker as run on the agent side; it produces advisory diagnostics only |
| assurance plane (B) | Checks in the custodian's formal-use gate; the custodian reruns the check and judges the custody of the inputs |
| protected input | A file that `core/protected/trusted_input.read_protected()` accepts, i.e. one only the custodian could have written |
| `plugin_release` | The result of `core/protected/identity.plugin_release()`: the version when the copy matches a release manifest exactly, otherwise `unreleased` |
| `.in_use/` | The runtime folder the plugin system writes into the root of an installed copy; since 0.24.0 it does not count towards the copy's identity |
| value gate | The measurement before any extension: how many more errors the checker catches than the existing defences (§10) |
| entry path | A tool that helps produce a v2 bundle (`analysis_check.py draft`); whether to build it is DR-14 (§11) |
| phase | A stage of the roadmap: Phases 0, 1 and 2 and coverage extension (§9) |
| session | The unit of effort estimates: one continuous stretch of implementation work |
| WP-R | The work package that renames the code-name identifiers (§8.3, per DR-15) |

### 2.3 ID families

| ID | Meaning | Defined in |
| --- | --- | --- |
| F1–F10 | Facts about the current state | §1 |
| P1–P10 | Design principles | §4 |
| G1–G22 / A1–A6 | Gaps / ancillary issues | §6 |
| DR-1–DR-15 | Decision items of this programme | §7 |
| R1–R3 | This programme's releases (relative labels) | §8.2 |
| RN-1–RN-7 | Rename safety rules | §8.3.3 |
| V01–V91 | Validation cases in the registry; V01–V71 exist, V72–V91 are added by this programme | `contracts/rules/registry.json`; §6 |
| O, C, HC, D12b, D11b, G-ENFORCE, T3, S3 | The plugin's existing open questions, conditions, hard constraints, record convention, decision gates, threat classes and execution scopes | `docs/dev/v6.3/` and `docs/protected-data-architecture.md` |

---

## 3. Goals and scope

### 3.1 Goals

1. Make the checker a **reliable consistency aid for reviewers**: its diagnostics are correct and honest.
2. **Obtain evidence of value** before any further development.
3. **Reserve the right place** for future assurance (the assurance plane) without implementing it now.

### 3.2 Non-goals

- No gate is enabled; no rule leaves shadow mode.
- No change to the permit or attestation schemas; no change to `core/partition/` or `core/protected/`.
- No old rule implementations are kept in the tree; old results are reproduced with the release that produced them.
- No operators are derived from run records or argv (unless the spike in §12 shows it is feasible).
- Two observations are never judged identical because their values are equal.
- No fixed tolerance cap.
- No support for model-card joint evaluations (O03).
- No retroactive bump of the 0.14.0 version labels (A2).
- No finer-grained semantic-lock (pinning only the definitions used): that needs a rule-to-definition map, which does not exist.
- No claim of forgery resistance: even the assurance plane cannot defend against a forged `state.json` or forged chunk files.

---

## 4. Design principles (normative)

| # | Principle |
| --- | --- |
| P1 | An agent-side check report **MUST** be advisory diagnostics only and **MUST NOT** be represented or used as authorization (HC-05). |
| P2 | The checker compares descriptions and tool-produced artifacts; it **MUST NOT** claim to represent the computation that actually ran. |
| P3 | Rules, the obligation generator and input checks **MUST** be under the version guard: a version mismatch gives `rule_not_run`, and an old version **MUST NOT** be evaluated with new code. Rule fixes **MUST** be released as new versions. |
| P4 | Removing or loosening any agent-writable input **MUST NOT** raise the status or remove obligations. A tool-produced draft **MUST NOT** write declarations or bindings automatically. |
| P5 | Rules **MUST** collect all evidence before deciding; a result **MUST NOT** depend on input order. |
| P6 | With dependency-missing diagnostics or `lock_differences`, the status **MUST NOT** be `complete` (it must agree with the exit code). `installed_differences` produced by reproducing old semantics from a snapshot **MAY** be complete, as D11b intends. |
| P7 | Blinding permission **MUST** trace to a data leaf; when only the result's own label is available, the outcome **MUST** be unverified. |
| P8 | (Assurance plane only) Only custodian-held files outside the project, referenced by digest, count as facts. Custody **MUST** be judged against a named analyst account, not the running account. |
| P9 | Any extension (rule fixes, the entry path, new suites) **MUST** come after the value gate. |
| P10 | A field that a rule compares against **MUST NOT** be generated automatically from the same source that rule reads. |

---

## 5. Architecture

### 5.1 Two planes (per DR-11; **open**)

| Item | Diagnostic plane A | Assurance plane B |
| --- | --- | --- |
| Purpose | Find contradictions between descriptions, and honest mistakes | A result the formal-use gate can rely on |
| Run by | The agent | The custodian's formal-use gate (not S3 execution) |
| When implemented | **Now** | After a custodian identity, a qualified host and the O14 roles exist; **design only for now** |
| Checker version | The installed version, under the version guard | Named by the purpose policy's `checker_digests`; **MUST NOT** be chosen by the bundle |
| Definitions | Installed definitions, or reproduced from a snapshot per D11b | Refuse analyst-supplied snapshots and bundle-supplied definitions, or use an index of released definitions |
| Role of `check-report` | Cheap refusals: dependency-missing, `lock_differences`, pre-release suite, mismatch with the frozen inventory | Gate logic: V60, V65, V66, custody judgement, comparison with the reviewed report |
| Trust flags | `declaration_based` is a hint only; G8 and A3 always flagged | P8; the source of the analyst account must be settled |
| Report format | Report 1.0.0 | Report 1.1.0 (`assessment.inputs`, `basis_summary`); `recheck_record.json`; a `plugin_release` of `unreleased` never counts as a recheck (§8.1) |
| Relation to human review | The report is reference material for the review | **MUST** be compared with the report the reviewers accepted |
| Mutation operators | relabel, rename, copy, copy+perturb, drop, loosen, toggle-optional, reorder, edit-report | unprotect, forge-definition |

**If DR-11 is rejected:** the assurance items revert to v3.1's WP1 (custody and claims) and WP6 (`check-report` hardening and recheck), implemented in the diagnostic plane; Phase 2 grows by about 5–7 sessions.

### 5.2 Data flow

```text
Diagnostic plane A (agent side)
  Project artifacts (spec, recipe, response, dataset-record, calibration)
    → hand-written bundle (after DR-14: draft → humans fill in the TODOs)
    → freeze (snapshot written by default to <root>/.hep-research/snapshots/)
    → check (version guard; P4–P7; run records passed with --results)
    → summary → analyst and reviewer (advisory)

                │ the report the reviewers accepted, as attestation evidence
                ▼
Assurance plane B (custodian's formal-use gate; design only)
  rerun with the checker release named by policy, on the custodian-held copy of the bundle
    → custody judgement (P8) → comparison with the reviewed report → check-report gate logic
```

### 5.3 Component register

| Component | Path | Lines | Plane | Current use (Confirmed) | Action |
| --- | --- | ---: | --- | --- | --- |
| freeze, check, summary | `contracts/analysis_check.py` | 847 | A | `--check-bundle`, `migrate.py`; documents teach manual use | Keep and fix |
| chain and ratio rules | `contracts/analysis_checks/rules.py` | 757 | A | Runs only with the checker | Keep; fix in Phase 2 |
| model-card suite | `contracts/analysis_checks/model.py` | 321 | A | Tests only; mentioned by two hep-statistics references | Freeze; fix only G5 and G12 in Phase 2; §13.4 retirement applies |
| run-lineage suite and result binding | `contracts/analysis_checks/runs.py` | 411 | A | Tests only; hep-computing references tell agents to write bindings | Keep; fix in Phase 2 |
| lock and snapshot | `contracts/analysis_checks/lock.py` and others | 173+ | A | A lock is built on every freeze and check | Keep; snapshots on by default; P6 |
| effect catalog and coverage | `contracts/effect_catalog.py`, `contracts/semantics/` | 206 | A | Runs only with the checker | Keep |
| migration | `contracts/migrate.py` | 151 | A | Mentioned only in dev records and the CHANGELOG | Keep; add the context 1.0→1.1 conversion in Phase 2 |
| rule registry | `contracts/rule_registry.py`, `contracts/rules/registry.json` | 217 | Shared | **CI gate** (`tools/run_all_checks.py:312`) | Keep; update the schema per §8 |
| custody inventory | `contracts/custody.py` | 102 | B (per DR-11) | No program callers; mentioned by the README and the detector atlas | Freeze |
| check-report | `report_check` in `contracts/permit.py` | (part of 427) | Cheap refusals in A; the rest in B | Tests only; the only implementation of V60, V65, V66 | **Re-scope; do not deprecate** |
| L2 recipe semantics | `contracts/recipe_semantics.py` | 349 | Baseline | Standalone CLI since 0.6 | Not part of the analysis-check programme; the value gate's baseline |
| run verification | `contracts/verify_run.py` | 78 | Baseline | Standalone CLI since 0.5 | Same |
| permit verification, attestation | `contracts/permit.py`, `contracts/attestation.py` | 427 + 285 | B | `hepdata_export.py`'s protected path, `protected_use.py:63`; the only example runs in non-protected mode | Out of scope |
| protected guard | `core/protected/` | — | B | **In use**: 8 skill scripts and 3 adapters | Used directly by the assurance plane; not modified |

---

## 6. Gap register

**Columns:**
- **Plane:** A = diagnostic plane; B = assurance plane.
- **Phase:** per §9.
- **V case:** the registry case that must pass for acceptance.

| ID | Gap | Evidence | Plane | Disposition | Phase | V case |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | Writing fewer spec corrections removes checks, and the result stays complete | probe `test_g1` | A | DR-8: `r-real.undescribed` | 2 | V86 |
| G2 | `required: false` is an unregistered waiver that can hide a violation | probe `test_g2` | A | DR-2: removed in check-context 1.1.0 | 2 | V78 |
| G3 | Validation-record outcomes depend on item-ID order | probe `test_g3` | A | P5; `r-ratio.correlation` 1.1.0 | 2 | V77 |
| G4 | A factor table chooses its own tolerance | probe `test_g4` | A | DR-6 | 2 | V79 |
| G5 | A copied observation file bypasses R-AUX | probe `test_g5` | A | DR-3 | 2 | V85 |
| G6 | Campaign closure does not reach the analysis | probe `test_g6` | A | `campaigns[].inputs`: no analysis input → unverified; digest mismatch → violated (`closure_mismatch`) | 2 | V82 |
| G7 | Blinding trusts a self-reported status | probe `test_g7` | A (lineage) / B (label) | DR-7 | 2 / B | V83 |
| G8 | A self-declared `asserted_by.kind: person` removes the flag | probe `test_g8` | A (always flag) / B (custody) | DR-1 | 2 / B | V88 |
| G9 | The report's `result_binding` section can be hand-edited | probe `test_g9` | B | Assurance-plane design | B | — |
| G10 | `CHECKER_FILES` does not cover the modules loaded at run time | probe `test_g10` | Shared | Use the modules actually loaded at run time | 0 | V74 |
| G11 | Editing or dropping report obligations goes unnoticed by `check-report` | `review/p_new2.py` | A (cheap comparison) / B (forgery) | Compare with the frozen inventory | 0 / B | V75 |
| G12 | `shared_parameters` within one model hides V07 | `review/p_new1.py` | A | Input-invalid for 1.1.0 contexts; fix the shadow classification | 2 | V80 |
| G13 | Whether blinding applies depends only on the spec's flag | `review/p_new4.py` | A | Per the DR-9 join key | 2 | V84 |
| G14 | The factor obligation depends on the calibration mapping key | `review/p_new5.py` | A | A table under the parent or any child key produces the obligation | 2 | V87 |
| G15 | One of two bundle coverage contracts is silently ignored | `review/p_new5.py` | A | Input-invalid for 1.1.0 contexts | 2 | V81 |
| G16 | A tolerance can be NaN or a string; calibrations have no schema | `review/p_new5.py` | A | Input-invalid for 1.1.0 contexts; calibration shape | 2 | V79 |
| G17 | `_exclusion` depends on declaration order | `review/p_new5.py` | A | P5; `r-rep.repetition` 1.1.0 | 2 | V77 |
| G18 | Rule code has no version | `review/p_drift.py` | Shared | Version-guard mechanism and function-level digests; Phase 0 builds the mechanism only | 0 | V72 |
| G19 | `check-report` notices neither a forged suite nor definition drift | `review3/p1_snapsuite.py` | A (drift) / B (forgery) | Cheap `check-report` refusals; forgery belongs to B | 0 / B | V75 |
| G20 | The status is complete while the exit code is 3 | `review3/p1_snapsuite.py` | A | P6 | 0 | V73 |
| G21 | Tool-produced recipe fragments fail L2 when composed | `review4/sf_recipe.py` | A | Classify in Phase 0. Changing the semantics table changes its digest, breaks recipe bindings and the `LEGACY_TABLE_SHA` test, so it needs its own decision | 0 / 2 | — |
| G22 | A root's unit is never checked for validity or against the estimand | `review5/unit_probe.py`, `review6/g22_unit.py` | A | Phase 2: freeze refuses empty and placeholder units. A full check needs a unit parser and goes to coverage extension | 2 / ext. | V89 |
| A1 | The generator digest hashes only one file | Code reading | Shared | Merged into G10 | 0 | V74 |
| A2 | 0.14.0 changed content without bumping version labels | Release manifests | — | No retroactive bump (it would cause drift) | — | — |
| A3 | Bundle-supplied coverage contracts are not flagged | Code reading | A / B | Handled with G8 | 2 / B | V88 |
| A4 | `runs.py` reads files in the pure-function layer | Code reading | A | Move the I/O up with the run-lineage fixes | 2 | — |
| A5 | Eras, per-sign factors and `simulated` are not modelled | Code reading | A | Coverage extension | ext. | — |
| A6 | No operator covers `luminosity`, `fakes` or `fiducial` | Code reading | A | Coverage extension | ext. | — |

**Other V cases:** V76 = mutation-testing skeleton (Phase 0); V90 = context 1.0→1.1 conversion (Phase 2); V91 = entry path (Phase 2, registered only if DR-14 passes).

---

## 7. Decision register

### 7.1 Rules

- DR-1 to DR-8 were adopted on 2026-10-22 on the maintainer's instruction in the session ("the maintainer's instruction in the session was to follow the recommendation").
- Anything marked "pending confirmation" **MUST** wait for a dated section by the programme owner (D12b); until then it **MUST NOT** be implemented as decided.
- Anything that depends on DR-11 must also wait for DR-11.

### 7.2 Register

| DR | Adopted content | Post-review revisions (**pending confirmation**) | Changes depending on DR-11 (**pending confirmation**) |
| --- | --- | --- | --- |
| DR-1 | Trust is judged by custody; `asserted_by.kind` has no effect on trust | Only files outside the project, referenced by digest, can be protected; judged against a named analyst account; `check-report` re-judges itself | Split: always flag G8 and A3 in A; custody judgement moves to B |
| DR-2 | check-context 1.1.0 removes `required`; deferral only through exceptions | A subject under a 1.0.0 suite first meets the version guard | — |
| DR-3 | Observation identity = source identity + pointer; values are never compared | **Reverses the adopted text:** without an envelope, use the canonical digest; a copy with one added key stays undetected (known limitation) | — |
| DR-4 | Forgery is addressed only by a custodian rerun; `require_recheck` | `recheck_record.json`; a forged `state.json` is not covered | Moves to B |
| DR-5 | Snapshots on by default; old rules reproduced by rerunning their release | Definitions in a snapshot must be released definitions | Split: default snapshots, version guard and P6 stay in A; the released-definitions index, custodian copies and release reruns move to B |
| DR-6 | Tolerance derived from declared significant digits | **Reverses the adopted text:** the undeclared default stays 1e-9 (adopted text: 1e-12); check the values' actual digits; replace k with Σ\|power\| | — |
| DR-7 | Blinding judged by lineage; `simulated` may be permitted | No data leaf → `lineage_no_data`; label only → unverified; dataset and envelope status vocabularies kept apart | The "custodian-approved derivative" row moves to B |
| DR-8 | Add `r-real.undescribed` | **Reverses the adopted text:** no root coverage (→ DR-10). Only a non-empty `backgrounds` block describes a background; `no_backgrounds_reason` with an applied background → `description_contradicted`; class matches limited to the members the spec lists | — |
| DR-9 | — | — | **Open:** the join key between the project's `blinded` list and a spec. Recommended: the spec's `artifact_id` |
| DR-10 | — | — | **Open:** the subject set of root coverage. Recommended: defer to coverage extension |
| DR-11 | — | — | **Open:** adopt the two-plane split. Recommended: adopt |
| DR-12 | — | — | **Open:** scope and cap of the spike. Recommended: §12 |
| DR-13 | — | — | **Open:** value-gate design and thresholds, which **MUST be decided before measuring**. Recommended: §10 |
| DR-14 | — | — | **Open:** build the entry path, conditional on the value gate passing. Recommended: §11 |
| DR-15 | — | — | **Open:** rename the code-name identifiers "v6.3 / v63" to descriptive names, using the mapping and safety rules of §8.3. Recommended: adopt, as Phase 0 item 11 |

### 7.3 Related existing open questions

| ID | Question | Relation to this programme |
| --- | --- | --- |
| O03 | Supported model-card pairings | Joint evaluations are out of scope |
| O04 | Non-author reviewers | The error planter and the human reviewer |
| O09 | Efficiency members of the effective exposure are undefined | Affects the value gate's flagship case |
| O14 | Roles that may accept reports | A precondition of the assurance plane |
| O16 | Which skills call the checker | Changing a `SKILL.md` needs a new decision |
| O17 | Whether the custodian adopts the gate requirement | A precondition of the assurance plane |

---

## 8. Versions, compatibility and releases

### 8.1 Compatibility facts and targets

| Object | Facts (Confirmed; measured on 0.21, re-checked on 0.24.1) | Target |
| --- | --- | --- |
| SemVer pre-releases | `semver.parse('1.1.0-dev.1')` raises `not a version`; the registry's rule `version` pattern and the context's suite-version pattern are both `^\d+\.\d+\.\d+$` (the `v_cases` pattern `^V\d{2}$` is unrelated to versions) | From R2, `1.1.0-dev.N` is accepted; `check-report` refuses pre-release suites (`permit.report_prerelease_suite`); no purpose policy accepts a pre-release suite |
| registry schema | `registry_version` enum is only `1.0.0`; rule objects are `additionalProperties: false`; `work_packages` is `^D\d{2}[a-d]?$`; `slice` is an M1–M3/D11b enum; a repeated `rule_id` → `registry.duplicate_rule` | R1: registry 1.1.0 (a rule source-digest field; new phase and work-package values). R2: unique key becomes (rule_id, version); retired versions marked by `lifecycle` |
| semantic-lock | 1.0.0; pins the whole registry, the whole coverage contract, the whole table, and every effect any operator references (14 for CASE-CHAIN) | **Unchanged.** Drift is absorbed by the default snapshots |
| check-context | `context_version` is a const; 1.1.0 is refused (freeze gives `bundle.context_schema`, check gives input-invalid); an unknown declaration type in 1.0.0 only gives a context finding | R2: 1.1.0 |
| report | `report_version` is a const; 1.1.0 is treated as `report_missing`; the top level is `additionalProperties: false`; `assessment` and obligation objects are open | The diagnostic plane stays at 1.0.0 (R1 adds `plugin_release` inside `assessment`); 1.1.0 belongs to the assurance plane |
| result binding | Gives `schema.const` and `schema.additional`, input-invalid | R2: 1.1.0 (`campaigns[].inputs`) |
| suites | All four are 1.0.0 | R2: `1.1.0-dev.N`; R3: 1.1.0 stable (counting-chain, ratio-subset, run-lineage, model-card) |
| effect catalog | The `catalog_version` enum in `effect_catalog.json` is only `1.0.0` | R3: 1.1.0 (`description_required`) |
| `plugin_release` | Bundle v2 already has the field; a development tree, and any copy with an added, missing or changed file, returns `unreleased`. **Since 0.24.0** an installed release copy returns its own version (measured on 0.24.1); before that, `.in_use/` made every installed copy return `unreleased` | R1 writes it into the report's `assessment`. Only because of the 0.24.0 fix is the rule "`unreleased` is not a recheck" (§5.1) workable on installed copies |

### 8.2 Release mapping

| Release | Phase | contracts | Format changes | Do rule outcomes change? |
| --- | --- | --- | --- | --- |
| R1 | Phase 0 | +1 minor | registry schema 1.1.0; the WP-R rename (if DR-15 is adopted) | **No** |
| R2 | Phase 2, first half | +2 minor | SemVer pre-release patterns (semver, registry, context); registry unique key; check-context 1.1.0; calibration shape; result binding 1.1.0 | Yes (only in `1.1.0-dev.N` suites) |
| R3 | Phase 2, second half | +3 minor | catalog 1.1.0 | Yes (suites 1.1.0 stable) |

**Release labels:**
- R1 is this programme's first release, i.e. the next minor after the version installed when implementation starts. For 0.24.1, installed on 2026-10-22, R1 is 0.25.0.
- R2 and R3 follow in order.
- In the contracts column, "+n minor" is relative to the contracts version before R1; each release with a format change bumps the contracts minor once.

**Default-suite policy:**
- R1: suite 1.0.0 gives the same results as on 0.21.
- R2: the stable suite is still 1.0.0, but its changed rules give `rule_not_run`. The release notes **MUST** say so and recommend reproducing 1.0.0 results with R1.
- From R3: the default suite is 1.1.0.

### 8.3 Renaming the code-name identifiers (WP-R, per DR-15)

#### 8.3.1 Purpose, status and timing

| Item | Content |
| --- | --- |
| Purpose | Replace the meaningless code name "v6.3 / v63" with descriptive names, without changing any behaviour or rewriting any historical record |
| Status | The tool is finished and verified (§8.3.5); **adoption depends on DR-15 (open)** |
| Timing | Phase 0 item 11 (§9.1): **MUST** come after item 5 (snapshots on by default) and ship in the **same release** (R1) as item 2 (registry schema 1.1.0) |
| Why this timing | The rename edits `contracts/rules/registry.json`, whose digest the semantic-lock pins (RN-4) |
| Tool | `rename_analysis_check_ids.py`; delivered into the plugin's `tools/` |

#### 8.3.2 Mapping

| Old name | New name |
| --- | --- |
| `docs/dev/v6.3/` | `docs/dev/cross-artifact-check/` (a forwarding `README.md` stays at the old path) |
| `test_v63_baseline_gaps` | `test_analysis_check_baseline_gaps` |
| `test_v63_d03a` | `test_analysis_check_profile_loading` |
| `test_v63_d04` | `test_analysis_check_effect_catalog` |
| `test_v63_d05a` | `test_analysis_check_identity_and_instances` |
| `test_v63_d05b` | `test_analysis_check_bundle_and_context` |
| `test_v63_d05c` | `test_analysis_check_report` |
| `test_v63_d05d` | `test_analysis_check_run_lineage` |
| `test_v63_d06` | `test_analysis_check_chain_rules` |
| `test_v63_d07` | `test_analysis_check_ratio_rules` |
| `test_v63_d07_model` | `test_analysis_check_model_rules` |
| `test_v63_d09` | `test_analysis_check_shadow_and_refusal` |
| `test_v63_d10` | `test_analysis_check_report_permit` |
| `test_v63_d11a` | `test_analysis_check_coverage_reader` |
| `test_v63_d11b` | `test_analysis_check_snapshots` |
| `test_v63_d12b` | `test_analysis_check_custody` |
| `test_v63_d17` | `test_analysis_check_review_integration` |
| `test_v63_refusal_blockers` | `test_analysis_check_refusal_blockers` |
| `test_v63_review_fixes` | `test_analysis_check_review_fixes` |
| `test_v63_rule_registry` | `test_analysis_check_rule_registry` |
| `v63_cases`, `v63_runs` (test helpers) | `analysis_check_cases`, `analysis_check_runs` |
| `tests/core/test_v63_evidence_query` | `tests/core/test_evidence_query` |

All of these are in `tests/contracts/` unless stated otherwise.

#### 8.3.3 Safety rules (normative)

| # | Rule | Reason |
| --- | --- | --- |
| RN-1 | Replace only **whole identifiers** from the mapping, never adjacent to a letter, digit or underscore; **MUST NOT** globally replace `v63` or `v6.3` | Confirmed: `test_v63_submission_bundle_digests` is a test method named after validation case **V63**, not the programme code name; a global replace would break it |
| RN-2 | **MUST NOT** modify: release manifests, `CHANGELOG.md`, `VALIDATION.md`, any `docs/dev/**/decision-*.md`, the content of moved records, pinned definitions (`contracts/vocab/effects.json`, `contracts/semantics/**`, `contracts/rules/suites/**`), `contracts/schemas/**` | Records are never rewritten (D12b); editing a pinned definition changes its digest and makes frozen analyses without snapshots unreproducible |
| RN-3 | Records are moved with `git mv` (history kept) and their content is unchanged; a forwarding `README.md` stays at the old path, so every old reference written as `docs/dev/v6.3/<file>` still finds the file (file names are unchanged) | Pinned definitions and historical records hard-code the old path |
| RN-4 | Test IDs in `contracts/rules/registry.json` **MUST** be updated together. Its digest is pinned by semantic-lock 1.0.0, so the rename ships only after snapshots are on by default, in the same release as other registry changes | Confirmed (0.24.1): after the rename, a bundle frozen by the old checker without snapshots gets 13 `semantics_unreproducible` (exit 3); with snapshots it stays complete |
| RN-5 | The tool must be idempotent: a second run changes nothing | Safe to re-run |
| RN-6 | Acceptance: the tool's `--verify` is ok, and the failure set of the full suite (`tools/run_all_checks.py`) is **identical** before and after. A timing test that fails on one side only and passes on reruns in both trees is recorded as flaky, not as a difference | The rename must not change any behaviour |
| RN-7 | After rewriting content, the committed derived files it affects **MUST** be regenerated: run only those of `tools/reference_inventory.py`, `tools/build_stanzas.py` and `tools/capability_map.py` whose `--check` fails; `--verify` requires all three `--check` runs to pass | Confirmed: `skills/hep-authoring/references/independent-review.md` cites four `docs/dev/v6.3/` paths; rewriting them changes its size, so `docs/reference-inventory.{json,md}` goes stale and three tests fail (`reference_inventory`, the soft budget, and the timeout test, which runs the inventory test internally) |

#### 8.3.4 What the tool does

| Item | Content |
| --- | --- |
| Modes | `ROOT` (dry run: lists the moves and edits), `ROOT --apply --date YYYY-MM-DD` (applies, then verifies), `ROOT --verify` (audit only) |
| Exit codes | 0 = ok; 1 = verification failed; 2 = usage error or refused (for example, a target already exists) |
| Does | 1. Moves per the mapping (`git mv` inside a git work tree); 2. replaces whole identifiers in non-protected text files (RN-1); 3. regenerates stale derived files (RN-7); 4. writes the forwarding `README.md` at the old path; 5. removes `__pycache__` |
| Does not | Modify any file listed in RN-2; edit a moved record after moving it |
| `--verify` checks | No leftover old identifiers; every target exists and no source is left behind; the forwarding stub exists and is the only file left in the old directory; all 107 registry test IDs resolve to existing modules; all three derived-file `--check` runs pass |
| Limits | Standard library only; skips `.git`, `__pycache__`, `.in_use` and `node_modules` |

#### 8.3.5 Verification results (2026-10-22, 0.24.1; Confirmed)

Setup: two throwaway copies of the installed 0.24.1 (before and after the rename), both git work trees with the same exclude rules for caches and the root `.in_use/` removed. The steps are in Appendix A.4.

| Check | Result |
| --- | --- |
| Moves | 23 (1 directory, 22 test modules); git classifies the 17 records as R100 (identical content), and the original directory index is byte-identical |
| Edits | 12 files rewritten; 2 derived files regenerated (`docs/reference-inventory.json`, `.md`); 1 forwarding stub added |
| Protected files | All unchanged |
| Idempotence | After a second run, `git status` is empty |
| `--verify` | ok: no leftovers; all 107 test IDs resolve; all three derived-file checks pass |
| Full suite (RN-6) | **Met.** Before and after, checks are 24 pass / 2 fail (`unittest`, `ams_optional`) / 1 skip (codex CLI not found); both sides run 4905 unit tests in 408 modules with 16 common failures (environment: sympy missing, LaTeX, external CLIs); **one-sided failures: 0**, and every count is identical; each run takes about 32 minutes |
| semantic-lock (RN-4) | Frozen on the pre-rename copy, checked on the renamed copy: without a snapshot store, 13 `semantics_unreproducible` (exit 3); with snapshots, complete (exit 0) |
| `plugin_release` | The renamed copy returns `unreleased` (its files have changed) until the release that carries the rename writes its own manifest. This is expected; the rename ships only in a release (RN-4) |

#### 8.3.6 Lessons from the verification

- **Derived files go stale.** The first comparison showed 4 extra failures after the rename, because the tool did not regenerate the reference inventory. RN-7 was added.
- **The two test setups must match.** In the first comparison the renamed copy was a git repo with no ignore rules, so the packaging check also counted test caches (3120 files, 48.3 MB). Those extra failures came from the setup, not the rename. Both copies **MUST** use the same exclude rules.
- **Never use a leftover copy as the source.** The full suite's `ams_optional` check copies the plugin to `/tmp/hep research no ams …` and leaves the copy behind when it times out. The rename source **MUST** be the clean installed or repository plugin.
- **Check that the version really is a release.** Confirm with `plugin_release()` that the baseline copy is a released build; that is how the earlier "0.23.0" baseline turned out to be a development build (§0.2).

---

## 9. Roadmap

### 9.1 Phase 0: foundations (release R1; estimate 6–8 sessions)

- **Entry conditions:** DR-9, DR-11, DR-12 and DR-13 decided (DR-13 must be decided before the Phase 1 measurement).
- **Work:**
  1. Version-guard mechanism: dispatch keyed by (rule_id, version); generator guard; input checks enabled by context version (G18).
  2. Function-level source digests; registry schema 1.1.0; `rule_registry.py check` fails when a digest changes without a version bump.
  3. Checker identity from the modules loaded at run time; the generator digest covers `obligations.py`, `model.py` and `effect_catalog.py` (G10, A1).
  4. P6: the status agrees with the exit code (G20).
  5. Snapshots on by default:
     - snapshots go to `<root>/.hep-research/snapshots/`;
     - freeze writes the bundle path to `<root>/.hep-research/bundles.json`;
     - `snapshots gc` deletes only digests that no indexed bundle references, and is a dry run by default.
  6. Cheap `check-report` refusals: dependency-missing, `lock_differences`, pre-release suite, mismatch with the frozen inventory (G11, the diagnostic part of G19).
  7. `assessment.plugin_release`.
  8. Classify G21.
  9. Add probes for G11–G22; mutation-testing skeleton.
  10. Confirm how old releases can be obtained (git tags).
  11. **Rename the code-name identifiers (WP-R; only if DR-15 is adopted):** run §8.3 with `rename_analysis_check_ids.py`. It **MUST** come after item 5 and ship in the same release as item 2 (RN-4).
- **Prohibition:** **no rule outcome may change.**
- **Exit conditions:**
  - V72–V76 pass;
  - existing tests pass;
  - `run_all_checks.py` is green;
  - suite 1.0.0 gives the same results on R1 as on 0.21;
  - if item 11 was done: RN-6 is met;
  - the gate record is confirmed by the programme owner.

### 9.2 Phase 1: evidence (estimate 4–10 sessions)

- **Entry conditions:** Phase 0 complete; DR-13 decided and registered in `decision-value-gate.md`.
- **Work:**
  1. The value gate (§10), with hand-written bundles and suite 1.0.0 (3–4 sessions).
  2. The optional spike (§12; 0–4 sessions).
  3. The assurance-plane design document (1–2 sessions, in parallel).
- **Prohibitions:** no rule changes; no adjusting thresholds after the fact.
- **Exit condition:** the gate result is recorded in `decision-value-gate.md`.

### 9.3 Decision point

The programme owner decides **continue, shrink or stop** from the gate result (§13.3).

### 9.4 Phase 2: completing the diagnostics (releases R2 → R3; estimate 11–16 sessions; only if the decision is "continue")

- **Entry conditions:** the decision point says "continue"; the pending revisions to DR-1 to DR-8 are confirmed by the programme owner.
- **Work:**
  - **R2:**
    - SemVer pre-releases and the registry unique key;
    - check-context 1.1.0 and the context conversion (V90);
    - calibration shape;
    - result binding 1.1.0;
    - fixes for G2–G8, G12, G13, G15–G17 and G22, released in `1.1.0-dev.N` suites.
  - **R3:**
    - G1 and G14;
    - catalog 1.1.0;
    - the four suites become 1.1.0 stable;
    - full mutation testing;
    - the entry path (if DR-14 passes; 2–3 sessions).
  - **G21:** the fix, if Phase 0 found it necessary (decided and estimated separately).
- **Exit conditions:** V77–V90 (and V91 if applicable) pass; the shadow review has zero unclassified differences.

### 9.5 Coverage extension (decided and estimated item by item)

O09, forward folding, per-sign ratio factors, eras, cross-section analyses, the full unit check (G22), DR-10.

### 9.6 Totals

| Scope | Sessions |
| --- | --- |
| To the decision point (Phase 0 6–8 + Phase 1 4–10) | about 10–18 |
| Phase 2 | about 11–16 |
| Everything | about 21–34 |

### 9.7 Gate common to every phase

- That phase's probes and new V cases pass;
- existing tests pass, or every changed assertion is listed in VALIDATION;
- `tools/run_all_checks.py` is green;
- the shadow review has zero unclassified differences;
- the gate record is confirmed by the programme owner.

---

## 10. Value-gate protocol (per DR-13; open)

| Step | Content |
| --- | --- |
| 1. Subject | The ams-flux-ratio spec and responses, with a hand-written recipe that **truthfully describes its TSVD unfolding**: subtract_background → unfold → correct_efficiency → divide_exposure → divide_bin_width |
| 2. Definition-induced results | With the current coverage, this recipe gives 4 `unrealized_correction` outcomes for `trigger_efficiency`. (Confirmed: `correct_efficiency` covers only `selection_efficiency`, while the program divides by both.) Using `divide_effective_exposure` instead gives `incomplete` (O09). **Pre-registered handling:**<br>• count these results in the false-positive arm, under "definition-induced";<br>• run once more with a bundle-supplied coverage that lists both members (flagged by A3), as a sensitivity analysis;<br>• neither counts as a detection |
| 3. Error taxonomy | Frozen in advance, by category rather than by rule; based on T3, `crflux-review.md` and published errata |
| 4. Planting | A non-author plants at least 20 errors, each into both the code and the descriptions, without seeing the rules. Preferably the person named under O04; if another agent stands in for now, the results are labelled "AI-planted" |
| 5. Scoring | Layer by layer: closure tests → `validate.py` and L2 → the checker (suite 1.0.0, run on R1). The main metric is the checker's **incremental detection** |
| 6. False-positive arm | Legitimate refactors, plus the "definition-induced" category from step 2 |
| 7. Cost | Record the number of hand-written fields per bundle, and which of them could in principle be derived (the basis for DR-14) |
| 8. Reproducibility | The measurement script is committed to the repository |
| 9. Thresholds | Pre-registered under DR-13 (`decision-value-gate.md`); they **MUST NOT** change after measuring |

**If DR-13 is rejected:** the programme stops after Phase 0 and does not enter Phase 2.

---

## 11. Entry-path specification (per DR-14; conditional on the value gate passing)

| Item | Specification |
| --- | --- |
| Command | `analysis_check.py draft --root DIR --spec SPEC` |
| Does | Lists the items (spec, response, dataset-record, calibration); copies the semantics table into the project; names the environment-lock source; derives the scope axes |
| **MUST NOT** | Write roots, instances, bindings or declarations automatically (always `TODO`; P4, P10); scan run records (they are passed to check with `--results`); derive operators from argv |
| freeze's part | Refuses any `TODO`; refuses roots whose unit is empty or a placeholder (the minimal G22 fix) |
| Skill routing | Changing a `SKILL.md` needs a new decision by the programme owner on O16 |
| Out of scope | Recipe templates (only `cosmic_ray_flux` declares operators, which does not help TSVD-type recipes) |

---

## 12. Bounded spike (per DR-12; optional)

- **Question:** on a new synthetic analysis chain using only contracted tools, can instances and data flow be derived from run records, and how many hand-written fields would that save?
- **Cap:** 3–4 sessions; stop when exceeded and record the result.
- **Limitation:** no operators are derived from argv (`cosmic_ray_flux.json:76`: whether the exposure includes efficiency is the caller's statement).

---

## 13. Governance

### 13.1 Owners

| Work | Owner |
| --- | --- |
| Programme owner; DR-9 to DR-15 decisions; confirming pending revisions; judging the value-gate result; confirming gate records | hchouTW (programme owner named in `decision-enforce.md`) |
| Drafting `decision-architecture.md` and `decision-value-gate.md` | The implementer drafts; the programme owner fills in the Decision sections |
| Running the value gate and its measurement script | The implementer |
| Running and verifying the WP-R rename | The implementer, per §8.3 and Appendix A.4 |
| Planting errors | To be named (O04); never a rule author |
| Assurance-plane design document | The implementer drafts; the custodian reviews (O17) |
| Non-author reviewer; roles that may accept reports | To be named (O04, O14) |
| `owner` of each rule in the registry | Stays the current skill name; `review_status` stays `unreviewed` until a non-author review |

### 13.2 Record convention (D12b)

- A decision record is **never rewritten** after its decision; a change is a new dated section.
- Each gate has one `decision-<gate>.md`; this programme adds `decision-architecture.md` and `decision-value-gate.md`.

### 13.3 Consequences of the value gate

| Outcome | Action |
| --- | --- |
| Pass | Enter Phase 2; decide DR-14 from the cost data of §10 step 7 |
| Shrink | Keep only the chain and ratio suite fixes; retire model-card, run-lineage and `custody.py` per §13.4 |
| Stop | Freeze the code; keep `--check-bundle` but mark it experimental; mark the manual instructions in skill references the same way; no new suites; keep the Phase 0 results (they change no rules) |

### 13.4 Retiring components without callers

- **Trigger:**
  - the value gate decides shrink or stop; or
  - **after the decision point**, two consecutive minor releases pass with no non-test caller and no gate use.

  Components assigned to the assurance plane (`check-report`, `custody.py`) are exempt until the assurance-plane design is decided.
- **Steps:**
  1. Deprecate in one release (CHANGELOG, README, related references).
  2. Remove the code in the next minor release.
  3. Readers explicitly refuse the old formats (the refusal matrix is maintained).

### 13.5 Exit conditions for shadow mode

For any rule to become an enforcing condition, **all** of the following must hold:
- the six G-ENFORCE conditions;
- the value gate passed;
- a non-author human review is complete (C15, O04);
- the custodian has adopted the gate requirement (O17);
- the roles that may accept reports are decided (O14).

This changes the exit conditions in `decision-enforce.md`, so it **MUST** be recorded there as a dated section.

---

## 14. Risks and open items

### 14.1 Risks

| Risk | Status | Response |
| --- | --- | --- |
| AI-planted errors still bias the value gate | Known | Prefer a human planter; otherwise label the results and discount them in the decision |
| The flagship case gives definition-induced violations | Confirmed | Pre-registered handling in §10 step 2 |
| G21 may need a change to the semantics table | Unresolved | Classify in Phase 0; a change needs its own decision |
| Unrelated definition changes cause `lock_differences` | Known | Absorbed by the default snapshots |
| In R2, some suite 1.0.0 rules give `rule_not_run` | Expected | The default-suite policy in §8.2 |
| Obtaining old releases | Unresolved: m0-baseline records only the 0.11.0 tag in the monorepo | Confirm in Phase 0 |
| No non-author human review yet | Known | §13.5 |
| The rename makes frozen bundles without snapshots unreproducible | Confirmed (RN-4) | The rename comes after snapshots are on by default, in the same release as the registry changes |
| The version installed when implementation starts differs from this document's baseline | Known (on 2026-10-22 alone the plugin moved from 0.21 to 0.24.1) | §15 rule 13: re-run Appendix A.1 and confirm the version before starting |

### 14.2 Open items

| Item | When |
| --- | --- |
| Nature and cost of the G21 fix | Phase 0 |
| Obtaining old releases | Phase 0 |
| Error planter; non-author reviewer | Phase 0 (O04) |
| Whether the member-set closure digest includes `catalog_version` | Before the Phase 2 catalog bump |
| A rule-to-definition map | Not scheduled; propose separately if needed |
| The full unit-consistency check (G22) | Coverage extension |
| No contracted tool for `unfold` or `correct_efficiency` | Coverage extension |
| Source of the analyst account; `read_protected` performance and Windows behaviour | Assurance-plane design |

---

## 15. Agent operating rules

An agent carrying out this programme (including Claude) **MUST** follow these rules:

1. **Check decision status first.** Before any work, check §7. If a relevant DR is "open" or "pending confirmation", only do preparatory work or drafts; **MUST NOT** implement the parts it affects.
2. **Never rewrite records.** For `docs/dev/v6.3/decision-*.md` (after the rename, `docs/dev/cross-artifact-check/decision-*.md`) and other records, only add dated sections. Decision sections are filled in by the programme owner; an agent **MUST NOT** fill them in.
3. **No rule changes in Phase 0.** No Phase 0 change may alter a suite 1.0.0 rule outcome. Verify by checking that suite 1.0.0 gives the same results on R1 as on 0.21.
4. **Rule changes require a version bump.** A fix that changes an outcome **MUST** raise that rule's version and be released through a pre-release suite (P3).
5. **Never auto-write intent.** No tool may generate check-context roots, instances, bindings or declarations automatically (P4, P10).
6. **Reports are diagnostics.** When reporting checker results, state that they are advisory; **MUST NOT** present them as authorization or as a pass (P1).
7. **Reproduce before fixing.** Before fixing a gap, make its probe fail; after the fix, make it pass. Do not just change assertions.
8. **Never move thresholds after the fact.** Value-gate thresholds **MUST NOT** change after measuring.
9. **Assurance plane: design only.** Until the preconditions in §5.1 hold, **MUST NOT** implement assurance-plane features.
10. **Leave protected areas alone.** **MUST NOT** modify `core/partition/`, `core/protected/`, or the permit and attestation schemas.
11. **Label evidence.** Statements in documents and reports carry Confirmed, Inferred or Unresolved, with their evidence.
12. **Rename only with the tool.** Code-name renames **MUST** use `rename_analysis_check_ids.py` and follow RN-1–RN-7 of §8.3.3; **MUST NOT** be done by hand or by global replacement.
13. **Confirm the baseline before starting.** Before implementation starts, re-run Appendix A.1 on the version installed at that time and confirm with `plugin_release()` that it is a released build; if the results differ from §0.2, update this document (§0.2, §1, §8.1) before implementing.

---

## 16. Document map and disposition

### 16.1 Working documents of this programme (scratchpad)

| Document | Status |
| --- | --- |
| `final/cross-artifact-check-architecture.zh.md` (Chinese) | **Valid** |
| `final/cross-artifact-check-architecture.en.md` (this document, English) | **Valid**; same content as the Chinese version |
| `final/test_cross_artifact_check_gap_probes.py` | **Valid**; covers G1–G10 now; Phase 0 adds G11–G22 |
| `final/rename_analysis_check_ids.py` | **Valid**: the WP-R rename tool (§8.3.4); delivered into the plugin's `tools/` |
| `final/cross-artifact-check-decision-rationale.zh.md` | **Rationale appendix.** The evidence and reasoning can be consulted, but its Decision texts **MUST NOT** be pasted. Refuted statements:<br>• DR-5 "availability only";<br>• DR-1 "automatically facts from S2";<br>• DR-3 bytes digest;<br>• DR-6 1e-12 and plain k;<br>• DR-7 label-only row;<br>• DR-8 root coverage |
| `archive/plans/cross-artifact-check-architecture-pre-cleanup-2.zh.md`, `.en.md` | Superseded (the same content before this clean-up) |
| `archive/plans/cross-artifact-check-architecture-pre-restructure.zh.md` | Superseded (the same content before the first restructuring, with the full disposition tables of both reviews) |
| `archive/plans/cross-artifact-check-plan-v2.zh.md` (v2) | Superseded; its §12 review record is kept |
| `archive/plans/cross-artifact-check-plan-v3.1.zh.md`, `-en.md` | Superseded; its §11 review record is kept; if DR-11 is rejected, its WP1 and WP6 become the basis again |
| `archive/plans/cross-artifact-check-architecture-rethink.zh.md` | Superseded; its §9 review record is kept |
| `archive/evidence/` (`review/`, `review3/`–`review6/`, `probe*.py`, `proto_*.py`, `usage.py`) | Kept as reproduction scripts. Run them from the plugin root with `PYTHONPATH` pointing at the script's folder. `review5/callers.py` takes the root as an argument; `review6/p6_scope.py` must run only in a throwaway copy |
| `archive/evidence/rename/` (`compare.py`, `lockprobe.py`) | Kept: the WP-R reproduction scripts (Appendix A.4) |
| `v241/` (`pristine/`, `proto/`, `lockp/`) | Kept until Phase 0 starts: a clean 0.24.1 snapshot, and the verification copies and outputs of §8.3.5 |
| `rename-proto/` | Kept until Phase 0 starts: the first rename verification, on the development build after 0.23.0 (including the comparison that led to RN-7) |
| `hr/` (plugin copy) | Kept until Phase 0 starts. A 0.21.0 copy that is not pristine: it contains the probe tests, and `plugin_release()` returns `unreleased` |

### 16.2 Plugin documents (recommendations; not yet modified)

If DR-15 is adopted, the `docs/dev/v6.3/` paths below become `docs/dev/cross-artifact-check/`.

| Document | Recommendation |
| --- | --- |
| `docs/dev/v6.3/README.md` | Index this architecture and the two new decision records |
| **New** `decision-architecture.md` | State and rationale of DR-1 to DR-15, with one Decision section per DR; replaces the `decision-hardening.md` proposed in v3.1 |
| **New** `decision-value-gate.md` | DR-13's design and pre-registered thresholds; after measuring, the result and the decision |
| `decision-enforce.md` | Text unchanged; add a dated section: the value gate joins the exit conditions; this document's phases replace the stacked-PR plan |
| `decision-m2a.md`, `m2a-design.md` | Text unchanged; add dated sections: DR-2 removes `root_not_required`; version guard; P6 |
| `decision-m0.md`, `decision-m2b.md` | Unchanged |
| `m2b-model-design.md` | Add a dated section: G5, G12 |
| `m2c-design.md`, `m2c-proposal.md` | After DR-11 is confirmed, add dated sections on the DR-1 and DR-7 changes |
| `custodian-gate-requirement.md` | Add a dated section: where the assurance plane sits, comparison with the reviewed report, the re-scoped `check-report` |
| `review-packet.md` | Add a dated section: adversarial review (run the probes and mutation tests) |
| `o16-agent-interface.md` | Add a dated section; changing a `SKILL.md` needs a new decision |
| `refusal-matrix.md`, `shadow-review.md` | Re-measure in dated sections when formats change |
| `m0-baseline.md`, `m0-budget.md`, `o03-model-pairings.md`, `crflux-review.md` | Unchanged |
| Plugin `README.md` (lines 275–312) | Note the diagnostic plane and current use |
| `docs/protected-data-architecture.md` | Add where the assurance plane sits in the formal-use gate; correct the stale "four contracts" on line 556 (there are 9) |

---

## 17. Evolution and review summary

| Stage | Result | Key reversals or corrections |
| --- | --- | --- |
| Two rounds of code checks | 10 gaps, written as probes | — |
| Plan v1 → v2 (independent review 1) | 18 gaps; a prerequisite work package added | Approved decisions had been treated as bugs; compatibility cost underestimated |
| Decision research DR-1–8 | "Trust follows custody" proposed | Initial recommendations for DR-3, DR-6, DR-7, DR-8 reversed |
| Plan v3 → v3.1 (independent review 2) | G19 added | Snapshots forgeable; files inside the project can never be protected; `1.1.0-dev` invalid |
| Architecture rethink v1 → v2 (independent review 3) | Two planes; value gate | The description model is deliberate; the execution bridge is not feasible; the gate was circular |
| Usage audit | No real workflow runs the checker | — |
| Final architecture (independent reviews 4 and 5) | One architecture; G20–G22; governance | The entry path must not auto-write intent; Phase 0 changes no rules; P6 aligned with the exit code; G22 reduced to a minimal fix |
| Code-name rename (WP-R, DR-15) | Rename tool; safety rules RN-1–RN-7 | The first comparison caught a stale reference inventory (RN-7 added). On the development build after 0.23.0: 4859 tests, 16 common failures, 0 failing only after the rename; the only one-sided failure was the timing test `test_scaling_check_rejects_a_quadratic_scan`, which passed 5 of 5 reruns in each tree and was recorded as flaky |
| Re-check against 0.24.1 | Facts, compatibility, tests and lock results all unchanged; the rename's full suite is identical before and after | The earlier "0.23.0" baseline was an unreleased development build; since 0.24.0 `plugin_release` returns the version on installed copies |
| Second clean-up | Added a one-page summary, a measurement-baseline table and an ID-family table; §8.3 split into six subsections; Appendix A rewritten as steps | The rename safety rules were renamed from R-1–R-7 to RN-1–RN-7 so they cannot be confused with releases R1–R3; no content change |

**Limitation:** all five reviewers were AI agents; the non-author human review required by C15 (O04) is still needed. The full disposition tables are in the review records of the documents under `archive/plans/`.

---

## Appendix A: Reproducing the evidence

Run every command from the plugin root unless stated otherwise.

### A.1 Baseline (§15 rule 13)

1. `python3 -c "import sys; sys.path.insert(0, '.'); from core.protected import identity; print(identity.plugin_release())"`: must return a released version, not `unreleased`.
2. `python3 -m unittest discover -s tests/contracts -t . -p 'test_v63_*.py'`: the 205 existing tests pass (after the rename, use `-p 'test_analysis_check_*.py'`).
3. `python3 contracts/rule_registry.py check`: pass; 23 rules, 71 V cases.

### A.2 Probe tests

1. Copy `final/test_cross_artifact_check_gap_probes.py` into the plugin's `tests/contracts/`.
2. Run `python3 -m unittest tests.contracts.test_cross_artifact_check_gap_probes -v`.

All 10 currently fail, as expected: each probe describes the intended behaviour.

### A.3 Review scripts

Run `PYTHONPATH=<script folder> python3 <script>`; individual limits are in the `archive/evidence/` row of §16.1.

### A.4 Rename verification (WP-R)

1. **Get a clean source:** the installed or repository plugin; **MUST NOT** be a leftover copy such as `/tmp/hep research no ams …` (§8.3.6).
2. **Make two copies** (before and after): remove the root `.in_use/` and every `__pycache__`; `git init` each; write `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.hypothesis/`, `.DS_Store` and `/.in_use/` into `.git/info/exclude`; `git add -A` and commit.
3. **Dry run:** in the "after" copy, run `python3 rename_analysis_check_ids.py .` and confirm 23 moves, every source present and every target absent.
4. **Apply:** `python3 rename_analysis_check_ids.py . --apply --date YYYY-MM-DD`; the output `status` must be `ok`.
5. **Idempotence:** commit, then repeat step 4; `git status --porcelain` must be empty.
6. **Protected files:** in `git diff -M --name-status HEAD~1`, files listed in RN-2 may appear only as R100 (pure moves).
7. **Full suite:** run `python3 tools/run_all_checks.py --out DIR` once in each copy (about 32 minutes each; run them one after the other, not in parallel, so timing tests are not disturbed).
8. **Compare:** `python3 archive/evidence/rename/compare.py OUT_BEFORE OUT_AFTER` maps the pre-rename test IDs to the new names with the tool's rules, then compares check statuses, failure sets and counts.
9. **One-sided failures:** rerun any failure that appears on one side only 5 times in each copy; if all reruns pass in both, record it as flaky (RN-6).
10. **Lock impact:** `python3 archive/evidence/rename/lockprobe.py BEFORE_TREE AFTER_TREE` (on clean trees exported with `git archive`): expect 13 `semantics_unreproducible` without a snapshot store and complete with snapshots (RN-4).

## Dated note (retirement)

This architecture describes the checker as of 2026-10-22 (0.24.1). Later events: Phase 0 shipped in 0.25.0; the value
gate measured I = 0 of 28 twice; Shrink removed `model-card` and `run-lineage` in 0.28.0; `decision-retire.md`
proposes retiring the rest, with the rules kept as review questions in hep-measurement and hep-statistics for use
through hep-review. Terms: R0-R3 now name hep-review's assurance tiers; the releases called R1-R3 here are 0.25.0 and
0.26.0. This note does not rewrite the sections above.
