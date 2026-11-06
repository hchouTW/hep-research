# T11: design cells, first pass (27 of 38 families)

State: in progress, not done. Covers the families with plugin text. Written from the plugin tree and the plan only, nothing from memory and nothing run. F21, F24, F26-F28 and F33-F38 have no plugin text and need sources (R14).

Result: 189 cells, 167 documented, 21 `gap-method`, 1 not-applicable (F14 space/time, a readout reason). Every anchor was resolved against the baseline headings. Cells marked `source-unverified` name a source the plugin cites that nobody has re-read here, so T11 cannot be done while they remain (R14). Documented means text exists, not that anything runs: most bindings are `none`.

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
