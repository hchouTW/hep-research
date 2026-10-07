"""reproduce_published_likelihood.py on a SYNTHETIC background-only workspace and patchset
in the HEPData release layout. The real reproduction (ATLAS-SUSY-2018-31, HEPData ins1748602) is not run here
because hepdata.net is not reachable from E4, so it stays unverified. Skipped where pyhf is not installed."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WS = ROOT / "adapters" / "pyhf-combine" / "assets" / "pyhf-shape-synthetic.json"
SCRIPT = ROOT / "adapters" / "pyhf-combine" / "assets" / "reproduce_published_likelihood.py"
try:
    import pyhf
    HAVE = True
except ImportError:
    HAVE = False


@unittest.skipUnless(HAVE, "pyhf not installed: published-likelihood reproduction unverified")
class PublishedReproductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "tests" / "adapters"))
        from test_pyhf_publication import fit_and_cls, split
        doc = json.loads(WS.read_text(encoding="utf-8"))
        cls.bkg, ops = split(doc)
        cls.patchset = {"metadata": {"name": "synthetic_grid", "description": "SYNTHETIC one-point grid",
                                     "digests": {"sha256": pyhf.utils.digest(pyhf.Workspace(cls.bkg))},
                                     "labels": ["mass"], "references": {"hepdata": "ins0000000"}},
                        "patches": [{"metadata": {"name": "signal_m100", "values": [100]}, "patch": ops}],
                        "version": "1.0.0"}
        model, best, obs, exp = fit_and_cls(pyhf.Workspace(doc))
        pyhf.set_backend("numpy", "scipy")
        cls.truth = {"mu_hat": float(best[model.config.poi_index]), "CLs_obs": obs, "CLs_exp": exp}
        cls.td = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls.td.name)
        (cls.tmp / "BkgOnly.json").write_text(json.dumps(cls.bkg))
        (cls.tmp / "patchset.json").write_text(json.dumps(cls.patchset))

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def published(self, values, tol=None, name="p.json", patch="signal_m100"):
        doc = {"record": "synthetic", "status": "synthetic", "patch": patch, "source": "the original workspace",
               "values": values, "tolerances": tol if tol is not None else {k: {"abs": 1e-4} for k in values}}
        p = self.tmp / name
        p.write_text(json.dumps(doc))
        return p

    def run_script(self, published, patchset="patchset.json"):
        out = self.tmp / ("out-" + published.stem)
        proc = subprocess.run([sys.executable, str(SCRIPT), "--bkgonly", str(self.tmp / "BkgOnly.json"), "--patchset",
                               str(self.tmp / patchset), "--published", str(published), "--out", str(out)],
                              capture_output=True, text=True, timeout=600)
        return proc, out

    def test_reproduces_the_original_workspace(self):
        proc, out = self.run_script(self.published(dict(self.truth)))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        rep = json.loads((out / "reproduction.json").read_text())
        self.assertEqual(rep["status"], "reproduced")
        self.assertEqual(len(rep["comparison"]), 3)
        self.assertIn("| CLs_obs |", (out / "reproduction.md").read_text())

    def test_a_shifted_value_fails(self):
        proc, _ = self.run_script(self.published(dict(self.truth, CLs_obs=self.truth["CLs_obs"] + 0.01), name="shift.json"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn('"fail"', proc.stdout)

    def test_not_provided_is_incomplete_and_tolerance_is_required(self):
        proc, _ = self.run_script(self.published({"CLs_obs": self.truth["CLs_obs"], "mu_hat": "not-provided"}, name="np.json"))
        self.assertEqual(proc.returncode, 3, proc.stdout)
        proc, _ = self.run_script(self.published({"CLs_obs": 0.1}, tol={}, name="notol.json"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no tolerance", proc.stdout)

    def test_refuses_digest_mismatch_and_unknown_patch(self):
        bad = copy.deepcopy(self.patchset)
        bad["metadata"]["digests"]["sha256"] = "0" * 64
        (self.tmp / "bad.json").write_text(json.dumps(bad))
        proc, _ = self.run_script(self.published(dict(self.truth), name="d.json"), patchset="bad.json")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("PatchSetVerificationError", proc.stdout)
        proc, _ = self.run_script(self.published(dict(self.truth), name="u.json", patch="signal_m999"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not in the patchset", proc.stdout)


if __name__ == "__main__":
    unittest.main()
