"""B-01: the SKILL.md budget is a 12,288-byte target (a warning, which tools/budget_exceptions.json may waive), a
16,384-byte hard limit and 500 lines (failures, never waived); descriptions stay at 1,024 characters (the Agent Skills
specification) and the registry at 3,072 bytes. The exit code depends only on over_budget."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "measure_entrypoints.py"
sys.path.insert(0, str(ROOT))

from tools.measure_entrypoints import BUDGET  # noqa: E402


def skill(n_bytes: int, n_lines: int = 20, desc_chars: int = 100) -> str:
    head = f"---\nname: synthetic\ndescription: \"{'d' * desc_chars}\"\n---\n"
    body_lines = n_lines - head.count("\n")
    filler = n_bytes - len(head.encode()) - body_lines
    per = max(filler // body_lines, 0)
    lines = ["x" * per for _ in range(body_lines)]
    lines[-1] += "x" * (filler - per * body_lines)
    text = head + "\n".join(lines) + "\n"
    assert len(text.encode()) == n_bytes and text.count("\n") == n_lines, (len(text.encode()), text.count("\n"))
    return text


def measure(text: str, exceptions: dict | None = None):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "skills" / "synthetic").mkdir(parents=True)
        (root / "skills" / "synthetic" / "SKILL.md").write_text(text, encoding="utf-8")
        (root / "profiles").mkdir()
        (root / "profiles" / "registry.json").write_text(json.dumps({"profiles": []}))
        if exceptions is not None:
            (root / "tools").mkdir()
            (root / "tools" / "budget_exceptions.json").write_text(json.dumps(exceptions))
        res = subprocess.run([sys.executable, "-I", str(TOOL), "--no-cli", "--root", str(root)], capture_output=True,
                             text=True, timeout=120)
    return res.returncode, json.loads(res.stdout)


class Budget(unittest.TestCase):
    def test_budget_constants(self):
        self.assertEqual(BUDGET, {"skill_bytes_target": 12288, "skill_bytes_max": 16384, "skill_lines_max": 500,
                                  "description_chars": 1024, "registry_bytes": 3072, "index_bytes": 4096})
        self.assertIn('"registry_bytes": 3072', TOOL.read_text(encoding="utf-8"))

    def test_within_target(self):
        code, out = measure(skill(12288))
        self.assertEqual((code, out["over_budget"], out["warnings"]), (0, [], []))

    def test_above_target_warns(self):
        code, out = measure(skill(12289))
        self.assertEqual(code, 0)
        self.assertEqual(out["over_budget"], [])
        self.assertEqual(len(out["warnings"]), 1)
        self.assertIn("12289", out["warnings"][0])

    def test_target_waived_by_the_exceptions_file(self):
        code, out = measure(skill(12289), {"synthetic:bytes": "reason"})
        self.assertEqual((code, out["warnings"]), (0, []))

    def test_above_hard_limit_fails_and_is_not_waived(self):
        for exc in (None, {"synthetic:bytes": "reason"}):
            with self.subTest(exceptions=exc):
                code, out = measure(skill(16385), exc)
                self.assertEqual(code, 1)
                self.assertTrue(any("16385" in o for o in out["over_budget"]))

    def test_more_than_500_lines_fails(self):
        code, out = measure(skill(9000, n_lines=501), {"synthetic:lines": "reason"})
        self.assertEqual(code, 1)
        self.assertTrue(any("lines=501" in o for o in out["over_budget"]))
        self.assertEqual(measure(skill(9000, n_lines=500))[0], 0)

    def test_description_limit(self):
        self.assertEqual(measure(skill(5000, desc_chars=1024))[0], 0)
        code, out = measure(skill(5000, desc_chars=1025))
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
