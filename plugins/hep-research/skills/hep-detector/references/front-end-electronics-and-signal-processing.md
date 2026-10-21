# Front-End Electronics and Signal Processing

How readout electronics shapes a detector's response: scale and linearity, resolution,
efficiency and fake rate, timing, rate behaviour, and data/MC agreement. The physical
signal (ionization, light, drift, gain) is in [signal formation and readout](signal-formation-and-readout.md);
the single-hit time-resolution budget and per-technology timing notes are in [timing detectors](timing-detectors.md); photosensor
statistics are in [cherenkov imaging variants and photosensors](cherenkov-imaging-variants-and-photosensors.md); the electronics model in
simulation is the Digitization section of [detector simulation](detector-simulation.md).
`<plugin root>/skills/hep-detector/scripts/frontend_response.py` evaluates the relations below
(ENC, noise-hit rate, timing, quantization, pileup, SiPM, ballistic deficit, dead time,
cluster noise) and flags inputs outside their validity range.

**Scope.** This file models electronics *as part of the response*: what it does to the
numbers an analysis sees, how to calibrate it, and how to simulate it. It does not cover
circuit, ASIC or FPGA design (transistor sizing, feedback topology, layout, power,
PLL design, firmware coding or timing closure), component or ADC/TDC architecture
selection for a new design, radiation-hardening design, grounding and signal integrity,
or DAQ networking. For those, say so and point to engineering sources (for example the
Spieler and Radeka references in the [bibliography](detector-principles-bibliography.md)). Code that implements a filter
or a digitizer model is a hep-computing deliverable; ML waveform reconstruction is
hep-ml's.

Labels: *exact* (follows from the stated model), *approximate*, *empirical*,
*device-specific* (take the number from the apparatus, never from memory).

## The chain and the questions to ask

Sensor -> preamplifier (usually charge-sensitive) -> shaper or anti-alias filter ->
discriminator and/or ADC / TDC / waveform digitizer -> digital filter, feature
extraction, zero suppression -> buffer -> trigger -> event building. For any analysis
question, first establish:

1. What is digitized (amplitude, time, time-over-threshold, binary hit, full waveform)
   and at what rate and resolution.
2. The pulse shape (peaking time, order, unipolar or bipolar) and its stability.
3. The noise: level per channel, spectrum, and correlations between channels.
4. Thresholds and their spread across channels.
5. Dynamic range: saturation, gain switching, nonlinearity.
6. Rate limits: pileup of pulses, dead time, buffers, trigger rules.
7. How each of these is calibrated, monitored, and reproduced in simulation.

## Signal induction

- **Shockley-Ramo** (*exact*, quasi-static fields): a charge `q` moving with velocity
  `v` induces on an electrode the current `i = q v · E_w`, where `E_w` is that
  electrode's weighting field (unit potential on it, zero on all others, space charge
  ignored). The induced charge between two points is `q (phi_w(x2) - phi_w(x1))`.
  (PDG RPP 2025 eq. 35.20 writes the same form.) With resistive elements, as in
  resistive plate chambers or underdepleted silicon, the signal also follows the
  time-dependent reaction of the materials, described by time-dependent weighting
  fields (W. Riegler, NIM A535 (2004) 287).
- Consequences: the signal flows *while charges move*, not when they arrive; in a
  pad or pixel much smaller than the sensor thickness the weighting field is
  concentrated near the electrode, so the charge drifting toward it dominates the
  signal ("small-pixel effect"); a neighbouring electrode that collects nothing sees a
  **bipolar** current with zero net charge, unless trapping (radiation damage) stops
  charges mid-way and leaves a net induced charge on neighbours.
- Wire chambers and LAr TPC induction planes produce bipolar signals by construction;
  their charge is recovered by deconvolving the field response (see LAr TPC below).
- **Charge division into the preamplifier.** A charge-sensitive amplifier of open-loop
  gain `A` and feedback capacitance `C_f` has input capacitance `C_in ≈ A C_f`; the
  fraction of the signal charge it receives is `C_in/(C_in + C_det)` (*approximate*).
  With large detector or inter-strip capacitance, the remainder appears on neighbours
  as crosstalk of order `C_inter/C_in`.
