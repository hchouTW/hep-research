"""tools/check_retired_names.py: the maintained tree spells no skill name retired in contracts 3.0.0; a planted name is
found, history files are not scanned, and case matters (ordinary text such as a capitalised compound is not a name).
The retired name is built from parts so this file does not spell it."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import check_retired_names as crn  # noqa: E402

OLD = "-".join(("physics", "ml"))


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = crn.main(argv)
    return code, json.loads(out.getvalue())


class RetiredNameTests(unittest.TestCase):
    def test_tree_is_clean(self):
        code, res = run([])
        self.assertEqual((code, res["hits"]), (0, []))

    def test_planted_name_is_found_and_history_is_not_scanned(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel in ("docs/a.md", "CHANGELOG.md", "release-manifests/0.1.0.json", "docs/dev/old.md",
                        "profiles/experiments/x/evidence/claims.json"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(f"intro\nsee {OLD} here\n", encoding="utf-8")
            (root / "docs" / "b.md").write_text(f"{OLD.title()} researcher\n", encoding="utf-8")
            code, res = run(["--root", str(root)])
        self.assertEqual((code, res["status"], res["hits"]), (1, "fail", [{"file": "docs/a.md", "line": 2}]))

    def test_bad_input(self):
        self.assertEqual(run(["--nope"])[0], 2)
        self.assertEqual(run(["--root", "/no/such/folder"])[0], 2)


if __name__ == "__main__":
    unittest.main()
