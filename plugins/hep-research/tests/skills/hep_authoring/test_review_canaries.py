"""Facts and design canaries of the independent review (spec A5; acceptance criteria 6 and 9): two-sided witnesses on
fixture data, one-sided candidates rejected and counted as a shortfall, key diffs, and hit and exact-correction
matching for numeric keys written in Chinese and in English. Synthetic data only."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.skills.hep_authoring import review_harness as H
from contracts import review as R
from review_lib import canary as C
from review_lib import units as U

LENSES = ["facts", "design", "sources", "bypass"]


def table(doc, root=H.PLUGIN):
    return U.unit_table(doc, LENSES, {}, (), root)


class WitnessTests(unittest.TestCase):
    def make(self, lens, n=2, seed="ab" * 32, doc=H.DOC, root=H.PLUGIN):
        units = table(doc, root)
        eligible = [u["id"] for u in units if u["in_scope"][lens]]
        return C.make_canaries(lens, units, doc, eligible, set(), n, seed, root)

    def test_facts_and_design_canaries_are_two_sided(self):
        lines = (H.PLUGIN / "LICENSE").read_text(encoding="utf-8").splitlines()
        for lens in ("facts", "design"):
            for seed in ("ab" * 32, "cd" * 32, "ef" * 32):
                cans, _ = self.make(lens, seed=seed)
                self.assertTrue(cans, (lens, seed))
                for c in cans:
                    with self.subTest(lens=lens, unit=c["unit"]):
                        self.assertEqual(H.DOC.count(c["original"]), 1)
                        self.assertNotIn(c["mutated"], H.DOC)
                        self.assertTrue(c["witness_right"] and c["witness_wrong"])
                        if c["type"] == "line-range":
                            a, b = map(int, c["witness_right"]["lines"].split("-"))
                            na, nb = map(int, c["witness_wrong"]["lines"].split("-"))
                            cited = "\n".join(lines[a - 1:b])
                            self.assertTrue(cited.strip())                     # the original lines exist
                            self.assertNotIn(cited, "\n".join(lines[na - 1:nb]))  # the new range does not hold them
                        elif c["type"] == "value":
                            self.assertIn(c["witness_right"]["value"], lines[c["witness_right"]["line"] - 1])
                            self.assertFalse(any(R.key_in(ln, c["witness_wrong"]["value"]) for ln in lines))
                        else:
                            units = {u["id"]: u for u in table(H.DOC)}
                            right, wrong = units[c["witness_right"]["cited"]], units[c["witness_wrong"]["cited"]]
                            self.assertNotEqual(right["text"], wrong["text"])
                        self.assertIn(c["old_key"], c["original"])
                        self.assertIn(c["new_key"], c["mutated"])

    def test_canaries_of_different_slots_never_share_a_unit(self):
        units = table(H.DOC)
        facts, _ = self.make("facts")
        eligible = [u["id"] for u in units if u["in_scope"]["design"]]
        design, _ = C.make_canaries("design", units, H.DOC, eligible + [c["unit"] for c in facts],
                                    {c["unit"] for c in facts}, 2, "ab" * 32)
        self.assertFalse({c["unit"] for c in facts} & {c["unit"] for c in design})

    def test_one_sided_candidate_is_rejected_and_short(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "rep.txt").write_text("same line\n" * 40, encoding="utf-8")
            doc = "# Note\n\nThe setting is at `rep.txt:3-4` of the file.\n"
            cans, rejected = self.make("facts", n=1, doc=doc, root=root)
            self.assertEqual(cans, [])  # canary_shortfall: fewer than canaries_per_slot
            self.assertEqual([r["reason"] for r in rejected], ["one-sided witness"])
            self.assertEqual(rejected[0]["witness_right"]["lines"], "3-4")

    def test_shortfall_reaches_the_dispatched_event(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t), config={"config_version": "1.0.0", "models": ["a", "b"], "canaries_per_slot": 3}).setup()
            h.start()
            H.dispatch_all(h, h.next())
            ds = [h.dispatched(h.slot_of("lens", lens)) for lens in ("facts", "design")]
            self.assertTrue(any(d["canaries"] < d["canaries_expected"] == 3 for d in ds), ds)
            self.assertIn("canary_shortfall", [c["code"] for c in R.check(h.rv.dir)["codes"]])

    def test_key_diff_widening(self):
        self.assertEqual(C.key_diff("foo.py:120-125", "foo.py:123-128"), ("120-125", "123-128"))
        self.assertEqual(C.key_diff("x 2.0 y", "x 2.3 y"), ("2.0", "2.3"))
        self.assertEqual(C.key_diff("see §6.5,", "see §6.4,"), ("6.5", "6.4"))
        self.assertEqual(C.key_diff("use `finding_shape`", "use `finding_shapes`"), ("finding_shape", "finding_shapes"))


class HitTests(unittest.TestCase):
    LIM = {"max_units_per_claim": 3}

    def record(self, value, correction):
        return {"findings": [{"id": "F1", "units": ["U0002"], "value": value, "correction": correction,
                              "description": "d", "fix": ""}]}

    def test_numeric_hits_and_exact_corrections_in_chinese_and_english(self):
        can = [{"unit": "U0002", "new_key": "5", "old_key": "3"}]
        for unit_text, value, correction in (("審查必須在 5 倍的時間內完成。", "5 倍", "應為 3 倍"),
                                             ("The review takes 5x the time.", "5x the time", "3x the time"),
                                             ("The review takes 5x the time.", "5x", "it should say 3 times")):
            with self.subTest(text=unit_text):
                rec = self.record(value, correction)
                hits = R.canary_hits(rec, can, {"U0002": unit_text}, 3)
                self.assertEqual(hits, {"U0002": ["F1"]})
                self.assertTrue(R.exact_correction(rec["findings"][0], "3"))

    def test_value_must_be_an_excerpt_and_cite_the_unit(self):
        can = [{"unit": "U0002", "new_key": "5", "old_key": "3"}]
        self.assertEqual(R.canary_hits(self.record("15 倍", "3"), can, {"U0002": "須 15 倍"}, 3), {"U0002": []})
        self.assertEqual(R.canary_hits(self.record("5 hours", "3"), can, {"U0002": "takes 5x"}, 3), {"U0002": []})

    def test_metrics_count_hits_and_exact_corrections(self):
        rec = self.record("5x", "3x")
        rec.update(role="reviewer", skim=[], claims=[], verdicts=[], evidence=[])
        m = R.record_metrics(rec, {"deep_units": ["U0002"], "limits": self.LIM, "unit_text": {"U0002": "takes 5x"},
                                   "canaries": [{"unit": "U0002", "new_key": "5", "old_key": "3"}]})
        self.assertEqual(m["canaries"], [{"place": "deep", "hit": True, "exact": True}])


if __name__ == "__main__":
    unittest.main()
