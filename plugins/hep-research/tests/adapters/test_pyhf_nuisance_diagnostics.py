"""S04: adapters/pyhf-combine/assets/pyhf_nuisance_diagnostics.py (pulls, constraints, impacts, ranking, grouped
breakdown, correlations). Impacts on the SYNTHETIC shape workspace are checked against independent refits of the
HistFactory reference likelihood (histfactory_reference.py, no pyhf). Skipped, and therefore unverified, where
pyhf is not installed; the no-pyhf exit path is checked either way."""
import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "pyhf-combine" / "assets"
SCRIPT = ASSETS / "pyhf_nuisance_diagnostics.py"
WS = ASSETS / "pyhf-shape-synthetic.json"
COUNTING = ASSETS / "pyhf-counting.json"
sys.path.insert(0, str(ASSETS))

try:
    import numpy as np
    import pyhf  # noqa: F401
    from scipy.optimize import minimize
    from .histfactory_reference import ShapeModel
    import pyhf_nuisance_diagnostics as diag
    HAVE = True
except ImportError:
    HAVE = False

REF_INDEX = {"jes": 1, "bkg_xsec": 2, **{f"staterror_synthetic_sr[{k}]": 3 + k for k in range(3)},
             **{f"cr_shape[{k}]": 6 + k for k in range(2)}}
NO_PYHF = "import runpy, sys; sys.modules['pyhf'] = None; sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')"


def ref_fit_fixed(ref, fixed):
    """Reference fit with some parameters fixed: (parameters, nll). Two starting points, as ShapeModel.fit."""
    free = [i for i in range(8) if i not in fixed]
    best = None
    for start in ([1, 0, 0, 1, 1, 1, 1, 1], [0.3, 0.5, -0.5, 1, 1, 1, 1, 1]):
        x0 = np.array(start, float)
        for i, v in fixed.items():
            x0[i] = v

        def f(x, x0=x0):
            q = x0.copy()
            q[free] = x
            return ref.nll(q)
        r = minimize(f, x0[free], method="L-BFGS-B", bounds=list(zip(ref.LO[free], ref.HI[free])),
                     options={"ftol": 1e-15, "gtol": 1e-11, "maxiter": 10000})
        q = x0.copy()
        q[free] = r.x
        if best is None or r.fun < best[1]:
            best = (q, r.fun)
    return best


