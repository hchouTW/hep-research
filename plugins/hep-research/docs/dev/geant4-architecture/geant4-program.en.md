# Geant4 simulation studies, the J15 minimal spectrometer and automated design search: consolidated document

> Document type: consolidated plan, implementation specs and design rationale (for the implementing agent, reviewers and the maintainer). Status: awaiting the user's and the maintainer's approval
> Baseline: hep-research `main` at `9f08796` (0.23.0 plus unreleased changes), contracts 3.5.0, adapter geant4 0.1.0, Geant4 11.4.3
> Date: 2026-10-23
> Language: English translation of the Traditional Chinese original [`geant4-program.md`](geant4-program.md), with the same content. If they disagree, the Chinese wins and the English is corrected at the same time
> Execution environment: **every stage runs in its own isolated git worktree** (§P.10); never change the main checkout or another worktree

## How to use this document

**For the implementing agent:**
1. Read §P.0 (stages at a glance), §P.10 (running in an isolated worktree), §P.6 (gates) and §P.4 (interface ownership).
2. Create and confirm the isolated worktree for your stage per §P.10.2 (`.claude/worktrees/geant4-<stage>`, branch `worktree-geant4-<stage>`, based on the latest `origin/main` that contains the prerequisite stages); every later step happens in it.
3. Read the task card of the part your stage belongs to (§A.0, §B.0 or §C.0), then that part's §1–§4 and your stage's work items and acceptance checklist.
4. Read Part 5 only when you need the reason for a rule.
5. This document is about 2,800 lines: read it in pieces by section number from the table of contents (e.g. search for `## §A.5`), not all at once.

**Authority of each part:**

| Part | Sections | Content | Authority |
|---|---|---|---|
| Part 1 Program plan | §P | Evaluation, principles, stages, interface ownership, naming, gates, open decisions, risks, execution environment | Stage order and dependencies, numbering, version placeholders, interface ownership, gates, open decisions, execution environment |
| Part 2 Task A | §A | Work items and acceptance of A1, A2; the shared hard rules (§A.3) and checks (§A.8) | Content and acceptance of these two stages |
| Part 3 Task B | §B | J15 design; work items and acceptance of B1, B2, B3 | Content and acceptance of these three stages; J15's numbers |
| Part 4 Task C | §C | Design of automated design search; work items and acceptance of C1, C2, C3 | Content and acceptance of these three stages |
| Part 5 Design rationale | §R | Design basis from real experiments, the architecture, superseded designs | Rationale only; where it conflicts with Parts 2–4, Parts 2–4 win and the conflict is reported |

**Numbering:**
- Sections: "§A.8" is section 8 of Part 2 (task A), "§P.10.2" is section 10.2 of Part 1, "§B Appendix A" is appendix A of Part 3.
- Work items: "A1.6", "B2.1", "C2.4" (stage.number), unique across the whole document.
- Contract versions: CV1 (A1), CV2 (B2), CV3 (C2), numbers fixed at merge; the whole document (Part 5 included) uses CV1–CV3, and "C1", "C2" mean only stages.
- Parts 2–4 share one structure: §X.0 task card, §X.1 terms and files, §X.2 prerequisites and provided interfaces, §X.3 hard rules, §X.4 design summary, from §X.5 one section per stage (work items and acceptance checklist), then contracts and versions, checks, not done and deferred, open decisions and risks, order of work, appendices.

**Consolidation note:** on 2026-10-23 the previously separate `plan.md`, `task-a-core.md`, `task-b-j15.md`, `task-c-design-search.md` and `architecture.md` (and their English versions) were merged into this document with unchanged content; only section numbers and cross-references were rewritten, and the old files were removed. Each part's version history stays in that part's appendix. The programs computing design numbers (`gate_operating_characteristics.py`, `j15_design_estimates.py`, `design_search_closure.py`) remain separate files in the same folder.

## Table of contents

- **Part 1 — Program plan (§P)**
  - §P.0 One-page summary
  - §P.1 Evaluation: problems of the earlier plan and how they are handled
  - §P.2 Planning principles
  - §P.3 Stage contents and acceptance (summary)
  - §P.4 Interface ownership
  - §P.5 Naming and numbering
  - §P.6 Stage gates
  - §P.7 Decisions for the maintainer (merged list)
  - §P.8 Main cross-task risks
  - §P.9 Document map and division of authority
  - §P.10 Execution environment: isolated worktree
  - §P.11 Version history
- **Part 2 — Task A: correctness fixes and boundary artifacts (§A)**
  - §A.0 Task card
  - §A.1 Terms and files
  - §A.2 Prerequisites and provided interfaces
  - §A.3 Hard rules
  - §A.4 Design summary
  - §A.5 Stage A1: correctness fixes (contracts CV1, sci-fix)
  - §A.6 Stage A2: shared headers and boundary artifacts (geant4 adapter 0.2.0)
  - §A.7 Contracts and versions
  - §A.8 Checks at the end of every stage
  - §A.9 Not done and deferred
  - §A.10 Open decisions and residual risks
  - §A.11 Suggested order of work
  - §A Appendix A: Statistics summary
  - §A Appendix B: Numbers
  - §A Appendix C: Baseline values (`9f08796`)
  - §A Appendix D: Sources
  - §A Appendix E: Version history
- **Part 3 — Task B: `element_sim`, reconstruction and the J15 minimal spectrometer (§B)**
  - §B.0 Task card
  - §B.1 Terms and files
  - §B.2 Prerequisites and provided interfaces
  - §B.3 Hard rules
  - §B.4 J15 design
  - §B.5 Stage B1: `element_sim` and event files (geant4 adapter 0.3.0)
  - §B.6 Stage B2: reconstruction and contracts (geant4 adapter 0.4.0, contracts CV2)
  - §B.7 Stage B3: J15 study
  - §B.8 Contracts and versions
  - §B.9 Not done and deferred
  - §B.10 Open decisions and residual risks
  - §B.11 Suggested order of work
  - §B Appendix A: Numbers
  - §B Appendix B: Sources
  - §B Appendix C: Version history
- **Part 4 — Task C: automated detector design search (§C)**
  - §C.0 Task card
  - §C.1 Terms and files
  - §C.2 Prerequisites and interfaces provided
  - §C.3 Hard rules
  - §C.4 Design
  - §C.5 Stage C1: requirements, grammar and fast search (detector-design 0.1.0)
  - §C.6 Stage C2: simulation evaluation and confirmation (detector-design 0.2.0, geant4 adapter 0.5.0, contracts CV3)
  - §C.7 Stage C3: example (detector-design 0.3.0)
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

---

# Part 1 — Program plan (§P)

> Date: 2026-10-23

---

## §P.0 One-page summary

Three tasks, eight stages; each stage is a change that can be merged on its own, with its own acceptance list:

| Stage | Task | In one sentence | Prerequisite | Version | Size |
|---|---|---|---|---|---|
| **A1** | A correctness | Fix defects D1–D8 and D10 that wrongly issue `validated-in-scope`; put the shared statistics and summary modules in `core/` | — | contracts **CV1** (sci-fix) | large |
| **A2** | A boundary artifacts | `g4sim` shared headers, per-event seeding, `layered_sim` writes the three boundary artifacts; the study layer reads only boundary artifacts (D9) | A1 | geant4 adapter **0.2.0** | large |
| **B1** | B new backend | `element_sim` (box elements, field, plane crossings, calorimeter leakage), per-event ROOT files, `simroot` | A2 | geant4 adapter **0.3.0** | large |
| **B2** | B reconstruction and contracts | `simreco`, result tables, transitive processing chains, verification / regression / surrogate classes | B1 | geant4 adapter **0.4.0**, contracts **CV2** | medium |
| **B3** | B J15 study | J15 validation ladder, convergence, variations, TOF sensitivity, journey | B2 | example and docs | medium (compute-heavy) |
| **C1** | C fast search | Requirements spec, component catalogue, design grammar, F0 analytic evaluation, NSGA-II, closure tests | A1 | detector-design adapter **0.1.0** | medium |
| **C2** | C simulation search | F1/F2 evaluation, confirmation runs, requirement decisions, paired comparison, robustness and guards | B2, C1 | detector-design **0.2.0**, geant4 adapter **0.5.0**, contracts **CV3** | large |
| **C3** | C example | J16 automated-design example (compared with J15), optional MOBO backend | B3, C2 | detector-design **0.3.0** | small to medium |

```
A1 ──▶ A2 ──▶ B1 ──▶ B2 ──▶ B3 ─────────┐
 │                    │                  ▼
 └──▶ C1 ─────────────┴──────▶ C2 ──▶ C3
```

The critical path to "automated detector design with simulation" (C2) is A1 → A2 → B1 → B2 → C2; C1 can run after A1 in parallel with A2 and B; the J15 physics study (B3) is not on C2's critical path and is only the comparison target of C3.

---

## §P.1 Evaluation: problems of the earlier plan and how they are handled

| # | Problem | Effect | Handling |
|---|---|---|---|
| P1 | **Scope creep in A1.** The previous round put features needed only by task C (one-sided threshold and order decisions, paired comparison, search roles, `values` accumulator) into A1 | A1 is a sci-fix that must quickly fix defects that already wrongly issue `validated-in-scope`; extra features add evidence and review burden and delay the fix | Principle R1 ("introduced by the first consumer"): A1 contains only what it uses itself; the decision engine's `change` is added in B2, `threshold` / `order` / paired comparison in C2; the location (`core/`) is fixed from the start |
| P2 | **Name clash.** "C1, C2" meant both contract versions and stages of task C | Agents and reviewers misread | Contract versions are written **CV1, CV2, CV3**; task C's stages are C1–C3 (§P.5) |
| P3 | **Critical path too long.** Task C waited for all of B2, and B2 mixed infrastructure (`simreco`, contracts) with the J15 physics study | Automated design held up by J15 research | B split into B2 (reconstruction and contracts) and B3 (J15 study); C2 waits only for B2; C1 waits only for A1 |
| P4 | **Interfaces in the wrong layer.** Statistics and summary reading were in hep-detector's scripts, which adapters may not import by the layering rules | Task C would need a second implementation | Shared code always in `core/`; §P.4 lists the location, owner and consumers of every interface |
| P5 | **Duplicated documents drift.** §R.10 copied each stage's content and acceptance, every change needed syncing, and inconsistencies appeared | Readers do not know which document wins | Division of authority (§P.9); §R.10 now points to this part |
| P6 | **Open decisions scattered** over three specs | The maintainer cannot see the whole picture, nor which decision blocks which stage | Merged into one table marking the blocked stage (§P.7) |
| P7 | **No gates between stages** | E.g. if ROOT reading capability or the deterministic field check fails, later stages would still proceed as planned | Explicit gates (§P.6) |
| P8 | **Only scattered effort estimates** | Cannot schedule | Relative size (small / medium / large) and the known estimate (A1 contract part about 8–12 working days); the rest estimated at the start of each stage (§P.0, §P.8) |
| P9 | **Cross-adapter dependency undefined.** Task C must produce and validate `element_sim` specs, but an adapter may not import another adapter | C1 cannot validate its realizations | `geant4_run.py` provides a `check-spec` subcommand (B1), called by `detector-design` as a subprocess; C1 relies on its own validity rules, and realizations are validated with `check-spec` in C2 (C2.9) (§P.4) |

---

## §P.2 Planning principles

| # | Principle | Explanation |
|---|---|---|
| R1 | **Introduced by the first consumer, but located correctly from the start** | Each interface is added in the first stage that needs it; shared interfaces live from day one where every consumer can import them (`core/`, `contracts/`) |
| R2 | **Schemas evolve only additively** | New fields are optional; version numbers (`summary_version` etc.) get a minor increase; old records can always be read and replayed |
| R3 | **One production implementation per quantity** | An implementation in another language or place exists only in tests as an oracle |
| R4 | **Keep the sci-fix minimal** | A1 contains only the changes needed to fix the defects and their direct foundations |
| R5 | **Each stage merges on its own** | Own version, VALIDATION entry, CHANGELOG, acceptance list; after merging the plugin is consistent |
| R6 | **Reproducible decisions, traceable numbers** | Reproducibility means the same decisions and labels (§R.5.6); results carry search size and evidence correlation |
| R7 | **AI is the designer, not the judge** | Claude chooses structures, proposes seeds and interprets results; "is it met, which is best" is decided only by recorded evaluation and statistics (task C) |

---

## §P.3 Stage contents and acceptance (summary)

Full work items and acceptance are in the task specs; this only lists scope boundaries to avoid overlap.

| Stage | Includes | Explicitly excludes (and where it goes) |
|---|---|---|
| A1 | Benchmark table and validation classes (reference, setup-matched, sanity, interface); scope comparison; configuration and isolation (`spec-v1`); block batch means, exact intervals, MPV, quantiles (histogram); the decision engine's `equivalence` and `detection_limit`; two-stage event count; seed hash H; evidence roles; schemas and reading of `simulation-summary/1` and `simulation-observables/1`; Python summary producer; the fixes of D6, D7 (stopping rule, evidence correlation, trace), D8 and D10; declaring the existing `simulation` property in `ext_computational_run.json`; `tolerance_mode` `absolute` (each observable's own `tolerance`); J14 regeneration; sci-fix process. The `absolute` mode is an exception to P1: A1's own J14 benchmarks need it | `change` (B2), `threshold` / `order` / paired comparison (C2), regression role (B2), search and confirmation roles and seed_group (C2), `values` accumulator (C2), C++ summary (A2) |
| A2 | `g4sim` (`SimHash`, `SimSeed`, `SimSummary`, `MiniJson`, `SimProbe`); `per-event` seeding; `layered_sim` writes summary, column map, effective config; name-free `tree-v1`; effective configs stored by content hash; `validate_spec`, `spec.schema.json` and `Spec.cc` accept `run.seeding`, `output.observables`, `output.blocks`, `output.debug_observable_dump`; study layer reads only boundary artifacts; schema keywords (`maxItems`, `maximum`, `exclusiveMaximum`) | `element_sim` (B1) |
| B1 | `element_sim.spec/1`, `element_sim`, field, plane crossings, calorimeter mother and leakage columns, per-event ROOT files, `simroot`, `geant4_run.py check-spec` (registered in `MISSING_FILE_ARGS`), interface consistency of the two backends, deterministic field check | `simreco` (B2), statistical study of J15 (B3) |
| B2 | `simreco` (digitization and reconstruction, portable random numbers), `geant4_run.py reco` and `table`, transitive processing chains, verification / regression / surrogate classes and table entries, the regression role, the decision engine's `change`, CV2 | J15's validation ladder and convergence (B3) |
| B3 | J15 study: validation ladder (the isolated PVT benchmark is a separate study record), calorimeter cut convergence, variations, TOF σ_t sensitivity, recorded data, journey and routing, docs | — |
| C1 | Requirements spec, first component catalogue, design grammar and realization, F0 analytic evaluation, NSGA-II (standard library), search record (F0-only), agent protocol, closure tests. Until A2 is merged the schemas do not use `maxItems`, `maximum`, `exclusiveMaximum` (A2.7 provides them); these limits are checked in Python | Any Geant4 evaluation, validating realizations with `check-spec` (C2) |
| C2 | F1/F2 evaluation, confirmation runs, the decision engine's `threshold` and `order`, paired comparison and seed_group, search roles, `values` accumulator (Python and `SimSummary.hh`), validating realizations with `check-spec` (C2.9; J15 checked with `--strict` if B3 is merged), guards against exploiting simulation defects, robustness, CV3 | J16, MOBO (C3) |
| C3 | J16 automated-design example (compared with J15), optional MOBO (Ax/BoTorch) backend | — |

---

## §P.4 Interface ownership

| Interface | Introduced | Location | Owner (steward) | Consumers |
|---|---|---|---|---|
| Benchmark table, validation classes, scope comparison, isolation rules | A1 (B2, C2 add) | `contracts/validate.py`, `dependencies.py` | contracts (content proposed by hep-detector) | A1, B2, B3, C2 |
| Seed hash H (Python) | A1 | `core/simulation/seeds.py` | hep-detector | geant4 adapter, `check_geant4_study.py`, detector-design |
| Seed hash H (C++) | A2 | `adapters/geant4/assets/g4sim/SimHash.hh` | hep-detector | `layered_sim`, `element_sim`, `simreco` |
| Roles: evidence roles | A1 | `contracts/`, study-spec schema | contracts | all |
| Roles: regression | B2 | same (CV2) | contracts | B2, B3 |
| Roles: search and confirmation roles, seed_group | C2 | same (CV3) | contracts | C2, C3 |
| Schemas, reading and merging of `simulation-summary/1` and `simulation-observables/1` | A1 (`values` added in C2) | `core/simulation/summary.py`, `core/simulation/schemas/` | hep-detector | all |
| Schemas of the column map and effective config | A2 | `core/simulation/schemas/` | hep-detector | A2, B1, C2 |
| `tree-v1` target hash and `hash_scheme` | A2 (`spec-v1` in A1) | `adapters/geant4/assets/g4sim/SimProbe.hh`; compared in `check_geant4_study.py` | hep-detector | A2, B1, B3, C2 |
| `per-event` seeding (`run.seeding`) | A2 | `adapters/geant4/assets/g4sim/SimSeed.hh`, spec/1 | hep-detector | `layered_sim`, `element_sim` |
| Physics probe (physics part of the effective config) | A2 | `adapters/geant4/assets/g4sim/SimProbe.hh` | hep-detector | A2, B1, B2 (regression), C2 |
| Block estimators, exact intervals, MPV, quantiles | A1 (`values` quantiles in C2) | `core/stats/batch_means.py` | hep-statistics | hep-detector scripts, detector-design |
| Distribution functions (`t_ppf`, `f_ppf`, `garwood`) | A1 | `core/stats/distributions.py` | hep-statistics | same |
| Decision engine | A1 `equivalence`, `detection_limit`; B2 `change`; C2 `threshold`, `order`, paired mode | `core/stats/decisions.py` | hep-statistics | A1, B2, B3, C2 |
| `g4sim` headers | A2 (`values` in `SimSummary` in C2) | `adapters/geant4/assets/g4sim/` | hep-detector | `layered_sim`, `element_sim`, `simreco` |
| `element_sim.spec/1` and `check-spec` | B1 | geant4 adapter | hep-detector | B1, B3, C2 (C2.9) |
| Per-event ROOT files, `simroot` | B1 | geant4 adapter | hep-detector | B2, B3 |
| `simreco` and reco spec | B2 | geant4 adapter (C++, not linked to Geant4) | hep-detector | B3, C2 |
| Requirements spec, component catalogue, design grammar, search spec | C1 | `adapters/detector-design/` | hep-detector (open, §P.7) | C1–C3 |
| `extension.design_search` and its rules | C2 | `contracts/` (CV3) | contracts | C2, C3 |

Cross-adapter calls always go through subprocesses and JSON files (layering rule: adapters import only `core` and `contracts`), e.g. detector-design calls `geant4_run.py check-spec`, `geant4_run.py run`, `geant4_run.py reco`.

---

## §P.5 Naming and numbering

| Object | Written as | Example |
|---|---|---|
| Stage | task letter plus number | A1, A2, B1, B2, B3, C1, C2, C3 |
| Work item | stage.number | A1.6, B2.1, C2.4 |
| Contract version (number fixed at merge) | **CV1, CV2, CV3** | CV1 = A1's contracts minor; CV2 = B2; CV3 = C2 |
| Gating form | `strict or _at_least(contract_version, CVn)` | — |
| geant4 adapter version | 0.2.0 (A2), 0.3.0 (B1), 0.4.0 (B2), 0.5.0 (C2) | — |
| detector-design adapter version | 0.1.0 (C1), 0.2.0 (C2), 0.3.0 (C3) | — |
| Journey | J14 thin silicon (existing), J15 minimal spectrometer (B3), J16 automated design (C3), J17 ion sources and Birks (deferred) | — |
| VALIDATION entries | GEANT4-CORRECTNESS (A1), GEANT4-SUMMARY (A2), GEANT4-ELEMENT (B1), GEANT4-RECO (B2), GEANT4-J15 (B3), DESIGN-SEARCH-F0 (C1), DESIGN-SEARCH (C2), DESIGN-SEARCH-J16 (C3) | — |
| Section references | All in this document: "§P.n" is Part 1, "§A.n", "§B.n", "§C.n" are Parts 2–4, "§R.n" is Part 5; "§B Appendix A" is an appendix of Part 3 | — |

"contracts C1, C2" in earlier documents are CV1, CV2; Part 5 (design rationale) keeps the old notation and states the mapping in its header.

---

## §P.6 Stage gates

| Gate | When | Condition | If it fails |
|---|---|---|---|
| G-A1 | Before merging A1 | Regenerated J14 records pass `--strict` and `dependencies.py`; gate, coverage, MPV and detection-limit toys pass | Do not merge; if J14 loses `validated-in-scope` through a missed target, the maintainer decides per §P.7 item 4 |
| G-A2 | Before merging A2 | J14's CSV bit-identical to the pre-A2 one; the probe does not change the random state | Do not merge |
| G-B1a | First day of B1 | `G4RootAnalysisReader` can read MT-merged, compressed files and string columns | `simroot` reads only scalar columns, strings move to a JSON side file (B1.5); either outcome is accepted, the fallback is a valid plan |
| G-B1b | Before merging B1 | Deterministic field check passes at nominal values; observables shared by the two backends agree by `equivalence` (declared tolerance and se target); the calorimeter comparison uses total leakage (rear, front and lateral summed), because the two backends' faces differ | Do not merge |
| G-C1 | Before merging C1 | All closure tests pass | Do not merge |
| G-C2a | C2 trial | Measure the variance reduction of paired comparison | If below the declared value, S2 uses independent comparison (C2.3) |
| G-C2b | Before merging C2 | Winner's-curse and requirement-decision toys and CV3 contract tests pass | Do not merge |
| G-C3 | Before merging C3 | J16 completed with the comparison against J15 | Do not merge |

---

## §P.7 Decisions for the maintainer (merged list)

