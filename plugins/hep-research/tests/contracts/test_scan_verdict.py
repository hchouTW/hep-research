"""P6.1: the scan-service interface. A verdict carries a fixed status and the budget state only (never a value, token,
location or count); the budget counts candidate values tested (a group test asks about every number in the outputs),
charges every submission whatever its answer, and refuses the one that would exceed it. Synthetic data only."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import scan_verdict as sv  # noqa: E402
from core.blinding.blinding import agent_view, scan_paths  # noqa: E402


class ScanVerdictTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def output(self, name, text):
        p = self.d / name
        p.write_text(text)
        return p

    def test_group_test_is_counted_in_candidate_values(self):
        self.assertEqual(sv.count_candidates(" ".join(str(i) for i in range(21))), 21)  # printing 0..20 asks 21 questions
        self.assertGreaterEqual(sv.count_candidates("total 1,234.5 events"), 1)
        sub = sv.make_submission([self.output("a.txt", "x = 3.5, y = 7"), self.output("b.csv", "1,2,3\n")], "ana", "rel-1", "s-1")
        self.assertEqual(sub["candidate_values"], 5)
        self.assertEqual(len(sub["outputs"]), 2)

    def test_budget_arithmetic(self):
        budget = {"analysis": "ana", "limit": 100, "consumed": 0, "charges": []}
        files = [self.output(f"o{i}.txt", " ".join("1" for _ in range(n))) for i, n in enumerate((40, 40, 30, 20))]
        subs = [dict(sv.make_submission([f], "ana", "rel-1", "s"), submission_id=f"sub-{i}") for i, f in enumerate(files)]
        got = [{str(f): f.read_bytes()} for f in files]
        budget, ok1 = sv.charge(budget, subs[0], got[0])
        budget, ok2 = sv.charge(budget, subs[1], got[1])
        refused, ok3 = sv.charge(budget, subs[2], got[2])  # 80 + 30 > 100: not scanned, not charged
        self.assertEqual((ok1, ok2, ok3), (True, True, False))
        self.assertEqual(budget["consumed"], 80)
        self.assertTrue(refused["exhausted"])
        self.assertFalse(sv.charge(refused, subs[3], got[3])[1])  # exhausted stays exhausted
        budget, ok4 = sv.charge(budget, subs[3], got[3])  # without the refused one: exactly reaches the limit
        self.assertTrue(ok4)
        self.assertTrue(budget["exhausted"])
        self.assertEqual([c["submission_id"] for c in budget["charges"]], ["sub-0", "sub-1", "sub-3"])
        other, ok = sv.charge(budget, dict(subs[0], analysis="another"), got[0])
        self.assertFalse(ok)  # one analysis's budget never pays for another's
        with self.assertRaises(ValueError):
            sv.charge({"analysis": "ana"}, subs[0], got[0])

    def test_the_service_recounts(self):
        budget = {"analysis": "ana", "limit": 100, "consumed": 0, "charges": []}
        f = self.output("o.txt", " ".join(str(i) for i in range(30)))
        sub = sv.make_submission([f], "ana", "rel-1", "s")
        lied = dict(sub, candidate_values=0)
        new, ok = sv.charge(budget, lied, {str(f): f.read_bytes()})
        self.assertTrue(ok)
        self.assertEqual(new["consumed"], 30)  # charged by the recount, not by the claim
        self.assertFalse(sv.charge(budget, sub, {str(f): b"0"})[1])  # bytes differ from the submitted digest
        self.assertFalse(sv.charge(budget, sub, {})[1])

    def test_verdict_never_carries_detail(self):
        leak = self.output("table.txt", "bins: 12 30 47.0 25 9")
        report = scan_paths([str(leak)], [47.0])
        self.assertEqual(report["status"], "fail")
        budget = {"analysis": "ana", "limit": 100, "consumed": 5, "charges": []}
        v = sv.verdict({"submission_id": "s-1"}, report, budget, True, time="2026-10-14T12:00:00Z")  # a fixed clock:
        # a real one can itself contain the sealed digits (03:47 on a CI run)
        self.assertEqual(sv.check_verdict(v), [])
        self.assertEqual(set(v), {"verdict_version", "submission_id", "status", "budget", "time"})
        text = json.dumps(v)
        self.assertNotIn("47", text)
        self.assertNotIn("table.txt", text)
        for extra in ({"hits": 1}, {"value": 47.0}, {"files": ["table.txt"]}, {"count": 1}):
            self.assertTrue(sv.check_verdict(dict(v, **extra)), extra)
        self.assertEqual(sv.verdict({"submission_id": "s-2"}, None, dict(budget, exhausted=True), False)["status"], "refused-budget")
        self.assertEqual(sv.verdict({"submission_id": "s-3"}, {"status": "weird"}, budget, True)["status"], "refused")
        self.assertEqual(agent_view(report)["status"], v["status"])  # the same status the agent view gives

    def test_command_line(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sv.main(["submission", "--analysis", "a", "--release", "r", "--session", "s", "--id", "x",
                            str(self.output("o.txt", "1 2 3"))])
        self.assertEqual((code, json.loads(out.getvalue())["candidate_values"]), (0, 3))
        bad = self.output("v.json", json.dumps({"verdict_version": "1.0.0", "submission_id": "x", "status": "fail",
                                                 "budget": "available", "time": "2026-10-14T12:00:00Z", "where": "line 3"}))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sv.main(["check-verdict", str(bad)]), 1)


if __name__ == "__main__":
    unittest.main()
