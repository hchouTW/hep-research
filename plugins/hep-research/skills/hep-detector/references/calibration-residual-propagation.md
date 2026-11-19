# Calibration Residual Propagation

How a calibration residual (scale, inverse offset, resolution) changes binned yields and ratios, and what to deliver.
Its summary, with the rest of the calibration chain, is in
[calibration and alignment](calibration-and-alignment.md#propagating-a-calibration-residual).

A calibration change is re-derived; a calibration *residual* (the uncertainty left after the best calibration, or a
weak-mode bound) is propagated as a systematic. Declare its form, then compute what it does to every bin:

| Form | Model | Effect on a power law `dN/dx ~ x^-gamma` |
|---|---|---|
| Scale | `x_m = (1+s) x` (energy or momentum scale) | every bin `(1+s)^(gamma-1) - 1 ~ (gamma-1) s`, the same in all bins |
| Inverse offset | `1/x_m = 1/x + q delta` (curvature offset, e.g. a weak mode) | density factor `(1 - q x_m delta)^(gamma-2)`, first order `(2-gamma) q x_m delta`: grows with x_m, opposite for the two charge signs |
| Resolution | core and tail widths scaled by `1 +/- r` | factor `E[(1+eps)^(gamma-1)]`, about `1 + (gamma-1)(gamma-2) sigma^2/2` for a Gaussian |

- **Opposite-sign ratios.** One curvature offset moves both operands, in opposite directions: the signed shifts
  subtract and their magnitudes add. A ratio does not cancel this residual; it doubles it. Same-sign operands with
  different spectral indices cancel only partly.
- **Validity.** In the inverse-offset row, x_m is the measured value (the bin value), x the true one. The tool warns
  when `|q x_m delta|` exceeds 0.3, a conventional threshold, not a derived bound: the error of the first-order form
  depends on gamma (at 0.3 about 1.4% of the factor at gamma 2.7, 3.8% at gamma 1.5, none at gamma 2 or 3), so use
  the exact factor where `|q x_m delta|` is not small. At `q x_m delta >= 1` the mapping is no longer one-to-one and
  events change charge sign (see [charge-confusion.md](charge-confusion.md)).
- **No default size.** `s` or `delta` comes from the calibration itself (a reference line, E/p, a known-mass peak,
  the external constraint on a weak mode), never from a typical value.
- **Deliverables.** Per-variation yields and per-bin shifts, `{nominal, up, down}` for
  `check_systematic_variations.py` (with the variance of the *difference*, because the variations reuse the same
  events), a fully correlated covariance block, and the ratio shift. A validation record that states the
  correlation between operands is written only on request.

Tool: `propagate_scale_distortion.py` (`response`: analytic yields for power-law components; `events`: the same
distortions applied to an event table; modes `scale`, `inverse-offset`, `resolution`, `plugin`). A seeded test
sample comes from `toy_spectrometer.py`.