| # | Item | Proposal | Blocks |
|---|---|---|---|
| 1 | Classification of CV1 | minor plus sci-fix | A1 |
| 2 | Stewards of the new `core/` modules | statistics to hep-statistics; `core/simulation/` to hep-detector | A1 |
| 3 | hep-computing's agreement to declaring the existing `simulation` property in `ext_computational_run.json` | agree | A1 |
| 4 | Two-stage factor F₀.₉₀ (about 10 % miss) or F₀.₉₅ (about 5 %, about 22 % more events); handling if regenerated J14 loses `validated-in-scope` by chance | F₀.₉₅ for re-recording J14; if lost, record it and keep the old records in the advisory | A1 |
| 5 | Live re-recording of J14's scan and variation runs, and the cap on recorded size | re-record; cap 3 MB | A1 |
| 6 | Switch threshold for exact intervals | any block 0 or total < 100 | A1 |
| 7 | How to confirm the G5 statement "no example code copied" | reviewer confirms in the VALIDATION entry | A2, B1 |
| 8 | Transitive processing chains (hep-computing's agreement) and classification of CV2 | agree; minor | B2 |
| 9 | Whether the C++17 CI job for `simreco` is required | required | B2 |
| 10 | Storage location and retention of ROOT files | not committed; left to the user's storage, records keep only hashes | B1 |
| 11 | Maintenance ownership of `element_sim` and detector-design | hep-detector | B1, C1 |
| 12 | Add one routing line in hep-detector's `SKILL.md` pointing to `detector-design-search.md` (about 120 bytes; quick load has 931 bytes left) | add | C1 |
| 13 | Classification of CV3 and hep-computing's agreement to `extension.design_search` | minor; agree | C2 |
| 14 | Whether the MOBO backend (Ax/BoTorch) is listed as a tested tool | list as optional | C3 |

---

## §P.8 Main cross-task risks

1. **Maintenance cost of two Geant4 programs** (`layered_sim` frozen, `element_sim` added). Duplication is controlled through `g4sim`; in the long run, once `element_sim` gains primary exit records, J14 can migrate to it and `layered_sim` can be retired (deferred; trigger: `element_sim` can produce all of J14's observables).
2. **Actual behaviour of the statistics**: O(1/B) bias of block batch means for skewed distributions, the miss rate of the two-stage design (about 19 % per point pair), and a possibly small variance reduction from paired comparison. All measured with toys and trials, never assumed.
3. **Geant4 behaviour not checked line by line**: stepper construction, the Birks API, the direction of the field intersection error, the nucleon cross sections of the two physics lists, the capability of `G4RootAnalysisReader`. Each is checked first in the stage that first uses it.
4. **Compute**: J14 re-recording (A1), calorimeter showers (B3), F1/F2 search (C2). Each stage writes its budget after a trial.
5. **Entry budget**: hep-detector quick load has only 931 bytes left, description 1,016 / 1,024 characters. Only §P.7 item 12 may touch `SKILL.md`.
6. **Incomplete effort estimates**: only the A1 contract part has a prototype estimate (about 8–12 working days); the rest is estimated and recorded at the start of each stage.
7. **References**: GRACE and VI-BRATO cited in task C are 2026 preprints; all sources are checked through hep-citations before formal citation.

---

## §P.9 Document map and division of authority

| Document | Content | Authority |
|---|---|---|
| Part 1 (this part) | Evaluation, principles, stages, interface ownership, naming, gates, open decisions, risks, execution environment | Order, numbering, version placeholders, ownership, gates, open decisions, execution environment (isolated worktree) |
| Part 2 (task A) | Work items and acceptance of A1, A2 | Content and acceptance of these two stages |
| Part 3 (task B) | J15 design; work items and acceptance of B1, B2, B3 | Content and acceptance of these three stages; J15's numbers |
| Part 4 (task C) | Design of automated design search; work items and acceptance of C1, C2, C3 | Content and acceptance of these three stages |
| Part 5 (design rationale) | Design rationale, reference experiments, superseded designs | Rationale; where it conflicts with a spec, the spec wins and the conflict is reported |
| `README.md` | Folder entry point, pointing to this document | — |
| `gate_operating_characteristics.py`, `j15_design_estimates.py`, `design_search_closure.py` | Programs computing design numbers | Numbers in the corresponding appendices |

Parts 2–4 share one structure: §X.0 task card, §X.1 terms and files, §X.2 prerequisites and provided interfaces, §X.3 hard rules, §X.4 design summary, from §X.5 the work items and acceptance of each stage, then contracts and versions, checks, not done and deferred, open decisions and risks, order of work, appendices (X is A, B or C).

---

## §P.10 Execution environment: isolated worktree

### §P.10.1 Principle

- **Every stage runs in its own isolated git worktree**: one stage, one worktree, one branch.
- Files in the main checkout (the working tree at the repository root) and in other worktrees are never changed.
- Reasons:
  - stages that can run in parallel (e.g. C1 with A2 and B1) and parallel agents do not overwrite each other;
  - build directories, Geant4 output and temporary files are isolated from each other;
  - a failed stage can be discarded as a whole without affecting other work;
  - each stage's change is exactly the diff of one branch, so review and merge scope are clear.

### §P.10.2 Creating and confirming

| Item | Rule |
|---|---|
| Location | `.claude/worktrees/geant4-<stage>`, stage name in lower case, e.g. `.claude/worktrees/geant4-a1` |
| Branch | `worktree-geant4-<stage>`, e.g. `worktree-geant4-a1` (the naming of `EnterWorktree`) |
| Base | The latest `main` that already contains all prerequisite stages (the "Prerequisite" column of §P.0); e.g. B2 is based on `main` after B1 is merged |
| Source of the specs | Once approved, this folder is merged to `main` and the worktree contains the specs. Before approval the specs exist only on branch `worktree-geant4-architecture`; read them with `git show worktree-geant4-architecture:plugins/hep-research/docs/dev/geant4-architecture/<file>`, and do not merge that branch into a stage branch |
| In Claude Code | The session itself creates and enters the worktree with `EnterWorktree` (name `geant4-<stage>`): location `.claude/worktrees/geant4-<stage>`, branch `worktree-geant4-<stage>`, base `origin/main`; when delegating work to a subagent, the Agent tool uses `isolation: "worktree"` |
| Elsewhere | `git fetch origin && git worktree add .claude/worktrees/geant4-a1 -b worktree-geant4-a1 origin/main`; in Claude Code this existing worktree can then be entered with `EnterWorktree`'s `path` |
| Confirm before starting | `git rev-parse --show-toplevel` is the worktree's path, `git branch --show-current` is the stage's branch, `git status` is clean; `git merge-base --is-ancestor <merge commit> HEAD` succeeds for the merge commit of every prerequisite stage; these results go into the stage's work record (the environment field of the VALIDATION entry) |

### §P.10.3 Rules inside the worktree

1. All editing, building, testing, Geant4 runs and spec corrections happen in the stage's worktree; never `cd` into the main checkout or another worktree.
2. Commands use clear absolute or relative paths inside the worktree; avoid composing git arguments from variables computed at run time, so that tools and reviewers can confirm a command stays inside the worktree.
3. **`git stash` is shared by all worktrees.** Do not use bare `git stash` or `git stash pop`; use a temporary WIP commit to set work aside.
4. Build directories, E2 output, ROOT files and trial results go in directories of that worktree that are not committed (e.g. `build/`, `work/`, excluded by `.gitignore`), or in a temporary directory owned by that worktree; different worktrees do not share build directories. The Geant4 installation itself (E2) may be shared read-only by several worktrees.
5. Commit only on the stage's branch; commits carry the required trailers; push to the remote branch of the same name. Do not push to `main` or open a pull request without the maintainer's approval.
6. Before merging, run the checks of §A.8 in the worktree and confirm the gates (§P.6).
7. If the specs need correcting: before the maintainer approves the specs, change them in the documentation worktree (`.claude/worktrees/geant4-architecture`, branch `worktree-geant4-architecture`); once implementation has started, in the stage's worktree. In both cases change both languages and record it in the version history; if other stages are affected, update this part too.
8. Independent reviews and other subagents run with `isolation: "worktree"`; reviews read and do not write, and worktrees without changes are cleaned up automatically when they finish.

### §P.10.4 Stages that can run in parallel

| Running together | Condition | Note |
|---|---|---|
| C1 with A2, B1, B2, B3 | A1 merged | C1 mainly touches `adapters/detector-design/` and its docs, but also a reference doc, one routing line in hep-detector's `SKILL.md` (§P.7 item 12), `core/physics/tracking.py` (new), hep-detector's `tracker_resolution.py` and `multiple_scattering.py` (changed to call `core/`) and `docs/capability-map.json` / `.md`; these files can conflict with other stages, so whichever merges later rebases and reruns the checks |
| B3 with C2 | B2 and C1 merged | Both may change `geant4-study-protocol.md` and the journey docs; whichever merges later rebases on the new `main` and reruns the checks |

Each parallel stage uses its own worktree and branch; one stage is never implemented by two agents in different worktrees at the same time.

### §P.10.5 Finishing

- **After merging:** `git worktree remove .claude/worktrees/geant4-<stage>` and delete the local branch; the next stage creates a new worktree from the new `main`.
- **Abandoning:** remove the worktree and the branch; do no cleanup in the main checkout.
- **This folder itself** is written on branch `worktree-geant4-architecture` in worktree `.claude/worktrees/geant4-architecture`; later document changes happen there too, until it is merged to `main`.

---

## §P.11 Version history

| Version | Content |
|---|---|
| 2026-10-23 | First version: consolidated evaluation (P1–P9), planning principles, eight stages (B split into B1–B3, C as C1–C3), interface ownership, naming (contract versions written CV1–CV3), gates, merged open decisions and risks |
| **2026-10-23 (this version)** | **Added §P.10 "Execution environment: isolated worktree" (creating, confirming, rules, parallel stages, finishing) and a reading guide for agents** |

---

# Part 2 — Task A: correctness fixes and boundary artifacts (§A)

> Order: A1 → A2; then task B (Part 3 (task B)) and task C (Part 4 (task C))
> Baseline: hep-research `main` at `9f08796` (0.23.0 plus unreleased changes), contracts 3.5.0, adapter geant4 0.1.0, Geant4 11.4.3
> Date: 2026-10-23

---

## §A.0 Task card

**Goal.** Fix the defects (D1–D8, D10) that let a simulation study be wrongly labelled `validated-in-scope`, and make the study layer know a simulation backend only through three boundary artifacts (run summary, column map, effective config) (D9). Statistics and summary reading live in `core/` from the start, so later adapters (task C) can use them directly.

**Two stages (in order, each merged separately):**

| Stage | Content | Version | Language |
|---|---|---|---|
| **A1** Correctness fixes | Contracts (benchmark table, scope, configuration and isolation, evidence roles); `core/stats/` (block batch means, exact intervals, MPV, quantiles, the decision engine's `equivalence` and `detection_limit`, distribution functions); `core/simulation/` (seed hash, schemas and reading of summaries and observables); Python summary producer; J14 regenerated | contracts **CV1** (minor, sci-fix) | Python |
| **A2** Shared headers and boundary artifacts | `g4sim` (`SimHash`, `SimSeed`, `SimSummary`, `MiniJson`, `SimProbe`); `per-event` seeding; `layered_sim` writes the three boundary artifacts; name-free `tree-v1`; effective configs stored by content hash; the study layer reads only boundary artifacts | geant4 adapter **0.2.0**; contracts unchanged | C++ and Python |

**Out of scope:**
- `element_sim`, fields, plane crossings, ROOT files, `simroot`, `simreco`, J15 (task B); the decision engine's `change` (B2).
- The decision engine's `threshold` and `order`, paired comparisons, search roles, seed_group, the `values` accumulator (task C's C2; §P.2 R1).
- The `layered_sim` spec format (spec/1) is not restructured; only optional fields are added.

**Deliverables:** code and tests; regenerated J14 records; sci-fix ledger entries and advisories; VALIDATION entries GEANT4-CORRECTNESS (A1) and GEANT4-SUMMARY (A2); CHANGELOG; release manifest.

**Definition of done:** every box in the acceptance lists A1.15 and A2.10 is ticked; every check in §A.8 passes; gates G-A1 and G-A2 (§P.6) pass.

**Main decisions:**
1. **A1 is a minimal sci-fix.** It contains only the changes needed to fix D1–D8 and D10 and their direct foundation; decisions and fields needed only by tasks B and C are added by those tasks (§P.2 R1, R4).
2. **Shared code lives in `core/`.** Adapters can import only `core` and `contracts`; statistics, decisions, the seed hash and summary reading are in `core/` from day one, and hep-detector's scripts are only callers.
3. **Reproducibility = same decisions.** No bit-identical statistics (§A.4.3).
4. **`layered_sim` is frozen.** A2 only adds optional fields and files; new geometry features go into task B's `element_sim`.

**First step:** create the isolated worktree for this stage per §P.10.2 (`.claude/worktrees/geant4-<stage>`, branch `geant4-<stage>`, based on the latest `main` that contains the prerequisite stages), and confirm `git rev-parse --show-toplevel`, `git branch --show-current` and `git status`. Every following step happens in this worktree.

**Before starting:**
1. Check whether `main` has moved past `9f08796`. If so, read the new CHANGELOG, redo the checks of §A appendix C, and update this part (both languages).
2. Read §P.0–§P.6; read §R.0 and §R.2; read the sci-fix process, the adapter-change process and the release steps in `docs/maintenance.md`.
3. Start A1 from `prototype/phase1-core.patch`. It changes only `contracts/validate.py`, `check_geant4_study.py`, `geant4_benchmarks.py`, the study-spec schema and two test files, nothing in `core/`: the benchmark table (grades and kinds, no validation classes), the scope comparison with kinds (`scope_outside()`; dimensions hard-coded as particle, material, energy, thickness, with an exception for `longitudinal-profile`), configuration and target hash in the benchmark output (derived from the run record's `extension.simulation.geometry`, not from spec/1; no target for `longitudinal-profile`), and the enum fix of A1.12. It predates this spec: it lacks `target_slabs`, `setup-matched`, per-benchmark scope dimensions, `hash_scheme`, the `dependencies.py` re-derivation and CV1 gating; it gates at a hard-coded 3.6.0; it writes `longitudinal-profile` as `("reference", ("shower-shape",))`.

---

## §A.1 Terms and files

| Term | Meaning |
|---|---|
| J14 | The existing journey `examples/geant4-thin-silicon/`: a thin-silicon study, the only Geant4 example with `validated-in-scope` records |
| study record | A computational-run record carrying `extension.study`; its `label` sets the artifact label |
| `validated-in-scope` | The label allowed only after validation by an upgrading benchmark with the declared scope inside the benchmark's scope; enforced by `_study_upgrade` in `contracts/validate.py` |
| validation class | The nature of a benchmark's reference (§A.4.4); A1 defines reference, setup-matched, sanity, interface; B2 adds verification, regression, surrogate |
| observable kind | The controlled kind of observable (enum) in the study spec, e.g. `most-probable-value` |
| configuration | How the target is placed: `isolated` or `embedded` (A1.3) |
| logical run | N events, numbered 0 … N−1, fixed by the spec, the backend and the logical-run seed S; may be split into several jobs |
| block | One of K segments of a logical run by event number, each with B events (N = K·B); the unit of batch means |
| three boundary artifacts | run summary (`simulation-summary/1`), column map (`simulation-columns/1`), effective config (engine-independent envelope plus the actual geometry tree) |
| `seeding` | `stream` (existing behaviour) or `per-event` (each event reseeds with H(S, event number); from A2) |
| `hash_scheme` | How the target hash is derived: `spec-v1` (A1, from spec/1) or `tree-v1` (from A2, from the geometry tree) |
| role | What a run is for in a study; A1 defines the evidence roles trial, nominal, scan, control, variation, calibration; B2 adds regression; C2 adds confirmation and the search roles |
| decision engine | `core/stats/decisions.py`; A1 provides `equivalence` and `detection_limit`, B2 and C2 add further decisions |
| CV1, CV2, CV3 | Contracts minors whose numbers are fixed only at merge (§P.5); CV1 belongs to A1 |
| E2 | An environment with a Geant4 11.4.3 build |
| IUT | intersection-union test: passes only if every observable is equivalent |
| DL | detection limit of a negative control |
| sci-fix | The process in `docs/maintenance.md` for fixing scientific-correctness defects |
| Notation | "A1.6", "B1.3", "C2.1" are work items (unique across the document); "§A.7", "§P.4", "§R.6" are sections of this document's parts (§P Part 1, §A this part, §B Part 3, §C Part 4, §R Part 5) |

**Main files (relative to `plugins/hep-research/`):**

| Purpose | Path |
|---|---|
| Contracts | `contracts/validate.py`, `contracts/dependencies.py`, `contracts/schema.py`, `contracts/schemas/ext_computational_run.json` |
| Shared modules (new) | `core/stats/distributions.py`, `core/stats/batch_means.py`, `core/stats/decisions.py` (steward hep-statistics); `core/simulation/seeds.py`, `core/simulation/summary.py`, `core/simulation/schemas/` (steward hep-detector) |
| Existing core | `core/status.py`, `core/trace.py`, `core/OWNERS.json`, `core/stats/tail_estimation.py` (`beta_ppf`, `clopper_pearson`), `core/partition/engine.py` (`NON_ADDITIVE_TOKENS` line 381) |
| Study layer | `skills/hep-detector/scripts/check_geant4_study.py` (`convergence()` line 335, relative difference line 357, decision line 359, `scope_within()` line 482), `geant4_benchmarks.py` (`GRADES` lines 92–94, `bootstrap()` line 197, `mpv()` line 204, detection limit line 275, bootstrap SE of the MPV line 369, `at_limit` line 678), `tracker_resolution.py`, `multiple_scattering.py`; `skills/hep-detector/assets/geant4-study-spec.schema.json`; `skills/hep-detector/references/geant4-study-protocol.md` |
| Adapter | `adapters/geant4/adapter.json`; `adapters/geant4/assets/geant4_run.py` (`SIM_SOURCES` line 63, `validate_spec()` line 103, `cmd_scan` line 435, `cmd_chunk` line 491, `cmd_summarize` line 525), `geant4_build.py` (`GEANT4_USE_GDML: OFF` line 53), `geant4_verify.py`, `g4common.py` (the existing Python module); `adapters/geant4/assets/layered_sim/` (`Actions.cc`: CSV format `%.10g` line 23, deposit multiplied by track weight line 113; `layered_sim.cc`: seeds and run manager lines 149–154; `MiniJson.hh`, `spec.schema.json`, `output.schema.json`) |
| J14 | `examples/geant4-thin-silicon/run.py`, `recorded/` (`events/` with 5 reduced CSVs, `runs/`, `summaries/`, `specs/`), `output/` |
| Tests | `tests/contracts/test_geant4_upgrade.py`, `test_simulated_dataset.py`, `test_schema_keywords.py`; `tests/adapters/test_geant4.py`; `tests/examples/test_geant4_thin_silicon.py`; `tests/skills/test_cli_robustness.py` |
| Tools | `tools/run_all_checks.py`, `check_layering.py`, `check_relocation.py`, `check_ownership.py`, `check_packaging.py`, `measure_entrypoints.py`, `reference_inventory.py`, `capability_map.py`, `check_routing_static.py`, `scifix_advisories.py` |

---

## §A.2 Prerequisites and provided interfaces

**Prerequisites:** none (task A comes first).

**Interfaces provided to tasks B and C** (ownership in §P.4):

| Interface | Work item | Users |
|---|---|---|
| Benchmark table, validation classes, scope comparison, isolation rule (entries can be added) | A1.1–A1.3 | B2, B3, C2 |
| Evidence roles (roles can be added) | A1.4 | B2, C2 |
| Seed hash H (Python `core/simulation/seeds.py`; C++ `g4sim/SimHash.hh`) | A1.4, A2.1 | All simulation programs, detector-design |
| Schemas and reading of `simulation-summary/1` and `simulation-observables/1` (fields can be added) | A1.5 | B1, B2, C2 |
| Block estimators, exact intervals, MPV, quantiles | A1.6, A1.7 | B3, C2 |
| Decision engine `equivalence`, `detection_limit` (decisions can be added) | A1.8, A1.10 | B2, B3, C2 |
| Two-stage event count | A1.9 | B3, C2 |
| `g4sim` headers, `per-event` seeding, probe, `tree-v1`, column map, effective-config storage | A2.1–A2.5 | B1, B2, C2 |
| Schema keywords `maxItems`, `maximum`, `exclusiveMaximum` | A2.7 | B1, C1 |

Additions can only be optional fields, new enum values or new functions; they may not change existing behaviour (§P.2 R2).

---

## §A.3 Hard rules

Breaking any of these blocks the merge.

1. **Layering.** Skill scripts and adapters import only `core` and `contracts`. Code needed by both hep-detector's scripts and any adapter (statistics, decisions, seed hash, summary reading) goes in `core/`, with a steward named in `core/OWNERS.json`; `core/` never references `skills/`, `adapters/` or `profiles/` paths.
2. **Experiment names.** No experiment names (ALICE included) in `skills/`, `contracts/` or `core/` (`check_layering.py`); use citation keys where needed.
3. **Python uses only the standard library**; no Python bindings. t and F quantiles (non-integer degrees of freedom) and Garwood intervals are implemented on the existing `beta_ppf` in `core/stats/distributions.py` (shared numerical functions, not the "new core validators" of §A.9).
4. **C++ dependencies.** `SimHash.hh`, `SimSummary.hh` and `MiniJson.hh` of `g4sim` use only the C++17 standard library; `SimSeed.hh`, `SimProbe.hh` and `layered_sim` link Geant4. No third-party libraries.
5. **G5 licence boundary.** Python exchanges only JSON and CSV with separate executables; code is written from the Geant4 API, without copying or adapting Geant4 example code.
6. **Status and exit codes** (`core/status.py`): 0 ok, 1 negative verdict (`refused`/`failed`), 2 unusable input (`rejected`), 3 `incomplete`. Unresolved and target-missed are always 3.
7. **Execution trace.** New record writers call `trace.provenance()`; new shared functions call `trace.tag()`; calls to C++ executables record the sha256 of the executable and its sources, the version and the subcommand.
8. **Size and paths.** Each file ≤ 2 MiB (`check_packaging.py` scans all text files); written paths go through `tilde()`; size claims in the plugin README must be within 10 % of the actual value.
9. **Entry budget.** hep-detector quick load ≤ 25,600 bytes (now 24,669), description ≤ 1,024 characters (`measure_entrypoints.py` reports 1,016). This task does not change `skills/hep-detector/SKILL.md` or the description.
10. **Process.** A1 follows the sci-fix process; A2 the adapter-change process; both follow the release steps. Each stage works in its own isolated worktree and branch (`geant4-a1`, `geant4-a2`) (§P.10); do not push to `main` or open a pull request without the maintainer's approval.
11. **Contract versions.** New rules are gated with `strict or _at_least(contract_version, CV1)`, with no warning branch.
12. **The offline replay of J14** always runs, without Geant4 or a compiler.
13. **No change to existing outputs.** A2 only adds files and optional fields; J14's existing specs must produce a CSV bit-identical to the pre-A2 one (same host).
14. **Not done:** integer quantization, 128-bit integers, bit-identical statistics, spec-format conversion, `simstat`, a `simcore` not linked to Geant4 (reasons in §R.13).

---

## §A.4 Design summary

### §A.4.1 Confirmed defects (`9f08796`)

| # | Defect | Location | Consequence | Work item |
|---|---|---|---|---|
| D1 | Scope check does not compare the observable; dimensions missing from the declaration are unconstrained | `validate.py` `_scope_inside()` (from line 349); `check_geant4_study.py` `scope_within()` (lines 482–493) | A study that passed an MPV benchmark can label other observables `validated-in-scope` | A1.2 |
| D2 | A benchmark's grade is declared by the record itself | `_study_upgrade` (line 395; filter line 419) | Writing `"grade": "reference"` is enough to upgrade | A1.1 |
| D3 | Negative control compared across units, tested in one direction only | `geant4_benchmarks.py` line 678 | Detection limit not demonstrated on the observable | A1.10 |
| D4 | Convergence gate has no equivalence test | `check_geant4_study.py` line 359 | Passes about 50 % of the time when the true difference equals the tolerance | A1.8 |
| D5 | MPV SE from bootstrap | `geant4_benchmarks.py` line 369 | Inconsistent variance estimate; J14's detection limit is built on it | A1.6, A1.7 |
| D6 | Stopping rule does not forbid adding events based on results | protocol section 4 | Optional-stopping bias | A1.11 |
| D7 | Evidence correlation not disclosed | J14's nominal run shared by gate, statistics target, benchmark and variation | Treated as independent evidence | A1.11 |
| D8 | Study-spec benchmark enum lacks `shower-containment` and `longitudinal-profile` | `geant4-study-spec.schema.json`; `GRADES` has 9, the enum 7 | Consistency gap | A1.12 |
| D9 | Study layer bound to `layered_sim`'s data format | `derived()` reads `geometry.layers`; `summarize` and benchmarks read fixed column names | Other backends cannot enter | A2.6 |
| D10 | Test-order dependence | `tearDownModule` of `test_geant4_upgrade` deletes the shared J14 replay directory; 5 tests of `test_simulated_dataset` error | Errors depend on execution order | A1.12 |

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
| reference | The physics model Geant4 approximates, or thin-target measurements, on an isolated target | Yes (in scope) | A1 (CV1) |
| setup-matched | A published measurement, target hash equal to the measured configuration, and isolated | Yes (in scope) | A1 (CV1) |
| sanity, interface | Plausible range, interface checks | No | existing |
| verification | Exact consequence of the inputs (analytic helix, kinematics) | No | B2 (CV2) |
| regression | The same study at a previous version | No | B2 (CV2) |
| surrogate | A fast simulation or surrogate model referenced to a full simulation | Cannot change the physics label | B2 (CV2) |

### §A.4.5 Shared modules in `core/`

| Module | A1 content | Added later |
|---|---|---|
| `core/stats/distributions.py` | `t_ppf`, `f_ppf` (non-integer degrees of freedom), `garwood` | — |
| `core/stats/batch_means.py` | Block estimators, SE, covariances, exact intervals, histogram quantiles, MPV | C2: empirical quantiles from `values` |
| `core/stats/decisions.py` | `equivalence` (IUT gate), `detection_limit`; returns `{verdict, margin, reason}` with `reason` from a closed list | B2: `change`; C2: `threshold`, `order`, paired mode |
| `core/simulation/seeds.py` | Seed hash H, logical-run seed, job seeds | — |
| `core/simulation/summary.py` and `schemas/` | Schemas, reading, validation and merging of `simulation-summary/1` and `simulation-observables/1` | A2: schemas of column map and effective config; C2: the `values` field |

hep-detector's `check_geant4_study.py` and `geant4_benchmarks.py` call these modules; later tasks call the same implementation.

---

## §A.5 Stage A1: correctness fixes (contracts CV1, sci-fix)

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
- Entries can be added to the table in later contract versions (B2, C2).
- J14's decisions are unchanged, but the content of study and benchmark files changes (new fields; `code_paths` gains `contracts/validate.py`).

### A1.2 Scope check (D1)

**Change:** `contracts/validate.py` (the single implementation, exported); `check_geant4_study.py` (imports it, deletes `scope_within()`; `label` writes `declared_scope.observable_kind`); study-spec schema (`validation_plan.scope` is `additionalProperties: false`; add `observable_kind`, `target_geometry_sha256`, `hash_scheme`).

**Rules:**
- Compare the controlled `observable.kind`, not free text.
- The declared kind must be among the kinds supported by the counted benchmarks.
- The dimension list is per benchmark (fourth column of A1.1); categorical dimensions compare by set inclusion, interval dimensions by interval inclusion; a scalar is treated as [v, v].
- Every dimension the benchmark has must be in the declared scope; a missing one counts as out of scope.
- When the target hash is a dimension, the declared scope must carry the same `target_geometry_sha256` and `hash_scheme`.
- Gating: `strict or _at_least(contract_version, CV1)`; records at 3.5.0 or below are constrained only under `--strict`, and only records with `validated-in-scope` fail.

### A1.3 Configuration and isolation

**Change:** `geant4_benchmarks.py` (output); `contracts/validate.py` (rule); `contracts/dependencies.py` (re-derivation).

- `geant4_benchmarks.py` outputs, for each benchmark result, `configuration`, `target_geometry_sha256`, `hash_scheme: spec-v1` and `configuration_basis`, derived from the spec/1 of the run record named by the benchmark setting's `run_record`, never from user input. A benchmark counted for upgrade must have a `run_record`.
- **Target:** the benchmark setting declares `target_slabs` (the names of the slabs in the target, absorbers included). A single-layer benchmark defaults to the measured slab; `longitudinal-profile` must list the whole sampling stack (its `layers` lists only the readout columns).
- **Vacuum:** the world material is `G4_Galactic`, or density < 1e-20 g/cm³.
- **isolated:** the world is vacuum and every placement other than the world belongs to the target; spec/1 has no field and is treated as field-free (the field rule takes effect in task B: only a field attached inside the target belongs to the target and counts in the hash). Otherwise embedded.
- **`spec-v1` normal form:** the ordered slabs, thicknesses, transverse sizes, material names and declared compositions; repeated placements listed one by one; numbers as Python `float.hex()`; sha256 of the JSON of this list (sorted keys, no whitespace).
- **Contract rule (CV1):** a counted reference benchmark must be isolated; a counted setup-matched benchmark must be isolated and its target hash and `hash_scheme` must equal those of the benchmark's measured configuration. Missing or embedded are errors. `dependencies.py` **must** re-derive from the run records in `evidence_records` and compare.
- Residual limits (written into the protocol): J14's recorded CSVs are reduced, so their hashes do not match the run records' `output_hashes`; configuration describes the run record the setting names. The geometry of negative-control runs is not checked separately.

### A1.4 Logical runs, seeds and roles

**Change:** new `core/simulation/seeds.py`; `check_geant4_study.py` and `geant4_run.py` call it.

- **Definition of H** (Python and C++ must agree; the C++ one is in `SimHash.hh` of A2.1): H(x₁, …, x_n) = int.from_bytes(sha256("\x1f".join(str(x) for x in (x₁, …, x_n)).encode("utf-8"))[:8], "big") % (2³¹ − 1) + 1, with values in [1, 2³¹ − 1]; integers are written as decimal strings without leading zeros.
- Each evidence point is one logical run with seed S = H(study_id, role, point_id); the two directions of a control use different point_ids.
- **Storage:** the run record's `extension.simulation` gains `role`, `point_id`, `logical_run_seed` (S) and `seed_scheme` (`hash-v1` or `legacy`); from A2 the execution spec also carries `run.logical_run_seed` (A2.2).
- New recordings in A1 always use `seeding: stream` (`layered_sim`'s current behaviour); a single job's seed pair is (H(S, 0, 0), H(S, 0, 1)). Do not use `make_manifest`'s `seed × 100003 + k`, `cmd_scan`'s `[s0, s1 + k]` or `cmd_chunk`'s `start + 1`.
- A logical run may be split into several jobs (`geant4_run.py chunk` with a hand-made manifest, each job covering a range of event numbers): the job starting at event e has seed pair (H(S, e, 0), H(S, e, 1)); `cmd_chunk` (`seeds=[max(1, args.seed), args.start + 1]` at line 504) runs with this pair instead and writes the job's seed H(S, e, 0) into the manifest. Seeds within one manifest then differ, and `validate_manifest`'s `partition.duplicate_seed` check needs no change. Under `stream`, different splits give different events, but statistically equivalent ones.
- **Roles:** `extension.simulation.role` comes from the evidence-role enum (trial, nominal, scan, control, variation, calibration); an unknown role is an error (CV1-gated). The enum can be extended later (B2's regression, C2's confirmation and search roles).
- **Uniqueness:** S is not repeated across all run records of a study (checked by `check_geant4_study.py`). The 5 J14 runs not re-recorded in A1 (A1.13) have no S: their run records are not rewritten; the study record registers them with their original seed pairs (first seed 1401 or 1402) as `seed_scheme: legacy`, and only their full seed pairs are checked for repetition.

### A1.5 Summary, observable declaration and Python producer

**Change:** new `core/simulation/summary.py` (reading, schema validation, merging by block, and access to accumulators of `simulation-summary/1`) and `core/simulation/schemas/` (`simulation-summary/1`, `simulation-observables/1`); new `adapters/geant4/assets/summary_from_csv.py` (or a `summarize-blocks` subcommand of `geant4_run.py`), which writes and merges through `core/simulation/summary.py`.

- **Observable declaration `simulation-observables/1`:** an array, each item `{name, source_column, selection, bins: {lo, hi, width}, thresholds, tolerance_mode, tolerance}`. `selection` is a declarative filter on CSV columns (column name, comparator `==`, `!=`, `<`, `<=`, `>`, `>=`, value; several conditions are ANDed); `thresholds` feed `count_if` (counting events with x > threshold, strictly greater, as for `tail_fraction` in `check_geant4_study.py`); `tolerance_mode` and `tolerance` see A1.8. The study spec (A1.12) and the simulation programs' `output.observables` (A2.3, B1.1) reference it.
- **Input:** per-event CSVs of one or more jobs, the observable declarations, block size B and block count K.
- **Selection:** each observable accumulates only events that satisfy its `selection` (declarations must reproduce the current code's selections: in `check_geant4_study.py` only `mpv_loss_MeV` requires `primary_fate == 1` (line 284), while `mpv_deposit_MeV` and `tail_fraction` use all events (lines 277–282); the benchmarks' `transmitted()` additionally requires `primary_fate == 1` and `primary_end_process == "Transportation"` (`geant4_benchmarks.py` lines 232–236)); `n` is the number of selected events, and the total number of events per block is recorded as well.
- **Blocks:** event i (the `event` column minus the logical run's first event number) belongs to block ⌊i/B⌋; events with i ≥ K·B are ignored and their number noted.
- **Accumulators per block and observable:** integers `n`, per-bin histogram counts (fixed binning; overflow and underflow separate), `count_if[]` (x > threshold); floating point Σx, Σx², `min`, `max` (Neumaier compensated summation).
- **Output fields:** `summary_version`, `run` (logical-run identity and seed, `role`, event range, `seeding`, B, K, spec hash, producer `python-csv` and version), `observables[]`, a `merge` rule for each accumulator (`sum`, `min`, `max`, `hist`). Multiple jobs merge by block number. The schema allows added optional fields (C2's `values`).
- **Event weights:** if the CSV has a `weight` column it must be all 1, otherwise exit 2 (deposits are already multiplied by the track weight; see `Actions.cc` line 113). Without a `weight` column (J14's 5 reduced CSVs have none), the summary records `weight_column: absent`, justified by the absence of biasing commands in the run record's spec; with biasing commands in the spec, exit 2.
- From A2, `layered_sim` writes summaries with the same schema; this Python producer then stays only in tests as an oracle.

### A1.6 Estimators and SE (D5)

**Change:** new `core/stats/distributions.py` and `core/stats/batch_means.py`; `check_geant4_study.py` and `geant4_benchmarks.py` call them (read only the summary; drop production use of `bootstrap()`, keep it in tests for comparison).

- For each block b compute θ_b; report θ̄ = mean, SE = sd(θ_b)/√K with K − 1 degrees of freedom. K ≥ 16, declared before the first evidence run.
- Several observables: the per-block vector of estimates is kept together, and covariances are estimated from these vectors.
- Full-sample values: means and proportions are also computed from the merged accumulators, and their difference from θ̄ is recorded as a diagnostic.
- Quantiles: linear interpolation within the histogram; bin width divided by the estimate must be below 1/10 of the relative tolerance; landing in the overflow or underflow bin makes it incomplete.
- **Low counts:** when any block of a count estimator is 0, or the merged total is < 100 (threshold can be declared), use exact intervals on the merged accumulators instead: Clopper–Pearson for proportions (the existing `clopper_pearson`), Garwood for counts; comparing two runs uses the conditional-binomial interval for the ratio of rates, relative difference = ratio − 1 (exact for Poisson counts; only approximate for proportions, because their denominators are fixed; the protocol notes this). There is then no SE, and the gate decides on interval endpoints (A1.8).
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
- **Difference:** keeps the convention of line 357: a is the finest setting and b the second-finest (`vals` sorted ascending, a = `finest[0]`, b = `finest[1]`). The observable declares a `tolerance_mode`: with `relative` (default) diff = (a − b)/b and se_diff = √(se_a² + se_b²)/|b|; with `absolute` diff = a − b and se_diff = √(se_a² + se_b²), and tol is the observable's declared `tolerance` (in the observable's unit; required under `absolute`); under `relative` tol is the study spec's `tolerance_relative`. ν from the Welch formula per pair (30 for equal variances and K = 16). (The first user of `absolute` is B3; because it is only an option of the same function, it is in A1 so that the gate's definition need not change later.)
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
- Trace tags (lowercase, hyphenated): `geant4-scope-kind`, `geant4-configuration`, `geant4-convergence-iut`, `geant4-batch-means`, `geant4-mpv-block`, `geant4-seed-hash`. Once `check_geant4_study.py` imports `contracts.validate`, `code_paths` gains `contracts/validate.py`; this change is expected.

### A1.12 Other fixes (D8, D10)

- The study-spec benchmark enum gains `shower-containment` and `longitudinal-profile`; the grade enum (now reference, sanity, interface) gains `setup-matched`; the observable-kind enum gains `shower-maximum`; `validation_plan.scope` gains `observable_kind`, `target_geometry_sha256` and `hash_scheme` (for setup-matched, A1.2).
- The study spec (top-level `additionalProperties: false`) gains top-level properties: `observables` (referencing `simulation-observables/1`; `name` must equal the names in `convergence_plan.observables`, e.g. `mpv_deposit_MeV`) and `blocks: {K, B}`. The existing singular `observable` is unchanged and remains the study's main observable.
- `ext_computational_run.json` declares the existing `simulation` property in the schema (J14's run records already carry `extension.simulation` and `_study_upgrade` already tests it; needs hep-computing's agreement).
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
- The size of `recorded/` is measured in A1 (in bytes, not `du`'s block usage); single files are limited by `check_packaging.py` to 2 MiB (2,097,152 bytes); the cap on the whole of `recorded/` is the maintainer's decision (§P.7 item 5).

### A1.14 Version and sci-fix process

- **Version:** contracts CV1 (minor). Precedents for new gated rule families (2.4.0, 2.6.0, 2.8.0, 3.1.0, 3.2.0) were all minor.
- **Ledger:** one entry per row of the table below (D10 is a test fix, not in the ledger, only in the CHANGELOG), `changelog` as a structured object (`{"kind": "unreleased", ...}`).

| Defect | Ledger entry | Severity | Reason |
|---|---|---|---|
| D1 (incl. per-benchmark scope dimensions) | scope-kind | S2 | Changes decisions |
| D2 (incl. validation classes) | grade-table | S2 | Changes decisions |
| D3 (incl. detection limit with t quantile) | control-shift | S2 | Changes decisions |
| D4 (incl. definition of diff and se) | gate-IUT | S2 | Changes decisions |
| D5 (incl. block batch means instead of bootstrap, exact count intervals, MPV interpolation) | variance-method | **S1** | Changes reported numbers |
| Isolation definition (incl. vacuum) | isolation | S2 | Changes decisions |
| D6 | stopping-rule | S3 | Guidance only |
| D7 | evidence-overlap | S3 | Disclosure only; decisions unchanged |
| D8 | enum-gap | S3 | Consistency; decisions unchanged |

- **Evidence:** S2 needs levels C2 and D2; S1 needs levels C3 and D2 (evidence levels from `docs/maintenance.md`; here C2 and D2 are evidence levels, not a contract version or a defect number). Evidence tests run through the command lines of `validate.py` and `check_geant4_study.py` so that they can run on the parent commit; what cannot run goes in `gaps`.
- **Advisories:** one for S1 and one for S2; S3 needs no advisory (`scifix_advisories.py check` requires an advisory's severity to equal that of every ledger entry it lists); numbers are the next unused at merge (now SFA-2026-038 and -039).
  - Keys: `artifact_types: [computational-run]`, `extension_keys: ["study", "evidence_records"]`.
  - Range: introduced 0.20.0, with `database_specific.introduced_basis`; affected versions 0.20.0–0.23.x and unreleased.
  - Simulated dataset-records cannot be distinguished by keys; the remedy asks holders to run `contracts/dependencies.py` on every simulated table.
- Study records produced from 0.20.0 on with `validated-in-scope` fail under `--strict`; the advisory says what to do (regenerate with the new version).

### A1.15 A1 acceptance

- [ ] Records with a kind mismatch, a declaration missing a dimension, a class or grade differing from the table, a missing or embedded configuration, or a mismatched target hash or `hash_scheme` are rejected under `--strict` and CV1; a `dependencies.py` re-derivation mismatch is rejected; scalar scopes compare correctly.
- [ ] Unknown roles and an S repeated within a study are rejected; runs with legacy seeds are checked by their rule.
- [ ] Regenerated J14 study records pass `validate.py --strict` and `dependencies.py`; any change in decisions is recorded with its reason (gate G-A1).
- [ ] Gate toys (10⁴ per cell, with the model stated in the A1.8 table header) agree with the A1.8 table to ±3σ_MC: the "se = target" columns check the TOST part only, the "two-stage" columns the full gate including the target condition; the `absolute` mode and the interval decisions for low counts are tested.
- [ ] Coverage toys for block batch means: for each class of J14 estimator (mean, proportion, quantile, mode), the actual coverage of a nominal 90 % interval satisfies |coverage − 0.90| ≤ 0.02 + 3σ_MC, reported per class.
- [ ] MPV bias toys: 95 % upper bound ≤ tol/10; the per-execution check is in effect.
- [ ] Detection-limit toys (the caught definition of A1.10): probability of catching an injection at DL ≥ 0.977 − 3σ_MC; the outcome of J14's realised controls recorded in VALIDATION.
- [ ] J14's offline replay runs from the committed summaries, decisions meet §A.4.3, without Geant4 or a compiler.
- [ ] Unit tests of the Python producer: block division, selection, merging, exit 2 when `weight ≠ 1`, overflow bins.
- [ ] Each new `core/` module has unit tests (`t_ppf`, `f_ppf`, `garwood` against known values; test vectors for H) and a steward in `core/OWNERS.json`; a test importing only `core` (as an adapter would) reads a summary, computes estimators and calls `equivalence`; `check_layering.py` passes.
- [ ] `python3 -m unittest discover -s tests/contracts -t .` has no errors.
- [ ] Nine ledger entries, two advisories passing `scifix_advisories.py check`, parent records complete; live Geant4 evidence recorded with release-gate; VALIDATION GEANT4-CORRECTNESS; CHANGELOG; release manifest.

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
| Storage | Content is stored once by `config_sha256` (`effective_configs/<config_sha256>.json`), and several runs with the same settings refer to the hash only; `extension.simulation.effective_config` holds the reference; committed J14 records also carry the full content for offline replay. The schema is in `core/simulation/schemas/` |

- Rules and the model assignment of variations read the probe first and fall back to the declaration only when the probe cannot be read, outputting `source: probe | declared`; when both exist and disagree, it is an error.
- Test trigger: a UI command that exists only in the test build calls the probe after `/run/initialize` and before the first `BeamOn`; it must write `recorded: false`.

### A2.5 Column map (`simulation-columns/1`)

- `layered_sim` writes `column_map.json` for each run, its hash written into the run record; the schema is in `core/simulation/schemas/`.
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

- Extend `contracts/schema.py` with `maxItems`, `maximum`, `exclusiveMaximum` (already used by `layered_sim`'s schemas; also needed by the schemas of `element_sim` and task C). Update `SUPPORTED_KEYWORDS`, and make `tests/contracts/test_schema_keywords.py` also scan the schemas of the adapters and of `core/simulation/schemas/`.
- Contracts not bumped (no contract schema uses the new keywords).
- `validate_spec()` in `geant4_run.py` is not replaced; A2.2 and A2.3 only add new fields to its key lists.

### A2.8 Adapter-change process

| Item | Content |
|---|---|
| Version | 0.1.0 → 0.2.0 |
| `adapter.json` | `assets` gains `g4sim/` and `summary_from_csv.py`; update `purpose`; `status` stays `demonstrated-on-synthetic-data` |
| `SIM_SOURCES` | Add the `g4sim/` files so that `sources_sha256` covers everything (B1 then groups it by program) |
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
- [ ] J14's offline replay still meets §A.4.3.
- [ ] VALIDATION GEANT4-SUMMARY; CHANGELOG; release manifest.

---

## §A.7 Contracts and versions

| Object | Location | Version |
|---|---|---|
| Benchmark table (class, kind, scope dimensions), scope comparison, configuration and isolation, `hash_scheme`, evidence roles, uniqueness of S | `contracts/validate.py`, `contracts/dependencies.py`, `check_geant4_study.py` | CV1 (minor, gated, sci-fix) |
| Declaration of the `simulation` property | `contracts/schemas/ext_computational_run.json` | CV1 (needs hep-computing's agreement) |
| Schema-keyword extension | `contracts/schema.py` | not bumped |
| Modules and schemas of `core/stats/` and `core/simulation/` | `core/` | with the plugin version; schemas versioned by `summary_version`, `column_map_version`, `probe_version` and the version of `simulation-observables/1` |
| Writing of `g4sim`, `seeding`, summary, column map, effective config | geant4 adapter | 0.2.0 |
| `GRADES`, kind and configuration output | hep-detector | with the plugin version |

The owner of the computational-run schema is hep-computing. CV2 belongs to task B (B2), CV3 to task C (C2).

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
- `tools/scifix_advisories.py check` (A1)
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
| `change`, `threshold`, `order`, paired comparisons, search roles, `values` | Moved to B2, C2 | §P.2 R1 |
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

**Open decisions** (numbers in §P.7): item 1 (classification of CV1), item 2 (stewards of the `core/` modules), item 3 (the `simulation` property), item 4 (two-stage factor and what to do if J14 loses its upgrade by chance), item 5 (J14 re-recording and the `recorded/` cap), item 6 (switch threshold for exact intervals), item 7 (how to confirm G5).

**Residual risks:**
1. J14's detection limits may change because of block batch means, t quantiles and controls in observable units; the controls need redesign.
2. Block batch means have O(1/B) bias for ratios, quantiles and modes of skewed distributions, which does not shrink with K; the coverage toys allow ±0.02, and B is increased if needed.
3. Block independence fails when events share state; the probe flags biasing, and in doubt use several independent logical runs.
4. With tolerance comparisons, near-threshold decisions may differ between platforms; handled by the margin flag and "the CI platform rules".
5. MT merging of a custom `G4VAccumulable` must be confirmed by tests.
6. The probe assumes workers and master have the same settings; if thread-local differences appear, switch to per-thread dumps.
7. A setup-matched target hash only proves the configuration is the same, not that it is the one in the paper; a reviewer must still check.
8. Quick load has only 931 bytes left.
9. Effort: the prototype estimated about 8–12 working days for the contract part of A1, plus Geant4 run time; the statistics part and A2 are estimated when they start.

---

## §A.11 Suggested order of work

At the start of each stage, create and confirm that stage's isolated worktree per §P.10.2 and do every step in it; remove it per §P.10.5 after merging.

**A1**
1. Pre-start checks (§A.0); apply `prototype/phase1-core.patch` and complete what A1.1–A1.3 lack.
2. Fix D10 first (A1.12); from then on always run `python3 -m unittest discover -s tests/contracts -t .` as a whole.
3. A1.1 → A1.2 → A1.3 (contracts and `dependencies.py`), with contract tests.
4. `core/simulation/seeds.py` and `summary.py`, the schemas and the A1.5 Python producer; produce summaries offline from J14's 5 per-event CSVs.
5. The three `core/stats/` modules (A1.6–A1.10), with hep-detector's scripts calling them and reading summaries; toy tests (gate, coverage, MPV bias, detection limit) and a usage test importing only `core`.
6. A1.4's role rules and the rest of A1.11 and A1.12 (protocol, enums, `simulation` property).
7. In E2, record the trial runs first and fix the event counts per A1.9, then re-record J14's scans, variations and negative-direction controls live (A1.13); regenerate J14 records and run `--strict`.
8. A1.14: ledger, advisories, parent records, VALIDATION, CHANGELOG, release manifest; run the checks of §A.8.

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
| Convergence gate | IUT; `relative` or `absolute`; se_diff; Welch ν; per-point se target tol/(4√2); pass needs both points to meet the target | A1.8 |
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

## §A Appendix C: Baseline values (`9f08796`)

| Item | Value |
|---|---|
| `CONTRACTS_VERSION` | 3.5.0 |
| `GEANT4_UPGRADE_FROM` | 3.1.0 (line 346) |
| J14 study record | contract 3.5.0, with `code_paths`, `code_tags` |
| J14 world material | `G4_Galactic` |
| J14 `recorded/` | 2,447,979 bytes (about 2.45 MB; `du -sh` shows 2.6M); `events/` 5 reduced CSVs (`event`, `primary_eloss_MeV`, `edep_Si_MeV`, `primary_fate`, `primary_end_process`); `runs/` 18 run records; `summaries/` holds single-value summaries (`geant4-run-summary/1`) of all 18 runs; 5 runs also have a per-event CSV, the 13 scan, variation and scenario runs only the single-value summary |
| J14 seeds | The first seed of the 5 non-re-recorded runs is 1401 or 1402 |
| Advisory | latest SFA-2026-037 |
| hep-detector | quick load 24,669 / 25,600 bytes; description 1,016 / 1,024 characters (`measure_entrypoints.py`); `DetectorScriptCount` 21 |
| `GRADES` | `longitudinal-profile: "reference"` (lines 92–94); the study spec's grade enum is reference, sanity, interface |
| `ext_computational_run.json` | Does not declare `simulation`; J14's run records already carry `extension.simulation` |
| `core/stats` | steward hep-statistics; already has `beta_ppf`, `clopper_pearson`; no t or F quantiles and no Garwood |
| Layering rules | Adapters import only `core` and `contracts` (`tools/check_layering.py`) |
| `SUPPORTED_KEYWORDS` | no maxItems, maximum, exclusiveMaximum |
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
| **2026-10-23 (this version)** | **Reorganized per the plan (Part 1): A1 back to a minimal sci-fix (`change`, `threshold`, `order`, paired comparisons, search roles and `values` moved to B2 and C2); contract version written CV1; the seed hash in `core/simulation/seeds.py`; section numbering consistent with tasks B and C (§A.2 prerequisites and provided interfaces, §A.8 checks, §A.10 open decisions and risks)** |
| 2026-10-23 | Added the isolated-worktree execution rule: header, the first step of §A.0, the start of §A.11 (§P.10) |
| 2026-10-23 | Fixes after the detailed check: new spec fields added to `validate_spec()`, `spec.schema.json` and `Spec.cc` together; A1.5's selections match the current code; `tolerance` and the direction of `count_if`; names of the seed fields and `cmd_chunk`; trial runs and N rounded up to a multiple of K; tol and se_rel of DL; the `tree-v1` target; `float.hex()` special values, `setTheSeeds`, `IsBlocked()` and the general processes; cross-platform tolerance of Box–Muller; D7 and D8 in the ledger; factual corrections (line numbers, size of `recorded/`, `summaries/`, the prototype's description) |

---

# Part 3 — Task B: `element_sim`, reconstruction and the J15 minimal spectrometer (§B)

> Order: B1 after A2; B2 after B1; B3 after B2. Task C's C2 waits only for B2, C3 for B3
> Baseline: at writing, the same as task A (hep-research `main` at `9f08796`, contracts 3.5.0, Geant4 11.4.3); must be rechecked before starting (§B.0)
> Date: 2026-10-23
> Nature of the example: J15 is a **synthetic geometry**, a carrier for verification, not any experiment's detector; the closest real instruments are PAMELA and AMS-02 (§B.4.3)

---

## §B.0 Task card

**Goal.** Add a general box-element Geant4 program `element_sim` as a second backend (field, plane crossings, calorimeter leakage, per-event ROOT files), add the reconstruction program `simreco` (not linked to Geant4) and new validation classes, then use them to complete the J15 minimal-spectrometer study.

**Three stages (in order, each merged separately):**

| Stage | Content | Version |
|---|---|---|
| **B1** `element_sim` and event files | `element_sim.spec/1` and `element_sim` (box elements, one level of nesting, field, plane crossings, calorimeter leakage); per-event ROOT files; `simroot`; `geant4_run.py check-spec`; interface consistency between the two backends; deterministic field check | geant4 adapter **0.3.0** |
| **B2** Reconstruction and contracts | `simreco` (digitization and reconstruction, portable random numbers); `geant4_run.py reco` and `table`; transitive processing chains; verification, regression and surrogate classes and table entries; the decision engine's `change`; the regression role | geant4 adapter **0.4.0**, contracts **CV2** (minor) |
| **B3** J15 study | Validation ladder, calorimeter cut convergence, variations, TOF σ_t sensitivity, recorded data, J15 journey and docs | example and docs (adapter not bumped) |

**Out of scope:** changes to task A's interfaces (if needed, first as an adapter patch release within task A); new geometry features in `layered_sim` (frozen); task C's design search; ion sources and Birks (J17); non-box geometry and field maps (§B.9).

**Deliverables:** `element_sim`, `simroot`, `simreco` and their tests; `geant4_run.py check-spec`, `reco`, `table`; the CV2 contract changes; the J15 example (a new folder under `examples/`, README, recorded data); J15 journey and routing case; VALIDATION entries GEANT4-ELEMENT (B1), GEANT4-RECO (B2), GEANT4-J15 (B3); CHANGELOG; release manifest.

**Definition of done:** every box in the acceptance lists B1.9, B2.6 and B3.8 is ticked; every check in §A.8 passes; gates G-B1a and G-B1b (§P.6) pass.

**Main decisions:**
1. **A new backend, not a change to `layered_sim`.** `element_sim` leaves J14's program untouched and validates the output-side interface with a real second backend (§R.3.2).
2. **Field accuracy by deterministic checks.** Charged geantinos against an analytic helix, no statistics needed; completed in B1 (B1.7).
3. **Infrastructure separated from the physics study.** B2 does only `simreco` and the contracts, so task C's C2 does not wait for the J15 study (§P.1 P3).
4. **J15 is a verification carrier.** Every result of the J15 study is `unvalidated`; the optional isolated PVT slab benchmark is a separate study record (not part of the J15 study) that shows the upgrade path for a new material (B3.2).
5. **No new scripts in hep-detector.** Reconstruction is in C++ in `simreco`, its interface in the adapter; quick load and description unchanged.

**First step:** create the isolated worktree for this stage per §P.10.2 (`.claude/worktrees/geant4-<stage>`, branch `geant4-<stage>`, based on the latest `main` that contains the prerequisite stages), and confirm `git rev-parse --show-toplevel`, `git branch --show-current` and `git status`. Every following step happens in this worktree.

**Before starting:**
1. Confirm that A2 is merged and that the interfaces listed in §B.2 exist.
2. Using the method of §A Appendix C, recheck the facts this part quotes against the `main` of that time (quick load, description length, journey list, `DetectorScriptCount`, contracts version, structure of `MISSING_FILE_ARGS`), and update this part (both languages).
3. Read §A.1, §A.3, §A.4 and §P.4–§P.6; this part does not repeat them.

---

## §B.1 Terms and files

| Term | Meaning |
|---|---|
| J15 | The minimal spectrometer of this task (synthetic geometry) |
| `element_sim` | The Geant4 program added in B1; spec `element_sim.spec/1` |
| Bending plane | The x–y plane (B along z); the non-bending direction is z |
| Rigidity R | p/\|q\|, in GV; C = 0.2998 GV/(T·m) |
| MDR | Maximum detectable rigidity: the rigidity at which σ_R/R = 1 counting only the measurement term |
| TOF station | TOF1 or TOF2; two layers (a, b) per station |
| charged geantino | A Geant4 charged test particle that feels only the field, with no material interactions (mass 0, β = 1) |
| Processing chain | simulation → reduction → digitization and reconstruction → table, one computational-run record per step |
| Notation | "B1.3" is a work item of this part; "§B.4.2" a section of this part; "A1.6", "C2.1" work items of tasks A and C; "§A.3", "§P.4", "§R.6" sections of other parts of this document |

**Main files (relative to `plugins/hep-research/`):** `adapters/geant4/assets/g4sim/` (created in A2, extended here); `adapters/geant4/assets/element_sim/` (new); `adapters/geant4/assets/simroot/` (new); `adapters/geant4/assets/simreco/` (new, not linked to Geant4); `adapters/geant4/assets/geant4_run.py` (new `check-spec`, `reco`, `table`; `SIM_SOURCES` defined at line 63, used at lines 327 and 386); `core/stats/decisions.py` (B2 adds `change`); `contracts/validate.py`, `contracts/dependencies.py` (CV2); `skills/hep-detector/scripts/geant4_benchmarks.py` (`GRADES`, new benchmark functions); `skills/hep-detector/assets/geant4-study-spec.schema.json`; `skills/hep-detector/references/geant4-study-protocol.md`; `tests/skills/test_cli_robustness.py` (`MISSING_FILE_ARGS`, `geant4_run.py`'s entry at line 130); `docs/researcher-journeys.md`, `docs/maintenance.md`, `docs/capability-matrix.md` ("twenty-one scripts" on line 47, checked by the test class `DetectorScriptCount` at line 145 of `tests/skills/test_documented_output_claims.py`), `docs/capability-map.json` and `docs/capability-map.md`; `tests/examples/test_geant4_minimal_spectrometer.py` (new).

---

## §B.2 Prerequisites and provided interfaces

**Prerequisites (provided by task A):**

| Interface | Use in task B |
|---|---|
| Benchmark table, validation classes, scope comparison, isolation rule (A1.1–A1.3) | B2 adds verification, regression, surrogate and J15 entries; the J15 study's benchmarks are all embedded and do not count for upgrade; the optional isolated PVT benchmark is a separate study record, decided by the isolation rule (B3.2) |
| Evidence roles and uniqueness of S (A1.4) | B2 adds the regression role |
| Block estimators, exact intervals, MPV, the decision engine's `equivalence`, two-stage event count (A1.6–A1.10) | Decisions in B3; B2 adds `change` through the same interface |
| `simulation-summary/1`, `simulation-observables/1` (A1.5) | `element_sim` and `simreco` write summaries with the same schema |
| `g4sim`: `SimHash.hh`, `SimSeed.hh`, `SimSummary.hh`, `MiniJson.hh`, `SimProbe.hh`, material and physics-list helpers (A2.1) | `element_sim` uses all of them; `simreco` only the Geant4-free `SimHash.hh`, `SimSummary.hh`, `MiniJson.hh` |
| `per-event` seeding (reseeded at the start of `GeneratePrimaries`, A2.2) | `element_sim` supports only `per-event` |
| Three boundary artifacts, name-free `tree-v1`, effective-config storage (A2.3–A2.6) | `element_sim` and `simreco` deliver the same boundary artifacts; the study layer needs no change; a field attached inside the target counts in the `tree-v1` target hash |
| Schema keywords `maxItems`, `maximum`, `exclusiveMaximum` (A2.7) | The `element_sim.spec/1` schema |

**Interfaces provided to task C:**

| Interface | Work item | Use in task C |
|---|---|---|
| `element_sim.spec/1` and `geant4_run.py check-spec` | B1.1, B1.6 | C1 validates realizations through a subprocess; F1/F2 evaluation in C2 |
| Calorimeter mother and `leak_*_MeV` | B1.3 | Objectives of calorimeter components |
| `simreco` (rigidity, β, calorimeter energy) | B2.1 | Reconstruction at F1/F2 |
| Decision engine `change`, surrogate class | B2.4 | C2 positions F0 and F1 as surrogates; C2 adds `threshold` and `order` |

---

## §B.3 Hard rules

All of §A.3 applies. In addition:

1. Do not change `skills/hep-detector/SKILL.md` or hep-detector's description (quick load has only 931 bytes left; description 1,016 / 1,024 characters). J15's routing case must reuse trigger words already in the description.
2. No experiment names in `skills/`, `contracts/` or `core/`; the contract table and the protocol refer to `longitudinal-profile`'s reference by citation key. Experiment names (PAMELA, AMS-02) may appear only in `docs/` and in J15's `examples/` README.
3. Field code is written from the Geant4 API, without copying or adapting the B5 example's code (G5).
4. The text of the shared stanza is not changed (point 5 says "3.1.0 upgrade rule"; changing it would touch every SKILL.md and rerun the live routing).
5. J15's `recorded/`: each file ≤ 2 MiB, total ≤ 3 MB; ROOT files are not committed (B3.6).
6. All results of the J15 study are `unvalidated`; no benchmark in the J15 study record may count for upgrade. The optional isolated PVT benchmark (B3.2) is a separate study record, not part of the J15 study, decided by A1.3's isolation rule.
7. No geometry features are added to `layered_sim`; new geometry features go only into `element_sim`.
8. Neither Python nor `simreco` parses ROOT directly; always through `simroot`.
9. Contract rules are gated with `strict or _at_least(contract_version, CV2)`.

---

## §B.4 J15 design

### §B.4.1 Geometry

Coordinates: origin at the world centre, stacking axis x, unit mm.

**Magnetic field: B = (0, 0, +0.5 T).** The bending plane is x–y, the non-bending direction z. A positive charge moving along +x bends towards −y; μ⁻ bends towards +y.

```
x:  −1000   −810 … −780   −520 −500        …         300  320    490 … 520   550          900   ±1200
     gun    TOF1 (2 layers)│ Si1  Si2  Si3  Si4  Si5  Si6  │     TOF2 (2 layers) calorimeter 50 layers  world edge
            10 + 10 mm    │◄────── uniform field 0.5 T ẑ (−520 … 320) ─────►│  10 + 10 mm   Pb 2 / PVT 5 mm
```

| Element | Material | Front face x | Thickness | Extent | Transverse (y × z) |
|---|---|---|---|---|---|
| World | `G4_Galactic` | — | 2400 | −1200 … 1200 | 1200 × 1200 |
| Particle source | — | x = −1000, y = z = 0 | — | — | — |
| TOF1a, TOF1b | `G4_PLASTIC_SC_VINYLTOLUENE` | −810, −790 | 10 each | −810 … −800, −790 … −780 | 300 × 300 |
| Field-region mother | `G4_Galactic` | −520 | 840 | −520 … 320 | 300 × 300 |
| Si1–Si6 (daughters) | `G4_Si` | −500.15 + 160k | 0.3 | centres −500, −340, −180, −20, 140, 300 | 200 × 200 |
| TOF2a, TOF2b | `G4_PLASTIC_SC_VINYLTOLUENE` (same as TOF1) | 490, 510 | 10 each | 490 … 500, 510 … 520 | 400 × 400 |
| Calorimeter mother | `G4_Galactic` | 550 | 350 | 550 … 900 | 500 × 500 |
| Calorimeter sampling layers (daughters) | 50 × (`G4_Pb` 2 + PVT 5) | 550 | 350 | 550 … 900 | 500 × 500 |

**TOF stations.** TOF1 and TOF2 have two layers each; all four layers have the same material and thickness (10 mm), with a 10 mm vacuum gap between the two layers of a station. Each layer is a whole slab, not segmented, with no paddle direction (a deliberate simplification); the two layers give two independent time measurements and dE/dx samples, and make the consistency of a station's two layers a check (B3.2).

**Checks** (the program of §B appendix A, recomputed in tests):
- Measurement lever arm L = 0.800 m; the front edge of Si1 and the back edge of Si6 are each 19.85 mm from the mother's boundary.
- The field extends 20 mm beyond each end of the measurement region.
- Distance between the TOF station centres (the midpoint of the two layers: −795, 505 mm) D = 1.300 m.
- The back face of TOF2's rear layer (520) is 30 mm from the calorimeter's front face (550); TOF1's front layer (−810) is downstream of the source (−1000).
- The world contains the source and the back of the calorimeter.

Materials (NIST definitions in 11.4.3 against PDG): `G4_PLASTIC_SC_VINYLTOLUENE` 1.032 g/cm³, I = 64.7 eV; `G4_Si` 2.33 g/cm³ (PDG 2.329).

**Deliberate simplifications** (listed one by one in J15's README): uniform field with sharp edges, no magnet material, silicon as whole planes (no strips, no charge sharing, the centroid shift from δ rays not simulated), TOF layers not segmented, no optical photons, no trigger or readout electronics, no anticoincidence.

### §B.4.2 Parameters and acceptance

| Parameter | Value | Basis |
|---|---|---|
| B | 0.5 T | The rigidity at which the multiple-scattering term equals the measurement term is about 16–22 GV (μ), independent of B; 0.5 T gives one decade each at 1–10 GV and 100–1000 GV |
| Si planes | 6 | N = 4 leaves only 1 degree of freedom in the bending plane; N = 8 improves the MDR by only about 8 % |
| MDR | about 1172 GV | Measurement term only. Reference value from the exact least squares of `tracker_resolution.py` (C = 0.2998). `mdr_intrinsic_only_gv` of `multiple_scattering.py` has the same definition but uses the Gluckstern approximation (about 1131 GV for N = 6); from 0.21.0 it also outputs `intrinsic_coefficient` and warns for N < 10 |
| TOF | Two layers per station; σβ/β ≈ 2.3 % (100 ps per layer, two independent layers, β = 1; 3.3 % with one layer per station); 3.5 % at 150 ps | D = 1.3 m; the station time is the mean of the two layers, σ_station = σ_layer/√2 |
| Calorimeter | 18.4 X₀, 0.886 λ_I, 50 cm wide | Enough to separate e/p by shower shape, not enough to measure hadron energy |

**Multiple-scattering term.** Highland formula, with the log term taken over the total thickness, times a factor 1.0–1.4. The review did an exact least-squares fit with discrete scattering planes, giving a factor of 1.02 (weighted) to 1.06 (unweighted). `multiple_scattering.py` by its convention **excludes** the log term; state the difference when comparing.

| Particle | Rigidity | β | Multiple-scattering term | Rigidity where the two terms are equal |
|---|---|---|---|---|
| μ | 1 GV | 0.994 | 1.3–1.9 % | 16–22 GV |
| p | 0.6 GV | 0.539 | 2.5–3.5 % | 29–41 GV |
| p | 1 GV | 0.729 | 1.8–2.6 % | 21–30 GV |
| p | 2 GV | 0.905 | 1.5–2.1 % | 17–24 GV |

**Acceptance** (unit charge, on-axis normal incidence, uniform field, sharp edges):

| Condition | Minimum rigidity |
|---|---|
| Does not leave the side of the field-region mother before x = 320 (\|y\| ≤ 150 mm) | 0.364 GV |
| Reaches Si6 (\|y\| ≤ 100 mm) | 0.511 GV |
| Reaches TOF2's front layer (x = 490, \|y\| ≤ 200 mm) | 0.385 GV |
| Passes both TOF2 layers (x = 520, \|y\| ≤ 200 mm) | 0.404 GV |
| Calorimeter front face, shower axis within 250 − 2 R_M,eff | 0.490 GV |
| Calorimeter back face, same | 0.745 GV |

Overall threshold 0.75 GV; 0.51 GV when only the track plus TOF is required. Below 0.364 GV the track leaves the side of the field region and then travels in a straight line in the field-free world.

Electrons: the shower axis is displaced 82 mm and 127 mm at the calorimeter's front and back faces at 1 GeV, 16 mm and 25 mm at 5 GeV. Bremsstrahlung photons from the upstream 11.3 % X₀ (83 % of it in the four TOF layers) are not bent, so the shower axis is not a straight extrapolation; the 79 mm margin is a geometric estimate, and the shower checks must be checked against the actual transverse energy distribution. Electron shower checks are limited to 1 GeV and above.

**Upstream energy loss** (Bethe integral, 2 cm of PVT in TOF1's two layers):

| Proton rigidity | Kinetic energy | TOF1 energy loss | Δp/p | Change in β between the station centres |
|---|---|---|---|---|
| 0.6 GV | 175 MeV | 10.23 MeV | 3.20 % | 2.87 % |
| 1 GV | 433 MeV | 6.00 MeV | 0.82 % | 0.46 % |
| 2 GV | 1271 MeV | 4.34 MeV | 0.24 % | 0.05 % |

At 0.6 GV, β changes by 2.87 % between the stations, more than the TOF resolution (2.3 %): β comparisons at low rigidity need a β model with energy loss, or are limited to 2 GV and above. TOF1 is before the first Si plane and does not affect curvature resolution; the true rigidity is taken from the crossing records of the Si planes.

**J14 cannot be reused.** J15's Si differs from J14's in material (`G4_Si` vs `Si_study`), physics settings and cuts, and J15 records only entry, so it cannot form J14's E_in − E_exit observable.

### §B.4.3 Comparison with real instruments

| Instrument | Configuration (sources in §R.14) | Compared with J15 |
|---|---|---|
| PAMELA | 0.43 T permanent magnet; 6 double-sided silicon microstrip planes, resolution better than 4 µm; MDR above 1 TV; three TOF planes (S1–S3, segmented into paddles); W/Si imaging calorimeter 16.3 X₀, 0.6 λ; also anticoincidence, S4, neutron detector | Almost the same type; J15 assumes 10 µm Si resolution (more conservative), unsegmented TOF and no anticoincidence |
| AMS-02 | Four TOF planes (8, 8, 10, 8 counters); system about 140 ps for protons | J15's 100 ps per layer is more optimistic, hence the 100 and 150 ps sensitivity (B3.5) |

J15's README uses this table to show that J15 is reasonable, and stresses that J15 is a synthetic geometry that represents no experiment.

---

## §B.5 Stage B1: `element_sim` and event files (geant4 adapter 0.3.0)

### B1.1 `element_sim` and its spec

**Location:** `adapters/geant4/assets/element_sim/` (CMake project linking Geant4 and `g4sim`).

**Spec `element_sim.spec/1`** (schema in the same directory, using only keywords supported by `contracts/schema.py`):

| Block | Content |
|---|---|
| Coordinates | Origin at the world centre, mm; elements given by centre and half-lengths (boxes). **All centres are world coordinates** (daughters included); `element_sim` converts them to mother coordinates when placing (e.g. the field-region mother's centre is at x = −100, so Si1's world centre x = −500 becomes −400 in the mother) |
| `materials` | NIST names or mixtures (component order kept; `g4sim`'s material helper) |
| `elements` | Box elements: name, material, centre, half-lengths, mother (the world or one element; only one level of nesting), role (`passive`, `tracker-plane`, `tof-layer`, `calorimeter` (the mother), `calorimeter-active`, `calorimeter-passive`), repetition (for calorimeter sampling layers) |
| `field` | Uniform magnetic field: element it is attached to, B vector, accuracy parameters (B1.2) |
| `physics` | Physics list and EM option, cuts, regions (same semantics as `layered_sim`, through `g4sim`) |
| `source` | `type: gun`: particle, energy (`energy_MeV` or `ekin_per_nucleon_MeV`), position, direction; `gps` and `event-file` only have their interface defined (§R.9.2) and exit 2 when met |
| `run` | Number of events, threads, logical-run seed; `seeding` allows only `per-event` |
| `output.observables`, `output.blocks` | As in A2.3 (referencing `simulation-observables/1`) |
| `output.event_file` | `level`: `none` (default), `summary`, `crossings`, `hits`; `compression` (default 1); `max_events_hits` (default 100) |

- Cross-field rules (elements do not overlap, daughters inside their mother, unique names, role compatible with material) are checked in the Python adapter (`check-spec` of B1.6); C++ checks only the minimum needed to run.
- Every run delivers the three boundary artifacts (summary, column map, effective config), the same as `layered_sim`.

### B1.2 Field

- Build `G4UniformMagField`, `G4FieldManager` and `G4ChordFinder` in `ConstructSDandField`, stored as `G4ThreadLocal`; the master and each worker have their own. Building them in `Construct()` would make workers share a non-thread-safe chord finder.
- Attach to the field-region mother with `SetFieldManager(fm, true)`, propagating to all daughters.
- With a field, add `G4StepLimiterPhysics`.
- Stepper and driver are **built explicitly**: a `G4DormandPrince745` on a `G4Mag_UsualEqRhs`, wrapped in a driver (e.g. `G4InterpolationDriver<G4DormandPrince745>`) and passed to `G4ChordFinder(G4VIntegrationDriver*)` (medium confidence; check the classes and constructors against the 11.4.3 source); not the stepper chosen by `G4ChordFinder`'s default constructor (which `G4FieldParameters` does not control). The stepper class is written into the spec, and the probe records the actual stepper and driver class names via RTTI (a helix stepper would make the field-propagation check meaningless). Check the constructor signatures against the 11.4.3 source before implementing.
- Written from the API, without copying or adapting the B5 example's code (G5).

| Parameter | Nominal | Note |
|---|---|---|
| `delta_chord_mm` | 0.25 | Has no effect when the maximum step is below about 80 mm; recorded, not scanned |
| `delta_one_step_mm` | 0.01 | In a uniform field the Runge–Kutta truncation error is far below the intersection error; the scan is expected to show no effect; confirmed once |
| `delta_intersection_mm` | **1e-5** (0.01 µm) | Sets the accuracy of crossing points |
| `min_epsilon_step` | 5e-5 | |
| `max_epsilon_step` | 1e-3 | epsilon = delta one step / step length, clamped at this upper bound |
| `max_step_mm` | 10 | Needs `G4StepLimiterPhysics`; `G4UserLimits` must be set per volume and does not propagate to daughters |
| `stepper` | DormandPrince745 | Built explicitly (see above) |

- **Probe:** `SimProbe.hh` walks `G4LogicalVolumeStore`, reads back B, the chord finder and each accuracy parameter via `GetFieldManager()`; deduplicates by pointer, records the volume of the original attachment; notes that the master sees only the master's copy. A field attached to a volume inside the target counts in the `tree-v1` target hash.
- **MT test:** a UI command that exists only in the test build reports each thread's field-manager pointer; they must all differ.

### B1.3 Plane crossings and calorimeter leakage

- **Crossings:** when the primary (track ID 1) **first** enters a `tracker-plane` or `tof-layer` element (pre-step point status `fGeomBoundary` and its volume is that plane), record the pre-step point's position, direction, kinetic energy, global time and PDG code; one "recorded" flag per plane. If the source lies inside a plane there is no `fGeomBoundary`, and no row is written for that plane.
- **Calorimeter leakage:** for the mother element with role `calorimeter`, each event records the energy carried out of the mother by particles leaving it from inside (steps whose `post` point leaves that mother; a positron adds 2 mₑc²; multiplied by the track weight), split by the face crossed into `leak_rear_MeV` (+x face), `leak_front_MeV` (−x face) and `leak_lateral_MeV` (y and z faces), with the same semantics as `layered_sim`'s columns of the same names (`layered_sim` uses the world boundary as the faces, `element_sim` the calorimeter mother). The three columns go into the CSV, the `events` ntuple and the column map, for shower-containment (`geant4_benchmarks.py` line 487) and the rear-leakage fraction of B3.3.
- The per-event CSV keeps only summary columns (primary truth, total deposit per subsystem, calorimeter leakage); crossings and per-layer deposits go into the ROOT file (B1.4).

### B1.4 Per-event ROOT files

| Item | Spec |
|---|---|
| Writing | Through `G4AnalysisManager` (ROOT output type); underneath is g4tools, bundled with Geant4, so no ROOT installation and no new build dependency |
| Files | One file per job; under MT, `SetNtupleMerging(true)` has the master merge into one file (in 11.4.3 only ROOT output supports ntuple merging); path written into the run record through `tilde()` |
| Structure | Flat ntuples with scalar columns only (I, D, S), each row keyed (`event_id` plus the ntuple's own secondary key); no vector columns |
| Row order | Not fixed after MT merging; readers always sort by key |
| When written | Rows filled in `EndOfEventAction`; the file written and closed at end of run. If the run is interrupted the file is incomplete and the run is incomplete (exit 3) |
| Version | Structure `element_sim.events/1`, `event_file_version` in the file |
| Hashes | File bytes include the write time and are not bit-identical; the run record keeps both the file sha256 (integrity) and the `content_sha256` from `simroot hash` (comparison and provenance). When a logical run has several job files, `content_sha256` is computed over the union of all files sorted by key (except the `run` ntuple, which differs per file), and `processes` deduplicated by `process_id`, so it does not depend on the split |
| Size | Not committed; the run record keeps path, hashes, row counts and size per ntuple |

| ntuple | Level | One row per | Columns |
|---|---|---|---|
| `run` | from `summary` | file | sha256 of spec and column map, program version and source hash, Geant4 version, logical-run seed, event range, `event_file_version` |
| `processes` | from `summary` | process | `process_id`, `name` (the process-number table for `hits`) |
| `events` | from `summary` | event | `event_id`, primary PDG code, kinetic energy, origin, direction; total deposit per subsystem; `leak_rear_MeV`, `leak_front_MeV`, `leak_lateral_MeV`; energy leaving the world; flags |
| `deposits` | from `summary` | event × volume with a deposit | `event_id`, `volume_id`, `copy`, total deposit, deposit by charged particles |
| `crossings` | from `crossings` (also in `hits`) | event × crossed plane | `event_id`, `plane_id`, `track_id`, PDG code, pre-step position, direction, kinetic energy, global time |
| `hits` | `hits` only | step with a deposit | `event_id`, `track_id`, `step_index` (the track's step number; with `event_id` and `track_id` a unique key), `parent_id`, PDG code, `volume_id`, `copy`, pre- and post-step positions, time, deposit, step length, `process_id` |

- `process_id` is assigned at initialization by a deterministic rule (e.g. sorted by process name), independent of threads and job splits; the `run` and `processes` ntuples are filled only by the master, never by workers.
- If the number of events requested at the `hits` level exceeds `max_events_hits`, spec validation rejects it as `rejected` (exit 2).
- Estimate (J15, `crossings` level): at most about 4 kB per event uncompressed (`crossings` 10 rows × 80 B, `deposits` up to 110 rows × 28 B, `events` about 120 B); at most about 400 MB uncompressed for 10⁵ events.

### B1.5 `simroot`

**Location:** `adapters/geant4/assets/simroot/` (same CMake project as `element_sim`; links only Geant4's analysis library, no run manager).

- **Gate G-B1a (the first day):** confirm that `G4RootAnalysisReader` can read MT-merged, compressed files and string columns. Either outcome is acceptable: if it can, the design stands; if it cannot, `simroot` reads only flat scalar columns, and the strings of `run` go into a JSON side file. The result is recorded in the VALIDATION entry.

| Subcommand | Content |
|---|---|
| `info` | Row counts and columns per ntuple, content of the `run` row; JSON output |
| `dump` | After sorting by key, writes the chosen ntuple and columns as CSV (stdout or `--out`), floating point as `%.17g`; can read several files at once; `--events` selects a subset |
| `hash` | Content hash: each ntuple sorted by key, numbers normalized as hex floats, then sha256; outputs `content_sha256` |

- Exit codes per `core/status.py`. Researchers may analyse the ROOT files directly with ROOT or uproot, but neither is a dependency of the pipeline or of the required tests.

### B1.6 `check-spec` and interface consistency between the two backends

- **`geant4_run.py check-spec --spec <file>`:** validates `element_sim.spec/1` against the schema and cross-field rules (no Geant4 needed); outputs JSON `{ok, problems[]}`, exit code 0 or 2. Task C's `detector-design` calls it as a subprocess (adapters do not import each other). B1 extends `MISSING_FILE_ARGS` in `tests/skills/test_cli_robustness.py` so that a script may map to one or more argv lists (today `geant4_run.py` has only the `run` list, line 130) and registers `check-spec`.
- The three boundary artifacts from `element_sim` pass the same interface tests as `layered_sim`'s (schema, hashes, semantic names in the column map).
- **Statistical agreement compares only observables both backends produce.** J14's `stopping-power`, `range` and `thin-layer-mpv` need `primary_eloss_MeV`, `primary_fate` and `primary_end_process` (`geant4_benchmarks.py`: `transmitted()` line 233, `bench_stopping_power` line 284, `bench_range` line 325, `bench_mpv` line 365), which `element_sim` does not produce, so J14's benchmark decisions are not compared.
- Method: a slab identical to J14's nominal (`Si_study` declared as a mixture with the same composition and density, same physics settings and cuts), one logical run on each backend (`layered_sim` with `stream`, `element_sim` with `per-event`; the events differ); compare the mean and mode (A1.7) of the silicon deposit `edep_Si_MeV`, and the **total leakage** fraction of a calorimeter-like configuration (`leak_rear_MeV + leak_front_MeV + leak_lateral_MeV` over the incident energy; the faces differ between backends, the world boundary in `layered_sim` and the calorimeter mother in `element_sim`, so single-face fractions are not comparable). Each observable is decided by `equivalence` (A1.8) with a tolerance and se target (se_diff ≤ tol/4) declared in advance; on failure, do not merge (gate G-B1b).

### B1.7 Deterministic field check (`field-propagation`)

No statistics needed; only `element_sim`.

- Tracks: charged geantinos (mass 0, β = 1) at rigidities 0.6, 1, 10, 100, 1000 GV.
- Directions: normal incidence; 50 mrad in the bending plane **opposite to the bending direction** (+y for positive charge); ±50 mrad in the non-bending plane.
- §B Appendix A checks that with these directions every track reaches every Si plane and both TOF2 layers and does not leave the field-region mother. With the bending direction instead, 0.6 GV and 1 GV miss Si6.
- Reference: the analytic helix; after the track leaves the field region, piecewise straight lines; only planes the analytic track actually reaches are compared.

| Scan | Grid | Decision |
|---|---|---|
| delta intersection | 1e-3, 1e-4, 1e-5, 1e-6 mm | At nominal (1e-5), the in-plane distance √(Δy² + Δz²) ≤ 0.5 µm (ε/20) on all planes, the analytic track evaluated at the plane's x; the two finest differ by ≤ 0.2 µm; \|x − x_plane\| of Geant4's crossing point is also recorded. The result of every grid point is reported; 1e-3 mm is not assumed to fail (Geant4's intersection error is mainly along x, and in the plane it becomes only about slope × δ ≤ 0.25 µm) |
| Maximum step | 100, 30, 10, 3 mm | Same |
| delta one step and epsilon | nominal and 1/10 | Expected no change; confirmed once |
| TOF2 path time (both layers) | — | \|Δt\| ≤ 1 ps (about 0.3 mm of path), checks path length only |

- Negative control: B × (1 ± δ) on the Geant4 side, δ chosen by a trial run so that the deviation exceeds the criterion.
- The result is recorded as the `field-propagation` benchmark (verification, added to the table in B2.4); in B1 it is first recorded by tests and the VALIDATION entry. B2's `field_propagation()` reuses B1's analytic-helix oracle (the same code) rather than a second one.

### B1.8 Adapter-change process

| Item | Content |
|---|---|
| Version | 0.2.0 → 0.3.0 |
| `adapter.json` | `assets` gains `element_sim/`, `simroot/`, the `element_sim.spec/1` schema; update `purpose` |
| `SIM_SOURCES` | Today a flat tuple of file names, hashed only under `ASSETS/"layered_sim"` (`geant4_run.py`: defined at line 63, used at lines 327 and 386). Change it to a table grouped by program, `{"layered_sim": [...], "element_sim": [...], "simroot": [...], "g4sim": [...]}`; each run record records the program used and the hashes of the `g4sim` files; field code in `element_sim/Field.hh`, `Field.cc`; `layered_sim`'s hash keys are unchanged, so old records still compare |
| G5 | Statement "written from the Geant4 API; no example code (B5 included) copied or adapted", confirmed by the reviewer in the VALIDATION entry; the same entry notes the ROOT file type and `simroot` |
| Tests | Offline tests (spec validation, cross-field rules, `check-spec`); live tests (`HEP_GEANT4_LIVE_TEST=1`): geometry, field, event files, `simroot` round trip |
| Docs | The Geant4 row of `docs/capability-matrix.md`; adapter docs |

### B1.9 B1 acceptance

- [ ] `element_sim`'s J15 geometry passes overlap, material-budget and per-event energy-balance checks; the check values of §B.4.1 and §B.4.2 are recomputed by tests.
- [ ] `check-spec` returns exit 2 with the reason for every kind of cross-field error, and exit 0 for a valid spec; `check-spec` is registered in the extended `MISSING_FILE_ARGS` and passes the missing-file tests.
- [ ] Interface consistency of B1.6 and statistical agreement of the two backends (gate G-B1b).
- [ ] Under `per-event`, the same logical run with 1, 2, 4 jobs and 1, 2, 4 threads: summary integers identical, floating-point relative difference ≤ 1e-12.
- [ ] The field-manager pointers reported by the MT test command differ between threads; the field parameters recorded by the probe agree with the spec; the field counts in the target hash.
- [ ] The deterministic field check of B1.7 passes at nominal values, the result of every grid point is reported, and the negative control is caught (gate G-B1b).
- [ ] Calorimeter leakage: in a simple configuration (electrons on a thin calorimeter), `leak_*_MeV` plus deposits and energy leaving the world satisfy per-event energy balance.
- [ ] `simroot` round trip: values of I, D, S columns identical at each level; `content_sha256` identical between serial, different thread counts, and 1 and 4 jobs (consistent after deduplicating `processes`); `deposits` summed per event equals the subsystem totals in the CSV; `hits` above the cap gives exit 2; an interrupted run is incomplete.
- [ ] VALIDATION GEANT4-ELEMENT; CHANGELOG; release manifest.

---

## §B.6 Stage B2: reconstruction and contracts (geant4 adapter 0.4.0, contracts CV2)

### B2.1 `simreco` (digitization and reconstruction)

**Location:** `adapters/geant4/assets/simreco/` (CMake project; uses only the C++17 standard library and the Geant4-free `SimHash.hh`, `SimSummary.hh` and `MiniJson.hh` of `g4sim`; not linked to Geant4). Parameters (ε, σ_t, nominal B, calibration sample) are in a reco spec owned by hep-detector.

**Input:** `crossings` and `deposits` taken from the ROOT file by `simroot dump` (sorted by key, passed through a pipe, not stored), and the summary CSV.

| Step | Content |
|---|---|
| Silicon | Gaussian smearing of crossing points: bending direction (y) ε = 10 µm, non-bending direction (z) 30 µm; the fit uses the same x as the scorer (entry face) |
| TOF | Independent Gaussian smearing σ_t of each layer's time (100 ps; 150 ps separately for sensitivity); station time = mean of the two layers' times (after converting both to the station centre with the fitted track); also outputs each layer's dE/dx and the time difference of a station's two layers |
| Track | Circle fit in the x–y plane with multiple-scattering covariance (without it, χ²/dof is in the thousands at 1 GV), giving the curvature κ; straight-line fit in the x–z plane, giving the dip angle λ; R_reco = C·B/(κ cos λ) with the nominal B (total momentum, C = 0.2998 GV/(T·m)); outputs R, χ², degrees of freedom |
| True rigidity | 1/R_true = mean of \|q\|/p_i from the crossing records of the six planes (**total momentum** p_i; for unit charge 1/R = 1/p); R_true and R_reco both use total momentum, avoiding the p vs p_T difference (about 0.125 % at 50 mrad, more than the 0.05 % tolerance of the muon field check) |
| β | Path length with the two station centres as end points, including the straight segments TOF1→Si1 and Si6→TOF2 and the 3D inclination; at low β reports the change in β between the stations |
| Calorimeter | Total deposit in active layers divided by the **electron** sampling fraction; the sampling fraction is obtained from a 10 GeV electron sample of role `calibration`; also outputs e/mip |
| Random numbers | Each event's digitization random stream comes from the SplitMix64 of `SimHash.hh`, seeded with H(S, i, "digi") (H of A1.4; S the logical-run seed, i the event number); normal deviates from the Box–Muller of `SimHash.hh`; not `std::normal_distribution` (libstdc++ and libc++ give different output). Separate from Geant4's random stream. Bit-identical on the same platform; across platforms libm functions such as `log` and `cos` differ, so bit identity is not guaranteed and only a relative difference ≤ 1e-12 is required; build with `-ffp-contract=off` |

**Output:** a per-event result CSV (R, χ², β, calorimeter energy, etc.) and a run summary (`simulation-summary/1`, producer `simreco`; block accumulators of observables such as (1/R_reco − 1/R_true)·R_true and β − β_true).

- **Fitter unit tests:** `tracker_resolution.py` does not fit; it only computes the curvature resolution from a parabola least-squares fit (`curvature_sigma`, line 89). The test therefore compares, on toys without multiple scattering (R ≥ 300 GV), the σ(1/R) and pull width of the C++ fit with the measurement-term resolution from `tracker_resolution.py momentum` (`mdr_intrinsic_gev`), within the toys' MC error; pull width within 1 ± 3σ_MC.

### B2.2 `geant4_run.py reco` and `table`

- `reco`: runs `simroot dump` and `simreco`; each execution writes one computational-run record (with `**trace.provenance()`, `simreco`'s program hash, the hashes of the input run records and the ROOT file's `content_sha256`, and the list of dumped ntuples and columns). Changing digitization parameters does not require rerunning the simulation.
- `table`: writes reconstructed results (e.g. rigidity resolution vs rigidity) as a simulated dataset-record (with `trace.provenance()`).
- Exit codes per `core/status.py`: 0 ok, 1 negative verdict, 2 `rejected` (unreadable input, including missing files), 3 incomplete.
- **CLI registration:** add `reco` and `table` to `MISSING_FILE_ARGS` as extended in B1 (B1.6).

### B2.3 Result tables and transitive processing chains

- **Transitive processing chain:** today `dependencies.py` requires every input of a simulated table to be a computational-run with `extension.simulation` or `extension.study`; reconstruction records have neither. CV2 changes this: the input chain may be arbitrarily deep, as long as every level is a recorded computational-run and every root of the chain is a simulation run (needs hep-computing's agreement; §P.7 item 8).
- When the study is `unvalidated`, the table stays `unvalidated`; a communication using it gets the `communication.simulated_source` warning, and figures are marked "Simulation".

### B2.4 Validation classes, table entries and `change`

**New benchmark table entries** (A1.1 format; grade is class; `GRADES` and the study spec's benchmark and grade enums gain them as well; the functions go in `geant4_benchmarks.py` and read only summaries or `simroot dump`):

| benchmark | Class | Supported kind | Scope dimensions | Computed in |
|---|---|---|---|---|
| `field-propagation` | verification | — | — | `field_propagation()`, reading `crossings` from `simroot dump` and the analytic helix (B1.7) |
| `field-propagation-muon` | sanity | — | — | `field_propagation_muon()`, reading `simreco`'s summary |
| `tof-beta` | verification | — | — | `tof_beta()`, reading `simreco`'s summary |
| `tof-layer-consistency` | verification | — | — | `tof_layer_consistency()`, reading `simreco`'s summary |
| `sampling-fraction` | sanity | — | — | `sampling_fraction()`, reading `element_sim`'s summary |
| `regression-comparison` | regression | — | — | `regression_comparison()`, reading the summaries of two versions |
| `surrogate-comparison` | surrogate | — | — | `surrogate_comparison()`, reading the summaries of the surrogate (a) and the reference simulation (b) |

- **verification:** does not count for upgrade.
- **regression:** the role enum gains `regression`. The same study with the same settings runs once at each of two versions (plugin, backend or Geant4); the point_id of each is the version tag, so S differs and the samples are independent (no clash with A1.4's uniqueness). Only scalar observables are compared (histogram comparison belongs to the distribution-level benchmarks deferred in §B.9). Both versions must be runs from A1 on (both carry S and a summary). The decision is made by the decision engine's new `change(diff, se, ν, tol, m)`: `changed` = |diff| − t_{1−α/m}·se_diff > tol; `unchanged` = pass of `equivalence`; otherwise `unresolved`. Count observables take the exact-interval branch, as in `equivalence` (A1.7). Tolerance and α are declared in advance. The record does not affect the label; a reference observable marked `changed` may trigger a sci-fix check.
- **surrogate:** a surrogate model **never changes the physics label**. A surrogate study declares its reference study (a study record, not a run record; run records carry no upgrade) and scope; decided by `equivalence` (χ² only as a diagnostic). The comparison takes a = surrogate, b = reference simulation. On pass it records `extension.study.surrogate = {reference_study_ref, reference_sha256, scope}`, the scope being the intersection of the declared scope and the reference study's scope; `dependencies.py` re-derives `reference_sha256` and the scope intersection from the reference study record and checks them. Task C's F0 and F1 evaluations architecturally belong to this class.
- Gating: `strict or _at_least(contract_version, CV2)`, no warning branch.

### B2.5 Adapter-change process and CI

| Item | Content |
|---|---|
| Version | 0.3.0 → 0.4.0 |
| `adapter.json` | `assets` gains `simreco/` and the reco-spec schema; update `purpose` |
| `SIM_SOURCES` | Add a `simreco` group |
| CI | A C++17 CI job builds and tests `simreco` (required or optional is the maintainer's decision, §P.7 item 9) |
| Docs | Adapter docs, `geant4-study-protocol.md` (validation classes, processing chains, `reco` and `table`) |

### B2.6 B2 acceptance

- [ ] `simreco`'s fitter unit tests pass per B2.1; `simreco` is built and tested in a CI job (a required job; or, if the maintainer decides it is optional, an optional job plus a local build-and-test record).
- [ ] `simreco`'s digitization output is bit-identical on the same platform; between Linux (libstdc++) and macOS (libc++) the relative difference is ≤ 1e-12 (built with `-ffp-contract=off`).
- [ ] `simreco`'s summary passes the same consistency test as A2.9 (Python recomputes from the per-event result CSV).
- [ ] `reco` and `table` are registered in `MISSING_FILE_ARGS` and pass the missing-file tests.
- [ ] A processing chain of three or more levels (simulation → reconstruction → table) is accepted by `dependencies.py`; it is rejected when a root is not a simulation run.
- [ ] The new table entries agree with `GRADES` and the study spec's enums (consistency test); the verification class does not count for upgrade.
- [ ] Toys of `change`: probability of changed when the true difference equals tol ≤ α/m + 3σ_MC; report the probability of changed at a true difference of 2·tol (power) and of unchanged at 0; a regression check (e.g. J14 on two plugin versions) produces a `changed`, `unchanged` or `unresolved` record without affecting the label.
- [ ] Contract tests of surrogate: a record carrying `extension.study.surrogate` that declares `validated-in-scope` is rejected; a reference that is not a study record is rejected.
- [ ] J14 still passes under `--strict`.
- [ ] VALIDATION GEANT4-RECO; CHANGELOG; release manifest.

---

## §B.7 Stage B3: J15 study

### B3.1 J15's study spec

- Declares: observables (rigidity resolution, β resolution, sampling fraction, total deposit, rear leakage fraction; referencing `simulation-observables/1`), K and B, benchmarks, convergence plan, variations, stopping rule.
- All results `unvalidated`; the README and the study record state its role as a "verification carrier".

### B3.2 Validation ladder

| Check | Class | Reference | Spec | Negative control |
|---|---|---|---|---|
| overlap | implementation | — | — | Shift one Si plane to create an overlap |
| Per-event energy balance (J15 geometry) | implementation | Energy conservation | — | Omit 2 mₑc², double counting |
| Material budget (geantino) | implementation | PDG X₀ sum | Tolerance about 2 % (Geant4's X₀ formula differs from PDG by about 1 %) | Pb density ± δ |
| `field-propagation` | **verification** | Charged geantino against the analytic helix | B1.7 | B × (1 ± δ) on the Geant4 side |
| `field-propagation-muon` | **sanity** | Plane-averaged true 1/R (B2.1) | μ⁻ 1, 10, 100 GV; observable: mean of (1/R_reco − 1/R_true)·R_true; decided by `equivalence` (A1.8) with `tolerance_mode: absolute` and tolerance 0.05 % (the observable is already relative); SE target 0.1 %, N from the trial run per A1.9 (estimates: about 400 at 1 GV, about 7400 at 100 GV, for SE of about 0.07 % and 0.10 %) | B × (1 ± 1 %) on the Geant4 side |
| Fitter unit test | test (not a benchmark) | B2.1 | — | — |
| One-off multiple-scattering comparison | sanity | The analytic term of `multiple_scattering.py` (no log); optionally `toy_spectrometer.py` (needs NumPy) | μ and p, 1–10 GV, with β | — |
| `tof-beta` | **verification** (bookkeeping) | Kinematics along the true trajectory | — | Scorer test flag injects a time offset; there is no physics control on the Geant4 side, noted in the docs |
| `tof-layer-consistency` | **verification** (bookkeeping) | Time difference between a station's two layers against "inter-layer path length / βc" (66.7 ps at β = 1, normal incidence) | Mean residual 0; width √2 σ_t (141 ps at 100 ps) | Test flag injects an offset into one layer's scorer time |
| `sampling-fraction` | sanity | Ratio of ionization dE/dx at the run momentum from the PDG muon energy-loss tables (Groom et al., obtained via hep-citations) | μ⁻ 1 GeV; statistic Σ PVT deposit / Σ (PVT + Pb) deposit; plausible range ±10 % (the reviewer's Bethe estimate is about 0.271); different seed from the `calibration` sample | PVT density ± δ |
| Shower containment | sanity | PDG gamma profile, effective critical energy of the mixture about 10.2 MeV | Electrons 1–100 GeV; `leak_*_MeV` (B1.3) | — |
| `longitudinal-profile` (0.21.0) | not applicable | Its reference is the published ALICE FoCal-E measurement, valid only for that stack; J15's calorimeter differs, and is embedded | — | — |
| Optional: stopping power in an isolated PVT slab | reference (`configuration: isolated`) | Bethe (RPP 2024 eq. 34.5) | p, T = 200–600 MeV (βγ ≈ 0.69–1.30, below PVT's 10^x₀ ≈ 1.40, so the density correction is 0), 1 cm slab, nuclear interactions excluded (about 1 %); Sternheimer parameters from Sternheimer, Berger & Seltzer (1984), checked via hep-citations | PVT density ± δ |

The optional last item runs in an isolated slab (a single element of `element_sim`) as a separate study record, not part of the J15 study, to show the upgrade path for a new material; its label is decided by A1.3's isolation rule and does not affect the J15 study's `unvalidated`. Event counts and decisions follow A1.6–A1.10.

### B3.3 Calorimeter production-cut convergence

- Grid: 0.1, 0.3, 0.7, 1.0 mm.
- Sample: 10 GeV e⁻; trial first, then N per A1.9.
- Observables: total deposit (relative tolerance 1 %, about 400 showers per point), rear leakage fraction (`leak_rear_MeV` divided by the incident kinetic energy, back face of the calorimeter mother only; **absolute** tolerance 0.002, `tolerance_mode: absolute`, about 5000 showers per point). These two numbers exclude the two-stage factor f ≈ 1.97 (A1.9); with f, about 770 and 9,900 showers per point.
- Events per point: the larger of the two; decision per A1.8 (`equivalence`).
- The Si production cut is not converged in J15: it affects only the Si deposit, and J15's Si results are not used as evidence. The study spec's `convergence_plan.observables` gains total deposit and rear leakage fraction. The parameter sets each benchmark depends on are declared in advance and checked against the probe's actual settings.

### B3.4 Variations

| Variation | Scope | Rule |
|---|---|---|
| EM option4 vs option3 | Calorimeter profile, sampling fraction | `G4R-PRECISION-EM` |
| FTFP_BERT_EMZ vs **QGSP_BIC_EMZ** | Nucleons below 1.5 GeV; final-state observables: deposit in the 5 layers after the first interaction, energy of charged secondaries after the interaction. Interaction probability and first-interaction depth are reported only when the probe confirms the two inelastic cross sections differ (the two physics lists may share nucleon cross sections, and then the difference is 0 by construction; this is the same kind of problem as the false zero from shared models warned about in the protocol's §6 Variations, lines 157–162) | `G4R-BIC-RANGE`; below 3 GeV for π and at 6–12 GeV for hadrons both use the same model and must not be used as a variation |
| Vacuum vs air | Multiple scattering, rigidity resolution | — |

### B3.5 TOF time-resolution sensitivity

- `simreco` reconstructs once with σ_t = 100 ps and once with 150 ps (same simulation, no rerun).
- Report σβ/β for both (expected about 2.3 % and 3.5 %) and the effect of β resolution vs rigidity; the README says that 100 ps is more optimistic than AMS-02's system resolution (about 140 ps).

### B3.6 Recorded-data budget

- `check_packaging.py` caps each file at 2 MiB (`MAX_BYTES = 2 * 1024 * 1024`, in bytes); J14's `recorded/` totals 2,447,979 bytes (about 2.45 MB; the 2.6 MB shown by `du -h` includes file-system blocks).
- ROOT files are not committed; run records keep only the path, file sha256, `content_sha256`, row counts and size per ntuple; ROOT files needed by tests are produced in live tests.
- J15 commits only: run summaries (simulation and reconstruction), effective configs (stored by content hash), column maps, summary CSVs with reduced columns (benchmark runs), reduced crossing and deposit records extracted with `simroot dump --events` (for offline replay tests of `simreco`; the event subset set by the budget), reconstructed result tables.
- Each file ≤ 2 MiB, J15's `recorded/` total ≤ 3 MB.

### B3.7 Registration, journey and docs

| Item | Content |
|---|---|
| Script count | No new scripts in hep-detector; the count test (`DetectorScriptCount` at line 145 of `tests/skills/test_documented_output_claims.py`) stays at 21, and "twenty-one scripts" on line 47 of `docs/capability-matrix.md` is unchanged |
| Routing table | `skills/hep-detector/SKILL.md` not changed; descriptions of J15, `element_sim` and `simreco` go into `geant4-study-protocol.md` and the adapter docs |
| Journey | J15; `docs/researcher-journeys.md`, the examples table of `docs/maintenance.md`; `tests/examples/test_geant4_minimal_spectrometer.py` (replay and compare decisions) |
| Capability | `docs/capability-map.json` and `docs/capability-map.md` (new entry under `full-detector-simulation`, run `capability_map.py --write`), `docs/capability-matrix.md` |
| Routing | New routing case for J15; `check_routing_static.py` reads the journey list from `docs/researcher-journeys.md`, so once J15 is in the table it **must** have a routing case. Rerun the live Geant4 cases, including the existing Traditional Chinese underspecified case `g4-underspec-2` |
| Description length | Description 1,016 / 1,024 characters; routing cases reuse existing trigger words, the description is not changed |
| README | J15's list of simplifications (§B.4.1), comparison with PAMELA and AMS-02 (§B.4.3), its role as a "synthetic geometry, verification carrier" |
| Independent review | This task's Markdown (protocol changes, J15 README, this part) is reviewed with 0.22.0's `review.py`; its record is advisory only and, per O04/O14, does not replace the human G5 confirmation |
| Other | `reference_inventory.py --check`, CHANGELOG, release manifest |

### B3.8 B3 acceptance

- [ ] `field-propagation` (B1.7's result, written as a benchmark record with B2.4's table entry), `field-propagation-muon`, `tof-beta`, `tof-layer-consistency`, `sampling-fraction` and shower containment are complete and listed in the J15 study record; if the optional isolated PVT benchmark is run, its study record is listed separately; each negative control is caught per B3.2, or the absence of a control is noted.
- [ ] Calorimeter cut convergence (B3.3) and variations (B3.4) are complete, with decisions and the incomplete rate recorded in the study record.
- [ ] The TOF σ_t sensitivity at 100 and 150 ps is reported.
- [ ] Recorded budget, registration items and docs all done; J15's offline replay test passes.
- [ ] An independent agent, using only the docs and tools, completes "rigidity resolution of a 1 GV proton in J15": the result record passes `validate.py --strict`, the label is `unvalidated`, the resolution (central 68 % half-width of the distribution of (1/R_reco − 1/R_true)·R_true) lies within the range of the 1 GV proton row of the §B.4.2 multiple-scattering table (1.8–2.6 %; the measurement term is negligible at 1 GV), and no maintainer help is needed.
- [ ] VALIDATION GEANT4-J15; CHANGELOG; release manifest.

---

## §B.8 Contracts and versions

| Object | Location | Version |
|---|---|---|
| `element_sim`, `element_sim.spec/1`, `element_sim.events/1`, `simroot`, `check-spec` | geant4 adapter | 0.3.0 (B1) |
| `simreco`, reco spec, `reco`, `table` | geant4 adapter (C++, not linked to Geant4) | 0.4.0 (B2) |
| verification, regression, surrogate classes and table entries; regression role; transitive processing chains | `contracts/validate.py`, `contracts/dependencies.py` | CV2 (minor, gated) |
| Decision engine `change` | `core/stats/decisions.py` | with the plugin version |
| `GRADES` and the study spec's enums; total deposit and rear leakage fraction in `convergence_plan.observables` | hep-detector | with the plugin version |

---

## §B.9 Not done and deferred

| Item | Decision | Reason / trigger |
|---|---|---|
| σ(1/R) in the measurement-dominated region as a benchmark | Not done | Replaced by the fitter unit test |
| `skills/hep-detector/scripts/digitize_reconstruct.py` | Not done | Replaced by `simreco` in C++ |
| New geometry features in `layered_sim` | Not done | New features only in `element_sim` |
| Reading ROOT directly from Python (uproot) in the pipeline | Not done | Through `simroot` |
| Ion sources and Birks visible energy (J17) | Deferred | Cosmic-ray nuclide studies, and a documented Birks constant for PVT. Implementation per 11.4.3: get the ion with `GetIon(Z, A)` in `GeneratePrimaries`; set kB in `Construct` (`GetIonisation()->SetBirksConstant`), call `G4EmParameters::Instance()->SetBirks(true)` at PreInit, then get it via `G4LossTableManager::Instance()->EmSaturation()` (check the API names against the 11.4.3 source when implementing) |
| Non-box solids, rotations, GDML input, field maps, fringe fields in `element_sim` | Deferred | The first study that needs them and cannot use a user application (also the trigger for task C's cylindrical geometry) |
| Primary exit records in `element_sim` (J14's observables) | Deferred | When J14 is migrated to `element_sim` and `layered_sim` retired (§P.8) |
| Distribution-level benchmarks (including histogram comparison for regression), combination of observables, profiles, `gps` and `event-file` sources, `simreduce` | Deferred (interfaces defined in §R.9.2) | Each one's first use case |
| RNTuple, vector columns | Deferred | ROOT file size or read speed becomes a bottleneck |

For other items not done or deferred, see §A.9.

---

## §B.10 Open decisions and residual risks

**Open decisions** (numbers from §P.7): item 7 (how to confirm G5), item 8 (transitive processing chains and the classification of CV2), item 9 (the CI job for `simreco`), item 10 (where ROOT files are stored), item 11 (maintenance ownership of `element_sim`).

**Residual risks:**
1. The sampling-fraction reference needs the PDG muon energy-loss tables; the optional PVT benchmark needs Sternheimer parameters. Both need literature records via hep-citations before use.
2. Calorimeter showers dominate CPU time; convergence of rear leakage needs about 5000 showers per point (about 9,900 with the two-stage factor); event counts are set by trial runs and recorded.
3. The read capability of `G4RootAnalysisReader` is unverified (gate G-B1a).
4. ROOT files of large samples can reach hundreds of MB; under MT merging, worker data may accumulate in memory until end of run (actual behaviour depends on 11.4.3's ntuple merging and basket settings, not checked); `hits` has an event cap; size and memory confirmed in trial runs.
5. Maintenance cost of two Geant4 programs; duplication controlled through `g4sim` (§P.8).
6. Hadronic variation: if the two physics lists share nucleon inelastic cross sections, the interaction probability does not change; only final-state observables are reported (B3.4).
7. Some Geant4 behaviour (stepper construction, the Birks API, the direction of the intersection error) rests on the reviewer's experience and was not checked line by line against the 11.4.3 source; check it first when implementing.
8. Effort is estimated at the start of B1 based on the actual `g4sim`.
9. Task A's residual risks (the block-independence assumption, near-threshold decisions, the probe assuming worker and master settings are the same) also apply; see §A.10.

---

## §B.11 Suggested order of work

At the start of each stage, create and confirm that stage's isolated worktree per §P.10.2 and do every step in it; remove it per §P.10.5 after merging.

**B1**
1. Pre-start checks (§B.0); the one-day `G4RootAnalysisReader` trial (gate G-B1a).
2. `element_sim`'s spec, schema, `check-spec` and geometry (B1.1, B1.6); two-backend consistency with a slab configuration identical to J14.
3. Field (B1.2) and MT test; deterministic field check (B1.7).
4. Build the J15 geometry (§B.4.1); pass overlap, material budget, energy balance; recompute the check values of §B.4.1 and §B.4.2 in tests.
5. Plane crossings and calorimeter leakage (B1.3), ROOT files (B1.4), `simroot` (B1.5).
6. Adapter-change items of B1.8; tick all of B1.9; run the checks of §A.8.

**B2**
1. `simreco`'s fitter unit tests first, then the `simroot dump` input (B2.1); CI job.
2. `reco` and `table`, extension of `MISSING_FILE_ARGS` (B2.2); transitive processing chains (B2.3).
3. Validation classes, table entries, `change`, regression role and contract tests (B2.4).
4. Adapter-change items of B2.5; tick all of B2.6; run the checks of §A.8.

**B3**
1. J15's study spec (B3.1); run the validation ladder in E2 (B3.2).
2. Calorimeter cut convergence, variations, TOF sensitivity (B3.3–B3.5).
3. Recorded data, registration, journey, docs, the independent-agent acceptance problem (B3.6–B3.7); tick all of B3.8; run the checks of §A.8.

---

## §B Appendix A: Numbers

Computed by `j15_design_estimates.py` (this folder; standard library only, scipy optional; A_N checked against the closed form by exact rational least squares).

**Geometry**
- Si centres: −500, −340, −180, −20, 140, 300 mm; L = 0.800 m.
- Field region: −520 … 320 mm; margins 19.85 mm at each end.
- TOF1 layers −810 … −800, −790 … −780; TOF2 layers 490 … 500, 510 … 520; station-centre distance D = 1.300 m; world ±1200 mm.

**Tracking**
- A_N = 720 (N−1)³ / [(N−2) N (N+1)(N+2)]: A₄ = 81.0, A₆ = 66.96, A₈ = 57.17 (N equally spaced points including both ends, equal weights).
- MDR (measurement term only) = C B L² / (ε √A_N): 1172 GV for C = 0.2998 (1173 GV for C = 0.3).
- Multiple-scattering term (β = 1, with log): 1.34 %, bracketed with a factor of 1.0–1.4.

| B (T) | N | MDR (GV) | Multiple-scattering term (β = 1) | Rigidity where the two terms are equal |
|---|---|---|---|---|
| 0.15 | 6 | 352 | 4.5–6.2 % | 16–22 GV |
| **0.5** | **6** | **1172** | **1.3–1.9 %** | **16–22 GV** |
| 1.0 | 6 | 2345 | 0.7–0.9 % | 16–22 GV |
| 0.5 | 4 | 1066 | 1.1–1.5 % | 11–16 GV |
| 0.5 | 8 | 1269 | 1.6–2.2 % | 20–28 GV |

**Field-check grid** (50 mrad, opposite to the bending direction, positive charge):

| Rigidity | Max \|y\| in field | y at Si1 … Si6 (mm) | y at the two TOF2 layers |
|---|---|---|---|
| 0.6 GV | 29.0 | 25.0, 29.0, 26.6, 17.8, 2.5, −19.3 | −50.0, −53.2 |
| 1 GV | 32.4 | 25.0, 30.6, 32.4, 30.3, 24.4, 14.6 | 0.2, −1.4 |
| 10 GV | 60.7 | 25.0 … 60.0 | 67.1, 67.9 |
| 100 GV | 65.5 | 25.0 … 64.5 | 73.8, 74.8 |
| 1000 GV | 66.0 | 25.0 … 65.0 | 74.5, 75.5 |

If the direction is the same as the bending (−50 mrad): y at Si6 is −151 mm for 0.6 GV and −116 mm for 1 GV, both missing Si6. At normal incidence (0 mrad), 0.6 GV gives y ≈ −85 mm at Si6 and ≈ −126, −130 mm at TOF2's two layers, still within acceptance (printed by `j15_design_estimates.py`).

**TOF**: σ_station = σ_layer/√2, σβ/β = σ_layer c / D; 80, 100, 150 ps per layer give 1.8 %, 2.3 %, 3.5 % (with one layer per station 2.6 %, 3.3 %, 4.9 %). Time of flight at β = 1 between a station's two layers 66.7 ps; resolution of the two layers' time difference √2 σ_layer (141 ps at 100 ps).

**Calorimeter**: 18.41 X₀, 0.886 λ_I, 35 cm; effective Molière radius 3.95 cm; the mip energy-loss ratio 0.284 is only a ratio of dE/dx_min, **not** a reference value.

**Material before the calorimeter**: 11.32 % X₀ (four TOF layers 9.40 %, 83 %; Si 1.92 %), 5.46 % λ_I; TOF1, before the tracker, is 4.70 % X₀ of it.

**Event counts** (difference se ≤ tol/4, without the two-stage factor): 10 GeV electron total deposit (tolerance 1 %) about 392; rear leakage (absolute tolerance 0.002) about 5000. Multiplied by the two-stage factor f = F_0.90(15,15) ≈ 1.97, about 770 and 9,900.

## §B Appendix B: Sources

- PDG Atomic and Nuclear Properties (retrieved 2026-10-21): [Silicon](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/silicon_Si.html), [Lead](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/lead_Pb.html), [Polyvinyltoluene](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/polyvinyltoluene.html)
- PDG Review of Particle Physics 2024, chapter 34: eqs. 34.5, 34.12, 34.16, 34.34–34.36 (equation numbers per the plugin's VALIDATION GEANT4-STUDY)
- Geant4 v11.4.3 sources relevant to fields and event files: `G4FieldManager.hh`, `G4ChordFinder.hh`, `G4PropagatorInField.cc`, `G4FieldParameters`, `G4LogicalVolume`, `G4ChargedGeantino.cc`, `G4VAnalysisManager.hh`, `G4EmSaturation`, `G4LossTableManager`, `G4IonTable`, `G4NistMaterialBuilder.cc`
- Geant4 Book for Application Developers, [Basic Examples](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Examples/BasicCodes.html) (B4, B5)
- Sources for PAMELA and AMS-02 are in §R.14
- To obtain: PDG muon energy-loss tables (Groom, Mokhov & Striganov); Sternheimer, Berger & Seltzer (1984), *Atomic Data and Nuclear Data Tables* 30, 261

## §B Appendix C: Version history

| Version | Content |
|---|---|
| Detector document and v5 | Single-axis stacked spectrometer; Gluckstern small-N formula corrected; field direction and field-check grid |
| 2026-10-22 | TOF1 and TOF2 with two layers each; digitization and reconstruction moved to C++; per-event ROOT files; split out as task B; rewritten for the new architecture (`element_sim` replacing spec/2; B1, B2; PAMELA and AMS-02 comparison and TOF sensitivity) |
| 2026-10-23 | Fixes after independent review (B1.6 compares only shared observables, calorimeter leakage, table entries, surrogate and regression rules, total-momentum rigidity, CLI and `SIM_SOURCES`, portable random numbers, explicit stepper construction, etc.) |
| **2026-10-23 (this version)** | **Reorganized per the plan (Part 1): B2 split into B2 (reconstruction and contracts) and B3 (J15 study), so that task C's C2 waits only for B2; deterministic field check moved to B1.7; new `geant4_run.py check-spec` (B1.6, for task C to use as a subprocess); the decision engine's `change` and the regression role added in B2; contract version written CV2; section numbering aligned with tasks A and C** |
| 2026-10-23 | Added the isolated-worktree execution rule: header, the first step of §B.0, the start of §B.11 (§P.10) |

---

# Part 4 — Task C: automated detector design search (§C)

> Order: C1 after A1 (may run in parallel with A2 and B); C2 after B2 and C1; C3 after B3 and C2
> Date: 2026-10-23
> In one sentence: the user writes down the physics requirements; Claude freely chooses and combines detector structure types from a component catalogue, an optimizer searches on multi-fidelity simulation, and independent confirmation runs report the best designs meeting the requirements and their trade-offs

---

## §C.0 Task card

**Goal.** Let the AI start from "physics requirements", choose detector structure types by itself (tracker planes, magnet region, TOF, calorimeters, passive layers, …), combine them freely and tune their parameters, and arrive at an optimized design (or a Pareto front of trade-offs) that meets the requirements, with results that withstand statistical and provenance checks.

**Three stages:**

| Stage | Content | Prerequisite | Version |
|---|---|---|---|
| **C1** Requirements, grammar and fast search | Requirements spec, component catalogue, design grammar and realization, F0 analytic evaluation, standard-library optimizer (Sobol, NSGA-II), search record (F0-only), agent protocol, closure tests | A1 | new adapter `detector-design` **0.1.0** |
| **C2** Simulation evaluation and confirmation | Additions to `core/` (`threshold`, `order`, paired comparison, `values`, search roles and seed_group); F1/F2 evaluation; confirmation runs and requirement decisions; robustness and guards; CV3 | B2, C1 | detector-design **0.2.0**, geant4 adapter **0.5.0**, contracts **CV3** (minor) |
| **C3** Example | J16 automated-design example (compared with J15); optional MOBO backend; journey and routing | B3, C2 | detector-design **0.3.0** |

**Out of scope:** differentiable simulation and differentiable surrogates (the MODE route, §C.9); non-box geometry (cylindrical collider detectors); optical physics (Cherenkov, RICH); reinforcement learning; letting an LLM alone decide the best design.

**Deliverables:** `adapters/detector-design/` (schemas, catalogue, realization, evaluation, search, report); additions to `core/` (C2.1); hep-detector reference `detector-design-search.md` (with the agent protocol); CV3 contract rules; closure tests; the J16 example; VALIDATION entries DESIGN-SEARCH-F0 (C1), DESIGN-SEARCH (C2), DESIGN-SEARCH-J16 (C3); CHANGELOG; release manifest.

**Definition of done:** every box in the acceptance lists C1.9, C2.9 and C3.4 is ticked; every check in §A.8 passes; gates G-C1, G-C2a, G-C2b, G-C3 (§P.6) pass.

**Main decisions:**
1. **Claude is the designer, not the judge.** Claude chooses structure types, proposes seed designs, sets the search ranges and interprets results; "which design is best and whether it meets the requirements" is decided only by recorded evaluation and statistics. Claude's proposals go through the same evaluation pipeline as randomly generated candidates, with no privilege (§C.4.2).
2. **Free combination, within a grammar.** Structural freedom comes from "component catalogue × composition rules": any sequence of components passing the validity rules is a legal design. New component types enter only through a reviewed catalogue change (§C.4.4).
3. **Multi-fidelity.** F0 analytic formulas screen 10⁴–10⁶ designs; F1 Geant4 with few events refines hundreds; F2 full statistics only for a few finalists (§C.4.5).
4. **Search and confirmation are separate.** Search-stage values suffer from the "winner's curse", are used only for ranking and are never reported as results; reported performance comes only from pre-declared confirmation runs with independent seeds (§C.4.7).
5. **The result is a proposal, not a validation.** Searched designs are always labelled `unvalidated`; the record states "simulation-optimized design", with the search size, confirmation runs and robustness.
6. **The statistical additions task C needs are added by task C itself** (§P.2 R1), located in `core/` so that hep-detector and the adapter share them (C2.1).

**First step:** create the isolated worktree for this stage per §P.10.2 (`.claude/worktrees/geant4-<stage>`, branch `geant4-<stage>`, based on the latest `main` that contains the prerequisite stages), and confirm `git rev-parse --show-toplevel`, `git branch --show-current` and `git status`. Every following step happens in this worktree.

**Before starting:** read §P.0–§P.6; read §A.1, §A.3, §A.4 and A1.4–A1.9; for C2 also §B.4, B1.1, B1.6, B2.1, B2.4. Check the facts this part quotes with the method of §A Appendix C.

---

## §C.1 Terms and files

| Term | Meaning |
|---|---|
| requirements spec | `detector-requirements/1`: physics objectives, hard requirements (constraints), resource limits and envelope, declared in advance |
| design grammar | `detector-design/1`: a design description made of catalogue components arranged by composition rules |
| component catalogue | `catalogue/1`: the available structure types (block types), each with parameters, ranges, validity rules, realization rule and mass/cost model |
| realize | The deterministic function turning a design into `element_sim.spec/1` (and `simreco`'s reco spec) |
| genome | The design encoding the optimizer sees: structure (which components, order, count) + categorical parameters (materials) + integers + continuous parameters |
| fidelity F0, F1, F2 | F0 analytic; F1 Geant4 with few events; F2 full evaluation per task A's statistical spec |
| finalists | The few designs that go to F2 and confirmation |
| confirmation run | A logical run with role `confirmation`, whose seed was never used in the search; reported performance comes only from it |
| winner's curse | When choosing the best of n noisy evaluations, the expectation of its estimate is optimistic |
| Pareto front | The set of designs no other design matches or beats on every objective while beating on at least one |
| search size | The number of designs actually evaluated at each fidelity; written into the record, like a look-elsewhere effect |
| seed_group, paired comparison | A group of runs sharing one S; the SE of a difference is estimated from per-block differences (common random numbers; C2.1) |
| Notation | "C1.3" is a work item of this part; "A1.8", "B2.1" are work items of tasks A and B (work-item numbers are unique across the document); "§C.4" is a section of this part; "§A.3", "§P.7", "§R.6" etc. are sections of other parts of this document |

**Main files (relative to `plugins/hep-research/`):** `adapters/detector-design/` (new: `adapter.json`, `assets/design_search.py`, `assets/catalogue/`, `assets/schemas/`); `core/stats/decisions.py`, `core/stats/batch_means.py`, `core/simulation/summary.py`, `core/simulation/seeds.py` (additions in C2); `contracts/validate.py`, `contracts/dependencies.py` (CV3); `adapters/geant4/assets/g4sim/SimSummary.hh` (`values` added in C2); `skills/hep-detector/references/detector-design-search.md` (new); `core/physics/tracking.py` (new in C1: `curvature_sigma` and the scattering formulas moved out of `tracker_resolution.py`); `skills/hep-detector/scripts/tracker_resolution.py`, `multiple_scattering.py` (changed in C1 to call the `core/` functions, output unchanged); `adapters/detector-design/assets/catalogue/materials.json` (new in C1, the shipped material table).

---

## §C.2 Prerequisites and interfaces provided

| Provider | Interface | Use in task C | Needed in |
|---|---|---|---|
| Task A | `core/simulation/seeds.py` (H, S) | F1: S = H(search_id, role, seed_group); F2 and confirmation: S = H(search_id, role, design_sha256) (C2.1) | C1 (record), C2 |
| Task A | `core/simulation/summary.py`, `simulation-observables/1` | The search spec references the same observable declaration; reading F1/F2 summaries | C2 |
| Task A | `core/stats/batch_means.py`, `equivalence` of `decisions.py`; two-stage event count (A1.9) | F1/F2 estimates; event counts of confirmation runs; comparing F0 with confirmation | C2 |
| Task A | Evidence roles, uniqueness of S (A1.4) | C2 adds search roles, confirmation and seed_group | C2 |
| Task A | Name-free `tree-v1`; effective configs stored by content hash (A2.4) | Design cache; settings of hundreds of runs are not stored repeatedly | C2 |
| Task A | Schema keywords (A2.7) | detector-design schemas; before A2 merges, C1's schemas do not use `maxItems`, `maximum`, `exclusiveMaximum`, and those limits are checked in Python (C1.1) | C1 (if A2 is merged), C2 |
| Task B | `element_sim.spec/1` and `geant4_run.py check-spec` (B1.1, B1.6) | Validation of realizations (subprocess) | C1 (test added after B1 merges), C2 |
| Task B | Calorimeter mother and `leak_*_MeV` (B1.3) | Objectives of calorimeter components | C2 |
| Task B | `simreco`, `geant4_run.py reco` (B2.1, B2.2) | Reconstruction at F1/F2 | C2 |
| Task B | Surrogate class, decision-engine `change` (B2.4) | F0 and F1 are architecturally surrogates; C2 adds decisions through the same interface | C2 |
| Task B | J15 design and results (B3) | The comparison target of J16 | C3 |
| Existing tools | `tracker_resolution.py`, `multiple_scattering.py` | Tracking resolution at F0: C1 moves `curvature_sigma` and the scattering formulas to `core/physics/tracking.py`, so the scripts and F0 share one implementation (a subprocess per design costs too much) | C1 |

**Interfaces provided to other tasks:** the decisions, paired comparison, `values` and roles that C2.1 adds to `core/` are usable by any study (e.g. a convergence gate may declare paired mode).

---

## §C.3 Hard rules

All of §A.3 and §B.3 apply. In addition:

1. **The optimizer core uses only the standard library.** Sobol sequences, NSGA-II and (optionally) CMA-ES are implemented with the standard library. Bayesian optimization (Ax/BoTorch) is only an optional backend (C3), with tested versions recorded in `adapter.json`; the search still runs without it. The MOBO backend is loaded by lazy import (imported inside a function, falling back to NSGA-II on failure), the only exception to the standard-library rule.
2. **Adapters do not import each other.** detector-design calls `geant4_run.py` (`check-spec`, `run`, `reco`) as subprocesses, exchanging JSON files; shared Python code (including F0's tracking formulas) is imported only from `core/`.
3. **One production implementation per quantity.** C1 moves F0's tracking and multiple-scattering formulas to `core/physics/tracking.py`, and hep-detector's scripts call it; material constants come from the shipped material table (C1.4), not a separate copy.
4. **Declared in advance.** Requirements, catalogue version, grammar, search budget, optimizer settings and seeds are written into the search spec and hashed before the first evaluation. Any later change creates a new search version; old versions and their results stay in the record.
5. **Search values are not reported.** Search-stage objective values are used only for ranking; every externally reported performance number must cite confirmation runs.
6. **LLM proposals have no privilege.** Designs proposed by Claude are marked `proposer: llm` and go through the same validity checks and evaluation; Claude may not change evaluation outputs, nor change the requirements after seeing results without opening a new version.
7. **Cost and mass models are declared inputs.** The plugin ships only placeholder models marked `assumed`; real unit prices and mass models are supplied by the user with sources. Without a model, cost and mass are not used as objectives or constraints.
8. **Experiment names** appear only in `docs/` and example READMEs; the component catalogue uses generic names. The reference `detector-design-search.md` cites the studies of §C.4.1 only by citation key (e.g. `Cisbani2020`), without names such as EIC or ePIC (the experiment-name scan checks this).
9. **Do not change `skills/hep-detector/SKILL.md`**, unless the maintainer approves one routing line pointing to the reference (§P.7 item 12).
10. Contract rules are gated with `strict or _at_least(contract_version, CV3)`.

---

## §C.4 Design

### §C.4.1 Practice in the field and lessons

| Study | Approach | Lesson adopted here |
|---|---|---|
| EIC dRICH (Cisbani et al., JINST 15 (2020) P05009) | 8 parameters; objective π/K separation (harmonic mean at two momenta); Geant4 with 2.5 % noise; Gaussian-process Bayesian optimization, 20 designs in parallel per call, converging after about 55 calls; better than the original design (3.23 vs 2.9); tolerance intervals from the posterior (numbers to be verified against the paper) | Model the noise explicitly; parallel batches; tolerance and parameter-correlation analysis from the posterior; results "simulation only", prototype validation needed |
| AID(2)E (ePIC, arXiv:2405.16279) | Multi-objective Bayesian optimization (qNEHVI, Ax/BoTorch) and NSGA-II; dRICH with 7 parameters, 200 evaluations, converging after 150; closure test on DTLZ2 with a known Pareto front; distributed execution with PanDA | Multiple objectives and Pareto; MOBO for ≤ 4 objectives, genetic algorithms for more or for discontinuities; closure tests first; geometry constraints (overlap, envelope) checked before simulation |
| MODE (arXiv:2203.13818, 2310.05673) | End-to-end differentiable optimization; differentiable surrogates replace non-differentiable simulation; utility includes physics goals and cost | Align with experiment goals through one utility or a Pareto front, not per-subsystem optimization; surrogates can steer designs into bias and must be confirmed with full simulation |
| AIDO diffusion-model calorimeter (arXiv:2502.02152) | 6-layer sampling calorimeter, 12 parameters (thickness and material; numbers to be verified against the paper); material as a softmax categorical; cost and length caps; the result reproduces known calorimeter principles | Categorical choices (materials) and cost constraints can be part of the search; "reproducing known principles" is a reasonable first acceptance |
| ECAL longitudinal structure (Borysov et al., EPJ Web Conf. 315, 03006) | Semi-analytic model (checked against Geant4) + genetic algorithm with non-dominated sorting | Screen with an analytic model, check with Geant4: the F0 → F2 multi-fidelity |
| SWGO array layout (arXiv:2310.01857) | Differentiable optimization of the positions of order 10³–10⁴ units; utility = flux precision + energy resolution + pointing resolution + area cost | The utility's weights are a declared choice; some derivative terms dominate and push designs to extremes, and need checking |
| GRACE (arXiv:2602.15039) | An LLM agent builds simulations from natural language or papers and explores design variants; physics verifier and provenance | Geometry often needed several regenerations to match the spec and should be validated before simulation; the agent noticed anomalies but did not follow them up; cost and engineering constraints ignored |
| VI-BRATO (arXiv:2604.21804) | An LLM agent directs a two-level DD4hep/Geant4 scan of geometry and digitization, reaching the optimum of a 2255-point grid in 46 runs | Agents are good at decomposing problems and steering scans; but conclusions need independent checks, and experts are still needed for realizability |

Summary: in no real case does the LLM declare "the best" by itself; successful approaches all have "explicit objectives and constraints + reproducible evaluation + a recorded optimizer + confirmation with full simulation". The LLM's value lies in turning requirements into a search problem, proposing physically motivated starting points, decomposing the problem and following up anomalies.

### §C.4.2 Three roles

```
 User ──requirements──▶ Claude (designer) ──design brief, seed designs, search ranges──▶ Optimizer (recorded, reproducible)
                            ▲                                                              │ candidate designs
                            │ Pareto front, anomalies, trade-offs                          ▼
                            └──────────────── evaluation pipeline F0 → F1 → F2 → confirmation ◀──┘
```

| Role | May | May not |
|---|---|---|
| Claude (designer) | Turn the requirements into `detector-requirements/1` (confirmed with the user); choose candidate structure types from the catalogue; write 2–6 seed topologies with physics reasoning; set search ranges (within catalogue limits); decompose the problem (e.g. decide field and lever arm first, then the calorimeter); decide when to escalate fidelity; follow up anomalies; interpret the Pareto front and explain trade-offs to the user | Invent components outside the catalogue; skip validity checks; change evaluation outputs; report search-stage values; quietly change requirements after seeing results |
| Optimizer | Generate candidates in genome space; run per budget, seed and settings; record every evaluation | Decide whether requirements are met (that is the job of evaluation and statistics) |
| Evaluation pipeline | Realize designs, check validity, compute objectives and constraints at the requested fidelity, with SE | Behave differently depending on the proposer |

### §C.4.3 Requirements spec `detector-requirements/1`

Illustration (`//` marks comments, not part of the JSON):

```
{ "requirements_version": 1,
  "particles": [{"species": "proton", "rigidity_GV": [0.6, 1000]}, {"species": "electron", "energy_GeV": [1, 100]}],
  "objectives": [  // minimize or maximize; at most 4 enter the Pareto front, the rest are expressed as constraints
    {"name": "rigidity_resolution", "at": {"species": "proton", "rigidity_GV": 100}, "sense": "min"},
    {"name": "mass_kg", "sense": "min"} ],
  "constraints": [  // hard requirements: each with a threshold and direction
    {"name": "mdr_GV", "op": ">=", "value": 1000},
    {"name": "beta_resolution", "at": {"beta": 1}, "op": "<=", "value": 0.03},
    {"name": "acceptance_threshold_GV", "op": "<=", "value": 0.8},
    {"name": "calorimeter_depth_X0", "op": ">=", "value": 16},
    {"name": "upstream_material_X0", "op": "<=", "value": 0.15} ],
  "envelope": {"length_mm": 2000, "transverse_mm": [600, 600]},
  "environment": {"world_material": "G4_Galactic"},
  "cost_model": null, "mass_model": "catalogue-default",
  "tolerance": {"relative": 0.01},
  "provenance": {"elicited_by": "claude", "confirmed_by_user": true} }
```

- **Objective catalogue** (each objective declares how it is evaluated at each fidelity): rigidity resolution (at a given rigidity), MDR, β resolution, acceptance threshold rigidity, geometric factor (area × solid angle), calorimeter depth (X₀, λ_I), upstream material (X₀), energy resolution (F1/F2), e/p rejection (F2), total mass, total length, channel count, cost (with a model).
- Objective and constraint names must be in the catalogue; adding one needs a catalogue change and tests.
- Claude drafts the requirements from the user's description, but they must be confirmed by the user (`confirmed_by_user`) before the search starts.

### §C.4.4 Design grammar `detector-design/1` and component catalogue

**First component catalogue** (all realizable as `element_sim` box elements, at most one level of nesting):

| Component type | Parameters (type) | Realization | F0 model |
|---|---|---|---|
| `magnet-region` | B (continuous, T), length, aperture (continuous, mm) | Field-region mother (`field`), can hold tracker and TOF daughters | Bending; MDR; mass model (declared) |
| `tracker-plane` | Material (categorical), thickness, position resolution (bending/non-bending), size | `tracker-plane` element; resolution written into the reco spec | `tracker_resolution.py` (measurement term), `multiple_scattering.py` (scattering term) |
| `tof-layer` | Material, thickness, σ_t, size | `tof-layer` element | σβ/β = σ_t c / D (averaged over layers; §B.4.2) |
| `calorimeter-sampling` | Absorber material and thickness, active material and thickness, layer count (integer), transverse size | `calorimeter` mother + repeated sampling layers | X₀, λ_I, effective Molière radius; an energy-resolution parametrization for F0 ranking only, its source recorded through hep-citations |
| `calorimeter-homogeneous` | Material, length, transverse size | `calorimeter` mother + one active volume | X₀, λ_I |
| `passive` | Material, thickness, size | `passive` element | Material budget, multiple scattering |

**Composition rules (validity, checked before simulation):**
- Components form a sequence along the x axis; the sequence length and the count of each type have caps (declared in the search spec).
- No overlaps; everything inside the envelope; a minimum spacing between planes (declared).
- Daughters only in a `magnet-region` or `calorimeter` mother, with one level of nesting (the `element_sim` limit).
- Parameters within catalogue ranges; materials from the catalogue's material list.
- Structurally "unreasonable" combinations (e.g. requiring rigidity resolution without a field) are **not** forbidden by rules but naturally eliminated by objectives and constraints; rules handle only what is physically or programmatically impossible. This keeps the "free combination".

**Genome encoding:** a fixed number of slots, each with an "enabled" bit, a component type (categorical), a `parent_slot` (integer; −1 for top level, otherwise pointing to an enabled `magnet-region` or `calorimeter-*` slot, making this slot a daughter) and that type's parameters; disabled slots are not realized. Order follows the slots' x positions. This lets the genetic algorithm add and remove components and switch types.

**Repair and violation measure:** after crossover or mutation, repair in order: clip continuous and integer parameters to the catalogue ranges; set `parent_slot` to −1 when it points to a disabled slot or one that cannot be a mother; clip a daughter's position into its mother when it sticks out. Designs still invalid after repair are not repaired further and enter constrained domination with the violation v = Σ (normalized violation of each rule: overlap length / envelope length, length outside the envelope / envelope length, spacing shortfall / declared minimum spacing, number of daughters nested more than one level) (smaller v wins; objectives are compared only at v = 0).

**Realization:** `realize(design) → (element_sim.spec/1, reco spec)` is deterministic; design hash = sha256 of the normalized design JSON; the realized spec is validated with `geant4_run.py check-spec` (B1.6); after a run the geometry is checked with `tree-v1` (A2.4). Evaluations with the same design hash can be reused (cache); the cache key includes design hash, fidelity, catalogue version, program hash, and S, N, K, B (the same design in different seed_groups is a different evaluation). Duplicate designs in one search (same design hash, same fidelity and S) are evaluated once, and the search size counts distinct designs.

### §C.4.5 Multi-fidelity evaluation

| Fidelity | Method | Cost per design | Output | Use |
|---|---|---|---|---|
| F0 | Analytic formulas and existing tools (tracking measurement and scattering terms, material budget, helix geometry for acceptance, TOF formula, X₀ and λ_I) | Microseconds to milliseconds | Objective values (no statistical error, but model error) | Structure search; screening 10⁴–10⁶ designs |
| F1 | `element_sim` + `simreco`, about 10³ events per design, K = 16 | Minutes | Objective values ± SE (block batch means) | Refining continuous parameters of hundreds of designs; calibrating F0 |
| F2 | As F1, event count from A1.9's two-stage design; convergence gate (A1.8) and variations (rules of B3.4) | Hours | Objective values ± SE, decisions | Finalists |
| Confirmation | As F2, role `confirmation`, independent seeds | Hours | Reported performance and requirement decisions | The only reportable numbers |

- **The F0 vs F2 difference** is recorded for each finalist (`fidelity_gap`). If it exceeds the declared threshold, that objective is ranked by F2 only at the final selection, and the report explains the F0 model's limitation.
- Architecturally F0 and F1 belong to the surrogate class (B2.4): they never change the label.

### §C.4.6 Search strategy

| Step | Content | Default method | Budget (default, declarable) |
|---|---|---|---|
| S0 Design brief | Claude reads the requirements and writes candidate structure types, 2–6 seed topologies with physics reasoning, and a decomposition of the problem | Claude | — |
| S1 Structure search | Search the full genome (structure + parameters) at F0; initial population = seed topologies + Sobol random designs | NSGA-II (standard library) | population 200 × 100 generations = 2×10⁴ F0 evaluations |
| S2 Parameter refinement | Take the top K designs with **distinct topologies** (deduplicated by topology hash) and refine continuous parameters at F1; designs of one generation (including surviving parents, re-evaluated in that generation) share a seed_group (paired comparison, gate G-C2a) | NSGA-II or CMA-ES; from C3 optionally MOBO (qNEHVI), limited to ≤ 4 objectives and ≤ 20 parameters | K = 5, about 100 F1 evaluations each |
| S3 Final selection | The best design of each topology goes to F2; convergence gate, variations | — | ≤ 5 designs |
| S4 Confirmation | Confirmation runs of the finalists; requirement decisions; robustness | — | ≤ 5 designs |

- Stopping rule: budget exhausted, or hypervolume improves by less than the declared value over G consecutive generations. Hypervolume is computed exactly with the WFG algorithm in the normalized objective space (≤ 4 objectives); the reference point is declared in the search spec, by default each objective's declared threshold moved toward worse by a factor 1.1 (multiplied by 1.1 for minimized objectives, divided by 1.1 for maximized ones), and objectives without a threshold must declare a reference point. No budget increase based on results; more budget is a new search version.
- After S0, Claude may add new seed topologies (e.g. to follow up an anomaly), but these proposals are likewise marked `proposer: llm` and count toward the search size.

### §C.4.7 Statistical integrity

| Risk | Handling |
|---|---|
| Winner's curse | Search values only rank; reports come only from confirmation runs (role `confirmation`, S never used in the search); the recommended design is fixed from F2 before confirmation, confirmation only reports its performance, and there is no re-selection among finalists after seeing confirmation results (otherwise the confirmation results of all finalists must be reported with the selection bias explained); the report gives "search estimate − confirmation estimate" for each finalist as a diagnostic |
| Noisy constraints | Requirement decisions are made by the decision engine's `threshold` (C2.1), one-sided: for a "≤ threshold" requirement, met = estimate + t₀.₉₅·SE ≤ threshold; not met = estimate − t_{1−α/m}·SE > threshold; otherwise unresolved (m = finalists × requirements). Exact intervals for low counts |
| Claiming dominance in noise | Ordering among finalists is decided by `order` (C2.1), claimed only when the two-sided t_{1−α/(2m)} bound of the difference excludes 0 (m = finalist pairs × objectives); the report gives "the statistically non-dominated set" |
| Ranking noise | Designs of one generation in S2 share a seed_group (paired comparison), so differences vary less; confirmation runs do not share one and stay independent |
| Search size | The record gives the number of designs evaluated at each fidelity, the number of topologies, optimizer settings and seeds |
| Exploiting simulation defects | Finalists must pass the convergence gate for their relevant parameters (production cut, maximum step, field accuracy); physics-model variations (rules of B3.4); designs in materials or energy regions outside every reference benchmark's scope are flagged in the report (the label is `unvalidated` anyway; this is information for the reader) |
| Robustness | Continuous parameters are perturbed within the requirements' `tolerance` and the catalogue's manufacturing tolerances, exploring the performance distribution with F0 full factorial or F1 sampling to find the worst point within tolerance; "robustly met" is decided only on confirmation-fidelity runs (the worst point rerun with role `confirmation` and F2 event counts), and results are classed as "robustly met" or "nominally met" |
| Changing requirements | Any change to requirements or budget is a new search version; the report lists all versions |

### §C.4.8 Records and contracts (CV3)

A search record is a computational-run with `extension.design_search`:

```
{ "requirements_sha256": "...", "catalogue_version": "1", "catalogue_sha256": "...",
  "search_spec_sha256": "...", "search_version": 1, "previous_versions": [],
  "optimizer": {"name": "nsga2", "implementation": "detector-design 0.2.0", "backend": null, "seed": 12345, "config": {...}},
  "budgets": {"F0": 20000, "F1": 500, "F2": 5, "confirmation": 5},
  "evaluated": {"F0": 20000, "F1": 487, "F2": 5, "topologies": 143},
  "evaluations_ref": {"path": "...", "sha256": "..."},
  "proposals": [{"design_sha256": "...", "proposer": "llm", "rationale": "..."}],
  "pareto_set": ["<design_sha256>", ...],
  "finalists": [{"design_sha256": "...", "spec_sha256": "...", "confirmation_runs": ["..."],
                 "requirements": [{"name": "mdr_GV", "verdict": "met|not-met|unresolved", "robust": true}],
                 "fidelity_gap": {...}, "search_minus_confirmation": {...}}],
  "label": "unvalidated" }
```

The rules are in C2.6. C1 records carry only the F0 fields and are marked `fidelity: F0-only`. C1 writes `extension.design_search` before CV3: the envelope schema only requires `extension` to be an object (`contracts/schemas/envelope.json`) and does not restrict its keys, so C1 records are accepted before CV3; after CV3 they are checked by the rules of C2.6.

---

## §C.5 Stage C1: requirements, grammar and fast search (detector-design 0.1.0)

### C1.1 Schemas

`detector-requirements/1`, `detector-design/1`, `catalogue/1`, `design-search-spec/1` (requirements hash, catalogue version, slot count and caps, budget, optimizer settings, seed, stopping rule), in `adapters/detector-design/assets/schemas/`, using only keywords supported by `contracts/schema.py`; cross-field rules checked in Python. Before A2 (A2.7) merges, the schemas do not use `maxItems`, `maximum`, `exclusiveMaximum`; sequence lengths, count caps and parameter upper bounds are checked in Python; after A2 merges they may move into the schemas, with the Python checks kept as tests.

### C1.2 First component catalogue

The six components of §C.4.4; each with parameter ranges, material list (NIST names), manufacturing tolerances, mass model (density × volume; magnet mass is a declared placeholder model marked `assumed`), F0 model and realization rule. Each catalogue entry has unit tests (realized geometry, material budget).

### C1.3 Realization and validity

`design_search.py realize`: design → `element_sim.spec/1` and reco spec; no Geant4 needed. Invalid designs return the reason (overlap, outside envelope, nesting, range), exit 2.

- C1 uses detector-design's own validity rules and the draft of `element_sim.spec/1` (the table of B1.1); C1 may merge before B1.
- C2 (B1 is then certainly merged): add a test that calls `geant4_run.py check-spec` as a subprocess to validate the realization of every catalogue component type (C2.9).

### C1.4 F0 evaluation

`design_search.py evaluate --fidelity F0`, computed in one process:
- **Tracking:** `curvature_sigma` (measurement term) and the scattering term from `core/physics/tracking.py`. C1 moves them from `tracker_resolution.py` to `core/` (with a steward), `tracker_resolution.py` and `multiple_scattering.py` call `core/`, and the existing tests confirm unchanged output. The scattering constant follows `tracker_resolution.py`'s convention: the scattering term of the curvature fit uses PDG's 0.016 GeV/c (`PDG_MS`, no log correction), and the Highland version (13.6 MeV, `HIGHLAND`) is output as well; the constant used is written into `model`. The measurement-term formula assumes all planes are in the uniform field; for designs with planes outside the `magnet-region`, the curvature uses only the planes inside the field, the design is marked `model: planes-outside-field`, and its `fidelity_gap` is listed separately in the report.
- **Materials:** material budget, X₀ and λ_I from the shipped material table `catalogue/materials.json` (density, X₀, λ_I of each catalogue material; generated from a dump of Geant4 NIST materials, with the Geant4 version and generating command in the file header; or taken from PDG and recorded through hep-citations). F0 does not call Geant4 at run time; a test checks the table against the same dump (`geant4_verify.py` line 132 uses the dump's `radiation_length_cm`).
- **Acceptance threshold rigidity:** the lowest rigidity that, starting in the declared incidence direction (default normal incidence) in the uniform field, still crosses every required plane (helix and box boundaries; the same formula as §B Appendix A).
- **Geometric factor:** the analytic formula for a telescope of two parallel rectangular planes (Sullivan 1971, recorded through hep-citations) formed by the first and last required planes (by default the outermost two tracker planes), ignoring field deflection; this approximation is written into `model`.
- **TOF:** from the formula of §B.4.2.

Each objective carries a `model` field describing the approximation.

### C1.5 Optimizer

`design_search.py search`: Sobol initialization (Joe–Kuo direction numbers, with a table for the needed dimensions shipped), NSGA-II (simulated binary crossover η_c = 15 and polynomial mutation η_m = 20 for continuous and integer genes, integers rounded after mutation; uniform crossover and random reset for categorical genes and `parent_slot`; bit flips for slot-enabled bits); then repair per §C.4.4, with constraints through constrained domination on the violation measure. Distribution indices and mutation probabilities are written into the search spec. Standard-library implementation; the same seed gives bit-identical results.

### C1.6 Search record and report

`design_search.py report`: Pareto front, best design per topology, search size, F0 model limitations; outputs the record (§C.4.8, `fidelity: F0-only`) and a Markdown summary for the user. C1 results are clearly marked "based on analytic models only".

### C1.7 Agent protocol and docs

- `skills/hep-detector/references/detector-design-search.md`: the roles and limits of §C.4.2, the requirement-confirmation flow, the format of the design brief, when to escalate fidelity, how to report (must state search size, confirmation status and robustness).
- The reference cites studies only by citation key (§C.3 rule 8).
- Adapter docs; a detector-design row in `docs/capability-matrix.md`.
- Routing: per the decision on §P.7 item 12, either one line in `SKILL.md` pointing to the reference, or only routing cases and the reference.

### C1.8 Closure tests

| Test | Known answer | Pass condition |
|---|---|---|
| DTLZ2 (3 objectives, known Pareto front) | The analytic front | Hypervolume reaches ≥ 95 % of the true value within 2×10⁴ evaluations (the closure-test practice of AID(2)E) |
| Plane placement (N = 6, fixed lever arm L, measurement term only, declared minimum spacing L/32) | Best A = 47.66: exhaustive enumeration on the 1/32 grid, and a local search without the grid gives the same value (66.96 for equal spacing; §C Appendix A) | The optimizer finds a configuration with A ≤ 47.66 × 1.01 under minimum spacing L/32 |
| Structure choice (requirement MDR ≥ 1 TV, given envelope and mass cap) | Must choose a topology with a `magnet-region` and ≥ 3 `tracker-plane`s; all field-free topologies are infeasible | Every feasible Pareto design contains a magnet region and tracker planes; B·L² agrees with the analytic formula |
| Calorimeter depth (requirement ≥ 16 X₀, length cap) | Among the absorber materials, high-Z absorbers give the shortest length | The chosen absorber agrees with the analytic ordering |
| Reproducibility | — | Same search spec and seed: the records of two executions are bit-identical (except timestamps) |

### C1.9 C1 acceptance

- [ ] Tests of the four schemas and the cross-field rules; every kind of invalid-design reason has a test.
- [ ] Realization tests for the six catalogue components; before A2 merges the schemas do not use `maxItems`, `maximum`, `exclusiveMaximum`, and the corresponding Python checks have tests.
- [ ] Every F0 objective agrees with the existing tools or the analytic values of the appendix.
- [ ] All closure tests of C1.8 pass (gate G-C1; do not merge otherwise).
- [ ] Unit tests of `core/physics/tracking.py`; the existing tests of `tracker_resolution.py` and `multiple_scattering.py` pass unchanged; `materials.json` agrees with the Geant4 dump.
- [ ] An independent agent, following the agent protocol, completes from a natural-language requirement: requirement confirmation (a test plays the user), design brief, F0 search, report; the report says "based on analytic models only" and lists the search size.
- [ ] `check_layering.py` (detector-design imports only `core` and `contracts`) and `check_packaging.py` pass.
- [ ] VALIDATION DESIGN-SEARCH-F0; CHANGELOG; release manifest.

---

## §C.6 Stage C2: simulation evaluation and confirmation (detector-design 0.2.0, geant4 adapter 0.5.0, contracts CV3)

### C2.1 Additions to `core/` and the contracts

Following principles R1 and R2 of §P.2 (additions only, no change to existing behaviour):

| Addition | Location | Content |
|---|---|---|
| `threshold(est, se, ν, op, value, m)` | `core/stats/decisions.py` | met / not-met / unresolved; met = the one-sided 95 % bound satisfies the threshold; not met = the one-sided 1 − α/m bound violates it; exact-interval branch |
| `order(diff, se, ν, m)` | Same | better / worse / indistinct; better or worse claimed only when the two-sided t_{1−α/(2m)}(ν) bound of the difference excludes 0; m = finalist pairs × objectives |
| Paired mode | Same (`equivalence`, `change` and `order` all accept `pairing: paired`) | Both points belong to one seed_group, with the same K and B; `absolute`: per-block differences d_b = θ_a,b − θ_b,b, diff = d̄, se_diff = sd(d_b)/√K. `relative`: for each bound r to be checked (±tol for TOST, tol for `change`, 0 for `order`) form z_b = (θ_a,b − (1+r)θ_b,b)/b̄ (b̄ the block mean of point b), and test z̄ against 0 one-sided with sd(z_b)/√K (Fieller type; the uncertainty of b̄ need not be ignored). ν = K − 1; the se target is se ≤ tol/4 at r = 0. The default stays `independent` |
| `values` accumulator | `core/simulation/summary.py` and schema (minor increase of `summary_version`); `core/stats/batch_means.py` | Each block's raw selected values (sorted by event number); `values_max` (from the observable declaration, default 10⁴) is a per-block cap: a block's values are written when its `n` ≤ `values_max`, and if any block exceeds it the observable does not use empirical quantiles and this is noted; `merge` rule `concat`; with `values`, quantiles are empirical (Hyndman–Fan type 7, recorded as `quantile_method`). Reason: resolutions differ widely between designs, and no fixed binning suits every design |
| C++ implementation of `values` | `g4sim/SimSummary.hh`; written by `element_sim` and `simreco` | Agrees with the Python producer (the method of A2.9) |
| Roles | `contracts/`, schemas of the study spec and the search spec | Add `confirmation` (evidence role) and `search-F1`, `search-F2` (search roles); runs with a search role are never evidence for any upgrade or report |
| seed_group | `core/simulation/seeds.py`; `contracts/` | F1: runs of one seed_group share S = H(search_id, role, seed_group); F2 and confirmation do not share: S = H(search_id, role, design_sha256). Runs of one seed_group have the same K, B and `seeding`, and mutually different spec hashes; uniqueness becomes "(S, spec hash) does not repeat; S repeats only within a declared seed_group"; the S of an evidence role must not equal the S of any search role |

### C2.2 F1 and F2 evaluation

`design_search.py evaluate --fidelity F1|F2`: realization → `geant4_run.py run` (`element_sim`) → `geant4_run.py reco` (`simreco`) → summary; each design evaluation is a logical run, point_id = design hash, role `search-F1` or `search-F2`. Event counts: F1 fixed (declared), F2 per A1.9. Batches run through the existing partition and batch machinery (hep-computing), cached with the cache key of §C.4.4. Surviving parents are re-evaluated in each generation's seed_group, so every comparison within a generation is paired; a re-evaluation is a new evaluation (different S, no cache hit) and counts toward the F1 budget.

### C2.3 Paired comparison in the search

- Each generation of S2 declares a seed_group; designs of one generation share S, and ranking uses `order` in paired mode.
- **Gate G-C2a:** in the trial of the first search, measure the variance ratio of differences Var(independent) / Var(paired); if the ratio is below the declared value (default 2), S2 uses independent comparison instead, noted in the record. The paired estimate is valid at any degree of correlation; only the gain may be small (in Geant4 different designs soon consume different random numbers).

### C2.4 Confirmation and requirement decisions

`design_search.py confirm`: confirmation runs of the finalists (role `confirmation`, S in no search evaluation); the one-sided requirement decisions of §C.4.7 (`threshold`); ordering among finalists (`order`, independent mode); `search_minus_confirmation` and `fidelity_gap`. The recommended design is fixed from F2 before confirmation and written into the record (§C.4.7).

### C2.5 Guards and robustness

Convergence gate of the finalists (production cut, maximum step, field accuracy; A1.8); variations (rules of B3.4); tolerance perturbations; flags for regions outside benchmark scopes (decided with the scope comparison exported by `contracts/validate.py`).

### C2.6 Contracts CV3

- The label of a search record must be `unvalidated`.
- Each finalist's `confirmation_runs` must exist with role `confirmation`, their spec hash must equal the design's realization, and their seed S must not appear in any search evaluation listed in `evaluations_ref` (re-derived by `dependencies.py`).
- Tables or communications derived from a search record must take their numbers from confirmation runs; citing search-stage values is rejected.
- A communication using search results gets the `communication.simulation_optimized_design` warning.
- The role and seed_group rules of C2.1.
- Gated with `strict or _at_least(contract_version, CV3)`; needs hep-computing's agreement to `extension.design_search` (§P.7 item 13).

### C2.7 Adapter changes

| Item | Content |
|---|---|
| detector-design | 0.1.0 → 0.2.0: `evaluate --fidelity F1|F2`, `confirm`; the search spec references `simulation-observables/1`; `adapter.json` and docs |
| geant4 adapter | 0.4.0 → 0.5.0: `values` in `SimSummary.hh`; `element_sim` and `simreco` write `values` per the observable declaration; `SIM_SOURCES` structure unchanged |
| G5 | New C++ changes written from the Geant4 API; the reviewer confirms in the VALIDATION entry |

### C2.8 Compute budget

F0 for 2×10⁴ designs: minutes; F1 about 500 × 10³ events; F2 and confirmation ≤ 5 designs each, event counts per A1.9; calorimeter showers dominate CPU. The actual budget is written into the search spec after a trial.

### C2.9 C2 acceptance

- [ ] `threshold` toys: probability of met when the true value equals the threshold ≤ 0.05 + 3σ_MC; `order` toys: probability of claiming an ordering when the true difference is 0 ≤ α/m + 3σ_MC.
- [ ] Paired-mode toys: coverage of the nominal 90 % interval from se_diff satisfies |coverage − 0.90| ≤ 0.02 + 3σ_MC; the variance ratio measured in the trial is recorded (gate G-C2a).
- [ ] `values` accumulator: Python and `SimSummary.hh` agree; above `values_max` it is omitted and noted; empirical quantiles have unit tests; old summaries (without `values`) are still readable.
- [ ] The realization of every catalogue component passes `geant4_run.py check-spec` as a subprocess (C1.3).
- [ ] `order` uses the two-sided t_{1−α/(2m)}; toys of the paired `relative` mode: probability of rejecting when the true relative difference equals r ≤ 0.05 + 3σ_MC.
- [ ] Contract tests of roles and seed_group: a search role listed as evidence is rejected; an S repeated outside a seed_group, or equal spec hashes within one seed_group, are rejected; a confirmation run whose S equals that of a search run is rejected.
- [ ] F1 and F2 summaries pass task A's consistency tests; the evaluation cache is keyed by design hash, fidelity, catalogue version, program hash and S, N, K, B; duplicate designs are evaluated once; surviving parents are re-evaluated in each generation.
- [ ] CV3 contract tests: a table citing search values is rejected; a search record whose label is not `unvalidated` is rejected.
- [ ] Winner's-curse toys: on a set of pure-noise designs, the search estimate is significantly optimistic while the confirmation estimate is unbiased (gate G-C2b).
- [ ] A complete small search (e.g. the structure-choice problem of C1.8, evaluated at F1/F2) runs S0–S4, with a report containing search size, confirmation decisions and robustness.
- [ ] J14 still passes under `--strict`; so does J15 if B3 is merged.
- [ ] VALIDATION DESIGN-SEARCH; CHANGELOG; release manifest; the checks of §A.8.

---

## §C.7 Stage C3: example (detector-design 0.3.0)

### C3.1 J16: automated-design example

- Requirements: taken from J15's design goals (MDR ≥ 1 TV, σβ/β ≤ 3 %, acceptance threshold ≤ 0.8 GV, calorimeter ≥ 16 X₀, upstream material ≤ 15 % X₀, length ≤ 2 m, a declared mass model); J15's geometry is **not** given.
- Run S0–S4; the report compares the search result with J15 (the results of B3): whether a J15-type topology was found, on which objectives it is better or worse, and why (e.g. clustering planes at the ends and centre raises the MDR but worsens resolution where multiple scattering dominates; §C appendix A).
- Like J15 it is a synthetic study; the README says it demonstrates the process, not a new detector design (the same positioning as the AIDO and SWGO studies).

### C3.2 Optional MOBO backend

Ax/BoTorch (qNEHVI), used only in S2, limited to ≤ 4 objectives and ≤ 20 continuous parameters; version recorded in the record and in `adapter.json` (whether it is listed as a tested tool: §P.7 item 14); without it, fall back to NSGA-II and note it in the record. The two are compared on the DTLZ2 closure test.

### C3.3 Registration and docs

`docs/researcher-journeys.md` (J16), routing case (reusing the trigger words "design principles and trade-offs" already in hep-detector's description; `check_routing_static.py` requires a routing case for every journey in the table), `tests/examples/test_detector_design_j16.py` (replay and compare decisions), capability map, capability matrix, adapter docs, protocol; this task's Markdown reviewed with `review.py` (advisory).

### C3.4 C3 acceptance

- [ ] J16 completed, with a report containing search size, confirmation decisions, robustness and the comparison with J15 (gate G-C3).
- [ ] J16's offline replay (from the committed records and summaries) gives the same decisions.
- [ ] MOBO backend (if installed) passes the DTLZ2 closure test; without it, fallback noted.
- [ ] Registration and docs done; the routing case passes.
- [ ] VALIDATION DESIGN-SEARCH-J16; CHANGELOG; release manifest; the checks of §A.8.

---

## §C.8 Contracts and versions

| Object | Location | Version |
|---|---|---|
| `detector-requirements/1`, `detector-design/1`, `catalogue/1`, `design-search-spec/1`, F0, optimizer | `adapters/detector-design/` | detector-design 0.1.0 (C1) |
| F1, F2, confirmation | `adapters/detector-design/` | detector-design 0.2.0 (C2) |
| `threshold`, `order`, paired mode, `values`, seed_group | `core/` | with the plugin version (C2); minor increase of the summary schema's `summary_version` |
| C++ implementation of `values` | geant4 adapter | 0.5.0 (C2) |
| Roles, seed_group rules, `extension.design_search` and its rules | `contracts/validate.py`, `contracts/dependencies.py` | CV3 (minor, gated; C2) |
| MOBO backend, J16 | `adapters/detector-design/`, `examples/` | detector-design 0.3.0 (C3) |
| Agent protocol | `skills/hep-detector/references/detector-design-search.md` | with the plugin version |

---

## §C.9 Not done and deferred

| Item | Decision | Reason / trigger |
|---|---|---|
| Letting an LLM alone decide the best design | Not done | No real case does this; decisions must be reproducible |
| Inventing component types during a search | Not done | New components need a realization rule, F0 model and tests; added through a catalogue change |
| Differentiable simulation and differentiable surrogates (the MODE route) | Deferred | Geant4 is not differentiable; differentiable surrogates at point-cloud scale are still immature (arXiv:2310.05673). Trigger: a problem with > 20 continuous parameters and an insufficient F1 budget |
| Cylindrical and non-box geometry, collider detectors | Deferred | `element_sim` has only box elements. Trigger: `element_sim` gains cylindrical elements (§B.9) |
| Cherenkov, RICH, TRD | Deferred | Need optical physics and dedicated reconstruction |
| Reinforcement learning, large neural-network surrogates | Deferred | Data volume and interpretability; NSGA-II and MOBO suffice for up to a few dozen parameters |
| A real cost database | Not shipped | Supplied by the user with sources |

---

## §C.10 Open decisions and residual risks

**Open decisions** (numbered as in §P.7): item 11 (maintenance ownership of detector-design), item 12 (the routing line in `SKILL.md`), item 13 (CV3 and `extension.design_search`), item 14 (MOBO backend).

**Residual risks:**
1. Bias of the F0 models may make the structure search miss good topologies; mitigated by topology diversity in S2 and `fidelity_gap`, but not excluded.
2. Simulation-optimized designs may exploit Geant4 behaviour in unvalidated regions; the convergence gate and variations only partly guard against this, and the label stays `unvalidated`.
3. The placeholder mass and cost models are crude; without a user model they should not be objectives.
4. With more than 4 objectives the Pareto front is hard to read; requirements should express the rest as constraints.
5. Claude's design brief may bring in a bias toward "known instruments"; offset by Sobol random designs and topology diversity, and the report separates the contributions of LLM and random proposals.
6. The variance reduction of paired comparisons in Geant4 may be small (gate G-C2a).
7. Compute: F1 and F2 evaluations with calorimeters are expensive; budgets are adjusted after a trial.
8. Among this part's references, GRACE and VI-BRATO are 2026 preprints whose conclusions are not yet peer reviewed.

---

## §C.11 Suggested order of work

At the start of each stage, create and confirm that stage's isolated worktree per §P.10.2 and do every step in it; remove it per §P.10.5 after merging.

**C1 (after A1 is merged; may run in parallel with A2 and B)**
1. Pre-start checks; schemas (C1.1) and catalogue (C1.2).
2. Realization and validity (C1.3); F0 (C1.4), checked against the existing tools.
3. Optimizer (C1.5) and the DTLZ2 and plane-placement closure tests.
4. Record and report (C1.6); agent protocol and docs (C1.7); the remaining closure tests and the independent-agent acceptance; C1.9.

**C2 (after B2 and C1 are merged)**
1. Additions to `core/` and the contracts (C2.1), with their toys and contract tests.
2. F1 and F2 (C2.2); paired-comparison trial (C2.3); confirmation and requirement decisions (C2.4).
3. Guards and robustness (C2.5); CV3 (C2.6); adapter changes (C2.7); C2.9.

**C3 (after B3 and C2 are merged)**
1. J16 (C3.1); optional MOBO (C3.2).
2. Registration and docs (C3.3); C3.4.

---

## §C Appendix A: Numbers

**Plane-placement closure test** (curvature variance σ_k² = A σ² / L⁴, N = 6, equal weights, measurement term only; exact rational least squares; computed by `design_search_closure.py` in this folder):

| Configuration | A | MDR relative to equal spacing |
|---|---|---|
| Equal spacing (J15) | 66.96 | 1 |
| Two planes each at both ends and the centre (coincident) | 48.00 | 1.181 |
| 2/3/1 planes clustered at 0, 1/2, 1 (coincident) | 45.33 | 1.215 |
| 2/3/1 planes clustered, middle cluster moved to 0.465 (best of a 1/1000 scan) | 44.77 | 1.223 |
| Best by exhaustive enumeration on a 1/16 lever-arm grid (distinct planes, minimum spacing L/16) | 50.34 (0, 3/8, 7/16, 1/2, 9/16, 1) | 1.153 |
| Best by exhaustive enumeration on a 1/32 lever-arm grid (minimum spacing L/32; the closure-test answer) | 47.66 (0, 1/32, 7/16, 15/32, 1/2, 1) | 1.185 |
| Asymptotic large-N limit (N/4, N/2, N/4 clustered at 0, 1/2, 1; not reachable with integer plane counts at N = 6) | 256/N = 42.67 | 1.253 |

Coincident clusters violate any minimum spacing, so they are not the closure-test answer and only show the trend. J15's MDR of 1172 GV becomes about 1389 GV with the best 1/32-grid configuration; but clustered configurations are worse where multiple scattering dominates, which is exactly the trade-off J16 asks the optimizer to handle.

## §C Appendix B: Sources

- E. Cisbani et al., "AI-optimized detector design for the future Electron-Ion Collider: the dual-radiator RICH case", JINST 15 (2020) P05009, [arXiv:1911.05797](https://arxiv.org/abs/1911.05797)
- AID(2)E collaboration, "AI-Assisted Detector Design for the EIC (AID(2)E)", [arXiv:2405.16279](https://arxiv.org/abs/2405.16279)
- MODE collaboration, "Toward the end-to-end optimization of particle physics instruments with differentiable programming", [arXiv:2203.13818](https://arxiv.org/abs/2203.13818); "Progress in end-to-end optimization of detectors for fundamental physics with differentiable programming", [arXiv:2310.05673](https://arxiv.org/abs/2310.05673)
- Schmidt et al. (MODE), "End-to-end detector optimization with diffusion models: a case study in sampling calorimeters", [arXiv:2502.02152](https://arxiv.org/abs/2502.02152)
- O. Borysov et al., "Longitudinal structure optimization for a high density electromagnetic calorimeter", [EPJ Web Conf. 315, 03006 (2024)](https://www.epj-conferences.org/10.1051/epjconf/202431503006)
- T. Dorigo et al., "Toward the end-to-end optimization of the SWGO array layout", [arXiv:2310.01857](https://arxiv.org/abs/2310.01857)
- J. Hill, H. J. Ryoo, "GRACE: an agentic AI for particle physics experiment design and simulation", [arXiv:2602.15039](https://arxiv.org/abs/2602.15039) (preprint)
- W. Chung et al., "Agentic-AI detector co-design and optimization in vertically-integrated differentiable full simulations", [arXiv:2604.21804](https://arxiv.org/abs/2604.21804) (preprint)
- Retrieved 2026-10-23; authors and journal details to be checked through hep-citations before citing

## §C Appendix C: Version history

| Version | Content |
|---|---|
| 2026-10-23 | First proposal: three roles, requirements spec, component catalogue and design grammar, F0/F1/F2 multi-fidelity, search separated from confirmation, contracts, C1/C2, J16; later updated to use the shared `core/` modules after the re-examination of task A |
| **2026-10-23 (this version)** | **Reorganized per the plan (Part 1): three stages (C1 after A1, C2 after B2 and C1, C3 after B3 and C2); the `threshold`, `order`, paired comparison, `values`, search roles and seed_group that task C needs are added to `core/` and the contracts by C2.1 itself; realizations validated with `geant4_run.py check-spec`; contract version written CV3; J16 and MOBO moved to C3; section numbering aligned with tasks A and B** |
| 2026-10-23 | Added the isolated-worktree execution rule: header, the first step of §C.0, the start of §C.11 (§P.10) |
| 2026-10-23 | Fixes after the detailed check: schema-keyword limit before A2; check-spec test moved to C2; two-sided bound and m of `order`; paired `relative` mode uses z_b; cache key includes S, N, K, B; parents re-evaluated each generation; S of F1 versus F2/confirmation; design deduplication; recommended design fixed from F2; shipped material table; tracking formulas moved to `core/`, scattering constant and planes outside the field; genome `parent_slot`, repair, violation measure, SBX/PM indices, Joe–Kuo, hypervolume; acceptance and geometric factor; minimum spacing and new configurations of the closure test; robustness decided at confirmation fidelity; citation keys; lazy import of MOBO; `values_max` per block; literature numbers to be verified |

---

# Part 5 — Design rationale (§R)

> Baseline: hep-research `main` at `9f08796` (0.23.0 plus unreleased changes), contracts 3.5.0, adapter geant4 0.1.0, Geant4 11.4.3
> Date: 2026-10-22 (corrected 2026-10-23 after the detailed check)
> Note: this part was written before the 2026-10-23 re-plan (task C, eight stages, the `core/` modules) and has only received the necessary pointers. Stages, versions, interfaces and acceptance follow Parts 1–4; where they conflict, Parts 1–4 win and the conflict is reported.

---

## §R.0 Summary

**Purpose.** Make simulation studies in hep-research (Geant4 today) achieve three things: results cannot be wrongly labelled `validated-in-scope`; numbers and decisions are reproducible and traceable; the study layer is not tied to one simulation program, one geometry or one kind of study.

**Starting point.** Large experiments have solved the same problems at a much larger scale. This architecture takes only practices that have stood the test of time and are feasible under the plugin's constraints (standard-library Python, separate executables exchanging JSON/CSV, minimal change):

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

- Python uses only the standard library.
- G5 licence boundary: Python exchanges only JSON and CSV with separate executables; no Geant4 example code is copied.
- Layering: skill scripts and adapters import only `core` and `contracts`; code both need (statistics, decisions, seed hashing, summary reading) therefore lives in `core/stats/` and `core/simulation/` (§A.3 rule 1, §A.4.5); no experiment names in `skills/` or `contracts/` (experiment names may appear in `docs/` and `examples/`).
- Statuses and exit codes (`core/status.py`): 0 ok, 1 a negative verdict, 2 `rejected`, 3 `incomplete`.
- Files ≤ 2 MiB; hep-detector quick load ≤ 25,600 bytes (24,669 now), description ≤ 1,024 characters (`measure_entrypoints.py` reports 1,016). `SKILL.md` and the description are not changed; the only exception is the one-line route pending as §P.7 item 12 (C1).
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
  hep-detector      rules, reference formulas, inference (batch means, exact intervals, MPV, IUT, negative controls, distribution comparison), decisions, labels
  adapters/geant4   spec validation, build, run, job splitting, records (trace.provenance()), simulated tables;
                    produces run summaries from per-event CSVs in A1 (only as the oracle in tests from A2)
  adapters/detector-design  (task C) requirements, component catalogue, realization, search and confirmation
  core              trace, status; stats/ (block estimators, exact intervals, decision engine, distributions);
                    simulation/ (seed hash, summary and observable schemas and reading)
  contracts         validation-class and grade table, scope, configuration and isolation (CV1); new classes,
                    transitive processing chains (CV2); extension.design_search (CV3)
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
| contracts | Python | A1 (CV1), B2 (CV2), C2 (CV3) | — |
| inference and decisions (`core/stats/`, `core/simulation/`) | Python | A1; additions in B2, C2 | — |
| `detector-design` adapter | Python | C1–C3 | `core`, `contracts`; calls the geant4 adapter |
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
| model-to-model (surrogate) | a full simulation such as Geant4, as the reference for fast simulation or an ML surrogate | a parametrized calorimeter against Geant4 | IUT or χ² | cannot upgrade physics labels; the surrogate itself may get a "consistent with the reference simulation in scope" mark |

There are also `sanity` (a rough plausibility check) and `interface` (an interface check); neither can upgrade.

### §R.6.2 Benchmark table (CV1, extended in CV2)

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
| added in CV2: J15's checks (`field-propagation` and others) | verification or sanity | — | — |
| added in CV2: `regression-comparison` | regression | — | — |
| added in CV2: `surrogate-comparison` | surrogate | — | — |

The scope of `regression-comparison` and `surrogate-comparison` is the intersection of the two compared studies' scopes, re-derived by `dependencies.py` (the CV2 table of §B governs).

A record whose class or grade disagrees with the table, or whose name is not in it, is an error. `GRADES` in `geant4_benchmarks.py` stays for the tool, with a consistency test.

### §R.6.3 Scope (CV1)

- Compare the controlled `observable.kind`; `label` writes it into `declared_scope.observable_kind`.
- The dimension list is declared per benchmark (fourth column of 6.2), each dimension typed: categorical or a numeric range; a scalar is [v, v]. A new use case adds dimensions by changing the table only.
- A declared scope missing a dimension the benchmark has is outside.
- With a target-hash dimension, the declared scope must carry the same `target_geometry_sha256` and `hash_scheme`.
- Gating: `strict or _at_least(contract_version, CV1)`, no warning branch.

### §R.6.4 Configuration and isolation (CV1)

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

### §R.6.5 Regression and model-to-model (CV2)

- **Regression:** the same study with the same settings runs once on each of two versions (plugin, backend or Geant4) (point_id is the version tag, so the samples are independent), and every scalar observable is compared. Three outcomes: `changed` (|diff| − t_{1−α/m}·se_diff > tol), `unchanged` (the pass rule of §R.6.6), `unresolved`; "not significant" does not mean "unchanged". Histogram comparison is deferred to distribution-level benchmarks. Labels are not affected; a reference observable marked `changed` can trigger a sci-fix check.
- **Model-to-model:** a surrogate never changes the physics label. A surrogate's study declares its reference study (a study record) and scope; decided by IUT (χ² only as a diagnostic). On pass, `extension.study.surrogate` is recorded (reference study's reference and hash, scope the intersection of the two).

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

### §R.7.1 CV1 (A1)

The table, scope and isolation rules of §R.6.2–6.4; `dependencies.py`'s re-derivation; an optional `simulation` property in `ext_computational_run.json` (needs hep-computing's agreement).

### §R.7.2 CV2 (B2)

The new entries of §R.6.2 (verification, `regression-comparison`, `surrogate-comparison`); the rules of §R.6.5; the transitive processing chain of §R.7.4. Gated like CV1. CV3 (C2) adds `extension.design_search` and the rules for confirmation runs; see §C.

### §R.7.3 sci-fix and advisories (A1)

| Defect | Ledger entry | Severity |
|---|---|---|
| D1 (including per-benchmark scope dimensions) | scope-kind | S2 |
| D2 | grade-table | S2 |
| D3 (including the t-based detection limit) | control-shift | S2 |
| D4 (including the definitions of the difference and its se) | gate-IUT | S2 |
| D5 (including block batch means replacing the bootstrap, exact counting intervals, MPV interpolation) | variance-method | **S1** |
| isolation definition (including field and vacuum) | isolation | S2 |
| D6 | stopping-rule | S3 |

One advisory each for S1 and S2 (keys `artifact_types: [computational-run]`, `extension_keys: ["study", "evidence_records"]`; introduced 0.20.0). simulated dataset-records cannot be keyed; the remedy asks holders to run `contracts/dependencies.py` on each simulated table.

### §R.7.4 Tracing processing chains

- Every processing step (simulation, reduction, digitization and reconstruction, table) writes a computational-run record with `**trace.provenance()`, the configuration hash, hashes of input records and files, and the code hash.
- The input chain of a simulated table can be any depth, as long as every level is a recorded computational-run and every root of the chain is a simulation run (CV2; previously only one level).
- When calling a C++ executable, Python records the sha256 of the executable and its sources, the version and the subcommand, and tags the call with `trace.tag()`.

---

## §R.8 Code and CI

| Location | Change |
|---|---|
| `contracts/validate.py`, `dependencies.py` | §R.6, §R.7 |
| `contracts/schema.py` | `maxItems`, `maximum`, `exclusiveMaximum` (added in A2.7; needed by `element_sim`'s schema; no contracts version change) |
| `core/stats/`, `core/simulation/` | Block estimators, the decision engine (A1's `equivalence` and `detection_limit`; B2's `change`; C2's `threshold`, `order` and paired mode), distribution functions, the seed hash, summary reading and schemas. They are in `core/` because both hep-detector's scripts and adapters (`geant4`, task C's `detector-design`) need them, and the layering rules let adapters import only `core` and `contracts` (§A.3 rule 1, §A.4.5) |
| `skills/hep-detector/scripts/` | inference and decisions read only boundary artifacts; geometry facts (minimum thickness, configuration) come from the effective config, records from before A2 still from spec/1; no new script; `SKILL.md` and description unchanged, the only exception being the one-line route pending as §P.7 item 12 (C1) |
| `adapters/geant4/assets/` | `g4sim/`; `layered_sim/` gains `g4sim`; `geant4_run.py` (logical runs and job splitting, the A1 Python summary producer, B2's `reco` and `table`); B1 `element_sim/` and `simroot`; B2 `simreco` |
| `adapters/detector-design/` | task C (C1–C3) |
| `SIM_SOURCES` | covers `g4sim` and the sources of each program |
| CI | task A needs no new required CI job; a ctest of `SimSummary.hh` can be an optional job. whether B2's `simreco` C++17 CI job is required is the maintainer's decision (§P.7 item 9, proposed: required) |

---

## §R.9 Generality

### §R.9.1 Use cases covered

| Use case | Supported by | Status |
|---|---|---|
| material-level references (J14-like) | the reference class, isolated slabs | A1 |
| spectrometers with a field (J15, compared with PAMELA and AMS-02) | `element_sim`, the field counted in the target, verification, the reconstruction chain | B1, B2, B3 |
| automated detector design (J16) | the `detector-design` adapter, confirmation runs, requirement decisions | C1–C3 |
| test beams and modules (compared with data) | the setup-matched class, target hashes from the geometry tree, per-benchmark scope dimensions | contracts in A1 and A2; geometry from a user application or `element_sim` |
| rare events | exact counting intervals | A1 |
| software or Geant4 changes | the regression class | B2 |
| fast simulation, ML surrogates | the surrogate class, reducers | B2 (contracts); reducers at the first need |
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
| ion sources and Birks (J17) | a cosmic-ray nuclei study and a literature record for PVT's Birks constant |
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

---

## §R.10 Stages and acceptance

Before 2026-10-23 this section copied the content and acceptance of each stage, which easily drifted from the task specs, so it now points to them. Stage order, scope boundaries, interface ownership, gates and open decisions are defined in Part 1; the work items and acceptance of each stage are defined in the task specs.

| Stage | In one sentence | Spec |
|---|---|---|
| A1 | Fix the defects that wrongly issue `validated-in-scope`; shared statistics and summary modules in `core/` (contracts CV1) | §A.5 |
| A2 | `g4sim`, `per-event` seeding, `layered_sim` writes the three boundary artifacts, study layer reads only them | §A.6 |
| B1 | `element_sim`, field, plane crossings, calorimeter leakage, per-event ROOT files, `simroot`, `check-spec` | §B.5 |
| B2 | `simreco`, processing chains, verification / regression / surrogate (contracts CV2) | §B.6 |
| B3 | The J15 study | §B.7 |
| C1 | Requirements, component catalogue, F0 search, closure tests | §C.5 |
| C2 | F1/F2 evaluation, confirmation runs, requirement decisions, paired comparison (contracts CV3) | §C.6 |
| C3 | J16 automated-design example, optional MOBO | §C.7 |

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
10. Only 931 bytes of quick-load budget remain; this architecture does not change `SKILL.md` or the description, the only exception being the one-line route pending as §P.7 item 12 (about 120 bytes, C1).
11. Effort: the prototype estimates A1's contract part at about 8–12 engineer-days plus Geant4 time; the rest is not estimated.

---

## §R.12 Decision record

### §R.12.1 Decided by the user

| Date | Decision | Where |
|---|---|---|
| 2026-10-22 | core code in C++, Python as the interface; compute core in C++, reference values stay in Python; separate executables exchanging JSON/CSV, no Python bindings | principle 2 (as interpreted by item 1 of 12.2) |
| 2026-10-22 | J15's TOF1 and TOF2 two layers each, all four of the same material | §B |
| 2026-10-22 | detailed per-event information stored in ROOT files | §R.4.1 T1, B1 |
| 2026-10-22 | J15 split from the rest into a second task, done later | task A (A1, A2), task B (B1, B2, B3); task C added later (§P.0) |

### §R.12.2 Proposals of this part (need the user's confirmation)

1. **Interpreting the language split:** per-event computation (simulation, digitization, reconstruction, accumulation) in C++; inference after merging in Python.
2. **A backend interface at the output** (three boundary artifacts), no engine abstraction layer.
3. **Event determinism:** `seeding: per-event` by default for new specs; job splitting and thread count do not affect events.
4. **Reproducibility means "same decisions"**, with numbers compared within tolerances; no integer quantization and no bit-identical statistics.
5. **Block batch means:** K ≥ 16 blocks by event number within one run; J14 runs with per-event data are recomputed offline without re-recording.
6. **A new `element_sim`**, with `layered_sim`'s spec format unchanged; both share `g4sim`.
7. **Five validation classes**, with regression and surrogate added in CV2 (B2).
8. **Eight stages** (A1, A2, B1, B2, B3, C1, C2, C3; §P.0), with ROOT files and `simroot` in B1.
9. The two-stage factor F₀.₉₀ or F₀.₉₅; the threshold for exact intervals (any block at 0 or a total < 100).

### §R.12.3 For the maintainer to decide

The merged list and its proposals are in §P.7 (14 items); this part's original seven items are all included there.

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
