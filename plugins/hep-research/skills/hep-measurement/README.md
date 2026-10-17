# hep-measurement

Measurement design and review for particle and astroparticle physics. What the skill owns, never does, and its
invariants are stated once, in [SKILL.md](SKILL.md); this page is a folder guide for people. Correlations: hep-measurement supplies the physical correlation evidence and a proposed scheme with its justification; hep-statistics encodes it in the likelihood and checks positive semidefiniteness.

Formerly `hep-analysis`; the old name is a deprecated alias in contracts 2.9.0.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point: invariants, workflow, context resolution, resources, handoffs |
| `references/` | thirteen method references, routed from `hep-measurement-guide.md` (`data-pipelines.md` is a pointer: the code-level pipeline material moved to hep-computing's `analysis-data-pipelines.md`) |
| `scripts/` | eighteen command-line helpers (acceptance from generation records, anisotropy in right ascension, systematic variations, yield and systematics tables, counting reference, blinded-bin masking, analysis-change and spec review, collection time, cosmic-ray helpers, spectral-variable transformation, isotope fractions) |
| `assets/` | the `measurement-spec` template and its field guide, a synthetic cosmic-ray worked spec, the systematics ledger (CSV), the report template, the measurement-review template and a synthetic review example, a synthetic cosmic-ray spectrum example |

## Scripts

The scripts cover the acceptance from generation records (generation factor times the selected fraction, Clopper-Pearson per bin), systematic variations, yield and systematics tables, a Poisson counting reference, a ratio of two yields, blinded-bin masking (synthetic data and tests only), analysis-change and spec review, collection time per era and bin (live time above the cutoff, with partial accumulation and merge), and cosmic-ray helpers (flux from counts, power-law fit, first-harmonic anisotropy with exposure and spurious-modulation checks, geomagnetic cutoff, force-field modulation), the transformation of a flux to another spectral variable with an isotope composition, and isotope fractions from mass templates. Each one is described once, in the "Executable resources" section of `references/hep-measurement-guide.md`. Every script takes `--status`, emits JSON or a labelled table, and exits 0 ok, 1 finding or failed computation, 2 invalid input, 3 incomplete. Read `--help` first.

## References

Start with `references/hep-measurement-guide.md`, which routes to one reference per question: analysis design, review and deliverables, weights and normalization, histograms and efficiencies, backgrounds, systematics, measurement definitions (unfolding and combination methods belong to hep-statistics), analysis validation. `references/cosmic-ray-measurements.md` indexes the cosmic-ray measurement types (absolute flux, flux and isotope ratios, time-dependent flux, rare-event searches) by linking existing sections, and adds the anisotropy measurement design (dipole amplitude and phase, directional exposure, upper limits on the amplitude, whose statistics belong to hep-statistics; time-bin covariance and binned-series inference link to hep-statistics' `time-series-inference.md`); status `documented`. `references/rare-event-and-neutrino-measurements.md` covers rare-event searches and neutrino measurements (exposure in kg y or t y and live time, region-of-interest choice without unblinding, salting and blinding, the background budget, energy scale and quenching, flux, cross section and near/far extrapolation, presentation); status `documented`. Detector data/MC validation lives in hep-detector.

## Handoffs

| Need | Hand to |
|---|---|
| Response matrix, efficiency or resolution evidence | hep-detector |
| Likelihood, intervals, unfolding, covariance assembly | hep-statistics |
| Prediction to compare against | hep-theory |
| Classifier or BDT training, working point | hep-ml |
| Pipeline code, partition and merge, run manifests | hep-computing |
| Write-up | hep-communication |

## Tests and validation

`tests/skills/hep_measurement/` (twenty-one test modules: one per script or reference family, including the CLI contract, the reference links and the worked examples of the method references) and the journey examples under `examples/` (the synthetic flux-ratio and collider-angular examples start here). What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.

## Example requests

Requests this skill answers (moved from the analysis guide, B-03):

- "Review this measurement spec and tell me whether it is ready."
- "Design the selection, background estimate and correction chain for a flux measurement over two periods."
- "Which systematics should I evaluate for this cross section, and how does each reach the result?"
- "Review this NanoAOD selection and explain the yield difference for the negative-weight sample."
- "Is a 4.8-sigma excess in my ON/OFF gamma-ray source search significant after accounting for the sky scan?"
- "Convert this local-interstellar proton spectrum to what we'd expect at 1 AU during solar minimum vs. solar maximum."
- "Propagate the uncertainty on a positron fraction from independent positron and electron template-fit yields."
- "Compute the differential flux and its statistical uncertainty from these raw counts, exposure, and bin width."
