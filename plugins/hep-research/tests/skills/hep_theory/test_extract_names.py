"""skills/hep-theory/scripts/extract_names.py (semantic naming N13): theory-spec parameters and scheme labels,
prediction parameter points."""
from __future__ import annotations

import unittest

from tests.skills.naming_extractor_helpers import ProjectCase


class N13Tests(ProjectCase):
    SKILL = "hep-theory"

    def test_parameters_and_schemes(self):
        self.write("art/th.json", {"artifact_type": "theory-spec", "artifact_id": "t1", "status": "unvalidated",
                                   "conventions": {"renormalization_scheme": "MSbar", "unit_system": "natural units"},
                                   "extension": {"parameters": {"alpha_s_mz": 0.118, "m_top_gev": 172.5}}})
        self.write("art/pred.json", {"artifact_type": "prediction", "artifact_id": "p1", "status": "unvalidated",
                                     "extension": {"parameter_point": {"alpha_s_mz": 0.118}}})
        _, inv = self.extract("N13")
        self.assertEqual(sorted(self.names(inv, "parameter")), ["alpha_s_mz", "alpha_s_mz", "m_top_gev"])
        self.assertEqual(self.names(inv, "scheme_label"), ["MSbar"])


if __name__ == "__main__":
    unittest.main()
