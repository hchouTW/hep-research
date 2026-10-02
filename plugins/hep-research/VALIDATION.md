# VALIDATION — hep-research (partial, through M2)

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
| AC13 | pass (M2 scope) | 16 valid / 18 invalid artifact fixtures; legacy AMS spec converter with valid, invalid, incomplete and legacy-form tests (20, `test_convert_legacy_spec.py`), lossless round trip, explicit refusal codes | — |
| AC16 | partial | Path A reproducible: `examples/ams-flux-ratio/run_path_a.py --toys 400 --seed 20261002` gives byte-identical `results.json` on rerun; report, figures, 6 contract-valid artifacts, all labeled synthetic (`tests/examples/test_path_a.py`, 11 tests) | Paths B–D in M3–M4 |
| AC17 | partial | Correlated ratio and time-dependent exposure (Path A, T10/T11); unchanged integral with changed shape (T12) | Low/zero counts in a path, response inefficiency, ML leakage, theory conventions M3–M4 |
| AC18 | pass (M2 scope) | Ported original tests pass where tools exist (skips listed above); algorithm fixes only in `sci-fix:` commits, moves in `move:` commits; Path A seeds and tolerances in `results.json` | — |
| AC21 | partial | No values invented in dataset records; newer or inaccessible citations classed unverified (T17 sci-fix); three dates kept distinct (schema and ledger checks) | Private-evidence separation M4 |
| AC22 | partial | All five Section 12 corrections applied as `sci-fix:` commits with regressions (YAML subset docs, unverified citations, dates, T12, theory routing); synthetic labels on every Path A output | T18 blinding across plots/logs/caches/reports not yet implemented |
| AC29 | partial | Layering directions, no-hard-coded-profile rule (names, IDs, namespaces, paths), steward check enforced; one documented whitelist entry | Re-run M5 |
| AC30 | partial | J1–J12 traced (`docs/researcher-journeys.md`) | Executions M2–M5 |
| AC31 | partial | Vocabularies extensible by namespaced profile terms; non-collider normalization validates (T26); conventions gate T25 | Published-data comparison run M4 |
| others | not started | — | per task Section 10 |

## Tests (Section 11), M2 scope

| Test | Result | Evidence |
|---|---|---|
| T10 | pass (correlated ratio) | Path A He/p sigma equals an independent linear propagation with the shared trigger term to < 1e-15; treating it as independent overstates sigma by 1.00–1.17. Low/zero-count references: `core/stats` Poisson diagnostics tests (ported) |
| T11 | pass | Period average = sum of corrected counts / sum of per-period exposures; an equal live-time split mis-states low-rigidity exposure by up to 7.9% (synthetic), test asserts the difference |
| T12 | pass | `tests/skills/hep_analysis/test_check_systematic_variations.py`: unchanged integral with changed shape classified as shape, no propagation warning |
| T17 | pass | `profiles/experiments/ams-02/tests/test_docs_consistency.py` NewerLiteratureTests, DateWordingTests |
| T18 | not run | Blinding enforcement across outputs not implemented yet |
