# Signal Formation, Transport, and Readout

The first four arrows of the [chain](detector-measurement-framework.md): particle
and interaction, detector response, signal formation and transport, electronics and
raw data. Electronics in quantitative detail (noise, shaping, thresholds, optimal
filtering, digitization, timing pickoff, rate effects) is in
[front-end electronics and signal processing](front-end-electronics-and-signal-processing.md). Material-budget/multiple-scattering bookkeeping is in
[detector systems overview](detector-systems-overview.md); the calibration chain (pedestal, gain, scale, time
dependence) is in [calibration and alignment](calibration-and-alignment.md), and worked corrections for `t0` and
drift velocity, refractive index and electron lifetime are in
[case studies and checklists](detector-case-studies-and-checklists.md) (Cases 3, 6, 8). Most equations below
state their validity; none is a substitute for a full simulation ([detector simulation](detector-simulation.md)).

## Energy loss and its fluctuations

**Mean ionization loss (Bethe-Bloch; approximate, intermediate energies, heavy charged
particles)**:

```
-<dE/dx> = K z^2 (Z/A) (1/beta^2) [ 0.5 ln(2 m_e c^2 beta^2 gamma^2 W_max / I^2)
                                     - beta^2 - delta(beta*gamma)/2 ]
K = 4 pi N_A r_e^2 m_e c^2 = 0.307075 MeV mol^-1 cm^2
```

`z` projectile charge, `Z/A` medium (mol/g), `I` mean excitation energy, `W_max`
maximum energy transfer, `delta` the density-effect correction. Parameters come from
tabulated fits (PDG), not from data. Uncorrected, it fails below `beta gamma ~ 0.1`
(shell, Barkas, and charge-exchange corrections; PDG adds the shell term `-C/Z`, the
Barkas term `z L1` and the Bloch term `z^2 L2` inside the bracket, so the shell term scales
as `z^2` overall like the leading term, while the Barkas and Bloch terms scale as `z^3` and
`z^4` and matter most for nuclei, and the corrected formula holds to about 1%
down to `beta ≈ 0.05`; for slower protons and alphas use the NIST PSTAR and ASTAR
stopping-power and range tables (PSTAR covers 1 keV to 10 GeV protons)) and, for muons, above
`beta gamma ~ 1000` (`p ≈ 100 GeV/c`)
(PDG passage-of-particles review: radiative losses take over near the muon critical
energy, a few hundred GeV in iron/copper). Electrons are not described by this formula
at all (different kinematics; bremsstrahlung dominates above the electron critical energy, from
about 7 MeV in lead to about 90 MeV in air: `E_c ≈ 610 MeV/(Z + 1.24)` for solids and liquids, `710
MeV/(Z + 0.92)` for gases, PDG). Shape: falls as `1/beta^2`, minimum at
`beta gamma ~ 3-4` (minimum-ionizing, "MIP"), logarithmic relativistic rise. With the density effect
`delta` the *mean* keeps rising (more slowly); the *restricted* loss (transfers below a cut) and the
most probable loss reach a Fermi plateau. A thin layer records roughly the restricted loss, because
energetic delta rays escape, so the measured rise is *smaller than the mean suggests*. Most probable
loss (PDG): `Delta_p = xi [ln(2 m_e c^2 beta^2 gamma^2/I) + ln(xi/I) + 0.200 - beta^2 - delta]`.

**Fluctuations (regime by `kappa = xi/W_max`, `xi = (K/2)(Z/A) z^2 (x rho)/beta^2`)**:
`kappa <~ 0.05-0.1` (PDG "moderate thickness", most detectors; thin absorber, gases, silicon of
~100 um): the Landau (Landau-Vavilov) distribution - asymmetric with a long high tail from
delta rays, most-probable value
(MPV) below the mean, no finite mean or variance in the pure Landau limit; for thin silicon
Bichsel's straggling functions (atomic binding included) describe the width better than
Landau-Vavilov (PDG); larger `kappa`: Vavilov's distribution, less skewed as `kappa` grows;
`kappa >> 1` (very thick absorbers): less skewed still but, per PDG, never Gaussian - a
Gaussian approximates only the core. Consequences: use the truncated mean, MPV fit, or
likelihood, not the raw mean, for thin-layer `dE/dx` ([particle identification](particle-identification.md));
the fluctuation is a *physical, irreducible* per-layer term, reduced only by more layers
or cluster counting.

