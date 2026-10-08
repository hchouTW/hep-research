"""tools/check_instruction_text.py (AGENTIC-R5 T0.7, U12): the shipped texts pass, and a planted MUST-item phrase or a
missing required text is reported."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_instruction_text", ROOT / "tools" / "check_instruction_text.py")
cit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cit)


class InstructionTextTests(unittest.TestCase):
    def test_shipped_texts_pass(self):
        rep = cit.check()
        self.assertEqual(rep["findings"], [])

    def test_planted_phrase_and_missing_requirement_are_found(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for _, rel, phrase in cit.REQUIRED:
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(phrase + "\n", encoding="utf-8")
            (root / "skills" / "x").mkdir(parents=True)
            (root / "skills" / "x" / "SKILL.md").write_text(
                "Keep it masked until unblinding is authorized by the user.\nUse blinding enforcement here.\n", encoding="utf-8")
            (root / "CHANGELOG.md").write_text("history: unblinding_authorization was renamed\n", encoding="utf-8")
            (root / "contracts" / "stanzas" / "context-resolution.md").write_text("no policy\n", encoding="utf-8")
            old = cit.ROOT
            cit.ROOT = root
            try:
                rep = cit.check()
            finally:
                cit.ROOT = old
            self.assertEqual(sorted((f["rule"], f["file"]) for f in rep["findings"]),
                             [("M01", "skills/x/SKILL.md"), ("M10", "skills/x/SKILL.md"),
                              ("M16", "contracts/stanzas/context-resolution.md")])


if __name__ == "__main__":
    unittest.main()
