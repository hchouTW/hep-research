# Batch site note: NSTCCore (TWGrid) Slurm

## When to read this file

Read it before submitting to the NSTCCore Slurm cluster run by ASGC/TWGrid (Taipei), with
[batch-scheduling.md](batch-scheduling.md) (the adapter), the site guide and the Slurm pages for the site's version.
Everything here is either a statement of a cited page or an observation on the cluster on 2026-10-10 (Slurm 24.05.1,
cluster `slurm-ctrl01`, login node `slurm-ui-asiop.twgrid.org`, AlmaLinux 9); nothing is from memory, and an
observation holds for that version and day: partitions, priority tiers and node software change. Status:
**documented, observed on 24.05.1**. Pages: guide = `https://nstccore.twgrid.org/documents/slurm/` (read 2026-10-10),
storage = `https://nstccore.twgrid.org/documents/storage/` (read 2026-10-10); SchedMD pages from the 24.05.1 archive
`https://slurm.schedmd.com/archive/slurm-24.05.1/` (the current `slurm.schedmd.com` index is for 26.05): sbatch,
salloc, srun, sacct, sprio, sshare, job_array, job_exit_code, job_reason_codes, slurm.conf, cgroup.conf,
priority_multifactor. Site support: the contact block at the end of the guide.

## Site facts