**Multiple Coulomb scattering (Highland, approximate: Gaussian for the central 98% of the
projected angle; `beta` dependence poorly represented for large `Z` and small `x`; PDG Eq. 34.16)**:
`theta_0 = (13.6 MeV / (beta c p)) z sqrt(x/X_0) [1 + 0.038 ln(x z^2/(X_0 beta^2))]`.
It sets the low-momentum resolution floor of every tracker
([tracking and vertexing](tracking-and-vertexing.md)); the non-Gaussian large-angle tail
(single-scatter) is why fit `chi^2` has heavy tails. `theta_0` is the rms of the projected angle (`theta_space,rms = sqrt(2) theta_0`); for a stack apply the formula once with the total `x/X_0`, since per-layer values added in quadrature come out too small (PDG).

**Charge yield and intrinsic statistics** (approximate; PDG RPP 2024, particle detectors at accelerators): `N = E/W` carriers, with `W` = 3.65 eV in silicon, 2.96 eV in germanium, about 26 eV in argon gas and 23.6 eV in liquid argon; for a fixed deposit in a semiconductor the variance is reduced by the Fano factor, `sigma_N = sqrt(F N)` with `F ≈ 0.1` in Si and Ge, so `sigma_E/E = sqrt(F W/E)`, usually below the electronic noise. A minimum-ionizing particle leaves a most probable charge of about 23 000 electrons (3.7 fC) in 300 um of silicon, about 77 e-h pairs per um, against a mean of about 106 per um (3.88 MeV/cm over 3.65 eV): quote which.

**Radiative and nuclear processes.** Bremsstrahlung (energy scale `~ X_0`, critical
energy `E_c`), photon conversion (`~ 9/7 X_0` mean free path; at low energy the photoelectric effect and Compton scattering dominate the photon cross section, with attenuation `I = I_0 exp(-(mu/rho) rho x)` and `mu/rho` from the NIST XCOM tables), delta rays (extended
clusters, tail of `dE/dx`), and nuclear interactions (interaction length
`lambda_I`, produce kinks, secondary vertices, and the invisible energy of
[calorimetry ecal hcal](calorimetry-ecal-hcal.md)). Each is a topological source of fakes and tails,
not a smooth resolution term.

**Cluster counting.** Primary ionization clusters are Poisson-distributed with
`~ 10s per cm` in typical tracking gases (order of magnitude; species/pressure
dependent). Counting clusters instead of integrating charge removes the Landau tail
and reaches better `dE/dx` resolution, at the price of needing to resolve single
clusters in the waveform (rate, diffusion, and electronics limits).

## Light: scintillation, wavelength shifting, attenuation

- **Scintillation.** Light yield `N_gamma = Y E` (photons/MeV; material dependent),
  decay-time spectrum (fast + slow components). **Quenching**: yield per unit energy is
  not linear at high `dE/dx` (Birks-type; `dL/dx = S (dE/dx)/(1 + kB dE/dx)`,
  empirical), so heavy ions and alphas give less light than electrons of the same
  energy. For nuclear recoils the larger effect is Lindhard quenching: only a fraction
  `L` of the recoil energy goes into electronic excitation (PDG RPP 2025, sec. 36: `L`
  about 0.2-0.25 in liquid argon and 0.15-0.2 in liquid xenon for 3-100 keV recoils), and
  in noble liquids recombination also changes the split between light and charge.
  Together these are the origin of "electron-equivalent" versus nuclear-recoil energy
  scales ([noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md)).
