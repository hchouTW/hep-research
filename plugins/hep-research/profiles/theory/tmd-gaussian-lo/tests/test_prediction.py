"""theory:tmd-gaussian-lo prediction tests: checks pass, the Drell-Yan Sivers function carries the opposite sign,
consistency checks (same author, not independent) against the shipped skills/hep-theory/scripts/tmd_gaussian.py (sidis, dy, sivers), bad inputs
refused, no hard-coded checks, no experiment content."""
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
SHIPPED = ROOT.parents[2] / "skills" / "hep-theory" / "scripts" / "tmd_gaussian.py"


def shipped(*args):
    proc = subprocess.run([sys.executable, str(SHIPPED), *map(str, args)], capture_output=True, text=True, timeout=120)
    return proc.returncode, json.loads(proc.stdout)


class SiversSignTests(unittest.TestCase):
    def test_dy_sivers_function_is_opposite(self):
        for k in (0.1, 0.4, 0.9):
            s = predict.sivers_function(k, 0.3, 0.6, 0.25, 0.36, "SIDIS")
            dy = predict.sivers_function(k, 0.3, 0.6, 0.25, 0.36, "DY")
            self.assertGreater(s, 0)
            self.assertEqual(dy, -s)

    def test_unknown_process_refused(self):
        with self.assertRaises(predict.InputError):
            predict.sivers_function(0.3, 0.3, 0.6, 0.25, 0.36, "e+e-")

    def test_shipped_sivers_rule_agrees(self):
        s = predict.sivers_function(0.4, 0.3, 0.6, 0.25, 0.36, "SIDIS")
        code, out = shipped("sivers", "--sidis-value", s, "--notation", "DeltaN_f")
        self.assertEqual(code, 0, out)
        self.assertAlmostEqual(out["outputs"]["drell_yan_value"], predict.sivers_function(0.4, 0.3, 0.6, 0.25, 0.36,
                                                                                         "DY"), places=15)


@unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required")
class PredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = predict.predict(CFG)

    def test_all_checks_pass(self):
        self.assertTrue(all(self.p["checks"].values()), self.p["checks"])

    def test_no_hard_coded_checks(self):
        self.assertNotIn("units", " ".join(self.p["checks"]))
        self.assertIn("units", self.p["declarations"])

    def test_sign_rule_is_a_declaration_not_a_check(self):
        self.assertNotIn("sivers_dy_opposite_to_sidis", self.p["checks"])
        self.assertIn("Trento Eq. 14", self.p["declarations"]["sivers_sign_rule"])

    def test_zero_sivers_values_are_positive_zero(self):
        for r in self.p["sivers_function"]:
            for v in (r["Delta_N_f_SIDIS"], r["Delta_N_f_DY"]):
                if v == 0:
                    self.assertEqual(str(v), "0.0")

    def test_prediction_dy_sivers_rows_opposite(self):
        rows = self.p["sivers_function"]
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(r["Delta_N_f_DY"], -r["Delta_N_f_SIDIS"])
        self.assertTrue(any(r["Delta_N_f_SIDIS"] != 0 for r in rows))

    def test_shipped_sidis_agrees(self):
        base = {f: 0.0 for q in ("d", "u", "s", "c", "b") for f in (q, q + "bar")}
        f1, d1 = dict(base), dict(base)
        for fl in CFG["flavours"]:
            f1[fl["name"]], d1[fl["name"]] = fl["f"], fl["D"]
        with tempfile.TemporaryDirectory() as tmp:
            pf = Path(tmp) / "partons.json"
            pf.write_text(json.dumps({"f1": f1, "D1": d1}), encoding="utf-8")
            code, out = shipped("sidis", "--x", CFG["x"], "--z", CFG["z"], "--partons", pf, "--kperp2",
                                CFG["kperp2_gev2"], "--pperp2", CFG["pperp2_gev2"], "--PhT", *CFG["PhT_gev"])
        self.assertEqual(code, 0, out)
        self.assertAlmostEqual(out["outputs"]["PT2_width_GeV2"], self.p["PT2_width_gev2"], places=14)
        for mine, theirs in zip(self.p["F_UU_T"], out["outputs"]["rows"]):
            self.assertAlmostEqual(mine["F_UU_T"] / theirs["F_UU_T"], 1.0, places=12)

    def test_shipped_dy_agrees(self):
        d = CFG["drell_yan"]
        code, out = shipped("dy", "--k1perp2", d["k1perp2_gev2"], "--k2perp2", d["k2perp2_gev2"], "--qT", *d["qT_gev"])
        self.assertEqual(code, 0, out)
        for mine, theirs in zip(self.p["drell_yan_qT_shape"], out["outputs"]["rows"]):
            self.assertAlmostEqual(mine["shape_per_gev2"] / theirs["shape_per_GeV2"], 1.0, places=12)

    def test_hand_value_fuut_at_zero(self):
        w = CFG["pperp2_gev2"] + CFG["z"] ** 2 * CFG["kperp2_gev2"]
        coll = CFG["x"] * sum(float(Fraction(f["charge"])) ** 2 * f["f"] * f["D"] for f in CFG["flavours"])
        self.assertAlmostEqual(self.p["F_UU_T"][0]["F_UU_T"], coll / (math.pi * w), places=14)

    def test_bad_inputs_refused(self):
        for change in ({"z": 1.5}, {"kperp2_gev2": 0.0}, {"PhT_gev": [-0.1]}):
            with self.subTest(change=change), self.assertRaises(predict.InputError):
                predict.predict(dict(CFG, **change))

    def test_profile_has_no_experiment_content(self):
        prof = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(prof["depends_on"], [])
        text = " ".join(f.read_text(encoding="utf-8") for f in ROOT.rglob("*")
                        if f.is_file() and f.suffix in (".py", ".json", ".md") and "tests" not in f.parts)
        for word in ("profiles/experiments", "blinding\":", "luminosity_pb", "experiment:", "HERMES", "COMPASS"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
