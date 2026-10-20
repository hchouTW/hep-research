"""hep-statistics evidence ledgers (docs/evidence/statistics): the source and claim ledger passes core/evidence/ledger.py
strictly, and every capability names an allowed status and gate and existing tests; experimental capabilities point
at code labelled EXPERIMENTAL."""
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.evidence.ledger import check_ledger  # noqa: E402

DIR = ROOT / "docs" / "evidence" / "statistics"


class StatisticsEvidence(unittest.TestCase):
    def test_source_and_claim_ledger(self):
        sources = json.loads((DIR / "sources.json").read_text())
        claims = json.loads((DIR / "claims.json").read_text())
        res = check_ledger(sources, claims, date(2026, 10, 21), 365)  # the latest verification (hepstats:S07)
        self.assertEqual(res["errors"], [], res["errors"])
        self.assertEqual(res["warnings"], [], res["warnings"])

    def test_capabilities(self):
        doc = json.loads((DIR / "capabilities.json").read_text())
        for c in doc["capabilities"]:
            with self.subTest(c["id"]):
                self.assertIn(c["status"], ("supported", "experimental", "unvalidated"))
                self.assertIn(c["gate"], ("pr", "scheduled", "release"))
                for t in c["tests"]:
                    self.assertTrue((ROOT / t).is_file(), t)
        experimental = {"eft-scans": "eft_scan.py", "discrete-profiling": "discrete_profile.py",
                        "global-significance": "global_significance.py", "pcl-efficiency-ratio": "pcl_efficiency_ratio.py",
                        "ratio-estimation": "ratio_estimation.py"}
        statuses = {c["id"]: c["status"] for c in doc["capabilities"]}
        for cid, script in experimental.items():
            self.assertEqual(statuses[cid], "experimental")
            self.assertIn("EXPERIMENTAL", (ROOT / "skills" / "hep-statistics" / "scripts" / script).read_text())


if __name__ == "__main__":
    unittest.main()
