# T08 calorimetry example: generate, reconstruct, check (synthetic)

Generator t08-grid/1, block 1 (tuning), variant main, stratum 7, 2 events, recipe reco.calo.cell-cluster/1 (a development binding), product calo-cluster-product/1, energy kind clustered-deposited-energy. Synthetic data only. No calorimetry quality claim: the counts are what the programs wrote, not an efficiency or a resolution; T08's quality verdict waits for K09 at Freeze B.

| Event | Objects | Kinds | Components | Without objects | Kept cells | Unclustered cells | Dead | Saturated |
|---|---|---|---|---|---|---|---|---|
| 0 | 2 | two-peak 2 | 1 | 0 | 90 | 1510 | 0 | 0 |
| 1 | 2 | two-peak 2 | 1 | 0 | 92 | 1508 | 0 | 0 |

| Check | Result |
|---|---|
| every operation is ok with exit 0 | pass |
| the recipe's commands name no truth file | pass |
| the product names the recorded cells file and payloads | pass |
| the product was made with the t08-grid/1 configuration | pass |
| the product reads back whole, clustered deposited energy, never incident energy | pass |
| no cell is counted twice | pass |
| the kept cells are section 7.1's selection and hit and unhit cells account for the input (A38) | pass |
| the recipe run again on the recorded cells writes the recorded product | pass |
