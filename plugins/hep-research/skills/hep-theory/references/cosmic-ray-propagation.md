# Galactic cosmic-ray propagation: models, inputs and what a fit can constrain

Purpose: give propagation questions (secondary-to-primary ratios, antiparticle backgrounds, spectral breaks, solar
modulation) a structured answer instead of memory. Propagation fits are outside v1: there is no validated propagation
profile and no propagation code in the plugin, so a request for a fit gets the "no validated domain profile" notice
and this reference is used to state assumptions, degeneracies and what the data can and cannot decide. Statistical
work on a fit (likelihood, nuisance parameters, correlated data) belongs to hep-statistics; measured fluxes come from
dataset records, never from memory.

## Kinematics and units

Conversions among rigidity R, momentum, total energy, kinetic energy and kinetic energy per nucleon, of bin edges
(bin-average flux factor) and of point flux Jacobians are implemented once, in
`<plugin root>/core/kinematics/relativistic.py` (steward hep-theory; `python3 core/kinematics/relativistic.py --help`).
It takes |Z|, A and the mass from the caller and ships no particle constants; do not write a second converter.

- p = |Z| R (c = 1, R in GV, p in GeV/c); the charge sign does not enter (module docstring).
- Kinetic energy per nucleon is T / A with A the mass number: the force-field form E^TOA / A = E^IS / A - (|Z|/A) phi
  divides the total energy by A (Ghelfi, Barao, Derome, Maurin, A&A 591 (2016) A94, arXiv:1511.08650, Sec. 2.1, Eq.
  (1), read 2026-10-13).
- The mass passed to the converter is a choice that must be stated: the nuclear (or ion) mass, A times a nucleon
  mass, or A times the atomic mass unit differ at the per-mille level, and the difference shifts T/n at fixed R at
  low energy (`unverified`: no opened source compares the conventions; state the one used and its source).
- Flux in per-nucleon energy and flux in rigidity differ by the Jacobian dR / d(T/n); a bin-averaged flux converts
  with the ratio of bin widths, not with the point Jacobian (both are in the module; tests in
  `tests/core/test_kinematics_relativistic.py`).

## The model families

- **Diffusion (transport) equation.** The standard description is a steady-state transport equation for each species
  with a source term, spatial diffusion, convection (a Galactic wind), reacceleration (diffusion in momentum, set by
  the Alfvén speed), energy losses (ionization, Coulomb; for leptons synchrotron and inverse Compton), and
  fragmentation and radioactive decay as loss and gain terms linking species. A model states which of these terms it
  keeps; "pure diffusion", "diffusion + reacceleration" and "diffusion + convection" fits of the same data give
  different transport parameters.
- **Geometry.** A cylindrical halo of half-height L with the sources and gas in a thin disc, free escape at the halo
  boundary. Two-dimensional (cylindrical) and simplified one-dimensional or semi-analytic versions are both in use.
- **Diffusion coefficient.** Usually a rigidity power law, D(R) = D0 beta^eta (R / R0)^delta, sometimes with a break
  (or a spatially dependent D) to describe the hardening of nuclear spectra at a few hundred GV; whether the break sits
  in injection or in propagation is a model choice that secondary-to-primary ratios help discriminate.
- **Leaky box and weighted slab.** Older effective descriptions (an escape length or path-length distribution). They
  reproduce stable secondary ratios but carry no spatial information, so they cannot use radioactive clocks or
  lepton losses consistently.
- **Solar modulation.** Below a few tens of GV the interplanetary heliosphere modifies the local interstellar spectrum.
  The force-field approximation has one parameter (the modulation potential phi, per time period) and ignores charge-
  sign and drift effects; numerical heliospheric models do not. Time-resolved data need a time-dependent modulation.

## Force-field solar modulation

- Gleeson and Axford derive, for a spherically symmetric heliosphere with a separable diffusion coefficient and
  negligible streaming, J(r, E, t) / (E^2 - E_0^2) = J(infinity, E + Phi) / ((E + Phi)^2 - E_0^2) with E the total
  energy, E_0 the rest energy and, for kappa_2 proportional to rigidity, Phi = |Z| e phi(r, t) (ApJ 154 (1968) 1011,
  Sec. III, Eqs. (15)-(16), pp. 1015-1016, read 2026-10-13 from the ADS scan). phi is "a single parameter describing
  the modulation" (Eq. (13), p. 1014) and has the units of a potential (their Fig. 2 abscissa in BV; a fitted shift of
  -80 MV, p. 1015).
