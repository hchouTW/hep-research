# Background Estimation and Control Data

## Simultaneous control-region models

Use shared process normalization parameters to link CRs and SRs. Model detector, theory, and MC-statistical uncertainties in transfer factors by source. A CR is not exact truth: retain its observation model, other backgrounds, and possible signal contamination. If its observations already enter the joint likelihood, do not add an independent Gaussian estimate derived from the same data.

## ABCD

Fix region definitions first. For example, A=(x pass,y pass), B=(pass,fail), C=(fail,pass), and D=(fail,fail), with A the target. Under background independence and appropriate contamination treatment, `A≈BC/D`. Test correlation in independent validation data or simulation; introduce `kappa=AD/(BC)` and its uncertainty/correlations when justified.

A small or zero D invalidates simple ratio propagation. Use a joint four-region likelihood or another justified model; do not replace D by one. Background-subtracted estimates can be negative and are not Poisson counts. Prefer explicit component modeling where possible. Do not tune closure uncertainties to force agreement with the observed SR.

## Fake factors and matrix methods

Define loose/tight, prompt/fake, measurement/application regions, sample purity, and parameterization. If f is the probability for a loose fake object to pass tight selection, the corresponding failing sample often receives `f/(1-f)`. Multiple-object cases require correct inclusion–exclusion, not arbitrary products that double count events.

Validate prompt subtraction, composition, kinematic dependence, and extrapolation. Extreme weights near f=1 require investigation of method stability rather than an unexplained cap. Nearly equal efficiencies can make matrix-method inversion unstable; report conditioning and identifiability limitations.

## Sidebands and data-driven shapes

Exclude or model signal leakage and specify fit ranges and extrapolation to the SR. Assess bias and spurious signal with independent samples and alternative models. Selecting the best chi-square alone is insufficient. Discrete functional-form uncertainty needs a coherent treatment, not an arbitrary extra rate error.

Propagate covariance and finite control-sample statistics after subtraction, smoothing, or reweighting. If the same control data train a reweighter and test closure, split samples or use cross-fitting.

## Antiparticles and charge-sign confusion

In a measurement of a rare antiparticle against an abundant particle (antiprotons against protons, positrons against
electrons in a proton-dominated flux), the main background is the abundant species reconstructed with the wrong
charge sign or the wrong identity.

- **Charge confusion as a migration matrix.** Write the observed counts as `(N+_obs, N-_obs) = M (N+, N-)` with
  `M = [[1 - c+, c-], [c+, 1 - c-]]`, where `c+` is the probability that a positive particle is reconstructed negative.
  Measure `c` from the tails of the tracker (curvature significance, track-quality variables) in data, validated on
  simulation; it rises with rigidity as the curvature resolution degrades, so measure it per bin. Then invert `M` (or
  fit the charge-sign templates); quote `c` and its uncertainty as a systematic.
- **Species-specific effects do not cancel.** In a ratio of an antiparticle to a particle, effects common to both
  (exposure, live time, a charge-independent efficiency) cancel to the extent they are equal; charge confusion,
  charge-dependent interaction cross sections in the detector material and charge-sign-dependent acceptance belong to
  one species and must be corrected separately (record them as `independent` in the spec's ratio cancellations).
- **Misidentified protons in lepton selections.** Build the proton template from a data sample enriched in protons
  (for example inverting the electron-identification requirement) and fit it with the lepton template in the
  identification variable; the template shape and its rigidity dependence are a systematic, and the template must
  come from events not used to define the signal selection.

Worked example (synthetic): a true antiproton-to-proton ratio of 1.0e-4 with confusion `c+ = 1.0e-5` (and negligible
`c-` contribution) is observed as `r(1 - c-) + c+` = 1.1e-4, a 10% bias that inverting `M` removes.

## Coupled species

Some backgrounds are another species measured in the same data: the feed-down of a heavier nucleus that fragments
above the detector, the confused-sign partner of an antiparticle, the neighbouring charge in a charge ladder. Their
size depends on a quantity the analysis measures at the same time, so a subtraction with a fixed number freezes a
value that is itself uncertain and correlated with the result.
- Fit the species together: a joint likelihood of the coupled samples with the migration between them
  (`<plugin root>/skills/hep-detector/scripts/species_response.py` builds the blocks), or iterate the measurement of
  the background species and the subtraction until both are stable, propagating the background species' uncertainty.
- Declare the coupling in the spec: `coupled_backgrounds: [{background, species, treatment, source}]`, treatment
  `joint-fit`, `iterative` or `fixed-subtraction`. `review_measurement_spec.py` warns with
  `coupled.fixed_subtraction` on the last.
- A fixed subtraction is acceptable only when the coupling is weak and the background species is measured
  elsewhere with its uncertainty propagated; say so in the spec's notes.

## Deliverables

Provide region definitions, contamination estimates, transfer factors/kappa, closure plots and uncertainties, the correlation evidence with a proposed scheme (hep-statistics encodes it), and an inventory of how each dataset enters the joint likelihood. Distinguish validation of normalization, shape, and extrapolation.
