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
  command's placeholders kept, so the record does not depend on where it ran. Each record names the argument list,
  the SHA-256 of every script in it, the plugin release and the Python and NumPy versions; `--incremental` skips a
  step whose previous record matches on all of them and on its inputs and outputs (never when the release digest is
  unknown, as in a development checkout). A step may declare `parameter_digest` (a command printing the digest of the
  design parameters it reads, e.g. `evaluate_design.py run --digest-only`) that replaces the candidate files in the
  skip key, so a design chain reruns only where a parameter it reads changed.
  Outputs are fresh and owned by the run: every input, output and `stdout` path must be relative to the work folder,
  without `..` and not through a symlink (anything else is refused before a step runs); an output left from before
  that the step did not rewrite makes the step fail; `--incremental` also reruns when the set of declared outputs
  changed. Each step runs in its own process group under its deadline (`timeout_s`, default 3600 s): on a timeout, or
  when the step leaves processes behind, the group is stopped and confirmed gone, and the record carries
  `end_status` (success, failure, timeout), `termination` (confirmed, unconfirmed), `output_contract` and
  `artifact_digest` (SHA-256 of the canonical output manifest). Output hashes are recorded only when termination is
  confirmed. Termination is observed on POSIX hosts (tested on Linux, where processes that leave the group are also
  found through an environment token); a process that leaves the group and clears its environment is not seen.
  `--receipt-dir DIR` writes one receipt per executed step outside the work folder (attempt, end status,
  termination, outputs with location and digest, artifact digest, declared inputs, run-record digest, times, wall and
  CPU seconds). A check step declares its `check` identity (check, criterion and target digests, criteria and result
  files, target manifest, role, type, read list); its result counts only when it binds to the run, otherwise the step
  fails. `executor_capabilities.py` qualifies the runner by fault injection (G1 output isolation, G2 termination on
  POSIX; G3–G6 unsupported) and refuses a capability whose declaration does not cite a passing, current
  qualification.
  `control_layer.py` keeps the task record of a T2-numeric+ deliverable (append-only, digest-chained, compare-and-set
  appends), admits each attempt, turns these receipts into facts and derives labels, achieved tiers, publish records
  and the completion report; its control rules did not pass the spec review, so its derivations are stated as such
  (see [research workflow control](research-workflow-control.md)).
  When the numbers will be delivered or used downstream (evidence tier T2-numeric or above), run one step per
  invocation in a fresh output directory and keep the task record of
  [research workflow control](research-workflow-control.md), which also sets the evidence tier and the completion
  report.
- `<plugin root>/skills/hep-computing/assets/workflow/`: a SYNTHETIC example DAG (`workflow.json`: generate events,
  histogram them chunk by chunk, report) and a `Snakefile` with the same rules. Snakemake adds incremental reruns
  (only steps whose inputs changed), cluster profiles and DAG plots; the runner (with `--incremental`) is the dependency-free reference the
  tests use. Keep the two in step: the tests check that the Snakefile has one rule per step with the same outputs.
- Other engines (Make, Nextflow, Luigi, law, coffea processors) fit the same pattern; what matters is declared files
  and a run record per step, not the engine.

## Large and partitioned steps

- A step that processes many files runs as a partitioned job: `<plugin root>/skills/hep-computing/scripts/local_partition.py`
  plans chunks with a manifest, resubmits failures within a bound, and merges with declared rules; batch campaigns
  on Slurm or HTCondor follow [batch scheduling](batch-scheduling.md). The workflow step is then the plan, the run
  and the merge, and its output is the merged file with its merge record.
- Chunked reductions inside a step follow [columnar and large-scale data](columnar-and-large-scale-data.md).

## Tying results to their runs

- Keep each published result's producing run records (computational-run: inputs with digests, output hashes) and the
  merge record of a partitioned run with the frozen bundle (see the [preservation checklist](preservation-checklist.md)).
  No tool checks the chain from result to runs any more: the analysis check's run-lineage suite was removed in 0.28.0.

## Checks

- A rerun on synthetic inputs is byte-identical (the runner's test does this).
- Every output of the final step traces back through run records to input checksums.
- The DAG has no cycle, and no step reads a file it did not declare.
