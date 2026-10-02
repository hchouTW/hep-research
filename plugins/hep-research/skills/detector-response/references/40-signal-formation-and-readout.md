# Signal Formation, Transport, and Readout

The first four arrows of the [chain](39-detector-measurement-framework.md): particle
and interaction, detector response, signal formation and transport, electronics and
raw data. Material-budget/multiple-scattering bookkeeping is in
[21](21-detector-systems-overview.md); calibration of the constants introduced here is in
[29](29-calibration-and-alignment.md). Every equation below states its validity; none
is a substitute for a full simulation ([28](28-detector-simulation.md)).

## Energy loss and its fluctuations

**Mean ionization loss (Bethe-Bloch; approximate, intermediate energies, heavy charged
particles)**:

```
-<dE/dx> = K z^2 (Z/A) (1/beta^2) [ 0.5 ln(2 m_e c^2 beta^2 gamma^2 W_max / I^2)
                                     - beta^2 - delta(beta*gamma)/2 ]
K = 4 pi N_A r_e^2 m_e c^2 = 0.307 MeV mol^-1 cm^2
```

`z` projectile charge, `Z/A` medium (mol/g), `I` mean excitation energy, `W_max`
maximum energy transfer, `delta` the density-effect correction. Parameters come from
tabulated fits (PDG), not from data. It fails below `beta gamma ~ 0.05-0.1`
(shell, Barkas, and charge-exchange corrections) and, for muons, above `~ 1000`
(PDG passage-of-particles review: radiative losses take over near the muon critical
energy, a few hundred GeV in iron/copper). Electrons are not described by this formula
at all (different kinematics; bremsstrahlung dominates above the electron critical
energy, tens of MeV). Shape: falls as `1/beta^2`, minimum at
`beta gamma ~ 3-4` (minimum-ionizing, "MIP"), logarithmic relativistic rise, then a
Fermi plateau from `delta`. The rise is *smaller in dense media and thin gas volumes
than a naive mean suggests* because the density effect and delta-ray escape truncate it.

**Fluctuations (regime by `kappa = xi/W_max`, `xi = (K/2)(Z/A) z^2 (x rho)/beta^2`)**:
`kappa << 1` (thin absorber, gases, silicon of ~100 um): the Landau/Vavilov
distribution - asymmetric with a long high tail from delta rays, most-probable value
(MPV) below the mean, no finite variance in the pure Landau limit; `kappa >> 1`
(thick absorbers): Gaussian. Consequences: use the truncated mean, MPV fit, or
likelihood, not the raw mean, for thin-layer `dE/dx` ([24](24-particle-identification.md));
the fluctuation is a *physical, irreducible* per-layer term, reduced only by more layers
or cluster counting.

**Multiple Coulomb scattering (Highland, approximate, ~11% for `1e-3 < x/X0 < 100`)**:
`theta_0 = (13.6 MeV / (beta c p)) z sqrt(x/X_0) [1 + 0.038 ln(x z^2/(X_0 beta^2))]`.
It sets the low-momentum resolution floor of every tracker
([22](22-tracking-and-vertexing.md)); the non-Gaussian large-angle tail
(single-scatter) is why fit `chi^2` has heavy tails.

**Radiative and nuclear processes.** Bremsstrahlung (energy scale `~ X_0`, critical
energy `E_c`), photon conversion (`~ 9/7 X_0` mean free path), delta rays (extended
clusters, tail of `dE/dx`), and nuclear interactions (interaction length
`lambda_I`, produce kinks, secondary vertices, and the invisible energy of
[23](23-calorimetry-ecal-hcal.md)). Each is a topological source of fakes and tails,
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
  empirical), so heavy ions, alphas, and nuclear recoils give less light than electrons
  of the same energy - the origin of "electron-equivalent" versus nuclear-recoil energy
  scales ([44](44-noble-liquid-neutrino-and-rare-event-detectors.md)).
- **Attenuation.** Light reaching a photosensor at distance `L`: `~ exp(-L/lambda_att)`
  plus geometric losses; a position-dependent gain that must be measured or corrected;
  in a wavelength-shifter, the photon spectrum shifts and the trapping/re-emission
  efficiency adds a second stochastic step ([45](45-cherenkov-imaging-variants-and-photosensors.md)).
- **Photon statistics** (Poisson; exact for the count, approximate for the Gaussian
  limit): `sigma_E/E = 1/sqrt(N_pe)`, `N_pe = N_gamma * eps_collection * QE`. Gain
  fluctuation adds an excess noise factor `F >= 1`:
  `sigma_E/E ≈ sqrt(F/N_pe)`; the stochastic term `a/sqrt(E)` of a calorimeter is the
  energy-scaled form of this.

**Cherenkov radiation (exact kinematics; approximate yield)**: emission when
`beta > 1/n` with `cos theta_C = 1/(n beta)`; threshold `p_th = m c/sqrt(n^2 - 1)`;
number of photons per unit path per energy `d^2N/(dx dE) ≈ 370 sin^2 theta_C  eV^-1 cm^-1`
(before detection efficiency). Yield is small (tens of detected photons at most for
practical radiators), so `N_pe` is the dominant performance limit
([24](24-particle-identification.md), [45](45-cherenkov-imaging-variants-and-photosensors.md)).

**Transition radiation.** Emitted when a relativistic particle crosses interfaces
between media of different dielectric constants; the yield rises with Lorentz factor
`gamma` and onsets near `gamma ~ 10^3`, so it separates electrons from hadrons only at
momenta where the hadron is below threshold. X-rays are absorbed in the same gas as
the ionization signal (mind the overlap in likelihood; [24](24-particle-identification.md)).

