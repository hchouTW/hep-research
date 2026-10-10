# VALIDATION — hep-research 0.3.0

What was checked, where, and the result. Software checks establish contract consistency only: not physical validity,
proof, statistical coverage, or authorization to unblind.

**Scope.** Validation of the code shipped in 0.3.0: `core/`, `contracts/`, the seven skills, the adapters
(`pyhf-combine`, `root-uproot`, `batch-schedulers`, `hepdata`, `unbinned-fit`), the examples, the public profiles
(`experiment:ams-02` public part: evidence ledger, analysis-spec audit, paper and CRDB helpers, domain modules, the
synthetic flux-ratio example; `experiment:eic`; `experiment:synthetic-collider`; `theory:qed-benchmark`;
`theory:qcd-r-ratio`), the host install tests (Claude Code and Codex; macOS and Linux), the routing tests, and the
relocation and packaging checks. Entries dated before 2026-10-07 ran on earlier versions (0.1.0 to 0.2.6); they are
condensed dated records stating the version they ran on and were not re-run for 0.3.0. Access-controlled AMS-02
content (Offline software usage, EOS production catalogue, ntuple producer, generated catalogs) left this plugin in
0.3.0 and is validated with the separate `ams02-research` plugin. The converter for the pre-plugin analysis-spec format
and the ledger-preservation and traceability checks were deleted in 0.3.0; their results are not recorded, and where an
earlier run's totals included them ("since removed") the totals are quoted as they were.

**Environments.** Each entry names one of these unless it says otherwise.

| Label | Environment |
|---|---|
| E1 | Linux cloud container (Claude Code cloud, Linux 6.18 x86_64), Python 3.11.15 in `.venv-hep` with numpy 2.4.6, scipy 1.17.1, matplotlib 3.11.2, sympy 1.14.0 (`requirements-core.txt`); Claude Code CLI 2.1.287. Optional tools added per entry |
| E2 | macOS workstation, macOS 26.5 (Darwin 25.5.0), arm64 Apple M3, Python 3.13.2 with numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2, sympy 1.14.0; Claude Code 2.1.288 to 2.1.289; Codex CLI 0.160.0 |
| E3 | Linux (EL9) shared cluster node (AlmaLinux 9, Linux 5.14.0 x86_64), plugin tree on a network file system, Python 3.11.13 in a venv on local disk; system ROOT 6.40.04 (C++17, g++ 11.5.0; PyROOT through the system Python 3.9), cmake 3.31.8, Graphviz 2.44.0, HTCondor 25.0.14; Claude Code 2.1.287, Codex CLI 0.160.0 |
| E4 | Linux cloud container (Claude Code cloud, Linux x86_64), Python 3.13.16 in `.venv-hep` with numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2, sympy 1.14.0, pyhf 0.7.6; no ROOT, PyTorch, Combine or Codex; Claude Code 2.1.292 |

Aggregate command: `python3 tools/run_all_checks.py --out <dir>` from the plugin root (`--help` runs nothing). Seeds
and tolerances of every example are in its `results.json`.

## Acceptance criteria (0.1.0 handover, 2026-10-02, E1)

Handover run of 0.1.0: 14 checks pass / 0 fail / 0 skip; 973 unit tests, 934 pass, 0 fail, 39 skip (PyTorch, PyROOT,
awkward/uproot, pyhf, Combine, Graphviz, Mermaid, PlantUML, tectonic not installed; skipped tests are unverified, not
passing); profile suites ams-02 258, synthetic-collider 9, qed-benchmark 16 pass. The optional tools were installed
afterwards (OPTIONAL-TOOLS). Criteria about the deleted traceability and conversion tools are not listed.

| AC | Result | Evidence (remaining items in italics) |
|---|---|---|
| AC02 | pass | Seven SKILL.md with uses, exclusions, owned artifacts, handoffs; host validator `--strict` passes; no profile adds a skill; native discovery lists the seven `hep-research:*` skills |
| AC03 | pass | `check_layering.py` 0 violations; profile paths rejected in skill/core/contract text |
| AC04 | pass | SKILL.md 50–63 lines, 5.2–7.0 KiB (≤ 8 KiB), descriptions ≤ 921 chars, always-on ≈ 2,005 tokens, registry 690 B, profile indexes ≤ 2,370 B. Loading traces from 48 headless runs: no theory or computing case read an experiment profile. *One trace with the host environment leaked in showed a computing case reading the synthetic-collider generator; recorded, not counted* |
| AC05 | pass | One definition and one implementation owner per method (`core/OWNERS.json`); each AMS method module opens with a `Method owner:` line, whose skill's text overrides general passages (`MethodOwnerTests`). *Generic passages inside AMS modules marked, not deleted* |
| AC06 | pass | Registry negatives: duplicate ID, incompatible version, missing resource, template violation, escaping path (incl. symlink), cycle, missing dependency, unbacked capability, bad namespace, registry mismatch (`RegistryTests`) |
| AC07 | pass | 0/1/many × 0/1/many configs, local profile, conflict diagnostics, overrides need provenance (`ProjectConfigTests`); composition diagnostics (`ComposeTests`); Path D binds two profiles; project config read by the installed plugin (J11 live) |
| AC08 | pass | 60 sources / 183 claims as `ams02:` IDs; index in sync; modules for species, subsystems, methods, periods, sources; 7 metadata-only dataset records. Live traces: J1 read the registry, `ams-02/index.md` and two modules; J2 the index and one subsystem module |
| AC09 | pass | `tools/check_ams_optional.py`: the plugin without the AMS profile passes registry, Paths B and C, core/contract/generic tests and the other profile suites; AMS cases read only `ams-02` files |
| AC10 | pass | `experiment:synthetic-collider` added with no change to skills, `core/`, `contracts/`, validators or algorithms; generator imports no theory code |
| AC11 | pass (benchmark scope) | `theory:qed-benchmark`: conventions, tree order, validity, `analytic-derivation` status (SymPy traces, 8 checks), PDG eqs. 51.2/51.3 read at page level (`qedbench:S01`, C01, C02), independent checks (Simpson, quad, trapezoid order 2.00), artifacts in `examples/qed-prediction/output/` |
| AC12 | pass | Path C reads zero experiment-profile files (audit hook), artifacts carry no detector/data/blinding fields, SymPy/NumPy only; numerical agreement recorded as corroboration, derivation status kept separate |
| AC13 | pass | 16 valid / 18 invalid artifact fixtures with explicit refusal codes |
| AC14 | pass | `contracts/comparison/gate.py` checks quantity, units, binning, phase space, frame, conventions, level, normalization kind, corrections, parameter point, validity range, uncertainty objects; transformations recorded; double counting blocked (GateTests, 17 tests); Path D rejects 9 mismatched variants naming field and resolution; a failing gate stops the dependent fit |
| AC15 | pass | `contracts/comparison/combination.py` + `combine_measurements.py`: independence never assumed, shared auxiliaries need a declared correlation, missing covariance stays missing, scale/model/truncation objects never enter a Gaussian matrix; GLS = BLUE = whitened least squares (`CombinationTests`, `GlsTests`, `ModelSetTests`). *Real multi-experiment inputs outside v1* |
| AC16 | pass | Path A `examples/ams-flux-ratio/run.py --toys 400 --seed 20261002` byte-identical, 6 contract-valid artifacts labeled synthetic (11 tests); Path B `collider-angular`: fiducial σ 745.65 ± 6.63 (stat) ± 14.9 (lumi) pb vs 745.81 pb expected, χ² 10.4/10 (8 tests); Path C `qed-prediction` (4 tests); Path D `theory-comparison`, `published-comparison`, `detector-resolution`, `recasting` byte-identical to the committed outputs |
| AC17 | pass | T10/T11, T12, T13–T15, T07, T16; low and zero counts in the Path D Poisson likelihood (`LowCountTests`) |
| AC18 | pass | Unit tests pass where tools exist (skips unverified); algorithm fixes only in `sci-fix:` commits with regressions |
| AC19 | pass | Failure statuses propagate (T20); bounded recovery in `local_partition.py` (T21) |
| AC20 | pass (noted misses) | Static: 48 cases pass `check_routing_static.py` (the case set on 2026-10-02; 62 from 2026-10-04, 118 since 2026-10-07). Live (Claude Code 2.1.287, claude-sonnet-5-5, plugin only, synthetic inputs): 41/48 route to the expected owner or ask (en 27/33, zh-Hant 14/15); 2 to a neighboring plugin skill (J5 → detector-response, J12 → hep-computing with the limited-support notice); 5 load no skill; no profile loaded by theory or computing cases. Round 2 with tuned `hep-theory`/`hep-statistics` descriptions: 43/48. *Later rounds below; short theory questions answered directly remain unreliable* |
| AC21 | pass | No values invented in dataset records; newer or inaccessible citations classed unverified (T17); private local profile usable through project config and absent from the tree (T27); `tools/check_packaging.py` finds no private paths, credentials, transcripts, rubrics, caches or project artifacts |
| AC22 | pass | Five scientific corrections as `sci-fix:` commits with regressions (YAML subset docs, unverified citations, dates, T12, theory routing); blinding (T18); signed weights pass unclipped, normalization by `sum(signed weights)` stated (T26); `observed` cannot combine with `synthetic` or `asimov`; Path D keeps Asimov and synthetic-observed apart |
| AC23 | pass | No adapter claims more than its least-tested tool: `pyhf-combine` and `root-uproot` are `demonstrated-on-synthetic-data` (pyhf 0.7.6; Combine 11.1.0 with ROOT 6.40.04 and 6.36.14; uproot 5.7.6, awkward 2.14.0; ROOT 6.40.04); the lowest-status rule is enforced by `AdapterDeclarationTests`. *Combine on one synthetic counting card; adapters not run on real experiment files* |
| AC24 | pass | Relocation check (12 pass, 2 skip since removed); native Claude Code 2.1.287 install, discovery, namespaced invocation, profile access from the installed path (with spaces), removal |
| AC26–AC28 | pass | Authoring and maintenance guides in `docs/`; `docs/capability-matrix.md` per capability, profile, adapter and host (tested / unverified / proposed / not-in-v1), rows matching `adapter.json`; this file and the limitations section below (the `DECISIONS.md` record named here then was removed with the other pre-release records in 0.3.0) |
| AC29 | pass | Layering directions, no-hard-coded-profile rule (names, IDs, namespaces, paths), steward check; one documented whitelist entry (`tools/layering_whitelist.json`) |
| AC30 | pass | J1–J12 traced (`docs/researcher-journeys.md`), each executed or answered on synthetic inputs; one live routing case per journey; J12 gives the limited-support notice |
| AC31 | pass | Vocabularies extensible by namespaced profile terms (T25, T26); published-style record compared without detector modules (T24) |

