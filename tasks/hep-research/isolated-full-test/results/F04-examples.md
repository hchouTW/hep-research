# F04 examples (E2, dd9b940)

Script `f04_examples.py` (venv Python): each example run twice into a scratch directory with its test's arguments,
then compared with the committed `output/`. Full data: `F04-examples.json`.

| Example | Exit (2 runs) | Rerun byte-identical | Committed output | Notes |
|---|---|---|---|---|
| ams-flux-ratio | 0, 0 | yes | **differs** | `observed_counts` identical; flux, ratio and T10/T11 values equal to rel 1e-9; **106 `toy_closure` summary values differ** (e.g. helium period-1 bin 1 mean pull −0.1012 vs −0.1102). All pass criteria hold on E2. Figures differ |
| batch-partition | 0, 0 | yes | identical | |
| collider-angular | 0, 0 | yes | differs | `results.json` numerically equal (rel 1e-9 / abs 1e-12); figure differs |
| detector-resolution | 0, 0 | yes | differs | `results.json` byte-identical; only the figure differs |
| local-partition | 0, 0 | yes | identical | |
| published-comparison | 0, 0 | yes | differs | numerically equal; `report.md` and `artifacts/result.json` differ in float digits |
| qed-prediction | 0, 0 | yes | differs | numerically equal; figure differs |
| recasting | 0, 0 | yes | identical | |
| theory-comparison | 0, 0 | yes | identical | committed output was regenerated on E2 in PR #17 |
| end-to-end-sample | 0, 0 | yes | n/a (no committed output) | `--seed 1` |

`[Inferred]` ams-flux-ratio toy closure: the first `simulate` call matches exactly. The toy loop then draws thousands
of `rng.poisson` and `rng.binomial` samples from rates computed in floating point. A rate that differs in the last
digit can change how many uniforms a draw consumes, and every later draw in the stream then differs. The
example's test only checks same-machine reruns, so nothing fails, but the committed toy-closure numbers are not
reproducible across platforms.

Figures (PNG) differ across platforms for five examples; no test compares them.