| Topic | Fact | Page | Observed 2026-10-10 |
|---|---|---|---|
| Login, rules | log in with 2FA to `slurm-ui.twgrid.org` (round robin) or an institute node such as `slurm-ui-asiop`; compute nodes cannot be logged into; login nodes are for submitting, editing, monitoring and transfer only, and administrators may kill heavy processes without notice | guide | — |
| Spaces | home `/dicos_ui_home/<user>` (100 GB, temporary, no integrity guarantee; over quota blocks login); group space `/ceph/work/<group>` (Ceph) is the working area; avoid very many files in one directory | guide, storage | home and group space are both mounted on the compute nodes; `/ceph/work` is a symbolic link into `/ceph/sharedfs/work`, so tools that resolve paths print the latter |
| Partitions | `edr1-al9_*`, `edr2-al9_*`, `intel-g4-al9_*` each as `short`, `short_serial`, `moderate_serial`, `long_serial`, `large`; `global`, `bigmemory_hdr1`; GPU `a100_devel-al9` (20 min), `a100_short-al9`, `a100-al9`, `a100_long-al9`, `v100-al9_short`, `v100-al9`, `v100-al9_long`, `b6000-al9*` | — (`sinfo -s`) | default `edr1-al9_short` (3 h, PriorityTier 1); the `*_serial` partitions share its nodes (192 CPUs, 1.386 TB each) with PriorityTier 500 and QoS `cpu_single_short` (MaxTRES cpu=24, 4 h) |
| Which partition | — | not stated | the default `edr1-al9_short` (PriorityTier 1) shares its nodes with the `*_serial` partitions (PriorityTier 500), and backfill gives free cores to the higher tier, so the default partition can starve while a `*_serial` partition starts jobs in seconds; `sbatch --test-only` does not see this and predicts an immediate start either way; compare the pending reasons per partition first (batch-scheduling.md, "Checking what a Slurm cluster can give you") |
| QoS | the association allows QoS `normal`; GPU partitions carry their own QoS (`a100_devel`: exactly 1 GPU; `gpu_v100_short`: 1–8; `b6000_res`: 1–2) | — | a 1-GPU job without `--qos` was accepted and the partition QoS imposed its limits, but the job's own QoS stayed `normal` (`SLURM_JOB_QOS`, `sacct` `QOS`); `--qos=gpu_a100_devel` is refused ("Invalid qos specification") |
| Memory | `--mem-per-cpu` defaults to `DefMemPerCPU`; above `MaxMemPerCPU` the CPU count is raised (slurm.conf) | sbatch, slurm.conf | `DefMemPerCPU 6000` MB; `MaxMemPerCPU` 7165 (edr1, edr2, global), 15933 (a100), 15828 (v100); `--mem-per-cpu=8000` with 1 CPU ran as 2 CPUs × 4000 MB and was **billed as 2 CPUs** (`AllocTRES billing=2`); `EnforcePartLimits=ALL` refuses over-limit time and node counts at submission, not memory |
| Memory enforcement | RAM is constrained by the job cgroup; `AllowedSwapSpace` does not stop the kernel from using swap | cgroup.conf | `memory.max` = `memory.high` = the request on the job cgroup, `memory.swap.max = max`: a job above `--mem` is **not** killed and not `OUT_OF_MEMORY`; it pages to the node's shared 4 GB swap and runs many times slower (2 GiB under `--mem=500M`: RSS pinned at 495 MB, 10× CPU time, `COMPLETED`). Symptom: `MaxRSS ≈ ReqMem` and `CPUTimeRAW` far above expectation. The limit sits two cgroup levels above the task; walk up from `/proc/self/cgroup` to read it |
| GPU nodes | `--gres=gpu:N` | guide | A100 nodes 64 CPUs and 8 GPUs, V100 nodes 48 CPUs and 8 GPUs, two threads per core: a 1-CPU, 1-GPU request became 2 CPUs (one core), 12,000 MB and billing 2; `CUDA_VISIBLE_DEVICES` is set per step. `hp-rtx6kp02` (`b6000-al9_devel`): 8 GPUs, NVIDIA RTX PRO 6000 Blackwell Server Edition (97,887 MiB, compute capability 12.0, 188 SMs), driver 590.48.01, 64 CPUs, 1.5 TB (`hp-rtx6kp01`, in the other `b6000-al9*` partitions, also has 8 GPUs; its model was not checked); same 1-CPU → 2-CPU rounding; the `cuda` 13.1 module compiles for it with `nvcc -arch=native` (sm_120) and a test kernel ran correctly |
| Partition access | `AllowAccounts`, `AllowQos` and the partition `QoS` | — (`scontrol show partition`, `sacctmgr show qos`) | `b6000-al9_devel` has no account restriction; its QoS `b6000_res` requires 1–2 GPUs per job (`MinTRESPerJob`/`MaxTRESPerJob gres/gpu`, `DenyOnLimit`), `MaxTime` 5 days. `nthu_course_2026` and `reservation_b6000_2` are limited to other accounts (`AllowAccounts`; `--test-only` answers "Invalid account or account/partition combination specified"), so an idle node there is not available to you |
| Time limit | at the limit tasks get SIGTERM, then SIGKILL `KillWait` later; resolution one minute | sbatch | `OverTimeLimit 0`, `KillWait 30 s`; a 1-minute job was signalled 76 s after its start; a script that traps SIGTERM and exits leaves the job `TIMEOUT` and its `.batch` step `COMPLETED 0:0` |
| Requeue | `--no-requeue` | sbatch | `JobRequeue 0` on the cluster, so nothing is requeued by default anyway |
| Environment | `--export=NONE` passes only `SLURM_*` and then "implicitly attempt[s] to load the user's environment"; with it, `SLURM_EXPORT_ENV` should be set to ALL in the script before `srun` | sbatch | `--export=NONE` rebuilds the **login environment, dotfiles included** (conda base, user PATH entries, the node's Modules 5.3.0); `srun` under it fails with `execve(): bash: No such file or directory` unless the script exports `SLURM_EXPORT_ENV=ALL` first; `module` works in either mode but not in a pipeline; `--export=NIL` gives a bare start: `PATH=/usr/local/bin:/usr/bin`, `HOME` empty, no `USER`, no `module` command |
| Software on the nodes | modules `gcc` 13.1.0, `cuda` 13.1.0, `anaconda3` 2024.10-1, `root` v6.40.02, `singularity` 4.1.2, `mpi` openmpi-5.0.3 (`module avail`); the guide tells you to compile on the target architecture | guide | the `root` module loads but `root.exe` fails on CPU compute nodes: `libxxhash.so.0` is missing there (present on the login node); a copy of the library in group space on `LD_LIBRARY_PATH` works around it; the module does not set `PYTHONPATH`: PyROOT (built for Python 3.12) imports under the `anaconda3` Python 3.12.7 only with `PYTHONPATH=$ROOTSYS/lib` plus that workaround; `stress` (used in the guide's array example) is absent on the nodes (exit 127) |
| Arrays | `--array=A-B%N`; `SLURM_ARRAY_JOB_ID`, `SLURM_ARRAY_TASK_ID`, `_COUNT`, `_MIN`, `_MAX`; `%A_%a` in file names | job_array, guide | `MaxArraySize 20000`; the `%N` throttle held (never more than N running); each task has its own `SLURM_JOB_ID` and the master ID is not the lowest task's |
| Dependencies | `afterok`, `afternotok`, `afterany`, `aftercorr`; a never-satisfiable dependency leaves the job pending unless `kill_invalid_depend` | sbatch, guide | `DependencyParameters` unset: of an `afterok`/`afternotok` pair one job always stays `PENDING (DependencyNeverSatisfied)` until cancelled |
| Exit codes | a batch job's exit code is the script's; `DerivedExitCode` starts as the highest step exit code | job_exit_code | `exit 3` → `FAILED 3:0`; `DerivedExitCode` counts only `srun` steps, not the `.batch` step: a script that runs a failing `srun` step and exits 0 is `COMPLETED 0:0` with `DerivedExitCode 4:0`; check step rows, not only the job state |
| Accounting | `sacct` fields as documented; `MaxRSS` comes from periodic sampling | sacct | records appear within seconds of the end; `JobAcctGatherFrequency 15`: tasks of 3 s reported `MaxRSS` 44–80 K, a 5 s task 18 MB, so `MaxRSS` of a job shorter than about 15 s is not its peak |
| Priority | multifactor; `sprio -w`, `sshare -l` | priority_multifactor, sshare | weights FairShare 100000, Age 1000, QOS 10, Partition 1, JobSize 0; half-life and max age 7 days; Fair Tree (`LevelFS` printed): the factor is a rank among users, so any usage moves a new user down from 1.0 and fair-share rank is almost the whole priority; `sprio` refuses a job still waiting on `--begin` |
| `--parsable` | prints `jobid[;cluster]` | sbatch | the job ID alone on this single cluster |
| Containers | `--container` runs a step in an OCI bundle when the nodes have `oci.conf` | sbatch, srun | no `oci.conf`, no `scrun` on the nodes, and `srun --container=<missing path> true` **succeeds**: the option is silently ignored and the command runs on the host; `singularity` 4.1.2 (module) works as an ordinary command in a job |

## Running the batch adapter here

- `slurm.partition`: a `*_serial` partition (for example `edr1-al9_short_serial`) for one-CPU chunks, not the default
  partition; `slurm.account`: the account `sacctmgr show assoc user=$USER` lists; no `slurm.qos`.
- `worker_python`: an absolute interpreter the nodes have, for example the `anaconda3` module's `bin/python3`
  (3.12.7). The template's `--export=NONE` and `exec` of that interpreter in the batch step (no `srun`) ran without
  any environment problem; a worker that needs ROOT must apply the `libxxhash` workaround itself.
- `campaign_dir` in group space; the adapter records it under `/ceph/sharedfs/work/...` (the link target).
- GPU chunks: `resources.gpus` (`--gpus=N`) works on `v100-al9_short` like `--gres=gpu:N`; give `worker_python` the
  torch build for that GPU type (CUDA 12.6 build for V100: its driver supports CUDA 12.9 at most; CUDA 13.0 build for
  the Blackwell node). Each requested CPU is allocated and billed as 2 there; set `limits.alloc_cpu_factor: 2` for GPU
  partitions (1 or unset on CPU partitions) so `max_core_hours` holds from the first submission; once a job is polled
  the allocated CPUs (`AllocCPUS`) count. `limits.max_gpu_hours` counts the allocated GPUs (`gres/gpu` in
  `AllocTRES`, 1 for a 1-GPU request) times the elapsed time, or the walltime limit until the job ends.
- `resources.memory_mb`: size from a pilot that runs well past 15 s, or measure the peak inside the worker; an
  undersized value does not fail, it swaps. On GPU partitions ask for CPUs in pairs.
- A chunk worker should return only additive quantities: `merge` sums every key of a chunk result, so bookkeeping
  fields (seed, item range) in the result come out as meaningless sums.
- First real campaign: one synthetic 10-chunk toy campaign on 2026-10-10 (pilot, then nine chunks as one array with
  throttle 4), all `COMPLETED`, merged equal to recomputing every chunk from the manifest seeds; the report validates
  with status `synthetic, unvalidated`. `RealSlurmTests` (two chunks, `HEP_SLURM_TEST=1`, `HEP_SLURM_CONFIG` naming a
  user-reviewed configuration) passed in 31 s; Slurm is `demonstrated-on-synthetic-data` with `tested_versions
  ["24.05.1"]`.
