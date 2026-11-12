"""D4 stage E6a: the evaluation's parallel layout (d4-e6a-brief.md, item 2), on hand-made outputs. No evaluation job is written or run here.

The layout is tests/adapters/t04_evaluation_layout.py, scoring side. Sections cited are of t04-values-v4.md (Freeze A). Every test here runs on
hand-made files and records; none draws an event of any fixture. The range-split equality on generated block-1 events (T07, T08, T09) is the job
of record's (jobs/d4-e6a), through the same functions.

Expectations, fixed before the first run (d4-e6a-report.md, "Predictions"): the completeness check refuses a gap, an overlap, a duplicate and a
missing range; a range file of T08 and T09 holds the full stratum file's events byte for byte, and the merged range products equal the full
product line for line once each event line is renumbered; T07's data and truth bodies concatenate to the full file's.

Run from the plugin root: python -m unittest tests.adapters.test_t04_evaluation_layout -v
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.adapters import t04_evaluation_core as core  # noqa: E402
from tests.adapters import t04_evaluation_layout as layout  # noqa: E402


def ranges(*pairs):
    return [layout.EventRange(first, count) for first, count in pairs]


class RangeSplit(unittest.TestCase):
    """One task per (fixture, stratum, event range); every range draws exactly the events a single full draw would."""

    def test_split_covers_every_event_once(self):
        found = layout.split(12000, 500)
        self.assertEqual(len(found), 24)
        self.assertEqual(found[0], layout.EventRange(0, 500))
        self.assertEqual(found[-1], layout.EventRange(11500, 500))
        layout.check_ranges(found, 12000)
        uneven = layout.split(1000, 300)
        self.assertEqual([(r.first, r.count) for r in uneven], [(0, 300), (300, 300), (600, 300), (900, 100)])
        self.assertEqual(layout.split(12000, 12000), [layout.EventRange(0, 12000)])

    def test_split_refuses_nonsense(self):
        for total, size in ((0, 10), (10, 0), (-5, 2), (10, -1)):
            with self.subTest(total=total, size=size):
                with self.assertRaises(layout.LayoutError):
                    layout.split(total, size)

    def test_completeness_refuses_a_gap(self):
        with self.assertRaisesRegex(layout.LayoutError, "gap"):
            layout.check_ranges(ranges((0, 100), (150, 50)), 200)

    def test_completeness_refuses_an_overlap(self):
        with self.assertRaisesRegex(layout.LayoutError, "overlap"):
            layout.check_ranges(ranges((0, 120), (100, 100)), 200)

    def test_completeness_refuses_a_duplicate(self):
        with self.assertRaisesRegex(layout.LayoutError, "duplicate"):
            layout.check_ranges(ranges((0, 100), (100, 100), (100, 100)), 200)

    def test_completeness_refuses_a_missing_range(self):
        with self.assertRaisesRegex(layout.LayoutError, "missing"):
            layout.check_ranges(ranges((0, 100)), 200)
        with self.assertRaisesRegex(layout.LayoutError, "missing"):
            layout.check_ranges(ranges((100, 100)), 200)
        with self.assertRaisesRegex(layout.LayoutError, "missing"):
            layout.check_ranges([], 200)

    def test_completeness_refuses_events_outside_the_bin(self):
        with self.assertRaisesRegex(layout.LayoutError, "outside"):
            layout.check_ranges(ranges((0, 100), (100, 120)), 200)
        with self.assertRaises(layout.LayoutError):
            layout.check_ranges(ranges((0, 0), (0, 200)), 200)

    def test_top_up_never(self):
        """Section 3.4: a missing range is a failed task, not a smaller bin."""
        with self.assertRaisesRegex(layout.LayoutError, "missing"):
            layout.check_ranges(layout.split(12000, 500)[:-1], 12000)
        with self.assertRaises(layout.LayoutError):
            layout.check_ranges(layout.split(11500, 500), 12000)


def readout_bytes(events: int, channels: int = 5, saturation=None):
    sys.path.insert(0, str(ROOT / "adapters" / "photon-likelihood" / "assets"))
    from light_recipe import readout
    i = numpy.arange(events * channels).reshape(events, channels)
    state = numpy.where(i % 3 == 0, readout.LIVE_HIT, readout.LIVE_UNHIT).astype(numpy.int8)
    state[:, -1] = readout.DEAD
    charge = numpy.where(state == readout.LIVE_HIT, 1.0 + (i % 7) * 0.25, 0.0)
    charge[state == readout.DEAD] = numpy.nan
    time = numpy.where(state == readout.LIVE_HIT, 10.0 + i * 0.125, numpy.nan)
    saturated = numpy.zeros_like(state, dtype=bool)
    return readout.readout_bytes(state, charge, time, saturated, 0.5, saturation)


def cells_bytes(events: int, nx: int = 3, ny: int = 4):
    sys.path.insert(0, str(ROOT / "adapters" / "calo-cluster" / "assets"))
    from calo_recipe import cell_input
    i = numpy.arange(events * nx * ny).reshape(events, nx, ny)
    live = (i % 11) != 5
    raw = numpy.where(live, 100.0 + (i % 13) * 0.5, numpy.nan)
    return cell_input.cells_bytes(raw, live, numpy.zeros_like(live))


class RangeFiles(unittest.TestCase):
    """Choice (b): one generation task per stratum writes the whole stratum with the unchanged fixture tool; the harness cuts range files."""

    def test_t09_readout_range_is_the_full_files_events(self):
        full = readout_bytes(10)
        piece = layout.t09_readout_range(full, 3, 4)
        sys.path.insert(0, str(ROOT / "adapters" / "photon-likelihood" / "assets"))
        from light_recipe import readout
        a, b = readout.read_bytes(full), readout.read_bytes(piece)
        self.assertEqual(b.events, 4)
        for name in ("state", "charge", "time", "saturated"):
            self.assertEqual(getattr(b, name).tobytes(), getattr(a, name)[3:7].tobytes())
        self.assertEqual({k: v for k, v in b.header.items() if k != "events"}, {k: v for k, v in a.header.items() if k != "events"})
        self.assertEqual(layout.t09_readout_range(full, 0, 10), full)  # the whole range is the file itself, byte for byte

    def test_t08_cells_range_is_the_full_files_events(self):
        full = cells_bytes(9)
        piece = layout.t08_cells_range(full, 2, 5)
        sys.path.insert(0, str(ROOT / "adapters" / "calo-cluster" / "assets"))
        from calo_recipe import cell_input
        a, b = cell_input.read_cells(full), cell_input.read_cells(piece)
        self.assertEqual(b.raw.shape[0], 5)
        self.assertEqual(b.raw.tobytes(), a.raw[2:7].tobytes())
        self.assertEqual(b.live.tobytes(), a.live[2:7].tobytes())
        self.assertEqual(layout.t08_cells_range(full, 0, 9), full)

    def test_a_range_outside_the_file_is_refused(self):
        with self.assertRaises(layout.LayoutError):
            layout.t09_readout_range(readout_bytes(4), 2, 3)
        with self.assertRaises(layout.LayoutError):
            layout.t08_cells_range(cells_bytes(4), 0, 0)

    def test_t09_truth_range(self):
        with tempfile.TemporaryDirectory() as folder:
            full = Path(folder) / "full.truth.npz"
            header = {"format": "t09-truth/1", "role": "truth", "generator": "g", "fixture": "main", "block": 1, "stratum": 0, "events": 6,
                      "readout_sha256": "f" * 64}
            with open(full, "wb") as stream:
                numpy.savez(stream, header=numpy.array(json.dumps(header, sort_keys=True)), dead_channels=numpy.zeros(0, numpy.int64),
                            n_exp=numpy.arange(6.0), vertex=numpy.arange(18.0).reshape(6, 3), t0=numpy.arange(6.0) * 2)
            piece = Path(folder) / "piece.truth.npz"
            layout.t09_truth_range(full, 2, 3, "a" * 64, piece)
            with numpy.load(piece) as npz:
                self.assertEqual(npz.files, ["header", "dead_channels", "n_exp", "vertex", "t0"])
                got = json.loads(str(npz["header"]))
                self.assertEqual((got["events"], got["readout_sha256"]), (3, "a" * 64))
                self.assertEqual(npz["vertex"].tolist(), numpy.arange(18.0).reshape(6, 3)[2:5].tolist())
                self.assertEqual(npz["dead_channels"].size, 0)


def jsonl(events, dumps, offset=0, fmt="demo/1"):
    lines = [dumps({"format": fmt, "events": len(events)})]
    lines += [dumps({"event": i, **doc}) for i, doc in enumerate(events)]
    lines.append(dumps({"end": fmt, "events": len(events)}))
    return "\n".join(lines) + "\n"


COMPACT = (lambda doc: json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False))
SPACED = (lambda doc: json.dumps(doc, sort_keys=True, allow_nan=False))


EXPECTED = core.BinIdentity("T09", 9001, 11, 3)


def product(first, count, *, drop_last=False):
    """A hand-made JSON Lines product of `count` events (as a range task writes it: event lines numbered from 0)."""
    events = [{"x": float(first + i)} for i in range(count)]
    text = jsonl(events, SPACED)
    if drop_last:
        lines = text.split("\n")
        text = "\n".join(lines[:-3] + lines[-2:])   # one event line gone, the end line kept: a truncated product
    return text.encode()


def record(first, count, *, events=None, stratum=3, block=11, fixture=9001, attempt="7600000_3", content=None, stratum_sha256="5" * 64):
    content = product(first, count) if content is None else content
    return layout.RangeRecord(workflow="T09", fixture_id=fixture, block=block, stratum=stratum, first=first, count=count,
                              events=tuple(range(first, first + count)) if events is None else tuple(events),
                              product_sha256=layout.sha256_bytes(content), stratum_sha256=stratum_sha256, input_sha256="6" * 64, attempt=attempt)


def products_of(*pairs):
    return {first: product(first, count) for first, count in pairs}


class BinCompleteness(unittest.TestCase):
    """The scoring step runs only on the complete bin: every range present once, no gap, no overlap, every event index 0 to N - 1; each product
    read and tied to its record and the expected bin (fix round 1, I7)."""

    def check(self, records, pairs, total=1000, expected=EXPECTED, products=None):
        return layout.check_bin(records, expected, total, products_of(*pairs) if products is None else products)

    def test_a_complete_bin(self):
        pairs = ((0, 400), (400, 400), (800, 200))
        self.assertEqual(self.check([record(f, c) for f, c in pairs], pairs), list(range(1000)))

    def test_every_listed_event_must_be_its_ranges(self):
        bad = [record(0, 400), record(400, 600, events=list(range(400, 999)) + [998])]
        with self.assertRaisesRegex(layout.LayoutError, "events"):
            self.check(bad, ((0, 400), (400, 600)))

    def test_one_expected_bin_only(self):
        with self.assertRaisesRegex(layout.LayoutError, "one bin"):
            self.check([record(0, 500), record(500, 500, stratum=4)], ((0, 500), (500, 500)))
        with self.assertRaisesRegex(layout.LayoutError, "one bin"):
            self.check([record(0, 500, block=12), record(500, 500, block=12)], ((0, 500), (500, 500)))   # a complete block-12 set at block 11
        with self.assertRaisesRegex(layout.LayoutError, "stratum file"):
            self.check([record(0, 500), record(500, 500, stratum_sha256="7" * 64)], ((0, 500), (500, 500)))

    def test_a_truncated_or_mismatched_product_is_refused(self):
        short = product(500, 500, drop_last=True)
        with self.assertRaisesRegex(layout.LayoutError, "disagree|holds"):
            self.check([record(0, 500), record(500, 500, content=short)], (), products={0: product(0, 500), 500: short})
        with self.assertRaisesRegex(layout.LayoutError, "SHA-256"):
            self.check([record(0, 500), record(500, 500)], (), products={0: product(0, 500), 500: product(500, 499) + b""})
        with self.assertRaisesRegex(layout.LayoutError, "missing"):
            self.check([record(0, 500), record(500, 500)], (), products={0: product(0, 500)})
        with self.assertRaises(layout.LayoutError):
            layout.check_bin([record(0, 1000)], EXPECTED, 1000, None)
        honest_short = product(500, 499)
        with self.assertRaisesRegex(layout.LayoutError, "holds 499"):
            self.check([record(0, 500), record(500, 500, content=honest_short)], (), products={0: product(0, 500), 500: honest_short})

    def test_gap_overlap_duplicate_missing_through_records(self):
        cases = {"gap": ([record(0, 400), record(500, 500)], ((0, 400), (500, 500))),
                 "overlap": ([record(0, 600), record(500, 500)], ((0, 600), (500, 500))),
                 "duplicate": ([record(0, 500), record(500, 500), record(500, 500, attempt="7600001_3")], ((0, 500), (500, 500))),
                 "missing": ([record(0, 500)], ((0, 500),))}
        for word, (records, pairs) in cases.items():
            with self.subTest(word=word):
                with self.assertRaisesRegex(layout.LayoutError, word):
                    self.check(records, pairs)

    def test_product_events_of_a_t07_record(self):
        text = "acts-tracking-finding-record/2\nevent 0 x\nevent 1 x\nend 2 0 0\n"
        self.assertEqual(layout.product_events(text.encode(), "t07-record"), 2)
        with self.assertRaises(layout.LayoutError):
            layout.product_events(text.replace("end 2", "end 3").encode(), "t07-record")
        with self.assertRaises(layout.LayoutError):
            layout.product_events(b"acts-tracking-finding-record/2\nevent 0 x\n", "t07-record")

    def test_the_record_round_trips(self):
        one = record(0, 3)
        self.assertEqual(layout.RangeRecord.from_json(one.to_json()), one)
        with self.assertRaises(layout.LayoutError):
            layout.RangeRecord.from_json(json.dumps({**json.loads(one.to_json()), "extra": 1}))


class Collection(unittest.TestCase):
    """Fix round 1, I3: the collection (afterany) selects attempts and checks every bin; a failed range gives section 10's "required output
    missing", never a smaller bin, and the workflow fails."""

    def setUp(self):
        self.spans = layout.split(1000, 500)
        self.products = products_of((0, 500), (500, 500))

    def test_a_complete_bin_after_a_no_draw_attempt(self):
        attempts = {self.spans[0]: [("NO-DRAW", None), ("NO-FAILURE", record(0, 500))], self.spans[1]: [("NO-FAILURE", record(500, 500))]}
        found = layout.collect_bin(EXPECTED, self.spans, attempts, self.products, total=1000)
        self.assertEqual((found.status, [r.first for r in found.records]), ("complete", [0, 500]))

    def test_a_failed_range_makes_the_bin_missing_and_the_workflow_fail(self):
        for tried in ([("NOT-REPEATABLE", None)], [("REPEATABLE", None), ("NO-FAILURE", record(500, 500))], []):
            with self.subTest(tried=tried):
                attempts = {self.spans[0]: [("NO-FAILURE", record(0, 500))], self.spans[1]: tried}
                found = layout.collect_bin(EXPECTED, self.spans, attempts, self.products, total=1000)
                self.assertEqual(found.status, "missing")
                self.assertIn("missing range", found.reason)
        missing = layout.missing_bin_records(EXPECTED, [("pull x location", "trimmed-centre"), ("tail", "rate")], found.reason)
        self.assertEqual([(m.result, m.required, m.attempt) for m in missing], [("inconclusive", True, 1)] * 2)
        self.assertTrue(all("required output missing" in m.reason for m in missing))
        records = [core.TestResult(gate="g", bin="b", statistic="rate", estimate=0.0, standard_error=None, lower=0.0, upper=0.001, limit=0.01,
                                   result="pass", step=3, attempt=1, confidence=0.95, replicates=None, required=True, reason="", readings={})] * 268 + missing
        self.assertEqual(core.workflow_outcome("T09", records, [], attempt=1, required_checks=()).r11_state, "failed")

    def test_a_truncated_product_makes_the_bin_missing(self):
        short = product(500, 500, drop_last=True)
        attempts = {self.spans[0]: [("NO-FAILURE", record(0, 500))], self.spans[1]: [("NO-FAILURE", record(500, 500, content=short))]}
        found = layout.collect_bin(EXPECTED, self.spans, attempts, {0: product(0, 500), 500: short}, total=1000)
        self.assertEqual(found.status, "missing")

    def test_the_plan_runs_the_collections_on_afterany(self):
        plan = layout.evaluation_plan(block=11)
        for workflow in ("T07", "T08", "T09"):
            collection = plan.by_name[f"{workflow} collection"]
            self.assertEqual(collection.dependency, "afterany")
            ranges_of = [t.name for t in plan.tasks if t.kind.startswith(workflow) and t.span is not None]
            self.assertTrue(set(ranges_of) <= set(collection.depends))
            self.assertEqual(plan.by_name[f"{workflow} summary"].dependency, "afterany")
            for task in plan.tasks:
                if task.kind == f"{workflow} scoring":
                    self.assertEqual(task.depends, (f"{workflow} collection",))


