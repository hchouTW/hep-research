# EIC profile: routing map

Profile `experiment:eic` adds Electron-Ion Collider (EIC) facility context and ePIC experiment context to the core skills; it is never an entry point. Public documents only. **EIC is the facility; ePIC is the first experiment at it.** A fact about ePIC is not a fact about every possible EIC experiment, and a facility design target is not a measured value. Read [working rules](modules/working-rules.md) first. Paths are relative to this folder.

| Request | Read |
|---|---|
| Beam species and polarization overview, project stage, where EIC design values live (EIC facility) | `modules/facility/eic-facility-context.md` |
| Beam configurations: species, beam energies, polarization, luminosity, derived center-of-mass energies, spec field format (EIC facility) | `modules/facility/beam-configurations.md` |
| Crossing angle, crab crossing, space around the interaction point (EIC facility) | `modules/facility/interaction-region.md` |
| ePIC detector concept: magnet, tracking, calorimetry, PID, far-forward/backward, data acquisition | `modules/detector/epic-detector-context.md` |
| ePIC tracking subsystems: silicon vertex tracker, MPGDs, tracking volume | `modules/detector/epic-tracking.md` |
| ePIC particle identification detectors: pfRICH, hpDIRC, dRICH, time of flight | `modules/detector/epic-pid.md` |
| ePIC calorimeters, electromagnetic and hadronic, by region | `modules/detector/epic-calorimetry.md` |
| ePIC far-forward and far-backward: B0, Roman pots, ZDC, luminosity monitor, low-Q2 tagger | `modules/detector/epic-far-forward-backward.md` |
| ePIC readout and data acquisition: streaming readout, front-end ASICs | `modules/detector/epic-readout-and-daq.md` |
| ePIC early running: proposed configurations (not facility values) | `modules/detector/epic-early-running.md` |
| ePIC software and data formats: eic-shell, EICrecon, epic geometry, EDM4hep/EDM4eic | `modules/detector/epic-software-entry-points.md` |
| What is general method, what is EIC, what is ePIC, what belongs to the project | `modules/placement-inventory.md` |
| Which sources count, how to quote them, "latest" | `modules/sources/source-policy.md`, then `evidence/index.md` |
| Detector performance (resolution, efficiency, PID separation) | not shipped: say so, then ask for the detector concept, geometry release and whether a projection or a measurement is meant (`modules/working-rules.md`) |
| Generic DIS kinematics, QCD, cross sections | not this profile: `hep-theory` with no experiment profile |
| Selection, backgrounds, corrections, systematics for an EIC measurement | `hep-measurement` general method plus the facility module for configuration facts; cuts and samples come from the project |

Conventions: `conventions.json` (asymmetric beams, lab is not CM, per-nucleon ion energies, beam-direction and polarization signs unknown until a release or analysis states them). Evidence: `evidence/sources.json`, `evidence/claims.json` (ids `eic:S01`, `eic:C01`; modules cite the same full form), `evidence/index.md` (generated). Datasets: none (`datasets/README.md`). Routing scenarios used by the tests: `benchmarks/routing-scenarios.json`.
