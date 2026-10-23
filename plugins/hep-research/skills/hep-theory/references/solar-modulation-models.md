# Solar modulation models beyond the force field

Purpose: modulation models with more structure than the one-parameter force field, the inputs they need, and how to line
a model up with time-resolved fluxes (monthly, per Bartels rotation, daily). The force field itself (derivation,
validity, drift limits, polarity-era segmentation, sourced reversal dates) is in [cosmic-ray
propagation](cosmic-ray-propagation.md), "Force-field solar modulation"; the code is the hep-measurement force-field
script named there. No drift or numerical heliospheric model ships in the plugin. Experiment time bins and periods come
from the bound experiment profile or a dataset record. Part of [cosmic-ray phenomenology](cosmic-ray-phenomenology.md).
Sources were read in full text on 2026-10-23 (list at the end of that page).

## Models

In order of cost:

| Model | What changes | Source |
|---|---|---|
| Energy-dependent force field | phi(T) = phi_L below T_L = 0.125 GeV, phi_H above T_H = 4.65 GeV, a smooth cubic step between | Corti et al. 2016, Sec. 3, Eq. 7 (T_L and T_H fixed, not fitted) |
| Empirically modified force field | potential adjusted for protons from a few hundred MeV to tens of GeV; the plain phi depends on the LIS, the energy range and the solar magnetic epoch | Gieseler, Heber and Herbst 2017, abstract |
| Analytic charge-sign and rigidity dependence | Phi(R,t) = phi0 B/4nT + phi1 H(-qA) (B/4nT) (1 + (R/R0)^2)/(beta (R/R0)^3) (alpha/(pi/2))^4, B the field at Earth, alpha the tilt angle, H the step function | Cholis, Hooper and Linden 2016, Eq. 12 (best fit phi0 = 0.35 GV, phi1 = 3.9 GV, R0 = 0.5 GV) |
| Extended force field with drifts | semi-analytic, two scale factors tied to moving averages of tilt angle and field strength; validated against a numerical code | Kuhlen and Mertsch 2019, abstract, Eq. 5 and the correlation paragraph after "Validation" |
| Numerical transport | Parker equation: convection, drifts, diffusion, adiabatic energy change (Potgieter 2013, Sec. 4.1, Eq. 5); HelMod: 2D Monte Carlo with symmetric and antisymmetric diffusion tensor | Potgieter 2013; Della Torre et al. (arXiv:1612.08445), abstract |

- **phi depends on the LIS.** The force-field potential has no absolute meaning: it depends on the assumed local
  interstellar spectrum (Usoskin et al. 2017, Sec. 6.3; Gieseler, Heber and Herbst 2017, abstract). The 2011 and 2017
  series, which differ in LIS, yield function and calibration, are related tightly but slightly nonlinearly (Usoskin
  et al. 2017, Sec. 6.3, Fig. 10). Never
  mix phi values from different LIS, and never use a published phi series with another LIS without converting.
- **phi series are recalibrated.** A neutron-monitor reconstruction from 1951 was recalibrated with a new yield
  function and a new LIS (the Vos and Potgieter 2015 form, as used there) against satellite proton spectra of
  2006-2010 in 47 intervals; its values are not to be
  compared directly with older series (Usoskin et al. 2017, abstract and Sec. 6.3). A published phi carries its LIS
  and its series version.
- **Time dependence and lag.** Time-dependent models take heliospheric inputs (tilt angle, field magnitude, sunspot
  number). The flux lags solar activity: 8.1 +- 1.2 months (a +-0.8-month systematic is included in that error) in one global proton
  fit, 2000-2012, an A < 0 period (Tomassetti et al. 2017, abstract and Sec. 3). Cholis et al. average B and alpha over
  the 3 months before each data period for qA > 0 and over 3-12 months for qA < 0, depending on B and alpha (Sec. IV).
  Treat the lag or window as a model parameter with its period of validity, not a constant.
- **Tilt-angle inputs.** The Wilcox Solar Observatory gives tilt angles every 10 days from two reconstructions,
  "model L" (classic) and "model R"; one study takes a smoothed model R as default and the L-R difference as a
  systematic (Tomassetti et al. 2017, Sec. 2). Both are potential-field models of the photospheric field: L with a
  line-of-sight boundary and a polar-field correction, R with a radial boundary and a higher source surface (3.25),
  which gives a flatter current sheet and usually lower tilts; the observatory calls L probably the better estimate,
  and values above 70 degrees are lower limits (WSO tilt-angle page, read 2026-10-23). State which model and smoothing
  were used.
- **Charge sign.** A > 0 denotes the epochs when the solar polar field points outward in the northern hemisphere,
  A < 0 inward (Potgieter 2013, Sec. 2.2.1; Cholis et al. 2016, Sec. II). In the Cholis et al. form the drift term
  acts only for qA < 0; Kuhlen and Mertsch state that for qA > 0 particles arrive mostly from polar, for qA < 0 from
  equatorial directions. Opposite-sign species need the drift-aware models above, per polarity era.

## Lining a model up with time-resolved data

Monthly, per Bartels rotation or daily:

1. Take the time bins exactly as published (dataset record or the bound experiment profile's time-dependent
   module). A Bartels rotation is 27 days counted from 1832-02-08; calendar months are not rotations: never
   mix the two in one series.
2. Average each heliospheric input over the same window shifted by the stated lag (or over the stated preceding
   window, as in Cholis et al.): `bartels_rotation.py average` (coverage reported; a rotation below the declared
   minimum makes the run incomplete).
   `bartels_rotation.py rotation` and `dates` convert dates and rotation numbers.
3. Use the binning variable of the data (rigidity or energy per particle or per nucleon) and convert with the shared
   kinematics module, not by hand.
4. Keep the LIS shared across all periods and charge signs; let only modulation parameters vary per period (and per
   sign or polarity era).
5. Fit the periods jointly with the cross-period covariance: hep-statistics, "Joint fits of several periods".

## What to report

The model (row of the table above) and its parameters; the LIS and its source; the phi series and its version if one
is used; the inputs (tilt-angle model, field data), their averaging window and lag; the time bins and binning
variable of the data; one parameter set per period and sign or polarity era; the joint-fit covariance.