**Showers.** Electromagnetic (scale `X_0`, Moliere radius `R_M`, log growth of depth
with energy) and hadronic (scale `lambda_I`, non-compensation, invisible energy) are
developed in [23](23-calorimetry-ecal-hcal.md); for signal formation they add a
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
position reconstruction and calibrated with tracks ([22](22-tracking-and-vertexing.md),
[41](41-gaseous-and-specialized-tracking-technologies.md)).

**Avalanche gain.** In proportional gas, `G = exp(int alpha dx)` (Townsend `alpha`);
gain fluctuates with a Polya (approximately exponential) distribution; gain depends
exponentially on voltage and, through the density `T/P`, on temperature and pressure
(the sensitivity is gas- and voltage-specific and must be measured) - hence
pressure/temperature corrections in every gaseous detector. Beyond the proportional regime: Geiger,
streamer, discharge; space charge from ion backflow modulates the effective field.

**Losses in transport.** Electron attachment to electronegative impurities (`O2`, `H2O`)
gives `Q(t) = Q0 exp(-t/tau_e)` (electron lifetime `tau_e`; a slow, measured,
time-dependent correction in noble-liquid TPCs); recombination for liquid/high-density
media depends on `dE/dx` and field, producing the scintillation-ionization
anticorrelation ([44](44-noble-liquid-neutrino-and-rare-event-detectors.md));
charge trapping and radiation damage in semiconductors reduce the collected charge
(charge collection efficiency `CCE < 1` and rising leakage current with fluence).
**Space charge**: positive-ion buildup distorts `E` and hence reconstructed positions
(TPC, high-rate gas detectors).

**Phonons and heat.** Cryogenic bolometers convert deposited energy into a temperature
rise `Delta T = E/C` (heat capacity `C`); sensitivity to sub-keV energies is bought by
very low `C`. Nuclear/electron recoil discrimination uses the ratio of ionization or
light to heat ([44](44-noble-liquid-neutrino-and-rare-event-detectors.md)).

**Irreducible versus correctable.** Landau fluctuation, photostatistics, sampling
fluctuation, and diffusion are stochastic floors (reducible only by design); gain,
drift velocity, attenuation length, lifetime, refractive index, and `t0` are correctable
response variations whose *residual error* is a systematic
([29](29-calibration-and-alignment.md)).

## Readout and digitization

**Chain**: sensor -> preamplifier -> shaper -> discriminator and/or ADC/TDC ->
buffer -> zero-suppression / trigger -> data. Each stage removes information; keep the
**analog information loss** (irreversibly discarded at digitization, e.g. threshold,
binary readout, coarse ADC) separate from **reconstruction loss** (information present
in the raw data but not used by the algorithm).

- **Pulse shaping and sampling.** A CR-RC shaper with peaking time `tau` trades noise
  against pileup: slow shaping reduces series noise but increases pileup and dead time;
  sampling a waveform at rate `f_s` needs `f_s` above twice the signal bandwidth
  (Nyquist) or aliasing biases amplitude and time extraction. Amplitude and time from a
  waveform: peak, matched filter, template fit (best; needs the pulse shape and its
  variation with occupancy).
- **Noise.** Equivalent noise charge (ENC, electrons) sets the threshold and the
  minimum measurable signal; signal-to-noise `S/N` of a minimum-ionizing particle in a
  thin sensor is the driver of both hit efficiency and position resolution. **Common-mode
  noise** (coherent across channels) is subtracted event-by-event; **crosstalk**
  (capacitive, inductive, or optical) creates ghost signals and biases charge sharing.
- **Pedestal, zero suppression, dynamic range.** Pedestals are measured (dedicated
  runs, empty events) and drift with temperature; zero suppression removes noise
  at the cost of dropping small real signals (threshold efficiency,
  [39](39-detector-measurement-framework.md)); **saturation** clips large signals
  (high-energy showers, heavy ions) and biases sums downward unless a dynamic-range
  overlap is calibrated.
- **Time-over-threshold and binary readout.** Time above threshold encodes amplitude
  nonlinearly (calibrated per channel); binary readout keeps only "hit/no hit" and
  timing, losing amplitude - fine position resolution then relies on geometry and
  cluster topology.
- **Pileup and dead time.** Signals overlapping in time within the shaping/integration
  window merge; a non-paralyzable dead time `tau` turns a true rate `n` into a
  measured `m = n/(1 + n tau)` (approximate); a paralyzable one saturates and turns
  over at high rate. The measured rate versus the true rate is a *response* needing a
  correction ([19](19-triggers-luminosity-pileup.md)).
- **Buffering and data loss.** Finite buffer depth and bandwidth drop events or hits
  under burst conditions; the loss is *rate- and topology-dependent* (large events
  lost more), so it can look like a physics-dependent efficiency.
- **Trigger primitives and bias.** A hardware trigger acts on coarse, low-latency
  information (fewer bits, poorer alignment, no full calibration). Trigger efficiency
  differs from offline efficiency and depends on the same variables as the analysis
  cut (turn-on curves, prescales) - see [19](19-triggers-luminosity-pileup.md). A
  trigger-level cut on an under-calibrated quantity creates an *inefficiency that is
  correlated with the analysis observable*, the most common way a trigger biases a
  measurement.

## Common misconceptions and failure modes

- **"Threshold has no effect on resolution."** Thresholds truncate the low tail of the
  response and bias centroids and energy sums, especially for low-`S/N` clusters.
- **Using Bethe-Bloch outside its range.** Below `beta gamma ~ 0.1` or in the radiative
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
