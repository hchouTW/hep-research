# v6.3 D03b — review of the cosmic-ray level terms

Status: review record of work package D03b (Phase M1 side track), 2026-10-16. No profile is changed and no term is
promoted: promotion needs a recorded equivalence **and** the maintainer's approval (O02). Sources are the public
files of this checkout only; the `ams02-research` companion was not opened. Labels: **Confirmed**, **Inferred**,
**Unresolved**.

## Terms reviewed

| Term | Owner (namespace) | Where defined | Used by |
| --- | --- | --- | --- |
| `crflux:top-of-instrument` | `experiment:ams-02` (`crflux`, declared in `vocabulary_namespaces`) | `profiles/experiments/ams-02/profile.json:40` (vocabulary only); meaning from `conventions.json` `frame` | 7 dataset records under `profiles/experiments/ams-02/datasets/`; the `ams-flux-ratio` example |
| `crflux:local-interstellar` | `experiment:ams-02` (`crflux`) | `profiles/experiments/ams-02/profile.json:41` (vocabulary only) | nothing in the checkout |
| `crsr:local-interstellar` | `theory:cr-secondary-ratio` (`crsr`) | `profiles/theory/cr-secondary-ratio/profile.json:38`; meaning from `conventions.json` (`frame`, `crsr:observable`) | `predictions/bc-benchmark.prediction.json` |
| `crpb:interstellar-source` | `theory:cr-secondary-antiprotons` (`crpb`) | `profiles/theory/cr-secondary-antiprotons/profile.json:39`; meaning from `conventions.json` and `index.md:20` | `predictions/source-term-benchmark.prediction.json` |

## Term by term

| Aspect | `crflux:top-of-instrument` | `crflux:local-interstellar` | `crsr:local-interstellar` | `crpb:interstellar-source` |
| --- | --- | --- | --- | --- |
| Definition found | `frame`: "detector location (top of the instrument) unless a solar-modulation model is applied and stated" | **none**: the term is declared but no file defines it | `frame`: Galactic rest frame, observer at the disc mid-plane z = 0; observable "interstellar fluxes … at z = 0, before solar modulation" | a source term (production of secondaries in interstellar gas of H and He, n_He/n_H = 0.1), Galactic rest frame; "a source term, not a propagation model" |
| Location | the detector, in orbit | — | z = 0 in the Galactic disc | interstellar gas |
| Quantity | measured flux (or ratio of fluxes) | — | B/C ratio of interstellar fluxes at equal E/n | source term (production rate), not a flux |
| Solar modulation | included (as measured) | — | excluded (before modulation) | not applicable |
| Value domain | level of a measurement-spec observable | — | level of a prediction | level of a prediction |
| Label | Confirmed | Confirmed (absence) | Confirmed | Confirmed |

## Equivalence judgements

| Pair | Judgement | Basis |
| --- | --- | --- |
| `crflux:local-interstellar` ≡ `crsr:local-interstellar` | **Unresolved**: cannot be judged | the `crflux` term has no definition in the checkout; matching names prove nothing (C13) |
| `crflux:top-of-instrument` ≡ either interstellar term | **not equivalent** (Confirmed) | different location and the solar modulation is in one and not the other; relating them needs a modulation model, i.e. a comparison mapping with its conditions, never an alias |
| `crpb:interstellar-source` ≡ any other term | **not equivalent** (Confirmed) | a different quantity (a source term, not a flux) |
| `crflux:top-of-instrument` ≡ a base level | **no base term exists** (Confirmed) | base `levels` are `parton`, `particle-fiducial`, `detector`, `unfolded`; `detector` means reconstructed quantities with detector effects, which a corrected flux is not |

Related but separate: `theory:heliospheric-modulation` predicts "differential flux at 1 AU (top of the atmosphere)
from a LIS" (`conventions.json`) without a level term. 1 AU outside the magnetosphere is not the AMS-02 position; a
force-field conversion between a local interstellar spectrum and 1 AU is an explicit numeric conversion, which C13
makes a comparison mapping, not an alias (**Inferred**).

## Decision proposal (O02; the maintainer decides)

1. Promote nothing to the base layer now: no pair meets equivalence with evidence.
2. Ask the `experiment:ams-02` owner either to define `crflux:local-interstellar` (location, frame, modulation,
   quantity) or to retire it, since nothing uses it. Only with a definition can it be compared to
   `crsr:local-interstellar`, one term at a time.
3. Keep every name as it is. If an equivalence is later recorded, the original owner declares the alias (the D03a
   alias contract checks owner, target, cycles and conversions) and consumers are updated before any profile depends
   on a new base term.
4. Model the top-of-instrument ↔ 1 AU ↔ local-interstellar relations as comparison mappings with their conditions
   (geomagnetic cutoff, modulation model and its parameters) when a case needs them.

## Companion public-interface compatibility matrix

From the public files only (`docs/profile-authoring.md`, `docs/deployment-model.md`,
`tests/contracts/test_companion_validation_cli.py`). The companion's profile is `experiment:ams-02-private`.

| Interface the companion uses | Before M1 | After D03a/D04 | Compatible? |
| --- | --- | --- | --- |
| `registry.py --local <companion>/profile`: JSON `ok`, `profiles`, findings; exit 0/1/2 | as documented | unchanged output and exit codes (validated by `test_companion_validation_cli`) | yes |
| `project.py <dir> --local …`: `profiles` lists every bound id | as documented | unchanged listing; a bound profile that did not load cleanly adds `project.profile_rejected` | yes (one extra error only on an already failing load) |
| A companion profile with an error (for example an incompatible `compatible` range) | reported, but still bound and used by `load_project` consumers | reported and not used by any consumer | yes: stricter, as the profile-authoring text already promises ("dependent work must not proceed") |
| `depends_on: ["experiment:ams-02"]` | checked | checked; a dependency that is rejected rejects the dependent (`profile.dependency_rejected`) | yes |
| Namespaces the companion profile declares | not checked against other profiles at load time | **each namespace has exactly one owner**: a companion profile declaring a namespace a registered profile owns (`ams02`, `crflux`, …) gives `profile.namespace_collision` and neither profile is used | **Unresolved**: depends on the namespaces the companion declares, which this review may not read |
| Base vocabulary | unchanged | unchanged (`effects.json` is new and read by no existing entry point) | yes |

**Action before any release of D03a (Unresolved, for the maintainer):** run the companion's own check,
`python3 "<hep-research root>/contracts/registry.py" --local "<companion root>/profile"`, against this branch. A
`profile.namespace_collision` there means the companion declares a namespace the public `experiment:ams-02` owns;
resolve it by an ownership record or a companion change before release (companion transition stays at stage 1, O11).

## Decision (2026-10-16)

The owner chose the recommendation: **retire `crflux:local-interstellar`**. It is removed from
`profiles/experiments/ams-02/profile.json` (the `experiment:ams-02` profile is part of this plugin, not of the
companion). Nothing is promoted and every other name stays. Before the removal, the companion's own check
(`registry.py --local`) against main `c1ab70b` reported `ok` with no findings, so there is no `profile.namespace_collision`.
