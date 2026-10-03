# TASK: Fix validation gaps in the `hep-research` plugin

> **For Claude (agent):** This file is an executable work order. Read it fully before changing any code. Follow the Execution Rules, work through the tasks in the stated order, and finish with the Final Report. Unless otherwise noted, every path is relative to `plugins/hep-research/`.

> **Revision r2 (2026-10-03, re-checked against `main` at `8f2b3da`, after PR #11).** Every path, function and
> fixture named below exists on current `main`; all eight findings were re-run as minimal counterexamples
> (`tasks/hep-research/audit/phase0_repro.py`) and still reproduce. Changes from r1: the commit is now known; the
> reference table gains the cloud run; "release notes" is defined (there was no changelog: create
> `plugins/hep-research/CHANGELOG.md`); T07 names the second auxiliary-truncation site; T06 fixes its status
> vocabulary; C03 carries the recorded routing count. Nothing else changed.

---

## 0. Context

| Item | Value |
|---|---|
| Repository | <https://github.com/hchouTW/hep-research/tree/main> |
| Plugin version audited | `0.1.0` |
| Audit date | 2026-10-03 (Asia/Taipei) |
| Audit source | Uploaded ZIP `hep-research-main.zip`; commit unknown in the ZIP. **r2: verified against `main` `8f2b3da`** (merge of PR #11) |
| Audit status | Prior evaluation exists but must be **re-verified** (Phase 0); **no fixes implemented yet** |
| Scope | Seven core skills, `contracts/`, `core/` statistics and blinding, `profiles/`, tests, maintenance tooling |

**Goal:** Make the plugin's research rules enforceable. Wrong inputs, infeasible fits, and incomplete checks must never be reported as success. Every fix must be backed by a regression test that fails on the original code and passes after the fix.

Because the audited snapshot may not match the current `main`, **first confirm that each finding still reproduces** (see Phase 0). If a finding no longer reproduces, record that and skip the fix for it.

---

## 1. Execution Rules

1. **Regression test first.** For every task T01–T08: write the regression test, run it, and confirm it **fails** on the unmodified code before implementing the fix. Then confirm it passes.
2. **Do not weaken existing tests.** Never delete, skip, or loosen an existing assertion to make the suite pass. If an existing test encodes the buggy behavior, stop and explain in the report why it must change.
3. **Preserve these existing designs** (no regressions allowed):
   - Responsibility split across the seven skills.
   - Profiles loaded on demand.
   - `unknown` is never treated as zero.
   - Synthetic / Asimov labels.
   - Separation of non-Gaussian theory uncertainties.
   - Distinction between software consistency and physical validity.
4. **Keep the schema validator lightweight.** `validate_artifact()` stays single-file and must not read arbitrary filesystem paths. Cross-artifact checks go into a new project-level validator (T05).
5. **Fail closed.** When equivalence or completeness cannot be established, report `unresolved` / `incomplete` / `failed` — never a silent pass.
6. **Separate three kinds of outcomes** in every report: environment failures (missing deps), tool skips (optional tools not installed), and product defects. Skips are **not** evidence of success.
7. **Stay in scope.** Do not modify unrelated files, choose a license, or make legal judgments (see C05).
8. **Small, reviewable commits.** One task per commit (or per logical step), with the task ID in the message, e.g. `T03: reject infeasible template fits`.
9. If a task requires a design decision not specified here (e.g. exact field names), choose the minimal option consistent with existing contract conventions, document it in the report, and continue.

---

## 2. Phase 0 — Baseline

Run from `plugins/hep-research/` unless noted. Record each result.

```bash
python3 -m unittest discover -s tests -t .
python3 -m unittest discover -s tests/contracts -t .
( cd profiles/experiments/ams-02 && python3 -m unittest discover -s tests -t tests )
python3 tools/check_layering.py
python3 tools/build_stanzas.py --check
python3 tools/check_routing_static.py
python3 tools/measure_entrypoints.py --no-cli
python3 tools/check_packaging.py
```

**Reference results from the audit** (macOS, Python 3.14.8, NumPy present, SciPy and several optional tools absent):

| Check | Audit result | Notes |
|---|---|---|
| Main suite | 1,031 tests: 931 pass, 99 skip, 1 error | Error = `test_solver_failure_recorded` failing to import SciPy (environment, not product) |
| Contracts suite | 83 tests, all pass | Coverage is insufficient (see T01, T02, T05) |
| AMS-02 profile suite | 258 tests, all pass | Run from `profiles/experiments/ams-02/` |
| `check_layering.py` | Pass | |
| `build_stanzas.py --check` | Pass | |
| `check_routing_static.py` | 48 cases, pass | Static descriptions only; not live routing quality |
| `measure_entrypoints.py --no-cli` | Pass | Host CLI not verified |
| `check_packaging.py` | Pass | |

**r2 cloud baseline** (Linux 6.18, Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1, Matplotlib, SymPy; optional tools absent): main suite 1,031 tests, OK, 57 skipped, **0 errors** (SciPy is a core dependency in `requirements-core.txt`, so `test_solver_failure_recorded` runs and passes); contracts 83 OK; AMS-02 258 OK; all five tool checks pass. The 57 skips are all optional tools (PyTorch, uproot/awkward, ROOT, pyhf, Combine, Graphviz/PlantUML/Mermaid, tectonic, legacy checkout).

**Phase 0 steps (all pending — redo against the current code; do not rely on the audit's conclusions):**

- [ ] Confirm the plugin structure and version (expected `0.1.0`); record the current commit hash.
- [ ] Read `README`, `VALIDATION`, the capability matrix, and the instructions of the seven core skills.
- [ ] Inspect the comparison gate, artifact schemas, semantic validator, and handoff status rules.
- [ ] Inspect the template fit, the Berger–Boos approximation, blinding, ML split integrity, and manuscript checks.
- [ ] Install core requirements (including SciPy if it is a core dependency) so that `test_solver_failure_recorded` can run. If it cannot be installed, record it as an environment failure.
- [ ] Run the main tests, contract tests, AMS-02 profile tests, and static maintenance checks (commands above); record results.
- [ ] Use minimal counterexamples to confirm the gate, artifact, fit, blinding, provenance, ML, and bibliography issues (T01–T08 reproductions below); record **reproduces / does not reproduce** for each.
- [ ] Classify each finding as a reproduced defect, a method-claim gap, or a product capability gap, and update the Task List evidence column if it differs from the audit.

---

## 3. Task List

Priority: **P1** = can let wrong research inputs pass, mark failures as success, or leave a key check incomplete. **P2** = strengthens validation completeness, method labels, or workflow.

| ID | Pri | Task | Evidence |
|---|---|---|---|
| T01 | P1 | Compare physical observable definition and **all** axes in the comparison gate | Reproduced with minimal counterexample |
| T02 | P1 | Cross-field and numeric consistency in artifact validation | Reproduced |
| T03 | P1 | Reject infeasible fits; propagate solver status | Reproduced |
| T04 | P1 | Fix `.npy` blinding scan and "incomplete" semantics | Reproduced |
| T05 | P1 | Project-level artifact dependency, hash, and status validation | Validator behavior confirmed; new layer required |
| T06 | P2 | ML split grouping metadata completeness | Reproduced |
| T07 | P2 | Correct Berger–Boos coverage claim; add precision checks | Source/test analysis; undercoverage **not** demonstrated |
| T08 | P2 | Detect citations with no bibliography | Reproduced |

**Execution order:** T01 → T02 → T03 → T04 → T05 → T06 → T08 → T07. Capability/maintenance items C01–C05 only if explicitly requested afterward.

---

### T01 (P1) — Comparison gate: physical definition and multi-axis comparison

**Files:** `contracts/comparison/gate.py` — `_state()`, `gate()`.

**Reproduce:**
1. Take a valid prediction fixture's observable. Build a measurement side identical to it, and clear the parameter point to isolate the field under test.
2. Create four variants, each run through `gate()`:
   - (a) change the measurement's **process**;
   - (b) change the measurement's **species**;
   - (c) change the measurement's **phase-space definition**;
   - (d) add a second variable on both sides, then make the second axis differ in **name, unit, and edges**.
3. **Bug:** all four return `comparable: true`.

**Root cause:** `_state()` reads only `variables[0]`; phase space is reduced to a fiducial boolean; process, species, and the full selection definition are dropped.

**Implement:**
- [ ] Define comparable fields for process, species, and structured phase space. If free-text values cannot be judged equal, return `unresolved`.
- [ ] Compare **every** axis. If multi-dimensional data is not supported yet, reject it explicitly rather than comparing only the first axis.
- [ ] When equivalence evidence is missing, require a named mapping with a stated justification.

**Acceptance:**
- [ ] Variants (a)–(d) are not directly comparable; each mismatch names the field and how to resolve it.
- [ ] Existing valid cases still pass: rebinning, folding, unit conversion, named mappings.

---

### T02 (P1) — Artifact axes, units, representation, finite numbers

**Files:** `contracts/validate.py`, `contracts/schema.py`, `contracts/schemas/common.json`, `contracts/schemas/ext_prediction.json`.

**Reproduce:** Starting from a valid prediction fixture, create four variants and pass each to `validate_artifact()`:
- (a) modify `values.edges` so they no longer match the observable;
- (b) set `values.unit` to a unit different from the observable's;
- (c) remove `values` from a **numerical** prediction;
- (d) set one value to `float('nan')`.

**Bug:** all four validate successfully.

**Root cause:** binned data checks only its own length vs. edges, not the observable; the number type does not require finiteness; `representation` does not determine required payload.

**Implement:**
- [ ] Require data axes and shape to match the observable; define multi-dimensional axis ordering explicitly.
- [ ] Require data units to match the observable, or a performed and traceable conversion.
- [ ] Make `symbolic`, `numerical`, and `grid` representations each require their payload.
- [ ] Reject NaN, ±Infinity, and non-finite values in values, uncertainties, and axes.

**Acceptance:**
- [ ] Variants (a)–(d) each produce explicit, specific errors.
- [ ] Legitimate metadata-only datasets remain expressible and valid.

---

### T03 (P1) — Infeasible template fits and solver status

**Files:** `core/stats/template_fit.py` — `_nelder_mead()`, `fit_yields()`, `bb_fit()`, `main()`.

**Reproduce:** feed this input to the CLI (inspect `main()` for the exact invocation):

```json
{"data": [10, 10], "templates": {"sig": [10, 0]}}
```

**Bug:** bin 2 has no template support, so the likelihood returns an infeasibility sentinel; yet the CLI exits `0` with `status: "ok"`, yield `20`, and a `null` error.

**Root cause:** the optimizer returns no termination/convergence state; the fit wrappers do not check likelihood feasibility; the CLI writes `ok` unconditionally.

**Implement:**
- [ ] Return diagnostics: convergence, termination reason, objective validity, covariance quality, boundary flags.
- [ ] Classify infeasible models as `rejected` / `failed` with a **non-zero** exit code.
- [ ] Distinguish: valid boundary solution, covariance warning, non-convergence, infeasible model.
- [ ] Propagate a failed fit status into the statistical-result artifact and research-communication; inference depending on the fit must stop.

**Acceptance:**
- [ ] The input above never yields anything downstream can treat as a successful fit.
- [ ] Existing feasible fits are unchanged in result and status.
- [ ] `test_solver_failure_recorded` runs (with SciPy installed) and passes.

---

### T04 (P1) — Blinding: `.npy` reading and scan completeness

**Files:** `core/blinding/blinding.py` — `scan_file()`, `scan_paths()`.

**Reproduce:**
- (A) Save a sealed value into a `.npy` file and scan it → raises `TypeError` (ndarray is not a context manager).
- (B) Scan only an unsupported `.root` file → report lists it under `unscanned`, `scanned` is empty, but `ok: true`.

**Root cause:** `.npy` and `.npz` share a context-manager code path; overall `ok` considers leaks only, not scan completeness. (The tool does disclose `unscanned`, so this is weak success semantics, not hidden skipping.)

**Implement:**
- [ ] Handle `ndarray` (`.npy`) and `NpzFile` (`.npz`) lifecycles separately.
- [ ] Introduce `pass` / `fail` / `incomplete` status and a **strict publication mode**.
- [ ] In strict mode, unsupported formats cannot count as verified.
- [ ] For publication, require a scan record **or** a named exemption with reason for every output.
- [ ] Keep (and document) the limitation that the scanner cannot detect arbitrary numeric transformations of sealed values.

**Acceptance:**
- [ ] A sealed value in `.npy` is detected; a clean `.npy` scans to completion.
- [ ] Repro B returns `incomplete` (and fails in strict mode), not `ok`.

---

### T05 (P1) — Project-level artifact dependency validation

**Files:** `contracts/schemas/envelope.json`, `contracts/validate.py`; add a new project-level validator module.

**Reproduce:** an artifact whose input `ref` points to a non-existent file with an incorrect `sha256` string still validates. Status propagation reads only the caller-supplied `inputs[].status` and never resolves the source artifact.

**Scope boundary:** keep the schema validator lightweight and single-file. Add a separate project-level dependency validator; schema validation must not read arbitrary paths.

**Implement:**
- [ ] Within a controlled project root, verify for each ref: existence, artifact ID/type, version, and hash.
- [ ] Derive sticky statuses from the actual source artifacts and check they match what the manifest declares.
- [ ] Missing, substituted, or hash-mismatched sources, or an unpropagated `failed` source status → `error` or `unresolved`, blocking formal downstream steps.
- [ ] Explicitly support an `unresolved` state for external, non-materialized references.
- [ ] Never read files outside the authorized project root (reject path traversal and absolute paths outside it).

**Acceptance:**
- [ ] The repro case is reported as an error.
- [ ] Tests cover: valid chain, missing file, hash mismatch, type/ID mismatch, undeclared failed upstream, external unresolved ref, out-of-root path.

---

### T06 (P2) — ML split grouping completeness

**Files:** `skills/physics-ml/scripts/check_split_integrity.py`.

**Reproduce:** `train=['a']`, `test=['b']` with no groups, or with partial groups `{'a': 'run1'}` → both `passed`. The partial case also reports `groups_checked: true`.

**Root cause:** IDs without a group are skipped; `passed` only means the checks that ran found no leakage.

**Implement:**
- [ ] Add a strict grouping mode; report mapping coverage and the list of missing IDs.
- [ ] In strict mode every sample needs grouping metadata; missing metadata → `incomplete` or `failed`.
- [ ] Report timestamp coverage for time-ordering checks in the same way.
- [ ] r2: status vocabulary is `passed` / `failed` (leakage found) / `incomplete` (metadata missing); `passed` is true only for `passed`. `--strict` turns `incomplete` into `failed` with `failure_kind: missing-metadata`. The existing unit test `test_group_check_is_skipped_without_a_mapping` tests `find_group_leakage()` only and stays as is.

**Acceptance:**
- [ ] A complete, leak-free split passes.
- [ ] Missing metadata and detected leakage produce distinct, clearly labeled outcomes.
- [ ] `groups_checked` is true only when coverage is complete.

---

### T08 (P2) — Citations without a bibliography

**Files:** `skills/research-communication/scripts/check_manuscript.py` — `scan()`.

**Reproduce:** a directory containing only a `.tex` file with `A claim \cite{Nonexistent}.` and no `.bib` → CLI exits `0`, "No issues found".

**Root cause:** the missing-citation check is guarded by `if bib_files`, so no findings are produced when there is no bibliography at all.

**Implement:**
- [ ] Citations present but no resolvable bibliography → `error` or `unresolved`.
- [ ] Support inline bibliographies (`thebibliography`) and externally built inputs through explicit configuration.

**Acceptance:**
- [ ] The repro case does not pass.
- [ ] Separate tests: valid bibliography; document with no citations; declared external build pipeline.

---

### T07 (P2) — Berger–Boos approximation and coverage labeling

**Files:** `core/stats/likelihood_limits.py` — `_p_sup()`, `neyman_limit()`; `tests/core/test_stats_likelihood_limits.py`.

**Finding:** the implementation uses a finite nuisance grid and finite toys, yet the method label claims *guaranteed coverage*. The note discloses grid/toy noise, and the existing coverage test checks only specific parameter points.

**Scope boundary:** undercoverage has **not** been demonstrated. The issue is the mismatch between finite numerical validation and a global-guarantee label. Also check whether generating the Gaussian auxiliary observation truncated to non-negative values is consistent with the fitted likelihood.

**Implement:**
- [ ] Change the primary label to an approximation; distinguish the theoretical construction from its numerical implementation.
- [ ] Add grid-refinement, toy-precision, and true-parameter coverage-scan tests (mark slow tests appropriately so the default suite stays fast).
- [ ] Report outer/inner toy uncertainties and the validated range of applicability.
- [ ] Define and test that auxiliary generation and the likelihood use the same model.
- [ ] r2: the truncation `max(b + sig * z, 0)` appears in the Berger–Boos toys (`_p_at`, `neyman_coverage`) **and** in `_toy_p1` (profile-limit). Fix the Berger–Boos path in this task; record the profile-limit site as an open item instead of changing other commands' outputs here.

**Acceptance:**
- [ ] No output claims global coverage guarantees unless the applicability range has been validated.
- [ ] Coverage scan results are reported with Monte Carlo uncertainties.

---

## 4. Capability and Maintenance Items (not reproduced defects — do only if requested)

- [ ] **C01** Add one end-to-end benchmark on real public data: source, actual values, uncertainties, covariance or missing-covariance prescription, gate, fit, and communication. (The seven AMS dataset records are metadata-only; most end-to-end examples use synthetic data.)
- [ ] **C02** In the capability matrix, separate: guidance-only, contract-tested, executed, validated-in-scope. (Bayesian has no sampler run; recasting is a single-signal-region synthetic example.)
- [ ] **C03** Add live routing and task-completion evaluation: short queries, Traditional Chinese variants, mixed tasks, legacy coexistence, multiple hosts/models. (VALIDATION records 43/48 for run 4; G5-REPORT re-scores it 44/48 after the scorer fix of PR #9. Not re-run in the audit.)
- [ ] **C04** Build a core/optional-tool CI matrix, reproducible environments, and release gates; optional skips are not success evidence. (The ZIP contained no `.github` CI.)
- [ ] **C05** **Human decision — do not act.** Choose a license and verify compatibility of reused content before release. The root README says no license is chosen and not to redistribute. Provide no legal conclusions.

---

## 5. Global Definition of Done

- [ ] Every reproduced issue has a regression test that fails on the original code and passes after the fix.
- [ ] Old and new tests run in an environment with core requirements installed; environment failures, tool skips, and product defects are reported separately.
- [ ] No regressions in legitimate transformations, profiles (including the AMS-02 suite), synthetic/Asimov labels, or skill handoffs.
- [ ] All Phase 0 tool checks still pass.
- [ ] `VALIDATION`, the capability matrix, and release notes (r2: new `CHANGELOG.md`) are updated so that every capability claim matches actual evidence.
- [ ] Nowhere is schema validity, program termination, a single-point coverage check, or static routing success presented as physical validity.

---

## 6. Final Report (deliver at the end)

Produce a report with these sections:

1. **Environment** — OS, Python version, installed core/optional dependencies.
2. **Phase 0 reproduction table** — T01–T08: reproduces / does not reproduce on current code.
3. **Per-task summary** — files changed, regression test names, before/after behavior, design decisions made under Rule 9.
4. **Test results** — counts for each suite (pass / fail / error / skip), with skips and environment errors listed separately from product defects.
5. **Documentation updates** — what changed in VALIDATION, capability matrix, release notes.
6. **Open items** — anything unresolved, deferred, or requiring a human decision (including C05).
