# AMS-02 profile: routing map

Profile `experiment:ams-02` adds AMS-02 knowledge to the core skills; it is never an entry point. Public-domain reasoning only: no invented internal AMS data, cuts, constants or run rules. Read [working rules](modules/working-rules.md) first (invariants, labels, source rule, full routing table). Paths are relative to this folder.

| Request | Read |
|---|---|
| Subsystem, observable, unit, cross-subsystem role | `modules/subsystems/detector-and-observables.md` (+ `instrument-overview.md` for a short tour) |
| p, He, nuclei flux or B/C-type ratio | `modules/species/charged-cosmic-rays.md`, then the methods below |
| e+, e-, positron fraction, antiprotons, antinuclei | `modules/species/antimatter-and-leptons.md` |
| Isotopes, charge ladder, mass from R and beta | `modules/species/nuclei-and-isotopes.md` |
| Selection, run quality, time stability | `modules/methods/reconstruction-and-data-quality.md` |
| Efficiency, acceptance, exposure, backgrounds | `modules/methods/efficiency-acceptance-backgrounds.md` |
| Calibration, MC, systematics | `modules/methods/calibration-mc-systematics.md` |
| Response, likelihood, unfolding, limits | `modules/methods/inference-and-unfolding.md`; exact numbers via `modules/methods/statistical-diagnostics.md` |
| Specification, ledger or formal review as deliverable | `modules/methods/analysis-artifacts.md` (audit with `scripts/audit_analysis_spec.py`) |
| Time-resolved flux or ratio, solar cycle, periodicity | `modules/periods/time-dependent-analysis.md` |
| What AMS published, "latest", is a paper real | `modules/sources/source-policy.md`, then `evidence/index.md` |
| Other experiments' data, CRDB, SSDC database | `modules/sources/cosmic-ray-databases.md` |
| Intended behavior on sample requests | `modules/methods/worked-examples.md` |
| AMS Offline software, EOS productions, ntuple producer (access-controlled) | not in this profile: see below |

Access-controlled software and data are in `experiment:ams-02-private`, provided by the access-restricted `ams02-research` plugin. Without that plugin installed, say the profile is unavailable and never answer those topics from memory.

Evidence: `evidence/sources.json`, `evidence/claims.json` (IDs `ams02:S01`, `ams02:C01`), `evidence/index.md` (generated). Quote an AMS number only from a claim whose species, range, period and selection cover the statement. What AMS published, a paper's numbers or a supplement's contents are answered from these files at the reading level each row records; a missing PDF is no reason to decline.

Conventions: `conventions.json`. Datasets: `datasets/` (metadata records; `ams02:method_module` names the method module and claims). Networked scripts (`scripts/fetch_papers.py`, `scripts/crdb_query.py`) run only with the user's approval.
