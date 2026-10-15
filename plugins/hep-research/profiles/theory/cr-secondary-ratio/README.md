# Cosmic-ray secondary ratio profile

Profile `theory:cr-secondary-ratio`, version 0.1.0: the first narrow cosmic-ray propagation domain. It predicts the
stable secondary-to-primary ratio B/C (boron from carbon and oxygen) in a weighted-slab (leaky-box) model and in a
1D diffusion-halo model with a thin disc and no convection, derives that the two agree for an escape grammage
lambda_esc = n_H m_H h v L / D, and records the consequence: B/C constrains D0/L, not D0 and L separately. It needs
no experiment profile and holds no detector, data or blinding content.

All shipped cross sections and transport values are **ILLUSTRATIVE** placeholders: the code and its checks are the
deliverable, not the numbers. Excluded: convection, reacceleration, losses, radioactive clocks, energy-dependent or
published cross sections, solar modulation, 2D geometry, comparison with data, and any propagation code.

This README is for people. The skills route through [index.md](index.md); the manifest is
[profile.json](profile.json).

## What it holds

- **Models** (`models/secondary-ratio-models.md`) and two illustrative cross-section sets (`models/xs-*.json`).
- **Derivation** (`scripts/derive.py`, recorded in `derivations/`): SymPy checks of the slab and thin-disc closed
  forms, their equivalence, the D0/L invariance and the finite-disc solution; `derivations/theory-spec.json` is the
  theory-spec artifact (`model.family: cosmic-ray-propagation`, `degenerate_directions: ["D0/L"]`).
- **Prediction** (`scripts/predict.py`): B/C at any parameter point, on grids, or bin-averaged in ln(E/n);
  `predictions/bc-benchmark.prediction.json` is the prediction artifact at the benchmark point, written by
  `scripts/make_artifacts.py`.
- **Benchmark** (`predict.py --benchmark`, settings in `benchmarks/bc-benchmark.json`): the closed forms against the
  profile's own numerical solutions (slab ODEs averaged over the path-length distribution; finite-thickness disc
  solved exactly and by finite volumes, and its thin-disc limit).
- **References** (`evidence/`, namespace `crsr`), cited from background knowledge; four of them opened on 2026-10-15
  for their tables and captions only, in the search for an external benchmark.
- **External benchmark: open (B1).** No publication examined on 2026-10-15 prints B/C or the escape grammage in a
  table for inputs this profile can reproduce (they tabulate fit parameters or cross sections and show B/C in
  figures only). The search, the reason per paper and what would close it are recorded in
  `benchmarks/external-benchmark-search.json` (claim `crsr:C06`); no value is read off a figure.

## Using it

```bash
python3 scripts/derive.py
python3 scripts/predict.py                                  # benchmark parameter point
python3 scripts/predict.py --set D0_cm2_s=2e28 --set L_kpc=6
python3 scripts/predict.py --grid D0_cm2_s=1e28,2e28,4e28 --grid L_kpc=2,4,8 --out grid.json
python3 scripts/predict.py --benchmark
python3 scripts/make_artifacts.py --check
```

For a grid fit, call `predict.evaluate(cfg, overrides)` or `predict.bin_averaged(cfg, edges, overrides)` per grid
point (`cfg` from `benchmarks/bc-benchmark.json`); `predict.grid` returns the Cartesian product, row-major.

## Tests

```bash
python3 -m unittest discover -s tests -t tests
```

`test_derivation.py` (SymPy), `test_missing_dependency.py`, `test_benchmark.py`, `test_prediction.py`,
`test_artifacts.py` (both artifacts validate; a theory-spec without `degenerate_directions` fails with
`theory.degeneracy_missing`) and `test_convention_mismatch.py`. Needs numpy, scipy and sympy.
