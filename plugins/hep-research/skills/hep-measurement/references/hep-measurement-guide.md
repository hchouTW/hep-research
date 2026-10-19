# Measurement design and review: routing and invariants (guide)

Routing and rules of the hep-measurement skill: the routing table first, then check-first corrections, working
procedure, analysis invariants and this skill's scripts. Links are relative to this file.

## Reference routing

| Task | Read |
|---|---|
| Analysis design, quality masks, triggers, blinding, event keys | [Analysis design](analysis-design.md) |
| Trigger efficiency from data: orthogonal and bootstrap triggers, prescaled unbiased samples, bias checks | [Analysis design, triggers](analysis-design.md#trigger-efficiency-from-data) |
| Selection optimization: figures of merit (Asimov Z, Punzi), disjoint optimization samples | [Analysis design, optimization](analysis-design.md#selection-optimization-without-bias) |
| Look-elsewhere at the design stage: scan grid and trials method fixed before unblinding | [Analysis design, look-elsewhere](analysis-design.md#look-elsewhere-at-the-design-stage) |
| Review an analysis, note or spec; which deliverable to produce; measurement brief | [Review and deliverables](review-and-artifacts.md) |
| The measurement-spec fields and template | [Field guide](../assets/measurement_spec.template.md) |
| Correction chain: efficiency factors and their denominators, exposure, luminosity, POT, data/MC ratios | [Correction chain](correction-chain.md) |
| Cosmic-ray measurement types (absolute flux, ratios, isotopes, time dependence, rare events) and anisotropy design (dipole, directional exposure, amplitude limits) | [Cosmic-ray measurements](cosmic-ray-measurements.md) |
| Time-dependent measurements: per-period exposure, Bartels rotations, efficiency drift | [Correction chain, time dependence](correction-chain.md#time-dependent-measurements) |
| Nuclei and isotopes: survival probability, fragmentation feed-down, charge-ladder leakage | [Correction chain, nuclei](correction-chain.md#nuclei-and-isotopes) |
| Neutrino and fixed-target: POT, near/far extrapolation, target absorption, empty-target subtraction | [Correction chain, neutrino and fixed target](correction-chain.md#neutrino-and-fixed-target-specifics) |
| Rare events and neutrinos: exposure, ROI, salting, backgrounds, quenching, near/far | [Rare events and neutrinos](rare-event-and-neutrino-measurements.md) |
| Luminosity, cross sections, signed weights, cutflows | [Normalization](weights-normalization.md) |
| Histograms, efficiencies, covariance, plotting | [Histograms and uncertainties](histograms-efficiencies.md) |
| Control regions, ABCD, fake rates, sidebands, transfer factors | [Background estimation](backgrounds.md) |
| Antiparticle backgrounds: charge-sign confusion, species-specific effects, misidentified-proton templates | [Backgrounds, antiparticles](backgrounds.md#antiparticles-and-charge-sign-confusion) |
| Physical sources of systematics, correlation evidence, variation registry | [Systematics](systematics.md) |
| Estimand sentence, truth-level and fiducial definitions, result levels; cross sections, response, unfolding inputs, combinations | [Measurements and unfolding](measurements-and-unfolding.md) |
| Steeply falling spectra: spillover, forward-fold or unfold, binning, resolution tails | [Measurements, spillover](measurements-and-unfolding.md#steeply-falling-spectra-and-spillover) |
| Debugging, verification, preservation, review checks | [Validation](analysis-validation.md) |

## Handoffs to other skills

| Task | Read |
|---|---|
| Detector response, efficiencies, resolution, triggers, calibration, cosmic-ray detection | hep-detector: [detector measurement framework](../../hep-detector/references/detector-measurement-framework.md) |
| Likelihoods, nuisance modeling, intervals, significance, unfolding, combinations | hep-statistics: [core statistics guide](../../hep-statistics/references/core-stats-guide.md) |
| Predictions, generators, theory uncertainties | hep-theory: [event generation](../../hep-theory/references/event-generation.md) |
| Classifiers, BDTs, leakage, mass sculpting | hep-ml: [ML in analyses](../../hep-ml/references/ml-analysis.md) |
| Analysis code, ROOT/columnar pipelines, builds, batch jobs | hep-computing: [analysis data pipelines](../../hep-computing/references/analysis-data-pipelines.md) |
| Citations, versions and methodological sources; diagrams | hep-literature: [primary sources](../../hep-literature/references/primary-sources-and-version-checks.md) |
| Experiment-specific practice and results | The bound experiment profile's `index.md` (`<plugin root>/profiles/registry.json`) |

## Check first: proposals to correct before answering

If the user proposes one of these, open with the correction, even when they only ask "is that right?". Each row restates an invariant below.

| User proposes | Answer |
|---|---|
| MC normalization by entry count, post-skim count, or sum of abs(weights) | No: `lumi * xsec / sum(signed genWeight)` over the full produced sample before any skim (e.g. the NanoAOD `Runs` tree `genEventSumw`); keep negative weights. Units: lumi in fb^-1 times xsec in pb needs a factor 1000 (`lumi_fb * 1000 * xsec_pb / sumw`). For code, show RDataFrame that reads `genEventSumw` from `Runs` ([pattern](../../hep-computing/references/analysis-data-pipelines.md#normalization-denominator-in-rdataframe-skimmed-nanoaod)) |
| `sqrt(N)` error on a few-count flux/rate bin | No: run `python3 <plugin root>/skills/hep-measurement/scripts/cosmic_ray_flux.py --counts N --exposure E --bin-width W --bin-width-unit GV --level 0.6827` (W in the flux's energy or rigidity unit (per GV: 600 for a 1.2-1.8 TV bin; never pass a width in TV)) with Bash before you answer, and quote the `flux`, `flux_lower` and `flux_upper` it prints, with units and asymmetric errors. Never write a flux value you did not read from that output; if you cannot run it, give the formula and the count interval from the table only. The table below is the check on the count interval. In a high-rigidity/energy bin also spillover and background |
| A plot or ratio covering a blinded region | Say first that SR data stay hidden: on real data plot only the released blinded derivative; on synthetic data drop or NaN the region before plotting; shading is not masking; offer MC/Asimov/CR checks |
| Scaling the final histogram for a kinematic systematic (JES, energy scale) | No: a flat bin scaling is only a normalization change. Vary the object (and propagate to MET and jet ordering), rerun selection and migration, then compare nominal and varied templates for normalization, shape and bin migration (`<plugin root>/skills/hep-measurement/scripts/check_systematic_variations.py`) and the variation's effect on the result. An unchanged integrated yield does not show the variation failed to propagate: a shape-only or migration-only effect keeps it; only a histogram unchanged in every bin calls for confirming propagation |
| Widening a prior or retuning to improve agreement or a limit | If the reason is the fit, the agreement or the limit: decline in your first sentence, before looking for or asking for any file (a missing datacard changes nothing), and do not offer to make the change later; offer pulls/impacts, GoF, a CR constraint. If the user gives an independent measurement made before looking at the fit, that is not tuning: make the change and cite the measurement. Owner of the constraint itself: hep-statistics ([nuisance modeling](../../hep-statistics/references/nuisance-modeling.md)) |
| Quadrature errors on a ratio with shared systematics | No: use the covariance. Only fully correlated multiplicative terms of equal relative size cancel; for a fraction whose numerator is a subset of the denominator use the binomial-type covariance |
| Hottest spot of a scan as a detection | `1-(1-p)^N` holds for N independent trials only; for a correlated scan use toys or the Gross-Vitells bound and report the global p-value ([Gross & Vitells 2010, arXiv:1005.1891](https://arxiv.org/abs/1005.1891)); computed by hep-statistics ([look-elsewhere](../../hep-statistics/references/inference-recipes.md#look-elsewhere-global-significance-of-a-scan)) |
| Tau/iterations chosen by agreement with a model | No: objective criterion fixed in advance, closure on alternative truths; owner hep-statistics ([unfolding](../../hep-statistics/references/unfolding.md)) |

Exact 68.27% (Garwood) interval on the count N; divide by exposure times bin width for the flux (for N = 0 the upper value 1.84 is a one-sided 84.1% upper limit):

| N | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lower | 0 | 0.17 | 0.71 | 1.37 | 2.09 | 2.84 | 3.62 | 4.42 | 5.23 | 6.06 | 6.89 |
| upper | 1.84 | 3.30 | 4.64 | 5.92 | 7.16 | 8.38 | 9.58 | 10.77 | 11.95 | 13.11 | 14.27 |

## Working procedure

1. Classify the task (design, review, quick question). Inspect the project's spec, configs and a small sample before proposing changes.
2. Establish the estimand, data/MC distinction, units, observables, selections, normalization, regions and blinding state. State assumptions; never invent luminosities, cross sections, calibration values or correlations for a reported result.
3. Read only the references the task needs (routing table above). When a bundled script computes the number asked for (flux and Poisson interval, cutoff, ratio uncertainty), run it and quote its output instead of computing by hand. Code itself belongs to hep-computing ([analysis data pipelines](../../hep-computing/references/analysis-data-pipelines.md)).
4. Deliver the spec or answer with its assumptions, validation evidence and limitations, scaled to the question; state which checks were not run and why.

Follow the user's language and project conventions; do not assume an experiment, energy, era or input format.
Preserve existing physics behaviour (cuts, weights, binning, fit models) unless the user asks for a physics change.

## Analysis invariants

### General

- Do not silently change cuts, object ordering, binning, weights, corrections, models, parameter bounds, or nuisance correlations during a refactor. If a change risks altering physics output, say so and propose a comparison method (event count per cut, histogram integrals, max absolute/relative bin difference, fit parameters/uncertainties).
- Preserve signed generator weights. Normalize with the signed sum of generator weights for the corresponding full production (before any skim), not the selected entry count and not the sum of absolute weights. Store both sumw and sumw2.
- Do not count the same events, MC statistical information, or auxiliary measurement twice as independent likelihood information. Remove region overlaps or model them jointly.
- Label observed counts, weighted yields, Asimov expectations, and toy data separately. Arbitrary weighted or background-subtracted data are not ordinary Poisson observations.
- Poisson expectations must be nonnegative. Do not silently clip negative bins; investigate signed weights, sample statistics, binning, or model suitability.
- Propagate shape variations through object corrections, ordering, selections, missing transverse momentum, and category migration where affected. Changing only the final histogram weight is insufficient for a kinematic variation.
- Blinding: masks hide observed values everywhere and only an authorized person unblinds, outside the session; the full rules are in [analysis design, Blinding](analysis-design.md#blinding).
- Do not tune a model to obtain a desired significance, exclusion, or goodness-of-fit value. This includes widening or narrowing a nuisance prior/constraint, changing parameter bounds, or dropping a nuisance after seeing the fit or the limit. Do not write such a change into a datacard or workspace on request, and decline before searching for or asking for the file when the reason is the fit or the limit. Say it biases the result, ask for the independent measurement that justifies it, and offer pulls/impacts, a goodness-of-fit test, or a control-region constraint instead.
- Do not tune simulation, calibration, or alignment parameters to remove a disagreement in the observable being measured. Tune only on independent control observables, with a stated physical justification, and carry the remaining freedom as a systematic.
- Detector-level quantities are inferred, not observed. Rigidity is `p/q`, not momentum; efficiency is not acceptance; a matched object is matched under a stated criterion. State the definition whenever one of these is quoted.
- Distinguish frequentist confidence intervals from Bayesian credible intervals. Report the statistic, tail convention, nuisance treatment, and validity conditions.

### Astroparticle and cosmic-ray

The astroparticle and cosmic-ray invariants (ON/OFF trials, flux level, cutoff and solar phase, shower composition, low-count intervals, correlated ratios) are in [cosmic-ray measurements, invariants](cosmic-ray-measurements.md#astroparticle-and-cosmic-ray-invariants).

## Executable resources

Scripts in `<plugin root>/skills/hep-measurement/scripts/`; each takes `--status`, prints JSON or a labelled table, and exits 0 ok, 1 finding, 2 invalid input, 3 incomplete. Read `--help` first.

- `check_systematic_variations.py`: check that Up/Down histograms exist with the nominal binning, classify each variation's effect as normalization, shape or mixed with a statistical test when the variance of the difference is known (`--independent` only for variations not made from the same events), and flag same-direction integral shifts; its direction comes from payloads and generation code, not integrals (ROOT input needs PyROOT).
- `make_yield_table.py`, `systematics_table_tex.py`: Markdown yield and booktabs systematics tables, labelled with their status.
- `counting_reference.py`: exact Poisson tails and a flat-prior Bayesian bound for one bin, known background; **not** CLs.
- `particle_ratio_with_uncertainty.py`: ratio or fraction of two yields (delta method, optional correlation).
- `mask_blinded_bins.py`: mask blinded bins and data/reference ratios; synthetic data and tests only.
- `review_analysis_change.py`: calibration updates with provenance vs outcome-driven tuning; any verdict other than accept exits 1, and text in a non-Latin script goes to human review.
- `review_measurement_spec.py`: verdict-first review draft of a `measurement-spec` from the validator findings (ranked defects, unresolved inputs; `--markdown`).
- `cosmic_ray_flux.py`: differential flux from an observed count, exposure, and bin width (`--bin-width-unit` required), with an exact Garwood interval for any count, a Feldman-Cousins interval on s >= 0 with a known background, Cousins-Highland (default) or seeded profile-FC with an uncertain background; never a negative bound (`flux_upper_limit` when the lower end is 0); `--method naive` only, labelled approximate.
- `acceptance_from_generation.py` (acceptance), `collection_time.py` (collection time per era and bin), `spectrum_transform.py` (flux in another variable, by isotope), `isotope_fraction.py` (isotope fractions): [correction chain](correction-chain.md).
- `cr_spectrum_powerlaw_fit.py`, `anisotropy.py`, `geomagnetic_cutoff.py`, `orbit_averaged_geomagnetic_cutoff.py`, `solar_modulation_force_field.py`: power-law fits, first-harmonic anisotropy, vertical Stormer cutoff (point, orbit), force-field solar modulation; planning estimates, not backtracing or propagation. The broken power law is the plugin's one parametrization, shared with hep-statistics `covariance_fit.py` ([convention](../../hep-statistics/references/core-stats-commands.md#broken-power-law)); a break's position and significance: hep-statistics (`break-scan`, `global_significance.py`).

Assets in `<plugin root>/skills/hep-measurement/assets/`: `measurement_spec.template.json` and its field guide, `worked-spec.cosmic-ray.synthetic.json`, `measurement-review-template.md`, `review-example.synthetic.json`, `systematics.csv`, `report-template.md`, `cosmic-ray-spectrum.example.json` (synthetic power-law-fit input).

Worked end to end: `<plugin root>/examples/collider-angular/` and `<plugin root>/examples/ams-flux-ratio/` (each writes `review.md`, a sideband closure test, a masked blinded bin); specs with backgrounds, control regions, closure and an active blinding mask: `assets/measurement_spec.template.json` (collider) and `assets/worked-spec.cosmic-ray.synthetic.json` (cosmic ray).
