# Readout Digitization and Overlay

How to turn simulated energy deposits into simulated readout that matches the real
electronics, how to combine simulation with recorded data (overlay, premixing), and how to
show that the digitization is right. Digitization is where a simulation stops being physics
and becomes an electronics model; it is the step most often simplified and the most common
source of a data/MC difference that no calibration removes. The electronics relations used
here (induction, shaping, noise and its correlations, thresholds, optimal filtering,
quantization, pileup) are in [front-end electronics and signal processing](front-end-electronics-and-signal-processing.md); the
transport stage before it is in [detector simulation](detector-simulation.md).

**Scope.** The order of operations and the correctness rules for a digitization and an
overlay, and the closure checks that validate them. Production digitization code in an
experiment's software is a hep-computing deliverable; learned fast digitization is hep-ml's.
`<plugin root>/skills/hep-detector/scripts/frontend_response.py` gives the quick checks named below
(`hit-efficiency`, `optimal-filter`, `waveform-toy`).

## A digitization recipe

Simulate in the same order as the hardware, each step from the conditions of the period
being simulated:

1. **Charge or light** on each electrode with its own fluctuations
   ([signal formation and readout](signal-formation-and-readout.md)); then the **induced
   current** from the weighting field ([signal induction](front-end-electronics-and-signal-processing.md#signal-induction)), or an instantaneous charge
   when the collection time is short against the shaping (check with the ballistic deficit).
   Crosstalk to neighbours (capacitive division, same section) belongs here, before the
   noise is added.
2. **Electronics response.** Convolve the current with the impulse response of
   preamplifier and shaper on a time step of at most a tenth of the rise time, or use the
   analytic response for a delta-like charge; normalize so that a unit charge gives the
   calibrated amplitude, and take pole-zero, tail cancellation and the pulse template from
   the same period and gain as the data templates.
3. **Noise** with the measured covariance between samples and between channels: a Cholesky
   factor of the measured covariance (sample-by-channel blocks, including the common mode),
   or spectral synthesis from the measured noise spectrum (Gaussian Fourier amplitudes with
   random phases, inverse transform over several correlation times). Exponential sample
   correlation (an AR(1) process, as in `waveform-toy`) is a special case to check, not a
   default. Random telegraph signals and pickup come only from recorded data (overlay
   below) or measured templates.
4. **Sampling phase** from the data's distribution: locked to the bunch clock with its
   measured jitter for a collider; uniform within the clock period, smeared by the trigger
   time resolution, for asynchronous events (cosmic rays, beam-off and calibration data).
5. **Pileup**, in time and out of time, from the period's pileup profile over the whole
   pulse support before the first sample, not only inside the readout window.
6. **Sum in the linear domain, then apply the nonlinearities in hardware order:**
   preamplifier and shaper saturation, gain selection, ADC quantization with the
   per-channel nonlinearity, clipping, pedestal. A nonlinearity applied before the sum (or
   to each contribution separately) misses saturation and threshold crossings produced by
   the sum.
7. **Firmware**: feature extraction, zero suppression and trigger primitives in the same
   fixed-point arithmetic and rounding as the hardware, bit for bit wherever an efficiency is
   taken from simulation; verify the emulation on recorded raw data (emulated and online
   decisions agree, or the disagreement rate is measured).
8. **Conditions per period**: thresholds, pedestals, noise, gains, dead and noisy channels,
   and intervals affected by single-event upsets, with simulated events assigned to periods
   in proportion to the recorded luminosity
   ([event reconstruction](event-reconstruction.md#digitization-boundary-and-calibration)).
9. **Reconstruct** with the same code, pulse templates, optimal-filter weights and
   calibration constants as data for the same conditions; otherwise amplitude bias and
   resolution differ.

## Overlay and premixing

Overlaying recorded zero-bias or random-trigger data brings in the real noise and pileup,
including correlations and non-Gaussian tails, which independent Gaussian noise does not.
The rules that make it correct:

- **No noise twice.** Overlaid channels already carry electronic noise and pileup; adding
  simulated noise or pileup to them counts it twice (for equal levels the noise grows by
  `sqrt(2)`; occupancy and cluster size rise). Simulate only the hard-scatter signal on top
  of the overlay.
- **Add before the nonlinearity.** Sum the simulated signal and the overlay in the linear
  domain (pedestal-subtracted samples before saturation, gain selection and zero
  suppression), never as digitized codes or reconstructed hits: a sum of codes applies the
  pedestal twice and misses saturation and threshold crossings caused by the sum. With
  multi-gain readout the overlay must be stored in a form from which the gain the sum would
  select can be reproduced (all gains, or a linearized value).
- **Zero-suppressed overlay loses sub-threshold content.** A simulated signal just below
  threshold plus a sub-threshold noise or pileup contribution can cross it in the detector
  but not in a suppressed overlay; efficiency and charge near threshold come out low. Record
  the overlay data unsuppressed (or with lower thresholds), or quantify the bias, for
  example with `hit-efficiency` and `waveform-toy` at the period's noise and pileup.
- **Same detector, same time.** The overlay comes from the same conditions period
  (thresholds, masks, gains, pedestals) as the simulated events, with the same sampling
  phase relative to the bunch crossing; an overlay from another period brings in that
  period's detector.
- **Pileup counted once.** The overlay's own luminosity profile replaces simulated pileup;
  it must not be reweighted again for the pileup it already contains
  ([triggers luminosity pileup](triggers-luminosity-pileup.md)), and the overlay's
  trigger must be unbiased (zero bias or random).

## Validating the digitization

Each check compares simulation with data on a control observable that is not the analysis
observable ([detector simulation](detector-simulation.md#validating-the-simulation)):

- **Pedestal runs emulated**: digitize empty events and compare per-channel noise, the
  sample autocorrelation (or noise spectrum), the common-mode fraction and the noise tail
  with pedestal and random-trigger data.
- **Threshold scans emulated**: inject charge in the digitizer and compare the S-curves (50 %
  points and widths) and the noise occupancy versus threshold with the data scans.
- **Amplitude and time closure**: reconstruct known injected amplitudes and check the bias
  and resolution against phase, pileup and gain (`waveform-toy` is the quick version of
  this check).
- **Calibration closure**: run the data's calibration procedures (pedestal, injection,
  S-curve fits, trim) on simulated calibration data and recover the constants the
  digitization was given ([calibration of the electronics](front-end-electronics-and-signal-processing.md#calibration-of-the-electronics)).
- **Charge scale and sharing**: most probable value per channel after the same calibration
  chain, and cluster size and charge sharing versus incidence angle.
- Tune digitization parameters only on these control observables, with the physical
  reason stated; the remaining freedom becomes a systematic.

## Common misconceptions and failure modes

- **"Independent Gaussian noise per channel is a fair default."** Common mode, sample
  correlations and non-Gaussian tails change cluster size, occupancy and fake rates.
- **"Overlay plus simulated noise."** Noise counted twice.
- **"Add the overlay to the digitized simulation."** Sum before saturation, gain selection
  and zero suppression.
- **"A zero-suppressed overlay is complete."** It lacks the sub-threshold content that lifts
  signals over threshold.
- **"One period's conditions for all simulated events."** Thresholds, masks, gains and
  noise change with time; assign events to periods by luminosity.
- **"The firmware emulation is right because the code compiles."** Compare its decisions
  with the online ones on recorded raw data.

## Deliverables

- The digitization model step by step (recipe above), with the conditions source and
  version for each step and the period assignment of simulated events.
- The noise model: covariance or spectrum, common-mode fraction, tails, and where each
  comes from.
- The overlay configuration: what is overlaid, in which domain, from which period, whether
  suppressed, and how pileup is counted once.
- The closure checks with their results, and any tuning with its control observable and
  its remaining freedom as a systematic.
