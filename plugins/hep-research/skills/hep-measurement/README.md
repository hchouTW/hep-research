# hep-measurement

Measurement design and verdict-first measurement review for particle and astroparticle physics, delivered as a validated `measurement-spec` artifact, a measurement brief, a quick answer or a review.

## Core capabilities

- Estimand and observable definition: one-sentence estimand, variables with units and binning, phase space or fiducial definition, result level, frame, normalization kind, bin semantics.
- Event and candidate selection with cutflows; every selection names its conditional denominator and its validation (metric, threshold, action).
- Background estimation: control regions, ABCD, sidebands, fake rates, transfer factors, coupled species, antiparticle backgrounds; each background with an estimator, a control region or constraint, and a closure test.
- Correction chains: efficiency factors and their denominators, acceptance from generation records, exposure, live and collection time, luminosity, protons on target, data/MC ratios; each correction exactly once.
- Physical sources of systematic uncertainties, their correlation evidence and evaluation plan (normalization, shape, migration or mixed; `applied_via`; scaling class).
- Correlations: hep-measurement supplies the physical correlation evidence and a proposed scheme with its justification; hep-statistics encodes it in the likelihood and checks positive semidefiniteness.
- Blinding design advice (the blinding policy itself belongs to the collaboration).
- Measurement review: verdict first, ranked defects, unresolved inputs; review of a spec or of an analysis change.
- Cosmic-ray measurements: absolute flux, flux and isotope ratios, time-dependent flux, rare-event searches, anisotropy design (dipole amplitude and phase, directional exposure, upper limits on the amplitude).
- Rare-event and neutrino measurements: exposure in kg y or t y and live time, region-of-interest choice without unblinding, salting and blinding, background budget, energy scale and quenching, flux, cross section, near/far extrapolation, presentation.
- Command-line helpers for acceptance, collection time, systematic variations, yield and systematics tables, a counting reference, a ratio of two yields, blinded-bin masking, spec and change review, cosmic-ray quantities and the naming inventories (see Input and output specifications).

## Triggering conditions

Use when:

- the deliverable is the design or review of an experimental measurement: estimand, observable, selection, cutflow, backgrounds, correction chain, systematics plan, blinding policy;
- the measurement is collider, fixed-target, neutrino or cosmic-ray, with or without a profile;
- the question concerns a named experiment's beams or run conditions for a measurement (load it first even for a quick question).

Not for:

| Need | Hand to |
|---|---|
| Response matrix, efficiency or resolution evidence; detector data/MC validation | hep-detector |
| Likelihood, intervals, unfolding, combinations, covariance assembly | hep-statistics |
| Prediction to compare against; theory or model-vs-data comparison | hep-theory |
| Classifier or BDT training, working point | hep-ml |
| Pipeline code, partition and merge, run manifests | hep-computing |
| Write-up | hep-authoring |

## Workspace directory architecture

```text
hep-measurement/
├── SKILL.md          entry point loaded by the host
├── README.md         this folder guide
├── references/       method references, entry: hep-measurement-guide.md
├── scripts/          command-line helpers (standard library first)
└── assets/           spec template, field guide, ledgers, templates, synthetic examples
```

