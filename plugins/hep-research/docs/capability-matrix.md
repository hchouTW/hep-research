# Capability matrix (v0.1.0)

Status words: **tested** = exercised by a check that passed in the environment named below; **unverified** = code or
guidance exists but its tool was not installed, so it was not run; **proposed** = a starting point or design, not
executed; **not in v1** = outside scope, handled by the limited-support response. "Tested" means contract and
software consistency only, not physical validity, proof, statistical coverage, or authorization to unblind.

Environment E1 (all "tested" rows): Claude Code cloud container, Linux 6.18 x86_64, Python 3.11.15, NumPy 2.4.6,
SciPy 1.17.1, Matplotlib 3.11.2, SymPy 1.14.0, Claude Code CLI 2.1.287, 2026-10-02. Evidence: [VALIDATION.md](../VALIDATION.md).

Environment E2 (rows marked "E2" below): macOS 26.5 arm64 (Apple M3), Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1,
Matplotlib 3.11.2, SymPy 1.14.0, Claude Code CLI 2.1.288, 2026-10-04 at `dd9b940`. E2 results do not replace E1
results; they are listed in "E2 results" at the end. Evidence: VALIDATION FULLTEST-E2.

## Capabilities

| Capability | Owner | Status | Evidence or reason |
|---|---|---|---|
| Measurement specs, correlated ratios, time-dependent exposure | hep-analysis | tested (E1) | Path A, T10, T11 |
| Systematic-variation classification (shape vs normalization) | hep-analysis | tested (E1) | T12 |
| Blinding: masks, sealing, scans of plots, logs, CSV and caches | hep-analysis, core | tested (E1) | T18; AUDIT T04: `.npy` caches read, scans report pass / fail / incomplete (an unreadable output is never a pass), strict publication mode with named exemptions. A pass cannot see transformed values |
| Analysis-change review (tuning after unblinding flagged) | hep-analysis | tested (E1) | T19 |
| Response objects, forward folding, double-counting checks | detector-response | tested (E1) | Path B, T07 |
| Resolution and efficiency studies (detector level) | detector-response | tested (E1), synthetic detector | J2 example (`examples/detector-resolution/`) |
| Unfolding | detector-response | guidance only | reference text; no unfolding is executed in v1 checks |
| Theory specs, conventions, analytic derivation status | hep-theory | tested (E1), tree-level QED only | Path C, T13, T14 |
| Numerical checks and convergence studies | hep-theory, hep-computing | tested (E1) | T15 |
| Competing models kept distinct; envelopes only by prescription | hep-theory | tested (E1) | T03 |
| Recasting with parametrized response | hep-theory, detector-response, hep-statistics | tested (E1), synthetic, one signal region | J7 example (`examples/recasting/`); interchange formats still proposed |
| Comparison gate (observable definition: process, species, phase space; units, level, every axis and its binning, conventions, corrections) | hep-statistics, contracts | tested (E1) | Path D, T08, T25; AUDIT T01: free-text definitions that differ are `unresolved` until a justified mapping is declared |
| Artifact payload consistency (axes, units, representation, finite numbers) | contracts | tested (E1) | AUDIT T02 |
| Project-level artifact dependencies (refs inside a project root, type/ID/version, sha256, upstream statuses) | contracts | tested (E1) | AUDIT T05 (`contracts/dependencies.py`); external refs stay `unresolved` |
| Binned Poisson likelihoods with nuisance parameters, toys | hep-statistics | tested (E1) | Path D, low and zero counts |
| Template fits with Barlow-Beeston (fit diagnostics; infeasible or unconverged fits reported failed) | hep-statistics, core | tested (E1) | AUDIT T03 |
| Berger-Boos upper limit (single-bin background nuisance) | hep-statistics, core | tested (E1) as an approximation: coverage validated by a seeded 36-point scan in `BB_VALIDATED_RANGE` only | AUDIT T07; outside that range the implementation's coverage is unvalidated, and no global coverage guarantee is claimed |
| Combinations (GLS) with declared correlations | hep-statistics | tested (E1), Gaussian only | T04, T05, T09 |
| Comparison with published records, no detector modules | hep-statistics | tested (E1) | T24 (synthetic published-style record) |
| Bayesian inference (samplers, priors, convergence) | hep-statistics | tested (E1) for convergence diagnostics on supplied chains, prior reweighting, and a demonstration Metropolis sampler on one counting model | T28; STATS S07 (`bayes_diagnostics.py`): R-hat, bulk/tail ESS and quantile MCSE on seeded synthetic chains; the demo sampler reproduces the flat-prior bound for n = 0, b = 0. No production sampler is shipped or tested |
| ON/OFF significance (Li & Ma) with toy-calibrated and exact conditional p-values | hep-statistics | tested (E1) | STATS S01 (`li_ma_significance.py`, `test_li_ma_significance.py`): the statistic is labeled asymptotic; low-count p-values come from seeded toys or the exact conditional binomial test |
| Global significance of 1D scans (look-elsewhere: brute-force toys, Gross-Vitells bound) | hep-statistics | tested (E1), one-dimensional scans only | STATS S05 (`look_elsewhere.py`): the bound agrees with brute-force toys for global p in [1e-3, 0.1] in the slow test (`HEP_SLOW_TESTS=1`, run in STATS-REINFORCEMENT-RUN); multi-dimensional scans are not implemented |
| Expected discovery sensitivity (Asimov, with a background uncertainty) and toy-calibrated goodness of fit | hep-statistics | tested (E1) | STATS S06 (`sensitivity_and_gof.py`): Asimov Z matches a numerical profile to 1e-6; toy p-values uniform for a correct model (KS, slow test) |
| Weighted unbinned fits and sWeights (covariance) | hep-statistics | guidance, with a tested (E1) toy walkthrough | STATS S08 (`test_weighted_unbinned_fit.py`): full sandwich pull width 1.020 over 300 toys; no fitting script is shipped |
| ML-assisted inference validity (NSBI, SBC, classifier observables) | hep-statistics | guidance only | STATS S09: reference text and static routing checks; no ML inference is executed |
| Post-fit nuisance diagnostics for pyhf (pulls, constraints, impacts, grouped breakdown, correlations) and interpolation comparison | hep-statistics | demonstrated on synthetic data (E1 + pyhf 0.7.6) | STATS S03, S04 (`pyhf_nuisance_diagnostics.py`): impacts match independent refits to 1e-3 relative; skipped, and then unverified, without pyhf |
| Likelihood publication (background-only workspace plus signal patchset) | hep-statistics | demonstrated on synthetic data (E1 + pyhf 0.7.6) | STATS S10 (`test_pyhf_publication.py`): the patched workspace reproduces best fit and CLs to 1e-6; skipped, and then unverified, without pyhf |
| HistFactory / pyhf workflows | hep-statistics | demonstrated on synthetic data (E1 + pyhf 0.7.6), asymptotic CLs | counting and two-channel shape workspaces (normsys, histosys, staterror, shapesys) match an independent likelihood in log-likelihood, best fit and limit (`tests/adapters/test_pyhf_counting.py`, `test_pyhf_shape.py`); end-to-end sample passes; toy-based CLs and other modifier types not tried |
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

