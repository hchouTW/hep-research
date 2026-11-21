# Timing Detectors and Time Measurement

Timing and fast detectors (time-of-flight (TOF), fast scintillator layers, low-gain avalanche detectors (LGAD,
ultra-fast silicon), microchannel-plate (MCP) detectors, multigap resistive plate chambers (MRPC), precision timing
in trackers and calorimeters, beam/start-time, bunch-timing and luminosity monitors): the timing-error budget, the
simulation chain and the objects. Elsewhere: TOF physics (`beta`, `m^2`, separation ceiling) in [particle
identification](particle-identification.md), separation by `<plugin root>/skills/hep-detector/scripts/pid_separation_power.py`;
the event-level timing window in [event reconstruction](event-reconstruction.md#timing-and-event-association); event
time, bunch assignment, association, direction and station synchronisation in [event time and timing
association](event-time-and-timing-association.md); `t0`, walk and light-speed methods in [in-situ calibration
methods](in-situ-calibration-methods.md#time-of-flight-and-timing); line shapes in [resolution shape
models](resolution-shape-models.md); TOF simcal (hep-statistics) in [simulation-calibration/tof](simulation-calibration/tof.md).
Environment codes: COL collider; FXT fixed target and test beam; SPC space and balloon; UGD underground, neutrino and
rare-event; GND ground-based arrays; NUC nuclear and low-energy.

## Relations (definition, exact unless noted)

```
beta = L / (c t)        m^2 = p^2 (1/beta^2 - 1)      Delta t = (L/c) [ (1/beta_1) - (1/beta_2) ]
```

`L` path length along the track (from the track fit, not the straight-line distance), `t` measured flight time
(stop minus start), `p` momentum. Two species at the same `p`: `Delta t ≈ (L/(2 c p^2))(m_1^2 - m_2^2)` only for
`p >> m`, so `N_sigma` falls as `1/p^2` and is lost above a momentum set by `L` and the total time resolution; where
TOF is used take the exact form; for `p << m` (both masses)
the difference falls as `1/p` ([core detector equations](core-detector-equations.md), E8).

| # | Relation | Status and validity | Source |
|---|---|---|---|
| T1 | `sigma_t^2 = sigma_walk^2 + sigma_Landau^2 + sigma_distortion^2 + sigma_jitter^2 + sigma_TDC^2` (threshold time of a silicon sensor, with or without gain) | approximate: independent terms | arXiv:1704.08666 sec. 3, eq. 3-1, p. 14 |
| T2 | `sigma_jitter = N / (dV/dt) ≈ t_rise / (S/N)`; walk `sigma_walk = [t_rise V_th / S]_rms`; `sigma_TDC = Delta_t / sqrt(12)` | approximate: linear edge of amplitude `S`, rise time `t_rise`, threshold `V_th`, noise `N`; TDC term exact for a uniform phase in a bin `Delta_t` | same, secs. 3.1.1, 3.3, 3.5, eq. 3-3, pp. 15, 18-19 |
| T3 | `i = -q v · E_w` per carrier (Ramo-Shockley), summed per time step; gain-induced LGAD slew rate `dI_gain/dt ∝ G/d` (gain `G`, thickness `d`) | first exact; second approximate (gain current only, `G >> 1`; the total rises less than `G`) | same, eqs. 3-2, 4-1, 4-7, 4-8, pp. 16, 22, 27 |
| T4 | `sigma_TOT^2 = sigma_MRPC^2 + 2 sigma_TDC^2 + sigma_FEE^2 + sigma_clock^2 + sigma_cal^2 + sigma_trk^2 + sigma_event^2` for the residual `t_TOF - t_event - t_exp,i` | approximate: independent terms; written for one MRPC TOF | arXiv:1806.03825 sec. 3, eqs. 3.1-3.2, p. 5 |
| T5 | light `Q = p1 Z^2 / (1 + p2 Z^2 + p3 Z^4)` (second-order Birks with `dE/dx ∝ Z^2`); `sigma_t = P1/Z + P2` | approximate: empirical; `Q` per counter, `sigma_t` the time of flight between a pair of counters, at minimum-ionizing velocity; `P2` the electronics floor of the pair | arXiv:hep-ex/0305074 sec. 3, Fig. 4, p. 4 |
| T6 | `T = t - t_gamma + L0/c`; `E_n = m_n c^2 [1/sqrt(1 - ((L0 + lambda)/(c T))^2) - 1]`, `lambda` a stochastic moderation path | exact kinematics; simulated `lambda` makes `T -> E_n` a resolution function | arXiv:2505.00042 sec. 4.1, eqs. 6-7; sec. 6 |
| T7 | kinetic `sigma_E / E = gamma (gamma + 1) sqrt((sigma_t/t)^2 + (sigma_L/L)^2)`, `-> 2 sqrt(...)` for `gamma -> 1` | exact first-order propagation of T6 with `lambda = 0` and independent errors (derived here) | T6 |

## Pulse-time extraction

Leading-edge discriminator (walk corrected with amplitude or ToT, a curve per channel); constant-fraction
discrimination (amplitude-independent to first order, at some jitter and pulse-shape sensitivity); waveform fit or
template (best if pulse shape and noise are known). Jitter `sigma_t ≈ sigma_noise/(dV/dt)` (T2), so the slope-to-noise ratio at threshold matters: gain before the
dominant noise (sensor gain) helps, and the bandwidth has an optimum, since more admits more noise
(arXiv:1704.08666 sec. 3.3, p. 18; [time pickoff](front-end-electronics-and-signal-processing.md#time-pickoff)).

## Time-resolution budget (single hit)

`sigma_t^2 = sigma_sensor^2 + sigma_photostat^2 + sigma_elec^2 + sigma_clock^2 +
sigma_calib^2 + sigma_geom^2 + sigma_ref^2`

| Term | Origin | Scaling / handle |
|---|---|---|
| Sensor / intrinsic | single-photoelectron transit-time spread (PMT, MCP, SiPM), entering a many-photon hit about as `TTS/sqrt(N_pe)`; Landau (silicon), drift (gas) | detector design; the silicon and gas terms are irreducible per hit |
| Photostatistics | first-photon time `tau_decay/N_pe` (negligible rise time); `k`-th photon `~ sqrt(k) tau_decay/N_pe`; with rise time `~ sqrt(tau_rise tau_decay/N_pe)` (approximate; `tau_decay`, `tau_rise` the scintillation decay and rise times, not the dead time `tau_d` of the [glossary](detector-glossary.md)) | more photons, faster rise and decay |
| Electronics | jitter (`noise/slope`), TDC bin `/sqrt(12)` (rms over random phases; at a fixed phase it averages out only with about 0.5 bin of noise or more), uncorrected time walk (its residual after the walk curve is the Calibration term) | design, calibration ([front-end electronics](front-end-electronics-and-signal-processing.md)) |
| Clock | distribution jitter and offsets | global part: common to all channels, not averaged, but cancels in time differences within one event; local part (per board/PLL): averages over independent boards |
| Calibration | `t0` per channel, walk curve, cable/fiber delay | in-situ residual method |
| Geometry | path length, position along the bar, `L` error | tracking quality |
| Reference/start time | the experiment's start-time source (bunch crossing, start counter, gamma flash, own timing plane, fitted event time); per environment and with its bias: [companion](event-time-and-timing-association.md#event-time-estimators) | improves as `1/sqrt(N_tracks)` when estimated from tracks; dominates in low-multiplicity events or when only the bunch-crossing spread is known (COL) |

Keep four resolutions apart: **single-hit** (one channel), **per-track** (all hits on
one track, after averaging the uncorrelated part), **event-time** (start time
estimated from many tracks), and **system** (what the analysis sees, including the
common-mode clock and reference terms). Averaging `N` hits reduces only the
uncorrelated terms as `1/sqrt(N)`; correlated ones (clock, `t_ref`) remain.

**Association and time windows.** Wrong track or start-time window makes late or early tails (quote core and
tail fraction apart): [event time and timing association](event-time-and-timing-association.md).

## Timing simulation chain

A simulated time compares with data only if each step that shapes it is simulated and the data's calibration is then
applied:

1. **Deposit** with position and time from transport code; for silicon, Geant4 energy releases along the track keep
   the Landau term of T1 (COL; arXiv:1704.08666 sec. 4.1.1, p. 22).
2. **Carriers or photons**: drift in electric and weighting fields solved from the Poisson and Laplace equations
   (p. 21), induced current by T3; or scintillation light (with quenching, T5), propagation and photosensor response.
3. **Front end, discriminator, TDC**: amplifier response and noise, so jitter and walk (T2) arise as in data
   ([front-end calibration](front-end-calibration.md#simulation-of-the-electronics),
   [digitization](detector-simulation.md#digitization)); ToT, if the data use it, from the measured per-channel
   curve ([ToT](front-end-electronics-and-signal-processing.md#digitization-adc-and-tdc)).
4. **Calibration as in data**: light generation, PMT response, acquisition and calibration make simulated hits
   equivalent to measured ones (NUC; arXiv:2108.01384 sec. 3.1).
5. **Validation**: simulated against test-beam pulses with the same read-out (FXT; arXiv:1704.08666 sec. 4.1, p. 20);
   a time-to-energy relation known only from simulation (T6) against features of known energy (NUC; arXiv:2505.00042
   sec. 6).

Tools: [sensor and gas transport tools](sensor-and-gas-transport-tools.md),
[hep-computing operations](../../hep-computing/references/sensor-and-gas-simulation-operations.md). State which steps
were simulated: a Gaussian smear of the true time has no walk, tail or rate effect.

## Technologies

- **Fast scintillator with PMT/SiPM (TOF bars, layers)**: `~ tens of ps` class
  achievable in principle by photostatistics, limited in practice by electronics,
  clock, position along the bar, and light-collection non-uniformity (quote only from a
  named apparatus). Position along the bar from time difference of two ends.
- **LGAD / ultra-fast silicon**: internal gain of order 10-50 with a thin sensor gives
  a steep, low-jitter pulse; time resolution is limited by Landau fluctuations in
  the thin depletion region and by the electronics (PDG RPP 2025 eq. 35.25, the terms of
  T1 with an irreducible arrival-time term from non-uniform charge deposition; 15-20 ps for minimum-ionizing particles reached with thin, high-gain
  (> 40) LGADs, better only with several layers); **radiation damage** reduces the
  effective doping (gain layer), so gain and time resolution degrade with fluence and
  operating voltage must be raised (single-event burnout limit); fill factor at
  pad boundaries is a design issue. Levers (arXiv:1704.08666): gain-induced slew rate `∝ G/d` (T3), but a very thin sensor has
  a large capacitance and needs more gain (sec. 2.3.4, p. 12); saturated drift and a uniform weighting field need
  implant width about equal to the pitch, both much larger than the thickness (sec. 3.2, pp. 16-17), against fine
  segmentation (sec. 4.6, p. 29). In space, front-end power per channel over a large area favours strips over
  pixels; LGAD strips are a proposal there (SPC; inspire_2613721 sec. 1, p. 2).
- **MCP timing detectors**: fast rise and small transit-time spread; used as
  precision photon/particle timing; aging by charge extracted, ion feedback.
- **RPC/MRPC**: stacks of narrow gas gaps between resistive glass plates; leading-edge time, ToT as the amplitude
  for slewing (COL; arXiv:1806.03825 secs. 1, 3.1, pp. 2, 6). The local flux selects the electrode: ceramic at the
  highest rates, low-resistivity glass at high rate (higher dark rate), float glass at low rate (FXT; arXiv:1807.02070 sec. 2, pp. 3, 6); cluster
  size rises with field (p. 6). Further terms: pad-size walk, multi-pad clusters at pad edges, an asymmetric tail of
  unsettled origin (arXiv:1806.03825 sec. 3, pp. 5-6). Construction:
  [gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md).
- **Precision timing in trackers/calorimeters**: time assigned to tracks or clusters
  (e.g. shower-time for photons, vertex-time for pileup rejection (COL)); needs the same
  calibration/clock discipline, and a time-of-arrival correction for shower depth and
  time-walk with energy.
- **Beam/start-time, bunch-timing, luminosity monitors (COL, FXT)**: `t_0` and bunch identification
  with beam-phase drift and bunch shapes
  ([companion](event-time-and-timing-association.md#bunch-or-beam-bucket-assignment)); luminosity monitors:
  [triggers luminosity pileup](triggers-luminosity-pileup.md).

## Calibration and diagnostics

Per-channel `t0` and walk from a common reference (laser, pulser, minimum-ionizing
particle); the walk curve must span the amplitude range of the data: for nuclei (SPC, NUC,
heavy-ion beams) the deposit scales as `Z^2` (the light as T5, with saturation at high `Z`), so a curve from
minimum-ionizing particles does not transfer ([front-end electronics](front-end-electronics-and-signal-processing.md#time-pickoff)).
Then the global offset (start time) and the distribution of the reference clock: the accelerator clock, distributed
clocks with round trips and flashers (UGD), GPS stations (GND)
([synchronisation](event-time-and-timing-association.md#synchronisation-of-separated-stations-or-modules)), or the
instrument's own trigger (SPC; arXiv:hep-ex/0305074 sec. 2). Validate
with **time residuals** `t_meas - t_pred(p, m, L)` per species, using a
sample of known particle type (muons, identified pions, electrons at `beta = 1`).
Residual versus amplitude reveals walk; versus position along the bar reveals
propagation; versus run/fill reveals clock drift. MRPC walls: common clock offset, channel offsets and
slewing (COL; arXiv:1806.03825 sec. 3, p. 5); free-streaming: offsets and walk, then reference tracks
(FXT; arXiv:1807.02070 sec. 2.3, p. 5).

**Photostatistics versus charge.** At fixed velocity the deposit grows as `Z^2`, the light as T5, and the
pair resolution improves until the electronics floor `P2` dominates (a space counter in an ion beam, FXT;
arXiv:hep-ex/0305074 sec. 3, p. 4). Walk matters most at low `Z` (FXT ion-beam test of a space TOF;
arXiv:0810.3830 sec. 4, Table 2, pp. 8-9). The same photon-number mechanism makes a thinner scintillator time worse
(NUC heavy ions; arXiv:1609.09064 sec. 1, p. 2). Quote resolution per charge or amplitude class.

**Neutral particles.** Start from the beam (gamma flash, T6; NUC) or a coincident charged particle
([event-time estimators](event-time-and-timing-association.md#event-time-estimators)); the interaction depth in the bar enters `sigma_L/L` (T7).
Photon peaks (`beta = 1`) give per-bar offsets; neutrons are selected in time of flight per path length
(FXT; arXiv:2004.10339v1 pp. 12-13, secs. 3.2.1, 3.2.3).

## Methods (decision table)

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Precise single hits | LGAD, CFD or walk-corrected threshold (T1-T3) | thin sensor with gain; uniform fields | gain loss with fluence; Landau term not simulated | COL, FXT, SPC (proposed) |
| Large-area TOF at rate | MRPC, electrode chosen by local flux; ToT slewing | field on plateau; channel offsets | rate loss; asymmetric tail; multi-pad clusters | COL, FXT |
| Nuclei of many charges | per-`Z` resolution (T5); walk curve over the full amplitude range, e.g. `t_TDC - (p0 + p1/sqrt(A) + p2/A)` (arXiv:0810.3830 eq. 2, p. 8) or `T_raw - c_w/(Q_L Q_R)^(1/4)` for two ends (arXiv:1609.09064 eq. 4, p. 3) | independent charge | MIP walk curve applied to nuclei | SPC, FXT, NUC |
| Neutral-particle energy | TOF over `L` (T6, T7), beam or coincident start | known or effective `L`; photon peak | interaction depth; moderation spread | NUC, FXT |
| Simulated timing | the chain above | models validated on measured pulses | smeared true time; no data calibration | COL, FXT, NUC |

Event time and association: [companion](event-time-and-timing-association.md#methods).

### Distinctive but generalizable reconstruction and performance features (timing)

- **Topology**: time series per hit; one scalar per channel, sometimes with waveform.
- **Inverse problem**: `t` from a noisy pulse; degeneracy: absolute offset versus
  reference time versus path length.
- **Natural objects**: hit time, track time, event start time. **Informative
  residual**: time residual to the expected time for a known species vs amplitude,
  position, and run.
- **Scaling**: `TTS/sqrt(N_pe)` (photosensor spread), `tau_decay/N_pe` (first photon, negligible rise time),
  `sqrt(tau_rise tau_decay/N_pe)` (with rise time) and `noise/slope`; TOF separation `~ L/p^2` for `p >> m`.
- **Conventions**: quote resolution with the reference, core Gaussian sigma and tail
  fraction; state whether clock jitter is included.
- **Tails**: wrong-bunch (COL) or wrong-window, afterpulses, late light, mis-association.
- **Dependence**: rate (baseline shifts), dose (LGAD gain, SiPM dark counts), temperature,
  clock distribution. **Data sample**: `Z`/`J/psi -> mu mu` (COL); cosmic muons (ground and
  underground set-ups); ion-beam secondaries of known charge, for resolution versus charge
  (FXT; arXiv:hep-ex/0305074 sec. 3); identified species in overlapping momentum ranges. A sample for a counter in
  flight (SPC) is not given here (a gap).
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
  offsets first ([case studies](detector-case-studies-and-checklists.md)).
- **One resolution for all charges.** Photostatistics and walk change with `Z`; a light-ion value does not hold for
  heavy ions or protons.
- **A smeared true time as timing simulation.** It has no walk or tail, so core agreement says nothing about tails.

## Deliverables

- A time-resolution budget with each term's origin and whether it averages.
- Single-hit, per-track, event-time, and system resolutions, with tail fractions, per charge or amplitude class.
- Association rules and their failure rates ([companion](event-time-and-timing-association.md#deliverables)).
- Calibration chain (`t0`, walk, clock) and the residual used to validate it, on a sample or run range independent
  of the calibration sample (state both).
- For simulation: the steps simulated, their validation, and the calibration applied.

## Tool hooks

Existing: `frontend_response.py timing` (jitter, walk, CFD); `<plugin root>/adapters/timing-pid/` (time chain to
species likelihoods; demonstrated-on-synthetic-data, no quality claim).

**Time-resolution budget** (planned):

- Inputs: each term of the single-hit budget, T1 or T4 in ps, flagged per channel, per group (with its id: board,
  track) or common; hits per track `N` with their groups; tracks per event `N_tracks`; whether the reference comes
  from tracks.
- Outputs: single-hit, per-track, event-time and system resolutions in ps, each listing its terms.
- Conventions: Gaussian sigma; tail fractions reported apart, never folded in.
- Negative controls at `N >= 2` (at `N = 1` averaging everything passes): per-channel terms on distinct channels
  and groups give single-hit over `sqrt(N)`; a per-group term does not fall with `N` in one group and falls as
  `1/sqrt(k)` over `k` groups; a common term never falls; an event time from tracks falls as `1/sqrt(N_tracks)` in
  its per-track part only, the global clock staying in the system resolution.
- Statuses: `computed`; `incomplete` (a missing term or correlation flag, named; no default class); `failed` (a
  negative term, `N < 1` or `N_tracks < 1`).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Timing simulation chain | arxiv_1704.08666 | arxiv_1704.08666 (test beam) | gap | gap | gap | arxiv_2108.01384; arxiv_2505.00042 |
| LGAD detail | arxiv_1704.08666 | arxiv_1704.08666 | inspire_2613721 (proposal) | gap | gap | gap |
| MRPC detail | arxiv_1806.03825 | arxiv_1807.02070 | gap | gap | gap | gap |
| Photostatistics versus `Z` | gap | arxiv_0810.3830; arxiv_hep-ex_0305074 (space counters, ion beams) | gap (beam tests of space counters only) | gap | gap | arxiv_1609.09064 (mechanism only) |
| Neutral-particle TOF | gap | arxiv_2004.10339 | gap | gap | gap | arxiv_2505.00042 |

MRPC detail exists in COL and FXT only; LGAD timing in COL and FXT, with a space proposal. Event time and
association: [companion](event-time-and-timing-association.md#environment-coverage).

## Worked examples

<!-- example: UFSD/LGAD and the Weightfield2 simulator -->
LGAD-based UFSD: gain 10-20 (arXiv:1704.08666 sec. 2.3.2, p. 10); about 50 um with gain about 20 optimal
(sec. 2.3.4, p. 12); gain 20 doubles the slew rate at 300 um, more
than six times at 50 um (sec. 4.5, p. 27).
<!-- /example -->

<!-- example: ALICE TOF (LHC) and CBM TOF (FAIR SIS100) -->
ALICE TOF: MRPCs with two stacks of five 250 um gaps (arXiv:1806.03825 sec. 1, p. 2); `sigma_TDC` about 20 ps, `sigma_FEE` about 10 ps, `sigma_clock` about 15 ps; 56 ps after the 2017
channel-by-channel slewing calibration (84 ps before) (sec. 3, pp. 5-6); MRPC performance decreases above
1 kHz/cm^2 (sec. 2.1, p. 4). CBM TOF: a design system resolution better than 80 ps, for fluxes of
0.1-100 kHz/cm^2 depending on position; ceramic MRPCs in the start-time region up to 100 kHz/cm^2, low-resistivity
glass between 30 and 1 kHz/cm^2, float glass below (arXiv:1807.02070 abstract, sec. 2, pp. 1-3); a 140 um-gap prototype pair at 67 ps,
about 47 ps per counter if equal (sec. 2.1, p. 4); strip prototypes (50 ± 1) ps in a cosmic stack (p. 6).
<!-- /example -->

<!-- example: AMS-02 TOF and PAMELA TOF (ion-beam tests), ETF plastic TOF (IMP Lanzhou) -->
AMS-02 TOF, SPS ion beam 2002 (Z = 1-82 secondaries): `P1` = 0.0606 ns, `P2` = 0.0572 ns in `sigma_t = P1/Z + P2`;
pair floor 57 ± 1 ps with standard electronics, about 40 ps per counter if equal (arXiv:hep-ex/0305074 sec. 3,
Fig. 4, p. 4). PAMELA TOF, GSI 2006,
paddle S3: 146.5 ps before and 117.3 ps after walk correction for Z = 1, 118 and 114 ps for Z = 3, 50 ps and 46.5 ps
unchanged for Z = 5 and 6 (arXiv:0810.3830 Table 2, p. 9). ETF counters (3 mm, 18O at 400 MeV/nucleon): 27 ps and 36 ps
after walk and position corrections (arXiv:1609.09064 abstract, p. 1).
<!-- /example -->

<!-- example: CLAS12 BAND (JLab Hall B) and n_TOF EAR2 (CERN) -->
BAND: photon peak sigma = 294 ps after per-bar offsets (arXiv:2004.10339v1 p. 12, sec. 3.2.1); neutron
`delta p/p < 1.5%` for 200-600 MeV/c (abstract, p. 1). n_TOF EAR2: about 20 m vertical flight path (sec. 2);
the FLUKA resolution function was validated with 197Au and 56Fe (n, gamma) resonances (arXiv:2505.00042 sec. 6).
<!-- /example -->

## Citations

Source IDs: `arxiv_<id>`, `inspire_<recid>`; pages are PDF page indices of the version named; all read 2026-11-21.

- S. Navas et al. (Particle Data Group), "Particle detectors at accelerators" (eq. 35.25), in Review of Particle
  Physics, Phys. Rev. D 110 (2024) 030001 and 2025 update, DOI 10.1103/PhysRevD.110.030001.
- H. F.-W. Sadrozinski, A. Seiden and N. Cartiglia, "4D tracking with ultra-fast silicon detectors", Rep. Prog. Phys. 81
  (2018) 026101, arXiv:1704.08666v4.

<!-- example: apparatus sources -->
- F. Carnesecchi (ALICE Collaboration), "Performance of the ALICE Time-Of-Flight detector at the LHC", JINST 14 (2019)
  C06023, arXiv:1806.03825v1.
- I. Deppner and N. Herrmann (CBM Collaboration), "The CBM Time-of-Flight system", JINST 14 (2019) C09020,
  arXiv:1807.02070v1.
- M. Duranti et al., "Opportunities of Si-microstrip LGAD for next-generation space detectors", J. Phys. Conf. Ser.
  2374 (2022) 012046, DOI 10.1088/1742-6596/2374/1/012046, inspire_2613721.
- V. Bindi et al. (AMS TOF Collaboration), "The AMS-02 Time of Flight System. Final Design", Proc. 28th ICRC (2003),
  arXiv:hep-ex/0305074v1.
- D. Campana et al., "Capability of the PAMELA Time-Of-Flight to identify light nuclei: results from a beam test",
  Nucl. Instrum. Methods A 598 (2009) 696, arXiv:0810.3830v1.
- W.-J. Lin et al., "Plastic scintillation detectors for precision time-of-flight measurements of relativistic heavy
  ions", Chin. Phys. C 41 (2017) 066001, arXiv:1609.09064v1.
- E. P. Segarra et al., "The CLAS12 Backward Angle Neutron Detector (BAND)", Nucl. Instrum. Methods A 978 (2020)
  164356, arXiv:2004.10339v1.
- J. A. Pavon-Rodriguez et al., "Characterisation of the neutron beam in the n_TOF-EAR2 experimental area at CERN
  following the spallation target upgrade", Eur. Phys. J. A (2025), arXiv:2505.00042v2.
- J. Mayer et al., "Classical and Machine Learning Methods for Event Reconstruction in NeuLAND", Nucl. Instrum.
  Methods A 1013 (2021) 165666, arXiv:2108.01384v1.
<!-- /example -->
