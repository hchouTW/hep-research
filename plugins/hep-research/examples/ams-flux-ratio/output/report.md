# Path A report: synthetic flux and correlated He/p ratio (SYNTHETIC)

**Status: synthetic.** All inputs are invented (see `results.json` → `synthetic_inputs`). Nothing here is an AMS-02 measurement, performance figure or result. The profile supplies conventions (rigidity R = pc/(Ze) in GV, flux at the top of the instrument, exposure normalization) and one documented practice: R > 1.2 × maximum cutoff, documented for the proton flux analysis [Documented, ams02:C31] and applied to helium here as a [Proposal].

Reproduce: `python3 examples/ams-flux-ratio/run.py --toys 400 --seed 20261002` (from the plugin root, D5 environment).

Validate the spec (its level is a profile term, so the profile vocabulary is needed): bind `experiment:ams-02` in a `hep-research.project.json` outside the plugin and run `python3 "<plugin root>/contracts/validate.py" examples/ams-flux-ratio/output/artifacts/measurement_spec.json --profiles-from <your project>/hep-research.project.json`.

## Pre-declared criteria and outcome

| Check | Criterion | Result |
|---|---|---|
| Asimov closure (flux, ratio, period average) | max relative deviation < 1e-09 | pass (max 5.09e-12) |
| Toy closure, mean pull per bin | abs < 0.2 | pass |
| Toy closure, pull width per bin | in (0.85, 1.15) | pass |
| Ratio sigma vs independent propagation (T10) | relative difference < 1e-09 | pass |
| Background estimate, Asimov closure | TF x expected sideband = expected window background, relative < 1e-12 | pass (max 2.2e-16) |
| Background estimate, validation band 1.6 <= Q < 1.7, per period | abs total pull < 3.0 and chi2 p > 0.001 (bins with >= 5 predicted) | pass (synthetic-period-1: observed 259, predicted 308.6, pull -2.68, chi2 10.5 / 8; synthetic-period-2: observed 416, predicted 390.0, pull 1.25, chi2 8.2 / 9) |
| Figures drawn outside the blinded range (core.blinding.check_figure) | no artist inside | pass |
| Response and covariance validators (core.stats) | no failure | pass |
| Contract artifacts (profile vocabulary) | all valid | pass |

The covariance validator warns that the trigger and background blocks have rank 1. That is expected: a single per-period trigger efficiency, and a single transfer factor, scale every bin together, so these blocks are fully correlated by construction.

## Background: Z=1 charge tail in the helium window (synthetic)

A synthetic 5% of the selected Z=1 events has a charge estimator Q above 1.3 with an exponential tail (slope 0.2); the part inside the helium window 1.7 <= Q < 2.5 is a background to helium. Per reco rigidity bin and period it is estimated as TF x the counts of the helium-free sideband 1.3 <= Q < 1.6, TF = 0.1710 from the synthetic tail shape (10% fully correlated uncertainty), and subtracted before the helium unfolding. The validation band 1.6 <= Q < 1.7 (TF = 0.1130) checks the extrapolation on data. The proton flux is not affected.

## Blinding (synthetic policy)

The helium signal-region count in the bin 60-100 GV is blinded in both periods. A custodian step (`skills/hep-analysis/scripts/mask_blinded_bins.py`) masks it before the analysis reads the histograms; the released files are `blinded/helium_signal_region_synthetic-period-1.masked.json`, `blinded/helium_signal_region_synthetic-period-2.masked.json`. The unfolding fills the blinded bin with the simulated helium expectation and zero variance, so no published number depends on its count. The helium flux, the He/p ratio and the period average are null in that bin in `results.json`, the dataset records stop at 60 GV, and the figures show 2-60 GV. Proton counts and the charge sidebands stay open. Nothing here unblinds; that is done by an authorized person outside the agent session.

## What the chain does

Per species and synthetic period: selected truth counts = ∫Φ dR × acceptance × livetime × cutoff fraction × trigger efficiency × selection efficiency; rigidity migration (2% core resolution in curvature, a 2% tail five times wider) gives Poisson reco counts; a full-rank weighted least-squares unfolding (`core.stats.unfolding_diagnostics.linear_matrix`, no regularization) returns selected truth counts; dividing by the efficiencies, the exposure and the bin width gives the bin-averaged flux. The first and last bins (1.5-2 and 100-150 GV) absorb migration and are not reported. For helium the charge-tail background is subtracted from the reco counts first.

