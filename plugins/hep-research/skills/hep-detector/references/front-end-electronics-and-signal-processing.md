# Front-End Electronics and Signal Processing

How readout electronics shapes a detector's response: scale and linearity, resolution,
efficiency and fake rate, timing, rate behaviour, and data/MC agreement. The physical
signal (ionization, light, drift, gain) is in [signal formation and readout](signal-formation-and-readout.md);
the single-hit time-resolution budget and per-technology timing notes are in [timing detectors](timing-detectors.md); photosensor
statistics are in [cherenkov imaging variants and photosensors](cherenkov-imaging-variants-and-photosensors.md); the electronics model in
simulation is the Digitization section of [detector simulation](detector-simulation.md).
`<plugin root>/skills/hep-detector/scripts/frontend_response.py` evaluates the relations below
(ENC, noise-hit rate, timing, quantization, pileup, SiPM, ballistic deficit, dead time,
cluster noise) and flags inputs outside their validity range. For reconstruction and
simulation it also gives the optimal-filter weights of a sampled pulse with correlated and
pileup noise, with phase and baseline constraints and the joint amplitude-time errors
(`optimal-filter`), the hit efficiency of a Landau or Gaussian signal against the noise
occupancy, threshold by threshold (`hit-efficiency`), and a seeded synthetic sampled readout
reconstructed by those estimators with closure against the analytic prediction
(`waveform-toy`). For calibration it fits threshold scans and plans them (`s-curve`) and
gives the threshold dispersion left by a trim DAC (`threshold-trim`). Reconstruction from
sampled waveforms, pileup, photosensor and LAr TPC readout, digital pulse processing and
pulse-shape discrimination are in [front-end waveform processing](front-end-waveform-processing.md);
the calibration chain and the simulation of the electronics in
[front-end calibration and simulation](front-end-calibration.md).

**Scope.** This file models electronics *as part of the response*: what it does to the
numbers an analysis sees, how to calibrate it, and how to simulate it. It does not cover
circuit, ASIC or FPGA design (transistor sizing, feedback topology, layout, power,
PLL design, firmware coding or timing closure), component or ADC/TDC architecture
selection for a new design, radiation-hardening design, grounding and signal integrity,
or DAQ networking. For those, say so and point to engineering sources (for example the
Spieler and Radeka references in the [bibliography](detector-principles-bibliography.md)). Production code that implements
a filter or a digitizer model in an experiment's software is a hep-computing deliverable
(this page and the toy give its specification and its checks); ML waveform reconstruction
is hep-ml's.

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
8. What charge reaches one channel (sharing, trapping, ballistic deficit) and therefore
   where the operating window between efficiency and noise occupancy lies.

## Signal induction

- **Shockley-Ramo** (*exact*, quasi-static fields): a charge `q` moving with velocity
  `v` induces on an electrode the current `i = q v · E_w`, where `E_w` is that
  electrode's weighting field (unit potential on it, zero on all others, space charge
  ignored). Integrating that current with `E_w = -grad phi_w`, the charge induced
  while it moves between two points is `-q (phi_w(x2) - phi_w(x1))`. (PDG RPP 2025
  eq. 35.20 writes the same relation with the opposite sign convention for the
  current; keep one convention when reasoning about polarity.) With resistive elements, as in
  resistive plate chambers or underdepleted silicon, the signal also follows the
  time-dependent reaction of the materials, described by time-dependent weighting
  fields (W. Riegler, NIM A535 (2004) 287).
- Consequences: the signal flows *while charges move*, not when they arrive; in a
  pad or pixel much smaller than the sensor thickness the weighting field is
  concentrated near the electrode, so the charge drifting toward it dominates the
  signal ("small-pixel effect"); a neighbouring electrode that collects nothing sees a
  **bipolar** current with zero net charge, unless trapping (radiation damage) stops
  charges mid-way and leaves a net induced charge on neighbours.
