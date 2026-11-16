"""The 0.70.0 compatibility layer of the simcal rename (docs/dev/simcal-naming-map.md): files written by 0.69.0 under the
old schema ids are read through the aliases of core/simcal/legacy.py with only the notice `simcal.legacy_schema_id`, and
read and hashed as written (their hash citations resolve); the deprecated script stubs forward arguments, output and
exit codes; `core.calibration` is an alias package of `core.simcal`.

tests/core/data/legacy-0.69/ was made with the 0.69.0 code (main 5b47c577): fixture.json is its
core/calibration/data/toy_detector_design.json, contract.json and plan.json are that fixture's two parts,
result.json, result_contract.json and snapshot_template.json are the inputs r.json, c.json and s.json of the golden case
propagate_g4sim_snapshot (tests/core/data/simcal_p5_identity.json), and ask_tell_state.json was written by the 0.69.0
emulator script (`init --purpose training`) from emulator_fixture.json.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.simcal import legacy  # noqa: E402
from contracts.schema import validate  # noqa: E402

LEGACY = ROOT / "tests" / "core" / "data" / "legacy-0.69"
S = ROOT / "skills" / "hep-statistics" / "scripts"
GOLDEN = ROOT / "tests" / "core" / "data" / "simcal_p5_identity.json"
NOTICE = re.compile(r"^simcal\.legacy_schema_id: (\S+) is read as (\S+) ")
STEMS = ("chain", "closure", "contract", "contrib", "data", "deps", "design", "emulator", "fit", "identify", "interval",
         "kernel_check", "likelihood", "propagate", "reweight", "shift", "use", "validate")
STUBS = [(S / f"calib_{s}.py", S / f"simcal_{s}.py") for s in STEMS] + \
    [(ROOT / "adapters" / "geant4" / "assets" / "g4sim_calib_eval.py",
      ROOT / "adapters" / "geant4" / "assets" / "g4sim_simcal_eval.py")]


def run(script: Path, *args, cwd=None, timeout=300):
    res = subprocess.run([sys.executable, "-I", str(script), *map(str, args)], capture_output=True, text=True,
                         timeout=timeout, cwd=cwd)
    return res.returncode, res.stdout, res.stderr


def notices(stderr: str) -> list:
    """The (old, new) ids of the notices; fails on any other stderr line."""
    out = []
    for line in stderr.splitlines():
        m = NOTICE.match(line)
        if not m:
            raise AssertionError(f"stderr has more than the notice: {line!r}")
        out.append(m.groups())
    return out


def renamed(text: str) -> str:
    """The text with each old id replaced by its new id (what a 0.70.0 writer would have written)."""
    for old_id, new_id in legacy.OLD_TO_NEW_ID.items():
        text = text.replace(f'"{old_id}"', f'"{new_id}"')
    return text


class Legacy(unittest.TestCase):
    def setUp(self):
        legacy._noticed.clear()

    def test_aliases_and_notice_once(self):
        for old_id, new_id in legacy.OLD_TO_NEW_ID.items():
            self.assertTrue(legacy.is_schema({"schema": new_id}, new_id))
            self.assertTrue(legacy.is_schema({"schema": old_id}, new_id))
        self.assertFalse(legacy.is_schema({"schema": "simcal-plan/1"}, "simcal-fixture/1"))
        self.assertFalse(legacy.is_schema({"schema": "calibration-plan/1"}, "simcal-fixture/1"))
        self.assertFalse(legacy.is_schema({"schema": "other/1"}, "simcal-fixture/1"))
        self.assertFalse(legacy.is_schema(["simcal-fixture/1"], "simcal-fixture/1"))
        self.assertEqual(len(legacy.OLD_TO_NEW_ID), 10)

    def test_schemas_accept_the_old_and_the_new_id_only(self):
        for name, f in (("simcal_contract.json", "contract.json"), ("simcal_plan.json", "plan.json"),
                        ("simcal_fixture.json", "fixture.json"), ("simcal_result.json", "result.json")):
            doc = json.loads((LEGACY / f).read_text())
            schema = json.loads((ROOT / "contracts" / "schemas" / name).read_text())
            self.assertEqual(schema["properties"]["schema"]["enum"][1], doc["schema"], name)
            for sid in schema["properties"]["schema"]["enum"]:
                self.assertFalse([e for e in validate({**doc, "schema": sid}, name).errors if e.path == "$.schema"])
            self.assertTrue([e for e in validate({**doc, "schema": "calibration-other/1"}, name).errors
                             if e.path == "$.schema"], name)


class OldFiles(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="simcal-compat-"))
        self.addCleanup(shutil.rmtree, self.d)

    def both(self, script, files: dict, *args):
        """Run `script` on the 0.69.0 files and on the same files with the new ids: (old run, new run)."""
        out = []
        for tag, f in (("old", lambda t: t), ("new", renamed)):
            w = self.d / tag
            w.mkdir()
            for n, src in files.items():
                (w / n).write_text(f((LEGACY / src).read_text()))
            out.append(run(S / script, *args, cwd=w))
        return out

    def test_fixture_through_the_chain(self):
        (rc0, out0, err0), (rc1, out1, err1) = self.both("simcal_chain.py", {"fx.json": "fixture.json"}, "p4",
                                                         "--contract", "fx.json")
        self.assertEqual((rc0, out0), (rc1, out1))
        self.assertEqual(notices(err0), [("calibration-fixture/1", "simcal-fixture/1")])
        self.assertEqual(err1, "")

    def test_contract_check(self):
        """The contract checker validates the 0.69.0 contract; its lock hash is that of the file as written (the hash
        covers the schema field), so the two runs differ only in contract_sha256."""
        from core.canonical import canonical_sha256
        (rc0, out0, err0), (rc1, out1, err1) = self.both("simcal_contract.py", {"c.json": "contract.json"}, "check",
                                                         "--contract", "c.json")
        r0, r1 = json.loads(out0), json.loads(out1)
        old = json.loads((LEGACY / "contract.json").read_text())
        self.assertEqual(r0["contract_sha256"], canonical_sha256(old))
        self.assertEqual(r1["contract_sha256"], canonical_sha256(json.loads(renamed(json.dumps(old)))))
        self.assertEqual((rc0, {**r0, "contract_sha256": None}), (rc1, {**r1, "contract_sha256": None}))
        self.assertFalse([e for e in r0.get("findings", []) if "schema" in json.dumps(e)])
        self.assertEqual(err1, "")
        notices(err0)

    def test_contract_and_plan(self):
        (rc0, out0, err0), (rc1, out1, err1) = self.both(
            "simcal_kernel_check.py", {"c.json": "contract.json", "p.json": "plan.json"}, "p0", "--contract", "c.json",
            "--plan", "p.json")
        self.assertEqual((rc0, out0), (rc1, out1))
        self.assertEqual(notices(err0), [])
        self.assertEqual(err1, "")

    def test_result_hash_citations_resolve(self):
        """The golden case's result is read as written: the exported record cites the hash of the 0.69.0 file and
        equals the 0.69.0 output byte for byte."""
        case = json.loads(GOLDEN.read_text())["cases"]["propagate_g4sim_snapshot"]
        for n, src in (("r.json", "result.json"), ("c.json", "result_contract.json"), ("s.json", "snapshot_template.json")):
            (self.d / n).write_text((LEGACY / src).read_text())
        rc, out, err = run(S / case["script"], *case["args"], cwd=self.d)
        self.assertEqual((rc, out), (case["golden"]["returncode"], case["golden"]["stdout"]))
        self.assertEqual((self.d / "out.json").read_text(), case["golden"]["outputs"]["out.json"])
        self.assertEqual(notices(err), [])
        result = json.loads((LEGACY / "result.json").read_text())
        self.assertEqual(json.loads(out)["record"]["source_of_facts"]["calibration_result"]["result_sha256"],
                         result["result_sha256"])

    def test_ask_tell_state(self):
        st = self.d / "state.json"
        st.write_text((LEGACY / "ask_tell_state.json").read_text())
        rc, out, err = run(S / "simcal_emulator.py", "ask", "--state", st, "--n", "2")
        self.assertEqual((rc, [q["run_id"] for q in json.loads(out)["requests"]]), (0, ["training-0000", "training-0001"]))
        self.assertEqual(notices(err), [("calibration-ask-tell/1", "simcal-ask-tell/1")])
        st.write_text(json.dumps({**json.loads(st.read_text()), "schema": "calibration-other/1"}))
        self.assertEqual(run(S / "simcal_emulator.py", "ask", "--state", st, "--n", "1")[0], 2)


class Shims(unittest.TestCase):
    def test_stubs_forward_arguments_output_and_exit_code(self):
        self.assertEqual(len(STUBS), 19)
        for stub, script in STUBS:
            self.assertTrue(stub.is_file(), stub)
            for args in (["--help"], [], ["--no-such-option"]):
                rc0, out0, err0 = run(stub, *args)
                rc1, out1, err1 = run(script, *args)
                lines = err0.splitlines()
                self.assertTrue(lines and lines[0].startswith("simcal.deprecated_script: ")
                                and script.name in lines[0], (stub.name, err0[:200]))
                self.assertEqual((rc0, out0, "\n".join(lines[1:])), (rc1, out1, err1.rstrip("\n")), (stub.name, args))

    def test_old_evaluator_import_registers_the_g4sim_kind(self):
        """0.69.0 code registered the g4sim evaluator by importing it under its old name (review F4)."""
        assets = ROOT / "adapters" / "geant4" / "assets"
        code = ("import sys, warnings\n"
                f"sys.path[:0] = [{str(assets)!r}, {str(ROOT)!r}]\n"
                "with warnings.catch_warnings(record=True) as w:\n"
                "    warnings.simplefilter('always')\n"
                "    import g4sim_calib_eval as old\n"
                "import g4sim_simcal_eval as renamed\n"
                "from core.simcal import evaluator\n"
                "print(old is renamed, 'g4sim' in evaluator._REGISTERED, [x.category.__name__ for x in w])")
        res = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(res.stdout.strip(), "True True ['DeprecationWarning']", res.stderr)

    def test_old_package_is_the_new_one(self):
        code = ("import warnings; warnings.simplefilter('always')\n"
                "import core.simcal.use as new\n"
                "with warnings.catch_warnings(record=True) as w:\n"
                "    warnings.simplefilter('always')\n"
                "    import core.calibration.use as old\n"
                "print(old is new, new.__spec__.name, [str(x.category.__name__) for x in w])")
        res = subprocess.run([sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {str(ROOT)!r})\n" + code],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(res.stdout.strip(), "True core.simcal.use ['DeprecationWarning']", res.stderr)


if __name__ == "__main__":
    unittest.main()
