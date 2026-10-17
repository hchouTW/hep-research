"""X2: one owner per topic. The propagation equation and B/C (owner hep-theory), the force-field formula (owner
hep-theory) and period searches (owner hep-statistics) are kept once and linked from hep-detector; the broken power
law is computed only by core/stats/broken_power_law.py in both fitting scripts; the hep-measurement script list is
kept once (the analysis guide), not repeated in the README."""
import math
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DET = ROOT / "skills" / "hep-detector" / "references"


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


class DetectorLinksToOwners(unittest.TestCase):
    def test_propagation_equation_and_bc_live_in_hep_theory(self):
        det = (DET / "cosmic-ray-spectrum-and-composition.md").read_text()
        self.assertNotIn("dN_i/dt", det)
        self.assertIn("../../hep-theory/references/cosmic-ray-propagation.md#the-model-families", det)
        theory = read("skills/hep-theory/references/cosmic-ray-propagation.md")
        self.assertIn("**Secondary-to-primary ratios.**", theory)
        self.assertIn("path length", theory)

    def test_force_field_formula_lives_in_hep_theory(self):
        det = (DET / "space-based-direct-detection.md").read_text()
        self.assertNotIn("E_LIS = E + |Z|*phi", det)
        self.assertIn("../../hep-theory/references/cosmic-ray-propagation.md#force-field-solar-modulation", det)

    def test_period_search_method_lives_in_hep_statistics(self):
        det = (DET / "space-based-direct-detection.md").read_text()
        sec = det[det.index("## Searching for periodicity"):det.index("## Direct-detection composition")]
        self.assertNotIn("Lomb-Scargle", sec)
        self.assertIn("../../hep-statistics/references/time-series-inference.md#periodicity-in-a-binned-series", sec)
        stats = read("skills/hep-statistics/references/time-series-inference.md")
        self.assertIn("**Known or unknown period.**", stats)
        self.assertIn("opposite charge sign", stats)


class OneBrokenPowerLaw(unittest.TestCase):
    SCRIPTS = ("skills/hep-measurement/scripts/cr_spectrum_powerlaw_fit.py",
               "skills/hep-statistics/scripts/covariance_fit.py")

    def test_scripts_import_core_and_carry_no_own_break_math(self):
        for rel in self.SCRIPTS:
            code = "\n".join(l for l in read(rel).splitlines() if not l.lstrip().startswith("#"))
            with self.subTest(script=rel):
                self.assertIn("core.stats", code)
                self.assertIn("broken_power_law", code)
                self.assertIsNone(re.search(r"log1p|logaddexp|softplus", code))

    def test_measurement_wrapper_equals_core(self):
        from core.stats.broken_power_law import log_flux
        sys.path.insert(0, str(ROOT / "skills" / "hep-measurement" / "scripts"))
        import cr_spectrum_powerlaw_fit as cr
        for e in (3.0, 10.0, 200.0, 1000.0):
            for s in (None, 0.05, 0.3):
                with self.subTest(e=e, s=s):
                    self.assertEqual(cr.broken_log_flux(e, 1.2, 2.8, 2.6, 200.0, s),
                                     log_flux(e, 1.2, 2.8, 2.6, math.log(200.0), s))


class ScriptListOnce(unittest.TestCase):
    def test_measurement_readme_points_to_the_guide(self):
        readme = read("skills/hep-measurement/README.md")
        self.assertIn("Executable resources", readme)
        self.assertNotIn("`particle_ratio_with_uncertainty.py`", readme)
        guide = read("skills/hep-measurement/references/hep-measurement-guide.md")
        for script in sorted(p.name for p in (ROOT / "skills/hep-measurement/scripts").glob("*.py")):
            with self.subTest(script=script):
                self.assertIn(f"`{script}`", guide)


if __name__ == "__main__":
    unittest.main()
