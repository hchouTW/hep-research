"""sum_rules.py (Th14): sum-rule integrals of toy PDFs against analytic Beta-function integrals.

Toy: x q_v = N x^a (1 - x)^b, so int q_v dx = N B(a, b + 1) and int x q_v dx = N B(a + 1, b + 1). Tolerances fixed
before comparing: 5e-4 absolute for the integrals on a 400-point log grid; exact power-law extrapolation to 1e-12.
"""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-theory/scripts/sum_rules.py"


def beta(a, b):
    return math.gamma(a) * math.gamma(b) / math.gamma(a + b)


def toy_table(n=400, xmin=1e-7):
    xs = [xmin ** (1 - i / (n - 1)) for i in range(n)]  # log grid up to x = 1
    # valence: x u_v = Nu x^0.7 (1-x)^3 with int u_v = 2; x d_v = Nd x^0.7 (1-x)^4 with int d_v = 1
    nu, nd = 2 / beta(0.7, 4), 1 / beta(0.7, 5)
    sea = lambda x, n_, b: n_ * x ** 1.1 * (1 - x) ** b  # x qbar, finite momentum, zero number for q = qbar
    cols = {"x": xs, "representation": "xf"}
    cols["ubar"] = [sea(x, 0.1, 7) for x in xs]
    cols["dbar"] = [sea(x, 0.12, 7) for x in xs]
    cols["u"] = [nu * x ** 0.7 * (1 - x) ** 3 + cols["ubar"][i] for i, x in enumerate(xs)]
    cols["d"] = [nd * x ** 0.7 * (1 - x) ** 4 + cols["dbar"][i] for i, x in enumerate(xs)]
    for q, n_ in (("s", 0.05), ("c", 0.02), ("b", 0.01)):
        cols[q] = [sea(x, n_, 8) for x in xs]
        cols[q + "bar"] = list(cols[q])
    momentum_quarks = (nu * beta(1.7, 4) + nd * beta(1.7, 5)
                       + 2 * (0.1 + 0.12) * beta(2.1, 8) + 2 * (0.05 + 0.02 + 0.01) * beta(2.1, 9))
    ng = (1 - momentum_quarks) / beta(1.9, 6)  # x g = Ng x^0.9 (1-x)^5 closes the momentum sum rule exactly
    cols["g"] = [ng * x ** 0.9 * (1 - x) ** 5 for x in xs]
    return cols


def run(table, *args):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "t.json"
        p.write_text(json.dumps(table))
        r = subprocess.run([sys.executable, str(SCRIPT), "--table", str(p), *args], capture_output=True, text=True, timeout=60)
    return r.returncode, json.loads(r.stdout)


class SumRules(unittest.TestCase):
    def test_toy_sum_rules(self):
        t = toy_table()
        for rule, value in (("momentum", 1.0), ("number:u", 2.0), ("number:d", 1.0), ("number:s", 0.0),
                            ("adler-lo", 2.0), ("gls-lo", 3.0)):
            code, out = run(t, "--rule", rule, "--expected", str(value), "--tolerance", "5e-4")
            self.assertEqual(code, 0, (rule, out))
            self.assertEqual(out["checks"][0]["result"], "pass", (rule, out["checks"]))
            self.assertLess(out["outputs"]["convergence_estimate"], 5e-3, rule)

    def test_f_and_xf_representations_agree(self):
        t = toy_table(n=60)
        f_table = {"representation": "f", "x": t["x"]}
        for k in ("u", "ubar", "d", "dbar"):
            f_table[k] = [v / x for v, x in zip(t[k], t["x"])]
        _, a = run(t, "--rule", "number:u")
        _, b = run(f_table, "--rule", "number:u")
        self.assertAlmostEqual(a["outputs"]["integral_in_range"], b["outputs"]["integral_in_range"], places=12)

    def test_power_law_extrapolation_is_exact_for_a_power_law(self):
        xs = [0.01 * (100 ** (i / 199)) for i in range(200)]  # 0.01 .. 1
        table = {"representation": "f", "x": xs, "u": [x ** -0.5 for x in xs], "ubar": [0.0] * len(xs)}
        _, out = run(table, "--rule", "number:u")
        below = out["outputs"]["below_xmin"]
        self.assertAlmostEqual(below["p"], -0.5, places=12)
        self.assertAlmostEqual(below["integral"], 0.2, places=12)  # int_0^0.01 x^-1/2 dx
        self.assertEqual(out["outputs"]["above_xmax"]["integral"], 0.0)

    def test_divergent_small_x_is_reported_not_summed(self):
        xs = [10 ** (-3 + 3 * i / 49) for i in range(50)]
        table = {"representation": "f", "x": xs, "u": [1 / x ** 1.2 for x in xs], "ubar": [0.0] * 50}
        code, out = run(table, "--rule", "number:u")
        self.assertEqual(code, 0)
        self.assertIsNone(out["outputs"]["below_xmin"]["integral"])
        self.assertIsNone(out["outputs"]["total_with_extrapolation"])
        self.assertEqual(out["checks"], [])

    def test_requested_check_that_cannot_run_is_incomplete(self):
        # review I1: --expected given, extrapolated total undefined -> not a pass (exit 3, incomplete)
        table = {"representation": "f", "x": [0.01, 0.1, 0.5, 0.9], "u": [1, 1, 1, 1], "ubar": [2, 0, 0, 0]}
        code, out = run(table, "--rule", "number:u", "--expected", "2", "--tolerance", "0.01")
        self.assertEqual(code, 3, out)
        self.assertEqual(out["status"], "incomplete")

    def test_violation_is_a_failed_verdict(self):
        t = toy_table(n=100)
        t["u"] = [1.1 * v for v in t["u"]]
        code, out = run(t, "--rule", "number:u", "--expected", "2", "--tolerance", "1e-3")
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "failed")

    def test_rejections(self):
        t = toy_table(n=10)
        bad = [dict(t, x=list(reversed(t["x"]))), {k: v for k, v in t.items() if k != "g"},
               dict(t, u=t["u"][:-1]), dict(t, representation="logx")]
        for table in bad:
            code, out = run(table, "--rule", "momentum")
            self.assertEqual(code, 2, out)
            self.assertEqual(out["status"], "rejected")
        code, _ = run(t, "--rule", "number:t")
        self.assertEqual(code, 2)
        code, _ = run(t, "--rule", "momentum", "--expected", "1")
        self.assertEqual(code, 2)


