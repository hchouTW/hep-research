# Geometry reference cases (reference profile)

Detector-specs reconstructed from cited claims, each "an approximate reconstruction from the cited claims, not the experiment's geometry" (g4sim plan, Section 13). The profile holds no claims: every value of a case's `detector-spec.json` names, in `source_of_facts`, a claim of `reference:detector-atlas`, `experiment:ams-02` or `experiment:eic`, which `contracts/geometry.py --claims` resolves.

| Case | Level | Quantities | Status |
|---|---|---|---|
| `cms-ecal-barrel-crystal` | L1 | x/X0 along one barrel crystal | see `case.json` |
| `ams02-tof` | L1 | x/X0 of one half; number of counters | see `case.json` |
| `epic-zdc-hadronic` | L2 | x/X0 of the steel; readout cells | see `case.json` |

Each `case.json` gives the level, the cited claims, each quantity's reference value with its derivation and sources, the result of verifying that the reference does not come from Geant4, the tolerance (copied from `docs/dev/geant4-architecture/g4sim-tasks/S6.md`), the negative control and detection limit, the declared approximations, and the last result. A comparison with cited values is validation, not confirmation. `coverage.json` lists the modules the cases use.

Run: `adapters/geant4/tests/g4proto/s6_gates/cases_gate.py --program PATH --work DIR [--write]`, in an activated Geant4 environment.
