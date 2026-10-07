# Particle Identification: TRD, TOF, RICH, dE/dx, and Muon Systems

Covers how detectors determine *what* a particle is, as opposed to where it went and
how much energy it carried. Every technique here measures velocity, Lorentz factor, or
charge, and converts that - combined with the rigidity from
[tracking and vertexing](tracking-and-vertexing.md) - into a mass or species
hypothesis. Organized by technology and independent of experiment; calorimeter-based
identification (`E/p`, shower shape) is in
[calorimetry](calorimetry-ecal-hcal.md).

## The common principle

A magnetic spectrometer measures rigidity `R = p/q`. Mass does not appear. To identify
a particle you need a second, independent measurement that depends on mass through a
different combination of variables - and every technique below is a way of measuring
either velocity `beta` or Lorentz factor `gamma`:

    m = p / (beta * gamma) = (p / beta) * sqrt(1 - beta^2)

The precision of the resulting mass therefore depends on the precision of *both*
measurements, and because `gamma` grows without bound while `beta` saturates at 1, every
velocity-based technique has a momentum ceiling above which the species become
indistinguishable. Where that ceiling sits is the single most important number to
quote for any PID system. Propagating `dm/m` from `dbeta/beta` gives

    dm/m = gamma^2 * (dbeta/beta)   (at fixed momentum)

- the `gamma^2` factor is why velocity-based identification degrades so quickly with
momentum, and why different technologies are needed in different momentum bands.
`<plugin root>/skills/detector-response/scripts/pid_separation_power.py` evaluates this for time-of-flight and ionization
measurements, and `<plugin root>/skills/detector-response/scripts/cherenkov_angle.py` for ring-imaging detectors.

## Time of flight (TOF)

A TOF system measures the time a particle takes to traverse a known flight path `L`,
giving `beta = L / (c * t)` directly. Two scintillator planes (or any two timing
layers) define the path; the resolution is set by the timing resolution `sigma_t` of
the pair and by the uncertainty in `L`, which comes from the track fit.

Separation between two species of mass `m1` and `m2` at momentum `p` follows from
their time difference over the same path, which for relativistic particles scales as

    dt ~ (L / 2c) * (m1^2 - m2^2) / p^2

The `1/p^2` is decisive: TOF separation power falls as the square of momentum, so a
system with a given timing resolution has a sharp practical ceiling - typically a few
GeV/c for pion/kaon separation with sub-100-picosecond timing over a metre-scale path.
Extending the reach requires a longer path or better timing, and both scale only
linearly against a quadratic loss.

Practical points that dominate real TOF performance:

- **The start time must be known.** At a collider it comes from the bunch crossing or
  from a dedicated start detector; in a non-collider experiment one plane defines the
  start. An error in start time is common to all particles in the event and biases
  every `beta` in the same direction - so it does not average out and shows up as a
  species-dependent mass shift.
- **Path length is a track-fit output**, not a constant. For curved tracks it depends
  on the fitted trajectory, and using a straight-line approximation at low momentum
  introduces a bias that grows exactly where TOF is most useful.
- **Time-walk and charge dependence.** Signal amplitude affects the measured time in
  most discriminator schemes; the correction depends on deposited charge, which for
  nuclei scales as `Z^2`. A TOF calibrated on singly-charged particles is not
  automatically valid for heavier ones.
- **TOF also measures direction of travel.** The sign of the time difference between
  planes distinguishes downward- from upward-going particles, which is the primary
  rejection against albedo and backward-going background in non-collider geometries.

## Ionization energy loss (dE/dx)

Every charged particle traversing material loses energy by ionization, at a mean rate
described by the Bethe-Bloch formula. The rate depends on `beta` (falling steeply at
low `beta`, reaching a minimum near `beta*gamma ~ 3-4`, then rising logarithmically in
the relativistic rise before saturating at the Fermi plateau) and on the square of the
particle's charge, `Z^2`.

That `Z^2` dependence makes any ionization measurement primarily a **charge**
measurement, and it is usually the cleanest way to determine `|Z|` for nuclei -
silicon trackers and gas chambers both provide it, and requiring consistent charge
across many layers is a powerful rejection of interactions and of mis-associated hits.