def polarized_table(n=400, xmin=1e-7):
    """Toy helicity densities x Dq = N x^a (1-x)^b with Beta-function first moments."""
    xs = [xmin ** (1 - i / (n - 1)) for i in range(n)]
    forms = {"Du": (0.9, 0.7, 3), "Dd": (-0.4, 0.7, 4), "Ds": (-0.02, 1.0, 7),
             "Dubar": (0.01, 1.0, 7), "Ddbar": (-0.015, 1.0, 7), "Dsbar": (-0.02, 1.0, 7)}
    t = {"representation": "xf", "x": xs}
    moments = {}
    for k, (amp, a, b) in forms.items():
        t[k] = [amp * x ** a * (1 - x) ** b for x in xs]
        moments[k] = amp * beta(a, b + 1)
    return t, moments


class PolarizedSumRules(unittest.TestCase):
    def test_g1_moments_and_bjorken(self):
        t, m = polarized_table()
        up, dn, st = m["Du"] + m["Dubar"], m["Dd"] + m["Ddbar"], m["Ds"] + m["Dsbar"]
        gp = 0.5 * (4 / 9 * up + 1 / 9 * dn + 1 / 9 * st)
        gn = 0.5 * (4 / 9 * dn + 1 / 9 * up + 1 / 9 * st)  # isospin: Du <-> Dd for the neutron
        for rule, value in (("g1-moment:p", gp), ("g1-moment:n", gn), ("bjorken-lo", (up - dn) / 6)):
            code, out = run(t, "--rule", rule, "--expected", repr(value), "--tolerance", "5e-4")
            self.assertEqual(code, 0, (rule, out))
            self.assertEqual(out["checks"][0]["result"], "pass", (rule, out["checks"]))

    def test_ellis_jaffe_reference(self):
        t, m = polarized_table()
        ga, a8 = 1.27, 0.585  # inputs of the test (their source is the user's); EJ: Gamma_1^p = gA/12 + 5 a8/36
        code, out = run(t, "--rule", "ellis-jaffe:p", "--gA", str(ga), "--a8", str(a8))
        self.assertEqual(code, 0, out)
        self.assertAlmostEqual(out["outputs"]["ellis_jaffe_prediction"], ga / 12 + 5 * a8 / 36, places=12)
        self.assertIn("heuristic-argument", out["outputs"]["ellis_jaffe_status"])
        code, _ = run(t, "--rule", "ellis-jaffe:p")
        self.assertEqual(code, 2)  # gA and a8 are required inputs

    def test_eq43_anchor_neutron_ellis_jaffe_and_charm(self):
        t, m = polarized_table()
        a3 = (m["Du"] + m["Dubar"]) - (m["Dd"] + m["Ddbar"])
        a8 = (m["Du"] + m["Dubar"]) + (m["Dd"] + m["Ddbar"]) - 2 * (m["Ds"] + m["Dsbar"])
        a0 = (m["Du"] + m["Dubar"]) + (m["Dd"] + m["Ddbar"]) + (m["Ds"] + m["Dsbar"])
        gp = (0.75 * a3 + 0.25 * a8 + a0) / 9  # Kuhn, Chen, Leader Eq. 43, independent of the code's e_q^2 sum
        code, out = run(t, "--rule", "g1-moment:p", "--expected", repr(gp), "--tolerance", "5e-4")
        self.assertEqual(out["checks"][0]["result"], "pass", out["checks"])
        _, out = run(t, "--rule", "ellis-jaffe:n", "--gA", "1.27", "--a8", "0.585")
        self.assertAlmostEqual(out["outputs"]["ellis_jaffe_prediction"], -1.27 / 12 + 5 * 0.585 / 36, places=12)
        # review: a charm helicity column enters g_1 with e_c^2 = 4/9 instead of being ignored
        tc = dict(t, Dc=[0.01 * x ** 0.5 for x in t["x"]], Dcbar=[0.0] * len(t["x"]))
        _, base = run(t, "--rule", "g1-moment:p")
        _, withc = run(tc, "--rule", "g1-moment:p")
        diff = withc["outputs"]["integral_in_range"] - base["outputs"]["integral_in_range"]
        self.assertAlmostEqual(diff, 0.5 * 4 / 9 * 0.01 * 2 * (1 - 1e-7 ** 0.5), delta=2e-5)  # columns hold x Dc
        # review: --gA/--a8 with another rule are rejected, not ignored
        code, _ = run(t, "--rule", "bjorken-lo", "--gA", "1.27")
        self.assertEqual(code, 2)

    def test_unpolarized_rule_on_polarized_table_rejected(self):
        t, _ = polarized_table(n=20)
        code, _ = run(t, "--rule", "momentum")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
