"""theory:drell-yan-lo prediction tests: Lam-Tung in channels and mixtures, the mixing-rule alternative, the LO
cross section and its numerical Jacobian check (SYNTHETIC toy densities), bad inputs refused, no experiment content."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

CFG = predict.load_json(predict.DEFAULT_CONFIG)
TOY = predict.load_json(predict.TOY_XS)
SHIPPED = ROOT.parents[2] / "skills" / "hep-theory" / "scripts" / "drell_yan_lo.py"


class AngularTests(unittest.TestCase):
    def test_lam_tung_in_mixtures(self):
        for f in (0.0, 0.3, 0.585, 1.0):
            for r in (0.1, 0.7, 2.5):
                self.assertAlmostEqual(predict.mixture_coefficients(f, r)["lam_tung"], 0.0, places=14)

    def test_mixture_endpoints_are_the_channels(self):
        r = 0.6
        for f, ch in ((0.0, "qqbar"), (1.0, "qg")):
            m, c = predict.mixture_coefficients(f, r), predict.channel_coefficients(ch, r)
            self.assertAlmostEqual(m["lambda"], c["lambda"], places=15)
            self.assertAlmostEqual(m["nu"], c["nu"], places=15)

    def test_A_average_equals_lambda_form_mixture(self):
        """A_i^mix = sum f_c A_i^c is the same as lambda_mix = sum f_c lambda_c/(3 + lambda_c) / sum f_c/(3 + lambda_c)
        (and nu likewise), f_c the angle-integrated cross-section fractions; a linear average of lambda is not."""
        for f in (0.2, 0.5, 0.9):
            for r in (0.3, 1.0, 2.0):
                m = predict.mixture_coefficients(f, r)
                cs = [(1.0 - f, predict.channel_coefficients("qqbar", r)), (f, predict.channel_coefficients("qg", r))]
                w = sum(fc / (3.0 + c["lambda"]) for fc, c in cs)
                lam = sum(fc * c["lambda"] / (3.0 + c["lambda"]) for fc, c in cs) / w
                nu = sum(fc * c["nu"] / (3.0 + c["lambda"]) for fc, c in cs) / w
                self.assertAlmostEqual(m["lambda"], lam, places=14)
                self.assertAlmostEqual(m["nu"], nu, places=14)
                linear = sum(fc * c["lambda"] for fc, c in cs)
                self.assertGreater(abs(m["lambda"] - linear), 1e-4)

    def test_linear_lambda_rule_is_gone(self):
        with self.assertRaises(predict.InputError):
            predict.mixture_coefficients(0.5, 0.5, "average-lambda-nu")

    def test_bad_inputs_refused(self):
        with self.assertRaises(predict.InputError):
            predict.sin2_theta1("qqbar", -0.1)
        with self.assertRaises(predict.InputError):
            predict.sin2_theta1("gg", 0.1)
        with self.assertRaises(predict.InputError):
            predict.mixture_coefficients(1.2, 0.5)


@unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required")
class PredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = predict.predict(CFG)

    def test_all_checks_pass(self):
        self.assertTrue(all(self.p["checks"].values()), self.p["checks"])

    def test_no_hard_coded_checks(self):
        self.assertNotIn("units_dimensionless_coefficients", self.p["checks"])
        self.assertNotIn("mixtures_average_lambda_nu", self.p)

    def test_jacobian_check(self):
        xs = self.p["lo_cross_section_check"]
        self.assertTrue(xs["pass"])
        self.assertLess(xs["relative_difference"], TOY["relative_tolerance"])
        self.assertIn("SYNTHETIC", xs["label"])

    def test_cross_section_hand_point(self):
        """One point by hand: y = 0, x1 = x2 = M/sqrt(s), luminosity 2 sum e^2 q qbar."""
        m = 4.5
        x = m / TOY["sqrt_s_gev"]
        lum = sum(float(Fraction(fl["charge"])) ** 2 * 2 * predict._density(fl["quark"], x) * predict._density(fl["antiquark"], x)
                  for fl in TOY["flavours"])
        expect = 2.0 / 3.0 / (m * TOY["sqrt_s_gev"] ** 2) * lum
        self.assertAlmostEqual(predict.d2sigma_dm_dy(TOY, m, 0.0) / expect, 1.0, places=13)
        self.assertTrue(math.isclose(predict.NB_GEV2, 86.8))

    def test_cross_section_against_shipped_script(self):
        """Independent normalization check: skills/hep-theory/scripts/drell_yan_lo.py xsec at one point, same toy partons.
        alpha below is a test input (any value: both sides scale as alpha^2)."""
        m, y, alpha = 4.5, 0.3, 0.01
        rs = TOY["sqrt_s_gev"]
        x1, x2 = m / rs * math.exp(y), m / rs * math.exp(-y)
        flav = {fl["name"]: fl for fl in TOY["flavours"]}

        def xf(x):
            out = {}
            for q in ("d", "u", "s", "c", "b"):
                fl = flav.get(q)
                out[q] = x * predict._density(fl["quark"], x) if fl else 0.0
                out[q + "bar"] = x * predict._density(fl["antiquark"], x) if fl else 0.0
            return out
        with tempfile.TemporaryDirectory() as tmp:
            pf = Path(tmp) / "partons.json"
            pf.write_text(json.dumps({"representation": "xf", "x1": x1, "x2": x2, "beam1": xf(x1), "beam2": xf(x2)}),
                          encoding="utf-8")
            proc = subprocess.run([sys.executable, str(SHIPPED), "xsec", "--M", str(m), "--y", str(y),
                                   "--sqrt-s", str(rs), "--rapidity-frame", "cm", "--alpha", str(alpha),
                                   "--alpha-label", "test input", "--bosons", "gamma", "--partons", str(pf)],
                                  capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        doc = json.loads(proc.stdout)
        shipped = (doc.get("outputs") or doc)["d2sigma_dM_dy_GeV3"]
        mine = predict.d2sigma_dm_dy(TOY, m, y) * 4.0 * math.pi * alpha ** 2 / 3.0
        self.assertAlmostEqual(mine / shipped, 1.0, places=12)

    def test_profile_has_no_experiment_content(self):
        prof = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(prof["depends_on"], [])
        text = " ".join(f.read_text(encoding="utf-8") for f in ROOT.rglob("*")
                        if f.is_file() and f.suffix in (".py", ".json", ".md") and "tests" not in f.parts)
        for word in ("profiles/experiments", "blinding\":", "luminosity_pb", "experiment:"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
