# TASK: Build the `hep-research` Claude Code Plugin for Experimental and Theoretical HEP Research

> **Executor:** Claude (Claude Code, run inside the source repository).
> **Task type:** Multi-session implementation with human review gates.
> **Working language:** English for every file, log, decision record, question, and status report (Section 2.6).
> **Supersedes:** `AMS-02-Research-Plugin-Integration-Task-EN.md` and earlier revisions of this file.

| Revision | Change |
|---|---|
| r1 | Authoring-round specification (scientific requirements, AC01–AC28) |
| r2 | Executable protocol, Claude Code as default host, baseline-script fix, milestone mapping |
| **r3 (this)** | Researcher-centered architecture review: personas and journeys, contested-ownership resolution, layering and shared core library, shared scientific vocabulary (observable spec, dataset records, conventions, levels, normalization kinds), project configuration and private profiles, Claude Code runtime mechanics, versioning, risk register, architecture-review gate, AC29–AC31, T23–T28, English-only reporting |

---

## 0. How to Start (for the human)

1. Copy this file into the source repository as `tasks/hep-research-plugin.md` and commit it.
2. Open Claude Code at the repository root (default `~/.agentic_ai_skills`).
3. Kick off with:

   ```text
   Read tasks/hep-research-plugin.md completely. Follow Section 3 (Session Protocol).
   Start or resume at the milestone recorded in tasks/hep-research/PROGRESS.md
   (start at M0 if it does not exist). Stop at the next human gate and report in English.
   ```

4. Every later session uses the same kickoff prompt. Claude resumes from `PROGRESS.md`.

---

## 1. Mission

Turn the seven existing standalone skills in this repository into **one** portable plugin, `hep-research` ("HEP Research"), that serves **both experimental and theoretical** high-energy physics researchers, including work that connects predictions to measurements.

- **Seven stable core skills:** `hep-analysis`, `detector-response`, `hep-theory`, `hep-statistics`, `hep-computing`, `physics-ml`, `research-communication`.
- **Composable resources (never extra skills):** experiment profiles, theory-domain profiles, tool adapters, a shared core library and contracts, and project-local configuration.
- **AMS-02** as the first deep experiment profile, fully preserved but **optional**.
- **Proof of generality:** a non-AMS experiment added only through the extension contract, a standalone theory benchmark, a theory–experiment comparison, and a published-data comparison that needs no detector internals.

Done means the four mandatory paths (Section 9) run reproducibly, the plugin installs and works natively in Claude Code, the architecture review (Section 7.17) passes, and `VALIDATION.md` gives evidence for AC01–AC31 (Section 10). The plugin is a research assistant and must never imply endorsement by AMS or any collaboration or institution.

---

## 2. Operating Rules (non-negotiable)

### 2.1 Safety and repository hygiene

- Work on branch `feat/hep-research-plugin` (or a git worktree). Never commit to the default branch; never push or open PRs without explicit user approval.
- **Never modify** the seven legacy skill folders, `~/.claude/`, or any installed skill or plugin. Corrections to legacy content are made in the new plugin copy (Section 12).
- Never delete user files. Never install software system-wide. Python dependencies go in a repo-local virtual environment `.venv-hep/` (gitignored).
- No network access by default. Ask before any networked action (documentation or literature fetch, package download, paid model evaluation).
- Never fabricate measurements, data values, citations, internal experiment details, benchmark numbers, proof status, or test results. Synthetic fixtures are labeled synthetic everywhere, including file names and metadata.
- Never put private data, bulk paper caches, model transcripts, or grading rubrics into the distributable plugin.

### 2.2 Evidence labels (use in all docs you write)

`[Confirmed]` verified from user requirements or files you inspected · `[Inferred]` judgment derived from confirmed facts · `[Proposal]` design choice · `[Unresolved]` not yet established · `[To verify]` a tool/host fact you must check before relying on it.
Never describe proposed profiles, adapters, or theory capabilities as existing or validated.

### 2.3 Ask vs. proceed

- **Proceed without asking** on naming, layout, serialization details, test organization, and anything covered by a default in Section 5. Record the choice in `DECISIONS.md`.
- **Stop and ask** only for the conditions in Section 13, or at gates G0, G1, G5.
- When asking, state the decision, options, your recommendation, and what is blocked. Continue unblocked work.

### 2.4 Honesty in reporting

- Every "pass" cites a command, exit code, and environment. Report pass / fail / skip / unverified separately; never hide a failure in an aggregate count.
- Passing software tests does not establish physical validity, a mathematical proof, global statistical coverage, authorization to unblind, or collaboration approval. Say so where relevant.
- Baseline (pre-existing) failures are reported as baseline, distinct from regressions you introduce.

### 2.5 Context management

- Do not read entire ledgers or large references into context when a script can answer (counts, ID sets, diffs). Use `python3`, `jq`, `grep`.
- Read a file before editing it. Inventory before migrating.
- Maintain a todo list for the current milestone. Keep `PROGRESS.md` current enough that a fresh session can resume with no chat history.

### 2.6 Language

- **English is the single working language** of this task: plugin files, docs, code, comments, commit messages, `PROGRESS.md`, `DECISIONS.md`, `VALIDATION.md`, check-run summaries, questions to the user, and every status report.
- Two scoped exceptions, both about plugin *behavior*, not executor reporting: (a) routing test fixtures include Traditional Chinese requests alongside English ones (AC20); (b) the installed plugin's documented runtime behavior is to answer end users in the language they use.

---

## 3. Session Protocol

**At session start**

1. Read this file, `tasks/hep-research/PROGRESS.md`, and `tasks/hep-research/DECISIONS.md` (create both in M0 if missing).
2. Run `git status --short` and `git log -1 --format=%H`. If HEAD differs from the last recorded commit, or the tree contains changes you did not make, record it and check Section 13.
3. Activate `.venv-hep` (created in M0). Confirm the current milestone and its next unchecked step.

**During the session**

- Execute milestone steps in order. Commit at each meaningful sub-step: `hep-research(M<n>): <what>`. Keep **scientific fixes** separate from **relocations/interface changes** (`sci-fix:` vs `move:` prefixes).
- After each step, run the milestone exit checks that are already runnable.

**At session end or at a gate**

1. Run `python3 plugins/hep-research/tools/run_all_checks.py` (once it exists); save its JSON summary under `tasks/hep-research/check-runs/`.
2. Update `PROGRESS.md` (milestone, done steps, next step, blockers) and partial `VALIDATION.md` entries.
3. Commit. Report to the user in English using the template in Section 14.

---

## 4. Fixed Facts (inspection baseline)

Baseline: 2026-10-02 (Asia/Taipei), commit `3e995a49a89fad8e0e9d52130ee1fd93a3a0f4f9`, clean tree. Upstream mirror: <https://github.com/hchouTW/agentic-ai-skills/tree/3e995a49a89fad8e0e9d52130ee1fd93a3a0f4f9>. Re-verify all of these in M0; if anything differs, the repository is authoritative and the migration map records the difference.

- [Confirmed] Source skills: `ams-analysis`, `hep-analysis`, `deep-learning`, `academic-papers`, `academic-diagrams`, `agile-development`, `task-authoring`. README describes copy-based, independent installation.
- [Confirmed] AMS ledger: 60 sources, 183 claims (inventory counts, not fresh verification of every paper).
- [Confirmed] `ams-analysis/SKILL.md`: 95 lines / 16,281 bytes. `hep-analysis/SKILL.md`: 218 lines / 38,172 bytes.
- [Confirmed] No root plugin manifest and no root `LICENSE` at baseline.
- [Confirmed] Theory-relevant references exist (mathematical reasoning, numerical methods, event generation, scientific ML). They are starting material, not a complete theory capability.
- [Confirmed] Existing validators and scripts depend on skill names, resource locations, and cross-references; moving files can break them.

### 4.1 Source → destination map

