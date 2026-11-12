# EIC profile

Profile `experiment:eic`, version 0.6.1. It adds Electron-Ion Collider facility context and ePIC experiment context
to the core skills (`hep-measurement`, `hep-detector`, `hep-theory`, `hep-computing`), from public documents only.
It is never an entry point. Not endorsed by the EIC project, BNL, Jefferson Lab or the ePIC Collaboration.

This README is for people. The skills route through [index.md](index.md); read
[modules/working-rules.md](modules/working-rules.md) before relying on any statement; the manifest is
[profile.json](profile.json).

**EIC is the facility; ePIC is the first experiment at it.** A fact about ePIC is not a fact about every EIC
experiment, and every number here is a design target, a requirement, a design value (an ePIC construction
parameter) or a proposed run plan, never a measured value.

## What it holds

- **Facility context** (`modules/facility/`): an overview, the beam configurations (species, energies,
  polarization, luminosity, derived center-of-mass energies, the spec field format) and the interaction region, from
  the CDR, the Yellow Report and the project requirements pages.
- **Detector context** (`modules/detector/`): the ePIC overview and subsystem map; tracking, particle
  identification, calorimetry, far-forward and far-backward, readout and data acquisition, and early-running
  proposals; software and data-format entry points (eic-shell, EICrecon, the epic geometry, EDM4hep/EDM4eic) with no
  release pinned.
- **Configuration checker** (`scripts/check_eic_conventions.py`): checks the EIC-specific parts of a
  measurement-spec or theory-spec; `scripts/number_rules.py` holds the per-number rule shared with the tests.
- **Placement inventory** (`modules/placement-inventory.md`): what is general method, what is EIC, what is ePIC and
  what belongs to your project.
- **Evidence ledger** (`evidence/`, ids `eic:S01`, `eic:C01`): every factual bullet in the modules cites a claim,
  and every number in a module appears in a cited numeric claim. `evidence/index.md` is generated. Numeric claims
  carry atlas blocks, so the hep-detector atlas returns them for a project bound to this profile.
- **Routing scenarios** (`benchmarks/routing-scenarios.json`) used by the tests.

It holds no performance numbers, no datasets (`datasets/README.md` explains why), no
calibration constants and no runnable experiment software. ePIC internal documents, cuts and samples belong in your
project or a local profile, and reach the agent only under a project `agent_policy` that allows them on a qualified host
configuration (none is qualified yet).

## Layout

| Path | Contents |
|---|---|
| `index.md` | routing map: request type to file |
| `profile.json` | id, version, scope, exclusions, resources, capabilities and their tests |
| `conventions.json` | asymmetric beams, lab is not CM, per-nucleon ion energies, beam-direction and polarization signs |
| `modules/` | working rules, placement inventory, facility, detector and source-policy modules |
| `evidence/` | `sources.json`, `claims.json`, generated `index.md` |
| `datasets/` | none yet |
| `benchmarks/` | routing scenarios |
| `scripts/` | `check_eic_conventions.py` (configuration checker), `number_rules.py` (per-number rule) |
| `tests/` | ledger, metadata, routing, scope and placement, and checker tests (`fixtures/`) |

## Using it

Name the EIC or ePIC in a request, or pin the profile in `hep-research.project.json` at your project root:

```json
{"schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0",
 "experiments": [{"profile": "experiment:eic", "version": "0.6.1"}]}
```

Check a spec's EIC fields with
`python3 profiles/experiments/eic/scripts/check_eic_conventions.py SPEC.json [--profiles-from hep-research.project.json]`
from the plugin root. Generic DIS kinematics and QCD go to `hep-theory` with no experiment profile. Detector performance is not shipped:
the skill says so and asks which detector concept, geometry release and whether a projection or a measurement is
meant.

## Tests

```bash
python3 -m unittest discover -s tests -t tests    # from this folder
```

The tests are static and need only the standard library and the plugin's `core` and `contracts`. They check
structure, citations and routing, not the truth of any claim.
