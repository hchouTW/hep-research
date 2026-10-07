# Synthetic collider profile: routing map

Profile `experiment:synthetic-collider` is **illustrative and synthetic**. It exists to show how a non-AMS experiment is added through profile resources, registry metadata and bindings only, and to drive mandatory Path B. Nothing here describes a real detector or result. Paths are relative to this folder.

| Request | Read |
|---|---|
| What is simulated, invented parameters, limitations | `modules/detector-model.md` |
| Rules for using this profile (labels, what not to claim) | `modules/working-rules.md` |
| Run configuration (sqrt(s), luminosity, shape, seeds) | `benchmarks/path-b.json` |
| Generate synthetic events | `scripts/generate_events.py --help` |
| Efficiency, smearing, analytic response | `scripts/detector.py` |
| Dataset record of the synthetic measurement | `datasets/` |

Conventions: `conventions.json`. Evidence ledger: `evidence/` is empty by design (there is no real source to cite).
