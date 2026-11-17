"""CHK-AT-06-03 (S4): multisample_pid.py charge --method likelihood crashed with a TypeError traceback (exit 1) when the
response R(Z^2) is not positive anywhere in --z-range; the Moyal likelihood needs a positive signal, and the docstring
promises exit 2 with status rejected for invalid input. Now it is rejected with a message.

Behavioral evidence (C1), SYNTHETIC inputs:
- a response with signal from -100 to -1 over Z^2 in [0, 100] (strictly increasing, so accepted) and --z-range 0.5 2:
  exit 2, status rejected, an error naming the non-positive response, no traceback;
- control: a response that is positive on part of --z-range only still gives a result (exit 0).
No tolerances: exit codes and keys only.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "skills" / "hep-detector" / "scripts" / "multisample_pid.py"


class NonPositiveResponse(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.d = Path(self.workdir.name)

    def tearDown(self):
        self.workdir.cleanup()

    def run_tool(self, signal, rows, z_range):
        (self.d / "response.json").write_text(json.dumps({"z2": [0.0, 100.0], "signal": signal}), encoding="utf-8")
        (self.d / "ev.csv").write_text("a,b,c\n" + "\n".join(",".join(map(str, r)) for r in rows) + "\n",
                                       encoding="utf-8")
        return subprocess.run([sys.executable, "-B", str(TOOL), "charge", str(self.d / "ev.csv"), "--layers", "a,b,c",
                               "--response", str(self.d / "response.json"), "--method", "likelihood",
                               "--moyal-rel-width", "0.1", "--z-range", *map(str, z_range), "--no-path-correction"],
                              capture_output=True, text=True, timeout=600)

    def test_response_not_positive_in_the_range_is_rejected(self):
        res = self.run_tool([-100.0, -1.0], [[-50.0, -50.0, -50.0], [2.0, 2.0, 2.0]], (0.5, 2.0))
        self.assertNotIn("Traceback", res.stderr)
        self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
        out = json.loads(res.stdout)
        self.assertEqual(out["status"], "rejected")
        self.assertIn("not positive", out["error"])

    def test_response_positive_on_part_of_the_range_still_works(self):
        res = self.run_tool([-50.0, 50.0], [[14.0, 14.0, 14.0]], (0.5, 10.0))  # R > 0 above Z = 7.07; Z = 8 here
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertEqual(json.loads(res.stdout)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
