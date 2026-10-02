# Path A report: synthetic flux and correlated He/p ratio (SYNTHETIC)

**Status: synthetic.** All inputs are invented (see `results.json` → `synthetic_inputs`). Nothing here is an AMS-02 measurement, performance figure or result. The profile supplies conventions (rigidity R = pc/(Ze) in GV, flux at the top of the instrument, exposure normalization) and one documented practice: R > 1.2 × maximum cutoff, documented for the proton flux analysis [Documented, ams02:C31] and applied to helium here as a [Proposal].

Reproduce: `python3 examples/ams-flux-ratio/run_path_a.py --toys 400 --seed 20261002` (from the plugin root, D5 environment).

## Pre-declared criteria and outcome

| Check | Criterion | Result |
|---|---|---|
| Asimov closure (flux, ratio, period average) | max relative deviation < 1e-09 | pass (max 5.09e-12) |
| Toy closure, mean pull per bin | abs < 0.2 | pass |
| Toy closure, pull width per bin | in (0.85, 1.15) | pass |
| Ratio sigma vs independent propagation (T10) | relative difference < 1e-09 | pass |
| Response and covariance validators (core.stats) | no failure | pass |
| Contract artifacts (profile vocabulary) | all valid | pass |

The covariance validator warns that the trigger block has rank 1. That is expected: a single per-period trigger efficiency scales every bin together, so its block is fully correlated by construction.

## What the chain does

Per species and synthetic period: selected truth counts = ∫Φ dR × acceptance × livetime × cutoff fraction × trigger efficiency × selection efficiency; rigidity migration (2% core resolution in curvature, a 2% tail five times wider) gives Poisson reco counts; a full-rank weighted least-squares unfolding (`core.stats.unfolding_diagnostics.linear_matrix`, no regularization) returns selected truth counts; dividing by the efficiencies, the exposure and the bin width gives the bin-averaged flux. The first and last bins (1.5-2 and 100-150 GV) absorb migration and are not reported.

Efficiencies are estimated from synthetic control samples. The trigger efficiency is one estimate per period shared by both species (fully correlated across bins); the selection efficiency is measured per bin and species and shared by the two periods. In the He/p ratio the trigger term cancels exactly and the livetime and cutoff fraction cancel by construction; acceptance and selection efficiency do not cancel.

## Correlated ratio (T10)

- synthetic-period-1: ratio sigma per bin 0.004651, 0.005471, 0.005127, 0.007371, 0.007611, 0.009615, 0.01549, 0.02472, 0.0306; independent linear propagation with the shared trigger component agrees to 2.2e-16. Treating the trigger term as independent would overstate the sigma by factors 1.096, 1.073, 1.091, 1.048, 1.049, 1.035, 1.017, 1.007, 1.004.
- synthetic-period-2: ratio sigma per bin 0.004605, 0.005537, 0.004491, 0.006271, 0.006473, 0.007888, 0.01185, 0.01964, 0.02743; independent linear propagation with the shared trigger component agrees to 4.4e-16. Treating the trigger term as independent would overstate the sigma by factors 1.152, 1.112, 1.174, 1.097, 1.106, 1.084, 1.038, 1.016, 1.011.

## Time-dependent exposure (T11)

- proton: the period average is the sum of efficiency-corrected counts over the sum of per-period exposures (livetimes 1.5e+06 s, 2.6e+06 s; different cutoff fractions). Splitting the total livetime equally between periods would mis-state the exposure per bin by 0.0789, 0.0789, 0.025, 0.025, 0.0082, 0, 0, 0, 0 (relative).
- helium: the period average is the sum of efficiency-corrected counts over the sum of per-period exposures (livetimes 1.5e+06 s, 2.6e+06 s; different cutoff fractions). Splitting the total livetime equally between periods would mis-state the exposure per bin by 0.0789, 0.0789, 0.025, 0.025, 0.0082, 0, 0, 0, 0 (relative).

## Toy closure

400 pseudo-experiments (seed 20261003) regenerate the counts and the control samples.

| Quantity | mean pull per bin | pull width per bin |
|---|---|---|
| proton/synthetic-period-1 | -0.0449, 0.0471, 0.0313, 0.0139, -0.0537, 0.0019, -0.0963, 0.0003, 0.0104 | 1.038, 0.9944, 0.9963, 0.9588, 1.026, 0.9608, 0.9802, 0.9956, 1.004 |
| proton/synthetic-period-2 | -0.0708, -0.062, -0.0611, 0.026, -0.0539, -0.0944, -0.0838, -0.0159, 0.0525 | 0.9883, 0.9981, 0.9928, 0.996, 1.036, 0.9979, 1.051, 1.011, 0.9906 |
| helium/synthetic-period-1 | -0.0104, -0.1102, 0.0269, 0.0012, -0.1096, 0.0418, -0.0266, -0.0581, -0.0265 | 0.9513, 1.038, 1.028, 1.006, 1.009, 1.02, 1.028, 1.041, 0.9833 |
| helium/synthetic-period-2 | 0.0042, -0.0173, -0.0452, -0.0099, -0.0729, -0.0413, -0.1078, -0.0438, 0.0024 | 0.952, 1.012, 0.9797, 1.006, 0.9868, 0.9737, 0.9605, 1.015, 0.9956 |
| ratio/synthetic-period-1 | 0.007, -0.1341, 0.0028, -0.0116, -0.0859, 0.0312, 0.0049, -0.0709, -0.0473 | 0.9615, 1.01, 1.046, 1.005, 0.9912, 1.009, 1.014, 1.037, 0.9499 |
| ratio/synthetic-period-2 | 0.0399, 0.0104, -0.0141, -0.0302, -0.0491, 0.0017, -0.0747, -0.0484, -0.0389 | 0.9247, 0.9798, 0.997, 1.03, 0.9847, 0.9468, 1.027, 1.035, 1.031 |

## Limitations (by construction of this example)

- Acceptance and the response are assumed exactly known; no finite-MC or acceptance systematic is modeled.
- No background, charge confusion or fragmentation is modeled; the synthetic truth exists only in 1.5-150 GV.
- The response uses the generated spectral shape inside each bin, so model dependence of the unfolding is not studied.
- Acceptance, efficiencies and cutoff fractions are constant within a bin by construction.
- Passing these checks shows the chain is internally consistent on synthetic data; it says nothing about any real detector.

Figures: `flux_per_period.png`, `ratio_per_period.png`. Artifacts: `artifacts/*.json` (all status `synthetic`).
