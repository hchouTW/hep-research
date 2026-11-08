"""The geometry reference cases without Geant4: every value cites a claim of a profile depended on, every case copies the task card's
tolerances, every case carries the label, an independence result, a negative control and a detection limit, and coverage.json lists every
module the cases use (g4sim plan, Sections 13, 19.2 S6)."""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT.parents[2]
sys.path.insert(0, str(PLUGIN))

from contracts import geometry  # noqa: E402

LABEL = "an approximate reconstruction from the cited claims, not the experiment's geometry"
GATE = PLUGIN / "adapters/geant4/tests/g4proto/s6_gates/cases_gate.py"


def gate():
    spec = importlib.util.spec_from_file_location("cases_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def claims() -> set:
    profile = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
    paths = {"reference:detector-atlas": "reference/detector-atlas", "experiment:ams-02": "experiments/ams-02", "experiment:eic": "experiments/eic"}
    return {c["id"] for p in profile["depends_on"] for c in json.loads((PLUGIN / "profiles" / paths[p] / "evidence/claims.json").read_text(encoding="utf-8"))}


class Cases(unittest.TestCase):
    def test_every_value_resolves_to_a_claim(self):
        ids = claims()
        for case in sorted((ROOT / "cases").iterdir()):
            with self.subTest(case=case.name):
                checked = geometry.check_file(case / "detector-spec.json", ids)
                self.assertEqual(checked["status"], "ok", checked.get("findings"))
                self.assertEqual(geometry.check_file(case / "detector-spec.json", set())["status"], "rejected")

    def test_every_case_copies_the_card(self):
        rows = gate().card_rows()
        for case in sorted((ROOT / "cases").iterdir()):
            document = json.loads((case / "case.json").read_text(encoding="utf-8"))
            registered = sorted((r["reference"], r["tolerance"]) for r in rows if r["case"].startswith(document["card_case"]))
            with self.subTest(case=case.name):
                self.assertTrue(registered)
                self.assertEqual(sorted((q["reference"], q["tolerance_relative"]) for q in document["quantities"]), registered)

    def test_every_case_states_what_section_13_asks(self):
        for case in sorted((ROOT / "cases").iterdir()):
            document = json.loads((case / "case.json").read_text(encoding="utf-8"))
            with self.subTest(case=case.name):
                self.assertEqual(document["label"], LABEL)
                self.assertIn(document["level"], ("L1", "L2", "L3"))
                for q in document["quantities"]:
                    self.assertIn("verified", q["independence"])
                    self.assertTrue(q["negative_control"]["change"])
                    self.assertIn("detection_limit_relative", q)
                if document["status"].startswith("validated-in-scope"):
                    self.assertTrue(all(q["independence"]["verified"] for q in document["quantities"]))
                    self.assertTrue(all(item["control_caught"] for item in document["result"]["quantities"]))

    def test_coverage_lists_every_module_used(self):
        coverage = json.loads((ROOT / "coverage.json").read_text(encoding="utf-8"))["modules"]
        for case in sorted((ROOT / "cases").iterdir()):
            spec = json.loads((case / "detector-spec.json").read_text(encoding="utf-8"))
            for node in [*spec["templates"].values(), spec["world"]]:
                if "solid" in node:
                    self.assertIn(case.name, coverage["shape:" + next(iter(node["solid"]))])
                for child in node.get("children", []):
                    self.assertIn(case.name, coverage["placement:" + next(iter(child["placement"]))])


if __name__ == "__main__":
    unittest.main()
