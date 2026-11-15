# K12 performance targets: draft for the user (U10)

**State: DRAFT. Not frozen. No speed or cost claim follows from it.** K12's targets are the user's (plan 0.5.2, `decisions.md` K12). Until the
user's word, K12's default stands: no speed or cost claim. This draft is Gate D's item "K12 targets drafted from recorded costs (U10)"
(`finish-plan.md`) and `t04-values-v4.md` section 12 ("targets are drafted from those records after P2").

**Rule used.** Every number below is read from a record: `sacct`, or a job's own report. Nothing is estimated, extrapolated or rounded up
for a margin. A per-event figure is a division of two recorded numbers and is labelled "derived". Where no record exists, the row says so
and proposes no number. No margin or tolerance is proposed anywhere: the run-to-run spread of the same work at the same hash is not recorded
(see "No record"), so a margin would be a guess. The user sets it, or chooses "not above the recorded value".

## Sources

| Source | What it gives |
| --- | --- |
| `sacct`, queried 2026-11-13T07:27Z, saved in `<private>/jobs/gate-d/sacct/` (`*.allocations.psv` one line per allocation; `*.steps.psv` with steps; `SUITE.steps.psv`) | Elapsed, `CPUTimeRAW` (billed = allocated CPUs x elapsed), `TotalCPU` (used), `MaxRSS` per step, `ReqMem`, node, state |
| `<private>/evidence/freeze-b-run/collect-7585958/costs.log` and `freeze-b-summary.txt` | Wall seconds and MaxRSS per command of the Freeze-B run; events per workflow (PASS BLOCKS lines) |
| `<private>/evidence/evaluation-b11/T0{7,8,9}/collection/current/` | Events per workflow in evaluation attempt 1 (T07 24 bin records; T08 and T09 `collection.json` counts) |
| `decisions.md` (Freeze-B run results; E6a; the evaluation's resources) and `t07-closeout.md`, `t08-closeout.md`, `t09-closeout.md` | Process-level memory readings; the user's approved ceiling; "cost lines are printed, warm only" |

Reading notes, from the records:
- `sacct` `MaxRSS` here is the cgroup's memory including page cache (`jobacct_gather/cgroup`; `decisions.md`, Freeze-B run, Cost). It is
  an upper bound on process memory: T07's Freeze-B job shows 15.42 GB in `sacct` while its largest process, the refit, was 8.01 GB
  (`costs.log`, `t07 refit`, 8,012,452 kB).
- Billed and used differ most for T07 (multi-CPU tasks with serial phases). Both are given.
- Environment of every job below: partition `edr2-al9_short_serial`, account `ams`, nodes `hpa-wn33` (two Freeze-B tasks on `hpa-wn34`),
  the AMD EPYC 9645 class (U-W7, as recorded in `decisions.md`); CPU only; interpreter `<workdir>/env/py313` 3.13.18; ACTS 48.2.0 from
  `<workdir>/env/acts48`. No GPU job exists (A13 recorded `blocked-by-resource` by the user, 2026-11-13).

## Recorded costs

### Evaluation attempt 1 on block 11 (frozen hashes, Freeze B)

Allocations 7613385-7613413 and 7613443-7613459 (46 submissions, arrays expanded: 526 tasks), plus the user-ruled T08 checks rerun 7620410
and its summary 7620411: 528 allocations; 526 COMPLETED, 2 FAILED (7613402 T08 checks, harness result-line defect, exit 3; 7613455 T08
summary on the frozen code, exit 3; both recorded in `decisions.md`). First start 2026-11-13T02:45:17, last end 03:56:44 (71.5 min,
queue included).

| Part | Tasks | Events | Billed CPU-h | Used CPU-h | Derived used per event | Longest task | Largest step MaxRSS (sacct) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T07 (build, bins, refit ranges, slices, checks, negative cases) | 73 | 288,000 | 4.21 | 2.03 | 25.4 ms | 14.9 min (7613400) | 15.42 GB (7613386_20; request 2 x 7,900 MB) |
| T08 (samples, checks, rerun, its summary) | 18 | 180,000 | 0.73 | 0.31 | 6.2 ms | 3.8 min (7620410) | 1.74 GB (7613401_10) |
| T09 (generation, ranges, fixed points) | 376 | 180,000 | 177.60 | 171.29 | 3.43 s | 38.5 min (7613409_4) | 1.11 GB (7613403_7) |
| Scoring, collection, summaries (all workflows) | 61 | - | 1.85 | 0.89 | - | 8.0 min (7613449) | 11.31 GB (7613450_8; request 12,000 MB) |
| **Total** | **528** | | **184.39** | **174.52** | | | |

The user's approved ceiling for this attempt was 200 CPU-hours; the last estimate before submission was 176.4 CPU-hours (`decisions.md`,
"ceiling"). Recorded: 184.39 billed, 8.0 CPU-hours above that estimate and 15.6 below the ceiling.

