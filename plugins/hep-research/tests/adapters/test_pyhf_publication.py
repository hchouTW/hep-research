"""S10: likelihood publication pattern (background-only workspace plus a signal patchset, as published on HEPData)
with pyhf, on the SYNTHETIC shape workspace pyhf-shape-synthetic.json. The signal sample is removed to make the
background-only workspace; a one-patch PatchSet (digest-checked) adds it back; the patched workspace reproduces the
original's best fit and observed/expected CLs to 1e-6. Skipped, and therefore unverified, where pyhf is not
installed."""
import copy
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WS = ROOT / "adapters" / "pyhf-combine" / "assets" / "pyhf-shape-synthetic.json"
try:
    import numpy as np
    import pyhf
    HAVE = True
except ImportError:
    HAVE = False


def split(doc):
    """Background-only workspace and the patch operations that restore the signal sample."""
    bkg = copy.deepcopy(doc)
    ch = next(i for i, c in enumerate(bkg["channels"]) if any(s["name"] == "signal" for s in c["samples"]))
    si = next(i for i, s in enumerate(bkg["channels"][ch]["samples"]) if s["name"] == "signal")
    signal = bkg["channels"][ch]["samples"].pop(si)
    ops = [{"op": "add", "path": f"/channels/{ch}/samples/{si}", "value": signal}]
    return bkg, ops


def fit_and_cls(ws):
    model = ws.model()
    data = ws.data(model)
    pyhf.set_backend("numpy", pyhf.optimize.scipy_optimizer(tolerance=1e-10))
    best = pyhf.infer.mle.fit(data, model)
    obs, exp = pyhf.infer.hypotest(1.0, data, model, test_stat="qtilde", return_expected=True)
    return model, np.asarray(best), float(obs), float(exp)


@unittest.skipUnless(HAVE, "pyhf or numpy not installed: likelihood publication pattern unverified")
class PublicationPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(WS.read_text(encoding="utf-8"))
        cls.bkg_doc, ops = split(cls.doc)
        cls.bkg_ws = pyhf.Workspace(cls.bkg_doc)                     # schema-valid on its own
        cls.patchset = pyhf.PatchSet({
            "metadata": {"name": "synthetic_signal_grid", "description": "SYNTHETIC one-point signal grid",
                         "digests": {"sha256": pyhf.utils.digest(cls.bkg_ws)}, "labels": ["mass"], "references": {"hepdata": "ins0000000"}},   # schema-required; placeholder, no record
            "patches": [{"metadata": {"name": "signal_m100", "values": [100]}, "patch": ops}],
            "version": "1.0.0"})

    @classmethod
    def tearDownClass(cls):
        pyhf.set_backend("numpy", "scipy")                           # restore the default optimizer

    def test_background_only_has_no_signal(self):
        names = {s["name"] for c in self.bkg_doc["channels"] for s in c["samples"]}
        self.assertNotIn("signal", names)

    def test_patch_restores_the_workspace(self):
        patched = self.patchset.apply(self.bkg_ws, "signal_m100")
        self.assertEqual(pyhf.utils.digest(patched), pyhf.utils.digest(pyhf.Workspace(self.doc)))

    def test_patched_fit_and_cls_match(self):
        m0, best0, obs0, exp0 = fit_and_cls(pyhf.Workspace(self.doc))
        m1, best1, obs1, exp1 = fit_and_cls(self.patchset.apply(self.bkg_ws, [100]))
        self.assertEqual(m0.config.par_order, m1.config.par_order)
        np.testing.assert_allclose(best1, best0, rtol=0, atol=1e-6)
        self.assertAlmostEqual(obs1, obs0, delta=1e-6)
        np.testing.assert_allclose(exp1, exp0, rtol=0, atol=1e-6)
        print(f"\npublication patch: mu_hat = {best1[m1.config.poi_index]:.4f}, CLs(mu=1) obs = {obs1:.4f}")

    def test_digest_mismatch_is_refused(self):
        other = copy.deepcopy(self.bkg_doc)
        other["observations"][0]["data"][0] += 1
        with self.assertRaises(pyhf.exceptions.PatchSetVerificationError):
            self.patchset.apply(pyhf.Workspace(other), "signal_m100")


if __name__ == "__main__":
    unittest.main()
