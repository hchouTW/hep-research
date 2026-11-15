"""D4 stage E6c: the evaluation's task runner (tests/adapters/t04_evaluation_tasks.py; d4-e6c-brief.md, items 3 and 4).

Hand-made inputs only: fake scripts in a temporary folder stand in for the recipe and fixture scripts (named as the real ones, so the runner
judges them by the real scripts' result lines), a hand-made sacct and hand-made milestones; no fixture is drawn, no recipe runs, no Slurm job
is submitted. Expectations, fixed before the first run (d4-e6c-report.md, "Predictions"): every block but 11 and 12 is refused by every
operation before anything is read; fit-started is in the milestones file before the first recipe call; a crashed range task leaves its bin
"missing" and every test of the bin "required output missing", so the workflow fails; the T07 calls are E6b's commands, each parsed by E6b's
own parser (E6 merge stage, E6c re-review R2), and a T07 harness task that left no marker makes the summary incomplete.

Run from the plugin root: python -m unittest tests.adapters.test_t04_evaluation_tasks -v
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shlex
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
from tests.adapters import t07_evaluation_scoring as scoring  # noqa: E402

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
    """E6 merge stage (E6c re-review R2): E6c's T07 calls adapted to E6b's parser. Every call is E6b's operation and keywords (t07_call), run by
    E6b's t07_interface; each parses through E6b's real build_parser; the stub is gone."""

    def parsed(self, operation, **arguments):
        e6b_operation, keywords = tasks.t07_call(operation, **arguments)
        argv = scoring.interface_argv(e6b_operation, **keywords)
        with redirect_stdout(io.StringIO()):
            try:
                return argv, scoring.build_parser().parse_args(argv)
            except SystemExit:
                self.fail(f"E6b's parser refuses {argv}")

    def test_the_stub_is_gone(self):
        self.assertFalse(hasattr(tasks, "T07InterfaceNotMerged"))
        self.assertFalse(hasattr(tasks, "T07_INTERFACE_STATE"))

    def test_every_call_parses_through_the_t07_scoring_parser(self):
        argv, ns = self.parsed("bin", block=11, index=23, build="b", out="o")
        self.assertEqual((ns.operation, ns.fixture_id, ns.stratum, ns.first, ns.count, ns.build, ns.out), ("bin-task", 7002, 11, 0, 12000, "b", "o"))
        _, ns = self.parsed("bin", block=12, index=0, build="b", out="o")
        self.assertEqual((ns.block, ns.fixture_id, ns.stratum), (12, 7001, 0))
        _, ns = self.parsed("refit", block=11, index=35, bin_dir="d", build="b", out="o")
        self.assertEqual((ns.operation, ns.stratum, ns.first, ns.count, ns.bin_dir), ("refit-task", 11, 8000, 4000, "d"))
        _, ns = self.parsed("refit", block=11, index=0, bin_dir="d", build="b", out="o")
        self.assertEqual((ns.stratum, ns.first, ns.count), (0, 0, 4000))
        _, ns = self.parsed("slices", block=11, index=9, scores="s")
        self.assertEqual((ns.operation, ns.fixture_id, ns.events, ns.bins, ns.out, ns.parameters), ("score-slices", 7002, 12000, "s", "s", "q/p"))
        _, ns = self.parsed("slices", block=11, index=0, scores="s")
        self.assertEqual((ns.fixture_id, ns.parameters), (7001, "loc0"))
        _, ns = self.parsed("negative-cases", block=11, build="b", out="o")
        self.assertEqual((ns.operation, ns.folder), ("negative-task", str(tasks.T07_NEGATIVE_FOLDER)))
        _, ns = self.parsed("checks", block=11, build="b", out="o", workers=2)
        self.assertEqual((ns.operation, ns.workers), ("checks-task", 2))
        _, ns = self.parsed("collect", block=11, index=12, attempts="a.json", out="c.json")
        self.assertEqual((ns.operation, ns.fixture_id, ns.stratum, ns.count, ns.refit_range), ("collect", 7002, 0, 12000, 4000))
        _, ns = self.parsed("score", block=11, index=5, collection="c.json", scores="s")
        self.assertEqual((ns.operation, ns.fixture_id, ns.stratum, ns.events, ns.collection, ns.out, ns.rate_record), ("score-bin", 7001, 5, 12000, "c.json", "s", None))
        _, ns = self.parsed("score", block=11, index=17, collection="c.json", scores="s", rate_record="rr")
        self.assertEqual((ns.fixture_id, ns.stratum, ns.rate_record), (7002, 5, "rr"))
        argv, ns = self.parsed("summary", block=11, scores="s", checks="n.json,d.json")
        self.assertEqual((ns.operation, ns.scores, ns.checks), ("summary", "s", "n.json,d.json"))
        self.assertNotIn("--out", argv)                                  # E6b's summary has no --out
        e6b_operation, keywords = tasks.t07_call("score", block=11, index=5, collection="c", scores="s")
        self.assertNotIn("--index", scoring.interface_argv(e6b_operation, **keywords))

    def test_indices_and_inputs_are_refused_before_anything_runs(self):
        for operation, arguments in (("bin", dict(index=24, build="b", out="o")), ("refit", dict(index=36, bin_dir="d", build="b", out="o")),
                                     ("slices", dict(index=10, scores="s")), ("score", dict(index=17, collection="c", scores="s")),
                                     ("collect", dict(index=-1, attempts="a", out="c")), ("pool", dict(index=0))):
            with self.assertRaises(tasks.TaskError):
                tasks.t07_call(operation, block=11, **arguments)
        code, text = run_main(["t07-bin", "--block", 11, "--index", 0, "--out", "/nonexistent-merge"])
        self.assertEqual(code, 2)
        self.assertIn("RESULT t07-bin rejected", text)                    # no build given: refused before any draw
        self.assertEqual(layout.RESULT_LINES["t07_evaluation_scoring.py"], scoring.RESULT_LINE)

    def test_the_refit_takes_the_counted_bin_attempt(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            base = Path(folder)
            first, second = base / "bin-a", base / "bin-b"
            for d in (first, second):
                d.mkdir()
            (base / "attempts.tsv").write_text(f"T07 bin 4\t901_4\t{first}\nT07 bin 4\t902_4\t{second}\n")
            states = {"901_4": ("FAILED", 2, "00:00:05"), "902_4": ("COMPLETED", 0, "00:03:00")}   # a NO-DRAW refusal, then the counted run
            seen = {}
            original = tasks.t07_run
            tasks.t07_run = lambda operation, **a: seen.update(a, operation=operation) or 0
            try:
                code = tasks.t07_refit(11, 13, base / "out", "b", base / "attempts.tsv", state_of=states.get)
            finally:
                tasks.t07_run = original
            self.assertEqual((code, seen["operation"], seen["index"], Path(seen["bin_dir"])), (0, "refit", 13, second))

    def test_collect_score_slices_and_summary_end_to_end_on_hand_made_state(self):
        """No attempt of any bin: E6b's collection marks all 24 missing; each scoring writes v4 10's records and its marker; the slices read the
        markers; the summary needs every marker and both checks tasks, else it is incomplete; with all, the outcome is the core's (a fail)."""
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            base = Path(folder)
            neg_line, neg = fake_single(base, "T07 negative cases", "t07-negative-cases", {"t07-negative-cases.log": "RESULT t07-negative-cases ok\n"})
            chk_line, chk = fake_single(base, "T07 checks", "t07-checks", {"t07-checks.log": "RESULT t07-checks ok\n"})
            (base / "attempts.tsv").write_text(neg_line + "\n" + chk_line + "\n")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(tasks.t07_collect(11, base / "attempts.tsv", base / "collection", state_of=DONE), 0)
            document = json.loads((base / "collection" / "collection.json").read_text())
            self.assertTrue(document["finished"])
            self.assertEqual(len(document["bins"]), 24)
            self.assertTrue(all(entry["status"] == "missing" for entry in document["bins"].values()))
            scores = base / "scores"

            def summary():
                with redirect_stdout(io.StringIO()) as printed:
                    code = tasks.t07_summary(11, scores, base / "collection" / "collection.json", base / "summary", attempts_file=base / "attempts.tsv",
                                             state_of=DONE)
                return code, printed.getvalue()
            with redirect_stdout(io.StringIO()):
                self.assertEqual(tasks.t07_score(11, 0, base / "collection" / "collection.json", scores / "bin-0", "rr"), 0)
            self.assertEqual(len(scoring.read_records(scores / scoring.records_name(7001, 11, 0))), 57)
            self.assertTrue((scores / "bin-0" / "scored.json").exists())
            code, text = summary()
            self.assertEqual(code, 3)
            self.assertIn("SUMMARY INCOMPLETE T07 block 11: the scoring of T07 bin 1 left no scored.json", text)
            with redirect_stdout(io.StringIO()):
                for index in range(1, 24):
                    self.assertEqual(tasks.t07_score(11, index, base / "collection" / "collection.json", scores / f"bin-{index}", "rr"), 0)
                code, text = run_main(["t07-slices", "--block", 11, "--index", 0, "--scores", scores, "--out", base / "slices-task"])
            self.assertEqual(code, 0, text)
            code, text = summary()
            self.assertEqual(code, 3)
            self.assertIn("the slices task 1 left no scored.json", text)
            with redirect_stdout(io.StringIO()):
                for index in range(1, 10):
                    self.assertEqual(tasks.t07_slices(11, index, scores, base / f"slices-{index}"), 0)
            code, text = summary()
            self.assertEqual(code, 3)
            self.assertIn("negative-checks.json", text)                  # the negative cases task left no checks: incomplete, never a fail
            (neg / "negative-checks.json").write_text(json.dumps([{"name": n, "kind": "negative", "result": "pass", "stop": False,
                                                                   "recorded_unsupported_gap": False} for n in scoring.NEGATIVE_CHECK_NAMES]))
            (chk / "deterministic-checks.json").write_text(json.dumps([{"name": n, "kind": k, "result": "pass", "stop": False,
                                                                        "recorded_unsupported_gap": False} for n, k, _ in scoring.T07_CHECKS]))
            code, text = summary()
            self.assertEqual(code, 0, text)
            self.assertIn("SUMMARY T07 attempt 1: workflow fail, R11 state failed; 1260 records", text)   # every bin missing on the recipe side
            (scores / "bin-3" / "scored.json").write_text(json.dumps({"collection_sha256": "0" * 64}))
            code, text = summary()
            self.assertEqual(code, 3)
            self.assertIn("T07 bin 3 is not of this collection", text)