### Freeze-B run on block 2

Jobs 7585954 (T07), 7585955 (T08), 7585956 (T09 multistart, array 0-14), 7585957 (T09 topology, array 0-12), 7585958 (collection), and the
read-only rate-check supplement 7590984. All 32 COMPLETED. First start 2026-11-12T02:58:51, last end 06:32:29 (collection; the supplement
ran later).

| Part | Tasks | Events | Billed CPU-h | Used CPU-h | Derived used per event | Longest task | Largest step MaxRSS (sacct) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T07 | 1 | 180,000 | 1.61 | 0.74 | 14.8 ms | 48.4 min | 15.42 GB (process max 8.01 GB, refit) |
| T08 | 1 | 45,000 | 0.09 | 0.08 | 6.4 ms | 5.5 min | 2.48 GB |
| T09 multistart | 15 | 45,000 (both parts) | 11.29 | 11.15 | 3.01 s (both parts) | 72.5 min (7585956_12) | 1.04 GB |
| T09 topology | 13 | | 26.63 | 26.42 | | 138.7 min (7585957_2) | 1.10 GB |
| Collection, supplement | 2 | - | 0.04 | 0.02 | - | 2.4 min | 1.33 GB |
| **Total** | **32** | | **39.67** | **38.40** | | | |

Per command (`costs.log`, wall seconds, warm): T07 build 336.6; noise draw and finding 1,397.5; clean 110.4; comparator 532.3; refit 315.3
(8.01 GB); noise-file deletion 74.6. T09 multistart fit per sample 1,767.3 to 2,637.4; topology fit per sample 6,323.2 to 8,129.1; the
two-source sample 1,867.0 (multistart) and 2,977.0 (topology). T08 reconstruction per sample 1.2 to 8.7.

### Development jobs (T07, T08, T09)

From `sacct`; each job is a different stage, so these are costs of development, not of one workload.

| Workflow | Jobs | Billed CPU-h | Used CPU-h | Longest | Largest step MaxRSS |
| --- | --- | --- | --- | --- | --- |
| T07 stages 1-11, record, E2 | 7489042, 7489159, 7489656, 7490165, 7490742, 7491894, 7492037, 7492427, 7493368, 7493849, 7494285, 7494405, 7496491, 7502411, 7503215, 7512409, 7515600, 7522969, 7524096, 7536797, 7537235, 7546791, 7548207, 7551619, 7584388 (25; 12 ended FAILED in Slurm, each a recorded stage outcome) | 21.08 | 8.43 | 20.3 min (7537235) | 10.56 GB (7503215) |
| T08 stages 1-4 | 7552825, 7554028, 7555555, 7557508, 7557888, 7557963 (6; 1 FAILED in Slurm, 7557888) | 1.05 | 0.71 | 14.6 min (7557508) | 3.32 GB (7557508) |
| T09 stages 1-5, E1 | 7565328, 7566770, 7571207, 7575617, 7578442, 7584387 (6) | 4.07 | 3.73 | 83.9 min (7575617) | 1.59 GB (7575617) |

