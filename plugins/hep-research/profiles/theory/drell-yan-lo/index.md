# Drell-Yan LO profile: routing map

Profile `theory:drell-yan-lo` covers the LO Drell-Yan cross section d2sigma/dM dy (photon exchange) and the lepton
angular coefficients lambda and nu at O(alpha_s), including the Lam-Tung relation. It needs no experiment profile.
Paths are relative to this folder.

| Request | Read |
|---|---|
| Model, assumptions, validity domain, what each output can claim | `models/drell-yan-lo.md` |
| Derivations (LO cross section, Eqs. 5-7, Lam-Tung, Eq. 10), status, checks, versions | `derivations/derivation-record.md` (run `scripts/derive.py`) |
| lambda, nu, 1 - lambda - 2 nu versus qT/Q, per channel or mixture | `scripts/predict.py --help`; stored output `predictions/angular-coefficients.prediction.json` |
| Theory spec (contract artifact) | `derivations/theory-spec.json` (written by `scripts/make_artifacts.py`) |
| Published closed-form benchmark (Peng et al. Eq. 10) | `benchmarks/peng-eq10.json` |
| Toy inputs of the numerical Jacobian check (SYNTHETIC) | `benchmarks/toy-lo-cross-section.json` |
| References read and what they state | `evidence/sources.json`, `evidence/claims.json` |

Conventions are in `conventions.json`: Collins-Soper frame, negative-lepton angles, nu/2 in front of
sin^2 theta cos 2phi, photon exchange only, and rapidity in the hadronic c.m. frame with +z along hadron 1.

Keep these limits in view:
- The q g input (Eq. 9) is an approximation.
- The Lam-Tung relation is established here only at O(alpha_s), with coplanarity cited rather than derived.
- The q g fraction of a mixture is a parameter, never a fitted value.

Comparisons with data go through hep-statistics. Out of scope (say so): Z exchange, NLO, resummation and TMD effects.
