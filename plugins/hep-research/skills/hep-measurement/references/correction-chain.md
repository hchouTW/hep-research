# Correction chain: from counts to the estimand

Every measured rate, flux or cross section is a count corrected by a chain of factors. Write the chain down once, with
each factor's conditional denominator, before any number is computed; the `corrections` ledger of the
[measurement spec](../assets/measurement_spec.template.md) records it, and `contracts/validate.py` checks that each
factor appears once (`_measurement_semantics`, codes `measurement.duplicate_correction`,
`measurement.correction_category_repeated`, `measurement.normalization_double_counted`). The response object itself
(migration, efficiency inside a matrix) belongs to hep-detector; this file is the measurement-design view.

## Generic forms

| Domain | Estimand per bin i | Normalization kind |
|---|---|---|
| Space or ground-based cosmic rays | `Phi_i = (N_i - B_i) / (A_i eps_i T_i dR_i)` (acceptance A, efficiency eps, live time T, bin width dR in the flux's unit) | `exposure` (A x T) or `live-time` |
| Collider, fiducial | `sigma_fid = (N - B) / (L C)`, `C` = reconstructed / generated in the fiducial region | `integrated-luminosity` |
| Neutrino beam | `sigma_i = (N_i - B_i) / (eps_i Phi_nu N_targets)`, with the integrated flux `Phi_nu` per proton on target times the POT | `protons-on-target` |
| Rare event, target | rate = `(N - B) / (eps M t)` per target mass M and time t | `target-exposure` |

The normalization kind is declared once in `observable.normalization`; the same quantity is never also a correction in
the chain (a luminosity correction next to an `integrated-luminosity` normalization divides by L twice).

## Factorized efficiency

Write the efficiency as conditional factors, each with its denominator:

`eps = eps_trigger(| reconstructed, selected) x eps_reco(| in acceptance) x eps_sel(| reconstructed)`

or in the order the selection is applied; what matters is that each factor's denominator is the numerator of the
previous one. In the spec, give each factor its own category (`trigger_efficiency`, `reconstruction_efficiency`,
`selection_efficiency`, `identification_efficiency`, or a profile's `<ns>:<term>`); a bare `efficiency` next to any of
them is the same efficiency counted twice and fails validation.

**Factorization bias.** The product equals the total only if the factors are independent given the denominator. Test
it: measure the total directly on a sample where that is possible (simulation truth, or an orthogonal-trigger
sample) and compare with the product, binned in the variables that drive both factors (for example the trigger and the
reconstruction both depending on the track multiplicity). A significant difference is either corrected (measure the
factors jointly in bins of the common variable) or carried as a systematic.

**Data/simulation efficiency ratio.** When the efficiency comes from simulation, correct it with a scale factor
`SF = eps_data / eps_sim` measured on a control sample (tag and probe, an unbiased trigger stream), in the same bins and
with the same denominator. Its systematic comes from the control-sample statistics, the background under the probe,
the tag definition, and the extrapolation from the control kinematics to the signal kinematics. Apply SF to the
simulated efficiency once; a selection already reweighted by SF in the event weight must not be divided by it again.

## Worked example (synthetic)

All numbers invented. A flux bin with N = 40 selected events, B = 4 expected background (known), acceptance
A = 0.05 m^2 sr, live time T = 1.0e5 s, bin width dR = 10 GV, and factors eps_trigger = 0.90, eps_reco = 0.80,
eps_sel = 0.75 (each relative to the previous step): eps = 0.54, exposure A T = 5.0e3 m^2 sr s, and
`Phi = (40 - 4) / (5.0e3 x 0.54 x 10) = 1.333e-3 (m^2 sr s GV)^-1`. The interval comes from the counts:
`cosmic_ray_flux.py --counts 40 --background 4 --exposure 2.7e3 --bin-width 10 --bin-width-unit GV` (exposure x
efficiency = 2.7e3) prints flux 1.333e-3 with its Feldman-Cousins interval. If eps_sel had instead been quoted relative to all events in the acceptance (0.54
already includes the trigger and reconstruction), multiplying it with the other two would give eps = 0.389 and a flux
1.39 times too high: the denominator, not the number, decides.

## Time-dependent measurements

- **Per-period exposure and live time.** Each period (run, day, Bartels rotation of 27 days for solar-modulation
  studies) has its own live time, acceptance-weighted exposure and, near a geomagnetic cutoff, its own cutoff-filtered
  exposure per bin. The flux of a period is that period's counts over that period's exposure.
- **Averaging periods.** The average flux over periods is `sum_p N_p / sum_p E_p` (exposure-weighted), not the mean of
  the period fluxes; the two differ whenever the exposures differ, and the plain mean over-weights short periods.
- **Efficiency in time.** Detector efficiencies drift (gain, dead channels, thresholds). Measure them per period, or
  monitor them with a control species or a control sample whose true rate is stable over the period, and correct or
  bin in time where the monitor moves beyond its statistics.
- **Systematics by period.** Separate the period-correlated part of each systematic (a common calibration, the
  acceptance model) from the period-specific part (a per-period efficiency fit). The correlation pattern is evidence
  for hep-statistics, which encodes it in the time-series covariance.
- **Period agreement as a null test.** Agreement of fluxes between periods in a range where no physical variation is
  expected (for cosmic rays, high rigidity above the solar-modulation range) tests the time-dependent corrections only
  after arguing that instrument, exposure, composition and other time effects are controlled there. It is a check
  within one experiment, not a general oracle across experiments.

- **Collection time.** Near a cutoff, the normalization of a bin is its collection time T: the live time of the
  periods in which the bin lies above the cutoff threshold (cutoff x a declared safety factor), times the acceptance
  for the exposure (catalog composition `exposure_acceptance_livetime_transmission`: acceptance x `livetime` x
  `cutoff_transmission`). Declare everything: the period key, duration, live fraction, quality cuts, the cutoff column
  and safety factors, the variable and time binning, and the eras; nothing has a default. Count a period split across
  files once, refuse overlapping periods and periods that cross an era or time-bin boundary, and report how many
  periods each condition removed. T must not grow when the safety factor grows. "Collection time" is this quantity
  in seconds; the contracts' `exposure_record` is the blinding record of data exposure, a different thing.
  `scripts/collection_time.py` computes it (`accumulate`, `--emit-partial` and `merge`, which agree with a single
  run); the generic pattern for partitioned time-sliced records is in
  `<plugin root>/skills/hep-computing/references/analysis-data-pipelines.md`.

Worked example (synthetic): period 1 has N = 100 in exposure 1.0e4, period 2 has N = 30 in exposure 2.0e3 (a short
period). Fluxes 1.0e-2 and 1.5e-2; the exposure-weighted average is 130 / 1.2e4 = 1.083e-2, while the plain mean of the
two fluxes would be 1.25e-2, 15% higher.

## Nuclei and isotopes

- **Survival probability.** A nucleus crossing material of grammage x survives without an inelastic interaction with
  probability `P = exp(-x / lambda_int)`, with lambda_int the interaction length of that nucleus in that material; the
  top-of-instrument flux divides by P for the material above the measuring layers. lambda_int comes from measured
  cross sections or a validated simulation, per species and energy; its uncertainty is a systematic.
- **Fragmentation in the detector and above it.** A heavier nucleus that fragments in the upper material can be
  reconstructed as a lighter one (for example carbon into boron), so the lighter species gains a feed-down background
  `N_feed = N_heavy (1 - P_heavy) f(heavy -> light)`, with f the partial fragmentation fraction into that species;
  subtract it, or fit the charge measured in several layers to tag fragmentation before the last layer.
- **Charge-ladder leakage.** Charge resolution spreads each species into its neighbours (Z +- 1); fit the charge
  templates of the neighbouring species together, and take the template tails from data where possible.
- **Isotopes.** Separating isotopes needs mass, so velocity and rigidity (or energy) both enter; the mass resolution
  degrades with gamma, so the isotope ratio has a limited energy range set by the resolution, not by the statistics.

Worked example (synthetic, invented interaction lengths): with x = 10 g/cm2 above the detector and lambda_int =
20 g/cm2 for the light species, P = 0.607 and the flux is corrected by 1/P = 1.65. If 1000 heavy nuclei arrive with
P_heavy = 0.55 and 10% of their fragments are reconstructed as the light species, the feed-down is
1000 x 0.45 x 0.10 = 45 events, to be subtracted before the survival correction.

## Neutrino and fixed-target specifics

- **Protons on target.** The normalization is the integrated POT of the selected spills (beam-quality and detector-live
  requirements applied to the same spills as the events), declared as the `protons-on-target` normalization kind.
- **Near/far extrapolation.** Predict the far-detector spectrum from the near-detector data times a far/near ratio from
  simulation (or a fit that shares the flux and cross-section parameters); flux and cross-section uncertainties that are
  common to both detectors largely cancel in the ratio, while detector-specific efficiencies, acceptance and energy
  scales do not. Record which parts are correlated between the detectors: that is evidence for hep-statistics.
- **Flux and cross section are correlated.** A measured event rate constrains flux x cross section; a cross-section
  measurement takes the flux from an external prediction or constraint, and its uncertainty must not be counted again
  through a flux systematic.
- **Target thickness and absorption.** For a target of length L and interaction length lambda, the beam is attenuated
  inside the target; the effective thickness is `L_eff = lambda (1 - exp(-L / lambda))`, not L.
- **Empty-target subtraction.** Subtract the target-out (empty-target) rate scaled to the same POT; its statistical
  uncertainty and any difference in beam conditions enter the background.

Worked example (synthetic): 1000 events in 1.0e12 POT with the target in and 100 events in 5.0e11 POT with it out give
1000 - 100 x 2 = 800 target events; a 2 cm target with lambda = 40 cm has L_eff = 1.951 cm, 2.5% less than its length.

