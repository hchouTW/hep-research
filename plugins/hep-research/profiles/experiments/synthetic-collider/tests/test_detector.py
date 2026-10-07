"""Tests for scripts/detector.py (SYNTHETIC efficiency, smearing and analytic response)."""
import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import detector  # noqa: E402
import generate_events as gen  # noqa: E402

CFG = json.loads((ROOT / "benchmarks" / "path-b.json").read_text(encoding="utf-8"))


class DetectorTests(unittest.TestCase):
    def test_efficiency_formula_and_range(self):
        c = np.linspace(-1, 1, 11)
        np.testing.assert_allclose(detector.efficiency(c, CFG), 0.92 - 0.25 * c ** 4)
        self.assertTrue(np.all((detector.efficiency(c, CFG) > 0) & (detector.efficiency(c, CFG) <= 1)))

    def test_response_columns_account_for_every_selected_event(self):
        r = detector.response(CFG, 1.0, 0.0)
        np.testing.assert_allclose(r["matrix"].sum(axis=0) + r["underflow"] + r["overflow"], r["efficiency"], rtol=1e-12)
        self.assertTrue(np.all(np.diag(r["matrix"]) > 0.5 * r["efficiency"]))

    def test_response_matches_event_level_simulation(self):
        """Analytic response vs a large independent event sample (chi2 per bin)."""
        cfg = dict(CFG, integrated_luminosity_pb=CFG["integrated_luminosity_pb"] * 40)
        ev = gen.generate(cfg, 99)
        te, re_ = np.array(cfg["truth_edges"]), np.array(cfg["reco_edges"])
        tj = np.digitize(ev["truth_cos"], te) - 1
        sel = ev["selected"] & (ev["reco_cos"] >= re_[0]) & (ev["reco_cos"] < re_[-1])
        counts = np.zeros((len(re_) - 1, len(te) - 1))
        np.add.at(counts, (np.digitize(ev["reco_cos"][sel], re_) - 1, tj[sel]), 1)
        ntruth = np.bincount(tj, minlength=len(te) - 1)
        expected = detector.response(cfg, 1.0, 0.0)["matrix"] * ntruth[None, :]
        mask = expected > 20
        chi2 = np.sum((counts[mask] - expected[mask]) ** 2 / expected[mask])
        ndf = int(mask.sum())
        self.assertLess(chi2, ndf + 5 * np.sqrt(2 * ndf), (chi2, ndf))


if __name__ == "__main__":
    unittest.main()