- **Ballistic deficit** (*approximate*): when the current lasts `T_c` and the shaper
  peaks at `t_p`, the amplitude is lower than for an instantaneous charge. For
  CR-(RC)^n and a rectangular current, deficit `≈ n (T_c/t_p)^2/24` for `T_c ≲ t_p`
  (CR-RC: 1.0 % at `T_c = 0.5 t_p`, 4 % at `t_p`; the formula overestimates beyond
  that). A collection
  time that depends on depth, angle, or field makes the amplitude depend on them too
  (a `dE/dx` and pulse-height bias in gas and thick or irradiated silicon).

## Shaping

- **CR-(RC)^n** step response (*exact* for ideal stages with equal time constants
  `tau`): `g(t) ∝ (t/tau)^n exp(-t/tau)`, peaking time `t_p = n tau`. Higher order gives
  a more symmetric pulse, shorter tail for the same `t_p`, and slightly different noise
  coefficients (below).
- **Pole-zero cancellation** removes the undershoot caused by the preamplifier's decay
  time; a mis-set pole-zero gives a rate-dependent baseline.
- **AC coupling and bipolar shaping** keep the mean baseline at zero *in steady state*
  only: after a change in rate (start of a bunch train, a spill, a burst) the baseline
  is displaced for several shaping times (bipolar shaping) or several coupling time
  constants (AC coupling alone; see Pileup below). Baseline restorers reduce, but do not
  remove, this.
- **Shaping time is a trade-off** between series noise (falls with `t_p`), parallel
  noise (rises with `t_p`), pileup and dead time (rise with `t_p`), and ballistic
  deficit (falls with `t_p`). There is an optimum; it moves to shorter `t_p` as leakage
  current grows with radiation dose.

## Noise

**Equivalent noise charge.** For a charge-sensitive amplifier followed by a shaper whose
unit-charge response `g(t)` is normalized to peak 1, with one-sided noise densities
(*exact* for stationary noise, linear system):

    ENC^2 = (i_n^2/2) ∫ g^2 dt  +  C^2 (e_n^2/2) ∫ g'^2 dt  +  C^2 A_f ∫_0^∞ |G'(f)|^2 / f df

- parallel (current) noise `i_n^2 = 2 q I_leak + 4 k T / R_p`: its `ENC^2` grows as `t_p`;
- series (voltage) noise `e_n^2` (input-transistor thermal noise, `4 k T R_s` for a
  series resistance): its `ENC^2` grows as `C^2` and falls as `1/t_p`;
- `1/f` noise `e_f^2 = A_f/f`: its `ENC^2` grows as `C^2`, *independent of `t_p`*;
- `C` is the total capacitance at the input (detector + amplifier + strays).

For CR-(RC)^n these integrals have closed forms (the script evaluates them). Rules of
thumb for CR-RC (`n = 1`): parallel `ENC ≈ 107 √(I_leak[nA] · t_p[µs])` electrons;
series with `R_s = 50 ohm` at 300 K, `C = 10 pF`, `t_p = 1 µs`: 55 electrons. The optimum shaping
time, where series and parallel terms are equal, is `t_p,opt = C e_n / i_n` for CR-RC
(example: `C = 10 pF`, `e_n = 1 nV/√Hz`, `I_leak = 1 µA` gives 18 ns; at 1 nA it is
0.56 µs). These coefficients are shaper-specific; quote the shaper.

**Leakage current and its drift** (*empirical*, silicon): the bulk damage current grows
with fluence as `ΔI = alpha Φ_eq V` with `alpha ≈ 4e-17 A/cm` at 20 °C after the
standard anneal (alpha depends on annealing history and temperature), and scales with
temperature as `I ∝ T^2 exp(-E_eff / 2kT)` with `E_eff ≈ 1.21 eV`: about a factor 19
between 20 °C and -10 °C, halving every ~7.6 K near room temperature and every ~6 K
near -20 °C. Parallel noise, power, and thermal
runaway risk follow. Noise is therefore time-dependent through dose, temperature, and
annealing; treat it as conditions data.

**Noise in a sum of channels** (*exact*, equal `sigma` and pairwise correlation `rho`):
`sigma_sum = sigma √(N + N(N-1) rho)`. With `rho = 0.1` and 25 cells, `sigma_sum = 9.2
sigma`, not `5 sigma`. Coherent noise is the usual reason a calorimeter's noise term `b`
is underestimated in simulation and why cluster-size and occupancy distributions
disagree with data.

