"""pyhf-combine model checks (T18): input they cannot read or map is bad input, status "rejected" with exit 2.

The hep-computing script contract (skills/hep-computing/SKILL.md) gives bad input exit 2, and core/status.py names that
run status "rejected"; "refused" there is a negative verdict (exit 1). backend_comparison.py and model_card.py printed
"refused" with exit 2. Every input-refusal path of both tools is run: a missing file, a file that is not JSON, and a
model or card the tool cannot map. Needs pyhf (the dependency check comes first); listed in the stats-backends gate
(tools/run_required_backends.py), so a skip there fails."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "pyhf-combine" / "assets"
HAVE_PYHF = importlib.util.find_spec("pyhf") is not None
CONTRACT_EXIT = {"ok": 0, "negative verdict": 1, "bad input": 2, "missing dependency or incomplete": 3}  # SKILL.md

# (tool, option, file content or None for a missing file)
CASES = [
    ("backend_comparison.py", "--model", None),
    ("backend_comparison.py", "--model", "not json"),
    ("backend_comparison.py", "--model", json.dumps({"channels": "not a list"})),
    ("model_card.py", "--card", None),
    ("model_card.py", "--card", "not json"),
    ("model_card.py", "--card", json.dumps({"bins": 1})),
]


@unittest.skipUnless(HAVE_PYHF, "pyhf not installed: the input-refusal statuses of the pyhf adapters are unverified")
class PyhfAdapterRejectedInput(unittest.TestCase):
    def test_unreadable_or_unmappable_input_is_rejected_with_exit_2(self):
        for tool, option, content in CASES:
            with self.subTest(tool=tool, content=content), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "in.json"
                if content is not None:
                    path.write_text(content, encoding="utf-8")
                p = subprocess.run([sys.executable, "-I", str(ASSETS / tool), option, str(path)], capture_output=True,
                                   text=True, timeout=600, cwd=tmp)
                self.assertEqual(p.returncode, CONTRACT_EXIT["bad input"], p.stdout + p.stderr)
                self.assertEqual(json.loads(p.stdout)["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
