# T11: design cells (all 38 families)

State: in progress, not done. Parts 1 and 2 cover the 27 families with plugin text, from the plugin tree and the plan only. Part 3 covers F21, F24, F26-F28 and F33-F38 from papers actually read (t11-sources.md); those cells apply to the named experiment, not a whole family, unless they say otherwise. Nothing was run, and nothing comes from memory.

Parts 1 and 2: 189 cells, 167 documented, 21 `gap-method`, 1 not-applicable (F14 space/time, a readout reason). Every anchor was resolved against the baseline headings. Cells marked `source-unverified` name a source the plugin cites that nobody has re-read here, so T11 cannot be done while they remain (R14). Documented means text exists, not that anything runs: most bindings are `none`.

# Part 1: families the inventory first marked documented

Read-only design record. Nothing was run. Baseline tree commit `580dc79e`, plugin 0.56.0. Plan v9.2 sections 5.5, 5.15, 6, 6.6, 7.1.1, BP01-BP08, BP11, BP15.

Conventions:

- Paths are relative to `plugins/hep-research/`. A bare `name.md#anchor` is under `skills/hep-detector/references/`. All anchors were resolved against the headings of the baseline tree.
- Status: `documented`, `gap-method`, `not-applicable`. `gap-backend` is unused by instruction; a documented method with nothing implementing it is `documented` with binding `none`.
- Generic text (front-end, track fit) counts for a family only where it applies by its own scope and the family text adds that family's failure modes. Otherwise the cell is `gap-method`.
- Binding: `none`, or a real path. `adjacent:` names something that computes a related number but takes no detector observations, or does not do this task; it is not a binding. `E` means the family's environment line. All family and axis cases are design cases: none has been run unless the evidence column says so.
- `source-unverified`: the plugin cites that source, and nobody has re-read the original here.
- ACTS 48.2.0: planned for planar silicon fixtures in T07, not run for any family and absent from the tree (no `ACTS` in `skills/hep-detector`, `adapters/geant4/adapter.json` or `tests/adapters`).
- simreco = `adapters/geant4/assets/simreco/simreco.cc` with `Fit.hh`, through `adapters/geant4/assets/geant4_run.py reco`. It reads element_sim events only.
- Predicates: `&&`, `||`. Each term is a fact to establish per product scope (5.5). A term not established stays unknown; a name or description alone does not establish it (5.5).

## F01 Silicon pixel/strip, MAPS, CCD, DEPFET, radiation-tolerant tracking

E: collider/fixed-target and space; event readout, low to high occupancy.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | documented | `front-end-electronics-and-signal-processing.md#noise`, `signal-formation-and-readout.md#readout-and-digitization`, `front-end-calibration.md` | pedestal runs; common mode excluding hit channels (iterative or median) | channel charge [e or fC]; ToT or binary as such | residual common mode flat versus occupancy | heavily ionizing track absorbed into the estimate: negative neighbours, lost clusters | `none`; adjacent: `frontend_response.py` `cluster-noise`, `hit-efficiency`, `s-curve`; `adapters/detector-simulation` `allpix.pixel-charge` (simulation); E | none; adjacent: VALIDATION DETSIM-W4A, DETSIM-W5 (pipeline only) |
| Finding/association | documented | `gaseous-and-specialized-tracking-technologies.md#silicon-pixels-and-strips-recap-of-what-is-distinctive`, `tracking-and-vertexing.md#track-finding-strategies`; source-unverified: Ai et al., Comput. Softw. Big Sci. 6 (2022) 8 | clusters; stereo pairing keeps ghosts; seeds, CKF or road following, shared-hit ambiguity | cluster, source link, track candidate [dimensionless relations] | two tracks through a stereo pair: 4 intersections, 2 real, both retained until track level | merged clusters; seed-layer miss loses the track | simreco, plane-by-plane association on simulated crossings, not a data-side finder; ACTS 48.2.0 planned T07, not run; E | `tests/adapters/test_simreco.py`; VALIDATION GEANT4-F4, GEANT4-J15 (SYNTHETIC); stereo-ghost case: none |
| Parameter estimation | documented | `tracking-and-vertexing.md#the-track-fit`; source-unverified: Kleinwort, Nucl. Instrum. Methods A 673 (2012) 107; Adam et al., J. Phys. G 31 (2005) N9 | centroid or charge template; Kalman, broken-lines, annealing, Gaussian-sum fit | local coordinate [length]; track state with covariance | pulls of width 1 at fixed material | wrong hit absorbed with an unremarkable chi-square | simreco `Fit.hh` (Gauss-Newton arc chain, field along z); ACTS planned T07, not run; E | `tests/adapters/test_simreco.py`; VALIDATION GEANT4-F4 (SYNTHETIC) |
| Space/time/direction | documented | `tracking-and-vertexing.md#vertexing`, `tracking-and-vertexing.md#sensor-technologies`; source-unverified: Waltenberger, Frühwirth and Vanlaer, J. Phys. G 34 (2007) N343; PDG RPP 2025 sec. 35.8 | Lorentz-angle correction; vertex finding then adaptive fit; impact parameter | position [length], impact parameter [length], vertex; time only where the sensor stamps it | nearby vertices separated with timing | prompt fit used on a material-interaction vertex; hit time assumed from an integrating sensor | hits: simreco, no Lorentz model; vertex: `none`; E | hits: VALIDATION GEANT4-J15 (SYNTHETIC); vertex: none |
| Energy/momentum | documented | `tracking-and-vertexing.md#propagation-in-a-non-uniform-field`, `tracking-and-vertexing.md#rigidity-resolution-and-its-two-regimes`; source-unverified: PDG RPP 2025 sec. 35.12 | q/p from fit with field and material; mass hypothesis in energy loss | signed rigidity [GV] or p [GeV/c] at a reference surface | resolution against bending power along the path | field-map scale error read as rigidity shift; pion-fit track used as proton | simreco (field along z); adjacent: `tracker_resolution.py`, `multiple_scattering.py` (design); E | VALIDATION GEANT4-J15 (SYNTHETIC, invented geometry) |
| PID/topology | documented | `tracking-and-vertexing.md#sensor-technologies`, `particle-identification.md#ionization-energy-loss-dedx`, `particle-identification.md#combining-many-samples` | multi-layer charge, truncated mean; \|Z\| consistency; kink/secondary vertex topology | \|Z\| [e units]; dE/dx [charge per path] | saturating response inverted through the curve | dE/dx used for species at high momentum in silicon | `skills/hep-detector/scripts/multisample_pid.py` (samples as CSV); E | `tests/skills/hep_detector/test_multisample_pid.py`; VALIDATION UPGRADE-B (SYNTHETIC) |
| Uncertainty/quality | documented | `tracking-and-vertexing.md#the-track-fit`, `tracking-and-vertexing.md#alignment-coupling`, `tracking-and-vertexing.md#charge-confusion` | unbiased residuals, pulls, hit pattern, full covariance, weak-mode check | residual [length], covariance, efficiency/fake/duplicate rates | unbiased residual versus angle and cluster size | smoothed residual used as unbiased; weak mode leaves chi-square unchanged | `none`; adjacent: simreco fit errors; `charge_confusion_rate.py`; E | none for quality; adjacent: VALIDATION GEANT4-J15 (charge confusion refused, no tail reference) |

Variant and condition gaps:

- CCD: one shared paragraph and a Table 1 row. No method text for pedestal per variant, charge transfer or readout phase.
- DEPFET: same shared paragraph and row. No variant method.
- MAPS: diffusion sharing stated, otherwise the same paragraph.
- Rolling/integrating readout: "integration-time ambiguity, hit-time association" is named, no method.
- Merged-cluster splitting in silicon: named, no method.
- Dose: dependence listed, constants treated as conditions, no procedure for changing irradiation conditions in the fit.

Signature facts: container/schema; representation (binary, ToT, analog charge, cluster, retained raw or not); coordinates (1D strip or 2D pixel, sensor frame, pitch); acquisition (integration time, rolling or frame, event-time source); bindings (geometry, alignment, field, material, masks, Lorentz angle, dose-period conditions). 5.15: BP01 samples/clock/window; BP02 channel features with local coordinates; BP03 measurements or source links with surfaces; BP04 tracks with state and covariance.

Applicability: `schema && local_measurement && geometry && readout_mode_known && (pixel_2d || (strip_1d && second_view_with_ambiguity_retained))`; track: `&& source_links && surfaces && (field_and_material || straight_line_declared)`; momentum: `&& field_map && material && alignment`; vertex: `tracks_with_covariance && (beam_constraint_checked || no_beam_constraint)`.
Stays unknown: event time without a stamp or external association; 2D point from one strip view; charge from binary hits; Lorentz shift without `theta_L` and field; finding when only truth-assisted fitting exists.

## F04 Drift chambers/tubes, straws, gaseous muon drift

E: collider/fixed-target muon and tracking systems; event readout.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | documented | `gaseous-and-specialized-tracking-technologies.md#drift-chambers-and-drift-tubes`, `front-end-electronics-and-signal-processing.md#time-pickoff` | TDC time; subtract t0, walk, propagation along the wire | drift time [ns] | residual flat versus amplitude after walk correction | out-of-time hit taken as a drift time | `none`; adjacent: `garfield.gas-table-query` (table input); E | none; adjacent: VALIDATION DETSIM-W4G (pipeline only) |
| Finding/association | documented | `gaseous-and-specialized-tracking-technologies.md#drift-chambers-and-drift-tubes`, `tracking-and-vertexing.md#track-finding-strategies`, `muon-systems.md#reconstruction-chain` | segment line fit through `(z, +-r)`; Legendre transform; link segments; chi-square match to inner track | drift circle, segment, track link | staggered layers resolve left-right | false left-right solution; accidental segment matched as rate grows | `none`; E | none |
| Parameter estimation | documented | `gaseous-and-specialized-tracking-technologies.md#drift-chambers-and-drift-tubes`, `detector-case-studies-and-checklists.md#case-3-drift-chamber-t0rt-offset`, `tracking-and-vertexing.md#the-track-fit` | r(t) per cell and condition; per-period t0 refit; annealing weights left-right | r(t) [length per time], t0 [ns], radius [length] | t0 offset gives opposite signs left and right in signed residual | t0 degenerate with alignment when one side dominates | `none`; adjacent: `garfield.gas-table-query` (drift velocity from a 1D table, not r(t)); E | none; adjacent: `tests/adapters/test_detsim_garfield.py`, VALIDATION DETSIM-W4G |
| Space/time/direction | documented | `gaseous-and-specialized-tracking-technologies.md#drift-chambers-and-drift-tubes`, `muon-systems.md#reconstruction-chain` | radius, not point; stereo or small-angle wires for second coordinate; segment direction | radius [length], segment position and direction | residual versus drift distance flat with wire position fixed | wire sag or wire offset read as resolution | `none`; E | none |
| Energy/momentum | documented | `muon-systems.md#reconstruction-chain`, `muon-systems.md#performance-and-scaling` | sagitta in field with material; standalone and combined fit | q/p [1/(GeV/c)], p [GeV/c] | inner tracker dominates low p, muon system high p | weak-mode misalignment shifts q/p with charge | `none`; E | none |
| PID/topology | documented | `particle-identification.md#muon-systems`, `muon-systems.md#backgrounds-and-fakes`, `muon-systems.md#reconstruction-chain` | penetration plus match; muon types declared | muon type label; matching chi-square | segment-tagged muon recovers low momentum | punch-through; decay in flight with kink; penetration assumed prompt | `none`; E | none |
| Uncertainty/quality | documented | `gaseous-and-specialized-tracking-technologies.md#distinctive-but-generalizable-reconstruction-and-performance-features-drift-systems`, `muon-systems.md#distinctive-but-generalizable-reconstruction-and-performance-features-muon-system` | residual versus drift distance, angle; two tail mechanisms; tag-and-probe per type | residual [length], efficiency per muon type, charge misID | Z or J/psi mass closure versus eta, phi, charge | one "muon efficiency" over all types | `none`; adjacent: `tag_and_probe_efficiency.py`; E | none |

Variant and condition gaps:

- Straws: one bullet, a features line and table rows; left-right and transfer of r(t) only. No straw-specific r(t) text.
- Wire sag: named as a piece and a degeneracy, no correction method.

Signature facts: representation (TDC time, with or without amplitude); time convention (t0 reference, clock); coordinates (wire positions, stereo angle, cell map); bindings (r(t) or `v_d` per cell and condition, gas, T, P, field, wire geometry, alignment); acquisition (event time source, occupancy). 5.15: BP01 samples/clock/window if waveforms; BP02 channel features with geometry; BP03 measurements with surfaces, field, material; BP07 clock/event time.

Applicability: `schema && drift_time && wire_geometry && (calibrated_rt || (v_d_table && rt_derivation_planned)) && (external_t0 || fitted_t0_from_residuals) && (staggered_layers || segment_or_track_fit || wire_signal_timing)`; momentum: `&& field && material && (standalone_chain || inner_track_match)`.
Stays unknown: radius without t0 and r(t); side of the wire when no left-right constraint exists (keep two-fold); t0 versus alignment when one side dominates or geometry is fixed.

## F05 GEM, Micromegas, other MPGDs

E: collider/fixed-target, test beam; high rate.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | documented | `gaseous-and-specialized-tracking-technologies.md#micro-pattern-gaseous-detectors-gem-micromegas-and-relatives`, `front-end-calibration.md` | generic pedestal and noise; gain map from in-situ tracks; discharge flagged | pad/strip charge [ADC to fC via gain] | gain map flattens cluster charge | discharge event; rate-driven gain drop | `none`; E | none |
| Finding/association | documented | `gaseous-and-specialized-tracking-technologies.md#micro-pattern-gaseous-detectors-gem-micromegas-and-relatives`, `tracking-and-vertexing.md#track-finding-strategies` | pad/strip clustering; generic track finding; 2D strip projections keep ambiguity | cluster, strip-pair candidate | isolated cluster with size matching angle | cross-pad sharing; high occupancy (no splitting text) | `none`; E | none |
| Parameter estimation | documented | `gaseous-and-specialized-tracking-technologies.md#micro-pattern-gaseous-detectors-gem-micromegas-and-relatives` | charge centroid or template; micro-TPC segment | local position [length] | residual flat at normal incidence | centroid bias on inclined tracks | `none`; E | none |
| Space/time/direction | documented | `gaseous-and-specialized-tracking-technologies.md#distinctive-but-generalizable-reconstruction-and-performance-features-mpgd` | residual versus angle; micro-TPC gives angle per chamber | position [length], angle [rad] | micro-TPC removes inclined-track dependence | angle-dependent bias ignored; one strip view read as 2D | `none`; E | none |
| Energy/momentum | documented | `muon-systems.md#reconstruction-chain`, `tracking-and-vertexing.md#the-track-fit` | only through a system fit: chambers feed segments and q/p | q/p [1/(GeV/c)] from the host tracker | GEM or Micromegas stations in a muon chain | momentum claimed from a single chamber | `none`; E | none |
| PID/topology | gap-method | none for MPGD | no MPGD dE/dx or topology text; muon ID is the system's | none; deliver cluster charge only | none | none | `none`; E | none |
| Uncertainty/quality | documented | `gaseous-and-specialized-tracking-technologies.md#common-misconceptions-and-failure-modes`, `gaseous-and-specialized-tracking-technologies.md#distinctive-but-generalizable-reconstruction-and-performance-features-mpgd` | residual versus angle; efficiency at operating rate; heuristic resolution scaling | residual [length], efficiency versus rate | efficiency measured at operating rate | plateau efficiency quoted across rates | `none`; E | none |

Variant and condition gaps:

- Other MPGDs: "relatives" only; no named variant (T01 searched THGEM, RWELL; repeated here, no hit).
- Micro-TPC: one clause. No time-to-depth or t0 text.
- High-occupancy clustering: no method.

Signature facts: representation (pad or strip, analog charge, time samples if micro-TPC); coordinates (pitch, readout plane, one or two views); bindings (gain map, drift field, gas, alignment); acquisition (rate, discharge flags). 5.15: BP01; BP02 channel features with coordinates; BP03 measurements; BP08 drift waveforms and carrier mapping for micro-TPC.

Applicability: `schema && pad_or_strip_charge && geometry && (gain_map || uncalibrated_declared) && (pads_2d || (two_strip_views && projection_ambiguity_retained))`; angle: `&& ((micro_tpc_time_samples && drift_law) || track_external)`.
Stays unknown: charge scale without a gain map; 2D from one strip view; micro-TPC depth until a t0 source is defined, which the plugin does not yet state.

## F09 Dual-phase noble-liquid TPC

E: low-background underground; event waveforms, low occupancy.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | documented | `noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs`, `front-end-waveform-processing.md#amplitude-and-time-from-sampled-waveforms` | pulse finding for S1, S2, single-electron tails | pulse area [phe], pulse time [ns] | S1 and S2 found with threshold efficiency | delayed emission or pileup; low-threshold pulse lost | `none`; adjacent: `frontend_response.py waveform-toy` (generic pulse); E | none; adjacent: `tests/skills/hep_detector/test_frontend_waveforms.py`, VALIDATION FRONTEND-RECO-SIM (TOY) |
| Finding/association | gap-method | none: `noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs` names "pairing" and "mis-pairing" only | no S1-S2 pairing procedure | S1-S2 candidate relation, undefined | none | incorrect multiple-S1/S2 pairing (plan case) | `none`; E | none |
| Parameter estimation | documented | `photon-likelihood-reconstruction.md#the-expected-light-model`, `noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs` | light-response fit; gains from mono-energetic lines; lifetime correction | LRF fraction per sensor; gains; `tau_e` [time] | line position stable versus depth after `tau_e` map | stale `tau_e`: z-dependent scale | `none`; E | none |
| Space/time/direction | documented | `noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs`, `photon-likelihood-reconstruction.md#the-expected-light-model`, `event-reconstruction.md#planning-a-reconstruction-the-method-contract` | xy from top array; `z = v_d Delta t`; field-distortion map | x, y, z [length], drift time [time] | uniform-source position map | wall events biased inward; no paired S1: no absolute z | `none`; E | none |
| Energy/momentum | documented | `noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs`, `noble-liquid-neutrino-and-rare-event-detectors.md#rare-event-detectors`; source-unverified: PDG RPP 2025 sec. 36; Lindhard model as named | `E = W (n_gamma + n_e)`; state W; quenching model for nuclear recoils | energy [keV, electron-equivalent or nuclear-recoil, declared] | calibration line improves in the combined scale | electron-equivalent applied to nuclear recoils; charge and light summed without recombination | `none`; E | none |
| PID/topology | documented | `noble-liquid-neutrino-and-rare-event-detectors.md#noble-liquid-tpcs`, `front-end-waveform-processing.md#pulse-shape-discrimination` | charge-to-light ratio; pulse shape in argon | discrimination variable, leakage at stated acceptance | leakage versus energy from calibration sources | extrapolating leakage below calibrated energy | `none`; E | none |
| Uncertainty/quality | documented | `noble-liquid-neutrino-and-rare-event-detectors.md#rare-event-detectors`, `detector-case-studies-and-checklists.md#case-8-noble-liquid-electron-lifetime-drift` | threshold efficiency, fiducial mass, lifetime propagation | `epsilon(E)`, fiducial mass [kg], `tau_e` error | fiducial-mass uncertainty entered in the rate | fiducial cut uncertainty ignored | `none`; E | none |

Variant and condition gaps:

- S1-S2 pairing with multiple candidates: no method (the axis gap).
- Multi-scatter events: "multiple scatters" named in pulse finding, no reconstruction or energy-sharing text (the germanium multi-site text is a different family).
- Incomplete signals (one of S1, S2 missing): no restricted-delivery text.
- Extraction efficiency and gain: one line, no method.

Signature facts: representation (PMT waveforms or pulse summaries, retained or not); quantity (phe, drift time convention); acquisition (event window, trigger, single-electron tail ownership); bindings (`v_d`, `tau_e` by period, light and charge maps, field map, sensor map, S1 and S2 gains, W value). 5.15: BP01 samples/clock/window; BP06 live and dead sensors, light model; BP08 carrier and alternative timing constraints; BP15 for shared clock between charge and light.

Applicability: `schema && waveforms_or_pulses && clock && sensor_map && (paired_s1_s2 && v_d && tau_e)` for position and corrected energy; `&& lrf_map` for xy; `&& s1_gain && s2_gain && w_value` for combined energy.
Alternative constraints: none stated for z in dual phase; S1 is the only time reference in the text. Without it, report no absolute drift position, apply no drift-time correction, mark charge uncorrected.
Stays unknown: z and corrected energy without a pair; recoil type outside the calibrated energy range; which S1 goes with which S2 under pileup (retain candidates).

## F12 LGAD, MCP, other precision timing layers

E: collider/fixed-target, beam instrumentation; event readout.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | documented | `timing-detectors.md#pulse-time-extraction`, `front-end-waveform-processing.md#amplitude-and-time-from-sampled-waveforms`; source-unverified: Cleland and Stern | leading edge plus walk curve; CFD; joint amplitude-time template | pulse time [ps], amplitude or ToT | same shape, different amplitudes: walk removed | low-amplitude tail; free-time fit below `A/sigma` about 10 | `none`; adjacent: `frontend_response.py` `timing`, `waveform-toy`; E | none; adjacent: `tests/skills/hep_detector/test_frontend_waveforms.py`, VALIDATION FRONTEND-RECO-SIM (TOY, generic pulse) |
| Finding/association | documented | `timing-detectors.md#time-resolution-budget-single-hit`, `event-reconstruction.md#timing-and-event-association` | extrapolate track, match position and time, resolve multi-hit; bunch assignment | hit-track relation, bunch ID | one hit per cell inside the window | wrong interaction: late/early tail; wrong bunch | `none`; E | none |
| Parameter estimation | documented | `timing-detectors.md#calibration-and-diagnostics`, `timing-detectors.md#pulse-time-extraction` | per-channel t0 and walk from a reference; clock transfer | t0 offset [ps], walk curve | residual flat versus amplitude and run | t0 constants held fixed under dose | `none`; E | none |
| Space/time/direction | documented | `timing-detectors.md#time-resolution-budget-single-hit` | keep single-hit, per-track, event-time, system apart | hit, track and event time [ps] | averaging reduces only uncorrelated terms | common-clock term averaged away | `none`; adjacent: `frontend_response.py timing`; E | none |
| Energy/momentum or identifiable | documented | `timing-detectors.md#relations-definition-exact-unless-noted`, `particle-identification.md#time-of-flight-tof` | `beta = L/(c t)`, `m^2` with supplied path, reference time and p; no energy from time | beta [dimensionless], `m^2` [GeV^2/c^4] | path from the track fit | straight-line path at low momentum; amplitude read as energy | `none`; adjacent: `pid_separation_power.py --mode tof` (design); E | none; adjacent: `tests/skills/hep_detector/test_detector_helpers.py` (analytic) |
| PID/topology | documented | `particle-identification.md#time-of-flight-tof`, `timing-detectors.md#distinctive-but-generalizable-reconstruction-and-performance-features-timing` | TOF hypothesis residual `t_meas - t_pred(p, m, L)` | species hypothesis, time residual [ps] | residual per known species centred | used above the momentum ceiling; start-time error as mass shift | `none`; adjacent: `pid_separation_power.py`; E | none |
| Uncertainty/quality | documented | `timing-detectors.md#time-resolution-budget-single-hit`, `timing-detectors.md#technologies`; source-unverified: PDG RPP 2025 eq. 35.25 | budget by term; core sigma and tail fraction; global clock cancels in differences | sigma terms [ps], tail fraction | budget states which terms average | single-channel resolution quoted as system; radiation damage held static | `none`; E | none |

