"""Tests for core/constants (Th9): hbar c from the exact SI constants, exact flags, provenance on every value,
unit conversions (round trips and natural units), the AME2020 subset that geomagnetic_cutoff.py used before it moved
here (bit-identical), Q values against AME2020 mass excesses, user-supplied full tables, and, when the optional
`pdg` package is installed, the bundled PDG values against the package. Standard library only."""
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core import constants as K  # noqa: E402
from core.constants import ConstantsError  # noqa: E402

# Literal values copied from skills/hep-measurement/scripts/geomagnetic_cutoff.py before Th9 (AME2020 atomic
# masses in u, CODATA 2022 m_p, m_u and m_e in GeV): the move must not change a single bit.
OLD_ATOMIC_MASS_U = {
    (1, 1): 1.007825031898, (1, 2): 2.014101777844, (1, 3): 3.01604928132, (2, 3): 3.01602932197,
    (2, 4): 4.00260325413, (3, 6): 6.01512288742, (3, 7): 7.01600343426, (4, 7): 7.016928714,
    (4, 9): 9.012183062, (4, 10): 10.013534692, (5, 10): 10.012936862, (5, 11): 11.009305166, (6, 12): 12.0,
    (6, 13): 13.00335483534, (6, 14): 14.00324198862, (7, 14): 14.00307400425, (7, 15): 15.00010889827,
    (8, 16): 15.99491461926, (8, 17): 16.99913175595, (8, 18): 17.99915961214,
}
OLD_PROTON_GEV, OLD_U_GEV, OLD_E_GEV = 0.93827208943, 0.93149410372, 0.00051099895069


class ProvenanceTests(unittest.TestCase):
    def test_every_bundled_value_carries_value_uncertainty_unit_source_edition(self):
        items = [K.constant(k) for k in K.constant_names()]
        items += [K.particle(n, prop) for n in K.particle_names() for prop in ("mass", "width", "lifetime")
                  if K.has_particle_property(n, prop)]
        items += [K.atomic_mass(n) for n in K.nuclide_names()]
        self.assertGreater(len(items), 90)
        for q in items:
            with self.subTest(name=q.name):
                d = q.to_dict()
                for key in ("name", "value", "uncertainty", "unit", "source", "edition"):
                    self.assertIn(key, d)
                self.assertTrue(math.isfinite(d["value"]))
                self.assertTrue(d["source"] and d["edition"] and d["unit"] is not None)

    def test_editions(self):
        eds = {e["edition"] for e in K.editions()}
        self.assertEqual(eds, {"CODATA 2022", "PDG 2026", "AME2020 + NUBASE2020"})

    def test_exact_si_constants_are_exact(self):
        for name in ("speed_of_light", "planck_constant", "elementary_charge", "boltzmann_constant", "avogadro_constant"):
            q = K.constant(name)
            self.assertTrue(q.exact, name)
            self.assertEqual(q.uncertainty, 0.0)
        self.assertFalse(K.constant("proton_mass_energy").exact)
        self.assertEqual(K.constant("speed_of_light").value, 299792458.0)

    def test_unknown_names_are_refused(self):
        with self.assertRaises(ConstantsError):
            K.constant("proton mass please")
        with self.assertRaises(ConstantsError):
            K.particle("tachyon")
        with self.assertRaises(ConstantsError):
            K.nuclide("999Xx")


