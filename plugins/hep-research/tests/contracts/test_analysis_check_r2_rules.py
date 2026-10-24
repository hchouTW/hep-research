"""Cross-artifact check Phase 2, release R2 rule fixes that need more than a gap probe. A3 (check-context 1.1.0): an
outcome that read a bundle-supplied coverage contract is declaration-based. r-comp.factor_values 1.1.0 (G4, DR-6),
whose relative tolerance comes from declared significant digits and never from the factor table. A table whose values
are the true values rounded to the declared digits passes for any powers (the bound sum|power| * u); a real break, an
undeclared table and a declaration the values contradict get the 1e-9 default. The R2 tests of the model-card and
run-lineage rules (G5, G6, G7, G13) went with those suites in 0.28.0. Synthetic numbers only."""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class Env:
    def __init__(self, powers: dict, doc: dict):
        self.catalog = {"compositions": [{"composition_id": "c", "parent": "p",
                                          "children": [{"effect": e, "power": w} for e, w in powers.items()]}]}
        self.items = {"t": {"role": "calibration", "doc": doc}}


def table(parent, children: dict, digits=None, tolerance=None) -> dict:
    doc = {"factor_table_version": "1.0.0", "factors": {"p": {"values": parent}, **{e: {"values": v} for e, v in children.items()}}}
    if digits is not None:
        doc["significant_digits"] = digits
    if tolerance is not None:
        doc["tolerance"] = {"relative": tolerance}
    return doc


def run(powers: dict, doc: dict) -> dict:
    from contracts.analysis_checks.rules import r_comp_factor_values
    return r_comp_factor_values({"subject": {"composition": "c", "factor_table": "t"}}, Env(powers, doc))


def rounded(x: float, d: int) -> float:
    return float(f"{x:.{d - 1}e}")


class FactorTolerance(unittest.TestCase):
    def test_rounded_tables_pass_and_a_real_break_fails(self):
        rng = random.Random(20261023)
        for trial in range(400):
            d = rng.randint(2, 7)
            powers = {f"e{i}": rng.choice([-2, -1, 1, 2]) for i in range(rng.randint(1, 3))}
            true = {e: [10 ** rng.uniform(-3, 3) for _ in range(6)] for e in powers}
            parent = [1.0] * 6
            for e, w in powers.items():
                parent = [a * b ** w for a, b in zip(parent, true[e])]
            children = {e: [rounded(x, d) for x in v] for e, v in true.items()}
            with self.subTest(trial=trial, d=d, powers=powers):
                o = run(powers, table([rounded(x, d) for x in parent], children, digits=d))
                self.assertEqual(o["state"], "satisfied", o["message"])
                broken = [rounded(x, d) for x in parent]
                broken[3] = rounded(broken[3] * (1 + 4 * o["tolerance"]["relative"]), d)
                self.assertEqual(run(powers, table(broken, children, digits=d))["state"], "violated")

    def test_undeclared_digits_use_the_default(self):
        o = run({"a": 1, "b": 1}, table([1.0, 3.0], {"a": [0.5, 1.0], "b": [2.0, 2.0]}))
        self.assertEqual((o["state"], o["tolerance"]["relative"]), ("violated", 1e-9))
        o = run({"a": 1}, table([0.333], {"a": [1 / 3]}))
        self.assertEqual(o["state"], "violated")

    def test_the_tables_own_tolerance_is_not_used(self):
        o = run({"a": 1, "b": 1}, table([1.0, 3.0], {"a": [0.5, 1.0], "b": [2.0, 2.0]}, tolerance=0.6))
        self.assertEqual(o["state"], "violated")
        self.assertIn("own tolerance is not used", o["message"])

    def test_a_declaration_the_values_contradict_is_not_used(self):
        # 0.3333 against 0.3333 passes at 4 declared digits; against 0.33333 (5 digits) the declaration is false
        self.assertEqual(run({"a": 1}, table([0.3333], {"a": [0.3333]}, digits=4))["state"], "satisfied")
        o = run({"a": 1}, table([0.3333], {"a": [0.33333]}, digits=4))
        self.assertEqual(o["state"], "violated")
        self.assertIn("more than the declared 4", o["tolerance"]["basis"])

    def test_one_digit_tables_tolerate_what_one_digit_cannot_resolve(self):
        # the probe table at 1 declared digit: 3 = 1 x 2 cannot be refuted by values rounded to one digit
        o = run({"a": 1, "b": 1}, table([1.0, 3.0], {"a": [0.5, 1.0], "b": [2.0, 2.0]}, digits=1))
        self.assertEqual(o["state"], "satisfied")
        self.assertAlmostEqual(o["tolerance"]["relative"], 1.5)

    def test_powers_count_by_absolute_value(self):
        from contracts.analysis_checks.rules import _factor_tolerance
        comp = {"children": [{"effect": "a", "power": -2}, {"effect": "b", "power": 1}]}
        tol, _ = _factor_tolerance({"significant_digits": 3}, comp, {"p": [1.0], "a": [1.0], "b": [1.0]})
        self.assertAlmostEqual(tol, 4 * 0.5e-2)

    def test_significant_digits_shape(self):
        from contracts.analysis_check import factor_table_shape
        base = table([1.0], {"a": [1.0]})
        self.assertEqual(factor_table_shape(dict(base, significant_digits=3)), [])
        for bad in (0, 18, 2.5, True, "3"):
            with self.subTest(bad=bad):
                self.assertIn("significant_digits is an integer from 1 to 17", factor_table_shape(dict(base, significant_digits=bad)))

    def test_significant_digits_of_written_numbers(self):
        from contracts.analysis_checks.rules import _significant_digits
        for x, n in ((2.0, 1), (0.5, 1), (0.3333, 4), (1200, 2), (1.25e-7, 3), (1 / 3, 16), (-0.0750, 2)):
            with self.subTest(x=x):
                self.assertEqual(_significant_digits(x), n)




