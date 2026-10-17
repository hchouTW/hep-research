"""D12: adapters/geomagnetic-backtracing (OTSO, run as a separate program; GPL-3.0, never imported or bundled).

Offline tests use a fake OTSO package on PYTHONPATH; the dipole oracle replays a recorded OTSO 1.3.8 run
(tests/adapters/fixtures/geomagnetic_backtracing/otso_axial_dipole_run.json): in an axial dipole the lowest allowed
vertical rigidity is never below the Stormer vertical cutoff of skills/hep-measurement/scripts/geomagnetic_cutoff.py
(Stormer theory forbids every rigidity below it) and equals it at the equator within 1%. Set HEP_OTSO_PYTHON to an
interpreter with OTSO installed to rerun the oracle live. All inputs are SYNTHETIC."""
import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
ADAPTER = PLUGIN / "adapters" / "geomagnetic-backtracing"
ASSET = ADAPTER / "assets" / "otso_cutoff.py"
FIXTURE = PLUGIN / "tests" / "adapters" / "fixtures" / "geomagnetic_backtracing" / "otso_axial_dipole_run.json"

FAKE_OTSO = '''
class _Table:
    def __init__(self, d):
        self._d = d
    def to_dict(self):
        return self._d

def cutoff(Stations=None, customlocations=None, cutoff_comp="Vertical", **kw):
    import json, os
    log = os.environ.get("FAKE_OTSO_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"cutoff_comp": cutoff_comp, "n": len(customlocations), **kw}) + "\\n")
    table = {}
    for name, lat, lon in customlocations:
        rl = round(10.0 - abs(lat) / 10.0, 2)
        table[name] = {"Ru": rl + 0.3, "Rc": rl + 0.1, "Rl": rl, "PTF": 0.25}
    return [_Table(table), "OTSO Version: 0.0.0-fake\\nCutoff Computed: Vertical Cutoff Rigidity"]
'''


