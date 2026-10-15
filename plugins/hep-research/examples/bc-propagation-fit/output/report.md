# B/C propagation-parameter grid fit (SYNTHETIC)

SYNTHETIC data from theory:cr-secondary-ratio at an ILLUSTRATIVE truth point; ILLUSTRATIVE cross sections. No statement about the Galaxy or any measurement.

Grid: D0 1e+28-1e+29 cm^2/s x L 1-10 kpc, 21 nodes per axis, 0.05 dex steps on both axes, two cross-section sets (882 gated prediction artifacts).

Truth D0/L = 7.5e+27 cm^2 s^-1 kpc^-1 (D0 = 3e+28, L = 4); 12 E/n bins at level crsr:local-interstellar.

| Fit | D0/L | sigma(ln D0/L) | chi2 / dof | degenerate direction (ln D0, ln L) | matches |
|---|---|---|---|---|---|
| Asimov, set A | 7.51e+27 | 0.0166 | 0.00 / 11 | (0.707, 0.707) | D0/L |
| pseudo-data, set A | 7.449e+27 | 0.0165 | 9.37 / 11 | (0.707, 0.707) | D0/L |
| pseudo-data, xs-illustrative-B | 8.775e+27 | 0.0162 | 16.52 / 11 | (0.707, 0.707) | D0/L |

D0 and L separately: unconstrained (best-fit positions along the flat direction are not measurements).
Pull of ln(D0/L), pseudo-data set A: -0.41; chi2 p-value 0.588.
Cross-section model set (min-max, never Gaussian): D0/L in [7.449e+27, 8.775e+27].
Toys (set A, 100, seed 20261015): mean pull 0.015890433616, sd 0.952059607406.

Negative variants (each refused):

- ungated-no-measurement: exit 1 (expected 1)
- rigidity-bins: exit 1 (expected 1)
- unfolded-level: exit 1 (expected 1)
- unknown-correlation: exit 3 (expected 3)

Criteria: all pass
