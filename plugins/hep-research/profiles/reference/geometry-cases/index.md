# Geometry reference cases (reference profile)

Detector-specs reconstructed from cited claims, each "an approximate reconstruction from the cited claims, not the experiment's geometry" (g4sim plan, Section 13). The profile holds no claims: every value of a case's `detector-spec.json` names, in `source_of_facts`, a claim of `reference:detector-atlas`, `experiment:ams-02` or `experiment:eic`, which `contracts/geometry.py --claims` resolves.

| Case | Level | Quantities | Status |
|---|---|---|---|
| `cms-ecal-barrel-crystal` | L1 | x/X0 along one barrel crystal | see `case.json` |
| `ams02-tof` | L1 | x/X0 of one half; number of counters | see `case.json` |
| `epic-zdc-hadronic` | L2 | x/X0 of the steel; readout cells | see `case.json` |
| `ams02-ecal` | L1 | depth_x0 | see `case.json` |
| `ams02-rich` | L3 | aerogel_tiles; naf_tiles; aerogel_cherenkov_angle; naf_cherenkov_angle | see `case.json` |
| `ams02-tracker-magnet` | L1 | silicon_layers; layer_silicon_x0; bore_field_integral | see `case.json` |
| `ams02-trd` | L1 | straw_layers; layer_radiator_x0 | see `case.json` |
| `cms-ecal-barrel-crystal-optics` | L3 | cherenkov_angle | see `case.json` |
| `cms-ecal-barrel-supermodule` | L2 | crystals | see `case.json` |
| `cms-endcap-csc` | L2 | chambers; gas_gaps | see `case.json` |
| `cms-phase1-bpix` | L2 | modules; sensor_x0 | see `case.json` |
| `epic-drich` | L3 | sectors; aerogel_cherenkov_angle | see `case.json` |
| `epic-hpdirc` | L1 | bar_boxes; bar_pieces; bar_x0 | see `case.json` |
| `epic-tof` | L1 | staves; sensor_x0 | see `case.json` |
| `lhcb-rich-radiators` | L3 | cherenkov_angle_c4f10; cherenkov_angle_cf4 | see `case.json` |
| `lhcb-scifi` | L2 | modules; cfrp_x0 | see `case.json` |
| `ams02-rich-replica` | L3 | aerogel_photons_at_plane (synthetic: a comparison with the task package's replica, never validation) | see `case.json` |

Each `case.json` gives the level, the cited claims, each quantity's reference value with its derivation and sources, the result of verifying that the reference does not come from Geant4, the tolerance (copied from the task card of its phase, `g4sim-tasks/S6.md` or `S7.md`), the negative control and detection limit, the declared approximations, and the last result. A comparison with cited values is validation, not confirmation. `coverage.json` lists the modules the cases use.

Run: `adapters/geant4/tests/g4proto/s6_gates/cases_gate.py --program PATH --work DIR [--write]` for S6's cases and `adapters/geant4/tests/g4proto/s7_gates/cases_gate.py --program PATH --work DIR [--case NAME] [--write]` for S7's (each S7 quantity names its measure and its negative control), in an activated Geant4 environment.
