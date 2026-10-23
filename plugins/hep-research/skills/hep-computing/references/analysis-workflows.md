# Analysis workflows

An analysis is a DAG of steps: each step reads declared inputs, writes declared outputs, and can be rerun alone.
Writing it down as a DAG (rather than as a sequence of commands in someone's shell history) is what makes a result
reproducible, partial reruns safe, and the provenance of every number checkable.

## The pattern

- **One step, one command, declared files.** A step lists its inputs and outputs; it reads nothing else and writes
  nothing else. Configuration is an input file, not an environment variable.
- **A computational-run per step.** Each step leaves a record with its inputs and their SHA-256, the command, the
  environment, seeds, tolerances, exit status and output hashes (`<plugin root>/contracts/schemas/ext_computational_run.json`).
  A later step that consumes an output can check it against the record.
- **Deterministic outputs.** Seeds are explicit; outputs carry no timestamps, host names or absolute paths, so a
  rerun on the same inputs is byte-identical and a changed hash means a changed result.
- **Fail loudly.** A step that exits non-zero, or exits zero without writing its outputs, stops the chain; nothing
  downstream runs on a partial result.

## Tools

- `<plugin root>/skills/hep-computing/scripts/run_workflow.py`: a standard-library runner for a workflow JSON (steps
  with `needs`, `inputs`, `outputs`, `argv`, optional `stdout` and `seeds`). It runs the steps in a topological
  order, refuses cycles and missing inputs, and writes `runs/<step>.computational-run.json` per step with the
  command's placeholders kept, so the record does not depend on where it ran.
- `<plugin root>/skills/hep-computing/assets/workflow/`: a SYNTHETIC example DAG (`workflow.json`: generate events,
  histogram them chunk by chunk, report) and a `Snakefile` with the same rules. Snakemake adds incremental reruns
  (only steps whose inputs changed), cluster profiles and DAG plots; the runner is the dependency-free reference the
  tests use. Keep the two in step: the tests check that the Snakefile has one rule per step with the same outputs.
- Other engines (Make, Nextflow, Luigi, law, coffea processors) fit the same pattern; what matters is declared files
  and a run record per step, not the engine.

## Large and partitioned steps

- A step that processes many files runs as a partitioned job: `<plugin root>/skills/hep-computing/scripts/local_partition.py`
  plans chunks with a manifest, resubmits failures within a bound, and merges with declared rules; batch campaigns
  on Slurm or HTCondor follow [batch scheduling](batch-scheduling.md). The workflow step is then the plan, the run
  and the merge, and its output is the merged file with its merge record.
- Chunked reductions inside a step follow [columnar and large-scale data](columnar-and-large-scale-data.md).

## Results the analysis check can bind

- The outputs that become published results are bound to the runs that made them with a result binding
  (`<plugin root>/contracts/schemas/result_binding.json`); the advisory, experimental and deprecated suite `run-lineage/v1` (removed in the next minor release) of the analysis check
  (`<plugin root>/contracts/analysis_check.py`, shadow mode) reads those bindings, the run records and the merge
  records to show that a result descends from a complete merge of the declared inputs.
- Keep run records and bindings with the frozen bundle (see the [preservation checklist](preservation-checklist.md)).

## Checks

- A rerun on synthetic inputs is byte-identical (the runner's test does this).
- Every output of the final step traces back through run records to input checksums.
- The DAG has no cycle, and no step reads a file it did not declare.
