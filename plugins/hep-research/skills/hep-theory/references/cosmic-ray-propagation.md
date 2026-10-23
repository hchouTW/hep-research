# Galactic cosmic-ray propagation: models, inputs and what a fit can constrain

Purpose: give propagation questions (secondary-to-primary ratios, antiparticle backgrounds, spectral breaks, solar
modulation) a structured answer instead of memory. Three narrow theory-domain profiles exist (secondary-to-primary
ratios in a weighted-slab and a 1D thin-disc diffusion model; the secondary antiproton source term; force-field solar
modulation, derived and benchmarked against the hep-measurement script), and hep-statistics
fits grid parameters to a measurement from tabulated predictions (`covariance_fit.py`, model `tabulated-grid`, with the
degenerate directions reported); both are demonstrated on synthetic data, the antiproton pp source term also against a
published table (12 of 15 entries; `docs/capability-matrix.md`). There is no propagation code in the plugin core (the
optional DRAGON2 adapter drives an external build; see Tool coverage below): a global fit that runs one (many
species, reacceleration, convection, a code's own nuclear network) gets the "no validated domain profile" notice, and
this reference is used to state assumptions, degeneracies and what the data can and cannot decide. Statistical
work on a fit (likelihood, nuisance parameters, correlated data) belongs to hep-statistics; measured fluxes come from
dataset records, never from memory. Code parameter conventions, production cross-section sets and their nuisance
schemes and the nuisance structure of a global fit are in [cosmic-ray phenomenology](cosmic-ray-phenomenology.md);
modulation beyond the force field (with Bartels-rotation alignment) in
[solar modulation models](solar-modulation-models.md); dark-matter and pulsar interpretations in
[cosmic-ray new physics](cosmic-ray-new-physics.md).

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
- **Secondary-to-primary ratios.** Secondaries (B, sub-iron) are made by spallation of primaries on the interstellar
  gas, so a ratio such as B/C measures the path length traversed. A ratio falling with energy shows that higher-rigidity
  particles escape faster (a rigidity-dependent diffusion coefficient), independently of the source spectrum: the
  standard way to separate a propagation effect from an acceleration-spectrum effect.
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
- Code: `<plugin root>/skills/hep-measurement/scripts/solar_modulation_force_field.py` implements it in total kinetic
  energy with the shift |Z| phi, and takes kinetic energy per nucleon or rigidity input and a tabulated local
  interstellar spectrum (owned by hep-measurement; conversions through `core/kinematics/relativistic.py`). A
  theory-domain profile in `profiles/registry.json` holds the derivation, the validity table and a closed-form
  benchmark of a power-law spectrum against this script (synthetic). Do not add a second implementation under
  hep-theory.

### Charge-sign-dependent modulation

- Limits of drift effects. Gradient and curvature drifts in the heliospheric magnetic field move particles of opposite
  charge sign along different paths, and which sign is favoured depends on the polarity of the Sun's polar field. The
  force-field formula has no drift term; a different phi for each charge sign (Cholis et al., above) absorbs the
  difference into an effective parameter only. Such a phi is a fit parameter, not a measured potential, and it does
  not carry over from one polarity era to the other. Ratios of opposite-sign species (antiprotons or positrons to their
  matter partners) are where this matters most; for them the force field gives a guide, not a prediction, and a
  numerical heliospheric model with drifts is the tool (none ships here: say so).
- Segment by polarity era. Split time-resolved data at the polar-field reversals and fit or compare each era on its
  own. Around a reversal the field is disordered and neither era's pattern applies: keep those periods as a separate
  transition segment, not averaged into either era. Name the reversal dates and their source.
- One phi per period. Within an era, fit one phi per time period (per charge sign if both signs are fitted), never one
  phi across periods or across a reversal. Report the period edges and the era of each.
- Reversal dates come from a source, not from memory. For solar cycle 25, Li et al. (arXiv:2606.15259, abstract read
  2026-10-17) find from Hinode vector magnetograms that the northern polar field changed from positive to negative and
  the southern from negative to positive, and that the polarity reversals of the northern and southern polar caps
  (above 70 deg latitude) "likely occurred in November 2024 and October 2024, respectively". Quote it with that hedging;
  other methods (other instruments, other latitude cuts) date reversals differently.
- The heliospheric-modulation profile (the theory-domain profile above, which holds the force-field derivation)
  covers the force field only; it gives no drift model and no reversal dates.

## Inputs that dominate the uncertainty

- **Production (spallation) cross sections** of secondaries (for example B from C and O, including ghost-nucleus
  chains) are measured sparsely in energy and channel; their uncertainty is often comparable to or larger than the
  statistical precision of modern secondary-to-primary ratios and must be carried, not fixed: as a normalization
  nuisance, or a choice among sets as model alternatives with an envelope.
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

## Electron and positron energy losses

Electrons and positrons lose energy fast enough that their losses, not escape, set how far they travel. For an
isotropic electron of Lorentz factor gamma (Moderski et al. 2005, Eqs. 1, 3, 7, A10, A12; they write gamma^2, the
ultra-relativistic limit of the exact beta^2 gamma^2 = gamma^2 - 1 used here and in the script):

- synchrotron: b_sync = (4/3) sigma_T c (gamma^2 - 1) U_B, with U_B = B^2 / 8 pi (Gaussian units);
- inverse Compton on a photon field of energy density U: b_IC = (4/3) sigma_T c (gamma^2 - 1) U F_KN, where
  F_KN = 1 in the Thomson limit b~ = 4 gamma eps0 / (m_e c^2) << 1 and falls as (9 / 2 b~^2)(ln b~ - 11/6) for
  b~ >> 1 (Klein-Nishina). A Planck field is well approximated as mono-energetic at eps0 = 2.8 kT. The closed form
  F_KN = (1 + b~)^-1.5 is within 3% for b~ <= 1 but up to a factor 3 off at b~ = 1e4: state which one was used;
- loss time tau = E / b, and diffusion distance sqrt(4 D tau) with D at that energy. In the Thomson limit
  tau is proportional to 1/E, so high-energy electrons come from nearby sources.

`<plugin root>/skills/hep-theory/scripts/lepton_energy_losses.py` computes these per energy for declared fields (no
built-in field values, magnetic field or diffusion coefficient). Ionization, bremsstrahlung and adiabatic losses are
not included; it gives rates, not a transport solution.

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

Common propagation codes include GALPROP, DRAGON and USINE. One of them now runs through the optional
`adapters/cr-propagation` (owned by hep-computing): DRAGON2 (cosmicrays/DRAGON2-Beta_version, commit cd588707, built
from source on E2) is `tested-in-declared-environment` for running a JSON run spec and converting the local spectrum
into one grid-node `prediction` per run, which the comparison gate and `covariance_fit.py` model `tabulated-grid`
consume unchanged. GALPROP and USINE are `proposed`: not installed, run or verified, named only so that a user can
state which code produced a number.

What the DRAGON2 runs establish is narrow (convection, reacceleration, energy losses and decay off; the profile's
ILLUSTRATIVE production cross sections substituted through DRAGON2's data table; recorded outputs replayed in
`tests/adapters/test_cr_propagation.py`, criteria fixed before the comparison). Against the 1D thin-disc closed form of
the secondary-ratio theory profile: the high-energy slope of B/C agrees (difference 0.006, tolerance 0.05); the absolute B/C
agrees within the declared 30% (DRAGON2 9-12% higher at 10-1000 GeV/n, mostly its fixed helium target, He/H = 0.11);
the D0/L degeneracy holds within 2% between L = 2 and 4 kpc but fails at L = 8 kpc (15-18% low, tolerance 10%) because
of the radial boundary at 20 kpc and the radial gas structure, which the closed form does not have. With the boundary at
60 kpc and the gas made uniform in R (a local diagnostic patch of DRAGON2), DRAGON2 reaches the closed form: within 2%
between L = 2, 4 and 8 kpc and within 5% in absolute B/C once its helium production term is divided out (post-hoc
diagnostics with no tolerance declared in advance, not DRAGON2 as released; the declared C2 still fails). A five-node D0
grid of DRAGON2 runs recovers the D0 of a sixth run within 2% through `tabulated-grid`. DRAGON2's ASCII columns are per
total kinetic energy, not per nucleon: a ratio of species with different mass numbers needs each column multiplied by
A, which `dragon2_to_prediction.py` does (a first version did not, and reported a 32-34% B/C excess made mostly of
DRAGON2's helium target (a factor 1.143) and this unit (about 1.19)). So results from DRAGON2 and from the closed form
are different models: compare them only with the geometry, gas, target and cross sections stated. No propagation code is
used in a fit to real data, and a global fit that runs a propagation code stays outside v1.

The closed-form secondary-ratio and source-term benchmarks of the two theory-domain profiles, and the grid fit with its
end-to-end example (`examples/bc-propagation-fit`, synthetic B/C data, D0/L recovered and the flat direction reported),
remain at demonstrated-on-synthetic-data. No fit to real data is tested.

## Sources read (for the kinematics, force-field, antiproton and lepton-loss sections; on 2026-10-13 unless dated)

- L.J. Gleeson and W.I. Axford, "Solar modulation of galactic cosmic rays", ApJ 154 (1968) 1011,
  https://articles.adsabs.harvard.edu/pdf/1968ApJ...154.1011G (scan); Secs. I-III, Eqs. (5), (11), (13)-(16).
- C. Ghelfi, F. Barao, L. Derome, D. Maurin, A&A 591 (2016) A94, arXiv:1511.08650; Sec. 2.1, Eq. (1).
- I. Cholis, D. Hooper, T. Linden, arXiv:1511.01507v3; Sec. I, Eq. (1), pp. 1-2.
- Y. Li, S. Yang, Y. Zhang, Q. Song, G. Zhou, Y. Deng, J. Wang, "Polarity Reversal of the Polar Magnetic Fields in
  Solar Cycle 25", arXiv:2606.15259 (2026); abstract page only, read 2026-10-17 (body not read).
- M. di Mauro, F. Donato, A. Goudelis, P.D. Serpico, PRD 90 (2014) 085017, arXiv:1408.0288v3; Secs. I, II, IV, V.
- R. Moderski, M. Sikora, P.S. Coppi, F. Aharonian, MNRAS 363 (2005) 954, arXiv:astro-ph/0504388; Secs. 2.1, 2.2 and
  Appendix A (Eqs. 1-3, 7, A1-A12), read 2026-10-17.
- M.W. Winkler, JCAP 02 (2017) 048, arXiv:1701.04866v1; Secs. 2, 3, 8, 9, 10.
- M. Korsmeier, F. Donato, M. Di Mauro, PRD 97 (2018) 103019, arXiv:1802.03030v2; Secs. I-V.

The other sections of this file predate these sources and cite none; read them as guidance, not as verified claims.
