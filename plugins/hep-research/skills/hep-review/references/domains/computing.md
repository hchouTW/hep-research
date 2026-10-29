# Computing domain card (owner: hep-computing)

Questions: does the implementation match the specified method; can the stated numbers be recomputed from the stated
inputs; are units, bins, indices, seeds, I/O and environment traceable; is numerical error within the stated
tolerance?

| Field | Content |
|---|---|
| Typical required material | source code or the computation description, the input files, reference inputs and outputs, tolerances, the environment record |
| Methods | numerical recomputation; reproduction (reference quantities and tolerance fixed in advance); static reading of code (no import, no execution without enforced restrictions) |
| Evidence | recomputed values with the tool and environment that produced them (`tools` recorded on every attempt; `tools: []` only for pure reasoning) |
| Do not confuse | passing tests or exit 0 with method correctness; reproducing the author's numbers with the method being appropriate (that is the statistics obligation) |
| decision_required | usually false when a statistics obligation carries the decision |

Executing reviewed code is controlled execution (T06, not implemented): without enforced restrictions, review
statically and record the gap.

## Positive case (supported)

A weighted mean with inverse-variance weights; the stated mean and uncertainty 1/√(Σ 1/σᵢ²) recompute within the
0.1% tolerance with the stated precision. Expected: `supported`.

## Negative case (violated)

The stated uncertainty 0.0055 differs from the recomputed 0.005541 by 0.74%, outside the 0.1% tolerance, because it was
rounded to two significant figures. Expected: `violated` (minor) with the element and both values; the statistics
obligation stays `supported` because the method is right.