## Tests (Section 11)

Results at the 0.1.0 handover (E1); every listed test is in the 0.3.0 tree.

| Test | Result | Evidence |
|---|---|---|
| T01 | pass | `RegistryTests` (`tests/contracts/test_contracts.py`): duplicate profile ID, incompatible version, missing resource fail naming the offender; dependent resolution stops |
| T02 | pass | `RegistryTests`: dependency cycle, package-escaping path (including a symlink), template violation fail deterministically |
| T03 | pass | `ModelSetTests`: theory-only predictions keep their own specs; a shared spec is rejected; an envelope needs a hep-theory prescription and is non-Gaussian |
| T04 | pass | `GlsTests`: with a declared shared normalization, GLS equals the one-bin BLUE and a whitened least-squares reference to 1e-12 |
| T05 | pass | `CombinationTests`: a shared auxiliary without a declared correlation refuses combination ("comparison-only"); declared independence contradicting the overlap is reported |
| T06 | pass | `ComposeTests`: `ams02:C01` and `beta:C01` stay distinct; a correlation between them needs evidence or a scoped assumption |
| T07 | pass | Validator `response.double_counted`; gate rejects efficiency applied before folding with a response that includes it, and folding a detector-level prediction |
| T08 | pass | Wrong level, units, binning rejected; documented conversions accepted; the restricted prediction integrates to the theory profile's fiducial cross section (`test_published_comparison.py`) |
| T09 | pass | Missing covariance reported and kept missing; a scale envelope is marked not Gaussian and not quantified |
| T10 | pass | Path A He/p sigma equals an independent linear propagation with the shared trigger term to < 1e-15; treating it as independent overstates sigma by 1.00–1.17 |
| T11 | pass | Period average = sum of corrected counts / sum of per-period exposures; an equal live-time split mis-states low-rigidity exposure by up to 7.9% (synthetic) |
| T12 | pass | `tests/skills/hep_analysis/test_check_systematic_variations.py`: unchanged integral with changed shape classified as shape |
| T13 | pass | `profiles/theory/qed-benchmark/tests/test_convention_mismatch.py`: coupling normalization, angle definition, mass approximation (even at 1e-6) and a missing namespaced key reported as mismatches |
| T14 | pass | `test_derivation.py`: status `analytic-derivation` (not proof) stored apart from the numerical checks; `test_prediction.py` records tolerances |
| T15 | pass | `test_prediction.py::test_convergence_study`: trapezoid refinement 3…257 points, observed order within 0.05 of 2, error reduced > 1000×; Simpson and `scipy.integrate.quad` errors recorded |
| T16 | pass | Group leakage found by `check_split_integrity.py`; `check_surrogate_domain.py` flags outside and sparse queries; AUC-only validation is a contract error |
| T17 | pass | `profiles/experiments/ams-02/tests/test_docs_consistency.py` NewerLiteratureTests, DateWordingTests |
| T18 | pass | `tests/core/test_blinding.py` (15 tests, synthetic): masked JSON/log/CSV/npz and a masked plot pass; leaks detected: SR value in a log, a rounded value in a CSV, a raw npz cache, a data/MC ratio and a total including the SR, SR points in main or ratio panels and bar charts; CLI exit 0/1/2 |
| T19 | pass | `review_analysis_change.py`: control-sample calibration accepted with provenance; a change after looking at signal-region data flagged (not refused) |
| T20 | pass | Missing tool and solver failure give `failed` artifacts; consumers without `failed` fail validation; communication cannot upgrade statuses |
| T21 | pass | `examples/local-partition/run.py` (10 criteria): no retry without config, finished chunks not rerun, transient failure recovered, repeated identical failure stops with state kept, merged = single run (counts exact, floating sum within 1e-9), stray and foreign chunks excluded |
| T22 | pass | Install from a copy of tracked files only, relocation, removal, separate project state (AC24; E2-INSTALL-FULLTEST, MULTIHOST, FULLTEST-E3) |
| T23 | pass | `tests/tools/test_check_layering.py`: core importing a profile, a profile path or hard-coded AMS ID in core skill text, contracts importing skills; each reported with file and line |
| T24 | pass | `examples/published-comparison/run.py`: gate and GLS fit on a synthetic published-style record; load trace shows no `profiles/experiments/` file; GLS bias for multiplicative covariance reported |
| T25 | pass | `ConventionsGateTests`: unknown or namespaced convention keys on one side make the gate report not comparable unless a justified mapping is declared |
| T26 | pass | `NonColliderNormalizationTests`: `exposure`, `protons-on-target`, `target-exposure` specs validate with no luminosity field |
| T27 | pass | `PrivateLocalProfileT27`: a local profile in a project path with spaces validates, extends the vocabulary only when loaded; its namespace appears nowhere in the plugin |
| T28 | pass | Bayesian needs priors, sampler and convergence; frequentist needs construction and coverage; mislabeled results rejected (`ParadigmsT28`) |

## Known limitations and unresolved external conditions

| Item | Effect |
|---|---|
| tectonic 0.17.0 unusable in the cloud containers: the network policy blocks its TeX bundle host (relay.fullyjustified.net, proxy CONNECT 403) | the paper-skeleton compile test skips when tectonic is off `PATH`; the paper-build capability row is `unverified`. On E2 tectonic was present and the test ran |
| `vision_transfer.py` pretrained ResNet-18 weights download from download.pytorch.org, blocked by the network policy | the training test builds ResNet-18 with `weights=None`; accuracy on real images not assessed |
| hepdata.net not reachable from the cloud environment | `adapters/hepdata` tested on synthetic HEPData-layout tables only; `reproduce_published_likelihood.py` ran on a synthetic BkgOnly + patchset split only. No capability row reaches "reproduces a published result"; both unverified on real records (IMPROVEMENT-PLAN T6) |
| PyTorch verified on CPU only | GPU, NCCL and GPU mixed precision not tried; the CPU-only wheel index is blocked in the cloud container |
| pyhf demonstrated on two synthetic workspaces, asymptotic only | toy-based CLs, lumi/shapefactor modifiers and non-default interpolation codes not tried |
| CMS Combine checked on one synthetic counting card (E1 only); needs `HEP_COMBINE_WRAPPER`, and with ROOT 6.40 `--strictBounds` | the observed-limit search throws out of range under ROOT 6.40.04 without `--strictBounds` (OPTIONAL-TOOLS) |
| Slurm and HTCondor exercised through fake schedulers only (`tests/adapters/batch_shims/`); on E3 one `condor_submit -dry-run` parsed, nothing queued | `adapters/batch-schedulers` stays `documented`; a few formats are not stated in the Slurm 26.05 / HTCondor 25.13 documentation and stay to be confirmed on a real run |
| Live routing measured on claude-sonnet-5-5 (113/118, E4, 0.2.6), claude-haiku-4-5 (37/118) and Codex `gpt-6.1-sol` (61/62 on the 0.2.0 cases, macOS); Codex live routing not run on Linux | misses in IMPROVEMENT-PLAN T3; quick questions answered without a skill remain accepted misses; not re-measured on 0.3.0 before the release check |
| J2 and J7 run on synthetic inputs only | J2 uses an invented Gaussian detector; J7 has one signal region, an efficiency map without its own uncertainty, a toy model; recasting frameworks stay `proposed` |
| Combination is Gaussian (GLS) only | non-Gaussian components are refused, not combined; Peelle's-puzzle bias for multiplicative covariance documented in T24 |
| Truncation uncertainty (theory) not quantified | recorded as a non-Gaussian object, never folded into a covariance |
| AMS module generic passages kept as marked snapshots | the owner skill's text applies where they differ (AC05) |
| AMS-02 behavioral suite ran on profile 1.x under 0.2.x (AMS-FULLTEST, AMS-FOLLOWUPS) | last scores main 91.4% with 1 blocking failure, forward 87.9%; the suite is not part of the plugin and was not rerun on the 2.0.0 public-only profile |
| Blinding scan cannot see transformed values | a `pass` means the sealed numbers were not found at the precisions tested; rescaled, shifted or fitted numbers are not detected (AUDIT-RUN T04) |
| Berger-Boos implementation validated in a finite range | coverage checked by a seeded scan at 36 true points (`BB_VALIDATED_RANGE`); outside it, run `neyman-coverage` at the values that matter. The profile-limit toys (`_toy_p1`) truncate the auxiliary observation at zero |
| EIC profile is documentation only | no EIC performance number, dataset or software execution; beam parameters unread and unquoted |
| `theory:qcd-r-ratio` is massless, non-singlet QCD through alpha_s^4 | EFT global fits and cosmic-ray propagation fits stay outside v1 (limited-support notice) |

## OPTIONAL-TOOLS (2026-10-02, E1, version 0.1.0): PYHF-RUN to COMBINE-ROOT640

Eight consecutive runs (PYHF-RUN, UPROOT-RUN, PYTORCH-RUN, ROOT-RUN, DIAGRAM-RUN, TORCHVISION-RUN, COMBINE-RUN,
COMBINE-ROOT640), each adding one tool to E1 and re-running the aggregate: pyhf 0.7.6; uproot 5.7.6, awkward 2.14.0,
PyYAML 6.0.3; PyTorch 2.14.1 from PyPI (CUDA 13.0 build, no GPU: CPU, 4 threads); ROOT 6.40.04 from conda-forge
(Python 3.11.16, gcc 16.2.0, C++20) in a project-local micromamba environment, cmake 3.28.3, reached through
`HEP_ROOT_PYTHON`; Graphviz 14.1.2, PlantUML 1.2026.8, tectonic 0.17.0 (conda-forge) and Mermaid CLI 12.0.0 (npm, Node
22.22.0) driven by Playwright Chromium 141 through a `mmdc` wrapper (`--no-sandbox`); torchvision 0.29.1 (`--no-deps`,
torch unchanged); CMS Combine 11.1.0 from conda-forge built against ROOT 6.36.14 (Python 3.13) and against ROOT
6.40.04 (Python 3.14), each in its own environment, reached through `HEP_COMBINE_WRAPPER` (runs its arguments under
`env -i` with that environment's `bin` first on PATH). Aggregate run/pass/skip after each step: 975/940/35 (pyhf;
979/944/35 with the shape workspace), 982/955/27, 982/966/16, 987/978/9, 987/982/5, 988/984/4, 988/985/3 (Combine,
both builds); 0 fail; all 14 checks pass; profile suites unchanged.

