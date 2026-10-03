# TASK: Reinforce `hep-statistics` to cover experimental HEP statistical analysis in breadth and depth

> **For Claude (agent):** This file is an executable work order. Read it fully before changing any file. Follow the
> Execution Rules, finish Phase 0 before any task, work through the tasks in the stated order, and end with the Final
> Report. Unless noted otherwise, every path is relative to `plugins/hep-research/`. Suggested location in the
> repository: `tasks/hep-research/stats-reinforcement/TASK.md`.

> **Revision r2 (2026-10-03).** Checked against `main` at `dbda2aa` (PR #12 merged) before execution. Changes from
> r1 are listed in §10 and marked `(r2)` in place; everything else is unchanged.
>
> **Revision r1 (2026-10-03).** Written from an inspection of the uploaded ZIP `hep-research-main.zip` (commit not
> recorded in the ZIP; it already contains the validation-gap audit fixes listed in `CHANGELOG.md`, "Unreleased").
> Evidence labels follow `tasks/hep-research-plugin.md` §2.2: `[Confirmed]` read in the repository or reproduced,
> `[Inferred]` a conclusion drawn from confirmed facts, `[Proposal]` a design choice open to change, `[To verify]` a
> fact (citation, tool behavior) that must be checked before it is written into the plugin.

---

## 0. Context

| Item | Value |
|---|---|
| Repository | <https://github.com/hchouTW/hep-research> |
| Plugin / contracts version | `0.1.0` (`.claude-plugin/plugin.json`) / `1.0.0` (`contracts/__init__.py`) `[Confirmed]` |
| Skill under work | `skills/hep-statistics/` (SKILL.md 54 lines, 6,777 B; description 1,014 of 1,024 chars) `[Confirmed]` |
| Implementation it stewards | `core/stats/` (7 modules, standard library only), `skills/hep-statistics/scripts/` (2 scripts), `adapters/pyhf-combine/` `[Confirmed]` |
| Authoring baseline | Linux, Python 3, NumPy 2.4.4, SciPy 1.17.1, pyhf **not** installed: `tests/core` 283 tests OK (2 skipped); `tests/skills/hep_statistics` OK `[Confirmed]` |
| Execution baseline (r2) | `dbda2aa`, Linux 6.18, Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1, pyhf 0.7.6 installed in `.venv-hep` after approval (Q1); ROOT and Combine not installed. Full suite 1094 run, 0 failures, 59 skipped; contracts 114 OK; AMS-02 258 OK; `run_all_checks` all pass except `ams_ledger_preservation` (skip: legacy ledger not fetched) `[Confirmed]` |

### 0.1 What already exists (do not rebuild)

`[Confirmed]` by reading the files:

- **Guardrails** in `skills/hep-statistics/SKILL.md`: declared paradigm, named and validated approximations, missing
  covariance stays missing, no likelihood multiplication across overlapping data, comparison gate before mixed
  inference, Asimov/toy closure before observed claims, `failed`/`not-run` propagation.
- **References** (`skills/hep-statistics/references/`):
  - `likelihood-fitting.md`: binned/unbinned/extended likelihoods, identifiability, RooFit checks, a pull convention, a GoF caution, and a verified RooFit walkthrough.
  - `inference-recipes.md`: q0/q_mu/q̃_mu, CLs tail conventions, toys and coverage, a short Bayesian checklist.
  - `statistical-tools.md`: pyhf modifiers, a Combine datacard checklist, the ROOT 6.40 `--strictBounds` note, cross-backend verification.
  - `astroparticle-statistics.md`: Li & Ma, sky-scan trials, forward folding.
  - `statistical-inference-for-physics.md`: inference review questions and claim calibration.
- **Executable diagnostics** in `core/stats/`:
  - `likelihood_limits.py`: profile limit and significance, multibin, profile FC, profile CLs, shape limit, Berger–Boos Neyman limit and coverage scan.
  - `poisson_diagnostics.py`: exact limits, Garwood, FC, CLs with Cousins–Highland.
  - `statistical_toys.py`: boundary, template-stat, D'Agostini scan, Barlow–Beeston-lite, ratio toys.
  - `template_fit.py`: full and weighted Barlow–Beeston.
  - `unfolding_diagnostics.py`: Tikhonov/TSVD/D'Agostini, closure, fold-compare, L-curve/GCV/LOO, response covariance, non-parametric fold.
  - `validate_covariance.py` and `validate_response.py`.
- **Adapter** `adapters/pyhf-combine/adapter.json`: pyhf 0.7.6 and CMS Combine 11.1.0 are both
  `demonstrated-on-synthetic-data`; pyhf matches an independent HistFactory likelihood
  (`tests/adapters/histfactory_reference.py`).
- **Neighbouring content owned by other skills:**
  - `skills/hep-analysis/references/systematics.md`: source inventory, rate/shape/MC-stat types, "small postfit impact alone does not justify removal", "freezing groups is a diagnostic".
  - `skills/hep-analysis/references/histograms-efficiencies.md`: Wilson, Clopper–Pearson and Bayesian efficiency intervals.
  - `skills/physics-ml/references/scientific-machine-learning.md`: SBI coverage, simulator mismatch.

### 0.2 Why this task exists

The skill is strong as a **reviewer** (guardrails, claim calibration) and its `core/stats` diagnostics are well tested.
It is thin as a **working toolkit** for the parts of an experimental analysis where most statistical effort is spent.
It also contains one scientific error and one structural inversion. Findings, each reproduced in Phase 0:

| # | Finding | Kind | Evidence |
|---|---|---|---|
| F1 | `astroparticle-statistics.md` says Li & Ma is asymptotically equivalent to `Z = sqrt(2) * sqrt(-2 ln(lambda))`. The correct statistic is `S = sqrt(-2 ln lambda)`; the `sqrt(2)` belongs inside, in front of the log sum. The reference and the docstring of `skills/hep-statistics/scripts/li_ma_significance.py` also say the formula "does not require large counts" / "remains valid at low counts". Its Gaussian reading rests on Wilks asymptotics. | scientific error, method-claim gap | `[Confirmed]` text. `[Inferred]`, computed while authoring: at `N_on=4, N_off=2, alpha=0.25` the asymptotic p = 6.65e-3, a toy-calibrated p (plug-in background, 2e5 toys, seed 1) ≈ 9.0e-3, and the exact conditional (binomial) p = 1.696e-2. |
| F2 | The only generic usage guide to `core/stats` is in the **optional** AMS-02 profile: `profiles/experiments/ams-02/modules/methods/statistical-diagnostics.md` (what each subcommand does, decision rules, "Not implemented", failure modes) and `inference-and-unfolding.md`. The owner skill only says "run each with `--help` first". Without that profile loaded (the context-resolution stanza forbids loading an unrelated experiment), a non-AMS user has no decision rules for these tools. The AMS module also states an exit-code convention (0 or 2) that `template_fit.py` no longer follows (it exits 1 on a failed fit), and repeats several failure-mode lines. | layering inversion, stale docs | `[Confirmed]` |
| F3 | No executable or reference workflow for **post-fit nuisance diagnostics**: pulls/constraints table, pre/post-fit impacts, ranking, grouped uncertainty breakdown, NP correlation review. Only principles exist (`systematics.md`, `likelihood-fitting.md`). | capability gap | `[Confirmed]` by grep: no impact, ranking or breakdown tool in `core/`, `skills/hep-statistics/` or `adapters/` |
| F4 | **Likelihood model construction for systematics** is spread over two skills and misses interpolation-code semantics: pyhf code 1 vs code 4 normsys, histosys interpolation, Combine `lnN`/`shape`. It also misses two-point and one-sided systematics, envelope-to-nuisance rules, and smoothing and pruning criteria tied to diagnostics. The code-4 vs exponential difference already caused a wrong cross-check once (PR #1, commit message of the pyhf shape cross-check). | content gap | `[Confirmed]` |
| F5 | **Look-elsewhere** is described (Gross & Vitells cited; an astroparticle `1-(1-p)^N_eff` bound) but no tool computes a global p-value for a scan. | capability gap | `[Confirmed]` |
| F6 | No expected-sensitivity formulas: Asimov discovery significance with and without background uncertainty. No executable goodness-of-fit, and no model-comparison guidance (nested vs non-nested, information criteria, Bayes factors). | capability gap | `[Confirmed]`: grep for `Z_A`, "expected significance", "Bayes factor" in `skills/hep-statistics` finds nothing |
| F7 | **Bayesian** inference is "contract checks only; no sampler run" (`docs/capability-matrix.md`). No convergence-diagnostic code, no prior-sensitivity procedure. | capability gap | `[Confirmed]` |
| F8 | **Unbinned weighted fits / sWeights**: `likelihood-fitting.md` says only that sWeights "need suitable methods". | content gap | `[Confirmed]` |
| F9 | **ML-assisted inference validity** (classifier-output templates, neural likelihood ratios, NSBI, SBI posteriors) is assigned to `hep-statistics` by `tasks/hep-research-plugin.md` §7.2/§7.3, and routing case `ml-neighbor-1` expects `hep-statistics`, but the skill has no content on it. | ownership-content gap | `[Confirmed]` |
| F10 | No guidance on **publishing likelihoods** (full pyhf JSON / patchsets on HEPData, simplified likelihoods, what covariance to publish) from the producer side. | content gap | `[Confirmed]`: "simplified likelihood" has no hit in the plugin |
| F11 | `statistical-result` (`contracts/schemas/ext_statistical_result.json`) has no field for local vs global significance and trials method, expected bands, uncertainty breakdown method, or GoF. A scan result without a global p-value therefore cannot be flagged. | contract gap | `[Confirmed]` |

### 0.3 Design constraints to preserve (no regressions allowed)

- **Ownership** (`tasks/hep-research-plugin.md` §7.2–7.3):
  - Physical sources of systematics belong to `hep-analysis`.
  - Nuisance modeling and correlations in the likelihood belong to `hep-statistics`, from provided evidence only.
  - Training and evaluation of ML models belong to `physics-ml`; inferential use belongs to `hep-statistics`.
  - Theory-uncertainty prescriptions belong to `hep-theory`, and are never auto-Gaussianized.
- **"Diagnostics, not frameworks."** `core/stats` modules state they are not statistics frameworks. Framework-level
  work (many-NP shape models, workspace combination) is done through the pyhf/Combine adapter, not reimplemented.
- **`core/` admission rule** (`core/OWNERS.json`): code enters `core/` only if more than one top-level component uses
  it. New single-consumer code goes in `skills/hep-statistics/scripts/` or adapter assets.
- **Layering** (`tools/check_layering.py`): no experiment names outside `<!-- example -->` blocks in skill, core or
  contract text.
- **Budgets** (`tools/measure_entrypoints.py`): SKILL.md ≤ 8,192 B and ≤ 180 lines; description ≤ 1,024 chars.
- **DECISIONS M6-02.** Generic passages in AMS modules are not deleted, because they are interleaved with ledger
  citations; the owner's text takes precedence. Changing this needs a new decision record (see S02).
- Synthetic/Asimov/observed labels, `unknown` never treated as zero, fail-closed status semantics introduced by the
  audit.

---

## 1. Execution Rules

1. **Regression test first** for every `sci-fix` and every behavior change: run it, confirm it fails on the
   unmodified code, then fix and confirm it passes. New capabilities get tests that would fail if the capability
   were removed.
2. **Every number written into a reference is reproduced.** It is either produced by a committed command or test
   (the "verified walkthrough" convention of `likelihood-fitting.md` and `statistical-tools.md`), or quoted from a
   primary source checked on INSPIRE-HEP or Crossref with the verification date. Citations in §7 are `[To verify]`
   until checked. Never write a citation from memory.
3. **No network, package installation or paid model runs without explicit user approval** (`tasks/hep-research-plugin.md`
   §2.1, §13.3). pyhf is needed for S04 and S10 tests; ask before installing it into `.venv-hep`. Tests that need an
   optional tool **skip** without it, and a skip is reported as unverified, never as passing.
4. **Do not weaken existing tests**, and do not change committed example outputs. If an output must change, follow
   `docs/maintenance.md` ("Rerunning comparisons and examples").
5. **Fail closed.** New tools report `failed` / `incomplete` / `unresolved` with a non-zero exit code when inputs are
   infeasible, a fit does not converge, or validation is outside its tested range. Use the exit-code convention of the
   module being extended.
6. **Commits:** one task (or one logical step) per commit, ID in the message. Scientific corrections use
   `sci-fix(Sxx): …` and are separate from `docs(Sxx): …` and new features (`feat(Sxx): …`).
7. **Tolerances and thresholds marked `[Proposal]` below may be changed**, with the reason recorded in the Final
   Report. Never pick a tolerance after looking at the result it gates.
8. **English** for every file, commit and report (`tasks/hep-research-plugin.md` §2.6). Routing fixtures keep their
   en + zh-Hant mix.
9. **Stay in scope** (§4 and §5). Escalate the stop conditions of `tasks/hep-research-plugin.md` §13: a scientific
   choice not determined by sources or the user, three failed fix attempts, or a needed install.

---

## 2. Phase 0 — Baseline and reproduction

Run from `plugins/hep-research/`. Record every result in the Final Report.

```bash
python3 -m unittest discover -s tests -t .
python3 -m unittest discover -s tests/contracts -t .
( cd profiles/experiments/ams-02 && python3 -m unittest discover -s tests -t tests )
python3 tools/run_all_checks.py --out /tmp/stats-r0
python3 tools/check_ams_optional.py
python3 tools/measure_entrypoints.py --no-cli
```

Steps:

- [ ] Record the commit hash, Python and package versions, and which optional tools are present (pyhf, ROOT, Combine).
- [ ] Write a small script that reproduces F1–F11 and prints `reproduces: true/false` per finding (pattern:
  `tasks/hep-research/audit/phase0_repro.py`). Save it as `tasks/hep-research/stats-reinforcement/phase0_repro.py`.
  - F1: compute the three p-values above; grep the reference and the script docstring for the claims.
  - F2: copy the plugin without the AMS-02 profile (as `tools/check_ams_optional.py` does) and confirm that no file under `skills/` names the `core/stats` subcommands.
  - F3–F10: grep for the absent topics.
  - F11: validate a `statistical-result` fixture that declares a scan and has no global significance; confirm it passes.
- [ ] Classify each finding as reproduced defect, method-claim gap, or capability gap. If one does not reproduce,
  record that and drop or reduce the task.

---

## 3. Task List

Priority:

- **P1:** produces a wrong number or claim, or leaves generic guidance unreachable for non-AMS users, or misses a tool needed in nearly every LHC-style shape analysis.
- **P2:** a capability commonly needed in experimental analyses.
- **P3:** breadth extension.

| ID | Pri | Task | Finding |
|---|---|---|---|
| S01 | P1 | Correct the Li & Ma statement and low-count claim; add calibrated p-values | F1 |
| S02 | P1 | Give `hep-statistics` its own generic `core/stats` guide | F2 |
| S03 | P1 | Reference: building nuisance parameters into the likelihood | F4 |
| S04 | P1 | Post-fit nuisance diagnostics: pulls, impacts, ranking, grouped breakdown | F3 |
| S05 | P1 | Global significance for scans (look-elsewhere) | F5 |
| S06 | P2 | Expected sensitivity, goodness of fit, model comparison | F6 |
| S07 | P2 | Bayesian executable path: convergence diagnostics, prior sensitivity, an oracle run | F7 |
| S08 | P2 | Unbinned weighted fits and sWeights | F8 |
| S09 | P2 | ML-assisted inference: validity reference and handoff | F9 |
| S10 | P3 | Publishing likelihoods for reinterpretation | F10 |
| S11 | P2 | `statistical-result` contract: optional fields and one fail-closed rule | F11 |
| S12 | P1 | Integration: SKILL.md resources, routing cases, VALIDATION, capability matrix, changelog | all |

**Execution order:** S01 → S02 → S03 → S04 → S05 → S06 → S11 → S07 → S08 → S09 → S10 → S12. S04 needs pyhf (Rule 3);
if it is not approved, do S04's pyhf-free parts, record the rest as blocked, and continue.

---

### S01 (P1) — Li & Ma: correct the statement, bound the claim, add calibrated p-values

**Files:**

- `skills/hep-statistics/references/astroparticle-statistics.md`
- `skills/hep-statistics/scripts/li_ma_significance.py`
- new test `tests/skills/hep_statistics/test_li_ma_significance.py`

**Implement:**

- [ ] `sci-fix`: replace the equivalence statement with `S = sqrt(-2 ln lambda)` (Li & Ma eq. 17 `[To verify]`).
  State that its standard-normal reading is asymptotic (Wilks) and that accuracy degrades for small `N_on`, `N_off`.
  Keep the true contrast with the naive Gaussian formula.
- [ ] Same correction in the script docstring and `--help`.
- [ ] Add `--toys N --seed S`: a toy-calibrated p-value of the Li & Ma statistic under the background-only hypothesis
  with the background profiled from the data. Report its binomial Monte Carlo uncertainty, or a binomial upper
  bound when there are zero exceedances (the rule in `inference-recipes.md`).
- [ ] Add `--exact-conditional`: the conditional binomial test (`N_on | N_on+N_off ~ Bin(N, alpha/(1+alpha))`).
  Label it conservative for discrete data.
- [ ] Output lists every p-value with its method label. Default behavior without the new flags is unchanged
  (byte-identical JSON keys for existing fields).
- [ ] Fix the stale link label `[35, low-count, high-rigidity bins]` in the same reference (`docs`).

**Acceptance:**

- [ ] The test fails on the old text (sqrt(2) equivalence phrase present; "does not require large counts" present)
  and passes after the fix.
- [ ] For `(N_on, N_off, alpha) = (4, 2, 0.25)`:
  - `--exact-conditional` gives p = 0.01696 ± 1e-5.
  - `--toys 200000 --seed 1` gives a p-value within 3 Monte Carlo standard errors of an independent toy computation inside the test (different code path, same model).
- [ ] At `(50, 100, 0.2)` the asymptotic and toy p-values agree within 3 Monte Carlo standard errors or 10% relative
  `[Proposal]`. Large counts are where the asymptotic form is expected to hold.
- [ ] Existing callers (`astroparticle-statistics.md` deliverables, detector-response references) still work.

---

### S02 (P1) — An owner-side guide to `core/stats`

**Files:**

- new `skills/hep-statistics/references/core-stats-guide.md`
- `profiles/experiments/ams-02/modules/methods/statistical-diagnostics.md`
- `profiles/experiments/ams-02/modules/methods/inference-and-unfolding.md`
- new test `tests/skills/hep_statistics/test_core_stats_guide.py`
- `tasks/hep-research/DECISIONS.md`

**Implement:**

- [ ] Write the generic guide: one section per module and subcommand. Each section covers what question it answers,
  model assumptions, inputs, outputs and status/exit codes, the decision rule for when to use it instead of an
  alternative, and its "Not implemented" limits. Source the general rules from the AMS module's `[General method]`
  items; the AMS module states that the owner's text takes precedence, so the owner now holds the canonical copy.
  Contains no experiment names (layering).
- [ ] In the AMS modules: add a pointer at the top to the owner guide. Correct the stale exit-code sentence
  (`template_fit.py` exits 1 on a failed fit) and the duplicated failure-mode lines. Do **not** delete generic
  passages interleaved with ledger citations, unless a new decision record superseding M6-02 is approved (Open
  Question Q3).
- [ ] Record the decision in `DECISIONS.md`.

**Acceptance:**

- [ ] The new test imports each `core/stats` module's `build_parser()` and asserts every subcommand name appears in
  `core-stats-guide.md`. It fails if a future subcommand is added without documentation. (r2) Only five modules have
  `build_parser()` and subcommands; `validate_covariance.py` and `validate_response.py` are single-command scripts
  built inside `main()`, so the test checks their file names and every long option they declare instead.
- [ ] `tools/check_ams_optional.py` passes, and in its AMS-free copy the guide is present and its links resolve.
- [ ] `tools/check_layering.py` passes; `tests/skills/test_skill_resources.py` (or its current equivalent) resolves
  every new link.

---

### S03 (P1) — Reference: nuisance parameters in the likelihood

**Files:**

- new `skills/hep-statistics/references/nuisance-modeling.md`
- cross-links from `skills/hep-analysis/references/systematics.md` and `statistical-tools.md`

**Content (each item with a primary source or a verified walkthrough, Rule 2):**

- [ ] **Constraint terms:** Gaussian, log-normal and gamma, with what each implies for positivity and asymmetric
  effects; Poisson auxiliary measurements; frequentist constraint vs Bayesian prior wording (keep the existing
  rule in `likelihood-fitting.md`).
- [ ] **Interpolation:**
  - pyhf normsys code 1 vs code 4 and histosys code 0 vs code 4p; Combine `lnN` (symmetric and asymmetric) and `shape` vertical interpolation. Mark each `[To verify]` against the installed release documentation.
  - A worked comparison on `adapters/pyhf-combine/assets/pyhf-counting.json` showing the limit change between code 1 and code 4. The repository already recorded this effect (pyhf counting limit 2.1529 with code 4).
- [ ] **Two-point and one-sided systematics:** symmetrization options and their bias, when a one-sided variation
  becomes a one-sided nuisance, and why "max of up/down" double counts.
- [ ] **Envelopes and alternative models:** an envelope from `hep-theory` enters only through its prescription. Cover
  discrete-model nuisances (discrete profiling) and when a single Gaussian NP is not acceptable. Refuse auto-Gaussianizing, consistent with `contracts/comparison/combination.py`.
- [ ] **MC statistics:** `staterror` vs `shapesys` vs Barlow–Beeston(-lite); the light/full trade-off tested by
  `core/stats/template_fit.py` and `statistical_toys.py template-bb`; never both on the same source.
- [ ] **Smoothing, symmetrization and pruning:** criteria tied to S04 diagnostics. Keep raw templates; quantify the
  POI change; never prune on postfit impact alone (consistent with `systematics.md`).
- [ ] **Correlation scheme:** NP naming as correlation; decomposed sources; partial correlations via latent
  variables. Point to `systematics.md` for the physical source inventory; do not duplicate it.

**Acceptance:**

- [ ] Every numeric claim has a command or test; the code-1 vs code-4 walkthrough runs in a test that skips without
  pyhf.
- [ ] `hep-analysis/references/systematics.md` links to the new file for likelihood treatment and loses no content.
- [ ] Layering and budget checks pass.

---

### S04 (P1) — Post-fit nuisance diagnostics

**Files:**

- new adapter asset `adapters/pyhf-combine/assets/pyhf_nuisance_diagnostics.py` (pyhf-based; the adapter owner is
  `hep-statistics`)
- new section in `nuisance-modeling.md`
- new test `tests/adapters/test_pyhf_nuisance_diagnostics.py`
- `adapters/pyhf-combine/adapter.json` (bump version; add asset and test)

**Implement** (pyhf only; cabinetry is Open Question Q2):

- [ ] **Pulls and constraints table:** `(theta_hat - theta_0)/sigma_prefit` and `sigma_postfit/sigma_prefit`. State the convention and flag non-Gaussian constraints, where this scale is inappropriate.
- [ ] **Impacts:** pre-fit (NP fixed at `theta_hat ± sigma_prefit`) and post-fit (`theta_hat ± sigma_postfit`), each by
  a full refit of the POI with that NP fixed, with signs kept.
- [ ] **Ranking:** order NPs by impact magnitude.
- [ ] **Grouped breakdown:** freeze each declared group and report `sqrt(sigma_total^2 - sigma_frozen^2)`. Also report the
  order dependence and the non-closure (sum in quadrature vs total), per the existing "decompositions can depend on
  method and order" rule.
- [ ] **NP correlation matrix:** list pairs above a threshold `[Proposal: |rho| > 0.5]`.
- [ ] Unconverged refits are listed as `failed`, never dropped. Exit non-zero if the nominal fit fails.
- [ ] Output JSON plus a text table; seed and pyhf version echoed.
- [ ] Document the Combine equivalents (`FitDiagnostics`, impacts via the CombineHarvester `combineTool.py`) as
  `[To verify]` text only; do not add Combine code unless Combine is available and approved. (r2) §6 forbids a
  `[To verify]` marker in plugin files, so Combine statements are written only as far as a checked source supports
  them; anything unchecked is worded "not verified in this plugin" with the documentation link, not as a fact.

**Acceptance:**

- [ ] On `adapters/pyhf-combine/assets/pyhf-shape-synthetic.json`, the POI shift for each NP impact agrees with an
  independent refit using `tests/adapters/histfactory_reference.py` within 1e-3 relative or 1e-4 absolute
  `[Proposal]`.
- [ ] A constructed workspace with one NP that does not affect any bin gives impact 0 and pull 0 with constraint 1.
  A workspace with two fully degenerate NPs is reported with |rho| ≈ 1 and a warning.
- [ ] Without pyhf the test skips with a clear reason (unverified), and the script exits non-zero with a "pyhf not
  installed" message.
- [ ] `tests/adapters/test_adapter_declarations.py` passes with the new asset, version and test listed.

---

### S05 (P1) — Global significance for scans

**Files:**

- new `skills/hep-statistics/scripts/look_elsewhere.py` (single consumer → skill script, not `core/`)
- new section in `inference-recipes.md`
- new test `tests/skills/hep_statistics/test_look_elsewhere.py`

**Implement:**

- [ ] Input: a binned background model and a signal shape family scanned over a 1D parameter (for example
  position/mass with a fixed width), as JSON.
- [ ] `local`: local q0 per scan point, with the asymptotic half-χ² and the maximum.
- [ ] `brute`: global p-value from seeded background-only toys, maximizing over the scan in each toy. Report the binomial
  Monte Carlo error, or a bound with zero exceedances.
- [ ] `gross-vitells`: the expected number of upcrossings at a low reference level from a small toy set, extrapolated to
  the observed maximum (Gross & Vitells 2010, already cited in the plugin). Report the reference level, its toy
  count and the extrapolation distance. Warn when the target level is far beyond the levels the upcrossing estimate
  was validated at.
- [ ] Output: local Z/p, global Z/p, method, trials-equivalent factor, seed, toy counts. Global p is never less than local p.

**Acceptance:**

- [ ] On a seeded synthetic scan (≥ 40 bins, flat background, Gaussian signal shape of fixed width scanned over the
  range), the `gross-vitells` global p agrees with `brute` (≥ 20,000 toys `[Proposal]`, marked slow) within
  max(3 Monte Carlo standard errors, 20% relative) for global p in [1e-3, 0.1] `[Proposal]`. (r2) The upper end is
  0.1, not 0.5: the Gross–Vitells expression is an asymptotic upper bound for high levels (their eq. for large u) and
  is loose by construction where the global p is large; this was decided before any scan was run.
- [ ] When the scan has one point, global p equals local p (exact).
- [ ] Wrong inputs (empty scan, negative background, unsorted grid) are refused with exit 2. Slow tests are marked so
  the default suite time grows by no more than 30 s `[Proposal]`.

---

### S06 (P2) — Expected sensitivity, goodness of fit, model comparison

**Files:**

- `inference-recipes.md` (new sections)
- new `skills/hep-statistics/scripts/sensitivity_and_gof.py`
- new test `tests/skills/hep_statistics/test_sensitivity_and_gof.py`

**Implement:**

- [ ] **Sensitivity:**
  - Asimov discovery significance `Z_A = sqrt(2((s+b)ln(1+s/b) - s))`.
  - The version with background uncertainty (Cowan et al. 2011 / Cowan's later note `[To verify]`), stating its assumption: a Poisson auxiliary measurement with `tau = b/sigma_b^2`, not a Gaussian constraint.
  - The expected-limit median and bands, pointing to the existing `multibin-limit` and `cls-limit` subcommands.
  - A rule: never quote `s/sqrt(b)` without stating it is the large-b limit.
- [ ] **GoF:**
  - Saturated-model Poisson deviance (zero-count terms by their limit), calibrated with seeded toys, refitting the model in each toy.
  - Pearson/Neyman χ² only with a stated count condition.
  - A note that GoF does not test bias (link to closure).
- [ ] **Model comparison:**
  - Nested: likelihood ratio, with Wilks conditions and boundary/non-identifiability cases (point to S05 when a parameter exists only under the alternative).
  - Non-nested: toys under each hypothesis.
  - AIC/BIC as heuristics with their assumptions.
  - Bayes factors: point to S07, with their prior dependence.

**Acceptance:**

- [ ] `Z_A(s=5, b=20) = 1.07572 ± 1e-5`.
- [ ] With `sigma_b = 2` the formula gives `0.97554 ± 1e-5` and matches a numerical profile of q0 on the Asimov data
  with a Poisson auxiliary term (an independent code path in the test) within 1e-6.
- [ ] GoF calibration: over seeded datasets drawn from the fitted model, the toy-calibrated GoF p-values are
  uniform within a stated tolerance (for example a KS test at α = 0.01 on ≥ 300 datasets `[Proposal]`, marked slow).
  A deliberately wrong model gives a median p below 0.05 on a stated configuration.

---

### S07 (P2) — Bayesian executable path

**Files:**

- new `skills/hep-statistics/scripts/bayes_diagnostics.py`
- `inference-recipes.md` Bayesian section (expand)
- new test `tests/skills/hep_statistics/test_bayes_diagnostics.py`
- `docs/capability-matrix.md` (Bayesian row)

**Implement** (NumPy only; a sampler package is Open Question Q2):

- [ ] Diagnostics on user-supplied chains (JSON or `.npy`):
  - rank-normalized split-R̂, bulk and tail ESS (Vehtari et al. 2021 `[To verify]`), Monte Carlo standard error of quantiles;
  - flags for too few chains or draws;
  - status `converged` / `not-converged` / `incomplete` with exit codes matching S01–S06.
- [ ] Prior sensitivity: importance-reweight the posterior draws to an alternative prior. Report the shift of the
  requested quantiles and the weight ESS. When the weight ESS is below a threshold `[Proposal: 10% of draws]`, say
  the result requires a rerun, not reweighting.
- [ ] A minimal reference sampler (Metropolis, seeded) used **only** as a test oracle and demonstration on the counting
  model of `skills/hep-analysis/scripts/counting_reference.py`. It is labeled a demonstration, not a production
  sampler.
- [ ] Reference text: priors and parameterization (flat in μ ≠ flat in log μ, already present); reference and
  Jeffreys priors as conventions with their caveats; marginalization vs profiling; credible vs confidence wording
  (point to `statistical-inference-for-physics.md`); Bayes-factor prior sensitivity (Lindley's paradox `[To verify]`).

**Acceptance:**

- [ ] Independent normal chains (4 × 1,000, seeded) give R̂ < 1.01. Chains with offset means (Δ = 1σ) give R̂ > 1.1.
  An AR(1) chain with ρ = 0.9 gives bulk ESS within 15% of `N(1-ρ)/(1+ρ)` `[Proposal]`. (r2) Configurations fixed
  before running: the offset case is 4 × 1,000 draws with two chains at mean 0 and two at mean Δ = 1σ; the AR(1) case
  is 4 independent chains × 5,000 draws (N = 20,000), stationary start.
- [ ] The demonstration sampler's 95% upper bound for `n = 0, b = 0` agrees with `counting_reference.py`
  (`-log(0.05) ≈ 2.995732`) within 3 Monte Carlo standard errors of the quantile.
- [ ] A `statistical-result` with `paradigm: bayesian` written by the demo validates; one with `convergence` showing
  R̂ > 1.01 is accepted only with `fit_status: converged-with-warnings` or `failed` (enforced in S11).
- [ ] The capability-matrix row changes from "contract checks only" to exactly what was run (diagnostics tested; demo
  sampler on one model). No wider claim.

---

### S08 (P2) — Unbinned weighted fits and sWeights

**Files:**

- `likelihood-fitting.md` (new section)
- new seeded demonstration test `tests/skills/hep_statistics/test_weighted_unbinned_fit.py`

**Implement:**

- [ ] Reference content:
  - **sPlot:** the assumptions (independence of the discriminating and control variables per component, a correct discriminating model), negative weights, and that the sWeights' own uncertainty enters the covariance (Pivk & Le Diberder 2005 `[To verify]`).
  - **Weighted unbinned ML:** asymptotically correct covariance vs the naive and "sum w²" corrections (Langenbruch 2022 `[To verify]`).
  - **COWs:** custom orthogonal weight functions when independence fails (Dembinski et al. 2022 `[To verify]`).
  - **Signed generator weights:** in unbinned fits.
  - **Background subtraction:** do not treat background-subtracted data as Poisson signal (already stated; keep).
- [ ] The test is a verified walkthrough with a seeded NumPy/SciPy toy: Gaussian mass signal on a flat background, an
  exponential decay-time signal. Fit the lifetime on sWeighted data with (a) the naive weighted-likelihood Hessian and
  (b) the asymptotically correct covariance. Report pull widths over toys.

**Acceptance:**

- [ ] Over ≥ 300 seeded toys `[Proposal]`, method (b) gives a pull width in [0.9, 1.1] `[Proposal]`. Method (a) is
  reported as measured, with no assertion chosen after seeing it (Rule 7).
- [ ] The numbers in the reference walkthrough equal the test's committed output.
- [ ] A variant where the control variable depends on the discriminating variable is shown to bias the fit. The bias is
  reported in the walkthrough, motivating COWs.

---

### S09 (P2) — ML-assisted inference: validity and handoff

**Files:**

- new `skills/hep-statistics/references/ml-assisted-inference.md`
- cross-link with `skills/physics-ml/references/scientific-machine-learning.md` (no duplication)

**Content:**

- [ ] **Classifier/regressor outputs as observables:** valid by construction when templates and all systematic variations
  are evaluated through the same frozen model. The risks are training/evaluation overlap and systematics that move the
  output distribution.
- [ ] **Neural likelihood-ratio / NSBI:**
  - calibration of the estimated ratio (Cranmer, Pavez, Louppe 2015 `[To verify]`);
  - closure on known-ratio benchmarks;
  - nuisance-parameterized networks;
  - toy-based coverage of the final intervals;
  - the ATLAS NSBI implementation note (arXiv:2412.01600 `[To verify]`) as an example of the required validation, inside an `<!-- example -->` block.
- [ ] **SBI posteriors:** simulation-based calibration (Talts et al. 2018 `[To verify]`); coverage across the prior;
  simulator mismatch (point to physics-ml).
- [ ] **Deliverables checklist:** which ML artifact, training domain, calibration evidence, coverage evidence, systematics
  propagation, and status labels. The existing validator rule that AUC-only ML validation is an error stays as is.

**Acceptance:**

- [ ] Routing case `ml-neighbor-1` still routes to `hep-statistics` (static check). The SKILL.md Resources section links
  the new file.
- [ ] `tests/routing/test_theory_routing.py`-style static checks (or a new one) confirm physics-ml references point
  inferential validity to `hep-statistics` and `hep-statistics` points training to `physics-ml`.
- [ ] No training code is added (`tasks/hep-research-plugin.md` §15: no extra ML frameworks).

---

### S10 (P3) — Publishing likelihoods for reinterpretation

**Files:**

- `statistical-tools.md` (new section)
- optional test `tests/adapters/test_pyhf_publication.py` (skips without pyhf)

**Content:**

- [ ] Full likelihood publication: pyhf JSON workspace, background-only workspace plus signal patchsets, HEPData
  conventions, what is lost in a translation between tools (rule already present: textual translation ≠ equivalent
  likelihood). Source: Cranmer et al. 2022 "Publishing statistical models" `[To verify]`.
- [ ] Simplified likelihoods: covariance-only and skew-corrected forms (Buckley et al. 2019 `[To verify]`), and when
  they fail (non-Gaussian, few counts).
- [ ] Producer checklist: bin correlations, signal-region overlap, expected vs observed, the model version.
  Recasting itself stays with `hep-theory` (§7.2 routing rule).

**Acceptance:**

- [ ] With pyhf, a test builds a background-only workspace plus a one-signal patch from
  `pyhf-shape-synthetic.json`, applies the patch, and reproduces the original workspace's best fit and CLs to
  1e-6.
- [ ] Without pyhf: skipped and reported as unverified.

---

### S11 (P2) — `statistical-result` contract additions

**Files:**

- `contracts/schemas/ext_statistical_result.json`
- `contracts/validate.py`
- `contracts/__init__.py` (version)
- `contracts/fixtures/artifacts/valid|invalid/`
- `tests/contracts/`
- `CHANGELOG.md`

**Implement** (all new fields optional → minor version `1.1.0`, per `docs/maintenance.md` "Schema migration"):

- [ ] `significance`: `{local_p, local_z, global_p, global_z, trials_method ∈ {none-needed, toys, gross-vitells,
  analytic-bound}, scan: {parameters, ranges}}`.
- [ ] `expected`: `{median, band_1sigma, band_2sigma, method}`.
- [ ] `uncertainty_breakdown`: `{method ∈ {group-freeze, impacts, other}, order, groups[], closure}`.
- [ ] `goodness_of_fit`: `{statistic, p_value, calibration ∈ {asymptotic, toys}, n_toys}`.
- [ ] `construction` enum gains `berger-boos`, `cousins-highland`, `toy-calibrated-profile`. Existing values unchanged.
- [ ] Fail-closed rules:
  - When `significance.scan` is present and `global_p` is missing, report `unresolved` (`stats.lee_missing`).
  - When `paradigm: bayesian` and the declared R̂ exceeds 1.01 with `fit_status: converged`, report an error (`stats.convergence_mismatch`). The threshold is `[Proposal]`.
  - (r2) `docs/maintenance.md` makes "tightening a rule so old artifacts fail" a major change, and the acceptance
    below requires a v1.0.0 artifact to validate the same under 1.1.0. So `stats.convergence_mismatch` is an error
    only for artifacts declaring `contract_version` ≥ 1.1.0, and a warning for 1.0.0 artifacts. `stats.lee_missing`
    needs the new `significance` field, which no 1.0.0 artifact can carry, so it applies as written.

**Acceptance:**

- [ ] All existing fixtures (`statres_frequentist.json`, `statres_bayesian.json`, and the invalid ones) keep their
  outcome; `ParadigmsT28` passes.
- [ ] New valid and invalid fixtures for each rule. Validating a v1.0.0 artifact under 1.1.0 gives the same result.
- [ ] The CHANGELOG entry lists the new fields and rules.

---

### S12 (P1) — Integration, routing, documentation

**Files:**

- `skills/hep-statistics/SKILL.md`
- `tests/routing/cases.json` (via `tests/routing/make_cases.py` if that is the generator)
- `VALIDATION.md`
- `docs/capability-matrix.md`
- `CHANGELOG.md`
- `docs/provenance-new.csv`

**Implement:**

- [ ] SKILL.md Resources: link each new reference and script by name. Keep SKILL.md ≤ 8,192 B and ≤ 180 lines. Leave the
  description unchanged unless a routing miss justifies an edit that keeps it ≤ 1,024 chars.
- [ ] Add ≥ 8 routing cases (≥ 3 in zh-Hant) covering impacts/pulls, global significance, expected sensitivity, GoF,
  Bayesian convergence, sWeights, NSBI validity, and likelihood publication. Each states `expected_primary` and,
  where relevant, `not`.
- [ ] `VALIDATION.md`: new section `STATS-REINFORCEMENT-RUN` with commands, environment, pass/fail/skip/unverified
  counts.
- [ ] Capability matrix rows for each new capability, using the matrix's status words. Optional-tool parts stay
  "unverified" when skipped.
- [ ] Register new files: commit, then `python3 tools/check_traceability.py --write-new`, then commit the register.

**Acceptance:**

- [ ] `tools/run_all_checks.py`: all aggregate checks pass. `tools/check_relocation.py` passes.
- [ ] `tools/check_routing_static.py` passes with the new cases.
- [ ] `tools/measure_entrypoints.py --no-cli` passes the budgets.
- [ ] No capability is described more strongly than its evidence: a skipped pyhf test never appears as "tested".

---

## 4. Capability items (not part of this order; do only if the user requests them)

- [ ] **C01 Domain patterns:** neutrino-oscillation intervals with non-regular parameter spaces (full FC scans);
  flavor-physics amplitude fits; precision template-morphing measurements. Add only where the generic methods
  mislead, each as a profile-independent example block. EFT global fits and cosmic-ray propagation stay out of v1
  (`tasks/hep-research-plugin.md` §15).
- [ ] **C02 Live evaluation (paid):**
  - live routing for the new cases;
  - a skill-vs-baseline answer comparison on statistics prompts (the `prompts_eval` pattern of the legacy repository), including short queries ("quick CLs limit", "is this 3σ local excess significant?") answered from memory.
- [ ] **C03 Dependencies:** adopt cabinetry (impacts and ranking cross-check), emcee or another sampler, or zfit/iminuit
  for unbinned fits, via the adapter process (`docs/adapter-authoring.md`).
- [ ] **C04 Public-data benchmark:** reproduce a published full likelihood from HEPData (best fit, CLs) end to end
  through S04 and S10 tooling. Needs network access.

---

## 5. Out of scope

- A general statistics framework in `core/` (many-NP shape models, workspace combination, a production sampler).
  These go through adapters.
- Physics content of systematics (`hep-analysis`, `detector-response`), theory prescriptions (`hep-theory`), ML training
  (`physics-ml`).
- Changing the seven-skill design or the skill description beyond S12's rule.
- Licensing decisions (audit C05 still applies).

---

## 6. Global Definition of Done

- [ ] F1–F11 are each fixed, implemented, or recorded as dropped with the Phase 0 reason.
- [ ] Every `sci-fix` and behavior change has a regression test that failed on the original code.
- [ ] All Phase 0 checks still pass; the AMS-02 suite is unchanged in outcome; example outputs are byte-identical.
- [ ] Every number in a new or changed reference is reproduced by a committed command or test, or cited from a
  primary source with a verification date. No `[To verify]` marker remains in plugin files.
- [ ] Environment failures, optional-tool skips and product defects are reported separately; skips are never success.
- [ ] Nowhere is a passing test, a single-point coverage check or a static routing pass presented as physical
  validity or global coverage.

---

## 7. Sources to check before use (all `[To verify]`)

Already in the plugin, so `[Confirmed]` present:

- Cowan, Cranmer, Gross, Vitells, EPJC 71 (2011) 1554, arXiv:1007.1727.
- Gross & Vitells, EPJC 70 (2010) 525, arXiv:1005.1891.
- Feldman & Cousins 1998; Junk 1999; Read 2002; PDG Statistics review.

To be checked on INSPIRE-HEP/Crossref and dated. (r2) `curl` to inspirehep.net and api.crossref.org is refused by the
container proxy (403); the read-only lookups the user approved go through the WebFetch tool against the INSPIRE
API, and journals outside INSPIRE through their Crossref/DOI record or the arXiv abstract page:

- Li & Ma, ApJ 272 (1983) 317.
- Barlow & Beeston, Comput. Phys. Commun. 77 (1993) 219.
- Conway, arXiv:1103.0354.
- Cousins & Highland, NIM A 320 (1992) 331.
- Pivk & Le Diberder, NIM A 555 (2005) 356, arXiv:physics/0402083.
- Langenbruch, EPJC 82 (2022) 393, arXiv:1911.01303.
- Dembinski, Kenzie, Langenbruch, Schmelling, NIM A 1040 (2022) 167270, arXiv:2112.04574.
- Vehtari, Gelman, Simpson, Carpenter, Bürkner, Bayesian Analysis 16 (2021) 667, arXiv:1903.08008.
- Talts et al., arXiv:1804.06788.
- Cranmer, Pavez, Louppe, arXiv:1506.02169.
- ATLAS, arXiv:2412.01600.
- Cranmer et al., SciPost Phys. 12 (2022) 037, arXiv:2109.04981.
- Buckley et al., JHEP 04 (2019) 064, arXiv:1809.05548.

If any detail above (volume, page, arXiv number) does not match the record, use the record and note the correction
in the Final Report.

---

## 8. Open Questions

- **Q1** Approve installing pyhf 0.7.6 into `.venv-hep` for S03/S04/S10 tests (the version already demonstrated)?
  Without it those parts are unverified.
- **Q2** Adopt cabinetry and/or a sampler package now (C03), or keep S04/S07 dependency-light as specified?
- **Q3** May S02 remove generic passages from the AMS-02 modules (superseding DECISIONS M6-02), or only add pointers?
- **Q4** Accept or replace the `[Proposal]` tolerances: S01 10%, S04 1e-3/1e-4, S05 20% and 20,000 toys, S06 KS
  α = 0.01, S07 15% ESS and R̂ 1.01, S08 [0.9, 1.1], S11 R̂ 1.01, slow-test budget 30 s.
- **Q5** Run paid live routing for the new cases (C02) after S12?

---

## 9. Final Report (deliver at the end)

1. **Environment:** OS, Python, core and optional packages, commit hash.
2. **Phase 0 table:** F1–F11, reproduces / does not reproduce, and classification.
3. **Per-task summary:** files changed, tests added (names), before/after behavior, decisions made under Rule 7 and
   Open Questions answered.
4. **Test results:** per suite pass / fail / error / skip, with skips and environment errors separate from product
   defects.
5. **Documentation updates:** VALIDATION section, capability-matrix rows, CHANGELOG entry, DECISIONS entries.
6. **Citations:** each source in §7 with the verification date and any corrected detail.
7. **Open items:** blocked parts (for example pyhf not approved), deferred C items, and anything needing a human
   decision.

---

## 10. Revision r2 (2026-10-03), checked against `main` at `dbda2aa`

| # | Change | Reason |
|---|---|---|
| R1 | Execution baseline row added to §0 | Versions and test counts on the real commit differ from the ZIP inspection (NumPy 2.4.6; 1094 tests, 59 skips) |
| R2 | Open questions answered: Q1 yes (pyhf 0.7.6 into `.venv-hep`, and read-only INSPIRE/Crossref lookups), user 2026-10-03; Q2 stay dependency-light; Q3 pointers only, no deletion from AMS modules; Q4 accept the `[Proposal]` tolerances; Q5 no paid live routing. C01–C04 not done | Q1 from the user; Q2–Q5 the defaults the project coordinator set for this run |
| R3 | S02 test: the two validators have no subcommands | `validate_covariance.py`, `validate_response.py` define their parser inside `main()` |
| R4 | S04: no `[To verify]` text left in plugin files for Combine | Conflict between S04 and §6 |
| R5 | S05: Gross–Vitells comparison range [1e-3, 0.1] | The approximation is an asymptotic upper bound; set before running |
| R6 | S07: offset and AR(1) chain configurations fixed | r1 left them ambiguous; set before running |
| R7 | S11: `stats.convergence_mismatch` is an error only for `contract_version` ≥ 1.1.0 | Minor-version rule in `docs/maintenance.md` and S11's own acceptance |
| R8 | §7: citation lookups through WebFetch | Proxy refuses curl to INSPIRE and Crossref |

Findings F1–F11 were all re-read on `dbda2aa`; their evidence is unchanged (the F1 numbers were recomputed:
asymptotic p 6.646e-3, exact conditional p 0.01696). The F4 "2.1529 with code 4" is recorded in the commit message
of the M6 pyhf shape cross-check in this repository's history.
