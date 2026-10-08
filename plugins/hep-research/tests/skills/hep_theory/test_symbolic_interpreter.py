"""SYMPY S05: the skills tell the agent to choose a SymPy interpreter with find_python.py and to record its versions."""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
THEORY = (PLUGIN / "skills" / "hep-theory" / "SKILL.md").read_text(encoding="utf-8")
COMPUTING = (PLUGIN / "skills" / "hep-computing" / "SKILL.md").read_text(encoding="utf-8")
FINDER = "skills/hep-computing/scripts/find_python.py"


class SymbolicInterpreterTextTests(unittest.TestCase):
    def test_finder_exists(self):
        self.assertTrue((PLUGIN / FINDER).is_file())

    def test_theory_workflow_runs_finder_before_sympy_and_records_versions(self):
        step = next(line for line in THEORY.splitlines() if re.match(r"3\. Derive", line))
        self.assertIn(f"<plugin root>/{FINDER}", step)
        self.assertIn("SymPy", step)
        for word in ("interpreter", "Python", "versions", "never install"):
            self.assertIn(word, step)

    def test_computing_resources_name_finder_and_variable(self):
        self.assertIn("`find_python.py`", COMPUTING)
        self.assertIn("HEP_RESEARCH_PYTHON", COMPUTING)


if __name__ == "__main__":
    unittest.main()