class DerivedTests(unittest.TestCase):
    def test_hbar_c_from_exact_h_c_e_matches_codata_table(self):
        q = K.hbar_c()
        self.assertTrue(q.exact)
        self.assertEqual(q.unit, "MeV fm")
        # The CODATA 2022 table prints the exact value truncated: 197.326 980 4...
        self.assertTrue(0.0 <= q.value - 197.3269804 < 1e-7, q.value)
        h, c, e = (K.constant(n).value for n in ("planck_constant", "speed_of_light", "elementary_charge"))
        self.assertAlmostEqual(q.value, h * c / (2 * math.pi) / e * 1e9, delta=1e-12)

    def test_hbar_c_squared_and_hbar(self):
        self.assertAlmostEqual(K.hbar_c_squared().value / 0.3893793721, 1.0, delta=1e-9)  # GeV^2 mb
        self.assertEqual(K.hbar_c_squared().unit, "GeV^2 mb")
        self.assertAlmostEqual(K.hbar("GeV s").value / 6.582119569e-25, 1.0, delta=1e-9)

    def test_constant_in_another_unit_is_decimal_exact(self):
        self.assertEqual(K.constant("proton_mass_energy", unit="GeV").value, OLD_PROTON_GEV)
        self.assertEqual(K.constant("atomic_mass_constant_energy", unit="GeV").value, OLD_U_GEV)
        self.assertEqual(K.constant("electron_mass_energy", unit="GeV").value, OLD_E_GEV)
        self.assertEqual(K.constant("proton_mass_energy", unit="GeV").unit, "GeV")


class ConversionTests(unittest.TestCase):
    PAIRS = [("GeV", "MeV"), ("keV", "J"), ("fm", "cm"), ("mb", "pb"), ("cm2", "fb"), ("GeV^-2", "mb"),
             ("GeV^-1", "fm"), ("GeV^-1", "s"), ("MeV/c2", "kg"), ("u", "GeV/c2"), ("g", "u"), ("ns", "s"),
             ("barn", "m2"), ("TeV", "eV")]

    def test_round_trips(self):
        for a, b in self.PAIRS:
            for x in (1e-6, 0.37, 1.0, 42.0, 3.3e5):
                with self.subTest(a=a, b=b, x=x):
                    self.assertAlmostEqual(K.convert(K.convert(x, a, b), b, a) / x, 1.0, delta=1e-14)

    def test_natural_unit_oracles(self):
        self.assertAlmostEqual(K.convert(1.0, "GeV^-2", "mb") / 0.3893793721, 1.0, delta=1e-9)
        self.assertAlmostEqual(K.convert(1.0, "fm", "GeV^-1") * 0.1973269804, 1.0, delta=1e-9)
        self.assertAlmostEqual(K.convert(1.0, "u", "MeV/c2") / 931.49410372, 1.0, delta=1e-10)
        self.assertEqual(K.convert(938.27208943, "MeV", "GeV"), 0.93827208943)
        self.assertEqual(K.convert(1.0, "barn", "mb"), 1000.0)

    def test_incompatible_or_unknown_units_are_refused(self):
        for a, b in (("GeV", "fm2"), ("s", "mb"), ("parsec", "m"), ("GeV", "furlong")):
            with self.subTest(a=a, b=b), self.assertRaises(ConstantsError):
                K.convert(1.0, a, b)
        with self.assertRaises(ConstantsError):
            K.convert(float("nan"), "GeV", "MeV")


