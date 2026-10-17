"""coalescence.py (Th6): the coalescence coefficient B_A and the coalescence momentum p0, the coalesced invariant
yield, and the Wigner-function factors. Oracles: the closed form B_A = A (4 pi p0^3 / 3 m_N)^(A-1) (Kachelriess et
al. 2019, Eq. 2) and its inverse; it equals Duperray et al. 2005, Eq. 5, (4 pi p0^3 / 3)^(A-1) m_A / m_p^A when
m_A = A m_N; the yield at p_A = A p_p; zeta -> 1 for sigma -> 0 and -> 0 for sigma -> infinity. SYNTHETIC inputs."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "coalescence.py"
sys.path.insert(0, str(SCRIPT.parent))


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


class Coalescence(unittest.TestCase):
    def setUp(self):
        import coalescence as m
        self.m = m

    def test_closed_form_and_inverse(self):
        mn = 0.938
        for a in (2, 3, 4):
            for p0 in (0.06, 0.079, 0.2):
                with self.subTest(A=a, p0=p0):
                    b = self.m.b_from_p0(p0, a, mn)
                    self.assertAlmostEqual(b, a * (4 * math.pi * p0 ** 3 / (3 * mn)) ** (a - 1), delta=1e-15 * b)
                    self.assertAlmostEqual(self.m.p0_from_b(b, a, mn) / p0, 1.0, delta=1e-12)

    def test_two_conventions_agree_when_m_a_is_a_m_n(self):
        mn, p0 = 0.938, 0.079
        for a in (2, 3):
            duperray = (4 * math.pi * p0 ** 3 / 3) ** (a - 1) * (a * mn) / mn ** a
            self.assertAlmostEqual(self.m.b_from_p0(p0, a, mn) / duperray, 1.0, delta=1e-12)

    def test_cli_ba_and_yield(self):
        code, out = run("ba", "--p0-gev", "0.079", "--mass-number", "2", "--nucleon-mass", "proton")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["status"], "ok")
        self.assertIn("nucleon_mass_source", out)
        b2 = out["B_A"]
        with tempfile.TemporaryDirectory() as d:
            spec = Path(d) / "pbar.json"
            spec.write_text(json.dumps({"p_gev": [1.0, 2.0, 4.0], "invariant_yield_gev_minus2": [1e-3, 2e-4, 1e-5]}),
                            encoding="utf-8")
            code, out = run("yield", "--spectrum", str(spec), "--mass-number", "2", "--b-a", str(b2))
            self.assertEqual(code, 0, out)
            row = out["rows"][1]
            self.assertAlmostEqual(row["p_A_gev"], 4.0, delta=1e-12)
            self.assertAlmostEqual(row["invariant_yield_A"], b2 * 2e-4 ** 2, delta=1e-12 * b2 * 4e-8)

    def test_wigner_factors(self):
        self.assertAlmostEqual(self.m.zeta(3.2, 1e-6), 1.0, delta=1e-9)
        self.assertLess(self.m.zeta(3.2, 1e3), 1e-6)
        code, out = run("wigner", "--d-fm", "3.2", "--sigma-fm", "1.0", "--q-gev", "0", "0.1")
        self.assertEqual(code, 0, out)
        z = (3.2 ** 2 / (3.2 ** 2 + 4.0)) ** 1.5
        self.assertAlmostEqual(out["zeta"], z, delta=1e-12)
        self.assertAlmostEqual(out["rows"][0]["weight"], 3 * z, delta=1e-12)
        hbarc = 0.1973269804  # GeV fm
        self.assertAlmostEqual(out["rows"][1]["weight"], 3 * z * math.exp(-(0.1 * 3.2 / hbarc) ** 2), delta=1e-9)

    def test_bad_input(self):
        for args in (("ba", "--p0-gev", "-1", "--mass-number", "2", "--nucleon-mass", "proton"),
                     ("ba", "--p0-gev", "0.08", "--mass-number", "1", "--nucleon-mass", "proton"),
                     ("wigner", "--d-fm", "0", "--sigma-fm", "1", "--q-gev", "0")):
            with self.subTest(args=args):
                code, out = run(*args)
                self.assertEqual(code, 2, out)


if __name__ == "__main__":
    unittest.main()
