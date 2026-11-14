# E6 RESULT_LINES audit (block-11 evaluation running), 2026-11-13

> Copy of the ledger file `<private>/worktree/.superpowers/sdd/finish-plan/e6-result-lines-audit.md` (git-ignored, SHA-256 `ba01bb028f60aaeed8f7e5083c80f00fb69c26e0f970738d4bca7da6cf0f573e`), copied into the tracked records on 2026-11-14 (G3) because `decisions.md` cites it. Content unchanged below this note; it held no absolute host path. Relative paths such as `evidence/...` and `jobs/...` are under `<private>/`.

Read only. Tree: worktree/plugins/hep-research at 268e5bd4 (feature/detector-reconstruction). The running jobs execute the snapshot
evidence/evaluation-tree-d98f5e6f.../worktree/plugins/hep-research. I compared all 12 files audited here (t04_evaluation_layout.py,
t04_evaluation_tasks.py, t07_evaluation_scoring.py, t08_cai.py, t08_scenarios.py, t08_fixture_files.py, calo_cluster.py,
photon_likelihood.py, t09_fixture_files.py, t09_negative_checks.py, t09_truth_start.py, t09_fixed_points.py). All 12 are
byte-identical to the worktree, so the findings below describe what is running now.

## How the patterns are used

- `run_script` (t04_evaluation_tasks.py:411) looks up `RESULT_LINES["<script> <argv[0]>"]` first, then falls back to `RESULT_LINES["<script>"]`.
  `classify_script_run` (t04_evaluation_layout.py:275) gives "crashed" if the run has a traceback, if no line matches, or if the exit code
  is outside 0-3. Otherwise exit 0 is ok, exit 3 is incomplete, and exit 1 or 2 is negative. The line returned is the last matching line.
- Only the T08 and T09 recipe and fixture scripts go through `run_script`. Every T07 operation (bin, refit, negative cases, checks,
  collect, score, slices, summary) runs in the same process through `t07_run` -> `t07_evaluation_scoring.t07_interface`. Its exit code
  is used directly. T07 checks are judged by `unittest_verdict`, not by RESULT_LINES.
- The collections, scoring (T08, T09 and the T09 pool), the T08/T09/T07 summaries and the T07 slices call no scripts. They run in the
  same process, and each job script judges the runner's own line with its `need '^RESULT <op> (ok|failed|rejected|crashed|incomplete)'`.
  **Nothing that block 11 still has to run after the ranges (collections, scoring, slices, pool, summaries) depends on RESULT_LINES.**
  The steps still running that do depend on it are the T09 range tasks: photon_likelihood fit, topology and check-product, and
  t09_truth_start fit.

## Table: every RESULT_LINES entry

"Fallback" means the call site's argv[0] is not a key, so the bare-name entry is used.

