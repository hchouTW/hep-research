# Path A report: synthetic flux and correlated He/p ratio (SYNTHETIC)

**Status: synthetic.** All inputs are invented (see `results.json` → `synthetic_inputs`). Nothing here is an AMS-02 measurement, performance figure or result. The profile supplies conventions (rigidity R = pc/(Ze) in GV, flux at the top of the instrument, exposure normalization) and one documented practice: R > 1.2 × maximum cutoff, documented for the proton flux analysis [Documented, ams02:C31] and applied to helium here as a [Proposal].

Reproduce: `python3 examples/ams-flux-ratio/run.py --toys 400 --seed 20261002` (from the plugin root, D5 environment).

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
- synthetic-period-2: ratio sigma per bin 0.004605, 0.005537, 0.004491, 0.006271, 0.006473, 0.007888, 0.01185, 0.01964, 0.02743; independent linear propagation with the shared trigger component agrees to 2.2e-16. Treating the trigger term as independent would overstate the sigma by factors 1.152, 1.112, 1.174, 1.097, 1.106, 1.084, 1.038, 1.016, 1.011.

## Time-dependent exposure (T11)

- proton: the period average is the sum of efficiency-corrected counts over the sum of per-period exposures (livetimes 1.5e+06 s, 2.6e+06 s; different cutoff fractions). Splitting the total livetime equally between periods would mis-state the exposure per bin by 0.0789, 0.0789, 0.025, 0.025, 0.0082, 0, 0, 0, 0 (relative).
- helium: the period average is the sum of efficiency-corrected counts over the sum of per-period exposures (livetimes 1.5e+06 s, 2.6e+06 s; different cutoff fractions). Splitting the total livetime equally between periods would mis-state the exposure per bin by 0.0789, 0.0789, 0.025, 0.025, 0.0082, 0, 0, 0, 0 (relative).

## Toy closure

400 pseudo-experiments (seed 20261003) regenerate the counts and the control samples.

| Quantity | mean pull per bin | pull width per bin |
|---|---|---|
| proton/synthetic-period-1 | -0.046, 0.0488, 0.0308, 0.0095, -0.0505, 0.0005, -0.0905, -0.0036, 0.0102 | 1.038, 0.9891, 0.9922, 0.9564, 1.029, 0.9617, 0.9821, 0.9953, 1.006 |
| proton/synthetic-period-2 | -0.0729, -0.0731, -0.0654, 0.0343, -0.0567, -0.1067, -0.0802, -0.0154, 0.0567 | 0.9882, 1.001, 0.9936, 0.9906, 1.035, 1.001, 1.049, 1.013, 0.9932 |
| helium/synthetic-period-1 | -0.0115, -0.1012, 0.0215, -0.0005, -0.1118, 0.0489, -0.017, -0.0574, -0.0321 | 0.9555, 1.042, 1.019, 0.9975, 1.009, 1.03, 1.027, 1.054, 0.9685 |
| helium/synthetic-period-2 | 0.009, -0.0181, -0.0452, -0.0229, -0.0676, -0.0477, -0.1019, -0.0609, 0.0104 | 0.9533, 1.015, 0.9791, 1.01, 0.9864, 0.973, 0.9666, 1.015, 0.9949 |
| ratio/synthetic-period-1 | 0.0065, -0.126, -0.002, -0.0114, -0.0894, 0.0385, 0.0114, -0.0686, -0.0516 | 0.9661, 1.001, 1.035, 1.002, 0.9914, 1.015, 1.011, 1.046, 0.93 |
| ratio/synthetic-period-2 | 0.0458, 0.0156, -0.0115, -0.0469, -0.0424, 0.0018, -0.0709, -0.0642, -0.0333 | 0.9282, 0.9748, 0.997, 1.031, 0.9839, 0.946, 1.035, 1.032, 1.03 |

## Limitations (by construction of this example)

- Acceptance and the response are assumed exactly known; no finite-MC or acceptance systematic is modeled.
- No background, charge confusion or fragmentation is modeled; the synthetic truth exists only in 1.5-150 GV.
- The response uses the generated spectral shape inside each bin, so model dependence of the unfolding is not studied.
- Acceptance, efficiencies and cutoff fractions are constant within a bin by construction.
- Passing these checks shows the chain is internally consistent on synthetic data; it says nothing about any real detector.

Figures: `flux_per_period.png`, `ratio_per_period.png`. Artifacts: `artifacts/*.json` (all status `synthetic`).
