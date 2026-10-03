# Batch scheduling: Slurm and HTCondor

How to run manifest-partitioned work (event generation, histogram filling, toys, systematic variations) on a Slurm
or HTCondor cluster with the same guarantees as the local engine: seeds from the manifest, write-once outputs, no
duplicate ever summed, bounded and explicit retries, a merge that needs every chunk exactly once.

Code: `core/partition/` (engine, campaign, worker-side runner, normalized states) and the optional adapter
`adapters/batch-schedulers/` (`batch_campaign.py` CLI, `slurm_backend.py`, `htcondor_backend.py`, `batch_config.py`,
templates in `assets/`). Status: **documented**. Both backends are tested only against fake schedulers
(`tests/adapters/batch_shims/`); no real Slurm or HTCondor has run them, and the tool facts below are not yet checked
against the tools' documentation (see "Tool facts"). Treat the first real run on your site as a pilot.

## When to batch, and when not

Batch it when the work splits into independent chunks whose results add up: event generation, filling histograms
over input files, pseudo-experiments for `hep-statistics`, systematic variations, one GPU training job per
configuration. Do not use this for:

- multi-stage pipelines with dependencies between stages (generate, reconstruct, fill, merge): use a workflow system
  or the scheduler's dependency features yourself; this adapter submits one stage;
- grid or experiment workload systems, Kubernetes or cloud batch services (out of scope);
- multi-node distributed training: `physics-ml`'s distributed-training reference owns that.

## The workflow

```
python3 batch_campaign.py check-config --config batch-config.json
python3 batch_campaign.py plan     --config batch-config.json --job toys --items 100000 --chunk-size 1000 --seed 42 \
        --cmd "python3 toy.py --start {start} --stop {stop} --seed {seed} --out {out}"
python3 batch_campaign.py submit   --config batch-config.json --pilot            # dry run: shows the job files
python3 batch_campaign.py submit   --config batch-config.json --pilot --submit   # one chunk, to size the rest
python3 batch_campaign.py status   --config batch-config.json                    # one poll: elapsed, peak memory
python3 batch_campaign.py submit   --config batch-config.json --submit           # the remaining chunks
python3 batch_campaign.py watch    --config batch-config.json                    # needs monitor limits
python3 batch_campaign.py resubmit --config batch-config.json                    # dry run: decisions per chunk
python3 batch_campaign.py reset    --config batch-config.json --chunks c0042 --reason "input path fixed"
python3 batch_campaign.py merge    --config batch-config.json
python3 batch_campaign.py report   --config batch-config.json --out artifacts/toys-run.json --label synthetic
```

The script is `${CLAUDE_PLUGIN_ROOT}/adapters/batch-schedulers/batch_campaign.py`. Exit codes: 0 done, 1 incomplete
or blocked, 2 refused. `submit` and `resubmit` are dry runs without `--submit`; `cancel` needs `--approve-cancel`.
Ask the user before every command that submits, cancels or writes to a shared area, each time.

## Configuration: site facts come from the user

One JSON file per campaign, in the user's project (never in the plugin). Required: `backend`, `campaign_dir`,
`resources`; for Slurm `slurm.partition` and `resources.time_limit`; for HTCondor `htcondor.universe`,
`htcondor.file_transfer` and, for the container universe, `htcondor.container_image`. Unknown keys are refused.
Never fill in a partition, account, QoS, pool requirement, memory or time limit, GPU type or file-system path the
user did not give: ask, or point them to their site's documentation. The shipped example
(`assets/batch-config.example.json`) holds only placeholders and validates only with `--example`.

## Slurm and HTCondor side by side

