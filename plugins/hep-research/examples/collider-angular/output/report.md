# Path B report: synthetic corrected angular distribution (SYNTHETIC, ILLUSTRATIVE)

**Status: synthetic.** Profile `experiment:synthetic-collider` is illustrative: its generator, efficiency, resolution and luminosity are invented (`profiles/experiments/synthetic-collider/benchmarks/path-b.json`). Nothing here describes a real detector or measurement, and the generator's shape and cross section are inputs, not predictions. Only this profile is loaded.

Reproduce: `python3 examples/collider-angular/run.py --toys 400 --seed 20261003` (from the plugin root, D5 environment).

## Pre-declared criteria and outcome

| Check | Criterion | Result |
|---|---|---|
| Asimov closure (d sigma / d cos theta and fiducial sigma) | relative deviation < 1e-09 | pass (max 3.0e-14) |
| Toy closure, mean pull per bin | abs < 0.2 | pass |
| Toy closure, pull width per bin | in (0.85, 1.15) | pass |
| Toy closure, fiducial cross section | mean abs < 0.2, width in (0.85, 1.15) | pass (mean -0.005, width 1.0216) |
| Background estimate, Asimov closure | TF x expected control = expected signal-region background, relative < 1e-12 | pass (max 2.2e-16) |
| Background estimate, validation band 0.8 <= x_vis < 0.9 | abs total pull < 3.0 and chi2 p > 0.001 | pass (observed 1171, predicted 1173.0, pull -0.05; chi2 13.7 / 12, p = 0.32) |
| Figure drawn outside the blinded range (core.blinding.check_figure) | no artist inside | pass |
| Response and covariance validators (core.stats) | no failure | pass |
| Contract artifacts (profile vocabulary) | all valid | pass |

The covariance validator warns that the luminosity and background blocks have rank 1. That is expected: one luminosity and one transfer factor scale every bin together.

## Blinding (synthetic policy)

The forward signal-region bin cos theta >= 0.9 (x_vis >= 0.9), outside the reported fiducial range, is blinded for a separate synthetic forward analysis. A custodian step (`skills/hep-analysis/scripts/mask_blinded_bins.py`) masks its count before the analysis reads the histogram; the released file is `blinded/signal_region_counts.masked.json`. The unfolding fills the blinded bin with the simulated signal expectation and zero variance, so no published number depends on its count, and every value in that bin is null in `results.json`. The control and validation sidebands stay open: the background estimate needs them. Nothing here unblinds; that is done by an authorized person outside the agent session.

## Result on the synthetic sample

14316 selected signal-region events in the unblinded bins; estimated background there 414.9 events (TF = 0.0707 x 6112 control-sideband events in all bins). Fiducial cross section (|cos theta| < 0.9): 746.50 ± 6.73 (stat) ± 2.23 (background) ± 14.93 (lumi) pb; expected from the generator inputs 745.81 pb.

d sigma / d cos theta per bin (pb): 560.5, 440.4, 391.7, 339.3, 327.1, 329.4, 339.4, 404.6, 450.3, 564.5
Expected (analytic bin integrals of the generator shape): 541.2, 456.6, 393.2, 350.9, 329.8, 329.8, 350.9, 393.2, 456.6, 541.2
chi2 against expected with the full covariance: 8.02 / 10 (p = 0.63). This only checks the chain on its own synthetic input.

## What the chain does

Synthetic signal and background events are generated with the profile's generator, kept with the invented efficiency and smeared in cos theta. Selected events are histogrammed in reconstructed cos theta in three bands of the visible-energy fraction x_vis: the signal region (>= 0.9), the control sideband (0.5-0.8, signal-free) and the validation band (0.8-0.9). The background in the signal region is the control count times a transfer factor from the simulated background x_vis shape, subtracted bin by bin (10% fully correlated transfer-factor uncertainty). A full-rank unfolding with an analytic response that includes the efficiency (normalized per generated truth event, so column sums are the bin efficiencies) returns generated truth counts per bin. Dividing by the integrated luminosity and the bin width gives the bin-averaged d sigma / d cos theta. The outer truth bins (|cos theta| > 0.9) absorb migration and are not reported. The covariance has a statistical block (signal-region and control counts), a background block (transfer factor) and a fully correlated 2% luminosity block.

Toys: 400 pseudo-experiments (seed 20261004) fluctuate the signal-region and control counts (Poisson), the transfer factor and the luminosity estimate, and apply the same blinded procedure.

| Bin | mean pull | pull width |
|---|---|---|
| [-0.9, -0.72) | 0.0086 | 1.0471 |
| [-0.72, -0.54) | 0.0019 | 1.0366 |
| [-0.54, -0.36) | 0.0062 | 0.9774 |
| [-0.36, -0.18) | -0.0387 | 0.9539 |
| [-0.18, 0) | -0.0238 | 0.9391 |
| [0, 0.18) | -0.0167 | 0.9934 |
| [0.18, 0.36) | -0.09 | 0.9186 |
| [0.36, 0.54) | 0.004 | 1.0167 |
| [0.54, 0.72) | 0.0274 | 1.0529 |
| [0.72, 0.9) | -0.0508 | 1.0348 |

## Limitations (by construction)

- The response uses the generated shape inside each bin; model dependence of the unfolding is not studied.
- The background's x_vis shape factorizes from cos theta by construction, so one transfer factor serves every bin.
- No radiative corrections, charge confusion or beam-energy spread are modeled.
- Efficiency and resolution are assumed exactly known; only the luminosity and the transfer factor carry a systematic.
- Passing these checks shows internal consistency on synthetic data, nothing about a real detector.

Figure: `dsigma_dcos.png`. Artifacts: `artifacts/*.json` (status `synthetic`).
