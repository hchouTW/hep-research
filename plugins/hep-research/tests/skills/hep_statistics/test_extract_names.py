"""skills/hep-statistics/scripts/extract_names.py (semantic naming N10): datacard, pyhf workspace and
statistical-result names, and the shape histograms a nuisance derives through the shapes lines."""
from __future__ import annotations

import unittest

from tests.skills.naming_extractor_helpers import ProjectCase

CARD = """imax 1
jmax 1
kmax *
shapes * * shapes.root $PROCESS $PROCESS_$SYSTEMATIC
shapes data_obs * shapes.root data_obs
bin ch_a
observation -1
bin ch_a ch_a
process ttbar dy
process 0 1
rate -1 -1
lumi_2018 lnN 1.02 1.02  # luminosity
jes shape 1 -
r_dy rateParam ch_a dy 1
"""
WORKSPACE = {"version": "1.0.0", "channels": [{"name": "sr", "samples": [
    {"name": "signal", "data": [1], "modifiers": [{"name": "mu", "type": "normfactor", "data": None},
                                                  {"name": "lumi", "type": "lumi", "data": None}]},
    {"name": "bkg", "data": [2], "modifiers": [{"name": "lumi", "type": "lumi", "data": None},
                                               {"name": "bkg_norm", "type": "normsys", "data": {"hi": 1.1, "lo": 0.9}}]}]}],
    "observations": [{"name": "sr", "data": [3]}],
    "measurements": [{"name": "meas", "config": {"poi": "mu", "parameters": []}}]}


class N10Tests(ProjectCase):
    SKILL = "hep-statistics"

    def test_datacard_names_and_derived_shapes(self):
        self.write("cards/ch_a.txt", CARD)
        code, inv = self.extract("N10")
        self.assertEqual(code, 0)
        kinds = {(e["entity_kind"], e["name"]) for e in inv["entities"]}
        self.assertLessEqual({("channel", "ch_a"), ("process", "ttbar"), ("process", "dy"), ("nuisance", "lumi_2018"),
                              ("nuisance", "jes"), ("rate_parameter", "r_dy"), ("observed_data", "data_obs")}, kinds)
        jes = self.entity(inv, "jes")
        self.assertEqual({t["name"] for t in jes["targets"]}, {"ttbar_jesUp", "ttbar_jesDown"})  # dy has '-'
        self.assertTrue(all(t["file"] == "cards/shapes.root" and t["derived"] for t in jes["targets"]))
        self.assertEqual(self.entity(inv, "ttbar", "process")["targets"][0]["name"], "ttbar")
        self.assertEqual(self.entity(inv, "data_obs")["source"], "external")
        self.assertEqual(self.entity(inv, "lumi_2018")["scope"]["container"], "ch_a")

    def test_pyhf_workspace(self):
        self.write("ws.json", WORKSPACE)
        _, inv = self.extract("N10")
        kinds = {(e["entity_kind"], e["name"]) for e in inv["entities"]}
        self.assertLessEqual({("poi", "mu"), ("channel", "sr"), ("process", "signal"), ("nuisance", "lumi"),
                              ("nuisance", "bkg_norm")}, kinds)
        self.assertEqual(self.names(inv).count("lumi"), 1)  # one entity per channel and modifier

    def test_statistical_result_and_nothing_to_read(self):
        code, inv = self.extract("N10")
        self.assertEqual((code, inv["inputs_scanned"]), (3, 0))
        self.write("art/fit.json", {"artifact_type": "statistical-result", "artifact_id": "fit1", "status": "asimov",
                                    "extension": {"parameters_of_interest": ["mu"], "nuisances": [{"name": "jes"}]}})
        _, inv = self.extract("N10")
        self.assertEqual(self.entity(inv, "jes")["meaning"]["status_label"], "asimov")


if __name__ == "__main__":
    unittest.main()