- LAr TPC induction planes (and any non-collecting neighbour electrode) produce bipolar
  signals by construction; their charge is recovered by deconvolving the field response
  (see LAr TPC below). Collecting electrodes, the anode wires of a wire chamber or the
  collection plane of a LAr TPC, give unipolar signals with a net charge; in a gas
  chamber it is dominated by the slow ion drift, with a long `1/(t + t0)` tail that the
  shaper removes by tail cancellation.
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
- **Continuous versus sampled comparison.** Rice counts up-crossings of a continuously
  compared signal. A readout that compares samples (zero suppression on ADC samples) is
  noisy with probability `Q(T/sigma)` per sample (`Q` the Gaussian upper tail), correlated
  between neighbouring samples; a binary channel open for a window `W` is noisy with
  probability at most `Q(T/sigma) + nu W` (it starts above threshold or crosses). Use the
  decision rule of the actual readout. With a Gaussian threshold spread `sigma_thr` across
  channels the channel-averaged rates are exact in closed form: `Q(T/s)` and
  `nu_0 (sigma/s) exp(-T^2 / 2 s^2)` with `s^2 = sigma^2 + sigma_thr^2`; the low-threshold
  channels dominate, so trim before quoting a fake rate.
- **Efficiency with a fluctuating signal and the operating window** (*approximate*: signal
  and noise independent and additive). With a signal `Q` of distribution `F_Q` on the
  channel, the channel-averaged inefficiency at threshold `T` is `E[F_Q(T + s u)]` over
  `u ~ N(0, 1)`. For a Landau signal the low side is very steep, so the efficiency is set
  by the fraction of the charge that reaches the channel: sharing between strips or pixels,
  trapping after irradiation, a ballistic deficit. Example (`hit-efficiency`, Landau with
  most probable value 23 000 e and `xi = 1500 e`, about 300 um of silicon; ENC 1000 e,
  `sigma_thr = 300 e`, CR-RC^2 with `t_p = 25 ns`, series noise, 25 ns window; targets
  efficiency >= 99 % and noise occupancy <= 10^-4): the window runs from 4500 e
  (occupancy 5.7e-5; 4.1e-4 at 4000 e) to beyond 9000 e with the full charge; with half the
  charge on the channel (track at a strip boundary) the efficiency at 9000 e is 98.8 %, so
  the window ends at 8500 e; with 20 % of the charge no threshold meets both targets. The
  Landau low tail is thinner than that of real thin silicon (Bichsel straggling,
  delta-ray escape, cluster splitting): use the measured charge spectrum on the channel for
  the inefficiency below about 1 %, and the measured noise tail above about 6 sigma. For that
  low-side tail, give the measured spectrum as a table (`hit-efficiency --signal-model table
  --spectrum FILE`, CSV `charge,density` or `charge,count`); the table is normalized over its
  range, so it must reach far enough up that the missing tail is negligible. For the
  `noise-digitization` tail source of the Geant4 adapter's `simreco`, `--simreco-channels N`
  (channels per side of a plane; one threshold, also given as `--threshold-enc` in noise
  sigmas) prints its `threshold` (the fraction of the most probable charge), `efficiency`
  and `noise_hits_per_plane` (two sides: both powers of two); simreco's defaults stay.
- **Zero suppression** with seed/neighbour thresholds keeps clusters but truncates
  their tails; cluster charge and centroid are then biased for low-`S/N` clusters, and
  the bias differs between data and simulation if the thresholds or noise differ.
- **Thresholds and the response**: a threshold turns a gain or noise drift into an
  efficiency change only for signals near it; the most exposed populations are
  minimum-ionizing particles in thin sensors, single photoelectrons, and low-energy
  showers.

## Amplitude and time from sampled waveforms (moved)

