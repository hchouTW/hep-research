"""reco.scan.destriper/1: T10's destriping reference replay, a development binding in Python, not a native backend (decisions.md,
"The user's answer to U7"; the native scan or global solver stays a recorded gap, as U12 A).

The method is F38's as t11-cells.md records it: a joint fit of map and baselines, conjugate gradient for the baseline amplitudes,
then binning; the offset null mode fixed by an explicit zero-sum condition on the baselines. Modules:

- timestream: the destriper-timestream/1 reader (role reconstruction-input); refuses a scan whose map the data and one
  constraint do not determine (an unobserved pixel, more than one connected component).
- solver: conjugate gradient on the reduced baseline system restricted to the zero-sum subspace, then the map by binning.
- product: destriper-product/1 with the embedded reconstruction-product/1 (reconstruction:scan-v1, subcase global), its writer
  and a reader that refuses a malformed or incomplete product.

Nothing here imports the fixture generator, the exact reference or the comparator (assets/fixture_tools).
"""

RECIPE = "reco.scan.destriper/1"
LABEL = "synthetic; development binding, not native"
DEFAULT_STOPPING = 1e-10
BUDGET_PER_BASELINE = 10
