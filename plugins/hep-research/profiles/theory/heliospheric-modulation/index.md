# Heliospheric modulation profile: routing map

Profile `theory:heliospheric-modulation`: solar modulation of galactic cosmic rays in the force-field approximation.
The force field itself is computed by `<plugin root>/skills/hep-measurement/scripts/solar_modulation_force_field.py`;
this profile holds its derivation, validity range, limits and a closed-form benchmark. It needs no experiment profile.
Paths are relative to this folder.

| Request | Read |
|---|---|
| Force field, validity range, known limits; other models, neutron monitors, multi-period fits | `models/heliospheric-modulation-models.md` |
| Derivation, checks run and not run | `derivations/derivation-record.md` (run `scripts/derive.py`) |
| Theory-spec artifact | `derivations/theory-spec.json` (regenerate with `scripts/make_artifacts.py`) |
| Closed form vs the force-field script, one point or the benchmark | `scripts/predict.py --help`; settings `benchmarks/power-law-benchmark.json`; stored output `predictions/power-law-benchmark.json` |
| References and what is attributed to them | `evidence/sources.json`, `evidence/claims.json` |

Conventions: `conventions.json`. phi is a fitted effective parameter per period, degenerate with the LIS shape: never
quote a phi without its LIS and period. Fits of phi belong to hep-statistics
(`skills/hep-statistics/references/time-series-inference.md`).
