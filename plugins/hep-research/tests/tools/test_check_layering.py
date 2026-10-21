"""T23: layering violation fixtures. Each case builds a minimal plugin tree in a temp directory
(so deliberate violations never sit inside the package) and checks file, line and rule."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from check_layering import check  # noqa: E402

OWNERS = {"modules": {"bootstrap": {"steward": "hep-computing"}}}


def tree(files: dict[str, str]) -> tempfile.TemporaryDirectory:
    td = tempfile.TemporaryDirectory()
    base = Path(td.name)
    defaults = {"core/__init__.py": "", "core/bootstrap.py": "import os\n", "core/OWNERS.json": json.dumps(OWNERS),
                "profiles/registry.json": json.dumps({"registry_version": "1.0.0", "profiles": []})}
    for rel, text in {**defaults, **files}.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return td


def with_profiles(*profs):
    files, entries = {}, []
    for pid, path, deps, ns in profs:
        files[f"profiles/{path}/profile.json"] = json.dumps({"id": pid, "depends_on": deps, "evidence_namespace": ns})
        entries.append({"id": pid, "kind": "experiment", "version": "1.0.0", "scope": "x", "path": path})
    files["profiles/registry.json"] = json.dumps({"registry_version": "1.0.0", "profiles": entries})
    return files


class LayeringTests(unittest.TestCase):
    def run_case(self, files):
        with tree(files) as td:
            return check(Path(td))

    def assertViolation(self, violations, rule, file, line=None):
        hits = [v for v in violations if v["rule"] == rule and v["file"] == file and (line is None or v["line"] == line)]
        self.assertTrue(hits, f"expected {rule} at {file}:{line}, got {violations}")

    def test_clean_tree(self):
        self.assertEqual(self.run_case({"skills/a/SKILL.md": "General method text.\n"}), [])

    def test_shipped_plugin_is_clean(self):
        self.assertEqual(check(ROOT), [])

    def test_core_imports_profile(self):
        v = self.run_case({"core/stats.py": "import math\nfrom profiles.experiments import ams\n",
                           "core/OWNERS.json": json.dumps({"modules": {"bootstrap": {}, "stats": {}}})})
        self.assertViolation(v, "direction", "core/stats.py", 2)

    def test_core_references_profile_path(self):
        v = self.run_case({"core/bootstrap.py": "P = 'profiles/experiments/x/index.md'\n"})
        self.assertViolation(v, "direction", "core/bootstrap.py", 1)

    def test_hard_coded_profile_id_in_skill_text(self):
        v = self.run_case({"skills/hep-measurement/SKILL.md": "# x\n\nAlways use experiment:ams-02 defaults.\n"})
        self.assertViolation(v, "hard-coded-profile-id", "skills/hep-measurement/SKILL.md", 3)

    def test_profile_path_in_skill_text(self):
        v = self.run_case({"skills/hep-measurement/scripts/s.py": '"""See <plugin root>/profiles/experiments/foo-1/index.md."""\n'})
        self.assertViolation(v, "hard-coded-profile-path", "skills/hep-measurement/scripts/s.py", 1)

    def test_experiment_name_in_skill_text(self):
        v = self.run_case({"skills/hep-measurement/SKILL.md": "line\nAMS-02 uses rigidity.\n"})
        self.assertViolation(v, "hard-coded-experiment-name", "skills/hep-measurement/SKILL.md", 2)

    def test_eic_and_epic_names_are_flagged(self):
        md = "intro\nePIC tracking uses silicon.\nEIC beams are polarized.\n"
        v = self.run_case({"skills/hep-measurement/SKILL.md": md})
        self.assertViolation(v, "hard-coded-experiment-name", "skills/hep-measurement/SKILL.md", 2)
        self.assertViolation(v, "hard-coded-experiment-name", "skills/hep-measurement/SKILL.md", 3)

    def test_lowercase_epic_word_is_not_an_experiment_name(self):
        self.assertEqual(self.run_case({"skills/a/SKILL.md": "An epic derivation, not an experiment.\n"}), [])

    def test_example_block_is_whitelisted(self):
        md = "intro\n<!-- example: routing -->\n- AMS-02 flux -> experiment:ams-02\n<!-- /example -->\nend\n"
        py = "x = 1\n# example-begin\nID = 'experiment:ams-02'\n# example-end\n"
        self.assertEqual(self.run_case({"skills/a/SKILL.md": md, "skills/a/scripts/s.py": py}), [])

    def test_line_numbers_survive_example_blocks(self):
        md = "a\n<!-- example -->\nAMS\n<!-- /example -->\nCMS detail\n"
        v = self.run_case({"skills/a/SKILL.md": md})
        self.assertViolation(v, "hard-coded-experiment-name", "skills/a/SKILL.md", 5)

    def test_registered_namespace_in_core_code(self):
        files = with_profiles(("experiment:x-exp", "experiments/x-exp", [], "xex"))
        files["contracts/rules.py"] = "DEFAULT = 'xex:C017'\n"
        v = self.run_case(files)
        self.assertViolation(v, "hard-coded-namespace", "contracts/rules.py", 1)

    def test_skill_script_imports_other_skill(self):
        v = self.run_case({"skills/a/scripts/s.py": "from skills.b.scripts import t\n"})
        self.assertViolation(v, "direction", "skills/a/scripts/s.py", 1)

    def test_core_optional_dependency(self):
        v = self.run_case({"core/bootstrap.py": "import numpy\nimport torch\n"})
        self.assertViolation(v, "dependency", "core/bootstrap.py", 2)
        self.assertEqual(len([x for x in v if x["rule"] == "dependency"]), 1)

    def test_contracts_must_not_import_skills(self):
        v = self.run_case({"contracts/x.py": "import core\nimport skills.hep_theory\n"})
        self.assertViolation(v, "direction", "contracts/x.py", 2)

    def test_schema_requiring_collider_field(self):
        v = self.run_case({"contracts/schemas/m.json": json.dumps({"type": "object", "required": ["kind", "luminosity"]})})
        self.assertViolation(v, "schema-term", "contracts/schemas/m.json")

    def test_core_module_without_steward(self):
        v = self.run_case({"core/units.py": "import math\n"})
        self.assertViolation(v, "steward", "core/units.py")

    def test_core_relative_and_dynamic_imports_of_contracts(self):
        # T03: only absolute static imports were scanned, and any .py under a fixtures/ folder was skipped
        owners = json.dumps({"modules": {n: {"steward": "hep-computing"} for n in ("bootstrap", "x", "stats")}})
        cases = {"core/x.py": "from ..contracts import validate\n",
                 "core/stats/__init__.py": "import importlib\nM = importlib.import_module('contracts.validate')\n",
                 "core/stats/dyn.py": "C = __import__('contracts')\n",
                 "core/stats/fixtures/fx.py": "import contracts\n",
                 "core/stats/rel.py": "from ... import contracts\n"}
        for rel, code in cases.items():
            with self.subTest(file=rel):
                v = self.run_case({rel: code, "core/OWNERS.json": owners})
                hits = [x for x in v if x["rule"] == "direction" and x["file"] == rel]
                self.assertTrue(hits, f"expected a direction violation at {rel}, got {v}")
                self.assertIn("contracts", hits[0]["message"])

    def test_core_relative_imports_inside_core_are_clean(self):
        owners = json.dumps({"modules": {n: {"steward": "hep-computing"} for n in ("bootstrap", "stats")}})
        files = {"core/OWNERS.json": owners, "core/stats/__init__.py": "from . import fit\nfrom .fit import f\n",
                 "core/stats/fit.py": "from ..bootstrap import os\nimport importlib\nimportlib.import_module('core.bootstrap')\n",
                 "skills/a/scripts/s.py": "from . import t\nfrom .t import u\n", "skills/a/scripts/t.py": "u = 1\n"}
        self.assertEqual(self.run_case(files), [])

    def test_skill_relative_import_of_another_skill(self):
        v = self.run_case({"skills/a/scripts/s.py": "from ...b.scripts import t\n"})
        self.assertViolation(v, "direction", "skills/a/scripts/s.py", 1)

    def test_empty_or_placeholder_steward(self):
        # T04: only the presence of a key was checked, so steward '' or 'TBD' passed
        owners = {"modules": {"bootstrap": {"steward": "hep-computing"}, "units": {"steward": ""},
                              "tables": {"steward": "TBD"}, "misc": {}}}
        v = self.run_case({"core/OWNERS.json": json.dumps(owners), "core/units.py": "import math\n",
                           "core/tables.py": "import math\n", "core/misc.py": "import math\n"})
        for f in ("core/units.py", "core/tables.py", "core/misc.py"):
            self.assertViolation(v, "steward", f)
        self.assertEqual(len([x for x in v if x["rule"] == "steward"]), 3, v)

    def test_profile_reference_requires_depends_on(self):
        files = with_profiles(("experiment:a", "experiments/a", [], "a"), ("experiment:b", "experiments/b", [], "b"))
        files["profiles/experiments/a/index.md"] = "See profiles/experiments/b/index.md\n"
        v = self.run_case(files)
        self.assertViolation(v, "direction", "profiles/experiments/a/index.md", 1)
        files = with_profiles(("experiment:a", "experiments/a", ["experiment:b"], "a"), ("experiment:b", "experiments/b", [], "b"))
        files["profiles/experiments/a/index.md"] = "See profiles/experiments/b/index.md\n"
        self.assertEqual(self.run_case(files), [])


if __name__ == "__main__":
    unittest.main()
