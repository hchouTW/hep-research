"""What reconstruction and a study read of a g4sim run: the planes and the field from the IR, and the geometry Geant4 really built, without Geant4."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters/geant4/assets"))

import g4sim_reco as reco  # noqa: E402
import geant4_run as run  # noqa: E402

TEMPLATES = {"world": {"half_mm": ["1000", "1000", "1000"], "material": "G4_Galactic"}, "telescope": {"half_mm": ["300", "200", "200"], "material": "G4_Galactic"}, "sensor": {"half_mm": ["0.15", "200", "200"], "material": "G4_Si"}}
IR = {"physical": {"templates": TEMPLATES, "placements": [{"mother": "world", "template": "telescope", "centre_mm": ["10", "0", "0"]}, {"mother": "telescope", "template": "sensor", "centre_mm": ["100", "0", "0"]}, {"mother": "telescope", "template": "sensor", "centre_mm": ["-100", "0", "0"]}]},
      "marker": {"tags": {"sensor": ["tracker"]}}}
REQUEST = {"source": {"particle": "proton", "energy": {"mono": {"energy_MeV": 433.0}}}}
CARD = {"run": {"logical_run_seed": 7, "events": 10}}
PLACEMENT = {"name": "world", "logical": 0, "mother_logical": None, "copy_number": 0, "translation_mm": ["0x0.0p+0"] * 3}
TREE = {"logical_volumes": [{"id": 0, "name": "world", "material": "G4_Galactic", "solid": {"type": "G4Box", "parameters": {}}}], "placements": [PLACEMENT], "materials": [{"name": "G4_Galactic", "density_g_cm3": "0x1p-80"}], "global_field": {"present": False}}


class Planes(unittest.TestCase):
    def test_a_position_adds_those_of_its_mothers(self):
        self.assertIn(("sensor", (110.0, 0.0, 0.0)), reco.world_positions(IR))

    def test_the_planes_come_in_order_of_x_with_the_field_over_the_world(self):
        view = reco.element_view(IR, REQUEST, CARD, [0.0, 0.0, 1.0])
        planes = [item for item in view["elements"] if item["role"] == "tracker-plane"]
        self.assertEqual([item["centre_mm"][0] for item in planes], [-90.0, 110.0])
        self.assertEqual(view["field"]["regions"], [{"element": "field", "b_tesla": [0.0, 0.0, 1.0]}])

    def test_a_specification_without_a_tracker_is_refused(self):
        with self.assertRaises(ValueError):
            reco.element_view({**IR, "marker": {"tags": {}}}, {}, CARD, [0.0, 0.0, 0.0])


class Recorded(unittest.TestCase):
    def config(self, base: dict) -> dict:
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "probe-v2.json").write_text(json.dumps({"base": base}), encoding="utf-8")
            return run.g4sim_effective_config(Path(folder))

    def test_a_run_carries_the_tree_its_probe_recorded(self):
        config = self.config({"recorded": True, "geometry": TREE})
        self.assertTrue(config["recorded"])
        self.assertEqual(config["geometry"]["tree"], TREE)
        self.assertEqual(len(config["geometry"]["tree_sha256"]), 64)

    def test_a_probe_that_recorded_nothing_gives_no_tree(self):
        config = self.config({"recorded": False})
        self.assertFalse(config["recorded"])
        self.assertIsNone(config["geometry"]["tree"])


if __name__ == "__main__":
    unittest.main()