| Path | Content |
|---|---|
| `SKILL.md` | entry point: invariants, workflow, context resolution, resources, handoffs; its front matter carries the routing description and it stays under 8 KiB |
| `references/` | twelve method references, routed from `hep-measurement-guide.md` (the code-level pipeline material is hep-computing's analysis-data-pipelines.md) |
| `scripts/` | nineteen command-line helpers (acceptance from generation records, anisotropy in right ascension, systematic variations, yield and systematics tables, counting reference, ratio of two yields, blinded-bin masking, analysis-change and spec review, collection time, cosmic-ray helpers, spectral-variable transformation, isotope fractions, the naming extractor for samples, regions and variations) |
| `assets/` | the `measurement-spec` template and its field guide, a synthetic cosmic-ray worked spec, the systematics ledger (CSV), the report template, the measurement-review template and a synthetic review example, a synthetic cosmic-ray spectrum example, an isotope-fraction example |

References, starting from `references/hep-measurement-guide.md` (one reference per question):

- analysis design (triggers, optimization, look-elsewhere at the design stage, blinding), review and deliverables, weights and normalization, histograms and efficiencies, backgrounds, systematics, measurement definitions (unfolding and combination methods belong to hep-statistics), analysis validation, correction chain.
- `references/cosmic-ray-measurements.md`: indexes the cosmic-ray measurement types by linking existing sections and adds the anisotropy measurement design; the statistics of amplitude limits belong to hep-statistics; time-bin covariance and binned-series inference link to hep-statistics' time-series-inference reference; status `documented`.
- `references/rare-event-and-neutrino-measurements.md`: rare-event searches and neutrino measurements; status `documented`.

## Input and output specifications

Inputs:

- Request: a design question, a measurement to specify, or a spec, note or analysis change to review.
- Profiles and context: the profiles the user names, else those bound in `hep-research.project.json` (checked with `contracts/project.py --preflight`); a profile's `index.md` and only the modules or dataset records the task needs. Without a profile, general methods.
- Files and artifacts read: `measurement-spec` artifacts, yield tables (CSV with region, sample, yield), systematics ledgers (CSV columns of `assets/systematics.csv`: name, source, effect, applied_via, affected_processes, correlation_key, payload, validation), dataset-record artifacts, generation records, counts, exposure and bin widths.

Outputs:

- Artifacts written: `measurement-spec` (selection, background and systematics ledgers inside it) in the project's `artifacts_dir` (default `./hep-research-artifacts/`), validated with `python3 "<plugin root>/contracts/validate.py" <artifacts_dir> [--profiles-from <hep-research.project.json>]`.
- Handoff artifacts: `response` (from hep-detector), `measurement-spec` plus inputs (to hep-statistics), `prediction` (hep-theory), `ml-artifact` (hep-ml), `computational-run` (hep-computing), `communication` (hep-authoring).
- Naming inventories: a working file under `<project>/naming/`, refused inside `artifacts_dir`.

Script CLI contract (every script; each one is described once, in the "Executable resources" section of `references/hep-measurement-guide.md`):

```text
--help              read first
--status LABEL      artifact status label of the inputs, echoed in the output
output              JSON or a labelled table
exit 0              ok
exit 1              finding or failed computation
exit 2              invalid input
exit 3              incomplete (or a missing optional package)
```

Script coverage (descriptions, not file names): the acceptance from generation records (generation factor times the selected fraction, Clopper-Pearson per bin), systematic variations, yield and systematics tables, a Poisson counting reference, a ratio of two yields, blinded-bin masking (synthetic data and tests only), analysis-change and spec review, collection time per era and bin (live time above the cutoff, with partial accumulation and merge), cosmic-ray helpers (flux from counts, power-law fit, first-harmonic anisotropy with exposure and spurious-modulation checks, geomagnetic cutoff, force-field modulation), the transformation of a flux to another spectral variable with an isotope composition, isotope fractions from mass templates, and the naming extractor.

## Setup requirements

- Python 3.13 or newer.
- Standard library first; contract, registry and blinding checks need only the standard library.
- NumPy: needed only by the isotope-fraction helper; without it that script exits 3.
- Plugin-wide scientific stack for examples and tests: `requirements-core.txt` at the plugin root (NumPy, SciPy, Matplotlib, SymPy).
- No environment variables.

## Operational constraints

- Never invents experiment conventions, cut values, efficiencies or resolutions; never writes theory derivations; never encodes correlations in the likelihood.
- Every number that describes an experiment comes from a profile evidence record, the user, or is marked `unknown` / `not-provided`; unknown is never zero.
- Each correction appears exactly once; efficiency, acceptance, exposure (or luminosity, protons on target, target exposure) and live time stay distinct; the normalization kind is declared.
- An unchanged integrated yield does not show a systematic was not propagated; shape, migration between bins and sensitivity of the result are checked.
- Blinded observables and regions stay masked in every plot, ratio, log, cache and report; only an authorized person unblinds, outside the agent session, never the agent even if asked; passing checks is not authorization.
- Synthetic, Asimov and observed data are never mixed without labels; status labels carry to everything derived.
- Profiles are read only through the context-resolution steps; no experiment facts are embedded; durable results are JSON artifacts in `artifacts_dir`, never inside the plugin.
- A successful script run is a software check, not scientific validity.
- No other skill runs automatically; a handoff names the consuming skill and the artifact path.
- [SKILL.md](SKILL.md) is the authoritative statement of what the skill owns, never does, and its invariants.

## Validation

- `tests/skills/hep_measurement/`: 33 test modules (one per script or reference family, including the CLI contract, the reference links and the worked examples of the method references).
- Journey examples under the plugin's `examples/`: the synthetic flux-ratio (`examples/ams-flux-ratio/`) and collider-angular (`examples/collider-angular/`) examples start here.
- What is and is not validated: `docs/capability-matrix.md`; the evidence: `VALIDATION.md`.

## Example requests

- "Review this measurement spec and tell me whether it is ready."
- "Design the selection, background estimate and correction chain for a flux measurement over two periods."
- "Which systematics should I evaluate for this cross section, and how does each reach the result?"
- "Review this NanoAOD selection and explain the yield difference for the negative-weight sample."
- "Is a 4.8-sigma excess in my ON/OFF gamma-ray source search significant after accounting for the sky scan?"
- "Convert this local-interstellar proton spectrum to what we'd expect at 1 AU during solar minimum vs. solar maximum."
- "Propagate the uncertainty on a positron fraction from independent positron and electron template-fit yields."
- "Compute the differential flux and its statistical uncertainty from these raw counts, exposure, and bin width."
