# Rare-event and neutrino measurements

Design and review points for searches with a handful of expected events (direct dark-matter detection, double-beta
decay, rare decays) and for accelerator and reactor neutrino measurements. The statistics of low counts, limits and
discovery claims belong to hep-statistics ([astroparticle statistics](../../hep-statistics/references/astroparticle-statistics.md),
[inference recipes](../../hep-statistics/references/inference-recipes.md)); oscillation probabilities to hep-theory
([neutrino oscillations](../../hep-theory/references/neutrino-oscillations.md)); detector response to hep-detector.
No experiment numbers are quoted here: a specific detector's values come from its profile, its papers, or the user.

## Exposure and live time

- **Exposure** is target mass x live time after all cuts that remove time or mass: kg y or t y (kg d in older work).
  State the fiducial mass, not the instrumented mass, and the live time after vetoes, dead time and data-quality cuts;
  a quoted exposure that mixes the two is not comparable with another experiment's.
- Keep the **exposure** (mass x time) and the **signal acceptance** (efficiency of every selection for the signal
  hypothesis, often energy dependent) as separate factors in the correction chain ([correction chain](correction-chain.md)),
  each with its uncertainty; their product enters the rate.
- For a time-varying signal (annual modulation, a source that switches on and off) the live time per time bin is the
  normalization: `collection_time.py` gives it per era and bin.

## Signal region and its choice

- The **region of interest** (ROI: energy window, fiducial volume, discrimination cut) is chosen on simulation,
  calibration data and sidebands, never on the unblinded signal region; the figure of merit (expected sensitivity,
  discovery reach) is declared before it is optimized ([analysis design](analysis-design.md)).
- A fiducial volume defined from 3D positions removes backgrounds from surrounding materials; single- versus
  multiple-scatter selection removes backgrounds a weakly interacting signal cannot produce; discrimination between
  electronic and nuclear recoils (two signals per event, or pulse shape) separates the dominant background classes.
  Each cut has a measured signal acceptance and a measured background leakage with uncertainties.
- An energy-dependent efficiency near threshold dominates the sensitivity at low masses: state the threshold
  definition and how the efficiency curve was measured (calibration source, simulation, or both).

## Blinding and salting

- Blind the ROI (or the variable that reveals the answer) until the selection, the background model, the
  uncertainties and the statistical procedure are frozen; record what was frozen and when
  ([analysis design](analysis-design.md), blinding policy).
- **Salting** injects fake signal events, unknown to the analysts, into the data; they are removed at unblinding.
  It protects against tuning the selection on a fluctuation but must not change the background model: the salt
  injection procedure, its population and its removal are documented before unblinding.
- Post-unblinding changes are allowed only for documented defects and are reported with their effect.

## Background budget

- List every background source with its expected count in the ROI and its uncertainty: radioactivity of detector
  materials and of the target itself (intrinsic and cosmogenic activation), surface backgrounds, environmental
  radiation, cosmic muons and their neutrons, and the irreducible neutrino backgrounds (elastic scattering on
  electrons, coherent scattering on nuclei) that define a floor for large exposures.
- Each estimate states its method (screening and simulation, sidebands, control samples) and is validated in a
  region that does not overlap the ROI ([backgrounds](backgrounds.md)). An unknown background is a stated limitation,
  not a zero.
- With few events, background uncertainties enter as nuisance parameters, not by subtraction.

## Energy scale and quenching

- The energy scale is calibrated with sources covering the ROI; nonlinearity and the position dependence of the
  response are systematics ([systematics](systematics.md)).
- Nuclear recoils yield less light or charge than electronic recoils of the same energy (quenching): state whether
  energies are electron-equivalent (keVee) or nuclear-recoil (keVnr), the quenching model or measurement used and
  its uncertainty; converting a threshold between the two scales goes through that model.

## Neutrino measurements: flux, cross section and near/far

- An event rate is flux x cross section x target x efficiency: the flux prediction and the neutrino-nucleus cross
  section (with its nuclear effects: kinematic, final-state and rate effects) are separate, correlated uncertainty
  sources, and both depend on energy.
- A **near detector** measures the unoscillated spectrum; the far prediction is extrapolated from it with the
  flux ratio (geometry, beam divergence), the detector and target differences and the cross-section model. Only the
  parts that differ between near and far cancel; state which uncertainties are treated as correlated between them.
- Report cross sections for what was detected (the final-state topology) where the correction to an
  interaction-level quantity relies on an uncertain nuclear model; say which.
- Oscillation-parameter inference from the spectra is hep-statistics; the probabilities are hep-theory.

## Presenting the result

- A null result is a limit (method, confidence level, whether it is a one-sided or unified interval, the background
  assumed) together with the median expected sensitivity and its bands; a positive result states its significance
  with the look-elsewhere treatment. Both go through hep-statistics.
- Publish the inputs a reinterpretation needs: exposure, efficiency curve, background model, observed events with
  their energies, and the likelihood or its approximation.

<!-- example: direct dark-matter searches -->
Illustration: liquid-xenon time projection chambers measure scintillation and ionization for each event, so they
separate electronic from nuclear recoils and reconstruct 3D positions for a fiducial volume; at the largest exposures
their electronic-recoil background at low energy is dominated by solar pp neutrinos and radon daughters (PDG Review
2026, "Dark Matter", Section 27.6.3).
<!-- /example -->

## Sources

Particle Data Group, Review of Particle Physics (2026 edition): "Dark Matter", Section 27.6.3 (direct detection
technologies, backgrounds including neutrinos), read in full; "Neutrino Cross Section Measurements", introduction and
the discussion of nuclear effects and final-state reporting, read; "Neutrino Masses, Mixing, and Oscillations",
Sections 14.3-14.5, read. All on 2026-10-17 from pdg.lbl.gov. The design rules above are method statements; they
quote no measured value.
