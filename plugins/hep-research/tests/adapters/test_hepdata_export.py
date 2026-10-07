"""adapters/hepdata/assets/hepdata_export.py (T21): a contract artifact written as a HEPData submission, read back by
hepdata_record.py with the same numbers, validated by hepdata-validator when installed, and its status kept."""
import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "hepdata" / "assets"
sys.path.insert(0, str(ASSETS))
import hepdata_export as hx  # noqa: E402
import hepdata_record as hr  # noqa: E402

EXAMPLE = ROOT / "examples" / "published-comparison"
RECORD = EXAMPLE / "synthetic-published-record.json"
FIXTURE = ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "dataset_record.json"
try:
    import yaml  # noqa: F401  # hepdata_record reads .yaml tables with PyYAML
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False
try:
    from hepdata_validator.full_submission_validator import FullSubmissionValidator
except ImportError:
    FullSubmissionValidator = None
try:
    import hepdata_lib  # noqa: F401
    HAVE_LIB = True
except ImportError:
    HAVE_LIB = False


def export(artifact, out, *extra):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = hx.main(["--artifact", str(artifact), "--out", str(out), "--table-name", "Table 5", *extra])
    return code, json.loads(buf.getvalue())


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "sub"

    def tearDown(self):
        self.tmp.cleanup()

    def test_files_and_status(self):
        code, rep = export(RECORD, self.out)
        self.assertEqual((code, rep["files"]), (0, ["submission.yaml", "Table_5.yaml", "Table_5-covariance.yaml"]))
        docs = [json.loads(d) for d in (self.out / "submission.yaml").read_text().split("---\n")]
        self.assertTrue(docs[0]["comment"].startswith("SYNTHETIC values, not a measurement."))
        self.assertEqual(docs[1]["keywords"][1], {"name": "phrases", "values": ["status: synthetic"]})
        table = json.loads((self.out / "Table_5.yaml").read_text())
        dep = table["dependent_variables"][0]
        self.assertEqual(dep["header"], {"name": "differential-cross-section", "units": "pb"})
        self.assertIn({"name": "Level", "value": "particle-fiducial"}, dep["qualifiers"])
        self.assertEqual(len(table["independent_variables"][0]["values"]), 10)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed: hepdata_record.py cannot read the YAML back")
    def test_round_trip_through_the_importer(self):
        self.assertEqual(export(RECORD, self.out)[0], 0)
        original = json.loads(RECORD.read_text())
        cov = json.loads((EXAMPLE / "synthetic-published-covariance.json").read_text())["matrix"]
        label = original["extension"]["data"]["uncertainties"][0]["name"] + ", from the covariance diagonal"
        opts = Namespace(table=self.out / "Table_5.yaml", observable=None, dependent=0, status="synthetic",
                         evidence_id=None, record="ins0", table_name="Table 5", dataset_id=None, created="2026-10-08",
                         covariance=self.out / "Table_5-covariance.yaml", covariance_of=[label])
        obs_file = Path(self.tmp.name) / "obs.json"
        obs = dict(original["extension"]["observable"])
        obs_file.write_text(json.dumps(obs))
        opts.observable = obs_file
        doc, cov_doc = hr.build(opts)
        self.assertEqual(doc["extension"]["data"]["values"], original["extension"]["data"]["values"])
        self.assertEqual(doc["extension"]["data"]["edges"], original["extension"]["data"]["edges"])
        for row_a, row_b in zip(cov_doc["matrix"], cov):
            for a, b in zip(row_a, row_b):
                self.assertAlmostEqual(a, b, delta=1e-12 * max(1.0, abs(b)))

    def test_per_bin_and_asymmetric_errors(self):
        doc = json.loads(FIXTURE.read_text())
        doc["extension"]["data"]["uncertainties"] += [
            {"name": "jes (+)", "kind": "systematic", "values": [0.2] * 4, "correlation": "fully-correlated", "gaussian": False},
            {"name": "jes (-)", "kind": "systematic", "values": [0.3] * 4, "correlation": "fully-correlated", "gaussian": False}]
        art = Path(self.tmp.name) / "a.json"
        art.write_text(json.dumps(doc))
        self.assertEqual(export(art, self.out)[0], 0)
        errs = json.loads((self.out / "Table_5.yaml").read_text())["dependent_variables"][0]["values"][0]["errors"]
        self.assertEqual(errs, [{"symerror": 0.1, "label": "stat"},
                                {"asymerror": {"plus": 0.2, "minus": -0.3}, "label": "jes"}])
        self.assertFalse((self.out / "Table_5-covariance.yaml").exists())  # covariance absent: no table invented

    def test_refusals(self):
        bad = json.loads(FIXTURE.read_text())
        cases = {"invalid": dict(bad, artifact_type=["x"]),
                 "two axes": copy.deepcopy(bad), "missing cov": json.loads(RECORD.read_text())}
        cases["two axes"]["extension"]["observable"]["variables"].append({"name": "y", "unit": "1", "edges": [0, 1]})
        for name, doc in cases.items():
            art = Path(self.tmp.name) / f"{name}.json"
            art.write_text(json.dumps(doc))  # the covariance file is not next to this copy
            code, rep = export(art, self.out / name)
            self.assertEqual((code, rep["status"]), (1, "failed"), name)

    @unittest.skipUnless(FullSubmissionValidator, "hepdata-validator not installed: the submission format is unverified")
    def test_hepdata_validator_accepts_both_engines(self):
        engines = ["plain"] + (["hepdata_lib"] if HAVE_LIB else [])
        for engine in engines:
            out = self.out / engine
            self.assertEqual(export(RECORD, out, "--engine", engine)[0], 0, engine)
            v = FullSubmissionValidator()
            ok = v.validate(directory=str(out))
            self.assertTrue(ok, {k: [m.message for m in ms] for k, ms in v.get_messages().items()})


if __name__ == "__main__":
    unittest.main()
