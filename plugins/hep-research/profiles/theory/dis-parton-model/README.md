# DIS parton-model profile

Profile `theory:dis-parton-model`, version 0.1.0. It holds LO quark-parton-model F_2 for photon exchange (PDG
Eq. 18.18) and the O(alpha_s) longitudinal structure function F_L. F_L is built from the LO coefficient functions of
Moch, Vermaseren and Vogt (Eqs. 1-3) and rewritten in SymPy into the Altarelli-Martinelli form
F_L = (alpha_s/(4 pi)) x^2 int_x^1 dz/z^3 [ (16/3) F_2(z) + 8 sum e_q^2 (1 - x/z) z g(z) ]. The profile needs no
experiment profile and holds no detector, data or blinding content.

**Synthetic only.** No published F_L number was read for this profile. Every capability therefore has status
`demonstrated-on-synthetic-data`. The numerical benchmark is an analytic closed form on invented toy densities
(`benchmarks/toy-closed-form.json`), not a published value. Do not compare the outputs with data.

Validity: photon exchange, massless quarks, leading twist (Q^2 well above the nucleon mass squared), mu_R = mu_F = Q,
and F_L at its leading order only. Excluded: higher orders, evolution, PDF sets, heavy-quark mass effects, target-mass
and higher-twist terms, Z/W exchange, and polarized structure functions.

This README is for people. The skills route through [index.md](index.md); the manifest is
[profile.json](profile.json).

## What it holds

- **Model** (`models/dis-parton-model.md`): assumptions, validity domain, and what each output can claim.
- **Derivation** (`scripts/derive.py`, recorded in `derivations/`): the change of variables, the flavour algebra and
  the Altarelli-Martinelli identity in SymPy. It also has a toy closed form against quadrature, with a convergence
  study.
- **Prediction** (`scripts/predict.py`, artifacts written by `scripts/make_artifacts.py`): F_2 and F_L on a toy
  (x, Q^2) grid, plus `derivations/theory-spec.json` and `predictions/fl-toy-grid.prediction.json`. Both are labelled
  `synthetic`.
- **References** (`evidence/`, namespace `dispm`).

## Using it

```bash
python3 scripts/derive.py              # needs SymPy (find it with skills/hep-computing/scripts/find_python.py)
python3 scripts/predict.py --config benchmarks/toy-closed-form.json
python3 scripts/make_artifacts.py --check
```

## Tests

```bash
python3 -m unittest discover -s tests -t tests
```

The suite has `test_derivation.py` (SymPy), `test_prediction.py`, `test_artifacts.py` (contracts/validate.py on both
artifacts), `test_convention_mismatch.py` and `test_missing_dependency.py`. It needs numpy, scipy and sympy.
