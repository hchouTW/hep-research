# Capability matrix (v0.4.0)

Status words: **tested** = exercised by a check that passed in the environment named below; **unverified** = code or
guidance exists but its tool was not installed, so it was not run; **proposed** = a starting point or design, not
executed; **not in v1** = outside scope, handled by the limited-support response. "Tested" means contract and
software consistency only, not physical validity, proof, statistical coverage, or authorization to unblind.

Environment E1 (all "tested" rows): Claude Code cloud container, Linux 6.18 x86_64, Python 3.11.15, NumPy 2.4.6,
SciPy 1.17.1, Matplotlib 3.11.2, SymPy 1.14.0, Claude Code CLI 2.1.287, 2026-10-02. Evidence: [VALIDATION.md](../VALIDATION.md).

Environment E2 (rows marked "E2" below): macOS 26.5 arm64 (Apple M3), Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1,
Matplotlib 3.11.2, SymPy 1.14.0, Claude Code CLI 2.1.288, 2026-10-04 at `dd9b940`. E2 results do not replace E1
results; they are listed in "E2 results" at the end. Evidence: VALIDATION FULLTEST-E2.

Environment E3 (rows marked "E3" below): Linux (EL9), x86_64, Python 3.11.13, NumPy 2.4.6, SciPy 1.17.1,
Matplotlib 3.11.2, SymPy 1.14.0, Claude Code CLI 2.1.287, codex-cli 0.160.0, 2026-10-05 at `e296b9b` (plugin 0.2.1). E3 results do not replace E1 or E2
results; they are listed in "E3 results" at the end. Evidence: VALIDATION FULLTEST-E3.

## Capabilities