class T07Markers(unittest.TestCase):
    """E6 merge review, the coordinator's rulings: a slice marker pins its member bins' .slices.npz files and the summary checks them against the
    current bin markers (M1); a bin refused at scoring leaves a refused marker and the summary stays incomplete naming the bin and the refusal
    (M3); the collection reads the refit pieces by their count (M6) and removes an earlier collection.json first (M7)."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(dir=TEMPORARY_ROOT, prefix="t07-markers-"))
        self.addCleanup(__import__("shutil").rmtree, self.base, True)
        self.collection = self.base / "collection" / "collection.json"
        self.scores = self.base / "scores"

    def whole_state(self):
        """Every T07 harness task ended: the collection (no recipe attempt: every bin missing), the 24 scorings, the 10 slices, both checks."""
        neg_line, neg = fake_single(self.base, "T07 negative cases", "t07-negative-cases", {"t07-negative-cases.log": "RESULT t07-negative-cases ok\n"})
        chk_line, chk = fake_single(self.base, "T07 checks", "t07-checks", {"t07-checks.log": "RESULT t07-checks ok\n"})
        (neg / "negative-checks.json").write_text(json.dumps([{"name": n, "kind": "negative", "result": "pass", "stop": False,
                                                               "recorded_unsupported_gap": False} for n in scoring.NEGATIVE_CHECK_NAMES]))
        (chk / "deterministic-checks.json").write_text(json.dumps([{"name": n, "kind": k, "result": "pass", "stop": False,
                                                                    "recorded_unsupported_gap": False} for n, k, _ in scoring.T07_CHECKS]))
        (self.base / "attempts.tsv").write_text(neg_line + "\n" + chk_line + "\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tasks.t07_collect(11, self.base / "attempts.tsv", self.collection.parent, state_of=DONE), 0)
            for index in range(24):
                self.assertEqual(tasks.t07_score(11, index, self.collection, self.scores / f"bin-{index}", "rr"), 0)
            for index in range(10):
                self.assertEqual(tasks.t07_slices(11, index, self.scores, self.base / f"slices-{index}"), 0)

    def summary(self):
        with redirect_stdout(io.StringIO()) as printed:
            code = tasks.t07_summary(11, self.scores, self.collection, self.base / "summary", attempts_file=self.base / "attempts.tsv", state_of=DONE)
        return code, printed.getvalue()

    def test_m1_a_slice_marker_pins_its_bins_slice_files(self):
        self.whole_state()
        self.assertEqual(self.summary()[0], 0)
        marker = json.loads((self.scores / "slices-0" / "scored.json").read_text())
        self.assertEqual(marker["bin_slices"]["3"], json.loads((self.scores / "bin-3" / "scored.json").read_text())["slices_sha256"])
        # bin 3 rescored after the slices ran (a new slice file and its own new marker): the slices read the old file, so they are stale
        slices = self.scores / scoring.slices_name(7001, 11, 3)
        scoring.write_slices(slices, scoring.bin_identity(7001, 11, 3), None, "", "missing", "rescored after the slices ran")
        bin_marker = self.scores / "bin-3" / "scored.json"
        doc = json.loads(bin_marker.read_text())
        doc["slices_sha256"] = sha(slices)
        bin_marker.write_text(json.dumps(doc, sort_keys=True) + "\n")
        code, text = self.summary()
        self.assertEqual(code, 3)
        self.assertIn("the slices task 0 read another .slices.npz of T07 bin 3", text)

    def test_m3_a_bin_refused_at_scoring_has_a_refused_marker_and_the_summary_names_it(self):
        self.whole_state()
        original = tasks.t07_run

        def refusing(operation, **a):   # E6b's score-bin on files it refuses: v4 10's records and the slices file, then exit 2
            if operation != "score" or a["index"] != 5:
                return original(operation, **a)
            identity = scoring.bin_identity(7001, 11, 5)
            reason = "the bin's files are refused: the product is of another bin"
            scoring.write_records(Path(a["scores"]) / scoring.records_name(7001, 11, 5),
                                  [core.missing_output(g, identity, s, reason) for g, s in scoring.bin_gates(7001)])
            scoring.write_slices(Path(a["scores"]) / scoring.slices_name(7001, 11, 5), identity, None, "", "missing", reason)
            print(f"RESULT t07-scoring score-bin rejected: {reason}")
            return 2
        tasks.t07_run = refusing
        try:
            with redirect_stdout(io.StringIO()):
                code = tasks.t07_score(11, 5, self.collection, self.scores / "bin-5", "rr")
        finally:
            tasks.t07_run = original
        self.assertEqual(code, 2)                                        # the task itself: rejected
        marker = json.loads((self.scores / "bin-5" / "scored.json").read_text())
        self.assertTrue(marker["refused"])
        self.assertIn("the product is of another bin", marker["reason"])
        code, text = self.summary()
        self.assertEqual(code, 3)                                        # never a pass, never silently a fail: the coordinator's
        self.assertIn("SUMMARY INCOMPLETE T07 block 11: T07 bin 5 was refused at scoring", text)
        self.assertIn("the product is of another bin", text)
        self.assertNotIn("SUMMARY T07 attempt", text)
        code, text = run_main(["t07-slices", "--block", 11, "--index", 0, "--scores", self.scores, "--out", self.base / "slices-again"])
        self.assertEqual(code, 3)
        self.assertIn("T07 bin 5 was refused at scoring", text)

    def test_m6_the_collection_reads_the_refit_pieces_by_their_count(self):
        original = (tasks.T07_REFIT_PIECES, tasks.t07_run)
        seen = {}

        def collect(operation, **a):
            seen[a["index"]] = json.loads(Path(a["attempts"]).read_text())
            Path(a["out"]).write_text(json.dumps({"status": "missing", "reason": "hand-made"}))
            return 0
        folder = self.base / "refit-2"
        folder.mkdir()
        (self.base / "attempts.tsv").write_text(f"T07 refit 2\t901_2\t{folder}\n")
        tasks.T07_REFIT_PIECES = tuple(layout.split(tasks.EVENTS, 6000))   # 2 pieces: refit index 2 s + p
        tasks.t07_run = collect
        try:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(tasks.t07_collect(11, self.base / "attempts.tsv", self.collection.parent, state_of=DONE), 0)
        finally:
            tasks.T07_REFIT_PIECES, tasks.t07_run = original
        self.assertEqual(seen[1]["refit"]["0"][0][1], str(folder))        # stratum 1, piece 0 is refit 2 with two pieces (3 s + p would read 3)
        self.assertEqual(seen[0]["refit"]["6000"], [])

    def test_m7_a_collection_rerun_removes_the_earlier_collection_first(self):
        original = tasks.t07_run

        def collect(operation, **a):
            if a["index"] == 5 and failing:
                return 2
            Path(a["out"]).write_text(json.dumps({"status": "missing", "reason": "hand-made"}))
            return 0
        (self.base / "attempts.tsv").write_text("")
        tasks.t07_run = collect
        try:
            failing = False
            with redirect_stdout(io.StringIO()):
                self.assertEqual(tasks.t07_collect(11, self.base / "attempts.tsv", self.collection.parent, state_of=DONE), 0)
            self.assertTrue(self.collection.exists())
            failing = True
            with redirect_stdout(io.StringIO()):
                self.assertEqual(tasks.t07_collect(11, self.base / "attempts.tsv", self.collection.parent, state_of=DONE), 2)
        finally:
            tasks.t07_run = original
        self.assertFalse(self.collection.exists())                       # no earlier collection.json beside rewritten bin documents


class TimedOutIsIncomplete(unittest.TestCase):
    """Integration fix round: a script that outlives its task's deadline is stopped and its task is incomplete (exit 3, RESULT incomplete),
    never failed and never ok; sacct is asked with a short timeout and a bounded retry, and no answer is incomplete."""

    def tearDown(self):
        layout.reset_task()

    def test_a_script_past_the_deadline_is_stopped_and_incomplete(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            script = Path(folder) / "t07_fake_rate.py"
            script.write_text("import time\nprint('started', flush=True)\ntime.sleep(60)\nprint('RESULT ok: never')\n")
            layout.start_task("t08-sample", now=__import__("time").monotonic() - 1800)   # the deadline has passed
            started = __import__("time").monotonic()
            with self.assertRaises(tasks.Incomplete) as caught:
                tasks.run_script(script, ["run"], Path(folder) / "run.log")
            self.assertLess(__import__("time").monotonic() - started, 30)
            self.assertIn("timed out", str(caught.exception))
            self.assertIn("started", (Path(folder) / "run.log").read_text())          # what it printed is kept

    def test_the_runner_reads_a_timeout_as_incomplete(self):
        original = tasks.t08_sample

        def timing_out(*arguments, **keywords):
            raise tasks.Incomplete("calo_cluster.py ['reconstruct'] timed out after 1680 s (the task's deadline)")
        tasks.t08_sample = timing_out
        try:
            code, text = run_main(["t08-sample", "--block", 11, "--index", 0, "--out", "/nonexistent-timeout"])
        finally:
            tasks.t08_sample = original
        self.assertEqual(code, 3)
        self.assertIn("RESULT t08-sample incomplete", text)

    def test_the_task_command_line_sets_the_deadline_from_its_operation(self):
        layout.reset_task()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tasks.task_main(["names", "--block", "11"]), 0)
        self.assertLessEqual(layout.subprocess_timeout(), layout.TASK_LIMIT_SECONDS["names"] - layout.RECORD_MARGIN_SECONDS)
        layout.reset_task()
        with redirect_stdout(io.StringIO()):
            tasks.main(["names", "--block", "11"])                                     # in-process: no deadline of its own
        self.assertGreater(layout.subprocess_timeout(), layout.TASK_LIMIT_SECONDS["names"])

    def fake_sacct(self, folder, body):
        sacct = Path(folder) / "sacct"
        sacct.write_text("#!/bin/sh\n" + body)
        sacct.chmod(0o755)
        return {**os.environ, "PATH": f"{folder}:{os.environ.get('PATH', '/usr/bin:/bin')}"}

    def test_sacct_has_a_short_timeout_and_a_bounded_retry(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            environment = self.fake_sacct(folder, "sleep 30\n")
            original = os.environ.copy()
            os.environ.update(environment)
            try:
                started = __import__("time").monotonic()
                with self.assertRaises(tasks.Incomplete) as caught:
                    tasks.sacct_state("901_3", timeout=0.5, attempts=2, pause=0)
                self.assertLess(__import__("time").monotonic() - started, 10)
                self.assertIn("sacct did not answer", str(caught.exception))
                counter = Path(folder) / "n"
                (Path(folder) / "sacct").write_text(f"#!/bin/sh\nif [ -e {shlex.quote(str(counter))} ]; then echo '901_3|COMPLETED|0:0|00:02:00'; else touch {shlex.quote(str(counter))}; sleep 30; fi\n")
                self.assertEqual(tasks.sacct_state("901_3", timeout=0.5, attempts=2, pause=0), ("COMPLETED", 0, "00:02:00"))
            finally:
                os.environ.clear()
                os.environ.update(original)
        self.assertEqual((tasks.SACCT_TIMEOUT_SECONDS, tasks.SACCT_ATTEMPTS), (30, 3))


class SacctNoAnswerIsIncomplete(unittest.TestCase):
    """Integration review C1 and M2: an error answer of sacct (a non-zero exit, an error on stderr) or no row for the job is no answer, the same
    as a timeout: retried within the bound, then Incomplete; a state is never guessed. The retries and the pause keep to the task's deadline."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(dir=TEMPORARY_ROOT, prefix="sacct-"))
        self.addCleanup(__import__("shutil").rmtree, self.folder, True)
        self.addCleanup(layout.reset_task)
        self.original = os.environ.copy()
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.original)))
        os.environ["PATH"] = f"{self.folder}:{os.environ.get('PATH', '/usr/bin:/bin')}"
        self.calls = self.folder / "calls"

    def sacct(self, body):
        script = self.folder / "sacct"
        script.write_text(f"#!/bin/sh\necho x >> {shlex.quote(str(self.calls))}\n" + body)
        script.chmod(0o755)

    def count(self):
        return len(self.calls.read_text().splitlines()) if self.calls.exists() else 0

    def test_an_error_exit_is_no_answer(self):
        self.sacct("echo 'sacct: error: Problem talking to the database: Connection refused' >&2\nexit 1\n")
        with self.assertRaises(tasks.Incomplete) as caught:
            tasks.sacct_state("901_3", timeout=5, attempts=3, pause=0)
        self.assertIn("sacct did not answer", str(caught.exception))
        self.assertEqual(self.count(), 3)

    def test_an_error_on_stderr_is_no_answer(self):
        self.sacct("echo '901_3|COMPLETED|0:0|00:02:00'\necho 'sacct: error: slurmdbd: partial answer' >&2\n")
        with self.assertRaises(tasks.Incomplete):
            tasks.sacct_state("901_3", timeout=5, attempts=2, pause=0)

    def test_no_row_for_the_job_is_no_answer(self):
        self.sacct("exit 0\n")
        with self.assertRaises(tasks.Incomplete):
            tasks.sacct_state("901_3", timeout=5, attempts=3, pause=0)
        self.sacct("echo '901_4|COMPLETED|0:0|00:02:00'\n")                          # another task's row only
        with self.assertRaises(tasks.Incomplete):
            tasks.sacct_state("901_3", timeout=5, attempts=2, pause=0)

    def test_a_row_on_the_third_attempt_is_read(self):
        self.sacct(f"[ \"$(wc -l < {shlex.quote(str(self.calls))})\" -ge 3 ] && echo '901_3|COMPLETED|0:0|00:02:00'\nexit 0\n")
        self.assertEqual(tasks.sacct_state("901_3", timeout=5, attempts=3, pause=0), ("COMPLETED", 0, "00:02:00"))
        self.assertEqual(self.count(), 3)

    def test_past_the_deadline_sacct_is_not_asked(self):
        self.sacct("echo '901_3|COMPLETED|0:0|00:02:00'\n")
        layout.start_task("collect", now=__import__("time").monotonic() - 3600)
        with self.assertRaises(tasks.Incomplete) as caught:
            tasks.sacct_state("901_3", timeout=5, attempts=3, pause=10)
        self.assertIn("deadline", str(caught.exception))
        self.assertEqual(self.count(), 0)


