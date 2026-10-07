# Galactic cosmic-ray propagation: models, inputs and what a fit can constrain

Purpose: give propagation questions (secondary-to-primary ratios, antiparticle backgrounds, spectral breaks, solar
modulation) a structured answer instead of memory. Propagation fits are outside v1: there is no validated propagation
profile and no propagation code in the plugin, so a request for a fit gets the "no validated domain profile" notice
and this reference is used to state assumptions, degeneracies and what the data can and cannot decide. Statistical
work on a fit (likelihood, nuisance parameters, correlated data) belongs to hep-statistics; measured fluxes come from
dataset records, never from memory.

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

## Inputs that dominate the uncertainty

- **Production (spallation) cross sections** of secondaries (for example B from C and O, including ghost-nucleus
  chains) are measured sparsely in energy and channel; their uncertainty is often comparable to or larger than the
  statistical precision of modern secondary-to-primary ratios and must be carried as nuisance parameters, not fixed.
- **Interstellar gas** (H, He, molecular hydrogen tracers) normalizes the grammage; its uncertainty is degenerate
  with the transport normalization.
- **Source spectra and abundances** for each species, including whether species share one injection index.
- **Antiparticle production** (antiprotons, positrons) from cosmic rays on gas needs pp, pA and AA production cross
  sections, often extrapolated; the secondary prediction is a background estimate only as good as these inputs.

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

## Tool coverage (honest status)

Common propagation codes include GALPROP, DRAGON and USINE. None of them is installed, run or verified in this
plugin: they are named only so that a user can state which code produced a number. No propagation result in this
plugin is tested, and no capability row claims one.
