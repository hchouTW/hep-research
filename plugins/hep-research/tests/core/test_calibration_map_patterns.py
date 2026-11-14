"""The adapter that joins a mapping run's primaries.csv and photons.csv into the joint-pattern input (Part B section 6.7, D28;
adapters/geant4/assets/g4sim_map_patterns.py; phase 3, WP-D), on synthetic CSV pairs (no Geant4). Each negative has its positive
control."""
from __future__ import annotations

import json
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters" / "geant4" / "assets"))

import g4sim_map_patterns as MP  # noqa: E402

from core.calibration import map_basis as MB  # noqa: E402
from core.simulation import efficiency_map as em  # noqa: E402

IR = {"physical": {"templates": {"world": {"shape": "box", "half_mm": ["5e2", "5e2", "5e2"], "material": "G4_AIR"},
                                 "bar": {"shape": "box", "half_mm": ["1e1", "1e1", "2e1"], "material": "scint"}},
                   "placements": [{"mother": "world", "template": "bar", "copy_number": 0, "centre_mm": ["1e2", "0", "0"],
                                   "rotation": None}]}}
SEG = {"kind": "along_axis", "axis": 2, "width_mm": ["10"]}
HALF = [10.0, 10.0, 20.0]


class Patterns(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d)
        draw = random.Random(4)
        self.points = [(100 + draw.uniform(-10, 10), draw.uniform(-10, 10), draw.uniform(-20, 20)) for _ in range(2000)]
        fate0 = [draw.random() for _ in self.points]
        self.dets = []
        for j in range(2):
            det = {}
            for e, u in enumerate(fate0):
                if j and draw.random() < 0.1:
                    u = draw.random()
                if u < 0.05:
                    det[e] = "pe/1"
                elif u < 0.08 + 0.01 * j:
                    det[e] = "pe/2"
            self.dets.append(det)
        self.works = [self.write_run(f"p{j}", self.points, self.dets[j]) for j in range(2)]
        self.maps = []
        for det in self.dets:
            local = {e: [p[0] - 100, p[1], p[2]] for e, p in enumerate(self.points)}
            self.maps.append(em.build(template="bar", component=1, spectrum={"energy_eV": ["2", "3"], "value": ["1", "1"]},
                                      segmentation=SEG, half_mm=HALF, channels=sorted(set(det.values())), emitted=local,
                                      detected=[(e, c, 1.0) for e, c in sorted(det.items())],
                                      hashes={"materials_sha256": "0" * 64, "surfaces_sha256": "1" * 64, "mapping_run_id": "x"}))

    def write_run(self, name, points, det, extra_photons=()):
        w = self.d / name
        w.mkdir()
        (w / "ir.json").write_text(json.dumps(IR), encoding="utf-8")
        prim = ["event,energy_MeV,x_mm,y_mm,z_mm,dx,dy,dz"] + [f"{e},3e-06,{x},{y},{z},0,0,1" for e, (x, y, z) in enumerate(points)]
        phot = [f"{e},{c.split('/')[0]},{c.split('/')[1]},1.0,1.5,3,0,0,0" for e, c in sorted(det.items())] + list(extra_photons)
        (w / "primaries.csv").write_text("\n".join(prim) + "\n", encoding="utf-8")
        (w / "photons.csv").write_text("\n".join(phot) + "\n", encoding="utf-8")
        return w

    def test_table_matches_the_maps(self):
        r = MP.scan_patterns(self.works, "bar", SEG, self.maps)
        self.assertEqual((r["status"], r["findings"]), ("ok", []))
        local = {e: em.bin_of(SEG, HALF, [p[0] - 100, p[1], p[2]]) for e, p in enumerate(self.points)}
        self.assertEqual(r["pattern_table"], MB.pattern_table(local, self.dets, [m["channels"] for m in self.maps]))
        self.assertEqual(r["detections"][1], self.dets[1])

    def test_maps_in_the_wrong_order_fail(self):
        r = MP.scan_patterns(self.works, "bar", SEG, self.maps[::-1])
        self.assertEqual(r["findings"][0]["code"], "joint.counts")

    def test_mismatched_primaries_rejected(self):
        moved = list(self.points)
        moved[7] = (moved[7][0], moved[7][1], -moved[7][2])
        other = self.write_run("q1", moved, self.dets[1])
        r = MP.scan_patterns([self.works[0], other], "bar", SEG, self.maps)
        self.assertEqual((r["status"], r["findings"][0]["code"], r["findings"][0]["event"]), ("failed", "design.map_primaries", "7"))

    def test_malformed_or_inconsistent_runs_rejected(self):
        cases = {"orphan": ["99999,pe,1,1.0,1.5,3,0,0,0"], "twice": [f"{min(self.dets[0])},pe,2,1.0,1.5,3,0,0,0"],
                 "malformed": ["12,pe"]}
        for name, extra in cases.items():
            w = self.write_run(name, self.points, self.dets[0], extra)
            with self.assertRaises(MP.MapPatternError, msg=name):
                MP.run_patterns(w, "bar", SEG)
        bad = self.write_run("badprim", self.points, self.dets[0])
        (bad / "primaries.csv").write_text("event,e,x\n0,1,abc\n", encoding="utf-8")
        with self.assertRaises(MP.MapPatternError):
            MP.run_patterns(bad, "bar", SEG)
        self.assertEqual(len(MP.run_patterns(self.works[0], "bar", SEG)["detections"]), len(self.dets[0]))   # control


if __name__ == "__main__":
    unittest.main()
