"""T12 stage 3: partitioning, recovery and boundaries (T12-10 to T12-12; plan v9.2 Sections 10.2 items 3-7 and 10.5; A11, A12).

Every expectation is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 3": M1, M2, P1-P8, K1-K8) before the harness
was written. The products are recorded examples of the T07 refit, T08 and T09 recipes, read by SHA-256 and cut into ranges by the
harness; the runner cases run skills/hep-computing/scripts/run_workflow.py unchanged. The comparison of separate range runs with full
runs on block-1 evidence is the job of record's (t12_partition.py recorded). No quality claim.

Run from the plugin root: python -m unittest tests.contracts.test_t12_partition -v
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.adapters import t04_evaluation_layout as layout  # noqa: E402
from tests.contracts import t12_partition as tp  # noqa: E402
from tests._platform import needs  # noqa: E402

R = layout.EventRange
EXAMPLES = ("t07-refit", "t08", "t09-multistart", "t09-topology")
PINNED = {
    "t07-refit": "a02d04b0b9d522eec9d6923fe79b406ab95477906eb3e3af23eac3231875495b",
    "t08": "1107dcec6509d236f13954439d650384f389bab0a32096df6bb82f76fd729cc8",
    "t09-multistart": "9d44ae712dc4b758cc9cbd4311c17fd1e31568cccd6377250c65aeaa60eee6b1",
    "t09-topology": "b42cb36ace58a8a31c24fb8b8af0d0502d188dd8fad91e8598ee5b2ef1133150",
}
IDENTITY = {"t07-refit": tp.Identity("T07", 7001, 1, 2), "t08": tp.Identity("T08", 8001, 1, 4),
            "t09-multistart": tp.Identity("T09", 9001, 1, 9), "t09-topology": tp.Identity("T09", 9001, 1, 9)}
EMPTY = {"success": [], "excluded": {}, "failure": [], "unconfirmed": []}


def kind(name):
    return tp.KIND_OF[name]


def keys_of_event(product, event):
    return {k for k, _ in product.objects.items() if tp.event_of(k) == event}


def bump_first_number(doc):
    """In place: the first number met depth-first through the keys in sorted order ('event' left out) is increased by 1; returns its path."""
    def walk(node, path):
        items = sorted(node.items()) if isinstance(node, dict) else list(enumerate(node)) if isinstance(node, list) else []
        for key, value in items:
            if path == () and key == "event":
                continue
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                node[key] = value + 1
                return path + (key,)
            found = walk(value, path + (key,))
            if found:
                return found
        return None
    return walk(doc, ())


def change_jsonl_event(content: bytes, local: int) -> bytes:
    lines = content.decode().split("\n")
    doc = json.loads(lines[1 + local])
    assert bump_first_number(doc)
    lines[1 + local] = json.dumps(doc)
    return "\n".join(lines).encode()


def change_t07_track(content: bytes, event: int) -> bytes:
    lines = content.decode().split("\n")
    for i, line in enumerate(lines):
        tokens = line.split(" ")
        if tokens[0] == "track" and tokens[1].startswith(f"event-{event}-"):
            tokens[-1] = repr(float(tokens[-1]) + 0.5)
            lines[i] = " ".join(tokens)
            return "\n".join(lines).encode()
    raise AssertionError("no track line of that event")


def complete_attempts(identity, kind_, parts, attempt="a1"):
    """One completed attempt per range of one event, with its record and product."""
    out = {}
    for first, content in parts:
        span = R(first, 1)
        out[span] = [tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), tp.make_record(identity, span, content, attempt), content,
                                attempt=attempt)]
    return out


class RecordedProducts(unittest.TestCase):
    """P1: the recorded examples, by SHA-256, and their keys."""

    def test_pinned_hashes(self):
        for name in EXAMPLES:
            self.assertEqual(tp.EXAMPLES[name][1], PINNED[name], name)
            self.assertEqual(tp.sha256_hex(tp.read_example(name)), PINNED[name], name)

    def test_a_changed_example_is_refused(self):
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "x.product"
            path.write_bytes(tp.read_example("t08") + b"\n")
            with self.assertRaises(tp.PartitionError):
                tp.frozen_bytes(path, PINNED["t08"])

    def test_t07_refit_keys(self):
        product = tp.read_product(tp.read_example("t07-refit"), "t07-refit")
        tracks = [k for k in product.objects if k[0] == "track"]
        self.assertEqual(len(tracks), 12)
        self.assertEqual(product.end, (12, 96, 288, 12, 384, 96, 12))
        self.assertEqual(len(product.objects), 12 + 96 + 288 + 12 + 384 + 96 + 12)
        self.assertEqual(product.events, {0, 1})
        self.assertEqual(product.header["recipe"], "reco.track.acts-kf-refit/1")

    def test_jsonl_keys(self):
        for name in ("t08", "t09-multistart", "t09-topology"):
            product = tp.read_product(tp.read_example(name), "jsonl")
            self.assertEqual(set(product.objects), {("event", 0), ("event", 1)}, name)
            self.assertEqual(product.count, 2, name)


class Merge(unittest.TestCase):
    """M2, P2-P5: merged ranges against the single pass, by object key."""

    def parts(self, name):
        content = tp.read_example(name)
        return content, tp.cut_ranges(content, kind(name), [R(0, 1), R(1, 1)])

    def read_parts(self, name, parts):
        return [tp.read_product(c, kind(name), first=f) for f, c in parts]

    def test_cut_ranges_merge_back_equal(self):
        for name in EXAMPLES:
            content, parts = self.parts(name)
            single = tp.read_product(content, kind(name))
            report = tp.merge_by_key(single, self.read_parts(name, parts))
            self.assertTrue(tp.merge_equal(report), (name, report))
            report = tp.merge_by_key(single, self.read_parts(name, parts[::-1]))
            self.assertTrue(tp.merge_equal(report), (name, report))
            self.assertEqual(set(report), {"omitted", "duplicated", "differing", "extra", "header"})

    def test_a_dropped_range_is_omitted_and_required_output_missing(self):
        for name in EXAMPLES:
            content, parts = self.parts(name)
            single = tp.read_product(content, kind(name))
            report = tp.merge_by_key(single, self.read_parts(name, parts[:1]))
            self.assertEqual(set(report["omitted"]), keys_of_event(single, 1), name)
            self.assertEqual([report[k] for k in ("duplicated", "differing", "extra", "header")], [[], [], [], []], name)
            attempts = complete_attempts(IDENTITY[name], kind(name), parts[:1])
            got = tp.collect_ranges(IDENTITY[name], kind(name), 2, [R(0, 1), R(1, 1)], attempts)
            self.assertEqual(got.status, "missing", name)
            self.assertEqual([span for span, _ in got.missing], [R(1, 1)], name)
            self.assertIn("missing range", got.missing[0][1])
            self.assertIn("required output missing", got.records[0])
            self.assertEqual(got.accounts, {**EMPTY, "success": [0], "failure": [1]}, name)
            self.assertEqual(tp.exposure(got.accounts, 2)["exposure"], 0.5)
            self.assertEqual(tp.check_accounts(got.accounts, 2), [])

    def test_a_duplicated_range_and_a_changed_value(self):
        for name in EXAMPLES:
            content, parts = self.parts(name)
            single = tp.read_product(content, kind(name))
            report = tp.merge_by_key(single, self.read_parts(name, [parts[0], parts[0], parts[1]]))
            self.assertEqual(set(report["duplicated"]), keys_of_event(single, 0), name)
            self.assertEqual([report[k] for k in ("omitted", "differing", "extra", "header")], [[], [], [], []], name)
            changed = change_t07_track(parts[1][1], 1) if name == "t07-refit" else change_jsonl_event(parts[1][1], 0)
            report = tp.merge_by_key(single, self.read_parts(name, [parts[0], (1, changed)]))
            self.assertEqual(len(report["differing"]), 1, (name, report["differing"]))
            key = report["differing"][0]
            self.assertEqual(tp.event_of(key), 1)
            if name == "t07-refit":
                self.assertEqual(key[0], "track")
            self.assertEqual([report[k] for k in ("omitted", "duplicated", "extra", "header")], [[], [], [], []], name)

    def test_header_rule(self):
        configuration = {"t07-refit": "start_prior", "t08": "configuration", "t09-multistart": "budget", "t09-topology": "budget"}
        for name in EXAMPLES:
            content, parts = self.parts(name)
            single = tp.read_product(content, kind(name))
            ranged = self.read_parts(name, parts)
            changed = tp.with_header(parts[1][1], kind(name), configuration[name], "changed")
            report = tp.merge_by_key(single, [ranged[0], tp.read_product(changed, kind(name), first=1)])
            self.assertEqual(len(report["header"]), 1, (name, report))
            self.assertIn(configuration[name], report["header"][0])
            identity_field = "product_id"
            changed = tp.with_header(parts[1][1], kind(name), identity_field, "another-range-id")
            report = tp.merge_by_key(single, [ranged[0], tp.read_product(changed, kind(name), first=1)])
            self.assertTrue(tp.merge_equal(report), (name, report))


class Truncation(unittest.TestCase):
    """P6: a truncated product, an object outside its range."""

    def test_truncated_products_are_refused(self):
        for name in EXAMPLES:
            content = tp.read_example(name)
            _, second = tp.cut_ranges(content, kind(name), [R(0, 1), R(1, 1)])
            lines = second[1].decode().split("\n")
            no_end = "\n".join(lines[:-2] + [""]).encode()
            with self.assertRaises(tp.PartitionError, msg=name):
                tp.read_product(no_end, kind(name), first=1)
            attempts = complete_attempts(IDENTITY[name], kind(name), [(0, tp.cut_ranges(content, kind(name), [R(0, 1)])[0][1])])
            attempts[R(1, 1)] = [tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",),
                                            tp.make_record(IDENTITY[name], R(1, 1), no_end), no_end, attempt="a1")]
            got = tp.collect_ranges(IDENTITY[name], kind(name), 2, [R(0, 1), R(1, 1)], attempts)
            self.assertEqual(got.status, "missing", name)
            self.assertEqual(got.accounts["failure"], [1], name)

    def test_a_t07_end_count_off_by_one_is_refused(self):
        content = tp.read_example("t07-refit")
        lines = content.decode().split("\n")
        tokens = lines[-2].split(" ")
        tokens[1] = str(int(tokens[1]) - 1)
        lines[-2] = " ".join(tokens)
        with self.assertRaises(tp.PartitionError):
            tp.read_product("\n".join(lines).encode(), "t07-refit")

    def test_a_jsonl_event_line_lost_before_the_end_line_is_refused(self):
        """Added after mutation-1 (mutant M7 survived): an event line lost while the end line stays is a truncation too."""
        for name in ("t08", "t09-multistart", "t09-topology"):
            lines = tp.read_example(name).decode().split("\n")
            del lines[2]
            with self.assertRaises(tp.PartitionError, msg=name):
                tp.read_product("\n".join(lines).encode(), "jsonl")

    def test_an_object_outside_its_range_is_refused(self):
        for name in EXAMPLES:
            content = tp.read_example(name)
            with self.assertRaises(tp.PartitionError, msg=name):
                tp.read_product(content, kind(name), first=0, count=1)


class EmptyCollection(unittest.TestCase):
    """P7: an event without objects inside a successful range is never a failure: a success for JSON Lines (an event line is written),
    unconfirmed for the T07 refit product (fix round 1, I2: a format gap)."""

    def test_t07_event_without_tracks(self):
        single = tp.without_event_objects(tp.read_example("t07-refit"), 1)
        product = tp.read_product(single, "t07-refit")
        self.assertEqual(product.events, {0})
        parts = tp.cut_ranges(single, "t07-refit", [R(0, 1), R(1, 1)])
        report = tp.merge_by_key(product, [tp.read_product(c, "t07-refit", first=f, count=1) for f, c in parts])
        self.assertTrue(tp.merge_equal(report), report)
        got = tp.collect_ranges(IDENTITY["t07-refit"], "t07-refit", 2, [R(0, 1), R(1, 1)],
                                complete_attempts(IDENTITY["t07-refit"], "t07-refit", parts))
        # Fix round 1, I2: the T07 refit format declares no events read, so the merge is equal but event 1 is not claimed read.
        self.assertEqual(got.status, "missing")
        self.assertEqual(got.accounts, {**EMPTY, "success": [0], "unconfirmed": [1]})

    def test_t08_event_without_objects(self):
        lines = tp.read_example("t08").decode().split("\n")
        doc = json.loads(lines[2])
        doc["objects"], doc["components"] = [], []
        lines[2] = json.dumps(doc)
        single = "\n".join(lines).encode()
        parts = tp.cut_ranges(single, "jsonl", [R(0, 1), R(1, 1)])
        report = tp.merge_by_key(tp.read_product(single, "jsonl"), [tp.read_product(c, "jsonl", first=f) for f, c in parts])
        self.assertTrue(tp.merge_equal(report), report)
        got = tp.collect_ranges(IDENTITY["t08"], "jsonl", 2, [R(0, 1), R(1, 1)], complete_attempts(IDENTITY["t08"], "jsonl", parts))
        self.assertEqual(got.status, "complete")
        self.assertEqual(got.accounts["success"], [0, 1])


class Accounts(unittest.TestCase):
    """P8: every source event in exactly one category; exclusions need reasons; gaps apart; exposure."""

    def test_check_accounts_finds_each_defect(self):
        good = {**EMPTY, "success": [0, 2], "excluded": {1: "boundary: insufficient neighbourhood"}, "failure": [3]}
        self.assertEqual(tp.check_accounts(good, 4), [])
        two = {**good, "unconfirmed": [2]}
        self.assertTrue(any("2" in d and "two" in d for d in tp.check_accounts(two, 4)), tp.check_accounts(two, 4))
        none = {**good, "failure": []}
        self.assertTrue(any("3" in d and "no category" in d for d in tp.check_accounts(none, 4)), tp.check_accounts(none, 4))
        reasonless = {**good, "excluded": {1: ""}}
        self.assertTrue(any("reason" in d for d in tp.check_accounts(reasonless, 4)), tp.check_accounts(reasonless, 4))
        outside = {**good, "failure": [3, 7]}
        self.assertTrue(any("7" in d and "outside" in d for d in tp.check_accounts(outside, 4)), tp.check_accounts(outside, 4))

    def test_exclusions_and_gaps(self):
        content = tp.read_example("t08")
        parts = tp.cut_ranges(content, "jsonl", [R(0, 1), R(1, 1)])
        got = tp.collect_ranges(IDENTITY["t08"], "jsonl", 2, [R(0, 1), R(1, 1)], complete_attempts(IDENTITY["t08"], "jsonl", parts),
                                exclusions={1: "boundary: insufficient neighbourhood"})
        self.assertEqual(got.status, "complete")
        self.assertEqual(got.accounts, {**EMPTY, "success": [0], "excluded": {1: "boundary: insufficient neighbourhood"}})
        self.assertEqual(tp.check_accounts(got.accounts, 2), [])
        seen = tp.exposure(got.accounts, 2, gaps=[{"scope": "T08/8001/b1/s4/e2-e4", "first": 2, "count": 3, "reason": "never recorded"}])
        self.assertEqual((seen["source_events"], seen["success"], seen["excluded"], seen["failure"], seen["unconfirmed"]), (2, 1, 1, 0, 0))
        self.assertEqual(seen["exposure"], 0.5)
        self.assertEqual(seen["original_gaps"], [{"scope": "T08/8001/b1/s4/e2-e4", "first": 2, "count": 3, "reason": "never recorded"}])
        with self.assertRaises(tp.PartitionError):
            tp.collect_ranges(IDENTITY["t08"], "jsonl", 2, [R(0, 1), R(1, 1)], complete_attempts(IDENTITY["t08"], "jsonl", parts),
                              exclusions={1: ""})

    def test_scope_is_stable(self):
        self.assertEqual(tp.scope(tp.Identity("T07", 7001, 1, 2), 49), "T07/7001/b1/s2/e49")

    def test_a_bad_plan_is_rejected(self):
        content = tp.read_example("t08")
        parts = tp.cut_ranges(content, "jsonl", [R(0, 1), R(1, 1)])
        with self.assertRaises(tp.PartitionError):
            tp.collect_ranges(IDENTITY["t08"], "jsonl", 2, [R(0, 1), R(0, 1)], complete_attempts(IDENTITY["t08"], "jsonl", parts))
        with self.assertRaises(tp.PartitionError):
            tp.collect_ranges(IDENTITY["t08"], "jsonl", 3, [R(0, 1), R(1, 1)], complete_attempts(IDENTITY["t08"], "jsonl", parts))


class Recovery(unittest.TestCase):
    """K1-K4: killed, out-of-memory, timed-out and unconfirmed attempts at the collection."""

    def setUp(self):
        self.name = "t07-refit"
        self.content = tp.read_example(self.name)
        self.parts = tp.cut_ranges(self.content, "t07-refit", [R(0, 1), R(1, 1)])
        self.partial = self.parts[1][1][: len(self.parts[1][1]) // 2]

    def collect(self, second_attempts, block=1):
        identity = tp.Identity("T07", 7001, block, 2)
        attempts = complete_attempts(identity, "t07-refit", self.parts[:1])
        attempts[R(1, 1)] = second_attempts(identity)
        return tp.collect_ranges(identity, "t07-refit", 2, [R(0, 1), R(1, 1)], attempts)

    def test_k1_a_killed_range_leaves_nothing_that_passes(self):
        for state in ("TIMEOUT", "OUT_OF_MEMORY", "CANCELLED by 1234"):
            got = self.collect(lambda identity: [tp.Attempt(state, 0, "00:30:00", ("draws-started",), None, self.partial, attempt="a1")])
            self.assertEqual(got.status, "missing", state)
            self.assertEqual(got.accounts, {**EMPTY, "success": [0], "failure": [1]}, state)

    def test_k2_a_resubmission_never_counts_the_partial_file(self):
        def history(identity):
            fresh = self.parts[1][1]
            return [tp.Attempt("TIMEOUT", 0, "00:30:00", ("draws-started",), None, self.partial, attempt="a1"),
                    tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), tp.make_record(identity, R(1, 1), fresh, "a2"), self.partial, attempt="a2")]
        got = self.collect(history, block=2)
        self.assertEqual(got.status, "missing")
        self.assertIn("not the one its record names", got.missing[0][1])
        self.assertEqual(got.accounts["failure"], [1])

    def test_k2_a_repeat_on_a_freeze_b_block_but_not_on_block_11(self):
        def history(identity):
            fresh = self.parts[1][1]
            return [tp.Attempt("TIMEOUT", 0, "00:30:00", ("draws-started",), None, self.partial, attempt="a1"),
                    tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), tp.make_record(identity, R(1, 1), fresh, "a2"), fresh, attempt="a2")]
        self.assertEqual(self.collect(history, block=2).status, "complete")
        got = self.collect(history, block=11)
        self.assertEqual(got.status, "missing")
        self.assertEqual(got.accounts["failure"], [1])

    def test_k3_unconfirmed(self):
        fresh = self.parts[1][1]
        running = self.collect(lambda identity: [tp.Attempt("RUNNING", 0, "00:10:00", ("draws-started",), None, self.partial, attempt="a1")])
        self.assertEqual(running.status, "missing")
        self.assertEqual(running.accounts, {**EMPTY, "success": [0], "unconfirmed": [1]})
        self.assertIn("check before resubmitting", running.missing[0][1])
        unconfirmed = self.collect(lambda identity: [tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",),
                                                                tp.make_record(identity, R(1, 1), fresh), fresh, termination="unconfirmed", attempt="a1")])
        self.assertEqual(unconfirmed.accounts["unconfirmed"], [1])
        self.assertEqual(tp.check_accounts(unconfirmed.accounts, 2), [])

    def test_k4_a_complete_file_without_a_record_is_never_counted(self):
        fresh = self.parts[1][1]
        got = self.collect(lambda identity: [tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), None, fresh, attempt="a1")])
        self.assertEqual(got.status, "missing")
        self.assertEqual(got.accounts["failure"], [1])

    def test_a_record_of_another_range_or_bin_is_refused(self):
        fresh = self.parts[1][1]
        other = self.collect(lambda identity: [tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",),
                                                          tp.make_record(tp.Identity("T07", 7001, 1, 3), R(1, 1), fresh), fresh, attempt="a1")])
        self.assertEqual(other.accounts["failure"], [1])
        shifted = self.collect(lambda identity: [tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",),
                                                            tp.make_record(identity, R(0, 1), fresh), fresh, attempt="a1")])
        self.assertEqual(shifted.accounts["failure"], [1])


@needs("process_groups")  # run_workflow.py refuses a host without them (missing-dependency, tests/core/test_hostcaps.py)
class Runner(unittest.TestCase):
    """K5-K8: run_workflow.py, unchanged, on a timed-out, killed, resubmitted and repeatedly failing step."""

    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.work = Path(self._scratch.name)

    def tearDown(self):
        self._scratch.cleanup()

    def test_k5_timeout(self):
        code, out, records = tp.run_steps(self.work, tp.partial_then("sleep"), timeout_s=1)
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "failed")
        self.assertEqual(records["range"]["extension"]["end_status"], "timeout")
        self.assertNotIn("merge", records)
        self.assertEqual([s["id"] for s in out["steps"]], ["range"])

    def test_k6_killed(self):
        code, out, records = tp.run_steps(self.work, tp.partial_then("kill"))
        self.assertEqual(code, 1)
        self.assertEqual(records["range"]["extension"]["end_status"], "failure")
        self.assertEqual(records["range"]["extension"]["exit_status"], -9)
        self.assertNotIn("merge", records)

    def test_k7_resubmission(self):
        code, _, _ = tp.run_steps(self.work, tp.partial_then("sleep"), timeout_s=1)
        self.assertEqual(code, 1)
        self.assertTrue((self.work / "range.out").is_file())
        code, out, _ = tp.run_steps(self.work, tp.partial_then("sleep"), timeout_s=1, incremental=True)
        self.assertEqual(code, 1)
        self.assertFalse(out["steps"][0].get("skipped", False), "an identical resubmission after a timeout is never a skip")
        code, out, records = tp.run_steps(self.work, tp.partial_then("keep"), incremental=True)
        self.assertEqual(code, 1)
        self.assertFalse(out["steps"][0].get("skipped", False))
        self.assertIn("existed before and were not written by this run", out["steps"][0]["stderr_tail"])
        code, out, records = tp.run_steps(self.work, tp.partial_then("rewrite"), incremental=True)
        self.assertEqual(code, 0, out)
        self.assertEqual(records["range"]["extension"]["end_status"], "success")
        self.assertEqual((self.work / "range.out").read_text(), "complete\n")

    def test_k8_no_retry(self):
        for extra in ({}, {"retries": 3}):
            work = self.work / ("plain" if not extra else "retries")
            work.mkdir()
            code, _, _ = tp.run_steps(work, tp.partial_then("fail"), step_extra=extra)
            self.assertEqual(code, 1, extra)
            self.assertEqual((work / "invocations.txt").read_text(), "1\n", extra)


class RecordedDriver(unittest.TestCase):
    """The job's R2 and R3 functions on small files cut from the recorded examples (written after green-1, not test-first: the job's
    driver, M-items R2 and R3 of the stage plan)."""

    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.base = Path(self._scratch.name)

    def tearDown(self):
        self._scratch.cleanup()

    def test_r2_jsonl_ranges(self):
        content = tp.read_example("t09-topology")
        (self.base / "full.jsonl").write_bytes(content)
        for first, part in tp.cut_ranges(content, "jsonl", [R(0, 1), R(1, 1)]):
            (self.base / f"r{first}.jsonl").write_bytes(part)
        ok, single, report = tp.jsonl_ranges(self.base, "full.jsonl", [(0, "r0.jsonl"), (1, "r1.jsonl")])
        self.assertTrue(ok, report)
        self.assertEqual(single.count, 2)
        ok, _, report = tp.jsonl_ranges(self.base, "full.jsonl", [(0, "r0.jsonl")])
        self.assertFalse(ok)
        self.assertEqual(report["omitted"], [("event", 1)])

    def test_r3_refit_ranges_and_their_collection(self):
        content = tp.read_example("t07-refit")
        parts = tp.cut_ranges(content, "t07-refit", [R(0, 1), R(1, 1)])
        names = {}
        for first, part in parts:
            names[first] = f"refit-{first}.product"
            (self.base / names[first]).write_bytes(part)
        problems, keys = tp.refit_ranges(self.base, names, 1, 2)
        self.assertEqual(problems, [])
        self.assertEqual(keys, len(tp.read_product(content, "t07-refit").objects))
        identity = tp.Identity("T07", 7001, 1, 4)
        attempts = {R(f, 1): [tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), tp.make_record(identity, R(f, 1), part),
                                         self.base / names[f], attempt="a1")] for f, part in parts}
        self.assertEqual(tp.collect_ranges(identity, "t07-refit", 2, [R(0, 1), R(1, 1)], attempts).status, "complete")
        dropped = tp.collect_ranges(identity, "t07-refit", 2, [R(0, 1), R(1, 1)], {R(0, 1): attempts[R(0, 1)]})
        self.assertEqual((dropped.status, dropped.accounts["failure"]), ("missing", [1]))
        records = {f: tp.make_record(identity, R(f, 1), part) for f, part in parts}
        problems, _ = tp.refit_ranges(self.base, names, 1, 2, records)
        self.assertTrue(problems and all("stratum file or range input" in p for p in problems), problems)   # fix round 1, m3
        header = tp.read_product(parts[0][1], "t07-refit").header
        tied = {f: layout.RangeRecord(**{**r.__dict__, "stratum_sha256": header["data_sha256"], "input_sha256": header["hit_sets_sha256"]})
                for f, r in records.items()}
        self.assertEqual(tp.refit_ranges(self.base, names, 1, 2, tied)[0], [])
        (self.base / "refit-1.product").write_bytes(parts[0][1])   # range 1's file holds range 0's objects
        problems, _ = tp.refit_ranges(self.base, names, 1, 2)
        self.assertTrue(any("outside" in p for p in problems), problems)
        self.assertTrue(any("two ranges" in p for p in problems), problems)
        changed = tp.collect_ranges(identity, "t07-refit", 2, [R(0, 1), R(1, 1)], attempts)
        self.assertEqual(changed.accounts["failure"], [1])
        (self.base / "refit-1.product").write_bytes(parts[1][1][:-30])   # truncated
        problems, _ = tp.refit_ranges(self.base, names, 1, 2)
        self.assertTrue(any("truncated" in p or "end line" in p for p in problems), problems)


class Command(unittest.TestCase):
    """The job's operation refuses an evidence folder without the pinned files (rejected, exit 2)."""

    def test_recorded_rejects_a_missing_folder(self):
        with tempfile.TemporaryDirectory() as scratch:
            self.assertEqual(tp.main(["recorded", "--evidence", str(Path(scratch) / "absent")]), 2)
            self.assertEqual(tp.main(["recorded", "--evidence", scratch]), 2)

    def test_recorded_pins_exactly_the_files_it_reads(self):
        """Fix round 1, n1 (replaces a vacuous uniqueness test): RECORDED pins every file recorded() reads, and only those."""
        self.assertEqual(set(tp.RECORDED), tp.recorded_reads())
        self.assertTrue(all(len(h) == 64 for h in tp.RECORDED.values()))
        self.assertTrue(all(not p.startswith("/") for p in tp.RECORDED))

    def test_a_refusal_after_the_hashes_is_incomplete(self):
        """Fix round 1, m6: past the hash check, a refusal is the harness's crash (exit 3), never rejected (exit 2)."""
        saved = (tp.RECORDED, tp._compare_recorded)
        def refuse(evidence, lines):
            raise tp.PartitionError("refused after the hashes")
        try:
            tp.RECORDED, tp._compare_recorded = {}, refuse
            with tempfile.TemporaryDirectory() as scratch:
                self.assertEqual(tp.main(["recorded", "--evidence", scratch]), 3)
        finally:
            tp.RECORDED, tp._compare_recorded = saved


