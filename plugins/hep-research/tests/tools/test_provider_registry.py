"""tools/provider_registry.py: the cr-provider/1 registry is generated from the 'provider' fields of adapter.json and
profile.json plus explicit user-supplied declarations, written outside the plugin, and refuses bad declarations,
duplicate ids, entrypoints outside their folder and links."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.provider.registry import load_registry  # noqa: E402
from tools.provider_registry import declaring_files  # noqa: E402

TOOL = ROOT / "tools" / "provider_registry.py"


def run(*argv):
    proc = subprocess.run([sys.executable, "-I", str(TOOL), *map(str, argv)], capture_output=True, text=True,
                          timeout=120, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else {}, proc.stderr


def declared_ids() -> set[str]:
    ids = set()
    for _, manifest in declaring_files(ROOT):
        field = manifest.get("provider")
        if field is not None:
            ids |= {d["id"] for d in (field if isinstance(field, list) else [field])}
    return ids


class ProviderRegistryTests(unittest.TestCase):
    def setUp(self):
        self._workdir = tempfile.TemporaryDirectory()
        self.scratch = Path(self._workdir.name)

    def tearDown(self):
        self._workdir.cleanup()

    def user_declaration(self, name="mine", **changes) -> Path:
        folder = self.scratch / name
        folder.mkdir(exist_ok=True)
        (folder / "entry.py").write_text("print('provider')\n", encoding="utf-8")
        decl = {"id": f"user-{name}", "entrypoint": "entry.py", "protocol": "cr-provider/1", "version": "0.0.1",
                "domain": {"L_kpc": {"min": 1, "max": 10}}, "observables": ["B/C"], "axes": ["ekn"],
                "decomposable": False, "deterministic": True, "output_units": {"ratio": "1"}}
        decl.update(changes)
        path = folder / "declaration.json"
        path.write_text(json.dumps(decl), encoding="utf-8")
        return path

    def test_write_lists_every_declared_provider(self):
        code, out, err = run("--write", self.scratch / "registry.json")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "written")
        entries = load_registry(self.scratch / "registry.json")
        self.assertEqual(set(entries), declared_ids())
        self.assertIn("cr-secondary-ratio-closed-form", entries)
        for entry in entries.values():
            self.assertTrue(entry.entrypoint.is_absolute() and entry.entrypoint.is_file())
            self.assertFalse(entry.user_supplied)

    def test_check_writes_nothing(self):
        code, out, _ = run("--check")
        self.assertEqual((code, out["status"]), (0, "ok"))

    def test_registry_is_never_written_inside_the_plugin(self):
        code, out, _ = run("--write", ROOT / "registry.json")
        self.assertEqual((code, out["status"]), (2, "rejected"))
        self.assertFalse((ROOT / "registry.json").exists())

    def test_user_supplied_provider_is_listed_explicitly(self):
        code, out, err = run("--write", self.scratch / "registry.json", "--user-provider", self.user_declaration())
        self.assertEqual(code, 0, err)
        entries = load_registry(self.scratch / "registry.json")
        self.assertTrue(entries["user-mine"].user_supplied)
        self.assertEqual(entries["user-mine"].component, "user-supplied:declaration.json")

    def test_refusals(self):
        cases = {
            "no version": self.user_declaration("nov", version=None),
            "bad protocol": self.user_declaration("proto", protocol="cr-provider/9"),
            "leaves folder": self.user_declaration("up", entrypoint="../mine/entry.py"),
            "missing entry": self.user_declaration("gone", entrypoint="absent.py"),
            "duplicate id": self.user_declaration("dup", id="cr-secondary-ratio-closed-form"),
        }
        # a declaration with version null: drop the key instead
        decl = json.loads(cases["no version"].read_text())
        decl.pop("version")
        cases["no version"].write_text(json.dumps(decl))
        link = self.user_declaration("link", entrypoint="linked.py")
        os.symlink(link.parent / "entry.py", link.parent / "linked.py")
        cases["link"] = link
        for name, path in cases.items():
            with self.subTest(case=name):
                code, out, _ = run("--write", self.scratch / "registry.json", "--user-provider", path)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")
                self.assertTrue(out["problems"])

    def test_help(self):
        proc = subprocess.run([sys.executable, "-I", str(TOOL), "--help"], capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--user-provider", proc.stdout)


F1_TABLES = ROOT / "tests" / "adapters" / "fixtures" / "cr_propagation" / "f1" / "force-field"


def _usine_reader():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "usine_to_prediction_k2", ROOT / "adapters" / "cr-propagation" / "assets" / "usine_to_prediction.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def recorded_usine_hook(scale_toa: float = 1.0):
    """isotope_tables replayed from USINE's recorded F1 tables (11B, 12C; LIS and SolMod0DFF at phi = 0.7312345 GV),
    the modulated fluxes optionally scaled (a provider that disagrees with the force-field tool)."""
    reader = _usine_reader()

    def hook(request, point):
        phi = point.get("phi_2011_2016_gv", 0.0)
        tables = reader.read_run(F1_TABLES, "Model1DKisoVc", ["11B", "12C"], phi)
        return {"phi_gv": phi, "isotopes": {
            nuc: {"charge": z, "mass_number": a, "ekn": list(tables[nuc][0]),
                  "flux": [f * (scale_toa if phi else 1.0) for f in tables[nuc][1]]}
            for nuc, (z, a) in (("11B", (5, 11)), ("12C", (6, 12)))}}
    return hook


class ModulationConformance(unittest.TestCase):
    """K2-2: the conformance gate of a declared modulation (--conformance): USINE's recorded SolMod0DFF tables agree
    with the plugin's force-field tool applied to USINE's own LIS within 1e-3; a provider off by 0.2% fails; the gate
    refuses a provider without a modulation block, a looser tolerance and a reference point without its potential."""

    POINT = {"D0_cm2_s": 3.0e28, "delta": 0.5, "L_kpc": 4.0, "phi_2011_2016_gv": 0.7312345}

    def test_usine_declares_a_passing_result(self):
        from core.provider.protocol import check_declaration
        decl = next(d for path, m in declaring_files(ROOT) for d in (m.get("provider") or [])
                    if isinstance(d, dict) and d.get("id") == "usine")
        self.assertEqual(check_declaration(decl), [])
        conf = decl["modulation"]["conformance"]
        self.assertEqual(conf["result"]["status"], "passed")
        self.assertLessEqual(conf["tolerance"], 1e-3)
        self.assertLessEqual(conf["result"]["max_relative_deviation"], conf["tolerance"])
        self.assertEqual(decl["modulation"]["parameters"], ["phi_2011_2016_gv"])
        # L2-1: the result was obtained at the provider's current version (the gate rerun at 0.3.0)
        self.assertEqual(conf["result"]["provider_version"], decl["version"])
        self.assertEqual(check_declaration(decl, decl["version"]), [])

    def test_a_result_of_another_version_is_refused(self):
        """L2-1: a provider version bumped without rerunning the gate is refused when the registry is built (the
        declaration's version, or the adapter's version it defaults to), with the instruction to rerun the gate."""
        import copy

        from tools.provider_registry import collect
        path, manifest = next((p, m) for p, m in declaring_files(ROOT)
                              if any(isinstance(d, dict) and d.get("id") == "usine" for d in m.get("provider") or []))
        field = copy.deepcopy(manifest["provider"])
        usine = next(d for d in field if d["id"] == "usine")
        items, problems = collect([usine], path.parent, "cr-propagation", manifest["version"], False, "adapter.json")
        self.assertEqual((len(items), problems), (1, []))
        bumped = dict(usine, version="9.9.9")
        items, problems = collect([bumped], path.parent, "cr-propagation", manifest["version"], False, "adapter.json")
        self.assertEqual(items, [])
        self.assertTrue(any("differs from the provider version '9.9.9'" in p and "rerun" in p for p in problems),
                        problems)
        inherited = {k: v for k, v in usine.items() if k != "version"}       # the adapter's version applies
        items, problems = collect([inherited], path.parent, "cr-propagation", "9.9.9", False, "adapter.json")
        self.assertEqual(items, [])
        self.assertTrue(any("'9.9.9'" in p for p in problems), problems)

    def test_gate_on_recorded_usine_tables(self):
        from tools.provider_registry import modulation_conformance
        out = modulation_conformance("usine", self.POINT, hook=recorded_usine_hook())
        result = out["conformance"]["result"]
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual(result["isotopes"], ["11B", "12C"])
        self.assertGreater(result["nodes_compared"], 100)
        self.assertLess(result["max_relative_deviation"], 1e-4)   # USINE's 6-digit tables and masses
        self.assertEqual(result["provider_version"], out["provider_version"])   # L2-1: the version the gate ran at
        from tools.provider_registry import find_declaration
        self.assertEqual(out["provider_version"], find_declaration("usine")[2])
        bad = modulation_conformance("usine", self.POINT, hook=recorded_usine_hook(1.002))["conformance"]["result"]
        self.assertEqual(bad["status"], "failed")
        self.assertGreater(bad["max_relative_deviation"], 1e-3)

    def test_gate_refusals(self):
        from tools.provider_registry import ConformanceError, modulation_conformance
        hook = recorded_usine_hook()
        for args in (("dragon2", self.POINT, None, None), ("usine", self.POINT, None, 2e-3),
                     ("usine", {"delta": 0.5}, None, None), ("nope", self.POINT, None, None)):
            with self.subTest(args=args[0:1] + args[2:]), self.assertRaises(ConformanceError):
                modulation_conformance(args[0], args[1], args[2], args[3], hook=hook)

    def test_cli_rejects_a_provider_without_the_block(self):
        code, out, _ = run("--conformance", "dragon2")
        self.assertEqual(code, 2, out)
        self.assertIn("no modulation block", out["error"])


if __name__ == "__main__":
    unittest.main()
