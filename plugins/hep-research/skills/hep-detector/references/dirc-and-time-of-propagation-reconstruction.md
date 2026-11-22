# DIRC and Time-of-Propagation Reconstruction

Reconstruction for Cherenkov counters whose radiator is also the light guide: photons trapped by total internal
reflection in a bar or plate are imaged after transport in pixel position and arrival time. Ring imaging in an
expansion volume, the per-pixel likelihood, background and ring finding:
[Cherenkov ring reconstruction](cherenkov-ring-reconstruction.md); radiators and photosensors:
[Cherenkov imaging variants](cherenkov-imaging-variants-and-photosensors.md); event time and its bias:
[event time and timing association](event-time-and-timing-association.md); module time offsets and alignment from
data: [in-situ calibration](in-situ-calibration-methods.md); time-PDF shapes:
[resolution shape models](resolution-shape-models.md). Simcal of DIRC optics is hep-statistics'
([DIRC simcal](simulation-calibration/dirc.md)).

Environments: COL collider; FXT fixed target, test beam; SPC space, balloon; UGD underground; GND ground arrays;
NUC nuclear. Bar geometry, expansion region, pixel size, photosensor transit-time spread, readout time window,
background rate and the start-time source are parameters. Source IDs as in the ring page. Pages are PDF pages.

## Relations (with source locators)

- **Transport** (exact for a flat, rectangular radiator made to optical precision;
  pdg_2025_particle-detectors-at-accelerators sec. 35.5, p. 23; arXiv:hep-ex/0010068 p. 3): reflections at the
  bar faces conserve the magnitude of the Cherenkov angle, so the photons can be imaged outside the particle's
  path in up to three dimensions, two in space and, from the long paths, one in time. For `beta ≈ 1` some photons
  always lie inside the total-internal-reflection limit.
- **Per-track angle** (approximate: no correlated errors; arXiv:hep-ex/0010068 eq. 1, p. 3):
  `sigma_C,track = sigma_C,gamma / sqrt(N_pe)`; the geometric term (bar, pixel and expansion sizes) and the
  chromatic term set `sigma_C,gamma`, the photosensor transit-time spread the time resolution.
- **Time-imaging extended likelihood** (exact given the PDFs; arXiv:2504.19090 sec. 8.2, eq. 12, p. 33):
  `ln L_h = sum_i ln[(N_h S_h(c_i, t_i) + N_B B(c_i, t_i)) / (N_h + N_B)] + ln P_mu(N)`, `c_i` the pixel and `t_i`
  the arrival time of photon `i`, `N_h` and `S_h` the hypothesis yield and PDF, `N_B` and `B` the background's,
  `P_mu(N)` the Poisson probability of `N` photons for `mu = N_h + N_B`.
- **Signal PDF per pixel** (approximate: Gaussian peaks; sec. 8.2, eq. 13, p. 34):
  `S_h(c, t) = sum_k f_ck sum_j f_j G(t - t_ck - t_TTS,j; sigma_ck (+) sigma_TTS,j (+) sigma_el)`: one peak `k`
  per photon path (number of internal reflections), with position `t_ck`, width `sigma_ck` and fraction `f_ck`
  computed analytically by inverse ray tracing for each hypothesis, convolved with a multi-Gaussian transit-time
  spread measured per tube and an electronics term set per photon from its amplitude.
- **Background PDF** (approximate: uniform in time; sec. 8.2, eq. 14, p. 34):
  `B(c, t) = (eps_c / sum_c' eps_c') / (t_2 - t_1)`, `eps_c` the pixel's photon detection efficiency (quantum,
  collection and threshold, corrected for ageing) in the window `[t_1, t_2]`.
- **Start time** (a parameter; sec. 8.2, p. 33): times are measured from the event start and so include the
  particle's time of flight. With a bunch clock (COL) the start is found by maximizing the summed `ln L` of
  identified tracks over a common offset, then rounding to the nearest bunch crossing (p. 34). Elsewhere the start
  comes from a trigger counter, a time-of-flight system, or the same offset fit left unrounded (not in the sources
  read; [event time](event-time-and-timing-association.md)).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Pin-hole or mirror imaging through an expansion region | Per-photon angle from pixel, time and track; likelihood per hypothesis | Bar and expansion geometry, alignment; photon yield per incidence angle | Several paths reaching one pixel (the peaks of eq. 13) left unmodelled give structured background | COL (arXiv:hep-ex/0010068 p. 3); FXT (arXiv:2002.07990 sec. 3, p. 5) |
| Compact imaging, ring folded on itself | Analytic `(pixel, time)` PDF per hypothesis and path, extended likelihood | Per-tube transit-time spread and efficiency; electronics resolution; start time | `beta` from a ring radius is impossible here (arXiv:2504.19090 sec. 8.1, p. 33); wrong start time shifts all hypotheses | COL only in the sources read (arXiv:2504.19090 secs. 8.1-8.2) |
| Background yield | Event by event from hits in modules without a track | Several modules; uniform-in-time model | Light of other tracks in the module is not uniform (inferred; not tested in the source) | COL only in the sources read (arXiv:2504.19090 sec. 8.2, p. 33) |
| Module time offsets | Maximize muon likelihoods over a per-module offset, after a pairwise least-squares start | Two-track events crossing different modules | A start-time error absorbed into module offsets (inferred) | COL only in the sources read (arXiv:2504.19090 sec. 7.3, p. 33) |
| Chromatic dispersion | Time imaging or focusing optics correct it | Fast pixelated photosensors (multi-anode or microchannel-plate PMTs) | Uncorrected, it enters `sigma_C,gamma` (arXiv:hep-ex/0010068 p. 3) | COL only in the sources read (pdg_2025_particle-detectors-at-accelerators p. 23) |

