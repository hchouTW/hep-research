"""kinematics.py (Th7): the CLI over core/kinematics/fourvector.py. Oracles: a two-body momentum from the Kallen
function, the antiproton threshold 7 m_p (beam energy), a boost that preserves the invariant mass, s + t + u, and
masses named from core/constants with their source. Bad input exits 2 with JSON. Inputs are SYNTHETIC."""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "kinematics.py"


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


class KinematicsCli(unittest.TestCase):
    def test_two_body_with_numbers_and_names(self):
        code, out = run("two-body", "3.0", "1.0", "0")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["result"]["p"], 8.0 / 6.0, delta=1e-12)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["status_label"], "unvalidated")
        code, out = run("two-body", "K0", "pi+", "pi+")
        self.assertEqual(code, 0)
        self.assertEqual(out["masses"]["pi+"]["edition"], "PDG 2026")
        self.assertAlmostEqual(out["result"]["p"], math.sqrt(0.497611 ** 2 / 4 - 0.13957039 ** 2), delta=1e-9)

    def test_threshold(self):
        code, out = run("threshold", "--beam", "0.938", "--target", "0.938", "--final", "0.938", "0.938", "0.938", "0.938")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["result"]["beam_energy"], 7 * 0.938, delta=1e-12)

    def test_boost_and_invariant_mass(self):
        code, out = run("boost", "--vector", "5,1,2,3", "--beta", "0.1,0.2,-0.3")
        self.assertEqual(code, 0)
        m_before = math.sqrt(25 - 1 - 4 - 9)
        code2, out2 = run("invariant-mass", "--vector", ",".join(str(x) for x in out["result"]["vector"]))
        self.assertEqual(code2, 0)
        self.assertAlmostEqual(out2["result"]["mass"], m_before, delta=1e-12)
        code, out = run("boost", "--vector", "5,1,2,3", "--to-rest-of", "5,1,2,3")
        self.assertAlmostEqual(out["result"]["vector"][0], m_before, delta=1e-12)

    def test_mandelstam_sum(self):
        m = 0.5
        p = math.sqrt(4.0 - m * m)
        code, out = run("mandelstam", "--p1", f"2,0,0,{p}", "--p2", f"2,0,0,{-p}", "--p3", f"2,{p},0,0",
                        "--p4", f"2,{-p},0,0")
        self.assertEqual(code, 0)
        r = out["result"]
        self.assertAlmostEqual(r["s"] + r["t"] + r["u"], 4 * m * m, delta=1e-12)

    def test_lifetime_from_a_named_particle(self):
        code, out = run("lifetime", "--particle", "pi+")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["result"]["ctau_m"], 2.6033e-8 * 299792458.0, delta=1e-9)
        self.assertIn("PDG", out["input_source"]["source"])

    def test_dalitz_and_rapidity(self):
        code, out = run("dalitz", "1.86484", "0.493677", "0.13957039", "0.1349768", "--m12sq", "1.0")
        self.assertEqual(code, 0)
        lo, hi = out["result"]["m23sq_range"]
        self.assertLess(lo, hi)
        code, out = run("rapidity", "--vector", "5,1,2,3")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["result"]["rapidity"], 0.5 * math.log(8 / 2), delta=1e-12)

    def test_bad_input_exits_2(self):
        for args in (("two-body", "0.2", "pi+", "pi+"), ("two-body", "tachyon", "0", "0"),
                     ("boost", "--vector", "1,0,0", "--beta", "0,0,0.5"), ("lifetime", "--width-gev", "-1")):
            with self.subTest(args=args):
                code, out = run(*args)
                self.assertEqual(code, 2)
                self.assertEqual(out["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
