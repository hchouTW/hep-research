# DIS parton-model profile: routing map

Profile `theory:dis-parton-model` covers LO quark-parton-model F_2 (photon exchange) and the O(alpha_s) longitudinal
structure function F_L in the Altarelli-Martinelli form. It needs no experiment profile. Paths are relative to this
folder.

**Synthetic only:** no published F_L value was read. Every capability has status `demonstrated-on-synthetic-data`, and
the benchmark is an analytic closed form on invented toy densities, not a published number. Never present its output
as a physical F_L, and never compare it with data.

| Request | Read |
|---|---|
| Model, assumptions, validity domain, what the outputs can claim | `models/dis-parton-model.md` |
| Derivation of the Altarelli-Martinelli form, status, checks, versions | `derivations/derivation-record.md` (run `scripts/derive.py`) |
| F_2 and F_L at (x, Q^2) for given densities and alpha_s | `scripts/predict.py --help`; stored output `predictions/fl-toy-grid.prediction.json` |
| Theory spec (contract artifact) | `derivations/theory-spec.json` (written by `scripts/make_artifacts.py`) |
| References read and what they state | `evidence/sources.json`, `evidence/claims.json` |
| Analytic closed-form check settings (toy inputs) | `benchmarks/toy-closed-form.json` |

Conventions are in `conventions.json`: expansion in alpha_s/(4 pi), mu_R = mu_F = Q, number densities, photon exchange
only, zero-mass flavours, target mass neglected. Out of scope (say so): NLO/NNLO F_L, PDF sets or evolution,
heavy-quark schemes beyond zero-mass, Z/W exchange, and polarized structure functions.
