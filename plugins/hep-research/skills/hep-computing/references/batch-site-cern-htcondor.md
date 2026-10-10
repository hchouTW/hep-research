# Batch site note: CERN HTCondor (local pool) from lxplus

## When to read this file

Read it before submitting to the CERN local HTCondor pool, with [batch-scheduling.md](batch-scheduling.md) (the
adapter) and the CERN Batch Docs themselves. Everything here is either a statement of a batchdocs page (cited with
the page's own "last update" date) or an observation on the pool on 2026-10-10 (HTCondor 24.12.16 client and
schedd, lxplus, AlmaLinux 9); nothing is from memory, and an observation holds for that version and day. Status:
**documented, observed on 24.12.16**. Base URL `https://batchdocs.web.cern.ch/`; page keys: submit =
`local/submit.html` (2025-11-11), quick = `local/quick.html` (2019-11-26), spool = `local/spool.html` (2025-02-11),
xfer = `local/file_xfer_plugin.html` (2025-11-17), myschedd = `local/myschedd.html` (2020-09-07), eossubmit =
`local/eossubmit.html` (2026-08-05), kerberos = `concepts/kerberos.html` (2024-07-26), limits =
`concepts/service-limits.html` (2025-01-21), afs = `troubleshooting/afs.html` (2026-05-11), eos =
`troubleshooting/eos.html` (2026-02-02), pitfalls = `troubleshooting/pitfalls.html` (2026-05-11), common =
`troubleshooting/commonexceptions.html` (2026-05-11), idle = `troubleshooting/idle-job.html` (2026-04-27), retry =
`workarounds/job-retry.html` (2025-08-11), ex6b = `tutorial/exercise6b.html` (2025-01-13), ex2b =
`tutorial/exercise2b.html` (2022-05-02).

## Site facts