Warm per-stage cost lines printed by the jobs (examples, from the logs): T07 stage 11 (7551619) `REFIT-COST` 25.9 to 26.8 s per 3,000
events (18,000 tracks), `FINDING-COST` clean 2.3 to 18.3 s per 3,000 events by stratum; T08 stage 4 (7557963) clustering 1.22 ms per event
over 100 events; T09 (7575617, 7578442) one fit 39 to 69 ms at `N_exp` 40 to 1,500.

### T07 vertex diagnosis and candidates (development data, block 1)

| Job | What | Elapsed | Billed CPU-h | Used CPU-h | Largest step MaxRSS | Request |
| --- | --- | --- | --- | --- | --- | --- |
| 7623497 | diagnosis | 12.6 min | 0.84 | 0.14 | 5.11 GB | 4 x 16,000 MB |
| 7623624 | C1 | 28.5 min | 1.90 | 0.50 | 4.29 GB | same |
| 7624555 | C2 | 28.3 min | 1.89 | 0.50 | 4.54 GB | same |
| 7625490 | C3 | 28.3 min | 1.88 | 0.51 | 5.11 GB | same |

### Checks (for the gate jobs themselves)

Full unit suite and static gate from a snapshot, 6 CPUs: 7592961 21.8 min, 7596005 20.5 min, 7596486 18.6 min, 7597152 14.4 min,
7606257 26.2 min (batch MaxRSS 1.58 to 1.89 GB; `SUITE.steps.psv`). Inside 7606257: `run_all_checks.py --part units --jobs 6` 567 s,
`--part static --jobs 6` 169 s (`evidence/t12-stage1-7606257/steps.tsv`); inside 7596005: 454 s and 167 s. Jobs that also ran the E6
units: 7598757 21.5 min, 7601521 24.9 min, 7623515 26.0 min, 7624491 24.7 min (batch MaxRSS 5.38 to 6.66 GB).

## Draft targets for U10

Each target is stated as a form plus the recorded reference it rests on. "Not above the reference" is the only threshold proposed; a margin
is the user's. Plan 14.2 applies to all: a cost target is judged only on a run that does the same scientific work at the same frozen hashes
and passes its quality gates; a run that changes physics results is not a cost comparison.

