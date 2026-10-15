# Extensive Air Showers

Covers what happens between a primary cosmic ray entering the atmosphere and the
particle cascade that ground-based and fluorescence detectors actually measure -
the physics that
[ground-based detection arrays](ground-based-detection-arrays.md) reconstruct into
energy and `X_max`, and that
[cosmic-ray spectrum and composition](cosmic-ray-spectrum-and-composition.md) draws
composition inferences from. Everything here is a *simulated and parameterized*
cascade - no ground-based technique observes the primary particle directly.

## The Heitler-Matthews toy model

The simplest useful picture: an electromagnetic shower proceeds by alternating
bremsstrahlung and pair production, with each generation splitting the particle count
in two and halving the energy per particle, over one radiation length. After `n`
generations there are `2^n` particles each carrying `E0 / 2^n` of the initial energy
`E0`; the cascade stops multiplying once the per-particle energy falls to a critical
energy `E_c` where ionization loss overtakes radiative loss, fixing the shower's
maximum particle count at `N_max ~ E0 / E_c` and reaching it after
`n_max ~ log2(E0 / E_c)` generations - the single result that makes calorimeter energy
resolution scale as `1/sqrt(E)` (see
[calorimetry](calorimetry-ecal-hcal.md)) and, in air-shower form, ties the shower's
longitudinal development directly to the primary energy.

**Matthews' extension to hadronic showers** treats each hadronic interaction as
splitting the energy among a fixed multiplicity of secondaries, roughly a third of
which are neutral pions that decay promptly to photons and feed the electromagnetic
sub-cascade, while the charged pions continue interacting until their energy falls
below a critical energy at which they decay to muons instead. This toy model, despite
its crudeness, correctly predicts the two results that dominate composition analysis:

- **Muon number scales as `N_mu ~ E0^beta` with `beta` slightly below 1** (typically
  ~0.9), because each hadronic generation "spends" some energy into the
  electromagnetic channel before the remaining hadronic energy reaches the pion decay
  threshold - so muon number grows more slowly than linearly with primary energy.
- **A nucleus of mass number `A` behaves approximately as `A` independent proton
  showers each of energy `E0/A`** (the superposition model). Since `N_mu` is sublinear
  in single-shower energy, the sum over `A` sub-showers gives *more* muons for a
  nucleus than for a proton of the same total energy `E0` - the origin of the
  muon-content composition observable in
  [cosmic-ray-spectrum-and-composition.md](cosmic-ray-spectrum-and-composition.md).
  Superposition also predicts an earlier shower maximum for a heavier nucleus (each
  sub-shower has less energy and so develops less deeply), consistent with the
  `X_max` composition observable below.

## Longitudinal profile: Gaisser-Hillas and Greisen

The number of charged particles as a function of atmospheric slant depth `X` (in
`g/cm^2`) is well described empirically by the **Gaisser-Hillas function**:

    N(X) = N_max * ((X - X0) / (X_max - X0))^((X_max - X0)/lambda)
           * exp((X_max - X) / lambda)

with four parameters: the peak size `N_max`, the depth of maximum `X_max`, a depth
offset `X0` (the depth of first interaction, extrapolated back; not itself directly
physical), and a shape/attenuation length `lambda`. `X_max` is the single most
composition-sensitive observable a fluorescence or hybrid detector can measure
directly (see [ground-based detection arrays](ground-based-detection-arrays.md)),
since it tracks the depth of first interaction and the subsequent cascade length,
both of which are set by the primary's mass through the superposition argument above.
`<plugin root>/skills/hep-detector/scripts/xmax_gaisser_hillas.py` evaluates `N(X)`, the shower
age and the half-maximum depths for a given parameter set (with `X_max` as an input); it does not
fit a profile or locate `X_max` from samples. Fluorescence detectors fit the energy-deposit profile
`dE/dX`, not `N(X)`.

