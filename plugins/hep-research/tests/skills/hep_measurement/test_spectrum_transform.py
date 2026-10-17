"""spectrum_transform.py (M7): a bin-averaged flux in one spectral variable becomes the bin-averaged flux in another
(Jacobian and bin averaging, not a relabeling), with an isotope-composition model and its covariance.

Oracles: the analytic power-law result for one isotope (mapped edges exactly, arbitrary target edges with the
power-law within-bin shape); the R -> T/A -> R round trip; the statistical covariance through the exact bin factors;
the composition covariance against toys; refusals when Z, A, a mass or the composition is missing. All inputs are
SYNTHETIC (an invented helium-like element with two isotopes and a pure power law)."""
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-measurement" / "scripts" / "spectrum_transform.py"
sys.path.insert(0, str(PLUGIN))
from core import constants  # noqa: E402
from core.kinematics.relativistic import Species, convert  # noqa: E402

GAMMA = 2.7
Z = 2
M3, M4 = constants.nuclear_mass_gev(2, 3), constants.nuclear_mass_gev(2, 4)


def powerlaw_integral(lo, hi, g=GAMMA):
    return (hi ** (1 - g) - lo ** (1 - g)) / (1 - g)


def log_edges(lo, hi, n):
    return [lo * (hi / lo) ** (i / n) for i in range(n + 1)]


def source(edges, cov_rel=None):
    vals = [powerlaw_integral(a, b) / (b - a) for a, b in zip(edges, edges[1:])]
    doc = {"variable": "rigidity", "edges": edges, "values": vals, "Z": Z}
    if cov_rel is not None:
        doc["covariance"] = [[(cov_rel * vals[i]) ** 2 if i == j else 0.0 for j in range(len(vals))]
                             for i in range(len(vals))]
    return doc


def run(doc, *args, expect=None):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "in.json"
        p.write_text(json.dumps(doc), encoding="utf-8")
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), str(p), *args], capture_output=True, text=True,
                           timeout=600)
    out = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {"raw": r.stdout, "stderr": r.stderr}
    if expect is not None:
        assert r.returncode == expect, (r.returncode, out, r.stderr)
    return r.returncode, out


ONE = {"kind": "fixed", "isotopes": [{"A": 4, "fraction": 1.0}]}
TWO = {"kind": "fixed", "isotopes": [{"A": 3, "fraction": 0.2, "fraction_uncertainty": 0.03},
                                     {"A": 4, "fraction": 0.8}]}


