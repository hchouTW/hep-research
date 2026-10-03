# Final Report: hep-statistics reinforcement (S01–S12)

Work order: `tasks/hep-research/stats-reinforcement/TASK.md`, revision r2 (checked against `main` at `dbda2aa`).
Branch `claude/stats-reinforcement-qfy9o9`; final checked commit `bb23947` (this report and VALIDATION are added after it).
All data in tests and walkthroughs are SYNTHETIC.

## 1. Environment

- Claude Code cloud container, Linux 6.18 x86_64, Python 3.11.15.
- Core: numpy 2.4.6, scipy 1.17.1, matplotlib 3.11.2, sympy 1.14.0 (`.venv-hep`).
- Optional, installed with approval: pyhf 0.7.6.
- Not installed in this container: PyTorch, ROOT, uproot/awkward, CMS Combine, Graphviz, PlantUML, Mermaid CLI and tectonic. Their tests skip.
- Network use: read-only WebFetch lookups (INSPIRE, Crossref, arXiv, the Combine docs), approved by the user on 2026-10-03. No paid model calls.

## 2. Phase 0

`phase0_repro.py` printed `reproduces: true` for all eleven findings on `dbda2aa`. On the final branch it prints `reproduces: false` for all eleven.

| ID | Finding | Classification | Fixed by |
|---|---|---|---|
| F1 | Li & Ma written as `sqrt(2)·sqrt(-2 ln λ)`; the docs claimed it was valid at low counts | scientific error + method-claim gap | S01 |
| F2 | The only core/stats usage guide lived in the optional AMS-02 profile | layering inversion + stale docs | S02 |
| F3 | No post-fit nuisance diagnostics (pulls, impacts, breakdown) | capability gap | S04 |
| F4 | Interpolation-code semantics and two-point/one-sided systematics missing | content gap | S03 |
| F5 | No global p-value tool for scans | capability gap | S05 |
| F6 | No Asimov sensitivity, executable GoF or model-comparison guidance | capability gap | S06 |
| F7 | No Bayesian convergence diagnostics | capability gap | S07 |
| F8 | sWeights mentioned only in one line | content gap | S08 |
| F9 | ML-assisted inference validity not written down in hep-statistics | ownership-content gap | S09 |
| F10 | No producer-side likelihood publication guidance | content gap | S10 |
| F11 | `statistical-result` could not record global significance, bands, breakdown or GoF; a scan without a global p passed | contract gap | S11 |

## 3. Per-task summary

The tasks ran in the stated order. Each has its own commit, and each sci-fix or behavior change had its test written first.

- **S01** (`af782a5` sci-fix, `385151d`, `ea5550d`). `li_ma_significance.py` and three references now call the statistic `sqrt(-2 ln λ)` and say its normal reading is asymptotic.
  - New options: `--toys N --seed S` and `--exact-conditional`. The default output is unchanged.
  - Test: `test_li_ma_significance.py`, which failed 8/10 on the old code.
  - At (4, 2, 0.25): asymptotic p 6.646e-3, toys 9.03e-3, exact 0.01696.
  - r2 R9 moved the large-count point to (30, 100, 0.2).
- **S02** (`704c979`). New `core-stats-guide.md`.
  - The AMS modules get pointers, an exit-code fix and two merged duplicate lines. Nothing was deleted (Q3; DECISIONS STATS-01).
  - Test: `test_core_stats_guide.py`.
- **S03** (`2cc47df`). New `nuisance-modeling.md`.
  - Its walkthrough comes from `test_nuisance_interpolation.py` (pyhf).
  - Adapter version 0.5.0.
- **S04** (`ad6e5ae`). New asset `pyhf_nuisance_diagnostics.py`.
  - Impacts match independent refits within 1e-3 rel / 1e-4 abs ([Proposal] tolerance accepted).
  - Test: `test_pyhf_nuisance_diagnostics.py`.
- **S05** (`1231ff4`). New `look_elsewhere.py`.
  - Gross–Vitells agrees with brute-force toys over global p in [1e-3, 0.1]; the range was set before running (r2 R5).
  - Test: `test_look_elsewhere.py`; its slow part runs with `HEP_SLOW_TESTS=1`.
- **S06** (`ab05fab`). New `sensitivity_and_gof.py`, plus Expected sensitivity, GoF and Model comparison sections.
  - Test: `test_sensitivity_and_gof.py`.
- **S11** (`ff79a1e`). Contracts 1.1.0 adds optional fields and two fail-closed rules:
  - `stats.lee_missing`: a scan without a global p is unresolved.
  - `stats.convergence_mismatch`: an error from 1.1.0 on, and a warning for 1.0.0 artifacts (r2 R7).
  - Test: `test_statistical_result_v11.py`, which failed 4/7 on the old code.
