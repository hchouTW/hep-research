"""Text event files and hit cells in C++, with no Geant4: a malformed file is refused rather than read wrongly, and a cell survives its two 32-bit columns (g4sim plan, Sections 6.3, 9.2)."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADERS = ROOT / "adapters/geant4/assets/g4sim"
DRIVER = r"""
#include <cstdio>
#include <iostream>
#include "ExternalEvents.hh"
#include "HitColumns.hh"
int main(int argc, char** argv) {
  if (argc > 1) {
    for (int at = 1; at < argc; ++at) {
      const std::uint64_t cell = std::strtoull(argv[at], nullptr, 10);
      std::printf("%llu\n", static_cast<unsigned long long>(g4sim::CellOf(g4sim::CellHigh(cell), g4sim::CellLow(cell))));
    }
    return 0;
  }
  try {
    for (const auto& [id, rows] : g4sim::ParseExternalEvents(std::cin, "file")) {
      std::printf("%lld %zu", id, rows.size());
      for (const auto& row : rows) std::printf(" %d %g %g", row.pdg, row.position[2], row.momentum[2]);
      std::printf("\n");
    }
  } catch (const std::exception& error) {
    std::printf("refused: %s\n", error.what());
  }
}
"""
GOOD_PARTICLE = "2212 1 2 3 4 5 6\n"


@unittest.skipUnless(shutil.which("c++"), "a C++ compiler is needed")
class ExternalEvents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        source = Path(cls.folder.name) / "driver.cc"
        source.write_text(DRIVER, encoding="utf-8")
        cls.program = Path(cls.folder.name) / "driver"
        subprocess.run(["c++", "-std=c++17", f"-I{HEADERS}", str(source), "-o", str(cls.program)], check=True, capture_output=True, timeout=120)

    def read(self, text: str) -> str:
        return subprocess.run([str(self.program)], input=text, capture_output=True, text=True, check=True, timeout=30).stdout

    def test_a_good_file_is_read(self):
        self.assertEqual(self.read("# g4sim-events/1\n\nevent 3 2\n" + GOOD_PARTICLE + "11 0 0 -9 0 0 8\nevent 4 0\n"), "3 2 2212 3 6 11 -9 8\n4 0\n")

    def test_a_malformed_file_is_refused(self):
        cases = {"event twice": "event 3 1\n" + GOOD_PARTICLE + "event 3 1\n" + GOOD_PARTICLE, "negative count": "event 3 -2\n", "negative event": "event -3 1\n" + GOOD_PARTICLE,
                 "short line": "event 3 2\n2212 1 2 3 4 5\n" + GOOD_PARTICLE, "long line": "event 3 1\n2212 1 2 3 4 5 6 7\n", "ends inside an event": "event 3 2\n" + GOOD_PARTICLE,
                 "not an event": "2212 1 2 3 4 5 6\n", "words on the event line": "event 3 1 x\n" + GOOD_PARTICLE, "fraction in the PDG": "event 3 1\n22.5 1 2 3 4 5 6\n"}
        for name, text in cases.items():
            with self.subTest(case=name):
                self.assertTrue(self.read(text).startswith("refused"), self.read(text))

    def test_a_cell_survives_its_two_columns(self):
        cells = ["0", "1", "4294967295", "4294967296", "18014407103612931", str(2 ** 63), str(2 ** 64 - 1)]
        done = subprocess.run([str(self.program), *cells], capture_output=True, text=True, check=True, timeout=30)
        self.assertEqual(done.stdout.split(), cells)


if __name__ == "__main__":
    unittest.main()
