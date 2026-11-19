# Timing Detectors and Time Measurement

Timing and fast detectors: time-of-flight (TOF), fast scintillator layers, low-gain
avalanche detectors (LGAD, including ultra-fast silicon), microchannel-plate (MCP) timing
detectors, precision timing in trackers and calorimeters, and beam/start-time,
bunch-timing, and luminosity monitors. The TOF physics (`beta`, `m^2`, separation
ceiling) is in [particle identification](particle-identification.md); event-level timing/association is in
[event reconstruction](event-reconstruction.md); `<plugin root>/skills/hep-detector/scripts/pid_separation_power.py` evaluates
TOF separation. This file adds the timing-error budget and the objects. Environment codes
used here: COL collider; SPC space and balloon; UGD underground, neutrino and rare-event;
GND ground-based cosmic-ray and gamma-ray arrays; NUC nuclear and low-energy.

## Relations (definition, exact unless noted)

```
beta = L / (c t)        m^2 = p^2 (1/beta^2 - 1)      Delta t = (L/c) [ (1/beta_1) - (1/beta_2) ]
```

`L` path length along the track (not straight-line distance; requires the track fit),
`t` measured flight time (stop minus start), `p` momentum. The TOF separation of two
species with the same `p` in the ultrarelativistic limit is
`Delta t ≈ (L/(2 c p^2))(m_1^2 - m_2^2)` (approximate, valid only for `p >> m`); separation in
`N_sigma` falls as `1/p^2` and is lost above a momentum set by `L` and total time resolution.
At `p` comparable to `m`, where TOF is used, take the exact form above (the limit overestimates
`Delta t` by 22% for pi/K at 0.5 GeV/c and by a factor of about 2 at 0.2 GeV/c); below `m` the
difference falls as `1/p` ([core detector equations](core-detector-equations.md), E8).

## Pulse-time extraction

- **Leading-edge discriminator**: fixed threshold; **time walk** (larger pulses cross
  earlier) must be corrected with amplitude or ToT (a calibration curve per channel).
- **Constant-fraction discrimination (CFD)**: time at a fixed fraction of the peak;
  removes amplitude dependence to first order, at the cost of jitter and pulse-shape
  sensitivity (an input to calibration).
- **Waveform fit / template**: best precision if the pulse shape and noise are known;
  fits amplitude and time jointly.

The **jitter** term is `sigma_t ≈ sigma_noise/(dV/dt)` (noise over slope; approximate
for a Gaussian noise and linear rising edge), which is why fast, high-gain, low-noise
front ends win.

## Time-resolution budget (single hit)

`sigma_t^2 = sigma_sensor^2 + sigma_photostat^2 + sigma_elec^2 + sigma_clock^2 +
sigma_calib^2 + sigma_geom^2 + sigma_ref^2`

| Term | Origin | Scaling / handle |
|---|---|---|
| Sensor / intrinsic | single-photoelectron transit-time spread (PMT, MCP, SiPM), entering a many-photon hit about as `TTS/sqrt(N_pe)`; Landau (silicon), drift (gas) | detector design; the silicon and gas terms are irreducible per hit |
| Photostatistics | first-photon time `tau_decay/N_pe` (negligible rise time); `k`-th photon `~ sqrt(k) tau_decay/N_pe`; with rise time `~ sqrt(tau_rise tau_decay/N_pe)` (approximate; `tau_decay`, `tau_rise` the scintillation decay and rise times, not the dead time `tau_d` of the [glossary](detector-glossary.md)) | more photons, faster rise and decay |
| Electronics | jitter (`noise/slope`), TDC bin `/sqrt(12)` (rms over random phases; at a fixed phase it averages out only with >= 0.5 bin of noise), time walk | design, calibration ([front-end electronics](front-end-electronics-and-signal-processing.md)) |
| Clock | distribution jitter and offsets | global part: common to all channels, not averaged, but cancels in time differences within one event; local part (per board/PLL): averages over independent boards |
| Calibration | `t0` per channel, walk curve, cable/fiber delay | in-situ residual method |
| Geometry | path length, position along the bar, `L` error | tracking quality |
| Reference/start time | the experiment's start-time source: collision or bunch-crossing time (COL); the prompt gamma flash of a pulsed neutron source, corrected for its flight time (NUC; arXiv:2505.00042, sec. 4.1); a timing plane of the same instrument, so `t` is a difference of two measured times and both planes' terms enter (SPC; [particle identification](particle-identification.md)); or an event time fitted with the direction or vertex from the hit times (GND, UGD; [ground-based detection arrays](ground-based-detection-arrays.md), [neutrino astronomy](neutrino-astronomy.md)) | improves as `1/sqrt(N_tracks)` when estimated from tracks; dominates in low-multiplicity events or when only the bunch-crossing spread is known (COL) |

Keep four resolutions apart: **single-hit** (one channel), **per-track** (all hits on
one track, after averaging the uncorrelated part), **event-time** (start time
estimated from many tracks), and **system** (what the analysis sees, including the
common-mode clock and reference terms). Averaging `N` hits reduces only the
uncorrelated terms as `1/sqrt(N)`; correlated ones (clock, `t_ref`) remain.

