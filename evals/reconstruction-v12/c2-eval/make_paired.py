"""Synthetic sample for the C2 paired missing-backend case. Truth: sigma(pT)/pT = sqrt(a^2 + (b*pT)^2),
a = 0.010, b = 0.0005 /GeV, applied to curvature k = 1/pT. 2% of rows are failed fits (pt_reco = -1, a sentinel)."""
import csv, sys
import numpy as np
rng = np.random.default_rng(20261030)
n = 200_000
pt = np.exp(rng.uniform(np.log(1.0), np.log(100.0), n))
eta = rng.uniform(-2.4, 2.4, n)
rel = np.sqrt(0.010**2 + (0.0005 * pt)**2)
k = (1 / pt) * (1 + rng.normal(0, 1, n) * rel)
reco = 1 / k
bad = rng.random(n) < 0.02
reco[bad] = -1.0
with open(sys.argv[1], "w", newline="") as f:
    w = csv.writer(f); w.writerow(["track_id", "pt_true_gev", "eta", "pt_reco_gev"])
    for i in range(n):
        w.writerow([i, f"{pt[i]:.6f}", f"{eta[i]:.5f}", f"{reco[i]:.6f}"])
