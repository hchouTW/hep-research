"""g4sim_digi (g4sim S8, Section 10.5) built from source and compared with core/simulation/digitize.py on a small fixture, at the three
levels of Section 10.2 that S8 gate 2 judges at full size. Skipped where no C++17 compiler is found."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters/geant4/tests/g4proto/s8_gates"))

import digi_determinism as gate  # noqa: E402

ASSETS = ROOT / "adapters/geant4/assets"
COMPILER = shutil.which("g++") or shutil.which("clang++")


@unittest.skipUnless(COMPILER, "no C++ compiler")
class G4simDigi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = Path(tempfile.mkdtemp())
        cls.program = cls.folder / "g4sim_digi"
        subprocess.run([COMPILER, "-O2", "-std=c++17", "-ffp-contract=off", "-I", str(ASSETS / "g4sim_digi"), "-I", str(ASSETS / "g4sim"),
                        str(ASSETS / "g4sim_digi/g4sim_digi.cc"), "-o", str(cls.program)], check=True, timeout=600)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.folder, ignore_errors=True)

    def test_the_three_levels_on_a_small_fixture(self):
        done = subprocess.run([sys.executable, str(ROOT / "adapters/geant4/tests/g4proto/s8_gates/digi_determinism.py"), "--program", str(self.program),
                               "--work", str(self.folder / "work"), "--events", "12"], capture_output=True, text=True, timeout=900, check=False)
        report = json.loads(done.stdout)
        self.assertEqual(report["status"], "ok", done.stdout[-2000:])
        for fixture in report["fixtures"].values():
            self.assertEqual(fixture["level_3"]["discrete_disagreements"], 0)

    def test_a_bin_twice_and_a_wrong_job_are_refused(self):
        job = self.folder / "job.json"
        job.write_text(json.dumps(gate.digitize.job_with_keys(gate.fixture_jobs(1)["A"])), encoding="utf-8")
        bins = self.folder / "bins.csv"
        bins.write_text("0,3,1,0x1p-3,0x1p-6,2\n0,3,1,0x1p-3,0x1p-6,2\n", encoding="ascii")
        done = subprocess.run([str(self.program), str(job), str(bins), str(self.folder / "c.csv"), str(self.folder / "t.csv")], capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 2)
        self.assertIn("bin-twice", done.stderr)
        job.write_text(json.dumps({"schema": "other"}), encoding="utf-8")
        done = subprocess.run([str(self.program), str(job), str(bins), str(self.folder / "c.csv")], capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 2)


if __name__ == "__main__":
    unittest.main()
