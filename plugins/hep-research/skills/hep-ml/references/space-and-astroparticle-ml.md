# Machine Learning for Space and Ground-Based Astroparticle Detectors

Methods for classifiers and regressors in cosmic-ray, gamma-ray and neutrino instruments:
- **space-borne:** magnetic spectrometers, calorimetric telescopes, pair-conversion telescopes;
- **ground-based:** air-shower arrays, imaging atmospheric Cherenkov telescopes (IACTs), neutrino telescopes.

This file has no experiment facts. The detector, its estimators, its periods and its published procedures come from
the bound profile, read through the context-resolution steps in `SKILL.md`. Read only the modules the task needs,
typically those on:
- subsystems and observables (the estimators the classifier uses or replaces);
- the species and their backgrounds;
- efficiency, acceptance and background methods;
- reconstruction and data quality;
- time-dependent analysis periods.

When no profile is bound, say so and apply the general discipline below. Analysis principles (weights, metrics,
decorrelation) are in [ml-analysis.md](ml-analysis.md).

## How these measurements differ from collider analyses

| Aspect | Collider analysis | Astroparticle flux or spectrum measurement |
|---|---|---|
| Signal and background | Process cross sections | Particle species in a cosmic-ray beam with steeply falling power-law spectra; spectral indices and features (hardenings, softenings) come from the bound profile with their sources |
| Class imbalance | Set by cross sections | Often several orders of magnitude, varying with rigidity or energy (rare antimatter or γ against a proton or hadron background) |
| Truth labels | Simulation truth | Simulation truth *and* data-driven pure samples tagged by other subdetectors |
| Time | Run periods | Continuous operation over years: orbit, temperature, gas, gain and solar-modulation variations |
| Classifier output used as | A selection cut or a fit observable | A cut whose efficiency enters the flux, or a template-fit observable per rigidity or energy bin |
| Normalization | Luminosity | Exposure: acceptance × live time × trigger efficiency, with geomagnetic cutoff and pointing |

## Typical tasks

- **Particle identification:**
  - electron or positron against proton: transition radiation likelihoods, calorimeter shower shape, energy–momentum
    matching (E/p);
  - photon against hadron: IACT image parameters or full images, air-shower array observables;
  - neutrino flavor or topology: track against cascade.
- **Charge (Z) identification:** combine several dE/dx-type measurements (tracker layers, time-of-flight, Cherenkov,
  calorimeter). The background is the neighboring charges, through resolution and through fragmentation in the
  material above the measuring layers. Treat it as ordinal: a confusion with Z ± 1 differs from a gross error.
- **Charge-sign confusion** in magnetic spectrometers: at high rigidity mainly finite rigidity resolution (towards
  the maximum detectable rigidity); at all rigidities, interactions, large-angle scattering, delta rays and wrong hit
  association. The measured sign flips, so the far more abundant opposite-sign species leaks into the rare sample. Classifiers on
  track-quality features (fit χ², rigidities from different hit subsets, nearby hits, cross-detector charge
  consistency) estimate it; the profile states what the experiment actually uses.
- **Regression:** energy (calorimeter leakage, shower containment), rigidity resolution modeling, direction
  (IACT/array arrival direction), interaction depth.
- **Isotopes:** mass from velocity (Cherenkov, time of flight) and rigidity. Velocity resolution dominates;
  classifiers mostly help with background rejection and quality selection.

## Labels and training samples

- **Simulation truth is not free of ambiguity.** A nucleus that fragments in the upper detector has one charge at
  the top and another at the bottom. Define the label at the layer the measurement refers to, and record that
  definition.
- **Data-driven training samples.** Pure samples selected in data with *other* subdetectors (for example protons
  selected by a different identification system) avoid simulation mismodeling. The tagging and classifier inputs
  must be independent; otherwise the efficiency measured with the tag is circular. This is the circularity failure
  the profile warns about.
- **Test-beam data** gives true labels at fixed energies, positions and particle types. It is a domain-shift check
  against flight data, not a substitute for it: the conditions, the incidence angles and the backgrounds differ.