- Per nucleon (Ghelfi et al., arXiv:1511.08650, Sec. 2.1, Eq. (1), read 2026-10-13): E^TOA / A = E^IS / A -
  (|Z| / A) phi and J^TOA(E^TOA) = (p^TOA / p^IS)^2 J^IS(E^IS), with J the flux per kinetic energy per nucleon and phi
  of the dimension of rigidity. So the per-nucleon shift is Phi_n = (|Z| / A) phi, the same physics as the
  total-energy shift |Z| phi.
- Validity: Gleeson and Axford find the approximation breaks down below about 300 MeV per nucleon for protons and
  250 MeV per nucleon for alpha particles, where streaming is no longer negligible (p. 1016, read 2026-10-13). The
  force field "does not allow for any rigidity dependent effects" and cannot predict the time dependence of the
  potential; studies often use different phi for positive and negative charges to allow charge-sign effects, and phi
  is degenerate with injection and transport parameters (Cholis, Hooper, Linden, arXiv:1511.01507v3, pp. 1-2, read
  2026-10-13). Drift (charge-sign) effects are absent from the formula: one phi per period and per charge sign at most.
- Code: `<plugin root>/skills/hep-analysis/scripts/solar_modulation_force_field.py` implements it in total kinetic
  energy with the shift |Z| phi (owned by hep-analysis; its extension to rigidity input and tabulated local
  interstellar spectra is planned there). Convert rigidity or per-nucleon inputs with
  `core/kinematics/relativistic.py` first. Do not add a second implementation under hep-theory.

## Inputs that dominate the uncertainty

- **Production (spallation) cross sections** of secondaries (for example B from C and O, including ghost-nucleus
  chains) are measured sparsely in energy and channel; their uncertainty is often comparable to or larger than the
  statistical precision of modern secondary-to-primary ratios and must be carried as nuisance parameters, not fixed.
- **Interstellar gas** (H, He, molecular hydrogen tracers) normalizes the grammage; its uncertainty is degenerate
  with the transport normalization.
- **Source spectra and abundances** for each species, including whether species share one injection index.
- **Antiparticle production** (antiprotons, positrons) from cosmic rays on gas needs pp, pA and AA production cross
  sections, often extrapolated; the secondary prediction is a background estimate only as good as these inputs
  (antiproton conventions below).

## Secondary antiprotons: source-term conventions

- **Source term.** q_ij(T_pbar) = integral over the projectile kinetic energy per nucleon T_i of 4 pi n_ISM,j phi_i(T_i)
  dsigma_ij / dT_pbar (Korsmeier, Donato, Di Mauro, PRD 97 (2018) 103019, arXiv:1802.03030v2, Sec. I, Eq. (1), read
  2026-10-13); di Mauro et al. write the pp term with threshold 7 m_p and an ISM H:He:C = 1 : 0.1 : 5 x 10^-4
  (PRD 90 (2014) 085017, arXiv:1408.0288v3, Sec. II.A, Eq. (1), read 2026-10-13). State the ISM composition and
  which projectile and target species are summed.
- **Channels.** pp gives "roughly 50-60%" of the spectrum and pHe and Hep "10-20% each" (Korsmeier et al., Sec. I,
  p. 2); helium channels "easily" reach about 50% at low energies and heavier nuclei only a few percent (di Mauro et
  al., Sec. I, p. 1). Winkler sums only p and He projectiles and targets, "the contribution from heavier nuclei is
  negligible" (JCAP 02 (2017) 048, arXiv:1701.04866v1, Sec. 9, Eq. (19), read 2026-10-13). Nuclear channels are not
  measured where they matter (pHe, HeHe) and are obtained by rescaling pp: Winkler Eq. (17) and Korsmeier et al.
  Eqs. (15)-(17) give rescaling functions with free parameters fitted to pA data. Name the rescaling used.
- **Antineutrons.** Antineutrons decay to antiprotons; their production is not measured and is estimated by isospin
  arguments. The total is written sigma = sigma_pbar (2 + Delta_IS + 2 Delta_Lambda) with Delta_IS the antineutron
  enhancement over antiprotons (Winkler Eq. (5); Korsmeier et al. Eq. (4), with Delta_IS parametrized in Eq. (5)).
  di Mauro et al. note that the traditional factor 2 assumes sigma(pp -> nbar) = sigma(pp -> pbar) and that
  kappa = 1.3 +- 0.2 "should encompass the data" (Sec. IV, p. 8, read 2026-10-13). State whether and how the
  antineutron term is included.
