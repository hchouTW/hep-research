# Detector Comparison Tables

Reusable, qualitative comparison tables under one set of definitions
([46](46-performance-metrics-and-residual-diagnostics.md)). Entries give mechanism and
scaling, not performance numbers; a numeric performance claim requires the apparatus,
configuration, phase space, conditions, and source ([13](../../research-communication/references/13-sources.md)). Abbreviations
are defined in [50](50-detector-glossary.md).

## Table 1: Master detector table

| Family | Interaction / medium | Direct observable | Inferred quantity | Calibration | Alignment / conditions | Local object | Ambiguity | Resolution terms | Inefficiency / fakes | Validation | Systematics |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Hybrid pixel | ionization in Si | charge, ToT, hit | position, vertex | threshold, gain, Lorentz angle | module alignment, temp, dose | cluster | merged clusters | pitch, sharing, scattering | dead/noisy pixels, merged | overlaps, tag-probe | alignment, dose, Lorentz angle |
| Silicon strip | ionization in Si | 1D charge | 1D position | gain, common mode | alignment, stereo | cluster | ghosts | pitch, noise | ghosts, noise | tag-probe, residuals | alignment, noise |
| MAPS/DEPFET/CCD | ionization in Si | charge | position | pedestal, threshold | alignment | cluster | integration-time | diffusion, pitch | rolling readout | overlaps | timing association |
| Drift chamber/tube | ionization in gas | drift time | radius, position | `t0`, `r(t)`, gain | wire position, sag | drift circle, segment | left-right | diffusion, ionization statistics | cell edges, delta rays | residual vs distance | `t0`, `v_d`, alignment |
| TPC | ionization in gas/liquid | 3D charge + time | 3D track, `dE/dx` | `v_d`, gain, lifetime | field map | cluster, track | `t_0` | diffusion, MS | distortions, merging | laser, cross-detector | distortion map |
| MWPC/straw | gas avalanche | wire hit / time | position | gain, `t0` | wire pos. | hit, straw circle | left-right | pitch, drift | edges, streamer | plateau scan | efficiency vs rate |
| RPC/MRPC | gas gap streamer | strip time | position, time | `t0`, HV plateau | strip alignment | hit cluster | multi-hit | gap, rate | rate-dependent | cosmics | rate |
| GEM/Micromegas | micropattern gas | pad/strip charge | position, angle | gain map | alignment | cluster | angle | pitch, diffusion | discharges | test beam, cosmics | gain, rate |
| Scintillating fiber | scintillation | amplitude | position | gain, attenuation | mapping | hit | stereo ghosts | pitch, sharing | crosstalk, dark counts | MIPs | attenuation, dose |
| Emulsion | grains | grain positions | track/vertex | scanning | layer alignment | base-track | no timing | grain size | overlap | through tracks | fading, distortion |
| TOF / timing layers | scintillation, gas gap, Si gain | time | `beta`, `m^2`, time | `t0`, walk | clock, path | hit, track time | multi-hit | jitter, photostat, clock | wrong bunch | muons | offsets |
| LGAD / MCP | gain in Si / channels | time | time | gain, walk | fluence | hit time | multi-hit | Landau, jitter | fill factor | MIPs | dose |
| RICH / DIRC / TOP | Cherenkov light | photon hits (+ time) | `beta`, species | index, mirror, gain | alignment, `T/P` | ring / arc | photon-path | emission, chromatic | low `N_pe`, background | kinematic PID | index, aging |
| Threshold / differential Cherenkov | Cherenkov light | photon counts | species (thresholds) | index, gain | `T/P` | counter response | near threshold | photostat | dark counts | known-species | index stability |
| TRD | transition radiation | X-ray + `dE/dx` in gas | `e/h` | gain, pressure | alignment | layer likelihood | overlap of `dE/dx` and TR | absorption stat | high `p` | `e`/`h` samples | gas, gain |
| `dE/dx` | ionization | charge samples | species | gain, path | field | truncated mean | band overlap | Landau, samples | saturation | tag samples | gain drift |
| ECAL (crystal/sampling) | EM shower | charge/light | `E`, position | intercalibration, scale | geometry, material | cell, cluster | overlap | stoch., noise, const. | leakage, conversions | `Z->ee`, `pi^0`, `E/p` | scale, material |
| HCAL | hadron shower | charge/light | `E`, position | EM scale, response | geometry | cluster | `e/h` | stoch., leakage | leakage | single hadron, jets | JES |
| Muon system | ionization in gas | hits | `p`, `q`, ID | `t0`, gain | alignment, field | segment | left-right | MS, spatial | punch-through | `Z`, `J/psi`, cosmics | alignment, charge misID |
| Noble-liquid TPC | scintillation + charge | `S1`, `S2` | `E`, position, ID | lifetime, light map | field | pulse, vertex | pairing | recomb., stats | pileup, wall | sources | lifetime, threshold |
| Water / scintillator | Cherenkov / scintillation | charge, time | vertex, `E`, ID | PMT gain, optics | medium | ring / hit | ring counting | optics | containment | Michel, `pi^0` | optics, nuclear model |
| Bolometer / semiconductor | phonons / ionization | pulse | `E`, recoil type | energy scale | thermal | pulse | noise | statistics, noise | threshold, surface | lines | threshold |
| Air-shower / IACT / neutrino telescope | atmosphere / ice / water optics | sparse samples | direction, energy, mass | atmosphere, optics | geometry | footprint / image / hit pattern | topology | sampling | acceptance | hybrid, star tracker | atmosphere, ice |

