# pyhf, HistFactory, and Combine

## Model mapping

A pyhf workspace contains channels, observations, measurements, and a version. A `normfactor` commonly represents a free strength; `normsys` specifies multiplicative rate changes; `histosys` accepts absolute varied bin yields; `shapesys` accepts absolute per-bin uncertainties. Reusing names affects shared parameters and must match the correlation inventory. See the [pyhf likelihood specification](https://scikit-hep.org/pyhf/likelihood.html).

Do not assume a modifier supplies a meaningful model for zero nominal yield with nonzero MC uncertainty. Check the precise behavior and correlations of `shapesys` and `staterror`. Do not apply both to the same statistical source without a justified decomposition.

`${CLAUDE_PLUGIN_ROOT}/adapters/pyhf-combine/assets/pyhf-counting.json` is synthetic: one bin with signal=5, background=20, and observation=20. Its 10% background-rate uncertainty is illustrative, not an experimental input. The integer observation is a demonstration, not a complete Asimov workflow.

```python
# Adaptation example: requires pyhf; fit synthetic input and test fixed mu.
import json
import pyhf
with open("${CLAUDE_PLUGIN_ROOT}/adapters/pyhf-combine/assets/pyhf-counting.json", encoding="utf-8") as stream:
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

Check the naming, correlations, positivity, interpolation, and bounds of rate, shape, normalization, and MC-statistical constraints. Translating textual fields between tools does not necessarily create equivalent likelihoods.

## Worked walkthrough: a pyhf workflow end to end (verified 2026-09-24)

```bash
pyhf cls ${CLAUDE_PLUGIN_ROOT}/adapters/pyhf-combine/assets/pyhf-counting.json                       # single-bin schema and CLs check
# end-to-end sample analysis: deferred to the M3 example; not shipped yet
```

The first command gives CLs_obs = 0.335 at mu = 1 for n = b = 20 with a 10% normsys. The second
(the legacy end-to-end sample analysis at agentic-ai-skills@3e995a4, verified there on 2026-09-24 and
not re-run in this plugin until its M3 port) builds a synthetic ntuple, normalizes it by the full signed weight sum, and makes a sumw/sumw2
cutflow. It then fills orthogonal SR (njet >= 4) and CR (njet == 3) histograms and fits a shared
`mu_bkg` normfactor, per-bin `staterror` from sumw2, and a lumi normsys to labelled Poisson
pseudo-data. With mu injected = 1 it recovers mu = 0.91 +- 0.16 (Minuit) with an observed 95% CLs
limit of 1.19; with mu injected = 0 it gives an observed limit of 0.25, inside the expected
band [0.17, 0.56]. Reuse the pattern: keep regions orthogonal, take the MC-stat error from
sumw2 and not from sqrt(N), and label pseudo-data and Asimov data as what they are.

## Cross-backend verification

First compare main expected counts and auxiliary terms at identical parameter points. Then compare delta-NLL, fitted parameters, and profile curves before comparing limits. Absolute NLL values may differ by constants. Align statistics, bounds, constraint parameterizations, global observations, interpolation, and optimizer tolerances. Agreement of a final limit alone is insufficient evidence of equivalence.