| Topic | Fact | Page | Observed 2026-10-10 |
|---|---|---|---|
| Submit host, credentials | lxplus; a Kerberos ticket is needed (`kinit`); the submit host registers a credential (`batch_krb5_credential`), the schedd keeps it and `condor_credmon` renews it; the job gets Kerberos, AFS (`aklog`) and EOS FUSE tokens; check inside the job with `klist -f` or `tokens` | quick, kerberos | with `getenv = false` the job had `krbtgt` and `afs/cern.ch` tickets and an rxkad token and wrote to AFS |
| First submissions of a session | — | not stated | the first four `condor_submit` calls failed after ~20 s: `Failed to process job credential requests (1): 'ERROR: store_cred of Kerberos credential failed - The credmon did not process credentials within the timeout period'; BAILING OUT.`; no cluster was created; every later call succeeded |
| Schedd | each user is mapped to one schedd; `myschedd show`, `myschedd bump` (least loaded), `myschedd set <bigbirdNN>`; `condor_q -name <schedd>` for another | submit, myschedd | `_condor_SCHEDD_HOST` exported in a login shell overrides the mapping (`myschedd show` said bigbird25, `condor_q` used bigbird13) |
| Minimal submit file | `executable`, `arguments = $(ClusterId) $(ProcId)`, `output`, `error`, `log`, `queue`; "HTCondor won't create the directory for you though, and will error if it doesn't exist" | quick | a missing `output` directory is **accepted at submission**; after the run the job is held: `012 Job was held. / Transfer output files failure at access point ... (errno 2) No such file or directory / Code 12 Subcode 2`, with `ExitCode 0` |
| `condor_submit` output | "Submitting job(s). / 1 job(s) submitted to cluster 70." | quick | `-terse` prints one line `15004467.0 - 15004467.9` |
| stdout, stderr, log | stdout/stderr are written on the worker and copied back only at the end; `stream_output`/`stream_error` are not allowed; the `log` is written by the schedd in near real time; `condor_wait -status <log> [<job>]`; a run-time overrun normally loses the partial stdout/stderr | submit, quick | the overrun job's `.out` never arrived; the log on AFS lagged `condor_q` by a few seconds right after completion |
| Shared file system | relative paths are presumed shared between submit node and schedd; "this effectively means AFS" | submit | files a job writes in its sandbox come back to the **submit cwd** (initialdir), not next to `output` |
| OS, architecture | AlmaLinux 9 by default and "only one answer"; `requirements = (OpSysAndVer =?= "...")` matches the base OS; `MY.WantOS = "el7"\|"el8"\|"el9"` runs in an Apptainer container when the base OS differs; the architecture follows the submit node, `requirements = (Arch =?= "aarch64")` for ARM | submit | 4,672 slots `AlmaLinux9`, 4,644 x86_64 + 28 aarch64; `OpSysAndVer AlmaLinux9` also matches hosts whose `/etc/os-release` says RHEL 9.8; `WantOS el9` ran natively; `OpSysAndVer =?= "CentOS7"` is **refused at submission** ("CentOS 7 has been decommissioned"); an unknown value is accepted and idles forever (`condor_q -better`: 0 slots match) |
| Run time | wall time; `+JobFlavour`: espresso 20 min, microcentury 1 h, longlunch 2 h, workday 8 h, tomorrow 1 d, testmatch 3 d, nextweek 1 wk; `+MaxRuntime = <s>`; the default is espresso; over the limit the job is terminated | submit, ex6b | no flavour → `JobFlavour` undefined, `MaxRuntime 1200`; `+MaxRuntime = 60` with a 180 s sleep → `009 Job was aborted. / Job removed by SYSTEM_PERIODIC_REMOVE due to wall time exceeded allowed max.`, history `JobStatus 3`, `ExitCode 0` |
| Resources | 1 core, 3 GB, 20 GB disk; 3 GB per core: `request_cpus = 2` gives 6000 MB; memory is a soft limit; 4+ core jobs schedule faster than 2–3 | submit, ex6b | `request_cpus 2` → `RequestMemory 6000`, `nproc 2`, `OMP_NUM_THREADS 2`; `RequestDisk` is `DiskUsage` in KB in the ClassAd |
| Many jobs, throttle | `queue N`; `max_materialize = M`; `next_job_start_delay` is rejected | submit, common | `queue 10` → ProcIds 0–9 once each, one `log` with `$(ClusterId)` holds all events |
| Environment | "Do not use getenv=True" | pitfalls | — |
| AFS | 16,000–25,000 entries per directory ("(errno 27) File too large"); separate `log/ output/ error/` folders; one `log` per submission named with `$(ClusterId)` only; a new folder per submission; avoid AFS for many jobs | afs, pitfalls | — |
| EOS | paths on the EOS mount are refused in `executable`, `log`, `input`, `output`, `error`, `initialdir`, `transfer_input_files`; inside the job use `xrdcp root://...` or `eos`, not the FUSE mount ("fragile"); EOS outside batch: [storage-cern-eos.md](storage-cern-eos.md) | eos, pitfalls | with `getenv = false` the job had Kerberos and AFS tickets and an AFS token; `xrdcp root://eosuser.cern.ch/...` into the sandbox took 0.15 s for 5 MB and its adler32 matched the EOS checksum; the mount was visible in the job and gave the same checksum |
| xrootd transfer plugin | `output_destination = root://eosuser.cern.ch/<EOS path of a directory>/`, `MY.XRDCP_CREATE_DIR = True`, `transfer_output_files = f1, f2`; `transfer_input_files` with `root://` URLs to files only; `executable` and `initialdir` cannot be `root://`; the user log stays on AFS unless `-spool` | xfer | `MY.XRDCP_CREATE_DIR = True` created the destination folder and the two files arrived with the right checksum; **`output` and `error` went to the destination too** (as `<destination>/logs/job.<cluster>.<proc>.out`, keeping their relative path), not to the submit folder; only the user `log` stayed on AFS |
| Output transfer | `transfer_output_files = ""` → only log, stdout and stderr come back | ex2b, pitfalls | — |
| Spool, EosSubmit | `condor_submit -spool` after `module load lxbatch/spool` (100 jobs per submission, 500 per owner, 1024 MB); EosSubmit schedds (`module load lxbatch/eossubmit`): every path in EOS, one log per cluster | spool, eossubmit | — |
| Service limits | no submission limit; 10,000 running jobs per schedd; held jobs removed after 24 h; jobs restarted more than 10 times removed | limits | — |
| Retry recipe | `on_exit_remove = (ExitBySignal == False) && (ExitCode == 0)`, `max_retries = 3`, `requirements = (Machine =!= split(LastRemoteHost, "@")[1])` | retry | — |
| Exit code, removal, eviction | — | not stated | `exit 3` → `005 Job terminated. / (1) Normal termination (return value 3)`, `ExitCode 3`; `condor_rm` of an idle job → `009 Job was aborted. / via condor_rm (by user ...)`, `NumJobStarts 0`; a job's first match can end in `022`/`024`/`004 Job was evicted. Code 1008 Subcode 0 / Reason: Job not found at execution machine` before any execute event, with a reschedule minutes later and no extra `NumJobStarts` |
| Event log on 24.12 | — | not stated | the log opens with `035 (<cluster>.-01.000) Cluster submitted` and ends with `036 ... Cluster removed` (proc −1); records are separated by `...`; `001` lists `SlotName`, `CondorScratchDir`, `Cpus`, `Disk`, `GPUs`, `Memory`; `040` marks file transfer |
| `condor_history` | — | not stated | a job's history record appears **minutes** after it leaves the queue; a cluster query without a match scans the whole history file (>300 s on bigbird13); with the records present, `-match N` returns in under a second |
| Idle jobs | `condor_q -better <job>` (forward and reverse matching, `-machine slot1@host [-reverse]`); CERN adds `PreAfsRequirements`/`PreCvmfsRequirements` to every job; a matching job starts within about 5 min | idle | the toy jobs started 40–120 s after submission |
| Common errors | wrong shebang or CRLF → job ends in seconds; "Can't find address of local schedd" → expired Kerberos; `SECMAN:2007` → busy schedd; CVMFS misses are transient | common | — |