| Item | Result | Evidence |
|---|---|---|
| End-to-end sample (`examples/end-to-end-sample/`) | pass, 4 of 4 | `tests/examples/test_end_to_end_sample.py` |
| pyhf counting workspace (`pyhf-counting.json`, SYNTHETIC s=5, b=20, n=20, 10% background normsys): asymptotic CLs 95% upper limit on mu | observed 2.1529; expected band 1.097 / 1.503 / 2.153 / 3.129 / 4.419 (−2σ…+2σ) | `tests/adapters/test_pyhf_counting.py`; the independent implementation (`histfactory_reference.py`, q̃_mu, background-only Asimov) gives 2.1529. A first version used exponential normsys interpolation (2.1541); pyhf's default is code 4, corrected |
| Two-channel shape workspace (`pyhf-shape-synthetic.json`, SYNTHETIC: 3-bin SR, 2-bin CR; normsys, histosys, staterror, shapesys) | pass | `test_pyhf_shape.py` (4 tests): log-likelihood equal to the reference within 1e-9 at 200 random nuisance points; best-fit NLL within 1e-4; observed CLs limit 2.4320 vs 2.4319 (reference) |
| uproot/awkward: synthetic NanoAOD generator, awkward reference values | pass, 8 tests | `tests/skills/hep_computing/test_synthetic_nanoaod.py`, `tests/skills/detector_response/test_reference_values.py` |
| `uproot_awkward_analysis.py` on a SYNTHETIC file (4000 events, 0–4 muons, 15% negative weights) | pass | `test_uproot_awkward_asset.py` (3 tests): TH1D contents and sum(w²) equal an independent numpy computation; selected-event count matches; a missing branch is refused |
| physics-ml tests needing PyTorch (allocation measurement, dataset building, asset smoke tests) | pass, 13 tests | `tests/skills/physics_ml/test_physics_ml_skill.py`, `test_assets_smoke.py` |
| `ddp_train_skeleton.py` with `torchrun --nproc_per_node=2` (gloo) | pass | `test_ddp_skeleton_two_gloo_processes`; `torchrun` found next to the interpreter |
| Clean degradation without PyTorch | pass under the system Python 3.11 (no torch) | `CleanDegradationWithoutTorchTests` (2 tests) |
| PyROOT scripts and assets (inspection, histogram comparison, systematic variations, RooFit workspace summary, RDataFrame cutflow, RooFit peak fit recovers mean 91 within 0.5) | pass, 7 tests | `tests/skills/hep_computing/test_root_integration.py` |
| C++ assets `rdf_cutflow_analysis.cpp`, `fit_histogram.cpp`, `rdf_histogram_branch.cpp` with `root-config`; CMake `analysis` target; `plot_branch.C` in batch | pass, 5 tests | `tests/adapters/test_root_cpp_assets.py`; the C++ cutflow (3044, 2718, 2223 of 5000 synthetic events) equals the PyROOT asset's |
| Graphviz `dot` accepts a valid graph and rejects an invalid one; Mermaid CLI rejects bad flowchart syntax; PlantUML rejects a one-line class body; every shipped diagram source passes `check_diagram_sources.py` with the real tools | pass | `tests/skills/research_communication/test_diagrams.py` |
| Bundled paper skeleton compiles with tectonic | unverified | with tectonic on PATH the test fails before compiling: the TeX bundle download is rejected by the network policy; tectonic left off PATH, the test skips with "tectonic not on PATH (it also downloads a TeX bundle on first use)" |
| `vision_transfer.py --help`; one epoch on a SYNTHETIC ImageFolder (random 32x32 images, 2 classes, 8 train, 4 val) with a frozen backbone, checkpoint with the right classes and a 2x512 head | pass | `test_assets_smoke.py`; ResNet-18 built with `weights=None`; pretrained weights unverified |
| Combine datacard template with the SYNTHETIC counting model (s=5, b=20, n=20, 10% lnN), `text2workspace.py` then `combine -M AsymptoticLimits --rMax 10`, ROOT 6.36.14 build | pass: observed 2.1565, expected 1.1118 / 1.5116 / 2.1562 / 3.1275 / 4.3733 (2.5% to 97.5%); pyhf 2.153 (tolerance 2%) | `tests/adapters/test_combine_datacard_template.py`, `test_limit_matches_pyhf`; `adapters/pyhf-combine` became `demonstrated-on-synthetic-data` |
| Same card, Combine built against ROOT 6.40.04 | fails without `--strictBounds`: no limit printed, log `Caught exception Value 26.4507 is outside the default range [0, 14.5482] of the variable "r"!`; `--run expected` / `--run blind` give median 2.1562; `--rMax 10 --strictBounds` gives observed 2.1518, median 2.1562 in both builds | manual runs; `test_limit_matches_pyhf` now passes `--strictBounds` and passes with both wrappers |

Cause (`combine -v 3`): after the expected band, the observed-limit search starts at r = 26.4507 while the POI range
is [0, 14.5482]. ROOT 6.36.14 visits the same point and continues because RooRealVar then clipped out-of-range values
silently; ROOT 6.40.04 throws (its message names `RooRealVar::enableSilentClipping()` as the old behavior) and Combine
prints no observed limit. Why Combine picks that starting point was not traced. The two observed values (2.1565,
2.1518) differ by 0.2%, inside Combine's default `--rRelAcc` of 2%; the `hep-statistics` statistical-tools reference
gives the workaround.

## REFACTOR-RUN (2026-10-03, E1, plugin-wide refactor)

E1 plus pyhf, uproot, awkward, PyYAML; ROOT 6.40.04 recreated. Aggregate: 14 pass / 0 fail / 0 skip; 1031 unit
tests, 1008 pass, 0 fail, 23 skip; `check_relocation.py` passes. Renames keep every reference valid (registry,
layering, stanza, skill-resource and adapter-declaration checks); every example rerun with its documented seed
reproduces the committed `output/` byte for byte; renamed ROOT C++ and PyROOT assets pass (12 ROOT tests); new
regression tests for the 20 fixes and the `sci-fix` each failed on the previous code (`tests/contracts/test_robustness.py`,
`tests/core/test_blinding.py`, `tests/skills/**`). PyTorch, diagram, Combine and tectonic tests skipped (unverified for
this change).

## AUDIT-RUN (2026-10-03, E1, validation-gap audit T01–T08)

E1 core stack, no optional tools. Baseline 1031 unit tests OK with 57 skips; a reproduction script reproduced all
eight findings before and none after the fixes. Final: 13 checks pass / 0 fail / 1 skip (since removed); 1094 unit
tests, 1035 pass, 0 fail, 59 skip (57 optional tools, 2 slow); profile suites 258, 9, 16 pass.

| Task | Result | Evidence |
|---|---|---|
| T01 comparison gate | pass; each regression failed before the fix | `GateDefinitionAuditT01` (process, species, phase space, second axis, structured cuts, named mappings, multi-dimensional transformations); `theory-comparison` and `recasting` outputs regenerated (new `status`, `kind`, `definition_mappings_applied` fields, one negative variant) |
| T02 artifact consistency | pass | `ArtifactConsistencyAuditT02` (edges, unit, traceable conversion, payload per representation, NaN and ±Infinity, metadata-only record, multi-dimensional `axes`) |
| T03 template-fit status | pass; feasible fits byte-identical | `FitStatusAuditT03`; `test_solver_failure_recorded` passes with SciPy |
| T04 blinding scans | pass | `ScanCompletenessAuditT04` (`.npy` leak and clean scan, unsupported-only is `incomplete`, strict mode, exemptions, manifest, CLI exit codes) |
| T05 dependency validation | pass | `tests/contracts/test_dependencies.py` (valid chain, missing, hash mismatch, substitution, type/ID/version mismatch, undeclared failed upstream, external unresolved, out-of-root paths incl. symlink, never opened) |
| T06 split grouping | pass | `SplitGroupingCompletenessAuditT06` |
| T07 Berger-Boos | pass (label, auxiliary model, MC errors); coverage in range only | `BergerBoosApproximationAuditT07`; with `HEP_SLOW_TESTS=1` a 36-point coverage scan (s ∈ {0, 2, 5}, b ∈ {1, 3, 8}, σ_b ∈ {0.5, 2}, cl ∈ {0.90, 0.95}, β = 0.01, 600 × 300 toys, seed 7): coverage ≥ cl − 3σ_MC at every point (lowest 0.8967 ± 0.0124 at cl 0.90, s = 5, b = 8, σ_b = 0.5); the plug-in profile limit fell to 0.8717 ± 0.0137 at one point. One seeded scan, not a characterization |
| T08 citations without bibliography | pass | `TestCitationsWithoutBibliographyAuditT08` |

## STATS-REINFORCEMENT-RUN (2026-10-03, E1, hep-statistics reinforcement S01–S12)

E1 core stack plus pyhf 0.7.6. Baseline 1094 unit tests, 59 skips; a reproduction script reproduced all eleven
findings before and none after. Final: 14 pass / 0 fail / 0 skip; 1165 unit tests, 1115 pass, 0 fail, 50 skip (46
optional tools, 4 slow); profile suites 258, 9, 16 pass; `check_relocation.py` (12 pass, 2 skip),
`check_routing_static.py` (56 cases), `measure_entrypoints.py --no-cli`, `check_layering.py`, `check_packaging.py`,
`check_ams_optional.py` pass; slow tests (`HEP_SLOW_TESTS=1`) 34 pass.

| Task | Result | Evidence |
|---|---|---|
| S01 Li & Ma | pass (failed 8/10 before) | `test_li_ma_significance.py`: at (4, 2, 0.25) asymptotic p 6.646e-3, toys 9.03e-3 ± 0.21e-3, exact conditional 0.01696 |
| S02 core/stats guide | pass | `test_core_stats_guide.py`: every subcommand and option documented, exit-code table matches |
| S03 interpolation | pass (pyhf) | `test_nuisance_interpolation.py`: CLs limit 2.1529 (code4) vs 2.1541 (code1); asymmetric 1.3/0.95: 2.1145 vs 2.0525 |
| S04 nuisance diagnostics | pass (pyhf) | `test_pyhf_nuisance_diagnostics.py`: impacts equal independent refits within 1e-3 rel / 1e-4 abs |
| S05 look-elsewhere | pass | Gross-Vitells vs 20,000 brute toys: (0.1, 0.110), (0.03, 0.0337), (0.01, 0.0111), (0.003, 0.00289), (0.001, 0.00127) |
| S06 sensitivity and GoF | pass | Z_A(5, 20) = 1.07572; with σ_b = 2, 0.97554 equal to a numerical profile within 1e-6; KS D = 0.040, p = 0.708 over 300 datasets |
| S07 Bayesian diagnostics | pass | `test_bayes_diagnostics.py`: offset chains R-hat 1.13; AR(1) bulk ESS 1082 vs 1053 expected; demo bound 2.957 ± 0.060 vs 2.9957 |
| S08 sWeights | pass | `test_weighted_unbinned_fit.py` (300 toys): pull width 1.020 (full sandwich), 1.013 (sum w² sandwich), 2.799 (naive Hessian); a mass-dependent background lifetime gives mean τ 0.575 instead of 1 |
| S09, S12 routing | pass (static) | `tests/routing/test_ml_inference_routing.py`; 8 new cases, 3 in Traditional Chinese; no live run |
| S10 likelihood publication | pass (pyhf) | `test_pyhf_publication.py`: patched background-only workspace reproduces best fit and CLs within 1e-6 (mu_hat 0.7949, CLs 0.4924) |
| S11 contract 1.1.0 | pass (failed 4/7 before) | `test_statistical_result_v11.py`; 25 example artifacts regenerated, only the contract version string changed |