**Track-to-hit association and multi-hit ambiguity.** A time is meaningless without the
right track: extrapolate the track to the layer, match by position (and time), and
resolve multiple candidate hits/tracks per cell. Wrong association creates a late/early
tail. **Time-window assignment**: the measured time must be assigned to the right time
window of the experiment's start-time source, the bunch crossing at a collider (COL). A
self-triggered instrument has no external window: its own timing planes or a fitted
event time set the reference, and the ambiguity is instead the direction of travel, the
sign of the time difference between planes (SPC; arXiv:hep-ex/0305074, sec. 2;
[particle identification](particle-identification.md)), or the synchronisation of many
stations or optical modules (GND, UGD; PDG RPP 2025, sec. 36.3.2). Out-of-time pileup and
late tails (afterpulses, delayed light, slow components) produce non-Gaussian tails and
mis-assigned windows, so quote core width and tail fraction separately.

## Technologies

- **Fast scintillator with PMT/SiPM (TOF bars, layers)**: `~ tens of ps` class
  achievable in principle by photostatistics, limited in practice by electronics,
  clock, position along the bar, and light-collection non-uniformity (quote only from a
  named apparatus). Position along the bar from time difference of two ends.
- **LGAD / ultra-fast silicon**: internal gain of order 10-50 with a thin sensor gives
  a steep, low-jitter pulse; time resolution is limited by Landau fluctuations in
  the thin depletion region and by the electronics (PDG RPP 2025 eq. 35.25: walk from
  signal-height fluctuations at threshold, jitter `sigma_n/(dS/dt)`, an irreducible
  arrival-time term from non-uniform charge deposition, weighting-field distortion and
  TDC terms; 15-20 ps for minimum-ionizing particles reached with thin, high-gain
  (> 40) LGADs, better only with several layers; walk, jitter and CFD formulas are in
  [front-end electronics](front-end-electronics-and-signal-processing.md)); **radiation damage** reduces the
  effective doping (gain layer), so gain and time resolution degrade with fluence and
  operating voltage must be raised (single-event burnout limit); fill factor at
  pad boundaries is a design issue.
- **MCP timing detectors**: fast rise and small transit-time spread; used as
  precision photon/particle timing; aging by charge extracted, ion feedback.
- **RPC/MRPC**: gas gap timing, rate-dependent ([gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md)).
- **Precision timing in trackers/calorimeters**: time assigned to tracks or clusters
  (e.g. shower-time for photons, vertex-time for pileup rejection); needs the same
  calibration/clock discipline, and a time-of-arrival correction for shower depth and
  time-walk with energy.
- **Beam/start-time, bunch-timing, luminosity monitors**: give `t_0` and bunch
  identification; beam-phase drift and asymmetric bunch shapes are systematic inputs to
  every timing analysis ([triggers luminosity pileup](triggers-luminosity-pileup.md)). Luminosity monitors
  count coincidences or hits and carry their own linearity/pileup correction.

## Calibration and diagnostics

Per-channel `t0` and walk from a common reference (laser, pulser, minimum-ionizing
particle), then the global offset (start time) and the distribution of the experiment's
reference clock: the accelerator clock at an accelerator; synchronisation signals sent
to the optical modules, checked with in-situ LED or laser flashers (UGD neutrino
telescopes; PDG RPP 2025, sec. 36.3.2); the synchronisation of fluorescence and surface
detectors of a hybrid air-shower array (GND; sec. 36.2.1); or the instrument's own
trigger and clock (SPC; arXiv:hep-ex/0305074, sec. 2); validated with **time residuals** `t_meas - t_pred(p, m, L)` per species, using a
sample of known particle type (muons, identified pions, electrons at `beta = 1`).
Residual versus amplitude reveals walk; versus position along the bar reveals
propagation; versus run/fill reveals clock drift.

### Distinctive but generalizable reconstruction and performance features (timing)

- **Topology**: time series per hit; one scalar per channel, sometimes with waveform.
- **Inverse problem**: `t` from a noisy pulse; degeneracy: absolute offset versus
  reference time versus path length.
- **Natural objects**: hit time, track time, event start time. **Informative
  residual**: time residual to the expected time for a known species vs amplitude,
  position, and run.
- **Scaling**: `1/sqrt(N_pe)` and `noise/slope`; TOF separation `~ L/p^2` for `p >> m`.
- **Conventions**: quote resolution with the reference, core Gaussian sigma and tail
  fraction; state whether clock jitter is included.
- **Tails**: wrong-bunch (COL) or wrong-window, afterpulses, late light, mis-association.
- **Dependence**: rate (baseline shifts), dose (LGAD gain, SiPM dark counts), temperature,
  clock distribution. **Data sample**: `Z`/`J/psi -> mu mu` or cosmic muons, identified
  species in overlapping momentum ranges.
- **Transfers**: walk/offset calibration and jitter budget to every timed detector;
  **does not transfer**: TOF's `1/p^2` separation ceiling to non-timing PID.

## Common misconceptions and failure modes

- **Quoting single-channel resolution as system resolution.** Correlated clock and
  reference terms do not average.
- **Ignoring path length.** A 1 cm error on `L` matters; it comes from the track fit.
- **Time-walk not corrected.** Looks like a momentum- or amplitude-dependent
  mass-hypothesis shift.
- **Radiation damage treated as a static constant.** LGAD/SiPM timing evolves with
  dose and operating point.
- **Clock offsets look like PID or alignment problems.** Check run-by-run/fill-by-fill
  offsets first ([detector case studies and checklists](detector-case-studies-and-checklists.md)).

## Deliverables

- A time-resolution budget with each term's origin and whether it averages.
- Single-hit, per-track, event-time, and system resolutions, with tail fractions.
- The association rule (track-to-hit, time-window assignment) and its failure rate.
- Calibration chain (`t0`, walk, clock) and the residual used to validate it.