| key | runner call site(s) (t04_evaluation_tasks.py) | verdict prints (script:line) | regex matches | only verdict lines? | exercised in a real job |
|---|---|---|---|---|---|
| t08_cai.py rereco | 554 (t08-checks) | ok: t08_cai.py:333 via 448..458 `CAI-T08-2 {label} RECORD recorded without a numeric assertion (R37)`, exit 0; refused: :461 `REFUSED {label} rereco: ...`, exit 2; unexpected exception: traceback | **ok line: NO**; REFUSED: yes; traceback: crash (correct) | yes. The `GATE ` alternative is dead: rereco never prints GATE | b11 7613402 main-E3-iso/cai2-multiply.log: real ok output, read as crashed. Freeze-B t08-7585955 printed the same RECORD lines (judged there by exit code only). Never matched in any job |
| t08_cai.py fixed-membership | 544, 546 | :192 `CAI-T08-1 {label} RESULT PASS/FAIL` (last line), exit 0/1; :461 REFUSED, exit 2 | yes / yes | yes. The earlier lines say RECORD or `...: PASS` with no " RESULT " | b11 7613402 cai1-multiply.log (PASS), cai1-control-multiply.log (FAIL), both matched |
| t08_cai.py payloads | 536 | :425 `{"status": "ok", ...}`; :461 `REFUSED payloads payloads: ...` | yes / yes | yes (one line) | b11 7613402 payloads.log |
| t08_scenarios.py accounting | 504 (t08-sample) | :206 `GATE {label} selection-and-accounting PASS/FAIL: ...` (followed by DEFECT lines, which do not match); :243 REFUSED, exit 2 | yes / yes | yes (the A38 and DEFECT lines do not match) | b11 T08 sample-0..14 (all PASS); d4-e6c-7592360 t08 |
| t08_scenarios.py reference-selection | 557 (t08-checks) | :221 `GATE reference-selection PASS/FAIL: ...` (after DEFECT lines); :243 REFUSED | yes / yes | yes | **Never** through run_script: b11 7613402 crashed before reaching it; Freeze-B t08-7585955 did not run it; no other run found |
| t08_fixture_files.py (fallback, argv[0] `--generator`) | 494, 533 | :154 `{"status": "ok", ...}`; :152 `{"status": "rejected"}` exit 2; :146 missing-dependency exit 3 | yes / yes / yes | yes (one line) | b11 T08 samples and 7613402 generate.log; d4-e6c |
| calo_cluster.py (fallback: reconstruct, check-product) | 498, 501, 541, 543, 550, 553 | report() :40, a single JSON line on every handled path (ok, failed exit 1, rejected exit 2, missing-dependency exit 3); other exceptions give a traceback | yes on all | yes | b11 T08 samples, 7613402 nominal/derived/check-*; d4-e6c |
| t09_fixture_files.py (fallback, `--generator`) | 589 | :159 ok; :157 rejected; :151 missing-dependency | yes | yes | b11 T09 generate-0..14; d4-e6c |
| t09_negative_checks.py relabel-dead | 602 | :302 `{"status": "ok", ...}`; :309 `REFUSED relabel-dead: ...` | yes / yes | yes | b11 generate-12 relabel-r*.log; d4-e6c dead-B3/relabel.log |
| photon_likelihood.py (fallback: fit, topology, check-product) | 638, 643, 653, 661, 668, 671 | report() :53, a single JSON line on every path, including `"status": "error"` (exit 2) from the catch-all at :282 | yes on all | yes, but see defect 3: "error" is matched and read as negative, not crash | fit, check-product: b11 ranges (e.g. range-0-0/7613404_0); topology, check-topology, fit-unhit, check-unhit, fit-single-photon, check-single-photon(-main): d4-e6c only. b11 topology was still running (.partial) when I looked |
| t09_truth_start.py (fallback: fit) | 649 | :338 `RESULT {json}` on every path (ok, rejected, error); REFUSED/ERROR/READING lines come before it | yes | yes | b11 range-0-0 truth-start.log; d4-e6c |
| t09_fixed_points.py (fallback, `--generator`) | 685 | :107 `GATE per-channel sum at the fixed points ... PASS/FAIL` (last of 3 GATE lines); :119 `REFUSED fixed points:`; :124 `ERROR fixed points:` exit 2 | yes / yes / yes | yes (POINT, READING and the other two GATE lines do not match) | b11 T09 fixed-points/7613448 (PASS) |
| t07_evaluation_scoring.py | none (in-process) | `_result` :1825 `RESULT t07-scoring <op> ok/failed/rejected/incomplete: ...` | yes for every word printed | yes | not used by run_script. The b11 T07 bins print it (e.g. bin-0 t07-bin.log) |
| t04_evaluation_tasks.py | none (job scripts use their own `need`) | main :498-521 `RESULT <op> ok/failed/rejected/incomplete/crashed[: ...]` | yes | yes | not used by run_script |
| t07_fake_rate.py run | none | `RESULT ok/failed/refused:`; REJECTED lines (exit 2) at main :559/:564/:567 | REJECTED: no (would read as crash) | yes | not used by the evaluation |
| t07_fake_rate.py check | none | `OK `/`REFUSED `/`REJECTED ` | yes | yes | not used |
| fbrun_tools.py classify | none | `CLASSIFY job ...`; `REJECTED ...` exit 2 | REJECTED: no | yes | not used (Freeze-B run only) |
| fbrun_tools.py t07-comparator | none | `RESULT comparator ok/failed:`; `REJECTED t07-comparator: ...` | REJECTED: no | yes | not used |
| check_generators.py | none (lib.sh generator_check uses its own `need`) | `RESULT PASS` | yes | yes | not used by run_script |

