"""The interpreter guard's variables (HEP_RESEARCH_PYTHON, HEP_RESEARCH_GUARD_REEXEC) never reach a batch job: the
executor refuses them as passthrough names and bundle freezing refuses a spec or configuration that sets them.
Synthetic campaigns only."""
import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.interpreter_guard import MARKER_VARIABLE, TARGET_VARIABLE  # noqa: E402
from core.partition import bundle as bd  # noqa: E402
from core.partition import campaign as cp  # noqa: E402
from core.partition import engine  # noqa: E402
from core.partition import executors as ex  # noqa: E402
from tests.core.partition_helpers import WORKER  # noqa: E402

GUARD = (TARGET_VARIABLE, MARKER_VARIABLE)


class Passthrough(unittest.TestCase):
    def test_guard_variables_are_refused(self):
        for name in GUARD:
            with self.subTest(name=name):
                problems = ex.passthrough_problems([name])
                self.assertEqual(len(problems), 1)
                self.assertIn("interpreter guard variable", problems[0])
                with self.assertRaises(ValueError):
                    ex.allowed_env({name: "/usr/bin/python3"}, [name])

    def test_other_names_still_pass(self):
        self.assertEqual(ex.passthrough_problems(["OMP_NUM_THREADS", "HEP_RESEARCH_OTHER"]), [])

    def test_guard_variables_never_leak_without_passthrough(self):
        env = {TARGET_VARIABLE: "/opt/py/bin/python3.13", MARKER_VARIABLE: "1", "PATH": "/usr/bin"}
        self.assertEqual(ex.allowed_env(env), {"PATH": "/usr/bin"})


class Freeze(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        root = Path(self.scratch.name)
        self.worker = root / "worker"
        self.worker.mkdir()
        (self.worker / "work.py").write_text(WORKER)
        q = shlex.quote
        cmd = (f"{q(sys.executable)} {q(str(self.worker / 'work.py'))} --start {{start}} --stop {{stop}} "
               "--seed {seed} --out {out} --id {id}")
        self.cdir = cp.init(root / "camp", engine.make_manifest("synthetic-guard", 8, 4, 3), cmd)
        state = json.loads((Path(self.cdir) / "state.json").read_text(encoding="utf-8"))
        if not state.get("campaign_uid"):
            state["campaign_uid"] = "synthetic-uid"
            (Path(self.cdir) / "state.json").write_text(json.dumps(state), encoding="utf-8")

    def test_plain_freeze_still_works(self):
        doc = bd.freeze(self.cdir, self.worker)
        self.assertFalse(doc["reused"])

    def test_spec_environment_with_a_guard_variable_is_refused(self):
        spec_path = Path(self.cdir) / "spec.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        for key in ("env", "environment"):
            for name in GUARD:
                with self.subTest(key=key, name=name):
                    spec_path.write_text(json.dumps(dict(spec, **{key: {name: "/x/python3"}})), encoding="utf-8")
                    with self.assertRaises(bd.BundleError) as ctx:
                        bd.freeze(self.cdir, self.worker)
                    self.assertEqual(ctx.exception.code, "bundle.guard_variable")
        self.assertFalse(any((Path(self.cdir) / "bundles").glob("*.json")), "a refused freeze writes nothing")

    def test_configuration_passthrough_with_a_guard_variable_is_refused(self):
        for name in GUARD:
            with self.subTest(name=name):
                with self.assertRaises(bd.BundleError) as ctx:
                    bd.freeze(self.cdir, self.worker, config={"env_passthrough": [name]})
                self.assertEqual(ctx.exception.code, "bundle.guard_variable")


if __name__ == "__main__":
    unittest.main()
