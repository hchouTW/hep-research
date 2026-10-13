# Higgs to b bbar width profile: routing map

Profile `theory:higgs-bb-width`: Gamma(H -> b bbar) with the MS-bar running b mass and alpha_s, massless b at leading
power, QCD corrections through alpha_s^4. The first theory domain with a running mass (scheme conversion and running:
`skills/hep-theory/references/regularization-and-schemes.md`). It needs no experiment profile. Paths are relative to
this folder.

| Request | Read |
|---|---|
| Model, assumptions, validity domain, what each uncertainty object can claim | `models/running-mass-hbb.md` |
| Scale dependence of coupling and mass, derivation status and checks | `derivations/derivation-record.md` (run `scripts/derive.py`) |
| The width by order, scale envelope, truncation, alpha_s and m_b variations | `scripts/predict.py --help`; stored output `predictions/hbb_125.json` |
| References read and what they state | `evidence/sources.json`, `evidence/claims.json` |
| Benchmark settings | `benchmarks/hbb-125.json` |

Conventions: `conventions.json`. A scale envelope is a prescription, not a confidence interval: never turn it into a
Gaussian. The prediction is not a measured width; top-induced, electroweak and m_b^2/M_H^2 terms are excluded.