- **S07** (`d537a8a`). New `bayes_diagnostics.py` with three subcommands: diagnose, reweight and demo-sampler.
  - The chain configurations were fixed before running (r2 R6).
  - Test: `test_bayes_diagnostics.py`.
- **S08** (`f218b06`). New sWeights section in `likelihood-fitting.md`, with a verified toy walkthrough.
  - Pull width 1.020 with the full sandwich; the naive Hessian is reported as measured (2.799).
  - Broken factorization biases τ to 0.575.
  - Test: `test_weighted_unbinned_fit.py`.
- **S09** (`701b8cb`). New `ml-assisted-inference.md`.
  - Cross-links with physics-ml's `scientific-machine-learning.md`. The ATLAS note sits inside an `<!-- example -->` block.
  - Test: `tests/routing/test_ml_inference_routing.py`. No training code was added.
- **S10** (`7cf7632`). New publishing-likelihoods section in `statistical-tools.md`.
  - Test: `test_pyhf_publication.py`. The background-only workspace plus signal patchset reproduces best fit and CLs within 1e-6, and a digest mismatch is refused.
  - Adapter version 0.6.0.
- **S12** (`d742044`, `a5ab30a`, `bb23947`). Integration:
  - SKILL.md Resources links every new reference, script and asset (7621 B, under the 8192 B budget). The description is unchanged.
  - Eight routing cases, three in zh-Hant.
  - New capability rows and CHANGELOG entries.
  - The 23 new files are registered in `provenance-new.csv`.

Open questions as answered: Q1 yes (pyhf, read-only lookups), from the user. Q2–Q5 took the defaults: stay dependency-light, pointers only, accept the [Proposal] tolerances, no paid live routing.

## 4. Test results

| Suite | Run | Pass | Fail | Error | Skip |
|---|---|---|---|---|---|
| Unit tests (final, `check-run-2026-10-03T044810Z.json`) | 1165 | 1115 | 0 | 0 | 50 |
| Profile suites ams-02 / synthetic-collider / qed-benchmark | 258 / 9 / 16 | all | 0 | 0 | 0 |
| Slow tests, `HEP_SLOW_TESTS=1`, four new statistics modules | 34 | 34 | 0 | 0 | 0 |
| run_all_checks aggregate | 14 checks | 14 | 0 | – | 0 |
| check_relocation (path with spaces, outside the repo) | 14 checks | 12 | 0 | – | 2 |

- Skip breakdown: 46 skips are optional tools missing from this container (PyTorch 17, ROOT/PyROOT 12, uproot/awkward 11, diagram tools 4, Combine 1, tectonic 1), and 4 are slow tests that were run separately.
- No product defect is hidden by a skip. All pyhf-dependent tests ran.
- The first full run found one defect in this work: SKILL.md named the S04 asset by its bare file name, which the resource test cannot resolve. It was fixed in `bb23947`, and the rerun above is clean.

## 5. Documentation updates

- VALIDATION: new `STATS-REINFORCEMENT-RUN` section.
- Capability matrix: seven new rows, plus the S07 Bayesian row.
- CHANGELOG: the "Unreleased (hep-statistics reinforcement)" entry.
- DECISIONS: STATS-01 (S02 pointers; M6-02 stands).
- Architecture doc: contract 1.1.0.

## 6. Citations

All checked on 2026-10-03; the details are in `citations.md`. Corrections applied in the plugin:

- Conway is a PHYSTAT 2011 proceedings paper (doi 10.5170/CERN-2011-006.115), not a journal article.
- Talts et al. and Cranmer–Pavez–Louppe are preprints.
- The ATLAS NSBI note is now Rep. Prog. Phys. 88 (2025) 067801.
- For Vehtari et al. the start page is not quoted; the DOI is used instead.
- Gross–Vitells is eq. 3, written as a bound.
- Cowan et al. 2011 is cited with its erratum (EPJC 73 (2013) 2501).
- The Cowan 2012 σ_b formula is eq. 20 of an unpublished note.

The Combine documentation facts were read but not executed, because Combine is not installed here.

## 7. Open items and deviations

- **Deviation from Rule 4 / byte-identical examples.** The contract bump to 1.1.0 (S11) changed the version string in 25 committed example artifacts. They were regenerated, and the diff is the version string only; results, reports and figures are byte-identical.
- **Provenance register.** On this shallow clone, `check_traceability.py --write-new` would rewrite the commit and milestone columns of existing rows. So the 23 new rows were appended, and the existing rows were kept as they were.
- **Not done by decision:** C01–C04, cabinetry and sampler packages, and a paid live routing run for the new cases (static routing passes).
- **Limits that remain:**
  - Look-elsewhere covers one-dimensional scans only.
  - No production Bayesian sampler is shipped.
  - sWeights and NSBI are guidance plus a toy walkthrough, not a fitting tool.
  - The Combine parts of the nuisance-modeling reference are documentation-based.
- **Carried over from the audit:** the profile-limit toys still truncate the auxiliary observation at 0.
