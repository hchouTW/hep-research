"""`g4kit.py list` shows each kit's role and purpose, which state its limits (CHK-AC-04-10).

The expected values are read from the kit files themselves, never from the script's output.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-detector/scripts/g4kit.py"
KITS = ROOT / "skills/hep-detector/assets/g4kits"


class Listing(unittest.TestCase):
    def test_each_listed_kit_carries_its_role_and_purpose(self):
        done = subprocess.run([sys.executable, str(SCRIPT), "list"], capture_output=True, text=True, timeout=120, check=False)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        listed = {kit["name"]: kit for kit in json.loads(done.stdout)["kits"]}
        files = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(KITS.glob("*.json"))]
        self.assertEqual(set(listed), {kit["name"] for kit in files})
        for kit in files:
            with self.subTest(kit=kit["name"]):
                self.assertEqual(listed[kit["name"]]["role"], kit["role"])
                self.assertEqual(listed[kit["name"]]["purpose"], kit["purpose"])
                self.assertEqual(listed[kit["name"]]["version"], kit["version"])
                self.assertEqual(listed[kit["name"]]["inputs"], sorted(kit["inputs"]))


if __name__ == "__main__":
    unittest.main()