class FixRound1(unittest.TestCase):
    """Fix round 1 (jobs/t12-stage3/REVIEW.md), written before the harness change and run red first: I1, I2, m1, m2, m5."""

    def setUp(self):
        self.content = tp.read_example("t07-refit")
        self.parts = tp.cut_ranges(self.content, "t07-refit", [R(0, 1), R(1, 1)])
        self.identity = tp.Identity("T07", 7001, 2, 2)
        self._scratch = tempfile.TemporaryDirectory()
        self.base = Path(self._scratch.name)

    def tearDown(self):
        self._scratch.cleanup()

    def first_range(self):
        content = self.parts[0][1]
        return {R(0, 1): [tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), tp.make_record(self.identity, R(0, 1), content, "j0"),
                                     content, attempt="j0")]}

    def collect(self, second):
        attempts = self.first_range()
        attempts[R(1, 1)] = second
        return tp.collect_ranges(self.identity, "t07-refit", 2, [R(0, 1), R(1, 1)], attempts)

    def test_i1_a_record_of_an_earlier_attempt_is_not_the_counted_attempts(self):
        fresh = self.parts[1][1]
        stale = tp.make_record(self.identity, R(1, 1), fresh, "j1")   # left by attempt j1, which then timed out
        got = self.collect([tp.Attempt("TIMEOUT", 0, "00:30:00", ("draws-started",), stale, fresh, attempt="j1"),
                            tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), stale, fresh, attempt="j2")])
        self.assertEqual(got.accounts["failure"], [1])
        self.assertIn("attempt", got.missing[0][1])
        own = tp.make_record(self.identity, R(1, 1), fresh, "j2")
        got = self.collect([tp.Attempt("TIMEOUT", 0, "00:30:00", ("draws-started",), stale, fresh, attempt="j1"),
                            tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), own, fresh, attempt="j2")])
        self.assertEqual(got.status, "complete")

    def test_i2_a_t07_refit_event_without_objects_is_not_claimed_read(self):
        single = tp.without_event_objects(self.content, 1)
        parts = tp.cut_ranges(single, "t07-refit", [R(0, 1), R(1, 1)])
        attempts = {R(f, 1): [tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), tp.make_record(self.identity, R(f, 1), c, "j"),
                                         c, attempt="j")] for f, c in parts}
        got = tp.collect_ranges(self.identity, "t07-refit", 2, [R(0, 1), R(1, 1)], attempts)
        self.assertEqual(got.accounts["unconfirmed"], [1])
        self.assertEqual(got.accounts["success"], [0])
        self.assertEqual(got.status, "missing")
        self.assertIn("format gap", got.missing[0][1])

    def test_m1_exposure_refuses_inconsistent_accounts_and_overlapping_gaps(self):
        good = {"success": [0], "excluded": {1: "boundary"}, "failure": [], "unconfirmed": []}
        with self.assertRaises(tp.PartitionError):
            tp.exposure({**good, "failure": [0]}, 2)
        with self.assertRaises(tp.PartitionError):
            tp.exposure(good, 2, gaps=[{"scope": "x", "first": 10, "count": 5, "reason": "never recorded"},
                                       {"scope": "y", "first": 12, "count": 5, "reason": "never recorded"}])
        with self.assertRaises(tp.PartitionError):
            tp.exposure(good, 2, gaps=[{"scope": "x", "first": 10, "count": 5, "reason": ""}])
        seen = tp.exposure(good, 2, gaps=[{"scope": "x", "first": 10, "count": 5, "reason": "never recorded"}])
        self.assertEqual(set(seen["denominator"]), {"success", "excluded", "failure", "unconfirmed", "original_gaps"})

    def test_m2_an_earlier_unconfirmed_attempt_makes_the_range_unconfirmed(self):
        fresh = self.parts[1][1]
        got = self.collect([tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), None, fresh, termination="unconfirmed", attempt="j1"),
                            tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), tp.make_record(self.identity, R(1, 1), fresh, "j2"),
                                       fresh, attempt="j2")])
        self.assertEqual(got.accounts["unconfirmed"], [1])
        self.assertIn("check before resubmitting", got.missing[0][1])

    def test_m5_a_streamed_product_gets_the_verdict_of_the_same_bytes(self):
        lines = self.parts[1][1].decode().split("\n")
        first_object = next(i for i, line in enumerate(lines) if line.startswith("track "))
        late_header = "\n".join(lines[:first_object + 1] + ["acts_version 0.0.0"] + lines[first_object + 1:]).encode()
        cases = {"truncated": self.parts[1][1][:-30], "outside": self.parts[0][1], "header after an object": late_header,
                 "intact": self.parts[1][1]}
        for name, content in cases.items():
            path = self.base / f"{name.replace(' ', '-')}.product"
            path.write_bytes(content)
            verdicts = []
            for product in (content, path):
                record = tp.make_record(self.identity, R(1, 1), content, "j2")
                got = self.collect([tp.Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), record, product, attempt="j2")])
                verdicts.append((got.status, got.accounts["failure"]))
            self.assertEqual(verdicts[0], verdicts[1], name)
            self.assertEqual(verdicts[0], ("complete", []) if name == "intact" else ("missing", [1]), name)



