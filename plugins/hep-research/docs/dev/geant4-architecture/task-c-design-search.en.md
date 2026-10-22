# Task C: automated detector design search

> Document type: design proposal and implementation spec (for the implementing agent and reviewers). Status: proposal, awaiting the user's and the maintainer's approval
> Basis: [`architecture.en.md`](architecture.en.md) (simulation architecture), [`task-a-core.en.md`](task-a-core.en.md) (statistics and boundary artifacts), [`task-b-j15.en.md`](task-b-j15.en.md) (`element_sim`, `simreco`, J15)
> Order: C1 needs only task A; C2 starts after task B is merged
> Date: 2026-10-23
> Language: English translation of the Traditional Chinese original [`task-c-design-search.md`](task-c-design-search.md), with the same content. If they disagree, the Chinese wins and the English is corrected at the same time
> In one sentence: the user writes down the physics requirements; Claude freely chooses and combines detector structure types from a component catalogue, an optimizer searches on multi-fidelity simulation, and independent confirmation runs report the best designs meeting the requirements and their trade-offs

---

## 0. Task card

**Goal.** Let the AI start from "physics requirements", choose detector structure types by itself (tracker planes, magnet region, TOF, calorimeters, passive layers, …), combine them freely and tune their parameters, and arrive at an optimized design (or a Pareto front of trade-offs) that meets the requirements, with results that withstand statistical and provenance checks.

**Two stages:**

| Stage | Content | Prerequisite | Version |
|---|---|---|---|
| **C1** Requirements, grammar and fast search | Schemas for requirements and design grammar; first component catalogue; realization of a design as `element_sim.spec/1`; F0 analytic evaluation; standard-library search (Sobol, NSGA-II); search record; closure tests | Task A merged; the `element_sim.spec/1` schema (B1.1) may be used as a draft | new adapter `detector-design` **0.1.0** |
| **C2** Simulation evaluation and confirmation | F1 and F2 evaluation (`element_sim` and `simreco`); confirmation runs; robustness and guards against exploiting simulation defects; optional MOBO backend; contracts C3; J16 automated-design example | Task B merged | adapter **0.2.0**, contracts **C3** (minor) |

**Out of scope:** differentiable simulation and differentiable surrogates (the MODE route, §9); non-box geometry (cylindrical collider detectors); optical physics (Cherenkov, RICH); reinforcement learning; letting an LLM alone decide the best design.

**Deliverables:** `adapters/detector-design/` (schemas, catalogue, realization, evaluation, search, report); hep-detector reference `detector-design-search.md` (with the agent protocol); contract rules for search records (C3); closure tests; the J16 example; VALIDATION entries DESIGN-SEARCH-F0 (C1) and DESIGN-SEARCH (C2); CHANGELOG; release manifest.

**Definition of done:** every box in the acceptance lists C1.9 and C2.9 is ticked; every check in task A §9 passes.

**Main decisions:**
1. **Claude is the designer, not the judge.** Claude chooses structure types, proposes seed designs, sets the search ranges and interprets results; but "which design is best and whether it meets the requirements" is decided only by recorded evaluation and statistics. Claude's proposals go through the same evaluation pipeline as randomly generated candidates, with no privilege (§5.1).
2. **Free combination, within a grammar.** Structural freedom comes from "component catalogue × composition rules": any sequence of components passing the validity rules is a legal design. New component types enter only through a reviewed catalogue change, never invented ad hoc during a search (§5.3).
3. **Multi-fidelity.** F0 analytic formulas (microseconds per design) screen 10⁴–10⁶ designs; F1 Geant4 with few events refines hundreds; F2 full statistics only for a few finalists (§5.4). This is the common practice of AID(2)E, dRICH and the MODE studies.
4. **Search and confirmation are separate.** Search-stage values suffer from the "winner's curse" (choosing the best of many noisy evaluations is necessarily optimistic), so they are used only for ranking and are never reported as results; reported performance comes only from pre-declared confirmation runs with independent seeds (§5.6).
5. **The result is a proposal, not a validation.** Searched designs are always labelled `unvalidated`; the record states "simulation-optimized design", with the search size, confirmation runs and robustness.

**Before starting:** read task A §1, §2, §4, A1.8 (gate) and A1.9 (two-stage event count); for C2 also task B §4, B1.1 and B2.1. Check the facts this document quotes with the method of task A appendix B.

