"""skills/hep-measurement/scripts/extract_names.py (semantic naming N7, N8, N9): yield tables, systematics ledgers,
measurement-spec and dataset-record names, status labels and official dataset ids of a bound profile."""
from __future__ import annotations

import unittest

from tests.skills.naming_extractor_helpers import ProjectCase

SPEC = {"artifact_type": "measurement-spec", "artifact_id": "ms1", "status": "synthetic", "extension": {
    "selections": [{"name": "sr_final", "definition": "m > 500", "conditional_denominator": "all"}],
    "backgrounds": [{"name": "ttbar", "estimator": "cr", "control_region": "cr_emu"}],
    "systematics": [{"name": "jes", "source": "calibration", "effect": "shape", "applied_via": "rerun"}],
    "eras": [{"id": "run_2018", "start": 1, "end": 2, "kind": "configuration", "source": "log"}]}}


class MeasurementTests(ProjectCase):
    SKILL = "hep-measurement"

    def setUp(self):
        super().setUp()
        self.write("yields.csv", "region,sample,yield\nsr,ttbar,1\nsr,synthcol:synthetic-path-b-dsigma,2\ncr,ttbar,3\n")
        self.write("syst.csv", "name,source,effect,applied_via,affected_processes,correlation_key,payload,validation\n"
                               "lumi_2018,lumi,normalization,scale,all,lumi,x,y\n")
        self.write("art/spec.json", SPEC)

    def test_n7_samples_eras_and_official_ids(self):
        self.write("hep-research.project.json", {"schema_version": "1.3.0", "experiments": ["experiment:synthetic-collider"]})
        _, inv = self.extract("N7")
        self.assertEqual(self.names(inv, "internal_alias"), ["ttbar", "synthcol:synthetic-path-b-dsigma"])
        self.assertEqual(self.entity(inv, "synthcol:synthetic-path-b-dsigma")["source"], "external")
        self.assertEqual(self.entity(inv, "ttbar")["source"], "project")
        self.assertEqual(self.names(inv, "run_range"), ["run_2018"])

    def test_n8_regions_and_selections_carry_the_status(self):
        _, inv = self.extract("N8")
        self.assertEqual(set(self.names(inv)), {"sr", "cr", "sr_final", "cr_emu"})
        self.assertEqual(self.entity(inv, "sr_final")["meaning"]["status_label"], "synthetic")

    def test_n9_ledger_and_spec(self):
        _, inv = self.extract("N9")
        self.assertEqual(set(self.names(inv, "variation")), {"lumi_2018", "jes"})


if __name__ == "__main__":
    unittest.main()
