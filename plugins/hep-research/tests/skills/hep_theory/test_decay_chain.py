"""decay_chain.py (Th12): Bateman solutions for linear chains and a matrix exponential for branches, production and
nearly equal decay constants; half-lives from core/constants (NUBASE2020) with their edition. Oracles: the two-member
closed form; the daughter-to-parent activity ratio tends to 1 at secular equilibrium; the matrix exponential equals
Bateman where both apply; the neutron and tritium Q values from AME2020 equal the tabulated beta-decay energies.
Amounts and rates are SYNTHETIC."""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "decay_chain.py"
PHYS = PLUGIN / "skills" / "hep-theory" / "scripts" / "physical_data.py"
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(PLUGIN))
import decay_chain as dc  # noqa: E402

LN2 = math.log(2.0)


def run(script, *args):
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


class Solutions(unittest.TestCase):
    def test_two_member_closed_form(self):
        l1, l2, n0 = 1e-3, 5e-3, 1e6
        for t in (0.0, 10.0, 300.0, 5000.0):
            n = dc.bateman([l1, l2], [n0, 0.0], t)
            self.assertAlmostEqual(n[0], n0 * math.exp(-l1 * t), delta=1e-9 * n0)
            self.assertAlmostEqual(n[1], n0 * l1 / (l2 - l1) * (math.exp(-l1 * t) - math.exp(-l2 * t)), delta=1e-9 * n0)

    def test_matrix_equals_bateman_on_a_linear_chain(self):
        lam = [2e-4, 3e-3, 7e-2, 0.0]  # last member stable
        n0 = [1e8, 2e5, 0.0, 10.0]
        edges = [(0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0)]
        for t in (1.0, 100.0, 1e4):
            b = dc.bateman(lam, n0, t)
            m = dc.matrix_solution(lam, edges, n0, [0.0] * 4, t)
            for x, y in zip(b, m):
                self.assertAlmostEqual(x, y, delta=1e-8 * max(n0))

    def test_nearly_equal_constants_use_the_matrix(self):
        lam = [1e-3, 1e-3 * (1 + 1e-9)]
        r = dc.solve(lam, [(0, 1, 1.0)], [1e6, 0.0], [0.0, 0.0], [1000.0], method="auto")
        self.assertEqual(r["method"], "matrix-exponential")
        t = 1000.0  # the limit lambda1 = lambda2: N2 = N0 lambda t e^{-lambda t}
        self.assertAlmostEqual(r["amounts"][0][1], 1e6 * 1e-3 * t * math.exp(-1e-3 * t), delta=1e-2)

    def test_branching_and_production(self):
        lam = [1e-2, 1e-3, 2e-3]
        edges = [(0, 1, 0.3), (0, 2, 0.7)]
        r = dc.solve(lam, edges, [0.0, 0.0, 0.0], [5.0, 0.0, 0.0], [1e5], method="auto")
        n = r["amounts"][0]
        # at equilibrium with production R into the parent: A_parent = R, A_d = R x fraction
        self.assertAlmostEqual(n[0] * lam[0], 5.0, delta=1e-6)
        self.assertAlmostEqual(n[1] * lam[1], 1.5, delta=1e-3)
        self.assertAlmostEqual(n[2] * lam[2], 3.5, delta=1e-3)


class Cli(unittest.TestCase):
    def test_secular_equilibrium_with_nubase_half_lives(self):
        code, out = run(SCRIPT, "--chain", "238U", "234Th", "--initial", "238U=1e20", "--times", 0, 1, 3,
                        "--time-unit", "y")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["half_lives"]["238U"]["edition"], "AME2020 + NUBASE2020")
        ratios = [r["activity_ratios"]["234Th/238U"] for r in out["results"]]
        self.assertEqual(ratios[0], 0.0)
        self.assertAlmostEqual(ratios[-1], 1.0, delta=1e-9)  # 3 y >> 24 d
        self.assertIn("secular", out["equilibrium"]["234Th/238U"])

    def test_user_half_life_and_branch(self):
        code, out = run(SCRIPT, "--chain", "A", "B", "C", "--half-life", "A=10:s", "B=20:s", "C=stable",
                        "--branch", "A:C:0.25", "--initial", "A=1000", "--times", 0, 5, "--time-unit", "s")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["method"], "matrix-exponential")
        last = out["results"][-1]["amounts"]
        self.assertAlmostEqual(sum(last.values()), 1000.0, delta=1e-6)  # nothing leaves the chain

    def test_bad_input_exits_2(self):
        for args in (("--chain", "238U", "--initial", "238U=1", "--times", "-1", "--time-unit", "s"),
                     ("--chain", "999Xx", "--initial", "999Xx=1", "--times", 1, "--time-unit", "s"),
                     ("--chain", "A", "B", "--half-life", "A=1:s", "B=1:s", "--branch", "A:B:1.5",
                      "--initial", "A=1", "--times", 1, "--time-unit", "s")):
            with self.subTest(args=args):
                code, out = run(SCRIPT, *args)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")

    def test_neutron_and_tritium_q_values_from_ame2020(self):
        for parent, tabulated in (("n", 782.3470), ("3H", 18.59202)):  # AME2020 mass.mas20 "B-" column, keV
            code, out = run(PHYS, "qvalue", parent, "--mode", "beta-")
            self.assertEqual(code, 0, out)
            self.assertAlmostEqual(out["qvalue"]["value_keV"], tabulated, delta=5e-4)


if __name__ == "__main__":
    unittest.main()
