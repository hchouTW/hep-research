# VALIDATION — hep-research (partial, through M3)

Environment for all entries below: Claude Code cloud container (Linux 6.18 x86_64), Python 3.11.15, `.venv-hep` with numpy 2.4.6, scipy 1.17.1, matplotlib 3.11.2, sympy 1.14.0; Claude Code CLI 2.1.287. Date 2026-10-02.
Aggregate command: `python3 tools/run_all_checks.py --out <dir>`; latest run `tasks/hep-research/check-runs/check-run-2026-10-02T150623Z.json`: 8 pass / 0 fail / 0 skip; 851 unit tests: 816 pass, 0 fail, 35 skip (PyTorch, PyROOT, awkward/uproot, Combine, Graphviz, Mermaid, PlantUML, tectonic not installed here; these are unverified, not passing); AMS profile suite 257 pass.
Software checks establish contract consistency only: not physical validity, proof, statistical coverage, or authorization to unblind.

| AC | Result so far | Evidence | Remaining |
|---|---|---|---|
| AC01 | partial | Inventory covers 100% of 942 files; every one of 394 redistributed files has a record (`tasks/hep-research/m2/redistribution/*.csv`) written back to `docs/migration-map.csv`; AMS ledger and modules mapped (`m2/equivalence.md`); legacy skills untouched | Final traceability audit M6 |
| AC02 | partial | Seven SKILL.md with uses, exclusions, owned artifacts, handoffs; host validator `--strict` passes; no profile adds a skill | Discovery at G5 |
| AC03 | pass (M2 scope) | `check_layering.py` 0 violations after migration; experiment passages in moved text inside example blocks; new rule rejects profile paths in skill/core/contract text | Re-check M5 |
| AC04 | partial | ~2,005 always-on tokens (host estimate), SKILL.md 4.4–6.0 KiB | Real traces M5 |
| AC05 | partial | One owner per method recorded in `core/OWNERS.json` and the migration map; generic text inside AMS modules is a recorded dedupe item (DECISIONS M2-04) | Dedupe pass M3 |
| AC06 | pass | Registry negatives: duplicate ID, incompatible version, missing resource, template violation, escaping path (incl. symlink), cycle, missing dependency, unbacked capability, bad namespace, registry mismatch (`RegistryTests`) | — |
| AC07 | partial | 0/1/many × 0/1/many configs, local profile, conflict diagnostics, overrides need provenance (`ProjectConfigTests`) | Composition in M4 |
| AC08 | pass (M2 scope) | 60 sources / 183 claims as `ams02:` IDs; `check_ams_ledger_preservation.py` passes; index regenerated and in sync; modules for species, subsystems, methods, periods, sources; 7 metadata-only dataset records | Selective-loading traces M5 |
| AC09 | pass (M3 scope) | `tools/check_ams_optional.py`: plugin copied to a path with spaces without the AMS profile and its registry entry; registry check, Paths B and C, core/contracts/generic skill tests and both remaining profile suites pass. AMS tasks load selectively (M2) | Selective-loading traces M5 |
| AC10 | pass | `experiment:synthetic-collider` (illustrative) added with no change to skills, `core/`, `contracts/`, validators or algorithms: `tasks/hep-research/m3/ac10-diff.txt` lists only the profile, `profiles/registry.json`, `examples/`, `tests/examples/`; generator imports no theory code | — |
| AC11 | pass (benchmark scope) | `theory:qed-benchmark`: conventions, tree order, validity, `analytic-derivation` status (SymPy traces, 8 checks), PDG eqs. 51.2/51.3 read at page level (`qedbench:S01`, C01, C02), independent checks (Simpson, quad, trapezoid order 2.00), theory_spec and prediction artifacts (`examples/qed-benchmark/output/`) | Competing models T03 in M4 |
| AC12 | pass | Path C reads zero experiment-profile files (audit hook), artifacts carry no detector/data/blinding fields, SymPy/NumPy only, no GPU; numerical agreement recorded as corroboration, derivation status kept separate | — |
| AC13 | pass (M2 scope) | 16 valid / 18 invalid artifact fixtures; legacy AMS spec converter with valid, invalid, incomplete and legacy-form tests (20, `test_convert_legacy_spec.py`), lossless round trip, explicit refusal codes | — |
| AC16 | partial | Path A reproducible: `examples/ams-flux-ratio/run_path_a.py --toys 400 --seed 20261002` gives byte-identical `results.json` on rerun; report, figures, 6 contract-valid artifacts, all labeled synthetic (`tests/examples/test_path_a.py`, 11 tests); Path B (`examples/collider-angular/run_path_b.py`): fiducial σ 745.65 ± 6.63 (stat) ± 14.9 (lumi) pb vs 745.81 pb expected, χ² 10.4/10, byte-identical rerun (`tests/examples/test_path_b.py`, 8 tests); Path C reproducible (`tests/examples/test_path_c.py`, 4 tests) | Path D in M4 |
| AC17 | partial | Correlated ratio and time-dependent exposure (Path A, T10/T11); unchanged integral with changed shape (T12); theory conventions and checks (T13–T15, M3) | Low/zero counts in a path, response inefficiency, ML leakage M4 |
| AC18 | pass (M2 scope) | Ported original tests pass where tools exist (skips listed above); algorithm fixes only in `sci-fix:` commits, moves in `move:` commits; Path A seeds and tolerances in `results.json` | — |
| AC21 | partial | No values invented in dataset records; newer or inaccessible citations classed unverified (T17 sci-fix); three dates kept distinct (schema and ledger checks) | Private-evidence separation M4 |
| AC22 | partial | All five Section 12 corrections applied as `sci-fix:` commits with regressions (YAML subset docs, unverified citations, dates, T12, theory routing); synthetic labels on every Path A output; T18 blinding enforcement in `core/blinding` with synthetic tests across plots, ratios, logs, CSV and caches | Weight/normalization conventions and synthetic/Asimov/observed distinctions re-checked in Path D (M4) |
| AC29 | partial | Layering directions, no-hard-coded-profile rule (names, IDs, namespaces, paths), steward check enforced; one documented whitelist entry | Re-run M5 |
| AC30 | partial | J1–J12 traced (`docs/researcher-journeys.md`) | Executions M2–M5 |
| AC31 | partial | Vocabularies extensible by namespaced profile terms; non-collider normalization validates (T26); conventions gate T25 | Published-data comparison run M4 |
| others | not started | — | per task Section 10 |

