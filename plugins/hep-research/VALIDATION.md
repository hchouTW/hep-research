# VALIDATION — hep-research 0.1.0 (handover, M6)

Environment E1 for all entries below unless a row says otherwise: Claude Code cloud container (Linux 6.18 x86_64), Python 3.11.15, `.venv-hep` with numpy 2.4.6, scipy 1.17.1, matplotlib 3.11.2, sympy 1.14.0 (`requirements-core.txt`); Claude Code CLI 2.1.287. Date 2026-10-02. Branch `feat/hep-research-plugin` of hchouTW/hep-research; each row's evidence is at the final handover commit unless it names another. Legacy source `agentic-ai-skills@3e995a4`.
Aggregate command: `python3 tools/run_all_checks.py --out <dir>` (from the plugin root). Handover run `tasks/hep-research/check-runs/check-run-2026-10-02T174050Z.json`: 14 checks pass / 0 fail / 0 skip; 973 unit tests: 934 pass, 0 fail, 39 skip (PyTorch, PyROOT, awkward/uproot, pyhf, Combine, Graphviz, Mermaid, PlantUML, tectonic not installed; these are unverified, not passing); profile suites: ams-02 258, synthetic-collider 9, qed-benchmark 16 pass. pyhf rerun (user-approved install of pyhf 0.7.6 into `.venv-hep`, `tasks/hep-research/m6/pyhf/pip-freeze-pyhf.txt`): see PYHF-RUN below; uproot/awkward rerun: see UPROOT-RUN below; PyTorch rerun: see PYTORCH-RUN below; ROOT rerun: see ROOT-RUN below; diagram-tool rerun: see DIAGRAM-RUN below; torchvision rerun: see TORCHVISION-RUN below; Combine rerun (latest run, 985 pass, 0 fail, 3 skip): see COMBINE-RUN below. Seeds and tolerances of every example are in its `results.json`; commands are in each row.
Software checks establish contract consistency only: not physical validity, proof, statistical coverage, or authorization to unblind.

