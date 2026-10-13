"""Tests for skills/hep-computing/scripts/compare_root_histograms.py (CMP-06).

On c1d375c the script compared GetNbinsX() bins only, ignored edges and errors, printed text, always exited 0 and
needed PyROOT. These tests write synthetic ROOT files with uproot and run the uproot backend (E2); the PyROOT backend
runs in tests/skills/hep_computing/test_root_integration.py with HEP_ROOT_PYTHON. All inputs SYNTHETIC.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-computing" / "scripts" / "compare_root_histograms.py"

try:
    import numpy as np
    import uproot
except ImportError:  # pragma: no cover - E2 has both
    uproot = None


def run(*argv, isolated=False):
    cmd = [sys.executable, *(["-I", "-S"] if isolated else []), str(SCRIPT), *map(str, argv)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    doc = json.loads(p.stdout) if p.stdout.strip().startswith("{") else None
    return p.returncode, doc, p.stderr


@unittest.skipIf(uproot is None, "uproot and numpy are needed to write the fixtures")
class CompareHistogramsUprootTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)

    def write(self, name, **hists):
        p = self.d / name
        with uproot.recreate(p) as f:
            for key, h in hists.items():
                f[key] = h
        return p

    def h1(self, values, edges=None):
        values = np.asarray(values, float)
        return values, np.asarray(edges if edges is not None else np.arange(len(values) + 1), float)

    def cmp(self, ref, cand, *extra):
        return run("--reference", ref, "--candidate", cand, "--hist", "h", "--backend", "uproot", *extra)

    def test_identical_is_exit_0(self):
        a = self.write("a.root", h=self.h1([10, 20, 30, 40]))
        code, doc, err = self.cmp(a, a)
        self.assertEqual(code, 0, err)
        self.assertEqual((doc["status"], doc["verdict"], doc["backend"]), ("pass", "within tolerance", "uproot"))
        self.assertTrue(all(c["ok"] for c in doc["checks"].values()))

    def test_one_bin_outside_rel_tol_is_named(self):
        a = self.write("a.root", h=self.h1([10, 20, 30, 40]))
        b = self.write("b.root", h=self.h1([10, 20, 33, 40]))
        code, doc, _ = self.cmp(a, b, "--rel-tol", "0.05")
        self.assertEqual(code, 1)
        self.assertEqual(doc["status"], "fail")
        self.assertEqual(doc["checks"]["values"]["first_bins_outside"], [[3]])
        self.assertEqual(doc["worst_bins"]["rel"]["bin"], [3])
        self.assertAlmostEqual(doc["worst_bins"]["rel"]["rel_diff"], 0.1)
        code, doc, _ = self.cmp(a, b, "--rel-tol", "0.2")
        self.assertEqual(code, 0)

    def test_worst_bins_reported_separately(self):
        a = self.write("a.root", h=self.h1([1000, 2, 30]))
        b = self.write("b.root", h=self.h1([1010, 3, 30]))
        code, doc, _ = self.cmp(a, b)
        self.assertEqual(code, 1)
        self.assertEqual(doc["worst_bins"]["abs"]["bin"], [1])  # 10 counts in the big bin
        self.assertEqual(doc["worst_bins"]["rel"]["bin"], [2])  # 50 % in the small bin

    def test_sigma_tolerance_uses_bin_errors(self):
        a = self.write("a.root", h=self.h1([100, 100]))
        b = self.write("b.root", h=self.h1([110, 100]))
        code, doc, _ = self.cmp(a, b, "--rel-tol", "1", "--sigma-tol", "0.5")  # pull 10/sqrt(210) = 0.69
        self.assertEqual(code, 1)
        self.assertFalse(doc["checks"]["sigma"]["ok"])
        self.assertTrue(doc["checks"]["values"]["ok"])
        self.assertAlmostEqual(doc["worst_bins"]["sigma"]["pull"], 10 / 210 ** 0.5)
        self.assertEqual(self.cmp(a, b, "--rel-tol", "1", "--sigma-tol", "1")[0], 0)

    def test_same_bin_count_different_edges_fails_the_edge_check(self):
        a = self.write("a.root", h=self.h1([1, 2, 3], [0, 1, 2, 3]))
        b = self.write("b.root", h=self.h1([1, 2, 3], [0, 1, 2.5, 3]))
        code, doc, _ = self.cmp(a, b)
        self.assertEqual(code, 1)
        self.assertEqual(doc["checks"]["edges"], {"ok": False, "axes_differing": ["x"]})

    def test_bin_count_mismatch_is_a_verdict_not_a_traceback(self):
        a = self.write("a.root", h=self.h1([1, 2, 3]))
        b = self.write("b.root", h=self.h1([1, 2, 3, 4]))
        code, doc, err = self.cmp(a, b)
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)
        self.assertFalse(doc["checks"]["shape"]["ok"])

    def test_th2_reports_per_axis_indices(self):
        vals = np.arange(6, dtype=float).reshape(2, 3) + 1
        a = self.write("a.root", h=(vals, np.array([0.0, 1, 2]), np.array([0.0, 1, 2, 3])))
        vals2 = vals.copy()
        vals2[1, 2] += 5
        b = self.write("b.root", h=(vals2, np.array([0.0, 1, 2]), np.array([0.0, 1, 2, 3])))
        code, doc, _ = self.cmp(a, b)
        self.assertEqual(code, 1)
        self.assertEqual(doc["worst_bins"]["abs"]["bin"], [2, 3])  # ROOT numbering: x bin 2, y bin 3
        self.assertEqual(doc["checks"]["shape"]["reference"], {"dimension": 2, "bins": [2, 3]})

    def test_flow_bins_only_with_include_flow(self):
        a = self.write("a.root", h=self.h1([1, 2]))
        code, doc, _ = self.cmp(a, a, "--include-flow")
        self.assertEqual(code, 0)
        self.assertTrue(doc["include_flow"])

    def test_bad_input_is_exit_2_with_json(self):
        a = self.write("a.root", h=self.h1([1, 2]))
        for args in (("--reference", self.d / "missing.root", "--candidate", a, "--hist", "h"),
                     ("--reference", a, "--candidate", a, "--hist", "nope"),
                     ("--reference", a, "--candidate", a, "--hist", "h", "--rel-tol", "-1")):
            with self.subTest(args=args):
                code, doc, err = run(*args, "--backend", "uproot")
                self.assertEqual(code, 2, err)
                self.assertNotIn("Traceback", err)
                self.assertEqual(doc["status"], "error")
                self.assertIn("error", doc)


class CompareHistogramsDependencyTests(unittest.TestCase):
    def test_no_backend_is_exit_3_with_a_dependency_message(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "x.root"
            f.write_bytes(b"root")
            code, doc, err = run("--reference", f, "--candidate", f, "--hist", "h", isolated=True)
        self.assertEqual(code, 3, err)
        self.assertEqual(doc["status"], "missing-dependency")
        self.assertIn("uproot", doc["error"])


if __name__ == "__main__":
    unittest.main()