| Source | Content | Destination / role |
|---|---|---|
| `README.md` | Seven skills, install/validation | Baseline and compatibility docs |
| `ams-analysis/SKILL.md` | AMS tasks, evidence rules, invariants, routing | Split: general methods → core owners; AMS specifics → `profiles/experiments/ams-02`. No eighth core skill |
| `ams-analysis/references/analysis-artifacts.md`, `tests/fixtures/spec_valid.json` | Analysis contract and valid fixture | Measurement extension and legacy converter |
| `ams-analysis/data/sources.json`, `data/claims.json` | Scoped source/claim IDs, verification levels | AMS-owned, namespaced evidence |
| `ams-analysis/data/papers_manifest.json`, `references/source-policy.md` | Acquisition metadata, evidence rules | Profile maintenance and shared evidence conventions |
| `ams-analysis/scripts/audit_analysis_spec.py` | Spec checker | Wrap/migrate under versioned contracts |
| `ams-analysis/scripts/ams_kinematics.py` | Rigidity/momentum/energy conversions | General kinematics → `core/`; experiment interpretation → AMS profile; constants keep provenance |
| `ams-analysis/scripts/validate_response.py`, `validate_covariance.py` | Consistency checks | Shared response/covariance contracts |
| `ams-analysis/scripts/likelihood_limits.py`, `template_fit.py`, `unfolding_diagnostics.py` | Numerical diagnostics with documented limits | `core/` code stewarded by `hep-statistics`; AMS examples stay in profile |
| `ams-analysis/scripts/validate_evidence_ledger.py`, `render_source_index.py` | Ledger validation, generated index | Shared evidence tools |
| `ams-analysis/scripts/validate_skill_bundle.py`, `agents/openai.yaml` | Structure/discovery metadata | Updated validators; host adaptation |
| `hep-analysis/SKILL.md`, `references/12-validation.md` | Analysis, detectors, inference, computing, validation | Redistribute to core owners |
| `hep-analysis/references/27-event-generation.md` | Generation, matching/merging, weights | Physics → `hep-theory`; execution → adapters via `hep-computing` (Section 7.3) |
| `hep-analysis/assets/end_to_end_sample_analysis.py`, `tests/test_end_to_end.py` | Synthetic collider example | Starting point for `synthetic-collider` (no support claim for any named experiment) |
| `deep-learning/SKILL.md`, `scripts/check_split_integrity.py` | PyTorch engineering, split checks | `physics-ml` |
| `deep-learning/references/scientific-machine-learning.md` | Constraints, surrogates, inverse problems | ML/theory/statistics boundaries |
| `academic-papers/references/mathematical-reasoning-and-proof.md` | Assumptions, derivation status, checks | Canonical theory reasoning contract (`hep-theory`) |
| `academic-papers/references/numerical-and-computational-methods.md` | Numerical reliability | `hep-computing` general checks plus domain verification |
| `academic-papers/SKILL.md`, `scripts/check_manuscript.py` | Literature, writing, citations | `research-communication` |
| `academic-diagrams/SKILL.md` | Diagrams, captions | `research-communication` (diagram branch) |
| `agile-development/SKILL.md` | Engineering discipline | References inside `hep-computing` |
| `task-authoring/SKILL.md`, `templates/task-template.md` | Task authoring | Research-task authoring inside `hep-computing` (confirm in M1) |

---

## 5. Decisions and Defaults

Confirm D1–D5 with the user at G0. Until then, proceed with the defaults; they are chosen so confirmation causes no rework.

| ID | Decision | Default `[Proposal]` | Status |
|---|---|---|---|
| D1 | Primary host | **Claude Code** plugin system. Other hosts are outside v1 acceptance; content stays host-neutral | Confirm at G0 |
| D2 | Non-AMS example | Illustrative `synthetic-collider` profile. A named real experiment needs public sources, fixtures, and integration evidence | Confirm at G0 |
| D3 | Theory benchmark | `qed-benchmark`: tree-level e⁺e⁻ → μ⁺μ⁻ via single-photon exchange; declared mass approximation, spin-averaged, coupling convention, validity √s ≫ m_μ and √s ≪ m_Z | Confirm at G0 |
| D4 | Plugin location | `plugins/hep-research/` in this repo; local dev marketplace at repo root | Confirm at G0 |
| D5 | Mandatory environment | Python ≥ 3.10 with `numpy`, `scipy`, `matplotlib`, `sympy` (pinned in `requirements-core.txt`). ROOT, PyTorch, uproot, pyhf, generators, commercial CAS are optional and excluded from mandatory paths | Confirm at G0 |
| D6 | Metadata serialization | JSON (stdlib-parseable); legacy strict-YAML-subset inputs supported via the converter | Finalize in M1 |
| D7 | Test framework | `unittest` (matches source); aggregate runner `tools/run_all_checks.py` emitting JSON | Fixed |
| D8 | Dev tracking location | `tasks/hep-research/` outside the distributable plugin: `PROGRESS.md`, `DECISIONS.md`, `baseline/`, `check-runs/` | Fixed |
| D9 | License | None invented. Local reviewable package only; public release blocked until the user resolves licensing and attribution | Fixed |
| D10 | Plugin components | **Skills only** in v1 (no hooks, MCP servers, background processes, or required subagents); commands only if 5.1 #8 shows a clear benefit | Fixed (Section 7.1) |

### 5.1 Claude Code plugin facts to verify in M0 `[To verify]`

Check current official Claude Code plugin documentation (ask before network access; otherwise inspect the installed CLI, e.g. `claude plugin --help`). Record verified answers with date and source in `docs/architecture.md`. Do not build on an unverified item.

1. Manifest location and required fields (expected: `.claude-plugin/plugin.json` with `name`, `version`, `description`).
2. Skill discovery (expected: `skills/<name>/SKILL.md`, YAML frontmatter `name`, `description`), description length limit, and how installed skills' metadata enters context (always-loaded cost, AC04).
3. Namespacing of plugin skills (expected: `hep-research:<skill>`) — the basis for coexistence with legacy `hep-analysis`.
4. Whether installed plugins are copied to a cache (expected: yes, so nothing outside the plugin root resolves), whether the model is told a loaded skill's base directory, and whether `${CLAUDE_PLUGIN_ROOT}` is available to scripts.
5. Local marketplace format (expected: `.claude-plugin/marketplace.json`) and install/remove commands.
6. Whether a non-interactive validator exists (expected: `claude plugin validate <path>`).
7. Whether headless runs (`claude -p --output-format stream-json`) expose loaded skills and files (needed for AC04/AC20 traces).
8. Whether slash commands are a separate component or merged into user-invocable skills.

If skills cannot read shared resources at the plugin root, use the fallback: a build step that generates per-skill copies of the needed shared resources plus a consistency check (AC05).

---

## 6. Who the Plugin Serves

The architecture is judged by whether these researchers can complete real work without understanding internal routing and without loading irrelevant knowledge. Every journey is traced through skills, profiles, and contracts in `docs/researcher-journeys.md` during M1; mandatory journeys are also executed.

| ID | Persona | Journey | Primary skill → handoffs | Context | v1 evidence |
|---|---|---|---|---|---|
| J1 | AMS cosmic-ray analyst | Time-dependent flux and correlated ratio of two species | `hep-analysis` → `detector-response` → `hep-statistics` → `research-communication` | `experiment:ams-02` | Executed (Path A) |
| J2 | Detector physicist | Subsystem resolution or calibration study (e.g. RICH velocity resolution) | `detector-response` → `hep-statistics` | AMS subsystem modules only | Desk-check + T07 |
| J3 | Non-AMS experimentalist (illustrative) | Corrected angular distribution with its own normalization and response | `hep-analysis` → `detector-response` → `hep-statistics` | `experiment:synthetic-collider` | Executed (Path B) |
| J4 | Analytic theorist | Tree-level calculation with conventions, limits, and independent checks | `hep-theory` (↔ `hep-computing` for numerics) | `theory:qed-benchmark` | Executed (Path C) |
| J5 | Phenomenologist | Fold a prediction into a measurement's observable space and fit an identifiable parameter | `hep-theory` → `hep-statistics` → `research-communication` | theory + experiment profiles | Executed (Path D) |
| J6 | Phenomenologist using published data | Compare a model with a *published* dataset without detector internals | `hep-theory` → `hep-statistics` | Dataset record only; no detector modules loaded | T24 (synthetic record) |
| J7 | Reinterpretation (recasting) | Constrain a model with published efficiencies or likelihoods | `hep-theory` → `detector-response` (parametrized) → `hep-statistics` | Dataset record; optional interchange adapters | Desk-check only |
| J8 | Computational theorist | Convergence study; symbolic vs numerical cross-check | `hep-computing` ↔ `hep-theory` | Run artifact | T14, T15 |
| J9 | Physics-ML researcher | Grouped-split classifier or surrogate with a declared validity domain | `physics-ml` → `hep-statistics` | ML artifact | T16 |
| J10 | Any researcher writing up | Paper section and figures with claim-to-result links and honest status | `research-communication` | Communication artifact | Desk-check |
| J11 | Collaboration member with internal knowledge | Use private calibrations/conditions through a local profile; nothing enters the plugin | Any; via project config | Local profile path | T27 |
| J12 | Researcher in a domain outside v1 (lattice, EFT global fits, CR propagation, …) | Gets general discipline (statistics, computing, derivation status) with an explicit "no validated domain profile" notice | `hep-theory` / `hep-statistics` | None | Routing limited-support cases |