## Tests (Section 11), through M3

| Test | Result | Evidence |
|---|---|---|
| T10 | pass (correlated ratio) | Path A He/p sigma equals an independent linear propagation with the shared trigger term to < 1e-15; treating it as independent overstates sigma by 1.00–1.17. Low/zero-count references: `core/stats` Poisson diagnostics tests (ported) |
| T11 | pass | Period average = sum of corrected counts / sum of per-period exposures; an equal live-time split mis-states low-rigidity exposure by up to 7.9% (synthetic), test asserts the difference |
| T12 | pass | `tests/skills/hep_analysis/test_check_systematic_variations.py`: unchanged integral with changed shape classified as shape, no propagation warning |
| T17 | pass | `profiles/experiments/ams-02/tests/test_docs_consistency.py` NewerLiteratureTests, DateWordingTests |
| T13 | pass | `profiles/theory/qed-benchmark/tests/test_convention_mismatch.py`: coupling normalization, angle definition, mass approximation (even at a 1e-6 effect) and a missing namespaced key are reported as mismatches; only a justified mapping makes them comparable |
| T14 | pass | `test_derivation.py`: status `analytic-derivation` (not proof) stored apart from the numerical checks; `test_prediction.py` records tolerances |
| T15 | pass | `test_prediction.py::test_convergence_study`: trapezoid refinement 3…257 points with observed order asserted within 0.05 of 2 and error reduced >1000×; Simpson (exact for this quadratic) and `scipy.integrate.quad` errors against the analytic bin integral are recorded; convergence is shown by the observed order, not by the loop ending |
| T18 | pass | `tests/core/test_blinding.py` (15 tests, synthetic): masked JSON/log/CSV/npz and a masked plot pass; detected leaks: SR value in a log, a rounded value (`1234.6`, `1.235e+03`) in a CSV, a raw npz cache, a data/MC ratio and a total including the SR, SR points in a main or ratio panel and in bar charts; CLI exit 0/1/2 |
