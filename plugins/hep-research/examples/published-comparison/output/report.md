# T24 report: prediction vs a synthetic published-style record (SYNTHETIC)

The record (`synthetic-published-record.json`) is synthetic: its values and covariance are copied from the Path B output. Only the record and its covariance file are used; no detector module, response or experiment-profile file is read.

Reproduce: `python3 examples/published-comparison/run.py` (from the plugin root).

Gate: comparable after level-identification, fiducial-restriction (both justified), with declared convention mappings.

mu = 0.9951 ± 0.0218; chi2 = 10.27 / 9 (p = 0.33). Whitened least squares gives the same mu to 2.2e-16. Fiducial prediction 744.09 pb.

Limitation: the record's luminosity block is built from the measured values (fully correlated, proportional to the data); a Gaussian GLS normalization fit with such a matrix is known to be biased low for multiplicative uncertainties (Peelle's pertinent puzzle), so mu here can differ from the ratio of fiducial cross sections.

| Check | Result |
|---|---|
| gate_comparable | pass |
| mu_matches_whitened_lstsq | pass |
| chi2_reasonable | pass |
| no_detector_files_read | pass |
| contracts | pass |

Files read: `.claude-plugin/plugin.json`, `contracts/schemas/common.json`, `contracts/schemas/envelope.json`, `contracts/schemas/ext_comparison_spec.json`, `contracts/schemas/ext_statistical_result.json`, `contracts/vocab/core.json`, `examples/published-comparison/synthetic-published-covariance.json`, `examples/published-comparison/synthetic-published-record.json`, `examples/qed-prediction/output/artifacts/prediction.json`, `release-manifests/0.4.0.json`
