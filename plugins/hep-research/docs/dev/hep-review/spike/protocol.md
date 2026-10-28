# T0S spike protocol (written before any review ran)

Spec §1.2 step 4, §15.1, §18.2; task file T0S step 1. Exploration only: nothing here supports a capability or
reliability claim (spec §15.1), and every instance below is `exposed: true` and may never be used for G2 (case N25).

## 1. Time box

| Item | Value |
|---|---|
| Written T01 estimate | 8 hours of agent wall-clock: 62 owned cases, schemas, strict ingestion with gold byte vectors, validator, closures, projection, decision-table generator, layering and lint |
| `T0S_fraction_of_T01` | 0.20 (task file §1) |
| Spike time box | 96 minutes of wall-clock from the commit of this file to the commit of `observations.md`, excluding waiting for the background baseline run of T00 |
| Dispatch budget | at most 20 subagent dispatches (16 review instances + at most 4 host probes); no automatic retry (spec §16): a failed dispatch is a recorded outcome, not a reason to rerun |
| If the box runs out | stop, write what is known, decision = no-go per spec §18.2, ask the user (task file §4.2) |

## 2. Instances

Sixteen exploratory instances, four of each type (spec §15.5), small text + JSON statistics material (combination of
measurements, covariance, chi-square, weighted mean) with a collaborating computing obligation (can the stated numbers
be recomputed from the JSON):

| Type | Meaning | Instances |
|---|---|---|
| C01 | a locatable, non-cosmetic known defect | x01a-x01d |
| C02 | a correct same-scope control | x02a-x02d |
| C03 | a required input is missing | x03a-x03d |
| C04 | an intent minimum requirement left unplanned | x04a-x04d |

Each instance has an intent, a plan (obligations), material files and an expected-result file. The expected-result
files are written to the session scratch folder, outside the worktree and outside every reviewer packet, and are
copied into `spike/expected/` only after all reviews have been submitted. On this shared-filesystem host that keeps
them out of the packets, not out of reach: held-out isolation is not claimed (spec §15.4); the instances are exposed
anyway.

## 3. Go / no-go thresholds (spec §18.2 table made concrete)

Scoring is by the coordinator against the expected-result files, per instance:

- **C01 located with relevant evidence**: the reviewer's submission has `violated` (or a finding) on the obligation
  that carries the defect, and the finding names the defective element (the field, number or step) and gives a reason
  that matches the expected defect. "Located but weak evidence" = right obligation and element, reason missing or wrong.
- **C02 false alarm**: any finding claimed as a defect, or any `violated`, on a correct control.
- **C03 gap kept**: the obligation needing the missing input is `undetermined` or `not-examined` with the missing input
  named; `supported` or `violated` on it is a failure to keep the gap.
- **C04**: mechanical. The projection must give `plan_requirements_met = false` with the unplanned requirement listed as
  a planning gap in 4/4. Whether the reviewer also notices the unplanned requirement is recorded, not scored.
- **Submission reliability**: a dispatch counts as submitted when a drop file exists, parses as the requested JSON and
  names its assignment.

| Decision | Condition (all instances counted, failures included) |
|---|---|
| **go** | C01 located with relevant evidence in >= 3 of 4; C02 false alarms <= 1 of 4; C03 gap kept in >= 3 of 4; C04 mechanical 4/4; submissions >= 15 of 16 |
| **go, narrowed** | not go, but C01 located (any evidence quality) in >= 2 of 4, C02 false alarms <= 2 of 4 and submissions >= 13 of 16; T03's pilot then narrows to the obligation type that worked and G2 adds an evidence-quality threshold |
| **no-go** | otherwise (C01 located in <= 1 of 4, C02 false alarms >= 3 of 4, submissions <= 12 of 16, or C04 mechanical below 4/4) |
| **time box exhausted** | treated as no-go (spec §18.2) |

## 4. Host measurements (spec §18.2 items 1-6; results in `docs/dev/hep-review/host-profile.md`)

| Id | Measurement | How |
|---|---|---|
| H1 | Sibling readability | Two probe subagents A and B dispatched in parallel; A writes its drop file; B, told it is a capability probe, lists and reads A's drop directory and reports what it saw. Readable / not readable |
| H2 | Transcript writability | If subagent transcripts are on disk, locate the directory and test `os.access(path, os.W_OK)` only; never write to or modify a transcript |
| H3 | Parallelism | Every review dispatch and both probes write `started_at` / `ended_at` (UTC, from the `date` command or the clock) in their drop file; overlap of intervals among subagents dispatched in one message = parallel |
| H4 | Reviewer capabilities | Each reviewer writes its drop file with its file-write tool and, if it can, reports the file's SHA-256 in its reply; the coordinator checks the digest against the bytes it reads. Records file-transfer feasible yes/no and hash capable yes/no |
| H5 | Persistence | Read the T00 marker (`~/.local/state/hep-research/hep-review/hep-review-persistence-marker`); first session -> `pending-next-session` |
| H6 | Checkpoint handover | The session report hands the user a test checkpoint line; the next session records whether it came back |

## 5. What the spike path is

`spike/spike.py` (never imported by product code, not a module of the plugin): intent -> plan -> packet -> (dispatch by
the coordinator with the host's Agent tool) -> file submission read by bytes -> record -> projection -> report, using
plain files under a run folder in the session scratch; no SQLite. The run's raw submissions are kept byte for byte
and copied into `spike/runs/` with their SHA-256 after the reviews.
