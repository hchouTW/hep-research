# Robustness and Distribution Shift Reference

Evaluating a model beyond IID performance before it is trusted for a physics claim. Production drift:
[monitoring-and-lifecycle.md](monitoring-and-lifecycle.md); slices: [evaluation-strategy.md](evaluation-strategy.md);
calibration under shift: [uncertainty-and-calibration.md](uncertainty-and-calibration.md); the HEP methods (control
regions, reweighting, scale factors): [ml-analysis-decorrelation-and-systematics.md](ml-analysis-decorrelation-and-systematics.md), "Simulation-to-data differences".

| Shift | What moved | Research-time check |
|---|---|---|
| Covariate | input distribution | compare input features between training and the target population |
| Label | class fractions | compare the class marginals, not only accuracy |
| Concept | the input-output relation | needs labels on the shifted population |
| Domain | the data-generating process (simulation vs data, one detector period vs another) | evaluate on the target domain itself |
| Out-of-distribution | inputs unlike training | check that the domain flags fire (`check_surrogate_domain.py`) |
| Nuisance | a variable the output should not depend on | stratify by it |

Progression, scaled to the stakes of the claim: IID -> slices -> known nuisance variations -> domain shift -> OOD ->
the failure envelope. Passing one stage says nothing about the next.

**Simulation is not data by default.** Ask which inputs the simulation may mismodel and how sensitive the model is to
exactly those; whether the known nuisances (detector response, background composition, generator choice) were varied
in the evaluation, not only in training; whether performance was measured on data at all; whether it depends on
simulator artifacts (a seed, a generator-specific correlation): a drop under a simulation change that should not
matter physically is diagnostic; and whether calibration and uncertainty survive the move, not only point
predictions. Deliver which stages ran and which were skipped, per-nuisance slices, the simulation changes tested, and
the conditions under which the output should not be trusted.

## Domain-shift report

`<plugin root>/skills/hep-ml/scripts/domain_shift_report.py` compares a reference sample (simulation) with a target
sample (data or a control region): per feature the weighted Kolmogorov-Smirnov distance and p-value (effective sample
sizes), the Wasserstein-1 distance and a binned chi2; a classifier two-sample test (grouped K-fold logistic regression
on the standardized features and their squares, out-of-fold AUC against its null spread); a per-period breakdown; and
the drivers (features passing a Bonferroni threshold, by distance). It writes the `domain_shift` block of the
ml-artifact (`--domain-shift-out`, for `write_ml_artifact.py --domain-shift`) with status `checked`; what was done
about a shift (`--outcome`, with `--nuisance` for bounded-by-nuisance or uncorrected) is the analyst's declaration.
With large samples tiny shifts are significant: read the distances and the driver ranking, then decide whether the
shift matters for the output (slices of the score, not only the inputs).

## Detector configuration change (eras)

A hardware or calibration change (an added or removed layer, a new readout, a changed trigger) splits the data into
eras: a domain shift with a known boundary, which the analysis records as eras in its measurement spec. Choose one of:
- **per-era training**: one model per era; simplest to validate, but each era needs enough training data;
- **era conditioning**: one model with the era as an input; it shares statistics but must be checked era by era;
- **common features only**: train on inputs that exist and mean the same in every era; loses what the change added;
- **missing-feature indicators**: the new inputs plus an indicator that they are absent, never a silent fill value.
Whatever the choice: per-era calibration of the output, per-era working points (a fixed cut on the score does not
give a fixed efficiency across eras), and efficiencies measured in data per era (tag-and-probe or control samples),
not taken from simulation. Grouped splits keep each era's periods apart (`make_grouped_splits.py`, a composite key
with the era). The executable BDT path is `train_bdt.py`, described in [multivariate-analysis-bdt-nn.md](multivariate-analysis-bdt-nn.md) ("XGBoost in an analysis").

