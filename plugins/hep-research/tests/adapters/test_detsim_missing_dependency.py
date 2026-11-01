"""The detector-simulation adapter without ROOT or uproot (R-07 (i) of docs/dev/detector-simulation/TASK.md).

detsim.py is the adapter's only command (the only assets file containing the string __main__) and imports no
third-party package anywhere, so tests/adapters/test_adapter_missing_dependency.py does not put it in its domain.
This test hides ROOT and uproot (sys.modules[name] = None, so importing them fails whether or not they are
installed) and runs describe, check and prepare with the simulator-free backend: everything this version offers
works without them. The backends import ROOT or uproot only inside the functions that need them (the Garfield++
backend not at all: ROOT is imported by its query script, in the backend process); with ROOT hidden, check --probe of
the Garfield++ backend answers missing-dependency (exit 3) for an environment root without ROOT (more cases in
test_detsim_garfield.py). The Allpix Squared backend's expectation comes with work item W4A.
SYNTHETIC inputs; standard library only.
"""
import ast
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "detector-simulation" / "assets"
HERE = Path(__file__).resolve().parent
for _entry in (str(ROOT), str(ASSETS), str(HERE)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import detsim_backend_synthetic as synthetic  # noqa: E402
from tests._platform import needs  # noqa: E402
from tests.adapters.test_adapter_missing_dependency import third_party_imports  # noqa: E402
from tests.adapters.test_detsim_plan import run_cli  # noqa: E402

HIDDEN = ("ROOT", "uproot")


class WithoutRootOrUproot(unittest.TestCase):
    def test_only_detsim_is_a_command_and_it_has_no_third_party_import(self):
        commands = sorted(p.name for p in ASSETS.glob("*.py") if "__main__" in p.read_text(encoding="utf-8"))
        self.assertEqual(commands, ["detsim.py"])
        for path in sorted(ASSETS.glob("*.py")):
            with self.subTest(module=path.name):
                self.assertEqual(third_party_imports(str(path.relative_to(ROOT))), [])
                tree = ast.parse(path.read_text(encoding="utf-8"))
                names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
                names |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
                self.assertFalse(names & set(HIDDEN), path.name)

    @needs("process_groups")
    def test_describe_check_prepare_without_root_and_uproot(self):
        with tempfile.TemporaryDirectory() as scratch:
            project = synthetic.make_project(Path(scratch) / "project")
            for hidden in ("ROOT", "uproot", "ROOT,uproot"):
                for argv in (["describe"], ["--backend", "synthetic", "describe"],
                             ["--backend", "synthetic", "check", "--workspace", str(project), "--task", "task.json"],
                             ["--backend", "synthetic", "prepare", "--workspace", str(project), "--task", "task.json"],
                             ["--backend", "synthetic", "prepare", "--workspace", str(project), "--task", "task.json",
                              "--digest-only", "--replicate", "3"]):
                    with self.subTest(hidden=hidden, argv=argv[-3:]):
                        code, answer, err = run_cli(argv, hide=hidden)
                        self.assertEqual((code, answer["status"]), (0, "ok"), (answer, err[-300:]))

    @needs("process_groups")
    def test_garfield_probe_without_root_is_missing_dependency(self):
        with tempfile.TemporaryDirectory() as scratch:
            project = synthetic.make_project(Path(scratch) / "project")
            empty_view = Path(scratch) / "view without ROOT"
            (empty_view / "bin").mkdir(parents=True)
            for hidden in ("ROOT", "ROOT,uproot"):
                with self.subTest(hidden=hidden):
                    code, answer, err = run_cli(["--backend", "garfieldpp", "describe"], hide=hidden)
                    self.assertEqual((code, answer["status"]), (0, "ok"), (answer, err[-300:]))
                    code, answer, err = run_cli(["--backend", "garfieldpp", "check", "--workspace", str(project),
                                                 "--probe", "--env-root", str(empty_view)], hide=hidden)
                    self.assertEqual((code, answer["status"], answer["error_code"]),
                                     (3, "missing-dependency", "missing-dependency"), (answer, err[-300:]))
                    self.assertTrue(any("ROOT" in m for m in answer["missing"]), answer["missing"])

    def test_hidden_module_really_fails_to_import(self):
        proc = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.modules['ROOT'] = None; import ROOT"],
                              capture_output=True, text=True, timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("ModuleNotFoundError", proc.stderr)


if __name__ == "__main__":
    unittest.main()