**Common-mode subtraction.** Estimating the common mode from the same channels that
carry signal biases it: at high occupancy, in large clusters, or under heavily ionizing
tracks the estimate absorbs signal, producing negative charge on neighbours and lost
clusters. Exclude hit channels (iterative or median estimate) and monitor the residual
common mode versus occupancy.

**Non-Gaussian noise.** Random telegraph signals, pickup from switching supplies, and
periodic interference give tails that a Gaussian `sigma` does not describe; fake-hit
rates computed from `sigma` then fail by orders of magnitude. Measure the noise
distribution, not only its width, and its spectrum when tails appear.

## Thresholds, fake hits, and zero suppression

- **Efficiency at a threshold** (*approximate*, Gaussian noise): for signal `Q` and
  threshold `T`, `eps = Phi((Q - T)/sigma)` (the turn-on in
  [detector measurement framework](detector-measurement-framework.md)). A threshold
  scan with injected charge gives an **S-curve**: its 50 % point is the threshold and
  its width is the noise. Across channels the spread of 50 % points is the threshold
  dispersion; the effective threshold noise is `√(ENC^2 + sigma_thr^2)`. Per-channel
  trim reduces `sigma_thr`.
- **Noise-hit rate** (*exact* for stationary Gaussian noise, Rice): the rate of upward
  crossings of level `T` is `nu = nu_0 exp(-T^2 / 2 sigma^2)` with
  `nu_0 = (1/2pi) √(m_2/m_0)`, with `m_k = ∫ omega^k S(omega) d omega` the moments of
  the output noise spectrum in angular frequency. For CR-(RC)^n,
  `nu_0 tau` is 0.092 (parallel) and 0.276 (series) for `n = 2`, 0.060 and 0.123 for `n = 4` (per RC
  constant `tau = t_p/n`; per peaking time, `nu_0 t_p` is 0.184 and 0.551 for `n = 2`, 0.241 and
  0.493 for `n = 4`); for CR-RC (`n = 1`) with series noise `nu_0` is undefined without a further
  bandwidth limit. Fake hits per event = channels × window × `nu`. A "5 sigma threshold"
  is not "no fakes" for 10^8 channels.
- **Zero suppression** with seed/neighbour thresholds keeps clusters but truncates
  their tails; cluster charge and centroid are then biased for low-`S/N` clusters, and
  the bias differs between data and simulation if the thresholds or noise differ.
- **Thresholds and the response**: a threshold turns a gain or noise drift into an
  efficiency change only for signals near it; the most exposed populations are
  minimum-ionizing particles in thin sensors, single photoelectrons, and low-energy
  showers.

## Amplitude and time from sampled waveforms

- **Optimal filter** (*exact* for known pulse shape `g`, known phase, stationary
  Gaussian noise with autocorrelation matrix `R`; Cleland and Stern): the
  minimum-variance unbiased linear amplitude estimate is `A = w · s` with
  `w = R^-1 g / (g^T R^-1 g)` and variance `1/(g^T R^-1 g)`. A time (phase) estimate
  uses the derivative `g'` with additional constraints.
  - `R` must include pileup noise (its autocorrelation follows from Campbell's
    theorem, below), so the weights depend on the pileup level; stale weights give a
    resolution and a bias that change with pileup.
  - A template fit that ignores noise correlations can be *worse* than a single sample
    (example: CR-RC with `t_p = 25 ns`, 5 samples every 25 ns starting 15 ns before
    the peak, noise correlation `rho^|i-j|` with `rho = 0.6`: sigma 1.12 for the
    uncorrelated template fit, 1.07 for the largest sample alone, 1.04 for the
    optimal filter, in units of the per-sample noise).
  - A fit with free time at low `S/N` follows the noise and is biased upward.
  - A phase error biases the amplitude. With white noise (CR-RC^4, `t_p = 45 ns`, 5
    samples every 25 ns from one before the peak to three after): −0.04 % to −0.3 % at
    2 ns and −0.8 % to −1.5 % at 5 ns, depending on the direction. With correlated or
    pileup noise the weights extrapolate harder and the bias reaches several percent
    with either sign (same pulse, `rho = 0.6`, samples two before to two after the
    peak: +0.9 % / −1.8 % at ∓2 ns, up to −5.8 % at 5 ns). This appears as an energy
    scale that drifts with the timing calibration.
