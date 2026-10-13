"""hep-statistics audit T16: the same likelihood in core/stats (shape-limit model) and pyhf. Pointwise Delta NLL at the
nominal point, +-0.5, +-1 and +-2.5 sigma and a mu grid, and the profiled q-tilde on the mu grid agree within the tolerances
fixed in backend_comparison.py; a deliberately wrong mapping (pyhf normsys code1 for a core code4 factor) is caught;
features without a pyhf equivalent are refused. SYNTHETIC models. Combine is not run here (not-run, not passed).
Skipped where pyhf is not installed: the backend equivalence is then unverified."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters" / "pyhf-combine" / "assets"))
try:
    import pyhf  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False

A = {"bins": [{"n": 9, "b": 6.0, "s": 1.5}, {"n": 5, "b": 4.0, "s": 2.0}, {"n": 2, "b": 1.5, "s": 1.0}],
     "nuisances": [{"name": "bnorm", "kind": "background_norm", "hi": 1.12, "lo": 0.9, "interpolation": "code4"},
                   {"name": "bshape", "kind": "background_shape", "up": [6.5, 4.1, 1.4], "down": [5.6, 3.9, 1.65],
                    "interpolation": "code0"},
                   {"name": "snorm", "kind": "signal_norm", "hi": 1.08, "lo": 0.93, "interpolation": "code4"}]}
B = {"bins": [{"n": 30, "b": 25.0, "s": 3.0, "mc_stat": 2.0}, {"n": 14, "b": 12.0, "s": 4.0, "mc_stat": 1.5},
              {"n": 6, "b": 5.0, "s": 2.0, "mc_stat": 0.8}],
     "nuisances": [{"name": "bshape", "kind": "background_shape", "up": [27, 12.5, 4.6], "down": [23.5, 11.6, 5.5],
                    "interpolation": "code4p"},
                   {"name": "bnorm", "kind": "background_norm", "hi": 1.1, "lo": 0.92, "interpolation": "code4"}]}
C = {"bins": [{"n": 4, "b": 3.0, "s": 1.0}, {"n": 2, "b": 1.5, "s": 0.8}],
     "nuisances": [{"name": "bkg", "kind": "background_norm", "sigma": 0.1}]}


@unittest.skipUnless(HAVE, "pyhf not installed: core/pyhf backend equivalence unverified")
class BackendEquivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import backend_comparison as bc
        cls.bc = bc
        cls.reports = {k: bc.compare(d) for k, d in (("A", A), ("B", B), ("C", C))}

    def test_equivalent_within_the_fixed_tolerances(self):
        for k, r in self.reports.items():
            with self.subTest(model=k):
                self.assertEqual(r["status"], "equivalent")
                self.assertTrue(all(x["ok"] for x in r["profiled"]))
                self.assertEqual(r["core_fit_diagnostics"]["failed"], 0)
                self.assertEqual(r["combine"]["status"], "not-run")
        self.assertTrue(self.reports["A"]["pointwise_compared"])
        self.assertGreaterEqual(len(self.reports["A"]["pointwise"]), 5 + 6 * 3)   # mu grid and +-0.5, +-1, +-2.5 per nuisance
        self.assertFalse(self.reports["B"]["pointwise_compared"])               # mc_stat: profiled comparison only

    def test_limits_are_reported_not_used_as_an_oracle(self):
        for r in self.reports.values():
            self.assertFalse(r["limits"]["same_oracle"])
            self.assertLess(abs(r["limits"]["relative_difference"]), 0.02)

    def test_wrong_interpolation_mapping_is_caught(self):
        orig = self.bc.to_pyhf

        def wrong(doc, normsys_code="code4"):
            spec, names = orig(doc, normsys_code)
            spec["_normsys_code"] = "code1"      # pyhf's default normsys interpolation, not the core's code4
            return spec, names
        self.bc.to_pyhf = wrong
        try:
            r = self.bc.compare(A)
        finally:
            self.bc.to_pyhf = orig
        self.assertEqual(r["status"], "not-equivalent")
        self.assertTrue(any(not x["ok"] for x in r["pointwise"]))

    def test_unrepresentable_features_are_refused(self):
        bad = [dict(C, nuisances=[{"name": "g", "kind": "background_norm", "sigma": 0.2, "prior": "gamma"}]),
               dict(C, nuisances=[{"name": "l", "kind": "background_norm", "sigma": 0.2, "prior": "lognormal"}]),
               dict(A, correlation=[[1, 0.3, 0], [0.3, 1, 0], [0, 0, 1]]),
               dict(C, nuisances=[{"name": "n", "kind": "background_norm", "hi": 1.1, "lo": 0.9, "interpolation": "code0"}])]
        for doc in bad:
            with self.assertRaises(self.bc.MappingRefused):
                self.bc.compare(doc)


@unittest.skipUnless(HAVE, "pyhf not installed: ordinary-size asymptotic CLs unverified against pyhf")
class OrdinarySizeAsymptoticCLsSTH316(unittest.TestCase):
    """STH-T3.16: 100 bins with about 1000 background events each run on the asymptotic path of shape-limit (the toy
    caps of 40 bins, b <= 200 and 400 events do not apply without toys); the observed asymptotic CLs limit agrees with
    pyhf 0.7.6 (q-tilde, asymptotic CLs) within 1%."""

    def test_cls_limit_matches_pyhf(self):
        import math
        import random
        import pyhf
        sys.path.insert(0, str(ROOT))
        from core.stats import likelihood_limits as ll
        rng = random.Random(3)
        b = [800.0 + 400.0 * math.sin(0.1 * i) ** 2 for i in range(100)]
        sig = [30.0 * math.exp(-0.5 * ((i - 50) / 4.0) ** 2) for i in range(100)]
        n = [int(round(bi + rng.gauss(0.0, math.sqrt(bi)))) for bi in b]
        ours = ll.shape_limit({"bins": [{"n": ni, "b": bi, "s": si} for ni, bi, si in zip(n, b, sig)], "cl": 0.95}, 0.95, 0, 1)
        self.assertEqual(ours["status"], "ok", ours["fit_diagnostics"])
        self.assertTrue(ours["path"].startswith("asymptotic"))
        spec = {"channels": [{"name": "c", "samples": [
            {"name": "s", "data": sig, "modifiers": [{"name": "mu", "type": "normfactor", "data": None}]},
            {"name": "b", "data": b, "modifiers": []}]}]}
        pyhf.set_backend("numpy", "scipy")
        model = pyhf.Model(spec, poi_name="mu")
        import numpy as np
        data = np.array([float(v) for v in n] + list(model.config.auxdata))
        mus = np.array([0.05 * k for k in range(1, 121)])
        obs = pyhf.infer.intervals.upper_limits.upper_limit(data, model, mus, level=0.05, test_stat="qtilde",
                                                            return_results=False)[0]
        self.assertLess(abs(ours["asymptotic_observed_cls_upper_limit"] / float(obs) - 1.0), 0.01,
                        (ours["asymptotic_observed_cls_upper_limit"], float(obs)))

    def test_toy_paths_keep_their_caps(self):
        sys.path.insert(0, str(ROOT))
        from core.stats import likelihood_limits as ll
        doc = {"bins": [{"n": 1000, "b": 1000.0, "s": 5.0} for _ in range(60)]}
        with self.assertRaises(ll.LikelihoodError) as ctx:
            ll.shape_limit(doc, 0.95, 100, 1)
        self.assertIn("pyhf", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