A journey that cannot be traced without a missing field, owner, or contract is an architecture defect to fix in M1 or record as a known limitation.

---

## 7. Target Architecture

### 7.1 Plugin components

| Component | v1 use | Reason |
|---|---|---|
| Skills | Seven core skills | Description-routed entry points |
| Shared resources (`core/`, `contracts/`, `profiles/`, `adapters/`) | Yes, read on demand | Specialization without extra entry points |
| Commands | Optional, only deterministic validators, only if 5.1 #8 confirms a clean mechanism | Convenience, not required |
| Hooks, MCP servers, background processes | No | No implicit activity; nothing to secure or host |
| Subagents | Not required | Handoffs are file-based artifacts |

### 7.2 Core skill ownership

| Core skill | Owns | Typical artifacts | Boundary |
|---|---|---|---|
| `hep-analysis` | Experimental design, estimands, selections, backgrounds, correction chains, physical sources of systematics, measurement review, blinding policy | Measurement spec; selection/background/systematics ledgers | Loads experiment content; never invents experiment conventions; no theory derivations |
| `detector-response` | Signal formation, reconstruction, calibration, alignment, efficiency/resolution, truth matching, detector simulation, data/MC, parametrized response for recasting | Response construction, performance report, conditions provenance | Detector facts come from profiles; inference belongs to statistics |
| `hep-theory` | Models, assumptions, conventions, derivations, amplitudes/rates/predictions, event-generation physics, approximations, validity, theory uncertainty prescriptions, consistency checks | Theory spec, derivation record, prediction, benchmark report | Works with no experiment; running a tool ≠ theory support |
| `hep-statistics` | Likelihoods, frequentist and Bayesian inference, intervals/limits, covariance assembly, model comparison, unfolding/forward folding algorithms, toys, coverage, combinations | Statistical model, fit/posterior artifacts, diagnostics | Never chooses unprovided physics assumptions or correlations; respects theory-error prescriptions |
| `hep-computing` | Scientific software, symbolic/numerical execution, builds, I/O, debugging, performance, manifests, partition/merge, reproducibility, blinding enforcement in outputs, research-task authoring | Code, environment/run manifests, output audits | Execution success ≠ scientific validity |
| `physics-ml` | Classification/regression, generation, surrogates, ML-assisted inference, calibration, domain shift | Dataset/model contracts, training and validation reports | Physics assumptions → theory; inferential validity → statistics |
| `research-communication` | Literature discovery/verification workflow, writing, diagrams, talks, referee replies, handover, packaging | Literature matrix, manuscript, figures/captions | Consumes verified artifacts; never invents results or upgrades derivation status |

**Routing rule:** choose the primary skill by the **deliverable**, not by an experiment name.

- RICH resolution study → `detector-response` + AMS profile. AMS flux design → `hep-analysis` + AMS profile.
- Symbolic derivation → `hep-theory`, no experiment. A theory request that mentions an experiment's *published* data → `hep-theory` with a dataset record, not `hep-analysis`.
- Recasting → `hep-theory` (predictions in the published observable space), handing off to `hep-statistics` for the limit.
- Memory leak in an AMS script → `hep-computing`.
- Outside-v1 domain → the closest core owner with an explicit limited-support notice (J12).

Cross-domain work uses explicit, file-based artifact handoffs (Section 7.14). No coordinator skill, no assumed sibling auto-invocation.

### 7.3 Contested-ownership resolutions

One canonical owner per *definition* and one per *implementation*; they may differ, but neither may be duplicated.

| Topic | Owns the definition | Owns the implementation | Others |
|---|---|---|---|
| Event generation (ME order, PDFs, shower, matching/merging, scale/PDF variations, weights) | `hep-theory` | Execution via adapters: `hep-computing` | Detector simulation: `detector-response`; consumption: `hep-analysis`; variation treatment: `hep-statistics` |
| Unfolding / forward folding | Response matrix: `detector-response` | Algorithms, regularization, coverage: `hep-statistics` (`core/stats`) | Choice of folded vs unfolded comparison: `hep-analysis` + `hep-theory` |
| Systematic uncertainties | Physical sources and evaluation plan: `hep-analysis`; detector components: `detector-response` | Nuisance modeling and correlations in the likelihood: `hep-statistics` (from provided evidence only) | — |
| Theory uncertainties | Prescription (scale envelope, truncation, model alternatives): `hep-theory` | Inferential treatment: `hep-statistics` | Never auto-Gaussianized |
| Covariance | Components from evidence: `hep-analysis`, `detector-response` | Assembly and validation: `hep-statistics` | Missing stays missing |
| Units, physical constants, generic kinematics | Conventions and values with provenance: `hep-theory` | `core/units`, `core/constants`, `core/kinematics` (steward `hep-theory`) | Experiment-specific interpretations live in profiles |
| Binned-data representation and I/O | Semantics from observable specs: contracts layer | `core/binned` (steward `hep-computing`) | Interchange formats via adapters |
| Observable spec, dataset record, conventions vocabulary, compatibility gate | Contracts layer (single canonical location) | `contracts/` | Profiles contribute namespaced vocabulary and transformations as data |
| Blinding | Policy: `hep-analysis` + project config | Enforcement in outputs, logs, caches: `core/blinding` (steward `hep-computing`) | All producers must honor |
| Literature evidence | Ledger content: owning profile namespace | Discovery/verification workflow: `research-communication` | No competing ledgers |
| ML surrogates of physics | Physics and validity domain: `hep-theory` | Training and evaluation: `physics-ml` | Inferential use: `hep-statistics` |
| Feynman and physics diagrams | Physics correctness: `hep-theory` | Rendering and captions: `research-communication` | — |

### 7.4 Layers and dependency directions

| Layer | Contains | Must not contain |
|---|---|---|
| `core/` (shared library) | Units, constants, kinematics, binned data, statistics algorithms, blinding utilities, evidence tools — each module with a steward in `core/OWNERS.json` | Experiment or theory-domain specifics; anything used by only one component |
| `contracts/` | Envelope, typed extensions, observable spec, dataset record, conventions/level/normalization vocabularies, compatibility gate, legacy converter | Profile content |
| Core skills | Entry points, methods, routing, skill-local references/scripts | Mandatory AMS assumptions, internal paths, copies of profiles |
| Experiment profiles | Observables, detector configurations, public methods/evidence, validity periods, dataset records, scoped examples | Duplicate inference engines; undocumented collaboration procedures |
| Theory-domain profiles | Domain conventions, model definitions, approximation regimes, benchmarks, evidence | Mandatory detector or input-file fields; claims of comprehensive coverage |
| Tool adapters | Tool identity/versions, I/O, environment, invocation, error mapping | Ownership of scientific methods; fabricated "installed" status |
| Project config and artifacts (outside the plugin) | Bindings, pins, overrides, local profiles/adapters, blinding config, private evidence, run outputs | Writes into the installed plugin |

Allowed import/reference directions (enforced by `tools/check_layering.py`, AST import scan plus text scan):

```text
core/  contracts/          → stdlib + mandatory environment only
skills/*/scripts           → core, contracts
profiles/*                 → core, contracts; other profiles only if declared in depends_on
adapters/*                 → core, contracts
examples/  tests/  tools/  → anything
```