Runner call sites with no entry of their own: none would raise TaskError. The ones that rely on the bare-name fallback are
t08_fixture_files.py (494, 533), calo_cluster.py reconstruct/check-product (498, 501, 541, 543, 550, 553), t09_fixture_files.py (589),
photon_likelihood.py fit/topology/check-product (638, 643, 653, 661, 668, 671), t09_truth_start.py fit (649) and t09_fixed_points.py
(685). For t08_fixture_files.py, t09_fixture_files.py and t09_fixed_points.py the lookup key is "<script> --generator", which is never
a key. All these fallbacks are correct today.

## Defects, most urgent first

1. **t08_cai.py rereco: the success line never matches** (t04_evaluation_layout.py:266 against t08_cai.py:333). The pattern expects
   `RESULT (PASS|FAIL|RECORDED)`, but the script ends with `CAI-T08-2 {label} RECORD recorded without a numeric assertion (R37)`. The
   test example (test_t04_evaluation_layout.py:411) invents "RESULT RECORDED", so the test checks the pattern against itself, not
   against the script.
   - Effect on block 11: T08 checks 7613402 crashed at its first rereco (exit 3, `RESULT t08-checks crashed`). No checks.json was
     written, so CAI-T08-1, CAI-T08-2 and the reference selection have no block-11 result.
   - The attempt has milestones draws-started and fit-started and exit 3, so classify_attempt gives REPEATABLE. On block 11,
     select_attempt allows only NO-DRAW or NEVER-RAN before the counted attempt. So even a fixed rerun cannot be counted, and the T08
     summary will end SUMMARY INCOMPLETE (counted_single raises Incomplete) unless the coordinator rules. The draws are block-1 check
     events, not evaluation events, which may matter for that ruling.
   - Every other T08 task (the 15 samples) ended ok.

2. **The single-photon refusal check accepts any exit 2** (t04_evaluation_tasks.py:671, `ok=(2,)`, the line is ignored).
   photon_likelihood.py also exits 2 for `"status": "error"` (catch-all :282, any unexpected exception in the reader), so a defect in
   the main reader would pass as "the main reader refuses the single-photon product". The Freeze-B run's t09-ms.sh:156-158 required the
   status to be "rejected", so this is a regression from the jobs of record.
   - Effect on block 11: this applies only to the range tasks of T09 sample 10 (fixture 9001, stratum 10). None of them had started
     when I looked. It can only produce a false pass, never a false crash. After the run, check-single-photon-main.log in each of those
     range folders should be checked by hand for `"status": "rejected"`. In d4-e6c it was rejected (correct).

3. **A recipe defect is read as a negative result, not a crash, for photon_likelihood.py and t09_truth_start.py.** Their catch-alls
   print a matching line with status "error" and exit 2. That covers an unexpected exception, a MemoryError, or a ModuleNotFoundError
   from the light_recipe imports inside the operations (photon_likelihood.py:95, 181, 204). classify_script_run reads it as negative,
   then StepFailed makes `RESULT t09-range failed` (exit 1, NOT-REPEATABLE). The layout's own rule is that a ModuleNotFoundError at
   import is a crash, never a negative reading. t09_fixed_points.py's ERROR line is the same, although its docstring makes that
   intended.
   - Effect on block 11: the bin is "required output missing" either way, because a crash after fit-started cannot be repeated on
     block 11 either. Only the label differs (failed instead of crashed). If a range task fails, read the JSON status in its step log
     before treating it as a gate failure.
   - None has happened so far: every finished range step printed status ok.

4. Dormant, not used by the evaluation: the entries for t07_fake_rate.py run, fbrun_tools.py classify and fbrun_tools.py
   t07-comparator do not match those scripts' REJECTED lines (exit 2), so a refused input would be read as a crash. The entries for
   t07_fake_rate.py (run, check), fbrun_tools.py, check_generators.py, t07_evaluation_scoring.py and t04_evaluation_tasks.py are not
   used by any run_script call.

5. Coverage gap: t08_scenarios.py reference-selection has never run through run_script in any job. Its pattern matches the script's
   lines as read, but there is no recorded output to confirm it.

Nothing else is wrong: every other active pair's regex matches every verdict line its script can print, and matches no earlier
informational line.

Note on method: one read-only grep over evidence/ hit its time limit and was moved to the background automatically. I stopped it
(TaskStop) with no output. It wrote nothing to evidence/.
