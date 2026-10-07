# QED benchmark profile

Profile `theory:qed-benchmark`, version 1.0.0. A small, fully checked theory domain: tree-level e+e- -> mu+mu-
through one s-channel photon, with point-like fermions, unpolarized beams and alpha = e^2/(4 pi). It needs no
experiment profile and holds no detector, data or blinding content.

Validity: sqrt(s) well above the muon mass and well below the Z mass. Excluded: Z exchange and gamma-Z interference,
QED radiative corrections, running of alpha, beam polarization.

It drives Path C (`examples/qed-benchmark`) and, with the synthetic collider, is the template for writing a new
profile (see `docs/profile-authoring.md` at the plugin root).

This README is for people. The skills route through [index.md](index.md); the manifest is
[profile.json](profile.json).

## What it holds

- **Model** (`models/tree-level-photon-exchange.md`): assumptions, validity domain, exclusions.
- **Derivation** (`scripts/derive.py`, recorded in `derivations/`): the spin-averaged squared amplitude,
  d sigma / d Omega, d sigma / d cos theta and sigma(beta) derived with SymPy from explicit Dirac matrices, and
  compared with PDG eqs. 51.2 and 51.3. This is an analytic derivation checked with SymPy, not a formal proof.
- **Predictions** (`scripts/predict.py`, stored in `predictions/`): bin-averaged d sigma / d cos theta and integrated
  cross sections at a given sqrt(s), with an integration convergence study.
- **Benchmark settings** (`benchmarks/path-c.json`) and the reference read (`evidence/`, namespace `qedbench`).

## Layout

| Path | Contents |
|---|---|
| `index.md` | routing map: request type to file |
| `profile.json` | id, version, scope, exclusions, resources, capabilities and their tests |
| `conventions.json` | units, metric, coupling and reference-constant conventions |
| `models/` | model definition |
| `derivations/` | derivation record (`.md`) and its machine-readable form (`.json`) |
| `predictions/` | stored prediction at sqrt(s) = 10 GeV |
| `scripts/` | `derive.py`, `predict.py` |
| `benchmarks/` | Path C settings |
| `evidence/` | sources and claims |
| `tests/` | derivation, prediction and convention-mismatch tests |

## Using it

```bash
python3 scripts/derive.py
python3 scripts/predict.py --sqrt-s 10
```

Or pin it in `hep-research.project.json` at your project root:

```json
{"schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0",
 "theory": [{"profile": "theory:qed-benchmark", "version": "1.0.0"}]}
```

Never present the derivation as a formal proof, or numerical agreement as proof.

## Tests

```bash
python3 -m unittest discover -s tests -t tests    # from this folder; needs NumPy, SciPy, SymPy
```
