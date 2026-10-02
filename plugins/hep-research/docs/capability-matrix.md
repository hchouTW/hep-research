# Capability matrix (v0.1.0)

Status words: **tested** = exercised by a check that passed in the environment named below; **unverified** = code or
guidance exists but its tool was not installed, so it was not run; **proposed** = a starting point or design, not
executed; **not in v1** = outside scope, handled by the limited-support response. "Tested" means contract and
software consistency only, not physical validity, proof, statistical coverage, or authorization to unblind.

Environment E1 (all "tested" rows): Claude Code cloud container, Linux 6.18 x86_64, Python 3.11.15, NumPy 2.4.6,
SciPy 1.17.1, Matplotlib 3.11.2, SymPy 1.14.0, Claude Code CLI 2.1.287, 2026-10-02. Evidence: [VALIDATION.md](../VALIDATION.md).

## Capabilities

| Capability | Owner | Status | Evidence or reason |
|---|---|---|---|
| Measurement specs, correlated ratios, time-dependent exposure | hep-analysis | tested (E1) | Path A, T10, T11 |
| Systematic-variation classification (shape vs normalization) | hep-analysis | tested (E1) | T12 |
| Blinding: masks, sealing, scans of plots, logs, CSV and caches | hep-analysis, core | tested (E1) | T18 |
| Analysis-change review (tuning after unblinding flagged) | hep-analysis | tested (E1) | T19 |
| Response objects, forward folding, double-counting checks | detector-response | tested (E1) | Path B, T07 |
| Resolution and efficiency studies (detector level) | detector-response | tested (E1), synthetic detector | J2 example (`examples/detector-resolution/`) |
| Unfolding | detector-response | guidance only | reference text; no unfolding is executed in v1 checks |
| Theory specs, conventions, analytic derivation status | hep-theory | tested (E1), tree-level QED only | Path C, T13, T14 |
| Numerical checks and convergence studies | hep-theory, hep-computing | tested (E1) | T15 |
| Competing models kept distinct; envelopes only by prescription | hep-theory | tested (E1) | T03 |
| Recasting with parametrized response | hep-theory, detector-response, hep-statistics | tested (E1), synthetic, one signal region | J7 example (`examples/recasting/`); interchange formats still proposed |
| Comparison gate (observable, units, level, binning, conventions, corrections) | hep-statistics, contracts | tested (E1) | Path D, T08, T25 |
| Binned Poisson likelihoods with nuisance parameters, toys | hep-statistics | tested (E1) | Path D, low and zero counts |
| Combinations (GLS) with declared correlations | hep-statistics | tested (E1), Gaussian only | T04, T05, T09 |
| Comparison with published records, no detector modules | hep-statistics | tested (E1) | T24 (synthetic published-style record) |
| Bayesian inference (samplers, priors, convergence) | hep-statistics | contract checks only | T28; no sampler run |
| HistFactory / pyhf workflows | hep-statistics | demonstrated on synthetic data (E1 + pyhf 0.7.6), one counting channel | `tests/adapters/test_pyhf_counting.py`: CLs limit 2.153 agrees with an independent scipy profile likelihood (2.154); end-to-end sample passes; multi-channel and shape workspaces not tried |
| Local partition, resubmission, merge | hep-computing | tested (E1) | T21 |
| ROOT, PyROOT, uproot/awkward tools | hep-computing | unverified | tools not installed; tests skipped |
| Task files for coding agents (task authoring) | hep-computing | tested (E1) | bundle validator, lint_task tests |
| Split integrity, surrogate domain, ML artifact checks | physics-ml | tested (E1) | T16 |
| PyTorch training, inference, profiling assets | physics-ml | unverified | PyTorch not installed; tests skipped |
| Claims linked to results, status preserved in text | research-communication | tested (E1) | T20 |
| Literature and citation verification online | research-communication | unverified | needs network; offline it marks citations unverified |
| Diagrams and paper builds (Graphviz, Mermaid, PlantUML, tectonic) | research-communication | unverified | tools not installed; tests skipped |
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
| `adapters/pyhf-combine` (pyhf JSON, Combine datacard template) | proposed | adapter status is its least-tested tool: pyhf part demonstrated-on-synthetic-data (pyhf 0.7.6); Combine part proposed, Combine not installed |
| `adapters/root-uproot` (ROOT, RDataFrame, RooFit, uproot/awkward assets) | proposed | starting points only; ROOT and uproot not installed |
| Interchange formats for recasting and published data | proposed | named as optional in the J7 trace; no code |

## Hosts

| Host | Status | Notes |
|---|---|---|
| Claude Code (plugin, development marketplace) | tested (E1, CLI 2.1.287) | install, discovery, namespaced invocation, profile access, removal, legacy coexistence (G5); routing quality not yet established |
| Codex, Antigravity, other agents | not tested | see `skills/hep-computing/references/{codex,antigravity,generic-agent}.md` |
