# Front-End Calibration and Simulation

The calibration chain of the electronics and its simulation, moved from
[front-end electronics and signal processing](front-end-electronics-and-signal-processing.md), which keeps
the noise, threshold and timing relations these steps measure.
`<plugin root>/skills/hep-detector/scripts/frontend_response.py` gives `s-curve` and `threshold-trim`.

## Calibration of the electronics

Electronics calibration produces the per-channel constants that reconstruction applies and
simulation must reproduce. Its order is part of its definition: pedestal and noise, then
gain and linearity, then thresholds and trim, then timing and pulse templates; the
absolute scale with physics signals (minimum-ionizing particles, sources, resonances) comes
after, in [calibration and alignment](calibration-and-alignment.md). A constant derived
before a step it depends on (a gain measured with a stale pedestal) carries that error into
everything downstream.

- **Pedestals and noise**: dedicated runs or random triggers, per channel, versus
  temperature and time. Where signals can be present, use a robust estimate (median, or
  iterative exclusion of hit channels, as for the common mode). Keep the noise as a
  covariance (sample autocorrelation and channel correlations), not only a sigma: the
  optimal filter and the digitization both need it.
- **Charge injection** (test pulse): gain and linearity per channel, with the integral
  nonlinearity from the residuals of the linear fit. The absolute scale carries the
  uncertainty of the injection capacitor and the pulser amplitude, common to all channels
  injected by the same circuit: a correlated scale systematic, not per-channel scatter.
  An injected pulse is not a sensor signal (no collection time, so no ballistic deficit;
  sometimes without the sensor capacitance), so the injection gain and the physics-signal
  gain differ; cross-check with a source or minimum-ionizing particles.
  <!-- example: source citation -->
  The ATLAS liquid-argon calorimeter carries an explicit physics-to-calibration pulse ratio
  (`M_phys/M_cali`) in its cell-energy formula (N. Nikiforou for ATLAS, arXiv:1306.6756v2,
  sec. II-C; read 2026-10-25); its readiness paper defines `1/(M_phys/M_cali)` as the ratio
  of the responses to a calibration pulse and to an ionization pulse of the same input
  current (G. Aad et al., arXiv:0912.2642v4, sec. 3.1.2, eq. 5; read 2026-10-25).
  <!-- /example -->
- **Threshold scans** (S-curves): fit hits out of `N` injections at each charge with a
  binomial likelihood for `Phi((Q - T)/sigma)` (`frontend_response.py s-curve`), not a
  least-squares fit to fractions, which mis-weights the points near 0 and 100 % and cannot
  use a point at 0/N. The fitted width is the quadrature sum of the channel noise, the
  injection-amplitude noise and any threshold drift during the scan. Steps of about
  `sigma/2` across the turn-on make the errors scale as `1/sqrt(N)`: with 8 charges every
  200 e, 100 injections each and `sigma = 300 e`, `sigma_T ≈ 18 e` and `sigma_sigma ≈ 17 e`
  (6 %; a Monte Carlo of 2000 scans gives 17.9 and 17.5 e with pulls 0.98 and 1.02 wide, and
  the maximum-likelihood sigma about 0.1 of its error low). A poor fit (non-Gaussian noise,
  crosstalk, a drifting threshold) means the width is not the ENC.
- **Threshold trim**: a trim DAC of `2^b` codes of step `D` leaves a uniform residual of
  rms `D/sqrt(12)` for channels inside its range and the excess for those beyond it
  (`threshold-trim`; *exact* for a Gaussian spread much wider than `D`). Example: an
  untrimmed spread of 1500 e with 4 bits of 250 e leaves 18 % of channels beyond the range
  and a residual dispersion of 442 e, not 72 e (a Monte Carlo of the trim codes agrees).
  The residual is the `--threshold-dispersion` of `hit-efficiency`; it grows with dose, so
  retrim on a schedule and keep the trim codes as conditions.
- **Timing**: per-channel offsets, walk curves, TDC bin widths by code density, clock
  phase per board.
- **Photosensors**: single-photoelectron spectra (gain), LED/laser linearity, dark rate
  and crosstalk versus temperature and dose.
- **Pulse shape and filter weights**: templates per channel and gain from the average of
  normalized, time-aligned data pulses (misalignment broadens the template and biases the
  amplitude, so iterate the alignment), and optimal-filter weights recomputed when the
  noise or pileup conditions change, stored with the conditions they assume.
- **Calibration closure in simulation**: run the same calibration procedures on simulated
  calibration data (pedestal runs, injection, S-curves) and check that they return the
  constants the digitization was given; a mismatch (a gain defined at a different point of
  the chain, a threshold in different units) is a digitization-calibration inconsistency
  that no physics calibration removes.
- **Monitoring**: track pedestals, noise, gains and thresholds over time
  (`stability_monitor.py`) and store all constants as conditions with intervals of
  validity ([calibration and alignment](calibration-and-alignment.md)).

## Simulation of the electronics

Simulate the electronics in the same order as the hardware, from the conditions of the
period being simulated: induced signal, preamplifier and shaper, noise with its measured
correlations, sampling phase, pileup over the whole pulse support, the sum in the linear
domain and then the nonlinearities (saturation, gain selection, ADC, pedestal), firmware
feature extraction and zero suppression bit for bit, and reconstruction with the same
templates, weights and constants as data. The step-by-step recipe, the rules for overlay
and premixing (no noise counted twice, the sum taken before saturation and zero
suppression, a suppressed overlay loses sub-threshold content, overlay from the same
period, pileup counted once) and the closure checks that validate the digitization are in
[readout digitization and overlay](readout-digitization-and-overlay.md).