class AttemptClassification(unittest.TestCase):
    """The classification of earlier attempts, as the Freeze-B run's collection step (fbrun_tools.py classify): sacct and milestones only; and
    fix round 1, I4: fit-started counts as a draw."""

    def test_the_rows(self):
        rows = [
            (("COMPLETED", 0, "00:10:00", {"draws-started"}), "NO-FAILURE"),
            (("CANCELLED", 0, "00:00:00", None), "NEVER-RAN"),
            (("PENDING", 0, "00:00:00", None), "NEVER-RAN"),
            (("CANCELLED", 0, "00:00:00", set()), "NO-DRAW"),   # a milestones file exists: it started
            (("FAILED", 1, "00:05:00", {"draws-started", "first-reading"}), "NOT-REPEATABLE"),
            (("FAILED", 2, "00:00:10", set()), "NO-DRAW"),
            (("NODE_FAIL", 0, "00:05:00", {"draws-started"}), "REPEATABLE"),
            (("TIMEOUT", 0, "04:00:00", {"draws-started"}), "REPEATABLE-WITH-NEW-REQUEST"),
            (("OUT_OF_MEMORY", 0, "00:30:00", {"draws-started"}), "REPEATABLE-WITH-NEW-REQUEST"),
            (("FAILED", 3, "00:01:00", {"draws-started"}), "REPEATABLE"),
            (("CANCELLED by 123", 0, "00:03:00", {"draws-started"}), "NOT-REPEATABLE"),
            (("FAILED", 1, "00:03:00", {"draws-started"}), "NOT-REPEATABLE"),
        ]
        for arguments, expected in rows:
            with self.subTest(arguments=arguments):
                self.assertEqual(layout.classify_attempt(*arguments)[0], expected)

    def test_a_fit_only_task_that_started_its_fit_is_not_no_draw(self):
        for state, code, expected in (("TIMEOUT", 0, "REPEATABLE-WITH-NEW-REQUEST"), ("OUT_OF_MEMORY", 0, "REPEATABLE-WITH-NEW-REQUEST"),
                                      ("FAILED", 1, "NOT-REPEATABLE"), ("NODE_FAIL", 0, "REPEATABLE")):
            with self.subTest(state=state):
                verdict = layout.classify_attempt(state, code, "00:40:00", {"fit-started"})[0]
                self.assertEqual(verdict, expected)
                with self.assertRaises(layout.LayoutError):
                    layout.select_attempt([verdict, "NO-FAILURE"], block=11)
        self.assertEqual(layout.classify_attempt("TIMEOUT", 0, "00:40:00", set())[0], "NO-DRAW")

    def test_selection_at_evaluation_accepts_only_attempts_that_drew_nothing(self):
        self.assertEqual(layout.select_attempt(["NO-DRAW", "NEVER-RAN", "NO-FAILURE"], block=11), 2)
        for earlier in ("REPEATABLE", "REPEATABLE-WITH-NEW-REQUEST", "NOT-REPEATABLE", "NO-FAILURE"):
            with self.subTest(earlier=earlier):
                with self.assertRaises(layout.LayoutError):
                    layout.select_attempt([earlier, "NO-FAILURE"], block=12)
        with self.assertRaises(layout.LayoutError):
            layout.select_attempt(["NO-FAILURE", "REPEATABLE"], block=11)

    def test_selection_on_a_freeze_b_block_follows_u_b12_and_evaluation_is_never_looser(self):
        self.assertEqual(layout.select_attempt(["REPEATABLE", "NO-FAILURE"], block=2), 1)
        self.assertEqual(layout.select_attempt(["REPEATABLE-WITH-NEW-REQUEST", "NO-FAILURE"], block=2), 1)
        with self.assertRaises(layout.LayoutError):
            layout.select_attempt(["NOT-REPEATABLE", "NO-FAILURE"], block=2)
        verdicts = ("NO-DRAW", "NEVER-RAN", "REPEATABLE", "REPEATABLE-WITH-NEW-REQUEST", "NOT-REPEATABLE", "NO-FAILURE")
        for earlier in verdicts:
            def accepted(block):
                try:
                    layout.select_attempt([earlier, "NO-FAILURE"], block=block)
                    return True
                except layout.LayoutError:
                    return False
            with self.subTest(earlier=earlier):
                self.assertLessEqual(accepted(11), accepted(2))


