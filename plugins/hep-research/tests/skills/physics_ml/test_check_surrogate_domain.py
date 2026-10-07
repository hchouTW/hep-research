"""CLI tests for skills/physics-ml/scripts/check_surrogate_domain.py (T11): exit codes, the box-only mode, sparse
queries inside the box, and malformed input reported as JSON with exit 2."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "physics-ml" / "scripts" / "check_surrogate_domain.py"
sys.path.insert(0, str(SCRIPT.parent))
import check_surrogate_domain as csd  # noqa: E402

GRID = [[i / 4, j / 4] for i in range(5) for j in range(5) if not (1 <= i <= 3 and 1 <= j <= 3)]  # a ring: hole inside


def run_main(payload, *extra):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "d.json"
        path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = csd.main([str(path), *extra])
        return code, json.loads(buf.getvalue())


class CheckSurrogateDomainCliTests(unittest.TestCase):
    def test_inside_outside_and_sparse(self):
        code, rep = run_main({"features": ["a", "b"], "training": GRID, "queries": [[0.0, 0.25]]})
        self.assertEqual((code, rep["passed"]), (0, True))
        code, rep = run_main({"features": ["a", "b"], "training": GRID, "queries": [[0.0, 0.25], [1.4, 0.5], [0.5, 0.5]]},
                             "--factor", "1.5")  # the hole's centre is 0.5 from the ring, spacing 0.25
        self.assertEqual(code, 1)
        self.assertEqual([q["status"] for q in rep["queries"]], ["inside", "outside", "sparse"])
        self.assertEqual(rep["queries"][1]["outside_features"], ["a"])

    def test_factor_changes_the_sparse_threshold(self):
        payload = {"features": ["a", "b"], "training": GRID, "queries": [[0.5, 0.5]]}
        self.assertEqual(run_main(payload, "--factor", "100")[0], 0)
        self.assertEqual(run_main(payload, "--factor", "1.5")[0], 1)

    def test_box_only_domain(self):
        code, rep = run_main({"features": ["a"], "training_domain": {"a": [0, 1]}, "queries": [[0.5], [2.0]]})
        self.assertEqual(code, 1)
        self.assertIsNone(rep["spacing_threshold"])
        self.assertNotIn("sparse", rep["queries"][0])

    def test_bad_input_is_exit_2_with_a_json_error(self):
        for payload in ("{not json", {"features": ["a"], "queries": [[0.1]]}, {"features": 3, "training": [[1]], "queries": [[1]]},
                        {"features": ["a", "b"], "training": GRID, "queries": [[0.1]]}):
            with self.subTest(payload=str(payload)[:40]):
                code, rep = run_main(payload)
                self.assertEqual(code, 2)
                self.assertIn("error", rep)

    def test_missing_file_through_the_command_line(self):
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "/nonexistent/domain.json"], capture_output=True, text=True, timeout=600)
        self.assertEqual(res.returncode, 2)
        self.assertIn("error", json.loads(res.stdout))
        self.assertNotIn("Traceback", res.stderr)


if __name__ == "__main__":
    unittest.main()
