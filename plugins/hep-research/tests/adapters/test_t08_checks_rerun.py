"""The T08 checks deviation during attempt 1 on block 11 (job 7613402 read as CRASHED; the user: "Fix and rerun T08 checks").

(1) The task runner's result line for `t08_cai.py rereco` (layout.RESULT_LINES) matches the tool's own verdict line: t08_cai.rereco's last line,
"CAI-T08-2 <label> RECORD recorded without a numeric assertion (R37)", produced here by the real function on hand-made products (the recipe-side
tool itself is unchanged: it is in calo-cluster's Freeze B adapter manifest).
(2) The user's ruling (2026-11-13, "Count it: block 1/6 only"): a check task that draws only from blocks 1 and 6 (the T08 checks, the T07 checks
and the T07 negative cases) may be repeated after a harness crash (exit 3 or infrastructure: REPEATABLE), and the latest attempt is counted,
said as "repeated check task (block 1/6 only; user 2026-11-13)". A failed check (NOT-REPEATABLE) still stands; a failed generator check still
goes to the user; the T09 fixed points are not named by the ruling and keep the rule; every recipe task of blocks 11 and 12 keeps v4 3.4's rule:
no repeat after a draw.

Run from the plugin root: python -m unittest tests.adapters.test_t08_checks_rerun -v
"""
from __future__ import annotations

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

from tests.adapters import t04_evaluation_layout as layout  # noqa: E402
from tests.adapters import t04_evaluation_tasks as tasks  # noqa: E402
from tests.adapters import test_calo_cai as calo  # noqa: E402

TEMPORARY_ROOT = os.environ.get("TMPDIR") or None


CAPTURED = ROOT / "tests" / "adapters" / "data" / "t08-cai-rereco-7613402-main-E3-iso-multiply.log"
CAPTURED_SHA256 = "bfb734acc1a8b9fea3ebde7ee0d093a90a07044aa6371a73c2c3eea065c70505"   # block-11 job 7613402, main-E3-iso/cai2-multiply.log


class RerecoResultLine(unittest.TestCase):
    def test_the_verdict_line_job_7613402_printed_is_the_result_line(self):
        """The audit (e6-result-lines-audit.md, finding 1): the real output of t08_cai.py rereco on block-1 check events, captured from job
        7613402, which the old pattern read as a crash."""
        import hashlib
        raw = CAPTURED.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), CAPTURED_SHA256)
        text = raw.decode("utf-8")
        verdict = "CAI-T08-2 main-E3-iso-multiply RECORD recorded without a numeric assertion (R37)"
        self.assertEqual(text.splitlines()[-1], verdict)
        self.assertEqual(layout.classify_script_run(0, text, layout.RESULT_LINES["t08_cai.py rereco"]), ("ok", verdict))

    def rereco_text(self):
        ped_b = calo.pedestal_bytes()
        nominal_b = calo.nominal_gain_bytes("multiply", ped=ped_b)
        derived_b = calo.gain_payload.derive(nominal_b, {calo.flat(27, 11): calo.FACTOR}, "hand-made change")
        grids = [calo.image([calo.LONE] + calo.PAIR)]
        nominal = calo.product.read_text(calo.make_product(grids, ped_b, nominal_b))
        changed = calo.product.read_text(calo.make_product(grids, ped_b, derived_b))
        lines, _ = calo.t08_cai.rereco(nominal, changed, calo.gain_payload.read(nominal_b), calo.gain_payload.read(derived_b), calo.CFG,
                                       "main-E3-iso-multiply")
        return "\n".join(lines) + "\n"

    def test_the_tools_own_verdict_line_is_the_result_line(self):
        text = self.rereco_text()
        verdict = "CAI-T08-2 main-E3-iso-multiply RECORD recorded without a numeric assertion (R37)"
        self.assertEqual(text.splitlines()[-1], verdict)                                # the tool's last line, as printed by t08_cai.py:448-458
        self.assertEqual(layout.classify_script_run(0, text, layout.RESULT_LINES["t08_cai.py rereco"]), ("ok", verdict))

    def test_a_reading_line_alone_is_still_no_result_line(self):
        text = "\n".join(line for line in self.rereco_text().splitlines() if " RECORD recorded without" not in line) + "\n"
        self.assertEqual(layout.classify_script_run(0, text, layout.RESULT_LINES["t08_cai.py rereco"])[0], "crashed")


