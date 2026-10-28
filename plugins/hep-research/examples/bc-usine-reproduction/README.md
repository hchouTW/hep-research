# Reproduction of Génolini et al. 2019 with USINE (OBSERVED data)

Work package F1 of the cosmic-ray propagation plan: the BIG, SLIM and QUAINT fits of Génolini et al. 2019
(arXiv:1904.08917, PRD 99 123028, Table II) to the AMS-02 B/C ratio (PRL 117, 231102, 2016) redone with USINE V3.5
through the plugin's `usine` provider and `skills/hep-statistics/scripts/propagation_fit.py`. The pass criteria (H0
decision D9: best-fit delta and K10 within the paper's 1 sigma for every family) are in `VALIDATION.md`, section
CRPROP-F1, written before the first fit.

```bash
export HEP_USINE_BIN=<USINE>/bin/usine HEP_USINE_DATA=<USINE>/inputs HEP_USINE_RUN_DIR=<out>/runs
python3 examples/bc-usine-reproduction/run.py --out <out>                      # data, start, fit, compare
python3 examples/bc-usine-reproduction/run.py --out <out> --stages compare     # the D9 table from finished fits
```

Exit 0 when every family is within D9, 1 on a failed stage or a miss, 3 without USINE's inputs, numpy or scipy.
Nothing is written inside the repository. A full run is about 1000 USINE runs of about 9 s (three families fitted in
parallel); `--cache-dir` keeps the provider results, so a rerun costs no USINE run. The recorded outcome is
`tests/adapters/fixtures/cr_propagation/f1/f1-reproduction.json`, checked offline by `tests/adapters/test_cr_propagation.py`.

## Inputs

| Input | Source | Label |
|---|---|---|
| B/C values and per-source uncertainties (stat, background, acceptance, unfolding, scale) | USINE V3.5 `inputs/CRDATA_COVARIANCE/ERRORS/AMS02_BC_R__PRL117_231102_2016.txt`, read in place (GPL-2.0, never copied) | `observed` |
| Covariance | `build_covariance.py`: statistical uncorrelated; background, acceptance and scale fully correlated; unfolding with a correlation length in ln R fitted to the unfolding block of USINE's `cov_AMS02_201105201605__BC_R.dat` (Derome et al. 2019's toy model, the file the paper's initialisation files name) | model-supplied |
| Cross-check of the values | the AMS02 B/C rows of the CRDB export `inputs/crdata_crdb20170523.dat` shipped with USINE | `secondary` |
| Model families, fixed inputs and priors | the paper's initialisation files and fit outputs shipped in USINE's `doc/DocFiles/2019-Génolini-benchmarks-BC.tar.gz` (numbers only) | |

HEPData answered with a browser challenge (HTTP 403) and the live CRDB REST query redirected to a non-HTTPS page, so
neither was used; the paper's own data file (`AMS02_published_newBCgeo_rigidity.USINE`) is not shipped with USINE.

## What differs from the paper

USINE V3.5 instead of V3.4; the provider's energy grid (20 nodes per decade) instead of 200 bins over 1e-3-5e3 GeV/n;
source normalisation of C, N, O to HEAO-3 at 10.6 GeV/n (USINE's shipped CRDB export has no AMS-02 C, N, O fluxes)
instead of AMS-02 at 50 GV; the covariance scaled with the data instead of the model; the high-rigidity break fixed at
each family's published best fit (its priors are not determined by the shipped files); SLIM with V_A = V_c = 0 (its
initialisation file has 6 and 0.1 km/s); the 12C+H->11B norm and slope applied to the nodes of USINE's production
table instead of USINE's energy grid. Each is attributed in `VALIDATION.md` CRPROP-F1.
