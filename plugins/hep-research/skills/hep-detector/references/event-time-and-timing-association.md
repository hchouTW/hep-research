# Event Time and Timing Association

How the reference (start) time of an event is estimated, and how time assigns hits to tracks, events, beam bunches
and directions: event-time estimators and their bias with and without a bunch clock, bunch or beam-bucket
assignment, track-to-hit and hit-to-event association, up- versus down-going particles, and the synchronisation of
separated stations or modules. Not repeated here, and found in [timing detectors](timing-detectors.md) (its sections extended with this page): the
single-hit [budget](timing-detectors.md#time-resolution-budget-single-hit), the technologies and the [timing
simulation chain](timing-detectors.md#timing-simulation-chain) (five steps, deposit to validation); the event-level timing window in [event
reconstruction](event-reconstruction.md#timing-and-event-association) and pileup in [its pileup
section](event-reconstruction.md#reconstruction-under-pileup); TOF PID in [particle
identification](particle-identification.md#time-of-flight-tof); air-shower geometry in [ground-based detection
arrays](ground-based-detection-arrays.md#surface-array-event-reconstruction); optical-module arrays in [neutrino
astronomy](neutrino-astronomy.md); core-plus-tail shapes of a time residual in [resolution shape
models](resolution-shape-models.md); matching rates from truth in [truth
matching](reconstruction-performance-and-truth-matching.md).

Environment codes: COL collider; FXT fixed target and test beam; SPC space and balloon; UGD underground, neutrino and
rare-event; GND ground-based arrays; NUC nuclear and low-energy. A bunch or pulse clock exists only where a beam is bunched or pulsed: COL,
bunched FXT, accelerator-neutrino UGD (spills) and pulsed NUC sources, the same four environments as bucket
assignment below; SPC, GND and non-beam UGD instruments have none.

## Relations

| # | Relation | Status and validity | Source |
|---|---|---|---|
| E1 | `t_ev(m) = sum_i W_i (t_i - t_exp,i(m_i)) / sum_i W_i`, `W_i = 1/(sigma_t^2 + sigma_exp,i^2)`, `sigma_ev = (sum_i W_i)^(-1/2)` | exact for independent Gaussian times at fixed mass hypotheses `m_i`; `∝ 1/sqrt(n)` for equal weights | arXiv:1610.03055 sec. 4.1, eqs. 4-6, pp. 6-7 |
| E2 | hypotheses from the minimum of `chi2(m) = sum_i W_i ((t_i - t_ev(m)) - t_exp,i)^2` over all combinations (`3^n` for three species) | exact as a definition; the combinatorics force subsamples | same, eq. 7, pp. 6-7 |
| E3 | `n` equal-variance hits: `Var(t_k - t_ev) = sigma^2 (n - 1)/n` with hit `k` inside `t_ev`, `sigma^2 n/(n - 1)` with it left out | exact for independent Gaussian times (derived here from E1) | E1 |
| E4 | independent estimators combined with inverse-variance weights; with none, the nominal crossing with `sigma = sigma_vertex/c` | exact for independent Gaussians; the fallback approximate (bunch length as spread) | arXiv:1610.03055 secs. 4, 4.3, pp. 5-7 |
| E5 | `t_0 = (t_A + t_C)/2` from counters on both sides of the source, independent of the vertex position along the axis; one side needs the vertex `z` | exact for speed-of-light particles along the axis | same, sec. 4.2, p. 7 |
| E6 | `c (t_i - t_0) = |x_sh - x_i|`, `t_0` and the virtual origin `x_sh` fitted; a plane front first | approximate (a speed-of-light sphere) | arXiv:1502.01323 sec. 11.2, eq. 9, p. 61 |
| E7 | `Delta t = t_lower - t_upper` between the instrument's own planes; `beta = L / (c Delta t)` carries the sign of the direction | definition (`L` along the fitted track) | arXiv:hep-ex/0305074 sec. 2, p. 3 |
| E8 | hits of one event clustered if `|Delta x|, |Delta y|, |Delta z| <= k d_bar` and `|Delta t| <= Delta t_max`, applied transitively | definition (clustering within an event); `k`, `Delta t_max` a trade between correlated and uncorrelated hits | arXiv:2108.01384 sec. 3.3, eq. 2 |

## Event-time estimators

