# Program plan: Geant4 simulation, the J15 minimal spectrometer and automated design search

> Document type: plan (for the implementing agent, reviewers and the maintainer). Status: awaiting the user's and the maintainer's approval
> Date: 2026-10-23
> Language: English translation of the Traditional Chinese original [`plan.md`](plan.md), with the same content. If they disagree, the Chinese wins and the English is corrected at the same time
> Authority: **the order of stages, numbering, version placeholders, interface ownership, gates, open decisions and the execution environment are set by this document**; the content and acceptance of work items are set by each task spec; [`architecture.en.md`](architecture.en.md) only explains the design rationale
> Execution environment: **every stage runs in its own isolated git worktree**, and no file in the main checkout is changed (§10)

**For the implementing agent:** read §0 (stages at a glance), §10 (running in an isolated worktree), §6 (gates) and §4 (interface ownership) in that order, then the §0 task card of the task spec your stage belongs to. Before writing any code, create and confirm the worktree per §10.2.

---

## 0. One-page summary

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

## 1. Evaluation: problems of the earlier plan and how they are handled

| # | Problem | Effect | Handling |
|---|---|---|---|
| P1 | **Scope creep in A1.** The previous round put features needed only by task C (one-sided threshold and order decisions, paired comparison, search roles, `values` accumulator) into A1 | A1 is a sci-fix that must quickly fix defects that already wrongly issue `validated-in-scope`; extra features add evidence and review burden and delay the fix | Principle R1 ("introduced by the first consumer"): A1 contains only what it uses itself; the decision engine's `change` is added in B2, `threshold` / `order` / paired comparison in C2; the location (`core/`) is fixed from the start |
| P2 | **Name clash.** "C1, C2" meant both contract versions and stages of task C | Agents and reviewers misread | Contract versions are written **CV1, CV2, CV3**; task C's stages are C1–C3 (§5) |
| P3 | **Critical path too long.** Task C waited for all of B2, and B2 mixed infrastructure (`simreco`, contracts) with the J15 physics study | Automated design held up by J15 research | B split into B2 (reconstruction and contracts) and B3 (J15 study); C2 waits only for B2; C1 waits only for A1 |
| P4 | **Interfaces in the wrong layer.** Statistics and summary reading were in hep-detector's scripts, which adapters may not import by the layering rules | Task C would need a second implementation | Shared code always in `core/`; §4 lists the location, owner and consumers of every interface |
| P5 | **Duplicated documents drift.** `architecture.md` §10 copied each stage's content and acceptance, every change needed syncing, and inconsistencies appeared | Readers do not know which document wins | Division of authority (§9); `architecture.md` §10 now points to this document |
| P6 | **Open decisions scattered** over three specs | The maintainer cannot see the whole picture, nor which decision blocks which stage | Merged into one table marking the blocked stage (§7) |
| P7 | **No gates between stages** | E.g. if ROOT reading capability or the deterministic field check fails, later stages would still proceed as planned | Explicit gates (§6) |
| P8 | **Only scattered effort estimates** | Cannot schedule | Relative size (small / medium / large) and the known estimate (A1 contract part about 8–12 working days); the rest estimated at the start of each stage (§0, §8) |
| P9 | **Cross-adapter dependency undefined.** Task C must produce and validate `element_sim` specs, but an adapter may not import another adapter | C1 cannot validate its realizations | `geant4_run.py` provides a `check-spec` subcommand (B1), called by `detector-design` as a subprocess; before B1, C1 relies on its own validity rules (§4) |

---

## 2. Planning principles

| # | Principle | Explanation |
|---|---|---|
| R1 | **Introduced by the first consumer, but located correctly from the start** | Each interface is added in the first stage that needs it; shared interfaces live from day one where every consumer can import them (`core/`, `contracts/`) |
| R2 | **Schemas evolve only additively** | New fields are optional; version numbers (`summary_version` etc.) get a minor increase; old records can always be read and replayed |
| R3 | **One production implementation per quantity** | An implementation in another language or place exists only in tests as an oracle |
| R4 | **Keep the sci-fix minimal** | A1 contains only the changes needed to fix the defects and their direct foundations |
| R5 | **Each stage merges on its own** | Own version, VALIDATION entry, CHANGELOG, acceptance list; after merging the plugin is consistent |
| R6 | **Reproducible decisions, traceable numbers** | Reproducibility means the same decisions and labels (architecture §5.6); results carry search size and evidence correlation |
| R7 | **AI is the designer, not the judge** | Claude chooses structures, proposes seeds and interprets results; "is it met, which is best" is decided only by recorded evaluation and statistics (task C) |

---

## 3. Stage contents and acceptance (summary)