Variant and condition gaps:

- MCP: one bullet and Table 1/3 rows. No reconstruction text of its own (ion feedback and aging named only).
- Other precision layers: one bullet for tracker and calorimeter timing.
- Slewing and gain versus fluence: dependence stated, no correction procedure.

Signature facts: representation (waveform, or time with amplitude or ToT); time convention (clock domain, reference, bunch phase); bindings (per-channel t0, walk curve, clock tree, sensor gain and fluence by period, mask); request (hit, track or event time). 5.15: BP01 samples/clock/window; BP03 track for association; BP07 time/path/momentum, clock and event time. A sensor name alone cannot select TOF.

Applicability: `schema && (waveform_and_clock || (discriminator_time && (amplitude || tot))) && channel_t0 && clock_domain`; track time: `&& track_extrapolation`; TOF: `&& path_length && (start_detector || bunch_crossing || event_time_from_tracks) && momentum`.
Stays unknown: absolute time, without a reference; beta, without path; system resolution when clock correlations are not declared; species, without momentum.

## F13 Threshold/differential Cherenkov, RICH, DIRC, TOP

E: collider/fixed-target and space; event readout.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | documented | `cherenkov-imaging-variants-and-photosensors.md#photosensors-and-light-transport`, `cherenkov-imaging-variants-and-photosensors.md#cherenkov-pid-variants` | photon hits or counts from SPE response; dark rate kept | `N_pe` [count], hit position, time [ns] | gain and SPE monitored | dark counts at low `N_pe` | `none`; E | none |
| Finding/association | documented | `particle-identification.md#ring-imaging-cherenkov-detectors-rich`, `cherenkov-imaging-variants-and-photosensors.md#cherenkov-pid-variants` | track-seeded track-photon association; background term in likelihood; photon-path hypotheses | photon-track relation, ring or arc | isolated ring around a track | overlapping rings; secondaries; left/right bounce paths | `none`; E | none |
| Parameter estimation | documented | `particle-identification.md#ring-imaging-cherenkov-detectors-rich`; source-unverified: PDG "Passage of particles through matter", Cherenkov radiation; PDG "Particle detectors at accelerators", Cherenkov detectors | `cos theta_c = 1/(n beta)`; per-photon angle; per-track average | `theta_c` [rad], `N_pe` | `sigma_theta` shrinks by `sqrt(N_pe)` to `sigma_trk` | chromatic term ignored at low photon count | `none`; adjacent: `skills/hep-detector/scripts/cherenkov_angle.py` (declared inputs, no photon data); E | none; adjacent: `tests/skills/hep_detector/test_detector_helpers.py` (analytic) |
| Space/time/direction | documented | `cherenkov-imaging-variants-and-photosensors.md#cherenkov-pid-variants` | angle relative to the supplied track; photon time in DIRC/TOP; a threshold counter yields no angle or position | photon angle [rad], arrival time [ns] | TOP time breaks path degeneracy | multiple paths with the same position; track direction error treated as averaging | `none`; E | none |
| Energy/momentum or identifiable | documented | `particle-identification.md#ring-imaging-cherenkov-detectors-rich`, `cherenkov-imaging-variants-and-photosensors.md#cherenkov-pid-variants` | beta with supplied p gives mass; threshold gives only `p > p_th` information | beta [dimensionless], or threshold bit; no energy | mass from beta and rigidity with `gamma^2` propagation | unique beta claimed from a threshold counter | `none`; adjacent: `cherenkov_angle.py`; E | none |
| PID/topology | documented | `particle-identification.md#ring-imaging-cherenkov-detectors-rich`, `particle-identification.md#combining-measurements`, `cherenkov-imaging-variants-and-photosensors.md#cherenkov-pid-variants` | likelihood per hypothesis; absence above threshold with ring efficiency; which counter fired | likelihood difference, species hypothesis | kinematic control samples set efficiency and mis-ID | absent ring read as exclusion without detection efficiency; LLR read as probability | `none`; adjacent: `pid_separation_power.py --mode velocity`; E | none |
| Uncertainty/quality | documented | `cherenkov-imaging-variants-and-photosensors.md#distinctive-but-generalizable-reconstruction-and-performance-features-cherenkov-imaging`, `detector-case-studies-and-checklists.md#case-6-rich-refractive-index-drift` | per-photon residual; turn-on `1 - exp(-N_pe(p))`; index monitoring | residual [rad], `epsilon(p)`, ring efficiency and misreconstruction rate | per-photon residual centred with background pedestal | Gaussian `N_sigma` on few photons; index drift | `none`; E | none |

Variant and condition gaps:

- TOP: "timing-position likelihood" named; no time density or likelihood form.
- DIRC: one paragraph shared with TOP; same gap.
- Differential counter: selection principle and systematic only; no estimator or output rule.
- Ring finding without a track seed: no method.

Signature facts: representation (count, photon hits, photon hits with time); bindings (radiator, n by period, T/P, optics, mirror alignment, photosensor map, dark rate); quantity (angle or time convention); request (species, beta, threshold bit); supplied track state and p. 5.15: BP01 samples/clock/window; BP06 charge/count/time, live/dead/unhit; BP07 radiator, path, species operating point.

Applicability: `schema && photon_observable && radiator_index && live_mask`; threshold: `&& track_momentum && turn_on`, output threshold information only; RICH: `&& track_state && optics && background_model`; DIRC/TOP: `&& bar_optics && photon_time && clock && photon_path_model`.
Stays unknown: beta for a threshold counter; species without momentum; exclusion by absence without ring efficiency; TOP hypothesis response until a time density is defined.

## F14 TRD and multisample ionization PID/charge

E: collider/fixed-target and space/balloon; event readout.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | documented | `particle-identification.md#combining-many-samples`, `particle-identification.md#transition-radiation-detectors-trd`; source-unverified: PDG for TR X-ray range | path correction; inversion through measured response curve; TR as statistical per-layer excess | per-layer signal [ADC or MeV], path cosine | saturating curve inverted | pure `Z^2` law at high Z | `skills/hep-detector/scripts/multisample_pid.py charge`; E | `tests/skills/hep_detector/test_multisample_pid.py` (`test_saturating_response_is_inverted`, `test_path_length_correction`); VALIDATION UPGRADE-B (SYNTHETIC) |
| Finding/association | gap-method | none: only consistency rejection in `particle-identification.md#ionization-energy-loss-dedx`, `nuclear-interactions-in-detector-material.md` | no text assigning layer signals to a track | layer-track relation, undefined; samples arrive pre-assigned | none | mis-associated hit passing the consistency test | `none`; E | none |
| Parameter estimation | documented | `particle-identification.md#ionization-energy-loss-dedx`, `particle-identification.md#combining-many-samples`; source-unverified: PDG RPP 2024 eq. 35.17 | truncated mean, weighted mean with declared correlation, Moyal likelihood | \|Z\| estimate; truncated dE/dx | core width against `--toys` prediction | mean of few samples dominated by Landau tail | `multisample_pid.py charge`; E | `test_multisample_pid.py` (`test_truncated_mean_width_matches_toys`); VALIDATION UPGRADE-B (SYNTHETIC) |
| Space/time/direction | not-applicable | `particle-identification.md#combining-many-samples` | readout reason: per-layer amplitudes; path and direction are inputs from the track, so no coordinate output; a straw stack's coordinates belong to F04 | input only: `cos(theta)` | not applicable | not applicable | `none`; E | none |
| Energy/momentum or identifiable | documented | `particle-identification.md#transition-radiation-detectors-trd`, `particle-identification.md#ionization-energy-loss-dedx` | identifiable: \|Z\|; beta from dE/dx with supplied p; `gamma` band from TR yield; no energy | \|Z\| [e units], `gamma` band | momentum band stated with working point | energy or `gamma` value claimed from one TRD layer | `multisample_pid.py charge` for \|Z\| only; E | as parameter estimation (SYNTHETIC) |
| PID/topology | documented | `particle-identification.md#transition-radiation-detectors-trd`, `particle-identification.md#combining-many-samples`, `particle-identification.md#combining-measurements` | per-layer LLR from control-sample PDFs; count of layers over threshold; rejection at fixed efficiency | LLR, efficiency, rejection factor | LLR reaches the Neyman-Pearson bound on known PDFs | species-band overlap; TRD and dE/dx multiplied as independent; LLR read as probability | `multisample_pid.py likelihood` (LLR; no layer-count estimator); adjacent: `pid_separation_power.py`; E | `test_multisample_pid.py` (`test_reaches_the_neyman_pearson_bound`); VALIDATION UPGRADE-B (SYNTHETIC) |
| Uncertainty/quality | documented | `particle-identification.md#combining-many-samples`, `particle-identification.md#combining-measurements` | leakage matrix P(reco\|true) with Clopper-Pearson; sigma68 and tail fraction; correlation declared or "independence assumed" | leakage matrix, sigma68, efficiency-misID curve | neighbouring-charge migration block | missing layers filled with zero (BP07); layers summed as independent | `multisample_pid.py`; E | `test_multisample_pid.py` (`test_leakage_matrix_matches_the_gaussian_truth`, `test_declared_correlation_is_reported`); VALIDATION UPGRADE-B (SYNTHETIC) |

Variant and condition gaps:

- TRD layer response: no gas or gain model; the text requires measured per-layer distributions, so the model is a calibration input.
- TRD threshold-count estimator: documented, not in `multisample_pid.py`.
- Missing layers: BP07 requires a validated missing-input method; the plugin has none.
- `multisample_pid.py` has no file in `contracts/tool_contracts/`.

Signature facts: representation (per-layer samples, retained or truncated summary); quantity (signal scale, path cosine convention); bindings (response curve, per-layer PDFs with sample and selection, gas and gain by period, momentum band); request (|Z|, species, working point); declared layer correlation. 5.15: BP01 samples/clock/window; BP07 layer observations, species/charge operating point.

Applicability: `schema && per_layer_samples && (path_correction || no_path_correction_declared) && response_curve`; PID: `&& per_layer_pdfs_from_control_samples && momentum_band`; independence: `declared_correlation || independence_assumed_stated`.
Stays unknown: species without momentum; probability without priors; layer correlation (never invented); neighbouring-charge assignment outside the response curve's range.

## F15 Homogeneous ECAL: crystal, lead-glass, etc.

E: collider/fixed-target; event readout.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | documented | `front-end-waveform-processing.md#amplitude-and-time-from-sampled-waveforms`, `calibration-and-alignment.md#calibration-standards-and-their-pitfalls`; source-unverified: Cleland and Stern; M. Aharrouche et al., arXiv:0709.1094 | optimal filter; pi0/eta or phi-symmetry intercalibration; light monitoring | cell amplitude [ADC to GeV] | intercalibration with an absolute reference | stale weights under pileup; light-yield drift | `none`; adjacent: `frontend_response.py optimal-filter` (fixed CR-RC^n pulse); E | none; adjacent: VALIDATION FRONTEND-RECO-SIM (TOY) |
| Finding/association | documented | `event-reconstruction.md#clustering` | window or topological growth; splitting | cluster, seed and growth thresholds | single shower contained in window | overlapping photons merged: summed energy, intermediate position | `none`; E | none |
| Parameter estimation | documented | `event-reconstruction.md#clustering`, `calorimetry-ecal-hcal.md#leakage-dead-material-and-containment` | cluster sum with leakage and dead-material corrections, in energy and angle | cluster energy [GeV], energy kind declared | correction applied per energy and polar angle | single global correction | `none`; E | none |
| Space/time/direction | documented | `calorimetry-ecal-hcal.md#shower-position-direction-and-shape`; source-unverified: Awes et al., Nucl. Instrum. Methods A 311 (1992) 130 | S-curve or log-weight position at stated depth; direction only with longitudinal layers or a track segment | position [length] at depth; direction [rad] if identifiable | S-curve correction within the cell | shower edge; direction claimed from an unsegmented block | `none`; E | none |
| Energy/momentum | documented | `calorimetry-ecal-hcal.md#homogeneous-versus-sampling-calorimeters`, `calorimetry-ecal-hcal.md#the-resolution-decomposition`, `detector-case-studies-and-checklists.md#case-4-ecal-dead-material-and-nonlinearity`; source-unverified: PDG RPP 2025 sec. 34.5 | calibrated deposit, then scale and nonlinearity; `E/p` cross-check | E [GeV], deposited or incident declared | `Z -> ee`, pi0 mass closure | saturation; deposited energy substituted for incident | `none`; adjacent: `calorimeter_resolution.py` (fits supplied points); E | none; adjacent: `tests/skills/hep_detector/test_detector_helpers.py` (analytic) |
| PID/topology | documented | `calorimetry-ecal-hcal.md#calorimeter-based-identification`, `calorimetry-ecal-hcal.md#shower-position-direction-and-shape` | shower shape; `E/p`; double peak for two photons | shape variables, `E/p` | electron `E/p` near 1 | converted photon (no method); bremsstrahlung tail above 1 | `none`; E | none |
| Uncertainty/quality | documented | `calorimetry-ecal-hcal.md#the-resolution-decomposition`, `calorimetry-ecal-hcal.md#shower-position-direction-and-shape` | three terms at cluster energy; enlarge or flag for leakage; pulls | sigma_E [GeV], flags | pulls on test beam or `E/p` | stochastic term alone extrapolated; negative squared term clipped | `none`; adjacent: `calorimeter_resolution.py`; E | none; adjacent as above |

Variant and condition gaps:

- Crystal: Table 1 and Table 5 rows plus shared text. No crystal-specific reconstruction.
- Lead-glass: one Table 5 row and a passing mention in `signal-formation-and-readout.md`. No reconstruction text.
- "etc." in the plan row: no further homogeneous media named.
- Converted photon: appears in tables and Case 4 as a tail; no method.

Signature facts: representation (cell energies or waveforms, retained); quantity (energy kind: deposited, EM scale, incident); bindings (geometry, material upstream, intercalibration, absolute scale, light-yield monitoring by period, masks); acquisition (pileup, thresholds used in clustering). 5.15: BP01 samples/clock/window; BP05 cells with geometry, energy kind, calibration, containment.

Applicability: `schema && cells_or_waveforms && geometry && masks && intercalibration && absolute_scale_reference`; incident energy: `&& leakage_model && dead_material_model`; direction: `longitudinal_segmentation || track_segment_for_charged_primary`.
Stays unknown: incident energy from deposit alone; direction without either alternative; one or two showers in a merged cluster unless splitting is validated (retain flag).

## F23 Ice/water neutrino telescopes and sparse optical arrays

E: large media ice/water; event readout, array.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | documented | `photon-likelihood-reconstruction.md#the-per-channel-likelihood`, `cherenkov-imaging-variants-and-photosensors.md#photosensors-and-light-transport` | charge via SPE response; first time or waveform series | charge [phe], time [ns] | Poisson counts in time bins with waveforms | single-photon density on first-time readout; saturated channel as a value | `none`; E | none |
| Finding/association | documented | `photon-likelihood-reconstruction.md#seeding-and-the-fit-sequence` | cleaning by windows and neighbour coincidences; event splitting | cleaned hit set, subevents | coincident muons split before fit | coincident muons fitted as one track; time density not matched to cleaned hits | `none`; E | none |
| Parameter estimation | documented | `photon-likelihood-reconstruction.md#the-per-channel-likelihood`, `photon-likelihood-reconstruction.md#the-expected-light-model`, `photon-likelihood-reconstruction.md#seeding-and-the-fit-sequence`; source-unverified: Ahrens et al., Nucl. Instrum. Methods A 524 (2004) 169 | line-fit seed; multistart all-channel likelihood; tabulated light model | hypothesis x, -ln L, minimum reached | seeds recorded, wrong-minimum rate measured | local minima; dead channels counted as unhit | `none`; E | none |
| Space/time/direction | documented | `photon-likelihood-reconstruction.md#seeding-and-the-fit-sequence`, `neutrino-astronomy.md#event-topologies`; source-unverified: PDG RPP 2025 sec. 36.3.2 | direction and vertex from fit; down-going-constrained refit | direction [rad], vertex [length], time [ns] | Moon-shadow pointing check | reversed track: down-going muon as up-going | `none`; E | none |
| Energy/momentum or proxy | documented | `photon-likelihood-reconstruction.md#energy`, `neutrino-astronomy.md#event-topologies`; source-unverified: Aartsen et al., J. Instrum. 9 (2014) P03009 | light fit; truncated mean or unfolded loss; range if contained | visible, EM-equivalent or in-detector muon energy [GeV], declared | cascade with most energy contained | through-going muon energy read as neutrino energy; raw charge sum | `none`; E | none |
| PID/topology | documented | `photon-likelihood-reconstruction.md#topologies-and-hypothesis-comparison`, `neutrino-astronomy.md#event-topologies` | fit each hypothesis, compare with a calibrated variable | track, cascade or double-pulse label with efficiency and mis-ID | double cascade fitted within one event | track/cascade confusion; raw likelihood favouring more parameters | `none`; E | none |
| Uncertainty/quality | documented | `photon-likelihood-reconstruction.md#per-event-uncertainty-and-quality`, `detector-measurement-framework.md#choosing-the-estimator` | paraboloid or resampling; pulls in energy and topology; effective area | angular error [rad], quality variables, IRF | pull width flat in energy and topology | Hessian trusted for few-photon events; optical parameters varied per event | `none`; E | none |

Count and spectrum outputs are legitimate here: effective area and scrambled-RA background (`neutrino-astronomy.md#significance-and-exposure`) need no per-event claim beyond direction and energy proxy.

Variant and condition gaps:

- Sparse optical arrays as a distinct variant: "sparse timing geometry" only; no text for reduced coverage.
- Water versus ice: shared text; water has biofouling and a cascade direction figure only.

Signature facts: representation (charge and first time, or traces; retained after cleaning or not); quantity (phe, time offsets, group and phase index convention); acquisition (trigger, cleaning applied before input, readout window); bindings (sensor geometry, live/dead masks, optical model and version, noise rate, sensor acceptance). 5.15: BP01; BP06 live/dead/unhit, first-time or series, optics and light model; BP11 geometry/time, medium, trigger/multiplicity.

Applicability: `schema && sensor_charge_time && geometry && time_offsets && live_mask && (analytic_light_model || tabulated_light_model) && noise_rate`; all-channel likelihood: `&& unhit_semantics && (first_time_density_with_total_mu || waveform_series)`; time density: `cleaning_described`.
Stays unknown: full-likelihood claim without unhit semantics; neutrino energy from a through-going track; direction of a sparse event outside the supported domain. Live versus dead must not be assumed from absence.

## F29 Air-shower surface arrays

E: ground-based atmosphere; array, continuous operation with event triggers.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | documented | `ground-based-detection-arrays.md#surface-array-event-reconstruction` | station scale from atmospheric-muon background; low-gain or undistorted-pulse recovery | station signal [reference muon units], start time [ns] | scale follows ageing and temperature | omnidirectional peak taken as the reference unit; saturated station as a value | `none`; E | none |
| Finding/association | gap-method | none: `ground-based-detection-arrays.md#surface-array-event-reconstruction` assumes the event's station set | no text selecting stations for an event or rejecting chance stations | station-event relation, undefined | none | sparse stations with an unrelated triggered station (design case) | `none`; E | none |
| Parameter estimation | documented | `ground-based-detection-arrays.md#surface-array-event-reconstruction` | joint core and size lateral fit; non-triggered stations bound the footprint; saturated censored | core [length], signal at reference distance [muon units] | non-triggered stations in the likelihood | saturated station as measured; non-triggered dropped | `none`; E | none |
| Space/time/direction | documented | `ground-based-detection-arrays.md#surface-detector-arrays`, `ground-based-detection-arrays.md#surface-array-event-reconstruction` | plane or curved-front fit with time-variance model | arrival direction [rad], core | time variance grows far from core | equal weights across stations; clock offset | `none`; E | none |
| Energy/momentum or proxy | documented | `ground-based-detection-arrays.md#surface-detector-arrays`, `extensive-air-showers.md#shower-universality` | signal at reference distance; constant-intensity cut; hybrid calibration | size proxy; energy [stated unit] only with calibration | fluorescence subsample sets the conversion | conversion assumed from simulation alone; energy-domain shift | `none`; E | none |
| PID/topology | documented | `ground-based-detection-arrays.md#surface-array-event-reconstruction`, `ground-based-detection-arrays.md#muon-detectors-radio-detection-and-wide-field-gamma-ray-arrays`, `extensive-air-showers.md#the-muon-puzzle`; source-unverified: ApJ 843 (2017) 39; Chin. Phys. C 45 (2021) 025002 | second response for muon/EM split; lateral hit pattern; `N_mu/N_e` | composition proxy, gamma/hadron variable | shielded muon counters outside the punch-through region | muon content alone taken as composition | `none`; E | none |
| Uncertainty/quality | documented | `ground-based-detection-arrays.md#surface-array-event-reconstruction`, `ground-based-detection-arrays.md#instrument-response-functions-checklist` | shower-to-shower and sampling fluctuations, lateral-shape term; IRF checklist | size uncertainty, exposure [m^2 sr s] | exposure above full trigger efficiency | composition-dependent trigger efficiency ignored below it | `none`; E | none |

Variant and condition gaps:

- Array edge: no text.
- Sparse stations and degenerate core: no surface-array text (the radio section states it for antennas only).
- Energy-domain shift: no procedure.

