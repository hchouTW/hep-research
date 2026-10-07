"""Every subprocess call in the tests, the profile tests, tools/ and the diagram checker has a timeout (T14), so a
child that hangs (for example a renderer whose Chromium cannot start) fails with a reason instead of stalling the run.
The partition engine's calls are excluded: they run users' jobs, whose limits belong to the job configuration."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CALLS = ("run", "check_output", "check_call", "call")


def unbounded(path: Path) -> list[str]:
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in CALLS
                and getattr(node.func.value, "id", "") == "subprocess" and not any(k.arg == "timeout" for k in node.keywords)):
            out.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    return out


class SubprocessTimeoutTests(unittest.TestCase):
    def test_every_call_is_bounded(self):
        files = (sorted((ROOT / "tests").rglob("*.py")) + sorted((ROOT / "profiles").rglob("tests/*.py"))
                 + sorted((ROOT / "tools").glob("*.py"))
                 + [ROOT / "skills" / "research-communication" / "scripts" / "check_diagram_sources.py"])
        missing = [m for f in files for m in unbounded(f)]
        self.assertEqual(missing, [], "add timeout=... to these subprocess calls")

    def test_the_check_sees_a_missing_timeout(self):
        probe = ROOT / "tests" / "tools" / "_probe_unbounded.py"
        try:
            probe.write_text("import subprocess\nsubprocess.run(['true'])\nsubprocess.run(['true'], timeout=5)\n")
            self.assertEqual(unbounded(probe), ["tests/tools/_probe_unbounded.py:2"])
        finally:
            probe.unlink()


if __name__ == "__main__":
    unittest.main()