| AC | Result | Evidence | Remaining |
|---|---|---|---|
| AC01 | pass | `tools/check_traceability.py --legacy .legacy/agentic-ai-skills`: all 949 files tracked at `3e995a4` have a row in `docs/migration-map.csv` with source commit; 380 plugin files are concrete migration destinations, 415 are registered as new in `docs/provenance-new.csv` (commit and milestone from git history); every exclusion (`retain-outside`, `retire`) has a rationale; the legacy checkout is at the pin with no local change. Scientific changes are `sci-fix:` commits with regressions (AC22); 26 vague M1 destinations and 26 directory-valued destinations were made concrete in M6 | — |
| AC02 | pass | Seven SKILL.md with uses, exclusions, owned artifacts, handoffs; host validator `--strict` passes; no profile adds a skill; native discovery lists the seven `hep-research:*` skills (G5, `tasks/hep-research/m5/g5/G5-REPORT.md`) | — |
| AC03 | pass | `check_layering.py` 0 violations (re-run in M5, `check-run-2026-10-02T162614Z.json`); experiment passages in moved text inside example blocks; profile paths rejected in skill/core/contract text | — |
| AC04 | pass (budgets and traces) | `tasks/hep-research/m5/budgets.json`: SKILL.md 50–63 lines, 5.2–7.0 KiB (≤ 8 KiB), descriptions ≤ 921 chars, always-on ≈2,005 tokens, registry 690 B, profile indexes ≤ 2,370 B; no exceptions (M5-02). Host loading traces from 48 headless runs: no theory or computing case read an experiment profile (G5 run 2); invocation of `hep-theory` read only the registry and the theory profile (`tasks/hep-research/m5/g5/G5-REPORT.md`) | A run-1 trace (host env leaked in) shows one computing case reading the synthetic-collider generator; recorded, not counted |
| AC05 | pass | One definition and one implementation owner per method: `core/OWNERS.json` (stewards), migration map owner columns; each AMS method module now opens with a `Method owner:` line naming the owning skill and states that its general passages are legacy snapshots the owner overrides (`MethodOwnerTests` in the AMS profile suite); legacy skills documented as frozen snapshots (`docs/migration.md`) | Generic passages inside AMS modules were marked, not deleted (DECISIONS M6-02) |
| AC06 | pass | Registry negatives: duplicate ID, incompatible version, missing resource, template violation, escaping path (incl. symlink), cycle, missing dependency, unbacked capability, bad namespace, registry mismatch (`RegistryTests`) | — |
| AC07 | pass | 0/1/many × 0/1/many configs, local profile, conflict diagnostics, overrides need provenance (`ProjectConfigTests`); composition diagnostics for several profiles (`contracts/compat/compose.py`, `ComposeTests`); Path D binds two profiles; project config read by the installed plugin (J11 live case, G5 run 3) | — |
| AC08 | pass | 60 sources / 183 claims as `ams02:` IDs; `check_ams_ledger_preservation.py` passes; index regenerated and in sync; modules for species, subsystems, methods, periods, sources; 7 metadata-only dataset records. Live load traces (G5 run 3): J1 read the registry, `ams-02/index.md` and two modules; J2 read the index and one subsystem module ({G}) | — |
| AC09 | pass | `tools/check_ams_optional.py`: plugin without the AMS profile passes registry, Paths B and C, core/contract/generic tests and the other profile suites. Live traces: theory, computing and AMS-computing cases read no experiment profile; AMS cases read only `ams-02` files ({G}) | — |
| AC10 | pass | `experiment:synthetic-collider` (illustrative) added with no change to skills, `core/`, `contracts/`, validators or algorithms: `tasks/hep-research/m3/ac10-diff.txt` lists only the profile, `profiles/registry.json`, `examples/`, `tests/examples/`; generator imports no theory code | — |
| AC11 | pass (benchmark scope) | `theory:qed-benchmark`: conventions, tree order, validity, `analytic-derivation` status (SymPy traces, 8 checks), PDG eqs. 51.2/51.3 read at page level (`qedbench:S01`, C01, C02), independent checks (Simpson, quad, trapezoid order 2.00), theory_spec and prediction artifacts (`examples/qed-benchmark/output/`) | Competing models T03 in M4 |
| AC12 | pass | Path C reads zero experiment-profile files (audit hook), artifacts carry no detector/data/blinding fields, SymPy/NumPy only, no GPU; numerical agreement recorded as corroboration, derivation status kept separate | — |
| AC13 | pass | 16 valid / 18 invalid artifact fixtures; legacy AMS spec converter with valid, invalid, incomplete and legacy-form tests (`test_convert_legacy_spec.py`), lossless round trip, explicit refusal codes | — |
| AC14 | pass | `contracts/compat/gate.py`: quantity, units, variables and binning, phase space, frame, conventions, level, normalization kind, corrections, parameter point, validity range and uncertainty objects checked; transformations recorded with before/after state; double counting blocked (`tests/contracts/test_compat.py` GateTests, 17 tests); Path D rejects 9 mismatched variants, each naming the field and a resolution; a failing gate stops the dependent fit (`test_gate_failure_stops_the_fit`) | — |
| AC15 | pass | `contracts/compat/combine.py` + `skills/hep-statistics/scripts/combine_measurements.py`: independence never assumed (needs a scoped assumption), shared auxiliary measurements need a declared correlation, missing covariance stays missing, scale/model/truncation objects never enter a Gaussian matrix; positive (GLS = textbook BLUE, = whitened least squares) and negative fixtures (`CombinationTests`, `GlsTests`); model envelopes need a hep-theory prescription and stay non-Gaussian (`ModelSetTests`) | Real multi-experiment inputs are outside v1 |
| AC16 | pass | Path A reproducible: `examples/ams-flux-ratio/run_path_a.py --toys 400 --seed 20261002` gives byte-identical `results.json` on rerun; report, figures, 6 contract-valid artifacts, all labeled synthetic (`tests/examples/test_path_a.py`, 11 tests); Path B (`examples/collider-angular/run_path_b.py`): fiducial σ 745.65 ± 6.63 (stat) ± 14.9 (lumi) pb vs 745.81 pb expected, χ² 10.4/10, byte-identical rerun (`tests/examples/test_path_b.py`, 8 tests); Path C reproducible (`tests/examples/test_path_c.py`, 4 tests) ; Path D (`examples/theory-comparison/run_path_d.py`, `tests/examples/test_path_d.py`, byte-identical to the committed output); T24 (`examples/published-comparison/run_t24.py`); J2 and J7 examples reproduce byte for byte (`tests/examples/test_journeys_j2_j7.py`) | — |
| AC17 | pass | Correlated ratio and time-dependent exposure (Path A, T10/T11); unchanged integral with changed shape (T12); theory conventions and checks (T13–T15, M3) ; response inefficiency and double-counted efficiency (T07), ML group leakage and surrogate domain (T16), low and zero counts in the Path D Poisson likelihood (`LowCountTests`) | — |
| AC18 | pass | Ported original tests pass where tools exist (skips listed above are unverified); algorithm fixes only in `sci-fix:` commits, moves in `move:` commits; seeds and tolerances in each example's `results.json` | — |
| AC19 | pass | Failure statuses propagate (T20: missing tool, solver failure, `failed` required downstream and in communication claims); bounded recovery in `local_partition.py`: no retries without configuration, `max_attempts` limit, stop after two identical failures with state kept, explicit reset with a reason (T21, `tests/skills/hep_computing/test_local_partition.py`) | — |
| AC21 | pass | No values invented in dataset records; newer or inaccessible citations classed unverified (T17); three dates kept distinct; a private local profile is usable through project config and absent from the plugin tree (T27); packaging scan of every distributable file finds no private paths, credentials, transcripts, rubrics, caches or project artifacts (`tools/check_packaging.py`) | — |
| AC22 | pass | All five Section 12 corrections as `sci-fix:` commits with regressions (YAML subset docs, unverified citations, dates, T12, theory routing); blinding across plots, ratios, logs, CSV, caches and reports (T18); signed weights pass through unclipped (`test_negative_yield_is_reported_not_clipped`), normalization by `sum(signed weights)` stated in `hep-analysis` references and non-collider normalization kinds (T26); `observed` cannot be combined with `synthetic` or `asimov` (`DataKindStatusTests`), Path D keeps Asimov and synthetic-observed results apart | — |
| AC23 | pass | No adapter claims more than its least-tested tool: `adapters/pyhf-combine` (since COMBINE-RUN) and `adapters/root-uproot` are both `demonstrated-on-synthetic-data` (Combine 11.1.0, COMBINE-RUN; ROOT 6.40.04, ROOT-RUN) in `docs/capability-matrix.md`; in `adapters/pyhf-combine` the pyhf part is `demonstrated-on-synthetic-data` (pyhf 0.7.6, `tests/adapters/test_pyhf_counting.py`, `test_pyhf_shape.py` and the end-to-end sample) and the Combine part `demonstrated-on-synthetic-data` (Combine 11.1.0 with ROOT 6.36.14); in `adapters/root-uproot` the uproot/awkward part is `demonstrated-on-synthetic-data` (uproot 5.7.6, awkward 2.14.0, `tests/adapters/test_uproot_awkward_asset.py`) and, since ROOT-RUN, the ROOT part too; per-tool status, versions and the lowest-status rule are enforced by `AdapterDeclarationTests`; tools not installed are labeled unverified | Combine checked on one synthetic counting card only, and only with ROOT 6.36.14; adapters not run on real experiment files |
| AC20 | pass (with noted misses) | Static: 48 cases pass `check_routing_static.py`. Live, Claude Code 2.1.287, claude-sonnet-5-5, plugin only, synthetic inputs per case (run 3): 41/48 route to the expected owner or ask (en 27/33, zh-Hant 14/15); 2 go to a neighboring plugin skill (J5 to detector-response, J12 to hep-computing with the limited-support notice); 5 load no skill. No dispatch API used; no experiment profile loaded by theory or computing cases. With the seven legacy skills also installed (run 2) the legacy predecessor won 7 cases (`tasks/hep-research/m5/g5/G5-REPORT.md`). Routing round 2 (run 4, tuned `hep-theory` and `hep-statistics` descriptions): 43/48; over three runs of the 10 changed cases, old 12/30 vs new 16/30 (report section "Routing round 2") | Misses listed in the report; short theory questions answered directly remain unreliable |
| AC24 | pass | Relocation (`relocation-20261002T161906Z.json`; rerun at handover `tasks/hep-research/m6/relocation-20261002T172735Z.json`: 12 pass, 2 skip because the ledger-preservation and traceability checks need the source repository and legacy checkout) and native Claude Code 2.1.287 install, discovery, namespaced invocation, profile access from the installed path (a path with spaces), removal (`tasks/hep-research/m5/g5/G5-REPORT.md`) | — |
| AC27 | pass | `docs/capability-matrix.md` per capability, profile, adapter and host with tested / unverified / proposed / not-in-v1 and environment E1; adapter rows match `adapter.json` (`AdapterDeclarationTests`); all four mandatory paths ran and the host test is recorded (G5) | — |
| AC25 | pass | Seven legacy skills installed beside the plugin stay byte-identical through install, ~100 headless runs and removal; plugin skills are namespaced `hep-research:*`; the test project directory stays empty (`tasks/hep-research/m5/g5/G5-REPORT.md`) | Routing preference between legacy and plugin skills is reported under AC20 |
| AC26 | pass | Guides: `docs/profile-authoring.md`, `docs/adapter-authoring.md`, `docs/maintenance.md` (porting fixes, rerunning comparisons, ledgers, schema migration, versioning, traceability, routing), `docs/migration.md` (coexistence, disabling legacy skills, rollback). Reproducible checks: `run_all_checks.py`, `check_relocation.py`, `check_traceability.py`, ledger and registry validators; adapter declarations tested so no untested tool is advertised | — |
| AC28 | pass | This file, `tasks/hep-research/PROGRESS.md` (handover state, resume checklist), `DECISIONS.md`, the G5 report and the limitations section below; unresolved external conditions and their effect listed there | — |
| AC29 | pass | Layering directions, no-hard-coded-profile rule (names, IDs, namespaces, paths), steward check enforced and re-run in M5; one documented whitelist entry | — |
| AC30 | pass | J1–J12 traced (`docs/researcher-journeys.md`); every journey is executed or answered: J1 Path A, J2 `examples/detector-resolution/run_j2.py`, J3 Path B, J4 Path C, J5 Path D, J6 T24, J7 `examples/recasting/run_j7.py`, J8 T15, J9 T16, J10 T20, J11 T27 (all synthetic); one live routing case per journey (G5 run 3); J12 gives the limited-support notice. J2 and J7 tests: `tests/examples/test_journeys_j2_j7.py` (13 tests, byte-identical reruns) | — |
| AC31 | pass | Vocabularies extensible by namespaced profile terms; non-collider normalization validates (T26); conventions gate T25 ; published-style record compared without detector modules (T24, load trace) | — |

