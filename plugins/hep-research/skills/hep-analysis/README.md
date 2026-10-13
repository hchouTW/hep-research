# hep-analysis

Measurement design and review for particle and astroparticle physics. What the skill owns, never does, and its
invariants are stated once, in [SKILL.md](SKILL.md); this page is a folder guide for people. Correlations: hep-analysis supplies the physical correlation evidence and a proposed scheme with its justification; hep-statistics encodes it in the likelihood and checks positive semidefiniteness.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point: invariants, workflow, context resolution, resources, handoffs |
| `references/` | nine method references, routed from `hep-analysis-guide.md` |
| `scripts/` | twelve command-line helpers (systematic variations, yield and systematics tables, counting reference, blinded-bin masking, analysis-change review, cosmic-ray helpers) |
| `assets/` | the `measurement-spec` template and its field guide, the systematics ledger (CSV), the report template, a synthetic cosmic-ray spectrum example |

## Scripts

`check_systematic_variations.py` classifies each variation as normalization, shape or mixed (an unchanged integral is not a propagation failure); `make_yield_table.py` and `systematics_table_tex.py` build tables that keep their status label; `counting_reference.py` is the Poisson counting reference; `particle_ratio_with_uncertainty.py`; `mask_blinded_bins.py` masks blinded bins and data/reference ratios on synthetic data and tests only (it reads the unmasked histogram, so with real data it is the data custodian's preparation step); `review_analysis_change.py` separates calibration updates with provenance from outcome-driven tuning; `cosmic_ray_flux.py`, `cr_spectrum_powerlaw_fit.py`, `geomagnetic_cutoff.py`, `orbit_averaged_geomagnetic_cutoff.py` and `solar_modulation_force_field.py` are cosmic-ray helpers (`cosmic_ray_flux.py` needs `--bin-width-unit`). Every script takes `--status`, emits JSON or a labelled table, and exits 0 ok, 1 finding or failed computation, 2 invalid input, 3 incomplete. Read `--help` first.

## References

Start with `references/hep-analysis-guide.md`, which routes to one reference per question: analysis design, data pipelines, weights and normalization, histograms and efficiencies, backgrounds, systematics, measurement definitions (unfolding and combination methods belong to hep-statistics), analysis validation. Detector data/MC validation lives in detector-response.

## Handoffs

| Need | Hand to |
|---|---|
| Response matrix, efficiency or resolution evidence | detector-response |
| Likelihood, intervals, unfolding, covariance assembly | hep-statistics |
| Prediction to compare against | hep-theory |
| Classifier or BDT training, working point | physics-ml |
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