As a *velocity* measurement dE/dx is harder, for a specific reason: the energy loss in
a thin layer is not Gaussian but **Landau-distributed**, with a long high-side tail
from rare large energy transfers. Consequently the *mean* of a few samples is a poor
estimator - it is dominated by the tail and has large variance. The standard remedy is
a **truncated mean**: discard the highest-loss fraction of samples (commonly the top
30-40%) and average the rest. This is why detectors with many samples (a TPC with
hundreds of measurements) achieve far better dE/dx resolution than a few silicon
layers, and why quoting "dE/dx resolution" without stating the number of samples and
the truncation fraction is meaningless.

The relativistic rise gives some separation power above the minimum-ionizing region,
but it is weak - a few percent difference in mean loss against a resolution of similar
size - so dE/dx alone rarely separates species cleanly at high momentum. Its real
strength is at low momentum, below the minimum, where the `1/beta^2` rise is steep, and
in charge determination at all momenta.

## Transition radiation detectors (TRD)

When a relativistic charged particle crosses a boundary between materials of different
dielectric constant, it emits transition radiation - X-ray photons whose *yield*
depends on the Lorentz factor `gamma`, not on velocity. This is the crucial
distinction: `beta` saturates at 1 and stops discriminating, while `gamma = E/m`
continues to grow, so a TRD keeps separating species long after TOF and dE/dx have
failed.

Because yield per interface is tiny, a TRD stacks many radiator foils or fibre layers
followed by an X-ray-absorbing gas chamber (typically xenon-based, for photoelectric
absorption at the relevant few-keV energies). The signal is a *statistical excess* of
high-energy deposits in some layers on top of ordinary ionization - not a distinct
signature in any single layer. That has two direct consequences:

- **Identification is inherently a likelihood problem across layers**, not a cut on one
  measurement. The standard estimators are a likelihood ratio built from per-layer
  amplitude distributions, or a count of layers exceeding a threshold. Either way the
  per-layer response distributions are the calibration, and they must be measured from
  data control samples, not taken from simulation alone.
- **Performance is quoted as a rejection factor at a fixed efficiency**, and it is
  strongly `gamma`-dependent. A TRD separates electrons from protons over the momentum
  band where their `gamma` values differ greatly (because of the ~1836 mass ratio) and
  loses power once the heavier species also becomes ultra-relativistic. State the
  momentum band, the working-point efficiency, and the rejection factor together - one
  without the others is uninterpretable.

Transition radiation is emitted at very small angles and its energy deposit is
superimposed on the particle's own ionization in the same chamber, so a TRD's
`gamma`-dependent signal and its dE/dx signal are *correlated*, not independent
measurements. Combining them as if independent overstates the separation.

## Ring-imaging Cherenkov detectors (RICH)

A charged particle traversing a radiator of refractive index `n` faster than light in
that medium emits Cherenkov radiation on a cone of half-angle

    cos(theta_c) = 1 / (n * beta)

Imaging the resulting ring measures `theta_c`, hence `beta`, directly and very
precisely. There is a hard **threshold**: emission requires `beta > 1/n`, so each
species has a threshold momentum below which it produces no ring at all. That
threshold is itself identification information - the *absence* of a ring above a
species' threshold excludes it - and using it requires knowing the detector's
efficiency for detecting a ring that should be there.

Key behaviors:

- **The angle saturates.** As `beta -> 1`, `theta_c` approaches its maximum
  `arccos(1/n)`, and species separation vanishes. The usable momentum range is bounded
  below by threshold and above by saturation, and the width of that window is set by
  `n`: a radiator close to `n = 1` (aerogel, or a gas) pushes the whole window to
  higher momentum. Experiments needing broad coverage use **multiple radiators** with
  different indices, and each has its own calibration and its own window.
- **Angular resolution improves with photon count.** The single-photon angular
  resolution is set by chromatic dispersion (index varies with photon energy), by pixel
  granularity, and by the emission-point uncertainty along the track; the per-track
  resolution improves as the square root of the number of detected photons. Photon
  yield is itself proportional to `sin^2(theta_c)`, so rings are dimmest exactly at
  threshold, where the angle is most sensitive to velocity - the two effects partially
  cancel and must be evaluated together, not separately.