| Capability | Owner | Status | Evidence or reason |
|---|---|---|---|
| Measurement specs, correlated ratios, time-dependent exposure | hep-analysis | tested (E1) | Path A, T10, T11 |
| Systematic-variation classification (shape vs normalization) | hep-analysis | tested (E1) | T12 |
| Blinding: masks, sealing, scans of plots, logs, CSV and caches | hep-analysis, core | tested (E1) | T18; AUDIT T04: `.npy` caches read, scans report pass / fail / incomplete (an unreadable output is never a pass), strict publication mode with named exemptions. A pass cannot see transformed values |
| Analysis-change review (tuning after unblinding flagged) | hep-analysis | tested (E1) | T19 |
| Response objects, forward folding, double-counting checks | detector-response | tested (E1) | Path B, T07 |
| Resolution and efficiency studies (detector level) | detector-response | tested (E1), synthetic detector | J2 example (`examples/detector-resolution/`) |
| Unfolding | hep-statistics | demonstrated on synthetic data (E4) | `examples/unfolding-coverage/` (4,000 seeded toys, 10 bins): inversion unbiased with per-bin 68% coverage 0.675–0.69; Tikhonov at relative strength 1e-2 and 1e-1 undercovers (minimum 0.599 and 0.238) with largest bias 0.58 and 1.69 sigma; 6-of-10 TSVD bias up to 17.5 sigma; `core/stats/unfolding_diagnostics.py` closure, L-curve and cross-validation tests; `examples/collider-angular/` full-rank unfolding with toy closure; response exactly known, D'Agostini not in the example, no real data |
| Theory specs, conventions, analytic derivation status | hep-theory | tested (E1) tree-level QED; tested (E4) fixed-order QCD for R | Path C, T13, T14 |
| Numerical checks and convergence studies | hep-theory, hep-computing | tested (E1) | T15 |
| Higher-order predictions: scale dependence from the RGE, envelope, truncation and parametric uncertainty kept apart | hep-theory | tested (E4), one observable (R in e+e-, massless, photon exchange) | `theory:qcd-r-ratio` |
| PDF uncertainty combination by error type (symmetric/asymmetric Hessian, replicas) | hep-theory | demonstrated-on-synthetic-data | `pdf_uncertainty.py` on constructed member values; LHAPDF not installed, API unverified |
| Generator weights: full-production normalization, negative fraction, effective sample size | hep-theory | demonstrated-on-synthetic-data | `event_weights.py`; no generator run |
| SMEFT/EFT conventions and linear vs quadratic truncation bookkeeping | hep-theory | demonstrated-on-synthetic-data | `eft_truncation.py`; coefficients are inputs; global fits, RG running and basis translation not in v1 |
| Competing models kept distinct; envelopes only by prescription | hep-theory | tested (E1) | T03 |
| Recasting with parametrized response | hep-theory, detector-response, hep-statistics | tested (E1), synthetic, one signal region | J7 example (`examples/recasting/`); interchange formats still proposed |
| Comparison gate (observable definition: process, species, phase space; units, level, every axis and its binning, conventions, corrections) | hep-statistics, contracts | tested (E1) | Path D, T08, T25; AUDIT T01: free-text definitions that differ are `unresolved` until a justified mapping is declared |
| Artifact payload consistency (axes, units, representation, finite numbers) | contracts | tested (E1) | AUDIT T02 |
| Project-level artifact dependencies (refs inside a project root, type/ID/version, sha256, upstream statuses) | contracts | tested (E1) | AUDIT T05 (`contracts/dependencies.py`); external refs stay `unresolved` |
| Binned Poisson likelihoods with nuisance parameters, toys | hep-statistics | tested (E1) | Path D, low and zero counts |
| Template fits with Barlow-Beeston (fit diagnostics; infeasible or unconverged fits reported failed) | hep-statistics, core | tested (E1) | AUDIT T03 |
| Barlow-Beeston template fit with empty MC bins (a template's true content kept as a nuisance where its MC has none) | hep-statistics, core | tested (E2, 2026-10-08) | `core/stats/template_fit.py`: the profiled bin equals a brute-force maximum over the true contents for five bin configurations; 300 toys with MC samples of about 60 and 85 events in 8 bins: no Barlow-Beeston fit fails (the naive fit is infeasible in about one toy in five), 1-sigma coverage above 0.56 and robust pull width below 1.3 (`ZeroMcBinTests` in `tests/core/test_stats_template_fit.py`); Hessian errors still under-cover slightly with so little MC |
| Berger-Boos upper limit (single-bin background nuisance) | hep-statistics, core | tested (E1) as an approximation: coverage validated by a seeded 36-point scan in `BB_VALIDATED_RANGE` only | AUDIT T07; outside that range the implementation's coverage is unvalidated, and no global coverage guarantee is claimed |
| Combinations (GLS) with declared correlations | hep-statistics | tested (E1), Gaussian only | T04, T05, T09 |
| Comparison with published records, no detector modules | hep-statistics | tested (E1) | T24 (synthetic published-style record) |
| Bayesian inference (samplers, priors, convergence) | hep-statistics | tested (E1) for convergence diagnostics on supplied chains, prior reweighting, and a demonstration Metropolis sampler on one counting model | T28; STATS S07 (`bayes_diagnostics.py`): R-hat, bulk/tail ESS and quantile MCSE on seeded synthetic chains; the demo sampler reproduces the flat-prior bound for n = 0, b = 0. No production sampler is shipped or tested |
| ON/OFF significance (Li & Ma) with toy-calibrated and exact conditional p-values | hep-statistics | tested (E1) | STATS S01 (`li_ma_significance.py`, `test_li_ma_significance.py`): the statistic is labeled asymptotic; low-count p-values come from seeded toys or the exact conditional binomial test |
| Global significance of 1D scans (look-elsewhere: brute-force toys, Gross-Vitells bound) | hep-statistics | tested (E1), one-dimensional scans only | STATS S05 (`look_elsewhere.py`): the bound agrees with brute-force toys for global p in [1e-3, 0.1] in the slow test (`HEP_SLOW_TESTS=1`, run in STATS-REINFORCEMENT-RUN); multi-dimensional scans are not implemented |
| Expected discovery sensitivity (Asimov, with a background uncertainty) and toy-calibrated goodness of fit | hep-statistics | tested (E1) | STATS S06 (`sensitivity_and_gof.py`): Asimov Z matches a numerical profile to 1e-6; toy p-values uniform for a correct model (KS, slow test) |
| Weighted unbinned fits and sWeights (covariance) | hep-statistics | guidance, with a tested (E1) toy walkthrough | STATS S08 (`test_weighted_unbinned_fit.py`): full sandwich pull width 1.020 over 300 toys; no fitting script is shipped |
| Unweighted extended unbinned ML fit (one observable, Gaussian peak + exponential background) with Hessian and profile intervals | hep-statistics | demonstrated on synthetic data (E4) | `adapters/unbinned-fit` (SciPy 1.18.1): 300 seeded toys (150 signal, 800 background), 0 failed fits, Hessian 68% coverage 0.66–0.72 per parameter and profile coverage of the signal yield 0.687 (binomial standard error 0.027), pull widths 0.96–1.07 (`tests/adapters/test_unbinned_fit.py`); weighted fits and other shapes not covered |
| ML-assisted inference validity (NSBI, SBC, classifier observables) | hep-statistics | guidance only | STATS S09: reference text and static routing checks; no ML inference is executed |
| Post-fit nuisance diagnostics for pyhf (pulls, constraints, impacts, grouped breakdown, correlations) and interpolation comparison | hep-statistics | demonstrated on synthetic data (E1 + pyhf 0.7.6) | STATS S03, S04 (`pyhf_nuisance_diagnostics.py`): impacts match independent refits to 1e-3 relative; skipped, and then unverified, without pyhf |
| Likelihood publication (background-only workspace plus signal patchset) | hep-statistics | demonstrated on synthetic data (E1 + pyhf 0.7.6) | STATS S10 (`test_pyhf_publication.py`): the patched workspace reproduces best fit and CLs to 1e-6; skipped, and then unverified, without pyhf |
| HistFactory / pyhf workflows | hep-statistics | demonstrated on synthetic data (E1 + pyhf 0.7.6), asymptotic CLs | counting and two-channel shape workspaces (normsys, histosys, staterror, shapesys) match an independent likelihood in log-likelihood, best fit and limit (`tests/adapters/test_pyhf_counting.py`, `test_pyhf_shape.py`); end-to-end sample passes; toy-based CLs and other modifier types not tried |
| Asymptotic CLs limit and expected 1/2-sigma bands (CLs and CLs+b) from the Asimov data set | hep-statistics, core | tested (E2, 2026-10-08) | `likelihood_limits.py` multibin-limit and shape-limit (Cowan et al. 2011, sec. 4.3; q-tilde form of the CLs+b bands below the median): one bin matches the closed-form Asimov statistic to 1e-5; the five bands match the quantiles of 400 (known background) and 300 (common scale) background-only toys within 12–14% (`tests/core/test_stats_asymptotic_bands.py`); at a few events per bin the asymptotic bands are wider than the toys, so use toys there |
| HistFactory interpolation codes in shape-limit (code0, code1, code4 for asymmetric normalization factors; code0, code4p for shapes) | hep-statistics, core | tested (E2, 2026-10-08) | `likelihood_limits.py` reproduces the pyhf 0.7.6 interpolators to 1e-9 on a grid of θ in [-2.5, 2.5] for three factor pairs and two shape bins (live check skipped without pyhf; hard-coded pyhf values always checked); code4 and code4p are smooth at 0 and join value, slope and curvature at ±1; an Asimov set made at known θ is fitted back to within 2e-3 (`tests/core/test_stats_interpolation.py`) |
| Barlow-Beeston-lite MC statistics (per-bin `mc_stat`) in multibin-limit and shape-limit | hep-statistics, core | tested (E2, 2026-10-08) | `likelihood_limits.py`: a per-bin Gaussian factor on the background, profiled in closed form; with background templates from 25 effective MC events per bin, 1000 pseudo-experiments cover at 0.95 ± 0.025 with it and below 0.92 without; the multibin and shape-limit implementations agree (mc_stat alone, and with a common scale versus a Gaussian normalization) (`tests/core/test_stats_mc_statistics.py`); with about 9 effective events (33%) the Gaussian factor over-covers (0.98) |
| Toy-based CLs for the multi-bin shape-limit (observed and expected 1/2-sigma limits) | hep-statistics, core | tested (E2, 2026-10-08) | `likelihood_limits.py shape-limit --cls-toys N`: a grid in μ with common random numbers, CLs+b toys at the nuisances profiled at μ and CLb toys at μ = 0, expected limits from the background-only quantiles of the same toys; one bin with a known background reproduces the exact Poisson CLs limit (3000 toys; a 40-seed scan gives 5.412 ± 0.046 against 5.395), and with a normalization nuisance at large counts it agrees with the asymptotic CLs within 12% (observed) and 15% (median) (`tests/core/test_stats_toy_cls.py`); cost is two fits per toy, hypothesis and grid point |
| Profile-likelihood contours of two signal strengths | hep-statistics, core | tested (E2, 2026-10-08) | `likelihood_limits.py contour`: best fit, Hessian covariance and the Wilks 2-dof contours (default 68.27% and 95%) traced along rays, with the shape-limit nuisances (no signal shapes) and `mc_stat`; 2000 toys at the true point give coverage within 0.035 (68%) and 0.015 (95%) of nominal with and without a normalization nuisance; every contour point lies on the level of an independent Poisson deviance to 2e-4 (`tests/core/test_stats_two_poi.py`); a non-star-shaped region is not traced, and Wilks needs enough events per bin |
| Combination of asymmetric uncertainties (Barlow's methods) | hep-statistics | tested (E2, 2026-10-08) | `skills/hep-statistics/scripts/combine_asymmetric.py`: measurements by the linear-variance or linear-σ likelihood, sources by cumulants with a quadratic or piecewise model; 800 sets of three 6-decay lifetime measurements against the exact pooled likelihood: central value within 0.05 of an error on average, errors within 10%, coverage within 0.05 of the exact interval's; sources match the cumulants, median and 16/84% quantiles of a 100k Monte Carlo sum; symmetric inputs reduce to the weighted mean and to quadrature (`tests/skills/hep_statistics/test_combine_asymmetric.py`); correlations between measurements are not modeled |
| Saturated-model goodness of fit of a likelihood with nuisances | hep-statistics, core | tested (E2, 2026-10-08) | `likelihood_limits.py shape-gof`: Poisson bins and constraint terms against the saturated model, μ fitted or fixed, toy-calibrated from the fitted model with auxiliary measurements redrawn; 500 null data sets at 10–36 events per bin follow χ²(4) (mean within 0.4, tail fraction within 0.03); at 1–4 events per bin the toy p-value is uniform over 200 data sets while the χ² reference is not; equals an independent Poisson deviance without nuisances (`tests/core/test_stats_saturated_gof.py`). The template-yield GoF without nuisances stays in `sensitivity_and_gof.py gof` |
| Reproduce a published result from an open full likelihood (BkgOnly + patchset) | hep-statistics | unverified on a real record; script demonstrated on synthetic data (E4 + pyhf 0.7.6) | `adapters/pyhf-combine/assets/reproduce_published_likelihood.py`: digest check, patch, best fit and asymptotic CLs compared with published values under stated tolerances (`tests/adapters/test_pyhf_published_reproduction.py`: reproduces, fails on a 0.01 shift, incomplete when a value is not provided, refuses a digest mismatch); intended anchor ATLAS-SUSY-2018-31 (HEPData ins1748602) not run: hepdata.net is not reachable from E4 |
| Local partition, resubmission, merge | hep-computing | tested (E1) | T21 |
| Batch campaigns on Slurm and HTCondor (job arrays / item-data clusters, duplicate-safe collection, bounded explicit resubmission, watch with limits, provenance) | hep-computing, core | documented; protocol tested (E1) against fake schedulers only | BATCH B01–B13: `core/partition` campaign and runner tests, `tests/adapters/test_batch_*.py`, `examples/batch-partition/` (byte-reproducible); no real Slurm or HTCondor run, tool facts checked on 2026-10-03 against the Slurm 26.05 and HTCondor 25.13 documentation (a few formats are not stated there and stay to be confirmed on a real run) |
| uproot/awkward tools | hep-computing | demonstrated on synthetic data (E1 + uproot 5.7.6, awkward 2.14.0) | synthetic NanoAOD-like files written and read; `uproot_awkward_analysis.py` histogram and sum(w^2) match numpy (`tests/adapters/test_uproot_awkward_asset.py`) |
| ROOT, PyROOT tools | hep-computing | demonstrated on synthetic data (ROOT 6.40.04, conda-forge) | PyROOT scripts and assets (inspection, histogram comparison, systematics, RooFit workspace and fit), C++ RDataFrame/fit assets built with root-config and CMake, batch macro; C++ cutflow equals the PyROOT cutflow (`tests/adapters/test_root_cpp_assets.py`, `test_root_integration.py`) |
| Task files for coding agents (task authoring) | hep-computing | tested (E1) | bundle validator, lint_task tests |
| Split integrity, surrogate domain, ML artifact checks | physics-ml | tested (E1) | T16; AUDIT T06: group and timestamp coverage reported, missing metadata is `incomplete`, not a pass |
| PyTorch training, inference, profiling assets | physics-ml | tested (E1 + PyTorch 2.14.1 and torchvision 0.29.1, CPU only) | asset smoke tests (training, inference, datasets, allocation measurement) and a 2-process DDP run on the gloo backend pass; `vision_transfer.py` trains one epoch on a synthetic ImageFolder with an untrained ResNet-18 (TORCHVISION-RUN); GPU, NCCL, mixed precision on GPU and the pretrained-weight download not tried |
| Claims linked to results, status preserved in text | research-communication | tested (E1) | T20 |
| Manuscript pre-submission check (citations, bibliography, labels) | research-communication | tested (E1) | AUDIT T08: citations with no bibliography fail; inline `thebibliography` and `.bbl` resolve; an external bibliography leaves keys `unresolved` |
| Literature and citation verification online | research-communication | unverified | needs network; offline it marks citations unverified |
| Diagram source checks (Graphviz, Mermaid, PlantUML) | research-communication | tested (Graphviz 14.1.2, PlantUML 1.2026.8, Mermaid CLI 12.0.0 with Chromium 141, project-local) | real `dot`, `mmdc` and `plantuml` accept valid and reject invalid sources; every shipped diagram source passes `check_diagram_sources.py` (`tests/skills/research_communication/test_diagrams.py`) |
| Paper builds (tectonic) | research-communication | unverified | tectonic 0.17.0 installed, but the network policy blocks its TeX bundle host (relay.fullyjustified.net), so the skeleton compile test stays skipped (VALIDATION DIAGRAM-RUN) |
| Lattice QCD, EFT global fits, cosmic-ray propagation, other domains | none | not in v1 | limited-support response (J12) |
| Cosmic-ray propagation (model families, inputs, degeneracies) | hep-theory | guidance only; fits not in v1 | `skills/hep-theory/references/cosmic-ray-propagation.md`; no propagation code (GALPROP, DRAGON, USINE) installed or run, nothing tested |
| Environment manifest and drift check for a run | hep-computing | tested (E2, 2026-10-08) | `environment_manifest.py`: Python, platform, origin (LCG view, container, conda, venv, system), package versions, a fixed list of variables (never others) and the git commit, in the `computational-run` shape; `check` reports every drift (`tests/skills/hep_computing/test_environment_manifest.py`) |
| Systematics table as booktabs LaTeX | hep-analysis | tested (E2, 2026-10-08) | `systematics_table_tex.py`: status label required and carried into the caption; output compiled with pdflatex (`tests/skills/hep_analysis/test_systematics_table_tex.py`) |

## Profiles

| Profile | Kind | Status | Evidence |
|---|---|---|---|
| `experiment:ams-02` | experiment | tested (E1) for the public evidence ledger and domain modules; dataset records are metadata only, no values | public profile only: evidence ledger (60 sources, 184 claims) rendered into `evidence/index.md`, domain modules under `modules/methods/`, the analysis-spec audit (`scripts/audit_analysis_spec.py`), and the papers and CRDB helpers (`scripts/fetch_papers.py`, `scripts/crdb_query.py`); profile tests under `profiles/experiments/ams-02/tests/`; AC08, AC09. Restricted software and data content (experiment software environment, library map, data catalogues, ntuple producer) now lives in the separate access-controlled `ams02-research` companion plugin and is not part of this matrix |
| `experiment:synthetic-collider` | experiment (illustrative, invented detector) | tested (E1) | 9 profile tests; Path B; AC10 |
| `experiment:eic` | experiment (EIC facility context and ePIC experiment, public documents only) | documented (E2) for the facility, detector and software modules; tested (E2) for the ledger (5 sources, 9 claims; one Tier 3 context claim) and five static routing scenarios; `software-execution` unavailable; no datasets, no performance numbers | 43 profile tests; `examples/eic-profile-routing/`; VALIDATION EIC-PROFILE, VALIDATION EIC-FOLLOWUPS |
| `theory:qed-benchmark` | theory domain | tested (E1), tree level only | 16 profile tests; Path C |
| `theory:qcd-r-ratio` | theory domain | tested (E4), massless QCD corrections to R through alpha_s^4, photon exchange only | 19 profile tests (derivation, prediction, convention mismatches); PDG eqs. 9.3, 9.7-9.9 and Table 1.1 read 2026-10-07 |
| Private local profiles | any | tested (E1) with a fixture | T27 |

## Adapters

| Adapter | Status | Notes |
|---|---|---|
| `adapters/pyhf-combine` (pyhf JSON, Combine datacard template) | demonstrated-on-synthetic-data | adapter status is its least-tested tool: pyhf part demonstrated-on-synthetic-data (pyhf 0.7.6); Combine part demonstrated-on-synthetic-data (Combine 11.1.0 with ROOT 6.40.04 and 6.36.14: with `--strictBounds` the filled datacard gives observed 2.1518 and median expected 2.1562 against pyhf 2.153 in both; without it ROOT 6.40 rejects an out-of-range r, COMBINE-ROOT640) |
| `adapters/root-uproot` (ROOT, RDataFrame, RooFit, uproot/awkward assets, coffea template, ROOT-to-Parquet) | demonstrated-on-synthetic-data | ROOT 6.40.04, uproot 5.7.6 and awkward 2.14.0 each run on synthetic fixtures; the coffea 2026.9.0 template reproduces the synthetic NanoAOD generator's answers for any chunking and the Parquet converter (pyarrow 25.0.1) writes every entry once with jagged branches (E2, `tests/adapters/test_columnar_assets.py`); not run on real experiment files |
| `adapters/batch-schedulers` (Slurm job arrays, HTCondor clusters, campaign CLI) | documented | both tools `documented`: the backends are tested only against fake schedulers (`tests/adapters/batch_shims`); real-tool tests are gated by `HEP_SLURM_TEST` / `HEP_HTCONDOR_TEST` and skipped |
| `adapters/hepdata` (HEPData table and covariance/correlation table to dataset-record, and dataset-record or prediction to a HEPData submission) | demonstrated-on-synthetic-data | export: `hepdata_export.py` writes `submission.yaml`, the table and its covariance table, keeps the status in the comment, descriptions and `phrases`; hepdata-validator 0.3.6 accepts both the plain and the hepdata_lib 0.21.0 engine, and the importer reads the export back with the same values and covariance (E2, `tests/adapters/test_hepdata_export.py`). Import: synthetic tables in the HEPData layout only (`tests/adapters/test_hepdata_record.py`); no real record read, because hepdata.net is not reachable from E4; the adapter refuses gaps, unnamed covariance components, asymmetric or non-PSD matrices and published records without a ledger claim |
| `adapters/unbinned-fit` (extended unbinned ML fit, toy coverage) | demonstrated-on-synthetic-data | SciPy 1.18.1 on synthetic toys only; convergence judged by a repeat minimizer pass and EDM < 1e-3, failed fits counted, never dropped |
| `adapters/recasting` (MadGraph5_aMC@NLO, Rivet, Delphes, SModelS, MadAnalysis 5 templates) | documented | starting templates and `skills/hep-theory/references/recasting-toolchain.md` (route choice, what to record, cutflow validation before use); none of the tools installed on E2, so no template has been run; structure checked by `tests/adapters/test_recasting_templates.py` |
| `adapters/environments` (LCG view on CVMFS, Apptainer definition) | documented | templates only: CVMFS and Apptainer are not available on E2, so neither was sourced or built; `sh -n`, the refusal on a missing view and the definition's sections are checked by `tests/skills/hep_computing/test_environment_manifest.py` |
| Interchange formats for recasting and published data | proposed | named as optional in the J7 trace; no code |

## Hosts

| Host | Status | Notes |
|---|---|---|
| Claude Code (plugin, development marketplace) | tested (E1, CLI 2.1.287) | install, discovery, namespaced invocation, profile access, removal, coexistence with standalone skills (G5); routing quality not yet established |
| Claude Code × macOS (E2, CLI 2.1.288) | tested | install, discovery, namespaced invocation, profile access through `<plugin root>` (no host variable), removal (MULTIHOST M05) |
| Codex CLI × macOS (E2, CLI 0.160.0) | tested | `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json`: install, discovery, invocation by name, profile access through `<plugin root>`, removal; with and without `~/.agents/skills` (MULTIHOST M05) |
| Codex CLI routing × macOS (E2, CLI 0.160.0, gpt-6.1-sol, plugin only) | tested: 61/62 | all 62 cases of the 2026-10-04 set (118 cases since 2026-10-07; not rerun on Codex) (en 41/42, zh-Hant 20/20); the one miss is fold-and-fit (`j05`) going to hep-statistics; 0 loading violations (MULTIHOST M08) |
| Claude Code × Linux at 0.2.0, Codex CLI × Linux | not tested | Linux cells deferred (MULTIHOST Q3); Claude Code on Linux was tested at 0.1.0 (E1 row above) |
| Claude apps: Chat and Cowork | documented, not tested | install by marketplace (`hchouTW/hep-research`) or `.zip` upload, from Anthropic's documentation (README "Install and remove"); Chat has no local project access |
| ChatGPT | documented, not tested | not in the public plugin directory; admin marketplace import unverified; per-skill `.zip` upload loses the shared plugin folders (README "Install and remove") |
| Antigravity, other agents | not tested | see `skills/hep-computing/references/host-notes.md` |

## E2 results (FULLTEST-E2, 2026-10-04)

| Capability or tool | E2 status | Evidence or reason |
|---|---|---|
| Core checks, profile suites, examples | tested (E2) | 14 of 14 aggregate checks pass at `e54707d`; all ten examples rerun byte-identically on E2; committed output equal or numerically equal, with the `ams-flux-ratio` toy-closure summary equal at Monte Carlo precision |
| pyhf workflows | tested (E2 + pyhf 0.7.6) | adapter and statistics tests pass |
| uproot/awkward tools | tested (E2 + uproot 5.7.6, awkward 2.14.0) | `test_uproot_awkward_asset` passes |
| ROOT, PyROOT tools | tested (E2 + ROOT 6.38.04, Homebrew, PyROOT under Python 3.14) | ROOT C++ assets, PyROOT integration and scripts pass; older than the E1 version 6.40.04 |
| CMS Combine | unverified (E2) | no `combine`, no Docker |
| PyTorch assets | tested (E2 + PyTorch 2.14.1, torchvision 0.29.1, CPU) | the 2-process gloo DDP run passes with `--standalone --local-addr=127.0.0.1`, also with an unresolvable host name (FULLTEST-E2-FOLLOWUPS) |
| Diagram source checks | tested (E2: Graphviz 16.1.0, PlantUML 1.2026.8, Mermaid CLI 12.0.0 with chrome-headless-shell 154) | Homebrew `mermaid-cli` needs a separate `chrome-headless-shell` install |
| Batch campaigns | protocol tested (E2) against fake schedulers; real Slurm/HTCondor unverified | no `sbatch`, no `condor_submit` |
| Relocation (AC24) | tested (E2) | copy of the git-listed files at a path with spaces passes, also with an ignored venv in the tree; the Codex check that needs the repository skips in the copy |
| Claude Code (plugin, isolated config) | tested (E2, CLI 2.1.288): install, discovery, namespaced invocation, profile access, removal | invocation run once the isolated config was logged in (FULLTEST-E2-ROUTING follow-ups) |
| Live routing | tested (E2, claude-sonnet-5-5, plugin only, the 62 cases of 2026-10-04): 56/62; superseded by the 118-case row below | 3 quick questions answered without a skill; 1 case without inputs; 2 neighbor-skill choices (fold-and-fit, SMEFT out of v1); 0 loading violations (FULLTEST-E2-ROUTING) |

## E3 results (FULLTEST-E3, 2026-10-05)

| Capability or tool | E3 status | Evidence or reason |
|---|---|---|
| Core checks, profile suites, examples | tested (E3) with one failure | 17 of 18 aggregate checks pass at `e296b9b`; unit 1281 run, 1253 pass, 1 fail, 27 skip; profile suites 265, 43, 9, 16 pass. The failure: `theory-comparison` committed output, q at μ = 1.15 is 2.5e-9 against 0.0 (abs 1e-12). Ten of eleven examples rerun byte-identically; `qed-prediction` differs between a cold and a warm bytecode cache (`profile_files_read`) |
| pyhf workflows | tested (E3 + pyhf 0.7.6) | adapter tests pass |
| uproot/awkward tools | tested (E3 + uproot 5.7.6, awkward 2.14.0) | `test_uproot_awkward_asset` passes |
| ROOT, PyROOT tools | tested (E3 + ROOT 6.40.04, EL9 system package, C++17, g++ 11.5.0, PyROOT under Python 3.9.25 via `HEP_ROOT_PYTHON`) | ROOT C++ assets (5) and PyROOT integration (7) pass |
| CMS Combine | unverified (E3) | no `combine`; no CMSSW area set up |
| PyTorch assets | tested (E3 + PyTorch 2.14.1, torchvision 0.29.1, CPU; FULLTEST-E3-FOLLOWUPS) | physics-ml tests 130 run, 128 pass, 2 skip (meaningful only without PyTorch; they pass without it), including the 2-process gloo DDP run; FULLTEST-E3 itself ran without PyTorch (17 tests skipped) |
| Diagram source checks | partly (E3: Graphviz 2.44.0); Mermaid CLI, PlantUML, tectonic unverified | not installed (3 tests skip) |
| Batch campaigns | protocol tested (E3) against fake schedulers; HTCondor 25.0.14 **dry run only**: the rendered submit file parses with `condor_submit -dry-run` (2 procs) after its item-list path is made to exist; Slurm unverified (no `sbatch`) | status stays documented; no real submission |
| Relocation (AC24) | tested (E3) | two target locations on the same host: identical results (14/1/3 checks; the failure is the `theory-comparison` one, the skips are the checks that need the repository or a host CLI) |
| Claude Code (plugin, isolated config) | tested (E3, CLI 2.1.287): install, discovery (seven skills, plugin path inside the copy), removal; namespaced invocation unverified | the isolated config was not logged in |
| Codex CLI (plugin load) | tested (E3, codex-cli 0.160.0) | `codex-plugin-load` check: install from the repository marketplace into a throwaway `CODEX_HOME` and list at 0.2.1 |
| Live routing | not run (E3) | not approved (Q2) |

## E4 results (2026-10-07)

| Capability or tool | E4 status | Evidence or reason |
|---|---|---|
| Live routing harness (`evals/routing/`, outside the plugin) | documented; tested with a fake CLI | `run_routing_eval.py`: one pass per case, read-only tools, pinned model, budgets, contamination stop, strict and lenient scoring, baselines per CLI, version and model; harness tests in `evals/routing/tests/` (no model calls); 150 cases (en, zh-Hant, zh-Hans, ja, de; adversarial, quick, multi-turn) pass the static check; live cost probe (E2, CLI 2.1.293, claude-sonnet-5-5, setting-sources isolation): 5/5 strict on a quick, a Japanese, an adversarial, a two-turn and a German case, $0.455 ($0.076 per prompt turn); full run 2026-10-08 (same setup, 150 cases): **143/150** strict, $11.67 (en 88/93, zh-Hant 40/42, zh-Hans, ja, de 5/5 each; adversarial 6/6, quick 5/7, multi-turn 2/4, underspecified 1/3); 0 loading violations; committed as the baseline |
| Live routing, claude-sonnet-5-5 | tested (E4, CLI 2.1.292, plugin only, 118 cases): 113/118 | en 73/77, zh-Hant 40/41; misses: 2 underspecified cases without a clarifying question, 2 quick questions without a skill, 1 neighbor skill; 0 loading violations |
| Live routing, claude-haiku-4-5 | tested (E4, same setup): 37/118 | 72 runs loaded no skill; descriptions alone do not route this model reliably |
| Live routing, Codex | not run (E4) | the user's decision, 2026-10-07 |
