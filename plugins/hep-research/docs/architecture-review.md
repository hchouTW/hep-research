# Architecture Review (Gate G1)

Date 2026-10-02. Environment: Claude Code cloud container, Python 3.11.15 with `.venv-hep` (numpy 2.4.6, scipy 1.17.1, matplotlib 3.11.2, sympy 1.14.0), Claude Code CLI 2.1.287.
Aggregate run: `python3 tools/run_all_checks.py` → 6 pass, 0 fail, 0 skip; 47 unit tests pass.
Software checks show contract consistency only; they say nothing about physical validity.

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Journeys J1–J12 traced; gaps fixed or recorded | **Met.** Three gaps found and fixed (ratio cancellations, detector-level quantity types, parametrized response for recasting); two limitations recorded | `docs/researcher-journeys.md`; fixtures `measurement_ratio.json`, `response_parametrized.json` and their negatives |
| 2 | One definition owner and one implementation owner per method; contested topics resolved | **Met at file level; section level pending M2.** Every method file has a definition owner (a skill) and an implementation owner (`core/OWNERS.json`). Test files follow the code they test and `hep-analysis/scripts/*` carry a provisional owner; both are resolved per symbol in M2. No further contested topic was found | `core/OWNERS.json`; `tools/check_ownership.py` |
| 3 | `check_layering.py` passes on the skeleton with a minimal whitelist | **Met.** 0 violations; whitelist file absent (empty). Two real leaks were caught and fixed during M1 (an experiment name in a schema comment and in a skill description) | `python3 tools/check_layering.py` exit 0; T23 cases in `tests/tools/test_check_layering.py` (15 tests) |
| 4 | No collider-only or AMS-only term required by any core schema | **Met.** Schema-term scan finds none; normalization kinds include `exposure`, `protons-on-target`, `target-exposure`, `live-time`, `shape-only` | `check_layering.py` schema scan; T26 `NonColliderNormalizationTests` |
| 5 | Theory artifacts validate with all experiment fields absent | **Met.** `theory-spec` forbids experiment fields and experiment bindings | `TheoryIndependenceTests.test_theory_spec_has_no_experiment_fields`; negatives `theory_experiment_field.json`, `theory_experiment_binding.json` |
| 6 | Published-dataset comparison specifiable without detector modules | **Met at contract level.** A `dataset-record` with status `published` and evidence IDs validates with no response or detector field; the inference run itself is T24 in M4 | `TheoryIndependenceTests.test_dataset_record_without_detector_modules` |
| 7 | Project-config fixtures: 0/1/many experiments × 0/1/many theory, plus a local profile | **Met.** 9 matrix configs + local profile + 6 conflict cases (unknown profile, pin mismatch, conflicting pins, wrong axis, override without provenance, incompatible plugin) | `contracts/fixtures/projects/`; `ProjectConfigTests` |
| 8 | Host facts support skill access to shared resources, or fallback chosen | **Met.** Installed plugins are cached as a whole directory and `${CLAUDE_PLUGIN_ROOT}` resolves inline in skill content, so shared resources are reachable; fallback not needed. Still to observe live at G5 | `docs/architecture.md` host facts 4 (docs quotes, dated) |
| 9 | Always-loaded metadata and entry-point sizes measured | **Met.** ~2,005 always-on tokens for seven descriptions (host estimate); SKILL.md 4.4–6.0 KiB each; descriptions 773–919 characters; registry 47 B | `python3 tools/measure_entrypoints.py` |
| 10 | Risk register reviewed; new risks added | **Met.** R11 shared vocabulary namespaces, R12 fixtures mistaken for real profiles, R13 headless trace visibility | `docs/architecture.md` §8 |

## Decisions taken in M1

- `contracts/` may import `core/`; `core/` never imports `contracts/`.
- Profiles may declare `vocabulary_namespaces` (default: their evidence namespace), so a domain namespace such as one for cosmic-ray levels can be shared deliberately.
- Description working limit 1,024 characters (not a documented host limit).
- JSON-schema subset validator written in-house (no `jsonschema` dependency), keeping the mandatory environment to D5.

## Open items for M2+

- Section/symbol-level ownership (item 2).
- Full comparison gate (M4); headless load traces (M5, needs approval for paid runs).
- Live install, namespacing and coexistence test (G5, on the user's machine).
