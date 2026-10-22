"""v6.3 D11a: an operator of the old semantics table (differential-flux 1.0.0, which has no stages or member coverage)
is read through the coverage contract pinned in the semantic lock (V17). A coverage contract whose digest is not the
pinned one is not used to read the old table."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.recipe_semantics import canonical_sha256  # noqa: E402

TABLE = json.loads((ROOT / "contracts" / "semantics" / "tables" / "differential_flux.json").read_text())


def coverage():
    from contracts.effect_catalog import load_coverage
    return load_coverage("differential-flux")


class V17OldTableReader(unittest.TestCase):
    def test_operator_through_pinned_semantics(self):
        from contracts.analysis_checks.readers import read_table
        cov = coverage()
        res = read_table(TABLE, cov, pinned=canonical_sha256(cov))
        self.assertEqual((res["status"], res["reader"]), ("pinned", "differential-flux-1.0.0-via-coverage"))
        op = res["operators"]["divide_effective_exposure"]
        self.assertEqual(op["applies"], ["exposure", "efficiency"])  # the old table's own statement, unchanged
        self.assertEqual(op["stage"], "normalization")
        self.assertIsNone(op["class_coverage"]["efficiency"]["members"])
        self.assertNotIn("stage", TABLE["operators"][0], "the old table itself is never upgraded")

    def test_unpinned_or_changed_semantics_are_not_used(self):
        from contracts.analysis_checks.readers import read_table
        cov = coverage()
        changed = copy.deepcopy(cov)
        changed["operators"][0]["stage"] = "calibration"
        res = read_table(TABLE, changed, pinned=canonical_sha256(cov))
        self.assertEqual(res["status"], "mismatch")
        self.assertEqual(res["operators"], {})
        self.assertEqual(read_table(TABLE, cov, pinned=None)["status"], "unpinned")
        other = copy.deepcopy(TABLE)
        other["operators"][0]["meaning"] = "edited"
        self.assertEqual(read_table(other, cov, pinned=canonical_sha256(cov))["status"], "table_changed")


if __name__ == "__main__":
    unittest.main()