| Topic | Slurm (adapter behavior) | HTCondor (adapter behavior) |
|---|---|---|
| Many chunks | one job array per submission, `--array=0-(n-1)%throttle`; the array index reaches a chunk only through `map.json` | one cluster per submission, `queue chunk_id, attempt_id from items.txt`; each process gets its IDs as item data |
| Files | shared file system: the runner writes into `outputs/<chunk>/` | `file_transfer: shared-filesystem` as Slurm, or `transfer`: the job writes in its scratch directory and `transfer_output_remaps` brings `<attempt>.json` and `<attempt>.meta.json` back into `outputs/<chunk>/` |
| Scheduler restarts | `--no-requeue`; if the site still requeues, `sacct --duplicates` shows earlier records and each counts as an attempt | eviction restarts the job; every extra execute event counts as an attempt; output is transferred only on exit |
| Observing | accounting (`sacct`), else queue (`squeue`) plus the runner's meta files, marked `queue+outputs` | the job event log (survives the queue), confirmed with `condor_q` / `condor_history -json` |
| Held jobs | `REQUEUE_HOLD` maps to held | event 012 with reason and code; never released by the plugin |
| Exit status | `ExitCode` as `exit:signal` | terminated event: return value or signal |
| Resources | `--cpus-per-task`, `--mem=<n>M`, `--time`, `--gpus`, `--tmp`, `--constraint`, `--gres` | `request_cpus`, `request_memory = <n>MB`, `request_disk = <n>MB`, `request_gpus`, `requirements` |
| Containers | run the container inside your command | `universe = container`, `container_image` |
| Throttle | `%M` in the array range | `max_materialize` |

Normalized states: `planned, queued, running, done, failed, timeout, out-of-memory, preempted-or-evicted,
node-failure, held, cancelled, lost, unknown`. A native state the adapter does not know is `unknown`, never success.

## Sizing

- Submit a pilot chunk first; `status` reports its elapsed time and peak memory. Set `time_limit` and `memory_mb`
  from it with headroom you can justify (for example the pilot value plus the spread you expect between chunks).
  The plugin never raises a request on its own.
- Chunk count: keep each chunk long enough that scheduling overhead is small, and the array or queue within your
  site's limits (maximum array size, jobs per user): these are site facts; ask, never assume.
- Throttle so the shared file system and the scheduler are not flooded.
- Heavy work never runs on login nodes; only `plan`, `check-config`, `status` and `merge` belong there.

## The plugin's rules applied

- **Seeds** come from the manifest, never from a job ID or array index (those change on resubmission).
- **Write-once:** the runner links its output into place without overwriting; a second execution of the same attempt
  writes `<attempt>.rerun-<k>.json`. Collection ingests the first valid output by attempt order into
  `chunks/<chunk>.json`; every other valid output is a duplicate, recorded and never summed. Invalid outputs (another
  manifest, unknown attempt, wrong range or seed, non-finite numbers, truncated files) go to `quarantine/` with a reason.
- **Bounded retries:** nothing is resubmitted without `max_attempts`. Preemption, node failure and lost jobs may be
  resubmitted within it; timeouts and out-of-memory only after the resource request changed (the change is recorded
  in the attempt); failed, held, cancelled and unknown chunks only after `reset` with a reason. Two identical failure
  signatures (state, exit code, signal, hold code; never host or time) in a row stop the chunk, across resets.
- **A scheduler's success is not a result:** a job reported complete without a valid output is `lost`.
- **Held jobs need a person.** `watch` stops early on held, unknown or stopped chunks.
- **Polling etiquette:** `status` polls once. `watch` needs `monitor.poll_interval_s` (at least 60) and
  `monitor.max_polls` or `monitor.deadline_s`; it stops when everything is done or settled, early on problems or on
  the same poll error twice, and at its limit it reports `incomplete`. It never resubmits.
- **Logs are outputs.** Job stdout and stderr (`*.stdout.log`, `*.stderr.log`), event logs and job files live under
  `campaign_dir/submissions/`; scan them with `scripts/audit_blinded_outputs.py scan` before sharing anything from a
  blinded analysis.
- **No credentials.** The adapter reads, stores and passes no passwords, tokens or grid proxies; authentication is
  the user's environment.
- **Provenance:** `report` writes a `computational-run` artifact with input hashes, the queried scheduler version,
  the exact submit commands, the config and its hash, per-attempt records in `environment.execution`, seeds,
  per-chunk and merged output hashes, and per-attempt elapsed time and peak memory. An incomplete campaign is labeled
  `failed` with a non-zero exit status. A complete merge says nothing about physics correctness.

## Consumers and handoffs

- `hep-statistics` toy campaigns: a dropped chunk can bias a coverage study the same way dropped failed fits do. Merge
  only complete campaigns, or report the missing chunks with the result; never rescale a partial merge silently.
- `physics-ml` single-node GPU training: one job per configuration with `gpus` in the resources; the model, its
  training and its validation stay with `physics-ml`.

## Worked walkthrough (reproduced by `examples/batch-partition/`)

