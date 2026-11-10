"""reco.calo.cell-cluster/1: the T08 development binding (t07-t09-task-sheets.md, T08; decisions.md, U12 A).

A development binding in Python, not a native backend: the native-integration gap stays open. Modules, in chain order:

- cell_input: the calo-cells/1 readout file (role reconstruction-input) and the calo-calibration-payload/1 payloads (role
  conditions). The readout holds raw values, live and saturated flags only: no truth, no seed, no generator field.
- gain_payload: calo-gain-payload/1, the gain per channel of a stated channel map with its role, and derived payloads that
  record their source (D2 stage 2; plan R32, R37).
- cell_chain: per cell, raw beside calibrated, each chain step with its payload identity, in chain order (plan R34).
- profile: the cell-integrated Gaussian of width W and its derivative in the centre.
- clustering: t04-values-v4.md section 7.1, followed step by step.
- product: calo-cluster-product/1, its writer and a reader that refuses a malformed or incomplete product (plan 8.3).
- recalibration: a product's objects re-evaluated under another gain payload with the membership and fractions held
  fixed (CAI-T08-1), and the two-peak objects re-shared on the same cells and peaks.

D2 stage 3 adds a labelled input: calo-cells/2 (cell_input), a readout converted from another simulation's deposits with its
label (simulated-unvalidated) and provenance; calo-cluster-configuration/2 (configuration), its configuration, which may give
no shower profile and no response model; and calo-cluster-product/3 (product), which carries the label and provenance. The
converter of the user-supplied zdcsim program's deposits is fixture_tools/t08_zdcsim_cells.py, outside the recipe.

Written from t04-values-v4.md sections 4.2 and 7.1 and skills/hep-detector/references/event-reconstruction.md#clustering. No
code is shared with the reference clusterer or the fixture generator, and nothing here imports either (section 3.1).
"""

RECIPE = "reco.calo.cell-cluster/1"
ENERGY_KIND = "clustered-deposited-energy"
