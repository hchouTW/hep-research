"""Text event files and hit cells in C++, with no Geant4: a malformed file is refused rather than read wrongly, and a cell survives its two 32-bit columns (g4sim plan, Sections 6.3, 9.2)."""
from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADERS = ROOT / "adapters/geant4/assets/g4sim"
DRIVER = r"""
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include "ExternalEvents.hh"
#include "HitColumns.hh"
#include "PlaneCrossing.hh"
int main(int argc, char** argv) {
  if (argc > 1 && std::string(argv[1]) == "crossing") {
    double v[15];
    for (int i = 0; i < 14; ++i) v[i] = std::strtod(argv[i + 2], nullptr);
    const auto out = g4sim::CrossingOf({v[0], v[1], v[2]}, {v[3], v[4], v[5]}, {v[6], v[7], v[8]}, {v[9], v[10], v[11]}, v[12], v[13], argc > 16);
    std::printf("%a %a %a %a %a %a %a\n", out.fraction, out.position[0], out.position[1], out.position[2], out.direction[0], out.direction[1], out.direction[2]);
    return 0;
  }
  if (argc > 1 && std::string(argv[1]) == "crosses") {
    std::printf("%d\n", g4sim::StepCrosses(std::strtod(argv[2], nullptr), std::strtod(argv[3], nullptr)));
    return 0;
  }
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

    def crossing(self, from_, start, to, end, length, z, smooth):
        words = [str(value) for value in (*from_, *start, *to, *end, length, z)] + (["smooth"] if smooth else [])
        line = subprocess.run([str(self.program), "crossing", *words], capture_output=True, text=True, check=True, timeout=30).stdout
        return [float.fromhex(word) for word in line.split()]

    def test_a_crossing_on_a_helix_follows_the_curve(self):
        radius = 3335.0  # a 1 GeV/c proton in 1 T, over a long vacuum step

        def at(angle):
            return (radius * (1 - math.cos(angle)), 0.0, radius * math.sin(angle)), (math.sin(angle), 0.0, math.cos(angle))

        for arc, z, tolerance in ((0.07, 120.0, 1e-3), (0.3, 150.0, 0.05)):  # the error falls as the fourth power of the step
            with self.subTest(arc=arc):
                out = self.crossing(*at(0.0), *at(arc), radius * arc, z, True)
                position, direction = at(math.asin(z / radius))
                self.assertAlmostEqual(out[1], position[0], delta=tolerance)
                self.assertAlmostEqual(out[3], z, delta=1e-12)
                self.assertAlmostEqual(out[4], direction[0], delta=tolerance / 10)
                chord = self.crossing(*at(0.0), *at(arc), radius * arc, z, False)
                self.assertGreater(abs(chord[1] - position[0]), 10 * tolerance)  # the chord is the fault this curve removes

    def test_a_straight_step_is_exact(self):
        out = self.crossing((0, 0, 0), (0.6, 0, 0.8), (6, 0, 8), (0.6, 0, 0.8), 10.0, 4.0, True)
        self.assertAlmostEqual(out[0], 0.5, delta=1e-12)
        self.assertAlmostEqual(out[1], 3.0, delta=1e-12)
        self.assertAlmostEqual(out[4], 0.6, delta=1e-12)

    def test_a_kink_at_the_end_of_a_step_leaves_the_chord(self):
        out = self.crossing((0, 0, 0), (0, 0, 1), (0, 0, 10), (1, 0, 0), 10.0, 5.0, False)
        self.assertAlmostEqual(out[1], 0.0, delta=1e-12)
        self.assertAlmostEqual(out[6], 1.0, delta=1e-12)

    def test_a_track_born_on_a_plane_has_not_crossed_it(self):
        def crosses(before, after):
            return subprocess.run([str(self.program), "crosses", str(before), str(after)], capture_output=True, text=True, check=True, timeout=30).stdout.strip()

        self.assertEqual((crosses(-1, 1), crosses(1, -1), crosses(-1, 0), crosses(0, 1), crosses(0, -1), crosses(1, 2)), ("1", "1", "1", "0", "0", "0"))

    def test_a_cell_survives_its_two_columns(self):
        cells = ["0", "1", "4294967295", "4294967296", "18014407103612931", str(2 ** 63), str(2 ** 64 - 1)]
        done = subprocess.run([str(self.program), *cells], capture_output=True, text=True, check=True, timeout=30)
        self.assertEqual(done.stdout.split(), cells)


if __name__ == "__main__":
    unittest.main()
