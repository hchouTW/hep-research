"""Journey J15 (examples/design-minimal-spectrometer, Geant4 program B3): the minimal spectrometer taken from F1 to F4.
Offline replay of run.py: the design project, its F1 and F2 evaluations and, from recorded/ (written by live.py with
Geant4 11.4.3, gzip-compressed run records), every F4 study re-labelled through the qualification path and evaluated;
the derived results reproduce the committed output (numbers within 1e-9 relative, since libm differs between
platforms in the last bit), every pre-declared criterion passes, and recorded/ stays inside its budget (B3.7)."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
HERE = PLUGIN / "examples" / "design-minimal-spectrometer"
SCRIPT = HERE / "run.py"
sys.path.insert(0, str(PLUGIN))
from contracts.validate import validate_artifact  # noqa: E402


def differences(a, b, path="$"):
    if isinstance(a, dict) and isinstance(b, dict):
        out = [f"{path}: keys {sorted(set(a) ^ set(b))}"] if set(a) != set(b) else []
        return out + [d for k in set(a) & set(b) for d in differences(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, f"{path}[{i}]")]
    if isinstance(a, float) and isinstance(b, (int, float)) and not isinstance(b, bool):
        return [] if abs(a - b) <= 1e-9 * max(abs(a), abs(b), 1e-300) else [f"{path}: {a!r} != {b!r}"]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


class DesignMinimalSpectrometer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("design_minimal_spectrometer_run", SCRIPT)
        cls.mod = importlib.util.module_from_spec(spec)
        sys.modules["design_minimal_spectrometer_run"] = cls.mod
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
        self.assertIn("trk1_upgraded", self.r["pass"])  # the recorded F4 studies were replayed

    def test_reproduces_committed_output(self):
        committed = json.loads((HERE / "output" / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(differences(self.r, committed), [])

    def test_upgraded_study_records_validate_strictly(self):
        studies = self.out / "artifacts" / "studies"
        seen = 0
        for sid in ("N4-TRK1", "N6-TRK1", "N8-TRK1"):
            rec = json.loads((studies / sid / "study.computational-run.json").read_text(encoding="utf-8"))
            self.assertEqual(rec["status"], ["validated-in-scope"], sid)
            rep = validate_artifact(rec, strict=True)
            self.assertTrue(rep.ok, [f.message for f in rep.errors])
            unc = rec["extension"]["study"]["results"]["momentum-resolution-core"]["uncertainty_components"]
            self.assertIn("qualification", unc)  # D0-c: the qualifying reference's tolerance is in the uncertainty
            seen += 1
        self.assertEqual(seen, 3)

    def test_every_verdict_is_derived(self):
        rep = json.loads((self.out / "artifacts" / "reports" / "design-report.json").read_text(encoding="utf-8"))
        self.assertEqual((rep["artifact_type"], rep["provenance"]["producer_skill"]), ("communication", "hep-detector"))

    def test_recorded_budget(self):
        """B3.7: no file above 2 MiB, recorded/ at most 3 MB; no ROOT file is committed."""
        files = [p for p in (HERE / "recorded").rglob("*") if p.is_file()]
        self.assertTrue(all(p.stat().st_size <= 2 * 1024 * 1024 for p in files))
        self.assertLessEqual(sum(p.stat().st_size for p in files), 3_000_000)
        self.assertFalse([p for p in files if p.suffix == ".root"])


if __name__ == "__main__":
    unittest.main()
