"""The elemental-constant table (g4sim S1): complete, consistent between its two sources, and in agreement with a value the
repository holds independently."""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core import constants  # noqa: E402
from core.constants import ConstantsError  # noqa: E402

NO_STABLE_ISOTOPE = {"Tc", "Pm", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Np", "Pu", "Am", "Cm", "Bk", "Cf"}


class Table(unittest.TestCase):
    def test_every_element_up_to_californium_is_there_in_order(self):
        self.assertEqual([constants.element(s)["Z"] for s in constants.element_symbols()], list(range(1, 99)))

    def test_every_element_has_the_constants(self):
        for symbol in constants.element_symbols():
            record = constants.element(symbol)
            with self.subTest(element=symbol):
                self.assertRegex(record["pdg_atomic_mass"], r"^[0-9.]+(\(\d+\))?$")
                self.assertRegex(record["radiation_length_g_cm2"], r"^[0-9.]+$")
                self.assertTrue("mean_excitation_eV" in record or "mean_excitation_eV_by_state" in record)

    def test_a_standard_weight_is_absent_only_without_a_stable_isotope(self):
        missing = {s for s in constants.element_symbols() if constants.element(s)["standard_atomic_weight"] is None}
        self.assertEqual(missing, NO_STABLE_ISOTOPE)

    def test_the_two_sources_agree(self):
        for symbol in set(constants.element_symbols()) - NO_STABLE_ISOTOPE:
            record = constants.element(symbol)
            mass = float(record["pdg_atomic_mass"].split("(")[0])
            weight = record["standard_atomic_weight"]
            interval = re.fullmatch(r"\[([0-9.]+),([0-9.]+)\]", weight)
            low, high = (float(interval[1]), float(interval[2])) if interval else (float(weight.split("(")[0]),) * 2
            with self.subTest(element=symbol):
                self.assertLessEqual(low - 0.01, mass)
                self.assertLessEqual(mass, high + 0.01)

    def test_state_dependent_energies_are_kept_apart(self):
        self.assertEqual(constants.element("H")["mean_excitation_eV_by_state"], {"gas": "19.2", "liquid": "21.8"})

    def test_silicon_agrees_with_the_repository_s_own_pdg_table(self):
        own = json.loads((ROOT / "examples/geant4-thin-silicon/refdata/pdg-silicon-2024.json").read_text(encoding="utf-8"))
        self.assertEqual(float(constants.element("Si")["mean_excitation_eV"]), own["values"]["mean_excitation_eV"])
        self.assertEqual(constants.element("Si")["pdg_atomic_mass"], own["values"]["A_g_mol"])

    def test_an_unknown_symbol_is_refused(self):
        with self.assertRaises(ConstantsError):
            constants.element("Xx")

    def test_the_edition_names_both_sources(self):
        edition = [e for e in constants.editions() if "CIAAW" in e["edition"]]
        self.assertEqual(len(edition), 1)
        self.assertIn("pdg.lbl.gov", edition[0]["source"])


if __name__ == "__main__":
    unittest.main()
