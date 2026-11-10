"""reco.calo.cell-cluster/1: the T08 development binding (t07-t09-task-sheets.md, T08; decisions.md, U12 A).

A development binding in Python, not a native backend: the native-integration gap stays open. Modules, in chain order:

- cell_input: the calo-cells/1 readout file (role reconstruction-input) and the calo-calibration-payload/1 payloads (role
  conditions). The readout holds raw values, live and saturated flags only: no truth, no seed, no generator field.
- cell_chain: per cell, raw beside calibrated, each chain step with its payload identity, in chain order (plan R34).
- profile: the cell-integrated Gaussian of width W and its derivative in the centre.
- clustering: t04-values-v4.md section 7.1, followed step by step.
- product: calo-cluster-product/1, its writer and a reader that refuses a malformed or incomplete product (plan 8.3).

Written from t04-values-v4.md sections 4.2 and 7.1 and skills/hep-detector/references/event-reconstruction.md#clustering. No
code is shared with the reference clusterer or the fixture generator, and nothing here imports either (section 3.1).
"""

RECIPE = "reco.calo.cell-cluster/1"
ENERGY_KIND = "clustered-deposited-energy"
