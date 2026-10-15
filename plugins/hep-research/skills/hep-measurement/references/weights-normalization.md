# Weights and Normalization

## Basic convention

A common MC event weight is

`w_event = (L × sigma × k × filter_efficiency / sum_full_gen_weights) × w_gen × product(corrections)`.

This convention does not override production metadata. Do not multiply a k-factor, filter efficiency, or branching fraction twice if it is already included in the cross section. Luminosity in inverse femtobarns and cross section in picobarns require a factor of 1000. Document units rather than inferring them from magnitudes. The denominator must cover the corresponding production with the same generator-weight convention, normally from preselection metadata.

### Denominator in a skimmed NanoAOD sample

A skim removes events, so neither `Events` entries nor a `genWeight` sum over skimmed events is the denominator. NanoAOD stores the pre-skim sums in the `Runs` tree (`genEventSumw`, `genEventSumw2`, `genEventCount`; check the branch names with `Runs->Print()`, since some older productions append `_`). Sum the tree over every file of the sample, including skim outputs that kept zero events. If the skim dropped `Runs` or empty files, recompute the sum with a pass over the unskimmed sample. In formulas:

`norm = L x sigma / sumw_full`, with `sumw_full = sum of genEventSumw over the Runs tree of every file of the sample`
(`L` in pb^-1, so `lumi_fb x 1000`), and event weight `w = genWeight x norm` kept signed; the weighted cutflow reports
`sum(w)` and `sqrt(sum(w^2))` at each node. The verified RDataFrame code is in hep-computing:
[analysis data pipelines](../../hep-computing/references/analysis-data-pipelines.md#normalization-denominator-in-rdataframe-skimmed-nanoaod).

The weights stay signed throughout. Do not use `abs(genWeight)`, and do not drop negative-weight events.

Data usually have unit event weights. Prescaled triggers or specialized estimators may require weights, in which case the resulting histogram is not automatically an ordinary Poisson count. Data-driven backgrounds should not automatically receive MC luminosity normalization.

## Negative weights

Never replace signed NLO generator weights by absolute values, discard them, or set them to zero without a justified analysis prescription. Store N, positive/negative counts, sumw, sumw2, and sumabsw by sample, region, and bin. Large entry counts can coexist with poor precision when cancellation is strong.

For independent events under the usual compound-Poisson MC approximation, `Var(sumw)=sumw2`. The effective-count diagnostic `N_eff=sumw^2/sumw2` is not an observed Poisson count. In particular, signed weights do not justify a binomial interval through this substitution.

If the generator-weight denominator is nearly zero, inspect metadata, generator conventions, and cancellation. Do not insert an epsilon or take its absolute value merely to avoid a failure.

## Selection and corrections

Separate generator normalization, pileup, lepton/trigger, b-tagging, prefiring, and other factors. Verify each is applied exactly once. Record correction inputs, units, eta convention, working point, validity range, and out-of-range behavior. Do not silently clamp unsupported values.

B-tag event weights can depend on both tagged and untagged jets. Untagged objects do not necessarily contribute a factor of one. Use era-matched payloads; unsourced example scale factors are not valid experimental inputs.

## Special productions

- **Extensions:** samples covering the same phase space normally require a consistent cross section and combined denominator. Do not normalize each extension to the full cross section and then add them.
- **Stitching:** remove inclusive/exclusive overlap through documented generator-level phase-space rules or approved weights. Preserve the stitching map and closure evidence.
- **LHE/PDF/scale weights:** identify absolute versus relative conventions, nominal indices, and sums of weights. Decide explicitly whether rate changes are retained; do not silently renormalize each variation.
- **Reweighting and interference:** rates may depend nonlinearly on parameters. A positive signal template multiplied by a strength parameter is not universally adequate.

## Cutflows

For each step, report the selection name, N, sumw, and sqrt(sumw2), separated by data/process as appropriate. Unweighted counts for nested cuts should not increase; signed yields can increase. Inspect extreme weights and negative-weight fractions before and after selections. Use a consistent histogram-flow policy.
