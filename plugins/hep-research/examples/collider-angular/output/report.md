# Path B report: synthetic corrected angular distribution (SYNTHETIC, ILLUSTRATIVE)

**Status: synthetic.** Profile `experiment:synthetic-collider` is illustrative: its generator, efficiency, resolution and luminosity are invented (`profiles/experiments/synthetic-collider/benchmarks/path-b.json`). Nothing here describes a real detector or measurement, and the generator's shape and cross section are inputs, not predictions. Only this profile is loaded.

Reproduce: `python3 examples/collider-angular/run.py --toys 400 --seed 20261003` (from the plugin root, D5 environment).

## Pre-declared criteria and outcome

| Check | Criterion | Result |
|---|---|---|
| Asimov closure (d sigma / d cos theta and fiducial sigma) | relative deviation < 1e-09 | pass (max 1.6e-15) |
| Toy closure, mean pull per bin | abs < 0.2 | pass |
| Toy closure, pull width per bin | in (0.85, 1.15) | pass |
| Toy closure, fiducial cross section | mean abs < 0.2, width in (0.85, 1.15) | pass (mean -0.0114, width 0.9868) |
| Response and covariance validators (core.stats) | no failure | pass |
| Contract artifacts (profile vocabulary) | all valid | pass |

The covariance validator warns that the luminosity block has rank 1. That is expected: one luminosity scales every bin together.

## Result on the synthetic sample

17449 events generated, 14920 selected. Fiducial cross section (|cos theta| < 0.9): 745.65 ± 6.63 (stat) ± 14.91 (lumi) pb; expected from the generator inputs 745.81 pb.

d sigma / d cos theta per bin (pb): 561.5, 440.4, 388.8, 336.2, 325.3, 329.5, 335.5, 407.7, 454.3, 563.3
Expected (analytic bin integrals of the generator shape): 541.2, 456.6, 393.2, 350.9, 329.8, 329.8, 350.9, 393.2, 456.6, 541.2
chi2 against expected with the full covariance: 10.38 / 10 (p = 0.41). This only checks the chain on its own synthetic input.

## What the chain does

Synthetic events are generated with the profile's generator, kept with the invented efficiency and smeared in cos theta. Selected events are histogrammed in reconstructed cos theta. A full-rank unfolding with an analytic response that includes the efficiency (normalized per generated truth event, so column sums are the bin efficiencies) returns generated truth counts per bin. Dividing by the integrated luminosity and the bin width gives the bin-averaged d sigma / d cos theta. The outer truth bins (|cos theta| > 0.9) absorb migration and are not reported. The covariance has a statistical block and a fully correlated 2% luminosity block.

Toys: 400 pseudo-experiments (seed 20261004) fluctuate the reconstructed counts (Poisson) and the luminosity estimate.

| Bin | mean pull | pull width |
|---|---|---|
| [-0.9, -0.72) | -0.0307 | 0.9803 |
| [-0.72, -0.54) | -0.0524 | 1.0234 |
| [-0.54, -0.36) | 0.014 | 0.9932 |
| [-0.36, -0.18) | -0.0944 | 1.0138 |
| [-0.18, 0) | -0.0502 | 1.006 |
| [0, 0.18) | -0.0035 | 1.0143 |
| [0.18, 0.36) | -0.0086 | 1.0115 |
| [0.36, 0.54) | 0.062 | 1.0563 |
| [0.54, 0.72) | -0.0349 | 0.9671 |
| [0.72, 0.9) | -0.0106 | 0.9508 |

## Limitations (by construction)

- The response uses the generated shape inside each bin; model dependence of the unfolding is not studied.
- No background, radiative corrections, charge confusion or beam-energy spread are modeled.
- Efficiency and resolution are assumed exactly known; only the luminosity carries a systematic.
- Passing these checks shows internal consistency on synthetic data, nothing about a real detector.

Figure: `dsigma_dcos.png`. Artifacts: `artifacts/*.json` (status `synthetic`).