class CarriedMinors(unittest.TestCase):
    """Carried from the stage 3 re-review (jobs/t12-stage3/REREVIEW.md): the gap checks of exposure()."""

    GOOD = {"success": [0], "excluded": {1: "boundary"}, "failure": [], "unconfirmed": []}

    def test_equal_spans_with_and_without_a_scope_are_an_overlap_not_a_crash(self):
        """Minor (1): two gaps with the same span, one scope None and one a string, overlap; the sort never compares the scopes."""
        for scopes in ((None, "x"), ("x", None)):
            with self.assertRaises(tp.PartitionError, msg=scopes):
                tp.exposure(self.GOOD, 2, gaps=[{"scope": scopes[0], "first": 10, "count": 5, "reason": "never recorded"},
                                                {"scope": scopes[1], "first": 10, "count": 5, "reason": "never recorded"}])
        seen = tp.exposure(self.GOOD, 2, gaps=[{"scope": None, "first": 10, "count": 5, "reason": "never recorded"},
                                               {"scope": "x", "first": 15, "count": 5, "reason": "never recorded"}])
        self.assertEqual(len(seen["original_gaps"]), 2)

    def test_a_gap_span_is_a_non_negative_integer_never_a_bool(self):
        """Minor (2): first True, first -1 and count True are refused; first 0 is accepted."""
        for first, count in ((True, 5), (-1, 5), (0, True), (False, 5)):
            with self.assertRaises(tp.PartitionError, msg=(first, count)):
                tp.exposure(self.GOOD, 2, gaps=[{"scope": "x", "first": first, "count": count, "reason": "never recorded"}])
        self.assertEqual(tp.exposure(self.GOOD, 2, gaps=[{"scope": "x", "first": 0, "count": 1, "reason": "never recorded"}])["source_events"], 2)


if __name__ == "__main__":
    unittest.main()
