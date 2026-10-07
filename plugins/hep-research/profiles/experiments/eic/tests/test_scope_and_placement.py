"""Content-ownership tests: every module declares its scope (EIC facility, ePIC, or none) and the skill that owns the
general method; the placement inventory covers every module; no module copies general DIS identities or names
another profile's path; the detector module refuses to supply performance numbers."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT.parents[2]
MODULES = sorted(p for p in (ROOT / "modules").rglob("*.md") if p.name != "placement-inventory.md")
INVENTORY = (ROOT / "modules" / "placement-inventory.md").read_text(encoding="utf-8")
SKILLS = {"hep-analysis", "detector-response", "hep-theory", "hep-statistics", "hep-computing", "physics-ml", "research-communication"}
PLACEMENTS = {"general HEP method", "EIC facility context", "ePIC configuration", "project-local"}


def rows(table_text):
    out = []
    for line in table_text.splitlines():
        if line.startswith("|") and not line.startswith("|---") and "Content" not in line.split("|")[1]:
            out.append([c.strip() for c in line.strip().strip("|").split("|")])
    return out


class OwnerHeaderTests(unittest.TestCase):
    def test_every_module_names_scope_and_method_owner(self):
        for f in MODULES:
            text = f.read_text(encoding="utf-8")
            m = re.search(r"^> Method owner: (none|\[([a-z-]+)\]\(([^)]+)\))", text, re.M)
            self.assertIsNotNone(m, f.name)
            if m.group(2):
                self.assertIn(m.group(2), SKILLS, f.name)
                target = (f.parent / m.group(3)).resolve()
                self.assertTrue(target.is_file(), (f.name, m.group(3)))
                self.assertEqual(target.parent.name, m.group(2), f.name)
            if f.parent.name in ("facility", "detector"):
                s = re.search(r"^> Scope: (EIC facility|ePIC experiment)\b", text, re.M)
                self.assertIsNotNone(s, f.name)
                expected = "EIC facility" if f.parent.name == "facility" else "ePIC experiment"
                self.assertEqual(s.group(1), expected, f.name)


class InventoryTests(unittest.TestCase):
    def test_inventory_covers_every_module_file(self):
        linked = " ".join(r[4] for r in rows(INVENTORY))
        for f in MODULES:
            self.assertIn(f.relative_to(ROOT / "modules").as_posix(), linked, f.name)

    def test_every_row_has_a_known_placement_and_owner(self):
        for r in rows(INVENTORY):
            self.assertEqual(len(r), 5, r)
            self.assertIn(r[1], PLACEMENTS, r)
            owner = r[2]
            self.assertTrue(owner in SKILLS or owner in ("profile:eic", "project"), r)
            if r[1] == "general HEP method":
                self.assertIn(owner, SKILLS, r)
                self.assertIn("not in this profile", r[3].lower(), r)

    def test_general_dis_row_points_to_hep_theory_and_records_the_gap(self):
        dis = [r for r in rows(INVENTORY) if "DIS" in r[0]]
        self.assertTrue(dis)
        self.assertEqual(dis[0][2], "hep-theory")
        self.assertIn("follow-up", dis[0][3].lower())


class ContentBoundaryTests(unittest.TestCase):
    def test_no_dis_identities_in_the_profile(self):
        for f in MODULES:
            text = f.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"Q\^2\s*=\s*-", f.name)
            self.assertNotRegex(text, r"x_?B\s*=", f.name)
            self.assertNotRegex(text, r"\by\s*=\s*\(?p", f.name)

    def test_no_other_profile_path(self):
        for f in MODULES + [ROOT / "index.md", ROOT / "modules" / "placement-inventory.md"]:
            self.assertNotRegex(f.read_text(encoding="utf-8"), r"profiles/(experiments|theory)/(?!eic\b)", f.name)

    def test_detector_module_refuses_performance_numbers_and_asks(self):
        text = (ROOT / "modules" / "detector" / "epic-detector-context.md").read_text(encoding="utf-8").lower()
        self.assertIn("no performance number", text)
        self.assertIn("geometry release", text)
        self.assertIn("projection", text)
        self.assertNotIn("measured resolution", text)

    def test_facility_module_quotes_no_design_number(self):
        text = (ROOT / "modules" / "facility" / "eic-facility-context.md").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"\d+\s*(GeV|cm\^-2|%|mrad)")

    def test_plugin_root_paths_exist(self):
        for f in MODULES + [ROOT / "index.md"]:
            for rel in re.findall(r"<plugin root>/([A-Za-z0-9_./-]+)", f.read_text(encoding="utf-8")):
                self.assertTrue((PLUGIN / rel).exists(), (f.name, rel))


if __name__ == "__main__":
    unittest.main()
