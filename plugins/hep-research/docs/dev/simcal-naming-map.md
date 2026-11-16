# simcal naming map (hep-research 0.70.0)

The simulator parameter calibration workflow, **simcal**, shipped in 0.67.0 and 0.69.0 under names that use the bare
word "calibration". In HEP that word means detector constants (hep-detector), and hep-ml owns the calibration of model
outputs, so 0.70.0 renames the workflow's public names. The author approved the rename (a C3 rename of public names)
on 2026-11-16, record A34 in `simulator-calibration/simcal-approvals.md`. The naming extractors list no entity of these
kinds (module paths, script file names, schema ids), so this file is the naming record of the rename.

## Name map

| Old (0.69.0) | New (0.70.0) |
|---|---|
| `core/calibration/`, module `core.calibration` | `core/simcal/`, `core.simcal` |
| `contracts/schemas/calibration_<x>.json` (13 files) | `contracts/schemas/simcal_<x>.json` |
| `calibration-{contract,data-release,fixture,ledger,plan,result}/1` | `simcal-<x>/1` |
| `calibration-identity-equivalence/1`, `calibration-ask-tell/1`, `calibration-decisions/1` | `simcal-<x>/1` |
| `calibration-{control-variable,degeneracy-mode,functional,mechanism,parameter-index,reference,stage-graph}/1` (ids of the abstract schemas) | `simcal-<x>/1` |
| `g4sim-calib-eval-state/1` | `g4sim-simcal-eval-state/1` |
| `skills/hep-statistics/scripts/calib_<x>.py` (18 scripts) | `simcal_<x>.py` |
| `adapters/geant4/assets/g4sim_calib_eval.py` | `g4sim_simcal_eval.py` |
| `tests/core/test_calibration_<x>.py`, `tests/core/calibration_<x>.py` | `test_simcal_<x>.py`, `simcal_<x>.py` |
| `tests/contracts/test_calibration_schemas.py`, `tests/skills/test_calib_scripts.py` | `test_simcal_schemas.py`, `test_simcal_scripts.py` |
| `tests/skills/hep_statistics/test_cli_input_fuzz_calib_{a,b}.py` | `test_cli_input_fuzz_simcal_{a,b}.py` |
| `core/OWNERS.json` `modules.calibration` | `modules.simcal` |
| the schema name `calibration-result` in prose | `simcal-result` |

Class names inside the renamed modules are unchanged. The folders `skills/hep-detector/references/simulation-calibration/`
and `skills/hep-detector/assets/simulation-calibration/` keep their names.

## Names that do not change, and why

| Name | Why it stays |
|---|---|
| `calib-map-joint/1`, `calib-map-pde/1` | random-number keys shared with g4sim |
| `calib-map-basis/1`, `calib-masked/1` | inside identity hashes |
| the export key `calibration_result` and the prefix `calibration-result:` | written into `condition-snapshot/1` and `alignment-overlay/1` records |
| the data role `"calibration"` (`role="calibration"`), `calibration_releases`, `calibration_units`, `calibration_rows`, `calibration_fraction`, `calibration_slopes`, `--calibration`, `--calibration-units` | the role of data used to calibrate, as opposed to validation data; not the workflow's name |
| `extension.calibration`, `ml.calibration_*`, `skills/hep-ml/assets/calibration.py` | hep-ml's calibration of model outputs |
| the design role `"calibration"`, `calorimeter-calibration-plan`, `GEANT4_EVIDENCE_ROLES` | detector-side vocabulary |
| `skills/hep-statistics/scripts/bayes_calibration.py` | a statistics tool unrelated to simcal |
| the `"calibration"` topic of `docs/reference-inventory.json` | a reference topic, not the workflow |
| `REFERENCE_SHA256` (`c5279adf…`) and the frozen reference `calib_use_decision_table.py` | frozen evidence of phase 0 |
| the shared vocabulary `core/naming/data/hep-abbreviations.json` | shared by every skill |

The existing files of the frozen package `docs/dev/simulator-calibration/` and the history (`CHANGELOG.md`,
`VALIDATION.md`, release manifests) keep the old names.

## Alias window: 0.70.0 and 0.71.x, removed in 0.72.0

- **Schema ids.** The six schema files accept the new id and the old id (`enum`). `core/simcal/legacy.py` holds the old
  → new table; readers accept an old id through `legacy.is_schema`, which prints `simcal.legacy_schema_id: <old> is
  read as <new> …` once per id on stderr. Writers emit only new ids. No reader rewrites an id, so a 0.69.0 file is read
  and hashed as written: its hash citations still resolve, and its lock and result hashes are those of the file as
  written (they cover the `schema` field).
- **Module.** `core/calibration/__init__.py` warns once (`DeprecationWarning`) and makes `core.calibration.<m>` the same
  module object as `core.simcal.<m>`; `core/OWNERS.json` lists it as `deprecated-alias`.
- **Scripts.** `skills/hep-statistics/scripts/calib_<x>.py` and `adapters/geant4/assets/g4sim_calib_eval.py` print one
  notice (`simcal.deprecated_script`) and run the new script with the same arguments, so output and exit code are the
  new script's. They are not skill scripts (`tools/skill_scripts.json` lists none of them) and the CLI fuzz skips them.
- **Removal.** 0.72.0 (`CORE_VERSION` 2.0.0) removes the aliases, the shim and the stubs. A migration tool that
  rewrites old ids in users' files is a separate task due before 0.72.0: rewriting an id changes a file's hash and every
  hash that cites it, so it needs engine changes in gate-protected code.