Full work items and acceptance are in the task specs; this only lists scope boundaries to avoid overlap.

| Stage | Includes | Explicitly excludes (and where it goes) |
|---|---|---|
| A1 | Benchmark table and validation classes (reference, setup-matched, sanity, interface); scope comparison; configuration and isolation (`spec-v1`); block batch means, exact intervals, MPV, quantiles (histogram); the decision engine's `equivalence` and `detection_limit`; two-stage event count; seed hash H; evidence roles; schemas and reading of `simulation-summary/1` and `simulation-observables/1`; Python summary producer; J14 regeneration; sci-fix process | `change` (B2), `threshold` / `order` / paired comparison (C2), search roles and seed_group (C2), `values` accumulator (C2), C++ summary (A2) |
| A2 | `g4sim` (`SimHash`, `SimSeed`, `SimSummary`, `MiniJson`, `SimProbe`); `per-event` seeding; `layered_sim` writes summary, column map, effective config; name-free `tree-v1`; effective configs stored by content hash; study layer reads only boundary artifacts; schema keywords | `element_sim` (B1) |
| B1 | `element_sim.spec/1`, `element_sim`, field, plane crossings, calorimeter mother and leakage columns, per-event ROOT files, `simroot`, `geant4_run.py check-spec`, interface consistency of the two backends, deterministic field check | `simreco` (B2), statistical study of J15 (B3) |
| B2 | `simreco` (digitization and reconstruction, portable random numbers), `geant4_run.py reco` and `table`, transitive processing chains, verification / regression / surrogate classes and table entries, the decision engine's `change`, CV2 | J15's validation ladder and convergence (B3) |
| B3 | J15 study: validation ladder, calorimeter cut convergence, variations, TOF σ_t sensitivity, recorded data, journey and routing, docs | — |
| C1 | Requirements spec, first component catalogue, design grammar and realization, F0 analytic evaluation, NSGA-II (standard library), search record (F0-only), agent protocol, closure tests | Any Geant4 evaluation (C2) |
| C2 | F1/F2 evaluation, confirmation runs, the decision engine's `threshold` and `order`, paired comparison and seed_group, search roles, `values` accumulator (Python and `SimSummary.hh`), guards against exploiting simulation defects, robustness, CV3 | J16, MOBO (C3) |
| C3 | J16 automated-design example (compared with J15), optional MOBO (Ax/BoTorch) backend | — |

---

## 4. Interface ownership

| Interface | Introduced | Location | Owner (steward) | Consumers |
|---|---|---|---|---|
| Benchmark table, validation classes, scope comparison, isolation rules | A1 (B2, C2 add) | `contracts/validate.py`, `dependencies.py` | contracts (content proposed by hep-detector) | A1, B2, B3, C2 |
| Seed hash H (Python) | A1 | `core/simulation/seeds.py` | hep-detector | geant4 adapter, `check_geant4_study.py`, detector-design |
| Seed hash H (C++) | A2 | `adapters/geant4/assets/g4sim/SimHash.hh` | hep-detector | `layered_sim`, `element_sim`, `simreco` |
| Roles: evidence roles | A1 | `contracts/`, study-spec schema | contracts | all |
| Roles: search roles, seed_group | C2 | same (CV3) | contracts | C2, C3 |
| Schemas, reading and merging of `simulation-summary/1` and `simulation-observables/1` | A1 (`values` added in C2) | `core/simulation/summary.py`, `core/simulation/schemas/` | hep-detector | all |
| Schemas of the column map and effective config | A2 | `core/simulation/schemas/` | hep-detector | A2, B1, C2 |
| Block estimators, exact intervals, MPV, quantiles | A1 (`values` quantiles in C2) | `core/stats/batch_means.py` | hep-statistics | hep-detector scripts, detector-design |
| Distribution functions (`t_ppf`, `f_ppf`, `garwood`) | A1 | `core/stats/distributions.py` | hep-statistics | same |
| Decision engine | A1 `equivalence`, `detection_limit`; B2 `change`; C2 `threshold`, `order`, paired mode | `core/stats/decisions.py` | hep-statistics | A1, B2, B3, C2 |
| `g4sim` headers | A2 (`values` in `SimSummary` in C2) | `adapters/geant4/assets/g4sim/` | hep-detector | `layered_sim`, `element_sim`, `simreco` |
| `element_sim.spec/1` and `check-spec` | B1 | geant4 adapter | hep-detector | B1, B3, C1 (after B1 is merged), C2 |
| Per-event ROOT files, `simroot` | B1 | geant4 adapter | hep-detector | B2, B3 |
| `simreco` and reco spec | B2 | geant4 adapter (C++, not linked to Geant4) | hep-detector | B3, C2 |
| Requirements spec, component catalogue, design grammar, search spec | C1 | `adapters/detector-design/` | hep-detector (open, §7) | C1–C3 |
| `extension.design_search` and its rules | C2 | `contracts/` (CV3) | contracts | C2, C3 |