Signature facts: representation (signal, time, optional trace per station; station state); quantity (signal unit, time reference); acquisition (trigger, station state list, exposure); bindings (station geometry, clock, calibration by period, atmosphere, hadronic model for any conversion). 5.15: BP01 samples/clock/window; BP11 station observations with geometry/time, trigger/multiplicity; BP15 for hybrids: shared geometry and clock.

Applicability: `schema && station_signal_time && geometry && clock && station_state(triggered, non_triggered, saturated, dead) && signal_scale`; energy: `&& lateral_model && attenuation_curve && (hybrid_calibration || simulation_conversion_with_model_declared)`; composition: `&& (muon_detector || layered_response || time_structure)`.
Stays unknown: energy without a conversion, deliver the size proxy; composition without a second response; absent station state (absent is not zero); full-chain claim outside the supported domain at edges or sparse coverage.

## F30 IACT and stereoscopic atmospheric Cherenkov imaging

E: ground-based atmosphere; single telescope or array, event images.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | documented | `imaging-atmospheric-cherenkov.md#image-cleaning-and-reconstruction-choices`, `photon-likelihood-reconstruction.md#the-image-template-variant` | pixel charge with SPE and night-sky-background noise; thresholds set against that background | pixel charge [phe], pixel time [ns] | background level matched to simulation per observation | moonlight raising noise with thresholds unchanged | `none`; E | none |
| Finding/association | documented | `imaging-atmospheric-cherenkov.md#image-cleaning-and-reconstruction-choices` | two-level neighbour cleaning, optional time coincidence | cleaned image | same cleaning in data and simulation | faint edges removed at low energy | `none`; E | none |
| Parameter estimation | documented | `imaging-atmospheric-cherenkov.md#the-technique`, `photon-likelihood-reconstruction.md#the-image-template-variant`; source-unverified: M. de Naurois and D. Mazin, C. R. Physique 16 (2015) 610; Parsons and Hinton, Astropart. Phys. 56 (2014) 26 | Hillas moments; template pixel likelihood; learned per hep-ml | size [phe], width, length, alpha [deg] | moments seed and cross-check template | template treated as simulation-independent; truncated image (no text) | `none`; E | none |
| Space/time/direction | documented | `imaging-atmospheric-cherenkov.md#image-cleaning-and-reconstruction-choices`, `imaging-atmospheric-cherenkov.md#the-technique` | stereo axis intersection; mono displacement with head-tail ambiguity | direction [deg], impact point [m] | stereo multiple images | mono head-tail ambiguity collapsed | `none`; E | none |
| Energy/momentum or proxy | documented | `imaging-atmospheric-cherenkov.md#energy-reconstruction` | size with impact distance, simulation-calibrated | reconstructed energy [TeV], atmospheric model declared | atmosphere model reported with the scale | absolute scale treated as calorimetric | `none`; E | none |
| PID/topology | documented | `imaging-atmospheric-cherenkov.md#the-technique`, `imaging-atmospheric-cherenkov.md#deliverables` | shape cuts or classifier; working point | gamma/hadron score, efficiency, rejection | training sample and working point reported | cosmic-ray electrons left by image shape; score read as probability | `none`; E | none |
| Uncertainty/quality | documented | `imaging-atmospheric-cherenkov.md#image-cleaning-and-reconstruction-choices`, `imaging-atmospheric-cherenkov.md#background-rejection-and-significance`, `imaging-atmospheric-cherenkov.md#instrument-response-functions-checklist` | pairwise intersection spread or covariance; PSF on a point source; ON/OFF counts; IRF | direction error [deg], counts, `alpha` | bright point source sets PSF | naive significance at low counts | counts only: `skills/hep-statistics/scripts/li_ma_significance.py`; reconstruction: `none`; E | ON/OFF walkthrough in the reference is a counts calculation; reconstruction: none |

Count, spectrum and image outputs are legitimate: ON/OFF excess, forward-folded spectrum, morphology (`imaging-atmospheric-cherenkov.md#spectral-and-morphological-analysis`).

Variant and condition gaps:

- Truncated image: no text.
- Bad telescope or bad pixel: no text.
- Cross-telescope image association: stereo intersection presumes it; no method.
- Pixel trace integration: no IACT text, only pixel charge as input.
- Learned estimator: deferred to hep-ml; no IACT-specific validation.

Signature facts: representation (pixel charge and time, or traces; cleaned or not); quantity (phe, camera coordinates, nominal frame); acquisition (telescope multiplicity, trigger, observation block, moonlight); bindings (pointing, optics, throughput from muon rings, night-sky-background level, atmosphere, simulation library version). 5.15: BP01; BP06 live/dead, optics and light model; BP11 camera observations with geometry/time, IACT variant, atmosphere, trigger/multiplicity.

Applicability: `schema && camera_pixels && pointing && pixel_mask && cleaning_config && nsb_level`; direction: `stereo_images_two_or_more || (mono_with_displacement && head_tail_retained)`; energy: `&& impact_distance && simulation_calibration && atmosphere_model`; estimator: `moments || (template_library_with_axes && pixel_noise_model) || learned_with_domain_check`.
Stays unknown: head-tail in mono unless resolved; absolute energy scale without the atmospheric and throughput model; truncated images, which sit outside any documented domain.

## F31 Air-shower fluorescence telescopes

E: ground-based atmosphere; telescopes, often hybrid with a surface array; dark-sky operation.

| Axis | Status | Reference anchor | Method | Observable/port | Positive case | Negative case | Binding/environment | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | gap-method | none: pixel signal is an input in `ground-based-detection-arrays.md#fluorescence-geometry-and-profile-reconstruction` | no pixel pulse or background-light method | pixel signal, undefined scale | none | none | `none`; E | none |
| Finding/association | gap-method | none: same section starts from "the pixels on the shower image" | no pixel selection or image finding text | image pixel set, undefined | none | none | `none`; E | none |
| Parameter estimation | documented | `ground-based-detection-arrays.md#fluorescence-geometry-and-profile-reconstruction`, `extensive-air-showers.md#longitudinal-profile-gaisser-hillas-and-greisen`; source-unverified: The Pierre Auger Collaboration, Nucl. Instrum. Methods A 798 (2015) 172; JCAP 03 (2019) 018 | shower-detector plane; `t_i(chi_i)` fit; Gaisser-Hillas profile fit | `R_p` [m], `chi_0` [rad], `dE/dX(X)` [energy per g/cm^2] | long track with curvature in `t(chi)` | short or distant track: `R_p`, `chi_0` degenerate | `none`; adjacent: `skills/hep-detector/scripts/xmax_gaisser_hillas.py` (evaluates a given profile, not a fit); E | none; adjacent: `tests/skills/hep_detector/test_reference_values.py` (analytic) |
| Space/time/direction | documented | `ground-based-detection-arrays.md#fluorescence-geometry-and-profile-reconstruction` | monocular, hybrid (one station time) or stereo (two planes) | shower axis [rad], core [m], `t_0` [ns] | station time breaks degeneracy | monocular degeneracy reported as a unique axis | `none`; E | none |
| Energy/momentum | documented | `ground-based-detection-arrays.md#fluorescence-detectors`, `ground-based-detection-arrays.md#atmospheric-monitoring`; source-unverified: Verzi for the Pierre Auger Collaboration, PoS ICRC2019 (2019) 231 | integrate profile; add invisible energy; subtract Cherenkov light | calorimetric and primary energy [EeV], kept separate | model of the invisible-energy correction named | Cherenkov light not subtracted; average atmosphere assumed | `none`; adjacent: `xmax_gaisser_hillas.py`; E | none |
| PID/topology | documented | `extensive-air-showers.md#longitudinal-profile-gaisser-hillas-and-greisen`, `ground-based-detection-arrays.md#fluorescence-detectors`; source-unverified: Kampert & Unger 2012, arXiv:1201.0018 | `X_max` mean and spread as composition proxies | `X_max` [g/cm^2], composition proxy | mean and fluctuation both used | single mean masking a mixed composition | `none`; E | none |
| Uncertainty/quality | documented | `ground-based-detection-arrays.md#fluorescence-geometry-and-profile-reconstruction`, `ground-based-detection-arrays.md#atmospheric-monitoring` | geometry propagated to `X_max` and energy; viewed-maximum selection; monitoring or exclusion | `X_max` and energy errors, selection flags | night without monitoring excluded | clouds; seasonal density profile ignored | `none`; E | none |

Variant and condition gaps:

- Field-of-view truncation: only the "viewed shower maximum" selection and the observed-versus-extrapolated deliverable; no procedure.
- Hybrid: one sentence on the station time; no association of station to telescope event, no hybrid selection bias text (BP15 obligation).
- Fluorescence pixel signal and image finding: the two axis gaps.

Signature facts: representation (pixel signal, time, pointing direction; retained traces or not); quantity (photon or light-at-aperture scale, depth); acquisition (night, monitoring coverage, telescope set); bindings (telescope calibration, atmospheric transmission by night, density profile, fluorescence yield model, invisible-energy model). 5.15: BP02 image features with geometry; BP11 camera observations with geometry/time, fluorescence variant, atmosphere; BP15 hybrid: shared geometry and clock.

Applicability: `schema && pixel_signal_time && pixel_pointing && (stereo_two_planes || hybrid_station_time || (mono && degeneracy_retained))`; profile: `&& atmospheric_transmission && density_profile && fluorescence_yield && cherenkov_subtraction`; energy: `&& invisible_energy_model && viewed_maximum`.
Stays unknown: `R_p` and `chi_0` for short monocular tracks; `X_max` when the maximum is outside the field of view; energy on nights without monitoring (exclude, never an assumed average).

## Counts

Cells: 84 (12 families, 7 axes). `documented` 77, `gap-method` 6, `not-applicable` 1, `gap-backend` 0.

`gap-method` cells: F05 PID/topology; F09 finding/association; F14 finding/association; F29 finding/association; F31 signal extraction; F31 finding/association.

Bindings: 10 cells have a real binding, with SYNTHETIC or simulated-event evidence only: F01 finding, parameter, position (hits), momentum (simreco) and PID (`multisample_pid.py`); F14 signal, parameter, identifiable, PID, uncertainty (`multisample_pid.py`). F30 uncertainty has a counts-only script. The other 73 cells have binding `none`.

## Corrections to the T01 inventory

1. F12 named gaps say multi-hit, common-clock correlation and wrong-interaction have "no procedure". `timing-detectors.md#time-resolution-budget-single-hit` gives track-to-hit matching, multi-hit resolution, bunch assignment, and the global or local clock split. No tool and no run remain true.
2. F23 says boundary events have no specific text. `photon-likelihood-reconstruction.md#the-per-channel-likelihood` states the boundary vertex bias from dropped unhit channels, and `#per-event-uncertainty-and-quality` uses track length in the instrumented volume.
3. F09, F29, F31 and F14 carry Documentation `yes` although a whole axis has no method: S1-S2 pairing; station selection; fluorescence pixel signal and image finding; layer-to-track assignment. The F29, F31 and F14 gaps are not in the inventory.
4. F05 omits `muon-systems.md`, which names GEM and Micromegas chambers, and "other MPGDs" remains an uncovered variant here (judgement call 5 goes the other way).
5. F04 omits three method anchors: `tracking-and-vertexing.md#track-finding-strategies` (Legendre on drift circles), `tracking-and-vertexing.md#the-track-fit` (annealing on left-right) and `detector-case-studies-and-checklists.md#case-3-drift-chamber-t0rt-offset`. "Straws have one bullet" undercounts slightly: a features line and table rows exist too.
6. F01 "no CCD pedestal" method: Table 1 lists pedestal for MAPS/DEPFET/CCD and generic pedestal text applies. The absence of a charge-transfer term is right. Judgement call 4's stricter reading is the one used here.

Checked and held: F13, F15, F30 and F31 tool `no`; `multisample_pid.py` has no tool contract; `xmax_gaisser_hillas.py` is an evaluator; simreco has no Lorentz model and reads element_sim only; all inventory anchors for these families resolve.

# Part 2: families the inventory marked partly documented

Read-only design table. Text read at `baseline-tree`, plugin 0.56.0. Paths are relative to `plugins/hep-research/`. Nothing was run. Plan = detector reconstruction plan v9.2, sections 5.5, 5.15, 6, 7.1.1, BP sections.

## Conventions

Anchor aliases, all under `skills/hep-detector/references/` unless stated:

| Alias | File | Alias | File |
|---|---|---|---|
| FEW | front-end-waveform-processing.md | EVT | event-reconstruction.md |
| FEE | front-end-electronics-and-signal-processing.md | TIM | timing-detectors.md |
| GAS | gaseous-and-specialized-tracking-technologies.md | PID | particle-identification.md |
| NOB | noble-liquid-neutrino-and-rare-event-detectors.md | CAL | calorimetry-ecal-hcal.md |
| PHO | photon-likelihood-reconstruction.md | GBA | ground-based-detection-arrays.md |
| SIG | signal-formation-and-readout.md | TBL | detector-comparison-tables.md |
| TRK | tracking-and-vertexing.md | MUO | muon-systems.md |
| CAS | detector-case-studies-and-checklists.md | CAA | calibration-and-alignment.md |
| RAR | skills/hep-measurement/references/rare-event-and-neutrino-measurements.md | | |

Rules applied:

- `documented`: the text names the family or technology, or states a transfer scope that includes it (for example TIM "every timed detector"), and gives method plus assumption or failure mode. Sensor-level text alone does not count (plan section 6: same sensor, not same method).
- A row's status is for the variants the text names. Uncovered variants are the `Variant gap` lines. `Sub-method gap` lines are plan method questions with no text inside an otherwise documented axis. `Thin` lists documented cells that rest on generic or one-sentence text.
- `gap-method`: anchor column gives only the nearest text that falls short; method, observable and cases stay `gap`.
- Binding: a script that takes detector observations or simulated events. `none; adj X` means X exists but only computes from declared numbers, so it does not implement the cell.
- `stability_monitor.py` accepts any per-period series, so it is bound only in the one row where a family needs it (F03).
- Environment: the `Env` line of each family applies to every row; the cell adds a run environment only where a binding has one. E2 is macOS arm64.
- `source-unverified`: named as the reference names it; the original was not re-read here.
- No axis is `not-applicable` as a whole in these 15 families. Sub-quantities that are excluded, with their reason, are on the `Excluded` lines.
- All families also need 5.5 rows 1 and 7 (container, schema, product role; runtime and evidence). A metadata-versus-schema conflict holds the affected cells until resolved (5.5); it is never settled by majority or LLM confidence. Type recognition does not establish runtime or quality evidence.

Status count: `documented` 90, `gap-method` 15, `not-applicable` 0, total 105.

| Family | documented | gap-method | not-applicable |
|---|---|---|---|
| F02 | 7 | 0 | 0 |
| F03 | 4 | 3 | 0 |
| F06 | 7 | 0 | 0 |
| F07 | 6 | 1 | 0 |
| F08 | 7 | 0 | 0 |
| F10 | 3 | 4 | 0 |
| F11 | 7 | 0 | 0 |
| F16 | 7 | 0 | 0 |
| F17 | 7 | 0 | 0 |
| F18 | 7 | 0 | 0 |
| F19 | 5 | 2 | 0 |
| F20 | 6 | 1 | 0 |
| F22 | 7 | 0 | 0 |
| F25 | 3 | 4 | 0 |
| F32 | 7 | 0 | 0 |

## F02 Semiconductor spectroscopy and segmented detectors (BP01/02/09/10)

Env: low-background and laboratory spectroscopy, offline, event pulses.

