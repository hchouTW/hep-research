# Error taxonomy (frozen before planting)

Frozen 2026-10-22, before any error was planted (protocol step 3, `decision-value-gate.md`). Categories describe
**what goes wrong in the analysis**, never which checker rule might see it. Sources: the T3 threat class of
`docs/protected-data-architecture.md` ("repeated corrections, units, normalization, denominators"), the level and
frame distinctions of `docs/dev/cross-artifact-check/crflux-review.md`, and the correction-chain, background, ratio
and blinding practice of the `hep-measurement` skill. Published errata were **not** consulted in this session
(**Unresolved**; recorded as a deviation from protocol step 3).

| ID | Category | Examples of an honest mistake (not exhaustive) |
| --- | --- | --- |
| C01 | Repeated correction | an efficiency or the acceptance applied twice (in the estimator and again inside the exposure, or by the response and again afterwards) |
| C02 | Omitted correction | an efficiency, the livetime or the cutoff fraction left out of the chain |
| C03 | Correction at the wrong stage or on the wrong quantity | an efficiency applied to folded counts when the response already contains it; a background subtracted after unfolding |
| C04 | Normalization and denominators | exposure or livetime of the wrong period; bin width missing, applied twice or in the wrong variable; wrong solid angle |
| C05 | Units, conventions and level | GV against GeV or GeV/n; m² against cm²; top-of-instrument against interstellar |
| C06 | Binning and range | edges in the code differ from the spec; reported range or buffer bins changed in one place only |
| C07 | Response misuse | a response of the wrong species or period; a response used for unfolding that was built for folding; the migration treatment changed in one place only |
| C08 | Background | not subtracted; subtracted twice; estimated for the wrong species or region; a transfer factor of another period |
| C09 | Ratio and correlations | a term treated as cancelling that does not cancel, or as independent when shared; numerator and denominator swapped |
| C10 | Scope of corrections | a correction applied to one species or period only; species or periods mixed up in the chain or the average |
| C11 | Blinding | a blinded bin read or published; the blinding state or region described differently from what the code does |
| C12 | Uncertainties | a systematic component dropped; a correlated component treated as uncorrelated, or the reverse |

**Planting quotas.** At least 20 errors; every category used at least once; at most 3 errors per category. Each error
changes the code (`run.py`) **and** at least one description (`recipe.json`, `context.json`, or the spec and record
text that `run.py` writes), the way the error would show up when one analyst writes both.

**Legitimate refactors.** At least 10 changes that keep the analysis correct, also touching the code and at least
one description (renamed steps or ids, equivalent reorderings, merged or split steps that do the same thing,
rewritten rationale text, equivalent numerical rewrites).