---

## 1. Terms and notation

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
| Notation | "C1.3" is a work item of this document; "A1.8", "B2.1" are work items of tasks A and B; "architecture §6" is a section of `architecture.en.md` |

---

## 2. Practice in the field and lessons

| Study | Approach | Lesson adopted here |
|---|---|---|
| EIC dRICH (Cisbani et al., JINST 15 (2020) P05009) | 8 parameters; objective π/K separation (harmonic mean at two momenta); Geant4 with 2.5 % noise; Gaussian-process Bayesian optimization, 20 designs in parallel per call, converging after about 55 calls; better than the original design (3.23 vs 2.9); tolerance intervals from the posterior | Model the noise explicitly; parallel batches; tolerance and parameter-correlation analysis from the posterior; results "simulation only", prototype validation needed |
| AID(2)E (ePIC, arXiv:2405.16279) | Multi-objective Bayesian optimization (qNEHVI, Ax/BoTorch) and NSGA-II; dRICH with 7 parameters, 200 evaluations, converging after 150; closure test on DTLZ2 with a known Pareto front; distributed execution with PanDA | Multiple objectives and Pareto; MOBO for ≤ 4 objectives, genetic algorithms for more or for discontinuities; closure tests first; geometry constraints (overlap, envelope) checked before simulation |
| MODE (arXiv:2203.13818, 2310.05673) | End-to-end differentiable optimization; differentiable surrogates replace non-differentiable simulation; utility includes physics goals and cost | Align with experiment goals through one utility or a Pareto front, not per-subsystem optimization; surrogates can steer designs into bias and must be confirmed with full simulation |
| AIDO diffusion-model calorimeter (arXiv:2502.02152) | 6-layer sampling calorimeter, 12 parameters (thickness and material); material as a softmax categorical; cost and length caps; the result reproduces known calorimeter principles | Categorical choices (materials) and cost constraints can be part of the search; "reproducing known principles" is a reasonable first acceptance |
| ECAL longitudinal structure (Borysov et al., EPJ Web Conf. 315, 03006) | Semi-analytic model (checked against Geant4) + genetic algorithm with non-dominated sorting | Screen with an analytic model, check with Geant4: the F0 → F2 multi-fidelity |
| SWGO array layout (arXiv:2310.01857) | Differentiable optimization of about 6000 tank positions; utility = flux precision + energy resolution + pointing resolution + area cost | The utility's weights are a declared choice; some derivative terms dominate and push designs to extremes, and need checking |
| GRACE (arXiv:2602.15039) | An LLM agent builds simulations from natural language or papers and explores design variants; physics verifier and provenance | Geometry often needed several regenerations to match the spec and should be validated before simulation; the agent noticed anomalies but did not follow them up; cost and engineering constraints ignored |
| VI-BRATO (arXiv:2604.21804) | An LLM agent directs a two-level DD4hep/Geant4 scan of geometry and digitization, reaching the optimum of a 2255-point grid in 46 runs | Agents are good at decomposing problems and steering scans; but conclusions need independent checks, and experts are still needed for realizability |

Summary: in no real case does the LLM declare "the best" by itself; successful approaches all have "explicit objectives and constraints + reproducible evaluation + a recorded optimizer + confirmation with full simulation". The LLM's value lies in turning requirements into a search problem, proposing physically motivated starting points, decomposing the problem and following up anomalies.

---

## 3. Prerequisites: interfaces provided by tasks A and B

