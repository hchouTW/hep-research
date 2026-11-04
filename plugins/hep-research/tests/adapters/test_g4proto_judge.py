"""The judge of prototypes GB4 and GB10 (adapters/geant4/tests/g4proto/gb4_gb10/judge.py): a correct synthetic run is
confirmed, and each defect it exists to catch is refused. No Geant4 here; the live run is recorded in the S1 task card."""
from __future__ import annotations

import copy
import importlib.util
import math
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("g4proto_judge", ROOT / "adapters/geant4/tests/g4proto/gb4_gb10/judge.py")
judge_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(judge_module)


def run_document(key: str, rotation) -> dict:
    chain = {"key": key, "end_half": "50", "gap_half": "0.0000005", "rotated_end": rotation is not None,
             "end_rotation": ["y", 5, 13 - 1, 13], "mothers": [{"name": key + "1", "t": ["1000.1", "2.5", "-3"], "half": "900",
                                                               "rotation": rotation}]}
    point = [Fraction(1000), Fraction(3), Fraction(-3)]
    samples = []
    for volume in (key + "A", key + "B"):
        local = judge_module.true_local(chain, volume, point)
        samples.append({"chain": key, "volume": volume, "global": [float(v).hex() for v in point],
                        "local": [float(v).hex() for v in local]})
    return {"geant4": "synthetic", "surface_tolerance": (1e-9).hex(), "inside_at_0p4e-9": 1, "inside_at_0p6e-9": 2, "kSurface": 1,
            "kOutside": 2, "overlaps": 0, "regions": dict(judge_module.EXPECTED_REGIONS), "chains": [chain], "samples": samples,
            "shots": [{"chain": key, "path": judge_module.expected_path(chain)}]}


class Judge(unittest.TestCase):
    def setUp(self):
        self.translated, self.rotated = run_document("T", None), run_document("R", ["z", 3, 4, 5])
        self.extent = {"extent_mm": (40000.0).hex(), "before": (1e-9).hex(), "after": (40000.0 * 1e-11).hex()}

    def status(self):
        return judge_module.judge(self.translated, self.rotated, self.extent)["status"]

    def test_a_correct_run_is_confirmed(self):
        self.assertEqual(self.status(), "ok")

    def test_a_coordinate_beyond_the_bound_is_refused(self):
        sample = self.translated["samples"][0]
        sample["local"][0] = (float.fromhex(sample["local"][0]) + 2e-10).hex()
        self.assertEqual(self.status(), "failed")

    def test_a_wrong_region_is_refused(self):
        self.rotated["regions"]["G4"] = "RegionOuter"
        self.assertEqual(self.status(), "failed")

    def test_a_stuck_track_is_refused(self):
        shot = self.rotated["shots"][0]
        shot["path"] = shot["path"][:2] + shot["path"][1:]
        self.assertEqual(self.status(), "failed")

    def test_an_overlap_is_refused(self):
        self.translated["overlaps"] = 1
        self.assertEqual(self.status(), "failed")

    def test_a_changed_tolerance_is_refused(self):
        self.rotated["surface_tolerance"] = (2e-9).hex()
        self.assertEqual(self.status(), "failed")

    def test_inside_at_full_tolerance_is_refused(self):
        self.rotated["inside_at_0p6e-9"] = 1
        self.assertEqual(self.status(), "failed")

    def test_an_extent_that_changes_nothing_is_refused(self):
        self.extent["after"] = (1e-9).hex()
        self.assertEqual(self.status(), "failed")

    def test_a_chain_sampled_on_one_side_is_refused(self):
        self.translated["samples"] = self.translated["samples"][:1]
        self.assertEqual(self.status(), "failed")

    def test_the_bound_follows_section_7_3(self):
        chain = copy.deepcopy(self.translated["chains"][0])
        self.assertEqual(judge_module.bound_mm(chain), 3 * math.ulp(20000))
        chain = copy.deepcopy(self.rotated["chains"][0])
        self.assertEqual(judge_module.bound_mm(chain), 21 * math.ulp(20000))


if __name__ == "__main__":
    unittest.main()
