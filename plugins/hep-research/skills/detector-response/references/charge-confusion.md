# Charge-Sign Confusion: Mechanisms, Measurement, and Handoff

A synthesis note: it ties together what the subsystem references say about charge-sign confusion, states how
detector-response measures the confusion rate, and where the number goes next. Mechanism details stay in their home
files and are linked, not repeated. Detector-specific values (maximum detectable rigidity, layer layout, the variables
an experiment actually uses) come from the profile or the user, never from this file.

## What it is

Charge-sign confusion (charge misidentification, "charge flip") is the reconstruction of a particle with the sign
of its curvature, and so of its charge, inverted. It is a **migration between two samples**, not a widening of one:
a particle of one sign is counted in the opposite-sign sample. Wherever one sign is far more abundant than the other
(a rare antiparticle against its abundant partner, same-sign lepton pairs against opposite-sign ones), even a small
confusion probability of the abundant species produces a background comparable to the signal.

Three ingredients, which a good study keeps separate because they scale differently:

- **Finite curvature resolution (high rigidity).** The measured quantity is the curvature, close to `1/R`, and its
  error is roughly constant in curvature, so `sigma(R)/R` grows with rigidity until the sign itself is undetermined
  at the maximum detectable rigidity
  ([magnetic spectrometry](detector-systems-overview.md#magnetic-spectrometry-rigidity-momentum-and-charge-sign),
  [the two resolution regimes](tracking-and-vertexing.md#rigidity-resolution-and-its-two-regimes)). For a purely
  Gaussian curvature error with `sigma(1/R) = 1/MDR`, the flip probability at true rigidity `R` is
  `Phi(-MDR/R)` (standard normal CDF); it is continuous in `R`, not a switch at the MDR. The Gaussian core is a lower
  bound: the rate away from the MDR is set by the tails
  ([charge confusion](tracking-and-vertexing.md#charge-confusion)).
- **Scattering and interactions (all rigidities, dominant at low rigidity).** The Highland formula describes the
  Gaussian core of multiple scattering only; single large-angle Coulomb scatters and nuclear interactions in the
  material give non-Gaussian kinks that the fit can absorb as a wrong curvature (PDG RPP, *Passage of particles
  through matter*, multiple-scattering section, which states the Highland accuracy for the central part of the
  distribution only; Highland and Lynch-Dahl in the [bibliography](detector-principles-bibliography.md)). The material budget per layer therefore enters the
  confusion rate, not only the resolution core
  ([material budget](detector-systems-overview.md#material-budget-and-multiple-scattering)).
- **Wrong hit association and secondaries (all rigidities).** A noise hit, a delta ray, a hit from a nearby
  secondary or a decay-in-flight kink pulled into the track changes the fitted sagitta; for electrons, a
  bremsstrahlung photon that converts can hand the track to a daughter of either sign. These failures are
  pattern-recognition failures, so they show up in track-quality variables rather than in the curvature error
  alone ([muon backgrounds and fakes](muon-systems.md#backgrounds-and-fakes),
  [pattern recognition](tracking-and-vertexing.md#from-hits-to-tracks-pattern-recognition)).

A fourth effect is not confusion but biases it: an alignment weak mode adds a curvature offset of fixed sign, which
shifts the two signs in opposite directions, so the confusion rates of the two species differ (`c+ != c-`) and a
charge asymmetry can be faked
([alignment coupling](tracking-and-vertexing.md#alignment-coupling),
[alignment and weak modes](calibration-and-alignment.md#alignment-and-weak-modes),
[muon performance and scaling](muon-systems.md#performance-and-scaling)).

Confusion and spillover are the same migration seen along two axes: a confused event also carries a mismeasured
magnitude, so it lands in a different rigidity bin as well as in the wrong sample. Treat the migration as joint in
(sign, rigidity) when the spectrum is steep
([spillover](../../hep-analysis/references/measurements-and-unfolding.md#steeply-falling-spectra-and-spillover)).

## How detector-response measures the rate

The deliverable is the confusion probability per true-rigidity (or true-momentum) bin and per species,
`c+(R)` and `c-(R)`, with statistical and systematic parts, the selection it is conditional on (the denominator),
the validity range and the conditions period. Three complementary routes; a credible result uses at least two.

1. **Simulation, validated on data.** In simulation, `c` is the fraction of truth-matched tracks of one sign
   reconstructed with the other, binned in the **true** value
   ([truth matching](reconstruction-performance-and-truth-matching.md#truth-matching-is-a-definition-not-a-measurement),
   [bin in truth](reconstruction-performance-and-truth-matching.md#resolution-and-bias-from-reco-versus-truth)).
   It is only as good as the simulated tails, so validate the inputs that drive them: the material map, the hit
   noise and cluster model, the alignment residuals, and the curvature-error tail measured in data by splitting a
   track into independent halves or hit subsets, or comparing it with a second tracking system
   ([resolution measured in data](performance-metrics-and-residual-diagnostics.md#resolution-measured-in-data),
   [data/MC comparison](data-mc-validation-and-detector-systematics.md#datamc-comparison-what-to-compare)). Quote a
   robust width and the tail fraction, never a Gaussian sigma alone.
2. **Templates in a confusion-sensitive variable.** Choose variables in which correctly and wrongly signed tracks
   differ: curvature significance (curvature over its error), agreement of rigidities fitted from different hit
   subsets, track-fit chi-square, extra hits near the track, consistency with other subsystems. Build a template
   for correctly signed and for confused tracks (from simulation, or from data control samples where they exist),
   and fit the opposite-sign sample with both; the confused yield over the abundant-species yield gives `c`. A
   classifier on these variables is one such variable
   ([charge-sign confusion in ML](../../physics-ml/references/space-and-astroparticle-ml.md#typical-tasks),
   [efficiency and background from the classifier](../../physics-ml/references/space-and-astroparticle-ml.md#efficiency-and-background-from-the-classifier)).
   The fit itself, its template-statistics treatment and the nuisance parameters belong to hep-statistics.
3. **Control samples of known sign.** A sample whose sign is fixed independently of the curvature: same-sign pairs
   from a resonance decaying to an opposite-sign pair (tag-and-probe style), a beam of known sign, a cosmic track
   reconstructed as two halves, or the abundant species selected by identification that does not use the sign
   ([control samples](data-mc-validation-and-detector-systematics.md#control-samples-and-data-driven-methods),
   [muon conventions](muon-systems.md#distinctive-but-generalizable-reconstruction-and-performance-features-muon-system)).
   State the bias of the sample: its rigidity range, its selection and its track topology may differ from the
   analysis sample, and the rate may need extrapolation to the highest bins, which is then a stated systematic.

Systematics on `c` come from the spread between routes, the template-shape variation, the material and alignment
variations, and the extrapolation outside the control-sample range
([systematic sources](data-mc-validation-and-detector-systematics.md#systematic-uncertainties-sources-and-mapping)).
A closure test (method run on simulation with known `c`) shows the procedure recovers its input, not that the
simulated tails are right.

## Handoff: hep-analysis subtracts it as a background

detector-response measures `c`; hep-analysis decides how the measurement uses it, and hep-statistics fits it.

- **What is handed over:** a performance report (or artifact) with `c+(R)` and `c-(R)` per bin, their covariance or
  the correlation scheme across bins, the denominator and selection, the templates and their shape variations, the
  validity range and the conditions period. Any status label (`synthetic`, `preliminary`, ...) stays on it.
- **What hep-analysis does:** writes the observed counts as a two-by-two sign migration of the true counts, inverts
  it or fits the sign templates, and carries `c` as a background systematic that does **not** cancel in an
  antiparticle-to-particle ratio, because it acts on one species
  ([antiparticles and charge-sign confusion](../../hep-analysis/references/backgrounds.md#antiparticles-and-charge-sign-confusion)).
  In a low-count high-rigidity bin the confused yield is counted before a flux is quoted
  ([low-count bins](space-based-direct-detection.md#low-count-high-rigidity-bins)).
- **Count it once.** If the sign migration is already inside a `response` used for forward folding, it is not
  subtracted again as a background, and the reverse; declare which one carries it
  ([double-counting checks](response-and-forward-folding.md#double-counting-checks)).

<!-- example: synthetic numbers (no experiment) -->
Gaussian-core flip probability `Phi(-MDR/R)` for a synthetic spectrometer: at `R = MDR/2` it is 2.3%, at `MDR/3`
0.135%, at `MDR/5` about 3e-7. If the measured tail gives 1e-5 at `MDR/5`, the tail, not the core, sets the
background there, by more than an order of magnitude. Propagated through the two-by-two migration with an abundant
species ten thousand times the rare one, `c = 1e-5` biases the observed ratio by about 10%, as in the worked
example of [backgrounds](../../hep-analysis/references/backgrounds.md#antiparticles-and-charge-sign-confusion).
<!-- /example -->

## Common misconceptions and failure modes

- **Gaussian extrapolation of the core.** Underestimates the rate except close to the MDR.
- **Confusion only above the MDR.** It is a continuous function of rigidity and is measured in every bin.
- **One rate for both signs.** Alignment weak modes and charge-dependent interactions make `c+` and `c-` differ.
- **Binning the rate in reconstructed rigidity.** Confused events are mismeasured in magnitude too; bin in truth
  and fold, or treat sign and rigidity jointly.
- **Subtracting a confusion already in the response.** Count it once.

## Sources

- PDG, Review of Particle Physics 2025: *Passage of particles through matter* (multiple scattering, the Gaussian
  core of the Highland form and its non-Gaussian tails) and *Particle detectors at accelerators* (momentum
  resolution of a track fit); URLs in the [bibliography](detector-principles-bibliography.md).
- R. L. Gluckstern, "Uncertainties in track momentum and direction, due to multiple scattering and measurement
  errors", Nucl. Instrum. Methods 24 (1963) 381 (origin of the measurement and scattering terms quoted in
  [tracking and vertexing](tracking-and-vertexing.md#rigidity-resolution-and-its-two-regimes); not reopened for
  this note).
- The mechanisms and methods above are drawn from this skill's own references, linked in place.
