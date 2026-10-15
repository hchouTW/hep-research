# Secondary antiproton source term profile

Profile `theory:cr-secondary-antiprotons`, version 0.1.0: the source term of secondary antiprotons,

    q_ij(T) = 4 pi n_j int_{T_th}^oo dT_i phi_i(T_i) dsigma_ij/dT(T_i, T),

for cosmic-ray projectiles i = p, He on interstellar targets j = H, He (channels pp, pHe, Hep, HeHe), times the
antineutron and hyperon factor (2 + Delta_IS + 2 Delta_Lambda). The conventions are those of the hep-theory
reference `skills/hep-theory/references/cosmic-ray-propagation.md` (section "Secondary antiprotons: source-term
conventions", after Korsmeier, Donato and Di Mauro 2018, di Mauro et al. 2014 and Winkler 2017). It needs no
experiment profile and holds no detector, data or blinding content.

The cross sections are a **TOY** x-scaling form, (sigma0 / T_i) (1 - T/T_i)^n above the pp threshold, with constant
channel factors and constant Delta_IS and Lambda-bar/pbar, all **ILLUSTRATIVE**: none of the published
parametrizations is used for the prediction. The toy form is chosen because the source integral for a power-law
primary then has a closed form, an incomplete beta function, which benchmarks the profile's numerical integration.

**External benchmark (open question B2, 2026-10-15).** Table VI of di Mauro, Donato, Goudelis and Serpico, PRD 90
(2014) 085017 (arXiv:1408.0288v3) prints the pp-induced source term at T = 5, 10, 100, 500 and 1000 GeV.
`scripts/published_benchmark.py` recomputes it from the same paper's closed-form parametrizations (Eqs. (11)-(13)
with Tables III-V; inelastic cross section Eqs. (B1)-(B2), Table VII; `models/xs-dimauro2014-pp.json`), n_H = 1 cm^-3
and the proton flux of arXiv:1402.0321v2 Sec. 2.3 that the paper names. Tolerance per entry: the paper's own Table VI
error. 12 of 15 entries are reproduced (within 2.5% at 5 and 10 GeV, within 6.5% up to 500 GeV); Eq. (11) at
1000 GeV (+9.3% against 6.9%) and Eq. (13) at 500 and 1000 GeV (dependent on the unstated upper limit of the
projectile-energy integral) are documented, not reproduced, as are the spline, Tan & Ng and Duperray et al. columns
(no closed form in the paper, or an ambiguous parameter set). The proton-flux parameters are printed in running text,
not a table (claim `crpb:C09`). Benchmark file: `benchmarks/published-source-term-dimauro2014.json`.

`model.family` is `cosmic-ray-secondary-source-term`, not `cosmic-ray-propagation`: the validator's
`theory.degeneracy_missing` rule does not apply, and the theory-spec lists no degenerate directions. A source term is
not a propagation prediction and cannot drive a propagation-parameter fit.

This README is for people. The skills route through [index.md](index.md); the manifest is
[profile.json](profile.json).

## What it holds

- **Models** (`models/source-term-models.md`) and two toy cross-section sets (`models/xs-toy-*.json`), used as
  model alternatives.
- **Derivation** (`scripts/derive.py`, recorded in `derivations/`): SymPy checks of the closed form above and below
  threshold, of broken power laws by pieces, and of the antineutron/hyperon bookkeeping; `derivations/theory-spec.json`
  is the theory-spec artifact.
- **Prediction** (`scripts/predict.py`): q per channel and in total, channel fractions, switches for antineutrons and
  hyperons, bin averages; `predictions/source-term-benchmark.prediction.json` is the prediction artifact with two
  model-alternative objects (toy set B; antineutrons without isospin enhancement), written by
  `scripts/make_artifacts.py`.
- **Benchmark** (`predict.py --benchmark`, settings in `benchmarks/source-term-benchmark.json`): numerical quadrature
  against the closed form for every channel, for power-law and broken power-law primaries, on both sides of the
  threshold, plus a hand-computed point.
- **External benchmark** (`scripts/published_benchmark.py`, `benchmarks/published-source-term-dimauro2014.json`):
  the published pp source term (above).
- **References** (`evidence/`, namespace `crpb`): di Mauro et al. 2014 read in full (2026-10-15); the proton-flux
  paragraph of arXiv:1402.0321v2 read; Korsmeier et al. 2018 and Winkler 2017 opened for their tables and ancillary
  files only (no tabulated source term, claim `crpb:C11`).

## Using it

```bash
python3 scripts/derive.py
python3 scripts/predict.py                         # benchmark point, numerical integration
python3 scripts/predict.py --method closed-form
python3 scripts/predict.py --xs models/xs-toy-B.json
python3 scripts/predict.py --benchmark
python3 scripts/published_benchmark.py          # external benchmark, di Mauro et al. 2014 Table VI
python3 scripts/make_artifacts.py --check
```

## Tests

```bash
python3 -m unittest discover -s tests -t tests
```

`test_derivation.py` (SymPy), `test_missing_dependency.py`, `test_benchmark.py`, `test_published_benchmark.py`,
`test_prediction.py`,
`test_artifacts.py` (both artifacts validate; the theory-spec validates without `degenerate_directions`, while the same
spec relabelled as a propagation family fails) and `test_convention_mismatch.py`. Needs numpy, scipy and sympy.
