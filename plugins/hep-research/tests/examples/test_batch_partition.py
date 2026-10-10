"""B11: the T21 job as a batch campaign on fake Slurm and HTCondor schedulers (SYNTHETIC, injected faults)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]

try:
    import numpy  # noqa: F401
    HAVE_NP = True
except ImportError:
    HAVE_NP = False


@unittest.skipUnless(HAVE_NP, "numpy required (D5 environment)")
class BatchPartitionExampleTests(unittest.TestCase):
    def test_every_criterion_passes_and_output_is_reproducible(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run([sys.executable, str(PLUGIN / "examples" / "batch-partition" / "run.py"), "--out", td],
                               capture_output=True, text=True, timeout=1200)
            fresh = (Path(td) / "results.json").read_bytes()
        r = json.loads(fresh)
        self.assertEqual(p.returncode, 0, r["pass"])
        for backend in ("slurm", "htcondor"):
            self.assertTrue(all(v is True for v in r["pass"][backend].values()), r["pass"][backend])
        self.assertIn("SYNTHETIC", r["label"])
        self.assertIn("FAKE", r["label"])
        committed = json.loads((PLUGIN / "examples" / "batch-partition" / "output" / "results.json").read_bytes())
        # every count, state, digest and label is reproduced exactly; a floating sum (sum_cos is a numpy reduction)
        # may differ in its last digits between hosts and numpy builds (T03, lxplus with numpy 1.23.5 against the
        # committed file: -202.23230211395253 vs ...256), so floats are compared at a relative 1e-9
        self.assertEqual(same_up_to_float_rounding(r, committed), [], "committed results.json differs beyond float rounding")


def same_up_to_float_rounding(a, b, path="$", rel=1e-9):
    """The paths at which two JSON values differ, floats compared with math.isclose(rel_tol=rel)."""
    import math
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return [f"{path}: keys {sorted(set(a) ^ set(b))}"]
        return [d for k in a for d in same_up_to_float_rounding(a[k], b[k], f"{path}.{k}", rel)]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} vs {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in same_up_to_float_rounding(x, y, f"{path}[{i}]", rel)]
    if isinstance(a, float) and isinstance(b, float) and not isinstance(a, bool):
        return [] if math.isclose(a, b, rel_tol=rel, abs_tol=0.0) else [f"{path}: {a!r} vs {b!r}"]
    return [] if a == b and type(a) is type(b) else [f"{path}: {a!r} vs {b!r}"]


class FloatRoundingComparisonTests(unittest.TestCase):
    def test_only_float_rounding_is_tolerated(self):
        a = {"n": 10, "sum_cos": -202.23230211395253, "pass": {"htcondor": {"c1": True}}, "states": ["done", "done"]}
        b = {"n": 10, "sum_cos": -202.23230211395256, "pass": {"htcondor": {"c1": True}}, "states": ["done", "done"]}
        self.assertEqual(same_up_to_float_rounding(a, b), [])
        self.assertEqual(same_up_to_float_rounding(dict(a, n=11), b), ["$.n: 11 vs 10"])
        self.assertEqual(same_up_to_float_rounding(dict(a, sum_cos=-202.2323), b), ["$.sum_cos: -202.2323 vs -202.23230211395256"])
        self.assertEqual(same_up_to_float_rounding(dict(a, states=["done", "failed"]), b), ["$.states[1]: 'failed' vs 'done'"])
        self.assertEqual(same_up_to_float_rounding(dict(a, n=10.0), b), ["$.n: 10.0 vs 10"])  # an int is not a float


if __name__ == "__main__":
    unittest.main()