- **Bunch clock at a collider (COL)**: the clock gives the nominal crossing only; finite bunches leave the collision time a
  spread, so it is measured per event (arXiv:1610.03055 sec. 4, p. 5): by a start counter (E5), by the timing
  detector's own tracks (E1-E2), or by both (E4), with the crossing as fallback.
- **Self-use bias**: a track used in `t_ev` pulls `t_ev` towards its own hypothesis, so its residual is too narrow
  (E3) and its identification biased, worst at low multiplicity. Remedy: compute `t_ev` without that track, or, for
  speed, without its group (momentum bins) (arXiv:1610.03055 sec. 4.1, pp. 6-7). The source states a minimum
  of two tracks (sec. 5.1, p. 8, from sec. 4.1); with one track outside the tested track's group the `chi2` of E2 is
  zero for every hypothesis, so this page asks for two or more outside it (Methods).
- **Common offset**: an internal `t_ev` moves with a common offset of all channels, so the TOF cannot see it (follows
  from E1); only an external reference constrains it: an external start, or a species of known `beta` timed against the bunch
  clock (pions against the clock phase per fill: arXiv:1610.03055 sec. 3, pp. 4-5).
- **Starts other than the bunch clock** (on bunched FXT and pulsed NUC beams the coincident particle or the gamma
  flash gives the per-bunch or per-pulse time): a dedicated start counter in a free-streaming fixed-target set-up (FXT;
  arXiv:1807.02070 sec. 2, p. 2); the instrument's own planes (E7), so both planes' terms enter (SPC;
  arXiv:0810.3830 sec. 4, p. 9); `t_0` fitted with the geometry (E6), correlated with it (GND); a vertex time fitted
  with the track (UGD; [photon likelihood reconstruction](photon-likelihood-reconstruction.md)); the gamma flash of a pulsed source, corrected for its own flight time
  `L0/c` (NUC; start and time to energy in arXiv:2505.00042v2 sec. 4.1, eqs. 6-7, also T6 of [timing
  detectors](timing-detectors.md#relations-definition-exact-unless-noted)); for a neutral particle on a bunched
  beam, a coincident charged particle traced back to the target (FXT; arXiv:2004.10339v1 secs. 3.2.1, 3.2.3).

## Bunch or beam-bucket assignment (bunched or pulsed beams)

Applies in the four environments with a bunch or pulse clock: COL, bunched FXT, accelerator-neutrino UGD spills and
pulsed NUC sources. No source here states the assignment rule (FXT gives only the out-of-time structure and the
bunch spread), so all four are gaps in the coverage table, not exclusions. The hit or event goes to the bucket nearest its time corrected for
the expected flight time; this needs
a bunch spacing much larger than the total time resolution plus the flight-time spread of the species considered.
At a collider the clock gives the nominal crossing only (arXiv:1610.03055 sec. 4, p. 5); no source here assigns an event
to a crossing (a COL gap). Out-of-time particles from other bunches appear as a periodic structure at
the bunch spacing in the time spectrum (FXT; structure only, arXiv:2004.10339v1 sec. 3.2.1); the bunch's own time spread enters the
budget (sec. 3.2.2). Beam-phase drift and asymmetric bunch shapes are systematic inputs.
Quote the in-time core and the out-of-time fraction separately. Without bunches (SPC, GND, non-beam UGD) there is
nothing to assign; the ambiguities are direction and synchronisation (below).

## Track-to-hit and hit-to-event association

- **Track to hit**: extrapolate the track, open a window around the point, take the closest signal (COL;
  arXiv:1806.03825 sec. 3, footnote 1, p. 5). Matching efficiency folds intrinsic efficiency, algorithm, acceptance,
  material in front and extrapolation accuracy (sec. 2.2, p. 4). A hit on the wrong track gives unphysical `beta`
  (Fig. 5, p. 7), a tail that is not the resolution.
- **Reference tracks**: in a self-triggered stack, tracks from the other counters, interpolated to the counter
  under test, define efficiency (a hit close in space and time) and residuals (FXT; arXiv:1807.02070 sec. 2.3, p. 5).
- **Hit to event**: event building from coincidences of several detectors (same, p. 5), or from all hits in a short
  time window, meant to hold one nuclear reaction (NUC; event building, arXiv:2108.01384v1 sec. 3.1, data flow); rejecting hits isolated in time and space as noise or afterpulses (UGD;
  arXiv:astro-ph/0407044 sec. 5.3, p. 22); removing stations incompatible in time with the fitted front, with cuts
  set to keep a stated fraction of signal stations (GND; arXiv:1502.01323 sec. 11.1, p. 60).
- **Hits to clusters within an event**: space-time clustering (E8, NUC; arXiv:2108.01384 eq. 2 in sec. 3.3,
  applied there to simulated hits).
- **Delayed hits**: backscattered particles from a calorimeter reach a tracker above it later than the primary,
  so hit times separate them (SPC, simulation of a proposed instrument; inspire_2613721 sec. 2, p. 2).

Measure the mismatch rate in simulation against truth and in data from the tails of the residual or `beta`.

## Up-going versus down-going

- **SPC**: the sign of the flight time between planes above and below the spectrometer gives the direction, which
  is needed to separate particles from antiparticles (arXiv:hep-ex/0305074 sec. 2, p. 3), since a reversed
  direction reverses the charge sign inferred from the curvature. It also rejects albedo particles (arXiv:0810.3830 sec. 1, p. 2).
- **UGD**: the direction comes from the hit-time pattern. Down-going atmospheric muons outnumber neutrino-induced
  muons by orders of magnitude near the vertical but vanish for up-going tracks, so a small mis-reconstructed fraction
  dominates an up-going sample; a zenith-dependent prior enters the reconstruction (arXiv:astro-ph/0407044
  sec. 3.1.4, p. 11). Mis-reconstructed down-going classes (the eight of sec. 6.1, pp. 23-24): nearly horizontal muons, muon
  bundles, cascades, stopping muons, scattering layers, corner clippers, uncorrelated coincident muons from two air
  showers in one event (a hit-to-event failure), and electronic artifacts (noise, cross talk) distorting the time pattern.
- Not a timing question at COL and FXT (particles leave the vertex) or in GND arrays (showers arrive from above).

## Synchronisation of separated stations or modules

- **GND**: each station time-stamps against GPS seconds with the receiver's corrections, which also calibrate the
  local clocks (arXiv:1502.01323v5 sec. 3.3, PDF p. 18 of v5, the version cached and read); a modelled single-station time variance propagates to the
  arrival-direction resolution (sec. 11.4, p. 63).
- **UGD**: a shore clock is distributed; the round-trip time to each module gives its delay (arXiv:1012.2204
  sec. 3, p. 8); LED and laser beacons re-measure the offsets within and between lines in situ (sec. 4.2, p. 12). The
  relative offsets set the pointing; absolute time to UTC is far less demanding (secs. 1, 3, pp. 4, 8).
- **COL, FXT** (no separated stations): one distributed clock, whose offsets are still calibrated in situ: a common
  offset to the collision time and per-channel cable-delay offsets (COL; arXiv:1806.03825 sec. 3, p. 5), or time and
  position offsets before track finding in a free-streaming stack (FXT; arXiv:1807.02070 sec. 2.3, p. 5).
- A station offset is common to all hits of that station, so it does not average over them
  ([budget](timing-detectors.md#time-resolution-budget-single-hit)).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Bunch clock, no per-event time | nominal crossing (E4 fallback) | known luminous-region length | taken as the event time; dominates low multiplicity | COL |
| Start counter | E5, or one side with the vertex | counters on both sides or a vertex | acceptance; amplitude-dependent resolution | COL, FXT |
| Many timed tracks | E1-E2 with the track left out (E3) | two or more tracks outside the tested track's leave-out group (momentum bin), in any groups, and two or more in every combinatorial subsample (E2): with one, the `chi2` of E2 is zero for every hypothesis; momentum and path | self-use bias; combinatorics; with one outside, no `t_ev` for PID: fall back to E4 and record it | COL |
| Self-timed instrument | E7 | two or more planes; track length | both planes' terms; direction error | SPC |
| No start at all | `t_0` fitted with geometry (E6, GND); vertex time fitted with the track by the photon likelihood (UGD) | more stations than fitted parameters (plane front 3, E6 sphere 4); UGD: more hit modules than track and vertex parameters | `t_0`-geometry correlation | GND, UGD |
| Pulsed source | gamma-flash start and time to energy (arXiv:2505.00042v2 sec. 4.1, eqs. 6-7; T6 of [timing detectors](timing-detectors.md#relations-definition-exact-unless-noted)) | prompt photons seen | the flash's own flight time `L0/c` omitted | NUC |
| Bunched or pulsed beam | nearest bucket after flight-time correction | spacing much larger than the total time resolution plus the flight-time spread of the species | out-of-time bunches; aliased buckets | COL, FXT, NUC, UGD (rule unsourced: gaps) |
| Track-to-hit | window and closest hit | extrapolation errors known | mismatches; multi-hit cells | COL, FXT |
| Hit-to-event | coincidence or time window, isolation cuts, front compatibility; E8 within an event; delayed-hit times (SPC) | noise rate low; cuts set to a stated signal-retention fraction, loss rate reported | signal hits removed; noise kept | NUC, FXT, UGD, GND, SPC (simulation) |
| Direction | sign of E7; hit-time pattern | timing over the track length | flipped charge; mis-reconstructed background | SPC, UGD |
| Separated stations | GPS, distributed clock with round trip, flashers | offsets monitored over time | offsets drift with temperature | GND, UGD; module offsets also COL, FXT |

## Distinctive but generalizable features (event time and association)

- **Topology**: hit times on tracks or stations; one event time per event, often per hypothesis.
- **Inverse problem**: event time and mass hypotheses together (E1-E2); `t_0` with geometry (E6).
- **Natural objects**: event time with its source and estimator; hit-track and hit-event links; bucket; direction.
- **Informative residual**: `t - t_ev - t_exp` per track with the track left out; station residuals to the front.
- **Scaling**: `sigma_ev ∝ 1/sqrt(n)` for internal estimators; a fixed floor from a common clock.
- **Conventions**: name the start-time source and whether the track under test was excluded.
- **Tails**: mismatches, out-of-time bunches, noise hits, reversed directions.
- **Dependence**: multiplicity, collision system, rate, temperature of clock links.
- **Data sample**: high-multiplicity events (internal estimator), cosmic muons through a stack, flasher or beacon runs.
- **Transfers**: leave-out estimators and space-time windows to any timed system; **does not transfer**: a bunch
  clock to unbunched or non-accelerator environments.

## Common misconceptions and failure modes

- **A track in its own event time.** Pulls too narrow, PID biased at low multiplicity (E3).
- **A common offset calibrated against an internal event time.** It is invisible there; use an external reference.
- **The bunch clock taken as the event time.** It is the crossing, not the collision.
- **Out-of-time bunches fitted as a Gaussian tail.** They are periodic at the bunch spacing.
- **Direction error rates from simulation alone** where the background exceeds the signal by orders of magnitude.
- **Absolute time confused with relative synchronisation.** Track reconstruction needs only the relative offsets,
  which set the direction in the detector frame; celestial coordinates also need absolute time, to seconds (arXiv:1012.2204 sec. 3, p. 8).

## Deliverables

- The start-time source, estimator, its resolution versus multiplicity, and whether the tested track was excluded.
- The bucket rule and out-of-time fraction (bunched beams).
- The association rules (windows, adjacency, isolation, front compatibility) with mismatch and loss rates.
- The direction rule with its misidentification probability, measured or bounded.
- The station or module offsets, their monitoring and their contribution to the direction resolution.

## Tool hooks

Existing: `<plugin root>/adapters/timing-pid/` computes external, common linear, per-track leave-one-out and median
event times and refuses a TOF whose leave-one-out start includes its own hit (status
demonstrated-on-synthetic-data; synthetic constants only, no timing or PID quality claim).

**Association and mismatch rate** (planned):

- Inputs: per event, tracks with extrapolated position, time and their errors; hits with position, time and channel;
  window sizes; optional truth links.
- Outputs: hit-track links, unmatched hits and tracks, mismatch rate against truth and its binomial interval (without
  truth, a data-driven estimate or bound from the residual tails, flagged), the tail fraction of the residual.
- Conventions: ns and cm; the window in units of the extrapolation error, stated.
- Negative control: hits shuffled between events must give a mismatch rate whose 95% binomial interval contains
  the chance rate predicted from hit density and window size; a positive control with planted wrong links must recover them.
- Statuses: `computed`; `no-truth` (no truth links: the mismatch rate is still reported, as a data-driven estimate or
  upper bound from the residual or `beta` tails, flagged as such); `failed` (an input error: window size missing, zero or negative, or no extrapolation errors; never a result; an empty window gives an
  unmatched track).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Event-time estimator and bias | arxiv_1610.03055; arxiv_1806.03825 | arxiv_1807.02070; arxiv_2004.10339 (neutral start) | arxiv_hep-ex_0305074; arxiv_0810.3830 | [photon likelihood reconstruction](photon-likelihood-reconstruction.md) | arxiv_1502.01323 | arxiv_2505.00042 (gamma flash, sec. 4.1, eq. 6) |
| Bunch or bucket assignment | gap (applies; arxiv_1610.03055 gives the nominal crossing only, not crossing assignment) | gap (applies; arxiv_2004.10339 gives bunch structure and spread, not assignment) | n/a (no beam) | gap (applies to accelerator-neutrino spills; not sourced) | n/a (no beam) | gap (applies to pulsed sources; not sourced) |
| Track-to-hit, hit-to-event | arxiv_1806.03825 | arxiv_1807.02070 | inspire_2613721 (simulation) | arxiv_astro-ph_0407044 | arxiv_1502.01323 | arxiv_2108.01384 |
| Up- versus down-going | n/a (outgoing from the vertex) | n/a (outgoing from the target) | arxiv_hep-ex_0305074; arxiv_0810.3830 | arxiv_astro-ph_0407044 | n/a (showers from above; [arrays](ground-based-detection-arrays.md)) | n/a |
| Synchronisation of separated stations or modules | arxiv_1806.03825 (offsets of one distributed clock; no separated stations) | arxiv_1807.02070 (time offsets calibrated before tracking; no separated stations) | n/a | arxiv_1012.2204 | arxiv_1502.01323 | n/a |

Every technique but bunch assignment has two or more sourced environments; bunch assignment applies in four (COL,
FXT, UGD, NUC), and its rule is sourced in none (FXT gives only the out-of-time structure and bunch spread), so all
four cells are gaps.

## Worked examples

<!-- example: ALICE event time and TOF matching (LHC) -->
Without a per-event estimator the fallback resolution is about 200 ps (arXiv:1610.03055 sec. 4, p. 6); tracks are
split into ten momentum bins for the leave-out (sec. 4.1, pp. 6-7); T0 gives about 25 ps (Pb-Pb) and 50 ps (pp) with
both sides (sec. 4.2, p. 7) and about 70% efficiency in very low multiplicity pp (sec. 5.1, p. 8). `sigma_event` is
about 80-200 ps from the bunch size; the TOF estimator is below 10 ps above 100 tracks; the matching window is 3 cm
(Pb-Pb) or 10 cm (pp) (arXiv:1806.03825 secs. 3, 3.2, pp. 5-6).
<!-- /example -->

<!-- example: CBM TOF (FAIR SIS100), NeuLAND (R3B, FAIR), CLAS12 BAND (JLab), n_TOF EAR2 (CERN), LGAD strips in space (proposal) -->
CBM: a start counter for fluxes up to 100 kHz/cm^2 (arXiv:1807.02070 sec. 2, p. 2); in a six-station cosmic stack,
events need four or more signals and five counters define the reference track (sec. 2.3, p. 5). NeuLAND: `k` = 1.5,
`d_bar` = 5 cm, `Delta t_max` = 1 ns (arXiv:2108.01384 sec. 3.3, eq. 2). BAND: 4 ns spikes from other beam bunches;
bunch spread about 25 ps (arXiv:2004.10339v1 secs. 3.2.1-3.2.2); photon-peak sigma of 294 ps after per-bar offsets
(sec. 3.2.1); neutron `delta p/p < 1.5%` for 200-600 MeV/c (abstract). LGAD proposal: thin LGADs reach 30-40 ps; pixels over
O(10 m^2) in space would need O(nW)/channel, strips O(0.1 mW)/channel; target O(100 ps) per hit (inspire_2613721
secs. 1-2, p. 2); 10 strip layers with 100 ps above a BGO calorimeter (sec. 2, pp. 2-3). n_TOF EAR2: about 20 m
vertical flight path (arXiv:2505.00042v2 sec. 2); the FLUKA resolution function was validated with 197Au and 56Fe
(n, gamma) resonances (sec. 6).
<!-- /example -->

<!-- example: Pierre Auger surface detector, ANTARES, AMANDA -->
Auger: GPS 1 PPS offset up to 50 ns, corrected; data synchronised to GPS within 10 ns RMS (arXiv:1502.01323v5 sec. 3.3,
p. 18); time cuts keep 99% of signal stations (sec. 11.1, p. 60); angular resolution better than 1.6 deg with more
than three stations, 0.9 deg with more than six (sec. 11.4, p. 63). ANTARES: about 2 ns per photon from 1.3 ns TTS and
1.5 ns chromatic dispersion; relative offsets needed below 1 ns (arXiv:1012.2204 sec. 1, p. 4); GPS to UTC about
100 ns; round trips hourly; LCM-to-SCM stability about 16 ps (sec. 3, p. 8). AMANDA: a hit is noise without another
within 60-100 m and 300-600 ns (arXiv:astro-ph/0407044 sec. 5.3, p. 22); about 5 orders of magnitude of down-going
excess at the vertical (sec. 3.1.4, p. 11); mis-reconstructed fraction about 1e-2 (unbiased) and 1e-4 (zenith
weighted) (sec. 6.1, p. 23).
<!-- /example -->

<!-- example: AMS-02 TOF and PAMELA TOF -->
AMS-02 TOF: four scintillator planes, two above and two below the magnet, measure `beta` and the direction
(arXiv:hep-ex/0305074 secs. 2-3, pp. 1-3). PAMELA TOF: flight time from the difference of paddle mean times, no
external start (arXiv:0810.3830 sec. 4, pp. 7, 9).
<!-- /example -->

## Citations

Source IDs: `arxiv_<id>`, `inspire_<recid>`; pages are PDF page indices of the version named; all read 2026-11-21.

<!-- example: apparatus sources -->
- ALICE Collaboration, "Determination of the event collision time with the ALICE detector at the LHC", Eur. Phys. J.
  Plus 132 (2017) 99, arXiv:1610.03055v2.
- F. Carnesecchi (ALICE Collaboration), "Performance of the ALICE Time-Of-Flight detector at the LHC", JINST 14 (2019)
  C06023, arXiv:1806.03825v1.
- I. Deppner and N. Herrmann (CBM Collaboration), "The CBM Time-of-Flight system", JINST 14 (2019) C09020,
  arXiv:1807.02070v1.
- Pierre Auger Collaboration, "The Pierre Auger Cosmic Ray Observatory", Nucl. Instrum. Methods A 798 (2015) 172,
  arXiv:1502.01323v5.
- ANTARES Collaboration, "Time Calibration of the ANTARES Neutrino Telescope", Astropart. Phys. 34 (2011) 539,
  arXiv:1012.2204v1.
- J. Ahrens et al. (AMANDA Collaboration), "Muon track reconstruction and data selection techniques in AMANDA", Nucl.
  Instrum. Methods A 524 (2004) 169, arXiv:astro-ph/0407044v1.
- V. Bindi et al. (AMS TOF Collaboration), "The AMS-02 Time of Flight System. Final Design", Proc. 28th ICRC (2003),
  arXiv:hep-ex/0305074v1.
- D. Campana et al., "Capability of the PAMELA Time-Of-Flight to identify light nuclei: results from a beam test calibration"
  (title as on INSPIRE and arXiv), Nucl. Instrum. Methods A 598 (2009) 696, arXiv:0810.3830v1.
- E. P. Segarra et al., "The CLAS12 Backward Angle Neutron Detector (BAND)", Nucl. Instrum. Methods A 978 (2020)
  164356, arXiv:2004.10339v1.
- J. Mayer et al., "Classical and Machine Learning Methods for Event Reconstruction in NeuLAND", Nucl. Instrum.
  Methods A 1013 (2021) 165666, arXiv:2108.01384v1.
- M. Duranti et al., "Opportunities of Si-microstrip LGAD for next-generation space detectors", J. Phys. Conf. Ser.
  2374 (2022) 012046, DOI 10.1088/1742-6596/2374/1/012046, inspire_2613721 (journal version read).
- J. A. Pavon-Rodriguez et al., "Characterisation of the neutron beam in the n_TOF-EAR2 experimental area at CERN
  following the spallation target upgrade", Eur. Phys. J. A 61 (2025) 277, DOI
  10.1140/epja/s10050-025-01727-x, arXiv:2505.00042v2.
<!-- /example -->
