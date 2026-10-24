# Cosmic-ray new physics: dark matter and pulsars without overclaiming

Purpose: what enters a dark-matter or pulsar contribution to cosmic-ray antiprotons and positrons, how much each input
moves the answer, and what must hold before an interpretation is stated. Part of [cosmic-ray
phenomenology](cosmic-ray-phenomenology.md), whose "Sources read" lists every paper cited here (read in full text
on 2026-10-23). Scope: the predictions and their uncertainties are in v1;
deciding which model explains an excess is outside v1 (limited support), the significance of a signal is hep-statistics,
and whether a published result supports a claim is hep-citations. Experiment numbers come from the bound profile, never
from here.

## Dark matter to antiprotons

Ingredients: yields at production per channel, propagation functions per halo profile and propagation set, the halo
itself (PPPC 4 DM ID provides all three in numerical form and estimates the yield uncertainty by comparing two event
generators; Cirelli et al. 2011, abstract), plus modulation. Each one is a model alternative of the signal:

- **Halo height.** The dark-matter antiproton flux scales almost linearly with L, which is uncertain by about a factor
  2 (Calore et al. 2022, Sec. 4); a bound or a fitted cross section inherits that factor unless L is fitted jointly
  ([cosmic-ray phenomenology](cosmic-ray-phenomenology.md), halo height).
- **Halo profile and local density.** Across cored, NFW and contracted profiles the bound moves by less than a factor
  2, and a 30% uncertainty on the local density gives about 70% on the annihilation signal (Calore et al. 2022,
  Sec. 5.2). Conventions in [dark matter](dark-matter-phenomenology.md).
- **Transport family.** Switching the benchmark family from BIG to QUAINT moves the best-fit point by about 14% in
  mass and almost a factor 3 in cross section (Calore et al. 2022, Sec. 5.1); against BIG and SLIM, QUAINT changes the
  shape of a bound, not only its normalization (Sec. 5.2).
- **Modulation.** That study used the force field with one potential for antiprotons and nuclei (no charge-sign
  dependence, Sec. 3); an earlier excess claim named better production cross sections and solar modulation as what a
  confirmation would need (Cuoco, Kramer and Korsmeier 2017, abstract). For opposite-sign ratios use the drift-aware
  models of [solar modulation models](solar-modulation-models.md).

One published antiproton excess and its reassessment is the reference case:

<!-- example: experiment-specific illustration -->

(AMS-02 antiproton data.)

- joint fits reported a preference for a dark-matter mass near 80 GeV at about 4.5 sigma (Cuoco, Kramer and Korsmeier
  2017, abstract; main text: formally Delta chi^2 = 25 for two extra parameters, without systematic errors) and at 20-80 GeV
  (Cui et al. 2017, abstract), both noting compatibility with the Galactic-centre gamma-ray excess;
- with an updated production cross section the significance fell to about 3 sigma, and cross-section uncertainties
  (as a covariance) changed it little; benchmark models of data correlations raised it, in some cases above 5 sigma
  (Cuoco et al. 2019, abstract and conclusions): the treatment of data correlations mattered much more than the
  cross-section uncertainties;
- with propagation and cross-section errors and a data correlation matrix the data are consistent with a secondary
  origin (Boudaud et al. 2020, abstract); with all systematics, including detector-absorption cross sections, the
  global significance is below 1 sigma and no mass from 10 GeV to 10 TeV is preferred (Heisig et al. 2020, abstract);
  the earlier hints are statistically insignificant (Calore et al. 2022, abstract).

<!-- /example -->

## Dark matter to positrons

Sommerfeld-enhanced s-wave annihilation fitted to the positron excess faces severe constraints from dwarf-galaxy gamma
rays and the CMB (Ding et al. 2021, abstract, which proposes p-wave annihilation to evade them). The CMB bound is
p_ann = f_eff <sigma v>/m_chi < 3.2 x 10^-28 cm^3 s^-1 GeV^-1 at 95% for s-wave annihilation, f_eff the fraction of
the energy deposited around z ~ 600 (temperature, polarization, lensing and BAO; Planck 2018 VI, Sect. 7.9, Eqs.
88-89c), and the positron-fraction regions for annihilation into muons are in strong tension with it (Fig. 46); combined dwarf limits
fall below the thermal cross section for masses below about 100 GeV in quark and tau channels (dwarf-galaxy gamma-ray
search 2015, abstract). Lepton data can, in some cases, constrain dark matter as strongly as or more strongly than
other indirect probes (Di Mauro et al. 2016, abstract). The excess is defined against a secondary positron prediction whose production cross
section alone carries 5-8% on the source term and whose older parametrization (Kamae, p+p, above 5 GeV) differs by about 20% (Orusa et al. 2022,
abstract and Sec. VI; [cosmic-ray phenomenology](cosmic-ray-phenomenology.md), secondary positrons): state the secondary
model before the excess. Lepton energy losses: [cosmic-ray propagation](cosmic-ray-propagation.md).

## Pulsars

Pulsars (the Galactic population of mature pulsars plus the nearest ones, such as Geminga and B0656+14) could
plausibly produce the positron signal, and a nearby source would leave a small dipole anisotropy in
the lepton arrival directions that could separate it from dark matter (Hooper, Blasi and Serpico 2009, abstract). The
TeV halos around Geminga and PSR B0656+14 were read both ways: slow diffusion near the sources (D = (4.5 +- 1.2) x 10^27 cm^2/s
for 100 TeV electrons, about 100 times below earlier models) makes them unlikely to explain the excess (HAWC 2017,
abstract, Table 1) or makes pulsars very likely its origin (Hooper et al. 2017, abstract); the
exclusion depends on assuming homogeneous diffusion, and with a radially dependent diffusion coefficient the two
pulsars can match the observed high-energy positron flux (Profumo et al. 2018, abstract).
Geminga alone gives at most 20% of the positrons at the highest measured energies (Di Mauro, Manconi and Donato 2019,
abstract); the 1 sigma band of simulated pulsar populations spans at least an order of magnitude (Manconi et al. 2020, abstract) and fits are
often carried by a few bright sources (Orusa et al. 2021, abstract).

Antideuterons and antihelium are not covered here; their production by coalescence (conventions and B_A, p0) is in
[light-nuclei coalescence](light-nuclei-coalescence.md).

## Before stating an interpretation

- The background is a set of model alternatives (transport families, cross-section sets, modulation model, LIS), not
  one curve; the signal claim survives all of them or is stated per alternative. So is the signal (yields, L, halo).
- The data covariance is used; a result that appears only with diagonal errors is not a result.
- Masses, channels and halos scanned are trials: local and global significance from hep-statistics.
- The signal is consistent with other probes (gamma rays, CMB, other species) or the tension is stated.
- Wording follows the derivation status: "compatible with", "a fit improvement of", never "evidence for dark matter"
  from one channel. Which model explains an excess is outside v1 (limited support); whether a published result
  supports a claim is hep-citations; the experiment's own reading comes from its profile ledger.

## What to report

The signal model (channel, mass, cross section or lifetime), yields and their generator, halo profile, local density
and L; the background alternatives and their cross sections; the modulation model per charge sign; the data and their
covariance; the scan (masses, channels, halos) and the global significance from hep-statistics; the other probes
checked.
