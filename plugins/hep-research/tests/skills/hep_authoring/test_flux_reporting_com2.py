"""Com2: the flux-measurement reporting policy adds refold_kit, collection_time_definition, bin_position,
variable_conversion and era. Each applies when the record's method says so; a missing one is then an unresolved
finding (the audit reports incomplete); records that do not declare those methods keep their results. Synthetic."""
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / "skills" / "hep-authoring" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from communication_lib.reporting import check_reporting, load_policy  # noqa: E402

POLICY = SCRIPTS.parent / "assets" / "reporting-policies.json"
ORIGINAL = ("quantity_and_unit", "binning", "exposure", "acceptance", "live_time", "unfolding",
            "statistical_uncertainty", "systematic_uncertainty", "scale_systematic", "period")
NEW = {"refold_kit": "forward_folding", "collection_time_definition": "time_dependent",
       "bin_position": "points_in_bins", "variable_conversion": "variable_converted", "era": "multi_era"}


def record(method, names):
    return {"result_type": "flux-measurement", "method": method,
            "fields": {n: {"state": "provided", "value": f"synthetic {n}"} for n in names}}


class FluxReportingCom2(unittest.TestCase):
    def setUp(self):
        self.pol = load_policy(POLICY)

    def test_new_fields_exist(self):
        self.assertTrue(set(NEW) <= set(self.pol["result_types"]["flux-measurement"]["fields"]))

    def test_existing_complete_record_keeps_its_result(self):
        rep = check_reporting(record({"platform": "orbital", "unfolded": True}, ORIGINAL), self.pol)
        self.assertEqual(rep["findings"], [])
        for name in NEW:
            self.assertEqual(rep["fields"][name]["state"], "not-applicable", name)

    def test_existing_incomplete_record_keeps_its_findings(self):
        rep = check_reporting(record({"platform": "ground", "unfolded": False}, ORIGINAL[:-1]), self.pol)
        self.assertEqual([(f["code"], f["location"]) for f in rep["findings"]], [("reporting.field_missing", "fields.period")])

    def test_declared_methods_make_the_new_fields_required(self):
        method = {"platform": "orbital", "unfolded": False, **{flag: True for flag in NEW.values()}}
        rep = check_reporting(record(method, ORIGINAL), self.pol)
        missing = {f["location"] for f in rep["findings"] if f["code"] == "reporting.field_missing"}
        self.assertEqual(missing, {f"fields.{n}" for n in NEW})
        self.assertTrue(all(f["severity"] == "unresolved" for f in rep["findings"]))
        rep = check_reporting(record(method, ORIGINAL + tuple(NEW)), self.pol)
        self.assertEqual(rep["findings"], [])


if __name__ == "__main__":
    unittest.main()