def _case_modules():
    sys.path.insert(0, str(ROOT / "tests" / "contracts"))
    import analysis_check_cases as cases
    return cases, None


def _report(bundle: Path, root: Path) -> dict:
    from contracts import analysis_check as ac
    view, diags = ac.load_subject(bundle, root)
    return ac.evaluate(view, diags)


class BundleCoverageFlag(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)

    def outcomes(self, name, *variants):
        cases, _ = _case_modules()
        root = Path(self.td.name) / name
        return _report(cases.positive_case(root, cases.both(*variants)), root)["obligations"]

    def test_outcomes_on_bundle_coverage_are_declaration_based_in_1_1_0(self):
        cases, _ = _case_modules()
        bundled = lambda c: cases.custom_table(c, "differential-flux-x", None, None)  # noqa: E731
        obs = self.outcomes("a", bundled, cases.context_1_1)
        flagged = [o for o in obs if "coverage-contract:differential-flux-x" in o["declarations"]]
        self.assertTrue(flagged)
        self.assertTrue(all(o["declaration_based"] and o["state"] in ("satisfied", "not_applicable") for o in flagged))
        self.assertIn("r-real.description", {o["rule_id"] for o in flagged})
        self.assertNotIn("r-inv.root", {o["rule_id"] for o in flagged})  # reads no coverage
        plugin = self.outcomes("b", cases.context_1_1)  # the plugin's own coverage contract: no flag
        self.assertFalse([o for o in plugin if any(d.startswith("coverage-contract:") for d in o["declarations"])])
        old = self.outcomes("c", bundled)  # a 1.0.0 context keeps its outcomes (P3)
        self.assertFalse([o for o in old if any(d.startswith("coverage-contract:") for d in o["declarations"])])



if __name__ == "__main__":
    unittest.main()
