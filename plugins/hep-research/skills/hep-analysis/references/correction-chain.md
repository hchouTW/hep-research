# Correction chain: from counts to the estimand

Every measured rate, flux or cross section is a count corrected by a chain of factors. Write the chain down once, with
each factor's conditional denominator, before any number is computed; the `corrections` ledger of the
[measurement spec](../assets/measurement_spec.template.md) records it, and `contracts/validate.py` checks that each
factor appears once (`_measurement_semantics`, codes `measurement.duplicate_correction`,
`measurement.correction_category_repeated`, `measurement.normalization_double_counted`). The response object itself
(migration, efficiency inside a matrix) belongs to detector-response; this file is the measurement-design view.

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

Worked example (synthetic): period 1 has N = 100 in exposure 1.0e4, period 2 has N = 30 in exposure 2.0e3 (a short
period). Fluxes 1.0e-2 and 1.5e-2; the exposure-weighted average is 130 / 1.2e4 = 1.083e-2, while the plain mean of the
two fluxes would be 1.25e-2, 15% higher.

