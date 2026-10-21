"""Packaging-scan rules (tools/check_packaging.py): the local-hostname rule still catches hostnames and no longer
flags the Claude Code file names CLAUDE.local.md and settings.local.json, which the independent review host notes
must name (maintainer decision 2026-10-21); the private-path rule still catches Claude session folders."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("check_packaging", ROOT / "tools" / "check_packaging.py")
CP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CP)
# planted values are assembled at run time, so this shipped file does not trip the scan it tests
LOCAL, TMP, PROJECTS = "." + "local", "/" + "tmp/claude", "." + "claude/projects/"


class LocalHostnameRuleTests(unittest.TestCase):
    def test_hostnames_are_still_caught(self):
        for text in (f"ssh mymac{LOCAL}", f"host-1{LOCAL}:8080", f"see build-box{LOCAL}.", f"printer{LOCAL}/queue"):
            self.assertTrue(CP.RESTRICTED.search(text), text)

    def test_claude_code_file_names_are_not_hostnames(self):
        for text in (f"CLAUDE{LOCAL}.md", f".claude/settings{LOCAL}.json", f"`CLAUDE{LOCAL}.md` in the working directory"):
            self.assertIsNone(CP.RESTRICTED.search(text), text)


class PrivatePathRuleTests(unittest.TestCase):
    def test_session_folders_are_still_caught(self):
        for text in (f"{TMP}-501/x/scratchpad", f"/private{TMP}-0/p", f"~/{PROJECTS}-a-b/s/tool-results"):
            self.assertTrue(CP.PRIVATE.search(text), text)

    def test_placeholder_patterns_are_not_private_paths(self):
        for text in ("<tmp>/claude-<uid>/<project-slug>/*/scratchpad", "<claude-config>/projects/<project-slug>/*/tool-results"):
            self.assertIsNone(CP.PRIVATE.search(text), text)
            self.assertIsNone(CP.RESTRICTED.search(text), text)


def scan(files: dict[str, str | bytes]) -> list[dict]:
    """Findings of tools/check_packaging.py --root on a temp tree holding files (not a git checkout)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for rel, body in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(body, bytes):
                p.write_bytes(body)
            else:
                p.write_text(body, encoding="utf-8")
        res = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "check_packaging.py"), "--root", str(root)],
                             capture_output=True, text=True, timeout=120)
    return [f for f in json.loads(res.stdout)["findings"] if f["rule"] != "size-statement-drift"]


HOME = "/" + "Users/alice/"


class TextScanCoverageTests(unittest.TestCase):
    """T27: only files with a suffix in TEXT were scanned, so a .hh header, a suffix-less shim or a .patch was not."""

    def test_every_text_file_is_scanned(self):
        for rel in ("adapters/g4/include/Probe.hh", "skills/a/scripts/shim", "docs/fix.patch", "examples/x/Snakefile",
                    "examples/x/run.out", "LICENSE"):
            with self.subTest(file=rel):
                found = scan({rel: f"#include <x>\nconst char* p = \"{HOME}secret\";\n"})
                self.assertIn(("private-path", rel), {(f["rule"], f["file"]) for f in found}, found)

    def test_binary_files_are_not_scanned(self):
        self.assertEqual(scan({"docs/img.bin": b"\x89PNG\x00\x00" + HOME.encode() + b"secret"}), [])


if __name__ == "__main__":
    unittest.main()
