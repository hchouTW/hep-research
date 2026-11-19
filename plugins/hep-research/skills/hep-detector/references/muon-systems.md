# Muon Systems: Spectrometers, Identification, and Trigger

Muon detection and reconstruction: drift-tube, cathode-strip, RPC-, GEM-, and
Micromegas-based chambers; standalone, combined, segment-tagged, calorimeter-tagged, and
trigger-level muons. The PID summary is in [particle identification](particle-identification.md);
technology physics is in [gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md);
alignment weak modes in [calibration and alignment](calibration-and-alignment.md) and
[tracking and vertexing](tracking-and-vertexing.md). Environment codes used here: COL collider;
UGD underground, neutrino and rare-event; GND ground-based cosmic-ray and gamma-ray arrays.
Atmospheric-muon rejection in neutrino telescopes (upward-going selection, containment and veto regions,
self-veto) is in [neutrino astronomy](neutrino-astronomy.md#backgrounds).

## Why muons are special

Muons are close to minimum-ionizing, rarely shower below a few hundred GeV, and
traverse the calorimeters, so the outermost layers see them nearly free of other
particles. Radiative losses (bremsstrahlung, pair production, photonuclear) equal ionization near
the muon critical energy (a few hundred GeV in iron) and dominate at TeV energies, so catastrophic energy losses and accompanying showers in the
absorbers must be expected and modelled. A muon system therefore
does two jobs: identification (it is the layer that survives absorbers) and an
independent momentum measurement at large lever arm, often in its own field.

## Reconstruction chain

1. **Chamber hits** (drift time -> radius; strip/pad charge centroid; RPC strip time).
2. **Segments**: line fit per chamber station (direction and position), resolving
   left-right ambiguity and rejecting delta-ray and noise hits.
3. **Standalone track**: link segments across stations through the spectrometer field,
   fit with material (multiple scattering, energy loss in absorbers).
4. **Extrapolation and matching** to the inner tracker: propagate the tracker track
   through calorimeter material (energy loss, scattering) to the muon system; match by
   position/direction with the extrapolated covariance (a `chi^2` match, not a fixed
   cut only).
5. **Combined fit**: refit hits from both systems; the inner tracker dominates at low
   `p`, the muon system's long lever arm at high `p`. Resolution scales as (approximate)
   `sigma_pT/pT ≈ a pT (measurement) ⊕ b (multiple scattering)`
   ([tracking and vertexing](tracking-and-vertexing.md)).
6. **Trigger matching**: the hardware-level (coarse) muon candidate matched to the
   offline muon for the trigger efficiency ([triggers luminosity pileup](triggers-luminosity-pileup.md)).

**Muon types (definitions differ by community; state the one used).**
*Standalone*: muon-system track only. *Combined/global*: tracker + muon-system fit.
*Segment-tagged*: tracker track that extrapolates to at least one muon segment (recovers
low-momentum muons that do not reach far). *Calorimeter-tagged*: tracker track with
minimum-ionizing calorimeter deposit (recovers acceptance gaps). *Trigger-level*: coarse
online track. Each type has its own efficiency, purity, and momentum resolution.

## Performance and scaling

- **Resolution**: at low `p`, multiple scattering and energy-loss fluctuations in the absorbers and
  calorimeters upstream of the muon system dominate; at high `p`, spatial
  resolution and alignment of the muon stations limits the *sagitta*
  `s ≈ 0.3 z B L^2/(8 p_perp)`-like measurement (approximate, uniform field; `s` and `L`
  in m, `B` in T, `p_perp` in GeV/c, `z` the charge number; `p_perp` the momentum component
  perpendicular to `B` (`p cos lambda` for pitch angle `lambda`) and `L` the path length in
  the field projected on the bending plane: PDG RPP 2025, eq. 35.57, p. 108, eqs. 35.66 and
  35.68 (`L'`), p. 112; momentum error `∝ p^2 sigma_s`). High-momentum resolution is a **weak-mode/alignment** problem
  (see below).
- **Efficiency**: geometric gaps (cracks, support structures, feet), chamber
  inefficiency, matching and reconstruction inefficiency, quoted **per type and versus
  the detector's coordinates and momentum**; the binning variables and the reference
  sample are parameters to state. At a collider (COL): versus `eta`, `phi`, `pT`, with a
  tag-and-probe from `J/psi` and `Z -> mu mu`
  ([triggers luminosity pileup](triggers-luminosity-pileup.md)). Muon counters of
  ground-based and underground arrays and the outer muon vetoes of underground detectors
  (GND, UGD; PDG RPP 2025, secs. 35.6.6.1 and 36.3.1) need a reference sample of their
  own; no hep-detector page gives a method for it yet.
- **Rate capability**: drift tubes (long drift, space-charge and occupancy limits),
  cathode-strip chambers (high granularity, good for high rate), RPCs (fast, rate
  limited by resistivity), GEM/Micromegas (high rate, discharge risk)
  ([gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md)).
- **Charge sign**: from curvature direction; at high momentum the sagitta shrinks
  toward the alignment/resolution floor and **charge misidentification** grows; it is
  measured from the non-Gaussian tail of the curvature distribution, since a Gaussian
  extrapolation of the core underestimates it ([tracking and vertexing](tracking-and-vertexing.md),
  charge confusion); a weak-mode misalignment gives a *momentum-charge
  correlated bias*: `q/p` shifts by a constant offset, so `delta p/p` grows with `p` and
  flips sign with charge, mimicking a charge asymmetry.

## Backgrounds and fakes

- **Punch-through**: hadrons that leak through calorimeter absorbers; falls with
  absorber thickness, rises with hadron energy.
- **Decay in flight**: `pi/K -> mu nu` inside the tracker: a kinked track whose
  combined-fit `chi^2` is bad and whose tracker-muon momentum mismatch is large.
- **Accidental matches**: an unrelated segment (cavern background at a collider (COL),
  noise) matched to a tracker track; grows with rate.
- **Cosmic rays and beam halo** (COL): out-of-time or off-vertex muons; suppress with timing,
  vertex/impact parameter, and back-to-back topology. Outside a collider the same muons
  are the background to reject with a veto or an up-going selection (neutrino telescopes,
  PDG RPP 2025, sec. 36.3.2; [neutrino astronomy](neutrino-astronomy.md#backgrounds)), the
  source of cosmogenic backgrounds removed by a veto on the time correlation with the
  crossing muon (UGD; sec. 36.6.5), or the calibration source of a surface array
  ([ground-based detection arrays](ground-based-detection-arrays.md#surface-array-event-reconstruction)).
- **Hadron mis-identification vs reconstruction fake**: a pion identified as a muon
  (mis-ID, real object with wrong identity) is a different failure from a fake track
  ([performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)).

## Distinctive but generalizable reconstruction and performance features (muon system)

- **Topology**: sparse hits grouped into segments over a large lever arm; almost no
  other particles (clean but low redundancy).
- **Inverse problem**: momentum and charge from sagitta in a field with material
  between stations; degeneracy: alignment weak modes that leave `chi^2` nearly
  unchanged; curl, sagitta and twist modes add a curvature offset that shifts `q/p`
  charge-antisymmetrically, while a radial expansion is charge-symmetric (a momentum-scale
  error constant in `p`; [calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes)).
- **Objects**: segment, standalone, combined, tagged muon. **Informative
  residual/closure**: at a collider (COL), `Z -> mu mu` mass versus `eta`, `phi`, `pT`,
  and charge (`m` and `q/p` residual versus `q * eta`); in any spectrometer, cosmic-ray
  track splitting (upper/lower half fits) to expose sagitta bias.
- **Scaling**: `sigma_pT/pT ∝ pT` at high `p` (measurement-dominated), constant at low
  `p` (scattering); charge misID rises steeply with `pT`.
- **Conventions** (COL): efficiency measured with tag-and-probe at fixed working point and
  isolation; resolution from `Z` line-shape width or MC truth for the momentum range.
  Charge misID per muon comes from same-sign pairs of a resonance that decays to an
  opposite-sign pair (`Z -> mu mu` at a collider): with per-muon rates `c_i`, `c_j` a pair
  is same-sign with probability `c_i (1 - c_j) + (1 - c_i) c_j` (about `2c` for equal small
  rates), so fit `c` per bin to the background-corrected same-sign counts rather than
  quoting the same-sign fraction as the per-muon rate (the same pair model is fitted for
  `Z -> ee` in arXiv:1908.00005, sec. 9.2).
- **Tails**: wrong-segment link, decay-in-flight, delta-ray overlap, charge flip.
- **Dependence**: rate/occupancy (background hits), magnetic field map stability,
  chamber temperature/gas, alignment time-dependence.
- **Strongest data sample**: at a collider (COL), `Z -> mu mu` and `J/psi -> mu mu` (mass
  scale and resolution in bins) and collision tracks for alignment with external
  constraints; in any spectrometer, cosmic muons (split tracks; arXiv:1206.4071, sec. 6.2.1).
  For other muon detectors (the muon vetoes of underground detectors, the muon counters of
  air-shower arrays, muon rings in imaging Cherenkov telescopes; PDG RPP 2025, secs. 36.3.1
  and 36.2.2) the closure sample is a parameter: see
  [noble-liquid, neutrino and rare-event detectors](noble-liquid-neutrino-and-rare-event-detectors.md),
  [ground-based detection arrays](ground-based-detection-arrays.md#muon-detectors-radio-detection-and-wide-field-gamma-ray-arrays)
  and [imaging atmospheric Cherenkov](imaging-atmospheric-cherenkov.md).
- **Transfers**: sagitta-weak-mode and charge-dependent-bias reasoning to any
  spectrometer ([tracking and vertexing](tracking-and-vertexing.md)); **does not transfer**: the
  specific punch-through/absorber background model.

## Common misconceptions and failure modes

- **One "muon efficiency."** Reconstruction, identification, isolation, and trigger
  efficiencies differ, and each is conditional on the previous
  ([performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md)).
- **Trusting `chi^2` for alignment.** Weak modes leave the fit quality unchanged; check
  `q/p` versus `q*eta` and mass versus `eta`, `phi`.
- **Same-sign fraction read as charge flip only.** Backgrounds also contribute; correct
  for them before quoting charge misID.
- **Identical efficiency applied to all muon types.** A segment-tagged muon is not a
  combined muon.
- **Ignoring decay in flight for hadron-mimic estimates.** Depends on the track's
  position in the tracker.

## Deliverables

- The muon-type definitions, with efficiency, purity, resolution, and charge misID per type
  (a per-muon rate, not the same-sign pair fraction).
- Tag-and-probe (or equivalent) efficiency with its uncertainty: binomial (Clopper-Pearson)
  only for unweighted, background-free, independent probes; a background-subtracted
  resonance sample needs the simultaneous pass/fail fit of
  [triggers luminosity pileup](triggers-luminosity-pileup.md#tag-and-probe-efficiency-measurement),
  with the tag-probe correlations handled; and the trigger matching definition.
- The high-`pT` alignment/field validation (mass and `q/p` versus `q*eta`, cosmic split).
- The background model for punch-through, decay-in-flight, accidental, cosmic.
