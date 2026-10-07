"""examples/published-comparison/make_record.py reproduces the committed SYNTHETIC record and covariance (T11).

The script is run with its output directory redirected to a temporary folder. Structure and strings must match
exactly; numbers to a relative 1e-12, since the collider-angular output it copies from was regenerated after the
record was written and differs from it only in the last digit."""
import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
EXAMPLE = PLUGIN / "examples" / "published-comparison"


def same(a, b, path="$"):
    if isinstance(a, float) or isinstance(b, float):
        ok = isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-300)
        return [] if ok else [f"{path}: {a!r} != {b!r}"]
    if type(a) is not type(b):
        return [f"{path}: {type(a).__name__} != {type(b).__name__}"]
    if isinstance(a, dict):
        if set(a) != set(b):
            return [f"{path}: keys {sorted(set(a) ^ set(b))}"]
        return [m for k in a for m in same(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [m for i, (x, y) in enumerate(zip(a, b)) for m in same(x, y, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


class MakeRecordTests(unittest.TestCase):
    def test_reproduces_the_committed_files(self):
        spec = importlib.util.spec_from_file_location("make_record", EXAMPLE / "make_record.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as td:
            mod.HERE = Path(td)
            self.assertEqual(mod.main(), 0)
            for name in ("synthetic-published-record.json", "synthetic-published-covariance.json"):
                with self.subTest(file=name):
                    new = json.loads((Path(td) / name).read_text(encoding="utf-8"))
                    old = json.loads((EXAMPLE / name).read_text(encoding="utf-8"))
                    self.assertEqual(same(new, old), [])

    def test_the_record_is_labelled_synthetic_and_validates(self):
        import sys
        sys.path.insert(0, str(PLUGIN))
        from contracts.validate import validate_artifact
        rec = json.loads((EXAMPLE / "synthetic-published-record.json").read_text(encoding="utf-8"))
        self.assertIn("synthetic", rec["status"])
        self.assertEqual(rec["extension"]["status"], "synthetic")
        self.assertTrue(validate_artifact(rec).ok, validate_artifact(rec).as_dict())


if __name__ == "__main__":
    unittest.main()