- **Sampling.** With a known pulse shape and a phase locked to the clock, a few
  samples per pulse below the Nyquist rate of the signal give unbiased amplitudes
  (collider calorimeters at 40 MHz). What is required is an anti-alias filter on the
  noise and a stable phase. Nyquist sampling matters when the waveform itself is
  unknown (pulse-shape discrimination, multiple pulses, unknown timing).
- **Out-of-time pileup**: fit several pulses with templates at neighbouring bunch
  crossings (multi-pulse fit), or deconvolve (for example the deconvolution readout
  mode of silicon strip front ends); both trade noise for pileup rejection.
- **Pulse-shape stability**: pulse shape changes with temperature, gain switch, and
  radiation; a template measured once is a conditions item with a validity range.

## Digitization: ADC and TDC

- **Quantization** (*approximate*): `LSB/√12` is the rms error over a broad spread of
  true values (or random phases for a TDC). At a *fixed* true value it averages out
  only when the input noise is at least about 0.5 LSB; with less noise the error is
  deterministic: at 0.05 LSB of noise the mean of 16 samples keeps a −0.30 LSB bias at
  a true value of 0.3 LSB. Above that noise level `sigma ≈ √(sigma_n^2 + LSB^2/12)`.
- **Nonlinearity**: differential nonlinearity (unequal bin widths) creates structure in
  spectra and in time distributions; integral nonlinearity bends the scale. Measure
  with a code-density test (uniform input, histogram of codes) and correct per channel.
  `ENOB = (SINAD - 1.76 dB)/6.02 dB` summarizes ADC noise and distortion.
- **Dynamic range**: saturation clips large signals and biases sums downward;
  multi-gain readout needs the gain ratios intercalibrated in the overlap region, or a
  step appears at the switch energy that looks like a nonlinearity or a resolution
  loss. Recovering saturated pulses from the leading edge is a correction with its own
  uncertainty.
- **Time-over-threshold** encodes amplitude nonlinearly and depends on pulse shape and
  baseline; calibrate per channel with injected charge.

## Time pickoff

- **Jitter** (*approximate*, linear edge): `sigma_t = sigma_n / (dV/dt) ≈ t_r / (S/N)`
  with `t_r` the 0-100 % rise time; with a 10-90 % rise time the slope is `0.8 A/t_r`
  and the jitter `1.25 t_r/(S/N)`.
- **Walk** of a leading-edge discriminator (*approximate*, linear edge of rise time
  `t_r` and amplitude `A`, threshold `T`): crossing time `T t_r / A`, so two amplitudes
  differ by `T t_r (1/A_1 - 1/A_2)` (`t_r = 1 ns`, `T = 0.5`, `A = 0.6` versus 1:
  333 ps). Correct with amplitude or time-over-threshold, per channel; for nuclei the
  walk falls as `1/A ∝ 1/Z^2`, so the calibration must span the whole charge range,
  including saturation, and one made with singly charged particles does not transfer.
- **Constant-fraction discrimination** removes amplitude dependence for a fixed pulse
  shape in both of its modes. In "true" CFD mode (`t_d > (1 - f) t_r`: the attenuated
  prompt pulse has reached its peak when the crossing occurs) the time still depends on
  the rise time (`t_d + f t_r` for a linear edge); in amplitude-and-rise-time-compensated
  mode (`t_d < (1 - f) t_r`) the crossing is at `t_d/(1 - f)` from the pulse start,
  independent of both amplitude and rise time for linear edges. Rise-time fluctuations
  (Landau fluctuations in LGADs, depth of interaction) favour the latter.
- **TDC**: bin `/√12` as the rms over random phases, with the same averaging condition as
  an ADC at a fixed phase; differential
  nonlinearity calibrated by code density; clock distribution adds jitter with a
  *global* part (common to all channels, cancels in time differences within one event)
  and a *local* part (per board or PLL, averages over independent boards).
- The per-detector budgets (sensor, photostatistics, calibration, geometry, reference
  time) are in [timing detectors](timing-detectors.md).

