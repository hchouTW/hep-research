"""adapters/hepdata: HEPData table -> dataset-record, on synthetic tables only."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "adapters" / "hepdata" / "assets" / "hepdata_record.py"
FIX = PLUGIN / "tests" / "adapters" / "fixtures" / "hepdata"
sys.path.insert(0, str(PLUGIN))
from contracts.validate import validate_artifact  # noqa: E402


class HepdataRecordTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tmp = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def run_adapter(self, *extra, table=FIX / "synthetic-table.json", status="synthetic"):
        out = self.tmp / f"out{len(list(self.tmp.iterdir()))}"
        cmd = [sys.executable, str(SCRIPT), "--table", str(table), "--observable", str(FIX / "synthetic-observable.json"),
               "--record", "synthetic", "--table-name", "Table 1", "--status", status, "--created", "2026-10-07",
               "--out", str(out), *extra]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return proc, out

    def write(self, name, doc):
        p = self.tmp / name
        p.write_text(json.dumps(doc), encoding="utf-8")
        return p

    def test_record_is_valid_and_keeps_identifiers(self):
        proc, out = self.run_adapter()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        doc = json.loads((out / "dataset-record.json").read_text())
        self.assertEqual(validate_artifact(doc).errors, [])
        ext = doc["extension"]
        self.assertEqual(ext["data"]["edges"], [-0.9, -0.3, 0.3, 0.9])
        self.assertEqual(ext["observable"]["external_ids"]["hepdata"], "synthetic / Table 1")
        self.assertEqual(ext["covariance"]["status"], "absent")
        comps = {c["name"]: c for c in ext["data"]["uncertainties"]}
        self.assertAlmostEqual(comps["sys,lumi"]["values"][0], 8.4)  # 2% of 420
        self.assertFalse(comps["sys,model (+)"]["gaussian"])
        self.assertEqual(comps["sys,model (-)"]["values"][2], 7.0)
        self.assertIn("not given in bins [0, 1]", comps["sys,model (+)"]["note"])
        self.assertIn("not given in bins [2]", comps["sys,lumi"]["note"])
        self.assertTrue(all(c["correlation"] == "unknown" for c in comps.values()))

    def test_correlation_and_covariance_tables_give_the_same_matrix(self):
        mats = []
        for kind in ("correlation", "covariance"):
            proc, out = self.run_adapter("--covariance", str(FIX / f"synthetic-{kind}.json"), "--covariance-of", "stat")
            self.assertEqual(proc.returncode, 0, proc.stdout)
            doc = json.loads((out / "dataset-record.json").read_text())
            self.assertEqual(doc["extension"]["covariance"]["status"], "present")
            comps = {c["name"]: c for c in doc["extension"]["data"]["uncertainties"]}
            self.assertEqual(comps["stat"]["correlation"], "covariance")
            self.assertEqual(comps["sys,lumi"]["correlation"], "unknown")
            mats.append(json.loads((out / doc["extension"]["covariance"]["ref"]).read_text())["matrix"])
        for r, s in zip(*mats):
            for x, y in zip(r, s):
                self.assertAlmostEqual(x, y, places=9)

    def test_entries_are_placed_by_labels_not_file_order(self):
        cov = json.loads((FIX / "synthetic-covariance.json").read_text())
        perm = list(reversed(range(9)))
        for iv in cov["independent_variables"]:
            iv["values"] = [iv["values"][k] for k in perm]
        cov["dependent_variables"][0]["values"] = [cov["dependent_variables"][0]["values"][k] for k in perm]
        proc, out = self.run_adapter("--covariance", str(self.write("rev.json", cov)), "--covariance-of", "stat")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        m = json.loads((out / "Table-1-covariance.json").read_text())["matrix"]
        for got, want in zip([m[0][0], m[1][1], m[2][2], m[0][1]], [144.0, 100.0, 156.25, 24.0]):
            self.assertAlmostEqual(got, want, places=9)

    def test_refusals(self):
        corr = FIX / "synthetic-correlation.json"
        cases = {
            "correlation without --covariance-of": ("--covariance", str(corr)),
            "asymmetric error named": ("--covariance", str(corr), "--covariance-of", "sys,model (+)"),
            "unknown label": ("--covariance", str(corr), "--covariance-of", "stat;nope"),
        }
        for why, extra in cases.items():
            with self.subTest(why):
                proc, _ = self.run_adapter(*extra)
                self.assertEqual(proc.returncode, 1, proc.stdout)
                self.assertIn("covariance-of", proc.stdout)

    def test_refuses_published_without_evidence(self):
        proc, _ = self.run_adapter(status="published")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("--evidence-id", proc.stdout)

    def test_refuses_gaps_wrong_size_asymmetry_and_non_psd(self):
        table = json.loads((FIX / "synthetic-table.json").read_text())
        gap = copy.deepcopy(table)
        gap["independent_variables"][0]["values"][1]["low"] = -0.2
        proc, _ = self.run_adapter(table=self.write("gap.json", gap))
        self.assertIn("not contiguous", proc.stdout)
        cov = json.loads((FIX / "synthetic-covariance.json").read_text())
        variants = {}
        small = copy.deepcopy(cov)
        for part in [*small["independent_variables"], small["dependent_variables"][0]]:
            part["values"] = part["values"][:4]
        variants["4 entries for 3 bins"] = (small, "entries for 3 bins")
        asym = copy.deepcopy(cov)
        asym["dependent_variables"][0]["values"][1]["value"] = 30.0
        variants["asymmetric"] = (asym, "not symmetric")
        npsd = copy.deepcopy(cov)
        for k in (1, 3):
            npsd["dependent_variables"][0]["values"][k]["value"] = 500.0
        variants["not PSD"] = (npsd, "positive semidefinite")
        for why, (doc, msg) in variants.items():
            with self.subTest(why):
                proc, _ = self.run_adapter("--covariance", str(self.write(f"{len(why)}.json", doc)), "--covariance-of", "stat")
                self.assertEqual(proc.returncode, 1, proc.stdout)
                self.assertIn(msg, proc.stdout)


if __name__ == "__main__":
    unittest.main()
