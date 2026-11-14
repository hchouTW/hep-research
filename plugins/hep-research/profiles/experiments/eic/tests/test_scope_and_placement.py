"""Content-ownership tests: every module declares its scope (EIC facility, ePIC, or none) and the skill that owns the
general method; the placement inventory covers every module; no module copies general DIS identities or names
another profile's path; the detector module refuses to supply performance numbers."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT.parents[2]
sys.path.insert(0, str(PLUGIN))
from contracts.skill_names import SKILLS as SKILL_NAMES  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import number_rules as nr  # noqa: E402

MODULES = sorted(p for p in (ROOT / "modules").rglob("*.md") if p.name != "placement-inventory.md")
INVENTORY = (ROOT / "modules" / "placement-inventory.md").read_text(encoding="utf-8")
SKILLS = set(SKILL_NAMES)  # the plugin's skill names (contracts/skill_names.py)
PLACEMENTS = {"general HEP method", "EIC facility context", "ePIC configuration", "project-local"}
CLAIMS = {c["id"]: c for c in json.loads((ROOT / "evidence" / "claims.json").read_text(encoding="utf-8"))}
FROZEN_SOFTWARE_MODULE = "epic-software-entry-points.md"
CONTENT = [p for p in MODULES if p.parent.name in ("facility", "detector")]
CHECKED = [p for p in CONTENT if p.name != FROZEN_SOFTWARE_MODULE]
SCOPE_PREFIX = {"facility": "eic facility:", "detector": "epic:"}


def rows(table_text):
    out = []
    for line in table_text.splitlines():
        if line.startswith("|") and not line.startswith("|---") and "Content" not in line.split("|")[1]:
            out.append([c.strip() for c in line.strip().strip("|").split("|")])
    return out


def scope_problems(folder, text, claims):
    """facility/ modules cite only 'EIC facility:' claims; detector/ modules only 'ePIC:' claims."""
    prefix = SCOPE_PREFIX[folder]
    return [cid for cid in sorted(set(nr.CITATION_PATTERN.findall(text)))
            if cid in claims and not claims[cid]["scope"]["text"].lower().startswith(prefix)]


def derived_mismatch(line):
    """Recompute a derived sqrt(s) line with its stated command; None when it reproduces to the digits written."""
    parts = nr.parse_derived(line)
    command = [sys.executable, str(PLUGIN / parts["script"])]
    for flag, value in parts["flags"].items():
        command += [f"--{flag}", value]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60, cwd=PLUGIN)
    computed = json.loads(result.stdout)["outputs"]["sqrt_s"]
    decimals = len(parts["value"].split(".")[1]) if "." in parts["value"] else 0
    written = float(parts["value"])
    return None if round(computed, decimals) == written else f"computed {computed}, written {parts['value']}"


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

    def test_every_number_appears_in_a_cited_numeric_claim(self):
        for f in CHECKED:
            self.assertEqual(nr.module_problems(f.read_text(encoding="utf-8"), CLAIMS), [], f.name)

    def test_derived_values_reproduce(self):
        for f in CHECKED:
            for _, line in nr.checked_lines(f.read_text(encoding="utf-8")):
                if nr.is_derived(line):
                    self.assertEqual(derived_mismatch(line), None, (f.name, line))

    def test_no_performance_numbers(self):
        for f in CHECKED:
            self.assertEqual(nr.performance_number_problems(f.read_text(encoding="utf-8")), [], f.name)

    def test_modules_cite_claims_of_their_own_scope(self):
        for f in CONTENT:
            self.assertEqual(scope_problems(f.parent.name, f.read_text(encoding="utf-8"), CLAIMS), [], f.name)

    def test_plugin_root_paths_exist(self):
        for f in MODULES + [ROOT / "index.md"]:
            for rel in re.findall(r"<plugin root>/([A-Za-z0-9_./-]+)", f.read_text(encoding="utf-8")):
                self.assertTrue((PLUGIN / rel).exists(), (f.name, rel))


class NumberRuleTests(unittest.TestCase):
    """Unit tests of the per-number algorithm (task section 7.4) on hand-written lines."""
    MAGNET = {"eic:C90": {"claim": "a 25 mrad crossing angle", "numeric_quotation_allowed": True,
                          "scope": {"text": "EIC facility: design target", "number_kind": "design-target"}},
              "eic:C91": {"claim": "18 GeV electrons on 275 GeV protons", "numeric_quotation_allowed": True,
                          "scope": {"text": "EIC facility: design target", "number_kind": "design-target"}},
              "eic:C92": {"claim": "only 18 GeV electrons", "numeric_quotation_allowed": True,
                          "scope": {"text": "EIC facility: design target", "number_kind": "design-target"}},
              "eic:C93": {"claim": "a 5 mrad angle", "numeric_quotation_allowed": True, "scope": {"text": "x"}}}

    def test_substring_does_not_match(self):
        self.assertEqual(nr.unsourced_numbers("- a 5 mrad angle (eic:C90)", self.MAGNET), [5.0])
        self.assertEqual(nr.unsourced_numbers("- a 25 mrad angle (eic:C90)", self.MAGNET), [])

    def test_claim_without_number_kind_cannot_source(self):
        self.assertEqual(nr.unsourced_numbers("- a 5 mrad angle (eic:C93)", self.MAGNET), [5.0])

    def test_superscripts(self):
        self.assertEqual(nr.normalise("10³³"), "10^33")
        self.assertEqual(nr.tokens("10³³ cm⁻² s⁻¹"), [1e33])

    def test_unit_exponents_yield_no_token(self):
        self.assertEqual(nr.tokens("cm^-2"), [])
        self.assertEqual(nr.tokens("10^34 cm^-2 s^-1"), [1e34])
        self.assertEqual(nr.tokens("1e34 cm-2 s-1"), [1e34])

    def test_symbol_exponent_and_words_with_digits(self):
        self.assertEqual(nr.tokens("low-Q² tagger"), [])
        self.assertEqual(nr.tokens("B0 spectrometer with PbWO₄ crystals"), [])

    def test_references_and_list_markers(self):
        self.assertEqual(nr.tokens("Chapter 8.3 of the draft Version 1"), [])
        self.assertEqual(nr.tokens("1. first item"), [])
        self.assertEqual(nr.tokens("§3.2.1 and Table 3.4"), [])
        self.assertEqual(nr.tokens("CHEP 2023 proceedings"), [])
        self.assertEqual(nr.tokens("1.7T"), [1.7])

    def test_years_and_counts_in_the_year_range(self):
        """Q12: a 1900-2099 number is a year unless a unit or a count word follows it."""
        self.assertEqual(nr.tokens("PDR draft, Dec 2024; in 2019; the 2021 Conceptual Design Report"), [])
        self.assertEqual(nr.tokens("2000 channels and 1920 towers"), [2000.0, 1920.0])
        self.assertEqual(nr.tokens("2024 SiPMs"), [2024.0])
        self.assertEqual(nr.tokens("a 2000 mm long vessel"), [2000.0])
        self.assertEqual(nr.unsourced_numbers("- read out by 2000 channels (eic:C90)", self.MAGNET), [2000.0])

    def test_scientific_notation(self):
        self.assertEqual(nr.tokens("2.0 x10^33"), [2e33])
        self.assertEqual(nr.tokens("2.0 x 10^33"), [2e33])

    def test_nuclides_and_signs(self):
        self.assertEqual(nr.tokens("Au-197"), [197.0])
        self.assertEqual(nr.tokens("¹⁹⁷Au"), [197.0])
        self.assertEqual(nr.tokens("η from -3.5"), [-3.5])
        self.assertEqual(nr.tokens("20-140 GeV"), [20.0, 140.0])

    def test_prose_line_is_checked(self):
        problems = nr.module_problems("A prose paragraph with 42 GeV and no claim.\n", self.MAGNET)
        self.assertEqual(len(problems), 1)

    def test_excluded_lines(self):
        text = ("| a | b |\n| --- | --- |\n```\n18x275 e+p\n```\n## General method\n\nSee page 99 of nothing.\n")
        self.assertEqual(nr.module_problems(text, self.MAGNET), [])

    def test_derived_line_is_routed_to_the_derived_rule(self):
        line = ("- derived: 140.7 GeV from eic:C91, eic:C90 via skills/hep-theory/scripts/dis_kinematics.py "
                "--E-lepton 18 --E-hadron 275 --M 0.93827208943 --crossing-angle-mrad 25 --x 0.1 --y 0.5")
        self.assertTrue(nr.is_derived(line))
        self.assertEqual(nr.module_problems(line + "\n", self.MAGNET), [])
        self.assertEqual(derived_mismatch(line), None)
        self.assertTrue(nr.derived_line_problems(line.replace("0.93827208943", "0.93827"), self.MAGNET))
        self.assertTrue(nr.derived_line_problems(line.replace("--E-lepton 18", "--E-lepton 10"), self.MAGNET))
        self.assertTrue(nr.derived_line_problems(line.replace("dis_kinematics.py", "no_such_script.py"), self.MAGNET))
        self.assertTrue(nr.derived_line_problems(line.replace("eic:C91, eic:C90", "eic:C93"), self.MAGNET))
        self.assertEqual(derived_mismatch(line.replace("140.7 GeV", "140.8 GeV")), "computed 140.7044034857381, written 140.8")

    def test_configuration_label_needs_both_numbers(self):
        self.assertEqual(nr.unsourced_numbers("- the 18x275 setting (eic:C91)", self.MAGNET), [])
        self.assertEqual(nr.unsourced_numbers("- the 18x275 setting (eic:C92)", self.MAGNET), [275.0])


class ContentDefectTests(unittest.TestCase):
    """Injected defects in copies of the shipped modules must be reported."""

    def detector_text(self):
        return (ROOT / "modules" / "detector" / "epic-detector-context.md").read_text(encoding="utf-8")

    def test_unsourced_number_in_a_module(self):
        text = self.detector_text().replace("1.7 tesla", "1.8 tesla")
        self.assertTrue(nr.module_problems(text, CLAIMS))

    def test_number_near_a_performance_word(self):
        text = self.detector_text() + "\nThe momentum resolution is 2 percent (eic:C03).\n"
        self.assertTrue(nr.performance_number_problems(text))

    def test_performance_word_far_from_numbers_passes(self):
        text = "- 1.7 tesla magnet (eic:C03)" + " " * 50 + "no resolution value is given\n"
        self.assertEqual(nr.performance_number_problems(text), [])

    def test_whole_line_tokenising_keeps_numbers_whole(self):
        line = "x" * 38 + " 195 " + "resolution"
        self.assertEqual([v for _, _, v in nr.spans(line)], [195.0])

    def test_claim_of_the_other_scope(self):
        text = self.detector_text() + "\n- facility claim cited here (eic:C06)\n"
        self.assertEqual(scope_problems("detector", text, CLAIMS), ["eic:C06"])


if __name__ == "__main__":
    unittest.main()
