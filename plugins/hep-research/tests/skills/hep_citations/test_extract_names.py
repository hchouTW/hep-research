"""skills/hep-citations/scripts/extract_names.py (semantic naming N17): literature record ids are external, and a
mistyped DOI fails the identifier format (C4: corrected in the ledger, never renamed)."""
from __future__ import annotations

import json
import unittest

from tests.skills.naming_extractor_helpers import ROOT, ProjectCase


class N17Tests(ProjectCase):
    SKILL = "hep-citations"

    def test_ids_and_format(self):
        self.write("art/lit.json", {"artifact_type": "literature-record", "artifact_id": "lit", "status": "unvalidated",
                                    "extension": {"sources": {"S01": {"id": "lit:S01", "title": "x", "verification_level": "a",
                                                                      "read_events": [], "identifiers": {
                                                                          "doi": "10.1103/PhysRevLett.114.171103.",
                                                                          "arxiv": "1503.04245", "inspire": None}}}}})
        code, inv = self.extract("N17")
        self.assertEqual(code, 0)
        self.assertTrue(all(e["source"] == "external" for e in inv["entities"]))
        self.assertEqual({e["entity_kind"] for e in inv["entities"]}, {"record_id", "doi", "arxiv_id"})
        import io
        from contextlib import redirect_stdout

        from contracts import naming_check
        with redirect_stdout(io.StringIO()) as buf:
            naming_check.main(["check", "--inventory", str(self.root / "naming/N17.json"), "--all"])
        rep = json.loads(buf.getvalue())
        bad = [f for f in rep["findings"] if f["rule_id"] == "naming.n17.identifier-format"]
        self.assertEqual([(f["current"], f["state"], f["action"]) for f in bad],
                         [("10.1103/PhysRevLett.114.171103.", "violated", "propose-alias")])
        self.assertTrue((ROOT / "skills/hep-citations/scripts/extract_names.py").is_file())


if __name__ == "__main__":
    unittest.main()