Efficiencies are estimated from synthetic control samples. The trigger efficiency is one estimate per period shared by both species (fully correlated across bins); the selection efficiency is measured per bin and species and shared by the two periods. In the He/p ratio the trigger term cancels exactly and the livetime and cutoff fraction cancel by construction; acceptance and selection efficiency do not cancel.

## Correlated ratio (T10)

- synthetic-period-1: ratio sigma per bin 0.004847, 0.00566, 0.005279, 0.007528, 0.007845, 0.009792, 0.01588, 0.02464; independent linear propagation with the shared trigger component agrees to 2.2e-16. Treating the trigger term as independent would overstate the sigma by factors 1.089, 1.069, 1.085, 1.046, 1.046, 1.033, 1.016, 1.007.
- synthetic-period-2: ratio sigma per bin 0.004775, 0.00571, 0.004635, 0.006425, 0.006632, 0.008083, 0.01206, 0.02002; independent linear propagation with the shared trigger component agrees to 1.1e-16. Treating the trigger term as independent would overstate the sigma by factors 1.143, 1.106, 1.162, 1.093, 1.1, 1.081, 1.036, 1.016.

## Time-dependent exposure (T11)

- proton: the period average is the sum of efficiency-corrected counts over the sum of per-period exposures (livetimes 1.5e+06 s, 2.6e+06 s; different cutoff fractions). Splitting the total livetime equally between periods would mis-state the exposure per bin by 0.0789, 0.0789, 0.025, 0.025, 0.0082, 0, 0, 0, 0 (relative).
- helium: the period average is the sum of efficiency-corrected counts over the sum of per-period exposures (livetimes 1.5e+06 s, 2.6e+06 s; different cutoff fractions). Splitting the total livetime equally between periods would mis-state the exposure per bin by 0.0789, 0.0789, 0.025, 0.025, 0.0082, 0, 0, 0, 0 (relative).

## Toy closure

400 pseudo-experiments (seed 20261003) regenerate the counts, the control samples, the charge-tail counts and the transfer factor, and apply the same blinded procedure; helium and ratio pulls cover 2-60 GV.

| Quantity | mean pull per bin | pull width per bin |
|---|---|---|
| proton/synthetic-period-1 | -0.009, -0.043, -0.0466, -0.0512, -0.0755, -0.0092, 0.0042, 0.0415, -0.0511 | 1.031, 1.011, 0.9924, 1.012, 0.9514, 1.02, 0.9927, 1.025, 1.002 |
| proton/synthetic-period-2 | -0.0785, -0.0423, 0.0029, -0.0236, -0.1315, -0.0756, 0.0076, -0.0564, 0.0102 | 0.9441, 0.9935, 0.9727, 0.9629, 0.9642, 1.018, 0.9715, 0.9578, 1.036 |
| helium/synthetic-period-1 | -0.0304, -0.0156, -0.0226, -0.04, -0.0563, -0.0311, -0.0014, 0.025 | 0.9679, 1.05, 0.9704, 1.038, 0.986, 0.9671, 0.9509, 1.047 |
| helium/synthetic-period-2 | -0.0278, -0.0612, -0.0043, -0.0327, -0.0044, -0.0614, -0.0506, 0.0389 | 1.013, 0.937, 1.01, 1.009, 0.9468, 0.9885, 1.036, 1.039 |
| ratio/synthetic-period-1 | -0.031, -0.0011, -0.0042, -0.0226, -0.0254, -0.0322, -0.0137, -0.0101 | 0.9743, 1.046, 0.9745, 1.047, 0.9616, 0.942, 0.9762, 1.028 |
| ratio/synthetic-period-2 | 0.0113, -0.0448, -0.0123, -0.0256, 0.058, -0.0297, -0.0597, 0.046 | 1.011, 0.9801, 1.04, 1.011, 0.9265, 1.024, 1.027, 1.034 |

## Limitations (by construction of this example)

- Acceptance and the response are assumed exactly known; no finite-MC or acceptance systematic is modeled.
- The only background is the synthetic Z=1 charge tail; its charge shape factorizes from rigidity by construction, so one transfer factor serves every bin. No charge confusion or fragmentation is modeled; the synthetic truth exists only in 1.5-150 GV.
- The response uses the generated spectral shape inside each bin, so model dependence of the unfolding is not studied.
- Acceptance, efficiencies and cutoff fractions are constant within a bin by construction.
- Passing these checks shows the chain is internally consistent on synthetic data; it says nothing about any real detector.

Figures: `flux_per_period.png`, `ratio_per_period.png`. Artifacts: `artifacts/*.json` (all status `synthetic`).
