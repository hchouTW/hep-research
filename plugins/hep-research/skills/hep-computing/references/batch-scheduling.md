# Batch scheduling: Slurm and HTCondor

How to run manifest-partitioned work (event generation, histogram filling, toys, systematic variations) on a Slurm
or HTCondor cluster with the same guarantees as the local engine: seeds from the manifest, write-once outputs, no
duplicate ever summed, bounded and explicit retries, a merge that needs every chunk exactly once.

Code: `core/partition/` (engine, campaign, worker-side runner, normalized states) and the optional adapter
`adapters/batch-schedulers/` (`batch_campaign.py` CLI, `slurm_backend.py`, `htcondor_backend.py`, `batch_config.py`,
templates in `assets/`). Status: **documented**. Both backends are tested only against fake schedulers
(`tests/adapters/batch_shims/`); no real Slurm or HTCondor has run them, and the tool facts below were
checked against the tools' documentation only (see "Tool facts"; a few formats are not stated there). Treat the first real run on your site as a pilot.

**Submission is unsandboxed execution.** The scheduler client runs outside the agent sandbox, and the job script runs
on worker nodes with the user's permissions, so submitting runs code the agent just wrote outside every boundary the
sandbox gives. Until a trusted submitter is qualified (one that runs only frozen bundles verified by full digest), use
`submit` and `resubmit` only in a disposable test environment, on synthetic data, with each submission explicitly
approved by the user from a configuration the user has reviewed. With protected data the agent prepares a bundle and a
trusted submitter outside the agent's reach submits it; `confirm`, `abandon` and `cancel` are then not agent commands.

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

The script is `<plugin root>/adapters/batch-schedulers/batch_campaign.py`. Exit codes: 0 done, 1 incomplete
or blocked, 2 refused. `submit` and `resubmit` are dry runs without `--submit`; `cancel` needs `--approve-cancel`.

Only one command changes a campaign at a time: each holds a lock on `<campaign_dir>/.lock`, and a second one is refused
(`campaign.locked`) instead of racing it. `submit` records its attempts before it calls the scheduler. If it is
interrupted after that (a kill, a lost connection), the submission stays unconfirmed and nothing is submitted again
until you look at the scheduler: `confirm --submission S --jobs ATTEMPT=JOB ...` with the jobs it lists, or
`abandon --submission S --reason TEXT` when it has none (those chunks then need `reset` before `resubmit`).
Ask the user before every command that submits, cancels or writes to a shared area, each time; approval does not make
submission sandboxed (see above).

## Configuration: site facts come from the user

One JSON file per campaign, in the user's project (never in the plugin). Required: `backend`, `campaign_dir`,
`resources`; for Slurm `slurm.partition` and `resources.time_limit`; for HTCondor `htcondor.universe`,
`htcondor.file_transfer` and, for the container universe, `htcondor.container_image`. Unknown keys are refused.
Never fill in a partition, account, QoS, pool requirement, memory or time limit, GPU type or file-system path the
user did not give: ask, or point them to their site's documentation. The shipped example
(`assets/batch-config.example.json`) holds only placeholders and validates only with `--example`; it has a `slurm`
and an `htcondor` section: keep the chosen backend's section, delete the other (and `resources.time_limit` for
HTCondor), and replace every placeholder.

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
  `campaign_dir/submissions/`. From a blinded analysis they return through the same release and scanning rules as
  every other output: scanning against real sealed values is done by the data custodian or by a person outside the
  agent session (an agent runs `scripts/audit_blinded_outputs.py scan` only with synthetic sentinels), and a passing
  scan never authorizes sharing.
- **No credentials.** The adapter reads, stores and passes no passwords, tokens or grid proxies. Scheduler CLIs and
  jobs still inherit the user's environment today, so keep tokens and agent sockets out of it; with protected data,
  scheduler credentials must be unreachable from the sandbox and the trusted submitter verifies full digests of the
  runner and spec (the campaign copies are agent-writable).
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

Every option, field, state code and output format the backends emit or parse, checked on 2026-10-03 against the
official documentation: Slurm 26.05 (slurm.schedmd.com: sbatch, sacct, squeue, scancel, job arrays) and HTCondor
Manual 25.13.2 (htcondor.readthedocs.io: condor_submit, Job Description Language, job event log codes, job ClassAd
attributes, condor_q, condor_history, managing a job). No real Slurm or HTCondor was run; the fake schedulers follow
these formats. "Documented" means the page states it; "not stated" means the page does not say it either way, so
confirm it on a real run of the version you use before relying on it.