- **Attenuation.** Light reaching a photosensor at distance `L`: `~ exp(-L/lambda_att)`
  plus geometric losses; a position-dependent gain that must be measured or corrected;
  in a wavelength-shifter, the photon spectrum shifts and the trapping/re-emission
  efficiency adds a second stochastic step ([cherenkov imaging variants and photosensors](cherenkov-imaging-variants-and-photosensors.md)).
- **Photon statistics** (Poisson; exact for the count, approximate for the Gaussian
  limit): `sigma_E/E = 1/sqrt(N_pe)`, `N_pe = N_gamma * eps_collection * QE`. Gain
  fluctuation adds an excess noise factor `F >= 1`:
  `sigma_E/E ≈ sqrt(F/N_pe)`; the stochastic term `a/sqrt(E)` of a calorimeter is the
  energy-scaled form of this.

**Cherenkov radiation (exact kinematics; approximate yield)**: emission when
`beta > 1/n` with `cos theta_C = 1/(n beta)`; threshold `p_th = m c/sqrt(n^2 - 1)`;
number of photons per unit path per energy `d^2N/(dx dE) ≈ 370 z^2 sin^2 theta_C eV^-1 cm^-1` for a projectile of charge number `z`
(before detection efficiency). In gas and aerogel RICH radiators the yield is small (of order
tens of detected photons per track), so `N_pe` is the dominant performance limit there;
thicker or denser radiators (water Cherenkov, lead glass, quartz bars) give more
([particle identification](particle-identification.md), [cherenkov imaging variants and photosensors](cherenkov-imaging-variants-and-photosensors.md)).

**Transition radiation.** Emitted when a relativistic particle crosses interfaces
between media of different dielectric constants; the yield (proportional to `z^2`)
rises with Lorentz factor `gamma`, with an onset near `gamma ~ 10^3` and, for a foil stack,
saturation from interference above `gamma_sat`; both are set by the foil thickness, the
spacing and the foil plasma frequency (`gamma_thr ~ l1 omega1/c`,
`gamma_sat ~ 0.6 omega1 sqrt(l1 l2)/c`), and most detectors choose `gamma_sat ≈ 3000`
(PDG RPP 2025, secs. 34.7.3 and 35.6.5). It separates electrons from hadrons only at
momenta where the hadron is below threshold. X-rays are absorbed in the same gas as
the ionization signal (mind the overlap in likelihood; [particle identification](particle-identification.md)).

**Showers.** Electromagnetic (scale `X_0`, Moliere radius `R_M`, log growth of depth
with energy) and hadronic (scale `lambda_I`, non-compensation, invisible energy) are
developed in [calorimetry ecal hcal](calorimetry-ecal-hcal.md); for signal formation they add a
stochastic *sampling* term (fluctuation in the number of charged particles crossing
active layers) and a *containment* term.

## Charge: drift, diffusion, gain, losses

**Drift.** In field `E`, electrons in gas reach a drift velocity `v_d = mu E`
(constant mobility, low field only; in real gases `v_d(E, B, T, P, composition)` is
measured and tabulated). In liquid noble gases `v_d ~ mm/us` at a few hundred V/cm.
**Diffusion (approximate, Gaussian)**: longitudinal/transverse spread after drift
distance `L` is `sigma = sqrt(2 D L / v_d) = C_D sqrt(L)`, with `C_D` in
`um/sqrt(cm)` measured for the gas mixture. In a magnetic field parallel to `E`,
transverse diffusion is reduced by `1/sqrt(1 + omega^2 tau^2)` (approximate). Diffusion
is the floor on drift-coordinate resolution at long drift and the reason for gas
selection ("cold" gases have low diffusion).

