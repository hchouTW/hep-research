# Higgs to b bbar width profile

Profile `theory:higgs-bb-width`, version 0.1.0. The third theory domain and the first with a running mass:
Gamma(H -> b bbar) = 3 G_F M_H / (4 sqrt 2 pi) mbar_b(mu)^2 R, with R through alpha_s^4 in the MS-bar scheme
(s_1..s_3 exact from Chetyrkin, hep-ph/9608318, s_4 at n_f = 5 from Baikov, Chetyrkin and Kuhn, hep-ph/0511063), the
running of alpha_s and of mbar_b at four loops, and PDG 2026 inputs. It needs no experiment profile and holds no
detector, data or blinding content.

Validity: n_f = 5 massless quarks at leading power, mu in [M_H/2, 2 M_H]. Excluded: m_b^2/M_H^2 power corrections,
top-induced and electroweak corrections, flavour-threshold matching, and any comparison with a measured width.

This README is for people. The skills route through [index.md](index.md); the manifest is
[profile.json](profile.json).

## What it holds

- **Model** (`models/running-mass-hbb.md`): assumptions, validity domain, what each uncertainty object can claim.
- **Derivation** (`scripts/derive.py`, recorded in `derivations/`): the scale-dependent coefficients r_n(L) from
  s_1..s_4 and the RGEs of mass and coupling, with exact-arithmetic checks of mu-independence.
- **Prediction** (`scripts/predict.py`, stored in `predictions/hbb_125.json`): the width at each order with the
  scale envelope, a truncation estimate and the alpha_s(m_Z) and mbar_b(mbar_b) variations, reported separately.
- **References** (`evidence/`, namespace `hbb`).

## Using it

```bash
python3 scripts/derive.py
python3 scripts/predict.py --config benchmarks/hbb-125.json
```

Or pin it in `hep-research.project.json` (`"profiles": ["theory:higgs-bb-width"]`).

## Tests

```bash
python3 -m unittest discover -s tests -t tests
```

`test_derivation.py` (SymPy, about 10 s), `test_prediction.py` (scipy), `test_convention_mismatch.py` and
`test_missing_dependency.py`. Needs scipy and sympy; without them the affected tests skip with a reason.
