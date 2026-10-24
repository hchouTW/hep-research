"""Example A (detector system design spec, M1; examples/design-space-spectrometer): a SYNTHETIC AMS-like spectrometer
designed at F1 through evaluate_design.py. Reproduction of the committed results, every pre-declared criterion, and the
M1 acceptance "Example A reproduces M0": the same verdict pattern as the M0 fixture project (probe fails resolution with
bound.excludes, the two reasonable candidates inconclusive with bound.direction on resolution and charge confusion),
derived through evaluate_design.py instead of the fixture builder; no verdict is hand-written (RPT-01)."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "design-space-spectrometer" / "run.py"
sys.path.insert(0, str(PLUGIN))
from contracts.design import derive  # noqa: E402


class DesignSpaceSpectrometer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("design_space_spectrometer_run", SCRIPT)
        cls.mod = importlib.util.module_from_spec(spec)
        sys.modules["design_space_spectrometer_run"] = cls.mod
        spec.loader.exec_module(cls.mod)
        cls.tmp = tempfile.TemporaryDirectory()
        with contextlib.redirect_stdout(io.StringIO()):
            cls.code = cls.mod.main(["--out", cls.tmp.name])
        cls.out = Path(cls.tmp.name)
        cls.r = json.loads((cls.out / "results.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_criteria_pass(self):
        self.assertEqual(self.code, 0, self.r["pass"])
        self.assertTrue(all(self.r["pass"].values()), self.r["pass"])

    def test_reproduces_committed_output(self):
        committed = (SCRIPT.parent / "output" / "results.json").read_bytes()
        self.assertEqual((self.out / "results.json").read_bytes(), committed)

    def test_reproduces_the_m0_verdicts(self):
        m0 = derive(PLUGIN / "contracts" / "fixtures" / "design" / "spectrometer" / "artifacts")

        def pattern(full, names):
            return {(item["id"].split(":")[1], names[c.split(":")[1]]): (m["result"], tuple(m["codes"]))
                    for item in full["requirements"] for m in item["matrix"] for c in m["candidates"]}
        fixture = pattern(m0, {"cand-A": "reasonable-1", "cand-B": "reasonable-2", "cand-P": "probe"})
        example = pattern(derive(self.out / "artifacts", self.out / "decisions"),
                          {"cand-S": "reasonable-1", "cand-L": "reasonable-2", "cand-P": "probe"})
        self.assertEqual(example, fixture)

    def test_every_verdict_is_derived(self):
        """RPT-01: the report is a communication artifact written by evaluate_design.py report from design.py."""
        rep = json.loads((self.out / "artifacts" / "reports" / "design-report.json").read_text(encoding="utf-8"))
        self.assertEqual((rep["artifact_type"], rep["provenance"]["producer_skill"]), ("communication", "hep-detector"))
        for f in (self.out / "artifacts" / "evaluations").glob("*.json"):
            ext = json.loads(f.read_text(encoding="utf-8"))["extension"]
            self.assertNotIn("verdict", ext)
            self.assertIn("run_ref", ext)

    def test_public_facts_are_cited(self):
        cand = json.loads((self.out / "artifacts" / "candidates" / "cand-L.json").read_text(encoding="utf-8"))
        params = cand["extension"]["subsystems"]
        self.assertEqual(params["DES-MAG-001"]["parameters"]["field_T"]["status"], "public-fact")
        self.assertIn("ams02:C93", params["DES-MAG-001"]["parameters"]["field_T"]["source"])
        self.assertIn("SYNTHETIC", self.r["label"])


if __name__ == "__main__":
    unittest.main()
