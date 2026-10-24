# Geant4 simulation studies, the J15 minimal spectrometer and automated generation of design candidates: consolidated document

> Document type: consolidated plan, implementation specs and design rationale (for the implementing agent, reviewers and the maintainer). Status: awaiting the user's and the maintainer's approval
> Baseline: hep-research `main` at `5584927` (0.38.0), contracts 3.12.0, adapter geant4 0.1.0 (unchanged since `9f08796`), Geant4 11.4.3
> Date: 2026-10-24
> Language: English translation of the Traditional Chinese original [`geant4-program.md`](geant4-program.md), with the same content. If they disagree, the Chinese wins and the English is corrected at the same time
> Relation to main: this program plugs into main's detector system design loop (hep-detector, `skills/hep-detector/references/system-design-workflow.md`, `contracts/design.py`, `evaluate_design.py`); requirements, candidates, evidence and verdicts use main's artifacts and rules
> Execution environment: **every stage runs in its own isolated git worktree** (§P.10); never change the main checkout or another worktree

## How to use this document

**For the implementing agent:**
1. Read §P.0 (stages at a glance), §P.10 (running in an isolated worktree), §P.6 (gates) and §P.4 (interface ownership).
2. Create and confirm the isolated worktree for your stage per §P.10.2 (`.claude/worktrees/geant4-<stage>`, branch `worktree-geant4-<stage>`, based on the latest `origin/main` that contains the prerequisite stages); every later step happens in it.
3. Read main's `skills/hep-detector/references/system-design-workflow.md` (design loop, fidelities, gates); it is a prerequisite of Parts 3 and 4.
4. Read the task card of the part your stage belongs to (§A.0, §B.0 or §C.0), then that part's §1–§4 and your stage's work items and acceptance checklist.
5. Read Part 5 only when you need the reason for a rule.
6. This document is about 2,800 lines: read it in pieces by section number from the table of contents (e.g. search for `## §A.5`), not all at once.

**Authority of each part:**

| Part | Sections | Content | Authority |
|---|---|---|---|
| Part 1 Program plan | §P | Evaluation, principles, stages, interface ownership, naming, gates, open decisions, risks, execution environment | Stage order and dependencies, numbering, version placeholders, interface ownership, gates, open decisions, execution environment |
| Part 2 Task A | §A | Work items and acceptance of A1, A2; the shared hard rules (§A.3) and checks (§A.8) | Content and acceptance of these two stages |
| Part 3 Task B | §B | Geant4 F4 evaluator and the J15 design project; work items and acceptance of B1, B2, B3 | Content and acceptance of these three stages; J15's numbers |
| Part 4 Task C | §C | Automated generation of design candidates; work items and acceptance of C1, C2, C3 | Content and acceptance of these three stages |
| Part 5 Design rationale | §R | Design basis from real experiments, the architecture, relation to main's design loop, superseded designs | Rationale only; where it conflicts with Parts 2–4, Parts 2–4 win and the conflict is reported |

**Numbering:**
- Sections: "§A.8" is section 8 of Part 2 (task A), "§P.10.2" is section 10.2 of Part 1, "§B Appendix A" is appendix A of Part 3.
- Work items: "A1.6", "B2.1", "C2.4" (stage.number), unique across the whole document.
- Contract changes: named by owning stage as CV-A1, CV-B2, CV-C1, CV-C2, numbers fixed at release in merge order (all ≥ 3.13.0); "C1", "C2" on their own mean only stages.
- Fidelities: always main's F0–F5 (F0 heuristic, F1 analytic tool contract, F2 toy MC, F3 response / expected precision, F4 Geant4 study re-issued as `validated-in-scope`, F5 measurement); short Geant4 runs inside a search produce only "search values", which have no fidelity.
- Parts 2–4 share one structure: §X.0 task card, §X.1 terms and files, §X.2 prerequisites and provided interfaces, §X.3 hard rules, §X.4 design summary, from §X.5 one section per stage (work items and acceptance checklist), then contracts and versions, checks, not done and deferred, open decisions and risks, order of work, appendices.

**Consolidation note:** on 2026-10-23 the previously separate `plan.md`, `task-a-core.md`, `task-b-j15.md`, `task-c-design-search.md` and `architecture.md` (and their English versions) were merged into this document with unchanged content; only section numbers and cross-references were rewritten, and the old files were removed. Each part's version history stays in that part's appendix. The programs computing design numbers (`gate_operating_characteristics.py`, `j15_design_estimates.py`, `design_search_closure.py`) remain separate files in the same folder.

**Re-plan note:** on 2026-10-24, after the review against main 0.38.0 ([`review-2026-10-24-main-0.38.md`](review-2026-10-24-main-0.38.md)), the program was re-planned around main's detector system design loop: task B becomes the Geant4 evaluator for F4, J15 becomes a design project, and task C becomes the candidate generator `evaluate_design.py search`; see §P.1 and §P.11.

## Table of contents

- **Part 1 — Program plan (§P)**
  - §P.0 One-page summary
  - §P.1 Evaluation: problems and how they are handled
  - §P.2 Planning principles
  - §P.3 Content and acceptance of the stages (summary)
  - §P.4 Interface ownership
  - §P.5 Naming and numbering
  - §P.6 Stage gates
  - §P.7 Decisions awaiting the maintainer (consolidated list)
  - §P.8 Main cross-task risks
  - §P.9 Document map and authority
  - §P.10 Execution environment: isolated worktree
  - §P.11 Version history
- **Part 2 — Task A: correctness fixes and boundary artifacts (§A)**
  - §A.0 Task card
  - §A.1 Terms and files
  - §A.2 Prerequisites and provided interfaces
  - §A.3 Hard rules
  - §A.4 Design summary
  - §A.5 Stage A1: correctness fixes (contracts CV-A1, sci-fix)
  - §A.6 Stage A2: shared headers and boundary artifacts (geant4 adapter 0.2.0)
  - §A.7 Contracts and versions
  - §A.8 Checks at the end of every stage
  - §A.9 Not done and deferred
  - §A.10 Open decisions and residual risks
  - §A.11 Suggested order of work
  - §A Appendix A: Statistics summary
  - §A Appendix B: Numbers
  - §A Appendix C: Baseline values (`9f08796`; rechecked against `5584927` on 2026-10-24)
  - §A Appendix D: Sources
  - §A Appendix E: Version history
- **Part 3 — Task B: `element_sim`, reconstruction and the J15 minimal spectrometer (§B)**
  - §B.0 Task card
  - §B.1 Terms and files
  - §B.2 Prerequisites and provided interfaces
  - §B.3 Hard rules
  - §B.4 Design of J15
  - §B.5 Stage B1: `element_sim`, event files and geometry derivation (geant4 adapter 0.3.0)
  - §B.6 Stage B2: reconstruction and the F4 interface (geant4 adapter 0.4.0, contracts CV-B2)
  - §B.7 Stage B3: the J15 design project
  - §B.8 Contracts and versions
  - §B.9 Not done and deferred
  - §B.10 Open decisions and residual risks
  - §B.11 Suggested order of work
  - §B Appendix A: numbers
  - §B Appendix B: sources
  - §B Appendix C: version history
- **Part 4 — Task C: automated candidate generation (§C)**
  - §C.0 Task card
  - §C.1 Terms and files
  - §C.2 Prerequisites and provided interfaces
  - §C.3 Hard rules
  - §C.4 Design
  - §C.5 Stage C1: F1 search (contracts CV-C1)
  - §C.6 Stage C2: Geant4 search values and F4 confirmation (geant4 adapter 0.5.0, contracts CV-C2)
  - §C.7 Stage C3: Examples (J16)
  - §C.8 Contracts and versions
  - §C.9 Not done and deferred
  - §C.10 Open decisions and residual risks
  - §C.11 Suggested order of work
  - §C Appendix A: Numbers
  - §C Appendix B: Sources
  - §C Appendix C: Version history
- **Part 5 — Design rationale (§R)**
  - §R.0 Summary
  - §R.1 Design basis: what real experiments teach
  - §R.2 Goals, constraints and principles
  - §R.3 Architecture overview
  - §R.4 Data tiers and the run summary
  - §R.5 Execution, seeds, blocks and reproducibility
  - §R.6 Validation classes and decisions
  - §R.7 Contracts, traceability and sci-fix
  - §R.8 Code and CI
  - §R.9 Generality
  - §R.10 Stages and acceptance
  - §R.11 Residual risks
  - §R.12 Decision record
  - §R.13 History: superseded designs
  - §R.14 Sources
  - §R.15 Relation to main's detector system design loop (2026-10-24)

---

# Part 1 — Program plan (§P)

> Date: 2026-10-24 (re-planned against the detector system design loop of main 0.38.0)

---

## §P.0 One-page summary

This program plugs into the detector system design loop main already has (hep-detector, 0.37.0–0.38.0): the design-spec / design-candidate / design-evaluation artifacts, verdicts derived by `contracts/design.py`, fidelities F0–F5, and the human gates H1–H4. It adds the three things the loop lacks: **correct Geant4 labels** (task A), **a Geant4 evaluator that can count as F4** (task B), and **automated candidate generation** (task C). Three tasks, eight stages; each stage is a change that can be merged on its own, with its own acceptance list:

| Stage | Task | In one sentence | Prerequisite | Version | Size |
|---|---|---|---|---|---|
| **A1** | A correctness | Fix defects D1–D8, D10 and D11 that wrongly issue `validated-in-scope`; put the shared statistics and summary modules in `core/` (reusing existing functions); let `evaluate_design.py f4` complete `label --upgrade` | — | contracts **CV-A1** (sci-fix) | large |
| **A2** | A boundary artifacts | `g4sim` shared headers, per-event seeding, `layered_sim` writes the three boundary artifacts; the study layer reads only boundary artifacts (D9) | A1 | geant4 adapter **0.2.0** | large |
| **B1** | B new backend | `element_sim` (box elements, piecewise-uniform field, plane hits for every charged track, calorimeter leakage), per-event ROOT files, `simroot`; `geant4_run.py from-geometry` turns `design-geometry/1` into `element_sim.spec/1` | A2 | geant4 adapter **0.3.0** | large |
| **B2** | B reconstruction and F4 interface | `simreco` with switchable tail sources; `label` writes `results`, `tail_sources_simulated` and the geometry file; tracking reference benchmark (the F4 qualification path); mapping 1.1.0 | B1 | geant4 adapter **0.4.0**, contracts **CV-B2** | large |
| **B3** | B J15 | J15 as a design project (design-spec + candidates), F1 and F2 through `evaluate_design.py run`, F4 through `geometry → study → f4`; the validation ladder is a separate `unvalidated` record | B2, G-D0 | example and docs; journey J15 | medium (compute-heavy) |
| **C1** | C candidate generator | `evaluate_design.py search`: searches at main's F1, writes a `search_summary`, turns finalists into candidates with `expand --search`; writes no verdicts and ranks nothing | — | contracts **CV-C1** | medium |
| **C2** | C Geant4 search and confirmation | Search values from short `element_sim` runs, common-random-number paired comparison, winner's-curse protection; finalists confirmed at F4 with fresh seeds; `design.py` refuses evidence that uses search seeds | B2, C1 (confirmation also G-D0) | contracts **CV-C2** | large |
| **C3** | C examples | Search on Example A (space spectrometer) and Example B (collider tracker + ECAL); optional Bayesian-optimisation backend | C2 | example and docs; journey J16; optional `adapters/design-bo/` **0.1.0** | small to medium |

```
D0 (maintainer approves the F4 qualification path) ─┐
                                                    ▼
A1 ──▶ A2 ──▶ B1 ──▶ B2 ──┬───────────────────────▶ B3
                          │
C1 ───────────────────────┴──▶ C2 ──▶ C3
```

- The critical path to "a Geant4 study counts as F4 evidence in the design loop" is A1 → A2 → B1 → B2, plus the approval of D0.
- C1 depends only on main and can run in parallel with A and B from day one.
- C2's search part waits only for B2 and C1; its F4 confirmation and B3 both wait for D0.

---

## §P.1 Evaluation: problems and how they are handled

The previous version (2026-10-23) was based on main `9f08796` (0.23.0). The review against main 0.38.0 on 2026-10-24 (`review-2026-10-24-main-0.38.md`) found that main already has a complete design loop, so the program was re-planned.

| # | Problem | Impact | Handling |
|---|---|---|---|
| P1 | **A detector-level Geant4 study cannot become F4.** F4 accepts only studies re-issued as `validated-in-scope` (`contracts/design.py:1004`); upgrading needs a reference benchmark whose scope covers the study, and resolution, charge confusion and shower containment have none | No Geant4 result of task B or C can enter the design loop | Build an F4 qualification path (D0, §P.7 item 1): the study may be upgraded only when its material scope, the field-propagation verification, the reconstruction verification and a new tracking reference benchmark all pass (B2) |
| P2 | **Fidelity name clash.** Task C's F0/F1/F2 in the previous version meant something different from main's F0–F5 | Readers and `design.py` read the same name differently | The whole document uses main's names (§P.5); short Geant4 runs inside a search produce only "search values", which have no fidelity |
| P3 | **Task C rebuilt a design system of its own**: its own requirements spec, design format, requirement verdicts, ranking and "recommended design", and broke main's rules (verdicts derived only by `design.py`, never claim a global optimum, gates need a human) | Cannot be merged | C becomes a candidate generator for stage D2, `evaluate_design.py search`: it reads the design-spec and a base candidate, writes only a `search_summary`, and finalists become candidates through `expand`, whose verdicts `report` derives |
| P4 | **The F4 data path is incomplete.** Nothing on main writes `extension.study.results` or `tail_sources_simulated`; `evaluate_design.py f4` calls `label --upgrade` without `--run-record`, so `label` always refuses | F4 cannot actually be produced | A1 fixes the pass-through and the exit code in `f4`; B2 makes `label` write the fields F4 needs and adds an end-to-end test |
| P5 | **A1 missed a defect and used old formats.** The convergence gate passes on coarser points when the finest scan point is missing (D11); the ledger and advisory formats changed; a Garwood interval and a seed derivation already exist in `core/stats` | A1 cannot start as written | A1 adds D11, uses the new formats and reuses existing functions (Part 2) |
| P6 | **A1 scope creep** (handling kept from the previous version). Functions only later stages need stay out of A1 | The sci-fix is delayed | Principle R1; the decision engine has only `equivalence` and `detection_limit` in A1, B2 adds `change`; requirement verdicts belong to `design.py` |
| P7 | **Contract-change placeholders depend on merge order.** C1 no longer depends on A and may merge before A1 | The order "CV1–CV3" no longer holds | Named by owning stage: CV-A1, CV-B2, CV-C1, CV-C2; numbers fixed at release in merge order (§P.5) |
| P8 | **Interfaces in the wrong layer** (kept). `core/` may import only `core` (`check_layering.py:4`) | `core/` cannot use `contracts/schema.py` | The summary schemas live in `contracts/schemas/` and are validated by adapter or skill scripts; `core/simulation/` only computes |
| P9 | **Open decisions and gates scattered** (kept) | Nobody sees which decision blocks which stage | Merged into the two tables §P.6 and §P.7; items main has already decided are marked with their source |

**Interfaces main provides that this program uses directly:** design-spec, design-candidate, design-evaluation (contracts 3.11.0); `contracts/design.py` (verdicts, aggregation, screening, comparison basis, ranking and Pareto, F4 and F5 checks); `contracts/rules/design_adequacy.json` (screening and compliance fidelity per figure of merit); `contracts/rules/design_geometry.json` (the `layered-spectrometer` mapping 1.0.0); `evaluate_design.py` `run`, `budget`, `geometry`, `f4`, `scan`, `expand`, `plan`, `report`; parameter-level staleness and `run_workflow.py --incremental`; `scan_summary`; the capability `detector-design` (hep-detector).

**What this program adds:** correct labels and statistics (A1); a Geant4 application, reconstruction and tail sources that can produce F4 (B1, B2); a complete demonstration of J15 as a design project (B3); automated candidate generation and multi-fidelity Geant4 search (C1, C2); demonstrations on two examples (C3).

---

## §P.2 Planning principles

| # | Principle | Explanation |
|---|---|---|
| R1 | **Introduced by the first user, but placed right from the start** | Each interface is added in the first stage that needs it; shared interfaces live from day one where every user can import them (`core/`, `contracts/`) |
| R2 | **Schemas evolve only by addition** | New fields are optional; version numbers get a minor increase; old records can always be read and replayed |
| R3 | **One official implementation per quantity** | An implementation in another language or place may only serve as a test oracle; functions `core/stats` already has are reused |
| R4 | **Keep the sci-fix minimal** | A1 contains only the changes needed to fix the defects and their direct foundations (including the small fixes that keep the F4 consumer from misreporting) |
| R5 | **Every stage can be merged on its own** | It has its own version, VALIDATION entry, CHANGELOG and acceptance list; after the merge the plugin is consistent |
| R6 | **Reproducible verdicts, traceable numbers** | Reproduction means the same verdict and label (§R.5.6); results carry the search size and the evidence correlation |
| R7 | **AI is the designer, not the judge** | Claude chooses structures, proposes candidates and interprets results; "is it met" is derived only by `contracts/design.py` from the artifacts, and gates are approved by a human |
| R8 | **Plug into main's design loop, do not build a second one** | Requirements are a design-spec, candidates are design-candidates, evidence is design-evaluations; fidelities are main's F0–F5 |
| R9 | **Verdicts are derived only by `design.py`** | This program's code writes no verdict, maturity, stale marker, `screened_out` or `at-risk`; `core/stats/decisions.py` decides only study-layer gates (convergence, benchmarks, regression) |
| R10 | **Never claim a global optimum** | A search front is a non-binding search-stage front; ranking and Pareto come only from `report` when the comparison basis holds |

---

## §P.3 Content and acceptance of the stages (summary)

The full work items and acceptance of each stage are in Parts 2–4; here only the scope boundaries are listed, to avoid overlap.

| Stage | Includes | Explicitly excludes (in which stage) |
|---|---|---|
| A1 | Fixes of D1–D8, D10, D11; benchmark table and validation classes (reference, setup-matched, sanity, interface); scope comparison; configuration and isolation (`spec-v1`); block batch means, exact intervals (reusing `central_interval` of `core/stats/poisson_diagnostics.py`), MPV, quantiles; the decision engine's `equivalence` and `detection_limit`; two-stage event counts; seed hash H (its relation to `toy_ensemble.toy_seed` stated); `extension.simulation.evidence_role`; the schemas of `simulation-summary/1` and `simulation-observables/1` (`contracts/schemas/`); the Python summary generator; `tolerance_mode` `absolute` (the P6 exception: A1's own J14 benchmarks need it); `evaluate_design.py f4` passes `--label-run-record` through and maps `label` exit 3 to `incomplete`; the new ledger and advisory `/2` formats; J14 regeneration | `change` and regression (B2), the `results` and tail-source fields (B2), the seed rules for search and confirmation (C2), the `values` accumulator (C2), C++ summary (A2) |
| A2 | `g4sim` (`SimHash`, `SimSeed`, `SimSummary`, `MiniJson`, `SimProbe`); `per-event` seeding; `layered_sim` writes summary, column map, effective config; `tree-v1`; effective config stored by content hash; `validate_spec`, `spec.schema.json` and `Spec.cc` accept `run.seeding`, `output.observables`, `output.blocks`, `output.debug_observable_dump`; `geant4_run.py run` writes `argv`, `script_sha256`, `versions.plugin_release`; the study layer reads only boundary artifacts; schema keywords (`maxItems`, `maximum`, `exclusiveMaximum`; never `uniqueItems`) | `element_sim` (B1) |
| B1 | `element_sim.spec/1`, `element_sim`, piecewise-uniform field, a plane hit table for every charged track, calorimeter mother volume and leakage columns, per-event ROOT files, `simroot`, `geant4_run.py check-spec` (registered in `MISSING_FILE_ARGS`), `geant4_run.py from-geometry` with the realization profile, interface consistency of the two backends, deterministic field check | `simreco` and tail sources (B2), mapping 1.1.0 (B2), J15 (B3) |
| B2 | `simreco` (digitization and reconstruction, portable RNG); switchable tail sources (misalignment, digitization and noise, hit association, field-scale miscalibration) and the curvature offset; `geant4_run.py reco` and `table`; transitive processing chains; verification and regression classes, the regression role, the decision engine's `change`; Gaussian-core resolution and counting charge-confusion observables; `label` `--results`, `--geometry`; `f4` accepts asymmetric or exact uncertainties; mapping 1.1.0; tracking reference benchmark and the F4 qualification rule; end-to-end test `geometry → study → label --upgrade → f4`; CV-B2 | J15 design project (B3); the surrogate class for task C (deleted) |
| B3 | J15's design-spec and candidates (nominal 0.5 T / N = 6, variants N = 4, N = 8); F1 and F2 through `evaluate_design.py run`; one F4 study per (figure of merit, denominator); demonstrating that the bound moves from `optimistic` to `estimate` as tail sources are switched on, the model envelope, and charge confusion at `chain.incomplete` without data validation; the validation ladder (field propagation, TOF, sampling fraction; the isolated PVT benchmark is a separate study record) as an `unvalidated` record; calorimeter cut convergence, variations, TOF σ_t sensitivity; journey J15 | — |
| C1 | `evaluate_design.py search` and `expand --search`; the search spec (parameter ranges, subsystem slots per role, evaluation budget, seed, objectives = figures of merit of the adequacy table); genome and decoder (written as `overrides` on the base candidate); in-process F1 evaluation by the same functions the tool contracts run; NSGA-II, Sobol, WFG hypervolume; `search_summary` (CV-C1, exempt from the orphan-run rule); closure tests; the section "D2 automated candidate generation" in `system-design-workflow.md` | Any Geant4 evaluation (C2); verdicts, ranking, recommended design (not done; `design.py`'s job); a new reference file or `SKILL.md` change (not done) |
| C2 | Search values from `from-geometry` and short `element_sim` runs; common random numbers and paired comparison (G-C2a); the `values` accumulator (Python and `SimSummary.hh`, `values_max` per block); winner's-curse toys; seed roles and cache key; F4 confirmation of finalists; the search-seed rule in `design.py` (CV-C2) | Examples (C3); selection-aware coverage (only proposed to hep-statistics and `design.py`) |
| C3 | Searches on Example A and Example B (with `capability.unavailable` rows), finalists through the report gates (including a refused ranking when expected-precision is missing), one Geant4 confirmation on Example A once C2 is merged; journey J16; optional `adapters/design-bo/` (Ax/BoTorch) | — |

---

## §P.4 Interface ownership

| Interface | Introduced | Location | Owner (steward) | Users |
|---|---|---|---|---|
| Benchmark table, validation classes, scope comparison, isolation rule | A1 (B2 adds verification, regression, tracking reference) | `contracts/validate.py`, `dependencies.py`, `geant4_benchmarks.py` | contracts (content proposed by hep-detector) | A1, B2, B3, C2 |
| Seed hash H (Python) | A1 | `core/simulation/seeds.py` (states its relation to `toy_seed` in `core/stats/toy_ensemble.py`) | hep-detector | geant4 adapter, `check_geant4_study.py`, `evaluate_design.py search` |
| Seed hash H (C++) | A2 | `adapters/geant4/assets/g4sim/SimHash.hh` | hep-detector | `layered_sim`, `element_sim`, `simreco` |
| `extension.simulation.evidence_role` | A1 | `contracts/`, study spec schema | contracts | all |
| Regression role | B2 | same (CV-B2) | contracts | B2, B3 |
| Schemas of `simulation-summary/1`, `simulation-observables/1` | A1 (`values` added in C2) | `contracts/schemas/` | contracts (content proposed by hep-detector) | all |
| Reading and merging summaries (computation only) | A1 | `core/simulation/summary.py` | hep-detector | all |
| Schemas of the column map and effective config | A2 | `contracts/schemas/` | contracts | A2, B1, C2 |
| `tree-v1` target hash and `hash_scheme` | A2 (A1 has `spec-v1`) | `g4sim/SimProbe.hh`; comparison in `check_geant4_study.py` | hep-detector | A2, B1, B3, C2 |
| `per-event` seeding (`run.seeding`) | A2 | `g4sim/SimSeed.hh`, spec/1 | hep-detector | `layered_sim`, `element_sim` |
| Physics probe (physics part of the effective config) | A2 | `g4sim/SimProbe.hh` | hep-detector | A2, B1, B2 (regression), C2 |
| Block estimators, MPV, quantiles | A1 (`values` quantiles in C2) | `core/stats/batch_means.py` | hep-statistics | hep-detector scripts, `evaluate_design.py search` |
| Distribution functions (`t_ppf`, `f_ppf`); Garwood reuses `central_interval` | A1 | `core/stats/distributions.py`; `core/stats/poisson_diagnostics.py` | hep-statistics | same |
| Study-layer decision engine | A1 `equivalence`, `detection_limit`; B2 `change`; C2 paired mode | `core/stats/decisions.py` | hep-statistics | A1, B2, B3, C2 |
| `--label-run-record` and exit-code mapping of `evaluate_design.py f4` | A1 | `skills/hep-detector/scripts/evaluate_design.py` | hep-detector | B3, C2 |
| `g4sim` headers | A2 (`SimSummary` `values` in C2) | `adapters/geant4/assets/g4sim/` | hep-detector | `layered_sim`, `element_sim`, `simreco` |
| `element_sim.spec/1` and `check-spec` | B1 | geant4 adapter | hep-detector | B1, B3, C2 |
| `geant4_run.py from-geometry` and the realization profile | B1 | geant4 adapter | hep-detector | B3, C2 |
| Per-event ROOT files, `simroot` | B1 | geant4 adapter | hep-detector | B2, B3 |
| `simreco`, reco spec and tail sources | B2 | geant4 adapter (C++, not linked to Geant4) | hep-detector | B3, C2 |
| Study record `results.<fom>`, `tail_sources_simulated`, geometry file (`label --results`, `--geometry`) | B2 | `skills/hep-detector/scripts/check_geant4_study.py` | hep-detector | B3, C2 (through `f4`) |
| Geometry mapping 1.1.0 | B2 | `contracts/rules/design_geometry.json`, `contracts/schemas/design_geometry.json` (CV-B2) | contracts | B3, C2 |
| Asymmetric and exact uncertainties in `f4` | B2 | `contracts/design.py`, `evaluate_design.py` (CV-B2) | contracts | B3, C2 |
| Tracking reference benchmark and the F4 qualification rule | B2 (in force after D0 is approved) | `geant4_benchmarks.py`, `geant4-study-protocol.md` | hep-detector | B3, C2 |
| `evaluate_design.py search`, `expand --search`, search spec, genome and decoder | C1 | `skills/hep-detector/scripts/evaluate_design.py` | hep-detector | C1–C3 |
| `search_summary` (computational-run field, exempt from the orphan-run rule) | C1 | `contracts/schemas/ext_computational_run.json`, `contracts/design.py` (CV-C1) | contracts | C1–C3 |
| In-process F1 search values | C1 | `evaluate_design.py search` imports the F1 tool scripts and calls their `main(argv)` with the tool contract's arguments (C1.4); no new `core/` module (the admission rule in `core/OWNERS.json` requires use by several top-level components, and these tools and `evaluate_design.py` all belong to hep-detector) | hep-detector | `evaluate_design.py search` |
| Search-seed rule (an evaluation whose run or study seed appears in a search summary → `design.contract_mismatch`) | C2 | `contracts/design.py` (CV-C2) | contracts | C2, C3 |
| Optional Bayesian-optimisation backend | C3 | `adapters/design-bo/` (lazy import) | hep-detector | C3 |

Calls across adapters and skills always go through subprocesses and JSON files (layering rule: adapters import only `core` and `contracts`; `evaluate_design.py` does not import `adapters/geant4`), e.g. `evaluate_design.py search` calls `geant4_run.py from-geometry`, `run`, `reco`.

---

## §P.5 Naming and numbering

| Object | Form | Example |
|---|---|---|
| Stage | task letter plus number | A1, A2, B1, B2, B3, C1, C2, C3 |
| Work item | stage.number | A1.6, B2.1, C2.4 |
| Contract change (numbers fixed at release in merge order, all ≥ 3.13.0) | **CV-A1, CV-B2, CV-C1, CV-C2** | CV-A1 = A1's contracts minor (sci-fix); CV-C1 = `search_summary` |
| Gating form | `strict or _at_least(contract_version, CV-x)` | — |
| Fidelity | main's **F0–F5**: F0 heuristic (no run), F1 analytic tool contract, F2 toy MC, F3 response / expected precision, F4 Geant4 study re-issued as `validated-in-scope`, F5 measurement | short Geant4 runs inside a search produce only "search values" |
| geant4 adapter versions | 0.2.0 (A2), 0.3.0 (B1), 0.4.0 (B2); C2 is 0.5.0 only if it adds a run option | — |
| Other adapters | only the optional `adapters/design-bo/` 0.1.0 (C3); there is no `adapters/detector-design/` | — |
| Journeys | J14 thin silicon (existing), J15 minimal spectrometer design project (B3), J16 automated candidate generation (C3) | main's journeys end at J14 |
| VALIDATION entries | GEANT4-CORRECTNESS (A1), GEANT4-SUMMARY (A2), GEANT4-ELEMENT (B1), GEANT4-F4 (B2), GEANT4-J15 (B3), DESIGN-SEARCH-F1 (C1), DESIGN-SEARCH-G4 (C2), DESIGN-SEARCH-EXAMPLES (C3) | — |
| Open decisions | D0 and the numbers of §P.7 | D0 = F4 qualification path |
| Section references | all within this document: "§P.n" is Part 1, "§A.n", "§B.n", "§C.n" are Parts 2–4, "§R.n" is Part 5; "§B Appendix A" is the appendix of Part 3 | — |

The previous CV1, CV2, CV3 become CV-A1, CV-B2, CV-C2; CV-C1 is new. The previous task C's "F0" corresponds to main's F1, and its "F1, F2" and "confirmation" correspond to search values and F4.

---

## §P.6 Stage gates

| Gate | When | Condition | If it fails |
|---|---|---|---|
| G-D0 | Before B3 starts and before C2's confirmation starts | The maintainer approves the F4 qualification path (§P.7 item 1) | B3 and C2's confirmation do not start; B2's qualification rule stays but is not in force |
| G-A1 | Before A1 merges | The regenerated J14 records pass `--strict` and `dependencies.py`; the gate, coverage, MPV and detection-limit toys pass; `tools/scifix_ledger.py report` and the advisory check pass; the `f4 --label-spec` test passes as Part 2 describes | Do not merge; if J14 loses `validated-in-scope` by not reaching its target, the maintainer decides per §P.7 item 5 |
| G-A2 | Before A2 merges | J14's CSVs are bit-identical to those before A2; the probe does not change the random state | Do not merge |
| G-B1a | First day of B1 | `G4RootAnalysisReader` can read MT-merged, compressed files and string columns | `simroot` reads only scalar columns and strings move to a JSON side file (B1.5); either outcome is acceptable |
| G-B1b | Before B1 merges | The deterministic field check passes at nominal values; the common observables of the two backends agree by `equivalence` (declared tolerance and se target); the calorimeter comparison uses total leakage (sum of rear, front and lateral); `from-geometry` produces the same spec for the same geometry file | Do not merge |
| G-B2 | Before B2 merges | The end-to-end test `geometry → study → label --upgrade → f4` passes; the tracking reference benchmark catches its negative control; with all tail sources off the results agree with B1 | Do not merge |
| G-C1 | Before C1 merges | All closure tests pass; `search` writes no verdict; candidates produced by `expand --search` pass `design.py` | Do not merge |
| G-C2a | C2's trial | Measure the variance reduction of the paired comparison | If the reduction is below the declared value, use independent comparison (C2.3) |
| G-C2b | Before C2 merges | The winner's-curse toys and the contract tests of the search-seed rule pass | Do not merge |
| G-C3 | Before C3 merges | The searches on both examples are complete and the finalists pass the report gates | Do not merge |

---

## §P.7 Decisions awaiting the maintainer (consolidated list)

| # | Item | Recommendation | Blocks |
|---|---|---|---|
| 1 | **D0: the path by which a detector-level Geant4 study becomes F4** | Build a qualification path (direction chosen by the user): materials inside the scopes of passed A1 material benchmarks, the field-propagation verification passed, the reconstruction verification passed, and a new tracking reference benchmark passed (multiple-scattering angular width in an isolated Si slab against PDG Highland / Lynch–Dahl, with a negative control, scope dimensions rigidity and species); the other option (`design.py` admits unvalidated F4 for screening only) is not taken | B3, C2's confirmation |
| 2 | Classification of CV-A1 | minor plus sci-fix | A1 |
| 3 | Stewards and second consumers of the new `core/` modules | statistics to hep-statistics; `core/simulation/` to hep-detector; registered in `OWNERS.json` | A1 |
| 4 | hep-computing agrees to declare `simulation` and `search_summary` in `ext_computational_run.json` | agree | A1, C1 |
| 5 | Two-stage factor F₀.₉₀ or F₀.₉₅; what happens if the regenerated J14 loses `validated-in-scope` by chance | use F₀.₉₅ for the J14 re-recording; if lost, record it and keep the old record in the advisory | A1 |
| 6 | Live re-recording of J14's scan and variation runs, and the recorded size cap | re-record; cap 3 MB | A1 |
| 7 | Switching threshold for exact intervals | any block at 0 or total < 100 | A1 |
| 8 | How G5 "no copied example code" is confirmed | the reviewer confirms in the VALIDATION entry | A2, B1 |
| 9 | Storage location and retention of ROOT files | not committed; left to the user's storage, records keep only hashes | B1 |
| 10 | Transitive processing chains (hep-computing agreement) and classification of CV-B2 | agree; minor | B2 |
| 11 | Whether the C++17 CI job for `simreco` is required | required | B2 |
| 12 | `results` keyed by denominator; several geometry files per candidate | first use "one study per (figure of merit, denominator)"; keyed results as a later improvement of main | B3 |
| 13 | Classification of CV-C1 and CV-C2 | minor | C1, C2 |
| 14 | Whether the Bayesian-optimisation backend (Ax/BoTorch) is listed as a tested tool | list as optional | C3 |
| 15 | New CI impact groups (`adapters/geant4/**`, `core/stats/**`, `core/simulation/**`) | add them, to avoid full CI runs | A1 |

**Already decided by main (no longer open):**
- The owner of the capability `detector-design` is hep-detector (`docs/capability-map.json`).
- The entry to the design loop is a hub link with no change to the `SKILL.md` description (CHANGELOG 0.37.0, OQ-01); task C only adds a section to `system-design-workflow.md`.
- The search is a subcommand, following the precedent of `scan` (OQ-18).
- The previous `extension.design_search` becomes the computational-run field `search_summary` (like `scan_summary`).
- The previous detector-design adapter, requirements-spec schema and component-catalogue schema are deleted.

---

## §P.8 Main cross-task risks

1. **main moves fast.** main went from contracts 3.5.0 to 3.12.0 in two days. The shared files `contracts/validate.py`, `dependencies.py`, `design.py`, `evaluate_design.py`, `ext_computational_run.json` conflict easily; each stage rechecks the cited main line numbers on the latest `main` when it starts, and rebases and reruns the checks before merging.
2. **The F4 qualification path is not approved.** If D0 is not approved, the Geant4 results of B3 and C2 stay `unvalidated` and cannot become F4; B1 and B2 keep their value (infrastructure and the end-to-end path).
3. **How far the tail sources are modelled.** An F4 resolution or charge confusion is an `estimate` only when all four tail sources are simulated; B2's misalignment, digitization and noise, hit association and field miscalibration are simplified models, and the meaning of the result is limited to what the study record declares.
4. **Maintenance cost of two Geant4 programs** (`layered_sim` frozen, `element_sim` new). Duplication is controlled by `g4sim`; in the long run `layered_sim` can be retired once `element_sim` produces all of J14's observables (deferred).
5. **Actual behaviour of the statistics**: the O(1/B) bias of block batch means for skewed distributions, the shortfall rate of the two-stage design (about 19 % per pair of points), and possibly small variance reduction from paired comparison. All are measured with toys and trials, not assumed.
6. **Geant4 behaviour not checked line by line**: stepper construction, the Birks API, the direction of the field-intersection error, the nucleon cross sections of the two physics lists, the capabilities of `G4RootAnalysisReader`, the name of the function that stores the random status. Each is checked first in the stage that first uses it.
7. **Compute**: J14 re-recording (A1), calorimeter showers and one F4 study per (figure of merit, denominator) (B3), Geant4 search (C2). Each stage writes its budget after its trial.
8. **CI cost**: main's `contracts/rules/registry.json` has no impact groups for `adapters/geant4/**`, `core/stats/**` and the like, so these changes trigger full CI (§P.7 item 15).
9. **Entry budget**: hep-detector quick load has only 931 bytes left, the description 1,016 / 1,024 characters. This program does not change `SKILL.md`.
10. **Incomplete effort estimates**: only the contract part of A1 has a prototype estimate (about 8–12 working days); the rest are estimated and recorded at the start of each stage.
11. **References**: GRACE and VI-BRATO cited in task C are 2026 preprints; the AIDO and Cisbani numbers are to be verified; every source is checked through hep-citations before it is cited formally.

---

## §P.9 Document map and authority

| Document | Content | Authority |
|---|---|---|
| Part 1 (this part) | Evaluation, principles, stages, interface ownership, naming, gates, open decisions, risks, execution environment | Order, numbering, version placeholders, ownership, gates, open decisions, execution environment (isolated worktree) |
| Part 2 (task A) | Work items and acceptance of A1, A2 | Content and acceptance of these two stages |
| Part 3 (task B) | J15 design; work items and acceptance of B1, B2, B3 | Content and acceptance of these three stages; J15's numbers |
| Part 4 (task C) | Design of automated candidate generation; work items and acceptance of C1, C2, C3 | Content and acceptance of these three stages |
| Part 5 (design rationale) | Design rationale, reference experiments, relation to main's design loop, superseded designs | Rationale; where it conflicts with the specs, the specs win and the conflict is reported |
| `review-2026-10-24-main-0.38.md` | Review record against main 0.38.0 (findings and recommendations) | The basis of the re-plan; this document has been revised accordingly |
| `README.md` | Folder entry, points to this document | — |
| `gate_operating_characteristics.py`, `j15_design_estimates.py`, `design_search_closure.py` | Programs computing design numbers | The numbers of the corresponding appendices |

Parts 2–4 share one structure: §X.0 task card, §X.1 terms and files, §X.2 prerequisites and provided interfaces, §X.3 hard rules, §X.4 design summary, from §X.5 the work items and acceptance of each stage, then contracts and versions, checks, not done and deferred, open decisions and risks, order of work, appendices (X is A, B or C).

---

## §P.10 Execution environment: isolated worktree

### §P.10.1 Principles

- **Every stage runs in its own isolated git worktree**: one stage, one worktree, one branch.
- Files in the main checkout (the working tree at the repo root) and in other worktrees are never changed.
- Reasons:
  - stages that can run in parallel (e.g. C1 with A and B) and parallel agents do not overwrite each other;
  - build directories, Geant4 output and scratch files are isolated from each other;
  - a failed stage can be thrown away as a whole without affecting other work;
  - each stage's change is one branch's diff, so the scope of review and merge is clear.

### §P.10.2 Creating and confirming

| Item | Rule |
|---|---|
| Location | `.claude/worktrees/geant4-<stage>`, stage name in lower case, e.g. `.claude/worktrees/geant4-a1` |
| Branch | `worktree-geant4-<stage>`, e.g. `worktree-geant4-a1` (the naming rule of `EnterWorktree`) |
| Base | The latest `main` that contains all prerequisite stages (the "Prerequisite" column of §P.0); e.g. B2 is based on `main` after B1 merged; C1 on the latest `main` at the time |
| Source of the spec | Once approved, this folder is merged into `main` and the worktree contains the spec. Before approval, the spec exists only on branch `worktree-geant4-architecture`; read it with `git show worktree-geant4-architecture:plugins/hep-research/docs/dev/geant4-architecture/<file>`, without merging that branch into the stage branch |
| In Claude Code | The session itself creates and enters the worktree with `EnterWorktree` (name `geant4-<stage>`): location `.claude/worktrees/geant4-<stage>`, branch `worktree-geant4-<stage>`, base `origin/main`; when implementation work is delegated to a subagent, the Agent tool uses `isolation: "worktree"` |
| In other environments | `git fetch origin && git worktree add .claude/worktrees/geant4-a1 -b worktree-geant4-a1 origin/main`; in Claude Code this existing worktree can then be entered with `EnterWorktree`'s `path` |
| Check before starting | `git rev-parse --show-toplevel` is the worktree's path, `git branch --show-current` is the stage's branch, `git status` is clean; every prerequisite stage's merge commit satisfies `git merge-base --is-ancestor <merge commit> HEAD`; the main line numbers cited in this document are rechecked on the new base; these results go into the stage's work record (the environment field of the VALIDATION entry) |

### §P.10.3 Rules inside the worktree

1. All editing, building, testing, Geant4 runs and spec corrections happen in the stage's worktree; never `cd` into the main checkout or another worktree.
2. Commands use clear absolute paths or paths relative to the worktree; avoid building git arguments from variables computed at run time, so that tools and reviewers can confirm the command stays inside the worktree.
3. **`git stash` is shared by all worktrees.** Never use bare `git stash` or `git stash pop`; to set work aside, use a temporary WIP commit.
4. Build directories, E2 output, ROOT files and trial results go in uncommitted directories inside the worktree (e.g. `build/`, `work/`, excluded by `.gitignore`) or in a scratch directory dedicated to that worktree; worktrees do not share build directories. The Geant4 installation itself (E2) may be shared read-only by several worktrees.
5. Commit only on the stage's branch; commits carry the required trailers; push to the remote branch of the same name. Without the maintainer's approval, do not push to `main` or open a pull request.
6. Before merging, run the checks of §A.8 in the worktree and confirm the gates (§P.6).
7. When the spec needs a correction: before the maintainer approves the spec, change it in the documentation worktree (`.claude/worktrees/geant4-architecture`, branch `worktree-geant4-architecture`); after implementation has started, change it in the stage's worktree. In both cases change the Chinese and English versions together and record it in the version history; when other stages are affected, update this part at the same time.
8. Isolation for independent review follows Appendix A7 of `docs/dev/independent-review-spec.md` (host settings: `CLAUDE_CODE_FORK_SUBAGENT=0` or `Agent(fork)` in `permissions.deny`, and a named non-fork subagent type); worktrees are for implementation only. Reviews only read, never write.

### §P.10.4 Stages that can run in parallel

| Together | Condition | Note |
|---|---|---|
| C1 with A1, A2, B1, B2 | none (C1 depends only on main) | C1 touches `skills/hep-detector/scripts/evaluate_design.py`, `contracts/design.py`, `contracts/schemas/ext_computational_run.json`, `skills/hep-detector/references/system-design-workflow.md`; A1 also touches `evaluate_design.py`, B2 also touches `design.py` and `evaluate_design.py`; whichever merges later rebases on the new `main` and reruns the checks |
| B3 with C2 | B2 and C1 merged, and G-D0 passed (for B3 and C2's confirmation) | Both may change `geant4-study-protocol.md`, `system-design-workflow.md` and the journey docs; whichever merges later rebases and reruns the checks |

Each parallel stage uses its own worktree and branch; a single stage is never implemented by two agents in different worktrees at the same time.

### §P.10.5 Finishing

- **After merging:** `git worktree remove .claude/worktrees/geant4-<stage>` and delete the local branch; the next stage creates a new worktree from the new `main`.
- **Abandoning:** remove the worktree and the branch; do no cleanup in the main checkout.
- **This folder itself** is written on branch `worktree-geant4-architecture` in worktree `.claude/worktrees/geant4-architecture`; later documentation changes also happen there until it is merged into `main`.

---

## §P.11 Version history

| Version | Content |
|---|---|
| 2026-10-23 | First version: consolidated evaluation, planning principles, eight stages (B split into B1–B3, C into C1–C3), interface ownership, naming (contract versions written CV1–CV3), gates, consolidated open decisions and risks |
| 2026-10-23 | Added §P.10 "Execution environment: isolated worktree" (creating, confirming, rules, parallel stages, finishing) and the reading guide for agents |
| **2026-10-24 (this version)** | **Re-planned against the detector system design loop of main 0.38.0 (review record `review-2026-10-24-main-0.38.md`): baseline `5584927`; main's fidelities F0–F5 adopted; B becomes the F4 evaluator (`from-geometry`, tail sources, `results` fields, qualification path D0); J15 becomes a design project; C becomes the candidate generator `evaluate_design.py search` and no longer depends on A; contract placeholders become CV-A1, CV-B2, CV-C1, CV-C2; G-D0 and G-B2 added; open decisions renumbered and those main already decided marked** |

---

# Part 2 — Task A: correctness fixes and boundary artifacts (§A)

> Order: A1 → A2; then task B (Part 3). Task C's C1 does not depend on task A (§P.0)
> Baseline: hep-research `main` at `5584927` (0.38.0), contracts 3.12.0, adapter geant4 0.1.0 (unchanged since `9f08796`), Geant4 11.4.3; first written against `9f08796` (0.23.0)
> Date: 2026-10-24

---

## §A.0 Task card

**Goal.** Fix the defects (D1–D8, D10, D11) that let a simulation study be wrongly labelled `validated-in-scope`, and make the study layer know a simulation backend only through three boundary artifacts (run summary, column map, effective config) (D9). From main 0.37.0 the detector design loop counts only `validated-in-scope` studies as F4 (`contracts/design.py` line 1004), so these defects also affect design evaluations; A1 also lets `evaluate_design.py f4` hand a study to `label --upgrade` and report the outcome faithfully (A1.17). Statistics and summary reading live in `core/` from the start, so task B and task C (`evaluate_design.py search`) can use them directly.

**Two stages (in order, each merged separately):**

| Stage | Content | Version | Language |
|---|---|---|---|
| **A1** Correctness fixes | Contracts (benchmark table, scope, configuration and isolation, evidence roles, completeness of the convergence scan); `core/stats/` (block batch means, exact intervals, MPV, quantiles, the decision engine's `equivalence` and `detection_limit`, distribution functions); `core/simulation/` (seed hash, reading and merging of summaries); schemas of summaries and observables (`contracts/schemas/`); Python summary producer; J14 regenerated; F4-consumer compatibility (`evaluate_design.py f4`) | contracts **CV-A1** (minor, sci-fix); `CORE_VERSION` minor | Python |
| **A2** Shared headers and boundary artifacts | `g4sim` (`SimHash`, `SimSeed`, `SimSummary`, `MiniJson`, `SimProbe`); `per-event` seeding; `layered_sim` writes the three boundary artifacts; name-free `tree-v1`; effective configs stored by content hash; the study layer reads only boundary artifacts | geant4 adapter **0.2.0**; contracts unchanged | C++ and Python |

**Out of scope:**
- `element_sim`, fields, plane crossings, ROOT files, `simroot`, `simreco`, J15 (task B); the decision engine's `change` (B2).
- Paired comparisons, search and confirmation roles, seed_group, the `values` accumulator (task C's C2; §P.2 R1). Requirement verdicts, ranking and Pareto fronts are derived by main's `contracts/design.py`, not in `core/stats/decisions.py`.
- The study record's `results.<figure of merit>`, `tail_sources_simulated` and geometry file (B2).
- The `layered_sim` spec format (spec/1) is not restructured; only optional fields are added.

**Deliverables:** code and tests; regenerated J14 records; sci-fix ledger entries (one per fix) and two advisories (format `/2`); VALIDATION entries GEANT4-CORRECTNESS (A1) and GEANT4-SUMMARY (A2); CHANGELOG; release manifest.

**Definition of done:** every box in the acceptance lists A1.15 and A2.10 is ticked; every check in §A.8 passes; gates G-A1 and G-A2 (§P.6) pass.

**Main decisions:**
1. **A1 is a minimal sci-fix.** It contains only the changes needed to fix D1–D8, D10 and D11 and to make the F4 consumer report faithfully, and their direct foundation; decisions and fields needed only by tasks B and C are added by those tasks (§P.2 R1, R4).
2. **Shared code lives in `core/`.** Adapters can import only `core` and `contracts`; statistics, decisions, the seed hash and summary reading are in `core/` from day one, and hep-detector's scripts are only callers. `core/` may import only `core`, so schema validation runs in the callers through `contracts.schema`; the existing Garwood interval, toy seeds and coverage gate are reused (§A.4.5).
3. **Reproducibility = same decisions.** No bit-identical statistics (§A.4.3).
4. **`layered_sim` is frozen.** A2 only adds optional fields and files; new geometry features go into task B's `element_sim`.
5. **Plug into main's design loop.** A1 does not write F4 result fields (B2's work), but fixes the F4 consumer so that the outcome of a study's upgrade is reported faithfully (A1.17).

**First step:** create the isolated worktree for this stage per §P.10.2 (`.claude/worktrees/geant4-<stage>`, branch `worktree-geant4-<stage>`, based on the latest `origin/main` that contains the prerequisite stages), and confirm `git rev-parse --show-toplevel`, `git branch --show-current` and `git status`. Every following step happens in this worktree.

**Before starting:**
1. Check whether `main` has moved past `5584927` (0.38.0; the checks were redone against it on 2026-10-24, see §A Appendix C and the review record `review-2026-10-24-main-0.38.md`). If so, read the new CHANGELOG, redo the checks of §A Appendix C, and update this part (both languages).
2. Read §P.0–§P.6; read §R.0 and §R.2; read the sci-fix process (evidence grades and ledger around lines 126–251, advisories around lines 252–294), the adapter-change process and the release steps in `docs/maintenance.md`; read D3 (the F4 row) of `skills/hep-detector/references/system-design-workflow.md`.
3. Start A1 from `prototype/phase1-core.patch`. It changes only `contracts/validate.py`, `check_geant4_study.py`, `geant4_benchmarks.py`, the study-spec schema and two test files, nothing in `core/`: the benchmark table (grades and kinds, no validation classes), the scope comparison with kinds (`scope_outside()`; dimensions hard-coded as particle, material, energy, thickness, with an exception for `longitudinal-profile`), configuration and target hash in the benchmark output (derived from the run record's `extension.simulation.geometry`, not from spec/1; no target for `longitudinal-profile`), and the enum fix of A1.12. It predates this spec: it lacks `target_slabs`, `setup-matched`, per-benchmark scope dimensions, `hash_scheme`, the `dependencies.py` re-derivation and CV-A1 gating; it gates at a hard-coded 3.6.0 (which would apply the new rules retroactively to 3.6.0–3.12.x records and must be replaced by the CV-A1 constant); it writes `longitudinal-profile` as `("reference", ("shower-shape",))`. It still applies to `5584927` (dry run; `contracts/validate.py` offset by 2 lines).

---

## §A.1 Terms and files

| Term | Meaning |
|---|---|
| J14 | The existing journey `examples/geant4-thin-silicon/`: a thin-silicon study, the only Geant4 example with `validated-in-scope` records |
| study record | A computational-run record carrying `extension.study`; its `label` sets the artifact label |
| `validated-in-scope` | The label allowed only after validation by an upgrading benchmark with the declared scope inside the benchmark's scope; enforced by `_study_upgrade` in `contracts/validate.py` |
| validation class | The nature of a benchmark's reference (§A.4.4); A1 defines reference, setup-matched, sanity, interface; B2 adds verification and regression, and adds a tracking benchmark to the reference class (§B) |
| observable kind | The controlled kind of observable (enum) in the study spec, e.g. `most-probable-value` |
| configuration | How the target is placed: `isolated` or `embedded` (A1.3) |
| logical run | N events, numbered 0 … N−1, fixed by the spec, the backend and the logical-run seed S; may be split into several jobs |
| block | One of K segments of a logical run by event number, each with B events (N = K·B); the unit of batch means |
| three boundary artifacts | run summary (`simulation-summary/1`), column map (`simulation-columns/1`), effective config (engine-independent envelope plus the actual geometry tree) |
| `seeding` | `stream` (existing behaviour) or `per-event` (each event reseeds with H(S, event number); from A2) |
| `hash_scheme` | How the target hash is derived: `spec-v1` (A1, from spec/1) or `tree-v1` (from A2, from the geometry tree) |
| evidence role | What a run is for in a study, stored in `extension.simulation.evidence_role` (not `role`: `label` already writes `evidence_records[].role = "Geant4 run"`); A1 defines trial, nominal, scan, control, variation, calibration; B2 adds regression; C2 adds search and confirmation |
| decision engine | `core/stats/decisions.py`; A1 provides `equivalence` and `detection_limit`, B2 adds `change`, C2 adds the paired mode; it decides only study-layer gates, requirement verdicts are derived by `contracts/design.py` |
| CV-A1, CV-B2, CV-C1, CV-C2 | Contracts minors named by their owning stage, numbers fixed at release in merge order, all ≥ 3.13.0 (§P.5); CV-A1 belongs to A1 |
| F4 | The fidelity of main's design loop: a Geant4 study re-issued `validated-in-scope` by `check_geant4_study.py label --upgrade` (D3 of `system-design-workflow.md`) |
| E2 | An environment with a Geant4 11.4.3 build |
| IUT | intersection-union test: passes only if every observable is equivalent |
| DL | detection limit of a negative control |
| sci-fix | The process in `docs/maintenance.md` for fixing scientific-correctness defects |
| Notation | "A1.6", "B1.3", "C2.1" are work items (unique across the document); "§A.7", "§P.4", "§R.6" are sections of this document's parts (§P Part 1, §A this part, §B Part 3, §C Part 4, §R Part 5) |

**Main files (relative to `plugins/hep-research/`):**

| Purpose | Path |
|---|---|
| Contracts | `contracts/validate.py`, `contracts/dependencies.py`, `contracts/schema.py`, `contracts/schemas/ext_computational_run.json`, `contracts/schemas/` (new schemas of summaries and observables), `contracts/design.py` (`check_f4` lines 988–1062, read only) |
| Shared modules (new) | `core/stats/distributions.py`, `core/stats/batch_means.py`, `core/stats/decisions.py` (steward hep-statistics); `core/simulation/seeds.py`, `core/simulation/summary.py` (steward hep-detector) |
| Existing core | `core/status.py`, `core/trace.py`, `core/OWNERS.json`, `core/stats/tail_estimation.py` (`beta_ppf`, `clopper_pearson`), `core/partition/engine.py` (`NON_ADDITIVE_TOKENS` line 381), `core/stats/poisson_diagnostics.py` (`central_interval`, Garwood, line 162), `core/stats/toy_ensemble.py` (`toy_seed` line 60, `coverage` line 160, `coverage_gate` line 189), `core/__init__.py` (`CORE_VERSION`) |
| Study layer | `skills/hep-detector/scripts/check_geant4_study.py` (`convergence()` line 335, relative difference line 357, decision line 359, `scope_within()` line 482), `geant4_benchmarks.py` (`GRADES` lines 92–94, `bootstrap()` line 197, `mpv()` line 204, detection limit line 275, bootstrap SE of the MPV line 369, `at_limit` line 678), `tracker_resolution.py`, `multiple_scattering.py`; `skills/hep-detector/assets/geant4-study-spec.schema.json`; `skills/hep-detector/references/geant4-study-protocol.md`; `skills/hep-detector/scripts/evaluate_design.py` (`f4` lines 498–560), `skills/hep-detector/references/system-design-workflow.md` |
| Adapter | `adapters/geant4/adapter.json`; `adapters/geant4/assets/geant4_run.py` (`SIM_SOURCES` line 63, `validate_spec()` line 103, `cmd_scan` line 435, `cmd_chunk` line 491, `cmd_summarize` line 525), `geant4_build.py` (`GEANT4_USE_GDML: OFF` line 53), `geant4_verify.py`, `g4common.py` (the existing Python module); `adapters/geant4/assets/layered_sim/` (`Actions.cc`: CSV format `%.10g` line 23, deposit multiplied by track weight line 113; `layered_sim.cc`: seeds and run manager lines 149–154; `MiniJson.hh`, `spec.schema.json`, `output.schema.json`) |
| J14 | `examples/geant4-thin-silicon/run.py`, `recorded/` (`events/` with 5 reduced CSVs, `runs/`, `summaries/`, `specs/`), `output/` |
| Tests | `tests/contracts/test_geant4_upgrade.py`, `test_simulated_dataset.py`, `test_schema_keywords.py`; `tests/adapters/test_geant4.py`; `tests/examples/test_geant4_thin_silicon.py`; `tests/skills/test_cli_robustness.py`; `tests/skills/hep_detector/test_design_m2.py` (`F4Path` line 336); `tests/tools/test_scifix_ledger.py`, `test_scifix_advisories.py`, `test_scifix_schemas.py` |
| Tools | `tools/run_all_checks.py`, `check_layering.py`, `check_relocation.py`, `check_ownership.py`, `check_packaging.py`, `measure_entrypoints.py`, `reference_inventory.py`, `capability_map.py`, `check_routing_static.py`, `scifix_advisories.py`, `scifix_ledger.py`, `check_wiring.py`, `ci_plan.py`, `run_required_backends.py` |
| Sci-fix records | `docs/evidence/sci-fixes.json` (`fixes`, `documentation_fixes`, `superseded`), `docs/evidence/advisories/`, `docs/evidence/schemas/`, `scifix-sources.json`, `scifix-claims.json` |

---

## §A.2 Prerequisites and provided interfaces

**Prerequisites:** none (task A comes first).

**Interfaces provided to tasks B and C** (ownership in §P.4):

| Interface | Work item | Users |
|---|---|---|
| Benchmark table, validation classes, scope comparison, isolation rule (entries can be added) | A1.1–A1.3 | B2, B3, C2 |
| Evidence roles (roles can be added) | A1.4 | B2, C2 |
| Seed hash H (Python `core/simulation/seeds.py`; C++ `g4sim/SimHash.hh`) | A1.4, A2.1 | All simulation programs, `evaluate_design.py search` (C2) |
| Schemas (`contracts/schemas/`) and reading of `simulation-summary/1` and `simulation-observables/1` (fields can be added) | A1.5 | B1, B2, C2 |
| Definition of `statistical_uncertainty` (the 68.27 % t half-width) | A1.6 | B2 |
| Block estimators, exact intervals, MPV, quantiles | A1.6, A1.7 | B3, C2 |
| Decision engine `equivalence`, `detection_limit` (decisions can be added) | A1.8, A1.10 | B2, B3, C2 |
| Two-stage event count | A1.9 | B3, C2 |
| `evaluate_design.py f4` passes the run records on to `label` and reports faithfully | A1.17 | B2, B3, C2 |
| `g4sim` headers, `per-event` seeding, probe, `tree-v1`, column map, effective-config storage | A2.1–A2.5 | B1, B2, C2 |
| Schema keywords `maxItems`, `maximum`, `exclusiveMaximum` | A2.7 | B1, C1 |

Additions can only be optional fields, new enum values or new functions; they may not change existing behaviour (§P.2 R2).

---

## §A.3 Hard rules

Breaking any of these blocks the merge.

1. **Layering.** Skill scripts and adapters import only `core` and `contracts`. Code needed by both hep-detector's scripts and any adapter (statistics, decisions, seed hash, summary reading) goes in `core/`, with a steward named in `core/OWNERS.json`; `core/` never references `skills/`, `adapters/` or `profiles/` paths. `core/` itself may import only `core` (`check_layering.py` lines 4–5), so it cannot use `contracts/schema.py`: schema validation runs in the callers (A1.5). New core files and modules are registered under the admission rule of `core/OWNERS.json` (more than one top-level consumer).
2. **Experiment names.** No experiment names (ALICE included) in `skills/`, `contracts/` or `core/` (`check_layering.py`); use citation keys where needed.
3. **Python uses only the standard library**, a deliberate choice rather than a constraint (core's mandatory environment already includes numpy and scipy, see `requirements-core.txt`): it keeps the adapter scripts and J14's replay free of scientific packages; scipy serves only as a third-party oracle in tests. No Python bindings. t and F quantiles (non-integer degrees of freedom) are implemented on the existing `beta_ppf` in `core/stats/distributions.py` (shared numerical functions, not the "new core validators" of §A.9); the Garwood interval reuses the existing `central_interval` of `core/stats/poisson_diagnostics.py` (line 162) instead of a second copy.
4. **C++ dependencies.** `SimHash.hh`, `SimSummary.hh` and `MiniJson.hh` of `g4sim` use only the C++17 standard library; `SimSeed.hh`, `SimProbe.hh` and `layered_sim` link Geant4. No third-party libraries.
5. **G5 licence boundary.** Python exchanges only JSON and CSV with separate executables; code is written from the Geant4 API, without copying or adapting Geant4 example code.
6. **Status and exit codes** (`core/status.py`): 0 ok, 1 negative verdict (`refused`/`failed`), 2 unusable input (`rejected`), 3 `incomplete`. Unresolved and target-missed are always 3.
7. **Execution trace.** New record writers call `trace.provenance()`; new shared functions call `trace.tag()`; calls to C++ executables record the sha256 of the executable and its sources, the version and the subcommand.
8. **Size and paths.** Each file ≤ 2 MiB (`check_packaging.py` scans all text files); written paths go through `tilde()`; size claims in the plugin README must be within 10 % of the actual value.
9. **Entry budget.** hep-detector quick load ≤ 25,600 bytes (now 24,669), description ≤ 1,024 characters (`measure_entrypoints.py` reports 1,016). This task does not change `skills/hep-detector/SKILL.md` or the description.
10. **Process.** A1 follows the sci-fix process; A2 the adapter-change process; both follow the release steps. Each stage works in its own isolated worktree and branch (`worktree-geant4-a1`, `worktree-geant4-a2`) (§P.10); each A1 fix is committed separately as a `sci-fix:` commit (`robust-fix:` for S4), so that the ledger's `commits` and parent records can point to it (A1.14); do not push to `main` or open a pull request without the maintainer's approval.
11. **Contract versions.** New rules are gated with `strict or _at_least(contract_version, CV-A1)`, with no warning branch.
12. **The offline replay of J14** always runs, without Geant4 or a compiler.
13. **No change to existing outputs.** A2 only adds files and optional fields; J14's existing specs must produce a CSV bit-identical to the pre-A2 one (same host).
14. **Not done:** integer quantization, 128-bit integers, bit-identical statistics, spec-format conversion, `simstat`, a `simcore` not linked to Geant4 (reasons in §R.13).

---

## §A.4 Design summary

### §A.4.1 Confirmed defects (found at `9f08796`, still present at `5584927`)

| # | Defect | Location | Consequence | Work item |
|---|---|---|---|---|
| D1 | Scope check does not compare the observable; dimensions missing from the declaration are unconstrained | `validate.py` `_scope_inside()` (from line 351); `check_geant4_study.py` `scope_within()` (lines 482–493) | A study that passed an MPV benchmark can label other observables `validated-in-scope` | A1.2 |
| D2 | A benchmark's grade is declared by the record itself | `_study_upgrade` (line 397; filter line 421) | Writing `"grade": "reference"` is enough to upgrade | A1.1 |
| D3 | Negative control compared across units, tested in one direction only | `geant4_benchmarks.py` line 678 | Detection limit not demonstrated on the observable | A1.10 |
| D4 | Convergence gate has no equivalence test | `check_geant4_study.py` line 359 | Passes about 50 % of the time when the true difference equals the tolerance | A1.8 |
| D5 | MPV SE from bootstrap | `geant4_benchmarks.py` line 369 | Inconsistent variance estimate; J14's detection limit is built on it | A1.6, A1.7 |
| D6 | Stopping rule does not forbid adding events based on results | protocol section 4 | Optional-stopping bias | A1.11 |
| D7 | Evidence correlation not disclosed | J14's nominal run shared by gate, statistics target, benchmark and variation | Treated as independent evidence | A1.11 |
| D8 | Study-spec benchmark enum lacks `shower-containment` and `longitudinal-profile` | `geant4-study-spec.schema.json`; `GRADES` has 9, the enum 7 | Consistency gap | A1.12 |
| D9 | Study layer bound to `layered_sim`'s data format | `derived()` reads `geometry.layers`; `summarize` and benchmarks read fixed column names | Other backends cannot enter | A2.6 |
| D10 | Test-order dependence | `tearDownModule` of `test_geant4_upgrade` deletes the shared J14 replay directory; 5 tests of `test_simulated_dataset` error | Errors depend on execution order | A1.12 |
| D11 | The convergence gate takes the two finest values only among the supplied summaries; when the finest scan point is missing it passes on coarser ones | `check_geant4_study.py` `convergence()` lines 341–348; protocol lines 93–95 document it and ask the user to supply every run | A cut that is too coarse can pass the only check that catches it | A1.16 |

### §A.4.2 Two planes

Per-event processing is in C++ (the simulation programs; from A2 also the summary accumulation); inference after merging, decisions, records and contracts are in Python. Each quantity has one production implementation; an implementation in the other language may exist only in tests as an oracle. In A1 the summary is produced by Python from the per-event CSV; from A2 it is produced by `layered_sim`, and the Python producer stays only in tests.

### §A.4.3 What reproducibility means

| Level | Requirement |
|---|---|
| Traceability | Every record keeps the spec, effective config, code (`sources_sha256`), seeds, and hashes of input and output files |
| Re-execution | Same build and platform, same logical run: identical event content; summary integer accumulators identical, floating-point relative difference ≤ 1e-12 |
| Replay (from committed summaries and records) | Decisions and labels identical; numbers within relative 1e-9; decisions with a margin < 1e-9 (relative) flagged "near threshold" in the record |
| Regression check (A2) | J14's existing specs (`seeding: stream`) produce a CSV bit-identical to the pre-A2 one on the same host |

### §A.4.4 Validation classes

| Class | Reference | Upgrades | Introduced |
|---|---|---|---|
| reference | The physics model Geant4 approximates, or thin-target measurements, on an isolated target | Yes (in scope) | A1 (CV-A1) |
| setup-matched | A published measurement, target hash equal to the measured configuration, and isolated | Yes (in scope) | A1 (CV-A1) |
| sanity, interface | Plausible range, interface checks | No | existing |
| verification | Exact consequence of the inputs (analytic helix, kinematics) | No | B2 (CV-B2) |
| regression | The same study at a previous version | No | B2 (CV-B2) |

B2 also adds a tracking benchmark to the reference class (the multiple-scattering angular width in an isolated Si slab), as part of the qualification path by which detector-level studies become F4 (D0 in §P.7, §B). The previously planned surrogate class is deleted: main's fidelity and bound model already covers fast simulations.

### §A.4.5 Shared modules in `core/`

| Module | A1 content | Added later |
|---|---|---|
| `core/stats/distributions.py` | `t_ppf`, `f_ppf` (non-integer degrees of freedom); Garwood is not here, `poisson_diagnostics.central_interval` is reused | — |
| `core/stats/batch_means.py` | Block estimators, SE, covariances, exact intervals, histogram quantiles, MPV | C2: empirical quantiles from `values` |
| `core/stats/decisions.py` | `equivalence` (IUT gate), `detection_limit`; returns `{verdict, margin, reason}` with `reason` from a closed list | B2: `change`; C2: paired mode (decides only study-layer gates and search values; requirement verdicts are in `contracts/design.py`) |
| `core/simulation/seeds.py` | Seed hash H, logical-run seed, job seeds; the docs state how H differs from the existing `toy_ensemble.toy_seed` (H's range [1, 2³¹ − 1] is what the Geant4 engine accepts as a seed, `toy_seed` is 63-bit; both are derived from SHA-256 and independent of the split) | — |
| `core/simulation/summary.py` | Reading, merging by block, and accumulator access of `simulation-summary/1`; no schema validation (the schemas are in `contracts/schemas/`, validated by the callers with `contracts.schema.validate`) | C2: the `values` field |

hep-detector's `check_geant4_study.py` and `geant4_benchmarks.py` call these modules; later tasks call the same implementation.

`core/OWNERS.json`: the `files` of the `stats` module gain `distributions`, `batch_means`, `decisions` (the module already has several consumers); a new `simulation` module (steward hep-detector; consumers `skills/hep-detector/scripts/check_geant4_study.py` and `adapters/geant4/assets/geant4_run.py`, `summary_from_csv.py`, meeting the admission rule). `CORE_VERSION` gets a minor bump in A1 (1.0.0 → 1.1.0; Versioning in `docs/maintenance.md`). The coverage toys of A1.15 run through `run`, `coverage` and `coverage_gate` of `toy_ensemble`.

---

## §A.5 Stage A1: correctness fixes (contracts CV-A1, sci-fix)

A1 changes only Python. Statistics are computed from summaries that Python produces from the per-event CSV; from A2 they read the summary written by `layered_sim`.

### A1.1 Benchmark table (D2)

**Change:** `contracts/validate.py` (new constant table; `_study_upgrade` takes class, kind and scope dimensions only from the table); `geant4_benchmarks.py` (`GRADES` kept for the tool, its values changed to the table's class, plus a consistency test).

**Grade is class.** The table's second column is also the value the record's `grade` field must have.

| benchmark | Class | Supported kind | Scope dimensions (type) |
|---|---|---|---|
| `stopping-power` | reference | `stopping-power` | particle (categorical), material (categorical), energy (interval), thickness (interval) |
| `range` | reference | `range` | same |
| `thin-layer-mpv` | reference | `most-probable-value` | same |
| `thin-layer-width` | sanity | `thin-layer-width` | same |
| `multiple-scattering` | sanity | — | — |
| `em-shower-shape` | sanity | — | — |
| `shower-containment` | sanity | — | — |
| `longitudinal-profile` | setup-matched | `shower-maximum` (new kind, t_max only) | particle (categorical), energy (interval), target hash |
| `published-data` | interface | — | — |

**Rules:**
- A class or grade in the record that differs from the table, or a benchmark name not in the table: error. Applies to every record with a Geant4 study block.
- Only reference and setup-matched are counted by `_study_upgrade`.
- Supported kinds and scope dimensions come only from the table; values output by the tool are for reading only.
- The table's 9 names equal the current `GRADES`; the values of `GRADES` become the table's class, the only change being `longitudinal-profile`: reference → setup-matched (lines 92–94). The study spec's grade enum gains `setup-matched` (A1.12).
- Entries can be added to the table in later contract versions (B2: verification, regression and the tracking reference benchmark).
- J14's decisions are unchanged, but the content of study and benchmark files changes (new fields; `code_paths` gains `contracts/validate.py`).

### A1.2 Scope check (D1)

**Change:** `contracts/validate.py` (the single implementation, exported); `check_geant4_study.py` (imports it, deletes `scope_within()`; `label` writes `declared_scope.observable_kind`); study-spec schema (`validation_plan.scope` is `additionalProperties: false`; add `observable_kind`, `target_geometry_sha256`, `hash_scheme`).

**Rules:**
- Compare the controlled `observable.kind`, not free text.
- The declared kind must be among the kinds supported by the counted benchmarks.
- The dimension list is per benchmark (fourth column of A1.1); categorical dimensions compare by set inclusion, interval dimensions by interval inclusion; a scalar is treated as [v, v].
- Every dimension the benchmark has must be in the declared scope; a missing one counts as out of scope.
- When the target hash is a dimension, the declared scope must carry the same `target_geometry_sha256` and `hash_scheme`.
- Gating: `strict or _at_least(contract_version, CV-A1)`; records below CV-A1 (today ≤ 3.12.x; J14's study records are already written at 3.12.0) are constrained only under `--strict`, and only records with `validated-in-scope` fail.

### A1.3 Configuration and isolation

**Change:** `geant4_benchmarks.py` (output); `contracts/validate.py` (rule); `contracts/dependencies.py` (re-derivation).

- `geant4_benchmarks.py` outputs, for each benchmark result, `configuration`, `target_geometry_sha256`, `hash_scheme: spec-v1` and `configuration_basis`, derived from the spec/1 of the run record named by the benchmark setting's `run_record`, never from user input. A benchmark counted for upgrade must have a `run_record`.
- **Target:** the benchmark setting declares `target_slabs` (the names of the slabs in the target, absorbers included). A single-layer benchmark defaults to the measured slab; `longitudinal-profile` must list the whole sampling stack (its `layers` lists only the readout columns).
- **Vacuum:** the world material is `G4_Galactic`, or density < 1e-20 g/cm³.
- **isolated:** the world is vacuum and every placement other than the world belongs to the target; spec/1 has no field and is treated as field-free (the field rule takes effect in task B: only a field attached inside the target belongs to the target and counts in the hash). Otherwise embedded.
- **`spec-v1` normal form:** the ordered slabs, thicknesses, transverse sizes, material names and declared compositions; repeated placements listed one by one; numbers as Python `float.hex()`; sha256 of the JSON of this list (sorted keys, no whitespace).
- **Contract rule (CV-A1):** a counted reference benchmark must be isolated; a counted setup-matched benchmark must be isolated and its target hash and `hash_scheme` must equal those of the benchmark's measured configuration. Missing or embedded are errors. `dependencies.py` **must** re-derive from the run records in `evidence_records` and compare.
- Residual limits (written into the protocol): J14's recorded CSVs are reduced, so their hashes do not match the run records' `output_hashes`; configuration describes the run record the setting names. The geometry of negative-control runs is not checked separately.

### A1.4 Logical runs, seeds and roles

**Change:** new `core/simulation/seeds.py`; `check_geant4_study.py` and `geant4_run.py` call it.

- **Definition of H** (Python and C++ must agree; the C++ one is in `SimHash.hh` of A2.1): H(x₁, …, x_n) = int.from_bytes(sha256("\x1f".join(str(x) for x in (x₁, …, x_n)).encode("utf-8"))[:8], "big") % (2³¹ − 1) + 1, with values in [1, 2³¹ − 1]; integers are written as decimal strings without leading zeros.
- Each evidence point is one logical run with seed S = H(study_id, role, point_id); the two directions of a control use different point_ids.
- **Storage:** the run record's `extension.simulation` gains `evidence_role`, `point_id`, `logical_run_seed` (S) and `seed_scheme` (`hash-v1` or `legacy`); from A2 the execution spec also carries `run.logical_run_seed` (A2.2).
- New recordings in A1 always use `seeding: stream` (`layered_sim`'s current behaviour); a single job's seed pair is (H(S, 0, 0), H(S, 0, 1)). Do not use `make_manifest`'s `seed × 100003 + k`, `cmd_scan`'s `[s0, s1 + k]` or `cmd_chunk`'s `start + 1`.
- A logical run may be split into several jobs (`geant4_run.py chunk` with a hand-made manifest, each job covering a range of event numbers): the job starting at event e has seed pair (H(S, e, 0), H(S, e, 1)); `cmd_chunk` (`seeds=[max(1, args.seed), args.start + 1]` at line 504) runs with this pair instead and writes the job's seed H(S, e, 0) into the manifest. Seeds within one manifest then differ, and `validate_manifest`'s `partition.duplicate_seed` check needs no change. Under `stream`, different splits give different events, but statistically equivalent ones.
- **Roles:** `extension.simulation.evidence_role` comes from the evidence-role enum (trial, nominal, scan, control, variation, calibration); an unknown role is an error (CV-A1-gated). The field is not called `role`: `evidence_records[].role = "Geant4 run"` written by `label` (`check_geant4_study.py` line 623) means something else. The enum can be extended later (B2's regression, C2's confirmation and search roles).
- **Uniqueness:** S is not repeated across all run records of a study (checked by `check_geant4_study.py`). The 5 J14 runs not re-recorded in A1 (A1.13) have no S: their run records are not rewritten; the study record registers them with their original seed pairs (first seed 1401 or 1402) as `seed_scheme: legacy`, and only their full seed pairs are checked for repetition.

### A1.5 Summary, observable declaration and Python producer

**Change:** new `core/simulation/summary.py` (reading, merging by block, and access to accumulators of `simulation-summary/1`; no schema validation, since `core/` cannot import `contracts`); new schemas of `simulation-summary/1` and `simulation-observables/1` in `contracts/schemas/` (CV-A1; file names fixed at implementation; only keywords `contracts/schema.py` implements, covered by `tests/contracts/test_schema_keywords.py`); new `adapters/geant4/assets/summary_from_csv.py` (or a `summarize-blocks` subcommand of `geant4_run.py`), which writes and merges through `core/simulation/summary.py` and validates the summary it writes with `contracts.schema.validate` (`check_geant4_study.py` validates on reading as well); `summary_from_csv.py` is registered in `MISSING_FILE_ARGS` of `tests/skills/test_cli_robustness.py`.

- **Observable declaration `simulation-observables/1`:** an array, each item `{name, source_column, selection, bins: {lo, hi, width}, thresholds, tolerance_mode, tolerance}`. `selection` is a declarative filter on CSV columns (column name, comparator `==`, `!=`, `<`, `<=`, `>`, `>=`, value; several conditions are ANDed); `thresholds` feed `count_if` (counting events with x > threshold, strictly greater, as for `tail_fraction` in `check_geant4_study.py`); `tolerance_mode` and `tolerance` see A1.8. The study spec (A1.12) and the simulation programs' `output.observables` (A2.3, B1.1) reference it.
- **Input:** per-event CSVs of one or more jobs, the observable declarations, block size B and block count K.
- **Selection:** each observable accumulates only events that satisfy its `selection` (declarations must reproduce the current code's selections: in `check_geant4_study.py` only `mpv_loss_MeV` requires `primary_fate == 1` (line 284), while `mpv_deposit_MeV` and `tail_fraction` use all events (lines 277–282); the benchmarks' `transmitted()` additionally requires `primary_fate == 1` and `primary_end_process == "Transportation"` (`geant4_benchmarks.py` lines 232–236)); `n` is the number of selected events, and the total number of events per block is recorded as well.
- **Blocks:** event i (the `event` column minus the logical run's first event number) belongs to block ⌊i/B⌋; events with i ≥ K·B are ignored and their number noted.
- **Accumulators per block and observable:** integers `n`, per-bin histogram counts (fixed binning; overflow and underflow separate), `count_if[]` (x > threshold); floating point Σx, Σx², `min`, `max` (Neumaier compensated summation).
- **Output fields:** `summary_version`, `run` (logical-run identity and seed, `evidence_role`, event range, `seeding`, B, K, spec hash, producer `python-csv` and version), `observables[]`, a `merge` rule for each accumulator (`sum`, `min`, `max`, `hist`). Multiple jobs merge by block number. The schema allows added optional fields (C2's `values`).
- **Event weights:** if the CSV has a `weight` column it must be all 1, otherwise exit 2 (deposits are already multiplied by the track weight; see `Actions.cc` line 113). Without a `weight` column (J14's 5 reduced CSVs have none), the summary records `weight_column: absent`, justified by the absence of biasing commands in the run record's spec; with biasing commands in the spec, exit 2.
- From A2, `layered_sim` writes summaries with the same schema; this Python producer then stays only in tests as an oracle.

### A1.6 Estimators and SE (D5)

**Change:** new `core/stats/distributions.py` and `core/stats/batch_means.py`; `check_geant4_study.py` and `geant4_benchmarks.py` call them (read only the summary; drop production use of `bootstrap()`, keep it in tests for comparison).

- For each block b compute θ_b; report θ̄ = mean, SE = sd(θ_b)/√K with K − 1 degrees of freedom. K ≥ 16, declared before the first evidence run.
- Several observables: the per-block vector of estimates is kept together, and covariances are estimated from these vectors.
- Full-sample values: means and proportions are also computed from the merged accumulators, and their difference from θ̄ is recorded as a diagnostic.
- Quantiles: linear interpolation within the histogram; bin width divided by the estimate must be below 1/10 of the relative tolerance; landing in the overflow or underflow bin makes it incomplete.
- **Low counts:** when any block of a count estimator is 0, or the merged total is < 100 (threshold can be declared), use exact intervals on the merged accumulators instead: Clopper–Pearson for proportions (the existing `clopper_pearson`), Garwood for counts (the existing `poisson_diagnostics.central_interval`); comparing two runs uses the conditional-binomial interval for the ratio of rates, relative difference = ratio − 1 (exact for Poisson counts; only approximate for proportions, because their denominators are fixed; the protocol notes this). There is then no SE, and the gate decides on interval endpoints (A1.8).
- **Uncertainty for F4:** the `statistical_uncertainty` a study record writes (from B2 in `results.<figure of merit>`) is defined as the 68.27 % t half-width t_{0.84135}(K − 1)·SE (about 1.03·SE at K = 16), so that `contracts/design.py`, which reads a scalar as a Gaussian with coverage 0.6827 (lines 1050–1052), gets the right coverage. The exact low-count branch has no SE and writes an asymmetric interval; making `f4` accept asymmetric or exact uncertainties is a B2 change (CV-B2).
- Assumption: no state between events. The probe (A2) records biasing and similar settings; in A1, J14 satisfies the assumption.

### A1.7 MPV (D5)

**Change:** `core/stats/batch_means.py`.

- In each block's histogram take the maximum bin and interpolate the mode with a three-point parabola through it and its two neighbours; report the mean of the K modes and its SE (A1.6). This replaces the five-point least-squares fit of the current `mpv()`, noted in the S1 ledger entry.
- **Edge cases:** bin origin and width come from the observable declaration's `bins`; ties for the maximum bin take the lowest index; when the maximum bin is the first or last valid bin, or the denominator y₋ − 2y₀ + y₊ = 0, that block's mode is the centre of the maximum bin, counted and recorded; if such blocks exceed K/4 the benchmark is incomplete.
- **At design time:** estimate the bias with toys at the declared B and bin width; the toys' 95 % upper bound must be ≤ tol/10. The toys use a Landau–Vavilov distribution, checked against the histogram shape of one high-statistics Geant4 run.
- **Every execution:** with m the three-point interpolated mode of the merged histogram, |θ̄ − m|/|m| ≤ tol/5 + 2·SE/|m| (tol is the relative tolerance); otherwise that benchmark is incomplete.
- Block MPVs must not go through the partition merge rules (`mpv` is not in `NON_ADDITIVE_TOKENS`); they are computed only from the summary histograms.

### A1.8 Convergence gate and decision engine (D4)

**Change:** new `core/stats/decisions.py` (`equivalence`); `convergence()` and `cmd_run` in `check_geant4_study.py` call it.

- **Decision-engine interface:** every decision has an SE branch and an exact-interval branch for low counts, takes multiplicity m, and returns `{verdict, margin, reason}` with `reason` from a closed list. A1 implements `equivalence(diff, se, ν, tol, m) → pass / fail / unresolved` and `detection_limit` (A1.10); B2 and C2 add further decisions through the same interface.
- **Difference:** keeps the convention of line 357: a is the finest setting and b the second-finest (declared values sorted ascending, a and b the first two; A1.16). The observable declares a `tolerance_mode`: with `relative` (default) diff = (a − b)/b and se_diff = √(se_a² + se_b²)/|b|; with `absolute` diff = a − b and se_diff = √(se_a² + se_b²), and tol is the observable's declared `tolerance` (in the observable's unit; required under `absolute`); under `relative` tol is the study spec's `tolerance_relative`. ν from the Welch formula per pair (30 for equal variances and K = 16). (The first user of `absolute` is B3; because it is only an option of the same function, it is in A1 so that the gate's definition need not change later.)
- **Event-count target:** the se target per point is tol/(4√2) (a relative se under `relative`).
- **Decision:** pass |diff| + t₀.₉₅(ν)·se_diff ≤ tol, **and both points meet their se target**; fail |diff| − t_{1−α/m}(ν)·se_diff > tol (α = 0.05, m the number of (parameter × observable) pairs; a point that missed its se target can still give fail, since a larger se only makes fail harder); otherwise unresolved. Low counts: pass = the 90 % interval lies inside [−tol, tol]; fail = the one-sided 1 − α/m interval lies entirely outside.
- **Reporting:** unresolved and target-missed are reported as `incomplete` (exit 3), and the label stays `unvalidated`; only fail is `failed` (exit 1). Today every non-pass is treated as `failed`; this must change.

**Operating characteristics** (recomputed by `gate_operating_characteristics.py`, 2×10⁶ toys per cell. "se = target": se_diff equal to the target, estimated with ν = 30, TOST part only (without the condition that both points meet the target); "two-stage": each of the two points designed per A1.9, K = K_trial = 16, ν from the Welch formula on the estimated se):

| True difference | Pass (se = target, TOST part only) | Pass (two-stage) | Pass (two-stage, given both points met the target) | Fail m = 1 (se = target) | Fail m = 30 (se = target) | Fail m = 30 (two-stage) |
|---|---|---|---|---|---|---|
| 0 | 0.976 | 0.809 | 0.999 | 0.000 | 0.000 | 0.000 |
| tol/2 | 0.621 | 0.696 | 0.860 | 0.000 | 0.000 | 0.000 |
| tol | 0.050 | 0.044 | 0.054 | 0.050 | 0.002 | 0.002 |
| 2 tol | 0.000 | 0.000 | 0.000 | 0.988 | 0.780 | 0.952 |

- Under the two-stage design about 19 % of point pairs have at least one point that missed its target, which is why the pass rate at a true difference of 0 is only 0.809.
- At a true difference of tol the unconditional pass rate is 0.044 ≤ 0.05; given that both points met the target it is 0.054, slightly above the nominal 0.05 (points that meet the target have a smaller se); the protocol discloses this.
- At a true difference of tol about 90 % are unresolved; the protocol states the expected incomplete rate.

### A1.9 Two-stage event count

- Each evidence point first records a trial run (role trial, K_trial = 16, event count N_trial declared in advance); then N = ceil(N_trial·(SE_trial/target)²·f), rounded up to a multiple of K (so B = N/K is an integer); f = F₀.₉₀(K − 1, K_trial − 1) (≈ 1.97 when both are 16).
- About 10 % of evidence runs miss their target and are incomplete; **no top-up is allowed** (if the maintainer chooses F₀.₉₅ ≈ 2.40, about 5 %, with about 22 % more events; §P.7 item 4).
- Misses are independent per run: about 19 % of the point pairs of a convergence gate are incomplete; a study needing n runs with an se target has all of them meet it with probability about 0.9ⁿ (about 0.53 at n = 6). The protocol states this.
- The 5 J14 runs not re-recorded in A1 have fixed event counts not planned by this design; their se is still compared with the target, and a miss is likewise incomplete.
- With low counts, plan with the trial run's Poisson variance.

### A1.10 Negative controls and detection limit (D3)

**Change:** `geant4_benchmarks.py`; the detection limit is computed by `detection_limit()` in `core/stats/decisions.py`.

- Test quantity: shift = (control − nominal)/reference, SE combined from the two runs.
- **Caught:** the control's benchmark verdict is fail, i.e. |rel_c| > tol (rel_c is the control's deviation from the reference); consistent with the current code, which uses the control's benchmark verdict (`geant4_benchmarks.py` around line 672).
- Detection limit: DL = tol + |rel| + t_{0.977}(ν)·se_rel (replacing `2 * se_rel` at line 275). tol is the benchmark's total tolerance (the total returned by `_tol()`, lines 261–269); rel is the nominal's deviation from the reference; se_rel = √(se_control² + se_nominal²)/|reference|, the combined SE of the shift; ν its Welch degrees of freedom. The toys use the same definitions.
- Design requirement: toys show the probability of catching an injection at DL is ≥ 0.977. With the definition above the true power is near 0.977 (the reviewer's calculation about 0.9785), so the toy acceptance threshold is 0.977 − 3σ_MC (A1.15).
- Inject in both directions; otherwise narrow the claim to one direction, recorded in `scope.detection_limit_sign`. At the detection limit = caught and |shift| ≤ 1.1 × DL.
- A single miss is recorded and explained, not an automatic failure; rerunning with another seed is not allowed.
- J14's existing controls inject only +density; until negative-direction controls are recorded, J14's two claims are narrowed to `detection_limit_sign: "+"`.

### A1.11 Stopping rule, evidence correlation and trace (D6, D7)

- Protocol section 4: the stopping rule, scan grid, K and B, and the handling of unresolved results are written into the study spec before the first evidence run.
- `extension.study.evidence_overlap` lists runs shared by several decisions, with `evidence_overlap_version`.
- Trace tags (lowercase, hyphenated): `geant4-scope-kind`, `geant4-configuration`, `geant4-convergence-iut`, `geant4-batch-means`, `geant4-mpv-block`, `geant4-seed-hash`, `geant4-convergence-complete`. Once `check_geant4_study.py` imports `contracts.validate`, `code_paths` gains `contracts/validate.py`; this change is expected.

### A1.12 Other fixes (D8, D10)

- The study-spec benchmark enum gains `shower-containment` and `longitudinal-profile`; the grade enum (now reference, sanity, interface) gains `setup-matched`; the observable-kind enum gains `shower-maximum`; `validation_plan.scope` gains `observable_kind`, `target_geometry_sha256` and `hash_scheme` (for setup-matched, A1.2).
- The study spec (top-level `additionalProperties: false`) gains top-level properties: `observables` (referencing `simulation-observables/1`; `name` must equal the names in `convergence_plan.observables`, e.g. `mpv_deposit_MeV`) and `blocks: {K, B}`. The existing singular `observable` is unchanged and remains the study's main observable.
- `ext_computational_run.json` declares the existing `simulation` property in the schema (J14's run records already carry `extension.simulation` and `_study_upgrade` already tests it; needs hep-computing's agreement). `study` is a free object today (lines 90–92); if CV-A1 declares its structure, it must stay open: `results`, `tail_sources_simulated` (written by B2, read by `check_f4` in `contracts/design.py`) and `evidence_overlap` are all optional.
- D10: `test_geant4_upgrade` and `test_simulated_dataset` no longer share a temporary directory that gets deleted (each builds its own replay, or a package-level fixture is used).

### A1.13 Regenerating and recording J14

| Run type | Today | What A1 does |
|---|---|---|
| The 5 runs with per-event CSV (`events/`, with an `event` column) | A single reduced CSV | No re-recording: cut blocks offline with the A1.5 producer, produce and commit `simulation-summary/1` |
| 13 scan, variation and scenario runs (e.g. `mpv-cut-0.1`, `sp-em-option3`, `mpv-density-10`) | Only `geant4-run-summary/1` (one value plus a bootstrap SE) | Re-record live in E2 with `seeding: stream` (event counts per A1.9); produce and commit the summary; CSV not committed |
| Negative-direction (−density) controls | Do not exist (the existing `mpv-control` and `sp-control` inject only +density) | Record new ones in E2; commit the summary |
| Trial runs | Do not exist | Every point recorded live first gets a trial run in E2 (A1.9); its summary is committed as the basis of the event count |

- Replay: `examples/geant4-thin-silicon/run.py` computes from the committed summaries instead, meeting the replay requirement of §A.4.3; no Geant4 or compiler needed.
- Old `geant4-run-summary/1` files are kept, only for replaying old records.
- Both J14 studies supply all three declared cut values (0.01, 0.03, 0.1 mm), so A1.16 does not change their gate decisions.
- The size of `recorded/` is measured in A1 (in bytes, not `du`'s block usage); single files are limited by `check_packaging.py` to 2 MiB (2,097,152 bytes); the cap on the whole of `recorded/` is the maintainer's decision (§P.7 item 5).

### A1.16 Completeness of the convergence scan (D11)

Numbered when added on 2026-10-24; not renumbered, so that existing references stay valid.

**Change:** `convergence()` in `check_geant4_study.py` (from line 335; `vals` at lines 341–348); protocol lines 93–95.

- Every declared value of a parameter (`convergence_plan.parameters[].values`) must have a summary with role scan or nominal; if any is missing, that parameter's gate is `incomplete` (exit 3), `reason: missing-scan-value`, listing the missing values.
- "The two finest" are the two finest declared values (declared values sorted ascending, the first two; A1.8's a and b are defined this way), no longer the two finest among the supplied summaries.
- Protocol lines 93–95 now ask the user to supply every value and check `two_finest` by hand; they are changed to say the code checks it.
- Trace tag `geant4-convergence-complete`.
- J14's decisions do not change (A1.13).
- Ledger: S2 (changes decisions), entry `geant4-gate-scan-completeness` (A1.14).

### A1.17 F4-consumer compatibility

Since main 0.37.0, `evaluate_design.py f4 --label-spec …` first re-issues the study record with `check_geant4_study.py label --upgrade`, then reads `extension.study.results.<figure of merit>` (`evaluate_design.py` lines 498–560); `check_f4` in `contracts/design.py` (lines 988–1062) counts only `validated-in-scope` records (line 1004). This path cannot complete today: `f4` passes no `--run-record`, so `label` refuses the upgrade with "no run record to reference as evidence" (`check_geant4_study.py` lines 564–569) but still exits 0 and writes an `unvalidated` record; `f4` then fails with exit 2 because the record has no `results` (`evaluate_design.py` lines 530–532). A1 changes `label`'s upgrade rules, so A1 fixes the consumer to report the outcome faithfully; writing `results` and tail sources is B2's work.

**Change:** `skills/hep-detector/scripts/evaluate_design.py` (the `f4` subcommand only), the F4 row of `system-design-workflow.md`; tests.

- `f4` gains `--label-run-record REL`, `--label-reference-record REL` (both repeatable) and `--label-variations REL`, passed on unchanged as `label`'s `--run-record`, `--reference-record` and `--variations`.
- `label`'s exit codes follow §A.3 rule 6; `f4` maps `label`'s exit 3 to `incomplete` (exit 3), exit 1 to `failed`, exit 2 to `rejected`; today any non-zero is `failed` (line 508).
- When the re-issued record is not `validated-in-scope` (upgrade refused), `f4` reports `incomplete` (exit 3) with `label`'s `upgrade.refused` reasons, instead of falling through to the later usage error "the record has no `results`"; a `validated-in-scope` record without `results.<figure of merit>` is likewise `incomplete`, reason `results-missing` (the normal case before B2).
- `label` itself keeps its current behaviour when the upgrade is refused: exit 0, an `unvalidated` record written, the refusal reported.
- Tests (`tests/skills/hep_detector/`, following `F4Path` in `test_design_m2.py`, with a synthetic design project and J14-style study records): (a) run records reach `label` through `f4`; (b) a refused upgrade gives `incomplete` from `f4` with the reasons listed; (c) an upgrade without `results` gives `incomplete`, `results-missing`; (d) the existing `F4Path` tests pass unchanged. The full positive path (`geometry → study → label --upgrade → f4` giving an F4 evaluation) is tested in B2.
- Per `docs/maintenance.md`, turning an error into a finding is S4 (`robust-fix:`): it needs a regression test and a parent record, no advisory (ledger entry `design-f4-label-passthrough`, A1.14). `evaluate_design.py` has no tool contract, so `contracts/tool_contracts/` needs no update.

### A1.14 Version and sci-fix process

- **Version:** contracts CV-A1 (minor). Precedents for new gated rule families (2.4.0, 2.6.0, 2.8.0, 3.1.0, 3.2.0) were all minor.
- **Commits:** one `sci-fix:` commit per fix (`robust-fix:` for S4), with its regression test; the ledger's `commits` (`parent`, `fix`, `follow_up`, 40-character hashes) point to it (`docs/maintenance.md` lines 219–227).
- **Ledger (`docs/evidence/sci-fixes.json`):** one entry is one fix (line 226; an entry bundling several is split and its old id kept in `superseded`). Each `fixes` entry has `id`, `title`, `changelog` (`{"kind": "unreleased"}` before the merge), `severity`, `evidence_tests`, `oracle_kinds`, `correctness`, `discrimination`, `negative_control_emulates_pre_fix`, `gaps`, `note`, `independence` (each: kind, test, basis, detail, `expected_from`, `requires`), `commits`, `parent_records`, `mutants`. D8 changes no number or verdict and D10 is a test fix; both go only in the CHANGELOG.

| Defect | `fixes` entry | Severity | Minimum evidence |
|---|---|---|---|
| D1 observable kind | `geant4-scope-kind` | S2 | C2, D2 |
| D1 missing scope dimensions (per-benchmark dimensions) | `geant4-scope-missing-dimension` | S2 | C2, D2 |
| D2 grade declared by the record itself | `geant4-grade-table` | S2 | C2, D2 |
| D2 validation classes (`longitudinal-profile` becomes setup-matched) | `geant4-setup-matched-class` | S2 | C2, D2 |
| D3 control judged on the observable, both directions | `geant4-control-shift` | S2 | C2, D2 |
| D3 t quantile of the detection limit | `geant4-detection-limit` | S2 | C2, D2 |
| D4 IUT of the convergence gate (definitions of diff and se) | `geant4-gate-iut` | S2 | C2, D2 |
| D11 completeness of the scan | `geant4-gate-scan-completeness` | S2 | C2, D2 |
| Isolation definition (incl. vacuum) | `geant4-isolation` | S2 | C2, D2 |
| D5 block batch means instead of the bootstrap SE | `geant4-batch-means-se` | **S1** | C3, D2; `review` sign-off |
| D5 exact intervals for low counts | `geant4-low-count-exact` | **S1** | C4 (a finite count range can be enumerated), D2; `review` sign-off |
| D5 three-point interpolation of the MPV | `geant4-mpv-estimator` | **S1** | C3, D2; `review` sign-off |
| `f4` pass-through and exit codes (A1.17) | `design-f4-label-passthrough` | S4 (`robust-fix:`) | C1, D2 |

| Defect | `documentation_fixes` entry | Severity | Sources |
|---|---|---|---|
| D6 stopping rule | `geant4-stopping-rule` | S3 | One external source (literature on optional stopping, verified and located through hep-citations) and one internal source (protocol section 4) |
| D7 evidence correlation | `geant4-evidence-overlap` | S3 | Same; internal sources only are noted in `gaps` |

- **Evidence:** the C and D axes are reported separately (lines 133–153). S1 needs at least C3 + D2 (C4 where a closed form or a finite domain exists), S2 at least C2 + D2, S3 a located source and a second source, S4 C1 + D2 (here C and D are evidence grades, not contract versions or defect numbers). C3 needs at least one independence record whose `expected_from` is not `transcribed-formula` (e.g. t and F quantiles from scipy as `third-party-definition`, the coverage of batch means as `general-result`); `requires` lists only packages of `requirements-core.txt`. D2 needs, for every oracle named by an independence record, a parent record (fails on the parent commit, passes on the fix); D3 also needs a killed `revert` mutant. On the parent, a new function, argument or output key is an `error` and does not count (lines 147–149), so evidence tests are written through the command lines of `validate.py` and `check_geant4_study.py` with existing inputs. Geant4 evidence that runs only in E2 is recorded in the release gate; what cannot run goes in `gaps`.
- **Checks:** `tools/scifix_ledger.py report` (lists S1 entries without `review` and entries with transcribed formulas only), `tests/tools/test_scifix_ledger.py`, `test_scifix_schemas.py`, `tools/run_required_backends.py --from-ledger --no-skips`.
- **Advisories (format `hep-research-scifix-advisory/2`, lines 252–283):** one for S1 and one for S2 (`scifix_advisories.py check` requires an advisory's severity to equal that of every entry it lists); S3 and S4 need none. Numbers are the next unused at merge (now SFA-2026-039 (S1) and SFA-2026-040 (S2)).
  - `applies_to.match` (OR over groups, AND within a group; every group needs a discriminating condition):
    - Study records: `artifact_types` includes `computational-run`; conditions `extension.study` exists, `status[*]` eq `validated-in-scope`, `provenance.code_paths[*]` regex `check_geant4_study\.py$` (`unknown_before: 3.5.0`: older records carry no trace and are "possibly affected (no trace)").
    - F4 design evaluations (built on wrongly upgraded study records): `artifact_types` includes `design-evaluation`; condition `extension.fidelity` eq `F4`.
    - Simulated dataset-records: conditions on the fields the `dataset.simulated_upgrade_*` rules of `contracts/validate.py` read; when no field can tell, `match_basis` says why and they are listed under `no_trace`.
    - Whether `scifix_advisories.py check` accepts a `status[*]` path is confirmed with the tool at implementation (unverified).
  - Range: `introduced` 0.20.0 with `database_specific.introduced_basis`; no `fixed` event before the merge, with `database_specific.fixed_commit`; `affected` computed by the tool from `release-manifests/` (now 0.20.0–0.38.x); the `fixed` event is added at the release.
  - `impact`: `observables` (the affected study observables, detection limits, values and verdicts of F4 evaluations), `bias`, `trigger`.
  - `remedy`: regenerate study records with the new version; after a study is re-issued, redo its F4 evaluations with `evaluate_design.py f4 --replace` (once the study's hash changes, the old evaluations become stale in `contracts/design.py`); run `contracts/dependencies.py` on simulated tables.
- Study records produced from 0.20.0 on with `validated-in-scope` fail under `--strict`; the advisory says what to do (regenerate with the new version).

### A1.15 A1 acceptance

- [ ] Records with a kind mismatch, a declaration missing a dimension, a class or grade differing from the table, a missing or embedded configuration, or a mismatched target hash or `hash_scheme` are rejected under `--strict` and CV-A1; a `dependencies.py` re-derivation mismatch is rejected; scalar scopes compare correctly.
- [ ] Unknown roles and an S repeated within a study are rejected; runs with legacy seeds are checked by their rule.
- [ ] Regenerated J14 study records pass `validate.py --strict` and `dependencies.py`; any change in decisions is recorded with its reason (gate G-A1).
- [ ] Gate toys (10⁴ per cell, with the model stated in the A1.8 table header) agree with the A1.8 table to ±3σ_MC: the "se = target" columns check the TOST part only, the "two-stage" columns the full gate including the target condition; the `absolute` mode and the interval decisions for low counts are tested.
- [ ] Coverage toys for block batch means: for each class of J14 estimator (mean, proportion, quantile, mode), the actual coverage of a nominal 90 % interval satisfies |coverage − 0.90| ≤ 0.02 + 3σ_MC, reported per class (run with `coverage` and `coverage_gate` of `toy_ensemble`).
- [ ] MPV bias toys: 95 % upper bound ≤ tol/10; the per-execution check is in effect.
- [ ] Detection-limit toys (the caught definition of A1.10): probability of catching an injection at DL ≥ 0.977 − 3σ_MC; the outcome of J14's realised controls recorded in VALIDATION.
- [ ] J14's offline replay runs from the committed summaries, decisions meet §A.4.3, without Geant4 or a compiler.
- [ ] Unit tests of the Python producer: block division, selection, merging, exit 2 when `weight ≠ 1`, overflow bins.
- [ ] Each new `core/` file has unit tests (`t_ppf`, `f_ppf` against known values and third-party values from scipy; test vectors for H) and is registered in `core/OWNERS.json` (the `files` of `stats` and the new `simulation` module), with a minor bump of `CORE_VERSION`; Garwood exists only once, as `poisson_diagnostics.central_interval`; a test importing only `core` (as an adapter would) reads a summary, computes estimators and calls `equivalence`; `check_layering.py` passes.
- [ ] `python3 -m unittest discover -s tests/contracts -t .` has no errors.
- [ ] D11 (A1.16): the gate is `incomplete` when any declared scan value is missing; "the two finest" are declared values; J14's decisions unchanged.
- [ ] The four tests of the F4 consumer (A1.17) pass; `tests/skills/hep_detector/test_design_*.py` and `tests/contracts/test_design_*.py` pass unchanged.
- [ ] The schemas of summaries and observables are in `contracts/schemas/` and validated by the callers; `core/` does not import `contracts` (`check_layering.py`).
- [ ] The thirteen `fixes` and two `documentation_fixes` entries of A1.14 pass `tests/tools/test_scifix_ledger.py`, `test_scifix_schemas.py` and `tools/scifix_ledger.py report` (S1 entries signed off with `review` before the next minor); two advisories (format `/2`) pass `scifix_advisories.py check`; parent records and mutants complete, and `tools/run_required_backends.py --from-ledger --no-skips` reports no failing oracle; live Geant4 evidence recorded with release-gate; VALIDATION GEANT4-CORRECTNESS; CHANGELOG; release manifest.

---

## §A.6 Stage A2: shared headers and boundary artifacts (geant4 adapter 0.2.0)

A2 does not change `layered_sim`'s spec format or existing outputs; it only adds optional fields and files.

### A2.1 `g4sim`

**Location:** `adapters/geant4/assets/g4sim/` (headers; shared by `layered_sim` and task B's `element_sim` and `simreco`; owner hep-detector). The directory is not named `g4common`, to avoid confusion with the existing Python module `assets/g4common.py` (imported by four scripts, listed in `adapter.json`).

| File | Content | Dependency |
|---|---|---|
| `SimHash.hh` | SHA-256 (written in the plugin) and A1.4's H, checked against `core/simulation/seeds.py` with test vectors; a SplitMix64 generator and Box–Muller normal deviates (for programs not linked to Geant4). SplitMix64 uses only integer arithmetic and is bit-identical across platforms; Box–Muller uses libm's `log` and `cos`, so it is bit-identical only on the same platform, with relative difference ≤ 1e-12 across platforms; built with `-ffp-contract=off` | C++17 standard library only |
| `SimSeed.hh` | The two seeds of event i, (H(S, i, 0), H(S, i, 1)); calls `G4Random::setTheSeeds` with the zero-terminated array `long seeds[3] = {s0, s1, 0}` (as in `layered_sim.cc` lines 150–151) | Geant4, `SimHash.hh` |
| `SimSummary.hh` | Block accumulators (the fields of A1.5), Neumaier summation, merging, JSON writing of `simulation-summary/1` | C++17 standard library only |
| `MiniJson.hh` | Moved from `layered_sim/` (content unchanged; `layered_sim` includes this copy instead) | C++17 standard library only |
| `SimProbe.hh` | The probe (A2.4) | Geant4 |
| Helpers | Material construction (including the order of mixtures), physics-list selection, CSV writing | Geant4 |

- Moving code with the same function from `layered_sim` into `g4sim` must not change its behaviour (guaranteed by the regression check).
- `SimHash.hh` and `SimSummary.hh` are tested in an environment without Geant4 by optional ctests (optional CI job).

### A2.2 Per-event seeding

- `layered_sim` spec/1 gains an optional `run.seeding`: `stream` (default, existing behaviour) or `per-event`; and `run.logical_run_seed` (S). All three places gain them together: the `run` key list of `validate_spec()` in `geant4_run.py` (line 204), `layered_sim/spec.schema.json` and `layered_sim/Spec.cc`.
- `per-event`: event i reseeds with `SimSeed.hh` at the **start** of `GeneratePrimaries` (before any random draw), i being the global event number. Geant4 calls `GeneratePrimaries` before `BeginOfEventAction`, so reseeding cannot happen in `BeginOfEventAction`; `BeginOfEventAction` must not draw random numbers. The same logical run gives identical events for any split into jobs and any thread count.
- Geant4 stores the random status before calling `GeneratePrimaries` (`/random/setSavingFlag`, `StoreRandomNumberStatusToG4Event`), so the stored status is the one before reseeding and cannot reproduce a `per-event` event; reproduction uses (S, i) instead. The probe records these flags.
- J14's existing specs are not changed and stay `stream`. Specs of new studies get `per-event` written by the adapter by default.

### A2.3 `layered_sim` writes the run summary

- spec/1 gains optional `output.observables` (referencing `simulation-observables/1`), `output.blocks` (K, B, the logical run's first event number) and `output.debug_observable_dump`; all three places gain them together: the `output` key list of `validate_spec()` (line 215), `spec.schema.json` and `Spec.cc`; `geant4_run.py` writes them into the execution spec from the study spec's observable declarations.
- At the end of each event, the declared observables are accumulated into their block; under MT they merge through a custom `G4VAccumulable`: `G4AccumulableManager::Reset()` is called at the start of every run (`BeginOfRunAction`); workers call `G4AccumulableManager::Merge()` in their own `EndOfRunAction`, the master writes in its own `EndOfRunAction`; master and workers register in the same order.
- Output `summary.json` (`simulation-summary/1`, producer `layered_sim`), its hash written into the run record.
- Event weight ≠ 1: exit 2.
- **Test dump:** with `output.debug_observable_dump: true` in the spec, a side file lists the declared observables per event as `%.17g`; used only in tests, and the CSV itself is unchanged.

### A2.4 Effective config and the probe (`SimProbe.hh`)

```
{ "engine": "geant4", "engine_version": "11.4.3", "probe_version": "...",
  "backend": {"name": "layered_sim", "version": "...", "sources_sha256": "..."},
  "source": "probe" | "declared", "recorded": true, "config_sha256": "...",
  "seeding": {"mode": "per-event" | "stream", "logical_run_seed": ...},
  "geometry": { "tree": [...], "tree_sha256": "...", "naming_sha256": "...", "hash_scheme": "tree-v1", "gdml_sha256": null },
  "environment_ref": "<hash of the build record>",
  "sections": { "geant4": { ... } } }
```

| Item | Spec |
|---|---|
| When | The master's `BeginOfRunAction` (called inside `G4RunManager::RunInitialization`, after the kernel closes the geometry); state `G4State_GeomClosed` and more than 0 couples; otherwise `recorded: false` (`layered_sim` still exits 0), and that run cannot upgrade. A fake run (`/run/beamOn 0`) returns before `BeginOfRunAction`, so the probe does not run |
| Frequency and threads | Once per run; master only; noted as "workers assumed identical" |
| Geometry tree | Rebuilt from `G4PhysicalVolumeStore` (a flat list in creation order) and each volume's mother logical volume; per placement: name, copy number, solid type and parameters, material (composition and density as resolved by Geant4), transform, mother, attached field manager and parameters; numbers written in the format of Python `float.hex()` (e.g. `0x1.0000000000000p+0`); C's `%a` output differs (`0x1p+0`), so `SimProbe.hh` carries its own formatter, checked against Python with test vectors, special values included: 0.0 → `0x0.0p+0`, −0.0 → `-0x0.0p+0`, subnormals (e.g. `0x0.0000000000001p-1022`), `inf`, `-inf`, `nan` (inf or nan in the geometry gives exit 2); replica and parameterised volumes record their parameterisation |
| `tree-v1` hash | Target = the set of placements of the slabs listed in `target_slabs` (A1.3), each with its subtree, in the canonical order below; target hash = sha256 of the JSON (sorted keys, no whitespace) of this set, with transforms taken relative to the first target placement (so moving the whole target does not change the hash); `tree_sha256` by the same rules over the whole tree. Content is physics only: solid type and parameters, material composition and density, transform relative to the mother, attached field; volume names and copy numbers are **not** included. Daughters of one mother are in canonical order (by the translation of the transform, then solid parameters, then material, all compared as hex strings), not creation order; when translation, solid and material are all identical, they are ordered by copy number and this is noted. Names and copy numbers are counted separately in `naming_sha256`. This lets setup-matched compare the same configuration built by different programs, and lets task C cache identical designs |
| GDML | The plugin's build has GDML off; when a user build has GDML, `gdml_sha256` may be attached, but is not required |
| EM parameters | Full text of `G4EmParameters::StreamInfo(os)` plus parsed fields; not `Dump()` |
| Cuts | Per material-cuts couple: material, region, range cut, energy threshold per particle |
| Hadronic models | Per process and model, energy ranges queried with `GetHadronicInteractionList()` and `GetMinEnergy(mat, elm)`, `GetMaxEnergy(mat, elm)`; overlapping ranges marked as random selection; each model's `IsBlocked()` per material and element is recorded; when `G4NeutronGeneralProcess` or `G4GammaGeneralProcess` is active, the sub-processes and models it contains are recorded one by one. **Must not** call `G4EnergyRangeManager::GetHadronicInteraction` or `ChooseHadronicInteraction` (with overlapping ranges they call `G4UniformRand`) |
| Random numbers | The probe must draw no random numbers (otherwise it breaks §A.3 rule 13); a test confirms the random-engine state is the same before and after the probe |
| Run manager | The actual run-manager type (with `MTOnly`/`SerialOnly` the environment variable `G4RUN_MANAGER_TYPE` is ignored), `seedOncePerCommunication`; SubEvt or a non-zero seed mode reports a gap |
| Other | `G4UserLimits`, biasing (with biasing, flag "events may share state") |
| Datasets | Paths and content hashes computed once in the build record; the probe refers to it via `environment_ref` |
| Field | Field managers are per thread; a declared field the master cannot see is marked `source: declared` (`layered_sim` has no field) |
| Paths | Written through `tilde()` |
| Storage | Content is stored once by `config_sha256` (`effective_configs/<config_sha256>.json`), and several runs with the same settings refer to the hash only; `extension.simulation.effective_config` holds the reference; committed J14 records also carry the full content for offline replay. The schema is in `adapters/geant4/assets/schemas/` (owned by the adapter, validated by the adapter's scripts with `contracts.schema.validate`) |

- Rules and the model assignment of variations read the probe first and fall back to the declaration only when the probe cannot be read, outputting `source: probe | declared`; when both exist and disagree, it is an error.
- Test trigger: a UI command that exists only in the test build calls the probe after `/run/initialize` and before the first `BeamOn`; it must write `recorded: false`.

### A2.5 Column map (`simulation-columns/1`)

- `layered_sim` writes `column_map.json` for each run, its hash written into the run record; the schema is in `adapters/geant4/assets/schemas/`.
- Per column: semantic name, actual column name, unit, operational definition, file it lives in (`csv` or `summary`); with `column_map_version`.
- Only declarative operations are allowed (rename, unit conversion, sum, filter); a transformation that needs computation is a separate, recorded step.

### A2.6 The study layer reads only boundary artifacts (D9)

| Location | Change |
|---|---|
| `cmd_summarize`, benchmarks | Read only the summary (and the column map's semantic names); no CSV column names |
| `derived()` and the thin-layer rule | Minimum thickness from the effective config's geometry tree; records from before A2 (no effective config) still use spec/1's `geometry.layers` |
| Configuration and target hash | Records from A2 use `tree-v1`; A1 records keep `spec-v1`; comparison only between the same `hash_scheme`; `dependencies.py` re-derives by the record's `hash_scheme` |
| Consistency check | `geant4_run.py` (not `layered_sim`, to avoid a second implementation of `spec-v1` in C++) checks after every `layered_sim` run that the configuration derived via `spec-v1` and the one derived via `tree-v1` give the same decision; exit 2 if not |
| `geant4_verify.py` | Volume counts and material budget from the geometry tree |

### A2.7 Schema keywords

- Extend `contracts/schema.py` with `maxItems`, `maximum`, `exclusiveMaximum` (still missing from `SUPPORTED_KEYWORDS` on main 0.38.0, lines 61–63; already used by `layered_sim`'s schemas; also needed by `element_sim`'s schemas). `layered_sim/spec.schema.json` also uses `oneOf` and `not`: either implement these two keywords or rewrite them into supported forms, and note which in VALIDATION. Update `SUPPORTED_KEYWORDS`, and make `tests/contracts/test_schema_keywords.py` also scan the adapters' schemas (including `adapters/geant4/assets/schemas/`); `layered_sim/output.schema.json` is not a JSON Schema (its top-level keys are column names) and is exempt. New schemas never use `uniqueItems` (unsupported by the validator, see that test's docstring); uniqueness, where needed, is checked in Python.
- Contracts not bumped (no contract schema uses the new keywords).
- `validate_spec()` in `geant4_run.py` is not replaced; A2.2 and A2.3 only add new fields to its key lists.

### A2.8 Adapter-change process

| Item | Content |
|---|---|
| Version | 0.1.0 → 0.2.0 |
| `adapter.json` | `assets` gains `g4sim/` and `summary_from_csv.py`; update `purpose`; `status` stays `demonstrated-on-synthetic-data` |
| `SIM_SOURCES` | Add the `g4sim/` files so that `sources_sha256` covers everything (B1 then groups it by program) |
| Run record | The run record written by `geant4_run.py run` also carries `argv`, `script_sha256`, `versions.plugin_release` (as `run_workflow.py` does; optional fields of `ext_computational_run.json` since 3.11.0) |
| Schemas | `adapters/geant4/assets/schemas/` (column map, effective config) |
| G5 | Statement "written from the Geant4 API; no example code copied or adapted", confirmed by the reviewer in the VALIDATION entry |
| Tests | The assets check in `tests/adapters/test_geant4.py`; offline tests; live tests with `HEP_GEANT4_LIVE_TEST=1`; ctests of `SimHash.hh` and `SimSummary.hh` (optional) |
| Docs | The Geant4 row of `docs/capability-matrix.md`; `geant4-study-protocol.md` (boundary artifacts, blocks, validation classes) |

### A2.9 Tests and oracle

- From the A2.3 test dump, recompute the summary with the A1.5 Python producer and compare with the one written by `layered_sim`: integers identical, floating-point relative difference ≤ 1e-12.
- Under `per-event`, the same logical run with 1, 2, 4 jobs and 1, 2, 4 threads: identical event content (dumps bit-identical), summary integers identical, floating-point relative difference ≤ 1e-12.

### A2.10 A2 acceptance

- [ ] Regression check: on the same host, `layered_sim` is rebuilt from the pre-A2 commit (`main` after A1 is merged) as the reference, and J14's 18 existing specs produce CSVs bit-identical to it with the A2 build; the random-engine state is the same before and after the probe (gate G-A2).
- [ ] H in `SimHash.hh` equals `core/simulation/seeds.py` on the test vectors; the hex format of `SimProbe.hh` equals Python's `float.hex()`.
- [ ] Both tests of A2.9 pass; under `per-event`, if `GeneratePrimaries` draws random numbers (a random gun in a test), event content still does not depend on how the run is split into jobs.
- [ ] `tree-v1` does not depend on naming: one geometry built twice with different volume names and creation order gives the same `tree_sha256` and target hash and different `naming_sha256`; changing any physical quantity (thickness, material, position) changes the hash.
- [ ] Effective configs are stored only once per content hash; two runs with the same settings refer to the same file.
- [ ] The new spec fields (`run.seeding`, `run.logical_run_seed`, `output.observables`, `output.blocks`, `output.debug_observable_dump`) are accepted by `validate_spec()`, `spec.schema.json` and `Spec.cc`; unknown fields are still rejected.
- [ ] The new run records of the J14 specs rerun in E2 for the regression check (all 18 in `recorded/specs/`: `mpv-nominal`, `mpv-control`, `mpv-cut-0.03`, `mpv-cut-0.1`, `mpv-cut-0.3`, `mpv-cut-1.0`, `mpv-density-10`, `mpv-em-option0`, `mpv-em-option3`, `mpv-ftfp-bert-emz`, `mpv-pai`, `sp-nominal`, `sp-control`, `sp-cut-0.03`, `sp-cut-0.1`, `sp-density-10`, `sp-em-option0`, `sp-em-option3`; still `stream`) all carry an effective config, and `tree-v1` and `spec-v1` give the same decisions; a deliberate inconsistency is caught; a run with `recorded: false` cannot upgrade. The committed J14 records stay at their A1 version and are not regenerated in A2.
- [ ] The thin-layer rule takes the minimum thickness from the effective config, with the same conclusion for J14 as in A1.
- [ ] The study layer's production code reads no CSV column names (confirmed by a test).
- [ ] Event weight ≠ 1 gives exit 2.
- [ ] Run records carry `argv`, `script_sha256`, `versions.plugin_release`.
- [ ] The schema-keyword test scans the adapters' schemas (`output.schema.json` exempt); `oneOf` and `not` handled per A2.7; no `uniqueItems`.
- [ ] J14's offline replay still meets §A.4.3.
- [ ] VALIDATION GEANT4-SUMMARY; CHANGELOG; release manifest.

---

## §A.7 Contracts and versions

| Object | Location | Version |
|---|---|---|
| Benchmark table (class, kind, scope dimensions), scope comparison, configuration and isolation, `hash_scheme`, evidence roles, uniqueness of S, completeness of the scan | `contracts/validate.py`, `contracts/dependencies.py`, `check_geant4_study.py` | CV-A1 (minor, gated, sci-fix) |
| Declaration of the `simulation` property | `contracts/schemas/ext_computational_run.json` | CV-A1 (needs hep-computing's agreement) |
| Schemas of summaries and observables | `contracts/schemas/` | CV-A1 |
| Schema-keyword extension | `contracts/schema.py` | not bumped |
| Modules of `core/stats/` and `core/simulation/` | `core/` | `CORE_VERSION` (SemVer; minor bump in A1); the summary format versioned by `summary_version` and the version of `simulation-observables/1` |
| Schemas of column map and effective config | `adapters/geant4/assets/schemas/` | geant4 adapter 0.2.0; versioned by `column_map_version`, `probe_version` |
| F4-consumer compatibility (`--label-run-record` etc., exit-code mapping) | `skills/hep-detector/scripts/evaluate_design.py` | with the plugin version (no contract change) |
| Writing of `g4sim`, `seeding`, summary, column map, effective config | geant4 adapter | 0.2.0 |
| `GRADES`, kind and configuration output | hep-detector | with the plugin version |

The owner of the computational-run schema is hep-computing. CV-B2 belongs to task B (B2); CV-C1 and CV-C2 to task C. Numbers are fixed at release in merge order.

---

## §A.8 Checks at the end of every stage

Every stage of tasks B and C runs these checks as well.

- `run_all_checks.py` (including the CI lock environment)
- `check_layering.py`, `check_relocation.py`, `check_ownership.py`, `check_packaging.py`
- `measure_entrypoints.py` (quick load ≤ 25,600 bytes)
- `reference_inventory.py --check`, `capability_map.py --check`, `check_routing_static.py`
- Every study record passes `validate.py --strict` and `dependencies.py`
- `tests.adapters.test_geant4` offline and live (`HEP_GEANT4_LIVE_TEST=1`)
- `tests/examples/test_geant4_thin_silicon.py` (replay decisions meet §A.4.3)
- `python3 -m unittest discover -s tests/contracts -t .` (run as a whole)
- `tools/check_wiring.py` (also run by `run_all_checks.py`): new scripts and references must be wired
- `tools/ci_plan.py`: confirm that pull requests select the Geant4 and core tests (`contracts/rules/registry.json` has no impact group for `adapters/geant4/**`, `core/stats/**` or `core/simulation/**` today, so it falls back to a full run; adding groups is optional, §P.8)
- `tests/skills/test_cli_robustness.py` (scans `adapters/*/assets/*.py`; new scripts registered in `MISSING_FILE_ARGS`)
- Scripts with a tool contract (`contracts/tool_contracts/`) agree with their `--help`; task A adds no tool contract (`check_geant4_study.py`, `geant4_run.py` and `evaluate_design.py` have none)
- Design-loop tests: `tests/skills/hep_detector/test_design_*.py`, `tests/contracts/test_design_*.py`
- `tools/scifix_advisories.py check`, `tools/scifix_ledger.py report`, `tests/tools/test_scifix_ledger.py`, `test_scifix_schemas.py`, `tools/run_required_backends.py --from-ledger --no-skips` (A1)
- Tests with 10⁴ toys go in the slow tier (`HEP_SLOW_TESTS=1`), run and recorded in the release gate
- A new problem run by an agent that did not take part in writing, with pass conditions
- The Markdown of each stage reviewed with 0.22.0's `review.py` (`--lens-model design=<strongest model>`, `--filter-model`); its record is advisory only and, per O04/O14, does not replace the human G5 confirmation
- VALIDATION entries, CHANGELOG, release manifest

---

## §A.9 Not done and deferred

| Item | Decision | Reason / trigger |
|---|---|---|
| spec/2, spec conversion, dual-format accessor, bit-identical comparison gate | Not done | `layered_sim` keeps its format; new features go into `element_sim` |
| Integer quantization, 128-bit integers, bit-identical statistics | Not done | Reproducibility means same decisions |
| `simstat`, a `simcore` not linked to Geant4 | Not done | Inference stays in Python |
| Several independent processes per evidence run | Not done | Blocks are within the run |
| `uses-validated-physics` label | Not done | The hash is both too strict and too loose; it would bypass the scope check |
| Adaptive stopping on SE, refined scans as evidence, rerunning controls with another seed | Not done | Optional stopping |
| New core validators, rewriting the tracking and multiple-scattering formulas | Not done | Reuse existing tools |
| Contracts 4.0 | Not done | New optional blocks and gated rules are minor |
| Python bindings | Not done | The user chose separate executables exchanging JSON/CSV |
| Replacing `validate_spec()` | Not done | Out of scope |
| `change`, paired comparisons, search roles, `values` | Moved to B2, C2 | §P.2 R1 |
| `threshold` and `order` as requirement decisions | Not done | Requirement verdicts, ranking and Pareto fronts are derived by main's `contracts/design.py` (§P.0) |
| A second Garwood, a second toy-seed derivation, another coverage gate | Not done | Reuse `poisson_diagnostics.central_interval` and `toy_ensemble`; each quantity has one production implementation |
| Weighted accumulation and biasing rules | Deferred | The first study that uses biasing |
| `physics_config_comparison` | Deferred | A study that compares physics settings; then differences must obtain the effective config through `evidence_records`, and always fail when it is missing |
| Rule version ranges, probes for several Geant4 versions | Deferred | Supporting a second Geant4 version (B2's regression class uses it first) |
| Benchmark registry | Deferred | Replaced by the contract table and the enum consistency test |
| `inspect` and Linux environments | Deferred | Needed to run on CVMFS or LCG |
| ReferenceMaterial contract | Deferred | The first reference benchmark on non-slab geometry |
| Generalized `scoped_upgrade` | Deferred | A second study type needs upgrades |
| Migrating J14 to `element_sim`, retiring `layered_sim` | Deferred | `element_sim` can produce all of J14's observables (§P.8) |

---

## §A.10 Open decisions and residual risks

**Open decisions** (numbers in §P.7): item 1 (classification of CV-A1), item 2 (stewards of the `core/` modules), item 3 (the `simulation` property), item 4 (two-stage factor and what to do if J14 loses its upgrade by chance), item 5 (J14 re-recording and the `recorded/` cap), item 6 (switch threshold for exact intervals), item 7 (how to confirm G5).

**Residual risks:**
1. J14's detection limits may change because of block batch means, t quantiles and controls in observable units; the controls need redesign.
2. Block batch means have O(1/B) bias for ratios, quantiles and modes of skewed distributions, which does not shrink with K; the coverage toys allow ±0.02, and B is increased if needed.
3. Block independence fails when events share state; the probe flags biasing, and in doubt use several independent logical runs.
4. With tolerance comparisons, near-threshold decisions may differ between platforms; handled by the margin flag and "the CI platform rules".
5. MT merging of a custom `G4VAccumulable` must be confirmed by tests.
6. The probe assumes workers and master have the same settings; if thread-local differences appear, switch to per-thread dumps.
7. A setup-matched target hash only proves the configuration is the same, not that it is the one in the paper; a reviewer must still check.
8. Quick load has only 931 bytes left.
9. Effort: the prototype estimated about 8–12 working days for the contract part of A1, plus Geant4 run time; the statistics part and A2 are estimated when they start. The new ledger rules (one entry per fix, parent records, mutants, S1 sign-off) add to A1's effort.
10. main moves fast (3.5.0 to 3.12.0 in two days); `validate.py`, `dependencies.py`, `evaluate_design.py` and the design-loop PRs share files; rerun §A.8 after every rebase.
11. D2 needs a parent-commit record for every oracle; Geant4 evidence that runs only in E2 may fall short, in which case `gaps` says so and the maintainer decides the grade.

---

## §A.11 Suggested order of work

At the start of each stage, create and confirm that stage's isolated worktree per §P.10.2 and do every step in it; remove it per §P.10.5 after merging.

**A1**
1. Pre-start checks (§A.0); apply `prototype/phase1-core.patch`, replace its hard-coded 3.6.0 by CV-A1, and complete what A1.1–A1.3 lack.
2. Fix D10 first (A1.12); from then on always run `python3 -m unittest discover -s tests/contracts -t .` as a whole.
3. For each fix, first write the evidence tests that fail on the parent commit (through the command lines), then fix in a separate `sci-fix:` commit (A1.14).
4. A1.1 → A1.2 → A1.3 (contracts and `dependencies.py`) → A1.16 (D11), with contract tests.
5. `core/simulation/seeds.py` and `summary.py`, the schemas in `contracts/schemas/`, the A1.5 Python producer; produce summaries offline from J14's 5 per-event CSVs.
6. The three `core/stats/` files (A1.6–A1.10), with hep-detector's scripts calling them and reading summaries; toy tests (gate, coverage, MPV bias, detection limit) and a usage test importing only `core`; `OWNERS.json` and `CORE_VERSION`.
7. A1.4's role rules and the rest of A1.11 and A1.12 (protocol, enums, `simulation` property).
8. A1.17: pass-through and exit codes of `evaluate_design.py f4`, with tests (`robust-fix:`).
9. In E2, record the trial runs first and fix the event counts per A1.9, then re-record J14's scans, variations and negative-direction controls live (A1.13); regenerate J14 records and run `--strict`.
10. A1.14: the ledger's `commits`, `parent_records`, `mutants`, `independence`; two advisories (format `/2`); VALIDATION, CHANGELOG, release manifest; run `tools/scifix_ledger.py report` and the checks of §A.8.

**A2 (after A1 is merged)**
1. `g4sim/SimHash.hh`, `SimSummary.hh` and ctests (no Geant4), with `core/simulation/` and the A1.5 Python producer as oracles.
2. `SimSeed.hh` and `run.seeding`; `SimProbe.hh` with the geometry tree and `tree-v1`.
3. `layered_sim` integration: the new spec fields (`validate_spec()`, `spec.schema.json`, `Spec.cc`), summary, effective config (with storage by content hash), column map, test dump; rebuild `layered_sim` from the pre-A2 commit as the reference and confirm the CSVs of J14's 18 specs are bit-unchanged.
4. Study layer reads boundary artifacts (A2.6); schema keywords (A2.7).
5. Adapter-change items of A2.8; run live tests in E2; tick all of A2.10; run the checks of §A.8.

---

## §A Appendix A: Statistics summary

| Item | Spec | Work item |
|---|---|---|
| Blocks | K ≥ 16 blocks by event number, B events each; declared in advance | A1.5, A1.6 |
| SE | Batch means, sd(θ_b)/√K, t_{K−1} | A1.6 |
| Low counts | Any block 0 or total < 100: Clopper–Pearson, Garwood, conditional binomial; the gate decides on interval endpoints | A1.6, A1.8 |
| MPV | Mean of three-point interpolations of block histograms; bias toy 95 % upper bound ≤ tol/10; per-execution check | A1.7 |
| Quantiles | Linear interpolation within the histogram; bin < tol/10; incomplete on overflow (C2 adds empirical quantiles from `values`) | A1.6 |
| Convergence gate | IUT; `relative` or `absolute`; se_diff; Welch ν; per-point se target tol/(4√2); pass needs both points to meet the target; every scan value present, the two finest taken from the declared values | A1.8, A1.16 |
| Uncertainty for F4 | `statistical_uncertainty` = t_{0.84135}(K−1)·SE; the exact branch writes an asymmetric interval | A1.6 |
| Two-stage | Trial run; N rounded up to a multiple of K; f = F₀.₉₀(K−1, K_trial−1); target missed → incomplete, no top-up; about 19 % of point pairs incomplete, all n runs meet the target with probability about 0.9ⁿ | A1.9 |
| Negative control | Shift in the observable; DL = tol + \|rel\| + t_{0.977}(ν)·se_rel; both directions; toy threshold 0.977 − 3σ_MC | A1.10 |
| Seeds | Byte-level definition of H; S = H(study_id, role, point_id); job seeds H(S, e, 0/1); event seeds H(S, i, 0/1) | A1.4, A2.2 |
| Evidence correlation | `evidence_overlap` | A1.11 |
| Reproducibility | Same decisions, numbers within relative 1e-9, near-threshold flag | §A.4.3 |
| Version fields | `summary_version`, `column_map_version`, `probe_version`, `evidence_overlap_version` | A1.5, A1.11, A2.4, A2.5 |

## §A Appendix B: Numbers

Computed by `gate_operating_characteristics.py` (needs numpy and scipy; a design aid only).

- F₀.₉₀(15,15) = 1.972; F₀.₉₅(15,15) = 2.403; F₀.₉₀(31,31) = 1.594.
- t₀.₉₅(30) = 1.697, t₀.₉₅(15) = 1.753, t₀.₉₇₅(15) = 2.131; fail quantile for m = 30, t_{1−0.05/30}(30) = 3.189.
- Welch ν (K = 16): 30 at variance ratio 1, 27 at 2, 22.1 at 4, 18.0 at 10.
- Mean se_diff under the two-stage design ≈ 0.189 tol (target 0.25 tol); probability that at least one point of a pair misses its target 0.190.
- Detection-limit power (the caught definition of A1.10) is near 0.977 (the reviewer's calculation about 0.9785).

## §A Appendix C: Baseline values (`9f08796`; rechecked against `5584927` on 2026-10-24)

| Item | Value |
|---|---|
| `CONTRACTS_VERSION` | 3.12.0 (3.5.0 at `9f08796`) |
| `GEANT4_UPGRADE_FROM` | 3.1.0 (line 348) |
| J14 study record | contract 3.12.0, with `code_paths`, `code_tags` |
| J14 world material | `G4_Galactic` |
| J14 `recorded/` | 2,447,979 bytes (about 2.45 MB; `du -sh` shows 2.6M); `events/` 5 reduced CSVs (`event`, `primary_eloss_MeV`, `edep_Si_MeV`, `primary_fate`, `primary_end_process`); `runs/` 18 run records; `summaries/` holds single-value summaries (`geant4-run-summary/1`) of all 18 runs; 5 runs also have a per-event CSV, the 13 scan, variation and scenario runs only the single-value summary |
| J14 seeds | The first seed of the 5 non-re-recorded runs is 1401 or 1402 |
| Advisory | latest SFA-2026-038; format `hep-research-scifix-advisory/2` |
| hep-detector | quick load 24,669 / 25,600 bytes; description 1,016 / 1,024 characters (`measure_entrypoints.py`); `DetectorScriptCount` 23 (`tests/skills/test_documented_output_claims.py` lines 145–147) |
| `GRADES` | `longitudinal-profile: "reference"` (lines 92–94); the study spec's grade enum is reference, sanity, interface |
| `ext_computational_run.json` | Does not declare `simulation`; J14's run records already carry `extension.simulation` |
| `core/stats` | steward hep-statistics; already has `beta_ppf`, `clopper_pearson`, Garwood (`poisson_diagnostics.central_interval`, line 162, present at the baseline already), `toy_ensemble` (`toy_seed`, `coverage`, `coverage_gate`); no t or F quantiles |
| `core` | `CORE_VERSION = "1.0.0"` (`core/__init__.py` line 2); admission rule of `OWNERS.json`: more than one top-level consumer |
| Layering rules | Adapters import only `core` and `contracts`; `core/` imports only `core` (`tools/check_layering.py`) |
| `SUPPORTED_KEYWORDS` | no maxItems, maximum, exclusiveMaximum, uniqueItems, oneOf, not (`contracts/schema.py` lines 61–63) |
| Sci-fix ledger | `docs/evidence/sci-fixes.json`: `fixes` (46 entries), `documentation_fixes`, `superseded`; each entry with `independence`, `commits`, `parent_records`, `mutants` |
| F4 of the design loop | `evaluate_design.py f4` (lines 498–560) calls `label --upgrade` without `--run-record`; `label` therefore refuses the upgrade but still exits 0 and writes an `unvalidated` record (`check_geant4_study.py` lines 544–628); the record has no `results`, so `f4` then fails with exit 2 (lines 530–532) |
| Convergence gate | `convergence()` takes the two finest values from the supplied summaries (lines 341–348); both J14 studies supply 0.01, 0.03, 0.1 mm |
| Prototype | `prototype/phase1-core.patch` still applies to `5584927` (dry run; `validate.py` offset by 2 lines) |
| `check_packaging.py` MAX_BYTES | 2 MiB (2,097,152 bytes, per file) |
| Geant4 build | `GEANT4_USE_GDML: OFF`; `layered_sim` MT uses `G4RunManagerType::MTOnly` |
| Shared stanza point 5 | says "3.1.0 upgrade rule" (unchanged) |
| Journey table | J1–J14 |
| Stage 1 prototype | 55 tests pass; J14's 7 study records pass `--strict`; D10 reproduced on clean main (5 errors) |

## §A Appendix D: Sources

The experiments and frameworks the design refers to (ATLAS, CMS, ALICE, Key4hep, Allpix², geant-val, Belle II) are in §R.14. Relevant Geant4 11.4.3 source files: `G4RunManager.cc`, `G4MTRunManager.cc`, `G4WorkerRunManager.cc`, `G4EmParameters.cc`, `G4ProductionCutsTable`, `G4HadronicProcess.hh`, `G4EnergyRangeManager`, `G4AccumulableManager`, `G4VAccumulable`, `G4PhysicalVolumeStore`, `G4LogicalVolume`, `G4NistMaterialBuilder.cc`, `G4PVPlacement`.

## §A Appendix E: Version history

| Version | Content |
|---|---|
| Before 2026-10-21 | Three rounds of independent review, two checks against 0.21.0 and `9f08796`, stage 1 prototype |
| 2026-10-22 | Language split, per-event ROOT files, task split, organized as an implementation spec; redesign referencing real experiments (Part 5 (design rationale)); rewritten for the new architecture |
| 2026-10-23 | Fixes after independent review (two-stage operating characteristics recomputed, definition of H, caught definition, reseeding at the start of `GeneratePrimaries`, etc.); re-examined for automated design (statistics moved to `core/`) |
| 2026-10-23 | Reorganized per the plan (Part 1): A1 back to a minimal sci-fix (`change`, `threshold`, `order`, paired comparisons, search roles and `values` moved to B2 and C2); contract version written CV1; the seed hash in `core/simulation/seeds.py`; section numbering consistent with tasks B and C (§A.2 prerequisites and provided interfaces, §A.8 checks, §A.10 open decisions and risks) |
| 2026-10-23 | Added the isolated-worktree execution rule: header, the first step of §A.0, the start of §A.11 (§P.10) |
| 2026-10-23 | Fixes after the detailed check: new spec fields added to `validate_spec()`, `spec.schema.json` and `Spec.cc` together; A1.5's selections match the current code; `tolerance` and the direction of `count_if`; names of the seed fields and `cmd_chunk`; trial runs and N rounded up to a multiple of K; tol and se_rel of DL; the `tree-v1` target; `float.hex()` special values, `setTheSeeds`, `IsBlocked()` and the general processes; cross-platform tolerance of Box–Muller; D7 and D8 in the ledger; factual corrections (line numbers, size of `recorded/`, `summaries/`, the prototype's description) |
| **2026-10-24 (this version)** | **Re-planned against main 0.38.0 (detector design loop): baseline `5584927` / contracts 3.12.0; D11 added (A1.16) and F4-consumer compatibility (A1.17); ledger and advisories in main's current formats (one entry per fix, `documentation_fixes`, advisory `/2`, SFA-2026-039/-040, covering F4 design evaluations); Garwood, `toy_seed` and `coverage_gate` reused; summary schemas moved to `contracts/schemas/`, column-map and effective-config schemas to the adapter; definition of `statistical_uncertainty`; `evidence_role`; CV1 written CV-A1; `CORE_VERSION` and `OWNERS.json`; A2's run records gain `argv`, `script_sha256`, `versions.plugin_release`, schema keywords `oneOf`/`not` and exemptions; line numbers updated** |

---

# Part 3 — Task B: `element_sim`, reconstruction and the J15 minimal spectrometer (§B)

> Order: B1 after A2; B2 after B1; B3 after B2. Task C's C2 waits for B2 and C1; B3 and C2's F4 confirmation wait for D0 (§P.7)
> Baseline: hep-research `main` at `5584927` (0.38.0), contracts 3.12.0, adapter geant4 0.1.0, Geant4 11.4.3; must be rechecked before starting (§B.0)
> Date: 2026-10-24
> Nature of the example: J15 is a design project with a **synthetic geometry**, not any experiment's detector; the closest real instruments are PAMELA and AMS-02 (§B.4.3)

---

## §B.0 Task card

**Goal.** Add a general box-element Geant4 program `element_sim` as a second backend, add the reconstruction program `simreco` that does not link Geant4, and make the two the **missing F4 evaluator** of main's detector system design loop: derive the simulation setup from the `design-geometry/1` file that `evaluate_design.py geometry` generates from a design-candidate, simulate and reconstruct, and write a study record that `evaluate_design.py f4` accepts (`extension.study.results`, `tail_sources_simulated`, the geometry file in `input_manifest`). Finally take the J15 minimal spectrometer, as a design project, from F1 and F2 to F4.

**Three stages (in order, each merged separately):**

| Stage | Content | Version |
|---|---|---|
| **B1** `element_sim`, event files and geometry derivation | `element_sim.spec/1` and `element_sim` (box elements, one level of nesting, piecewise-uniform field, plane crossings of every charged track, calorimeter leakage); per-event ROOT files; `simroot`; `geant4_run.py check-spec` and `from-geometry` (`design-geometry/1` plus a realization profile → `element_sim.spec/1`); interface consistency of the two backends; deterministic field check | geant4 adapter **0.3.0**, no contract change |
| **B2** Reconstruction and the F4 interface | `simreco` (digitization and reconstruction, portable random numbers, switchable tail sources); observables for F4; `geant4_run.py reco`, `table` and the F4 results file; `check_geant4_study.py label` writing `results`, tail sources and the geometry file; geometry mapping 1.1.0; asymmetric uncertainty and a per-evaluation geometry file in `f4`; transitive processing chain; verification and regression classes; the decision engine's `change`; the **F4 qualification path** (D0) with the tracking reference benchmark; end-to-end test `geometry → study → f4` | geant4 adapter **0.4.0**, contracts **CV-B2** (minor) |
| **B3** J15 design project | J15's design-spec and candidates (N = 6, 4, 8); F1 and F2 through `evaluate_design.py`; one F4 study per (figure of merit, denominator); the effect of tail-source switches on the bound; the verification ladder (a separate `unvalidated` record); calorimeter cut convergence, variations and model envelope, TOF σ_t sensitivity; recorded data; journey J15 and docs | example and docs (no adapter version bump) |

**Out of scope:** interface changes of task A (if needed, first handled within task A as an adapter patch release); new geometry features in `layered_sim` (it is frozen); task C's candidate search; ion sources and Birks (deferred, §B.9); non-box geometry and field maps (§B.9); F4 qualification of calorimeter figures of merit (needs a published-data reference, §B.9).

**Deliverables:** `element_sim`, `simroot`, `simreco` and their tests; `geant4_run.py check-spec`, `from-geometry`, `reco`, `table`; the CV-B2 changes to `check_geant4_study.py label`, `evaluate_design.py f4` and `contracts/design.py`; geometry mapping 1.1.0; the J15 example `examples/design-minimal-spectrometer/` (design-spec, candidates, evaluations, study records, README, recorded data); the J15 journey and routing case; VALIDATION entries GEANT4-ELEMENT (B1), GEANT4-F4 (B2), GEANT4-J15 (B3); CHANGELOG; release manifest.

**Definition of done:** the acceptance checklists of B1.10, B2.10 and B3.9 are all ticked; all checks of §A.8 pass; gates G-B1a, G-B1b and G-B2 (§P.6) pass; the qualification rules of B2.8 and B3's F4 confirmation merge only after D0 is approved.

**Main decisions:**
1. **Add a backend, do not change `layered_sim`.** `element_sim` leaves J14's program untouched and validates the output-layer interface with a real second backend (§R.3.2).
2. **The design-candidate is the single source of truth.** The geometry of an F4 study always comes from `evaluate_design.py geometry` applied to the candidate, and `element_sim.spec/1` is derived from it deterministically (B1.8); hand-written specs are only for studies that are not used as F4.
3. **Field accuracy by a deterministic check.** Charged geantino against an analytic helix, no statistics needed; done in B1 (B1.7).
4. **F4 through a qualification path.** A detector-level study can become `validated-in-scope` through `label --upgrade` only when materials, field and reconstruction have passed verification and the tracking reference benchmark has passed (B2.8, D0). J15's verification ladder is a separate record that is always `unvalidated` (B3.2).
5. **Tail sources declared honestly.** The four tail sources (alignment, calibration-non-uniformity, noise-digitization, pattern-recognition) are switchable stages of `simreco`; the study record lists only the sources actually simulated, an empty array if none; only with all four is an F4 resolution or charge-confusion value an `estimate` (`contracts/design.py:64`, `1058-1059`).
6. **Infrastructure separate from the physics study.** B2 delivers the F4 interface and `simreco`, so task C's C2 does not wait for the J15 study (§P.1 P3).
7. **No new hep-detector script.** Reconstruction is the C++ `simreco`, the interface is in the adapter; only the existing `check_geant4_study.py`, `geant4_benchmarks.py` and `evaluate_design.py` change (the script count stays 23); quick load and description unchanged.

**First step:** create this stage's isolated worktree per §P.10.2 (`.claude/worktrees/geant4-<stage>`, branch `worktree-geant4-<stage>`, based on the latest `origin/main` that contains the prerequisite stages), and confirm `git rev-parse --show-toplevel`, `git branch --show-current`, `git status` and that the prerequisite stages' merge commits are ancestors of `HEAD`. Every later step happens in that worktree.

**Before starting:**
1. Confirm A2 is merged and every interface listed in §B.2 exists; before B2 starts, confirm the status of D0 (§P.7).
2. Using the method of §A Appendix C, recheck against the then-current `main` the facts this part cites (quick load, description length, journey list, `DetectorScriptCount`, contracts version, structure of `MISSING_FILE_ARGS`, the version of `design_geometry.json`, the fields `check_f4` reads), and update this part (both languages).
3. Read §A.1, §A.3, §A.4, §P.4–§P.6 and main's `skills/hep-detector/references/system-design-workflow.md`; this part does not repeat them.

---

## §B.1 Terms and files

| Term | Meaning |
|---|---|
| J15 | This task's minimal spectrometer (synthetic geometry), in the form of a design project (B3.1) |
| `element_sim` | The Geant4 program added in B1; spec `element_sim.spec/1` |
| `design-geometry/1` | The geometry file main's `evaluate_design.py geometry` generates from a candidate (fields per `contracts/rules/design_geometry.json`), with a parameter digest |
| realization profile | `element_sim.realization/1`: the geometric facts the mapping table lacks (materials, transverse sizes, field-region extent, coordinate origin, subsystems not yet in the mapping), read by `from-geometry`; its hash goes into `input_manifest` (B1.8) |
| F1–F5 | Main's fidelities (`contracts/design.py:65`): F1 analytic tool, F2 toy MC, F3 response and expected precision, F4 Geant4 study re-issued by `label --upgrade`, F5 measurement |
| figure of merit, denominator | A quantity of main's adequacy table (`contracts/rules/design_adequacy.json`), e.g. `momentum-resolution-core` (denominator `rigidity_GV`, `species`) |
| tail sources | The four of `contracts/design.py:64`: alignment, calibration-non-uniformity, noise-digitization, pattern-recognition |
| bending plane | The x–y plane (B along z); the non-bending direction is z |
| rigidity R | p/\|q\| in GV; C = 0.2998 GV/(T·m) |
| MDR | Maximum detectable rigidity: the rigidity at which σ_R/R = 1 from the measurement term alone |
| TOF station | TOF1 or TOF2; two layers per station (a, b) |
| charged geantino | Geant4's charged test particle that feels only the field and has no material interactions (mass 0, β = 1) |
| processing chain | simulation → reduction → digitization and reconstruction → table, one computational-run record per step |
| Notation | "B1.3" is a work item of this part; "§B.4.2" is a section of this part; "A1.6", "C2.1" are work items of tasks A and C; "§A.3", "§P.4", "§R.6" are sections of other parts of this document |

**Main files (relative to `plugins/hep-research/`):** `adapters/geant4/assets/g4sim/` (created in A2, extended here); `adapters/geant4/assets/element_sim/` (new); `adapters/geant4/assets/simroot/` (new); `adapters/geant4/assets/simreco/` (new, does not link Geant4); `adapters/geant4/assets/geant4_run.py` (adds `check-spec`, `from-geometry`, `reco`, `table`; `SIM_SOURCES` defined at line 63, used at lines 327 and 386); `core/stats/decisions.py` (B2 adds `change`); `contracts/validate.py`, `contracts/dependencies.py`, `contracts/design.py`, `contracts/rules/design_geometry.json`, `contracts/schemas/design_geometry.json` (CV-B2); `skills/hep-detector/scripts/check_geant4_study.py` (`label`, lines 540–630), `skills/hep-detector/scripts/geant4_benchmarks.py` (`GRADES` at line 92, new benchmark functions), `skills/hep-detector/scripts/evaluate_design.py` (`geometry` at line 462, `f4` at line 498); `skills/hep-detector/assets/geant4-study-spec.schema.json`; `skills/hep-detector/references/geant4-study-protocol.md`, `system-design-workflow.md`; `tests/skills/test_cli_robustness.py` (`MISSING_FILE_ARGS`, the `geant4_run.py` entry at line 153); `docs/researcher-journeys.md`, `docs/maintenance.md`, `docs/capability-matrix.md` ("twenty-three scripts" at line 49, checked by the test class `DetectorScriptCount` at line 145 of `tests/skills/test_documented_output_claims.py`), `docs/capability-map.json` and `docs/capability-map.md`; `examples/design-minimal-spectrometer/` and `tests/examples/test_design_minimal_spectrometer.py` (new).

---

## §B.2 Prerequisites and provided interfaces

**Prerequisites (provided by task A):**

| Interface | How task B uses it |
|---|---|
| Benchmark table, validation classes, scope comparison, isolation rule (A1.1–A1.3) | B2 appends verification, regression and tracking-reference entries and the qualification rules; the benchmarks of J15's verification ladder are all embedded and do not count toward an upgrade |
| Evidence roles and uniqueness of S (A1.4) | B2 appends the regression role |
| Block estimators, exact intervals, MPV, decision engine `equivalence`, two-stage event counts (A1.6–A1.10) | B3's decisions; B2 adds `change` through the same interface; the F4 `statistical_uncertainty` is the 68.27 % t half-width (A1) |
| `simulation-summary/1`, `simulation-observables/1` (A1.5, schemas in `contracts/schemas/`) | `element_sim` and `simreco` write summaries with the same schema |
| Compatibility fixes of `label` and `f4`: `f4` passes `--label-run-record` through, `label` exit 3 maps to `incomplete` (A1) | Used by B2's end-to-end test |
| `g4sim`: `SimHash.hh`, `SimSeed.hh`, `SimSummary.hh`, `MiniJson.hh`, `SimProbe.hh`, material and physics-list helpers (A2.1) | `element_sim` uses all of them; `simreco` uses only the Geant4-free `SimHash.hh`, `SimSummary.hh`, `MiniJson.hh` |
| `per-event` seeding (reset at the start of `GeneratePrimaries`, A2.2) | `element_sim` supports only `per-event` |
| The three boundary artifacts, name-free `tree-v1`, effective-config storage, `argv` and `script_sha256` in the run record (A2.3–A2.6) | `element_sim` and `simreco` deliver the same boundary artifacts; a field attached inside the target counts in the `tree-v1` target hash |
| Schema keywords `maxItems`, `maximum`, `exclusiveMaximum` (A2.7) | The schemas of `element_sim.spec/1` and `element_sim.realization/1` |

**Prerequisites (already provided by main):**

| Interface | Location | How task B uses it |
|---|---|---|
| `evaluate_design.py geometry`: generates `design-geometry/1` from a candidate and sets the candidate's `geometry_ref` | `evaluate_design.py:462-495` | Input of `from-geometry` (B1.8) |
| `evaluate_design.py f4` and the F4 checks of `contracts/design.py` | `evaluate_design.py:498-560`; `design.py:988-1062` | B2.6's output must pass them; B2 changes both (CV-B2) |
| Geometry mapping `layered-spectrometer` 1.0.0 | `contracts/rules/design_geometry.json` | Five tracking and field fields; B2 extends it to 1.1.0 |
| Adequacy table | `contracts/rules/design_adequacy.json` | Figures of merit, denominators, compliance fidelities (resolution F3; charge confusion F4 plus data validation and rigidity-scale offset; shower containment F4; tracking-selection-efficiency F4) |
| F1 and F2 tools | `tracker_resolution`, `multiple_scattering`, `toy_spectrometer` (F2), `design_estimates.py infield-acceptance` (F2) | B3's F1 and F2 evaluations |
| Example project format | `examples/design-space-spectrometer/` | Format of the J15 design project |

**Provided to task C:**

| Interface | Work item | How task C uses it |
|---|---|---|
| `element_sim.spec/1`, `check-spec` | B1.1, B1.6 | The specs of C2's Geant4 search values are generated by `from-geometry` and validated |
| `geant4_run.py from-geometry` and the realization profile `element_sim.realization/1` | B1.8 | C2 obtains a spec from a decoded candidate through `geometry` and `from-geometry`; one realization profile serves a whole search |
| Calorimeter mother and `leak_*_MeV` | B1.3 | Search values of calorimeter subsystems |
| `simreco` (rigidity, β, calorimeter energy) and the tail-source switches | B2.1, B2.2 | Reconstruction of search values; tail sources of confirmation studies |
| F4 results file and `label --results`, `--geometry` | B2.6 | C2's F4 confirmation of finalists |
| Decision engine `change` | B2.7 | C2's version-regression checks |

---

## §B.3 Hard rules

All rules of §A.3 apply. In addition:

1. Do not change `skills/hep-detector/SKILL.md` or the hep-detector description (only 931 bytes of quick load left; description 1,016 / 1,024 characters). J15's routing case must reuse trigger words already in the description.
2. No experiment names in `skills/`, `contracts/` or `core/`; the contract table and the protocol cite references by citation key. Experiment names (PAMELA, AMS-02) may appear only in `docs/` and the J15 `examples/` README.
3. The field code is written from the Geant4 API, without copying or adapting the B5 example's code (G5).
4. Do not change the shared stanza's text (point 5 says "3.1.0 upgrade rule"; changing it touches every SKILL.md and requires a live routing rerun).
5. J15's `recorded/`: ≤ 2 MiB per file, ≤ 3 MB in total; ROOT files are not committed (B3.7).
6. The record of J15's verification ladder (B3.2) is always `unvalidated`, and its benchmarks do not count toward an upgrade. J15's F4 studies (B3.6) can become `validated-in-scope` only through B2.8's qualification path and `label --upgrade`; never claim that a study that was not upgraded is F4.
7. No geometry features are added to `layered_sim`; new geometry features go only into `element_sim`.
8. Neither Python nor `simreco` parses ROOT directly; always through `simroot`.
9. Contract rules are gated by `strict or _at_least(contract_version, CV-B2)`.
10. Follow the "Never" list of main's design loop (`system-design-workflow.md:201-208`): no hand-written verdicts, maturities or stale markers; evaluations are written only by `evaluate_design.py` and never edited afterwards; F4 evaluations are produced only by `evaluate_design.py f4`.
11. The `design-geometry/1` of an F4 study and the `element_sim.spec/1` derived from it are never edited by hand; changing the geometry means changing the candidate and regenerating.

---

## §B.4 Design of J15

### §B.4.1 Geometry

Coordinates: origin at the world centre, stack axis x, unit mm.

**Field: B = (0, 0, +0.5 T).** Bending plane x–y, non-bending direction z. A positive charge moving along +x bends toward −y; a μ⁻ toward +y.

```
x:  −1000   −810 … −780   −520 −500        …         300  320    490 … 520   550          900   ±1200
     gun    TOF1 (2 layers)│ Si1  Si2  Si3  Si4  Si5  Si6  │     TOF2 (2 layers) calorimeter 50 layers  world edge
            10 + 10 mm    │◄────── uniform field 0.5 T ẑ (−520 … 320) ─────►│     10 + 10 mm   Pb 2 / PVT 5 mm
```

| Element | Material | Front face x | Thickness | Extent | Transverse (y × z) |
|---|---|---|---|---|---|
| World | `G4_Galactic` | — | 2400 | −1200 … 1200 | 1200 × 1200 |
| Source | — | x = −1000, y = z = 0 | — | — | — |
| TOF1a, TOF1b | `G4_PLASTIC_SC_VINYLTOLUENE` | −810, −790 | 10 each | −810 … −800, −790 … −780 | 300 × 300 |
| Field-region mother | `G4_Galactic` | −520 | 840 | −520 … 320 | 300 × 300 |
| Si1–Si6 (daughters) | `G4_Si` | −500.15 + 160k | 0.3 | centres −500, −340, −180, −20, 140, 300 | 200 × 200 |
| TOF2a, TOF2b | `G4_PLASTIC_SC_VINYLTOLUENE` (same as TOF1) | 490, 510 | 10 each | 490 … 500, 510 … 520 | 400 × 400 |
| Calorimeter mother | `G4_Galactic` | 550 | 350 | 550 … 900 | 500 × 500 |
| Calorimeter sampling layers (daughters) | 50 × (`G4_Pb` 2 + PVT 5) | 550 | 350 | 550 … 900 | 500 × 500 |

**TOF stations.** TOF1 and TOF2 each have two layers; all four layers have the same material and thickness (10 mm), with a 10 mm vacuum gap between the two layers of a station. Each layer is one slab, not segmented and without a paddle direction (a deliberate simplification); the two layers give two independent time measurements and dE/dx samples, and their agreement within a station becomes a check (B3.2).

**Checks** (program in §B Appendix A, recomputed in tests):
- Lever arm L = 0.800 m; the front of Si1 and the back of Si6 are 19.85 mm from the mother's boundaries.
- The field extends 20 mm beyond the measurement region at each end.
- Distance between the TOF station centres (midpoints of the two layers: −795, 505 mm) D = 1.300 m.
- The back face of TOF2's rear layer (520) is 30 mm from the calorimeter's front face (550); TOF1's front layer (−810) is downstream of the source (−1000).
- The world contains the source and the back of the calorimeter.

Materials (11.4.3 NIST definitions against PDG): `G4_PLASTIC_SC_VINYLTOLUENE` 1.032 g/cm³, I = 64.7 eV; `G4_Si` 2.33 g/cm³ (PDG 2.329).

**Deliberate simplifications** (listed one by one in J15's README): nominally a uniform field with sharp edges (the piecewise-uniform field serves only miscalibration, B1.2), no magnet material, unsegmented TOF layers, no optical photons, no trigger or readout electronics, no anticoincidence. Silicon strips, thresholds, efficiency, noise and clustering are handled in `simreco` as a switchable digitization stage (B2.2), off in the nominal setup.

### §B.4.2 Parameters and acceptance

| Parameter | Value | Basis |
|---|---|---|
| B | 0.5 T | The rigidity where the multiple-scattering term equals the measurement term is about 16–22 GV (μ), independent of B; 0.5 T gives one decade in 1–10 GV and one in 100–1000 GV |
| Number of Si layers | 6 | With N = 4 the bending plane has only 1 degree of freedom; N = 8 improves the MDR by only about 8 % |
| MDR | about 1172 GV | Measurement term only. Reference value from `tracker_resolution.py`'s exact least squares (C = 0.2998). `multiple_scattering.py`'s `mdr_intrinsic_only_gv` has the same definition but uses the Gluckstern approximation (about 1131 GV for N = 6); since 0.21.0 it also outputs `intrinsic_coefficient` and warns for N < 10 |
| TOF | Two layers per station; σβ/β ≈ 2.3 % (100 ps per layer, two independent layers, β = 1; 3.3 % with one layer per station); 3.5 % at 150 ps | D = 1.3 m; the station time is the mean of the two layers, σ_station = σ_layer/√2 |
| Calorimeter | 18.4 X₀, 0.886 λ_I, 50 cm wide | Enough to separate e/p by shower shape, not enough to measure hadron energy |

**Multiple-scattering term.** Highland formula with the log term on the total thickness, times a factor 1.0–1.4. The review's exact least squares with discrete scattering planes gives a factor of 1.02 (weighted) to 1.06 (unweighted). By its convention `multiple_scattering.py` **omits** the log term; comparisons state the difference.

| Particle | Rigidity | β | Multiple-scattering term | Rigidity where the two terms are equal |
|---|---|---|---|---|
| μ | 1 GV | 0.994 | 1.3–1.9 % | 16–22 GV |
| p | 0.6 GV | 0.539 | 2.5–3.5 % | 29–41 GV |
| p | 1 GV | 0.729 | 1.8–2.6 % | 21–30 GV |
| p | 2 GV | 0.905 | 1.5–2.1 % | 17–24 GV |

**Acceptance** (unit charge, on-axis normal incidence, uniform field, sharp edges):

| Condition | Minimum rigidity |
|---|---|
| Does not leave the field-region mother through its side before x = 320 (\|y\| ≤ 150 mm) | 0.364 GV |
| Reaches Si6 (\|y\| ≤ 100 mm) | 0.511 GV |
| Reaches TOF2's front layer (x = 490, \|y\| ≤ 200 mm) | 0.385 GV |
| Crosses both TOF2 layers (x = 520, \|y\| ≤ 200 mm) | 0.404 GV |
| Calorimeter front face, shower axis within 250 − 2 R_M,eff | 0.490 GV |
| Calorimeter back face, same | 0.745 GV |

Overall threshold 0.75 GV; 0.51 GV when only tracker plus TOF is required. Trajectories below 0.364 GV leave the field region through its side and then travel in straight lines in the field-free world. The F2 acceptance evaluation comes from main's `design_estimates.py infield-acceptance` (B3.1).

Electrons: the shower axis is displaced by 82 mm and 127 mm at the calorimeter's front and back faces at 1 GeV, 16 mm and 25 mm at 5 GeV. Bremsstrahlung photons from the 11.3 % X₀ upstream (83 % of it in the four TOF layers) are not bent, so the shower axis is not a straight-line extrapolation; the 79 mm margin is a geometric estimate and the shower check must be confirmed with the actual lateral energy distribution. Electron shower checks are limited to 1 GeV and above.

**Upstream energy loss** (Bethe integral, 2 cm PVT for TOF1's two layers):

| Proton rigidity | Kinetic energy | TOF1 loss | Δp/p | Change of β between station centres |
|---|---|---|---|---|
| 0.6 GV | 175 MeV | 10.23 MeV | 3.20 % | 2.87 % |
| 1 GV | 433 MeV | 6.00 MeV | 0.82 % | 0.46 % |
| 2 GV | 1271 MeV | 4.34 MeV | 0.24 % | 0.05 % |

At 0.6 GV β changes by 2.87 % between the stations, more than the TOF resolution (2.3 %): low-rigidity β comparisons need a β model with energy loss, or are limited to 2 GV and above. TOF1 is before the first Si plane and does not affect the curvature resolution; the true rigidity comes from the Si plane crossings.

**J14 cannot be reused.** J15's Si differs from J14's in material (`G4_Si` against `Si_study`), physics settings and cuts, and J15 records only entries, so J14's E_in − E_exit observable cannot be formed.

### §B.4.3 Comparison with real instruments

| Instrument | Configuration (sources in §R.14) | Compared with J15 |
|---|---|---|
| PAMELA | 0.43 T permanent magnet; 6 double-sided silicon microstrip planes, resolution better than 4 µm; MDR above 1 TV; three TOF planes (S1–S3, segmented into paddles); tungsten/silicon imaging calorimeter 16.3 X₀, 0.6 λ; also anticoincidence, S4, neutron detector | Almost the same type; J15 assumes 10 µm Si resolution (more conservative), unsegmented TOF, no anticoincidence |
| AMS-02 | TOF with four planes (8, 8, 10, 8 counters); about 140 ps system resolution for protons | J15's 100 ps per layer is optimistic, hence the 100 and 150 ps sensitivity (B3.5) |

J15's README uses this table to argue that J15 is reasonable, and stresses that J15 is a synthetic geometry and represents no experiment. Main's `examples/design-space-spectrometer` (three AMS-like candidates, F1 only) is a different example; J15 adds the F2 to F4 it lacks.

### §B.4.4 J15 in the design loop

| Artifact | Content |
|---|---|
| design-spec `j15-v1` | Goals and requirements (illustrative numbers, the README says they are synthetic): `REQ-TRK-001` `momentum-resolution-core` (proton 1 GV); `REQ-TRK-002` the same (proton 100 GV); `REQ-CC-001` `charge-confusion-rate` (proton, a declared `curvature_offset_per_GV` with its tolerance); `REQ-CAL-001` `shower-containment` (electron 10 GeV); constraints (mass, channel count) list their `subsystems`; derived requirements name their driving requirement in `covered_by`; `comparison_basis` equal mass; `pareto_axes` include `expected-precision` |
| candidate `cand-N6` (nominal) | `DES-TRK-001` (role `tracking`): `layer_positions_m` = [0, 0.16, 0.32, 0.48, 0.64, 0.80], `point_resolution_um` = 10, `layer_x_over_x0` = 0.0032 (0.3 mm Si), `passive_x_over_x0` = 0; `DES-MAG-001` (role `bending`): `field_T` = 0.5; parameters of `DES-TOF-001` (role `tof`) and `DES-CAL-001` (role `calorimetry-em`) per mapping 1.1.0 (B2.6); every subsystem has a calibration (method and control samples) and synthetic budgets |
| variants `cand-N4`, `cand-N8` | `derived_from: cand-N6`, `overrides` change only `layer_positions_m` and `layer_x_over_x0` (equally spaced, same lever arm) |
| realization profile `j15.realization.json` | Coordinate origin (Si1 centre x = −500 mm), stack axis x, field along z, layer material `G4_Si`, transverse sizes of the elements, field-region extent (20 mm beyond the measurement region at each end), TOF and calorimeter elements (until mapping 1.1.0), world size; all values agree with §B.4.1 |

`from-geometry` (B1.8) rebuilds the geometry of §B.4.1 from the candidate's geometry file and this profile; a test compares the two element by element.

---

## §B.5 Stage B1: `element_sim`, event files and geometry derivation (geant4 adapter 0.3.0)

### B1.1 `element_sim` and its spec

**Location:** `adapters/geant4/assets/element_sim/` (CMake project linking Geant4 and `g4sim`).

**spec `element_sim.spec/1`** (schema in the same directory, using only keywords `contracts/schema.py` supports):

| Block | Content |
|---|---|
| Coordinates | Origin at the world centre, mm; elements given by centre and half-lengths (boxes). **All centres are world coordinates** (daughters included); `element_sim` converts them to mother coordinates when placing (e.g. field-region mother centre x = −100, Si1 world centre x = −500 → mother coordinate −400) |
| `materials` | NIST names or mixtures (component order preserved; `g4sim`'s material helper) |
| `elements` | Box elements: name, material, centre, half-lengths, mother (the world or one element; only one level of nesting), role (`passive`, `tracker-plane`, `tof-layer`, `calorimeter` (mother), `calorimeter-active`, `calorimeter-passive`), repetition (for the calorimeter's sampling layers) |
| `field` | `regions[]`: the element each region is attached to, the B vector (uniform within the region); accuracy parameters (B1.2). J15 nominally has one region |
| `physics` | Physics list and EM option, cuts, regions (same semantics as `layered_sim`, through `g4sim`) |
| `source` | `type: gun`: particle, energy (`energy_MeV` or `ekin_per_nucleon_MeV`), position, direction; `gps` and `event-file` define the interface only (§R.9.2), exit 2 if encountered |
| `run` | Number of events, threads, logical run seed; `seeding` allows only `per-event` |
| `output.observables`, `output.blocks` | As in A2.3 (referring to `simulation-observables/1`) |
| `output.event_file` | `level`: `none` (default), `summary`, `crossings`, `hits`; `compression` (default 1); `max_events_hits` (the maximum number of events allowed at `hits` level, default 100) |
| `provenance` | When generated by `from-geometry`: paths and sha256 of the geometry file and the realization profile, the candidate id and the parameter digest; omitted when hand-written |

- Cross-field rules (no overlapping elements, daughters inside their mother, unique names, roles compatible with materials, no overlapping field regions) are checked in the Python adapter (`check-spec` of B1.6); C++ checks only what it needs to run.
- Every run delivers the three boundary artifacts (summary, column map, effective config), as `layered_sim` does.

### B1.2 Field

- In `ConstructSDandField`, create a `G4UniformMagField`, `G4FieldManager` and `G4ChordFinder` per field region, stored with `G4ThreadLocal`; the master and every worker each have their own copy. Creating them in `Construct()` would make workers share a chord finder that is not thread-safe.
- Attach with `SetFieldManager(fm, true)` to the region's element, propagating to all daughters; field regions may not nest.
- Add `G4StepLimiterPhysics` when there is a field.
- Stepper and driver are **built explicitly**: build `G4DormandPrince745` with `G4Mag_UsualEqRhs`, wrap it in a driver (e.g. `G4InterpolationDriver<G4DormandPrince745>`), then construct `G4ChordFinder(G4VIntegrationDriver*)` (medium confidence; check the classes and constructor against the 11.4.3 source); do not use the stepper chosen by `G4ChordFinder`'s default constructor (that is not controlled by `G4FieldParameters`). The stepper class is written into the spec, and the probe records the actual class names of stepper and driver via RTTI (a helix stepper would make the field-propagation check meaningless).
- The **piecewise-uniform field** is the minimal form before a field map: it makes a field-scale miscalibration (`simreco` reconstructs with each region's nominal value, B2.2) a tail source that can be simulated. Real field maps and fringe fields are deferred (§B.9).
- Written from the API, without copying or adapting the B5 example's code (G5).

| Parameter | Nominal | Note |
|---|---|---|
| `delta_chord_mm` | 0.25 | Has no effect when the maximum step is below about 80 mm; recorded, not scanned |
| `delta_one_step_mm` | 0.01 | In a uniform field the Runge–Kutta truncation error is far below the intersection error; no effect expected from a scan; confirm once |
| `delta_intersection_mm` | **1e-5** (0.01 µm) | Sets the accuracy of the crossing points |
| `min_epsilon_step` | 5e-5 | |
| `max_epsilon_step` | 1e-3 | epsilon = delta one step / step length, clamped at this upper limit |
| `max_step_mm` | 10 | Needs `G4StepLimiterPhysics`; `G4UserLimits` must be set per volume and does not propagate to daughters |
| `stepper` | DormandPrince745 | Built explicitly (see above) |

- **Probe:** `SimProbe.hh` walks `G4LogicalVolumeStore` and reads back each region's B, chord finder and accuracy parameters through `GetFieldManager()`; deduplicates by pointer and records the volume each was originally attached to; notes that the master sees only the master's copy. A field attached to a volume inside the target counts in the `tree-v1` target hash.
- **MT test:** a UI command that exists only in the test build reports each thread's field-manager pointer; they must all differ.

### B1.3 Plane crossings and calorimeter leakage

- **Crossings:** **every charged track** (not only the primary) is recorded the first time it enters a `tracker-plane` or `tof-layer` element (pre-step point status `fGeomBoundary` and the volume is that plane): `track_id`, `parent_id`, PDG code, and the pre-step point's position, direction, kinetic energy and global time; one "recorded" flag per track and plane. If the source sits inside a plane there is no `fGeomBoundary` and that plane writes no row. The primary's rows are identified by `track_id = 1`; B2's hit association takes all rows as input, so fake hits from δ rays and secondaries can be simulated (pattern-recognition).
- **Calorimeter leakage:** for the mother element with role `calorimeter`, record per event the energy carried out of the mother by particles leaving it from inside (steps whose `post` point leaves that mother; positrons add 2 mₑc²; times the track weight), split by the face they leave through into `leak_rear_MeV` (+x face), `leak_front_MeV` (−x face) and `leak_lateral_MeV` (y and z faces), with the same meaning as `layered_sim`'s columns of the same names (`layered_sim` uses the world boundary as faces, `element_sim` the calorimeter mother). These three columns go into the CSV, the `events` ntuple and the column map, for shower containment (`bench_containment()` in `geant4_benchmarks.py`, line 482) and B3.3's rear-leakage fraction.
- The per-event CSV keeps only summary columns (primary truth, total deposit per subsystem, calorimeter leakage); crossings and per-layer deposits go into the ROOT file (B1.4).

### B1.4 Per-event ROOT file

| Item | Specification |
|---|---|
| Writing | Through `G4AnalysisManager` (ROOT output type); underneath is the g4tools bundled with Geant4, so ROOT need not be installed and no build dependency is added |
| Files | One file per job; under MT, `SetNtupleMerging(true)` makes the master merge into a single file (in 11.4.3 only ROOT output supports ntuple merging); the path is written into the run record through `tilde()` |
| Structure | Flat ntuples with scalar columns only (I, D, S); every row has a key (`event_id` plus the ntuple's own secondary key); no vector columns |
| Row order | Not fixed after MT merging; readers always sort by key |
| When written | Rows filled in `EndOfEventAction`; the file is written and closed at the end of the run. An interrupted run leaves an incomplete file and the run is incomplete (exit 3) |
| Version | Structure `element_sim.events/1`, with `event_file_version` in the file |
| Hash | File bytes include the write time and are not bit-identical; the run record stores both the file sha256 (integrity) and `simroot hash`'s `content_sha256` (comparison and provenance). For a logical run split into several job files, `content_sha256` is computed over the union of all files sorted by key (except the `run` ntuple, which differs per file), with `processes` deduplicated by `process_id`, so it does not depend on the split |
| Size | Not committed; the run record stores path, hashes, row count and size per ntuple |

| ntuple | Level | One row per | Columns |
|---|---|---|---|
| `run` | from `summary` | file | sha256 of the spec and column map, program version and source hash, Geant4 version, logical run seed, event range, `event_file_version` |
| `processes` | from `summary` | process | `process_id`, `name` (the process number table for `hits`) |
| `events` | from `summary` | event | `event_id`, primary PDG code, kinetic energy, origin, direction; total deposit per subsystem; `leak_rear_MeV`, `leak_front_MeV`, `leak_lateral_MeV`; energy leaving the world volume; flags |
| `deposits` | from `summary` | event × volume with a deposit | `event_id`, `volume_id`, `copy`, total deposit, deposit of charged particles |
| `crossings` | from `crossings` (also in `hits`) | event × charged track × crossed plane | `event_id`, `plane_id`, `track_id`, `parent_id`, PDG code, pre-step position, direction, kinetic energy, global time, that track's deposit in that plane |
| `hits` | only in `hits` | step with a deposit | `event_id`, `track_id`, `step_index` (the track's step number; with `event_id` and `track_id` a unique key), `parent_id`, PDG code, `volume_id`, `copy`, pre- and post-step positions, time, deposit, step length, `process_id` |

- `process_id` is assigned at initialization by a deterministic rule (e.g. sorted by process name), independent of threads and job splitting; only the master fills `run` and `processes`, workers do not write these two ntuples.
- If the requested number of events at `hits` level exceeds `max_events_hits`, spec validation rejects it with `rejected` (exit 2).
- Estimate (J15, `crossings` level): charged tracks besides the primary (δ rays, back-scattering from the calorimeter) add rows; about 4–8 kB per event before compression (`crossings` 10–30 rows × 100 B, `deposits` up to 110 rows × 28 B, `events` about 120 B); up to about 800 MB for 10⁵ events before compression. The actual size is confirmed in the trial run.

### B1.5 `simroot`

**Location:** `adapters/geant4/assets/simroot/` (same CMake project as `element_sim`; links only Geant4's analysis library and creates no run manager).

- **Gate G-B1a (first day of the stage):** confirm that `G4RootAnalysisReader` can read MT-merged, compressed files and string columns. Either outcome is acceptable: if it can, keep the original design; if not, `simroot` reads only flat scalar columns and the `run` strings go to a JSON side file. The result is recorded in the VALIDATION entry.

| Subcommand | Content |
|---|---|
| `info` | Row counts and columns of each ntuple, the content of the `run` rows; JSON output |
| `dump` | After sorting by key, writes the chosen ntuples and columns as CSV (stdout or `--out`), floats as `%.17g`; can read several files at once; `--events` takes a subset |
| `hash` | Content hash: each ntuple sorted by key, values normalized as hex floats, then sha256; outputs `content_sha256` |

- Exit codes follow `core/status.py`. Researchers may analyse the ROOT files directly with ROOT or uproot, but these are not dependencies of the pipeline or of required tests.

### B1.6 `check-spec` and interface consistency of the two backends

- **`geant4_run.py check-spec --spec <file>`:** validates an `element_sim.spec/1` against the schema and the cross-field rules (no Geant4 needed); outputs JSON `{ok, problems[]}`, exit 0 or 2. B1 extends `MISSING_FILE_ARGS` in `tests/skills/test_cli_robustness.py` so that a script can map to one or more argv sets (today `geant4_run.py` has only the `run` set, line 153), and registers `check-spec` and `from-geometry`.
- The three boundary artifacts delivered by `element_sim` pass the same interface tests as `layered_sim`'s (schema, hashes, semantic names of the column map).
- **Statistical consistency compares only observables both backends produce.** J14's `stopping-power`, `range` and `thin-layer-mpv` need `primary_eloss_MeV`, `primary_fate`, `primary_end_process` (`geant4_benchmarks.py`: `transmitted()` at line 232, `bench_stopping_power` at line 278, `bench_range` at line 311, `bench_mpv` at line 347); `element_sim` does not produce these columns, so J14's benchmark verdicts are not compared.
- Method: the same slab as J14 nominal (`Si_study` declared as a mixture with the same composition and density, the same physics settings and cuts), one logical run per backend (`layered_sim` with `stream`, `element_sim` with `per-event`, so the events differ); compare the mean and mode of the Si deposit `edep_Si_MeV` (A1.7), and the **total leakage** fraction of a calorimeter-type configuration (`leak_rear_MeV + leak_front_MeV + leak_lateral_MeV` over the incident energy; the "faces" differ between the backends, the world boundary for `layered_sim` and the calorimeter mother for `element_sim`, so single-face fractions are not comparable). Each observable is decided by `equivalence` (A1.8) with a tolerance and se target (se_diff ≤ tol/4) declared in advance; on failure, do not merge (gate G-B1b).

### B1.7 Deterministic field check (`field-propagation`)

No statistics; needs only `element_sim`.

- Trajectories: charged geantino (mass 0, β = 1), rigidities 0.6, 1, 10, 100, 1000 GV.
- Directions: normal incidence; **50 mrad in the bending plane, against the bending** (+y for a positive charge); ±50 mrad in the non-bending plane.
- §B Appendix A check: with these directions every trajectory reaches every Si plane and both TOF2 layers and does not leave the field-region mother. With the bending direction instead, 0.6 GV and 1 GV miss Si6.
- Reference: analytic helix; when a trajectory leaves the field region it becomes piecewise straight, and only planes the analytic trajectory actually reaches are compared. A piecewise-field configuration is checked separately with two regions (different B), each with its own analytic helix segment.

| Scan | Grid | Criterion |
|---|---|---|
| delta intersection | 1e-3, 1e-4, 1e-5, 1e-6 mm | At nominal (1e-5), the in-plane distance √(Δy² + Δz²) ≤ 0.5 µm (ε/20) at every plane, with the analytic trajectory evaluated at the plane's x; the two finest settings differ by ≤ 0.2 µm; also record \|x − x_plane\| of Geant4's crossing point. Every grid point is reported; 1e-3 mm is not presumed to fail (Geant4's intersection error is mainly along x, and the in-plane error is only about slope × δ ≤ 0.25 µm) |
| Maximum step | 100, 30, 10, 3 mm | Same |
| delta one step and epsilon | nominal and 1/10 | No change expected; confirm once |
| TOF2 path time (both layers) | — | \|Δt\| ≤ 1 ps (about 0.3 mm of path), checks path length only |

- Negative control: Geant4-side B × (1 ± δ), with δ chosen from a trial run so that the deviation exceeds the criterion.
- Results are recorded as the `field-propagation` benchmark (verification, added to the table in B2.7); in B1 they are recorded first by tests and the VALIDATION entry. B2's `field_propagation()` reuses B1's analytic-helix oracle (the same code), not a second implementation. This check is also condition (ii) of the F4 qualification path (B2.8).

### B1.8 `geant4_run.py from-geometry` and the realization profile

**Purpose:** make the geometry of an F4 study come from the design-candidate. Inputs are the `design-geometry/1` written by main's `evaluate_design.py geometry` (`studies/<id>.geometry.json`) and a realization profile; the output is an `element_sim.spec/1`.

```
python3 <plugin root>/adapters/geant4/assets/geant4_run.py from-geometry \
    --geometry studies/G.geometry.json --profile j15.realization.json --out studies/G.element_sim.json
```

- **Deterministic:** the same two inputs give a bit-identical spec (sorted keys, values checked by a `float.hex` round trip); the spec's `provenance` records the sha256 of both inputs, the candidate id and the geometry file's `parameter_digest`.
- **Realization profile `element_sim.realization/1`** (schema in the adapter, supported keywords only): geometry kind (`layered-spectrometer`), mapping version, stack axis and field direction, coordinate origin, an element template per role (material, transverse size, the material used to convert x/X₀ into a thickness), the field-region extent rule (distance beyond the first and last measuring planes), elements of subsystems the mapping does not yet cover (TOF, calorimeter, positions of passive material), world size, physics and run defaults. The profile is general configuration and carries no candidate parameters; one profile can serve a whole design project or search.
- **Mapping rules (mapping 1.0.0):** `layer_positions_m` → centres of the `tracker-plane` elements (plus the origin); `layer_x_over_x0` × X₀(material) → thickness; `passive_x_over_x0` → one passive slab at the position the profile gives (thickness converted the same way); `point_resolution_um` does not enter the simulation and is written into the reco spec (B2.1); `field_T` → the field region's B (direction from the profile). The new fields of mapping 1.1.0 (B2.6) are mapped the same way.
- **Refusals:** an unknown geometry kind or mapping version, a profile without a template for some role, or a derived spec that fails `check-spec` are all refused with exit 2 and the reason.
- The study spec of an F4 study must list the geometry file, the realization profile and the derived spec in `input_manifest` (B2.6).
- Tests: the spec obtained from J15's candidate `cand-N6` through `geometry` and `from-geometry` equals the hand-written spec of §B.4.1 element by element (positions, thicknesses, materials, field); changing one candidate parameter changes only the corresponding element.

### B1.9 Adapter change procedure

| Item | Content |
|---|---|
| Version | 0.2.0 → 0.3.0 |
| `adapter.json` | `assets` adds `element_sim/`, `simroot/` and the schemas of `element_sim.spec/1` and `element_sim.realization/1`; `purpose` updated |
| `SIM_SOURCES` | Today a flat tuple of file names hashed only under `ASSETS/"layered_sim"` (`geant4_run.py`: defined at line 63, used at lines 327 and 386). Becomes a per-program map `{"layered_sim": [...], "element_sim": [...], "simroot": [...], "g4sim": [...]}`; every run record stores the program used and the file hashes of `g4sim`; the field code lives in `element_sim/Field.hh`, `Field.cc`; `layered_sim`'s hash keys do not change, so old records still compare |
| G5 | Statement "written from the Geant4 API; no example code (including B5) copied or adapted", confirmed by a reviewer in the VALIDATION entry; the same entry notes the ROOT file type and `simroot` |
| Tests | Offline tests (spec validation, cross-field rules, `check-spec`, `from-geometry`); live tests (`HEP_GEANT4_LIVE_TEST=1`): geometry, field, event file, `simroot` round trip; the scan of `adapters/*/assets/*.py` in `tests/skills/test_cli_robustness.py`; `tools/check_wiring.py` |
| Docs | The Geant4 row of `docs/capability-matrix.md`; adapter docs |

### B1.10 B1 acceptance

- [ ] `element_sim`'s J15 geometry passes overlap, material budget and per-event energy balance; the check values of §B.4.1 and §B.4.2 are recomputed by tests.
- [ ] `check-spec` returns exit 2 with the reason for each kind of cross-field error and exit 0 for a valid spec; `check-spec` and `from-geometry` are registered in the extended `MISSING_FILE_ARGS` and pass the missing-file tests.
- [ ] `from-geometry`: the spec derived from the J15 candidate equals §B.4.1 element by element; the same inputs are bit-identical; a missing template or unknown version gives exit 2 (B1.8).
- [ ] Interface consistency of B1.6 and statistical consistency of the two backends (gate G-B1b).
- [ ] Under `per-event`, the same logical run executed with 1, 2, 4 jobs and 1, 2, 4 threads gives identical summary integers and floats within relative 1e-12.
- [ ] The MT test command reports distinct field-manager pointers per thread; the field parameters of every region recorded by the probe agree with the spec; the field counts in the target hash.
- [ ] B1.7's deterministic field check passes at nominal (one region and two regions), every grid point is reported, and the negative control is caught (gate G-B1b).
- [ ] Crossings: rows of secondary charged tracks exist with the correct `parent_id`; the primary's rows equal those of a primary-only recording.
- [ ] Calorimeter leakage: in a simple configuration (electrons on a thin calorimeter), `leak_*_MeV` plus deposits plus energy leaving the world satisfies per-event energy balance.
- [ ] `simroot` round trip: values of I, D, S columns identical at every level; `content_sha256` identical for serial, different thread counts, and 1 versus 4 jobs (`processes` agree after deduplication); `deposits` summed per event equal the CSV subsystem totals; `hits` over the limit gives exit 2; an interrupted run is incomplete.
- [ ] VALIDATION GEANT4-ELEMENT; CHANGELOG; release manifest.

---

## §B.6 Stage B2: reconstruction and the F4 interface (geant4 adapter 0.4.0, contracts CV-B2)

### B2.1 `simreco` (digitization and reconstruction)

**Location:** `adapters/geant4/assets/simreco/` (CMake project; uses only the C++17 standard library and the Geant4-free `SimHash.hh`, `SimSummary.hh`, `MiniJson.hh` of `g4sim`; does not link Geant4). Parameters (ε, σ_t, nominal B per region, calibration samples, tail-source switches and parameters) are written in a reco spec owned by hep-detector; for a study generated by `from-geometry`, `point_resolution_um` comes from the geometry file.

**Input:** the `crossings` and `deposits` extracted from the ROOT file by `simroot dump` (sorted by key, passed through a pipe, not stored) and the summary CSV.

| Step | Content |
|---|---|
| Silicon | Nominal setup: Gaussian errors on the primary's crossing points, ε = 10 µm in the bending direction (y) and 30 µm in the non-bending direction (z); the x used in the fit is the scorer's (entry face). With tail sources on, B2.2's digitization and hit association are used instead |
| TOF | Independent Gaussian error σ_t per layer time (100 ps; 150 ps for the sensitivity); station time = mean of the two layer times (each first transported to the station centre along the fitted track); also outputs per-layer dE/dx and the time difference between a station's two layers |
| Track | Circle fit in the x–y plane with the multiple-scattering covariance (otherwise χ²/dof is in the thousands at 1 GV), giving curvature κ; straight-line fit in x–z giving dip angle λ; R_reco = C·B/(κ cos λ) with the reconstruction B (nominal per region, times that run's scale when B2.2's miscalibration is on) (total momentum, C = 0.2998 GV/(T·m)); a nonzero `curvature_offset_per_GV` is applied as 1/R_reco + offset; outputs R, χ², degrees of freedom, charge sign |
| True rigidity | 1/R_true = mean of \|q\|/p_i over the six plane crossings (**total momentum** p_i; for unit charge 1/R = 1/p); both R_true and R_reco use total momentum, avoiding the p versus p_T difference (about 0.125 % at 50 mrad, larger than the 0.05 % tolerance of the μ field check) |
| β | Path length between the two station centres, including the straight segments TOF1→Si1 and Si6→TOF2 and the 3D inclination; at low β reports the change in β between the stations |
| Calorimeter | Total deposit in the active layers divided by the **electron** sampling fraction; the sampling fraction comes from a 10 GeV electron sample with role `calibration`; also outputs e/mip |
| Random numbers | Each event's digitization stream is SplitMix64 from `SimHash.hh` seeded with H(S, i, "digi") (A1.4's H; S the logical run seed, i the event number); each run's misalignment and field scales are drawn with H(S, "align") and H(S, "fieldscale"); normal deviates by `SimHash.hh`'s Box–Muller; not `std::normal_distribution` (libstdc++ and libc++ differ). Separate from Geant4's streams. Bit-identical on the same platform; across platforms libm functions such as `log` and `cos` differ, so bit identity is not guaranteed and only a relative difference ≤ 1e-12 is required; build with `-ffp-contract=off` |

**Output:** a per-event result CSV (R, χ², charge sign, β, calorimeter energy, etc.) and a run summary (`simulation-summary/1`, producer `simreco`; observables in B2.3).

- **Fitter unit test:** `tracker_resolution.py` does no fit; it computes the curvature resolution from a parabola least squares (`curvature_sigma`, line 89). The test compares, on a toy without multiple scattering (R ≥ 300 GV), the C++ fit's σ(1/R) and pull width with the measurement-term resolution from `tracker_resolution.py momentum` (`mdr_intrinsic_gev`) within the toy's MC error; the pull width within 1 ± 3σ_MC.

### B2.2 Tail sources (switchable reconstruction stages)

Each stage has a switch and parameters in the reco spec; `simreco` writes the stages actually on into the summary's `tail_sources_simulated`, with names equal to `TAIL_SOURCES` in `contracts/design.py:64`. With all off it writes an empty array.

| Tail source | Stage | Parameters (reco spec) | Note |
|---|---|---|---|
| `alignment` | Per run, draw a misalignment per plane (translations in y, z and rotation about x), then subtract a residual model after alignment | Width of the misalignment distribution; width of the residual after alignment; description of the alignment method | Reconstruction fits with the "aligned" positions while the true positions keep the residual; weak modes (e.g. a global curvature offset) are represented by `curvature_offset_per_GV` |
| `calibration-non-uniformity` | Per run, draw a field scale (1 + δ_region) per field region; reconstruction uses the nominal B | Width of the δ distribution | The piecewise-uniform field (B1.2) is the minimal model of this source |
| `noise-digitization` | Strips (pitch), a simplified charge-sharing model, threshold, efficiency, noise hits, clustering and centroid | Pitch, threshold, efficiency, noise rate, clustering rule | Replaces the nominal Gaussian point error; the point resolution results from it instead of being assumed |
| `pattern-recognition` | With the crossings of all charged tracks (B1.3) and noise hits as input, associate hits plane by plane (nearest neighbour plus a χ² cut), then fit | Search window, χ² cut, minimum number of hits | Association errors produce resolution and charge-confusion tails; association failures count toward tracking-selection-efficiency |

- With all four on, the F4 `momentum-resolution-core` and `charge-confusion-rate` are `estimate`, otherwise `optimistic` (`contracts/design.py:1058-1059`). B3.6 demonstrates this transition.
- These models are **synthetic** minimal models with parameters declared by the user and written into the README; they make the declared bound honest and do not represent any experiment's real tails. Charge-confusion compliance still needs data validation and the rigidity-scale offset (adequacy table); F4 alone is never enough for compliance.

### B2.3 Observables for F4

Declared in `simulation-observables/1` (A1.5) and accumulated in `simreco`'s summary:

| Figure of merit | Estimator | Denominator | Uncertainty |
|---|---|---|---|
| `momentum-resolution-core` | Gaussian core width: iterative ±2σ truncated fit of (1/R_reco − 1/R_true)·R_true (definition and truncation parameters written into the study block, field `estimator`) | `rigidity_GV`, `species` | 68.27 % t half-width of the block batch means (A1) |
| `charge-confusion-rate` | Count: fraction of events whose reconstructed charge sign is opposite to the truth (`count_if` and the total) | `rigidity_GV`, `species`, `charge_sign`, `curvature_offset_per_GV` | Exact (Clopper–Pearson) interval, asymmetric (B2.6) |
| `shower-containment` | Mean of 1 − (total leaked energy / incident energy); the rear-leakage fraction is also reported | `energy_GeV`, `species` | t half-width of the block batch means |
| `tracking-selection-efficiency` (optional) | Count: fraction of primaries that pass hit association and the fit-quality cut | `rigidity_GV`, `species` | Exact interval |

- The core estimator differs from the earlier "central 68 % half-width"; both are output, and only the core estimator becomes `results.momentum-resolution-core.value`.

### B2.4 `geant4_run.py reco` and `table`

- `reco`: runs `simroot dump` and `simreco`; each execution writes a computational-run record (with `**trace.provenance()`, `argv`, `script_sha256`, `simreco`'s program hash, the hashes of the input run records and the ROOT files' `content_sha256`, the list of dumped ntuples and columns, the reco spec's hash). Changing digitization parameters or tail-source switches does not require rerunning the simulation.
- `table`: writes reconstructed results (e.g. rigidity resolution against rigidity) as a simulated dataset-record (with `trace.provenance()`); `table --f4-results` also writes an F4 results file (B2.6).
- Exit codes follow `core/status.py`: 0 ok, 1 negative decision, 2 `rejected` (unreadable input, including a missing file), 3 incomplete.
- **CLI registration:** add `reco` and `table` to the `MISSING_FILE_ARGS` extended in B1 (B1.6).

### B2.5 Transitive processing chain

- Today `dependencies.py` requires every input of a simulated table to be a computational-run with `extension.simulation` or `extension.study`; a reconstruction record has neither. CV-B2 changes this to: the input chain may be arbitrarily deep, as long as every level is a recorded computational-run and every root of the chain is a simulation run (needs hep-computing's agreement; §P.7). The existing behaviour of `dependencies.py` for parameter binding (`binding: parameters`, warn only) does not change.
- While the study is `unvalidated`, the table stays `unvalidated`; a communication that uses it gets the `communication.simulated_source` warning, and figures are labelled "Simulation".

### B2.6 F4 interface (CV-B2)

**F4 results file `f4-results/1`** (written by `geant4_run.py table --f4-results`): one entry per figure of merit `{value, statistical_uncertainty | uncertainty, model_envelope, estimator, denominator}`, plus `tail_sources_simulated` and the geometry file's path and sha256. `model_envelope` = [lo, hi] of the per-physics-list results in the variation table (`check_geant4_study.py variations`), with each end's standard error kept in an annotation (`design.py` compares end by end, lines 1310–1316).

**Extension of `check_geant4_study.py label`:** new flags `--results <f4-results>` and `--geometry <design-geometry>`. `label --write` (with or without `--upgrade`) writes the results into `extension.study.results.<fom>` and `extension.study.tail_sources_simulated`, and adds the results file, the geometry file, the realization profile and the derived spec to `input_manifest` (today `label` rebuilds the record from scratch and all of these would be lost: `check_geant4_study.py:584-617`). If the geometry sha256 in the results file differs from `--geometry`, exit 2.

**Changes to `contracts/design.py` and `evaluate_design.py` (need the maintainer's agreement, §P.7):**

| Change | Reason |
|---|---|
| F4 of a counting figure of merit accepts an asymmetric or exact interval (an `uncertainty` object, not only a scalar `statistical_uncertainty`) | Charge confusion is a counting figure of merit (adequacy table `counting: true`); today F4 always writes a symmetric Gaussian (`evaluate_design.py:546-548`; `design.py:1050-1054`) |
| The F4 evaluation records its own `geometry_ref` and `check_f4` reads the evaluation's geometry file; the candidate's `geometry_ref` stays as the most recent one | A candidate has one `geometry_ref`, while each geometry file belongs to one figure of merit and denominator; a second `geometry` call makes earlier F4 evaluations fail on the `input_manifest` check (`design.py:1013-1028`) |
| `check_f4` compares the geometry file's denominator with the evaluation's | Today only the figure of merit is compared (`design.py:1041-1042`) |

If the maintainer does not agree to the second change, B3 keeps only one valid F4 evaluation per candidate at a time and the README says so.

**Geometry mapping 1.1.0 (CV-B2):** `mapping_version` in `contracts/rules/design_geometry.json` becomes 1.1.0 and the enum in `contracts/schemas/design_geometry.json` gains 1.1.0; new fields: material and transverse area of the tracker layers, field-region extent along the stack axis, role `tof` (layer positions, thickness, time resolution), role `calorimetry-em` (front-face position, depth in X₀, sampling structure). Candidates under mapping 1.0.0 keep working (missing fields come from the realization profile).

**What a study must provide for `f4` to accept it (checklist):**

- [ ] The geometry comes from `evaluate_design.py geometry --figure-of-merit F --denominator … --id G`, and `element_sim.spec/1` is derived from `studies/G.geometry.json` through `from-geometry`.
- [ ] The study record's `extension.input_manifest` lists the geometry file (matching sha256), the realization profile and the derived spec (`design.py:1025-1028`).
- [ ] The geometry file's `parameter_digest` equals the candidate's current digest (`design.py:1029-1039`).
- [ ] The geometry file's figure of merit equals the evaluated figure of merit (`design.py:1041-1042`); one study per denominator point.
- [ ] `extension.study.results.<fom>` holds `value`, `statistical_uncertainty` (68.27 % t half-width) or an asymmetric `uncertainty` (counting), and `model_envelope` [lo, hi] (`design.py:1044-1057`).
- [ ] `extension.study.tail_sources_simulated` is a subset of the four sources; all four are needed for `estimate`.
- [ ] The record is re-issued `validated-in-scope` by `label --upgrade` (qualification path of B2.8), and the re-issued record keeps the fields and manifest above.
- [ ] Denominators: resolution {`rigidity_GV`, `species`}; charge confusion {`rigidity_GV`, `species`, `charge_sign`, `curvature_offset_per_GV`}; showers {`energy_GeV`, `species`}.
- [ ] Charge-confusion compliance also needs upstream `charge-confusion-data-validation` and `rigidity-scale-offset` evaluations (adequacy table); F4 alone never makes it compliant.

### B2.7 Validation classes, table entries and `change`

**New benchmark table entries** (A1.1's format; the grade is the class; `GRADES` (`geant4_benchmarks.py` line 92) and the study spec's benchmark and grade enums are extended together; compute functions live in `geant4_benchmarks.py` and read only summaries or `simroot dump`):

| Benchmark | Class | Supported kinds | Scope dimensions | Computed in |
|---|---|---|---|---|
| `field-propagation` | verification | — | field configuration (number of regions, B range) | `field_propagation()`, reads the `crossings` of `simroot dump` and the analytic helix (B1.7) |
| `field-propagation-muon` | sanity | — | — | `field_propagation_muon()`, reads `simreco`'s summary |
| `reco-closure` | verification | — | rigidity, species | `reco_closure()`: with all tail sources off and toy input without multiple scattering, `simreco`'s pull width and bias against the truth (the fitter's integration test, B2.1) |
| `tof-beta` | verification | — | — | `tof_beta()`, reads `simreco`'s summary |
| `tof-layer-consistency` | verification | — | — | `tof_layer_consistency()`, reads `simreco`'s summary |
| `sampling-fraction` | sanity | — | — | `sampling_fraction()`, reads `element_sim`'s summary |
| `multiple-scattering-reference` | **reference** | `tracking-resolution`, `charge-confusion` | material, thickness (X₀), rigidity, species | `ms_reference()`: core width of the projected exit angle in an isolated Si slab (reusing the central-98 % estimator of the existing `multiple-scattering` sanity benchmark, described in the header of `geant4_benchmarks.py`) against the Lynch–Dahl (F = 98 %) formula; the tolerance follows that formula's published accuracy (obtained and checked through hep-citations); if the accuracy is not good enough for a reference, use published multiple-scattering measurements (e.g. MuScat) as `published-data` instead |
| `regression-comparison` | regression | — | — | `regression_comparison()`, reads the summaries of two versions |

- **verification:** does not count toward an upgrade on its own; `field-propagation` and `reco-closure` are conditions of B2.8's qualification path.
- **`multiple-scattering-reference`:** the negative control is slab density or thickness × (1 ± δ), δ chosen from a trial run; turning multiple scattering off is a "gross control" that does not count under the protocol. The existing `multiple-scattering` (sanity, against Highland) is unchanged.
- **regression:** the role enum gains `regression`. The same study and setup run once on each of two versions (plugin, backend or Geant4); the two point_ids are version labels, so S differs and the samples are independent (no violation of A1.4's uniqueness). Only scalar observables are compared (histogram comparison belongs to the distribution-level benchmarks deferred in §B.9). Both versions must be runs from A1 on (both carry S and a summary). The decision is the decision engine's new `change(diff, se, ν, tol, m)`: `changed` = |diff| − t_{1−α/m}·se_diff > tol; `unchanged` = `equivalence` passes; otherwise `unresolved`. Counting observables take the exact-interval branch as `equivalence` does (A1.7). Tolerance and α are declared in advance. The record does not affect the label; a reference observable that is `changed` can trigger a sci-fix check.
- Gating: `strict or _at_least(contract_version, CV-B2)`, no warning branch.

### B2.8 F4 qualification path (D0)

**Problem:** under the protocol, an upgrade needs a passed reference benchmark whose scope covers the study's scope; detector-level observables (resolution, charge confusion) have no reference in A1's table, so such studies can never be `validated-in-scope` and so never count as F4.

**Qualification rule** (the `geant4.upgrade_*` rules of `contracts/validate.py` and the eligibility decision of `check_geant4_study.py`, CV-B2; for studies of kind `tracking-resolution` or `charge-confusion`): upgradable if and only if all of the following hold.

1. **Materials:** the material of every element with matter in the study lies within the scope of a passed A1 material benchmark (stopping-power, thin-layer-mpv, etc.) or within the material scope of `multiple-scattering-reference`.
2. **Field:** the `field-propagation` verification has passed for the same field configuration (number of regions and B range).
3. **Reconstruction:** the `reco-closure` verification has passed for the same reco spec (with tail sources off).
4. **Tracking reference:** `multiple-scattering-reference` has passed with its negative control caught, and its scope (material, thickness, rigidity, species) covers the scope the study declares.
5. A1's other conditions (convergence gate, no remaining gaps, `reference_origin: independent`, variation table) apply as before.

- `shower-containment` and the other calorimeter figures of merit are not on this path: the only reference is the PDG gamma-profile fit (sanity; the header of `geant4_benchmarks.py` says it is never validation), and a published-data reference for leakage is needed (§B.9). J15's shower-containment F4 study therefore stays not upgraded (`f4_unqualified`), and the README says so.
- The rule, conditions and scope dimensions are written into `geant4-study-protocol.md` and the F4 row of `system-design-workflow.md`.
- **While D0 is not approved:** the rest of B2 may merge; the rules of this section (the eligibility decision in `validate.py` and `check_geant4_study.py`) stay on the branch and do not merge (§P.6, §P.7).

### B2.9 Adapter change procedure and CI

| Item | Content |
|---|---|
| Version | 0.3.0 → 0.4.0 |
| `adapter.json` | `assets` adds `simreco/` and the schemas of the reco spec and `f4-results/1`; `purpose` updated |
| `SIM_SOURCES` | Adds a `simreco` group |
| CI | A C++17 CI job builds and tests `simreco` (required or optional decided by the maintainer, §P.7); suggest an impact group for `adapters/geant4/**` in `contracts/rules/registry.json` |
| Docs | Adapter docs, `geant4-study-protocol.md` (validation classes, qualification path, processing chain, `reco`, `table`, F4 results file), the F4 row of `system-design-workflow.md` (`from-geometry`, tail sources, qualification) |

### B2.10 B2 acceptance

- [ ] `simreco`'s fitter unit test passes as in B2.1; `simreco` is built and tested in a CI job (a required job; or, if the maintainer makes it optional, the optional job plus a local build-and-test record).
- [ ] `simreco`'s digitization results are bit-identical on the same platform; relative difference ≤ 1e-12 between Linux (libstdc++) and macOS (libc++) (built with `-ffp-contract=off`).
- [ ] Tail sources: switching on each stage alone changes resolution or charge confusion in the expected direction; `tail_sources_simulated` lists only the stages on, and is empty with all off; the effect of `curvature_offset_per_GV` on charge confusion agrees with the analytic expression (for a Gaussian core).
- [ ] `simreco`'s summary passes the same consistency test as A2.9 (Python recomputes from the per-event result CSV); B2.3's estimators have unit tests (core fit, exact interval).
- [ ] `reco` and `table` are registered in `MISSING_FILE_ARGS` and pass the missing-file tests.
- [ ] A chain of three or more levels (simulation → reconstruction → table) is accepted by `dependencies.py`; one whose root is not a simulation run is refused.
- [ ] The new table entries agree with `GRADES` and the study spec's enums (consistency test); verification classes do not count toward an upgrade on their own.
- [ ] `change` toys: the probability of `changed` at true difference = tol is ≤ α/m + 3σ_MC; report the probability of `changed` at true difference = 2·tol (power) and of `unchanged` at true difference = 0; one regression check (e.g. J14 on two plugin versions) produces a `changed`, `unchanged` or `unresolved` record without affecting the label.
- [ ] `label --results --geometry`: the re-issued record keeps `results`, tail sources and the manifest; a geometry sha256 mismatch gives exit 2.
- [ ] Mapping 1.1.0: the schema, `design.py`'s field reading and `from-geometry` agree; candidates under 1.0.0 still work (main's two examples unchanged).
- [ ] **End-to-end test** (gate G-B2): a small spectrometer candidate → `evaluate_design.py geometry` → `from-geometry` → `element_sim` → `reco` → `table --f4-results` → `label --upgrade --results --geometry` (through A1's `--label-run-record`) → `evaluate_design.py f4` → `report`; refused with the reasons listed when the qualification conditions do not hold; when they hold (after D0 approval) an F4 evaluation results, with bound `optimistic` or `estimate` depending on the tail sources.
- [ ] The asymmetric uncertainty of counting F4 and the evaluation's own `geometry_ref` (if the maintainer agrees) have tests in `contracts/design.py`; main's `tests/contracts/test_design_*.py` and `tests/skills/hep_detector/test_design_m2.py` still pass.
- [ ] J14 still passes under `--strict`; `tools/check_wiring.py` and `tools/scifix_ledger.py report` pass.
- [ ] VALIDATION GEANT4-F4; CHANGELOG; release manifest.

---

## §B.7 Stage B3: the J15 design project

### B3.1 J15's design-spec, candidates, F1 and F2

- Following §B.4.4, write the design-spec `j15-v1`, the candidates `cand-N6`, `cand-N4`, `cand-N8` and the realization profile in `examples/design-minimal-spectrometer/`, in the format of main's `examples/design-space-spectrometer/`.
- For the human gates H1 and H2 the agent prepares the decision records and marks them as needing a human signature (the README notes that in the example they are a demonstration).
- F1: `evaluate_design.py run` for every candidate and requirement (`tracker_resolution`, `multiple_scattering`, `charge_confusion_rate`); `budget` for mass and channel count.
- F2: `toy_spectrometer`'s resolution and `design_estimates.py infield-acceptance`'s acceptance. This replaces the earlier "one-off multiple-scattering comparison": the F1 and F2 values and the hand-computed tables of §B.4.2 are cross-checked (test).
- `evaluate_design.py plan` lists the missing evidence; `report` derives the compliance matrix, screening and comparison basis.

### B3.2 Verification ladder (a separate `unvalidated` record)

The verification ladder is J15's verification carrier, written in a **separate** study record (not an F4 study) that is always `unvalidated`; its verification results are also the evidence for the conditions of B2.8's qualification.

| Check | Class | Reference | Specification | Negative control |
|---|---|---|---|---|
| overlap | implementation | — | — | shift one Si plane to create an overlap |
| per-event energy balance (J15 geometry) | implementation | energy conservation | — | omit 2 mₑc², double counting |
| material budget (geantino) | implementation | sum of PDG X₀ | tolerance about 2 % (Geant4's X₀ formula and PDG differ by about 1 %) | Pb density ± δ |
| `field-propagation` | **verification** | charged geantino against the analytic helix | B1.7 | Geant4-side B × (1 ± δ) |
| `field-propagation-muon` | **sanity** | plane-averaged true 1/R (B2.1) | μ⁻ 1, 10, 100 GV; observable: mean of (1/R_reco − 1/R_true)·R_true; decided by `equivalence` (A1.8), `tolerance_mode: absolute`, tolerance 0.05 % (the observable is already relative); SE target 0.1 %, N from a trial run per A1.9 (estimates: about 400 at 1 GV and 7400 at 100 GV, for SE about 0.07 % and 0.10 %) | Geant4-side B × (1 ± 1 %) |
| `reco-closure` | **verification** | truth | B2.7 | reconstruction B × (1 ± δ) |
| `tof-beta` | **verification** (bookkeeping) | kinematics along the true trajectory | — | a scorer test flag injects a time offset; no physics control on the Geant4 side, stated in the docs |
| `tof-layer-consistency` | **verification** (bookkeeping) | time difference of a station's two layers against "inter-layer path / βc" (66.7 ps for β = 1 at normal incidence) | residual mean 0; width √2 σ_t (141 ps at 100 ps) | a test flag injects an offset into one layer's scorer time |
| `sampling-fraction` | sanity | ratio of ionization dE/dx at the run momentum from PDG's muon energy-loss tables (Groom et al., through hep-citations) | μ⁻ 1 GeV; statistic Σ PVT deposit / Σ (PVT + Pb) deposit; plausible range ±10 % (the reviewer's Bethe estimate about 0.271); different seeds from the `calibration` sample | PVT density ± δ |
| shower containment | sanity | PDG gamma profile, effective critical energy of the mixture about 10.2 MeV | electrons 1–100 GeV; `leak_*_MeV` (B1.3) | — |
| `longitudinal-profile` (0.21.0) | not applicable | its reference is the published ALICE FoCal-E measurement, valid only for that stack; J15's calorimeter differs, and it would be embedded | — | — |

`multiple-scattering-reference` (B2.7) runs in an isolated Si slab (a single `element_sim` element), as a separate study record decided by A1.3's isolation rule; it is the evidence for condition 4 of B2.8's qualification. The optional isolated PVT stopping-power benchmark of the earlier version may still be run, also as a separate record. Event counts and decisions follow A1.6–A1.10.

### B3.3 Calorimeter production-cut convergence

- Grid: 0.1, 0.3, 0.7, 1.0 mm.
- Sample: 10 GeV e⁻; trial run first, then N per A1.9.
- Observables: total deposit (relative tolerance 1 %, about 400 showers per point), rear-leakage fraction (`leak_rear_MeV` over the incident kinetic energy, counting only the back face of the calorimeter mother; **absolute** tolerance 0.002, `tolerance_mode: absolute`, about 5000 showers per point). These two numbers exclude the two-stage factor f ≈ 1.97 (A1.9); with f they are about 770 and 9,900 showers per point.
- Events per point are the larger of the two; decided per A1.8 (`equivalence`); every declared grid point must have a summary (A1's D11).
- Si production-cut convergence is done only for the F4 tracking studies (B3.6), with the core resolution as observable; the Si results of the verification ladder are not evidence. The study spec's `convergence_plan.observables` adds total deposit and rear-leakage fraction. The parameter set each benchmark depends on is declared in advance and checked against the probe's actual settings.

### B3.4 Variations and model envelope

| Variation | Scope | Rule |
|---|---|---|
| EM option4 against option3 | calorimeter profile, sampling fraction | `G4R-PRECISION-EM` |
| EM multiple-scattering model: option0 against option4 (Urban against WentzelVI) | core resolution and charge confusion of the F4 tracking studies | results turned into `model_envelope` (B2.6) |
| FTFP_BERT_EMZ against **QGSP_BIC_EMZ** | nucleons below 1.5 GeV; observables are final-state quantities: deposit in the 5 layers after the first interaction, energy of charged secondaries after the interaction. Interaction probability and first-interaction depth are reported only if the probe confirms the two lists have different inelastic cross sections (the two physics lists may share nucleon cross sections, and then the difference is necessarily 0; the same kind of problem as the "false zero from shared models" warned of in protocol §6 Variations, from line 161, the false-zero warning at lines 166–168) | `G4R-BIC-RANGE`; pions below 12 GeV and nucleons between 1.5 and 12 GeV have the same models in both (protocol lines 166–168) and must not be used as a variation |
| vacuum against air | multiple scattering, rigidity resolution | — |

- Every variation difference carries its standard error; a difference below about 2 SE is not resolved (protocol §6). The envelope goes to hep-statistics as an envelope, not as a σ.

### B3.5 Sensitivity to the TOF time resolution

- `simreco` reconstructs once with σ_t = 100 ps and once with 150 ps (the same simulation, no rerun).
- Report σβ/β for both (expected about 2.3 % and 3.5 %) and the effect of β resolution against rigidity; the README explains that 100 ps is more optimistic than AMS-02's system resolution (about 140 ps).

### B3.6 F4 studies and the tail-source demonstration

- **Splitting the studies:** one study per (candidate, figure of merit, denominator): for `cand-N6`, `momentum-resolution-core` (proton 1 GV, 100 GV), `charge-confusion-rate` (proton, the offset declared in the requirement), `shower-containment` (electron 10 GeV); for `cand-N4` and `cand-N8`, only the 1 GV and 100 GV resolutions. Each study: `geometry` → `from-geometry` → `element_sim` → `reco` → `table --f4-results` → `label --upgrade` (qualification path) → `f4`.
- **Tail-source demonstration:** the same simulation is reconstructed once with all tail sources off and once with all on, as two study records; `f4` gives bounds `optimistic` and `estimate` respectively; the README tabulates the change in resolution and charge confusion.
- **Compliance chain:** the compliance fidelity of resolution is F3: run `evaluate_design.py response` with the F4 core evaluation as upstream; charge confusion stops at `chain.incomplete`, missing `charge-confusion-data-validation` and `rigidity-scale-offset` (listed honestly in the example, no fabricated data); shower containment stops at a not-upgraded F4 (B2.8).
- **Comparison:** `report` derives screening, comparison basis and ranking; without expected-precision evaluations, ranking and Pareto front are refused with every reason listed.
- Convergence (Si production cut, B3.3) and variations (B3.4) follow A1's rules; event counts come from trial runs per A1.9.

### B3.7 Recorded-data budget

- `check_packaging.py`'s per-file limit is 2 MiB (`MAX_BYTES = 2 * 1024 * 1024`, in bytes); J14's `recorded/` totals 2,447,979 bytes (about 2.45 MB; the 2.6 MB shown by `du -h` includes file-system blocks).
- ROOT files are not committed; run records store only path, file sha256, `content_sha256`, row count and size per ntuple; ROOT files needed by tests are generated in live tests.
- J15 commits only: design-spec, candidates, realization profile, geometry files, evaluations, study records, report; run summaries (simulation and reconstruction), effective configs (stored by content hash), column maps, reduced-column summary CSVs, reduced crossing and deposit records extracted with `simroot dump --events` (for the offline `simreco` replay test; the event subset chosen by the budget), reconstructed result tables and F4 results files.
- ≤ 2 MiB per file, ≤ 3 MB in total for J15's `recorded/`.

### B3.8 Registration, journey and docs

| Item | Content |
|---|---|
| Script count | No new hep-detector script; the count test (`DetectorScriptCount` at line 145 of `tests/skills/test_documented_output_claims.py`) stays at 23, and "twenty-three scripts" at line 49 of `docs/capability-matrix.md` is unchanged |
| Routing table | `skills/hep-detector/SKILL.md` unchanged; documentation of `element_sim`, `simreco` and the F4 path goes into `geant4-study-protocol.md`, `system-design-workflow.md` and the adapter docs (the design loop's entry is already a hub link, main's OQ-01) |
| Journey | J15 ("take a spectrometer design from F1 to F4"); `docs/researcher-journeys.md`, the example table of `docs/maintenance.md`; `tests/examples/test_design_minimal_spectrometer.py` (replays and compares `report`'s derived results) |
| Capability | `docs/capability-map.json` and `docs/capability-map.md` (new items under `full-detector-simulation` and `detector-design`, run `capability_map.py --write`), `docs/capability-matrix.md` |
| Routing | Add a J15 routing case; `check_routing_static.py` reads the journey list from `docs/researcher-journeys.md`, so once J15 is listed it **must** have a routing case. Rerun the live Geant4 cases, including the existing Traditional Chinese underspecified case `g4-underspec-2` |
| Description length | Description 1,016 / 1,024 characters; the routing case reuses existing trigger words, the description is not changed |
| README | J15's list of simplifications (§B.4.1), the synthetic nature of the tail-source models (B2.2), the comparison with PAMELA and AMS-02 (§B.4.3), the "synthetic geometry" positioning, which evidence is still missing (B3.6) |
| Independent review | This task's Markdown (protocol changes, J15 README, design report, this part) is reviewed with `review.py` per main's `docs/dev/independent-review-spec.md`; the record is advisory only and, per O04/O14, does not replace the human G5 confirmation |
| Other | `reference_inventory.py --check`, `tools/check_wiring.py`, CHANGELOG, release manifest |

### B3.9 B3 acceptance

- [ ] J15's design-spec and candidates pass `contracts/design.py` (no `design.*` errors); the F1 and F2 evaluations are written by `evaluate_design.py`, and their values agree with the hand-computed tables of §B.4.2 (test).
- [ ] The verification ladder (B3.2) is complete and written as a separate `unvalidated` record; each negative control is caught, or the absence of a control is stated. The `multiple-scattering-reference` record is listed separately.
- [ ] Calorimeter cut convergence (B3.3) and variations (B3.4) are complete, with the decisions and the fraction of incomplete runs recorded in the study record; the model envelope of the tracking studies is in the results file.
- [ ] The 100 and 150 ps TOF σ_t sensitivity is reported.
- [ ] F4 studies (B3.6): after D0 approval, the resolution studies are upgraded through the qualification path and accepted by `f4`; tail sources all off and all on give `optimistic` and `estimate`; charge confusion stops at `chain.incomplete` with the missing upstreams listed; shower containment stops not upgraded, with the reason; `report`'s derived results agree with the README. While D0 is not approved, `f4`'s refusal reasons are recorded in the README and this item is accepted as "refused correctly".
- [ ] Recorded budget, registration items and docs all complete; J15's offline replay test passes.
- [ ] An independent agent completes "the rigidity resolution of 1 GV protons in J15" using only the docs and tools: produces an F1 evaluation and an F4 study through `evaluate_design.py`, the study record passes `validate.py --strict`; the core resolution falls within the 1 GV proton row of §B.4.2's multiple-scattering table (1.8–2.6 %, the measurement term is negligible at 1 GV; the core estimate may be slightly below the central 68 % half-width, and both are reported); no maintainer help needed.
- [ ] VALIDATION GEANT4-J15; CHANGELOG; release manifest.

---

## §B.8 Contracts and versions

| Object | Location | Version |
|---|---|---|
| `element_sim`, `element_sim.spec/1`, `element_sim.realization/1`, `element_sim.events/1`, `simroot`, `check-spec`, `from-geometry` | geant4 adapter | 0.3.0 (B1) |
| `simreco`, reco spec, tail sources, `reco`, `table`, `f4-results/1` | geant4 adapter (C++, does not link Geant4) | 0.4.0 (B2) |
| verification, regression and tracking-reference classes and table entries; regression role; transitive processing chain; F4 qualification rules | `contracts/validate.py`, `contracts/dependencies.py` | CV-B2 (minor, gated; qualification rules pending D0) |
| uncertainty of counting F4, the evaluation's own geometry file, denominator comparison; geometry mapping 1.1.0 | `contracts/design.py`, `contracts/rules/design_geometry.json`, `contracts/schemas/design_geometry.json` | CV-B2 (minor; needs the maintainer's agreement) |
| `label --results --geometry` | `skills/hep-detector/scripts/check_geant4_study.py` | with the plugin version |
| decision engine `change` | `core/stats/decisions.py` | `CORE_VERSION` minor |
| `GRADES` and the study spec's enums; `convergence_plan.observables` adds total deposit and rear-leakage fraction | hep-detector | with the plugin version |

---

## §B.9 Not done and deferred

| Item | Decision | Reason / trigger |
|---|---|---|
| σ(1/R) in the measurement-dominated regime as a benchmark | not done | replaced by the fitter unit test and `reco-closure` |
| `skills/hep-detector/scripts/digitize_reconstruct.py` | not done | replaced by the C++ `simreco` |
| surrogate class and `surrogate-comparison` | not done | main's fidelity and bound model already covers approximate evaluations; task C's search values are not evaluations (§C) |
| new geometry features in `layered_sim` | not done | new features go only into `element_sim` |
| Python reading ROOT directly in the pipeline (uproot) | not done | through `simroot` |
| F4 qualification of calorimeter figures of merit | deferred | needs published leakage or profile data as a `published-data` reference; trigger: the first design that needs calorimeter F4 compliance |
| ion sources and Birks visible energy | deferred | for cosmic-ray nuclei studies, and PVT's Birks constant has a literature record. When implemented, per 11.4.3: get the ion with `GetIon(Z, A)` in `GeneratePrimaries`; set kB in `Construct` (`GetIonisation()->SetBirksConstant`), call `G4EmParameters::Instance()->SetBirks(true)` in PreInit, then obtain it with `G4LossTableManager::Instance()->EmSaturation()` (check API names against the 11.4.3 source when implementing) |
| non-box solids, rotations, GDML import, field maps, fringe fields in `element_sim` | deferred | the first study that needs them and cannot use a user application; the extension point is "geometry kind → realizer" (Part 5): a new geometry kind adds a mapping table and a realizer |
| primary exit record in `element_sim` (J14's observables) | deferred | when J14 migrates to `element_sim` and `layered_sim` is retired (§P.8) |
| distribution-level benchmarks (including regression histogram comparison), combinations of observables, profiles, `gps` and `event-file` sources, `simreduce` | deferred (interfaces defined in §R.9.2) | each one's first use case |
| RNTuple, vector columns | deferred | when ROOT file size or read speed becomes a bottleneck |
| real alignment algorithms, Kalman filter, full pattern recognition | deferred | B2.2's minimal models are enough to make the bound honest; the first study that needs realistic tail shapes |

Other items not done or deferred are in §A.9.

---

## §B.10 Open decisions and residual risks

**Open decisions** (numbers in §P.7): D0 (F4 qualification path); how G5 is confirmed; the transitive processing chain and the classification of CV-B2; the CI job for `simreco`; storage of ROOT files; maintenance ownership of `element_sim`; the three F4 changes to `contracts/design.py` (B2.6).

**Residual risks:**
1. The sampling-fraction reference needs PDG's muon energy-loss tables; `multiple-scattering-reference` needs the published accuracy of the Lynch–Dahl formula; the optional PVT benchmark needs the Sternheimer parameters. All must be obtained with a literature record through hep-citations before use; if the Lynch–Dahl accuracy is not enough, use published measurements instead (B2.7).
2. Calorimeter showers dominate CPU time; rear-leakage convergence needs about 5000 showers per point (about 9,900 with the two-stage factor); event counts come from trial runs and are recorded.
3. The read capability of `G4RootAnalysisReader` is unverified (gate G-B1a).
4. ROOT files of large samples can reach hundreds of MB; recording the crossings of every charged track roughly doubles the size; under MT merging the workers' data may accumulate in memory until the end of the run (actual behaviour depends on 11.4.3's ntuple merging and basket settings, not checked); `hits` has an event limit, and size and memory are confirmed in the trial run.
5. Maintenance cost of two Geant4 programs; duplication controlled through `g4sim` (§P.8).
6. Hadronic variation: if the two physics lists have the same nucleon inelastic cross sections, the interaction probability does not change; only final-state quantities are reported (B3.4).
7. Some Geant4 behaviour (stepper construction, the Birks API, the direction of the intersection error) relies on the reviewers' experience and was not checked line by line against the 11.4.3 source; check before implementing.
8. Effort is estimated at the start of B1 from the actual `g4sim`.
9. Task A's residual risks (independence of blocks, decisions near the threshold, the probe assuming worker and master settings are the same) apply as well, see §A.10.
10. **D0 not approved:** detector-level studies cannot become F4, and B3 can only demonstrate the refused path; `element_sim` and `simreco` remain simulation tools below F4, but the figures of merit that main's adequacy table can only screen or decide at F4 remain `capability.unavailable`.
11. **Main's design loop changes fast** (3.5.0 to 3.12.0 in about two days): `contracts/design.py`, `evaluate_design.py` and `design_geometry.json` are shared files; rebase and rerun main's design tests before B2 starts and before it merges.
12. The minimal tail-source models could be misread as an experiment's real tails; the README and the report both state that they are synthetic.

---

## §B.11 Suggested order of work

At the start of each stage, create and confirm its isolated worktree per §P.10.2; every step happens in it; remove it after the merge per §P.10.5.

**B1**
1. Pre-start checks (§B.0); one-day trial of `G4RootAnalysisReader` (gate G-B1a).
2. `element_sim`'s spec, schema, `check-spec` and geometry (B1.1, B1.6); consistency of the two backends with the same slab configuration as J14.
3. Field (B1.2, including regions) and the MT test; deterministic field check (B1.7).
4. Build the J15 geometry (§B.4.1); pass overlap, material budget, energy balance; recompute the check values of §B.4.1 and §B.4.2 in tests.
5. Plane crossings of every charged track and calorimeter leakage (B1.3), ROOT file (B1.4), `simroot` (B1.5).
6. `from-geometry` and the realization profile (B1.8); check with the J15 candidate.
7. Adapter change items of B1.9; tick all of B1.10; run the checks of §A.8.

**B2**
1. `simreco`'s fitter unit test, then connect `simroot dump` input (B2.1); CI job.
2. Tail sources (B2.2) and F4 observables (B2.3).
3. `reco` and `table`, the `MISSING_FILE_ARGS` extension (B2.4); transitive processing chain (B2.5).
4. F4 interface: `f4-results/1`, `label --results --geometry`, mapping 1.1.0, the `design.py` changes (B2.6).
5. Validation classes, table entries, `change`, regression role, `multiple-scattering-reference` and contract tests (B2.7).
6. Qualification path (B2.8): stays on the branch until D0 is approved.
7. End-to-end test (gate G-B2); adapter change items of B2.9; tick all of B2.10; run the checks of §A.8.

**B3**
1. J15's design-spec, candidates, realization profile; F1, F2 and `report` (B3.1).
2. Run the verification ladder and `multiple-scattering-reference` on E2 (B3.2).
3. Calorimeter cut convergence, variations and envelope, TOF sensitivity (B3.3–B3.5).
4. F4 studies and the tail-source demonstration (B3.6).
5. Recorded data, registration, journey, docs, the independent-agent acceptance task (B3.7–B3.8); tick all of B3.9; run the checks of §A.8.

---

## §B Appendix A: numbers

Program: `j15_design_estimates.py` (this folder; standard library only, scipy optional; A_N's closed form checked against exact rational least squares).

**Geometry**
- Si centres: −500, −340, −180, −20, 140, 300 mm; L = 0.800 m.
- Field region: −520 … 320 mm; margins 19.85 mm at both ends.
- TOF1 layers −810 … −800, −790 … −780; TOF2 layers 490 … 500, 510 … 520; station-centre distance D = 1.300 m; world ±1200 mm.

**Tracker**
- A_N = 720 (N−1)³ / [(N−2) N (N+1)(N+2)]: A₄ = 81.0, A₆ = 66.96, A₈ = 57.17 (N equally spaced points including both ends, equal weights).
- MDR (measurement term only) = C B L² / (ε √A_N): 1172 GV with C = 0.2998 (1173 GV with C = 0.3).
- Multiple-scattering term (β = 1, with log): 1.34 %, bracketed by the factor 1.0–1.4.

The table below is printed by `j15_design_estimates.py` (fixed lever arm L, equally spaced planes; MDR ∝ B/√A_N; the multiple-scattering term ∝ 1/B and varies with the total thickness N × 0.3 mm through Highland with log; rigidity where the two terms are equal = multiple-scattering term × MDR):

| B (T) | N | MDR (GV) | Multiple-scattering term (β = 1) | Rigidity where the two terms are equal |
|---|---|---|---|---|
| 0.15 | 6 | 352 | 4.5–6.2 % | 16–22 GV |
| **0.5** | **6** | **1172** | **1.3–1.9 %** | **16–22 GV** |
| 1.0 | 6 | 2345 | 0.7–0.9 % | 16–22 GV |
| 0.5 | 4 | 1066 | 1.1–1.5 % | 11–16 GV |
| 0.5 | 8 | 1269 | 1.6–2.2 % | 20–28 GV |

**Field-check grid** (50 mrad, against the bending, positive charge):

| Rigidity | Max \|y\| in field | y at Si1 … Si6 (mm) | y at TOF2's two layers |
|---|---|---|---|
| 0.6 GV | 29.0 | 25.0, 29.0, 26.6, 17.8, 2.5, −19.3 | −50.0, −53.2 |
| 1 GV | 32.4 | 25.0, 30.6, 32.4, 30.3, 24.4, 14.6 | 0.2, −1.4 |
| 10 GV | 60.7 | 25.0 … 60.0 | 67.1, 67.9 |
| 100 GV | 65.5 | 25.0 … 64.5 | 73.8, 74.8 |
| 1000 GV | 66.0 | 25.0 … 65.0 | 74.5, 75.5 |

If the direction is the same as the bending (−50 mrad): y at Si6 is −151 mm for 0.6 GV and −116 mm for 1 GV, both missing Si6. At normal incidence (0 mrad), 0.6 GV gives y ≈ −85 mm at Si6 and ≈ −126, −130 mm at TOF2's two layers, still within acceptance (printed by `j15_design_estimates.py`).

**TOF**: σ_station = σ_layer/√2, σβ/β = σ_layer c / D; 80, 100, 150 ps per layer give 1.8 %, 2.3 %, 3.5 % (2.6 %, 3.3 %, 4.9 % with one layer per station). Flight time between a station's two layers for β = 1 is 66.7 ps, and the resolution of the two-layer time difference is √2 σ_layer (141 ps at 100 ps).

**Calorimeter**: 18.41 X₀, 0.886 λ_I, 35 cm; effective Molière radius 3.95 cm; the mip energy-loss ratio 0.284 is only a ratio of dE/dx_min and is **not** a reference value.

**Material in front of the calorimeter**: 11.32 % X₀ (four TOF layers 9.40 %, i.e. 83 %; Si 1.92 %), 5.46 % λ_I; of this, TOF1 is in front of the tracker, 4.70 % X₀.

**Event counts** (se of the difference ≤ tol/4, without the two-stage factor): 10 GeV electron total deposit (tolerance 1 %) about 392; rear leakage (absolute tolerance 0.002) about 5000. With the two-stage factor f = F_0.90(15,15) ≈ 1.97, about 770 and 9,900.

## §B Appendix B: sources

- PDG Atomic and Nuclear Properties (retrieved 2026-10-21): [Silicon](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/silicon_Si.html), [Lead](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/lead_Pb.html), [Polyvinyltoluene](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/polyvinyltoluene.html)
- PDG Review of Particle Physics 2024, chapter 34: Eqs. 34.5, 34.12, 34.16, 34.34–34.36 (equation numbers per the plugin's VALIDATION GEANT4-STUDY)
- Geant4 v11.4.3 source, for the field and event files: `G4FieldManager.hh`, `G4ChordFinder.hh`, `G4PropagatorInField.cc`, `G4FieldParameters`, `G4LogicalVolume`, `G4ChargedGeantino.cc`, `G4VAnalysisManager.hh`, `G4EmSaturation`, `G4LossTableManager`, `G4IonTable`, `G4NistMaterialBuilder.cc`
- Geant4 Book for Application Developers, [Basic Examples](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Examples/BasicCodes.html) (B4, B5)
- hep-research `main` `5584927`: `skills/hep-detector/references/system-design-workflow.md`, `contracts/design.py` (`check_f4` lines 988–1062, `TAIL_SOURCES` line 64), `skills/hep-detector/scripts/evaluate_design.py` (`geometry` line 462, `f4` line 498), `contracts/rules/design_geometry.json`, `contracts/rules/design_adequacy.json`, `examples/design-space-spectrometer/`, `skills/hep-detector/references/geant4-study-protocol.md` (§6 lines 161–168)
- Sources for PAMELA and AMS-02 are in §R.14
- To obtain: PDG's muon energy-loss tables (Groom, Mokhov & Striganov); Sternheimer, Berger & Seltzer (1984), *Atomic Data and Nuclear Data Tables* 30, 261; Lynch & Dahl (1991), *Nucl. Instrum. Methods B* 58, 6 (multiple-scattering width formula and its accuracy); published multiple-scattering measurements (e.g. MuScat)

## §B Appendix C: version history

| Version | Content |
|---|---|
| Detector document and v5 | Single-axis stacked spectrometer; correction of the Gluckstern small-N formula; field direction and field-check grid |
| 2026-10-22 | Two layers each for TOF1 and TOF2; digitization and reconstruction moved to C++; per-event ROOT file; split out as task B; rewritten for the new architecture (`element_sim` replaces spec/2; B1, B2; PAMELA and AMS-02 comparison and TOF sensitivity) |
| 2026-10-23 | Fixes after independent review (B1.6 compares only common observables, calorimeter leakage, table entries, surrogate and regression rules, total-momentum rigidity, CLI and `SIM_SOURCES`, portable random numbers, explicit stepper construction, etc.) |
| 2026-10-23 | Reorganized per the plan (Part 1): B2 split into B2 (reconstruction and contracts) and B3 (J15 study); deterministic field check moved to B1.7; `geant4_run.py check-spec` added; the decision engine's `change` and the regression role added in B2 |
| 2026-10-23 | Isolated-worktree execution rules added: header, first step of §B.0, start of §B.11 (§P.10) |
| **2026-10-24 (this version)** | **Re-planned against main 0.38.0's design loop (findings B1–B12 of the review record `review-2026-10-24-main-0.38.md`): task B becomes main's missing F4 evaluator; B1 adds `from-geometry` and the realization profile, crossings of every charged track, a piecewise-uniform field; B2 adds switchable tail sources, F4 observables, `label --results --geometry`, `f4-results/1`, mapping 1.1.0, the F4 changes to `design.py`, the F4 qualification path (D0) with `multiple-scattering-reference`, the end-to-end test, and drops the surrogate class; B3 becomes the J15 design project (F1, F2, F4) with the verification ladder as a separate record; fidelities use main's F0–F5; the contract change is named CV-B2; VALIDATION entry GEANT4-F4; facts corrected (`MISSING_FILE_ARGS` line 153, script count 23, benchmark function lines, model ranges of protocol §6)** |

---

# Part 4 — Task C: automated candidate generation (§C)

> Order: C1 is based on main (independent of tasks A and B); C2 after B2 and C1 (F4 confirmation also needs approval of D0 in §P.7); C3 after C2
> Date: 2026-10-24 (re-planned on the detector system design loop of main 0.38.0)
> In one sentence: add `evaluate_design.py search` to the D2 stage of main's design loop to generate candidate designs automatically; the search only proposes candidates, while verdicts, screening, comparison and the Pareto front are always derived by `contracts/design.py`, and reported performance comes only from F4 confirmation studies

---

## §C.0 Task card

**Goal.** Under the user's design-spec, let the AI choose the kinds and number of subsystems and tune their parameters by itself, generate candidate designs worth evaluating automatically, and hand the few finalists to main's design loop for evaluation, verdicts and comparison; refine with Geant4 search values and confirm with F4 studies on independent seeds. The results stand up to statistical and provenance checks and never claim a global optimum.

**Three stages:**

| Stage | Content | Prerequisites | Versions |
|---|---|---|---|
| **C1** F1 search | Search spec, realization rules per role and the materials table, genome and decoder (emitting overrides of a design-candidate), F1 search values computed in-process through the tool contracts, a standard-library searcher (Sobol, NSGA-II, hypervolume), `evaluate_design.py search` and `search_summary`, `expand --search`, closure tests, workflow docs | main (0.38.0) | contracts **CV-C1** (minor) |
| **C2** Geant4 search values and F4 confirmation | Paired mode and the `values` accumulator in `core/`; Geant4 search values from short `element_sim` runs; paired comparison in the search; F4 confirmation studies of the finalists; the seed rule | B2, C1; F4 confirmation needs D0 | geant4 adapter **0.5.0**, contracts **CV-C2** (minor) |
| **C3** Examples | J16: run the search on Example A (space spectrometer) and Example B (collider tracker + ECAL); optional Bayesian-optimisation backend | C2 | optional `adapters/design-bo/` **0.1.0** |

**Out of scope:** writing or deriving verdicts, rankings, Pareto fronts or a "recommended design" (derived by `contracts/design.py`); claiming a global optimum; differentiable simulation and differentiable surrogates (§C.9); non-box geometry for Geant4 search values; optical physics; reinforcement learning; cost as an objective.

**Deliverables:** the `search` subcommand of `evaluate_design.py` and `expand --search`; `contracts/schemas/design_search_spec.json` and `search_summary` in `ext_computational_run.json` (CV-C1); `skills/hep-detector/assets/design-search/` (realization rules per role, materials table, Sobol direction numbers); paired mode and `values` in `core/` (C2.1); the seed rule in `contracts/design.py` (CV-C2); a "D2 automated candidate generation" section in `system-design-workflow.md`; closure tests; J16; VALIDATION entries DESIGN-SEARCH-F1 (C1), DESIGN-SEARCH-G4 (C2), DESIGN-SEARCH-EXAMPLES (C3); CHANGELOG; release manifest.

**Definition of done:** every box in the acceptance checklists C1.10, C2.9, C3.4 ticked; all checks of §A.8 pass; gates G-C1, G-C2a, G-C2b, G-C3 (§P.6) pass.

**Main decisions:**
1. **The search only proposes candidates; it gives no verdicts.** Verdicts, screening, comparison basis, ranking and Pareto front are derived only by `contracts/design.py` (`system-design-workflow.md` lines 3–4, 149–150, 203–207); the search writes no `verdict`, ranks nothing, has no "recommended design" and never claims a global optimum.
2. **The search is a D2 candidate generator.** Its inputs are the current design-spec and a base candidate; the population (order 10⁴) exists only in the `search_summary`, and only finalists produced by `expand` become design-candidates, which are then handled like any candidate with `evaluate_design.py run`, `budget` and `report` (RSK-04: only points that enter comparison are expanded).
3. **Fidelity names are main's.** In-process F1 is main's F1 tool contract; values from short Geant4 runs are **search values**, have no fidelity and are never evaluations; confirmation is an F4 study on independent seeds.
4. **Search and confirmation are separate.** Search values suffer the "winner's curse" and are used only for selection; numbers reported outside come only from evaluations written by `evaluate_design.py`, and Geant4 performance comes only from F4 confirmation studies (§C.4.8).
5. **Free combination, but within the roles.** Structural freedom comes from "`subsystem_roles` × realization rules per role": any combination that passes the validity rules is a legal candidate; new roles or realization rules enter through a reviewed change (§C.4.5).
6. **Claude is the designer, not the judge.** Claude writes the design brief, seed designs and search ranges; its proposals take the same evaluation pipeline as randomly generated candidates, their parameters carry `source` `proposal`, and they are flagged in the `search_summary`.
7. **Standard library only is a deliberate choice.** The core dependencies already allow numpy and scipy (`requirements-core.txt`); the searcher is written with the standard library for bit-for-bit reproducibility and dependency-free runs, not because of a constraint.

**First step:** create the isolated worktree for this stage per §P.10.2 (`.claude/worktrees/geant4-<stage>`, branch `worktree-geant4-<stage>`, based on the latest `origin/main` that contains the prerequisite stages), and confirm `git rev-parse --show-toplevel`, `git branch --show-current`, `git status` and that the merge commits of the prerequisite stages are ancestors of `HEAD`. Every step below happens in this worktree.

**Before starting:** read §P.0–§P.6; read all of `skills/hep-detector/references/system-design-workflow.md` and `orphan_runs`, `effective`, `effective_digest`, `check_f4`, `ranking`, `pareto` in `contracts/design.py`; read `run_evaluation`, `scan`, `expand` in `evaluate_design.py`. For C2 also read §A.3, §A.4, A1.4–A1.9, §B.4, B1.1, B1.6, B2.1, B2.4 and the F4 qualification path (D0 in §P.7). Check the facts cited in this part with the method of §A Appendix C.

---

## §C.1 Terms and files

| Term | Meaning |
|---|---|
| design-spec, design-candidate, design-evaluation | main's three design artifacts (from contracts 3.11.0); requirements, candidates and evaluations use them, and this task defines no format of its own |
| Base candidate | The starting point of the search; decoded candidates name it in `derived_from` and list only `overrides` (except topologies that drop a subsystem, §C.4.5) |
| Search spec | `design-search-spec/1`: the referenced design-spec and base candidate, objectives and constraints (figure-of-merit ids and denominators), free parameters and ranges, role slots, budget, optimizer settings, seed, stopping rule; hashed before the first evaluation |
| Realization rules per role | For each `subsystem_roles` role, the parameters the search may change, their ranges, units, calibration template and budget model; shipped in `skills/hep-detector/assets/design-search/` |
| Genome | The searcher's internal encoding: slot enable bits, role, `parent_slot`, categorical, integer and continuous parameters; exists only inside the searcher |
| Decoder | The deterministic function genome → design-candidate (overrides on the base candidate) |
| Search value | An objective value computed during the search: in-process F1, or a short Geant4 run in C2; used only for selection and never written as an evaluation |
| Fidelity F0–F5 | main's definition (`contracts/design.py:65`): F0 heuristic, F1 analytic tool contract, F2 toy MC, F3 response and expected precision, F4 Geant4 study re-issued `validated-in-scope`, F5 measurement |
| `search_summary` | The block (CV-C1) of the search run (`runs/SEARCH-*.computational-run.json`): design digests, search values, search front, hypervolume, search size, proposal flags, finalists |
| Search front | The non-dominated set on search values; non-binding, not main's Pareto front |
| Finalists | The few designs fixed at the end of the search and turned into design-candidates by `expand` |
| Confirmation study | The F4 study of a finalist, with seed S = H(search_id, "confirmation", design_sha256), never used in the search |
| Winner's curse | Selecting the best of n noisy evaluations gives an estimate that is optimistic in expectation |
| Search size | The number of distinct designs and topologies actually evaluated; written to the `search_summary`, like a look-elsewhere count |
| seed_group, paired comparison | A set of Geant4 search runs sharing S; the SE of a difference is estimated from per-block differences (common random numbers; C2.1) |
| Notation | "C1.3" is a work item of this part; "A1.8", "B2.1" are work items of tasks A and B (work-item numbers are unique in the whole document); "§C.4" is a section of this part; "§A.3", "§P.7", "§R.6" etc. are sections of other parts of this document |

**Main files (relative to `plugins/hep-research/`):**
- `skills/hep-detector/scripts/evaluate_design.py` (new subcommand `search`; `expand` accepts `--search`).
- `skills/hep-detector/assets/design-search/` (new: `roles.json` realization rules per role, `materials.json` materials table, `sobol_joe_kuo.txt` direction numbers).
- `contracts/schemas/design_search_spec.json` (new), `contracts/schemas/ext_computational_run.json` (`search_summary`), `contracts/design.py` (exemption in `orphan_runs`; the CV-C2 seed rule).
- `skills/hep-detector/references/system-design-workflow.md` (one new section).
- C2: `core/stats/decisions.py`, `core/stats/batch_means.py`, `core/simulation/summary.py`, `core/simulation/seeds.py` (paired mode, `values`, seed_group); `adapters/geant4/assets/g4sim/SimSummary.hh` (`values`).

---

## §C.2 Prerequisites and provided interfaces

| Provider | Interface | Use in task C | Needed in |
|---|---|---|---|
| main | design-spec (REQ, denominators, allocations, `comparison_basis`, `pareto_axes`) and H1, H2 | Objectives and constraints only reference the design-spec's requirements and figure-of-merit ids of `design_adequacy.json`; a requirement change is a new spec version + a `requirement-change` record | C1 |
| main | design-candidate (`DES-*` subsystems, `subsystem_roles`, `derived_from` + `overrides`, parameter `source`/`status`, subsystem `calibration`, `budgets`) | The decoder's output format; dedup by `effective_digest` | C1 |
| main | F1 tool contracts (`tracker_resolution`, `multiple_scattering`, `charge_confusion_rate`, `pid_separation_power`, `cherenkov_angle`, `calorimeter_resolution`, `design_estimates`) and the argument recomputation of `run_evaluation` | In-process F1 search values: computed by the same tool with the same arguments (C1.4) | C1 |
| main | `scan`/`expand` and `scan_summary` (`evaluate_design.py:754-875`; `orphan_runs` exempts `scan_summary`, `contracts/design.py:1655-1683`) | `search_summary` follows the same pattern; `expand --search` generalises `expand` | C1 |
| main | `run`, `budget`, `report`, `plan`; verdicts, screening, ranking, Pareto (`contracts/design.py:1369-1508`, `1949-2051`) | Official evaluation and comparison of the finalists | C1 |
| main | `geometry` → study → `f4` (`evaluate_design.py:462-560`; `contracts/design.py:988-1062`) | F4 confirmation of the finalists | C2 |
| main | `run_workflow.py --incremental`, `parameter_digest` | Reruns of the finalists' evaluation chains | C2 |
| Task A | `core/simulation/seeds.py` (H, S), `summary.py`, `simulation-observables/1`, `core/stats/batch_means.py`, `equivalence` in `decisions.py`, two-stage event counts (A1.9), `extension.simulation.evidence_role` (A1.4) | Seeds, estimates and roles of Geant4 search values | C2 |
| Task B | `geant4_run.py from-geometry` (B1), `element_sim`, `simreco`, `reco`, `results` and `tail_sources_simulated` written by `label`, mapping 1.1.0, B2's change decision `change` (B2.4) | Geant4 search values; F4 confirmation studies | C2 |
| §P.7 | D0: the qualification path by which detector-level studies become F4 (implemented in B2) | Whether confirmation studies can be upgraded to `validated-in-scope` | C2 |

**Interfaces provided to other tasks:** `search_summary` and `expand --search` (any automated or manual candidate generator can reuse them); the paired mode and `values` accumulator of C2.1, usable by any study (e.g. a convergence gate can declare paired mode).

---

## §C.3 Hard rules

The rules of §A.3 and §B.3 that apply to this part all apply. In addition:

1. **No verdicts.** The search and its outputs never write or change a verdict, maturity, stale marker, `screened_out`, `at-risk`, ranking or Pareto front; they never claim a global optimum (the "Never" section of `system-design-workflow.md`).
2. **Search values are not evaluations.** Search values exist only in the `search_summary`; the population is not written to the artifacts_dir as design-candidates; only finalists from `expand` become candidates. Any performance number reported outside must cite a design-evaluation.
3. **One official implementation per quantity.** In-process F1 search values are computed by the same tool with the same arguments as the tool contract (import the tool script and call its `main(argv)`, C1.4), with no formula of our own; a consistency test compares in-process values with those of `evaluate_design.py run` (C1.10).
4. **Pre-declaration.** The search spec, the hashes of the design-spec and the base candidate, the versions of the role rules and the materials table, the budget, the optimizer settings and the seed are written to the `search_summary` before the first evaluation; any later change is a new search (a new SEARCH id). Requirement changes follow main's rule (a new design-spec version + a `requirement-change` record).
5. **LLM proposals have no privilege.** Designs proposed by Claude go through the same decoding, validity and evaluation pipeline as random designs; their parameters carry `source` `proposal` and are flagged `proposer: llm` in the `search_summary`; Claude may not modify any output.
6. **Cost is not an objective.** Cost has no evaluator on main (`capability.unavailable`); mass, power, channel count and data rate enter only through the candidate's `budgets` and main's budget figures of merit, and the budget rows the search generates from the role rules are marked `basis: estimate` with a source that names the assumed model.
7. **Standard library only** (a deliberate choice, §C.0 decision 7). Bayesian optimisation lives only in the optional `adapters/design-bo/`, loaded by lazy import; the search still runs without it.
8. **Experiment names** appear only in `docs/` and example READMEs; role rules use generic names; documents cite the studies of §C.4.1 only by citation key (e.g. `Cisbani2020`), never by names such as EIC or ePIC (the experiment-name scan checks this).
9. **No new reference and no change to `skills/hep-detector/SKILL.md`.** The entry to the design loop was decided as a hub link (OQ-01 in CHANGELOG 0.37.0); this task only adds a section to `system-design-workflow.md`.
10. **Human gates are not replaced by the search.** The search need not wait for H1, H2, but `report` shows the gate flags as usual; finalists entering convergence (H3) and the baseline (H4) still need human records.
11. Contract rules are gated by `strict or _at_least(contract_version, CV-C1)` (`search_summary`) and `CV-C2` (the seed rule).

---

## §C.4 Design

### §C.4.1 References and lessons from practice

| Study | Approach | Lesson adopted here |
|---|---|---|
| `Cisbani2020` (JINST 15 (2020) P05009) | 8 parameters; objective π/K separation (harmonic mean at two momenta); Geant4 with 2.5 % noise; Gaussian-process Bayesian optimisation, 20 designs in parallel per call, converging in about 55 calls; better than the original design (3.23 vs 2.9); tolerance intervals from the posterior (numbers to be checked against the paper) | Model the noise explicitly; parallel batches; results are "simulation only" and need higher fidelity and prototype confirmation |
| `AID2E2024` (arXiv:2405.16279) | Multi-objective Bayesian optimisation (qNEHVI, Ax/BoTorch) and NSGA-II; 7 parameters, 200 evaluations, converging in 150; closure test on DTLZ2 with a known Pareto front; distributed execution | Multiple objectives; MOBO for ≤ 4 objectives, a genetic algorithm for more or discontinuous ones; closure tests first; geometric constraints checked before simulation |
| `MODE2022`, `MODE2023` (arXiv:2203.13818, 2310.05673) | End-to-end differentiable optimisation; differentiable surrogates; a utility with physics objectives and cost | Optimise for the experiment's goal, not each subsystem separately; surrogates can steer the design into bias and must be confirmed with full simulation |
| `AIDO2025` (arXiv:2502.02152) | Thicknesses and materials of a sampling calorimeter (numbers to be checked against the paper); materials as categorical variables; cost and length limits; rediscovers known calorimeter principles | Categorical choices can enter the search; "rediscovering known principles" is a reasonable first acceptance |
| `Borysov2024` (EPJ Web Conf. 315, 03006) | Semi-analytic model (checked against Geant4) + genetic algorithm with non-dominated sorting | Screen with an analytic model, check with Geant4: main's F1 → F4 |
| `SWGO2023` (arXiv:2310.01857) | Differentiable optimisation of the positions of order 10³–10⁴ units; utility = flux precision + energy resolution + pointing resolution + area cost | The utility weights are a declared choice; some terms push the design to extremes and need checking |
| `GRACE2026` (arXiv:2602.15039) | An LLM agent builds simulations from natural language or papers and explores design variants; physics checkers and provenance | Validate the geometry before simulating; the agent noticed anomalies but did not follow them up; engineering constraints ignored |
| `VIBRATO2026` (arXiv:2604.21804) | An LLM agent drives a two-level DD4hep/Geant4 scan and reaches the optimum of a 2255-point grid in 46 runs | Agents are good at decomposing problems and steering scans; conclusions need independent checks, and feasibility still needs an expert |

Summary: in no real case does an LLM declare "the best" by itself; every successful approach is "explicit objectives and constraints + reproducible evaluation + a recorded optimizer + confirmation with full simulation". main's design loop already provides the first two and the place for confirmation (F4, H1–H4); this task adds "a recorded optimizer" and "statistical protection from search to confirmation".

### §C.4.2 Place in main's design loop

```
D0 scope (H1) → D1 allocation (H2) → D2 exploration ──────────────────────▶ D3 convergence (H3) → D4 review (H4)
                                       │  manual candidates, scan/expand (main)
                                       │  search (this task):
                                       │    design brief → F1 search values → (C2) Geant4 search values → finalists
                                       │    → expand → run/budget (F1–F3) → (C2) geometry → F4 confirmation → f4
                                       └▶ report: verdicts, screening, comparison basis, ranking and Pareto or their refusal (design.py)
```

| Role | May | May not |
|---|---|---|
| Claude (designer) | Turn the design-spec into a search spec; choose candidate roles and slots; write 2–6 seed topologies with physics reasons; set search ranges (within the role rules); decompose the problem; decide when to run the Geant4 search and confirmation; follow up anomalies; explain the `report` results and trade-offs to the user | Invent parameters outside the role rules; skip validity checks; modify any output; report search values; write verdicts or rankings; quietly change requirements after seeing results |
| Searcher | Generate candidates in genome space; run within budget, seed and settings; record every evaluation | Decide whether requirements are met; rank finalists |
| `evaluate_design.py`/`contracts/design.py` | Official evaluation, verdicts, screening, comparison, Pareto | Behave differently by proposer |
| User and reviewers | Human records of H1–H4; dispositions (accept-risk, next-study) | — |

### §C.4.3 Concepts of the old task C and their main counterparts

| Old task C concept | main counterpart | Handling |
|---|---|---|
| Requirements spec `detector-requirements/1`, `confirmed_by_user` | design-spec (REQ, denominators, allocations, `comparison_basis`, `pareto_axes`); H1, H2 | Deleted; read the design-spec instead |
| Objective and constraint catalogue | Figure-of-merit ids of `design_adequacy.json` | Deleted; use the ids |
| Component catalogue `catalogue/1` | `subsystem_roles` + design blocks of the tool contracts | Becomes realization rules per role with parameter ranges (new) |
| Design grammar `detector-design/1` | design-candidate (subsystem graph) | Deleted; the genome is only an internal encoding + decoder (new) |
| `realize()` → `element_sim.spec/1` | `evaluate_design.py geometry` + B1's `from-geometry` | Deleted; provided by task B |
| Fidelities F0/F1/F2 | main's F1; Geant4 search values (no fidelity); F4 | Renamed (§C.4.6) |
| Design hash and evaluation cache | `effective_digest`, `parameter_digest`, `--replace`, `run_workflow.py --incremental` | The in-search cache stays; official evaluations use main's mechanisms |
| `threshold` requirement verdicts, `order`, own Pareto, "recommended design" | Verdict table and aggregation, `ranking()`, `pareto()` | Deleted |
| Search record `extension.design_search` | The `scan_summary` pattern | Becomes `search_summary` (CV-C1) |
| CV3 role rules | Orphan-run rule | Becomes the CV-C2 seed rule |
| Adapter `detector-design`, reference, one `SKILL.md` line | Capability `detector-design` (hep-detector), workflow document | Deleted; one new workflow section |
| `proposer: llm` | Parameter `source`/`status: proposal` | Merged, and also flagged in the `search_summary` |
| NSGA-II, Sobol, hypervolume, repair and violation measure | None | Kept (new) |
| Multi-fidelity Geant4 search, paired comparison, G-C2a, `values` | None | Kept (C2) |
| Winner's-curse and search-size protection | Partly: RSK-04 expands only points that enter comparison | Kept and extended |
| Closure tests | None | Kept |
| J16 | Examples A, B (no journey) | Now run on Examples A, B |

### §C.4.4 Search spec `design-search-spec/1`

Sketch (`//` is commentary, not part of the JSON):

```
{ "search_spec_version": 1,
  "design_spec": {"path": "design-spec.v1.json", "sha256": "..."},
  "base_candidate": "<design_id>:cand-S",
  "objectives": [  // figure-of-merit id and denominator from the design-spec's requirements; direction from the adequacy table's better
    {"requirement": "REQ-TRK-001"},                       // momentum-resolution-core, rigidity_GV 100, proton
    {"figure_of_merit": "mass-budget"} ],
  "constraints": [ {"requirement": "REQ-MDR-001"} ],      // feasibility checked on search values during the search; non-binding
  "free_parameters": [  // ranges within the role rules; integers and categoricals marked
    {"ref": "DES-TRK-001.parameters.layer_positions_m", "kind": "positions", "n": [4, 8], "min_spacing_m": 0.05},
    {"ref": "DES-MAG-001.parameters.field_T", "range": [0.1, 1.0]} ],
  "slots": {"tof": [0, 1]},                               // optional: roles that may be added or removed, and how many
  "rules_version": "1.0.0", "materials_version": "1.0.0",
  "budget": {"evaluations": 20000, "geant4": 0},           // geant4 > 0 from C2
  "optimizer": {"name": "nsga2", "population": 200, "generations": 100, "eta_c": 15, "eta_m": 20, "seed": 12345},
  "stopping": {"hypervolume_window": 10, "min_improvement": 0.001, "reference_point": "auto"},
  "finalists": {"max": 5, "distinct_topologies": true} }
```

- At most 4 objectives (hypervolume computed exactly with WFG); the rest are expressed as constraints.
- Objectives can only be figures of merit with an F1 tool contract (C1) or with a Geant4 implementation in C2; figures of merit that need an upstream (charge confusion needs resolution) are computed in-process in chain order.
- Figures of merit that are only `capability.unavailable` cannot be objectives; the search records them as they are, and `report` lists them as usual.

### §C.4.5 Genome, decoding and validity

**Realization rules per role, first version** (`roles.json`; each rule has parameters, units, ranges, a calibration template and a budget model):

| Role | Parameters the search may change | Budget model (`basis: estimate`, assumed model) | Matching F1 tool |
|---|---|---|---|
| `tracking` | `layer_positions_m` (array; number of layers N), `point_resolution_um`, `layer_x_over_x0` (from material and thickness via the materials table), `passive_x_over_x0` | density × volume; channel count = area / pitch | `tracker_resolution`, `multiple_scattering`, `charge_confusion_rate` |
| `bending` | `field_T` (see Example A's note on magnet length) | declared placeholder mass model | same as above (bending power) |
| `tof` | number of layers, σ_t, thickness, path length | density × volume; channel count | `pid_separation_power` |
| `calorimetry-em` | sampling coefficient, depth (X₀) | density × volume | `calorimeter_resolution` (evaluate, optimistic) |
| `rich` | radiator index and length, photon-yield parameters | declared model | `cherenkov_angle` |

**Genome encoding:** a fixed number of slots, each with an "enabled" bit, a role (categorical), `parent_slot` (integer; −1 for top level, otherwise pointing to an enabled `bending` or `calorimetry-*` slot), the role's categorical parameters (material), integer and continuous parameters. This lets the genetic algorithm add and remove subsystems and change their kind.

**Decoding (genome → design-candidate):**
- main's granularity: one subsystem per role, planes expressed as array parameters (e.g. `layer_positions_m` of one `tracking` subsystem), not one subsystem per plane.
- Designs that only change parameters or add subsystems are written as `overrides` on the base candidate (new subsystems with new `DES-*` ids); `deep_merge` can add but not remove (`contracts/design.py:252-260`, `384-394`), so topologies that drop a subsystem are written as independent candidates without `derived_from`, copied from the base candidate with a note in the description.
- Every parameter gets `source: "search SEARCH-<id> point <k>"`, `status: proposal`; new subsystems get, from the role rule, a `calibration` (method and at least one control sample; else `design.calibration_incomplete`) and a budget row for every budget quantity.
- The decoded result is validated with `contracts.validate.validate_artifact` and the candidate checks of `contracts/design.py`.

**Validity (checked before evaluation):** parameters within the role-rule ranges; minimum spacing between planes; inside the envelope; daughters only one level deep; materials in the materials table. Structurally "unreasonable" combinations (e.g. requiring rigidity resolution with no magnet) are **not** forbidden by the rules; they fall away naturally through the objectives and constraints.

**Repair and violation measure:** after crossover or mutation, repair in order: clip continuous and integer parameters to range; set `parent_slot` to −1 when it points to a disabled slot or one that cannot be a mother; sort plane positions, push them apart to the minimum spacing and clip back those beyond range. Designs still invalid after repair enter constrained domination with the violation v = Σ (normalised violation of each rule: overlap length / envelope length, length outside the envelope / envelope length, spacing shortfall / declared minimum spacing, number of daughters nested deeper than one level) (smaller v wins; objectives are compared only when v = 0).

**Dedup and cache:** within the search, designs are deduplicated by the `effective_digest` of the decoded candidate (equal parameters give equal digests), and the search size counts distinct designs. Cache key = `effective_digest`, evaluation level, versions of the tools and role rules, code hash, and for Geant4 search values S, N, K, B (the same design in different seed_groups is a different evaluation).

### §C.4.6 Evaluation levels

| Level | Method | Cost per design | Written to | Use |
|---|---|---|---|---|
| F1 search value | In-process call of the F1 tool-contract tool (C1.4) | milliseconds | `search_summary` | Structure and parameter search, 10⁴–10⁵ designs |
| Geant4 search value (C2) | Short `element_sim` + `simreco` runs, about 10³ events, K = 16 | minutes | `search_summary` | Refine hundreds of designs; correct F1 biases |
| Official evaluation (F1–F3) | Finalists after `expand`, with `evaluate_design.py run`, `budget`, `response` | seconds to minutes | `evaluations/`, `runs/` | Verdicts and comparison by design.py |
| Confirmation (F4, C2) | `geometry` → study (new seeds, A1.9 event counts, convergence gate, variations) → `label --upgrade` → `f4` | hours | `evaluations/`, study record | The only Geant4 performance numbers |

- F1 search values inherit the tool contract's bound (mostly `optimistic`): a search value meeting a target does not mean compliance, only that the design is worth evaluating.
- Each finalist records "search value − official evaluation or confirmation value" (`search_minus_official`) to diagnose the winner's curse and model differences; when the difference exceeds a declared threshold, Claude explains it in the reply.

### §C.4.7 Search strategy

| Step | Content | Default method | Budget (default, declarable) |
|---|---|---|---|
| S0 design brief | Claude reads the design-spec and writes the candidate roles, 2–6 seed topologies with physics reasons, and the decomposition of the problem | Claude | — |
| S1 structure and parameter search | Search the full genome on F1 search values; initial population = seed topologies + Sobol random designs | NSGA-II (standard library) | population 200 × 100 generations = 2×10⁴ |
| S2 Geant4 refinement (C2) | Take the top K designs **with distinct topologies** and refine continuous parameters on Geant4 search values; designs of one generation (including surviving parents, re-evaluated in that generation) share a seed_group (paired comparison, gate G-C2a) | NSGA-II or CMA-ES; from C3 optionally MOBO (qNEHVI), limited to ≤ 4 objectives and ≤ 20 parameters | K = 5, about 100 each |
| S3 finalists and expansion | Fix the finalists per the `finalists` rule and write them to the `search_summary`, then `expand --search`; official evaluation with `run`, `budget`, and `report` derives verdicts and comparison | — | ≤ 5 designs |
| S4 confirmation (C2) | One F4 study per finalist and per (figure of merit, denominator); `f4`; `report` | — | ≤ 5 designs |

- Stopping rule: the budget is spent, or the hypervolume improves by less than a declared value over G consecutive generations. The hypervolume is computed exactly with the WFG algorithm in the normalised objective space (≤ 4 objectives); the reference point defaults to each objective's requirement threshold moved towards worse by × 1.1 (multiplied by 1.1 for minimised objectives, divided by 1.1 for maximised ones), and objectives without a threshold must declare a reference point. No budget is added because of results; adding budget is a new search.
- After S0 Claude may add new seed topologies (e.g. to follow up an anomaly); these proposals are flagged likewise and count toward the search size.

### §C.4.8 Statistical integrity

| Risk | Handling |
|---|---|
| Winner's curse | Search values are used only for selection; finalists are fixed and written to the `search_summary` before any official evaluation or confirmation; there is no reselection among finalists afterwards, and `report` always lists all finalists; seeds of confirmation studies never appear in the search (the CV-C2 rule); `search_minus_official` as a diagnostic |
| Noisy constraints and dominance | No verdict engine of our own: compliance is decided by design.py with the adequacy table's `coverage_cl`; superiority among finalists is handled only by design.py's ranking and Pareto (dominated only beyond the combined 1σ); selection-aware or multiplicity-corrected coverage is a proposal to hep-statistics and design.py (§C.9) |
| Ranking noise | Designs of one generation in S2 share a seed_group (paired comparison), so the difference has smaller variance; confirmation studies do not share and stay independent |
| Search size | The `search_summary` records the number of distinct designs and topologies evaluated, the optimizer settings and the seed |
| Exploiting simulation defects | Confirmation studies must pass the convergence gate (A1.8, D11) and physics-model variations (B2); the scope and tail sources of F4 are checked by `check_geant4_study.py label --upgrade` and `check_f4` (out of scope gives `domain.mismatch` or no upgrade) |
| Robustness | Explore each finalist within the declared tolerances with `scan` (F1); expand the worst point into a candidate and evaluate it like any candidate (F4 when needed); "robust" only means the verdict of the worst-point candidate in `report`, with no verdict of our own |
| Changing requirements | Any requirement change is a new design-spec version and a `requirement-change` record; the search is rerun (a new SEARCH id), and the old search run is kept |

### §C.4.9 Search record and contracts

The search run is `runs/SEARCH-<id>.computational-run.json`, with `argv`, `script_sha256` and `input_manifest` (design-spec, base-candidate chain, search spec, role rules, materials table) written the way `scan` writes them, plus a `search_summary` (CV-C1):

```
{ "search_spec_sha256": "...", "design_spec": "design-spec.v1.json", "base_candidate": "<design_id>:cand-S",
  "optimizer": {"name": "nsga2", "implementation": "evaluate_design.py search", "backend": null, "seed": 12345, "config": {...}},
  "levels": ["F1"],                                   // "geant4" added from C2
  "evaluated": {"F1": 20000, "geant4": 0, "distinct_designs": 18734, "topologies": 143},
  "points": [{"index": 0, "effective_digest": "...", "genome": {...}, "proposer": "random|llm",
              "values": {"momentum-resolution-core": {"value": 0.081, "bound": "optimistic"}}, "violation": 0.0}],
  "front": [0, 17, 233],                              // search front: non-binding
  "hypervolume": [{"generation": 1, "value": 0.41}, ...],
  "finalists": [{"index": 233, "fixed_before": "expand"}],
  "seeds": {"geant4_search": []},                     // C2: S of every Geant4 search run
  "note": "search values are not evaluations: they take part in no aggregation and support no verdict; expand a point to evaluate it" }
```

- **CV-C1:** `ext_computational_run.json` gains `search_summary` (required `search_spec_sha256`, `points`, `front`, `finalists`; the rest optional); `orphan_runs` in `contracts/design.py` exempts `search_summary` (as for `scan_summary`); an evaluation whose `run_ref` is a search run is `design.scan_point_not_expanded` (reuse that code, or add `design.search_point_not_expanded`, §C.10).
- **CV-C2:** an evaluation whose run or study seed (`extension.seeds` or `extension.simulation.logical_run_seed`) appears in any `search_summary.seeds` of the same artifacts_dir is `design.contract_mismatch`; Geant4 search runs have `extension.simulation.evidence_role` `search` and cannot be evidence for `label --upgrade`.
- Large `points` may be stored as a JSON Lines file in the same folder, listed with its sha256 in `output_hashes`; the `search_summary` then holds only the summary and the front.

---

## §C.5 Stage C1: F1 search (contracts CV-C1)

### C1.1 Schema of the search spec

`contracts/schemas/design_search_spec.json` (`design-search-spec/1`, §C.4.4), using only keywords supported by `contracts/schema.py` (currently no `maxItems`, `maximum`, `exclusiveMaximum`, `uniqueItems`; `contracts/schema.py:61-63`); the objective-count limit, upper bounds of ranges, slot counts and cross-field rules (an objective's requirement exists in the design-spec, figure-of-merit ids are in the adequacy table, parameter refs exist in the base candidate, roles are in `subsystem_roles`) are checked in Python. If A2.7 adds those keywords, the schema may express them, and the Python checks remain as tests.

### C1.2 Realization rules per role and the materials table

- `skills/hep-detector/assets/design-search/roles.json`: the five roles of §C.4.5, each with parameters, units, ranges, manufacturing tolerances, a calibration template, a budget model and the matching F1 tool.
- `materials.json`: density, X₀, λ_I of each material; generated from a dump of Geant4 NIST materials (the header records the Geant4 version and the command), or taken from the PDG and recorded through hep-citations; checked against the same dump when Geant4 is available (`geant4_verify.py` line 132 uses the dump's `radiation_length_cm`).
- Every rule has unit tests (decoded parameters, budget rows, calibration fields).

### C1.3 Genome, decoding and validity

The genome, decoder, validity, repair and violation measure of §C.4.5. Invalid designs return the reason (overlap, outside the envelope, nesting, range) and are not evaluated. Decoded results pass `validate_artifact` and design.py's candidate checks; topologies that drop a subsystem are written as independent candidates.

### C1.4 In-process F1 search values

- For each objective, select the F1 operation the way `run_evaluation` does (`choose_operation`), recompute its arguments from the decoded candidate and the denominator with `contracts/design.py` (T-58), then, in the same process, import the tool script once and call its `main(argv)`, capturing the output JSON; config files go to a scratch folder. No formula of our own, so constants and approximations (e.g. `PDG_MS = 0.016` and the Highland variant in `tracker_resolution.py`) are the tool contract's; points outside the tool's validity domain are recorded with `in_domain: false`.
- Figures of merit that need an upstream (charge confusion needs resolution) are computed in-process in chain order.
- The formulas are not moved into `core/`: the admission rule of `core/OWNERS.json` requires more than one top-level consumer, and `tracker_resolution.py` and `evaluate_design.py` both belong to hep-detector.
- Consistency: sampled points (declared number, default 20) and all finalists are recomputed with `run` in a scratch copy, relative difference ≤ 1e-12 (C1.10).

### C1.5 Searcher

Sobol initialisation (Joe–Kuo direction numbers, shipping the table for the needed dimensions); NSGA-II (simulated binary crossover η_c = 15, polynomial mutation η_m = 20, for continuous and integer genes, integers rounded after mutation; categorical genes and `parent_slot` by uniform crossover and random reset; slot enable bits by bit flip); then repair per §C.4.5, with constraints handled by constrained domination on the violation; hypervolume computed exactly with WFG. Distribution indices and mutation probabilities are written to the search spec. Standard-library implementation; bit-for-bit identical results for the same seed.

### C1.6 `evaluate_design.py search` and `search_summary`

```
evaluate_design.py search --artifacts DIR --spec REL --id SEARCH-ID [--max-evaluations N] [--status LABEL]
```

Reads the current design-spec and the search spec, runs S1 after S0 and the finalist selection of S3, and writes `runs/SEARCH-*.computational-run.json` (§C.4.9). It writes no design-candidate or evaluation; `--max-evaluations` is a safety cap (default: the search spec's budget). CV-C1: the `search_summary` schema and the exemption in `orphan_runs`; gated by `strict or _at_least(contract_version, CV-C1)`.

### C1.7 `expand --search`

```
evaluate_design.py expand --artifacts DIR --search REL --point K --candidate-id NAME
```

Generalises the existing `expand` (which today reads only `scan_summary`, `evaluate_design.py:837-875`): reads a point of the `search_summary` and writes the candidate with the decoder of §C.4.5; with `derived_from` to the base candidate when only parameters change or subsystems are added, as an independent candidate when a subsystem is dropped; inputs list the base candidate (`binding: parameters`) and the search run. `--point` accepts only finalists; other points are refused (RSK-04). Returns suggested next `run` and `budget` calls (`plan` lists them as well).

### C1.8 Closure tests

| Test | Known answer | Pass condition |
|---|---|---|
| DTLZ2 (3 objectives, known Pareto front; searcher called directly) | Analytic front | Hypervolume ≥ 95 % of the true value within 2×10⁴ evaluations (the closure-test practice of `AID2E2024`) |
| Plane placement (N = 6, fixed lever arm L, measurement term only, declared minimum spacing L/32) | Best A = 47.66: exhaustive on the 1/32 grid, and a local search not tied to the grid gives the same value (equal spacing 66.96; §C Appendix A) | The searcher finds a configuration with A ≤ 47.66 × 1.01 at minimum spacing L/32 |
| Structure choice (Example A's design-spec, base candidate without the magnet, slots allowing 0–1 `bending`) | Every feasible design on the search front contains `bending` and ≥ 3 `tracking` layers; every design without field is infeasible | Designs without field on the front have violation > 0; after expanding the finalists, `report`'s verdicts on them agree with the feasibility on search values |
| Reproducibility | — | The same search spec and seed give bit-for-bit identical `search_summary` in two runs (timestamps excepted) |
| Consistency | In-process F1 = F1 from `run` | Relative difference ≤ 1e-12 for sampled points and finalists |

### C1.9 Documentation and registration

- `system-design-workflow.md` gains a "D2 automated candidate generation" section: when to use `search` (L2 full design, more parameters or topologies than can be compared by hand), how to write the search spec, the difference between search values and evaluations, `expand --search`, the winner's curse and "never claim an optimum", Claude's role limits (§C.4.2), and that replies must state the search size and confirmation status.
- The docstring and `--help` of `evaluate_design.py`; `tools/check_wiring.py`; `MISSING_FILE_ARGS` in `tests/skills/test_cli_robustness.py` (`--spec` reads a file).
- A new item in capability `detector-design` (e.g. DSD-SEARCH); capability matrix; one "automated candidate generation" case in routing set DSD (reusing existing trigger words, no description change).
- No new reference, no change to `SKILL.md` (§C.3 rule 9).

### C1.10 C1 acceptance

- [ ] Tests of the search-spec schema and cross-field rules; limits checked in Python and tested; every kind of invalid design has a test.
- [ ] Unit tests of the role rules; decoded candidates pass `validate_artifact` and design.py's candidate checks (incl. `calibration` and budget rows); topologies that drop a subsystem are written as independent candidates.
- [ ] Consistency test of in-process F1 against `run` (relative difference ≤ 1e-12).
- [ ] All closure tests of C1.8 pass (gate G-C1; do not merge otherwise).
- [ ] `search` writes no design-candidate or evaluation; schema test of `search_summary`; `orphan_runs` exempts it; an evaluation with a search run as `run_ref` is refused.
- [ ] `expand --search` accepts only finalists; expanded candidates go through `run`, `budget`, `report`, and `report`'s verdicts and the ranking refusal (when expected precision is missing) appear as usual.
- [ ] An independent agent, following the new workflow section, completes from Example A's design-spec the design brief, `search`, `expand`, official evaluation and `report`; the reply states the search size and claims no optimum.
- [ ] `check_layering.py --strict`, `check_packaging.py`, `check_wiring.py` pass; existing design tests (`tests/contracts/test_design_*.py`, `tests/skills/hep_detector/test_design_*.py`) pass unchanged.
- [ ] VALIDATION DESIGN-SEARCH-F1; CHANGELOG; release manifest.

---

## §C.6 Stage C2: Geant4 search values and F4 confirmation (geant4 adapter 0.5.0, contracts CV-C2)

### C2.1 Additions to `core/`

Per R1 and R2 of §P.2 (append only, no change to existing behavior):

| Addition | Location | Content |
|---|---|---|
| Paired mode | `core/stats/decisions.py` (`equivalence` and `change` accept `pairing: paired`) | Both points belong to one seed_group with equal K, B; `absolute`: per-block differences d_b = θ_a,b − θ_b,b, diff = d̄, se_diff = sd(d_b)/√K. `relative`: for each bound r to test (TOST's ±tol, `change`'s tol) form z_b = (θ_a,b − (1+r)θ_b,b)/b̄ (b̄ the block mean of point b) and test z̄ with sd(z_b)/√K one-sided against 0 (Fieller type; the uncertainty of b̄ need not be ignored). ν = K − 1; the se target is se ≤ tol/4 at r = 0. The default stays `independent` |
| `values` accumulator | `core/simulation/summary.py` and the summary schema in `contracts/schemas` (minor increase of `summary_version`); `core/stats/batch_means.py` | Raw selected values per block (sorted by event number); `values_max` (in the observable declaration, default 10⁴) is a per-block limit: a block's values are written when its `n` ≤ `values_max`, and when any block exceeds it the observable does not use empirical quantiles and this is recorded; `merge` rule `concat`; with `values`, quantiles are empirical (Hyndman–Fan type 7, written to `quantile_method`). Reason: resolutions differ a lot between designs, and fixed bins cannot suit all of them |
| C++ implementation of `values` | `g4sim/SimSummary.hh`; written by `element_sim` and `simreco` | Agrees with the Python generator (the method of A2.9) |
| seed_group | `core/simulation/seeds.py` | Geant4 search values: runs of one seed_group share S = H(search_id, "search", seed_group); confirmation studies: S = H(search_id, "confirmation", design_sha256). Runs of one seed_group have equal K, B, `seeding` and pairwise different spec hashes; uniqueness becomes "(S, spec hash) unique; S repeats only within a declared seed_group" |

`core/stats/decisions.py` decides only study gates (convergence, variations, change), never requirements.

### C2.2 Geant4 search values

When the `search` budget has `geant4 > 0`, each design of S2 is decoded into a candidate in a scratch folder → `design-geometry/1` generated with `design.geometry_fields` → `geant4_run.py from-geometry` (B1) → `geant4_run.py run` (`element_sim`) → `reco` (`simreco`) → summary; value and SE are written to `search_summary.points[].values`, and S to `search_summary.seeds`. A fixed (declared) number of events, K = 16. Batches go through the existing partition and batch machinery (hep-computing), cached with the cache key of §C.4.5; duplicate designs are evaluated once. Surviving parents are re-evaluated in the seed_group of every generation, so all comparisons within a generation are paired; a re-evaluation is a new evaluation (different S, no cache hit) and counts against the budget. Geant4 search runs have `extension.simulation.evidence_role` `search`.

### C2.3 Paired comparison in the search

- Every generation of S2 declares a seed_group; its designs share S, and selection uses differences in paired mode.
- **Gate G-C2a:** in the trial of the first search, measure the variance ratio of the difference Var(independent) / Var(paired); when it is below the declared value (default 2), S2 switches to independent comparison and notes it in the `search_summary`. The paired estimate is valid at any correlation; only the gain may be small (in Geant4 different designs quickly consume different random numbers).

### C2.4 F4 confirmation of the finalists

- Finalists are fixed from the S2 search values before any confirmation and written to the `search_summary` (§C.4.8); `expand --search` turns them into candidates.
- For each finalist and each (figure of merit, denominator): `evaluate_design.py geometry` → F4 study (S = H(search_id, "confirmation", design_sha256), two-stage event counts of A1.9, convergence gate, B2's variations and tail sources) → `check_geant4_study.py label --upgrade` (the qualification path of D0) → `evaluate_design.py f4`. Each candidate has only one `geometry_ref` and `results.<fom>` is not keyed by denominator, so each pair gets its own study (B2).
- While D0 is not approved, confirmation studies still run but stop at "upgrade refused"; `report` treats them as unqualified F4 (`f4_unqualified`), and this must not be rewritten into any other verdict.
- `evaluate_design.py search --diagnose SEARCH-ID` writes a diagnostic run (`search_minus_official`: each finalist's search value minus its official evaluation or F4 value); it writes no evaluation and does not affect verdicts.

### C2.5 Protections and robustness

The convergence gate of confirmation studies (production cut, maximum step, field accuracy; A1.8 and D11); variations (B2); tail sources written honestly (B2); out-of-scope cases handled by `label --upgrade` and `check_f4`. Robustness per §C.4.8: `scan` of each finalist within tolerances and expansion of the worst point.

### C2.6 Contracts CV-C2

- The seed rule of §C.4.9: an evaluation whose run or study seed appears in any `search_summary.seeds` is `design.contract_mismatch`.
- Runs with `extension.simulation.evidence_role: search` cannot be listed as evidence for `label --upgrade` (`check_geant4_study.py`).
- The seed_group uniqueness rule (C2.1).
- Gated by `strict or _at_least(contract_version, CV-C2)`.

### C2.7 Adapter changes

| Item | Content |
|---|---|
| geant4 adapter | 0.4.0 → 0.5.0: `values` in `SimSummary.hh`; `element_sim` and `simreco` write `values` per the observable declaration; `run` accepts `--seed-group`; `SIM_SOURCES` keeps its structure |
| G5 | New C++ changes are written against the Geant4 API; the reviewer confirms in the VALIDATION entry |

### C2.8 Computing budget

F1 search over 2×10⁴ designs: minutes; Geant4 search about 500 × 10³ events; confirmation ≤ 5 designs × the number of (figure of merit, denominator) pairs, event counts per A1.9; calorimeter showers dominate CPU. Actual budgets are written to the search spec after the trial.

### C2.9 C2 acceptance

- [ ] Paired-mode toys: coverage of the nominal 90 % interval from se_diff |coverage − 0.90| ≤ 0.02 + 3σ_MC; paired `relative` mode toys reject with probability ≤ 0.05 + 3σ_MC when the true relative difference equals r; the variance ratio measured in the trial is recorded (gate G-C2a).
- [ ] `values` accumulator: Python and `SimSummary.hh` agree; omitted and recorded above `values_max`; unit tests of empirical quantiles; old summaries (without `values`) still readable.
- [ ] `element_sim.spec/1` produced from decoded candidates through `geometry` and `from-geometry` passes `geant4_run.py check-spec` in a subprocess (at least one case per role).
- [ ] Contract tests of seed_group and the seed rule: S repeated outside a seed_group and equal spec hashes within one seed_group are refused; a confirmation study whose S equals that of a search run gives `design.contract_mismatch`; runs with `evidence_role: search` cannot be upgrade evidence.
- [ ] The cache is keyed by `effective_digest`, level, versions, code hash and S, N, K, B; duplicate designs are evaluated once; surviving parents are re-evaluated every generation.
- [ ] Winner's-curse toy: on a set of pure-noise designs, search values are clearly optimistic and confirmation values unbiased (gate G-C2b).
- [ ] One complete small search (the structure-choice problem of C1.8, with Geant4 search values) completes S0–S4: finalists fixed, expanded, officially evaluated, F4-confirmed (stopping at a refused upgrade, shown as it is, while D0 is not approved), `report` and the diagnostic run.
- [ ] J14 still passes under `--strict`; so does J15 when B3 is merged.
- [ ] VALIDATION DESIGN-SEARCH-G4; CHANGELOG; release manifest; the checks of §A.8.

---

## §C.7 Stage C3: Examples (J16)

### C3.1 J16: automated candidate generation on Examples A and B

- **Example A** (`examples/design-space-spectrometer`, space spectrometer): starting from its design-spec and one candidate, search the number of layers, layer positions and field; expanded finalists go through `report`, showing whether the comparison basis holds and that ranking and Pareto are refused while expected precision is missing; with C2 merged, one finalist gets an F4 confirmation.
- **Example B** (`examples/design-collider-tracker`, collider tracker + ECAL): search tracker and ECAL parameters; `capability.unavailable` requirements (hadronic energy resolution, trigger efficiency, pileup robustness, etc.) are carried through to `report` as they are, showing that the search does not depend on the detector kind.
- Both are synthetic examples; the README says they demonstrate the process, not new detector designs (the same positioning as `AIDO2025`, `SWGO2023`); a comparison with the J15 design (B3) serves as illustration, e.g. clustering planes towards the ends and the centre raises the MDR but worsens the resolution where multiple scattering dominates (§C Appendix A).

### C3.2 Optional Bayesian-optimisation backend

`adapters/design-bo/` (0.1.0): Ax/BoTorch (qNEHVI), used only in S2, limited to ≤ 4 objectives and ≤ 20 continuous parameters; loaded by lazy import, with versions recorded in the `search_summary` and `adapter.json` (whether listed as a tested tool: see the MOBO item of §P.7); without it the search falls back to NSGA-II and notes this. Both compared on the DTLZ2 closure test.

### C3.3 Registration and documentation

`docs/researcher-journeys.md` (J16), routing case (`check_routing_static.py` requires a routing case for every journey in the table), `tests/examples/test_design_search_j16.py` (replays from the committed `search_summary` and evaluations and compares `report`), capability map, capability matrix, adapter docs (if design-bo is added); the Markdown of this task is reviewed with hep-authoring's independent review process (advisory).

### C3.4 C3 acceptance

- [ ] J16 completed on Examples A and B; `report` contains screening, comparison basis, ranking or its refusal; the reply states the search size and confirmation status (gate G-C3).
- [ ] The offline replay of J16 (from the committed records) gives the same `report`.
- [ ] The Bayesian-optimisation backend (if installed) passes the DTLZ2 closure test; otherwise the fallback is noted.
- [ ] Registration and documentation done; routing case passes.
- [ ] VALIDATION DESIGN-SEARCH-EXAMPLES; CHANGELOG; release manifest; the checks of §A.8.

---

## §C.8 Contracts and versions

| Object | Location | Version |
|---|---|---|
| `design-search-spec/1`, `search_summary`, the exemption in `orphan_runs` | `contracts/schemas/`, `contracts/design.py` | CV-C1 (minor, gated; C1) |
| `search`, `expand --search`, role rules, materials table, searcher | `skills/hep-detector/` | with the plugin version (C1) |
| Paired mode, `values`, seed_group | `core/` | with the plugin version, minor increase of `CORE_VERSION` (C2); minor increase of the summary schema's `summary_version` |
| C++ implementation of `values`, `--seed-group` | geant4 adapter | 0.5.0 (C2) |
| Seed rule, restriction on `evidence_role: search` | `contracts/design.py`, `check_geant4_study.py` | CV-C2 (minor, gated; C2) |
| Bayesian-optimisation backend | `adapters/design-bo/` | 0.1.0 (C3, optional) |
| J16 | `examples/`, `docs/researcher-journeys.md` | with the plugin version (C3) |

All CV-* numbers are fixed at release in merge order, each ≥ 3.13.0.

---

## §C.9 Not done and deferred

| Item | Decision | Reason / trigger |
|---|---|---|
| The search writing verdicts, rankings, a recommended design, or claiming an optimum | Not done | Derived by design.py (review C2, C3) |
| Letting the LLM decide the design by itself | Not done | No real case does this; verdicts must be reproducible |
| Selection-aware or multiplicity-corrected coverage | Deferred, as a proposal | main uses `coverage_cl` per figure of merit with no multiplicity correction; for review with hep-statistics and design.py (review C12) |
| Cost as an objective | Not done | Cost has no evaluator (review C13); trigger: main adds a cost evaluator |
| Calorimeter-depth closure test | Deferred | The old "depth ≥ 16 X₀" is not a figure of merit of the adequacy table; shower-containment is `capability.unavailable` below F4; trigger: B2's shower-containment F4 available |
| Differentiable simulation and differentiable surrogates (MODE route) | Deferred | Geant4 is not differentiable; differentiable surrogates are still immature at point-cloud scale (`MODE2023`). Trigger: a problem with > 20 continuous parameters and an insufficient Geant4 search budget |
| Cylindrical and non-box geometry for Geant4 search values | Deferred | `element_sim` has only box elements. Trigger: a new geometry kind and realizer (the extension point in §R) |
| Geant4 search values for Cherenkov, RICH, TRD | Deferred | Need optical physics and dedicated reconstruction; searching at F1 (`cherenkov_angle`) is possible |
| Reinforcement learning, large neural-network surrogates | Deferred | Data volume and interpretability; NSGA-II and MOBO suffice for ≤ tens of parameters |
| Real cost and mass databases | Not shipped | Provided by the user through candidate budget rows, with sources |

---

## §C.10 Open decisions and residual risks

**Open decisions** (numbers in §P.7): D0 (F4 qualification path, blocks the upgrade of C2's confirmations); whether the MOBO backend is listed as a tested tool; whether an evaluation with a search run as `run_ref` reuses `design.scan_point_not_expanded` or gets a new `design.search_point_not_expanded` (decided with CV-C1); whether `results` is keyed by denominator and several `geometry_ref`s are allowed (raised by B2 with the maintainer; affects the number of studies in C2.4).

**Residual risks:**
1. Biases of the F1 tools (mostly optimistic) can make the structure search miss good topologies; mitigated, not excluded, by topology diversity in S2 and `search_minus_official`.
2. Simulation-optimised designs may exploit Geant4 behaviour in unvalidated regions; the convergence gate, variations and F4 qualification protect only partly.
3. The budget models of the role rules are crude; without the user's budget rows, budget objectives are only illustrative.
4. With more than 4 objectives the search front is hard to read; the design-spec should express the rest as constraints.
5. Claude's design brief may carry "known instrument" bias; offset by Sobol random designs and topology diversity, and the `search_summary` separates LLM and random proposals.
6. The variance reduction of paired comparison in Geant4 may be small (gate G-C2a).
7. Computing: Geant4 search values and confirmations of calorimeters are expensive; budgets are adjusted after the trial.
8. main's design loop changes fast (0.37.0 to 0.38.0 in one day); allow time for rebase conflicts in `evaluate_design.py` and `contracts/design.py` (§P.8).
9. Of the references of this part, GRACE and VI-BRATO are 2026 preprints whose conclusions are not yet peer reviewed.

---

## §C.11 Suggested order of work

At the start of each stage, create and confirm that stage's isolated worktree per §P.10.2 and do every step in it; remove it after merge per §P.10.5.

**C1 (based on main; can run in parallel with tasks A, B)**
1. Pre-start checks; search-spec schema (C1.1); role rules and materials table (C1.2).
2. Genome, decoding and validity (C1.3); in-process F1 and the consistency test (C1.4).
3. Searcher (C1.5) and the DTLZ2 and plane-placement closure tests.
4. `search` and `search_summary` (C1.6); `expand --search` (C1.7); remaining closure tests; documentation and registration (C1.9); independent-agent acceptance; C1.10.

**C2 (after B2 and C1 are merged)**
1. Additions to `core/` (C2.1) and their toys.
2. Geant4 search values (C2.2); trial of paired comparison (C2.3).
3. F4 confirmation (C2.4, depending on the state of D0); protections and robustness (C2.5); CV-C2 (C2.6); adapter changes (C2.7); C2.9.

**C3 (after C2 is merged)**
1. J16 on Examples A, B (C3.1); optional Bayesian-optimisation backend (C3.2).
2. Registration and documentation (C3.3); C3.4.

---

## §C Appendix A: Numbers

**Plane-placement closure test** (curvature variance σ_k² = A σ² / L⁴, N = 6, equal weights, measurement term only; exact rational least squares; computed by `design_search_closure.py` in this folder):

| Configuration | A | MDR relative to equal spacing |
|---|---|---|
| Equal spacing (J15) | 66.96 | 1 |
| Two planes each at both ends and the centre (coincident) | 48.00 | 1.181 |
| 2/3/1 planes clustered at 0, 1/2, 1 (coincident) | 45.33 | 1.215 |
| 2/3/1 clusters, middle cluster moved to 0.465 (best of a 1/1000 scan) | 44.77 | 1.223 |
| Best by exhaustive search on a 1/16 lever-arm grid (distinct planes, minimum spacing L/16) | 50.34 (0, 3/8, 7/16, 1/2, 9/16, 1) | 1.153 |
| Best by exhaustive search on a 1/32 lever-arm grid (minimum spacing L/32; the closure-test answer) | 47.66 (0, 1/32, 7/16, 15/32, 1/2, 1) | 1.185 |
| Asymptotic large-N limit (N/4, N/2, N/4 clustered at 0, 1/2, 1; not reachable with integer plane counts at N = 6) | 256/N = 42.67 | 1.253 |

Coincident clusters are not bound by the minimum spacing, so they are not the closure-test answer and only illustrate the trend. J15's MDR of 1172 GV becomes about 1389 GV with the best 1/32-grid configuration; but clustered configurations are worse where multiple scattering dominates, which is exactly the trade-off J16 lets the search handle. When the closure test uses the F1 resolution of `tracker_resolution` as objective with zero material (measurement term only), the resolution is ∝ √A, so the best configuration is the same as in the table.

## §C Appendix B: Sources

- `Cisbani2020`: E. Cisbani et al., "AI-optimized detector design for the future Electron-Ion Collider: the dual-radiator RICH case", JINST 15 (2020) P05009, [arXiv:1911.05797](https://arxiv.org/abs/1911.05797)
- `AID2E2024`: AID(2)E collaboration, "AI-Assisted Detector Design for the EIC (AID(2)E)", [arXiv:2405.16279](https://arxiv.org/abs/2405.16279)
- `MODE2022`, `MODE2023`: MODE collaboration, "Toward the end-to-end optimization of particle physics instruments with differentiable programming", [arXiv:2203.13818](https://arxiv.org/abs/2203.13818); "Progress in end-to-end optimization of detectors for fundamental physics with differentiable programming", [arXiv:2310.05673](https://arxiv.org/abs/2310.05673)
- `AIDO2025`: Schmidt et al. (MODE), "End-to-end detector optimization with diffusion models: a case study in sampling calorimeters", [arXiv:2502.02152](https://arxiv.org/abs/2502.02152)
- `Borysov2024`: O. Borysov et al., "Longitudinal structure optimization for a high density electromagnetic calorimeter", [EPJ Web Conf. 315, 03006 (2024)](https://www.epj-conferences.org/10.1051/epjconf/202431503006)
- `SWGO2023`: T. Dorigo et al., "Toward the end-to-end optimization of the SWGO array layout", [arXiv:2310.01857](https://arxiv.org/abs/2310.01857)
- `GRACE2026`: J. Hill, H. J. Ryoo, "GRACE: an agentic AI for particle physics experiment design and simulation", [arXiv:2602.15039](https://arxiv.org/abs/2602.15039) (preprint)
- `VIBRATO2026`: W. Chung et al., "Agentic-AI detector co-design and optimization in vertically-integrated differentiable full simulations", [arXiv:2604.21804](https://arxiv.org/abs/2604.21804) (preprint)
- All retrieved on 2026-10-23; the citation keys are provisional names in this document, and authors and journal data must be checked through hep-citations before citing

## §C Appendix C: Version history

| Version | Content |
|---|---|
| 2026-10-23 | First proposal: three roles, requirements spec, component catalogue and design grammar, F0/F1/F2 multi-fidelity, search and confirmation separated, contracts, C1/C2, J16; later references to the shared `core/` modules after the re-examination of task A |
| 2026-10-23 | Reorganised per the plan (Part 1): three stages; `threshold`, `order`, paired comparison, `values`, search roles and seed_group added by C2.1; realization checked with `check-spec`; contract version recorded as CV3; J16 and MOBO moved to C3 |
| 2026-10-23 | Isolated-worktree execution rules added (§P.10) |
| 2026-10-23 | Fixes after the detailed check: schema keyword limits; two-sided bound of `order`; paired `relative` mode; cache key; parent re-evaluation; design dedup; materials table; genome repair and violation measure; minimum spacing of the closure test; citation keys; `values_max` per block |
| **2026-10-24 (this version)** | **Re-planned on the detector system design loop of main 0.38.0 (review record `review-2026-10-24-main-0.38.md`, C1–C13, P2–P4): task C becomes the D2 candidate generator `evaluate_design.py search`; deleted the formats of the requirements spec, component catalogue and design grammar, `realize()`, `threshold`/`order`, the recommended design and own Pareto, adapter `detector-design`, the reference and the `SKILL.md` line; fidelities use main's F0–F5 (old F0 = F1, Geant4 search values have no fidelity, confirmation = F4); the search population lives in `search_summary` (CV-C1), and only finalists are expanded; in-process F1 calls the same tool as the tool contract; the C2 seed rule (CV-C2) replaces the role rules; C1 no longer depends on task A; J16 now runs on Examples A, B; the Bayesian-optimisation backend becomes the optional `adapters/design-bo/`; concept-mapping table added (§C.4.3)** |

---

# Part 5 — Design rationale (§R)

> Baseline: hep-research `main` at `5584927` (0.38.0), contracts 3.12.0, adapter geant4 0.1.0, Geant4 11.4.3; most code facts in §R.1–§R.14 were checked at `9f08796`, and the files concerned (the Geant4 adapter, `check_geant4_study.py`, `geant4_benchmarks.py`) are unchanged in 0.38.0
> Date: 2026-10-22 (corrected 2026-10-23 after the detailed check; aligned with the re-plan 2026-10-24)
> Note: this part was originally written before the re-plans of 2026-10-23 and 2026-10-24; on 2026-10-24 only the passages that conflict with main's design loop were changed, and §R.15 was added. Where other passages conflict with Parts 1–4, Parts 1–4 win and the conflict is reported.

---

## §R.0 Summary

**Purpose.** Make simulation studies in hep-research (Geant4 today) achieve three things: results cannot be wrongly labelled `validated-in-scope`; numbers and decisions are reproducible and traceable; the study layer is not tied to one simulation program, one geometry or one kind of study.

**Starting point.** Large experiments have solved the same problems at a much larger scale. This architecture takes only practices that have stood the test of time and are feasible under the plugin's constraints and this program's choices (new modules deliberately standard-library only, separate executables exchanging JSON/CSV, minimal change):

| Problem | What real experiments do | This architecture |
|---|---|---|
| reproducibility under parallel execution | ATLAS reseeds each event from the event and run numbers; Allpix² seeds by event number, "reproducible even when the number of workers is different" | each event reseeded with H(logical-run seed, event number); job splitting and thread count do not affect event content (§R.5) |
| merging results of many parallel jobs | CMS DQM: jobs fill histograms independently; the harvesting step merges them and only then runs quality tests | simulation programs write mergeable run summaries; Python infers and decides only after merging (§R.4) |
| tracing configuration and processing chains | CMS identifies configurations by parameter-set hashes and records each processing step in a process history | each step records hashes of its configuration, inputs and code; multi-level chains are traced transitively (§R.7) |
| supporting several simulation engines | ALICE's Virtual MC puts an insulation layer between user code and the engine, but separating geometry took years | no abstraction at the API level; abstraction at the **output**: any backend that delivers three boundary artifacts (§R.3) |
| sharing data between components | Key4hep uses EDM4hep as the common data model between components; legacy tools join by converting | the boundary artifacts are the common data model; other frameworks join through a reducer (§R.3.4) |
| whether a simulation can be trusted | Geant4's geant-val compares with experimental data across releases; CMS selects the physics list with test-beam data, then checks with collision data; ATLAS validates fast simulation against Geant4 | five validation classes, each with its own reference, statistics and rule on upgrading (§R.6) |
| whether a software change alters results | Belle II runs validation scripts nightly, compares across versions and can bisect the commit that caused a degradation; geant-val runs monthly | a regression class: compares with the previous version, detects change, never upgrades (§R.6.5) |
| data volume tiers | ATLAS: HITS → RDO → AOD; only the tiers needed downstream are kept | four data tiers: event detail (not committed) → per-event summary → run summary → decision records (§R.4.1) |

**The core of the architecture (six sentences):**
1. **Two planes.** Per-event processing is in C++ (the data plane: simulation, digitization, reconstruction); inference after merging, decisions, records and contracts are in Python (the control plane).
2. **A backend interface at the output.** Any backend that delivers a run summary, a column map and an effective config (including the actual geometry tree) reaches the gates, benchmarks and labels.
3. **Event determinism.** Event content depends only on the logical-run seed and the event number; job splitting, thread count and processing order do not matter.
4. **Reproducibility means "same decisions".** On replay, decisions and labels must be identical and numbers within a relative difference of 1e-9; decisions close to a threshold are flagged. Source files are traced by hash. Re-execution on the same platform gives bit-identical events; across platforms (different libm) floating-point accumulators need only agree within a relative difference of 1e-12.
5. **One variance method.** The run summary splits events into K blocks by event number; every SE is estimated by batch means over the blocks, with exact intervals for small counts.
6. **Five validation classes.** Verification, physics reference, setup-matched measurement, regression, model-to-model; only physics reference and setup-matched measurement can upgrade, under conditions the contract re-derives from evidence.

**Stages:** the order, content and versions of the eight stages (A1, A2, B1, B2, B3, C1, C2, C3) are in §P.0 and §P.3; §R.10 lists only one-line pointers.

**Relation to main's design loop.** Since 0.37.0 main has a detector system design loop (design-spec, design-candidate, design-evaluation; verdicts derived by `contracts/design.py`; fidelity F0–F5, a Geant4 study being F4). The division of work in this program: task A makes the label F4 depends on correct; task B provides a spectrometer-capable Geant4 application and the F4 study-record interface; task C is a candidate generator for stage D2 that writes no verdicts and ranks nothing. The reasons are in §R.15.

---

## §R.1 Design basis: what real experiments teach

Each point has a source (§R.14). "Taken" is what this architecture adopts; "not taken" is what it deliberately leaves out, and why.

### §R.1.1 Random numbers and reproducibility

- **ATLAS (AthenaMT):** random streams for different purposes are distinguished by the name of the algorithm using them; generator states are reseeded for each event from the event and run numbers; the goal is that "the sequence of random numbers must be independent of the order in which events are processed".
- **Allpix²:** the main thread seeds each event from a central seed generator as events are created; a worker seeds its engine just before running the event; the design aims at "reproducibility of simulation results from the same inputs even when the number of workers is different". Modules that need ordered output wait in a buffer queue, saving the random-engine state.
- **CMS:** a different approach: one engine per module and per stream, whose state can be saved into the event and restored later for exact replay.
- **Taken:** the per-event reseeding of ATLAS and Allpix². It is the simplest, and it makes "one logical run split into several jobs" produce exactly the same events as a single job. **Not taken:** CMS's state saving (saving engine states per event is unnecessary at our scale).

### §R.1.2 Merging results and where decisions are made

- **CMS DQM:** data is split into any number of jobs, processed out of order and massively parallel; each job fills MonitorElements (mostly histograms); the harvesting step merges matching histograms across files and only then runs quality tests and derived quantities, single-threaded and in order.
- **Taken:** simulation programs fill only "mergeable accumulators" (counts, sums, histograms); all decisions are made after merging, in Python. This is exactly the split between the run summary and the control plane.

### §R.1.3 Traceability

- **CMS:** configurations are identified by parameter-set hashes, and a process history records every processing step the data went through.
- **Taken:** every step (simulation, digitization, reconstruction, table) writes a record with the hashes of its configuration, inputs and code; the input chain of a simulated table can be any depth, checked transitively by the contract (§R.7.4).

### §R.1.4 Several engines

- **ALICE Virtual MC:** an insulation layer between user code and the transport engine, so that geometry and hit-generation code is written once; at the time Geant3 was used in production, Geant4 only for physics validation, FLUKA was not yet finished, and separating geometry from transport was still ongoing.
- **ATLAS AtlFast3:** work is routed by particle type and energy to Geant4, FastCaloSim V2 and FastCaloGAN; fast simulation is validated by showing "no sizeable differences from the Geant4 simulation" after reconstruction.
- **Taken:** abstraction at the **output**, not at the stepping API: a backend may simulate however it likes, as long as it delivers the same boundary artifacts. A backend that mixes simulators describes its routing in the effective config. Fast simulation and ML surrogates validated against Geant4 are "model-to-model" validation (§R.6.5). **Not taken:** a VMC-style engine abstraction layer (ALICE's experience shows high cost and a long time scale).

### §R.1.5 A common data model and geometry

- **Key4hep:** Gaudi as the processing framework, DD4hep for geometry, EDM4hep (built with podio) as the data model; EDM4hep is the exchange format between components in memory and on file; legacy iLCSoft processors convert to and from EDM4hep on entry and exit instead of being rewritten.
- **Taken:** the boundary artifacts are our common data model; external frameworks join through a "reducer" (for example reducing an EDM4hep file to a run summary). Geometry is taken from the backend's actual (as-built) geometry. **Not taken:** Gaudi or DD4hep as dependencies (plugin constraints).
- **GDML:** Geant4 can write the actual geometry as GDML, but only when built with GDML; this plugin's build has `GEANT4_USE_GDML: OFF` (`geant4_build.py` line 53). So the probe walks the actual geometry itself (§R.3.3); a user's build with GDML may attach a GDML file as well.

### §R.1.6 Validation

- **geant-val (Geant4 collaboration):** community validation tests run monthly with development releases; results are stored in a database, compared across releases, with χ² and KS tests on distributions.
- **CMS:** first tunes and selects the physics list with test-beam data, then checks calorimeter response and resolution with isolated charged particles in collision data; compares several Geant4 versions before adopting one, trading speed against accuracy.
- **Belle II:** every software package has validation scripts producing histograms; they run centrally every night, are compared across versions, and a tool bisects the commit that introduced a degradation.
- **Taken:** "validation" split into five classes of different nature (§R.6): verification as an exact consequence; a physics reference on an isolated target (geant-val's thin-target tests belong here); comparison with a measurement on the same configuration (CMS test beams); regression across versions (Belle II, geant-val's monthly comparison); model-to-model (ATLAS fast simulation).

### §R.1.7 Data tiers

- **ATLAS:** simulation writes a HITS file; digitization writes RDO (conceptually similar to raw detector data); reconstruction writes AOD.
- **Taken:** four data tiers, each with its own retention rule (§R.4.1).

### §R.1.8 Real instruments (comparison for J15)

- **PAMELA:** a 0.43 T permanent magnet; 6 planes of double-sided silicon microstrip sensors, resolution better than 4 µm; MDR above 1 TV; three TOF planes (S1–S3, segmented into paddles); a tungsten/silicon imaging calorimeter of 16.3 X₀ and 0.6 λ; plus anticoincidence, S4 and a neutron detector.
- **AMS-02:** four TOF planes (8, 8, 10 and 8 counters); about 140 ps for protons for the system.
- **Taken:** J15 (0.5 T, 6 Si planes, MDR about 1.17 TV, two TOF layers per station, an 18.4 X₀ calorimeter) is almost the same type as PAMELA and serves as a plausibility comparison; 100 ps per TOF layer is optimistic against AMS-02, so J15 scans σ_t at 100 and 150 ps (B3, §B.7). J15 remains a synthetic geometry and represents no experiment.

---

## §R.2 Goals, constraints and principles

### §R.2.1 Goals

| Goal | Guaranteed by |
|---|---|
| `validated-in-scope` cannot be obtained wrongly | facts the contract re-derives from evidence (§R.7) |
| reproducible decisions, traceable numbers | event determinism (§R.5.1), inference after merging (§R.4), the same-decision definition of reproducibility (§R.5.6), hashes of every step (§R.7.4) |
| the study layer is not tied to one backend, geometry or kind of study | a backend interface at the output (§R.3) |
| demonstrate a field, several subsystems and reconstruction | J15 (B1, B2, B3) |

### §R.2.2 Constraints

- The Python modules this program adds use only the standard library. This is a deliberate choice, not a plugin constraint: main's `core/` allows numpy and scipy (`docs/architecture.md` §3); this program's computations do not need them, and J14's offline replay gains no extra dependency. The one exception is C3's optional backend `adapters/design-bo/` (lazy import).
- G5 licence boundary: Python exchanges only JSON and CSV with separate executables; no Geant4 example code is copied.
- Layering: skill scripts and adapters import only `core` and `contracts`; code both need (statistics, decisions, seed hashing, summary reading) therefore lives in `core/stats/` and `core/simulation/` (§A.3 rule 1, §A.4.5); no experiment names in `skills/` or `contracts/` (experiment names may appear in `docs/` and `examples/`).
- Statuses and exit codes (`core/status.py`): 0 ok, 1 a negative verdict, 2 `rejected`, 3 `incomplete`.
- Files ≤ 2 MiB; hep-detector quick load ≤ 25,600 bytes (24,669 now), description ≤ 1,024 characters (`measure_entrypoints.py` reports 1,016). `SKILL.md` and the description are not changed; main already provides the entry to the design loop through a hub link (OQ-01), and task C only adds a section to `system-design-workflow.md`.
- J14's offline replay must always run, with no Geant4 and no compiler.

### §R.2.3 Principles

1. **Correctness before extension.** Nothing new is merged before A1.
2. **Per-event in C++, after merging in Python.** Code that processes per-event data is in the data plane; code that processes merged accumulators is in the control plane. One production implementation per quantity; one in the other language may exist only in tests, as an oracle.
3. **Abstract at the output.** The study layer knows only the boundary artifacts, never a backend's column names, spec format or UI commands.
4. **Trust the actual state; declarations are only the fallback.** Geometry, field and physics settings come from the probe; declarations alone are marked `source: declared` and cannot upgrade.
5. **Upgrade-relevant facts are decided by the contract.** Grade, kind, scope dimensions, configuration and target hash are never self-declared by a record.
6. **The validation class follows the nature of the reference** (§R.6).
7. **Event determinism.** Event content depends only on the logical-run seed and the event number.
8. **What is reproduced is the decision.** Numbers are compared within tolerances, decisions must be identical, sources are traced by hash.
9. **Stopping rules, grids and block counts of evidence are declared in advance.** Topping up, refining and redoing controls are never decided from results.
10. **Extensible interfaces, implementation only as needed.** No general expression language, no plug-in system, no engine abstraction layer.
11. **Look for an existing implementation first; minimal change.**

---

## §R.3 Architecture overview

### §R.3.1 Two planes and the components

```
Control plane (Python, standard library)
  hep-detector      rules, reference formulas, inference (batch means, exact intervals, MPV, IUT, negative controls, distribution comparison), study-level decisions, labels;
                    evaluate_design.py search (C1, C2: the D2 candidate generator; requirement verdicts and comparison derived by contracts/design.py)
  adapters/geant4   spec validation, build, run, job splitting, records (trace.provenance()), simulated tables;
                    produces run summaries from per-event CSVs in A1 (only as the oracle in tests from A2);
                    from-geometry (B1: design-geometry/1 -> element_sim.spec/1)
  adapters/design-bo  (C3, optional) Ax/BoTorch Bayesian-optimisation backend, lazy import
  core              trace, status; stats/ (block estimators, exact intervals, decision engine, distributions);
                    simulation/ (seed hash, summary computation and reading; schemas in contracts/schemas/)
  contracts         validation-class and grade table, scope, configuration and isolation (CV-A1); new classes, transitive
                    processing chains, F4 study-record fields, geometry mapping 1.1.0 (CV-B2); search_summary (CV-C1);
                    search seeds never used for confirmation (CV-C2); design.py derives requirement verdicts (in main)
        ▲
        │  three boundary artifacts (JSON; small, committable, hashable)
        │    run summary        simulation-summary/1    (§R.4)
        │    column map         simulation-columns/1    (§R.3.5)
        │    effective config   engine-independent envelope + actual geometry tree (§R.3.3)
        │
Data plane (C++)
  g4sim/         shared Geant4 helper library (headers):
                      SimHash.hh     sha256 and the seed hash H (consistent with core/simulation/seeds.py)
                      SimSeed.hh     per-event seed H(logical-run seed, event number)
                      SimSummary.hh  block accumulators, merging, JSON writer (standard library only)
                      MiniJson.hh    minimal JSON reader and writer (also used by simreco)
                      SimProbe.hh    the probe: settings and actual geometry tree (depends on Geant4)
                      materials, physics-list selection, CSV writer
  layered_sim       the existing slab program; spec/1 unchanged; gains g4sim
  element_sim       (B1) a general box-element program: nesting, field, plane crossings, per-event ROOT files
  simroot           (B1) links only Geant4's analysis library: info / dump / hash of ROOT files
  simreco           (B2) no Geant4: digitization and reconstruction, writes run summaries and per-event results
  other backends    a user's Geant4 application (including g4sim), other engines or frameworks (converted by a reducer)
```

| Component | Language | Stage | Depends on |
|---|---|---|---|
| contracts | Python | A1 (CV-A1), B2 (CV-B2), C1 (CV-C1), C2 (CV-C2) | — |
| inference and study-level decisions (`core/stats/`, `core/simulation/`) | Python | A1; additions in B2, C2 | — |
| `evaluate_design.py search` (hep-detector) | Python | C1, C2 | `core`, `contracts`; F1 tool contracts; C2 calls `geant4_run.py` as a subprocess |
| `adapters/design-bo/` (optional) | Python | C3 | Ax/BoTorch (lazy import) |
| Python run-summary producer (from per-event CSVs) | Python | A1; only the oracle from A2 | — |
| `g4sim` (`SimHash.hh`, `SimSeed.hh`, `SimSummary.hh`, `MiniJson.hh`, `SimProbe.hh`, helpers) | C++ | A2 | Geant4 (`SimHash.hh`, `SimSummary.hh`, `MiniJson.hh` standard library only) |
| `layered_sim` | C++ | existing; gains `g4sim` in A2 | Geant4 |
| `element_sim` | C++ | B1 | Geant4, `g4sim` |
| `simroot` | C++ | B1 | Geant4 analysis (g4tools) |
| `simreco` | C++ | B2 | standard library, `SimSummary.hh`, `MiniJson.hh` |

### §R.3.2 Backends

| Backend | Purpose | Geometry | Status |
|---|---|---|---|
| `layered_sim` | material-level slab studies (J14) | spec/1: a stack of slabs along x | existing; after A2 only maintenance and `g4sim` integration, no new geometry features |
| `element_sim` | detector-level studies (from J15) | box elements, one level of nesting, field regions | new in B1; future geometry features go here |
| a user's Geant4 application | an experiment group's own geometry | anything (GDML included) | delivers the boundary artifacts by including `g4sim` |
| other engines or frameworks | FLUKA, fast simulation, ML surrogates, Key4hep and others | anything | a reducer converts their output into boundary artifacts; with probe content declared only (`source: declared`) they cannot upgrade |

**Why a new `element_sim` rather than reworking `layered_sim`.** Moving `layered_sim` to a new geometry format needs a spec conversion with a same-host bit-identical check, plus a dual-format accessor maintained forever; it was the most costly and least valuable step of the previous version (§R.13). A new program leaves J14's program untouched and gives two real backends to test the output interface from day one. Both share `g4sim`, avoiding duplication.

### §R.3.3 Effective config

```
{ "engine": "geant4", "engine_version": "11.4.3", "probe_version": "...",
  "backend": {"name": "element_sim", "version": "...", "sources_sha256": "..."},
  "source": "probe" | "declared", "recorded": true, "config_sha256": "...",
  "seeding": {"mode": "per-event" | "stream", "logical_run_seed": ...},
  "geometry": { "tree": [...], "tree_sha256": "...", "hash_scheme": "tree-v1", "gdml_sha256": null },
  "environment_ref": "<hash of the build record>",
  "sections": { "geant4": { ... } } }
```

| Part | Content |
|---|---|
| envelope | engine-independent; rules are chosen as a rule pack by `engine` (only Geant4's `G4R-*` today) |
| `geometry.tree` | rebuilt from `G4PhysicalVolumeStore` (a flat list in creation order) and each volume's mother logical volume; each placement records name, copy number, solid type and parameters, material (composition and density as resolved by Geant4), transform, mother, attached field manager and its parameters; numbers in Python's `float.hex()` format. Replica and parameterised volumes record their parameterization |
| GDML | when a user's build enables GDML, a file written by `G4GDMLParser` and its hash may be attached; not required |
| `sections.geant4` | the full text of `G4EmParameters::StreamInfo` plus parsed fields; per-couple cuts and energy thresholds; energy ranges per process and model; run-manager type; `G4UserLimits`, biasing |
| datasets | paths and content hashes computed once in the build record; the probe refers to it by `environment_ref` |
| timing | master `BeginOfRunAction` (after `RunInitialization`), in `G4State_GeomClosed` with more than 0 couples; otherwise `recorded: false`, and the run cannot upgrade |
| field | field managers are per thread; the master also calls `ConstructSDandField`, so backends using `g4sim` see the field on the master; a declared field the master cannot see marks the config `source: declared` |
| mixed simulators | a backend that routes particles or regions to different simulators describes the routing in `sections` |

### §R.3.4 Reducers (where external backends join)

A backend that cannot include `g4sim` (other engines, Key4hep's EDM4hep files, ML surrogates) joins through a recorded reduction step: it reads that backend's per-event output and writes a run summary and a column map as declared in `output.observables`; its effective config is declared only. The step is itself a computational-run record in the processing chain (§R.7.4). The first reducer, `simreduce`, reads the output of `simroot dump` (implemented after B1, at the first need).

### §R.3.5 Column map (`simulation-columns/1`)

For each observable and output column: semantic name, actual column name, unit, operational definition, and the file it lives in (`csv`, which ntuple of `root`, or `summary`); with `column_map_version`. Only declarative operations (rename, unit, sum, filter) are allowed; a conversion that computes something is a separate recorded step.

---

## §R.4 Data tiers and the run summary

### §R.4.1 Four data tiers

| Tier | Content | Analogue | Retention |
|---|---|---|---|
| T1 event detail | ROOT files: per-volume deposits, plane crossings, per-step hits | ATLAS HITS | not committed; records keep the path, file hash, content hash and row count per ntuple |
| T2 per-event summary | CSV: primary truth, total deposit per subsystem, declared observables | a reduced event table | benchmark runs commit a reduced-column version; others are not committed |
| T3 run summary | `simulation-summary/1`: mergeable accumulators per event block | CMS DQM MonitorElements | all committed (a few kB per run) |
| T4 decision records | study records, benchmark results, labels | — | all committed |

J14's offline replay needs only T3 and T4; T2 is used only for optional oracle tests and the high-statistics MPV check.

### §R.4.2 Run summary (`simulation-summary/1`)

One JSON per job.

| Field | Content |
|---|---|
| `run` | identity and seed of the logical run, the event-number range this job covers, `seeding`, block size B and block count K, hashes of the spec and effective config, the producer (`layered_sim`, `element_sim`, `simreco`, `python-csv`, a reducer) and its version |
| `observables[]` | per declared observable: semantic name (matching the column map), unit, accumulators |
| blocks | events go into blocks by number: block b covers events [b·B, (b+1)·B); each block has its own set of accumulators |
| accumulators | integers: `n`, the count per histogram bin (declared fixed bins; overflow and underflow separate), `count_if[]` (the number of events with x > a declared threshold); floating point: Σx, Σx², `min`, `max`, with Neumaier compensated summation; from C2 `values` may appear (raw values per block for empirical quantiles, omitted and recorded when above `values_max`); `profile` and 2D histograms are interfaces only (§R.9.2) |
| `merge` | each accumulator's merge rule (`sum`, `min`, `max`, `hist`); several jobs of one logical run merge by block number |

**Event weights.** `layered_sim`'s deposits are already multiplied by the track weight, while the CSV's `weight` column is only the primary vertex weight. To avoid double weighting, the event weight must be 1 for now (otherwise exit 2); the meaning of weighted accumulation and rules for biasing are deferred (§R.9.3).

**Numerical precision.** Integer accumulators (counts, histograms, `count_if`) are exact. Floating-point sums use compensated summation; different job splits or thread counts change only the merge order, giving relative differences of about 1e-15, far below the reproducibility tolerance (§R.5.6).

---

## §R.5 Execution, seeds, blocks and reproducibility

### §R.5.1 Logical runs and event determinism

- A **logical run** is fixed by the spec, the backend and the logical-run seed S, and has N events numbered 0 … N−1.
- `seeding: per-event` (the default for new specs): event i reseeds at its start with H(S, i). Therefore:
  - splitting a logical run into any number of jobs (each covering a range of event numbers) gives exactly the same events as a single job;
  - serial and MT with any thread count give the same event content.
- `seeding: stream`: the old behaviour (serial: one continuous stream; MT: the master draws per-event seeds in batches). Used only for J14's existing specs, so that A2's regression check can require bit-identical CSVs.
- Seeds: S = H(study_id, role, point_id), mapped to [1, 2³¹); the evidence roles in A1 are trial, nominal, scan, control, variation, calibration; B2 adds regression and C2 adds confirmation and the search roles; positive and negative controls use different point_ids. No S repeats within a study, with one exception: C2's seed_group, whose runs share S on purpose so that paired comparison reduces the variance of differences (§C.6 C2.1, C2.3). The S of design evaluations is defined in §C.

### §R.5.2 Blocks and batch means

- Block size B and block count K (K ≥ 16) are declared before the first evidence run; N = K·B.
- From the summary, each block b gives an estimate θ_b (mean, fraction, ratio, quantile, mode); report θ̄ = the mean; SE = sd(θ_b)/√K, with K − 1 degrees of freedom.
- Blocks are non-overlapping event ranges of the same run. Events are independent (guaranteed by the seeds with `per-event`; the standard Monte Carlo assumption with `stream`), so block estimates are independent.
- One run is enough to estimate the SE; there is no need for several processes for statistics, and job splitting is only for parallelism.
- Precondition: no state carried between events (adaptive biasing, cross-event caches and the like). The probe records biasing and related settings; when in doubt, use several independent logical runs instead.

### §R.5.3 Estimators

- **Several observables:** the vector of per-block estimates is kept together; covariances between observables are estimated from these vectors.
- **Full-sample values:** means and fractions also from the merged accumulators; the difference from θ̄ goes into the record as a diagnostic.
- **Quantiles:** linear interpolation within a histogram bin; the bin width must be below 1/10 of the tolerance; a quantile in the overflow or underflow bin makes the estimate incomplete. From C2, with a `values` accumulator, the empirical quantile within each block is used instead.
- **MPV:** per block, take the highest histogram bin and interpolate the mode with a three-point parabola through it and its neighbours; report the mean of the K modes. At design time a toy shows the bias's 95 % upper bound ≤ tol/10 (the toy uses Landau–Vavilov, checked against the shape from one high-statistics Geant4 run); at every run, the difference between θ̄ and the mode of the merged histogram must be ≤ tol/5 + 2·SE, otherwise the benchmark is incomplete.

### §R.5.4 Small counts

- When a counting estimator has a block at 0, or a merged total < 100 (the threshold can be declared), exact intervals on the merged accumulators are used instead: Clopper–Pearson for fractions, Garwood for counts; comparing two runs uses the exact conditional binomial interval for the ratio of the rates, with relative difference = ratio − 1.
- There is no SE in these cases; the gate decides on interval endpoints (§R.6.6), and event planning uses the Poisson variance of the trial run.

### §R.5.5 Two-stage event count

N = ceil(N_trial·(SE_trial/target)²·f), with f = F₀.₉₀(K − 1, K_trial − 1) (≈ 1.97 when both are 16). About 10 % of evidence runs miss their target and are incomplete, with no top-up; F₀.₉₅ (≈ 2.40) brings this to about 5 % at about 22 % more events.

### §R.5.6 What reproducibility means

| Level | Requirement |
|---|---|
| traceability | every record keeps hashes of the spec, effective config, code (`sources_sha256`), seeds, and input and output files |
| re-execution | same build and platform, same logical run: bit-identical event content and identical integer accumulators; across platforms (libm's log, cos etc. are not guaranteed bit-identical) floating-point accumulators within a relative difference of 1e-12, built with `-ffp-contract=off` |
| replay (from committed T3 and T4) | decisions and labels identical; numbers within a relative difference of 1e-9; any decision whose margin is < 1e-9 (relative) is flagged "close to threshold" in the record |
| regression check (A2) | J14's existing specs (`seeding: stream`) produce, on the same host, CSVs bit-identical to those from before A2; files are only added, existing output is unchanged |

---

## §R.6 Validation classes and decisions

### §R.6.1 Five classes

| Class | Reference | Examples | Statistics | Can upgrade |
|---|---|---|---|---|
| verification | an exact consequence of the inputs | charged geantino against the analytic helix, kinematics, least-squares algebra | deterministic comparison or IUT | no |
| physics reference (reference) | a physics model Geant4 approximates, or a published thin-target measurement, on an isolated target | Bethe stopping power, Landau–Vavilov MPV, geant-val-style thin-target tests | IUT (scalars); χ² (distributions, §R.9.2) | yes (in scope) |
| setup-matched measurement (setup-matched) | a published measurement whose configuration has the same target hash | a test-beam longitudinal profile, a module's response and resolution | as above, plus the measurement uncertainties | yes (in scope) |
| regression | the same study's result with the previous software or Geant4 version | MPV, histogram shapes before and after a change | difference and SE for scalars; χ² p-value for histograms | no; only flags "changed" and may trigger an advisory |
| model-to-model (surrogate) | a full simulation such as Geant4, as the reference for fast simulation or an ML surrogate | a parametrized calorimeter against Geant4 | IUT or χ² | cannot upgrade physics labels; the surrogate itself may get a "consistent with the reference simulation in scope" mark. Deferred from 2026-10-24, not in CV-B2 (fast simulation in a design context is expressed by main's fidelity and bound) |

There are also `sanity` (a rough plausibility check) and `interface` (an interface check); neither can upgrade.

### §R.6.2 Benchmark table (CV-A1, extended in CV-B2)

`contracts/validate.py` carries its own table; `_study_upgrade` takes class, grade, kinds and scope dimensions only from it.

| Benchmark | Class | Supported kinds | Scope dimensions |
|---|---|---|---|
| `stopping-power` | reference | `stopping-power` | particle, material, energy, thickness |
| `range` | reference | `range` | particle, material, energy, thickness |
| `thin-layer-mpv` | reference | `most-probable-value` | particle, material, energy, thickness |
| `thin-layer-width` | sanity | `thin-layer-width` | particle, material, energy, thickness |
| `multiple-scattering` | sanity | — | — |
| `em-shower-shape` | sanity | — | — |
| `shower-containment` | sanity | — | — |
| `longitudinal-profile` | setup-matched | `shower-maximum` | particle, energy, target hash |
| `published-data` | interface | — | — |
| added in CV-B2: J15's checks (`field-propagation` and others) | verification or sanity | — | — |
| added in CV-B2: `regression-comparison` | regression | — | — |
| added in CV-B2: a tracking reference benchmark (multiple-scattering angular width in an isolated Si slab against PDG Highland / Lynch–Dahl, with a negative control; item iv of the F4 qualification path, §R.15.5) | reference | see §B | rigidity, species (see also §B) |
| deferred: `surrogate-comparison` | surrogate | — | — |

The scope of `regression-comparison` is the intersection of the two compared studies' scopes, re-derived by `dependencies.py` (the CV-B2 table of §B governs).

A record whose class or grade disagrees with the table, or whose name is not in it, is an error. `GRADES` in `geant4_benchmarks.py` stays for the tool, with a consistency test.

### §R.6.3 Scope (CV-A1)

- Compare the controlled `observable.kind`; `label` writes it into `declared_scope.observable_kind`.
- The dimension list is declared per benchmark (fourth column of 6.2), each dimension typed: categorical or a numeric range; a scalar is [v, v]. A new use case adds dimensions by changing the table only.
- A declared scope missing a dimension the benchmark has is outside.
- With a target-hash dimension, the declared scope must carry the same `target_geometry_sha256` and `hash_scheme`.
- Gating: `strict or _at_least(contract_version, CV-A1)`, no warning branch.

### §R.6.4 Configuration and isolation (CV-A1)

- **Target:** the benchmark config declares `target_slabs` (A1, `layered_sim`) or a list of target volumes (from A2, matching placements in the geometry tree).
- **Vacuum:** the world material is `G4_Galactic`, or its density is < 1e-20 g/cm³.
- **Isolated:** the world is vacuum and every placement other than the world belongs to the target; a field attached only inside the target is part of the target and enters the hash; a field extending beyond the target makes it embedded.
- **Derivation and hash versions:**

| Stage | Derived from | `hash_scheme` |
|---|---|---|
| A1 | `layered_sim`'s spec/1 (for `layered_sim` the spec is the actual geometry; A2 checks it against the geometry tree) | `spec-v1` |
| from A2 | the geometry tree of the effective config (any backend) | `tree-v1` |

- Comparisons happen only within the same `hash_scheme`; `dependencies.py` re-derives with the record's `hash_scheme`. J14 uses no target-hash dimension and is unaffected by the switch.
- A backend with declarations only can run and be published but cannot upgrade.
- **Contract rule:** every counted benchmark must be isolated (reference), or both isolated and matching the target hash of the measured setup (setup-matched); `dependencies.py` must re-derive from the run records in `evidence_records` and compare.

### §R.6.5 Regression and model-to-model (CV-B2)

- **Regression:** the same study with the same settings runs once on each of two versions (plugin, backend or Geant4) (point_id is the version tag, so the samples are independent), and every scalar observable is compared. Three outcomes: `changed` (|diff| − t_{1−α/m}·se_diff > tol), `unchanged` (the pass rule of §R.6.6), `unresolved`; "not significant" does not mean "unchanged". Histogram comparison is deferred to distribution-level benchmarks. Labels are not affected; a reference observable marked `changed` can trigger a sci-fix check.
- **Model-to-model (deferred from 2026-10-24):** a surrogate never changes the physics label. A surrogate's study declares its reference study (a study record) and scope; decided by IUT (χ² only as a diagnostic). On pass, `extension.study.surrogate` is recorded (reference study's reference and hash, scope the intersection of the two).

### §R.6.6 Convergence gate (IUT)

- **Difference:** a is the finest setting, b the second-finest; in `relative` mode diff = (a − b)/b and se_diff = √(se_a² + se_b²)/|b|, in `absolute` mode diff = a − b and se_diff = √(se_a² + se_b²) (the two points are independent logical runs); ν by Welch's formula for each pair. From C2 a paired mode can be declared (`pairing: paired`): both points are in one seed_group with equal K and B, se_diff is estimated from per-block differences, ν = K − 1 (defined in §C.6 C2.1); independent remains the default.
- **Event-count target:** each point's se target is tol/(4√2), so that se_diff ≤ tol/4.
- **Decision:** pass: |diff| + t₀.₉₅(ν)·se_diff ≤ tol, and both points meet their se target; fail (possible even with a missed target): |diff| − t_{1−α/m}(ν)·se_diff > tol, with m the number of (parameter × observable) pairs; otherwise unresolved. For small counts, interval endpoints: pass = the 90 % interval lies within [−tol, tol]; fail = the one-sided 1 − α/m interval lies entirely outside.
- **Reporting:** unresolved and missed targets are `incomplete` (exit 3) and the label stays `unvalidated`; only fail is `failed` (exit 1).

**Operating characteristics** (α = 0.05, 2×10⁶ simulated trials; recompute with `gate_operating_characteristics.py` in this folder; model in task A's A1.8):

| True difference | Pass (se = target) | Pass (two-stage) | Pass (two-stage, given both points met the target) | Fail m = 1 (se = target) | Fail m = 30 (se = target) | Fail m = 30 (two-stage) |
|---|---|---|---|---|---|---|
| 0 | 0.976 | 0.809 | 0.999 | 0.000 | 0.000 | 0.000 |
| tol/2 | 0.621 | 0.696 | 0.860 | 0.000 | 0.000 | 0.000 |
| tol | 0.050 | 0.044 | 0.054 | 0.050 | 0.002 | 0.002 |
| 2 tol | 0.000 | 0.000 | 0.000 | 0.988 | 0.780 | 0.952 |

At a true difference of tol about 90 % of results are unresolved, which is inherent to an equivalence test. Under the two-stage design about 19 % of point pairs are incomplete because one point missed its target. The independent review of 2026-10-23 found that the old two-stage columns double-counted the trial χ²; they have been recomputed.

### §R.6.7 Negative controls and the detection limit

- Decision quantity: shift = (control − nominal)/reference, with the SE combined from both runs.
- Detection limit: DL = tol + |rel| + t_{0.977}(ν)·se_rel.
- Caught: the control's benchmark verdict is fail (|rel_c| > tol).
- Design requirement: a toy shows that an injection at the DL is caught with probability ≥ 0.977; the true power is near 0.977, so the acceptance threshold is 0.977 − 3σ_MC (an A1 acceptance condition).
- Realization: inject both signs (otherwise restrict the claim to one sign); at the detection limit = caught and |shift| ≤ 1.1 × DL. A single miss is recorded and explained, does not fail automatically, and the control is never rerun with another seed.

### §R.6.8 Stopping rule and evidence correlation

- The stopping rule, scan grid, K and B, and the handling of unresolved results are written into the study spec before the first evidence run.
- `extension.study.evidence_overlap` lists runs shared by several decisions.

---

## §R.7 Contracts, traceability and sci-fix

### §R.7.1 CV-A1 (A1)

The table, scope and isolation rules of §R.6.2–6.4; `dependencies.py`'s re-derivation; an optional `simulation` property in `ext_computational_run.json` (needs hep-computing's agreement; fields in §A). `study` stays an open object so that B2 can add the fields F4 needs.

### §R.7.2 CV-B2 (B2)

The new entries of §R.6.2 (verification, `regression-comparison`, the tracking reference benchmark); the regression rules of §R.6.5; the transitive processing chain of §R.7.4; the F4 study-record fields `results` and `tail_sources_simulated` and asymmetric uncertainties for counting figures of merit; `design_geometry.json` 1.1.0. Gated like CV-A1. CV-C1 (C1) adds `search_summary`; CV-C2 (C2) adds one `design.py` rule: an evaluation whose run or study seed appears in a search summary is `design.contract_mismatch`; see §C.

### §R.7.3 sci-fix and advisories (A1)

The fixes of D1–D11 are recorded in main's current ledger format (`docs/maintenance.md`): one entry per fix (e.g. the variance method split into batch-means SE, exact low-count intervals and the MPV estimator); S1 with C4 where a closed form exists and a per-entry review sign-off; S3 in `documentation_fixes`. Advisories use format `/2` with `applies_to.match` groups; they cover wrongly upgraded study records and the F4 design-evaluations built on them (§R.15.5). Entries, severities and advisory numbers follow A1.14 in §A.

### §R.7.4 Tracing processing chains

- Every processing step (simulation, reduction, digitization and reconstruction, table) writes a computational-run record with `**trace.provenance()`, the configuration hash, hashes of input records and files, and the code hash.
- The input chain of a simulated table can be any depth, as long as every level is a recorded computational-run and every root of the chain is a simulation run (CV-B2; previously only one level).
- When calling a C++ executable, Python records the sha256 of the executable and its sources, the version and the subcommand, and tags the call with `trace.tag()`.

---

## §R.8 Code and CI

| Location | Change |
|---|---|
| `contracts/validate.py`, `dependencies.py` | §R.6, §R.7 |
| `contracts/schema.py` | `maxItems`, `maximum`, `exclusiveMaximum` (added in A2.7; needed by `element_sim`'s schema; no contracts version change) |
| `core/stats/`, `core/simulation/` | Block estimators, the study-level decision engine (A1's `equivalence` and `detection_limit`; B2's `change`; C2's paired mode), distribution functions, the seed hash, summary reading. They are in `core/` because both hep-detector's scripts and the geant4 adapter need them, and the layering rules let adapters import only `core` and `contracts` (§A.3 rule 1, §A.4.5); `core/` may import only `core`, so the summary schemas live in `contracts/schemas/` and scripts validate them with `contracts.schema`. Main's existing functions (the Garwood interval, `toy_ensemble`) are reused, not rewritten |
| `skills/hep-detector/scripts/` | inference and decisions read only boundary artifacts; geometry facts (minimum thickness, configuration) come from the effective config, records from before A2 still from spec/1; `check_geant4_study.py label` writes the F4 fields (B2); `evaluate_design.py` gains the `search` subcommand (C1) and fixes `f4`'s `--label-run-record` pass-through and exit codes (A1); no new script; `SKILL.md` and description unchanged |
| `contracts/design.py`, `contracts/rules/design_geometry.json` | counting uncertainties for F4 and mapping 1.1.0 (B2); the orphan-rule exemption of `search_summary` (C1); the search-seed rule (C2) |
| `adapters/geant4/assets/` | `g4sim/`; `layered_sim/` gains `g4sim`; `geant4_run.py` (logical runs and job splitting, the A1 Python summary producer, B1's `from-geometry`, B2's `reco` and `table`); B1 `element_sim/` and `simroot`; B2 `simreco` |
| `adapters/design-bo/` | C3's optional backend (Ax/BoTorch); the only adapter this program may add |
| `SIM_SOURCES` | covers `g4sim` and the sources of each program |
| CI | task A needs no new required CI job; a ctest of `SimSummary.hh` can be an optional job. whether B2's `simreco` C++17 CI job is required is the maintainer's decision (§P.7 item 9, proposed: required) |

---

## §R.9 Generality

### §R.9.1 Use cases covered

| Use case | Supported by | Status |
|---|---|---|
| material-level references (J14-like) | the reference class, isolated slabs | A1 |
| spectrometers with a field (J15, compared with PAMELA and AMS-02) | `element_sim`, the field counted in the target, verification, the reconstruction chain, the F4 study-record interface | B1, B2, B3 |
| automated detector design (J16) | `evaluate_design.py search` (D2 candidate generator), F4 confirmation with fresh seeds; requirement verdicts and comparison by `contracts/design.py` | C1–C3 |
| test beams and modules (compared with data) | the setup-matched class, target hashes from the geometry tree, per-benchmark scope dimensions | contracts in A1 and A2; geometry from a user application or `element_sim` |
| rare events | exact counting intervals | A1 |
| software or Geant4 changes | the regression class | B2 |
| fast simulation, ML surrogates | the surrogate class, reducers | deferred (moved out of B2 on 2026-10-24); reducers at the first need |
| other engines or frameworks (FLUKA, Key4hep) | the output interface, reducers | interface ready; converters deferred |

### §R.9.2 Interfaces defined now, implemented later

| Interface | Content | First use case |
|---|---|---|
| distribution-level comparison | χ² on summary histograms (statistical uncertainties on both sides; measurement uncertainties when the reference is a measurement) | the first benchmark with a shape as its observable, or the first regression check |
| observable combinations and selections | a linear combination of columns, the ratio of two columns; AND of column-against-constant comparisons | the first study that needs an event selection |
| profiles and 2D histograms | n, Σy, Σy² in bins of x; 2D counts | the first study with a spectrum source; J15 runs at fixed rigidities and does not need it |
| sources | `gps` (declarative settings only), `event-file`; the summary records the source area and solid angle for flux normalization | the first spectrum or flux study |
| `simreduce` | reads event files (through `simroot`) or external formats and writes summaries as declared | the first observable decided after the fact, or the first external backend |

### §R.9.3 Deferred (with triggers)

| Item | Trigger |
|---|---|
| weighted accumulation and biasing rules | the first study with biasing |
| non-box solids, rotations and GDML input in `element_sim` | the first study that needs them and cannot use a user application |
| rule packs and probes for other engines | the first non-Geant4 backend |
| a reducer for EDM4hep | the first Key4hep backend |
| optical photons, long time windows, decay chains | the first scintillator or rare-event study |
| ion sources and Birks | a cosmic-ray nuclei study and a literature record for PVT's Birks constant |
| probes for several Geant4 versions | the first application on a version other than 11.4 (the regression class will need it first) |
| `physics_config_comparison` | a study that needs to compare physics settings |
| RNTuple, vector columns | ROOT file size or read speed becomes a bottleneck |

### §R.9.4 Deliberately not done

- An engine abstraction layer (VMC-style): abstraction at the output is enough, and ALICE's experience shows API-level abstraction is costly.
- A processing framework (Gaudi-style), a validation database and website (geant-val-style): they solve the scale problems of large collaborations and break the plugin's constraints.
- A general expression language, a plug-in system for estimators, one probe content for all engines.
- Integer quantization and bit-identical statistics (§R.13).
- Topping up, refining or reseeding controls based on results.
- The `uses-validated-physics` label, contracts 4.0, Python bindings, a content-addressed cache, `simstat`, a Geant4-free `simcore`.
- An own requirements spec, own requirement verdicts, candidate ranking or a "recommended design", and any claim of a global optimum: these belong to main's `contracts/design.py` and human gates (§R.15.2, §R.15.3).

---

## §R.10 Stages and acceptance

Before 2026-10-23 this section copied the content and acceptance of each stage, which easily drifted from the task specs, so it now points to them. Stage order, scope boundaries, interface ownership, gates and open decisions are defined in Part 1; the work items and acceptance of each stage are defined in the task specs.

| Stage | In one sentence | Spec |
|---|---|---|
| A1 | Fix the defects that wrongly issue `validated-in-scope`; shared statistics and summary modules in `core/` (contracts CV-A1) | §A.5 |
| A2 | `g4sim`, `per-event` seeding, `layered_sim` writes the three boundary artifacts, study layer reads only them | §A.6 |
| B1 | `element_sim`, field, plane crossings, calorimeter leakage, per-event ROOT files, `simroot`, `check-spec` | §B.5 |
| B2 | `simreco`, tail sources, processing chains, verification / regression, the F4 study-record interface and qualification path (contracts CV-B2) | §B.6 |
| B3 | J15 as a design project: F1, F2 and F4 per (figure of merit, denominator) | §B.7 |
| C1 | `evaluate_design.py search`: in-process search at main's F1, writes `search_summary`, `expand`s finalists; closure tests (contracts CV-C1) | §C.5 |
| C2 | Geant4 search values, paired comparison, F4 confirmation with fresh seeds (contracts CV-C2) | §C.6 |
| C3 | J16: search examples on Examples A and B, optional `adapters/design-bo/` | §C.7 |

---

## §R.11 Residual risks

1. J14's detection limits may change with block batch means, t quantiles and controls in observable units, and the controls may need redesigning.
2. Block batch means has an O(1/B) bias for ratios, quantiles and modes of skewed distributions that K does not reduce; the coverage toy allows ±0.02, and B is raised if needed.
3. Block independence fails when state is carried between events; the probe records the relevant settings, and several independent logical runs are used when in doubt.
4. Under the two-stage design about 10 % of evidence runs miss their target (§R.5.5).
5. With tolerance comparisons, decisions close to a threshold may differ across platforms; handled by margin flags and "the CI platform decides".
6. Two Geant4 programs: `layered_sim` is frozen in maintenance mode, and `g4sim` keeps duplication down.
7. The probe assumes workers match the master; if a thread-local difference appears, dump per thread.
8. When a target hash is matched to a published measurement, the contract can only compare hashes, not decide that the target is the configuration in the paper; a reviewer still checks.
9. The reading ability of `G4RootAnalysisReader` is unverified (the B1 trial).
10. Only 931 bytes of quick-load budget remain; this architecture does not change `SKILL.md` or the description (main's hub link provides the entry to the design loop).
11. Effort: the prototype estimates A1's contract part at about 8–12 engineer-days plus Geant4 time; the rest is not estimated.
12. Until the maintainer approves the detector-level F4 qualification path (§R.15.5), J15's and task C's confirmation studies can only be `unvalidated`, and design.py will not count them as F4.

---

## §R.12 Decision record

### §R.12.1 Decided by the user

| Date | Decision | Where |
|---|---|---|
| 2026-10-22 | core code in C++, Python as the interface; compute core in C++, reference values stay in Python; separate executables exchanging JSON/CSV, no Python bindings | principle 2 (as interpreted by item 1 of 12.2) |
| 2026-10-22 | J15's TOF1 and TOF2 two layers each, all four of the same material | §B |
| 2026-10-22 | detailed per-event information stored in ROOT files | §R.4.1 T1, B1 |
| 2026-10-22 | J15 split from the rest into a second task, done later | task A (A1, A2), task B (B1, B2, B3); task C added later (§P.0) |
| 2026-10-24 | full rewrite to plug into main's design loop; task C's search is `evaluate_design.py search`; detector-level Geant4 studies become F4 through a qualification path | §R.15, §P.0 |

### §R.12.2 Proposals of this part (need the user's confirmation)

1. **Interpreting the language split:** per-event computation (simulation, digitization, reconstruction, accumulation) in C++; inference after merging in Python.
2. **A backend interface at the output** (three boundary artifacts), no engine abstraction layer.
3. **Event determinism:** `seeding: per-event` by default for new specs; job splitting and thread count do not affect events.
4. **Reproducibility means "same decisions"**, with numbers compared within tolerances; no integer quantization and no bit-identical statistics.
5. **Block batch means:** K ≥ 16 blocks by event number within one run; J14 runs with per-event data are recomputed offline without re-recording.
6. **A new `element_sim`**, with `layered_sim`'s spec format unchanged; both share `g4sim`.
7. **Five validation classes**, with regression added in CV-B2 (B2); surrogate deferred.
8. **Eight stages** (A1, A2, B1, B2, B3, C1, C2, C3; §P.0), with ROOT files and `simroot` in B1.
9. The two-stage factor F₀.₉₀ or F₀.₉₅; the threshold for exact intervals (any block at 0 or a total < 100).

### §R.12.3 For the maintainer to decide

The merged list and its proposals are in §P.7; this part's original seven items are all included there.

---

## §R.13 History: superseded designs

| Previous design | Replaced by | Basis |
|---|---|---|
| `simstat` and a Geant4-free `simcore`: moving run-level statistics to C++ | inference stays in Python, reading merged summaries | little code and data, no gain from C++, and replay would need a compiler (soundness assessment P1); CMS DQM also decides only after merging |
| spec/2, `layered_sim convert`, a dual-format accessor, a same-host bit-identical gate | `layered_sim`'s format unchanged; a new `element_sim` | the most costly, least valuable step; a new program leaves J14 untouched and gives a real second backend |
| integer quantization, a two-word 128-bit integer, round half to even, `%.17g` needed for recomputation | compensated floating-point sums; integers only for counts and histograms; reproducibility defined as same decisions | bit identity is not a scientific need; real experiments aim at reproducible events and traceable sources |
| 16 independent processes per evidence run | blocks by event number within one run | batch means is batching within a run; per-event seeds make job splitting irrelevant to statistics |
| per-event seeding forced only for bit identity | per-event seeding as the default for new specs, for event determinism | the practice of ATLAS and Allpix² |
| an interface-only synthetic backend | `element_sim` as a real second backend | third check R19 |
| validation as grades only (reference, sanity, verification, interface) | five validation classes, adding regression and surrogate | geant-val, Belle II, ATLAS AtlFast3 |
| task C's own requirements spec `detector-requirements/1`, component catalogue and design format `detector-design/1` | main's design-spec and design-candidate; the genome is only the optimiser's internal encoding, decoded into `overrides` on a base candidate | main 0.37.0 already has these artifacts (2026-10-24 review C4, C5) |
| task C's fidelities F0, F1, F2 | main's F0–F5: the old F0 is main's F1; short Geant4 runs inside a search are search values only; confirmation is F4 | name clash (review P2) |
| task C's requirement verdicts (`threshold`), `order`, own Pareto and "recommended design" | `contracts/design.py` derives verdicts, screening, ranking and Pareto; no optimum is claimed | main's rules (review C2, C3) |
| `realize()`: design -> spec | `evaluate_design.py geometry` writes `design-geometry/1`, B1's `from-geometry` derives `element_sim.spec/1` | main already has the geometry step (review C6, B4) |
| `adapters/detector-design/` and its version series | `evaluate_design.py search`; only the optional Bayesian-optimisation backend is an adapter | an adapter is an optional component connecting an external tool (review P3) |
| the surrogate class B2 added for task C | deferred | fast simulation in a design context is expressed by main's fidelity and bound (review's B re-plan) |

Still valid from the previous version (merged here): the fixes of D1–D10, the contracts grade table and per-benchmark scope dimensions, the isolation and field definitions, versioned target hashes, the IUT gate and its t-based operating characteristics, exact counting intervals, MPV interpolation with two bias checks, the t-based detection limit, the two-stage event count, the event-weight restriction, the probe's content and timing, the ROOT file design, J15's design. Of the 25 findings of the third deep check, R11, R12, R16 and R18 no longer apply because the design changed, R19 is resolved by `element_sim`, and the rest are merged.

---

## §R.14 Sources

- ATLAS Collaboration, *Software and computing for Run 3 of the ATLAS experiment at the LHC*, [arXiv:2404.06335](https://arxiv.org/pdf/2404.06335) (random numbers: §R.3.1; data formats: §R.2.3)
- ATLAS Collaboration, *AtlFast3: the next generation of fast simulation in ATLAS*, [arXiv:2109.02551](https://ar5iv.labs.arxiv.org/html/2109.02551)
- CMSSW `RandomNumberGenerator.h` ([LXR](https://cmssdt.cern.ch/lxr/source/FWCore/Utilities/interface/RandomNumberGenerator.h)); DQM `README.md` ([LXR](https://cmssdt.cern.ch/lxr/source/DQMServices/Core/README.md)); `ProcessHistory` ([doxygen](https://cmsdoxygen.web.cern.ch/cmsdoxygen/CMSSW_12_3_2/doc/html/d8/d42/ProcessHistory_8cc_source.html))
- S. Banerjee, V. Ivanchenko (CMS), *Validation of physics models of Geant4 using data from the CMS experiment*, [EPJ Web Conf. CHEP 2021](https://www.epj-conferences.org/articles/epjconf/abs/2021/05/epjconf_chep2021_03010/epjconf_chep2021_03010.html)
- *Simulation in ALICE* (Virtual MC), [physics/0306092](https://ar5iv.labs.arxiv.org/html/physics/0306092)
- Key4hep, *Progress Report on Integrations*, [arXiv:2312.08152](https://arxiv.org/html/2312.08152v1)
- Allpix², [multithreading documentation](https://allpix-squared.docs.cern.ch/docs/04_framework/10_multithreading); [arXiv:1806.05813](https://arxiv.org/pdf/1806.05813)
- *Geant-val: a web application for validation of detector simulations*, [EPJ Web Conf. CHEP 2018](https://www.epj-conferences.org/articles/epjconf/abs/2019/19/epjconf_chep2018_05002/epjconf_chep2018_05002.html)
- Belle II, *Tools for Physics Validation of the Software* ([basf2 documentation](https://software.belle2.org/release-09-00-15/sphinx/_sources/validation/doc/index.rst))
- *The PAMELA Space Experiment*, [arXiv:0905.2551](https://ar5iv.arxiv.org/html/0905.2551)
- *The AMS-02 Time of Flight System*, [astro-ph/0206021](https://ar5iv.labs.arxiv.org/html/astro-ph/0206021)
- hep-research `9f08796`: `adapters/geant4/assets/geant4_build.py` (line 53, `GEANT4_USE_GDML: OFF`), `layered_sim/Actions.cc` (lines 23, 113), `examples/geant4-thin-silicon/recorded/`, `check_geant4_study.py` (line 357), `geant4_benchmarks.py` (line 274)

---

## §R.15 Relation to main's detector system design loop (2026-10-24)

main 0.37.0–0.38.0 added a detector system design loop to hep-detector (`references/system-design-workflow.md`, `contracts/design.py`, `scripts/evaluate_design.py`). On 2026-10-24 this program was changed to plug into that loop rather than build a second one; this section gives the reasons for the division of work.

### §R.15.1 Fidelity and where Geant4 sits

| Fidelity (main) | Meaning | What this program provides |
|---|---|---|
| F0 | heuristic argument, no run | — |
| F1 | analytic, run through a tool contract (`tracker_resolution`, `multiple_scattering`, `design_estimates` and others) | C1's search inner loop uses the same functions in-process |
| F2 | toy Monte Carlo (`toy_spectrometer`, `design_estimates.py infield-acceptance`) | B3 runs them on the J15 candidates, replacing hand comparisons |
| F3 | response assembly and expected precision (hep-statistics Asimov fit) | — |
| F4 | a Geant4 study re-issued `validated-in-scope` by `check_geant4_study.py label --upgrade` | A1 makes the label correct; B1 and B2 make spectrometer studies possible and write the F4 fields; B3 (J15) and C2's confirmation produce F4 |
| F5 | prototype or test-beam measurement | — |

Short Geant4 runs inside a search have no fidelity and are not evaluations; they are search values stored in the `search_summary`. Reason: F4 requires a qualified study; search runs trade statistics for speed and are entangled with the selection (the winner's curse), so they must not count as evidence.

### §R.15.2 Who owns verdicts

Whether a requirement is met, maturity, staleness, screening, the comparison basis, ranking and the Pareto front are all derived by `contracts/design.py` from the artifacts, never written by hand (the workflow's "Never" section). This program's statistical decisions (`core/stats/decisions.py`'s `equivalence`, `detection_limit`, `change`, the convergence gate and paired comparison) answer only study-level questions: did a benchmark pass, did a run converge, did a result change between versions, is the difference between two designs in a search resolved. Reason: they are inputs to a study label; requirement compliance also needs the adequacy table, the bound combination and the upstream chain, which only `design.py` has. Task C's own requirement verdicts (`threshold`), `order` and "recommended design" are therefore deleted (§R.13).

### §R.15.3 No optimum claimed; human gates

main ranks only when the comparison basis holds and every surviving candidate has a non-optimistic expected-precision evaluation with the same fidelity vector and denominator; a Pareto dominance is decided only beyond the combined 1σ; a global optimum is never claimed; gates H1–H4 need a human. Task C is therefore a D2 candidate generator: a search population of order 10⁴ stays in the `search_summary`, only finalists become candidates through `expand`, and they then go through the ordinary `evaluate_design.py run` and `report`. The winner's curse is handled by requiring confirmation through F4 studies with fresh seeds, enforced by CV-C2's rule: an evaluation whose seed appears in a search summary is `design.contract_mismatch`.

### §R.15.4 Parameter-level staleness and incremental reruns

main's evaluations bind the candidate by `parameter_digest`: they go stale only when a parameter they read changes; `run_workflow.py --incremental` skips on argv, scripts, the plugin release digest, the environment and the inputs. Task C therefore has no design-cache rules of its own, only the search-internal cache key (including S, N, K, B); `geant4_run.py run` also writes `argv`, `script_sha256` and `versions.plugin_release` as `run_workflow.py` does (A2).

### §R.15.5 The F4 study-record interface and the qualification path

What `design.py` requires of F4: the study record is `validated-in-scope`; the geometry file written by `evaluate_design.py geometry` (`design-geometry/1`) is in the `input_manifest`, and its parameter digest matches the candidate; `extension.study.results.<figure of merit>` has `value`, `statistical_uncertainty` and `model_envelope`; `tail_sources_simulated` lists which tail sources were simulated (only with all four of alignment, calibration-non-uniformity, noise-digitization and pattern-recognition is the bound `estimate`, otherwise it is `optimistic`).

How this program meets it: B1's `from-geometry` derives `element_sim.spec/1` from the geometry file and a declared realization profile; B2's `simreco` makes the four tail sources switchable stages, and `label` writes `results`, the tail sources and the geometry file; `statistical_uncertainty` is defined as the 68.27 % t half-width (A1), consistent with `design.py` reading it as a Gaussian with coverage 0.6827; one study per (figure of merit, denominator), because a candidate has one `geometry_ref` and `results` is not keyed by denominator.

**Qualification path (D0, pending the maintainer's approval).** Detector-level studies (resolution, charge confusion, shower containment) have no matching physics reference and can never be upgraded under the current rules. The program chooses a qualification path rather than letting `design.py` accept unvalidated F4: (i) every material of the study lies inside the scope of a passed A1 material benchmark; (ii) the field-propagation verification (B1's analytic helix) passed for its field configuration; (iii) the reconstruction verification (`simreco` against known truth) passed; (iv) a new tracking reference benchmark passed (multiple-scattering angular width in an isolated Si slab against PDG Highland / Lynch–Dahl, with a negative control, scope dimensions rigidity and species). Reason: `validated-in-scope` keeps a single meaning across the plugin; item iv gives detector-level studies a physical anchor, and the first three ensure the rest of the study is correct inference.

### §R.15.6 Extension point: geometry kind -> realizer

`contracts/rules/design_geometry.json` maps a candidate's parameters to a geometry kind (today only `layered-spectrometer`). Each kind needs a realizer that turns the geometry file into a backend's spec: `element_sim` (B1's `from-geometry`), a user's Geant4 application (including `g4sim`) or a GDML file when the user's build has GDML, later DD4hep. Adding a detector kind = one mapping entry (contracts) plus one realizer; the study layer reads only boundary artifacts and does not change. C1's search is driven by tool contracts, so at F1 and F2 it does not depend on the detector kind; its Geant4 part can use only geometry kinds with a realizer (today spectrometers; B2's mapping 1.1.0 adds fields for TOF and EM calorimeters).

### §R.15.7 Why the search is not an adapter

An adapter is an optional component that connects an external tool, and no skill or core module may depend on it (the opening of `docs/adapter-authoring.md`). The search is plugin logic over main's artifacts, so it lives in `evaluate_design.py search`, following main's precedent of making `scan` a subcommand (OQ-18). Only the optional Bayesian-optimisation backend (Ax/BoTorch) is an external tool, hence `adapters/design-bo/`.