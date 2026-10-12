# Coverage grid of 95% counting procedures (SYNTHETIC, [General method])

Gate: one-sided lower bound >= nominal - max_deficit, Bonferroni per procedure (nominal 0.95, max deficit 0.01). Seed 20261012, 20000 toys per asymptotic point.

## Exact coverage (known background)

| s | b | classical | CLs | Feldman-Cousins |
|---|---|---|---|---|
| 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| 0.5 | 0 | 1.0000 | 1.0000 | 0.9856 |
| 1 | 0 | 1.0000 | 1.0000 | 0.9810 |
| 2 | 0 | 1.0000 | 1.0000 | 0.9834 |
| 3 | 0 | 0.9502 | 0.9502 | 0.9962 |
| 5 | 0 | 0.9596 | 0.9596 | 0.9796 |
| 8 | 0 | 0.9576 | 0.9576 | 0.9690 |
| 0 | 0.5 | 1.0000 | 1.0000 | 0.9856 |
| 0.5 | 0.5 | 1.0000 | 1.0000 | 0.9810 |
| 1 | 0.5 | 1.0000 | 1.0000 | 0.9814 |
| 2 | 0.5 | 1.0000 | 1.0000 | 0.9858 |
| 3 | 0.5 | 0.9698 | 0.9698 | 0.9599 |
| 5 | 0.5 | 0.9734 | 0.9734 | 0.9624 |
| 8 | 0.5 | 0.9699 | 0.9699 | 0.9561 |
| 0 | 2 | 1.0000 | 1.0000 | 0.9834 |
| 0.5 | 2 | 1.0000 | 1.0000 | 0.9580 |
| 1 | 2 | 0.9502 | 1.0000 | 0.9665 |
| 2 | 2 | 0.9817 | 1.0000 | 0.9603 |
| 3 | 2 | 0.9596 | 0.9933 | 0.9796 |
| 5 | 2 | 0.9704 | 0.9704 | 0.9576 |
| 8 | 2 | 0.9707 | 0.9707 | 0.9565 |
| 0 | 5 | 0.9596 | 1.0000 | 0.9682 |
| 0.5 | 5 | 0.9734 | 1.0000 | 0.9747 |
| 1 | 5 | 0.9826 | 1.0000 | 0.9574 |
| 2 | 5 | 0.9704 | 1.0000 | 0.9657 |
| 3 | 5 | 0.9576 | 0.9997 | 0.9521 |
| 5 | 5 | 0.9707 | 0.9897 | 0.9565 |
| 8 | 5 | 0.9741 | 0.9741 | 0.9600 |

Classical and Feldman-Cousins pass at every point: True. CLs is reported, not gated as a belt: it over-covers by design.

## Asymptotic profile limit, Gaussian-constrained background (toys)

| s | b | sigma_b | coverage | 95% interval | lower bound (Bonferroni) | gate |
|---|---|---|---|---|---|---|
| 0 | 3 | 0.3 | 1.0000 | [0.9998, 1.0000] | 0.9997 | pass |
| 1 | 0.5 | 0.25 | 1.0000 | [0.9998, 1.0000] | 0.9997 | pass |
| 2 | 3 | 0.3 | 0.9597 | [0.9569, 0.9624] | 0.9561 | pass |
| 2 | 3 | 1.5 | 0.9813 | [0.9794, 0.9832] | 0.9788 | pass |
| 5 | 10 | 0.5 | 0.9458 | [0.9426, 0.9489] | 0.9417 | pass |
| 5 | 10 | 5 | 0.9838 | [0.9820, 0.9855] | 0.9814 | pass |
| 10 | 50 | 2.5 | 0.9537 | [0.9507, 0.9566] | 0.9499 | pass |
| 20 | 100 | 5 | 0.9454 | [0.9422, 0.9485] | 0.9413 | pass |

Toy calibration at s = 3, b = 1: exact 0.9817, toys 0.9825 (99.9% interval [0.9792, 0.9853]): agrees.

Negative control (asymptotic limit ignoring sigma_b, s = 5, b = 10, sigma_b = 5): coverage 0.8733, gate fail.

A failed point marks the asymptotic limit inapplicable there (use a toy-calibrated or exact construction); passing points validate only themselves, not the space between them.