class ScriptRuns(unittest.TestCase):
    """Fix round 2: a script's own result line decides, never its exit code alone; a traceback or a missing result line is a crash. And the
    interpreter flags keep a script's folder on sys.path (job 7590464: -I dropped it, and t07_fake_rate.py's sibling import failed)."""

    def run_child(self, flags, folder, script):
        import subprocess
        done = subprocess.run([sys.executable, *flags, str(Path(folder) / script)], capture_output=True, text=True, timeout=60, env={"PATH": "/usr/bin:/bin"})
        return done.returncode, done.stdout + done.stderr

    def test_a_module_not_found_child_is_a_crash_not_a_negative(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "sibling_e6a.py").write_text("VALUE = 1\n")
            (Path(folder) / "uses_sibling.py").write_text("import sys\nimport sibling_e6a\nprint('RESULT refused: a negative reading')\nsys.exit(1)\n")
            code, run_text = self.run_child(("-I", "-B"), folder, "uses_sibling.py")
            self.assertIn("ModuleNotFoundError", run_text)
            self.assertEqual(code, 1)                                    # the exit code alone reads like a negative
            self.assertEqual(layout.classify_script_run(code, run_text, layout.RESULT_LINES["t07_fake_rate.py run"])[0], "crashed")
            code, run_text = self.run_child(layout.SCRIPT_FLAGS, folder, "uses_sibling.py")
            self.assertEqual(layout.classify_script_run(code, run_text, layout.RESULT_LINES["t07_fake_rate.py run"]), ("negative", "RESULT refused: a negative reading"))

    def test_the_states(self):
        pattern = layout.RESULT_LINES["t07_fake_rate.py run"]
        self.assertEqual(layout.classify_script_run(0, "RUN x\nRESULT ok: 12 bins\n", pattern), ("ok", "RESULT ok: 12 bins"))
        self.assertEqual(layout.classify_script_run(1, "RESULT refused: U_dev > C\n", pattern)[0], "negative")
        self.assertEqual(layout.classify_script_run(0, "RUN x\n", pattern)[0], "crashed")                      # exit 0 without its line
        self.assertEqual(layout.classify_script_run(1, "", pattern)[0], "crashed")
        self.assertEqual(layout.classify_script_run(139, "RESULT ok: x\n", pattern)[0], "crashed")             # a signal
        self.assertEqual(layout.classify_script_run(0, "RESULT ok: x\nTraceback (most recent call last):\n", pattern)[0], "crashed")
        self.assertEqual(layout.SCRIPT_STATES, ("ok", "negative", "incomplete", "crashed"))

    def test_exit_3_with_its_own_line_is_incomplete_never_negative(self):
        """E6 merge review (nit): core/status.py's exit 3 (a missing dependency or an incomplete run) is never read as a negative reading."""
        pattern = layout.RESULT_LINES["t07_evaluation_scoring.py"]
        line = "RESULT t07-scoring summary incomplete: required checks absent"
        self.assertEqual(layout.classify_script_run(3, line + "\n", pattern), ("incomplete", line))
        self.assertEqual(layout.classify_script_run(2, "RESULT t07-scoring summary rejected: x\n", pattern)[0], "negative")

    def test_the_result_lines_match_the_scripts_own(self):
        examples = {"t07_fake_rate.py run": "RESULT ok: 12 clean bins produced; no rate", "t07_fake_rate.py check": "OK every noise bin within C",
                    "t08_fixture_files.py": '{"block": 1, "events": 600, "status": "ok"}', "calo_cluster.py": '{"chain": [], "status": "ok"}',
                    "t09_fixture_files.py": '{"files": {}, "status": "ok"}', "photon_likelihood.py": '{"exit_code": 0, "status": "ok"}',
                    "t09_truth_start.py": 'RESULT {"exit_code": 0, "status": "ok"}', "fbrun_tools.py classify": "CLASSIFY job 1 NO-DRAW: x",
                    "fbrun_tools.py t07-comparator": "RESULT comparator ok: 1 of 1 noise bins",
                    "t09_negative_checks.py relabel-dead": '{"format": "t09-dead-as-unhit/1", "status": "ok"}',
                    "t08_scenarios.py accounting": "GATE main-E3-iso selection-and-accounting PASS: 0 of 3000 events with a defect",
                    "t08_scenarios.py reference-selection": "GATE reference-selection PASS: the reference clusterer's W, SN, Q, TC, TS and ITERS",
                    "t08_cai.py payloads": '{"files": {}, "status": "ok"}',
                    "t08_cai.py fixed-membership": "CAI-T08-1 main-E3-iso-multiply RESULT PASS",
                    "t08_cai.py rereco": "CAI-T08-2 main-E3-iso-multiply RESULT RECORDED",
                    "t09_fixed_points.py": "GATE per-channel sum at the fixed points (v4 9.3, the T09 stop): points 50, failures 0: PASS",
                    "check_generators.py": "RESULT PASS",
                    "t07_evaluation_scoring.py": "RESULT t07-scoring score-bin ok: T07 fixture 7001 block 11 stratum 0: 57 records written",
                    "t04_evaluation_tasks.py": "RESULT score ok"}
        self.assertEqual(set(examples), set(layout.RESULT_LINES))
        for name, line in examples.items():
            with self.subTest(name=name):
                self.assertEqual(layout.classify_script_run(0, line + "\n", layout.RESULT_LINES[name]), ("ok", line))
        self.assertNotIn("-I", layout.SCRIPT_FLAGS)


