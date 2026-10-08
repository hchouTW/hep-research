"""T4.7: machine-readable tool contracts. Every shipped contract passes against its tool's command line, the tool
behaves as its contract says on synthetic inputs (declared outputs present, declared failure exits observed), and
mutated contracts or scopes fail with a specific code. Synthetic values only."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import tool_contract as tc  # noqa: E402

FLUX = json.loads((ROOT / "contracts" / "tool_contracts" / "cosmic_ray_flux.json").read_text(encoding="utf-8"))
FLUX_ARGS = ["--counts", "42", "--exposure", "1.5e7", "--bin-width", "10"]


def codes(res):
    return sorted({f["code"] for f in res["findings"] if f["severity"] == "error"})


def run_tool(entry, args):
    return subprocess.run([sys.executable, "-I", "-B", str(ROOT / entry), *args], capture_output=True, text=True,
                          timeout=60)


class ShippedContractTests(unittest.TestCase):
    def test_every_shipped_contract_passes(self):
        paths = sorted(tc.CONTRACT_DIR.glob("*.json"))
        self.assertTrue(paths)
        for p in paths:
            with self.subTest(contract=p.name):
                res = tc.check(json.loads(p.read_text(encoding="utf-8")))
                self.assertEqual(res["status"], "pass", res["findings"])

    def test_flux_tool_behaves_as_contracted(self):
        op = FLUX["operations"][0]
        p = run_tool(FLUX["entry"], FLUX_ARGS)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        for o in op["outputs"]:
            self.assertIn(o["name"], out)
        self.assertAlmostEqual(out["flux"], 42 / (1.5e7 * 10))

    def test_flux_failure_states_are_the_declared_exit(self):
        declared = {f["exit_code"] for f in FLUX["operations"][0]["failure_states"]}
        bad = [["--counts", "-1", "--exposure", "1", "--bin-width", "1"],
               ["--counts", "3", "--exposure", "0", "--bin-width", "1"],
               ["--counts", "3", "--exposure", "1", "--bin-width", "nan"],
               ["--counts", "501", "--exposure", "1", "--bin-width", "1"],
               FLUX_ARGS + ["--level", "0"], FLUX_ARGS + ["--level", "1"], FLUX_ARGS + ["--level", "nan"],
               FLUX_ARGS + ["--background", "-1"], ["--exposure", "1", "--bin-width", "1"],
               ["--counts", "3", "--exposure", "1e-200", "--bin-width", "1e-200"],
               ["--counts", "3", "--exposure", "1e200", "--bin-width", "1e200"],
               ["--counts", "10", "--exposure", "1", "--bin-width", "1", "--background-sigma", "1e200"]]
        for args in bad:
            with self.subTest(args=args):
                p = run_tool(FLUX["entry"], args)
                self.assertIn(p.returncode, declared)
                self.assertEqual(p.stdout, "")

    def test_cli_runs(self):
        p = subprocess.run([sys.executable, "-B", str(ROOT / "contracts" / "tool_contract.py")], capture_output=True,
                           text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["status"], "pass")


class MutationTests(unittest.TestCase):
    def mutate(self, fn, help_check=True):
        doc = copy.deepcopy(FLUX)
        fn(doc)
        return tc.check(doc, help_check=help_check)

    def op(self, doc):
        return doc["operations"][0]

    def test_option_omitted_from_contract(self):
        def drop(d):
            self.op(d)["invocation"]["options"] = [o for o in self.op(d)["invocation"]["options"] if o["flag"] != "--level"]
            self.op(d)["inputs"] = [i for i in self.op(d)["inputs"] if i["name"] != "level"]
        self.assertIn("tool.option_undeclared", codes(self.mutate(drop)))

    def test_option_the_tool_lacks(self):
        def add(d):
            self.op(d)["invocation"]["options"].append({"flag": "--seed", "input": "seed"})
            self.op(d)["inputs"].append({"name": "seed", "kind": "parameter", "unit": "1", "required": False,
                                         "constraint": "integer"})
        self.assertIn("tool.option_missing", codes(self.mutate(add)))

    def test_required_mismatch(self):
        def flip(d):
            next(i for i in self.op(d)["inputs"] if i["name"] == "exposure")["required"] = False
        self.assertIn("tool.required_mismatch", codes(self.mutate(flip)))

    def test_unmapped_and_unreachable(self):
        def orphan(d):
            self.op(d)["inputs"].append({"name": "orphan", "kind": "parameter", "unit": "1", "required": False,
                                         "constraint": "none"})
            self.op(d)["invocation"]["options"].append({"flag": "--ghost", "input": "ghost"})
        c = codes(self.mutate(orphan, help_check=False))
        self.assertIn("tool.input_unreachable", c)
        self.assertIn("tool.option_unmapped", c)

    def test_default_on_required(self):
        self.assertIn("tool.default_on_required",
                      codes(self.mutate(lambda d: self.op(d)["inputs"][0].update(default=1), help_check=False)))

    def test_ambiguous_exit(self):
        def dup(d):
            self.op(d)["failure_states"].append({"exit_code": 2, "status": "failed", "meaning": "other"})
        self.assertIn("tool.ambiguous_exit", codes(self.mutate(dup, help_check=False)))

    def test_unknown_capability(self):
        self.assertIn("tool.unknown_capability", codes(self.mutate(
            lambda d: self.op(d)["required_capabilities"].append("core:never-implemented"), help_check=False)))

    def test_unbound_unit_symbol(self):
        self.assertIn("tool.unit_unbound", codes(self.mutate(
            lambda d: self.op(d)["outputs"][3].update(unit="1/({X} {E} {T})"), help_check=False)))

    def test_unknown_operator(self):
        self.assertIn("tool.unknown_operator", codes(self.mutate(
            lambda d: self.op(d)["operators"].append("divide_twice"), help_check=False)))

    def test_schema_refusals(self):
        for name, fn in {
            "network": lambda d: self.op(d)["side_effects"].update(network=True),
            "formal purpose": lambda d: self.op(d)["purposes"].append("formal-analysis"),
            "no failure states": lambda d: self.op(d).update(failure_states=[]),
            "exit 0 as failure": lambda d: self.op(d)["failure_states"][0].update(exit_code=0),
            "escaping entry": lambda d: d.update(entry="../outside.py"),
            "authorization field": lambda d: self.op(d).update(approved=True),
        }.items():
            with self.subTest(name):
                res = self.mutate(fn, help_check=False)
                self.assertEqual(res["status"], "fail")
                self.assertTrue(any(c.startswith("schema.") for c in codes(res)), codes(res))

    def test_entry_link_or_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "skills").mkdir()
            os.symlink(ROOT / FLUX["entry"], root / "skills" / "flux.py")
            doc = dict(copy.deepcopy(FLUX), entry="skills/flux.py")
            self.assertIn("tool.entry_missing", codes(tc.check(doc, root=root)))
            (root / "real").mkdir()
            (root / "real" / "flux.py").write_bytes((ROOT / FLUX["entry"]).read_bytes())
            os.symlink(root / "real", root / "linked")
            doc["entry"] = "linked/flux.py"
            self.assertIn("tool.entry_missing", codes(tc.check(doc, root=root, help_check=False)))
            self.assertIn("tool.entry_missing", codes(tc.check(dict(doc, entry="real/flux.py"), root=root / "linked",
                                                               help_check=False)))
            doc["entry"] = "skills/absent.py"
            self.assertIn("tool.entry_missing", codes(tc.check(doc, root=root)))

    def test_usage_parsing(self):
        flags = tc.usage_flags("usage: x.py [-h] --a A [--b B]\n          [--c-d C_D] --e E\n\nbody --z\n")
        self.assertEqual(flags, {"--a": True, "--b": False, "--c-d": False, "--e": True})
        self.assertIsNone(tc.usage_flags("no usage here"))


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.results = {"cosmic-ray-flux": (FLUX, tc.check(FLUX, help_check=False))}

    def test_scope_passes(self):
        res = tc.check_scope({"operations": ["cosmic-ray-flux:flux"], "purpose": "fixed-execution"}, self.results)
        self.assertEqual(res["status"], "pass", res)

    def test_uncontracted_operation(self):
        res = tc.check_scope({"operations": ["cosmic-ray-flux:flux", "cosmic-ray-flux:other", "plot:draw"],
                              "purpose": "exploration"}, self.results)
        self.assertEqual(codes(res), ["scope.uncontracted"])
        self.assertEqual(len(res["findings"]), 2)

    def test_purpose_not_declared(self):
        doc = copy.deepcopy(FLUX)
        doc["operations"][0]["purposes"] = ["exploration"]
        res = tc.check_scope({"operations": ["cosmic-ray-flux:flux"], "purpose": "fixed-execution"},
                             {"cosmic-ray-flux": (doc, tc.check(doc, help_check=False))})
        self.assertEqual(codes(res), ["scope.purpose_undeclared"])

    def test_failing_contract_fails_scope(self):
        doc = copy.deepcopy(FLUX)
        doc["operations"][0]["required_capabilities"] = ["core:never-implemented"]
        res = tc.check_scope({"operations": ["cosmic-ray-flux:flux"], "purpose": "exploration"},
                             {"cosmic-ray-flux": (doc, tc.check(doc, help_check=False))})
        self.assertEqual(codes(res), ["scope.contract_failed"])

    def test_malformed_scope(self):
        for scope in ({}, {"operations": [], "purpose": "exploration"}, {"operations": ["a:b"], "purpose": "formal-analysis"},
                      {"operations": "a:b", "purpose": "exploration"}, []):
            with self.subTest(scope=scope):
                self.assertEqual(codes(tc.check_scope(scope, self.results)), ["scope.malformed"])

    def test_cli_scope_and_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            scope = Path(tmp) / "scope.json"
            scope.write_text(json.dumps({"operations": ["cosmic-ray-flux:missing"], "purpose": "exploration"}))
            p = subprocess.run([sys.executable, "-B", str(ROOT / "contracts" / "tool_contract.py"), "--no-help-check",
                                "--scope", str(scope)], capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 1)
            self.assertEqual(json.loads(p.stdout)["scope"]["status"], "fail")
            scope.write_text("null")
            p = subprocess.run([sys.executable, "-B", str(ROOT / "contracts" / "tool_contract.py"), "--no-help-check",
                                "--scope", str(scope)], capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 1)
            scope.write_text("{")
            p = subprocess.run([sys.executable, "-B", str(ROOT / "contracts" / "tool_contract.py"), "--scope", str(scope)],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 2)


if __name__ == "__main__":
    unittest.main()
