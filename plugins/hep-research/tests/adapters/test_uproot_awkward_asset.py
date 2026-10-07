"""adapters/root-uproot: assets/uproot_awkward_analysis.py runs end to end on a SYNTHETIC NanoAOD-like file written
with uproot (signed weights included), and the TH1D it writes matches an independent numpy recomputation in bin
contents and sum(w^2). Skipped, and therefore unverified, without uproot, awkward, numpy and PyYAML; ROOT itself is
not used."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT / "adapters" / "root-uproot" / "assets" / "uproot_awkward_analysis.py"
try:
    import awkward as ak
    import numpy as np
    import uproot
    import yaml  # noqa: F401  (the asset reads a YAML config)
    HAVE = True
except ImportError:
    HAVE = False


def write_synthetic(path, n=4000, seed=20261002):
    """Synthetic events: 0-4 muons, falling pT, |eta| up to 3, weights +-1 with 15% negative."""
    rng = np.random.default_rng(seed)
    counts = rng.integers(0, 5, n)
    total = int(counts.sum())
    pt = ak.sort(ak.unflatten(rng.exponential(30.0, total) + 3.0, counts), axis=1, ascending=False)  # leading first
    eta = ak.unflatten(rng.uniform(-3, 3, total), counts)
    w = np.where(rng.random(n) < 0.15, -1.0, 1.0) * rng.uniform(0.5, 1.5, n)
    with uproot.recreate(path) as f:
        f["Events"] = {"nMuon": counts.astype(np.int32), "Muon_pt": pt, "Muon_eta": eta, "event_weight": w}
    return counts, pt, eta, w


@unittest.skipUnless(HAVE, "uproot, awkward, numpy or PyYAML not installed")
class UprootAwkwardAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        cls.counts, cls.pt, cls.eta, cls.w = write_synthetic(tmp / "synthetic_events.root")
        config = {"inputs": {"tree": "Events", "files": [str(tmp / "synthetic_events.root")]},
                  "branches": {"required": ["nMuon", "Muon_pt", "Muon_eta", "event_weight"]},
                  "output": {"directory": str(tmp / "out"), "root_file": "synthetic_hist.root"}}
        (tmp / "config.yaml").write_text(json.dumps(config), encoding="utf-8")  # JSON is valid YAML
        cls.proc = subprocess.run([sys.executable, str(ASSET), "--config", str(tmp / "config.yaml")],
                                  capture_output=True, text=True, timeout=600)
        cls.out = tmp / "out" / "synthetic_hist.root"

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _expected(self):
        two = self.counts >= 2
        lead_pt = ak.to_numpy(ak.firsts(self.pt[two]))
        lead_eta = ak.to_numpy(ak.firsts(self.eta[two]))
        w = self.w[two]
        sel = (lead_pt > 25.0) & (np.abs(lead_eta) < 2.4)
        edges = np.linspace(0.0, 200.0, 51)
        return (np.histogram(lead_pt[sel], edges, weights=w[sel])[0],
                np.histogram(lead_pt[sel], edges, weights=w[sel] ** 2)[0], int(sel.sum()))

    def test_runs_and_reports_selection(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        _, _, n_sel = self._expected()
        self.assertIn(f"selected events: {n_sel}", self.proc.stdout)
        self.assertIn(f"processed events: {len(self.counts)}", self.proc.stdout)

    def test_histogram_contents_and_sumw2_match_independent_numpy(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        h = uproot.open(self.out)["h_leading_muon_pt"]
        self.assertEqual(h.classname, "TH1D")
        sumw, sumw2, _ = self._expected()
        np.testing.assert_allclose(h.values(), sumw, rtol=0, atol=1e-9)
        np.testing.assert_allclose(h.variances(), sumw2, rtol=0, atol=1e-9)  # not sqrt(sum w) errors
        self.assertTrue(np.any(sumw2 > np.abs(sumw)))  # signed weights make the distinction visible

    def test_missing_branch_is_refused(self):
        tmp = Path(self._tmp.name)
        bad = json.loads((tmp / "config.yaml").read_text())
        bad["branches"]["required"].append("Muon_charge")
        (tmp / "bad.yaml").write_text(json.dumps(bad), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(ASSET), "--config", str(tmp / "bad.yaml")], capture_output=True, text=True, timeout=600)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Missing required branches: Muon_charge", proc.stderr)


if __name__ == "__main__":
    unittest.main()