class MergedProducts(unittest.TestCase):
    """The merged range products equal one full task's products event for event, byte-equal once the event line is renumbered."""

    def setUp(self):
        self.docs = [{"x": 0.1 * i, "fit": {"ok": i % 2 == 0, "v": [1.0 / (i + 1), 2.5]}} for i in range(9)]

    def test_equal_products_merge(self):
        for dumps in (COMPACT, SPACED):
            full = jsonl(self.docs, dumps)
            parts = [(0, jsonl(self.docs[0:4], dumps)), (4, jsonl(self.docs[4:5], dumps)), (5, jsonl(self.docs[5:9], dumps))]
            self.assertEqual(layout.compare_jsonl_ranges(full, parts, dumps), [])

    def test_a_changed_value_a_missing_or_a_reordered_event_is_found(self):
        full = jsonl(self.docs, COMPACT)
        changed = [dict(d) for d in self.docs[4:9]]
        changed[2] = {**changed[2], "x": changed[2]["x"] + 1e-15}
        found = layout.compare_jsonl_ranges(full, [(0, jsonl(self.docs[0:4], COMPACT)), (4, jsonl(changed, COMPACT))], COMPACT)
        self.assertTrue(any("event 6" in line for line in found), found)
        found = layout.compare_jsonl_ranges(full, [(0, jsonl(self.docs[0:4], COMPACT)), (5, jsonl(self.docs[5:9], COMPACT))], COMPACT)
        self.assertTrue(found)
        swapped = self.docs[4:9]
        swapped = [swapped[1], swapped[0]] + swapped[2:]
        found = layout.compare_jsonl_ranges(full, [(0, jsonl(self.docs[0:4], COMPACT)), (4, jsonl(swapped, COMPACT))], COMPACT)
        self.assertTrue(found)

    def test_a_line_that_does_not_round_trip_is_found(self):
        full = jsonl(self.docs, COMPACT).replace('"x":0.0', '"x":0.00', 1)
        found = layout.compare_jsonl_ranges(full, [(0, jsonl(self.docs, COMPACT))], COMPACT)
        self.assertTrue(any("does not round-trip" in line for line in found), found)


