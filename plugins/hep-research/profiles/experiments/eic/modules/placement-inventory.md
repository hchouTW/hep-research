# Placement inventory

> Method owner: none (this table records where every piece of content lives and why).

Four placements: **general HEP method** (owned by a core skill; not in this profile), **EIC facility context** (`modules/facility/`), **ePIC configuration** (`modules/detector/`), **project-local** (`hep-research.project.json`, a local profile or research artifacts; never this profile).

| Content | Placement | Owner | Rationale | Link |
|---|---|---|---|---|
| DIS kinematic variables, identities and QCD concepts | general HEP method | hep-theory | Not in this profile: relevance to the EIC does not make a derivation experiment-specific. hep-theory now owns the general reference (added as a follow-up of the profile review, which had recorded the gap) | `<plugin root>/skills/hep-theory/references/dis-kinematics.md` |
| Event selection, efficiency and acceptance corrections, backgrounds, luminosity normalization, systematics evaluation | general HEP method | hep-analysis | Not in this profile; only configuration facts (species, energies as design targets) enter from `facility/eic-facility-context.md` | `<plugin root>/skills/hep-analysis/SKILL.md` |
| Tracking, calorimetry, PID, timing, DAQ and calibration methods, resolution and efficiency measurement | general HEP method | detector-response | Not in this profile; `detector/epic-detector-context.md` adds only what ePIC states about itself | `<plugin root>/skills/detector-response/SKILL.md` |
| Likelihoods, covariance propagation, unfolding algorithms, coverage | general HEP method | hep-statistics | Not in this profile; nothing EIC-specific is needed for v0.1 | `<plugin root>/skills/hep-statistics/SKILL.md` |
| Software environments, builds, I/O, batch execution, reproducibility | general HEP method | hep-computing | Not in this profile; `detector/epic-software-entry-points.md` names ePIC entry points only | `<plugin root>/skills/hep-computing/SKILL.md` |
| Literature verification, citation practice | general HEP method | research-communication | Not in this profile; `sources/source-policy.md` fixes the EIC tiers only | `<plugin root>/skills/research-communication/SKILL.md` |
| Beam species, polarization, collision configurations, interaction region, where design targets live | EIC facility context | profile:eic | Facility facts, labeled design targets; no number transcribed in v0.1 | `facility/eic-facility-context.md` |
| ePIC identity, magnet design value, subsystem list, streaming readout plan | ePIC configuration | profile:eic | Experiment-scoped statements from the host laboratory page, an undated page read on the verification date | `detector/epic-detector-context.md` |
| ePIC software repositories, data model, container environment | ePIC configuration | profile:eic | Entry points only; no release pinned, nothing executed | `detector/epic-software-entry-points.md` |
| Source tiers and quotation rules for EIC and ePIC material | ePIC configuration | profile:eic | Profile-specific application of the general citation discipline | `sources/source-policy.md` |
| Scope labels, ask-before-selecting rule, what never to claim | ePIC configuration | profile:eic | Profile rules | `working-rules.md` |
| Analysis cuts, generated samples, campaign settings, private conditions, unpublished constants, software release pins | project-local | project | Never universal plugin defaults; recorded in project configuration and `computational-run` artifacts | `hep-research.project.json` |
