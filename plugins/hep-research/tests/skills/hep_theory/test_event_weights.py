"""event_weights.py: input checks and selected-event statistics (THY-WP1.3).

Every input is a constructed test input, not a generator sample. Hand values for the 6-event example:
weights [1.2, -0.4, 0.8, 1.0, -0.2, 0.6], selected [0, 1, 3, 5] -> w = 1.2, -0.4, 1.0, 0.6;
sum w = 2.4, sum w^2 = 1.44 + 0.16 + 1.0 + 0.36 = 2.96, N_eff = 5.76 / 2.96, rel. unc. = sqrt(2.96) / 2.4."""
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "hep-theory" / "scripts" / "event_weights.py"
_spec = importlib.util.spec_from_file_location("event_weights", SCRIPT)
weights = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(weights)

SIX = [1.2, -0.4, 0.8, 1.0, -0.2, 0.6]
# the audit's reproduction inputs (copied, not imported)
REPRO = {
    "dup": {"weights": [1, 1], "sigma_pb": 5.0, "selected": [0, 0, 0]},
    "nan": {"weights": [1, "nan", 1], "sigma_pb": 5.0},
    "negidx": {"weights": [1, 1], "sigma_pb": 5.0, "selected": [-1]},
    "neglumi": {"weights": [1, 1], "sigma_pb": 5.0, "luminosity_ipb": -1},
    "negsigma": {"weights": [1, 1], "sigma_pb": -5.0},
    "oob": {"weights": [1, 1], "sigma_pb": 5.0, "selected": [7]},
}


def cli(doc):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "in.json"
        p.write_text(doc if isinstance(doc, str) else json.dumps(doc))
        return subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True, timeout=600)


class SelectedStatisticsTests(unittest.TestCase):
    def test_six_event_example_hand_values(self):
        r = weights.summarize(SIX, 10.0, 2.0, selected=[0, 1, 3, 5])
        self.assertAlmostEqual(r["selected_sum_w"], 2.4, delta=1e-12)
        self.assertAlmostEqual(r["selected_sum_w2"], 2.96, delta=1e-12)
        self.assertAlmostEqual(r["selected_effective_sample_size"], 5.76 / 2.96, delta=1e-12)
        self.assertAlmostEqual(r["selected_relative_stat_uncertainty"], math.sqrt(2.96) / 2.4, delta=1e-12)
        self.assertAlmostEqual(r["selected_fraction_of_sum"], 2.4 / 3.0, delta=1e-12)

    def test_non_positive_selected_sum_is_refused(self):
        with self.assertRaises(ValueError) as cm:
            weights.summarize(SIX, 10.0, selected=[1, 4])
        self.assertIn("selected", str(cm.exception))


class RefusalTests(unittest.TestCase):
    def test_audit_reproductions_exit_1_without_traceback(self):
        for name, doc in REPRO.items():
            with self.subTest(name=name):
                r = cli(doc)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                self.assertEqual(json.loads(r.stdout)["status"], "failed")

    def test_other_bad_inputs(self):
        for doc in ({"weights": [1, 1], "sigma_pb": 0.0}, {"weights": [1, 1], "sigma_pb": "inf"},
                    {"weights": [1, 1], "sigma_pb": 1.0, "luminosity_ipb": float("nan")},
                    {"weights": [1, 1], "sigma_pb": 1.0, "selected": [0.5]},
                    {"weights": [1, 1], "sigma_pb": 1.0, "selected": [True]},
                    {"weights": [1, 1], "sigma_pb": 1.0, "selected": "0"},
                    {"weights": "11", "sigma_pb": 1.0}, {"sigma_pb": 1.0}, [1, 2]):
            with self.subTest(doc=doc):
                r = cli(json.dumps(doc))
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                self.assertEqual(json.loads(r.stdout)["status"], "failed")
        r = cli('{"weights": [1, Infinity], "sigma_pb": 1.0}')
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
