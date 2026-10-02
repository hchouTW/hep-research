# Robustness and Distribution Shift Reference

Evaluating model behavior beyond IID aggregate performance, at research time - before
a model is trusted for a scientific claim or shipped. For post-deployment production
drift monitoring see [monitoring-and-lifecycle.md](monitoring-and-lifecycle.md), which
covers the same underlying shift taxonomy from the detection/alerting side; this file
covers evaluating robustness *during model development*. For slice definition see
[evaluation-strategy.md](evaluation-strategy.md); for calibration under shift see
[uncertainty-and-calibration.md](uncertainty-and-calibration.md).

## Shift taxonomy, where it changes what you do

Only distinguish these when the distinction changes the response:

| Shift | What moved | Typical research-time check |
|---|---|---|
| Covariate shift | Input distribution | Compare input feature distributions train vs. eval population |
| Label shift | Outcome base rates | Compare class/target marginal, not just accuracy |
| Concept shift | Input-output relationship itself | Needs labels on the shifted population; cannot be detected from inputs alone |
| Domain shift | The whole data-generating process (e.g. sim vs. real, one instrument vs. another) | Evaluate on held-out data from the target domain directly |
| Out-of-distribution input | Input unlike anything in training | Epistemic uncertainty should be high; check that it actually is |
| Nuisance variation | A variable that should not affect the output but the model is sensitive to it anyway | Slice or stratify by the nuisance variable |
| Adversarial perturbation | Deliberately constructed worst-case input | Only relevant where an adversary is a credible threat model - do not add this evaluation reflexively |

## Robustness evaluation progression

```text
IID evaluation -> slice evaluation -> known nuisance variation -> domain shift -> OOD behavior -> failure envelope
```

Not every project needs every stage - scale the evaluation to the risk and scientific
importance of the claim. A result that will drive a discovery claim or a deployment
decision earns the full progression; an exploratory internal result may stop at
slices. Each stage subsumes less than it looks: passing IID and slice evaluation says
nothing about domain shift, and passing domain shift says nothing about genuinely
novel OOD inputs.

## Simulation-to-data shift

For scientific ML and HEP, simulated training/test data and real observed data are
**not** the same distribution by default, and treating them as interchangeable is the
single most common robustness failure in this setting. Before trusting
simulation-based results, ask:

- Which input features may be mismodeled by the simulation, and how sensitive is
  performance to exactly those features?
- Which nuisance variations are known (detector response, background composition,
  systematic effects) and were they varied in the evaluation, not just the training
  data?
- Was performance actually evaluated on real data, or only on held-out simulation?
- Does performance depend strongly on artifacts specific to the simulator (e.g. an
  exact random seed, a generator-specific correlation) rather than genuine physical
  structure? A performance drop under a simulation-parameter change that shouldn't
  matter physically is diagnostic here.
- Does calibration and uncertainty (see
  [uncertainty-and-calibration.md](uncertainty-and-calibration.md)) survive the move
  from simulation to data, or only the point predictions?

A model that performs extremely well on simulated test data has not yet demonstrated
anything about real-data performance - see [data-strategy.md](data-strategy.md) on
simulation-specific artifacts that let a model solve an easier unintended problem.

## Deliverables

- Which stages of the evaluation progression were run, and an explicit statement of
  which were skipped and why.
- Nuisance variables identified in advance, with per-nuisance-slice performance.
- For simulation-trained models: the specific plausible simulation changes tested, and
  whether real-data performance was checked at all.
- Whether calibration/uncertainty were re-validated under each shift tested, not only
  point-prediction accuracy.
- An explicit failure envelope statement: the conditions under which this model's
  output should not be trusted.
