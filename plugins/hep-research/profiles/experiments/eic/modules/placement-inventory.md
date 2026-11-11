# Placement inventory

> Method owner: none (this table records where every piece of content lives and why).

Four placements: **general HEP method** (owned by a core skill; not in this profile), **EIC facility context** (`modules/facility/`), **ePIC configuration** (`modules/detector/`), **project-local** (`hep-research.project.json`, a local profile or research artifacts; never this profile).

| Content | Placement | Owner | Rationale | Link |
|---|---|---|---|---|
| DIS kinematic variables, identities and QCD concepts | general HEP method | hep-theory | Not in this profile: relevance to the EIC does not make a derivation experiment-specific. hep-theory now owns the general reference (added as a follow-up of the profile review, which had recorded the gap) | `<plugin root>/skills/hep-theory/references/dis-kinematics.md` |
| Event selection, efficiency and acceptance corrections, backgrounds, luminosity normalization, systematics evaluation | general HEP method | hep-measurement | Not in this profile; only configuration facts (species, energies as design targets) enter from `facility/beam-configurations.md` | `<plugin root>/skills/hep-measurement/SKILL.md` |
| Tracking, calorimetry, PID, timing, DAQ and calibration methods, resolution and efficiency measurement | general HEP method | hep-detector | Not in this profile; `detector/epic-detector-context.md` adds only what ePIC states about itself | `<plugin root>/skills/hep-detector/SKILL.md` |
| Likelihoods, covariance propagation, unfolding algorithms, coverage | general HEP method | hep-statistics | Not in this profile; nothing EIC-specific is needed for v0.1 | `<plugin root>/skills/hep-statistics/SKILL.md` |
| Software environments, builds, I/O, batch execution, reproducibility | general HEP method | hep-computing | Not in this profile; `detector/epic-software-entry-points.md` names ePIC entry points only | `<plugin root>/skills/hep-computing/SKILL.md` |
| Machine-learning classifiers, regressors, fast simulation and surrogates: grouped splits, event weights, calibration of outputs, simulation-to-data shift | general HEP method | hep-ml | Not in this profile; no ePIC-specific model, training sample or working point is recorded in v0.1 | `<plugin root>/skills/hep-ml/SKILL.md` |
| Literature verification, citation practice | general HEP method | hep-citations | Not in this profile; `sources/source-policy.md` fixes the EIC tiers only | `<plugin root>/skills/hep-citations/SKILL.md` |
| Kinds of number, project stage, where facility design values live | EIC facility context | profile:eic | Facility overview; quotes no number | `facility/eic-facility-context.md` |
| Beam species, energies, polarization and luminosity per configuration; derived center-of-mass energies; spec field format | EIC facility context | profile:eic | CDR design targets and project requirements, each number from a cited numeric claim; kinematics stay with hep-theory | `facility/beam-configurations.md` |
| Crossing angle, crab crossing, space around the interaction point | EIC facility context | profile:eic | CDR design targets and project requirements; reconstruction and kinematics methods stay with hep-detector and hep-theory | `facility/interaction-region.md` |
| ePIC identity, magnet design value, subsystem map, refusal of performance numbers | ePIC configuration | profile:eic | Experiment-scoped overview; design values live in the subsystem modules | `detector/epic-detector-context.md` |
| ePIC tracking subsystems: SVT, MPGDs, tracking volume | ePIC configuration | profile:eic | Construction parameters from cited claims; tracking methods stay with hep-detector | `detector/epic-tracking.md` |
| ePIC particle identification: pfRICH, hpDIRC, dRICH, time of flight | ePIC configuration | profile:eic | Construction parameters from cited claims; PID methods stay with hep-detector | `detector/epic-pid.md` |
| ePIC electromagnetic and hadronic calorimeters by region; calorimeter front end | ePIC configuration | profile:eic | Construction parameters and absence searches; calorimetry methods stay with hep-detector | `detector/epic-calorimetry.md` |
| ePIC far-forward and far-backward detectors: B0, Roman pots, off-momentum detectors, ZDC, luminosity monitor, low-Q² tagger | ePIC configuration | profile:eic | Construction parameters and absence searches; methods stay with hep-detector | `detector/epic-far-forward-backward.md` |
| ePIC streaming readout and front-end architecture | ePIC configuration | profile:eic | Architecture only; no rates, no software | `detector/epic-readout-and-daq.md` |
| ePIC early-running configurations proposed by the collaboration | ePIC configuration | profile:eic | Proposed run plans, never facility values; measurement design stays with hep-measurement | `detector/epic-early-running.md` |
| ePIC software repositories, data model, container environment | ePIC configuration | profile:eic | Entry points only; no release pinned, nothing executed | `detector/epic-software-entry-points.md` |
| Source tiers and quotation rules for EIC and ePIC material | ePIC configuration | profile:eic | Profile-specific application of the general citation discipline | `sources/source-policy.md` |
| Scope labels, ask-before-selecting rule, what never to claim | ePIC configuration | profile:eic | Profile rules | `working-rules.md` |
| Analysis cuts, generated samples, campaign settings, private conditions, unpublished constants, software release pins | project-local | project | Never universal plugin defaults; recorded in project configuration and `computational-run` artifacts | `hep-research.project.json` |
