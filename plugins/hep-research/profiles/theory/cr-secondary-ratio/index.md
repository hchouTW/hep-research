# Cosmic-ray secondary ratio profile: routing map

Profile `theory:cr-secondary-ratio`: B/C in a weighted-slab (leaky-box) model and a 1D thin-disc diffusion model
without convection. It needs no experiment profile. Paths are relative to this folder. All shipped cross sections
and transport values are ILLUSTRATIVE.

| Request | Read |
|---|---|
| Models, assumptions, validity, what B/C can and cannot constrain | `models/secondary-ratio-models.md` |
| Derivation, D0/L degeneracy, checks run and not run | `derivations/derivation-record.md` (run `scripts/derive.py`) |
| Theory-spec artifact (model family, degenerate directions) | `derivations/theory-spec.json` |
| B/C at a parameter point, or on a (D0, L) grid | `scripts/predict.py --help`; in Python `predict.evaluate(cfg, {"D0_cm2_s": ..., "L_kpc": ...})`, `predict.grid(cfg, axes)`, `predict.bin_averaged(cfg, edges, overrides)` |
| Stored prediction artifact | `predictions/bc-benchmark.prediction.json` (regenerate with `scripts/make_artifacts.py`) |
| Benchmark: closed forms vs the profile's numerical solutions | `scripts/predict.py --benchmark`; settings `benchmarks/bc-benchmark.json` |
| Cross-section sets (inputs, model alternatives) | `models/xs-illustrative-A.json`, `models/xs-illustrative-B.json` |
| References and what is attributed to them (read level per source) | `evidence/sources.json`, `evidence/claims.json` |
| External benchmark (B1): open; search record and reasons | `benchmarks/external-benchmark-search.json` |
| Thin disc with convection (V_c) and radioactive decay (10Be, 10Be -> 10B gain): closed forms, limits, units | `derivations/convection-decay-record.md` (run `scripts/derive_convection_decay.py`); `scripts/convection_decay.py --help`, `--benchmark`; settings `benchmarks/convection-decay-benchmark.json` |

Conventions: `conventions.json`. The level `crsr:local-interstellar` is this profile's vocabulary: validate its
artifacts with `contracts/validate.py <artifact> --profiles-from <project config binding theory:cr-secondary-ratio>`.
B/C alone constrains D0/L only; never quote D0 or L separately from it. Fits belong to hep-statistics.