The **Greisen parameterization** is the equivalent closed-form profile specifically
for pure electromagnetic (photon/electron-initiated) showers, expressed in radiation
lengths rather than the Gaisser-Hillas form's atmospheric slant depth; it is the
appropriate reference profile for gamma-ray-initiated showers (see
[imaging Cherenkov](imaging-atmospheric-cherenkov.md)), which lack the hadronic component of
hadron-initiated showers (whose fluctuations are largest for protons).

**`X_max` fluctuations, not just its mean, carry composition information.** A
proton-initiated shower's depth of first interaction fluctuates with the full
proton-air cross section's interaction-length distribution, while a nucleus's sub-showers average part of
the fluctuations out: simulations give about 60 g/cm2 for protons and about 20 g/cm2 for iron near 1e18 eV, much
wider than the naive superposition value (about 8 g/cm2), because the nucleons of one interaction are correlated
([Kampert & Unger 2012, arXiv:1201.0018](https://arxiv.org/abs/1201.0018), Sec. 2).
Measuring only `<X_max>(E)` and its slope, the elongation rate
`D_10 = d<X_max>/d log10(E)`, and not its shower-to-shower spread discards a composition-sensitive observable and, worse, can mask a mixed
composition that happens to produce the same mean as a single pure species.

## Shower universality

Detailed simulation shows that once a shower's stage of development is expressed
relative to its own `X_max` (rather than absolute atmospheric depth), the lateral and
energy distributions of shower particles at a given stage are nearly independent of
the primary's mass, energy, and even the hadronic interaction model used to simulate
it - a property called **shower universality**. This is what allows a ground array
(which samples the shower at one fixed depth, not its full profile) to reconstruct
energy from particle density at a reference distance from the shower core without
needing to know the primary species: the density-to-energy conversion is
approximately universal once corrected for the shower's estimated depth of maximum
relative to the observation level (see
[ground-based detection arrays](ground-based-detection-arrays.md)). Universality is
approximate, not exact - the residual mass and interaction-model dependence is itself
a systematic that must be quoted, not assumed away.

## The muon puzzle

<!-- example: source citation (experiment named as the source of a general method or number) -->
Most, but not all, experiments with independent muon measurements find more muons in air showers
than simulations predict for the composition implied by `X_max`. The combined analysis of eight
air-shower experiments (WHISP, as summarized by Gesualdi et al., PoS(ICRC2021)473,
opened 2026-10-14) finds the deficit in simulations growing with energy, with a non-vanishing slope
at 8 sigma, while EAS-MSU, KASCADE-Grande, IceCube and Yakutsk data are consistent with no deficit
in their ranges. The size depends on the hadronic model and its version (name both). This is treated as evidence of a genuine gap in hadronic-interaction
modeling at energies far above any accelerator calibration point (a shower's first few
interactions can reach center-of-mass energies beyond the LHC), not as a composition
effect, since, where the deficit is seen, no mixture of known primaries reconciles both observables
under current models. Any composition or hadronic-model conclusion
drawn from muon content alone, without also checking consistency against `X_max`,
should be treated as provisional given this open discrepancy.
<!-- /example -->

## Deliverables

- Which shower observable underlies a reported composition or energy result -
  `X_max` and its fluctuation, muon content, or a hybrid combination - and the
  hadronic interaction model and version used to interpret it.
- Whether an energy or composition estimate assumed shower universality, and whether
  the residual model/mass dependence of that assumption was propagated as a
  systematic.
- For an `X_max`-based result: the fitted Gaisser-Hillas parameters (or equivalent),
  the depth range actually observed versus extrapolated, and whether both the mean
  and the fluctuation of `X_max` were used.
- For a muon-content result: an explicit note of the muon-puzzle discrepancy and
  whether the analysis's conclusion is robust to it or depends on resolving it.
- The primary energy estimator used (calorimetric fluorescence yield, ground-array
  lateral density, or a hybrid combination) and its own model dependence.
