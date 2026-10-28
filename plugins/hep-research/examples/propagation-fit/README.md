# Multi-dataset propagation fit through a provider (SYNTHETIC)

End-to-end example of `skills/hep-statistics/scripts/propagation_fit.py`: two SYNTHETIC B/C datasets are fitted
with predictions from the closed-form provider `cr-secondary-ratio-closed-form` (profile `theory:cr-secondary-ratio`,
protocol `cr-provider/1`). It shows Asimov recovery (also at a domain bound), an exact D0/L degeneracy found by the
Fisher screen and a profile scan and written as object-form `degenerate_directions` in a fit-derived theory-spec,
model families with toy-calibrated delta chi2 (BIG and SLIM listed as not expressible by the closed form), a
posterior with its convergence diagnostics, and interval coverage from 1000 toys, including a nearly flat direction.
All inputs are ILLUSTRATIVE; nothing here describes the Galaxy or a measurement, and no real data are fitted.

```bash
python3 examples/propagation-fit/run.py --out /tmp/propfit      # from the plugin root; about 1-2 min
python3 examples/propagation-fit/run.py --out /tmp/propfit --stages asimov-interior,degeneracy --toys 1000
```

Exit 0 when every pre-declared criterion of the stages run passes, 1 otherwise, 3 without numpy/scipy. Nothing is
written inside the repository: the inputs, one folder per stage (`result.json`, `statistical-result.json`,
`theory-spec.json`), `results.json` and `report.md` go to `--out`; the provider cache to `--cache-dir` (default
`<out>/cache`), so a rerun costs no provider evaluation.

## Binning

The provider returns the ratio averaged uniformly in ln(E/n) over each bin (`bin_semantics: bin-averaged`,
convention `crsr:bin_average`), not the ratio of bin integrals of the propagation plan's rule P2: the profile has no
primary spectra. The synthetic datasets are generated and declared with the same semantics. Data declared
`bin-integrated` are refused by the fit (`tests/skills/hep_statistics/test_propagation_fit.py`).

## Stages

| Stage | What | Criterion |
|---|---|---|
| `asimov-interior` | family `diffusion` (`D0_cm2_s`, `delta` free; `L_kpc` = 4), production norms C->B and O->B with 10% priors | every free parameter and norm within 0.1 sigma of the truth |
| `asimov-boundary` | the same at `delta` = 0.2, the lower edge of the provider domain; profile interval of `delta` | on the bound, KKT condition met, within 0.1 of the one-sided width |
| `degeneracy` | `L_kpc` also free; profile scan over `L_kpc`; covariance alternatives (correlation length 0.5, 1.5, 4) | `D0_cm2_s/L_kpc` in object form with `valid_range`; theory-spec and statistical-result validate |
| `families` | BIG, SLIM (literature parameters), `diffusion`, `kolmogorov` (`delta` = 1/3), `iroshnikov-kraichnan` (`delta` = 1/2); 200 toys per family; posterior of `diffusion` | BIG, SLIM not expressible; each fitted family listed with its toy-calibrated delta chi2 |
| `coverage` | 1000 plug-in toys at the truth, C->B norm only | coverage of `D0_cm2_s`, `delta` and the flattest Fisher direction within the Bonferroni band |

The criteria were written to `VALIDATION.md` (section CRPROP-C2) before the first fit. Toys, family calibration and
the posterior run on a response model of the provider (validated against provider evaluations); the reported fits
use the provider itself.

## Limits

D0 and L are not separately constrained by B/C in this model. The closed form has no reacceleration, convection,
diffusion break or isotopic fluxes, so BIG and SLIM cannot be fitted and solar modulation is not applied (datasets
are at the local interstellar level). The provider's inputs are placeholders; the USINE case is a separate work
package.
