"""End-to-end independent review (acceptance criteria 8 and 10): driven only by `next` and the action it prints, four
lenses and four shadows go through a reject and re-dispatch, a returned-empty, a timeout, an arbitration
(uphold-finding), an adopted-unverified change, a change_reverted, a change_confirmed, an escalate followed by the
report and a human resolve, a re-review with changed, added and removed units, and close; check exits 0. Two runs
with the same clock, seed and observation input give byte-identical review directories. Synthetic data only."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.skills.hep_authoring import review_harness as H
from contracts import review as R


def tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="hep-review-e2e-")
        cls.h, cls.marks = H.run_e2e(Path(cls._tmp.name) / "a")
        cls.events = cls.h.rv.events()
        cls.kinds = [e["event"] for e in cls.events]

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_four_lenses_and_four_shadows(self):
        slots = self.h.rv.slots()["1"]
        roles = sorted((v["role"], v["lens"]) for v in slots.values() if v["role"] != "arbiter")
        self.assertEqual(roles, sorted([(r, L) for r in ("lens", "shadow") for L in ("facts", "design", "sources", "bypass")]))

    def test_reject_and_redispatch(self):
        rej = [e["data"] for e in self.events if e["event"] == "rejected"]
        self.assertEqual(len(rej), 1)
        self.assertEqual(rej[0]["codes"], ["refutation_weak"])
        again = [e for e in self.events if e["event"] == "dispatched" and e["data"]["slot_id"] == rej[0]["slot_id"]
                 and e["data"]["round"] == rej[0]["round"]]
        self.assertEqual([e["data"]["attempt"] for e in again], [1, 2])

    def test_returned_empty_and_timeout_are_withdrawn(self):
        reasons = sorted(e["data"]["reason"] for e in self.events if e["event"] == "withdrawn")
        self.assertEqual(reasons, ["host-failure", "timeout"])
        hf = next(e["data"] for e in self.events if e["event"] == "withdrawn" and e["data"]["reason"] == "host-failure")
        self.assertTrue(any(e["event"] == "returned" and e["data"]["slot_id"] == hf["slot_id"] and e["data"]["attempt"] == hf["attempt"]
                            for e in self.events))

    def test_arbitration_uphold_finding(self):
        res = [e["data"] for e in self.events if e["event"] == "arbitration_resolved"]
        self.assertEqual([r["conclusion"] for r in res], ["uphold-finding"])
        st = R.fold(self.events)
        item = st["items"][res[0]["item_id"]]
        disp = [e["data"]["disposition"] for e in self.events if e["event"] == "disposed" and e["data"]["finding"] == item["finding"]]
        self.assertEqual(disp, ["declined", "changed"])

    def test_adopted_unverified(self):
        self.assertTrue(any(e["event"] == "disposed" and (e["data"]["verification"] or {}).get("adopted_unverified")
                            for e in self.events))

    def test_change_reverted_and_confirmed(self):
        self.assertEqual(self.kinds.count("change_reverted"), 1)
        self.assertEqual(self.kinds.count("change_confirmed"), 2)

    def test_escalate_report_resolve_then_continue(self):
        i = self.kinds.index("escalated")
        self.assertEqual(self.kinds[i + 1:].index("reported") >= 0, True)
        j = self.kinds.index("human_resolved")
        self.assertLess(self.kinds.index("reported"), j)
        self.assertIn("closed", self.kinds[j:])

    def test_rereview_with_changed_added_removed(self):
        m = self.marks["mapping"]
        self.assertGreaterEqual(m["changed"], 1)
        self.assertGreaterEqual(m["added"], 1)
        self.assertGreaterEqual(m["removed"], 1)
        self.assertEqual(self.kinds.count("round_started"), 2)

    def test_auto_canary_disposals(self):
        self.assertTrue(any(e["event"] == "disposed" and e["data"]["disposition"] == "auto-canary" for e in self.events))

    def test_closed_and_check_exits_zero(self):
        self.assertEqual(self.kinds[-1], "closed")
        res = R.check(self.h.rv.dir)
        self.assertEqual(res["status"], "ok", res)
        cli = subprocess.run([sys.executable, str(H.PLUGIN / "contracts" / "review.py"), "check", str(self.h.rv.dir)],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(cli.returncode, 0, cli.stdout[-800:])
        self.assertIn("adopted_unverified", cli.stdout)

    def test_next_after_close_stops_without_writing(self):
        n = len(self.h.rv.events())
        out = self.h.next()
        self.assertEqual((out["action"], out["row"]), ("stop", 2))
        self.assertEqual(len(self.h.rv.events()), n)

    def test_report_lists_the_required_parts(self):
        text = (self.h.rv.dir / "report.md").read_text(encoding="utf-8")
        for part in ("## Configuration used", "weak_config", "Hit rate (skim)", "Exact-correction rate", "original right",
                     "new wrong", "no_control", "## Shadow review", "adopted-unverified", "change_reverted",
                     "change_confirmed", "returned-empty", "## Host checks", "## Reviews of this document",
                     "## Limitations that applied", "Agents dispatched"):
            self.assertIn(part, text)

    def test_reproducible_byte_for_byte(self):
        with tempfile.TemporaryDirectory(prefix="hep-review-e2e-b-") as tmp:
            h2, _ = H.run_e2e(Path(tmp) / "a")
            a, b = tree(self.h.rv.dir), tree(h2.rv.dir)
            self.assertEqual(sorted(a), sorted(b))
            diff = [k for k in a if a[k] != b[k]]
            self.assertEqual(diff, [])


if __name__ == "__main__":
    unittest.main()
