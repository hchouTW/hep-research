# J7 recast (SYNTHETIC, illustrative)

SYNTHETIC and ILLUSTRATIVE: invented search record and toy model; no experiment, search or physical model. No profile loaded. Seed 20261006, 20000 toys, CL 0.95.

Signal-count limit (CLs, background profiled): s < 9.571 for n = 9, b = 6.2 ± 1.4.
Check with sigma_b = 0: toys 9.568, closed form 9.718 (difference -1.54%).

| m_X (GeV) | sigma (g = 1, pb) | efficiency | expected signal (g = 1) | g^2 upper limit |
|---|---|---|---|---|
| 200 | 10.1250 | 0.310 | 62.775 | 0.152 |
| 300 | 2.0000 | 0.350 | 14.000 | 0.684 |
| 400 | 0.6328 | 0.390 | 4.936 | 1.939 |
| 500 | 0.2592 | 0.430 | 2.229 | 4.294 |
| 600 | 0.1250 | 0.470 | 1.175 | 8.145 |
| 700 | 0.0675 | 0.510 | 0.688 | 13.907 |
| 800 | 0.0396 | 0.550 | 0.435 | 21.999 |

Outside the map's validity (m_X = 1000 GeV): refused.
Gate: comparable at every mass after multiply-by-normalization and forward-fold; the variant that applies the efficiency before folding is rejected.

Criteria: gate_comparable_all_masses pass, gate_rejects_double_efficiency pass, outside_validity_refused pass, toy_vs_closed_form pass, coupling_limit_weakens_with_mass pass, contracts pass.

Limits: one signal region, so shapes and correlations between regions are not exercised; the efficiency map has no uncertainty of its own; the toy model is not physics. This shows the J7 chain and its contracts.

Reproduce: `python3 examples/recasting/run.py --toys 20000 --seed 20261006`