| Provider | Interface | Use in task C |
|---|---|---|
| Task A | `core/stats/batch_means.py` (block batch means, SE, exact intervals, quantiles), `core/stats/decisions.py` (decision engine), `core/simulation/summary.py`; all in `core/`, importable by an adapter (task A §4.4) | Objective estimates at F1 and F2; requirement decisions use `threshold`, ordering of finalists uses `order`, comparing confirmation with F0 uses `equivalence` |
| Task A | Two-stage event count (A1.9) | Event counts of confirmation runs |
| Task A | Paired comparison and seed_group (A1.4, A1.8) | Designs of one generation in S2 share a seed_group, to reduce ranking noise |
| Task A | Role classes: `search-F1`, `search-F2`, `confirmation` (A1.4) | Search runs are never evidence; the S of a confirmation run never equals that of any search run |
| Task A | `simulation-observables/1`, the `values` accumulator (A1.5) | The search spec references the same observable declaration; accurate quantiles even for designs with widely different resolutions |
| Task A | Name-free `tree-v1` and effective configs stored by content hash (A2.4) | Design cache; settings of hundreds of runs are not stored repeatedly |
| Task A | Seed hash H and S = H(study_id, role, point_id) (A1.4) | point_id of each design evaluation = design hash; confirmation runs have role `confirmation` |
| Task A | Three boundary artifacts, `tree-v1` (A2.3–A2.6) | Evaluation reads only summaries; the design hash is checked against the realized geometry tree |
| Task B | `element_sim.spec/1` (B1.1), field (B1.2), calorimeter leakage (B1.3) | Realization target of designs |
| Task B | `simreco` (B2.1): rigidity, β, calorimeter energy | Reconstruction at F1 and F2 |
| Task B | surrogate class (B2.3) | Positioning of F0 and F1 relative to F2: surrogates that do not change the label |
| Existing tools | `tracker_resolution.py`, `multiple_scattering.py` | Tracking resolution at F0 (called as subprocesses, formulas not rewritten) |

---

## 4. Hard rules

All of task A §2 and task B §3 apply. In addition:

1. **The optimizer core uses only the standard library.** Sobol sequences, NSGA-II and (optionally) CMA-ES are implemented with the standard library. Bayesian optimization (Ax/BoTorch) is only an optional backend of the adapter, with tested versions recorded in `adapter.json` like other adapters' external tools; the search still runs without it.
2. **One production implementation per quantity.** F0 calls the existing tracking and multiple-scattering scripts; material constants come from Geant4's NIST tables or PDG (via hep-citations), not a separate copy.
3. **Declared in advance.** Requirements, catalogue version, grammar, search budget, optimizer settings and seeds are written into the search spec and hashed before the first evaluation. Any later change creates a new search version; old versions and their results stay in the record.
4. **Search values are not reported.** Search-stage objective values are used only for ranking; every externally reported performance number must cite confirmation runs.
5. **LLM proposals have no privilege.** Designs proposed by Claude are marked `proposer: llm` and go through the same validity checks and evaluation; Claude may not change evaluation outputs, nor change the requirements after seeing results without opening a new version.
6. **Cost and mass models are declared inputs.** The plugin ships only placeholder models marked `assumed`; real unit prices and mass models are supplied by the user with sources. Without a model, cost and mass are not used as objectives or constraints.
7. **Experiment names** appear only in `docs/` and example READMEs; the component catalogue uses generic names.
8. **Do not change `skills/hep-detector/SKILL.md`**, unless the maintainer approves one routing line pointing to the reference (§10).

---

## 5. Design

### 5.1 Three roles

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

### 5.2 Requirements spec `detector-requirements/1`

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

### 5.3 Design grammar `detector-design/1` and component catalogue

**First component catalogue** (all realizable as `element_sim` box elements, at most one level of nesting):

| Component type | Parameters (type) | Realization | F0 model |
|---|---|---|---|
| `magnet-region` | B (continuous, T), length, aperture (continuous, mm) | Field-region mother (`field`), can hold tracker and TOF daughters | Bending; MDR; mass model (declared) |
| `tracker-plane` | Material (categorical), thickness, position resolution (bending/non-bending), size | `tracker-plane` element; resolution written into the reco spec | `tracker_resolution.py` (measurement term), `multiple_scattering.py` (scattering term) |
| `tof-layer` | Material, thickness, σ_t, size | `tof-layer` element | σβ/β = σ_t c / D (averaged over layers) |
| `calorimeter-sampling` | Absorber material and thickness, active material and thickness, layer count (integer), transverse size | `calorimeter` mother + repeated sampling layers | X₀, λ_I, effective Molière radius; an energy-resolution parametrization for F0 ranking only |
| `calorimeter-homogeneous` | Material, length, transverse size | `calorimeter` mother + one active volume | X₀, λ_I |
| `passive` | Material, thickness, size | `passive` element | Material budget, multiple scattering |

