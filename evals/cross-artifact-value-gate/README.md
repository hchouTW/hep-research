# Value gate of the cross-artifact analysis check

Phase 1 measurement of the plugin's cross-artifact check (architecture section 10; record
`plugins/hep-research/docs/dev/cross-artifact-check/decision-value-gate.md`). It asks how many planted analysis
errors the checker catches that the existing defences miss, and at what false-positive and authoring cost. Checker
outcomes are advisory diagnostics (HC-05); this measurement authorizes nothing.

| Path | Content |
| --- | --- |
| `subject/recipe.json`, `subject/context.json` | the hand-written descriptions of the subject: the TSVD chain of `examples/ams-flux-ratio/run.py` and the check-context (four flux roots, two He/p ratio roots, response bindings, instance mappings) |
| `taxonomy.md` | the error categories and quotas, frozen before planting |
| `planter-brief.md` | the brief the planter works from |
| `measure.py` | the measurement: three layers per case, comparison with the baseline report, summary against the pre-registered thresholds |
| `cases/` | the planted errors (`E*`) and refactors (`R*`), each with `key.json` |
| `results/` | `results.json` and `results.md` of the recorded run |

Run from the repository root:

```bash
python3 evals/cross-artifact-value-gate/measure.py --cases evals/cross-artifact-value-gate/cases --out OUT --sensitivity
```

About 5 s per case and arm. Needs numpy and matplotlib (the example's environment). Work files go to `OUT/work/`.