class SingleCheckTaskRerun(unittest.TestCase):
    """counted_single (t04_evaluation_tasks) over the attempts of one check task on block 11."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(dir=TEMPORARY_ROOT, prefix="t08-rerun-"))
        self.addCleanup(__import__("shutil").rmtree, self.base, True)

    def attempt(self, job, marks):
        folder = self.base / job
        folder.mkdir()
        (folder / "milestones.txt").write_text("".join(f"{m} 2026-11-13T00:00:00Z\n" for m in marks))
        return job, folder

    def test_a_crashed_check_task_may_precede_its_counted_rerun(self):
        crashed, rerun = self.attempt("7613402", ["draws-started", "fit-started"]), self.attempt("7699999", ["draws-started", "fit-started"])
        states = {"7613402": ("FAILED", 3, "00:20:00"), "7699999": ("COMPLETED", 0, "00:20:00")}
        self.assertEqual(layout.classify_attempt(*states["7613402"], ["draws-started", "fit-started"])[0], "REPEATABLE")
        folder = tasks.counted_single({"T08 checks": [crashed, rerun]}, "T08 checks", 11, states.get)
        self.assertEqual(folder, rerun[1])

    def test_a_failed_check_still_stands(self):
        failed, rerun = self.attempt("7613402", ["draws-started", "fit-started"]), self.attempt("7699999", ["draws-started"])
        states = {"7613402": ("FAILED", 1, "00:20:00"), "7699999": ("COMPLETED", 0, "00:20:00")}     # exit 1: NOT-REPEATABLE
        with self.assertRaises(tasks.Incomplete):
            tasks.counted_single({"T08 checks": [failed, rerun]}, "T08 checks", 11, states.get)

    def test_a_recipe_task_of_block_11_keeps_no_repeat_after_a_draw(self):
        crashed, rerun = self.attempt("8001_3", ["draws-started"]), self.attempt("8002_3", ["draws-started"])
        states = {"8001_3": ("FAILED", 3, "00:20:00"), "8002_3": ("COMPLETED", 0, "00:20:00")}
        with self.assertRaises(layout.LayoutError):
            tasks.counted_folder([crashed, rerun], 11, states.get)
        with self.assertRaises(layout.LayoutError):
            layout.select_attempt(["REPEATABLE", "NO-FAILURE"], block=11)

    def test_the_repeat_is_said_in_the_classification_output(self):
        crashed, rerun = self.attempt("7613402", ["draws-started", "fit-started"]), self.attempt("7699999", ["draws-started", "fit-started"])
        states = {"7613402": ("FAILED", 3, "00:20:00"), "7699999": ("COMPLETED", 0, "00:20:00")}
        with redirect_stdout(io.StringIO()) as printed:
            tasks.counted_single({"T08 checks": [crashed, rerun]}, "T08 checks", 11, states.get)
        self.assertIn("CLASSIFY T08 checks attempt 0 (7613402): REPEATABLE, repeated check task (block 1/6 only; user 2026-11-13); "
                      "counted: attempt 1 (7699999)", printed.getvalue())

    def test_the_latest_of_several_repeats_is_counted(self):
        rows = [self.attempt(f"76134{i:02d}", ["draws-started"]) for i in range(3)]
        states = {"7613400": ("FAILED", 3, "00:05:00"), "7613401": ("NODE_FAIL", 0, "00:05:00"), "7613402": ("COMPLETED", 0, "00:20:00")}
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tasks.counted_single({"T07 checks": rows}, "T07 checks", 11, states.get), rows[2][1])

    def real_t07_attempt(self, job, operation, bad):
        """A T07 check task's folder with the milestones its real command writes (review I3: never hand-written): the checks task with each
        module's output given, or the negative-cases task with its kept-folder check replaced; bad: the checks crash (no unittest
        summary), the negative cases are refused (no kept folder, exit 2)."""
        import functools
        from tests.adapters import t07_evaluation_scoring as scoring
        folder = self.base / job
        with redirect_stdout(io.StringIO()):
            if operation == "checks-task":
                text = "Traceback (most recent call last):\nKilled\n" if bad else "Ran 1 test in 0.1s\n\nOK\n"
                original = scoring.checks_task
                scoring.checks_task = functools.partial(original, module_runner=lambda module: text)
                try:
                    code = scoring.main(["checks-task", "--block", "11", "--build", str(self.base / "build"), "--out", str(folder)])
                finally:
                    scoring.checks_task = original
            else:
                # review m3: the real negative_task in both cases (its own milestones); bad: no kept folder (refused, exit 2); good: the kept
                # folder's check, the finder, its record and v4 11's checks replaced by passing stand-ins (no build, no kept case file here)
                saved = {name: getattr(scoring, name) for name in ("check_negative_case_folder", "_run", "negative_case_checks")}
                saved_record = (scoring.finding_record.parse_record, scoring.finding_record.iter_seed_events)
                if bad:
                    scoring.check_negative_case_folder = lambda kept: saved["check_negative_case_folder"](self.base / "no-kept-folder")
                else:
                    def finder(command, log):
                        Path(command[command.index("--record-file") + 1]).write_text("stand-in\n")
                        return 0.0
                    scoring.check_negative_case_folder = lambda kept: {}
                    scoring._run = finder
                    scoring.negative_case_checks = lambda description, record, seeds: [
                        scoring.core.CheckResult(name, "negative", "pass") for name in scoring.NEGATIVE_CHECK_NAMES]
                    scoring.finding_record.parse_record = lambda text: {"header": {"data_sha256": scoring.NEGATIVE_CASE_SHA256,
                                                                                   "configuration_sha256": scoring.FREEZE_B_CONFIGURATION_SHA256}}
                    scoring.finding_record.iter_seed_events = lambda path: iter(())
                try:
                    code = tasks.main(["t07-negative-cases", "--block", "11", "--t07-build", str(self.base / "build"), "--out", str(folder)])
                finally:
                    for name, value in saved.items():
                        setattr(scoring, name, value)
                    scoring.finding_record.parse_record, scoring.finding_record.iter_seed_events = saved_record
        return (job, folder), code

    def test_the_t07_check_tasks_follow_the_same_rule(self):
        crashed, code = self.real_t07_attempt("checks-1", "checks-task", bad=True)
        rerun, _ = self.real_t07_attempt("checks-2", "checks-task", bad=False)
        self.assertEqual(code, 3)
        states = {"checks-1": ("FAILED", 3, "00:05:00"), "checks-2": ("COMPLETED", 0, "00:05:00")}
        self.assertEqual(layout.classify_attempt(*states["checks-1"], tasks.Milestones(crashed[1]).names())[0], "REPEATABLE")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tasks.counted_single({"T07 checks": [crashed, rerun]}, "T07 checks", 11, states.get), rerun[1])

    def test_a_refused_t07_negative_cases_task_stands(self):
        refused, code = self.real_t07_attempt("negative-1", "negative-task", bad=True)
        rerun, rerun_code = self.real_t07_attempt("negative-2", "negative-task", bad=False)
        self.assertEqual((code, rerun_code), (2, 0))
        self.assertEqual(tasks.Milestones(rerun[1]).names(), ["draws-started"])
        states = {"negative-1": ("FAILED", 2, "00:05:00"), "negative-2": ("COMPLETED", 0, "00:05:00")}
        self.assertEqual(layout.classify_attempt(*states["negative-1"], tasks.Milestones(refused[1]).names())[0], "NOT-REPEATABLE")
        with self.assertRaises(tasks.Incomplete):
            tasks.counted_single({"T07 negative cases": [refused, rerun]}, "T07 negative cases", 11, states.get)

    def test_the_fixed_points_are_not_named_by_the_ruling(self):
        crashed, rerun = self.attempt("7613448", ["draws-started"]), self.attempt("7613499", ["draws-started"])
        states = {"7613448": ("FAILED", 3, "00:05:00"), "7613499": ("COMPLETED", 0, "00:05:00")}
        with self.assertRaises(tasks.Incomplete):
            tasks.counted_single({"T09 fixed points": [crashed, rerun]}, "T09 fixed points", 11, states.get)
        self.assertEqual(tasks.REPEATABLE_CHECK_TASKS, ("T08 checks", "T07 checks", "T07 negative cases"))

    def test_the_t08_summary_reads_the_reruns_checks(self):
        crashed, rerun = self.attempt("7613402", ["draws-started", "fit-started"]), self.attempt("7699999", ["draws-started", "fit-started"])
        (crashed[1] / "t08-checks.log").write_text("Traceback (most recent call last):\nRESULT t08-checks crashed\n")
        (rerun[1] / "t08-checks.log").write_text("RESULT t08-checks ok\n")
        (rerun[1] / "checks.json").write_text(json.dumps([{"name": "CAI-T08-1", "kind": "cai", "result": "pass", "stop": False,
                                                           "recorded_unsupported_gap": False}]))
        states = {"7613402": ("FAILED", 3, "00:20:00"), "7699999": ("COMPLETED", 0, "00:20:00")}
        with redirect_stdout(io.StringIO()):
            found = tasks.extra_checks("T08", 11, {"T08 checks": [crashed, rerun]}, states.get)
        self.assertEqual([c.name for c in found], ["CAI-T08-1"])


if __name__ == "__main__":
    unittest.main()