## BATCH-RUN (2026-10-03, E1, Slurm and HTCondor batch execution B01–B13)

E1 core stack; no Slurm or HTCondor installed (fake schedulers only, user decision). Final: 13 checks pass, 0 fail,
1 skip (since removed); 1240 unit tests, 1162 pass, 0 fail, 78 skip; profile suites 258, 9, 16 pass;
`check_relocation.py` 12 pass, 2 skip; T21 output byte-identical. The fake-scheduler suite (`tests/core/test_partition*.py`,
`tests/adapters/test_batch_*.py`, 74 tests, 2 skipped) runs in 21 s.

**Shim-only:** every Slurm and HTCondor result comes from the fake schedulers in `tests/adapters/batch_shims/` (with
fault injection and a call log), which implement the formats the backends parse. They show internal consistency, not
that the adapter works with real Slurm or HTCondor; both stay `documented`. The tool facts in
`skills/hep-computing/references/batch-scheduling.md` were checked on 2026-10-03 against the Slurm 26.05 and HTCondor
25.13 documentation; a few formats are not stated there.

| Task | Result | Evidence |
|---|---|---|
| B01–B03 core/partition, remote protocol, states | pass | `tests/core/test_partition*.py` (9 + 11 + 13): local executor through the batch protocol equals a single run; a double run is one duplicate and the merge equals the single run; a foreign-manifest output is quarantined; `.tmp-` and truncated files never collected; every normalized state has its decision; the same exit code on two hosts stops the chunk; no `max_attempts` means zero resubmissions |
| B04 Slurm | pass (shim) | `test_batch_slurm.py` (9 + 1 skipped real-tool): 12 native states map; golden array script for 10 chunks with throttle 3; dry run makes no call; missing partition and time refuse with exit 2 |
| B05 HTCondor | pass (shim) | `test_batch_htcondor.py` (9 + 1 skipped): eviction then completion is one done chunk with two attempts; a held job blocks the merge and is never released; transfer mode remaps outputs (golden submit file) |
| B06 watch; B07 config | pass | `test_batch_watch.py` (7): a stuck chunk stops after exactly `max_polls`; no limits exits 2 with no poll. `test_batch_config.py` (7): each missing key, unknown key and non-positive resource refuses |
| B09 provenance; B10 reference | pass | `test_batch_provenance.py`: the artifact validates for both backends; a stopped chunk gives `failed`. `test_batch_reference.py`: every workflow command in the reference runs, in order, on the fake scheduler |
| B11 example | pass | `examples/batch-partition/run.py`: 10 criteria per backend; merged result equals the local single run exactly; byte-identical rerun |
| B12 privacy; B13 integration | pass | `test_batch_privacy.py` (4): a sealed value in job stdout is found; a planted account fails `check_packaging.py`. `adapter.json` `documented` with no tested versions; matrix rows match; six routing cases (two in Traditional Chinese) |

## CERN-HTCONDOR-RUN (2026-10-10, E3, work order T03: first real HTCondor runs of the batch adapter)

E3 (lxplus, AlmaLinux 9, HTCondor 24.12.16 client, schedd bigbird13; adapter driven by `/usr/bin/python3.11`,
workers `/usr/bin/python3` 3.9.25; campaigns on AFS). Submission approved per phase by the user; 31 synthetic jobs in
all, every one espresso or `MaxRuntime 60`. Records: the user's task folder (`T03-htcondor/runs/h2-*`, `h4-*`), not
this repository.

**Found before any job ran.** The fake-scheduler suite failed on this host (10 of 10 HTCondor shim tests): the
worker-side `runner.py` used `datetime.UTC` (Python 3.11+) and `python3` on the job's PATH was 3.8/3.9, so every job
died before the worker started. Fixed (`datetime.timezone.utc`); `tests/core/test_r5_runner.py` now runs the runner
under `/usr/bin/python3` when it is older than 3.11.

**Plain submit files (H2, 21 jobs, 5 refused at submission).** Default flavour espresso (`MaxRuntime 1200`,
`JobFlavour` undefined); a run-time overrun is removed by `SYSTEM_PERIODIC_REMOVE` with `ExitCode 0` and no stdout
back; a missing `output` directory is accepted at submission and held after the run (`Code 12 Subcode 2`, `ExitCode
0`); `getenv = false` keeps Kerberos and AFS tokens; `request_cpus 2` gives 6000 MB; `OpSysAndVer AlmaLinux9` also
matches RHEL 9.8 hosts; `CentOS7` is refused at submission; an unknown OS value idles forever; sandbox files return
to the submit cwd; the first four `condor_submit` calls of the session failed on the credmon timeout and later ones
succeeded; two jobs were evicted (code 1008) before executing and rescheduled. The `-terse` line, the event-log
separator and the termination, held and aborted lines match the parser (tool-facts rows now say "observed").

**Adapter (H3, test-first).** `htcondor.site_attributes`, `resources.time_limit` for HTCondor, `htcondor.schedd`
(recorded per submission, `-name` on every later call), the two refusal texts → `not-submitted`, `-match N` on
`condor_history`, cluster-level events (proc −1) skipped. 76 batch-adapter tests pass; the old golden file is
byte-identical; new golden `htcondor-chunks-site-attributes.sub`.

**Real campaigns (H4, 12 jobs).** Two synthetic 5-chunk toy campaigns (2,000 items per chunk, seeds 42 and 43),
`shared-filesystem` then `transfer` mode, pilot first: both merges equal the local single run in every field
(`n`, `sum`, `sum_cos`, a seeded weighted sum, `seed_sum`); both reports validate with status `synthetic,
unvalidated`. `RealHTCondorTests` (two chunks, `HEP_HTCONDOR_TEST=1`, `HEP_HTCONDOR_CONFIG` naming a user-reviewed
configuration) passed in 61 s. `adapter.json`: HTCondor `demonstrated-on-synthetic-data`, `tested_versions
["24.12.16"]`; the adapter stays `documented` (Slurm has not run). Found on the pool and recorded in
`skills/hep-computing/references/batch-site-cern-htcondor.md`: the 035/036 cluster events (fixed), history records
appearing minutes after completion (fresh `condor_history` queries exceeded 120 s and 300 s; `-match N` added; a
re-read of the event log before the fallback is recommended, not implemented), `watch` not stopping on a partially
submitted campaign while holding the lock, `freeze` refusing a changed configuration with an unchanged file set
(`bundle.request_differs`).

**Gate on this host.** `run_all_checks.py` 18 pass / 2 fail: `tests.examples.test_batch_partition` differs in the
last two digits of `sum_cos` (numpy 1.23.5 here; the same on unmodified `main`, the committed file is from another
host) and `ams_optional` (no matplotlib and sympy for `/usr/bin/python3.11` on this host); `tests.tools.test_subprocess_timeouts`
failed once on a new test's unbounded call and was fixed in the same branch. Both failures were environmental:
after 0.6.4 and the float-rounding comparison of the example output, `run_all_checks.py` on `main` (`915617d`) in a
venv on local disk (Python 3.11.13 with `requirements-core.txt`: numpy 2.4.6, scipy 1.17.1, sympy 1.14.0, matplotlib
3.11.2) gave **20 pass / 0 fail / 0 skip**: 1,840 unit tests, 1,733 pass, 0 fail, 107 skipped (PyTorch, PyROOT,
pyhf, uproot/awkward and the real-scheduler gates); profile suites ams-02 238, eic 43, synthetic-collider 9,
qed-benchmark 18, qcd-r-ratio 21 pass.

## E2-INSTALL-FULLTEST (2026-10-03 to 2026-10-04, E2, version 0.1.0): INSTALL, FULLTEST-E2 and follow-ups

**INSTALL.** First install into a day-to-day configuration: the user's own `~/.claude`, user scope, from the GitHub
marketplace `hchouTW/hep-research` (plugin loaded from the plugin cache at 0.1.0); headless model claude-opus-5-5.
Gate: 12 pass, **1 fail** (unittest), 1 skip (since removed); 1235 unit tests, 1159 pass, 5 fail, 1 error, 70 skip;
`claude plugin validate --strict` passes. The user installed despite the unit failures, all platform causes on E2: the
batch golden tests (macOS `/var/folders` is a symlink to `/private/var/folders`, so the `<CAMPAIGN>` substitution left
a `/private` prefix); `test_batch_privacy` (the scan copied the untracked `.venv-hep`, whose NumPy license e-mail
addresses trip the scanner); `test_root_cpp_assets` (`python3` 3.13 on `PATH` imports Homebrew ROOT 6.38.04 built for
Python 3.14.4 and `dlopen` fails instead of a clean ImportError); `test_theory_comparison` (`response_matches_path_b`
used exact `np.array_equal`, false on arm64 / numpy 2.5.3). Checks: `claude plugin marketplace add
hchouTW/hep-research --scope user`, then `claude plugin install` of `hep-research` from the `hep-research-dev`
marketplace; `claude plugin list` shows 0.1.0 enabled, 7 skills, ~2,142 always-on tokens; the settings and plugin
registry files differ from their backups only by the added entries; headless init lists the seven `hep-research:*`
skills among 59 with no short-name clash; `/hep-research:hep-theory` succeeds in 5 turns ($0.22) and reads the
registry, the qed-benchmark index and `conventions.json` under the cache path. Live routing not approved. Rollback:
`claude plugin uninstall` of the plugin, then `claude plugin marketplace remove hep-research-dev`.

**E2-FOLLOWUPS.** Aggregate 13 pass, 0 fail, 1 skip (since removed); 1241 run, 1171 pass, 0 fail, 70 skip.
`batch_harness.py` resolves the temporary project dir; the privacy scan copy is built from git-listed files;
`test_root_cpp_assets` picks an interpreter that can import ROOT (all 5 pass with Homebrew ROOT 6.38.04 via
`python3.14`; the class skips cleanly when none can); `response_matches_path_b` within 1e-12 relative (largest E2
difference 1.1e-16; E1 committed floats matched E2 to rel 1e-9 / abs 1e-12; output regenerated on E2); qed-benchmark
`conventions.json` gains an explicit not-applicable `scales` entry.