Now in [front-end waveform processing](front-end-waveform-processing.md#amplitude-and-time-from-sampled-waveforms).

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
  baseline; calibrate per channel with injected charge. The shape of `ToT(Q)` is
  device-specific: roughly logarithmic in `Q` when the pulse tail is exponential, nearly
  linear with a constant-current discharge of the feedback. The charge resolution is
  `sigma_ToT / (dToT/dQ)`, so it degrades where `ToT(Q)` flattens, and the inverse is
  steep near threshold, where a small threshold shift moves the reconstructed charge most.
  Invert the measured curve channel by channel in reconstruction and generate ToT from the
  same curve (with its spread) in simulation, never from a generic shape.

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
- **Bandwidth and rise time.** For a single-pole system the 10-90 % rise time is
  `2.2 RC = 0.35 / f_3dB` (*exact*). The rms widths of cascaded responses add in quadrature
  (*exact*: variances add under convolution of non-negative responses); 10-90 % rise times
  only approximately so. More bandwidth sharpens the edge but admits more series noise, so
  the jitter `t_r / (S/N)` has an optimum bandwidth rather than improving without limit.
- The per-detector budgets (sensor, photostatistics, calibration, geometry, reference
  time) are in [timing detectors](timing-detectors.md).

## Pileup of pulses, baseline, and rate (moved)

Now in [front-end waveform processing](front-end-waveform-processing.md#pileup-of-pulses-baseline-and-rate).

## Photosensor readout (moved)

Now in [front-end waveform processing](front-end-waveform-processing.md#photosensor-readout).

## LAr TPC signal processing (moved)

Now in [front-end waveform processing](front-end-waveform-processing.md#lar-tpc-signal-processing).

## Digital pulse processing for spectroscopy (moved)

Now in [front-end waveform processing](front-end-waveform-processing.md#digital-pulse-processing-for-spectroscopy).

## Pulse-shape discrimination (moved)

Now in [front-end waveform processing](front-end-waveform-processing.md#pulse-shape-discrimination).

## Radiation and the electronics

- **Single-event upsets** flip configuration or data bits: channels become noisy, dead,
  or mis-configured until reconfigured, so inefficiency grows during a fill and tracks
  luminosity; it is absent from a static dead-channel map unless that map is
  time-dependent.
- **Total ionizing dose** shifts thresholds, gain, and leakage of the front-end
  itself; recalibrate thresholds and monitor S-curves versus dose.
- **Sensor damage** raises leakage current (Noise above) and reduces collected charge;
  the signal-to-noise ratio falls from both sides.

## Calibration of the electronics (moved)

Now in [front-end calibration and simulation](front-end-calibration.md#calibration-of-the-electronics).

## Simulation of the electronics (moved)

Now in [front-end calibration and simulation](front-end-calibration.md#simulation-of-the-electronics).

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
- **"Fit S-curve fractions by least squares."** Use the binomial likelihood.
- **"Injection gain is the signal gain."** No ballistic deficit or sensor in the injected
  pulse; cross-check with a physics signal.
- **"Trim leaves D/sqrt(12)."** Only for channels within the trim range.
- **"Five sigma means no fake hits."** Multiply by channels, window, and `nu` (not `nu_0`).
- **"Noise is per channel and independent."** Coherent noise can dominate sums.
- **"The dead-channel map is static."** Upsets, dose, and temperature change it.
- **Electronics nonlinearity calibrated away as a physics effect** (SiPM saturation,
  gain switching).
- **"Efficiency is `Phi((Q - T)/sigma)` at the mean charge."** Average over the charge
  distribution on the channel; sharing and trapping move the operating window.
- **"A Landau fit predicts the inefficiency."** Its low tail is too thin for thin silicon;
  measure the charge spectrum near threshold.
- **"Noise occupancy is the Rice rate."** For sampled comparisons it is the per-sample tail
  probability; for a gated binary channel both terms.
- **"A phase-insensitive filter is free."** The constraint costs noise; quote both.

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
- The operating window: efficiency and noise occupancy versus threshold for the charge on
  the channel (with sharing and radiation), and its evolution with dose.
- The electronics calibration chain in its order (pedestal, noise covariance, gain and
  linearity, S-curve thresholds and trim, timing, templates and weights), the fit method and
  errors of each constant, its conditions and intervals of validity, and the calibration
  closure in simulation.
- For simulation, the digitization, overlay and closure deliverables of
  [readout digitization and overlay](readout-digitization-and-overlay.md).