def t07_data(events):
    sys.path.insert(0, str(ROOT / "adapters" / "acts-tracking" / "assets" / "fixture_tools"))
    import t07_fixture_files as files
    return files.encode_data_file(0.02, events)


T07_RECORD_HEAD = "acts-tracking-finding-record/2\nrecipe reco.track.acts-ckf-planar/1\nproduct_id demo\n"


def t07_record(event_lines):
    body = "".join(event_lines)
    return T07_RECORD_HEAD + body + "end 0 0 0\n"


def t07_event(g, first=0, candidates=1, vertex=True):
    """Event g's lines as a run starting at event `first` writes them: ordinals and keys local (g - first), values those of event g."""
    o = g - first
    lines = [f"event {o} 10 1 1 0 0 1 0 0 0 {candidates} {candidates} none\n"]
    lines += [f"candidate event-{o}-candidate-{c} {o} 1-2-3 selected none 0 8 0 1.5 0.3{g} 2.5 16 1,2,3,4,5,6,7,{g}\n" for c in range(candidates)]
    lines.append(f"vertexing {o} ok {candidates} 0 {1 if vertex else 0}\n")
    if vertex:
        lines.append(f"vertex event-{o}-vertex-0 {o} -99.9 0.0{g} 24.4 1 0 0 1 0 1 3.5 2 {candidates}\n")
        lines += [f"vertex-track event-{o}-vertex-0 event-{o}-candidate-{c} 0.98 0.5 0.3\n" for c in range(candidates)]
    return "".join(lines)