**FULLTEST-E2.** Venv outside the plugin tree with pyhf 0.7.6, uproot 5.7.6, awkward 2.14.0, torch 2.14.1,
torchvision 0.29.1 (CPU); Homebrew ROOT 6.38.04, Graphviz 16.1.0, PlantUML 1.2026.8, Mermaid CLI 12.0.0, tectonic
0.17.0, cmake 4.3.2; Claude Code 2.1.288. Absent: CMS Combine, Docker, Slurm, HTCondor. Aggregate 13 pass, **1 fail**
(unittest), 0 skip: 1241 run, 1230 pass, 1 fail, 1 error, 9 skip (3 missing tool, 4 slow, 2 meaningful only without
PyTorch). The fail was Mermaid (Homebrew `mermaid-cli` ships without its headless Chrome); after installing
`chrome-headless-shell` 154.0.8037.57 all 22 diagram tests pass (1231 pass, 0 fail, 1 error).

| Step | Result | Evidence |
|---|---|---|
| F04 examples | pass; 1 cross-platform difference | all ten rerun byte-identically on E2; batch-partition, local-partition, recasting, theory-comparison byte-identical to the committed output; collider-angular, published-comparison, qed-prediction numerically equal; detector-resolution `results.json` identical (figure differs); **ams-flux-ratio toy-closure summary differs** (observed counts and all pass criteria agree) |
| F05 adapters | pass except DDP; Combine unverified | pyhf, uproot/awkward, ROOT 6.38.04 tested; fake Slurm/HTCondor pass; `test_ddp_skeleton_two_gloo_processes` **error**: torchrun rendezvous hangs because the host name does not resolve on this network |
| F06 relocation | pass apart from the DDP error | path with spaces, outside the repository; a first run failed packaging because a leftover `.venv-hep` was copied with the tree |
| F07 isolated host | pass (install, discovery, removal) | isolated `CLAUDE_CONFIG_DIR`, marketplace from a `git archive` copy at a path with spaces; uninstall leaves no plugins; `~/.claude` checksums identical before and after |

**FULLTEST-E2-FOLLOWUPS.** Aggregate **14 pass, 0 fail, 0 skip**; 1242 run, 1233 pass, 0 fail, 9 skip. DDP: `torchrun
--standalone --local-addr=127.0.0.1` (with the host name made unresolvable, the default launch and `--standalone`
alone both hang; with `--local-addr=127.0.0.1` all 9 smoke tests pass). ams-flux-ratio: new
`test_matches_committed_output` compares deterministic values to rel 1e-9 / abs 1e-12 and the toy-closure summary
within 3 Monte Carlo standard errors; the E1 output passes on E2. Relocation copy of the 885 git-listed files with a
planted e-mail address in an ignored venv: packaging passes, unit 1242 run, 0 fail, 10 skip. Mermaid browser note added
to `references/mermaid-patterns.md`. Isolated-config invocation of `/hep-research:hep-theory` after login: exit 0, 5
turns, $0.18, claude-opus-5-5, reads the registry, the qed-benchmark index and `conventions.json` inside the copy.

## FULLTEST-E2-ROUTING (2026-10-04, E2, version 0.1.0)

Live routing over all 62 cases of `tests/routing/cases.json` (42 en, 20 zh-Hant). Claude Code 2.1.288,
claude-sonnet-5-5, isolated `CLAUDE_CONFIG_DIR` holding only this plugin from a `git archive` copy; `run_headless.py
routing`, 6 jobs, 4 turns, synthetic inputs per case; scored by `score_routing.py`; `~/.claude` checksums identical
before and after; $5.85. **56/62** (en 37/42, zh-Hant 19/20). Misses: no skill, answered directly: `co-direct-1`
(ROOT memory leak), `co-neighbor-1` (tree-level QED check), `st-sensitivity-1` (Asimov significance); no skill, asked
for inputs: `st-impacts-1` (the case had no input files); another plugin skill: `j05` fold-and-fit → detector-response
(it owns folding), `out-of-v1-2` SMEFT global fit → hep-theory with the limited-support notice. Loading violations 0.
Against E1 round 2 on the 48 shared cases: 44/48 (was 43/48); of the 14 newer cases 12 pass. One run per case.

Follow-ups: the three quick questions answered without a skill were accepted as known misses (user decision).
`st-impacts-1` got inputs in `tests/routing/inputs.py` (synthetic two-bin pyhf workspace and a `fit_result.json`
computed from it with pyhf 0.7.6). Both changed cases were rerun live four times each (Claude Code 2.1.288,
claude-sonnet-5-5, $0.72): `st-impacts-1` 2 × hep-statistics, 2 × no skill (every run read the inputs);
`out-of-v1-2` 2 × hep-theory, 2 × hep-statistics, every run with the limited-support notice; no loading violations.
The scorer then gained `also_accept` (user decision): `tests/routing/make_cases.py` allows an optional list per case
(`out-of-v1-2` → `["hep-statistics"]`); `check_routing_static.py` allows it only on limited-support cases, never
repeating the expected skill, and only for skills whose SKILL.md carries the limited-support notice (planted
violations rejected). Rescored with unchanged traces: **57/62** (en 37/42, zh-Hant 20/20); changed-case repeats **6/8**.

## MULTIHOST (2026-10-04, E2, version 0.2.0): Claude Code and Codex on macOS

Claude Code 2.1.288, Codex CLI 0.160.0; Linux cells deferred. Every host test used an isolated `CLAUDE_CONFIG_DIR` or
`CODEX_HOME`, logged in by the user and deleted afterwards; `~/.claude` and `~/.codex` unchanged (checksums).

| Step | Result | Evidence |
|---|---|---|
| M01 Codex spike | done | Codex installs from `.agents/plugins/marketplace.json` + `.codex-plugin/plugin.json`, copies the plugin into its cache, namespaces skills `hep-research:*`, gives the model each SKILL.md path, does not set Claude Code's plugin-root variable, passes the full description, runs plugin scripts in the read-only sandbox |
| M02 host-neutral paths | pass | 389 occurrences in 112 files rewritten to `<plugin root>/...` (the folder two levels above the SKILL.md); `check_host_neutral.py`: no host variable outside its allow-list, every `<plugin root>/` path exists (planted violations caught) |
| M03 manifests, 0.2.0 | pass | Codex manifest and marketplace beside the Claude ones, both 0.2.0; `check_host_manifests.py` agrees (a planted mismatch fails); 25 example artifacts regenerated with the version string |
| M04 host-aware checks | pass | `codex-plugin-load` installs from the repository marketplace into a throwaway `CODEX_HOME` (no login) and finds 0.2.0; check-runs record host versions; with both CLIs hidden from `PATH` both host checks skip with a reason |
| M05 Claude Code × macOS; Codex × macOS | pass | the model resolves `<plugin root>` from the skill's base directory and reads `registry.json` and `conventions.json` inside the install ($0.19); same reads inside the Codex 0.2.0 cache; removal clean on both |
| M08 Codex routing | **61/62** | 62 cases, `gpt-6.1-sol`, plugin only (`HOME` = scratch), read-only sandbox, `run_headless_codex.py` + `score_routing.py`: en 41/42, zh-Hant 20/20, 0 loading violations; only `j05` missed (→ hep-statistics). 4.94M input tokens (4.18M cached), 65k output. Every case passing for Claude on E2 passes here, plus the four quick questions Claude answered without a skill |

M06 final aggregate at 0.2.0 with both hosts present: **17 pass, 0 fail, 0 skip**; 1242 run, 1233 pass, 9 skip.
Relocation passes (`codex-plugin-load` skips in the copy). Detection note: Codex has no Skill tool, so a skill counts
as invoked when its `SKILL.md` is read; 54 runs read one SKILL.md and 7 read two (`j02`, `an-direct-2` checked by
hand). GitHub source: `codex plugin marketplace add hchouTW/hep-research` in a throwaway `CODEX_HOME` found the
marketplace file and `codex plugin add` installed 0.2.0 with the seven skills; removal clean; no login or model call.

## EIC-PROFILE (2026-10-04, E2, version 0.2.0): experiment:eic 0.1.0, with EIC-FOLLOWUPS and EIC-TODO

E2, Python 3.13.2 (the profile checks need the standard library only); Claude Code 2.1.289 and Codex CLI 0.160.0
installed, so the host checks ran.

| Check | Result | Evidence |
|---|---|---|
| Registry; layering | pass, 4 profiles | registry 904 B ≤ 2048; eic index 2127 B ≤ 4096; `check_layering.py` plus a word-boundary grep for EIC/ePIC in skills, core, contracts, tools, adapters: none (+2 regex tests) |
| eic ledger (`core/evidence/ledger.py --strict`) | pass | 4 sources, 8 claims, then 5 sources, 9 claims after follow-ups (S05 via OSTI; C09 third_party_context); index in sync |
| Profile suite; example | 42 tests pass; `examples/eic-profile-routing/` 7 tests, byte-identical rerun | `profiles/experiments/eic/tests/`, `tests/examples/test_eic_profile_routing.py` |
| DIS kinematics | pass, 12 tests | `tests/skills/hep_theory/test_dis_kinematics.py`: closed forms vs four-vector arithmetic to 1e-7, PDG eq. 18.1 Jacobian, refusals; PDG review read 2026-10-04 |
| `check_ams_optional.py`; static routing | pass; 66 cases | registry still valid with eic present; hep-analysis and detector-response descriptions 1016 and 993 chars, detector-response SKILL.md 8151 B (budgets 1024, 8192) |
| Live routing, 4 EIC cases | baseline 1/4 (claude-fable-5-1, $1.87) and 1/4 (claude-sonnet-5-5, $0.29): the three EIC-named cases answered from memory without a skill. After the description fix: r2 3/4, r3 2/4 at the harness cap of 4; named-experiment direct cases load the owner 4/4 (0/6 before); `eic-underspec-1` asks at cap 8, runs out of turns at cap 4; total $1.07 | `~/.claude` snapshots bracket every run. The other 62 cases were not rerun then (measured later in IMPROVEMENT-PLAN T3) |
| Aggregate | 18 pass / 0 fail / 0 skip; final 1274 unit tests, 1231 pass, 0 fail, 43 skip | check-run records |

Documentation only: no EIC performance number, dataset or software execution; the DIS identities are checked
numerically against the stated definitions, not against any experiment; a 4-case routing sample is indicative, not a
measured rate.

