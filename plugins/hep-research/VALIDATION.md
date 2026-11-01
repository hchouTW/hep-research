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
| E-crprop | The E2 host (macOS 26.5 arm64; Python 3.13.2 in the E2 venv with numpy 2.5.3, scipy 1.18.1) plus the external cosmic-ray propagation codes of the cr-propagation campaign: DRAGON2 (cosmicrays/DRAGON2-Beta_version commit cd588707, configure.ac DRAGON 3.1.0; serial build of 2026-10-15, binary sha256 d26dbb85…, data directory = the checkout's `data/`), built with Homebrew GCC 15.2.0_1 (g++-15, gfortran-15), GSL 2.8, CFITSIO 4.6.4, Autoconf 2.72, libtool 2.6.2; on the host also ROOT 6.38.04, cmake 4.3.2, Apple clang 21.0.0 (not used by DRAGON2). From 2026-10-28 (host now macOS 27.2, Darwin 27.2.0): USINE V3.5 (gitlab.com/dmaurin/USINE tag V3.5, tag object 7197ddc1, commit fb53006d; GPL-2.0; decision A1.1), built with cmake 4.3.2 and Apple clang 21.0.0 (`-O0`, C++17) against Homebrew ROOT 6.38.04 (GSL 2.8 through ROOT MathMore; CFITSIO not used), binary sha256 1d444720…, data directory = the checkout's `inputs/` (run with `USINE` set to the checkout). GALPROP v57 absent (no source, D5, A1.2). No batch client: local `local_partition.py` only (D6). Located through `HEP_DRAGON2_BIN`, `HEP_DRAGON2_DATA`, `HEP_USINE_BIN`, `HEP_USINE_DATA`; records in `tests/adapters/fixtures/cr_propagation/env/` |

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
| T12 | pass | `tests/skills/hep_measurement/test_check_systematic_variations.py`: unchanged integral with changed shape classified as shape |
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
| Batch adapter limits: allocation known only after a poll (GPU-CAMPAIGN-RUN) | GPU-hours count GPUs × time (`max_gpu_hours`), allocated GPUs once polled and requested before; HTCondor counts requested GPUs. On Slurm allocated CPUs count once polled; before that (the first submission, queued tasks) requested CPUs count times `limits.alloc_cpu_factor`, so without that key they are 2× low on hyper-threaded GPU nodes; HTCondor counts requested CPUs times that factor |
| PyTorch on GPU verified on two GPU types only (V100 with the CUDA 12.6 build, RTX PRO 6000 Blackwell with the CUDA 13.0 build; torch 2.14.1; TORCH-GPU-RUN) | other GPU types, multi-node DDP and FSDP not tried; GPU tests run only where `HEP_TORCH_GPU_TEST=1` is set on a GPU host (no GPU in CI) |
| pyhf demonstrated on two synthetic workspaces, asymptotic only | toy-based CLs, lumi/shapefactor modifiers and non-default interpolation codes not tried |
| CMS Combine checked on one synthetic counting card (E1 only); needs `HEP_COMBINE_WRAPPER`, and with ROOT 6.40 `--strictBounds` | the observed-limit search throws out of range under ROOT 6.40.04 without `--strictBounds` (OPTIONAL-TOOLS) |
| Slurm and HTCondor each run on one real site with synthetic campaigns only (Slurm 24.05.1 at NSTCCore, HTCondor 24.12.16 at CERN; NSTCCORE-SLURM-RUN, CERN-HTCONDOR-RUN) | `adapters/batch-schedulers` is `demonstrated-on-synthetic-data`; other versions and sites, and real-data campaigns, not tried; tool-fact rows not observed on those runs stay documentation-only |
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

## CERN-EOS-STORAGE (2026-10-10, E3, work order T06: CERN EOS storage note)

E3 (lxplus, AlmaLinux 9; `eos` client and `eosxd` 5.4.9, xrootd 5.9.7, ROOT 6.40.04; a node-local venv with Python
3.11.13, `requirements-core.txt`, uproot 5.7.7, awkward 2.14.0, fsspec-xrootd 0.5.5 and the XRootD Python bindings
6.2.0). Sources read 2026-10-10: the EOS project site (its content catalogue) and the EOS 5 documentation pages
introduction, architecture, using, interfaces and protocols ("last updated Oct 08, 2026"). Records: the user's task
folder (`T06-eos/runs/`, `T06-eos/sources/` with sha256 sums), not this repository.

**Synthetic checks on the user instance** (`root://eosuser.cern.ch` named in every command; never the instance the
login shell exports; one test directory in the user's home; random bytes and one synthetic NanoAOD-like file):
checksums from `xrdadler32`, `eos fileinfo` and `xrdfs query checksum` agree for 1 MB and 100 MB files, also from a
second node; a new directory inherits versioning 10, adler32, 2 replicas and atomic upload; `xrdcp -f` overwrites
keep versions, overwrites through the mount keep none; grabbing a version and restoring a deleted file from the
recycle bin give the original checksums; an upload killed after 0.7 s leaves nothing under the target name; a
user token for one file is refused, a directory-tree token works without Kerberos for reading and refuses writing;
`TFile::Open` and `uproot.open` read the file over `root://`; 200 small files cost about 25–40 ms each (single runs,
indicative). HTCondor check (E2f, run later the same day on the user's go): one espresso job (HTCondor 24.12.16,
RHEL 9.8 worker, `getenv = false`) had Kerberos and AFS credentials and the EOS mount, read a 5 MB synthetic file
with `xrdcp` (adler32 equal to the EOS checksum) and returned two files through `output_destination` with
`MY.XRDCP_CREATE_DIR`; `output` and `error` were sent to the destination too, only the user log stayed on AFS.
The site note's two EOS rows now carry these observations; the test folder was removed.

**Not as planned.** The test directory was removed, but a normal user cannot purge recycle entries on this instance
("cannot purge your recycle bin without being a sudo or having an admin role"), so its 207 entries expire after the
42-day lifetime; the user's quota returned to its earlier value. First attempts of three checks were inconclusive
because of the test sequence (mixed overwrite methods, an upload that finished before the kill, a file token) and
were repeated in isolation; the records keep both.

**Gate.** `check_packaging.py`, `measure_entrypoints.py` (hep-computing `SKILL.md` 8,190 of 8,192 B),
`reference_inventory.py --check` and a link check of the changed files (26 links) pass. The first full
`run_all_checks.py` run failed `check_layering` and its unit test: "CTA" (CERN Tape Archive) in the new note matched
an experiment name; the note now spells it out. Rerun on the final tree: **20 pass / 0 fail / 0 skip**; 1,840 unit tests, 1,741 pass, 0 fail, 99 skipped (8 fewer skips than the 915617d baseline because uproot and awkward were installed); profile suites ams-02 238, eic 43, synthetic-collider 9, qed-benchmark 18, qcd-r-ratio 21 pass.

## NSTCCORE-SLURM-RUN (2026-10-10, NSTCCore login node: first real Slurm runs of the batch adapter)

NSTCCore (ASGC/TWGrid), login node `slurm-ui-asiop.twgrid.org`, AlmaLinux 9, Slurm 24.05.1 (cluster `slurm-ctrl01`);
adapter driven by the login node's Python 3, workers the site's `anaconda3` Python 3.12.7; campaign in Ceph group space.
Each submission approved by the user. Records: the user's exercise folder (site notes, evidence per job), not this
repository. Plugin code changed only in the gated test (`RealSlurmTests`).

**Plain Slurm exercises (31 jobs, 0.15 CPU-hours, all `short`/`devel` partitions, at most 4 CPUs, 1 GPU, 10 min).**
Batch, failure, time-limit, over-memory, array, dependency, CPU and GPU layout, export-mode and priority behaviour,
recorded in `skills/hep-computing/references/batch-site-nstccore-slurm.md`. Findings that touch the adapter: an
over-`--mem` job swaps instead of reaching `OUT_OF_MEMORY` (no swap constraint); `--export=NONE` rebuilds the login
environment and empties `srun` steps unless `SLURM_EXPORT_ENV=ALL` (the template's `exec` in the batch step avoids
this); `DerivedExitCode` ignores the `.batch` step; `MaxRSS` is sampled every 15 s.

**Adapter (10 jobs).** `check-config` ok; `freeze`; `verify-bundle` identical; pilot `submit --pilot --submit` pinned to
the bundle and the reviewed `plan_digest` (one chunk, `COMPLETED 0:0`, 5 s); then the nine remaining chunks as one
array with throttle 4 (all `COMPLETED 0:0`, 3–8 s, at most 4 running). `status` complete, 0 duplicates, 0
quarantined, one attempt per chunk; `merge` 10/10 equals recomputing every chunk from the manifest seeds (`n` 1000,
`sum` identical to the last digit); `report --label synthetic` validates (`synthetic, unvalidated`). The `sbatch
--parsable`, template-option, `sacct` and `--version` rows of the tool facts are now marked observed.

**Gated test (2 jobs).** `RealSlurmTests` replaces its placeholder skip with the counterpart of `RealHTCondorTests`:
`HEP_SLURM_TEST=1`, `sbatch` on PATH and `HEP_SLURM_CONFIG` naming a user-reviewed configuration; a fresh campaign
beside its `campaign_dir`, two 100-item chunks with a worker that returns only additive fields, dry run, submission
pinned to the dry run's `plan_digest`, poll every 30 s (deadline 1200 s), merge equal to `sum(range(200))`, report.
It skips without the variables (checked both ways) and passed on NSTCCore in 31 s (array of two tasks, `COMPLETED
0:0`, 3 s each). `adapter.json`: Slurm `demonstrated-on-synthetic-data`, `tested_versions ["24.05.1"]`, so the
adapter, whose status is its least-tested tool's, is now `demonstrated-on-synthetic-data`; capability matrix,
adapter-authoring guide and README follow.

## TORCH-GPU-RUN (2026-10-11, NSTCCore GPU nodes through Slurm: first GPU runs of the physics-ml assets)

NSTCCore (Slurm 24.05.1), each job approved by the user: `b6000-al9_devel` (NVIDIA RTX PRO 6000 Blackwell Server
Edition, compute capability 12.0, driver 590.48.01) and `v100-al9_short` (Tesla V100-SXM2-32GB, 7.0, driver
575.51.03). Python 3.12.7 venvs with torch 2.14.1 and torchvision 0.29.1 plus `requirements-test.txt`: the CUDA 13.0
build for Blackwell, the CUDA 12.6 build for V100. No single build covers both: the 12.6 build is compiled for
sm_50–sm_90, the 13.0 build for sm_75–sm_120 (the 12.8 index tops out at torch 2.11.0, sm_75–sm_120). 11 jobs (10 ran),
0.31 GPU-hours. Records: the user's `torch-gpu` folder (job scripts, evidence per job, `results.md`), not this repository.

**Existing tests on GPU nodes, unchanged.** With two visible GPUs all 130 physics-ml tests pass on both types. With
one visible GPU `test_ddp_skeleton_two_gloo_processes` fails on both: the skeleton picks NCCL whenever CUDA is
available and rank 1 fails at `torch.cuda.set_device(1)` with `torch.AcceleratorError: CUDA error: invalid device
ordinal`; with two GPUs the test passes but runs NCCL, not the gloo it is named for. Fixed: the test hides the GPUs
from its child processes (`CUDA_VISIBLE_DEVICES=""`), so it tests gloo everywhere (passes on a 1-GPU node).

**GPU paths (1 GPU, both types).** `train_classifier.py` on CUDA with and without `--use-amp`, then `inference.py`
on the checkpoint; `benchmark_model.py` with and without `--amp`; `lora_finetune.py`; `TransformerClassifier` on CUDA
with fp16 autocast (its own `__main__` smoke test has no CUDA path); `vision_transfer.py` on a synthetic ImageFolder
with `weights=None`. All exit 0. Tolerance for CPU vs CUDA training with the same seed, fixed before the V100
comparison: final validation loss within 5 % relative; observed −0.07 % (CUDA) and −0.20 % (AMP), the same on both
GPU types. AMP was slower than fp32 for the tiny benchmark MLP (casts dominate). `torch.cuda.is_bf16_supported()` is
True on V100, which has no native bf16 (emulation counted). No GPU-only bug found in the assets.

**NCCL DDP (2 GPUs, both types).** `ddp_train_skeleton.py` through `torchrun --nproc_per_node=2`: `epoch=5`, checkpoint
written; NCCL 2.29.3 over SHM on V100 (GPUs on different NUMA nodes), NCCL 2.30.7 over P2P on Blackwell.

**Gated test.** New `tests/skills/physics_ml/test_gpu_real.py` (`HEP_TORCH_GPU_TEST=1` and CUDA available): CPU vs
CUDA training with and without AMP within the tolerance, inference on a CUDA checkpoint, transformer forward/backward
with fp16 autocast, and NCCL DDP when two GPUs are visible (asserts NCCL in the log). Skips without the variable,
without CUDA and without torch (checked all three on the login node); passed on 1 Blackwell GPU (NCCL test skipped)
and on 2 V100 GPUs (all pass). The capability matrix and the known-limitation rows follow; the stale batch-adapter
limitation row is corrected as well.

**Follow-up (after 0.6.8): `check_pytorch_env.py`.** On a V100 node the CUDA 13.0 build reports CUDA unavailable —
"The NVIDIA driver on your system is too old (found version 12090)": the driver supports CUDA 12.9 at most — so the
mismatch is a driver one before it is an architecture one, and the script used to print "CUDA available: False" and
exit 0. It now exits 3 with torch's reason when `nvidia-smi` sees GPUs that the build cannot use, and exits 3 when a
visible GPU's compute capability is outside the build's compiled list; with `CUDA_VISIBLE_DEVICES=''` it still exits 0.
Verified on `hp-teslav06` (job record in the user's `torch-gpu` folder): CUDA 12.6 build exit 0 ("supported"),
CUDA 13.0 build exit 3, hidden GPUs exit 0. Release check for 0.6.9 (docs/maintenance.md, "Real-hardware checks"): the `gpu-tests` run on
PR #41's head commit `03929e2` (B6000 with the CUDA 13.0 build, 1 GPU; V100 with the CUDA 12.6 build, 2 GPUs; 140
tests each, all pass, NCCL test run on 2 GPUs); no `physics-ml` code or test changed between that commit and the
release.

## GPU-CAMPAIGN-RUN (2026-10-11, NSTCCore V100: first GPU campaign of the batch adapter)

Slurm 24.05.1, `v100-al9_short`, `resources {cpus 1, gpus 1, memory_mb 8000, time_limit 00:10:00}`, `worker_python` a
venv with torch 2.14.1 (CUDA 12.6 build). Synthetic worker: points drawn on the CPU from the manifest seed and
counted on the GPU in integer arithmetic, additive keys only, including `on_cuda`. 2 chunks; `check-config`,
`freeze`, reviewed dry runs, pilot then the rest, `status`, `merge`, `report`; each submission approved by the user.
Records: the user's `torch-gpu/gpu-campaign` folder.

- `#SBATCH --gpus=1` (from `resources.gpus`) is accepted and recorded as `gres/gpu=1`, the same as `--gres=gpu:1`;
  the job keeps QoS `normal`.
- Both chunks `COMPLETED 0:0`, one attempt each, no duplicate; merged `on_cuda` 2; merged `n_points` and `inside`
  identical to a CPU recompute from the manifest seeds. The report validates (`synthetic, unvalidated`).
- **Limit accounting:** 1 CPU requested, 2 allocated and billed (whole cores on hyper-threaded GPU nodes), while the
  adapter's usage counted requested CPUs × elapsed time (0.001111 core-hours for a 4 s chunk): `max_core_hours`
  under-counts by 2× here, and GPU-hours are neither tracked nor limited. **Follow-up (Unreleased):** the Slurm poll
  now reads `AllocCPUS` and the limit counts allocated CPUs, projecting new jobs at the observed factor; `sacct` on
  these two jobs reports `AllocCPUS` 2 (1 for the CPU campaign's jobs), and that output is a parser test
  (now `test_poll_parses_real_sacct_alloc_cpus_and_gpus`). **Second follow-up (Unreleased):** `max_gpu_hours`;
  `sacct` on these jobs reports `AllocTRES` `gres/gpu=1` for the 1-GPU job and no `gres/gpu` for the CPU campaign's
  job (read-only query, 2026-10-11), and both lines are in that parser test. Release check for 0.6.10
  (docs/maintenance.md, "Real-hardware checks"; the release changes the batch adapter): `RealSlurmTests` with
  `HEP_SLURM_TEST=1` and the user's reviewed configuration on NSTCCore (Slurm 24.05.1, `edr1-al9_short_serial`,
  2026-10-12, user-approved) on `main` at `9522ec0`: array 7061186, 2 synthetic CPU chunks COMPLETED on `hpa-wn06`,
  merged equal to a single run, test OK in 34 s. Both attempts recorded `alloc_cpus` 1 and `alloc_gpus` 0 from the
  8-field `sacct` (`AllocTRES` `billing=1,cpu=1,mem=200M,node=1`).
- `MaxRSS` of a 4 s chunk is 0.07 MB (accounting samples every 15 s), as in the CPU campaign. `freeze` refuses a
  `#!/usr/bin/env python3` worker ("name one interpreter only").

## STATS-AUDIT (2026-10-12, E2 + pyhf 0.7.6, ArviZ 0.23.4, ROOT 6.38.04; version 0.6.10 + unreleased): hep-statistics audit T01–T30

Work order: the hep-statistics audit handed over on 2026-10-10 (audit commit `b5c3a55`, findings F01–F04, checks
T01–T30; the bundle is kept outside the repository). Branch `feat/stats-audit-p0` from `1d42271`. `git diff
b5c3a55..1d42271` touches no statistics file, and the audit's reproduction program printed output identical to the
audit's on `1d42271`: all four findings still held. ArviZ was installed in an isolated environment; pyhf from the E2
venv; PyROOT from Homebrew's Python 3.14. Combine was not available: every Combine statement below is unverified in E2.
Software checks: consistency and the stated oracles only, within the stated synthetic or public scope.

| Item | Result | Evidence |
|---|---|---|
| F01–F03 (T01–T05) | pass; 8 of the 20 first regressions fail on the audited `likelihood_limits.py` (red), all pass after the fix | `tests/core/test_stats_p0_regressions.py` (now 25 tests) |
| F04 (T06–T08) | pass; the audit's four mutations rejected or unresolved at contract 2.2.0 and with `--strict`; unresolved or failed at the publication gate; every legacy fixture keeps its outcome | `tests/contracts/test_statistical_semantics.py` (22 tests) |
| T09 exact counting | pass: classical and CLs equal SciPy roots (n ≤ 8, five b, 90% and 95%); FC equals an independently written ordering within two grid steps | `test_stats_counting_asymptotic_oracles.py` |
| T10 asymptotic forms and gate | pass: arXiv:1007.1727v3 eqs. (14), (16), (101) to 1e-10; gate consistent at n = 60, b = 45, inapplicable at n = 3, b = 0.3 (20,000 toys agree with the exact tail), not-applicable at q0 = 0 | same |
| T11 toy CLs | pass: limits 4.12 / 4.27 / 4.28 (200 toys 12 points, 400 toys, 18 points) within the quadrature of the ranges plus half a grid step; doubling the toys narrows the range; a floored CLb is not a resolved limit | `test_stats_toy_ensemble.py` |
| T12, T13 ensembles and accounting | pass: partitioned tasks merge to the single run; duplicates and gaps refused; with 5% injected fit failures plus empty, invalid, timeout and error outcomes, counts sum to N and C/N, (C+F)/N, C/(N−F) are kept | same |
| T14 coverage grid | pass: exact coverage of the classical and FC belts ≥ 0.950 at 28 (s, b) points (CLs ≥ 0.9502, reported); the asymptotic profile limit at 8 points (20,000 toys each) 0.945–1.000, all pass the predeclared gate; toy calibration 0.98245 vs exact 0.98168; the negative control (sigma_b ignored) covers 0.873 and is rejected | `examples/stats-benchmarks/coverage-grid/` |
| T15 SR/CR | pass: pyhf fit equals the closed form within 5e-5; Asimov closure unbiased; omitted CR contamination biases mu by −mu s_CR b_SR / (b_CR s_SR) and fails closure | `tests/adapters/test_sr_cr_model_card.py` |
| T16 backends | core–pyhf pass: Delta NLL 1e-15, q-tilde 1e-11 on three models; a wrong interpolation code caught after tightening the pointwise tolerance to 1e-9; Combine **not run** | `test_backend_likelihood_equivalence.py` |
| T17 published likelihood | asymptotic (primary, preregistered) **reproduces**: S95 obs 4.876 (4.9), exp 5.135 (5.1), −1/+1σ 3.431/7.910 (3.4/7.9), CLb 0.451 (0.45), p0 0.4997 (0.50), post-fit SM yield 3.232 (3.3); negative control (no CR) fails; toy-based (5,000 toys, 7 points) **does not reproduce** the observed (5.28, MC range 5.03–5.56) and −1σ (3.94) limits; median 5.19 and +1σ 7.59 agree (crossings now interpolate log CLs; the first, linear interpolation read 5.34/4.03/5.27/7.70 with the same toys, same verdicts). **Diagnosed (post hoc, not preregistered):** SRB is one bin with n = 3, b = 3.23; the exact counting CLs limit is 5.284, inside the toy range; pyhf's ToyCalculator matches exact Poisson sums on the bare one-bin model (CLs+b and CLb inside 99% Clopper-Pearson intervals at S = 4, 5, 5.5, 4,000 toys each); pyhf's asymptotic formulae give 4.68 on that bare model, 12% below the exact limit. The toys are correct; the asymptotic construction understates the limit at n = 3, and the published values follow it (an inference: the paper does not state its construction) | `examples/stats-benchmarks/published-likelihood-sbottom/`; download rerun checked |
| T18, T19 covariance fits | pass; Peelle setup (1,000 toys): data-scaled bias −0.043 ± 0.007, C(theta) with ln det −0.039 ± 0.007, normalization nuisance −0.002 ± 0.007 | `test_covariance_fit.py` |
| T20 signed weights | pass: Gaussian MC term covers 0.679 and 0.683 (5,000 toys, two seeds) with 20% negative weights; 0.526 without | `test_stats_weighted_mc.py` |
| T21 sWeights | pass: asymptotic pull width in [0.9, 1.1], bootstrap within 10%; RooFit AsymptoticError equals the sandwich to 1e-4; RooFit SumW2Error 0.0444 vs 0.0389 here, unexplained; independence check size 4/400, power 100/100 | `test_sweighted_fit.py` |
| T22, T23 unfolding | pass: inversion covers 0.68 per bin and jointly; omitting the efficiency or MC term undercovers (0.41–0.54); Tikhonov with per-toy GCV on another truth covers 0.43 jointly | `test_stats_unfolding_outer.py` |
| T24 Bayesian diagnostics | pass: equal to ArviZ 0.23.4 to 1e-9 on six chain sets; constant chains undefined (ArviZ: ESS = draws) | `test_bayes_arviz_oracle.py` |
| T25 Bayesian calibration | pass: conjugate quantiles within 4 MCSE; a missing Jacobian fails; SBC power 1.0 against a 0.7 width; false alarms ≤ 4/60 | `test_bayes_calibration.py` |
| T26, T28, T29, T30 (EXPERIMENTAL) | pass within their controlled examples | `test_eft_scan.py`, `test_global_significance.py`, `test_pcl_efficiency_ratio.py`, `test_ratio_estimation.py` |
| T27 (EXPERIMENTAL) | partial: 300 toys × 4 truths (one outside the family) × mu = 0, 1, selection redone per toy, 1 failed toy counted; the envelope meets the bias criterion everywhere (|bias| ≤ 0.18 of the spread), a single exp1 form fails it where its form is wrong (up to 0.49); envelope coverage 0.647–0.697 is **insufficient-precision** against the predeclared 0.633 bound (300 toys cannot decide it): coverage not established | `examples/stats-benchmarks/discrete-profile/` |
| T27 follow-up (2026-10-12) | pass: 1,500 toys per envelope row (preregistered, seed 20261013): bias ≤ 0.09 of the spread, coverage 0.665–0.694 with lower bounds 0.634–0.663 ≥ 0.633 at every truth and signal | `discrete-profile/output/results-envelope-1500.json` |
| Combine release gate (GitHub, 2026-10-12) | pass after a fix (package `cms-combine`): Combine 11.1.0, ROOT 6.36.14, 3 tests, 0 skipped; published-likelihood job passed on main, not-run once (download failed, exit 4). First all-green run 38219873921 (branch with the fixes): published pass (2 min), combine pass (11 min), campaigns pass (58 min: coverage grid at 20,000 toys and the 300-toy T27 rerun in parallel with the cross-platform tolerance) | `statistics-validation.yml` runs 38212946007, 38213199345, 38219873921 |
| Required backends gate | 119 tests, 0 failures with pyhf 0.7.6 and ArviZ 0.23.4; fails naming ArviZ without it | `tools/run_required_backends.py` |
| CI workflows | `stats-backends` job and `statistics-validation.yml` written and YAML-parsed; **not yet run on GitHub** | `.github/workflows/` |
| Aggregate | pass: 18 checks pass, 2 CLI checks skipped (`--no-cli`); 2,007 unit tests, 0 failures, 0 errors, 55 skipped (slow tier, network, GPU, scheduler and optional tools); `tools/check_relocation.py` passes | `tools/run_all_checks.py --no-cli` |

Found and fixed along the way: ties crashing and constant chains reported healthy in `bayes_diagnostics.py`; toys
silently dropped in `statistical_toys.py ratio` and `unfolding_diagnostics.py response-stat`; signed-weight templates
accepted by the effective-count likelihood; a duplicated test class hiding two covariance tests; citation numbers of
Cowan et al. (one written in this work was wrong). An independent review of the branch found further defects (typed
2.2 fields changing legacy outcomes, a permissive publication gate, the gate at q0 = 0, stale global fits, a
`beta_ppf` underflow), all fixed with tests. pyhf 0.7.6's toy expected bands fail with NumPy ≥ 2.4 (upstream).

## RC-TRACEABILITY (2026-10-12, E2, version 0.6.12 + unreleased): research-communication reliability plan T0–T11

Work order: the research-communication implementation plan (revision 2, inspected baseline `1d42271`, plugin 0.6.10,
contracts 2.1.0), executed on `e699b24` (plugin 0.6.12, contracts 2.2.0) on branch
`feat/research-communication-traceability`. Host: E2 (macOS, Python 3.13.2) with Graphviz, Mermaid CLI with Chromium,
PlantUML, Java and tectonic on PATH. All fixtures are synthetic; the `observed` label of the golden input simulates a
measured result. Software checks: consistency only, not scientific support or physical validity.

**T0 discrepancy log (before):** F1 a claim with numeric text, null `result_ref` and object status validated (ok,
no findings); F2 a dangling `result_ref` and an unknown `sources_read` id validated (by design of the pure validator;
no project bridge existed); F3 an observed-only claim in a mixed observed/synthetic document was rejected
(`communication.status_upgraded`); F4 an empty manuscript directory exited 0 with "No issues found"; F5 a label in an
unincluded sibling `.tex` satisfied a reference in `main.tex` (exit 0); F6 `code-review-report.md` sent the statistical
treatment of ROOT/uproot code to hep-analysis; F7 "Checked N block(s)" counted linted and skipped diagram blocks; F8
`evals/` held routing only. Reproduced with minimal fixtures on `e699b24` before any change. The one failing
diagram test of the review (Chromium startup) did not reproduce on E2: every shipped diagram renders here.

| Item | Result | Evidence |
|---|---|---|
| T1 contracts | pass: F1 types rejected, F3 claim-scoped propagation, capability dispatch and old-reader rejection, mixed provenance, comparison and contradictory-evidence cases, assessment currency, layering (no cycle, no file opened by pure validation); project resolution of inputs, ledgers, sources, documents, bound-profile ledgers and vocabulary; outcome normalization and output aliasing | `tests/contracts/test_communication.py` (29), `test_communication_project.py` (21); fixtures `communication_traceability.json` and four invalid, one unresolved |
| T2 manuscript | pass: F4 empty directory exit 2; F5 unincluded label no longer resolves in `--main` mode; nested includes, suffixes, missing includes, cycles, build-root semantics, out-of-root refusal (audit hook), macro-generated and conditional includes incomplete, `\includeonly`, verbatim bodies, declared bibliography only, unassociated `.bbl` unresolved, separate documents sharing labels, JSON report | `test_check_manuscript_main.py` (22); the 25 earlier tests unchanged |
| T3 diagrams | pass: F7 per-block outcomes reconcile with the total; preflight once, broken renderer not relaunched (launch counter), parse error vs timeout vs no output, strict mode exit 3, SVG XML-only, TikZ skipped; real `dot` rejects bad source as a source error; shipped bundle at merge: 74 blocks, 58 rendered, 2 lint-only (SVG), 14 skipped (7 TikZ plus 7 LaTeX code examples); after the review minors a ```latex fence counts only with a tikzpicture: 67 blocks, 58 rendered, 2 lint-only, 7 skipped | `test_diagrams.py` (30) |
| T4 handoffs | pass: F6 fixed; routing by the question in `code-review-report.md` and the papers guide; significance table scoped; reuse of verified records; response wording from completion state; 157 routing cases pass the static check | `test_handoff_text.py` (6), `tests/routing/` |
| T5 claims and reporting | pass: golden scenario (abstract, body, caption located; wrong manuscript sentence behind a correct manifest fails; unresolved source incomplete; schema-only opens no project file); claim audit (unsupported verdict fails, abstract value citable with its locator while an unread table is unresolved, status-promotion and discovery wording advisory with a hep-statistics handoff, rounding within the declared rule accepted, outside it failed, unit conversion unresolved); reporting policies for five result types | `test_communication_audit.py` (20), `test_claim_audit.py` (18), `test_reporting_completeness.py` (12) |
| T6 revisions | pass: changed result lists exactly the three stale occurrences and keeps the illustration; rename, same-filename replacement (old value not recovered from today's file), rounding-only edit, stronger wording, metadata-only change, one claim changed, overwritten history, unmapped coverage, verified items reopened or lacking evidence | `test_revision_impact.py` (17) |
| T7 literature | pass: identifier-only merges, similar titles proposed not merged, report and study related, arXiv version history flags claims, partial notice flags one claim to reassess and the other to check, retraction asserts no falsity, journal-version supersession, incomplete search unresolved, access limitation, quoted instruction kept as data, citation-key collision; input never edited | `test_literature_lifecycle.py` (16) |
| T8 adaptation | pass: consistent summary passes; missing statement, missing claim id, wrong number, dropped status label, dropped caveat (paraphrase declared counts), universal wording, stale record, missing semantic review; reviewer responses: pending rerun not worded as done, completed change past tense with locator, many-to-one and one-to-many links, reasoned decline | `test_adaptation.py` (15) |
| T9 terminology | pass: acceptance/efficiency in Chinese and English, precision/resolution, confidence/credible, quoted mention skipped, bilingual aliases fine, scoped symbol reuse vs drift, undeclared scope, abbreviation redefined and used before definition, LaTeX and a second document | `test_terminology.py` (14) |
| T10 evaluation | infrastructure pass: eleven cases, scorer self-tests (good output, uncertainty-stating correct answer, prose inventing a result behind a correct manifest, invented citation with the right skill, hidden promotion, false completion, everything-unresolved, unjudged never pass, summary lists every critical failure). Live run `live-20261013-sonnet` (2026-10-13, claude-sonnet-5-5, Claude Code 2.1.296, plugin `f7709da`, $0.71, 11 of 11 cases): 6 pass, 4 fail (routing: four quick cases answered without a plugin skill), 1 critical-fail (a referee reply asserting an edit with only a bracketed caveat); no fabricated identifier, invented number or status promotion; semantic judgments by the executor, not an independent review; scorer calibrated to 1.1 on this run (the first scoring's 7 critical failures were scorer artifacts except one) | `evals/research_communication/results/live-20261013-sonnet.json`; `tests/test_score_replay.py` (22) |
| T11 integration | pass: worked example regenerates byte-identical reports (`examples/evidence-linked/`, five steps including the unresolved branch); capability matrix, references, SKILL.md and README updated; `run_all_checks.py --no-cli --jobs 4`: 18 checks pass, 2 CLI checks skipped (`--no-cli`); 2225 unit tests after the review fix pass (2209 before), 0 failures, 0 errors, 96 skipped (slow tier, network, GPU, scheduler and optional tools); a first run failed one packaging test because a test file then held a literal private-path string, fixed before the second run | `test_worked_example.py` (3) |
| Whole-branch review | a fresh reviewer found 2 critical and 8 important defects (a claim audit passing on a missing or replaced evidence file; a rename plus stronger wording not reopening an assessment; a crash on a new edge; baseline refs read outside the root; a silent locator miss; prefix-matched read coverage; a LaTeX include reported as a mismatch; false abbreviation and definition conflicts; negated completion wording flagged; English-only status words), all fixed with sixteen regression tests; eleven minor items deferred and listed in the PR | `ReviewFixes` classes in the research-communication tests |

Not verified here: online literature verification (no lookup is performed by any new tool); rendering of diagrams on a
host without Chromium (the preflight path is covered by fake renderers only); behavioral quality of any model on the
new cases; Combine, ROOT and GPU paths (unchanged by this work). The branch kept contracts at 2.2.0; release 0.6.13 bumps them to 2.3.0 (minor) with the capability
`communication:traceability-v1`.

## SKILL-TRIM (2026-10-13, E2, version 0.6.14 + unreleased): detector-response, hep-statistics, hep-computing

The three `SKILL.md` files sat within 30 bytes of the 8 KiB budget. Their reference and script lists moved into index
sections of `detector-principles-summary.md`, `core-stats-guide.md` and `engineering-playbook.md` (6566, 7545 and 7598
bytes after; descriptions, Owns lines, invariants and handoffs unchanged; every skill now points to its folder README).
Static routing (157 cases), ownership, layering, instruction-text, packaging and the reference inventory pass. Live
routing rerun of the 80 cases that involve the three skills (claude-sonnet-5-5, Claude Code 2.1.296, $5.96): 75 of 80
strict; against the 2.1.293 baseline one quick case regressed (`st-sensitivity-1`, 1 pass in 3 repeats on the trimmed
tree: stochastic, and its routing description did not change), one improved, two second-turn misses as before, two
cases newer than the baseline missed; 0 loading violations. Recorded in `evals/routing/README.md`.

## PHYSICS-ML-ENFORCEMENT (2026-10-13, E2 + PyTorch 2.14.1 on CPU, version 0.6.16 + unreleased, contracts 2.5.0)

Open items of the external physics-ml review (Chapter 8 patch merged as PR #59; this entry covers its section 8.4 and
roadmap phases 1, 2 and 4). Scientific checks, not only smoke tests:

| Item | Result | Evidence |
|---|---|---|
| Domain check, 800 points from a 20-D standard normal, query (2, ..., 2) | flagged outside (Mahalanobis about 9.3, threshold about 6.6); the old check called it inside | `test_check_surrogate_domain.py` |
| Domain check, 200 in-distribution draws at q = 0.99 | about 1 % flagged; reported false-positive rate from a held-out cross-fit | same |
| Domain check, correlated features, point inside the per-feature box but off the ridge; constant feature; dimension mismatch | outside; no overflow; exit 2 | same |
| Grouped splits by run, period (temporal) and k-fold | manifests pass `check_split_integrity.py --strict`; deterministic for a seed; folds disjoint | `test_make_grouped_splits.py` |
| Split check with null groups and case or whitespace variants | reported, not a pass | `test_split_integrity_normalization.py` |
| Training pipeline | a leaky manifest stops training before a model is built; test ids disjoint from validation; model hash matches `best.pt`; out-of-domain rows flagged, refused with `reject` | `test_training_pipeline.py` (21 tests) |
| Calibration on a toy with known miscalibration (T = 3) | T recovered within 0.06; T near 1 for a calibrated input; isotonic reaches the ECE floor; integer weights equal duplicated events | `test_calibration.py` (21 tests) |
| Set classifiers | permutation and padding invariance at 1e-5, finite outputs for empty sets, toy AUC above 0.6 | `test_set_classifier.py` (10 tests) |
| ml-artifact contracts 2.5.0 | each new code fires at its level; 2.4.0 artifacts keep their outcome without `--strict`; lint with the CI pins (ruff 0.16.10, mypy 2.4.0) clean on `core/` and `contracts/` | `test_ml_contract.py`, `test_write_ml_artifact.py` |
| Journey J9, `examples/ml-classifier-to-inference/` (SYNTHETIC, seed 20261013, NumPy trainer, runs without PyTorch) | 12 of 12 pre-declared criteria pass: random row split caught (leakage in all 24 runs), grouped split passes, ECE 0.0176 after calibration (floor 0.0158), injected `pt_miss` shift detected (KS D 0.056, floor 0.024), 9 of 357 pseudo-data rows out of domain, Asimov mu 1.000000, toy pull mean -0.055 and width 0.984, 68 % coverage 0.693, pseudo-data mu 1.307 +0.281 -0.261 (GoF p 0.80); both artifacts validate and the statistical-result links the ml-artifact by sha256; `results.json` byte-identical between the E2 venv and miniconda; the `--trainer torch` path also passes all criteria (run once) | `tests/examples/test_ml_classifier_to_inference.py` (8 tests) |
| Reference snippets (ONNX `dynamo=True` with onnxruntime at a new batch size and multiplicity, `torch.export` and AOTInductor, checkpoint resume bit-identical, seeded workers, bf16 and fp16 recipes, `torch.compile` dynamic shapes, FSDP2 + DCP on gloo world size 1) | run; each marked with the version | onnx/onnxruntime in a scratch target dir, not in E2 |

`tools/run_all_checks.py` with the host CLIs and the E2 venv: 20 of 20 checks pass; 2,458 unit tests, 0 failures, 55
skipped. Not run: GPU, multi-GPU NCCL for FSDP2, a benchmark-dataset performance study of the set classifiers. The
J9 example's fit uses private helpers of `core/stats/likelihood_limits.py` (`template_fit.py` refuses signed-weight
templates).

## THEORY-AUDIT (2026-10-13, E2 + SymPy 1.14.0, version 0.6.17 + unreleased, contracts 2.6.0): hep-theory audit THY-WP0 to WP5

Each fix had its regression test seen failing on the `c1d375c` code first (counts in the commit messages).

| Finding | Regression test | Before | After |
|---|---|---|---|
| `pdf_uncertainty.py` mixes the two alpha_s members into a `symmhessian` delta; `+as` types refused; NaN member ok | `tests/skills/hep_theory/test_pdf_uncertainty.py` | 43 members: delta 0.0443; `symmhessian+as` failed; NaN gave `ok` | `+as`: PDF delta 0.012649 (40 eigenvectors), separate `alphas.delta` 0.03; `num_members` mismatch, NaN refused (exit 1) |
| `eft_truncation.py` sums `a*b` and `b*a`; empty conventions ok; `lambda_tev` 0 traceback; rescaling check absent | `test_eft_truncation.py` | quadratic 0.11, ok; `ZeroDivisionError` | refused with both spellings named; `rescaling_check: pass`; flag fraction with its source |
| `event_weights.py`: index -1, 7, repeated indices; negative sigma and luminosity; NaN weight | `test_event_weights.py` | wrap-around, `IndexError`, fraction 1.5, ok | refused (exit 1, JSON); selected sum w, sum w^2, N_eff, relative uncertainty to 1e-12 |
| `dis_kinematics.py` ignores the lepton mass in the bounds; target at rest refused | `test_dis_kinematics.py` (+5) | muon y = 1 and Q^2 below Q^2_min accepted | exact y_max, Q^2_min(y) against a 60-digit angle scan (1e-9, collider and fixed target); refused outside |
| theory-spec / prediction invariants unchecked (six audit copies all `ok`, also with `--strict`) | `tests/contracts/test_theory_contract.py` (16 tests), fixtures from `make_fixtures.py` | no rule fired | eleven codes at their levels from 2.6.0; 2.5.0 artifacts keep their outcome, codes with `--strict` (API and CLI) |
| Committed theory examples | same, `CommittedExampleTests` | 2.5.0, `folded_expectation` unlinked, truncation without method | 2.6.0, numbers byte-identical (word diff: versions and added fields only) |

References `amplitudes-and-widths.md`, `selection-rules.md`, `regularization-and-schemes.md` and the cosmic-ray
additions cite sources opened on 2026-10-13 (PDG 2026 reviews, arXiv papers, the Gleeson-Axford ADS scan) or say
`unverified` (Furry's theorem, read only in a tertiary source; isospin and strangeness conservation by interaction;
LHAPDF `.info` files, blocked). New profile `theory:higgs-bb-width`: 25 tests (derivation with exact mu-independence
through alpha_s^4 and negative tests, prediction, convention mismatches, missing SymPy) pass in E2; in
`sympy-py313` 25 run, 9 skipped (no scipy). Gamma(H -> b bbar) = 2.386 MeV at alpha_s^4 (scale envelope 2.384-2.386
MeV), a perturbative argument conditional on the stated exclusions.

`tools/run_all_checks.py` with the host CLIs and the E2 venv: 21 of 21 checks pass; 2,525 unit tests, 0 failures, 55
skipped; profile suites ams-02 238, eic 43, synthetic-collider 9, qed-benchmark 18, qcd-r-ratio 21, higgs-bb-width
25. `check_relocation.py`: pass. Lint with the CI pins (ruff 0.16.10, mypy 2.4.0) clean on `core/` and `contracts/`.
`make_fixtures.py` and `make_cases.py` leave no diff on a second run. Not run: a live routing run (paid); CI on a PR
(no PR opened); LHAPDF, MadGraph or any generator.
## HEP-ANALYSIS-AUDIT (2026-10-13, E2, version 0.6.17 + unreleased, contracts 2.6.0)

hep-analysis audit P0-1 to P4-8 on branch `fix/hep-analysis-audit`.

Live routing evidence for the fourteen new boundary cases (`an-b-*`, one en and one zh-Hant per boundary): **pending**.
A live run makes paid model calls and was not authorized for this branch; the static check covers the cases (179
cases, 0 failed). The description changed only by dropping "space or ground-based" (925 to 897 characters, Q7), so the
previous live routing baseline stays the reference until that run.

| Item | Before (`c1d375c`) | After | Evidence |
|---|---|---|---|
| hep-analysis `SKILL.md` | 8,157 B, description 925 characters | 7,795 B, 897 characters | `tools/measure_entrypoints.py` |
| Analysis guide | 219 lines | 118 lines | `tests/skills/hep_analysis/test_reference_links.py` |
| Validator mutation probe (30 spec violations of the SKILL.md invariants, plain and `--strict`) | 30 silent passes (contracts 2.5.0) | 2 silent passes (contracts 2.6.0): `objective_x` (the estimand now lives in `estimand`; `estimand: "x"` fails) and `ratio_cancels_no_verification` (a warning by design) | audit probe, `tests/contracts/test_measurement_contract.py` |
| `cosmic_ray_flux.py` (n = 3, b = 10 +- 1) | flux -7, interval [-8.9, -3.9] | lower bound 0, upper limit 0.2 (Cousins-Highland) | `test_cosmic_ray_flux.py` |
| `cosmic_ray_flux.py` N = 480, 1000, 10000 | N = 480 exits 2 (500 ceiling) | Garwood bounds equal scipy chi2 to 1e-6 | same |
| Orbit cutoff, 51.6 deg, 1.065 Re | min 1.96 GV (untilted) | tilted dipole (pole as input), 30 days: geomagnetic latitude +-60.9 deg, min 0.735 GV, mean 6.97 GV | `test_orbit_cutoff.py` |
| Deuteron mass in the cutoff conversion | 1.863 GeV (A x u) | 1.875613 GeV (AME2020) | `test_nuclear_masses.py` |
| Systematic check, +-1e-5 wiggle with 1% errors | "shape" | "none" (5% tilt: "shape") | `test_systematic_stat_test.py` |
| Change review, four documented evasions | accepted, exit 0 | flagged or exit 2 | `test_review_analysis_change.py` |
| Ratio 3/5 | 0.6 +- 0.438 | Poisson ratio [0.218, 1.564] at 68.27% | `test_ratio_intervals.py` |

`tools/run_all_checks.py --out <scratch>` with the host CLIs and the E2 venv: all checks pass after the AMS-optional
fix; unit tests 2,596 run, 0 failures, 55 skipped (201 modules). Lint with the CI pins (ruff 0.16.10, mypy 2.4.0) on
`core/` and `contracts/`: clean. Physics statements corrected with sources opened on 2026-10-13: SILSO cycle table and
news item (cycle 24), Kampert & Unger 2012 (sigma(X_max)), Gross & Vitells 2010 (trials), Barlow hep-ex/0207026
(passed checks), AME2020 and CODATA 2022 (nuclear masses). Not done: simulated backgrounds and masked outputs inside
the two example pipelines (P4-2 partial; completed in HEP-ANALYSIS-P4-2 below).

## HEP-ANALYSIS-P4-2 (2026-10-13, E2, version 0.6.17 + unreleased, contracts 2.6.0)

hep-analysis audit items P4-2 and P3-12 on branch `fix/hep-analysis-p4-2`: simulated backgrounds with a sideband
estimate and closure, and a blinded output, inside both journey pipelines. All inputs synthetic.

| Example | Background and estimate | Closure (pre-declared criteria) | Blinded output |
|---|---|---|---|
| `collider-angular` (Path B) | tau-pair-like sample from the synthetic-collider generator; B = TF x N(0.5 <= x_vis < 0.8), TF = 0.0707, 10% fully correlated; 414.9 events in the unblinded signal-region bins | Asimov 2.2e-16; validation band 0.8-0.9: observed 1171, predicted 1173.0, pull -0.05, chi2 13.7/12 (p 0.32); toys run the blinded procedure | forward signal-region bin cos theta >= 0.9 (outside the fiducial range); fiducial sigma 746.50 +- 6.73 (stat) +- 2.23 (bkg) +- 14.93 (lumi) pb, expected 745.81 |
| `ams-flux-ratio` (Path A) | Z=1 charge tail in the helium window; B = TF x N(1.3 <= Q < 1.6), TF = 0.1710, 10% fully correlated | Asimov 2.2e-16; validation band 1.6-1.7: period 1 observed 259, predicted 308.6, pull -2.68, chi2 10.5/8; period 2 observed 416, predicted 390.0, pull 1.25, chi2 8.2/9 (pull spread over seeds 0-9 consistent with unit width) | helium signal-region count at 60-100 GV in both periods; helium flux, He/p ratio and period average null there, dataset records stop at 60 GV |

Both pipelines mask through `mask_blinded_bins.py` as the custodian step (the unmasked histogram lives only in a
temporary directory), fill the blinded bin with the simulated expectation at zero variance, and save figures only
after `core.blinding.check_figure` finds nothing in the blinded range. The example tests rerun each pipeline with a
synthetic sentinel (987654.321) in the blinded bins: all outputs byte-identical to the normal run,
`audit_blinded_outputs.py scan` with the sealed sentinel histogram passes, a planted sentinel fails. Sealing the real
blinded counts instead gives false hits in the AMS example (a two-digit count equal to an unrelated public count, and
a three-digit printed factor within rounding of a sealed ratio), so the sentinel form is the test. Specs validate
strictly with their profiles and review as `acceptable-with-open-inputs`; gate-verdict snapshot unchanged (no
`--write`). Downstream: the published-comparison record copied from Path B is regenerated (mu 0.9977 +- 0.0221, chi2
7.98/9); theory-comparison and detector-resolution rerun byte-identically. The synthetic-collider profile dataset
record `datasets/synthetic-path-b-dsigma.json` is a contracts-1.0.0 snapshot and was not regenerated.

`tools/run_all_checks.py` with the host CLIs and the E2 venv at `a1801ce`: 21 pass, 0 fail; unit tests 2,804 run,
0 failures, 58 skipped (212 modules); synthetic-collider profile suite 12 tests. `core/` and `contracts/` not touched.

## 0.6.17 release check (2026-10-13, E2)

Version 0.6.17: physics-ml enforcement and ML artifact semantics (contracts 2.5.0, PRs #59 and #60); partition engine
retries bounded across runs and merge from canonical chunk files only (hep-computing audit F01 and F02, PR #61, 15
regression tests, 14 of which fail on the previous code); faster CI (PR #62: two balanced unit shards plus one job for
the profile suites and static checks per Python version, slowest modules first, parallel optional and AMS-optional runs;
PR CI wall time 17.5 min to about 7 min with every job passing). For the release the examples were rerun with the E2
venv: the plugin version string changed, `local-partition/output/results.json` gained the new state fields
(`attempts_since_reset`, `signatures`) and the ML example's statistical result records the new hash of its ML artifact
(unfolding-coverage and end-to-end-sample not rerun, as in earlier releases); the published-likelihood benchmark's two
artifacts were rewritten with the new plugin version. The contract fixtures keep the plugin version they were made
with. `tools/run_all_checks.py` with the host CLIs (Claude Code 2.1.296, codex-cli 0.160.0) and the E2 venv: 20 of 20
checks pass; 2,478 unit tests in 187 modules, 0 failures, 55 skipped. The CI lint job (ruff 0.16.10, mypy 2.4.0) passed
on PRs #61 and #62. Release manifest `release-manifests/0.6.17.json`.

## 0.6.16 release check (2026-10-13, E2)

Version 0.6.16 (detector-response front-end electronics and signal processing, PR #57: a new reference, the
standard-library script `frontend_response.py` with 23 tests whose values were checked by numerical integration and
Monte Carlo, ten corrected electronics statements, a dead-time and live-time section, and nine Crossref-checked
electronics citations; no contracts change, no `core/` or `contracts/` change). The package's NumPy verification scripts
were rerun with the E2 venv and reproduce the reference values. `frontend_response.py` is covered by the strict-JSON
edge-case test of all nine subcommands. For the release the examples were rerun with the E2 venv and only the plugin
version string changed (26 files, 26 lines; unfolding-coverage not rerun, as in earlier releases); the
published-likelihood benchmark's two artifacts were rewritten with the new plugin version. `tools/run_all_checks.py`
with the host CLIs and the E2 venv: 20 of 20 checks pass; 2,317 unit tests, 0 failures, 55 skipped. The CI lint job
(ruff 0.16.10, mypy 2.4.0) passed on PR #57. The README size statement now reads about 1200 files,
12.1 MB (the packaging check flagged 10.7 MB as drift). Release manifest `release-manifests/0.6.16.json`.

## 0.6.15 release check (2026-10-13, E2)

Version 0.6.15 (detector-response review fixes WP1–WP5, PR #54; hep-computing SKILL.md interpreter order, PR #55;
skill READMEs and SKILL.md trims; contracts 2.4.0 with the response semantic rules, minor: 2.3.0 artifacts keep their
outcome and get the rules with `--strict`, no new capability). The contracts bump and the two examples' response
artifacts (`explicit_bins`, `intended_use: unfolding`) were regenerated in PR #54; for the release the examples were
rerun with the E2 venv and only the plugin version string changed (26 files, 26 lines; unfolding-coverage not rerun,
as in earlier releases); the published-likelihood benchmark's two artifacts were rewritten with the new plugin version.
ruff 0.16.10 and mypy 2.4.0 with the CI pins pass on `core/` and `contracts/`. `tools/run_all_checks.py` with the host
CLIs and the E2 venv: 20 of 20 checks pass; 2,294 unit tests, 0 failures, 55 skipped. Release manifest
`release-manifests/0.6.15.json`.

## 0.6.14 release check (2026-10-13, E2)

Version 0.6.14 (lint-clean contracts after the 0.6.13 tag failed the GitHub lint job; no behavior change). ruff
0.16.10 and mypy 2.4.0 with the CI pins pass on `core/` and `contracts/` (54 files); ruff with the project
configuration also passes on the research-communication scripts. Examples rerun with the E2 venv: only the plugin
version string changed (28 files, 28 lines). `tools/run_all_checks.py` with the host CLIs and the E2 venv: 20 of 20
checks pass; 2,236 unit tests, 0 failures, 55 skipped. Release manifest `release-manifests/0.6.14.json`.

## 0.6.13 release check (2026-10-12, E2)

Version 0.6.13 (research-communication reliability plan T0–T11 and its review fixes; contracts 2.3.0 with the
capability `communication:traceability-v1`, additive). Examples rerun with the E2 venv: only the plugin and contracts
version strings changed (28 files, 78 lines; the unfolding-coverage example was not rerun, as in earlier releases);
the published-likelihood benchmark's two artifacts were rewritten with the new plugin version as in 0.6.11 and
0.6.12. `contracts/migrate_statistical_result.py` writes the current contracts version. `tools/run_all_checks.py`
with the host CLIs and the E2 venv: 20 of 20 checks pass; 2,236 unit tests, 0 failures, 55 skipped. Release manifest
`release-manifests/0.6.13.json`.

## 0.6.12 release check (2026-10-12, E2)

Version 0.6.12 (hep-statistics follow-ups, #51: T27 coverage at 1,500 toys, the Combine release gate, the campaigns
job). Examples rerun with the E2 venv: only the plugin version string changed (the unfolding-coverage float drift was
reverted as in earlier releases). `tools/run_all_checks.py` with the host CLIs: 20 of 20 checks pass; 2,008 unit tests,
0 failures, 55 skipped. Release manifest `release-manifests/0.6.12.json`.

## 0.6.11 release check (2026-10-12, E2)

Version 0.6.11 (the hep-statistics audit, contracts 2.2.0). Examples rerun with the E2 venv: only the plugin version
string changed (the unfolding-coverage float drift of about 1e-13 was reverted as in earlier releases); the
published-likelihood benchmark's artifacts were rewritten from the stored results with the new version. `tools/run_all_checks.py`
with the host CLIs: 20 of 20 checks pass; 2,007 unit tests, 0 failures, 55 skipped. Release manifest
`release-manifests/0.6.11.json`.

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
interpreter and the SymPy version in a `computational-run` (`tools`, `environment`) instead. Closed 2026-10-13 (THEORY-AUDIT, THY-WP2.1): the
extension has an optional `computational_run_ref` naming that `computational-run`.

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

## CMP-REMEDIATION (2026-10-13, E2 + Homebrew ROOT 6.38.04, version 0.6.17 + unreleased): hep-computing remediation

Branch `fix/hep-computing-remediation` from `c1d375c`, one commit per task CMP-01…CMP-28 (CMP-27 deferred by Q1)
plus CMP-ANA-P2-7 (the `core/blinding` part of the hep-analysis audit item P2-7). Every bug-fix test was run against
an export of `c1d375c` and failed there: `tests/core/test_partition_robustness.py` (8 of 8),
`tests/core/test_blinding_regressions.py` (8 of 10; the two that pass on `c1d375c` check that nonzero blinded values
stay sealed), `test_local_partition.py` (2 new), `test_compare_histograms.py` (10 of 10), the CMP-07 class of
`test_environment_manifest.py` (7 of 7), `test_root_cpp_scripts.py` (5 of 6 new; the CMake build test passes on `c1d375c` too), `test_lint_task.py` (3 of 4 new),
`tests/skills/test_cli_robustness.py` contract class (22 cases) and `tests/adapters/test_batch_cmp_regressions.py`
(5 of 6).
`tools/run_all_checks.py` with `~/.venvs/hep-research-e2` (Python 3.13.2) at `1606c04`: 20 pass, 0 fail, 0 skip;
2535 unit tests in 191 modules, 0 failures, 56 skipped (55 at 0.6.17; the new skip is
`test_root_integration.test_viewers_json_mode`, PyROOT). PyROOT-dependent tests run with
`HEP_ROOT_PYTHON=/opt/homebrew/bin/python3.14` (Homebrew ROOT 6.38.04): `test_root_integration` 8 and
`tests.adapters.test_root_cpp_assets` 5, all pass; the generated `new_root_cpp_project.sh` project and the
`cmake-and-build.md` snippet configured and built with CMake 4.3.2; the parallel `check_root_cpp_env.sh` test ran.
uproot 5.7.6 ran the uproot backend of `compare_root_histograms.py`. CI lint pins in a scratch venv: `ruff 0.16.10`
`check core contracts` clean, `mypy 2.4.0` clean (55 files). Reference snippets were run where the tool exists:
SymPy 1.14.0 and SciPy 1.18.1 (every number in `symbolic-and-numerical-computation.md`), PyROOT 6.38.04
(`python-hep-coding-patterns.md`, the RDataFrame/RNTuple features, `GetNRuns`, `TTreePerfStats`, the directory
"leak"), Bash 3.2.57 (`set -u` empty arrays, SIGTERM forwarding). Not run here: gdb, valgrind, perf, py-spy, the
Linux LeakSanitizer, real Slurm or HTCondor (fakes only), and a live routing run (three static cases added). The
`lint_task.py` run on the task order reports one error by design: it cites `references/product-framing.md`, which
CMP-26 moved to `docs/dev/engineering/`. Contracts unchanged (2.5.0). Software checks only; no scientific validity.
## STATISTICS-HARDENING (2026-10-13, CI lock env: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, pyhf 0.7.6, ArviZ 0.23.4; version 0.6.17 + unreleased, contracts 2.6.0)

hep-statistics hardening order STH (audit on 0.6.15, re-checked on `c1d375c`). Contract checks establish consistency
only, not statistical validity.

| Item | Result | Evidence |
|---|---|---|
| Adversarial gate inputs (17 statistical-result mutations, 5 Bayesian, comparison-gate relabel, edge overwrite and unit factors -3/0/NaN/inf, duplicate combination id, unequal envelope rows, scaled covariance, contour domain, result_artifact refusals) | 36 failing (sub)tests on `c1d375c` (only the unmutated-bases control passed); all green on the branch, each with its own reason code | `tests/contracts/test_gate_adversarial.py` |
| Verdict snapshot of the 90 committed artifacts of `c1d375c` | default and strict validator outcomes unchanged for every artifact; gate verdicts changed only through `gate.not_observed_data` (Q3): J9 passed -> failed, 11 synthetic/asimov examples and fixtures unresolved -> failed; the sbottom benchmark stays unresolved; 19 new 2.6.0 fixtures added | `tests/contracts/test_gate_verdict_snapshot.py`, `tests/contracts/gate_verdicts.json` |
| Contracts 2.6.0 back-compatibility and migration | each new code fires natively at 2.6.0; a 2.5.0 copy of every new fixture keeps ok without `--strict` and reports the code with it; the migrator refuses each of the 8 new error fixtures and moves a 2.5.0 artifact to 2.6.0 without inventing a seed | `tests/contracts/test_statistical_semantics.py` (`Contracts26Hardening`) |
| Covariance scale invariance | the rho/sigma matrix (correlation eigenvalue -0.80) fails with `not_psd` at sigma ratios 1, 1e4 and 1e12; diag(1e-20, 1e20) passes with rank 2, condition 1 | `tests/core/test_stats_covariance.py` |
| Two-POI contour, 3-bin audit input | exit 0, status ok, 72 points on the level of an independent Poisson deviance within 1e-4; out-of-domain probes counted, not failed | `tests/core/test_stats_two_poi.py` |

| Unbinned fit at three scales (same shape on [0, 5], [0, 500], [10000, 10500]) | 300 toys each (HEP_SLOW_TESTS=1, 95 s): no failed fit, every pull width in [0.9, 1.1]; before, the last two failed every toy | `tests/adapters/test_unbinned_fit.py` |
| Break position of a broken power law (x_b = 10, gamma 2.7 -> 2.4, 20 points, 2% + 1% correlated errors) | 500 toys (HEP_SLOW_TESTS=1, 342 s): bias of ln x_b within 0.2 sigma (0.11 in a 300-toy probe), toy-calibrated 68.27% interval coverage within 0.03 (0.693 in the probe); no-break control: chi2(1) reference rejects > 10% at 5% | `tests/skills/hep_statistics/test_covariance_fit.py` |
| Ratio covariance at 1e5-1e7 counts; D'Agostini data unfolding; asymptotic shape-limit vs pyhf; multi-bin q0 | within 5% per element of 200k toys; 15 x 15 variances within 10% of 1500 toys; CLs limit within 1% of pyhf 0.7.6 at 100 bins x 1000 events; q0 equal to `look_elsewhere.py local` to 1e-6 | `test_stats_statistical_toys.py`, `test_stats_unfolding_outer.py`, `test_backend_likelihood_equivalence.py`, `test_stats_likelihood_limits.py` |
| Expected bands; MC ranges; shape-limit at n = b = 0; model card with pyhf | `cls-limit --n 2 --b 3.7` -2 sigma 2.996 (was 3.5595); `profile-cls --n 0 --b 3` range contains 3.00; n = b = 0 status ok, toy CLs range contains 2.996; a validation region moved mu_hat 0.70 -> -3.94 before the fix, none after | `test_stats_poisson.py`, `test_stats_toy_ensemble.py`, `test_stats_likelihood_limits.py`, `test_sr_cr_model_card.py` |

| Reference sources (STH-T2.4, T4.1-T4.5) | 27 sources added to `docs/evidence/statistics/sources.json` (S15-S41): 15 arXiv abstract pages and, at page level, the iminuit reference and the HistFactory `Measurement.h` header read on 2026-10-13 (two Combine documentation pages update S14); 10 recorded metadata-only and cited only for what their titles and venues establish; the ledger check passes strictly | `tests/tools/test_statistics_evidence.py`, `tests/core/test_evidence_ledger.py` |

Provenance moved here from `core-stats-guide.md` (STH-T2.3): the "Validation tools outside `core/stats`" table there
(result_artifact, covariance_fit, sweighted_fit, bayes_calibration, the EXPERIMENTAL eft_scan, discrete_profile,
global_significance, pcl_efficiency_ratio and ratio_estimation, the pyhf backend comparison and model card, the
sbottom benchmark) was added by the hep-statistics audit of 2026-10-12 (T01-T30, PRs #49, #51, #53).

## INTEGRATION (2026-10-13, E2 + Homebrew ROOT 6.38.04, PR #64): fixes found by CI on the merged audits

| Finding | Regression test | Before | After |
|---|---|---|---|
| `check_systematic_variations.py` combined per-sample variances as independent for same-event variations (ROOT fixture `jes_Up`/`jes_Down` = nominal events scaled by 1.03/0.97) | `tests/skills/hep_analysis/test_systematic_stat_test.py` `SameEventVariationTests` (4), `tests/skills/hep_computing/test_root_integration.py::test_check_systematic_variations` | up/down `effect: none`, "neither variation changes this histogram" | no test without `--independent` or difference variances, effect from tolerance (`mixed`); `up_diff_sumw2` detects the shift |
| `SrCrModelCard` lost its pyhf skip (STH-T3.12 inserted a class under the decorator) | `tests/adapters/test_sr_cr_model_card.py` with pyhf hidden | 3 errors without pyhf | 6 skipped without pyhf, all pass with it |
| Broken-power-law covariance comparison at `places=9` | `tests/skills/hep_analysis/test_broken_power_law.py` | fails on Python 3.11 (difference 1.8e-9) | relative 1e-6; measured 1.0e-8 (3.12, 3.13), 9.0e-8 (3.11) |
| `check_root_cpp_env.sh`: `ROOT_VERSION=$(root --version \| head -n 1)` under `set -euo pipefail` (CI: `test_env_check_parallel_runs_and_cleanup` failed in `rootproject/root:6.38.00-ubuntu25.10`, passed on macOS) | `tests/skills/hep_computing/test_root_cpp_scripts.py` `test_env_check_survives_a_failing_root_version`, `test_env_check_reports_a_failing_root_config` | fake `root --version` exiting 1: exit 1, no output; failing `root-config`: exit 1, no JSON | `status: ok` with the first version line; `status: failed`, exit 1 |

## STATISTICS-FOLLOWUPS (2026-10-13, E2: Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1; version 0.6.17 + unreleased, contracts 2.6.0)

STH Q8 (one broken-power-law parametrization). Synthetic input: 20 points over x = 3-300, truth
`[ln 5, 2.7, 2.4, ln 30]`, covariance 2% uncorrelated + 1% fully correlated; smooth case s = 0.3.

| Check | Before | After | Test |
|---|---|---|---|
| Model value, same parameters, `cr_spectrum_powerlaw_fit.broken_log_flux` vs `covariance_fit.bpl_log` | sharp identical (1e-15); smooth differs by the constant 2^-((g2-g1) s) = 1/1.0644 (the hep-analysis form had no 1/2) | identical (covariance_fit bit-identical to the core helper; hep-analysis within 1e-12, the exp/log round trip of x_b) | `tests/core/test_stats_broken_power_law.py` `test_identical_model_values` |
| Smooth fit, Asimov points: A from both tools | 5.199 (hep-analysis, labelled `normalization_at_break` but `F(x_b) 2^((g2-g1)s)`) vs 5.195 | both recover the truth: hep-analysis within 1e-6, covariance_fit within 1e-3 sigma; index and break uncertainties agree to 1e-3 relative | `test_asimov_both_recover_the_truth` |
| Fitted parameters on the same toys (40 seeded per model, measured; 8 per model in the test) | not comparable for A (smooth) | largest difference 0.17 sigma (sharp, covariance_fit started at the hep-analysis fit) and 0.11 sigma (smooth); test tolerance 0.3 sigma. The tools minimize different chi2 (ln F with the linearized covariance vs F) | `test_toys_agree_within_stated_tolerance` |
| Sharp break, covariance_fit started at the truth instead | — | 2 of 40 toys reach another local minimum (differences up to 1.4 sigma; one has the lower flux chi2 at the hep-analysis point): the sharp-break chi2 is kinked in ln x_b, so the guide says to start from a profiled break | measured, not a test |
| Found, not changed: `covariance_fit.py fit` on the same spectrum over x = 1-1000 (flux spans 8 decades) | refused: "singular beyond the 0 declared constraint(s)", eigenvalue ratio 4e-16 in absolute units | open: the subspace singularity test is not on the correlation scale (unlike `_linalg.py`); the comparison uses x = 3-300 | — |

hep-statistics SKILL.md headroom: `tools/measure_entrypoints.py` 8178 -> 7653 B (budget 8192, target <= 7700);
core-stats-guide.md 16651 -> 16944 B (test limit 17000); `tools/check_routing_static.py` ok (197 cases, no failures);
`test_core_stats_guide`, `test_skill_resources`, `test_ml_inference_routing`, `test_check_ownership` pass.

## 0.7.0 release check (2026-10-13, E2)

Version 0.7.0: the hep-analysis, hep-computing, hep-statistics and hep-theory audits (PR #64; contracts 2.6.0 with three
rule families, each native from 2.6.0 and applied to older artifacts only with `--strict`) and their follow-ups (PR #65:
background estimates and masked outputs in the two flagship examples, one broken-power-law convention in
`core/stats/broken_power_law.py`, hep-statistics `SKILL.md` 7,653 B, live routing 51/52 then `j05-turn-fit` 3/3 after
giving it inputs). For the release the examples were rerun with the E2 venv: only the plugin version string changed,
and the ML example's statistical result records the new hash of its ML artifact (unfolding-coverage and
end-to-end-sample not rerun, as in earlier releases); the published-likelihood benchmark's two artifacts were rewritten
with the new plugin version, and `tests/contracts/test_gate_adversarial.py` now ignores that string when it compares its
inlined copy. The companion ams02-research requires `hep-research >=0.4.0`; its profile range is `contracts >=2.0,<3.0` in 1.4.9
and `contracts >=2.0` from 1.4.10 (ams02-research PR #26), and its checker reports 0.7.0 `compatible`. `tools/run_all_checks.py` with the host CLIs (Claude Code 2.1.296,
codex-cli 0.160.0) and the E2 venv: 21 of 21 checks pass; 2,814 unit tests in 213 modules, 0 failures, 58 skipped. CI on
main at `3c348fa` passed every job, including the optional ROOT and Python-extras jobs. Release manifest
`release-manifests/0.7.0.json`.

## 0.7.1 release check (2026-10-13, E2)

Version 0.7.1: the R4 correction key for bounded recipes (PR #67: `recipe_version` 1.1.0 with optional `effect_keys`,
upstream key fields, repeat / distinct / undetermined rule; `tests/contracts/test_recipe_semantics.py` 43 tests, the
review-driven ones failing on the first commit and passing after the fix; the approved `differential_flux.json` table
unchanged) and the skill texts aligned with R4 §9 scientific-validation guidance (PR #68: 14 skill files; hep-statistics
and hep-computing `SKILL.md` 7,677 and 7,984 B of 8,192). Contracts stay 2.6.0. For the release the examples were rerun
with the E2 venv: only the plugin version string changed, and the ML example's statistical result records the new hash
of its ML artifact (unfolding-coverage and end-to-end-sample not rerun, as in earlier releases); the
published-likelihood benchmark's two artifacts were rewritten with the new plugin version. The companion
ams02-research (main `dc0e674`, 1.4.10) checker reports 0.7.1 `compatible` (requires `>=0.4.0`). `tools/run_all_checks.py`
with the host CLIs (Claude Code 2.1.296, codex-cli 0.160.0) and the E2 venv: 21 of 21 checks pass; 2,830 unit tests in
213 modules, 0 failures, 58 skipped. CI passed on both merged PRs (#67 every job; #68 every required job). Release
manifest `release-manifests/0.7.1.json`.

## AGENTIC-COMPLETION release A (2026-10-14, E2: Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1; version 0.7.1 + unreleased, contracts 2.7.0)

Plan "Complete the agentic architecture inside hep-research", packages P2, P3, P1 and P7 for them (decisions DP-1 to
DP-6 as recommended). Synthetic data and sentinels only; custodian-written files are modeled by evaluating them for
another account, because a test cannot create files owned by another identity without privileges.

| Package | Evidence |
|---|---|
| P2 revocation log, head, reverse index, source checks | `tests/contracts/test_revocation.py` (43 tests): every corruption refused and unanswerable; recipe, release, source and attestation revocation reach every dependent with no byte change; own, writable, replaceable (including an account-owned read-only directory), hard-linked and non-regular inputs refused; `dependencies.py`, `release_manifest.py`, `attestation.py` read the same verified log |
| P3 exposure and decision lineage | `tests/contracts/test_lineage.py` (17 tests): ordering and append-only checks, `exposed` from signal-region entries and `unknown` from missing records, decision binding through appends, producers and the release check use one derivation, new capabilities refused by an older reader |
| P1 protected-use mode (C07 plugin half) | `tests/contracts/test_protected_entry_points.py` (16 tests): 17 command lines and 31 lower-level functions under 9 failure modes with a valid control (only formal use refused there), revoked inputs (digest, canonical digest, path), unknown capabilities, qualification revocation and binding, the review regressions, nothing changing outside protected mode, core rules equal to the schemas on every single-field mutation |
| P7 texts | `tools/check_instruction_text.py` 17 rules (P01-P03 new), 0 findings; reference inventory regenerated; SKILL.md files unchanged |

Contracts bump to 2.7.0 (decided 2026-10-14): `CONTRACTS_VERSION` and `vocab/core.json`; the current fixtures
(`measurement_v26`, `ml_artifact_v25`, `statres_v26`, `statres_v26_bayesian`) and the measurement-spec template
restamped, `tests/contracts/make_fixtures.py` rerun (version lines only changed), the examples rerun with the E2 venv
(only version stamps changed, and the ML example's recorded digest of its own ML artifact); `unfolding-coverage` kept at
2.6.0 (its rerun drifts at 1e-14) and the published-likelihood benchmark not rerun (network), both valid under a 2.7
reader.

An independent review of the first implementation reported eight findings; seven were fixed with regression tests
(`ReviewFindingTests`), and the eighth (custodian tools are not guarded) is a stated limit. `tools/run_all_checks.py`
with the E2 venv: 21 of 21 checks pass; 2,917 unit tests in 216 modules, 0 failures, 58 skipped. ruff 0.16.10 and
mypy 2.4.0 clean on `core` and `contracts`. Not run: CI, the host CLIs' live sessions, any carry-over.

## 0.8.0 release check (2026-10-14, E2)

Version 0.8.0 is release A of the plan "Complete the agentic architecture inside hep-research": the release-manifest
custodian options and the architecture and deployment documents (PR #70), the hash-chained revocation log and reverse
index (PR #71), exposure and decision lineage (PR #72), protected-use mode at the formal-use entry points and contracts
2.7.0 (PR #73); evidence in "AGENTIC-COMPLETION release A" above. Project config schema 1.2.0. For the release the
examples were rerun with the E2 venv: only the plugin version string changed, and the ML example's statistical result
records the new hash of its ML artifact (unfolding-coverage and end-to-end-sample not rerun, as in earlier releases);
the published-likelihood benchmark's two artifacts were rewritten with the new plugin version. The companion
ams02-research (main `dc0e674`, 1.4.10) checker reports 0.8.0 `compatible` (requires `>=0.4.0`; contracts `>=2.0`).
`tools/run_all_checks.py` with the host CLIs (Claude Code 2.1.296, codex-cli 0.160.0) and the E2 venv: 21 of 21 checks
pass; 2,918 unit tests in 216 modules, 0 failures, 58 skipped. CI passed every job on PRs #70-#73 (Python 3.11, 3.12,
3.13; ruff, mypy; optional ROOT and columnar). Release manifest `release-manifests/0.8.0.json`.

## AGENTIC-COMPLETION release B (2026-10-14, E2: Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1; version 0.8.0 + unreleased, contracts 2.7.0)

Packages P5.2, P5.1, P5.3, P4, P5.4 and P6.1 with P7 for them, stacked on release A. Synthetic data and sentinels only.

| Package | Evidence |
|---|---|
| P5.2 analysis-level bundles | `tests/contracts/test_permits.py` `AnalysisBundleTests`: a changed spec, recipe, calibration, environment lock or plugin release changes the digest; reformatting JSON does not; duplicates, missing roles, escapes, links, bad refs and duplicate keys refused; attestations take the bundle as subject |
| P5.1, P5.3 permits and recipe-use review | `PermitTests`, `FormalEntryPointTests`, `ReviewFindingTests`: every permit refusal code; budget counted in the nonce ledger; changed bundle invalidates; review out of scope, not accepted, missing roles, inactive or revoked refuse; HEPData export runs in protected mode only with a valid permit (command line and `build_tables`); directory and empty inputs, S3 execution binding, unattested recipes |
| P4 transforms, preparation, residual checks | `tests/core/test_blinding_residual.py` (20 tests), `tests/contracts/test_release_prepare.py` (7 tests): every mode's draft passes `release_manifest.py` with every custodian option; a leaked sealed value fails; the §6.2 attacks are detected, refused or stated; the quantization check has 0 false positives in 5,000 random five-value sets and detects scaled counts up to 10^5 |
| P5.4 tool contracts | `tests/contracts/test_tool_contract.py` `ShippedScopeTests`: four contracts pass with the help check (per subcommand for the output audit); both scopes pass; every recipe step's tool is scoped |
| P6.1 scan interface | `tests/contracts/test_scan_verdict.py`: closed verdict; budget in candidate values from the service's recount; refusal past the limit is sticky |

An independent review of the first release-B implementation reported findings in permits, release preparation, the
scan budget, residual checks and malformed-input handling; all were fixed with regression tests. The package grew to
15.0 MB (about 1430 files): the README size statement is updated. `tools/run_all_checks.py` with the E2 venv: 21 of 21
checks pass; 2,966 unit tests in 220 modules, 0 failures, 58 skipped. ruff 0.16.10 and mypy 2.4.0 clean. Not run: CI,
live sessions, any carry-over.


## PROTECTED-BATCH (2026-10-14, E2: Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1; version 0.9.0 + unreleased, contracts 2.7.0)

Review of deferred task P6.2 (trusted submitter, Q-07): Q-07 stays deferred; the agent-side refusal it called for is
built for protected projects now, switched by protected mode (DP-2) instead of the campaign config. Synthetic data only.

| Check | Evidence |
|---|---|
| Refused in protected mode before any scheduler call | `tests/core/test_partition_protected_batch.py` `ProtectedProjectRefuses`: real `submit`, `resubmit`, `cancel` and `confirm`, `abandon`, `reset`, `clear-orphans` refused with `protected.batch_needs_trusted_submitter`; the scripted executor records no call; campaign-config keys (`submitter`, `protected`) do not switch it off; with broken protected inputs the input refusal comes first |
| Dry runs and observation unchanged | same file: dry-run `submit` and `cancel`, `poll`, `report` run in protected mode |
| Outside protected mode unchanged | `OutsideProtectedModeNothingChanges`: a real submit reaches the executor; no guard refusal |
| Bypass suite | `tests/contracts/test_protected_entry_points.py`: five more batch entry points; every broken-input mode refused at each; `REFUSED_IN_CONTROL` lists the entry points refused with valid inputs |

Not changed: polling (`status`, `watch`) and `reconcile` still call the scheduler client from the agent side when one is
reachable; on the qualified host the launcher's sandbox and egress rules block it. The trusted submitter itself (T3.5)
and P6.2's request/sync interface stay unbuilt.

## 0.9.0 release check (2026-10-14, E2)

Version 0.9.0 is release B of the plan "Complete the agentic architecture inside hep-research" (PR #74): analysis-level
bundles, formal-use permits and the recipe-use review, input-blinding transforms with release preparation and residual
checks, tool contracts and scopes, the scan-service interface, and `--strict-versions`; evidence in
"AGENTIC-COMPLETION release B" above. Contracts stay 2.7.0. For the release the examples were rerun with the E2 venv:
only the plugin version string changed, and the ML example's statistical result records the new hash of its ML
artifact (unfolding-coverage and end-to-end-sample not rerun, as in earlier releases); the published-likelihood
benchmark's two artifacts were rewritten with the new plugin version. The companion ams02-research (main `dc0e674`,
1.4.10) checker reports 0.9.0 `compatible`. `tools/run_all_checks.py` with the host CLIs (Claude Code 2.1.296,
codex-cli 0.160.0) and the E2 venv: 21 of 21 checks pass; 2,971 unit tests in 221 modules, 0 failures, 58 skipped. CI
passed every job on PR #74 (Python 3.11, 3.12, 3.13; ruff, mypy; optional ROOT and columnar). On the release PR #76
three jobs failed on one clock-dependent test (`test_scan_verdict`: the verdict's real timestamp 03:47 contained the
sealed digits it asserts are absent); the test now uses a fixed time. Release manifest `release-manifests/0.9.0.json`.

## 0.10.0 release check (2026-10-14, E2 and the CI lock)

Version 0.10.0 carries the detector-response, physics-ml and research-communication audits (PR #81; evidence in
PHYSICS-ML-AUDIT, DETECTOR-RESPONSE-AUDIT, RC-AUDIT-2 and THREE-AUDITS-LIVE-ROUTING below) and moves the contracts to
2.8.0. For the release the examples were rerun with the E2 venv: only the plugin version string changed, and the ML
example's statistical result records the new hash of its ML artifact (unfolding-coverage rerun and its 1e-13 float
drift reverted; end-to-end-sample not rerun, as in earlier releases); the published-likelihood benchmark's two
artifacts were rewritten with the new plugin version. The companion ams02-research (main `dc0e674`, 1.4.10) checker
reports 0.10.0 `compatible` (it requires hep-research >=0.4.0 and contracts >=2.0, so no companion change).
`tools/run_all_checks.py` with the host CLIs (Claude Code 2.1.299, codex-cli 0.160.0): with the E2 venv (PyTorch) 21 of
21 checks pass, 3,162 unit tests in 237 modules, 0 failures, 58 skipped; with a venv built from
`requirements-ci.lock` (no PyTorch, NumPy 2.4.6) 21 of 21 pass, 3,162 tests, 0 failures, 167 skipped. ruff 0.16.10 and
mypy 2.4.0 clean on `core/` and `contracts/`. CI passed every job on PR #81 after three test fixes for environments the
local gate had not covered (no-PyTorch exit code, the J9 framework version, and cross-platform float differences in
the J9 calibration fit). Release manifest `release-manifests/0.10.0.json`.

## 0.10.1 release check (2026-10-15, E2 and the CI lock)

Version 0.10.1 is a patch release: the follow-ups to the check of the three audit orders on 0.10.0 (PR #84; evidence
in DETECTOR-RESPONSE-AUDIT, PHYSICS-ML-AUDIT and RC-AUDIT-2 below) and the `tools/run_all_checks.py` timeout fix
(PR #83). Contracts stay 2.8.0. For the release the examples were rerun with the E2 venv: only the plugin version
string changed, and the ML example's statistical result records the new hash of its ML artifact (unfolding-coverage
rerun and its 1e-13 float drift reverted; end-to-end-sample not rerun, as in earlier releases); the published-likelihood
benchmark's two artifacts were rewritten with the new plugin version. The companion ams02-research (main `dc0e674`,
1.4.10) checker reports 0.10.1 `compatible` (it requires hep-research >=0.4.0 and contracts >=2.0, so no companion
change). `tools/run_all_checks.py` (on the release tree before the manifest and documentation edits) with the host CLIs (Claude Code 2.1.300, codex-cli 0.160.0): with the E2 venv
(PyTorch) 21 of 21 checks pass, 3,179 unit tests in 237 modules, 0 failures, 59 skipped; with a venv built from
`requirements-ci.lock` (no PyTorch, NumPy 2.4.6) 21 of 21 pass, 3,179 tests, 0 failures, 167 skipped. ruff 0.16.10 and
mypy 2.4.0 clean on `core/` and `contracts/`. CI passed every job on PR #83 and PR #84. After the manifest was written
`check_packaging.py` found the README size statement out of its 10% margin (15.1 MB stated, 16.8 MB measured); it now
says about 1560 files, 16.8 MB; `check_packaging.py` and `tests/tools` (80 tests) then pass. A local rerun of the
gate's check part (`--part checks`, E2) after these documentation edits gave 19 of 20 passing and `ams_optional` timed
out after 600 s (it passed in both full runs above; the machine was under background load). A standalone rerun of
`check_ams_optional.py` was stopped and no further local gate was run at the user's request; GitHub CI on the release
PR is the gate for the final tree. Release manifest `release-manifests/0.10.1.json`.

## PHYSICS-ML-AUDIT (2026-10-14, E2: Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1, PyTorch 2.14.1 CPU; version 0.9.0 + unreleased, contracts 2.8.0)

Physics-ml remediation brief (findings ML-C01…C28, ML-K01…K16, ML-R01…R36), executed on branches fix/physics-ml-p0,
-p1, -p2 from main 84202aa. Every row's test failed on 84202aa and passes on the branch. Synthetic data only.

| Item | Before (84202aa) | After | Evidence |
|---|---|---|---|
| A1 NaN timestamp | `passed`, exit 0 | exit 2 naming id `a` | `tests/skills/physics_ml/test_audit_split_tools.py` |
| A2 unknown or single `temporal_order` names | `passed`, `timestamps_checked: true` | exit 2 | same |
| A3 date `2024-1-10` in temporal mode | sorted as text into test; check `passed` | exit 2 naming row `a1`; ISO date lands in train | same |
| A4 group values 1, 1.0, "1" | three groups, split across train/val/test | one group `1` | same |
| A5 same-sample isotonic calibration | writer exit 0, validator no finding (ECE 6.5e-17) | writer exit 1, `ml.calibration_on_fit_sample` | `test_audit_calibration_identity.py` |
| A6 gate on relabelled J9 (a) no ML input, (b) domain shift failed, (c) overlap not run | `passed` x3 | (a) failed `stats.observable_source_unlinked`; (b), (c) failed `gate.ml_input_invalid` (the relabelled ml-artifact is itself refused: 'observed' without an observed input); with an observed input, (b) and (c) unresolved `gate.ml_input_unresolved` | `tests/contracts/test_ml_provenance_gate.py` |
| K06 `dependencies.py` on J9 | exit 1 (raw `work/` files as inputs) | exit 0; a source's unresolved findings propagate | same |
| K02 downstream "ROC AUC = 0.93", ["weighted AUC","accuracy"], bare pass | no finding | errors (native 2.8.0; under `--strict` for older artifacts) | `tests/contracts/test_ml_mutation_probe.py` |
| Appendix B mutation probe | 50 of 53 rows silent | 1 of 53 silent (M47, by design: listed in the test) | same |
| J9 domain shift (Q3) | shift measured, not carried | `theta_pt_miss_scale` in the fit: mu 1.30738 +0.280857/-0.260727 -> 1.33104 +0.293293/-0.277051; Asimov +0.258174/-0.237781 -> +0.271493/-0.256756; toy pull mean -0.0547 -> -0.0325, width 0.984 -> 1.028, 68% coverage 0.693 -> 0.660 (1000 toys) | `examples/ml-classifier-to-inference/`; two runs byte-identical |
| J9 calibration (Q5) | ECE 0.0159 -> 0.0176 recorded as a probability calibration | output_semantics score, outcome no-op-within-floor (floor 0.0158) | `tests/examples/test_ml_classifier_to_inference.py` |
| Inference domain check, d = 32, n = 600 | about 10% of fresh in-distribution rows flagged (box) | near the nominal 1% | `test_audit_domain_method.py` |
| Grouped domain calibration, 300 design points x 10 replicas | reported 4%, measured 100% flagged | reported 3-10%, measured 5-11% (nominal 5%) | same |
| `compare_model_runs.py` false improvements at 3/5/9 seeds | 26%/15%/11% (first pass, 3/5/10) | 5.7%/5.3%/5.1% (1500 null comparisons each) | `test_audit_small_corrections.py` |
| References size | 257,182 B | 179,135 B (38 files; re-measured 2026-10-15 on 41871d1 with `cat skills/physics-ml/references/*.md \| wc -c`; the 179,004 B first recorded here predates `7a4f739`, +131 B) | `docs/reference-inventory.json` |
| physics-ml tests (E2, torch) | 269 run, 6 skipped | 322 run, 6 skipped (4 GPU, 2 only-without-torch) | `python -m unittest discover -s tests/skills/physics_ml -t .` |

Live routing: see THREE-AUDITS-LIVE-ROUTING below (45/45 physics-ml cases). Not verified here: GPU behaviour of the changed assets; statements marked `unverified` in the references (numerical inversion,
the in-situ term as the usual dominant one, square-root LR scaling for Adam, TMVA option strings, two-dimensional DDT
maps, JetClass split, spurion attribution, journal details of Drnevich et al. and the CaloChallenge report, the
OmniLearn name). The domain false-positive and calibration checks are statistical tests with fixed seeds.

## DETECTOR-RESPONSE-AUDIT (2026-10-14, E2, version 0.9.0 + unreleased, contracts 2.8.0)

detector-response audit DR-WP1 to DR-WP4 on branch `fix/detector-response-audit` (rebased on PML-X0, contracts 2.8.0).
Live routing for the SKILL.md change (workflow step 5; description unchanged): 23/24 detector-response cases, see
THREE-AUDITS-LIVE-ROUTING below; `tools/check_routing_static.py` passes.

| Item | Before (`84202aa`) | After | Evidence |
|---|---|---|---|
| Crafted broken responses refused by `validate.py` (30 cases, also `--strict`) | 5 of 30 | 28 of 30; cases 20 and 24 pass with warnings by design; the same artifacts stamped 2.6.0/2.7.0 keep their default outcome (5 fail) | `tests/contracts/test_response_contract.py` (ResponseHardeningTests), fixtures `invalid/response_2_8/`, `warning/response_2_8/` |
| He4 Cherenkov photons, p = 40 GeV/c, n = 1.05, L = 2 cm, N0 = 100/cm | 17.02 (sigma_theta 1.212 mrad) | 68.08 (0.606 mrad) | `CherenkovChargeTests` |
| Gaisser-Hillas, X_max = 1e20, lambda = 60 | no result within 10 s | FWHM 1.824036e11 in 0.03 s (Gaussian limit 1.8240358e11) | `GaisserHillasBracketingTests` |
| Calorimeter constant term, 2000 toys, 2% scatter, true c = 0.0070 | unit weights: c^2 < 0 in 26% of fits, mean c 0.0083 in the rest | 1/r^4 weights: mean c 0.0070, sd 0.00013, no failed fit | `evidence/calo_toys_after.txt` of the task (script in the task folder), `CalorimeterFitDefaultTests` |
| Audit regression suite (appendix, 30 methods) | 29 failing (32 failures, 15 errors with subtests) | 30 passing, plus 7 follow-up tests (N-*) | `tests/skills/detector_response/test_detector_response_audit.py` |
| Shipped responses, `response_adapter.py --validate` | 3 of 3 fail (`matrix_ref` unreadable) | 5 of 5 pass (AMS: one per species and period) | `tests/examples/test_ams_flux_ratio.py`, `test_collider_angular.py` |
| Proton crossover rigidity, prototype stack (B 0.5 T, L 0.5 m, 300 um, 4 layers, x/X0 0.3) | 1.3087 GV (beta = 1 assumed) | 1.534037 GV with beta(R) | `MultipleScatteringBetaTests` |
| CLI errors | argparse text on stderr, empty stdout, no status label | JSON with `status: failed` and `error_kind` at exit 2; `status` echoed by all eight scripts | `UniformErrorTests`, `StatusLabelTests` |

`tools/run_all_checks.py --out <scratch> --jobs 6` with the E2 venv: all checks pass; unit tests 3,037 run, 0
failures, 58 skipped (224 modules); profile tests pass (AMS-02 238). Lint with the CI pins (ruff 0.16.10, mypy 2.4.0)
on `core/` and `contracts/`: clean. SKILL.md 7,568 B.

Sources opened on 2026-10-14 for the physics edits: PDG RPP 2024 Passage of particles through matter (rev. March
2025), Particle detectors at accelerators, Cosmic rays; PDG Atomic and Nuclear Properties (water, liquid); CMS muon
performance JINST 7 (2012) P10002; ATLAS luminosity EPJC 76 (2016) 653; CERN Open Data CMS pileup simulation;
DAMPE Sci. Adv. 5 (2019) eaax3793; ECSS-E-ST-10-04C annex B.8 (SPENVIS); R. Nolty, arXiv:hep-ex/0201015; Auger
PoS(ICRC2019)231; WHISP summary PoS(ICRC2021)473; LHAASO arXiv:2505.14447; arXiv:1703.06298; SIDC and the Royal
Observatory of Belgium (cycle 25).

**Not verified here (text left unchanged, appendix rows deferred):** AB-A29 (books beyond PDG), A32, A38; AB-F23;
the AB-F10 `f_em` power law and 95% longitudinal-containment rule; the rest of the C-E15 mode table; D-F5 (Heitler
splitting length), D-F8, D-F18. The appendix's dE/dx resolution formula gave the sample length in m; PDG eq. 35.17
implies cm (applied as cm). Rows done in the follow-up below are no longer listed here.

**Gaisser-Hillas acceptance value:** the work order called 6271594.24 (case `--n-max 1 --x-max 5e6 --x0 -60 --lambda-param 2e5`)
the "FWHM"; it is the falling half-maximum depth. The FWHM for that case is 2358463.01; the script reports both edges
and the FWHM correctly, only the order's label was wrong.

### DETECTOR-RESPONSE follow-ups to the 0.10.0 check (2026-10-15, E2, branch `fix/dr-followups` from `41871d1`)

| Item | After | Evidence |
|---|---|---|
| F-DR1 front-end tool contract | `contracts/tool_contracts/frontend_response.json`, ten operations (one per subcommand) checked against each subcommand's help; the tool's top-level usage is one line so the first-line subcommand reader sees all ten | `tests/contracts/test_tool_contract.py` `FrontendResponseContractTests` (4 tests; fail on `41871d1`) |
| F-DR2 AB-F2, AB-F18, AB-F22 tail | noble-liquid W values, pulse shape, VUV and TPB (PDG RPP 2025 sec. 36); Gluckstern validity N >= 10, N = 3 coefficient 9.8, projected L, X0 as a length (PDG sec. 35.12, arithmetic); `(heuristic)` | reference text; `tools/reference_inventory.py --check` |
| F-DR3 D-F15 remainder | muon detectors, radio detection (PDG sec. 36.3.3), wide-field gamma-ray arrays (HAWC arXiv:1701.01778, LHAASO-KM2A arXiv:2010.06205, in an example block) in `ground-based-detection-arrays.md` | reference text; `tools/check_layering.py` |
| F-DR4 C-U4 | one `Check:` line per section in the triggers, physics-objects and event-reconstruction references | reference text |
| F-DR5 deferred rows | done: AB-A10, A11, A12, A19, A36, AB-F3, F13 (with N9), F15, C-E8, C-E14, C-Sec2, D-F13, D-F14, D-F22, D-N3, D-N4; partly: AB-F10, C-E15; still deferred: AB-F23 (PDG gives the silicon rise only as a figure) | sources per row in the task folder's FOLLOWUP-0.10.0.md |
| F-DR6 NV-1 | the scattering term's `beta` power (first power) agrees with PDG RPP 2025 eq. 35.70; stated in `tracking-and-vertexing.md` | reference text |
| F-DR7 IGRF dipole | `geomagnetic_cutoff.py` default 8.05e25 G cm^3 unchanged: it is the IGRF-14 1955 dipole (8.0507e25 from the degree-1 coefficients) and gives C = 59.6 GV; the 2025 dipole is 7.69e25 (4.5% lower cutoffs); one docstring statement, both scripts' help name the epoch | `tests/skills/hep_analysis/test_astroparticle.py` `GeomagneticDipoleDefaultTests` (docstring test fails on `41871d1`) |

Sources opened on 2026-10-15: PDG RPP 2025 reviews 34 (Passage of particles, rev. Aug. 2023), 35 (Particle detectors at
accelerators, rev. 2025) and 36 (Non-accelerator detectors, rev. Oct. 2025) as PDF from pdg.lbl.gov/2025/reviews/; NIST
PSTAR page; Geant4 Book for Application Developers ("Production Threshold versus Tracking Cut", "Physics Processes:
Production Cuts") and Physics Reference Manual ("Mean Energy Loss"); IGRF-14 coefficients
(ngdc.noaa.gov/IAGA/vmod/coeffs/igrf14coeffs.txt); arXiv 0901.2882, 1902.08960, 1809.04346, 1102.0132, 0901.4118,
2212.09379, 1403.2286, 1511.00463, 2110.15051, 2111.10299, 1604.03637, 1701.01778, 2010.06205; INSPIRE record of Riegler,
NIM A535 (2004) 287; LST collaboration news of 2026-06-13 and IAC news of 2025-07-11. Tests run on the branch:
`tests.contracts.test_tool_contract` (30), `tests/skills/detector_response` (200), `tests/skills/hep_analysis` (235),
`tests/tools` (80), `tests.skills.test_cli_robustness`, `tests.skills.test_skill_resources`, AMS-02 profile (239): all
pass; `check_routing_static`, `check_ownership`, `check_layering`, `measure_entrypoints`, `reference_inventory --check`,
`build_stanzas --check`: pass. The full gate is run at integration.

## RC-AUDIT-2 (2026-10-14, E2: Python 3.13.2; version 0.9.0 + unreleased, contracts 2.8.0)

Second research-communication audit (work order RC, tasks A1-E3), branch `fix/research-communication-audit`, rebased
on PML-X0 (`2b439e7`, contracts 2.8.0). Every task has a regression test that failed on `84202aa` and passes here,
unless the row says it is text only.

| Item | Result | Evidence |
|---|---|---|
| A1 brace-less `\input` | followed; unresolvable one gives exit 3 (was exit 0, coverage complete) | `ReviewFixes2Includes` |
| A2 value vs passage | `1.09` and `1.0` against a `1.02` passage fail in `check_communication` and `audit_claims` (were exit 0) | `ReviewFixes2ValueVsPassage`, updated `test_communication_audit` |
| A3 adaptation numbers | `1.09.`, CJK-adjacent, signed, exponent, grouped numbers tokenized; 9.99 drafts fail in en and zh-Hant | `ReviewFixes2Numbers`, `ReviewFixes2Adaptation` |
| A4 citation parsing | seven cases (capitalised, multicite, nested, `%` in `\url`, `.bib` depth, stripped blocks, crossref) | `ReviewFixes2Citations` |
| A5, A6, A15 rounding | no-rule non-rounding is an error; half-up default with `:half-even`; malformed rules and NaN/inf are findings | `ReviewFixes2Rounding` |
| A7, A9, A18 | `--bbl` outside root exit 2; 20,000 lines 10.3 s before, well under 1 s after; strict unused entries unresolved when coverage incomplete | `ReviewFixes2ManuscriptBounds` |
| A8 locators | nested-brace titles, `\pm`/`±`, fenced code | `ReviewFixes2Locators` |
| A10, A13, A17 Traditional Chinese | Chinese twins give the English findings; labels as words; declared terms mask parts; same-line early use | `ReviewFixes2Chinese*`, `ReviewFixes2LabelWords`, `ReviewFixes2TerminologyEdges` |
| A11 TikZ | compiled (LuaHBTeX 1.24, TeX Live 2026); `\undefinedmacro` exit 1; no TeX + `--require-render` exit 3; no block exit 2; all shipped TikZ compiles under `HEP_SLOW_TESTS=1` | `ReviewFixes2Diagrams`, `RealBundle` |
| A12, A14, A16, A19 | empty records and unmapped added claims flagged; bad `--today` and aliased output refused; README qualified | `ReviewFixes2RevisionImpact`, `ReviewFixes2SmallClis` |
| B1-B13 text | Mermaid duplicate removed (5 blocks render instead of 10); SKILL.md read levels equal the vocabulary; other items text only | `ReviewFixes2SkillText`, `test_reference_links` |
| B7 ledger | `ams02:C185` (absence claim, metadata-only, 2026-10-14) | profile `test_evidence_ledger.py` |
| C1-C11 content | three new references, examples `hep/09`-`hep/11` render; `flux-measurement` policy and result type (contracts 2.8.0, add-only) | `ReviewFixes2FluxPolicy`, `FluxMeasurementResultTypeTests`, `test_reporting_completeness` |
| D1-D7 usability | quick-questions block (SKILL.md 8098 B, description 950 unchanged); Done-when in all 56 references; links resolve | `test_reference_links`, `measure_entrypoints.py` |
| A2b and review follow-ups (fresh-subagent checks) | fresh rerun of A1-A4 and B2 passed; it found that display `1.0` still matched a passage holding `Figure 1` (`Decimal("1.0") == Decimal("1")`): now the passage must show at least the declared digits (caption flagged, 3 of 3 occurrences); fresh source review: 0 high, 2 medium (F1 Type 1 fonts for ICML, F2 venue-facts home), 12 low, all fixed or marked unverified; LaTeX-set matplotlib text gives Type 1 fonts (matplotlib 3.11.2, checked 2026-10-14) | `ReviewFixes2Numbers.test_contains_value_needs_the_displayed_precision`, `ReviewFixes2ValueVsPassage`; `research-communication-audit/evidence/fresh-repro-rerun.md`, `fresh-source-review.md` (task folder, outside the plugin) |
| C5b, C7b follow-ups (0.10.0 check, 2026-10-15) | Springer Nature AI-use row rewritten from the public page (no login; the old URL redirects to a login): risk levels, "Clearly describe use and confirm author accountability", AI as author not permitted, "AI Declaration" plus caption or legend for AI visuals, no "Methods" wording; ADS `citations(query)`/`references(query)` stated from the ADS help source file, unverified mark removed. Text only, no regression test | `submission-and-peer-review.md` AI-use table, `literature-lookup-recipes.md` ADS section; sources accessed 2026-10-15, read level `page` |
| Gate | `run_all_checks.py --no-cli` exit 0 (3026 tests, 0 failures, 58 skipped across the plugin; CLI checks skipped by `--no-cli`); `check_relocation.py` pass; ruff 0.16.10 and mypy 2.4.0 clean on `core/` and `contracts/`; worked example byte-identical on two runs | gate log of 2026-10-14 |

**Live routing.** The trigger-first description (RC-D1) was applied after maintainer approval; 20/20
research-communication cases pass live, see THREE-AUDITS-LIVE-ROUTING below. **Not verified here.** NSTC form names
come from university guides, not an NSTC page. The two fresh-reviewer reruns asked by the work order were run by the lead session (all high
reproductions pass; source-review findings F1-F14 and the A2b precision gap fixed).

### Export-route checks (moved from `legends-panels-and-export.md`, RC-D4)

Recorded when the export table was written (before 2026-10-14) and kept here, not in the reference: The Graphviz, `rsvg-convert`, and `mmdc` rows were run in this bundle's validation; the TikZ standalone compile (Tectonic; fonts embedded, `pdffonts`), `pdftoppm -r 300 -png` and `pdftocairo -svg` were run, and the `subcaption` `figure*` snippet compiled under `twocolumn` article with Tectonic (two panels (a)/(b) plus caption on a float page). `dvisvgm` 3.6.1 was run: on Tectonic's `.xdv` it warns "86 PDF specials ignored" and the SVG has the text overlapping with the boxes and arrow missing, so do not use that route; `dvisvgm --pdf` refuses to run with Ghostscript 10.08 and needs `mutool` or Ghostscript < 10.01 ; with `mutool` (`mupdf-tools`) installed, `dvisvgm --pdf` rendered the boxes, arrow and labels correctly, with text kept as `<text>` elements. With math labels and bold, italic, mono and small-caps text, plain `dvisvgm --pdf` rendered in rsvg with a fallback sans font (detached radical, lost bold and italic, overlapping words) while `--no-fonts` and `pdftocairo -svg` matched the PDF; `pdftoppm` matched too. Check any SVG export in the target viewer.

## LITERATURE-LOOKUP (2026-10-15, E2: Python 3.13.2, OpenSSL 3.6.4, macOS 26.5 arm64; version 0.10.1 + unreleased, branch `wp5-literature-lookup` from `f2039c7`)

Work order ams02-skill-upgrade WP5 (decision D5: optional adapter). New `adapters/literature-lookup` 0.1.0
(`assets/literature_lookup.py`, standard library only, owned by research-communication, required by no skill).
Network approved by the maintainer for this WP: fixture recording and one live smoke. Endpoints:
`https://inspirehep.net/api/literature` (search and record), `https://export.arxiv.org/api/query` (`id_list`);
`https://api.adsabs.harvard.edu/v1/search/query` not contacted (no `ADS_API_TOKEN` or `ADS_TOKEN` set). User-Agent
`hep-research-literature-lookup/0.1.0 (hep-research plugin; https://github.com/hchouTW/hep-research)`. Requests
02:31-02:37 UTC: 12 in total (INSPIRE 5, arXiv 7, ADS 0), no automatic retry.

| Item | Result | Evidence |
|---|---|---|
| Recording (`--record`) of public identifiers | INSPIRE: `arxiv:1007.1727` found (record 860907, texkey `Cowan:2010js`), `arxiv:2501.99999` total 0, record 860907 found, record 999999999 HTTP 404. arXiv: `1007.1727` found, latest `v3`; one request timed out after 20 s; `2501.99999` answered HTTP 429 "Rate exceeded." four times (02:31:49, 02:32:31, 02:34:44, 02:36:45) while `1007.1727` resolved at 02:32:11 and 02:36:38, so no arXiv not-found response was recorded | `tests/adapters/fixtures/literature_lookup/recorded/`, `rate-limit/arxiv-2501.99999-429.json` |
| Constructed fixtures (marked `synthetic` in the file; the record says so in its notes) | an INSPIRE HTTP 429 with `Retry-After: 5` (from the documented limit, not provoked) and an ADS search response in the documented layout | `rate-limit/inspire-arxiv-2501.99999-429.json`, `constructed/ads-arxiv-1007.1727.json` |
| Offline tests (no network: `urlopen` patched to fail) | 20 pass, 1 skipped (live): found in both sources; retrieval time = recording time in replay; erratum skipped in the journal reference; version mismatch (`v1` cited, `v3` latest, exit 3), latest version (exit 0), nonexistent `v9`; not found (INSPIRE total 0 and HTTP 404, exit 1); rate limit (real arXiv 429, constructed INSPIRE 429, one request per source, exit 3); ADS without a token makes no request (`not-verified`), the token goes only into the Authorization header and never into the output or a recorded file, a rejected token is `not-verified`; bad identifier and missing replay directory exit 2 | `python -m unittest tests.adapters.test_literature_lookup` |
| Live smoke (`HEP_LIVE_LOOKUP_TEST=1`, 02:36:36 UTC) | pass: `arxiv:1007.1727v1` found in INSPIRE (HTTP 200, record 860907, retrieved 02:36:36Z) and arXiv (HTTP 200, retrieved 02:36:38Z, latest `v3`, version mismatch reported); 2 requests, 3.0 s | `LiveSmokeTests` |
| CLI robustness, declarations | `--help` under `-I`, missing replay directory a short error; adapter status `demonstrated-on-synthetic-data` (ADS), INSPIRE and arXiv `tested-in-declared-environment` | `tests/skills/test_cli_robustness.py`, `tests/adapters/test_adapter_declarations.py` |

**Not verified here.** No ADS request was made (no token); the ADS parser and the token handling ran on a constructed
response only. An arXiv not-found reply (an empty feed or an error entry) was not observed. The INSPIRE 429 was not
provoked.

## CR-PROPAGATION-DRAGON2-UNITS (2026-10-16, E2: macOS 26.5 arm64, Python 3.13.2, numpy 2.5.3, scipy 1.18.1; main `31ee717` + branch `fix-dragon2-per-nucleon`)

Check of the two failing WP13 limit-benchmark checks (C1 absolute B/C, C2 D0/L degeneracy). Local DRAGON2 runs only, no
network. Diagnostic binary: the same commit rebuilt with a two-line gas patch (`dragon2-gas-fixed-r.patch`: with
`DRAGON_GAS_FIXED_R` set, the BronfFerr H2 and HI densities are evaluated at that radius at every R); without the
variable it reproduced X1 byte for byte.

| Item | Result | Evidence |
|---|---|---|
| Cause of C1 | a unit error in the converter, not physics. DRAGON2's ASCII output is its internal density per total kinetic energy: `dragon.cc` writes `GetFluxAtSunPosition`, which computes `weight = A` and returns the density without it, and `particle.cc` scales the spallation source by `A_parent / A_daughter` "to convert between kinetic energy per nucleon ... to momentum". Read as per E/n, B/C was 12/11 too high and the closed form's O/C input 12/16 too low (together about 1.19, the "unattributed" 15-17%) | `dragon2_to_prediction.py` `mass_number`, `ratio`; `Converter.test_ratio_is_per_nucleon` (failed before the fix) |
| C1, C3 recomputed (same runs, same tolerances; plan amendment "C1-absolute") | C1: DRAGON2 / closed form 1.094-1.120 (tolerance 0.30) **pass**; 0.956-0.979 after dividing out DRAGON2's helium production term (the low-energy deficit fits its helium term on destruction, not ported). C3: -0.4727 against -0.4783 **pass**. C4 unchanged (a common factor) | `benchmark-results.json`; `LimitBenchmark` |
| C2 attribution (unchanged verdict: **fail**) | radial gas varied, boundary 20 kpc: no effect at L = 4 (gas fixed at 8.3 kpc changes C1 by < 0.1%). Boundary and sources at 60 kpc, real gas: X3/X1 0.928-0.948 (was 0.82-0.85). Boundary at 60 kpc and gas uniform in R: X2/X1 0.989-0.996, X3/X1 0.982-0.994, and DRAGON2 / closed form after the helium production term 0.972-0.998 (L = 2), 0.976-1.009 (L = 4), 0.960-1.001 (L = 8). The D0/L degeneracy and the absolute B/C of the thin-disc model are reached in DRAGON2's 1D limit; the C2 failure is the 2D geometry (boundary 11.7 kpc from the observer) and gas structure the closed form does not have | runs D_X1_R60, D_X3_R60 (released binary), D_X1_R60_UG, D_X2_R60_UG, D_X3_R60_UG (patched binary, version string names the patch); `Diagnostics` in `tests/adapters/test_cr_propagation.py` |

**Not verified here.** DRAGON2's inelastic cross sections and the helium term on destruction are not ported, so the
1D-limit agreement is within 5%, not exact. The patched binary is a diagnostic, not DRAGON2 as released.

## CR-PROPAGATION-DRAGON2 (2026-10-15, E2: macOS 26.5 arm64, Python 3.13.2, numpy 2.5.3, scipy 1.18.1; version 0.11.0 + unreleased, branch `wp13-cr-propagation` from `d95fd7c`)

Work order ams02-wp13-wp16 WP13 (decision D4: DRAGON2 first; download and build approved). New `adapters/cr-propagation`
0.1.0 (`assets/dragon2_run.py`, `assets/dragon2_to_prediction.py`; owner hep-computing; required by no skill). Network:
one `git clone` of https://github.com/cosmicrays/DRAGON2-Beta_version (HEAD `cd588707fe03c76f19bda1b8092e136dcbe3fe90`,
2021-09-30), nothing else. Built in a user work directory, no system-wide installation.

| Item | Result | Evidence |
|---|---|---|
| Build | attempt 1 (`autoconf` on the shipped `aclocal.m4`): `make` failed with "libtool: Version mismatch error. This is libtool 2.4.2, but the definition of this LT_INIT comes from libtool 2.4.6" (the repository's `ltmain.sh` and `m4/ltversion.m4` disagree; automake is not installed, so `startMAC.sh` cannot run); attempt 2 (`glibtoolize -c -f`, libtool 2.6.2, then `autoconf` 2.72, restoring `missing` and `depcomp`): configure and `make install` exit 0 with Homebrew GCC 15.2.0, GSL 2.8, CFITSIO 4.6.4, serial (configure adds OpenMP only for a compiler named exactly `g++`) | `tests/adapters/fixtures/cr_propagation/dragon2-build.computational-run.json` (commands, tool versions, binary and library SHA-256) |
| Runs | nine runs, each a `computational-run` (spec, XML and table SHA-256, command, environment manifest from `environment_manifest.py`, exit 0, output SHA-256): 2D, Rmax 20 kpc, dz 0.02 kpc, BronfFerr gas, sources uniform in R with abs(z) <= 0.2 kpc, convection, reacceleration, energy losses and decay off (the `Flags` block takes child elements; attributes are ignored and leave every flag on), D = D0 beta (R / 1 GV)^0.5, production table replaced by the ILLUSTRATIVE set A (C12 -> B11 70 mb, O16 -> B11 35 mb); 60-372 s each (up to three in parallel) | `tests/adapters/fixtures/cr_propagation/{specs,runs,outputs}/` |
| Limit benchmark (criteria committed in `limit-benchmark-plan.json` before any comparison) | C3 slope of B/C over 100-1000 GeV/n: -0.4727 against -0.4785 (tolerance 0.05) **pass**; C1 absolute B/C over 10-1000 GeV/n: DRAGON2 / closed form 1.316-1.344 (tolerance 0.30) **fail**: DRAGON2's helium target (He/H = 0.11 with its `He_to_H_CS_ratio`, ported in the test) gives a factor 1.143, the residual 1.151-1.175 is not isolated (Inferred: 2D gas rising inwards of the observer and sources uniform in R); C2 D0/L degeneracy: L = 2 within 1.8%, L = 8 15-18% low (tolerance 0.10) **fail**: with the radial boundary at 30 kpc instead of 20 the L = 8 run is 6-7% low, so the boundary is the main cause; C4 tabulated-grid fit (amended before it ran: five D0 nodes instead of three): D0 = 3.664e28 for a truth of 3.6e28 (|ln(D0/truth)| = 0.018 with a fit error of 0.024 in ln D0, tolerance 0.05 on |ln(D0/truth)|) **pass**, all five nodes gated | `tests/adapters/fixtures/cr_propagation/benchmark-results.json`; `python -m unittest tests.adapters.test_cr_propagation` (17 tests, 1 skipped live) |
| C4 as first declared | three D0 nodes: `covariance_fit.py` raised `CovFitError` "point [64.96] lies outside the grid [65.17 - 65.98]" before any fit value: near an upper edge its Fisher-matrix step takes a one-sided second-order difference at 2h without checking that 2h stays in the grid (h = one cell). Not changed here (hep-statistics); fixed afterwards by PR #114 (steps cut at the grid edges), after which the three-node grid fits: D0 = 3.664e28, |ln(D0/truth)| = 0.018 | `limit-benchmark-plan.json` amendment |
| Live rerun | `HEP_DRAGON2_LIVE_TEST=1` (with `HEP_DRAGON2_BIN`, `HEP_DRAGON2_DATA`): run X1 rerun through `dragon2_run.py` equals the recorded output (relative 1e-6), 78.5 s | `LiveDragon2` in the same module |
| Converter and gate | every run converts to a `prediction` (representation grid, node in `parameter_point`, B/C averaged uniformly in ln(E/n) over 8 bins from 10 to 1000 GeV/n) that validates with the `theory:cr-secondary-ratio` vocabulary and passes the gate against a measurement on the same observable, fails it in other bins; edges outside the run's range, unknown columns, a missing level and an output not listed in the run record exit 2 | `Converter` tests; `tests/skills/test_cli_robustness.py` |

**Not verified here.** GALPROP and USINE were not obtained. DRAGON2's helium target and inelastic cross sections cannot
be replaced without changing its code, so no run is a like-for-like reproduction of the closed form; the C1 residual is
not attributed by a run (superseded 2026-10-16: a converter unit error, see CR-PROPAGATION-DRAGON2-UNITS). No DRAGON2 default cross-section set, reacceleration, convection, energy losses or decay were
exercised; no OpenMP build; no fit to real data.

## CRDB-ADAPTER (2026-10-15, E2: Python 3.13.2, OpenSSL 3.6.4, macOS 26.5 arm64; version 0.10.1 + unreleased, branch `wp9-crdb-adapter` from `f2039c7`)

Work order ams02-skill-upgrade WP9 (decision D2: owner hep-theory). New `adapters/crdb` 0.1.0 (`assets/crdb_query.py`,
standard library only, required by no skill), promoted from the ams-02 profile's `scripts/crdb_query.py`, which is
removed; the profile lists `adapter:crdb` as optional and passes `--exp-dates AMS` explicitly. Network approved by the
maintainer for recording: 6 requests to `lpsc.in2p3.fr` between 03:03:51 and 03:04:36 UTC, no retry (`--retries 0`),
User-Agent `hep-research-crdb-adapter/0.1.0 (hep-research plugin; https://github.com/hchouTW/hep-research; ...)`.

| Item | Result | Evidence |
|---|---|---|
| CRDB version | the welcome page (`welcome.php`, 03:03:59 UTC) states "Current version: V4.2 (September 2026)", code last change 13/10/2026, 143 experiments from 614 publications (4429 sub-experiments, 452456 data points); the export header names the 2014, 2020 and 2023 CRDB papers and no release, so the version is passed with `--crdb-version` | `tests/adapters/fixtures/crdb/recording.json` |
| Live `fetch` runs of the adapter (recorded as fixtures) | all HTTP 200, redirected to `_dialog_result.php` with the same query: a ratio on kinetic energy per nucleon (10 rows, two experiments: the filter is not an exact-name match), a rigidity flux (6 rows, two sub-experiments with different data-taking ranges), a positron flux sent as `num=e%2B` (8 rows), a filter matching nothing (header only, exit 1, `no-data-rows`); `energy_start` and `energy_stop` restricted the bins | `tests/adapters/fixtures/crdb/*.csv` and their `.meta.json` sidecars |
| Offline tests (urlopen patched to fail) | 24 pass: no default experiment filter (`url` and `fetch` without `--exp-dates` or `--all-experiments` exit 2, no request; an empty filter exits 2; `build_params` has no default; a source check fails if a default is added, mutation-checked); every summarized row and sub-experiment group is `secondary: true`; the sidecar holds request (parameters, URL, User-Agent), UTC retrieval time, CRDB version, export date and SHA-256 of the saved file; replay writes the recorded bytes and the rebuilt URLs equal the live ones; blocks never retried, one retry of a transient error, size cap, https only; no experiment name in the adapter's code or declaration | `python -m unittest tests.adapters.test_crdb_query` |
| Declarations, CLI robustness, profile | `test_adapter_declarations` 2 pass (status `tested-in-declared-environment`, matrix row matches); `test_cli_robustness` 6 pass with the new inventory entry; ams-02 profile tests 213 pass after removing `test_crdb_query.py` | `tests/adapters/test_adapter_declarations.py`, `tests/skills/test_cli_robustness.py`, `profiles/experiments/ams-02/tests/` |

**Not verified here.** No CRDB value was compared with a paper or a HEPData record; the matching rule of `exp_dates`
is not documented by this run (observed once); HTTP 429, 5xx and a timeout were not provoked (synthetic responses only);
the `crdb` Python library was not used.

## THREE-AUDITS-LIVE-ROUTING (2026-10-14, Claude Code 2.1.299, claude-sonnet-5-5)

Paid live routing run `20261014T113734Z-claude-claude-sonnet-5-5` (`evals/routing/results/`, outside the plugin) of
the 89 routing cases whose expected owner is detector-response, physics-ml or research-communication (92 prompt
turns), plugin from `--plugin-dir` on `integrate/three-audits` at `71470cb` (the summary's `plugin_commit` field
records the eval checkout, `84202aa`), isolation `setting-sources`, `--jobs 4`, max 6 turns, $0.50 per case.

| Expected owner | Cases | Strict pass |
|---|---|---|
| detector-response | 24 | 23 |
| physics-ml | 45 | 45 |
| research-communication | 20 | 20 |
| **all** | **89** | **88** (en 48/49, zh-Hant 34/34, ja, de, zh-Hans 2/2 each) |

Cost $6.80 ($0.077 per case). The one miss, `t19-turns-1`, is the second turn of a handoff (unfold with the
response just built) answered without a skill; the 2.1.293 baseline and the 2026-10-12 rerun missed it too. No
contamination, 0 loading violations. Not run: the cases of the other four skills, Codex.


## WP6-QUICK-ROUTING (2026-10-15, Claude Code 2.1.300, claude-sonnet-5-5, plugin 0.10.1 at `f2039c7`)

Re-measurement of the research-communication "Quick questions" block (RC-D1) on the released 0.10.1 tree, paid
runs approved by the maintainer (order TASK-ams02-skill-upgrade, WP6). Both runs live outside the plugin
(`evals/`).

| Run | Cases | Result | Cost |
|---|---|---|---|
| routing `20261015T022722Z-claude-claude-sonnet-5-5` | 31: every research-communication case (20), every `quick` case, and the three quick cases missed on 2026-10-12 (`st-sensitivity-1`, `co-companion-ws-1`, `rc-t4-code-1`) | 29/31 strict; research-communication 20/20; misses `t19-quick-3` (detector-response, no skill; missed in the 2.1.293 baseline, passed on 2026-10-12) and `co-companion-ws-1` (quick code question, no skill, as on 2026-10-12) | $2.04 |
| communication eval `live-20261015-0227-sonnet` | 11 of 11 | 0 pass, 6 fail, 1 critical-fail, 4 unjudged (semantic judgments not yet recorded). Routing: 5 cases answered without a plugin skill (`rc-eval-04` abstract draft, `-06` Traditional Chinese status, `-09` Traditional Chinese terminology, `-10` public summary, `-11` injection), against 4 on 2026-10-13. The critical failure (`rc-eval-07`) is a scorer artifact: it counts the plugin reference path `references/evidence-linked-writing.md`, which the answer names as its method, as a fabricated identifier | $0.69 |

Conclusion: quick verification questions route (20/20); short drafting, terminology and summary requests with
fixtures still skip the skill. That decision is taken before `SKILL.md` is read, from the description alone, so
the WP6 remedy (reordering the body, description byte-identical) cannot change it; `SKILL.md` was not changed.
Open: a description change (needs approval and a routing rerun) or a scorer fix for plugin reference paths.

## PY313-FLOOR (2026-10-15, Python 3.13.2 conda-forge on macOS 26.5 arm64 with the CI lock; CI ubuntu-latest Python 3.13.16 and the ROOT 6.38.00 container's Python 3.13.7)

Validation-first migration to Python 3.13 as the minimum. Gate 1 (trial `b8aa140` on base `21506da`; CI on the PR
merge `2675f22`, run 38689427002, draft PR #97 not for merging) passed before any CI or documentation change:

| Obligation | Result |
|---|---|
| Floor tests (3.11/3.12 rejected from every candidate source, 3.13 selected in order, all-old fails, lower `--min-python` refused, stricter kept; metadata, Ruff and mypy targets) | 20/20 on Python 3.13.2; 8 failed first on the old code |
| Full suite and checks, clean venv from `requirements-ci.lock` (`pip check` clean) | 3259 tests, 0 failures, 168 skipped, 242 modules; the same modules and skip reasons as the clean baseline at `21506da` (3250 tests; +9 floor tests) |
| CI on 3.13: units 1/2, 2/2, static and profiles, AMS optional | pass, skip counts equal to the baseline run 38687423557 |
| Backends on 3.13 (CI): ROOT container (3.13.7), pyhf, uproot + awkward, coffea columnar, hepdata, PyTorch CPU; stats-backends with pyhf 0.7.6 and ArviZ 0.23.4 required | all pass, skip counts equal to the baseline; required backends 153 tests, no problems |
| Tool-contract scopes, routing-harness and replay-scorer tests, release manifests, Ruff 0.16.10 (`py313`), mypy 2.4.0 (`3.13`) | pass |
| Slow tier once (`HEP_SLOW_TESTS=1`) | 241 of 242 modules pass; `tests.examples.test_stats_benchmarks` timed out at 600 s under 6 parallel jobs, then passed alone (525 s; the baseline takes 544 s): a load effect near the module limit, the same on the baseline |
| CI on 3.11 / 3.12 (the trial still ran them) | 6 failures each, all in `test_find_python` (the calling interpreter is below the floor): the intended withdrawal |

Every backend already ran on Python 3.13 at the baseline, so none blocks the floor. The repository has no rulesets or
branch protection on `main`, so removing the 3.11/3.12 jobs needs no required-status change. **Not verified here:**
Python 3.14 (installable, not tested); Windows; the slow tier in CI (the weekly `latest` job last failed on
2026-10-12 for an older runner timeout).

## WP12-LIVE-ROUTING (2026-10-15, Claude Code 2.1.300, claude-sonnet-5-5, rename tree of PR #102)

Paid live routing run approved for WP12 (`evals/routing/results/20261015T083754Z-claude-claude-sonnet-5-5.json`, outside
the plugin): 229/241 cases ($18.55). On the 150 cases of the 2.1.293 baseline: 143/150, the same total; per case,
`rc-t3-neg` and `j12` passed before and missed now, `rc-t3-4` and `t19-quick-6` missed before and pass now.
Diagnosis by repeats: `rc-t3-neg` (a short Traditional Chinese Feynman-diagram question) loads no skill on main with
the old names too (0/3), so it is not a rename effect; `j12` ("Set up a lattice QCD global analysis of form factors")
went to hep-statistics in 3 of 9 runs on the rename tree against 11 of 11 with the old names. Fix: hep-theory's
out-of-v1 example reads "lattice QCD and its global analyses, EFT global fits" (description 1,005 characters); after it
`j12` passed 9/9 and the 34 hep-theory cases plus the propagation and out-of-v1 cases passed 36/39 (misses
`rc-t3-neg`, `wp11-bound-dm-1`, `wp11-bound-dm-2`). Cases added since the baseline: 86/91. **Not verified here:** a
full 241-case rerun after the fix; Codex.

## CR-BENCHMARKS-B1-B2 (2026-10-15, E2: Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1, SymPy 1.14.0, macOS 26.5 arm64)

Open questions B1 and B2 of the ams02-skill-upgrade order; network approved for reading papers, tables only (no value
read off a figure). Every source, version, table and read level is in the profiles' `evidence/` ledgers (access date
2026-10-15).

| Question | Source | Result |
|---|---|---|
| B2, `theory:cr-secondary-antiprotons` | di Mauro, Donato, Goudelis, Serpico, PRD 90 (2014) 085017, arXiv:1408.0288v3, **Table VI** (pp-induced source term at T = 5, 10, 100, 500, 1000 GeV), read in full (`crpb:S02`, claims `crpb:C07`-`C08`); proton flux input from arXiv:1402.0321v2 Sec. 2.3, running text, not a table (`crpb:S05`, `crpb:C09`) | `scripts/published_benchmark.py` implements the paper's closed forms (Eqs. (2), (11)-(13), (A15), (B1)-(B2); Tables III-V, VII) for the benchmark only. Tolerance per entry: the paper's own Table VI 1-sigma error. **12 of 15** entries of the three closed-form columns reproduced (within 2.5% at 5 and 10 GeV, within 6.5% up to 500 GeV); documented, not reproduced: Eq. (11) at 1000 GeV (+9.3% against 6.9%, cause not identified), Eq. (13) at 500 and 1000 GeV (depends on the unstated upper limit of the projectile-energy integral), and the spline, Tan & Ng and Duperray et al. columns. `tests/test_published_benchmark.py` (12 tests, including a wrong flux index that must fail). Korsmeier et al. 2018 (1802.03030v2) and Winkler 2017 (1701.04866v1) tabulate no source term (`crpb:C11`) |
| B1, `theory:cr-secondary-ratio` | Jones et al. 2001 (astro-ph/0007293v1), Genolini et al. 2015 (1504.03134v2) and 2019 (1904.08917v2), Schroer, Evoli, Blasi 2025 (2502.15115v1): table and figure captions of the arXiv sources; Webber, Villa 2016 (1606.03031v1): PDF text searched for tables | **stays open**: the tables hold fit parameters or cross sections and B/C appears in figures only, so there is no tabulated B/C or grammage for inputs the profile can reproduce. Record and reasons in `benchmarks/external-benchmark-search.json` (claim `crsr:C06`, `tests/test_external_benchmark_search.py`) |

Profile tests: `cr-secondary-antiprotons` 48 pass, `cr-secondary-ratio` 41 pass (`python -m unittest discover -s tests
-t tests`); both ledgers pass `core/evidence/ledger.py --strict`. **Not verified here:** the journal supplemental
cross-section tables of 1802.03030; the Tan & Ng and Duperray et al. columns of Table VI; any figure.

## 0.11.0 release check (2026-10-15, E2 and the CI lock)

Release branch `release/0.11.0` from main `f142d8b` (AMS-02 upgrade WP1–WP12 and WP15, the four-skill rename with
contracts 2.9.0, the Python 3.13 floor, CI batches 1 and 2, and the follow-ups PRs #103–#106). Version 0.11.0 in both
manifests, `pyproject.toml` and the README; CHANGELOG "Unreleased" became 0.11.0. Examples regenerated with the E2 venv
(version strings; the bc-propagation-fit grid hash, which covers version-stamped artifacts); unfolding-coverage drift
(about 1e-14) reverted; the sbottom benchmark artifacts' `plugin` string rewritten by hand; both new theory profiles
stamp 0.11.0 / contracts 2.9.0 and their artifacts were regenerated with their own scripts.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli`, E2 (Python 3.13.2, NumPy 2.5.3) | 21 pass, 0 fail, 2 skipped (CLI checks); 3332 tests, 0 failures, 60 skipped, 247 modules |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 21 pass, 0 fail; 3332 tests, 0 failures, 169 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## V63-M0 (2026-10-16, Python 3.13.2 on macOS 26.5 arm64; base main `982af52`, plugin 0.11.0)

Phase M0 of the v6.3 analysis-check programme: D01 baseline and gap runs, D02 evidence query, D12a rule registry, on
the stacked branches `v63/d01-baseline`, `v63/d02-evidence-query`, `v63/d12a-rule-registry`. Records:
`docs/dev/v6.3/m0-baseline.md`, `m0-budget.md`, `decision-m0.md`. Each gate run below used a clean worktree of the
branch head.

| Check | Result |
|---|---|
| Baseline `run_all_checks.py`, main `982af52` | 24 pass, 0 fail, 0 skip; 3366 tests, 0 failures, 107 skipped, 248 modules |
| Same, `v63/d01-baseline` `954f1d1` | 24 pass, 0 fail; 3380 tests, 0 failures, 107 skipped |
| Same, `v63/d02-evidence-query` `a37cd47` | 24 pass, 0 fail; 3391 tests, 0 failures, 107 skipped |
| Same, `v63/d12a-rule-registry` `4a81884` (adds the static check `rule_registry`) | 25 pass, 0 fail; 3417 tests, 0 failures, 107 skipped |
| Same with the CI lock (no torch), `4a81884` | 25 pass, 0 fail; 3417 tests, 0 failures, 170 skipped |
| `check_relocation.py`, `4a81884` | pass (codex-plugin-load skipped in the relocated copy) |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |
| Gap runs 1–5 (`tests.contracts.test_v63_baseline_gaps`) | all reproduce today's behaviour; gap 4 is a cross-artifact contradiction that L1, L2 and bundle verify all pass |

Two failures met on the way, both caused by the new files and fixed before the runs above: a subprocess call in the
gap tests had no timeout (T14), and the baseline record named a local path (packaging scan). No legacy entry point
changed output, verdict or exit code; V cases V01–V71 are registered as `not-run`. Software checks only: these runs
say nothing about physical validity.

## V63-M1 (2026-10-16, Python 3.13.2 on macOS 26.5 arm64; on top of V63-M0)

Phase M1 of the v6.3 programme after the G-M0 decision (full bounded path): D03a namespace ownership, alias contract
and load-error consumers; D04 effect catalog and operator coverage contract; D03b review of the cosmic-ray level
terms (`docs/dev/v6.3/crflux-review.md`, no term promoted). Stacked branches `v63/d03a-namespaces-aliases`,
`v63/d04-effect-contracts`, `v63/d03b-crflux-review`; each gate run used a clean worktree of the branch head.

| Check | Result |
|---|---|
| `run_all_checks.py`, `v63/d03a-namespaces-aliases` `c945263` | 25 pass, 0 fail; 3432 tests, 0 failures, 107 skipped |
| Same, `v63/d04-effect-contracts` `1d0376e` | 25 pass, 0 fail; 3444 tests, 0 failures, 107 skipped |
| Same, `v63/d03b-crflux-review` `d1a5b61` | 25 pass, 0 fail; 3444 tests, 0 failures, 107 skipped |
| Same with the CI lock (no torch), `d1a5b61` | 25 pass, 0 fail; 3444 tests, 0 failures, 170 skipped |
| `check_relocation.py`, `d1a5b61` | pass |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |
| V cases | V13, V29 passing; V35, V43, V58 definition parts (M1) passing; their M2a parts not run |
| Legacy capture (132 runs of the registry, project, validate, review and communication CLIs on the existing fixtures) | unchanged except 18 runs of `review_measurement_spec.py --profiles-from` an invalid project config, now exit 2 instead of a review (intended: D03a) |

Open before release: the companion's namespaces were not checked (its content is out of scope here); run
`contracts/registry.py --local <companion>/profile` on this tree first. Software checks only.

## V63-M2a (2026-10-16, Python 3.13.2 on macOS 26.5 arm64; on top of V63-M1)

Phase M2a (chain slice) of the v6.3 programme: D05a identity and instances, D05b bundle v2, context, inventory and
lock, D05c evaluation, report and CLI, D06 chain rules, D11a old-table reader, D17 agent interface, D08 cases and
context cost, then the fixes of an independent code review. Stacked branches `v63/d05a-identity-instances` …
`v63/m2a-review-fixes`; each gate run used a clean worktree of the branch head. Records: `docs/dev/v6.3/m2a-design.md`,
`decision-m2a.md`, `o16-agent-interface.md`.

| Check | Result |
|---|---|
| `run_all_checks.py`, D05a `ee2b910` / D05b `3774d41` / D05c `207698b` | 25 pass, 0 fail each; 3454 / 3465 / 3476 tests, 0 failures, 107 skipped |
| Same, D06 `6ede6e7` / D11a `58c0a42` / D17 `77d2607` / D08 `df430b3` | 25 pass, 0 fail each; 3501 / 3503 / 3506 / 3506 tests, 0 failures, 107 skipped |
| Same, review fixes `96f18b9` | 25 pass, 0 fail; 3518 tests, 0 failures, 107 skipped |
| Same with the CI lock (no torch), `96f18b9` | 25 pass, 0 fail; 3518 tests, 0 failures, 170 skipped |
| `check_relocation.py`, `96f18b9` | pass |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |
| V cases | all 40 M2a parts passing (registry); 45 of 80 parts passing overall (the M1 and M2a parts), the rest are M2b, M2c, D11b and M3 |
| Cases | reduced positive case complete and consistent (exit 0); CASE-CHAIN partial, 44 of 64 obligations decided (exit 3) |
| Legacy capture (132 runs of the old CLIs on the existing fixtures) | unchanged against the post-D03a capture |

A first gate run of the D06, D11a and D17 heads failed one registry test (its fixture case had become passing in D06);
the test was fixed in D06 and the later branches restacked before the runs above. Software checks only.

## V63-M2b-ratio and D11b (2026-10-16, Python 3.13.2 on macOS 26.5 arm64; on top of V63-M2a)

After the G-M2a decision (M2b ratio first, M2c paused): D07 ratio subset (`ratio-subset/v1`, R-RATIO) with the
RATIO-FACTORS and RATIO-EVIDENCE cases, and D11b definition snapshots and the migration dispatcher. Branches
`v63/d07-ratio-subset`, `v63/d11b-snapshots-migration`; gate runs on clean worktrees of the heads.

| Check | Result |
|---|---|
| `run_all_checks.py`, D07 `d2bc757` | 25 pass, 0 fail; 3524 tests, 0 failures |
| Same, D11b `6e1b3d2` | 25 pass, 0 fail; 3530 tests, 0 failures, 107 skipped |
| Same with the CI lock (no torch), `6e1b3d2` | 25 pass, 0 fail; 3530 tests, 0 failures, 170 skipped |
| `check_relocation.py`, `6e1b3d2` | pass |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |
| V cases | V28, V44, V45 (ratio), V19, V57 (D11b) passing; 50 of 80 parts passing overall |
| V44 oracle | the residual bins reported for a selection efficiency taken from different rows of one table equal the hand-computed e2/e1 != 1 bins |
| Legacy capture (132 old-CLI runs) | unchanged against the post-D03a capture |

The model-card part of M2b is not built (O03); a context that selects it is refused at freeze. Software checks only.

## V63-M3 chain and ratio (2026-10-16, Python 3.13.2 on macOS 26.5 arm64; on top of V63-M2b-ratio and D11b)

After the decision to run M3 for the chain and ratio suites: D09 shadow difference review and reader refusal matrix,
D10 advisory report check in `permit.py`, scoped exceptions and the custodian-gate requirement. Branches
`v63/d09-shadow-refusal`, `v63/d10-report-gate`; gate runs on clean worktrees of the heads. Records:
`docs/dev/v6.3/shadow-review.md`, `refusal-matrix.md`, `custodian-gate-requirement.md`, `decision-enforce.md`.

| Check | Result |
|---|---|
| `run_all_checks.py`, D09 `1d21e9a` | 25 pass, 0 fail; 3534 tests, 0 failures |
| Same, D10 `35631eb` | 25 pass, 0 fail; 3540 tests, 0 failures, 107 skipped |
| Same with the CI lock (no torch), `35631eb` | 25 pass, 0 fail; 3540 tests, 0 failures, 170 skipped |
| `check_relocation.py`, `35631eb` | pass |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |
| V cases | V31, V59 (D09), V26, V60 pre-execution parts, V65, V66 (D10) passing; 56 of 80 parts passing overall |
| Shadow difference review | zero unclassified over eight cases |
| Refusal matrix | measured on this tree and the 0.11.0 release; two non-refusing readers listed as release blockers |
| Legacy capture (132 old-CLI runs) | unchanged against the post-D03a capture |

Not run: V32 (post-execution, needs run lineage) and V30 (needs ownership metadata no reader has). No rule enforces:
the G-ENFORCE record recommends shadow mode. Software checks only.

## V63 G-ENFORCE step 1 (2026-10-16, Python 3.13.2 on macOS 26.5 arm64)

After the decision to keep every rule in shadow mode: `recipe_semantics.py` refuses an upstream artifact with an
unknown capability; the `dependencies.py` row of the refusal matrix is documented as intended and awaits review.
Branch `v63/refusal-blockers`, head `bbed3ec`, clean worktree.

| Check | Result |
|---|---|
| `run_all_checks.py` | 25 pass, 0 fail; 3542 tests, 0 failures, 107 skipped |
| Same with the CI lock (no torch) | 25 pass, 0 fail; 3542 tests, 0 failures, 170 skipped |
| `check_relocation.py` | pass |
| Ruff 0.16.10, mypy 2.4.0 | clean |
| Legacy capture (132 old-CLI runs) | unchanged |

## 0.12.0 release check (2026-10-16, E2 and the CI lock)

Release branch `release/0.12.0` from main `8c05905`. It covers the v6.3 analysis-check programme (PRs #116–#120, #122),
contracts 2.10.0 with the retirement of `crflux:local-interstellar` (#121), and WP13–WP16 with the DRAGON2 fix
(#110–#115).

What changed:
- Version 0.12.0 in both manifests, `pyproject.toml` and the README; CHANGELOG "Unreleased" became 0.12.0.
- Examples regenerated with the E2 venv. Only version strings and the bc-propagation-fit grid hash change; that hash
  covers version-stamped artifacts.
- Two regenerated values were reverted:
  - the unfolding-coverage drift (about 1e-13);
  - one bc-propagation-fit `condition_number_log10` that flipped between 17.2 and null. Both mean a flat direction,
    and the test treats them alike.
- The sbottom benchmark artifacts' `plugin` string was rewritten by hand.
- The three theory profiles stamp 0.12.0 / contracts 2.10.0, and their artifacts were regenerated with their own
  scripts.

The companion ams02-research 1.5.0 requires hep-research >=0.11.0. Its namespace check (`registry.py --local`)
reported no findings.

| Check | Result |
|---|---|
| `run_all_checks.py`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail; 3542 tests, 0 failures, 61 skipped, 265 modules |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 25 pass, 0 fail; 3542 tests, 0 failures, 170 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## V63-M2b-MODEL (2026-10-16, Python 3.13.2 on macOS 26.5 arm64; base main `f3089da`, plugin 0.12.0)

The model part of M2b on branch `v63/m2b-model`: suite `model-card/v1`, bundle mode `model` and the pairing contract
`contracts/semantics/model_pairings.json` (the O03 set). Design in `docs/dev/v6.3/m2b-model-design.md`.

How it was built:
- Red tests first, as expected failures: `593b4a6`.
- Then the implementation, with the decorators removed.
- All cases are synthetic: CASE-MODEL, MODEL-USAGE and MODEL-SHARING in `tests/contracts/v63_cases.py`.
- The adapter `to_pyhf` confirms the structural mapping of CASE-MODEL (V06): one `normsys` for `lumi` across SR and CR.

| Check | Result |
|---|---|
| `tests/contracts/test_v63_d07_model.py` | 16 tests pass. V06, V07, V08, V46, V47 and the model parts of V11, V15, V18, V24, V25 and V64 are passing in the registry (67 of 80 V parts). |
| O03 gap tests (`tests/adapters/test_sr_cr_model_card.py`, `UnmappedPairings`) | pass: Poisson and log-normal constraints are refused, and the bounds are the converter's fixed ones |
| A chain bundle selecting `model-card` | refused with `bundle.suite_mode` (`test_v63_d07`) |
| `run_all_checks.py` | 25 pass, 0 fail; 3560 tests, 0 failures, 107 skipped |
| Same with the CI lock (no torch) | 25 pass, 0 fail; 3560 tests, 0 failures, 170 skipped |
| `check_relocation.py` | pass |
| Ruff 0.16.10, mypy 2.4.0 | clean |

One failure seen once and not reproduced: `test_a_hanging_module_fails_with_a_reason` failed during a parallel full
run. It passed alone and in both full reruns, so it is timing under load.

## V63-D12B-CUSTODY (2026-10-16, Python 3.13.2 on macOS 26.5 arm64; branch `v63/d12b-custody` on `v63/m2b-model`)

V30 at companion transition stage 1: `contracts/custody.py`, an inventory and report only. Red tests first
(`aadc554`), then the implementation. All profiles are synthetic stand-ins in temporary folders; no companion content
was read.

| Check | Result |
|---|---|
| `tests/contracts/test_v63_d12b.py` | 3 tests pass. Plugin profile: public by origin. Run-time `--local` profile: `controlled-metadata-missing`, unverified. Project-local profiles, including one whose content is public: `unknown`, unverified, never public. A rejected run-time profile stays rejected, and `load_project` gives the same result before and after the inventory. |
| Registry | V30 passing (68 of 80 V parts) |
| `run_all_checks.py`, then the CI lock | first run: 23 pass, 2 fail. The packaging scan read the old argument destination as a site fact (a `.local` host name); it was renamed to `run_time_dirs`. The final-tree run is recorded below (V63-M2C-PROPOSAL). |
| Ruff, mypy | clean |

## V63-M2C-PROPOSAL (2026-10-16; final tree of steps 1–3 on branch `v63/m2c-proposal`)

Step 3 of the decision change is `docs/dev/v6.3/m2c-proposal.md`, which is docs only and stops for the owner's
decision. Gate on the final tree (model part, V30 and the proposal):

| Check | Result |
|---|---|
| `run_all_checks.py` (miniconda Python 3.13.2) | 25 pass, 0 fail; 3563 tests, 0 failures, 107 skipped |
| Same with the CI lock (no torch) | 25 pass, 0 fail; 3563 tests, 0 failures, 170 skipped |
| `check_relocation.py` | pass |
| Registry | 68 of 80 V parts passing. Not run: the 11 M2c parts and V32 (post-execution) |

Two timing-sensitive tests failed once each under a parallel full run and passed in isolation (three times each)
and in this run:
- `test_batch_hardening.SubmissionOutcomesT31` (CI lock);
- `test_run_all_checks.ModuleTimeoutTests` (earlier).

## V63-M2C (2026-10-16, Python 3.13.2 on macOS 26.5 arm64; branch `v63/d05d-run-lineage`)

`run-lineage/v1` (D05d, D08 run cases), built after the owner approved `m2c-proposal.md`. Design in
`docs/dev/v6.3/m2c-design.md`.

How it was built:
- Red tests first, as expected failures: `71328d8`.
- Fixtures are synthetic and in temporary folders (`tests/contracts/v63_runs.py`).
  - Single runs are hand-made computational-runs.
  - The campaign is a `core.partition` campaign run with `LocalExecutor`, with an execution bundle frozen by the test
    (`core.partition.bundle.freeze`), and the adapter's `build_artifact` as the interface record.
  - Tampering variants edit only those temporary records.
- `core/partition/` and `examples/batch-partition` are unchanged.

| Check | Result |
|---|---|
| `tests/contracts/test_v63_d05d.py` | 17 tests pass: V20, V32, V33, V38, V53, V54, V55, V56, V61, V62, V63, V70, and the post-execution part of V60 |
| V70 | no report or agent summary of the blinded cases contains the fixture's result value |
| Refusal matrix (`test_v63_d09`) | three result-binding rows. `validate.py` and `review_measurement_spec.py` refuse; `dependencies.py` accepts (the documented behaviour, listed as a blocker) |
| Registry | **80 of 80 V parts passing** |
| `run_all_checks.py` | 25 pass, 0 fail; 3580 tests, 0 failures, 107 skipped |
| Same with the CI lock (no torch) | 25 pass, 0 fail; 3580 tests, 0 failures, 170 skipped |
| `check_relocation.py` | pass |
| Ruff 0.16.10, mypy 2.4.0 | clean |

## 0.13.0 release check (2026-10-16, E2 and the CI lock)

Release branch `release/0.13.0` from main `4b90c71`. It covers the v6.3 model-card suite, the custody inventory and run
lineage (PRs #124–#127): all 80 V parts pass.

What changed:
- **Contracts 2.11.0:** new sidecar formats only. The 127 fixtures and the measurement-spec template moved to 2.11.0.
- **Version 0.13.0** in both manifests, `pyproject.toml` and the README; CHANGELOG "Unreleased" became 0.13.0.
- **Examples regenerated** with the E2 venv. Only version strings and the bc-propagation-fit grid hash change.
  - The unfolding-coverage drift was reverted.
  - The bc-propagation-fit flat-direction condition number (17.2 versus null) was kept at its committed value.
- **Hand edits:** the sbottom benchmark artifacts' `plugin` string.
- **Theory profiles:** the three stamp 0.13.0 / contracts 2.11.0, and their artifacts were regenerated with their own
  scripts.
- **Review packet** (`docs/dev/v6.3/review-packet.md`): extended to the full suite set.

The companion ams02-research 1.5.0 requires hep-research >=0.11.0. Its namespace check (`registry.py --local`)
against main `4b90c71` reported no findings.

| Check | Result |
|---|---|
| `run_all_checks.py`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail; 3580 tests, 0 failures, 61 skipped, 268 modules |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 25 pass, 0 fail; 3580 tests, 0 failures, 170 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## V63-ENFORCE-INPUTS (2026-10-17, Python 3.13.2 on macOS 26.5 arm64; branch `v63/enforce-inputs` on main `bce13af`)

The G-ENFORCE inputs were completed for the full suite set.

**Shadow difference review** (`docs/dev/v6.3/shadow-review.md`): extended to 12 model and run cases, with zero
unclassified differences (`test_v63_d09.ModelAndRunShadowReview`). Legacy model-card errors agree with the new rule
that decides the same question.

**Custodian-gate requirement** (dated update), with matching advisory checks in `permit.py check-report`
(`test_v63_d05d.PostExecutionPermit`, 4 tests):
- the post-execution conditions;
- `min_evidence_level` per purpose (O15);
- per-root evidence levels must follow from the obligations, so a raised level is inconsistent;
- model-only bundles are diagnostics only (O13).

| Check | Result |
|---|---|
| `run_all_checks.py` | 25 pass, 0 fail; 3584 tests, 0 failures, 107 skipped |
| Same with the CI lock (no torch) | 25 pass, 0 fail; 3584 tests, 0 failures, 170 skipped |
| `check_relocation.py` | pass |
| Ruff 0.16.10, mypy 2.4.0 | clean |
| Registry | 80 of 80 V parts passing |

## SPLIT-LIVE-EVAL (2026-10-19, Claude Code 2.1.303, claude-sonnet-5-5)

Live evals of the split of hep-communication into hep-literature and hep-writing (restructuring plan v6, section 8),
branch `feat/split-communication` at 80201cde against main ee6b8b83 (0.15.0), one campaign, about $74 in model
calls. Results in the repository's `evals/` (`routing/results/split-*`, `research_communication/results/split-*`,
`behavior/results/split-2026-10-19-*`). Single samples are noisy; doubtful cases were repeated twice on both sides.

| Plan section 8 criterion | Main | Branch | Verdict |
|---|---|---|---|
| Full routing set, strict | 369/394 | 369/404 (lenient 372) | baseline re-measured |
| 2. The 53 cases that named hep-communication, strict | 51 | 51 | pass (not below) |
| New split cases (`lit-*`, `j13`) | - | 7/10; repeats: `lit-turns-1` 0/3, `lit-bound-table-1` 1/3, `lit-bound-related-1` 1/3 | weak spots |
| 3. Communication eval, cases loading no skill | 2/11 | 4/11 (01 trace, 06 zh status, 10 summary, 11 injection) | **fail** (limit 2/11) |
| 4. Publication-record questions loading no skill (12 cases) | 0 | 0 | pass |
| 5. Other skills' cases: pass on main, fail on branch | - | 11 in one run; with 3 runs each: `wp11-xexp-2` 3/3 -> 0/3 (loads hep-literature), `dr-a-toy-1` 3/3 -> 1/3, `th-nucstruct-1` 3/3 -> 1/3, `t19-quick-3` 3/3 -> 1/3, `dr-a-toy-2` 3/3 -> 2/3; `th-a-const-2` 1/3 -> 0/3 and `wp11-bound-dm-2` 1/3 -> 0/3 now load hep-literature instead of hep-communication; `c-nuc-iso-2`, `co-roofit-neg-1`, `d-ms-aniso-1` flaky on both | **fail** |
| 5. Plan 6.7 cases (`wp11-xexp-3`, `eic-underspec-1`, `t19-turns-3`) | fail | fail, same outcome | not worse |
| 6. G3 behavior case `l2-write-cite-intro` | - | pass (loads hep-literature) | pass |
| 7. Always-on growth | 2,417 | 2,529 tokens (+112) | pass |
| Behavior subset (communication cases, 1 run) | 2/8 | 5/9; `l2-comm-status` (short abstract sentence) loads no skill | - |
| Name comparison (63 cases involving the two skills) | - | working names 58/63, `hep-sources`/`hep-manuscript` 53/63 | keep working names |

Outcome: the round fails criteria 3 and 5. The split pulls published-result questions that belong to hep-theory or
hep-statistics (`wp11-xexp-2`, `th-a-const-2`, `wp11-bound-dm-2`) into hep-literature, and short writing requests
(abstract sentence, one-line summary, a status sentence in Chinese) load no skill more often than before. Per plan
section 8 the next step is a description round (at most two) before the split may proceed; plan step 0 stands either
way.

Description round 1 (dbb5ed02, about $8; plan section 8 allows two). hep-literature names a source's status and whether
citations are verified, and its "Not for" sends models and constants to hep-theory and p-values to hep-statistics (687
characters); hep-writing adds "even one sentence for an abstract or summary; load it first" (652); always-on 2,534
(+117). Rerun of the 93 cases that involve the two skills, the wp11 set and the doubtful cases, one run:

| Measure | Round 0 | Round 1 | Main |
|---|---|---|---|
| The 93 cases, strict | 76 | 78 | 80 of the 83 that exist on main |
| Communication eval, no skill loaded (criterion 3, limit 2/11) | 4/11 | 3/11 (01, 06, 09) | 2/11 |
| `wp11-xexp-2` (hep-statistics) | hep-literature | hep-literature (0/4 over all branch runs) | 3/3 |
| `th-a-const-2`, `wp11-bound-dm-2` (hep-theory) | hep-literature | hep-theory; no skill | 1/3 each |
| `lit-turns-1` second turn (citations verified?) | no skill | no skill | - |
| `dr-a-toy-1`, `th-nucstruct-1`, `t19-quick-3` (outside the split) | fail | fail (now 0/4, 1/4, 1/4 on the branch) | 3/3 each |

Round 1 still fails criteria 3 and 5. The persistent regressions in `dr-a-toy-1`, `th-nucstruct-1` and `t19-quick-3`
involve hep-detector, hep-theory and hep-computing only, whose descriptions the split did not change; they point to the
eight-skill listing itself, which a description round of the two new skills cannot address.

Cause of the regressions outside the split (about $6.60, 5 runs per arm; `evals/routing/results/cause-*`):

| Arm | `dr-a-toy-1` (hep-detector) | `t19-quick-3` (hep-detector) | `th-nucstruct-1` (hep-theory) |
|---|---|---|---|
| A main (7 skills) | 5/5 | 4/5 | 3/5 |
| B branch (8 skills) | 1/5 | 2/5 | 2/5 |
| C branch without hep-literature (7) | 0/5 | 1/5 | 3/5 |
| E as C, hep-writing with the old hep-communication description | 0/5 | 3/5 | - |
| F phase 0 only (338f8d78) | 5/5 | 5/5 | - |
| G branch, the two skills renamed hep-citations / hep-authoring | 5/5 | 5/5 | - |

`th-nucstruct-1` is noise on every arm. The other two follow the alphabetical position of the skills in the host's
listing, not the description text: with hep-communication gone, hep-computing is listed first and draws ambiguous
detector requests (`dr-a-toy-1` loads hep-computing); names that sort before hep-computing (arm G) restore main's
outcome. A name change is therefore the candidate for description round 2 (plan section 8 allows names or
descriptions); the working names and `hep-sources`/`hep-manuscript` all sort after hep-computing.

Description round 2 (ebb58136, about $9.30; the last round plan section 8 allows): the two skills are renamed
hep-citations and hep-authoring, which sort before hep-computing; descriptions as in round 1 (689 and 651 characters);
always-on 2,538 (+121); offline gate 24 pass, 4,324 tests, 119 skipped. Same 93 cases, communication eval and
behavior subset; doubtful cases repeated twice:

| Measure | Main | Round 2 | Verdict |
|---|---|---|---|
| The 93 cases, strict (83 exist on main) | 80/83 | 74/83; all 93: 82 (round 1 78, round 0 76) | - |
| 3. Communication eval, no skill loaded | 2/11 | 1/11 (01) | pass |
| 4. Publication-record questions | 0 no-skill | 0 no-skill | pass |
| 6. `l2-write-cite-intro` | - | pass | pass |
| Behavior subset (communication) | 2/8 | 4/8 | - |
| `dr-a-toy-1`, `t19-quick-3` (listing order) | 5/5, 4/5 | 5/5 (cause arm G), 2/3 | fixed |
| `th-a-const-2`, `co-roofit-neg-1`, `wp11-bound-dm-1` (3 runs) | 1/3, 1/3, 1/1 | 2/3, 2/3, 2/3 | not worse |
| `wp11-bound-dm-2` (3 runs) | 1/3 | 0/3 (no skill) | marginal |
| `wp11-xexp-2`: compatibility p-value of two named experiments (3 runs) | 3/3 hep-statistics | 0/3, loads hep-citations | **regression** |
| New split cases | - | 8/10 (`lit-negative-1`, `lit-turns-1` fail) | - |

Round 2 passes criteria 2, 3, 4, 6 and 7 and fails criterion 5 on one case (`wp11-xexp-2`, every branch run since
round 0 loads the literature skill) and marginally on `wp11-bound-dm-2`. By the plan's rule (two failed rounds) the
split is abandoned unless the maintainer accepts or waives that case.

Targeted fix after round 2 (769f34a0, about $2.60, maintainer-approved beyond the plan's two rounds): hep-citations
drops the comparison ask-first clause and its "Not for" says hep-statistics owns whether two results agree (653
characters, always-on 2,527, +110). The 28 cases that expect hep-citations, name it in `not` or accept it, plus
`wp11-xexp-2`, `wp11-xexp-3` and `wp11-bound-dm-2`: 26/28 strict (round 2: 23). `wp11-xexp-2` 3/3 hep-statistics
(main 3/3), `wp11-bound-dm-2` 1/3 (main 1/3), `lit-negative-1` now passes. With this, every regression measured in
the rounds above is back at main's level; the full 404-case set was not rerun after the fix.

Final full routing run on e79ccf80 (2026-10-20, about $32 plus $0.60 of repeats): 379/404 strict (380 lenient); on
the 394 cases that exist on main 371 against main's 369. Four cases pass on main and fail here, six the other way;
repeated: `c-det-atlas-2` 2/3 on both sides, `d-cc-preserve-1` 3/3 main vs 2/3, `st-sensitivity-1` and
`wp11-bound-dm-2` flaky on main (2/3, 1/3). New split cases 8/10 (`lit-bound-related-1`, `lit-turns-1` fail). No
regression beyond run-to-run noise; accepted by the maintainer and merged. Total live spend for the split about $134.

Follow-up `lit-turns-1` (2026-10-20, Claude Code 2.1.304, claude-sonnet-5-5, branch `fix/authoring-citation-handoff`):
the second turn ("have all these citations been verified?") had loaded no skill in all 7 earlier runs, because
hep-authoring's resource table offered `check_citations.py` for it. hep-authoring now says to load hep-citations
for it (Never line, table row, workflow step 6). Live: `lit-turns-1` 2/3 strict (`cithop-turns-r1..3`); the third
run loaded hep-citations in turn 1, as the draft's citation handoff, and nothing new in turn 2 (lenient pass). The
other new split cases and `j13` (`cithop-others`): 8/9; `lit-bound-related-1` loads hep-citations before
hep-authoring, as in its earlier runs (1/3). Spend $1.43, of which $0.47 on a first attempt with a relative
`--plugin-dir` that loaded no plugin (discarded; the harness does not yet fail when the plugin is missing).

## INDEPENDENT-REVIEW-P1 (2026-10-21, E2; branch `feat/independent-review-p1` from main `c4f7954b`, unreleased)

P1 of the independent review mechanism (`docs/dev/independent-review-spec.md`; draft decision record
`docs/dev/decision-independent-review.md`), contracts 3.3.0. Baseline: `run_all_checks.py --part all` on clean main
passes; the run started on the branch failed only `packaging_scan` on the newly added spec.

| Check | Result |
|---|---|
| New review tests: `tests/contracts/test_review_{contract,state,lcs}.py`, `tests/skills/hep_authoring/test_review_{units,canaries,generator,receipt,repair_check,end_to_end}.py` | 161 pass. Covered: every receipt code of spec 7.1 and 7.2 rejected alone; every repair and check code of 7.3 and 7.4; decide rows 1-14 and the five arbitration conclusions; the exhaustive state test (74,800 combinations); the 5.3 field table against `review_record.json`; two-sided canary witnesses and the one-sided shortfall; LCS against brute force on 500 random sequences; the written example per role and a corrupted example stopping the build; packet hygiene; the end-to-end review driven by `next` (closed, `check` exit 0) and its byte-identical rerun |
| `run_all_checks.py --part all`, E2 (Python 3.13.2), commit `95d79322` | 25 pass, 2 fail (`packaging_scan` and `tests.adapters.test_batch_privacy`, which runs the same scan); 4671 tests in 392 modules, 4541 pass, 1 failure (that scan test), 129 skipped |
| Same after the maintainer's packaging decision (options A and B), commit `c6c4942c` | 27 pass, 0 fail; 4676 tests in 393 modules, 4547 pass, 0 failures, 129 skipped |
| `packaging_scan` | at `95d79322` fail: `restricted-site-fact` on `docs/dev/independent-review-spec.md` and `skills/hep-authoring/assets/review-hosts.json` (Claude Code local memory and settings file names), `private-path` on `review-hosts.json` (inferred shared-directory patterns); a stop condition of the work order. Resolved at `c6c4942c` by the maintainer's choice (decision record, open item 1): the hostname rule skips names followed by `.md` or `.json`, the host notes use placeholders; pass |
| `check_ownership.py`, `check_layering.py`, `check_host_neutral.py`, `check_routing_static.py`, `make_cases.py --stdout` equal to `cases.json` | pass |
| After the maintainer decisions 1, 2, 5, 6 (clarifying line under the invariant, decision record, host facts and the `CLAUDE_PID` session start), commit `54823740` | 27 pass, 0 fail; 4679 tests in 393 modules, 4550 pass, 0 failures, 129 skipped; `session_start()` on this host gave 11:09:16Z, the session's start (19:09:16 local) |
| After the P3 stage-1 pilot fixes (master seed bound to the review id; plugin-relative paths in records), commit `9f36acec` | 27 pass, 0 fail; 4682 tests in 393 modules, 4553 pass, 0 failures, 129 skipped |
| After the three pilot must-fix items (copy guard, design canaries on ordinary documents, no empty slots; `test_review_pilot_fixes.py`), commit `88a40a9a` | 27 pass, 0 fail; 4690 tests in 394 modules, 4561 pass, 0 failures, 129 skipped; design canaries generated on all five pilot documents (2 each) |
| P3 stage-1 pilot, live agents (outside the repository; decision record, Decision 4) | 5 documents, 54 agent runs: planted errors self-check 9/12, independent review 10/12; facts canaries 7/7 hit and exactly corrected; findings for P2 listed there |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |
| `hep-authoring/SKILL.md` | 8,992 bytes, 73 lines |
| Smoke test on a copy of the spec, real host observation | `next` prints the repair `isolation_precondition` on this host; with `CLAUDE_CODE_FORK_SUBAGENT=0` it prints `dispatch` with 8 slots; every written example passes `check --record-only`; `check` gives `not_closed` (incomplete) |

Not run: the CI-lock environment (the new tests are standard-library only), live agent reviews (P3), live routing of
the four new cases. Skipped tests are unverified, not passed.

## 0.20.0 release check (2026-10-21, E2 and the CI lock)

Release branch `release/0.20.0` from main `c325d678` (#186 Geant4 phase 2; main CI green). Minor release with
contracts 3.1.0 (GEANT4-PHASE2 below). The ams02-research companion (requires hep-research `>=0.11.0`, profile
contracts `>=2.0`) needs no change.

What changed: version 0.20.0 in both manifests, `pyproject.toml`, the README, the two assets and the theory-profile
scripts; CHANGELOG `Unreleased` is `0.20.0`. Examples regenerated (E2; `bc-propagation-fit` with the CI lock): only
version strings and the hashes that cover them change (`unfolding-coverage` drifted at 1e-14 and was left as
committed); the sbottom benchmark artifacts' `plugin` string edited by hand; theory-profile artifacts regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4491 tests, 4363 pass, 0 failures, 128 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 25 pass, 0 fail, 2 skipped; 4491 tests, 4270 pass, 0 failures, 221 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## 0.21.0 release check (2026-10-21, E2 and the CI lock)

Release branch `release/0.21.0` from main `bae1be9a` (#188-#192; main CI green, `optional-selection` ok). Minor release
with contracts 3.2.0 (simulated dataset status), the Gluckstern few-layer warning, the FoCal-E `longitudinal-profile`
reference benchmark with mixture materials (GEANT4-FOCAL below) and the CI speedup. The ams02-research companion
(requires hep-research `>=0.11.0`, profile contracts `>=2.0`) needs no change.

What changed: version 0.21.0 in both manifests, `pyproject.toml`, the README, the two assets, the theory-profile scripts
and the sbottom benchmark artifacts' `plugin` string (by hand); CHANGELOG `Unreleased` is `0.21.0`. Examples
regenerated (E2; `bc-propagation-fit` with the CI lock): only version strings and the hashes that cover them change
(`unfolding-coverage` drifted at 1e-14 and was left as committed).

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4510 tests in 383 modules, 4381 pass, 0 failures, 129 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 25 pass, 0 fail, 2 skipped; 4510 tests, 4288 pass, 0 failures, 222 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## EFFICIENCY-NAMESPACED (2026-10-22, E2): same efficiency counted twice under a namespace

Found after 0.23.0, unfixed until now: a measurement spec listing a bare `efficiency` next to `<ns>:efficiency` (or
two namespaced `<ns>:efficiency` terms) passed with no finding. The bare-efficiency error needs the other name to end
in `_efficiency`, and the repeated-category error compares names with the namespace kept, while
`_correction_classes` folds both into one class. Decision: no contracts major, so a new warning
`measurement.efficiency_counted_twice_namespaced` (the existing errors unchanged and not doubled by it).
`correction-chain.md` now describes the behavior (a profile term with another name, such as `<ns>:trigger`, still
passes unflagged: the validator cannot tell it is an efficiency); reference inventory regenerated.

| Evidence test (file::Class::method) | Kind | Parent `a53af7e0` | Fix |
|---|---|---|---|
| `tests/contracts/test_measurement_contract.py::MeasurementRules::test_namespaced_efficiency_next_to_bare_efficiency_warns` | behavioral (warning on 3 pairs, no finding on 2 single-efficiency chains, error unchanged on 3) | fail (3 of 3 warning subtests) | pass |
| `tests/contracts/test_theory_contract.py` warning-fixture test on the new fixture `warning/measurement_v26_efficiency_counted_twice_namespaced.json` | fixture | fail (no warning) | pass |

Outcome check: every JSON artifact in the plugin with an `artifact_type` (360 files: fixtures, examples, assets,
profiles), validated plain and strict before and after the change: identical `ok` and identical findings for all 720
validations, so no shipped artifact gains the new warning. Fixtures regenerated with `make_fixtures.py`: only the new
warning fixture and its `cases.json` entry change; the verdict snapshot (`gate_verdicts.json`) gains its entry
(valid, default and strict), no other entry moves.

## PERIODICITY-REFIT (2026-10-22, E2): periodicity_scan.py red-noise null refitted per surrogate (sci-fix, S1)

Found after 0.23.0: the AR(1)/OU surrogates of `periodicity_scan.py` (added in 0.14.0, `2cd78747`) used phi (or
tau) and the variance estimated once from the observed series, and the docstring called the result conservative.
Measured first, with a criterion fixed before the run: no-signal toys, 400 per configuration (AR(1) on t = 0..n-1
with phi 0.3, 0.7, 0.9; OU on sorted uniform times with lag-1 correlation 0.5 and 0.8; n = 50, 100, 200; errors 1;
grid 1/T to 0.5 in ceil(2.5 n) steps, whole band), 199 surrogates, seeded; rejection fraction r(alpha) for alpha
0.01, 0.05, 0.1 with binomial errors; anti-conservative beyond errors when r > alpha + 2 sqrt(alpha (1 - alpha) / 400).

Pre-fix method (a), the 0.23.0 `scan()` itself (r +- binomial error; `!` beyond the criterion):

| Configuration | alpha 0.01 | alpha 0.05 | alpha 0.1 |
|---|---|---|---|
| AR(1) n 50, phi 0.3 / 0.7 / 0.9 | 0.005 / 0.007 / 0.018 | 0.052 / 0.065 / **0.147 +- 0.018 !** | 0.092 / **0.142 +- 0.017 !** / **0.253 +- 0.022 !** |
| AR(1) n 100, phi 0.3 / 0.7 / 0.9 | 0.005 / 0.003 / 0.007 | 0.030 / 0.045 / **0.077 +- 0.013 !** | 0.075 / 0.113 / **0.163 +- 0.018 !** |
| AR(1) n 200, phi 0.3 / 0.7 / 0.9 | 0.013 / 0.010 / 0.010 | 0.043 / 0.043 / 0.060 | 0.072 / 0.098 / 0.107 |
| OU n 50, 0.5 / 0.8 | 0.000 / 0.005 | 0.015 / 0.045 | 0.050 / 0.117 |
| OU n 100, 0.5 / 0.8 | 0.005 / 0.005 | 0.015 / 0.033 | 0.050 / 0.095 |
| OU n 200, 0.5 / 0.8 | 0.003 / 0.005 | 0.020 / 0.035 | 0.035 / 0.083 |

(a) is anti-conservative beyond errors in 5 cells (short, strongly red AR(1) series: the lag-1 estimate is biased low,
mean 0.80 for phi 0.9 at n = 50, so the surrogates are too white); OU is calibrated or conservative. Variant (b), a
double parametric bootstrap that refits the null on each outer surrogate (prepivoting, arXiv:2208.02028v1 section
3.2.2), measured in a separate vectorized implementation on the same toys (199 x 199), removed most of it but not all
(AR(1) n 50, phi 0.9: 0.072 at 0.05 and 0.142 at 0.1, still beyond the criterion; 4 cells). With the first-order
bias-corrected lag-1 estimate phi + (1 + 4 phi)/n in both levels (exploration on the six worst configurations) no
cell exceeded it, but for OU it was conservative (0.025 at 0.05, n = 50), so the fix uses the correction for ar1 only.

Decision: (a) is anti-conservative beyond errors, so the refit is the default (`--null-fit refit`, `--inner-surrogates`
default 199); `--null-fit once` keeps the 0.14.0-0.23.0 numbers for the same seed (checked on all 4000 shared toys
and pinned in `test_periodicity_scan.py::NullFitOption`) and carries a `calibration_note`. The default after the fix,
`scan()` itself on the same toys (400 toys for n = 50 and 100, 200 toys for n = 200; no cell beyond the criterion):

| Configuration | alpha 0.01 | alpha 0.05 | alpha 0.1 |
|---|---|---|---|
| AR(1) n 50, phi 0.3 / 0.7 / 0.9 | 0.007 / 0.015 / 0.010 | 0.058 / 0.060 / 0.043 | 0.122 +- 0.016 / 0.098 / 0.117 |
| AR(1) n 100, phi 0.3 / 0.7 / 0.9 | 0.010 / 0.000 / 0.005 | 0.048 / 0.048 / 0.037 | 0.100 / 0.100 / 0.095 |
| AR(1) n 200 (200 toys), phi 0.3 / 0.7 / 0.9 | 0.005 / 0.010 / 0.015 | 0.045 / 0.060 / 0.050 | 0.105 / 0.105 / 0.090 |
| OU n 50, 0.5 / 0.8 | 0.010 / 0.007 | 0.048 / 0.052 | 0.085 / 0.113 |
| OU n 100, 0.5 / 0.8 | 0.010 / 0.013 | 0.048 / 0.052 | 0.090 / 0.107 |
| OU n 200 (200 toys), 0.5 / 0.8 | 0.010 / 0.000 | 0.045 / 0.065 | 0.085 / 0.125 +- 0.023 |

Cost: N x (M + 1) surrogate series (new cap 4e6); about 0.2 s for n = 100, N = M = 199 (E2, this machine). The study scripts
(`calib.py`, `calib_final.py`) ran outside the plugin; the slow tier below reruns its discriminating part.

Evidence (`tests/skills/hep_statistics/test_periodicity_refit_null.py`; parent tree `a53af7e0` adapted by adding only
this test module, whose `scan()` call passes the inner count only where `scan()` has it):

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `test_periodicity_refit_null.py::RefitCalibration::test_size_is_at_most_alpha_on_short_red_series` | analytic (locator: arXiv:2208.02028v1 p. 8, Theorem 3.2 p. 15); negative control | fail: 0.113 > 0.103 at 0.05, 0.207 > 0.173 at 0.1 | pass: 0.047, 0.080; control 0.193 > 0.173 | no | E2, Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1 |
| `test_periodicity_refit_null.py::RefitCalibration::test_size_does_not_depend_on_phi` | invariant (pivotality) | fail: 0.107 > 0.104 | pass: 0.033 | no | E2 |
| `test_periodicity_refit_null.py::IndependentDoubleBootstrap::test_module_p_matches_the_double_bootstrap_of_the_source` | independent implementation (locator: arXiv:2208.02028v1 section 3.2.2, pp. 14-15) | fail: 0.5145 vs 0.8015 | pass: 0.7985 vs 0.8015 | no | E2 |
| `test_periodicity_refit_null.py::RefitCalibrationSlow::test_ar1_size_at_most_alpha` | analytic; negative control | fail: AR(1) n 50 phi 0.9: 0.110 at 0.05, 0.198 at 0.1 | pass (9 cells) | slow tier, run with HEP_SLOW_TESTS=1 | E2 |
| `test_periodicity_refit_null.py::RefitCalibrationSlow::test_ou_size_at_most_alpha` | analytic (calibration check, not discriminating: OU was not anti-conservative) | pass | pass | slow tier, run | E2 |

Tolerances were fixed before the first run (3 binomial sigma per cell; 0.05 for the implementation comparison, about 4
combined Monte Carlo sigma at N = 1999, inner 199). One change after the first fix run: the negative control was
asserted at alpha 0.05 and 0.1, and at 0.05 it gave 0.093, above alpha but below the 3-sigma bound of 150 toys; it is
now asserted at 0.1 only (0.193 > 0.173). The checks of the fix itself were not changed. Mutants of `scan()` against
the three fast tests: M1 default reverted to `once` killed (3 tests), M2 no bias correction killed (3), M3 inner
surrogates from the data's fit (no refit) killed (independent implementation), M5 correction sign flipped killed
(independent implementation), M4 prepivot count `<` instead of `<=` survived (a tie rule below the Monte Carlo
tolerance). Also passing with HEP_SLOW_TESTS=1: `test_periodicity_scan.py::NullCalibrationSlow` (white-noise p
uniform; AR(1) phi 0.7 n 100 rejects 0.05 +- 0.02, now with the refit). Ledger PERIODICITY-REFIT (C3, D3);
advisory SFA-2026-038 (introduced 0.14.0, no fixed event yet). Docstring, `time-series-inference.md`, the
hep-statistics README and the capability matrix state the measured calibration; reference inventory regenerated.

## SCIFIX-TRACE-FORWARD (2026-10-22, CI lock venv; branch `scifix/trace-forwarding` from main)

| Check | Result |
|---|---|
| `poisson_diagnostics.py fc-interval --n 3 --b 1.0` output | `trace.code_paths`: core/__init__.py, core/stats/__init__.py, core/stats/_linalg.py, core/stats/_poisson.py, core/stats/poisson_diagnostics.py, core/trace.py |
| `tests/contracts/test_trace.py::TraceForwarding` (the CLI trace reaches the statistical-result, sorted, valid; malformed entries and a non-object trace are dropped) | pass |
| `run_all_checks.py --no-cli --jobs 6`, CI lock (before the rebase on main) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4906 tests, 4655 pass, 0 failures, 251 skipped |
| ruff, mypy on `core/` and `contracts/` | clean |

## SCIFIX-EVIDENCE-CI (2026-10-22, CI lock venv plus pyhf 0.7.6, ArviZ 0.23.4, pdg 2026.0, SQLAlchemy 2.1.5, typing_extensions 4.16.0; branch `scifix/evidence-ci-pdg` from main `f238ef3e`, 0.24.0)

| Check | Result |
|---|---|
| `run_required_backends.py --from-ledger --require pyhf==0.7.6,arviz==0.23.4,pdg==2026.0 --no-skips` (the new weekly `ledger-evidence` job, run locally) | exit 0; 56 nodes in 25 modules: 56 pass, 0 environment errors, 0 unverified, 0 do not hold, 0 skipped |
| `tests/core/test_constants.py::PdgPackageTests::test_bundled_masses_equal_the_package` (TH9-MASSES) on parent `84c0a68c` and fix `23910085`, each in a detached worktree with the current test file copied in, CI lock plus pdg 2026.0 | pass on both: `core/constants` exists on the parent and the fix does not change it, so the oracle cannot show the defect; parent record updated (was skip), TH9-MASSES stays D1 |
## SCIFIX-TRANSCRIPTION-ORACLES (2026-10-22, CI lock venv: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch; Geant4 11.4.3 native build; branch `scifix/transcription-oracles` from main `f238ef3e`)

The transcription report (`tools/scifix_ledger.py report`) listed four C3 entries whose independence records all
take their expected values from formulas transcribed into the repository: DR-WP1-01, DR-WP1-02, DR-WP2-06-CALO and
DR-WP2-06-MS. One oracle whose expected value comes from elsewhere was added to each of the first three; none was
found for DR-WP2-06-MS. Tolerances were fixed in the docstrings before the first run; all three new tests passed on
their first run on this branch and none was changed afterwards.

**What was read (2026-10-22).** arXiv:1811.04660v2 (scifix:S07), p. 5: eq. (3.1), the Gaisser-Hillas function in
R = sqrt(lambda/|X0'|), L = sqrt(|X0'| lambda), X0' = X0 - Xmax, and the sentence below it ("a Gaussian with standard
deviation L, multiplied by a term that distorts it, with the asymmetry governed by R"): claim scifix:C31. PDG RPP
2024, 40. Statistics (rev. August 2023, G. Cowan), new source scifix:S13, read at page level: sec. 40.2 p. 2
(consistency, bias) and sec. 40.2.3 (least squares, linear model, eqs. (40.21)-(40.23)): claim scifix:C32. PDG RPP
2024, 34. Passage of Particles Through Matter (scifix:S01), p. 16: eq. (34.16) and the text below it (no numerical
accuracy; "for large Z and small x the beta-dependence is not well represented"). Geant4 11.4.3 sources:
`G4Cerenkov::GetAverageNumberOfPhotons` (Rfact = 369.81/(eV cm), yield proportional to charge^2), the OpNovice2
example, and TestEm5 `Run::ComputeMscHighland` (13.6 MeV z sqrt(t)(1 + 0.038 ln t)/(beta p c), without z^2/beta^2
in the logarithm).

**Oracles.**

- DR-WP1-01, `CherenkovChargeTests::test_yield_matches_geant4_cerenkov_for_protons_and_alphas`
  (independent implementation, basis third-party, `expected_from` third-party-definition). Geant4 11.4.3 OpNovice2,
  built from the release's example source against the local install; the only change prints the integer total of
  Cerenkov photons (output only). Box of G4_Galactic (no energy loss, delta rays or hadronic interactions) with a
  constant RINDEX 1.05 over 2.0-2.5 eV, world G4_AIR without RINDEX, primary from x = -999.95 mm along +x (path
  199.995 cm), `/gun/momentumAmp`, 2000 events per row, seeds 1101-1601. Totals frozen in the test: p 40 GeV/c
  6836393, alpha 25183431; 20 GeV/c 6728768, 18180150; 12 GeV/c 6465855, 1616253. The script with N0 = 369.81 x 0.5
  per cm gives 3419.60 / 12587.20, 3364.23 / 9092.12, 3232.99 / 807.47 against the Geant4 means 3418.20 / 12591.72,
  3364.38 / 9090.08, 3232.93 / 808.13 (largest offset 1.8 Poisson sigma; tolerance 5 sigma plus 1e-6). On the parent
  the He4 yield has no z^2 and is 4 times low.
- DR-WP1-02, `GaisserHillasPropertyTests::test_profile_reaches_the_gaussian_limit_at_large_x_max`
  (analytic, basis locator S07/C31, `expected_from` general-result). For x_max 1e12 and 1e15, lambda 20, 60, 300
  (R = 1.4e-7 to 1.7e-5) and t = +-0.5 to +-3: |ln N + t^2/2| <= (2/3)|t|^3 R + 2 eps |t|/R + 1e-12 (the leading
  distortion t^3 R/3 bounded for |tR| <= 1/2, plus the fix's rounding). The parent's form misses by up to 8e-4.
- DR-WP2-06-CALO, `ScriptPhysicsOracleTests::test_calorimeter_toy_study_recovers_the_truth_for_several_term_sets`
  (analytic, basis locator S13/C32, `expected_from` general-result). Term sets (a, b, c) = (0.10, 0.20, 0.0070),
  (0.05, 0.10, 0.010), (0.15, 0.30, 0.020), 2000 toys each, 2% relative scatter, no per-point errors: real terms in
  at least 99% of the toys and each mean within 0.003 truth + 5 Monte Carlo sigma. The expected values are the toys'
  truth; the generator uses the same E9 model as the fit, so a mistranscribed model would cancel here, but the
  defect (the weighting) does not.

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/hep_detector/test_hep_detector_audit.py::CherenkovChargeTests::test_yield_matches_geant4_cerenkov_for_protons_and_alphas` (DR-WP1-01, `4aebc0be` / `70f7fbcb`) | independent implementation (third-party: Geant4 11.4.3) | fail (assertion, 3 of 3 subtests: He4 201.87 against 808.13 at 12 GeV/c, 2273.03 against 9090.08, 3146.80 against 12591.72) | pass | no | CI lock |
| `tests/skills/hep_detector/test_hep_detector_audit.py::GaisserHillasPropertyTests::test_profile_reaches_the_gaussian_limit_at_large_x_max` (DR-WP1-02, `70f7fbcb` / `0f3a2e3f`) | analytic (general result, locator S07 eq. (3.1) p. 5) | fail (assertion, 27 of 48 subtests: all 24 at x_max 1e15, 3 at 1e12; up to 7.9e-4 against bounds of 2e-8 to 1e-5) | pass | no | CI lock |
| `tests/skills/hep_detector/test_hep_detector_audit.py::ScriptPhysicsOracleTests::test_calorimeter_toy_study_recovers_the_truth_for_several_term_sets` (DR-WP2-06-CALO, `f6a64702` / `6c793363`) | analytic (general result, locator S13 sec. 40.2 p. 2) | fail (assertion: 446 of 2000 toys without a real term for (0.10, 0.20, 0.0070), limit 20; the other two sets pass) | pass | no | CI lock |

Method as in SCIFIX-PLAN-B3-B6: a detached worktree of the source repository per commit (removed after the run), the
current test file copied in under the test folder and file name of that commit, with the skill folder name mapped
to the one of that commit (`docs/maintenance.md`), no other change; each node run alone with `python -m unittest`.

**Grades.** DR-WP1-01: C3 kept, the transcription gap closed; D0 -> D1 (the new oracle fails on the parent by
assertion, the two older oracle nodes still error there, so D2 is out of reach under the D-scope rule). DR-WP1-02:
C3 D2 kept, gap closed. DR-WP2-06-CALO: C3 D1 kept (the closure oracle still passes on the parent), gap closed.
DR-WP2-06-MS: C3 D0 unchanged; its gap now says what was searched. No printed crossover, MDR or beta(R) value for a
stated stack was found; Geant4's TestEm5 Highland value uses the older logarithm without z^2/beta^2, and its
simulated angle could be compared only with a tolerance on the beta dependence that no located source gives (PDG
2024 states none), so it was not run as evidence. The maintainer decides between more evidence and a lower grade.

## CROSS-ARTIFACT-PHASE0 (2026-10-22, Python 3.13.2 on macOS arm64; branch `feat/cross-artifact-phase0` from main `460919eb`, 0.24.1, unreleased)

Phase 0 (release R1) of `docs/dev/cross-artifact-check/cross-artifact-check-architecture.en.md`; gate record
`docs/dev/cross-artifact-check/decision-phase0.md`.

| Check | Result |
|---|---|
| Suite 1.0.0 outcomes, main 0.24.1 against this branch | 22 cases (positive, chain, ratio, model, run chain, run campaign and every probe variant), 403 obligations: identical (obligation, state, reason); both outcome files SHA-256 `00655e16…` |
| `rule_registry.py check` | pass: registry 1.1.0, 23 rules with current source digests, 76 V cases, 85 V parts passing (V72–V76 new) |
| Analysis-check tests (`test_analysis_check_*`, formerly `test_v63_*`) | 227 pass (205 existing, 22 new in `test_analysis_check_foundations`) |
| Gap probes `test_cross_artifact_check_gap_probes` | G10, G11, G18, G19, G20 pass; 15 expected failures (G1–G8 except G9, G12–G17, G22), each checked to fail by assertion for its stated reason; G9 and G21 skipped with reason |
| Rename (WP-R) `rename_analysis_check_ids.py --verify` | ok: no leftovers, 169 registry test IDs resolve, stub present, derived-file checks pass; a second `--apply` changes nothing; 23 moves |
| Full suite before the rename (`0c1dd20c`) | 26 pass, 1 fail (`unittest`: `test_subprocess_timeouts`, six new calls without timeout); 4955 tests |
| Full suite after the rename (`cecc4dcb`) | the same failure plus `test_preservation_checklist_c3` (`--snapshots` wording, in `unittest` and `ams_optional`): a documentation edit of that commit, not the rename; skipped sets identical (187) |
| Full suite on the branch head (`890f8481`, both fixed) | 27 pass, 0 fail; 4955 tests in 410 modules, 0 failures, 187 skipped |
| ruff 0.16.10, mypy 2.4.0 (CI pins) on `core/` and `contracts/` | pass |

Changed assertions of existing tests (registry 1.1.0): `test_analysis_check_rule_registry` expects V01–V76
(was V01–V71) and 76 V cases in the CLI count (was 71); `test_complete_new_rule_is_accepted` registers an
implementation and source digest for its hypothetical rule, which registry 1.1.0 requires.

Not run: the slow tier, live routing (no skill text changed except one reference's wording), the value gate
(Phase 1). Skipped tests are unverified, not passed.

## SCIFIX-PLAN-A2 (2026-10-22, CI lock venv: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch; worktree branch `scifix/pr-1-identity-runtime-dir` from main `a53af7e0`)

Sci-fix improvement plan v3, PR-1 (A2; findings F-03, F-25). `core/protected/identity.py` gains
`RUNTIME_ROOT_DIRS = {".in_use"}`, matched at the plugin root only (both the `git ls-files` path and the walk of an
installed copy); `verify()` adds an `identity.bytecode_unverified` warning when any `.pyc` is present and keeps its
verdict. Guard semantics are unchanged: identical means the same code.

| Check | Result |
|---|---|
| New tests on the parent `identity.py` (`test_identity_and_versions`: root `.in_use/` kept out, git checkout path, bytecode warning; `test_protected_entry_points`: qualified copy with root `.in_use/` accepted, nested `core/.in_use/x.py`, `adapters/demo/assets/json.py`, `contracts/tool_contracts/new.json` refused) | fail (3 failures, 1 error) |
| Same tests on the fix | pass |
| The installed 0.23.0 copy in the Claude Code plugin cache (read only; holds `.in_use/`) | parent: `unreleased`; fix: `{"release": "0.23.0", "digest": "3adfaf6f…"}`, `verify` identical with no differences |

| `run_all_checks.py --no-cli --jobs 6`, CI lock, worktree head | 24 pass, 1 fail, 2 skipped (CLI host checks); 4799 tests, 4549 pass, 1 failure, 249 skipped. The failure: `test_subprocess_timeouts` (the new git-checkout test called `git` without `timeout=`); fixed, and that module and `test_identity_and_versions` rerun: pass |

Not changed: `.pyc` files stay outside the identity (F-25); a full fix (no bytecode, or hash-based `.pyc`) needs its
own assessment.
## SCIFIX-PLAN-C3-C4 (2026-10-22, CI lock venv: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch; branch `scifix/pr-9-scan-surface` from main `168ede40`)
## SCIFIX-PLAN-C1-C2-C6 (2026-10-22, CI lock venv; branch `scifix/pr-8-governance` from main `bc8ac2e6`)

Sci-fix improvement plan v3, PR-8 (C1, C2, C6).

| Check | Result |
|---|---|
| Regression warning on the shipped advisories before `regression_of` | 2: SFA-2026-002 introduced by `811f02b6` (the fix of SFA-2026-020), SFA-2026-003 by `f7846755` (the fix of SFA-2026-021); recorded, then 0 warnings |
| S1 and S2 entries without an advisory | 7, each with `advisory_waiver`: CLS-LOGINTERP (example script only, commit `6e7274c3`), CLI-MISSING-INPUT-EXIT2, ADAPTER-MISSING-DEPENDENCY, PYHF-REJECTED-STATUS (status of input that produced no result; 0.23.0 release check), SCAN-VERDICT-ORDER, SCAN-MISSING-MARKER, ADVISORY-MATCH-V2 (shadow-mode report) |
| Missing advisory numbers | SFA-2026-012, -013, -026 to -029: no commit ever held or mentioned them (`git log --all`); README, no tombstones |
| `published` | the UTC time of the commit that added each advisory (SFA-2026-001 to -003 2026-10-20T09:43:20Z; -004 to -035 2026-10-20T14:31:42Z; -036 2026-10-21T20:26:57Z; -037 2026-10-22T00:37:17Z; -038 2026-10-22T01:47:39Z) |
| Schemas | the ledger and all 32 advisories validate; broken copies are refused (11 cases); only implemented keywords, no `$ref` |
| New tests (`test_scifix_advisories`: timestamps, regression warning; `test_scifix_ledger`: waivers, regression_of; `test_scifix_schemas`) | pass |
| `run_all_checks.py --no-cli --jobs 4`, CI lock (before the rebase on main) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4863 tests, 4612 pass, 0 failures, 251 skipped |

## SCIFIX-PLAN-C3-C4 (2026-10-22, CI lock venv: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch; branch `scifix/pr-9-scan-surface`, stacked on `scifix/pr-5-advisory-v2`)

Sci-fix improvement plan v3, PR-9 parts C3 and C4.

| Check | Result |
|---|---|
| `release_manifest.py backfill --commit hep-research--v0.3.0` | 955 files, digest `d75dbfdd1d3091df…`, commit `351029c0bfdd…` (the root import) |
| `release_manifest.py backfill --commit 9870a35a` (0.4.0, never tagged: the merge of PR #6, whose `plugin.json` says 0.4.0) | 1013 files, digest `a755680f6011b12f…`, commit `9870a35ab49e…` |
| `check-published` on the branch | pass; both backfilled manifests identical to their tag or commit; no pending tags; no unrecorded tags left |
| `scifix_advisories.py check` with the two manifests | 0 problems; the fixed-release rule now also checks 0.4.0 against 0.3.0 for SFA-2026-008 to -011, -030, -031 (all changed) |
| `tests/tools/test_release_manifest.py` (new: backfill from an untagged commit, checked against it, its record may not change, a short commit is refused) | pass, 10 tests |
| C3: `check_routing_static.py`, `check_ownership.py`, `measure_entrypoints.py` after the reference-index rule | pass; reference inventory regenerated |
| `run_all_checks.py --no-cli --jobs 6`, CI lock, after the rebase on main `168ede40` | 25 pass, 0 fail, 2 skipped (CLI host checks); 4856 tests, 4605 pass, 0 failures, 251 skipped |

Not run: live routing for the C3 rule (maintainer decision 2026-10-22: the reference-index option, no paid run). The
rule sits in a reference, not in the SKILL.md body, so it triggers only when the reference is read.

## SCIFIX-ADVISORY-V2 (2026-10-22, CI lock venv: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch; branch `scifix/pr-5-advisory-v2`, stacked on `scifix/pr-4-execution-trace`)

Sci-fix improvement plan v3, PR-5 (A1 change 1), sci-fix ADVISORY-MATCH-V2 (S2, C2, D2). Fix `5cb720b8`, parent
`c3d9208a` (PR-4's head) in a detached worktree with the fix commit's `tests/tools/test_scifix_advisories.py` and
`tests/tools/fixtures/advisory_matrix.json` copied in; the worktree was removed after the run.

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/tools/test_scifix_advisories.py::ThreeValuedMatch::test_every_match_of_up_to_two_groups_of_up_to_two_conditions` | exhaustive (156 matches and `[]`) | error (`match_verdict` absent: the /1 scan has no undecided state) | pass | no | CI lock |
| `tests/tools/test_scifix_advisories.py::AcceptanceMatrix::test_every_advisory_cell_by_cell` | behavioral (31 advisories, hand-written verdicts) | fail by assertion for 11 advisories: SFA-2026-001, 002, 004, 006, 010, 020, 023, 025, 030, 031, 033 | pass | no | CI lock |

The acceptance matrix (`tests/tools/fixtures/advisory_matrix.json`) gives, per advisory, synthetic artifacts in and out
of range, with and without a trace, positive and negative, and for SFA-2026-020 one written under contracts 2.4.0,
before its fields existed; every verdict is written by hand from the advisory's `applies_to`. A mutation check (two
expectations altered) made the matrix test fail for exactly those two advisories. The plan's two `hadd` jobs of F-01
(0.12.0 and 0.21.0, digest-consistent) get no finding from any shipped advisory.

Migration of the 31 advisories (each read against the code that writes the artifact):

| Class | Advisories | Basis |
|---|---|---|
| outputs only (`artifact_types: []`) | 001, 030 (blinding scanner), 014 to 019 (detector scripts), 036 (`anisotropy.py`), 037 (`estimate_training_memory.py`) | the affected code prints a report and writes no artifact, and no artifact writer imports it within the range (checked: the writers' imports) |
| `match: []`, possibly affected (no trace) | 004, 006, 010 | `result_artifact.py` writes the statistical-result from a core/stats CLI's JSON printed in another process; no field names the code (the listed keys were required, or do not show it) |
| `match: []` | 023, 025 (ml-artifact), 033 (communication) | the keys were required in every artifact of the type; the affected scripts run apart from the writer |
| discriminating fields | 002, 020 (`splits.overlap_check.tool` matching `check_split_integrity`, or `splits.manifest`; 020 `unknown_before` 2.5.0, when they appeared), 003, 021 (`calibration`), 005, 009 (`significance`), 007 (`convergence`, `sampler`), 008 (`construction`), 011 (`results`), 022 (`domain_shift`), 024 (`weights`), 032, 034, 035 (`occurrences`), 031 (`tools[*].name` equal to `hep-research core/partition runner`, the name in 0.3.0's `batch_campaign.py`, plus `local_partition.py` outputs) | each top-level key existed in the extension schema at every release tag in the advisory's range (checked against the tags) |

Full gate: `run_all_checks.py --no-cli --jobs 4`, CI lock, branch head: 25 pass, 0 fail, 2 skipped (CLI host
checks); 4828 tests, 4579 pass, 0 failures, 249 skipped.

Expected effect, as the plan states: findings on old artifacts do not drop. The six `match: []` advisories now say
"possibly affected (no trace)" where they said "affected"; the outputs-only ones no longer match any artifact.

## SCIFIX-PLAN-A1-TRACE (2026-10-22, CI lock venv: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch; E2 venv for fixtures and examples; branch `scifix/pr-4-execution-trace`, stacked on `scifix/pr-3-scan-order`)

Sci-fix improvement plan v3, PR-4: A1 change 2 (contracts 3.5.0, `contracts/trace.py`, maintainer decision
2026-10-22; `core/trace.py`, re-exported by `contracts/trace.py`) and A4, sci-fix SCAN-MISSING-MARKER (S2, C2, D2). Fix `01dd65a6`, parent `8e7517da` (PR-3's head) in a detached
worktree with the fix commit's `tests/tools/test_scifix_advisories.py` copied in; the worktree was removed after the run.

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/tools/test_scifix_advisories.py::ProjectScan::test_missing_markers_and_empty_values_do_not_show_the_code_ran` | exhaustive (14 value classes) | fail, 4 of 14 subtests by assertion (`unknown`, `not-applicable`, `not-provided`, `0`) | pass | no | CI lock |

| Check | Result |
|---|---|
| `tests/contracts/test_trace.py` (snapshot without tests/, tags per envelope, schema accepts and refuses, a producer subprocess records its own script and not the CLI it read) | pass, 6 tests |
| Writers that add the trace | 12: import_published_table, manage_literature, result_artifact, bayes_diagnostics, build_response, mix_period_responses, check_geant4_study, run_workflow, write_ml_artifact, hepdata_record, batch_campaign, g4common; not dragon2_run.py, dragon2_to_prediction.py, geant4_build.py (they import no contracts) |
| Contracts 3.5.0 | `CONTRACTS_VERSION`, vocab, the two pinned tests; `make_fixtures.py` (E2): 40 valid, 125 invalid, 27 unresolved, 6 warning fixtures; three theory-profile `make_artifacts.py`; three assets |
| Examples regenerated (E2; `bc-propagation-fit` with the CI lock) | version strings, the hashes that cover them, the writers' `code_paths`, and `check_geant4_study.py`'s own hash; `unfolding-coverage` drifted at 1e-14 and was restored |
| `run_all_checks.py --no-cli --jobs 4`, CI lock, at `deb21207` (before the rebase on the merged PR-2 and the move of the trace into core) | 23 pass, 2 fail, 2 skipped (CLI host checks); 4814 tests, 4564 pass, 1 failure, 249 skipped. Both failures were the retired-name defect fixed in PR-2 (`test_check_retired_names`, `retired_names`); after the rebase both pass. The rebased head with the trace in core runs in CI |

Limit found while implementing: `result_artifact.py`, the statistical-result writer, wraps the JSON a core/stats CLI
printed in another process, so its `code_paths` never shows `core/stats/*`; an advisory about core/stats code must
match on fields the CLI output carries, or say that no field shows it (plan PR-5).
## SCIFIX-PLAN-B2-B5-B7 (2026-10-22, CI lock venv; branch `scifix/pr-7b-ledger-report` from main `40a21d1a`)

Sci-fix improvement plan v3, the rest of PR-7: B2 (report only), B5, B7.

| Check | Result |
|---|---|
| `expected_from` of the 64 independence records (classified by hand from each record's detail) | third-party-definition 29, transcribed-formula 15, exhaustive 15, printed 4, general-result 1 (PERIODICITY-REFIT's size = alpha); DR-WP2-06-CALO's `numpy.linalg.lstsq` record is transcribed-formula (a third-party solver fitting the repository's model) |
| C3 entries with transcribed formulas only | DR-WP1-01, DR-WP1-02, DR-WP2-06-CALO, DR-WP2-06-MS (the plan expected DR-WP1-02 and DR-WP2-06-MS); `gaps` added, grades unchanged |
| `tools/scifix_ledger.py report` | 27 entries below their minimum; 18 S1 entries without `review`; 5 S3 entries below their minimum: DR-REFS, ML-REFS, REVIEW-REFS (sources never itemized in the ledger; not transcribed here), REVIEW-CODE-WARN-TAIL and -MANIFEST (internal only) |
| `documentation_fixes` | `sources_with_locators` text kept as `note`; `sources` itemized where the ledger named them (REVIEW-REFS-2, -3, REVIEW-CODE-WARN-NEGW, STATUS-REFUSED-MEANING and the two internal-only entries) |
| `tests/tools/test_scifix_ledger.py` (new: expected_from and the transcription report, S3 sources, review format and report) | pass, 21 tests |
| `run_all_checks.py --no-cli --jobs 6`, CI lock | 25 pass, 0 fail, 2 skipped (CLI host checks); 4855 tests, 4604 pass, 0 failures, 251 skipped |

Not done: no S1 entry is signed off (a person's act); the sources of DR-REFS, ML-REFS and REVIEW-REFS are not
itemized from their VALIDATION records.

## SCIFIX-PLAN-B3-B6 (2026-10-22, CI lock venv: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, SymPy 1.14.0, mpmath 1.3.0, no pyhf, ArviZ, pdg or torch; E2v: NumPy 2.5.3, SciPy 1.18.1, SymPy 1.14.0, pyhf 0.7.6, PyTorch 2.14.1, no ArviZ or pdg; branch `scifix/pr-7-d-axis`, stacked on `scifix/pr-6-evidence-sources`)

Sci-fix improvement plan v3, PR-7 parts B3 and B6 (F-11, F-14, F-23). Maintainer decisions of 2026-10-22, now in
`docs/maintenance.md`: D2 needs a parent record (fails on the parent, passes on the fix) for every oracle node named
by the entry's `independence` records, at most D1 when only other regression tests have one (the D-scope rule); D3
also needs a killed `revert` mutant.

**B3, the D axis as data.** Each ledger entry now has `commits` (parent, fix, follow_up; 40-hex, resolved with
`git rev-parse` in the source repository from the short hashes in its note, its VALIDATION section or its
advisory's `fixed_commit`; where none names the parent it is the fix's first parent, and the ANISO-CL-RANGE fix
`1853e619` is the commit whose message names the entry), `parent_records` (133: 87 transcribed from the sections
they name, 46 from the reruns below; each with `requires`, found by hiding one package at a time as in
SCIFIX-PLAN-B1-B4, or copied from the node's independence record) and `mutants` (46, transcribed). Rows
transcribed: every parent failure the sections record by assertion or by an exception they name as the defect
itself; rows whose parent failure was an import error or a function, argument or output key new in the fix are
left out unless the node is an oracle (then recorded as `error`); the core/stats guide tests (a module list) are
left out. A failure on the parent is `error` when the test could not reach the parent's code. `evidence_tests` is
now the list of nodes used (independence and parent-record nodes); files without a recorded node
(`test_properties.py`, `test_published_tables.py`, `test_constant_literals.py` and others) left the lists.
`tests/tools/test_scifix_ledger.py` recomputes D2 and D3 from the records.

**Reruns.** Every oracle node without a parent record was run on its parent and fix commit: a detached worktree of
the source repository per commit (`git worktree add --detach`, removed after the run), the current test file (and
its fixtures or test helpers) copied in, skill and test folder names mapped to those of the commit where they
differ (`docs/maintenance.md`), each node run alone with `python -m unittest`. Adaptations, all within the
adapted-parent rule: F01-F03 add `core/stats/fit_diagnostics.py` and `tail_estimation.py` from the fix (new modules);
ROBUST-CAMPAIGN guards the import of `SubmitAmbiguous`, `SubmitRefused` (added after the fix). For F02 and F03 the
adapted run is not a valid record: the added modules hold the oracles' code under test, so the unadapted run
(import error) is recorded. Where an entry then had no valid parent failure at all, the fix commit's own changed
test files were run on its parent the same way (the SCIFIX-PARENT-RECORDS method; 5 fix commits).

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/examples/test_stats_benchmarks.py::PublishedLikelihood::test_crossing_at_zero_events_is_ln_20_for_any_background` (CLS-LOGINTERP, `90388aa0` / `99a18fd8`) | symbolic | error (AttributeError: `_crossing` is new in the fix) | pass | no | CI lock |
| `tests/core/test_stats_p0_regressions.py::T01LikelihoodDomain::test_lnl_against_scipy_and_sympy_poisson` (F01, `1d42271a` / `9f1ee4a9`) | independent implementation, symbolic | fail (assertion: ln L at mu = -1 is 0.0, not below -1e300; adapted, adds new modules) | pass | no | CI lock |
| `tests/core/test_stats_p0_regressions.py::T02T03ToyTails::test_clopper_pearson_against_scipy` (F02) | independent implementation | error (import: `tail_estimation` is new in the fix); adapted: pass, the added module is the code under test | pass | no | CI lock |
| `tests/core/test_stats_p0_regressions.py::T02T03ToyTails::test_extreme_exact_tail_in_log_space` (F02) | independent implementation | error (as above); adapted: pass | pass | no | CI lock |
| `tests/core/test_stats_p0_regressions.py::T02T03ToyTails::test_zero_exceedance_bound_solves_the_binomial_equation_symbolically` (F02) | symbolic | error (as above); adapted: pass | pass | no | CI lock |
| `tests/core/test_stats_p0_regressions.py::T04AnalyticOracle::test_converged_fits_match_a_third_party_minimum` (F03) | independent implementation | error (as above; `newton_fit` in the new `fit_diagnostics`); adapted: pass | pass | no | CI lock |
| `tests/skills/hep_statistics/test_bayes_diagnostics.py::Diagnostics::test_ar1_bulk_ess` (BAYES-T24, `bb0774f0` / `d161b3b7`) | analytic | pass | pass | no | CI lock |
| `tests/core/test_stats_counting_asymptotic_oracles.py::T09ExactCounting::test_monotone_upper_end_against_an_independent_envelope` (FC-MONOTONE, `b3734189` / `04338bbf`) | independent implementation | error (TypeError: `fc_interval`'s `monotone` argument is new in the fix) | pass | no | CI lock |
| `tests/core/test_stats_poisson.py::FeldmanCousinsTests::test_monotone_construction_matches_entries_where_the_plain_one_dips` (FC-MONOTONE, current test; confirms SCIFIX-PARENT-RECORDS) | published | fail (assertion: 1.08 != 1.26 at (0.9, 0, 2.0)) | pass | no | CI lock |
| `tests/core/test_stats_poisson.py::UpperTailTests::test_matches_third_party_and_symbolic_tails` (POISSON-SF, `04338bbf` / `a2adc126`) | independent implementation, symbolic | error (AttributeError: `poisson_sf` is new in the fix) | pass | no | CI lock |
| `tests/core/test_stats_linalg.py::EigenvalueOracleTests::test_verdict_matches_the_eigenvalues_at_any_scale` (COV-NOREPAIR, `a2adc126` / `6a81109c`) | independent implementation | error (import: `core.stats._linalg` is new in the fix and is the code under test) | pass | no | CI lock |
| `tests/core/test_stats_linalg.py::ExhaustiveDefinitenessTests::test_verdict_over_every_rational_unit_diagonal_3x3` (COV-NOREPAIR) | exhaustive | error (as above) | pass | no | CI lock |
| `tests/core/test_stats_poisson.py::MeanLimitTests::test_ends_beyond_500_against_third_party_and_symbolic_poisson_cdfs` (POISSON-500, `6a81109c` / `b7b7825a`) | independent implementation, symbolic | fail (assertion, 5 subtests: upper end 0.799 of the SciPy root) | pass | no | CI lock |
| `tests/core/test_constants.py::PdgPackageTests::test_bundled_masses_equal_the_package` (TH9-MASSES, `84c0a68c` / `23910085`) | published | skip (pdg not installed) | skip | yes | CI lock |
| `tests/skills/hep_detector/test_hep_detector_audit.py::SpeciesMassPropertyTests::test_binding_energies_agree_with_ame2020_and_the_pre_fix_table_does_not` (TH9-MASSES) | published | fail (assertion: d binding residual 5.7 eV against 1.42 eV, the pre-fix table) | pass | no | CI lock |
| `tests/skills/hep_detector/test_hep_detector_audit.py::CherenkovChargeTests::test_helium_yield_scales_with_z_squared` (TH9-MASSES) | analytic | fail (assertion: 68.07557497 against 68.07557493, tolerance 1e-9) | pass | no | CI lock |
| same test (DR-WP1-01, `4aebc0be` / `70f7fbcb`) | analytic | error (KeyError: the CLI has no `charge` output on the parent) | fail (assertion: the same 4e-8 offset; it passes from TH9's fix `23910085` on) | no | CI lock |
| `tests/skills/hep_detector/test_hep_detector_audit.py::CherenkovChargeTests::test_yield_matches_the_frank_tamm_spectrum_integrated_in_wavelength` (DR-WP1-01) | independent implementation | error (import: `core.constants`, added after the fix) | error (same) | no | CI lock |
| `tests/skills/hep_detector/test_hep_detector_audit.py::GaisserHillasPropertyTests::test_profile_against_high_precision_and_the_old_form` (DR-WP1-02, `70f7fbcb` / `0f3a2e3f`) | analytic, independent implementation | fail (assertion, 73 subtests: ratio 1.000003 against a 1e-10 tolerance) | pass | no | CI lock |
| `tests/skills/hep_detector/test_hep_detector_audit.py::ScriptPhysicsOracleTests::test_calorimeter_toy_study_unweighted_fit_is_unbiased_and_matches_weighted_lstsq` (DR-WP2-06-CALO, `f6a64702` / `6c793363`) | independent implementation | fail (assertion: the fitted squared terms differ from weighted lstsq at rtol 1e-10) | pass | no | CI lock |
| `tests/skills/hep_detector/test_hep_detector_audit.py::ScriptPhysicsOracleTests::test_calorimeter_fit_closure_and_energy_scale_covariance` (DR-WP2-06-CALO) | analytic | pass | pass | no | CI lock |
| `tests/skills/hep_detector/test_hep_detector_audit.py::PidElectronAndUnitTests::test_water_uses_the_pdg_mean_excitation_energy` (DR-WP2-06-PID) | published, analytic | fail (assertion: 2.0506 against 2.0390, I = 75 eV) | pass | no | CI lock |
| `tests/skills/hep_detector/test_hep_detector_audit.py::ScriptPhysicsOracleTests::test_crossover_and_mdr_with_beta_of_rigidity_against_their_closed_forms` (DR-WP2-06-MS) | analytic, independent implementation | error (TypeError, 45 subtests: `summarize`'s `mass_gev` argument is new in the fix) | pass | no | CI lock |
| `tests/core/test_blinding.py::RenderingOracleTests::test_every_claimed_rendering_is_found_in_every_claimed_encoding` (BLINDING-SCANNER, `d7148901` / `b6334c04`) | independent implementation | error (AttributeError: `_significant_digits`, added later) | fail (assertion, 420 subtests: the test reads the later rounding-zeros rule) | no | CI lock |
| `tests/core/test_partition_safety.py::IndependentClosureTests::test_merged_campaign_equals_the_closed_form` (ROBUST-CAMPAIGN, `f5070718` / `f7b677c9`) | independent implementation | pass (import guarded) | pass (import guarded) | no | CI lock |
| `tests/skills/hep_authoring/test_review_fixes2.py::ReviewFixes2NumbersGenerated::test_tokens_equal_the_numbers_put_into_generated_passages` (RC-A2, `2b439e74` / `ffd7804e`) | independent implementation | error (import: `communication_lib.numbers`, added later) | fail (assertion: the test reads the later tokenizer) | no | CI lock |
| same test (RC-A3, `ffd7804e` / `dc97a00c`) | independent implementation | fail (assertion) | pass | no | CI lock |
| `tests/skills/hep_authoring/test_review_fixes2.py::ReviewFixes2Rounding::test_no_rule_classification_exhaustively_against_integer_arithmetic` (RC-A5, `111585dd` / `7e0ee239`) | exhaustive | error (import: `_rounds_somehow` is new in the fix) | pass | no | CI lock |
| `tests/skills/hep_authoring/test_review_fixes2.py::ReviewFixes2Rounding::test_rounding_rules_exhaustively_against_integer_arithmetic` (RC-A6) | exhaustive | error (TypeError: the parent's `_round` returns None for the rule form `decimals:n:mode`, new in the fix) | pass | no | CI lock |
| `tests/skills/hep_ml/test_audit_split_tools.py::GroupKeyTests::test_numeric_forms_of_an_integer_are_one_group_exhaustively` (ML-SPLITS, `2b439e74` / `811f02b6`) | exhaustive | error (import: `canonical_key` is new in the fix; the test calls it) | pass | no | CI lock |
| `tests/skills/hep_ml/test_audit_calibration_identity.py::SampleIdentityPropertyTests::test_event_id_check_is_exhaustively_right_over_all_subset_pairs` (ML-CALIBRATION, `811f02b6` / `f7846755`) | exhaustive | pass | pass | no | CI lock |
| `tests/skills/hep_ml/test_audit_calibration_identity.py::SampleIdentityPropertyTests::test_validator_names_one_sample_under_every_spelling_of_its_path` (ML-CALIBRATION) | independent implementation | fail (assertion, 5725 subtests) | pass | no | CI lock |
| `tests/skills/hep_ml/test_domain_shift_report.py::ShiftCarriedByNuisance::test_fit_against_pyhf` (ML-K05, `879e0733` / `7b32b109`) | independent implementation | error (TypeError: `shape_model`'s `b_up` argument is new in the fix) | pass | no | E2v |
| `tests/skills/hep_ml/test_audit_domain_method.py::DomainModelTests::test_flag_rates_match_the_split_conformal_rank` (ML-DOMAIN, `50d3e922` / `7011baaf`) | analytic | error (AttributeError: `DomainModel` is new in the fix) | pass | no | E2v |
| `tests/skills/hep_ml/test_audit_domain_method.py::DomainModelTests::test_false_positive_interval_is_the_beta_quantile_clopper_pearson` (ML-DOMAIN) | independent implementation | error (KeyError: `false_positive_rate_interval_68` is new in the fix) | pass | no | E2v |
| `tests/skills/hep_ml/test_audit_metric_layer.py::MetricTests::test_asimov_against_pyhf` (ML-NEGWEIGHTS, `153307a6` / `ef5d068f`) | analytic | pass | pass | no | E2v |
| `tests/skills/hep_ml/test_audit_metric_layer.py::MetricTests::test_cell_resampling_matches_a_brute_force_reading_of_eq_2_2` (ML-NEGWEIGHTS) | independent implementation | error (AttributeError: `cell_resample` is new in the fix) | pass | no | E2v |
| `tests/skills/hep_ml/test_audit_small_corrections.py::SmallSeedComparisonTests::test_student_t_quantile_against_scipy_and_the_published_table` (ML-SMALL-C10, `f5cc59a7` / `fd637dcc`) | independent implementation | error (AttributeError: `student_t_quantile` is new in the fix) | pass | no | CI lock |

**Fix commits' own test files on their parents** (paths as at the fix commit, mapped to today's; only the rows
that decide a record are listed; the rest pass on both or need code new in the fix):

| Fix commit | Result |
|---|---|
| `70f7fbcb` (DR-WP1-01) | no valid parent failure: the z^2 test (KeyError `charge`), the `mass:charge` species syntax and `--rigidity` are all new in the fix; 1 test passes on both |
| `ffd7804e` (RC-A2) | `test_communication_audit.py::ManuscriptOccurrences::test_value_not_in_passage_is_an_error_compared_as_a_number` fails by assertion on the parent, passes on the fix; `test_review_fixes2.py` does not import on the parent; 21 pass on both |
| `7e0ee239` (RC-A5, RC-A6) | `ReviewFixes2Rounding::test_no_rule_accepts_only_a_rounding_of_the_source` (RC-A5) and `::test_default_rounding_is_half_up_and_half_even_is_opt_in` (RC-A6) fail by assertion on the parent, pass on the fix; two tests raise InvalidOperation (RC-A15, not a ledger entry), one needs `_rounds_somehow`; 16 pass on both |
| `7b32b109` (ML-K05) | `tests/contracts/test_ml_mutation_probe.py::MutationProbe` `test_legacy_artifacts_keep_their_outcome_and_strict_reports`, `test_report_silent_count`, `test_rows_reach_their_level_natively` fail by assertion on the parent (row M25, the domain-shift record), pass on the fix; 2 pass on both (E2v) |
| `7011baaf` (ML-DOMAIN) | `DomainModelTests::test_cli_groups_and_categorical`, `TrainingAndInferenceTests::test_inference_flags_the_broken_constraint_and_scores_no_non_finite_row` and `test_training_pipeline.py::TrainClassifierPipelineTests::test_inference_flags_and_rejects_out_of_domain` fail by assertion on the parent, pass on the fix; 9 need `DomainModel` or other code new in the fix; 19 pass on both (E2v) |

**Grade changes (axis D), recomputed from the records:**

| Entry | Severity | D before | D now | Reason |
|---|---|---|---|---|
| CLS-LOGINTERP | S1 | D2 | D1 | symbolic oracle (n = 0, ln 20) errors on the parent |
| F02 | S1 | D2 | D1 | its three oracles test `tail_estimation`, new in the fix |
| F03 | S2 | D2 | D1 | its oracle tests `newton_fit`, new in the fix |
| BAYES-T24 | S1 | D3 | D1 | the analytic AR(1) oracle passes on the parent |
| FC-MONOTONE | S1 | D2 | D1 | the envelope oracle errors on the parent (`monotone` argument new) |
| POISSON-SF | S1 | D2 | D1 | the oracle errors on the parent (`poisson_sf` new) |
| COV-NOREPAIR | S1 | D2 | D1 | both oracles import `_linalg`, new in the fix |
| TH9-MASSES | S1 | D2 | D1 | the PDG oracle skips without pdg (no record) |
| DR-WP1-01 | S1 | D2 | D0 | no test reaches the parent's code (no charge input before the fix) |
| DR-WP2-06-CALO | S1 | D3 | D1 | the closure oracle passes on the parent |
| DR-WP2-06-MS | S1 | D3 | D0 | the oracle errors on the parent (`mass_gev` argument new); no other record |
| BLINDING-SCANNER | S2 | D2 | D1 | the rendering oracle errors on the parent and fails on the fix |
| ROBUST-CAMPAIGN | S2 | D2 | D1 | the closed-form oracle passes on the parent |
| RC-A2 | S2 | D2 | D1 | the oracle errors on the parent and fails on the fix |
| RC-A5 | S2 | D2 | D1 | the exhaustive oracle errors on the parent |
| RC-A6 | S2 | D2 | D1 | the exhaustive oracle errors on the parent (rule form new) |
| ML-SPLITS | S2 | D2 | D1 | the exhaustive oracle calls `canonical_key`, new in the fix |
| ML-CALIBRATION | S2 | D2 | D1 | the event-id oracle passes on the parent |
| ML-K05 | S2 | D2 | D1 | the oracle errors on the parent (`b_up` argument new) |
| ML-DOMAIN | S1 | D3 | D1 | both oracles error on the parent; no revert mutant recorded |
| ML-NEGWEIGHTS | S1 | D3 | D1 | the Asimov oracle passes on the parent, the eq. 2.2 oracle errors; no revert mutant recorded |
| ANISO-WEIGHTED-COV | S1 | D3 | D1 | three of five oracles test `harmonic_covariance` or `AnisotropicNull`, new in the fix |
| ML-SMALL (C2, D2) | S2 | D2 | split | ML-SMALL-C10 C2 D1 (t-quantile oracle errors on the parent); -C24 C1 D0 (its only record errors: the `n_baseline` output is new); -C25 C1 D2; -C26 C1 D2 |

Unchanged: F01, POISSON-500, DR-WP1-02, DR-WP2-06-PID, RC-A3 (D2, every oracle fails on the parent by assertion);
BLINDING-ROUNDING-ZEROS, CANONICAL-KEY-ZERO-FRACTION, SAMPLE-NAME-DOT-SEGMENTS (D3, revert killed); the entries
without oracle nodes or with recorded oracles (ROBUST-MALFORMED, ANISO-CL-RANGE, the six triage entries, the two scan
entries) D2. None was raised. The ledger now has 44 entries: D3 3, D2 17, D1 21, D0 3; 24 are below their
severity's minimum on axis D (S1 13, S2 11), each with a `gaps` line. The F-23 note of ROBUST-MALFORMED is
withdrawn: it has no oracle node, and its regression tests' records hold.

**B6, one fix per entry.** ML-SMALL is a tombstone in the new top-level `superseded` list. Its four code fixes
(CHANGELOG 0.10.0 ML audit, "Small corrections"; the `### ML-SMALL` subsection of SCIFIX-PARENT-RECORDS; commit
`fd637dcc`) are entries of their own: C10 the small-seed comparison (`compare_model_runs.py`; follow-up `db40e842`,
after `fd637dcc` over-corrected), C24 the sculpting baseline, C25 the constant training feature, C26 `model_hash`.
K13 corrected a test, not code, and left the ledger (the tombstone says so). SFA-2026-025 names the four entries;
`scifix_advisories.py check`: 31 advisories, 0 problems.

**Not converted** (in `gaps`): mutants that VALIDATION records only as a count (F03 5, BLINDING-SCANNER 9,
ROBUST-CAMPAIGN 3, RC-A2 7, RC-A5 4, ML-SPLITS 4, ML-CALIBRATION 5, ML-K05 5, the former ML-SMALL 4); the
functions of the mutants of BAYES-T24, DR-WP2-06-CALO and -MS, ML-DOMAIN and ML-NEGWEIGHTS (the file is the
advisory's; `killed_by` names the class or module VALIDATION names); the parent record of
`FeldmanCousinsTests::test_full_published_tables`, a test no longer present under that name.

| Check | Result |
|---|---|
| `tests/tools/test_scifix_ledger.py` (18 tests; 8 new in `StructuredDiscrimination`, each rule with a synthetic ledger that obeys it and ones that break it) | pass |
| Same with `sci-fixes.json` and SFA-2026-025 reverted to the branch's parent | fail: 45 failures, 16 errors (subtests) |
| Same with the new records but the old D grades | fail: 3 (the D2 rule on every lowered entry; the D3 rule on ML-DOMAIN and ML-NEGWEIGHTS) |
| `tools/scifix_advisories.py check` | 31 advisories, 0 problems |
| `tools/check_retired_names.py` | ok |
| `run_all_checks.py --no-cli --jobs 4`, CI lock | 25 pass, 0 fail, 2 skipped (CLI host checks); 4834 tests, 4585 pass, 0 failures, 249 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

The first gate run failed only the README size statement (31.0 MB said, 34.5 MB measured, just beyond the 10%
margin with this change); the statement now says about 2400 files, 34.5 MB.

Added at the rebase onto main after #206: PERIODICITY-REFIT (S1, D3 unchanged) gains `commits` (parent `a53af7e0`
as its record states, fix `573f093a`), three parent records (the three fast oracle and invariant tests fail by
assertion on the parent, E2) and four killed mutants (M1, the revert of the default, among them), transcribed from
VALIDATION PERIODICITY-REFIT; M4 survived and stays in its gaps.

Added at the rebase onto main (after PR-5 merged): ADVISORY-MATCH-V2 (S2) D2 → D1. Its exhaustive oracle
errors on the parent (`match_verdict` is new in the fix), which the D-scope rule does not count; the acceptance matrix
fails there by assertion but is behavioral. Fix `5cb720b8` (PR-5 rebased before merging; was `cc7357ba`), parent `c3d9208a`.

## SCIFIX-PLAN-B1-B4 (2026-10-22, CI lock venv: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, SymPy 1.14.0, mpmath 1.3.0, no pyhf, ArviZ, pdg or torch; E2: NumPy 2.5.3, SciPy 1.18.1, pyhf 0.7.6, PyTorch 2.14.1, no ArviZ or pdg; branch `scifix/pr-6-evidence-sources`, stacked on `scifix/pr-4-execution-trace`)

Sci-fix improvement plan v3, PR-6 (B1, B4; F-10, F-12). Counts recomputed on the branch: 40 ledger entries, 60
`independence` records, 15 of them `locator`, 52 distinct oracle nodes in 24 modules, 16 of which are not in
`run_required_backends.py` `MODULES`.

B1: the *Sources read for locators* table of SCIFIX-LEDGER-REVIEW is now `docs/evidence/scifix-sources.json`
(scifix:S01-S11) and `scifix-claims.json` (scifix:C01-C27, one per locator; index `scifix-index.md`). The PDG
chapter 35 row became two sources (2024 and 2025 editions, S02 and S03); Gaisser and Hillas 1977 is `not-opened`
(S10, cited by no claim); the cosmic-ray review's "does not state the form" is an `absence_search` claim (C26). The
FC-MONOTONE published record points at Table IV, p. 37 (C21), the table read with its page; Table VI has no page in
the reading record and is not claimed. arXiv:2109.07851 (S11, ML-NEGWEIGHTS) was read on 2026-10-22: the v2 abstract
page and pp. 1-5 of the v2 PDF (page level). Eq. (2.2), w_i -> (sum_C w_j / sum_C |w_j|) |w_i| for every event in a
cell grown around a negative-weight seed until its summed weight is non-negative, is in Sec. 2 "Cell Resampling",
p. 3, and p. 4 applies the steps successively to each negative-weight event: this supports the brute-force oracle
(C27), so the basis holds and the grade stays C3. Sec. 2.2 is the nearest-neighbour search (p. 9); the ledger detail
and the `hep_metrics.cell_resample` docstring cited "sect. 2.2" and are corrected.

B4: each record's `requires` was found by hiding one package at a time (a meta-path blocker plus a patched
`importlib.util.find_spec`, also in subprocesses) and running all 52 nodes in E2: hiding numpy changes 27 nodes,
scipy 22, sympy 11, mpmath 12 (sympy needs mpmath), pyhf 3, torch and matplotlib 0; ArviZ and pdg (not in E2) come
from the nodes' own guards (one node each).

| Check | Result |
|---|---|
| `core/evidence/ledger.py --namespace scifix --strict --today 2026-10-22` | pass: 11 sources, 27 claims, 0 errors, 0 warnings; 1 note (S10 cited by no claim) |
| `core/evidence/render_index.py` on `scifix-index.md` | in sync |
| `run_required_backends.py --from-ledger --no-skips`, CI lock | exit 1: 47 pass, 5 unverified (backend missing: pyhf 3, ArviZ 1, pdg 1), 0 environment errors, 0 do not hold, 0 skipped |
| Same without `--no-skips`, CI lock | exit 0, same classes |
| `run_required_backends.py --from-ledger --no-skips`, E2 | exit 1: 50 pass, 2 unverified (ArviZ 1, pdg 1), 0 environment errors, 0 do not hold, 0 skipped |
| Backends in `requires` (pyhf, arviz, pdg) against the required gates' `--require` | each locked: pyhf and arviz by `stats-backends`, pdg by `pdg-cross-check` |
| New tests (5 in `test_scifix_ledger`, 3 in `test_run_required_backends`) with the ledger and the tool reverted | fail: 5 failures and 14 errors (subtests); with `scifix-sources.json` removed as well, 1 failure and 4 errors |
| Same on the change | pass: `test_scifix_ledger` 10 tests, `test_run_required_backends` 6 tests |
| `run_all_checks.py --no-cli --jobs 4`, CI lock | 23 pass, 2 fail, 2 skipped (CLI); 4822 tests, 4572 pass, 1 failure, 249 skipped. Both failures are `retired_names` on the 11 `changelog.name` values of the 0.10.0 detector and ML audits, which spell the retired skill names and which `8f8c66f9` (PR-2) added; a `git archive` of this branch's parent fails the same way |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## SCIFIX-SCAN-VERDICT-ORDER (2026-10-22, CI lock venv: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch; branch `scifix/pr-3-scan-order`, stacked on `scifix/pr-2-advisory-check`)

Sci-fix improvement plan v3, PR-3 (A5), sci-fix SCAN-VERDICT-ORDER (S2, C2, D2). Fix `e48396a4`, parent `8472cdb5`
(PR-2's head) in a detached worktree with the fix commit's `tests/tools/test_scifix_advisories.py` copied in; the
worktree was removed after the run.

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/tools/test_scifix_advisories.py::ProjectScan::test_verdict_over_every_combination_of_the_five_steps` | exhaustive (40 cases) | fail, 21 of 40 subtests by assertion | pass | no | CI lock |
| `tests/tools/test_scifix_advisories.py::ProjectScan::test_verdict_order_no_artifact_and_manifest_paths` | behavioral | fail (assertion) | pass | no | CI lock |
| `tests/tools/test_scifix_advisories.py::ProjectScan::test_shipped_no_artifact_advisories_skip_the_hadd_job` | behavioral | fail (assertion: SFA-2026-036 and -037 affected) | pass | no | CI lock |
| `tests/tools/test_scifix_advisories.py::ProjectScan::test_release_basis_and_verdicts` | behavioral | fail (assertion: `verified` basis) | pass | no | CI lock |

Reproduction of plan F-01/F-27 (a 0.21.0 `computational-run` that only ran `hadd`, with the 0.21.0 manifest digest):
main `a53af7e0` reports SFA-2026-036 and SFA-2026-037 `affected`; the fix reports no finding and lists the eight
advisories without artifacts (SFA-2026-014 to -019, -036, -037) in `outputs_not_artifacts`.

## SCIFIX-PLAN-P0-CHECK (2026-10-22, CI lock venv: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch; worktree branch `scifix/pr-2-advisory-check` from main `a53af7e0`)

Sci-fix improvement plan v3, PR-2 (A0, A3, C5, F-23). Counts on main `a53af7e0` (0.23.0), recomputed because the
plan was written on 0.22.0: 31 advisories, 39 ledger entries, 8 documentation fixes, 59 independence records.

| Check | Result |
|---|---|
| Parent `check` on the shipped advisories | 0 problems (accepts all) |
| New `check` on the shipped advisories before the data changes | 10 problems: SFA-2026-014 to -019, -036, -037 key on `tools` (required by `ext_computational_run`); SFA-2026-002 and -003 introduced at 0.10.0 although 0.9.0 holds an affected path |
| The 8 scripts named by those advisories write an artifact? | no: each prints JSON (or text) on stdout; `no_artifact` and `outputs` added |
| `introduced_basis` of SFA-2026-002 and -003 | verified in git: `canonical_key` with `int()` was added by 811f02b6 (the ML-SPLITS fix, SFA-2026-020); the `./`-only sample-name rule by f7846755 (the ML-CALIBRATION fix, SFA-2026-021) |
| Advisories still keyed non-discriminatingly (frozen allowlist) | 11: SFA-2026-001, 002, 004, 006, 010, 020, 023, 025, 030, 031 (no key), 033 |
| New `check` after the data changes | 0 problems |
| New tests (`StricterCheck`, 8 tests; `test_changelog_names_the_release_that_shipped_the_fix`) on the parent tool and ledger | fail (6 failures, 2 errors; the changelog test fails on the string values) |
| Same on the change | pass; `test_scifix_advisories` 15 tests, `test_scifix_ledger` 5 tests |
| `changelog` migration | only the `changelog` field changed in the 39 entries; releases: 0.4.0 (7), 0.6.11 (4), 0.6.13, 0.10.0 (15, three audits), 0.14.0, 0.18.0 (3, were `Unreleased`), 0.22.0 (ANISO-WEIGHTED-COV, was `Unreleased`), 0.23.0 (7 triage and anisotropy entries) |

| `run_all_checks.py --no-cli --jobs 4`, CI lock, worktree head | 23 pass, 2 fail, 2 skipped (CLI host checks); 4804 tests, 4554 pass, 1 failure, 249 skipped. Both failures were one defect: the audit names first written into `changelog` spelled two retired skill names (`check_retired_names.py`); renamed to `audit DR-WP1 to DR-WP4` and `ML audit (ML-C, ML-K, ML-R items)`, then `check_retired_names.py` and the three affected test modules rerun: pass |

Scan verdicts are unchanged by this step (the separate listing of advisories without artifacts is plan PR-3).

## REVIEW-EXPERT-SLOT (2026-10-22, Python 3.13.2 on macOS 26.5 arm64; E2 venv and the CI lock venv; branch `feat/review-config-expert` from main `f016edce`, unreleased)

Three changes to the independent review, contracts 3.6.0 (spec sections 5.1, 5.2, 5.3, 6.10, 7.6, A8). `start
--own-config` gives a review its own configuration file (`reviews/<id>/review-config.json`, recorded in
`round_started` as `config_file`), so concurrent reviews can use different settings; no schema change. The filter
packet's free text (`correction`, `description`, `fix`) has the raising slot's id, its record identity and the model
names replaced by `[redacted]`, with counts in the private `filter_ids.json` and the report. `start --expert-model M`
adds one expert slot to round 1 (role `expert` in `review_record`, config `expert`, receipt code
`finding_without_verdict`): whole document, no canaries, at most two attempts, never escalated, findings handled like
any other. Synthetic data only; no live agent run.

| Check | Result |
|---|---|
| New tests: `tests/contracts/test_review_expert_contract.py` (18), `tests/skills/hep_authoring/test_review_expert_slot.py` (23) | 41 pass. Covered: an end-to-end review with `--own-config`, the expert slot and the filter (expert rejected once with `finding_without_verdict`, then accepted; the filter over the expert's and a lens's findings; the expert finding changed and confirmed by the design lens in round 2; no expert slot in round 2; close, `check` exit 0); the expert packet's files, scope, units and instructions (no other slot id, no canary, valid example); scrubbed filter packet (slot ids, identities and model names in any case gone, a lowercase look-alike kept, `value` and `unit_texts` untouched, counts 3/2/2 in `filter_ids.json` and the report); receipt codes `finding_without_verdict`, `basis_missing`, `finding_shape`, `verdict_without_finding`, `self_citation`, `read_outside_packet` (the delivered document and a copy elsewhere in the project), `prior_conversation`, `same_identity`, `schema_invalid` (skim, wrong role); an empty expert record accepted; exhaustion after two attempts not escalated; returned-empty through row 5; `check --record-only --role expert`; an expert-only dispatch (start, dispatch and receive only the expert slot); a conflict item between an expert and a lens verdict with lenses including `expert` and its arbiter dispatched; own-config: shared file unchanged, concurrent reviews with different settings, the shared-file refusal naming only shared-config reviews, own config without a shared file, observe and `repair config_changed` on the own file, `check` `artifacts_changed` on an edited own file; the spec 6.10 and 7.6 text against the code; fold, snapshot (kind `expert`), attempt limit, transitions, carry-forward to the design lens (and to dispose without one), an exhaustive decide test over two review slots and the expert slot; fixtures in `contracts/fixtures/review/` (2 valid, 6 invalid expert records); unchanged behaviour without the options |
| Unchanged without the options | the P1 end-to-end review (`run_e2e`): review and private directories byte-identical to main `f016edce` (174 files, sha256 per file), checked after every step and on the final tree; reviewer and arbiter instruction files keep their role row (the `expert` role is not offered to them) |
| `run_all_checks.py --no-cli --jobs 6`, E2 (NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4885 tests in 407 modules, 4751 pass, 0 failures, 134 skipped |
| Same with the CI lock (NumPy 2.4.6, SciPy 1.17.1, no torch) | 25 pass, 0 fail, 2 skipped; 4885 tests, 4659 pass, 0 failures, 226 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |
| Contracts 3.6.0 bump | fixtures (`make_fixtures.py`), templates, theory-profile artifacts and examples regenerated (E2; `bc-propagation-fit` with the CI lock): version strings and the hashes that cover them only; `unfolding-coverage` drifted at 1e-14 and was restored |
| Packaging | the README size statement moved from 31.0 to 34.5 MB (about 2400 files): main was already 34.4 MB, at the edge of the 10% margin, and this branch's files crossed it |

Both gate runs were on the final tree except this section and the CHANGELOG entry. Not run: a live agent review with
the expert slot, so whether it finds the whole-page errors the reviewers missed is not shown here; the reference
describes it without recommending it. Skipped tests are unverified, not passed.

## HADRON-PHASE7 (2026-10-23; branch `feat/hadron-phase7-fits`)

Hadron-structure plan, phase 7 (S12 PDF reweighting and profiling, S13 global fits), macOS, Python 3.13 with NumPy and
SciPy; constructed inputs only (software checks; no physical validity).

Sources read in full text 2026-10-23: Ball et al. arXiv:1012.0836v4 (Nucl. Phys. B 849 (2011) 112; errata B 854, 855),
arXiv:1108.1758v2 (Nucl. Phys. B 855 (2012) 608), arXiv:0912.2276v2 (JHEP 05 (2010) 075); Giele and Keller
arXiv:hep-ph/9803393v1 (Phys. Rev. D 58 (1998) 094023); Watt and Thorne arXiv:1205.4024v2 (JHEP 08 (2012) 052);
Paukkunen and Zurita arXiv:1402.6623v3 (JHEP 12 (2014) 100); PDG 2026 Structure Functions Sec. 18.3. Journal references
confirmed at INSPIRE-HEP.

| Check | Result |
|---|---|
| `test_pdf_reweighting.py` (NNPDF and Giele-Keller weights and N_eff against hand values, Kish ESS, movement toward a synthetic truth, low-N_eff warning, Hessian-generated replicas only with GK weights and chi2/Delta chi^2, a one-point zero-chi2 case, refusals) | pass |
| `test_hessian_profiling.py` (w_min, profiled central value and uncertainty against the exact stacked weighted least squares on a linear toy; the no-information limit; dynamic tolerance withholds the verdict; refusals incl. an odd eigenvector-member count) | pass |
| `test_covariance_fit.py` t0 (GLS oracle for value and error; the central value's independence of t0 for one common normalization; iteration to a self-consistent t0 for separate normalizations; guards) | pass |
| `run_all_checks.py --part static`, `check_layering.py`, `check_wiring.py`, `check_routing_static.py` (453 cases) | pass |

Independent review (a read-only agent with the sources): no wrong formula. Fixed with tests that failed first: a
dynamic tolerance gave wrong profiled uncertainties and a misleading verdict; Hessian-generated replicas were reweighted
without the chi2/Delta chi^2 rescaling (Paukkunen and Zurita, Eq. 5.2); the t0 tests could not tell whether t0 was used
or iterated (with one common normalization the central value does not depend on t0); an NNPDF weight could be NaN. The
hep-statistics description now names PDF reweighting/profiling and PDF fits. Not run: live routing for the 4 S12-S13
cases and the description change (paid; pending approval).

## HADRON-PHASE6 (2026-10-23; branch `feat/hadron-phase6-smallx-gpd`)

Hadron-structure plan, phase 6 (Th19 small x and saturation, Th20 exclusive processes and GPDs), macOS, Python 3.13
with SciPy (core stack); constructed inputs only (software checks; no physical validity).

Sources read in full text 2026-10-23: Golec-Biernat and Wusthoff arXiv:hep-ph/9807513v1 (Phys. Rev. D 59 (1998)
014017); Kowalski and Teaney arXiv:hep-ph/0304189 (Phys. Rev. D 68 (2003) 114005); Albacete and Kovchegov
arXiv:0704.0612 (Phys. Rev. D 75 (2007) 125021); Belitsky, Mueller, Kirchner arXiv:hep-ph/0112108 (Nucl. Phys. B 629
(2002) 323); Ji arXiv:hep-ph/9603249v1 (Phys. Rev. Lett. 78 (1997) 610); Collins arXiv:hep-ph/9709499v2 (Phys. Rev. D
57 (1998) 3051); PDG 2026 Structure Functions Secs. 18.2.2, 18.5, 18.6.1. Journal references from arXiv.

| Check | Result |
|---|---|
| `test_dipole_lo.py` (K_0, K_1 against their integral representation to 1e-10; sigma_hat small- and large-r limits; sigma_L against its analytic colour-transparency limit for m = 0, 2e-3, which pins the 6 alpha/4 pi^2 prefactor and the d^2 r measure; the mass-modified x as GBW Eq. 21; positivity and convergence; alpha cancels in F_2; refusals of a fit's x-variable mismatch and x above the declared limit; rejections) | pass |
| `test_exclusive_kinematics.py` (t_min against four-vector arithmetic with the photon along q; both xi forms; phi_BMK and phi_Trento on constructed events and phi_Trento = pi - phi_BMK; beta x_P = x; rejections incl. an off-shell recoil) | pass |
| `test_sum_rules.py` GPD rules (form-factor and Ji integrals of a forward toy built from PDG Eq. 18.36, Beta-function values) | pass |
| `run_all_checks.py --part static`, `check_layering.py`, `check_wiring.py` | pass |

Independent review (a read-only agent with the sources): no wrong formula; it rederived phi_Trento = pi - phi_BMK and
reproduced F_L/F_2 = 0.194 at Q^2 = 10 GeV^2 with the GBW no-charm parameters. Fixed: BMK section citations (Sec. 4);
the normalization test above (the earlier dipole tests could not catch a prefactor error); a crash on a charge such as
2/0 and duplicate flavours; an off-shell recoil accepted; the convergence report now varies r_max and r_min at fixed
nodes; Eq. 21 applies to every flavour; Ji Eq. 13 cited for J = (A + B)/2; GPD table conventions documented. Deferred:
no upper |t| bound in `dvcs`, no M_X <= W - M check in `diffractive`, an xi-dependent GPD toy. Not run: live routing for
the 4 Th19-Th20 cases (paid; pending).

## HADRON-PHASE5 (2026-10-23; branch `feat/hadron-phase5-tmd`)

Hadron-structure plan, phase 5 (Th18 SIDIS and TMDs, fragmentation functions, profile `theory:tmd-gaussian-lo`),
macOS (Darwin 25.5.0), the interpreter from `find_python.py` (a miniconda Python 3.13.2: SymPy 1.14.0, SciPy 1.17.1,
NumPy 2.4.4); constructed inputs only (software checks; no physical validity).

Sources read in full text 2026-10-23: Trento conventions arXiv:hep-ph/0410050v2 (Phys. Rev. D 70 (2004) 117504);
Bacchetta et al. arXiv:hep-ph/0611265v2 (JHEP 02 (2007) 093); Anselmino et al. arXiv:hep-ph/0501196v2 (Phys. Rev. D
71 (2005) 074006); Collins arXiv:hep-ph/0204004v3 (Phys. Lett. B 536 (2002) 43); PDG 2026 Fragmentation Functions
(revised August 2023). Journal references confirmed at arXiv.

| Check | Result |
|---|---|
| `test_sidis_kinematics.py` (invariants and Trento phi_h against events built from an explicit right-handed basis, boost along the beam, mirror reflection, spin flip, classification, rejections incl. spacelike vectors) | pass |
| `test_tmd_gaussian.py` (F_UU,T against a direct numerical Eq. 4.1 convolution with Bacchetta's D(z, k_T^2) normalization, d^2 P_hT integral, Drell-Yan width and normalization, Sivers sign, rejections) | pass |
| `test_sum_rules.py` FF momentum rule (Beta-function toys; malformed hadron columns rejected) | pass |
| `theory:tmd-gaussian-lo` 0.1.0: `python3 -m unittest discover -s tests -t tests` in the profile (SymPy: Anselmino Eqs. 34-39 and the Cahn term Eq. 38, Bacchetta's convolution convention giving the same F_UU,T, the Sivers asymmetry Eqs. 58, 63-68; the Anselmino and Trento azimuths shown to coincide; the Drell-Yan q_T convolution derived here) | 37 run, 37 pass; `sidis-unpolarized-and-cahn` and `sivers-asymmetry` `tested-in-declared-environment` in the environment above; the benchmark (Anselmino Eqs. 38-39, 64-67 against the profile's own quadrature at 4 points, 1e-7) follows the paper's route and checks algebra and transcription, not physics; the Drell-Yan sign change is a cited rule (Trento Eq. 14) |
| `run_all_checks.py --part static`, `check_layering.py`, `check_wiring.py` | pass |

Independent reviews (read-only agents with the sources): pages and scripts, no wrong formula; fixed a dropped malformed
FF column, spacelike vectors accepted, the multiplicity's gamma -> 0 assumption, the hadron sum in Eq. 2.18, |q_T|
labelling, the Boer-Mulders sign change (now cited from Bacchetta et al. Sec. 3.3), FF notation. Profile: physics
correct; the frame mapping was closed, independence wording, benchmark label and conventions keys corrected, a
circular sign "check" turned into a declaration. Not run: live routing for the 3 Th18 cases (paid; pending).

## HADRON-PHASE4 (2026-10-23; branch `feat/hadron-phase4-pol`)

Hadron-structure plan, phase 4 (Th17 polarized DIS and the first two theory-domain profiles), macOS (Darwin 25.5.0)
arm64, interpreter from `find_python.py` (a miniconda Python 3.13.2, SymPy 1.14.0, SciPy
1.17.1, NumPy 2.4.4); constructed inputs only (software checks; no physical validity).

Sources read in full text 2026-10-23: PDG 2026 Structure Functions Eqs. 18.6, 18.13-18.22; Kuhn, Chen, Leader
arXiv:0812.3535v1 (Secs. 1.1, 2.1, 2.2, 3.1); Moch, Vermaseren, Vogt arXiv:hep-ph/0411112 (Eqs. 1-3; Phys. Lett. B 606
(2005) 123, DOI confirmed at INSPIRE-HEP); Peng et al. arXiv:1511.08932v3 (Eqs. 1-10; Phys. Lett. B 758 (2016) 384,
confirmed at INSPIRE-HEP); PDG 2026 Cross-Section Formulae Eqs. 51.3, 51.40.

| Check | Result |
|---|---|
| `test_sum_rules.py`, polarized rules (g_1 moments of p and n, Bjorken at LO, Ellis-Jaffe values for p and n, an independent anchor through Kuhn-Chen-Leader Eq. 43 from a_3, a_8, a_0, charm helicity columns, rejections) | pass (11 tests in the file) |
| `theory:dis-parton-model` 0.1.0: `python3 -m unittest discover -s tests -t tests` in the profile (SymPy change of variables from the Moch-Vermaseren-Vogt coefficient functions to the Altarelli-Martinelli form, negative tests for a wrong C_F and a dropped <e^2>, gluon-only and quark-only hand values pinning 8 sum e_q^2 and 16/3, quadrature against the exact closed form within 1e-10 with a 4-128 node convergence study) | 35 run, 35 pass; capabilities `demonstrated-on-synthetic-data` (no published F_L benchmark read) |
| `theory:drell-yan-lo` 0.1.0: same command in the profile (LO cross section in SymPy and against the shipped `drell_yan_lo.py xsec` to 1e-12; Peng Eq. 4 into Eq. 2 reproduces Eq. 5; Eqs. 6-7; Lam-Tung for phi_1 = 0; channel mixing derived as the cross-section-fraction average of A_i; benchmark Peng Eq. 10, 2 channels x 7 q_T/Q x lambda, nu, relative 1e-12) | 40 run, 40 pass; capabilities `angular-coefficients-and-lam-tung` and `published-closed-form-benchmark` `tested-in-declared-environment` in the environment above; the LO cross section `demonstrated-on-synthetic-data` |
| `run_all_checks.py --part static` (profile tests included as `profile-tests:theory:*`), `check_layering.py`, `check_wiring.py` | pass |

The benchmark follows the paper's own route (Eqs. 8-9 into the A_i relations), so it checks the algebra and the
transcription, not the physics of Eqs. 8-9. Independent reviews (read-only agents with the sources): polarized page and
rules, no wrong formula; fixed section citations, the unsourced a_8 = 3F - D (now "not verified"), charm columns that
were ignored, `--gA`/`--a8` accepted with other rules. Profiles: the channel-mixing "alternative" (a linear average of
lambda, nu stored as a model uncertainty) was wrong and is removed, the A-average now derived; the Lam-Tung sign is
stated within the quark-axis representation; two hard-coded "checks" became declarations; an independent LO
normalization and a quark-only F_L hand value added. Not run: live routing for the 2 Th17 cases (paid; pending).

## HADRON-PHASE3 (2026-10-23; branch `feat/hadron-phase3-nuclear`)

Hadron-structure plan, phase 3 (Th16, nuclear targets), macOS 26.5 arm64, Python 3.13, constructed inputs only
(software checks; no physical validity). Sources read in full text 2026-10-23: PDG 2026 Structure Functions Sec. 18.3;
Klasen and Paukkunen arXiv:2311.00450; EPPS21 arXiv:2112.12462v2; nNNPDF3.0 arXiv:2201.12363v2; nCTEQ15
arXiv:1509.00792; nCTEQ15HQ arXiv:2204.09982 (the plan named arXiv:2105.09873, a different nCTEQ paper; PDG's
reference [134] gives 2204.09982). Authors and journal references confirmed at arXiv.

| Check | Result |
|---|---|
| `test_nuclear_combination.py` (free-proton limit, isoscalar symmetry, factor A and a lead value, x conversion; member-by-member ratio against a hand value and against divided bands on a correlated toy; replica headline by prescription; refusals for different sets, mixed error types or CL, baseline mismatch, unpaired members, replica over external proton, average-nucleon grids; rejections) | pass |

Independent review (a read-only agent with all six sources): no wrong formula. Fixed before the commit, each code fix
with a test that failed first: an average-nucleon grid could be combined again (now refused; the input declares
`grid_kind`); a replica set could be paired with an external proton set (refused); the replica headline was the mean
and standard deviation where nNNPDF3.0 prescribes the median and central 68% interval (the prescription is now an
input); `convert` accepted x_A > 1, M_A < M_N and negative values, `ratio` negative denominators. Page fixes: the
nNNPDF3.0 baseline is an NNPDF3.1-methodology variant, not NNPDF4.0; EPPS21's proton pairing (Eq. 40) spelled out;
sets have no support above x_N = 1; isoscalar-corrected data need theory at Z = A/2; nCTEQ15HQ states no tolerance;
locators corrected. Not run: live routing for the 3 Th16 cases (paid; pending approval).

## HADRON-PHASE2 (2026-10-23; branch `feat/hadron-phase2-dy`)

Hadron-structure plan, phase 2 (Th15, Drell-Yan), macOS 26.5 arm64, Python 3.13, constructed inputs only (software
checks; no physical validity). Sources read in full text 2026-10-23: PDG 2026 "Cross-Section Formulae" (Eqs. 51.2,
51.3, 51.25, 51.40; it has no explicit Drell-Yan formula), Peng et al. arXiv:1511.08932v3 (Eqs. 1-7), Aad et al.
arXiv:1606.00689v1 (Sec. 1, Eqs. 1-5), Faccioli et al. arXiv:1006.2738v1 (Eqs. 18-22, 25-31) and arXiv:1005.2601v1
(Eq. 8); journal references confirmed at arXiv, first author of 1606.00689 at INSPIRE-HEP. Derived here and marked so:
the LO cross section from Eq. 51.3, the colour average and Eq. 51.40; the x_F definitions and Jacobians; the lab shift;
the lepton-swap behaviour; the exact non-negativity condition of the angular distribution.

| Check | Result |
|---|---|
| `test_drell_yan_lo.py` (hand value; normalization against PDG's 86.8 nb / s within 2e-3, independent of the code's constant; Jacobians and x_F against four-vectors; round trips; fixed-target lab shift; y symmetry; LO scaling; closed-form y integral within 1e-6; pd/pp response to dbar/ubar; 13 refusals and rejections) | pass |
| `test_dy_angular_frames.py` (rotation angle against boosted axes; Eq. 21 against a direct numerical rotation, 1e-9; HX -> CS sign end to end on boosted axes; invariants and round trip; Lam-Tung frame independence; allowed domain against a 300-point sphere scan) | pass |

Independent review (a read-only agent; both PDFs, an independent derivation and an end-to-end frame check): no wrong
formula or number. Fixed before the commit, each with a test that failed first: the allowed-domain check used only the
Eq. 22 bounds and accepted distributions negative on part of the sphere (now also W >= 0 through the eigenvalues of
I + M; the scan showed that neither condition implies the other); two point specifications, beams with no
centre-of-mass frame (an uncaught division by zero) and a resonance window with LO > HI were accepted. Page fixes: Peng
et al. apply non-coplanarity to the collider data only; the lepton swap flips A_7 as well; mu(-y) = -mu(y) only for
symmetric beams; at q_T = 0 and y < 0 the HX axis is antiparallel to the CS axis; Peng et al. Eq. 7 cited for the
A_i relations. Not run: live routing for the 4 Th15 cases (paid; pending approval).

## HADRON-PHASE1 (2026-10-23; branch `feat/hadron-phase1-dis` from main `4ff6ee6a`)

Hadron-structure plan, phase 1 (Th14, unpolarized inclusive DIS), macOS 26.5 arm64, Python 3.13 (miniconda), on
constructed inputs only: these are software checks and establish no physical validity.

Sources read in full text 2026-10-23: PDG 2026 "Structure Functions" review (pages 1-16, Eqs. 18.1-18.25) and
Schienbein et al., arXiv:0709.1775v2 (Eq. 3, Sec. 2.2, Sec. 4, App. A). Derived here and marked so on the page: the
polarization dependence through lambda -> P_e (NC) and eta^CC = 2 (1 +/- P_e) eta_W (CC), d2sigma/dx dQ^2 =
(y / Q^2) d2sigma/dx dy, the Adler and GLS LO integrands from Eq. 18.19, the boson-gluon-fusion threshold.

| Check | Result |
|---|---|
| `test_structure_functions_lo.py` (photon hand value, charge symmetry with antiquarks, e+/e- xF_3 sign, polarized NC through charge times P_e, photon limit of gamma-Z, CC normalization against the parton form G_F^2/(2 pi x) prop^2 x[(ubar+cbar)+(1-y)^2(d+s)], CC polarization scaling, nucleus limits, 13 rejections; relative 1e-12) | pass |
| `test_sum_rules.py` (momentum, number, Adler, GLS on Beta-function toys within 5e-4; exact power-law extrapolation; divergence and an un-runnable check reported as incomplete; violation exit 1) | pass |
| `test_hadron_structure_th14.py` (conditional convention keys skipped by `theory.conventions_incomplete`, page format) | pass |
| `run_all_checks.py --no-cli --jobs 6` | 5033 tests, 4843 pass, 187 skipped; the 3 failures and the `reference_inventory` fail were the stale inventory, regenerated and rerun (pass) |
| `run_all_checks.py --part static`, `check_wiring.py --since 4ff6ee6a`, `check_routing_static.py` (433 cases), ruff 0.16.10 and mypy 2.4.0 on core and contracts | pass |

Independent review (a read-only agent that did not write the material, checking against both source PDFs and an
independent recalculation): no wrong formula, sign, normalization, coupling or W assignment. Fixed before the commit
with a test that failed first: a requested sum-rule check that could not run exited 0 (now incomplete, exit 3);
G_F, M_Z, M_W <= 0 and sin^2 theta_W outside (0, 1) were accepted (now rejected); the page did not say that the TMC
review defines F_L^TMC = r^2 F_2^TMC - 2x F_1^TMC. Wording fixed: GM-VFNS variant names are not in the PDG text;
"at large Q^2" restored; the Kretzer-Reno attribution of Eq. 23; the hadronic threshold marked as derived. Deferred:
`--s` silently overrides beam energies; negative parton values are accepted without a warning.

Contracts: the 13 new keys are core `convention_keys` and also `conditional_convention_keys`, which
`theory.conventions_incomplete` skips, so existing theory-specs gain no warning. Not run: the live routing run for the
description change and the 8 Th14 cases (paid; pending approval). Pre-existing on main: 5 tests of
`tests/contracts/test_simulated_dataset.py` fail under a whole-directory pytest run and pass alone (order dependent).

## SEMANTIC-NAMING-P3-P5 (2026-10-26, E2: macOS 26.5 arm64, Python 3.13.2, uproot 5.7.6; ruff 0.16.10 and mypy 2.4.0 from the CI venv; PR #304, merged into main `467648ea`, unreleased)

Semantic naming spec, phases P3 to P5 (an extractor for every surface N1-N17, cross-surface names, glossary
identifiers) and the code fixes of the spec's third review round (R869ec87b88, kept outside the repository with the
v4.3 spec). Software consistency only: the checks say the extractors and the engine behave as specified on synthetic
inputs and on the plugin itself, not that any name is good.

| Check | Result |
|---|---|
| Cross-surface engine | `tests/core/test_naming_cross_surface.py` (22): a shape nuisance's derived `Up`/`Down` histograms (missing `Down` violated with the N3 inventory, unverified without it, linked into the histograms' references); a dangling `\ref`; a figure target without the N2 inventory unverified; the correlation inventory read from a measurement-spec (era-decorrelated names satisfied, one source with two names violated, `partial` left out); glossary identifiers on two surfaces; one DOI under two BibTeX keys (a deduplication change set needs the N14 inventory, a non-uniqueness trigger is refused); a narrowed scope gives partial references and C2; a waiver without its line; cross-surface change sets (no N3 inventory exit 3, an unreplaced derived histogram exit 1, a lower recorded level or missing digests refused, a complete set passes) |
| Engine, CLI, registries | `tests/core/test_naming_engine.py` (35), `tests/contracts/test_naming_check.py` (24): the P1-P2 cases plus the per-kind `deprecate` policy, the C3 handoff owner, N10 near-duplicates resolved only by a declaration, an expected surface without inventory (exit 3), every name reported when no inventory carries change marks, two active rule versions and `naming.waived` on a non-waivable rule refused |
| Extractors | `tests/skills/hep_computing/test_extract_names_root.py` (5; N3/N4 skip without uproot): ROOT objects and shape histograms, no reader gives unsupported, TTree and RNTuple fields, defined columns, `--external`, the datacard-to-ROOT hand-off through the check (exit 1); N6 Snakemake, Slurm, HTCondor and workflow names. One module per owner skill: hep-statistics (3: datacard with derived shapes, pyhf workspace, statistical-result), hep-measurement (3: yield tables, official dataset ids of a bound profile, ledger and spec), hep-authoring (2: labels, references, macros, figure and table targets, comments ignored; BibTeX keys with DOI and arXiv ids and their citations), hep-detector, hep-ml, hep-theory, hep-citations (1 each; a mistyped DOI gives `propose-alias`) |
| Plugin gate | `tests/tools/test_check_naming.py` (6; unsupported results never baselined); on the plugin: N1 95,441, N5 2,214, N16 447 names, 409,820 results satisfied, 1,042 violations all in `tools/naming_known_gaps.json`; the generic names it flagged in this branch's own code were renamed |
| Registry and docs | `contracts/naming_registry.py check` passes (17 surfaces, 20 rules, every surface with an extractor, owner anchor and current kinds block); `check_wiring`, `check_ownership`, `capability_map --check`, `reference_inventory --check` pass; hep-statistics quick load 25,592 B (B-03 limit 25,600) |
| Aggregate | `tools/run_all_checks.py --no-cli` on `e3f794ab`: 5,715 unittest run, 3 failures (the reference inventory stale after a late edit, which also failed the soft-budget test; a module-timeout test that passes alone, a timing flake under load); fixed and rerun green in `c6f1b1a9`. CI on the PR after updating from main (`b25957cd`): every required and optional job passed, 2 skipped by design; ruff and mypy clean on `core` and `contracts` |
| Open | the re-review (round 2) has slot S4 escalated for a human decision and its findings not yet disposed, among them `--changed` given a revision that already holds the new names (listed in PR #304) |

## SEMANTIC-NAMING-P1-P2 (2026-10-26, macOS 26.5 arm64, miniconda Python 3.13.2; ruff 0.16.10 and mypy 2.4.0 from the CI venv; branch `feat/semantic-naming` from main `cfd9f547`, unreleased)

Semantic naming spec v4.2, phases P1 (skeleton) and P2 (first extractors, the plugin's gate, stanza item 6). Software
consistency only: the checks say the engine and the extractors behave as specified on synthetic inputs and on the
plugin itself, not that any name is good.

| Check | Result |
|---|---|
| Spec §12 cases | `tests/core/test_naming_engine.py` (34 tests): tokenizer cases; forbidden (whole name, generic-only, `data_obs` and `DataLoader` not, a glossary alias never overrides); waivers (explicit id, a pattern rejected by the schema, a non-waivable rule unaffected); N10 declared correlation both ways, decorrelated years, `lumi2018`/`lumi_2018` unverified without a proposal and resolved by a declaration or an annotation; Up without Down; status honesty; semantic confidence (low, medium, high, high without every referrer read); levels (loop index C0, unsearched `do_something` C2 and not `fix`, external C4, C3 handoff, out-of-request fix proposed); same-name ids and duplicates; a removed name referenced from an unchanged file reported; zero inputs and an expected surface unsupported; the six change-set checks |
| CLI, registries, project settings | `tests/contracts/test_naming_check.py` (21): exit 3 when everything is unverified or nothing was scanned, 0 with style warnings only, 1 with `--strict` or a correctness error, 2 for a bad inventory or an `--out` inside `artifacts_dir`; the glossary digest changes with the glossary; the report validates against `naming_report.json`; registry mutations (duplicate rule, heuristic with a violated code, stale source digest, mirror mismatch, missing anchor, lowered floor) fail; `naming` block 1.3.0 passes, an unknown key or schema 1.2.0 fails |
| Extractor | `tests/skills/hep_computing/test_extract_names.py` (11, 1 skipped when PyYAML is installed): N1 kinds, import-resolved and keyword references, duplicates; `--changed` against a git commit (modified body, added, removed and still referenced, which the check fails); N2 version in name, `\includegraphics` references, manifest-checksummed files; N5 flags, environment variables, duplicate JSON keys; N16 on the plugin; refusal inside `artifacts_dir` |
| Plugin gate | `tests/tools/test_check_naming.py` (5); on the plugin: N1 93,601, N5 2,213, N16 440 names, 401,571 results satisfied, 1,042 violations all in `tools/naming_known_gaps.json` (none in files this branch adds: those were renamed), 22 s; a `do_something()` added on purpose in `core/naming/` fails it (exit 1) |
| Budgets | `tools/measure_entrypoints.py`: the spec's stanza sentence gave hep-statistics a quick load of 25,656 B (> 25,600); the shipped shorter sentence gives 25,597 B; every SKILL.md within budget |
| Aggregate | `tools/run_all_checks.py --no-cli`: 30 of 31 checks pass, 2 skip (host CLIs); unittest 5,672 run, 5 failures, all convention tests on the new files (no `--status`, bytecode, subprocess timeouts, a module timing, a SKILL.md path), fixed and their modules rerun green (103 tests); `--part static` afterwards 31 of 31 pass or skip; ruff and mypy clean on `core` and `contracts` |

## FRONTEND-FE5 (2026-10-25, E2: macOS 26.5 arm64, Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1, SymPy 1.14.0, mpmath 1.3.0; branch `worktree-frontend-fe5` in `.claude/worktrees/frontend-fe5`, unreleased)

Stage FE5: the front-end reference page split in three. Maintainer decision D-FE5 (2026-10-25): two new pages, the
front-end page registered as a hub. Stacked on FE4. Worktree checks at the start: top level the worktree, branch
`worktree-frontend-fe5`, status clean.

| Check | Result |
|---|---|
| No content change (`move:` commit) | every non-blank line of the old page is in one of the three pages (multiset comparison: 0 lines lost); the only new lines are the two titles, their introductions and the eight "(moved)" pointers |
| Size | front-end page 40,480 -> 23,863 bytes after the move, 24,202 with the sentence naming the new pages (warning line 24,576); new pages 12,656 and 6,034 bytes; `reference_inventory.py --check` pass, the page no longer warned |
| Wiring | `check_wiring.py --since` the FE4 head: pass (hub registered; the new pages reachable through it; CHANGELOG names both); section pointers recorded under `pointers` with `remove_in` 0.42.0 and a note that `check_wiring.py` checks pointer pages only |
| Links | `test_reference_links` pass; links into moved sections and links whose topic moved retargeted; `InjectionGainGuidance` reads the calibration page; FRONTEND-INJECTION-GAIN internal sources split between the two pages |
| Validation commands | static part pass, `lint_task.py` 0 errors |
| Full check at `a1267715` | 31 of 31 checks pass with the host CLIs; unittest 5598 run, 5445 pass, 153 skipped, 0 failures or errors |

FE0 head `297169a3` alone (with the exit-code fix), full check: 31 of 31 pass; unittest 5575 run, 5422 pass, 153
skipped, 0 failures or errors.

## FRONTEND-FE4 (2026-10-25, E2: macOS 26.5 arm64, Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1, SymPy 1.14.0, mpmath 1.3.0; branch `worktree-frontend-fe4` in `.claude/worktrees/frontend-fe4`, unreleased)

Stage FE4: `hit-efficiency` fills the `noise-digitization` tail source of the Geant4 adapter's simreco. Maintainer
decision D-FE4 (2026-10-25): new options only (`feat:`). Stacked on FE3 (the §P.10.2 exception of FE1; the maintainer
asked to start FE4 while FE0 is open). Worktree checks at the start: top level the worktree, branch
`worktree-frontend-fe4`, status clean. The adapter is not changed (an adapter change needs an adapter version bump,
out of scope), so simreco, its defaults (threshold 0.2, efficiency 1, no noise hits) and the J15/J16 records are
unchanged by construction.

| Check | Result |
|---|---|
| Block against the closed form (Gaussian signal 6000 +- 800 e, noise 1000 e, threshold 4500 e, 25 ns peaking, 50 ns window, 640 channels) | `threshold` = 4500/6000 (1e-14), `efficiency` = Phi((mu - T)/sqrt(ss^2 + sn^2))^2 (1e-12), `noise_hits_per_plane` = ((Phi(-T/sn) + nu0 exp(-T^2/2 sn^2) w) x 640)^2 (relative 1e-10); one side as negative control (efficiency differs by more than 0.05) |
| `--threshold-enc` | 4.5 x 1000 e gives output equal to `--thresholds 4500`; 4 x 1200 e gives 4800 e; Landau reference is the MPV, table reference its peak |
| Default output | without the new options the CLI output equals, byte for byte, the JSON of `hit_efficiency` with the same inputs; with them every other key is equal and one assumption is appended |
| simreco spec | the block merged into `tail_sources.noise-digitization` passes `simreco_spec.check` against J15 and reaches the effective spec unchanged |
| Bad inputs | two thresholds, no window, 0 channels, sides 3, sides without channels, signal fraction 0.5, threshold above the reference, `--threshold-enc` 0 or nan or with `--thresholds`: exit 2, `invalid-input`, no traceback |
| Mutants | 17 local mutants, all killed (four needed sharper tests: a mutant string that matched another function, `--noise` 1000 hiding the ENC product, the derivation's `sides`; a finiteness check that `hit_efficiency` repeats was removed instead) |
| Validation commands | unit tests (`SimrecoBlock`, 6 tests), tool contract pass, reference inventory pass, wiring `--since` pass, ruff 0.16.10 clean, `lint_task.py` 0 errors |
| Full check at `cdcb3651` (before the rebase onto the amended FE3 record; same code) | 31 of 31 checks pass with the host CLIs; unittest 5598 run, 5445 pass, 153 skipped, 0 failures or errors |

## FRONTEND-FE3 (2026-10-25, E2: macOS 26.5 arm64, Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1, SymPy 1.14.0, mpmath 1.3.0; branch `worktree-frontend-fe3` in `.claude/worktrees/frontend-fe3`, unreleased)

Stage FE3: batch S-curve fits from a scan file. Based on the FE2 branch head `42a4ccbc` (the §P.10.2 exception of
FE1, stacked). Worktree checks at the start: top level the worktree, branch `worktree-frontend-fe3`, status clean.

| Check | Result |
|---|---|
| FE3-1 | every key of each channel's batch result equals `scurve_fit` on that channel (200 channels) |
| FE3-2 (60 batches of 200 channels; thresholds N(3700, 150^2) e, sigma 300 e, 8 charges every 200 e, 100 injections; seed 2) | mean `threshold_dispersion_corrected` within 3 MC standard errors of 150 e, and of each batch's own true-threshold sd (paired); the uncorrected sd is high by more than 3 standard errors (negative control). Prototype: the Fisher error of the threshold matches the actual fit error (18.48 against 18.49 e, 20 000 fits); with seed 1 the generated true thresholds themselves have sd 151.6 e over 200 batches (a 3-sigma excursion of the stream), which the corrected value follows (151.8 e), so the paired form is the seed-independent check |
| FE3-3 | true spread 0 and 5 e, 8 batches each: exit-free, finite, >= 0; every batch with radicand <= 0 reports 0 with "dispersion not above the fit error" (at least one occurs), the output serializes without NaN |
| FE3-4 | a channel that never crosses 50 % is in `failed_channels`, a converging one with p ~ 1e-12 in `excluded_channels` with the reason p < 1e-3; neither changes the summary; the > 5 % warning appears (2 of 22) |
| FE3-5 | mean `threshold_mad_sigma` within 3 MC standard errors of sqrt(150^2 + mean sigma_T^2), the spread of the fitted thresholds the MAD estimates (the task document said "the true sigma"; the MAD is not corrected for the fit error); the unscaled MAD fails (negative control); median noise and the p < 1e-3 count (over all fitted channels; over the included ones it is always 0) recomputed from the per-channel results |
| Files | missing, empty, header only, wrong header, three columns, not a number, nan charge, fractional injections, hits above injections, zero injections, empty channel, charges not increasing, not UTF-8; `--scan-file` with `--charges` or `--injections`; neither input: exit 2, `invalid-input`, no traceback |
| Mutants | 11 local mutants all killed (fit-error subtraction, MAD factor, n - 1, the p rule, clipping, the 5 % rule, median over included, even-length median, increasing charges, integer counts, input exclusion) |
| Validation commands 1-6 | unit tests, tool contract pass (the batch fields are mode-specific and, like the fit fields, not listed as outputs), reference inventory pass, wiring pass, ruff 0.16.10 clean, static checks pass |
| Full check (command 7) at `49356c8c` | 31 of 31 checks pass with the host CLIs; unittest 5591 run, 5438 pass, 153 skipped, 0 failures or errors |

**Rebased (2026-10-25)** with FE1 and FE2 onto the FE0 commit `297169a3` (the exit-code fix; no conflict in this
stage). Full check of the rebased stack at FE3 head `96d8363c` (the same tree as this record's commit, without the
rebase notes): `tools/run_all_checks.py --out <scratch>` with the host CLIs, 31 of 31 checks pass; unittest 5592 run,
5439 pass, 153 skipped, 0 failures or errors (458 modules).

## FRONTEND-FE2 (2026-10-25, E2: macOS 26.5 arm64, Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1, SymPy 1.14.0, mpmath 1.3.0; branch `worktree-frontend-fe2` in `.claude/worktrees/frontend-fe2`, unreleased)

Stage FE2: a measured noise covariance for `optimal-filter` and `waveform-toy`. Based on the FE1 branch head
`b97a3203` (the same §P.10.2 exception as FE1, and stacked so that FE1-FE3, which change the same files, merge in
order without conflicts). Worktree checks at the start: top level the worktree, branch `worktree-frontend-fe2`, status
clean.

| Check | Result |
|---|---|
| FE2-1 rho^\|i-j\| matrix (rho 0.6, 7 samples) | `optimal-filter` sigmas and weights (plain, phase-constrained, with pileup and the joint fit) and `waveform-toy` `predicted_sigma` equal the `--rho 0.6` values to 1e-12; closure \|z\| < 4 (20 000 events). The toy draws are identical too: the Cholesky factor of rho^\|i-j\| is the AR(1) recursion |
| FE2-2 rho^\|i-j\| + 0.3 common mode | sample covariance of 20 000 `correlated_noise` draws within 4 Gaussian standard errors of every element; AR(1) draws without the common mode differ by more than 4 (negative control); toy closure \|z\| < 4; the template variance rises by 0.3 (sum w)^2 exactly (1e-12) |
| FE2-3 bad matrices | not positive definite, singular (all ones), not symmetric, wrong dimension, ragged, non-finite: ValueError from `measured_covariance`, the input unchanged (no repair); bad files (missing, does not parse, no key, not an object, not rows, empty, a string, a boolean, NaN and Infinity tokens, wrong dimension, not UTF-8) and `--rho` with `--noise-covariance`: exit 2, `invalid-input`, no traceback, for both subcommands |
| FE2-4 | `noise_model` `ar1` / `measured`; `noise_covariance_sha256` equals the SHA-256 recomputed in the test and changes when one element changes by 1e-9 |
| Mutants | 9 local mutants: 8 killed (measured base, L z, symmetry, semidefinite repair, ragged rows, hash separators, rho exclusion, number check); 1 equivalent (the non-finite check, which `cholesky` repeats). The repair mutant survived the first tests and got its own. The exit-code fix that FE2 first carried (serialization apart from the input checks) is now the FE0 commit `297169a3` with its tests |
| Validation commands 1-6 | unit tests, tool contract pass, reference inventory pass, wiring pass, ruff 0.16.10 clean, static checks pass |
| Full check (command 7) at `4734555f` | 31 of 31 checks pass with the host CLIs; unittest 5585 run, 5432 pass, 153 skipped, 0 failures or errors |

**Rebased (2026-10-25)** onto the FE0 commit `297169a3` and the rebased FE1: the serialization split and its exit-1
test, which `4734555f` carried, are now that FE0 commit, so this stage no longer changes `main()`'s error handling.
The full check above ran before the rebase; the full check of the rebased stack is in FRONTEND-FE3.

## FRONTEND-FE1 (2026-10-25, E2: macOS 26.5 arm64, Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1, SymPy 1.14.0, mpmath 1.3.0; branch `worktree-frontend-fe1` in `.claude/worktrees/frontend-fe1`, unreleased)

Stage FE1 of `docs/dev/frontend-electronics/frontend-reco-sim-calibration.md`: the table signal model of
`hit-efficiency`. **Exception to §P.10.2 (task document §0 item 2):** the maintainer asked for FE1-FE3 to run
unattended while FE0 (#294) was still open, so FE1 is based on the FE0 branch head `317e452f`, not on a main that
contains FE0; it is rebased onto main and all checks rerun before it merges. Worktree checks at the start: top level
the worktree, branch `worktree-frontend-fe1`, status clean.

| Check | Result |
|---|---|
| FE1-1 Landau density table (MPV 23000 e, xi 1500 e, noise 1000 e; 8000-60000 e, step 25 e) | relative difference < 1e-3 at 16000-24000 e against the `landau` model truncated at 60000 e. Amended criterion: as written (untruncated `landau`) it cannot hold, since the normalized table misses the tail beyond its end (0.88 % for a table to 200 000 e; the tail falls as about xi/(Q - MPV)); interpolation adds 4.5 % (linear CDF) or 2.3 % (linear density) at 16000 e with a 150 e step, falling as the step squared (prototype, recorded in the task document). `validity` flags the truncation |
| FE1-2 negative control (+300 e shift) | relative difference > 9 % at every threshold |
| FE1-3 Gaussian density table (mean 20000 e, sigma 1000 e, step 50 e) | efficiency within 1e-4 of the closed form at 17000-23000 e; a 5 % wider table differs by more than 1e-3 |
| Count table | bins with edges at the midpoints, uniform within a bin, against a hand computation; the signal fraction scales the charge axis; thresholds outside the table flagged |
| FE1-4 bad files | missing, empty, header only, one row, wrong names, three columns, a short row, not a number, nan, inf, not increasing, a repeated charge, a negative value (positive total), zero total, not UTF-8: exit 2, `invalid-input`, no traceback; `frontend_response.py` in `MISSING_FILE_ARGS` |
| Mutants | 8 local mutants of the new code (density interpolation, count edges, signal-fraction scaling, normalization, truncation flag, outside-range flag, strict increase, negative values) all killed by `HitEfficiencyTable`; the negative-value mutant survived the first version of the test (that case also had a zero total) and the case was fixed |
| Validation commands 1-6 | unit tests (108), tool contract pass, reference inventory pass, wiring pass, ruff 0.16.10 clean, static checks pass |
| Full check (command 7) at `1214aebd` | 31 of 31 checks pass with the host CLIs; unittest 5579 run, 5426 pass, 153 skipped, 0 failures or errors |

Software checks only: the table model reproduces the Landau and Gaussian models it was sampled from; no measured
thin-silicon spectrum was used (open question "FE1 spectrum").

**Rebased (2026-10-25)** onto `297169a3`, the FE0 commit that fixes the exit code of an input error naming JSON (no
conflict). The full check above ran before the rebase; the full check of the rebased stack is in FRONTEND-FE3.

## FRONTEND-RECO-SIM (2026-10-25, Linux x86_64 container, Python 3.13.17, NumPy 2.5.3, SciPy 1.18.1 for the oracles, no SymPy or mpmath; branch `worktree-frontend-reco-sim` from main `bc7b1c18`, unreleased)

hep-detector front-end electronics for reconstruction and simulation: `frontend_response.py` subcommands
`optimal-filter`, `hit-efficiency`, `waveform-toy`, `s-curve`, `threshold-trim`; the reference additions and the new
`readout-digitization-and-overlay.md`. No contracts, `core/` or adapter version change.

| Check | Result |
|---|---|
| Page numbers already on the front-end page (optimal filter, phase error) | recomputed with NumPy before any code: template 1.117, largest sample 1.066, optimal 1.037; white-noise phase bias -0.041 / -0.333 % at -/+2 ns, -0.787 / -1.538 % at -/+5 ns; correlated +0.93 / -1.79 % at -/+2 ns, -5.81 % at 5 ns; all as printed; `optimal-filter` reproduces them and `test_frontend_waveforms.py` pins them |
| Pulse autocorrelation (closed form) | against trapezoid integration for n = 1, 2, 4 and four lags; zero lag equals int g^2 |
| Optimal filter | Lagrange conditions (w . g = 1, R w parallel to g) to 1e-9; no worse than the template or the largest sample; white noise equals the template; Campbell pileup per sample exact; constraints: w . g' = 0 and sum w = 0 to 1e-10, the phase-constrained bias even and quadratic in the phase error; joint amplitude-time errors against a SciPy least-squares MC (4000 pulses: 0.431 ns, 0.778) and the sign of the correlation on rising and falling edges |
| Landau | against SciPy 1.18.1 `landau` (S1(1, 1, 1, 0), mapped with scale pi/2 and location ln(pi/2)) to 3.5e-13 over lambda -5 to 100 during development, recorded values to 1e-10 in the test; against the oscillatory integral (independent standard-library implementation) to 2e-6; MPV -0.222783, peak 0.1806556; CDF derivative equals the density |
| Hit efficiency | Landau case against `scipy.integrate.quad` (0.98796331) and a 4e6-event MC (0.987947 +- 0.000055); Gaussian case closed form; threshold-spread averages of the Rice rate and of the per-sample tail against numerical averages over thresholds; the worked operating window of the page |
| Waveform toy | closure |z| < 4 for bias and width of four estimators with correlated noise and exponential-amplitude pileup (several seeds and 200 000 events during development); the standard error of the width uses the fourth moment (the Gaussian formula overstated the z-scores for exponential pileup); the baseline constraint removes the pileup mean bias; jitter and saturation flagged |
| Mutants | eight local mutants of the new code; six killed by the new tests (Landau MPV constant, threshold-spread factor, autocorrelation power, Gaussian width, phase sign, fourth-moment error); the endpoint constant of the Zolotarev integral is equivalent within the adaptive tolerance; the amplitude-time correlation sign got its own test afterwards |
| S-curve | fit equal to `scipy.optimize.minimize` (Nelder-Mead) of the same likelihood to 1e-3 e; a NumPy MC of 2000 scans (T 3700 e, sigma 300 e, 8 charges every 200 e, 100 injections): sd 17.9 and 17.5 e against the design prediction 18.3 and 17.3 e, pulls 0.98 and 1.02 wide, mean noise pull -0.12 (maximum-likelihood bias); 1/sqrt(N) scaling exact; coarse and inconsistent scans flagged |
| Threshold trim | against a NumPy MC of 2e6 channels with rounded, clipped codes: 441.76 e and 18.28 % beyond the range for (1500 e, 4 bits, 250 e), tool 441.57 e and 18.24 %; 258.47 e for (800 e, 5 bits, 60 e), tool 258.73 e; wide-range limit D/sqrt(12) and the nonlinearity in quadrature exact |
| Tool contract | `contracts/tool_contract.py`: pass, 15 operations; `FrontendResponseContractTests` with the five new operations |
| Aggregate (`tools/run_all_checks.py --part all --no-cli --jobs 2`) | 27 of 31 checks pass, 2 skip (host CLIs); unittest 5549 run, 5237 pass, 294 skipped, 18 failures or errors, all outside hep-detector and all from this environment: SymPy and mpmath are not installed and PyPI is unreachable (16), and `test_paper_skeleton` and `test_ci_plan.RunnerRecord` fail identically on a clean checkout of main here; `ams_optional` fails on the same missing SymPy. Rerun in E2 before merging |

**Independent review R720d9d2e80** of `docs/dev/frontend-electronics/frontend-reco-sim-calibration.md`
(`skills/hep-authoring/scripts/review.py`, models opus and sonnet, `--lens-model design=opus --filter-model opus
--expert-model opus --own-config`, isolation precondition `fork-denied`; advisory): round 1, 9 slots, the expert slot
and the filter (36 findings, 26 kept). All findings disposed: 35 changed (each verified by the author against the plugin
files or a tool run), 1 declined (the branch name it reported was in this file and had been fixed). Canary hit rate
2/2. The facts lens slot S4 was rejected twice (it copied the document to run `lint_task.py`) and was escalated for a
human. On 2026-10-26 the maintainer accepted it as missing (the human decision `accept-missing` for a slot; the
shadow facts slot S3 was accepted with 4 claims supported, and S4's overlapping findings were checked by the author).
The review's state stayed in the container it ran in, so the decision is recorded here, not through
`review.py resolve`.

**FE1 spectrum asset (2026-10-26, E2).** `skills/hep-detector/assets/thin-silicon-300um-mu10gev.geant4-pai.csv`: the
J14 run `mpv-pai` (1 200 000 mu- of 10 GeV through 300 um silicon, `G4EmStandardPhysics_option4` with the PAI model in
the silicon region, Geant4 11.4.3 build A) binned in 100 e (2953 rows, every event inside; 3.65 eV per pair). The
recorded spec, rerun with the recorded executable (sha256 `d39225ea...`) and build record, gave the recorded hashes of
all five output files (`events.csv` `61dd5bf4...`); the current `geant4_run.py` marked the rerun failed only because
that older executable writes no `probe.json`. `HitEfficiencyGeant4Spectrum` (3 tests): total 1 200 000, mean, lowest and
highest charge within half a bin of the recorded block summaries; peak 23 250 e, within one bin of the recorded PAI
most probable loss (23 181 e) and +1.4 % from the Landau-Vavilov Delta_p of `geant4_benchmarks.py` (22 928 e); half-
maximum width 1.38 x Landau's 4.02 xi; at a 16 000 e threshold with ENC 1000 e the table's inefficiency is 9.5e-4
against 1.7e-6 for a Landau with that Delta_p and xi; no missing-tail warning. A table shifted by 300 e fails the
first two tests. The spectrum is a simulation (`unvalidated`), not a measurement. The substantive corrections: the FE1-1 criterion could not fail (thresholds
far below the Landau peak), the threshold spread is routed pre-trim to `threshold-trim` and post-trim to
`hit-efficiency`, the FE3 corrected spread is clipped at zero, the stage base follows P.10.2, the C4 guidance change is
flagged for classification and has a second located source (arXiv:0912.2642, sec. 3.1.2).

**FE0 pre-merge acceptance in E2 (2026-10-25).** Environment: E2 venv `~/.venvs/hep-research-e2`, macOS 26.5 arm64,
Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1, SymPy 1.14.0, mpmath 1.3.0; host CLIs Claude Code 2.1.310 and codex-cli
0.160.0; worktree `.claude/worktrees/frontend-fe0`, branch `worktree-frontend-fe0` from main `d5c8ff24` (0.40.0),
patches 0001-0004 applied with `git am --3way`: only the generated reference inventory conflicted (regenerated), and
the CHANGELOG entry, which auto-merged into the released 0.39.0 section, was moved to Unreleased. Checked at commit
`6f156782` (after the C4 split): `tools/run_all_checks.py --out <scratch>` with the host CLIs, 31 of 31 checks pass;
unittest 5573 run, 5420 pass, 153 skipped, 0 failures or errors (458 modules); no `ModuleNotFoundError`; the two
failures FE0-1 allows (`test_paper_skeleton`, `test_ci_plan.RunnerRecord`) do not occur here, nor does the
`ams_optional` failure of the container run. ruff 0.16.10 on the changed Python files and `core contracts`, and
mypy 2.4.0, clean. The task document passes `lint_task.py --repo .` (0 errors, 0 warnings).

**sci-fix FRONTEND-INJECTION-GAIN (C4, S3; maintainer decision D-C4 2026-10-25: split from the `feat:` calibration
commit).** The calibration chain no longer takes the charge-injection gain for the signal gain. Sources read in the
full text on 2026-10-25: arXiv:1306.6756v2 sec. II-C ("a factor to correct for differences between the physics signal
and calibration pulses") and arXiv:0912.2642v4 sec. 3.1.2, eq. 5 (the factor `1/(M_phys/M_cali)` "quantifies the
ratio of response to a calibration pulse and an ionization pulse corresponding to the same input current"); the second
source had only been located through a search index before. Parent: `9a116535` (the branch with C4 removed).

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/hep_detector/test_frontend_waveforms.py::InjectionGainGuidance::test_injection_bullet_separates_injection_and_signal_gain` | behavioral (guidance text with both locators) | fail (assertion) | pass | no | E2 |
| `tests/skills/hep_detector/test_frontend_waveforms.py::InjectionGainGuidance::test_misconception_is_listed` | behavioral | fail (assertion) | pass | no | E2 |

**Fix: exit code of an input error that names JSON (2026-10-25, E2).** `main()` serialized the result inside the
`try` that maps a `ValueError` to exit 2, and took a message containing "JSON" for a non-finite result (exit 1). The
serialization now has its own `try`. `CommandLine.test_input_error_naming_json_exits_2` (an input error with "JSON"
in its message, raised in-process) fails on the unfixed script (exit 1, `SystemExit` not raised) and passes on the fix;
`test_non_finite_result_exits_1` (an exception while computing, and `enc` at 1e300, an infinite result) passes on both.

Software checks show contract consistency and agreement with the named oracles, not physical validity: the Landau
model has no Bichsel broadening, and the toy is synthetic.

## DESIGN-SEARCH-EXAMPLES (2026-10-25, E2: macOS 26.5 arm64, Apple clang 21.0.0, Geant4 11.4.3 build A, Python 3.13; branch `worktree-geant4-c3` from main `2af81a39`, unreleased)

Geant4 program stage C3 (spec section C.7): journey J16, `examples/design-search-j16`. No code change outside the
example, J15's campaign (study prefix, realization-profile name, reference-slab thickness and materials as class
attributes, J15's values unchanged) and the registration; no contract or adapter version change.

| Check | Result |
|---|---|
| Example A search | base `cand-S`; plane count 4-9 and positions over 0-3 m, field 0.1-0.5 T, optional TOF slot; objectives REQ-TRK-001 (1 TV) and CON-MASS-001, constraint REQ-CC-001; three seed proposals (proposer llm); 1200 F1 evaluations, 1109 distinct designs, 12 topologies, search front 88, finalists 937 (7 planes, 0.10 T), 961 (9 planes, 0.36 T, TOF), 1047 (9 planes, 0.49 T); consistency against `run` 0 |
| Example B search | base `cand-B`; plane count 8-13 and positions, field 1-2 T (the role rule's limit, so the 3.8 T `cand-A` is outside the space), ECAL stochastic term; objectives REQ-TRK-001, REQ-ECAL-001, CON-MASS-001; 1200 evaluations, 1121 designs, 6 topologies, front 141, finalists 959, 1037, 1061; the four `capability.unavailable` requirements recorded for each finalist and inconclusive with `capability.unavailable` in the report |
| Reports (gate G-C3) | both: screening and verdicts from `design.py` (A: CON-MASS-001 pass for 937 and fail for 1047, resolution and charge confusion `bound.direction`; B: REQ-TRK-001 `bound.excludes` for the two lighter finalists, which the search kept as trade-offs because the requirement was an objective, not a constraint); comparison basis declared, does not hold (mass differences beyond 5 %); ranking refused (basis, and no expected-precision evaluation); gates H1-H3 flagged; no `design.py` error |
| Example A F4 confirmation (`live.py`, recorded 200 kB) | `cand-F937`, 1 TV protons, J15's campaign with `space.realization.json` and the aluminium support's independent entry; seeds from `confirmation_study_id(SEARCH-J16A, ...)`; trial 1600, then 5040 events (nominal, cut scan, two variations, tails off and on). Upgrade **refused**: the multiple-scattering reference (0.937 mm silicon, the planes' x/X0 0.01) agrees with Lynch-Dahl to +0.39 % and both controls are caught, but the -13 % control shifted -8.0 % against DL 6.4 % (beyond 1.1 DL); recorded and not rerun. The F4 evaluation (0.313 against 0.260 at F1) is unqualified: REQ-TRK-001 for `cand-F937` inconclusive with `fidelity.insufficient` |
| Offline replay | `tests/examples/test_design_search_j16.py`: every criterion, results within 1e-9 relative (1e-12 absolute: two search-minus-official values that are zero on macOS came out at 1e-20 and 1e-75 on Linux) of the committed `output/results.json`, the confirmation shown as recorded, the reply facts (search size, basis, ranking). The two search runs are recorded (`recorded/search/`, 497 kB gzip) and replayed: CI on Linux (PR #286, first run) reran the search and got another `cand-F937` (NSGA-II's polynomial mutation calls `pow`, whose last bit differs between glibc and macOS, so the trajectory diverged), which the recorded geometry then refused (ART-35); `run.py --live-search` reruns them |
| Bayesian-optimisation backend | not provided (`adapters/design-bo/` 0.1.0 is optional, P.7 item 14): neither environment has Ax or BoTorch, and an untested backend is not shipped; the search runs NSGA-II (C3.4: the fallback is noted) |

Problems found and fixed: the first export missed a refused study's run records (a refused study lists them in
`inputs`, not `evidence_records`); `live.py export` and the replay now read both, as J15's replay does. The fixed
size of J15's reference controls (+-13 %) misses 1.1 DL when the detection limit is small (100 GV in J15, 1 TV here):
sizing the control from a declared detection limit before the runs is a follow-up for the campaign code, and a new
reference study is the only way to qualify these points.

**`review.py` Markdown review** of the J16 README (R0b7acaa370, models opus and sonnet, `--lens-model design=opus
--filter-model opus`, own configuration; advisory, `reviews/R0b7acaa370/report.md` in
`~/Workspace/hep-research-tasks/geant4-program/c3/review`): round 1, 6 slots and the filter (13 findings, 5 kept):
all disposed, 12 changed, 1 declined (each reference control is judged against its own detection limit). Rounds 2
and 3, 6 slots each: the seeding sentence corrected (only the study's own runs use `confirmation_study_id`; the shared
verification and reference runs use fixed ids), `confirmation_study_id` has no attempt input (a new attempt needs a
new search or design), the re-labelling replay and the unqualified F4 evaluation it writes stated, Example B's
verdicts and mass limits completed, the single seed proposal of Example B stated. Code from the review:
`search_minus_official` (`search --diagnose`, `report`) carries `f4_qualified` for F4 evaluations, so a refused
study's F4 row is marked. The round limit is reached, so the review is escalated: **open, waiting for a human
`resolve`**. The reviewers caught the mechanism's planted canaries.

## DESIGN-SEARCH-G4 (2026-10-25, E2: macOS 26.5 arm64, Apple clang 21.0.0, Geant4 11.4.3 build A, Python 3.13; branch `worktree-geant4-c2` from main `98658064`, unreleased)

Geant4 program stage C2 (spec section C.6): Geant4 search values and F4 confirmation, geant4 adapter 0.5.0, contracts
CV-C2 (shares the unreleased 3.13.0), `CORE_VERSION` unchanged at the unreleased 1.1.0.

| Check | Result |
|---|---|
| Paired mode (C2.1) | `core/stats/decisions.py` `paired_statistic`, `equivalence` and `change` with `pairing: paired` (absolute: per-block differences; relative: Fieller-type z_b per bound r; se target tol/4); toys with common random numbers (`tests/core/test_simulation_paired_values.py`): coverage of the nominal 90 % interval within 0.02 + 3 sigma_MC (4000 trials), the relative test rejects at most 0.05 + 3 sigma_MC at the bound, Var(independent) / Var(paired) above 2 for correlated blocks; default stays independent |
| `values` accumulator | `core/simulation/summary.py` keeps per-block raw values in event order for `values: true` (`values_max`, default 10^4, else `values_omitted`), merge rule concat; empirical quantiles (Hyndman-Fan type 7) equal numpy's to 1e-12; `g4sim/SimSummary.hh` writes the same values as Python also when the work is split across accumulators (`tests/adapters/test_g4sim.py`); simreco writes them from its CSV (`tests/adapters/test_simreco.py`); old summaries without values read and validate; `estimates.block_estimates` for paired comparisons |
| seed_group and contract rules (CV-C2) | `core/simulation/seeds.py` `search_group_seed`, `confirmation_study_id`, `seed_uniqueness_problems` (the one implementation `contracts/design.py` calls): a seed repeated outside one declared seed_group, equal spec hashes or unequal blocks within one are `design.seed_reuse`; an evaluation whose run, study or study input reuses a `search_summary` Geant4 search seed is `design.contract_mismatch`; `check_geant4_study.py label` refuses a run with evidence role `search`; records older than 3.13.0 are not constrained (`tests/skills/hep_detector/test_design_search_g4.py`) |
| Decoded candidates to Geant4 | J15 candidates decoded for each role (tracking positions, bending field, TOF time resolution, the carried calorimeter, an added RICH) give a geometry file, an `element_sim` spec from `from-geometry`, and `check-spec` passes in a subprocess |
| S2 offline (fake backend) | generations in one seed_group, survivors re-evaluated with new S, one survivor per topology, finalists `fixed_from: geant4`, budget stop, gate G-C2a switching to independent seeds without common random numbers, the search run validates and its finalist expands, `search --diagnose` writes a valid diagnostic run; winner's-curse toy (gate G-C2b): on designs of equal truth the survivors' values lie below their selection pool and an independent confirmation is unbiased |
| Live acceptance (C2.9; `~/Workspace/hep-research-tasks/geant4-program/c2/c2_live.py`, work `~/Workspace/geant4-work/sim-c2/accept`) | J15 (SYNTHETIC), base `cand-N6`; free: plane count 4-8 and positions over 0.80 m, field 0.3-0.7 T; objectives REQ-TRK-001 (Geant4 target, 1 GV protons, Gaussian core) and CON-MASS-001 (F1). S0 brief with three seed topologies (4, 6, 8 planes). S1: 400 F1 evaluations, 331 distinct designs, 5 topologies, consistency against `run` 0.0. S2: 3 topologies x (1 + 3 offspring) x 3 generations, 30 Geant4 search runs of 12800 events (K = 16), 21 seeds; gate G-C2a variance ratio 1.58 < 2 on generation 0, so generations 1-2 used independent seeds (Geant4 designs consume different random numbers). Finalists, fixed before expansion: points 314 (5 planes), 326 (4), 329 (7), field about 0.62-0.69 T. S3: expanded, F1 run and budget evaluations. S4: one F4 study per finalist with study_id from `confirmation_study_id`; all three re-issued `validated-in-scope` (strict validation passes): F4 core 1.204 %, 1.018 %, 1.674 % (16944, 10192, 11376 events); `REQ-TRK-001` passes for all three (`estimate.decides`); REQ-TRK-002, REQ-CC-001, REQ-CAL-001 stay inconclusive (no evidence at 100 GV, 500 GV, showers); ranking refused (no expected-precision evaluation; the J15 base candidates lack F1 mass evaluations); `derive` reports no error (no evaluation shares a search seed) |
| Diagnostic (`runs/DIAG-SEARCH-C2`) | Geant4 search value minus F4: -0.039, +0.001, -0.073 percentage points (-3.2 %, +0.1 %, -4.4 % relative: the expected small optimism of the selected); F1 minus F4: +0.67, +0.48, +0.76 points (F1 overestimates the 1 GV core by 45-56 %: the Highland term against the Geant4 Gaussian core; J15 saw the same) |

Problems found and fixed during the stage:
- S2 started from the S1 search front only; on this problem the front held one design (four planes dominate at 1 GV),
  so one topology was refined. S2 now takes the first design of each topology from the whole population ranked by
  constrained non-dominated sorting and crowding (a development run, set aside as `accept-dev1`, showed it).
- Survivors beyond `finalists.max` were taken by point index; they are now ordered by rank and crowding on their last
  Geant4 values.
- 1600 events per search run (100 per block) is thin for the Gaussian-core estimator; the acceptance used 12800.

Limits, recorded: the role rules name a search-added TOF's and calorimeter's parameters for the F1 tools (n_layers,
path_m, depth_X0, z_front_m), not for the geometry mapping, so such a subsystem has no Geant4 geometry: Geant4 search
values vary only subsystems that carry mapping fields. Pairing gave no gain here (ratio 1.58); the paired estimate
stays valid but the search fell back to independent seeds, as the gate intends. G5: the C++ changes
(`g4sim/SimSummary.hh`, `SimObservables.hh`) use only the C++ standard library and the adapter's own headers; no
Geant4 example code. Evidence: the 3 changed C++ files (`SimSummary.hh`, `SimObservables.hh`, `simreco.cc`)
against all 5,657 `.cc`, `.hh`, `.icc` files of the Geant4 11.4.3 examples tree, normalized lines: 0 shared runs of 3
or 4 consecutive lines (`c2/g5_scan_k3.json`, `c2/g5_scan_k4.json`; positive control of GEANT4-A8-CHECKS gives 51).
Reviewer confirmation: confirmed by the maintainer on 2026-10-25.

## GEANT4-J15 (2026-10-24/25, E2: macOS 26.5 arm64, Apple clang 21.0.0, Geant4 11.4.3 build A, Python 3.13; branch `worktree-geant4-b3` from main `a97a40e2`)

Geant4 program stage B3 (spec §B.7): journey J15, `examples/design-minimal-spectrometer`, geant4 adapter 0.4.1.
Live campaign `live.py` (work folder `~/Workspace/geant4-work/sim-b3/j15`, element_sim and simreco rebuilt from this
branch), recorded in `recorded/` (1.83 MB); offline replay `run.py`, 18 pre-declared criteria pass; every geometry is
invented (J15 is SYNTHETIC).

| Check | Result |
|---|---|
| B3.1 design | design-spec `j15-v1`, three candidates (six, four, eight 0.3 mm Si planes over 0.80 m), no `design.*` error; F1 resolution at 1 GV 2.5 % and F2 2.2 % (§B.4.2: 1.8-2.6 %), MDR 1131 GV with Gluckstern (§B.4.2: about 1172 GV exact), 100 GV measurement term 8.7 %, F2 in-field acceptance within 10 % of the straight-line acceptance at 10 GV; `from-geometry` on `cand-N6` (mapping 1.1.0 fields: tracker size and material, field extent, TOF layers, calorimeter front, depth and sampling) equals §B.4.1 element by element; H1 and H2 drafts listed, not valid (DEC-05) |
| Event counts (A1.9) | per study a 1600-event trial, then N = N_trial (SE / target)^2 F_0.95(15, 15) on the core (target 1.77 %, the convergence se target): 12800 (N6, 1 GV), 18976 (N4, 1 GV), 9936 (N8, 1 GV), 5728, 7984, 8704 (100 GV), 11968 (500 GV, on the charge-flip proportion), 30064 (10 GeV showers, on the rear-leakage fraction) |
| Multiple-scattering reference (isolated 0.3 mm Si, protons, ±13 % density controls) | 1 GV: -1.79 %, controls +7.3 % and -7.0 % against DL 8.1 %; 100 GV: -0.57 %, both caught, the -13 % control shifted -8.1 % against DL 6.3 % (beyond 1.1 DL; the controls had a fixed size, not one sized from each rigidity's DL): a gap, recorded and not rerun; 500 GV: -1.18 %, caught |
| F4 tracking studies (tails on, 20 replicas) | 1 GV: N4 1.48 %, N6 1.82 %, N8 2.08 %, all re-issued `validated-in-scope` (four conditions: material definition, field propagation, reconstruction closure, the reference); N4 and N8 pass `REQ-TRK-001` at row 16 (D0-c uncertainty with the 1 GV reference's 4.0 % tolerance, floor 0.02); N6 is inconclusive only because the tails-off demonstration (`optimistic`, row 14) is also present at equal fidelity (AGG-04; without it N6 passes, checked, and J15 keeps it). 100 GV: N4 11.3 %, N6 10.5 %, N8 9.8 % (tails off: 9.3 %, 8.6 %, 7.9 %), refused for the reference control gap (N6 also missed its convergence se target) |
| Charge confusion, 500 GV | 3.4 % (replica mean; F1 Gaussian core 0.96 %), refused: no published tail reference (D0-b) |
| Shower containment, 10 GeV e- | 96.8 % (rear leakage 2.5 %, PDG gamma profile 2.3 %: plausible), cut scan 0.1 / 0.3 / 0.7 / 1.0 mm converged on containment and rear leakage; refused: no reference benchmark |
| Variations | 1 GV: single scattering (`FTFP_BERT__SS`) and binary cascade; 100 and 500 GV: option 3 (Urban msc for protons) and binary cascade; air instead of vacuum widens the N6 1 GV core by 5 % |
| TOF (B3.5) | sigma_beta/beta at 1 GV 1.68 % (100 ps) and 2.52 % (150 ps), = 2.3 % x beta (0.73) scaled; two-layer residual 142.6 and 213.9 ps (sqrt 2 sigma_t: 141.4, 212.1) |
| Verification ladder (separate `unvalidated` record) | overlaps (control: Si2 onto Si1, refused by check-spec), energy balance e-/e+ 1 GeV EM-only (controls double-count-leakage, omit-positron-mass caught), material budget, material definition (Pb density x 1.05 caught), field propagation (B x (1 ± 1e-4) caught), field-propagation-muon 1/10/100 GV (B x 1.01 caught), reco closure (reconstruction B x 1.05 caught), tof-beta and tof-layer-consistency (+100 ps caught), sampling fraction 0.268 vs 0.270 (PDG muon tables; PVT density x 1.2 caught) |
| Replay test | `tests/examples/test_design_minimal_spectrometer.py`: 5 tests (criteria, results within 1e-9, strict validation of the upgraded records with the D0-c term, derived report, recorded budget), 37 s |

Problems found by the campaign and fixed (each before the final runs):
- A planned event count of 21 million: the planner estimated the trial from the summary's own observable (no
  estimator: a plain mean, relative SE 1.3) instead of the study's declaration; fixed, plus a cap (200000 events) that
  refuses a planning error before any run.
- A looper: one worker stuck on an electron circling in the vacuum field region (every limited step completes, so the
  looper killer never acts); element_sim `field.max_track_time_ns` (J15: 1000 ns).
- Single scattering at 100 GeV is prohibitive (the hadronic shower's electrons in lead): the high-rigidity
  multiple-scattering variation is option 3 (Urban for protons, `isWVI=false`) against option 4 (WentzelVI).
- Tails on narrower than tails off at 100 GV: the strip digitization measured better than the declared 10 um (a fixed
  pencil beam saw the same strip phase every event, and charge sharing interpolates); simreco now draws a random
  strip phase per plane and event, uses sigma = sqrt((p - w)^3 / 12 p), and refuses a digitization finer than the
  declaration (J15: 47 um and 116 um, 8 um sharing).
- Shower containment above 1: the net face leakage subtracts secondaries radiated upstream that enter through the
  front face; containment is now the calorimeter deposit over E0.
- The ladder's balance gave no verdict (a hadronic list), its overlap check had no test points, and its muon field
  control reconstructed with the same wrong field: fixed (EM-only balance runs, a dedicated overlap run with 10000
  points, the control reconstructed with the design field).
- `geant4_benchmarks.py` raised a KeyError on a detector reference control outside its detection limit (B2 bug).
- A counting interval below zero (the replica spread added in quadrature): capped at zero.

**B3.9 independent-agent acceptance** ("the rigidity resolution of 1 GV protons in J15"; a general-purpose agent that
did not take part, given only the plugin path, the task and `HEP_GEANT4_CONFIG`, forbidden to use J15's `recorded/` and
`output/`; its own project `~/Workspace/geant4-work/sim-b3/agent-j15`): design `aj15-v1` with `cand-N6` passes
`design.py`; F1 0.02537; geometry, its own realization profile, `from-geometry`, a 1600-event trial planned to 15360
events, nominal, cut scan, two variations, tails on with 20 replicas, the four qualification benchmarks, `label
--upgrade` re-issued `validated-in-scope` with no gaps, `validate.py --strict` on the artifacts_dir passes; F4 core
0.018225 (1.82 %, inside §B.4.2's 1.8-2.6 %), ±0.000406 (statistical ⊕ replicas; ±0.000884 with the 4.3 % D0-c term),
`REQ-TRK-001` pass. No maintainer help. Deviations and doc gaps it reported:
- Its multiple-scattering controls were built from the PDG silicon density × (1 ± 0.13), while Geant4 resolves G4_Si
  to its own density, so `injected_relative` differed from the realized change and both controls were not counted; it
  re-declared `injected_relative` as the tool's `injection_in_run` and re-evaluated, without new runs. That is a
  correction after the result, which the protocol treats as a rerun after a miss: this acceptance item passes with
  that deviation recorded. The protocol and `geant4_benchmarks.py --help` now say to declare the injection Geant4
  realizes, before the runs.
- The single-scattering variation (`FTFP_BERT__SS`) was too slow (about 2000 events in 16 min, protons stopping in
  the lead calorimeter); it used option 3 instead. The protocol now warns about the cost.
- The detector benchmarks' config keys were documented only in J15's `live.py` (now in `geant4_benchmarks.py
  --help`); `geometry` writes `geometry_ref` into the candidate (now in the design workflow); validate the whole
  artifacts_dir, not a subfolder (now in the protocol).
- Not fixed here (follow-ups): no tool reports the central-68 % half-width that B3.9 asks for beside the core (so it is
  not reported); no bias-toy tool for the Gaussian-core bin width; the trial size, convergence tolerance and statistical
  target of a tracking study are not given by the protocol; `f4 --status` defaults to `unvalidated` for a
  `validated-in-scope` study.

**`review.py` Markdown review** of the J15 README (R102edead76, 0.22.0 mechanism, models opus and sonnet,
`--lens-model design=opus --filter-model opus`, own configuration; advisory, `reviews/R102edead76/report.md` in
`~/Workspace/hep-research-tasks/geant4-program/b3/review`): round 1, 8 slots (one rerun after a cited file changed)
and the filter (19 findings, 13 kept): all disposed, 18 changed, 1 declined (the 1 GV controls are within 1.1 DL; the
numbers were added). Fixed: the tail-source list, the 1 GV tolerance (4.0 %, not 3.9 %, also in this entry), why
`cand-N6` is inconclusive (AGG-04, not "the estimate decides"), 100 GV numbers labelled as refused studies, gate H3,
the comparison-basis tolerance, the 100 GV F1 row, the 1 GV control shifts, the hadronic-variation label. Round 2,
8 slots (two reruns after recorded/ was rewritten) and one arbitration: further wording findings (LIM-02 quoted
exactly, DEC-05 checks a declared actor, the floor does not bind for J15, option 3 differs in more than proton
scattering, alignment residuals per axis, a new 100 GV reference needs a pre-declared control size that only a human
can check), applied. Round 3, 8 slots: three more (the omission called a gap in LIM-02's shortcut guard, AGG-04 compares only the top fidelity present so an agreeing optimistic bound blocks a pass there but not below, this entry's content), applied; the round limit is reached, so the review is escalated: **open, waiting for a human `resolve`**. The reviewers also caught the mechanism's planted canaries. Follow-up for `design.py`: AGG-04 lets a `bound.direction` evaluation that agrees with a deciding estimate at the same fidelity block it.

**Packaging**: the live campaign wrote absolute home paths into the run records and study inputs; `live.py export` now
writes `~` for the home directory and rewrites every sha256 that cites a changed file, to a fixpoint (the committed
`recorded/` was converted the same way; the replay and its test pass on it). J15 adds 566 files; the plugin README's
size statement is updated.

Deviations, recorded here: the recorded simreco summaries carry producer version "0.4.0" (the version string was
bumped to 0.4.1 after the campaign; the code was the 0.4.1 code except the string). The verification-ladder record
lists the nominal implementation-check records as inputs; the negative-control check records, failed by design, are
summarized in the ladder's results instead (as inputs their `failed` label would propagate).

## GEANT4-F4 (2026-10-24, E2: macOS 26.5 arm64, Apple clang 21.0.0, CMake 4.3.2, Geant4 11.4.3 build A, Python 3.13; branch `worktree-geant4-b2` from main `8b3dc9f7`)

Geant4 program stage B2 (spec §B.6): geant4 adapter 0.4.0 (`simreco`, `geant4_run.py reco` and `table`, mapping 1.1.0
in `from-geometry`), contracts CV-B2 (sharing the unreleased 3.13.0: `GEANT4_B2_FROM`), the F4 qualification path
(D0, decided 2026-10-24). Scripts and outputs: `~/Workspace/hep-research-tasks/geant4-program/b2/` (`gate_b2.py`,
`ms_trial.py`, `ms_estimators.py`, `e2e_trial.py`, `PLAN.md`); runs in `~/Workspace/geant4-work/sim-b2/` (`gate/`,
`ms/`, `e2e/`). Every geometry is invented (the gate candidate is Example A's `cand-S` with the J15 tracker,
SYNTHETIC).

| Check | Result |
|---|---|
| simreco unit tests (`tests/adapters/test_simreco.py`, built with `c++ -std=c++17 -O2 -ffp-contract=off`) | 13 pass: fitter against `tracker_resolution.py`'s measurement term at 300 GV (no scattering) and pull width 1 within 3 sigma_MC; byte-identical reruns; the summary equals `core/simulation/summary.py` recomputed from the result CSV; noise-digitization and pattern-recognition each widen the core and raise charge confusion; alignment and calibration-non-uniformity with 20 replicas widen the replica-mean core with s_rep > 0; the global field scale moves only the mean; the curvature offset follows the Gaussian-core expression; the gaussian-core and exact-interval estimators; reco and table plumbing around the real simreco (record, replicas, a changed event file refused, the dataset-record's chain, the f4-results file). The CI job `simreco` builds and runs them on Linux with the runner's compiler (`HEP_SIMRECO_REQUIRED=1`) |
| Multiple-scattering core estimator (`ms_trial.py`, `ms_estimators.py`: 0.3 mm G4_Si, protons, option 4, 8000 events) | RMS(central 98 %) / 0.8673 is +11.5 % (10 GeV/c) and +10.6 % (1 GeV/c) above Lynch-Dahl F = 98 %; a Gaussian fitted to the central 98 % (Lynch and Dahl's definition, truncated-normal maximum likelihood) gives -1.4 % (relative SE 0.8 %) and -1.6 % (0.6 %), inside 2 % + 3 SE. `multiple-scattering-reference` uses the fit; the `multiple-scattering` sanity benchmark keeps RMS / 0.8673. Control: slab density x 1.2 with the reference unchanged gives +9.0 % (expected about +9.5 %), fail |
| Lynch-Dahl accuracy | 2 % against Moliere: the paper's abstract (NIM B 58 (1991) 6, DOI 10.1016/0168-583X(91)95671-Y; abstract+metadata) and PDG 1998 section 23.3 ("achieve accuracies of 2% or better", page read 2026-10-24 from the KEK mirror ccwww.kek.jp/pdg/1998/passagerpp_part2.pdf); PDG 2024 gives no accuracy for its Eq. 34.16. The reference is Moliere theory, not a measurement; the full text (validity range) is unread, an open non-blocking item |
| G-B2 end-to-end (`gate_b2.py`, 8000 events per run, the event counts and tolerances fixed in the script before the runs): `evaluate_design.py geometry` -> `from-geometry` -> `element_sim` (nominal cut 0.7 mm, scan 0.35 mm, variations QGSP_BIC_EMZ and FTFP_BERT) -> `reco` (tails off, and all four tails with 20 replicas) -> `table --f4-results` -> `label --upgrade --results --geometry` -> `f4` -> `report` | convergence gate pass (cut 0.35 against 0.7 mm: core -0.47 %, SE 2.1 %, tol 10 %); statistical target pass (relative SE 1.46 % against 3 %). Qualification: `material-definition` pass (geantino x/X0 of all six planes equal the declared 0.0032017, densities within 1e-3 of the PDG values for G4_Si, G4_Pb, PVT), `field-propagation` pass (5000 plane entries, largest in-plane deviation 0.0042 um, TOF 1.8e-6 ps), `reco-closure` pass (charged geantinos at 1000 GV: pull width 0.9961, sigma_MC 0.0079), `multiple-scattering-reference` pass at 1 GV (-2.10 %, tolerance 3.93 %; density x 1.13 and x 0.87 both caught at the claimed detection limits 0.084 and 0.079, shifts +0.069 and -0.063). The upgrade is granted; `f4` by path (i) (`label`, then `f4`) and path (ii) (`f4 --label-spec ... --label-results --label-geometry`) give the same evaluation: value 0.01810, bound `estimate`, uncertainty +-0.00087 at coverage 0.90 (statistical t_0.95 x 0.00029 (+) replica spread 4.5e-5 gives +-0.00050; (+) the qualifying reference's tolerance 3.93 % x value, D0-c), model envelope [0.01797, 0.01810], `geometry_ref` the study's geometry file; `validate.py --strict` passes on the project; the report puts both on row 16 (`estimate.decides`, compliant with the SYNTHETIC 3 % requirement) under the qualification-path floor 0.02 (adequacy 1.2.0). Before D0-c the same chain stopped at row 15 (`uncertainty.missing`: 2.7 % against the F1-bias floor 0.2). Refusal: without `reco-closure` the upgrade is refused ("the tracking-resolution qualification path does not hold"; gap "reco-closure: not present") and `f4 --label-spec` is incomplete (exit 3) with the reasons and gaps |
| Tails off against B1 (§B.4.2, 1 GV protons: multiple-scattering term 1.8-2.6 %) | core 1.794 %, central-68 % half-width 1.859 %: the half-width is in the band, the Gaussian core 0.3 % below its lower edge (§B.7's agent check allows the core slightly below the half-width; both are reported) |
| Decisive row (`tests/skills/hep_detector/test_design_b2.py`, a SYNTHETIC f4-results file on J14's upgraded study) | an upgraded F4 `estimate` with a D0-c uncertainty of 0.12 at 90 % on 0.3 (sigma-equivalent 24 %) reaches row 16 (`estimate.decides`); with 0.006 it stays at row 15 (`uncertainty.missing`) |
| Offline tests | `test_design_b2` (label --results and --geometry, geometry mismatch exit 2, both f4 paths equal, gaps listed on refusal, the decisive row, optimistic without all tails), `test_geant4_b2_benchmarks` (change toys, regression, qualification conjunction, the core estimator and a density control), `test_geant4_element.Mapping11` (mapping 1.1.0), `test_simulated_dataset` (a three-level chain accepted, a non-simulation root refused, pre-3.13 refused), `test_cli_robustness` (reco and table missing files) |
| change toys (6000 toys, nu = 15) | P(changed) at true difference = tol is within alpha/m + 3 sigma_MC for m = 1 and 3; power at 2 tol (sigma 0.3 tol) above 0.9; unchanged at no difference about 0.88 |

D0-c (the maintainer's decision of 2026-10-24 on the recommendation): the 2 % accuracy of Lynch and Dahl is kept,
now from two sources (the paper's abstract and PDG 1998 section 23.3, "achieve accuracies of 2% or better", page
read 2026-10-24; the full text is still unread and stays an open, non-blocking item); the F4 uncertainty of a study
upgraded through a qualification path includes the qualifying reference's tolerance, and its floor is the path's
(adequacy 1.2.0 `f4_qualified_min_relative_uncertainty`, 0.02 for the resolution) instead of the F1-bias 0.2, applied
only when the evaluation's uncertainty holds that term (also at each end of the model envelope: a first version
lost the qualification there and the live report gave row 17; fixed and tested). The values stay provisional until
the adequacy table's physics review (OQ-05).

Independent review (a code-review agent that did not write the change, given the working tree and §B.6; it read the
code without running it): ten findings at confidence 50 or more, all fixed and tested: declared qualification hashes
were not tied to the study's own inputs (now derived from `--geometry`, the derived spec and the results' reco record,
a mismatch is a gap); the qualification branch skipped the reference's isolation check (restored); a tail source
with zero widths counted as simulated (refused by `simreco_spec.check`); a figure of merit could be built from any
observable with the right estimator, without the fitted-track selection, and with a denominator unrelated to the
simulation (the column, the selection and the gun's rigidity and species are checked; `check_f4` also compares the
result's denominator); `material-definition` skipped the passive slab, truncated a short list and could skip a
density (all checked now); the results file was not bound to the study's runs (its reco record must be an evidence
record with the same tail sources); `check_f4` validated older-version records non-strictly (strict now); the counting
interval used replica 0 uncentred (centred on the replica mean); a control was "caught" without its injection being
checked (the control run's slab areal density must differ by the stated fraction); a missing plane used one segment's
field and dropped its material (path-weighted field, material kept). Lower-confidence items also fixed: rigidity for
charge above 1 and Highland's z, the true beta taken from the primary's own crossings instead of the fitted path, the
dataset uncertainty marked non-Gaussian, malformed CSV rows exit 2, `_core98` refuses a flat window. The gate was
rerun from scratch on the fixed adapter 0.4.0 (the numbers above).

Decisions and deviations, recorded here:
- The measuring plane of the multiple-scattering reference is 1 um of G4_Si (a tracker plane cannot be vacuum) and
  is part of the target, so the configuration stays isolated; its crossing is recorded at entry, before its material.
- Every run a qualification benchmark reads (geantino scan, charged geantinos, the closure reco, the reference runs
  and their controls) is passed to `label` as `--run-record`: `dependencies.py` re-derives the reference's
  configuration from its run record, which must be an evidence record or input, and an `unvalidated` record as a
  plain input would block the re-issue.
- Mapping 1.1.0's fields are optional (`"optional": true`): a candidate without them keeps the 1.0.0 fields,
  parameter refs and digest (tested); candidate parameters cannot be objects, so the calorimeter sampling structure is
  five fields (layers; passive and active material and thickness). A geometry file that uses a 1.1.0 field needs a
  realization profile that declares 1.1.0; `calo_depth_x0` is checked against the realized structure with the
  profile's `calorimetry-em` radiation lengths (1 %).
- `table`'s dataset-record names its denominator point as `points` only (giving `edges` too is a contract error).
- No impact group for `adapters/geant4/**` is added to `contracts/rules/registry.json` (B2.9 suggests one): without
  it a change there runs the full CI.
- Not done in B2: the bit-identity check between Linux (libstdc++) and macOS (libc++) builds compares only what the
  CI job runs (the tests pass on both); the §A.8 agent run and the Markdown review are B3's (B3.8).

G5: simreco links no Geant4 code; it reads the CSV files simroot writes. The reviewer's confirmation for element_sim
and simroot (GEANT4-ELEMENT) was recorded on 2026-10-25.

## GEANT4-ELEMENT (2026-10-24, E2: macOS 26.5 arm64, Apple clang 21.0.0, CMake 4.3.2, Geant4 11.4.3 build A, Python 3.13; branch `worktree-geant4-b1` from main `14e45d13`)

Geant4 program stage B1 (spec §B.5): geant4 adapter 0.3.0, `element_sim` and `simroot` (built by `geant4_run.py
build-sim --program element_sim`, Release; a second build with `-DELEMENT_SIM_TEST_HOOKS=ON` adds two test-only UI
commands), `geant4_run.py check-spec` and `from-geometry`, `geant4_verify.py field`, `core/simulation/helix.py`. No
contracts bump. Scripts and outputs: `~/Workspace/hep-research-tasks/geant4-program/b1/` (`gb1a/`, `gb1b.py`,
`field_check.py`, `mt_check.py`, `budget_balance.py`, `g5_b1.sh`, `gb1b-*.json`, `g5_scan_k*.json`); runs in
`~/Workspace/geant4-work/sim-b1/`. Every geometry is invented (J15 is SYNTHETIC).

| Check | Result |
|---|---|
| G-B1a: `G4RootAnalysisReader` on an MT-merged (4 threads), compressed file with I, D and S columns (`gb1a/trial.cc`) | 1000 event rows read back with every value equal, string columns included; a row the MT master fills in a merged ntuple is lost (Geant4 warns "Ntuple 0 does not exist"), so element_sim has worker 0 (the only thread in serial mode) fill the `run` and `processes` rows; strings stay in the file (no JSON side file) |
| J15 geometry (§B.4.1, 112 placements, geantino along the axis, 10,000 overlap test points) | `geant4_verify.py overlaps`: no overlap report, every placement checked at construction; `budget`: the geantino path lengths `plen_<element>_mm` equal the thicknesses, sum t/X0 18.518 from both (calorimeter 18.41 X0 plus 11.32 % X0 in front, as §B Appendix A) |
| Energy balance (1 GeV e- and e+ on 10 x (2 mm Pb + 5 mm PVT), option 4, 200 events each) | worst per-event residual 1.9e-5 MeV (e-) and 4.5e-5 MeV (e+) against the declared 1e-3 MeV; E_in = calorimeter deposits + leakage by face to the same precision; `--inject omit-positron-mass` (e+) and `double-count-leakage` fail in every event |
| B1.7 deterministic field check, J15, charged geantinos 0.6, 1, 10, 100, 1000 GV x (normal, 50 mrad against the bend, +-50 mrad non-bending), 200 plane entries per run | nominal (delta intersection 1e-5 mm, max step 10 mm): largest in-plane deviation 0.054 um (limit 0.5 um), TOF-layer times within 4e-6 ps (limit 1 ps), largest x - x_face 5e-10 um. Grid, every point reported: delta intersection 1e-3 / 1e-4 / 1e-5 / 1e-6 mm gives 4.1 / 0.26 / 0.054 / 0.0058 um (1e-3 mm fails the 0.5 um criterion, the others pass; the two finest differ by at most 0.05 um, limit 0.2 um); max step 100 / 30 / 10 / 3 mm gives 0.013 / 0.040 / 0.054 / 0.036 um; delta one step and epsilon at 1/10: unchanged. Two field regions (0.5 T and 0.3 T): 0.056 um. Negative control, Geant4-side B x (1 +- 1e-4) checked against the nominal field: 13.4 um, caught in both directions |
| G-B1b, consistency of the two backends on the observables both produce (tolerances and se targets declared in `gb1b.py` before the runs, m = 3, se_diff <= tol/4; trial 160,000 muons / 8,000 electrons, final 512,000 / 20,000 with the two-stage factor) | J14 slab (10 GeV mu-, 300 um Si_study, option 4, cut 0.03 mm; layered_sim per-event, element_sim per-event, different S): mean deposit 0.105372 against 0.105500 MeV, relative -0.0012, se 0.0009, tol 0.01: pass; most probable deposit 0.084332 against 0.084372 MeV, -0.0005, se 0.0045, tol 0.02: pass. Calorimeter (1 GeV e-, 10 x (2 mm Pb + 5 mm PVT)): total leakage fraction (rear + front + lateral over E_in; world faces for layered_sim, calorimeter mother faces for element_sim) 0.70185 against 0.70088, absolute +0.0010, se 0.0010, tol 0.005: pass |
| Per-event invariance (J15, 1 GV protons, crossings level, observables): serial, MT 2 and 4 threads; 4 jobs of 10 events | event-file `content_sha256` identical for all five; CSV rows identical; summary integers identical and floats within 1e-12 |
| Field managers per thread (test build, 4 threads) | five distinct field-manager addresses (master and four workers) |
| Probe | every region's B, accuracy parameters, driver `G4InterpolationDriver<G4DormandPrince745, true>` and stepper `G4DormandPrince745` recorded and equal to the spec; the field block changes the tree-v1 target hash of the field element; layered_sim runs give the same probe as before (no field, no `fields` key) |
| Crossings | rows of secondary charged tracks with their parent; the primary's rows equal those of a primary-only recording (test build) |
| simroot | info, dump and hash at levels summary, crossings and hits; process numbers sorted by name; events ntuple equals the CSV; deposits summed per event equal the CSV's element totals; the same file twice is refused (duplicate key, exit 2); hits level above `max_events_hits` exits 2; an interrupted run (timeout) is incomplete, exit 3, no record |
| from-geometry | `evaluate_design.py geometry` on a J15 candidate (Example A's candidate with the J15 layout) and the J15 profile rebuild the hand-written §B.4.1 spec element by element, including field, physics, source, run and output; the same inputs give byte-identical specs; changing one layer position changes only that plane, changing the field only the field; unknown mapping version or geometry kind, a missing template and a derived spec failing check-spec exit 2 |
| Event-file size (J15, 1 GV protons, crossings level, compression 1) | 322 kB for 100 events (about 3.2 kB per event compressed; §B.1.4 estimated 4-8 kB before compression) |
| Offline and live tests | `tests/adapters/test_geant4_element.py`: 22 offline, 8 live (`HEP_GEANT4_LIVE_TEST=1`, config with `element_sim` and `element_sim_test_hooks`), all pass; `tests/adapters/test_geant4.py` and `test_g4sim.py` offline and live pass with the rebuilt layered_sim |

Decisions and deviations, recorded here:
- The `run` and `processes` rows are filled by worker 0, not the master (G-B1a). The event file's column lists are
  stored as strings in the `run` row so that simroot binds the columns without guessing.
- A source `cycle` (energy and direction per event, i mod n) is added to the gun so that the field check runs its 20
  trajectories in one run; `gps` and `event-file` are refused (interface only).
- Primary path lengths per element (`plen_<element>_mm`) are added to the CSV and the events ntuple: the material
  budget check and B2's `material-definition` need them.
- `seeds` of an element_sim spec must be the job seeds of its `logical_run_seed` (check-spec refuses others).
- Per-ntuple file sizes are not recorded (the reader does not give them); the file size, rows and per-ntuple hashes
  are.
- The derived thickness and positions are rounded to 1 nm in `from-geometry`, so a float rounding of x/X0 cannot
  reach the spec; the radiation length that converts x/X0 is the profile template's, with its source.
- `contracts/schema.py`: an adapter schema's `$ref` to a sibling file resolves next to it (the realization schema
  reuses the spec schema's definitions).
- The calorimeter leakage columns are the net outflow per face: energy carried back into the calorimeter mother is
  subtracted from the face it enters through, except the primary's first entry (in J15, backsplash returned by TOF2
  would otherwise count both as leakage and as deposit). In a vacuum world nothing re-enters, so layered_sim's
  world-face leakage and element_sim's agree in meaning there (G-B1b rerun after the change: the same numbers).
- An element_sim run stopped by a timeout or by SIGKILL, SIGTERM or SIGINT is incomplete (exit 3, no record); a crash
  or a Geant4 fatal exception (SIGABRT, SIGSEGV) is a failed run with a record. The run record's `spec_sha256` of an
  element_sim run is the sha256 of the spec file element_sim read, the same as the event file's run row.
- Not done in B1: the §A.8 new-problem agent run and the `review.py` Markdown review are done once for task B's
  Markdown in B3 (B3.8); a C++ `-ffp-contract=off` build is not needed by B1 (no portable random numbers in
  element_sim).

Independent review (a code-review agent that did not write the change, given the working tree and §B.5): eight
findings, all fixed before the final runs and covered by tests: event numbers past 2^31 - 1 would wrap in the event
file's 32-bit columns (refused by check-spec and element_sim); a crash was reported as an interrupted run (now failed);
the run record's spec hash differed from the event file's (now the same bytes); leakage counted energy that came back
(now net outflow); a field region on a repeated element crashed the field check (refused by check-spec); simroot
joined files of different logical runs (the run rows must agree in seed, column map, program, sources and Geant4
version); the column-order test could not see a C++ reordering (a live test compares the CSV header with
`element_spec.csv_columns`); a geometry file that is not an object gave a traceback (exit 2 now). The live tests and
G-B1b were rerun on the fixed build.

G5: element_sim, simroot and the SimProbe field section are written from the Geant4 API; no example code (B5 or any
other) was copied or adapted. Evidence: the 13 new or changed C++ files against all 5,657 `.cc`, `.hh`, `.icc` files of
the Geant4 11.4.3 examples tree, normalized lines: 0 shared runs of 3 or 4 consecutive lines (`g5_scan_k3.json`,
`g5_scan_k4.json`; the positive control of GEANT4-A8-CHECKS gives 51). Reviewer confirmation: confirmed by the
maintainer on 2026-10-25.

## GEANT4-A8-CHECKS (2026-10-24, E2; branch `worktree-geant4-a8` from main `263eff50`)

The §A.8 items left open by stages A1, C1 and A2, and the G5 evidence. Material in
`~/Workspace/hep-research-tasks/geant4-program/a8/` (problem statements, grading scripts, review project).

**New problems run by agents that did not write the code** (`PROBLEMS.md`, fixed before the runs; each agent got only
its problem text, in its own worktree at main 263eff50; graded from the files):

| Problem | Result | Problems the agent found |
|---|---|---|
| S (A1 + A2): stopping power of 150 MeV protons in 2 mm Al as a study evidence point, live Geant4 | S1-S6 pass (`grade_s.py`): per-event seeding with S = H(study_id, role, point_id), K = 16, 37,200 events from a 3,200-event trial; layered_sim's summary validates; effective config recorded; benchmark tree-v1 isolated, verdict pass, relative difference -0.00116, tolerance 0.0313; report claims no validation | `check_geant4_study.py run` refused layered_sim's own summary (it read run fields only `summary_from_csv.py` wrote): **fixed**, `geant4_run.py` completes the summary's run block; the study spec had no place for the stopping rule: **fixed**, optional `stopping_rule`; `HEP_GEANT4_CONFIG` is read only by tests (follow-up) |
| F (C1): F1 search on the collider-tracker example (not used by the C1 tests) | F1-F5 pass (`grade_f.py`): search record and spec, `validate.py` ok; 3 finalists expanded and evaluated (9 evaluations); report lists the search size and every finalist, no search value as a result; the grader's rerun on a fresh copy gives the same search summary except timing | a fixed base parameter outside its role-rule range and a constant constraint are accepted silently (follow-up). The harness refused the agent's report file; the grader saved the text the agent returned, unchanged |

**`review.py` Markdown reviews** (0.22.0 mechanism, `--lens-model design=opus --filter-model opus`, models opus and
sonnet, own configuration; reports `reviews/<id>/report.md`, advisory only):

| Document | Rounds | Agents | Outcome |
|---|---|---|---|
| `geant4-study-protocol.md` (A1 + A2), R8e77b3c0a5 | 2 | 23 | round 1: 26 findings kept after the filter and one arbitration, all disposed (22 changed with code or text, 1 partially changed, 3 adopted); round 2: further findings; one round-2 slot exhausted its attempts and is escalated: **open, waiting for a human `resolve`** |
| `system-design-workflow.md` (C1), Rf2030b632a | 3 | 25 | rounds 1-2: 53 findings disposed (text corrected; code gaps partially changed with the follow-up issue); round 3: one slot exhausted its attempts and is escalated: **open, waiting for a human `resolve`** |

Code changed from the reviews and the problems: `geant4_run.py scan` gives every point its own S also when the base
spec declares per-event seeding, derives S = H(study_id, role, point id) (`--study-id`, `--role`) and passes S, role
and point id to `run` (records are hash-v1); `check_geant4_study.py` matches the hadronic table by exact list name
and takes the EM constructor from the suffix or the list itself (Geant4 11.4.3 sources: option 4 in the
QGSP_BIC_HP family, GS in FTFP_BERT_TRV, LBE ignores suffixes); `convergence_plan.observables` accepts any declared
observable (leakage gates); rule `G4R-DATASETS` tested a field that does not exist and now applies. Each with a test.
Findings that need contract or design-code changes are listed in the follow-up issue and stated as limits in the text.
The last-round findings were applied to the plugin copies after the reviews' final rounds and were not re-reviewed.

**GEANT4-STOPPING-RULE**: external source added (de Heide and Grünwald, Psychon. Bull. Rev. 28 (2021) 795-812,
arXiv:1708.08278v5 Sec. 5.2 p. 20, read in full text; DOI confirmed at Crossref), gap closed.

**G5 evidence**: every new or changed C++ file of A2 (`g4sim/`, `layered_sim/`) against all 5,657 `.cc`, `.hh`, `.icc`
files of the Geant4 11.4.3 examples tree, normalized lines (whitespace and comments removed, trivial lines skipped):
0 shared runs of 3 or 4 consecutive lines; a reformatted copy of B1's RunAction.cc gives 51 (positive control).
Script and outputs: `g5_scan.py`, `g5_scan_k3.json`, `g5_scan_k4.json`, `g5_control.json`. The reviewer's
confirmation is the maintainer's to record.

## GEANT4-SUMMARY (2026-10-24, E2: macOS 26.5 arm64, Apple clang 21.0.0, CMake 4.3.2, Geant4 11.4.3 build A, Python 3.13; branch `worktree-geant4-a2` from main `dd531e74`)

Geant4 program stage A2 (spec `docs/dev/geant4-architecture/geant4-program.md` §A.6): geant4 adapter 0.2.0, shared
headers `g4sim/` and three boundary artifacts per run (run summary, column map, effective config). No contracts bump.
layered_sim was built from these sources against the recorded installation (Release, no `-ffp-contract=off`, as
before); a second build with `-DLAYERED_SIM_TEST_HOOKS=ON` adds the two test-only UI commands. Scripts in
`~/Workspace/hep-research-tasks/geant4-program/` (`a2_gate.py`, `a2_smoke.py`, `a2_negatives.py`,
`a2_thin_layer.py`, `a2_checks.sh`); outputs in `~/Workspace/geant4-work/a2-*`.

| Check | Result |
|---|---|
| G-A2 regression: every recorded J14 spec (26 in `recorded/specs/`, the spec's 18 plus A1's trials and the two `*-control-minus`; `mpv-density-10` does not exist, `sp-density-10` does) run with the reference build (sources of main after A1, sha256 d39225ea, the binary the A1 records name) and the A2 build (sha256 e6d3134d) on the same host | 26/26 `events.csv` bit-identical; 23 also equal the committed records' hashes; sp-nominal, sp-control and sp-density-10 were recorded with the older `sim-a` build (a69ffad7), where reference and A2 agree with each other |
| Probe leaves the random state unchanged (engine `put()` before and after, every run) | 26/26 `random_state_unchanged: true`; probe recorded in state GeomClosed for every run |
| Probe before BeamOn (`/layered_sim/test/probeAfterInitialize`, test build) | `recorded: false`, state Idle; the run's own probe recorded |
| Per-event seeding, 4000 events, K = 8, J14 MPV observables: serial, MT 2 and 4 threads, 2 serial jobs, 4 jobs of 2 threads | dumps and CSV rows bit-identical across the five layouts; summary integers identical, floats within 1e-12 |
| The same with a random gun (`/layered_sim/test/randomGun`: GeneratePrimaries draws y and z) | identical across the five layouts; gun positions vary per event |
| A2.9 oracle: the summary layered_sim writes against `core/simulation/summary.py` recomputed from the `%.17g` dump | every layout: integers identical, sum and sumsq within 1e-12 relative |
| Event weight != 1 with observables (secondary biasing of muIoni in SiRegion) | layered_sim exits 2 (`rejected`), no summary.json; without observables the same run is `ok` |
| tree-v1 against spec-v1 on the A2 runs (targets: each slab and all slabs) | same isolation decision for all 26; a deliberately inconsistent probe (air where spec/1 says vacuum, fake program) is refused, exit 2 |
| Effective configs stored once per content | the 26 J14 runs share 14 configs (for example mpv-nominal, mpv-nominal-trial and sp-nominal: same geometry, physics and seeding mode); mpv-pai has its own through the PAI regions the probe records (`em_parameters.extra`; an earlier probe without them gave mpv-pai the nominal's config, which is why they are recorded) |
| Thin-layer rule from the effective config (`check_geant4_study.py spec --effective-config`, J14 MPV and SP studies) | minimum thickness 0.3 mm from the tree (0.3 mm from spec/1); same applicable rules, none fired, same exit |
| `g4sim` self-tests (`tests/adapters/test_g4sim.py`, the system compiler) | H equals `core/simulation/seeds.py` on 206 vectors; the hex format equals `float.hex()` on 316 bit patterns including 0.0, -0.0, subnormals, inf, -inf and nan; SplitMix64 bit-identical; Box-Muller within 1e-12; SimSummary equals `core/simulation/summary.py` with numeric and string selections, merged from three accumulators too |

Decisions and deviations, recorded here:
- The canonical tree-v1 form and its hashes are computed in Python (`contracts.validate.geant4_tree_v1`) from the
  flat tree the probe writes, one implementation for every program (the spec puts the hash in `SimProbe.hh`).
  Target-relative transforms are quantized to 1 nm and 1e-12 so that a moved target does not change its hash
  through the rounding of the subtraction.
- `oneOf` and `not` are implemented in `contracts/schema.py` (not rewritten in `spec.schema.json`).
- The run record carries the effective config's reference, hash and geometry block (tree and hashes); the full
  content is in `effective_configs/<config_sha256>.json` under the work folder. Committed J14 records are not
  regenerated in A2 and stay spec-v1.
- The EM constructor is not named by the probe (`G4EmParameters` records parameters, not the constructor): the EM
  model assignment of variations stays `source: declared`; the hadronic one reads the probe first.
- The study scripts name semantic columns; runs before 0.2.0 resolve them through
  `skills/hep-detector/assets/geant4-columns-legacy.json` (data). `geant4_run.py summarize` keeps its CSV path for
  partitions made before 0.2.0.
- Not done in A2: GDML (off in the plugin's build), per-copy parameterisation details (recorded as a gap), the
  gamma-nuclear sub-process of `G4GammaGeneralProcess` (no accessor; recorded as a gap).

Independent review (a code-review agent that did not write the change, given the diff and §A.6): eight findings, all
fixed before the final gate and covered by tests: the tree-v1 reference placement chosen by hex-string order (a
moved repeated target changed its hash; now numeric); the probe-first hadronic assignment refused energies at the top
of a transition (edge convention aligned with the declared table); `summarize` crashed on summaries that do not merge
or have one block (caught; K >= 2 required); an observable with a string source column, `contains` on a number, or
blocks starting after the run crashed layered_sim in the event loop (refused in `validate_spec` and `Spec.cc`, and
caught in the event loop, exit 2); the neutron general process branch of the probe was unreachable (it derives from
`G4HadronicProcess` in 11.4; tested first now); `config_sha256` used JSON with whitespace (now sorted keys, no
whitespace, as the schema says); canonical ties were counted more than once. All checks above were rerun on the
fixed build.

G5: the new C++ (`g4sim/`, the layered_sim changes) is written from the Geant4 API; no example code was copied or
adapted. Reviewer confirmation: confirmed by the maintainer on 2026-10-24 (evidence: GEANT4-A8-CHECKS).

## GEANT4-CORRECTNESS (2026-10-24, E2v: Python 3.13 miniconda with SciPy 1.17.1, Geant4 11.4.3; branch `worktree-geant4-a1`)

Geant4 program stage A1 (spec `docs/dev/geant4-architecture/geant4-program.md` Part 2, approved 2026-10-24; §P.7 items
2-15 as recommended). Thirteen ledger entries, two documentation entries, advisories SFA-2026-039 (S1) and
SFA-2026-040 (S2). Contracts CV-A1 is gated at `GEANT4_A1_FROM` = 3.13.0, the unreleased minor it shares with CV-C1
(stage C1, PR #275, merged first); the regenerated J14 records are written at 3.13.0 and pass the rules natively.

| Entry | Severity | C | D | Parent -> fix |
|---|---|---|---|---|
| GEANT4-GRADE-TABLE | S2 | C2 | D2 | `91ea6fda` -> `c6a6ef7b` |
| GEANT4-SETUP-MATCHED-CLASS | S2 | C2 | D2 | `c6a6ef7b` -> `68e74877` |
| GEANT4-SCOPE-KIND | S2 | C2 | D2 | `68e74877` -> `c8c877a7` |
| GEANT4-SCOPE-MISSING-DIMENSION | S2 | C2 | D2 | `c8c877a7` -> `65423ff0` |
| GEANT4-ISOLATION | S2 | C2 | D1 | `65423ff0` -> `97c68cc6` |
| GEANT4-GATE-SCAN-COMPLETENESS | S2 | C2 | D2 | `97c68cc6` -> `aeae0875` |
| GEANT4-GATE-IUT | S2 | C2 | D1 | `48244412` -> `3710ac62` |
| GEANT4-BATCH-MEANS-SE | S1 | C2 | D1 | `48244412` -> `3710ac62` |
| GEANT4-LOW-COUNT-EXACT | S1 | C2 | D1 | `48244412` -> `3710ac62` |
| GEANT4-MPV-ESTIMATOR | S1 | C2 | D1 | `48244412` -> `3710ac62` |
| GEANT4-CONTROL-SHIFT | S2 | C1 | D1 | `48244412` -> `3710ac62` |
| GEANT4-DETECTION-LIMIT | S2 | C1 | D1 | `48244412` -> `3710ac62` |
| DESIGN-F4-LABEL-PASSTHROUGH | S4 | C1 | D2 | `aeae0875` -> `ced5a53e` |

**Discrimination.** Each evidence test was run on the parent and the fix commit (trees from `git archive`, the final
evidence test files copied in, no other adaptation):

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/contracts/test_geant4_a1.py::BenchmarkGradeTable::test_every_benchmark_and_declared_grade` | exhaustive | fail (assertion) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::BenchmarkGradeTable::test_a_self_declared_reference_grade_does_not_upgrade` | regression | fail (assertion) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::SetupMatchedClass::test_longitudinal_profile_takes_only_the_setup_matched_grade` | exhaustive | fail (assertion) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::ScopeKind::test_every_declared_kind_against_the_mpv_benchmark` | exhaustive | fail (assertion) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::ScopeKind::test_every_upgrading_benchmark_and_kind` | regression | fail (assertion) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::ScopeDimensions::test_each_dimension_missing_inside_or_outside` | exhaustive | fail (assertion) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::ScopeDimensions::test_a_scope_that_declares_only_the_kind_is_outside` | regression | fail (assertion) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::Isolation::test_missing_or_embedded_configuration_is_refused` | regression | error (error) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::Isolation::test_setup_matched_needs_the_measured_target_hash` | regression | error (error) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::Isolation::test_dependencies_re_derive_the_configuration_from_the_run_record` | regression | error (error) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::Isolation::test_configuration_against_an_independent_implementation` | exhaustive | error (error) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::ScanCompleteness::test_every_subset_of_the_declared_values` | exhaustive | fail (assertion) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::GateIUT::test_the_rule_on_cases_where_the_old_gate_decided_otherwise` | regression | fail (assertion) | pass | no | E2v |
| `tests/contracts/test_geant4_a1.py::GateIUT::test_pass_probability_against_the_normal_closed_form` | analytic | pass | pass | no | E2v |
| `tests/core/test_simulation_stats.py::BatchMeans::test_mean_se_and_covariance` | regression | pass | pass | no | E2v |
| `tests/core/test_simulation_stats.py::BatchMeans::test_exact_intervals_reuse_the_existing_ones` | regression | pass | pass | no | E2v |
| `tests/core/test_simulation_stats.py::BatchMeans::test_block_mode_is_the_parabola_vertex` | regression | pass | pass | no | E2v |
| `tests/skills/hep_detector/test_geant4_benchmarks.py::StoppingPower::test_both_directions_validate_the_detection_limit` | regression | error (error) | pass | no | E2v |
| `tests/core/test_simulation_stats.py::Decisions::test_welch_and_detection_limit` | regression | pass | pass | no | E2v |
| `tests/skills/hep_detector/test_design_f4_label.py::F4LabelPassthrough::test_b_a_refused_upgrade_is_incomplete_with_the_reasons` | regression | fail (assertion) | pass | no | E2v |
| `tests/skills/hep_detector/test_design_f4_label.py::F4LabelPassthrough::test_c_an_upgrade_without_results_is_incomplete` | regression | error (error) | pass | no | E2v |

The entries of D3-D5 share the wiring commit `3710ac62` (one summary-based rewrite carries them; the spec's §H.1
records it). Their tests either need the summary interface new in that commit (parent error) or test core functions
added in the foundation commit `8765fd92` (parent pass), so they are D1 and say so in `gaps`. No mutants were run (no
entry claims D3).

**S1 correctness** (`tests/core/test_simulation_s1_evidence.py`, 12 tests, pass): GEANT4-BATCH-MEANS-SE C3 (scipy.stats
sem and t.interval; sympy.stats Student-t coverage of the t half-width; shift, scale and permutation invariants;
negative control: the pre-fix event bootstrap covers below 0.60 on block-correlated runs where batch means cover
0.90); GEANT4-LOW-COUNT-EXACT C4 (exact enumeration of coverage for n = 1..30 and rate-ratio totals 1..25; scipy
binomtest exact intervals; complement and nesting invariants; negative control: the pre-fix normal interval covers
below 0.75 at n = 20, p = 0.05); GEANT4-MPV-ESTIMATOR C3 (numpy.polyfit through the three bin centres; Gaussian
elimination in exact rationals over every count triple 0..12; translation and scaling invariants; negative control:
on J14's expected peak the pre-fix five-point fit is biased above tol/10 = 0.002 at every bin phase, about +0.0032,
the three-point vertex about +0.0010). These tests pass on the parent too (the core functions predate the wiring
commit), so the S1 entries stay D1. The maintainer signed off all three on 2026-10-24 (`review`, scope: whole entry).

**Slow tier (HEP_SLOW_TESTS=1, `tests/core/test_simulation_toys.py`).** Gate toys (1e4 per cell) reproduce the A1.8
operating-characteristics table to 3 sigma_MC in every cell (TOST-only and two-stage columns); coverage toys of nominal
90 % batch-means intervals (2000 toys, K = 16) pass for mean, proportion, quantile and mode, and coverage_gate does not
fail; the detection-limit power at the claimed limit is >= 0.977 - 3 sigma_MC.

**MPV design (A1.7).** The first design (2 keV bins, B >= 30000, realised 34158) failed the bias criterion: 1000 Moyal
toys (1.5 xi, shape checked against the recorded 60k-event Geant4 histogram near the peak, 10-20 % flat
normalisation) gave a 95 % upper bound of the relative bias of 0.00209 against tol/10 = 0.002 for `mpv_deposit_MeV`
(200-toy runs at 30000: 0.0018, 0.00203); the true bias, about +0.0017, sat too close to the bound. Its parts: a
deterministic bias of the three-point parabola on the skewed peak (exact bin contents: +0.0010 at 2 keV, +0.00024 at
1 keV, scaling as w^2) and a noise part that falls with B. A scan of w x B (4000 multinomial toys each) showed that
narrower bins raise the se above the per-point target (1 keV, B = 50000: se 0.00395 against 0.00354), so the design
keeps 2 keV bins and raises the block size: B >= 75000 gives bias +0.00144, upper bound 0.00151, se 0.00256. The
criterion is unchanged. `tests/core/test_simulation_toys.py::MpvBiasToys` (4000 toys, exact multinomial block
histograms) passes at B = 75000. The pre-fix five-point fit is biased about +0.0032 at infinite statistics.

**J14 regeneration (A1.13, live).** layered_sim rebuilt from the adapter sources (sha256 d39225ea) against the
recorded Geant4 11.4.3 build. Trial runs fixed N with F_0.95(15, 15); the A1.7 design minimum B >= 75000 sets every
point of the MPV study to 1,200,000 events (the trials asked for at most 709,712); stopping-power scans 16,000 and
17,760. sp-nominal, sp-control and sp-density-10 were not re-recorded (blocks cut from their CSVs, legacy seeds).
Results: both convergence gates pass (MPV: mean deposit -0.00011 +- 0.00044, MPV deposit +0.0029 +- 0.0038, tail
fraction +0.006 +- 0.009; SP: +0.0009 +- 0.0017); statistical targets met; thin-layer-mpv rel +0.0149, DL 0.0700
(0.0827 before), controls +0.071 and -0.070 caught at the limit; stopping-power rel -0.0019, DL 0.0394, controls
+0.038 (legacy) and -0.040 caught; both studies re-issued validated-in-scope and pass `--strict` and dependencies.py.
recorded/ 2,630,783 bytes with the legacy summaries (largest file 316,443). MPV per-execution check: 0 fallback blocks, |block mean - merged
mode| 0.25 % against the bound 1.17 %. A first live recording at B >= 30000 (546,528 events) passed every criterion
too and was replaced by this one for the bias design.

Not run here: the independent new-problem agent run and the `review.py` Markdown review of §A.8, and the external
source for GEANT4-STOPPING-RULE (all done later, GEANT4-A8-CHECKS); the contracts version bump (at release).

## DESIGN-SEARCH-F1 (2026-10-24, Python 3.13.2 on macOS 26.5 arm64; E2 venv and the CI lock venv; branch `worktree-geant4-c1` from main `55849275`, unreleased)

Geant4 program stage C1 (automated candidate generation at F1), contracts 3.13.0 (CV-C1 placeholder). Environment
(section P.10.2): isolated worktree, branch `worktree-geant4-c1` (pushed from the agent worktree), base `55849275` =
the spec's baseline; C1 has no prerequisite stage; the `file:line` citations of Part 4 (`contracts/design.py` 65,
252-260, 384-394, 988-1062, 1369-1508, 1655-1683, 1949-2051; `evaluate_design.py` 462-560, 754-875, 837-875;
`contracts/schema.py` 61-63; the `main()` lines 192, 364, 453, 218, 282 of the five F1 tools; `geant4_verify.py` 132;
`system-design-workflow.md` 3-4, 149-150, 203-207) were rechecked on the base and all match. Synthetic projects only
(Example A and the design fixture); no Geant4 run except one geantino run to dump the materials table.

| Check | Result |
|---|---|
| Closure, DTLZ2 (3 objectives, 12 variables, searcher called directly, 200 x 100 = 2 x 10^4 evaluations, seed 12345; `test_design_search_lib.py`) | search-front hypervolume 0.978 of the true r^3 - pi/6 at r = 1.1 (pass condition >= 0.95); the final population alone reaches 0.904 |
| Closure, plane placement (N = 6, lever arm 1 m, measurement term only, minimum spacing L/32, 5000 evaluations through `search`) | A = 47.65 at (0, 0.496, 0.527, 0.558, 0.969, 1.0), from the exact rational oracle of section C Appendix A; pass condition A <= 47.66 x 1.01; equal spacing 66.96; the tool's search value gives the same A to 1e-9 |
| Closure, structure choice (Example A's design-spec, cand-S without its magnet, 0-1 bending slot) | every design without field has violation > 0; every feasible front design has the magnet and >= 3 planes; the report's verdict on each expanded finalist is not `fail` exactly when it was feasible on its search value |
| Closure, reproducibility | two runs of the same spec and seed: identical `search_summary` (timing excepted) and identical points file |
| Consistency (C1.4): in-process F1 values of finalists and sampled points against `evaluate_design.py run` | relative difference 0 for tracker_resolution, design_estimates budget-sum, charge_confusion_rate (chained), pid_separation_power, cherenkov_angle, calorimeter_resolution (tolerance 1e-12) |
| Search spec and cross-field rules; role rules and decoding; validity (range, spacing, envelope, overlap, nesting); summary schema and gating; orphan exemption; `design.search_point_not_expanded`; `expand --search` (finalists only) then `run`, `budget`, `report` (verdicts as usual, ranking refused without expected precision, search minus official listed) | `tests/skills/hep_detector/test_design_search.py` 29 tests, `test_design_search_lib.py` 10, `tests/contracts/test_design_search_contract.py` 10: pass |
| `materials.json` against the Geant4 11.4.3 dump it was taken from (`HEP_DESIGN_SEARCH_MATERIALS_DUMP`) | equal |
| Cost of an in-process F1 call (Example A, 3000 evaluations) | 0.5 ms per tool call; 12.5 s for 3000 evaluations with four calls each |
| Existing design tests (`tests/contracts/test_design_*.py`, `tests/skills/hep_detector/test_design_*.py`, `test_evaluate_design.py`, both design examples) | pass unchanged |
| `check_wiring.py`, `check_layering.py --strict`, `check_ownership.py`, `capability_map.py --check`, `check_routing_static.py` (458 cases), `measure_entrypoints.py` (hep-detector quick load 24669 B), `reference_inventory.py --check` | pass |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` (the CI pins) | clean |
| Contracts 3.13.0 bump | fixtures, design fixture, templates, theory-profile artifacts and 13 examples regenerated with E2: version strings and the hashes that cover them only |

| `run_all_checks.py --no-cli --jobs 6`, CI lock (NumPy 2.4.6, SciPy 1.17.1, no torch), head `60d48920` | 29 pass, 0 fail, 2 skipped (CLI host checks); 5293 tests in 440 modules, 5064 pass, 0 failures, 229 skipped |
| Same with E2 (NumPy 2.5.3) | 29 pass, 0 fail, 2 skipped; 5293 tests, 5156 pass, 0 failures, 137 skipped |
| `check_packaging.py` | ok, 2702 files, no findings |
| `python3 -m unittest discover -s tests/contracts -t .` | 1142 tests; 5 errors, all in `test_simulated_dataset.py` (the order dependence already recorded under HADRON-PHASE7; the module passes alone) |
| `check_relocation.py` | one failure, `tests.adapters.test_geant4` partition test: the worker command breaks on the space in the relocated path; this stage changes nothing under `adapters/` |

Not done in this stage: the independent
new-problem run by an agent that did not take part (C1.10, section A.8), the `review.py` Markdown review, the release
manifest. The adequacy table is unchanged; search values remain F1 optimistic bounds and decide nothing.

## 0.50.0 release check (2026-10-30, E2 and the CI lock)

Release branch `release/0.50.0`, based on main `72edcf08` (PR #325 merged). Minor release: it ships PR #325 (hep-detector
reconstruction methods by detector family: a new reference, 22 Crossref-verified citations, four routing cases).
Documentation and routing cases only: no script, contract or adapter change and no skill `description` change;
contracts 3.17.0 and `CORE_VERSION` 1.4.0 are unchanged; the ams02-research companion needs no change.

What changed on the release branch:
- version 0.50.0 in both manifests, `pyproject.toml`, the README, two assets, the six theory-profile scripts,
  `usine_translate.py` and `examples/bc-usine-reproduction/run.py`; a CHANGELOG `0.50.0` section;
- the theory-profile artifacts and examples regenerated, with only version strings and the hashes that cover them
  changing. 17 files (8 theory-profile files; the `detector-resolution`, `eic-profile-routing` and `recasting` outputs)
  reproduce that way on Linux with the CI lock (`efe33b36`). The others drift at rounding level between macOS arm64 and
  Linux x86_64 even with identical package versions, and E2 records NumPy 2.5.3 (the lock has 2.4.6), so they were
  regenerated on E2 (`~/.venvs/hep-research-e2`): 162 files in `16f778f4` and 2 in `91aea00b`. Every changed line is a
  version string or a hash (removed and added lines equal after masking both); no PNG changed. `published-comparison`
  takes its version from the `qed-prediction` output, so it must run after it (`91aea00b`).
- the README's package-size statement updated to the measured 71.3 MB (about 4400 files, the release manifest
  included): with the 0.50.0 manifest the package passed the 10% tolerance of `check_packaging.py` around the old 63.9 MB.

| Check | Result |
|---|---|
| `run_all_checks.py --part static --no-cli`, CI lock on Linux (Python 3.13.2) | 29 pass, 0 fail, 2 skipped (CLI host checks) |
| `tests/examples` (unittest), CI lock on Linux, at `16f778f4` | 176 tests, 0 failures, 22 skipped |
| `check_relocation.py`, CI lock on Linux, at `91aea00b` | 32 pass, 0 fail, 1 skipped; 6126 tests, 0 failures, 309 skipped |
| draft PR #326 Linux CI on `91aea00b` | every required job passes (22 pass, 2 skipped) |

The relocation check needs a local, project-free temporary folder on this host: with `TMPDIR` on the NFS home it hit
temporary-folder cleanup errors and the sticky-directory test, and under `/tmp` (which holds another user's `.git`) the
name extractors rightly refused the test folders as inside a project; with `TMPDIR` under `/var/tmp` it is clean. The
full suite was not run on E2 itself for this release (E2 was used for the regeneration only).

## 0.49.1 release check (2026-10-30, E2 and the CI lock)

Release commit `f6c295f9` on `release/0.49.1`, based on main `e6bd8326` (PR #322 merged). Documentation-only patch: it ships
the README rewrite (PR #322: the plugin README and the nine skill READMEs). No `SKILL.md`, reference, script, contract
or adapter changes; contracts 3.17.0 and `CORE_VERSION` 1.4.0 are unchanged; the ams02-research companion needs no
change.

What changed in the release commit:
- version 0.49.1 in both manifests, `pyproject.toml`, the README, two assets, the six theory-profile scripts,
  `usine_translate.py` and `examples/bc-usine-reproduction/run.py`;
- a CHANGELOG `0.49.1` section;
- the theory-profile artifacts and examples were regenerated with E2. Only version strings and the hashes that cover
  them change (195 files). `bc-propagation-fit` and `unfolding-coverage` results, which drift with the environment and
  carry no version, were left as committed.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 4`, E2 (Python 3.13.2) | 31 pass, 0 fail, 2 skipped (CLI host checks); 6126 tests, 0 failures, 166 skipped |
| Same with the CI lock (no torch) | 31 pass, 0 fail, 2 skipped; 6126 tests, 0 failures, 261 skipped |
| `check_relocation.py` | 32 pass, 0 fail, 1 skipped; 6126 tests, 0 failures |
| draft PR #323 Linux CI on `f6c295f9` | every required job passes (22 pass, 2 skipped) |

## 0.49.0 release check (2026-10-29, E2 and the CI lock)

Release commit `51948d5b` on `release/0.49.0`, based on main `cca361ed` (PR #320 merged). It ships the removal of the
retired cross-artifact check's entry points (PR #319; VALIDATION RETIRE-CROSS-ARTIFACT-CHECK) and the hep-authoring
follow-ups 2 (PR #320; VALIDATION AUTHORING-FOLLOWUPS-2).

Contracts 3.17.0, `CORE_VERSION` 1.4.0 and the adapters are unchanged. The ams02-research companion needs no change: it
requires hep-research >= 0.11.0 and uses none of the removed entry points.

What changed in the release commit:
- version 0.49.0 in both manifests, `pyproject.toml`, the README, two assets, the six theory-profile scripts,
  `usine_translate.py` and `examples/bc-usine-reproduction/run.py`;
- CHANGELOG `Unreleased` is now `0.49.0`;
- the theory-profile artifacts and examples were regenerated with E2. Only version strings and the hashes that cover
  them change: 196 files, the same set as in 0.48.0. `bc-propagation-fit` and `unfolding-coverage` results, which
  drift with the environment and carry no version, were left as committed.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 4`, E2 (Python 3.13.2) | 31 pass, 0 fail, 2 skipped (CLI host checks); 6126 tests in 483 modules, 0 failures, 166 skipped |
| Same with the CI lock (no torch) | 31 pass, 0 fail, 2 skipped; 6126 tests, 0 failures, 261 skipped |
| `check_relocation.py` | 32 pass, 0 fail, 1 skipped; 6126 tests, 0 failures: the two `test_geant4` path-with-spaces failures known since 0.45.0 are gone (fixed in PR #320) |
| draft PR #321 Linux CI on `51948d5b` | every required job passes (22 pass, 2 skipped) |

## 0.48.0 release check (2026-10-29, E2 and the CI lock)

Release commit `9d8ce930` on `release/0.48.0`, based on main `f4ddae5b` (PR #315 merged). It ships the retirement of
the cross-artifact check (VALIDATION RETIRE-CROSS-ARTIFACT-CHECK; contracts 3.17.0) and the hep-authoring follow-ups
(PR #317; VALIDATION AUTHORING-FOLLOWUPS).

`CORE_VERSION` 1.4.0 and the adapters are unchanged (the only `core/` change is one docstring word). The ams02-research
companion needs no change: it requires hep-research >= 0.11.0 and uses none of the retired entry points. ruff and mypy
with the CI pins were clean on `core/` and `contracts/` in PR #315; the release commit does not touch either.

What changed in the release commit:
- version 0.48.0 in both manifests, `pyproject.toml`, the README, two assets, the six theory-profile scripts,
  `usine_translate.py` and `examples/bc-usine-reproduction/run.py`;
- CHANGELOG `Unreleased` is now `0.48.0`;
- the theory-profile artifacts and examples were regenerated with E2. Only version strings and the hashes that cover
  them change: 196 files. `bc-propagation-fit` and `unfolding-coverage` results, which drift with the environment and
  carry no version, were left as committed.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 4`, E2 (Python 3.13.2, NumPy 2.5.3) | 31 pass, 0 fail, 2 skipped (CLI host checks); 6125 tests in 483 modules, 5959 pass, 0 failures, 166 skipped |
| Same with the CI lock (no torch) | 31 pass, 0 fail, 2 skipped; 6125 tests, 5864 pass, 0 failures, 261 skipped |
| `check_relocation.py` | only the 2 known geant4 path-with-spaces failures (`test_geant4` partition merges), identical to 0.47.0 |
| draft PR #318 Linux CI on `9d8ce930` | every required job passes (22 pass, 2 skipped) |

## 0.47.0 release check (2026-10-29, E2 and the CI lock)

Release commit `3673aa66` on `release/0.47.0`, based on main `a2852507` (PR #314 merged). It ships the hep-authoring
improvement task (VALIDATION AUTHORING-IMPROVE): the hep-review handoff and ownership row, sci-fix HEDGE-DONE-WHEN
(S3), the compact-ledger completion criteria, the bilingual routing row and the frozen authoring-pilot tools in the
repository's `evals/`.

Contracts 3.16.0, `CORE_VERSION` 1.4.0 and the adapters are unchanged. The sci-fix ledger gains HEDGE-DONE-WHEN
(documentation fix, S3, two located external sources). The ams02-research companion needs no change (it requires
hep-research >= 0.11.0). No change touches `core/` or `contracts/`, so the lint pins were not rerun.

What changed in the release commit:
- version 0.47.0 in both manifests, `pyproject.toml`, the README, two assets, the six theory-profile scripts,
  `usine_translate.py` and `examples/bc-usine-reproduction/run.py`;
- CHANGELOG `Unreleased` is now `0.47.0`;
- the theory-profile artifacts and 15 examples were regenerated with E2. Only version strings and the hashes that
  cover them change: 194 files, 486 lines each way, and no numeric line.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 4`, E2 (Python 3.13.2, NumPy 2.5.3) | 31 pass, 0 fail, 2 skipped (CLI host checks); 6299 tests in 494 modules, 6131 pass, 0 failures, 168 skipped |
| Same with the CI lock (no torch) | 31 pass, 0 fail, 2 skipped; 6299 tests, 6036 pass, 0 failures, 263 skipped |
| `check_relocation.py` | only the 2 known geant4 path-with-spaces failures (`test_geant4` partition merges), identical to 0.46.0 |
| draft PR #316 Linux CI on `3673aa66` | every required job passes (22 pass, 2 skipped) |

## 0.46.0 release check (2026-10-29, E2 and the CI lock)

Release commit `c1435a41` on `release/0.46.0`, based on main `36101c6f` (PR #312 merged). It ships gate G3 of the
hep-review skill (spec v9 T08):
- the held-out Codex-authored evaluation (`docs/dev/hep-review/g3-report.md`);
- the capability-claim lifecycle, with fingerprints taken at the measured commit;
- the support matrix and the regression suite.

Contracts 3.16.0, `CORE_VERSION` 1.4.0 and the adapters are unchanged. There is no sci-fix ledger entry. The
ams02-research companion needs no change (it requires hep-research >= 0.11.0).

What changed in the release commit:
- version 0.46.0 in both manifests, `pyproject.toml`, the README, two assets, the six theory-profile scripts,
  `usine_translate.py` and `examples/bc-usine-reproduction/run.py`;
- CHANGELOG `Unreleased` is now `0.46.0`;
- the theory-profile artifacts and 15 examples were regenerated with E2. Only version strings and the hashes that
  cover them change: 194 files, 486 lines each way, and no numeric line.

ruff 0.16.10 and mypy 2.4.0 (the CI pins) pass on `core/` and `contracts/`. The draft PR #313 ran Linux CI on the
release commit first, and every required job passed.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 4`, E2 (Python 3.13.2, NumPy 2.5.3) | 31 pass, 0 fail, 2 skipped (CLI host checks); 6298 tests in 494 modules, 6130 pass, 0 failures, 168 skipped |
| Same with the CI lock (no torch) | 31 pass, 0 fail, 2 skipped; 6298 tests, 6035 pass, 0 failures, 263 skipped |
| `check_relocation.py` | only the 2 known geant4 path-with-spaces failures (`test_geant4` partition merges), identical to 0.45.0 |
| PR #313 Linux CI on `c1435a41` | every required job passes |

## 0.45.0 release check (2026-10-29, E2 and the CI lock)

Release commit `c7105355` on the follow-up integration branch, based on main `31f39ee8`. It ships the cr-propagation
follow-up L1-L2 (decision B1.3; sections CRPROP-L1 and CRPROP-L2 above): contracts 3.16.0 (gating constant
`CONFORMANCE_VERSION_FROM`), `CORE_VERSION` 1.4.0, adapter `cr-propagation` 0.3.0 (usine and dragon2 0.3.0, emulator
1.0.0). No sci-fix ledger entry. The ams02-research companion needs no change (it requires hep-research >= 0.11.0).

What changed in the release commit: version 0.45.0 in both manifests, `pyproject.toml`, the README, two assets, the
theory-profile scripts and artifacts, `usine_translate.py` and `examples/bc-usine-reproduction/run.py`; CHANGELOG
`Unreleased` is now `0.45.0`; examples regenerated with E2 (only version strings and the hashes that cover them
change). ruff 0.16.10 and mypy 2.4.0 (the CI pins) pass on `core/` and `contracts/`. The draft PR #311 ran Linux CI on
the release commit first; every required job passed.

While PR #311 was in CI, main gained PR #310 (the new skill hep-review, protocol hep-review/1). It was merged into
the release branch (`fdd97d46`): CHANGELOG (hep-review's entry folded into 0.45.0), README (main's skill table and
size line, version 0.45.0) and the regenerated reference inventory; the release manifest was regenerated after it.
The table below is for `c7105355`; the merged tree was checked by the full E2 run and the PR #311 Linux CI listed
after the table.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 4`, E2 (Python 3.13.2, NumPy 2.5.3) | 31 pass, 0 fail, 2 skipped (CLI host checks); 6043 tests in 480 modules, 5875 pass, 0 failures, 168 skipped |
| Same with the CI lock (no torch) | 31 pass, 0 fail, 2 skipped; 6043 tests, 5780 pass, 0 failures, 263 skipped |
| `check_relocation.py` | only the 2 known geant4 path-with-spaces failures (`test_geant4` partition merges), identical on main |
| PR #311 Linux CI on `c7105355` | every required job passes |

## 0.44.0 release check (2026-10-29, E2 and the CI lock)

Release commit `93614c71` on the follow-up integration branch, based on main `42f5bad1`. It ships the cr-propagation
follow-up K1-K4 (decisions B1.1 and B1.2; sections CRPROP-K1 to CRPROP-K4 above): contracts 3.15.0 (gating constant
`MODULATION_FROM`), `CORE_VERSION` 1.3.0, adapter `cr-propagation` 0.2.0 unchanged. No sci-fix ledger entry. The
ams02-research companion needs no change (it requires hep-research >= 0.11.0).

The draft PR #309 ran Linux CI before the release commit and found two issues that the per-WP impacted tests missed:
K2's two new contract fixtures were not in the gate verdict snapshot (regenerated with `--write`, additions only), and
K1's longer `core-stats-guide.md` entry pushed hep-statistics `SKILL.md` + guide to 25647 B > 25600 (the 0.43.0 text
restored, the detail stays in `core-stats-commands.md`). Both fixed and verified before the release commit.

What changed in the release commit: version 0.44.0 in both manifests, `pyproject.toml`, the README, two assets, the
theory-profile scripts and artifacts, `usine_translate.py` and `examples/bc-usine-reproduction/run.py`; CHANGELOG
`Unreleased` is now `0.44.0`; examples regenerated with E2 (only version strings and the hashes that cover them
change). ruff 0.16.10 and mypy 2.4.0 (the CI pins) pass on `core/` and `contracts/`.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 4`, E2 (Python 3.13.2, NumPy 2.5.3) | 31 pass, 0 fail, 2 skipped (CLI host checks); 6031 tests in 480 modules, 5863 pass, 0 failures, 168 skipped |
| Same with the CI lock (no torch) | 31 pass, 0 fail, 2 skipped; 6031 tests, 5768 pass, 0 failures, 263 skipped |
| `check_relocation.py` | only the 2 known geant4 path-with-spaces failures (`test_geant4` partition merges), identical on main |
| PR #309 Linux CI on `93614c71` | every required job passes |

## 0.43.0 release check (2026-10-29, E2 and the CI lock)

Release commit `790ef3e7` on the cr-propagation integration branch, based on main `8fcbb826` (main has not moved since
0.42.0, so no rebase). It ships the cr-propagation r4 campaign (CRPROP-* sections above; report in
`docs/dev/cr-propagation/campaign-report.md`); contracts 3.14.0 and `CORE_VERSION` 1.2.0 become official (decision
A1.15), adapter `cr-propagation` 0.2.0. No sci-fix ledger entry. The ams02-research companion needs no change (it
requires hep-research >= 0.11.0).

What changed in the release commit: version 0.43.0 in both manifests, `pyproject.toml`, the README, two assets, the
theory-profile scripts and artifacts, `usine_translate.py` and `examples/bc-usine-reproduction/run.py` (run records
stamp the plugin version; committed campaign run records keep the version that produced them); CHANGELOG `Unreleased`
is now `0.43.0`; examples regenerated with E2: only version strings, the hashes that cover them and the platform
string change. ruff 0.16.10 and mypy 2.4.0 (the CI pins) pass on `core/` and `contracts/`.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 4`, E2 (Python 3.13.2, NumPy 2.5.3) | 31 pass, 0 fail, 2 skipped (CLI host checks); 6000 tests in 480 modules, 5832 pass, 0 failures, 168 skipped |
| Same with the CI lock (no torch) | 31 pass, 0 fail, 2 skipped; 6000 tests, 5737 pass, 0 failures, 263 skipped |
| `check_relocation.py` | only the 2 known geant4 path-with-spaces failures (`test_geant4` partition merges), identical on main |

After the release commit, PR #308's Linux CI failed on 8 float comparisons pinned on macOS and on the C2UF emulator's
near-singular kernel; fixed under decision A1.20 (section CRPROP-CIFIX), verified, and the release manifest regenerated.

## 0.42.0 release check (2026-10-26, E2 and the CI lock)

Release branch `release/0.42.0` from main `848c5eb4`. It ships #302-#306 (semantic naming P1-P5 and the fixes of the
spec's third review round, SEMANTIC-NAMING-P1-P2 and SEMANTIC-NAMING-P3-P5; the removal of the front-end "(moved)"
pointers); contracts 3.13.0, `CORE_VERSION` 1.1.0 and geant4 adapter 0.5.0 unchanged. No sci-fix ledger entry. The
ams02-research companion needs no change (it requires hep-research >= 0.11.0).

What changed in the release branch: version 0.42.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts carry the new version); CHANGELOG `Unreleased` is now `0.42.0`; examples
regenerated with E2 (`bc-propagation-fit` with the CI lock): only version strings and the hashes that cover them change
(`unfolding-coverage` restored); reference inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 31 pass, 0 fail, 2 skipped (CLI host checks); 5730 tests in 471 modules, 5576 pass, 0 failures, 154 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 31 pass, 0 fail, 2 skipped; 5730 tests, 5481 pass, 0 failures, 249 skipped |

## 0.41.0 release check (2026-10-26, E2 and the CI lock)

Release branch `release/0.41.0` from main `b50db9b4` (main CI green). It ships #294-#300 (FRONTEND-RECO-SIM with the
sci-fix FRONTEND-INJECTION-GAIN and the exit-code fix, FRONTEND-FE1 to FRONTEND-FE5, the simulated thin-silicon
spectrum); contracts 3.13.0, `CORE_VERSION` 1.1.0 and geant4 adapter 0.5.0 unchanged. The new ledger entry is a
documentation fix of text added in this cycle, so it changes no released number and needs no advisory. The
ams02-research companion needs no change.

What changed in the release branch: version 0.41.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts carry the new version); CHANGELOG `Unreleased` is now `0.41.0`; examples
regenerated with E2 (`bc-propagation-fit` with the CI lock): only version strings and the hashes that cover them change
(`unfolding-coverage` restored); reference inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 29 pass, 0 fail, 2 skipped (CLI host checks); 5601 tests in 458 modules, 5448 pass, 0 failures, 153 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 29 pass, 0 fail, 2 skipped; 5601 tests, 5356 pass, 0 failures, 245 skipped |

## 0.40.0 release check (2026-10-25, E2 and the CI lock)

Release branch `release/0.40.0` from main `9d12d8ae` (main CI green). It ships #289-#292 (F4-REFUSED-STUDY,
SEARCH-ROLES-1.1.0, DECLARED-SIZE-CONTROLS, DECLARED-SIZE-SLABS-TOF-OVERLAP); contracts 3.13.0, `CORE_VERSION` 1.1.0
and geant4 adapter 0.5.0 unchanged; no sci-fix ledger entry is unreleased. The ams02-research companion needs no
change.

What changed in the release branch: version 0.40.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts carry the new version); CHANGELOG `Unreleased` is now `0.40.0`; examples
regenerated with E2 (`bc-propagation-fit` with the CI lock): only version strings and the hashes that cover them change
(`unfolding-coverage` restored; J16 replays from its `recorded/sources/` snapshot, unaffected by the bump); reference
inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 29 pass, 0 fail, 2 skipped (CLI host checks); 5540 tests in 457 modules, 5387 pass, 0 failures, 153 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 29 pass, 0 fail, 2 skipped; 5540 tests, 5295 pass, 0 failures, 245 skipped |

## DECLARED-SIZE-SLABS-TOF-OVERLAP (2026-10-25, E2 and the CI lock; branch `feat/declared-size-slabs-tof-overlap` from main `c2236ba9`)

The two follow-ups left by DECLARED-SIZE-CONTROLS and SEARCH-ROLES-1.1.0.

`declared-size/1` for `stopping-power` and `thin-layer-mpv`: the expected shift of an areal-density injection d is
(1 + d) x Bethe at the shifted mid-slab energy over Bethe at the nominal one (stopping power: mean loss over the spec
thickness), and Delta_p of the scaled areal density over the nominal (MPV); the density effect stays at the spec
density's Sternheimer parameters. The injection must be in the control's run record (effective config, to 1e-6), as
for the multiple-scattering reference. `range` (its response depends on whether density or thickness changed) and
`longitudinal-profile` keep the window rule.

| Check | Result |
|---|---|
| Modelled response against J14's recorded Geant4 controls (an independent oracle: the shifts Geant4 produced) | stopping power +3.8 % / -4.0 % density: within 2 SE of +3.81 % / -3.98 %; MPV +-6.9 %: within 2 SE of +7.12 % / -7.03 % (slope above 1, as Delta_p ~ xi (ln xi + C)) |
| J14's controls under `declared-size/1` | not counted: its run records carry no effective config, so the injection cannot be checked; under the window rule J14 ran with they still count |
| `plan-controls --benchmark stopping-power` on J14's nominal | +- injections with expected shift +-1.25 x the planned DL; injection about equal to the shift (slope about 1) |
| Rule coverage | accepted for the three modelled benchmarks; refused for `range` and `longitudinal-profile` |
| TOF plane overlap in `search` (`test_tof_planes_against_trackers_and_extents`) | a TOF plane on a tracking plane (0.5 m in cand-S) or inside a calorimeter (front 2.2 m) is an overlap; as the calorimeter's daughter it is not; planes between tracker planes are valid |
| `test_proposals_are_flagged` | its TOF proposal moved between the tracker planes (0.125, 1.125 m): at the rule's default positions the first plane sat on cand-S's plane at 0 m and the design is now invalid |
| J14, J15, J16 regenerated | only tool hashes change; J16 (rules 1.0.0, no TOF positions) unchanged |
| `run_all_checks.py --no-cli --jobs 6`, E2 | 29 pass, 0 fail, 2 skipped; 5540 tests, 0 failures, 153 skipped |
| Same with the CI lock | 29 pass, 0 fail, 2 skipped; 5540 tests, 0 failures, 245 skipped |

## DECLARED-SIZE-CONTROLS (2026-10-25, E2 and the CI lock; branch `feat/declared-size-controls` on `feat/search-roles-geometry`)

Follow-up recorded at stages B3 and C3: the multiple-scattering reference refused J15 at 100 GV and J16 at 1 TV
because a +-13 % density control's shift exceeded 1.1 DL. The recorded controls (shift / DL): J15 1 GV +7.3/8.1 %,
-7.0/8.1 %; 100 GV +6.3/6.3 %, -8.1/6.3 % (refused); 500 GV +6.7/7.6 %, -6.7/7.3 %; J16 1 TV +5.7/6.6 %, -8.0/6.4 %
(refused); SE of a shift 0.9-1.1 %. The window between caught (|offset| > tolerance) and 1.1 DL is about 2.6-3.6 %
wide against that scatter, so even a well-sized control misses it often (about 0.8 for both controls at J16 1 TV,
centred), and the protocol's "inject an error of the DL's size" moves the width only about DL/2 (theta0 ~ sqrt(x)).
Decision (maintainer, 2026-10-25, option D, for new studies only; factors provisional): control rule
`declared-size/1`.

| Check | Result |
|---|---|
| `ms_expected_shift`: +-13 % areal density at 1 GV, 0.3 mm Si | +5.5 to 7.5 % and -6 to -8.5 %, minus side larger, 0 at 0 |
| J15's recorded 100 GV numbers under both rules | window rule refuses the minus control; declared-size/1: both sized and caught, claimed DL 8.14 % (the demonstrated shift) |
| Oversized (3.6 x planned DL), uncaught and undeclared controls | not counted; the claimed DL is never below a caught control's shift |
| `run_detector_benchmark` on synthetic dumps and records (+-13 % density) | the declared fields appear only with the rule; the window rule's output is unchanged |
| `plan-controls` from a nominal dump | +- injections whose expected shift is +-1.25 x the planned DL (to 1e-5), within the 1.5 ceiling |
| `control_rule` validation | an unknown rule, or declared-size/1 on another benchmark, is refused |
| J14, J15, J16 regenerated | only the `geant4_benchmarks.py` tool hash changes; J15's and J16's refusals stand (results identical) |
| `run_all_checks.py --no-cli --jobs 6`, E2 | 29 pass, 0 fail, 2 skipped; 5535 tests, 0 failures, 153 skipped |
| Same with the CI lock | 29 pass, 0 fail, 2 skipped; 5535 tests, 0 failures, 245 skipped |

Not done: a live study under the rule (it needs local Geant4 time, a new study id, and the maintainer's go-ahead);
`declared-size/1` for the slab benchmarks (their responses to an injection are not modelled).

## SEARCH-ROLES-1.1.0 (2026-10-25, E2 and the CI lock; branch `feat/search-roles-geometry` from main `8b41af25`)

Follow-up recorded at stage C2 (DESIGN-SEARCH-G4 limits): role rules 1.0.0 named a search-added TOF's and
calorimeter's parameters for the F1 tools only, so such a subsystem had no Geant4 geometry. Role rules 1.1.0
(`assets/design-search/roles.json`) name them in the design-geometry mapping's parameters: TOF `layer_positions_m`
(2 to 4 plane centres, minimum spacing 0.02 m), `layer_thickness_m`, `time_resolution_ps`, with the F1 flight path
`path_m` derived (last minus first plane); calorimetry-em `depth_x0` (the whole sampling structure), `passive_material`,
`front_position_m`, with `sampling_layers`, `passive_thickness_mm` (whole micrometres), `active_material` and
`active_thickness_mm` derived from the rule's template (20 layers of 5 mm polyvinyltoluene), the extent and budget from
that structure. 1.0.0 is kept as `roles-1.0.0.json` (`load_asset` reads `<stem>-<version>.json`), so recorded searches
(J16) expand unchanged.

| Check | Result |
|---|---|
| `test_design_search.py` on rules 1.1.0 (31 tests; new `test_earlier_rules_version_still_decodes`) | pass; budget and extent expectations recomputed by hand from the template |
| `test_design_search_g4.py` `DecodedSpecs`: TOF positions [-0.32, -0.30, 1.00, 1.02] m and 12 mm thickness, calorimeter depth 20 X0 on J15's base, through `geometry`, `from-geometry` (depth check within 1 %) and `check-spec` | pass (an unrounded passive thickness first gave sub-nanometre layer overlaps; rounding to 1 um fixed it) |
| J16 (`test_design_search_j16.py`, recorded 1.0.0 searches) | pass, results unchanged |
| `run_all_checks.py --no-cli --jobs 6`, E2 | 29 pass, 0 fail, 2 skipped; 5529 tests, 0 failures, 153 skipped |
| Same with the CI lock | 29 pass, 0 fail, 2 skipped; 5529 tests, 0 failures, 245 skipped |

Limits: the realization profile must still have the matching elements (`from-geometry` refuses a TOF plane count other
than the profile's); TOF planes enter no overlap check with other subsystems.

## F4-REFUSED-STUDY (2026-10-25, E2 and the CI lock; branch `fix/f4-refused-study` from main `ec403217`)

Follow-up recorded at stage C3 (J16 README review R0b7acaa370): `evaluate_design.py f4 --study` on a study record
whose `label --upgrade` had been refused wrote an F4 evaluation that decided nothing (ART-31), while the same refusal
through `f4 --label-spec` was already incomplete (exit 3). Now `label --upgrade` keeps a refusal's reasons in the record
(`extension.study.upgrade_refused`), and `f4` refuses such a record (exit 3, `upgrade-refused`, the reasons and the
record's gaps) and writes nothing. A study never labelled with `--upgrade` keeps the below-screening evaluation (tests
T33, T46, T47 and the staleness test of `test_design_m2.py` use it).

| Check | Result |
|---|---|
| `test_design_f4_label.py` (new `test_b2_f4_on_a_recorded_refusal_writes_nothing`; `test_b` checks the recorded reasons) | pass |
| J15 regenerated | criteria all pass; the refused SIM-N4/N6/N8-TRK100, SIM-N6-CC500 and SIM-N6-CAL10 evaluations are no longer written (`f4_written: false`); verdicts unchanged, the rows lose the row-8 entries |
| J16 regenerated | the confirmation gives `f4_exit` 3 and no evaluation; `REQ-TRK-001 cand-F937` stays inconclusive (its code is now the F1 bound's `bound.direction`); the diagnostic F4 row is gone; `test_design_search_j16.py` checks the refusal |
| J14 regenerated | study records name the new `check_geant4_study.py` hash only |
| Gate verdict snapshot | the 5 removed J15 evaluations dropped, nothing else |
| `run_all_checks.py --no-cli --jobs 6`, E2 | 29 pass, 0 fail, 2 skipped; 5528 tests, 0 failures, 153 skipped |
| Same with the CI lock | 29 pass, 0 fail, 2 skipped; 5528 tests, 0 failures, 245 skipped |

## 0.39.0 release check (2026-10-25, E2 and the CI lock)

Release branch `release/0.39.0` from main `bc7b1c18` (main CI green). It ships the Geant4 program stages A1, C1, A2,
B1, B2, B3, C2 and C3 with their §A.8 checks and G5 confirmations (#274-#287); contracts 3.13.0, `CORE_VERSION`
1.1.0, geant4 adapter 0.5.0, adequacy table 1.2.0 (provisional). The ams02-research companion needs no change.

What changed in the release branch: version 0.39.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts carry the new version); CHANGELOG `Unreleased` is now `0.39.0`; examples
regenerated with E2 (`bc-propagation-fit` with the CI lock), only version strings and the hashes that cover them change
(`unfolding-coverage` restored), and the design reports of Examples A and B now name adequacy table 1.2.0 (B2 bumped
it without regenerating them; no verdict changes); reference inventory regenerated. J16 now replays from a snapshot of
Examples A and B's 0.38.0 artifacts (`recorded/sources/`): its recorded searches name the design-spec by sha256, and
the regenerated sibling outputs changed it (`expand --search` refused: "the search spec ... changed since the
search"); `output/results.json` is byte-identical, and the gate verdict snapshot lists the 56 snapshotted artifacts
(all valid, strict too). The 13 sci-fix ledger entries of stage A1 name release 0.39.0, and advisories SFA-2026-039
and SFA-2026-040 are fixed in 0.39.0 (the first check run failed `test_scifix_ledger` on the missing `Unreleased`
section and the snapshot test on the new artifacts; both pass after these changes).

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 29 pass, 0 fail, 2 skipped (CLI host checks); 5527 tests in 456 modules, 5374 pass, 0 failures, 153 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 29 pass, 0 fail, 2 skipped; 5527 tests, 5282 pass, 0 failures, 245 skipped |

## 0.38.0 release check (2026-10-24, E2 and the CI lock)

Release branch `release/0.38.0` from main `38cbff8e` (main CI green). It ships #271: the maintainer's decisions on the
four spec questions of the M3 reviews (derived requirements `covered_by`, hard-constraint `subsystems`, the ADQ-02
offset value check, Example A's basis note) and the CHN-16 automation (`evaluate_design.py calibration`); contracts
3.12.0, adequacy table 1.1.0. The ams02-research companion needs no change.

What changed in the release branch: version 0.38.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is now `0.38.0`; examples regenerated
with E2 (`bc-propagation-fit` with the CI lock), only version strings and the hashes that cover them change
(`unfolding-coverage` restored); reference inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 29 pass, 0 fail, 2 skipped (CLI host checks); 5244 tests in 437 modules, 5108 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 29 pass, 0 fail, 2 skipped; 5244 tests, 5016 pass, 0 failures, 228 skipped |

## 0.37.0 release check (2026-10-24, E2 and the CI lock)

Release branch `release/0.37.0` from main `6aaef412` (main CI green). It ships #265-#269: the hep-detector system
design loop (detector system design spec v2, milestones M0-M4; contracts 3.11.0). The ams02-research companion needs
no change (it requires hep-research >=0.11.0).

What changed in the release branch: version 0.37.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is now `0.37.0`; examples regenerated
with E2 (`bc-propagation-fit` with the CI lock), only version strings and the hashes that cover them change
(`unfolding-coverage` drifted at 1e-14 and was restored); reference inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 29 pass, 0 fail, 2 skipped (CLI host checks); 5234 tests in 436 modules, 5098 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 29 pass, 0 fail, 2 skipped; 5234 tests, 5006 pass, 0 failures, 228 skipped |

## 0.36.0 release check (2026-10-24, E2 and the CI lock)

Release branch `release/0.36.0` from main `01b66bc2` (main CI green). It ships #263: hadron structure phase 7
(S12 PDF reweighting and profiling, S13 global fits, `covariance_fit.py` t0 mode; VALIDATION HADRON-PHASE7), the last
phase of the hadron-structure plan. Minor release with no contract change (contracts 3.10.0). The ams02-research
companion needs no change.

What changed in the release branch: version 0.36.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is now `0.36.0`; examples regenerated
with E2 (`bc-propagation-fit` with the CI lock), only version strings and the hashes that cover them change
(`unfolding-coverage` drifted at 1e-14 and was restored); reference inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 29 pass, 0 fail, 2 skipped (CLI host checks); 5104 tests in 427 modules, 4968 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 29 pass, 0 fail, 2 skipped; 5104 tests, 4876 pass, 0 failures, 228 skipped |

## 0.35.0 release check (2026-10-23, E2 and the CI lock)

Release branch `release/0.35.0` from main `f09c69d0` (main CI green). It ships #261: hep-theory hadron structure
phase 6 (Th19 small x, Th20 exclusive processes and GPDs; VALIDATION HADRON-PHASE6). Minor release with no contract
change (contracts 3.10.0). The ams02-research companion needs no change.

What changed in the release branch: version 0.35.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is now `0.35.0`; examples regenerated
with E2 (`bc-propagation-fit` with the CI lock), only version strings and the hashes that cover them change
(`unfolding-coverage` drifted at 1e-14 and was restored); reference inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 29 pass, 0 fail, 2 skipped (CLI host checks); 5091 tests in 425 modules, 4955 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 29 pass, 0 fail, 2 skipped; 5091 tests, 4863 pass, 0 failures, 228 skipped |

## 0.34.0 release check (2026-10-23, E2 and the CI lock)

Release branch `release/0.34.0` from main `9f627aaf` (main CI green). It ships #259: hep-theory hadron structure
phase 5 (Th18 SIDIS and TMDs, fragmentation functions; profile `theory:tmd-gaussian-lo`; VALIDATION HADRON-PHASE5).
Minor release with no contract change (contracts 3.10.0). The ams02-research companion needs no change.

What changed in the release branch: version 0.34.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is now `0.34.0`; examples regenerated
with E2 (`bc-propagation-fit` with the CI lock), only version strings and the hashes that cover them change
(`unfolding-coverage` drifted at 1e-14 and was restored); reference inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 29 pass, 0 fail, 2 skipped (CLI host checks); 5077 tests in 423 modules, 4941 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 29 pass, 0 fail, 2 skipped; 5077 tests, 4849 pass, 0 failures, 228 skipped |

## 0.33.0 release check (2026-10-23, E2 and the CI lock)

Release branch `release/0.33.0` from main `10d02330` (main CI green). It ships #257: hep-theory hadron structure
phase 4 (Th17 polarized DIS; profiles `theory:dis-parton-model` and `theory:drell-yan-lo`; VALIDATION HADRON-PHASE4).
Minor release with no contract change (contracts 3.10.0). The ams02-research companion needs no change.

What changed in the release branch: version 0.33.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is now `0.33.0`; examples regenerated
with E2 (`bc-propagation-fit` with the CI lock), only version strings and the hashes that cover them change
(`unfolding-coverage` drifted at 1e-14 and was restored); reference inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 28 pass, 0 fail, 2 skipped (CLI host checks); 5066 tests in 421 modules, 4930 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 28 pass, 0 fail, 2 skipped; 5066 tests, 4838 pass, 0 failures, 228 skipped |

## 0.32.0 release check (2026-10-23, E2 and the CI lock)

Release branch `release/0.32.0` from main `a022d0c1` (main CI green). It ships #255: hep-theory hadron structure
phase 3 (Th16, nuclear targets: `nuclear-parton-effects.md`, nPDF section of `pdfs-and-lhapdf.md`,
`nuclear_combination.py`; VALIDATION HADRON-PHASE3). Minor release with no contract change (contracts 3.10.0). The
ams02-research companion needs no change.

What changed in the release branch: version 0.32.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is now `0.32.0`; examples regenerated
with E2 (`bc-propagation-fit` with the CI lock), only version strings and the hashes that cover them change
(`unfolding-coverage` drifted at 1e-14 and was restored); reference inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 26 pass, 0 fail, 2 skipped (CLI host checks); 5062 tests in 421 modules, 4926 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 26 pass, 0 fail, 2 skipped; 5062 tests, 4834 pass, 0 failures, 228 skipped |

## 0.31.0 release check (2026-10-23, E2 and the CI lock)

Release branch `release/0.31.0` from main `81ea0cf8` (main CI green). It ships #253: hep-theory hadron structure
phase 2 (Th15, Drell-Yan: `drell-yan.md`, `drell_yan_lo.py`; VALIDATION HADRON-PHASE2). Minor release with no contract
change (contracts 3.10.0). The ams02-research companion needs no change.

What changed in the release branch: version 0.31.0 in both manifests, `pyproject.toml`, the README, two assets and the
theory-profile scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is now `0.31.0`; examples regenerated
with E2 (`bc-propagation-fit` with the CI lock), only version strings and the hashes that cover them change
(`unfolding-coverage` drifted at 1e-14 and was restored); reference inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 26 pass, 0 fail, 2 skipped (CLI host checks); 5053 tests in 420 modules, 4917 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 26 pass, 0 fail, 2 skipped; 5053 tests, 4825 pass, 0 failures, 228 skipped |

## 0.30.0 release check (2026-10-23, E2 and the CI lock)

Release branch `release/0.30.0` from main `ea8d15ad` (main CI green). It ships #251: hep-theory hadron structure
phase 1 (Th14, unpolarized inclusive DIS: `hadron-structure-essentials.md`, `dis-structure-functions.md`,
`structure_functions_lo.py`, `sum_rules.py`; VALIDATION HADRON-PHASE1). Minor release with contracts 3.10.0 (additive:
13 core convention keys and the `conditional_convention_keys` vocabulary). The ams02-research companion (requires
hep-research `>=0.11.0`, profile contracts `>=2.0`) needs no change.

What changed in the release branch:
- **Version 0.30.0:** both manifests, `pyproject.toml`, the README, three assets, and the theory-profile scripts
  (profile artifacts regenerated).
- **Contracts 3.10.0:** `CONTRACTS_VERSION` with its history comment, `contracts/vocab/core.json`, the two pinned
  tests, the fixtures (contract version only).
- **CHANGELOG:** `Unreleased` is now `0.30.0`, with an upgrade summary.
- **Examples:** regenerated with E2 (`bc-propagation-fit` with the CI lock). Only version strings and the hashes that
  cover them change; `unfolding-coverage` drifted at 1e-14 and was restored.
- **Reference inventory:** regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 26 pass, 0 fail, 2 skipped (CLI host checks); 5034 tests in 418 modules, 4898 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 26 pass, 0 fail, 2 skipped; 5034 tests, 4806 pass, 0 failures, 228 skipped |

## 0.29.0 release check (2026-10-23, E2 and the CI lock)

Release branch `release/0.29.0` from main `eba95d89` (main CI green). It ships #240-#249: hep-theory Th13 (cosmic-ray
propagation, cross sections, solar modulation, new-physics interpretation, `bartels_rotation.py`) with every source read
in full text (TH13-SOURCES); architecture step 1, the wiring lint `tools/check_wiring.py` with no known gap left; the
AMS-optionality CI job selected per module (plan 1.1.0); decisions D1-D3 and T2 with its live routing evaluation (D7);
the `data-pipelines.md` pointer removed. Minor release with no contract change (contracts 3.9.0). The ams02-research
companion (requires hep-research `>=0.11.0`) needs no change.

What changed in the release branch:
- **Version 0.29.0:** both manifests, `pyproject.toml`, the README, two assets, and the theory-profile scripts
  (profile artifacts regenerated).
- **CHANGELOG:** `Unreleased` is now `0.29.0`, with an upgrade summary.
- **Examples:** regenerated with E2 (`bc-propagation-fit` with the CI lock). Only version strings and the hashes that
  cover them change; `unfolding-coverage` drifted at 1e-14 and was restored.
- **Reference inventory:** regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 26 pass, 0 fail, 2 skipped (CLI host checks); 5013 tests in 415 modules, 4877 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 26 pass, 0 fail, 2 skipped; 5013 tests, 4785 pass, 0 failures, 228 skipped |

## 0.28.0 release check (2026-10-23, E2 and the CI lock)

Release branch `release/0.28.0` from main `f1daac78` (main CI green). It ships #238: the `model-card` and
`run-lineage` suites, model-only bundles and result bindings are removed (value gate Shrink, architecture section
13.4 steps 2 and 3), and readers refuse them with the reason. Minor release, contracts 3.9.0: sidecar formats are
removed, with no artifact type, vocabulary term, envelope field or capability change. The ams02-research companion
(requires hep-research `>=0.11.0`) needs no change.

What changed in the release branch:
- **Version 0.28.0:** both manifests, `pyproject.toml`, the README, the assets, and the theory-profile scripts
  (profile artifacts regenerated).
- **Contracts 3.9.0:** `contracts/__init__.py` (with its comment), `contracts/vocab/core.json`, the two pinned tests,
  the templates, and the fixtures (`make_fixtures.py`, E2; only the version pairs change).
- **CHANGELOG:** `Unreleased` is now `0.28.0`.
- **Examples:** regenerated with E2 (`bc-propagation-fit` with the CI lock). Only version strings and the hashes that
  cover them change; `unfolding-coverage` drifted at 1e-14 and was restored.
- **Reference inventory:** regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4979 tests in 412 modules, 4843 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 25 pass, 0 fail, 2 skipped; 4979 tests, 4751 pass, 0 failures, 228 skipped |

## 0.27.0 release check (2026-10-23, E2 and the CI lock)

Release branch `release/0.27.0` from main `568a7356` (main CI green). It ships:
- #235: the value gate re-measured on 0.26.0 (I = 0 of 28);
- #236: the Shrink decision, which deprecates the `model-card` and `run-lineage` suites (registry lifecycle
  `deprecated`, a CLI notice on stderr).

Minor release with no contract change (contracts 3.8.0). The ams02-research companion (requires hep-research
`>=0.11.0`) needs no change.

What changed in the release branch:
- **Version 0.27.0:** both manifests, `pyproject.toml`, the README, two assets, and the theory-profile scripts
  (profile artifacts regenerated).
- **CHANGELOG:** `Unreleased` is now `0.27.0`.
- **Examples:** regenerated with E2 (`bc-propagation-fit` with the CI lock). Only version strings and the hashes that
  cover them change; `unfolding-coverage` drifted at 1e-14 and was restored.
- **Reference inventory:** regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 5026 tests in 414 modules, 4889 pass, 0 failures, 137 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 25 pass, 0 fail, 2 skipped; 5026 tests, 4797 pass, 0 failures, 229 skipped |

## 0.26.0 release check (2026-10-23, E2 and the CI lock)

Release branch `release/0.26.0` from main `8f03228b` (main CI green). It ships:
- #225: the value-gate decision changed to Continue;
- #226 to #228: R2 formats, the 1.1.0 input checks, and the rule fixes G3, G17, G4 and G5;
- #229 and #230: selective pull-request CI;
- #231: the run-lineage fixes G6, G7, G8, G13 and A3;
- #232 and #233: R3, with G1 under the broad scope, G14, catalog 1.1.0, the stable 1.1.0 suites, full mutation
  testing and the report-check fix.

Minor release, contracts 3.8.0:
- check-context 1.1.0, result binding 1.1.0, registry 1.2.0 and catalog 1.1.0;
- three terms added to the `response_corrections` vocabulary;
- no artifact type, envelope field or capability change.

The ams02-research companion (requires hep-research `>=0.11.0`) needs no change.

What changed in the release branch:
- **Version 0.26.0:** both manifests, `pyproject.toml`, the README, the assets, and the theory-profile scripts
  (profile artifacts regenerated).
- **Contracts 3.8.0:** `contracts/__init__.py` (with its comment), `contracts/vocab/core.json`, the two pinned tests,
  the templates, and the fixtures (`make_fixtures.py`, E2; only the version pairs change).
- **CHANGELOG:** `Unreleased` is now `0.26.0`, with a "Before you upgrade" summary.
- **Examples:** regenerated with E2 (`bc-propagation-fit` with the CI lock). Only version strings and the hashes that
  cover them change. `unfolding-coverage` drifted at 1e-14 and was restored; `stats-benchmarks` has no generator.
- **Reference inventory:** regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 5024 tests in 414 modules, 4887 pass, 0 failures, 137 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 25 pass, 0 fail, 2 skipped; 5024 tests, 4795 pass, 0 failures, 229 skipped |

## 0.25.1 release check (2026-10-22, E2 and the CI lock)

Release branch `release/0.25.1` from main `ed1f19d9` (#222 architecture clean-up edition; #223 value gate of the
cross-artifact check, AI-planted, I = 0 of 28, outcome Stop chosen by the maintainer, checker marked experimental;
main CI green). Patch release, contracts 3.7.0 unchanged; no behavior change; no ledger entry or advisory changes
release (none is unreleased). The ams02-research companion (requires hep-research `>=0.11.0`) needs no change.

What changed: version 0.25.1 in both manifests, `pyproject.toml`, the README, the two assets and the theory-profile
scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is `0.25.1`. Examples regenerated (E2;
`bc-propagation-fit` with the CI lock): only version strings and the hashes that cover them change;
`unfolding-coverage` drifted at 1e-14 and was restored.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4955 tests in 410 modules, 4819 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 25 pass, 0 fail, 2 skipped; 4955 tests, 4727 pass, 0 failures, 228 skipped |

## 0.25.0 release check (2026-10-22, E2 and the CI lock)

Release branch `release/0.25.0` from main `0414f783` (#220 cross-artifact check Phase 0, release R1: version guard,
rule source digests and registry 1.1.0, P6, default snapshots, cheap check-report refusals, the code-name rename;
main CI green). Minor release, contracts 3.7.0 (registry 1.1.0; no artifact type, vocabulary term, envelope field or
capability change); no ledger entry or advisory changes release (none is unreleased). The ams02-research companion
(requires hep-research `>=0.11.0`) needs no change.

What changed: version 0.25.0 in both manifests, `pyproject.toml`, the README, the assets and the theory-profile
scripts (profile artifacts regenerated); contracts 3.7.0 in `contracts/__init__.py` (with its comment),
`contracts/vocab/core.json`, the two pinned tests, the templates and the fixtures (`make_fixtures.py`, E2); CHANGELOG
`Unreleased` is `0.25.0`. Examples regenerated (E2; `bc-propagation-fit` with the CI lock): only version strings and
the hashes that cover them change; `unfolding-coverage` drifted at 1e-14 and was restored. Reference inventory
regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4955 tests in 410 modules, 4819 pass, 0 failures, 136 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 25 pass, 0 fail, 2 skipped; 4955 tests, 4727 pass, 0 failures, 228 skipped |

## 0.24.1 release check (2026-10-22, E2 and the CI lock)

Release branch `release/0.24.1` from main `a183b6ba` (#216 weekly ledger-evidence job and TH9-MASSES PDG record; #217
core/stats trace forwarding; #218 oracles not from transcribed formulas for DR-WP1-01, DR-WP1-02, DR-WP2-06-CALO,
DR-WP2-06-MS kept C3 by maintainer decision; main CI green on all three). Patch release, contracts 3.6.0 unchanged; no
ledger entry or advisory changes release (none is unreleased). The ams02-research companion (requires hep-research
`>=0.11.0`) needs no change.

What changed: version 0.24.1 in both manifests, `pyproject.toml`, the README, the two assets and the theory-profile
scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is `0.24.1`. Examples regenerated (E2; `bc-propagation-fit`
with the CI lock): only version strings and the hashes that cover them change. Reference inventory regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4909 tests in 408 modules, 4775 pass, 0 failures, 134 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 25 pass, 0 fail, 2 skipped; 4909 tests, 4658 pass, 0 failures, 251 skipped |

## 0.24.0 release check (2026-10-22, E2 and the CI lock)

Release branch `release/0.24.0` from main `d0a9f799` (#201 REVIEW-REFS-3; #202-#205 and #207-#212 the sci-fix
improvement plan, contracts 3.5.0, advisory format /2; #206 PERIODICITY-REFIT and the namespaced-efficiency warning;
#213 expert slot, per-review configuration and filter-packet scrub, contracts 3.6.0; #214 REVIEW-REFS-4). Minor
release. The ams02-research companion (requires hep-research `>=0.11.0`, profile contracts `>=2.0`) needs no change.

What changed: version 0.24.0 in both manifests, `pyproject.toml`, the README, the two assets and the theory-profile
scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is `0.24.0`; the four unreleased ledger entries
(SCAN-VERDICT-ORDER, SCAN-MISSING-MARKER, ADVISORY-MATCH-V2, PERIODICITY-REFIT) record release 0.24.0; advisory
SFA-2026-038 (PERIODICITY-REFIT) gets its `fixed` event 0.24.0. Examples regenerated (E2; `bc-propagation-fit` with
the CI lock): only version strings and the hashes that cover them change (`unfolding-coverage` left as committed).

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4904 tests in 408 modules, 4770 pass, 0 failures, 134 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 25 pass, 0 fail, 2 skipped; 4904 tests, 4678 pass, 0 failures, 226 skipped |

## 0.23.0 release check (2026-10-22, E2 and the CI lock)

Release branch `release/0.23.0` from main `59002566` (#197 anisotropy CL range, `bdt-backend` gate, 24 triaged plugin
issues; #198 REVIEW-REFS-2; #199 per-lens model and filtering pass, contracts 3.4.0; main CI green on all three).
Minor release. The ams02-research companion (requires hep-research `>=0.11.0`, profile contracts `>=2.0`) needs no
change.

What changed: version 0.23.0 in both manifests, `pyproject.toml`, the README, the two assets and the theory-profile
scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is `0.23.0`; new advisory SFA-2026-037
(TRAINING-MEMORY-VERDICT, fixed 0.23.0; the other new S2 entries change only the status of unusable input or a
missing dependency, where no result was produced). Examples regenerated (E2; `bc-propagation-fit` with the CI lock):
only version strings and the hashes that cover them change (`unfolding-coverage` drifted at 1e-14 and was left as
committed).

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4795 tests in 403 modules, 4663 pass, 0 failures, 132 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 25 pass, 0 fail, 2 skipped; 4795 tests, 4571 pass, 0 failures, 224 skipped |

## 0.22.0 release check (2026-10-22, E2 and the CI lock)

Release branch `release/0.22.0` from main `9db118e5` (#194 independent review P1, contracts 3.3.0; #195 the five
reference corrections REVIEW-REFS, the S1 sci-fix ANISO-WEIGHTED-COV and REVIEW-CODE-WARN; main CI green on both PRs).
Minor release. The ams02-research companion (requires hep-research `>=0.11.0`, profile contracts `>=2.0`) needs no
change.

What changed: version 0.22.0 in both manifests, `pyproject.toml`, the README, the two assets and the theory-profile
scripts (profile artifacts regenerated); CHANGELOG `Unreleased` is `0.22.0`; advisory SFA-2026-036 gets its `fixed`
event 0.22.0. Examples regenerated (E2; `bc-propagation-fit` with the CI lock): only version strings and the hashes
that cover them change (`unfolding-coverage` drifted at 1e-14 and was left as committed).

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4707 tests in 395 modules, 4575 pass, 0 failures, 132 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) | 25 pass, 0 fail, 2 skipped; 4707 tests, 4484 pass, 0 failures, 223 skipped |

## REVIEW-FILTER-PASS (2026-10-22, Python 3.13.2 on macOS 26.5 arm64; E2 venv and the CI lock venv; branch `feat/review-filter-pass` from main `5350266b`, unreleased)

Two optional settings of the independent review from the P3 tuning run (`p3-tune` report: Haiku design-lens slots
missed their canaries in 8 of 9 attempts; one Opus filtering pass raised precision from 0.53 to 0.88 at about 2% of the
review's tokens), contracts 3.4.0. `lens_models` (`start --lens-model LENS=MODEL`) fixes the model of a lens's lens
slot in every round; `filter` (`start --filter-model M`) adds a filtering pass at decide row 8a, after round 1's
records are received and before escalation, arbitration and dispose, with the new sidecar format
`review_filter_record` 1.0.0 (spec sections 5.1, 5.5, 6.9, 7.5, A2, A8). Synthetic data only; no live agent run.

| Check | Result |
|---|---|
| New tests: `tests/skills/hep_authoring/test_review_lens_models.py` (7), `test_review_filter_pass.py` (19), `tests/contracts/test_review_filter_contract.py` (20) | 46 pass. Covered: allocation without `lens_models` equal to the 0.22.0 function on 7,848 seed, lens, model, offset and plan combinations and on the harness review; the fixed lens slot and the shadow moving off its model; config and start refusals; an end-to-end review driven by `next` with the filter (one rejected attempt, then accepted), dispose with the filter's advice, a re-review round keeping the fixed design model and running no second filter, close and `check` exit 0; the filter packet holding no slot id, lens, role, model, reviewer name or reviewer finding id; receipt codes for a missing, repeated or unknown id, an unknown decision, `duplicate_of` a dropped finding, same identity, prior conversation, dispatch mismatch, forbidden read and wrong hash; exhaustion after two attempts (not escalated, report says not applied); returned-empty and timeout through rows 5 and 6; `check --record-only --role filter`; `artifacts_changed` on an edited filter record; the spec 5.5 table against the schema; row 8a in an exhaustive slot-state test; the fixtures in `contracts/fixtures/review/` (2 valid, 7 invalid); unchanged behaviour without either option |
| Unchanged without the options | the P1 end-to-end review (`run_e2e`): review directory and private directory byte-identical to main `5350266b` (172 files, sha256 per file) |
| `run_all_checks.py --no-cli --jobs 6`, E2 (NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4795 tests in 403 modules, 4663 pass, 0 failures, 132 skipped |
| Same with the CI lock (NumPy 2.4.6, SciPy 1.17.1, no torch) | 25 pass, 0 fail, 2 skipped; 4795 tests, 4571 pass, 0 failures, 224 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |
| Contracts 3.4.0 bump | fixtures (`make_fixtures.py`), templates, theory-profile artifacts and examples regenerated (E2; `bc-propagation-fit` with the CI lock): version strings and the hashes that cover them only; `unfolding-coverage` drifted at 1e-14 and was restored |

Both gate runs were on the final tree before this section was written (commit `6113ed8b` plus the report-layout fix
and the CHANGELOG entry committed after it). Not run: live agent reviews with either option, so the precision gain and
the design-lens fix are the tuning run's evidence, not this branch's. Skipped tests are unverified, not passed.

## BDT-BACKEND-GATE (2026-10-22, Python 3.13.2 on macOS 26.5 arm64; CI lock venv with xgboost 3.4.1 and scikit-learn 1.9.1, E2 venv without them; branch `fix/aniso-cl-bdt-gate`)

The tests of `skills/hep-ml/scripts/train_bdt.py` and `export_bdt.py` that need xgboost or scikit-learn, and the BDT
path of the analysis-to-paper example, skipped in every required CI job: none installs the `bdt` extra. New required
job `bdt-backend` (modelled on `torch-backend`): the CI lock plus `xgboost==3.4.1`, `scikit-learn==1.9.1` and
scikit-learn's dependencies outside the lock `joblib==1.6.0`, `narwhals==2.27.1`, `threadpoolctl==3.7.0` (the versions
of the CI lock venv), and `tools/run_required_backends.py --require xgboost==3.4.1,sklearn==1.9.1` over
`tests.examples.test_analysis_to_paper`, `tests.skills.hep_ml.test_train_bdt` and
`tests.skills.hep_ml.test_train_bdt_extensions`, so a test skipped for either backend fails the job. The gate matches
skip reasons by import name, so the two scikit-learn skip reasons now name `sklearn` (before, a scikit-learn skip
would not have counted as a skip for the backend). `tests/tools/test_pyproject.py`: every test module that marks an
xgboost or scikit-learn test is listed, its scikit-learn skip reasons name `sklearn`, and the job pins every package
of the extra within the extra's range (dropping a module or pinning scikit-learn 2.0.0 fails it).

- The job's command, run as the job runs it (CI lock venv with the backends): 44 run, 0 failures, 0 errors, 2 skips
  not for a backend (PyROOT for the RooFit cross-check; `test_tmva_without_root_exits_3_with_a_hint`, skipped where
  ROOT is importable, which it is not on the CI runner), `skipped_for_a_required_backend` empty, exit 0, about 49 s.
- Without the backends (E2 venv): exit 1, both backends reported not importable and 25 tests skipped for them
  (xgboost and sklearn reasons both caught).
- Branch protection is a repository setting: `bdt-backend` must be added to the required status checks there; the
  workflow cannot make it required by itself (as for `torch-backend`).

## TRIAGE-A (2026-10-22, Python 3.13 on macOS arm64; E2 venv (pyhf, NumPy, SciPy, uproot, awkward, PyYAML, torch; no coffea, pyarrow, hepdata_lib) and the CI lock venv; branch `fix/triage-A`)

Plugin triage batch A (TRIAGE.md T16, T17, T18, T19, T21, T33, T34), all on the hep-computing script contract
(skills/hep-computing/SKILL.md: 0 ok, 1 negative verdict, 2 bad input, 3 missing dependency or incomplete; names in
core/status.py). Every item reproduced on the tree before its fix. Parent for every row: `b45e4037` (main, 0.22.0)
with the fix commit's evidence test files copied in (only test files added or replaced; no code under test touched).
Fix result: the fix commit's own tree (`git archive`). Each test run on its own with `python -m unittest <id>`.

Fix commits: T17 `018e7b23` (sci-fix CLI-MISSING-INPUT-EXIT2); T19 and T18 code `61920170` (sci-fix
ADAPTER-MISSING-DEPENDENCY, PYHF-REJECTED-STATUS); T18 docs `14c0ff94` (STATUS-REFUSED-MEANING); T33/T34 `117f5375`
(sci-fix TRAINING-MEMORY-VERDICT); T21 `17a3dad8` (robust-fix RUN-ALL-CHECKS-GIT); T16 `01d8f357` (robust-fix
STATUS-UNKNOWN-EXIT).

**Correctness.** S2 items (C2): the contract applied exhaustively over a stated domain (basis exhaustive): every tool in
MISSING_FILE_ARGS (108; T17), every adapter tool and every third-party module it imports, found from the source
(14 tools, 28 pairs; T19), every input-refusal path of the two pyhf model checks (6; T18), and a 216-configuration grid
of the memory estimator plus two closed-form anchors (T33). S4 items (C1): behavioral.

**Discrimination (D2):**

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/test_cli_contract.py::CliContract::test_refused_input_prints_a_json_status` (tightened) | exhaustive | fail (assertion): geant4_build, hepdata_export, hepdata_record, calorimeter_resolution, multiple_scattering, pileup_reweight exit 1 | pass (018e7b23) | no | E2 |
| `tests/skills/hep_detector/test_detector_helpers.py::PileupReweightTests::test_cli_missing_file_fails_cleanly` (now expects 2) | behavioral | fail (assertion): 1 != 2 | pass (018e7b23) | no | E2 |
| `tests/adapters/test_adapter_missing_dependency.py::AdapterMissingDependency::test_each_hidden_module_gives_exit_3_and_status_missing_dependency` | exhaustive | fail (assertion): 24 of 28 pairs (all but dragon2_to_prediction/numpy and unfold.py/numpy, pyunfold, ROOT) | pass (61920170) | no | E2 |
| `tests/adapters/test_adapter_missing_dependency.py::AdapterMissingDependency::test_domain_is_every_adapter_with_a_third_party_import` (domain completeness, not a verdict test) | behavioral | pass | pass (61920170) | no | E2 |
| `tests/adapters/test_pyhf_nuisance_diagnostics.py::NoPyhf::test_exits_3_without_pyhf` (was the exit-2 test) | behavioral | fail (assertion): exit 2 | pass (61920170) | no | E2 |
| `tests/adapters/test_pyhf_adapter_statuses.py::PyhfAdapterRejectedInput::test_unreadable_or_unmappable_input_is_rejected_with_exit_2` | exhaustive | fail (assertion): 6 subtests, status refused | pass (61920170) | no (pyhf installed; in the stats-backends gate) | E2 |
| `tests/skills/hep_ml/test_training_memory_verdict.py::TrainingMemoryVerdict::test_closed_form_anchors` | behavioral (closed-form anchor) | fail (error): no status key, 2 subtests | pass (117f5375) | no | E2 |
| `tests/skills/hep_ml/test_training_memory_verdict.py::TrainingMemoryVerdict::test_exit_code_and_status_follow_the_verdict_over_the_grid` | exhaustive | fail (assertion): exit 0 / no status for the configurations that do not fit | pass (117f5375) | no | E2 |
| `tests/skills/hep_ml/test_training_memory_verdict.py::TrainingMemoryVerdict::test_the_text_report_fails_with_exit_1` | behavioral | fail (assertion): exit 0 | pass (117f5375) | no | E2 |
| `tests/skills/hep_ml/test_training_memory_verdict.py::TrainingMemoryVerdict::test_report_and_json_state_micro_batch_and_sequence_length` (T34) | behavioral | fail (error): no micro_batch key | pass (117f5375) | no | E2 |
| `tests/skills/hep_ml/test_hep_ml_skill.py::MemoryEstimateCliTests::test_text_report_names_the_binding_term` (now expects 1) | behavioral | fail (assertion): 0 != 1 | pass (117f5375) | no | E2 |
| `tests/tools/test_run_all_checks_git.py::GitFailureSummary::test_git_timeout_still_writes_the_summary` | behavioral | fail (error): TimeoutExpired out of main | pass (17a3dad8) | no | E2 |
| `tests/tools/test_run_all_checks_git.py::GitFailureSummary::test_missing_git_still_writes_the_summary` | behavioral | fail (error): FileNotFoundError out of main | pass (17a3dad8) | no | E2 |
| `tests/core/test_status.py::SharedVocabulary::test_unknown_status_is_incomplete_with_a_message_not_a_traceback` | behavioral | fail (error): KeyError/TypeError, 6 subtests | pass (01d8f357) | no | E2 |
| `tests/core/test_status.py::SharedVocabulary::test_a_script_with_an_unknown_status_exits_3_without_a_traceback` | behavioral | fail (assertion): exit 1 with a traceback | pass (01d8f357) | no | E2 |

Also run in the CI lock venv (no pyhf, uproot, awkward, PyYAML): the T17 contract survey (the only exit 3 is
inspect_checkpoint.py with missing-dependency) and the T19 pair test pass. No local mutants run (D2, not D3).

**Decisions.** T17: the hep-detector scripts echo the artifact label under "status", so a missing file uses their
existing exit-2 shape (`status` failed, `error_kind` invalid-input, as their tool contracts declare for exit 2); the
adapters print `rejected`. Invalid file content keeps its documented exit 1. T18: "refused" stays exit 1 in
core/status.py (most tools that print it use 1 and document it); the protected guard's exit 3 is a documented contract
and is written down as the exception; the pyhf model checks moved to `rejected`. T16: an unknown status maps to 3 with
a stderr message (the outcome cannot be classified), not 2 (the user's input was not at fault) and not a raise (an
uncaught exception exits 1). T19: no shared helper (the adapters share no module). Not changed: the root-uproot entries
stay in JSON_STATUS_FOLLOW_UP (with PyROOT or uproot installed a missing input is still a text error).

## TRIAGE-B checker gaps (2026-10-22, Python 3.13.2 on macOS 26.5 arm64, E2 venv; changed test modules also under the CI lock: NumPy 2.4.6, SciPy 1.17.1, no torch)

Plugin-issue triage batch B (`plugin-triage/TRIAGE.md` items T01, T02, T03, T04, T07, T27, T29, T30, T35), on branch
`fix/triage-B` from `b45e4037` (release 0.22.0). Each item is a development or packaging checker that enforced less
than the rule it states, plus one doc number. No scientific number, verdict or method guidance changes; none of these
is a `sci-fix:`. Each item was re-verified on this tree before the fix (the new tests failed on it).

**What changed.**

- **T01** `tools/measure_entrypoints.py`, `tools/validate_skill_bundle.py`: a folded or literal block description
  (`description: >-`, `|`) or a plain value continued on indented lines was read as its first line only, so a
  2,000-character description measured 2 characters and passed the 1,024 limit. Both tools now use one helper,
  `skill_description()` in `measure_entrypoints.py`, which joins block and continued values with single spaces.
  Measures of the eight shipped skills are unchanged (all use quoted one-line descriptions).
- **T02** `tools/measure_entrypoints.py`: `lines` counted newline characters, so 501 lines without a final newline
  counted 500; it is now `len(text.splitlines())`.
- **T03** `tools/check_layering.py`: the import scan read only absolute static imports and skipped every `.py` under a
  `fixtures/` folder. Relative imports are now resolved against the file's package (a level that climbs above `core/`
  lands at the plugin root, so `from ..contracts import x` in `core/x.py` is `contracts.x`; inside the own skill,
  profile or adapter a relative import stays internal), constant-string `importlib.import_module(...)` and
  `__import__(...)` calls are read, and `fixtures/` outside `tests/` is scanned. No such import exists in the tree
  (latent).
- **T04** `tools/check_layering.py`: the steward check only tested that a core module had a key in `core/OWNERS.json`;
  the steward must now be a skill name (`contracts.skill_names.SKILLS`), so `''`, `'TBD'` or a missing field fails.
  All eight current stewards are skill names.
- **T07** `tools/check_ownership.py`: `claims()` required a non-letter right after the term, so `BDTs` in another
  skill's Owns line did not claim `BDT`; an `s` or `es` suffix is now allowed. The tree still passes (21 topics).
- **T27** `tools/check_packaging.py`: content rules ran only on files whose suffix was in `TEXT`. A file is now scanned
  when its suffix is in `TEXT` (fast path) or its first 8 KiB hold no NUL byte. On the tree this adds 119 files
  (92 `.keep`, 6 `.out`, 5 `.hh`, 2 `.def`, 1 `.patch`, `Snakefile`, `LICENSE`, `.gitignore`, 10 suffix-less batch
  shims); none raises a finding.
- **T29** `tools/check_packaging.py`: `batch_site_facts()` looked only at the top level and a direct `slurm`/`htcondor`
  block, with case-sensitive keys. It now walks the JSON recursively; an object with a slurm or htcondor backend or
  section opens a batch scope over everything below it; keys and the backend value compare case-insensitively. The
  documented `synthetic` prefix stays accepted.
- **T30** `tools/check_packaging.py`: the placeholder local-part exemption (`author@`, `user@`, ...) applied at any
  domain. An address is now exempt only at a reserved domain (RFC 2606 / RFC 6761: `example.com/.org/.net` and their
  subdomains, `*.example`, `*.invalid`, `*.test`, `*.localhost`) or as the commit trailer address. The tightened rule
  found one shipped address (a placeholder local part at the non-reserved domain `inst.edu`, in an `\emailAdd` example) in `skills/hep-authoring/references/latex-venue-setup.md`,
  now `author@example.org` (`docs/reference-inventory.json` regenerated, +3 bytes).
- **T35** `docs/profile-authoring.md` said the registry stays under 2 KiB; it now says at or under 3,072 bytes
  (`REGISTRY_BUDGET` in `contracts/registry.py`), matching the code and `docs/maintenance.md`.

**Per-test record.** Parent = `git archive b45e4037` with the new test files copied in; fix = `11031f81`. Every
evidence test fails on the parent and passes on the fix; the controls pass on both.

| Item | Test | Parent b45e4037 | Fix 11031f81 |
|---|---|---|---|
| T01 | `tests/tools/test_measure_entrypoints_budget.py::Budget::test_block_scalar_description_is_measured_in_full` (`>-`, `\|`, `>`, continued plain value; short folded control) | FAIL (4/4 subtests) | pass |
| T01 | `tests/tools/test_validate_skill_bundle.py::DescriptionLimitTests::test_folded_description_over_the_limit_is_a_problem` | FAIL | pass |
| T01 | `tests/tools/test_validate_skill_bundle.py::DescriptionLimitTests::test_short_folded_description_passes` (control) | pass | pass |
| T02 | `tests/tools/test_measure_entrypoints_budget.py::Budget::test_line_count_without_final_newline` | FAIL | pass |
| T03 | `tests/tools/test_check_layering.py::LayeringTests::test_core_relative_and_dynamic_imports_of_contracts` (relative, `import_module`, `__import__`, `fixtures/`, `from ... import contracts`) | FAIL (5/5 subtests) | pass |
| T03 | `tests/tools/test_check_layering.py::LayeringTests::test_skill_relative_import_of_another_skill` | FAIL | pass |
| T03 | `tests/tools/test_check_layering.py::LayeringTests::test_core_relative_imports_inside_core_are_clean` (control) | pass | pass |
| T04 | `tests/tools/test_check_layering.py::LayeringTests::test_empty_or_placeholder_steward` | FAIL | pass |
| T07 | `tests/tools/test_check_ownership.py::OwnershipCheckTests::test_plural_of_a_term_is_a_claim` | FAIL | pass |
| T27 | `tests/tools/test_check_packaging_rules.py::TextScanCoverageTests::test_every_text_file_is_scanned` (`.hh`, suffix-less shim, `.patch`, `Snakefile`, `.out`, `LICENSE`) | FAIL (6/6 subtests) | pass |
| T27 | `tests/tools/test_check_packaging_rules.py::TextScanCoverageTests::test_binary_files_are_not_scanned` (control) | pass | pass |
| T29 | `tests/tools/test_check_packaging_rules.py::BatchSiteFactTests::test_nested_and_mixed_case_site_keys_are_found` | FAIL (5/5 subtests) | pass |
| T29 | `tests/tools/test_check_packaging_rules.py::BatchSiteFactTests::test_placeholders_and_synthetic_values_pass` (control) | pass | pass |
| T30 | `tests/tools/test_check_packaging_rules.py::PlaceholderEmailTests::test_placeholder_local_part_at_a_real_domain_is_reported` | FAIL (3/3 subtests) | pass |
| T30 | `tests/tools/test_check_packaging_rules.py::PlaceholderEmailTests::test_reserved_domains_are_exempt` | FAIL (3/8 subtests: `.net`, `.invalid`, `.test` were not exempt) | pass |
| T35 | `tests/contracts/test_contracts.py::RegistryTests::test_registry_budget_in_the_docs_matches_the_code` | FAIL | pass |

Totals: 12 evidence tests fail on the parent (33 failing subtests and tests) and pass on the fix; 4 controls pass on
both. The changed test modules (108 tests: measure_entrypoints_budget, validate_skill_bundle, check_layering,
check_ownership, check_packaging_rules, check_packaging_size, contracts) pass in the E2 venv and in the CI-lock venv.
`ruff 0.16.10 check core contracts` and on the five changed tools: clean.

**Aggregate.** `python3 tools/run_all_checks.py --no-cli --jobs 6 --out <dir>` on `11031f81`: 25 pass, 0 fail, 2 skip (`claude-plugin-validate` and `codex-plugin-load`, by `--no-cli`); unittest 4,723 run, 4,591 pass, 0 failures, 0 errors, 132 skipped (395 modules); every registered profile suite passes; report `check-run-2026-10-21T221938Z.json`.

**Environment.** E2: macOS 26.5 (Darwin 25.5.0) arm64, Python 3.13.2 (`~/.venvs/hep-research-e2`); CI lock venv
(`~/.venvs/hep-research-ci`, Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, no torch) for the changed test modules.

## TRIAGE-C (2026-10-22, E2: macOS 26.5 arm64, Python 3.13.2; lint with the CI lock venv)

Plugin triage batch C (`~/Workspace/hep-research-tasks/plugin-triage/TRIAGE.md` items T09, T11, T12, T14, T15, T23,
T26, T36), branch `fix/triage-C` from `b45e4037` (0.22.0, contracts 3.3.0). Every item was reproduced on the parent
before the fix. No contracts major: artifact-validation gaps are new warning codes (T09 is an error, see below); no
schema field added and `CONTRACTS_VERSION` unchanged. Codes are not registered in a vocabulary file (no registry of
validator finding codes exists; `contracts/rules/registry.json` lists none of the measurement codes), so they are
defined in the code and its docstrings.

**What changed.**

| Item | Change | Level, code |
|---|---|---|
| T09 | `validate_directory` compares the suffix case-insensitively: `bad.JSON` is validated as an artifact (or is `not_artifact`) | error (existing codes). The docstring already stated every JSON file is validated; a valid artifact named `*.JSON` still passes; no shipped file has a non-lower-case `.json` suffix |
| T11 | `conditional_denominator` null, number, bool, or a placeholder token (`n/a`, `na`, `none`, `null`, `tbd`, `todo`, `-`, `--`, `?`, `...`) | warning `measurement.denominator_placeholder` (blank string stays error `measurement.denominator_blank`) |
| T12 | empty `backgrounds` with a placeholder `no_backgrounds_reason` | warning `measurement.no_backgrounds_reason_placeholder` |
| T14 | blinded mask with no non-blank region and no interval with a non-blank variable | warning `measurement.blinding_mask_empty` (absent/empty mask stays error `measurement.blinding_mask_missing`) |
| T15 | unknown, not retired, skill name under an extension `handoff` key, any artifact type; dropped where `ml.handoff_unknown` already reports it | warning `skill.unknown_handoff` (retired names stay error `skill.unknown_name`) |
| T36 | observable at level `unfolded` whose `phase_space.definition` names no other level term (core or profile, not `detector`) | warning `observable.unfolded_target_undeclared`; `Vocabulary.terms()` added |
| T23 | `validate_manifest` refuses chunks sharing a seed | `PartitionError("partition.duplicate_seed")` (a `ValueError`; `campaign.init` wraps it as `campaign.bad_manifest`) |
| T26 | `RevocationStatus.events` is a property calling `_require()`; field renamed `_events` | `RevocationUnverified` on a failed status |

**Regression tests, parent and fix.** Parent = `git archive b45e4037` with the new test modules copied in (adaptation
adds tests only, never the code under test). T15 uses the literal code string so the parent fails on the assertion.

| Item | Test | Parent b45e4037 | Fix |
|---|---|---|---|
| T09 | `tests.contracts.test_validate_directory.ValidateDirectory.test_upper_case_json_suffix_is_validated` | FAIL (1) | pass |
| T11 | `tests.contracts.test_measurement_contract.MeasurementRules.test_placeholder_denominator_warns` | FAIL (9 subtests) | pass |
| T12 | `tests.contracts.test_measurement_contract.MeasurementRules.test_placeholder_no_backgrounds_reason_warns` | FAIL (3) | pass |
| T14 | `tests.contracts.test_measurement_contract.MeasurementRules.test_blinding_mask_naming_nothing_warns` | FAIL (4) | pass |
| T15 | `tests.contracts.test_skill_names.ArtifactTests.test_unknown_extension_handoff_warns` | FAIL (1) | pass |
| T23 | `tests.core.test_partition_preflight.ManifestTests.test_duplicate_seeds_are_refused` | FAIL (1) | pass |
| T26 | `tests.contracts.test_revocation.ChainTests.test_failed_status_has_no_readable_events` | FAIL (6 subtests) | pass |
| T36 | `tests.contracts.test_levels_f14.UnfoldedTarget.test_unfolded_without_target_warns` | FAIL (3) | pass |
| T36 control | `...UnfoldedTarget.test_unfolded_with_a_named_target_passes`, `...test_other_levels_are_untouched` | pass (control) | pass |

Each item's test module also passes at its own commit (`git archive <commit>`).

**Nothing existing breaks.** All 360 artifacts in the tree (contracts fixtures valid/invalid/unresolved, examples,
skill assets, test data) validated on parent and fix with every profile's vocabulary: no change of `ok` or of the error
set; the only difference is one added warning (`observable.unfolded_target_undeclared`) on the invalid fixture
`dataset_simulated_unfolded.json`, whose expected error stays `dataset.simulated_level`.
`tools/run_all_checks.py --no-cli --jobs 6`: 25 pass, 0 fail, 2 skip (`--no-cli`); unittest 4717 run, 4585 pass,
0 failures, 0 errors, 132 skip; all profile suites pass. Lint (CI pins, `~/.venvs/hep-research-ci`): ruff 0.16.10
`check core contracts` all passed; mypy 2.4.0 no issues in 98 files.

**Environment.** E2 (`~/.venvs/hep-research-e2`, Python 3.13.2) for tests and the check suite; CI-lock venv for lint.

## ANISO-CL-RANGE (2026-10-22, Python 3.13.2 on macOS 26.5 arm64; E2 venv and the CI lock venv; branch `fix/aniso-cl-bdt-gate` from `b45e4037`)

Robust-fix S4, parent `b45e4037` (release 0.22.0). `skills/hep-measurement/scripts/anisotropy.py harmonic --cl 0.3`
(with or without `--exposure-map`) ended in a TypeError reported as `rejected` (`'>' not supported between instances
of 'NoneType' and 'float'`): below CL 0.5 the expected limit, the Neyman limit at the median isotropic amplitude, is
empty (even s = 0 is excluded there), and `amplitude_upper_limit` compared it with the observed limit. The same
TypeError hit CL 0.5 itself with an anisotropic map (n = 2000 and 500 with `1 + 0.9 cos(alpha - 30 deg)`, 24 bins),
where the expected limit is 0 analytically but the bisection found it empty by rounding; and the library function at
cl = 1.0 did not terminate (the bracket search doubles while P >= 0; the CLI already rejected 1.0).

The fix (maintainer's decision: an upper limit below CL 0.5 is not supported, the power constraint is undefined): the
CLI rejects `--cl` outside [0.5, 1) with that reason (status `rejected`, exit 2, as for other bad input);
`amplitude_upper_limit` raises ValueError with the same reason for cl outside [0.5, 1) (NaN included); an expected
limit found empty within rounding of cl = 1/2 is reported as its analytic value 0. `AnisotropicNull.neyman` and
`_neyman` are unchanged, so the CL 0.3 and 0.2 evidence of ANISO-WEIGHTED-COV, which calls the class directly, still
runs. The module docstring states the range; the reference `cosmic-ray-measurements.md` states no CL range and is
unchanged.

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/hep_measurement/test_anisotropy_cl_range.py::CliRange::test_cl_below_one_half_is_rejected_with_the_reason` | behavioral (status, exit 2, the stated range, no TypeError; CL 0.3 and 0.4999, Rice and anisotropic) | fail (assertion, 4 subtests): exit 2 but the error is the TypeError text | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_cl_range.py::CliRange::test_cl_one_half_with_an_anisotropic_map_gives_a_limit` | behavioral (CL 0.5: ok, expected limit 0, the limit is the Neyman limit) | fail (assertion, 2 subtests): exit 2, rejected with the TypeError | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_cl_range.py::LibraryRange::test_amplitude_upper_limit_raises_value_error_below_one_half` | behavioral (ValueError naming the range, Rice and anisotropic, with and without r_obs) | fail: 2 errors (TypeError, not ValueError, with r_obs), 2 failures (no exception without r_obs: the dict carries an empty expected limit) | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_cl_range.py::LibraryRange::test_amplitude_upper_limit_rejects_cl_outside_the_range` | behavioral (cl 1.0, NaN, 0.0 raise ValueError; 0.5 gives a limit) | fail: did not finish in 90 s (cl = 1.0 does not terminate) | pass | no | E2v (parent and fix), CIlock (fix) |

- Parent record: an adapted parent tree (`git archive b45e4037`) to which only the new test module was added; the
  code under test is the parent's, unchanged. Each test run alone (`python -m unittest MODULE.Class.method`, 90 s
  limit): 4 of 4 fail on the parent (E2v; the first three also in the CI lock venv), 4 of 4 pass on the fix (E2v and
  the CI lock).
- Results kept bit for bit: the full CLI JSON (stdout) and stderr of 45 runs, three synthetic event sets (3000, 2000
  and 500 events with declination and time columns), no map, a uniform 24-bin map and the non-uniform one, at CL 0.5,
  0.68, 0.9, 0.95 and 0.99, plus a default run, compared byte for byte before and after the fix: the 43 runs that
  succeeded on the parent are identical; the 2 that changed are the CL 0.5 runs with the non-uniform map that were
  rejected with the TypeError and now report the limit with expected limit 0.
- `tests/skills/hep_measurement/test_anisotropy.py` and `test_anisotropy_weighted_covariance.py` pass on the fix (24
  run, 3 slow-tier skips), unchanged.

## ANISO-WEIGHTED-COV (2026-10-22, Python 3.13.2 on macOS 26.5 arm64; E2 venv: NumPy 2.5.3, SciPy 1.18.1, SymPy 1.14.0; CI lock venv: NumPy 2.4.6, SciPy 1.17.1, SymPy 1.14.0)

Sci-fix S1, fix `3c10ac23`, parent `32450b32`. `skills/hep-measurement/scripts/anisotropy.py harmonic` with
`--exposure-map` took the null covariance of the weighted harmonic components `(a, b)` as `(2/N_eff) I`. A non-uniform
exposure makes their variances unequal and correlated: for `1 + 0.9 cos alpha`, `N Var(a) = (4/e^2)(1/sqrt(1-e^2) - 1)
= 6.39` and `N Var(b) = 2.79` against 4.59 for both from `N_eff`. The Rayleigh probability overstated the significance
of a dipole along the less exposed axis and the Neyman upper limit was too tight.

The fix (maintainer's design): `harmonic_covariance(edges, rel, n)` computes V from the binned map (closed-form
integrals per bin; exactly `(2/n) I` for a uniform map; a map with an empty bin is rejected); `first_harmonic` reports
`covariance_ab`, `chi2_ab` and `rayleigh_probability = exp(-chi^2 / 2)`, `sigma_per_component = sqrt(trace V / 2)`,
`n_effective` informational; `amplitude_upper_limit` keeps the Rice construction bit for bit when V is isotropic
(relative tolerance 1e-12) and otherwise uses `AnisotropicNull`: `P(r <= x | s, phi, V)` as a closed-form radial
integral (exponential and erf terms) and a periodic trapezoid in the polar angle (64 to 8192 points, set by the axis
ratio and s / sigma; a second-order Gaussian above 40 sigma), s excluded only if excluded at every phase of a 72-point
grid aligned with V's eigen-axes (19 distinct phases by the symmetries of the Gaussian), the expected limit at the
null median for V. Reference `cosmic-ray-measurements.md` (Harmonic analysis, script bullet) updated; the slow
coverage test joins the `slow-evidence` job (`--require numpy,scipy,sympy --no-skips`).

Evidence module `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py`, tolerances fixed before the
first run and stated in its docstring (binning bound 2.1e-5 for 3600 bins, so 1e-4 relative; dblquad at 1e-10 and the
exponentially convergent trapezoid, so 1e-8 for the CDF; the phase grid 2e-3; Monte Carlo 4 SE for variances, CL minus
3 binomial SE for coverage; fixed seeds). Oracles never import the module to compute an expected value.

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::Covariance::test_covariance_matches_the_sympy_delta_method` | symbolic (SymPy delta method, third-party) | fail (AttributeError): module 'anisotropy' has no attribute 'harmonic_covariance' | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::Covariance::test_toy_skies_have_the_reported_covariance` | invariant (Monte Carlo, 2000 toy skies) | fail (AttributeError): module 'anisotropy' has no attribute 'harmonic_covariance' | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::Covariance::test_uniform_map_reproduces_the_unweighted_outputs_bit_for_bit` | invariant (bit for bit) | fail (KeyError): 'covariance_ab' | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::Covariance::test_a_map_with_an_empty_bin_is_rejected` | behavioral | fail (AttributeError): module 'anisotropy' has no attribute 'harmonic_covariance' | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::Significance::test_rayleigh_probability_matches_scipy_chi2` | independent implementation (scipy mahalanobis, chi2.sf; V from SymPy) | fail (assertion): CLI p 1.74e-06 against scipy 7.47e-05 | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::Significance::test_negative_control_pre_fix_n_eff_fails_the_oracle` | negative control (emulated exp(-N_eff r^2 / 4)) | fail (assertion): the CLI value equals the pre-fix emulation (log ratio 1.8e-15) | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::Significance::test_limit_meets_the_neyman_condition_by_scipy` | independent implementation (scipy dblquad over the 72-phase grid, minimize_scalar, brentq) | fail (assertion): max scipy CDF at the CLI limit 0.0885, not 0.05 | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::Significance::test_negative_control_pre_fix_rice_limit_fails_the_neyman_condition` | negative control (emulated Rice limit with 2/N_eff, scipy ncx2) | fail (assertion): CLI limit 0.10012 is the pre-fix limit, not above 1.01 x 0.10012 | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::LimitConstruction::test_cdf_matches_scipy` | independent implementation (scipy multivariate_normal + dblquad; ncx2) | fail (AttributeError): module 'anisotropy' has no attribute 'AnisotropicNull' | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::LimitConstruction::test_limit_takes_the_largest_cdf_over_the_phase_grid` | independent implementation (scipy dblquad over the 72-phase grid, CL 0.3 and 0.2) | fail (AttributeError): module 'anisotropy' has no attribute 'AnisotropicNull' | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::LimitConstruction::test_acceptance_region_covers_at_four_phases` | invariant (coverage, 1500 Gaussian toys per phase) + negative control | fail (AttributeError): module 'anisotropy' has no attribute 'AnisotropicNull' | pass | no | E2v, CIlock |
| `tests/skills/hep_measurement/test_anisotropy_weighted_covariance.py::LimitConstruction::test_upper_limit_covers_with_a_modulated_exposure` | invariant (coverage, 400 event-level toys per phase; slow tier) | fail (AttributeError): module 'anisotropy' has no attribute 'harmonic_covariance' | pass | no (HEP_SLOW_TESTS=1) | E2v, CIlock |

- Parent record: an adapted parent tree (`git archive 32450b32`) to which only the new test module was added; the
  code under test is the parent's, unchanged. 12 of 12 tests fail on the parent: 4 by assertion on the released CLI
  numbers (`test_rayleigh_probability_matches_scipy_chi2`, `test_limit_meets_the_neyman_condition_by_scipy` and the
  two negative controls, whose module check fails because the CLI still reports the pre-fix value), 8 because the
  function, class or output key they test is new in the fix. `tests/skills/hep_measurement/test_anisotropy.py`: 12
  tests pass on both (not discriminating).
- Mutants (D3), each run against the fast evidence tests on the fix with one change: M01 revert to the parent script
  (11 tests fail), M02 `cos^2 * rho` for `cos^2 / rho` (4), M03 covariance off-diagonal dropped (3), M04 covariance
  replaced by its isotropic mean, the N_eff idea (6), M05 chi^2 without the covariance term (1), M06 `exp(-chi^2 / 4)`
  (1), M07 radial integral without the erf term (5), M08 phase grid reduced to the major axis (1), M09 to the minor axis
  (4), M10 phase not rotated into the eigenframe (1), M11 CLI keeps the Rice limit with N_eff (2), M12 null median at
  the 45 % point (1), M13 every covariance treated as isotropic (5), M14 trapezoid with 4 points (3), M15 phase step
  45 deg (1), M16 uniform-map shortcut removed (1): 16 of 16 killed. M08 survived a first version of the module (at
  CL >= 1/2 the deciding phase was always the major axis); `test_limit_takes_the_largest_cdf_over_the_phase_grid`
  (CL 0.3 and 0.2) was added to kill it, with its tolerance set before its first run.
- Numbers (fix, E2v): SymPy `N V` for the axis at 30 deg `[[5.48961, 1.56109], [1.56109, 3.68702]]`, the 3600-bin map
  within 1.6e-6 relative. Significance case (20000 events, amplitude 0.06 along the exposure axis): scipy
  `p = 7.4718e-05` (chi^2 19.004), CLI 7.4717e-05, pre-fix 1.74e-06. Neyman limit at CL 0.95: 0.10540 (pre-fix
  0.10012, where the scipy CDF along the exposure axis is 0.0885); scipy maximum over the grid at the new limit
  0.05000007. Fast coverage (CL 0.95, floor 0.9331, 1500 toys, s = 5 sigma): 0.9493, 0.9793, 0.9947, 0.9760 at
  30, 75, 120, 165 deg; pre-fix emulation 0.9160 at 30 deg. Slow coverage (CL 0.95, floor 0.9173, 400 event-level
  toys, n = 2000, s = 0.15, 24-bin map, phases 0, 45, 90, 135 deg): passes.
- Unchanged outputs: the parent and fix CLIs give identical numbers (every key of the parent output, compared exactly)
  without a map, with a uniform 24-bin map, and with event times (solar, sidereal, anti-sidereal; exit 1 kept), on
  five input sets; the fix only adds `covariance_ab` and `covariance_source`.
- Runtime (fix, E2v): a CLI run with 20000 events and a 3600-bin map takes 0.13-0.17 s; `amplitude_upper_limit` with
  an anisotropic V takes 0.01-0.37 s over axis ratios 2.3 to 22 and r_obs up to 100 sigma.
- Gates: `tools/run_required_backends.py --require numpy,scipy,sympy --no-skips` with `HEP_SLOW_TESTS=1` on the new
  module and `test_anisotropy.py` in the CI lock venv: 24 run, 0 failures, 0 skips. `tools/run_all_checks.py --no-cli
  --jobs 6` (E2v): unittest 4522 run, 0 failures, 0 errors, 130 skipped; profile suites, static checks and the
  AMS-optional check pass.
- Known limitations: the covariance is leading order in 1/N and only as good as the exposure model; the grid of 72
  phases is the documented construction (a continuous maximum may exceed it by up to 2e-3 in the CDF); above
  40 sigma the CDF is a second-order Gaussian (up to 6e-4 from the trapezoid at 40 sigma). Pre-existing, not changed:
  `--cl` below 1/2 is rejected with a TypeError message because the expected limit is empty (also on the parent).

## REVIEW-CODE-WARN (2026-10-22; branch `fix/review-code-warnings` from `32450b32`)

Three code-and-guidance gaps that REVIEW-REFS found but did not fix ("Found, not fixed here"). Severity S3 (warnings
and guidance only); ledger `documentation_fixes` REVIEW-CODE-WARN-TAIL, -MANIFEST, -NEGW. No computed number, verdict,
exit code or policy name changes; the only output change is added warning text (and a new `warnings` key in the
`train_bdt.py` stdout result and in the `inference.py --external-scores` refusal).

- **`tail_extrapolation.py`, one-model envelope** (commit `2b221f92`). With exactly one model passing validation the
  envelope is `low = high` (and `gaussian_sigma = 0` under a prescription) by construction; a warning now names the
  model and says this is not a measured model uncertainty and the model uncertainty was not assessed.
  `inference-recipes.md` step 3, which said the tool gives no warning, updated.
- **`assets/inference.py --external-scores`, scored ids missing from the split manifest** (commit `cdb31f9e`). Still
  not refused (real data or other samples are legitimately outside the manifest). The warning (formerly "their
  train/test role is unknown") now says N scored events are not in the split manifest, so the check cannot exclude
  that the model was trained on them, and that the manifest is incomplete if they are simulated events from the
  training sample; the refusal for scored training ids carries it too. `leakage_check` docstring, module docstring
  and `multivariate-analysis-bdt-nn.md` ("Scores from another tool") updated.
- **Negative weights, `drop`** (commit `33bd6464`). Maintainer decision 2026-10-22: `ml-analysis-weights.md` option 4
  overstated. Dropping from training only makes the classifier learn the positive-weight density instead of the
  signed one, option 3's kind of distortion (|w| learns positive plus negative); acceptable only with the effect
  shown against option 1 or 2; never for evaluation (biases yields, efficiencies, working points).
  `multivariate-analysis-bdt-nn.md` matches. `train_bdt.py` warns under `drop` and `abs-train-signed-eval` when
  negative weights are present (it already evaluated with signed weights; `train_ok` and the evaluation block
  checked). A stale comment in `test_training_pipeline.py` (train_classifier.py's removed `dropped` option) updated.

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/hep_statistics/test_tail_extrapolation.py::Basics::test_one_usable_model_warns_that_the_envelope_has_zero_width` | behavioral (C1), negative control: two passing models, no warning | fail (3 subtests: no warning) | pass | no (NumPy, SciPy) | E2, CI venv |
| `tests/skills/hep_ml/test_train_bdt_extensions.py::ExternalScores::test_scored_ids_outside_the_manifest_are_reported_not_refused` | behavioral (C1), negative control: all ids in the manifest, no warning | fail (old warning text) | pass | no (NumPy only) | E2, CI venv |
| `tests/skills/hep_ml/test_train_bdt.py::Contract::test_negative_weight_warning_names_the_distorted_density` | behavioral (C1) | error (3 subtests: no `negative_weight_warning`) | pass | no (no backend needed) | E2, CI venv |
| `tests/skills/hep_ml/test_train_bdt.py::XgboostBackend::test_drop_and_abs_warn_that_the_training_density_is_distorted` | behavioral (C1), negative control: no negative weights, no warning | error (4 subtests: no `warnings` key) | pass | yes in E2 and in CI (no xgboost); ran in the CI venv | CI venv |
| `tests/skills/hep_ml/test_train_bdt.py::SklearnBackend::test_drop_and_abs_warn_that_the_training_density_is_distorted` | as above | error (4 subtests) | pass | yes in E2 and in CI (no scikit-learn); ran in the CI venv | CI venv |

Parent records: the `32450b32` tree (`git archive`) with the three fix-commit test files copied in, nothing else
changed. No required CI gate installs xgboost or scikit-learn (`bdt` extra; not in `requirements-ci.lock`,
`tools/run_required_backends.py` or an `optional-python` matrix entry), so the two backend tests are unverified in CI;
the backend-free Contract test covers the warning text there.

Environment: macOS 26.5 arm64. E2 `~/.venvs/hep-research-e2`: Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1, no xgboost or
scikit-learn. CI venv `~/.venvs/hep-research-ci`: Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1, xgboost 3.4.1,
scikit-learn 1.9.1.

| Check | Result |
|---|---|
| `tools/reference_inventory.py --check` | pass (218 references) |
| touched modules (tail_extrapolation, train_bdt, train_bdt_extensions, write_ml_artifact) | E2: 56 run, OK, 25 skipped; CI venv: 56 run, OK, 1 skipped |
| `run_all_checks.py --no-cli --jobs 6`, E2, at `33bd6464` | 25 pass, 0 fail, 2 skipped (CLI host checks); 4515 tests in 383 modules, 4384 pass, 0 failures, 131 skipped; profile tests all pass |

## TH13-SOURCES (2026-10-23; branch `fix/th13-source-verification` from main `1c82b194`)

The Th13 pages (`cosmic-ray-phenomenology.md`, `solar-modulation-models.md`, `cosmic-ray-new-physics.md`) had been
written from a summarizing fetch (2026-10-20), which hep-citations counts as a search snippet. Every cited source was
re-read in full text on 2026-10-23: 49 arXiv PDFs at the versions cited (export.arxiv.org, generic User-Agent), the
PoS(ICRC2025)234 PDF, the WDC Kp/Ap format description and the Caltech ACE Bartels table; Usoskin et al. 2005 (JGR,
paywalled) was not opened. Five independent read-only agents checked every attribution, locator, number and paper
characterization against the texts (about 165 statements); each correction below was rechecked against its quoted
passage before the edit. Severity S3 (guidance), ledger `documentation_fixes` TH13-SOURCES.

| Page | Statements | Corrected |
|---|---|---|
| phenomenology, propagation codes | 25 | GALPROP 90 equations are the framework up to v56, v57 adds data (Porter et al. 2022, Sec. 2, abstract); w taken as 1, only V_A^2/w enters (SM98 Sec. 2); DRAGON2 D_pp prefactor and beta^eta form found (App. C.9 Eq. C.27, App. C.8 Eq. C.23), removed from the "not verified" list; SM98 locator Sec. 3.2 |
| phenomenology, cross sections | 53 | opt12 has null Fe to Li and undershoots Fe to Be, B (Maurin et al. 2022, Sec. 3.2.2, Table 1); opt12 is Korsmeier and Cuoco's default, not GALPROP's; the 3% is the Si-to-Fe progenitor change; "can reach" 20-50%; Evoli et al. 2019 claim is in Sec. V (the abstract reads the other way); Korsmeier and Cuoco A for Li, Be, B profiled, not flat priors; source-term uncertainty "up to" +-20%; Orusa et al. cross section is p + p to e+-, AAfrag 2021 version |
| phenomenology, fits and metadata | 5 + 49 rows | Cuoco et al. 2019 significance without vs with correlations; first authors M.-J. Zhao, Y.-C. Ding; S. Della Torre (not Boschini) first author of arXiv:1612.08445; D'Angelo, Oliva, Masi order |
| solar modulation | 29 | Gieseler et al.: phi depends on LIS, energy range and magnetic epoch (not cycle phase); Tomassetti et al.: the +-0.8-month systematic is inside the +-1.2 and the fit is in Sec. 3; the LIS-dependence claim now rests on Usoskin et al. 2017 Sec. 6.3 (the unopened 2005 paper's "factor 2" and "linear conversion" dropped); Bartels epoch and 2426 = 2011-05-15 confirmed (270 Caltech rows, 0 mismatches) |
| new physics | 32 | L scaling in Calore et al. Sec. 4; BIG to QUAINT shift (Sec. 5.1) vs shape (Sec. 5.2); Cuoco et al. 2017 Delta chi^2 = 25 without systematics; Cuoco et al. 2019: fell to 3 sigma with updated cross sections, correlations matter more; Di Mauro et al. 2016 "comparable or stronger"; Hooper et al. 2009 "could plausibly"; Profumo et al. 2018 radially dependent diffusion (not two-zone); Manconi et al. 1 sigma band of simulated populations |

Journal references: the five not printed in the PDFs or found in citing papers (Evoli et al. 2020, Maurin et al.
2022, Orusa et al. 2022, Tomassetti et al. 2017, Ding et al. 2021) were then confirmed at three primary records (arXiv
journal-ref/DOI, INSPIRE-HEP publication info, Crossref), and all 16 DOIs on the list resolve at Crossref to the cited
paper (first author and title); Maurin et al. (A&A 668, A7) and Ding et al. (JCAP 09 (2021) 005) gained their volume
and article. Not changed: the instrument name
in one collaboration title stays replaced (layering rule). The source texts stay outside the repository.
A separate read-only agent then checked the whole diff against the source texts: one overstatement (the Usoskin et
al. 2017 series comparison: three causes, not the LIS alone), one locator (Delta chi^2 = 25 is in the letter's main
text) and five precision points (DRAGON2's Alfvenic option, 15-21 times, list locators, versions, "slightly") were
fixed before the commit.
Follow-ups the same day: the HAWC D100 = (4.5 +- 1.2) x 10^27 cm^2/s (arXiv:1711.06223, Table 1 and text, joint fit);
the Wilcox L and R model assumptions from http://wso.stanford.edu/Tilts.html (page updated 2025-10-23); the antiproton
source-term search rerun at INSPIRE-HEP (title queries, date after 2025-06) and the arXiv API (abstract query, newest
first): nothing peer-reviewed after the cited work (a p-He measurement conference paper, 2025, is data, not a source
determination); AAfrag 2021 = Koldobskiy et al., arXiv:2110.00496v2 (PRD 104 (2021) 123027, INSPIRE); Genolini et al.
2018 Sec. II.B ties opt12/opt22 to WKS93/TS98 where Maurin et al. 2022 Sec. 2.3 names WNEW 1998/YIELDX 2000; Maurin
et al. 2022's reference list labels the Weinrich 2020 papers the other way round. Last two items: Usoskin et al.
2005 read from the authors' institutional copy (https://cosmicrays.oulu.fi/phi/2005JA011250.pdf; App. A: LIS models
differ by a factor of 2 at low energy, Fig. A1; linear phi conversions "only an approximation", Eq. A4), and its claim
restored with those locators; the Planck 2018 limit read in arXiv:1807.06209v4 (Sect. 7.9: p_ann < 3.2e-28 cm^3 s^-1
GeV^-1, 95%, TT,TE,EE+lowE+lensing+BAO, Eq. 89c; Fig. 46) and cited. No listed source remains unread.

## REVIEW-REFS-4 (2026-10-22; branch `fix/review-refs-4` from main `c2fc9f5c`)

Five references were the documents of review batch 1 (`--models sonnet,haiku --lens-model design=sonnet
--filter-model opus`), run with a prospective expert-slot test (`--own-config --expert-model opus`, a separate review
of the same text) and an out-of-driver Sonnet filter on the same pooled findings; all outside the repository. A blind
Opus adjudicator per document judged the pooled findings of both arms: 41 issues upheld (4 substantive), none named
that no finding raised. Scores: lens slots 79 findings, precision 0.65; kept by the Opus filter 42, precision 0.92 (2
issues lost, minor and trivial); kept by the Sonnet filter 53, precision 0.69; expert slot 9 findings, 9 upheld, 4
substantive, 3 of them raised by no lens slot, at about 10% of the lens slots' tokens. The receipt check rejected 2 of 5
Opus filter attempts with `read_outside_packet` (recursive greps over the mechanism files; one read the installed copy
of the page); both retries were accepted. The 16 findings of the earlier retrospective expert-slot test were rechecked
against the current text of ten references: 13 fixed here, 3 already fixed. Each change was rechecked against its source
before the edit; for a partly correct finding only the upheld part changed. Severity S3, ledger `documentation_fixes`
REVIEW-REFS-4.

| Reference | Issues | Main changes | Sources (locators) |
|---|---|---|---|
| hep-detector `performance-metrics-and-residual-diagnostics.md` | 8 | biased residual positively correlated (C = V_pred, substantive); its covariance singular, fit chi^2 with V_meas and n - n_par; unbiased residual: the exclusive prediction is uncorrelated; pull width 1 needs the right covariance, not Gaussian errors; purity with correct identity; acceptance vs geometric factor; calorimeter residual coverage; escaped table pipes | least-squares algebra (straight-line toy, expert record); `skills/hep-detector/references/*` technology files |
| hep-detector `geant4-study-protocol.md` | 8 | QGSP_BIC/FTFP_BERT coincide for pions below 12 GeV and nucleons 1.5-12 GeV (substantive); the convergence gate uses the finest supplied runs and the scope check ignores the observable and an omitted thickness (substantive); output hashes checked for presence only; _HPT/_AllHP and Shielding lists use ParticleHP; t_max correlation conservative only for rho >= 0; scan step limit; vacuous Done-when | `check_geant4_study.py` HADRONIC table (75-80), `convergence()`, `scope_within()`; `contracts/validate.py _scope_inside`; `contracts/dependencies.py`; `geant4-physics-rules.json`; `adapters/geant4/assets/geant4_run.py` 457, 469; Var(t) cross term |
| hep-detector `response-and-forward-folding.md` | 7 | era mixing exact only when every era-varying factor is in R_t or w_tj; A*eps*T or stacking for selected-normalized eras (substantive); "pass" allows unresolved findings; `--strict`; `periods` vs the `mixing` record; species "outside" wording; test citation; S1/S6 labels | `mix_period_responses.py`, `species_response.py`, `contracts/validate.py`, `response_adapter.py` runs on a fixture copy; 2x2 counterexample (expert record) |
| hep-detector `core-detector-equations.md` | 10 | track-fit chi^2 uses the measurement covariance (substantive); Bethe range 0.1 < beta*gamma < 1000 and units; exact TOF difference, 1/p^2 asymptotic; delta omitted by `pid_separation_power.py` only; labels used; purity renamed; E1 wording; "single home" narrowed | PDG RPP 2024 chapter 34 (text after eq. 34.5); `geant4_benchmarks.py` 143-159; `pid_separation_power.py` 244-248; TOF recomputation |
| hep-statistics `astroparticle-statistics.md` | 8 | one-sided p-values (two-sided 1.33e-2); mixture needs the spectral index fixed too (Davies); Braun et al. used a flux-model background; alpha = t_on/t_off; RA scrambling needs uniform RA acceptance; sqrt(2) sentence; RooFit pointer; internal reference removed | `li_ma_significance.py` run; arXiv:0801.1604 Eq. 6 |
| ten references (retrospective expert findings) | 13 | `nuisance-modeling.md` code1/code4 difference; `time-series-inference.md` charge-sign comparison and harmonic trials; `front-end-electronics-and-signal-processing.md` unipolar anode signals, induced-charge sign; `calibration-and-alignment.md` most probable value vs angle, electron-only E/p symmetry; `triggers-luminosity-pileup.md` tag-and-probe shapes, reweighting check; `statistical-inference-for-physics.md` Bayesian vs profile intervals; `analysis-design.md` Z_A for discovery, non-nested trigger bootstrap | pyhf code1/code4 run; PDG RPP 2024 eq. 34.12; Z_A computation; trigger-efficiency algebra |

Also: the G4R-BIC-RANGE and G4R-HP-NEUTRON `concern` strings in `geant4-physics-rules.json` (text only), the
reference inventory, and the hep-authoring `independent-review.md` recommendation of `--expert-model` (with the strongest
model, alongside the lens slots and `--filter-model`) and of an Opus over a Sonnet filter.

Code follow-ups (not changed here): `convergence()` should use the declared values and require a run for each;
`scope_within()` and `_scope_inside()` should compare the observable and an omitted thickness; `dependencies.py`
should compare output hashes with the files; an unresolved `mc_stat` on an unfolding response could fail the gate;
`mix_period_responses.py` could warn on acceptance x time weights for selected-normalized eras.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 venv | 25 pass, 0 fail, 2 skipped (CLI host checks) |
| `run_all_checks.py --no-cli --jobs 6`, CI lock venv | 25 pass, 0 fail, 2 skipped (CLI host checks) |
| `unittest discover -s tests/skills`, E2 | 2297 tests, OK (74 skipped) |

## REVIEW-REFS-3 (2026-10-22; branch `fix/live-reference-issues` from main `a53af7e0`)

Five 0.23.0 references were the documents of the first live review with the new options (`--lens-model design=sonnet
--filter-model opus`; outside the repository). A blind Opus adjudicator per document upheld 40 issues from the
findings (none substantive) and named 2 more that no reviewer raised (one substantive). Each was rechecked against its
source before the edit; for a partly correct finding only the upheld part changed. Severity S3, ledger
`documentation_fixes` REVIEW-REFS-3. Sources opened 2026-10-22.

| Reference | Issues | Main changes | Sources (locators) |
|---|---|---|---|
| hep-detector `space-based-direct-detection.md` | 17 | Garwood level labelled 68.27%; T = 4.641 GeV is the bin-centre value; the cutoff deliverable and the worked example use the backtraced maximum over the cone (east-horizontal 5.99 GV vs vertical 4.54 GV); the Stormer formula is directional; a pure dipole has a penumbra; negative-particle sign; cutoff by charge sign; positron fraction rises from about 10 GeV; profile claims for the fraction and antiprotons; spectrometer items in the response checklist; scope, typo, links and read dates | `cosmic_ray_flux.py` run (level 0.6827); Stormer recomputation; Nolty, arXiv:hep-ex/0201015 Stormer section; AMS-02 evidence index C04, C06, C96, C110, C113; hep-theory `cosmic-ray-propagation.md`; SILSO pages (web.archive.org copies) |
| hep-detector `calibration-and-alignment.md` | 7 + 1 | measured-value notation `x_m` in the inverse-offset row (raised by the adjudicator; sign unchanged); 0.3 is a tool warning, not a bound; PDG cited for the most probable value only; muon scale anchors as the paper states them (no Upsilon); weak-mode constraints may enter the alignment fit; "must" for per-period stability; LED/laser monitoring; "300%" not equated with a factor of 3 | `propagate_scale_distortion.py` (`WARN_QXD`, edge mapping); PDG RPP 2024 sects. 34.2.3, 34.2.9; arXiv:1206.4071 sect. 6; arXiv:1403.2286 sect. 4.4; arXiv:2603.25085 abstract |
| hep-detector `triggers-luminosity-pileup.md` | 8 | Lendermann locators and the exclusion/inclusion weights; ATLAS 8 TeV sections 4-7 and the 13 TeV correlation section; tag-and-probe weight support; pileup script guards; prescales divide the live-time sum; `n1 n2` in the visible cross section; luminosity uncertainty about 1-2%; page title | arXiv:0901.4118 sects. 3-4 eqs. 3-13; arXiv:1608.03953 sects. 4.1, 7.3; arXiv:2212.09379 sect. 8.1; arXiv:2104.01927; `tag_and_probe_efficiency.py`, `pileup_reweight.py` |
| hep-statistics `statistical-inference-for-physics.md` | 2 + 1 | ignoring a positive correlation understates a sum but overstates a difference, ratio or shape (substantive, raised by the adjudicator); CLs is a modified exclusion criterion; citation style | Var(a +- b) = Var(a) + Var(b) +- 2 Cov(a, b); `inference-recipes.md`, `scientific-style.md` |
| hep-measurement `analysis-design.md` | 6 | only the boundary era check runs with one era; `batch_campaign.py` path; `residual.py` is advisory and partial; Z_A applies when s/b is not small; k-fold pointer to hep-ml; look-elsewhere script pointer | `review_measurement_spec.py` (two-era gate); `adapters/batch-schedulers/batch_campaign.py`; `core/blinding/residual.py` docstring; arXiv:1007.1727 sect. 5.1; `ml-analysis.md` "Splits and leakage"; `inference-recipes.md`, `core-stats-commands.md` |

Also: the `geomagnetic_cutoff.py` docstring penumbra wording (no behaviour change), and the hep-authoring
`independent-review.md` recommendation of `--filter-model` with the live-run numbers (precision 0.59 to 0.84, 39 of 40
real issues kept, about 10% of the review's tokens) and the design-lens result (5 of 5 accepted at the first attempt).

## REVIEW-REFS-2 (2026-10-22; branch `fix/tune-reference-issues` from main `5350266b`)

Five 0.22.0 references were the documents of the review tuning run (8-slot reviews of PR #194's mechanism, outside the
repository). A blind Opus adjudicator per document upheld 25 issues from the findings (3 substantive) and named 2 more
that no accepted finding raised. Each was rechecked against its source before the edit; for a partly correct finding
only the upheld part changed. Severity S3 (guidance), ledger `documentation_fixes` REVIEW-REFS-2. Sources opened
2026-10-22.

| Reference | Issues | Main changes | Sources (locators) |
|---|---|---|---|
| hep-measurement `correction-chain.md` | 5 + 1 | chained factors multiply to the total with no independence; bias only from factors measured on another population (substantive); the acceptance already holds the simulated selection, so eps holds only what it does not (raised by the adjudicator); validator scope for a bare `efficiency`; Garwood/Kish interval with a target spectrum; covariance scales with products of the factors; feed-down `N_heavy` and scope defined | chain rule against the page's chained definition; `contracts/validate.py` (bare-efficiency rule); `scripts/acceptance_from_generation.py` docstring and weighted branch; `scripts/spectrum_transform.py` (`J C J^T`) |
| hep-detector `front-end-electronics-and-signal-processing.md` | 4 | fake hits use `nu`, not `nu_0` (substantive, about 2.7e5 at 5 sigma); AC-coupling recovery on the coupling constant (also in Pileup); dark-count sigma `sqrt(20)`; timing link wording | the page's own Rice-rate bullet; numerical check of CR-RC plus CR coupling; `timing-detectors.md` sections |
| hep-statistics `time-series-inference.md` | 5 + 1 | `periodicity_scan.py` exists, with its null's limits (substantive); a model-built covariance is not equivalent to a normalization nuisance (raised by the adjudicator); `--allow-plugin`; EXPERIMENTAL label; Horne-Baliunas white-noise scope; a pre-specified period | `scripts/periodicity_scan.py` docstring, `_null`, `_surrogate`, `scan`; `core/stats/covariance_fit.py` header (Peelle bias data -0.043, model -0.039, nuisance -0.002) and flag; `global_significance.py` header; Horne and Baliunas 1986 abstract |
| hep-detector `particle-identification.md` | 6 | TOF ceilings are the "single" convention (quadrature 0.9-1.3 and 1.6-2.3 GeV/c); TR onsets 140 and 940 GeV/c at gamma 1e3; RICH threshold cancellation exact for photon statistics, not for chromatic and few-photon terms; velocity-based scope (also in the intro); cross-reference direction; deliverable intervals | `pid_separation_power.py --mode tof` runs (both conventions); PDG RPP 2024 sec. 34.7.3 and 35.5 eqs. 35.11-35.12 |
| hep-statistics `nuisance-modeling.md` | 5 | Combine impacts `--robustFit 1 --doFits`; pull denominator is the pre-fit uncertainty; `autoMCStats` doc link; diagnostics test scope; discrete-profiling penalty is the paper's choice, not "the usual" | Combine docs part3/nonstandard and part2/bin-wise-stats; arXiv:1408.6865 sec. 4.3 p. 18; `tests/adapters/test_pyhf_nuisance_diagnostics.py` |

Found, not fixed here: `contracts/validate.py` does not flag a bare `efficiency` next to `<ns>:efficiency` (the page
now says so); `periodicity_scan.py` does not refit its red-noise null per surrogate and calls the result conservative.

## REVIEW-REFS (2026-10-22; branch `fix/reference-review-issues` from main `c4f7954b`)

Five 0.21.0 references were the documents of the independent-review evaluation (a matched self-check against the
8-slot review of PR #194, outside the repository). A blind Opus adjudicator per document judged every finding of both
arms; 45 distinct issues had at least one finding judged correct or partly correct (2 substantive, the rest minor or
trivial). Each was rechecked against its source before the edit, and for a partly correct finding only the upheld
part was changed. Severity S3 (guidance), ledger `documentation_fixes` REVIEW-REFS. Sources were opened on 2026-10-22.

| Reference | Issues | Main changes | Sources (locators) |
|---|---|---|---|
| hep-measurement `cosmic-ray-measurements.md` | 7 | the `2/N` variance and `sqrt(pi/N)` bias of the first harmonic hold for uniform exposure; with weights `N_eff` is an approximation (substantive); upper-limit trigger fixed before unblinding; the script computes the Neyman limit, hep-statistics owns the choice; coverage test scope (one slow test, uniform exposure); stale "analysis guide" link labels; X_max width measures the lnA variance only after the shower-fluctuation term | numerical integration and toys (N Var(a) = 6.39 against 4.59 with `N_eff`, e = 0.9; marked Inferred); `scripts/anisotropy.py` `first_harmonic`, `_neyman`; `tests/skills/hep_measurement/test_anisotropy.py::test_upper_limit_covers`; Kampert and Unger, arXiv:1201.0018 Sec. 2.1, Eqs. 13-14 |
| hep-theory `cosmic-ray-propagation.md` | 6 | cross sections carried as a normalization nuisance or as model alternatives with an envelope; DRAGON2 agreement marked post-hoc (C2 still fails); the first 32-34% B/C excess was mostly the helium target (1.143) and the unit (about 1.19); intro points to the optional DRAGON2 adapter; Moderski write gamma^2, the page and script use the exact gamma^2 - 1; antiproton source term also checked against a published table | `docs/capability-matrix.md` (tabulated-grid, adapter and pp rows); VALIDATION CR-PROPAGATION-DRAGON2 and -UNITS rows; `tests/adapters/test_cr_propagation.py` Diagnostics; Moderski et al., arXiv:astro-ph/0504388v1 Eqs. 1 and 7; `scripts/lepton_energy_losses.py` |
| hep-statistics `inference-recipes.md` | 12 | Baker-Cousins gives the ML estimates (not "unbiased"); Gross-Vitells bound holds at every `c`; Cowan et al. eq. 98 (not 97) for `s/sqrt(b)`; Z_Bi over-covers at very low counts; reference and Jeffreys priors are reparametrization-invariant (not dependent); `cls-limit --sigma-b` (hybrid) and `profile-cls` are not interchangeable; a one-model envelope has zero spread by construction; demo-sampler MCSE 0.059 (rerun, seed 11); `counting_reference.py` path; pyhf pointer; the coverage example is labelled as an outside study; "below" to "above" | Baker and Cousins, NIM 221 (1984) 437, abstract; Gross and Vitells, arXiv:1005.1891 p. 1, Eqs. 1 and 3; Cowan et al., arXiv:1007.1727 Eqs. 97-98 (and a numerical check of the `sigma_b` limit); Cousins, Linnemann and Tucker, physics/0702156 abstract and Sec. 6; Demortier, Jain and Prosper, arXiv:1002.1111 Sec. II p. 6; `core/stats/poisson_diagnostics.py`, `core/stats/likelihood_limits.py`, `scripts/tail_extrapolation.py`, `scripts/bayes_diagnostics.py demo-sampler` output |
| hep-ml `multivariate-analysis-bdt-nn.md` | 11 | flattening or oversampling inside a class is a documented training-only choice, as the weights reference allows (substantive); hyperparameter selection averages the validation objective over all folds, so test-fold events inform it; the analysis metric (Asimov) before AUC; `drop` biases training; the `inference.py` leakage check only refuses training-part scores; Huber lies between mean and median; Cheong et al. cited by section, the mean-and-variance head marked unverified; regression closure on a different truth spectrum; cap changes within-class weights; leakage symptoms; statistics link to `ml-assisted-inference.md` | `ml-analysis-weights.md` ("Class balancing and the prior", "Negative weights"); `scripts/train_bdt.py` selection code; `assets/inference.py` `leakage_check`; Cheong et al., arXiv:1910.03773v3 Secs. 3, 3.1, 3.2, 3.5 |
| hep-detector `signal-formation-and-readout.md` | 9 | the shell term scales as `z^2` (Barkas `z^3`, Bloch `z^4`); Bethe limits: `beta gamma ~ 0.1` uncorrected, `beta ~ 0.05` corrected, muons radiative above `beta gamma ~ 1000` (about 100 GeV/c); fluctuation regimes by Vavilov `kappa`, very thick absorbers never Gaussian; Highland accuracy as PDG states it (no 11%); Pólya 0.31 ± 0.02 located; calibration pointers; "most equations" state their validity | PDG RPP 2025 Sec. 34 (Eqs. 34.5, 34.8, 34.16; Sec. 34.2.9 pp. 11-14); Zerguerras et al., arXiv:0901.2882 abstract and Eq. 2; NEWS-G arXiv:1902.08960 Eq. 1; `core-detector-equations.md` E4 |

Two docstrings with the same claims were corrected (no behavior change): `train_bdt.py` (hyperparameter selection
across folds) and `lepton_energy_losses.py` (Moderski's gamma^2). `tools/reference_inventory.py` regenerated.

Found here and fixed in the same branch (ANISO-WEIGHTED-COV and REVIEW-CODE-WARN above):

- `anisotropy.py` uses the Rayleigh probability and Rice width with `2/N_eff`; for a strongly modulated exposure this
  understates the variance of a, so the significance is overstated and the Neyman limit too tight.
- `tail_extrapolation.py` reports a one-model envelope (`low = high`, `gaussian_sigma = 0`) without a warning.
- `train_bdt.py --negative-weights drop` is offered while `ml-analysis-weights.md` says not to drop.
- `assets/inference.py` lets scored events that are missing from the split manifest through (counted only).

| Check | Result |
|---|---|
| `tools/reference_inventory.py --check` | pass (218 references) |
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4510 tests in 383 modules, 4381 pass, 0 failures, 129 skipped; profile tests all pass |

## GEANT4-FOCAL (2026-10-21, E2: macOS 26.5 arm64, Geant4 11.4.3 build A; branch `feat/geant4-focal-benchmark` from main)

Longitudinal-profile reference benchmark against ALICE FoCal-E test-beam data (M. Aehle et al., JINST 19 (2024)
P07006, arXiv:2311.07413, full text read 2026-10-21: Sec. 3, Tables 1-4, Sec. 5.7). Replaces Bathow et al. 1970
(paywalled; DESY-69-39 not on the DESY server, CDS bot challenge) and the LumiCal Moliere radius (EPJC 78 (2018) 135:
profiles in figures only, needs radial binning) as the open-access shower reference.

- layered_sim rebuilt with mixture materials (`~/Workspace/geant4-work/sim-focal`, executable sha256 d39225ea2470...);
  live suite 6/6 with `HEP_GEANT4_LIVE_TEST=1` (new: W-Ni-Cu alloy X0 within 1% of the mass-fraction rule with PDG
  X0 of W, Ni, Cu). Material dump: alloy X0 0.366 cm (Table 2 prints 0.37 cm and 6.80 g/cm2, which disagree at
  19 g/cm3); FR4 17.2 cm (Table 2: 16.0), glue as G4_MYLAR (Table 2 lists 50.3 cm for PET): together < 1.1% X0 per layer.
- Model: 20 layers (W alloy 3.5 mm, glue 0.11, Si 0.30 + 0.02, glue 0.13, Cu 0.14, FR4 1.60, air 2.70 mm; pixel
  layers 5 and 10: Al 1.5, Si 0.025, Kapton 0.05, air 2.0, Al 1.5 mm), 50 mm lateral (the 5 x 5 cm window), pencil
  e- beam, FTFP_BERT, cut 0.7 mm, 2000 events per run. Fit to pad layers 1-20 without 5, 7, 10 (t = layer number).
- Results (t_max = (alpha-1)/beta; reference = Table 3 data, alpha/beta uncertainties propagated without correlation;
  systematic 1.3% = the 50 -> 90 mm lateral variation at 100 GeV, which brackets the window):

| E (GeV) | Geant4 t_max | data t_max | rel. diff. | tolerance | detection limit | control (density) | control rel. | verdict |
|---|---|---|---|---|---|---|---|---|
| 20 | 6.790 +- 0.022 | 6.873 +- 0.781 | -1.2% | 13.6% | 15.5% | x 1.188 (15.5%) | -16.0% caught | pass |
| 60 | 8.016 +- 0.020 | 8.294 +- 0.495 | -3.4% | 8.0% | 11.8% | x 1.138 (11.9%) | -14.7% caught | pass |
| 80 | 8.335 +- 0.022 | 8.442 +- 0.434 | -1.3% | 7.2% | 9.0% | x 1.101 (9.0%) | -10.0% caught | pass |
| 100 | 8.499 +- 0.016 | 8.840 +- 0.282 | -3.9% | 5.1% | 9.3% | x 1.09 (8.1%) | -10.7% caught | pass |

- Stated plainly: without the window systematic the 100 GeV comparison fails by 0.1% (-3.85% against 3.77%); the
  variation run was planned before the results. All four energies are low (shower maximum earlier than the data), and
  our t_max is 1.6-2.8% below the authors' own Geant4 10.7 fit (Table 4) with the same stack; not modelled: pixel
  layers in the data fit (Eq. 5.2, except 60 GeV), upstream material, beam spot and leading-pad window offset (up to
  5 mm), air gap (Table 1: 2.7 mm; Sec. 3: 1.2 mm). The Gamma form does not describe the high-statistics profile
  (chi2/ndf 24-31 on 13 ndf); t_max is used as a fit summary, its SE from a 100-resample bootstrap with refits.
- Scope: e- 20-100 GeV, this stack, t_max of the pad profile in the 5 x 5 cm window. Lateral leakage still has no
  reference benchmark. Run outputs (events.csv sha256): e20 257ffef0d19d, e60 e94d7ad5f699, e80 175019cc2355, e100
  cbcaeaa2878a, e100-lat90 08da0a358c35, controls bb4dcc2e0fd2, 11824c1d261b, 0769f1e72696, 720721fbf932; specs,
  records and the benchmark output in `~/Workspace/geant4-work/focal` (not packaged: about 5 MB per run).
- Offline tests: mixture spec refusals (`RunAndPartition.test_mixture_materials_are_checked`), the Gamma fit on a
  noiseless profile, pass and a stretched-profile control caught, refusals without a published source or layers
  (`tests/skills/hep_detector/test_geant4_benchmarks.py::LongitudinalProfile`).

## GEANT4-PHASE2 (2026-10-21, E2 and the CI lock; branch `feat/geant4-phase2` from `538e7c28`, release 0.19.0)

Contracts 3.1.0: evidence records, the `geant4.upgrade_*` rule, the stanza exception, `label --upgrade`,
`build_response.py --input-record`. J14: 27/27 criteria; both study records re-issued as `validated-in-scope` for
their benchmarked scope (10 GeV mu- MPV and 100 MeV p stopping power in 300 um Si) pass `validate.py --strict` and
`dependencies.py` (run records resolved as evidence, labels not inherited); the coarse-cut scenario's upgrade is
refused; tampered copies fail with the named codes (`tests/contracts/test_geant4_upgrade.py`). Shared stanza point 5
changed, so every SKILL.md changed: the hep-measurement and hep-statistics entry references were trimmed (about 60
bytes) to keep the quick load within 25,600 bytes; `measure_entrypoints.py` reports no warning.

Full live routing rerun (`evals/routing/run_routing_eval.py`, claude-sonnet-5-5, all 415 cases, one pass; the CLI
updated itself from 2.1.305 to 2.1.306 during the run; `evals/routing/results/phase2-full-r1.json`): 388/415 strict
(390 lenient), $33.29. Against the last full run (`split-final-e79ccf80`, CLI 2.1.303, 404 common cases): 379 before,
378 after; 5 regressed, 4 improved. Three passes more of the 5 regressed cases (`phase2-regress-r1..3`, $1.33):
`co-roofit-neg-1` and `rc-neighbor-1` 3/3 pass, `t19-turns-1` 2/3; `b-ms-transform-1` (to hep-theory) and
`c-nuc-iso-2` (to hep-detector) 0/3. Control on the released 0.19.0 tree with the same CLI (`v0190-control-r1..2`,
$0.26): both 0/2, so these two follow the CLI and model environment, not this change. Total routing spend $34.88
(cap $35). No baseline was written (mixed CLI versions).

## 0.19.0 release check (2026-10-21, E2 and the CI lock)

Release branch `release/0.19.0` from main `f9a38965` (#183 Geant4 capability, #184 follow-ups; main CI green). Minor
release; contracts unchanged (3.0.1). The ams02-research companion (requires hep-research `>=0.11.0`) needs no change.

What changed: version 0.19.0 in both manifests, `pyproject.toml`, the README, the two assets and the theory-profile
scripts; CHANGELOG `Unreleased` is `0.19.0`. Examples regenerated (E2; `bc-propagation-fit` with the CI lock): only
version strings and the hashes that cover them change (`unfolding-coverage` drifted at 1e-14 and was left as
committed); the sbottom benchmark artifacts' `plugin` string edited by hand; theory-profile artifacts regenerated by
their scripts. The Geant4 J14 recorded run records keep the version they were recorded with (0.18.1).

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4484 tests, 4356 pass, 0 failures, 128 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 25 pass, 0 fail, 2 skipped; 4484 tests, 4263 pass, 0 failures, 221 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## GEANT4-FOLLOWUPS (2026-10-21, E2, branch `feat/geant4-followups` from `b1048f66`)

Live routing of the 11 Geant4 cases (`evals/routing/run_routing_eval.py`, claude-sonnet-5-5, Claude Code 2.1.305,
one pass, $0.88, `evals/routing/results/geant4-cases-r1.json`): 10/11 strict. The miss, `g4-underspec-2` (zh-Hant
"simulate this with Geant4 for me"), loaded hep-detector first and then asked five clarifying questions (setup,
particle and energy, observable, physics list, installation), refusing to guess detector parameters: scored
skill-instead-of-question by the harness; it did not ask for a precision target and offered a default physics list.
No description changed.

Gaps from GEANT4-INDEPENDENT closed: leakage by face (live, 200 lead-glass showers: the three faces sum to the four
categories within 1e-6 per event; 1 GeV e- in 2 cm lead glass gives rear leakage 0.9416, albedo 0.0006, lateral 0.0001
of the beam energy, against 0.956 from the PDG profile with b = 0.5, plausible); leakage observables in `summarize`;
`shower-containment` (gamma_p checked against closed forms to 1e-13); the shower and citation rules (citation source:
the run banner in 11.4.3 `G4RunManagerKernel.cc`); optional Sternheimer inputs. Highland E4 text revised from the RPP
2024 chapter read 2026-10-21. `check_citations.py` DOI fix with a regression test. J14 regenerated: 21/21 criteria,
byte-identical replay; the study records cite the literature record and gain no gap.
`run_all_checks.py --no-cli --jobs 6`: 25 pass, 0 fail, 2 skipped; 4484 tests, 4306 pass, 0 failures, 178 skipped;
live `tests.adapters.test_geant4.Live` pass (5 tests, with the leakage-by-face sum).

## GEANT4-ADAPTER (2026-10-21, E2: macOS 26.5 arm64, Apple clang 21.0.0, CMake 4.3.2, Python 3.13; branch `feat/geant4-capability` from `cb64cba5`)

Epic TASK-geant4-00 to 03, WP1. Geant4 11.4.3 (commit 2ee379e6843e55b9c6bbb835d2a2b03cc998fef0) built by
`adapters/geant4/assets/geant4_build.py` in `~/Workspace/geant4-work/` (no system-wide installation; hosts contacted
github.com, cern.ch, both user-approved), C++17, MT, internal CLHEP, no visualization, 11 datasets (no G4NDL), each MD5
checked at download and content-hashed after unpacking. Recorded runs and excerpts: `tests/adapters/fixtures/geant4/`.

| Check | Result |
|---|---|
| Build A, then clean rebuild B (fresh clone and download) | `geant4-config --version` 11.4.3 both; all 11 dataset content hashes identical; `geant4_build.py check` ok |
| Example values, build A against B, same seeds | B1, TestEm3, TestEm5 extracted values identical (72 quantities) |
| Official examples against the reference outputs (`geant4_examples.py compare`) | 48 compared quantities (B1 runs 0-1, TestEm3 run 0, TestEm5 runs 0-4), Bonferroni z_crit 3.28 (alpha 0.05): all pass, largest abs(z) 2.99; B4a smoke passes |
| TestEm3 run 0 mirror (10000 events) | first comparison failed on the lAr track length (z = 3.81) because the 3-digit print was treated as 4; per-field print precision from Run.cc added; fresh-seed rerun with the rule declared first: 7/7 pass, largest abs(z) 1.58 (z_crit 2.69) |
| TestEm5 run 0 mirror (1e5 events) | 6/6 pass |
| Overlaps; shifted-slab negative test | 0 reports; shifted slab caught (3 GeomVol1002 reports) |
| Material budget (geantino, TestEm3 geometry); tampered dump | sum t/X0 = 22.525 closes to 1e-9; tampered density caught |
| Energy balance (EM-only, 200 events with killed e+) | residual RMS 1.5e-6 MeV; omitting 2 m_e c^2 (+17.4 MeV mean) and double-counting booked energy (-163 MeV) both caught in every event; an injection with nothing to act on is now incomplete (exit 3) |
| Data path pointed at build B's copy of G4EMLOW | run `failed` |
| Bit-identical rerun (same build, serial) | CSV identical |
| Scan of 3 cuts under `run_workflow.py`; 4-chunk `local_partition.py` run | all steps ok with orchestration and Geant4 records; merge has no duplicate events, abs(z) <= 2.0 against a single run |
| `python3 -m unittest tests.adapters.test_geant4` | 31 offline pass, 4 live skipped; with `HEP_GEANT4_LIVE_TEST=1`: all pass (UI commands accepted between physics construction and `/run/initialize`, a bad one refused; MT merge in event order) |

The Apptainer definition `assets/geant4.def` was not built (no container runtime on E2). Every record is
`unvalidated`; the comparisons are verification, not validation.

## GEANT4-STUDY (2026-10-21, E2, same branch)

WP2: `skills/hep-detector/scripts/check_geant4_study.py`, `geant4_benchmarks.py`, the rule table and the protocol. The
Bethe implementation reproduces the PDG silicon muon table (Groom, Mokhov and Striganov, 2024 edition, retrieved
2026-10-21 from pdg.lbl.gov) within 0.3 % at 100, 300 and 1000 MeV and its density effect to 2e-3; at 10 GeV it is 1 %
low (the table's ionization column includes high-energy corrections). RPP 2024 equation numbers checked in the chapter
PDF (sha256 1b328278...): Bethe 34.5, delta 34.7, Delta_p 34.12 (j = 0.200), Highland 34.16, t_max 34.36; the Highland
text gives no "11 %" accuracy (the plugin's E4 statement is not from this edition). Hadronic transitions read in the
11.4.3 source (QGSP_BIC BIC to 1.5 GeV, FTF-cascade 3-6 GeV, QGS-FTF 12-25 GeV).

| Check | Result |
|---|---|
| `tests.skills.hep_detector.test_check_geant4_study`, `test_geant4_benchmarks` | 29 pass |
| Registration set (documented claims, audit, script guards, reference links, CLI robustness and contract, constant literals) | pass (the script-guard test found an overflow on 1e308 MeV, fixed by input guards) |
| `check_layering.py`, `reference_inventory.py --check`, `measure_entrypoints.py` | pass; no new warning; SKILL.md and entry references unchanged |

## GEANT4-J14 (2026-10-21, E2, same branch)

`examples/geant4-thin-silicon/` live (2 min 43 s, 26 Geant4 runs) and offline replay: 21/21 criteria pass; replay
byte-identical to the committed output wherever --out is; live rerun into a temporary folder gives the recorded
verdicts. thin-layer-mpv (10 GeV mu-, 300 um Si, 60000 events): +1.4 % from the PDG Delta_p, detection limit 8.3 %,
control (density x 1.083) caught; stopping-power (100 MeV p, 30000 events): -0.18 % from Bethe, limit 3.8 %, control
(x 1.038) caught; convergence gates pass; variations not resolved (SE about 1 %); FTFP_BERT_EMZ excluded as the same
model. Scenarios: coarse cut stopped by the gate, density +10 % caught, dump-origin inputs flagged. Study records pass
`validate.py --strict` and `dependencies.py`; the response passes `--strict` and `response_adapter.py --validate`; the
report passes `check_citations.py` (citations by key: the tool truncates DOIs with parentheses). The four DOIs were
verified on INSPIRE-HEP with `adapters/literature-lookup` (responses in `lookups/`).

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6` | 25 pass, 0 fail, 2 skipped (CLI host checks); 4476 tests, 4299 pass, 0 failures, 177 skipped |
| `check_routing_static.py` | 415 cases, empty failed, coverage and topic errors; rerunning `make_cases.py` gives no difference |
| `check_ownership.py`, `check_retired_names.py`, `check_packaging.py`, `capability_map.py --check` | pass |

## GEANT4-INDEPENDENT (2026-10-21, E2, same branch)

Epic Validation 2: an agent that did not write the code ran "estimate the longitudinal leakage of 1 GeV electrons in
2 cm of lead glass with Geant4" through the docs and tools (outputs in `~/Workspace/geant4-work/independent-validation/`;
pdg.lbl.gov contacted for the lead-glass table). Leakage fraction 0.9427 +- 0.0002 (MC), `unvalidated`. R1, R2, R4,
R6, R7 triggered; R3 partly (no rule covers EM showers or containment); R5 not (no reference benchmark for leakage;
the shower-shape sanity check does not apply: the 1.58 X0 slab does not contain t_max); R8 not (no tool asks for a
literature record outside J14). Bugs found and fixed: an uncontained shower maximum was "implausible" with no gap (now
not-applicable and a gap); an energy-balance injection that changes no event passed (now exit 3); the study record did
not list the absence of a reference benchmark (now a gap); scan points reused the base seeds (now s1 + k). Left open: no
leakage observable in `summarize`, rear leakage not separated from albedo, the schema requires Sternheimer inputs even
when no benchmark uses them.

## 0.18.1 release check (2026-10-21, E2 and the CI lock)

Release branch `release/0.18.1` from main `9298ab21` (#181: the sci-fix ledger review, SCIFIX-LEDGER-REVIEW below; main
CI green). Patch release; contracts unchanged (3.0.1). The ams02-research companion (requires hep-research `>=0.11.0`)
needs no change.

What changed: version 0.18.1 in both manifests, `pyproject.toml`, the README, the two assets and the theory-profile
scripts that record it; CHANGELOG `Unreleased` is `0.18.1`. Examples regenerated (E2; `bc-propagation-fit` with the CI
lock; `eic-profile-routing`): only version strings and the hashes that cover them change (`unfolding-coverage` drifted at
1e-14 and was left as committed); the sbottom benchmark artifacts' `plugin` string edited by hand; theory-profile
artifacts regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4405 tests, 4283 pass, 0 failures, 122 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 25 pass, 0 fail, 2 skipped; 4405 tests, 4190 pass, 0 failures, 215 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## SCIFIX-LEDGER-REVIEW (2026-10-21, E2v and the CI lock; branch `docs/ledger-review`)

The maintainer's review of `docs/evidence/sci-fixes.json` (decisions of 2026-10-20 and 2026-10-21, recorded in
`docs/maintenance.md`): an AI-written oracle counts as an independent kind only with a basis (locator, third-party,
exhaustive, person); a locator names an equation, table or page; adapted parent runs count when they only add imported
modules or guard an import; DR-WP2-06 is split; C4 entries get sampled checks beyond their domain. Every counted kind is
now an `independence` record (kind, test, basis, detail), checked by `tests/tools/test_scifix_ledger.py`.

**Sources read for locators** (2026-10-21; never from memory; read level as stated):

| Source | Identifier, URL | Read | Locators used |
|---|---|---|---|
| PDG RPP 2024, 34. Passage of Particles Through Matter (rev. Aug. 2023) | https://pdg.lbl.gov/2024/reviews/rpp2024-rev-passage-particles-matter.pdf | page | Bethe eq. (34.5) p. 4, W_max (34.4) p. 3, K Table 34.1 p. 2; Highland (34.16) p. 16; Cherenkov angle (34.41) p. 33, yield (34.43), (34.44) p. 34 |
| PDG RPP 2024 and 2025, 35. Particle Detectors at Accelerators | https://pdg.lbl.gov/2024/reviews/rpp2024-rev-particle-detectors-accel.pdf, https://pdg.lbl.gov/2025/reviews/rpp2025-rev-particle-detectors-accel.pdf | page | calorimeter resolution (35.43) p. 82 (2024), (35.50) p. 92 (2025); Gluckstern (35.68), multiple scattering (35.70) p. 112 (2025) |
| PDG Atomic and Nuclear Properties, water (liquid) | https://pdg.lbl.gov/2024/AtomicNuclearProperties/HTML/water_liquid.html | page | I = 79.7 eV |
| Vehtari, Gelman, Simpson, Carpenter, Buerkner, Bayesian Analysis 16 (2021) 667 | arXiv:1903.08008v5, DOI 10.1214/20-BA1221 | full text | R-hat eqs. (1)-(4), autocorrelation (10), ESS (12)-(13), rank normalization (14), folding (15), tail ESS (16), quantile MCSE (20) |
| Feldman, Cousins, Phys. Rev. D 57 (1998) 3873 | arXiv:physics/9711021v2, DOI 10.1103/PhysRevD.57.3873 | full text | ordering ratio eq. (4.1) and the non-increasing adjustment, Sec. IV.A, p. 8; Table IV p. 37 matches the fixture |
| Pierre Auger Collaboration, JCAP 03 (2019) 018 | arXiv:1811.04660v2 | full text | Gaisser-Hillas form eq. (2.1), p. 3 |
| M.B. Thompson, A Comparison of Methods for Computing Autocorrelation Time (2010) | arXiv:1011.0175v1 | full text | tau = 1 + 2 sum rho_k eq. (4); AR(p) autocorrelation time eq. (7), p. 2, giving (1 + rho)/(1 - rho) for AR(1); p. 3: rho = 0.98 gives 99 |
| PDG RPP 2024, 30. Cosmic Rays | https://pdg.lbl.gov/2024/reviews/rpp2024-rev-cosmic-rays.pdf | full text | does not state the Gaisser-Hillas form |
| Gaisser, Hillas, Proc. 15th ICRC 8 (1977) 353 | ADS 1977ICRC....8..353G | not opened | (no readable copy) |

Found on the way: the repository cited the Feldman-Cousins adjustment as Sec. IV.B (the Gaussian case); it is Sec. IV.A
(`core/stats/poisson_diagnostics.py` docstring and its `construction` string, `tests/core/test_stats_poisson.py`).
Vehtari et al. eq. (10) as printed scales the lag term by N/(N-1); `bayes_diagnostics.py` and its reference follow the
Stan/ArviZ implementation (biased autocovariance), take the 95% tail indicator as x >= q95 and add the improved last term
only when positive (hepstats:S07 notes). `multiple_scattering.py` uses the Highland leading term (34.16), not the 0.016
coefficient of (35.70), as `tracking-and-vertexing.md` states.

**Grades after the review:** every entry meets its minimum. BAYES-T24 (S1) first fell to C2: its ArviZ and located SciPy
oracles are one kind, Vehtari et al. state no AR(1) ESS, and its analytic AR(1) check had no source; Thompson's eq. (7)
located it (arXiv:1011.0175v1, read 2026-10-21), so it is C3 (independent implementation, analytic, invariant, negative
control). DR-WP2-06 became DR-WP2-06-CALO (C3, D3), -PID (C3, D2) and -MS (C3, D3); its tag-and-probe, pileup and
front-end parts (guards and labels) left the ledger; advisories SFA-2026-017..019 point to the new entries. Oracle kinds
relabelled where the qualifying oracle is symbolic or an independent implementation (CLS-LOGINTERP, F01-F03,
POISSON-SF, POISSON-500, COV-NOREPAIR, ROBUST-CAMPAIGN, ML-SPLITS) and kinds without a basis removed.

**Tests added or extended** (CI lock and E2v pass): third-party cross-checks with scipy.stats, SymPy, numpy.linalg and
Python's own formatting (F01, F02, F03, POISSON-SF, POISSON-500, CLS-LOGINTERP, RC-A2, RC-A3, ROBUST-CAMPAIGN); pyhf
oracles for ML-K05 and ML-NEGWEIGHTS, added to the required stats-backends gate (`tools/run_required_backends.py`);
exhaustive checks for COV-NOREPAIR (343 matrices), ML-SPLITS (19,999 integers in 7 forms) and the split-conformal rank
(ML-DOMAIN); scipy.optimize.brentq roots and a (2m, 2z) invariant for DR-WP2-06-MS; the z^2 Bethe invariant and the
I = 75 eV negative control for DR-WP2-06-PID; sampled checks beyond the exhaustive domains of BLINDING-ROUNDING-ZEROS,
CANONICAL-KEY-ZERO-FRACTION, RC-A5, RC-A6 and ML-CALIBRATION; locators cited in the test docstrings.

## 0.18.0 release check (2026-10-20, E2 and the CI lock)

Release branch `release/0.18.0` from main `5ad39f54` (#179: the advisory backfill; earlier #165-#178: the sci-fix
correction plan PR-1 to PR-7, three sci-fixes, the pdg and torch-backend CI gates). Contracts 3.0.1 (patch: the
validator's sample-name comparison, SCIFIX-SAMPLE-NAME). The ams02-research companion (requires hep-research
`>=0.11.0`, profile contracts `>=2.0`) needs no change.

What changed: version 0.18.0 in both manifests, `pyproject.toml`, the README, the three assets and the theory-profile
scripts that record it; contracts 3.0.1 in `contracts/__init__.py` (with its history line), `contracts/vocab/core.json`,
the two tests that pin it and the 131 fixtures (`tests/contracts/make_fixtures.py` regenerates them identically);
CHANGELOG `Unreleased` is `0.18.0`; SFA-2026-001 to -003 gain their `fixed: 0.18.0` event (affected releases now end
at 0.17.0). Examples regenerated (E2; `bc-propagation-fit` with the CI lock; `eic-profile-routing` too): only version
strings and the hashes that cover them change (`unfolding-coverage` drifted at 1e-14 and was left as committed); the
sbottom benchmark artifacts' `plugin` string edited by hand; theory-profile artifacts regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4388 tests, 4266 pass, 0 failures, 122 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 25 pass, 0 fail, 2 skipped; 4388 tests, 4175 pass, 0 failures, 213 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## SCIFIX-TORCH-GATE (2026-10-20, E2v and the CI lock; branch `ci/torch-backend-gate`)

The last open ledger gap (ML-DOMAIN): its PyTorch tests ran only in the optional, continue-on-error `torch-cpu` job.
On `54ee003a` the required unit jobs skipped 258 tests and `torch-cpu` 201: 60 tests in 9 hep-ml modules run only
with PyTorch (53 'PyTorch not installed', 4 'PyTorch is required to build datasets', 3 'PyTorch is required to
measure real allocations'). New required job `torch-backend`: the CI lock plus torch 2.14.1 and torchvision 0.29.1
(CPU wheels; the versions the unpinned job resolved and E2 runs), the 9 modules through
`tools/run_required_backends.py --require torch==2.14.1,torchvision==0.29.1`, so a test skipped for PyTorch fails.
Two clean-degradation tests meant for PyTorch's absence (`test_hep_ml_skill.CleanDegradationWithoutTorchTests`, run
by the jobs without torch) are allowed by the new `--allow-skip-reason` option and listed under
`skips_allowed_by_reason`. Locally (E2v): 211 run, 0 failures, those 2 skips allowed, exit 0, about 73 s; without
PyTorch (CI lock): exit 1. `tests/tools/test_pyproject.py` checks that every module marking a PyTorch test is listed
(the opt-in GPU module excepted); dropping one fails it. The optional job stays as an early warning for new PyTorch
releases.

## SCIFIX-GAPS-CLOSED (2026-10-20, branch `ci/close-evidence-gaps`)

Three ledger gaps that needed a backend, not a code change.

**BAYES-T24, ArviZ parent record.** A scratch venv with the CI lock and ArviZ 0.23.4 (Python 3.13.2, NumPy 2.4.6,
SciPy 1.17.1: the versions of the stats-backends CI job); the fix's test file taken into a worktree of its parent,
as in SCIFIX-PARENT-RECORDS.

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/hep_statistics/test_bayes_arviz_oracle.py::ArviZOracle::test_rhat_ess_and_mcse_match` (at `d161b3b7`) | independent implementation (ArviZ 0.23.4) | fail (assertion) on five cases: MCSE ratio 0.954 (iid), 1.036 (ar1), 0.956 (heavy tails); bulk ESS ratio 0.993 (two modes stuck), 0.994 (shifted chain); ValueError: Quantiles must be in the range [0, 1] (ties) | pass | no | CI lock + ArviZ 0.23.4 |

Parent `bb0774f0`, fix `d161b3b7`. The ratios equal those of the SciPy oracle on the same parent (SCIFIX-ORACLES-BATCH2):
the two independent oracles agree.

**TH9-MASSES, PDG cross-check in CI.** New required job `pdg-cross-check` in `.github/workflows/tests.yml`: the CI lock
plus pdg 2026.0 (SQLAlchemy 2.1.5, typing_extensions 4.16.0) and `tools/run_required_backends.py --require
pdg==2026.0 --modules tests.core.test_constants`, so the bundled-masses test fails the job if it skips for pdg (missing
package or another edition). Locally with that set: 16 run, 0 skipped, exit 0; without pdg: exit 1.

**ML-DOMAIN, PyTorch tests in CI.** The optional `torch-cpu` job's check-run record on `54ee003a` (main) lists
`tests.skills.hep_ml.test_audit_domain_method` with 13 run, 0 skipped, pass: the three PyTorch tests run there. That job
is continue-on-error, so a failure does not block a merge; whether it should is left to the maintainer (ledger gap).

## SCIFIX-SAMPLE-NAME (2026-10-20, E2v and the CI lock; branch `fix/s2-key-and-sample-name`)

sci-fix SAMPLE-NAME-DOT-SEGMENTS (S2: a validator verdict). Found by the SCIFIX-ORACLES-S2 tests: `_sample_name` in
`contracts/validate.py` removed only a leading './', so `ml.calibration_on_fit_sample` passed a calibration validated
on its fit sample written as 'work/./val_scores.csv'. The fix drops '.' segments anywhere and repeated or trailing
separators; '..' is kept. Contracts patch change (3.0.1, to be set at the release).

**Correctness (C2):** `tests/skills/hep_ml/test_audit_calibration_identity.py::SampleNameDotSegmentTests::
test_dot_segments_anywhere_in_the_path_name_one_sample`: 120 spellings of 'work/val_scores.csv' with '.' segments in
the middle ('/./', '/././', '//./', '/.//', '/././/') and optionally at the end ('/.', '/'), with or without a leading
'./', with '/' or '\\', in both cases, each paired with the plain name of the same file and of the other file in both
orders (480 validations); the rule fires exactly when pathlib.PurePosixPath names one file. Negative control: the
pre-fix rule misses all 240 same-file pairs.

**Discrimination (D3):**

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/hep_ml/test_audit_calibration_identity.py::SampleNameDotSegmentTests::test_dot_segments_anywhere_in_the_path_name_one_sample` | independent implementation | fail (assertion): 240 subtests (every same-file pair not flagged) | pass | no | E2v |

Parent: `6344738e` (this branch's first commit) with the test file copied in. Local mutants of `_sample_name`, all
killed: the revert, '.' segments kept, empty segments kept.

## SCIFIX-CANONICAL-KEY (2026-10-20, E2v and the CI lock; branch `fix/s2-key-and-sample-name`)

sci-fix CANONICAL-KEY-ZERO-FRACTION (S2: an overlap check can pass with the same ID in two splits). Found by the
SCIFIX-ORACLES-S2 tests: `canonical_key` in `skills/hep-ml/scripts/check_split_integrity.py` (and its copy in
`assets/train_classifier.py`) read a text with a zero fraction through int(), so "007.0" was "7" while "007" stayed
"007", and "+5.0" was "5" while "+5" stayed "+5". The fix keeps the integer part as written; the documented rule
(a string keeps its digits, "007" is not 7) is unchanged. Side effect: the text "-0.0" is "-0", no longer the key of
the float -0.0 ("0"); a negative zero is not a realistic ID.

**Correctness (C4, exhaustive):** `tests/skills/hep_ml/test_audit_split_tools.py::GroupKeyTests::
test_text_with_a_zero_fraction_keeps_its_digits_exhaustively`: every ASCII digit string of 1 to 4 digits, unsigned,
with '+' or with '-' (33,330 texts), with each of '.', '.0', '.000', has the key of the text itself in both case modes.
Negative control: the pre-fix int() reading splits 13,331 of them (every '+' text, unsigned or '-' texts with a
leading zero, and '-0'). The ML-SPLITS oracle (`test_canonical_key_against_an_independent_reading_of_its_rule`) now
keeps the integer part as written; the trainer agreement test's KEYS gain "007.0", "+5", "+5.0".

**Discrimination (D3):**

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/hep_ml/test_audit_split_tools.py::GroupKeyTests::test_text_with_a_zero_fraction_keeps_its_digits_exhaustively` | exhaustive | fail (assertion): '+0.' and '+0' are different keys | pass | no | E2v |
| `tests/skills/hep_ml/test_audit_split_tools.py::GroupKeyTests::test_canonical_key_against_an_independent_reading_of_its_rule` | independent implementation | fail (assertion): 6 subtests ('5' != '+5', '0' != '-0', '1' != '١', both case modes) | pass | no | E2v |
| `tests/skills/hep_ml/test_audit_train_keys.py::KeyAgreementTests::test_asset_copy_matches_the_split_tools` | consistency (not counted) | pass (both copies had the old rule) | pass | no (needs PyTorch: E2v) | E2v |

Parent: `54ee003a` (main) with this branch's test files copied in. Local mutants, all killed: the revert, stripping
only a '+', dropping leading zeros (split tools; CI lock), and a revert of the trainer copy only (agreement test; E2v,
on a temporary copy of the assets).

## SCIFIX-ROUNDING-ZEROS (2026-10-20, E2v and the CI lock; branch `fix/blinding-trailing-zeros`)

sci-fix BLINDING-ROUNDING-ZEROS (S2: a wrong verdict, the scan passed with a sealed value printed). Found by the
SCIFIX-ORACLES-S2 tests: `_printed_match` read every trailing zero of an integer as a printed digit (step 1), so
22000, 22,000 and 22010 passed for a sealed 22014 while 2.20e4 was a hit. The fix reads an integer token's trailing
zeros (no point, no exponent) as rounding, down to 3 significant digits. Environments as in SCIFIX-ORACLES-BATCH2.

**Correctness (C4, exhaustive):** `tests/core/test_blinding.py::RoundingZerosTests` compares the match with an oracle
in Decimal (the token equals the sealed value rounded half up or half down at a place its trailing zeros allow,
never below 3 significant digits) over every sealed n and n + 0.5, n = 100 to 4999, and every integer token ending
in zero within 600 of it: 1,149,200 pairs, equal on all; 8679 are renderings. Negative control: the pre-fix rule finds
1470 of them (exact or last-digit matches) and misses 7209. End to end through `scan_text`: 22000, 22,000, 22010,
22,010, -22000 are hits; 22050, 21900, 20000, 2.2e4, 22000.0 and 2.2010e4 are not.

**Discrimination (D3):**

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/core/test_blinding.py::RoundingZerosTests::test_rounding_zeros_exhaustively_against_decimal_rounding` | exhaustive | fail (assertion): token 1000 for sealed 995.0, scanner False, oracle True | pass | no | E2v |
| `tests/core/test_blinding.py::RoundingZerosTests::test_scan_text_flags_rounded_integers_and_not_coarser_ones` | behavioral | fail (assertion): 5 subtests (22000, 22,000, 22010, 22,010, -22000 not flagged) | pass | no | E2v |
| `tests/core/test_blinding.py::RenderingOracleTests::test_printed_precision_rule_against_exact_decimal_arithmetic` (oracle updated to the new rule) | independent implementation | fail (assertion): 30 subtests (integer tokens with rounding zeros) | pass | no | E2v |
| `tests/core/test_blinding_u11.py::RenderingsN12::test_unrelated_numbers_still_pass` (4730 now asserted a hit) | behavioral | fail (assertion): 4730 not flagged for 4731.3712 | pass | no | E2v |

Parent: `b34d363a` (main) with this branch's two test files copied in. Local mutants of `_printed_match`, all killed by
`RoundingZerosTests`: the revert (no rounding zeros), a 2-digit floor, a 4-digit floor, at most one rounding zero,
rounding zeros also before a point.

**False-alarm cost (measured before choosing normal over weak hits):** the 113 text outputs under `examples/` (215,002
number tokens, 4771 integers of four or more digits ending in zero) scanned for 40 random sets of 30 sealed values
(log-uniform 100 to 1e6): files with a hit 278 of 4520 (6.2%) before, 305 (6.7%) after; hits 3363 before, 4849 after.
Every hit there is a false alarm (the outputs hold no sealed value). The new matches are normal hits: the rise in
flagged files is small next to a silent pass.

## SCIFIX-ORACLES-S2 (2026-10-20, E2v and the CI lock; branch `test/scifix-oracles-s2`, plan PR-6 batch S2)

One independent oracle (axis C) for each of the ten S2 entries at C1, with a negative control that emulates the
pre-fix behaviour where one exists, and local mutants of the code under test (in memory or on a temporary copy of the
plugin; each killed means the new tests fail, the unmutated code passes). Environments as in SCIFIX-ORACLES-BATCH2;
hypothesis property tests skip in E2 (no hypothesis), and each such entry has a deterministic oracle that runs in both.
After this batch all 26 ledger entries meet their severity's minimum on both axes.

| Entry | New evidence (test file::class) | Oracle | Negative control (pre-fix, emulated) | Mutants killed | C now |
|---|---|---|---|---|---|
| F03 | `tests/core/test_stats_p0_regressions.py::T04AnalyticOracle` | analytic: two-parameter model n1 ~ Pois(mu s + theta b), n2 ~ Pois(theta c), theta ~ N(1, sigma) with closed-form minimum, gradient and Hessian; coordinates within sqrt(2e-5 (H^-1)_ii) (observed 8e-9), EDM equal to 1/2 g^T H^-1 g at every stop of fits cut after 0 to 5 iterations (24 stops), status converged exactly when that EDM is at most 1e-5 | no verdict: 14 of the 24 stops are not minima | 5 of 5 | C2 |
| ML-K05 | `tests/skills/hep_ml/test_domain_shift_report.py::ShiftCarriedByNuisance` | independent implementation: the J9 example's shape_model and fit_mu against a separate profile likelihood (per-bin background profiled, nuisance by scipy minimize_scalar, interval at delta(-2 ln L) = 1) on a synthetic three-bin template, 4 Asimov fits; ends within 1e-5 (observed 1e-11) | no shift nuisance: the shifted Asimov interval [1.040, 1.843] misses mu = 1; with it, [0.747, 1.736] | 5 of 5 | C2 |
| BLINDING-SCANNER | `tests/core/test_blinding.py::RenderingOracleTests` | independent implementation: 60 sealed values, about 34 renderings each written by the test, in the seven encodings decode_text claims, every one found with the right encoding; the printed-precision rule against exact Decimal arithmetic (over 500 must alarm, over 2000 must not); short values alarm only standalone | UTF-8 decoding with replacement misses all 8212 renderings in the UTF-16/32 files; the any-equal-token rule flags over 40 embedded short forms | 9 of 9 | C2 |
| ROBUST-CAMPAIGN | `tests/core/test_partition_safety.py::IndependentClosureTests` | analytic: the merged campaign (scripted scheduler, real runner, N = 1 to 37) equals n = N, sum = N(N-1)/2 and the sum of the chunk seeds, without engine merging, also after an interrupted then confirmed submit; a real two-process lock test forced by files (second submit refused with campaign.locked, 20 of 20 runs in each venv) | not emulated (the pre-fix state save sat outside the test files) | 3 of 3 (one, a `_sum` error, passes every existing test) | C2 |
| RC-A2 | `tests/skills/hep_authoring/test_review_fixes2.py::ReviewFixes2NumbersGenerated` | independent implementation: 3000 seeded passages whose numbers are known by construction (signs, grouping, exponents, sentence ends, CJK neighbours, units, decoys), compared as fractions with digit counts; 14,344 contains_value checks | the substring rule: 3368 of 14,344 wrong | 7 of 7 | C2 |
| RC-A3 | same file, `ReviewFixes2AdaptationContexts` and the generated-passage test | independent implementation: adaptation numbers equal the constructed numbers; a wrong 9.99 in 4 forms x 7 English and Chinese contexts fails end to end (28 of 28) | the pre-fix regex misreads 2706 of 3000 passages | (the RC-A2 tokenizer mutants) | C2 |
| RC-A5 | same file, `ReviewFixes2Rounding` | exhaustive: every three-decimal source in [-2, 2] x every display with 0 to 4 decimals within two last-digit steps, 111,581 cells (8449 ok, 11,778 warning, 91,354 error) against integer arithmetic; 12 cells end to end through audit_claims | "no rule is never an error": all 91,354 error cells called warnings | 4 of 4 | C4 |
| ML-SPLITS | `tests/skills/hep_ml/test_audit_split_tools.py::GroupKeyTests` | independent implementation: canonical_key against a decimal and string-splitting reading of its rule (17 floats incl. -0.0, subnormals, 2^53 + 2, NaN, inf; 7 integers; 29 strings), both case modes; invariant: an integer's seven forms give one key (64 integers); a hypothesis property test (CI lock) | str().strip().casefold() splits all 64 | 4 of 4 | C2 |
| ML-CALIBRATION | `tests/skills/hep_ml/test_audit_calibration_identity.py::SampleIdentityPropertyTests` | exhaustive: the event-id check over all 4096 subset pairs of six ids (729 disjoint); independent implementation: the validator's sample-name rule against PurePosixPath plus case folding over 1000 path-spelling pairs | without the id check all 4096 look disjoint (3367 share events); exact string comparison fires for none of the differing spellings | 5 of 5 | C2 |
| ML-SMALL | `tests/skills/hep_ml/test_audit_small_corrections.py`, `tests/examples/test_ml_classifier_to_inference.py` | independent implementation and published: the Student-t quantile against scipy.stats.t (df 1 to 1e4, fractional df, 7 levels, observed 1.8e-11) and the NIST/SEMATECH e-Handbook t-table (95% two-sided, 9 rows, 5e-4); analytic: the false-improvement rate equals the t-test size 0.05 within 4 binomial standard errors (2000 trials at n = 3, 5, 9: 0.0425, 0.050, 0.050); K13: the artifact comparison reports every 1e-5 move at its path while results.json stays identical | the bootstrap decision: 26.7%, 17.4%, 10.6% | 4 of 4 | C2 |

**ML-SMALL parent records** (E2v; the test files of this branch copied into worktrees, skill folder paths adapted to
`physics-ml` on the older commits):

| Evidence test | Commit | Result |
|---|---|---|
| `test_audit_small_corrections.py::...::test_false_improvement_rate_is_the_t_test_size_and_the_bootstrap_rate_is_not` | parent `f5cc59a7` | fail (assertion): rate 0.2175 at n = 3 against 0.05 +- 0.0195; n = 5 and 9 fail too |
| same | fix `fd637dcc` | fail (assertion): rate 0.0 at n = 3 and 5 (the exact sign-flip test of that commit cannot reach p < 0.05 with 5 or fewer seeds) |
| same | follow-up `db40e842` ("small-seed comparison decides with a Student-t interval") | pass |
| `test_ml_classifier_to_inference.py` K13 tests | `f5cc59a7`, `fd637dcc` | pass on both: K13 corrected a test, not code, so no parent failure is possible; its discrimination is the in-test negative control |

The t-quantile test errors on `f5cc59a7` (AttributeError: no student_t_quantile), which is not counted.

**Found, not changed** (listed as gaps in the ledger): the blinding scanner does not flag an integer printed with
rounding zeros (22000 for a sealed 22014; the rule reads the units digit as the last printed digit) and does not
list it in OUT_OF_SCOPE_RENDERINGS; canonical_key gives "+5" and "+5.0" (and "007" and "007.0") different keys; the
validator's sample name does not collapse a middle "./".

## SCIFIX-ORACLES-BATCH3 (2026-10-20, E2v and the CI lock; branch `test/scifix-oracles-batch3`, plan PR-6 batch 3)

The last three S1 entries below their requirement: second oracles, invariants and negative controls (axis C), a
per-test parent record for CLS-LOGINTERP (axis D) and local mutants for DR-WP2-06 (axis D3). Environments as in
SCIFIX-ORACLES-BATCH2. The new tests pass in both. After this batch every S1 entry meets C3 and D2.

| Entry | New evidence (test file) | Oracle kinds added | Negative control (pre-fix, emulated) | C, D now |
|---|---|---|---|---|
| CLS-LOGINTERP | `tests/examples/test_stats_benchmarks.py` (`PublishedLikelihood`) | independent implementation: the benchmark's `toy_based()` with its pool run in process and each grid point returning the exact counting CLs (n = 3, b = 3.232; expected-quantile counts 0, 1, 2, 3, 5), against the mpmath root (30 digits), tolerance the log-interpolation bound h^2/8 max abs(f'') / min abs(f') of f = ln CLs on the bracketing interval (0 at n = 0, 0.0024 to 0.019 otherwise; observed 0 to 0.015); invariant: at n = 0 the crossing is ln 20 for every b | linear interpolation of CLs: 0.036 to 0.127 high, outside every bound | C3, D2 |
| DR-WP1-01 | `tests/skills/hep_detector/test_hep_detector_audit.py` (`CherenkovChargeTests`) | independent implementation: the Frank-Tamm spectrum 2 pi alpha z^2 / lambda^2 (1 - 1/(beta n)^2) integrated numerically over 300-600 nm (scipy quad, CODATA alpha) against the CLI given the ideal-detector N0 = 2 pi alpha (1/lambda1 - 1/lambda2), z = 1, 2, 3, 26, to 1e-11 | the yield without z^2 | C3, D2 |
| DR-WP2-06 | `tests/skills/hep_detector/test_hep_detector_audit.py` (`ScriptPhysicsOracleTests`) | calorimeter fit: the fix's 2000-toy study (2% scatter, a = 0.10, b = 0.20, c = 0.0070) with numpy weighted lstsq on every toy (to 1e-10), bias of c -7.7e-6 = 0.06 sd (criterion 0.1 sd: weighting by the observed r is second order); closure on the model curve and energy-scale covariance; multiple scattering: crossover and MDR with beta(R) against their closed forms (quadratics in R^2), 45 stacks, masses and charges, to 1e-12 | calorimeter unit weights: c^2 < 0 in 24.8% of toys, mean c 0.00825 (about 10 sd); crossover with beta = 1: off by more than 1e-3 in 14 of 45 cases (slow heavy species) | C3, D3 |

### CLS-LOGINTERP (new test): fix `99a18fd8`, parent `90388aa0`

The test file of this branch, copied into worktrees of both commits; E2v. `toy_based()` and its crossing closure exist
on both, so the test reaches the pre-fix crossing.

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/examples/test_stats_benchmarks.py::PublishedLikelihood::test_toy_crossings_on_exact_counting_cls_meet_the_interpolation_bound` | independent implementation | fail (assertion): observed 5.3348 against 5.2844 (bound 0.0068); expected n = 0, 1, 2, 5: 3.118, 3.660, 4.411, 7.606 against 2.996, 3.613, 4.374, 7.478 | pass | no | E2v |

### Local mutants (axis D3), CI lock

| Entry | Mutant | Killed by |
|---|---|---|
| DR-WP2-06 | calorimeter fit with unit weights (pre-fix) | toy study |
| DR-WP2-06 | calorimeter weights 1/r^2 instead of 1/r^4 | toy study (lstsq comparison) |
| DR-WP2-06 | beta from R instead of zR | closed-form crossover |
| DR-WP2-06 | crossover with beta = 1 (pre-fix) | closed-form crossover |
| DR-WP2-06 | MDR with beta = 1 (pre-fix) | closed-form MDR |
| DR-WP2-06 | bisection stopped after 20 steps | closed-form crossover (1e-12) |

## SCIFIX-ORACLES-BATCH2 (2026-10-20, E2v and the CI lock; branch `test/scifix-oracles-batch2`, plan PR-6 batch 2)

Second oracles, invariants and negative controls for four S1 entries (axis C), a per-test parent record for the new
BAYES-T24 oracle (axis D), and local mutants of the code under test (axis D3: `docs/maintenance.md`). Environments:
E2v as in SCIFIX-PARENT-RECORDS below; the CI lock is `requirements-ci.lock` (Python 3.13.2, NumPy 2.4.6, SciPy 1.17.1,
mpmath 1.3.0, no PyTorch, no ArviZ). The new tests pass in both. Software checks: they show that the tests agree with
an independent calculation and tell the pre-fix behaviour apart, not that the methods suit a given analysis.

| Entry | New evidence (test file) | Oracle kinds added | Negative control (pre-fix, emulated) | C, D now |
|---|---|---|---|---|
| ML-DOMAIN | `tests/skills/hep_ml/test_audit_domain_method.py` | analytic: each statistic's flag rate equals the split-conformal value a = 1 - min(r, n)/(n+1) and the union lies in [a, 2a], 40 to 200 training draws, 4 standard errors; independent implementation: the reported interval equals Clopper-Pearson from `scipy.stats.beta` | per-feature min/max box: 10.5% of fresh in-distribution queries at d = 32, n = 600, against 2a = 1.7% (q = 0.99) and 5.0% (q = 0.95) | C3, D3 |
| ML-NEGWEIGHTS | `tests/skills/hep_ml/test_audit_metric_layer.py` | independent implementation: Z^2 as q0 on the Asimov dataset (mpmath, 50 digits; tolerance 1e-14 below the series switch at s/b = 1e-6, 1e-14 + 2 eps/x above); Cowan Eq. 20 against the profiled on/off likelihood (mpmath, 60 digits, numerical root of d ln L/db; agreement 5e-11 or better); cell resampling against a brute-force reading of arXiv:2109.07851 eq. 2.2 (full distance sort); invariants: Z falls as sigma_b grows and tends to the sigma_b = 0 value | the pre-fix float expression misses the reference on 212 of 483 grid points (Z = 0 at s/b = 1e-8); dropping negative events shifts the total weight | C3, D3 |
| BAYES-T24 | `tests/skills/hep_statistics/test_bayes_arviz_oracle.py` (`IndependentOracle`, runs without ArviZ) | independent implementation from Vehtari et al. 2021 with SciPy primitives (rankdata, norm.ppf, beta.ppf), direct-sum autocovariances and Geyer's pair sums: R-hat, bulk and tail ESS, quantile MCSE to 1e-12 (observed 4e-15) on the six cases; invariants: increasing maps (ESS), exact scaling (R-hat, MCSE), chain order | the ESS and MCSE of `bb0774f0`: bulk ESS 0.6% to 0.7% off, tail ESS 0.2% to 0.5%, MCSE 0.1% to 11% | C3, D3 |
| TH9-MASSES | `tests/skills/hep_detector/test_hep_detector_audit.py` (`SpeciesMassPropertyTests`) | published (second evaluation): binding energies of d, 3He, 4He from the CODATA 2022 masses equal those from AME2020 atomic mass excesses (bundled in core/constants), residuals 0.14, 0.18, 0.37 eV against 3 N sigma(m_n) + 0.1 eV; invariants over species and momenta: mass from beta inverts the kinematics, mass order, flight time grows with mass | the pre-fix table (`23910085^`, 10 eV steps): residuals 5.7, 12.4, 13.3 eV | C3, D2 |

A general affine map (2.5 x - 7) moves R-hat by 6e-6 on the iid case: rounding breaks the exact tie of the two middle
draws in |x - median|, two average ranks move by 1/2. Scaling by 4 (exact in floating point) leaves every value equal;
the test uses it and allows 1e-4 for the general map.

### BAYES-T24 (new oracle): fix `d161b3b7`, parent `bb0774f0`

The test file of this branch, copied into worktrees of both commits; E2v.

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/hep_statistics/test_bayes_arviz_oracle.py::IndependentOracle::test_diagnostics_match_the_reference_and_the_pre_fix_rules_do_not` | independent implementation | fail (assertion): MCSE ratio 0.954 (iid), 1.036 (ar1), 0.956 (heavy tails) at p = 0.05; bulk ESS ratio 0.993 (two modes stuck), 0.994 (shifted chain); ValueError: Quantiles must be in the range [0, 1] (ties) | pass | no | E2v |
| `tests/skills/hep_statistics/test_bayes_arviz_oracle.py::IndependentOracle::test_invariance_under_affine_and_increasing_maps_and_chain_order` | invariant | fail (ValueError): Quantiles must be in the range [0, 1] (ties case only; the invariants hold on the parent's other cases) | pass | no | E2v |

- `Health` tests: as in SCIFIX-PARENT-RECORDS; `ArviZOracle::test_rhat_ess_and_mcse_match`: skipped on both (no ArviZ).

### Local mutants (axis D3), CI lock

Each mutant edits one line of the code under test in memory; killed means the new tests fail. All mutants are killed;
the unmutated code passes.

| Entry | Mutant | Killed by |
|---|---|---|
| ML-DOMAIN | threshold always the held-out maximum | per-statistic rate (falls below a) |
| ML-DOMAIN | no halving of 1 - q across the two statistics (level = q) | per-statistic rate (about 2a) |
| ML-DOMAIN | conformal rank one too low | per-statistic rate, small setting (n = 100, 200 draws) |
| ML-NEGWEIGHTS | cell stops one event late | brute-force eq. 2.2; cell-sum test |
| ML-NEGWEIGHTS | equal shares in a cell instead of proportional to abs(w_i) | brute-force eq. 2.2 |
| ML-NEGWEIGHTS | Eq. 20 second term with log(1 + x) instead of log1p | profiled on/off reference |
| ML-NEGWEIGHTS | series switch moved from s/b = 1e-6 to 1e-9 | Asimov likelihood-ratio reference |
| BAYES-T24 | no improved last term in the ESS | independent oracle |
| BAYES-T24 | no monotone step in the ESS | independent oracle |
| BAYES-T24 | folded R-hat dropped | independent oracle |
| BAYES-T24 | pre-fix MCSE rule | independent oracle |
| BAYES-T24 | rank-normalization offsets (r - 1/2)/S instead of Blom's (r - 3/8)/(S + 1/4) | independent oracle |

## SCIFIX-PARENT-RECORDS (2026-10-20, E2v; branch `docs/scifix-parent-records`, plan PR-4)

Per-test parent records (axis D, `docs/maintenance.md`, "Scientific corrections: scope and evidence") for the 13 fix
commits behind the 15 ledger entries graded D0 or D1 in `docs/evidence/sci-fixes.json`. For each fix commit FIX, a
worktree of FIX^ takes every file under `tests/` that FIX added or changed (test modules and fixtures) from FIX, and
every changed test module runs on that tree and on FIX, one test at a time recorded (subtest failures count against
their test). Only tests that fail on the parent and pass on the fix are listed; the others are counted. A parent
failure is an assertion, an exception (named), or an import error of the whole module; an import error or a missing
function shows that the test needs code new in the fix, not that it would catch the defect, and is not counted as
discrimination. Two runs are adapted, as stated in their sections. Tests are named by their paths at the fix commit
(`docs/maintenance.md` maps old folder names). Software checks: they show which tests tell the parent from the fix,
not that either is physically right.

**E2v:** the E2 workstation with `~/.venvs/hep-research-e2`: Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1, mpmath 1.3.0,
pyhf 0.7.6, PyTorch 2.14.1 (CPU); no ArviZ, hypothesis or scikit-learn; `HEP_SLOW_TESTS=1` (slow tier on), no
network tests. Skipped tests are listed; a skip is unverified, not a pass.

**Result per ledger entry** (axis D after this record; the ledger has the details):

| Entry | Fix commit | D before | D now | Basis |
|---|---|---|---|---|
| FC-MONOTONE | `04338bbf` | D0 | D2 | 4 assertion failures on the parent, including the full Tables IV/VI test (slow tier) |
| POISSON-SF | `a2adc126` | D0 | D2 | 2 assertion failures (p-value 0 at n = 60, b = 5, in both CLIs); the reference tests need functions new in the fix |
| COV-NOREPAIR | `6a81109c` | D0 | D2 | 4 assertion failures on matrices (indefinite or singular ones accepted or misnamed), 2 missing records; the guide test |
| POISSON-500 | `b7b7825a` | D0 | D2 | assertion: 500.0 where 513.15 is right |
| ROBUST-MALFORMED (S4) | `d7148901` | D0 | D2 | tracebacks on malformed input on the parent (TypeError, AttributeError on a record), the defect itself |
| BLINDING-SCANNER | `b6334c04` | D0 | D2 | 2 assertion failures (low-count false alarm, undecodable log passed) |
| ROBUST-CAMPAIGN | `f7b677c9` | D0 | D2 | assertion: two concurrent submits both ran; merge guards |
| F01 | `9f1ee4a9` | D1 | D2 | adapted run: 3 assertion failures (negative mean accepted) |
| F02 | `9f1ee4a9` | D1 | D2 | adapted run: assertion, p = 0.0 reported for zero exceedances |
| F03 | `9f1ee4a9` | D1 | D2 | adapted run: the parent's shape-limit output has no `status` (the defect: no verdict); T05 tests need a method new in the fix |
| BAYES-T24 | `d161b3b7` | D0 | D1 | tie and signed-weight parts fail on the parent; the ArviZ oracle (ESS, MCSE values) skipped on both: no record for the values |
| CLS-LOGINTERP | `99a18fd8` | D1 | D1 | every parent failure needs a function new in the fix (`_crossing`); the old crossing was a closure inside the pyhf toy run. Before/after values only (5.34 -> 5.28) |
| ML-SPLITS | `811f02b6` | D1 | D2 | adapted run: 12 assertion failures (C02-C05, C14, C16, C28 cases) |
| ML-NEGWEIGHTS | `ef5d068f` | D0 | D2 | 6 assertion failures (negative weights not refused or flagged) |
| ML-SMALL | `fd637dcc` | D1 | D1 | C10, C24, C25, C26 fail on the parent (C10: false-improvement rate 0.26 and 0.15 against a bound of 0.088); K13's evidence (`tests/examples/test_ml_classifier_to_inference.py`) passes on the parent |

Evidence tests added after a fix commit (for example `tests/core/test_published_tables.py`, `tests/core/test_properties.py`,
and the oracles of plan PR-2 and PR-6) were not run on the parent: they need later code. Their discrimination rests on the
negative controls inside them (axis C), as the ledger says.

### FC-MONOTONE: fix `04338bbf`, parent `b3734189`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/core/test_stats_poisson.py::FeldmanCousinsTests::test_full_published_tables` | published (FC 1998 Table IV/VI fixture) | fail (assertion): 1.08 != 1.26 within 0.01 delta (0.17999999999999994 difference) : ('IV', 0, 2.0) | pass | no | E2v |
| `tests/core/test_stats_poisson.py::FeldmanCousinsTests::test_monotone_construction_matches_entries_where_the_plain_one_dips` | published (FC 1998 Table IV/VI fixture) | fail (assertion): 1.08 != 1.26 within 0.01 delta (0.17999999999999994 difference) : (0.9, 0, 2.0) | pass | no | E2v |
| `tests/core/test_stats_poisson.py::FeldmanCousinsTests::test_plain_construction_is_labelled_and_never_longer` | behavioral | fail (TypeError): fc_interval() got an unexpected keyword argument 'monotone' | pass | no | E2v |
| `tests/core/test_stats_poisson.py::FeldmanCousinsTests::test_published_values` | published (FC 1998 Table IV/VI fixture) | fail (assertion): 1.08 != 1.26 within 0.015 delta (0.17999999999999994 difference) : (0, 2.0) | pass | no | E2v |
| `tests/core/test_stats_poisson.py::FeldmanCousinsTests::test_upper_end_is_non_increasing_in_b` | invariant | fail (assertion): 1.22 not less than or equal to 1.09 : (0, 2.4000000000000004) | pass | no | E2v |

- `tests/core/test_stats_poisson.py`: 21 tests pass on both (not discriminating)


### POISSON-SF: fix `a2adc126`, parent `04338bbf`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/core/test_stats_likelihood_limits.py::SingleBinTests::test_exact_p_value_does_not_underflow` | independent implementation (decimal reference) | fail (assertion): 0.0 != 1.0 within 1e-06 delta (1.0 difference) | pass | no | E2v |
| `tests/core/test_stats_poisson.py::UpperTailTests::test_log_tail_and_significance_stay_finite_to_n_1000` | independent implementation (decimal reference) | fail (AttributeError): module 'core.stats.poisson_diagnostics' has no attribute 'log_poisson_sf' | pass | no | E2v |
| `tests/core/test_stats_poisson.py::UpperTailTests::test_matches_high_precision_reference` | independent implementation (decimal reference) | fail (AttributeError): module 'core.stats.poisson_diagnostics' has no attribute 'poisson_sf'. Did you mean:... | pass | no | E2v |
| `tests/core/test_stats_poisson.py::UpperTailTests::test_significance_from_log_p` | independent implementation (decimal reference) | fail (AttributeError): module 'core.stats.poisson_diagnostics' has no attribute 'z_from_log_p' | pass | no | E2v |
| `tests/core/test_stats_statistical_toys.py::BoundaryTests::test_exact_p_value_does_not_underflow` | independent implementation (decimal reference) | fail (assertion): 0.0 != 1.0 within 1e-06 delta (1.0 difference) | pass | no | E2v |

- `tests/core/test_stats_likelihood_limits.py`: 41 tests pass on both (not discriminating)
- `tests/core/test_stats_poisson.py`: 26 tests pass on both (not discriminating)
- `tests/core/test_stats_statistical_toys.py`: 28 tests pass on both (not discriminating)


### COV-NOREPAIR: fix `6a81109c`, parent `a2adc126`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/core/test_stats_likelihood_limits.py::PriorTests::test_a_singular_correlation_is_rejected` | behavioral | fail (assertion): "correlation matrix of the nuisances is singular" does not match "correlation matrix... | pass | no | E2v |
| `tests/core/test_stats_linalg.py (all 7 tests)` | closure | import error: No module named 'core.stats._linalg' | pass | no | E2v |
| `tests/core/test_stats_statistical_toys.py::RatioMeasuredTests::test_gls_constant_rejects_an_impossible_correlation` | behavioral | fail (assertion): ToyError not raised | pass | no | E2v |
| `tests/core/test_stats_statistical_toys.py::RatioMeasuredTests::test_indefinite_covariance_is_rejected_and_named` | behavioral | fail (assertion): ToyError not raised | pass | no | E2v |
| `tests/core/test_stats_statistical_toys.py::RatioMeasuredTests::test_semidefinite_covariance_is_sampled_with_the_shift_recorded` | behavioral | fail (KeyError): 'regularization' | pass | no | E2v |
| `tests/core/test_stats_unfolding_diagnostics.py::ResponseMeasuredTests::test_a_singular_supplied_covariance_is_accepted_and_reported` | behavioral | fail (KeyError): 'response_covariance_check' | pass | no | E2v |
| `tests/core/test_stats_unfolding_diagnostics.py::ResponseMeasuredTests::test_rejections` | behavioral | fail (assertion): "response_covariance is not positive semi-definite" does not match "bin-correlation ... | pass | no | E2v |
| `tests/skills/hep_statistics/test_core_stats_guide.py::CoreStatsGuide::test_every_module_has_a_section` | behavioral | fail (assertion): '`_linalg.py`' not found in '# Guide to the `core/stats` diagnostics\n\nThe owner\'s... | pass | no | E2v |

- `tests/core/test_stats_likelihood_limits.py`: 42 tests pass on both (not discriminating)
- `tests/core/test_stats_statistical_toys.py`: 30 tests pass on both (not discriminating)
- `tests/core/test_stats_unfolding_diagnostics.py`: 42 tests pass on both (not discriminating)
- `tests/skills/hep_statistics/test_core_stats_guide.py`: 5 tests pass on both (not discriminating)


### POISSON-500: fix `b7b7825a`, parent `6a81109c`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/core/test_stats_poisson.py::MeanLimitTests::test_fc_scan_keeps_its_own_documented_limit` | analytic (SciPy chi-square values recorded) | fail (assertion): DiagnosticsError not raised | pass | no | E2v |
| `tests/core/test_stats_poisson.py::MeanLimitTests::test_garwood_and_classical_limit_beyond_500` | analytic (SciPy chi-square values recorded) | fail (assertion): 500.0 != 513.1515084417051 within 1e-06 delta (13.151508441705118 difference) | pass | no | E2v |
| `tests/core/test_stats_poisson.py::MeanLimitTests::test_unbracketed_limit_fails_instead_of_returning_the_range_end` | analytic (SciPy chi-square values recorded) | fail (AttributeError): module 'core.stats.poisson_diagnostics' has no attribute 'SolveFailed' | pass | no | E2v |
| `tests/core/test_stats_poisson_numerics.py (all 5 tests)` | analytic (SciPy chi-square values recorded) | import error: cannot import name '_poisson' from 'core.stats' | pass | no | E2v |
| `tests/skills/hep_statistics/test_core_stats_guide.py::CoreStatsGuide::test_every_module_has_a_section` | analytic (SciPy chi-square values recorded) | fail (assertion): '`_poisson.py`' not found in '# Guide to the `core/stats` diagnostics\n\nThe owner\'... | pass | no | E2v |

- `tests/core/test_stats_poisson.py`: 29 tests pass on both (not discriminating)
- `tests/skills/hep_statistics/test_core_stats_guide.py`: 5 tests pass on both (not discriminating)


### ROBUST-MALFORMED: fix `d7148901`, parent `b7b7825a`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/contracts/test_robustness.py::GateMalformedInputTests::test_artifact_type_of_the_wrong_json_type` | behavioral | fail (TypeError): unhashable type: 'list' | pass | no | E2v |
| `tests/contracts/test_robustness.py::GateMalformedInputTests::test_explicit_null_phase_space_and_normalization` | behavioral | fail (AttributeError): module 'contracts.comparison.gate' has no attribute 'check' | pass | no | E2v |
| `tests/contracts/test_robustness.py::GateMalformedInputTests::test_malformed_plan_entries_are_findings_and_not_applied` | behavioral | fail (AttributeError): module 'contracts.comparison.gate' has no attribute 'check' | pass | no | E2v |
| `tests/contracts/test_robustness.py::GateMalformedInputTests::test_one_sided_cuts_with_null_bounds` | behavioral | fail (AttributeError): module 'contracts.comparison.gate' has no attribute 'check' | pass | no | E2v |
| `tests/contracts/test_robustness.py::GateMalformedInputTests::test_seeded_mutations_never_raise` | behavioral | fail (AttributeError): module 'contracts.comparison.gate' has no attribute 'check' | pass | no | E2v |
| `tests/contracts/test_robustness.py::GateMalformedInputTests::test_wrongly_typed_artifact_is_refused_with_paths` | behavioral | fail (AttributeError): module 'contracts.comparison.gate' has no attribute 'check' | pass | no | E2v |
| `tests/core/test_evidence_ledger.py::LedgerTests::test_malformed_records_are_findings_with_field_paths` | behavioral | fail (AttributeError): 'str' object has no attribute 'get' | pass | no | E2v |

- `tests/contracts/test_robustness.py`: 10 tests pass on both (not discriminating)
- `tests/core/test_evidence_ledger.py`: 13 tests pass on both (not discriminating)


### BLINDING-SCANNER: fix `b6334c04`, parent `d7148901`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/core/test_blinding.py::FigureTests::test_fill_between_hist2d_imshow_and_text_are_caught` | behavioral | fail (TypeError): check_figure() takes 2 positional arguments but 3 were given | pass | no | E2v |
| `tests/core/test_blinding.py::FigureTests::test_masked_areas_images_and_a_blinded_label_pass` | behavioral | fail (TypeError): check_figure() takes 2 positional arguments but 3 were given | pass | no | E2v |
| `tests/core/test_blinding.py::LowCountAndEncodingTests::test_low_counts_need_a_standalone_token` | behavioral | fail (assertion): 1, 'sealed_value': 0.0, 'token': '0'}] | pass | no | E2v |
| `tests/core/test_blinding.py::LowCountAndEncodingTests::test_undecodable_text_is_incomplete_never_pass` | behavioral | fail (assertion): + incomplete | pass | no | E2v |
| `tests/core/test_blinding.py::LowCountAndEncodingTests::test_utf16_and_latin1_logs_are_read` | behavioral | fail (KeyError): 'encoding' | pass | no | E2v |

- `tests/core/test_blinding.py`: 25 tests pass on both (not discriminating)


### ROBUST-CAMPAIGN: fix `f7b677c9`, parent `f5070718`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/adapters/test_batch_slurm.py::InterruptedSubmitCliTests::test_confirm_and_abandon` | behavioral | fail (SystemExit): 2 | pass | no | E2v |
| `tests/core/test_partition_safety.py::MergeGuardTests::test_non_finite_results_are_refused` | behavioral | fail (assertion): ? ++ | pass | no | E2v |
| `tests/core/test_partition_safety.py::MergeGuardTests::test_strings_are_not_concatenated` | behavioral | fail (assertion): ? ++ | pass | no | E2v |
| `tests/core/test_partition_safety.py::SafetyTests::test_a_refused_submission_is_recorded_as_not_submitted` | behavioral | fail (IndexError): list index out of range | pass | no | E2v |
| `tests/core/test_partition_safety.py::SafetyTests::test_an_abandoned_submission_needs_a_reset_to_run_again` | behavioral | fail (IndexError): list index out of range | pass | no | E2v |
| `tests/core/test_partition_safety.py::SafetyTests::test_an_interrupted_submit_leaves_a_recoverable_intent_record` | behavioral | fail (IndexError): list index out of range | pass | no | E2v |
| `tests/core/test_partition_safety.py::SafetyTests::test_concurrent_submits_cannot_both_run` | behavioral | fail (assertion): 2 != 1 | pass | no | E2v |
| `tests/core/test_partition_safety.py::SafetyTests::test_the_lock_is_released_and_reentrant` | behavioral | fail (AttributeError): module 'core.partition.campaign' has no attribute 'campaign_lock' | pass | no | E2v |

- tests/adapters/test_batch_slurm.py::RealSlurmTests::test_example_campaign_on_real_slurm: skipped (parent skipped, fix skipped): real Slurm not available (HEP_SLURM_TEST=1 and sbatch on PATH)
- `tests/adapters/test_batch_slurm.py`: 9 tests pass on both (not discriminating)
- `tests/core/test_partition_safety.py`: 0 tests pass on both (not discriminating)
- `tests/core/test_partition_states.py`: 14 tests pass on both (not discriminating)


### F01, F02, F03: fix `9f1ee4a9`, parent `1d42271a`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/core/test_stats_p0_regressions.py (all 20 tests)` | behavioral | import error: cannot import name 'tail_estimation' from 'core.stats' | pass | no | E2v |
| `tests/skills/hep_statistics/test_core_stats_guide.py::CoreStatsGuide::test_every_module_has_a_section` | behavioral | fail (assertion): update the guide and this test together | pass | no | E2v |

- `tests/core/test_stats_saturated_gof.py`: 5 tests pass on both (not discriminating)
- `tests/skills/hep_statistics/test_core_stats_guide.py`: 5 tests pass on both (not discriminating)


### F01, F02, F03 (adapted): fix `9f1ee4a9`, parent `1d42271a`

Adapted run: the parent tree also takes `core/stats/fit_diagnostics.py`, `core/stats/tail_estimation.py` from the fix (modules new in the fix that the test imports; the code under test is the parent's).

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/core/test_stats_p0_regressions.py::T01LikelihoodDomain::test_negative_mean_with_zero_count_is_invalid` | behavioral | fail (assertion): True is not false | pass | no | E2v |
| `tests/core/test_stats_p0_regressions.py::T01LikelihoodDomain::test_single_bin_log_likelihood_rejects_negative_mean` | behavioral | fail (assertion): 0.0 not less than or equal to -1e+300 | pass | no | E2v |
| `tests/core/test_stats_p0_regressions.py::T01LikelihoodDomain::test_zero_mean_zero_count_is_valid_and_positive_count_is_not` | behavioral | fail (assertion): True is not false | pass | no | E2v |
| `tests/core/test_stats_p0_regressions.py::T02T03ToyTails::test_zero_exceedances_give_a_bound_not_a_zero` | behavioral | fail (assertion): 0.0 is not None | pass | no | E2v |
| `tests/core/test_stats_p0_regressions.py::T04FitStatus::test_shape_limit_reports_failed_status_and_cli_exit` | behavioral | fail (KeyError): 'status' | pass | no | E2v |
| `tests/core/test_stats_p0_regressions.py::T05GlobalVersusConditional::test_boundary_optimum_is_accepted_by_kkt` | behavioral | fail (AttributeError): '_ShapeModel' object has no attribute 'log' | pass | no | E2v |
| `tests/core/test_stats_p0_regressions.py::T05GlobalVersusConditional::test_degraded_global_fit_is_refitted` | behavioral | fail (AttributeError): '_ShapeModel' object has no attribute 'log' | pass | no | E2v |
| `tests/core/test_stats_p0_regressions.py::T05GlobalVersusConditional::test_unrepairable_violation_is_a_failure` | behavioral | fail (AttributeError): '_ShapeModel' object has no attribute 'log' | pass | no | E2v |

- `tests/core/test_stats_p0_regressions.py`: 12 tests pass on both (not discriminating)


### BAYES-T24: fix `d161b3b7`, parent `bb0774f0`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/core/test_stats_weighted_mc.py::SignedWeightTemplates::test_effective_count_likelihood_refuses_signed_weights` | behavioral | fail (assertion): ToyError not raised | pass | no | E2v |
| `tests/skills/hep_statistics/test_bayes_arviz_oracle.py::Health::test_ties_do_not_crash_and_undefined_mcse_is_flagged` | behavioral | fail (ValueError): Quantiles must be in the range [0, 1] | pass | no | E2v |
| `tests/skills/hep_statistics/test_bayes_arviz_oracle.py::Health::test_unhealthy_chains_are_never_converged` | behavioral | fail (ValueError): Quantiles must be in the range [0, 1] | pass | no | E2v |

- `tests/core/test_stats_weighted_mc.py`: 1 tests pass on both (not discriminating)
- tests/skills/hep_statistics/test_bayes_arviz_oracle.py::ArviZOracle::test_rhat_ess_and_mcse_match: skipped (parent skipped, fix skipped): ArviZ 0.23.4 not installed: the oracle comparison is unverified
- `tests/skills/hep_statistics/test_bayes_arviz_oracle.py`: 0 tests pass on both (not discriminating)


### CLS-LOGINTERP: fix `99a18fd8`, parent `90388aa0`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/examples/test_stats_benchmarks.py::PublishedLikelihood::test_crossing_interpolates_log_cls` | independent implementation (exact counting CLs) | fail (AttributeError): module 'bench_published_likelihood_sbottom' has no attribute '_crossing' | pass | no | E2v |
| `tests/examples/test_stats_benchmarks.py::PublishedLikelihood::test_diagnosis_reruns_on_the_bare_model` | independent implementation (exact counting CLs) | fail (AttributeError): module 'bench_published_likelihood_sbottom' has no attribute 'toy_diagnosis' | pass | no | E2v |
| `tests/examples/test_stats_benchmarks.py::PublishedLikelihood::test_exact_counting_limit` | independent implementation (exact counting CLs) | fail (AttributeError): module 'bench_published_likelihood_sbottom' has no attribute '_counting_limit' | pass | no | E2v |
| `tests/examples/test_stats_benchmarks.py::PublishedLikelihood::test_toy_difference_is_diagnosed_post_hoc` | independent implementation (exact counting CLs) | fail (KeyError): 'toy_difference_explained_post_hoc' | pass | no | E2v |

- tests/examples/test_stats_benchmarks.py::PublishedLikelihood::test_asymptotic_reproduction_reruns: skipped (parent skipped, fix skipped): network and slow (downloads the HEPData pallet): set HEP_NETWORK_TESTS=1 and HEP_SLOW_TESTS=1
- `tests/examples/test_stats_benchmarks.py`: 10 tests pass on both (not discriminating)


### ML-SPLITS: fix `811f02b6`, parent `2b439e74`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/physics_ml/test_audit_split_tools.py (all 15 tests)` | behavioral | import error: cannot import name 'canonical_key' from 'check_split_integrity' | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_train_keys.py (all 3 tests)` | behavioral | import error: cannot import name 'canonical_key' from 'check_split_integrity' | pass | no | E2v |


### ML-SPLITS (adapted): fix `811f02b6`, parent `2b439e74`

Adapted run: in the fix's test file, the import of `canonical_key` (new in the fix) is guarded, so the other tests run against the parent's scripts; `test_canonical_numeric_keys` then errors.

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/physics_ml/test_audit_split_tools.py::GroupKeyTests::test_a4_check_reports_leakage_across_numeric_spellings` | behavioral | fail (assertion): ?                       +++++++ | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::GroupKeyTests::test_a4_numeric_group_values_are_one_group` | behavioral | fail (assertion): '1.0' | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::GroupKeyTests::test_boolean_list_object_groups_are_invalid` | behavioral | fail (assertion): PASSED | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::GroupKeyTests::test_canonical_numeric_keys` | behavioral | fail (TypeError): 'NoneType' object is not callable | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::GroupKeyTests::test_label_column_reports_class_counts_and_refuses_an_empty_class` | behavioral | fail (assertion): 'class' not found in '' | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::TemporalCheckTests::test_a1_nan_timestamp_is_invalid_input` | behavioral | fail (assertion): } | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::TemporalCheckTests::test_a2_single_entry_temporal_order` | behavioral | fail (assertion): } | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::TemporalCheckTests::test_a2_unknown_split_names_in_temporal_order` | behavioral | fail (assertion): } | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::TemporalCheckTests::test_booleans_and_unpadded_dates_are_invalid` | behavioral | fail (assertion): 1 != 2 : error: '>' not supported between instances of 'bool' and 'str' | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::TemporalCheckTests::test_empty_split_is_incomplete_under_strict` | behavioral | fail (assertion): } | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::TemporalCheckTests::test_misspelled_reserved_key_is_invalid` | behavioral | fail (assertion): 1 != 2 : error: split 'timestamp' must be a list of IDs | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::TemporalCheckTests::test_mixed_numbers_and_dates_are_invalid` | behavioral | fail (assertion): 1 != 2 : error: '>' not supported between instances of 'int' and 'str' | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_split_tools.py::TemporalSplitTests::test_a3_unpadded_date_is_refused` | behavioral | fail (assertion): } | pass | no | E2v |

- `tests/skills/physics_ml/test_audit_split_tools.py`: 2 tests pass on both (not discriminating)


### ML-NEGWEIGHTS: fix `ef5d068f`, parent `153307a6`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/physics_ml/test_audit_metric_layer.py::CalibrationWarningTests::test_temperature_warns_about_prior_shift` | behavioral | fail (KeyError): 'warnings' | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_metric_layer.py::DiscoTests::test_negative_weights_refused_by_default` | behavioral | fail (assertion): ValueError not raised | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_metric_layer.py::MetricTests::test_asimov_inputs_and_precision` | behavioral | fail (assertion): ValueError not raised | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_metric_layer.py::MetricTests::test_cell_resampling_preserves_cell_sums_and_removes_negatives` | behavioral | fail (AttributeError): module 'hep_metrics' has no attribute 'cell_resample' | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_metric_layer.py::MetricTests::test_fractional_label_is_refused_by_both_clis` | behavioral | fail (assertion): } | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_metric_layer.py::MetricTests::test_prior_shift_needs_positive_ratio` | behavioral | fail (assertion): ValueError not raised | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_metric_layer.py::MetricTests::test_signed_weight_out_of_range_flag` | behavioral | fail (AttributeError): module 'hep_metrics' has no attribute 'signed_weight_out_of_range' | pass | no | E2v |
| `tests/skills/physics_ml/test_calibration.py::Cli::test_cli_strict_json_and_calibration_block` | behavioral | fail (assertion): 'warnings' | pass | no | E2v |
| `tests/skills/physics_ml/test_training_pipeline.py::TrainClassifierPipelineTests::test_negative_weights_signed_with_net_weight_batch_report` | behavioral | fail (assertion): 0 != 2 | pass | no | E2v |

- `tests/skills/physics_ml/test_audit_metric_layer.py`: 0 tests pass on both (not discriminating)
- `tests/skills/physics_ml/test_calibration.py`: 20 tests pass on both (not discriminating)
- `tests/skills/physics_ml/test_training_pipeline.py`: 20 tests pass on both (not discriminating)


### ML-SMALL: fix `fd637dcc`, parent `f5cc59a7`

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|
| `tests/skills/physics_ml/test_audit_small_corrections.py::SculptingBaselineTests::test_baseline_is_a_quantile_of_at_least_20_resamplings` | behavioral | fail (KeyError): 'n_baseline' | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_small_corrections.py::SmallSeedComparisonTests::test_false_improvement_rate_is_at_most_nominal_with_few_seeds` | behavioral | fail (assertion): 0.25666666666666665 not less than 0.08774917217635375 : 0.25666666666666665 | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_small_corrections.py::SmallSeedComparisonTests::test_method_is_reported_and_a_real_effect_is_found` | behavioral | fail (KeyError): 'method' | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_small_corrections.py::SmallSeedComparisonTests::test_student_t_quantile` | behavioral | fail (AttributeError): module 'compare_model_runs' has no attribute 'student_t_quantile' | pass | no | E2v |
| `tests/skills/physics_ml/test_audit_small_corrections.py::TrainerTests::test_constant_training_feature_is_exit_2` | behavioral | fail (assertion): 0 != 2 : WARNING: training-domain model not fitted (40 training points are too few t... | pass | no | E2v |
| `tests/skills/physics_ml/test_training_pipeline.py::TrainClassifierPipelineTests::test_clean_manifest_summary_shape_and_hash` | behavioral | fail (assertion): + sha256:bfbee527f3511bf8d259964627917ab503e7b2dd2eaf77ed9b8d7c0ee907558e | pass | no | E2v |

- `tests/examples/test_ml_classifier_to_inference.py`: 9 tests pass on both (not discriminating)
- `tests/skills/physics_ml/test_audit_small_corrections.py`: 0 tests pass on both (not discriminating)
- `tests/skills/physics_ml/test_training_pipeline.py`: 20 tests pass on both (not discriminating)

## 0.17.0 release check (2026-10-20, E2 and the CI lock)

Release branch `release/0.17.0` from main `69a675c7` (#163: contracts 3.0.0 retires the deprecated skill names,
section CONTRACTS-3.0.0 below; main CI green). Migration option A is complete: 0.16.0 was the last release that
accepts the old names. The ams02-research companion (1.5.0, requires `>=0.11.0`, profile contracts `>=2.0`) records
no retired name and needs no change.

What changed: version 0.17.0 in both manifests, `pyproject.toml`, the README, the two assets and the profile scripts
that record it; examples regenerated (E2; `bc-propagation-fit` with the CI lock), only version strings and the hashes
that cover them change (`unfolding-coverage` drifted at 1e-14 and was left as committed); the sbottom benchmark
artifacts' `plugin` string edited by hand; theory-profile artifacts regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail, 2 skipped (CLI host checks); 4770 tests, 4651 pass, 0 failures, 119 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 25 pass, 0 fail, 2 skipped; 4770 tests, 4557 pass, 0 failures, 213 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## CONTRACTS-3.0.0 (2026-10-20, E2 and the CI lock, released in 0.17.0)

Branch `feat/retire-skill-aliases` from main `61fec265` (0.16.0). Contracts 3.0.0 retires the deprecated skill names
(migration option A, second step); plugin version unchanged. New tests: `tests/contracts/test_skill_names.py` (schema
enum equals SKILLS; the five hashes are the retired names; each retired name in producer_skill and to_skill is
`skill.unknown_name` pointing to 0.16.x, with and without `--strict-versions`; unknown to_skill is an error; unknown
producer_skill stays a schema error; retired related_skills fails the registry) and
`tests/tools/test_check_retired_names.py` (tree clean; planted name found; history not scanned; case-sensitive).
The alias test (15 tests) and the retired-folder link test are removed. Fixtures, templates, theory-profile artifacts
and examples moved to 3.0.0 (only the version pair and covering hashes change); profile and registry-fixture ranges
`<4.0`.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass (new: `retired_names`), 0 fail, 2 skipped (CLI host checks); 4770 tests, 0 failures, 119 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 25 pass, 0 fail, 2 skipped; 4770 tests, 0 failures, 213 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |
| ams02-research `origin/main` (1.5.0) | no file records a retired name; profile range `>=2.0` admits 3.0.0 |

Not run: a release (no version bump, manifest or tag), host installs, live evals (no routing text changed).

## 0.16.0 release check (2026-10-20, E2 and the CI lock)

Release branch `release/0.16.0` from main `47687ea5` (#157 communication split, contracts 2.13.0; #158 and #161
routing-harness fixes; #159 citation follow-up). Evidence for the split in SPLIT-LIVE-EVAL above. Migration option A
of the restructuring plan: every deprecated skill name still validates with a warning in 0.16.0; 0.17.0 (contracts
3.0.0) removes them. The deprecation message for hep-communication now names 0.16.0. The `docs/agentic-architecture.md`
pointer is removed. The ams02-research companion (1.5.0, requires `>=0.11.0`) names no retired skill outside its
CHANGELOG and needs no change.

What changed: version 0.16.0 in both manifests, `pyproject.toml`, the README, the two assets and the profile
scripts that record it (the assets and theory-profile artifacts also move to contracts 2.13.0, the version this
release ships); examples regenerated (E2; `bc-propagation-fit` with the CI lock), only version strings and the hashes
that cover them change (`unfolding-coverage` drifted at 1e-14 and was left as committed); the sbottom benchmark
artifacts' `plugin` string edited by hand; theory-profile artifacts regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3) | 24 pass, 0 fail, 2 skipped (CLI host checks); 4775 tests, 4656 pass, 0 failures, 119 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 24 pass, 0 fail, 2 skipped; 4775 tests, 4562 pass, 0 failures, 213 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## 0.15.0 release check (2026-10-19, E2 and the CI lock)

Release branch `release/0.15.0` from main `38cb740a` (#141-#154: behavioral evals and the L3 handoff fixes; the
protected-data doc rename. Evidence in `evals/behavior/README.md`: full L3 on main against #150, Sonnet 43 of 48 and
Haiku 39 of 48, no run writing outside its workspace). Contracts stay 2.12.0 (the one schema change since 0.14.1 is
a `$comment` path from the rename).

What changed: version 0.15.0 in both manifests, `pyproject.toml`, the README, the two assets and the profile
scripts that record it; examples regenerated (E2; `bc-propagation-fit` with the CI lock), only version strings and the
hashes that cover them change (`unfolding-coverage` drifted at 1e-14 and was left as committed; its output holds no
version); the sbottom benchmark artifacts' `plugin` string edited by hand; theory-profile artifacts regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3), `88bd43b0` | 24 pass, 0 fail, 2 skipped (CLI host checks); 4307 tests, 4188 pass, 0 failures, 119 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 24 pass, 0 fail, 2 skipped; 4307 tests, 4094 pass, 0 failures, 213 skipped |
| Ruff 0.16.10, mypy 2.4.0 on `core/` and `contracts/` | clean |

## 0.14.1 release check (2026-10-17, E2 and the CI lock)

Release branch `release/0.14.1` from main `61ef58aa` (#139: the hep-detector, hep-theory and hep-computing
descriptions name geomagnetic cutoff backtracing and published-table import; evidence in `evals/routing/README.md`:
the four targeted cases pass, and a 180-case check with repeats against 0.14.0 shows no regression). Contracts stay
2.12.0.

What changed: version 0.14.1 in both manifests, `pyproject.toml`, the README, the two assets and the profile
scripts that record it; examples regenerated (E2; `bc-propagation-fit` with the CI lock), only version strings and the
hashes that cover them change; the sbottom benchmark artifacts' `plugin` string edited by hand; theory-profile
artifacts regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3), `e25f2b15` | 24 pass, 0 fail, 2 skipped (CLI host checks); 4278 tests, 4163 pass, 0 failures, 115 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 24 pass, 0 fail, 2 skipped; 4278 tests, 4046 pass, 0 failures, 232 skipped |

## 0.14.0 release check (2026-10-17, E2 and the CI lock)

Release branch `release/0.14.0` from main `5d918484`, which carries the upgrade plan v1.3 (batches 0a-D, PRs
#131-#136; VALIDATION UPGRADE-0A to UPGRADE-D). Contracts 2.12.0 (vocabulary and optional fields only).

What changed:
- Version 0.14.0 in both manifests, `pyproject.toml` and the README; CHANGELOG "Unreleased" became 0.14.0.
- Contracts 2.12.0 in `contracts/__init__.py` (history entry), `vocab/core.json`, the two pinned tests, the 126
  fixtures, the measurement-spec template, the reading-notes record template and the D5 example response.
- Examples regenerated with the E2 venv; `bc-propagation-fit`, which records NumPy and SciPy versions, with the CI
  lock. Only version strings and the hashes that cover them change. The unfolding-coverage round-off drift was
  reverted. The sbottom benchmark artifacts' `plugin` string was edited by hand. The theory-profile artifacts were
  regenerated.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, E2 (Python 3.13.2, NumPy 2.5.3), `1d18f860` | 24 pass, 0 fail, 2 skipped (CLI host checks); 4278 tests, 4163 pass, 0 failures, 115 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 24 pass, 0 fail, 2 skipped; 4278 tests, 4046 pass, 0 failures, 232 skipped |

The release PR's first CI run failed one test in every job: the E-4 example test compared artifacts byte for byte,
and a tree identical to its release manifest gives `versions.plugin_release` the version and digest instead of
"unreleased". The test now compares those artifacts without the release identity and the hashes that cover it;
`tests/examples` passes in a clean checkout whose identity is 0.14.0 (147 tests, 21 skipped).

Not run: live routing of the cases added in batches A-D (gate G2), the slow tier, the CLI host checks.

## 0.13.1 release check (2026-10-17, E2 and the CI lock)

Release branch `release/0.13.1` from main `a6adf48`. It carries the G-ENFORCE inputs for all suites and the README
updates (#129). Contracts stay 2.11.0.

What changed:
- Version 0.13.1 in both manifests, `pyproject.toml` and the README; CHANGELOG "Unreleased" became 0.13.1.
- Examples regenerated with the E2 venv. Only version strings and the bc-propagation-fit grid hash change.
  - The unfolding-coverage drift was reverted.
  - The flat-direction condition number was kept at its committed value.
- The sbottom benchmark artifacts' `plugin` string was edited by hand.
- The theory-profile artifacts were regenerated.

The companion's namespace check against main `a6adf48` reported no findings.

| Check | Result |
|---|---|
| `run_all_checks.py`, E2 (Python 3.13.2, NumPy 2.5.3) | 25 pass, 0 fail; 3584 tests, 0 failures, 61 skipped |
| Same with the CI lock (Python 3.13.2, NumPy 2.4.6, no torch) | 25 pass, 0 fail; 3584 tests, 0 failures, 170 skipped |

## UPGRADE-0A (2026-10-17, Python 3.13.2 on macOS 26.5 arm64 with the CI lock: NumPy 2.4.6, SciPy 1.17.1, no torch; F-08 also in the E2 venv with PyTorch 2.14.1 CPU)

Upgrade plan v1.3, batch 0a (F-01 to F-15) on branch `upgrade/0a` from main `62f2dd6`. Every item has a regression
test that fails on its parent commit and passes on the fix commit; the new tests were run on the parent with the fix
commit's test files (F-10 with `PYTHONDONTWRITEBYTECODE` unset, F-08 in the E2 venv).

| Item | Parent | Fix |
|---|---|---|
| F-01 grid-fit status | fail (1) | pass |
| F-02 paradigm | fail (5 errors) | pass |
| F-03 Li & Ma labels | fail (1 error) | pass |
| F-04 status enum, CLI contract | fail (import; with `core/status.py` alone: 3 failures listing the noncompliant scripts) | pass |
| F-05 review verdicts | fail (4) | pass |
| F-06 defaults reported | fail (1 failure, 5 errors) | pass |
| F-07 merge rules | fail (2 failures, 2 errors) | pass |
| F-08 hashes (E2, PyTorch) | fail (1 failure, 1 error) | pass |
| F-09 plugin models | fail (1 failure, 3 errors) | pass |
| F-10 bytecode | fail (1) | pass |
| F-11 documentation consistency | fail (8) | pass |
| F-12 skeleton, Simplified Chinese | fail (7) | pass |
| F-13 side effects | fail (3 failures, 3 errors) | pass |
| F-14 levels | fail (2) | pass |
| F-15 documentation claims | fail (2) | pass |

Commands, from the plugin root with `PYTHONDONTWRITEBYTECODE=1`, on the final tree:

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, baseline main `62f2dd6` | 25 pass, 0 fail; 3584 tests, 3414 pass, 0 failures, 170 skipped |
| `run_all_checks.py --no-cli --jobs 6`, batch head | 23 pass, 0 fail, 2 skipped (the `claude` and `codex` CLI checks); 3644 tests, 3472 pass, 0 failures, 172 skipped |
| `check_relocation.py` | pass; 3644 tests, 3466 pass, 0 failures, 178 skipped |
| `measure_entrypoints.py --no-cli` | ok: SKILL.md 7,558-8,145 bytes, 57-71 lines; descriptions 883-1,017 characters |
| `check_layering.py`, `check_routing_static.py` (241 cases), `check_ownership.py` | pass |
| `ruff check core contracts`, `mypy` (CI pins) | pass |

Skipped tests are unverified, not passed: they need PyTorch, pyhf, ROOT, uproot, network access or
`HEP_SLOW_TESTS=1`. Not run: the slow tier, live routing (no description changed), the CLI host checks.

## UPGRADE-D (2026-10-17, Python 3.13.2 on macOS 26.5 arm64 with the CI lock: NumPy 2.4.6, SciPy 1.17.1, no torch)

Upgrade plan v1.3, batch D on branch `upgrade/D` from main `7c57cd1b`: S3, S4, S5, S9, S10, M2, M6, M9, Th2, Th5, Th6,
Th11, C2, C3, C4, C5, C6, Com2, Com4, Com5, D12 and the D13 expansion. Gate decisions (maintainer, 2026-10-17):
S10 (pyunfold, RooUnfold) and D12 (OTSO) as optional adapters with no extras or CI jobs (G5); the six further atlas
experiments at the "passages + overview" read level; sources may be fetched for Th5 and Com4 (G6); C6 ships a
Snakefile template plus a standard-library runner. Each item's tests, run on the parent with the item's test files,
then on the item's commit:

| Item | Parent | Commit |
|---|---|---|
| S3 (`7068e8ee`) | fail (failures=6, errors=4) | pass |
| S4 (`d04bf00a`) | fail (failures=3) | pass |
| S5 (`2cd78747`) | fail (errors=6, skipped=2) | pass (skipped=2) |
| S9 (`829f9fbe`) | fail (errors=9, skipped=2) | pass (skipped=2) |
| S10 (`0f4d7c4c`) | fail (failures=7) | pass |
| Th2 (`42ad7086`) | fail (failures=4, errors=8) | pass |
| Th5 (`98460703`) | fail (failures=2, errors=10) | pass |
| Th6 (`7321e6dc`) | fail (errors=5) | pass |
| Th11 (`4cedacd8`) | fail (failures=4, errors=3) | pass |
| C3 (`76c520c1`) | fail (errors=5) | pass |
| C4 (`b46124ad`) | fail (failures=2, skipped=3) | pass (skipped=3) |
| C5 (`63d31062`) | fail (failures=2, errors=2, skipped=2) | pass (skipped=2) |
| C6 (`98159ba5`) | fail (failures=2, errors=3, skipped=1) | pass (skipped=1) |
| Com4 (`655033a5`) | fail (failures=19, errors=2) | pass |
| Com5 (`01c56589`) | fail (failures=4, errors=1) | pass |
| D12 (`ed36cea3`) | fail (failures=4, errors=7, skipped=1) | pass (skipped=1) |
| M2 (`ecd989f1`) | fail (failures=3, errors=3) | pass |
| M9 (`f79b4c5f`) | fail (failures=3, errors=7, skipped=2) | pass (skipped=2) |
| C2 (`840fd013`) | fail (errors=6) | pass |
| M6 (`19424afc`) | fail (failures=2, errors=3) | pass |
| Com2 (`1b7ae5b0`) | fail (failures=2, errors=1) | pass |
| D13 expansion (hep-detector test) (`25ee70e7`) | pass | pass |
| D13 expansion, atlas profile test (`25ee70e7`) | fail (failures=1) | pass |

S10 ran in a venv with pyunfold 0.5.0; the other rows in the CI lock venv.

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, `8a1da481` | 23 pass, 1 fail (`unittest`: the F-11 README-consistency test still expected one uproot backend; C4 added a second), 2 skipped (CLI host checks); 4278 tests, 1 failure, 232 skipped |
| `check_relocation.py`, `08b9067b` (the test updated) | pass; 4278 tests, 4040 pass, 0 failures, 238 skipped |
| `ruff check core contracts`, `mypy` (CI pins) | pass |
| `measure_entrypoints.py --no-cli` | ok, no warnings: SKILL.md 8,142-10,201 bytes |
| `check_routing_static.py` | ok, 394 cases; `check_ownership.py`, `check_layering.py`, `check_packaging.py` (README: about 2040 files, 22.4 MB), `check_instruction_text.py` pass |
| `reference_inventory.py --check`, `capability_map.py --check` | pass; soft-budget warnings only |
| Default outputs unchanged | S4 without `scale_nuisance` and M6 defaults: every example and existing test result identical; Com2: existing records keep their results (the evidence-linked example changes only its policy version string) |
| Slow tier, run for these items | S5 global p uniform under white noise (300 series), AR(1) null rejects at 0.05 +- 0.02 (400); S9 false-alarm rate within 3 sigma, the declared covariance restores it under AR(1); M9 Rayleigh law under isotropy (KS) |
| Local optional runs | pyunfold 0.5.0 equals core D'Agostini to 1e-9 at 8 and 60 bins, toy coverage 0.68; OTSO 1.3.8 (GPL-3.0, run as a separate program) in a pure dipole: the traced cutoff is at or above Stormer at every latitude and within 0.7% at the equator; uproot 5.7.6 and ROOT 6.38.04 agree on the histogram summary; TeX Live 2026 xelatex builds the Chinese thesis skeleton |

Sources read (2026-10-17, generic User-Agent): PDG 2026 "Dark Matter" and "Cosmic Rays" sections; Baxter et al.
(arXiv:2105.00599, section 3.1, tables 1-2); Duda, Kemper, Gondolo (hep-ph/0608035); Moderski et al.
(astro-ph/0504388, sections 2.1-2.2, appendix A); Duperray et al. (astro-ph/0503544); Kachelriess et al.
(1905.01192); Blasi (1311.7346); the JINST author manual and the PoS author page; OTSO's repository and PyPI record
(license); the detector-atlas sources for Belle II (1011.0352), ALICE (2302.01238), DUNE (2002.02967), JUNO
(2104.02565), XENONnT (2402.10446) and the Pierre Auger Observatory (1502.01323), each claim's passage and the
overview sections in the full text. Marked to-verify: the PLB, NPB, NIM A, SciPost, PTEP and Chinese Physics C author
pages (bot checks or errors), Th5's published reference rate, and the Sullivan attribution of M2's two-disc formula.

Not run: live routing of the 38 new cases (gate G2), the full slow tier, the CLI host checks, RooUnfold (not part of
the local ROOT), snakemake (not installed; the Snakefile is checked for matching rules only), the Parquet path of
C5 (no pyarrow locally; CI's columnar job runs it). The run left `__pycache__` folders from tests that start
`python -I` (the known issue, present on main). Skipped tests are unverified, not passed.

## UPGRADE-C (2026-10-17, Python 3.13.2 on macOS 26.5 arm64 with the CI lock: NumPy 2.4.6, SciPy 1.17.1, no torch)

Upgrade plan v1.3, batch C on branch `upgrade/C` from main `8dab2bb2`: Th1, D4, D3, D2, M4, E-1, Th8, M8, M10, Th4,
Th10, Th12, S2 (with the E-3 projection), S7, S8, ML4, ML3 extensions, S11 extensions, C7, Com6, Com7, D13, D14, E-2,
E-4. Gate decisions (maintainer, 2026-10-17): every named public source may be fetched (G6); effects `survival` and
`fragmentation_feeddown`, spec field `coupled_backgrounds`, artifact statuses `projection` and
`outside-validated-range`, and the profile kind `reference` (G4); hep-detector owns `detector design principles` and
`sourced detector atlas` (G3); no new dependencies for the ML3 extensions (G5); the atlas covers six experiments in
v1. Each item's tests, run on the parent with the item's test files, then on the item's commit (counts in
parentheses):

| Item | Parent | Commit |
|---|---|---|
| Th1 (`151889fb`) | fail (errors=5) | pass |
| D4 (`c3afd32c`) | fail (failures=5, errors=5) | pass |
| D3 (`4c1cb871`) | fail (failures=3, errors=1, skipped=1) | pass (skipped=1) |
| D2 (`11f66a20`) | fail (failures=4, errors=1) | pass |
| M4 (`ccc1eb2a`) | fail (failures=4, errors=47) | pass |
| E-1 (`d4251e05`) | fail (errors=1) | pass |
| M8 (`b92ecb24`) | fail (failures=1, errors=2, skipped=1) | pass (skipped=1) |
| Th8 (`40d8c519`) | fail (failures=4, errors=5, skipped=1) | pass (skipped=1) |
| Th4 (`69f359f5`) | fail (errors=1) | pass |
| Th10 (`c0b6b6d8`) | fail (errors=4) | pass |
| Th12 (`87421c11`) | fail (errors=4) | pass |
| M10 (`c4d801c4`) | fail (errors=4) | pass |
| ML4 (`1a844ba0`) | fail (failures=4, errors=2, skipped=1) | pass (skipped=1) |
| ML3 extensions (`3398e5c3`) | fail (failures=8, errors=2, skipped=1) | pass (skipped=1) |
| C7 (`3b3dca7d`) | fail (failures=6, errors=1, skipped=2) | pass (skipped=2) |
| Com6 (`ac1eb235`) | fail (failures=2, errors=1) | pass |
| Com7 (`fe9839a2`) | fail (failures=9, errors=3) | pass |
| E-4 (`0cedf447`) | fail (errors=1) | pass (skipped=2) |
| D14 (`6721da68`) | fail (failures=8, errors=4) | pass |
| D13 (`1f95aab2`) | fail (failures=1, errors=3) | pass |
| D13 (`cbcf6c34`) | fail (failures=10, errors=2) | pass |
| S2 (`f598f1ae`) | fail (failures=7, errors=9) | pass |
| S7 (`ca23333b`) | fail (errors=1) | pass (skipped=2) |
| S8 (`a73d421e`) | fail (failures=5, errors=8) | pass |
| S11 extensions (`09237aee`), with local ROOT 6.38.04 | fail (3, the parent script; recorded by the track) | pass |
| E-2 (`8c671849`) | fail (errors=1) | pass |

ML3 extensions ran in a venv with xgboost 3.4.1 and scikit-learn 1.9.1; the other rows in the CI lock venv. The
atlas profile's own ledger test passed before D13 too: `core/evidence/ledger.py` already accepted the extra `atlas`
claim field (the work order's "Inferred" note, now confirmed).

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, `8c671849` | 23 pass, 1 fail (`ams_optional`: two S2/S7 tests read an example's committed output, which that check's copy omits), 2 skipped (CLI host checks); 4118 tests, 3903 pass, 0 failures, 215 skipped |
| `check_ams_optional.py`, `3b80cc0d` (tests read a contracts fixture) | pass |
| `check_relocation.py`, `3b80cc0d` | pass; 4118 tests, 3897 pass, 0 failures, 221 skipped |
| `ruff check core contracts`, `mypy` (CI pins) | pass |
| `measure_entrypoints.py --no-cli` | ok, no warnings: SKILL.md 8,142-9,997 bytes; registry 2,517 of 3,072 bytes |
| SKILL.md plus entry reference | hep-measurement and hep-statistics within 25,600 bytes after wording-only trims |
| `check_routing_static.py` | ok, 356 cases; `check_ownership.py` pass; `check_layering.py` ok; `check_instruction_text.py` 0 findings |
| `reference_inventory.py --check` | pass; soft-budget warnings only |
| Examples | E-1: B/C pull means within 0.07 of zero, widths 0.95-1.02 over 400 toys; the fixed-subtraction control biased and flagged. E-2: ratio shift equals the difference of the signed shifts to 2e-16; the injected 2e-4 recovered as 2.063e-4 +- 1.0e-5. E-3 projection: projected / toy uncertainty 0.949-1.043 at twice the exposure. E-4: macros, table and HEPData values identical; draft build passes, final build stops on the watermark (pdflatex, local) |
| Local optional runs | pyhf 0.7.6: a 72-bin model under the cap override agrees with pyhf asymptotic CLs within 1%. ROOT 6.38.04 (Python 3.14.8, `HEP_ROOT_PYTHON`): S11 crosscheck (MLE 3e-7, interval 3e-5, CLs 0.3%), pulls N(0,1), AsymptoticError covers 0.71 vs naive Hessian 0.46 (slow tier); C7 PyROOT and uproot 5.7.6 agree |
| Slow tier, run for these items | D3 coverage within +-0.05 at rates 1e-3, 1e-2, 1e-1 (200 toys); M8 pull widths 0.85-1.15 (400 toys); S8 envelope coverage and validation power (400 toys); ML4 p-value uniformity |

Sources read (2026-10-17, generic User-Agent): PDG 2026 reviews (neutrino mixing sections 14.3-14.5; QCD 9.1.1; CKM
introduction; Monte Carlo numbering; dark matter 27.6.3; neutrino cross sections, passages), PDG RPP 2025
Introduction section 5.3 (rounding), van Ritbergen, Vermaseren and Larin (hep-ph/9701390, Eqs. 4, 11, 12), NUBASE2020
section 2.3, Genolini et al. 2018 and Evoli et al. 2018 (full text), the PDG atomic and nuclear properties table, the
ROOT 6.40 class reference (14 pages), root.cern TH1/TEfficiency/RooWorkspace references, 6.38 release notes and
install page, the PyPI record of `root`, APS PRL/PRD and JHEP author guidelines. The detector atlas: the ATLAS and
CMS JINST detector papers (2008), LHCb Upgrade I (arXiv:2305.10515), IceCube instrumentation (arXiv:1612.05093),
Super-Kamiokande calibration (arXiv:1307.0162), Fermi-LAT instrument (arXiv:0902.1089): each claim's passage and the
overview sections were read in the full text; none of these papers was read cover to cover, and each source record
says so. Not read: the EPJC author page (did not load).

Not run: live routing of the 44 new cases (gate G2), the full slow tier, the CLI host checks, ONNX and TMVA export
(their packages are not installed; only the missing-package path is tested). The run left `__pycache__` folders
from tests that start `python -I` (the known issue, present on main). Skipped tests are unverified, not passed.

## UPGRADE-B (2026-10-17, Python 3.13.2 on macOS 26.5 arm64 with the CI lock: NumPy 2.4.6, SciPy 1.17.1, no torch)

Upgrade plan v1.3, batch B on branch `upgrade/B` from main `0687ad2`: C1, M1, D9, D5, D10, D11, M7, D8, M3, D6, S1,
S6, ML1, ML3, S11 and the first part of E-3. Gate decisions (maintainer, 2026-10-17): M1's effect `cutoff_transmission`
and composition `exposure_acceptance_livetime_transmission` (G4); M3's `eras` field (G4); the optional extra `bdt`
with xgboost and scikit-learn, tested in a recorded local run without a CI job (G5); D6 may read arXiv:2603.25085, and
S11 may use a local ROOT. Each item's tests, run on the parent with the item's test files, then on the item's commit:

| Item | Parent | Commit |
|---|---|---|
| C1 (`a57e22cf`) | fail (4 failures, 3 errors) | pass |
| M1 (`97d6ec54`) | fail (8 failures, 14 errors) | pass |
| D9 (`b25efa67`) | fail (5 failures, 5 errors) | pass |
| D5 (`c98cc355`) | fail (3 failures, 1 error) | pass |
| D10 (`f7d5722d`) | fail (11) | pass |
| D11 (`0d506417`) | fail (5 failures, 1 error) | pass |
| D8 (`fe6d9d65`) | fail (7) | pass |
| M7 (`36140fee`) | fail (9 failures, 8 errors) | pass |
| M3 (`fe71ebcf`) | fail (9 failures, 44 errors) | pass |
| D6 (`1d03565d`) | fail (2) | pass |
| S1 (`bb2e0465`) | fail (6 failures, 7 errors) | pass (1 skipped: slow tier) |
| S6 (`e2cb73b9`) | fail (3) | pass |
| ML1 (`6c1221a7`) | fail (2) | pass |
| ML3 (`f3e0ff6d`), in a venv with the backends | fail (16 failures, 2 errors) | pass |
| S11 (`23c707c9`), CI lock venv | fail (3 failures, 1 error) | pass (7 skipped: PyROOT) |
| E-3 (`9d998742`) | fail (1 error) | pass |

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, `83f5b982` | 23 pass, 0 fail, 2 skipped (the `claude` and `codex` CLI checks); 3914 tests, 3718 pass, 0 failures, 196 skipped |
| `check_relocation.py`, `83f5b982` | pass; 3914 tests, 3712 pass, 0 failures, 202 skipped |
| `ruff check core contracts`, `mypy` (CI pins) | pass |
| `measure_entrypoints.py --no-cli` | ok, no warnings |
| SKILL.md plus entry reference | hep-measurement 25,599 bytes (limit 25,600) |
| `check_routing_static.py` | ok, 312 cases; `check_ownership.py` pass; `check_layering.py` ok |
| `reference_inventory.py --check` | pass; 5 soft-budget warnings (references above 24 KB) |
| ML3 in a scratch venv (Python 3.13.2, xgboost 3.4.1, scikit-learn 1.9.1, NumPy 2.4.6, SciPy 1.17.1) | 18 tests pass; skipped, not failed, without the backends |
| S11 with Homebrew ROOT 6.38.04 under Python 3.14.8 (`HEP_ROOT_PYTHON`) | 11 tests pass; ROOT does not load under the local Python 3.13 interpreters, so CI's optional ROOT job is the recurring check |
| S1 slow tier (`HEP_SLOW_TESTS=1`): p-values uniform under the null, 20,000 toys | pass |
| E-3 `examples/multi-era-fit/` | every criterion passes: joint-fit coverage of the +-1 sigma intervals 0.689 over 1,000 seeded toys (0.68 +- 0.03); S1 p 0.11 without a difference, a 5% offset in one era caught; partial + merge = single run; a period split across files counted once; about 5 s |
| D11 on D7's "added layer" data (AC-B) | the era boundary is found at period 6 |

Sources read: arXiv:2603.25085 (abstract only, D6); ROOT master `tmva/tmva/src/MethodBDT.cxx` for the TMVA option
table (ML3), fetched 2026-10-17 with a generic User-Agent.

Gate G2 runs (recorded under the repository's `evals/routing/`, Claude Code 2.1.302, claude-sonnet-5-5): repeats of
the five batch-0b misses ($0.81) and a hep-theory description experiment for `j06` (41/49 on the fixed tree and on
main, `j06` 0/3 vs 1/3; not merged, $11.33). Live routing of the 30 batch B cases was not run.

Not run: the slow tier except S1's test, the CLI host checks, a CI job for xgboost and scikit-learn. The run left
`__pycache__` folders from tests that start `python -I` (the known issue, present on main). Skipped tests are
unverified, not passed.

## UPGRADE-A (2026-10-17, Python 3.13.2 on macOS 26.5 arm64 with the CI lock: NumPy 2.4.6, SciPy 1.17.1, no torch)

Upgrade plan v1.3, batch A on branch `upgrade/A` from main `b1f4d8e`: Th9 (with one sci-fix commit), Th7, D7, D1,
M5, Th3, ML2, Com1, Com3, X3, X1, X2. Gate decisions (maintainer, 2026-10-17): Th9 sources fetched (G6) and the
optional `pdg` extra (G5); PDG subset of about 30 particles; M5's `scaling` field (G4); D7 under
`skills/hep-detector/scripts/`; analysis-check inputs written only on request. Each item's tests, run on the parent
with the item's test files, then on the item's commit:

| Item | Parent | Commit |
|---|---|---|
| Th9 (`84c0a68`) | fail (7 failures, 8 errors) | pass (1 skipped: the `pdg` cross-check) |
| Th9 sci-fix (`2391008`) | fail (2) | pass |
| Th7 (`16e1690`) | fail (6 failures, 5 errors) | pass |
| D7 (`a1a1400`) | fail (1 error) | pass (1 skipped: slow tier) |
| D1 (`bb4e145`) | fail (10) | pass |
| M5 (`7cd0b7e`) | fail (2) | pass |
| Th3 (`505eb43`) | fail (3) | pass |
| ML2 (`03d2387`) | fail (2 failures, 9 errors) | pass |
| Com1 (`e5427f1`) | fail (6) | pass |
| Com3 (`064f60f`) | fail (13 failures, 3 errors) | pass |
| X3 (`cc72047`) | fail (1 error) | pass |
| X1 (`12b46ca`) | fail (1 failure, 4 errors) | pass |
| X2 (`2697017`) | fail (4 failures, 3 errors) | pass |

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 6`, `17979a6` | 23 pass, 0 fail, 2 skipped (the `claude` and `codex` CLI checks); 3783 tests, 3609 pass, 0 failures, 174 skipped |
| `check_relocation.py`, `17979a6` | pass; 3783 tests, 3603 pass, 0 failures, 180 skipped |
| `ruff check core contracts`, `mypy` (CI pins) | pass |
| `measure_entrypoints.py --no-cli` | ok, no warnings: SKILL.md 7,943-9,509 bytes |
| `check_routing_static.py` | ok, 282 cases, every domain outside v1 has a limited-support case; `check_ownership.py` pass; `check_layering.py` ok |
| `reference_inventory.py --check` | pass; no cross-skill overlap; 5 soft-budget warnings (references above 24 KB) |
| `tests/core/test_constants.py` with `pdg` 2026.0 installed (scratch venv) | pass, 16 tests: the 31 bundled masses equal the package's summary-table text |
| `tests/examples` | pass (no committed example output changed) |

Sources read for Th9 (2026-10-17, generic User-Agent): the NIST CODATA 2022 listing (allascii.txt, full table), the
`pdg` 2026.0 database (summary values of 32 particles), the AMDC files mass_1.mas20 and nubase_4.mas20 (40 nuclides).
Not read: the NUBASE2020 year length, so year-unit half-lives are not converted to seconds (to-verify). Th3 read the
abstract page of arXiv:2606.15259 only.

Gate G2 runs on the batch 0b tree (main `b1f4d8e`, Claude Code 2.1.302, claude-sonnet-5-5; recorded under the
repository's `evals/`): full routing 249/259 ($21.15), with four cases that passed in the 2.1.293 baseline missing
now (`co-neighbor-1`, `j06`, `rc-t3-neg`: hep-theory answered without a skill; `underspec-1`: a skill instead of a
question) and B-04's 18 cases 17/18 (`th-const-1`); the communication evaluation loaded hep-communication in 10 of 11
cases ($0.73). These are single runs.

Not run: live routing of the 23 batch A cases (gate G2), the slow tier, the CLI host checks. The run left
`__pycache__` folders from tests that start `python -I` (the known issue, present on main). Skipped tests are
unverified, not passed.

## UPGRADE-0B (2026-10-17, Python 3.13.2 on macOS 26.5 arm64 with the CI lock: NumPy 2.4.6, SciPy 1.17.1, no torch)

Upgrade plan v1.3, batch 0b (B-01 to B-05) on branch `upgrade/0b` from main `b02cd98`, with the validator-label
follow-up of F-15. Each item's tests, run on the parent with the item's test files, then on the item's commit:

| Item | Parent | Commit |
|---|---|---|
| Validator labels (`e1623b1`) | fail (2 errors) | pass |
| B-01 budget (`feb19ee`) | fail (5 failures, 3 errors) | pass |
| B-05 reference soft budget (`2251348`) | fail (1 failure, 3 errors) | pass |
| B-02 routing tables (`c16ff64`) | fail (8 errors) | pass |
| B-03 entry references (`485e96c`) | fail (5) | pass |

| Check | Result |
|---|---|
| `run_all_checks.py --no-cli --jobs 4`, baseline main `b02cd98` | 23 pass, 0 fail, 2 skipped; 3645 tests, 3473 pass, 0 failures, 172 skipped |
| `run_all_checks.py --no-cli --jobs 6`, `c2b743d` | 23 pass, 0 fail, 2 skipped (the `claude` and `codex` CLI checks); 3660 tests, 3488 pass, 0 failures, 172 skipped |
| `check_relocation.py`, `c2b743d` | pass; 3660 tests, 3482 pass, 0 failures, 178 skipped |
| `measure_entrypoints.py --no-cli` | ok, no warnings: SKILL.md 7,895-9,322 bytes; descriptions 883-1,017 characters |
| SKILL.md plus entry reference | 14,895-25,321 bytes (limit 25,600) |
| `check_routing_static.py` | ok, 259 cases; `check_ownership.py` pass; `check_layering.py` ok |
| `reference_inventory.py --check` | pass; 5 soft-budget warnings (references above 24 KB; no routing part above 4 KB) |

Not run: live routing for the six new descriptions, the routing tables and the 18 new cases (gate G2; estimate
$19.90 for all 259 cases, $1.36 for the 18 new ones, from the 2026-10-15 run's cost per turn), the communication
behavioral evaluation, the slow tier, the CLI host checks. Skipped tests are unverified, not passed.

## CRPROP-ACCEPTANCE (2026-10-26, E2; integration branch `worktree-crprop-integration` from `main` 8fcbb826, 0.42.0)

P0 of the cr-propagation r4 workflow (`docs/dev/cr-propagation/workflow-r4.md` §5). The frozen acceptance list
`docs/dev/cr-propagation/acceptance.json` (86 entries: ALL, A1–A4, B1–B3, providers folded into B1, D1, D2 and E2,
C1, C2, C2U, D1–D3, E1–E2, F1, F3, ENV, WF) is generated from r3's Acceptance Criteria before any work package
starts; this is R9's "criteria first" for the whole campaign. From here to H1, entries may only be added (stricter);
loosening or deleting one waits for H1 (`workflow_check.py acceptance`).

| Item | Result | Evidence |
|---|---|---|
| Frozen acceptance list | sha256 `f5b0dbe61aca360e364f0df52a41bc00f27f2cfaf0ad2808e43bc4f3480b813e` | `docs/dev/cr-propagation/acceptance.json` |
| Workflow manifest (WF-1) | `workflow_check.py dag`: ok, 21 work packages, 9 capabilities, acyclic, waves ordered; derived at H0 (decision D0), sha256 `017bb108bf5dac1dc197675fdfdf665cbe32c952259f808611e6990b75f3e208` | `docs/dev/cr-propagation/workflow.json` |
| Decision record | D0–D12 answered 2026-10-26 | `docs/dev/cr-propagation/decisions.md` |
| Task documents | `lint_task.py`: 0 errors for `workflow-r4.md`, `workflow-r4.zh.md`, `cr-propagation-plan.md`, `cr-propagation-plan.zh.md` (planned paths give warnings) | P0 run |
| Language versions | six differences reported (r4 §3 D2 vs D5; r4 Deliverables; r4 Open Questions on review.py; r3 line 7; r3 line 64 §0.4 vs §0.5; r3 line 257 status string), not chosen | `decisions.md` |
| P0 rework, round 1 (verifier REWORK, 5 problems) | `workflow.json` sha256 `73c6c8a3e6d5e1f23c6fe501973c158fb78f7d77bd65d0a741390c77d93c1d51` (RC owns WF-2..WF-10, criticality per r4 §8, F1 fallback mode, F2/E1/RC sources; checker and manifest orchestrator-only); `workflow_check.py` counts waivers and takes `--plugin-root`; D3 adds F1's HEPData/CRDB queries; two more language differences recorded; `acceptance.json` unchanged | `decisions.md`, `workflow.json` |
| P0 rework, round 2 (verifier REWORK) | `workflow.json` sha256 `c18ae1bf834d4760af6327a38f451a571894e22c033b33966b74b30d36851dcb`, `workflow_check.py dag` ok (21 work packages, 9 capabilities): `common_files` adds the skill and adapter README counts and SKILL.md Resources rows that `check_wiring.py` requires (r3 §0.5); narrower D1 and C2 file lists; F2 hard-depends on E2 (r3 Gate E); every non-r3/r4 value carries a source. Checker: duplicate acceptance ids rejected, frozen list read from the trusted integration history, `fallback_mode` deps and capabilities and soft-dependency waves checked. Three more language differences recorded. `acceptance.json` unchanged |  `decisions.md`, `workflow.json`, `workflow_check.py` |

Derived entries (not in r3): ENV-1 to ENV-3 (from r4 §3) and C2U-1, C2U-2 (from r3 §C2's USINE case, split by r4 §6).
ALL-2 is replaced by the P0 freeze. **Not verified here:** r3 Q10's formal independent review with `review.py` is not
run at P0; it moves to before H1 (r4 Open Questions).

## CRPROP-ENV — 2026-10-26 (environment E-crprop)

Work package ENV of the cr-propagation r4 workflow (`docs/dev/cr-propagation/workflow-r4.md` §3): capability probe
and external builds. **Environment field (r3 §0.3, base exception D10):** worktree `.claude/worktrees/crprop-env`,
branch `worktree-crprop-env`, base = integration HEAD ef37d970 (not `main`; decision D10); toplevel checked, status
clean at start, prerequisite P0 (ef37d970) an ancestor of HEAD. No plugin code changed.

| Item | Result | Evidence |
|---|---|---|
| Capability file (ENV-1) | all 9 capabilities of `workflow.json`: `repo` present, `net-github` present (DRAGON2 HEAD cd588707), `net-sources` absent, `net-data` partial (HEPData HTTP 200; CRDB times out after 25 s), `pkg-install` present (Homebrew 7.0.8, venv creation), `batch` partial (local only, D6), `env-dragon2` present, `env-usine` absent, `env-galprop` absent | `$CRPROP_OUT/capabilities.json` (outside the repo) |
| DRAGON2 build check | not rebuilt: source commit cd588707 (clean); sha256 of `install/bin/DRAGON` and the three libraries equal the 2026-10-15 build record | `tests/adapters/fixtures/cr_propagation/dragon2-build.computational-run.json` |
| DRAGON2 live rerun | `HEP_DRAGON2_LIVE_TEST=1 python -m unittest tests.adapters.test_cr_propagation`: 22 tests OK in 100.1 s (E2 venv) and 100.3 s (miniconda Python 3.13.2, numpy 2.4.4); `LiveDragon2` ran, not skipped: X1 rerun equals the recorded output at relative 1e-6 | `$CRPROP_OUT/env/live/` |
| Records (ENV-2) | computational-run `dragon2-verify.computational-run.json` (contracts 3.13.0, `validate.py` ok, no findings) and environment manifest `dragon2.environment.json` (`environment_manifest.py record`), de-identified (`<TOOL_HOME>`, `<VENV>`, `<RUN_DIR>`) | `tests/adapters/fixtures/cr_propagation/env/` |
| Environment label (ENV-3) | E-crprop registered in the Environments table with compiler, ROOT, GSL, CFITSIO and DRAGON2 versions | this file |
| Checks (ALL-3) | `run_all_checks.py`: exit 0. `check_relocation.py`: 31 pass, 1 fail, 1 skip; the failing check is two `tests.adapters.test_geant4` partition tests (`test_partition_summaries_merge_without_reading_a_csv`, `test_partition_merge_equals_a_single_run_and_refuses_nothing_twice`), whose worker command breaks on a plugin path with spaces (`can't open file '.../reloc'`); the same two tests fail identically from a copy of the base ef37d970 under a path with spaces, so the failure predates ENV and is not fixed here | `$CRPROP_OUT/env/reloc`, `$CRPROP_OUT/env/acceptance/ALL-3.spaces-path.*.log` |
| USINE, GALPROP | absent: `$HOME/hep-work/crprop-sources/` is empty; nothing downloaded or built (D4, D5). Fallbacks of `workflow.json`: USINE absent is critical (B1, B3, C2U wait; F1 takes D8); GALPROP absent makes D2 unavailable | `capabilities.json` |

**Not run:** the curl probes of `lpsc.in2p3.fr/usine`, `gitlab.in2p3.fr` and `galprop.stanford.edu` (outside the
consented network hosts of the campaign's common assignment; decision D2 records that they time out from the
sandbox). The DRAGON2 status is unvalidated: the live rerun shows reproducibility of the recorded X1 output, not
physical validity.

## CRPROP-A2 — 2026-10-26 (environment E2)

Work package A2 of the cr-propagation r4 campaign (r3 §A2, §5.4): the optional theory-spec `transport` block and
object-form `degenerate_directions` entries, contracts `CV-CRPROP` = 3.14.0 (unreleased minor) gated by
`validate.CRPROP_FROM`.

Environment: E2 (macOS arm64, Python 3.13.2). Base exception D10: base is the integration HEAD `ef37d970` (P0), not
`main`. r3 §0.3 checks at start: `git rev-parse --show-toplevel` = `.claude/worktrees/crprop-a2` (this worktree);
`git branch --show-current` = `worktree-crprop-a2`; `git status` clean; prerequisite P0 `ef37d970` is an ancestor of
HEAD (`git merge-base --is-ancestor` ok); `origin/main` is still 8fcbb826 (0.42.0), so no new CHANGELOG entries to
recheck; the cited lines were rechecked on the base (`_blank` at `contracts/validate.py` 1239, the string-only
degeneracy reader at `covariance_fit.py` 1110, the grid-only gate at 1025).

Acceptance criteria (frozen in `docs/dev/cr-propagation/acceptance.json`, written here before the change; no
numerical tolerance applies to A2):

| ID | Criterion | Pass condition |
|---|---|---|
| A2-1 | Every existing theory-spec in `contracts/fixtures` and `examples/` validates with the same result before and after | identical `ok` flag and identical sorted findings (severity, path, code, message), default and `--strict`, for every file |
| A2-2 | Each of the three new error codes is triggered by one negative fixture | `theory.degeneracy_evidence_missing`, `theory.degeneracy_range_missing`, `theory.degeneracy_evidence_unknown` each in `contracts/fixtures/artifacts/invalid/` |
| A2-3 | A list holding only objects does not trigger `theory.degeneracy_missing` | unit test in `tests/contracts` |
| A2-4 | `tabulated-grid` gives the same result for an object entry as for the equivalent string | identical fit output (apart from the echoed spec) in `tests.skills.hep_statistics.test_grid_fit` |
| A2-5 | The new rules apply from `CRPROP_FROM` only | a 3.13.0 artifact gets none of the three codes (default mode); a 3.14.0 artifact gets them |

Results (after the change; raw output in `$CRPROP_OUT/a2/`, `CRPROP_OUT` = the campaign's run-output folder):

A2-1, every theory-spec under `contracts/fixtures`, `examples/` and `profiles/` (23 files) validated before the
change (base `ef37d970`) and after it, default and `--strict` (`a2_baseline.py`, `theory_specs_before.json`,
`theory_specs_after.json`): ok flag and sorted findings (severity, path, code, message) identical for all 23. On
`worktree-crprop-a2-bump` (contracts 3.14.0) the findings are identical too; only the `contract_version` of the
qed-prediction example and the six profile theory-specs changes (`theory_specs_after_bump.json`).

| File | contract_version | default / strict | default codes | after |
|---|---|---|---|---|
| `contracts/fixtures/artifacts/invalid/envelope_missing_status.json` | 1.0.0 | errors / errors | schema.required | identical |
| `contracts/fixtures/artifacts/invalid/theory_experiment_binding.json` | 1.0.0 | errors / errors | theory.experiment_binding | identical |
| `contracts/fixtures/artifacts/invalid/theory_experiment_field.json` | 1.0.0 | errors / errors | schema.additional, theory.experiment_field | identical |
| `contracts/fixtures/artifacts/invalid/theory_v26_check_result_vocab.json` | 2.6.0 | errors / errors | theory.check_result_vocab | identical |
| `contracts/fixtures/artifacts/invalid/theory_v26_limit_missing.json` | 2.6.0 | errors / errors | theory.limit_missing | identical |
| `contracts/fixtures/artifacts/invalid/theory_v26_order_missing.json` | 2.6.0 | errors / errors | theory.order_missing | identical |
| `contracts/fixtures/artifacts/invalid/theory_v26_propagation_no_degeneracy.json` | 2.6.0 | errors / errors | theory.degeneracy_missing | identical |
| `contracts/fixtures/artifacts/invalid/theory_v26_unchecked_formal_proof.json` | 2.6.0 | errors / errors | theory.unchecked_strong_status | identical |
| `contracts/fixtures/artifacts/invalid/theory_v26_validity_empty.json` | 2.6.0 | errors / errors | theory.validity_empty | identical |
| `contracts/fixtures/artifacts/valid/theory_spec.json` | 1.0.0 | ok / ok | - | identical |
| `contracts/fixtures/artifacts/valid/theory_spec_v26.json` | 2.6.0 | ok / ok | - | identical |
| `contracts/fixtures/artifacts/valid/theory_spec_v26_analytic_checked.json` | 2.6.0 | ok / ok | - | identical |
| `contracts/fixtures/artifacts/valid/theory_spec_v26_asymptotic.json` | 2.6.0 | ok / ok | - | identical |
| `contracts/fixtures/artifacts/valid/theory_spec_v26_inapplicable_listed.json` | 2.6.0 | ok / ok | - | identical |
| `contracts/fixtures/artifacts/valid/theory_spec_v26_propagation.json` | 2.6.0 | ok / ok | - | identical |
| `contracts/fixtures/artifacts/warning/theory_v26_conventions_incomplete.json` | 2.6.0 | ok / ok | theory.conventions_incomplete | identical |
| `examples/qed-prediction/output/artifacts/theory_spec.json` | 3.13.0 | ok / ok | - | identical |
| `profiles/theory/cr-secondary-antiprotons/derivations/theory-spec.json` | 3.13.0 | ok / ok | - | identical |
| `profiles/theory/cr-secondary-ratio/derivations/theory-spec.json` | 3.13.0 | ok / ok | - | identical |
| `profiles/theory/dis-parton-model/derivations/theory-spec.json` | 3.13.0 | ok / ok | - | identical |
| `profiles/theory/drell-yan-lo/derivations/theory-spec.json` | 3.13.0 | ok / ok | - | identical |
| `profiles/theory/heliospheric-modulation/derivations/theory-spec.json` | 3.13.0 | ok / ok | - | identical |
| `profiles/theory/tmd-gaussian-lo/derivations/theory-spec.json` | 3.13.0 | ok / ok | - | identical |

| ID | Result | Evidence |
|---|---|---|
| A2-1 | pass | table above; `python3 -m unittest discover -s tests/contracts -t .`: 1213 tests OK (3 skipped); `test_crprop_degeneracy.CommittedSpecsUnchanged` |
| A2-2 | pass | `contracts/fixtures/artifacts/invalid/theory_crprop_degeneracy_{evidence_missing,range_missing,evidence_unknown}.json`, each giving exactly its code (`NegativeFixtures`) |
| A2-3 | pass | `ObjectEntries.test_object_only_list_is_not_blank` (at 3.14.0 and 2.6.0); fixture `valid/theory_spec_crprop_object_degeneracy.json` |
| A2-4 | pass | `python3 -m unittest tests.skills.hep_statistics.test_grid_fit`: 18 tests OK; `test_object_entry_gives_the_result_of_the_equivalent_string` (identical JSON output, with and without `combinations`) |
| A2-5 | pass | `Gating`: at 3.13.0, 3.0.0 and 2.6.0 none of the three codes by default, all under `--strict`; native at `CRPROP_FROM` = 3.14.0 |

| Check | Result |
|---|---|
| `run_all_checks.py --out $CRPROP_OUT/a2/checks` | 33 pass, 0 fail, 0 skip; unittest 5745 run, 0 failures, 206 skipped |
| `check_relocation.py` | fails 2 tests, `tests.adapters.test_geant4` partition tests (worker path with spaces is split: `can't open file '.../hep'`); the same 2 fail on the base `ef37d970` in a copy under a path with spaces (`reloc-base-geant4.txt`): not caused by A2 |
| `check_naming.py`; `workflow_check.py gaps` | pass; no new known gap |
| `check_wiring.py --since ef37d970`; `check_layering.py`; `check_packaging.py` | pass |
| `workflow_check.py acceptance` | ok, frozen sha256 unchanged |
| `workflow_check.py diff --work-package A2` | fail on one path: `tests/skills/hep_statistics/test_grid_fit.py`, where the frozen A2-4 command and the assignment place the A2-4 test; workflow.json's A2 `files` omit it |

Version bump: `CONTRACTS_VERSION` stays 3.13.0 on `worktree-crprop-a2`; `CRPROP_FROM` = 3.14.0, so a 3.14.0 artifact
reads with the newer-minor warning until the bump. The bump follows the 3.13.0 precedent (`ac3950b4`) and is one
commit on `worktree-crprop-a2-bump` (on top of this branch). Besides the in-scope files (`contracts/__init__.py`,
`vocab/core.json`, fixtures, pinned tests) it regenerates 166 example outputs, 19 theory-profile files (artifacts
and `make_artifacts.py` constants) and 3 skill templates, all outside A2's workflow.json list. Examples were regenerated
with the E2 venv. `bc-propagation-fit` and `unfolding-coverage` carry no contract version; their numpy/scipy drift
was reverted. On an export of the bump branch: `tests/contracts` 1213 tests OK (3 skipped), `tests/examples` 176 tests OK (22
skipped); the full `run_all_checks` was not run on the bump branch.

## CRPROP-A1 — 2026-10-26 (environment E2)

Work package A1 of the cr-propagation r4 campaign (r3 §A1, §5.5): convention conversion
(`skills/hep-theory/scripts/transport_conventions.py`) and the harmonized configuration `harmonized-v1`.

Environment: E2, macOS 26.5 arm64, Python 3.13.2, standard library only. r3 §0.3 checks, run 2026-10-26 before the
first edit: `git rev-parse --show-toplevel` = `.claude/worktrees/crprop-a1` (this worktree); `git branch
--show-current` = `worktree-crprop-a1`; `git status` clean; prerequisite P0 `ef37d970` is an ancestor of HEAD
(`git merge-base --is-ancestor` exit 0). Base exception (decision D10): the base is the integration HEAD `ef37d970`,
not `origin/main`; the line numbers r3 cites for A1 were rechecked on this base (the convention table of
`cosmic-ray-phenomenology.md` is at lines 45-49, three rows).

Acceptance criteria and tolerances, written before any implementation (R9; frozen in
`docs/dev/cr-propagation/acceptance.json`, never loosened):

| ID | Criterion | Tolerance |
|---|---|---|
| A1-1 | Pure power-law round trips (every pair of conventions, there and back) | relative error < 1e-12 |
| A1-2 | 1 kpc^2/Myr in cm^2/s, from the IAU parsec (648000/pi au, au = 149597870700 m) and the Julian year (365.25 d) | 3.0172e29 within relative 1e-4 |
| A1-3 | The tests parse the convention table of `cosmic-ray-phenomenology.md` row by row; a parse failure fails the test; no value copied by hand | parse of every row |
| A1-4 | With a break, or different smoothness conventions, the status is `approximate` or `not-convertible`; K0 <-> K10 with a break is never `exact` | status only |
| A1-5 | V_A between thin disc and whole halo | status `approximate` only |
| A1-6 | `harmonized-v1.json` carries every §5.5 row and the §5.4 `transport` structure; schema validation against `ext_theory_spec.transport` after A2 merges | every row present |

Results (2026-10-26, E2, HEAD `0a406fd2` for the full checks; outputs under `$CRPROP_OUT/a1/`):

| ID | Result | Evidence |
|---|---|---|
| A1-1 | pass: every pure power-law pair (eta 1: galprop, usine-k0, usine-k10, canonical; eta 0: dragon2 and the same; eta 0.7: usine and canonical) is `exact` and there-and-back within 1e-12 | `PowerLawRoundTrips` |
| A1-2 | pass: 1 kpc^2/Myr = 3.01720e29 cm^2/s from the IAU parsec and Julian year, within 1e-4 of 3.0172e29; the page's 3.017e29 within half its last digit | `Units`, `ConventionTable.test_page_unit_line_matches_derived_unit` |
| A1-3 | pass: the three table rows (plus K10 from "K10 = K0 10^delta") are parsed for eta, reference rigidity and unit and matched to the module; a row that does not parse fails (`test_parse_failure_fails`) | `ConventionTable` |
| A1-4 | pass: with a low break, K0 <-> K10 and K0 -> GALPROP are `approximate` with a bound >= abs(f(R0') - 1); different or unknown smoothness conventions and non-low breaks are `not-convertible`; never `exact` | `Breaks` |
| A1-5 | pass: V_A thin disc <-> whole halo is `approximate` (factor sqrt(L/h), no bound derived); same zone `exact` | `Reacceleration` |
| A1-6 | pass (structure): every §5.5 row present, §5.4 keys at both levels; schema validation against `ext_theory_spec.transport` skipped until A2 merges (the test runs it automatically once the property exists) | `Harmonized` |

Checks: `run_all_checks.py` 33 pass, 0 fail; `check_relocation.py` fails 2 tests in `tests.adapters.test_geant4`
(`test_partition_summaries_merge_without_reading_a_csv`, `test_partition_merge_equals_a_single_run_and_refuses_nothing_twice`:
a worker command split at the space of the relocated path), and the same 2 fail on the base `ef37d970` (exported with
`git archive`), so they are not caused by A1; `check_naming.py` pass, baseline not grown; `check_layering.py`,
`check_packaging.py`, `check_wiring.py --since ef37d970`, `reference_inventory.py --check` pass.
Not verified: the break form of the `usine` smoothness convention was not re-read from Weinrich et al. 2020a, Eq. 1;
the V_A zone scaling has no derived error bound.

## CRPROP-C1 — 2026-10-26 (environment E2)

Provider protocol `cr-provider/1` (r3 §C1, §5.2; r4 §6: wave 1, providers folded into the tool work packages).

**Environment.** E2 (macOS arm64 workstation), Python 3.13.2 from `~/.venvs/hep-research-e2`. Base exception D10:
the base is the integration HEAD `ef37d970` (P0), not `main`. r3 §0.3 checks at the start:
`git rev-parse --show-toplevel` = `.claude/worktrees/crprop-c1`; `git branch --show-current` = `worktree-crprop-c1`;
`git status` clean; `git merge-base --is-ancestor ef37d970 HEAD` succeeds (P0, the only prerequisite).

**Acceptance criteria (frozen in `acceptance.json`, written here before the work).** C1-1 a provider not in the
registry is refused; C1-2 single-shot and `--serve` responses have the same sha256 after removing `elapsed_s` and
timestamps (PRV-2); C1-3 a cache hit does not call the provider; C1-4 a forced provider crash is reported as `failed`
with the reason; C1-5 out of domain gives `failed` with `reason: out-of-domain`, and with
`--allow-outside-validated-range` a prediction labelled `outside-validated-range`; C1-6 the core hash equals
`contracts/recipe_semantics.py` `canonical_sha256` on 10 random objects (exact equality of the hex digest);
C1-7 `contracts/tool_contract.py` passes and `core/provider/` holds no path string (`check_layering.py`); ALL-1..ALL-7.
Tolerances: none numerical except C1-2 and C1-6, which are exact (byte-identical hashes).

**Results (E2, 2026-10-26).** Evidence under `$CRPROP_OUT/c1/acceptance/` (outside the repository).

| Entry | Result | Evidence |
|---|---|---|
| C1-1 | pass | `tests.core.test_provider.RegistryRefusal`: unregistered id refused (`unregistered-provider`, provider never started), registered version required |
| C1-2 | pass | `SingleShotAndServe`: sha256 of single-shot and `--serve` responses equal after removing `elapsed_s`; also the closed-form provider (profile `tests/test_provider.py`) |
| C1-3 | pass | `Cache`: second request answered from the cache with 0 provider calls; cache folders named by the point hash |
| C1-4 | pass | `Failures`: exit-7 crash gives `failed`, reason `provider-failed`, stderr in `detail`, in single-shot and `--serve`; exception, invalid response and timeout too |
| C1-5 | pass | `Domain`: `out-of-domain` without prediction; with `--allow-outside-validated-range` a prediction labelled `outside-validated-range` |
| C1-6 | pass | `Hash`: `core.provider.hashing.canonical_sha256` equals `contracts/recipe_semantics.py` `canonical_sha256` on 10 random objects (seed 20261026); point hash equals it on the r3 §5.2 object |
| C1-7 | pass | `contracts/tool_contract.py` pass (16 contracts, incl. `solar_modulation_force_field.json` with the help check); `check_layering.py` ok |
| PRV-1/PRV-2 (closed form) | pass | `core/provider/conformance.py`: 9 of 9 checks; values equal `predict.py bin_averaged` and the committed benchmark prediction exactly; components add to the prediction within 1e-12; 8- vs 32-node quadrature within the declared 1e-6 |

| Check | Result |
|---|---|
| `run_all_checks.py --out $CRPROP_OUT/c1/checks` | pass; 5772 tests, 0 failures, 0 errors, 155 skipped |
| `check_relocation.py --out $CRPROP_OUT/c1/reloc` | fail: 2 tests, `tests.adapters.test_geant4` (`RunAndPartition.test_partition_merge_equals_a_single_run_and_refuses_nothing_twice`, `BoundaryArtifacts.test_partition_summaries_merge_without_reading_a_csv`), a `--cmd` path split at the space of the relocated folder; both fail identically on the base `ef37d970` in a folder with a space (`$CRPROP_OUT/c1/reloc-base/`); not touched by C1 |
| `check_naming.py`, `workflow_check.py gaps/diff/acceptance` (integration copy, `--plugin-root`), `check_wiring.py --since ef37d970`, `check_packaging.py` | pass / ok |
| ruff 0.16.10 and mypy 2.4.0 on `core` and `contracts` | pass |

Not done in C1: the `CONTRACTS_VERSION` line (3.13.0 → 3.14.0). The bump makes 13 tests fail until the fixtures under
`contracts/fixtures/`, the 0.42.0 examples and the measurement template are regenerated, and those files are outside
C1's file list; A2 (merged first, `contracts/fixtures/**` in its list) sets the shared version and `CRPROP_FROM`.
C1 gates no rule by version: its schema changes are optional and additive. The closed-form provider's values are the
profile's ln(E/n) bin average of the ratio (`crsr:bin_average`), not the r3 P2 ratio of bin integrals.

**Rework round 1 (2026-10-27, independent verifier).** (1) Blocking: the shared conformance mixin cached its report on
`type(self)`, so a subclass inherited its parent's verdict (a missing provider passed after a good one). The report
is now kept in the class's own `__dict__`, keyed by provider id, request, outside point and user declarations;
`tests/core/test_provider_conformance_mixin.py` runs the mixin on a good provider, a missing one, a broken
user-supplied one, a subclass of a subclass, in both run orders (pass/fail as expected), and the verifier's
reproduction now fails the broken subclass (3 failures). (2) Advisory: the runner cache key now includes
`theory_spec_ref`, and a request with a `theory_spec_ref` but no transport block is never cached
(`tests.core.test_provider.CacheAndTheorySpec`).

## CRPROP-B2 — 2026-10-26 (environment E2)

Work package B2 of the cr-propagation r4 campaign (r3 §B2): closed forms of the 1D thin-disc model with constant
convection V_c and with radioactive decay of secondaries (¹⁰Be, rate 1/(γτ₀), ¹⁰Be→¹⁰B gain), in
`profiles/theory/cr-secondary-ratio/`.

**Environment (r3 §0.3, base exception D10).** E2: macOS 26.5 arm64 (Darwin 25.5.0), Python 3.13.2 (miniconda,
returned by `find_python.py`), SymPy 1.14.0, NumPy 2.4.4, SciPy 1.17.1. `git rev-parse --show-toplevel` =
`.claude/worktrees/crprop-b2`; `git branch --show-current` = `worktree-crprop-b2`; `git status` clean at start; base
`6a0c2ae6` = integration HEAD (decision D10, not `origin/main`); prerequisite P0: `git merge-base --is-ancestor
6a0c2ae6 HEAD` succeeds. r3 line numbers rechecked on this base (§B2 at line 414, P6 at line 162).

**Criteria and tolerances, fixed before any result (R9).**

| ID | Criterion | Tolerance |
|---|---|---|
| B2-1 (symbolic) | SymPy: the escape term K(V_c, Γ_d) = V_c + D S coth(S L/2), S = sqrt(V_c²/D² + 4Γ_d/D), tends to 2D/L for V_c → 0 and Γ_d → 0 (Γ_d = 1/(γτ₀), τ → ∞); the convective-decay ratio tends to the existing thin-disc ratio; the ¹⁰Be→¹⁰B gain tends to 0 | exact (`sp.limit`, `sp.simplify` equal to 0) |
| B2-1 (numerical) | at V_c = 0 and no decay the new code equals `predict.thin_disc_ratio` at every benchmark energy | relative 1e-12 |
| B2-1 (numerical, approach) | for V_c = 1, 1e-1, …, 1e-4 km/s and τ₀ scaled by 1, 1e2, …, 1e8 the deviation from pure diffusion falls monotonically and is below 1e-4 at the smallest | monotonic; 1e-4 |
| B2-num | closed forms (stable secondary, ¹⁰Be, ¹⁰B with decay gain) against an independent `scipy.integrate.solve_bvp` solution of the same 1D boundary-value problem | relative 1e-6 |
| B2-cons | decay conserves number: with ¹⁰Be and ¹⁰B given the same D and inelastic cross section, N(¹⁰Be) + N(¹⁰B) at z = 0 does not depend on τ₀ | relative 1e-10 |
| B2-2 | dimension checks recorded: [K] = velocity, [S L] = [V_c L / D] = [Γ_d t] = 1, K/(2 h n v) has the dimension of a cross section, every ratio dimensionless; unit conversions (km/s → cm/s, half-life → s, kpc → cm) checked | all pass |
| B2-3 | `python3 -m unittest discover -s profiles/theory/cr-secondary-ratio/tests -t .` | ok |

**Results (dispatch 2, 2026-10-28, on HEAD `236a374a`).** Environment E2 now macOS 27.2 arm64 (Darwin 27.2.0), same
Python 3.13.2, SymPy 1.14.0, NumPy 2.4.4, SciPy 1.17.1; §0.3 checks repeated (toplevel, branch, clean status, base
`6a0c2ae6` ancestor of HEAD). The closed forms were re-derived by hand against r3 P1/P6 and the record (escape term,
the 2 V_c N(0) sweep term of the conservative form, the daughter's particular and homogeneous parts, Γ = 1/(γτ₀) with
τ₀ = t½/ln 2 from `half_life_seconds`, NUBASE year). All criteria above pass within tolerance: B2-1 symbolic (SymPy
limits, both orders; 39 checks in `derivations/convection-decay-derivation.json`, rerun output identical to the stored
record); B2-1 numerical, max relative deviation from `predict.thin_disc_ratio` 2.2e-16 (tolerance 1e-12); approach
0.26, 4.1e-3, 7.2e-5, 4.0e-6, 4.0e-7 (monotonic; last < 1e-4); B2-num, closed forms vs `solve_bvp` 9.8e-15
(tolerance 1e-6); B2-cons spread < 1e-15 (tolerance 1e-10); B2-2 13 dimension checks and the unit-conversion check
pass; B2-3 58 tests ok (from the plugin root and from `tests/`). Checks: `run_all_checks.py` full (33/33 pass) on
`236a374a`; static part, naming, layering, packaging, wiring and `workflow_check.py` diff/gaps/acceptance pass.
Software and numerical-consistency checks only; the inputs are ILLUSTRATIVE and no comparison with data or with a
propagation code is made.

## CRPROP-P0 round 3 — 2026-10-28 (environment E2)

Extra P0 round authorized as decision A1.6 (escalation 4). Base `f747fbe7` (integration HEAD). `workflow_check.py`
`check_diff` now lists changed paths with `git diff --name-only --no-renames <base>...HEAD`, so a renamed or moved
file reports its source path as well as its destination. The other git calls in the file do not have the hole
(`git log --diff-filter=A -- acceptance.json` is path-limited, `git show` reads one revision) and are unchanged.
Regression test `docs/dev/cr-propagation/test_workflow_check.py` (unittest, throwaway repo with `diff.renames=true`):
moving an out-of-scope file and moving an orchestrator-only file (`status.json`) into an allowed path of WP A1 must
fail `diff`, and an in-scope-only change must pass. Without the fix 2 of 3 tests fail (the moves pass `diff`); with the
fix all 3 pass.

## CRPROP-ENV — 2026-10-28 (environment E2)

Work package ENV, dispatch 2 (decision A1.1: USINE V3.5 from `gitlab.com/dmaurin/USINE`). This extends environment
E-crprop with USINE. **Environment field (r3 §0.3, base exception D10):** worktree `.claude/worktrees/crprop-env`,
branch `worktree-crprop-env`, base = integration HEAD 71ae4a07 (not `main`; decision D10). `git rev-parse
--show-toplevel` = this worktree, `git branch --show-current` = `worktree-crprop-env`, status clean at start,
prerequisite P0 an ancestor of HEAD. Host E2 is now macOS 27.2 (Darwin 27.2.0) arm64, Python 3.13.2. No plugin code
changed.

| Item | Result | Evidence |
|---|---|---|
| Source (A1.1) | `git clone --depth 1 --branch V3.5 https://gitlab.com/dmaurin/USINE.git` into `$HOME/hep-work/crprop-build/usine/`: HEAD fb53006d, `refs/tags/V3.5` = 7197ddc1 (an annotated tag); both equal the values in A1.1. No other new network host was contacted | `capabilities.json` `env-usine` |
| Licence | GNU GPL version 2 (`LICENSE`). The plugin is Apache-2.0, so no USINE source or shipped input file (`inputs/`) is committed. Computed USINE output is not covered by the GPL (GPL-2.0 §0), so later work packages may commit output fixtures that hold only computed numbers. ENV commits none: only hashes | `LICENSE` in the checkout |
| Build | USINE's own steps (`mkdir build; cd build; cmake ../; make -jN`, here `make -j4`; 59 s). Products: `bin/usine`, `bin/usine_pbar`, `lib/libTUsine.dylib`, `lib/libfparser.dylib`. Apple clang 21.0.0 with USINE's flags (`-O0`) plus C++17, against Homebrew ROOT 6.38.04. No source file changed. Three host adaptations: `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`, needed because cmake 4.3.2 no longer accepts `cmake_minimum_required(2.8)`; a `root-config` shim outside the source tree that prints `6.38/04`, because `FindROOT.cmake` parses only that form; `-DCMAKE_CXX_STANDARD=17`, because USINE adds `-std=c++14` and ROOT 6.38 needs C++17. `make` runs with `ROOT_INCLUDE_PATH` unset. The host shell points it at the Xcode 26.4 libc++ headers, and those clash with the CommandLineTools 26.2 SDK compiled into libCling. The first `make` failed on this at `rootcling` (exit 139); the second `make`, with it unset, succeeded | `usine-build.computational-run.json`; `$CRPROP_OUT/env/usine/build-logs/` |
| Smoke run | The shipped example `usine -l inputs/init.TEST.par <out> "B/C,B,C,O:KEKN:0.,0.5,1.;B/C:kR:0.79" 2.8 1 1 0` (Model1DKisoVc, force field), 41 s: 14 local-flux tables, `results.root` and 7 plot macros (B/C = 9.36511e-02 at 0.05 GeV/n, φ = 0). Exit status is 1 because `usine` returns 1 on every path. The run with the host `ROOT_INCLUDE_PATH` and the run without it give identical tables (the timestamp line excluded). Without it the ROOT interpreter prints 13 `gCling unresolved` warnings, so runs keep the host value | `$CRPROP_OUT/env/usine/smoke-l*/`, content hashes in the run record |
| Installation test | `usine -tUSINE` (17 min 51 s): 42 of 46 reference tests pass. 4 differ without a changed result: `class_TUDatime` (printed in the local time zone); `usine_i_options` (axis-label text, last digit); `usine_e_options` (values below 1e-12 differ by ≤ 6.5e-14; one tail point at 1.2e-10, about 1e-9 of the peak, differs by 2 %); `propag_minimisation` (same χ²_min and best fit, covariance entries within 1.5e-5 relative; the reference run also stops at the Minuit2 call limit). `doc/install.rst` says last digits differ on macOS | `$CRPROP_OUT/env/usine/tUSINE.stdout.log`, `tUSINE.failed-diff-summary.txt` |
| Capability file (ENV-1) | `env-usine` present (`HEP_USINE_BIN` = `<TOOL_HOME>/bin/usine`, `HEP_USINE_DATA` = `<TOOL_HOME>/inputs`; init files read `$USINE/inputs/…`, so runs export `USINE` = `<TOOL_HOME>`); `net-sources` absent → partial (USINE host reachable; GALPROP hosts not probed); `env-galprop` stays absent (A1.2); the other capabilities are unchanged | `$CRPROP_OUT/capabilities.json` |
| Records (ENV-2) | computational-run `usine-build.computational-run.json` (contracts 3.14.0, `validate.py` ok, no findings) and environment manifest `usine.environment.json` (`environment_manifest.py record`, E2 venv), de-identified (`<TOOL_HOME>`, `<BUILD_ROOT>`, `<VENV>`, `<CONDA_HOME>`, `<RUN_DIR>`) | `tests/adapters/fixtures/cr_propagation/env/` |
| Environment label (ENV-3) | E-crprop row extended with USINE V3.5, compiler, cmake, ROOT, GSL and CFITSIO (not used) | Environments table of this file |
| Checks | `run_all_checks.py --part static --jobs 4`: 31 pass, 0 fail; impacted tests (`tests.tools.test_check_instruction_text`, `tests.adapters.test_cr_propagation`): 25 OK, 1 skipped; `check_naming.py`, `check_wiring.py --since 71ae4a07`, `check_layering.py`, `check_packaging.py`, `workflow_check.py diff --work-package ENV`, `acceptance` and `gaps`: pass; ALL-3 (full `run_all_checks`, `check_relocation`) deferred to the orchestrator's wave run (A1.5) | `$CRPROP_OUT/env/acceptance/` |

USINE status is unvalidated. The smoke run and the installation test show that the build runs and reproduces
USINE's own reference outputs to the last digits; they say nothing about physical validity. The `-O0` build is
USINE's default. An optimised build is not part of ENV and would need its own record.

## CRPROP-A3 — 2026-10-26 (environment E2)

Work package A3 (two-level degeneracy diagnostics) of the cr-propagation r4 workflow, r3 card §A3, principle P7.

Environment: E2 (macOS arm64 workstation), Python 3.13.2 (miniconda), NumPy 2.4.4, SciPy 1.17.1. r3 §0.3 checks:
toplevel `<repo>/.claude/worktrees/crprop-a3`, branch `worktree-crprop-a3`, status clean at start;
base exception (decision D10): base is the integration HEAD `b83881c6`, not `main`; prerequisite P0 (its rework
commits up to `34e2edeb`) is an ancestor of HEAD.

| Item | Result | Evidence |
|---|---|---|
| A3-1 baseline, recorded before any change | 161 tabulated-grid outputs hashed on the base (every in-process `grid_fit` result and every `covariance_fit.py fit` stdout on a tabulated-grid input, from `test_grid_fit`, `test_bc_propagation_fit`, `test_cr_propagation` (2 live DRAGON2 tests skipped), and `examples/bc-propagation-fit/run.py --toys 20` with its `results.json` and `report.md`); two base runs identical | `$CRPROP_OUT/a3/baseline.txt`, harness `$CRPROP_OUT/a3/baseline_harness.py` |
| A3-1 after the change | all 161 sha256 identical to the baseline | `$CRPROP_OUT/a3/after.txt` |
| A3-2 built-in study (`degeneracy.py synthetic-curved`, analytic, Asimov) | Fisher screen: `D0_cm2_s/L_kpc^1.2`, exponent of L_kpc -1.2000, `fisher-screen`, no `valid_range`; profile scan over L_kpc (41 points, D0_cm2_s profiled, threshold 1): `profile-scan`, `valid_range.L_kpc` = [2 (scan edge), 6.947 (threshold)], exponent -1.20003; profiled delta -2 ln L 1.6e-13 at 6 kpc, 19.4 at 8 kpc | `$CRPROP_OUT/a3/acceptance/` |
| A3-2 through `covariance_fit.py` (tabulated grid 25 x 17 nodes of the same model, `degeneracy_scan` {parameter L_kpc}) | Fisher exponent -1.2008, no `valid_range`; profile scan `valid_range.L_kpc` = [2, 6.851], exponent -1.2002 | `tests/skills/hep_statistics/test_degeneracy.py` |
| A3-3 | `degeneracy.py --help` exit 0; module in `NO_INPUT_FILE` | `tests/skills/test_cli_robustness.py` |
| A3-4 | `check_wiring.py --since b83881c6`: pass | |

How the synthetic break is made genuine: the prediction is y_i ∝ (R_i/10 GV)^-0.45 · (u_true/u) · (1 + b(L) h_i) with
u = D0_cm2_s / L_kpc^1.2, so for L <= 6 kpc every point with the same u predicts exactly the truth (exact degeneracy),
and above 6 kpc a spectral tilt b(L) = 0.05 ((L - 6 kpc) / 2 kpc)^2 changes the energy dependence, which u (a pure
normalization) cannot absorb. The data therefore exclude the valley at 8 kpc (profiled delta 19.4), not only the model
declaration. The numbers are SYNTHETIC. The Fisher screen at the best fit (L = 4 kpc) sees only the local exponent;
the profile scan finds where it holds. The A3 tests use only synthetic models; no propagation code was run.

Checks on `f71cd8bb`: `run_all_checks.py` and `check_relocation.py` fail on two findings, both from this WP. The
packaging scan (and `test_batch_privacy`) flagged a home path in this section; it is removed in the next commit and
`check_packaging.py` passes. `test_core_stats_guide.DependencyMarkers` fails because `degeneracy.py` is not listed in
the Skill scripts section of `skills/hep-statistics/references/core-stats-guide.md`, which is outside A3's file list
(workflow.json `files` and `common_files`); the one-line entry is left to the orchestrator. `check_naming.py`,
`check_wiring.py --since b83881c6`, `check_layering.py` and `workflow_check.py` diff, acceptance and gaps pass. The A3-1
hashes were checked again on the committed tree: all 161 identical.

Follow-up (orchestrator added `core-stats-guide.md` to A3's file list): `degeneracy.py` is listed in its Skill
scripts section with the marker "(needs NumPy and SciPy)". The hep-statistics quick load (SKILL.md plus the guide)
had 8 B of headroom under its 25,600 B budget, so four phrases in the guide were shortened with no change in content
(`measure_entrypoints.py --no-cli`: no warnings), and `docs/reference-inventory.*` were regenerated.

Dispatch 2 (2026-10-28, from `eca5da37`): the full `run_all_checks.py --jobs 4` on `eca5da37` failed only in
`tests.skills.test_documented_output_claims` (2 failures): the shortened dependency sentence of the guide had dropped
the two registered quotes "marked ones refuse to run without NumPy (and SciPy) with exit 2 and a JSON message" and
"every script prints `--help` without them". The sentence now carries both quotes again; its lead-in "Dependencies
are marked per script:" is dropped to stay in budget (quick load 25,590 B of 25,600 B, `measure_entrypoints.py
--no-cli`: no warnings) and `docs/reference-inventory.*` are regenerated. On `eca5da37` the other gates passed:
A3-1 (161/161 sha256 equal to the baseline), A3-2 (`valid_range.L_kpc.max` 6.947), A3-3, A3-4, `check_naming.py`,
`check_layering.py`, `check_packaging.py`, `workflow_check.py` acceptance and gaps, and `workflow_check.py diff`
with the integration branch's `workflow.json` (the branch copy predates the orchestrator's addition of
`core-stats-guide.md` to A3's files). The full checks and `check_relocation.py` are rerun on the fix commit
(`$CRPROP_OUT/a3/checks`, `$CRPROP_OUT/a3/reloc`).

## CRPROP-A4 — 2026-10-28 (environment E2)

Work package A4 of the cr-propagation r4 campaign (r3 §A4, r4 §6): cost benchmark of the closed form and DRAGON2
under `harmonized-v1`, and grid convergence of DRAGON2's B/C. The table is the next section, `CRPROP-COST`.

**Environment (r3 §0.3, base exception D10).** E2: macOS 27.2 arm64 (Darwin 27.2.0), 8 cores, 16 GiB; Python 3.13.2
in the E2 venv (numpy 2.5.3, scipy 1.18.1); DRAGON2 runs in E-crprop (the ENV build, `install/bin/DRAGON` sha256
d26dbb85…, source commit cd588707 clean, rechecked before the runs). `git rev-parse --show-toplevel` =
`.claude/worktrees/crprop-a4`; `git branch --show-current` = `worktree-crprop-a4`; `git status` clean at start; base
`566bfd1e` = integration HEAD (decision D10, not `origin/main`); prerequisites A1 (merge 5d5fd918) and ENV (merge
7d5c6934) are ancestors of HEAD (`git merge-base --is-ancestor`). Capabilities: `env-dragon2` present;
`env-usine` and `env-galprop` absent.

**Criteria, fixed before any measurement (R9).** A4-1: every cost number comes from a run record in
`tests/adapters/fixtures/cr_propagation/cost/`, none from the literature; a tool without its capability gets a row
marked "not measured (capability absent)", never an estimate. A4-2: the cost table has closed-form and DRAGON2 rows.
Method (r3 §A4): wall time and peak RSS (`/usr/bin/time -l`, "maximum resident set size", which includes the
DRAGON2 child of the adapter) of three identical runs each, the median reported; grid convergence = largest
|ΔB/C|/(B/C) over 2–1000 GV when the spatial grid (DimR 41 → 81, dz 0.02 → 0.01 kpc) and the energy grid
(Ekfactor 10^(1/20) → 10^(1/40)) are doubled once, each alone and both together; reported, no threshold.

**Results (2026-10-28, records under `tests/adapters/fixtures/cr_propagation/cost/`).** A4-1: every number in
`CRPROP-COST` is read from a computational-run record of this work package (13 records, each `contracts/validate.py`
ok; summary `cost-table.json`); none comes from the literature; USINE and GALPROP are marked not measured. A4-2: the
table has closed-form and DRAGON2 rows. The three DRAGON2 base runs give byte-identical output (sha256 cbfbc3c1…).
Expressing `harmonized-v1` in DRAGON2 (each difference and its substitute, none silent):

| Item | harmonized-v1 | DRAGON2 run | Reason |
|---|---|---|---|
| Diffusion | β¹ (R/1 GV)^0.5, `D0_cm2_s` = 3e28 | `D0_1e28` 3, `DiffRefRig` 1, `Delta` 0.5, `etaT` 1 (DRAGON2 `diffusion.cc`: D0 β^etaT (R/R_ref)^δ) | `transport_conventions.py diffusion` canonical → dragon2 returns `not-convertible` (its dragon2 convention fixes eta = 0); the adapter's `etaT` expresses β¹ directly, so the run spec is written by hand (A1 verifier advisory; not a blocker for the cost rows) |
| Gas | uniform n_H = 1 cm⁻³, He/H 0.1 | `BronfFerr` (adapter default); DRAGON2 helium term with its fixed He abundance 0.11 | `Uniform` is parsed by this DRAGON2 build but `gas.cc` has no density for it (default branch, −1); He/H is a compiled constant |
| Geometry | L 4 kpc, R 20 kpc, h 100 pc | L 4, Rmax 20; no disc half-thickness parameter | h only matters for reacceleration, which is off |
| Sources | all primaries R^−2.3, no break | `OneRing` 0–20 kpc; source.param with every slope 2.3 (breaks inert); DRAGON2 base abundances | the spatial source distribution is open in harmonized-v1 |
| Cross sections | ILLUSTRATIVE set A (C→B 70 mb, O→B 35 mb; inelastic B 250, C 270, O 310 mb) | production table C→¹¹B 70 mb, O→¹¹B 35 mb, O→C 0 mb; DRAGON2's own inelastic cross sections and He-target term | no data file replaces DRAGON2's inelastic cross sections (adapter docstring) |
| Network | parents C, O; tertiary and ghosts off | Z 5–8 (B, C, N, O), only the listed channels | — |
| Output | LIS 1–10³ GeV/n, 20 per decade | E/n grid 0.3–2000 GeV/n, Ekfactor 10^(1/20) | 0.3 GeV/n reaches 2 GV for ¹¹B (a first base run with 0.5 GeV/n was aborted for this) |

The closed form runs its own fixed inputs (hydrogen target, n_H = 1 cm⁻³, C:O = 1:0.9 observed); its point equals
harmonized-v1's transport values.

**Budget (D7).** DRAGON2: 6 completed runs plus the aborted one, 4257 CPU-s for the completed runs (about 1.2
core-hours in total); at most 3 DRAGON2 processes at once. Closed form: 771 point evaluations in 6 runs (about 7
CPU-s). Whether benchmark evaluations count toward D7's 5000 provider evaluations is not stated in D7; reported for
the orchestrator.

Software and timing measurements only; the DRAGON2 and closed-form outputs are not compared with each other or with
data here (that is B3/D3), and the inputs are ILLUSTRATIVE.

## CRPROP-COST — 2026-10-28 (environment E-crprop)

Cost table of the cr-propagation campaign (r3 §A4), feeding E1's budget (r4 §6). Configuration `harmonized-v1`;
`/usr/bin/time -l`; median of three identical runs; records in `tests/adapters/fixtures/cr_propagation/cost/runs/`,
summary `cost/cost-table.json`.

| Tool | Wall time (median) | CPU user (median) | Peak RSS (median) | Runs | Grid convergence of B/C, 2–1000 GV |
|---|---|---|---|---|---|
| Closed form (`cr-secondary-ratio` provider, 1 point × 60 bins, one process) | 0.14 s | 0.11 s | 41 MB | `closed-form-1pt-{1,2,3}` | no spatial or energy grid (analytic point values); bin-average quadrature 8 → 16 nodes: 4.4e-16 |
| Closed form (256 points × 60 bins in one request) | 2.55 s (marginal 9.4 ms per point) | 2.33 s | 44 MB | `closed-form-256pt-{1,2,3}` | as above |
| DRAGON2 cd588707 (DimR 41, DimZ 401, Ekfactor 10^(1/20), 0.3–2000 GeV/n, Z 5–8, serial) | 249 s (127 s in the least-loaded run) | 221 s (125 s) | 475 MB (728 MB) | `dragon2-base-{1,2,3}` | spatial doubled: 1.35e-3; energy doubled: 1.82e-3; both: 1.95e-3 (largest at 3.2 GV; `grid-convergence`) |
| DRAGON2, spatial grid doubled (DimR 81, DimZ 801) | 1931 s (one run) | 1131 s | 1.49 GB | `dragon2-x2s` | — |
| DRAGON2, energy grid doubled (Ekfactor 10^(1/40)) | 990 s (one run) | 503 s | 835 MB | `dragon2-x2e` | — |
| DRAGON2, both doubled | 3252 s (one run) | 2030 s | 2.23 GB | `dragon2-x2se` | — |
| USINE V3.5 fb53006d (Model2DKisoVc, 100 Fourier-Bessel terms, 20 E_k/n nodes per decade, 1–1000 GeV/n, adapter command end to end; added by B1) | 1.49 s | 0.92 s | 299 MB (285 MiB) | `cost/usine-harmonized-v1.computational-run.json` (three timed runs and the convergence runs in one record) | Bessel terms doubled: 1.1e-4; energy doubled: 7.1e-5; both: 6.7e-5 |
| GALPROP v57 | not measured (capability absent: `env-galprop`) | | | | |

Caveat: the host was shared with other campaign workers (load average 7.6 before the first DRAGON2 base run, 26–62
during the second and third, swap nearly full), so DRAGON2 wall time varies ×4 and peak RSS ×1.7 between identical
runs with identical output; the doubled-grid runs ran three at a time. The least-loaded base run (127 s, 125 CPU-s)
is the best estimate of the uncontended cost; the medians are the conservative figure. For E1 at the median CPU
time, D7's 200 core-hours cover about 3300 DRAGON2 evaluations at this grid (about 5700 at 125 CPU-s), fewer than
D7's 5000 evaluations; E1's USINE cost is in the USINE row (B1). Grid convergence is reported without a threshold; the
energy-doubling figure includes the change of the log-log interpolation between DRAGON2 nodes.

## CRPROP-B1 — 2026-10-28 (environment E2)

Work package B1 of the cr-propagation r4 campaign (r3 §B1 and §B1b folded together, r4 §6): USINE V3.5 translator
(`transport` block to a USINE initialisation file), reader (USINE local-flux tables to ratios of bin integrals, r3
P2, P3, P11), recorded runs replayed offline, the USINE row of the cost table and the cr-provider/1 entrypoint
`usine_provider.py`.

**Criteria and tolerances, fixed before any comparison (R9).** Frozen entries (acceptance.json): B1-1 offline replay
tests pass with `HEP_USINE_BIN` and `HEP_USINE_DATA` unset; B1-2 a live rerun (`HEP_USINE_LIVE_TEST=1`) of every
recorded run reproduces the recorded USINE outputs within relative 1e-6, value by value, with the live test not
skipped; B1-3 `tested_versions` of the USINE tool names the USINE version and commit, the compiler and the ROOT
version, and the adapter status follows R3 (the lowest tool status); B1-4 the cost table has a USINE row (wall time
and peak RSS, median of three identical runs, `/usr/bin/time -l`; grid convergence reported without a threshold, as
A4 does); B1-PRV-1 C1's conformance mixin passes for provider `usine`; B1-PRV-2 single-shot and `--serve` responses
have the same sha256 after removing `elapsed_s` and time stamps. Added by this work package (stricter checks only,
none replaces a frozen entry): the reader's element ratio from the isotope tables agrees with USINE's own element-ratio
output at USINE's grid points within relative 1e-4 on the axis ekn (same nodes; only the 6-digit rounding of the
tables differs) and within relative 2e-3 on the axis rigidity (log-log interpolation between nodes); a transport item
USINE cannot express is either recorded as a substitute in the translation or refused (never a silent default); no
USINE source, shipped input file or file copied from them is committed (GPL-2.0), only numbers computed by USINE runs
and this work package's own specifications and records.

**Environment (r3 §0.3, base exception D10).** E-crprop = E2 (macOS 27.2 arm64, Darwin 27.2.0), Python 3.13.2
(miniconda; the adapter needs the standard library and core only), USINE V3.5 built by ENV dispatch 2 (git tag V3.5,
tag object 7197ddc1, commit fb53006d, Apple clang 21.0.0, Homebrew ROOT 6.38.04, cmake 4.3.2; `bin/usine` sha256
1d444720…), located through `HEP_USINE_BIN` and `HEP_USINE_DATA`, with `USINE` set to its folder for each run.
`git rev-parse --show-toplevel` = `.claude/worktrees/crprop-b1`; `git branch --show-current` = `worktree-crprop-b1`;
`git status` clean at start; base `0be5a5de` = integration HEAD (decision D10, not `origin/main`); prerequisites A1
(merge 5d5fd918), C1 (merge 099d1d22) and ENV dispatch 1 (merge 7d5c6934) are ancestors of HEAD (`git merge-base
--is-ancestor`); ENV dispatch 2 (the USINE build record, branch `worktree-crprop-env`) is not merged into the base and
was used through its build only. Rebased on 2026-10-28 onto integration HEAD `d04cb47a` (A4 merged; orchestrator request): the translator, reader and provider are unchanged by the rebase, so the live runs were not repeated; the checks of the report were rerun on the rebased HEAD. r3 line numbers rechecked on this base (§B1 at line 406, §5.2 at line 300).

**Translation choices (recorded in every run's `substitutes`).** `cylinder-2d` → Model2DKisoVc (thin disc, observer
at r = 8.3 kpc as in the DRAGON2 adapter, no central hole, 100 Fourier-Bessel terms), `slab-1d` → Model1DKisoVc. Gas:
n_H read from `gas.model`, all neutral in the thin disc, so USINE's Coulomb term (on HII) is zero;
`He_to_H_number` not used, because the ILLUSTRATIVE sets are on hydrogen only. Sources: dQ/dE_k/n = q R^-γ,
uniform in r up to `radius_kpc` (template CST); parent abundances fixed by USINE's NormList on generated points (not
data) so that the unmodulated local O/C is 0.9 at 10 GeV/n (the parent list of `theory:cr-secondary-ratio`). Set A
(element-level) is placed on 12C, 16O and 11B. Low breaks use the plugin's "usine" convention
(transport_conventions.py; known issue 2: not re-read from Weinrich et al. 2020a, and USINE V3.5's shipped inputs
carry only a high-break formula, `inputs/init.TEST.par` Model1DKisoVc K); a high break is refused. Momentum
diffusion: the Kpp form of USINE's shipped initialisation files (Seo-Ptuskin, w = 1, here divided by w). The 10Be
half-life of USINE's chart (1.387 Myr) is checked against NUBASE2020 (core) at each decay run. Two USINE behaviours
found on the way: with `IsUseNormList false` USINE V3.5 crashes (segmentation violation in
`TUValsTXYZECr::OrphanVals`), hence the generated normalisation points; and USINE needs every reaction from a
heavier list member filled, hence the zero channels.

**Results (2026-10-28, on the final HEAD).**

| ID | Result | Evidence |
|---|---|---|
| B1-1 | passed: 43 tests, 5 skipped (the live USINE, conformance and DRAGON2 classes), with `HEP_USINE_BIN`/`HEP_USINE_DATA` unset | `$CRPROP_OUT/b1/acceptance/B1-1-offline.txt` |
| B1-2 | passed: the seven recorded runs rerun live reproduce every table (nodes identical, values within 1e-6; in fact identical apart from the time-stamp line); live test not skipped (only `LiveDragon2` skipped) | `$CRPROP_OUT/b1/acceptance/B1-2-live.txt` |
| B1-3 | `tested_versions` names V3.5, commit fb53006d, Apple clang 21.0.0 and ROOT 6.38.04; USINE `tested-in-declared-environment`, adapter stays `proposed` (GALPROP `proposed`, R3) | `adapters/cr-propagation/adapter.json` |
| B1-4 | USINE row in `CRPROP-COST` (record `tests/adapters/fixtures/cr_propagation/cost/usine-harmonized-v1.computational-run.json`) | `CRPROP-COST` table, `cost/cost-table.json` |
| B1-PRV-1 | passed: all nine checks of `core/provider/conformance.py` (declared, single-shot, serve, prv-2, unsupported-want, out-of-domain, outside-allowed, unregistered, runner-agrees) and the schema checks of the mixin, live | `$CRPROP_OUT/b1/acceptance/B1-PRV-conformance.json`, B1-2 log |
| B1-PRV-2 | passed: single-shot and `--serve` responses have equal sha256 after removing `elapsed_s` (check prv-2) | as above |
| reader (added) | passed: the reader's B/C and 10Be/9Be from the isotope tables against USINE's own ratio tables, every run: at most 8e-6 on E_k/n (tolerance 1e-4), 2.8e-4 on rigidity (tolerance 2e-3) | `UsineReader.test_reader_matches_usine_element_ratios` |

**Recorded runs** (`tests/adapters/fixtures/cr_propagation/usine/`: `specs/`, `inputs/` as written by the translator
with `<TOOL_HOME>`/`<RUN_DIR>`, `outputs/` USINE's tables, `runs/` computational-run records, `usine-results.json`):
harmonized-v1, d1-isotopic, d1-convection, d1-decay, d1-reacceleration, d1-losses (the transport blocks of D1's
`harmonized-v1-<item>.json`, branch `worktree-crprop-d1` 131ae000, copied unchanged) and b1-slab-all-items (1D, low
break, η = -0.5, whole-halo V_A, V_c, all losses, decay). Each run takes 0.7-2.7 s. For D1-1 (reacceleration and
losses items, USINE as reference): `usine-results.json` holds B/C on D1's 16 rigidity bins 2-1000 GV and 10Be/9Be on
its 12 E_k/n bins 0.05-10 GeV/n for every item (e.g. B/C in the first bin 0.2322 with reacceleration, 0.1437 with
losses, 0.1656 item off); D1 can also recompute them with `usine_to_prediction.ratio_of_bin_integrals` from
`outputs/<run>/`. Numbers only; no USINE file is committed.

**Cost row.** The USINE row (median wall 1.49 s, peak RSS 285 MiB, grid convergence 1.1e-4 / 7.1e-5 / 6.7e-5) is in the `CRPROP-COST` table above and in `cost/cost-table.json`; record `tests/adapters/fixtures/cr_propagation/cost/usine-harmonized-v1.computational-run.json` (moved there after the rebase onto A4, base d04cb47a).

Provider tolerance: with reacceleration on, B/C and 10Be/9Be bins change by at most 2.0e-3 between the default grid
and 80 nodes per decade with 200 Bessel terms (with losses, convection and decay all on 5.3e-4), so the provider
declares `numerical_tolerance` 0.005 (a rounded-up numerical bound, not a physics uncertainty). Checks: static part of
`run_all_checks.py`, naming, wiring, `workflow_check.py` diff and acceptance on the final HEAD (report); ALL-3
deferred to the wave run (A1.5). Software and numerical-consistency checks only: every input is ILLUSTRATIVE and no
comparison with data is made.

## CRPROP-C2 — 2026-10-28 (environment E2)

Work package C2 (multi-dataset propagation fit, closed-form provider, SYNTHETIC data only) of the cr-propagation r4
workflow, r3 card §C2 as split by r4 §6 (the USINE case is C2U).

Environment: E2 (macOS arm64 workstation), Python 3.13.2 (miniconda), NumPy 2.4.4, SciPy 1.17.1. r3 §0.3 checks:
toplevel `<repo>/.claude/worktrees/crprop-c2`, branch `worktree-crprop-c2`, status clean at start; base exception
(decision D10): base is the integration HEAD `699c3b5c`, not `main`; prerequisites A2 (`a3c880f8`), A3 (`f62f70e8`),
C1 (`099d1d22`) and B2 (`81cb2ce0`) are ancestors of HEAD.

Criteria and tolerances, written before any fit was run (R9; frozen entries C2-1 to C2-6 of `acceptance.json`, the
r3 suggested defaults adopted at H0). Provider: `cr-secondary-ratio-closed-form` 0.1.0 (B/C, axis ekn), whose values
are bin-averaged in ln(E/n) (`crsr:bin_average`), not P2 bin integrals; synthetic data are generated with the same
semantics, and data declared `bin-integrated` are refused. All inputs are ILLUSTRATIVE.

| Item | Pre-declared setting or criterion |
|---|---|
| Datasets | two SYNTHETIC B/C sets from the provider at the truth: A, 12 bins 1-1000 GeV/n (3% uncorrelated + 2% with correlation exp(-\|d ln E\|/1.5)); B, 8 bins 10^0.5-10^2.5 GeV/n (5% uncorrelated + 3% fully correlated) |
| Truth (interior) | `D0_cm2_s` = 3e28, `delta` = 0.5, `L_kpc` = 4 (fixed unless free), `R0_gv` = 1; production norms of C->B and O->B = 1 with Gaussian priors of 10% (P15) |
| C2-1 | Asimov fit with the provider (no response model): every free parameter within 0.1 sigma of its true value, sigma from the inverse Fisher matrix at the best fit; boundary case `delta` = 0.2 (lower edge of the provider domain, standing in for a physical boundary the closed form cannot express): the minimum on the boundary passes `boundary_kkt` and lies within 0.1 sigma_one-sided, sigma_one-sided = distance from the boundary to the profile delta chi2 = 1 crossing on the allowed side |
| C2-2 | 1000 plug-in toys at the interior truth (family: `D0_cm2_s`, `delta` free, C->B norm with its auxiliary value redrawn per toy); tested: `D0_cm2_s`, `delta` and the Fisher eigen-direction with the smallest eigenvalue in (ln D0, delta, C->B norm) (the nearly flat direction; eigenvalue ratio reported); covered when the profile delta chi2 at the true value is <= 1; pass when \|coverage - 0.6827\| <= z_m sqrt(0.6827 x 0.3173 / n) for each of the m = 3 quantities, z_m = Phi^-1(1 - 0.0027 / (2 m)) (Bonferroni over m at the familywise 3-sigma level; z_3 = 3.32); the uncorrected 3-sigma verdict is also reported |
| Response model (toys, posterior) | the toys and the posterior use a tensor Chebyshev interpolation of the provider components, built from provider evaluations in a box of +-5 sigma around the expansion point; refused unless its maximum error at 12 random provider points in the box is <= 0.02 of the data sigma in every bin; its error enters the toy covariance as an uncorrelated component (P10); a toy fit outside the box is a failed toy |
| C2-3 | BIG and SLIM declared in their literature parameters (V_A, V_c, low-energy break) are listed as not expressible by the closed form, with the reason; the expressible families are listed with their delta chi2 calibrated by 200 toys each, surviving when the toy p-value is >= 0.05 |
| C2-4 | the fit-derived theory-spec carries only object-form `degenerate_directions` (evidence `profile-scan` with `valid_range`) and passes `contracts/validate.py`; so does the statistical-result |
| C2-5 | a dataset without a covariance exits 3 (`incomplete`); a start point outside the provider domain is refused (exit 1, reason out-of-domain); a dataset declared `bin-integrated` is refused (exit 1) |
| C2-6 | a forced non-convergence (optimizer limited to 1 iteration) stops after 5 restarts with reason restart-cap; forced toy failures stop the study once more than 2% of the toys failed; a chain longer than 2e5 steps is refused; a posterior interval is withheld (`unvalidated`) when R-hat > 1.01 or ESS < 400 |
| D7 | provider point evaluations counted by the runner (`points_sent`) and reported; the provider cache lives under `$CRPROP_OUT/c2/cache` |

Results (`examples/propagation-fit/run.py --toys 1000 --family-toys 200`, seed 20261028, on the WP head; outputs in
`$CRPROP_OUT/c2/acceptance/`; tests in `tests/skills/hep_statistics/test_propagation_fit.py`, 16 tests):

| Item | Result | Evidence |
|---|---|---|
| C2-1 interior | converged (EDM below 1e-5, no restart); pulls of `D0_cm2_s` (sigma_ln 0.110), `delta` (sigma 0.0084), C->B and O->B norms (sigma 0.097, 0.099) all below 1e-10 sigma | `example/asimov-interior/result.json` |
| C2-1 boundary | `delta` = 0.2 on the lower domain bound, `boundary_kkt` derivative +0.092 (ok); profile interval lower end `bound`, upper crossing at 0.20605: sigma_one-sided = 0.00605, pull 4e-13; `D0_cm2_s` and the norms within 1e-10 sigma | `example/asimov-boundary/result.json` |
| C2-2 | 1000 plug-in toys, 0 failed; response model error 3.2e-7 of the data sigma (12 provider points); Fisher eigenvalue ratio 4.2e-4, flattest direction (0.726, -0.038, 0.686) in (ln D0, delta, C->B norm); coverage `D0_cm2_s` 0.686, `delta` 0.671, flattest 0.696; Bonferroni band (m = 3, z = 3.32) +-0.0489: pass for all three (also within the uncorrected 3-sigma band +-0.0442) | `example/coverage/result.json` |
| C2-3 | BIG (missing `V_A_kms`, `V_c_kms`, `R_break_gv`, `delta_below`, `s`) and SLIM (`R_break_gv`, `delta_below`, `s`) listed as not expressible by the closed form; delta chi2 with 200 toys each, 0 failed: `diffusion` 0 (p = 1.0, surviving), `iroshnikov-kraichnan` 0.195 (p = 0.61, surviving), `kolmogorov` 478.2 (0 of 200 toys, p < 0.015 at 95%, excluded) | `example/families/result.json` |
| C2-4 | fit-derived theory-spec: one object `D0_cm2_s/L_kpc` (exponent of L_kpc -1.00000002, evidence `profile-scan`, `valid_range` L_kpc [1, 20] at the scan edges, D0_cm2_s [7.40e27, 1.48e29]); the Fisher screen gave the same combination (exponent -0.9999994, no valid_range, not written to the spec); `contracts/validate.py` on the theory-spec and the statistical-result: ok, no finding | `C2-4.validate.txt`, `example/degeneracy/` |
| C2-5 | missing covariance: exit 3 `incomplete` (dataset named); start `D0_cm2_s` = 5e30: exit 1 `out-of-domain`; truth `delta` = 0.95: exit 1 `out-of-domain`; dataset declared `bin-integrated`: exit 1 `bin-semantics-mismatch`; binning convention missing: exit 1; cross-section set not stated in the gate plan: exit 1 `not-comparable`; dataset with a period: exit 1 `modulation-needs-isotopic-lis` | `test_propagation_fit.txt` |
| C2-6 | `optimizer.max_iterations` 1: 6 attempts, `restart-cap`, status failed; toys with `max_iterations` 1: stopped after 2 failed of 2 generated (above 2% of 50), `toy-failure-threshold`, no coverage; posterior `steps` 200001: exit 1 `chain-step-cap`; 2 chains of 200 steps: `unvalidated`, ESS below 400, no interval | `test_propagation_fit.txt` |
| P9 | covariance alternatives of set A, correlation length 0.5 / 1.5 / 4: chi2 10.72 / 11.22 / 11.72, `delta` 0.49625 / 0.49609 / 0.49658, `D0_cm2_s` 2.968e28 / 2.969e28 / 2.948e28 (fitted one by one) | `example/degeneracy/result.json` |
| Posterior | `diffusion` on the pseudo-data, 4 chains x 20000 steps (half burn-in) on the family response model: R-hat 1.0026, ESS 2524, acceptance 0.30, 23 of 80000 proposals outside the box; 68% intervals reported | `example/families/result.json` |

Provider point evaluations (D7; one request per dataset, so a two-dataset parameter point counts twice): a cold run of
the example costs about 2800, 1730 of them in the `degeneracy` stage (the L-BFGS-B profile scan of `degeneracy.py`,
7 points); the test module about 190 per run. C2 used about 6600 in total during development and acceptance (3328
cached under `$CRPROP_OUT/c2/cache`, about 2100 uncached scratch measurements, about 1150 in six test runs), at
about 4 ms each. If D7's cap of 5000 evaluations counts closed-form provider evaluations, C2 alone exceeds it: reported as a
budget item.

Not done in C2: the force-field modulation path (no provider with isotopic LIS exists yet; a dataset with a period is
refused), the USINE case (C2U), real data. Observed in the protocol: two observables with the same id in one request
make the provider's components ambiguous (the runner rejects the response as invalid), so the fit sends one request
per dataset.

## CRPROP-B3 — 2026-10-28 (environment E2)

Work package B3 of the cr-propagation r4 campaign (r3 §B3): USINE V3.5 against the closed forms of
`theory:cr-secondary-ratio` under `harmonized-v1`, the main production channels, and the check of level-by-level
cross-section reweighting (r3 P5, §5.3) against full USINE reruns.

**Criteria and tolerances, fixed before any comparison (R9).** Frozen entries (acceptance.json, D-defaults): B3-1
2%, B3-2 0.5%, B3-3 artifact `$CRPROP_OUT/b3/b3-channels.json`. How they are evaluated (written here before any B3 run
was compared; none of this replaces or widens a frozen entry):

- Common settings, both sides. Transport of `harmonized-v1` (L = 4 kpc, h = 100 pc, n_H = 1 cm^-3 in the thin disc,
  K = β K0 (R/1 GV)^0.5 with D0 = 3e28 cm²/s, V_A = V_c = 0, losses off, all primaries R^-2.3). Cross sections: the
  ILLUSTRATIVE sets of the profile (set A for B/C; `xs-illustrative-decay` with decay on for ¹⁰Be/⁹Be, D1's
  `harmonized-v1-decay` transport), on hydrogen only on both sides: `He_to_H_number` is used by neither side (the
  sets have no helium cross section; harmonized-v1 and xs-illustrative-A differ on the helium target, and the
  comparison uses the hydrogen-only reading). Tertiary chains and ghost nuclei off on both sides. Same losses on both
  sides (none). Every field of each transport block is set explicitly, and the translation's `substitutes` and
  generated USINE file are checked to carry the value set (the translator defaults geometry and diffusion fields and
  ignores `species` and `family` silently; B1 verifier).
- Same parents. USINE propagates C and O from R^-2.3 sources, normalized so that O/C = 0.9 at 10 GeV/n; the closed
  form is evaluated at each USINE E_k/n node with its parent ratio O/C set to USINE's propagated O/C at that node.
- Source spatial distribution (not fixed by harmonized-v1): uniform in r up to radius_kpc = 20 kpc, observer at
  r = 8.3 kpc, z = 0 (as D1 and B1) in the 2D model; none in the 1D model.
- Geometry. The closed form is the 1D thin-disc solution and cannot express the radial boundary of harmonized-v1
  (§5.5: the side that cannot express an item records the difference). B3-1 is evaluated on USINE Model1DKisoVc
  (`slab-1d`, same L and h; the like-for-like comparison) and B3-1 passes only if that comparison meets 2%. The same
  comparison against USINE Model2DKisoVc (harmonized-v1 geometry as frozen) is reported with the same 2% and its
  verdict stated separately; a 2D miss is recorded with its attribution and reported, never absorbed.
- B3-1 metric: the largest |r_closed / r_USINE - 1| over B/C on the 16 log-uniform rigidity bins 2-1000 GV and over
  ¹⁰Be/⁹Be on the 12 log-uniform E_k/n bins 0.05-10 GeV/n of B1 and D1, both ratios of bin integrals (r3 P2, P3;
  `usine_to_prediction.ratio_of_bin_integrals`); the closed-form isotope fluxes on USINE's nodes are the closed-form
  mid-plane density relative to ¹²C times USINE's ¹²C flux. Stricter, also required: the same at every USINE node in
  the two ranges (point ratios at equal E_k/n and at equal rigidity).
- B3-2 configurations (all USINE Model2DKisoVc): `h1` (harmonized-v1, set A), `dec` (harmonized-v1-decay), and `all`
  (`dec` plus V_A = 10 km/s in the thin disc, V_c = 10 km/s, losses ionization, coulomb and adiabatic; the gas is
  neutral, so USINE's Coulomb term is zero and the losses are ionization and adiabatic only), which couples energies.
  Reweighting of channel c by 1 + ε, ε = ±0.2: F_s = F_s(nominal) + ε F_s(c), with F(c) a USINE run in which only
  channel c is non-zero (same parents, which no channel feeds), applied level by level from heavy to light: the
  response of a ¹⁰Be channel carries its ¹⁰B decay daughter. It is compared with a full USINE rerun with σ_c × (1 + ε).
  Metric: the largest relative deviation over B/C (16 rigidity bins), ¹⁰Be/⁹Be and Be/B (12 E_k/n bins 0.05-10 GeV/n)
  and every secondary isotope flux at every USINE node in 0.05-1000 GeV/n; tolerance 0.5%. Reported, same tolerance:
  closure of the sum of single-channel responses on the nominal run, and the error of skipping the daughter update.
- Main channels (B3 step 2): a channel whose response is at least 1% of its observable's numerator (B for B/C, Be for
  Be/B) in at least one bin of `h1` or `dec`; the others are listed as minor and tested in the same way.
- B3-3: in `b3-channels.json` every channel and configuration carries `must_rerun: true` for norm reweighting if its
  B3-2 deviation exceeds 0.5%. Slope-type variation (P15, illustrative): σ_c(E) = σ_c (E/E_thr)^s below
  E_thr = 10 GeV/n, s = 0.1, for C→¹¹B and C→¹⁰Be in `dec` and `all`, compared with a rerun by (i) a post-propagation
  weight on the channel response at the output E_k/n and (ii) energy-basis responses (one USINE run per node of the
  cross-section table below E_thr, plus one for the rest); a method within 0.5% may be used (`must_rerun: false`, with
  the method named), otherwise `must_rerun: true`. Inelastic cross-section changes: `must_rerun: true` without a test
  (not linear, r3 P5).
- Budget (D7): each USINE run is counted; the B3 total is reported.

*Note of 2026-10-28 (rework round 1; the paragraph above is unchanged, R9).* The B3 verifier ruled that B3-1 as
frozen is judged under harmonized-v1 (cylinder-2d, R = 20 kpc; r3 §B3 and §5.5), not on the matched 1D geometry
chosen above. The maintainer's decision A1.10 (decisions.md) keeps B3-1 unchanged in acceptance.json and supersedes it
for B3's verdict by three added entries: B3-1a (USINE in a 1D geometry matched to the thin-disc closed form, same
parents, cross sections, tertiary/ghost and loss settings: B/C over 2-1000 GV and ¹⁰Be/⁹Be over 0.05-10 GeV/n within
2%, evaluated with the metric above, bins and nodes), B3-1b (the harmonized-v1 2D offset reported per bin and
attributed, including the hydrogen-only target against He_to_H_number 0.1; no tolerance) and B3-1c (stricter: USINE
harmonized-v1 2D against the Fourier-Bessel thin-disc solution with the same inputs within 0.5% on the same bins;
B/C of `h1-2d`, ¹⁰Be/⁹Be of `dec-2d`, 2000 terms). The tolerances above are not changed.

**Environment (r3 §0.3, base exception D10).** E-crprop = E2 (macOS 27.2 arm64), Python 3.13.2 (miniconda, numpy and
scipy for the closed forms), USINE V3.5 (git tag V3.5, commit fb53006d, Apple clang 21.0.0, ROOT 6.38.04; the ENV
build) through `HEP_USINE_BIN` and `HEP_USINE_DATA`. `git rev-parse --show-toplevel` = `.claude/worktrees/crprop-b3`;
`git branch --show-current` = `worktree-crprop-b3`; `git status` clean at start; base `2d451e87` = integration HEAD
(decision D10, not `origin/main`); prerequisites B1 (merge 3ed1e89e), B2 (merge 81cb2ce0), ENV dispatch 2 (cbb7907f),
A1 (5d5fd918), A2 (a3c880f8), C1 (099d1d22) are ancestors of HEAD (`git merge-base --is-ancestor`). r3 line numbers
rechecked on this base (§B3 at line 418, §5.5 at line 375, B3 criteria at line 550).

**Runs.** 181 USINE runs of the final study (`b3_study.py run`, 4 at a time, 433 s of USINE wall time in total, about
0.12 core-hours), plus 11 exploratory nominal runs of the same specifications before it (overwritten): 192 USINE runs
toward D7, none through a provider. Specifications `tests/adapters/fixtures/cr_propagation/b3/specs/` (every field
explicit; `check_used` confirmed each value in the generated USINE file and the translation, and no run reported a
problem); nominal tables and computational-run records committed in `b3/outputs/` and `b3/runs/`; every run with
the sha256 of the data lines of its isotope tables in `b3/b3-run-index.json` (header with the run date left out, so a
rerun compares; rework round 1); results `b3/b3-results.json`, channel list
`b3/b3-channels.json` (also `$CRPROP_OUT/b3/`). The production table of a varied run is written by `b3_study.py`
on a log grid of 10 nodes per decade (USINE interpolates it linearly in the value against ln E_k/n,
`TUMath::Interpolate` kLOGLIN_INFNULL_SUPCST, so responses superpose exactly); USINE's own cross-section files are
not used (escalation 8, WP B1X).

**Results (2026-10-28).**

| ID | Result | Evidence |
|---|---|---|
| B3-1 (frozen) | failed under harmonized-v1 (2D, R = 20 kpc): B/C closed form / USINE 2D = 1.009 (2-2.9 GV) rising to 1.0247 (678-1000 GV), above 1.02 in the 8 bins from 44.7 GV up (max 2.47%); ¹⁰Be/⁹Be within 2% (0.987-0.995, max 1.3%). Attributed to radial escape (below); superseded for B3's verdict by B3-1a/b/c (A1.10) | `b3_1.h1-2d`, `b3_1.dec-2d`; `test_b3_1_fails_under_harmonized_v1` |
| B3-1a | passed (USINE Model1DKisoVc, matched to the 1D thin-disc closed form): B/C max 9e-5 over the 16 rigidity bins (1e-4 at nodes); ¹⁰Be/⁹Be max 4.1e-4 over the 12 E_k/n bins (4.1e-4 at nodes); tolerance 2% | `b3_1.h1-1d`, `b3_1.dec-1d`; `test_b3_1a_matched_1d_geometry`; `$CRPROP_OUT/b3/acceptance/B3-1.txt` |
| B3-1b | reported and attributed (no tolerance): per-bin closed form / USINE 2D and USINE 2D / USINE 1D for B/C (h1-2d, dec-2d) and ¹⁰Be/⁹Be (dec-2d); the product of the two is 1 within 1e-3 in every bin, so radial escape accounts for the whole offset; target hydrogen-only on both sides (below) | `b3-results.json` `b3_1b`; `test_b3_1b_offset_reported_and_attributed` |
| B3-1c | passed: USINE harmonized-v1 2D against the Fourier-Bessel thin-disc solution (same inputs, 2000 terms): B/C (h1-2d) max 0.21%, ¹⁰Be/⁹Be (dec-2d) max 0.16%; tolerance 0.5% | `b3_1c`; `test_b3_1c_fourier_bessel` (recomputed offline from the committed outputs) |
| B3-2 | passed: level-by-level norm reweighting at ±20% against full reruns, all 22 channel × configuration cases (h1-2d 2, dec-2d 10, all-2d 10): max 8.9e-6 over B/C, ¹⁰Be/⁹Be, Be/B bins and every secondary isotope node (tolerance 0.5%); closure of the single-channel responses on the nominal run max 5.7e-6 | `b3_2`; `$CRPROP_OUT/b3/acceptance/B3-2.txt` |
| B3-3 | written: 22 rows, all main (share of the numerator 0.6-70%); norm `must_rerun: false` for every row (none beyond 0.5%); inelastic `must_rerun: true` for every row (not tested, P5); slope: C→¹¹B and C→¹⁰Be in dec-2d (post-propagation weight, 8.6e-6) and all-2d (energy-basis responses, 9.4e-6) `must_rerun: false` with the method named, the other 18 rows `must_rerun: true` (no energy-basis responses computed) | `$CRPROP_OUT/b3/b3-channels.json` |

Attribution of the B3-1 miss under harmonized-v1 (B3-1b; the closed form cannot express the radial boundary). USINE 2D / USINE 1D: B/C up to
-2.4%, ¹⁰Be/⁹Be up to -1.3%, growing with energy as destruction gives way to escape; a Fourier-Bessel thin-disc
solution written like the closed form (free escape at r = 20 kpc and z = ±L, sources uniform in r, observer at
8.3 kpc, same parents) reproduces USINE 2D within 0.21% for B/C (2000 terms; 100 terms as USINE: 0.21%) and 0.16% for
¹⁰Be/⁹Be; with the radial boundary at 40 kpc (80 kpc) the 1D closed form agrees with USINE 2D within 0.02% (0.06%).
The 2D-1D difference is therefore the radial escape of harmonized-v1's geometry, not a translation or transport
error; it is consistent with P7 (DRAGON2, R = 20 kpc: D0/L within 2% for L = 2-4 kpc). Target: harmonized-v1 sets
He_to_H_number 0.1, but both sides use hydrogen only (the ILLUSTRATIVE sets have no helium cross section; the
translator records the substitute), so the helium target does not enter the offset; it is a departure of both sides
from harmonized-v1 that would raise production and destruction alike (for scale: DRAGON2's fixed helium target
factor 1.143, P11) and is not tested here. Unattributed: the residual of USINE 2D against the Fourier-Bessel solution
(0.21% / 0.16%, within B3-1c), likely USINE's radial source integration (NIntegrR 1000); not investigated further.
Not loosened: B3-1 fails under harmonized-v1 as frozen; A1.10 supersedes it for B3's verdict.

Findings. (1) Same parents matter: USINE's propagated O/C runs from 0.849 to 0.922 over the grid (0.9 at the
10 GeV/n normalization), against the constant 0.9 of the profile's benchmark; O→B is about 30% of B. (2) Level by level
is needed: reweighting a ¹⁰Be channel without updating its ¹⁰B decay daughter errs by up to 2.1% (C→¹⁰Be) and 0.9%
(O→¹⁰Be). (3) Without energy coupling (dec-2d) an energy-dependent slope is applied exactly after propagation; with
reacceleration, convection and losses (all-2d) the post-propagation weight errs by 4.4% (C→¹¹B, ¹¹B nodes; 2.4% on
Be/B) and 1.5% (C→¹⁰Be, 1.2% on ¹⁰Be/⁹Be), while 26 energy-basis responses per channel reproduce the rerun within
1e-5. (4) In all-2d a response to a single table node undershoots below zero by up to 4% of its peak (USINE's energy
scheme); the values are used as written and still superpose. Limits: the ILLUSTRATIVE network has one parent level
(C, O primaries) plus ¹⁰Be→¹⁰B, so multi-level chains (O→C→B, P5) are not exercised; helium target and ghost nuclei off
on both sides; no low break used (the unverified "usine" low-break form does not enter); USINE's losses here are
ionization and adiabatic (neutral gas, Coulomb zero). Software and numerical-consistency checks only: every input is
ILLUSTRATIVE and no comparison with data is made. Checks: static part of `run_all_checks.py`, the impacted tests,
naming, wiring, `workflow_check.py` diff and acceptance on the final HEAD (report); ALL-3 deferred to the wave run
(A1.5).

## CRPROP-E1 — 2026-10-28 (environment E2)

Training set and bounded active addition with USINE (r3 §E1, r4 §6; optional WP). Driver and committed records under
`tests/adapters/fixtures/cr_propagation/e1/` (`active_addition.py`, `design.json`, `summary.json`,
`forced-test.json`); training data, run folders, cache and partition state stay under `$CRPROP_OUT/e1/` (E1-3).

**Environment (r3 §0.3, base exception D10).** E2: macOS 27.2 arm64, Python 3.13.2 in the E2 venv (numpy 2.5.3, scipy
1.18.1); USINE V3.5 fb53006d (`HEP_USINE_BIN`, `HEP_USINE_DATA` of the ENV build), provider `usine` 0.2.0 (adapter
cr-propagation). `git rev-parse --show-toplevel` = `.claude/worktrees/crprop-e1`; `git branch --show-current` =
`worktree-crprop-e1`; `git status` clean at start; base `4a58be50` = integration HEAD (decision D10, not
`origin/main`); prerequisites B1 (merge 3ed1e89e), C2 (merge 9f17775c), A4 (merge 0ee4c914) and C1 (merge 099d1d22)
are ancestors of HEAD (`git merge-base --is-ancestor`). No batch client: runs go through
`skills/hep-computing/scripts/local_partition.py` on E2 (decision D6), at most 4 USINE processes at once.

**Set-up and criteria, fixed before any loop run (R9).** Free parameters 5 (`D0_cm2_s` 1e28–1e29 on a log axis,
`delta` 0.3–0.8, `eta` −1.5–1.5, `V_A_kms` 0–100, `V_c_kms` 0–30; `L_kpc` 4 and every other transport field fixed at
the provider's `DEFAULT_TRANSPORT`, harmonized-v1 with the isotopic ILLUSTRATIVE cross sections, sent in full in
every request). Q9: N₀ = 10 × 5 = 50 → 64 (power of 2), k = 64/10 → 6. Sobol design scrambled, seed 20261028;
d_min = smallest pairwise distance of the design in the unit cube. Observable B/C, 20 log rigidity bins 2–1000 GV.
Synthetic data: the provider's B/C at the truth point (`D0_cm2_s` 3e28, `delta` 0.5, `eta` 1, `V_A_kms` 30,
`V_c_kms` 5; Asimov, labelled synthetic) with an ILLUSTRATIVE covariance (statistical 1.5% (R/10 GV)^0.4,
uncorrelated; systematic 2% with Gaussian correlation length 0.3 in log10 R). Hold-out: 16 points of the round-0
approximate 95% posterior region, never trained on.
- E1-1: every design point has a computational-run record (USINE run folder under `$CRPROP_OUT/e1/runs/`, its id in
  `design.json`); failures are recorded with their reason; more than 5% failed design points stops the WP.
- E1-2: with `--forced-max-rounds-test` (both termination thresholds 0, early stops off) the loop ends with status
  `max-rounds` after exactly 5 rounds and its reason names the unmet criteria and the failing bins.
- E1-3: `python3 tools/check_packaging.py` exits 0 and only the driver, the design file, the summaries (per-point
  hashes, computational-run references, no training values) are committed, each ≤ 2 MiB.
- Termination (r3 §E1 with E2's criteria, placeholder emulator): on every hold-out point Δχ² = bᵀC⁻¹b ≤ 1 (E2-1) and
  |b_i| ≤ 0.2 σ_i^stat in every bin (E2-2). Limits: 5 rounds; early stop when the largest hold-out |b_i|/σ_i^stat
  falls by less than 10% in 2 consecutive rounds, or every pick lies closer than d_min to a training point; cost cap
  1500 USINE evaluations for E1 (orchestrator), checked before every batch.

**Results (2026-10-28).** Standard run: status `early-stop-min-distance` at round 3 (all 6 picks within d_min =
0.2231 of a training point, not run); best emulator after round 2 meets E2-1 (largest hold-out Δχ² 0.225) but not
E2-2 (largest |b_i|/σ_i^stat 1.18, failing bins 0–4, 2–7 GV). Placeholder emulator per round (training points,
largest hold-out Δχ², largest |b|/σ^stat): round 0 (64) 7.69, 3.58; round 1 (70) 0.79, 1.36; round 2 (76) 0.225,
1.18. Emulator best fit after round 2 (before round 3's picks): `D0_cm2_s` 2.98e28, `delta` 0.501, `eta` 1.13,
`V_A_kms` 21.6, `V_c_kms` 6.0 (truth 3e28, 0.5, 1, 30, 5; χ² 0.004; the V_A–V_c–eta direction is weakly constrained
by B/C alone, as expected). The forced test (E1-2) ran the full 5 rounds: rounds 3–5 add 18 points and the largest
|b|/σ^stat stays at 1.27, 1.22, 1.22 — the plateau confirms the early stop and shows the placeholder (radial-basis
interpolation with jackknife error) does not reach 0.2 σ^stat in the low-rigidity bins of this posterior.

| ID | Result | Evidence |
|---|---|---|
| E1-1 | passed: 64/64 design points ok (0 failures, limit 5%); every one of the 111 USINE evaluations (design 64, truth 1, hold-out 16, additions 30) has a computational-run record that `contracts/validate.py` accepts; ids and point/output hashes in `design.json`, `summary.json`, `forced-test.json` | `$CRPROP_OUT/e1/acceptance/E1-1.txt` |
| E1-2 | passed: `--forced-max-rounds-test` ends with status `max-rounds` after 5 rounds, reason "maximum of 5 rounds reached without both E2 criteria (E2-1 met: False, E2-2 met: False; termination thresholds dchi2 <= 0.0, …) best emulator = after round 5, failing bins […]"; no limit exceeded | `forced-test.json`, `$CRPROP_OUT/e1/acceptance/forced-test.txt` |
| E1-3 | passed: `tools/check_packaging.py` exit 0; committed only the driver, `design.json` (38 kB), `summary.json` (51 kB), `forced-test.json` (64 kB), no training values | `$CRPROP_OUT/e1/acceptance/E1-3.txt` |

**Budget (D7, A1.8).** 114 USINE evaluations in E1: 111 in the loop runs (tally `$CRPROP_OUT/e1/tally.json`; reruns
of the standard and forced runs are answered from the provider cache) plus 1 probe and 2 smoke runs; well under the
orchestrator's E1 cap of 1500. CPU about 0.1 core-hours (about 1–3 s per USINE run, 4 processes at once).

**What E2 must replace.** The placeholder emulator (`JackknifeInterpolationEmulator`: scipy radial-basis
interpolation of ln(B/C), jackknife spread as its error) by the hep-ml emulator with an `ml-artifact`
(`training_domain`, `extrapolation_policy`, `regression_validation`, domain by `DomainModel`); the candidate-cloud
approximation of the 95% posterior region (global Sobol cloud plus a Laplace-shaped local cloud, Δχ² ≤ χ²₀.₉₅(5)) by a
posterior through the E2b emulator provider; the termination hold-out and the ILLUSTRATIVE synthetic covariance by
E2's hold-out and the data covariance. Observed for E2: the design's d_min (0.22 in the unit cube) is large compared
with the posterior region, so the min-distance early stop fires after two rounds of posterior-focused additions; a
better emulator, not more points of this placeholder, is what the low-rigidity bins need. Labels: synthetic,
unvalidated (ILLUSTRATIVE cross sections; USINE translator limits of B1, fixed by B1X in parallel).

## CRPROP-A1R — 2026-10-28 (environment E2)

Work package A1R (DRAGON2 convention row and reacceleration conventions; decision A1.9, escalations 6 and 9) of the
cr-propagation r4 workflow; extends r3 §A1.

Environment: E2 (macOS arm64 workstation), Python 3.13.2 (miniconda) for the module and tests (standard library);
the scratch derivation checks used the E2 venv (Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1). r3 §0.3 checks: toplevel
`<repo>/.claude/worktrees/crprop-a1r`, branch `worktree-crprop-a1r`, status clean at start; base exception (decision
D10): base is the integration HEAD `6bfd1117`, not `main`; prerequisites A1 (`5d5fd918`) and ENV (`7d5c6934`, dispatch
2 `cbb7907f`) are ancestors of HEAD. Sources read (not run): DRAGON2 at `<TOOL_HOME>/src`, commit cd588707 (clean);
USINE V3.5 at `<TOOL_HOME>` (gitlab, commit fb53006d, tag V3.5). No DRAGON2 or USINE run was made (A1.8 tally: 0).

Criteria (frozen entries A1R-1 to A1R-3 of `acceptance.json`, written before the work): A1R-1 the dragon2 convention
and the page row match cd588707 with file:line, the repo spec D_X1_R60_UG (etaT = 1) converts, a test pins it; A1R-2
the zone conversion and the D_pp normalisations of both codes stated from the code, each exact or approximate with a
bound; A1R-3 reacceleration round trips within 1e-12 relative, an approximate conversion returns its bound.

| Item | Result | Evidence |
|---|---|---|
| A1R-1 | `dragon2` = D0 beta^etaT (rho/DiffRefRig)^delta, `D0_1e28` in 1e28 cm^2/s, etaT and DiffRefRig free and required (src/diffusion.cc:150; src/grid.cc:108-110 per-nucleon momentum; src/crevolutor.cc:121-122 the (A/\|Z\|)^delta factor; src/input.cc:444-461, missing value -1 at src/input.cc:55-59); D_X1_R60_UG converts `exact` to canonical (3e28 cm^2/s at 1 GV, eta 1) and to galprop (3 x 4^0.5 at 4 GV) | `Dragon2Convention` (5 tests), page row parsed by `ConventionTable` |
| A1R-2 (b) | D_pp D = c V_A^2 p^2 / (delta (4 - delta) (4 - delta^2) w): DRAGON2 cd588707 Ptuskin94 c = 1, no w; Ptuskin03 c = 4/3 (src/galaxy.cc:279-284; enum src/include/constants.h:146-149 gives Ptuskin94 = 0, and the 4/3 is applied for value 1; the comment of src/include/input.h:156 says otherwise); whole halo (src/galaxy.cc:308, 324). USINE V3.5 c = 4/3 (inputs/init.Model1D.par:90, init.Model2D.par:97), energy terms in the thin disc only (src/TUModel1DKisoVc.cc:400-416, src/TUModel2DKisoVc.cc:445-463). Constant ratio exact (3/4 for Ptuskin94 vs USINE). Papers cited in the code not re-read | `test_momentum_diffusion_constants` |
| A1R-2 (a) | derived (1D slab, D independent of z, no convection, disc source and destruction): first-order disc-flux weights h L (thin disc) and L^2/3 (whole halo), so V_A,disc = V_A,halo sqrt(L/(3h)) at equal c and w; P1's "about sqrt(L/h)" gives a third of the first-order effect. Approximate: second-order terms differ by (1 + lam)/5, lam = h Gamma L / D (the returned bound) | independent oracle `slab_coefficients` (L/3 within 4e-7; mismatch 0.2/0.3/0.6/2.2 at lam 0/0.5/2/10); scratch 2D (z, p) solve: at a 1% effect the converted halo run matches the disc run within 1e-4, with sqrt(h/L) it gives a third (`$CRPROP_OUT/a1r/derivation/`) |
| A1R-3 | 4 V_A x 20 ordered pairs of the 5 conventions round trip within 1e-12; same zone `exact` (bound 0), across zones `approximate` with bound (1 + lam)/5; a zone change without lam is rejected | `test_round_trips`, `test_cli` |

Effect on the campaign: with USINE V_A,disc = 50 km/s (L = 4 kpc, h = 100 pc), DRAGON2 Ptuskin94 needs V_A,halo =
50 sqrt(4h/L) = 15.8 km/s for the same first-order effect; D1's translator used 50 sqrt(h/L) = 7.9 km/s (a quarter of
the D_pp), and B1's whole-halo branch uses sqrt(L/h). Neither translator is in A1R's files.

Not done in A1R: convection, a radial boundary and energy losses in the zone factor (the conversion says so); the
operator form beyond the D_pp coefficient was not re-derived; the translators of B1 and D1 were not changed.

Rework round 1 (wave-3 finding): `tests.skills.hep_theory.test_cosmic_ray_phenomenology_th13` requires the phrase
`D_pp D_xx` in the propagation-codes section; A1R had written `D_pp D`. The reacceleration bullet of
`cosmic-ray-phenomenology.md` now reads `D_pp D_xx = c V_A^2 p^2 / (...)` (content otherwise unchanged); the page is
24574 B (limit 24576 B; heading and `about 1` shortened to make room), `docs/reference-inventory.*` regenerated. Passing:
the Th13, transport_conventions, routing_tables and documented_output_claims tests, reference_inventory --check.

## CRPROP-B1X — 2026-10-28 (environment E2)

Work package B1X of the cr-propagation r4 campaign (decision A1.7, escalation 8): a high break in
`extension.transport`, and USINE's own cross-section files with data-normalised abundances in `usine_translate.py`.

**Criteria and tolerances, fixed before any comparison (R9).** The frozen entries B1X-1 to B1X-5 (acceptance.json,
added by the orchestrator on dispatch): B1X-1 a high break validates, a half-specified one is refused with a named
error, every committed theory-spec keeps its outcome default and `--strict` (the A2-1 comparison); B1X-2 and B1X-3 a
transport block matching USINE's shipped `inputs/init.TEST.par` (Model1DKisoVc), run through the translator, reproduces
the B/C table of that example run in place within relative 1e-6 on the common nodes, the live tests not skipped; B1X-4
no transport field silently ignored or defaulted; B1X-5 no USINE file or copy committed. Nothing was loosened.

**Environment (r3 §0.3, base exception D10).** E2 = E-crprop (macOS 27.2 arm64), Python 3.13.2 (miniconda), USINE V3.5
(commit fb53006d, Apple clang 21.0.0, ROOT 6.38.04; `bin/usine` sha256 1d444720…) through `HEP_USINE_BIN`,
`HEP_USINE_DATA`, `USINE`. `git rev-parse --show-toplevel` = `.claude/worktrees/crprop-b1x`; branch
`worktree-crprop-b1x`; status clean at start; base `e97680cf` = integration HEAD (decision D10, not `origin/main`);
prerequisites A2 and B1 are ancestors of the base (`git merge-base --is-ancestor`); env-usine is the ENV build above.

**Contracts (still CV-CRPROP 3.14.0, gate `CRPROP_FROM`, no bump, no new gate).** New fields: break `delta_above`
(slope above a high break; the canonical table's `delta_below` mirrored), `geometry.local_bubble_radius_kpc` (USINE's
`rhole`: changing it from 0.2038 to 0 kpc moves the shipped example's B/C by up to 3.9e-4, so it cannot be left to the
translator) and an injection item's `eta` (source beta exponent; USINE's `eta_s`, -1 in the example). All pass
`tools/check_naming.py` with `naming_known_gaps.json` unchanged (N13 has no extractor in this repository:
`extract_names.py` reads N1-N6, N16). New rules from `CRPROP_FROM` (else `--strict`): `theory.transport_break_incomplete`
(a low break needs `R_break_gv`, `delta_below`, `s`; a high break `R_break_gv`, `delta_above`, `s`; the other kind's
slope is refused) and `theory.transport_break_kind_unknown`. Fixtures from `tests/contracts/make_fixtures.py`: one
positive, two negative; `gate_verdicts.json` regenerated with only those three rows added. A2-1 rerun: all 29 committed
theory-specs (contracts/fixtures, examples, profiles, tests) have identical findings, default and strict, under the base
and the new validator; only the three new fixtures differ (`$CRPROP_OUT/b1x/acceptance/a21-*.json`).
`transport_conventions.py` evaluates the high break (K0 <-> K10 approximate with a bound, a half-specified break
not-convertible).

**High-break form, from USINE's own files.** USINE reads K as a formula from its initialisation file; its C++ source
fixes no break form. The shipped files carry one: `inputs/init.TEST.par` line 133 (also `init.Model1D.par` line 89,
`init.Model2D.par` line 96, `doc/tutorial_update_models.rst` line 99):
`beta^eta_t*K0*Rig^delta*(1+(Rig/Rbreak)^(Deltabreak/sbreak))^(-sbreak)`, so `delta_above` = delta - Deltabreak. No
shipped file or source line has a low break, so USINE does not settle the "usine" low-break form of
`transport_conventions.py` against Weinrich et al. 2020a (known issue stays open).

**Translator (`usine_translate.py`).** High break: `*(1+(Rig/Rh<i>)^((delta-dh<i>)/sh<i>))^(-sh<i>)`. USINE's own inputs:
`production_set`/`inelastic_set` `usine:<path>` and `sources.abundances` `data-normalised usine:<data file>
<elements>:<experiment>@<E_k/n>[;...]`, read in place from `HEP_USINE_DATA` (refused with exit 3 and a message naming
`HEP_USINE_DATA` and the files when it is unset); network 1H to `species.network_top`; NormList on the data file;
targets H and He with He = `He_to_H_number` (HI + HII + 2 H2); HII and H2 from `gas.model`; electron-capture decay
with `ec_treatment` `laboratory-half-life`; `--ekn-grid` for an explicit grid. With USINE's own inputs the Kpp line uses
the factor written in USINE's shipped Kpp (1.022712e-3, init.TEST.par line 134), 1.6e-7 below the IAU/Julian value:
with the derived factor one of 33 B/C nodes flipped its sixth digit (4.7e-6 relative); with USINE's factor all nodes
agree (recorded as a substitute; the ILLUSTRATIVE runs keep the derived factor). Every chart BETA half-life in the
network is compared with NUBASE2020 (14C differs by +0.5%, recorded; 10Be still refused above 1e-3). B1X-4: unknown
keys refused; every default (geometry kind, h, R, rhole, eta, R0, breaks, V_A, w, zone, relation, V_c, gradient,
losses, decay items, inelastic set, species) and every unused field (family, free, sources.spatial, diffusion.form,
ghost_threshold, ILLUSTRATIVE abundances and set names, zone/relation with V_A = 0, decay items with decay off) is
recorded in `substitutes`; `species.network_top` and `species.isotopic` must match an ILLUSTRATIVE set (Ni-64 refused)
and set the network with USINE's files. Test `test_no_field_silently_ignored` changes and removes every field of four
recorded specs and requires a changed input file, a changed record or a refusal. The whole-halo V_A factor stays
sqrt(L/h) at first, then replaced after A1R (addendum below). The reader counts 14C in carbon.

**Records.** `input_manifest` now holds `committed_form_sha256` (the placeholder form committed under `inputs/`) next
to the as-run `sha256`, and USINE's own files read in place (hashed, never copied). The seven B1 records gained
`committed_form_sha256` and `input_manifest_note` without a rerun: their generated inputs are unchanged (offline render
test, and the live B1-2 rerun passes), their `notes` keep B1's substitutes.

**Results (final HEAD).**

| ID | Result | Evidence |
|---|---|---|
| B1X-1 | passed: 23 tests (9 B1X), positive and both negative fixtures exercised, gating native from CRPROP_FROM | `$CRPROP_OUT/b1x/acceptance/B1X-1-contracts.txt`, `a21-*.json` |
| B1X-2 | passed: translator run of `specs/b1x-init-test.json` vs `usine -l inputs/init.TEST.par` run in place: B/C on 33/33 common nodes, max relative deviation 0 on E_k/n and on rigidity (identical tables); live test not skipped | `B1X-2-3-live.txt`, `runs/b1x-init-test`, `runs/shipped-init-test` |
| B1X-3 | passed: the same run reads `XS_NUCLEI/sigProdGALPROP17_OPT12.dat`, `XS_NUCLEI/sigInelTripathi99+Coste12.dat`, `crdata_crdb20170523.dat` in place; no run or committed file has the sha256 of any USINE input; refused without `HEP_USINE_DATA` | as above, `UsineB1XOffline.test_missing_usine_data_is_refused` |
| B1X-4 | for the verifier: field-by-field test above; file:line in the report | `test_no_field_silently_ignored`, `test_defaults_are_recorded` |
| B1X-5 | committed: specs, the translator's own `usine.init.par` (placeholders; regenerates byte-identically, test), USINE output tables and records; no USINE source or input file | `test_renders_to_the_recorded_inputs`, live hash scan |
| B1-2 | still passed: the seven B1 runs rerun live reproduce their outputs | `B1X-2-3-live.txt` |

Not translated, since they do not affect B/C: the example's antinuclei and tertiaries, the hydrogen slope 2.3 (one
shared slope 2.268922), `crdata_dummy.dat`, NormList elements above Si and the display settings. USINE runs:
about 37 (6 development and probe runs, 1 rerecord, two live acceptance invocations of about 15 each).
Checks: static part of `run_all_checks.py`, naming, wiring, layering, packaging, `workflow_check.py` diff, gaps and
acceptance on the final HEAD; ruff and mypy (CI pins) on `contracts/`; ALL-3 deferred to the wave run (A1.5).
Software and numerical-consistency checks; no comparison with data.

**Addendum (2026-10-28, rebase onto integration 2ae3063b, which contains A1R e5ecbd64).** Orchestrator decisions:
keep the mode-dependent Kpp factor (USINE's literal 1.022712e-3 only with USINE's own inputs, the IAU/Julian value
with the ILLUSTRATIVE sets, no rerun of the B1 runs). Whole-halo V_A is now converted by
`transport_conventions.py reacceleration --from whole-halo --to thin-disc` (same c and w; called as a subprocess, R1),
V_A,disc = V_A,halo sqrt(L/(3h)) at first order, `approximate` with `relative_error_bound` (1 + lam)/5 on the
second-order term; the translator computes lam = h Gamma L / D at every species and node of the run's grid (Gamma =
n_gas sigma_inel beta c with the set's inelastic cross sections, D from the K formula, atomic-mass-unit kinematics)
and passes the largest, recorded with the nuclide and E_k/n; with USINE's own cross sections a whole-halo V_A is
refused (their inelastic files are not read). Committed runs with whole-halo V_A: only B1's `b1-slab-all-items`
(none of B1X's, B3's under `b3/` or E1's under `e1/`, which uses the provider's thin-disc DEFAULT_TRANSPORT). Its
thin-disc V_A changes from 35.35533906 to 20.41241452 km/s (lam_max 0.561 at 16O, 1.995 GeV/n; bound 0.312; convection
on, recorded as outside the conversion's assumptions): rerun live, `inputs/`, `outputs/`, record and its
`usine-results.json` entry regenerated (B/C bins change by at most 0.63%, 10Be/9Be by at most 0.47%; first B/C bin
0.07760 -> 0.07776); the other six B1 runs and both B1X runs are unchanged. Checks rerun on the rebased HEAD (report).

## CRPROP-D1 — 2026-10-28 (environment E-crprop)

Work package D1 of the cr-propagation r4 campaign (r3 §D1 and §D1b folded together, r4 §6): DRAGON2 physics items,
one at a time, each with its `harmonized-v1-<item>.json`, and the cr-provider/1 entrypoint `dragon2_provider.py`.

**Environment (r3 §0.3, base exception D10).** E-crprop (E2 host, macOS 27.2 arm64, Python 3.13.2; DRAGON2 cd588707,
the serial build of 2026-10-15, located through `HEP_DRAGON2_BIN` and `HEP_DRAGON2_DATA`). Checked before the first
edit: `git rev-parse --show-toplevel` = `.claude/worktrees/crprop-d1`; `git branch --show-current` =
`worktree-crprop-d1`; `git status` clean; base = integration HEAD `566bfd1e` (not `origin/main`, decision D10);
prerequisite merge commits A1 `5d5fd918`, A2 `a3c880f8`, C1 `099d1d22`, B2 `81cb2ce0` are ancestors of HEAD
(`git merge-base --is-ancestor`, exit 0). `env-usine` is absent: B1 has not run.

**Criteria and tolerances, written before any DRAGON2 run of this work package (R9; frozen in `acceptance.json`, never
loosened).**

| ID | Criterion | Tolerance |
|---|---|---|
| D1-1 | For each item with a closed form (convection: V_c = 10 km/s constant, dV_c/dz = 0; decay: ¹⁰Be → ¹⁰B with the NUBASE2020 half-life), the DRAGON2 run with that item on is compared with the B2 closed form (`profiles/theory/cr-secondary-ratio/scripts/convection_decay.py`) with the same item on, fed with the same run's ¹²C and ¹⁶O fluxes per E/n as parents, the same D0, δ, η, R0, L and the same isotopic ILLUSTRATIVE production cross sections, and h n_H = half of DRAGON2's gas column at the observer (h = 0.1 kpc). Quantities: B/C = (¹⁰B + ¹¹B)/(¹²C + ¹³C + ¹⁴C) in 16 log-uniform rigidity bins over 2–1000 GV (isotopes summed at equal rigidity, P3; ratio of bin integrals, P2) and ¹⁰Be/⁹Be in 12 log-uniform E/n bins over 0.05–10 GeV/n (ratio of bin integrals). Verdict per item and observable: max over bins of abs(DRAGON2 / reference − 1) | 0.03 (3%) |
| D1-1 (items without a closed form) | Reacceleration and energy losses: the reference is USINE under the same item file (r3 §D1); not compared until B1 is merged (fallback of `workflow.json`) | 0.03 when compared |
| D1-1 diagnostic (no verdict, no tolerance) | The item effect, [DRAGON2(item on) / DRAGON2(item off)] / [closed form(item on) / closed form(item off)], per bin, with the item-off run `harmonized-v1-isotopic`; it separates the item from the fixed differences of the baseline (helium target, inelastic cross sections, 2D gas and boundary) | reported only |
| D1-2 | Every item (convection, decay, reacceleration, losses) and the item-off baseline has a recorded run: run spec, computational-run record (input and output SHA-256, command, environment) and output under `tests/adapters/fixtures/cr_propagation/dragon2/` | all five present |
| D1-PRV-1 | `dragon2_provider.py` passes C1's conformance mixin (`tests/core/provider_conformance.py`), live on E-crprop (skipped where DRAGON2 is not installed) | all checks pass |
| D1-PRV-2 | Single-shot and `--serve` responses have the same sha256 after removing `elapsed_s` and time stamps | equal sha256 |

**Results (2026-10-28, E-crprop; DRAGON2 runs under `$CRPROP_OUT/d1/`, outside the repository; host load 30-60 from
other workers, so wall times are not cost numbers).** Runs: five item runs translated by `dragon2_run.py
--from-transport` from `tests/adapters/fixtures/cr_propagation/specs/harmonized-v1-{isotopic,convection,decay,
reacceleration,losses}.json` (2D, radius 20 kpc, dR 0.5 kpc, dz 0.02 kpc, Z 4-8, 0.04-2000 GeV/n with factor 1.2,
injection R^-2.3 for every species, production table = the profile's isotopic ILLUSTRATIVE set for ¹²C and ¹⁶O),
575-710 s each, four at a time; specs, de-identified computational-run records and outputs in
`tests/adapters/fixtures/cr_propagation/dragon2/`. Substitutes recorded in every spec (§5.5): BronfFerr gas instead
of uniform n_H = 1 cm⁻³ (DRAGON2 cd588707's `Uniform` gas is not implemented: gas.cc writes -1), DRAGON2's fixed
helium (He/H 0.11 with its He_to_H_CS_ratio scaling) instead of 0.1, no thin-disc parameter, DRAGON2's own inelastic
cross sections, sources OneRing 0-20 kpc (the source distribution D1 chose), V_A thin disc 50 km/s run as whole-halo
50 sqrt(0.1/4) = 7.9 km/s (approximate, P1), ionization and Coulomb losses switched together; decay uses the
NUBASE2020 half-lives of ¹⁰Be and ¹⁴C written into a copy of `isotope_list.dat` (DRAGON2 ships ¹⁰Be at 1.51 Myr; the
run log confirms 1.38697 Myr).

| ID | Result | Evidence |
|---|---|---|
| D1-1 convection | **fail** for B/C: max abs(DRAGON2/reference − 1) = 0.148 (1.076-1.148 over 2-1000 GV); **pass** for ¹⁰Be/⁹Be: 0.022 | `dragon2/d1-item-results.json`; `D1Items.test_closed_form_comparison_matches_the_record` |
| D1-1 decay | **fail** for B/C: 0.144 (1.069-1.144); **fail** for ¹⁰Be/⁹Be: 0.152 (0.848-1.006, below 1 GeV/n) | same |
| D1-1 attribution (B/C) | the item-off run already gives 1.069-1.143: DRAGON2's helium target multiplies the production cross sections by 1.144-1.174 at these energies; with it divided out DRAGON2 / closed form at equal E/n is 0.93-1.01 (helium on destruction, DRAGON2's inelastic cross sections and the 2D geometry not separated; as in CR-PROPAGATION-DRAGON2-UNITS). Item effect (diagnostic): convection 1.001-1.007, decay 1.000-1.001 | `$CRPROP_OUT/d1/helium_attribution.txt`; `d1-item-results.json` `attribution` |
| D1-1 attribution (¹⁰Be/⁹Be, decay) | the reference is a thin disc, while DRAGON2's gas layer (H2 59 pc, HI 115 pc) is comparable with the ¹⁰Be decay length of about 0.3 kpc at 0.1 GeV/n. A 1D finite-difference diagnostic (source on DRAGON2's gas profile at 8.3 kpc against the same column in a thin disc) gives surviving-fraction ratios 0.843, 0.868, 0.889, 0.909 in bins 2-5 against the DRAGON2 item effects 0.873, 0.867, 0.888, 0.918; not attributed: bin 1 (0.05-0.078 GeV/n: DRAGON2 0.969, diagnostic 0.816) and a +1% residual above 1 GeV/n. The failure belongs to the thin-disc reference's validity (B2 excludes decay inside the disc), not to a defect shown in DRAGON2 | `$CRPROP_OUT/d1/thick_gas_decay.py`, `.json`; `d1-item-results.json` |
| D1-1 reacceleration, losses | **not run**: no closed form; the reference is USINE, waiting for B1 (`env-usine` absent). Their runs are recorded | `D1_reacceleration`, `D1_losses` fixtures |
| D1-2 | **pass**: five runs, each with spec, record (validates; exit 0; output and XML SHA-256 match; DRAGON2 commit in tools; no home path) and output; the specs are re-derived from the item files by the translator in the test | `D1Items.test_runs_are_recorded_and_translated_from_the_item_files` |
| D1-PRV-1 | **pass** live (`HEP_DRAGON2_LIVE_TEST=1`): mixin checks declared, single-shot, serve, prv-2, unsupported-want, out-of-domain, outside-allowed, unregistered, runner-agrees; responses valid against `cr_provider.json` with the `theory:cr-secondary-ratio` vocabulary; 4 tests in 353 s | `$CRPROP_OUT/d1/acceptance/D1-PRV-1.unittest.log`, `D1-PRV-conformance.json` |
| D1-PRV-2 | **pass**: single-shot and `--serve` responses equal in sha256 after removing `elapsed_s` (check prv-2) | same |
| Numerical tolerance of the provider | 2.2e-3: largest relative change of five B/C bins (ekn 10-100 GeV/n, rigidity 2-1000 GV) when dz is halved and the energy factor goes 1.2 → 1.1; declared 0.01 | `$CRPROP_OUT/d1/convergence/convergence.json` |

Open issues. (1) `transport_conventions.py` gives DRAGON2 the form D0 (p/p0)^δ with η = 0, but DRAGON2 cd588707
(`diffusion.cc`, type Constant) computes D0 β^etaT (ρ/DiffRefRig)^δ in rigidity, so a canonical spec with η = 1 maps
one to one (D1's translator does this and does not call the convention table); the convention table row in
`cosmic-ray-phenomenology.md` and the module need a hep-theory fix (outside D1's files). (2) DRAGON2's `Uniform` gas
is not implemented in this commit, so harmonized-v1's uniform gas cannot be run without a code change. (3) The
B/C absolute comparison cannot meet 3% with DRAGON2's fixed helium target and own inelastic cross sections unless the
reference includes them; the frozen tolerance is not changed. Checks: `run_all_checks.py --part static --jobs 4`
31/31 pass; impacted tests (`tests.adapters.test_cr_propagation`, `tests.skills.test_cli_robustness`,
`tests.adapters.test_adapter_declarations`, `tests.tools.test_provider_registry`, `tests.core.test_provider`,
`tests.core.test_provider_conformance_mixin`) pass; `check_naming.py`, `check_wiring.py --since 566bfd1e` pass;
ALL-3 (full `run_all_checks.py`, `check_relocation.py`) deferred to the wave run (decision A1.5).

**Addendum: items without a closed form (2026-10-28, after B1 merged; rebased onto integration HEAD `3d5a6295`, which
contains B1 `2d451e87`).** The rebase left the translator and reader unchanged apart from the provider reading its
entry from the `provider` list of `adapter.json`, so no DRAGON2 run was repeated. Reference: B1's
`usine/usine-results.json` (USINE V3.5 Model2DKisoVc, the same `harmonized-v1-<item>.json` on the same 16 rigidity and
12 E_k/n bins; thin disc, uniform neutral gas n_H = 1 cm⁻³ with h = 0.1 kpc, no helium, ILLUSTRATIVE energy-independent
inelastic cross sections, V_A 50 km/s in the thin disc). Like with like for losses: USINE's reference has ionization
only (its Coulomb term acts on HII, zero here), and DRAGON2's Coulomb term acts on BronfFerr's HII, also zero.

| ID | Result | Evidence |
|---|---|---|
| D1-1 reacceleration | **fail**: B/C max abs(DRAGON2/USINE − 1) = 0.381; ¹⁰Be/⁹Be 0.041. Item effect on B/C in the lowest bin: DRAGON2 1.072 against USINE 1.402 (DRAGON2 ran the r3 P1 whole-halo equivalent 50 sqrt(0.1/4) = 7.9 km/s with its Ptuskin94 D_pp; the zone conversion is approximate without a bound, and the D_pp normalizations are not separated) | `dragon2/d1-item-results.json` `usine_items`; `D1Items.test_usine_comparison_matches_the_record` |
| D1-1 losses | **fail**, not a physics comparison: DRAGON2 with eloss_flag 1 suppresses even primary ¹²C by 1e-4 (0.04 GeV/n) to 9e-3 (1.6 TeV/n) and B/C by about 1e-3 at every energy (max deviation 0.999); the same with dz = 0.1 kpc (diagnostic runs `$CRPROP_OUT/d1/diag-losses/`). USINE's ionization changes B/C by at most 13% at 2 GV. Cause in DRAGON2 cd588707's nuclear energy-loss path not located: open issue; the recorded run stays as evidence of the behaviour | same |
| D1-1 offsets against USINE (item-off) | B/C 1.27-1.39, ¹⁰Be/⁹Be 0.95-0.98: DRAGON2's helium target (×1.14-1.17 on production), its gas column at 8.3 kpc (9% above USINE's 2 h n_H) and its own inelastic cross sections; not separated further. For comparison, the convection and decay items against USINE give item effects within 0.9% (convection) and, for ¹⁰Be/⁹Be with decay, up to 11% (both 2D codes against each other: thin disc in USINE, DRAGON2's gas layer) | same |

D1-1 summary over the four items: pass only for ¹⁰Be/⁹Be with convection; fail for all others (tolerance 3%, frozen;
escalation 5 open for the closed-form items). New open issue (4): DRAGON2's energy-loss run.

**Dispatch 2 (2026-10-28; decisions A1.9, A1.10; rebased onto integration HEAD `2ae3063b`, which contains `e5ecbd64`
with A1R, B3, C2, E1).** D1-1 stays frozen and is recorded as **failed and superseded** for D1's verdict by D1-1a
(item effect, ratio with the item over ratio without it, within 3%) and D1-1b (absolute offsets reported and
attributed, no tolerance). USINE reference: `usine/usine-results.json` as committed in `9274db92` (B1), unchanged on
`2ae3063b`.

*Reacceleration.* The translator now calls hep-theory's `transport_conventions.py reacceleration` as a subprocess
(an adapter imports no skill, R1): a thin-disc V_A is USINE's Seo-Ptuskin convention (D_pp constant 4/3), DRAGON2 runs
Ptuskin94 (constant 1, whole halo; Ptuskin03 not used), so 50 km/s becomes 50 sqrt(4 h / L) = 15.81 km/s at
L = 4 kpc, h = 100 pc, status approximate, relative error bound 0.517 on the second-order term (destruction/escape
ratio 1.586 at 0.04 GeV/n, `escape_ratio_estimate`: n_H 1 cm⁻³, 310 mb). The item was rerun live.

*D1-L (losses), diagnosis in 5 DRAGON2 runs (limit 6; `$CRPROP_OUT/d1/diag-losses/`).* (1-2) dispatch 1: the
suppression is unchanged with dz = 0.1 kpc. (3-4) the same configuration with DRAGON2's `Galprop` gas (HII > 0),
losses on and off: physical (¹²C −74% and B/C −58% at 0.1 GeV/n, both < 0.1% above 50 GeV/n). (5) protons added
(Zmin 1): DRAGON2 crashes at start (exit −11), not pursued. Cause: BronfFerr writes n_HII = 0 (gas.cc), and the
nuclear branch of `TCoulombLoss` (eloss.cc:118-120, `coullog = -log(... n_HII ...)/2`, gas.back() = HII by
galaxy.cc:521-523) diverges there (the lepton branch guards n > 0). So it comes from the configuration and is fixed in
D1's files: the translator runs losses on Galprop gas and refuses losses on gas without HII
(`D1Items.test_translator_records_what_dragon2_cannot_express`, `Dragon2ProviderOffline.test_losses_run_on_gas_with_
ionized_hydrogen`); the provider inherits it. Upstream issue draft (not posted, two items: this divergence and the
Ptuskin94/Ptuskin03 enum, galaxy.cc:279-284 vs constants.h:146-149): `$CRPROP_OUT/d1/dragon2-upstream-issue-draft.md`.
The losses item was rerun on Galprop gas together with its item-off run `D1_losses_off` (isotopic item on Galprop gas).

| ID | Result | Evidence |
|---|---|---|
| D1-1 | **failed, superseded (A1.9)**: absolute deviations 14-15% (B/C against the closed form), 38-77% (B/C against USINE), up to 16% (¹⁰Be/⁹Be) | `dragon2/d1-item-results.json` `verdicts_D1_1_superseded` |
| D1-1a convection | **pass**: item effect within 0.73% / 0.44% (B/C / ¹⁰Be/⁹Be) against the closed form, 0.85% / 0.60% against USINE | `verdicts_D1_1a`; `D1Items.test_closed_form_comparison_matches_the_record`, `test_usine_comparison_matches_the_record` |
| D1-1a decay | **fail**: B/C passes (0.13% closed form, 0.02% USINE); ¹⁰Be/⁹Be fails (13.3% closed form, 11.3% USINE) below 1 GeV/n: DRAGON2's gas layer (59/115 pc) against the thin disc of both references; a 1D thick-gas diagnostic reproduces the DRAGON2 effect within about 1% in bins 2-5; lowest bin and a +1% residual above 1 GeV/n unattributed | same |
| D1-1a reacceleration | **fail**: B/C effect 1.322 (DRAGON2) vs 1.402 (USINE) in 2-2.95 GV and 1.183 vs 1.122 in the next bin (max 5.7%); ¹⁰Be/⁹Be up to 4.4%. Within the approximate first-order conversion (bound 0.517 on the second-order term) and the whole-halo vs thin-disc spatial difference; not separated | same |
| D1-1a losses | **fail**: B/C effect 0.815 vs 0.867 in the lowest bin (max 6.1%); ¹⁰Be/⁹Be passes (1.7%). Likely causes, not quantified: DRAGON2's Coulomb loss on Galprop's HII (USINE's reference is ionization only) and Galprop's neutral column differing from USINE's 2 h n_H | same |
| D1-1b | offsets reported for every item and reference in `d1-item-results.json` (`dragon2_over_closed`, `dragon2_over_usine`) with attributions: item-off B/C 1.07-1.14 vs the closed form (helium target ×1.144-1.174; residual 0.93-1.01 unattributed: helium on destruction, inelastic cross sections, 2D gas); item-off B/C 1.28-1.39 and ¹⁰Be/⁹Be 0.95-0.98 vs USINE (helium, gas column +9%, inelastic cross sections; split unattributed); losses runs on Galprop gas B/C 1.50-1.77 vs USINE (gas model, plus the above; unattributed beyond these causes) | `attribution` |
| D1-L | **fixed in the configuration** (see above); losses kept in D1-1a | file:line above |
| D1-2 | pass: six runs recorded, specs re-derived by the translator in the test | `test_runs_are_recorded_and_translated_from_the_item_files` |
| D1-PRV-1, D1-PRV-2 | pass, rerun live after the translator change (4 tests in 135 s) | `$CRPROP_OUT/d1/acceptance3/D1-PRV-1.unittest.log` |

DRAGON2 runs of D1 (D7, A1.8): dispatch 1: 19 (5 items, 2 convergence, 5 conformance mixin, 5 conformance CLI,
2 diagnostics); dispatch 2: 11 (3 diagnostics, 3 item runs, 5 conformance mixin); total 30, all on E-crprop, at most
4 at once.

## CRPROP-E2 — 2026-10-28 (environment E2)

Work package E2 of the cr-propagation r4 campaign (r3 §E2 with §E2b folded in, r4 §6; optional): the hep-ml emulator
of USINE B/C with its `ml-artifact`, its valid domain, and the cr-provider/1 entrypoint `emulator`.

**Environment (r3 §0.3, base exception D10).** E2 (macOS arm64 workstation), Python 3.13.2; USINE V3.5 (commit
fb53006d, ENV build) through `HEP_USINE_BIN`, `HEP_USINE_DATA`, `USINE`. `git rev-parse --show-toplevel` =
`.claude/worktrees/crprop-e2`; branch `worktree-crprop-e2`; status clean at start; base `e5ecbd64` = integration HEAD
(decision D10, not `origin/main`); the prerequisite E1 (merge `a4ad05d3`) and B1 (merge `3ed1e89e`), C1 (merge
`099d1d22`) are ancestors of HEAD (`git merge-base --is-ancestor`).

**Criteria and tolerances, fixed before any comparison (R9; frozen entries E2-1, E2-2, E2-3, E2-PRV-1, E2-PRV-2 of
`acceptance.json`, nothing loosened).** Set-up as E1 (VALIDATION CRPROP-E1): free parameters `D0_cm2_s` 1e28–1e29
(log axis), `delta` 0.3–0.8, `eta` −1.5–1.5, `V_A_kms` 0–100, `V_c_kms` 0–30; every other transport field the USINE
provider's `DEFAULT_TRANSPORT` (provider version 0.2.0); observable B/C on the 20 log rigidity bins 2–1000 GV;
synthetic data the USINE B/C at the truth point (`D0_cm2_s` 3e28, `delta` 0.5, `eta` 1, `V_A_kms` 30, `V_c_kms` 5;
Asimov, labelled synthetic); C = the full ILLUSTRATIVE data covariance of E1 (statistical 1.5% (R/10 GV)^0.4
uncorrelated plus systematic 2% with Gaussian correlation length 0.3 in log10 R); σ_i^stat its statistical part. b is
emulator minus USINE (provider `usine`) at the same point, per bin. Posterior: flat prior on the unit cube of the free
parameters (log D0), Gaussian likelihood with C, evaluated through the emulator provider (points it refuses have zero
posterior).
- Hold-out: 32 points drawn (seeded, weighted resampling without replacement) from the posterior through the first E2
  emulator (trained on E1's USINE points only), run with USINE, never trained on, fixed for every round. A second,
  confirmation hold-out of 32 points is drawn the same way from the posterior through the final emulator after it is
  frozen and evaluated once. E2-1 and E2-2 must hold on both sets (the second set is an addition, not a substitute).
- E2-1: on every hold-out point Δχ² = bᵀC⁻¹b ≤ 1.
- E2-2: on every hold-out point and in every bin |b_i| ≤ 0.2 σ_i^stat.
- E2-3: the same synthetic least-squares fit (unit-cube coordinates, box bounds, start at the box centre) once through
  the emulator provider and once through the USINE provider (at most 300 USINE evaluations for this fit). σ_j and the
  interval of each parameter j: the Laplace (Gauss–Newton) 68.27% interval at each best fit, half-width
  σ_j = sqrt[(JᵀC⁻¹J)⁻¹]_jj with J the central finite-difference Jacobian (step 0.01 in unit-cube coordinates), the same
  method for both providers; a boundary is not treated specially (stated in the result). Pass when for every j
  |θ̂_j(emulator) − θ̂_j(USINE)| ≤ 0.2 σ_j(USINE) and |σ_j(emulator)/σ_j(USINE) − 1| ≤ 0.10.
- E2-PRV-1: `tests.core.provider_conformance.ProviderConformance` (C1) passes for provider `emulator`.
- E2-PRV-2: single-shot and `--serve` responses have the same sha256 after removing `elapsed_s` and time stamps.
- Domain (r3 §E2, P10): `DomainModel` of `check_surrogate_domain.py` fitted on the training points (unit-cube
  coordinates); `outside` or `sparse` is out of domain and refused (`failed`, `out-of-domain`), evaluated only with
  `--allow-outside-validated-range` and then labelled `outside-validated-range`; the emulator error enters every
  prediction as an uncertainty component.
- Limits: at most 5 active-addition rounds after the first emulator; at most 500 USINE evaluations for E2 (tally kept;
  E1's 111 runs reused from its cache are not new evaluations); at most 4 USINE runs at once.

**Results (2026-10-28; run outputs `$CRPROP_OUT/e2/`, driver `tests/adapters/fixtures/cr_propagation/e2/emulator_campaign.py`,
E2 venv Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1).** Emulator: `skills/hep-ml/scripts/train_emulator.py`, a
Gaussian process (Matérn-5/2, one length scale per parameter, maximum marginal likelihood with an analytic gradient)
on each of 13 principal components of ln B/C (training reconstruction residual 2.3e-6), trained on E1's 110 USINE
points (design, E1 hold-out and every E1 addition; the truth point, which carries the synthetic data, left out);
`DomainModel` (quantile 0.99, k 5) stored in the model file; ml-artifact by `write_ml_artifact.py` (task surrogate,
`extrapolation_policy` reject, split check passed with test groups disjoint), valid without findings. The first
emulator already met both criteria on the hold-out, so no active-addition round was needed (the round machinery did
not run live).

| ID | Result | Evidence |
|---|---|---|
| E2-1 | passed: largest Δχ² 0.0045 on the 32 hold-out points (posterior of the first emulator) and 0.0022 on the 32 confirmation points (posterior of the final emulator, the same model); tolerance ≤ 1 | `e2/summary.json` rounds[0].holdout, confirmation; recomputed offline by `EmulatorValidation.test_holdout_criteria` from `e2/holdout.json` |
| E2-2 | passed: largest abs(b_i)/σ_i^stat 0.063 (hold-out, bin 0 at 2–2.7 GV) and 0.045 (confirmation); tolerance 0.2; largest relative error 6.1e-4 | same |
| E2-3 | passed: best fits (start at the box centre) emulator vs USINE differ by at most 0.0020 σ (V_A_kms; D0 0.0008, delta 0.0008, eta 0.0004, V_c 0.0003); Laplace half-widths differ by −0.10%, +0.01%, +0.48%, −1.16%, −0.43% (D0, delta, eta, V_A, V_c); tolerances 0.2 σ and 10%. USINE fit: 23 function evaluations, 113 USINE evaluations (cap 300), χ² 2.7e-11 at the truth; emulator fit χ² 4.9e-6. The Laplace 1σ intervals of eta, V_A_kms and V_c_kms cross the box edges (σ in the unit cube 0.34, 0.33, 0.96: B/C alone leaves V_c almost free, as E1 saw); the criterion compares the same Laplace method for both providers, boundaries not treated | `e2/summary.json` e2_3; ml-artifact `downstream_validation` |
| E2-PRV-1 | passed: `EmulatorProviderConformance` (C1 mixin) all checks, offline (no USINE) | `tests/adapters/test_cr_propagation.py` |
| E2-PRV-2 | passed: single-shot and `--serve` responses have equal sha256 without `elapsed_s` (check prv-2), and the runner's response equals the direct one | same |

Domain and posterior: the provider refuses a point the `DomainModel` calls sparse or outside (out-of-domain, with its
reasons), the box by the protocol, another transport block (out-of-domain) and bins that are not training bins
(unsupported-observable); a tampered model fails with provider-error, another model (`HEP_EMULATOR_ML_ARTIFACT`)
gets version `1.0.0+model.<sha12>`. Its GP and domain arithmetic equal hep-ml's `GaussianProcessEmulator` and
`DomainModel` (1e-12; 1,610 points). The posterior through the provider (importance sampling, 16,384 proposal draws,
6,469 in the box) refused 1,058 draws (16%), ESS 495: the stored `DomainModel` reports an estimated in-distribution
false-positive rate of 0.18 (22 held-out training points of a Sobol design, which the method's note says to read as a
guide), so the domain is conservative and the posterior is conditional on it. Every hold-out and confirmation point is
`inside`. Emulator error per prediction (P10): 13 fully correlated components (one per principal component) plus one
uncorrelated component, adding in quadrature to the GP variance. The GP mean carries rounding noise of about 1e-10 in
ln B/C (six components have the nugget at its 1e-12 floor), far below the 6e-4 error.

**Budget (D7, A1.8).** 177 USINE evaluations for E2 (hold-out 32, confirmation 32, E2-3 fit 113; E1's 110 points and
the truth were cache hits), cap 500; at most 4 USINE runs at once; each has a computational-run record under
`$CRPROP_OUT/e2/runs/`. CPU about 0.2 core-hours. B1X check: for the truth point and three hold-out points the USINE
input files rendered by the B1X translator (`worktree-crprop-b1x` at ce60dbaf, exported read-only) are byte-identical
to those of this base, and the ILLUSTRATIVE network has no 13C or 14C (B1X's reader change), so E1's and E2's USINE
values do not depend on B1X as it stands.

Labels: synthetic, unvalidated (ILLUSTRATIVE cross sections, synthetic data); the emulator is validated only in the
posterior of this synthetic fit, and its training transport is the USINE provider's `DEFAULT_TRANSPORT` (L_kpc 4).
Not done: an active-addition round with this emulator (not needed); a profile-likelihood or posterior interval
comparison with USINE (E2-3 uses Laplace intervals, as fixed above).

Rework round 1 (wave-3 finding): `tests.tools.test_subprocess_timeouts` failed on the two unbounded `subprocess.run`
calls (partition `plan` and `merge`) in `tests/adapters/fixtures/cr_propagation/e1/active_addition.py`. Both now carry
`timeout=SMALL_STEP_TIMEOUT` (600 s; each handles one shard manifest, milliseconds in practice, so a legitimate run
cannot be cut short). A `subprocess.TimeoutExpired` is recorded in the batch `problems` list (shard marked failed, then
`incomplete-batch` is raised as for any failed shard), not ignored. No design, record or result changed; no USINE run.
Checks on the fix: test_subprocess_timeouts + test_cr_propagation OK (83 tests, 10 skipped); `--part static --jobs 4`
passed; check_naming, workflow_check diff (base b0d0016d) and acceptance ok; `active_addition.py --help` works.

## CRPROP-C2U — 2026-10-28 (environment E2)

Work package C2U (propagation fit with the USINE provider) of the cr-propagation r4 workflow, r3 card §C2 (USINE case,
split by r4 §6). SYNTHETIC data only; every input ILLUSTRATIVE.

Environment: E2 (macOS arm64 workstation), Python 3.13.2 (miniconda), NumPy 2.4.4, SciPy 1.17.1; USINE V3.5 (tag V3.5,
commit fb53006d) located through HEP_USINE_BIN and HEP_USINE_DATA, runs kept under HEP_USINE_RUN_DIR =
`$CRPROP_OUT/c2u/runs`, provider cache `$CRPROP_OUT/c2u/cache`. r3 §0.3 checks: toplevel
`<repo>/.claude/worktrees/crprop-c2u`, branch `worktree-crprop-c2u`, status clean at start; base exception (decision
D10): base is the integration HEAD `651e4af9`, not `main`; prerequisites C2 (`9f17775c`), B1 (`3ed1e89e`), B1X
(`2360c294`), A1R (`18b43b34`), B3 (`c1b5967d`) and E1 (`a4ad05d3`) are ancestors of HEAD.

Criteria and settings, written before any fit with USINE was run (R9; frozen entries C2U-1 to C2U-3 of
`acceptance.json`). Provider `usine` 0.2.0 (adapter cr-propagation), not decomposable, values P2 ratios of bin
integrals (declared `bin-averaged` with the convention "ratio of the bin-integrated fluxes (r3 P2)").

| Item | Pre-declared setting or criterion |
|---|---|
| Transport | the provider's harmonized-v1 default (2D, L = 4 kpc, R0 = 1 GV, eta = 1, isotopic network to 16O, isotopic ILLUSTRATIVE cross sections, thin-disc V_A) with one ILLUSTRATIVE low diffusion break (R_break_gv 5, delta_below 0, s 0.05, 'usine' convention), the same for both families; the break is held fixed because the provider's domain has no break parameters (a difference from the literature SLIM, whose break is fitted) |
| Dataset | one SYNTHETIC Asimov B/C set from the provider at the truth: 15 bins equal in ln(E_k/n) from 0.3 to 300 GeV/n, 4% uncorrelated + 2% fully correlated; its observable block copied from the prediction |
| Truth (generating family BIG) | `D0_cm2_s` 3e28, `delta` 0.45, `V_A_kms` 70 (interior), `V_c_kms` 0 (on its physical lower bound, P8); `L_kpc` 4 and `eta` 1 fixed. Amended before the BIG fit: `V_A_kms` was first 30, but a SLIM smoke fit to that Asimov set gave chi2 0.09 (thin-disc reacceleration at 30 km/s is nearly absorbed by D0 and delta), so the truth was raised to 70 to make the family comparison discriminate; no criterion changed |
| Families | BIG: `D0_cm2_s`, `delta`, `V_A_kms`, `V_c_kms` free; SLIM: `D0_cm2_s`, `delta` free, `V_A_kms` = `V_c_kms` = 0 |
| Difference steps | USINE prints 6 significant digits (noise about 1e-6 relative, measured on 9 probe runs): stated steps 0.003 in ln D0, 0.001 in delta, 0.3 km/s in V_A and V_c for the Jacobian, the Fisher matrix and the convergence verdict |
| C2U-1 | BIG fitted with the provider (no response model): `D0_cm2_s`, `delta`, `V_A_kms` (interior true points) within 0.1 sigma of the truth, sigma from the inverse Fisher matrix at the best fit; `V_c_kms` on the boundary: the minimum passes `boundary_kkt` and lies within 0.1 sigma_one-sided of 0, sigma_one-sided = distance from the bound to the profile delta chi2 = 1 crossing on the allowed side |
| C2U-2 | every evaluation the fit used is recorded with provider `usine`, version 0.2.0 and a computational-run reference that resolves in the run folder, whose tool is USINE V3.5 commit fb53006d; a start point outside the domain (`V_A_kms` 200), a toy truth outside it and a point sent outside it to the provider are refused (out-of-domain) without a USINE run |
| C2U-3 | BIG and SLIM fitted to the Asimov data from BIG; each listed with its delta chi2 calibrated by 200 toys per family on a total-degree-3 polynomial response model in (ln D0, delta, V_A, V_c) from 96 Sobol design points (amended before the BIG calibration from degree 4 and 160 points, to stay within the USINE budget after the first run spent 873 evaluations; the 2D SLIM-only box of that run had a largest error of 6.2e-5 sigma at degree 4), refused unless its largest error at 20 random provider points is <= 0.05 of the data sigma in every bin; its error enters the toy covariance (P10); a family survives at alpha = 0.05 (toy p-value >= alpha); pass when BIG (the generator) survives |
| Bin semantics | the guard accepts the provider for data declared P2 (`bin-integrated`, or `bin-averaged` with the P2 statement) and refuses data with another binning convention (`crsr:bin_average`) or `point` values |
| D7 | USINE evaluations counted by the runner (`points_sent`); C2U cap 1500 with a running tally; at most 4 USINE processes at once (the fit runs one) |

Results (`tests/skills/hep_statistics/usine_family_study.py`, recorded in
`tests/adapters/fixtures/cr_propagation/c2u/usine-family-study.json`; outputs in `$CRPROP_OUT/c2u/acceptance/`; tests in
`tests/skills/hep_statistics/test_propagation_fit.py`, class `UsineProvider`, offline from the record, one live test
gated by HEP_USINE_LIVE_TEST=1):

| Item | Result | Evidence |
|---|---|---|
| C2U-1 interior | BIG converged (no restart, EDM 7.6e-7); pulls `D0_cm2_s` 4e-5 sigma (sigma_ln 0.139), `delta` 4e-5 sigma (sigma 0.0244), `V_A_kms` 6e-6 sigma (sigma 27.8 km/s: B/C alone constrains thin-disc reacceleration weakly) | `record.json` fits BIG |
| C2U-1 boundary | `V_c_kms` = 0 on the lower bound (snapped from 5.7e-5, within one difference step), `boundary_kkt` derivative +58.9 (ok); profile interval lower end `bound`, upper crossing at 7.129 km/s: sigma_one-sided 7.129, pull 0 | `record.json` profile_intervals |
| C2U-2 | provider `usine` 0.2.0 (not decomposable, one `total` component); 565 evaluation records (one per point, cache hits included), each with a computational-run reference, all 565 resolved in the run folder; one tool: USINE V3.5 (git tag V3.5, commit fb53006db41d...); start `V_A_kms` 200 refused (out-of-domain) before any run; a point with `V_A_kms` 200 sent to the provider refused by the entrypoint (out-of-domain) with USINE unset; multipliers with a non-decomposable provider refused (not-decomposable) | tests `test_c2u2_*` |
| C2U-3 | NOT MET. BIG and SLIM both fitted with the provider and listed: chi2 0 (BIG, dof 11) and 1.32 (SLIM, dof 13), delta chi2 1.32 for SLIM; the toy calibration did not run: the 4D polynomial response model's largest error was 2.81 of the data sigma at 20 validation points, above the pre-declared 0.05, so the fit refused it (response-model-above-tolerance) and no toy-calibrated delta chi2 exists. Cause: the box is +-5 sigma of BIG, and sigma(V_A) = 27.8 km/s makes it span the whole V_A domain [0, 150] km/s (and V_c [0, 38]); B/C over that box is not a degree-3 or -4 polynomial (offline cross-validation on the 1336 cached runs: largest held-out error 1-2.5 sigma at degree 3-4, worse above). A redesign (smaller data errors or a second dataset such as 10Be/9Be to constrain V_A, then refits, about 420 more runs) does not fit in the 160 runs left of C2U's 1500 cap | `record.json` family_calibration |
| Bin semantics | USINE's prediction is classified P2; data declared `bin-integrated` (P2) pass the guard and the comparison gate (the prediction's label aligned to the data's and recorded as `bin_semantics_aligned`); data with `point` values, with a `crsr:bin_average` convention, or `bin-averaged` without the P2 statement are refused (bin-semantics-mismatch); the closed-form refusals of C2 are unchanged | `test_bin_semantics_guard_accepts_p2_and_refuses_mismatches` |
| Live rerun | SLIM refitted live with USINE (32 runs, fresh cache and run folder): best fit equal to the record within 1e-6 relative, every record resolved, tool USINE V3.5 fb53006d | `test_live_slim_refit_matches_the_record` |

USINE evaluations (D7, distinct runs): 9 noise probes, 28 in a SLIM smoke fit at the first truth (V_A 30), 1 truth run,
873 in the first study (BIG stopped strictly inside the V_c bound, its verdict differences straddled the bound and
failed, so 5 restarts; fixed by snapping to a bound within one step), 6 in an aborted start, 423 in the second study
(BIG, SLIM, the V_c profile interval, 116 response-model runs), 0 in the recorded third study (all cached), 32 in the
live test: about 1372 of C2U's 1500. Each run took about 3 s (1 USINE process at a time).

Advisories of C2's verifier handled here: the toy seeds are in `extension.seeds` and `coverage.seed` of the
statistical-result; per-toy rows are kept in the coverage toys and in each family's calibration; the multipliers are
solved within NU_BOUNDS (bounded least squares when the unbounded solution leaves them). Recorded, not changed (C1
protocol, not C2U's files): two observables with the same id in one request make the components ambiguous, so the fit
still sends one request per dataset (a two-dataset point costs two USINE runs).

Not done in C2U: the toy-calibrated family comparison (C2U-3, above); the low break is fixed, not fitted (the provider's
domain has no break parameters); modulation (datasets with a period are refused) and real data (F1).

## CRPROP-D3 — 2026-10-28 (environment E-crprop)

Work package D3 of the cr-propagation r4 campaign (r3 §D3): two-level cross-code comparison of DRAGON2 and USINE.
GALPROP is `unavailable` (decisions A1.2; escalation 2), so the comparison is DRAGON2 vs USINE only (workflow.json
fallback of D3: "D2 skipped: DRAGON2 and USINE only").

**Environment (r3 §0.3, base exception D10).** Toplevel `.claude/worktrees/crprop-d3`; branch `worktree-crprop-d3`;
status clean at start; base = integration HEAD b0d0016d (not `main`, decision D10). Prerequisites are ancestors of
HEAD (`git merge-base --is-ancestor`): B1 3ed1e89e, B1X 2360c294, D1 e44377f4, A1R 18b43b34, B3 c1b5967d, A4
0ee4c914. External codes: DRAGON2 cd588707 (the D1 build, `HEP_DRAGON2_BIN`, `HEP_DRAGON2_DATA`) and USINE V3.5
(the B1 build, `HEP_USINE_BIN`, `HEP_USINE_DATA`) on E-crprop (macOS 27.2 arm64), at most 4 external processes at once.

**Criteria and tolerances, fixed before any D3 comparison (R9).** Frozen entries (acceptance.json): D3-1 5%, D3-2
judgment, D3-3 5% (added per A1.9). How they are evaluated (written here before any D3 run was compared; none of this
replaces or widens a frozen entry):

- Metric for D3-1 and D3-3: the largest |r_DRAGON2 / r_USINE - 1| of B/C on the 16 log-uniform rigidity bins
  2-1000 GV of B1 and D1, ratios of bin integrals (r3 P2, P3; `dragon2_to_prediction.ratio_of_bin_integrals` and
  `usine_to_prediction.ratio_of_bin_integrals`). ¹⁰Be/⁹Be on the 12 E_k/n bins 0.05-10 GeV/n is reported alongside
  with the same metric and no verdict of its own (the frozen entries name 2-1000 GV, i.e. B/C).
- D3-1 (level 1): each configuration that both codes ran from the same transport block: `harmonized-v1` (set A) and
  D1's `harmonized-v1-<item>` blocks (isotopic item-off, convection, decay, reacceleration; losses with its Galprop-gas
  item-off run on the DRAGON2 side). USINE as translated by B1/B1X from the block, DRAGON2 as translated by D1. A
  configuration passes only if its B/C metric is ≤ 5%; D3-1 passes only if every configuration passes. Recorded runs
  of B1 and D1 are reused where the configuration matches; DRAGON2 `harmonized-v1` (set A) is run once.
- D3-3 (level 1, matched): the same configurations with USINE given DRAGON2 cd588707's fixed settings where USINE can
  express them: helium target with He/H = 0.11 (constants.h `He_abundance`) of the hydrogen nucleon density, with
  DRAGON2's helium production factor 1 + 0.11 r(E) (GALPROP's `He_to_H_CS_ratio`, xsec.cc) on the same ILLUSTRATIVE
  production cross sections; DRAGON2's own inelastic cross sections (CROSEC/Barashenkov-Polanski `sighad`, option 2,
  times 1 + 0.11 · 2.10 / A^0.055 for helium) on hydrogen and helium, evaluated with DRAGON2's own code outside the
  repo; the thin-disc densities set to DRAGON2's gas columns at the observer (BronfFerr; Galprop's HI, HII and H2 for
  the losses item, D1-L); the parent ratio O/C at the normalisation energy set to DRAGON2's propagated O/C. Each
  setting that cannot be matched is recorded with its estimated effect on B/C. Pass if every configuration's B/C
  metric is ≤ 5%.
- Attribution ladder (evidence for D3-2 and D3-3): USINE runs that switch the matched settings on one at a time
  (gas column, helium target, inelastic cross sections, parent ratio), each step's effect recorded as a ratio of the
  B/C of consecutive runs.
- D3-2 (level 2): each code with its own default inputs at the same transport (harmonized-v1-isotopic): DRAGON2 with
  its shipped production table (Evoli 2019, cumulative), its BaseModel source abundances, BronfFerr gas, helium and
  inelastic cross sections; USINE with its own files (`sigProdGALPROP17_OPT12`, `sigInelTripathi99+Coste12`, as in
  B1X), data-normalised abundances and its gas and helium settings; same network top (O-16) on both sides. Every
  difference between the two is listed as a `model-alternative` with its attribution: an effect measured by a USINE
  run that swaps that one input for DRAGON2's (production table, inelastic cross sections, gas and helium,
  abundances), or, where no run can isolate it, an estimate with its method. D3-2 passes if no listed difference is
  without an attribution and the product of the attributed effects leaves a residual no larger than the D3-3 residual
  plus the stated uncertainty of the estimates; an unexplained residual is itself listed as unattributed (fail).
- Budget (A1.8): at most 60 DRAGON2 and 300 USINE runs in D3, tallied in this section.

**Runs (D7, A1.8).** DRAGON2: 2 propagation runs (`D3_harmonized_v1`: harmonized-v1 set A, 212 s; `D3_l2_dragon2`:
level 2 with DRAGON2's shipped production table and abundances, 313 s), plus 13 calls of a 20-line driver linking
DRAGON2's own `libDRAGON.a` (`sighad`, CROSEC option 2) to tabulate DRAGON2's inelastic cross sections
(`d3/dragon2-inelastic.json`; no propagation, a few ms each). USINE: 37 runs (20 in the final plan of
`d3_study.py usine_plan`, 15 superseded: reruns after fixing the study script's record step or adding the injection
setting, 1 aborted by a misparsed gas string, 1 live test), each 2-20 s. Reused, not rerun: D1's six DRAGON2 item runs and B1's seven USINE
runs. Tally against the D3 caps: DRAGON2 2/60, USINE 37/300.

**What USINE was given (D3-3, matched level 1)**, all from DRAGON2 cd588707's code: He/H 0.11 of the hydrogen nucleon
density (constants.h, galaxy.cc), production on He = σ_H × `He_to_H_CS_ratio` (xsec.cc 145, 2364-2410), inelastic on H
from DRAGON2's own `sighad` and on He × 2.10/A^0.055 (xsec.cc 2310-2317, xsec.h 465); thin-disc densities = DRAGON2's
gas columns at r = 8.3 kpc on its z grid / 2h (BronfFerr: HI 0.1396, H2 0.0392 molecules, nucleons 0.2180 kpc cm⁻³;
Galprop: HI 0.2054, HII 0.0419, H2 0.0498, nucleons 0.3469); O/C at 10 GeV/n = DRAGON2's propagated value (1.194-1.211;
the profile's parent list gives 0.9, and D1's translator keeps DRAGON2's BaseModel abundances without recording it);
injection β⁻¹ Rig^-2.3 (USINE `eta_s` = -1): DRAGON2's C and O spectra are 1.75 times USINE's at 0.2 GeV/n relative to
10 GeV/n (≈ 1/β, a rigidity power law per unit momentum), and agree within 0.6% at 0.05-1000 GeV/n once USINE has
`eta_s` = -1. Not expressible in USINE's KisoVc models, recorded with estimated effects on B/C (high-energy limits):
DRAGON2's radial gas profile (BronfFerr ×1.0076, Galprop ×0.888; Fourier-Bessel, uniform sources), the vertical extent
of its gas and of its source box |z| ≤ 0.2 kpc (BronfFerr ×0.980, Galprop ×0.913; slab Green's function), together
0.987 and 0.811 (`geometry_factor`); reacceleration in the whole halo (A1R first-order conversion, relative error bound
0.517 on the second-order term); finite gas layer for ¹⁰Be decay (D1's thick-gas factor); numerics (DRAGON2 grid 0.22%,
D1; USINE 100 Bessel terms 0.5%, B3-1c).

**Results** (`d3/d3-results.json`, recomputed offline by `D3CrossCode`; B/C max |r_DRAGON2/r_USINE − 1| on 2-1000 GV):

| Configuration | Level 1 (D3-1) | Matched (D3-3) | ¹⁰Be/⁹Be matched |
|---|---|---|---|
| harmonized-v1 (set A) | 1.270-1.408, 40.8% | 0.993-1.000, **0.67%** | — |
| isotopic (item-off) | 1.270-1.387, 38.7% | 0.993-1.000, **0.67%** | 0.13% |
| convection | 1.279-1.395, 39.5% | 0.994-1.000, **0.59%** | 0.17% |
| decay | 1.270-1.387, 38.7% | 0.993-1.000, **0.65%** | 18.3% (gas layer; matched / D1 thick-gas factor within 0.41% in all 12 bins) |
| reacceleration | 1.281-1.382, 38.2% | 0.830-1.003, **17.0%** (lowest bin) | 2.7% |
| losses-off (Galprop gas) | 1.510-1.770, 77.0% | 0.823-0.916, **17.7%** | 0.18% |
| losses (Galprop gas) | 1.499-1.770, 77.0% | 0.823-0.943, **17.7%** | 0.22% |

Attribution of the level-1 offset (isotopic, USINE ladder, effect of each step on B/C): gas column 1.054-1.087, helium
target 1.073-1.136, inelastic cross sections 1.003-1.077, parent ratio O/C 1.104-1.110, injection convention
1.000-1.031; their product times the matched residual equals the level-1 offset (test). Failing matched configurations:
reacceleration — item effect DRAGON2/USINE 0.834 in 2-2.95 GV, 1.007 in the next bin, within the A1R bound times
USINE's item effect (0.302, 0.090) in every bin (`reacceleration_check`); losses pair — the matched run with the gas
scaled by the Galprop geometry factor 0.811 (`a-losses-off-geometry`, `a-losses-geometry`) agrees within 1.9% and 3.3%,
and the high-energy offset 0.823 is the factor 0.811 within 1.5%; with like-for-like gas (HII in USINE) the losses
item effects agree within 3.0% (D1-1a found 6.1% against an ionization-only reference).

Level 2 (DRAGON2/USINE defaults 1.181-1.234), USINE swapping DRAGON2's inputs in one at a time: production table
(Evoli 2019 vs GALPROP17 OPT12) 0.971-1.041, inelastic (CROSEC vs Tripathi99+Coste12) 1.003-1.011, gas and helium
1.128-1.204, abundances 1.013-1.015, injection convention 1.000-1.029; residual 0.996-1.003 (0.42%). Estimated, not
isolated by a run: gas and source geometry 0.987-1.000, ¹³C/¹⁴C in the C denominator (solar fractions in USINE)
1.0085-1.0089, network edges (¹⁷O, ¹⁸O) ±0.05%, numerics ±0.5%. Every difference is registered as a
`model-alternative` in `level2_differences`.

| ID | Result | Evidence |
|---|---|---|
| D3-1 | **failed**: 38-77% at level 1 for every configuration (frozen 5%; reported, not loosened); fully decomposed by the ladder | `verdicts.D3-1`, `ladder`; `D3CrossCode.test_d3_1_level_one_fails_and_is_reported` |
| D3-3 | **failed overall**: passes within 0.59-0.67% for harmonized-v1, isotopic, convection and decay; fails for reacceleration (17.0%, attributed: first-order zone conversion, within its bound) and the losses pair (17.7%, attributed: Galprop gas geometry that a uniform thin disc cannot express; geometry check within 3.3%) | `verdicts.D3-3`, `reacceleration_check`, `geometry_checks`; `test_d3_3_matched_level_one` |
| D3-2 | **passed**: every level-2 difference measured or estimated; residual 0.42% ≤ allowed 2.46% (D3-3 isotopic residual 0.67% + BronfFerr geometry 1.29% + numerics 0.5%) | `level2_differences`, `verdicts.D3-2`; `test_d3_2_every_level_two_difference_is_attributed` |
| D3-3 command | `python3 -m unittest tests.adapters.test_cr_propagation`: ok | `$CRPROP_OUT/d3/acceptance/` |
| ALL-1 | environment field above | this section |

Open issues found (outside D3's files, for the orchestrator): (1) `dragon2_run.spec_from_transport` neither translates
`sources.abundances` nor records it as a substitute (DRAGON2's BaseModel O/C 1.21 vs the profile's 0.9: ×1.10 on B/C,
the part of D1-1b's USINE offset D1 left unnamed); (2) harmonized-v1's "all primaries R^-2.3" does not fix the measure
(per momentum in DRAGON2, per E_k/n in USINE: up to 3% on B/C at 2-3 GV, ×1.75 on primaries at 0.2 GeV/n), and neither
translator records it; (3) `usine_translate._gas` drops a density term written without `cm^-3` to 0 with only a
substitute note (found when a D3 run aborted); (4) D1's thick-gas attribution of the ¹⁰Be/⁹Be decay gap now holds in
every bin against a like-for-like USINE run, including the lowest bin D1 left unattributed.

Note (D3 verifier advisory, added at the rebase on 6a227a76): the level-2 swaps above, and the matched-level-1 ladder,
are cumulative (each USINE run keeps every earlier swap and adds one more; `L2_STEPS` and `LADDER` in
`d3_study.py`); "one at a time" means one more input per step, and each effect is relative to the previous step.

### CRPROP-E2 rework round 1 (wave-4 finding, 2026-10-28)
Base: integration HEAD 65cbaa56 (branch fast-forwarded from a6929c4d). Finding: `tests.skills.test_cli_contract`
CliContract.test_scoped_tools_take_status failed because `skills/hep-ml/scripts/train_emulator.py` had no `--status`.
Fix: `add_status_argument` (core/status.py) on both subcommands (train, predict), echoed as `status_label` in every
stdout JSON object like train_bdt.py; no exemption added; model, run summary and exit codes unchanged. Checks:
test_cli_contract, test_train_emulator, tests/skills/hep_ml (422 tests, 38 skipped), test_cli_robustness,
test_cr_propagation OK; measure_entrypoints hep-ml within budget; `--part static --jobs 4`, check_naming,
workflow_check diff and acceptance ok.

### CRPROP-D3 rework round 1 (wave-5 finding, 2026-10-28)
`tests.tools.test_subprocess_timeouts` failed on d3_study.py:285 and :295 (gfortran build of the inelastic driver and
the per-nuclide driver call, no `timeout=`). Both now carry `timeout=600` (seconds-scale and millisecond-scale runs;
generous bound, commented); `subprocess.TimeoutExpired` propagates like the existing `check=True` failures (raised,
never swallowed). The USINE run already had `timeout=900`. Results, fixtures and test assertions unchanged;
`d3_study.py --help` works. Checks: test_subprocess_timeouts and test_cr_propagation OK, `--part static --jobs 4`,
check_naming, check_wiring, workflow_check diff and acceptance (see report).

## CRPROP-C2UF — 2026-10-28 (environment E2)

Work package C2UF (toy-calibrated BIG vs SLIM with USINE; C2U-3 moved here by decision A1.12) of the cr-propagation r4
workflow, r3 card §C2 (C2-3, USINE case). SYNTHETIC data only; every input ILLUSTRATIVE.

Environment: E2 (macOS arm64 workstation), Python 3.13.2 (miniconda), NumPy 2.4.4, SciPy 1.17.1; USINE V3.5 (tag V3.5,
commit fb53006d) located through HEP_USINE_BIN and HEP_USINE_DATA, runs kept under HEP_USINE_RUN_DIR =
`$CRPROP_OUT/c2uf/runs`, provider cache `$CRPROP_OUT/c2uf/cache` (a copy of C2U's; C2U's left unchanged). r3 §0.3
checks: toplevel `<repo>/.claude/worktrees/crprop-c2uf`, branch `worktree-crprop-c2uf`, status clean at start; base
exception (decision D10): base is the integration HEAD `6a227a76`, not `main`; prerequisites C2U (merge `886bb316`)
and B1X (merge `2360c294`) are ancestors of HEAD.

### Design probes (before any fit; 33 USINE runs, `$CRPROP_OUT/c2uf/probe/`)

| Probe | Runs | Finding |
|---|---|---|
| Forward-difference Fisher at the C2U truth with C2U's transport, B/C, 10Be/9Be and Be/B from 0.3 GeV/n in one request | 5 | sigma(V_A) 26.8 km/s with B/C alone, 26.8 with 10Be/9Be added, 26.7 with Be/B too: no gain. Cause: the provider's default transport has `decay.enabled` false, so 10Be/9Be is the production ratio (0.55, flat) and insensitive to D0 (d ln / d ln D0 about 0.004) |
| Two 9-point V_A slices (Chebyshev nodes) at union-box corners (ln D0 65.03, delta 0.377, V_c 0, V_A 0-150; ln D0 65.18, delta 0.40, V_A 0-110) | 18 | along V_A alone, ln(B/C) needs degree 6 at the first corner and degree 5 at the second for 0.05 of the 4.47% sigma (degree 4: 0.23 and 0.057): a box that spans V_A from 0 (SLIM) to beyond the BIG truth reaches low-diffusion, high-V_A corners where no low-degree polynomial is good enough. B/C as a function of V_A^2 is no better |
| Fisher with bins from 0.05 GeV/n (decay still off) | 5 | B/C extended to 0.05 GeV/n alone gives sigma(V_A) 7.3 km/s (10Be/9Be still flat) |
| Fisher with 10Be decay on (beta decay and fed daughter, rate ln 2 / (gamma t_1/2), 7Be fully stripped, r3 P6), B/C 0.05-300 and 10Be/9Be 0.05-10 GeV/n | 5 | 10Be/9Be 0.072-0.34 (decaying); sigma with C2U's B/C (0.3-300) plus 10Be/9Be 0.05-10 GeV/n (6% + 3%): ln D0 0.070, delta 0.0129, V_A 8.1 km/s, V_c 2.35 km/s (B/C alone: V_A 58); 10Be/9Be only from 0.3 GeV/n: V_A 40 |

So the plan of A1.12 works only with decay switched on and 10Be/9Be extending below 0.3 GeV/n (10Be/9Be fixes D0 at the
fixed L; B/C then fixes V_A). A union response box still spans V_A from 0 (SLIM's fixed value) to beyond the BIG truth
and holds the low-diffusion corners above; separate boxes around each family's best fit avoid them.

### Criteria and settings (written before any fit; R9; frozen entry C2UF-1, same text as C2U-3)

| Item | Pre-declared setting or criterion |
|---|---|
| Transport | C2U's (the provider's harmonized-v1 default with the ILLUSTRATIVE low break R_break_gv 5, delta_below 0, s 0.05, 'usine' convention, held fixed) with `decay` = {enabled true, lorentz_dilation true, ec_treatment fully-stripped}; the same block for both families |
| Datasets | SYNTHETIC Asimov from ONE USINE run at the truth (one request naming both observables): B/C, C2U's 15 bins equal in ln(E_k/n) from 0.3 to 300 GeV/n, 4% uncorrelated + 2% fully correlated; 10Be/9Be, 12 bins equal in ln(E_k/n) from 0.05 to 10 GeV/n, 6% uncorrelated + 3% fully correlated; observable blocks copied from the predictions (P2, `bin-averaged` with the P2 statement) |
| Truth (generating family BIG), starts, steps, families | as C2U: `D0_cm2_s` 3e28, `delta` 0.45, `V_A_kms` 70, `V_c_kms` 0; `L_kpc` 4, `eta` 1 fixed; starts 2.4e28, 0.48, 60, 2; steps 0.003 (ln D0), 0.001, 0.3, 0.3 km/s; BIG all four free, SLIM D0 and delta free with V_A = V_c = 0 |
| Provider requests | `provider_requests` "per-point" (new in propagation_fit.py): one request and one USINE run per point for both datasets (distinct observable ids; provider not decomposable); the C1 protocol is unchanged |
| Response models | polynomial, total degree 3 (35 terms) in (ln D0, delta, V_A, V_c), 80 scrambled Sobol design points each, layout "per-center" (new): one model per family's best fit on best fit +- 5 x (largest sigma of either family per coordinate), clipped to the provider domain; each refused unless its largest error at 20 uniform random provider points in its box is <= 0.05 of the data sigma in every bin of both datasets (C2U's tolerance, not loosened); each family's fits to a null family's toys use the model whose box holds that family's fit to the null with a margin of 5 sigma (up to 2% of the half-width, MARGIN_TOL); the largest error of the models per bin enters the toy covariance (P10) |
| Contingency (declared now) | if a model is refused at degree 3, one rerun of the calibration at degree 4 (70 terms) with 150 design points per model, the fits answered from the provider cache; the tolerance stays 0.05 |
| Toys | 200 per family, seed 20261028, a toy whose fit fails or leaves its box is failed, the study stops above 2% failed (C2 loop limit) |
| C2UF-1 | pass when: BIG and SLIM both converge with the provider; the family calibration is `ok` with every response model validated (<= 0.05 sigma); each family is listed with its delta chi2 and its toy p-value (fraction of its own toys with delta chi2 >= the observed one); BIG (the generator) survives at alpha = 0.05 (toy p-value >= 0.05). SLIM's verdict is reported, not required |
| Test | `test_propagation_fit.py` class `UsineTwoDatasetFamilies` asserts the above from the recorded study (no skip); C2U's `test_c2u3` asserts C2U's recorded refusal (no skip); a live part gated by HEP_USINE_LIVE_TEST=1 |
| D7 / A1.8 | C2UF cap 600 USINE runs (running tally in `$CRPROP_OUT/c2uf/tally.json`, counted as runner `points_sent`, since run folders are named by point hash and a rerun of a point with other observables reuses its folder); the fit run capped at 540 (`--max-evaluations`); one USINE process at a time |

### First calibration (study 1, as declared) and amendment (written before the second calibration)

Study 1 (`$CRPROP_OUT/c2uf/study1/`, 298 USINE runs: 1 truth, 197 for the fits, 100 for one response model): BIG
converged with no restart (chi2 0.0, dof 23; pulls below 1e-4 sigma; sigma ln D0 0.0670, delta 0.0122, V_A 8.19 km/s,
V_c 2.37 km/s one-sided, V_c on its bound) and SLIM converged after one restart (chi2 23.93, dof 25; D0 2.509e28,
delta 0.4839): delta chi2 of SLIM 23.93. The family calibration was refused: the first per-center model (BIG's box,
V_A 29-111 km/s, ln D0 +-0.335) had a largest error of 0.883 of the data sigma (worst in the lowest B/C bin at low
D0 and high V_A), so the declared contingency was not run as declared. Offline from the cached runs: degree 3 misses
by up to 0.47 sigma in-sample in that box, degree 4 by 0.11. A 9-point V_c slice in the box (9 runs, `probe/vc-slice.json`)
is smooth (degree 3 within 1e-4 sigma), so the misses come from V_A at low D0, as in the corner slices above.

Two further findings make the declared design unworkable: (1) the declared contingency (degree 4, 150 design points
for both models) needs about 320 runs, more than the 260 left of the 600 cap; (2) under SLIM's null, B/C depends on
V_A only through V_A^2, so BIG's fits to SLIM's toys spread to V_A of about 34 km/s at one sigma and 59 at three
(from sigma(V_A) 8.2 at 70 km/s: one sigma in V_A^2 is 2 x 70 x 8.2 = 1148 km^2/s^2), far beyond the per-center box
around SLIM (V_A 0-41): those toys would leave the box and fail. One box holding both best fits is needed after all.

Amendment (the criteria, the 0.05 tolerance, the 20 validation points per model, the toys and alpha are unchanged):
layout "joint" (new: one polynomial model on the box spanning both best fits +- k times the largest sigma of either
family, so the fit of each family to the other's null has its margin without a rebuild; a margin short by up to 2% of
the half-width holds), k = 3 (half_width_sigma; box ln D0 65.19-65.77, delta 0.413-0.521, V_A 0-94.6 km/s, V_c
0-7.1 km/s), total degree 4 (70 terms) with 150 Sobol design points; the fits answered from the provider cache; the
run capped at 255 USINE evaluations (340 spent so far). Expected toy failures at k = 3 (a fit beyond 3 sigma on four
one-sided edges, about 1 per 200 toys) stay below the 2% limit. Offline, degree 4 in this box reproduces every cached
run within 1e-4 sigma (230 runs, most near the two fits, so not a validation). If this model is refused, the cap
leaves no further attempt and C2UF-1 is reported not met.

### Results (study 2, recorded in `tests/adapters/fixtures/cr_propagation/c2uf/usine-two-dataset-family-study.json`)

| Item | Result | Evidence |
|---|---|---|
| Fits (both datasets, one USINE run per point) | BIG and SLIM equal to study 1 (every fit evaluation answered from the provider cache): BIG returns the truth (pulls < 1e-4 sigma), sigma(V_A) 8.19 km/s (C2U, B/C alone: 27.8); SLIM chi2 23.93 (dof 25), delta chi2 23.93; every evaluation record names both datasets and a computational-run reference that resolves, tool USINE V3.5 fb53006d | `test_two_datasets_both_families_fitted_with_the_provider` |
| Response model (joint, k = 3, degree 4, 150 design points) | REFUSED: largest error 0.452 of the data sigma at 20 validation points (tolerance 0.05, not loosened); no toy ran. Offline from the 170 runs: degree 3 misses by 0.58, degree 4 by 0.55, degree 5 (126 terms on 150 points) by 0.44 at the same validation point (ln D0 65.71, delta 0.507, V_A 1.9, V_c 2.86, the high-D0, low-V_A corner), while in-sample misses fall to 0.03: the global polynomial spends its terms on the strongly curved low-D0, high-V_A region and misses elsewhere. A 9-point V_A slice 0-20 km/s at that point (9 runs, `probe/va-slice-low.json`) is smooth and continuous at V_A = 0 (no switch artifact) | `test_two_datasets_recorded_calibration_refusal` |
| C2UF-1 | NOT MET. BIG and SLIM are fitted with the provider and listed with their delta chi2 (0 and 23.93), but not toy-calibrated: no response model reached 0.05 sigma within the 600-run cap (study 1: 0.883 at degree 3, per-center; study 2: 0.452 at degree 4, joint, k = 3). The criterion runs from the record as an expected failure (`test_two_datasets_toy_calibrated_delta_chi2_and_generator_survives`, `@unittest.expectedFailure`; an unexpected success fails the suite) | test module |
| Live | the truth point rerun with USINE (fresh cache, 1 run) equals the recorded predictions of both datasets within 1e-6 relative; tool USINE V3.5 fb53006d | `test_live_truth_rerun_matches_the_record`, `$CRPROP_OUT/c2uf/acceptance/live-truth-rerun.txt` |

USINE runs (A1.8 tally, `$CRPROP_OUT/c2uf/tally.json`, counted as runner `points_sent`): probes 33 + 9 + 9, study 1 298
(truth 1, fits 197, response model 100), study 2 170 (response model; fits from the cache), live test 1: 520 of 600.
One USINE process at a time throughout.

Diagnosis and options for the maintainer (not done here: each needs more runs than the 80 left, or a decision):
- Cause: any box that holds BIG (V_A 70) and SLIM (V_A 0), plus BIG's fits to SLIM's toys (V_A up to about 60 km/s at
  three sigma, since V_A enters only as V_A^2 near 0), spans V_A from 0 to about 95 km/s at k = 3 and reaches the
  low-D0, high-V_A corner where B/C responds strongly to reacceleration (V_A^2 / K); a global total-degree polynomial
  in (ln D0, delta, V_A, V_c) does not reach 0.05 sigma there at degree 3-5 with the affordable designs.
- Options: (a) a local or adaptive response model (piecewise boxes covering the toy spread, or a sparse-grid /
  Gaussian-process emulator such as the E2 route) validated the same way; (b) coordinates adapted to reacceleration
  (V_A^2 / K at low rigidity); (c) a lower BIG truth for V_A, shrinking the box but weakening the SLIM test;
  (d) a larger budget: a degree-5 joint model needs at least 252 design points plus 20 validation points per attempt,
  with no guarantee (degree 5 missed by 0.44 offline).
- Findings for other work packages: the USINE provider's default transport has decay off, so its 10Be/9Be is the
  production ratio (flat, insensitive to D0); a 10Be/9Be dataset needs `decay.enabled` true and bins below 0.3 GeV/n
  to constrain D0 (and through B/C, V_A) at fixed L.

Not done in C2UF: the toy-calibrated family comparison (C2UF-1, above); modulation and real data (F1).

### Dispatch 2 (decision A1.14): Gaussian-process emulator of USINE (criteria written before any emulator run; R9)

C2UF's files were widened by the orchestrator to E2's emulator provider and trainer (A1.14 follow-up). Changes made
before any run here: `emulator_provider.py` accepts a per-model declaration (observables with their output slices,
axes, bins, the training runs' observable block and the domain taken from the model's feature boxes; the version then
always carries `+model.<hash>`; `--declaration` prints it for a registry entry); a model without it (the committed E2
model) is answered exactly as before, pinned by `EmulatorPinnedResponses` (8 responses recorded with the provider
before the change, equal to the last bit on E2); `train_emulator.py` unchanged (it copies the outputs block into the
model). `propagation_fit.py` gains response_model kind "provider": the toys evaluate the provider itself.

| Item | Pre-declared setting or criterion |
|---|---|
| Emulator | `train_emulator.py train` (subprocess; Matern-5/2 GP per principal component of ln values, `--pca-tolerance 1e-4`, `--restarts 4`, `--seed 20261028`), features ln D0 (log, 1.9e28-4.0e28), delta (0.40-0.535), V_A (0-105 km/s), V_c (0-9.5 km/s): the joint box at k = 4 around study 2's two fits, rounded outward, so the toy box (k = 3) lies one sigma inside it; outputs ln B/C (15 bins, ekn 0.3-300 GeV/n) then ln 10Be/9Be (12 bins, ekn 0.05-10 GeV/n), one vector of 27; transport = the study's (decay on); ml-artifact by `write_ml_artifact.py` (task surrogate, extrapolation_policy reject, regression-value) |
| Training runs | every cached USINE run of the study (same transport and request) inside the box (448), plus new USINE runs: 200 scrambled Sobol points in the box, 40 on the V_c = 0 face, 30 on the V_A = 0 face and 30 on the SLIM slice V_A = V_c = 0 (where BIG's boundary values and every SLIM evaluation lie): 300 runs |
| Validation (held out, never trained on) | 40 new USINE runs: 30 uniform random points in the toy box (ln D0 65.191-65.772, delta 0.4133-0.5206, V_A 0-94.56, V_c 0-7.108) and 10 uniform on the SLIM slice in the same ln D0 and delta ranges (seed 20261029); each answered through `emulator_provider.py` (the per-model declaration, via core/provider); pass when at every validation point, in every bin of both datasets, abs(emulator - USINE) <= 0.05 of the data sigma (B/C sqrt(0.04^2 + 0.02^2), 10Be/9Be sqrt(0.06^2 + 0.03^2) of the value), the tolerance pre-declared in C2U, not loosened; a point the DomainModel refuses fails the validation |
| P10 | the per-bin largest abs(emulator - USINE) over the validation points enters each dataset's covariance as an uncorrelated component named `emulator` |
| One refinement (declared now) | if the validation fails: the 40 validation runs join the training set with 60 new Sobol points in the box, the emulator is retrained, and 40 fresh validation points (seed 20261030, same mix) decide; no other change; if it fails again C2UF-1 is reported not met |
| Fit and toys | propagation_fit with provider `emulator` (registry entry from `--declaration`), the study's datasets (USINE Asimov at the truth, the recorded fixture values) with the `emulator` component, families BIG and SLIM, same starts and steps, response_model kind "provider", layout joint, half_width_sigma 3, 200 toys per family, seed 20261028, alpha 0.05, the 2% toy-failure limit (a toy fit the DomainModel refuses fails) |
| C2UF-1 | pass when: the emulator passes its validation; BIG and SLIM converge with the emulator provider; each is listed with its delta chi2 and toy p-value from 200 toys with at most 2% failed; BIG (the generator) survives at alpha 0.05 |
| D7 / A1.8 | 480 USINE runs left of 1000; the plan uses 340 (+140 for the refinement): within the cap; emulator evaluations are not USINE runs |

Emulator results and amendments (written before the recorded fit run):
- Validation round 0 PASSED: 738 training runs (448 cached + 300 new, 10 duplicates to 1e-9 dropped), 19 principal
  components; at the 40 held-out USINE runs the largest error is 0.0038 of the data sigma (tolerance 0.05), largest
  relative error 2.1e-4, no point refused by the DomainModel. No refinement round was needed (no further USINE run).
- First calibration with the emulator (not recorded as the result; `$CRPROP_OUT/c2uf/emu/record-first.json`): fits equal to USINE's (SLIM chi2 23.9272 vs 23.9273), but the toy study stopped at the 2% limit: the toy
  fits did not pass the convergence verdict. Diagnosed on the same toys (emulator only, no USINE run): (1) scipy's
  default relative difference steps (1e-8) sit below the emulator's rounding noise, so the Jacobian was noise; (2) fits
  stopping within one step of V_c = 0 had verdict differences straddling the bound; (3) BIG's fits to SLIM's toys have
  V_A nearly unidentifiable near 0 (B/C depends on V_A^2), so the optimizer stopped short (EDM 1e-4 to 5e-3);
  (4) BIG's fits to SLIM's toys spread in V_c beyond BIG's own 3-sigma box (V_c up to the 7.1 km/s edge: 8 of 200).
- Amendments to propagation_fit.py's toy fits (no criterion, tolerance, toy count or alpha changed): with stated
  difference steps, the fits on a response model or provider use them (central differences, `x_scale` "jac", dogbox
  for bounded fits), snap a coordinate within one step of a domain bound onto it as fit_family does, shrink a verdict
  step that would straddle a nearby bound, and finish a fit the verdict finds short of the minimum with up to 30
  damped Newton steps (core newton_fit) before judging it; kind "provider" bounds the toy fits by the provider's
  domain (no approximation, so no response box; a point the DomainModel refuses fails that toy). On 200 toys per
  family (diagnostic, same seeds) BIG had 0 and SLIM 3 failed toys (2 refused by the DomainModel, 1 not converged),
  below the 2% limit (4).

Results of dispatch 2 (recorded in `tests/adapters/fixtures/cr_propagation/c2uf/usine-emulator-family-study.json`,
with the model `emulator-model.json` and its ml-artifact `emulator.ml-artifact.json`):

| Item | Result | Evidence |
|---|---|---|
| E2 unchanged | the committed E2 model's 8 pinned responses reproduced (numbers equal within 1e-12, on E2 bit-identical apart from the timing field); every existing E2 test passes unchanged | `EmulatorPinnedResponses`, test_cr_propagation, test_train_emulator |
| Per-model declaration | the C2UF model declares B/C and 10Be/9Be on ekn, its box as the domain and version `1.0.0+model.<sha12>`; sub-ranges answered by slice; rigidity refused | `EmulatorPerModelDeclaration` |
| Emulator validation | PASSED: 40 held-out USINE runs (30 in the toy box, 10 on the SLIM slice), largest error 0.0038 of the data sigma (tolerance 0.05), none refused by the DomainModel; error component (largest held-out error per bin) added to both datasets' covariance | `test_emulator_validated_against_usine_and_its_error_in_the_covariance` |
| Fits (emulator provider) | BIG converged, chi2 0.0 (dof 23); SLIM converged, chi2 23.927 (dof 25); both equal to the USINE fits of study 2 within 1e-4 in chi2 | record |
| C2UF-1 | MET. BIG: delta chi2 0, toy p-value 1.0 (200 toys, 0 failed), survives at alpha 0.05. SLIM: delta chi2 23.93, no toy of 197 reached it, p < 0.0151 (95% upper bound), excluded at alpha 0.05 (200 toys, 3 failed: 2 refused by the DomainModel, 1 not converged; limit 4). The generator survives | `test_emulator_toy_calibrated_delta_chi2_and_generator_survives` |
| Live | two validation points rerun with USINE (fresh cache, 2 runs): the emulator within 0.05 sigma in every bin | `test_live_emulator_matches_fresh_usine_runs`, `$CRPROP_OUT/c2uf/acceptance/live-emulator-vs-usine.txt` |

USINE runs (A1.8 tally, cap 1000 after A1.14): 520 in dispatch 1, 340 for the emulator (300 training, 40 validation)
and 2 in the live test: 862 of 1000. Emulator evaluations (tens of thousands in the toys) are not USINE runs. The
refinement round was not needed.

## CRPROP-F1 — 2026-10-28 (environment E2)

Work package F1 of the cr-propagation r4 campaign (r3 card §F1, line 462; decisions D8, D9, A1.7-A1.12): reproduction
of Génolini et al. 2019 (arXiv:1904.08917, PRD 99 123028) Table II with USINE through the plugin's USINE provider and
`propagation_fit.py`.

**Criteria and tolerances, fixed before any comparison (R9; this paragraph is the work package's first commit).**
Frozen entries (acceptance.json): F1-1 reproduction within the H0 tolerance D9, every difference attributed
(cross sections, modulation, covariance, numerics, USINE version), a partial reproduction recorded with full
attribution but not enabling F3; F1-2 the data carry `observed`, the covariance its `model-supplied` label, CRDB rows
`secondary`. D9 made operational here (nothing loosened; a miss is recorded and attributed, never re-toleranced):

| Family | delta: published (card), pass window | K10 (kpc^2/Myr): published (card), pass window |
|---|---|---|
| BIG | 0.48 +0.04/-0.03, [0.45, 0.52] | 0.30, [0.266, 0.338] |
| SLIM | 0.51 ± 0.02, [0.49, 0.53] | 0.28, [0.258, 0.304] |
| QUAINT | 0.45 +0.05/-0.02, [0.43, 0.50] | 0.33, [0.297, 0.367] |

- delta windows: the card's central values and 1-sigma errors (Table II as transcribed in r3 §F1), closed intervals.
- K10 = K0 10^delta, K at R = 10 GV with beta = 1 and both break factors set to 1 (their effect at 10 GV is below 1e-6
  for every published best fit), in kpc^2/Myr (1 kpc^2/Myr = 3.0857e21^2 cm^2 / 3.15576e13 s, IAU parsec and Julian
  year, r3 P1); D0_cm2_s of the fit is K0 at R0_gv = 1 GV. The card gives no K10 error; the window is the card's
  central value times 10^(±s), with s the 1-sigma of log10 K10 propagated linearly from the authors' own fit
  covariance of (delta, log10 K0) (`fit_covmatrix.out` of BIG, SLIM and QUAINT in USINE V3.5's
  `doc/DocFiles/2019-Génolini-benchmarks-BC.tar.gz`, the paper's published fit outputs): s = 0.0520 (BIG), 0.0352
  (SLIM), 0.0463 (QUAINT). Table II's own K10 errors could not be read (arXiv is outside the network consent); if they
  differ, the windows above stand and the difference is reported.
- A family passes D9 when both its best-fit delta and K10 lie in their windows and the fit converged (fit_diagnostics
  verdict, boundary_kkt at a bound); a family that does not converge fails. F1-1 passes when all three families pass.
- F1-2 passes when the dataset-record carries `observed`, the covariance block carries `model-supplied`, and every CRDB
  row used as a cross-check carries `secondary`, all visible in the committed records.

**Environment (r3 §0.3, base exception D10).** E2 (macOS arm64), Python 3.13.2 (miniconda; NumPy, SciPy), USINE V3.5
(tag V3.5, commit fb53006d, Apple clang 21.0.0, ROOT 6.38.04) through HEP_USINE_BIN, HEP_USINE_DATA and USINE; runs
under HEP_USINE_RUN_DIR = `$CRPROP_OUT/f1/runs`, provider cache `$CRPROP_OUT/f1/repro/cache`. `git rev-parse
--show-toplevel` = `.claude/worktrees/crprop-f1`; branch `worktree-crprop-f1`; status clean at start; base `6a227a76` =
integration HEAD (decision D10, not `main`); prerequisites C2U (merge 886bb316), B3 (c1b5967d), B1X (2360c294) and B1
(3ed1e89e) are ancestors of HEAD. r3 line numbers rechecked on this base (§F1 at line 462).

**Settings (from the paper's own files, numbers only).** USINE V3.5 ships the paper's initialisation files, fit
outputs and fit covariances (`doc/DocFiles/2019-Génolini-benchmarks-BC.tar.gz`, read in a scratch folder, never
committed) and the covariance its fits name (`inputs/CRDATA_COVARIANCE/cov_AMS02_201105201605__BC_R.dat`, "a toy-model
for the covariance of AMS02 B/C(R) data ... courtesy of L. Derome"). From them: Model1DKisoVc, L = 10 kpc, h = 0.1 kpc,
rhole = 0; K = beta^eta K0 R^delta (1+(Rlow/R)^((deltalow+delta)/0.05))^0.05 (1+(R/Rb)^(Delta/s))^-s, so the plugin's
'usine' low-break form holds with delta_below = -deltalow (this settles known issue 2 of transport_conventions.py for
these files); Kpp of USINE's files; HI 0.867, HII 0.033, He 0.1 cm^-3 (He_to_H_number 0.1/0.9), Te 1e4 K; ionization,
Coulomb, adiabatic losses; BETA decay on, EC off (decay is set explicitly, so the provider default noted by C2UF does
not apply; B/C only); GALPROP opt12 production and Tripathi99+Coste12 inelastic files; ghost97 chart; source q beta^-1
R^-alpha with alpha fixed at the paper's 2.348466 (BIG), 2.33381 (SLIM), 2.360299 (QUAINT); 13C, 15N, 17O, 18O pure
secondaries; network 1H-58Fe. Families: BIG (D0, delta, V_A, V_c, R_break, delta_below free; eta = 1), SLIM (D0,
delta, R_break, delta_below; V_A = V_c = 0), QUAINT (D0, delta, V_A, V_c, eta; no low break). Nuisances as provider
parameters with the Gaussian priors of the fit outputs' "initial setting" (USINE's chi2_nuis is (val - init)^2/sigma^2,
src/TURunPropagation.cc 106-145): phi 0.73 ± 0.10 GV (USINE's force field per isotope), 12C+H->11B norm 1.10 ± 0.12 and
low-energy slope 0.03 ± 0.15 below 8 GeV/n (USINE's fit-mode transformation, src/TUXSections.cc 3912-3921, applied to
the table's nodes). The high break is fixed at each family's published best fit, Deltabreak kept when delta moves:
the shipped files do not determine its priors (the published chi2_nuis is not reproduced by any reading of their
"initial setting"). Starts at the published best fits. Data: the AMS-02 B/C table with per-source errors that USINE
ships (`inputs/CRDATA_COVARIANCE/ERRORS/AMS02_BC_R__PRL117_231102_2016.txt`, PRL 117 231102, 67 bins 1.92-2600 GV;
labelled `observed`); the card's "PRL 120, 021101" is not what the paper's 67-point fit and Derome's covariance
describe, and the profile's dataset record is PRL 117 (boron-to-carbon-2016), so PRL 117 is used (open question below).
HEPData answered HTTP 403 (browser challenge) and the CRDB REST URL redirected to a non-HTTPS dialog page: neither used.
Covariance (model-supplied): build_covariance.py, stat uncorrelated, background, acceptance and scale fully correlated
(as in the shipped matrix; its diagonals equal the table's relative errors within 1e-12), unfolding exp(-|ln R_i - ln
R_j|/0.8169) (length fitted to the shipped unfolding block, rms residual 0.06).

**Results (final HEAD; record `tests/adapters/fixtures/cr_propagation/f1/f1-reproduction.json`, outputs
`$CRPROP_OUT/f1/repro/`).**

| Family | delta (window) | K10 kpc^2/Myr (window) | -2 ln L (paper's chi2_min) | Verdict | D9 |
|---|---|---|---|---|---|
| BIG | 0.500 ([0.45, 0.52]) in | 0.286 ([0.266, 0.338]) in | 83.3 (61.7) | not reported: the fit reached its 550-evaluation cap; lowest cached point | missed (not converged) |
| SLIM | 0.516 ([0.49, 0.53]) in | 0.289 ([0.258, 0.304]) in | 90.3 (61.8) | failed: EDM 0.0020 after a restart from the best fit with steps of 0.3 conditional sigma (0.013 in the first pass) | missed (not converged) |
| QUAINT | 0.483 ([0.43, 0.50]) in | 0.293 ([0.297, 0.367]) out, 1.3% low | 83.8 (62.1) | failed: Hessian not positive definite | missed |

F1-1: NOT MET (D9 not loosened). Best-fit delta lies in the window for all three families and K10 for BIG and SLIM;
QUAINT's K10 is 1.3% below its window; no family has a converged verdict. F1-2: met (record: data `observed`,
covariance note `model-supplied`, all 67 CRDB rows role `secondary`; test UsineF1Record). USINE's force field agrees
with the plugin's force-field tool contract within 3e-5 (11B, 12C, 0.5-1000 GeV/n; test
`test_usine_force_field_agrees_with_the_tool_contract`).

**Attribution** (linear response at each best fit with the cached Jacobian; d log10 K10 = d ln D0/ln 10 + d delta):

| Difference from the paper | Effect |
|---|---|
| Numerics: provider grid (20/decade) vs the paper's 200 bins 1e-3-5e3 GeV/n | B/C within 1.2e-3 (SLIM published point, 3 runs) |
| Network 1H-30Si (SLIM/QUAINT init files) vs 1H-58Fe | B/C up to 0.75%; SLIM d delta -0.0027, d log10 K10 +0.0040; QUAINT +0.0006, -0.0013 |
| SLIM V_A 6, V_c 0.1 km/s (its init file) vs 0 | B/C 0.18%; d delta -0.0007, d log10 K10 +0.0012 |
| Covariance: USINE's relative covariance scaled with the model (the paper's choice) | chi2 at our best fit 107.6 (SLIM), 92.9 (QUAINT); SLIM d delta -0.0083, d log10 K10 +0.0018; QUAINT -0.016, +0.013 (moves QUAINT's K10 to 0.302, inside) |
| Covariance: USINE's unfolding correlation, data-scaled | SLIM -0.0013, -0.0001; QUAINT +0.0099, -0.017 |
| Covariance (P9): unfolding length x0.5 / x2 | SLIM -0.0021, -0.0001 / +0.0019, +0.0035; QUAINT -0.012, +0.021 / +0.0009, +0.0024 |
| Data: the paper's file `AMS02_published_newBCgeo_rigidity.USINE` is not shipped; PRL 117 values used | not testable; the published best fits give chi2 136-233 with every covariance tried (167.3, 236.1, 134.9 with the paper's own), so the excess is not the covariance; our fits prefer a flatter low break (delta_below -0.21 BIG, -0.45 SLIM vs the paper's -0.69, -0.87), i.e. the difference sits in the lowest-rigidity bins |
| Source normalisation: C, N, O to HEAO-3 at 10.6 GeV/n (USINE's shipped CRDB export has no AMS-02 C, N, O) vs AMS-02 at 50 GV | not tested (no data file); enters as an O/C normalisation of B production |
| High break fixed at the published nuisance values | conditions the fit on them; their correlation with delta in the published covariance is 0.07 (BIG) |
| USINE V3.5 vs V3.4 | not testable here |
| Convergence | USINE's -2 ln L changes by ±0.003 for a 1e-7 change of delta (6-digit tables, EPS_INTEGR 1e-4), and the first pass's steps (a quarter of the published sigma) were 2.6 conditional sigma for delta (parabola residuals ±0.11 over ±2 steps): the forward-difference least-squares minimum kept EDM 0.013; with steps of 0.3 conditional sigma EDM is 0.002, at the noise floor and far above fit_diagnostics' 1e-5. QUAINT's V_c (3.2 ± 5.8 km/s near its bound) makes the noisy Hessian indefinite. BIG's first pass stopped on its cap |

**USINE runs (A1.8 tally):** 1693 of F1's 2000 (13 probes and checks, 3 published points, 2 smoke, about 1540 in the
three first-pass fits, 12 + 114 in the SLIM passes, 6 noise and smoothness probes, 3 attribution variants); at most 4
USINE processes at once. Checks: static part of `run_all_checks.py`, naming, wiring, layering, `workflow_check.py`
diff and acceptance, impacted tests (report); ALL-3 deferred to the wave run (A1.5).

**Dispatch 2 (decision A1.16; written before any dispatch-2 refit, R9).** Rebased onto integration `8544d7ca`
(adapter.json now in F1's files; F1's USINE cap 2600). Nothing above is loosened. Declared before the refits:
- Noise (step 1): `usine_translate.py` gains `--usine-tolerance NAME=VALUE` (EPS_ITERCONV, EPS_INTEGR, EPS_NORMDATA;
  defaults 1e-6, 1e-4, 1e-10 render byte-identically). Measured at BIG's lowest cached point, delta + 0 / 1e-7 / 2e-7:
  -2 ln L = 82.13506 / 82.13462 / 82.13511 with the defaults and the same three numbers, digit for digit, with
  EPS_ITERCONV 1e-9 and EPS_INTEGR 1e-7 (6 runs, 7.8-8.9 s each, no cost difference). The tolerances do not set the
  noise (in Model1DKisoVc EPS_INTEGR enters only SecondaryProduction, src/TUModel1DKisoVc.cc 210-217, and the
  iteration had converged); the floor is USINE's 6-significant-digit tables (B/C changes of 2-4e-6 for a 1e-7 change of
  delta): about ±0.0005 (BIG here) to ±0.003 (SLIM) in -2 ln L. The provider is therefore run with its defaults.
- Restarts (step 2): each family from its lowest cached point with difference steps of 0.3 conditional sigma (SLIM,
  QUAINT: from their first-pass Fisher matrices; BIG: from the precision matrix of the paper's BIG fit covariance,
  `BIG_RESTART_STEPS`), polish off, no restart after a failed verdict. SLIM's pass 2 (above, EDM 0.0020) already is this
  restart and is not repeated.
- QUAINT V_c: refitted as the declared variant QUAINT-Vc0, V_c fixed at its lower bound 0 (the paper's QUAINT best fit
  lies on its own lower bound, 0.1 km/s; ours is 3.2 ± 5.8 km/s; its flat direction makes the noisy Hessian indefinite).
  The bound is accepted when boundary_kkt holds there: -2 ln L at V_c = 0.5 km/s minus at V_c = 0, at the variant's best
  fit, is >= 0 (one run). D9 is judged for QUAINT on the variant if the bound is accepted, else on the free fit.
- Paper's covariance choice (step 4, if budget remains): QUAINT-Vc0 refitted with USINE's shipped relative covariance
  (all five error types) times the QUAINT-Vc0 best-fit prediction, held fixed during the fit; a model alternative (P9),
  reported next to D9, never replacing the nominal verdict.
- The convergence criterion stays the fit_diagnostics verdict (EDM <= 1e-5, positive-definite Hessian, boundary_kkt);
  if it is not reached at the noise floor, it is reported with the measured noise and the work stops.

**Dispatch 2 results (record `tests/adapters/fixtures/cr_propagation/f1/f1-reproduction.json`, regenerated).**

| Fit | delta (window) | K10 (window) | -2 ln L | Verdict | Runs |
|---|---|---|---|---|---|
| BIG, restart from its lowest cached point | 0.500 in | 0.286 in | 83.34 | failed: EDM 0.046 (V_A held as exactly flat); least_squares stopped at the start (xtol) | 212 |
| SLIM, pass 2 (dispatch 1) | 0.516 in | 0.289 in | 90.31 | failed: EDM 0.0020 | 114 |
| QUAINT free (dispatch 1) | 0.483 in | 0.293 out | 83.78 | failed: Hessian not positive definite | 540 |
| QUAINT-Vc0 (V_c = 0, declared variant) | 0.459 in | 0.323 in | 84.02 | failed: EDM 0.00050, Hessian positive definite | 234 |
| QUAINT-Vc0, the paper's covariance choice (model alternative) | 0.453 in | 0.319 in | 91.75 | stopped on its 200-evaluation cap; lowest cached point | 200 |

QUAINT V_c bound: -2 ln L rises by 5.08 from V_c = 0 to 0.5 km/s at the variant's best fit, so boundary_kkt holds and
QUAINT is judged on QUAINT-Vc0 (delta chi2 0.24 against the free fit). F1-1 stays NOT MET, only on the convergence
criterion: every judged family (BIG, SLIM, QUAINT-Vc0) has delta and K10 in their windows, and none reaches the
fit_diagnostics verdict. The verdict is unreachable at USINE's noise floor: tighter USINE tolerances change no output
digit (step 1), the remaining noise is the 6-significant-digit tables (±0.0005 to ±0.003 in -2 ln L), and the EDM
reached at steps of 0.3 conditional sigma (5e-4 to 5e-2) stays above 1e-5. Reported as a known issue; the criterion is
not loosened. Data stay PRL 117: the paper's 67 points and Derome's covariance describe the 2011-05/2016-05 B/C of PRL
117 (231102), which is also the profile's dataset record (boron-to-carbon-2016); the card's PRL 120 (021101) is not the
set the target fits used. USINE runs: 2347 of F1's 2600 (dispatch 2: 6 noise probes, 212 BIG, 234 QUAINT-Vc0, 1 V_c
bound check, 200 paper-covariance refit; at most 4 USINE processes at once). Rebased onto integration `3547f9a0`
(C2UF): `propagation_fit.py` keeps C2UF's step-based polish in `_verdict` (it returns the polished point as "x") and F1's
`optimizer.polish_steps` now uses that path for provider fits; F1's priors, provider-side modulation (each request
carries only its own datasets' periods, also with C2UF's per-point requests) and C2UF's response model kind "provider"
and per-point requests coexist; the hep_statistics tests, `test_cr_propagation` offline and C2UF's UsineEmulatorFamilies
pass.

## CRPROP-RC — 2026-10-29 (environment E2)

Work package RC of the cr-propagation r4 campaign (`workflow-r4.md` §10): campaign report
`docs/dev/cr-propagation/campaign-report.md` and pull-request draft `docs/dev/cr-propagation/pr-draft.md`;
documentation only, no code or acceptance entry changed. **Environment field (r3 §0.3, base exception D10):**
`git rev-parse --show-toplevel` = `.claude/worktrees/crprop-rc`; branch `worktree-crprop-rc`; status clean at start;
base 47b004b4 = integration HEAD (not `main`; decision D10), rebased in rework round 1 onto 9b121eae
(status.json commits only); the merges of the RC prerequisites F1 (3ccaa643) and C2UF
(dee1179b) are ancestors of HEAD; `main` 8fcbb826 is an ancestor of HEAD (main has not moved, no rebase needed).

| Check | Result |
|---|---|
| `run_all_checks.py --part static --jobs 4` | exit 0, 31 checks pass, 0 fail (rework round 1, on the rebased branch) |
| `check_naming.py` | pass, no new findings, `naming_known_gaps.json` not grown |
| `check_wiring.py --since 47b004b4` | pass |
| `workflow_check.py diff --work-package RC --base 9b121eae`, `acceptance` | both ok; changed files only the 4 RC files; frozen sha256 f5b0dbe6…, 86 frozen entries, 17 added |
| Full `run_all_checks.py` and `check_relocation.py` (WF-10, wave 6, orchestrator) | final confirmation run on the release commit 790ef3e7 (after the wave-6 fixes and the 0.43.0 bump): full `run_all_checks.py --no-cli --jobs 4` passes in E2 (31 pass, 0 fail, 2 skipped CLI host checks; 6000 tests in 480 modules, 0 failures, 168 skipped) and with the CI lock (31 pass, 0 fail, 2 skipped; 6000 tests, 0 failures, 263 skipped); `check_relocation.py` shows only the 2 known geant4 path-with-spaces failures, identical on `main` |

RC has no acceptance entries of its own beyond WF-2 to WF-10, which its verifier checks against section 9 of the
report. Every number in the report is taken from `status.json`, `decisions.md`, `escalations.md`, `acceptance.json`
and the CRPROP sections above.

## CRPROP-CIFIX — 2026-10-29 (environment E2)

Cross-WP fix of the PR #308 CI failures on Linux (decision A1.20; rework round 1 of the B1, B2, D1, D3, E2 and C2UF
tests). **Environment field (r3 §0.3, base exception D10):** `git rev-parse --show-toplevel` =
`.claude/worktrees/crprop-cifix`; branch `worktree-crprop-cifix`; status clean at start; base 26222205 = integration
HEAD (not `main`). Linux was not available: the fixes are checked on macOS in E2 and in the CI-lock venv.

Cause of the C2UF `--declaration` KeyError: the C2UF emulator model's first kernel matrix (738 points, nugget 1.1e-12,
condition about 3e19) is numerically singular. On macOS its Cholesky factorization happens to succeed; with the
kernel entries perturbed by one or two units in the last place (as another libm/BLAS gives) it fails in 41 of 50
trials, so the provider refused the model ("kernel matrix cannot be factorized") and `--declaration` printed
`{"status": "failed", ...}`. Even when it factorizes, the self-check ln sigma moves by about 2e-7 under such
perturbations, above the provider's 1e-9. Fix in `emulator_provider.py`: if the matrix as stored does not factorize,
a jitter of 1e-14, else 1e-13, times its mean diagonal (perturbed: 0/40 failures at 1e-14); the self-check compares
ln sigma within 2e-6 (a 1e-13 jitter moves it by 1e-6), ln mean still within 1e-9 (the mean uses the stored alpha,
not the factor). On macOS the factorization succeeds as before, so the E2 and C2UF responses there are unchanged
(the pinned E2 responses still agree).

Test tolerances added (no acceptance entry, VALIDATION tolerance or criterion changed; no fixture regenerated):

| Test | Comparison | Tolerance | Reason |
|---|---|---|---|
| profile `test_provider` `test_values_are_the_closed_form` | provider values against the committed benchmark prediction | relative 1e-12 | libm last digits (Linux drift 1 ulp) |
| `UsineReader.test_results_file_is_recomputed` | recomputed ratios against `usine-results.json` | relative 1e-12 | libm last digits (Linux drift 4e-16) |
| `D3CrossCode.test_ports_of_dragon2_code_and_inelastic_table` | `table_nodes()` against the committed inelastic table grid | relative 1e-12 | libm `pow` last digits |
| `D3CrossCode.test_dragon2_runs_are_recorded_and_translated` (passed on Linux, hardened) | rebuilt DRAGON2 specs against the committed specs | relative 1e-12 on floats | libm last digits |
| `EmulatorValidation.test_holdout_criteria` | recomputed `dchi2_max`, `pull_max` against the recorded numbers | relative 1e-4 (was absolute 1e-9) | GP linear algebra (Linux drift 3e-7 relative); E2-1 and E2-2 checked unchanged |
| `EmulatorPinnedResponses.test_e2_responses_are_unchanged` | E2 responses against the macOS-pinned ones | relative 1e-4 (was 1e-12) | GP sigma of an ill-conditioned kernel (Linux drift 6e-6 relative) |

`EmulatorPerModelDeclaration.setUpClass` now fails with the provider's exit code, stdout and stderr if
`--declaration` gives no declaration.

| Check | Result |
|---|---|
| `tests.adapters.test_cr_propagation`, `tests.skills.hep_statistics.test_propagation_fit`, `tests.skills.hep_ml.test_train_emulator` | E2 and CI-lock venv: 164 tests OK (15 skipped) |
| profile tests theory:cr-secondary-ratio | E2 and CI-lock venv: 70 tests OK |
| impacted tests (`rule_registry.py impact`) | 200 tests OK |
| `check_naming.py` | pass |
| `run_all_checks.py --part static --jobs 4` | exit 0, 31 checks pass, 0 fail (includes the profile tests) |
| Full `run_all_checks.py`, `check_relocation.py`, `workflow_check.py diff` | deferred to the orchestrator (A1.5; cross-WP branch) |

**Rework round 2 (2026-10-29, base 12bdcc5b).** PR #308 CI run 2: everything passes except
`EmulatorPerModelDeclaration.setUpClass`. On Linux the C2UF kernel now factorizes, but `--declaration` refuses with
"the model does not reproduce its self-check predictions". Cause: with a near-singular kernel the stored alpha weights
are huge, so 1-ulp libm differences in the kernel evaluations k(x*, X) are amplified in the ln mean, not only in
sigma.

Drift simulation (macOS, E2 venv; scratch script outside the repository). Every kernel evaluation, both K(X, X) and
k(x*, X), was multiplied entry by entry by 1 + n eps/2 with n drawn from {-2, -1, 1, 2} (K kept symmetric). The model
was loaded through the provider and its self-check points predicted again. 120 trials per model (2 seeds x 60).
Deviations are the maximum over the self-check points and outputs, against the stored values:

| Model | max abs ln-mean deviation | max ln-mean deviation / sigma | max abs ln-sigma deviation | max ln-sigma deviation / sigma | stored ln sigma |
|---|---|---|---|---|---|
| E2 (`e2/emulator-model.json`) | 2.0e-9 (median 9e-10) | 9.1e-7 (median 4.4e-7) | 1.8e-9 | 8.8e-7 | 1.4e-3 to 7.8e-3 |
| C2UF (`c2uf/emulator-model.json`) | 7.4e-7 (median 4.3e-7) | 2.5e-2 (median 1.1e-2) | 8.7e-8 | 4.4e-3 | 1.9e-5 to 1.2e-4 |

Even E2 exceeded the old absolute 1e-9 on ln mean in a large fraction of the trials (median 9e-10, max 2.0e-9), so it passed CI by chance. New
self-check criterion (`emulator_provider.py`): ln mean and ln sigma each within max(1e-9, 1e-4 x the stored ln sigma)
at every check point and output. That is a drift far below the emulator's own uncertainty. The factor 1e-4, below the
proposed 1e-3, leaves E2 a margin of about 110, and E2 is accepted in 120 of 120 trials. The C2UF model's mean drift
reaches 2.5e-2 x sigma, 25 times even the 1e-3 bound, and it is refused in 120 of 120 trials. **The C2UF model is not
portable across libm implementations; it stays refused there.** No further loosening (A1.20 instruction). A refusal
now reports, for ln mean and ln sigma, the worst deviation (absolute, x sigma, relative) and the check point and output
where it occurs. On macOS both models reproduce their self-checks exactly (deviation 0), so the responses there are
unchanged. `EmulatorPerModelDeclaration` and the C2UF-dependent CI result therefore still fail on Linux. Options for
the orchestrator: retrain the C2UF emulator with a nugget floor that bounds the kernel's condition number (hep-ml
`train_emulator.py`, NUGGET_BOUNDS lower edge 1e-12), or mark that test as platform-bound.

| Check (round 2) | Result |
|---|---|
| `test_cr_propagation`, `test_propagation_fit`, `test_train_emulator`, `test_adapter_missing_dependency`, `test_cli_robustness` | E2 and CI-lock venv: 172 tests OK (15 skipped), pinned E2 responses and C2UF tests included |
| `run_all_checks.py --part static --jobs 4` | exit 0, 31 pass, 0 fail |
| `check_naming.py` | pass |

**Rework round 3 (2026-10-29, base 600c313a, decision A1.21).** The C2UF emulator fixture is platform-bound (A1.21):
its tests skip on the provider's self-check refusal and on nothing else; the follow-up is retraining it with a nugget
floor in `train_emulator.py`. The round-2 criterion is kept. Skip points:
- `EmulatorPerModelDeclaration.setUpClass` raises `unittest.SkipTest` only when `--declaration` returns status failed
  with "does not reproduce its self-check predictions". The skip reason names A1.21 and carries the provider's
  deviation message. Any other failure (another error, bad JSON, a missing key) still fails.
- `test_propagation_fit` `test_live_emulator_matches_fresh_usine_runs` (live only: HEP_USINE_LIVE_TEST) loads the C2UF
  emulator through the provider via `emulator_registry`. It skips on the same refusal only.
- No other test loads the C2UF emulator. The E2 tests (`EmulatorPinnedResponses`, `EmulatorProviderConformance`,
  `EmulatorProviderRefusals`, `EmulatorArtifact`, `EmulatorValidation`) are never skipped.

Skip path exercised locally with the self-check bound forced negative (not committed): `setUpClass` skipped with the
A1.21 reason and the deviation message, and `EmulatorPinnedResponses` failed (the E2 model refused, not skipped), as
intended. That run exposed a defect: the deviation message's worst-point search divided by a zero bound. It now picks
the point furthest beyond its bound (NaN counts as worst).

| Check (round 3) | Result |
|---|---|
| `test_cr_propagation`, `test_propagation_fit`, `test_train_emulator`, `test_adapter_missing_dependency`, `test_cli_robustness` | E2 and CI-lock venv: 172 tests OK (15 skipped); on macOS the C2UF declaration tests run and pass (not skipped) |
| `run_all_checks.py --part static --jobs 4` | exit 0, 31 pass, 0 fail |
| `check_naming.py` | pass (the skip constants named `SELF_CHECK_REFUSAL`, `TWO_DATASET_EMULATOR_NOT_PORTABLE`) |

## CRPROP-K2 — 2026-10-29 (environment E2)

Work package K2 of follow-up wave 7 (decision B1.1, issue 2 of the 0.43.0 known issues): provider-side modulation
becomes a declared, checked exception to "providers never modulate". Contracts 3.15.0 (one minor, gating constant
`validate.MODULATION_FROM`), `CORE_VERSION` 1.3.0 (core/provider behaviour changes).

Environment: E2 (macOS arm64, Python 3.13.2; examples and fixtures regenerated with the E2 venv). Base exception D10:
base is the integration HEAD `94ba34d1` (worktree-crprop-k), not `main`. r3 §0.3 checks at start:
`git rev-parse --show-toplevel` = `.claude/worktrees/crprop-k2`; `git branch --show-current` = `worktree-crprop-k2`;
`git status` clean; base `94ba34d1` is an ancestor of HEAD; no prerequisite work package (K2 `deps` empty; requires
`env-usine`: USINE V3.5 through `HEP_USINE_BIN`, `HEP_USINE_DATA`). `origin/main` is `42f5bad1` (0.43.0).

Acceptance entries (frozen in `docs/dev/cr-propagation/acceptance.json`): K2-1, K2-2 (tolerance 1e-3) and ALL-*.

What changed:
- `contracts/schemas/cr_provider.json`: optional declaration block `modulation` {model `force-field` (const),
  implementation, parameters [`phi_<period>_gv`], conformance {reference_point, observables, tolerance <= 1e-3,
  result {status `passed` (const), max_relative_deviation, nodes_compared, isotopes, tool}}}; the "never modulate"
  wording now says "unless the declaration carries a modulation block".
- `core/provider/protocol.py`: `check_declaration` refuses a `phi_<period>_gv` in the domain without the block, a
  block parameter outside the domain, an unlisted phi of the domain, a reference point that does not set exactly one
  modulation parameter or leaves the domain, an undeclared observable, a tolerance outside (0, 1e-3], a result that is
  not `passed` or whose deviation exceeds the tolerance (the registry, `parse_registry`, uses it, so such a
  declaration is refused). `point_refusal`: two modulation parameters in one point give `invalid-request` (runner and
  provider side). `check_modulation`: a top-of-atmosphere prediction without the block, a top-of-atmosphere prediction
  for a point without a modulation parameter, or another level for a point with one, is an invalid response; the
  runner applies it to fresh and cached results, the PRV conformance check to its single-shot response. A phi sent to
  a provider without the block stays `unknown-parameter` (it cannot be in the domain).
- `contracts/validate.py`: `MODULATION_FROM = "3.15.0"`; rule `prediction.modulated_twice` (more than one nonzero
  `phi_<period>_gv` in a prediction's parameter point), native from 3.15.0, else `--strict`; fixtures
  `valid/prediction_modulated_once.json`, `invalid/prediction_modulated_twice.json`.
- `tools/provider_registry.py --conformance PROVIDER [--reference-point] [--observables] [--tolerance] --out`:
  `modulation_conformance()` loads the entrypoint module's hook `isotope_tables(request, point)`, asks it for the
  isotopic LIS (the point without its modulation parameter: a run without modulation) and the modulated per-isotope
  output, applies the plugin's force-field tool (`solar_modulation_force_field.py --modulate --lis-table`, one call
  per node, the tool contract) to the LIS at every top-of-atmosphere node whose LIS energy lies inside the LIS table,
  and passes when every relative deviation is within the tolerance. `usine_provider.py` gains the hook.
- `adapters/cr-propagation/adapter.json`: the USINE declaration carries the block with its result (dragon2 and
  emulator entries untouched).
- `propagation_fit.py`: provider-side modulation is decided from the declared block (`modulation_parameters`), not
  from a phi in the domain; the result's `modulation` adds the declared `model` and `implementation`; a
  top-of-atmosphere first prediction for a dataset the fit did not ask the provider to modulate is refused
  (`double-modulation`). The fit-side isotopic path stays the documented default, not implemented (refusal
  `modulation-needs-isotopic-lis`, detail extended). Docstring and `core-stats-commands.md` updated; the hep-theory
  `cosmic-ray-phenomenology.md` does not state the provider rule (unchanged).

Conformance gate run (`$CRPROP_OUT/k2/conformance/`, two USINE runs of the 20 allowed): reference point
D0_cm2_s 3e28, delta 0.5, L_kpc 4, phi_2011_2016_gv 0.7312345 GV on the provider's DEFAULT_TRANSPORT (ILLUSTRATIVE
isotopic cross sections, network to O-16); observables B/C (rigidity 2-1000 GV, 4 bins) and 10Be/9Be (ekn 0.1-10
GeV/n, 2 bins); tolerance 1e-3. Result: passed, largest relative deviation 4.28e-5 over 390 nodes of 10B, 10Be, 11B,
12C, 9Be (13C is not in that network). Runs in temporary folders (no computational-run record kept).

| ID | Result | Evidence |
|---|---|---|
| K2-1 | pass | contracts 3.15.0 with `MODULATION_FROM`; schema/core agreement `tests.core.test_provider.DeclaredModulation` (8 tests: 9 bad blocks refused by both, 6 cross-field rules core-only and named so, registry refusal of a non-passing result, top-of-atmosphere without the block `invalid-response`, levels with the block, two potentials `invalid-request` before the provider runs and on the provider side, phi without the block `unknown-parameter`, a cached top-of-atmosphere result refused); every committed artifact keeps its outcome (below); ruff 0.16.10 and mypy 2.4.0 clean on `core/` and `contracts/` |
| K2-2 | pass | gate run above (4.28e-5 <= 1e-3, tolerance 1e-3, no looser than F1's); offline replay on USINE's recorded F1 tables (`tests.tools.test_provider_registry.ModulationConformance`: passes below 1e-4 on 11B and 12C; a provider off by 0.2% fails; refusals); `propagation_fit` uses the declaration (`test_provider_side_modulation_needs_the_declared_modulation_block`); F1 unchanged (below) |
| ALL-1 | pass | this section |
| ALL-2 | pass | `workflow_check.py acceptance` exit 0 |
| ALL-3 | deferred to the wave run (A1.5) | |
| ALL-4 | pass | `check_naming.py`, `workflow_check.py gaps --base 94ba34d1` |
| ALL-5 | pass | `check_layering.py`, `workflow_check.py diff --work-package K2 --base 94ba34d1` |
| ALL-6 | pass | `check_packaging.py` |
| ALL-7 | pass | worker report |

F1 unchanged, no new fit and no USINE run (`$CRPROP_OUT/k2/f1-verify/verify_f1.py`, `verify_f1.json`): for BIG, SLIM,
QUAINT and QUAINT-Vc0 of the committed `f1-reproduction.json`, the best-fit point (with the family's fixed values)
was evaluated through the K2 runner and registry from F1's provider cache with `HEP_USINE_BIN` unset: 0 points sent,
each prediction identical to the cached raw result (level top-of-atmosphere, accepted by `check_modulation`), and
-2 ln L recomputed from it (data covariance plus the F1 priors) equals the record's chi2 within relative 2.3e-16
(criterion 1e-9). The fit's decision is unchanged: provider-side for period 2011_2016 under the old rule (phi in the
domain) and the new one (phi in the declared block); the double-modulation guard accepts these predictions.
`tests.adapters.test_cr_propagation` (F1 record and force-field tests) passes.

Every committed artifact keeps its outcome (`$CRPROP_OUT/k2/outcome/`): all 696 committed JSON artifacts of the base
tree (`git archive 94ba34d1`) validated with the base and the K2 validator, default and `--strict`: ok flag and sorted
findings (severity, path, code) identical for all 696, the restamped ones included. The bump changed only version
strings and the hashes that cover them (fixtures, design fixtures, three skill templates, 13 theory-profile artifacts,
14 examples); `bc-propagation-fit` and `unfolding-coverage` were not rerun.

| Check | Result |
|---|---|
| Impacted tests (`rule_registry.py impact`: 35 modules, plus `test_cr_propagation`, `test_adapter_declarations`, `test_provider_conformance_mixin`) | 706 tests OK (17 skipped) |
| `tests/examples` | 176 tests OK (22 skipped) |
| theory-profile tests (9 profiles) | all pass |
| `run_all_checks.py --part static --jobs 4` | exit 0 after `tools/reference_inventory.py` was rerun (`core-stats-commands.md` grew) |
| `check_naming.py`, `check_wiring.py --since 94ba34d1`, `check_layering.py`, `check_packaging.py`, `workflow_check.py diff/gaps/acceptance` | pass / ok |
| ruff 0.16.10 and mypy 2.4.0 on `core/` and `contracts/` | clean |

Open: `docs/adapter-authoring.md` still says "providers never modulate" without the exception; it is outside K2's file
list (for the orchestrator). The USINE provider's conformance result was obtained at provider version 0.2.0; the
gate is rerun when the modulation implementation changes (the registry does not compare versions). Not run: ALL-3
(deferred to the wave run, A1.5), any new fit, a live routing run.

## CRPROP-K4 — 2026-10-29 (environment E2)

Work package K4 (decision B1.1, follow-up wave 7). Goal: an emulator nugget floor that bounds the kernel condition
number (K4-1); the C2UF emulator retrained with it, made portable and C2UF-1 re-run, with the A1.21 skip removed (K4-2).
Outcome (B1.2): K4-1 met; C2UF-1 not met on the retrained emulator, so the committed C2UF emulator and the A1.21 skip
are kept. SYNTHETIC data only; every input ILLUSTRATIVE.

**Environment field (r3 §0.3, base exception D10):** E2 (macOS arm64 workstation), Python 3.13.2 (miniconda), NumPy
2.4.4, SciPy 1.17.1; USINE V3.5 (tag V3.5, commit fb53006d) through HEP_USINE_BIN and HEP_USINE_DATA, runs under
HEP_USINE_RUN_DIR = `$CRPROP_OUT/k4/runs`, provider cache `$CRPROP_OUT/k4/cache` (a copy of C2UF's; C2UF's left
unchanged). `git rev-parse --show-toplevel` = `.claude/worktrees/crprop-k4`; branch `worktree-crprop-k4`; status clean
at start; base 94ba34d1 = integration HEAD (`worktree-crprop-k`), not `main`; no prerequisite work package (deps []),
C2UF and CIFIX (A1.20, A1.21) are ancestors of the base.

### Kernel condition bound (K4-1; chosen before the C2UF retraining)

Diagnosis of the committed models (eigenvalues of each component's kernel matrix K = K_f + nugget I, NumPy `eigvalsh`):

| Model | Points | Largest cond(K) | Nugget at the NUGGET_BOUNDS floor 1e-12 | Self-check drift (CIFIX simulation, 120 trials) |
|---|---|---|---|---|
| E2 (`e2/emulator-model.json`) | 110 | 1.3e13 (component 0; 3.8e12, 2.7e11, 1.2e10 next) | 6 of 13 components | max 9.1e-7 x sigma: margin about 110 against 1e-4 x sigma |
| C2UF (`c2uf/emulator-model.json`, A1.14) | 738 | numerically singular: components 0-4 have negative computed eigenvalues (-5e-11 to -2e-9 against largest 2e5 to 7e6), components 5-11 have 5e16 to 1e12 | nugget/signal 4e-15 to 2e-10 | max 2.5e-2 x sigma: refused in 120 of 120 |

Bound: `train_emulator.py --max-condition C` (default `MAX_CONDITION` = 1e10; 0 = no bound). Every Matern entry is at
most the signal variance s, so the largest eigenvalue of the noise-free n x n kernel is at most n s (Gershgorin) and the
smallest is >= 0; a nugget of at least n s / (C - 1) therefore keeps cond(K) <= C for any length scales. The optimizer
then works in log(nugget / s) with that lower bound (the lower bound on nugget / s is max(n / (C - 1), 1e-12), that is
NUGGET_BOUNDS' 1e-12 applied to the ratio; the upper edge becomes 0.1 s); the starts are the same absolute values moved inside the bounds. The trained model records
`training.max_condition`, `training.relative_nugget_floor` and per component `condition_number` (computed); a model
trained with `--max-condition 0` records none of them and is byte-identical to one trained before K4.
Why 1e10: a reader on another libm/BLAS sees the kernel entries change by a few ulp (eps = 2.2e-16); the GP weights
alpha = K^-1 y then move by up to about cond x eps relative, so C = 1e10 bounds that at about 2e-6 relative, while the
provider's self-check needs ln mean and ln sigma within 1e-4 x sigma (CIFIX round 2), and the C2UF emulator's sigma is
tiny (2e-5 to 1e-4 in ln). An exploratory retraining (no USINE run; drift only, no validation number looked at) gave
self-check drifts of at most 3.1e-8 x sigma at C = 1e10 (margin 3200 against 1e-4) and 6.8e-10 x sigma at C = 1e8.

E2 is not retrained: its committed model and every E2 test are unchanged (the bound acts at training time only; the
provider and the committed model files are untouched). Since E2's model has cond up to 1.3e13, a retraining at the new
default would change it, so E2's campaign script (`e2/emulator_campaign.py`) now passes `--max-condition 0`, which
reproduces the training as before (no new field in the model, same optimizer coordinates). The synthetic models of
`test_train_emulator.py` train at the default and keep their accuracy assertions (held-out relative error < 1e-2).

### C2UF emulator retraining (K4-2): settings written before the recorded training (R9)

| Item | Pre-declared setting or criterion |
|---|---|
| Training | as C2UF dispatch 2 (A1.14), unchanged except the bound: `usine_emulator_family_study.py train --round 0` (every cached USINE run of the study inside the box BOX = ln D0 1.9e28-4.0e28 (log), delta 0.40-0.535, V_A 0-105, V_c 0-9.5 km/s, minus the held-out validation and confirmation points, duplicates to 1e-9 dropped: the same 738 points as C2UF), Matern-5/2 GP per principal component of ln values, `--pca-tolerance 1e-4`, `--restarts 4`, `--seed 20261028`, and `--max-condition 1e10` (stated explicitly in the script); outputs ln B/C (15 bins) then ln 10Be/9Be (12 bins); no new USINE run for training |
| Validation (pre-declared in C2UF, not loosened) | the same 40 held-out USINE runs (30 uniform in the toy box, 10 on the SLIM slice, seed 20261029, all cached); pass when at every point, in every bin of both datasets, abs(emulator - USINE) <= 0.05 of the data sigma; a point the DomainModel refuses fails. If it fails: C2UF-1 is reported not met with the numbers (no refinement round, no tuning) |
| Confirmation over the toys' domain (new; the C2UF advisory) | the toy fits of kind "provider" are bounded by the model's whole box (k = 4), while the validation covered the toy box (k = 3); the C2UF fit's 77704 emulator evaluations include 2320 outside the k = 3 box (V_c above 7.108 km/s: 2206, V_A above 94.56: 116, delta: 1). 40 new USINE runs: 30 uniform in BOX and 10 uniform on the SLIM slice V_A = V_c = 0 over BOX's ln D0 and delta ranges (seed 20261031). Pass when every point the DomainModel accepts is within 0.05 of the data sigma in every bin; a refused point is listed (in the fit it is a failed toy, counted against the 2% limit, not a wrong answer). Its largest error per bin does not enter the covariance (P10 keeps the holdout's) unless it exceeds the holdout's, in which case C2UF-1 is reported with that finding and not re-run |
| Drift (portability) | the CIFIX drift simulation (`$CRPROP_OUT/k4/scripts/drift.py`, kernel entries x (1 + n eps/2), n in {-2, -1, 1, 2}, K kept symmetric), 2 seeds x 60 trials: accepted by the provider's self-check in every trial with max deviation <= 1e-5 x sigma (margin >= 10 against 1e-4) |
| C2UF-1 rerun | `usine_emulator_family_study.py fit` unchanged (emulator provider with the new per-model declaration, the holdout error component in both covariances, families BIG and SLIM, starts, steps, 200 toys per family, seed 20261028, alpha 0.05, the 2% toy-failure limit); pass as declared in C2UF (BIG and SLIM converge; each listed with delta chi2 and toy p-value; at most 2% failed toys; BIG survives at alpha 0.05). If it does not pass: reported PARTIAL with the numbers, nothing tuned |
| D7 / B1.1 | K4 cap 100 USINE runs; planned 40 (confirmation) + 2 (live test); tally in `$CRPROP_OUT/k4/tally.json` (ProviderRunner `points_sent`); one USINE process at a time |

### Results (K4-2 retraining and the C2UF-1 rerun)

Every number below is from `$CRPROP_OUT/k4/` (outside the repository; the attempt's record, model and ml-artifact are
in `$CRPROP_OUT/k4/k4-attempt/`).

| Item | C2UF (A1.14, committed) | K4 retraining (`--max-condition 1e10`) |
|---|---|---|
| Training set | 738 cached USINE runs | identical document (the same 738 points and values) |
| Model | `1.0.0+model.0a8dc86fdf16`, 19 components | `1.0.0+model.9b95e7465422`, 19 components; the nugget floor is active in 16 of 19 (nugget/signal = 7.38e-8 = 738 / (1e10 - 1)); components 15, 16 and 17 sit above it (nugget/signal 8.9e-8, 4.3e-7, 1.2e-6) |
| Largest kernel condition number | singular (computed eigenvalues below 0 in components 0-4; 5e16 in component 5) | 9.7e9 (every component <= 1e10) |
| Holdout (40 cached runs, 0.05 sigma, not loosened) | passed, largest error 0.0038 sigma, largest relative 2.07e-4 | passed, largest error 0.0032 sigma, largest relative 1.89e-4; none refused. Per bin, the largest error is 0.74-3.7 times C2UF's (worst in the B/C bins 12-14) and stays below 0.0033 sigma in every bin |
| Confirmation over the model box (k = 4; 40 new USINE runs, seed 20261031) | not run | passed: largest error 0.0226 sigma (point ln D0 = ln 2.41e28, delta 0.469, V_A 103.8, V_c 4.33: the high-V_A edge); 15 points inside the toy box, worst 0.0025; 25 outside it, worst 0.0226; none refused. The largest error per bin is above the holdout's in all 27 bins (1.6 to 19 times). As declared, the covariance keeps the holdout component |
| Self-check drift (2 seeds x 60 trials) | refused in 120 of 120; max 2.5e-2 x sigma | accepted in 120 of 120; max ln-mean deviation 3.1e-8 x sigma (2.0e-12 absolute), ln-sigma 4.7e-9 x sigma; margin 3217 (seed 1) and 3831 (seed 2) against 1e-4 x sigma, so the >= 10 criterion holds |
| Fits (emulator provider) | BIG chi2 1.3e-8, SLIM chi2 23.9272 | BIG chi2 1.1e-8 (D0 3.000003e28, delta 0.4500, V_A 70.00002, V_c 0), SLIM chi2 23.9274 (D0 2.50899e28, delta 0.48392); both converged, equal to the USINE fits of study 2 within 1e-3 in chi2 |
| BIG's toys (200) | 0 failed, p 1.0 (200/200), survives | 0 failed, p 1.0 (200/200), survives |
| SLIM's toys | 200 run, 3 failed (2 out of domain, 1 restart cap), p < 0.0151 (0/197), excluded | **stopped at the 2% limit after 37 toys**: 5 failed (BIG's fits to SLIM's toys 3, 5, 31, 36 at the restart cap; toy 10 out of the provider domain), 32 ok; family calibration `failed`, reason `toy-failure-threshold` |
| C2UF-1 | MET | **NOT MET with the retrained emulator** (the calibration fails before SLIM's p-value is computed) |

USINE runs (B1.1 cap 100 for K4, `$CRPROP_OUT/k4/tally.json`): 0 for training and the holdout (all cached), 40 for the
confirmation: 40 of 100. The live test was not run (the committed fixture is unchanged).

Per the assignment (stop rather than tune), the retrained model was **not committed**. The C2UF fixtures
(`usine-emulator-family-study.json`, `emulator-model.json`, `emulator.ml-artifact.json`), their tests and the A1.21 skips
in `EmulatorPerModelDeclaration.setUpClass` and `test_live_emulator_matches_fresh_usine_runs` are left as on the base.
The A1.21 skip stays until a portable model also passes C2UF-1. What is committed: the bound in `train_emulator.py` (K4-1)
and its tests; `--max-condition 0` in E2's campaign; in `usine_emulator_family_study.py`, a `--max-condition` option
(default 0 reproduces the committed A1.14 model: rerun of the train step from the K4 cache gave the same training set and a model byte-identical to the fixture, sha256 0a8dc86f...; K4 used 1e10) and a `confirm` step (the k = 4 confirmation above, kept
in the record when present). These are tooling only and change no committed result. Not diagnosed here, since diagnosing
would mean trying variants: why BIG's fits to SLIM's toys reach the restart cap more often with the regularized emulator
(4 of 37 against 1 of 200 before). The bound makes the GP mean a non-interpolating smoother with a nugget of 7.4e-8 x
signal (its holdout accuracy is unchanged), and the toy fits near V_A = 0, where B/C depends on V_A^2, were already the
fragile case in C2UF (dispatch 2, diagnosis 3). Options for the orchestrator: (a) a convergence-rule change for provider
fits (K1's noise-aware verdict) and then a rerun of this exact model (no retraining); (b) a different declared bound
(for example 1e12, if its drift margin stays >= 10) with a fresh declaration; (c) mark C2UF-1 on the retrained emulator
as an escalation and keep the A1.21 skip.

## CRPROP-K3 — 2026-10-29 (environment E2)

Work package K3 of the cr-propagation follow-up wave 7 (decision B1.1, release 0.44.0): DRAGON2's known differences
in `adapter.json` (A1.11, A1.13), the escalation-12 translator gaps, the escalation-10 wording and enum note, and the
B3 erratum.

**Environment (r3 §0.3, base exception D10).** E2 host (macOS 27.2 arm64), Python 3.13.2 (miniconda; numpy and scipy
present). Checked before the first edit: `git rev-parse --show-toplevel` = `.claude/worktrees/crprop-k3`;
`git branch --show-current` = `worktree-crprop-k3`; `git status` clean; base = integration HEAD `f778b9d3` (not
`main`, decision D10). K3 has no dependencies (workflow.json `deps: []`); the follow-up card `94ba34d1` and the 0.43.0
merge `42f5bad1` are ancestors of HEAD. External codes: DRAGON2 cd588707 (`HEP_DRAGON2_BIN`, `HEP_DRAGON2_DATA`, the D1
build) for one live check; USINE V3.5 not run.

**Criteria (frozen entries K3-1 to K3-3 and ALL-*, acceptance.json).** K3-1 adapter.json records DRAGON2 as tested
with the A1.11 and A1.13 differences, their sizes and attributions; K3-2 escalation-12 gaps closed, each with a test,
committed runs keep their outputs or the change is recorded; K3-3 P1 wording corrected where the plugin states it, the
Ptuskin94/03 enum documented, the B3 sign corrected by an appended erratum.

| ID | Result | Evidence |
|---|---|---|
| K3-1 | **done**: the `cr-provider/1` declaration has no free field (`additionalProperties: false`, schema unchanged), so the `dragon2` provider entry's `description` holds them: tested in the declared environment (D1, D3) with D1-1a item effects (decay ¹⁰Be/⁹Be 13.3% closed form / 11.3% USINE, finite gas layer; reacceleration B/C 5.7%, ¹⁰Be/⁹Be 4.4%, first-order zone conversion with bound 0.517; losses B/C 6.1%, Coulomb on Galprop's HII vs ionization-only USINE, 3.0% with HII in USINE), D3-1 (38.2-40.8%, 77.0% for the losses pair; ladder gas column ×1.054-1.087, helium ×1.073-1.136, inelastic ×1.003-1.077, O/C ×1.104-1.110, injection ×1.000-1.031), D3-3 (0.59-0.67% passing; reacceleration 17.0%, losses pair 17.7% with the 0.811 geometry check within 1.9%/3.3%) and the escalation-11 caveats (second-order term not estimated, losses attribution not quantified, thick-gas agreement within ~1% only in bins 3-5 in D1). Numbers from VALIDATION CRPROP-D1, CRPROP-D3 and escalations.md item 11 | `adapters/cr-propagation/adapter.json`; `tests.adapters.test_adapter_declarations` OK |
| K3-2 abundances | **done**: USINE (ILLUSTRATIVE sets) translates `fixed by the parent list of theory:cr-secondary-ratio` (O/C 0.9) or none (recorded), and refuses any other text, which it used to record as "not parsed" (USINE's own files: `data-normalised ...` only, unchanged). DRAGON2 (`dragon2_translate.py`, new; the provider and the D3 study translate through it) translates `dragon2:BaseModel_DRAGONxsec.source.param` or none (recorded) and refuses the rest with the reason (source.param fixes source abundances; a propagated ratio is known only after a run; BaseModel O/C 1.19-1.21, ×1.10 on B/C) | `TranslatorSourceItems.test_usine_abundances_translated_or_refused`, `test_dragon2_refuses_what_its_source_cannot_express`, `test_dragon2_translates_its_own_sources_and_records_defaults` |
| K3-2 injection variable | **done**: `sources.injection[].spectrum_variable` (dQ/dX = q β^η R^-γ) is stated in every harmonized-v1 file as `kinetic_energy_per_nucleon` (B1's USINE runs; the harmonized-v1 description says so). USINE: `kinetic_energy_per_nucleon` and `total_energy` give η_s = η, `rigidity` η_s = η − 1 (dR/dE_k/n = (A/\|Z\|)/β, constants absorbed by the normalisation; exact); not given: E_k/n, recorded. DRAGON2: `rigidity` with η = 0 translated (R^-γ per unit momentum, D3's 1/β evidence); per-energy variables and η ≠ 0 refused (they need a β factor source.param cannot carry; up to 3% on B/C at 2-3 GV); not given: rigidity, recorded | `test_harmonized_v1_states_the_injection_variable`, `test_usine_injection_variable`, the two DRAGON2 tests |
| K3-2 gas term | **done**: a density term `n_<H\|HI\|HII\|H2> = <number>` without `cm^-3` (or with another unit) is refused, not read as 0; a term not written at all stays 0 with its note | `test_usine_gas_term_without_unit_is_refused` (D3's aborted string included) |
| K3-2 committed runs | **outputs unchanged**: every committed transport (46 blocks; the 36 the old translator accepted) translated before and after K3 by the USINE translator renders identical USINE input files, except the 8 DRAGON2 specs, which now state DRAGON2's abundances and are not USINE inputs; the D1 (6) and D3 (2) DRAGON2 specs were regenerated through `dragon2_translate` with DRAGON2's own sources stated: only `transport.sources` (spectrum_variable `rigidity`, abundances `dragon2:...`) and two substitutes notes changed; the rendered XML and the injection slope (source.param) are identical, so every record's input hashes still match | `$CRPROP_OUT/k3/regen/regen-record.json`, `usine-scan.json`; `D1Items.test_runs_are_recorded_and_translated_from_the_item_files`, `D3CrossCode.test_dragon2_runs_are_recorded_and_translated`, `UsineTranslator.test_specs_render_to_the_recorded_inputs` |
| K3-2 provider behaviour | the `dragon2` provider now refuses a harmonized-v1 transport (provider-error with the reason); its `DEFAULT_TRANSPORT` is harmonized-v1-isotopic with DRAGON2's sources stated (`with_dragon2_sources`, tested). Live: C1's conformance mixin passes on the new default (4 tests, 231 s; the kept run specs carry the two notes) | `$CRPROP_OUT/k3/acceptance/D1-PRV-1.unittest.log` |
| K3-3 P1 wording | **done**: `transport_conventions.py` (module docstring and the reacceleration `reason`) and `cosmic-ray-phenomenology.md` state V_A,disc = V_A,halo sqrt(L/(3h)) at first order with bound (1+λ)/5 and say that r3 P1's "about sqrt(L/h)" puts V_A off by sqrt(3); the page stays under 24576 B (24573 B), inventory regenerated; the r3 plan files are not edited | `tests.skills.hep_theory` OK, `reference_inventory.py --check` pass |
| K3-3 enum note | **done** in the `dragon2` description of `adapter.json`, with the file:line evidence of A1R (galaxy.cc:279-284, constants.h:146-149, input.h:156; Ptuskin94 has 3/4 of USINE's D_pp), the translator's handling (Ptuskin94 with constant 1) and that a fixing commit is a new test; nothing posted upstream | `adapter.json` |
| K3-3 B3 erratum | **done**, below | `$CRPROP_OUT/k3/b3-sign/b3-sign.json` |
| ALL-1 | environment field above | this section |

### Erratum to CRPROP-B3 (appended by K3; the B3 section is not edited)

The B3-1b attribution paragraph of CRPROP-B3 reads "USINE 2D / USINE 1D: B/C up to -2.4%, ¹⁰Be/⁹Be up to -1.3%".
The ¹⁰Be/⁹Be sign is wrong: USINE 2D / USINE 1D for ¹⁰Be/⁹Be (dec-2d over dec-1d, the 12 E_k/n bins 0.05-10 GeV/n)
is **+0.57% to +1.34%**, positive in every bin, largest at 2.7-4.1 GeV/n. Recomputed by K3 from the committed B3
output tables (`b3/outputs/dec-2d-nom`, `dec-1d-nom`, read with `usine_to_prediction` as the B3 test does; script and
result `$CRPROP_OUT/k3/b3-sign/`), equal to `b3-results.json` `b3_1b["dec-2d 10Be/9Be"].usine_2d_over_usine_1d`
(1.00565-1.01341), as the B3 verifier said. The B/C sign (-0.9% to -2.4%) is right. Radial escape lowers ¹⁰B and ¹¹B
relative to C but raises ¹⁰Be/⁹Be (plausibly because the decaying ¹⁰Be samples a smaller volume than ⁹Be and loses
less to the radial boundary; not checked further). The attribution (radial escape, B3-1b product within 1e-3 of 1) is unchanged.

**Runs (budget ≤ 40).** DRAGON2: the conformance mixin of D1-PRV-1, live once (the same mixin recorded 5 runs in D1;
two point directories kept under `$CRPROP_OUT/k3/live-dragon2/runs/`). USINE: none (every USINE input rendering is
unchanged; η_s = −1 was already run by D3).

**Not done in K3.** `dragon2_run.py` is not in K3's files (the card names a `dragon2_translate.py`, now added), so its
own `--from-transport` command line still calls the D1 translator without the source checks; the provider and the
D3 study go through `dragon2_translate.py`. A one-line delegation in `dragon2_run.py` would close it in a later
package. The USINE translator's `usine_provider.DEFAULT_TRANSPORT` and B1's `usine/specs/d1-*.json` do not state
`spectrum_variable` (the default, E_k/n, is recorded). They stay unchanged because the emulator fixtures hash that
transport (K4's files).

### CRPROP-K3 continuation (same dispatch, 2026-10-29; rebased onto integration 42f41893 with K2 and K4)

`adapters/cr-propagation/assets/dragon2_run.py` was added to K3's card (workflow.json on 42f41893). Its
`--from-transport` command line now translates through `dragon2_translate.spec_from_transport`, the same source checks
as the provider: a harmonized-v1 transport is refused (exit 2, status error, the reason; no spec written), and one
with DRAGON2's own sources is translated and its written spec carries the two source notes. The open item "not done"
above is closed. Test: `TranslatorSourceItems.test_dragon2_command_line_applies_the_same_source_checks` (no DRAGON2
run; the translated case stops at the missing data directory, exit 3). Rebase: CHANGELOG and VALIDATION keep the
integration blocks first and K3's after; `docs/reference-inventory.*` regenerated; the phenomenology page is 24573 B.
The adapter version is not bumped (the orchestrator sets versions at release); the CHANGELOG entry names the
behaviour change of the dragon2 provider.

## CRPROP-K1 — 2026-10-29 (environment E2)

Work package K1 of the follow-up wave 7 (decision B1.1, release 0.44.0): a noise-aware convergence rule for provider
fits in `propagation_fit.py` (K1-1), and F1's BIG, SLIM and QUAINT-Vc0 re-judged under it (K1-2).

**Environment field (r3 §0.3, base exception D10).** E2 (macOS arm64), Python 3.13.2 (miniconda; NumPy, SciPy), USINE
V3.5 (commit fb53006d) through HEP_USINE_BIN, HEP_USINE_DATA and USINE; runs under HEP_USINE_RUN_DIR =
`$CRPROP_OUT/k1/runs`, provider cache `$CRPROP_OUT/k1/repro/cache` (a copy of F1's `$CRPROP_OUT/f1/repro/cache`, F1's
folders left untouched). `git rev-parse --show-toplevel` = `.claude/worktrees/crprop-k1`; branch `worktree-crprop-k1`;
status clean at start; base 94ba34d1 = integration HEAD `worktree-crprop-k` (not `main`; decision D10); `main` 42f5bad1
(release 0.43.0) is an ancestor of HEAD; K1 has no prerequisite work package (workflow.json deps empty; requires
env-usine, present).

**Rule, fixed before any re-judging fit (R9; this paragraph is committed before the first K1 USINE run).** Opt-in:
a fit uses it only when its configuration declares `optimizer.noise`, either `{"mode": "measure", "max_evaluations": B}`
or `{"mode": "declared", "sigma_m2lnl": s}`. Without it nothing changes: closed-form and emulator fits give the 0.43.0
numbers and verdicts (checked on `examples/propagation-fit` and the hep_statistics tests).

1. Noise floor sigma_noise (standard deviation of one evaluation of -2 ln L, the fit's chi2 with priors, at the best
   point t_hat). Method: polynomial residuals over a small stencil. For each judged coordinate i (interior, not held as
   exactly flat, stencil inside the domain), -ln L is evaluated at t_hat + j s_i e_i, j = -2..2, with
   s_i = 0.02 / sqrt(F_ii) (F = J^T J of the least-squares Jacobian, priors included; 1/sqrt(F_ii) is the conditional
   sigma), and a quadratic in j is fitted by least squares. sigma_f^2 = sum_i RSS_i / (2 m) (2 residual degrees of
   freedom per coordinate, m coordinates), sigma_noise = 2 sigma_f. Budget: 4 new evaluations per coordinate,
   m = min(judged coordinates, floor(B / 4)); B = 40 per fit by default (F1: 32 for BIG, 28 for SLIM and QUAINT-Vc0).
   Justification: USINE is deterministic, so repeats measure nothing; over +-0.04 conditional sigma the smooth part of
   -ln L is a quadratic to within |f'''| (0.04 sigma)^3 / 6, about 1e-5 for |f'''| sigma^3 <= 1, far below the
   expected 2.5e-4 to 1.5e-3, so the quadratic absorbs value, slope and curvature and the residual scatter is the
   non-smooth part. A stencil step of 0.02 conditional sigma moves the predictions by about 1e-4 relative, about 100
   units of the 6th printed digit, so the rounding errors at neighbouring points are uncorrelated (F1 measured -2 ln L
   jumps of 5e-4 for a 5e-5 sigma change of delta). For uncorrelated noise E[RSS_i] = 2 sigma_f^2 exactly (linear
   model); a noise component smooth on the stencil scale is partly absorbed, so the estimate errs low, i.e. strict.
   With 14 to 16 degrees of freedom its relative standard error is about 19%.
2. Difference steps, the h ~ (sigma_noise / |f''|)^(1/2) form: h_i = a / sqrt(F_ii) (f''_i = F_ii) with one factor
   a = clip(2 sqrt(sigma_f V), 0.1, 1), V = sum_i F_ii (F^-1)_ii over the judged coordinates (sum of the variance
   inflation factors; a = 1 if that block of F is singular), rounded to 3 significant digits and at most half the
   distance to a domain bound. Derivation: the verdict's central-difference gradient has noise variance
   sigma_f^2 / (2 h_i^2) per coordinate, so the expected noise contribution to EDM = g^T H^-1 g / 2 is
   sigma_f^2 V / (4 a^2); the uncapped a makes it sigma_f / 16. The noise error falls as 1/a^2 while the truncation
   error of the differences grows as a^2; the cap a <= 1 (one conditional sigma, where -ln L rises by 0.5 along the
   coordinate) bounds the truncation: scaling F1's measured parabola residuals (+-0.11 over +-5.2 conditional sigma for
   SLIM's delta) as a^3 gives a gradient bias whose EDM contribution is about 1e-4 at a = 1, the same order as the
   noise term there (BIG: sigma_f^2 V / 4, about 2.5e-5). These steps are used for the verdict's gradient and Hessian,
   the Newton polish, the reported Fisher matrix and the least-squares Jacobian of any later restart attempt.
3. Acceptance: EDM <= max(1e-5, k sigma_noise) with **k = 0.5**, i.e. EDM <= max(1e-5, sigma_f): the EDM may not exceed
   the noise of one -ln L evaluation. The other conditions are unchanged (finite value, positive-definite Hessian,
   boundary_kkt at a bound). Justification: a minimum of a function with noise sigma_f cannot be located better than
   where -ln L differs by about sigma_f; at that threshold the accepted point lies within sqrt(2 sigma_f) marginal sigma
   of the minimum (0.055 sigma for the largest F1 floor, 0.003 in -2 ln L), small against the D9 one-sigma windows. At
   a true minimum the noise part of EDM has mean at most sigma_f / 16 by step 2, so a false failure needs a 16-fold
   fluctuation (P(chi2_1 > 16) = 6e-5 for one dominant direction; 0.2% if sigma_noise is estimated 2 standard errors
   low). The base 1e-5 is not loosened: it still applies whenever k sigma_noise is below it.
4. The result records `noise` (mode, sigma_m2lnl, method, stencil, coordinates, degrees of freedom, evaluations, budget,
   step factor a, V, steps) and the verdict's `edm_threshold`.

Also fixed (no criterion change): with polish, a polished point with a higher -ln L than t_hat is discarded and t_hat
is judged again, so the verdict always describes the returned point; an unconverged fit is reported with reason
`not-converged` (or `restart-cap` only when restarts were allowed and used up) and no statistical-result is written
for a run without a converged fit, instead of exiting with "artifact-invalid".

**Re-judging plan for F1 (declared before the refits).** Each family restarts from F1's reported fit with F1's own
configuration (start, stated steps, priors, `max_restarts` 0), so the least-squares path replays from the cached runs
(checked: 0 USINE runs for all three) and only the noise stencil and the verdict are new. Stage 1: `optimizer.noise`
`{"mode": "measure", "max_evaluations": 40}`, polish 0; expected about 4n + 2n^2 + 2n runs (BIG n = 8 judged
coordinates, V_A held: 176; SLIM and QUAINT-Vc0 n = 7: 140 each). Stage 2: a family whose stage-1 verdict fails only on
the EDM (reasons gradient_not_small, max_iterations) is refitted with `polish_steps` 1 (one damped Newton step with the
noise-sized steps, about 2n^2 + 2n + 12 new runs), in the order SLIM, QUAINT-Vc0, BIG while the remaining budget covers
it. K1 cap: 600 USINE runs (B1.1), at most 4 USINE processes at once. A family passes D9 when its verdict under this
rule is converged and delta and K10 lie in the CRPROP-F1 windows (unchanged); a family that still fails is attributed
with its numbers (EDM against the threshold, Hessian eigenvalues, noise). D9 and the 1e-5 base are not loosened.

**Results (record `tests/adapters/fixtures/cr_propagation/f1/f1-reproduction.json`, regenerated through
`examples/bc-usine-reproduction/run.py --rejudge-from`; outputs `$CRPROP_OUT/k1/repro/`, stage-1 copies in
`$CRPROP_OUT/k1/repro/stage1/`).** Stage 1 restarted each family from F1's reported fit with F1's own configuration
(least-squares path replayed from the cache) and the rule above; every verdict failed on the EDM alone (Hessian
positive definite, no bound), so stage 2 polished SLIM, then QUAINT-Vc0; BIG's polish (about 2n^2 + 2n + 12 = 156
runs) no longer fitted the remaining budget (52) and was not run.

| Fit | sigma_noise (-2 ln L), dof | step factor a, V | EDM (threshold max(1e-5, 0.5 sigma_noise)) | Verdict | delta (window) | K10 (window) | -2 ln L | D9 |
|---|---|---|---|---|---|---|---|---|
| BIG (stage 1) | 0.00345, 16 | 1 (capped), 1575 | 0.0103 (0.00172) | failed: gradient_not_small | 0.500 in | 0.286 in | 83.344 | missed (not converged) |
| SLIM (polish 1) | 0.00480, 14 | 1 (capped), 176 | 0.0147 (0.00240) | failed: gradient_not_small, line_search_stalled | 0.516 in | 0.289 in | 90.308 | missed (not converged) |
| QUAINT-Vc0 (polish 1) | 0.00684, 14 | 1 (capped), 333 | 0.0113 (0.00342) | failed: gradient_not_small | 0.459 in | 0.323 in | 84.015 | missed (not converged) |

K1-2: every fit is re-judged and recorded with its noise floor and EDM; best-fit delta and K10 stay inside the D9
windows for all three; none converges under the rule, so F1-1 stays NOT MET on convergence only (D9 and the 1e-5 base
not loosened).

Attribution (evidence in `$CRPROP_OUT/k1/repro/`). The measured floors (0.0034 to 0.0068 in -2 ln L) are 1.6 to 7 times
F1's three-point probes. The EDMs at steps of one conditional sigma are 4.3 to 6.1 times the threshold, but they do not
describe a reachable improvement: SLIM's polish (one damped Newton step from that gradient and Hessian) found no lower
-ln L in 12 trials; its full Newton step raised -2 ln L by +0.019 (90.3265 against 90.3078) where the EDM predicted a
fall of 0.029, about 4 sigma_noise the wrong way. QUAINT-Vc0's polish accepted only a step of about 1e-7 sigma
(-2 ln L lower by 8e-5, far inside the noise) and judged EDM 0.0113 there, unchanged. With the measured floors the
expected noise part of EDM at these steps is sigma_f^2 V / 4 = 1.1e-4 (BIG), 2.5e-4 (SLIM), 9.7e-4 (QUAINT-Vc0); the
observed EDMs are 10 to 90 times larger. So the verdict's central differences over one conditional sigma carry an
error well above the white-noise floor the stencil sees: a component of USINE's output error that is smooth over the
0.04-sigma stencil and absorbed by its quadratic (the case the rule noted as making the estimate err low), or
truncation of the differences in these strongly correlated fits (variance inflation 176 to 1575), or both; the K1
budget left no runs to separate them (for example a stencil over +-1 sigma). The points remain F1's best fits; the
rule's verdict, not the fit, is what cannot be reached at USINE's 6-digit output.

**USINE runs (K1 tally):** 548 of 600 (1 published-point evaluation of QUAINT-Vc0 by the start stage; stage 1 about
414 in all, of which a first batch whose runs were cached was interrupted before writing results and resumed from the
cache; SLIM polish 12; QUAINT-Vc0 polish 121 including an evaluation-budget stop at 110 resumed from the cache); at most
3 USINE processes at once.

## CRPROP-L1 — 2026-10-29 (environment E2)

Work package L1 of the follow-up wave 8 (decision B1.3, release 0.45.0): toy fits robust at the V_A = 0 boundary
(L1-1), and C2UF-1 re-run on the committed (A1.14) and the K4 well-conditioned emulator (L1-2). SYNTHETIC data only;
every input ILLUSTRATIVE.

**Environment field (r3 §0.3, base exception D10):** E2 (macOS arm64 workstation), Python 3.13.2 (miniconda), NumPy
2.4.4, SciPy 1.17.1; USINE V3.5 through HEP_USINE_BIN, HEP_USINE_DATA and USINE (validation only, cap 60 runs, B1.3).
`git rev-parse --show-toplevel` = `.claude/worktrees/crprop-l1`; branch `worktree-crprop-l1`; status clean at start;
base f0f424da = integration HEAD (`worktree-crprop-l`), not `main`; no prerequisite work package (deps []); the
0.44.0 release merge 31f39ee8 (K1-K4) is an ancestor of HEAD. Outputs under `$CRPROP_OUT/l1/`.

### Diagnosis of the K4 toy failures (L1-1; base code, before any method was chosen)

The K4 record (`$CRPROP_OUT/k4/k4-attempt/usine-emulator-family-study.json`) keeps only each failed toy's reason, so
its first 40 SLIM toys were replayed on the same model (`1.0.0+model.9b95e7465422`, emulator provider only, no USINE
run) with the base `propagation_fit.py` and every SurrogateFit attempt, verdict and provider refusal logged (scratch
script; the 2% stop disabled in that script only, so that every toy is seen; `$CRPROP_OUT/l1/diag-k4/diag-base.json`).
The same five toys fail, all in BIG's fit to a SLIM toy:

| Toy | Outcome | What the log shows |
|---|---|---|
| 3, 5, 31, 36 | restart-cap | all 6 attempts end with least_squares status 0 (max_nfev = 100 evaluations reached), so no verdict is ever reached; the attempts stop at V_A 0.43-4.0 km/s (toy 31 with V_c on its bound 0) with -ln L equal to 1e-3 between attempts: the optimizer creeps towards V_A = 0 |
| 10 | provider-out-of-domain | in the first attempt, one dogbox step goes from (V_A 8.34, V_c 1.24) to the box corner (V_A 104.96, V_c 9.5, the upper bound), which the DomainModel calls sparse; the refusal ends the toy |

Cause: B/C depends on V_A only through V_A^2, so near V_A = 0 the residuals are r(V_A) ~ r0 + J_w V_A^2 and their
Jacobian column 2 J_w V_A vanishes at the bound. Gauss-Newton steps then shrink V_A by about a factor two per step
when the minimum lies at or near V_A = 0 (linear convergence), which runs out of evaluations (toys 3, 5, 31, 36; 31
of all logged attempts ended at max_nfev), and `x_scale="jac"` turns the small column into a long step in V_A (toy 10).
The well-conditioned emulator is a smoother GP mean (nugget 7.4e-8 x signal), which changes where the slow path
crosses the evaluation cap, not the mechanism; the committed emulator's one restart-cap toy in C2UF is the same case.

### Method (L1-1; written and committed before any C2UF-1 rerun, R9)

Chosen: **fit coordinate w = p^2 for a parameter declared to enter only through its square, used for the retries of a
toy or family-calibration fit that fails in p.** Declaration: `parameters.<name>.enters_squared: true` (allowed only on
a linear axis whose provider domain starts at 0; refused otherwise). In `SurrogateFit` (toys and family calibration,
unconstrained fits only):
1. The first attempt is unchanged (coordinate p, same start, steps, optimizer and verdict).
2. If it does not converge, or the provider refuses one of its points as out of domain, the remaining attempts
   (`max_restarts`, unchanged) run in w = p^2 on [0, max^2]: the first from the failed attempt's point mapped to w
   (from the fit's start when the attempt was refused), the later ones perturbed as now. The difference step in w is
   h_w = h x max (the stated step h in p is a step of 2 (max/2) h in w at the middle of the range); no step stated:
   unchanged (scipy's own).
3. The verdict is the same fit_diagnostics verdict in the w coordinate: EDM <= 1e-5, positive-definite Hessian, a
   coordinate within one step of w = 0 set on it when -ln L does not rise by more than 1e-6, and boundary_kkt there.
   A refusal in a w attempt fails the toy (provider-out-of-domain) as before. The reported chi2 and point are in p.
4. Unchanged: the main fits (`fit_family`), profile intervals, the posterior, the constrained profile fits of the
   coverage toys, every fit with no declared parameter, the 2% toy-failure threshold, EDM 1e-5 and every tolerance.

Justification: in w the prediction is regular at the bound (Jacobian column J_w, not 0), the bound is a linear
constraint, Gauss-Newton converges there as on any interior coordinate, and the first derivative that boundary_kkt
tests carries the information. The alternatives were rejected: V_A = u^2 makes the dependence u^4, worse; a restart
seeded on the bound in p starts where the gradient in p is exactly 0, so the optimizer cannot leave it and a KKT check
at p = 0 passes even when the data prefer p > 0 (a saddle along p, a chi2 too high, a biased delta chi2); projecting
an out-of-domain step back into the domain mends toy 10 only and keeps the cause. Retrying in w (rather than fitting
every toy in w) keeps every fit that converges in p bit for bit, as L1-1 requires, and the minimum found is the same
function's minimum, so toy and observed delta chi2 stay comparable (the observed fits are `fit_family`'s, unchanged;
EDM is invariant to leading order under a smooth reparametrization at an interior minimum).

### C2UF-1 rerun plan (L1-2; pre-declared)

| Item | Setting |
|---|---|
| Configuration | `usine_emulator_family_study.py fit` as in C2UF/K4, with `V_A_kms` declared `enters_squared` (stated in the script; nothing else changed): emulator provider, holdout error component in both covariances, families BIG and SLIM, starts and steps, response_model kind "provider", 200 toys per family, seed 20261028, alpha 0.05, the 2% toy-failure limit |
| Emulator A (committed, A1.14) | the fixture model `1.0.0+model.0a8dc86fdf16` with C2UF's `validation.json` |
| Emulator B (K4) | retrained in L1 by `train --max-condition 1e10` from a copy of K4's cache (the same training document); it must be byte-identical to K4's model-0 (sha256 9b95e746...), else stop; `validate` and `confirm` from the cache must reproduce K4's numbers (0.0032 and 0.0226 sigma) |
| Pass (as C2UF) | BIG and SLIM converge with the provider; each family's calibration has at most 4 of 200 failed toys and lists its delta chi2 and toy p-value; BIG survives at alpha 0.05 |
| If B passes | B replaces the C2UF fixtures (model, ml-artifact, record); the A1.21 skips are removed; the drift simulation (`$CRPROP_OUT/k4/scripts/drift.py`, 2 seeds x 60 trials) must give margin >= 10 |
| If B fails | nothing is swapped; numbers and attribution recorded; PARTIAL. Nothing is tuned after a rerun |
| USINE | expected 0 runs (all points cached); cap 60 |

### Results (L1-1 checks and the C2UF-1 rerun, L1-2)

L1-1 checks (code at f453828b, method committed at 98cb29e6 before any rerun; SHAs after the rebase below): `examples/propagation-fit/run.py` on
the base f0f424da and on L1, both exit 0; of its 25 JSON outputs 22 are identical and 3 differ only in absolute plugin
paths, `report.md` identical (`$CRPROP_OUT/l1/examples/compare.txt`). hep_statistics tests: 354 run, OK (27 skipped,
live or optional). New `SquaredParameterRetry` tests on a SYNTHETIC stub (prediction linear in a, b and v^2, v nearly
degenerate with b): fits failing in v converge after the v^2 retries at the exact bounded minimum (lsq_linear,
chi2 within 1e-6 relative), fits converging in v are bit-identical with and without the declaration, a first attempt
refused out of domain is retried, and the declaration is refused off a linear axis from 0.

C2UF-1 rerun (the pre-declared plan above; records `$CRPROP_OUT/l1/emu-a114/record/` and `$CRPROP_OUT/l1/emu-k4/record/`;
emulator B retrained in L1 byte-identical to K4's model-0, sha256 9b95e746..., holdout 0.0032 and confirmation 0.0226
sigma reproduced from the cache, 0 USINE runs):

| Item | A old (C2UF, committed) | A new (L1) | B old (K4 attempt) | B new (L1) |
|---|---|---|---|---|
| Model | `+model.0a8dc86fdf16` | same | `+model.9b95e7465422` | same |
| BIG fit | converged, chi2 1.3e-8 | identical (fit_family unchanged) | converged, chi2 1.1e-8 | identical |
| SLIM fit | converged, chi2 23.9272 | identical | converged, chi2 23.9274 | identical |
| BIG's toys | 200, 0 failed, p 1.0 (200/200), survives | 200, 0 failed, p 1.0 (200/200), survives; 3 toys used the V_A^2 retries | 200, 0 failed, p 1.0, survives | 200, 0 failed, p 1.0 (200/200), survives; 1 retried |
| SLIM's toys | 200, 3 failed (2 out of domain, 1 restart cap), p < 0.0151 (0/197), excluded | 200, **0 failed**, p < 0.0149 (0/200, 95% upper bound), excluded; 11 retried | **stopped at the 2% limit after 37** (5 failed: 4 restart cap, 1 out of domain) | 200, **0 failed**, p < 0.0149 (0/200), excluded; 20 retried |
| Largest toy delta chi2 under SLIM | 14.68 | 14.68 | - | 14.68 |
| C2UF-1 | MET | MET | NOT MET | **MET** |

Toy fits that converged in V_A are bit-identical to the old records (A: 197 of BIG's and 189 of SLIM's toy rows;
B: 199 and all 31 comparable rows). Toys that converged before only after a random restart in V_A and now went through
the V_A^2 retries changed chi2 by at most 6e-6 relative (A) and 2e-11 (B). Every previously failed toy now converges:
A's toys 10, 95, 111 and B's toys 3, 5, 10, 31, 36 (BIG's fits; toy delta chi2 0.003 to 2.26, far below SLIM's 23.93).

Swap (allowed by B1.3 since C2UF-1 passes on B): the C2UF fixtures `usine-emulator-family-study.json`,
`emulator-model.json` and `emulator.ml-artifact.json` are B's (the study's `train` step now defaults to
`--max-condition 1e10` and reproduces the committed model byte for byte from the cache: `$CRPROP_OUT/l1/emu-repro/`).
The A1.21 skips in `EmulatorPerModelDeclaration.setUpClass` and `test_live_emulator_matches_fresh_usine_runs` are
removed, so a self-check refusal fails again. Drift simulation (`$CRPROP_OUT/k4/scripts/drift.py`, 2 seeds x 60
trials, on the committed artifact): accepted in 120 of 120, max ln-mean deviation 3.1e-8 x sigma, margin 3217 (seed 1)
and 3831 (seed 2) against 1e-4 x sigma, so >= 10 holds (`$CRPROP_OUT/l1/drift/`). Live check (HEP_USINE_LIVE_TEST=1):
two fresh USINE runs, the committed emulator within 0.05 sigma in every bin.

Study driver: the emulator steps now send the transport recorded in the two-dataset study (the emulator's training
transport) instead of rebuilding it from `usine_provider.DEFAULT_TRANSPORT`, and ask for the registered USINE version,
so they keep working when L2 makes the default transport explicit and bumps the provider version (the transport is
identical today; checked). USINE runs (B1.3 cap 60): 2 (the live check); every other point was cached.

Rebase: before the report the branch was rebased onto the integration HEAD eeb62a4e (status.json and workflow.json
only, orchestrator files); f0f424da stays the base of the comparisons above.

## CRPROP-L2 — 2026-10-29 (environment E2)

Work package L2 of follow-up wave 8 (decision B1.3, follow-ups 2-6 of the 0.44.0 release): the modulation conformance
result tied to the provider version (L2-1), adapter and provider versions with a cache-key migration (L2-2), the USINE
injection variable stated explicitly and the K3/K1 doc slips (L2-3). Contracts 3.16.0 (one minor, gating constant
`validate.CONFORMANCE_VERSION_FROM`), `CORE_VERSION` 1.4.0 (core/provider refuses more declarations), adapter
`cr-propagation` 0.3.0.

**Environment field (r3 §0.3, base exception D10).** E2 (macOS arm64), Python 3.13.2; fixtures, theory-profile
artifacts and examples regenerated with the E2 venv (`~/.venvs/hep-research-e2`); USINE V3.5 (commit fb53006d) through
HEP_USINE_BIN, HEP_USINE_DATA and USINE, with the host ROOT_INCLUDE_PATH. `git rev-parse --show-toplevel` =
`.claude/worktrees/crprop-l2`; branch `worktree-crprop-l2`; status clean at start; base f0f424da = integration HEAD
`worktree-crprop-l` (not `main`; decision D10), which contains the 0.44.0 release merge 31f39ee8; L2 has no
prerequisite work package (workflow.json deps empty; requires env-usine, present). DRAGON2 not run. Rework round 1
(verifier): the emulator's normalised transport comparison (below). Rebased onto integration 009f8752 (L1 merged; card
widened in eeb62a4e) with `git rebase`, so the new base is 009f8752; conflicts only in CHANGELOG and VALIDATION (L1's
entries kept first). After the rebase the new tests run on L1's swapped C2UF fixture (the K4 model), and L1's tests
pass under the usine 0.3.0 registry: L1's driver reads the registered version, its records keep 0.2.0, and no test
replays an L1 cache expecting hits.

What changed:
- `contracts/schemas/cr_provider.json`: `modulation.conformance.result` requires `provider_version` (the provider
  version the result was obtained at). The field is required, not optional, so the change is a minor bump (3.16.0)
  with `validate.CONFORMANCE_VERSION_FROM`; declarations carry no contract_version, so the constant gates no artifact
  rule. A 3.15 declaration with a modulation block is refused by core 1.4.0 until the gate is rerun.
- `core/provider/protocol.py`: `check_declaration(declaration, version=None)` requires the field and refuses a result
  whose `provider_version` differs from `version` (the caller's resolved provider version), else from the declaration's
  own `version`; the message says to rerun `tools/provider_registry.py --conformance`. `registry.parse_registry` passes
  each entry's version and `conformance.run_conformance` passes the entry's version. `CORE_VERSION` 1.4.0.
- `tools/provider_registry.py`: `--conformance` writes `result.provider_version` (the version the gate ran at);
  `collect` checks each declaration against its effective version (the declaration's, else the adapter's or profile's).
- `adapters/cr-propagation/adapter.json`: version 0.3.0; `usine` and `dragon2` declare their own `version` 0.3.0 (they
  inherited the adapter's 0.2.0); `emulator` stays 1.0.0; the USINE result records `provider_version` 0.3.0.
- `usine_provider.DEFAULT_TRANSPORT` and `tests/adapters/fixtures/cr_propagation/usine/specs/d1-*.json` state
  `sources.injection[].spectrum_variable` = `kinetic_energy_per_nucleon`.
- Contracts bump as in K2: CONTRACTS_VERSION and comment, `vocab/core.json`, the two pinned tests, `make_fixtures.py`
  and `design_fixtures.py` rerun, three skill templates, six theory-profile scripts rerun, 14 examples rerun; only
  version strings and the hashes that cover them changed (diff checked line by line after masking 64-hex hashes). No
  contract fixture was added, so `gate_verdicts.json` is unchanged.

Conformance gate (L2-1; `$CRPROP_OUT/l2/conformance/usine-0.3.0.json`, 2 USINE runs of the 10 allowed):
`tools/provider_registry.py --conformance usine` at provider version 0.3.0 with K2's reference point, observables and
tolerance 1e-3: passed, largest relative deviation 4.27721405739101e-05 over 390 nodes of 10B, 10Be, 11B, 12C, 9Be,
equal to the digit to K2's result at 0.2.0. Recorded in `adapter.json` with `provider_version` 0.3.0.

Versions (L2-2). The point hash (`core/provider/hashing.point_hash`) and so the runner's cache key contain
`provider_version`; usine and dragon2 inherited the adapter's 0.2.0, set at B1 (77d661c3). Since then usine gained the
F1 point parameters (low break, phi, production channels) and the K2 modulation block and hook, and the K3 translator
source checks; dragon2 refuses harmonized-v1 transports whose sources it cannot express (K3). Both go to 0.3.0, set
explicitly so a later adapter bump does not move them. The emulator stays 1.0.0: its answers for the committed E2 model
are pinned unchanged (`EmulatorPinnedResponses`), a per-model declaration already carries `+model.<sha12>` in its
version, and its later changes only add refusals (a non-reproducing self-check), which produce no value to cache;
bumping it would also rewrite `c2uf/e2-pinned-responses.json`, which L1 may be replacing.

**Migration decision: keep, not re-key.** The committed records stay as records of what produced them, with usine 0.2.0
(C2U `c2u/usine-family-study.json`, C2UF `c2uf/usine-two-dataset-family-study.json`, `c2uf/` and `e2/` emulator model
contexts, E1/E2 summaries, F1 `f1-reproduction.json`). Re-keying would claim that 0.3.0 produced values it did not, and
the emulator model files are hashed by their ml-artifacts and versions. No test replays them through the runner
expecting a cache hit: the offline tests read their numbers; `ProviderVersionMigration.test_recorded_input_hashes_are_history`
recomputes all 565 C2U and 367 C2UF input hashes from the recorded point, transport and usine 0.2.0 (all equal) and
finds none of them among the hashes of the same points under 0.3.0, so a cache filled at 0.2.0 can never answer a
0.3.0 request (no stale hit; a miss is a fresh run). Live callers now ask the registered version: the F1 example
`examples/bc-usine-reproduction/run.py` and the C2U study driver read it from `adapter.json`, and the `UsineProvider`
tests of `test_propagation_fit.py` send the registry's version instead of the record's (the record still asserts
0.2.0). F1's record tests pass unchanged; no file under `c2uf/` or `e2/` was edited. The C2UF offline tests passed in
the first round too, but they never send the study's transport: `usine_emulator_family_study.emulator_values` sends
`st.transport()`, built from DEFAULT_TRANSPORT, and the C2UF emulator refused it after L2-3 (training transport sha256
25ea7f409b88..., study transport 4754ca1f5064...), so every rerun of the C2UF emulator study, and the live test
`test_live_emulator_matches_fresh_usine_runs`, would have failed (verifier, rework round 1). Fixed by the emulator's
transport normalisation below; `EmulatorPerModelDeclaration.test_study_transport_is_accepted` now covers it offline.

USINE inputs (L2-3; `$CRPROP_OUT/l2/render/before.json`, `after.json`): each of the five d1 specs and DEFAULT_TRANSPORT
translated with the old (implicit) and new (explicit) injection by the translator (unchanged by L2, so old and new
translator agree): all four rendered files identical, sha256 by sha256. The translation record changes (the default
note for spectrum_variable disappears; the echoed transport has the field) and so does the canonical hash of
DEFAULT_TRANSPORT (a4a7ec283011... implicit, d25f968e865d... explicit). Committed hashes over the transport object are
kept unchanged: the E2 and C2UF emulator models record the implicit block as their training transport (hashed into
their ml-artifacts), and the C2U/C2UF input hashes are history (above). Effect on the emulator, final state (rework
round 1): `emulator_provider.request_problem` compares canonical_sha256(normalise_transport(request transport)) with
canonical_sha256(normalise_transport(training transport)); `normalise_transport` drops an injection item's
spectrum_variable equal to DEFAULT_SPECTRUM_VARIABLE (`kinetic_energy_per_nucleon`, inlined; a test pins it equal to
`usine_translate.DEFAULT_SPECTRUM_VARIABLE`). So the emulator accepts null, its training transport and USINE's
DEFAULT_TRANSPORT (and the C2UF study's transport built from it), and still refuses another spectrum_variable or any
other block (`EmulatorProviderRefusals.test_transport_and_bins`, `test_normalised_transport`). The model files, the
ml-artifacts and model_sha256 are byte-identical; the runner's point hash still covers the block as sent, so the two
forms keep distinct cache keys that map to identical values (`test_study_transport_is_accepted` checks equal results
and different input hashes). No previously answered request changes its answer, so the emulator stays 1.0.0.
`EmulatorArtifact` checks that the training transport is DEFAULT_TRANSPORT minus the explicit default and renders the
same USINE inputs.

**Erratum (appended; the sections themselves are not edited).** CRPROP-K3, row K3-2: "46 blocks; the 36 the old
translator accepted" should read 37 accepted blocks (the verifier's scan). CRPROP-K1, environment field: base
94ba34d1 was the dispatch base; K1 was rebased onto 21ec114d before its merge. Also fixed: the docstring of
`tests/adapters/fixtures/cr_propagation/d3/d3_study.py` named `dragon2_run.spec_from_transport` for D3_harmonized_v1;
it is `dragon2_translate.spec_from_transport`.

| ID | Result | Evidence |
|---|---|---|
| L2-1 | pass | schema requires `result.provider_version`; core and schema agree (`tests.core.test_provider.DeclaredModulation`: the missing and the empty field refused by both, a result of another version core-only, `test_conformance_holds_only_at_the_version_it_was_obtained_at` for the registry); `tests.tools.test_provider_registry` (the gate writes the version, `collect` refuses a bumped version with or without an explicit declaration version); USINE gate rerun at 0.3.0 (above) |
| L2-2 | pass | adapter 0.3.0, usine and dragon2 0.3.0, emulator 1.0.0 (`ProviderVersionMigration.test_versions`); migration kept, not re-keyed, and checked (`test_recorded_input_hashes_are_history`); F1 record, C2U and E2 pinned tests pass unchanged; the C2UF study transport is accepted again (rework round 1) |
| L2-3 | pass | spectrum_variable stated (`UsineProviderOffline.test_injection_spectrum_variable_is_stated`); rendered USINE inputs identical; effect on hashes recorded above; the emulator accepts both forms by normalised comparison, refuses other variables (rework round 1); erratum and docstring fix |
| ALL-1 | pass | this section |
| ALL-2 | pass | `workflow_check.py acceptance` exit 0 |
| ALL-3 | deferred to the wave run (A1.5) | |
| ALL-4 | pass | `check_naming.py`, `workflow_check.py gaps --base 009f8752` |
| ALL-5 | pass | `check_layering.py`; `workflow_check.py diff --work-package L2 --base 009f8752` ok (after the rebase) against the card widened on integration (eeb62a4e: the contracts-bump set, `core/__init__.py`, `tests/skills/hep_statistics/**`); round 0 had listed those 353 paths as outside the card |
| ALL-6 | pass | `check_packaging.py` |
| ALL-7 | pass | worker report |

| Check | Result |
|---|---|
| Impacted tests (`rule_registry.py impact`: 35 modules, plus `test_provider`, `test_adapter_declarations`, `test_gate_verdict_snapshot`, `test_provider_conformance_mixin`) | after the rebase onto 009f8752: 719 tests OK (17 skipped) in the E2 venv and in `~/.venvs/hep-research-ci` alike (impact set for the new base plus test_cr_propagation, test_propagation_fit with SquaredParameterRetry and UsineEmulatorFamilies, test_provider_registry, test_provider, test_gate_verdict_snapshot, test_adapter_declarations, test_provider_conformance_mixin); live `test_live_emulator_matches_fresh_usine_runs` (HEP_USINE_LIVE_TEST=1, 2 fresh USINE runs against the C2UF emulator through the 0.3.0 registry): OK |
| `tests/examples` | 176 tests OK (22 skipped) |
| theory-profile tests (9 profiles) | all pass |
| `run_all_checks.py --part static --jobs 4` | exit 0 |
| `check_naming.py`, `check_wiring.py --since f0f424da`, `check_layering.py`, `check_packaging.py`, `workflow_check.py gaps/acceptance` | pass / ok |
| ruff 0.16.10 and mypy 2.4.0 on `core/` and `contracts/` | clean |

USINE runs: 4 of 10 (the gate, 2; the live C2UF emulator test after the rebase, 2). DRAGON2 runs: 0. Not run: ALL-3 (deferred to the wave run, A1.5), a live routing run.

## AUTHORING-IMPROVE — 2026-10-29 (macOS, Claude Code 2.1.312, claude-sonnet-5-5; branch `hep-authoring-improve-20261029` from `3a63e986`)

hep-authoring improvement task (runbook v10). Fast lane: the abstract row of `paper-structure.md` points to the venue
guide for venue limits (G2); a hep-review handoff row in SKILL.md, scope sentences in `independent-review.md` and
`reviewer-style-assessment.md`, and a hep-review row in the routing-contract ownership table (G10); the revision Done
when covers the compact change ledger, and a recorded hep-review review of a changed result is carried over by
hep-review (G5, fast-lane part); a Resources row routes translating or condensing a paper to the existing bilingual
rules (G9, fast-lane part). One verification-lane target (G5-V: reply wording for pending work) was frozen, run and
withdrawn: no difference. SKILL.md 9171 -> 9606 B (quick load 22888 of 25600). Spend: USD 14.79 (routing 5.81 over
86 case runs; exploration and handoff 1.84 over 28 runs; gold writer 0.61; pilot 2.81 over 30 runs; grading 3.72
over 10 sessions).

| Item | Evidence | Result |
|---|---|---|
| G2 venue limits in the venue guide only | engineering (`test_paper_blueprints.py`, L2) | pass |
| G10 review handoff and ownership row | engineering (`check_ownership.py` 23 topics, no problems; `check_routing_static.py` ok); live routing of the 50 hep-authoring/hep-review cases on `f90882b8`: 45/50 strict, the 5 new AR boundary cases pass | pass; the 5 failures predate the change (rerun on both sides, descriptions identical): `ir-direct-1` wrong skill 7/7, `lit-bound-referee-1` no skill 6/7, `d-cc-spectrum-1` base 2/6 vs 0/7, `lit-bound-related-1` 3/6 vs 4/7, `lit-turns-1` turn 2 flaky on both sides |
| G11 short writing requests | live routing: `aw-short-1`, `aw-short-2` pass; exploration 0/11 runs with no skill loaded | gap not kept; description unchanged |
| G5-F compact-ledger Done when | engineering (`test_revision_impact.py`, `test_reference_links.py`) | pass |
| G9-F bilingual routing row | engineering (L2) | pass |
| G1 hedging Done when (sci-fix, S3) | ledger HEDGE-DONE-WHEN: Hyland 1995 (Hong Kong Papers in Linguistics and Language Teaching 18:33-42, pp. 34-35) and Bongelli et al. 2019 (PLoS ONE 14 e0221933, Conclusion and Discussion), both read in full; `test_handoff_text.py::HedgingDoneWhen` fails on the parent | pass |
| G5-V reply wording for pending work | authoring-pilot (two calibrated fresh-context claude-opus-5-5 graders; 3 failure cases, 2 correct controls, 12 gold items each, 3 runs per version) | no difference: failure-case items 106/108 baseline vs 105/108 candidate, p(candidate better) = 1.0, leave-one-out remaining T = -1; controls 72/72 both; no critical or control regression; withdrawn (revert `039781da`) |
| G3, G4, G6 (verification lane) | spike: 4 baseline runs each of the drafting, method, discussion and talk cases | not reproduced (0/4 each); not selected |
| Adaptation path (G7) | engineering: golden record, talk outline and manifest through `check_adaptation.py` | single-study talk (golden record): exit 0 after a recorded semantic review; multi-study review talk: exit 0 with one record holding a claim per study (each from its literature source) and a synthesis claim as the central claim, the record valid (`validate.py` exit 0, assessments unresolved); slide numbers and the slot length are reported as unmapped numbers (warnings); contract unchanged |

Observation (not a claim): in the exploration and the pilot, reply drafts for pending work are often written as
completed-voice templates with placeholders ("We have repeated ... [X]"), although the model says the work is not done;
confirmed critical failures in 2/3 and 3/3 baseline runs of two pilot cases. The rule exists in
`submission-and-peer-review.md`; no exploration run read a reference file. Surfacing it in SKILL.md did not change this.
The replay scorer's completion pattern misses this wording and matched a negated "已完成" once (scorer artefacts).

External material (spike, one run each, no claim): an AMS Collaboration proceedings, PoS(ICRC2025)104 (CC BY-NC-ND
4.0, used verbatim for evaluation only and kept out of the repository). A 12-minute talk outline kept the
"preliminary" label on every flux slide and traced every number; a hypothetical, labelled result update (two changed
values) was carried to all six affected places (slide bodies, a caption, the summary, a backup table) without touching
the unchanged joint-fit value; a consistency review found four of five known source defects (a missing "million", a
missing decimal point, a ratio named inversely to its equation, a missing unit; missed a "position"/"positron" typo)
plus one more (a subscript typo). Three earlier runs that loaded no plugin were discarded.

L3: `tools/run_all_checks.py` passes (after regenerating the reference inventory). `tools/check_relocation.py` fails in
two Geant4 adapter tests (`test_geant4.py` partition runs) because a worker command is split at a space in the relocated
path; the same two tests fail identically on the unmodified base 3a63e986 copied to a path with a space (pre-existing,
not touched here).

Not verified here: P4 talk revisions at authoring-pilot level; P5 teaching examples (skipped, no delivered verification
item). Limitations: developer-authored brief; same-host gold (advisory); same model family for graders and gold writer;
gold items hit a ceiling (both versions 11-12 of 12), so the pilot had little power for this target. Records:
`evals/research_communication/authoring-items/` (exploration, pilot protocol, commitments, revealed gold, result) and
`evals/routing/results/ar-*.json` in the repository's top-level `evals/`.

## AUTHORING-FOLLOWUPS — 2026-10-29 (macOS, Claude Code 2.1.312, claude-sonnet-5-5; branch `hep-authoring-followups-20261029` from `5e2a75a2`)

Three follow-ups of AUTHORING-IMPROVE, requested by the maintainer after 0.47.0. Spend: USD 0.80 (12 runs).

| Item | Evidence | Result |
|---|---|---|
| G4 document part: drafting order is the measurement-paper default; other types start from their backbone (quick load 22888 -> 23012 B) | engineering (L2) | pass; behaviour not measured (the G4 defect did not reproduce at baseline, 0/4) |
| G7: review-talk outline in `audience-adaptation-templates.md`, which template applies, layout numbers as `context` statements | engineering: `test_adaptation.py::test_review_talk_with_a_synthesis_claim_and_layout_numbers` (a synthesis central claim passes; the slot length warns until its line is a context statement) | pass |
| G8/P5: three Contrast-format prose examples in `skills/hep-authoring/examples/prose/` (SKILL.md 9606 -> 9739 B, quick load 23145 of 25600) | engineering: `validate_skill_example.py` on each, `test_diagrams.py::test_prose_examples_follow_the_contrast_format`; example 03 quotes real `check_adaptation.py` reports (good manifest exit 0, weak manifest exit 1: status dropped, invented average, condition dropped) | pass |
| P5 transfer (spike, no claim): three new synthetic cases (a 2.6 sigma local excess, a review of three determinations, a review talk), 0.47.0 vs this branch, 2 runs each | live runs | no observable difference: both versions declined a consensus value and kept the preliminary label and the global significance; the examples were opened in 0 of 6 runs with them available. Kept as documentation by maintainer decision (2026-10-29); no model benefit is claimed |

## AUTHORING-FOLLOWUPS-2 — 2026-10-29 (macOS, Claude Code 2.1.312, claude-sonnet-5-5; branch `authoring-followups-2-20261029` from `6a7e5f8b`)

Four items requested by the maintainer after 0.48.0: the reply-template defect (G5-V2), P4b talk revisions at
authoring-pilot level, the replay scorer fix and the Geant4 tests on paths with spaces. SKILL.md 9739 -> 10113 B
(quick load 23519 of 25600). Spend: USD 14.34 (G5-V2: runs 2.54 over 30 runs, grading 3.74 over 10 sessions, gold
writer 0.71; P4b: runs 2.52 over 30 runs, grading 3.93 over 10 sessions, gold writer 0.90).

| Item | Evidence | Result |
|---|---|---|
| G5-V2 reply wording for pending work: SKILL.md Workflow step 7 (a reply, response letter or summary of changes states what is true when written; one version, no completed-voice template to fill in later; offer the final wording once the result exists) and the same sentence in `submission-and-peer-review.md` | authoring-pilot (`authoring-items/pilot/g5v2/`; frozen in `bb44fca0` before the change `5b94e1bf`; 3 failure cases, 2 correct controls, one F item per pending request, 3 runs per version; two calibrated fresh-context claude-opus-5-5 graders) | target improved: failure-case items held 77/108 baseline vs 108/108 candidate; p(candidate better) = 0.0005 for both graders (T = 31 and 30), leave-one-out remaining T = 13; confirmed critical failures 8/9 baseline runs vs 0/9 candidate; controls 70/72 vs 71/72; gold verified 15/15; delivered (claim: local improvement on the listed material and conditions) |
| P4b talk revisions (result update and condensation reach every affected slide, caption and backup) | authoring-pilot (`authoring-items/pilot/p4b/`; frozen in `47eb0cfa` before any run; 3 failure cases, 2 correct controls, 3 runs per version); recorded deviation: baseline 0.46.0 `3a63e986`, candidate `6a7e5f8b` (the whole hep-authoring task), so the result concerns the task, not one change | no difference: items held 106/108 vs 105/108 (grader 1); p(candidate better) = 1.0 (T = -1) and 0.8 (T = 0); no confirmed critical failure on either side; no control regression; gold verified 15/15. One confirmed major failure in one candidate run of `upd-det-timing-en` (an uncertainty called statistical only without a source), recorded and not adjudicated; both versions already near the ceiling on this material |
| Replay scorer 1.2.0 (`evals/research_communication/score_replay.py`) | engineering: `test_score_replay.py::test_completion_wording_seen_in_live_runs`; re-scoring the earlier runs | completion wording seen in live runs is caught ("We have repeated ...", "has been rerun", ...), and a CJK completion word negated earlier in the same clause ("不建議…暗示已完成") no longer counts; the ax-04 artefact is gone. Correction: the ax-11 reply template appears in 4 of 4 baseline runs (the G5-V protocol, frozen, says 3 of 4) |
| Geant4 partition tests on a path with spaces (`0aebec94`) | `tests/adapters/test_geant4.py` quotes the fixed paths of its `local_partition.py` command templates (`shlex.quote`; the template is split before placeholders are filled); the `batch-scheduling.md` example quotes its paths the same way | the two tests that failed `check_relocation.py` since 0.45.0 pass from a copy under a path with a space, and in the full `check_relocation.py` run (6126 tests; the only 3 failures came from the stale reference inventory below, none in `test_geant4`) |

The P5 transfer spike (AUTHORING-FOLLOWUPS) and this P4b pilot give no evidence that the prose examples or talk
guidance change model output; the G5-V2 change is the only behaviour change of the task measured as an improvement.
Limitations: developer-authored briefs; same-host gold (advisory); same model family for graders and gold writer;
no held-out evaluation. Records: `evals/research_communication/authoring-items/pilot/{g5v2,p4b}/` (protocol,
commitments, revealed gold, `result.json`) and the run outputs `evals/research_communication/{outputs,results}/g5v2-*`,
`p4b-*` in the repository's top-level `evals/`.

L3 (E2): `tools/run_all_checks.py --no-cli --jobs 4`: 29 pass, 2 fail, 2 skipped; 6126 tests, 3 failures, all from a
stale reference inventory (SKILL.md and `batch-scheduling.md` changed; `test_reference_inventory`,
`test_reference_soft_budget` and `test_run_all_checks` timeout test, which runs the inventory test). After
`tools/reference_inventory.py` the three modules pass (22 tests). `tools/check_relocation.py`, run on the same stale
inventory: the same 3 failures and nothing else.

## RETIRE-CROSS-ARTIFACT-CHECK — 2026-10-29 (environment E2)

Retirement of the cross-artifact analysis check (task file "retire the cross-artifact check" v1; decision option A,
`docs/dev/cross-artifact-check/decision-retire.md`, maintainer choice 2026-10-29). Contracts 3.17.0 (one minor:
sidecar formats removed); `CORE_VERSION` and the adapters are unchanged. Run record:
`docs/dev/cross-artifact-check/retire-STATE.md` (state, test classification, report).

**Environment.** E2 (macOS arm64), Python 3.13.2 in the E2 venv (`~/.venvs/hep-research-e2`); ruff 0.16.10 and mypy
2.4.0 from the CI venv. Branch `retire-cross-artifact-check` from `3a63e986` (0.46.0), merged with `main` `a2852507`
(PR #314). Fixtures, theory-profile artifacts and examples regenerated with the E2 venv.

What changed:
- Removed: the checker (`contracts/analysis_checks/` except `source_digest.py`), `contracts/migrate.py`, the 14 rule
  suites, `contracts/rules/refusal_matrix.json`, the operator coverage contract, the schemas of analysis bundle 2.0.0,
  check context, check report, semantic lock and operator coverage, `tools/rename_analysis_check_ids.py`, the two
  checker test helpers and 12 checker-only test modules.
- Kept under descriptive names: `contracts/source_digest.py` and ten test modules (five renamed unchanged, five split).
  Which tests went was decided by a function-level trace of the 301 tests in the 22 checker-named modules and six
  dependent modules on the unmodified tree; the 18 tests where the trace and the plan disagreed were settled from
  their source (CLI through a subprocess, imports inside the test, setUpClass, checker-only helpers, skipped
  placeholders, or rewritten in a kept module).
- The checker's 12 rules are review questions: 9 in hep-measurement (`review-and-artifacts.md`, "Spec against
  implementation"), 3 in hep-statistics (`combinations.md`, "Ratios of two results").
  `tests/skills/test_review_question_tables.py` builds an obligation from each row and validates it against hep-review's
  obligation definition and method cards (read only).
- `contracts/analysis_check.py`, `permit.py check-report` and `review_measurement_spec.py --check-bundle/--check-root`
  refuse with the reason (exit 2). The rule registry retires all 12 new or changed rules; 69 V-case parts became
  not-run with the reason in `host` (4 remain passing).
- `tools/naming_known_gaps.json` only shrinks (1,032 to 983 entries, none added): `tools/check_naming.py` compares the
  file with `origin/main` and counts a key that moves with a renamed file as growth, so the five identifiers flagged in
  the moved files were renamed instead (`obj` to `target` in `contracts/source_digest.py`, `tmp` to `workdir` in
  `test_contract_baseline_gaps.py`, `ec` to `catalog_module` in `test_effect_catalog.py`); no behaviour changes.
- Contracts bump as in CRPROP-L2: CONTRACTS_VERSION and comment, `vocab/core.json`, the two pinned tests,
  `design_fixtures.py` rerun (`make_fixtures.py` reproduces the edited fixtures), three skill templates, six
  theory-profile scripts (`--check` passes), 14 examples rerun; only version strings and the hashes that cover them
  changed (diff checked after masking 64-hex hashes). The two examples that dropped their advisory fields
  (`bc-fragmentation`, `pbar-p-curvature-offset`) differ from their previous output only by those fields.

Assertions changed (none loosened):
- `test_rule_registry`: the new-rule test now expects `registry.rule_not_implemented` for a live new rule and accepts
  a retired one; two module names updated; the suite test removed (no suites remain).
- `test_cutoff_transmission_m1`, `test_survival_fragmentation_d4`: the coverage-contract tests and assertions removed.
- `test_preservation_checklist_c3`: the retired items removed; it asserts the checklist no longer teaches the check.
- `test_pbar_p_curvature_offset`: the assertion on the removed `advisory_ratio_subset_v1` field removed.
- `test_ci_plan`: example paths moved to `contracts/permit.py`, `test_registry_keys_and_semver.py` and
  `design_fixtures.py` (a replacement that selects more than one module, so the tamper test still bites).
- The split modules keep their shared tests; the rewritten ones (`test_source_digest`,
  `test_catalog_version_and_retired_rules`) test the same shared code without the checker.

Results: `tools/run_all_checks.py --part all --no-cli` on the unmodified base: 31 pass, 2 skip (host CLI), 6,298 unit
tests, 0 failed (494 modules); after the change and the merge with `main`: 31 pass, 2 skip, 6,123 tests, 0 failed (483
modules); no failure on one side only (the -176 tests of the retirement; PR #314 added one). Static checks, ruff on
`core` and `contracts` and mypy pass; ruff on the changed files reports only the two pre-existing B904 in the example
`run.py` files. hep-review: 374 files hash-identical, claims registry check `[]`; `core/protected`, `core/partition`,
`release-manifests`, the pinned vocabularies, semantics tables and recipes, and the permit and attestation schemas are
unchanged. GitHub CI on PR #315 passed.

Cleanups: the `$comment` fields that still described the check as live (`contracts/vocab/effects.json`,
`contracts/schemas/rule_registry.json`, `contracts/schemas/effect_catalog.json`, `contracts/naming/rules.json`) now
say it was retired and name `contracts/source_digest.py`; no digest pins these files (checked against every stored
raw and canonical digest outside the release manifests), and the registry, naming and catalog checks pass. Two
timing keys of modules removed in 0.28.0 were dropped from `tools/module_timings.json`.

Not verified here: no live routing run.

## DETECTOR-RECONSTRUCTION-METHODS — 2026-10-30 (Linux, AlmaLinux 9 kernel 5.14; Python 3.13.2 from a conda environment; not installed there: iminuit, pyhf, arviz, emcee, h5py, xgboost, jsonschema, PyROOT; host CLI checks skipped with `--no-cli`; version 0.49.1 + unreleased)

Scope: hep-detector reconstruction methods by detector family (documentation and four routing cases only), from
branch `task/hep-detector-reco-methods` at base `313637c1`; every number below was measured in this run.

| Item | Evidence | Result |
|---|---|---|
| Scope from coverage | `docs/dev/hep-detector-reco/coverage-audit.md`: 19 families x 7 tasks audited at the base, counts recomputed by its script | 133 cells: 118 applicable (C 60, P 39, M 19), 15 not applicable; all 58 non-covered cells written: 46 in the first pass (groups A 19, B 7, C 6, D 14) and the 12 first deferred (radio, emulsion and fibre linking, cryogenic pileup and position) in a follow-up the user requested; audited matrix equal to the expected one |
| Citations | Crossref records of the 13 DOIs fetched in this run and compared with the bibliography (authors, title, venue, volume, pages, year) | 22 verified (13 in the first pass; 9 for the follow-up, found by Crossref search), 0 corrected, 0 not re-verifiable; one abstract read on INSPIRE-HEP to settle a review finding |
| Independent review | one fresh-context reviewer at `2d8e931c`, one re-reviewer of the fix diff `2d8e931c..9ff83cdf` (`docs/dev/hep-detector-reco/review-dispositions.md`) | 0 critical, 2 major, 9 minor, 1 optional; both major and 7 minor fixed, 2 minor not fixed by repository convention (routing budget; applicability already stated), optional left for a follow-up; re-review: all resolved or justifiably deferred, 3 new minor wording points open. Follow-up review at `6bfc7873`: 0 critical, 3 major, 12 minor, all fixed; re-review: all resolved, 4 minor and 1 optional point raised. On the user's request every open point (3 + 1 optional from the first pass, 4 + 1 optional from the follow-up) was then fixed; a last re-review found them resolved and 2 minor and 2 cosmetic points, also fixed; nothing open |
| Wiring and layering | `tools/check_wiring.py --since 313637c1`, `check_layering.py`, `check_instruction_text.py`, `check_ownership.py`, `check_naming.py` (the last four inside `run_all_checks.py --part static`) | wiring exit 0, no new gap; the other four pass |
| Reference budget and overlap | `tools/reference_inventory.py --check`; touched-reference sizes; routing part of `detector-principles-summary.md` | pass, 247 references, the same 6 size warnings as the base (none in a touched file), 0 overlap pairs; touched references at most 23594 B (limit 24576 B); routing part 4081 B before and after, also after the follow-up |
| Routing | `tools/check_routing_static.py`; `tests/routing/cases.json` regenerated by `make_cases.py` | pass; four new cases (`dr-reco-1`, `dr-reco-2`, `dr-reco-3` to hep-detector, `dr-reco-neg` to hep-ml) |
| Tests | `run_all_checks.py --part static --no-cli` and `pytest tests/skills tests/routing tests/tools/test_check_wiring.py` at the base, after the content, and after the review fixes | static: 29 pass, 0 fail, 2 skip (host CLI) at all three; pytest base 2885 passed, 28 failed, 1 error, 83 skipped; after the review fixes 2888 passed, 25 failed, 0 errors, 83 skipped; every failure is a base failure (29 base ids: hep-ml script and torch-asset tests, the Python and PyROOT floor tests, synthetic NanoAOD, the diagram renderer, the CLI contract, no-bytecode), 0 one-sided failures; 4 base failures passed in the later runs (environment timing). Follow-up: static 29/0/2; pytest after the follow-up fixes 2887 passed, 26 failed, 1 error, 83 skipped, 0 one-sided failures; in the run before those fixes one PyROOT-floor test failed outside the base list, from temporary-folder cleanup on the network file system (it fails at random when its file is repeated alone and reads no reference), and passed in the final run. After the open-item fixes (final text): static 29/0/2; pytest 2886 passed, 27 failed, 1 error, 83 skipped, 0 one-sided failures |

Passing checks show contract and documentation consistency, not physical validity of the methods described.

## RELEASE-FOLLOWUPS-0.50.0 — 2026-10-30 (Linux, EL9 x86_64; Python 3.13.2 with the CI lock; version 0.50.0 + unreleased)

Two follow-ups from the 0.50.0 release: a portable realization-profile entry in `check_geant4_study.py` study records,
and the release regeneration procedure in `docs/maintenance.md`.

| Item | Evidence | Result |
|---|---|---|
| Realization entry | `RealizationEntryTests` in `tests/skills/hep_detector/test_check_geant4_study.py` (recorded path present; path from another machine resolved to a matching copy; a copy with another or no recorded hash refused; nothing taken from outside the study root) | 28 tests in the module pass |
| Replay away from E2 | `examples/design-minimal-spectrometer/run.py --out <tmp>` on Linux, with no file at the recorded `~/Workspace/...` path | the input manifest of all 11 study records equals the committed (E2) one; before the change each lacked the realization-profile entry |
| Committed outputs | `geant4-thin-silicon`, `design-minimal-spectrometer`, `design-search-j16` regenerated on E2 (the checker's code-identity hash is in their study records) | `e28ff1b9` (E2): 21 files (`geant4-thin-silicon` 7, `design-minimal-spectrometer` 14, `design-search-j16` none), every changed line a hash (the checker's code identity and the sha256 values covering it), no PNG; afterwards `tests.examples.test_geant4_thin_silicon`, `test_design_minimal_spectrometer`, `test_design_search_j16` and `test_check_geant4_study` pass on Linux with the CI lock |

Passing checks show software consistency, not physical validity.

## RECON-V12-PR-A-ROUTING — 2026-10-30 (Linux, EL9 x86_64; Claude Code 2.1.314, claude-sonnet-5-5; branch `recon-v12/pr-a-runner-checks` rebased on 0.50.0, `3fd5b425`)

Live routing rerun required by `docs/maintenance.md` before merging a change to what hep-detector and hep-computing
read (their Owns lines and two routing-contract rows; descriptions unchanged).

| Item | Evidence | Result |
|---|---|---|
| Live routing, the cases involving hep-detector or hep-computing | `evals/routing/results/pr-a-0.50-routing.json` (137 cases, 139 prompt turns, $11.92) | 126/137 strict; hep-detector 61/67, hep-computing 43/48; 0 loading violations, no contamination |
| Misses against earlier runs | the same case ids in `evals/routing/results/` | 5 never passed before (0/7 each), 3 varied before, 3 passed every earlier run |
| Repeats of those 3, branch vs main 0.50.0 | `repeat-0.50-pra-1..3`, `repeat-0.50-main-1..3` ($1.09) | `d-cc-preserve-2` 3/3 vs 3/3, `d-cc-columnar-2` 2/3 vs 3/3, `th14-reco-1` 1/3 vs 2/3; descriptions identical, differences within run-to-run variation: no regression shown |

Single runs per case except the repeats; the result supports "no routing regression shown", not a routing guarantee.

## GEANT4-REGISTER — 2026-10-30 (environment E5: RHEL 9 x86_64, GCC 11.5.0, CMake 3.26.5, Python 3.13 CI lock; branch `geant4/register-existing-install` from `313637c1`)

Adapter 0.6.0: `geant4_build.py register` and the downstream changes, run end to end against an existing installation:
Geant4 11.4.3 from conda-forge in a conda environment (`geant4 11.4.3 qt` build: C++17, MT, external CLHEP 2.4.7.2,
GDML, Qt; twelve datasets, nine in folders without the `G4` prefix, e.g. `EMLOW8.8`, while `geant4-config
--datasets` names `G4EMLOW8.8`). Nothing was installed into the environment. The official example sources and
reference outputs came from a `git clone --depth 1 --branch v11.4.3` of github.com/Geant4/geant4 into the local work
folder (HEAD 2ee379e6843e55b9c6bbb835d2a2b03cc998fef0, the commit E2 built). Work folders on local disk, removed
afterwards. Recorded: `tests/adapters/fixtures/geant4/records/geant4-registered-e5.computational-run.json` (paths as
`~`) and `examples-compare-e5-s1.json` (the work folder written as `<work>`).

| Step | Result |
|---|---|
| `register --prefix` without activating the environment | refused (exit 1, no record): nine datasets found nowhere, each naming the folder without the `G4` prefix next to it |
| `register --prefix` in the activated environment (`--dataset-source auto`) | ok in 27 s: twelve datasets resolved from the environment variables (nine `without-G4-prefix`, three `exact`), content-hashed (G4NDL 16092 files ... G4ENSDFSTATE 3); artifact `geant4-registered-11.4.3-bc4790a9`, origin `registered`, tag and commit null |
| Content of the eleven datasets E2 also installed | identical content hashes to E2's MD5-checked cern.ch downloads (the MD5 of the conda packages' sources is not checked here) |
| CMake probe (`find_package(Geant4)`) | fails: `Could NOT find EXPAT (... Required is at least version "2.8.5")`; by hand, with expat and zlib pointed at the libraries, the next stop is freetype (the system 2.10.4 is older than the 2.14.3 required; the environment has no freetype CMake or header files): the environment ships the libraries but not the development files of Geant4's dependencies |
| `check` (environment deactivated) | ok, no difference (version, prefix, configuration hashes, twelve dataset hashes) |
| `build-sim` layered_sim with CMake | failed at configure (as the probe said), with the hint to use `--configure-with geant4-config` |
| `build-sim --configure-with geant4-config` layered_sim, element_sim (+ simroot), simreco | ok (GCC 11.5.0; run path to the environment's `lib`, no `LD_LIBRARY_PATH`; `ldd` finds every library, the environment's newer `libstdc++` included); only `-Wshadow` warnings from Geant4's flags (`s`, `m`, `g` against the unit symbols) |
| layered_sim TestEm5 run 0 mirror, 2000 events (a trial) | run ok; `geant4_verify.py mirror` failed `leak_secondaries_MeV` at z = -3.26 (z_crit 2.64); reported, not repaired |
| layered_sim TestEm5 run 0 mirror, 1e5 events (the declared mirror size) | 6/6 pass (largest abs(z) 1.29, z_crit 2.64) |
| layered_sim checks: overlaps, datapaths, balance (200 events, killed e+), budget (geantino, TestEm3 geometry) | pass (overlaps 0 reports in 10000 test points; balance residual RMS 1.5e-6 MeV); `--inject omit-positron-mass` caught in 200/200 events |
| element_sim J15 run (200 events) | ok; datapaths pass; balance reported without a verdict (proton primary); `overlaps` failed because the run did not request `/geometry/test/run` (the live test below runs it) |
| Official examples with CMake | failed at configure (same missing development files) |
| Official examples with `--configure-with geant4-config`, `--source` the v11.4.3 clone | B1, B4a, TestEm3, TestEm5 built; without `--source` the build is refused (exit 2) |
| `compare` B1 (runs 0-1), TestEm3 run 0 (10000 events), TestEm5 runs 0-4, seeds 20261030 1 | 48 quantities, Bonferroni z_crit 3.28: all pass, largest abs(z) 2.33 (TestEm5 run 0 steps_neutral) |
| B4a smoke | pass (three runs, material table, FTFP_BERT) |
| Live tests on the registration (`HEP_GEANT4_LIVE_TEST=1`) | `test_geant4.Live` 6/6 and `test_geant4_element.Live` 8/8 pass (element_sim test-hooks build made by hand with the same CMake helper) |
| J14 live (`examples/geant4-thin-silicon/run.py --live` into the work folder; committed `recorded/` untouched) | 27/27 criteria pass in 768 s; both studies re-issued `validated-in-scope` for their benchmarked scopes; the study records list the nine (MPV) and five (stopping power) run records on the registered installation with the provenance note |
| `HEP_GEANT4_REGISTER_TEST=<conda geant4-config>` (`RealInstallation`) | pass in the activated environment; fails, with the refusals, without the activation |

Software checks on a clean clone of the branch at `1e19ad29` on local disk (CI-lock Python 3.13, no dataset variable
set): `run_all_checks.py --part static` 31/31 pass (the naming gate first found five new names, renamed in `1e19ad29`);
the Geant4 adapter modules (`test_geant4`, `test_geant4_element`, `test_geant4_register`, `test_g4sim`, `test_simreco`,
`test_adapter_declarations`) 134 run, 0 failures, 15 skipped (the live and real-installation tests: unverified there,
run above); `tests/skills/hep_detector` 587, 0 failures, 4 skipped; `test_cli_robustness` and `test_cli_contract` 9;
`tests/tools` 371; `tests/contracts` 1160, 1 skipped; `tests/routing` 21; the J14, J15 and J16 example tests 16, 1
skipped; no failures anywhere.

Every record stays `unvalidated` except the two J14 study records `label --upgrade` re-issued; a completed run or an
agreement with an official example is verification, not validation. The adapter status stays
`demonstrated-on-synthetic-data`. Not done: the CVMFS LCG views (slow to list), the Apptainer definition, macOS rerun
of the changed CMake files (the `find_package` path is unchanged apart from `CMAKE_PREFIX_PATH`).

## GEANT4-REGISTER-REVIEW — 2026-10-30 (environment E5: RHEL 9 x86_64, GCC 11.5.0, CMake 3.26.5, CI-lock Python 3.13; branch `geant4/register-existing-install` at `50a8569c`)

Fixes for the PR #328 review of adapter 0.6.0. Each finding got a regression test that failed on `ac0b4140` before the
fix (`tests/adapters/test_geant4_register.py`, class `ReviewFixes`; the fake installation is now accepted by
`find_package(Geant4 11.4)` and answers `--cflags`/`--libs`, so the two build tests configure with the real CMake and
compiler and skip without them). Live checks against the conda-forge Geant4 11.4.3 installation of GEANT4-REGISTER
compare the code at `ac0b4140` (before) with the fixed code (after); work folders on local disk, removed afterwards.

| Finding | Regression test (before the fix) | Live, before | Live, after |
|---|---|---|---|
| `check` read `geant4-config` with stderr and ignored its exit | `test_check_reads_geant4_config_as_register_does`: exit 1, version `11.4.3\nbash: warning: ...` | `LC_ALL=xx_XX.UTF-8` (`/bin/sh: warning: setlocale`): `check` failed with a version and a prefix difference | ok, no difference |
| `Geant4Config.cmake` without readable dataset descriptions skipped every cross-check | `test_geant4config_cmake_without_dataset_descriptions_is_refused`: exit 0, record written | not reproduced live (the conda file declares them) | refused, no record (fake) |
| `register --prefix` on a view whose `bin/geant4-config` is a symbolic link | `test_a_view_whose_geant4_config_is_a_symbolic_link_is_registered`: refused | view of symbolic links to the conda `bin/geant4-config` and `lib/cmake/Geant4`: refused (`geant4-config --prefix is ~/.../envs/geant4`) | ok, the conda prefix recorded with `prefix_given` the view and a warning; `check` ok. Cause: Geant4's `geant4-config` follows its own links and canonicalises its prefix (`pwd -P`), so not resolving the path before querying would not have helped |
| `build-sim` kept a cached `G4SIM_GEANT4_CONFIG` | `test_build_sim_cmake_after_geant4_config_does_not_keep_the_helper`: the cmake-mode log says `Geant4 11.4.3 from .../geant4-config` | `--configure-with geant4-config`, then the default in the same `--work`: both ok, the second reported `configure_with: cmake` although `find_package(Geant4)` cannot work for this installation | geant4-config ok; cmake fails at configure (`Could NOT find EXPAT`, the probe's finding) with the hint; geant4-config again ok, `ldd` finds every library |
| examples: one build folder configured from two sources | `test_examples_switch_configure_with_in_one_work_folder` (B1 stand-in, geant4-config, cmake, geant4-config): the cmake step fails with `does not match the source ... used to generate cache` | not run (building the official examples from the v11.4.3 clone was not permitted in this session) | not run; the regression test passes |

Live end-to-end after the fixes: `register --prefix` (activated environment) ok in 31 s, twelve datasets, CMake probe
fails as recorded in GEANT4-REGISTER; `check` ok with the environment activated and deactivated; layered_sim (built
with `--configure-with geant4-config` after the mode switch) 200 events of `balance_killed_tracks` (SYNTHETIC) ok, run
record `unvalidated`, origin `registered`, every dataset path and content match.

Software checks on a clean clone at `50a8569c` on local disk (no dataset variable set): `run_all_checks.py --part
static` 31/31 pass; `tests/adapters` 505, 0 failures, 88 skipped (live and real-installation tests);
`tests/skills/hep_detector` 591, 4 skipped; `test_cli_robustness` and `test_cli_contract` 9; `tests/tools` 371;
`tests/contracts` 1160, 1 skipped; `tests/routing` 21; repo path guard ok. The adapter status stays
`demonstrated-on-synthetic-data`.

## 0.51.0 release check (2026-10-31, E2 and the CI lock)

Release branch `release/0.51.0`, based on main `ed4d07ff` (PR #328, #329, #330 merged). Minor release: it ships the
Geant4 adapter 0.6.0 (registration of an existing installation), reconstruction v12 part one (method contract and
research workflow control, workflow-runner fixes, check definitions, receipts and executor capabilities) and part two
(the control-layer helper, C1 and C2, whose rules did not pass S0: eight rounds, three known open defects). Contracts
3.17.0, `CORE_VERSION` 1.4.0 and every skill `description` are unchanged.

What changed on the release branch:
- version 0.51.0 in both manifests, `pyproject.toml`, the README, two assets, the six theory-profile scripts,
  `usine_translate.py` and `examples/bc-usine-reproduction/run.py`; a CHANGELOG `0.51.0` section;
- regenerated on Linux (EL9 x86_64, Python 3.13.2, CI lock) in `e41da037`: 21 files, 13 theory-profile files and the
  `detector-resolution`, `eic-profile-routing` and `recasting` JSON outputs;
- regenerated on E2 (`~/.venvs/hep-research-e2`, macOS arm64, Python 3.13.2, NumPy 2.5.3) in `320c31b9`: the six
  theory-profile scripts and the examples, `qed-prediction` before `published-comparison` and `theory-comparison`
  last; 166 files. 160 change only in version strings and the hashes that cover them (removed and added lines equal
  after masking both). Five theory-profile predictions (`cr-secondary-antiprotons`, `cr-secondary-ratio`,
  `dis-parton-model`, both `tmd-gaussian-lo`) return to their 0.50.0 E2 values: `e41da037` had accepted Linux values
  that differ in the last digits, because its mask treated a run of 16 or more decimal digits as a hash. The
  `detector-resolution` PNG returns to the E2 image shipped from 0.5.0 to 0.49.1 (sha256 `9b3c5d1e`); 0.50.0 had
  shipped a Linux rendering (`22e2512e`). `bc-propagation-fit` and `unfolding-coverage` carry no plugin version and
  drift at rounding level from their 0.42.0 outputs on E2; they were left as committed.

| Check | Result |
|---|---|
| `run_all_checks.py --part static`, CI lock on Linux (Python 3.13.2) | 31 pass, 0 fail |
| `run_all_checks.py --part static`, E2 at `320c31b9` | 31 pass, 0 fail |
| `tests/examples` (unittest), E2 at `320c31b9` | 176 tests, 0 failures, 17 skipped |
| `check_relocation.py`, E2 at `320c31b9`, `TMPDIR` on local disk, `SDKROOT` set to the Xcode SDK | 30 pass, 2 fail, 1 skipped; 6277 tests, 2 failures, 188 skipped, 1 module timed out (below) |

The relocation failures on E2 are host limits, not release changes:
- `test_executor_b2` (`test_admission`, `test_g1_g2_g5_pass_and_the_rest_are_unsupported`; the same two in the
  `ams_optional` check): G2 qualification fails because the runner finds processes that left the step's group only
  through `/proc`, which macOS lacks (documented in `run_workflow.py`). The tests assume Linux; `qualify_g2` could
  report `unsupported` there instead of `fail`. Follow-up.
- `tests.skills.hep_statistics.test_cli_input_fuzz` timed out at 600 s under load (15-minute load average about 70);
  alone it passes in 62 s.
- Without `SDKROOT`, every C++ build fails on this host (Xcode clang 21 cannot read the Command Line Tools'
  MacOSX 27.2 SDK), giving 13 failures and 3 errors; with `SDKROOT` set they pass.
- `test_geant4_register` `test_the_helpers_read_a_registered_record` fails on macOS when `TMPDIR` is under
  `/var/folders` (it compares an unresolved `G4LEDATA` path with a resolved one); it passes with a resolved `TMPDIR`.
  Follow-up.

## CROSS-PLATFORM-FOLLOWUPS — 2026-11-01 (macOS arm64, Apple clang 21.0.0, Python 3.13.7 with the CI lock; branch `xplat/pr-4-followups`)

Follow-ups to the cross-platform task (PRs #333-#336). MINIJSON-UNICODE-ESCAPES (sci-fix S2,
`docs/evidence/sci-fixes.json`): `adapters/geant4/assets/g4sim/MiniJson.hh` decodes `\u` escapes to UTF-8.

| Evidence test | Parent `54b2d011` (harness only) | Fix `7eb98412` |
|---|---|---|
| `test_g4sim.G4simSelfTest.test_strings_decode_like_python_json` | fail (assertion: exit -6, "non-ASCII \u escapes are not supported", ensure_ascii on) | pass |
| `test_g4sim.G4simSelfTest.test_malformed_unicode_escapes_are_refused` | fail (assertion: `\u12` and `\u12g4` decoded, exit 0) | pass |

The parent is the commit that adds only the self-test driver's `utf8_hex` request; MiniJson is unchanged there. The
oracle is Python's json decoder and `str.encode("utf-8")` (an independent implementation): 313 strings, 300 of them
random over every UTF-8 length, with `ensure_ascii` on and off. The negative control refuses 8 malformed escapes (lone
high or low surrogate, reversed pair, a high surrogate followed by a non-surrogate, fewer than four or non-hex digits).
`selftest.cc` compiles with `-Wall -Wextra -Wconversion -Werror` without a new diagnostic in MiniJson. Under a
`TMPDIR` named with a space and Chinese characters, `tests.adapters.test_simreco` and `tests.adapters.test_geant4`
pass (70 tests, 6 skipped; 11 simreco failures before).

## 0.52.0 release check (2026-11-01, E2 and CI)

Release branch `release/0.52.0`, based on main `bf5e453a` (the cross-platform stack #333-#337 and #338 merged).
Minor release: cross-platform support. Contracts 3.17.0 and every skill `description` are unchanged; `CORE_VERSION`
1.5.0 (`core/interpreter_guard.py`, `core/hostcaps.py`). The code-release digest changes (the guard block in 198
skill scripts): deployments re-pin and requalify.

What changed on the release branch:
- version 0.52.0 in both manifests, `pyproject.toml`, the README, two assets, the six theory-profile scripts,
  `usine_translate.py` and `examples/bc-usine-reproduction/run.py`; the CHANGELOG `0.52.0` section; the ledger entry
  MINIJSON-UNICODE-ESCAPES names release 0.52.0;
- regenerated on E2 (`~/.venvs/hep-research-e2`, macOS arm64, Python 3.13.2, NumPy 2.5.3) in `b61c791b`: the six
  theory-profile scripts (13 files, the plugin version only) and the examples in the order of `docs/maintenance.md`;
  167 files. Every changed line is a version string, a hash or hash prefix covering one, or one of 24 provenance
  `code_paths` lines naming `core/hostcaps.py` and `core/interpreter_guard.py` (skill scripts load them since the
  guard; maintainer option 1 of 2026-10-31); the `check_geant4_study.py` and `geant4_benchmarks.py` hashes in the
  `design-minimal-spectrometer` and `design-search-j16` study records follow the guard block. No number and no PNG
  changed. `bc-propagation-fit` and `unfolding-coverage` carry no plugin version and were left as committed;
  `bc-usine-reproduction` and `propagation-fit` have no committed output.

| Check | Result |
|---|---|
| CI `tests.yml` on `b61c791b` (run 41245961042) | success: `checks-complete`, units 1/3-3/3, static, AMS optional, lint, `old-python`, four `hostile-paths` legs |
| CI `platforms.yml` on `b61c791b` (run 41247746941) | macOS units part under `ulimit -n 256`: success; Windows (guard sweep, line endings, `tests/contracts`): success |
| `run_all_checks.py` (all parts, host CLIs), E2 at `b61c791b`, `--jobs 4` | 32 pass, 1 fail; units 6290 tests, 0 failures, 0 errors, 170 skipped, 3 modules timed out (below) |

The three modules that passed the 600 s module limit at `--jobs 4` pass alone on E2: `test_cli_input_fuzz` (4 tests,
277 s), `test_bc_propagation_fit` (14 tests, 241 s) and `test_diagrams` (31 tests, 176 s). `claude plugin validate
--strict` and `codex plugin load` pass. Host: Homebrew ROOT 6.40.04 (upgraded 2026-11-01); its include folder for vdt
is not in `root-config --cflags` (`check_root_cpp_env.sh` names it), and `test_root_cpp_assets` passes with it.

## EVENT-DISPLAY-TEMPLATES — 2026-11-01 (macOS 27.2 arm64, Python 3.13.2 venvs with the CI lock, E-full adding uproot 5.7.7, awkward 2.14.0, Playwright 1.63.0; version 0.52.0 + unreleased)

The event-display guide, facts file, checklist, templates (`skills/hep-computing/assets/event-display/`) and test
module added to hep-computing on branch `feat/event-display-templates` from main `cf622dab`, checked by the focused
test module, the end-to-end demo and the repository's static, unit and relocation runs.

| Item | Evidence | Result |
|---|---|---|
| `tests.skills.hep_computing.test_event_display_templates`, E-ci | `python -m unittest ... -v` | OK: 3 skipped (uproot/awkward not installed; full demo not requested) |
| Same module, E-full | `python -m unittest ... -v` | OK: 2 passed, 1 skipped (full demo not requested) |
| End-to-end demo (`run_demo.sh` on a copy of the templates outside the repository) | Node 26.10.0, npm 11.19.1, Vite 7.3.7, Phoenix 4.2.3, Playwright 1.63.0, Chromium headless shell 153.0.8010.12 | exit 0; steps 1, 2, 3 and 5 report `"status": "ok"`; Vite `✓ built`; `check_bundle.py` `sources_checked: true`, no unchecked sources (5 events, 3 panels, 20 objects); `test_page.py` `"status": "ok"`, 9 of 9 checks `ok` |
| Same module with `HEP_EVENT_DISPLAY_FULL=1`, E-full | `python -m unittest ...` | OK: 3 passed |
| Static part, `run_all_checks.py --part static --no-cli` | baseline at `cf622dab` and after the change | 29 pass, 0 fail, 2 skip (host CLIs) in both |
| Unit part, `run_all_checks.py --part units --no-cli`, E-ci | 6342 tests in 496 modules | 6046 passed, 295 skipped, 1 failed: `test_control_layer_model` scenario `t28_scale_linear`, a wall-clock ratio scenario (`control_oracle.py` `TIMING_SCENARIOS`) run while the demo and the relocation check loaded the host; the module passes 3 of 3 times alone on the branch and at `cf622dab`, and no changed file is on its path |
| `check_relocation.py --no-cli`, E-ci | relocated copy, path with spaces, outside the repository | pass (exit 0); 2 host-CLI skips |
| Wiring, skill scripts, naming | `check_wiring.py --since cf622dab`, `skill_scripts.py --check`, `insert_interpreter_guard.py --check`, `check_naming.py` | pass, ok, ok, pass; the template folder is excluded from the skill-script list, no template carries the guard block |
| Forced failure | `columns` renamed to `data` in `export_events.py`, then `check_naming.py` | exit 1 with `naming.common.forbidden` at `export_events.py:123`; file restored, diff empty |

Passing checks show software consistency, not physical validity.

## EVENT-DISPLAY-ROUTING — 2026-11-01 (macOS 27.2 arm64, Python 3.13.2 venv with the CI lock, Claude Code 2.1.316; version 0.52.0 + unreleased)

The `hep-computing` description names event displays (Phoenix) and sends paper figures to hep-authoring in its
`Not for` part, with six EVD routing cases, checked statically and by a live routing run of every case that involves
hep-computing.

| Item | Evidence | Result |
|---|---|---|
| Description length | `skills/hep-computing/SKILL.md` | 1,015 characters (limit 1,024; 1,022 before) |
| `tools/check_routing_static.py` | 481 cases, 6 in set EVD | exit 0; `failed`, `coverage_errors`, `topic_errors`, `scope_errors` empty; `event displays (phoenix)` no longer unpinned |
| Forced failure | the `paper figures: hep-authoring` clause removed | exit 1 on `evd-negative-2` only ("does not route this to hep-authoring in its 'Not for' part"); restored |
| `tools/check_ownership.py` | | exit 0 |
| Routing tests, `tests/skills` top-level modules | `unittest discover -s tests/routing`; `tests/skills/test_*.py` | OK: 21 tests; OK: 46 tests |
| Static part, `run_all_checks.py --part static --no-cli` | before and after | 29 pass, 0 fail, 2 skip (host CLIs) in both |
| Live routing run `evd-routing-20261101` | claude-sonnet-5-5, Claude Code 2.1.316, 68 cases, 4 jobs; smoke case first | 64/68 strict, USD 5.29 (smoke USD 0.08); EVD 6/6; `compare` with `claude-2.1.293-claude-sonnet-5-5`: 27 shared cases, 0 regressions |
| Misses | `d-cc-pairs-1`, `d-cc-pairs-2`, `d-cc-preserve-1`, `c-ml-roothist-2` | the first three missed before this change (2026-10-31 control on the unchanged base); `c-ml-roothist-2` 1/3 on the branch and 1/3 on main `cf622dab` (USD 0.39), varying in earlier runs: no regression shown |

Passing checks show software consistency, not physical validity.

## 0.53.0 release check (2026-11-01, E2 and CI)

Release branch `release/0.53.0`, based on main `395806ce` (PRs #340 and #341 merged). Minor release: event displays.
Contracts 3.17.0 and `CORE_VERSION` 1.5.0 are unchanged; the `hep-computing` description changes (VALIDATION
EVENT-DISPLAY-ROUTING), every other skill `description` is unchanged.

What changed on the release branch:
- version 0.53.0 in both manifests, `pyproject.toml`, the README, two assets, the six theory-profile scripts,
  `usine_translate.py` and `examples/bc-usine-reproduction/run.py`; the CHANGELOG `0.53.0` section;
- regenerated on E2 (`~/.venvs/hep-research-e2`, macOS arm64, Python 3.13.2, NumPy 2.5.3) in `bc06db3f`: the six
  theory-profile scripts and the examples in the order of `docs/maintenance.md`; every changed line is a version
  string or a hash covering one (checked hunk by hunk), no PNG changed. `bc-propagation-fit` and
  `unfolding-coverage` carry no plugin version and drift at rounding level: left as committed.

| Check | Result |
|---|---|
| CI `tests.yml` on `bc06db3f` (run 41264271915) | success: `checks-complete`, units 1/3-3/3, static, AMS optional, lint, `old-python`, four `hostile-paths` legs, the six optional extras |
| `run_all_checks.py` (all parts, host CLIs), E2 at `bc06db3f`, `--jobs 4` | 32 pass, 1 fail; units 6342 tests, 6168 passed, 173 skipped, 1 failure, 0 modules timed out |

The one failure, `tests.skills.hep_ml.test_assets_smoke` `test_ddp_skeleton_two_gloo_processes` (two gloo processes
on loopback), occurred under `--jobs 4` load; it passes 3 of 3 times alone on E2, and no file it reads changed in
this release. `claude plugin validate --strict` and `codex plugin load` pass.

Passing checks show software consistency, not physical validity.

## DETSIM-W3A — 2026-11-01 (macOS 27.2 arm64, Python 3.13.2 venv; examples regenerated with the E2 venv, NumPy 2.5.3; version 0.53.0 + unreleased)

The detector-simulation shared layer's plan and identity part (adapter `adapters/detector-simulation`, verbs
`describe`, `check`, `prepare`) and contracts 3.18.0, checked with a simulator-free backend on synthetic inputs; no
simulator was run.

| Item | Evidence | Result |
|---|---|---|
| T-CANON | `tests/adapters/test_detsim_identity.py`: golden vectors through the four `canonical_sha256` copies and an independent JCS serializer; `normalize_decimal` edge cases (incl. `decimal-exponent-range`); `check_hash_scope` refusals by name; run digest and `run_id` encoding | 17 OK |
| T-SCHEMA | `tests/adapters/test_detsim_schemas.py`: positive and negative fixtures, unknown keys, units, supported keywords only, anchored patterns re-applied with `re.fullmatch` (walker over every schema pattern), a float in the hash scope refused | 12 OK |
| T-PLAN | `tests/adapters/test_detsim_plan.py`: same plan from four working folders and a moved project; replaced input, changed backend or shared-layer code, changed or corrupt environment record, another profile, one extra argv, one changed rendered byte → `plan-stale`; wrong `--plan-digest` → `digest-mismatch`; review-round regression tests | 35 OK |
| Without ROOT / uproot | `tests/adapters/test_detsim_missing_dependency.py` | 3 OK |
| Contracts | `unittest discover -s tests/contracts`; every 3.17 artifact under `contracts/fixtures`, `examples` and `profiles` (602) gives the same findings with the 3.18 validator (independent review) | 1160 run, OK (1 skipped); 602 identical |
| Conventions | layering, naming, wiring, reference inventory, skill scripts, interpreter guard, python compat, adapter declarations and missing-dependency, CLI robustness and contract | pass |
| Hostile `TMPDIR` | a symlinked folder whose name has a space and non-ASCII characters | OK |
| Independent review | three rounds (fresh subagents, advisory, shared host): round 1 0 major / 9 minor, round 2 1 major / 6 minor, round 3 no earlier finding open and 2 new minor findings, fixed with tests after round 3 (no fourth round) | findings fixed |

Passing checks show software consistency, not physical validity.

## DETSIM-WK — 2026-11-01 (E2 macOS 27.2 arm64, Python 3.13.2 venv; version 0.53.0 + unreleased)

The knowledge deliverable K of the detector-simulation task: the hep-detector guide
`sensor-and-gas-transport-tools.md`, the hep-computing guide `sensor-and-gas-simulation-operations.md`, the source
index and the 20-question set; no simulator was built or run for it, and every operational part is marked unverified.

| Item | Evidence | Result |
|---|---|---|
| Sources | `docs/dev/detector-simulation/SOURCES.md`: 56 records (commit or URL, lines, retrieval time, SHA-256, licence, review status) | recorded; content hashes re-checked by the independent reviewers |
| T-DISCOVER | `WR/scratch/WK/t-discover.txt` (raw log): `skills/hep-detector/SKILL.md` row "Simulation (Geant4)" → `detector-simulation.md` → the hep-detector guide; `skills/hep-computing/SKILL.md` → `analysis-workflows.md` / `environments-and-containers.md` → the operations guide; `tools/check_wiring.py` pass; no backend on the host; the non-author answerer reached both guides from both entry points (result sheet, path column) | pass |
| T-CONTENT (knowledge part) | 20 questions (4/4/4/3/3/2) answered by fresh non-author subagents from the three corpus files and five routing pages, graded element by element: run 4 on the final guides | 20 of 20 within range, no veto (runs 2 and 3: 19 of 20, the gaps fixed in the guides) |
| T-CONV | `reference_inventory --check` (0 overlap pairs), `check_wiring`, `check_layering`, `check_naming`, `check_routing_static`, `check_ownership`, `capability_map --check`, `skill_scripts --check`, `insert_interpreter_guard --check`; routing-table, reference-link and doc-consistency tests (also with a TMPDIR with a space and non-ASCII) | pass |
| Independent review | three rounds (fresh subagents, advisory, shared host): round 1 5 major / 11 minor, round 2 1 major / 4 minor, round 3 no earlier finding open and 3 new minor findings, fixed after round 3 (no fourth round) | findings fixed |

Passing checks show software consistency, not physical validity.

## DETSIM-W3B — 2026-11-02 (macOS 27.2 arm64, APFS, Python 3.13.2 venv; version 0.53.0 + unreleased)

The execution part of the detector-simulation shared layer (adapter 0.2.0: `run`, `inspect`, `check --probe`), tested
with the simulator-free synthetic backend and a cooperative program; no simulator was run.

| Item | Evidence | Result |
|---|---|---|
| T-IDEM, T-LOCK, T-NOKILL, T-ORPHAN, T-RUNNER, T-COMMIT, T-FS, T-GUARANTEE, T-PLATFORM, T-EXIT, T-CONTRACT, T-OUTPUT | `tests/adapters/test_detsim_run.py` (controllers as separate processes for lock, orphan, interruption and crash injection before commit and after rename; signal shims around `os.kill`, `os.killpg` and the runner's call; injected recorder for the fsync / F_FULLFSYNC / rename order; file-system types nfs, smbfs, cifs, fuse, osxfuse, s3fs, unknown refused) | 62 tests: 61 OK, 1 not run (platform: PR_SET_PDEATHSIG is Linux only) |
| `contracts/validate.py`, `contracts/verify_run.py` | after a successful and after a failed run, in the tests | pass (an input read in place is reported outside-base by design and named in the record) |
| Runner profile | macos-g0 as measured (V-04): commit_noreplace hard (`renamex_np`), durable_commit soft (F_FULLFSYNC on files), local_fs_check hard (apfs), timeout_kill hard, output_size_abort soft, descendants_killed soft, backend_dies_with_controller soft, no_network unsupported; linux-g0 every level unsupported (not measured) | declared and recorded per run |
| Hostile `TMPDIR` | a symlinked folder whose name has a space and non-ASCII characters | OK |
| Conventions | layering, naming, wiring, adapter declarations and missing-dependency, CLI robustness, python compat; `run_all_checks.py --part static --no-cli` | pass; static 29 pass, 0 fail, 2 skip (host CLIs) |
| Independent review | three rounds (fresh subagents, advisory, shared host): round 1 7 major / 17 minor, round 2 0 major / 5 minor, round 3 no earlier finding open and 1 new minor finding, fixed with a test after round 3 (no fourth round) | findings fixed |

Passing checks show software consistency, not physical validity.
