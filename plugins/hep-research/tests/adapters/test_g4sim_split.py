"""The boundary of `edep_visible_ly_split`: Geant4 draws a Gaussian for mu_s > 10, so a step at exactly 10 belongs to E^S (g4sim plan, Section 10.3; negative test of Section 15.1)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r"""
#include <cstdio>
#include "ScintillationSplit.hh"
int main() {
  const bool control = g4sim::ScintillationControl();
  std::printf("%d %d %d\n", g4sim::IsLargeStep(9.999, control), g4sim::IsLargeStep(10., control), g4sim::IsLargeStep(10.001, control));
}
"""


@unittest.skipUnless(shutil.which("c++"), "a C++ compiler is needed")
class SplitBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        source = Path(cls.folder.name) / "driver.cc"
        source.write_text(DRIVER, encoding="utf-8")
        cls.program = Path(cls.folder.name) / "driver"
        subprocess.run(["c++", "-std=c++17", "-I", str(ROOT / "adapters/geant4/assets/g4sim"), str(source), "-o", str(cls.program)], check=True, capture_output=True, timeout=120)

    def sides(self, **settings: str) -> str:
        environment = {key: value for key, value in os.environ.items() if key != "G4SIM_SPLIT_CONTROL"}
        return subprocess.run([str(self.program)], env={**environment, **settings}, check=True, capture_output=True, text=True, timeout=30).stdout.strip()

    def test_a_step_at_exactly_ten_is_on_the_poisson_side(self):
        self.assertEqual(self.sides(), "0 0 1")

    def test_the_control_moves_only_that_step(self):
        self.assertEqual(self.sides(G4SIM_SPLIT_CONTROL="inclusive"), "0 1 1")


if __name__ == "__main__":
    unittest.main()
