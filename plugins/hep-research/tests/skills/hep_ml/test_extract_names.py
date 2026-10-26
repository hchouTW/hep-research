"""skills/hep-ml/scripts/extract_names.py (semantic naming N12): ml-artifact models and features, checkpoints."""
from __future__ import annotations

import unittest

from tests.skills.naming_extractor_helpers import ProjectCase


class N12Tests(ProjectCase):
    SKILL = "hep-ml"

    def test_models_features_checkpoints(self):
        self.write("art/ml.json", {"artifact_type": "ml-artifact", "artifact_id": "bdt_ttbar_vs_dy", "status": "synthetic",
                                   "extension": {"features": ["mu_pt", {"name": "jet_eta"}], "model_hash": "abc"}})
        self.write("models/ckpt_epoch040.pt", "x")
        _, inv = self.extract("N12")
        self.assertEqual(self.names(inv, "model_artifact"), ["bdt_ttbar_vs_dy"])
        self.assertEqual(self.names(inv, "feature"), ["mu_pt", "jet_eta"])
        self.assertEqual(self.names(inv, "checkpoint"), ["ckpt_epoch040.pt"])


if __name__ == "__main__":
    unittest.main()