class NoPyhf(unittest.TestCase):
    def test_exits_2_without_pyhf(self):
        p = subprocess.run([sys.executable, "-c", NO_PYHF, str(SCRIPT), str(WS)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn("pyhf not installed", p.stdout)


@unittest.skipUnless(HAVE, "pyhf, numpy or scipy not installed: nuisance diagnostics unverified")
class ShapeWorkspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(WS.read_text(encoding="utf-8"))
        groups = {"theory_like": ["bkg_xsec"], "detector": ["jes"], "mc_stat": ["staterror_synthetic_sr", "cr_shape"]}
        cls.out, cls.code = diag.diagnostics(cls.spec, groups=groups)
        cls.ref = ShapeModel(cls.spec)
        cls.ref_hat, _ = cls.ref.fit()

    def test_status_and_echo(self):
        self.assertEqual(self.code, 0, self.out["failures"])
        self.assertEqual(self.out["status"], "ok")
        self.assertIsNone(self.out["seed"])
        self.assertEqual(self.out["pyhf_version"], pyhf.__version__)
        self.assertAlmostEqual(self.out["best_fit"]["poi_hat"], self.ref_hat[0], delta=1e-4)

    def test_impacts_match_independent_refits(self):
        rows = {r["name"]: r for r in self.out["nuisances"]}
        self.assertEqual(set(rows), set(REF_INDEX))
        for name, i in REF_INDEX.items():
            r = rows[name]
            for kind, sigma in (("prefit", r["sigma_prefit"]), ("postfit", r["sigma_postfit"])):
                for sign, label in ((1, "up"), (-1, "down")):
                    p_fix, _ = ref_fit_fixed(self.ref, {i: r["theta_hat"] + sign * sigma})
                    expected = p_fix[0] - self.ref_hat[0]
                    got = r["impacts"][f"{kind}_{label}"]
                    with self.subTest(name=name, kind=kind, side=label):
                        self.assertTrue(abs(got - expected) <= max(1e-3 * abs(expected), 1e-4), (got, expected))

    def test_pull_convention_and_ranking(self):
        rows = {r["name"]: r for r in self.out["nuisances"]}
        r = rows["staterror_synthetic_sr[2]"]
        self.assertAlmostEqual(r["sigma_prefit"], 0.12)
        self.assertAlmostEqual(r["pull"], (r["theta_hat"] - 1.0) / 0.12, places=12)
        self.assertIn("Poisson", rows["cr_shape[0]"]["note"])
        self.assertAlmostEqual(rows["cr_shape[0]"]["sigma_prefit"], 0.05)
        mags = [max(abs(x["impacts"]["postfit_up"]), abs(x["impacts"]["postfit_down"])) for x in self.out["nuisances"]]
        self.assertEqual(mags, sorted(mags, reverse=True))

    def test_breakdown_reports_order_and_closure(self):
        b = self.out["breakdown"]
        self.assertEqual(set(b["sequential"]), {"given", "reversed"})
        self.assertLess(b["sigma_stat_all_frozen"], b["sigma_total"])
        self.assertIn("ratio_to_total", b["closure"])
        for v in b["freeze_one"].values():
            self.assertGreater(v, 0)


@unittest.skipUnless(HAVE, "pyhf, numpy or scipy not installed: nuisance diagnostics unverified")
class ConstructedWorkspaces(unittest.TestCase):
    def counting(self, extra_modifiers, background=20.0, observed=20):
        spec = json.loads(COUNTING.read_text(encoding="utf-8"))
        bkg = spec["channels"][0]["samples"][1]
        bkg["data"] = [background]
        bkg["modifiers"] += extra_modifiers
        spec["observations"][0]["data"] = [observed]
        return spec

    def test_inert_nuisance_has_zero_impact_and_unit_constraint(self):
        spec = self.counting([{"name": "inert", "type": "normsys", "data": {"hi": 1.0, "lo": 1.0}}])
        out, code = diag.diagnostics(spec)
        self.assertEqual(code, 0, out["failures"])
        r = {x["name"]: x for x in out["nuisances"]}["inert"]
        self.assertAlmostEqual(r["pull"], 0.0, delta=1e-6)
        self.assertAlmostEqual(r["constraint"], 1.0, delta=1e-4)
        for v in r["impacts"].values():
            self.assertAlmostEqual(v, 0.0, delta=1e-6)

    def test_degenerate_nuisances_flagged(self):
        # a signal bin and a large background-only bin; two normsys with identical effects: the data constrain only
        # their sum, so they are nearly fully anticorrelated
        mods = [{"name": n, "type": "normsys", "data": {"hi": 1.1, "lo": 0.9}} for n in ("bkg_norm", "twin_b")]
        spec = {"channels": [{"name": "synthetic_two_bins", "samples": [
                    {"name": "signal", "data": [50.0, 0.0], "modifiers": [{"name": "mu", "type": "normfactor", "data": None}]},
                    {"name": "background", "data": [100.0, 10000.0], "modifiers": mods}]}],
                "observations": [{"name": "synthetic_two_bins", "data": [100, 10000]}],
                "measurements": [{"name": "synthetic_degenerate", "config": {"poi": "mu", "parameters": []}}],
                "version": "1.0.0"}
        out, code = diag.diagnostics(spec)
        self.assertEqual(code, 0, out["failures"])
        pair = next(p for p in out["correlations"] if set(p["pair"]) == {"bkg_norm", "twin_b"})
        self.assertGreater(abs(pair["rho"]), 0.95)
        self.assertTrue(any("near-degenerate" in w for w in out["warnings"]))

    def test_bad_groups_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = Path(tmp) / "groups.json"
            g.write_text(json.dumps({"x": ["no_such_parameter"]}))
            p = subprocess.run([sys.executable, str(SCRIPT), str(WS), "--groups", str(g)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertIn("unknown parameter", p.stdout)


if __name__ == "__main__":
    unittest.main()
