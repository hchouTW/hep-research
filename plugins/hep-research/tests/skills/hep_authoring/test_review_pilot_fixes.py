"""Fixes found by the P3 stage-1 pilot (docs/dev/decision-independent-review.md, Decision 4): reviewers read copies
of the delivered document elsewhere on the host; design canaries never fired on documents without numbered
references; slots with nothing in scope were dispatched. Synthetic data only."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.skills.hep_authoring import review_harness as H
from review_lib import canary as C
from review_lib import units as U

LENSES = ["facts", "design", "sources", "bypass"]


def copy_of_doc() -> str:
    return H.DOC.replace("Each record lists its `claims` with their `verdicts`.", "Each record lists its claims.")


class CopyGuardTests(unittest.TestCase):
    def test_receipt_rejects_a_record_that_read_a_version_of_the_document(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            old = h.project / "notes" / "old-draft.md"
            old.parent.mkdir()
            old.write_text(copy_of_doc(), encoding="utf-8")
            out = h.start()
            self.assertIn("<project>/notes/old-draft.md", out["copies"])
            self.assertIn("exists nowhere else", out["warning"])
            H.dispatch_all(h, h.next())
            sid = h.slot_of("lens", "facts")
            rec = h.good_record(sid)
            rec["paths_read"].append({"path": str(old), "sha256": H.sha(old)})
            h.write_record(sid, rec)
            h.run("receive", sid)
            ev = [e for e in h.rv.events() if e["event"] in ("accepted", "rejected")][-1]
            self.assertEqual(ev["data"]["codes"], ["read_outside_packet"])
            self.assertIn("a copy or version of the delivered document", " ".join(ev["data"]["problems"]))
            h.run("report", expect=0)
            self.assertIn("<project>/notes/old-draft.md", (h.rv.dir / "report.md").read_text(encoding="utf-8"))

    def test_unrelated_files_are_not_copies(self):
        probes = U.copy_probes(U.split_markdown(H.DOC))
        self.assertFalse(U.is_copy(H.PLUGIN / "LICENSE", probes))
        self.assertGreater(U.copy_share(copy_of_doc(), probes), 0.9)

    def test_the_spec_in_the_plugin_is_found_as_a_copy(self):
        text = (H.PLUGIN / "docs" / "dev" / "independent-review-spec.md").read_text(encoding="utf-8")
        found = U.find_copies([H.PLUGIN], U.split_markdown(text.replace("13th Edition", "14th Edition")), [])
        self.assertIn(str((H.PLUGIN / "docs" / "dev" / "independent-review-spec.md").resolve()), found)

    def test_instructions_forbid_other_copies(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            h.start()
            act = h.next()
            h.run("dispatch", act["slots"][0], expect=0)
            text = (h.adir(act["slots"][0]) / "packet" / "instructions.md").read_text(encoding="utf-8")
            self.assertIn("Never read any other copy or version of the document under review", text)
            self.assertIn("git history", text)


DESIGN_DOC = """# Plan

## Budget

The pilot used 54 agent runs in total.
Each agent reads the `scope.json` file first.

## Notes

Reviewers write findings to `scope.json` only after reading it.
The cost estimate assumes 54 agent runs again.
"""


class DesignCanaryTests(unittest.TestCase):
    def test_repeated_value_and_term_canaries_are_two_sided(self):
        units = U.unit_table(DESIGN_DOC, LENSES, {}, ())
        eligible = [u["id"] for u in units if u["in_scope"]["design"]]
        types = set()
        for seed in ("ab" * 32, "cd" * 32, "ef" * 32, "12" * 32):
            cans, _ = C.make_canaries("design", units, DESIGN_DOC, eligible, set(), 2, seed)
            self.assertTrue(cans, seed)
            for c in cans:
                types.add(c["type"])
                self.assertEqual(DESIGN_DOC.count(c["original"]), 1)
                self.assertNotIn(c["mutated"], DESIGN_DOC)
                self.assertTrue(c["witness_right"] and c["witness_wrong"])
                other = next(u for u in units if u["id"] == c["witness_right"]["cited"])
                self.assertNotEqual(other["id"], c["unit"])
                self.assertIn(c["witness_right"]["ref"].split()[0], other["text"])
        self.assertEqual(types, {"repeated-value", "repeated-term"})

    def test_no_candidate_without_a_repeat(self):
        units = U.unit_table("# A\n\nThe run took 12 minutes with `alpha.json`.\n", LENSES, {}, ())
        cans, _ = C.make_canaries("design", units, "# A\n\nThe run took 12 minutes with `alpha.json`.\n",
                                  [u["id"] for u in units if u["in_scope"]["design"]], set(), 2, "ab" * 32)
        self.assertEqual(cans, [])


NO_SOURCES_DOC = """# Note

The contract module `contracts/review.py` must stay pure.
Every finding must quote 1 to 3 units.
The `limitations` field records what was not checked.
A reviewer must never read the event log.
"""


class SlotPlanTests(unittest.TestCase):
    def test_lens_without_units_gets_no_slot_and_no_slot_is_empty(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            h.write_doc(NO_SOURCES_DOC)
            out = h.start()
            self.assertEqual(sorted(out["no_slot"]), ["sources"])
            self.assertEqual(out["slots"], 6)
            roles = sorted((v["role"], v["lens"]) for v in h.rv.slots()["1"].values())
            self.assertNotIn(("lens", "sources"), roles)
            self.assertNotIn(("shadow", "sources"), roles)
            H.dispatch_all(h, h.next())
            for sid in h.rv.slots()["1"]:
                scope = h.packet(sid)[0]
                with self.subTest(slot=sid):
                    self.assertTrue(scope["skim_units"] or scope["deep_units"] or scope["focus_units"])
            h.run("report", expect=0)
            self.assertIn("lens sources: no unit in scope", (h.rv.dir / "report.md").read_text(encoding="utf-8"))

    def test_fixture_keeps_four_lenses_and_four_shadows(self):
        units = U.unit_table(H.DOC, LENSES, {}, ())
        import review as DRV
        deep = {L: [u["id"] for u in units if u["in_scope"][L]] for L in LENSES}
        plan, none = DRV.slot_plan(units, LENSES, deep)
        self.assertEqual(len(plan), 8)
        self.assertEqual(none, {})


if __name__ == "__main__":
    unittest.main()
