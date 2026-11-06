# g4sim execution plan: baselines, timing and long jobs

Why this exists: in S1 a reproduction job took about 6 hours on one Mac after being estimated at 0.15 hours, nothing could run elsewhere, and reference outputs lived on one machine. This plan keeps that from recurring. It changes how work is run, not Part B: gates, thresholds and the 112 recorded runs stay as they are. The maintainer's decision is in `g4sim-approvals.md` ("use linux as baseline").

## What went wrong, and the rule that prevents it

| Problem in S1 | Rule from now on |
| --- | --- |
| Runs could be reproduced on one machine only | New baselines are recorded on Linux (E5), where anyone can rerun them |
| Run records held no timings, so the cost was a guess | Every run record stores its time; a cost is a sum of recorded times |
| A small sample missed the expensive run types | A sample never prices a job when recorded times exist; a job with neither gets a time check first |
| Reference outputs existed on one disk | References live on shared storage with a hash list |
| A job depended on an open session | Long jobs run detached, resumable, with a status file |
| Commands were pasted by hand | Each machine runs one script, which writes one report |
| Two sessions committed to one branch | One writer per branch at a time |
| Wider repository rules were found late | The full check runs at each milestone, and checks gate every commit |

## 1. Baselines on Linux (from S2)

- New g4sim baselines are recorded on E5. A baseline belongs to its platform: E2 and E5 are not assumed bit-identical, so a T1 comparison is always against a baseline from the same platform.
- Each baseline records: platform, compiler, flags, Geant4 build hash, source commit, seed, events, threads, output hashes and wall time.
- Gates that name both E2 and E5 still run on both. They should be short by design, like the golden `geometry_id` check.
- The 112 recorded runs keep their E2 references. After S1 they are needed only for the S2 T1 gate, and `reproduce.py` is the way to rerun them.

Done when: an S2 baseline can be rerun on E5 from the repository and its records alone.

## 2. Timing in every run record (S2)

- `g4sim_run` writes `wall_seconds`, `cpu_seconds`, `startup_seconds`, the thread count and the load average at start.
- A negative test: a run record without these fields is refused.

Done when: the cost of any job over recorded runs is one sum, with no sample.

## 3. Reference storage (after S1)

- The maintainer names a shared folder this host can read, such as the AMS group area. Size first: `du -sh ~/Workspace/geant4-work`.
- Copy only what regression needs: reference outputs, specs and probe records, with a `SHA256SUMS` file. `g4sim_inventory.py check-work` already verifies by hash.

Done when: `check-work` passes from the shared folder on E5.

Changed by the maintainer on 2026-11-06 (`g4sim-approvals.md`): the shared references are the Linux outputs of the 112 runs, regenerated from the old programs on Slurm, and the Mac's originals are not copied. So the check is against the E5 baselines' hashes, not `check-work`, whose hashes are E2's.

## 4. Estimating cost

1. Use recorded times when they exist. Add 15 % for a loaded machine.
2. With none, time every distinct run type, not a sample of runs. Report it as an estimate and name what it leaves out.
3. Compare the estimate with the first few real runs. If they run over by more than a factor of 2, stop and report before going on.

## 5. Long jobs

Any job over 10 minutes:

- runs detached (`nohup`, and `caffeinate` on macOS), so closing a session cannot end it;
- is resumable: finished work is saved after each unit;
- writes `status.json` with done, total, current item, start time and estimated end;
- deletes bulky output once hashed, and states its disk need first;
- never writes near reference outputs: every output path is redirected, as in `reproduce.py`.

`reproduce.py` already resumes and redirects; it gains `status.json`, and `run_job.sh` wraps the detached start for both platforms.

## 6. Scale-out (optional, after S2)

Runs are independent and new baselines are on Linux, so a large job can run as a Slurm array on NSTCCore instead of one after another. Each submission needs the maintainer's approval. This is the only real way to shorten a multi-hour job: on one machine the cores were already full.

## 7. Working rules

- **One writer:** a branch has one committing session at a time. Other machines report results and do not commit, unless agreed for that task.
- **Commits:** tests, `check_naming.py` and `check_layering.py` run first, chained, so a failure stops the commit. Time limits must exceed the slowest module.
- **Full check:** `run_all_checks.py` runs at each milestone of a phase, not only at its end.
- **Live checks:** a round trip proves consistency, not correctness. Check against a real Geant4 record too: that is what found the frame error in the translator.
- **Worktree names:** two `hep_authoring` tests match `S1` in the path. They are rerun from a neutral path at each gate.

## Schedule

| When | What | Who |
| --- | --- | --- |
| End of S1 | Finish the reproduction job, inventory, version bumps, gate record | Claude, maintainer's Mac |
| End of S1 | Size of `geant4-work`, then a shared folder | Maintainer |
| S2 start | Sections 1 and 2 into the S2 card; `status.json` and `run_job.sh` | Claude |
| S2 | First Linux baselines; first job under Sections 4 and 5 | Claude |
| After S2 | Section 3 copy; decide on Section 6 | Maintainer, Claude |

## How we know it worked

- No job is more than a factor of 2 over its estimate without a report at the first few runs.
- A regression after S2 needs no Mac, except for gates that name E2.
- No reference output exists on only one disk.
- Closing a session never loses more than the unit in progress.