class SingleIsotope(unittest.TestCase):
    def test_mapped_edges_are_exact(self):
        edges = log_edges(2.0, 200.0, 12)
        doc = dict(source(edges), composition=ONE)
        _, out = run(doc, "--to", "kinetic_energy_per_nucleon", expect=0)
        sp = Species(Z=Z, A=4, mass=M4)
        new = [convert(e, "rigidity", "kinetic_energy_per_nucleon", sp) for e in edges]
        for a, b in zip(out["edges"], new):
            self.assertAlmostEqual(a / b, 1.0, delta=1e-13)
        for i, (lo, hi) in enumerate(zip(edges, edges[1:])):
            exact = powerlaw_integral(lo, hi) / (new[i + 1] - new[i])
            self.assertAlmostEqual(out["values"][i] / exact, 1.0, delta=1e-12)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["status_label"], "unvalidated")
        self.assertEqual(out["within_bin_shape"], "exact (mapped edges)")

    def test_arbitrary_target_edges_with_powerlaw_shape(self):
        edges = log_edges(1.0, 1000.0, 30)
        doc = dict(source(edges), composition=ONE)
        target = [1.0, 1.7, 3.3, 7.0, 15.0, 40.0, 100.0]  # GeV/n, not aligned with the source edges
        _, out = run(doc, "--to", "kinetic_energy_per_nucleon", "--to-edges", *map(str, target),
                     "--within-bin-shape", "powerlaw", expect=0)
        sp = Species(Z=Z, A=4, mass=M4)
        for i, (lo, hi) in enumerate(zip(target, target[1:])):
            rlo, rhi = (convert(x, "kinetic_energy_per_nucleon", "rigidity", sp) for x in (lo, hi))
            exact = powerlaw_integral(rlo, rhi) / (hi - lo)
            self.assertAlmostEqual(out["values"][i] / exact, 1.0, delta=1e-9)

    def test_round_trip(self):
        edges = log_edges(3.0, 300.0, 10)
        doc = dict(source(edges, cov_rel=0.05), composition=ONE)
        _, out = run(doc, "--to", "kinetic_energy_per_nucleon", expect=0)
        back = {"variable": "kinetic_energy_per_nucleon", "edges": out["edges"], "values": out["values"],
                "covariance": out["covariance"], "Z": Z, "composition": ONE}
        _, rt = run(back, "--to", "rigidity", expect=0)
        for a, b in zip(rt["edges"], edges):
            self.assertAlmostEqual(a / b, 1.0, delta=1e-12)
        for a, b in zip(rt["values"], doc["values"]):
            self.assertAlmostEqual(a / b, 1.0, delta=1e-12)
        for i in range(len(edges) - 1):
            self.assertAlmostEqual(rt["covariance"][i][i] / doc["covariance"][i][i], 1.0, delta=1e-9)

    def test_statistical_covariance_through_the_bin_factors(self):
        edges = log_edges(2.0, 50.0, 6)
        doc = dict(source(edges, cov_rel=0.1), composition=ONE)
        doc["covariance"][0][1] = doc["covariance"][1][0] = 0.3 * math.sqrt(doc["covariance"][0][0] * doc["covariance"][1][1])
        _, out = run(doc, "--to", "kinetic_energy_per_nucleon", expect=0)
        new = out["edges"]
        f = [(edges[i + 1] - edges[i]) / (new[i + 1] - new[i]) for i in range(6)]
        for i in range(6):
            for j in range(6):
                self.assertAlmostEqual(out["covariance"][i][j], f[i] * f[j] * doc["covariance"][i][j],
                                       delta=1e-9 * abs(f[i] * f[j] * doc["covariance"][0][0]))
        self.assertEqual(out["composition_covariance"], [[0.0] * 6 for _ in range(6)])


class TwoIsotopes(unittest.TestCase):
    TARGET = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]

    def test_sum_of_isotopes(self):
        edges = log_edges(1.0, 500.0, 40)
        doc = dict(source(edges), composition=TWO)
        _, out = run(doc, "--to", "kinetic_energy_per_nucleon", "--to-edges", *map(str, self.TARGET),
                     "--within-bin-shape", "powerlaw", expect=0)
        for i, (lo, hi) in enumerate(zip(self.TARGET, self.TARGET[1:])):
            exact = 0.0
            for a, m, f in ((3, M3, 0.2), (4, M4, 0.8)):
                sp = Species(Z=Z, A=a, mass=m)
                rlo, rhi = (convert(x, "kinetic_energy_per_nucleon", "rigidity", sp) for x in (lo, hi))
                exact += f * powerlaw_integral(rlo, rhi) / (hi - lo)
            self.assertAlmostEqual(out["values"][i] / exact, 1.0, delta=1e-9)
        rec = out["transformation_record"]
        self.assertEqual([i["A"] for i in rec["isotopes"]], [3, 4])
        self.assertIn("AME2020", rec["isotopes"][0]["mass_source"])

    def test_composition_covariance_matches_toys(self):
        edges = log_edges(1.0, 500.0, 40)
        doc = dict(source(edges), composition=TWO)
        _, out = run(doc, "--to", "kinetic_energy_per_nucleon", "--to-edges", *map(str, self.TARGET),
                     "--within-bin-shape", "powerlaw", expect=0)
        # toys: f3 ~ N(0.2, 0.03), f4 = 1 - f3; the transform is linear in the fractions
        per = []
        for a, m in ((3, M3), (4, M4)):
            sp = Species(Z=Z, A=a, mass=m)
            row = []
            for lo, hi in zip(self.TARGET, self.TARGET[1:]):
                rlo, rhi = (convert(x, "kinetic_energy_per_nucleon", "rigidity", sp) for x in (lo, hi))
                row.append(powerlaw_integral(rlo, rhi) / (hi - lo))
            per.append(row)
        rng = random.Random(1)
        ys = []
        for _ in range(20000):
            f3 = rng.gauss(0.2, 0.03)
            ys.append([f3 * per[0][k] + (1 - f3) * per[1][k] for k in range(5)])
        n = len(ys)
        mean = [sum(y[k] for y in ys) / n for k in range(5)]
        for k in range(5):
            var = sum((y[k] - mean[k]) ** 2 for y in ys) / (n - 1)
            self.assertAlmostEqual(out["composition_covariance"][k][k] / var, 1.0, delta=0.04)
        k, l = 0, 4
        cov = sum((y[k] - mean[k]) * (y[l] - mean[l]) for y in ys) / (n - 1)
        self.assertAlmostEqual(out["composition_covariance"][k][l] / cov, 1.0, delta=0.05)
        total = out["total_covariance"][2][2]
        self.assertAlmostEqual(total, out["composition_covariance"][2][2], delta=1e-15)  # no statistical input given

    def test_table_composition_equal_to_fixed(self):
        edges = log_edges(1.0, 500.0, 40)
        table = {"kind": "table", "x": [1.0, 500.0], "isotopes": [{"A": 3, "fractions": [0.2, 0.2]},
                                                                  {"A": 4, "fractions": [0.8, 0.8]}]}
        _, fixed = run(dict(source(edges), composition=TWO), "--to", "kinetic_energy_per_nucleon", "--to-edges",
                       *map(str, self.TARGET), "--within-bin-shape", "powerlaw", expect=0)
        _, tab = run(dict(source(edges), composition=table), "--to", "kinetic_energy_per_nucleon", "--to-edges",
                     *map(str, self.TARGET), "--within-bin-shape", "powerlaw", expect=0)
        for a, b in zip(fixed["values"], tab["values"]):
            self.assertAlmostEqual(a / b, 1.0, delta=1e-8)


