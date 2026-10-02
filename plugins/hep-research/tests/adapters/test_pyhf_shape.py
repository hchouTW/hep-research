"""adapters/pyhf-combine: the two-channel SYNTHETIC shape workspace (pyhf-shape-synthetic.json: histosys, normsys,
staterror, shapesys, a control region) gives the same log-likelihood, best fit and asymptotic CLs limit in pyhf as
in an independent implementation of the HistFactory definitions (histfactory_reference.py). Skipped, and therefore
unverified, where pyhf is not installed."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WS = ROOT / "adapters" / "pyhf-combine" / "assets" / "pyhf-shape-synthetic.json"
try:
    import numpy as np
    import pyhf
    from .histfactory_reference import ShapeModel
    HAVE = True
except ImportError:
    HAVE = False


def _to_pyhf(model, p):
    """Reference parameter order -> pyhf parameter vector."""
    pm, v = model.config.par_map, np.zeros(model.config.npars)
    for name, value in (("mu", p[0]), ("jes", p[1]), ("bkg_xsec", p[2]),
                        ("staterror_synthetic_sr", p[3:6]), ("cr_shape", p[6:8])):
        v[pm[name]["slice"]] = value
    return v


@unittest.skipUnless(HAVE, "pyhf, numpy or scipy not installed")
class PyhfShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        doc = json.loads(WS.read_text(encoding="utf-8"))
        cls.ws = pyhf.Workspace(doc)
        cls.model = cls.ws.model()
        cls.data = cls.ws.data(cls.model)
        cls.ref = ShapeModel(doc)

    def test_workspace_is_labeled_synthetic(self):
        self.assertTrue(all(c.startswith("synthetic_") for c in self.ws.channels))
        self.assertIn("synthetic", self.ws.measurement_names[0])

    def test_logpdf_matches_reference_inside_and_outside_interpolation_region(self):
        rng = np.random.default_rng(20261002)
        for _ in range(200):  # alphas in [-2, 2] cover the polynomial (|a| < 1) and extrapolated regions
            p = np.array([rng.uniform(0, 3), rng.uniform(-2, 2), rng.uniform(-2, 2), *rng.uniform(0.8, 1.2, 5)])
            self.assertAlmostEqual(float(self.model.logpdf(_to_pyhf(self.model, p), self.data)[0]), -self.ref.nll(p), delta=1e-9)

    def test_best_fit_matches_reference(self):
        p_hat, nll_hat = self.ref.fit()
        fitted, twice_nll = pyhf.infer.mle.fit(self.data, self.model, return_fitted_val=True)
        self.assertAlmostEqual(float(twice_nll) / 2, nll_hat, delta=1e-4)
        np.testing.assert_allclose(fitted, _to_pyhf(self.model, p_hat), atol=2e-3)

    def test_asymptotic_cls_limit_matches_reference(self):
        obs, exp = pyhf.infer.intervals.upper_limits.upper_limit(self.data, self.model, scan=np.linspace(0, 10, 501), level=0.05)
        self.assertAlmostEqual(float(obs), self.ref.cls_limit(), delta=0.005)  # pyhf interpolates a 0.02 scan
        self.assertTrue(all(a < b for a, b in zip(exp, exp[1:])))


if __name__ == "__main__":
    unittest.main()