## Table 2: Tracking-technology comparison

| Technology | Info topology | Position mechanism | Ambiguity | Material | Rate | Radiation | Distinctive tail |
|---|---|---|---|---|---|---|---|
| Hybrid pixels | 2D points | charge sharing | merged clusters | moderate | high | tolerant with design | delta rays |
| Strips | 1D points | interpolation | ghosts | low | high | moderate | ghosts |
| MAPS | 2D points | charge diffusion | integration time | very low | moderate | improving | timing |
| Drift chamber | radii | drift time | left-right | low | limited | aging | late clusters |
| TPC | 3D image | drift time + pads | `t_0` | very low | limited (ion backflow) | not for silicon dose | distortions |
| Straw | radii | drift time | left-right | low | moderate | aging | delta rays |
| MWPC | wire hits | wire pitch | crossing | low | limited | aging | streamers |
| RPC | strip hits | strip pitch | multi-hit | moderate | limited by resistivity | moderate | afterpulses |
| GEM/Micromegas | pad images | centroid | angle | low | high | discharge | discharges |
| Fibers | amplitude points | fiber pitch + sharing | stereo ghosts | moderate | high | SiPM dose | dark counts |
| Emulsion | 3D micro image | grains | none (no time) | none | very low | fluence | overlap |

## Table 3: Timing-technology comparison

| Technology | Time mechanism | Dominant term | Rate | Radiation | Association risk |
|---|---|---|---|---|---|
| Scintillator + PMT/SiPM | scintillation | photostat + electronics | high | SiPM dose | position along bar |
| MRPC | gas gap avalanche | gap, jitter | limited | moderate | multi-hit |
| LGAD | gain in thin Si | Landau + jitter | high | gain loss | fill factor |
| MCP | channel gain | transit spread | moderate | aging | rate droop |
| Tracker time | drift/pulse | sensor + `t0` | as tracker | as tracker | bunch assignment |
| Calorimeter time | shower pulse | pulse shape | as calo | as calo | shower depth, walk |

## Table 4: PID comparison

| Method | Discriminates by | Effective momentum range | Main degeneracy | Main systematics | Non-Gaussian caveat |
|---|---|---|---|---|---|
| `dE/dx` | ionization vs `beta gamma` | low, and rise region | band crossings, saturation | gain, path | Landau tail |
| Cluster counting | cluster number | broader | cluster merging | cluster resolution | Poisson |
| TOF | `beta` | low `p` (`~1/p^2`) | `t_0`, path | clock, path | late tails |
| RICH / Cherenkov | Cherenkov angle | mid to high `p` | saturation | index, alignment | low `N_pe` |
| DIRC / TOP | angle + time | mid `p` | photon-path | optics | multi-path |
| TRD | transition radiation | `e/h` at high `gamma` | `dE/dx` overlap | gas, gain | tail |
| Calorimetry | `E/p`, shower shape | `e/gamma`, hadrons | overlap | scale, material | shape tails |
| Muon system | penetration | mid to high `p` | punch-through | alignment | charge tail |

## Table 5: ECAL / HCAL technology comparison

| Type | Medium | Stochastic term origin | Advantage | Limitation | Signature systematic |
|---|---|---|---|---|---|
| Homogeneous crystal / lead-glass | full active | photostatistics | best energy resolution | cost, radiation, light yield drift | light-yield/temperature |
| Sampling (Pb/scintillator, LAr, Si, gas) | absorber + active | sampling fluctuation | compact, granular, depth segmentation | worse resolution | sampling fraction, calibration |
| Scintillator-tile HCAL | iron/steel + tile | sampling + `e/h` | robust | non-compensation | leakage, `e/h` |
| Liquid-argon | absorber + LAr | sampling | stable, uniform | cryogenics, signal shaping | lifetime/purity |
| Compensating | tuned `e/h ≈ 1` | reduced invisible | linear | complexity | tuning |
| Dual readout | scintillation + Cherenkov | separates EM/nonEM | corrects EM fraction | light sharing | calibration of both channels |
| Digital / semi-digital / imaging | binary/multi-threshold cells | count of cells | particle-flow ready | saturation at high density | threshold |
| Preshower / shower-max | fine sampling | | position, `pi^0` separation | material | alignment |
| Forward / zero-degree | hadron/EM | | beam-fragment measurement | radiation | dose, calibration |

