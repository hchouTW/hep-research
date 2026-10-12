# hep-analysis

Use when the deliverable is the design or review of an experimental measurement in particle or astroparticle physics: estimand and observable definition, event or candidate selection and cutflows, background estimation, correction chains, the physical sources of systematic uncertainties and their evaluation plan, blinding design advice, and verdict-first measurement review. Collider, fixed-target, neutrino and space- or ground-based cosmic-ray measurements, with or without a profile.

**Owns:** experimental design, estimands, selections, backgrounds, correction chains, physical sources of systematics and their evaluation plan, measurement review, blinding design advice (the blinding policy itself belongs to the collaboration). Typical artifact: `measurement-spec`.

**Never:** invent experiment conventions, cut values, efficiencies or resolutions; write theory derivations; choose correlations for the likelihood.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point: invariants, workflow, context resolution, resources, handoffs |
| `references/` | nine method references, routed from `hep-analysis-guide.md` |
| `scripts/` | twelve command-line helpers (systematic variations, yield and systematics tables, counting reference, blinded-bin masking, analysis-change review, cosmic-ray helpers) |
| `assets/` | templates: analysis contract (YAML), systematics table and config, report template, a synthetic cosmic-ray spectrum example |

## Scripts

`check_systematic_variations.py` classifies each variation as normalization, shape or mixed; `make_yield_table.py` and `systematics_table_tex.py` build tables that keep their status label; `counting_reference.py` is the Poisson counting reference; `particle_ratio_with_uncertainty.py`; `mask_blinded_bins.py` masks blinded bins on synthetic data and tests only (with real data it is the custodian's step); `review_analysis_change.py` separates calibration updates with provenance from outcome-driven tuning; `cosmic_ray_flux.py`, `cr_spectrum_powerlaw_fit.py`, `geomagnetic_cutoff.py`, `orbit_averaged_geomagnetic_cutoff.py` and `solar_modulation_force_field.py` are cosmic-ray helpers. Read `--help` first.

## References

Start with `references/hep-analysis-guide.md`, which routes to one reference per question: analysis design, data pipelines, weights and normalization, histograms and efficiencies, backgrounds, systematics, measurement definitions (unfolding and combination methods belong to hep-statistics), analysis validation. Detector data/MC validation lives in detector-response.

## Handoffs

| Need | Hand to |
|---|---|
| Response matrix, efficiency or resolution evidence | detector-response |
| Likelihood, intervals, unfolding, covariance assembly | hep-statistics |
| Prediction to compare against | hep-theory |
| Pipeline code, partition and merge, run manifests | hep-computing |
| Write-up | research-communication |

## Tests and validation

`tests/skills/hep_analysis/` (eight modules) and the journey examples under `examples/` (the synthetic flux-ratio and collider-angular examples start here). What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.
