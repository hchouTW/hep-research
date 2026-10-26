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
FLUX_ARGS = ["--counts", "42", "--exposure", "1.5e7", "--bin-width", "10", "--bin-width-unit", "GV"]
UNIT = ["--bin-width-unit", "GV"]


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
        bad = [["--counts", "-1", "--exposure", "1", "--bin-width", "1"] + UNIT,
               ["--counts", "3", "--exposure", "0", "--bin-width", "1"] + UNIT,
               ["--counts", "3", "--exposure", "1", "--bin-width", "nan"] + UNIT,
               ["--counts", "3", "--exposure", "1", "--bin-width", "1", "--background", "1", "--method", "garwood"] + UNIT,
               ["--counts", "480", "--exposure", "1", "--bin-width", "1", "--background", "10",
                "--method", "feldman-cousins"] + UNIT,  # M6: auto takes the asymptotic interval there
               FLUX_ARGS + ["--level", "0"], FLUX_ARGS + ["--level", "1"], FLUX_ARGS + ["--level", "nan"],
               FLUX_ARGS + ["--background", "-1"], ["--exposure", "1", "--bin-width", "1"],
               ["--counts", "3", "--exposure", "1", "--bin-width", "1"], FLUX_ARGS[:-1] + [""],  # M6: free unit
               ["--counts", "3", "--exposure", "1e-200", "--bin-width", "1e-200"] + UNIT,
               ["--counts", "3", "--exposure", "1e200", "--bin-width", "1e200"] + UNIT,
               ["--counts", "10", "--exposure", "1", "--bin-width", "1", "--background-sigma", "1e200"] + UNIT]
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
            self.op(d)["invocation"]["options"].append({"flag": "--no-such-option", "input": "no_such_option"})
            self.op(d)["inputs"].append({"name": "no_such_option", "kind": "parameter", "unit": "1", "required": False,
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
        grouped = tc.usage_flags("usage: x.py [-h] (--fit JSON | --evaluate) [--energy E]\n")
        self.assertEqual(grouped, {"--fit": False, "--evaluate": False, "--energy": False})


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



class ShippedScopeTests(unittest.TestCase):
    """P5.4: every tool a shipped recipe uses, the blinding CLIs and release preparation have passing contracts."""

    def test_shipped_scopes_pass(self):
        scopes = sorted((ROOT / "contracts" / "tool_scopes").glob("*.json"))
        self.assertEqual([p.stem for p in scopes], ["fixed-execution", "validation"])
        for path in scopes:
            with self.subTest(scope=path.stem):
                p = subprocess.run([sys.executable, "-B", str(ROOT / "contracts" / "tool_contract.py"), "--scope", str(path)],
                                   capture_output=True, text=True, timeout=600)
                self.assertEqual(p.returncode, 0, p.stdout[-2000:])
                self.assertEqual(json.loads(p.stdout)["scope"]["status"], "pass")

    def test_every_shipped_recipe_tool_is_scoped(self):
        scoped = set(json.loads((ROOT / "contracts" / "tool_scopes" / "fixed-execution.json").read_text())["operations"])
        for recipe in sorted((ROOT / "contracts" / "semantics" / "recipes").glob("*.json")):
            tools = {s["tool"] for s in json.loads(recipe.read_text()).get("steps", []) if isinstance(s, dict) and s.get("tool")}
            with self.subTest(recipe=recipe.name):
                self.assertTrue(tools, f"{recipe.name} names no tool")
                self.assertEqual(sorted(tools - scoped), [])


DR_ASSETS = ROOT / "skills" / "hep-detector" / "assets"
DR_CASES = {  # contract file -> (arguments that succeed, arguments that are invalid input)
    "tag_and_probe_efficiency.json": (["--pass-count", "92", "--total", "100"], ["--pass-count", "5", "--total", "3"]),
    "pid_separation_power.json": (["--mode", "tof", "--species", "pi", "K", "--momentum", "2"],
                                  ["--mode", "tof", "--species", "pi", "pi"]),
    "calorimeter_resolution.json": (["--fit", str(DR_ASSETS / "calorimeter-response.example.json")],
                                    ["--evaluate", "--energy", "-1"]),
    "pileup_reweight.json": ([str(DR_ASSETS / "pileup-profiles.example.json")], []),
}


class DetectorResponseContractTests(unittest.TestCase):
    """hep-detector audit DR-WP2-07: four tools behave as their contracts say: declared outputs present on
    success, declared exit codes on failure, and JSON on stdout at exit 2 (unlike cosmic_ray_flux.json)."""

    def test_declared_outputs_and_exits(self):
        for name, (good, bad) in DR_CASES.items():
            doc = json.loads((ROOT / "contracts" / "tool_contracts" / name).read_text(encoding="utf-8"))
            op = doc["operations"][0]
            with self.subTest(contract=name, case="ok"):
                p = run_tool(doc["entry"], good)
                self.assertEqual(p.returncode, 0, p.stderr)
                out = json.loads(p.stdout)
                for o in op["outputs"]:
                    self.assertIn(o["name"], out)
            if bad:
                with self.subTest(contract=name, case="invalid"):
                    p = run_tool(doc["entry"], bad)
                    self.assertIn(p.returncode, {f["exit_code"] for f in op["failure_states"]})
                    self.assertEqual(p.returncode, 2)
                    self.assertEqual(json.loads(p.stdout)["error_kind"], "invalid-input")

    def test_file_failures_exit_1_with_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps({"data_profile": [1, 0], "mc_profile": [1, 1], "bin_centers": [1, 0]}))
            for entry, args in (("skills/hep-detector/scripts/pileup_reweight.py", [str(bad)]),
                                ("skills/hep-detector/scripts/calorimeter_resolution.py", ["--fit", str(bad)])):
                with self.subTest(entry=entry):
                    p = run_tool(entry, args)
                    self.assertEqual(p.returncode, 1)
                    self.assertIs(json.loads(p.stdout)["ok"], False)


FRONTEND_OPS = {  # operation id -> (arguments that succeed, arguments that are invalid input)
    "enc": (["--capacitance", "10", "--en", "1", "--leakage", "1000", "--peaking", "25", "--rp", "1e7", "--af", "1e-12"],
            ["--capacitance", "10", "--peaking", "25", "--rp", "0"]),
    "noise-rate": (["--threshold", "4", "--peaking", "25", "--window", "100", "--channels", "10"],
                   ["--threshold", "4", "--peaking", "25", "--noise-type", "white"]),
    "timing": (["--rise", "1", "--snr", "50", "--threshold", "0.1", "--amplitudes", "1", "2", "--cfd-fraction", "0.3",
                "--cfd-delay", "1", "--tdc-lsb", "25"], ["--rise", "1", "--snr", "50", "--threshold", "0.1"]),
    "quantize": (["--noise-lsb", "0.5"], ["--noise-lsb", "x"]),
    "pileup": (["--rate", "1e6", "--mean-amp", "1", "--peaking", "25"], ["--rate", "1e6", "--peaking", "25"]),
    "sipm": (["--cells", "1000", "--npe", "100", "--crosstalk", "0.1", "--dcr", "1e5", "--gate", "100"],
             ["--cells", "1.5", "--npe", "100"]),
    "ballistic": (["--collection", "10", "--peaking", "25"], ["--collection", "10"]),
    "deadtime": (["--dead-time", "100", "--rate", "1e5"], ["--dead-time", "100", "--rate", "1e5", "--measured", "9e4"]),
    "leakage-scale": (["--current", "100", "--from-celsius", "20", "--to-celsius", "-10"],
                      ["--current", "100", "--from-celsius", "20"]),
    "cluster-noise": (["--channels", "3", "--sigma", "1", "--rho", "0.2"], ["--channels", "3", "--sigma", "1", "--rho", "2"]),
    "optimal-filter": (["--order", "4", "--peaking", "45", "--period", "25", "--samples", "5", "--first-offset", "-25",
                        "--rho", "0.3", "--pileup-rate", "1e6", "--pileup-rms", "2", "--amplitude", "40",
                        "--phase-errors", "-2", "2", "--constraints", "phase"],
                       ["--peaking", "45", "--period", "25", "--samples", "5", "--first-offset", "-25", "--rho", "1"]),
    "hit-efficiency": (["--thresholds", "3000", "6000", "--noise", "1000", "--mpv", "23000", "--xi", "1500",
                        "--threshold-dispersion", "300", "--peaking", "25", "--window", "25", "--min-efficiency", "0.99",
                        "--max-occupancy", "1e-4"],
                       ["--thresholds", "3000", "--noise", "1000", "--signal-model", "table"]),  # table without --spectrum
    "waveform-toy": (["--order", "2", "--peaking", "30", "--period", "10", "--samples", "6", "--first-offset", "-20",
                      "--amplitude", "20", "--events", "200", "--pileup-rate", "1e6", "--pileup-mean-amp", "2",
                      "--phase-jitter", "1", "--adc-lsb", "0.5", "--constraints", "baseline"],
                     ["--peaking", "30", "--period", "10", "--samples", "6", "--first-offset", "-20", "--amplitude",
                      "20", "--events", "5"]),
    "s-curve": (["--charges", "3000", "3400", "3800", "4200", "--injections", "100", "--hits", "2", "30", "70", "98"],
                ["--charges", "3000", "3400", "3800", "--injections", "100"]),
    "threshold-trim": (["--spread", "1500", "--trim-bits", "4", "--trim-step", "250", "--dac-nonlinearity", "20"],
                       ["--spread", "1500", "--trim-bits", "40", "--trim-step", "250"]),
}


class FrontendResponseContractTests(unittest.TestCase):
    """hep-detector follow-up F-DR1: frontend_response.py has one contracted operation per subcommand, checked
    against each subcommand's own help, and every subcommand behaves as contracted: declared outputs present at exit 0,
    JSON with error_kind invalid-input on stdout at exit 2, JSON with ok false at exit 1."""

    PATH = ROOT / "contracts" / "tool_contracts" / "frontend_response.json"

    def setUp(self):
        self.assertTrue(self.PATH.is_file(), "contracts/tool_contracts/frontend_response.json is missing")
        self.doc = json.loads(self.PATH.read_text(encoding="utf-8"))

    def test_contract_covers_every_subcommand_and_passes(self):
        ops = [o["operation_id"] for o in self.doc["operations"]]
        self.assertEqual(sorted(ops), sorted(FRONTEND_OPS))
        help_text, _ = tc.run_help(ROOT / self.doc["entry"])
        self.assertEqual(tc.subcommands(help_text or ""), set(FRONTEND_OPS))
        res = tc.check(self.doc)
        self.assertEqual(res["status"], "pass", res["findings"])

    def test_a_dropped_option_is_caught_per_subcommand(self):
        doc = copy.deepcopy(self.doc)
        op = next(o for o in doc["operations"] if o["operation_id"] == "sipm")
        op["invocation"]["options"] = [o for o in op["invocation"]["options"] if o["flag"] != "--gate"]
        op["inputs"] = [i for i in op["inputs"] if i["name"] != "gate"]
        self.assertIn("tool.option_undeclared", codes(tc.check(doc)))

    def test_every_operation_behaves_as_contracted(self):
        for op in self.doc["operations"]:
            good, bad = FRONTEND_OPS[op["operation_id"]]
            exits = {f["exit_code"]: f["status"] for f in op["failure_states"]}
            self.assertEqual(exits, {1: "failed", 2: "invalid-input"})
            with self.subTest(operation=op["operation_id"], case="ok"):
                p = run_tool(self.doc["entry"], [op["operation_id"], *good])
                self.assertEqual(p.returncode, 0, p.stderr)
                out = json.loads(p.stdout)
                for o in op["outputs"]:
                    self.assertIn(o["name"], out)
                self.assertEqual(out["status"], "unvalidated")
            with self.subTest(operation=op["operation_id"], case="invalid"):
                p = run_tool(self.doc["entry"], [op["operation_id"], *bad])
                self.assertEqual(p.returncode, 2, p.stdout)
                out = json.loads(p.stdout)
                self.assertEqual((out["status"], out["ok"], out["error_kind"]), ("failed", False, "invalid-input"))

    def test_non_finite_result_exits_1_with_json(self):
        p = run_tool(self.doc["entry"], ["pileup", "--rate", "1e308", "--mean-amp", "1e308", "--peaking", "1e300"])
        self.assertEqual(p.returncode, 1)
        out = json.loads(p.stdout)
        self.assertEqual((out["ok"], out["error_kind"]), (False, "failed"))



class Contract110Tests(unittest.TestCase):
    """Tool contract 1.1.0 (contracts 3.11.0, ART-42, ART-43): positional arguments in the usage line, and the 1.1.0
    features refused in a 1.0.0 contract. The design-block checks are in test_design_contracts.py."""

    def test_usage_positionals(self):
        text = ("usage: toy_spectrometer.py generate [-h] --seed SEED --events-out EVENTS_OUT\n"
                "                                    --periods-out PERIODS_OUT\n                                    config\n\n")
        self.assertEqual(tc.usage_positionals(text, ("toy_spectrometer.py", "generate")), ["config"])
        self.assertEqual(tc.usage_positionals("usage: x.py [-h] --a A [--b B]\n\n", ("x.py",)), [])
        self.assertIsNone(tc.usage_positionals("no usage", ()))

    def test_shipped_1_0_0_contracts_use_no_1_1_0_feature(self):
        for p in sorted(tc.CONTRACT_DIR.glob("*.json")):
            doc = json.loads(p.read_text(encoding="utf-8"))
            if doc["contract_version"] == "1.0.0":
                with self.subTest(contract=p.name):
                    self.assertEqual(tc.uses_1_1(doc), [])


class ForceFieldContractTests(unittest.TestCase):
    """cr-propagation C1 (r3 Q4): the force-field modulation script has a tool contract, called per isotope as a
    subprocess; the contract passes the checker with the help comparison, and the tool behaves as declared."""

    PATH = ROOT / "contracts" / "tool_contracts" / "solar_modulation_force_field.json"

    def test_contract_passes(self):
        doc = json.loads(self.PATH.read_text(encoding="utf-8"))
        result = tc.check(doc)
        self.assertEqual(result["status"], "pass", result["findings"])

    def test_declared_outputs_and_exits(self):
        doc = json.loads(self.PATH.read_text(encoding="utf-8"))
        op = doc["operations"][0]
        cases = (["--modulate", "--energy", "2.0", "--energy-kind", "Ek_per_nucleon", "--mass-number", "12", "--mass",
                  "11.1749", "--charge", "6", "--phi", "0.6", "--lis-normalization", "1e4", "--lis-index", "2.7"],
                 ["--demodulate", "--energy", "5.0", "--energy-kind", "rigidity", "--mass", "0.938272", "--charge",
                  "1", "--phi", "600", "--phi-unit", "MV", "--toa-flux", "12.5"])
        for args in cases:
            with self.subTest(mode=args[0]):
                p = run_tool(doc["entry"], args)
                self.assertEqual(p.returncode, 0, p.stderr)
                out = json.loads(p.stdout)
                for o in op["outputs"]:
                    self.assertIn(o["name"], out)
        p = run_tool(doc["entry"], ["--modulate", "--energy", "nan", "--mass", "1", "--charge", "1", "--phi", "0.5",
                                    "--lis-normalization", "1", "--lis-index", "2"])
        self.assertIn(p.returncode, {f["exit_code"] for f in op["failure_states"]})
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["error_kind"], "invalid-input")


if __name__ == "__main__":
    unittest.main()
