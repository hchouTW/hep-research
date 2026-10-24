"""The standard-library searcher of evaluate_design.py search (geant4 program C1.5): Sobol points against the Joe-Kuo
sequence, the exact hypervolume against hand values and against generic WFG, constrained domination, bit-for-bit
reproducibility of NSGA-II, and the DTLZ2 closure test of C1.8 (gate G-C1): the search front reaches at least 95 % of
the true hypervolume within 2 x 10^4 evaluations."""
import math
import random
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN / "skills" / "hep-detector" / "scripts"))
from design_search_lib import hypervolume as HV  # noqa: E402
from design_search_lib import nsga2  # noqa: E402
from design_search_lib.sobol import Sobol  # noqa: E402


def dtlz2(x: list, m: int = 3) -> list:
    """DTLZ2 (Deb, Thiele, Laumanns, Zitzler 2002): the Pareto front is the unit sphere's positive octant."""
    g = sum((xi - 0.5) ** 2 for xi in x[m - 1:])
    out = []
    for i in range(m):
        v = 1 + g
        for xj in x[:m - 1 - i]:
            v *= math.cos(xj * math.pi / 2)
        if i > 0:
            v *= math.sin(x[m - 1 - i] * math.pi / 2)
        out.append(v)
    return out


class SobolPoints(unittest.TestCase):
    def test_first_points(self):
        pts = Sobol(2).points(0, 8)
        self.assertEqual([p[0] for p in pts], [0, 0.5, 0.75, 0.25, 0.375, 0.875, 0.625, 0.125])
        self.assertEqual([p[1] for p in pts], [0, 0.5, 0.25, 0.75, 0.375, 0.875, 0.125, 0.625])
        self.assertEqual(Sobol(5).points(3, 4), Sobol(5).points(0, 7)[3:])

    def test_against_scipy_when_available(self):
        try:
            from scipy.stats import qmc
        except ImportError:
            self.skipTest("SciPy not installed (the direction numbers were taken from its copy)")
        for dim in (1, 7, 64, 128):
            mine = Sobol(dim).points(0, 256)
            ref = qmc.Sobol(dim, scramble=False).random(256).tolist()
            self.assertEqual(mine, ref, dim)

    def test_dimension_limit(self):
        with self.assertRaises(ValueError):
            Sobol(129)


class Hypervolume(unittest.TestCase):
    def test_hand_values(self):
        self.assertAlmostEqual(HV.hypervolume([[1, 2], [2, 1]], [3, 3]), 3.0)
        self.assertAlmostEqual(HV.hypervolume([[0, 0, 0]], [1, 1, 1]), 1.0)
        self.assertAlmostEqual(HV.hypervolume([[0, 0, 0.5], [0.5, 0.5, 0]], [1, 1, 1]), 0.625)
        self.assertAlmostEqual(HV.hypervolume([[0, 0, 0, 0.5], [0.5, 0.5, 0.5, 0]], [1, 1, 1, 1]), 0.5 + 0.125 - 0.0625)
        self.assertEqual(HV.hypervolume([[2, 0]], [1, 1]), 0.0)  # outside the reference point
        self.assertEqual(HV.hypervolume([[0, math.inf]], [1, 1]), 0.0)

    def test_three_objective_sweep_equals_generic_wfg(self):
        rng = random.Random(4)
        for _ in range(20):
            pts = [[rng.random() for _ in range(3)] for _ in range(rng.randrange(1, 40))]
            ref = [1.0, 1.0, 1.0]
            generic = HV._wfg_generic(HV.nondominated(pts), ref)
            self.assertAlmostEqual(HV.hypervolume(pts, ref), generic, places=12)

    def test_duplicates_and_dominated_points_add_nothing(self):
        base = [[0.2, 0.5, 0.4], [0.5, 0.2, 0.3]]
        self.assertAlmostEqual(HV.hypervolume(base + [base[0], [0.6, 0.6, 0.6]], [1, 1, 1]),
                               HV.hypervolume(base, [1, 1, 1]), places=14)


class Domination(unittest.TestCase):
    def test_constrained_domination(self):
        a = nsga2.Individual([], [1.0, 1.0], 0.0)
        b = nsga2.Individual([], [0.0, 0.0], 0.5)
        c = nsga2.Individual([], [0.0, 0.0], 0.2)
        self.assertTrue(nsga2.constrained_dominates(a, b))  # feasible beats infeasible whatever the objectives
        self.assertTrue(nsga2.constrained_dominates(c, b))  # the smaller violation wins
        self.assertFalse(nsga2.constrained_dominates(b, c))
        d = nsga2.Individual([], [0.5, 2.0], 0.0)
        self.assertFalse(nsga2.constrained_dominates(a, d) or nsga2.constrained_dominates(d, a))


class Searcher(unittest.TestCase):
    def run_dtlz2(self, pop: int, gens: int, seed: int = 12345):
        genes = [{"type": "real", "lo": 0.0, "hi": 1.0} for _ in range(12)]
        archive: list = []

        def evaluate(g):
            ind = nsga2.Individual(genome=g, objectives=dtlz2(g))
            archive.append(ind.objectives)
            return ind
        settings = {"seed": seed, "population": pop, "generations": gens, "eta_c": 15, "eta_m": 20,
                    "p_crossover": 0.9, "p_mutation": 1 / 12, "window": None, "min_improvement": 0.0}
        init = [nsga2.from_unit(genes, u) for u in Sobol(12).points(1, pop)]
        res = nsga2.run(genes, init, evaluate, lambda g: g, lambda p: 0.0, settings, pop * (gens + 1))
        return res, archive

    def test_reproducible_bit_for_bit(self):
        a, arch_a = self.run_dtlz2(20, 5)
        b, arch_b = self.run_dtlz2(20, 5)
        self.assertEqual(arch_a, arch_b)
        self.assertEqual([i.genome for i in a["population"]], [i.genome for i in b["population"]])
        c, arch_c = self.run_dtlz2(20, 5, seed=1)
        self.assertNotEqual(arch_a, arch_c)

    def test_mixed_genes_stay_in_range(self):
        genes = [{"type": "real", "lo": -1.0, "hi": 2.0}, {"type": "int", "lo": 3, "hi": 9},
                 {"type": "cat", "n": 3}, {"type": "bit"}]
        rng = random.Random(1)
        settings = {"p_crossover": 1.0, "p_mutation": 1.0, "eta_c": 2.0, "eta_m": 2.0}
        a, b = [0.0, 3, 0, True], [1.5, 9, 2, False]
        for _ in range(500):
            a, b = nsga2.vary(genes, a, b, settings, rng)
            for g in (a, b):
                self.assertTrue(-1.0 <= g[0] <= 2.0)
                self.assertTrue(isinstance(g[1], int) and 3 <= g[1] <= 9)
                self.assertIn(g[2], (0, 1, 2))
                self.assertIsInstance(g[3], bool)

    def test_dtlz2_closure(self):
        """C1.8: 3 objectives, 12 variables, 200 x 100 = 2 x 10^4 evaluations; the search front (non-dominated set of
        every evaluated point) covers at least 95 % of the true hypervolume r^3 - pi/6 at r = 1.1."""
        res, archive = self.run_dtlz2(200, 99)
        self.assertEqual(res["evaluations"], 20000)
        ref = [1.1, 1.1, 1.1]
        true = 1.1 ** 3 - math.pi / 6
        front_hv = HV.hypervolume(archive, ref)
        self.assertGreaterEqual(front_hv / true, 0.95, front_hv / true)
        self.assertLess(front_hv, true)


if __name__ == "__main__":
    unittest.main()
