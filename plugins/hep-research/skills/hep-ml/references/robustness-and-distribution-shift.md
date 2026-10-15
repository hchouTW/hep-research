# Robustness and Distribution Shift Reference

Evaluating a model beyond IID performance before it is trusted for a physics claim. Production drift:
[monitoring-and-lifecycle.md](monitoring-and-lifecycle.md); slices: [evaluation-strategy.md](evaluation-strategy.md);
calibration under shift: [uncertainty-and-calibration.md](uncertainty-and-calibration.md); the HEP methods (control
regions, reweighting, scale factors): [ml-analysis.md](ml-analysis.md), "Simulation-to-data differences".

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
