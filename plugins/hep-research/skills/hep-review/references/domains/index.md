# Domain cards (hep-review domain pack)

A domain card turns an owner skill's rules into review obligations: the questions to ask, the required material and
evidence, the methods, and what must not be confused. It never adds an outcome value and never changes kernel
semantics. The judging rules stay with the owner skill: load only what the obligation at hand needs. Citations are
never filled in from memory.

| Owner | Card | Status |
|---|---|---|
| hep-statistics | [statistics card](statistics.md) | pilot domain (T03): one positive and one negative case |
| hep-computing | [computing card](computing.md) | pilot domain (T03): one positive and one negative case |
| hep-theory, hep-measurement, hep-detector, hep-ml, hep-citations, hep-authoring | none yet | planned (spec 13.1); review them with the owner skill's rules and record the gap |

Cross-cutting questions need one obligation per owner: "the Python correctly implements an inappropriate likelihood"
is a computing obligation (supported) and a statistics obligation (violated); the first never overrides the second.

## Method cards

| Method | Produces | Never implies |
|---|---|---|
| assumption and convention check | a finding or support for each stated assumption | that unstated assumptions hold |
| numerical recomputation | recomputed values against stated ones, with the tolerance and its rounding rule | that the method is appropriate |
| reproduction | reference quantities, data version, environment, seed and tolerance fixed in advance | method validity; exit 0 is not reproduction |
| independent derivation or counterexample | a non-identical path to the result | independence of sources when inputs are shared |
| fix verification | the fix checked against the original finding | that other findings are fixed |