class DeadlineStops(unittest.TestCase):
    """Integration review M1 and M4: a task stopped at its deadline writes the milestone stopped-at-deadline (its attempt is classified with
    that reason); the T08 and T09 collection removes an earlier collection.json first, as T07's."""

    def tearDown(self):
        layout.reset_task()

    def test_a_stop_at_the_deadline_is_a_milestone_of_the_task(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            original = tasks.t08_sample

            def stopped(*arguments, **keywords):
                raise tasks.DeadlineReached("calo_cluster.py ['reconstruct'] timed out after 1680 s (the task's deadline)")
            tasks.t08_sample = stopped
            try:
                code, text = run_main(["t08-sample", "--block", 11, "--index", 0, "--out", folder])
            finally:
                tasks.t08_sample = original
            self.assertEqual(code, 3)
            self.assertIn("RESULT t08-sample incomplete", text)
            self.assertIn(layout.STOPPED_AT_DEADLINE, tasks.Milestones(folder).names())

    def test_the_collection_removes_an_earlier_collection_first(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            out = Path(folder) / "current"
            out.mkdir()
            (out / "collection.json").write_text('{"finished": true}\n')
            name = next(n for kind, _, _, n in tasks.task_names() if kind == "t08-sample")
            (Path(folder) / "attempts.tsv").write_text(f"{name}\t901_0\t{folder}\n")   # an attempt, so sacct is asked and does not answer

            def no_answer(job):
                raise tasks.Incomplete("sacct did not answer")
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(tasks.Incomplete):
                    tasks.collect("T08", 11, Path(folder) / "attempts.tsv", out, state_of=no_answer)
            self.assertFalse((out / "collection.json").exists())


class ExitThreeIsIncomplete(unittest.TestCase):
    """E6 merge review (nit): a script that ends with its own result line and exit 3 (core/status.py: incomplete) makes its task incomplete
    (exit 3, rerun), never a failed step."""

    def test_run_script_reads_exit_3_as_a_crash_of_the_task(self):
        with tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT) as folder:
            script = Path(folder) / "t07_fake_rate.py"
            script.write_text("import sys\nprint('RESULT failed: a dependency is missing')\nsys.exit(3)\n")
            with self.assertRaises(tasks.ScriptCrash):
                tasks.run_script(script, ["run"], Path(folder) / "run.log", ok=(0, 1))
            script.write_text("import sys\nprint('RESULT failed: U_dev > C')\nsys.exit(1)\n")
            self.assertEqual(tasks.run_script(script, ["run"], Path(folder) / "run.log", ok=(0, 1))[0], 1)


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
