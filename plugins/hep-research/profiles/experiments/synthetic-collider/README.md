# Synthetic collider profile

Profile `experiment:synthetic-collider`, version 1.0.0. **Illustrative and synthetic**: an invented e+e- collider
detector at fixed sqrt(s). Its event generator, efficiency, resolution and luminosity describe no real experiment,
and nothing here is a physics result.

It exists for two reasons: to show that a non-AMS experiment plugs in through profile resources, registry metadata
and bindings alone, and to drive Path B (the corrected angular distribution in `examples/collider-angular`) and the
detector-resolution example. Together with the QED benchmark it is the template for writing a new profile (see
`docs/profile-authoring.md` at the plugin root).

This README is for people. The skills route through [index.md](index.md); the manifest is
[profile.json](profile.json).

## What it holds

- **Detector model** (`modules/detector-model.md`): the invented parameters and their limitations.
- **Working rules** (`modules/working-rules.md`): labels to keep and what not to claim.
- **Generator** (`scripts/generate_events.py`): seeded synthetic e+e- -> mu+mu- angular events with a
  `1 + a cos^2 + b cos` shape. It imports no theory code.
- **Detector** (`scripts/detector.py`): invented efficiency, Gaussian cos theta smearing and an analytic response
  matrix that includes the efficiency.
- **Run configuration** (`benchmarks/path-b.json`): sqrt(s) = 10 GeV, luminosity, shape, efficiency, resolution,
  binning, seed and toy count.
- **Dataset record** (`datasets/synthetic-path-b-dsigma.json`) of the synthetic measurement.
- **Evidence ledger** (`evidence/`): empty by design, since there is no real source to cite.

## Layout

| Path | Contents |
|---|---|
| `index.md` | routing map: request type to file |
| `profile.json` | id, version, scope, exclusions, resources, capabilities and their tests |
| `conventions.json` | fiducial and luminosity definitions |
| `modules/` | detector model, working rules |
| `scripts/` | generator and detector model |
| `benchmarks/` | Path B run configuration |
| `datasets/` | synthetic dataset record |
| `evidence/` | empty sources and claims |
| `tests/` | generator and detector tests |

## Using it

```bash
python3 scripts/generate_events.py --help
python3 scripts/generate_events.py --config benchmarks/path-b.json --summary
```

Or pin it in `hep-research.project.json` at your project root:

```json
{"schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0",
 "experiments": [{"profile": "experiment:synthetic-collider", "version": "1.0.0"}]}
```

Keep the SYNTHETIC label on every output made from this profile.

## Tests

```bash
python3 -m unittest discover -s tests -t tests    # from this folder; needs NumPy
```

The end-to-end Path B and detector-resolution tests live in the plugin's `tests/examples/`.
