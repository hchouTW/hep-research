"""Adapters and a missing optional dependency (T19): exit 3 with one JSON object whose status is missing-dependency.

The hep-computing script contract (skills/hep-computing/SKILL.md) gives a missing dependency exit 3 and asks scripts to
print JSON with a "status" key. The domain is every adapter command-line tool and every third-party module it imports
(found by reading the source, not from a list), so a new adapter or a new optional import has to be added here. Each
(adapter, module) pair is run with that one module hidden (sys.modules[name] = None makes its import fail), whether or
not it is installed. SYNTHETIC inputs; the run stops at the dependency check, before any input is used."""
import ast
import glob
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PACKAGES = {"core", "contracts", "tests", "adapters", "skills", "profiles", "tools"}
HIDE = ("import runpy, sys; [sys.modules.__setitem__(m, None) for m in sys.argv[1].split(',')]; "
        "sys.argv = sys.argv[2:]; runpy.run_path(sys.argv[0], run_name='__main__')")

UNFOLD_IN = {"response": [[0.8, 0.1], [0.1, 0.8]], "data": [10.0, 12.0]}
# adapter -> (arguments with @TMP for a scratch folder, {file name under @TMP: content}); the hidden module varies
ARGS = {
    "adapters/cr-propagation/assets/dragon2_to_prediction.py": (
        ["--txt", "@TMP/run.txt", "--numerator", "B", "--denominator", "C", "--edges", "1,2", "--out", "@TMP/out"], {}),
    "adapters/hepdata/assets/hepdata_export.py": (
        ["--artifact", "@TMP/record.json", "--out", "@TMP/out", "--engine", "hepdata_lib"], {}),
    "adapters/hepdata/assets/hepdata_record.py": (
        ["--table", "@TMP/table.yaml", "--observable", "@TMP/obs.json", "--record", "ins1", "--table-name", "Table 1",
         "--out", "@TMP/out"], {"table.yaml": "independent_variables: []\n"}),
    "adapters/pyhf-combine/assets/backend_comparison.py": (["--model", "@TMP/model.json"], {}),
    "adapters/pyhf-combine/assets/model_card.py": (["--card", "@TMP/card.json"], {}),
    "adapters/pyhf-combine/assets/pyhf_nuisance_diagnostics.py": (["@TMP/workspace.json"], {}),
    "adapters/pyhf-combine/assets/reproduce_published_likelihood.py": (
        ["--bkgonly", "@TMP/b.json", "--patchset", "@TMP/p.json", "--published", "@TMP/pub.json", "--out", "@TMP/out"],
        {}),
    "adapters/root-uproot/assets/coffea_dijet_processor.py": (["@TMP/events.root"], {}),
    "adapters/root-uproot/assets/pyroot_rdf_cutflow_analysis.py": (
        ["--input", "@TMP/events.root", "--output", "@TMP/out.root"], {}),
    "adapters/root-uproot/assets/pyroot_roofit_signal_background.py": (
        ["--input", "@TMP/hist.root", "--hist", "h", "--output", "@TMP/out.root", "--min", "0", "--max", "1"], {}),
    "adapters/root-uproot/assets/root_to_parquet.py": (["--input", "@TMP/events.root", "--out", "@TMP/out"], {}),
    "adapters/root-uproot/assets/uproot_awkward_analysis.py": (["--config", "@TMP/config.yaml"], {}),
    "adapters/unbinned-fit/assets/unbinned_fit.py": (["fit", "--data", "@TMP/x.json", "--config", "@TMP/c.json"], {}),
}
# unfold.py loads a backend by name: the arguments depend on the hidden module
UNFOLD = "adapters/unfolding/assets/unfold.py"
UNFOLD_BACKEND = {"numpy": "pyunfold", "pyunfold": "pyunfold", "ROOT": "roounfold"}


def adapter_tools():
    return sorted(os.path.relpath(p, ROOT) for p in glob.glob(str(ROOT / "adapters/*/assets/*.py"))
                  if "__main__" in Path(p).read_text(encoding="utf-8"))


def third_party_imports(rel):
    """Top-level names of the modules a tool imports that are neither the standard library nor the plugin's own."""
    path = ROOT / rel
    local = {Path(p).stem for p in glob.glob(str(path.parent / "*.py"))}
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return sorted(n for n in names if n not in sys.stdlib_module_names and n != "__future__"
                  and n not in PLUGIN_PACKAGES and n not in local)


def run_hidden(rel, module):
    with tempfile.TemporaryDirectory() as tmp:
        if rel == UNFOLD:
            src = Path(tmp) / "in.json"
            src.write_text(json.dumps(UNFOLD_IN), encoding="utf-8")
            args = ["unfold", "--input", str(src), "--iterations", "4", "--backend", UNFOLD_BACKEND[module]]
        else:
            args, files = ARGS[rel]
            for name, text in files.items():
                (Path(tmp) / name).write_text(text, encoding="utf-8")
            args = [a.replace("@TMP", tmp) for a in args]
        return subprocess.run([sys.executable, "-I", "-c", HIDE, module, str(ROOT / rel), *args], capture_output=True,
                              text=True, timeout=300, cwd=tmp, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))


class AdapterMissingDependency(unittest.TestCase):
    def test_domain_is_every_adapter_with_a_third_party_import(self):
        found = {rel for rel in adapter_tools() if third_party_imports(rel)}
        self.assertEqual(found, set(ARGS) | {UNFOLD})
        self.assertEqual(set(third_party_imports(UNFOLD)), set(UNFOLD_BACKEND))

    def test_each_hidden_module_gives_exit_3_and_status_missing_dependency(self):
        failures = {}
        pairs = [(rel, m) for rel in sorted(set(ARGS) | {UNFOLD}) for m in third_party_imports(rel)]
        self.assertGreaterEqual(len(pairs), 20)
        for rel, module in pairs:
            with self.subTest(adapter=rel, hidden=module):
                p = run_hidden(rel, module)
                try:
                    doc = json.loads(p.stdout)
                except ValueError:
                    doc = None
                status = doc.get("status") if isinstance(doc, dict) else None
                if (p.returncode, status) != (3, "missing-dependency"):
                    failures[f"{rel} without {module}"] = (p.returncode, status, (p.stdout + p.stderr).strip()[-200:])
        self.assertEqual(failures, {}, json.dumps(failures, indent=1))


if __name__ == "__main__":
    unittest.main()