## AMS-FULLTEST (2026-10-05, E2, version 0.2.0): behavioral test of experiment:ams-02 through the plugin

Plugin tree unchanged by the run; `experiment:ams-02` at its 1.x public content (domain modules, ledger, datasets).
Claude Code 2.1.289 in an isolated config; answerer claude-sonnet-5-5, graders claude-opus-5-5 (primary and
adjudication) and claude-fable-5-1 (spread). Model grading, not human review; the suite is not part of the plugin.

| Item | Result |
|---|---|
| Deterministic layer | 18 pass / 0 fail / 0 skip; 1274 unit tests, 1265 pass, 9 skip; ams-02 profile suite 258/258 |
| Behavioral suite | 66 reproducible tests (T01–T66) plus 12 blind forward prompts in an `experiment:ams-02` project (25 prompts do not name AMS); 166 runs (2 samples each, plus 10 Bash-variant runs), $21.46 |
| Routing and loading | lenient routing 82/132 (main), 16/24 (forward); 42 of 74 publication-record runs loaded no skill; 57 runs loaded a skill but read no profile file |
| Rubric score | main **944/1308 = 72.2%, 9 blocking failures: fail** (bar ≥ 90%, no blocking); forward 144/240 = 60.0%, 2 blocking: fail; Bash variant 84/100, 0 blocking |
| Score by answer path | skill + profile file read 9.07/10 (55 answers); skill, no profile file 7.21 (57); no skill 4.52 (48); Fable regrade of 10 answers within ±1 point of the Opus grades |

Reading: answers are strong when the profile is reached (detector-response 92.0%) and weak from model memory; all 11
blocking failures are in such runs, all publication-record questions (research-communication family, 53.0%).

## AMS-FOLLOWUPS (2026-10-05, E2, version 0.2.0): two rounds of follow-ups (AMS-FOLLOWUPS, AMS-FOLLOWUPS-2)

Claude Code 2.1.289; answerer claude-sonnet-5-5, graders claude-opus-5-5 and claude-fable-5-1 (model grading).
Public-profile and skill changes only; the frozen suite of AMS-FULLTEST was rerun after each round.

| Item | Round 1 | Round 2 |
|---|---|---|
| research-communication description | "load it first even for a quick question" on publications, paper existence, paper contents; 962/1024 chars | adds currency and claim-support questions; 1017/1024 chars |
| Skill workflow | context-resolution stanza: step 1 applies before any answer and reads a bound profile; all SKILL.md ≤ 8192 B | all seven SKILL.md begin with the project-config read (detector-response 8185 B); hep-statistics runs the matching `core/stats/` script when a shell exists |
| AMS-02 profile | working-rules pointer in 15 modules (test); index line naming the ledger as the source for publication questions; ledger 60 sources, 184 claims (C184 added: PRL 114, 171103 break fit) | working-rules invariant 11: no remembered AMS number, method, threshold or result, hedged or not (test); antimatter module names Λ_TRD and Λ_CC (C22) and the lepton estimators (C24); 7/7 dataset records carry `extension["ams02:method_module"]` (test) |
| hep-statistics unit test | classical zero-count limit −ln(1 − CL) − b; fails against a background-dropping copy | — |
| Live routing (4 turns) | 69 cases: 64/69; 58/62 on the cases shared with FULLTEST-E2-ROUTING; new AMS publication-record cases 3/3 | 71 cases: 66/71; shared subsets unchanged; new cases 2/2 |
| Suite rerun | main **90.2%, 2 blocking: fail** (was 72.2%, 9); forward **91.7%, 0: pass** (was 60.0%, 2); Bash variant 82.0% | main **91.4%, 1 blocking (T56 s1): fail**; forward **87.9%, 0: fail**; Bash variant 78.0% |
| Answer path | research-communication no-skill runs 4/74 (was 42/74); skill + profile answers 116, mean 9.32/10 (was 55, 9.07) | no-skill runs 2/74; project config read 105/156 (was 92); target tests T25 4.0 → 9.5, T27 6.5 → 9.5, T38 5.5 → 7.5, T14 6.0 → 7.5, T40 5.5 → 6.0 |
| Spread; cost | Fable regrade identical on 10 answers; $36.98 | 0 on 6, −1 on 2, −2 on 2 (T36); $35.85 |

Reading: after round 1 the two blocking failures were remembered additions in answers that did read the profile (T40 s2
number, T27 s1 method). After round 2 the answers that read the profile handle the targeted points (T25, T27); the
remaining blocking failure and every answer below 6/10 among the target tests read no AMS-02 file, mostly short
research-communication runs that skipped the project-config read despite step 1; the forward set slipped below 90%
without a blocking call. A reminder hook not relying on the answerer reading step 1 was later evaluated and not
shipped (IMPROVEMENT-PLAN T3).

## FULLTEST-E3 (2026-10-05, E3, version 0.2.1), with FULLTEST-E3-FOLLOWUPS

E3 venv with numpy 2.4.6, scipy 1.17.1, matplotlib 3.11.2, sympy 1.14.0, pyhf 0.7.6, uproot 5.7.6, awkward 2.14.0.
Absent: PyTorch (added in the follow-ups), Mermaid CLI, PlantUML, tectonic, CMS Combine, Slurm. Live routing not run.
Aggregate: 18 checks, 17 pass, **1 fail** (unittest), 0 skip; 1281 unit tests, 1253 pass, 1 fail, 27 skip (17
PyTorch, 3 diagram/TeX tools, 1 Combine, 1 Slurm: missing tool; 1 real HTCondor gated, 4 slow); profile suites 265,
43, 9, 16 pass. The fail: `test_theory_comparison.test_reproduces_committed_output`,
`q_without_luminosity_constraint_at_mu_1.15` = 2.50e-9 on E3 against 0.0 committed (abs 1e-12); the value was 5.82e-11
in the E1 output before regeneration on E2.

| Step | Result | Evidence |
|---|---|---|
| L04 examples (eleven) | 10/11 rerun pass; 1 cache-dependent output; 1 tolerance miss | batch-partition, detector-resolution, eic-profile-routing, recasting byte-identical to the committed output; collider-angular, local-partition, published-comparison numerically equal; **qed-prediction** not byte-identical: `profile_files_read` lists `scripts/derive.py` and `predict.py` only on a cold bytecode cache; **theory-comparison** misses rel 1e-9 / abs 1e-12 on two minimizer outputs; ams-flux-ratio toy-closure differs as on E2 (accepted) |
| L05 adapters | pass; Combine unverified | 84 run, 81 pass, 3 skip; ROOT 6.40.04 C++ assets (5) and PyROOT integration (7), pyhf, uproot/awkward tested; fake Slurm/HTCondor pass |
| L06 relocation | same result on the network file system and local disk | 14 pass, 1 fail (theory-comparison), 3 skip (two since removed; Codex load needs the repository); network file system 24% slower; no file-system-specific failure |
| L07 isolated host | pass (install, discovery, removal); invocation unverified ("Not logged in") | seven skills, plugin path inside a `git archive` copy at a path with spaces; removal leaves no plugin or settings entry; `~/.claude` checksums identical |
| L08 HTCondor dry run | parses after one path edit; nothing queued | the shipped `batch-config.example.json` had no `htcondor` block; the dry-run `job.sub` read its items from `submissions/s001/items.txt`, which a dry run does not write; pointed at `dry-run/s001/items.txt` it parses into 2 procs (`JobUniverse=5`, `RequestCpus=1`, `RequestMemory=1000`) |

Follow-ups (same E3; each has a test that failed on E3 before the change). theory-comparison: fit outputs compared at
the fitter's precision (q without the luminosity constraint at abs 1e-7, interval ends and pull at rel 1e-7; other
floats still rel 1e-9 / abs 1e-12; no output changed). Files-read record: the audit hook skips `.py`/`.pyc` opens and
takes modules imported from `profiles/` from `sys.modules`; cold and warm runs against a fresh `PYTHONPYCACHEPREFIX`
agree and equal the committed output, which changed in that list only. HTCondor: `batch-config.example.json` gains an
`htcondor` section (tests fill the example for both backends) and the submit file uses `queue … from items.txt`
relative; live on HTCondor 25.0.14 the unmodified `dry-run/s001/job.sub` parses with `condor_submit -dry-run` (2
procs), nothing queued. `run_all_checks.py` gets an argparse command line (`-h`/`--help` runs nothing;
`tests/tools/test_run_all_checks.py`). PyTorch 2.14.1 and torchvision 0.29.1 (CPU wheels) added:
`tests/skills/physics_ml` 130 run, 128 pass, 2 skip, DDP 2-process gloo run passes. Live routing and logged-in
invocation **not run** (the isolated config could not be logged in). Aggregate after the first four follow-ups: 18
pass, 0 fail, 0 skip; 1287 run, 1260 pass, 0 fail, 27 skip. Batch-schedulers stays `documented`. Not rerun on E1 or E2.

## IMPROVEMENT-PLAN (2026-10-07, E4, version 0.2.6)

One commit per task. Baseline: 18 checks, 16 pass, 1 fail, 1 skip (Codex); 1289 unit tests, 1 fail
(`test_files_read_match_the_committed_output`, see T2), 53 skip. Task T5 (moving the AMS-02 generated catalogs out of
the plugin) concerned content no longer in this plugin and is not recorded.

