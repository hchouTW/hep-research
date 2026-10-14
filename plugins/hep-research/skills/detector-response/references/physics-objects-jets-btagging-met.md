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

**Check:** Algorithm, radius, recombination scheme, input constituents and constituent-level pileup mitigation are stated, and every calibration used was derived for that constituent definition.

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

The jet energy scale is a chain of corrections, each with its own uncertainty (general method): a pileup offset; a
simulated-response correction from truth matching; in-situ relative (eta intercalibration with dijets) and absolute
(Z or photon plus jet, multijet balance) residual corrections for data; and flavour response and composition terms.
The jet energy resolution in simulation is matched to data by scaling or by smearing (stochastic smearing for jets
without a matched generator jet).

**Check:** The JES is applied as its factorized chain with the uncertainty decomposed (eta, pT, period); a single overall nuisance is justified; JER smearing is a separate, varied correction.

## b-tagging

State the tagging algorithm, working point (loose/medium/tight or a numerical
threshold), and the calibrated flavor categories (b, c, light/gluon) explicitly - a
working point's efficiency and mistag rate are calibrated for a specific algorithm
version and analysis phase space, and reusing a scale factor outside its calibrated
pT/eta range is a common, hard-to-notice source of bias. b-tagging scale factors are provided per
jet and per truth flavour (b, c, light), binned in pT and eta, for one working point. For a
selection on the number of tagged jets, the event weight uses MC tagging efficiencies `eps_i`
measured in the analysis' own simulated sample per truth flavour: `w = prod_tagged SF_i *
prod_untagged (1 - SF_i eps_i)/(1 - eps_i)` (the ratio of the data-like to the simulated probability
of the observed tag pattern); multiplying only the tagged jets' SFs is wrong. When the discriminant
shape or several working points enter the analysis, use the shape calibration (per-jet reweighting
by discriminant value), which does not preserve yields by construction and needs a normalization
check. State the truth-flavour labelling, the c- and light-mistag calibrations, the correlations
between the b, c and light SF uncertainties, and how jets outside the calibrated range are handled
(typically extrapolated with an enlarged, explicitly flagged uncertainty rather than silently
extended).

**Check:** Algorithm, working point and flavour categories are stated; the event weight uses the tagged and untagged terms with the analysis' own MC efficiencies; jets outside the calibrated pT/eta range carry a flagged, enlarged uncertainty.

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

**Check:** Every object correction is propagated into a recomputed MET; the algorithm, the unclustered-energy treatment and the flat-cut or significance convention are stated.

## Pileup effects specific to jets and MET

Low-pT jets from pileup interactions ("pileup jets") are suppressed with a dedicated
jet-vertex/pileup-jet-identification discriminant, calibrated and carrying its own
scale factor and systematic uncertainty - state the working point used, since pileup
jets that survive selection inflate jet multiplicity and contribute spurious MET.
Pileup also broadens the unclustered-energy resolution component of MET; a MET
resolution correction derived for one pileup regime (e.g. a different data-taking
year with different average pileup) should not be assumed to transfer without
validation.

**Check:** The pileup-jet ID working point and its scale factor are stated; a MET resolution correction is validated for the pileup regime it is used in.

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

**Check:** The removal order, its position relative to the corrections, and the matching radius or criterion are stated.

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