| Fact used | Where | Status (2026-10-03) |
|---|---|---|
| `sbatch --parsable` prints `jobid[;cluster]` | Slurm submit | documented (job ID and cluster name, separated by a semicolon) |
| `--array=A-B%M` (throttle `%M`), `--no-requeue`, `--output`/`--error` with `%A` and `%a`, `--partition`, `--account`, `--qos`, `--constraint`, `--gres`, `--time`, `--cpus-per-task`, `--mem=<n>M`, `--gpus`, `--tmp`, `--job-name`; `SLURM_ARRAY_TASK_ID` in the job | Slurm template | documented (`--mem` default unit MiB, suffix K/M/G/T) |
| `sacct --duplicates --parsable2 --noheader --format=JobID,State,ExitCode,Elapsed,MaxRSS,NodeList`; array tasks `<job>_<task>`; `.batch` step; `ExitCode` as `exit:signal`; Elapsed `[DD-[HH:]]MM:SS`; MaxRSS with an optional unit letter; State followed by `+` when truncated (for example who cancelled) | Slurm poll | documented; the parser accepts both `MM:SS` and `D-HH:MM:SS` |
| Pending array ranges shown as `<job>_[a-b%m]` in sacct | Slurm poll | not stated (squeue documents a combined line "using a regular expression"); parsed if present |
| State codes: the adapter maps PENDING, CONFIGURING, REQUEUED, REQUEUE_FED, RUNNING, COMPLETING, STAGE_OUT, RESIZING, SIGNALING, COMPLETED, FAILED, TIMEOUT, OUT_OF_MEMORY, CANCELLED, NODE_FAIL, BOOT_FAIL, PREEMPTED, REQUEUE_HOLD, SPECIAL_EXIT, RESV_DEL_HOLD, DEADLINE, REVOKED; SUSPENDED and STOPPED map to `unknown` (a person decides) | Slurm state map | documented (squeue 26.05 table); RESV_DEL_HOLD, SIGNALING, DEADLINE, REVOKED, SUSPENDED and STOPPED were added after this check |
| `squeue --jobs=<ids> --array --noheader --format=%i\|%T` | Slurm fallback | documented (`%i` is `<base_job_id>_<index>` for arrays, `%T` the long state) |
| `scancel <job>_<task>`; `scancel --version` | Slurm cancel | documented |
| `sbatch --version` | Slurm provenance | not stated on the sbatch page (scancel documents `-V, --version`) |
| Submit description: `universe` (vanilla, container), `executable`, `transfer_executable`, `arguments`, `log`, `output`, `error`, `should_transfer_files`, `when_to_transfer_output = ON_EXIT`, `transfer_input_files`, `transfer_output_remaps = "a = b; c = d"`, `request_cpus`, `request_memory`/`request_disk` with an `MB` suffix, `request_gpus`, `max_materialize`, `queue a, b from file` (each line split on commas and/or spaces); macros `$(name)` | HTCondor template | documented (`request_disk` default unit is KiB, so the explicit `MB` suffix matters) |
| `container_image` | HTCondor template | not stated in the page excerpt read (the container universe is documented) |
| No automatic retry by default (`max_retries` unset, `on_exit_remove` default True, `periodic_release` default False) | HTCondor template | documented; an evicted job still restarts, which `NumJobStarts` counts |
| `condor_submit -terse` prints `<cluster>.<first> - <cluster>.<last>` | HTCondor submit | partly: "display JobId ranges only"; the exact layout is not stated |
| Job event log: three-digit code, `(cluster.proc.subproc)`, date and time, text; codes 000 submit, 001 execute, 002 executable error, 004 evicted, 005 terminated, 007 shadow exception, 009 aborted, 010 suspended, 011 unsuspended, 012 held, 013 released | HTCondor poll | documented |
| Event separator `...`; termination lines `(1) Normal termination (return value N)` / `(0) Abnormal termination (signal N)`; `Memory (MB)` usage line; held event `Code N Subcode M` | HTCondor poll | not stated verbatim (the pages say the log records termination type, return value or signal, resource usage and hold codes) |
| `condor_q` / `condor_history <cluster> -json -attributes ...`; JobStatus 1 idle, 2 running, 3 removing, 4 completed, 5 held, 6 transferring output (marked "not used"), 7 suspended (mapped to `unknown`); ExitCode, ExitBySignal, ExitSignal, HoldReason, HoldReasonCode, HoldReasonSubCode, NumJobStarts | HTCondor fallback | documented |
| `condor_rm <cluster>.<proc>`; `condor_version` | HTCondor cancel; provenance | documented (condor_rm page 25.14.1) |
