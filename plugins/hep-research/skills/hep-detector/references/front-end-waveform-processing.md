# Front-End Waveform Processing

Reconstruction from sampled waveforms and the signal processing of particular readouts, moved from
[front-end electronics and signal processing](front-end-electronics-and-signal-processing.md), which keeps
the chain, signal induction, shaping, noise, thresholds, digitization, time pickoff and radiation effects.
`<plugin root>/skills/hep-detector/scripts/frontend_response.py` gives `optimal-filter`, `waveform-toy` and
`pileup` for the numbers below.

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
- **Constrained filters** (*exact* for the linear model; Lagrange multipliers): minimizing
  `w^T R w` subject to `w · g = 1` and `w · c_k = 0` gives `w = R^-1 C (C^T R^-1 C)^-1 e_1`
  with `C = [g, c_1, ...]` and variance `((C^T R^-1 C)^-1)_11`. With `c = g'` (Cleland and
  Stern) the first-order phase sensitivity vanishes; with `c = (1, ..., 1)` a constant
  baseline offset (pedestal drift, the mean of unipolar pileup) does not bias the amplitude.
  Each constraint costs noise. Example (`optimal-filter`: CR-RC^4, `t_p = 45 ns`, 7 samples
  every 25 ns from three before the peak, `rho = 0.6`, pileup 2 MHz of rms amplitude
  4 sigma): unconstrained sigma 1.38 with phase bias +1.9 % / −3.0 % at ∓2 ns and
  `sum w = 0.56`; with the phase constraint sigma 1.40 and −0.5 % at either sign (second
  order); with the baseline constraint sigma 1.49 and `sum w = 0`.
  <!-- example: source citation -->
  The ATLAS liquid-argon reconstruction computes its amplitude and time coefficients this
  way, from the pulse shape, its derivative and the noise autocorrelation of pedestal runs
  (M. Aharrouche et al., arXiv:0709.1094; read 2026-10-25).
  <!-- /example -->
- **Baseline gain.** A constant offset `b` on every sample biases any linear estimate by
  `b sum w`. For unipolar pulses `sum w` is of order one unless a baseline constraint or
  pre-samples are used, so a pedestal error or the Campbell mean of pileup (`nu <a> ∫ g dt`)
  appears directly as an amplitude bias that changes with luminosity.
- **Time from samples.** A joint fit of amplitude and time (model `A g(t + d)`) has, to
  first order, the inverse Fisher matrix of the columns `g` and `A g'` as covariance
  (*approximate*, linearized at the true phase). Example: CR-RC^4, `t_p = 45 ns`, 5 samples
  every 25 ns from one before the peak, white noise, `A = 50 sigma`: `sigma_t = 0.43 ns`,
  `sigma_A = 0.79 sigma` (a least-squares Monte Carlo gives 0.431 ns and 0.78). Below
  `A/sigma` of about 10 the free-time fit follows the noise and the linearized error is
  optimistic.
- **Pulse-shape stability**: pulse shape changes with temperature, gain switch, and
  radiation; a template measured once is a conditions item with a validity range.
- **Checking an estimator before full simulation.** `frontend_response.py waveform-toy`
  simulates the sampled pulse with correlated noise, Poisson pileup, phase jitter and an
  ADC, and reconstructs it with the largest sample, the uncorrelated template, and optimal
  filters with electronic-only and pileup-matched weights; without jitter and ADC the bias
  and width of each must agree with the analytic prediction (closure z-scores), and with
  them the departure measures the effect of jitter or quantization. It is synthetic and
  establishes the estimator's behaviour, not the detector's.

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

## Digital pulse processing for spectroscopy

- In spectroscopy (germanium, silicon drift detectors, bolometric and rare-event
  readout) the preamplifier output is digitized and shaped digitally. Recursive algorithms
  give trapezoidal or triangular shapes in real time (V. T. Jordanov and G. F. Knoll, Nucl.
  Instrum. Methods A345 (1994) 337); a flat top longer than the spread of charge-collection
  times removes the ballistic deficit and reduces the effect of charge trapping, which a
  sharply peaked shape of the same noise would not.
- The rise (integration) time sets the series-parallel noise trade as the peaking time does
  for an analog shaper (Shaping above); the flat top and rise time together set the dead
  time per pulse, so resolution trades against throughput. A fast parallel channel (short
  shaping) detects pileup and rejects or flags it; the rejected fraction is a rate-dependent
  live-time loss to be measured ([triggers luminosity pileup](triggers-luminosity-pileup.md)).
- The digital deconvolution of the preamplifier decay (pole-zero in the digital domain)
  must use the per-channel decay constant: a wrong one tilts the flat top, so the amplitude
  depends on where it is sampled and the resolution degrades with rate.

## Pulse-shape discrimination

- Discrimination by pulse shape (scintillators with neutron-gamma separation, prompt
  fraction in liquid argon, single- versus multi-site events in germanium) reconstructs a
  shape variable, typically the ratio of tail (or prompt) charge to total charge, from the
  digitized waveform ([noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md)).
- The usual figure of merit `FOM = |mu_1 - mu_2| / (FWHM_1 + FWHM_2)` assumes two Gaussian
  peaks. When the width of the ratio is set by photoelectron statistics (a binomial prompt
  fraction), it scales as `1/sqrt(N_pe)`, so the FOM falls toward low energy as about
  `sqrt(E)` (*approximate*). Quote the FOM, and above all the measured leakage at the stated
  acceptance, in energy bins: the leakage at 10^-6 and beyond is set by non-Gaussian tails
  (pileup, afterpulses, baseline errors, saturation), which a FOM does not predict.
- The shape variable depends on the digitization: the sampling rate and bandwidth that
  resolve the prompt part, the baseline estimate, the integration windows and their
  alignment to the pulse start, and saturation of large pulses. Simulate the shape variable
  through the same digitization chain, or calibrate its distribution on tagged data.
