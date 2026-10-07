# QED benchmark profile: routing map

Profile `theory:qed-benchmark` is a small, fully checked theory domain: tree-level e+e- -> mu+mu- through one s-channel photon. It needs no experiment profile. Paths are relative to this folder.

| Request | Read |
|---|---|
| Model, assumptions, validity domain, what is excluded | `models/tree-level-photon-exchange.md` |
| How the formulas were derived and checked; derivation status | `derivations/derivation-record.md` (run `scripts/derive.py`) |
| Numerical predictions at a given sqrt(s); integration tolerance study | `scripts/predict.py --help`; stored outputs in `predictions/` |
| Reference read and what it states | `evidence/sources.json`, `evidence/claims.json` |
| Benchmark settings | `benchmarks/path-c.json` |

Conventions: `conventions.json`. Never present the derivation as a formal proof, and never present numerical agreement as proof.