Rules: `core/` and `contracts/` never import skills, profiles, or adapters. Core skill text and code contain no experiment-specific instructions or hard-coded profile IDs except inside explicitly marked example blocks whitelisted by the check. Code imported by more than one top-level component belongs in `core/` (admission rule; prevents a dumping ground). Experiment and theory selection are **independent axes** (0/1/many each); no experiment is the parent of a theory profile, and no single global experiment/model field exists.

### 7.5 Proposed layout

```text
<REPO>/
├── .claude-plugin/marketplace.json            # local dev marketplace [To verify]
├── tasks/
│   ├── hep-research-plugin.md                 # this file
│   └── hep-research/{PROGRESS.md,DECISIONS.md,baseline/,check-runs/}
└── plugins/hep-research/                      # distributable root
    ├── .claude-plugin/plugin.json
    ├── README.md  VALIDATION.md  requirements-core.txt
    ├── skills/<seven core skills>/SKILL.md  references/  scripts/  templates/
    ├── core/                                  # shared library + OWNERS.json
    │   ├── units/ constants/ kinematics/ binned/ stats/ blinding/ evidence/
    │   └── bootstrap.py                       # resolves plugin root from __file__
    ├── contracts/
    │   ├── schemas/  vocab/  compat/  legacy/  stanzas/  fixtures/
    ├── profiles/
    │   ├── registry.json                      # light index only
    │   ├── experiments/ams-02/
    │   ├── experiments/synthetic-collider/
    │   └── theory/qed-benchmark/
    ├── adapters/
    ├── examples/{projects,ams-flux-ratio,non-ams-measurement,theory-only,
    │             theory-experiment-comparison,published-data-comparison}/
    ├── tools/        # run_all_checks, check_layering, measure_entrypoints, build, relocation tests
    ├── tests/        # unit, contract, routing cases, integration
    └── docs/         # architecture, architecture-review, researcher-journeys, routing-contract,
                      # context-budget, migration, profile-authoring, adapter-authoring,
                      # maintenance, integration-inventory.json, migration-map.csv
```

Final names may change in M1; responsibilities may not.

### 7.6 Profiles

**Kinds.** `experiment` and `theory-domain`. Inside a theory-domain profile, distinguish three things: the *domain* (conventions, methods, approximation regimes), *models* (concrete definitions with parameters, each a theory-spec artifact), and *benchmarks* (verified calculations). Competing models are multiple model artifacts, possibly in one domain.

**Folder templates** (enforced by the registry validator):

```text
experiment profile:   profile.json  index.md  conventions.json  modules/  datasets/
                      evidence/  benchmarks/  tests/  [scripts/]
theory-domain profile: profile.json  index.md  conventions.json  models/  derivations/
                      predictions/  benchmarks/  evidence/  tests/  [scripts/]
```

`index.md` is a short routing map to modules (budget in 7.15). Profile scripts exist only when genuinely experiment- or domain-specific; shared algorithms live in `core/`.

**Two-tier registry.** `profiles/registry.json` holds only ID, kind, version, one-line scope, and path, so reading it is cheap. Full metadata lives in each `profile.json`.

**Local (private) profiles.** A project config may list `local_profile_paths`. They are validated with the same validator, resolved at runtime from the project, never copied into the plugin, never fetched remotely. This is how collaboration members use internal knowledge (J11).

### 7.7 Profile metadata (minimum fields)

```json
{
  "id": "experiment:ams-02",
  "kind": "experiment",
  "version": "1.0.0",
  "scope": "...", "exclusions": ["..."],
  "compatible": {"core": ">=1.0,<2.0", "contracts": ">=1.0,<2.0"},
  "related_skills": ["hep-analysis", "detector-response"],
  "resources": {"index": "index.md", "conventions": "conventions.json",
                "evidence": "evidence/", "datasets": "datasets/"},
  "vocabulary_extensions": {"levels": ["..."], "normalization_kinds": ["..."], "conventions": ["..."]},
  "adapters": {"required": [], "optional": ["adapter:root"]},
  "depends_on": [],
  "evidence_namespace": "ams02",
  "maintainer": "...",
  "capabilities": [
    {"name": "flux-ratio-synthetic", "status": "demonstrated-on-synthetic-data",
     "scope": "...", "tests": ["tests/..."]}
  ]
}
```

Capability status ∈ {`proposed`, `documented`, `demonstrated-on-synthetic-data`, `tested-in-declared-environment`, `unavailable`}, each with a scope. Registration is not proof of support. The validator rejects duplicate IDs, incompatible core/contract versions, missing required resources, template violations, paths escaping the package, and dependency cycles. Optional missing features degrade with a clear message; missing required inputs block only dependent work. Metadata enumerates resources without loading their content.

### 7.8 Project configuration

