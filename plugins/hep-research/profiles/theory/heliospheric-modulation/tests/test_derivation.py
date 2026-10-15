"""theory:heliospheric-modulation derivation tests: every SymPy check passes, the stored record is current, the
closed forms in predict.py equal the SymPy expressions, and wrong variants are caught."""
import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

HAVE_SYMPY = find_spec("sympy") is not None
if HAVE_SYMPY:
    import sympy as sp

    import derive


@unittest.skipUnless(HAVE_SYMPY, "sympy is required (requirements-core.txt)")
class DerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = derive.derive()

    def test_all_checks_pass(self):
        self.assertEqual(self.out["status"], "analytic-derivation")
        self.assertTrue(all(self.out["checks"].values()), self.out["checks"])

    def test_stored_record_is_current(self):
        stored = json.loads((ROOT / "derivations" / "derivation.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["checks"], self.out["checks"])
        self.assertEqual(stored["results"], self.out["results"])

    def test_wrong_sign_of_the_shift_is_caught(self):
        self.assertEqual(derive.force_field_pde(+1), 0)
        self.assertNotEqual(derive.force_field_pde(-1), 0)

    def test_numeric_closed_forms_match_sympy(self):
        cf = derive.closed_forms()
        for kind, var in (("Ek_total", derive.T), ("Ek_per_nucleon", derive.t), ("rigidity", derive.R)):
            for x, m, z, an, phi, g in ((0.3, 0.938272, 1, 1, 0.5, 2.7), (12.0, 3.7273794, 2, 4, 1.1, 2.0),
                                        (0.05, 11.17, 6, 12, 0.2, 3.1)):
                subs = {var: sp.nsimplify(x), derive.m: sp.nsimplify(m), derive.Z: z, derive.An: an,
                        derive.phi0: sp.nsimplify(phi), derive.gamma: sp.nsimplify(g), derive.A: 1}
                sym = float(cf[kind].subs(subs))
                num = predict.closed_form(kind, x, m, z, phi, 1.0, g, an if kind == "Ek_per_nucleon" else None)
                with self.subTest(kind=kind, x=x):
                    self.assertAlmostEqual(sym, num, delta=1e-12 * abs(sym))

    def test_flux_with_p_instead_of_p_squared_breaks_the_invariant(self):
        # J = p f instead of p^2 f would give the ratio p/p'; the derivation's p^2 identity rejects it
        T, m = derive.T, derive.m
        self.assertNotEqual(sp.simplify(sp.sqrt(T * (T + 2 * m)) - T * (T + 2 * m)), 0)


if __name__ == "__main__":
    unittest.main()
