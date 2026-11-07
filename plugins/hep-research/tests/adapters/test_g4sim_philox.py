"""Philox.hh against core/simulation/rng.py: the integer layer, the uniform variates and fsum agree bit for bit (Section 10.2)."""
from __future__ import annotations

import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.simulation import rng  # noqa: E402

HEADERS = ROOT / "adapters/geant4/assets/g4sim"
DRIVER = r"""
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>
#include "Philox.hh"
int main() {
  std::string kind;
  while (std::cin >> kind) {
    if (kind == "philox") {
      g4sim::PhiloxWords c; std::uint32_t a, b;
      std::cin >> c[0] >> c[1] >> c[2] >> c[3] >> a >> b;
      const auto w = g4sim::Philox4x32(c, a, b);
      const auto u = g4sim::UniformsOf(w);
      std::printf("%u %u %u %u %a %a\n", w[0], w[1], w[2], w[3], u[0], u[1]);
    } else {
      std::size_t n; std::cin >> n;
      std::vector<double> v(n);
      std::string text;
      for (auto& x : v) { std::cin >> text; x = std::strtod(text.c_str(), nullptr); }
      try {
        if (kind == "sum") {
          std::printf("%a\n", g4sim::Fsum(v));
        } else {
          std::vector<std::vector<double>> chunks;
          for (std::size_t at = 0; at < 5; ++at) {
            std::vector<double> part;
            for (std::size_t i = at; i < n; i += 5) part.push_back(v[i]);
            chunks.push_back(g4sim::PartialSums(part));
          }
          std::printf("%a\n", g4sim::MergePartialSums(chunks));
        }
      } catch (const std::range_error&) {
        std::printf("refused\n");
      }
    }
  }
}
"""


@unittest.skipUnless(shutil.which("c++"), "a C++ compiler is needed")
class PhiloxInCpp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        source = Path(cls.folder.name) / "philox_check.cc"
        source.write_text(DRIVER, encoding="utf-8")
        cls.program = Path(cls.folder.name) / "philox_check"
        subprocess.run(["c++", "-std=c++17", "-O2", f"-I{HEADERS}", str(source), "-o", str(cls.program)], check=True, timeout=120)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def ask(self, text):
        return subprocess.run([str(self.program)], input=text, capture_output=True, text=True, check=True, timeout=60).stdout.splitlines()

    def test_words_and_uniforms_agree_with_python(self):
        generator = random.Random(11)
        cases = [[generator.getrandbits(32) for _ in range(6)] for _ in range(2000)] + [[0] * 6, [0xFFFFFFFF] * 6]
        lines = self.ask("".join("philox " + " ".join(map(str, case)) + "\n" for case in cases))
        self.assertEqual(len(lines), len(cases))
        for case, line in zip(cases, lines):
            words = rng.philox4x32_10(tuple(case[:4]), tuple(case[4:]))
            cells = line.split()
            self.assertEqual(tuple(int(value) for value in cells[:4]), words)
            self.assertEqual(tuple(float.fromhex(value) for value in cells[4:]), rng.uniforms_of(words))

    def test_fsum_agrees_with_cpython(self):
        generator = random.Random(12)
        groups = [[2.0 ** 53, 1.0, 2.0 ** -80], [1e16, 1.0, 1e-16], [1.0, -1.0], []]
        groups += [[generator.uniform(-1, 1) * 10.0 ** generator.randint(-30, 30) for _ in range(generator.randint(1, 400))] for _ in range(300)]
        text = "".join(f"sum {len(group)} " + " ".join(value.hex() for value in group) + "\n" for group in groups)
        lines = self.ask(text)
        self.assertEqual(len(lines), len(groups))
        for group, line in zip(groups, lines):
            self.assertEqual(float.fromhex(line), math.fsum(group), json.dumps(group)[:120])

    def test_a_negative_zero_sums_as_in_cpython(self):
        self.assertEqual(self.ask("sum 1 -0x0p+0\n"), [math.fsum([-0.0]).hex().replace("0x0.0p+0", "0x0p+0")])

    def test_merged_chunks_equal_one_run_and_core(self):
        generator = random.Random(13)
        groups = [[2.0 ** 53, 1.0, 2.0 ** -80, -(2.0 ** 53), 1.0], [1e16, 1.0, 1e-16, -1e16, 3.0, 1e-3]]
        groups += [[generator.uniform(-1, 1) * 10.0 ** generator.randint(-30, 30) for _ in range(generator.randint(5, 300))] for _ in range(200)]
        lines = self.ask("".join(f"merge {len(group)} " + " ".join(value.hex() for value in group) + "\n" for group in groups))
        self.assertEqual(len(lines), len(groups))
        for group, line in zip(groups, lines):
            self.assertEqual(float.fromhex(line), rng.merge_partial_sums([rng.partial_sums(group[at::5]) for at in range(5)]))

    def test_summands_out_of_range_are_refused_as_in_core(self):
        self.assertEqual(self.ask(f"sum 2 1.0 {1e300.hex()}\nsum 1 inf\n"), ["refused", "refused"])

    def test_a_step_at_exactly_ten_is_on_the_poisson_side(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "split.cc"
            source.write_text('#include <cstdio>\n#include "ScintillationSplit.hh"\nint main() { std::printf("%d %d %d", g4sim::IsLargeStep(10.), g4sim::IsLargeStep(10.000000000000002), g4sim::IsLargeStep(10., true)); }\n', encoding="utf-8")
            subprocess.run(["c++", "-std=c++17", f"-I{HEADERS}", str(source), "-o", str(Path(folder) / "split")], check=True, timeout=60)
            done = subprocess.run([str(Path(folder) / "split")], capture_output=True, text=True, check=True, timeout=30)
        self.assertEqual(done.stdout, "0 1 1")  # the third is the negative control: mu_s = 10 in E^L

    def test_fast_math_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "fast.cc"
            source.write_text('#include "Philox.hh"\nint main() {}\n', encoding="utf-8")
            done = subprocess.run(["c++", "-std=c++17", "-ffast-math", f"-I{HEADERS}", str(source), "-o", str(Path(folder) / "fast")], capture_output=True, text=True, check=False, timeout=60)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("-ffast-math", done.stderr)


if __name__ == "__main__":
    unittest.main()
