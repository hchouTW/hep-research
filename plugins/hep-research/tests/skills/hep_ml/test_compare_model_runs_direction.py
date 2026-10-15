"""compare_model_runs.py: a score direction given on the command line wins over "lower_is_better" in the runs file
(before the fix the file value silently overrode --lower-is-better)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "hep-ml" / "scripts" / "compare_model_runs.py"
RUNS = {"baseline": [0.50, 0.51, 0.49, 0.50, 0.52], "variant": [0.60, 0.61, 0.59, 0.62, 0.60]}


def run(payload, *flags):
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "runs.json"
        f.write_text(json.dumps(payload))
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), str(f), "--json", "--resamples", "500", *flags],
                             capture_output=True, text=True, timeout=600)
    return res


class DirectionPrecedenceTests(unittest.TestCase):
    def test_command_line_overrides_file(self):
        out = json.loads(run({**RUNS, "lower_is_better": False}, "--lower-is-better").stdout)
        self.assertTrue(out["lower_is_better"])
        self.assertEqual(out["lower_is_better_source"], "command line")
        self.assertLess(out["mean_difference"], 0)
        out = json.loads(run({**RUNS, "lower_is_better": True}, "--no-lower-is-better").stdout)
        self.assertFalse(out["lower_is_better"])
        self.assertGreater(out["mean_difference"], 0)

    def test_file_value_used_when_no_flag(self):
        out = json.loads(run({**RUNS, "lower_is_better": True}).stdout)
        self.assertTrue(out["lower_is_better"])
        self.assertEqual(out["lower_is_better_source"], "runs file")

    def test_default_is_higher_is_better(self):
        out = json.loads(run(RUNS).stdout)
        self.assertFalse(out["lower_is_better"])
        self.assertTrue(out["lower_is_better_source"].startswith("default"))

    def test_non_boolean_file_value_is_rejected(self):
        res = run({**RUNS, "lower_is_better": "yes"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("true or false", res.stderr)


if __name__ == "__main__":
    unittest.main()