| Task | Result | Evidence |
|---|---|---|
| T1 ownership | `tools/check_ownership.py`: 5 topics, one owner each, pass; 9 tests incl. seeded contradictions (a "forward-folding algorithms" Owns line, a README row, a description, a matrix owner, an owner that does not claim) each fail; `check_routing_static.py` ok, 71 cases; live `j05` under T3 | `tests/tools/test_check_ownership.py` |
| T2 environment | baseline reproduced: a fresh in-tree bytecode cache adds `scripts/__pycache__/derive.cpython-313.pyc.<id>` to `profile_files_read`; the cold/warm test with the cache inside `profiles/` fails on the old hooks and passes after; the record equals the committed one; `test_comparison_still_fails_for_a_real_change` passes (q +1e-3 fails, q +1e-9 passes) | `tests/examples/test_qed_prediction.py`, `test_published_comparison.py`, `test_theory_comparison.py` |
| T3 routing, static | descriptions 924–990 characters (all ≤ 1,000); `check_routing_static.py` ok on 118 cases (77 en, 41 zh-Hant; 15–19 per skill); always-on estimate 2,205 tokens (2,299 before, CLI 2.1.292). Reminder-hook prototype fires on 41/118 cases, not on `co-direct-1`; not shipped | `tests/routing/make_cases.py`, `docs/routing-contract.md` |
| T3 routing, live | 118 cases, isolated `CLAUDE_CONFIG_DIR` with only this plugin from a `git archive`, Claude Code 2.1.292, `run_headless.py routing --jobs 5 --max-turns 4`, `score_routing.py`; Codex not run (user decision). **claude-sonnet-5-5: 113/118** (en 73/77, zh-Hant 40/41), $9.84; misses `ml-neighbor-1` (physics-ml instead of hep-statistics), `st-sensitivity-1` and `ml-t3-7` (no skill), `underspec-1` and `eic-underspec-1` (no clarifying question); `j05`, `co-direct-1`, `co-neighbor-1` pass. **claude-haiku-4-5: 37/118** (en 24/77, zh-Hant 13/41), $2.94: 72 runs loaded no skill (47 ended at the 4-turn cap), 8 another plugin skill, 1 a non-plugin skill. Loading violations 0 on both | routing traces and scores |
| T4 theory | registry ok (5 profiles); layering ok; ledger `qcdr` 2 sources, 4 claims. `theory:qcd-r-ratio` suite 19 tests: d_n(0) = c_n, mu-independence through each order in exact arithmetic (fails with the wrong sign of beta_0), closed forms equal SymPy, nf = 5 c_2 = 1.4097, c_3 = −12.767, c_4 = −79.98; R(15 GeV) = 3.8618 at alpha_s^4, envelope [3.8611, 3.8630], alpha_s(15 GeV) = 0.16276; 7 mismatch tests; 13 script tests | `profiles/theory/qcd-r-ratio/`, `tests/skills/hep_theory/test_theory_depth_scripts.py` |
| T6.1 published likelihood | `reproduce_published_likelihood.py` (pyhf-combine 0.7.0) on a SYNTHETIC BkgOnly + patchset split of `pyhf-shape-synthetic.json`: reproduces best fit and CLs to 1e-4, fails for CLs shifted by 0.01, exit 3 when a value is not provided, refuses a missing tolerance, a digest mismatch, an unknown patch (4 tests). **Real record not run: unverified** | `tests/adapters/test_pyhf_published_reproduction.py` |
| T6.2 HEPData adapter | 6 tests on synthetic HEPData-layout tables: valid record, identifiers kept, percent and asymmetric errors, "not given" bins noted; correlation table × `stat` errors equals the covariance table to 1e-9; entries placed by label; refusals: correlation without `--covariance-of`, unknown label, published without `--evidence-id`, gap in the bins, wrong entry count, asymmetric or non-PSD matrix. No real record read (hepdata.net not reachable) | `tests/adapters/test_hepdata_record.py` |
| T6.3 unbinned fit | 300 seeded toys (150 signal + 800 background, seed 3): 0 failed fits; Hessian 68% coverage n_sig 0.677, n_bkg 0.660, mu 0.680, sigma 0.717, slope 0.703; profile coverage of n_sig 0.687 (binomial SE 0.027); pull means within 0.11, widths 0.96–1.07. A first version stopped L-BFGS-B at the start values on large samples (Hessian and profile errors disagreed by 50%); fixed by scaled variables and a repeat pass, with a large-sample test (profile half-width vs Hessian error to 5%). 5 tests | `tests/adapters/test_unbinned_fit.py` |
| T6.4 unfolding | `examples/unfolding-coverage/` (4,000 toys, seed 20261007): inversion relative bias < 1e-12, per-bin coverage 0.675–0.69 (SE 0.0074); Tikhonov 1e-4/1e-3/1e-2/1e-1: largest bias 0.01/0.09/0.58/1.69 sigma, minimum coverage 0.675/0.674/0.599/0.238; TSVD 6 of 10: bias up to 17.5 sigma, coverage 0; all 5 pre-declared criteria pass and fail for an inversion scaled by 1.02; 3 tests | `tests/examples/test_unfolding_coverage.py` |
| T7 inventory | `reference_inventory.py --check` in `run_all_checks.py`; 2 tests; 169 references, 1.38 MB, none uncited; 3 pairs above the overlap thresholds; 5 proposals, none executed | `docs/reference-inventory.md`, `docs/reference-consolidation.md` |
| Final runs | A first aggregate had 3 failures from this work, all fixed (a profile-template placement; the inventory counting CHANGELOG and VALIDATION mentions as citations; `check_host_neutral.py` in the relocated copy flagging a path to a repository folder absent from a copy); `eic-profile-routing` output gained one file read, `profiles/theory/qcd-r-ratio/profile.json` (regenerated). Then `run_all_checks.py`: 19 pass, 0 fail, 2 skip (one since removed; Codex not installed); 1,336 unit tests, 0 fail, 53 skip; profile suites ams-02 335, eic 43, synthetic-collider 9, qed-benchmark 16, qcd-r-ratio 19 pass. `check_relocation.py` (copy at a path with spaces, outside the repository): **18 pass, 0 fail, 3 skip** (two since removed; Codex not installed) | `tools/run_all_checks.py`, `tools/check_relocation.py` |

## 0.3.0 release check (2026-10-07, E1)

Environment E1 (Linux cloud container, Python 3.13.16, Claude Code 2.1.292; no Codex CLI). Run on the 0.3.0 tree after
the split, the decoupling and the rewrites of this release; all software checks only.

| Check | Result |
|---|---|
| `tools/run_all_checks.py` (with `claude plugin validate --strict`) | 18 pass, 0 fail, 1 skip (Codex CLI not installed): 1,326 unit tests (81 environment skips), profile suites ams-02 238 / eic 43 / synthetic-collider 9 / qed-benchmark 16 / qcd-r-ratio 19, layering, stanza consistency, registry, AMS-optional, routing (static), ownership, reference inventory, packaging scan with the extended deny-list, host-neutral, host manifests (both marketplaces list the same plugins), entry-point budgets (largest SKILL.md 8,185 bytes) |
| `tools/check_relocation.py` | pass: copy at a path with spaces outside the repository, no symlinks, no file names the source path, the same 18 checks pass from an unrelated working directory |
| `tools/check_ams_optional.py` | pass: with `experiment:ams-02` removed, registry, Paths B and C, core, contracts, hep-statistics and hep-computing suites and the two small profiles pass |
| Companion profile with `contracts/project.py <project> --local <ams02-research>/profile` | `experiment:ams-02` 2.0.0 and `experiment:ams-02-private` 1.0.0 both resolve, `depends_on` satisfied, 0 findings |
| gitleaks 8.30.1 on the plugin tree and on a fresh-history commit of the public repository tree | no leaks (`.gitleaks.toml` allowlists DOIs, article keys and checksum tables) |
| Decoupling pattern and restricted-site patterns (`tools/check_packaging.py`) | zero hits |

Not run in E1: the Codex load check, live routing, and the companion-skill loading cases on the installed plugins (to be
run on a workstation with both hosts after the repositories are created).

## HARDENING-P0-P1 (2026-10-07 to 2026-10-08, E2, version 0.3.0 + unreleased): statistical fixes, tests, CI

