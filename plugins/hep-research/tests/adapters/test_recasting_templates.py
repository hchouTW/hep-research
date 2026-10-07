"""adapters/recasting templates (T20): declared `documented` (no tool was run), each with its placeholders, and each
file well-formed as far as can be checked without the tool (INI parses, braces balance, Rivet names agree)."""
import configparser
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "recasting"
ASSETS = ADAPTER / "assets"


class RecastingTemplateTests(unittest.TestCase):
    def test_declared_documented_with_no_versions(self):
        doc = json.loads((ADAPTER / "adapter.json").read_text())
        self.assertEqual(doc["status"], "documented")
        self.assertTrue(all(t["status"] == "documented" and not t["tested_versions"] for t in doc["tools"]))
        for a in doc["assets"]:
            self.assertTrue((ADAPTER / a).is_file(), a)
        self.assertIn("documented", (ROOT / "skills" / "hep-theory" / "references" / "recasting-toolchain.md").read_text())

    def test_every_template_says_what_it_is_and_has_placeholders(self):
        for path in ASSETS.iterdir():
            text = path.read_text()
            self.assertIn("TEMPLATE", text.upper(), path.name)
            if path.suffix == ".cc":
                self.assertIn("TEMPLATE_ANALYSIS", text)  # the class name is the placeholder to replace
            elif path.suffix != ".ini":
                self.assertRegex(text, r"<[A-Z_ ]+>", path.name)

    def test_madgraph_card_order(self):
        lines = [l.split("#")[0].strip() for l in (ASSETS / "mg5_proc_card.dat").read_text().splitlines()]
        steps = [l.split()[0] for l in lines if l]
        for earlier, later in (("import", "generate"), ("generate", "output"), ("output", "launch"), ("launch", "done")):
            self.assertLess(steps.index(earlier), steps.index(later), (earlier, later))

    def test_rivet_skeleton_is_consistent(self):
        cc = (ASSETS / "rivet_template_analysis.cc").read_text()
        self.assertEqual(cc.count("{"), cc.count("}"))
        self.assertEqual(cc.count("("), cc.count(")"))
        name = re.search(r"class (\w+) : public Analysis", cc).group(1)
        self.assertIn(f"RIVET_DECLARE_PLUGIN({name})", cc)
        self.assertIn(f"Name: {name}", (ASSETS / "rivet_template_analysis.info").read_text())

    def test_smodels_parameters_parse(self):
        cfg = configparser.ConfigParser(inline_comment_prefixes=(";",))
        cfg.read(ASSETS / "smodels_parameters.ini")
        self.assertEqual(set(cfg.sections()), {"options", "parameters", "particles", "database", "printer"})
        self.assertGreater(float(cfg["parameters"]["sigmacut"]), 0.0)

    def test_delphes_and_ma5_fragments(self):
        tcl = (ASSETS / "delphes_efficiency_override.tcl").read_text()
        self.assertEqual(tcl.count("{"), tcl.count("}"))
        self.assertIn("set EfficiencyFormula", tcl)
        ma5 = (ASSETS / "ma5_recast.ma5").read_text()
        self.assertIn("set main.recast = on", ma5)
        self.assertLess(ma5.index("import "), ma5.index("submit "))


if __name__ == "__main__":
    unittest.main()