- **Hyperons.** Antiprotons from Lambda-bar and Sigma-bar decays are included through Delta_Lambda (Winkler Eqs.
  (6)-(7): Delta_Lambda = (0.81 +- 0.04) (Lambda-bar / pbar), with Sigma-bar / Lambda-bar = 0.33 from symmetry and a
  25% uncertainty; Korsmeier et al. Eq. (6)); data differ in whether hyperon feed-down was subtracted, so the
  treatment of each data set must be stated (di Mauro et al., Sec. II.B, p. 3; Korsmeier et al., Sec. I).
- **The parametrization is a model alternative.** Different cross-section parametrizations agree to 10-20% where
  data exist and differ by up to 50% around 1 TeV in extrapolation (di Mauro et al., abstract); Korsmeier et al. give
  up to +-20% on the total source term, dominated by p + p -> pbar + X and transmitted to all channels by the
  rescaling (abstract; Sec. IV, p. 12), and warn that a rescaled di Mauro et al. parametrization deviates in shape at
  high energy (Sec. III, p. 12). Treat a choice among parametrizations as a `model-alternative` uncertainty object,
  and a fitted parametrization's own uncertainty with its correlation matrix (Winkler Sec. 10 provides one), never as
  an independent Gaussian per bin.

## Degeneracies a fit cannot remove alone

- **D0 / L:** stable secondary-to-primary ratios constrain roughly D0 / L, not D0 and L separately. Radioactive
  secondary clocks (for example 10Be/9Be, and other unstable isotopes) break it partly; lepton energy losses and
  gamma-ray or radio data add independent handles, each with its own model assumptions.
- **delta and reacceleration / convection:** the low-rigidity shape of a ratio can be absorbed by reacceleration,
  convection, a low-energy break in D or by the modulation potential; the high-rigidity slope constrains delta more
  cleanly.
- **Cross-section normalization and grammage:** a global rescaling of secondary production mimics a change of D0 / L.
- **Breaks:** a hardening in primaries alone does not tell injection from propagation; the ratio of secondaries to
  primaries above the break does.

## What to report with any propagation statement

- The model (terms kept, geometry, diffusion parametrization, modulation treatment) and the code and version used;
  results from different codes are compared only with these stated.
- The cross-section set and how its uncertainty enters (fixed, nuisance, or alternative sets as model alternatives).
- Which data constrain which parameters, the rigidity range used, and correlated systematic uncertainties of the
  data (a fit with diagonal errors on a high-precision ratio is not credible).
- Degenerate directions explicitly (for example only D0 / L quoted), and any parameter fixed rather than fitted.
  In a `theory-spec` set `model.family` to `cosmic-ray-propagation` and list them in `degenerate_directions`
  (strings such as `D0/L`); from contracts 2.6.0 the validator reports `theory.degeneracy_missing` when the family is
  declared and the list is empty. The trigger is the declared family, never a pattern in `model.id`.

## Tool coverage (honest status)

Common propagation codes include GALPROP, DRAGON and USINE. None of them is installed, run or verified in this
plugin: they are named only so that a user can state which code produced a number. No propagation result in this
plugin is tested, and no capability row claims one.

## Sources read (for the kinematics, force-field and antiproton sections; all on 2026-10-13)

- L.J. Gleeson and W.I. Axford, "Solar modulation of galactic cosmic rays", ApJ 154 (1968) 1011,
  https://articles.adsabs.harvard.edu/pdf/1968ApJ...154.1011G (scan); Secs. I-III, Eqs. (5), (11), (13)-(16).
- C. Ghelfi, F. Barao, L. Derome, D. Maurin, A&A 591 (2016) A94, arXiv:1511.08650; Sec. 2.1, Eq. (1).
- I. Cholis, D. Hooper, T. Linden, arXiv:1511.01507v3; Sec. I, Eq. (1), pp. 1-2.
- M. di Mauro, F. Donato, A. Goudelis, P.D. Serpico, PRD 90 (2014) 085017, arXiv:1408.0288v3; Secs. I, II, IV, V.
- M.W. Winkler, JCAP 02 (2017) 048, arXiv:1701.04866v1; Secs. 2, 3, 8, 9, 10.
- M. Korsmeier, F. Donato, M. Di Mauro, PRD 97 (2018) 103019, arXiv:1802.03030v2; Secs. I-V.

The other sections of this file predate these sources and cite none; read them as guidance, not as verified claims.