def t07_run_record(first, count):
    return t07_record([t07_event(g, first, candidates=1 + g % 2, vertex=g != 2) for g in range(first, first + count)])


def t07_product(first, count):
    head = "acts-tracking-product/1\nproduct_id demo\n"
    events = range(first, first + count)
    tracks = "".join(f"track event-{g - first}-candidate-0 {g - first} fitted none 8 0 0 6.{g} 16 0.3{g}\n" for g in events)
    states = "".join(f"state event-{g - first}-candidate-0 {s} {s + 1} measurement {40 + s} -3.{g} 12.0\n" for g in events for s in range(2))
    params = "".join(f"parameters event-{g - first}-candidate-0 0 predicted -3.9{g} 12.08\n" for g in events)
    return head + tracks + states + params + f"end {count} {2 * count} {count}\n"


class T07Ranges(unittest.TestCase):
    """T07's generator takes --first-event: each range is its own draw; bodies, records and products merge to the full ones."""

    def test_data_bodies_concatenate(self):
        events = [[(1, 0.5, -0.5), (2, 1.0, 2.0)], [(3, 0.25, 0.75)], [], [(1, -1.0, 4.0)]]
        full = t07_data(events)
        parts = [(0, t07_data(events[:1])), (1, t07_data(events[1:3])), (3, t07_data(events[3:]))]
        self.assertEqual(layout.compare_t07_bodies(full, parts, "data"), [])
        self.assertTrue(layout.compare_t07_bodies(full, [(0, t07_data(events[:2])), (2, t07_data(events[3:]))], "data"))
        self.assertTrue(layout.compare_t07_bodies(full, [(0, t07_data(events[:1])), (1, t07_data([events[2], events[1]])), (3, t07_data(events[3:]))], "data"))

    def test_records_renumber_and_merge(self):
        full = t07_run_record(0, 5)
        self.assertEqual(layout.compare_t07_records(full, [(0, t07_run_record(0, 2)), (2, t07_run_record(2, 3))]), [])
        self.assertEqual(layout.compare_t07_records(full, [(0, t07_run_record(0, 1)), (1, t07_run_record(1, 1)), (2, t07_run_record(2, 3))]), [])

    def test_a_record_difference_is_found(self):
        full = t07_run_record(0, 4)
        bad = t07_run_record(2, 2).replace("1.5 0.33", "1.5 0.39")
        found = layout.compare_t07_records(full, [(0, t07_run_record(0, 2)), (2, bad)])
        self.assertTrue(any("event 3" in line for line in found), found)
        self.assertTrue(layout.compare_t07_records(full, [(0, t07_run_record(0, 3))]))
        self.assertTrue(layout.compare_t07_records(full, [(0, t07_run_record(0, 2)), (2, t07_run_record(1, 2))]))

    def test_products_renumber_and_merge(self):
        full = t07_product(0, 5)
        self.assertEqual(layout.compare_t07_products(full, [(0, t07_product(0, 3)), (3, t07_product(3, 2))]), [])
        self.assertTrue(layout.compare_t07_products(full, [(0, t07_product(0, 3)), (3, t07_product(3, 1))]))
        self.assertTrue(layout.compare_t07_products(full, [(0, t07_product(0, 3)), (3, t07_product(3, 2).replace("6.4 16", "6.7 16"))]))
        self.assertTrue(layout.compare_t07_products(full, [(0, t07_product(0, 3)), (3, t07_product(2, 2))]))

    def test_the_class_of_a_difference(self):
        """Fix round 1, I6: two full runs first, then the ranges; a difference is nondeterminism, position dependence or a renumbering defect."""
        full = t07_run_record(0, 4)
        good = [(0, t07_run_record(0, 2)), (2, t07_run_record(2, 2))]
        self.assertEqual(layout.classify_t07_ranges(full, full, good)[0], "equal")
        self.assertEqual(layout.classify_t07_ranges(full, full.replace("1.5 0.32", "1.5 0.38"), good)[0], "nondeterminism")
        valued = [(0, t07_run_record(0, 2)), (2, t07_run_record(2, 2).replace("1.5 0.33", "1.5 0.39"))]
        self.assertEqual(layout.classify_t07_ranges(full, full, valued)[0], "position dependence")
        misnumbered = [(0, t07_run_record(0, 2)), (2, t07_run_record(2, 2).replace("event-1-candidate-0 1 ", "event-1-candidate-0 0 "))]
        self.assertEqual(layout.classify_t07_ranges(full, full, misnumbered)[0], "renumbering defect")