## Table 6: Calibration vs alignment vs reconstruction vs performance vs validation vs systematics

| Concept | Question answered | Output | Data or simulation | Typical mistake |
|---|---|---|---|---|
| Response | what does the detector do? | mean/distribution of `y|x,theta` | both | equated with calibration |
| Calibration | which constants map `y` to physical units? | gains, `t0`, scales | data (with MC) | tuned on the measured observable |
| Alignment | where are the elements? | positions, rotations, deformations | data | conflated with timing/drift calibration |
| Reconstruction | what objects best explain `y`? | hits, tracks, clusters | both | treated as truth |
| Performance measurement | how good is it? | `eps`, `P`, `sigma`, bias | MC truth; data proxies | denominators unstated |
| Validation | does the model match data? | agreement/closure | data vs MC | 1D agreement only |
| Systematic uncertainty | what is the uncertainty from remaining freedom? | `V_x`, `J` | both | double counting, arbitrary envelopes |

## Table 7: Detector-specific reconstruction/performance

| Family | Natural residual | Essential plot | Failure signature | Community efficiency convention |
|---|---|---|---|---|
| Pixels/strips | unbiased hit residual | residual vs angle, cluster size | offset, ghosts | hit efficiency from overlaps/tracks |
| Drift | residual vs drift distance | `r(t)` residual | left/right offset | per-layer efficiency vs distance |
| TPC | cluster-track residual | residual vs `(r, z, rate)` | distortion | tracking efficiency vs `p`, `eta` |
| MPGD | residual vs angle | gain map | discharges, angle bias | plateau scan |
| Fibers | residual vs position along fiber | amplitude vs position | attenuation | per-channel efficiency |
| Emulsion | slope/position agreement | link efficiency | fake links | scanning efficiency |
| TOF/timing | time residual vs species | time vs amplitude/run | walk, offset | core width + tail |
| RICH/DIRC | photon-angle residual | angle vs `p` | index shift | efficiency/mis-ID at a likelihood cut |
| TRD | layer likelihood | `e`/`h` rejection vs efficiency | gas/gain drift | rejection at fixed efficiency |
| ECAL | `E/p`, `Z->ee` mass | scale vs `eta`, `E` | material/nonlinearity | resolution from `Z` line shape |
| HCAL/jets | response vs `pT`, flavor | JES closure | non-compensation | response and `sigma_68` |
| Muon | mass/`q/p` vs `q*eta` | dimuon mass maps | weak modes | tag-and-probe; charge misID |
| Noble liquid | charge/light vs `z`, time | lifetime | purity drift | threshold efficiency |
| Rare-event | line scale, leakage vs `E` | leakage plot | wall events | threshold and fiducial efficiency |

## Table 8: Systematics mapping

The general mapping (scale, resolution, efficiency, alignment/field, material, drift,
noise/pileup, dead channels, mis-ID, trigger, response, background) is in
[47](../../hep-analysis/references/47-validation-systematics-and-combination.md); this table adds only the nuisances
specific to specialized detectors.

| Nuisance | Reconstructed effect | Physics effect |
|---|---|---|
| Gain/pedestal | energy/charge scale | mass, yields |
| Time offset | time, `beta`, drift coordinate | PID, momentum |
| Optical attenuation | light yield vs position | energy scale, resolution |
| Refractive index | angle, threshold | PID |
| Electron lifetime | charge vs depth | scale, threshold |
| Atmospheric profile | shower energy/`X_max` | flux, composition |
| Ice/water optics | angular/energy | effective volume, flux |

## Table 9: Specialized and auxiliary detectors

| Detector | Signal | Reconstructs | Distinctive concern |
|---|---|---|---|
| Neutron detectors | recoil/capture | neutron flux, energy (TOF) | gamma discrimination, efficiency model |
| Forward proton / Roman pots | position near the beam | proton momentum loss `xi` | beam optics, alignment to the beam, pileup |
| Beam position / loss / profile monitors | induced signal, ionization | beam parameters | calibration, dynamic range, bunch structure |
| Luminosity detectors | coincidence/hit counts | luminosity | linearity, pileup correction, aging ([19](19-triggers-luminosity-pileup.md)) |
| Trigger detectors / primitives | coarse hits | trigger decision | turn-on, bias, latency |
| Cosmic vetoes / active shielding | scintillator/RPC | veto flag | dead time, accidental veto rate |
| Polarimeters | asymmetry | polarization | analyzing power, systematic on asymmetry |
