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

## Acceptance from generation records

An acceptance from simulation is `A(x) = G_gen N_sel(x) / N_gen(x)`: the generation factor times the fraction of the
events generated in the bin that pass the selection. The generation must be declared, not inferred: the surface (a
plane of area S, or a sphere of radius R), the angular law (the cosine law of an isotropic flux crossing the surface,
`G_gen = pi S` for one side of a plane, `pi sin^2(theta_max) S` within theta_max, `pi 4 pi R^2` for a sphere), the
generation spectrum and its range, and the number generated, including every event that missed the instrument. The
generated count per bin follows from the spectrum (`N_gen(x) = N_generated P(x)`), never from the selected sample.
`acceptance_from_generation.py` does this with a Clopper-Pearson interval per bin and stops (exit 3) when the generated
count is missing. Two checks: a one-sided flat detector in an isotropic flux has `G = pi S`; two coaxial discs of radii
R1, R2 a distance L apart have `G = (pi^2/2) [R1^2 + R2^2 + L^2 - sqrt((R1^2 + R2^2 + L^2)^2 - 4 R1^2 R2^2)]`, which
tends to `pi^2 R^2` at L = 0 (R1 = R2 = R) and to `A1 A2 / L^2` far apart (the formula is usually attributed to
Sullivan 1971; to-verify, checked here against a Monte Carlo). Reweighting to a target spectrum changes the acceptance
within wide bins; a target taken from this measurement's own flux makes the result depend on itself (iterate and
report it; the script warns).

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
  subtract it, or fit the charge measured in several layers to tag fragmentation before the last layer. The heavy
  species is measured in the same data, so the feed-down is a coupled background (`references/backgrounds.md`,
  "Coupled species"), not a fixed number.
- **Charge-ladder leakage.** Charge resolution spreads each species into its neighbours (Z +- 1); fit the charge
  templates of the neighbouring species together, and take the template tails from data where possible.
- **Isotopes.** Separating isotopes needs mass, so velocity and rigidity (or energy) both enter; the mass resolution
  degrades with gamma, so the isotope ratio has a limited energy range set by the resolution, not by the statistics.
- **Cross sections.** Their kinds (inelastic, charge-changing, production), targets and uncertainty model are in
  `<plugin root>/skills/hep-theory/references/nuclear-cross-sections.md`.

Worked example (synthetic, invented interaction lengths): with x = 10 g/cm2 above the detector and lambda_int =
20 g/cm2 for the light species, P = 0.607 and the flux is corrected by 1/P = 1.65. If 1000 heavy nuclei arrive with
P_heavy = 0.55 and 10% of their fragments are reconstructed as the light species, the feed-down is
1000 x 0.45 x 0.10 = 45 events, to be subtracted before the survival correction.

## Spectral variables

A flux measured in one variable (rigidity, as a magnetic spectrometer measures it) is often compared in another
(kinetic energy per nucleon, the variable of propagation models). The conversion is a Jacobian and a bin average,
never a relabeling of the bin edges: the target bin [y1, y2] holds
`Phi_y = (1 / (y2 - y1)) * sum_i integral over x_i(y1)..x_i(y2) of f_i(x) Phi(x) dx`, with x_i(y) the inverse map for
isotope i and f_i the isotope fraction at equal source-variable value.

- **One isotope.** With the mapped source edges as target edges the result is exact,
  `Phi_y = Phi_x (x2 - x1) / (y2 - y1)`, and the statistical covariance scales with the same factors.
- **Several isotopes.** Each isotope maps the edges differently (A and the mass differ), so the edges of an element in
  rigidity correspond to different kinetic energies per nucleon for 3He and 4He. The transform then integrates inside
  source bins and needs a declared within-bin shape (constant, or a local power law). The isotope composition is an
  input with an uncertainty, and its covariance is reported separately from the statistical one; a published
  element flux in rigidity converted with an assumed composition is model-dependent, and the comparison carries the
  composition with it.
- **Refuse what is missing.** No default Z, A, mass or composition; a target bin that needs the flux outside the
  measured range is refused, not extrapolated.

`<plugin root>/skills/hep-measurement/scripts/spectrum_transform.py` does this (masses from `core/constants`, the
variables of `core/kinematics/relativistic.py`), and writes a transformation record (variables, isotopes, masses and
their sources, composition, shape, input checksum) for the comparison gate.

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