## Tests (Section 11)

| Test | Result | Evidence |
|---|---|---|
| T10 | pass (correlated ratio) | Path A He/p sigma equals an independent linear propagation with the shared trigger term to < 1e-15; treating it as independent overstates sigma by 1.00–1.17. Low/zero-count references: `core/stats` Poisson diagnostics tests (ported) |
| T11 | pass | Period average = sum of corrected counts / sum of per-period exposures; an equal live-time split mis-states low-rigidity exposure by up to 7.9% (synthetic), test asserts the difference |
| T12 | pass | `tests/skills/hep_analysis/test_check_systematic_variations.py`: unchanged integral with changed shape classified as shape, no propagation warning |
| T17 | pass | `profiles/experiments/ams-02/tests/test_docs_consistency.py` NewerLiteratureTests, DateWordingTests |
| T13 | pass | `profiles/theory/qed-benchmark/tests/test_convention_mismatch.py`: coupling normalization, angle definition, mass approximation (even at a 1e-6 effect) and a missing namespaced key are reported as mismatches; only a justified mapping makes them comparable |
| T14 | pass | `test_derivation.py`: status `analytic-derivation` (not proof) stored apart from the numerical checks; `test_prediction.py` records tolerances |
| T15 | pass | `test_prediction.py::test_convergence_study`: trapezoid refinement 3…257 points with observed order asserted within 0.05 of 2 and error reduced >1000×; Simpson (exact for this quadratic) and `scipy.integrate.quad` errors against the analytic bin integral are recorded; convergence is shown by the observed order, not by the loop ending |
| T03 | pass | `ModelSetTests`: two theory-only predictions keep their own theory specs and assumptions; a shared spec is rejected; an envelope needs a hep-theory prescription and is non-Gaussian; the validator rejects a Gaussianized model alternative |
| T04 | pass | `GlsTests`: two illustrative datasets with a declared shared normalization; GLS equals the textbook one-bin BLUE and a whitened least-squares reference to 1e-12 |
| T05 | pass | `CombinationTests.test_T05_overlapping_auxiliary_requires_joint_treatment`: a shared auxiliary measurement without a declared correlation refuses combination ("comparison-only"); declared independence that contradicts the overlap is reported |
| T06 | pass | `ComposeTests`: `ams02:C01` and `beta:C01` stay distinct; a correlation between them needs evidence or a scoped assumption |
| T07 | pass | Validator `response.double_counted`; gate rejects efficiency applied before folding with a response that includes it, and folding a detector-level prediction (`test_handoffs.py`, `test_compat.py`) |
| T08 | pass | Wrong level, units, binning rejected; documented conversions (unit conversion, exact rebinning, fiducial restriction with level identification) accepted, and the restricted prediction integrates to the theory profile's own fiducial cross section (`test_t24.py`) |
| T09 | pass | Missing covariance reported and kept missing by the gate and the combination plan; a scale envelope is marked not Gaussian and not quantified |
| T16 | pass | Group leakage found by `check_split_integrity.py`; `check_surrogate_domain.py` flags outside and sparse queries; AUC-only validation is a contract error |
| T19 | pass | `review_analysis_change.py`: control-sample calibration accepted with provenance; change after looking at signal-region data flagged (not refused); missing provenance asked for |
| T20 | pass | Missing tool and solver failure give `failed` artifacts; consumers without `failed` fail validation; communication cannot drop or upgrade statuses |
| T21 | pass | `examples/local-partition/run_partition.py` (10 criteria): no retry without config, missing work detected, finished chunks not rerun, transient failure recovered, repeated identical failure stops with state kept, completion after a reset, merged = single run (counts exact, floating sum within 1e-9), stray duplicate and foreign chunks excluded |
| T24 | pass | `examples/published-comparison/run_t24.py`: gate and GLS fit on a synthetic published-style record; load trace shows no `profiles/experiments/` file; GLS bias for multiplicative covariance reported as a limitation |
| T27 | pass | `PrivateLocalProfileT27`: local profile in a project path with spaces validates, extends the vocabulary only when loaded, and its namespace appears nowhere in the plugin |
| T28 | pass | Bayesian needs priors, sampler and convergence; frequentist needs construction and coverage; mislabeled results rejected (`ParadigmsT28` and M1 fixtures) |
| T18 | pass | `tests/core/test_blinding.py` (15 tests, synthetic): masked JSON/log/CSV/npz and a masked plot pass; detected leaks: SR value in a log, a rounded value (`1234.6`, `1.235e+03`) in a CSV, a raw npz cache, a data/MC ratio and a total including the SR, SR points in a main or ratio panel and in bar charts; CLI exit 0/1/2 |
| T22 | pass | Install from a copy of tracked files only, relocation, removal, legacy coexistence and separate project state (`tasks/hep-research/m5/g5/G5-REPORT.md`, AC24, AC25) |
| T01 | pass | `RegistryTests` (`tests/contracts/test_contracts.py`): duplicate profile ID, incompatible version and missing resource fail with the offender named; dependent resolution stops |
| T02 | pass | `RegistryTests`: dependency cycle, package-escaping path (including a symlink) and template violation fail deterministically, naming the offender |
| T23 | pass | `tests/tools/test_check_layering.py`: core importing a profile, a profile path or hard-coded AMS ID in core skill text, contracts importing skills; each reported with file and line |
| T25 | pass | `ConventionsGateTests`: unknown or namespaced convention keys on one side make the gate report not comparable unless a justified mapping is declared |
| T26 | pass | `NonColliderNormalizationTests`: `exposure`, `protons-on-target`, `target-exposure` measurement specs validate with no luminosity field |