Cross-adapter calls always go through subprocesses and JSON files (layering rule: adapters import only `core` and `contracts`), e.g. detector-design calls `geant4_run.py check-spec`, `geant4_run.py run`, `geant4_run.py reco`.

---

## 5. Naming and numbering

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
| Section references | "§n" is the same document; "task A §n", "architecture §n", "plan §n" are other documents | — |

"contracts C1, C2" in earlier documents are CV1, CV2; `architecture.md` keeps the old notation and states the mapping in its header.

---

## 6. Stage gates

| Gate | When | Condition | If it fails |
|---|---|---|---|
| G-A1 | Before merging A1 | Regenerated J14 records pass `--strict` and `dependencies.py`; gate, coverage, MPV and detection-limit toys pass | Do not merge; if J14 loses `validated-in-scope` through a missed target, the maintainer decides per §7 item 4 |
| G-A2 | Before merging A2 | J14's CSV bit-identical to the pre-A2 one; the probe does not change the random state | Do not merge |
| G-B1a | First day of B1 | `G4RootAnalysisReader` can read MT-merged, compressed files and string columns | `simroot` reads only scalar columns, strings move to a JSON side file (task B B1.5) |
| G-B1b | Before merging B1 | Deterministic field check passes at nominal values; observables shared by the two backends agree statistically | Do not enter B2 |
| G-C1 | Before merging C1 | All closure tests pass | Do not enter the search part of C2 |
| G-C2a | C2 trial | Measure the variance reduction of paired comparison | If below the declared value, S2 uses independent comparison (task C C2.3) |
| G-C2b | Before merging C2 | Winner's-curse and requirement-decision toys and CV3 contract tests pass | Do not merge |
| G-C3 | Before merging C3 | J16 completed with the comparison against J15 | Do not merge |

---

## 7. Decisions for the maintainer (merged list)

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

## 8. Main cross-task risks

