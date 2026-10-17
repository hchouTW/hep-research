"""import_published_table.py (Th8): a user-downloaded table (CSV, FITS, HEPData JSON or YAML) with declared columns,
units, edges and uncertainty breakdown becomes a dataset-record (status user-supplied) with a provenance sidecar.
Oracles: the values read back are identical to the source; the breakdown combined as declared reproduces the total,
or the difference is reported; missing optional readers exit 3. All tables are SYNTHETIC."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "import_published_table.py"
FIX = PLUGIN / "tests" / "adapters" / "fixtures" / "hepdata"
sys.path.insert(0, str(PLUGIN))
from contracts.validate import validate_artifact  # noqa: E402

OBSERVABLE = json.loads((FIX / "synthetic-observable.json").read_text(encoding="utf-8"))
CSV = """# SYNTHETIC table for tests; invented values
low,high,value,stat,sys_up,sys_down,total
-0.9,-0.3,420.0,12.0,9.0,7.0,15.0
-0.3,0.3,330.0,10.0,6.0,6.0,11.661903789690601
0.3,0.9,430.0,12.5,9.0,7.0,15.403246411
"""
SOURCE = {"url": "https://www.example.org/synthetic-table.csv", "downloaded": "2026-10-17",
          "citation": "SYNTHETIC: cite the paper that published the table"}


def spec(**over):
    s = {"dataset_id": "user:synthetic-angular", "observable": OBSERVABLE, "format": "csv",
         "columns": {"low": "low", "high": "high", "value": "value"},
         "uncertainties": [{"name": "stat", "kind": "statistical", "column": "stat"},
                           {"name": "sys", "kind": "systematic", "plus": "sys_up", "minus": "sys_down"}],
         "total": {"column": "total"}, "combination": "quadrature", "source": SOURCE}
    s.update(over)
    return s


class ImportPublishedTable(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.d = Path(self.td.name)
        self.csv = self.d / "table.csv"
        self.csv.write_text(CSV, encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def run_tool(self, table, sp, *extra, env=None):
        sp_path = self.d / f"spec{len(list(self.d.iterdir()))}.json"
        sp_path.write_text(json.dumps(sp), encoding="utf-8")
        out = self.d / f"out-{sp_path.stem}"
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--table", str(table), "--spec", str(sp_path),
                            "--created", "2026-10-17", "--out", str(out), *extra], capture_output=True, text=True,
                           timeout=600, env=env)
        doc = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {}
        return p.returncode, doc, out

    def test_csv_values_read_back_identical_and_record_valid(self):
        code, doc, out = self.run_tool(self.csv, spec())
        self.assertEqual(code, 0, doc)
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(doc["status_label"], "user-supplied")
        rec = json.loads((out / "dataset-record.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_artifact(rec).errors, [])
        self.assertEqual(rec["status"], ["user-supplied"])
        self.assertEqual(rec["extension"]["status"], "user-supplied")
        data = rec["extension"]["data"]
        self.assertEqual(data["values"], [420.0, 330.0, 430.0])
        self.assertEqual(data["edges"], [-0.9, -0.3, 0.3, 0.9])
        names = [c["name"] for c in data["uncertainties"]]
        self.assertEqual(names, ["stat", "sys (+)", "sys (-)"])
        self.assertEqual(data["uncertainties"][1]["values"], [9.0, 6.0, 9.0])
        self.assertFalse(data["uncertainties"][1]["gaussian"])
        self.assertEqual(rec["extension"]["covariance"]["status"], "absent")

    def test_provenance_sidecar(self):
        code, doc, out = self.run_tool(self.csv, spec())
        self.assertEqual(code, 0, doc)
        prov = json.loads((out / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(prov["sha256"], hashlib.sha256(self.csv.read_bytes()).hexdigest())
        self.assertEqual((prov["url"], prov["downloaded"]), (SOURCE["url"], SOURCE["downloaded"]))
        self.assertIn("cite", prov["citation_request"])
        self.assertFalse(prov["network_access"])

    def test_breakdown_reproduces_total_or_difference_reported(self):
        code, doc, _ = self.run_tool(self.csv, spec())
        tc = doc["total_check"]
        self.assertEqual(tc["rule"], "quadrature")
        self.assertTrue(tc["consistent"], tc)
        bad = CSV.replace("11.661903789690601", "14.0")
        self.csv.write_text(bad, encoding="utf-8")
        code, doc, _ = self.run_tool(self.csv, spec())
        self.assertEqual(code, 0)
        self.assertFalse(doc["total_check"]["consistent"])
        self.assertEqual(doc["total_check"]["bins_differing"], [1])
        self.assertTrue(any("total" in w for w in doc["warnings"]))
        code, doc, _ = self.run_tool(self.csv, spec(combination="linear"))
        self.assertEqual(doc["total_check"]["rule"], "linear")

    def test_hepdata_json(self):
        sp = spec(format="hepdata", columns=None, total=None,
                  uncertainties=[{"name": "stat", "kind": "statistical", "label": "stat"},
                                 {"name": "lumi", "kind": "systematic", "label": "sys,lumi"},
                                 {"name": "model", "kind": "systematic", "label": "sys,model"}])
        code, doc, out = self.run_tool(FIX / "synthetic-table.json", sp)
        self.assertEqual(code, 0, doc)
        rec = json.loads((out / "dataset-record.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["extension"]["data"]["values"], [420.0, 330.0, 430.0])
        lumi = [c for c in rec["extension"]["data"]["uncertainties"] if c["name"] == "lumi"][0]
        self.assertEqual(lumi["values"], [8.4, 6.6, 0.0])  # 2% of the value; not given in bin 2
        self.assertIn("not given", lumi["note"])

    def test_yaml_without_pyyaml_and_fits_without_astropy_exit_3(self):
        y = self.d / "table.yaml"
        y.write_text("independent_variables: []\n", encoding="utf-8")
        f = self.d / "table.fits"
        f.write_bytes(b"SIMPLE  =                    T")
        shadow = self.d / "shadow"
        shadow.mkdir()
        (shadow / "yaml.py").write_text("raise ImportError('hidden for this test')\n", encoding="utf-8")
        (shadow / "astropy.py").write_text("raise ImportError('hidden for this test')\n", encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=str(shadow), PYTHONDONTWRITEBYTECODE="1")
        code, doc, _ = self.run_tool(y, spec(format="hepdata", columns=None, total=None,
                                             uncertainties=[]), env=env)
        self.assertEqual(code, 3, doc)
        self.assertEqual(doc["status"], "missing-dependency")
        self.assertIn("PyYAML", doc["install"])
        code, doc, _ = self.run_tool(f, spec(format="fits", hdu=1), env=env)
        self.assertEqual(code, 3, doc)
        self.assertIn("astropy", doc["install"])

    def test_bad_input_exits_2(self):
        cases = [spec(source={"url": SOURCE["url"]}),                       # no download date or citation
                 spec(columns={"low": "low", "high": "high", "value": "nope"}),  # unknown column
                 spec(combination="average"),                                  # unknown rule
                 spec(uncertainties=[{"name": "stat", "kind": "statistical"}])]  # no column
        for sp in cases:
            with self.subTest(sp=sp):
                code, doc, _ = self.run_tool(self.csv, sp)
                self.assertEqual(code, 2, doc)
                self.assertEqual(doc["status"], "rejected")
        nonmono = CSV.replace("0.3,0.9", "0.2,0.9")
        self.csv.write_text(nonmono, encoding="utf-8")
        code, doc, _ = self.run_tool(self.csv, spec())
        self.assertEqual(code, 2, doc)  # bins must be contiguous

    def test_fits_with_astropy(self):
        try:
            from astropy.io import fits  # noqa: F401
            import numpy as np
        except ImportError:
            self.skipTest("astropy not installed")
        cols = [fits.Column(name=n, format="D", array=np.array(v)) for n, v in
                (("low", [-0.9, -0.3, 0.3]), ("high", [-0.3, 0.3, 0.9]), ("value", [420.0, 330.0, 430.0]),
                 ("stat", [12.0, 10.0, 12.5]), ("sys_up", [9.0, 6.0, 9.0]), ("sys_down", [7.0, 6.0, 7.0]))]
        path = self.d / "t.fits"
        fits.BinTableHDU.from_columns(cols).writeto(path)
        code, doc, out = self.run_tool(path, spec(format="fits", hdu=1, total=None))
        self.assertEqual(code, 0, doc)
        rec = json.loads((out / "dataset-record.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["extension"]["data"]["values"], [420.0, 330.0, 430.0])


if __name__ == "__main__":
    unittest.main()
