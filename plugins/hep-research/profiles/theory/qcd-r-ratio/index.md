# QCD R-ratio profile: routing map

Profile `theory:qcd-r-ratio`: R(e+e- -> hadrons) with massless QCD corrections through alpha_s^4, the second theory
domain after `theory:qed-benchmark`. It needs no experiment profile. Paths are relative to this folder.

| Request | Read |
|---|---|
| Model, assumptions, validity domain, what each uncertainty object can claim | `models/massless-r-ratio.md` |
| Scale dependence of the coefficients, derivation status and checks | `derivations/derivation-record.md` (run `scripts/derive.py`) |
| R at a given Q by order, scale envelope, truncation, alpha_s variation | `scripts/predict.py --help`; stored output `predictions/r_15gev.json` |
| References read and what they state | `evidence/sources.json`, `evidence/claims.json` |
| Benchmark settings | `benchmarks/r-ratio-15gev.json` |

Conventions: `conventions.json`. A scale envelope is a prescription, not a confidence interval: never turn it into a
Gaussian, and never present the prediction as measured R.