A project (the researcher's working directory, never the plugin) may contain `hep-research.project.json`:

| Field | Meaning |
|---|---|
| `schema_version`, `plugin_version` | Contract version and accepted plugin version range |
| `experiments` | 0..n bindings: profile ID + pinned version + datasets + conditions/periods |
| `theory` | 0..n bindings: profile ID + pinned version + model IDs + parameter points |
| `local_profile_paths`, `local_adapters` | Private resources validated locally |
| `blinding` | Blinded observables/regions and allowed outputs |
| `private_evidence` | Paths to internal evidence kept outside public ledgers |
| `overrides` | Local values with provenance; never rewrite canonical definitions |
| `artifacts_dir` | Output location (default `./hep-research-artifacts/`) |

**Resolution order for context:** explicit statement in the request → project config → ask, if the task needs a profile and none is determinable → otherwise proceed with no profile. Never guess an experiment from vague wording. A scientifically different model or convention is an explicit variant, not an override. Pin resolved versions in every run manifest; distinguish unknown / not-applicable / not-provided from zero.

### 7.9 Shared scientific vocabulary

This is the backbone that lets experiment and theory artifacts meet without assuming collider or AMS terminology.

| Element | Content | Notes |
|---|---|---|
| **Observable spec** | Quantity type (e.g. differential flux, cross section, ratio, rate), process/species, variables with units and binning, phase space or fiducial definition, level, frame, normalization kind and convention, bin semantics (point / bin-averaged / bin-integrated), optional external IDs (HEPData record, Rivet analysis) | Referenced by both measurements and predictions; the comparison gate checks equivalence or an explicit mapping |
| **Dataset record** | Source evidence ID, observable spec, values, uncertainty components with correlation information, covariance (present / absent / partial), period/conditions, status (published / preliminary / synthetic / user-supplied) | Stands alone; may reference an experiment profile without loading it (J6). Never contains invented values: AMS records carry real values only if they already exist in the source repo with provenance; otherwise metadata only |
| **Binned data** | Edges, values, uncertainty components, covariance references, units | JSON; HEPData/YODA/pyhf JSON/SLHA/LHE are optional adapters, unclaimed unless tested |
| **Conventions block** | Core keys (unit system, ħ = c = 1 or not, metric signature, coupling normalization, scheme, scales, energy variable, …) plus namespaced profile keys (e.g. `ams02:energy_variable`) | Unknown keys are allowed but the gate reports "not comparable" unless a mapping is declared |
| **Level vocabulary** | Core: `parton`, `particle-fiducial`, `detector`, `unfolded` · profile extensions (e.g. `crflux:instrument`, `crflux:top-of-atmosphere`, `crflux:interstellar`) | Transformations between levels are declared by profiles or adapters |
| **Normalization kinds** | Core: `integrated-luminosity`, `exposure` (acceptance × time), `protons-on-target`, `target-exposure` (mass × time), `live-time`, `shape-only` · profile extensions | Removes the collider-only "luminosity" assumption |
| **Units and constants** | `core/units`, `core/constants` with source and edition for every value | Migrated values keep their original provenance; no silent value changes |

### 7.10 Research contracts

A small **common envelope** (contract version, artifact ID/type, objective, resolved bindings with versions, plugin/profile versions, provenance/evidence, input/output refs, validation status, unresolved inputs) plus **typed extensions** used only when applicable:

| Extension | Required content (when applicable) | Owner |
|---|---|---|
| Measurement spec | Observable spec, species/process, period, selections, backgrounds, corrections, normalization kind, systematics, blinding | `hep-analysis` |
| Detector/response | Truth/reco definitions, matrix axes and normalization, inefficiency/flows, included corrections, conditions, provenance | `detector-response` |
| Theory spec / derivation | Model, assumptions, conventions block, order/truncation, parameters/scales, derivation status, validity domain, checks run and not run | `hep-theory` |
| Prediction | Observable spec, parameter point/domain, representation (symbolic / numerical / grid), uncertainties by type, allowed transformations | `hep-theory` |
| Comparison spec | Dataset/prediction bindings, gate result, transformations, correlations/overlaps, inference assumptions, limits | Contracts layer (gate) + `hep-statistics` (inference) |
| Statistical result | Paradigm (frequentist / Bayesian / likelihood-only); likelihood, POIs, nuisances, constraints; frequentist: test statistic, construction (e.g. Neyman, Feldman–Cousins, CLs, asymptotic), coverage checks; Bayesian: priors, sampler, convergence diagnostics; fit status | `hep-statistics` |
| ML artifact | Labels/features, grouped splits, training domain, preprocessing, weights, model hash, calibration, downstream validation | `physics-ml` |
| Computational run | Input manifest/checksums, tool/adapter versions, commands, environment, seeds/tolerances, resources, exit status, output hashes | `hep-computing` |
| Communication | Claim → result links, sources actually read, derivation/result status, figure inputs, limitations | `research-communication` |

Status values `failed`, `unvalidated`, `preliminary`, `synthetic`, `asimov`, `observed`, `user-supplied` survive every handoff. Small conceptual answers need no contract instance; durable results and cross-skill handoffs must carry the needed subset. Derivation records are Markdown with a machine-readable JSON header; predictions are JSON (plus CSV for tables/grids) with explicit units.

### 7.11 Comparison gate (before any mixed inference)

Implemented once in `contracts/compat/`. Check both sides for: quantity, units, variables and binning, phase space/fiducial selection, frame, conventions block, level, normalization kind, included corrections, validity range, uncertainty representation.

- Record every transformation (variable change with Jacobian, bin integration/rebinning, forward folding, efficiency/acceptance/normalization, profile-declared propagation or modulation) and block double counting.
- No point-vs-bin comparison without a defined mapping; no fiducial-vs-inclusive or unfolded-vs-raw equivalence. AMS keeps rigidity / kinetic energy per nucleon and instrument / top-of-atmosphere / interstellar distinctions; every other profile uses its own declared definitions, never AMS defaults.
- Missing covariance stays missing (never silently diagonal). Overlaps and cross-experiment correlations need evidence or a justified, scoped assumption. Scale envelopes, model alternatives, truncation, and numerical error are distinct uncertainty objects.
- If the gate fails: stop the dependent fit, explain the mismatch and what evidence would resolve it, and finish independent checks.

### 7.12 Evidence, adapters, run state

- Shared evidence schema with profile-qualified IDs (`ams02:C017`); preserve source location, scope, verification level/date, formal/preliminary status, supersession, attribution. Public facts, general methods, user-supplied internal information, proposals, unknowns, and newly derived results have distinct statuses. Canonical JSON is the source of truth; indexes are generated.
- Current date ≠ verification date. A paper newer than the ledger is *unverified*, not *nonexistent*. A cached PDF is not evidence that it was read.
- Adapters declare identity, tested versions, environment, I/O contracts, units/conventions, and error mapping. Adapter ≠ profile. Candidate optional adapters (ROOT, uproot, pyhf, HEPData, YODA/Rivet, SLHA, LHE/HepMC, batch schedulers) are `proposed` until executed in a declared environment.
- Failures (nonconvergence, missing tools/licenses, invalid outputs) propagate as explicit statuses. Everything mandatory works offline.

### 7.13 Versioning

SemVer for the plugin, contracts, each profile, and each evidence ledger. **Breaking (major):** removing or renaming fields, changing a convention default, changing numerical results beyond declared tolerance, renaming evidence IDs. Every durable artifact records plugin, contract, and profile versions. Legacy skill copies are frozen snapshots; `docs/maintenance.md` defines how fixes are ported and when comparisons are rerun.

### 7.14 Runtime mechanics in Claude Code

- **Context-resolution stanza.** Each core `SKILL.md` contains a short stanza, generated from the single template `contracts/stanzas/context-resolution.md` by the build step (consistency-checked). It tells Claude to: check the request and project config; read `profiles/registry.json` only if a profile may be needed; then the profile `index.md`; then only the needed modules or dataset records.
- **Handoffs are file-based.** The producing skill writes its artifact to `artifacts_dir` and names the consuming skill and path in its answer. Claude may continue in-session with the next skill, or the researcher resumes later. Handoff chains must terminate (AC20).
- **Script portability.** Scripts locate the plugin root from `Path(__file__).resolve()` via `core/bootstrap.py`; they never depend on cwd and treat `${CLAUDE_PLUGIN_ROOT}` as optional. Outputs go to an explicit `--out` directory, never into the plugin. Scripts emit exit codes and a JSON status, and print actionable messages for missing optional dependencies.
- **No implicit activity.** No hooks, background processes, installation steps, or network calls at runtime.

### 7.15 Loading budget

- Each `SKILL.md`: triggers/exclusions, invariants, short workflow, the context stanza, selective resource routes, handoff rules. Budget **100–180 lines, ≈ 8 KiB**; exceptions documented and reviewed. Moving content into an always-read file is not a reduction.
- Always-loaded metadata: measure the seven descriptions together (5.1 #2) and keep each within the host limit.
- `registry.json` ≤ 2 KiB; each profile `index.md` ≤ 4 KiB as initial budgets.
- Theory-only tasks load no experiment profiles; published-data comparisons load dataset records but no detector modules; AMS tasks load no other experiment profile; simple tasks never load all seven skills.

### 7.16 Architecture risk register

| ID | Risk | Mitigation and check |
|---|---|---|
| R1 | Description routing misroutes (e.g. theory request mentioning AMS → `hep-analysis`) | Exclusions in descriptions; neighboring/negative routing cases; live eval if approved |
| R2 | AMS profile becomes a hidden monolith | Template + index budget + load traces |
| R3 | `core/` becomes a dumping ground | Admission rule; steward per module; layering check |
| R4 | Vocabulary too rigid for future domains | Namespaced extensions; "not comparable" default for unknown keys |
| R5 | Legacy and plugin skills both trigger | Namespacing test; migration doc recommends disabling legacy after acceptance |
| R6 | Host format drift | Host manifest isolated; verified facts dated; validator in checks |
| R7 | Theory capability perceived broader than v1 | Capability matrix; J12 limited-support responses |
| R8 | Collider- or AMS-centric terms leak into core | Level/normalization vocabularies; T26 non-collider fixtures; layering text scan |
| R9 | Private data leaks into the package | Packaging scan for project/private paths; local profiles outside plugin |
| R10 | Always-loaded metadata cost grows | Measured in AC04 |

### 7.17 Architecture review (gate G1)

Produce `docs/architecture-review.md` answering each item with evidence (file, command, or fixture):

1. Every journey J1–J12 traced through skills, contracts, and profiles; gaps fixed or recorded.
2. Every method in the migration map has one definition owner and one implementation owner; Section 7.3 covers all contested topics found.
3. `check_layering.py` passes on the skeleton with a minimal whitelist.
4. No collider-only or AMS-only term is required by any core schema (vocabulary scan + fixtures).
5. Theory artifacts validate with all experiment fields absent.
6. A published-dataset comparison can be specified without any detector module.
7. Project-config fixtures cover 0/1/many experiments × 0/1/many theory contexts and a local profile.
8. Verified host facts support skill access to shared resources, or the fallback is chosen.
9. Always-loaded metadata and entry-point sizes measured against budget.
10. Risk register reviewed; new risks added.

---

## 8. Milestones

Each milestone: complete the steps, pass the exit checks, update `PROGRESS.md`, commit. Stop only at gates or Section 13 conditions.

### M0 — Baseline and release scope

1. Create branch `feat/hep-research-plugin`; create `tasks/hep-research/` with `PROGRESS.md` and `DECISIONS.md`.
2. Record `git log -1`, `git status --short`, OS, `python3 --version`. Create `.venv-hep`, add it to `.gitignore`, record `pip freeze`.
3. Before running tests, grep source scripts and tests for network use (`urllib`, `requests`, `http`, `socket`, API keys). Skip and record any test that would make external calls.
4. Run the baseline with per-command result capture:

   ```bash
   #!/usr/bin/env bash
   set -u
   REPO="${REPO:-$(git rev-parse --show-toplevel)}"
   OUT="$REPO/tasks/hep-research/baseline"; mkdir -p "$OUT"
   SUMMARY="$OUT/summary.csv"; echo "skill,step,result" > "$SUMMARY"
   for skill in ams-analysis hep-analysis deep-learning academic-papers \
                academic-diagrams agile-development task-authoring; do
     if [[ -f "$REPO/$skill/scripts/validate_skill_bundle.py" ]]; then
       (cd "$REPO/$skill" && python3 scripts/validate_skill_bundle.py) \
         > "$OUT/$skill.bundle.log" 2>&1
       echo "$skill,bundle,$?" >> "$SUMMARY"
     else
       echo "$skill,bundle,MISSING" >> "$SUMMARY"
     fi
     if [[ -d "$REPO/$skill/tests" ]]; then
       (cd "$REPO/$skill" && python3 -m unittest discover -s tests -v) \
         > "$OUT/$skill.unittest.log" 2>&1
       echo "$skill,unittest,$?" >> "$SUMMARY"
     else
       echo "$skill,unittest,MISSING" >> "$SUMMARY"
     fi
   done
   cat "$SUMMARY"
   ```

   Extract passed/failed/skipped counts per log into `baseline/summary.md`.
5. Re-verify Section 4 facts by script (line/byte counts, ledger counts and ID sets, absence of manifest/LICENSE).
6. Build `docs/integration-inventory.json` (every tracked file: path, type, size, hash, skill) and the first `docs/migration-map.csv`:
   `source_path,source_commit,section_or_symbol,definition_owner,implementation_owner,destination,disposition(reuse|merge|adapt|retain-outside|retire|new),dependencies,tests,rationale`.
   Record the disposition of caches, worktrees, private artifacts, and transcripts (excluded from distribution).
7. Verify the Section 5.1 facts. List legacy skills under `~/.claude/skills/` read-only.
8. Identify candidate authoritative references for D3 (e.g. the PDG *Review of Particle Physics* cross-section formulae, a standard QFT textbook treatment). Write no formula or number into the plugin yet.
9. Run `task-authoring/scripts/lint_task.py` on this file and record the result; adapt rather than force-fit if its template differs.

**Exit checks:** baseline summary has every skill × step row; inventory covers 100% of tracked files in the seven skills; Section 4 facts re-verified or discrepancies recorded; each 5.1 item marked verified/unverified with source.
**→ GATE G0:** Report baseline, discrepancies, 5.1 findings, and ask the user to confirm D1–D5. Stop.

### M1 — Architecture, vocabulary, and contracts

1. Write `docs/researcher-journeys.md` (Section 6) and trace each journey.
2. Write `docs/architecture.md`: components (7.1), ownership (7.2–7.3), layers and directions (7.4), verified host facts, versioning (7.13), risk register (7.16). Create `core/OWNERS.json`.
3. Write `docs/routing-contract.md`: direct / neighboring / negative triggers per skill, deliverable-based rules, limited-support behavior, handoff chains.
4. Implement the shared vocabulary (7.9) in `contracts/vocab` and `contracts/schemas`, with fixtures including non-collider normalization kinds and profile-namespaced levels.
5. Implement the envelope and typed extensions (7.10), stdlib validator, valid/invalid fixtures per extension.
6. Implement the two-tier registry, profile templates, and validator with negative fixtures (duplicate ID, incompatible version, missing resource, template violation, escaping path, cycle).
7. Implement the project-config schema, resolution order, and local-profile loading (7.8) with 0/1/many fixtures.
8. Define the evidence schema and namespacing rule.
9. Create the plugin skeleton: manifest, seven `SKILL.md` drafts with real descriptions (triggers + exclusions), generated context stanza, local marketplace file. Run the host validator if one exists.
10. Create `tools/run_all_checks.py`, `tools/check_layering.py`, `tools/measure_entrypoints.py`.
11. Write `docs/architecture-review.md` (7.17).

**Exit checks:** all contract/registry/project-config tests pass, including negative fixtures; layering check passes; architecture review complete with no unaddressed item.
**→ GATE G1:** Present the architecture review, journeys, contracts, and skill descriptions. Stop.

### M2 — Shared core and AMS migration

1. Migrate shared numerical/engineering code into `core/` with stewards, preserving each helper's assumptions, supported dimensions, approximations, and coverage limits. Port original tests; record inputs/seeds/tolerances before claiming equivalence. Constants keep their original values and provenance.
2. Build `profiles/experiments/ams-02` from the template with selective modules (species, subsystems, methods, periods, evidence). Migrate all 60 sources / 183 claims with namespaced IDs and a legacy mapping; regenerate indexes. Add `tools/check_ams_ledger_preservation.py` asserting identity, scope, and verification-strength preservation (or listing justified record-level changes).
3. Preserve AMS distinctions: rigidity vs momentum vs kinetic energy per nucleon, charge-sign source, conditional efficiency, acceptance/exposure/live time, correlated ratios, non-Gaussian tails, low counts, time-dependent conditions, all species/range/period restrictions. A method from one paper is not a universal AMS rule.
4. Add AMS dataset records as metadata (observable specs + evidence IDs); include numeric values only if they already exist in the source repo with provenance.
5. Implement the legacy AMS spec converter; test valid, invalid, incomplete, and legacy inputs.
6. Apply Section 12 corrections in the plugin copy, each as a `sci-fix:` commit with a regression test.
7. Build **Path A**.

**Exit checks:** ledger preservation passes; migrated-helper regressions pass or differences are justified; Path A passes; AMS tasks load only relevant profile sections; layering check still passes.

### M3 — Theory capability and extension proof

1. Build `profiles/theory/qed-benchmark` from the template (D3). Read an authoritative reference; record its exact location, the calculation, assumptions, and conventions. Then derive (symbolically with SymPy where useful) and implement the prediction and run independent checks: units, normalization, known limits, angular dependence, symmetry, analytic vs numerical integration with a convergence/tolerance study. Label derivation status correctly (analytical derivation ≠ formal proof; numerical agreement ≠ proof). Mark inapplicable fields as inapplicable. If no authoritative reference can be read, stop verification claims and ask (Section 13).
2. Build **Path C** with no experiment profile, no detector/blinding fields, no GPU, no commercial CAS.
3. Build `profiles/experiments/synthetic-collider` **only** through profile resources, registry metadata, and adapter/project bindings. Do not edit core skill text, generic validators, `core/`, or `contracts/` (vocabulary extensions go in the profile). Save the diff as AC10 evidence. Label it illustrative. Its synthetic generator must not import theory code.
4. Build **Path B**.
5. Verify AMS optionality: run Paths B and C and generic statistics/computing tests with the AMS profile removed from the registry and absent from a temp copy.

**Exit checks:** Paths B and C pass; AMS-absent run passes; AC10 diff touches no core, contracts, or skill files.

### M4 — Comparison and supporting integration

1. Implement the comparison gate (7.11) and composition diagnostics.
2. Build **Path D** and the published-data comparison example (J6, T24) using a synthetic dataset record shaped like a published one.
3. Implement detector/ML/communication handoffs exercised by Section 11 tests.
4. Implement the local partition/merge/recovery example: manifest-based chunks, no duplicate events or chunks on resubmission, missing work detected, merged and single-run results agree within declared tolerance. Automatic resubmission only with a configured maximum-attempt limit; absent config means no retries; repeated identical failures stop with retained state.
5. Run all Section 11 tests mapped to M4.

**Exit checks:** Path D and T24 pass; every negative composition/compatibility fixture fails with an actionable message; failure statuses propagate downstream.

### M5 — Packaging and evaluation

1. Copy the plugin to a temp path containing spaces, outside the repo, with no symlinks; run all checks from there with a different cwd.
2. Measure entry points, always-loaded metadata, registry and index sizes against 7.15.
3. Routing tests in `tests/routing/cases.json`: ≥ 3 cases per skill (direct, neighboring-domain, negative), one case per journey J1–J12, AMS-mentioning computing requests, theory with no experiment, recasting, out-of-v1 domains, underspecified cross-experiment requests; English and Traditional Chinese. Static check: descriptions cover triggers and exclusions. Live check via headless Claude Code only with user approval (paid model calls); capture loaded skills/files as traces.
4. Packaging scan: no private paths, project data, caches, or transcripts in the plugin.
5. Write `README.md` (quick start with example prompts per persona, install/remove, environments, offline behavior) and the capability matrix.
6. **→ GATE G5:** native install test. Ask the user to run (or approve you running) the verified local-marketplace install, then confirm discovery, invocation of a namespaced skill, profile-resource access, coexistence with legacy skills, and clean removal. Record host name and version.

**Exit checks:** relocation passes; budgets met or exceptions documented; host test recorded; no install step overwrote legacy skills.

### M6 — Handover

1. Complete `VALIDATION.md`: for AC01–AC31 → date, commit, environment, commands, inputs, seeds/tolerances, artifacts, result (pass/fail/skip/unverified), limitations. Include load traces and exclusions.
2. Write `docs/profile-authoring.md` (templates, vocabulary extensions, evidence, tests, capability states), `docs/adapter-authoring.md`, `docs/maintenance.md` (porting fixes, rerunning comparisons, schema migration, versioning), `docs/migration.md` (legacy coexistence, disabling legacy skills, rollback).
3. Final `run_all_checks.py`; report remaining limitations and unresolved external conditions with their exact effect.

**Exit checks:** every AC has evidence or an explicit non-pass status with reason; no release-critical failure hidden.

---

## 9. Mandatory End-to-End Paths

| Path | Required work | Success evidence |
|---|---|---|
| **A — AMS analysis (J1)** | AMS profile; synthetic charged-particle flux and correlated ratio (two species, rigidity bins, ≥ 2 time periods); selection/period, efficiency, `exposure` normalization, response, inference, covariance, closure, short report | Reproducible numbers/figures/report; legacy conventions and evidence IDs preserved; no unrelated profiles loaded |
| **B — Non-AMS measurement (J3)** | `synthetic-collider`: synthetic e⁺e⁻ → μ⁺μ⁻ angular distribution in cos θ bins at fixed √s, `integrated-luminosity` normalization, own efficiency and smearing response; measure the corrected distribution | Added via extension contract only; independent expected values; explicitly illustrative |
| **C — Standalone theory (J4)** | `qed-benchmark`: assumptions, conventions block, derivation record, differential and integrated prediction with units, authoritative reference, independent symbolic/numerical check | Analytical + numerical artifacts with status and validity; zero experiment resources loaded |
| **D — Theory–experiment comparison (J5)** | Bind C's prediction to B's measurement; gate checks level/units/phase space/binning; forward-fold the prediction through B's response; fit an identifiable parameter (default: normalization scale μ, truth μ = 1); injection tests at μ = 1 and μ ≠ 1 (Asimov + toys) | Contract trace prediction → folded expectation → inference; closure passes; mismatched variants rejected; no "new physics" claim |

All four: documented commands, declared environment, labeled synthetic/Asimov/observed status, independent expected values or references, short report.

---

## 10. Acceptance Criteria

Verified in `VALIDATION.md`. "M" = milestone where evidence is produced.

| ID | Criterion (summary — full intent from Sections 2, 6, and 7 applies) | M |
|---|---|---|
| AC01 | Traceable integration: every incorporated file/record has source path + commit or is marked new; exclusions and scientific changes have reasons and tests; legacy skills untouched | M0, M2, M6 |
| AC02 | Seven core skills independently discoverable with uses, exclusions, owned artifacts, handoffs; profiles never add top-level skills or a coordinator | M1, M5 |
| AC03 | Layer separation: no mandatory experiment assumptions, internal paths, or hard-coded AMS logic in core skills, `core/`, or `contracts/` | M1, M2 |
| AC04 | On-demand loading: entry-point lines/bytes, always-loaded metadata, registry/index sizes, and real traces recorded; budgets met or reviewed exceptions; theory/computing tasks load no experiment profiles | M5 |
| AC05 | Canonical ownership: one definition owner and one implementation owner per method; references and generated resources consistent; legacy copies documented as snapshots | M2, M5 |
| AC06 | Profile validation incl. rejection fixtures (duplicate ID, incompatible version, missing resource, template violation, escaping path, cycle) | M1 |
| AC07 | Independent composition: 0/1/many experiments × 0/1/many theory contexts; explicit bindings; actionable conflict diagnostics; overrides keep provenance | M1, M4 |
| AC08 | AMS depth: 60 sources / 183 claims preserved (or justified record-level changes); namespaced mapping and indexes consistent; species/detector/time-dependent/rare-event coverage kept | M2 |
| AC09 | AMS optional: theory-only, non-AMS, and generic paths work without the AMS profile; AMS workflows load selectively | M3 |
| AC10 | Extension proof: second experiment added without changes to core skills, `core/`, `contracts/`, validators, or algorithms; diff recorded; labeled illustrative | M3 |
| AC11 | Bounded theory capability: assumptions, conventions, order, validity, derivation status, authoritative source actually read, independent checks, meaningful artifact | M3 |
| AC12 | Theory independence: no experiment profile, detector/data/blinding fields, commercial license, or GPU; numerical corroboration not reported as proof | M3 |
| AC13 | Versioned contracts accept valid and reject invalid combinations; legacy AMS spec readable/convertible with regression tests and explicit errors | M1, M2 |
| AC14 | Observable compatibility gate before mixed inference; mismatches fail or need explicit valid conversion; no double counting | M4 |
| AC15 | Uncertainty and combinations: no silent independence or invented covariance; no auto-Gaussianized envelopes; positive and negative multi-experiment fixtures | M4 |
| AC16 | Four paths reproducible with reports, labeled synthetic data, independent references | M2–M4 |
| AC17 | Supporting cases: low/zero counts, response inefficiency, correlated ratios, time-dependent exposure, unchanged integral with changed shape, ML group leakage/domain limits, theory conventions/checks | M2–M4 |
| AC18 | Numerical/migration regression: original tests pass where applicable; seeds/tolerances recorded; algorithm fixes separated from moves | M2 |
| AC19 | Failure propagation and bounded recovery (max-attempt limit, tested stopping) | M4 |
| AC20 | Route by deliverable, not experiment name; per-skill positive/neighboring/negative cases and one case per journey; English + Traditional Chinese; handoffs terminate; no nonexistent dispatch APIs | M5 |
| AC21 | Evidence integrity: no fabrication; private evidence separate; legitimate new sources/calibrations usable with provenance; missing ledger entries ≠ blanket refusal | M2, M5 |
| AC22 | Section 12 contradictions fixed with regressions; blinding preserved across plots/logs/caches/reports; weight/normalization conventions; synthetic/Asimov/observed distinct | M2 |
| AC23 | Adapter honesty: claimed adapters have executable tests in a declared environment; unavailable or proposed ones labeled | M3, M5 |
| AC24 | Portable package (path with spaces, no repo/cwd/symlinks) and native Claude Code install/discovery/invocation/resource access/removal recorded | M5 |
| AC25 | Legacy coexistence (namespaces, no overwrite) and isolated project state | M5 |
| AC26 | Authoring/maintenance guides; reproducible checks for source updates, schema migrations, adapter changes; no untested names advertised | M6 |
| AC27 | Honest capability matrix per capability/profile/adapter/environment; missing mandatory paths or host test block completion | M5, M6 |
| AC28 | Complete handover with all deliverables and AC evidence; unresolved external conditions and their effect recorded | M6 |
| **AC29** | **Architecture conformance:** `check_layering.py` enforces 7.4 directions and the no-hard-coded-profile rule; every `core/` module has a steward; admission rule respected; Section 7.17 review complete | M1, M5 |
| **AC30** | **Researcher-journey coverage:** J1–J12 traced in `docs/researcher-journeys.md`; mandatory journeys executed; desk-checked journeys have no unresolved owner/contract gap or are listed as known limitations; out-of-v1 domains get explicit limited-support behavior | M1, M5 |
| **AC31** | **Shared scientific vocabulary and interoperability:** observable spec, dataset record, conventions/level/normalization vocabularies are extensible by profiles without core edits; non-collider normalization validates; a published-data comparison runs without detector modules; interchange adapters are unclaimed unless tested | M1, M4 |

---

## 11. Targeted Test Matrix

| ID | Test | Required observation | M |
|---|---|---|---|
| T01 | Duplicate profile ID / incompatible version / missing resource | Precise error; dependent work does not proceed | M1 |
| T02 | Dependency cycle / package-escaping path / template violation | Deterministic failure naming the offender | M1 |
| T03 | No experiment; multiple competing theory models | Theory task runs; bindings keep distinct assumptions | M4 |
| T04 | Two illustrative datasets, same observable, declared shared covariance | Valid joint result matches an independent small reference | M4 |
| T05 | Datasets with overlapping auxiliary measurement | Requires joint treatment or limited comparison; never multiplies likelihoods silently | M4 |
| T06 | AMS and non-AMS IDs with the same local name | Namespaces preserve identity; correlation needs explicit mapping | M4 |
| T07 | Response containing inefficiency/acceptance | Matrix convention validated; duplicate correction caught | M4 |
| T08 | Prediction at wrong level/units/binning | Rejected, or documented conversion applied and independently tested | M4 |
| T09 | Missing covariance; theory envelope | Status preserved; nothing invented or Gaussianized | M4 |
| T10 | Low/zero counts; correlated ratios | Matches independent references and stated limits | M2 |
| T11 | Time-dependent exposure/conditions | Periods and weights match; no equal split of total live time | M2 |
| T12 | Unchanged systematic integral, changed shape | Shape change detected without claiming propagation failed | M2 |
| T13 | Theory convention/approximation mismatch | Reported, not silently reconciled | M3 |
| T14 | Analytical result checked numerically | Derivation status separate from finite-domain corroboration; tolerances recorded | M3 |
| T15 | Numerical refinement / alternative calculation | Stability within tolerance; termination ≠ convergence | M3 |
| T16 | ML group leakage; surrogate extrapolation | Overlap detected; domain limits reported; AUC alone insufficient | M4 |
| T17 | Newer or inaccessible literature | Marked unverified, not nonexistent; actual level read preserved | M2 |
| T18 | Blinded values via plots/ratios/logs/caches | Masked values absent from outputs | M2 |
| T19 | Legitimate new calibration vs outcome-driven tuning | Former accepted with provenance; latter flagged, no blanket refusal | M4 |
| T20 | Missing tool / failed fit / solver failure | Downstream artifacts keep failed/unexecuted status | M4 |
| T21 | Local chunk resubmission and merge | No double counting; missing work detected; tolerance agreement | M4 |
| T22 | Install, relocation, removal, legacy coexistence | Only packaged resources used; old skills usable; project state separate | M5 |
| **T23** | Layering violation fixtures (core imports a profile; hard-coded AMS ID in core skill text) | `check_layering.py` fails naming file and line | M1 |
| **T24** | Published-data comparison via a synthetic dataset record | Gate and inference run; load trace shows no detector modules | M4 |
| **T25** | Unknown or namespaced convention keys on the two sides | Gate reports "not comparable" unless a declared mapping exists | M1 |
| **T26** | Non-collider normalization kinds (`exposure`, `protons-on-target`, `target-exposure`) | Measurement specs validate with no luminosity field | M1 |
| **T27** | Private local profile via project config | Validated and usable; absent from the plugin and packaging scan | M4 |
| **T28** | Bayesian vs frequentist statistical results | Bayesian requires priors and sampler diagnostics; frequentist requires construction and coverage info; neither mislabeled as the other | M4 |

---

## 12. Known Source Defects to Correct (in the plugin copy only)

| Source issue | Correction | Regression |
|---|---|---|
| HEP entry point equates unchanged systematic yields with missing propagation | Check shape, migration, sensitivity | T12 |
| AMS artifact docs deny YAML parsing although a strict subset is implemented | Align docs/validators/fixtures; reject unsupported YAML features explicitly | Contract fixtures |
| Source policy treats post-verification-date citations as likely nonexistent | Classify as unverified; prefer primary-source checks | T17 |
| Fixed-date wording conflates host date with source verification date | Keep current, publication/data-taking, and verification dates distinct | Evidence schema tests |
| Theory references route scientific inference to writing instead of statistics | Repair handoffs: derivation → `hep-theory`, inference → `hep-statistics`, explanation → `research-communication` | Routing cases |

During refactoring never silently: clip negative bins, repair covariance/response matrices, invent correlations, or change cuts/weights/binning/bounds/constants. Preserve signed generator weights and production normalization where applicable, and do not apply them to unrelated flux problems.

---

## 13. Stop / Escalation Conditions

Stop the affected thread, record it in `PROGRESS.md`, continue unblocked work, and ask the user (in English) when:

1. HEAD or the working tree differs from the recorded state with changes you did not make that touch files being migrated.
2. An action would modify legacy skills, `~/.claude/`, installed plugins, or anything outside the repo; or push/publish.
3. Network access, package download, or paid model evaluation is needed.
4. No authoritative theory reference can be read for D3 → benchmark claims stay `unverified`.
5. A scientific choice (convention, correlation, physics assumption) is not determined by sources or user input.
6. The same check still fails after three materially different fix attempts.
7. A verified Claude Code fact (5.1) contradicts this architecture in a way that changes scope.
8. An architecture-review item (7.17) cannot be satisfied without changing the seven-skill design or the established direction.
9. Licensing/attribution blocks something the user asked to distribute.

Do **not** stop for minor naming/layout choices; decide and log them.

---

## 14. Status Report Template (English, at every gate and session end)

```text
Milestone: M<n> — <name>   Commit: <hash>   Branch: feat/hep-research-plugin
Done this session: <steps>
Checks: pass <n> / fail <n> / skip <n> / unverified <n>   (run: tasks/hep-research/check-runs/<file>.json)
Baseline failures (pre-existing): <list or none>
New failures/regressions: <list or none>
Architecture findings (new risks, ownership changes, journey gaps): <list or none>
Decisions made (logged in DECISIONS.md): <list>
Blocked / needs your input: <question, options, recommendation, what is blocked>
Next step: <milestone.step>
```

---

## 15. Out of Scope

- Comprehensive coverage of every theory field or experiment in v1 (EFT, lattice, pQCD, flavor, cosmic-ray propagation, dark-matter phenomenology, etc. are future domains only).
- Separate top-level skills per experiment, model, particle, subsystem, tool, or workflow stage; a mandatory coordinator skill.
- Access to internal experiment software, conditions, triggers, calibrations, private theory code, commercial CAS licenses, or unpublished information.
- Operating detector hardware, DAQ, or slow control (user-supplied logs may be analyzed).
- New MCP servers, hooks, cloud services, databases, vector search, autonomous multi-agent frameworks; marketplace publication; remote profile fetching.
- Extra ML frameworks or broad MLOps without a demonstrated need.
- Deleting or replacing original skills, altering user installations without approval, submitting scientific results.

---

## 16. References

- Task format: `task-authoring/SKILL.md`, `task-authoring/templates/task-template.md`, `task-authoring/references/acceptance-criteria.md`, `task-authoring/references/task-quality-checklist.md`, `task-authoring/scripts/lint_task.py`.
- AMS: `ams-analysis/SKILL.md`, `references/source-policy.md`, `references/analysis-artifacts.md`, evidence/checker paths in 4.1.
- HEP analysis: `hep-analysis/SKILL.md`, `references/12-validation.md`, `references/27-event-generation.md`.
- Theory and numerics: `academic-papers/references/mathematical-reasoning-and-proof.md`, `academic-papers/references/numerical-and-computational-methods.md`.
- Scientific ML: `deep-learning/references/scientific-machine-learning.md`.
- QED benchmark: an authoritative source actually read during M3; record its exact location and the checks performed. This task intentionally contains no unchecked formula or benchmark value.
- Community interchange formats (HEPData, Rivet/YODA, pyhf JSON, SLHA, LHE/HepMC): consult their official specifications only when implementing the corresponding optional adapter; record version and source.
- Host: current official Claude Code plugin documentation, verified in M0 and cited in `docs/architecture.md`.