<!-- example: named apparatus and their numbers -->
- BaBar DIRC (COL): 4.9 m fused-silica bars (`n ≈ 1.473`), pin-hole imaging through 6000 l of water onto 10752
  PMTs about 1.2 m from the bar end; single-photon 10.2 mrad (9 expected), 1.7 ns (1.5 ns PMT transit-time
  spread); 20 to over 50 photoelectrons with dip angle; 2.8 mrad per track in dimuons (2.2 simulated); about
  3.8 sigma pi/K at 3 GeV/c (arXiv:hep-ex/0010068 pp. 3-5).
- Belle II TOP (COL): six hypotheses; transit-time spread of one tube type fitted with four Gaussians (33.5, 114,
  199, 552 ps; 46, 32, 15, 7%); correct bunch crossing found above 99%; module `t0` to better than 10 ps, common
  `t0` to about 10 ps, from dimuons (arXiv:2504.19090 secs. 7.3-7.4, 8.1-8.2, Fig. 37, pp. 33-34).
- GlueX DIRC (FXT): four former BaBar bar boxes, mirrors in water, MAPMTs; pion and kaon samples from exclusive
  rho and phi photoproduction; 15 to 35 photons per track; per-photon `theta_C` 0.8240 (pi) and 0.8173 rad (K) for
  `p > 3.8 GeV/c`, about 8 mrad per photon (arXiv:2002.07990 secs. 2-3, Fig. 7, pp. 3-6).
<!-- /example -->

## Distinctive but generalizable features (DIRC and TOP)

- **Topology**: a few tens of photons in (pixel, time), each with several possible paths.
- **Inverse problem**: species from `theta_c` and time of propagation; degeneracies: path ambiguity, start time
  versus time of flight, chromatic spread.
- **Natural objects**: photon `(c, t)`, path hypothesis, `ln L` per hypothesis.
  **Informative residual**: `t - t_ck` per pixel for identified tracks; per-photon angle residual per path.
- **Scaling**: Relations, each within its domain.
- **Conventions**: time origin (bunch, trigger or fitted); whether `ln P_mu(N)` is included.
- **Tails**: late transit-time components, scattered or wrongly reflected photons, other tracks in the bar.
- **Dependence**: bar surface quality, glue and window transmission, tube efficiency and ageing, temperature.
- **Data sample**: dimuons and kinematically identified decays (COL); exclusive reactions (FXT).
- **Transfers**: the extended likelihood, path enumeration, track-free background. **Does not transfer**:
  bunch-crossing rounding; peak positions tied to one bar geometry.

## Common misconceptions and failure modes

- **A start time treated as known.** A biased `t0` moves every hypothesis's time PDF; it is a parameter, and with
  a bunch clock it is found from the same likelihood ([event time](event-time-and-timing-association.md)).
- **Ignoring path ambiguities.** Unmodelled paths are a structured background, not noise.
- **Gaussian timing.** Transit-time spreads have late components; use the measured per-tube shape.

## Deliverables

- Optics model and path enumeration, per-tube transit-time spread and efficiency, start-time source and status.
- Likelihood form with yields, background yield method, and the time-residual check per pixel.
- PID efficiency and misidentification versus momentum and incidence angle at the stated cut.

## Tool hooks

- **Inputs**: tracks at the bar (position, direction, momentum, covariance); hypotheses; bar and optics geometry;
  pixel map with efficiency; per-tube transit-time spread (fractions, offsets, widths in ps); hits (pixel, time in
  ns, amplitude); start time with its source and uncertainty; window `[t_1, t_2]`.
- **Outputs**: per track `ln L` per hypothesis, `Delta ln L`, `N_h`, `N_B`, the fitted offset if fitted;
  per photon the most likely path.
- **Closure and negative control** (required): on identified tracks, the mean time residual of the assigned peak
  per pixel group must lie within a tolerance fixed in advance of zero; the negative control shifts all photon
  times by a multiple of that tolerance fixed in advance, which must fail. `failed` if the true check fails;
  `inconclusive` below a count fixed in advance or if the control passes; else `passed`.
- **Statuses**: per track `ok`, `no-photons`, `start-time-missing`, `out-of-acceptance`; per check `passed`,
  `failed`, `inconclusive`.

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| DIRC angle imaging | arxiv_hep-ex_0010068, pdg_2025_particle-detectors-at-accelerators | arxiv_2002.07990 | gap | gap | gap | gap |
| Time-imaging (TOP) likelihood | arxiv_2504.19090 | gap | gap | gap | gap | gap |
| Start time as a parameter | arxiv_2504.19090 (bunch crossing) | gap: [event time](event-time-and-timing-association.md) | gap: [event time](event-time-and-timing-association.md) | gap | gap | gap |
| Track-free background yield | arxiv_2504.19090 | gap | gap | gap | gap | gap |

`gap`: none in the sources read (COL, FXT, SPC) or not surveyed (UGD, GND, NUC). The time-imaging likelihood is
sourced in one environment (COL) only.

## Citations

Read in arXiv e-prints (PDG: 2025 review PDF), 2026-11-17 to 22. Entries: the
[particle identification bibliography](detector-principles-bibliography-particle-identification.md), section
"Cherenkov ring and DIRC reconstruction"; PDG RPP 2025: main [bibliography](detector-principles-bibliography.md).