- **Velocity precision translates to mass precision with the `gamma^2` amplification**
  above. A RICH achieving a `dbeta/beta` of order `1e-3` still loses isotope separation
  at high `gamma`, which is the limiting factor in isotope measurements.
- **Ring reconstruction is a pattern-recognition problem** with its own failure modes:
  overlapping rings from multiple tracks, rings from secondaries produced in the
  radiator, and background photons. Its efficiency and its misreconstruction rate are
  measured quantities, and both belong in the analysis's efficiency chain.

Because velocity precision is high, a RICH combined with rigidity gives mass precision
good enough to separate **isotopes** of the same element (which have identical charge
and nearly identical rigidity-vs-momentum behavior, differing only in mass). Isotope
separation is the most demanding PID application and is worth treating as its own
validation problem: the separation is a few percent in mass, so every systematic in
`beta`, in `R`, and in the charge assignment enters directly.

## Muon systems

Muons are identified largely by *survival*: they penetrate the calorimeters and any
additional absorber, so a track segment found beyond that material, matched to an
inner track, identifies a muon. This is not a velocity measurement and the
identification quality is set by the amount of absorber and by the matching criterion.

The dominant background is **punch-through** - hadrons, or their shower remnants, that
survive the absorber - plus **decay in flight** of pions and kaons producing genuine
muons that are not from the process of interest. Both are momentum-dependent and both
are estimated from data control samples rather than trusted from simulation.

## Combining measurements

Multiple PID systems are combined into a likelihood: for each species hypothesis,
evaluate the probability of the observed measurements (`beta` from TOF, `theta_c` from
RICH, per-layer amplitudes from the TRD, truncated-mean dE/dx, `E/p` and shower shape
from the calorimeters), multiply, and compare hypotheses. Several requirements are
easy to violate:

- **Do not sum chi-squares across correlated subsystems.** TRD amplitude and tracker
  dE/dx both measure ionization in the same particle's passage; TOF `beta` and the
  track fit share the path length. Treating correlated inputs as independent
  overstates separation, sometimes dramatically. Either use a joint distribution or
  drop the redundant input.
- **Each response distribution is a calibration.** The likelihood is only as good as
  the per-species response templates, which must be measured on data control samples
  selected *without* the variable being calibrated, or the selection biases the
  template.
- **Priors matter and must be stated.** A likelihood ratio becomes a probability only
  with a prior on species abundance, and in a sample where one species outnumbers
  another by orders of magnitude, a modest likelihood ratio does not establish the rare
  species. This is the same reasoning as background estimation in
  [backgrounds.md](../../hep-analysis/references/backgrounds.md), and mis-identification should
  appear as an explicit background component in the likelihood, with its rate
  constrained by a measurement.
- **Quote efficiency and contamination together, differentially.** A PID working point
  is a point on a trade-off curve; a rejection factor without its accompanying
  efficiency, or either one integrated over momentum, hides the behavior in the region
  that usually matters most.

## Common misconceptions and failure modes

- **Gaussian `N_sigma` applied to non-Gaussian tails** or to few-photon distributions.
- **Separation power quoted instead of efficiency and rejection at a working point.**
- **Correlated detector likelihoods multiplied as independent**, double counting shared inputs such as the track momentum.
- **TOF used beyond its momentum ceiling**, or `dE/dx` used without saturation and density-effect handling.
- **Momentum dependence ignored.** Every PID method's separation and background change with momentum.

## Deliverables

- The PID systems used, the momentum band over which each is valid, and the threshold
  and saturation momenta where applicable.
- Mass resolution as a function of momentum, showing the `gamma^2` degradation, and the
  momentum at which the required species separation is lost.
- For TOF: timing resolution, flight path and its uncertainty, start-time source, and
  any charge-dependent time-walk correction.
- For dE/dx: number of samples, truncation fraction, and whether it is used for charge,
  for velocity, or both.
- For TRD: estimator (likelihood or threshold count), working-point efficiency, the
  rejection factor at that point, the momentum band, and how the per-layer response
  templates were calibrated.
- For RICH: radiator(s) and index, per-track angular resolution and photon yield,
  ring-finding efficiency and misreconstruction rate.
- The combination method, with an explicit statement of which inputs are correlated and
  how that correlation is handled.
- Efficiency and contamination for each working point, quoted differentially, with
  mis-identification entering the likelihood as a constrained background.
