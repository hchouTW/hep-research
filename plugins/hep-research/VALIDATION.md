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
