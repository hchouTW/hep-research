"""tools/check_naming.py (semantic naming spec §8.5, P2 acceptance): the plugin's own gate passes on clean code, fails
when a forbidden name such as do_something() is added, applies the known-gaps baseline and reports stale entries."""
from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_naming", ROOT / "tools" / "check_naming.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.workdir.cleanup)
        self.root = Path(self.workdir.name)
        (self.root / ".claude-plugin").mkdir()
        (self.root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "hep-research"}))
        (self.root / "core").mkdir()
        (self.root / "core" / "selection.py").write_text("def apply_selection_cuts(events):\n    return events\n")
        (self.root / "skills" / "hep-demo").mkdir(parents=True)
        (self.root / "skills" / "hep-demo" / "SKILL.md").write_text("# demo\n")  # an N16 input: zero inputs fail the gate
        self.gaps = self.root / "gaps.json"

    def gate(self, *extra):
        out = io.StringIO()
        with redirect_stdout(out):
            code = G.main(["--root", str(self.root), "--known-gaps", str(self.gaps), *extra])
        return code, json.loads(out.getvalue())

    def test_clean_code_passes(self):
        code, out = self.gate()
        self.assertEqual((code, out["status"]), (0, "pass"), out)

    def test_do_something_fails(self):
        (self.root / "core" / "helpers.py").write_text("def do_something():\n    pass\n")
        code, out = self.gate()
        self.assertEqual(code, 1)
        self.assertEqual([f["current"] for f in out["new_findings"]], ["do_something"])

    def test_known_gap_applies_and_stale_entries_are_reported(self):
        (self.root / "core" / "helpers.py").write_text("def do_something():\n    pass\n")
        self.assertEqual(self.gate("--write-known-gaps")[0], 0)
        code, out = self.gate()
        self.assertEqual((code, out["known_gaps_applied"]), (0, 1))
        (self.root / "core" / "helpers.py").write_text("def apply_trigger_cuts():\n    pass\n")
        code, out = self.gate()
        self.assertEqual(code, 0)
        self.assertEqual(out["stale_count"], 1)

    def test_zero_inputs_fail(self):
        (self.root / "skills" / "hep-demo" / "SKILL.md").unlink()
        code, out = self.gate()
        self.assertEqual(code, 1)
        self.assertEqual({f["state"] for f in out["new_findings"]}, {"unsupported"})

    def test_unsupported_results_are_never_baselined(self):
        (self.root / "skills" / "hep-demo" / "SKILL.md").unlink()
        self.gate("--write-known-gaps")
        self.assertEqual(json.loads(self.gaps.read_text())["gaps"], {})
        self.assertEqual(self.gate()[0], 1)

    def test_shipped_baseline_is_well_formed(self):
        doc = json.loads((ROOT / "tools" / "naming_known_gaps.json").read_text())
        self.assertEqual(doc["known_gaps_version"], "1.0.0")
        self.assertTrue(all(isinstance(v, int) and v > 0 for v in doc["gaps"].values()))


if __name__ == "__main__":
    unittest.main()
