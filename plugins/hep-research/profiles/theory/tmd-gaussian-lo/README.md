# Gaussian TMD profile

Profile `theory:tmd-gaussian-lo`, version 0.1.0. It needs no experiment profile and holds no detector, data or
blinding content.

It covers Gaussian-ansatz transverse-momentum-dependent distributions and fragmentation functions at leading order,
without evolution:
- SIDIS F_UU,T(x, z, P_hT) in the conventions of both Anselmino et al. (hep-ph/0501196v2) and Bacchetta et al.
  (hep-ph/0611265v2).
- The Cahn cos(phi_h) term.
- The Sivers asymmetry A_UT^sin(phi_h - phi_S).
- The Drell-Yan q_T shape.
- The change of sign of the Sivers function between SIDIS and Drell-Yan (Trento conventions, hep-ph/0410050v2,
  Eq. 14).

**Status.**
- The physics status is `heuristic-argument`, because the Gaussian ansatz with constant widths is a model. Each
  derivation step is exact within it.
- `tested-in-declared-environment`: the SIDIS F_UU,T / Cahn capability and the Sivers-asymmetry capability. Both are
  checked against a published closed form (Anselmino et al. Eqs. 38-39 and 64-67) by numerical quadrature of the
  profile's transcription of the same paper's integrands. That follows the same route as the paper, so it checks
  algebra and transcription, not physics. The comparison with `skills/hep-theory/scripts/tmd_gaussian.py` is a
  consistency check: the script is by the same author, so it is not independent.
- `demonstrated-on-synthetic-data`: the Drell-Yan q_T shape (derived here, no source formula) and the Sivers sign
  change (cited and applied).
- The collinear inputs and Sivers normalizations are synthetic. The paper's fitted widths are used only as
  illustrative settings.

**Validity.** Small P_hT, well below Q. Corrections of O(k_perp^2/Q^2) are dropped. The widths are constant and
flavour independent.

**Excluded.** TMD evolution, fits, Collins and Boer-Mulders effects, a Drell-Yan Sivers asymmetry formula, and any
comparison with data.

This README is for people. The skills route through [index.md](index.md); the manifest is
[profile.json](profile.json).

## What it holds

- **Model** (`models/tmd-gaussian-lo.md`).
- **Derivation** (`scripts/derive.py`, recorded in `derivations/`).
- **Predictions** (`scripts/predict.py`; artifacts written by `scripts/make_artifacts.py`):
  `predictions/sidis-fuut.prediction.json`, `predictions/sivers-asymmetry.prediction.json` (which includes the
  Sivers function in SIDIS and Drell-Yan), and `predictions/dy-qt-shape.prediction.json`.
- **Benchmarks** (`benchmarks/`): the published closed forms and the inputs.
- **References** (`evidence/`, namespace `tmdg`).

## Using it

```bash
python3 scripts/derive.py              # needs SymPy (find it with skills/hep-computing/scripts/find_python.py); ~50 s
python3 scripts/predict.py --config benchmarks/toy-inputs.json
python3 scripts/make_artifacts.py --check
```

## Tests

```bash
python3 -m unittest discover -s tests -t tests
```

The suite has `test_derivation.py` (SymPy, about 1 min), `test_benchmark.py`, `test_prediction.py` (which includes
the consistency check against `skills/hep-theory/scripts/tmd_gaussian.py`), `test_artifacts.py`, `test_convention_mismatch.py`
and `test_missing_dependency.py`. It needs numpy, scipy and sympy.