Work order "Harden hep-research 0.3.0", items T01–T18 (P0 merged as PR #2, P1 on `feat/hardening-p1`). E2 as above;
the dev tools (hypothesis 6.168.5, ruff 0.16.10, mypy 2.4.0, pre-commit 4.6.2, pip-tools 7.6.2) in a separate venv.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 4` | 17 pass, 0 fail, 2 skip (host CLI checks off); 1,469 unit tests in 105 modules, 43 skipped (optional tools, slow tier); 3 min 35 s |
| Slow tier (`HEP_SLOW_TESTS=1`) | Feldman-Cousins Tables IV and VI (220 entries) and PDG Table 40.4 within 0.01; 10,000 contract mutations raise nothing; validator time budgets met |
| Published references | Feldman and Cousins (1998) Tables IV and VI; PDG 2024 Tables 40.3 and 40.4; SciPy 1.18 for Garwood ends, tails and limits; Li and Ma eq. 17 checked against an independent transcription (the paper prints no table) |
| Fuzzing | 30,000 seeded mutations over artifacts, gate plans and ledgers, and 15,000 over the covariance and response fixtures: no exception |
| ruff and mypy on `core/`, `contracts/` | pass |
| Examples | rerun with E2: outputs unchanged by this work; two differences appear at b373418 as well (ams-02 profile version 1.0.0 in the AMS artifacts; round-off in an exactly-zero unfolding bias) |
| CI (`tests.yml`) | Python 3.11–3.13 with `requirements-ci.lock`; results attached to the pull request |

Unverified here: the optional CI jobs (pyhf, uproot, PyTorch, ROOT container) run only on GitHub; a host where
Chromium cannot start (the Mermaid hang is covered by a fake renderer, not a real one); the SKILL.md trims planned in
`docs/maintenance.md` (not applied).

## HARDENING-P2 (2026-10-08, E2, version 0.3.0 + unreleased): features T19–T27

Same work order, items T19–T27, on `feat/hardening-p2`. E2 as above; hepdata_lib 0.21.0, hepdata-validator 0.3.6,
coffea 2026.9.0 and pyarrow 25.0.1 in the dev venv; pyhf 0.7.6 read from the E2 venv for one comparison (nothing
installed there).

`run_all_checks.py --no-cli --jobs 4`: 17 pass, 0 fail, 2 skip (host CLI checks off); 1,543 unit tests in 117 modules,
79 skipped (optional tools, slow tier). Harness tests: `python3 -m unittest discover -s evals/routing/tests` (10 tests).

| Item | Result | Evidence |
|---|---|---|
| T19 routing harness | harness tested with a fake CLI; live cost probe 5/5 strict (claude-sonnet-5-5, CLI 2.1.293, setting-sources isolation), $0.455 for 6 prompt turns; full 150-case run 2026-10-08: 143/150 strict, $11.67, 0 loading violations (misses: 2 quick questions, 1 proposal request, 2 handoff second turns without a skill, 2 underspecified cases); baseline `evals/routing/baselines/claude-2.1.293-claude-sonnet-5-5.json` | `evals/routing/` (outside the plugin), `results/probe-20261008-sonnet.json`; 32 new cases (zh-Hans, ja, de, adversarial, quick, multi-turn) pass `check_routing_static.py` (150 cases) |
| T20 recasting templates | documented: none of MadGraph5_aMC@NLO, Rivet, Delphes, SModelS, MadAnalysis 5 installed | `tests/adapters/test_recasting_templates.py` (structure only) |
| T21 HEPData export | pass: hepdata-validator accepts the plain and the hepdata_lib engine; the importer reads the export back | `tests/adapters/test_hepdata_export.py` |
| T22 statistics extensions | pass, eight items, each with a closure or coverage test | `tests/core/test_stats_template_fit.py` (`ZeroMcBinTests`), `test_stats_asymptotic_bands.py`, `test_stats_interpolation.py`, `test_stats_mc_statistics.py`, `test_stats_toy_cls.py`, `test_stats_two_poi.py`, `test_stats_saturated_gof.py`, `tests/skills/hep_statistics/test_combine_asymmetric.py` |
| T23 environments | manifest script tested; LCG-view and Apptainer templates documented (no CVMFS or Apptainer on E2) | `tests/skills/hep_computing/test_environment_manifest.py` |
| T24 columnar | pass on the synthetic NanoAOD-like file: the coffea processor reproduces the generator's answers for any chunking; the Parquet conversion writes every entry once | `tests/adapters/test_columnar_assets.py` |
| T25 handoffs | pass: rows added, routing static check and budgets green | `tools/check_routing_static.py`, `tools/measure_entrypoints.py` |
| T26 systematics table | pass: status required and carried into the caption; output compiles with pdflatex | `tests/skills/hep_analysis/test_systematics_table_tex.py` |
| T27 documentation drift | fixed: version headers, removed files, measured sizes and dated routing counts | `docs/` diffs in the T27 commit |

T22 numbers: the zero-MC Barlow-Beeston bin equals a brute-force maximum for five configurations, and 300 sparse-MC
toys give no failed fit (the naive fit is infeasible in about one in five); the Asimov bands match the quantiles of
300–400 background-only toys within 12–14%; the interpolation codes match pyhf 0.7.6 to 1e-9; with 20% MC
statistics per bin the Barlow-Beeston-lite limit covers at 0.95 ± 0.025 against below 0.92 without it; toy CLs
reproduces the exact Poisson CLs limit (40-seed mean 5.412 ± 0.046 against 5.395); two-POI regions cover within 0.035
(68%) and 0.015 (95%) over 2,000 toys; the asymmetric combination stays within 0.05 errors of the exact pooled
lifetime likelihood; toy GoF p-values are uniform at 1–4 events per bin, where the chi-square reference is not.

Also found and fixed: a `submission.tar.gz` written by hepdata_lib had been committed with T21 (removed; the export now
writes none, and the packaging scan refuses archives); the T03 audit's "infeasible" fixture now applies to the naive
comparison fit only, and failure propagation is tested with a non-converging minimizer.

Unverified here: any Codex routing run; the recasting and environment templates on a
real installation; the optional CI jobs for hepdata and columnar (GitHub only).

## 0.4.0 release check (2026-10-08, E2)

Version 0.3.0 → 0.4.0 in both plugin manifests, `pyproject.toml`, the README and the capability matrix; the CHANGELOG
"Unreleased" section became 0.4.0. Examples rerun with the E2 venv: only the embedded version changed (the
unfolding-coverage example, which embeds no version, showed its known 1e-14 round-off and was left as committed).
`run_all_checks.py --jobs 4` with the E2 venv: 19 pass, 0 fail, 0 skip, including `claude plugin validate` and the
Codex load check.

## SYMPY (2026-10-08, E2 + three conda SymPy environments, version 0.4.0 + unreleased): choosing a SymPy interpreter

Three conda-forge environments on the E2 Mac, each with SymPy only (no NumPy, SciPy or Matplotlib): `sympy-py311`
(Python 3.11.17), `sympy-py312` (3.12.15), `sympy-py313` (3.13.16), all SymPy 1.14.0, mpmath 1.4.1, gmpy2 2.3.2.
Nothing was installed into them for this run (`conda list --export` identical before and after).

| Check, run in each environment | 3.11.17 | 3.12.15 | 3.13.16 |
|---|---|---|---|
| `profiles/theory/qcd-r-ratio/scripts/derive.py`: exit, checks, output vs committed `derivations/derivation.json` | 0, 6/6, identical | 0, 6/6, identical | 0, 6/6, identical |
| `profiles/theory/qed-benchmark/scripts/derive.py`: exit, checks, output vs committed `derivations/derivation.json` | 0, 8/8, identical | 0, 8/8, identical | 0, 8/8, identical |
| qcd-r-ratio profile tests (21) | pass, 9 skipped (SciPy) | pass, 9 skipped | pass, 9 skipped |
| qed-benchmark profile tests (18) | pass, 6 skipped (NumPy) | pass, 6 skipped | pass, 6 skipped |
| `find_python.py` with `HEP_RESEARCH_PYTHON` set to the environment | found, SymPy 1.14.0 | found | found |

Before this change the same profile tests errored in `sympy-py312` (qcd-r-ratio: 2 errors on SciPy; qed-benchmark:
1 error on NumPy), and `derive.py` without SymPy stopped with a `ModuleNotFoundError` traceback. Now it prints a
JSON `failed` status and exits 2 (tested by hiding SymPy in a subprocess, and with `/usr/bin/python3` 3.9.6, which
has no SymPy). `find_python.py` on E2 picks the calling interpreter (miniconda base 3.13.2, SymPy 1.14.0). It rejects
`/usr/bin/python3` as `Python 3.9.6 < 3.11` and falls through to the next candidate.

`run_all_checks.py --jobs 4` with the E2 venv: 19 pass, 0 fail, 0 skip (unit tests: 1,555 run, 0 failures, 47
skipped for optional tools); `check_relocation.py`: pass.

Finding, not changed: the `theory-spec` extension has no field for tool versions. The skill text records the
interpreter and the SymPy version in a `computational-run` (`tools`, `environment`) instead.

CI on the PR (Linux): the `checks` jobs on Python 3.11, 3.12 and 3.13 and every optional job pass.

Unverified here: Windows interpreters for `find_python.py` (its tests use POSIX shell stand-ins and skip there); a
live agent session using the new step.

## 0.5.0 release check (2026-10-08, E2)

Version 0.4.0 → 0.5.0 in both plugin manifests, `pyproject.toml`, the README and the capability matrix; the CHANGELOG
"Unreleased" section became 0.5.0 (AGENTIC-R5 WP0′, contracts 2.1.0, project config 1.1.0, batch hardening). Examples
rerun with the E2 venv: only the embedded plugin version changed (unfolding-coverage left as committed, as in 0.4.0).
`run_all_checks.py --jobs 6` with the E2 venv: 20 pass, 0 fail, 0 skip (1668 unit tests, 47 skipped for optional
packages), including `claude plugin validate`, the Codex load check and the new `instruction_text` check. The code
release manifest `release-manifests/0.5.0.json` (`tools/release_manifest.py generate`) is recorded in the release commit;
the tag `hep-research--v0.5.0` points at the commit on main whose tree it describes. Software checks establish
consistency only; no host configuration is qualified for private or blinded data by this release.

## COMPANION-INDEPENDENCE (2026-10-08, system Python 3.13.2, version 0.5.0 + unreleased)

Source tests: `tests/tools/test_companion_independence.py` (parsed host dependencies in both plugin manifests and both
repository catalogs; no edge exists, so the tests are protective; CI files fetch no companion; stanza and docs text) and
`tests/contracts/test_companion_validation_cli.py` (registry and project CLIs with synthetic public profiles: no
project, pin mismatch, core/contracts incompatibility, missing dependency, unreadable inputs, dangling options, the same
folder twice, two folders with one ID, an unrelated project finding kept as itself). Two CLI bugs were reproduced first
and fixed (dangling `--local`/`--registry`; one folder listed twice reported as a duplicate ID).
`run_all_checks.py --jobs 4`: 20 pass, 0 fail, 0 skip (1699 unit tests, 79 skipped for optional packages), including
`ams_optional` (the plugin without the AMS-02 profile), `claude plugin validate` and the Codex load check (Codex CLI
0.160.0, temporary `CODEX_HOME`). `check_relocation.py`: the relocated package (both manifests, validators, no
repository catalogs) passes 19 of 20, Codex load skipped there (no repository marketplace).
Host (Claude Code 2.1.293, temporary `CLAUDE_CONFIG_DIR`, a local clone as the marketplace, no `ams02-research`):
`claude plugin marketplace add <clone>` and `claude plugin install hep-research@hep-research-dev` at the 0.4.0 release
commit `f4245fb`, then the clone moved to this branch, `claude plugin marketplace update hep-research-dev` and
`claude plugin update hep-research@hep-research-dev`: updated 0.4.0 → 0.5.0. On a configuration with `ams02-research`
1.0.1 installed, `claude plugin update hep-research@hep-research-dev` was skipped with `Requires
"hep-research@hep-research-dev" ^0.4.0, installed 0.5.0`: the old companion manifest holds hep-research until the
companion is updated. Not run: a live routing run (paid; companion local-path routing is checked as text only),
the real GitHub marketplace after merge, and a Codex Git-marketplace update.
Catalog pin moved to `ams02-research` 1.2.1 (`32d538a`; no host dependency, its own check accepts hep-research
`>=0.4.0,<0.6.0`). Migration on an isolated Claude Code 2.1.293 host (temporary `CLAUDE_CONFIG_DIR`, a local clone as
the marketplace, starting from hep-research 0.4.0 `f4245fb` with the AMS pin set to 1.0.1 `1c3f590` in a scratch
commit): both installed (0.4.0, 1.0.1); after moving the clone to this branch, `marketplace update`, then
`plugin update ams02-research` (1.0.1 → 1.2.1), then `plugin update hep-research` (0.4.0 → 0.5.0). The installed
companion's `tools/check_compatibility.py --hep-root <installed hep-research 0.5.0>` reported `compatible`, with
`contracts/registry.py --local <companion>/profile` exit 0. Not run: `claude plugin prune` after migration.

## 0.6.0 release check (2026-10-09, E2)

Version 0.5.0 → 0.6.0 in both plugin manifests, `pyproject.toml`, the README and the capability matrix; the CHANGELOG
"Unreleased" section became 0.6.0 (AGENTIC-R5 rounds 4–6: T4.4 structured data exposure, T3.4 campaign limits, T4.2
bundle freezing, T1.2 data release manifest checker, T4.5 attestations, T4.6 operator semantics, T4.7 tool contracts;
catalogs list hep-research only). Contracts stay 2.1.0. Examples rerun with the E2 venv: only the embedded plugin
version changed (unfolding-coverage left as committed). `run_all_checks.py --jobs 6` with the E2 venv: 20 pass, 0 fail,
0 skip (1821 unit tests, 47 skipped for optional packages). The code release manifest `release-manifests/0.6.0.json`
is recorded in the release commit; the tag `hep-research--v0.6.0` points at the commit on main whose tree it describes.
The companion ams02-research 1.3.1 declares hep-research `>=0.4.0,<0.6.0`, so its preflight refuses this release until
the companion widens its range. Software checks establish consistency only; no host configuration is qualified for
private or blinded data by this release.
