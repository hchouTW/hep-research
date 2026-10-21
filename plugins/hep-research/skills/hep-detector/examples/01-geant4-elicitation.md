---
role: Principal Detector Physicist
skill: hep-detector
archetype: elicitation
user_request: simulate a silicon detector with Geant4 for me
---

Illustrative example: the dialogue is constructed, the detector is generic and names no experiment. The protocol it
follows is [the Geant4 study protocol](../references/geant4-study-protocol.md); the tools named here are real.

## 1. Raw Ambiguous Input

"Simulate a silicon detector with Geant4 for me."

Nothing is run yet. Geant4 would accept almost any geometry and physics list and finish without an error, so a run
started now would produce numbers that cannot be checked against anything.

## 2. Missing Constraint Analysis

The request leaves open every field of a study spec that decides whether the result can be reviewed:

- **Observable**: an energy deposit, the most probable energy loss, a hit efficiency, a cluster size? Each needs a
  different definition and a different reference.
- **Particle and energy**: the physics settings and the applicable benchmarks change with them (the Bethe benchmark
  holds only for 0.1 <~ beta gamma <~ 1000; the Landau most-probable-value benchmark needs kappa < 0.05).
- **Geometry and material source**: a design value, a published description, or the user's drawing? The reference
  inputs (density, mean excitation energy, density-effect parameters) must come from an independent source, never from
  the Geant4 material dump.
- **Precision target and downstream use**: a 1 % statistical target on a most probable value needs a different event
  count from a rough deposit estimate; a response matrix for unfolding needs a different handoff from a report.

No experiment is chosen on the user's behalf: if the silicon belongs to a named detector, its profile or the user
supplies the layout.

## 3. Socratic Clarification Round

1. Which observable should the study deliver?
   a) The most probable energy loss in one sensor layer
   b) The mean energy deposit and its tail fraction
   c) The full deposit distribution for a response matrix
   d) Something else (please describe it)
2. Which particle and kinetic energy?
   a) Minimum-ionizing muons around 10 GeV
   b) Protons of tens to hundreds of MeV
   c) Electrons below 10 MeV
   d) A spectrum (please give it)
3. Where do the geometry and materials come from?
   a) A single slab of given thickness in vacuum (design study)
   b) A published layer description (give the reference)
   c) A drawing or table you supply
4. What precision and downstream use?
   a) 1 % relative statistical error, a report with independent-reference benchmarks
   b) A response matrix handed to hep-statistics
   c) A quick feasibility number, explicitly unvalidated

## 4. User Feedback Integration

The user answers 1a, 2a (10 GeV mu-), 3a (300 um of silicon, 10 mm x 10 mm) and 4a. That fixes:

- observable kind `most-probable-value`, domain `em`, defined on E_in - E_exit of transmitted primaries;
- an EM-only physics list (option 4 with decay) justified from its source, Urban fluctuations varied against PAI;
- a cut scan 0.1, 0.03 and 0.01 mm with tolerances for the convergence gate;
- the `thin-layer-mpv` reference benchmark against the PDG Landau-Vavilov value, inputs from the PDG silicon tables;
- the label: every output stays `unvalidated`, with benchmarks and scope embedded.

`check_geant4_study.py spec` on the draft spec reports the applicable rules (`G4R-THIN-FLUCT`,
`G4R-THIN-CUT-SCAN`, `G4R-PRECISION-EM`) with their sources and no missing field.

## 5. Final Mutually-Agreed Specification Document

```json
{
 "schema": "geant4-study-spec/1",
 "study_id": "illustrative-mpv-mu10gev-si300um",
 "label": "ILLUSTRATIVE study; every Geant4 output is unvalidated; names no experiment",
 "observable": {"name": "most probable energy loss", "kind": "most-probable-value", "domain": "em",
                "definition": "MPV of E_in - E_exit of primaries transmitted through the slab", "unit": "MeV",
                "weighted": false},
 "particle": {"name": "mu-", "energy_MeV": 10000.0},
 "geometry_source": {"kind": "design", "description": "one 300 um silicon slab, 10 mm x 10 mm, vacuum world",
                     "uses_replicas": false},
 "materials": [{"name": "Si_study", "density_g_cm3": 2.329, "z_over_a": 0.498478, "mean_excitation_eV": 173.0,
                "sternheimer": {"a": 0.1492, "k": 3.2546, "x0": 0.2015, "x1": 2.8716, "Cbar": 4.4355, "delta0": 0.14},
                "reference_source": "PDG Atomic and Nuclear Properties, silicon, 2024 edition",
                "reference_origin": "independent"}],
 "physics": {"layered_sim_spec": "specs/mpv-mu10GeV.json", "ui_order": "after-physics-list-before-initialize",
             "justification": [{"choice": "G4EmStandardPhysics_option4 + G4DecayPhysics",
                                "reason": "electromagnetic energy loss of a muon; precise EM models",
                                "source": "geant4:source/physics_lists/constructors/electromagnetic/include/G4EmStandardPhysics_option4.hh"}]},
 "convergence_plan": {"parameters": [{"name": "physics.default_cut_mm", "values": [0.1, 0.03, 0.01]}],
                      "observables": ["mean_deposit_MeV", "mpv_deposit_MeV", "tail_fraction"],
                      "tolerance_relative": {"mean_deposit_MeV": 0.01, "mpv_deposit_MeV": 0.02, "tail_fraction": 0.1}},
 "statistical_target": {"observable": "mpv_loss_MeV", "relative_se": 0.01},
 "validation_plan": {"benchmarks": [{"name": "thin-layer-mpv", "grade": "reference"},
                                    {"name": "thin-layer-width", "grade": "sanity"}],
                     "scope": {"particle": "mu-", "energy_MeV": [10000.0, 10000.0], "material": "Si_study",
                               "thickness_mm": [0.3, 0.3], "observable": "most probable energy loss"}},
 "variation_plan": {"observable": "mpv_loss_MeV", "model_assignment_checked": true,
                    "variations": [{"name": "em-option0", "change": "G4EmStandardPhysics"},
                                   {"name": "pai", "change": "/process/em/AddPAIRegion all SiRegion PAI"}]},
 "downstream_use": {"kind": "report", "handoff": ["hep-citations", "hep-authoring"]},
 "reproducibility": {"data_paths_recorded": true}
}
```

The runs, benchmarks and study record of this spec are worked through in
[examples/geant4-thin-silicon](../../../examples/geant4-thin-silicon/run.py).
