"""D4 stage E6c: the evaluation's task runner (tests/adapters/t04_evaluation_tasks.py; d4-e6c-brief.md, items 3 and 4).

Hand-made inputs only: fake scripts in a temporary folder stand in for the recipe and fixture scripts (named as the real ones, so the runner
judges them by the real scripts' result lines), a hand-made sacct and hand-made milestones; no fixture is drawn, no recipe runs, no Slurm job
is submitted. Expectations, fixed before the first run (d4-e6c-report.md, "Predictions"): every block but 11 and 12 is refused by every
operation before anything is read; fit-started is in the milestones file before the first recipe call; a crashed range task leaves its bin
"missing" and every test of the bin "required output missing", so the workflow fails; the T07 interface is a stub that refuses.

Run from the plugin root: python -m unittest tests.adapters.test_t04_evaluation_tasks -v
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.adapters import t04_evaluation_core as core  # noqa: E402
from tests.adapters import t04_evaluation_layout as layout  # noqa: E402
from tests.adapters import t04_evaluation_tasks as tasks  # noqa: E402

TEMPORARY_ROOT = os.environ.get("TMPDIR") or None

FAKE_OK = r'''
import json, sys
from pathlib import Path
args = sys.argv[1:]
def value(flag):
    return args[args.index(flag) + 1] if flag in args else None
log = Path(sys.argv[0]).parent / "calls.log"
with open(log, "a") as stream:
    stream.write(Path(sys.argv[0]).name + " " + (args[0] if args else "") + "\n")
'''

FAKE_LIKE = FAKE_OK + r'''
import os
marks = Path(os.environ["FAKE_OUT"]) / "milestones.txt"
seen = marks.exists() and any(line.startswith("fit-started ") for line in marks.read_text().splitlines())
with open(Path(sys.argv[0]).parent / "seen.log", "a") as stream:
    stream.write(f"{args[0]} fit-started-before {seen}\n")
for flag in ("--product",):
    if value(flag) and args[0] in ("fit", "topology"):
        Path(value(flag)).write_text("{}\n")
if os.environ.get("FAKE_CRASH") == args[0]:
    raise RuntimeError("planted crash")
if args[0] == "check-product" and "--configuration" not in args and "single-photon" in (value("--product") or ""):
    print(json.dumps({"status": "rejected"})); sys.exit(2)
print(json.dumps({"status": "ok"}))
'''

FAKE_TRUTH_START = FAKE_OK + r'''
Path(value("--out")).write_text("{}\n")
print("RESULT " + json.dumps({"status": "ok"}))
'''


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_main(argv) -> tuple:
    stream = io.StringIO()
    with redirect_stdout(stream):
        code = tasks.main([str(a) for a in argv])
    return code, stream.getvalue()


class BlockRefusal(unittest.TestCase):
    def test_check_block(self):
        self.assertEqual((tasks.check_block(11), tasks.check_block(12), tasks.check_block("12")), (1, 2, 2))
        for block in (0, 1, 2, 3, 4, 5, 6, 10, 13, "x", None):
            with self.subTest(block=block), self.assertRaises(tasks.TaskError):
                tasks.check_block(block)

    def test_every_operation_refuses_another_block_before_reading(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            out = Path(folder) / "never"
            cases = [["t08-sample", "--index", 0, "--out", out, "--t08-generator", "/nonexistent"],
                     ["t09-generate", "--index", 0, "--out", out, "--t09-generator", "/nonexistent"],
                     ["t09-range", "--index", 0, "--range", 0, "--generation", out, "--out", out],
                     ["t09-fixed-points", "--out", out], ["collect", "--workflow", "T09", "--attempts", "/nonexistent", "--out", out],
                     ["score", "--workflow", "T08", "--index", 0, "--collection", "/nonexistent", "--out", out],
                     ["summary", "--workflow", "T08", "--scores", out, "--collection", out, "--attempts", out, "--out", out], ["plan"],
                     ["t07-bin", "--index", 0, "--out", out], ["t08-checks", "--out", out], ["t07-slices", "--index", 0, "--out", out]]
            for block in (1, 2, 5, 6, 10, 13):
                for case in cases:
                    with self.subTest(block=block, operation=case[0]):
                        code, text = run_main([case[0], "--block", block, *case[1:]])
                        self.assertEqual(code, 2)
                        self.assertIn(f"RESULT {case[0]} rejected", text)
                        self.assertIn(f"block {block} is refused", text)
            self.assertFalse(out.exists())


class FitStartedFirst(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT)
        base = Path(self.folder.name)
        self.light = base / "light"
        (self.light / "fixture_tools").mkdir(parents=True)
        (self.light / "photon_likelihood.py").write_text(FAKE_LIKE)
        (self.light / "fixture_tools" / "t09_truth_start.py").write_text(FAKE_TRUTH_START)
        self.generation = base / "generation"
        (self.generation / "ranges").mkdir(parents=True)
        ranges = []
        for span in tasks.T09_RANGES:
            files = tasks.t09_range_files(self.generation, span.first)
            files["readout"].write_bytes(f"readout {span.first}".encode())
            files["truth"].write_bytes(f"truth {span.first}".encode())
            ranges.append({"first": span.first, "count": span.count, "readout_sha256": sha(files["readout"]), "truth_sha256": sha(files["truth"])})
        self.document = {"workflow": "T09", "fixture_id": 9001, "block": 11, "stratum": 0, "label": "main-B1-r0.0-0.4", "stratum_sha256": "f" * 64,
                         "truth_sha256": "e" * 64, "ranges": ranges, "attempt": "1_0"}
        (self.generation / "generation.json").write_text(json.dumps(self.document))
        self.out = base / "range-0"
        os.environ["FAKE_OUT"] = str(self.out)

    def tearDown(self):
        os.environ.pop("FAKE_OUT", None)
        os.environ.pop("FAKE_CRASH", None)
        self.folder.cleanup()

    def test_fit_started_before_the_first_recipe_call(self):
        paths = tasks.Paths(light=self.light)
        self.assertEqual(tasks.t09_range(11, 0, 0, self.generation, self.out, paths), 0)
        self.assertEqual(tasks.Milestones(self.out).names(), ["fit-started"])
        seen = (self.light / "seen.log").read_text().splitlines()
        self.assertEqual(seen[0], "fit fit-started-before True")
        self.assertTrue(all(line.endswith("True") for line in seen))
        kinds = sorted(p.stem for p in (self.out / "records").glob("*.json"))
        self.assertEqual(kinds, ["multistart", "topology", "truth-start"])
        record = layout.RangeRecord.from_json((self.out / "records" / "multistart.json").read_text())
        self.assertEqual((record.block, record.stratum, record.first, record.count, record.stratum_sha256), (11, 0, 0, 500, "f" * 64))

    def test_range_files_other_than_generation_json_are_refused_before_any_fit(self):
        tasks.t09_range_files(self.generation, 0)["readout"].write_bytes(b"changed")
        with self.assertRaises(tasks.TaskError):
            tasks.t09_range(11, 0, 0, self.generation, self.out, tasks.Paths(light=self.light))
        self.assertFalse((self.light / "calls.log").exists())

    def test_a_crash_is_crashed_never_a_negative(self):
        os.environ["FAKE_CRASH"] = "topology"
        code, text = run_main(["t09-range", "--block", 11, "--index", 0, "--range", 0, "--generation", self.generation, "--out", self.out,
                               "--light-assets", self.light])
        self.assertEqual(code, 3)
        self.assertIn("RESULT t09-range crashed", text)
        self.assertFalse((self.out / "records" / "topology.json").exists())

    def test_a_task_of_another_block_than_its_generation_is_refused(self):
        with self.assertRaises(tasks.TaskError):
            tasks.t09_range(12, 0, 0, self.generation, self.out, tasks.Paths(light=self.light))


def fake_collection(base: Path, workflow: str, block: int, statuses: dict) -> Path:
    """A finished collection.json with every bin's status (hand-made)."""
    samples = tasks.T08_SAMPLES if workflow == "T08" else tasks.T09_SAMPLES
    bins = {label: {"status": statuses.get(label, "missing"), "reason": "hand-made: no attempt", "kinds": {}, "stops": []} for _, _, label in samples}
    path = base / "collection" / "collection.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"workflow": workflow, "block": block, "bins": bins, "finished": True}))
    return path


