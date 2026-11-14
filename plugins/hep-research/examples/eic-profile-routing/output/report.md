# experiment:eic usage example

Profile experiment:eic 0.6.1 selected through hep-research.project.json; wrong pin rejected: True.

| Scenario | Decision | Files read |
|---|---|---|
| generic-dis | none | none |
| eic-facility | use | modules/facility/eic-facility-context.md |
| epic-detector | use | modules/detector/epic-detector-context.md |
| ambiguous-detector | ask | none |
| unrelated-experiment | use | none |
| eic-beam-configuration | use | modules/facility/beam-configurations.md |
| eic-crossing-angle | use | modules/facility/interaction-region.md |
| eic-theory-settings | use | modules/facility/beam-configurations.md |
| epic-tracking | use | modules/detector/epic-tracking.md |
| epic-pid | use | modules/detector/epic-pid.md |
| epic-calorimetry | use | modules/detector/epic-calorimetry.md |
| epic-far-forward | use | modules/detector/epic-far-forward-backward.md |
| epic-readout | use | modules/detector/epic-readout-and-daq.md |
| epic-early-running | use | modules/detector/epic-early-running.md |
| epic-pi-k-separation | use | modules/working-rules.md |
| eic-spec-check | use | modules/facility/beam-configurations.md |

Project config alone (request names no profile): decision use, source project-config, experiments experiment:eic.

| Atlas query | Rows | Bound-profile rows | see_profile |
|---|---|---|---|
| bound ePIC | 20 | 20 | - |
| bound EIC | 16 | 16 | - |
| unbound ePIC | 0 | 0 | experiment:eic |
| unbound EIC | 0 | 0 | experiment:eic |
| unbound Electron-Ion Collider | 0 | 0 | experiment:eic |

Profile files opened during the run: profiles/experiments/ams-02/profile.json, profiles/experiments/eic/benchmarks/routing-scenarios.json, profiles/experiments/eic/index.md, profiles/experiments/eic/modules/detector/epic-calorimetry.md, profiles/experiments/eic/modules/detector/epic-detector-context.md, profiles/experiments/eic/modules/detector/epic-early-running.md, profiles/experiments/eic/modules/detector/epic-far-forward-backward.md, profiles/experiments/eic/modules/detector/epic-pid.md, profiles/experiments/eic/modules/detector/epic-readout-and-daq.md, profiles/experiments/eic/modules/detector/epic-tracking.md, profiles/experiments/eic/modules/facility/beam-configurations.md, profiles/experiments/eic/modules/facility/eic-facility-context.md, profiles/experiments/eic/modules/facility/interaction-region.md, profiles/experiments/eic/modules/working-rules.md, profiles/experiments/eic/profile.json, profiles/experiments/synthetic-collider/profile.json, profiles/reference/detector-atlas/profile.json, profiles/reference/geometry-cases/profile.json, profiles/registry.json, profiles/theory/cr-secondary-antiprotons/profile.json, profiles/theory/cr-secondary-ratio/profile.json, profiles/theory/dis-parton-model/profile.json, profiles/theory/drell-yan-lo/profile.json, profiles/theory/heliospheric-modulation/profile.json, profiles/theory/higgs-bb-width/profile.json, profiles/theory/qcd-r-ratio/profile.json, profiles/theory/qed-benchmark/profile.json, profiles/theory/tmd-gaussian-lo/profile.json.

Shows profile selection, selective loading and how the detector atlas reaches the profile; asserts no EIC or ePIC value (the atlas rows are listed by claim id only).