**Lorentz angle.** In crossed `E x B`, the drift direction rotates by the Lorentz angle
`theta_L`; a pixel or strip cluster is displaced and broadened, an effect corrected in
position reconstruction and calibrated with tracks ([tracking and vertexing](tracking-and-vertexing.md),
[gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md)).

**Avalanche gain.** In proportional gas, `G = exp(int alpha dx)` (Townsend `alpha`);
gain fluctuates: the single-electron gain follows a Polya distribution with relative
variance `1/(1+theta)`; the exponential (Furry, `theta = 0`) is its limit when ionization is
memoryless, and measurements in Micromegas and GEMs at high `E/P` and gain need
`theta > 0` (Micromegas: relative variance 0.31 ± 0.02, `theta ≈ 2.2`, Zerguerras et al.,
NIM A608 (2009) 397, arXiv:0901.2882, eq. 2;
form from NEWS-G, arXiv:1902.08960, eq. 1); `theta` depends on gas, geometry and field. Gain depends
exponentially on voltage and, through the gas density (proportional to `P/T`; the
gain follows the reduced field `E/N`, proportional to `E*T/P`), on temperature and pressure
(the sensitivity is gas- and voltage-specific and must be measured) - hence
pressure/temperature corrections in every gaseous detector. Beyond the proportional regime: Geiger,
streamer, discharge; space charge from ion backflow modulates the effective field.

**Losses in transport.** Electron attachment to electronegative impurities (`O2`, `H2O`)
gives `Q(t) = Q0 exp(-t/tau_e)` (electron lifetime `tau_e`; a slow, measured,
time-dependent correction in noble-liquid TPCs); recombination for liquid/high-density
media depends on `dE/dx` and field, producing the scintillation-ionization
anticorrelation ([noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md));
charge trapping and radiation damage in semiconductors reduce the collected charge
(charge collection efficiency `CCE < 1` and rising leakage current with fluence).
**Space charge**: positive-ion buildup distorts `E` and hence reconstructed positions
(TPC, high-rate gas detectors).

**Phonons and heat.** Cryogenic bolometers convert deposited energy into a temperature
rise `Delta T = E/C` (heat capacity `C`); sensitivity to sub-keV energies is bought by
very low `C`. Nuclear/electron recoil discrimination uses the ratio of ionization or
light to heat ([noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md)).

**Irreducible versus correctable.** Landau fluctuation, photostatistics, sampling
fluctuation, and diffusion are stochastic floors (reducible only by design); gain,
drift velocity, attenuation length, lifetime, refractive index, and `t0` are correctable
response variations whose *residual error* is a systematic
([calibration and alignment](calibration-and-alignment.md) for the chain; worked `t0`, drift-velocity,
refractive-index and lifetime cases in [case studies and checklists](detector-case-studies-and-checklists.md)).

## Readout and digitization

**Chain**: sensor -> preamplifier -> shaper -> discriminator and/or ADC/TDC ->
buffer -> zero-suppression / trigger -> data. Each stage removes information; keep the
**analog information loss** (irreversibly discarded at digitization, e.g. threshold,
binary readout, coarse ADC) separate from **reconstruction loss** (information present
in the raw data but not used by the algorithm).

- **Pulse shaping and sampling.** A CR-RC shaper with peaking time `t_p` balances
  series noise (falls with `t_p`) against parallel, leakage-current noise (rises with
  `t_p`), pileup and dead time (rise with `t_p`): there is an optimum `t_p`, and it moves
  shorter as leakage current grows with dose. With a known pulse shape and a phase
  locked to the clock, a few samples per pulse give unbiased amplitudes even below the
  signal's Nyquist rate (an anti-alias filter on the noise and a stable phase are what
  is required); Nyquist sampling matters when the waveform itself is unknown. Amplitude
  and time from a waveform: peak, optimal filter (minimum variance when the noise
  autocorrelation, including pileup, and the phase are known), template fit (biased at
  low `S/N` with a free time). Details and numbers:
  [front-end electronics and signal processing](front-end-electronics-and-signal-processing.md).
