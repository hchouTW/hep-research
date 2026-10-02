# Muon Systems: Spectrometers, Identification, and Trigger

Muon detection and reconstruction: drift-tube, cathode-strip, RPC-, GEM-, and
Micromegas-based chambers; standalone, combined, segment-tagged, calorimeter-tagged, and
trigger-level muons. The PID summary is in [24](24-particle-identification.md);
technology physics is in [41](41-gaseous-and-specialized-tracking-technologies.md);
alignment weak modes in [29](29-calibration-and-alignment.md) and
[22](22-tracking-and-vertexing.md).

## Why muons are special

Muons are minimum-ionizing, do not shower strongly, and traverse the calorimeters, so
the outermost layers see them nearly free of other particles. A muon system therefore
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
   ([22](22-tracking-and-vertexing.md)).
6. **Trigger matching**: the hardware-level (coarse) muon candidate matched to the
   offline muon for the trigger efficiency ([19](19-triggers-luminosity-pileup.md)).

**Muon types (definitions differ by community; state the one used).**
*Standalone*: muon-system track only. *Combined/global*: tracker + muon-system fit.
*Segment-tagged*: tracker track that extrapolates to at least one muon segment (recovers
low-momentum muons that do not reach far). *Calorimeter-tagged*: tracker track with
minimum-ionizing calorimeter deposit (recovers acceptance gaps). *Trigger-level*: coarse
online track. Each type has its own efficiency, purity, and momentum resolution.

## Performance and scaling

- **Resolution**: at low `p`, multiple scattering in absorbers and calorimeters
  (energy-loss fluctuation before the muon system) dominates; at high `p`, spatial
  resolution and alignment of the muon stations limits the *sagitta*
  `s ≈ L^2 B q/(8 p)`-like measurement (approximate, uniform field: momentum error
  `∝ p^2 sigma_s`). High-momentum resolution is a **weak-mode/alignment** problem
  (see below).
- **Efficiency**: geometric gaps (cracks, support structures, feet), chamber
  inefficiency, matching and reconstruction inefficiency, quoted **per type and versus
  `eta`, `phi`, `pT`**, with a tag-and-probe from `J/psi` and `Z -> mu mu`
  ([19](19-triggers-luminosity-pileup.md)).
- **Rate capability**: drift tubes (long drift, space-charge and occupancy limits),
  cathode-strip chambers (high granularity, good for high rate), RPCs (fast, rate
  limited by resistivity), GEM/Micromegas (high rate, discharge risk)
  ([41](41-gaseous-and-specialized-tracking-technologies.md)).
- **Charge sign**: from curvature direction; at high momentum the sagitta shrinks
  toward the alignment/resolution floor and **charge misidentification** grows
  (`~ Gaussian tail of sagitta/sigma`); a weak-mode misalignment gives a *momentum-charge
  correlated bias*: `q/p` shifts charge-dependently, mimicking a charge asymmetry.

## Backgrounds and fakes

- **Punch-through**: hadrons that leak through calorimeter absorbers; falls with
  absorber thickness, rises with hadron energy.
- **Decay in flight**: `pi/K -> mu nu` inside the tracker: a kinked track whose
  combined-fit `chi^2` is bad and whose tracker-muon momentum mismatch is large.
- **Accidental matches**: an unrelated segment (cavern background, noise) matched to a
  tracker track; grows with rate.
- **Cosmic rays and beam halo**: out-of-time or off-vertex muons; suppress with timing,
  vertex/impact parameter, and back-to-back topology.
- **Hadron mis-identification vs reconstruction fake**: a pion identified as a muon
  (mis-ID, real object with wrong identity) is a different failure from a fake track
  ([46](46-performance-metrics-and-residual-diagnostics.md)).

## Distinctive but generalizable reconstruction and performance features (muon system)

- **Topology**: sparse hits grouped into segments over a large lever arm; almost no
  other particles (clean but low redundancy).
- **Inverse problem**: momentum and charge from sagitta in a field with material
  between stations; degeneracy: alignment weak modes (curl, sagitta, twist, radial)
  that leave `chi^2` nearly unchanged but shift `q/p` charge-dependently.
- **Objects**: segment, standalone, combined, tagged muon. **Informative
  residual/closure**: `Z -> mu mu` mass versus `eta`, `phi`, `pT`, and charge
  (`m` and `q/p` residual versus `q * eta`), plus cosmic-ray track splitting
  (upper/lower half fits) to expose sagitta bias.
- **Scaling**: `sigma_pT/pT ∝ pT` at high `p` (measurement-dominated), constant at low
  `p` (scattering); charge misID rises steeply with `pT`.
- **Conventions**: efficiency measured with tag-and-probe at fixed working point and
  isolation; resolution from `Z` line-shape width or MC truth for the momentum range,
  charge misID from same-sign fraction in `Z -> mu mu`.
- **Tails**: wrong-segment link, decay-in-flight, delta-ray overlap, charge flip.
- **Dependence**: rate/occupancy (background hits), magnetic field map stability,
  chamber temperature/gas, alignment time-dependence.
- **Strongest data sample**: `Z -> mu mu` and `J/psi -> mu mu` (mass scale and
  resolution in bins), cosmic muons (split tracks), and collision tracks for
  alignment with external constraints.
- **Transfers**: sagitta-weak-mode and charge-dependent-bias reasoning to any
  spectrometer ([22](22-tracking-and-vertexing.md)); **does not transfer**: the
  specific punch-through/absorber background model.

## Common misconceptions and failure modes

- **One "muon efficiency."** Reconstruction, identification, isolation, and trigger
  efficiencies differ, and each is conditional on the previous
  ([46](46-performance-metrics-and-residual-diagnostics.md)).
- **Trusting `chi^2` for alignment.** Weak modes leave the fit quality unchanged; check
  `q/p` versus `q*eta` and mass versus `eta`, `phi`.
- **Same-sign fraction read as charge flip only.** Backgrounds also contribute; correct
  for them before quoting charge misID.
- **Identical efficiency applied to all muon types.** A segment-tagged muon is not a
  combined muon.
- **Ignoring decay in flight for hadron-mimic estimates.** Depends on the track's
  position in the tracker.

## Deliverables

- The muon-type definitions, with efficiency, purity, resolution, and charge misID per type.
- Tag-and-probe (or equivalent) efficiency with binomial uncertainties, and the trigger
  matching definition.
- The high-`pT` alignment/field validation (mass and `q/p` versus `q*eta`, cosmic split).
- The background model for punch-through, decay-in-flight, accidental, cosmic.
