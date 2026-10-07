"""pyproject.toml stays consistent with the plugin (T18): its version is the plugin's, its extras match the
requirements files, the CI lock pins every package of the core and test extras, and the tool configuration covers
the folders CI lints."""
import json
import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def requirement_lines(path: Path) -> list[str]:
    return [l.split("#")[0].strip() for l in path.read_text(encoding="utf-8").splitlines()
            if l.split("#")[0].strip() and not l.startswith("-r")]


def name(req: str) -> str:
    return re.split(r"[<>=!~\[ ]", req, maxsplit=1)[0].lower()


class PyprojectTests(unittest.TestCase):
    def test_version_matches_the_plugin(self):
        for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            self.assertEqual(PYPROJECT["project"]["version"], json.loads((ROOT / manifest).read_text())["version"], manifest)

    def test_extras(self):
        extras = PYPROJECT["project"]["optional-dependencies"]
        self.assertEqual(set(extras), {"core", "pyhf", "root-uproot", "hepdata", "torch", "diagrams", "test", "lint"})
        self.assertEqual(sorted(extras["core"]), sorted(requirement_lines(ROOT / "requirements-core.txt")))
        self.assertEqual(sorted(extras["test"]), sorted(requirement_lines(ROOT / "requirements-test.txt")))

    def test_lock_pins_the_core_and_test_extras(self):
        lock = {name(l): l.split("==")[1] for l in requirement_lines(ROOT / "requirements-ci.lock")}
        self.assertTrue(all("==" in l for l in requirement_lines(ROOT / "requirements-ci.lock")))
        for req in PYPROJECT["project"]["optional-dependencies"]["core"] + PYPROJECT["project"]["optional-dependencies"]["test"]:
            self.assertIn(name(req), lock, req)
        for bound in requirement_lines(ROOT / "requirements-ci-constraints.txt"):
            pkg, ceiling = bound.split("<")
            if pkg in lock:
                pinned = tuple(int(x) for x in lock[pkg].split(".")[:2])
                self.assertLess(pinned, tuple(int(x) for x in ceiling.split(".")[:2]), bound)

    def test_tool_configuration(self):
        self.assertEqual(PYPROJECT["tool"]["mypy"]["files"], ["core", "contracts"])
        self.assertIn("F", PYPROJECT["tool"]["ruff"]["lint"]["select"])
        self.assertEqual(PYPROJECT["tool"]["setuptools"]["packages"], [])  # the plugin is not an installable package


if __name__ == "__main__":
    unittest.main()