## Known limitations and unresolved external conditions

| Item | Effect |
|---|---|
| tectonic 0.17.0 installed but unusable because the network policy blocks its TeX bundle host (relay.fullyjustified.net); the Combine test needs `HEP_COMBINE_WRAPPER` and Combine works only in the ROOT 6.36.14 build (COMBINE-RUN) | 3 tests skipped (tectonic, unverified; 2 no-PyTorch degradation tests that skip when PyTorch is present and pass under the system Python without it); the paper-build capability row is `unverified`. CMS Combine, pyhf, uproot, awkward, PyTorch, torchvision, ROOT, Graphviz, Mermaid CLI and PlantUML were installed after approval and their tests pass (PYHF-RUN, UPROOT-RUN, PYTORCH-RUN, ROOT-RUN, DIAGRAM-RUN, TORCHVISION-RUN, COMBINE-RUN); `vision_transfer.py` is not run with its pretrained ResNet-18 weights, which it downloads from download.pytorch.org (blocked by the network policy) |
| PyTorch verified on CPU only | GPU, NCCL and GPU mixed precision not tried; the CPU-only wheel index is blocked by the network policy, so the PyPI build (with CUDA libraries, unused) was installed |
| pyhf demonstrated on two synthetic workspaces, asymptotic only | toy-based CLs, lumi/shapefactor modifiers and non-default interpolation codes not tried |
| Live routing measured once on one host model (claude-sonnet-5-5 via `claude -p`) | 41/48 cases correct; 7 misses listed in the G5 report; with legacy skills co-installed the legacy predecessor wins some requests (7/48 in run 2) |
| J2 and J7 run on synthetic inputs only | J2 uses the invented Gaussian detector; J7 has one signal region, an efficiency map without its own uncertainty, and a toy model; interchange formats (HEPData-style records, recasting frameworks) stay `proposed` |
| Combination is Gaussian (GLS) only | non-Gaussian components are refused, not combined; Peelle's-puzzle bias for multiplicative covariance documented in T24 |
| Truncation uncertainty (theory) not quantified | recorded as a non-Gaussian object, never folded into a covariance |
| AMS module generic passages kept as marked snapshots | the owner skill's text applies where they differ (AC05) |
| Hosts other than Claude Code | not tested; notes say so |
| Old branch in agentic-ai-skills (M1-12) | left for the owner to delete; no effect on the plugin |