1. **Maintenance cost of two Geant4 programs** (`layered_sim` frozen, `element_sim` added). Duplication is controlled through `g4sim`; in the long run, once `element_sim` gains primary exit records, J14 can migrate to it and `layered_sim` can be retired (deferred; trigger: `element_sim` can produce all of J14's observables).
2. **Actual behaviour of the statistics**: O(1/B) bias of block batch means for skewed distributions, the miss rate of the two-stage design (about 19 % per point pair), and a possibly small variance reduction from paired comparison. All measured with toys and trials, never assumed.
3. **Geant4 behaviour not checked line by line**: stepper construction, the Birks API, the direction of the field intersection error, the nucleon cross sections of the two physics lists, the capability of `G4RootAnalysisReader`. Each is checked first in the stage that first uses it.
4. **Compute**: J14 re-recording (A1), calorimeter showers (B3), F1/F2 search (C2). Each stage writes its budget after a trial.
5. **Entry budget**: hep-detector quick load has only 931 bytes left, description 1,016 / 1,024 characters. Only §7 item 12 may touch `SKILL.md`.
6. **Incomplete effort estimates**: only the A1 contract part has a prototype estimate (about 8–12 working days); the rest is estimated and recorded at the start of each stage.
7. **References**: GRACE and VI-BRATO cited in task C are 2026 preprints; all sources are checked through hep-citations before formal citation.

---

## 9. Document map and division of authority

| Document | Content | Authority |
|---|---|---|
| `plan.md` (this document) | Evaluation, principles, stages, interface ownership, naming, gates, open decisions, risks, execution environment | Order, numbering, version placeholders, ownership, gates, open decisions, execution environment (isolated worktree) |
| `task-a-core.md` | Work items and acceptance of A1, A2 | Content and acceptance of these two stages |
| `task-b-j15.md` | J15 design; work items and acceptance of B1, B2, B3 | Content and acceptance of these three stages; J15's numbers |
| `task-c-design-search.md` | Design of automated design search; work items and acceptance of C1, C2, C3 | Content and acceptance of these three stages |
| `architecture.md` | Design rationale, reference experiments, superseded designs | Rationale; where it conflicts with a spec, the spec wins and the conflict is reported |
| `README.md` | Folder entry point and file list | — |
| `gate_operating_characteristics.py`, `j15_design_estimates.py`, `design_search_closure.py` | Programs computing design numbers | Numbers in the corresponding appendices |

Every spec has the same structure: §0 task card, §1 terms and files, §2 prerequisites and provided interfaces, §3 hard rules, §4 design summary, from §5 the work items and acceptance of each stage, then contracts and versions, checks, not done and deferred, open decisions and risks, order of work, appendices.

---

## 10. Execution environment: isolated worktree

### 10.1 Principle

- **Every stage runs in its own isolated git worktree**: one stage, one worktree, one branch.
- Files in the main checkout (the working tree at the repository root) and in other worktrees are never changed.
- Reasons:
  - stages that can run in parallel (e.g. C1 with A2 and B1) and parallel agents do not overwrite each other;
  - build directories, Geant4 output and temporary files are isolated from each other;
  - a failed stage can be discarded as a whole without affecting other work;
  - each stage's change is exactly the diff of one branch, so review and merge scope are clear.

### 10.2 Creating and confirming

| Item | Rule |
|---|---|
| Location | `.claude/worktrees/geant4-<stage>`, stage name in lower case, e.g. `.claude/worktrees/geant4-a1` |
| Branch | `geant4-<stage>`, e.g. `geant4-a1` |
| Base | The latest `main` that already contains all prerequisite stages (the "Prerequisite" column of §0); e.g. B2 is based on `main` after B1 is merged |
| Source of the specs | Once approved, this folder is merged to `main` and the worktree contains the specs. Before approval the specs exist only on branch `worktree-geant4-architecture`; read them with `git show worktree-geant4-architecture:plugins/hep-research/docs/dev/geant4-architecture/<file>`, and do not merge that branch into a stage branch |
| In Claude Code | The session itself enters the worktree with `EnterWorktree`; when delegating work to a subagent, the Agent tool uses `isolation: "worktree"` |
| Elsewhere | `git fetch origin && git worktree add .claude/worktrees/geant4-a1 -b geant4-a1 origin/main` |
| Confirm before starting | `git rev-parse --show-toplevel` is the worktree's path, `git branch --show-current` is the stage's branch, `git status` is clean; the three results go into the stage's work record (the environment field of the VALIDATION entry) |

### 10.3 Rules inside the worktree

1. All editing, building, testing, Geant4 runs and spec corrections happen in the stage's worktree; never `cd` into the main checkout or another worktree.
2. Commands use clear absolute or relative paths inside the worktree; avoid composing git arguments from variables computed at run time, so that tools and reviewers can confirm a command stays inside the worktree.
3. **`git stash` is shared by all worktrees.** Do not use bare `git stash` or `git stash pop`; use a temporary WIP commit to set work aside.
4. Build directories, E2 output, ROOT files and trial results go in directories of that worktree that are not committed (e.g. `build/`, `work/`, excluded by `.gitignore`), or in a temporary directory owned by that worktree; different worktrees do not share build directories. The Geant4 installation itself (E2) may be shared read-only by several worktrees.
5. Commit only on the stage's branch; commits carry the required trailers; push to the remote branch of the same name. Do not push to `main` or open a pull request without the maintainer's approval.
6. Before merging, run the checks of task A §8 in the worktree and confirm the gates (§6).
7. If the specs need correcting during implementation, change both languages in the same worktree and record it in the version history; if other stages are affected, update this document too.
8. Independent reviews and other subagents run with `isolation: "worktree"`; reviews read and do not write, and worktrees without changes are cleaned up automatically when they finish.

### 10.4 Stages that can run in parallel

| Running together | Condition | Note |
|---|---|---|
| C1 with A2, B1, B2, B3 | A1 merged | C1 touches only `adapters/detector-design/` and its docs, so conflicts are few |
| B3 with C2 | B2 and C1 merged | Both may change `geant4-study-protocol.md` and the journey docs; whichever merges later rebases on the new `main` and reruns the checks |

Each parallel stage uses its own worktree and branch; one stage is never implemented by two agents in different worktrees at the same time.

### 10.5 Finishing

- **After merging:** `git worktree remove .claude/worktrees/geant4-<stage>` and delete the local branch; the next stage creates a new worktree from the new `main`.
- **Abandoning:** remove the worktree and the branch; do no cleanup in the main checkout.
- **This folder itself** is written on branch `worktree-geant4-architecture` in worktree `.claude/worktrees/geant4-architecture`; later document changes happen there too, until it is merged to `main`.

---

## 11. Version history

| Version | Content |
|---|---|
| 2026-10-23 | First version: consolidated evaluation (P1–P9), planning principles, eight stages (B split into B1–B3, C as C1–C3), interface ownership, naming (contract versions written CV1–CV3), gates, merged open decisions and risks |
| **2026-10-23 (this version)** | **Added §10 "Execution environment: isolated worktree" (creating, confirming, rules, parallel stages, finishing) and a reading guide for agents** |