**Composition rules (validity, checked before simulation):**
- Components form a sequence along the x axis; the sequence length and the count of each type have caps (declared in the search spec).
- No overlaps; everything inside the envelope; a minimum spacing between planes (declared).
- Daughters only in a `magnet-region` or `calorimeter` mother, with one level of nesting (the `element_sim` limit).
- Parameters within catalogue ranges; materials from the catalogue's material list.
- Structurally "unreasonable" combinations (e.g. requiring rigidity resolution without a field) are **not** forbidden by rules but naturally eliminated by objectives and constraints; rules handle only what is physically or programmatically impossible. This keeps the "free combination".

**Genome encoding:** a fixed number of slots, each with an "enabled" bit, a component type (categorical) and that type's parameters; disabled slots are not realized. Order follows the slots' x positions. This lets the genetic algorithm add and remove components and switch types (AIDO handles materials one-hot; here categorical genes handle types and materials).

**Realization:** `realize(design) → (element_sim.spec/1, reco spec)` is deterministic; design hash = sha256 of the normalized design JSON; after realization the geometry is checked with `tree-v1` (A2.4). Evaluations with the same design hash can be reused (cache), but the cache key includes fidelity, catalogue version and program hash.

### 5.4 Multi-fidelity evaluation

| Fidelity | Method | Cost per design | Output | Use |
|---|---|---|---|---|
| F0 | Analytic formulas and existing tools (tracking measurement and scattering terms, material budget, helix geometry for acceptance, TOF formula, X₀ and λ_I) | Microseconds to milliseconds | Objective values (no statistical error, but model error) | Structure search; screening 10⁴–10⁶ designs |
| F1 | `element_sim` + `simreco`, about 10³ events per design, K = 16 | Minutes | Objective values ± SE (block batch means) | Refining continuous parameters of hundreds of designs; calibrating F0 |
| F2 | As F1, event count from A1.9's two-stage design; convergence gate (A1.8) and variations (B2.6) | Hours | Objective values ± SE, decisions | Finalists |
| Confirmation | As F2, role `confirmation`, independent seeds | Hours | Reported performance and requirement decisions | The only reportable numbers |

- **The F0 vs F2 difference** is recorded for each finalist (`fidelity_gap`). If it exceeds the declared threshold, that objective is ranked by F2 only at the final selection, and the report explains the F0 model's limitation.
- Architecturally F0 and F1 belong to the surrogate class (B2.3): they never change the label.

### 5.5 Search strategy

| Step | Content | Default method | Budget (default, declarable) |
|---|---|---|---|
| S0 Design brief | Claude reads the requirements and writes candidate structure types, 2–6 seed topologies with physics reasoning, and a decomposition of the problem | Claude | — |
| S1 Structure search | Search the full genome (structure + parameters) at F0; initial population = seed topologies + Sobol random designs | NSGA-II (standard library) | population 200 × 100 generations = 2×10⁴ F0 evaluations |
| S2 Parameter refinement | Take the top K designs with **distinct topologies** (deduplicated by topology hash, keeping diversity) and refine continuous parameters at F1 | NSGA-II or CMA-ES; optional MOBO (qNEHVI), limited to ≤ 4 objectives and ≤ 20 parameters | K = 5, about 100 F1 evaluations each |
| S3 Final selection | The best design of each topology goes to F2; convergence gate, variations | — | ≤ 5 designs |
| S4 Confirmation | Confirmation runs of the finalists; requirement decisions; robustness | — | ≤ 5 designs |

- Stopping rule: budget exhausted, or hypervolume improves by less than the declared value over G consecutive generations. No budget increase based on results; more budget is a new search version.
- After S0, Claude may add new seed topologies (e.g. to follow up an anomaly), but these proposals are likewise marked `proposer: llm` and count toward the search size.

### 5.6 Statistical integrity