## PYHF-RUN (2026-10-02, after the handover run)

Environment: E1 plus pyhf 0.7.6, jsonschema 4.26.0, click 8.5.0 (numpy unchanged at 2.4.6); full list in
`tasks/hep-research/m6/pyhf/pip-freeze-pyhf.txt`. Command: `python3 tools/run_all_checks.py --out <dir>` from the
plugin root, run `tasks/hep-research/check-runs/check-run-2026-10-02T174930Z.json`: 975 unit tests, 940 pass,
0 fail, 35 skip; profile suites unchanged (258, 9, 16 pass). Traceability passed after registering the new test
file (the run before the commit flagged it as unregistered).
Shape-workspace rerun: `check-run-2026-10-02T180440Z.json`, 979 unit tests, 944 pass, 0 fail, 35 skip; traceability
again passed once the three new files were registered.

| Item | Result | Evidence |
|---|---|---|
| End-to-end sample (`examples/end-to-end-sample/`) | pass, 4 of 4 (previously skipped) | `tests/examples/test_end_to_end_sample.py` |
| pyhf counting workspace (`adapters/pyhf-combine/assets/pyhf-counting.json`, SYNTHETIC s=5, b=20, n=20, 10% background normsys) | pass | `tests/adapters/test_pyhf_counting.py` (2 tests) |
| Asymptotic CLs 95% upper limit on mu | observed 2.1529; expected band 1.097 / 1.503 / 2.153 / 3.129 / 4.419 (-2σ…+2σ) | pyhf `upper_limit`, scan 0–5 in 501 points; the independent implementation (`tests/adapters/histfactory_reference.py`, q̃_mu, background-only Asimov) gives 2.1529; the legacy Combine template documents 2.153 for the same model. (The first version of this check used exponential normsys interpolation and gave 2.1541; pyhf's default is code 4, corrected in the next commit.) |
| Two-channel shape workspace (`assets/pyhf-shape-synthetic.json`, SYNTHETIC: 3-bin signal region, 2-bin control region; normsys, histosys, staterror, shapesys) | pass | `tests/adapters/test_pyhf_shape.py` (4 tests): log-likelihood equal to the reference within 1e-9 at 200 random points with nuisance values inside and outside the interpolation region; best-fit NLL within 1e-4; observed CLs limit 2.4320 (pyhf) vs 2.4319 (reference) |
| Combine template run | skip (Combine not installed); verified later in COMBINE-RUN | `CombineRunTests`; unverified in this run |

## UPROOT-RUN (2026-10-02, after the merge of PR #1)

Environment: E1 plus pyhf 0.7.6 (PYHF-RUN), uproot 5.7.6, awkward 2.14.0 (awkward_cpp 57), PyYAML 6.0.3; full list in
`tasks/hep-research/m6/uproot/pip-freeze-uproot.txt`. Run `tasks/hep-research/check-runs/check-run-2026-10-02T183213Z.json`:
982 unit tests, 955 pass, 0 fail, 27 skip; profile suites unchanged (258, 9, 16 pass). Traceability passed after
registering the new test file.

| Item | Result | Evidence |
|---|---|---|
| Previously skipped uproot/awkward tests (synthetic NanoAOD generator, awkward reference values) | pass, 8 tests no longer skipped | `tests/skills/hep_computing/test_hep_analysis_synthetic_nanoaod.py`, `tests/skills/detector_response/test_hep_analysis_reference_values.py` |
| `adapters/root-uproot/assets/uproot_awkward_analysis.py` on a SYNTHETIC file (4000 events, 0–4 muons, 15% negative weights) | pass | `tests/adapters/test_uproot_awkward_asset.py` (3 tests): TH1D bin contents and sum(w^2) equal an independent numpy computation; selected-event count matches; a missing branch is refused |
| PyROOT / RDataFrame / RooFit assets | skip (ROOT not installed) | unverified |

## PYTORCH-RUN (2026-10-02, after the merge of PR #2)

Environment: E1 plus pyhf, uproot and awkward (PYHF-RUN, UPROOT-RUN) and PyTorch 2.14.1 from PyPI (CUDA 13.0 build;
no GPU, so all runs are CPU, 4 threads); full list in `tasks/hep-research/m6/pytorch/pip-freeze-pytorch.txt`. Run
`tasks/hep-research/check-runs/check-run-2026-10-02T190132Z.json`: 14 checks pass; 982 unit tests, 966 pass, 0 fail,
16 skip; profile suites unchanged (258, 9, 16 pass).

| Item | Result | Evidence |
|---|---|---|
| physics-ml tests needing PyTorch (allocation measurement, dataset building, asset smoke tests: training, inference, metrics, datasets) | pass, 13 tests no longer skipped | `tests/skills/physics_ml/test_deep_learning_deep_learning_skill.py`, `test_deep_learning_assets_smoke.py` |
| `ddp_train_skeleton.py` with `torchrun --nproc_per_node=2` (gloo backend) | pass | `test_ddp_skeleton_two_gloo_processes`; the test now finds `torchrun` next to the interpreter, not only on PATH |
| Clean degradation without PyTorch | pass under the system Python 3.11 (no torch), skipped in `.venv-hep` | `CleanDegradationWithoutTorchTests` (2 tests) |
| `vision_transfer.py` | skip (torchvision not installed, not approved); verified later in TORCHVISION-RUN | unverified in this run |

## ROOT-RUN (2026-10-02, after the merge of PR #4)

Environment: E1 plus the packages of PYHF-RUN, UPROOT-RUN and PYTORCH-RUN in `.venv-hep`; ROOT 6.40.04 from
conda-forge (Python 3.11.16, conda gcc 16.2.0, C++20 build) in a project-local micromamba 2.9.0 environment
(`.venv-hep-root/`, gitignored; package list `tasks/hep-research/m6/root/conda-explicit-root.txt`); cmake 3.28.3.
Command: `HEP_ROOT_PYTHON=.venv-hep-root/env/bin/python .venv-hep/bin/python plugins/hep-research/tools/run_all_checks.py
--out tasks/hep-research/check-runs`, run `check-run-2026-10-02T193628Z.json`: 987 unit tests, 978 pass, 0 fail, 9 skip;
profile suites unchanged; traceability passed after registering the new test file (that run flagged it).

| Item | Result | Evidence |
|---|---|---|
| PyROOT scripts and assets (inspection, histogram comparison, systematic variations, histogram statistics, RooFit workspace summary, RDataFrame cutflow, RooFit peak fit recovers mean 91 within 0.5) | pass, 7 tests no longer skipped | `tests/skills/hep_computing/test_hep_analysis_root_integration.py` |
| C++ assets `cpp_rdataframe_analysis.cpp`, `fit_histogram.cpp`, `rdf_analysis.cpp` built with `root-config`; CMake `analysis` target; `plot_branch.C` in batch | pass, 5 new tests | `tests/adapters/test_root_cpp_assets.py`; the C++ cutflow (3044, 2718, 2223 of 5000 synthetic events) equals the PyROOT asset's |
| CMS Combine run of the datacard template | skip (Combine not installed); verified later in COMBINE-RUN | unverified in this run |

## DIAGRAM-RUN (2026-10-02, after the merge of PR #5)

Environment: as in ROOT-RUN, plus Graphviz 14.1.2, PlantUML 1.2026.8 (with its conda-forge OpenJDK) and tectonic
0.17.0 from conda-forge in a project-local micromamba environment (`.venv-hep-diagrams/env`, gitignored; package list
`tasks/hep-research/m6/diagrams/conda-explicit-diagrams.txt`), and Mermaid CLI 12.0.0 from npm in
`.venv-hep-diagrams/node` (Node 22.22.0; `tasks/hep-research/m6/diagrams/npm-mermaid.txt`) driven by the preinstalled
Playwright Chromium 141 through a wrapper `.venv-hep-diagrams/bin/mmdc` (puppeteer config with `--no-sandbox`).
`.venv-hep-diagrams/bin` holds `dot`, `plantuml` and `mmdc` and is put first on PATH.
Command: `PATH=.venv-hep-diagrams/bin:$PATH HEP_ROOT_PYTHON=.venv-hep-root/env/bin/python .venv-hep/bin/python
plugins/hep-research/tools/run_all_checks.py --out tasks/hep-research/check-runs`, run `check-run-2026-10-02T201906Z.json`:
987 unit tests, 982 pass, 0 fail, 5 skip; all 14 checks pass.

| Item | Result | Evidence |
|---|---|---|
| Graphviz `dot` accepts a valid graph and rejects an invalid one | pass, 2 tests no longer skipped | `tests/skills/research_communication/test_academic_diagrams_academic_diagrams_skill.py` (DotCompile) |
| Mermaid CLI rejects bad flowchart syntax | pass, no longer skipped | same file, `test_real_mmdc_rejects_bad_syntax` |
| PlantUML rejects a one-line class body | pass, no longer skipped | same file, `test_real_plantuml_rejects_one_line_class_body` |
| Every shipped diagram source passes `check_diagram_sources.py` with the real tools present | pass | same file, `test_shipped_diagram_sources_pass` |
| Bundled paper skeleton compiles with tectonic | unverified | with tectonic on PATH the test fails before compiling: tectonic must download its TeX bundle from relay.fullyjustified.net, which the network policy rejects (proxy CONNECT 403). tectonic is therefore left off PATH and the test skips; its skip message still says "tectonic not installed" |

## TORCHVISION-RUN (2026-10-02, after the merge of PR #6)

Environment: as in DIAGRAM-RUN, plus torchvision 0.29.1 from PyPI installed into `.venv-hep` with `--no-deps` so torch
2.14.1 stays unchanged (its requirements torch>=2.14.0, numpy and pillow 12.3.0 were already present; `pip check`
clean); list in `tasks/hep-research/m6/torchvision/pip-freeze-torchvision.txt`. Same command as DIAGRAM-RUN, run
`check-run-2026-10-02T231655Z.json`: 988 unit tests, 984 pass, 0 fail, 4 skip; all 14 checks pass.

| Item | Result | Evidence |
|---|---|---|
| `vision_transfer.py --help` | pass, no longer skipped | `tests/skills/physics_ml/test_deep_learning_assets_smoke.py`, `test_vision_transfer_help` |
| `vision_transfer.py` trains one epoch on a SYNTHETIC ImageFolder (random 32x32 images, 2 classes, 8 train and 4 val) with a frozen backbone and saves a checkpoint with the right classes and a 2x512 head | pass, new test | same file, `test_vision_transfer_trains_on_synthetic_image_folder`; the test builds ResNet-18 with `weights=None` |
| `vision_transfer.py` with its pretrained ResNet-18 weights | unverified | the weights download from download.pytorch.org, which the network policy blocks; accuracy on real images is not assessed |

## COMBINE-RUN (2026-10-02, after the merge of PR #7)

Environment: as in TORCHVISION-RUN, plus CMS Combine 11.1.0 from conda-forge (build `py313h7c74f60_0`, ROOT 6.36.14,
Python 3.13) in a project-local micromamba environment `.venv-hep-combine/env-root636` (gitignored; package list
`tasks/hep-research/m6/combine/conda-explicit-combine-root636.txt`). The test reaches it through
`HEP_COMBINE_WRAPPER=.venv-hep-combine/bin/combine-env`, a script that runs its arguments under `env -i` with that
environment's `bin` first on PATH. Command: as in DIAGRAM-RUN with `HEP_COMBINE_WRAPPER` set, run
`check-run-2026-10-02T233444Z.json`: 988 unit tests, 985 pass, 0 fail, 3 skip; all 14 checks pass.

| Item | Result | Evidence |
|---|---|---|
| Combine datacard template filled with the SYNTHETIC counting model (s=5, b=20, n=20, 10% background lnN), `text2workspace.py` then `combine -M AsymptoticLimits --rMax 10` | pass, no longer skipped: observed 2.1565, expected 1.1118 / 1.5116 / 2.1562 / 3.1275 / 4.3733 (2.5% to 97.5%); pyhf 0.7.6 gives 2.153 (test tolerance 2%) | `tests/skills/hep_statistics/test_hep_analysis_combine_template.py`, `test_limit_matches_pyhf` |
| `adapters/pyhf-combine` | `demonstrated-on-synthetic-data` (was `proposed`); version 0.4.0 | `adapter.json`, `AdapterDeclarationTests` |
| Combine 11.1.0 built against ROOT 6.40.04 (the conda-forge default) | fail, not used: `AsymptoticLimits` prints no limit and logs `Caught exception Value 26.4507 is outside the default range [0, 14.5482] of the variable "r"!` (the same with no `--rMax` or `--rMax 50`); recorded in `tasks/hep-research/m6/combine/conda-explicit-combine-root640-failed.txt`; cause not investigated beyond this | unverified with ROOT 6.40 |