def spec(**over):
    s = {"grid": {"latitudes_deg": [0.0, 30.0], "longitudes_deg": [0.0, 90.0]}, "altitude_km": 20.0,
         "datetime": {"year": 2000, "month": 1, "day": 1, "hour": 0},
         "field": {"internal": "IGRF", "external": "NONE", "magnetopause": "Kobel"},
         "rigidity": {"start_gv": 20.0, "end_gv": 0.0, "step_gv": 0.01},
         "particle": {"atomic_number": 1, "anti": "YES"}, "cutoff": "Vertical"}
    s.update(over)
    return s


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "fake" / "OTSO").mkdir(parents=True)
        (self.d / "fake" / "OTSO" / "__init__.py").write_text(FAKE_OTSO, encoding="utf-8")
        self.env = dict(os.environ, PYTHONPATH=str(self.d / "fake"), PYTHONDONTWRITEBYTECODE="1",
                        FAKE_OTSO_LOG=str(self.d / "calls.log"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_asset(self, *args, env=None):
        p = subprocess.run([sys.executable, "-B", str(ASSET), *map(str, args)], capture_output=True, text=True,
                           timeout=600, env=env or self.env)
        out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {"raw": p.stdout}
        return p.returncode, out

    def write_spec(self, s, name="spec.json"):
        path = self.d / name
        path.write_text(json.dumps(s), encoding="utf-8")
        return path


class Declaration(unittest.TestCase):
    def test_adapter_json_and_licence_boundary(self):
        doc = json.loads((ADAPTER / "adapter.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["id"], "adapter:geomagnetic-backtracing")
        self.assertIn("GPL-3.0", json.dumps(doc))
        self.assertIn("separate", doc["licence_boundary"])

    def test_the_asset_never_imports_otso(self):
        tree = ast.parse(ASSET.read_text(encoding="utf-8"))
        names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        names += [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module]
        self.assertFalse([m for m in names if m.split(".")[0] == "OTSO"], names)


class RunAndPartition(_Base):
    def test_missing_otso_exits_3_with_a_hint(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        code, out = self.run_asset("run", "--spec", self.write_spec(spec()), "--otso-python", sys.executable,
                                   "--out", self.d / "o.json", env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "missing-dependency")
        self.assertIn("pip install otso", out["install"])
        self.assertIn("GPL-3.0", out["install"])

    def test_bad_specs_are_rejected(self):
        for bad in (spec(field={"internal": "IGRF"}), spec(rigidity={"start_gv": 0.0, "end_gv": 20.0, "step_gv": 0.01}),
                    spec(otso_params={"data_retrieval_params": {"serverdata": "ON"}}), {"altitude_km": 20.0}):
            with self.subTest(bad=bad):
                code, out = self.run_asset("run", "--spec", self.write_spec(bad), "--otso-python", sys.executable,
                                           "--out", self.d / "o.json")
                self.assertEqual(code, 2)
                self.assertEqual(out["status"], "rejected")

    def test_run_writes_a_labelled_grid_with_penumbra(self):
        code, out = self.run_asset("run", "--spec", self.write_spec(spec()), "--otso-python", sys.executable,
                                   "--out", self.d / "o.json")
        self.assertEqual(code, 0, out)
        doc = json.loads((self.d / "o.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(doc["status_label"], "unvalidated")
        self.assertIn("not any experiment's official cutoff", doc["label"])
        self.assertEqual(doc["tool"]["version"], "0.0.0-fake")
        self.assertEqual(doc["field_model"]["internal"], "IGRF")
        self.assertEqual(len(doc["records"]), 4)
        r = doc["records"][0]
        self.assertAlmostEqual(r["penumbra_width_gv"], r["Ru_gv"] - r["Rl_gv"], places=12)
        self.assertIn("cores", doc["defaults_used"])
        call = json.loads((self.d / "calls.log").read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(call["magfield_params"]["externalmag"], "NONE")
        self.assertEqual(call["integration_params"]["startaltitude"], 20.0)

    def test_chunks_merged_equal_one_run(self):
        sp = self.write_spec(spec())
        self.run_asset("run", "--spec", sp, "--otso-python", sys.executable, "--out", self.d / "all.json")
        self.run_asset("run", "--spec", sp, "--otso-python", sys.executable, "--start", 0, "--stop", 3,
                       "--out", self.d / "a.json")
        self.run_asset("run", "--spec", sp, "--otso-python", sys.executable, "--start", 3, "--stop", 4,
                       "--out", self.d / "b.json")
        code, out = self.run_asset("merge", self.d / "b.json", self.d / "a.json", "--out", self.d / "m.json")
        self.assertEqual(code, 0, out)
        merged = json.loads((self.d / "m.json").read_text(encoding="utf-8"))
        single = json.loads((self.d / "all.json").read_text(encoding="utf-8"))
        self.assertEqual(merged["records"], single["records"])
        self.assertTrue(merged["complete"])

    def test_merge_refuses_duplicates_and_other_specs(self):
        sp = self.write_spec(spec())
        sp2 = self.write_spec(spec(altitude_km=30.0), "spec2.json")
        self.run_asset("run", "--spec", sp, "--otso-python", sys.executable, "--start", 0, "--stop", 2,
                       "--out", self.d / "a.json")
        self.run_asset("run", "--spec", sp2, "--otso-python", sys.executable, "--start", 2, "--stop", 4,
                       "--out", self.d / "b.json")
        code, out = self.run_asset("merge", self.d / "a.json", self.d / "a.json", "--out", self.d / "m.json")
        self.assertEqual(code, 2)
        code, out = self.run_asset("merge", self.d / "a.json", self.d / "b.json", "--out", self.d / "m.json")
        self.assertEqual(code, 2)


class DipoleOracle(_Base):
    def test_recorded_otso_run_respects_the_stormer_bound(self):
        code, out = self.run_asset("dipole-check", "--replay", FIXTURE)
        self.assertEqual(code, 0, out)
        rows = {r["latitude_deg"]: r for r in out["comparison"]}
        for r in rows.values():
            self.assertGreaterEqual(r["Rl_gv"], r["stormer_gv"] * (1 - 0.01))
        self.assertLess(abs(rows[0.0]["Rc_gv"] / rows[0.0]["stormer_gv"] - 1), 0.01)
        self.assertEqual(out["tool"]["version"], "1.3.8")

    def test_a_cutoff_below_stormer_fails(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for loc in raw["otso"]["table"].values():
            loc["Rl"] = loc["Rl"] * 0.8
            loc["Rc"] = loc["Rc"] * 0.8
        bad = self.d / "bad.json"
        bad.write_text(json.dumps(raw), encoding="utf-8")
        code, out = self.run_asset("dipole-check", "--replay", bad)
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "failed")

    @unittest.skipUnless(os.environ.get("HEP_OTSO_PYTHON"), "set HEP_OTSO_PYTHON to an interpreter with OTSO installed")
    def test_live_otso_dipole(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        code, out = self.run_asset("dipole-check", "--otso-python", os.environ["HEP_OTSO_PYTHON"], "--g10-nt", "-30000",
                                   "--latitudes", "0", "20", "40", "60", "--altitude-km", "20", env=env)
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