| Risk | Handling |
|---|---|
| Winner's curse | Search values only rank; reports come only from confirmation runs (role `confirmation`, S never used in the search); the report gives "search estimate − confirmation estimate" for each finalist as a diagnostic |
| Noisy constraints | Requirement decisions are made by the decision engine's `threshold` (task A A1.8), one-sided: for a "≤ threshold" requirement, met = estimate + t₀.₉₅·SE ≤ threshold; not met = estimate − t_{1−α/m}·SE > threshold; otherwise unresolved (m = finalists × requirements). Exact intervals for low counts |
| Claiming dominance in noise | Ordering among finalists is decided by the decision engine's `order`, claimed only when the bound of the difference excludes 0; the report gives "the statistically non-dominated set" |
| Ranking noise | Designs of one generation in S2 share a seed_group (task A's paired comparison), so differences vary less; confirmation runs do not share one and stay independent |
| Search size | The record gives the number of designs evaluated at each fidelity, the number of topologies, optimizer settings and seeds |
| Exploiting simulation defects | Finalists must pass the convergence gate for their relevant parameters (production cut, maximum step, field accuracy); physics-model variations (rules of B2.6); designs in materials or energy regions outside every reference benchmark's scope are flagged in the report (the label is `unvalidated` anyway; this is information for the reader) |
| Robustness | Continuous parameters are perturbed within the requirements' `tolerance` and the catalogue's manufacturing tolerances (F0 full factorial or F1 sampling) and the performance distribution reported; the worst case within tolerance is also decided, and results are classed as "robustly met" or "nominally met" |
| Changing requirements | Any change to requirements or budget is a new search version; the report lists all versions |

### 5.7 Records and contracts (C3)

A search record is a computational-run with `extension.design_search`:

```
{ "requirements_sha256": "...", "catalogue_version": "1", "catalogue_sha256": "...",
  "search_spec_sha256": "...", "search_version": 1, "previous_versions": [],
  "optimizer": {"name": "nsga2", "implementation": "detector-design 0.1.0", "backend": null, "seed": 12345, "config": {...}},
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

**Contract rules (C3, gated as in C1):**
- The label of a search record must be `unvalidated`.
- Each finalist's `confirmation_runs` must exist with role `confirmation`, their spec hash must equal the design's realization, and their seed S must not appear in any search evaluation listed in `evaluations_ref` (re-derived by `dependencies.py`).
- Tables or communications derived from a search record must take their numbers from confirmation runs; citing search-stage values is rejected.
- A communication using search results gets the `communication.simulation_optimized_design` warning.

---

## 6. Stage C1: requirements, grammar and fast search (adapter detector-design 0.1.0)

### C1.1 Schemas

`detector-requirements/1`, `detector-design/1`, `catalogue/1`, `design-search-spec/1` (requirements hash, catalogue version, slot count and caps, budget, optimizer settings, seed, stopping rule), in `adapters/detector-design/assets/`, using only keywords supported by `contracts/schema.py`; cross-field rules checked in Python.

### C1.2 First component catalogue

The six components of §5.3; each with parameter ranges, material list (NIST names), manufacturing tolerances, mass model (density × volume; magnet mass is a declared placeholder model marked `assumed`), F0 model and realization rule. Each catalogue entry has unit tests (realized geometry, material budget).

### C1.3 Realization and validity

`design_search.py realize`: design → `element_sim.spec/1` and reco spec; validated with the B1.1 schema and cross-field rules; no Geant4 needed. Invalid designs return the reason (overlap, outside envelope, nesting, range), exit 2.

### C1.4 F0 evaluation

`design_search.py evaluate --fidelity F0`: calls `tracker_resolution.py` and `multiple_scattering.py` as subprocesses; material budget, X₀ and λ_I from the composition of Geant4 NIST materials (the same method as `geant4_verify.py`, factored into a shared `core/` function with a steward if needed); acceptance threshold from a helix in a uniform field and box boundaries (the same formula as task B appendix A); TOF resolution from the formula of §4.2 of task B. Each objective carries a `model` field describing the approximation.

### C1.5 Optimizer

`design_search.py search`: Sobol initialization, NSGA-II (simulated binary crossover and polynomial mutation for continuous and integer genes; uniform crossover and random reset for categorical genes; bit flips for slot-enabled bits), constraints through constrained domination. Standard-library implementation; the same seed gives bit-identical results.

### C1.6 Search record and report

`design_search.py report`: Pareto front, best design per topology, search size, F0 model limitations; outputs the record (§5.7; in C1 the confirmation-related fields are empty and marked `fidelity: F0-only`) and a Markdown summary for the user. C1 results are clearly marked "based on analytic models only".

### C1.7 Agent protocol

`skills/hep-detector/references/detector-design-search.md`: the roles and limits of §5.1, the requirement-confirmation flow, the format of the design brief, when to escalate fidelity, how to report (must state search size, confirmation status and robustness).

### C1.8 Closure tests

| Test | Known answer | Pass condition |
|---|---|---|
| DTLZ2 (3 objectives, known Pareto front) | The analytic front | Hypervolume reaches ≥ 95 % of the true value within 2×10⁴ evaluations (the closure-test practice of AID(2)E) |
| Plane placement (N = 6, fixed lever arm, measurement term only) | Best A = 47.66 by exhaustive enumeration on a grid of 1/32 of the lever arm (66.96 for equal spacing; appendix A) | The optimizer finds a configuration with A ≤ 47.66 × 1.01 |
| Structure choice (requirement MDR ≥ 1 TV, given envelope and mass cap) | Must choose a topology with a `magnet-region` and ≥ 3 `tracker-plane`s; all field-free topologies are infeasible | Every feasible Pareto design contains a magnet region and tracker planes; B·L² agrees with the analytic formula |
| Calorimeter depth (requirement ≥ 16 X₀, length cap) | Among the absorber materials, high-Z absorbers give the shortest length | The chosen absorber agrees with the analytic ordering |
| Reproducibility | — | Same search spec and seed: the records of two executions are bit-identical (except timestamps) |

### C1.9 C1 acceptance

- [ ] Tests of the four schemas and the cross-field rules; every kind of invalid-design reason has a test.
- [ ] Realization tests for the six catalogue components; realized specs pass the `element_sim.spec/1` schema (draft or merged version).
- [ ] Every F0 objective agrees with the existing tools or the analytic values of the appendix.
- [ ] All closure tests of C1.8 pass.
- [ ] An independent agent, following the agent protocol, completes from a natural-language requirement: requirement confirmation (a test plays the user), design brief, F0 search, report; the report says "based on analytic models only" and lists the search size.
- [ ] VALIDATION DESIGN-SEARCH-F0; CHANGELOG; release manifest; `check_layering`, `check_packaging`.

---

## 7. Stage C2: simulation evaluation and confirmation (adapter 0.2.0, contracts C3)

### C2.1 F1 and F2 evaluation

`design_search.py evaluate --fidelity F1|F2`: realization → `geant4_run.py` (`element_sim`) → `simreco` → summary; each design evaluation is a logical run, point_id = design hash, role `search-F1` or `search-F2`. Event counts: F1 fixed (declared), F2 per A1.9. Batches run through the existing partition and batch machinery (hep-computing), cached by design hash.

### C2.2 Confirmation and requirement decisions

`design_search.py confirm`: confirmation runs of the finalists (role `confirmation`); the one-sided requirement decisions of §5.6; statistical dominance among finalists; `search_minus_confirmation` and `fidelity_gap`.

### C2.3 Guards and robustness

Convergence gate of the finalists (production cut, maximum step, field accuracy; A1.8); variations (rules of B2.6); tolerance perturbations; flags for regions outside benchmark scopes.

### C2.4 Optional MOBO backend

Ax/BoTorch (qNEHVI), used only in S2, limited to ≤ 4 objectives and ≤ 20 continuous parameters; version recorded in the record and in `adapter.json`; without it, fall back to NSGA-II and note it in the record. A test compares the two on the DTLZ2 closure test.

### C2.5 Contracts C3

The rules of §5.7; the `dependencies.py` re-derivation (spec hash of confirmation runs, no seed overlap); the communication warning. Gated with `strict or _at_least(contract_version, C3)`.

### C2.6 J16: automated-design example

- Requirements: taken from J15's design goals (MDR ≥ 1 TV, σβ/β ≤ 3 %, acceptance threshold ≤ 0.8 GV, calorimeter ≥ 16 X₀, upstream material ≤ 15 % X₀, length ≤ 2 m, a declared mass model); J15's geometry is **not** given.
- Run S0–S4; the report compares the search result with J15: whether a J15-type topology was found, on which objectives it is better or worse, and why (e.g. clustering planes at the ends and centre raises the MDR but worsens resolution where multiple scattering dominates).
- Like J15 it is a synthetic study; the README says it demonstrates the process, not a new detector design (the same positioning as the AIDO and SWGO studies).
- The ion-source and Birks study (previously reserved as J16) moves to J17.

### C2.7 Docs and registration

`docs/researcher-journeys.md`, routing case (reusing the trigger words "design principles and trade-offs" already in hep-detector's description), capability map, capability matrix, adapter docs, protocol.

### C2.8 Compute budget

F0 for 2×10⁴ designs: minutes; F1 about 500 × 10³ events; F2 and confirmation ≤ 5 designs each, event counts per A1.9; calorimeter showers dominate CPU. The actual budget is written into the search spec after a trial.

### C2.9 C2 acceptance

- [ ] F1 and F2 summaries pass task A's consistency tests; the evaluation cache is keyed by design hash, fidelity, catalogue version and program hash.
- [ ] Seeds of confirmation runs appear in no search evaluation (contract test); a table citing search values is rejected; a search record whose label is not `unvalidated` is rejected.
- [ ] Toys of the one-sided requirement decision: probability of "met" at the threshold ≤ 0.05 + 3σ_MC.
- [ ] Winner's-curse toys: on a set of pure-noise designs, the search estimate is significantly optimistic while the confirmation estimate is unbiased (showing why §5.6 is needed).
- [ ] J16 completed, with a report containing search size, confirmation decisions, robustness and the comparison with J15.
- [ ] MOBO backend (if installed) passes the DTLZ2 closure test; without it, fallback noted.
- [ ] VALIDATION DESIGN-SEARCH; CHANGELOG; release manifest; the checks of task A §9.

---

## 8. Contracts and versions

| Object | Location | Version |
|---|---|---|
| `detector-requirements/1`, `detector-design/1`, `catalogue/1`, `design-search-spec/1`, F0, optimizer | `adapters/detector-design/` | adapter 0.1.0 (C1) |
| F1, F2, confirmation, MOBO backend | `adapters/detector-design/` | adapter 0.2.0 (C2) |
| `extension.design_search` and its rules | `contracts/validate.py`, `contracts/dependencies.py` | C3 (minor, gated) |
| Agent protocol | `skills/hep-detector/references/detector-design-search.md` | with the plugin version |

---

## 9. Not done and deferred

| Item | Decision | Reason / trigger |
|---|---|---|
| Letting an LLM alone decide the best design | Not done | No real case does this; decisions must be reproducible |
| Inventing component types during a search | Not done | New components need a realization rule, F0 model and tests; added through a catalogue change |
| Differentiable simulation and differentiable surrogates (the MODE route) | Deferred | Geant4 is not differentiable; differentiable surrogates at point-cloud scale are still immature (arXiv:2310.05673). Trigger: a problem with > 20 continuous parameters and an insufficient F1 budget |
| Cylindrical and non-box geometry, collider detectors | Deferred | `element_sim` has only box elements. Trigger: `element_sim` gains cylindrical elements |
| Cherenkov, RICH, TRD | Deferred | Need optical physics and dedicated reconstruction |
| Reinforcement learning, large neural-network surrogates | Deferred | Data volume and interpretability; NSGA-II and MOBO suffice for up to a few dozen parameters |
| A real cost database | Not shipped | Supplied by the user with sources |

---

## 10. Decisions for the maintainer and residual risks

**To decide:**
1. Owner of the new adapter `detector-design` (proposed hep-detector).
2. Adding one routing line to `skills/hep-detector/SKILL.md` pointing to `detector-design-search.md` (about 120 bytes; quick load has only 931 bytes left), or relying only on the reference and routing cases.
3. Classification of C3 (proposed minor) and hep-computing's agreement to `extension.design_search`.
4. Whether the MOBO backend (Ax/BoTorch) is listed as a tested tool of the adapter.
5. The J16 number (the ion-source study moves to J17).

**Residual risks:**
1. Bias of the F0 models may make the structure search miss good topologies; mitigated by topology diversity in S2 and `fidelity_gap`, but not excluded.
2. Simulation-optimized designs may exploit Geant4 behaviour in unvalidated regions; the convergence gate and variations only partly guard against this, and the label stays `unvalidated`.
3. The placeholder mass and cost models are crude; without a user model they should not be objectives.
4. With more than 4 objectives the Pareto front is hard to read; requirements should express the rest as constraints.
5. Claude's design brief may bring in a bias toward "known instruments"; offset by Sobol random designs and topology diversity, and the report separates the contributions of LLM and random proposals.
6. Compute: F1 and F2 evaluations with calorimeters are expensive; budgets are adjusted after a trial.
7. Some references in this document (GRACE, VI-BRATO) are 2026 preprints whose conclusions are not yet peer reviewed.

---

## 11. Suggested order of work

**C1**
1. Pre-start checks; schemas (C1.1) and catalogue (C1.2).
2. Realization and validity (C1.3); F0 (C1.4), checked against the existing tools.
3. Optimizer (C1.5) and the DTLZ2 and plane-placement closure tests.
4. Record and report (C1.6); agent protocol (C1.7); the remaining closure tests and the independent-agent acceptance; C1.9.

**C2 (after task B is merged)**
1. F1 and F2 (C2.1); confirmation and requirement decisions (C2.2); contracts C3 (C2.5) and toys.
2. Guards and robustness (C2.3); optional MOBO (C2.4).
3. J16 (C2.6); docs and registration (C2.7); C2.9.

---

## Appendix A: Numbers

**Plane-placement closure test** (curvature variance σ_k² = A σ² / L⁴, N = 6, equal weights, measurement term only; exact rational least squares; computed by `design_search_closure.py` in this folder):

| Configuration | A | MDR relative to equal spacing |
|---|---|---|
| Equal spacing (J15) | 66.96 | 1 |
| Two planes each at both ends and the centre (coincident) | 48.00 | 1.181 |
| Best by exhaustive enumeration on a 1/16 lever-arm grid (distinct planes) | 50.34 (0, 3/8, 7/16, 1/2, 9/16, 1) | 1.153 |
| Best by exhaustive enumeration on a 1/32 lever-arm grid | 47.66 (0, 1/32, 7/16, 15/32, 1/2, 1) | 1.185 |
| Continuous limit (N/4, N/2, N/4 clustering) | 256/N = 42.67 | 1.253 |

J15's MDR of 1172 GV becomes about 1389 GV with the best 1/32-grid configuration; but clustered configurations are worse where multiple scattering dominates, which is exactly the trade-off J16 asks the optimizer to handle.

## Appendix B: Sources

- E. Cisbani et al., "AI-optimized detector design for the future Electron-Ion Collider: the dual-radiator RICH case", JINST 15 (2020) P05009, [arXiv:1911.05797](https://arxiv.org/abs/1911.05797)
- AID(2)E collaboration, "AI-Assisted Detector Design for the EIC (AID(2)E)", [arXiv:2405.16279](https://arxiv.org/abs/2405.16279)
- MODE collaboration, "Toward the end-to-end optimization of particle physics instruments with differentiable programming", [arXiv:2203.13818](https://arxiv.org/abs/2203.13818); "Progress in end-to-end optimization of detectors for fundamental physics with differentiable programming", [arXiv:2310.05673](https://arxiv.org/abs/2310.05673)
- Schmidt et al. (MODE), "End-to-end detector optimization with diffusion models: a case study in sampling calorimeters", [arXiv:2502.02152](https://arxiv.org/abs/2502.02152)
- O. Borysov et al., "Longitudinal structure optimization for a high density electromagnetic calorimeter", [EPJ Web Conf. 315, 03006 (2024)](https://www.epj-conferences.org/10.1051/epjconf/202431503006)
- T. Dorigo et al., "Toward the end-to-end optimization of the SWGO array layout", [arXiv:2310.01857](https://arxiv.org/abs/2310.01857)
- J. Hill, H. J. Ryoo, "GRACE: an agentic AI for particle physics experiment design and simulation", [arXiv:2602.15039](https://arxiv.org/abs/2602.15039) (preprint)
- W. Chung et al., "Agentic-AI detector co-design and optimization in vertically-integrated differentiable full simulations", [arXiv:2604.21804](https://arxiv.org/abs/2604.21804) (preprint)
- Retrieved 2026-10-23; authors and journal details to be checked through hep-citations before citing

## Appendix C: Version history

| Version | Content |
|---|---|
| **2026-10-23 (this version)** | **First proposal: three roles, requirements spec, component catalogue and design grammar, F0/F1/F2 multi-fidelity, search separated from confirmation, C3 contract, stages C1/C2, J16** |
