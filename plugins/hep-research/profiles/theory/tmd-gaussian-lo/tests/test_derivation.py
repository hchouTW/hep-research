"""theory:tmd-gaussian-lo derivation tests: every SymPy check passes, versions are recorded, and the checks catch a
wrong width combination and a missing z^2 in the Bacchetta D_1 width."""
import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

HAVE_SYMPY = find_spec("sympy") is not None
if HAVE_SYMPY:
    import sympy as sp

    import derive as d


@unittest.skipUnless(HAVE_SYMPY, "sympy is required (requirements-core.txt)")
class DerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = d.derive()
        cls.a_form = d.sidis_anselmino()
        cls.b_form = d.sidis_bacchetta()

    def test_all_checks_pass(self):
        self.assertTrue(all(self.out["checks"].values()), [k for k, v in self.out["checks"].items() if not v])
        self.assertIn("heuristic-argument", self.out["status"]["physics"])
        self.assertIn("cited", self.out["status"]["sivers_sign_change"])

    def test_versions_recorded(self):
        self.assertEqual(self.out["environment"]["sympy"], sp.__version__)

    def test_wrong_width_combination_is_caught(self):
        target = d.x * d.f0 * d.D0 * d.G(d.Px, d.Py, d.PT2)
        wrong = d.x * d.f0 * d.D0 * d.G(d.Px, d.Py, d.pperp2 + d.z * d.kperp2)  # z instead of z^2
        self.assertTrue(d.same(self.a_form, target))
        self.assertFalse(d.same(self.a_form, wrong))

    def test_missing_z2_in_bacchetta_width_is_caught(self):
        target = d.x * d.f0 * d.D0 * d.G(d.Px, d.Py, d.PT2)
        self.assertTrue(d.same(self.b_form.subs(d.kT2, d.pperp2 / d.z ** 2), target))
        self.assertFalse(d.same(self.b_form.subs(d.kT2, d.pperp2), target))  # <k_T^2> = <p^2> forgets the z^2

    def test_stored_derivation_current(self):
        stored = json.loads((ROOT / "derivations" / "derivation.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["checks"], self.out["checks"])
        self.assertEqual(stored["results"], self.out["results"])


if __name__ == "__main__":
    unittest.main()