## Running the batch adapter here

- `campaign_dir` on AFS, never on the EOS mount (the `log`, `output`, `error` and `transfer_input_files` of the
  rendered submit file all point into it); keep a submission below about 8,000 attempts (two log files per attempt
  in one `logs/` folder, AFS entry limit).
- `htcondor.site_attributes`: `{"JobFlavour": "espresso"}` (or `MaxRuntime`), otherwise every job gets 20 minutes;
  `resources.time_limit` the same length so `limits.max_core_hours` can count.
- `htcondor.schedd`: `"caller"` when the shell exports `_condor_SCHEDD_HOST`, or the name `myschedd show` prints;
  choose with `myschedd bump` before the first submission if you want the least-loaded one; the campaign then stays
  on that schedd.
- `worker_python`: an absolute interpreter the workers have (`/usr/bin/python3` is 3.9 on the EL9 workers; the
  plugin's runner stays 3.9-compatible).
- `throttle` is `max_materialize`, the throttle CERN asks for.
- A session's first `condor_submit` can fail on the credential step (above): the adapter records the attempts as
  `not-submitted`; `reset` with a reason and `resubmit` once a later `condor_submit` works.
- Right after a job completes, the AFS copy of the event log can trail the queue and the history record appears
  minutes later: the adapter reads the log once more when the queue says gone, and asks the history only for what
  the log still cannot settle (with `-match N`); a poll in that window may still report `htcondor.timeout`, so poll
  again a few minutes later. `watch` stops once nothing is queued or running, so a pilot can be watched.
- Held jobs vanish from the queue after 24 h and jobs restarted more than 10 times are removed: keep `max_attempts`
  below 10 and act on a held chunk within a day.
- First real campaigns: two synthetic 5-chunk toy campaigns (shared-filesystem and transfer modes) merged equal to
  a local single run on 2026-10-10; `RealHTCondorTests` passes with `HEP_HTCONDOR_TEST=1` and `HEP_HTCONDOR_CONFIG`
  (see VALIDATION.md).