class NuclideTests(unittest.TestCase):
    def test_geomagnetic_subset_moved_bit_identical(self):
        for (z, a), mass in OLD_ATOMIC_MASS_U.items():
            with self.subTest(Z=z, A=a):
                self.assertEqual(K.atomic_mass((z, a)).value, mass)
                old = mass * OLD_U_GEV - z * OLD_E_GEV
                self.assertEqual(K.nuclear_mass_gev(z, a), old)

    def test_nuclide_names_and_half_lives(self):
        self.assertEqual(K.nuclide("4He")["Z"], 2)
        self.assertTrue(K.nuclide("12C")["half_life"]["stable"])
        hl = K.half_life("3H")
        self.assertEqual((hl.value, hl.unit), (12.32, "y"))
        # NUBASE2020 (Kondev et al. 2021, Sec. 2.3): 1 y = 365.2422 d (tropical year); the paper rounds to 31 556 926 s
        self.assertAlmostEqual(K.half_life_seconds("3H")["value"], 12.32 * 365.2422 * 86400, delta=1e-3)
        self.assertAlmostEqual(K.half_life_seconds("238U")["value"], 4.463e9 * 365.2422 * 86400, delta=1e3)
        self.assertAlmostEqual(K.half_life_seconds("238U")["uncertainty"], 0.003e9 * 365.2422 * 86400, delta=1e3)
        self.assertIn("365.2422", K.half_life_seconds("14C")["note"])
        self.assertEqual(K.half_life_seconds("n")["value"], 609.8)
        self.assertAlmostEqual(K.half_life_seconds("234Pa")["value"], 6.70 * 3600.0, delta=1e-9)

    def test_qvalues_against_ame_mass_excesses(self):
        # Q from atomic masses equals the mass-excess difference (keV); both from AME2020.
        def dm(n):
            return K.nuclide(n)["mass_excess_keV"]
        q = K.qvalue("238U", "alpha")
        self.assertAlmostEqual(q["value_keV"], dm("238U") - dm("234Th") - dm("4He"), delta=1e-3)
        self.assertAlmostEqual(q["value_keV"], 4270.0, delta=2.0)
        q = K.qvalue("14C", "beta-")
        self.assertAlmostEqual(q["value_keV"], dm("14C") - dm("14N"), delta=1e-3)
        self.assertAlmostEqual(q["value_keV"], 156.476, delta=0.01)
        self.assertEqual(q["daughter"], "14N")
        q = K.qvalue("7Be", "ec")
        self.assertAlmostEqual(q["value_keV"], dm("7Be") - dm("7Li"), delta=1e-3)
        me = K.constant("electron_mass_energy").value * 1e3
        q = K.qvalue("26Al", "beta+")
        self.assertIn("missing", q)  # 26Mg is not in the bundled subset: say so, never guess
        with self.assertRaises(ConstantsError):
            K.qvalue("4He", "fission")
        self.assertGreater(me, 0)

    def test_user_supplied_full_tables(self):
        ame_line = '   0    2    2    4 He         2424.91587     0.00015    7073.9156     0.0002  B- -22898.2740   212.1320    4 002603.25413     0.00016'  # the 4He row of mass.mas20, verbatim
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "mass.mas20"
            p.write_text("\n" * 40 + ame_line + "\n", encoding="utf-8")
            table = K.load_ame(p)
        self.assertEqual(table[(2, 4)]["atomic_mass_u"], 4.00260325413)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.txt"
            p.write_text("not a table\n", encoding="utf-8")
            with self.assertRaises(ConstantsError):
                K.load_ame(p)


class PdgPackageTests(unittest.TestCase):
    """The bundled PDG 2026 subset against the optional `pdg` package of the same edition (skipped without it)."""

    def setUp(self):
        try:
            import pdg  # noqa: F401
        except ImportError:
            self.skipTest("optional package pdg not installed (pip install pdg)")

    def test_bundled_masses_equal_the_package(self):
        import warnings
        warnings.filterwarnings("ignore")
        import pdg
        api = pdg.connect()
        for name in K.particle_names():
            if not K.has_particle_property(name, "mass"):
                continue
            q = K.particle(name, "mass", unit="GeV")
            ref = api.get_particle_by_name(K.particle_record(name)["pdg_name"])
            if not str(ref.edition).startswith("2026"):
                self.skipTest(f"pdg package edition {ref.edition}, bundled 2026")
            rec = K.particle_record(name)["mass"]
            entries = [m for m in ref.masses() if m.units == rec["unit"]]
            with self.subTest(particle=name):
                # the bundled value is the summary-table text; the package's mass is the unrounded best value
                self.assertEqual(entries[0].best_summary().value_text, rec["pdg_value_text"])
                tol = 0.5 * min(x for x in (q.uncertainty, q.uncertainty_plus, q.uncertainty_minus) if x)
                self.assertLessEqual(abs(q.value - ref.mass), tol + 1e-15)


class DataFileTests(unittest.TestCase):
    def test_data_files_name_their_source_read_level_and_license(self):
        for p in sorted((ROOT / "core" / "constants" / "data").glob("*.json")):
            d = json.loads(p.read_text(encoding="utf-8"))
            with self.subTest(file=p.name):
                for key in ("edition", "source", "read", "license"):
                    self.assertTrue(d.get(key), key)


if __name__ == "__main__":
    unittest.main()
