# Brief for the error planter

You plant errors in a small synthetic physics analysis, so that we can measure which existing checks notice them.
You did not write any of the checks, and you must not look at them: work only with the files in your kit folder.

## What is in the kit

| File | What it is |
| --- | --- |
| `run.py` | the analysis program: simulates a synthetic proton and helium flux in two periods, unfolds (truncated SVD), corrects, normalizes, forms the He/p ratio, runs closure tests, and writes the descriptive artifacts (`measurement_spec.json`, responses, dataset records) |
| `reference-output/` | what the unchanged `run.py` writes (for reading only) |
| `recipe.json` | hand-written description of the per-species, per-period chain of operations |
| `context.json` | hand-written description of the analysis intent: the results (roots) and their units and binning, which recipe produces each species and period (instances), which response each instance uses (bindings), declarations of which spec corrections apply where, and the He/p ratio results |
| `operators.json` | the vocabulary of operator names a recipe step may use, with what each operator does |
| `taxonomy.md` | the error categories and quotas |

## What to produce

In your output folder, one subfolder per case:

- `E01` … `E20` (or more): **errors**. Each is a realistic honest mistake from `taxonomy.md`, made the way one analyst
  who writes both the code and the descriptions would make it. Change `run.py` **and** at least one description
  (`recipe.json`, `context.json`, or text and fields that `run.py` writes into the spec or records). The descriptions
  need not stay truthful to the code: an analyst may describe what they meant, what they did, or something half-way.
- `R01` … `R10` (or more): **legitimate refactors** that keep the analysis correct, also touching the code and at
  least one description.

Each subfolder holds only the changed files (full copies, same file names: `run.py`, `recipe.json`, `context.json`)
and a `key.json`:

```json
{"kind": "error" | "refactor", "category": "C01" … "C12" (errors only), "planter": "ai",
 "summary": "one sentence: what was changed and why it is wrong (or why it is still correct)",
 "code_change": "what changed in run.py", "description_change": "what changed in which description",
 "affected": ["ids from the descriptions that the change concerns: effect ids such as trigger_efficiency, instance ids such as helium-p1, root ids such as flux-helium-p2 or ratio-p1, step ids such as efficiency"]}
```

## Rules

1. Read only the kit. Do not open, search or list anything else on the machine (in particular no plugin, repository,
   cache or test folders), and do not run the analysis.
2. Keep `run.py` valid Python (check with `python3 -m py_compile`); keep the JSON files valid JSON. An error should be
   subtle enough that a careful analyst could make it; it need not break any closure test.
3. Use every category at least once and no category more than three times; vary which descriptions you change.
4. Do not tailor errors to any checker you imagine; plant what a real analysis would get wrong.
5. Finish with a short table: case, kind, category, one-line summary.
