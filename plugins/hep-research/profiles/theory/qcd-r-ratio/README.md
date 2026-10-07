# QCD R-ratio profile

Profile `theory:qcd-r-ratio`, version 1.0.0. The second theory domain after `theory:qed-benchmark`, and the first
beyond tree level: R = sigma(e+e- -> hadrons) / sigma(e+e- -> mu+mu-) with massless QCD corrections through
alpha_s^4, as given in the PDG QCD review (eqs. 9.7-9.9), its renormalization-scale dependence derived from the RGE
(eq. 9.3), and alpha_s(m_Z) from PDG Table 1.1. It needs no experiment profile and holds no detector, data or
blinding content.

Validity: photon exchange only, five massless quarks, Q well above the b threshold and well below m_Z (the code
refuses scales below 5 GeV and Q above m_Z/3). Excluded: Z exchange, quark masses, QED corrections, flavour matching,
non-perturbative corrections, and any comparison with measured R.

This README is for people. The skills route through [index.md](index.md); the manifest is
[profile.json](profile.json).

## What it holds

- **Model** (`models/massless-r-ratio.md`): assumptions, validity domain, and what each uncertainty object can claim.
- **Derivation** (`scripts/derive.py`, recorded in `derivations/`): the scale-dependent coefficients d_n(L) from the
  coefficients at mu = Q and the beta function, with exact-arithmetic checks.
- **Prediction** (`scripts/predict.py`, stored in `predictions/r_15gev.json`): R(15 GeV) at each order with the
  scale envelope, a truncation estimate and the alpha_s(m_Z) variation, reported separately.
- **References** (`evidence/`, namespace `qcdr`).

## Using it

```bash
python3 scripts/derive.py
python3 scripts/predict.py --config benchmarks/r-ratio-15gev.json
```

Or pin it in `hep-research.project.json` (`"profiles": ["theory:qcd-r-ratio"]`).

## Tests

```bash
python3 -m unittest discover -s tests -t tests
```

`test_derivation.py` (SymPy, about 15 s), `test_prediction.py` and `test_convention_mismatch.py` (each
convention variant is rejected with its field). Needs numpy, scipy and sympy.
