# Analysis preservation checklist

What a measurement keeps so that someone else, or you in five years, can rerun it and get the same numbers, and can
re-fold a new prediction through the same detector response. Rehearse it once, on the real chain, before data taking
or the analysis team ends: a checklist nobody has replayed is a wish list.

Each item names the file or command that holds it. Paths are relative to the plugin root unless they say otherwise.

## 1. Environment

- [ ] A manifest of every environment that produced a number: `<plugin root>/skills/hep-computing/scripts/environment_manifest.py`
      `record --project DIR --inputs ... --out env.json` (Python, packages, system, origin such as an LCG view or a
      container, git commit and dirty state). See [environments and containers](environments-and-containers.md).
- [ ] `environment_manifest.py check --manifest env.json` passes on the machine that will rerun it, or its drift list is
      written down and accepted.
- [ ] For each era, the data and simulation software versions agree: `environment_manifest.py pairs` (a mismatch
      fails, an undeclared version is incomplete).
- [ ] The container image or LCG view is archived by digest, not by a floating tag.

## 2. Inputs

- [ ] Every input file is listed with its path, SHA-256 and size (the `input_manifest` of a computational-run,
      `<plugin root>/contracts/schemas/ext_computational_run.json`).
- [ ] Inputs that cannot be archived (large raw data, access-controlled productions) are named by their dataset
      identifier and production version, and the custodian who can restore them is recorded.
- [ ] Partitioned inputs have their manifest and merge record (`<plugin root>/skills/hep-computing/scripts/local_partition.py`,
      [batch scheduling](batch-scheduling.md)): no duplicate or missing chunk.

## 3. Recipe

- [ ] The exact commands, seeds, tolerances and exit statuses of every step, as computational-run artifacts
      (`<plugin root>/contracts/validate.py` checks them).
- [ ] The workflow that chains the steps is in version control and reruns end to end
      ([analysis workflows](analysis-workflows.md)).
- [ ] Each correction is a recipe step with its correction key, so a later reader can see which factor was applied
      where.

## 4. Frozen analysis definition

- [ ] The v2 analysis bundle (`<plugin root>/contracts/schemas/analysis_bundle_v2.json`) is frozen with its
      semantic lock: `python3 <plugin root>/contracts/analysis_check.py freeze --root DIR --analysis NAME --items ITEMS.json
      --context CONTEXT.json --out bundle.json`.
- [ ] The definition snapshots freeze writes to `DIR/.hep-research/snapshots/` (or to the folder given with
      `--snapshots`; the bundle index is `DIR/.hep-research/bundles.json`) are archived with the bundle: they let a
      later check use the definitions that were current at freeze time, not today's.
- [ ] `analysis_check.py check bundle.json --root DIR` reruns on the archive (it reads that store). Its report is a
      diagnostic; it authorizes nothing.

## 5. Results and their bindings

- [ ] Every quoted number comes from an artifact (statistical-result, dataset-record) whose sha256 is recorded, and
      the paper's numbers are rendered from those artifacts, not retyped.
- [ ] Result bindings (`<plugin root>/contracts/schemas/result_binding.json`) tie each published result to the runs
      and the complete merge that produced it.

## 6. Products that can be re-folded

- [ ] The response matrices (with their normalization, inefficiency location and flow handling; see
      [response and forward folding](../../hep-detector/references/response-and-forward-folding.md)), the per-era
      collection time and acceptance, and the covariance of the result, so that a new model can be re-folded and
      compared without rerunning the analysis.
- [ ] A small re-fold test: fold the published prediction through the archived response and reproduce the published
      reco-level expectation to the declared tolerance.
- [ ] Where the measurement goes to HEPData, the record carries the same values as the artifacts.

## 7. Rehearsal

- [ ] Someone who did not build the analysis restores the archive on a clean machine, reruns the workflow, and
      compares the outputs with the archived hashes; every difference is explained and recorded.
- [ ] The rehearsal date, who did it, and its outcome are written in the analysis notes, with the evidence the
      [definition of done](validation-and-done.md) asks for.
