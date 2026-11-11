# T09 photon-likelihood example: generate, fit, choose the topology, check (synthetic)

Generator t09-sphere/1, block 1 (tuning); main: fixture main, stratum 7, 2 event(s); two-source: fixture two-source, stratum 0, 1 event(s). Recipe reco.light.channel-likelihood/1 (a development binding), product light-likelihood-product/4, penalty 30. Label shared-model closure: the events and the fit share the analytic light model, so this tests the code, not the model. Synthetic data only. No photon-likelihood quality claim: these are the fits the programs wrote, not a resolution, a wrong-minimum rate or a mis-ID rate; T09's quality verdict waits for K09 at Freeze B.

| Sample | Event | H1 fit | Hit | Dead | Saturated | Converged H1 starts | lnL_1 | lnL_2 (from) | 2 (lnL_2 - lnL_1) | Choice |
|---|---|---|---|---|---|---|---|---|---|---|
| main | 0 | converged | 136 | 0 | 0 | 8 | -650.322 | -643.380 (h2) | 13.883 | H1 |
| main | 1 | converged | 228 | 0 | 0 | 8 | -981.699 | -981.699 (h1 boundary) | 0.000 | H1 |
| two-source | 0 | converged | 384 | 0 | 0 | 8 | -2426.155 | -1709.220 (h2) | 1433.869 | H2 |

| Check | Result |
|---|---|
| every operation is ok with exit 0 | pass |
| the recipe's commands name no truth file | pass |
| each product names the recorded readout, and the topology product the recorded multistart product | pass |
| the products were made with the configuration and budgets beside the recipe | pass |
| the products read back whole as the recipe's /3 and /4, label shared-model closure, ln L and the per-channel check recomputed | pass |
| the topology product carries its multistart product unchanged | pass |
| no live channel's hit and no-hit probabilities miss one, at H1's or H2's point (the T09 stop) | pass |
| the topology choice is the frozen rule: H2 if and only if 2 (lnL_2 - lnL_1) >= 30 | pass |
| the recipe run again on the recorded readouts reproduces the recorded products: byte for byte on the recording's platform, else within the stated tolerances | pass |
