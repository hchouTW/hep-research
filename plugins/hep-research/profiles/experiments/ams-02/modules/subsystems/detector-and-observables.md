# AMS-02 Detector Response Chains and Observables

## When to read this file

Read for any question about what an AMS-02 subsystem measures, how an observable is defined, or which subsystem may be used for which quantity. This is the canonical location for observable definitions, conversions, and the subsystem matrix; other references link here instead of restating them. Only a few public performance values are given, each with its context: see [Source discipline for this file](#source-discipline-for-this-file).

## Contents

1. [Content contract used in this file](#content-contract-used-in-this-file)
2. [Core observables and conventions](#core-observables-and-conventions)
3. [Tracker and permanent magnet](#tracker-and-permanent-magnet)
4. [TOF](#time-of-flight-tof)
5. [TRD](#transition-radiation-detector-trd)
6. [ECAL](#electromagnetic-calorimeter-ecal)
7. [RICH](#ring-imaging-cherenkov-detector-rich)
8. [ACC](#anti-coincidence-counters-acc)
9. [Observation environment](#observation-environment)
10. [Cross-subsystem matrix](#cross-subsystem-matrix)
11. [Source discipline for this file](#source-discipline-for-this-file)
12. [Failure modes / Required source classes / Questions to ask](#failure-modes)

## Content contract used in this file

Each subsystem section gives, in order: **Purpose, Inputs, Definitions, Mechanism (response chain), Procedure, Dependencies, Validation, Failure modes, Uncertainties, Evidence, Output.** Where a field adds nothing beyond a linked canonical rule it is folded into the chain. Response chain for every subsystem:
`physical interaction → raw detector signal → calibrated channel quantity → reconstructed object → analysis observable → selection/template/likelihood use`.

## Core observables and conventions

| Quantity | Definition (units) | Convention / validity |
|---|---|---|
| Rigidity | `R = pc/(Ze)`; in practice `R[GV] = p[GeV/c] / Z` for charge `Ze` | Signed: `sign(R) = sign(Z)` under a stated bending convention (which projection, field direction, and fit orientation define "positive"). Analyses quote `|R|` for flux and `R` for charge-sign work |
| Momentum | `p = |Z| |R| / c` (GeV/c if `R` in GV, `Z` in units of e) | Never call `R` momentum. Helium at `R = 10 GV` has `p = 20 GeV/c` |
| Total / kinetic energy | `E = sqrt(p^2c^2 + m^2c^4)`, `T = E - mc^2` | Needs mass hypothesis. ECAL measures deposited/reconstructed shower energy, a separate estimator |
| Kinetic energy per nucleon | `T/A` | Needs mass number `A` (or isotope composition model). For an elemental flux, state the assumed `A` or the mixture and its uncertainty |
| `|Z|` | Estimated from energy loss / photon yield, `dE/dx ∝ Z^2` for the same `β` | Separate from sign. Tracker, TOF, RICH give estimators that are not identical observables |
| Velocity | `β = v/c` from TOF timing over a path length, or from Cherenkov angle `cosθ_c = 1/(nβ)` | TOF and RICH cover different ranges; the fitted-hypothesis `β` inside a track fit is not a measurement |
| Mass | `m = |Z| |R| / (γ β c)` → in GeV/c^2 with `R` in GV | Ill-conditioned as `β → 1`; see below |
| Flux | Differential: particles per (area·solid angle·time·rigidity or energy unit) | Bin-integrated vs differential must be stated; see [charged-cosmic-rays](../species/charged-cosmic-rays.md) |
| Geomagnetic cutoff | Minimum rigidity for a particle to reach the location from outside, from a field model | Model, safety factor, direction, position and time all matter |

**Mass uncertainty propagation.** With `ln m = ln|Z| + ln|R| - ln(βγ)` and `d ln(βγ) = γ^2 dβ/β`:
`(δm/m)^2 = (δR/R)^2 + (γ^2 δβ/β)^2 - 2 ρ (δR/R)(γ^2 δβ/β) + (δZ/Z)^2` where `ρ` is the correlation between the rigidity and velocity errors when they share information (usually assumed zero; verify). When `Z` is an integer assignment, `δZ` is a misassignment issue, not a Gaussian term. The `γ^2` factor makes the mass term blow up at high `β`, which is why isotope separation is limited in rigidity for a given `β` resolution (see [nuclei-and-isotopes](../species/nuclei-and-isotopes.md)). Validity: small errors, negligible non-Gaussian tails; tails and rigidity-velocity correlations must be validated, not assumed.

**Dependency of variables.** A rigidity-binned flux and a kinetic-energy-per-nucleon-binned flux are different measurements; converting the bin edges is not the same as unfolding into a new variable when response is non-trivial.

## Tracker and permanent magnet

**Purpose.** Signed rigidity, `|Z|`, direction; the only charge-sign source. **Inputs.** Silicon strip signals in multiple layers inside/around a permanent magnet, alignment constants, field map, hit efficiency maps. **Mechanism (chain).** Charged particle ionizes silicon → strip charge → cluster (with charge-sharing position estimation) → hit coordinates on layers → track fit with field → curvature → `R`; cluster amplitudes → `|Z|` estimate.

- **Charge sign.** Sign of curvature in the bending projection. Define which coordinate is the bending projection and the field convention. Charge confusion arises when curvature is measured with the wrong sign (see Failure modes).
- **Rigidity resolution.** At low `R` dominated by multiple scattering (`δR/R` roughly independent of `R` and growing with lower `β`), at high `R` by spatial resolution and alignment (`δR/R ∝ R`). The crossover and the **maximum detectable rigidity** (MDR, where `δR/R = 1`) depend on the track configuration and definition; never quote a universal MDR (the value published for \|Z\| = 1 with the full L1-L9 span is in the documented-values table below). `hep-analysis` script `multiple_scattering.py` gives a design-level estimate only.
- **Track configurations.** Inner-tracker vs full-span vs other subsets of layers give different lever arm, resolution and acceptance. Do not assume unpublished layer requirements; take the configuration definition from the user or the analysis paper.
- **`|Z|` from energy loss.** Cluster amplitude vs path length (angle-corrected), with saturation/nonlinearity, layer-by-layer consistency, and Landau-like fluctuations. Charge estimator resolution is `Z`-dependent and tails feed adjacent-element leakage.
- **Procedure for using the Tracker in an analysis.** (1) Fix the track definition; (2) validate hit efficiency and inactive/noisy channels vs time; (3) validate alignment hierarchy and time dependence; (4) validate the rigidity scale with a physical control (redundant measurement or a known-momentum reference: not just MC agreement); (5) check residuals and fit-quality tails; (6) check consistency of independent partial fits (e.g. upper vs lower track segments, where the configuration permits); (7) propagate the resolution function (including tails) into the response.
- **Dependencies.** Alignment (see [calibration-mc-systematics](../methods/calibration-mc-systematics.md)), field map/temperature, TOF (direction, trigger), ACC (side entry), material and secondary interactions (delta rays, fragmentation).
- **Validation.** Residual distributions per layer/region/time; rigidity-scale test; charge-sign consistency of partial fits; ratio of forward/backward-going track configurations. **A charge-confusion estimate that uses only the Gaussian core of `δR/R` is rejected;** request a data-driven or calibrated-simulation tail check.
- **Uncertainties.** Rigidity scale (a shift moves events across bins; effect on steep spectra is amplified by the local spectral index), resolution function including tails, hit efficiency, alignment, magnetic field map, fragmentation and delta-ray contamination.
- **Output.** A resolution function `P(R_meas | R_true, |Z|, config)` including tails and a charge-confusion migration matrix, each with a validation plan.

## Time of Flight (TOF)

**Purpose.** Trigger, direction (down- vs upward-going), `β` at suitable velocities, `|Z|` from energy loss, albedo rejection. **Mechanism.** Particle deposits energy in scintillator paddles → light collected by PMTs → channel time and amplitude → hit formation → path-length-corrected time of flight between planes → `β`, direction; amplitudes → `|Z|`.

- **Definitions.** `β = L / (c Δt)` with `L` the fitted path length between planes and `Δt` the corrected time difference; the sign of `Δt` gives direction. Slewing (amplitude-dependent time offset) and per-channel time offsets require calibration; multiple hits and accidental hits need explicit treatment.
- **Procedure.** Calibrate offsets/slewing/path length; require consistency among planes and with the fitted Tracker trajectory; measure TOF efficiency separately from the trigger logic when needed; validate upward/downward misassignment and slow-particle tails.
- **Limits.** TOF `β` resolution degrades in relative terms as `β → 1`; it is not an isotope discriminator at high `β`. RICH is the higher-`β` velocity source (see below).
- **Failure modes.** Downward-going/upward-going confusion (albedo enters flux at low `R`); accidental hits shifting `β`; slewing miscalibration mimicking a mass shift; correlated errors between TOF `β` and the Tracker fit (shared trajectory).
- **Output.** `β` resolution function (with tails), direction misassignment probability, `|Z|` estimator response, trigger/timing efficiency as conditional efficiencies (see [efficiency-acceptance-backgrounds](../methods/efficiency-acceptance-backgrounds.md)).

## Transition Radiation Detector (TRD)

**Purpose.** Lepton/hadron separation at momenta where a transition radiation signal is present; also ionization for `|Z|`-related information. **Mechanism.** Relativistic particle crosses radiator layers → transition radiation X-rays (yield depends on Lorentz factor `γ`, not on momentum alone) → absorbed in gas straws with ionization; layers in series give many samples of energy deposition → per-layer likelihoods or template observables → global discriminant.

- **Roles.** Strong `e`/`p` separation (species-level inference of `γ`), supporting `|Z|` for nuclei. **Never a standalone charge-sign detector**; it must be combined with the Tracker charge sign for `e+` vs `e-`.
- **Calibrations.** Gas conditions (composition, pressure, temperature), gain, spatial/time calibration, path length in gas, Tracker-TRD matching, missing layers.
- **Validation.** Separate training/calibration samples from fit samples; check template dependence on rigidity/energy; check proton tails inside lepton-selected samples using orthogonal selections; distinguish a cut-based use (threshold on a discriminant) from a template-fit use (discriminant shape in bins).
- **Failure modes.** Time-dependent gas/gain response producing time-dependent rejection; templates mismatched at high `R` where hadron `γ` grows and their transition radiation turn-on appears; data-MC mismatch of the discriminant shape being absorbed into the background estimate.
- **Output.** A discriminant with a documented training sample, a rejection-versus-efficiency curve on independent control data, and a time/rigidity stability plot. **No rejection number is quoted here**: public numbers depend on efficiency and selection context; see [source-index](../../evidence/index.md).

## Electromagnetic Calorimeter (ECAL)

**Purpose.** 3D shower imaging, electromagnetic energy, e/p discrimination, photon/lepton direction. **Mechanism.** Incident particle initiates a shower in a lead/scintillating-fiber sampling structure → light in cells → calibrated cell energies → cluster and 3D axis → energy estimator, longitudinal/lateral shape variables → classifier or template use.

- **`E/|p|` and `E/|R|`.** For an electron, `E_ECAL ≈ p c` (electron mass negligible), so `E/(|Z|·|R|)` (energy in GeV, `R` in GV, `Z = 1`) is near unity within resolution, bremsstrahlung and leakage. For a proton, the ECAL response is a hadronic fraction so `E/p < 1` on average with wide tails. For helium or heavier nuclei `E/R = 1` has no physical basis: `p = |Z|R/c` and hadronic response is species-dependent. State `Z` explicitly in any `E/R` variable.
- **Procedure.** Calibrate cell gains and energy scale; validate linearity and containment/leakage (shower near edges, dead material); match shower axis to Tracker track; define a shower-shape classifier and validate its hadronic tails in electron-like regions; state whether ECAL is used as the final energy estimator, a selector, or a fit observable.
- **Effects.** Photon conversion and bremsstrahlung upstream change the Tracker vs ECAL relation; hadronic showers with a large electromagnetic component (charge exchange, `π^0`) fake electrons; saturation/nonlinearity at high energy.
- **Validation.** Independent-sample energy scale check (physically motivated control, e.g. `E/p` in a pure-lepton sample); shower-shape data/MC agreement quantified per variable and per energy; classifier stability versus time, energy, incidence angle.
- **Failure modes.** ECAL variables used both to select and to define the template that measures the selection efficiency (circularity); correlated inputs (shower shape and `E/p`) double-counted.
- **Output.** Energy response function (with leakage tail), classifier-efficiency and background-efficiency curves on control data, matching-efficiency plot versus energy/geometry.

## Ring Imaging Cherenkov Detector (RICH)

**Purpose.** Precise `β` above the range where TOF resolution is adequate; charge from photon yield; combined with `R` gives mass. **Mechanism.** Particle above Cherenkov threshold in a radiator emits a cone at `cosθ_c = 1/(nβ)` → photons propagate to a photo-sensor plane → hits → ring reconstruction using the Tracker-extrapolated track → `β`; photoelectron count `∝ Z^2` (times a `β`-dependent factor) → charge.

- **Radiators.** The instrument has two radiator types with different indices, giving different velocity thresholds and coverage; the exact refractive indices, tile counts and boundaries must come from the public detector description (see [source-index](../../evidence/index.md)) rather than memory. Hits near tile boundaries and reflected photons need dedicated treatment.
- **Resolution propagation.** `δβ/β = tan θ_c δθ_c` at fixed `n`; mass resolution follows the formula above, with `γ^2` amplification. Ring quality, expected photoelectron count consistency, and Tracker extrapolation error all contribute.
- **Procedure.** Calibrate refractive index and alignment; require ring containment and quality; check expected-vs-observed photoelectrons; decide whether charge-estimator consistency with Tracker/TOF is required; treat accidental hits.
- **Validation.** `β` residuals versus rigidity for a species with known mass (e.g. abundant `Z = 1` singly charged particles at high `β`); ring-quality distributions per radiator region; stability vs time (refractive index, temperature).
- **Failure modes.** Ring from a secondary particle; radiator boundary mis-assignment; `β` bias correlated with rigidity error.
- **Output.** `β` resolution function with tails, acceptance/efficiency as a function of `R` and geometry (region-dependent), and a mass template family with a stated `A`-dependence.

## Anti-Coincidence Counters (ACC)

**Purpose.** Veto particles entering through the magnet sides or otherwise outside the nominal acceptance, and reject events with extra activity. **Mechanism.** Scintillator panels around the Tracker → thresholded signals → veto decision at event level. Documented as a veto counter (see [source-index](../../evidence/index.md)); its efficiency number requires a source context.

- **Trade-off.** Tighter veto removes off-acceptance and shower-contaminated events but loses valid events with accidental or backsplash activity; this loss is an **efficiency** to be measured (see [efficiency-acceptance-backgrounds](../methods/efficiency-acceptance-backgrounds.md)), and the veto’s effect on **acceptance** must not also be included in the geometric acceptance (double counting).
- **Failure modes.** Backsplash from ECAL showers at high energy vetoing signal (energy-dependent inefficiency); accidental activity time-dependent with orbit/rate; hardware inefficiency creates false side-entering events.
- **Output.** A veto definition, a conditional efficiency, and a rigidity/energy/time dependence check.

## Observation environment

ISS operation defines the analysis conditions: **livetime** (exposure time when trigger and DAQ are live; not the calendar interval), **attitude/orientation**, **geomagnetic cutoff** varying along the orbit, **South Atlantic Anomaly and other high-background periods**, **solar activity**, and **long-term time dependence**. Include only trigger/DAQ/thermal specifics that a public source supports (see [source-policy](../sources/source-policy.md)); otherwise treat them as user-supplied inputs. See [reconstruction-and-data-quality](../methods/reconstruction-and-data-quality.md) for the conditions model.

## Cross-subsystem matrix

Wording refined from the task specification. "Supporting" information must not be presented as an independent measurement without evidence.

| Quantity | Tracker | TOF | TRD | ECAL | RICH | ACC |
|---|---|---|---|---|---|---|
| Direction | Primary/auxiliary (track direction) | Primary at suitable velocity (up/down) | Matching only | Shower axis | Ring/track consistency | No |
| Charge sign | **Primary (only source)** | No | No | No | No | No |
| `\|Z\|` | Yes | Yes | Limited/context-dependent | Not the standard nucleus charge estimator | Yes | No |
| `β` | Indirect, via fit hypothesis only | Yes | No | No | Yes | No |
| Lepton/hadron ID | Track/rigidity consistency (E/p with ECAL) | Supporting | Strong | Strong | Limited/context-dependent | Veto only |
| Side-entry veto | Geometry support | Limited | Geometry support | Shower support | Geometry support | Primary |

**Complementarity rules.** (1) Independent handles are only independent if they exploit different physics and do not share a fit or calibration: TRD (transition radiation) and ECAL (shower development) are largely different processes, but shower shape and `E/p` share the ECAL energy; Tracker `|Z|` and TOF `|Z|` share incident particle but not readout. (2) Charge-sign errors are a Tracker problem and cannot be fixed by lepton/hadron ID. (3) A quantity from one subsystem used in the selection biases that subsystem's efficiency measurement (see [efficiency-acceptance-backgrounds](../methods/efficiency-acceptance-backgrounds.md)).

## Source discipline for this file

Public detector descriptions exist in the Collaboration's detector web pages, subsystem NIM papers, and the Phys. Rept. Part II review; see [source-index](../../evidence/index.md) (S01, S17-S19). Web-page headline figures (rejection, resolution) lack selection context, so they are not reproduced.

**Documented values with context** (full-text-verified in the main articles of S04, S05, S06, S08; claim C21; \|Z\| = 1 particles and the nine-layer tracker in those analyses; a number outside its context is not an AMS performance claim):

| Quantity | Value in those papers | Context |
|---|---|---|
| Maximum detectable rigidity | 2 TV | \|Z\| = 1, 3 m lever arm L1 to L9 (L1 at top, L2 above the magnet, L3-L8 in the bore, L9 above the ECAL) |
| Tracker charge resolution | ΔZ = 0.05 | \|Z\| = 1, inner tracker (S06, S08) |
| TOF velocity resolution | Δβ/β² = 4% | \|Z\| = 1 (S08) |
| RICH velocity resolution | Δβ/β = 0.1% | \|Z\| = 1 (S08); isotope papers quote Gaussian-core widths per radiator (C28) |
| ACC side-entry rejection efficiency | 0.99999 | quoted in S08 |
| ECAL | 17 radiation lengths, 3D imaging | S04 (claim C50; more detail in the review table below, C71) |
| TRD estimator | per-layer log-likelihood ratio Λ_TRD (e hypothesis over p or p̄ hypothesis) | S08, S04 |

**Review-level values (S01, Phys. Rept. 894, chapter 1, read in full text 2026-09-21; scope is the review of the first seven years, claims C63-C73).** [Documented] Each row keeps its claim's scope; none is a general performance figure.

| Quantity | Value | Claim and scope |
|---|---|---|
| Tracker MDR (L1-L9) | 2.0 TV p, 3.2 TV He, 3.7 TV C, 3.4 TV O, 3.7 TV Fe; resolution ΔR/R = 0.1 below 20 GV | C63, nine-layer configuration |
| Electron charge confusion | below 8% up to 1 TeV, after TRD and ECAL selection | C65, electrons only |
| TRD proton rejection | above 1000 at 90% e± efficiency, 2-200 GeV/c; better at 65% efficiency | C67, that selection and range only |
| ECAL proton rejection | Λ_ECAL with E/p > 0.7; a further factor about 3 at 65% versus 90% e± efficiency (curve is a figure) | C72, 1-2000 GeV/c |
| TOF velocity | Δ(1/β) = 4% (Z = 1), 2% (Z = 2), 1% (Z > 6); direction confusion about 1e-9 (Z = 2 sample) | C68 |
| RICH | β thresholds 0.75 (NaF) and 0.953 (aerogel); velocity better than 0.1% at β about 1 for \|Z\| > 1 | C70; the analysis papers' 0.1% for \|Z\| = 1 is C21, so quote the Z range |
| ECAL | 17 X0, 9 superlayers, 1296 cells; angular resolution 0.3° at 1 TeV | C71; resolution curves not transcribed |
| Trigger and DAQ | electron level-1 efficiency 100% above 3 GeV; average DAQ efficiency 86%, about 600 Hz | C73; electrons only, typical values, not livetime inputs |

Rejection factors are selection- and efficiency-dependent: quote a number only with its efficiency, energy range and claim ID (C67, C72), otherwise stay with estimator distributions and template fits. Tracker charge resolution against Z (C66) and ECAL energy resolution (C71) are figure-only in the review; do not supply values. When a user needs another number, fetch the primary paper section, record definition and context in the ledger, and quote it with the context.

## Failure modes

- Treating the fitted-hypothesis `β` in a track fit as a `β` measurement.
- Quoting a universal MDR or a rejection factor without configuration and efficiency.
- Using Gaussian-core resolution for charge-confusion or misidentification estimates.
- Declaring the TRD or ECAL sensitive to charge sign; conflating `|Z|` with sign.
- Using an `E/R` variable for helium or heavier nuclei as if `E ≈ p`.
- Mass resolution computed from one term while ignoring `γ^2 δβ/β` growth or `R`-`β` correlations.
- Treating a subsystem's veto or selection as a fully independent measurement of the same quantity.

## Required source classes

Tier 1 AMS papers (Phys. Rept. Part II; PRL methods sections and supplements) for performance, definitions and configuration; Tier 2 detector papers (subsystem NIM A, official AMS pages) for geometry and mechanism; Tier 4 (PDG particle passage/kinematics reviews) for general formulas (Bethe-Bloch, Highland, Cherenkov, kinematics). Tier 5 (other experiments) only for comparison.

## Questions to ask the user

Which species and rigidity/energy range? Which track configuration (inner tracker vs full span)? Which data periods and hardware configuration? Is this a detector-level, object-level or flux-level question? Do they already have resolution functions or only nominal values? Public paper or internal work?
