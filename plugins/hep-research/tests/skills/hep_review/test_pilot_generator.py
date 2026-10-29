"""The pilot instance generator's oracles (docs/dev/hep-review/pilot/make_pilot_instances.py; T03 step 7, design
only). Engineering checks of the generator, not pilot results."""
from __future__ import annotations

import importlib.util
import json
import random
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GEN = ROOT / "docs" / "dev" / "hep-review" / "pilot" / "make_pilot_instances.py"
spec = importlib.util.spec_from_file_location("make_pilot_instances", GEN)
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


class Generator(unittest.TestCase):
    def test_four_types_all_oracle_checked_and_seed_reproducible(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ra = G.build("seed-x", Path(a), 4)
            G.build("seed-x", Path(b), 4)
            self.assertEqual(ra["types"], {"C01": 4, "C02": 4, "C03": 4, "C04": 4})
            names = sorted(p.name for p in (Path(a) / "instances").iterdir())
            self.assertEqual(names, sorted(p.name for p in (Path(b) / "instances").iterdir()))
            oracle = json.loads((Path(a) / "oracle.json").read_text())
            self.assertTrue(all(v["oracle_ok"] for v in oracle.values()))
            # the type is not in the instance folder a reviewer reads
            for d in (Path(a) / "instances").iterdir():
                self.assertNotIn("C0", (d / "material" / "data.json").read_text())

    def test_different_seed_different_instances(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            G.build("seed-1", Path(a), 1)
            G.build("seed-2", Path(b), 1)
            self.assertNotEqual(sorted(p.name for p in (Path(a) / "instances").iterdir()),
                                sorted(p.name for p in (Path(b) / "instances").iterdir()))

    def test_oracle_rejects_a_control_quoted_too_coarsely(self):
        # the spike's x02c error: 0.005541 quoted as 0.0055 is 0.74% off, outside the 0.1% tolerance
        self.assertFalse(G.within(0.0055, 0.005541085))
        self.assertTrue(G.within(G.stated(0.005541085), 0.005541085))

    def test_c01_oracle_requires_the_defect_to_change_the_result(self):
        rng = random.Random(1)
        for fam in G.FAMILIES:
            _, _, v = fam(rng, defect=True)
            if v["oracle_ok"]:
                self.assertIsNotNone(v["defect"])
            _, material_values, v = fam(rng, defect=False)
            self.assertIsNone(v["defect"])

    def test_c03_stated_values_reachable_for_the_missing_input(self):
        rng = random.Random(7)
        ok = [G.c03_instance(rng)[2]["oracle_ok"] for _ in range(20)]
        self.assertTrue(any(ok))


if __name__ == "__main__":
    unittest.main()
