# Physics Objects: Jets, b-Tagging, and Missing Transverse Momentum

## Jet clustering

State the jet algorithm, radius parameter, and recombination scheme as part of the
object definition, not as an implementation detail - anti-kt with R=0.4 and R=0.8/1.0
("large-R", for boosted topologies) are common but not interchangeable, and comparing
yields between analyses using different R without acknowledging it produces a
spurious discrepancy. Anti-kt is the near-universal default for hard-scatter jets
because its output shape is geometrically regular and largely insensitive to soft
radiation, unlike kt or Cambridge/Aachen, which remain useful for jet substructure
(subjet history, grooming) rather than as the primary reconstruction algorithm.

Record the input constituents (particle-flow candidates, calorimeter towers, tracks)
and any pileup-mitigation applied at the constituent level (charged-hadron subtraction,
pileup-per-particle identification) before clustering - the same nominal algorithm and
radius produce different jets depending on what fed it, and a scale-factor or
calibration derived for one constituent definition does not transfer to another.

## Jet energy scale and resolution

Jet energy corrections are applied as a sequence of factorized steps (pileup offset,
absolute/relative response, residual data/MC), and each step's associated systematic
uncertainty is itself decomposed into correlated and uncorrelated components (in eta,
in pT, across data-taking periods). Do not collapse jet energy scale into a single
overall uncertainty unless the analysis genuinely has no sensitivity to its shape or
correlation structure - this is usually only true for a very inclusive selection, and
should be justified, not assumed for convenience. Jet energy resolution smearing
(applied to MC to match the resolution observed in data) is a separate correction from
scale, with its own uncertainty, and both must be varied consistently with the same
random seed handling described for other stochastic corrections in
[weights-normalization.md](../../hep-analysis/references/weights-normalization.md). When a correction step is
itself a trained BDT/NN regression (e.g. a jet-energy or b-jet-energy regression)
rather than a factorized analytic correction, see
[multivariate-analysis-bdt-nn.md](../../physics-ml/references/multivariate-analysis-bdt-nn.md#regression-targets)
for training/validation/uncertainty-propagation guidance specific to a regressed
correction.

## b-tagging

State the tagging algorithm, working point (loose/medium/tight or a numerical
threshold), and the calibrated flavor categories (b, c, light/gluon) explicitly - a
working point's efficiency and mistag rate are calibrated for a specific algorithm
version and analysis phase space, and reusing a scale factor outside its calibrated
pT/eta range is a common, hard-to-notice source of bias. b-tagging scale factors are
usually provided per-jet and combined multiplicatively (or via a full reweighting
method for analyses selecting on the number of tagged jets); document which combination
method was used and whether it correctly handles jets outside the calibrated range
(typically extrapolated with an enlarged, explicitly flagged uncertainty rather than
silently extended). Where the analysis selects a fixed number of tagged jets, prefer
the reweighting method (which preserves the full jet-multiplicity information) over a
simple efficiency-scaling method unless yields are shown to agree between the two.

## Missing transverse momentum (MET)

MET is a derived, whole-event quantity - propagate every applied object correction
(jet energy scale, electron/muon momentum corrections, unclustered energy) into the
MET recomputation rather than reusing the uncorrected MET saved in the original
production; failing to propagate corrections is one of the most common sources of a
MET/object-momentum mismatch that shows up as a spurious tail or a mismodeled
transverse-mass shape. Report the algorithm (e.g. particle-flow MET vs.
calorimeter-only) and any dedicated resolution corrections applied to the
unclustered-energy component, which typically carries its own systematic uncertainty
separate from the object-level ones above.

MET significance (MET normalized by an event-dependent resolution estimate rather
than a flat threshold) is preferable to a flat MET cut when the resolution varies
substantially across the phase space (e.g. with pileup or jet multiplicity); document
which convention is used since the two are not directly comparable as selection
thresholds.

## Pileup effects specific to jets and MET

Low-pT jets from pileup interactions ("pileup jets") are suppressed with a dedicated
jet-vertex/pileup-jet-identification discriminant, calibrated and carrying its own
scale factor and systematic uncertainty - state the working point used, since pileup
jets that survive selection inflate jet multiplicity and contribute spurious MET.
Pileup also broadens the unclustered-energy resolution component of MET; a MET
resolution correction derived for one pileup regime (e.g. a different data-taking
year with different average pileup) should not be assumed to transfer without
validation.

## Overlap removal

Physics objects reconstructed from overlapping detector signatures (an electron
depositing energy also clustered into a nearby jet; a jet built from the same tracks
as a nearby muon) must have a documented, order-sensitive overlap-removal procedure -
see the general caution on ordering in
[analysis-design.md](../../hep-analysis/references/analysis-design.md). State the removal order
(commonly leptons resolved against jets after jet energy corrections, but this varies
by analysis and object definitions) and the matching radius/criterion used, since
applying removal before vs. after corrections, or with a different matching radius,
changes both jet and lepton multiplicities.

## Deliverables

- Jet algorithm, radius, constituent definition, and pileup mitigation used at
  clustering.
- Jet energy scale/resolution correction version and the uncertainty decomposition
  applied (collapsed to a single nuisance only with justification).
- b-tagging algorithm, working point, and scale-factor combination method, with the
  calibrated phase-space range stated.
- MET algorithm, corrections propagated into its computation, and whether a flat
  threshold or significance-based selection is used.
- Pileup-jet identification working point and overlap-removal order/criterion.