def fake_single(base: Path, name: str, operation: str, files: dict) -> tuple:
    folder = base / name.replace(" ", "-")
    folder.mkdir(parents=True)
    (folder / "milestones.txt").write_text("fit-started 2026-11-12T00:00:00Z\n")
    for file, text in files.items():
        (folder / file).write_text(text)
    return f"{name}\t900_0\t{folder}", folder


GATES = "GATE likelihood check, joint: PASS\nGATE likelihood check, charge-only: PASS\nGATE per-channel sum at the fixed points: PASS\n"
DONE = (lambda job: ("COMPLETED", 0, "00:02:00"))


class CrashedRangeIsMissing(unittest.TestCase):
    """A crashed range task (Slurm FAILED, exit 3, after fit-started, no record) makes its bin "missing" at the collection, every test of the bin
    "required output missing" at the scoring, and the workflow failed at the summary (v4 10; top-up never, v4 3.4)."""

    def test_end_to_end_on_records(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            base = Path(folder)
            gen = base / "gen"
            gen.mkdir()
            (gen / "generation.json").write_text(json.dumps({"fixture_id": 9001, "block": 11, "stratum": 4, "stratum_sha256": "f" * 64,
                                                             "label": "main-B2-r0.4-0.7", "truth_sha256": "e" * 64, "ranges": []}))
            (gen / "milestones.txt").write_text("draws-started 2026-11-12T00:00:00Z\n")
            crashed = base / "range-crashed"
            crashed.mkdir()
            (crashed / "milestones.txt").write_text("fit-started 2026-11-12T00:00:00Z\n")
            line, _ = fake_single(base, "T09 fixed points", "t09-fixed-points", {"t09-fixed-points.log": "RESULT t09-fixed-points ok\n",
                                                                                 "fixed-points.log": GATES})
            lines = ["T09 generate main-B2-r0.4-0.7\t100_4\t" + str(gen), line]
            lines += [f"{tasks.task_name('T09', 'main-B2-r0.4-0.7', s)}\t101_{i}\t{crashed}" for i, s in enumerate(tasks.T09_RANGES)]
            (base / "attempts.tsv").write_text("\n".join(lines) + "\n")
            states = {"100_4": ("COMPLETED", 0, "00:01:00"), "900_0": ("COMPLETED", 0, "00:02:00"),
                      **{f"101_{i}": ("FAILED", 3, "00:05:00") for i in range(len(tasks.T09_RANGES))}}
            state_of = (lambda job: states.get(job, ("PENDING", 0, "00:00:00")))
            with redirect_stdout(io.StringIO()) as printed:
                tasks.collect("T09", 11, base / "attempts.tsv", base / "collection", state_of=state_of)
            collection = json.loads((base / "collection" / "collection.json").read_text())
            self.assertTrue(collection["finished"])
            self.assertEqual(collection["bins"]["main-B2-r0.4-0.7"]["status"], "missing")
            self.assertIn("the last attempt of the task did not complete", collection["bins"]["main-B2-r0.4-0.7"]["reason"])
            self.assertIn("COLLECT T09 block 11 main-B2-r0.4-0.7: missing", printed.getvalue())
            for index in range(tasks.T09_POOL_INDEX + 1):
                with redirect_stdout(io.StringIO()):
                    tasks.score("T09", 11, index, base / "collection" / "collection.json", base / "scores" / f"bin-{index}", tasks.Paths())
            records = json.loads((base / "scores" / "bin-4" / "records.json").read_text())
            self.assertEqual(len(records), 24)
            self.assertTrue(all(r["result"] == "inconclusive" and "required output missing" in r["reason"] for r in records))
            self.assertTrue((base / "scores" / "bin-4" / "scored.json").exists())
            with redirect_stdout(io.StringIO()) as printed:
                code = tasks.summary("T09", 11, base / "scores", base / "collection" / "collection.json", base / "summary",
                                     attempts_file=base / "attempts.tsv", state_of=state_of)
            self.assertEqual(code, 0, printed.getvalue())
            outcome = json.loads((base / "summary" / "outcome.json").read_text())
            self.assertEqual((outcome["workflow_result"], outcome["r11_state"]), ("fail", "failed"))
            self.assertIn("a required check was inconclusive (R11)", outcome["reasons"])

    def test_a_repeat_after_a_draw_is_not_counted_on_block_11(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            first, second = Path(folder) / "a", Path(folder) / "b"
            for f in (first, second):
                f.mkdir()
                (f / "milestones.txt").write_text("draws-started 2026-11-12T00:00:00Z\n")
            states = {"1": ("NODE_FAIL", 0, "00:03:00"), "2": ("COMPLETED", 0, "00:03:00")}
            with self.assertRaises(layout.LayoutError):
                tasks.counted_folder([("1", first), ("2", second)], 11, lambda job: states[job])

    def test_a_failed_generator_check_is_not_repeatable(self):
        self.assertEqual(layout.classify_attempt("FAILED", 1, "00:01:00", ["generator-check-failed"])[0], "NOT-REPEATABLE")
        self.assertEqual(layout.classify_attempt("FAILED", 1, "00:01:00", ["block6-started"])[0], "NO-DRAW")


class HarnessCrashIsIncomplete(unittest.TestCase):
    """Fix round 1, I1: a scoring task, a collection or a fixed-points run that crashed or was refused is SUMMARY INCOMPLETE, exit 3, never a
    workflow fail (and never the T09 stop); I2: a required check absent is incomplete too."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT)
        self.base = Path(self.folder.name)
        self.collection = fake_collection(self.base, "T08", 12, {})
        for index in range(15):
            with redirect_stdout(io.StringIO()):
                tasks.score("T08", 12, index, self.collection, self.base / "scores" / f"bin-{index}", tasks.Paths())
        line, self.checks_folder = fake_single(self.base, "T08 checks", "t08-checks", {"t08-checks.log": "RESULT t08-checks ok\n",
                                                                                     "checks.json": json.dumps([{"name": n, "kind": "cai", "result": "pass", "stop": False,
                                                                                                                 "recorded_unsupported_gap": False}
                                                                                                                for n in ("CAI-T08-1", "CAI-T08-2")] +
                                                                                                               [{"name": "reference selection (A38.1)", "kind": "deterministic",
                                                                                                                 "result": "pass", "stop": False, "recorded_unsupported_gap": False}])})
        (self.base / "attempts.tsv").write_text(line + "\n")

    def tearDown(self):
        self.folder.cleanup()

    def run_summary(self):
        with redirect_stdout(io.StringIO()) as printed:
            code = tasks.summary("T08", 12, self.base / "scores", self.collection, self.base / "summary", attempts_file=self.base / "attempts.tsv",
                                 state_of=DONE)
        return code, printed.getvalue()

    def test_every_harness_task_finished_gives_an_outcome(self):
        code, text = self.run_summary()
        self.assertEqual(code, 0, text)
        self.assertIn("OUTCOME T08 block 12 attempt 2: gate result fail, R11 state failed", text)   # every bin recipe-side missing

    def test_a_scoring_task_that_left_no_marker_is_incomplete(self):
        (self.base / "scores" / "bin-7" / "scored.json").unlink()
        code, text = self.run_summary()
        self.assertEqual(code, 3)
        self.assertIn("SUMMARY INCOMPLETE T08 block 12: the scoring of bin 7 left no scored.json", text)
        self.assertNotIn("OUTCOME", text)

    def test_a_crashed_collection_is_incomplete(self):
        self.collection.unlink()
        code, text = self.run_summary()
        self.assertEqual(code, 3)
        self.assertIn("collection left no collection.json", text)
        code, text = run_main(["score", "--block", 12, "--workflow", "T08", "--index", 0, "--collection", self.collection, "--out", self.base / "x"])
        self.assertEqual(code, 3)
        self.assertIn("RESULT score incomplete", text)

    def test_a_checks_run_without_its_result_is_incomplete(self):
        (self.checks_folder / "t08-checks.log").write_text("Traceback (most recent call last):\n")
        code, text = self.run_summary()
        self.assertEqual((code, "no result line ok or failed" in text), (3, True))

    def test_a_required_check_absent_is_incomplete(self):
        (self.checks_folder / "checks.json").write_text("[]")
        code, text = self.run_summary()
        self.assertEqual(code, 3)
        self.assertIn("required checks absent", text)

    def test_t09_fixed_points_without_their_gate_lines_are_incomplete_not_the_stop(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            base = Path(folder)
            collection = fake_collection(base, "T09", 11, {})
            for index in range(tasks.T09_POOL_INDEX + 1):
                with redirect_stdout(io.StringIO()):
                    tasks.score("T09", 11, index, collection, base / "scores" / f"bin-{index}", tasks.Paths())
            line, fixed = fake_single(base, "T09 fixed points", "t09-fixed-points", {"t09-fixed-points.log": "RESULT t09-fixed-points failed\n",
                                                                                     "fixed-points.log": "ERROR fixed points: unexpected\n"})
            (base / "attempts.tsv").write_text(line + "\n")
            with redirect_stdout(io.StringIO()) as printed:
                code = tasks.summary("T09", 11, base / "scores", collection, base / "summary", attempts_file=base / "attempts.tsv", state_of=DONE)
            self.assertEqual(code, 3)
            self.assertIn("printed 0 GATE lines, not 3", printed.getvalue())
            (fixed / "fixed-points.log").write_text(GATES.replace("joint: PASS", "joint: FAIL"))
            with redirect_stdout(io.StringIO()) as printed:
                code = tasks.summary("T09", 11, base / "scores", collection, base / "summary", attempts_file=base / "attempts.tsv", state_of=DONE)
            self.assertEqual(code, 0)
            self.assertIn("deterministic check fixed likelihood points", printed.getvalue())

    def test_a_failed_generator_check_goes_to_the_user(self):
        """Fix round 2, R4."""
        with open(self.checks_folder / "milestones.txt", "a") as stream:
            stream.write("generator-check-failed 2026-11-12T00:00:00Z\n")
        code, text = self.run_summary()
        self.assertEqual(code, 3)
        self.assertIn("goes to the user", text)
        self.assertNotIn("rerun it", text)

    def test_a_replaced_pool_file_is_incomplete(self):
        """Fix round 2, R5: the pool reads only a pool.npz that its scored.json names."""
        import numpy
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            base = Path(folder)
            statuses = {label: "complete" for f, s, label in tasks.T09_SAMPLES if f == 9001 and s in range(3, 12)}
            collection = fake_collection(base, "T09", 11, statuses)
            tag = tasks.sha256_file(collection)
            for s in range(3, 12):
                columns = {k: numpy.ones(2, dtype=numpy.int64) for k in ("reversed_m", "reversed_y", "mirrored_m", "mirrored_y")}
                columns["reversed_y"][:] = 0
                columns["mirrored_y"][:] = 0
                with redirect_stdout(io.StringIO()):
                    tasks.write_scores(base / "scores" / f"bin-{s}", [], [], [], collection_sha256=tag, label=f"bin {s}", extra=columns)
            with redirect_stdout(io.StringIO()):
                tasks.score("T09", 11, tasks.T09_POOL_INDEX, collection, base / "scores" / f"bin-{tasks.T09_POOL_INDEX}", tasks.Paths())
            records = json.loads((base / "scores" / f"bin-{tasks.T09_POOL_INDEX}" / "records.json").read_text())
            self.assertEqual([(r["gate"], r["readings"]["objects"]) for r in records], [("reversed", 18), ("mirrored", 18)])
            numpy.savez(base / "scores" / "bin-5" / "pool.npz", **{k: numpy.zeros(2, dtype=numpy.int64) for k in columns})
            code, text = run_main(["score", "--block", 11, "--workflow", "T09", "--index", tasks.T09_POOL_INDEX, "--collection", collection,
                                   "--out", base / "scores" / "pool-again"])
            self.assertEqual(code, 3)
            self.assertIn("pool.npz is not its scored.json's", text)

    def test_a_recorded_stop_is_a_failed_check_with_its_stop(self):
        document = json.loads(self.collection.read_text())
        document["bins"]["main-E2-iso"]["stops"] = [{"check": "double-count main-E2-iso", "line": '{"status": "failed"}', "exit": 1, "stop": True}]
        self.collection.write_text(json.dumps(document))
        for index in range(15):
            with redirect_stdout(io.StringIO()):
                tasks.score("T08", 12, index, self.collection, self.base / "scores" / f"bin-{index}", tasks.Paths())
        code, text = self.run_summary()
        self.assertEqual(code, 0, text)
        outcome = json.loads((self.base / "summary" / "outcome.json").read_text())
        self.assertTrue(outcome["stop"])
        self.assertIn("STOP T08 main-E2-iso: double-count main-E2-iso", text)


class ChecksSource(unittest.TestCase):
    def test_the_users_answer_and_the_other_refused(self):
        self.assertEqual((tasks.CHECKS_SOURCE, tasks.checks_source()), ("rerun-at-evaluation", "rerun-at-evaluation"))
        with self.assertRaises(tasks.TaskError):
            tasks.checks_source("freeze-b-record")
        self.assertEqual(tasks.CHECKS_BLOCK, 1)


class T07Interface(unittest.TestCase):
    def test_the_stub_refuses(self):
        with self.assertRaises(tasks.T07InterfaceNotMerged):
            tasks.t07_interface("score", block=11, index=0)
        for op in ("t07-bin", "t07-refit", "t07-score", "t07-slices"):
            code, text = run_main([op, "--block", 11, "--index", 0, "--out", "/nonexistent-e6c"])
            self.assertEqual(code, 2)
            self.assertIn("E6b's interface is not merged", text)
        for op in ("t07-negative-cases", "t07-checks"):
            code, text = run_main([op, "--block", 11, "--out", "/nonexistent-e6c"])
            self.assertEqual(code, 2)
        code, text = run_main(["collect", "--block", 11, "--workflow", "T07", "--attempts", "/x", "--out", "/nonexistent-e6c"])
        self.assertEqual(code, 2)
        code, text = run_main(["summary", "--block", 11, "--workflow", "T07", "--attempts", "/x", "--collection", "/x", "--scores", "/x", "--out", "/x"])
        self.assertEqual(code, 2)

    def test_the_commands_use_the_t07_scoring_argument_names(self):
        """d4-e6b-report.md, "The interface for E6c": score-bin, score-slices, negative-cases, summary and their options."""
        flags = (lambda command: [c for c in command if c.startswith("--")])
        bin_ = tasks.t07_commands("score-bin", block=11, fixture_id=7002, stratum=3, record="r", product="p", truth="t", out="o",
                                  truth_seeded_record="ts", rate_record="rr")
        self.assertEqual(bin_[bin_.index(str(tasks.T07_SCORING_SCRIPT)) + 1], "score-bin")
        self.assertEqual(flags(bin_), ["--block", "--fixture-id", "--stratum", "--events", "--record", "--product", "--truth", "--out",
                                       "--truth-seeded-record", "--rate-record"])
        self.assertIn("--refit-collection", flags(tasks.t07_commands("score-bin", block=11, fixture_id=7001, stratum=3, record="r", product="p",
                                                                     truth="t", out="o", refit_collection="j")))
        self.assertEqual(flags(tasks.t07_commands("score-slices", block=12, fixture_id=7001, bins="b", out="o", parameters="loc0")),
                         ["--block", "--fixture-id", "--events", "--bins", "--out", "--parameters"])
        self.assertEqual(flags(tasks.t07_commands("negative-cases", block=11, record="r", seeds="s", out="o")),
                         ["--block", "--folder", "--record", "--seeds", "--out"])
        self.assertEqual(flags(tasks.t07_commands("summary", block=11, scores="s", checks="c")), ["--block", "--scores", "--checks"])
        self.assertEqual(layout.RESULT_LINES["t07_evaluation_scoring.py"], r"^RESULT t07-scoring [a-z-]+ (ok|failed|rejected):")


class PlanTotals(unittest.TestCase):
    def test_plan_with_the_measured_refit(self):
        found = layout.evaluation_plan(block=11)
        self.assertEqual(layout.t07_refit_range(), 4000)
        counts = found.task_counts()
        self.assertEqual((counts["T07 refit"], counts["T09 range"], counts["T08 sample"], counts["T07 slices"]), (36, 360, 15, 10))
        code, text = run_main(["plan", "--block", 12])
        self.assertEqual(code, 0)
        self.assertIn(f"PLAN tasks {len(found.tasks)}", text)
        self.assertIn(f"PLAN total {found.cpu_hours():.1f} CPU-hours", text)

    def test_names_cover_the_single_and_t07_tasks(self):
        names = {name for _, _, _, name in tasks.task_names()}
        self.assertTrue({"T09 fixed points", "T08 checks", "T07 bin 0", "T07 refit 35", "T07 negative cases", "T07 checks"} <= names)
        self.assertEqual(len(tasks.task_names()), 15 + 15 + 360 + 2 + 24 + 36 + 2)


if __name__ == "__main__":
    unittest.main()