The T21 synthetic job (200,000 events, 10 chunks of 20,000) runs on both fake schedulers with injected faults.
`output/results.json` records, for each backend: the dry run made no scheduler call; c0001 ran twice and was
collected once (1 duplicate); with no `max_attempts` nothing was resubmitted (c0003 and c0004 blocked); with
`max_attempts: 3` and `memory_mb` 1000 → 2000, c0003 was resubmitted with the change recorded (HTCondor: after a
reset, because it was held); c0004 failed with exit code 3 twice and stopped (`stopped-repeated-failure`), resubmit
refused it until a reset after the fix; the merge then equals the local single-run merge exactly; the artifact
validates with status `synthetic, unvalidated`; the logs pass the blinding audit.

## Tool facts

Every option, field, state code and output format the backends emit or parse. **Status: not yet checked** against
the tools' documentation: the documentation pages could not be read when this was written, and no real Slurm or
HTCondor was run. The fake schedulers implement the formats as listed, so the shim tests show the adapter is
internally consistent, not that it agrees with the real tools. Check each row against the documentation of the
version you use (record version and date here) or a real run before relying on it.

| Fact used | Where | Source to check |
|---|---|---|
| `sbatch --parsable` prints `jobid[;cluster]` | Slurm submit | sbatch man page |
| `--array=A-B%M` (throttle `%M`), `--no-requeue`, `--output`/`--error` with `%A` (array job ID) and `%a` (task index), `--partition`, `--account`, `--qos`, `--constraint`, `--gres`, `--time`, `--cpus-per-task`, `--mem=<n>M`, `--gpus`, `--tmp`, `--job-name`; `SLURM_ARRAY_TASK_ID` in the job | Slurm template | sbatch man page; job array guide |
| `sacct --jobs=<ids> --duplicates --parsable2 --noheader --format=JobID,State,ExitCode,Elapsed,MaxRSS,NodeList`; array tasks as `<job>_<task>`, steps as `<job>_<task>.batch`, pending ranges as `<job>_[a-b%m]`; `ExitCode` as `exit:signal`; `CANCELLED by <uid>`; Elapsed `[D-]HH:MM:SS` | Slurm poll | sacct man page |
| State codes PENDING, CONFIGURING, REQUEUED, REQUEUE_FED, RUNNING, COMPLETING, STAGE_OUT, RESIZING, COMPLETED, FAILED, TIMEOUT, OUT_OF_MEMORY, CANCELLED, NODE_FAIL, BOOT_FAIL, PREEMPTED, REQUEUE_HOLD, SPECIAL_EXIT | Slurm state map | sacct / squeue job state codes |
| `squeue --jobs=<ids> --array --noheader --format=%i\|%T` | Slurm fallback | squeue man page |
| `scancel <job>_<task>` | Slurm cancel | scancel man page |
| Submit description: `universe` (vanilla, container), `container_image`, `executable`, `transfer_executable`, `arguments = "..."`, `log`, `output`, `error`, `should_transfer_files`, `when_to_transfer_output = ON_EXIT`, `transfer_input_files`, `transfer_output_remaps = "a = b; c = d"`, `request_cpus`, `request_memory`/`request_disk` with an `MB` suffix, `request_gpus`, `requirements`, `max_materialize`, `queue a, b from file`; macros `$(name)` | HTCondor template | condor_submit man page; file transfer section |
| Default exit handling (no `max_retries`, `on_exit_remove`, `periodic_release`) means no automatic retry | HTCondor template | condor_submit man page |
| `condor_submit -terse` prints `<cluster>.<first> - <cluster>.<last>` | HTCondor submit | condor_submit man page |
| Job event log: header `NNN (cluster.proc.subproc) date time text`, events separated by `...`; codes 000, 001, 002, 004, 005 (`(1) Normal termination (return value N)` / `(0) Abnormal termination (signal N)`, `Memory (MB) : usage`), 007, 009, 010, 011, 012 (reason line, `Code N Subcode M`), 013 | HTCondor poll | job event log codes |
| `condor_q` / `condor_history <cluster> -json -attributes ...`; JobStatus 1 idle, 2 running, 3 removed, 4 completed, 5 held, 6 transferring output, 7 suspended; ExitCode, ExitBySignal, ExitSignal, HoldReason, HoldReasonCode, HoldReasonSubCode, NumJobStarts | HTCondor fallback | condor_q, condor_history man pages; job ClassAd attributes |
| `condor_rm <cluster>.<proc>`; `condor_version`; `sbatch --version` | cancel; provenance | man pages |
