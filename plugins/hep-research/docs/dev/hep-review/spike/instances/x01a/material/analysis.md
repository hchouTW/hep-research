# Combination of two cross-section measurements

Two measurements of the same cross section are combined with the best linear unbiased estimator (BLUE).
Each has a statistical uncertainty and a systematic uncertainty. Both measurements use the **same luminosity
calibration**, and the systematic uncertainty of each is entirely due to that calibration, so the two systematic
uncertainties are fully correlated between the measurements.

The covariance matrix is built from the uncertainties in data.json; the BLUE weights are w = V^-1 1 / (1^T V^-1 1)
and the combined uncertainty is (1^T V^-1 1)^-1/2. The combined value is reported in data.json.