def t07_truth(indices, tracks_of=lambda g: 1 + g % 2):
    """A hand-made t07 truth file: events in the given order of event indices, each with tracks_of(g) tracks whose values follow g."""
    sys.path.insert(0, str(ROOT / "adapters" / "acts-tracking" / "assets" / "fixture_tools"))
    import t07_truth_files as truth
    header = numpy.zeros(1, dtype=truth.TRUTH_HEADER)
    header["magic"], header["role"], header["event_count"] = truth.TRUTH_MAGIC, truth.TRUTH_ROLE, len(indices)
    parts = [header.tobytes()]
    for g in indices:
        event = numpy.zeros(1, dtype=truth.TRUTH_EVENT)
        event["event_index"], event["track_count"], event["vertex_count"] = g, tracks_of(g), 1
        event["event_digest"] = bytes([g % 256]) * 32
        vertex = numpy.zeros(1, dtype=truth.VERTEX)
        vertex["z_mm"] = -100.0 + g
        track = numpy.zeros(tracks_of(g), dtype=truth.TRACK)
        track["momentum_gev"] = 1.0 + g
        parts += [event.tobytes(), vertex.tobytes(), track.tobytes()]
    return b"".join(parts)


def t07_files(indices, offset_of=None):
    """Data, truth, record and product of a hand-made T07 run whose file holds the event indices in the given order (the generator's own order)."""
    events = [[(1, 0.5 + g, -0.5), (2, 1.0, 2.0 + g)] for g in indices]
    record = t07_record([t07_event(g, g - q, candidates=1 + g % 2, vertex=g != 2) for q, g in enumerate(indices)])
    product = "acts-tracking-product/1\nproduct_id demo\n"
    product += "".join(f"track event-{q}-candidate-0 {q} fitted none 8 0 0 6.{g} 16 0.3{g}\n" for q, g in enumerate(indices))
    product += "".join(f"state event-{q}-candidate-0 {s} {s + 1} measurement {40 + s} -3.{g} 12.0\n" for q, g in enumerate(indices) for s in range(2))
    product += "".join(f"parameters event-{q}-candidate-0 0 predicted -3.9{g} 12.08\n" for q, g in enumerate(indices))
    product += f"end {len(indices)} {2 * len(indices)} {len(indices)}\n"
    return {"t07data": t07_data(events), "t07truth": t07_truth(indices), "record": record.encode(), "product": product.encode()}


class T07RangesByIndex(unittest.TestCase):
    """Fix round 2: the T07 generator writes each file in an order of its own, so ranges are compared event for event by the truth's event
    index (job 7590464 read position against position and called it position dependence)."""

    def setUp(self):
        self.full = t07_files([3, 0, 5, 1, 4, 2])          # the full file's own order
        self.parts = [(0, t07_files([2, 0, 1])), (3, t07_files([5, 3, 4]))]

    def test_equal_by_index_although_the_orders_differ(self):
        self.assertEqual(layout.compare_t07_by_index(self.full, self.parts), [])
        self.assertTrue(layout.compare_t07_records(self.full["record"].decode(), [(f, p["record"].decode()) for f, p in self.parts]))  # by position: differ
        self.assertEqual(layout.classify_t07_by_index(self.full, self.full, self.parts)[0], "equal")
        self.assertEqual(layout.t07_event_indices(self.full["t07truth"]), [3, 0, 5, 1, 4, 2])

    def test_the_classes(self):
        again = dict(self.full, record=self.full["record"].replace(b"1.5 0.33", b"1.5 0.38"))
        self.assertEqual(layout.classify_t07_by_index(self.full, again, self.parts)[0], "nondeterminism")
        valued = [(0, self.parts[0][1]), (3, dict(self.parts[1][1], record=self.parts[1][1]["record"].replace(b"1.5 0.34", b"1.5 0.39")))]
        self.assertEqual(layout.classify_t07_by_index(self.full, self.full, valued)[0], "position dependence")
        drawn = [(0, self.parts[0][1]), (3, t07_files([5, 3, 6]))]
        self.assertEqual(layout.classify_t07_by_index(self.full, self.full, drawn)[0], "draw differs")
        misnumbered = [(0, self.parts[0][1]), (3, dict(self.parts[1][1], record=self.parts[1][1]["record"].replace(b"event-1-candidate-0 1 ", b"event-1-candidate-0 0 ")))]
        self.assertEqual(layout.classify_t07_by_index(self.full, self.full, misnumbered)[0], "renumbering defect")

    def test_a_missing_or_changed_event_is_found(self):
        self.assertTrue(layout.compare_t07_by_index(self.full, self.parts[:1]))
        changed = [(0, self.parts[0][1]), (3, dict(self.parts[1][1], product=self.parts[1][1]["product"].replace(b"6.4 16", b"6.7 16")))]
        self.assertTrue(any("product track" in d for d in layout.compare_t07_by_index(self.full, changed)))
        hits = dict(self.parts[1][1], t07data=t07_data([[(1, 0.5 + g, -0.5), (2, 1.0, 2.0 + g + (g == 4))] for g in (5, 3, 4)]))
        found = layout.compare_t07_by_index(self.full, [(0, self.parts[0][1]), (3, hits)])
        self.assertEqual([d for d in found if "data hits" in d], ["event index 4: data hits differ"])
        self.assertEqual(layout.classify_t07_by_index(self.full, self.full, [(0, self.parts[0][1]), (3, hits)])[0], "draw differs")


