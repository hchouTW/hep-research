# Heliospheric modulation profile

Profile `theory:heliospheric-modulation`, version 0.1.0. Solar modulation of galactic cosmic rays in the force-field
approximation (Gleeson and Axford 1968). The force field is computed by the hep-measurement script
`skills/hep-measurement/scripts/solar_modulation_force_field.py`; this profile does not reimplement it. It adds the
derivation of the force-field solution (SymPy), its validity range and known limits with their sources, and a
closed-form benchmark: a power-law local interstellar spectrum modulated analytically, compared with the script in
total kinetic energy, kinetic energy per nucleon and rigidity. It needs no experiment profile and holds no detector,
data or blinding content.

Documented only: convection-diffusion, drift and 1D-3D numerical models, the neutron-monitor link, and multi-period
fits of phi (statistics: `skills/hep-statistics/references/time-series-inference.md`). Excluded: source terms (dark
matter, pulsars), galactic propagation, transients and any fitted or measured value.

This README is for people. The skills route through [index.md](index.md); the manifest is
[profile.json](profile.json).

## What it holds

- **Model** (`models/heliospheric-modulation-models.md`): force field, validity and limits table, other models.
- **Derivation** (`scripts/derive.py`, recorded in `derivations/`): the force-field solution, the flux relation and
  the closed forms with their limits; the theory-spec is written by `scripts/make_artifacts.py`.
- **Benchmark** (`scripts/predict.py --benchmark`, settings in `benchmarks/`): 90 synthetic points, the script against
  the closed forms to a relative 1e-10 (achieved about 2e-15); stored output `predictions/power-law-benchmark.json`.
- **References** (`evidence/`, namespace `helmod`).

## Using it

```bash
python3 scripts/derive.py
python3 scripts/predict.py --benchmark
python3 scripts/predict.py --point --kind rigidity --x 2 --mass 0.938272 --charge 1 --phi 0.6 --norm 1e4 --index 2.7
```

Or pin it in `hep-research.project.json` (`"theory": [{"profile": "theory:heliospheric-modulation", "version": "0.1.0"}]`).

## Tests

```bash
python3 -m unittest discover -s tests -t tests
```

`test_derivation.py` (SymPy), `test_benchmark.py` (runs the hep-measurement script about 120 times, a few seconds),
`test_convention_mismatch.py`, `test_artifacts.py` (theory-spec validates and is current) and
`test_missing_dependency.py`. Only the derivation needs SymPy; the benchmark is standard library.