## Pileup of pulses, baseline, and rate

- **Campbell's theorem** (*exact*, stationary Poisson arrivals at rate `nu` with
  amplitudes `a`): the shaped signal has mean `nu <a> ∫ g dt` and variance
  `nu <a^2> ∫ g^2 dt`; its autocorrelation is `nu <a^2> ∫ g(t) g(t + Δ) dt`. This is the
  pileup part of a calorimeter noise term and the pileup term to add to `R` in an
  optimal filter.
- **Bipolar or AC-coupled shaping** has `∫ g dt = 0`, so the mean offset vanishes in
  steady state, but not after a change in rate: after a step from zero to rate `nu`
  the offset is `nu <a> ∫_0^t g dt'`, which rises and then returns to zero over several
  shaping times for bipolar shaping, or several coupling time constants for AC coupling
  alone (longer when that constant exceeds the shaping time). For a bipolar pulse `g = tau d/dt[(t/tau) e^(1 - t/tau)]` it equals
  `nu <a> tau (t/tau) e^(1 - t/tau)`: maximal (`nu <a> tau`) one `tau` after the start of
  a bunch train, still 9 % of that after `5 tau`. The result is an energy offset that
  depends on position in the train and on pileup.
- **Dead time** (*exact* for Poisson arrivals): non-paralyzable `m = n / (1 + n tau_d)`;
  paralyzable `m = n exp(-n tau_d)`, which has a maximum at `n = 1/tau_d` and turns over.
  Bunched beams, spills, and trigger rules (minimum spacing between accepts, limits per
  window) break the Poisson assumption; then measure the live fraction directly per
  luminosity block or run ([triggers luminosity pileup](triggers-luminosity-pileup.md)).
- **Buffers and derandomizers** lose data in bursts and preferentially large events,
  so the loss looks like a rate- and topology-dependent efficiency.

## Photosensor readout

The statistics (Poisson photoelectrons, excess noise factor) are in
[cherenkov imaging variants and photosensors](cherenkov-imaging-variants-and-photosensors.md); the electronics-facing effects are:

- **SiPM saturation** (*approximate*, prompt and uniform light): fired cells
  `N_cells (1 - exp(-N_pe / N_cells))`; at `N_pe = N_cells` only 63 % of the linear
  response remains. Light pulses longer than the cell recovery time raise the
  effective `N_cells`; crosstalk and non-uniform illumination change the curve. Correct
  with a measured curve, never by assuming linearity at high deposits.
- **SiPM correlated noise**: optical crosstalk is a branching process (Borel): with
  `lambda` the mean number of secondary avalanches per avalanche, one primary gives on
  average `1/(1 - lambda)` cells with variance `lambda/(1 - lambda)^3`. With Poisson
  secondaries `lambda = -ln(1 - P_ct)`, where `P_ct` is the measured probability of
  at least one secondary (`P_ct = 0.2` gives `lambda = 0.22`, mean 1.29 cells).
  Dark counts add both a mean `DCR · gate` and a variance (1 GHz × 20 ns gives 20 pe
  mean and sigma = √20 ≈ 4.5 pe from Poisson alone, more with crosstalk); pedestal
  subtraction removes only the mean, which matters for irradiated SiPMs.
- **SiPM gain and photon detection efficiency** grow with overvoltage
  `V_bias - V_bd(T)`; the breakdown voltage changes with temperature (*device-specific*
  coefficient), so gain drifts with temperature unless the bias is compensated.
- **PMT gain** (*approximate*) `G ∝ V^(k n)` for `n` dynodes with `k ≈ 0.7-0.8`: a
  relative high-voltage change is amplified `k n` times (10 dynodes: 0.1 % in HV gives
  about 0.75 % in gain). Afterpulses, magnetic field, and rate-dependent gain (space
  charge at the last dynodes) are further response terms.

## LAr TPC signal processing

- Raw waveforms on induction planes are bipolar and on collection planes unipolar;
  each is the convolution of the drifting charge with the **field response** (from the
  weighting field) and the **electronics response**.
- Charge is recovered by deconvolving both (one- or two-dimensional, the latter using
  neighbouring wires), with a filter that suppresses noise amplification; the filter
  choice sets a resolution-versus-bias trade.