class PooledBins(unittest.TestCase):
    """E6c fix round 1 (with E6b's O5): a pool is complete only if every member bin is."""

    def test_pool_status(self):
        pool = core.PooledIdentity("T09", 9001, 11, 0, (3, 4, 5), "test pool")
        self.assertEqual(layout.pool_status(pool, {3: ("complete", ""), 4: ("complete", ""), 5: ("complete", "")}), ("complete", ""))
        status, reason = layout.pool_status(pool, {3: ("complete", ""), 4: ("missing", "a range crashed"), 5: ("complete", "")})
        self.assertEqual(status, "missing")
        self.assertIn("member stratum 4 is incomplete: a range crashed", reason)
        with self.assertRaises(layout.LayoutError):
            layout.pool_status(pool, {3: ("complete", ""), 4: ("complete", "")})


class EvaluationPlan(unittest.TestCase):
    """The evaluation on blocks 11 and 12 as arrays of short tasks, its task count, CPU-hours and wall by the closed form."""

    def test_the_t09_scoring_budget_is_the_conservative_estimate(self):
        """E6 merge review M4 (the coordinator's ruling): until the heaviest T09 scoring (main stratum 10) is measured at 12,000 events, T09's
        budget is E6c's estimate from the Freeze-B readings, about 1,208 s ((131 + 97) x 4 + 74 x 4), not the 600-event measurement scaled x 22;
        the total stays within the user's 200 CPU-hours."""
        self.assertGreaterEqual(layout.SCORING_SECONDS["T09"], 1208)
        self.assertLessEqual(layout.evaluation_plan(block=11).cpu_hours(), 200)

    def test_the_plan(self):
        plan = layout.evaluation_plan(block=11)
        counts = plan.task_counts()
        self.assertEqual(counts["T07 bin"], 24)
        self.assertEqual(counts["T08 sample"], 15)
        self.assertEqual(counts["T09 generation"], 15)
        self.assertEqual(counts["T09 range"], 15 * 24)
        self.assertEqual((counts["T07 collection"], counts["T07 scoring"]), (1, 24))
        for task in plan.tasks:
            self.assertEqual(task.cpu_class, "AMD EPYC 9645 96-Core Processor")   # U-W7 (review M9)
            if task.kind in ("T07 bin", "T07 refit"):
                self.assertEqual((task.cpus, task.memory_mb), (2, 7900))            # fix round 1, I5: as the Freeze-B run
        for task in plan.tasks:
            with self.subTest(task=task.name):
                self.assertLess(task.wall_seconds, 3600 * (0.6 if "scoring" not in task.kind else 1.0))  # recipe tasks well under 1 h; scoring under 1 h
        for kind in ("T09 fixed points", "T08 checks", "T07 checks", "T07 negative cases"):
            self.assertEqual(counts[kind], 1)
        self.assertEqual((counts["T07 slices"], counts["T09 scoring"], counts["T09 pool scoring"]), (10, 15, 1))   # E6c fix round 1 (M4; slices, E5)
        self.assertEqual(set(plan.by_name["T09 summary"].depends) >= {"T09 score pool", "T09 fixed points"}, True)
        self.assertIn("T08 checks", plan.by_name["T08 summary"].depends)
        for key, ranges_of_bin in plan.ranges_by_bin().items():
            with self.subTest(bin=key):
                layout.check_ranges(ranges_of_bin, 12000)

    def test_blocks(self):
        layout.evaluation_plan(block=12)
        for block in (1, 2, 6, 13):
            with self.assertRaises(layout.LayoutError):
                layout.evaluation_plan(block=block)

    def test_cost_closed_form(self):
        tasks = [layout.Task("g", "gen", 100, 0.5, 10, ()), layout.Task("a", "fit", 100, 2.0, 10, ("g",)), layout.Task("b", "fit", 50, 2.0, 10, ("g",)),
                 layout.Task("s", "score", 0, 0.0, 30, ("a", "b"))]
        plan = layout.Plan(tasks)
        self.assertEqual(plan.cpu_hours(), (60 + 210 + 110 + 30) / 3600)
        self.assertEqual(plan.longest_chain_seconds(), 60 + 210 + 30)
        self.assertEqual(plan.overhead_hours(), (10 + 10 + 10 + 30) / 3600)
        with self.assertRaises(layout.LayoutError):
            layout.Plan([layout.Task("a", "fit", 1, 1.0, 1, ("missing",))]).longest_chain_seconds()

    def test_the_memory_record_holds_job_7591439s_measurement(self):
        self.assertEqual(layout.T07_REFIT_PEAK_MEMORY, {3000: 8012452, 12000: 31841752})

    def test_the_refit_range_follows_the_memory_record(self):
        """Fix round 1, I5: 8.0 GB per 3,000 events (Freeze-B run, linear) cannot fit 12,000 events in 2 x 7,900 MB: the refit is split."""
        self.assertEqual(layout.t07_refit_range(), 4000)
        self.assertEqual(layout.t07_refit_range({3000: 8012452, 12000: 9000000}), 12000)
        self.assertEqual(layout.t07_refit_range({3000: 8012452, 12000: 20000000}), 6000)   # 12.0 GB interpolated at 6,000
        plan = layout.evaluation_plan(block=11)
        self.assertEqual(plan.task_counts()["T07 refit"], 12 * 3)
        self.assertIn("split by range", plan.notes[0])
        whole = layout.evaluation_plan(block=11, refit_measured={3000: 8012452, 12000: 9000000})
        self.assertEqual(whole.task_counts()["T07 refit"], 12)
        with self.assertRaises(layout.LayoutError):
            layout.t07_refit_range({1000: 40000000})

    def test_splitting_costs_the_overhead_only(self):
        """The model's arithmetic only (review M12: linear by construction, not evidence)."""
        whole = layout.evaluation_plan(block=11, t09_range=12000)
        split = layout.evaluation_plan(block=11)
        extra = split.cpu_hours() - whole.cpu_hours()
        self.assertAlmostEqual(extra, split.overhead_hours() - whole.overhead_hours(), places=9)
        self.assertLess(split.longest_chain_seconds(), whole.longest_chain_seconds())


if __name__ == "__main__":
    unittest.main()
