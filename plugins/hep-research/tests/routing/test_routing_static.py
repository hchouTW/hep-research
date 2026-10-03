"""Runs the static routing check (tools/check_routing_static.py) as part of the test suite."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class StaticRoutingTests(unittest.TestCase):
    def test_descriptions_cover_every_case(self):
        p = subprocess.run([sys.executable, str(ROOT / "tools" / "check_routing_static.py")], capture_output=True, text=True)
        rep = json.loads(p.stdout)
        self.assertEqual(p.returncode, 0, rep)
        self.assertGreaterEqual(rep["cases"], 7 * 3 + 12)

    def test_cases_file_is_generated_from_the_table(self):
        # compare without rewriting the tracked file, so a hand edit to cases.json fails every run
        generated = subprocess.run([sys.executable, str(ROOT / "tests" / "routing" / "make_cases.py"), "--stdout"],
                                   check=True, capture_output=True).stdout
        self.assertEqual((ROOT / "tests" / "routing" / "cases.json").read_bytes(), generated)


if __name__ == "__main__":
    unittest.main()
