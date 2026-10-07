"""Static routing scenarios (no model call): a generic DIS request needs no profile; an explicit EIC facility or
ePIC detector request resolves to the one module the index names; a detector request with no configuration asks;
an unrelated experiment loads no eic file. Decisions come from contracts/project.py; files from index.md."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT.parents[2]
sys.path.insert(0, str(PLUGIN))
from contracts.project import resolve_context  # noqa: E402

SCENARIOS = json.loads((ROOT / "benchmarks" / "routing-scenarios.json").read_text(encoding="utf-8"))["scenarios"]
INDEX = (ROOT / "index.md").read_text(encoding="utf-8")


def index_files(keyword):
    """Files the index tells a reader to open for the row whose Request cell contains keyword."""
    for line in INDEX.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 2 and keyword.lower() in cells[0].lower():
            return re.findall(r"`([a-z0-9_./-]+\.(?:md|json))`", cells[1])
    raise AssertionError(f"no index row mentions {keyword!r}")


class ScenarioTests(unittest.TestCase):
    def test_five_scenarios_with_distinct_ids(self):
        ids = [s["id"] for s in SCENARIOS]
        self.assertEqual(sorted(ids), sorted(["generic-dis", "eic-facility", "epic-detector", "ambiguous-detector", "unrelated-experiment"]))

    def test_decisions(self):
        for s in SCENARIOS:
            with self.subTest(s["id"]):
                out = resolve_context({"experiments": s["explicit_profiles"], "theory": []}, None, s["needs_profile"])
                self.assertEqual(out["decision"], s["expected_decision"])
                if s["expected_decision"] == "use":
                    self.assertEqual(out["experiments"], s["explicit_profiles"])

    def test_eic_files_only_when_eic_is_selected(self):
        for s in SCENARIOS:
            with self.subTest(s["id"]):
                selected = "experiment:eic" in s["explicit_profiles"]
                files = index_files(s["index_row_keyword"]) if selected else []
                self.assertEqual(files, s["expected_eic_files"])
                for f in files:
                    self.assertTrue((ROOT / f).is_file(), f)

    def test_facility_and_detector_resolve_to_different_single_modules(self):
        fac = next(s for s in SCENARIOS if s["id"] == "eic-facility")["expected_eic_files"]
        det = next(s for s in SCENARIOS if s["id"] == "epic-detector")["expected_eic_files"]
        self.assertEqual(len(fac), 1)
        self.assertEqual(len(det), 1)
        self.assertNotEqual(fac, det)
        self.assertIn("facility/", fac[0])
        self.assertIn("detector/", det[0])

    def test_ambiguous_detector_request_asks_and_the_index_says_why(self):
        amb = next(s for s in SCENARIOS if s["id"] == "ambiguous-detector")
        self.assertEqual(amb["expected_decision"], "ask")
        self.assertEqual(amb["expected_eic_files"], [])
        perf_line = next(l for l in INDEX.splitlines() if "Detector performance" in l)
        self.assertIn("not shipped", perf_line)
        self.assertIn("ask", perf_line)
        self.assertIn("geometry release", perf_line)

    def test_generic_dis_routes_away_from_the_profile(self):
        dis_line = next(l for l in INDEX.splitlines() if "Generic DIS" in l)
        self.assertIn("not this profile", dis_line)
        self.assertIn("hep-theory", dis_line)
        self.assertTrue((PLUGIN / "skills" / "hep-theory" / "SKILL.md").is_file())

    def test_expected_owner_is_a_shipped_skill_whose_description_mentions_a_trigger(self):
        for s in SCENARIOS:
            with self.subTest(s["id"]):
                skill = PLUGIN / "skills" / s["expected_owner"] / "SKILL.md"
                self.assertTrue(skill.is_file(), s["expected_owner"])
                desc = re.search(r'^description:\s*"(.*)"\s*$', skill.read_text(encoding="utf-8"), re.M).group(1).lower()
                self.assertTrue(any(t.lower() in desc for t in s["triggers"]), (s["id"], s["triggers"]))


if __name__ == "__main__":
    unittest.main()
