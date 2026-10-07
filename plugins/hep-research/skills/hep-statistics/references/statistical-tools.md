# pyhf, HistFactory, and Combine

## Model mapping

A pyhf workspace contains channels, observations, measurements, and a version. A `normfactor` commonly represents a free strength; `normsys` specifies multiplicative rate changes; `histosys` accepts absolute varied bin yields; `shapesys` accepts absolute per-bin uncertainties. Reusing names affects shared parameters and must match the correlation inventory. See the [pyhf likelihood specification](https://scikit-hep.org/pyhf/likelihood.html).

Do not assume a modifier supplies a meaningful model for zero nominal yield with nonzero MC uncertainty. Check the precise behavior and correlations of `shapesys` and `staterror`. Do not apply both to the same statistical source without a justified decomposition.

`<plugin root>/adapters/pyhf-combine/assets/pyhf-counting.json` is synthetic: one bin with signal=5, background=20, and observation=20. Its 10% background-rate uncertainty is illustrative, not an experimental input. The integer observation is a demonstration, not a complete Asimov workflow.

```python
# Adaptation example: requires pyhf; fit synthetic input and test fixed mu.
import json
import pyhf
with open("<plugin root>/adapters/pyhf-combine/assets/pyhf-counting.json", encoding="utf-8") as stream:
    workspace = pyhf.Workspace(json.load(stream))
model = workspace.model()
data = workspace.data(model)  # Includes auxiliary data; do not append it twice.
pars = pyhf.infer.mle.fit(data, model)
cls = pyhf.infer.hypotest(1.0, data, model, return_expected_set=True)
print(model.config.par_order, pars, cls)
```

Production inference additionally requires convergence diagnostics, bounds, scans, version records, and assessment of coverage conditions. A successful function call does not establish validation.

## Combine

Follow project datacards and the installed release. Check alignment of bin/process/rate columns, process IDs, shape-file and object patterns, observations, nuisance rows, rateParam, and autoMCStats. Interpret the relationship between template integrals and card rates before applying normalization again.

Before fitting, document: channels, categories, and regions; observed counts or
binned observed histograms; signal and background process names, with process
identifiers following the tool's sign convention (Combine expects non-positive signal
IDs); rate or shape-template names; nuisance-parameter names, types, affected
processes, and correlations; and the shape-file path and histogram-naming convention.
Then check that every process has a matching nominal histogram or rate, every shape
nuisance has nominal/up/down templates, template binning matches within each channel,
empty background templates are justified or protected by the framework's convention,
negative bins are handled according to the tool's requirements, and rate uncertainties
are not double-counted as both a normalization and a shape effect.

A common workflow creates a workspace and runs fit diagnostics, asymptotic limits, or suitable toy calculations. Verify options through the release's help and [official documentation](https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/). Blinded work uses authorized expected/Asimov modes; do not default to commands that inspect observations.

With Combine 11.1.0 built against ROOT 6.40, `combine -M AsymptoticLimits` can stop with `Value ... is outside the default range ... of the variable "r"` and print no observed limit: its observed-limit search tries an r above the POI range, which older ROOT silently clipped and ROOT 6.40 rejects. Pass `--strictBounds` with an `--rMax` well above the expected limit, and check that the limit is not at `--rMax` (seen on the synthetic counting card; VALIDATION COMBINE-ROOT640).

Check the naming, correlations, positivity, interpolation, and bounds of rate, shape, normalization, and MC-statistical constraints. Interpolation codes (pyhf `code1`/`code4`, `code0`/`code4p`; Combine `lnN`, `shape`, `shapeN`), constraint forms and the correlation-by-name rule are in [nuisance modeling](nuisance-modeling.md). Translating textual fields between tools does not necessarily create equivalent likelihoods.

## Worked walkthrough: a pyhf workflow end to end (verified 2026-09-24)

```bash
pyhf cls <plugin root>/adapters/pyhf-combine/assets/pyhf-counting.json                       # single-bin schema and CLs check
python3 <plugin root>/examples/end-to-end-sample/run.py --outdir demo_out   # full chain, needs numpy + pyhf
```

The first command gives CLs_obs = 0.335 at mu = 1 for n = b = 20 with a 10% normsys. The second
(`tests/examples/test_end_to_end_sample.py` runs it) builds a synthetic ntuple, normalizes it by the full signed weight sum, and makes a sumw/sumw2
cutflow. It then fills orthogonal SR (njet >= 4) and CR (njet == 3) histograms and fits a shared
`mu_bkg` normfactor, per-bin `staterror` from sumw2, and a lumi normsys to labelled Poisson
pseudo-data. With mu injected = 1 it recovers mu = 0.91 +- 0.16 (Minuit) with an observed 95% CLs
limit of 1.19; with mu injected = 0 it gives an observed limit of 0.25, inside the expected
band [0.17, 0.56]. Reuse the pattern: keep regions orthogonal, take the MC-stat error from
sumw2 and not from sqrt(N), and label pseudo-data and Asimov data as what they are.

## Publishing likelihoods for reinterpretation

A published full likelihood lets others reuse the analysis without re-deriving it (Cranmer et al., "Publishing statistical models: getting the most out of particle physics experiments", SciPost Phys. 12 (2022) 037).

- **Full likelihood.** Publish the pyhf JSON as a background-only workspace plus a signal patchset (one JSON-patch per signal hypothesis, with the workspace digest and the grid labels) on HEPData. The patch adds the signal samples, and the measurement keeps the POI. Before publishing, apply each patch and check that it reproduces the internal workspace's best fit and CLs. `tests/adapters/test_pyhf_publication.py` does this on the SYNTHETIC shape workspace (`pyhf-shape-synthetic.json`, verified 2026-10-03 with pyhf 0.7.6). After the patch, the best fit and the observed and expected CLs at mu = 1 agree with the original to 1e-6 (mu_hat = 0.7949, observed CLs 0.4924), and a patch applied to a workspace with a different digest is refused.
- **Translation between tools.** A likelihood converted between formats (Combine datacard, RooFit workspace, pyhf JSON) is not equivalent because the text converts. Interpolation codes, constraint shapes, MC-statistics treatment and bounds can all differ. Verify it as in "Cross-backend verification" below before publishing the translated version.
- **Simplified likelihoods** (Buckley et al., JHEP 04 (2019) 064). These keep only the background expectations per bin with a covariance, plus optionally a skew (third-moment) term. They suit many bins with large counts and approximately Gaussian background uncertainties. They fail for few-count bins, strongly non-Gaussian or one-sided systematics, and nuisance effects that do not act linearly on the yields. State which form was published and over what range it was validated against the full likelihood.
- **Producer checklist.** Publish the bin-to-bin correlations, or the full model rather than per-bin uncertainties. Say whether signal regions overlap and which ones may be combined. Give both expected and observed results. Record the model and tool versions, with the schema version for pyhf JSON. Label the data as observed, Asimov or synthetic.

Recasting a published likelihood for a new model (generating its signal, applying efficiencies) is `hep-theory` work. This section covers only what the producer publishes and how it is checked.

## Cross-backend verification

First compare main expected counts and auxiliary terms at identical parameter points. Then compare delta-NLL, fitted parameters, and profile curves before comparing limits. Absolute NLL values may differ by constants. Align statistics, bounds, constraint parameterizations, global observations, interpolation, and optimizer tolerances. Agreement of a final limit alone is insufficient evidence of equivalence.