| ID | Scope and workload unit | Measurement boundary | Recorded reference (jobs) | Draft target | Notes |
| --- | --- | --- | --- | --- | --- |
| K12-D1 | One evaluation attempt of T07, T08 and T09 at the Freeze-B hashes, as E6 lays it out; unit: the attempt | Billed CPU-hours (`CPUTimeRAW`) over every allocation, failures and reruns included | 184.39 billed, 174.52 used, 528 allocations (7613385-7613413, 7613443-7613459, 7620410, 7620411) | Billed not above 200 CPU-hours (the ceiling the user already approved, `decisions.md`) | The only target here with a number the user has already given. Attempt 2 for T07 would be a different layout (a return to Freeze B) |
| K12-D2 | T09 full chain at its frozen recipe; unit: generated event | Used CPU over every T09 task (generation, fits, checks, readings) / generated events | 3.43 s per event (evaluation, block 11, 376 tasks); 3.01 s per event (Freeze-B run, block 2, 28 tasks: 7585956, 7585957) | Not above the reference of the same layout: 3.43 s per event for the evaluation layout, 3.01 s for the Freeze-B layout | The two layouts differ (the evaluation fits each stratum in ranges; the task mix is not the same), so they are two references, not one. The difference is not attributed |
| K12-D3 | T09 task length; unit: task | Elapsed per task | 38.5 min (7613409_4) evaluation; 138.7 min (7585957_2) Freeze-B topology | Every task under the partition's 4 h limit, as approved for both runs; reference values as recorded | The 4 h limit is the user's (U-B9, evaluation resources) |
| K12-D4 | T07 tracking and vertexing chain at its frozen recipe; unit: generated event | Used CPU over every T07 task / generated events | 25.4 ms per event (evaluation, 73 tasks), 14.8 ms (Freeze-B, 7585954) | **Cost reading only, no target**: T07 failed its quality gates at attempt 1 (`decisions.md`), and plan 14.2 pairs cost with required quality | If T07 is reopened (the user's parked fix), its targets come from its new runs |
| K12-D5 | T07 refit memory; unit: process | Largest process (job's own `costs.log`), not `sacct` | 8.01 GB at 3,000 events (7585954); 31.8 GB for 12,000 events at once (E6a, 7591439, `decisions.md`) | Same reading-only status as K12-D4 | Kept because it set the evaluation's 4,000-event refit ranges |
| K12-D6 | T08 cell-to-cluster chain at its frozen recipe; unit: generated event | Used CPU over every T08 task / generated events | 6.2 ms per event (evaluation, 18 tasks, rerun included); 6.4 ms (Freeze-B, 7585955) | Not above 6.4 ms per event, the larger of the two | Both runs are dominated by checks and readings, not reconstruction (per-command lines in `costs.log`: reconstruction 1.2 to 8.7 s per 3,000-event sample) |
| K12-D7 | The gate job (full unit suite plus static gate from a snapshot, 6 CPUs); unit: job | Elapsed, batch MaxRSS | 14.4 to 26.2 min, 1.58 to 1.89 GB (7592961, 7596005, 7596486, 7597152, 7606257) | Not above 26.2 min and 1.89 GB for the same steps | The coordinator's job predictions already use 15 to 35 min, refuted above 60 min (`jobs/t12-stage1/t12-stage1.sh`): those are refutation bounds for a job, not a K12 target |
| K12-D8 | A T07 vertex candidate trial on the diagnosis events (K17 trial budget); unit: trial | Billed CPU-hours per job | 1.88 to 1.90 per candidate, 28.3 to 28.5 min (7623624, 7624555, 7625490) | For K17: a trial's budget request no larger than these, if the same layout is reused | Only if the user reopens T07 |

## No record: no number proposed

- **Cold start.** Every cost line printed is warm only (`t07-closeout.md`, `t08-closeout.md`, `t09-closeout.md`, K12 lines). No cold run
  of any recipe is recorded. Plan 14.2 and K12 ask for cold and warm apart; this stays open.
- **I/O apart from compute.** No job separates read, write, conversion and native compute times. Per-command walls in `costs.log` mix them.
- **Run-to-run spread at the same hash.** No job repeated the same work at the same hash for timing; the closest is the T08 checks task
  (7613402 crashed after 2.1 min; 7620410 3.8 min, different code). The C1 to C3 jobs share events but not configuration. So no margin.
- **Latency quantiles, throughput under fixed memory.** Not recorded per event, only per task or per command.
- **GPU.** No job; A13 is `blocked-by-resource` (the user, 2026-11-13).
- **AI startup, routing and first-valid-execution costs (plan 14.2 "AI comparisons").** T13 has not run; no record.
- **Selection objective cost (K16, T15b).** No `simreco` job has run on this branch (`t15b-assessment.md`).
- **T10 and T12.** Their jobs exist (T10 7593003, 7594892; T12 7606257) but those tasks are in progress; their targets are drafted when
  they close, from their own records.

## For the user (U10)

Options, each from the table above:
1. Accept K12-D1 to D3 and D6 to D8 as written ("not above the recorded reference"), with K12-D4 and D5 as readings. A rerun of a workflow
   at its frozen hash on the same CPU class is then judged against them.
2. As 1, with a margin the user names per target.
3. Keep K12's default for now (no speed or cost claim), and draft again at Phase G with cold runs and a repeat at the same hash.

The coordinator's recommendation is not made in this draft; it goes with the question at Gate D.