Variant gap: CdTe, no text (only hit in the tree is the element table).
Variant gap: CZT, no text.
Variant gap: Si spectroscopy, silicon drift named in one list only (FEW#digital-pulse-processing-for-spectroscopy).
Variant gap: segmented detectors, one sentence, no assumption or failure mode (NOB#pileup-and-position-in-cryogenic-and-germanium-detectors).
Sub-method gap: depth of interaction outside germanium pulse shape; escape and incomplete-energy handling (escape peaks appear only as calibration samples); cross-talk correction (FEE gives size only).
Thin: finding/association and space rest on germanium text only.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | FEW#digital-pulse-processing-for-spectroscopy; `source-unverified`: V. T. Jordanov and G. F. Knoll, Nucl. Instrum. Methods A345 (1994) 337 | digital trapezoid, flat top beyond collection-time spread, per-channel pole-zero | pulse amplitude; ADC | flat top longer than collection spread | wrong decay constant tilts flat top, amplitude depends on sample point | none; adj `frontend_response.py` ballistic, enc | none (adj: test_frontend_response.py Ballistic) |
| finding/association | documented | FEW#digital-pulse-processing-for-spectroscopy; NOB#pileup-and-position-in-cryogenic-and-germanium-detectors | fast parallel channel flags pileup; rejected fraction measured as live-time loss | pileup flag, live fraction; count, 1 | close pulses flagged on fast channel | unmeasured rejection loss taken as rate-independent | none; adj `frontend_response.py` deadtime | none |
| parameter estimation | documented | FEE#signal-induction; NOB#pileup-and-position-in-cryogenic-and-germanium-detectors | amplitude with ballistic-deficit and trapping limits; maximum current over energy | amplitude, A/E ratio; ADC, ratio | small-contact detector, A/E nearly position independent | semi-coaxial: A/E discriminates poorly | none; adj `frontend_response.py` ballistic | none |
| space/time/direction | documented | NOB#pileup-and-position-in-cryogenic-and-germanium-detectors | current pulse shape flags near-contact and slow surface events; segment and transient signals | location class, segment id; categorical | near-contact event flagged by pulse shape | large-contact detector: ratio weak | none | none |
| energy or identifiable quantity | documented | SIG#energy-loss-and-its-fluctuations; TBL#table-1-master-detector-table; `source-unverified`: PDG RPP 2024, particle detectors at accelerators | N = E/W, Fano limit, line scale | deposited energy; keV via calibration line | energy line and its position dependence | escape or incomplete deposit read as full energy (no handling text) | none | none |
| PID/topology | documented | FEW#pulse-shape-discrimination; NOB#pileup-and-position-in-cryogenic-and-germanium-detectors; `source-unverified`: Budjáš et al., J. Instrum. 4 (2009) P10007 | single- versus multi-site from shape variable | site class, shape variable; ratio | double-escape peak as single-site proxy | proxy not uniform in volume; acceptance extrapolated | none | none |
| uncertainty/quality | documented | NOB#pileup-and-position-in-cryogenic-and-germanium-detectors; NOB#rare-event-detectors | cut acceptance from calibration peaks, cross-checked; threshold efficiency | acceptance, leakage vs energy; fraction | two-neutrino continuum cross-check | FOM alone: tails not predicted | none | none |

Signature facts: rep waveform samples per channel or segment; qty amplitude in ADC, energy only after line calibration; acq event, window, rate, dead time; bind sampling clock, per-channel decay constant, contact type, material, segment map, calibration lines; req energy line, site class or location class. BP01 clue samples + clock + window; BP02 clue channel geometry; BP09 clue pulse + operating state; BP10 clue only when multi-site gamma ordering is asked (not covered here, F26).

Applicability: `schema && samples && sampling_clock && signal_window && material_in(Ge, documented-only) && (noise_model || baseline_window)`; energy adds `line_calibration`; location adds `(contact_type_and_shape_model || segment_map)`. Stays unknown: unknown sampling or summaries only, no pulse claim; no line calibration, amplitude stays ADC; unknown contact type, A/E not selected; CdTe, CZT or Si material, method unsupported and recorded as gap, not mapped to germanium.

## F03 Ionization and proportional chambers, MWPC, integrated charge (BP01/02/12)

Env: beam instrumentation, fixed target, event hits or integrated intervals, online and offline.

Variant gap: ionization chambers, no text (the term does not occur).
Variant gap: integrated charge or current readout, no method; TBL#table-9-specialized-and-auxiliary-detectors has only a monitor row.
Sub-method gap: profile output; count versus integrated current; rate nonlinearity and saturation; integration window.
Excluded: per-event tracks as a requirement (plan row); per-particle objects from integrated readout (BP12, plan 6.7: integrated signals are not events).
Thin: parameter estimation rests on text for every gaseous detector, not on chamber-specific text.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | FEE#signal-induction | anode unipolar charge, ion-drift tail removed by tail cancellation | wire charge; ADC | unipolar anode pulse after tail cancellation | neighbour electrode bipolar, zero net charge | none | none |
| finding/association | gap-method | none; nearest GAS#distinctive-but-generalizable-reconstruction-and-performance-features-wirerpc names wire-crossing ghosts only | gap | gap | gap | gap | none | none |
| parameter estimation | documented | SIG#charge-drift-diffusion-gain-losses | gain from Townsend form; pressure and temperature correction; Polya gain spread | gain; 1 | gain corrected for P/T at fixed voltage | uncorrected density change read as signal change | none | none |
| space/time/direction | documented | GAS#mwpcs-straw-tubes-and-rpcs; TBL#table-2-tracking-technology-comparison | wire hit pitch/sqrt(12), or induced cathode charge for second coordinate | hit position; mm | single hit on wire with cathode coordinate | wire crossings give ghosts | none | none |
| energy or identifiable quantity | gap-method | none; nearest FEW#pileup-of-pulses-baseline-and-rate dead-time relations are not chamber text | gap | gap | gap | gap | none; adj `frontend_response.py` deadtime | none |
| PID/topology | gap-method | none | gap | gap | gap | gap | none | none |
| uncertainty/quality | documented | GAS#distinctive-but-generalizable-reconstruction-and-performance-features-wirerpc; GAS#common-misconceptions-and-failure-modes; CAA#monitoring-stability-over-time | plateau scan, efficiency at operating rate; gain series tested for drift and steps | efficiency vs voltage and rate; fraction; gain series | efficiency plateau measured at operating rate | plateau taken as valid across rate | `skills/hep-detector/scripts/stability_monitor.py` (gain series only) | tests/skills/hep_detector/test_stability_monitor.py (generic series, not chamber data) |

Signature facts: rep hit, cluster, waveform, or integrated interval charge or current (must be stated); qty charge versus current versus count, gain state; acq event or interval, integration window, dead time, exposure; bind HV, gas, P, T, wire geometry, channel map; req position, profile, rate. BP01 clue samples + clock; BP02 clue channel + geometry, with binary/analog stated; BP12 clue count or interval + exposure; exclusion: absent treated as zero, per-event energy without energy observation.

Applicability: `schema && channel_map && readout_kind_known && (wire_hit || waveform)` for position; rate or profile output is a gap, so no predicate is authorized. Gain cells add `HV && (P && T || gas_density)`. Stays unknown: readout kind unknown, count and current are not interchangeable; not-read stays distinct from zero (BP12); integration window unknown, no rate claim.

## F06 RPC/MRPC and strip or pad gas timing (BP01/02/07/15)

Env: collider and fixed-target muon and TOF layers, event, online and offline.

Sub-method gap: strip clustering rule for multi-hit (only named as a tail); RPC-specific dead time and rate-dependent time response; MRPC TOF chain beyond the generic TOF text.
Thin: finding/association, parameter estimation and PID rest on generic timing text that lists RPC/MRPC by name.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | FEE#signal-induction; TIM#pulse-time-extraction; `source-unverified`: W. Riegler, NIM A535 (2004) 287 | resistive signal via time-dependent weighting fields; leading edge with walk correction, or CFD | strip time, amplitude or ToT; ns | walk corrected per channel with amplitude | streamers, afterpulses in tails | none; adj `frontend_response.py` timing | none (adj: test_frontend_response.py Timing) |
| finding/association | documented | TIM#time-resolution-budget-single-hit; MUO#reconstruction-chain | track extrapolated to layer, match by position and time; bunch assignment; chi2 match | hit-track link, bunch id; categorical | multiple hits resolved by track match | wrong association gives late or early tail; wrong bunch | none | none |
| parameter estimation | documented | TIM#calibration-and-diagnostics; TBL#table-1-master-detector-table | per-channel t0 and walk from common reference; time residuals | t0, walk curve; ns | residual flat in amplitude | residual vs amplitude shows walk | none | none |
| space/time/direction | documented | TBL#table-2-tracking-technology-comparison; GAS#distinctive-but-generalizable-reconstruction-and-performance-features-drift-systems; MUO#reconstruction-chain | strip pitch position; strip-end time difference reuses offset and velocity logic; segments | position, time; mm, ns | strip-end time difference, calibrated offset | shared clock offset does not average | none | none |
| energy or identifiable quantity | documented | TIM#relations-definition-exact-unless-noted; PID#time-of-flight-tof | beta = L/(c t), m^2; path from track fit | beta, m^2; 1, GeV^2 | path from fit, known start time | start-time error common to all, species-dependent mass shift | none | none |
| PID/topology | documented | PID#time-of-flight-tof; MUO#reconstruction-chain | TOF separation, downward versus upward by sign | species hypothesis, direction sign; categorical | separation inside 1/p^2 ceiling | wrong bunch misread as species | none; adj `pid_separation_power.py` tof | none (adj: test_detector_helpers.py PidSeparationTests) |
| uncertainty/quality | documented | TIM#time-resolution-budget-single-hit; GAS#distinctive-but-generalizable-reconstruction-and-performance-features-wirerpc | budget by term; core width and tail fraction; efficiency vs voltage and rate | sigma_t, tail fraction; ns, fraction | system resolution incl. clock and reference | single-channel value quoted as system; plateau assumed across rate | none | none |

Signature facts: rep strip or pad hit with time, or waveform; qty time in ns with clock basis, position along or across strip; acq event, bunch structure, rate; bind clock, t0, HV, strip geometry, path from tracking, event time; req time, TOF, segment. BP01 clue samples + clock; BP02 clue channel + geometry, 1D strip gives no independent 2D; BP07 clue time + path + momentum, exclusion: missing path or common clock, sensor name cannot select TOF; BP15 clue multiple products + associations.

Applicability: `schema && strip_time && channel_map && clock_known && (t0_calibration)`; TOF adds `path_from_track && (event_time || start_detector || start_plane)`; PID adds `momentum`. Stays unknown: no common clock, no flight time; no path, beta unknown; event time absent, relative times only.

## F07 Gaseous TPC, including continuous and negative-ion (BP01/03/08)

Env: collider and fixed-target, event or continuous, low and high occupancy.

Variant gap: negative-ion TPC, no text (no negative-ion, SF6 or minority-carrier hit); each carrier's drift law and internal carrier-relative distance constraint absent.
Variant gap: continuous readout, generic text only: EVT row for per-interaction t0, and EVT partitioning paragraph (halo, owner), none TPC-specific.
Sub-method gap: pad or wire waveform deconvolution in gas; joint timing constraint (external plus internal).
Thin: finding/association rests on generic tracking text that names TPCs. PID binding is generic: script scope names tracker layers, TPC use is untested.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | gap-method | none; nearest FEW#lar-tpc-signal-processing covers LAr only, GAS#time-projection-chambers-tpc has no waveform method | gap | gap | gap | gap | none | none |
| finding/association | documented | TRK#from-hits-to-tracks-pattern-recognition; TRK#track-finding-strategies; EVT#planning-a-reconstruction-the-method-contract | seed and extend in windows; t0 per track or interaction under pileup or continuous readout | track candidate, interaction t0; link, ns | light, crossing or matched-trigger t0 per track | one trigger t0 on out-of-time tracks; merging at high density | none | none |
| parameter estimation | documented | GAS#time-projection-chambers-tpc; CAS#case-2-tpc-space-charge-distortion | z = v_d (t - t0), diffusion scaling, distortion map from matching, laser or cosmics | v_d, distortion map; mm/ns, mm | rate-parameterized map from reference matching | distortion read as resolution | none; adj `adapters/detector-simulation` garfield.gas-table-query (drift velocity input) | none (adj: VALIDATION DETSIM-W4G, pipeline only) |
| space/time/direction | documented | GAS#time-projection-chambers-tpc; EVT#planning-a-reconstruction-the-method-contract | xy from arrival, z from drift; absolute z only with own t0 | 3D point; mm | track with its own t0 | no own t0: no absolute drift position, charge marked uncorrected | none | none |
| energy or identifiable quantity | documented | GAS#distinctive-but-generalizable-reconstruction-and-performance-features-tpc; TRK#sensor-technologies | momentum from lever arm and B; dE/dx from samples | momentum, dE/dx; GeV/c, charge per length | many samples, field known | start-time error absorbed in track parameters | none | none |
| PID/topology | documented | GAS#time-projection-chambers-tpc; PID#ionization-energy-loss-dedx; SIG#energy-loss-and-its-fluctuations; TBL#table-1-master-detector-table; `source-unverified`: PDG RPP 2024, eq. 35.17 | truncated mean, or cluster counting where single clusters resolve; path, saturation, gain, attachment corrected | truncated dE/dx, cluster number; ratio, count | truncation stated with sample number | clusters merged by rate, diffusion, electronics | `skills/hep-detector/scripts/multisample_pid.py` likelihood (per-layer PDFs) | tests/skills/hep_detector/test_multisample_pid.py, VALIDATION UPGRADE-B (SYNTHETIC, no TPC input) |
| uncertainty/quality | documented | GAS#distinctive-but-generalizable-reconstruction-and-performance-features-tpc; CAS#case-2-tpc-space-charge-distortion | cluster-to-track residuals vs r, z, phi, rate; map uncertainty correlated | residual, map uncertainty; mm | residual flat vs rate after map | z offset of out-of-time tracks; distortion against alignment degeneracy | none | none |

Signature facts: rep waveform, pad or wire cluster, or track candidate; qty charge, drift time, absolute versus relative z; acq event or frame, drift window, halo, interaction multiplicity; bind carrier type, drift law, field, gas, T, P, distortion map, timing source and its scope; req charge image, 3D, dE/dx. BP01 clue samples + clock; BP03 clue measurements or tracks + surfaces + field; BP08 clue drift waveforms + view, carrier, channel map, check alternative timing or distance constraints, exclusion: without localization constraints deliver only identifiable charge and geometry components.

Applicability: `schema && channel_map && (hit_cluster || waveform_with_response) && drift_law_for_carrier && (external_t0 || qualified_internal_t0)`, where `qualified_internal_t0` = light match || cathode or anode crossing || matched trigger per interaction; negative-ion carrier-relative distance is an alternative named by the plan but has no text, so it cannot satisfy this today. Continuous adds `frame_owner && halo`. Stays unknown: t0 unknown for a track, drift coordinate and drift corrections withheld; carrier unknown, no drift law chosen; external t0 is never a prerequisite in itself.

## F08 LArTPC and other liquid charge-imaging TPCs (BP01/03/05/08)

Env: neutrino beam and surface or underground, event or drift-window, offline.

Variant gap: pixel readout, named once only (NOB#neutrino-detectors), no method.
Variant gap: non-argon or other liquid imaging TPCs, no method.
Sub-method gap: track/shower separation as its own stage; missing-plane recovery beyond the channel-map dependence.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | FEW#lar-tpc-signal-processing; FEE#signal-induction | coherent noise removal, 1D or 2D deconvolution of field and electronics response, ROI | deconvolved charge per wire and tick; ADC to e | collection plane, filter trade stated | large-angle track: long low induction signal, charge least reliable | none | none |
| finding/association | documented | NOB#imaging-reconstruction-in-single-phase-lartpcs; `source-unverified`: Acciarri et al., Eur. Phys. J. C 78 (2018) 82; Qian et al., J. Instrum. 13 (2018) P05032 | view matching by drift range, or tomographic 3D cells | 3D cluster or cell; link | clusters matched across planes | constant-drift-time track; ghost cells in dense regions | none | none |
| parameter estimation | documented | NOB#imaging-reconstruction-in-single-phase-lartpcs; CAS#case-8-noble-liquid-electron-lifetime-drift | dQ/dx corrected for lifetime, space charge, channel response | dQ/dx; charge per length | lifetime map per time bin | pitch grows along drift or wire direction | none | none |
| space/time/direction | documented | NOB#imaging-reconstruction-in-single-phase-lartpcs; EVT#planning-a-reconstruction-the-method-contract | t0 from light, spill or tagger; beam-coincident track by light match | 3D position, t0; mm, ns | t0 from light match in spill | no t0: drift coordinate undetermined | none | none |
| energy or identifiable quantity | documented | NOB#imaging-reconstruction-in-single-phase-lartpcs; `source-unverified`: Abratenko et al., J. Instrum. 12 (2017) P10010 | recombination to dE/dx; range; MCS likelihood; shower calorimetry | dE/dx, momentum, shower energy; MeV/cm, MeV | stopping track by range with hypothesis | conversion steep at high charge density | none | none |
| PID/topology | documented | NOB#imaging-reconstruction-in-single-phase-lartpcs | dE/dx vs residual range; first-centimetres dE/dx and vertex gap | species, track or shower; categorical | Bragg peak separates p from mu, pi | reversed track, vertex at wrong end | none | none |
| uncertainty/quality | documented | NOB#imaging-reconstruction-in-single-phase-lartpcs | rates of broken, merged, reversed tracks; control samples | failure rates; fraction | stopping muons, decay electrons, pi0 mass | dead regions break tracks | none | none |

Signature facts: rep wire or pixel waveform, 2D wire-time image, 3D charge; qty charge, drift time, wire or pixel coordinate, view id; acq drift window, ROI retained or not, event, trigger; bind plane geometry, field response, electronics response, channel masks, lifetime, field map, recombination model, t0 source; req charge image, track, shower, dQ/dx to energy. BP01 clue samples + clock; BP03 clue measurements + surfaces; BP05 clue hits + geometry, energy kind; BP08 clue drift waveforms + view map, exclusion: induction bipolar amplitude is not collected charge, signal outside ROI not recoverable.

Applicability: `schema && wire_readout && channel_mask && (field_response && electronics_response) && plane_geometry`; absolute 3D adds `(light_t0 || spill_t0 || external_tagger)`; energy adds `lifetime && recombination_model && local_field`. Stays unknown: no t0, charge and energy uncorrected, no absolute position; missing plane, 3D marked ambiguous; pixel or non-argon readout, method unsupported and recorded as gap; only ROI retained, later recovery refused.

## F10 Single-phase noble-liquid scintillation and optical readout (BP01/06/07)

Env: low-background underground, event, low occupancy, offline.

Variant gap: light-only device class, not in the scope list of PHO; no light-only position or energy text.
Sub-method gap: surface versus bulk; optical-condition changes.
Excluded: drift coordinates, no charge signal (plan row; NOB ties drift position to charge arrival).

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | FEW#pulse-shape-discrimination; NOB#noble-liquid-tpcs; `source-unverified`: PDG RPP 2025, sec. 36, noble liquids | shape variable from digitized waveform: prompt or tail over total | prompt fraction; ratio | window aligned to pulse start, sampling resolves prompt part | baseline or window error shifts variable; saturation of large pulses | none | none |
| finding/association | gap-method | none; nearest NOB#noble-liquid-tpcs pulse finding is TPC text | gap | gap | gap | gap | none | none |
| parameter estimation | gap-method | none; nearest PHO#the-expected-light-model covers dual-phase top array | gap | gap | gap | gap | none | none |
| space/time/direction | gap-method | none; nearest PHO#the-expected-light-model as above | gap | gap | gap | gap | none | none |
| energy or identifiable quantity | gap-method | none; nearest SIG#light-scintillation-wavelength-shifting-attenuation gives quenching, no estimator | gap | gap | gap | gap | none | none |
| PID/topology | documented | FEW#pulse-shape-discrimination; NOB#noble-liquid-tpcs | prompt fraction separates recoil types in argon | recoil class; categorical | argon singlet and triplet times well apart | xenon times too close for the same power | none | none |
| uncertainty/quality | documented | FEW#pulse-shape-discrimination; NOB#rare-event-detectors | FOM and measured leakage at stated acceptance, in energy bins | leakage, acceptance; fraction | leakage measured on tagged data | FOM extrapolated to tails; leakage extrapolated below calibrated energy | none | none |

Signature facts: rep photosensor waveform, charge, time per channel; qty photoelectrons, prompt fraction, no drift time; acq event, window, trigger, exposure; bind medium, wavelength shifter, sensor map, live mask, optical model, sampling; req pulse, PSD, position, light energy. BP01 clue samples + clock + window; BP06 clue sensor charge or time, check live/dead/unhit and light model, exclusion: no complete-likelihood claim without unhit semantics; BP07 clue only where a photon or time observable feeds PID.

Applicability: `schema && samples && sampling_clock && baseline_method && medium_known` for PSD; position, energy and finding have no authorized method. Stays unknown: medium unknown, PSD power not assumed; no live mask, unhit not inferred; no charge channel, drift coordinate stays absent rather than estimated.

## F11 Plastic, liquid, crystal scintillator counters, bars, fibres (BP01/02/07/12)

Env: collider, fixed-target, space or balloon; event, online and offline. simreco applies to simulated element_sim events only.

Variant gap: liquid scintillator counters, no text (large-volume text is F22).
Variant gap: crystal scintillator counters, no text in skills (NaI, CsI, BGO, LYSO: no hit; atlas facts only).
Sub-method gap: count or rate delivery (BP12); per-bar attenuation fit as a tool.
Thin: signal extraction is generic scintillation plus timing text.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | SIG#light-scintillation-wavelength-shifting-attenuation; TIM#pulse-time-extraction; FEW#photosensor-readout | light yield with quenching, attenuation; CFD or template time; measured SiPM curve | amplitude, time; photoelectrons, ns | saturation corrected by measured curve | saturation assumed linear; attenuation constant | none; adj `frontend_response.py` sipm, timing | none (adj: test_frontend_response.py SiPM, Timing) |
| finding/association | documented | GAS#fibre-tracker-reconstruction; `source-unverified`: Aiola et al., Comput. Phys. Commun. 260 (2021) 107713 | amplitude-weighted clusters; ghosts by third view, stereo consistency, hit time | cluster, link; mm | third view removes stereo ghost | ghost rate unmeasured; cross-talk clusters | none | none |
| parameter estimation | documented | GAS#fibre-tracker-reconstruction; SIG#light-scintillation-wavelength-shifting-attenuation | attenuation and propagation corrected from coordinate along fibre, fit iterated | corrected amplitude, time; photoelectrons, ns | coordinate from stereo layers | endpoint positions; attenuation drift | none | none |
| space/time/direction | documented | TIM#technologies; GAS#fibre-tracker-reconstruction; PID#time-of-flight-tof | two-end time difference; centroid; sign of time difference gives direction | position, time, up or down; mm, ns | double-ended bar | one view gives no position along the fibre | `adapters/geant4/assets/simreco/simreco.cc` via `geant4_run.py reco` (TOF station times, declared Gaussian width; E2) | VALIDATION GEANT4-J15 TOF (B3.5), SYNTHETIC; tests/adapters/test_simreco.py |
| energy or identifiable quantity | documented | TIM#relations-definition-exact-unless-noted; PID#time-of-flight-tof | beta = L/(c t), path from fit; amplitude as deposit proxy after corrections | beta; 1 | fitted arc path | straight path at low momentum biases beta | simreco as above (beta) | VALIDATION GEANT4-J15, SYNTHETIC closure on invented layout |
| PID/topology | documented | PID#time-of-flight-tof; FEW#pulse-shape-discrimination | TOF species; PSD for n-gamma | species, shape class; categorical | separation inside 1/p^2 ceiling | walk calibrated on Z=1 applied to nuclei | none; adj `pid_separation_power.py` tof | none (adj: test_detector_helpers.py PidSeparationTests) |
| uncertainty/quality | documented | TIM#time-resolution-budget-single-hit; GAS#fibre-tracker-reconstruction | budget by term; core and tail; ghost rate | sigma_t, ghost rate; ns, fraction | sqrt(2) sigma_t on two-layer residual | single-channel value quoted as system | simreco as above (layer residual) | VALIDATION GEANT4-J15, SYNTHETIC; no real detector |

Signature facts: rep pulse amplitude and time, waveform, or fibre channel amplitude; qty photoelectrons, time, coordinate along bar; acq event, trigger, rate; bind clock, channel map, attenuation, effective speed, stereo geometry, sensor type, medium; req TOF, position, PSD, count. BP01 clue samples + clock; BP02 clue channel + geometry; BP07 clue time + path + momentum; BP12 clue count + exposure.

Applicability: `schema && channel_map && (pulse_time || waveform) && sensor_response`; position adds `(double_ended_readout || stereo_views)`; TOF adds `clock && path_from_track && event_time`; PSD adds `samples && medium_supports_psd`. Stays unknown: single view, coordinate along fibre unknown; no path, beta unknown; liquid or crystal medium, recorded as gap. simreco is selectable only for element_sim output.

## F16 Sampling and imaging ECAL (BP01/02/05)

Env: collider, fixed-target, space; event, offline. simreco and layered_sim: simulated events only.

Variant gap: Si active medium, no variant text.
Variant gap: scintillator active medium, no variant text.
Variant gap: LAr active medium, TBL#table-5-ecal--hcal-technology-comparison row and one FEW example only.
Sub-method gap: per-layer reconstruction with inactive layer; shower finding as a tool.
Thin: signal extraction is generic calorimeter text.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | FEW#amplitude-and-time-from-sampled-waveforms; EVT#digitization-boundary-and-calibration; `source-unverified`: M. Aharrouche et al., arXiv:0709.1094 | optimal filter with phase locked, R includes pileup | cell amplitude, time; ADC, ns | stale-free weights at stated pileup | phase error biases amplitude | none; adj `frontend_response.py` optimal-filter | none (adj: VALIDATION FRONTEND-RECO-SIM, synthetic) |
| finding/association | documented | EVT#clustering | fixed windows or topological growth; splitting | cluster; cells | thresholds stated and stable across periods | two particles merge, summed energy, mid position | none (simreco has no clustering) | none |
| parameter estimation | documented | CAL#shower-position-direction-and-shape; `source-unverified`: Awes et al., Nucl. Instrum. Methods A 311 (1992) 130 | S-curve or log weights, stated depth | centroid; mm | position quoted at stated depth | raw centroid pulled to cell centre | none | none |
| space/time/direction | documented | CAL#shower-position-direction-and-shape | line through per-layer centroids | shower axis; rad | fit uses layers around and after shower start | early fluctuations, back-scatter bias | none | none |
| energy or identifiable quantity | documented | CAL#homogeneous-versus-sampling-calorimeters; CAL#leakage-dead-material-and-containment; `source-unverified`: PDG RPP 2025, sec. 34.5 | active deposit over sampling fraction; leakage and dead-material corrections in energy and angle | deposited or incident energy, stated kind; MeV | sampling fraction stated per shower kind | one global correction; EM sampling fraction applied to hadrons | simreco (active deposit over sampling fraction; E2); `adapters/geant4/assets/layered_sim` (simulation only) | VALIDATION GEANT4-J15 (SYNTHETIC; containment refused); GEANT4-FOCAL (simulation profile, not reconstruction) |
| PID/topology | documented | CAL#shower-position-direction-and-shape; CAL#calorimeter-based-identification | shape variables; E/p; data control samples | shape discriminant, E/p; ratio | rejection measured on tagged data | simulated hadronic tails trusted | `skills/hep-detector/scripts/multisample_pid.py` likelihood (calorimeter samplings) | tests/skills/hep_detector/test_multisample_pid.py, VALIDATION UPGRADE-B (SYNTHETIC, no calorimeter input) |
| uncertainty/quality | documented | CAL#the-resolution-decomposition; CAL#shower-position-direction-and-shape | three-term resolution, per-event error, pulls | sigma_E/E; fraction | three distinct energies, covariance quoted | stochastic term extrapolated alone | none; adj `calorimeter_resolution.py` | none (adj: test_detector_helpers.py CalorimeterResolutionTests) |

Signature facts: rep cells, hits or waveforms per layer; qty deposited energy kind, depth, layer index; acq event, threshold, zero suppression; bind sampling geometry, sampling fraction, absorber, active medium, dead material, calibration, masks; req energy, direction, shape. BP01 clue samples + clock; BP02 clue channel + geometry; BP05 clue cells + thresholds + geometry, exclusion: analog sums without digital response, old-selection IRFs.

Applicability: `schema && cell_geometry && calibration && layer_map && (sampling_fraction_for_particle_kind)`; direction adds `longitudinal_segmentation`; energy claim adds `(containment_model || leakage_correction)`. Stays unknown: sampling fraction unknown, energy stays active deposit; energy kind unknown, deposited is not substituted for incident (BP05); active medium Si or scintillator, generic text only, marked restricted.

## F17 HCAL, compensating, dual-readout, digital and semi-digital (BP01/05/15)

Env: collider, test beam, event, offline.

Variant gap: digital and semi-digital, TBL#table-5-ecal--hcal-technology-comparison row only: no hit-count-to-energy method, no saturation handling.
Variant gap: dual readout, one CAL sentence plus one table row; no joint treatment of the two responses and their correlation.
Sub-method gap: particle-flow association specific to hadronic showers; multiple thresholds.
Thin: signal extraction and space are generic or EM-led calorimeter text; `f_em` weighting is stated at principle level.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | EVT#digitization-boundary-and-calibration; FEW#amplitude-and-time-from-sampled-waveforms | estimator from samples, weights as conditions | cell amplitude; ADC | analog cell, weights per pileup level | threshold occupancy treated as analog energy (BP05) | none; adj `frontend_response.py` optimal-filter | none (adj: VALIDATION FRONTEND-RECO-SIM, synthetic) |
| finding/association | documented | EVT#clustering; EVT#track-cluster-association-and-particle-flow-reconstruction | topological clusters; track-cluster link, subtraction | cluster, link; cells | single hadron linked to track | over- or under-subtraction; double counting | none | none |
| parameter estimation | documented | CAL#hadronic-showers-and-non-compensation | offline weighting estimates f_em from shower density | f_em, weights; 1 | correction with stated non-linearity | single-hadron calibration taken as jet calibration | none | none |
| space/time/direction | documented | CAL#shower-position-direction-and-shape | energy-weighted centroid; layer axis when segmented | position, axis; mm, rad | longitudinally segmented device | irregular hadronic shape | none | none |
| energy or identifiable quantity | documented | CAL#hadronic-showers-and-non-compensation; EVT#track-cluster-association-and-particle-flow-reconstruction; `source-unverified`: PDG Review of Particle Physics, "Calorimetry"; PDG RPP 2025, sec. 35.10.3 | pi/e response; compensation routes; PF replaces charged deposits by tracks | hadronic energy; GeV, derived and calibrated | non-linearity quantified | invisible energy; e/h = 1 assumed | none | none (example: `examples/design-collider-tracker` records HCAL resolution as unavailable) |
| PID/topology | documented | CAL#calorimeter-based-identification; CAL#shower-position-direction-and-shape | E/p; shape; later hadronic start | shape, E/p; ratio | control region validation first | weak contrast in low-Z media | none | none |
| uncertainty/quality | documented | CAL#the-resolution-decomposition; CAL#hadronic-showers-and-non-compensation | three-term fit, non-Gaussian tails stated | sigma_E/E, tails; fraction | range and covariance quoted | Gaussian understates tails | none; adj `calorimeter_resolution.py` | none (adj: test_detector_helpers.py CalorimeterResolutionTests) |

Signature facts: rep analog cells, waveforms, or binary or multi-threshold cells (must be stated); qty energy kind, or hit count, never interchanged; acq event, thresholds, integration time; bind e/h or compensation state, absorber, active medium, both channels for dual readout, tracking link, counting policy; req hadronic energy, PF input. BP01 clue samples + clock; BP05 clue cells + thresholds + geometry, check analog/digital; BP15 clue multiple products + associations, check shared geometry, clock, counting policy, exclusion: fusion claimed because two files are readable.

Applicability: `schema && cell_geometry && calibration && readout_kind_known && analog_cells`; hadronic scale adds `(compensation_state || offline_weighting)`; PF adds `track_cluster_links && counting_policy`. Digital or dual readout: no authorized method. Stays unknown: readout kind unknown, count is not energy; one dual-readout channel missing, no EM-fraction correction; no counting policy, no summed PF energy.

## F18 Nuclear emulsion, passive track detectors, optical scanning (BP02/03/04)

Env: passive exposure, offline scanning, hybrid or standalone, no event clock.

Variant gap: passive track detectors and etch-pit readout, no text; the reference does not list them as unsupported, which the plan row requires.
Variant gap: other optical-scanning track imaging media, no text.
Excluded: event time, integrating medium with no time axis (GAS#nuclear-emulsions); time only by import from electronic detectors.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | GAS#emulsion-reconstruction | tomographic images at focal depths, grains aligned | grain positions; um | aligned grains form microtrack | fog grains form fake microtracks | none | none |
| finding/association | documented | GAS#emulsion-reconstruction; `source-unverified`: Arrabito et al., J. Instrum. 2 (2007) P05004 | microtrack, base-track, film-to-film links in position and slope | base-track, volume track; link | passing track linked across films | allowing a missing film raises fake links | none | none |
| parameter estimation | documented | GAS#emulsion-reconstruction | shrinkage factor; affine alignment per film | slope, transform; rad, um | shrinkage from base-tracks | deformation left in slopes | none | none |
| space/time/direction | documented | GAS#nuclear-emulsions; GAS#emulsion-reconstruction | position and slope; time imported only | position, direction; um, rad | event time inherited from electronic detector | any native event time claimed | none | none |
| energy or identifiable quantity | documented | GAS#emulsion-reconstruction; `source-unverified`: De Serio et al., Nucl. Instrum. Methods A 512 (2003) 539 | MCS, angular or coordinate method | p beta; GeV/c | thickness in X0 known, several films | saturates at high momentum; measures p beta, not p | none | none |
| PID/topology | documented | GAS#emulsion-reconstruction | vertex by track convergence; kinks, secondary vertices | vertex, kink; topology | tracks converge in impact-parameter cut | high density overlap | none | none |
| uncertainty/quality | documented | GAS#emulsion-reconstruction; GAS#nuclear-emulsions | scanning efficiency, fake-link rate on exposed background, vertex-location efficiency | fractions | fake links measured on background | scan inefficiency near edges; fading | none | none |

Signature facts: rep image stack, grains, microtracks, base-tracks; qty position, slope, film index, no time; acq exposure interval, scan, integration; bind medium, film stack, shrinkage, alignment, scanner; req links, vertex, momentum. BP02 clue image features + local coordinates, exclusion: claiming unmeasured event times; BP03 clue measurements or tracks; BP04 clue tracks with state and error, exclusion: known assignment is not finding.

Applicability: `schema && medium_is_emulsion && (image_stack || microtracks || basetracks) && film_geometry && (alignment || through_tracks)`; momentum adds `X0_per_cell`; event association adds `external_electronic_time`. Stays unknown: medium unknown, no response assumed; passive plastic or etch-pit, recorded unsupported; no electronic detector, event time stays absent.

## F19 Thermal bolometers and TES, NTD, MMC microcalorimetry (BP01/09)

Env: cryogenic, low background, event pulses or continuous stream, offline.

Variant gap: MMC, no text.
Variant gap: NTD, one thermistor contrast only.
Variant gap: TES as microcalorimeter, named only as phonon sensor (F20 context).
Sub-method gap: noise PSD, nonstationarity, heater or gain stabilization, readout crosstalk, thermal nonlinear shape.
Excluded: position from the later thermal signal (NOB: it gives none).
Thin: signal extraction is generic filter text linked from the cryogenic section.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | FEW#amplitude-and-time-from-sampled-waveforms; NOB#pileup-and-position-in-cryogenic-and-germanium-detectors; `source-unverified`: Cleland and Stern | optimal filter, template; known shape, phase, stationary noise | pulse amplitude; ADC | same shape, different amplitude | template stale, pulse shape changes with temperature | none (`frontend_response.py` optimal-filter has fixed CR-(RC)^n pulse, no thermal template) | none |
| finding/association | documented | NOB#pileup-and-position-in-cryogenic-and-germanium-detectors; `source-unverified`: Chernyak et al., Eur. Phys. J. C 74 (2014) 2913 | pileup search: template residual, rising edge tests, two-pulse fit | pileup flag; categorical | superposed measured pulses at known separation | close pair merges inside resolving time | none | none |
| parameter estimation | documented | NOB#pileup-and-position-in-cryogenic-and-germanium-detectors; NOB#rare-event-detectors | amplitude; goodness of fit; rejection vs separation | amplitude, fit quality; ADC | rejection measured, not assumed | noise triggers near threshold | none | none |
| space/time/direction | gap-method | none; nearest FEW#amplitude-and-time-from-sampled-waveforms is not stated for thermal pulses | gap | gap | gap | gap | none | none |
| energy or identifiable quantity | documented | SIG#charge-drift-diffusion-gain-losses; NOB#rare-event-detectors; FEW#digital-pulse-processing-for-spectroscopy | Delta T = E/C; amplitude to energy; lines | energy; keV via line | calibration line scale | detector-to-detector variation | none | none |
| PID/topology | gap-method | none; nearest NOB#rare-event-detectors needs a second channel, which is F20 | gap | gap | gap | gap | none | none |
| uncertainty/quality | documented | NOB#rare-event-detectors; NOB#distinctive-but-generalizable-reconstruction-and-performance-features-rare-event | threshold efficiency; line closure; pileup rejection | epsilon(E), resolving time; fraction, time | epsilon(E) from calibration or pulse simulation | low-energy noise excess | none | none |

Signature facts: rep waveform or triggered pulse; qty amplitude, energy only by line; acq continuous or triggered, resolving time, exposure; bind thermal state, sensor type, template, noise covariance, stabilization, line sources; req energy, low threshold. BP01 clue samples + clock + window, exclusion: outside template domain; BP09 clue pulse + operating state, thermal variant; TES, NTD, MMC do not share a model.

Applicability: `schema && samples && sampling_clock && sensor_type && (template && noise_covariance) && operating_state`; energy adds `line_calibration`. Stays unknown: nonstationary state or shape change, template not valid, restricted delivery; MMC, method gap; sensor type unknown, no shared noise or energy model; no second channel, recoil type stays unknown.

## F20 Cryogenic multisignal recoil devices (BP01/09/15)

Env: cryogenic, low background, event, offline.

Variant gap: phonon plus scintillation light devices, light channel appears for pileup only.
Sub-method gap: channel covariance; energy combination; restricted energy estimate when a signal is missing; cross-channel association; bias dependence.
Thin: finding/association covers pileup, not cross-channel pairing; energy text covers amplitude and yield, not combination.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | NOB#rare-event-detectors; FEW#amplitude-and-time-from-sampled-waveforms | per-channel pulse amplitude by filter or template | amplitude per channel; ADC | known-shape channel | low-energy noise events in shape | none | none |
| finding/association | documented | NOB#pileup-and-position-in-cryogenic-and-germanium-detectors; `source-unverified`: Chernyak et al., Eur. Phys. J. C 74 (2014) 2913 | pileup on heat and on faster channel | pileup flag; categorical | faster channel resolves pair | correlated noise between channels (no text) | none | none |
| parameter estimation | gap-method | none; nearest FEW#amplitude-and-time-from-sampled-waveforms is single channel | gap | gap | gap | gap | none | none |
| space/time/direction | documented | NOB#pileup-and-position-in-cryogenic-and-germanium-detectors; `source-unverified`: Broniatowski et al., Nucl. Instrum. Methods A 559 (2006) 378 | athermal phonon partition and delay; surface electrodes | position, fiducial class; categorical | surface event charge on one side only | charge resolution degrades cut near threshold | none | none |
| energy or identifiable quantity | documented | NOB#rare-event-detectors; RAR#energy-scale-and-quenching | amplitude to energy; yield model, keVee vs keVnr | energy; keVee or keVnr | scale stated, model named | ee applied to nuclear recoils; combination absent | none | none |
| PID/topology | documented | NOB#rare-event-detectors; SIG#charge-drift-diffusion-gain-losses | ratio of ionization or light to heat | recoil class; ratio | leakage measured with sources | leakage extrapolated below calibration | none | none |
| uncertainty/quality | documented | NOB#pileup-and-position-in-cryogenic-and-germanium-detectors; NOB#rare-event-detectors | fiducial fraction vs energy from uniform events; leakage | fiducial efficiency, leakage; fraction | activation lines uniform in bulk | fiducial uncertainty ignored | none | none |

Signature facts: rep waveforms on phonon, charge or light channels; qty amplitude per channel, yield ratio; acq event, shared trigger, shared clock; bind sensor layout, electrode layout, bias, channel map, line and neutron calibrations; req energy, position, recoil type. BP01 clue samples + clock; BP09 clue pulse + state; BP15 clue multiple channels + associations, shared clock and nuisances.

Applicability: `schema && samples && sampling_clock && channel_map && shared_event_key && (phonon && (ionization || light))`; position adds `(multi_athermal_sensors || interleaved_electrodes)`; PID adds `both_channels_present && yield_calibration`. Stays unknown: one channel missing, recoil type unknown and energy restricted (method gap, so no combined value); noise covariance unknown, channels not assumed independent.

## F22 Large-volume water Cherenkov, LS, WbLS, hybrid optical (BP01/06/07)

Env: large media, underground, event plus delayed subevents, offline.

Variant gap: WbLS, no text.
Variant gap: hybrid optical detectors, no text; Cherenkov and scintillation components appear only as an emission-profile bullet and an LS energy clause.
Sub-method gap: component separation for energy and direction.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | PHO#the-per-channel-likelihood | Poisson plus dark noise, folded with SPE; saturated channels censored | charge, time per channel; pe, ns | live unhit channels kept | saturated value used as measured | none | none |
| finding/association | documented | PHO#seeding-and-the-fit-sequence; PHO#topologies-and-hypothesis-comparison | cleaning, splitting; delayed subevent search | hit set, subevent; link | time density matches cleaned hits | merged events | none | none |
| parameter estimation | documented | PHO#the-per-channel-likelihood; PHO#the-expected-light-model; `source-unverified`: Ahrens et al., Nucl. Instrum. Methods A 524 (2004) 169 | all-channel likelihood, first-photon density; analytic, table or data map | x, theta; mixed | f_1 with total mu | single-photon density on bright channels | none | none |
| space/time/direction | documented | PHO#seeding-and-the-fit-sequence; NOB#water-cherenkov-and-liquid-scintillator-detectors | multistart fit of vertex, time, direction | vertex, direction; mm, ns, rad | mirrored starts recorded | reflected vertex; LS isotropic light weak on direction | none | none |
| energy or identifiable quantity | documented | PHO#energy; `source-unverified`: Aartsen et al., J. Instrum. 9 (2014) P03009 | expected light fit; LS non-linearity and non-uniformity; muon estimators | visible energy; MeV, stated kind | gamma-to-electron model with beta spectra | raw charge sum as energy | none | none |
| PID/topology | documented | PHO#topologies-and-hypothesis-comparison; `source-unverified`: Jiang et al., Prog. Theor. Exp. Phys. 2019 (2019) 053F01 | per-hypothesis fits; rings added within likelihood | ring count, species; categorical | sharp muon against diffuse electron ring | score favours more parameters (BP06) | none | none |
| uncertainty/quality | documented | PHO#per-event-uncertainty-and-quality; PHO#validation-specific-to-this-method-class | likelihood scan or resampling; pulls in energy, topology; control samples | direction error, pulls; rad, 1 | Michel, stopping muons, pi0 | Hessian trusted for few photons | none | none |

Signature facts: rep per-sensor charge, count, time, or traces; qty pe, ns, first-time or pulse series (must be stated); acq event, cleaning already applied or not, trigger; bind live and dead mask, threshold, dark rate, optical model, medium, timing offsets, geometry; req vertex, direction, energy, topology. BP01 clue samples or charge; BP06 clue sensor charge/time, check live/dead/unhit, first-time or series, exclusion: no complete-likelihood claim without unhit semantics or time models; BP07 clue photon observables for PID.

Applicability: `schema && sensor_geometry && live_mask && threshold_model && (analytic_light_model || tabulated_light_model || data_map) && (first_time_model || pulse_series_model)`; medium is water or LS for documented use. Stays unknown: no live mask, unhit not inferred and complete likelihood not claimed; cleaning unknown, time density not selected; WbLS or hybrid medium, recorded as gap.

## F25 Neutron capture, recoil, capture-gated, TOF (BP01/07/12)

Env: reactor or neutron beam, low background; event or prompt-delayed; offline.

Variant gap: He-3, B, Li conversion, no text.
Variant gap: moderation and capture detectors, no text.
Variant gap: capture-gated association, one PHO bullet, no method.
Variant gap: neutron TOF and flight-path spectrum, TBL#table-9-specialized-and-auxiliary-detectors row only.
Variant gap: recoil detectors, no method beyond n-gamma PSD.
Sub-method gap: accidental rate, multiple partners, window truncation (BP12); direction.
Note: `skills/hep-detector/examples/02-geant4-adversarial-audit.md` is an invented audit example, not a run.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | FEW#pulse-shape-discrimination | tail or prompt charge over total from waveform | shape variable; ratio | digitization chain simulated or tagged data used | baseline or saturation shifts variable | none | none |
| finding/association | gap-method | none; nearest PHO#topologies-and-hypothesis-comparison delayed bullet | gap | gap | gap | gap | none | none |
| parameter estimation | gap-method | none | gap | gap | gap | gap | none | none |
| space/time/direction | gap-method | none | gap | gap | gap | gap | none | none |
| energy or identifiable quantity | gap-method | none; nearest TBL#table-9-specialized-and-auxiliary-detectors row | gap | gap | gap | gap | none | none |
| PID/topology | documented | FEW#pulse-shape-discrimination | n-gamma separation by shape variable | n or gamma class; categorical | leakage quoted at stated acceptance | gamma contamination in non-Gaussian tails | none | none |
| uncertainty/quality | documented | FEW#pulse-shape-discrimination | FOM with assumption stated, measured leakage in energy bins | FOM, leakage; 1, fraction | FOM falling toward low energy | FOM used to predict tails | none | none |

Signature facts: rep waveform, event pairs, or counts with windows; qty shape variable, delay, count, flight time; acq exposure, windows, dead time, shared exposure; bind converter, moderator, flight path, medium, quenching, clock; req count, spectrum, position, direction when identifiable. BP01 clue samples + clock; BP07 clue time + path, exclusion: missing path or common clock; BP12 clue count, interval, prompt-delayed, check coincidence, deadtime, exclusion: per-event energy without energy observations.

Applicability: `schema && samples && sampling_clock && baseline_method && medium_supports_psd` for PSD only. Prompt-delayed, energy, position, direction: no authorized method. Stays unknown: flight path unknown, no TOF energy; converter unknown, no capture response; absent partner is not zero (BP12).

## F32 Radio air-shower and neutrino antennas, coherent field arrays (BP01/11/13)

Env: ground-based atmosphere array, event, external or self trigger, offline.

Variant gap: neutrino antennas in dense media, Askaryan emission named once (GBA#muon-detectors-radio-detection-and-wide-field-gamma-ray-arrays), no reconstruction.
Variant gap: coherent field arrays beyond air-shower antennas, no text; links to F35 are not counted here.
Sub-method gap: ray paths, multipath, group delay, medium refraction; beamforming is one clause.

| Axis | Status | Reference anchor | Method | Observable/port | Positive | Negative | Binding/env | Run evidence |
|---|---|---|---|---|---|---|---|---|
| signal extraction | documented | GBA#radio-reconstruction; `source-unverified`: Huege, Phys. Rep. 620 (2016) 1 | unfold vector effective length, chain gain and phase; field and direction iterated | band-limited field; V/m, band stated | band part of every amplitude | transmitter removal also removes signal power | none | none |
| finding/association | documented | GBA#radio-reconstruction | external trigger window, or self-trigger coincidences with front, polarization, direction tests | pulse candidate; categorical | front at about speed of light | impulsive noise; false pulses near threshold | none | none |
| parameter estimation | documented | GBA#radio-reconstruction | fluence in window, noise fluence subtracted | energy fluence; energy per area | noise from outside window | interference term ignored | none | none |
| space/time/direction | documented | GBA#radio-reconstruction | plane then hyperbolic front; beamforming alternative; core in shower-plane coordinates | direction, core; rad, m | antenna times fit | few antennas: degenerate core | none | none |
| energy or identifiable quantity | documented | GBA#radio-reconstruction; `source-unverified`: Glaser et al., J. Cosmol. Astropart. Phys. 09 (2016) 024 | radiation energy, sin alpha and density corrections, EM energy only | EM energy proxy; GeV basis | scale tied to calibration or second detector | shower near field direction: poor | none | none |
| PID/topology | documented | GBA#radio-reconstruction; `source-unverified`: Buitink et al., Phys. Rev. D 90 (2014) 082003 | footprint compared with simulated X_max set, or parametric | X_max proxy; g/cm^2 | density profile listed | muon content needs particle detector | none | none |
| uncertainty/quality | documented | GBA#radio-reconstruction | per-antenna noise, pulls, independent energy or X_max | per-event error, pulls | common-event comparison | antenna pattern is leading scale systematic | none | none |

Signature facts: rep antenna traces, polarization channels; qty voltage, field, band, phase basis; acq trigger kind, window, sampling; bind antenna pattern, gain and phase chain, clock, geometry, geomagnetic field, atmosphere, band; req direction, energy proxy, X_max. BP01 clue samples + clock; BP11 clue antenna observations + geometry/time, exclusion: no equivalent full-chain claim beyond supported domain; BP13 clue only for frequency coordinates and band semantics.

Applicability: `schema && samples && sampling_clock && antenna_geometry && antenna_response && band && (external_trigger || self_trigger_rules)`; energy adds `(absolute_calibration || second_detector_scale)`; X_max adds `atmospheric_density_profile`. Stays unknown: antenna response unknown, voltage only; clock unknown, no front fit; dense medium or coherent field array, recorded as gap.

## Inventory check (coverage.md)

Anchors cited for these 15 rows resolve. Corrections:

1. F17: "Digital and semi-digital: absent (searched ... semi-digital)" is wrong. TBL#table-5-ecal--hcal-technology-comparison has a Digital / semi-digital / imaging row and a Dual readout row. Still no method, so the gap stands.
2. F06: "RPC time walk, wrong bunch ... no method text" is too strong. TIM lists RPC/MRPC and gives walk, multi-hit association and bunch assignment, with transfer to every timed detector; GAS gives strip-end time difference. Only strip clustering and RPC dead time remain.
3. F07: "Cluster counting named, no method" is wrong: SIG#energy-loss-and-its-fluctuations has a paragraph with its limits.
4. F07: "Continuous readout: only the t0 row" misses the EVT partitioning paragraph (halo, owner). It is generic. "External t0 is not stated as optional": the EVT row lists light match and crossings, for TPCs in general; the negative-ion constraint remains absent.
5. F03: "gain drift: no method text" is too strong: SIG gives P/T correction for every gaseous detector, and `stability_monitor.py` tests gain series.
6. F02: "cross-talk: no method text" is partly wrong: FEE gives size and trapping on neighbours, but no correction.
7. Tool column: `multisample_pid.py` scope names tracker layers and calorimeter samplings, so F07 and F16 PID have a generic binding the inventory omits. Untested on those inputs.

# Part 3: families with no plugin text, from sources read

119 cells: 83 `sourced`, 32 `gap-method`, 4 `not-applicable`. `sourced` means a paper was read for this cell. Variants with their own tables: F21 (SNSPD, KID), F35, F37.

Written from the papers read on 2026-11-06 and plan v9.2 (6.4, 6.5, 6.6, 5.15, 7.1.1, BP09, BP10, BP12). Nothing was run. Source records are in t11-sources-a.json.

Result: 49 cells, 44 `sourced`, 4 `gap-method`, 1 `not-applicable`. F21 has two tables (SNSPD, KID/MKID), because BP09 forbids a shared noise or energy model and one energy cell could not carry both statuses.

Conventions:

- `sourced` means text read gives this method for this axis, within the stated scope. It is scoped to the experiment or device named, never to the whole family. The variant gaps say what stays uncovered.
- Binding: `none` everywhere. A word search of `adapters/` in the baseline tree found no adapter for these devices.
- Run evidence: `none` everywhere. Positive and negative cases are design cases taken from the paper or the plan; none has been run here.
- Numbers are as printed in the source. Figures were not viewed: captions only.
- Predicates use `&&`, `||`. Each term is a fact to establish per product; a term not established stays unknown (5.5). Predicates are Inferred from the cited sources, scope as stated.
- Source sections are named by title where the LaTeX source has no numbers.

## F21a SNSPD

E: laboratory infrared photon counting. Only one review read, Natarajan et al. Particle-detector use is not covered.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 1204.5560 sec 2.2.1, 2.2.2, 1.2 | DC bias just below Ic; hotspot forms resistive barrier; voltage pulse across load; Lk and Rn(t) circuit model | voltage pulse, then one count | pulse with rise tau1 and recovery tau2 as in the model | stray light or electrical noise mimics a pulse (dark count) | none | none |
| Finding/association | gap-method | 1204.5560 sec 3.1, 2.2.4 (reviewed, no method) | names TCSPC and coincidences only; assumes electronics register every pulse; no discriminator or window method | none | none | none | none | none |
| Parameter estimation | sourced | 1204.5560 sec 2.3.6, 1.2. Scope: multi-element devices for photon number | PNR-SNSPD: parallel elements with series resistors, pulse height scales with elements fired; MESNSPD: interleaved elements read separately | photon number n from pulse height; count rate | n elements firing give an n times taller pulse | plain meander used as photon-number device; low-bias multiphoton regime is much less efficient | none | none |
| Space/time/direction | sourced | 1204.5560 sec 2.3.8, Fig. 3(c) caption. Scope: time only | TCSPC with ultrafast laser; Gaussian fit to instrument response; FWHM quoted as jitter | arrival time [ps], jitter FWHM [ps] | known laser arrival time, so jitter is the main timing uncertainty | non-uniform wire gives different hotspot resistances and rise times, broadening jitter | none | none |
| Energy/momentum | not-applicable | 1204.5560 sec 2.2.3 | photon energy is negligible against energy stored in Lk, so energy or photon-number resolution is lost to Joule heating of the hotspot. Scope: the single-wire device reviewed | none; count only | none | energy assigned to a count (plan BP09 forbids it) | none | none |
| PID/topology | gap-method | 1204.5560 (sections read) | nothing read. Polarization dependence (sec 2.3.7) is a response effect, not identification | none | none | none | none | none |
| Uncertainty/quality | sourced | 1204.5560 sec 1.2, 2.2.2, 2.3.4, 2.3.8 | eta_sde = coupling x absorption x registering; DCR versus Ibias; dead time tau ~ tau2; latching check | eta_sde, eta_dde, DCR, jitter, recovery time | DCR rises exponentially as Ibias nears Ic, measured per device | eta_dde reported as eta_sde; tau reduced too far gives a latched state with no detection until bias is lowered | none | none |

## F21b KID/MKID

E: millimetre-wave arrays studied for cosmic-ray response, cryogenic. Scope is two experiments: the Bourrion et al. FPGA board (up to 12 MKIDs) and the Karatsu et al. dark-array cosmic-ray test (about 960 pixels per chip). Neither is a photon-pulse analysis.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 1310.5891 MKID instrumentation, Firmware description | frequency comb, IQ up-conversion; per-tone digital down conversion with CIC+FIR low-pass; amplitude and phase per tone; pre-trigger samples for baseline | I, Q per tone; amplitude; phase; delta f | loop-back single tone with noise floor below -100 dBc | resonances not separated enough for the filter, so crosstalk; DC/DC spikes at multiples of 320 kHz | none | none |
| Finding/association | sourced | 1310.5891 Firmware description; 1901.02387 main text. Scope: cosmic-ray glitches | online: I^2+Q^2 against one threshold per MKID; offline: iterative second-derivative search, 5 sigma, next 3 tau_qp counted as one event | glitch points; event per pixel; multiplicity | large glitches removed first so rms reflects noise only; cross-check method differs by less than 1% in event number | single-pixel events in chip a change strongly with threshold, explained by statistics | none | none |
| Parameter estimation | sourced | 1901.02387 main text | single exponential fit to glitch tails gives tau_qp; dead-time and rate estimators | tau_qp [ms] | glitch shape resolved at about 1.27 kHz sampling | about 20% of MKIDs dropped for overlapping resonances or fit failures | none | none |
| Space/time/direction | sourced | 1310.5891 Performance and results, Fig. 1 caption; 1901.02387 main text. Scope: qualitative | relative arrival of phonon signal across pixels; rough location from KID ID via design frequency encoding | sample time [us]; pixel index | sampling shows time differences, impact near pixels 2 and 6 | KID ID read as position: no beam mapping was done, location is rough | none | none |
| Energy/momentum | sourced | 1310.5891 Introduction, Fig. caption of event traces. Scope: phonon-mediated, thin film, principle only | frequency shift proportional to deposited energy (cited to Swenson et al., not read); pulse amplitude used for spectra | delta f; no calibrated energy shown | delta f proportional to generated quasi-particles | raw amplitude compared across MKIDs: resonance depth and transfer function differ. Energy below 2 Delta is invisible (1901.02387) | none | none |
| PID/topology | sourced | 1901.02387 main text, Fig. 3 caption. Scope: event class, not particle type | multiplicity above 10 pixels taken as cosmic-ray event | multiplicity; event class | normal cosmic-ray events seen by more than 10 pixels at once | chip b isolated events on a few pixels, poorly understood | none | none |
| Uncertainty/quality | sourced | 1901.02387 main text, Table 1; 1310.5891 Electronics requirements | dead-time fraction = glitch points x readout step / time; event rate per pixel; dark NEP and tau_qp as array checks; SNR target | dead-time fraction; rate per pixel; pixel yield | measured chip rate consistent with the expected muon rate | L2 dead time is a scaling, not a measurement; simulated energy carries about 10% uncertainty | none | none |

Variant and condition gaps (F21):

- Other superconducting photon sensors: not covered by any source read.
- MKID photon pulses (single-photon or energy-resolving optical/UV): not covered. Both sources study cosmic-ray glitches.
- MKID energy calibration: no procedure from delta f to energy read; Bourrion defers physical interpretation.
- MKID resonance drift and tracking: not covered.
- MKID pileup: not covered. The 3 tau_qp window is an event-counting rule only.
- MKID operating point and readout power: not covered.
- MKID multiplex response: per-resonator threshold and crosstalk condition only, no channel-mixing correction.
- MKID phase noise model: not covered; rms from the time stream only.
- SNSPD particle (non-photon) detection: not covered.
- SNSPD array multiplexing: RSFQ and amplifier/discriminator named in sec 2.4.3, no method.
- SNSPD pulse discrimination and count-loss correction near dead time: not covered.
- SNSPD spatial readout: not covered.

Signature facts: variant (SNSPD or KID, never inferred from "superconducting"); representation (pulse, count and timestamp; or I/Q, amplitude, phase, delta f per tone); clock and sample rate; trigger threshold per channel; pre-trigger samples; bindings (SNSPD: Ibias, Ic, temperature, recovery time, efficiency type; KID: tone list, resonance frequency, per-resonator transfer function, tau_qp, frequency-to-pixel map). 5.15: BP01 samples/clock/window; BP09 pulse/IQ/count with variant branch; BP12 count, deadtime.

Applicability:

- SNSPD count: `variant_snspd && pulse_or_count_stream && (bias_point_known || operating_state_recorded) && recovery_time_known`; time: `&& timestamps && reference_clock`; photon number: `&& (pnr_device || multi_element_individual_readout)`; energy: never from a single-wire count.
- KID glitch/event: `variant_kid && (iq_samples || phase_time_stream) && sample_rate && tone_to_channel_map && threshold_rule`; delta f or energy proxy: `&& resonance_frequency_known && per_resonator_transfer_function`; position: `&& (beam_map || design_frequency_encoding_declared_as_rough)`.

Stays unknown: energy from counts; photon number from a plain meander; position from KID order without a map; dead time without the glitch list; `eta` type if not stated (sec 1.2 warns reports differ).

Recognition: positive, IQ per tone with a tone list. Negative, a pulse list labelled only "superconducting detector": stays unknown; it does not select any branch.

## F24 Superheated bubble chambers and droplets

E: low-background dark-matter searches. Scope is PICO-60 C3F8 (bubble chamber, optical plus acoustic plus pressure) and PICASSO SBD modules (droplets in polymer, acoustic only). Neither scope transfers to the other without saying so.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 1902.04031 Experimental Method, Data Analysis; physics/0508098 sec 5 | PICO: 340 Hz cameras into ring buffers, entropy of frame differences as bubble trigger; piezo acoustics; fast pressure sensor. PICASSO: piezo waveform on 1 MHz FADC, 15 ms re-trigger rejection, 40-130 kHz filter, time-frequency map, integrated to Q | frames; acoustic waveform; pressure rise; Q | PICASSO Q cut nearly fully efficient at medium and high amplitude | PICASSO filter about 50% efficient close to threshold | none | none |
| Finding/association | sourced | 1902.04031 Data Analysis; physics/0508098 sec 5. Scope: PICO for bubbles | image trigger; multiplicity from pressure rise rate; bubble followed over up to nine frames in 30 ms; near-surface events need both cameras within 30 ms. PICASSO: event if one transducer above threshold, all channels read | bubble count per event; bubble motion in frames (not a particle track) | wall events tagged by motion 10 degrees or more from vertical | near-surface visibility poor, position uncertain without the two-camera requirement | none | none |
| Parameter estimation | sourced | 1902.04031 Bubble Nucleation Threshold, Data Analysis; physics/0508098 sec 2 | threshold from T and P (Seitz); efficiency curves, monotonic piecewise linear, fitted to neutron calibration by MCMC; AP normalised per thermodynamic condition. PICASSO: sigmoid P(Edep, Eth) with fitted alpha | Seitz threshold [keV]; efficiency curve; AP | calibration singles, doubles, triples match simulation with best-fit efficiency | thresholds 1.20, 1.58, 1.81 keV lack comprehensive recoil calibration and are not in the search | none | none |
| Space/time/direction | sourced | 1902.04031 Experimental Method, Data Analysis. Scope: PICO optical. No direction of the incident particle | stereo cameras, sub-pixel position, correction for image shifts, per-camera weight by image quality | bubble position [mm]; frame time | fiducial mass raised after finer position and wall tag | failed LEDs and off-centre images degrade quality, so weights must follow them | none | none |
| Energy/momentum | sourced | 1902.04031 table of conditions, Bubble Nucleation Threshold; physics/0508098 sec 2, 5. Identifiable quantity is threshold only | operating threshold plus efficiency curve; no energy per bubble | threshold [keV]; count above threshold | T and P set threshold, with experimental and theoretical errors | PICASSO amplitude read as energy: it follows droplet size, position, solid angle and transducer response | none | none |
| PID/topology | sourced | 1902.04031 Introduction, Experimental Method, Background estimates, WIMP search Results | AP separates alphas from recoils; multi-bubble events tag neutrons; alpha chain also seen by time signature | AP; bubble multiplicity; event class | acceptance region set before unmasking from calibration | at the three lowest thresholds, gamma-induced recoils are indistinguishable acoustically | none | none |
| Uncertainty/quality | sourced | 1902.04031 Background estimates, WIMP search Results; physics/0508098 sec 5, 8 | live time and efficiency-corrected exposure; background from simulation, calibration and multi-bubble rate; profile likelihood with efficiency surfaces. PICASSO: trigger acceptance from second transducer, times Q acceptance | exposure [kg-day]; efficiency; live time; expected background | live-time fraction tracked per condition; PICASSO acceptance measured per detector | multi-bubble rate above simulation, so background left unconstrained; above about 72 C spontaneous nucleation makes SBDs unstable | none | none |

Variant and condition gaps (F24):

- Droplet detectors with optical readout: not covered. Dosimeter visual counting is only mentioned (physics/0508098 sec 1).
- Droplet localization by piezo: claimed as possible (sec 2 end) and planned (sec 9 end), no method read.
- Droplet multiplicity: not covered.
- Optical-acoustic association: no method; PICO treats them as one event, details deferred to a cited paper not read.
- Overlapping bubbles: not covered.
- Bubble image finding beyond the trigger entropy: cited earlier PICO processing not read.
- Threshold scan as an analysis method: conditions listed, no scan method.
- Gamma response model: PICO says it is under development; only a measured efficiency here.
- Other fluids (CF3I, Freon mixtures) in chambers: named only.

Signature facts: variant (chamber or droplet emulsion); readouts present (cameras, piezo, pressure); frame rate; acoustic sampling and band; T, P per live period; expansion and recompression cycle; live-time record; camera geometry; transducer positions; calibration set per condition. 5.15: BP01 acoustic samples/clock; BP02 image features with geometry; BP12 count/threshold, exposure/deadtime; BP15 only with a common event clock.

Applicability:

- Count: `thermodynamic_state_per_period && live_time && trigger_rule && (optical_frames || acoustic_waveform || pressure_trace)`.
- Threshold-identifiable result: `&& fluid_properties && recoil_efficiency_calibration_for_this_threshold`.
- Position: `optical_frames && camera_geometry && (two_views || second_constraint)`.
- Alpha rejection: `acoustic_waveform && per_condition_normalisation_from_calibration && threshold_not_gamma_dominated`.
- Neutron tag: `multiplicity_observable && simulated_or_measured_multiple_fraction`.
- Fusion: `common_event_id_or_clock && association_policy`.

Stays unknown: per-bubble energy; incident direction; zero as "no bubble" when a period was not live; droplet position from piezo without a stated method; alpha rejection at a threshold not calibrated.

Recognition: positive, frames plus T/P log. Negative, a list of "tracks" from bubble motion read as particle tracks: conflict, reject.

## F26 Compton telescopes and cameras

E: scope is NCT, balloon-borne compact germanium telescope, and Kuchment-Terzioglu cone-transform inversion on synthetic data only. No flight data enter the second paper.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 1106.0323 The NCT instrument. Scope: readout description; strip-to-hit details are in cited papers | onboard electronics return energy and timing of each strip above threshold; 3D interaction positions | strip energy, time; interaction position, energy | 2-4 keV FWHM at 662 keV, 2 mm pitch, 0.5 mm depth resolution as stated | below about 300 keV the background is a factor two under simulation, so excluded | none | none |
| Finding/association | sourced | 1106.0323 Event Reconstruction | N of 3 or more: CKD figure of merit with N-2 dof over N! orderings, best kept, limit seven; N=2: ordering maximising Klein-Nishina times photoabsorption probability | interaction order | extra interactions give more kinematic checks | two-interaction events have no kinematic dof; ordering often ambiguous, and they are 65.8% of selected events | none | none |
| Parameter estimation | sourced | 1106.0323 Introduction (scatter formula); 1604.03805 Introduction | Compton formula from energies gives scatter angle; first two sites give the axis | cos(phi), axis vector, Compton circle or cone | 1.2 cm first-interaction cut narrows ARM 10 to 7.4 degrees in simulation | short first separation: strip pitch dominates angular error | none | none |
| Space/time/direction | sourced | 1106.0323 Image of the Crab Nebula; 1604.03805 Reconstructions in 3D | backprojection of circles; list-mode MLEM, five iterations here. Second paper: cone data to Radon data, three methods, then filtered backprojection | sky image; source position; 3D source function (synthetic) | MLEM shows the Crab, not apparent in raw backprojection | non-admissible detector geometry gives limited-data blurring; formula with singular integrals failed numerically | none | none |
| Energy/momentum | sourced | 1106.0323 The NCT instrument, Analysis of the Crab spectrum. Scope: assumes full absorption | sum of deposits after ordering; on and off source spectra compared with simulation by chi-squared | reconstructed photon energy [keV]; spectrum | Crab spectrum consistent with simulation, test points not | 511 keV atmospheric line must be cut out; partial absorption has no method here | none | none |
| PID/topology | sourced | 1106.0323 Background Reduction, Table of cuts. Scope: event rejection, not particle type | CKD rejection, BGO anticoincidence, Earth horizon cut, interaction count 2-7 | accepted event class | simulation: instrumental events effectively eliminated by CKD | real photons dominate the remaining background; CKD does not remove them | none | none |
| Uncertainty/quality | sourced | 1106.0323 The ARM, Significance of the Crab detection, Analysis of the Crab ARM; 1604.03805 Comparison, Remarks | ARM histogram and FWHM; off-source points; excess variance from independent Poisson classes of circles. Second paper: L2 and H1 errors under added noise | ARM [deg]; excess, sigma_excess; significance | exact sigma 163.4 replaces naive 182.9, as circles cross several points | off-source ARM contains source counts unless modelled; method 2 breaks down at 20% noise | none | none |

Variant and condition gaps (F26):

- Escape hypothesis and incomplete absorption: no method; NCT is designed around full absorption.
- Polarization: not performed by NCT, stated as lack of counts. Link F37.
- Electron-tracking Compton: not covered.
- Two-layer time-of-flight telescopes (COMPTEL) and liquid xenon TPC (LXeGRIT): named in the introduction only.
- CZT, silicon and other compact telescopes: named by reference only.
- Compton cameras at finite distance with real data: only synthetic spherical geometry; paper states it assumes pure surface measure and that the correct weight is unclear.
- Material and passive-mass effects on ordering: not covered; mass model exists, no method.
- Doppler broadening: named as a limit on ARM, no correction.
- Ordering error rate: never quantified in text read.
- Extended sources: stated as future work.

Signature facts: per-event list of interaction position, energy and error; time; multiplicity; detector geometry; mass model; pointing or aspect; veto state; energy window; ordering policy and whether all orderings are kept. 5.15: BP10 multi-site gamma, ordering and escape; BP01/BP02 for raw strips; BP14 only with an azimuth port.

Applicability:

- Order and cone: `multi_site_events && position_energy_with_errors && geometry && (n_sites_ge_3 || two_site_prior_declared)`.
- Energy: `&& (full_absorption_assumed_and_declared || escape_hypothesis_available)`.
- Sky image: `cones && pointing && exposure && (backprojection || list_mode_mlem_response || cone_inversion_with_admissible_geometry)`.
- Polarization: `&& azimuth_response && sufficient_counts`; otherwise unknown.

Stays unknown: first site in two-site events without a stated prior; total energy when escape is not excluded; significance if circles are counted as independent per point.

Recognition: positive, event list with several sites each with position and energy. Negative, a single-site spectrum: not Compton imaging.

## F27 Pair-conversion gamma telescope

E: scope is Fermi LAT only: silicon strip tracker with tungsten converters, CsI calorimeter, segmented ACD. 0902.1089 is the 2009 instrument paper; Pass 8 (2013) is a status proceedings with work then in progress, so its items are not confirmed as final here.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 0902.1089 sec 2.2.1, 2.4.1, 2.4.2 | adjacent strips clustered; time-over-threshold per layer; crystal pedestals and gains, two ends give energy and position along crystal | cluster coordinate; TOT; crystal energy and position | clusters give z plus x or y | x-y pairing ambiguity with two or more particles in a plane | none | none |
| Finding/association | sourced | 0902.1089 sec 2.4.1; 1303.3514 Tracker Reconstruction | CSPR seeded by calorimeter centroid, then BSPR; Kalman hit search in covariance ellipse. Pass 8: tree-based linking of hits | track candidates, quality order; tree | gaps allowed; first-hit cone at high energy limits backsplash | pre-Pass-8 finding depends on calorimeter; backsplash hits confuse it; conversions rarely clean two-track | none | none |
| Parameter estimation | sourced | 0902.1089 sec 2.4.1; 1303.3514 Vertexing | Kalman fit with material; energy shared by observed scattering, refit; closest approach gives vertex, covariant combination | track state and covariance; vertex | best track plus second within distance gives vertex | LAT poorly determines single-track energies since calorimeter deposits overlap | none | none |
| Space/time/direction | sourced | 0902.1089 sec 2.4.1, 2.4.3.2; 1303.3514 Vertexing. Scope: direction, event time not read | vertex or best track, chosen by a classification tree; neutral-energy solution adds calorimeter centroid | photon direction; PSF class | neutral energy solution reduces non-Gaussian tails | thick section about twice worse; tracks may point far from photon when energy goes to gammas | none | none |
| Energy/momentum | sourced | 0902.1089 sec 2.4.2, 2.4.3.2; 1303.3514 Energy Reconstruction | leakage correction by PC, SP and LK methods, tree picks; tracker as sampling calorimeter at low energy. Pass 8: crystal-level profile fit | best energy; probability knob | LK result on CERN electron beam as stated | near 1 TeV crystal saturation; at about 100 MeV about half the energy can lie in the tracker | none | none |
| PID/topology | sourced | 0902.1089 sec 2.2.1, 2.4.3.2; 1303.3514 ACD Reconstruction, Event selection | ACD veto only on tiles pointed to by tracks; TOT at track end; topology and shower match into classification trees | gamma probability, event class | 2-track vertex cuts contamination by about an order | blanket ACD veto kills high-energy gammas through backsplash; irreducible background cannot be separated | none | none |
| Uncertainty/quality | sourced | 0902.1089 sec 2.4.3.2, 2.5; 1303.3514 Event-by-event Errors, Clustering | tree probabilities as knobs; hierarchical Transient, Source, Diffuse classes; reducible background from vertexed versus unvertexed flux; event covariance | effective area, PSF containment, energy dispersion by class | event error from hit composition and material | ghost signals bias calorimeter match; circular error is inaccurate far off axis | none | none |

Variant and condition gaps (F27):

- Spark chamber pair telescopes (EGRET): named only; Thompson 1993 not read.
- Gas TPC, emulsion and other pair telescopes: not covered.
- Charge hypothesis for e+ and e-: no charge-sign measurement in text read. The plan condition stays open; do not label tracks by sign.
- Low-energy scattering tails: named as PSF behaviour, with neutral-energy fix only above sufficient calorimeter energy.
- Pair polarimetry: preliminary in Pass 8. Link F37.
- Event time and clock: not read (sec 2.2.4 skipped).
- Tracker-only and calorimeter-only classes: proposals in Pass 8.

Signature facts: tracker layers and strips, converter map, cluster lists, TOT; calorimeter crystals, gains, pedestals; ACD tile geometry and signal; trigger word; material map; event classes in use and version of the pass. 5.15: BP03 measurements and surfaces; BP04 tracks with errors; BP05 cells with geometry; BP10 pair tracks; BP15 multi-subsystem association.

Applicability:

- Track: `tracker_clusters && surfaces && material_map && (calorimeter_seed || blind_search)`.
- Vertex: `n_tracks_ge_2 && track_covariance`; otherwise single-track direction, not a failure.
- Direction: `(vertex || best_track || (conversion_point && calorimeter_centroid))`.
- Energy: `calorimeter_signals && gains && track_axis && (leakage_model)`; low energy `&& tracker_hit_counts`.
- Gamma selection: `anticoincidence_signals && track_to_tile_extrapolation && classifier_with_stated_training`.

Stays unknown: charge sign; individual e+ e- energy; vertex above 1 GeV in events without a recognizable one; class purity without a background model.

Recognition: positive, converter-tracker plus calorimeter plus veto. Negative, a magnetic spectrometer: not F27 (6.6).

Coupling to record: finding, energy and fit are iterative here. Energy seeds finding, tracks correct energy, energy sets fit weights. BP10's split into BP03/BP04 and BP05 needs that loop stated.

## F28 Coded aperture and response-encoded imaging

E: scope is the coded-mask variant only, two-dimensional, source at infinity, one review (Braga). Near-field use is excluded by the review.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 1909.08595 The concept, Image formation, Masks and antimasks | event map in detector pixels per energy range and integration time; flat-field factors from equal illumination | shadowgram D [counts per pixel] | multiplicative pixel sensitivity corrected per energy range | additive background variation cannot be flat-fielded out | none | none |
| Finding/association | gap-method | 1909.08595 (sections read) | no source-finding or peak-selection algorithm; only that a source gives a peak | none | none | none | none | none |
| Parameter estimation | sourced | 1909.08595 Image formation | D = S (x) M + B; cross-correlate with decoding G, often by FFT; URA, MURA | reconstructed intensity per skybin | M (x) G a delta function gives no intrinsic artifacts | incomplete shadowgrams from the partly coded field give ghost peaks | none | none |
| Space/time/direction | sourced | 1909.08595 Detector plane resolution, Geometry and fields of view, Image formation | skybin grid, theta = atan(xi/l); resolution from m and Delta s over l; location accuracy scales as resolution over SNR | source direction; location accuracy | m about Delta s gives the lowest position uncertainty | repeated pattern on a large mask gives direction ambiguity (rotating mask named as remedy) | none | none |
| Energy/momentum | sourced | 1909.08595 Introduction, Signal-to-noise ratio. Scope: flux per energy band | image per energy range; F = N_H S / (A_eff T Delta E) | flux per band | A_eff includes open fraction and detector efficiency | spectrum taken without A_eff; energy redistribution is not treated | none | none |
| PID/topology | gap-method | 1909.08595 (sections read) | no event classification in text read | none | none | none | none | none |
| Uncertainty/quality | sourced | 1909.08595 Masks and antimasks, Signal-to-noise ratio | variance sigma^2 = N_S + N_T per skybin; SNR per peak; mask and antimask difference removes background | SNR; variance per skybin; minimum flux | antimask simulation reaches about 62, as Poisson predicts | mask only with 20% ramp: artifacts, SNR about 16; other sources add noise to every peak | none | none |

Variant and condition gaps (F28):

- Collimated imaging: not covered. A collimator appears only as a field-of-view device in a coded-mask camera, and non-imaging collimators are mentioned.
- Focusing optics (Wolter, NuSTAR, lobster-eye): named as comparisons only, no response or reconstruction.
- Partially coded field reconstruction: ghost problem stated, no correction read.
- Extended sources: word absent from text searched; no method.
- Attitude and pointing bias: `attitude`, `pointing`, `dither` absent from text searched; no method.
- Iterative or likelihood inversion: only cited.
- Near-field coded imaging (medical, security): explicitly excluded.
- Crossed one-dimensional cameras: described, no reconstruction method.
- Rotating mask timing analysis: named only.
- Off-axis mask thickness effects: neglected in the derivation as stated.

Signature facts: detector map in raw counts per pixel; energy band; integration time; mask pattern and open fraction; mask-detector distance; cell and pixel size; field class (fully or partly coded); background model or antimask; pointing record; variant. 5.15: BP02 channel features with geometry; BP10 detector maps/shadowgrams and mask/PSF/pointing.

Applicability:

- Coded-mask image: `variant_coded_mask && raw_count_map && mask_pattern && mask_detector_geometry && source_at_infinity && (in_fully_coded_field || partial_coding_handled) && (uniform_background || background_measured || antimask_pair)`.
- Flux: `&& effective_area_per_band && exposure`.
- Collimated or focusing input: stays unknown here; a coded-mask decoder is not applicable.

Stays unknown: source intensity from a normalized or cropped map (BP10); a source in the partly coded field without ghost handling; absolute position without pointing.

Recognition: positive, count map plus mask file. Negative, a sky image with no detector map: no inversion here.

## F33 Few-electron and Skipper-CCD readout

E: scope is two Skipper CCD studies (Tiffenberg et al. and SENSEI, Barak et al.), low-temperature, one device each. Links F01/F02 (6.6).

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 1706.00028 Technical Description, Signal processing | non-destructive repeat samples of one pixel; average of N samples; sigma = sigma_1/sqrt(N); samples configurable per pixel | sample stream; pixel charge | noise follows the 1/sqrt(N) curve, 0.068 e rms at 4000 samples | correlated noise from switching supplies; slight deviation at N of about 2000 and above | none | none |
| Finding/association | sourced | 2106.08347 Empirical model, Results, Appendix. Scope: pixel level; masks are defined in SENSEI 2020, not read | single-electron pixels counted after selection, edge and halo masks; jump search between sample groups at 5 std | SEE per pixel; jump count | dark rate falls with halo radius until roughly 30 pixels | above 100 e a jump is treated as a high-energy hit, not charge generation | none | none |
| Parameter estimation | sourced | 1706.00028 Impact of dark current, Fig. 1 | integer peaks; classify to nearest integer; keep within 3 sigma of an integer | charge state [e] | below 0.1 e rms, n to n+1 error about 3e-7, about 1e-12 after the cut | at 0.14 e rms, tail of dark bin needs a cut 0.84 e above it, 87% efficiency | none | none |
| Space/time/direction | sourced | 2106.08347 Dark current, Amplifier light. Scope: pixel position and effective exposure, no event time | pixel exposure differs by readout order; mean readout term lambda_DC/2 | pixel index; t_EXP, t_RO | last pixel read has extra t_RO | equal exposure assumed; amplifier-light rate averaged though it is localized | none | none |
| Energy/momentum | sourced | 1706.00028 Particle Physics. Scope: electron-recoil relation, ionization handoff | electrons to energy with an assumed 3.6 eV per extra pair above gap | charge [e]; electron recoil [eV] | 2 e about 4.7 eV, 3 e about 8.3 eV, as stated | nuclear recoil: ionization efficiency not accurately known at low energies | none | none |
| PID/topology | sourced | 2106.08347 Semi-empirical model, Transfer Curves. Scope: origin of single-electron events | separate by exposure, readout and space dependence | DC, AL, SC components | SC is exposure-independent and from clocking | extrinsic dark current is in principle indistinguishable from intrinsic | none | none |
| Uncertainty/quality | sourced | 2106.08347 Transfer Curves, Results, Appendix; 1706.00028 Impact of dark current | linear fits of SEE versus t_EXP and t_RO; V_DD scan for amplifier light; Poisson model of dark counts; misclassification check | lambda_DC, lambda_AL, mu_SC; readout noise | V_DD change from -22 to -21 V cuts amplifier light by two orders | quadrants with excess SEE or high CTI dropped; origin of jumps not settled | none | none |

Variant and condition gaps (F33):

- Other discrete-quanta semiconductor sensors: a depleted field effect transistor mini-array appears in one footnote only.
- Cluster finding and pixel grouping: not covered; selection deferred to SENSEI 2020.
- CTI correction: only exclusion of a quadrant and temperature effect, no method.
- Gain calibration from peaks to electrons: "stable linear gain" stated, no procedure read.
- Sample correlation beyond the sqrt(N) check: no model.
- Credible energy-response handoff: only the assumed pair energy; no response for nuclear recoils.
- Charge diffusion across pixels and depth: bias choice only.
- Zero/one-electron confusion measured on data: only Gaussian-noise probabilities.
- Spatial model of amplifier light: paper chose not to study it.

Signature facts: per-pixel sample array or averaged charge with N stated; sigma_1; gain; phase timing (cleaning, exposure, readout); t_EXP and t_RO; read order and pixel map; clocking settings; V_DD; temperature; masks in use; CTI status per quadrant. 5.15: BP01 samples/clock; BP02 pixel features; BP09 repeated samples with discrete-quanta branch.

Applicability:

- Charge state: `repeated_samples_or_averaged_with_N && gain_known && sample_independence_checked && resolved_integer_peaks`.
- SEE rate: `&& exposure_phase_times && read_order && selection_masks`.
- Origin split: `&& (several_exposures && several_readout_times) && zero_exposure_images`.
- Energy: `charge_state && energy_response_declared_for_recoil_kind`.

Stays unknown: nuclear recoil energy from charge (BP09); event time inside an exposure; tracks (not forced, plan F33 row); pixel exposure when the read order is missing.

Recognition: positive, repeated samples per pixel plus phase metadata. Negative, a conventional CCD with no repeats: F01 instead; a charge state may not be claimed.

## Plan statements checked against sources

No plan statement was contradicted. Supported directly: BP09 and F21 no energy from SNSPD counts (1204.5560 sec 2.2.3); BP09 few-electron charge is not recoil energy (1706.00028, ionization efficiency); F24 no continuous energy per bubble (physics/0508098 sec 5, amplitude follows droplet size and position); BP12 independence warning (1106.0323, naive Poisson variance fails); F33 exposure differences (2106.08347).

Refinements to consider:

- F27 row and BP10 imply a conversion vertex with e+/e- tracks. In 0902.1089 a majority of events above 1 GeV lack a recognizable vertex, and single tracks are assigned their own vertex. In 1303.3514 conversions rarely look like clean two-track events. Single-track is a normal output, and no charge sign is read.
- F28 ghosts/sidelobes: in 1909.08595 URA-type patterns have no intrinsic sidelobes in the fully coded field; ghosts come from partial coding, background and pattern choice. Scope the row accordingly.
- F24: a PICO-60 caption says higher-energy alphas give larger acoustic signals. Not an energy measurement, so no conflict with the plan.

Access date 2026-11-06. Plan v9.2 rows F34-F38, 5.15, 6.6, 7.1.1, BP13, BP14, W7. Nothing was run.

Conventions:

- Status: `sourced`, `gap-method`, `not-applicable`. Every `sourced` cell states the scope of the one experiment or code it comes from. It is not a family-wide claim.
- Source text was the arXiv LaTeX e-print of the latest listed version, with the PDF and abstract page fetched too. Section names are those printed in the source, because letters have no numbered sections. Source records: `t11-sources-b.json`.
- Read level `full-text` means the whole body was read. `page` means only the named sections were read, some paragraphs only up to a length cut-off; the cells rest on those sections alone.
- Binding is `none` throughout. The baseline tree has no code for these families; its only hits are a generic polarimeter table row and a bibliography mention. Run evidence is `none` throughout. Cases are taken from the sources but are design cases here.
- Predicates: `&&`, `||`. Each term is a fact to establish. A term not established stays unknown; a name alone does not establish it (5.5).
- F35 and F37 have one table per variant, as 6.6 requires. A variant with no source is a table of `gap-method` cells, not a stretched neighbour.

## F34 Cyclotron-radiation emission spectroscopy (CRES)

Scope: Project 8 only, Phase I (rectangular waveguide, 83mKr) and Phase II (circular waveguide, 83mKr and T2). Outputs are per-event start frequency and a binned spectrum. No other CRES instrument was read.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 2212.05048 apparatus paragraphs, Fig. "spectrogram"; 2303.12055 Sec. "Radio-frequency system" | amplify, downmix, digitize; FPGA FFT in three tunable windows; spectrogram; SNR trigger on bins | power vs frequency and time; bin 24.4 kHz by 40.96 us (Phase II); SNR = bin power / mean bin power | SNR used instead of absolute power in trigger, reconstruction and spectrum analysis, avoiding amplifier and filter gain variation | weak resonant cavity modes from residual reflections change response with trap position and frequency | none | none |
| Finding/association | sourced | 2212.05048 reconstruction paragraph; 2303.12055 Sec. "Electron event properties"; 1703.02037 Sec. "Results" (Phase I) | point clustering of high-SNR bins into tracks; tracks close in time grouped as one event. Phase I: segments above SNR 6 dB, next segment begins where previous ended | frequency-time track; event = ordered tracks | chirped tracks with frequency jumps from gas collisions grouped to one electron | first visible track is not the true first track: tracks can be too short or too weak | none | none |
| Parameter estimation | sourced | 2303.12055 Secs. "Electron event properties", "CRES energy spectrum model", "Tritium analysis procedures"; 2212.05048 Eq. FullModel | start frequency of first track; binned spectrum model S = eps (Y * R_PSF), R_PSF = sum_j A_j (I * L^{*j}); Poisson-likelihood chi-square fits (Kr), Bayesian and frequentist fits (T2) | start frequency [Hz]; binned f_c spectrum; B, A_j, sigma, E0, m_beta | Kr K-line fit with scatter parameters and B free, no background seen | fit that ignores scatter peaks: low-energy tail from undetected first tracks | none | none |
| Space/time/direction | gap-method | read: 2303.12055 Sec. "Electron event properties" and a keyword search for pitch angle; 1703.02037 Sec. "Results" | no per-event position or pitch-angle estimator in the sections read. Only a cut on event start vs trigger time (Phase I). Pitch and radius appear through simulation and efficiency | none | none | frequency-time track read as a spatial track (W7) | none | none |
| Energy/identifiable quantity | sourced | 2212.05048 Eq. energytofrequency; 2303.12055 Sec. "Test of the frequency-energy relation"; 1703.02037 Sec. "Cyclotron Radiation Emission Spectroscopy" | f_c = abs(e) B / (2 pi (m_e + E_kin/c^2)); mean B from 83mKr lines; result is energy at decay via start frequency | E_kin [eV] from start frequency and B | Voigt fits to Kr conversion lines verify the relation over 14.3 keV with B free | energy from a later track without the scatter model; B from a different trap configuration | none | none |
| PID/topology | sourced | 2303.12055 Sec. "Electron event properties"; 2212.05048 selection paragraph | electron event vs RF noise only: upward slope; cuts on number of tracks, first-track duration and SNR, fixed before tritium data | keep/reject per candidate event | zero counts observed in the region above the T2 endpoint over the 82-day run | RF noise fluctuations forming false tracks. No species identification read | none | none |
| Uncertainty/quality | sourced | 2212.05048 analysis paragraphs, Tab. uncertainties; 2303.12055 Secs. "Field-shifted Kr data analysis", "Background" | efficiency vs frequency from field-shifted Kr; MC coverage and bias of the approximate model; Asimov sets for individual systematics; background limit from counts above endpoint | eps(f_c); coverage; sigma(E0) terms | approximate model gives correct coverage and no bias on ensembles from the un-approximated model | efficiency notch near a TM01 mode: faster chirp, reconstruction tuned for normal slopes loses events | none | none |

Variant and condition gaps:

- Other CRES apparatus: nothing read. The planned cavity geometry is only an outlook sentence in 2212.05048.
- Incorrect merging of neighbouring chirps (plan negative case): not covered. 2303.12055 reports negligible pileup at its rates and says pileup is studied for future phases.
- Sidebands: in Phase II they are too weak to detect (2212.05048) and only the carrier is detected (2303.12055). No sideband reconstruction method exists in the sources; matched filtering and machine learning are stated as potential. 1909.08115 was not read.
- Space and direction: gap above. 2212.05048 says sideband identification could give input for kinematic corrections, which is a prospect, not a method.
- Overlapping DAQ windows: overlap handled by analysing only the highest-efficiency channel (2303.12055). Other overlap handling not covered.

Signature facts: representation (time series or spectrogram; raw kept only after trigger); axis (downmix offset, window centre, sign, bin sizes); acquisition (trigger rule, window overlap, live time); conditions (trap configuration, mean B, gas composition, collision time); calibration (line source, field-shifted efficiency). 5.15: BP01 samples and clock; BP13 IQ or frequency-time with RF/IF/LO coordinates.

Applicability: `(rf_timeseries || spectrogram) && frequency_axis_known && bin_sizes_known && trigger_rule_known`; track and event: `&& high_snr_bin_clustering_allowed && chirp_sign_known`; energy: `&& start_frequency && mean_B_calibrated && trap_configuration_matches_calibration`; spectrum: `&& efficiency_vs_frequency && (scatter_amplitudes && energy_loss && instrumental_resolution)`.
Stays unknown: per-event position and pitch; energy from a mid-event track; any spectrum without the missed-track term.
Recognition: positive, spectrogram with upward chirps and frequency jumps in a trapped-electron cell. Negative, a power spectrum averaged over a tuning step (F35), or a frequency-time plot offered as spatial tracks.

## F35 Resonant and coherent-field readout

Output is a spectrum, a limit or a candidate list, not events. Links per 6.6: F19, F21, F32 not counted here.

### F35-cavity

Scope: HAYSTAC first data run only, photon coupling, tunable cavity with JPA.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 1706.08388 Secs. "Axion search data", "Cuts on spectra", "Cuts on IF bins", "Removing the spectral baseline" | one averaged power spectrum per tuning step; VNA, JPA gain and Y-factor auxiliaries; cut spectra and IF bins; normalize to average baseline, Savitzky-Golay filter, subtract 1 | power vs IF bin [100 Hz bins]; processed spectrum, dimensionless | baseline removed on scales larger than the axion line without structure left in processed spectra | spectra near an intruder mode: single-mode assumption fails, all such spectra cut | none | none |
| Finding/association | sourced | 1706.08388 Secs. "Analysis overview", "Candidates and Exclusion", "Setting the threshold" | threshold on normalized grand spectrum; bins above it become rescan candidates; correlated neighbouring bins excluded around a candidate | candidate: frequency, threshold coupling, normalized excess | observed candidate count compared with simulated expectation at the chosen threshold | adjacent bins treated as separate candidates: grand-spectrum bins overlap and are correlated | none | none |
| Parameter estimation | sourced | 1706.08388 Secs. "Combining spectra vertically", "Constructing the combined spectrum", "Accounting for correlations"; rebinning from "Analysis overview" only | rescale by noise and Lorentzian conversion power; inverse-variance (ML) sum of IF bins on one RF bin; rebin and lineshape-weighted sum | combined, rebinned, grand spectrum; delta and sigma per RF bin | m_k spectra per RF bin independent because each spectrum gives at most one IF bin there | quadrature variance applied to correlated neighbouring bins | none | none |
| Space/time/direction | not-applicable | 1706.08388 Sec. "Axion search data" | readout reason: only one heavily averaged spectrum per iteration is stored, from one cavity mode antenna; no position or direction channel and no within-iteration time | none | none | a per-event or per-position result claimed from these spectra | none | none |
| Energy/identifiable quantity | sourced | 1706.08388 Secs. "Analysis overview", "Candidates and Exclusion" | excess power at frequency; threshold and SNR give excluded coupling at a chosen confidence, directly from statistics of combined data | frequency [Hz]; magnitude of g_gamma excluded per bin | confidence from Gaussian statistics of the grand spectrum | a field or mass read from one bin without the lineshape and detuning weights | none | none |
| PID/topology | sourced | 1706.08388 Secs. "Cuts on IF bins", "Candidates and Exclusion", "Rescan data and analysis" | signal vs interference: IF interference sits in the same IF bins; RF interference follows RF across tuning steps; real signal should persist on rescan | bad-bin list; rescan coincidence threshold | candidate fails coincidence threshold in separately processed rescan data | RF interference mimics an axion and is hard to flag before combination | none | none |
| Uncertainty/quality | sourced | 1706.08388 Secs. "Statistics of the processed spectra", "Accounting for correlations", "SG filter-induced attenuation", App. "Synthetic axion injections" | Gaussian check of bins; simulations for correlation factor xi and filter attenuation eta; hardware injections as fail-safe | xi, eta; SNR per bin | injected narrowband signals give excess, used only as a check | correlation or signal attenuation by the baseline filter left uncorrected | none | none |

### F35-spin

Scope: QUAX ferromagnetic haloscope, one paper; electron spin via YIG spheres coupled to a cavity mode. This is a spin-magnetometer readout. Not extended to other spin systems.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 2001.08940 (no section heads) paragraphs on calibration and search procedure | transmission sets hybrid mode, couples antenna, gives linewidth; JPA and heterodyne; ADC band around mode; FFT at 100 Hz to remove bad bins; rebin to about 5 kHz; degree-five polynomial fit, residuals | power vs frequency; residual sigma_P | noise budget consistent with measured T_n | model of two oscillators fails near a higher cavity mode; four-mode Hamiltonian used instead | none | none |
| Finding/association | gap-method | 2001.08940 search paragraphs | no candidate threshold or rescan rule stated; only that fluctuations match estimated noise and no significant signal was seen | none | none | none | none | none |
| Parameter estimation | sourced | 2001.08940 search and limit paragraphs | standard deviation of residuals gives sensitivity; compared with Dicke prediction | sigma_P [W] per run | measured fluctuation close to Dicke value at longest integration | none stated in text | none | none |
| Space/time/direction | sourced | 2001.08940 interaction and data paragraphs | signal has daily modulation from the angle between B0 and B_a; runs taken at the modulation maximum; 1 ms waterfall spectrogram for fast bursts | run time vs modulation phase | run placed at modulation maximum | run outside the maximum treated as equal sensitivity | none | none |
| Energy/identifiable quantity | sourced | 2001.08940 Eq. gaee and field paragraphs | sigma_P to field sigma_B; 95% CL limit on g_aee with transduction coefficient k_ac; scan by changing B0 | B field [T]; g_aee | all parameters measured within each run | k_ac is calculated from a model and depends on omega_1 | none | none |
| PID/topology | gap-method | 2001.08940 search paragraphs | no signal vs interference classification beyond bin removal and the burst check | none | none | none | none | none |
| Uncertainty/quality | sourced | 2001.08940 calibration paragraphs, Tab. noise budget, search paragraphs | injected calibrated tone gives gain and noise temperature; calibration uncertainty from antenna coupling; thermal-noise check; fake axion added to real data | T_n, gain, calibration uncertainty | analysis keeps signal and SNR for fake axion in real data | unaccounted difference between expected and measured noise | none | none |

### F35-circuit

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | gap-method | none read | none | none | none | none | none | none |
| Finding/association | gap-method | none read | none | none | none | none | none | none |
| Parameter estimation | gap-method | none read | none | none | none | none | none | none |
| Space/time/direction | gap-method | none read | none | none | none | none | none | none |
| Energy/identifiable quantity | gap-method | none read | none | none | none | none | none | none |
| PID/topology | gap-method | none read | none | none | none | none | none | none |
| Uncertainty/quality | gap-method | none read | none | none | none | none | none | none |

No circuit-readout candidate appears in the discovery hits, by title or abstract keyword search.

### F35-broadband

Scope: BREAD conceptual design, read at `page` level by keyword-selected sentences of the introduction, photosensor and sensitivity sections. No data exist in that paper; cells state what it proposes.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 2111.12103 Sec. "Photosensor technologies" | proposed: parabolic reflector focuses barrel signal on a sensor; bolometer with time-modulated input (chopper), or photocounter with thresholding and pulse fitting | NEP or dark count rate | signal shifted to where 1/f noise is subdominant | bolometer on static signal, limited by 1/f noise | none | none |
| Finding/association | gap-method | 2111.12103 sections above | no candidate method read | none | none | none | none | none |
| Parameter estimation | gap-method | 2111.12103 sections above | projections only | none | none | none | none | none |
| Space/time/direction | gap-method | 2111.12103 sections above; App. on focusing not read | none read | none | none | none | none | none |
| Energy/identifiable quantity | gap-method | 2111.12103 sections above | sensitivity scaling only, not a reconstruction | none | none | none | none | none |
| PID/topology | gap-method | 2111.12103 sections above | none read | none | none | none | none | none |
| Uncertainty/quality | gap-method | 2111.12103 sections above | assumed SNR and efficiency in projections only | none | none | none | none | none |

Variant and condition gaps:

- Circuit variant: no source, all seven cells gap.
- Spin variants other than ferromagnetic YIG (for example nuclear spin): no source. Spin relaxation enters QUAX as tau_s only.
- Spin scan combination: 2001.08940 reports fifty-six runs at fixed B0; the sections read give no rule for combining overlapping runs.
- Rescan in spin: not stated. Do not inherit HAYSTAC's rescan.
- Cavity variants other than HAYSTAC: not read. The paper notes ADMX obtains confidence from Monte Carlo, which is a difference, so HAYSTAC's procedure is not the family's.
- Broadband: no analysis method beyond sensor signal processing. All non-signal cells are gaps.
- Wrong RF/IF axis: HAYSTAC aligns bins by coercing LO to bin grid and defines the IF to RF map. An LO sign error case is not treated.
- Same-raw-interval reuse (W7 RF subcase): HAYSTAC combines separate measurements; shared raw data between settings is not treated.

Averaged spectra: HAYSTAC stores averages of many subspectra, and fluctuations are Gaussian by the central limit theorem, with filter-induced correlations. These bins are not Poisson counts. Only the averaged spectrum is on disk, so raw-level re-analysis is not possible from that product.

Signature facts: variant (cavity, circuit, spin, broadband: each stated, never inferred from a name); representation (raw IQ or averaged spectrum; averaging time; bin width); axis (LO and pump settings, RF/IF map, sign); per-setting response (mode frequency, Q, coupling, form factor or k_ac, noise temperature); order (scan order, tuning, drift, settling); role (discovery or rescan); injection log. 5.15: BP01 where samples are kept; BP13 scan settings with overlap and branch-specific response.

Applicability, cavity: `variant_cavity && spectra_per_setting && rf_if_map && averaging_time && per_setting_noise_and_mode_parameters && (baseline_filter_transfer_known || injection_or_simulation_available)`; candidates: `&& threshold_rule_fixed && rescan_role_declared`.
Applicability, spin: `variant_spin && hybrid_mode_model && per_run_tau_s_and_N_s && transduction_coefficient && calibrated_gain_and_noise`; limit: `&& modulation_phase_of_run`.
Circuit: `variant_circuit` selects a gap, nothing else.
Stays unknown: independence between settings without a raw-interval ledger; any coupling limit without per-setting response; a spin result from cavity constants.
Recognition: positive, sequence of averaged spectra with tuning steps and auxiliary mode measurements. Negative, a spectrogram with event tracks (F34), or a bare spectrum with no axis semantics (5.15 exclusion).

## F36 Retarding, integrating and scan-encoded spectroscopy

Scope: KATRIN first neutrino-mass campaign (KNM1) only, a MAC-E filter with stepped retarding potential. Output is an integral spectrum R(qU). Source-spectrum inference is handed to statistics and theory by BP13; the fit cell records what the source did.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 2101.05253 Secs. "Electron counting and region of interest", "Data pipeline" | per-pixel trigger; online double trapezoidal filter for energy and time; waveforms not saved; count in fixed ROI over selected pixels | counts per scan step in ROI; timestamp; ADC energy | ROI lower bound chosen so charge-sharing gain and loss compensate | high-rate pileup: energy pushed above ROI, event lost; rate correction applied | none | none |
| Finding/association | sourced | 2101.05253 Secs. "Data pipeline", "Acquisition of the integral beta-decay spectrum" | assign counts to a scan step by HV set point and handshake; remove first two seconds of each step; quality cuts on slow control | (setting, time, counts) per scan step | steps kept only after read-back reaches set point | acquisition starting before HV is stable, seen as synchronization errors | none | none |
| Parameter estimation | sourced | 2101.05253 Secs. "Scan combination (stacking)", "Spectral fit", "Covariance-matrix approach", "Monte-Carlo-propagation approach" | sum counts at like steps, average qU over scans; four-parameter shape-only fit; chi-square with covariance, or MC propagation | R(<qU>); signal amplitude, endpoint, background, m^2 | three blind analyses with independent code agree | stacking without stability and HV reproducibility checks; it does not correct scan-to-scan variation | none | none |
| Space/time/direction | sourced | 2101.05253 Secs. "Electron counting and region of interest", "Pixel combination", "Scan combination (stacking)" | pixel map and timestamps used for selection and stability tests; pixel-wise and scan-wise fits before merging into one effective pixel; pitch angle integrated in transmission, not measured per electron | pixel id; scan time; per-pixel endpoint | no spatial or temporal structure beyond statistics, so merge is justified | merge assumed where fields vary across the analyzing plane; radial variation exists | none | none |
| Energy/identifiable quantity | sourced | 2101.05253 Secs. "Response and transmission functions", "Analyzing-plane potentials", "Electron counting and region of interest" | threshold qU from monitored retarding potential; transmission condition; response f(E-qU) with scattering probabilities and energy-loss function; detector energy is low-resolution and used for ROI only | qU [eV]; response f(E-qU); integral rate | response measured with monoenergetic electrons from an e-gun | detector energy read as electron energy: per-particle energy is not available at spectrometer resolution | none | none |
| PID/topology | not-applicable | 2101.05253 Sec. "Electron counting and region of interest" | physical reason in source: background electrons are accelerated like signal and share the detector energy peak, so an energy cut cannot separate them per event; background is an estimated rate | none per event; R_bg in fit | background rate from scan steps above the endpoint | event-level signal label | none | none |
| Uncertainty/quality | sourced | 2101.05253 Secs. "Background", "Stacking", "Blinding strategy", "Covariance-matrix approach"; Sec. "Acquisition of the integral beta-decay spectrum" | alternating scan direction against drift; model blinding; MC twins; covariance or MC nuisance propagation; over-dispersion term on background; stacking bias from Asimov twins | C matrix; systematic breakdown; stacking uncertainty | MC twins recover inputs before unblinding | background treated as pure Poisson: measured distribution is wider than the Poisson expectation | none | none |

Variant and condition gaps:

- Time-encoded variants: 2007.01020 proposes time-focusing time-of-flight with a time-dependent potential and a time-of-arrival spectrum. It is a simulation study of added hardware at KATRIN, read at `page` level. It gives no measured method, so it is a separate gap; the earlier time-of-flight method it says needs a start time was not read (hit 1308.0532 is a candidate for it).
- Retarding instruments other than KATRIN: not read.
- Scan-step-duration background: not significant in KNM1 but seen in a later run, which the sections read only mention. A later campaign's handling is a gap.
- Per-pixel transmission: KNM1 uses an average over pixels. A per-pixel or per-patch fit is not covered.
- Deadtime: named by the plan. The source mentions it for high-rate e-gun measurement only; a deadtime correction for beta scans was not read.
- Link to general magnetic spectrometers (6.6): nothing read.

Counts: raw scan-step counts are the input; do not replace them with averages that drop time or conditions (W7). The source stacks after showing stability and keeps per-scan conditions for MC twins. Revisited steps are combined by summing like steps. Count rate and live time are computed after the two-second cut.

Signature facts: representation (setting, effective time, counts, per pixel or summed); setting (HV set point and read-back, scan order, direction); response version (transmission, energy-loss function, column density, field values); selection (ROI, pixel list, quality flags); background region steps. 5.15: BP12 count with interval and exposure; BP13 retarding counts.

Applicability: `setting_time_counts && retarding_readback && transmission_version && (scan_order_known) && effective_time_known`; stacking: `&& setting_reproducibility_shown && parameter_stability_shown`; pixel merge: `&& no_spatial_trend_shown`; fit handoff: `&& background_region_steps || independent_background_model`.
Stays unknown: per-electron energy; pitch angle; signal or background label; independence of revisits without condition records.
Recognition: positive, table of HV settings with times and counts. Negative, a differential detector energy spectrum offered as the science spectrum.

## F37 Radiation polarimetry

Output is Stokes parameters or a modulation curve over an ensemble, not a polarization per photon. ixpeobssim says IXPE recovers polarization on a statistical basis.

### F37-photoelectric

Scope: IXPE as described by ixpeobssim, a simulator and analysis framework based on parametrized response. Its input is reconstructed level-2 events; it does not reconstruct tracks.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | gap-method | 2203.06384 Secs. "Output data format", "Event weights" | level-1 track images exist; the code cannot generate track images and no image processing is given | none | none | none | none | none |
| Finding/association | gap-method | 2203.06384 same sections | no track-axis or absorption-point reconstruction given | none | none | none | none | none |
| Parameter estimation | sourced | 2203.06384 Secs. "Introduction", "Basic polarization analysis" | event Stokes q=2cos2phi, u=2sin2phi; sum over a subset, corrected by effective area and modulation factor; optional weights | q_i, u_i; Q, U, I over subset | Stokes form avoids dependence between polarization degree and angle | single event read as definite polarization: only ensemble sums are interpreted | none | none |
| Space/time/direction | sourced | 2203.06384 Secs. "Introduction", "Dithering and pointing history" | each event has time, energy, two sky coordinates, azimuth; dithering removed through aspect solution; pointing history kept | sky coordinates; detector coordinates; pointing | dither averages spurious modulation over the detector | exposure computed without the dither pattern | none | none |
| Energy/identifiable quantity | sourced | 2203.06384 Secs. "Response functions", "Spectro-polarimetric fitting" | Stokes spectra I_k, Q_k, U_k in PI channels with response matrix and modulation response function | Stokes spectra; polarization cubes and maps | fitted with standard tools using effective area for I and modulation response for Q, U | energy dispersion neglected by default in the simple analysis; verify per case | none | none |
| PID/topology | gap-method | 2203.06384 sections read | no event classification read; weights describe reconstruction quality only | none | none | none | none | none |
| Uncertainty/quality | sourced | 2203.06384 Secs. "Introduction", "Spectro-polarimetric fitting", "Event weights" | subtraction of spurious modulation (reference, not read); per-bin errors from sums of q^2, u^2; ground truth extension for checks | sigma_Q, sigma_U | ground truth used to test response effects | Q, U or weighted I treated as pure counting statistics: only unweighted I is; end-to-end weight test is a stated limitation | none | none |

### F37-Compton

Scope: POLAR, one paper on a channel-level correction. Polarization reconstruction there is summarized and referred to other papers.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 1507.04474 Secs. "Crosstalk and response non-uniformity modeling" (start), "Conclusion"; abstract | one matrix for crosstalk and non-uniformity, from mono-energetic calibration, applied by linear transformation | channel amplitudes to energy depositions | residual crosstalk near zero in ESRF test runs after correction | uncorrected crosstalk smears energy over channels | none | none |
| Finding/association | sourced | 1507.04474 Sec. "POLAR instrument" | azimuth from the line joining the two bars with highest deposits, a correlation shown in Monte Carlo | xi, angle to detector x-axis | line correlated with outgoing photon direction | none stated. Bar choice is a proxy, not the true scatter sequence | none | none |
| Parameter estimation | sourced | 1507.04474 Sec. "POLAR instrument" | fit modulation curve K{1+mu cos[2(xi-xi0)]}; p = mu/mu_100 | mu, xi_0, p | fit over all detected GRB photons | one photon read as polarized | none | none |
| Space/time/direction | gap-method | 1507.04474 sections above | detector-frame angle only; detector-to-sky rotation not read | none | none | none | none | none |
| Energy/identifiable quantity | sourced | 1507.04474 abstract, Sec. "Conclusion" | real energy deposition per bar from the transformation, with energy calibration | E_dep per channel | spectra unfolded at known beam energies | none stated | none | none |
| PID/topology | gap-method | 1507.04474 sections above | none read | none | none | none | none | none |
| Uncertainty/quality | sourced | 1507.04474 Secs. "POLAR instrument", "Conclusion" | mu_100 from Monte Carlo and 100% polarized beams; residual crosstalk and non-uniformity from test runs; 22Na sources for in-flight calibration | mu_100; residuals | verification on ESRF runs at two energies | a polarization systematic budget is not in the sections read | none | none |

### F37-modulated

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | gap-method | none read | none | none | none | none | none | none |
| Finding/association | gap-method | none read | none | none | none | none | none | none |
| Parameter estimation | gap-method | none read | none | none | none | none | none | none |
| Space/time/direction | gap-method | none read | none | none | none | none | none | none |
| Energy/identifiable quantity | gap-method | none read | none | none | none | none | none | none |
| PID/topology | gap-method | none read | none | none | none | none | none | none |
| Uncertainty/quality | gap-method | none read | none | none | none | none | none | none |

No modulated-readout candidate appears in the discovery hits. Azimuthal modulation in IXPE and POLAR is the analyzer's response, not a modulated readout, so those tables do not fill this one.

Variant and condition gaps:

- Modulated readout: no source, all seven cells gap.
- Photoelectric track reconstruction and absorption point: gap. Needed from a detector-level source; the plan row requires them.
- Compton scatter ordering and multi-site reconstruction beyond the two-bar proxy: gap. Link to F26 not assessed.
- Compton beam polarimeters (hep-ex hits on electron beams): a different measurement, not read.
- Unpolarized and rotated controls: IXPE correction named, procedure in a reference not read. Detector and sky rotation for POLAR: gap.
- Scope of ixpeobssim: simulation and high-level analysis; do not read it as the instrument's reconstruction.

Signature facts: variant (photoelectric, Compton, modulated); representation (track image, event azimuth, bar deposits, binned curve); angle convention (period, axis or vector, frame); basis (detector or sky, rotation source); response (modulation factor or mu_100, effective area, version, weighted or unweighted); spurious modulation calibration; pointing or dither history. 5.15: BP02 channel or image features; BP10 multi-site where Compton; BP14 angle/modulation.

Applicability, photoelectric: `variant_photoelectric && event_angle && angle_period_pi && basis_known && modulation_factor && effective_area && spurious_modulation_corrected`; sky products: `&& pointing_history`; fits: `&& (unweighted_I_only_counting_declared)`.
Applicability, Compton: `variant_compton && bar_deposits && crosstalk_matrix && energy_calibration && mu_100`; sky basis stays a gap.
Stays unknown: polarization of one photon; degree without modulation factor; sky angle without rotation; a result from a track axis alone.
Recognition: positive, event list with azimuth and a modulation response, or bar-hit pairs with a calibrated mu_100. Negative, a single track image offered as a measured polarization vector.

## F38 Scanning radiometer and timestream-to-map

Scope: Planck-like simulations only (LFI 70 GHz and 100 GHz, HFI-like). No real data in the sources read. Output is a map with noise description. Cosmological inference is excluded.

| Axis | Status | Source | Method | Observable/port | Positive case | Negative case | Binding | Run evidence |
|---|---|---|---|---|---|---|---|---|
| Signal extraction | sourced | 1103.2281 Secs. "Photometric calibration", "Dipole calibration" | gain per detector from the time-dependent orbital dipole, solved as a linear problem, iterated with offsets | gain g; calibrated rings | orbital dipole is known and not fixed on sky | single polarization-sensitive detector: degenerate if polarization modelled, biased if neglected | none | none |
| Finding/association | sourced | astro-ph/0501504 Sec. "Destriping technique"; 0904.3623 Sec. "Derivation" | pointing assigns samples to pixels; crossing points link baseline segments | hits per pixel; crossing points | baselines sufficiently connected: null space is one-dimensional | crossings clustered in a small region for short segments: errors may blow up | none | none |
| Parameter estimation | sourced | astro-ph/0412517 Sec. "Map-making problem", "Map-making algorithm"; astro-ph/0501504 Sec. "ROMA and MapCUMBA"; 0904.3623 Sec. "Derivation" | destriping: joint fit of map and baselines, conjugate gradient for amplitudes, then binning; with noise prior (Madam); or ML map with noise filter (ROMA, MapCUMBA) | map m; amplitudes a | Madam approaches the minimum-variance map as base functions increase | ML with noise spectrum assumed perfectly known; in real data it must be estimated | none | none |
| Space/time/direction | sourced | 0904.3623 Sec. "Derivation"; astro-ph/0501504 Sec. "Methods" | pointing matrix rows (1, cos2psi, sin2psi) on the pixel of the beam centre; no beam deconvolution, map is beam and pixel smoothed | pixel; psi; TOD sample | pixel kept when inverse condition number passes a limit | pixel with fewer than 3 sufficiently different angles: excluded with its samples | none | none |
| Energy/identifiable quantity | sourced | 0904.3623 Sec. "Derivation"; 1103.2281 Sec. "The map-making problem" | I, Q, U per pixel in calibrated temperature; constant offset is unidentifiable | I, Q, U map | anisotropy and polarization stay identifiable | monopole claimed from the map: same effect as a constant noise offset | none | none |
| PID/topology | not-applicable | astro-ph/0412517 Sec. "Map-making problem"; 0904.3623 Sec. "Derivation" | readout reason: data are sky-brightness samples per detector modelled as signal plus noise, with no individual particle or event object | none | none | a per-event label invented for samples | none | none |
| Uncertainty/quality | sourced | astro-ph/0412517 Sec. "Covariance of the output map"; 0904.3623 Sec. "Derivation", "Conclusions"; astro-ph/0501504 Sec. "Conclusions"; 1103.2281 Sec. "Dipole calibration" | map covariance; six residual components; null-space handling by a zero-sum constraint; gain error from Fisher term | C_m; rcond; residual map; sigma_g | residual split into components with analytic estimates for three | pixelisation noise from sub-pixel signal, biasing power spectra unless corrected | none | none |

Variant and condition gaps:

- Modulation (for example a modulator in the optics): nothing read; no hit covers it. 1103.2281 and 0904.3623 use scan-driven angle change only.
- Filtering and transfer function: not covered. These sources solve baselines rather than filter. Filtering out real signals and signal injection before filtering remain gaps.
- Ground and balloon scan strategies: not read. Sources are satellite-like.
- Beam and bandpass: beams idealized or symmetric; asymmetric effects are deferred by astro-ph/0501504 and deconvolution papers were not read. Bandpass mismatch not read.
- Shared and cross-detector noise: 0904.3623 has a part on correlations between detectors that was not read. No method claimed.
- Time-domain preparation of detector data (pointing reconstruction, glitches, waveform level): not read, and BP01 is not supported by these sources.
- Noise estimation from data: named as needed in astro-ph/0501504, not given.
- Map combination across experiments: not covered.

Null modes and averaging: destriping's matrix is singular. astro-ph/0501504 states an explicit zero-sum condition; 0904.3623 solves orthogonal to the null space, and says this holds exactly only when no pixels are excluded. So a stated constraint is what fixes the offset, not added data. This agrees with W7. Coadding repeated circles into rings is used by these sources, equivalent to uncoadded destriping only for ideal scanning (0904.3623 Sec. "Ring set or not"), so a coadded product must carry that condition. It is not the naive chunk average that W7 forbids.

Signature facts: representation (timestream or coadded rings); pointing and polarization angle psi; scan strategy (spin, repointing, crossings); noise model (white level, knee, slope, prior or none, stationarity intervals); calibration (gain, calibrator); beam treatment; pixelization; solver and baseline length; excluded pixels; null modes named. 5.15: BP13 scan settings; BP14 pointing plus timestream.

Applicability: `timestream && pointing && scan_crossings_sufficient && (noise_spectrum_known || baseline_model_declared) && calibration_known`; polarization: `&& polarization_angle && (at_least_3_distinct_angles_per_pixel || pixel_excluded)`; offset: `&& null_mode_constraint_declared`; gain: `&& (multiple_detectors || polarization_handled_declared)`.
Stays unknown: monopole; pixels below the condition limit; a map noise claim without a noise model; signal transfer where filtering was applied.
Recognition: positive, TOD with pointing and detector angles. Negative, a pre-averaged normalized map with no pointing or noise description, offered for global combination.

## Sources and plan comparison

Plan statements checked against sources: none contradicted. Three need a scope note.

1. W7 retarding subcase and the F36 negative case. KATRIN does sum counts at like steps and averages qU over 274 scans before fitting. It does so after stability and reproducibility checks, keeps per-scan conditions for MC twins, and carries a stacking uncertainty. Stacking is thus allowed when those conditions are shown; the plan's wording reads stricter than this.
2. BP13 says sidebands enter the CRES response. In the Project 8 response read, sidebands are undetected and have no term in the spectrum model; they act through carrier power, SNR and effective volume.
3. BP14 and W7 on naive averages. Coadding into rings is a legitimate source method under the ideal-scanning condition above.
