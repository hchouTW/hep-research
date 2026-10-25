"""skills/hep-detector/scripts/extract_names.py (semantic naming N11): conditions tags are external, response
artifacts and their maps are project outputs."""
from __future__ import annotations

import unittest

from tests.skills.naming_extractor_helpers import ProjectCase


class N11Tests(ProjectCase):
    SKILL = "hep-detector"

    def test_tags_and_outputs(self):
        self.write("config.json", {"global_tag": "106X_upgrade2018_realistic_v16"})
        self.write("run.py", "process.GlobalTag.globaltag = 'auto_mc'\n")
        self.write("art/resp.json", {"artifact_type": "response", "artifact_id": "muon_response_2018",
                                     "status": "synthetic", "extension": {"matrix_ref": "maps/muon_eff.json",
                                                                          "conditions": "calib_v3"}})
        code, inv = self.extract("N11")
        self.assertEqual(code, 0)
        tags = {e["name"]: e["source"] for e in inv["entities"] if e["entity_kind"] == "conditions_tag"}
        self.assertEqual(tags, {"106X_upgrade2018_realistic_v16": "external", "auto_mc": "external", "calib_v3": "external"})
        self.assertEqual(set(self.names(inv, "project_output")), {"muon_response_2018", "muon_eff.json"})


if __name__ == "__main__":
    unittest.main()