- **Coherent noise** (common across a readout board) is removed before deconvolution;
  regions of interest restrict processing to signal. Tracks at large angle to the wire
  plane give long, low induction signals whose deconvolved charge is the least
  reliable, which biases `dE/dx` and particle identification for those tracks.
- See [noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md) for the detector physics.

## Radiation and the electronics

- **Single-event upsets** flip configuration or data bits: channels become noisy, dead,
  or mis-configured until reconfigured, so inefficiency grows during a fill and tracks
  luminosity; it is absent from a static dead-channel map unless that map is
  time-dependent.
- **Total ionizing dose** shifts thresholds, gain, and leakage of the front-end
  itself; recalibrate thresholds and monitor S-curves versus dose.
- **Sensor damage** raises leakage current (Noise above) and reduces collected charge;
  the signal-to-noise ratio falls from both sides.

## Calibration of the electronics

- **Pedestals and noise**: dedicated runs or random triggers; per channel, versus
  temperature and time.
- **Charge injection** (test pulse): gain and linearity per channel; the absolute scale
  carries the uncertainty of the injection capacitor and the pulser amplitude, which
  is common to all channels injected by the same circuit.
- **Threshold scans** (S-curves): threshold, noise, and dispersion per channel; trim.
- **Timing**: per-channel offsets, walk curves, TDC bin widths by code density, clock
  phase per board.
- **Photosensors**: single-photoelectron spectra (gain), LED/laser linearity, dark rate
  and crosstalk versus temperature and dose.
- **Pulse shape**: templates and optimal-filter weights per channel and gain, with the
  pileup conditions they assume.
- Store all of these as conditions with intervals of validity
  ([calibration and alignment](calibration-and-alignment.md)).

## Simulation of the electronics

- Simulate in the same order as the hardware: induced signal, preamplifier and
  shaper, noise with its measured correlations (from pedestal data), pileup in the
  integration window, digitization (thresholds, ADC range, gain switching, time
  quantization), then the same feature extraction and zero suppression as online.
- Overlaying recorded zero-bias or random-trigger data brings in the real noise and
  pileup, including correlations and non-Gaussian tails, which independent Gaussian
  noise does not.
- Use the same pulse templates and optimal-filter weights in simulation as in data
  for the same conditions; otherwise amplitude bias and resolution differ.
- Emulate trigger firmware bit for bit where trigger efficiency is taken from
  simulation.
- Thresholds, noise, dead channels, and SEU-affected periods are time-dependent
  conditions; simulate them per period ([detector simulation](detector-simulation.md)).

## Common misconceptions and failure modes

- **"Longer shaping always lowers noise."** Only when series noise dominates; leakage
  current makes the opposite true after irradiation.
- **"Sampling below Nyquist biases the amplitude."** Not with a known shape and a
  locked phase; phase drift is the real risk.
- **"A template fit is optimal."** Only with the right noise correlations and a fixed
  phase.
- **"Quantization error averages out."** At a fixed input, only with enough noise to
  dither; `LSB/√12` is an rms over inputs.
- **"Pedestal subtraction removes dark counts."** It removes the mean, not the variance.
- **"Bipolar shaping has no baseline shift."** Only in steady state.
- **"Five sigma means no fake hits."** Multiply by channels, window, and `nu` (not `nu_0`).
- **"Noise is per channel and independent."** Coherent noise can dominate sums.
- **"The dead-channel map is static."** Upsets, dose, and temperature change it.
- **Electronics nonlinearity calibrated away as a physics effect** (SiPM saturation,
  gain switching).

## Deliverables

- The readout chain with what is digitized, the pulse shape, and the sampling.
- A noise budget (series, parallel, `1/f`, pickup) with its dependence on capacitance,
  shaping time, leakage current, temperature, and dose, and the channel correlations.
- Thresholds in units of noise and of the signal, with the resulting efficiency and
  fake-hit rate.
- The amplitude and time estimators, their assumptions (pulse shape, phase, noise
  correlation including pileup), and their bias and resolution.
- Dynamic range: saturation, gain switching, nonlinearity, and their calibration.
- Rate behaviour: pileup, baseline shifts, dead time, buffer losses, live fraction.
- The electronics calibration chain and its conditions, and how each element is
  reproduced in simulation.
