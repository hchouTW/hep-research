"""Com3: the glossary template's collection-time, exposure (normalization), data-exposure (blinding), rigidity and
momentum entries, in English and Traditional Chinese.

Oracles: every normalization entry names an effect ID that exists in contracts/vocab/effects.json (exposure,
acceptance, livetime); check_terminology.py, run with the shipped template, warns on each mixed use (exposure in a
blinding context, an "exposure time", a momentum in GV, a rigidity in GeV/c, in both languages) and stays quiet on the
correct uses. All synthetic."""
from __future__ import annotations

import json
import unittest

from tests.skills.hep_writing import comm_fixtures as fx
from tests.skills.hep_writing.test_terminology import GLOSSARY_TEMPLATE, Base, load_glossary

EFFECTS = fx.PLUGIN / "contracts" / "vocab" / "effects.json"
NEW = ("term:collection-time", "term:exposure", "term:data-exposure", "term:rigidity", "term:momentum")


def template():
    return load_glossary(GLOSSARY_TEMPLATE)


class TemplateEntries(unittest.TestCase):
    def test_new_entries_exist_in_both_languages(self):
        entries = {e["id"]: e for e in template()["entries"]}
        for eid in NEW:
            with self.subTest(entry=eid):
                self.assertIn(eid, entries)
                self.assertEqual(set(entries[eid]["preferred"]), {"en", "zh-Hant"})

    def test_normalization_terms_name_catalog_effects(self):
        catalog = {e["effect_id"] for e in json.loads(EFFECTS.read_text(encoding="utf-8"))["effects"]}
        entries = {e["id"]: e for e in template()["entries"]}
        expected = {"term:exposure": "exposure", "term:acceptance": "acceptance", "term:collection-time": "livetime"}
        for eid, effect in expected.items():
            with self.subTest(entry=eid):
                self.assertEqual(entries[eid].get("effect_id"), effect)
                self.assertIn(effect, catalog)
        for e in entries.values():
            if "effect_id" in e:
                self.assertIn(e["effect_id"], catalog, e["id"])
        self.assertNotIn("effect_id", entries["term:data-exposure"], "data exposure is a blinding record, not a normalization")


class MixedUse(Base):
    MIXED = [
        ("Before unblinding, the exposure of the signal region was limited to 10 %.", "term:data-exposure"),
        ("The exposure time of each period is 3.2e6 s.", "term:collection-time"),
        ("Events above a momentum of 20 GV are kept.", "term:rigidity"),
        ("The rigidity threshold is 5 GeV/c.", "term:momentum"),
        ("解盲前，訊號區的曝露量限制在 10%。", "term:data-exposure"),
        ("動量高於 20 GV 的事件保留。", "term:rigidity"),
        ("剛度門檻為 5 GeV/c。", "term:momentum"),
    ]
    CLEAN = ("The exposure, acceptance times live time, is 1.2e7 m^2 sr s.\n"
             "The data exposure record lists every look at the signal region before unblinding.\n"
             "The collection time of the period is 3.2e6 s.\n"
             "Events above a rigidity of 20 GV are kept.\n"
             "The momentum threshold is 5 GeV/c.\n"
             "曝露量為接受度乘以活時間。\n"
             "資料曝光紀錄列出解盲前每一次查看。\n")

    def findings(self, text):
        rep = self.run_check(text, glossary=template())
        return [f for f in rep["findings"] if f["code"] == "terminology.concept_substitution"]

    def test_each_mixed_use_is_warned(self):
        for line, rule in self.MIXED:
            with self.subTest(line=line):
                found = self.findings("# Results\n\n" + line + "\n")
                self.assertIn(rule, {f["rule"] for f in found}, found)
                self.assertTrue(all(f["severity"] == "warning" for f in found))

    def test_correct_uses_are_not_warned(self):
        self.assertEqual(self.findings("# Results\n\n" + self.CLEAN), [])


if __name__ == "__main__":
    unittest.main()