## Profiles

| Profile | Kind | Status | Evidence |
|---|---|---|---|
| `experiment:ams-02` | experiment | tested (E1) for the public evidence ledger and modules; dataset records are metadata only, no values | 257 profile tests; AC08, AC09 |
| `experiment:synthetic-collider` | experiment (illustrative, invented detector) | tested (E1) | 9 profile tests; Path B; AC10 |
| `theory:qed-benchmark` | theory domain | tested (E1), tree level only | 16 profile tests; Path C |
| Private local profiles | any | tested (E1) with a fixture | T27 |

## Adapters

| Adapter | Status | Notes |
|---|---|---|
| `adapters/pyhf-combine` (pyhf JSON, Combine datacard template) | demonstrated-on-synthetic-data | adapter status is its least-tested tool: pyhf part demonstrated-on-synthetic-data (pyhf 0.7.6); Combine part demonstrated-on-synthetic-data (Combine 11.1.0 with ROOT 6.40.04 and 6.36.14: with `--strictBounds` the filled datacard gives observed 2.1518 and median expected 2.1562 against pyhf 2.153 in both; without it ROOT 6.40 rejects an out-of-range r, COMBINE-ROOT640) |
| `adapters/root-uproot` (ROOT, RDataFrame, RooFit, uproot/awkward assets) | demonstrated-on-synthetic-data | ROOT 6.40.04, uproot 5.7.6 and awkward 2.14.0 each run on synthetic fixtures; not run on real experiment files |
| `adapters/batch-schedulers` (Slurm job arrays, HTCondor clusters, campaign CLI) | documented | both tools `documented`: the backends are tested only against fake schedulers (`tests/adapters/batch_shims`); real-tool tests are gated by `HEP_SLURM_TEST` / `HEP_HTCONDOR_TEST` and skipped |
| Interchange formats for recasting and published data | proposed | named as optional in the J7 trace; no code |

## Hosts

| Host | Status | Notes |
|---|---|---|
| Claude Code (plugin, development marketplace) | tested (E1, CLI 2.1.287) | install, discovery, namespaced invocation, profile access, removal, legacy coexistence (G5); routing quality not yet established |
| Codex, Antigravity, other agents | not tested | see `skills/hep-computing/references/{codex,antigravity,generic-agent}.md` |

## E2 results (FULLTEST-E2, 2026-10-04)

| Capability or tool | E2 status | Evidence or reason |
|---|---|---|
| Core checks, profile suites, examples | tested (E2) | 13 of 14 aggregate checks pass (unittest fails only on the DDP row below); all ten examples rerun byte-identically on E2; committed output equal or numerically equal except `ams-flux-ratio` toy closure (stream divergence across platforms) |
| pyhf workflows | tested (E2 + pyhf 0.7.6) | adapter and statistics tests pass |
| uproot/awkward tools | tested (E2 + uproot 5.7.6, awkward 2.14.0) | `test_uproot_awkward_asset` passes |
| ROOT, PyROOT tools | tested (E2 + ROOT 6.38.04, Homebrew, PyROOT under Python 3.14) | ROOT C++ assets, PyROOT integration and scripts pass; older than the E1 version 6.40.04 |
| CMS Combine | unverified (E2) | no `combine`, no Docker |
| PyTorch assets | tested (E2 + PyTorch 2.14.1, torchvision 0.29.1, CPU) except DDP | the 2-process gloo DDP run hangs when the host name does not resolve (network-dependent) |
| Diagram source checks | tested (E2: Graphviz 16.1.0, PlantUML 1.2026.8, Mermaid CLI 12.0.0 with chrome-headless-shell 154) | Homebrew `mermaid-cli` needs a separate `chrome-headless-shell` install |
| Batch campaigns | protocol tested (E2) against fake schedulers; real Slurm/HTCondor unverified | no `sbatch`, no `condor_submit` |
| Relocation (AC24) | tested (E2) apart from the DDP row | copy at a path with spaces: same results as in place; the 2 legacy checks and 1 legacy-dependent unit test skip in the copy |
| Claude Code (plugin, isolated config) | tested (E2, CLI 2.1.288): install, discovery, removal; namespaced invocation unverified (isolated config not logged in) | invocation passed in the user configuration (VALIDATION INSTALL) |
| Live routing | not run (E2) | not approved |