- **Selection consistency.** Train with the same preselection the analysis uses, including the geomagnetic-cutoff
  selection. That selection changes the rigidity-dependent composition of the sample.

## Splits and time dependence

- **Group by time.** Detector conditions drift (temperature, gas gain, calibration constants) and the environment
  varies (solar modulation, orbit, the South Atlantic Anomaly). Group splits by the period unit the analysis uses
  (calibration epoch, Bartels rotation, run). Do not mix events from the same short period across train and test.
- **Check stability over time.** For each period, show the classifier output in control samples and the efficiency
  at the working point. A time-resolved flux needs the efficiency per time bin, not one average.
- **Check stability in instrument variables.** Incidence angle and impact position (edges, dead regions, layer
  patterns) matter because the acceptance is geometric.

## Detector configuration change (eras)

When the instrument changes during the mission (an added tracking layer, a replaced subsystem, a new calibration
scheme), the periods before and after are different domains; the bound profile names the eras, never memory. Options:
per-era training, era conditioning (era as an input), common features only (inputs present in every era), or
missing-feature indicators for inputs that exist in one era only. Keep per-era calibration and per-era working
points chosen at the same signal efficiency, and use efficiencies measured in data for each era (control samples per
period), because the simulation of a new configuration is the least validated. Splits group by period within era.
The executable BDT path (cross-training, negative weights, working points) is `train_bdt.py`, described in
[multivariate-analysis-bdt-nn.md](multivariate-analysis-bdt-nn.md); the robustness view is in
[robustness-and-distribution-shift.md](robustness-and-distribution-shift.md).

## Steep spectra, rigidity dependence, and the working point

- **Training weight.** The training sample is dominated by the lowest rigidity or energy bins. Train flat in log
  rigidity (training weights), give rigidity as an input (a parameterized network, [ml-analysis.md](ml-analysis.md)),
  or train per range. Spectral features (hardening, cutoff regions) change the composition with rigidity; a flat
  training weight hides them, so check performance per bin.
- **Evaluation.** Evaluate and choose working points per rigidity or energy bin. One global cut gives a strongly
  energy-dependent efficiency and background.
- **Migration.** The classifier efficiency enters the flux denominator together with acceptance, live time and
  trigger efficiency, and resolution migrates events between bins. The efficiency must be defined in the same
  (measured or true) variable as the unfolding step; coordinate with hep-measurement and hep-statistics.

## Efficiency and background from the classifier

- **Efficiency on data.** Measure the signal efficiency at the working point on data control samples (tag-and-probe
  across subdetectors), per bin and per period. Use simulation only for the data/simulation ratio and its
  uncertainty.
- **Template fits.** When the classifier output is a fit observable, the templates come from data control samples
  where possible, else simulation with its uncertainty. Finite template statistics need a bin-by-bin treatment
  (Barlow–Beeston type, owned by hep-statistics).
- **Charge-confusion background.** Estimate it from the classifier's distribution in a confusion-enriched control
  sample, validated against simulation and test beam where the profile documents it.
- **A data/simulation shape mismatch is not a validation success.** If the template fit absorbs it, quantify how much
  and propagate it as a systematic.

## Ground-based specifics

- **IACTs:**
  - gamma/hadron separation and energy and direction regression from images;
  - mismodeling of the night-sky background, the atmosphere and the telescope optics is the main domain shift;
  - off-source and run-wise simulations are the usual controls.
  - The instrument side is in `hep-detector/references/imaging-atmospheric-cherenkov.md`.
- **Air-shower arrays and neutrino telescopes:**
  - graph networks on irregular sensor layouts;
  - check the sensor-level noise models and ice or water optical properties against calibration data;
  - test performance against sensor outages, because detector configurations change over the years.

## Deliverables

- the `ml-artifact` with the label definition (and the detector layer it refers to), data-driven versus simulation
  training samples, the time grouping key, the rigidity or energy training domain and training weights;
- efficiency at the working point per bin and per period on data, with uncertainty;
- data/simulation comparisons of the output in control samples;
- the background estimate built on the classifier and its validation;
- the profile modules read, and anything the profile did not cover, stated as such.
