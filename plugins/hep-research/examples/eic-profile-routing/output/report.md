# experiment:eic usage example

Profile experiment:eic 0.1.0 selected through hep-research.project.json; wrong pin rejected: True.

| Scenario | Decision | Files read |
|---|---|---|
| generic-dis | none | none |
| eic-facility | use | modules/facility/eic-facility-context.md |
| epic-detector | use | modules/detector/epic-detector-context.md |
| ambiguous-detector | ask | none |
| unrelated-experiment | use | none |

Project config alone (request names no profile): decision use, source project-config, experiments experiment:eic.

Profile files opened during the run: profiles/experiments/ams-02/profile.json, profiles/experiments/eic/benchmarks/routing-scenarios.json, profiles/experiments/eic/index.md, profiles/experiments/eic/modules/detector/epic-detector-context.md, profiles/experiments/eic/modules/facility/eic-facility-context.md, profiles/experiments/eic/profile.json, profiles/experiments/synthetic-collider/profile.json, profiles/reference/detector-atlas/profile.json, profiles/registry.json, profiles/theory/cr-secondary-antiprotons/profile.json, profiles/theory/cr-secondary-ratio/profile.json, profiles/theory/dis-parton-model/profile.json, profiles/theory/drell-yan-lo/profile.json, profiles/theory/heliospheric-modulation/profile.json, profiles/theory/higgs-bb-width/profile.json, profiles/theory/qcd-r-ratio/profile.json, profiles/theory/qed-benchmark/profile.json.

Shows profile selection and selective loading only; asserts nothing about the EIC or ePIC.
