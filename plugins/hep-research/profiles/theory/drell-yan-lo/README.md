# Drell-Yan LO profile

Profile `theory:drell-yan-lo`, version 0.1.0. It covers two things, and needs no experiment profile (it holds no
detector, data or blinding content):

- **LO Drell-Yan cross section.** d2sigma/dM dy = (8 pi alpha^2/(9 M s)) sum e_q^2 [q1 qbar2 + qbar1 q2] for photon
  exchange, derived from PDG Eqs. 51.3 and 51.40.
- **Lepton angular coefficients at O(alpha_s).** lambda and nu in the quark-axis picture of Peng, Chang, McClellan
  and Teryaev (arXiv:1511.08932v3, Eqs. 1-10), with the Lam-Tung relation 1 - lambda - 2 nu = 0.

**Benchmark status.** The angular coefficients are checked against a published closed form that was read (Peng et
al. Eq. 10), and their capabilities have status `tested-in-declared-environment`. That benchmark follows the same
route as the profile: it checks algebra and transcription, not the physics of the q g input (Eq. 9, an approximation).
The LO cross section is checked only on synthetic toy densities (`demonstrated-on-synthetic-data`). No published
cross-section number was read.

**Validity.** Photon exchange, massless partons, LO cross section, angular coefficients at O(alpha_s) with a coplanar
quark axis.

**Excluded.** Z exchange, NLO, qT resummation, intrinsic transverse momentum and TMD effects, Lam-Tung violation
beyond O(alpha_s), and any comparison with data.

This README is for people. The skills route through [index.md](index.md); the manifest is
[profile.json](profile.json).

## What it holds

- **Model** (`models/drell-yan-lo.md`): assumptions, validity domain, and what each output can claim.
- **Derivation** (`scripts/derive.py`, recorded in `derivations/`): the LO cross section, Eq. 5 from Eqs. 2 and 4,
  A_0..A_7 and lambda, mu, nu, Lam-Tung, and Eq. 10, all in SymPy.
- **Prediction** (`scripts/predict.py`, artifacts written by `scripts/make_artifacts.py`): lambda, nu and
  1 - lambda - 2 nu versus qT/Q for both channels and for q g fractions 0 to 1, plus the published-benchmark comparison
  and the numerical Jacobian check. Artifacts: `derivations/theory-spec.json` and
  `predictions/angular-coefficients.prediction.json`.
- **References** (`evidence/`, namespace `dylo`).

## Using it

```bash
python3 scripts/derive.py              # needs SymPy (find it with skills/hep-computing/scripts/find_python.py)
python3 scripts/predict.py --config benchmarks/angular-grid.json
python3 scripts/make_artifacts.py --check
```

## Tests

```bash
python3 -m unittest discover -s tests -t tests
```

The suite has `test_derivation.py` (SymPy), `test_benchmark.py` (Peng Eq. 10), `test_prediction.py`,
`test_artifacts.py` (contracts/validate.py on both artifacts), `test_convention_mismatch.py` and
`test_missing_dependency.py`. It needs numpy, scipy and sympy.
