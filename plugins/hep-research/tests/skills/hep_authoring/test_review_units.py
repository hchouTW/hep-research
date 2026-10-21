"""Units, scope and sampling of the independent review (spec 4.1-4.5, acceptance criterion 10): every unit is a
contiguous excerpt of its document (also an indented code fence inside a list item, which is one unit); list markers
belong to the following sentence; scope rules per lens; seeded, section-stratified, reproducible sampling."""
from __future__ import annotations

import unittest

from tests.skills.hep_authoring import review_harness as H
from review_lib import units as U

SPEC = H.PLUGIN / "docs" / "dev" / "independent-review-spec.md"
EXTRA = """# Small

Intro sentence one. Intro sentence two? 第三句。第四句；
- item one with `code.py` path.
- item two

---

| a | b |
|---|---|
| 1 | 2 |

    indented code block line
"""


def docs():
    return {"spec": SPEC.read_text(encoding="utf-8"), "fixture": H.DOC, "extra": EXTRA}


class SplitTests(unittest.TestCase):
    def test_every_unit_is_a_contiguous_excerpt(self):
        for name, text in docs().items():
            units = U.split_markdown(text)
            self.assertTrue(units, name)
            norm = U.norm_ws(text)
            for u in units:
                with self.subTest(doc=name, unit=u["id"]):
                    self.assertIn(u["text"], text)
                    self.assertIn(U.norm_ws(u["text"]), norm)
                    self.assertEqual(u["text_sha256"], U.sha256_text(u["text"]))

    def test_indented_code_fence_in_a_list_item_is_one_unit(self):
        units = U.split_markdown(H.DOC)
        code = [u for u in units if u["kind"] == "code"]
        self.assertEqual(len(code), 1)
        self.assertIn("Read and follow the instruction file below exactly.", code[0]["text"])
        self.assertIn("REVIEW-DISPATCH nonce=<nonce>", code[0]["text"])
        spec_code = [u for u in U.split_markdown(docs()["spec"]) if "REVIEW-DISPATCH nonce=<nonce> instructions" in u["text"]]
        self.assertEqual([u["kind"] for u in spec_code], ["code"])

    def test_list_markers_belong_to_the_sentence(self):
        units = U.split_markdown(H.DOC)
        texts = [u["text"] for u in units]
        self.assertIn("1. Run start, then next until it says stop.", texts)
        self.assertFalse(any(t.strip() in ("1.", "2.", "-", "*") for t in texts))

    def test_punctuation_only_fragments_merge_into_the_previous_unit(self):
        units = U.split_markdown(EXTRA)
        self.assertFalse(any(set(u["text"].strip()) <= set("-|: ") for u in units))
        header = next(u for u in units if u["text"].startswith("| a | b |"))
        self.assertIn("|---|---|", header["text"])
        self.assertTrue(any(u["text"].endswith("---") for u in units))

    def test_sentence_ends(self):
        texts = [u["text"] for u in U.split_markdown(EXTRA)]
        for t in ("Intro sentence one.", "Intro sentence two?", "第三句。", "第四句；"):
            self.assertIn(t, texts)

    def test_kinds_and_sections(self):
        units = U.split_markdown(H.DOC)
        self.assertEqual(units[0]["kind"], "heading")
        row = next(u for u in units if u["text"].startswith("| 2 |"))
        self.assertEqual((row["kind"], row["section"]), ("table-row", "2. Rules"))


class SubstantiveAndScopeTests(unittest.TestCase):
    def unit(self, text, kind="sentence"):
        u = {"id": "U0001", "section": "s", "kind": kind, "text": text}
        u["substantive"] = U.substantive(u)
        return u

    def test_substantive(self):
        self.assertFalse(self.unit("## 3 Rules", "heading")["substantive"])
        self.assertFalse(self.unit("1. Run start, then next until it says stop.")["substantive"])
        for t in ("The limit is 5 units.", "Use `next`.", "See https://example.org.", "審查必須完成。", "It must hold.",
                  "Read skills/hep-authoring/SKILL.md first."):
            self.assertTrue(self.unit(t)["substantive"], t)

    def test_scope(self):
        facts = self.unit("The header is at `LICENSE:2-3`.")
        self.assertTrue(U.in_scope(facts, "facts"))
        self.assertTrue(U.in_scope(facts, "sources"))
        self.assertTrue(U.in_scope(self.unit("Set `CLAUDE_CODE_FORK_SUBAGENT` to 0."), "facts", ["CLAUDE_CODE_FORK_SUBAGENT"]))
        self.assertFalse(U.in_scope(self.unit("Use the `nonexistent_file.py` helper."), "facts"))
        quoted = self.unit('The term "review packet" is used here.')
        self.assertFalse(U.in_scope(quoted, "sources"))
        self.assertTrue(U.in_scope(self.unit("According to the `routing-contract` document, it is so."), "sources"))
        self.assertTrue(U.in_scope(self.unit("依路由文件，必須如此。"), "sources"))
        self.assertTrue(U.in_scope(quoted, "design"))
        self.assertTrue(U.in_scope(self.unit("It must hold."), "bypass"))
        self.assertTrue(U.in_scope(self.unit("See `finding_shape` in the rules."), "bypass"))
        self.assertFalse(U.in_scope(self.unit("Use `next`."), "bypass"))
        self.assertTrue(U.in_scope(self.unit("The ECAL energy scale is 1.02."), "calo", keywords=["ECAL"]))

    def test_domain_lens_added_by_keyword(self):
        table = {"facts": {"fixed": True}, "calo": {"fixed": False, "keywords": ["ECAL"]}}
        self.assertEqual(U.active_lenses("no match here", table), ["facts"])
        self.assertEqual(U.active_lenses("the ECAL scale", table), ["facts", "calo"])
        self.assertEqual(U.active_lenses("x", table, ["calo"]), ["facts", "calo"])


class SamplingTests(unittest.TestCase):
    def test_reproducible_and_stratified(self):
        units = U.unit_table(SPEC.read_text(encoding="utf-8"), ["design"], {}, ())
        cand = [u["id"] for u in units if u["in_scope"]["design"]]
        a = U.sample_deep(units, cand, 15, U.derive("1", "deep", "design"))
        self.assertEqual(a, U.sample_deep(units, cand, 15, U.derive("1", "deep", "design")))
        self.assertNotEqual(a, U.sample_deep(units, cand, 15, U.derive("2", "deep", "design")))
        self.assertEqual(len(a), 15)
        sec = {u["id"]: u["section"] for u in units}
        self.assertEqual(len({sec[x] for x in a}), 15)  # more sections than draws: one unit per section
        self.assertEqual(a, sorted(a))

    def test_all_when_few(self):
        units = U.unit_table(H.DOC, ["facts"], {}, ())
        cand = [u["id"] for u in units if u["in_scope"]["facts"]]
        self.assertEqual(U.sample_deep(units, cand, 15, "ab" * 32), cand)

    def test_top_up(self):
        units = U.unit_table(H.DOC, ["design"], {}, ())
        cand = [u["id"] for u in units if u["in_scope"]["design"]]
        out = U.top_up(units, cand[:2], cand, 5, "cd" * 32)
        self.assertEqual(len(out), 5)
        self.assertTrue(set(cand[:2]) <= set(out))


if __name__ == "__main__":
    unittest.main()