class Refusals(unittest.TestCase):
    def base(self):
        return dict(source(log_edges(2.0, 200.0, 8)), composition=TWO)

    def test_refused_inputs(self):
        cases = []
        d = self.base()
        del d["Z"]
        cases.append(("no Z", d, ()))
        d = self.base()
        del d["composition"]
        cases.append(("no composition", d, ()))
        d = self.base()
        d["composition"] = {"kind": "fixed", "isotopes": [{"fraction": 1.0}]}
        cases.append(("no A", d, ()))
        d = self.base()
        d["composition"] = {"kind": "fixed", "isotopes": [{"A": 3, "fraction": 0.3}, {"A": 4, "fraction": 0.6}]}
        cases.append(("fractions do not sum to 1", d, ()))
        d = self.base()
        d["Z"], d["composition"] = 30, {"kind": "fixed", "isotopes": [{"A": 64, "fraction": 1.0}]}
        cases.append(("mass not tabulated", d, ()))
        cases.append(("two isotopes without a shape", self.base(), ()))
        cases.append(("target outside the source range", self.base(),
                      ("--to-edges", "0.1", "500", "--within-bin-shape", "constant")))
        d = self.base()
        d["composition"] = {"kind": "plugin", "path": "fractions.py"}
        cases.append(("plugin without opt-in", d, ("--within-bin-shape", "constant")))
        for name, doc, extra in cases:
            with self.subTest(case=name):
                code, out = run(doc, "--to", "kinetic_energy_per_nucleon", *extra)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")
                self.assertTrue(out["error"])

    def test_user_stated_mass_is_accepted_with_its_source(self):
        d = self.base()
        d["Z"], d["composition"] = 30, {"kind": "fixed", "isotopes": [
            {"A": 64, "fraction": 1.0, "mass_gev": 59.5, "mass_source": "SYNTHETIC test value"}]}
        code, out = run(d, "--to", "kinetic_energy_per_nucleon", expect=0)
        self.assertEqual(out["transformation_record"]["isotopes"][0]["mass_source"], "SYNTHETIC test value")

    def test_help(self):
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "--help"], capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0)
        self.assertIn("--within-bin-shape", r.stdout)


if __name__ == "__main__":
    unittest.main()
