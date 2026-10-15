# B/C propagation-parameter grid fit (SYNTHETIC)

End-to-end example: SYNTHETIC B/C points with a full covariance are fitted on a (D0, L) grid of
`theory:cr-secondary-ratio` predictions with `covariance_fit.py fit`, model `tabulated-grid`. It shows that the fit
recovers D0/L, reports D0 and L as unconstrained, and finds one degenerate direction along (1, 1) in (ln D0, ln L)
that it matches to the theory-spec's `degenerate_directions: ["D0/L"]`. All inputs are ILLUSTRATIVE; nothing here
describes the Galaxy or a measurement.

```bash
python3 examples/bc-propagation-fit/run.py            # from the plugin root; ~35 s with 100 toys
python3 examples/bc-propagation-fit/run.py --toys 0 --out /tmp/bcfit --keep /tmp/bcfit-inputs
python3 skills/hep-statistics/scripts/covariance_fit.py fit --input /tmp/bcfit-inputs/fit-input.json
```

Exit 0 when every pre-declared criterion passes (listed in `run.py`), 1 otherwise, 3 without numpy/scipy.

## What it does

1. **Grid.** 21 x 21 nodes, D0 = 1e28-1e29 cm^2/s and L = 1-10 kpc, equal log spacing (0.05 dex) on both axes, for
   each of the profile's two ILLUSTRATIVE cross-section sets: 882 `prediction` artifacts written by the profile's own
   `make_artifacts.prediction()` (bin-averaged B/C via `predict.bin_averaged`). They are regenerated on every run into
   a temporary directory, or into `--keep DIR/grid/`; `output/artifacts/grid-manifest.json` holds the axes and a
   combined SHA-256.
2. **Relabelling for the fit** (recorded here because it is an interface choice): `representation: "grid"`;
   `parameter_point` keys `D0` and `L` (the names in the theory-spec's `"D0/L"`; the profile's own keys are
   `D0_cm2_s` and `L_kpc`, so the units are kept in `D0_unit` and `L_unit`); the derived `D0_over_L` key dropped; one
   theory-spec per cross-section set (`theory-spec-xs-A.json` is the profile's spec with a suffixed id).
3. **Binning and level.** The data use the prediction's variable (E/n in GeV/n), its 12 bins, its bin semantics (the
   ratio averaged in ln(E/n)) and its level `crsr:local-interstellar`. Real data are at the top of the instrument,
   often in rigidity: comparing them needs solar modulation and a variable change, which the prediction does not
   allow and this example does not do. The negative variants show the gate refusing rigidity bins and an
   `unfolded` level.
4. **Data.** Truth D0 = 3e28 cm^2/s, L = 4 kpc (D0/L = 7.5e27 cm^2 s^-1 kpc^-1), set A; covariance 3% uncorrelated
   + 2% correlated (exp(-|d ln E| / 1.5)) in a `dataset-record` component with `correlation: "covariance"`;
   pseudo-data drawn once with `numpy.random.default_rng(20261015)`.
5. **Fits.** Asimov (set A); pseudo-data with sets A and B as a model set (min-max envelope); 100 toys (set A).
6. **Negatives.** No measurement (ungated, exit 1); rigidity bins (exit 1); unfolded level (exit 1); a component with
   unknown correlation (exit 3, `incomplete`).

Output: `output/results.json` (with the data values), `output/report.md`, and in `output/artifacts/` the fit inputs,
the covariance and the grid manifest. The envelope artifacts (grid nodes, theory-specs, data records) are not
committed (every committed artifact under `examples/` is snapshotted by `tests/contracts/test_gate_verdict_snapshot.py`);
`--keep DIR` writes them with a runnable `fit-input.json`. Test: `tests/examples/test_bc_propagation_fit.py`.

## Limits

D0 and L are not separately constrained by B/C in this model (only D0/L); the fit's position along the flat
direction is not a measurement. The cross-section envelope is a model-alternative spread of two placeholder sets.
No propagation code was run, and no published B/C benchmark is used (open question B1).