- **Noise.** Equivalent noise charge (ENC, electrons) sets the threshold and the
  minimum measurable signal; signal-to-noise `S/N` of a minimum-ionizing particle in a
  thin sensor is the driver of both hit efficiency and position resolution. **Common-mode
  noise** (coherent across channels) is subtracted event-by-event, excluding channels
  with signal (otherwise the estimate absorbs signal at high occupancy); **crosstalk**
  (capacitive, inductive, or optical) creates ghost signals and biases charge sharing.
- **Pedestal, zero suppression, dynamic range.** Pedestals are measured (dedicated
  runs, empty events) and drift with temperature; zero suppression removes noise
  at the cost of dropping small real signals (threshold efficiency,
  [detector measurement framework](detector-measurement-framework.md)); **saturation** clips large signals
  (high-energy showers, heavy ions) and biases sums downward unless a dynamic-range
  overlap is calibrated.
- **Time-over-threshold and binary readout.** Time above threshold encodes amplitude
  nonlinearly (calibrated per channel); binary readout keeps only "hit/no hit" and
  timing, losing amplitude - fine position resolution then relies on geometry and
  cluster topology.
- **Pileup and dead time.** Signals overlapping in time within the shaping/integration
  window merge; for Poisson arrivals a non-paralyzable dead time `tau_d` turns a true
  rate `n` into a measured `m = n/(1 + n tau_d)`, and a paralyzable one into
  `m = n exp(-n tau_d)`, which turns over at `n = 1/tau_d`. Bunched beams and trigger
  rules break the Poisson assumption. The measured rate versus the true rate is a
  *response* needing a correction (live time in
  [triggers luminosity pileup](triggers-luminosity-pileup.md)).
- **Buffering and data loss.** Finite buffer depth and bandwidth drop events or hits
  under burst conditions; the loss is *rate- and topology-dependent* (large events
  lost more), so it can look like a physics-dependent efficiency.
- **Trigger primitives and bias.** A hardware trigger acts on coarse, low-latency
  information (fewer bits, poorer alignment, no full calibration). Trigger efficiency
  differs from offline efficiency and depends on the same variables as the analysis
  cut (turn-on curves, prescales) - see [triggers luminosity pileup](triggers-luminosity-pileup.md). A
  trigger-level cut on an under-calibrated quantity creates an *inefficiency that is
  correlated with the analysis observable*, the most common way a trigger biases a
  measurement.

## Common misconceptions and failure modes

- **"Threshold has no effect on resolution."** Thresholds truncate the low tail of the
  response and bias centroids and energy sums, especially for low-`S/N` clusters.
- **Using Bethe-Bloch outside its range.** Below `beta gamma ~ 0.1` (uncorrected formula;
  `beta ≈ 0.05` with the shell, Barkas and Bloch terms) or in the radiative
  regime, the mean is not the right predictor; thin-layer `dE/dx` is Landau-shaped and
  the mean is not a stable estimator.
- **Treating attenuation as a constant.** It varies with position, time, temperature,
  and radiation dose; it is a per-channel and time-dependent calibration.
- **Confusing electron-equivalent and nuclear-recoil energy.** Quenching makes them
  different scales; quote which one.
- **Blaming analog loss for a reconstruction problem (or vice versa).** Check whether
  the information exists in the raw waveform before redesigning the algorithm.
- **Saturation invisible in ratios.** Clipped channels look like a resolution loss at
  the highest energies; monitor the saturated fraction.

## Deliverables

- The earliest physical signal and the digitized quantity for the detector, with the
  forward model and nuisance parameters.
- Which fluctuations are irreducible (with their scaling) and which response
  variations are correctable (with the calibration that handles them).
- Threshold, dynamic range, dead time, and buffering limits, with the resulting
  efficiency versus rate/occupancy behavior.
- A statement of the trigger-level information and the bias it can introduce.
