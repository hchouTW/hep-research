"""WP1: adapters/geant4 (Geant4 11.4.3 build, official examples, layered_sim runs, implementation checks, oracle).

Offline tests use a fake layered_sim executable (a Python script with the same file interface) and replay recorded real
runs from tests/adapters/fixtures/geant4/ (Geant4 11.4.3 on E2, 2026-10-21: the build records, excerpts of local
example outputs, layered_sim runs of the checks and the mirrors, paths written as ~ or <plugin root>). No test links,
imports or needs Geant4. Set HEP_GEANT4_LIVE_TEST=1 and HEP_GEANT4_CONFIG (a JSON {"build_record", "layered_sim"})
to rerun the live tests. All geometries are invented (SYNTHETIC) except the two example mirrors."""
import ast
import gzip
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
ADAPTER = PLUGIN / "adapters" / "geant4"
ASSETS = ADAPTER / "assets"
FIX = PLUGIN / "tests" / "adapters" / "fixtures" / "geant4"
J14 = PLUGIN / "examples" / "geant4-thin-silicon"
sys.path.insert(0, str(PLUGIN))
from contracts.validate import validate_artifact  # noqa: E402

LIVE = os.environ.get("HEP_GEANT4_LIVE_TEST") == "1" and os.environ.get("HEP_GEANT4_CONFIG")

FAKE_SIM = r'''#!/usr/bin/env python3
"""Fake layered_sim: the real program's file interface with deterministic invented events (no Geant4)."""
import json, os, sys
DATA_VARS = ("G4NEUTRONHPDATA", "G4LEDATA", "G4LEVELGAMMADATA", "G4RADIOACTIVEDATA", "G4PARTICLEXSDATA", "G4PIIDATA",
             "G4REALSURFACEDATA", "G4SAIDXSDATA", "G4ABLADATA", "G4INCLDATA", "G4ENSDFSTATEDATA", "G4CHANNELINGDATA",
             "G4PARTICLEHPDATA", "G4NUDEXLIBDATA", "G4URRPTDATA", "GEANT4_DATA_DIR")
spec = json.load(open(sys.argv[1]))
if any(c.startswith("/fake/refuse") for c in spec.get("ui_commands", [])):
    print('LAYERED_SIM_STATUS {"status": "rejected", "error": "UI command refused"}')
    sys.exit(2)
slabs = []
for layer in spec["geometry"]["layers"]:
    for s in layer["slabs"]:
        if s["name"] not in slabs:
            slabs.append(s["name"])
cols = ["event", "chunk", "weight", "primary_pdg", "primary_ekin_MeV", "primary_x_mm", "primary_y_mm", "primary_z_mm",
        "primary_dx", "primary_dy", "primary_dz"]
for n in slabs:
    cols += [f"edep_{n}_MeV", f"chlen_{n}_mm", f"plen_{n}_mm"]
cols += ["edep_world_MeV", "leak_gamma_MeV", "leak_e_MeV", "leak_nu_MeV", "leak_other_MeV", "killed_booked_MeV",
         "killed_unbooked_MeV", "killed_eplus", "exit_ekin_MeV", "primary_eloss_MeV", "exit_dx", "exit_dy", "exit_dz",
         "primary_fate", "primary_end_x_mm", "primary_end_process", "n_sec_gamma", "n_sec_electron", "n_sec_positron",
         "n_sec_other"]
e0 = spec["gun"]["energy_MeV"]
first, n = spec["run"].get("first_event", 0), spec["run"]["events"]
with open(spec["output"]["csv"], "w") as fh:
    fh.write("# SIMULATION\n" + ",".join(cols) + "\n")
    for ev in range(first, first + n):
        dep = 0.001 * (1 + (ev * 7919) % 13) / len(slabs)
        row = [ev, spec["run"].get("chunk", 0), 1, 13, e0, -1, 0, 0, 1, 0, 0]
        for _ in slabs:
            row += [dep, 0.3, 0.3]
        loss = dep * len(slabs)
        row += [0, 0, 0, 0, e0 - loss, 0, 0, 0, e0 - loss, loss, 1, 0, 0, 1, 0.15, "Transportation", 0, 0, 0, 0]
        fh.write(",".join(map(str, row)) + "\n")
json.dump({"materials": [{"name": "G4_Si", "density_g_cm3": 2.33, "radiation_length_cm": 9.37,
                          "nuclear_interaction_length_cm": 46.5, "mean_excitation_energy_eV": 173.0}]},
          open(spec["output"]["materials"], "w"))
json.dump({"geant4_version": "fake", "before_initialization": {},
           "after_run": {k: os.environ[k] for k in DATA_VARS if k in os.environ}}, open(spec["output"]["datapaths"], "w"))
print("LAYERED_SIM_STATUS {\"status\": \"ok\"}")
'''


def run(script, *args, env=None, cwd=None, timeout=600):
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True,
                       timeout=timeout, env=env, cwd=cwd)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = {"raw": p.stdout[-500:], "stderr": p.stderr[-500:]}
    return p.returncode, out


def asset(name):
    return ASSETS / name


def tree_hash(root):
    sys.path.insert(0, str(ASSETS))
    import geant4_build
    return geant4_build.tree_hash(Path(root))


class _Tmp(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def write(self, name, doc):
        p = self.d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
        return p

    def fake_install(self):
        """A fake installation and its build record (one dataset, a geant4-config that prints 11.4.3)."""
        if getattr(self, "_install", None):
            return self._install
        inst = self.d / "install"
        ds = inst / "share" / "Geant4" / "data" / "G4EMLOW8.8"
        ds.mkdir(parents=True)
        (ds / "table.dat").write_text("fake data\n")
        (inst / "bin").mkdir()
        cfg = inst / "bin" / "geant4-config"
        cfg.write_text("#!/bin/sh\necho 11.4.3\n")
        cfg.chmod(cfg.stat().st_mode | stat.S_IEXEC)
        digest, n = tree_hash(ds)
        rec = json.loads((FIX / "records" / "geant4-build.computational-run.json").read_text(encoding="utf-8"))
        rec["extension"]["build"].update(install_prefix=str(inst), datasets=[
            {"name": "G4EMLOW", "version": "8.8", "envvar": "G4LEDATA", "path": str(ds), "content_sha256": digest,
             "n_files": n, "md5_verified": True}])
        rec["extension"]["build"]["geant4_config"]["version"] = "11.4.3"
        self._install = (self.write("build.json", rec), ds)
        return self._install

    def fake_exe(self):
        exe = self.d / "fake_layered_sim"
        exe.write_text(f"#!{sys.executable}\n" + FAKE_SIM.split("\n", 1)[1])
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
        return exe


def spec(**over):
    s = json.loads((FIX / "specs" / "overlap_shifted_slab.json").read_text(encoding="utf-8"))
    s["geometry"]["layers"][0]["slabs"][1].pop("shift_mm")
    s["note"] = "SYNTHETIC test spec"
    s["run"]["events"] = 40
    for k, v in over.items():
        s[k] = v
    return s


class Declaration(unittest.TestCase):
    def test_adapter_json_and_licence_boundary(self):
        doc = json.loads((ADAPTER / "adapter.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["id"], "adapter:geant4")
        self.assertEqual(doc["owner_skill"], "hep-detector")
        lb = doc["licence_boundary"]
        for phrase in ("Geant4 Software License, Version 1.0, 28 June 2006", "Apache-2.0", "Nothing of Geant4 is bundled",
                       "separate executable", "JSON and CSV", "G5"):
            self.assertIn(phrase, lb)
        listed = set(doc["assets"])
        for src in ("CMakeLists.txt", "MiniJson.hh", "Spec.cc", "Detector.cc", "Physics.cc", "Actions.cc",
                    "layered_sim.cc", "spec.schema.json", "output.schema.json"):
            self.assertIn(f"assets/layered_sim/{src}", listed)

    def test_adapter_python_imports_no_skill_script_and_no_geant4(self):
        for py in ASSETS.glob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            mods = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
            mods += [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module]
            with self.subTest(script=py.name):
                self.assertFalse([m for m in mods if m.split(".")[0] in ("skills", "geant4_benchmarks",
                                                                         "check_geant4_study", "geant4_pybind")], mods)

    def test_ui_commands_are_applied_after_the_physics_list_and_before_initialize(self):
        src = (ASSETS / "layered_sim" / "layered_sim.cc").read_text(encoding="utf-8")
        i_phys = src.index("rm->SetUserInitialization(phys)")
        i_ui = src.index("ui->ApplyCommand(cmd)")
        i_init = src.index('ui->ApplyCommand("/run/initialize")')
        self.assertLess(i_phys, i_ui)
        self.assertLess(i_ui, i_init)

    def test_no_replicas_and_every_slab_checked_for_overlaps(self):
        det = (ASSETS / "layered_sim" / "Detector.cc").read_text(encoding="utf-8")
        self.assertNotIn("G4PVReplica", det)
        self.assertIn("false, fPlacements, true);", det)  # pSurfChk on for every slab placement


class Build(_Tmp):
    def good(self):
        return json.loads(asset("build_spec.example.json").read_text(encoding="utf-8"))

    def test_bad_build_specs_are_rejected(self):
        bads = []
        for path, value in (("geant4.commit", "2ee379e6"), ("cmake_options.CMAKE_CXX_STANDARD", "14"),
                            ("cmake_options.GEANT4_INSTALL_DATA", "ON"), ("datasets.source", "ftp")):
            s = self.good()
            k1, k2 = path.split(".")
            s[k1][k2] = value
            bads.append(s)
        for bad in bads:
            with self.subTest(bad=bad):
                code, out = run(asset("geant4_build.py"), "build", "--spec", self.write("b.json", bad), "--work",
                                self.d / "w", "--record", self.d / "r.json")
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")

    def test_missing_git_exits_3(self):
        env = dict(os.environ, PATH=str(self.d / "empty"))
        code, out = run(asset("geant4_build.py"), "build", "--spec", asset("build_spec.example.json"), "--work",
                        self.d / "w", "--record", self.d / "r.json", env=env)
        self.assertEqual(code, 3, out)
        self.assertEqual(out["status"], "missing-dependency")

    def test_dataset_definitions_and_content_hash(self):
        sys.path.insert(0, str(ASSETS))
        import geant4_build
        src = self.d / "src" / "cmake" / "Modules"
        src.mkdir(parents=True)
        (src / "G4DatasetDefinitions.cmake").write_text(
            "geant4_add_dataset(\n  NAME      G4EMLOW\n  VERSION   8.8\n  FILENAME  G4EMLOW\n  EXTENSION tar.gz\n"
            "  ENVVAR    G4LEDATA\n  MD5SUM    0123456789abcdef0123456789abcdef\n  )\n")
        defs = geant4_build.dataset_definitions(self.d / "src")
        self.assertEqual(defs["G4EMLOW"]["envvar"], "G4LEDATA")
        self.assertEqual(defs["G4EMLOW"]["md5"], "0123456789abcdef0123456789abcdef")
        a = self.d / "a"
        a.mkdir()
        (a / "x").write_text("1")
        h1 = geant4_build.tree_hash(a)
        (a / "x").write_text("2")
        self.assertNotEqual(h1, geant4_build.tree_hash(a))

    def test_check_finds_a_changed_dataset(self):
        rec, ds = self.fake_install()
        code, out = run(asset("geant4_build.py"), "check", "--record", rec)
        self.assertEqual(code, 0, out)
        (ds / "table.dat").write_text("another copy\n")
        code, out = run(asset("geant4_build.py"), "check", "--record", rec)
        self.assertEqual(code, 1, out)
        self.assertTrue(out["differences"])

    def test_recorded_builds_match_and_validate(self):
        a = json.loads((FIX / "records" / "geant4-build.computational-run.json").read_text(encoding="utf-8"))
        b = json.loads((FIX / "records" / "geant4-build-clean-rebuild.computational-run.json").read_text(encoding="utf-8"))
        for rec in (a, b):
            self.assertTrue(validate_artifact(rec).ok)
            bd = rec["extension"]["build"]
            self.assertEqual(bd["commit"], "2ee379e6843e55b9c6bbb835d2a2b03cc998fef0")
            self.assertEqual(bd["geant4_config"]["version"], "11.4.3")
            self.assertEqual(bd["cmake_cxx_standard"], "17")
            self.assertTrue(all(d["md5_verified"] and d["n_files"] > 0 for d in bd["datasets"]))
            self.assertIn("information only", bd["geant4_config"]["check_datasets_note"])
            self.assertEqual(rec["status"], ["unvalidated"])
        self.assertEqual([d["content_sha256"] for d in a["extension"]["build"]["datasets"]],
                         [d["content_sha256"] for d in b["extension"]["build"]["datasets"]])
        self.assertNotIn("/" + "Users/", json.dumps(a) + json.dumps(b))  # split: the packaging scan reads this file


class Examples(_Tmp):
    def source_tree(self, overrides=None):
        """A fake Geant4 source tree whose reference outputs are the recorded local excerpts."""
        sys.path.insert(0, str(ASSETS))
        import geant4_examples as E
        src = self.d / "src"
        for name in ("B1", "B4a", "TestEm3", "TestEm5"):
            folder, *_rest = E.EXAMPLES[name]
            ref = src / "examples" / folder / E.EXAMPLES[name][3]
            ref.parent.mkdir(parents=True, exist_ok=True)
            text = (FIX / "out" / f"{name}-local.out").read_text(encoding="utf-8")
            for a, b in (overrides or {}).get(name, []):
                text = text.replace(a, b)
            ref.write_text(text, encoding="utf-8")
        return src

    def test_extractors_tag_run_ids_and_both_b1_formats(self):
        code, out = run(asset("geant4_examples.py"), "extract", "--example", "TestEm5", "--out-file",
                        FIX / "out" / "TestEm5-local.out")
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted({q["run"] for q in out["quantities"]}), [0, 1, 2, 3, 4])
        text = (FIX / "out" / "B1-local.out").read_text(encoding="utf-8")
        self.assertIn("; rms =", text)
        ref_style = self.write("b1.out", text.replace("; rms =", "  rms ="))
        a = run(asset("geant4_examples.py"), "extract", "--example", "B1", "--out-file", FIX / "out" / "B1-local.out")[1]
        b = run(asset("geant4_examples.py"), "extract", "--example", "B1", "--out-file", ref_style)[1]
        self.assertEqual([q["value"] for q in a["quantities"]], [q["value"] for q in b["quantities"]])
        self.assertEqual(len(a["quantities"]), 2)

    def test_testem3_meanings(self):
        q = {(r["run"], r["quantity"]): r for r in run(asset("geant4_examples.py"), "extract", "--example", "TestEm3",
                                                       "--out-file", FIX / "out" / "TestEm3-local.out")[1]["quantities"]}
        self.assertFalse(q[(0, "eleak_MeV")]["compared"])  # anti-correlated with edep_total
        self.assertFalse(q[(1, "edep_total_MeV")]["compared"])  # biased run
        self.assertIn("not a standard error", q[(0, "resolution_G4_Pb_percent")]["se_formula"])
        rms = q[(0, "edep_rms_G4_Pb_MeV")]["value"]
        self.assertGreater(q[(0, "edep_G4_Pb_MeV")]["se"], rms / 10 * 0.99)  # RMS/sqrt(100) plus rounding

    def test_compare_passes_identical_and_flags_a_shift_then_pools_a_rerun(self):
        src = self.source_tree()
        local = FIX / "out" / "TestEm5-local.out"
        code, out = run(asset("geant4_examples.py"), "compare", "--source", src, "--local", f"TestEm5={local}")
        self.assertEqual(code, 0, out)
        self.assertTrue(all(abs(r["z"]) < 1e-9 for r in out["examples"]["TestEm5"]["rows"]))
        shifted = self.write("em5.out", local.read_text(encoding="utf-8").replace("6.348 keV", "6.548 keV"))
        code, out = run(asset("geant4_examples.py"), "compare", "--source", src, "--local", f"TestEm5={shifted}")
        self.assertEqual(code, 1, out)
        self.assertEqual(out["status"], "rerun-required")
        code, out = run(asset("geant4_examples.py"), "compare", "--source", src, "--local",
                        f"TestEm5={shifted},{local}")
        row = next(r for r in out["examples"]["TestEm5"]["rows"] if r["run"] == 0 and r["quantity"] == "edep_MeV")
        self.assertEqual(row["pooled"]["runs"], 2)  # pooled with the rerun, never replaced by it

    def test_b4a_smoke(self):
        src = self.source_tree()
        code, out = run(asset("geant4_examples.py"), "smoke", "--source", src, "--local", FIX / "out" / "B4a-local.out")
        self.assertEqual(code, 0, out)
        src = self.source_tree({"B4a": [("G4_Pb", "G4_Fe")]})
        code, out = run(asset("geant4_examples.py"), "smoke", "--source", src, "--local", FIX / "out" / "B4a-local.out")
        self.assertEqual(code, 1, out)
        self.assertFalse(out["checks"]["material_table_matches"])

    def test_recorded_comparison_table(self):
        t = json.loads((FIX / "records" / "examples-compare-s1.json").read_text(encoding="utf-8"))
        self.assertEqual(t["status"], "ok")
        self.assertEqual(t["m_compared"], 48)
        self.assertAlmostEqual(t["z_crit"], 3.2790243, places=6)
        for name, ex in t["examples"].items():
            for r in ex["rows"]:
                with self.subTest(example=name, run=r["run"], q=r["quantity"]):
                    self.assertIn("run", r)
                    self.assertTrue(r["se_formula"])
                    self.assertLessEqual(abs(r["z"]), t["z_crit"])
                    self.assertEqual(r["verdict"], "pass")


class RunAndPartition(_Tmp):
    def go(self, s, *extra, env=None, run_id="r1"):
        rec, _ = self.fake_install()
        sp = self.write(f"{run_id}.spec.json", s)
        return run(asset("geant4_run.py"), "run", "--spec", sp, "--exe", self.fake_exe(), "--build-record", rec,
                   "--work", self.d / "work", "--run-id", run_id, "--record", self.d / "art" / f"{run_id}.json",
                   "--created", "2026-10-21", *extra, env=env)

    def test_missing_executable_exits_3(self):
        rec, _ = self.fake_install()
        code, out = run(asset("geant4_run.py"), "run", "--spec", self.write("s.json", spec()), "--exe",
                        self.d / "none", "--build-record", rec, "--work", self.d / "w", "--run-id", "r", "--record",
                        self.d / "r.json")
        self.assertEqual(code, 3, out)
        self.assertEqual(out["status"], "missing-dependency")

    def test_bad_specs_are_rejected(self):
        bads = [spec(ui_commands=["/run/beamOn 10"]), spec(gun={"particle": "e-", "energy_MeV": -1}),
                spec(physics={"default_cut_mm": 1.0, "em_constructor": "G4EmStandardPhysics",
                              "reference_list": "FTFP_BERT"}),
                spec(unknown_key=1), spec(run={"events": 0, "seeds": [1, 2]})]
        for k, bad in enumerate(bads):
            with self.subTest(k=k):
                code, out = self.go(bad, run_id=f"bad{k}")
                self.assertEqual(code, 2, out)

    def test_run_writes_a_valid_unvalidated_record_with_a_simulation_block(self):
        code, out = self.go(spec(ui_commands=["/process/msc/Skin 1"]))
        self.assertEqual(code, 0, out)
        rec = json.loads((self.d / "art" / "r1.json").read_text(encoding="utf-8"))
        self.assertTrue(validate_artifact(rec).ok, validate_artifact(rec).as_dict())
        self.assertEqual(rec["status"], ["unvalidated"])
        self.assertEqual(rec["provenance"]["producer_skill"], "hep-detector")
        sim = rec["extension"]["simulation"]
        for k in ("geant4", "datasets", "physics", "ui_commands", "cuts", "step_limits", "spec_sha256",
                  "material_dump_sha256", "random", "events", "run_manager", "threads"):
            self.assertIn(k, sim)
        self.assertEqual(sim["ui_commands"], ["/process/msc/Skin 1"])
        self.assertTrue(all(d["path_match"] and d["content_match"] for d in sim["datasets"]))
        csv = (self.d / "work" / "r1" / "events.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(csv[0], "# SIMULATION")
        eff = json.loads((self.d / "work" / "r1" / "spec.json").read_text(encoding="utf-8"))
        self.assertEqual(eff["output"]["csv"], "events.csv")  # no absolute path in the effective spec

    def test_another_copy_of_the_data_fails_the_run(self):
        other = self.d / "copy" / "G4EMLOW8.8"
        other.mkdir(parents=True)
        (other / "table.dat").write_text("fake data\n")
        code, out = self.go(spec(), "--data-override", f"G4LEDATA={other}")
        self.assertEqual(code, 1, out)
        rec = json.loads((self.d / "art" / "r1.json").read_text(encoding="utf-8"))
        self.assertIn("failed", rec["status"])
        self.assertTrue(rec["extension"]["simulation"]["data_path_problems"])

    def test_a_refusal_by_the_program_writes_no_record(self):
        code, out = self.go(spec(ui_commands=["/fake/refuse"]))
        self.assertEqual(code, 2, out)
        self.assertFalse((self.d / "art" / "r1.json").exists())

    def test_scan_writes_a_workflow_that_run_workflow_runs(self):
        rec, _ = self.fake_install()
        base = self.write("base.json", spec())
        grid = self.write("grid.json", {"name": "cuts", "parameters": {"physics.default_cut_mm": [1.0, 0.1]}})
        code, out = run(asset("geant4_run.py"), "scan", "--base", base, "--grid", grid, "--exe", self.fake_exe(),
                        "--build-record", rec, "--out-dir", self.d / "scan", "--events-per-second", "1000",
                        "--created", "2026-10-21")
        self.assertEqual(code, 0, out)
        code, out = run(PLUGIN / "skills" / "hep-computing" / "scripts" / "run_workflow.py",
                        self.d / "scan" / "workflow.json", "--work", self.d / "scan", "--created", "2026-10-21")
        self.assertEqual(code, 0, out)
        for sid in ("cuts-000", "cuts-001"):
            self.assertTrue((self.d / "scan" / "runs" / f"{sid}.computational-run.json").is_file())  # orchestration
            g4 = json.loads((self.d / "scan" / "records" / f"{sid}.computational-run.json").read_text(encoding="utf-8"))
            self.assertIn("simulation", g4["extension"])
        code, out = run(asset("geant4_run.py"), "scan", "--base", base, "--grid", grid, "--exe", self.fake_exe(),
                        "--build-record", rec, "--out-dir", self.d / "slow", "--events-per-second", "0.001")
        self.assertEqual(code, 2, out)
        self.assertIn("partition", out["error"])

    def test_partition_merge_equals_a_single_run_and_refuses_nothing_twice(self):
        rec, _ = self.fake_install()
        s = spec()
        s["run"]["events"] = 60
        sp = self.write("s.json", s)
        lp = PLUGIN / "skills" / "hep-computing" / "scripts" / "local_partition.py"
        man, state, work = self.d / "m.json", self.d / "state", self.d / "chunks"
        self.assertEqual(run(lp, "plan", "--job", "g4", "--items", 60, "--chunk-size", 25, "--seed", 3, "--out", man)[0], 0)
        cmd = (f"{sys.executable} -B {asset('geant4_run.py')} chunk --spec {sp} --exe {self.fake_exe()} --build-record "
               f"{rec} --work {work} --start {{start}} --stop {{stop}} --seed {{seed}} --id {{id}} --out {{out}}")
        code, out = run(lp, "run", "--manifest", man, "--state", state, "--cmd", cmd)
        self.assertEqual(code, 0, out)
        code, merged = run(lp, "merge", "--manifest", man, "--state", state, "--rule", "csv=concat", "--rule",
                           "records=concat")
        self.assertEqual(code, 0, merged)
        mfile = self.write("merged.json", merged)
        code, out = self.go(s, run_id="single")
        code, summ = run(asset("geant4_run.py"), "summarize", "--merged", mfile, "--work", work, "--single-record",
                         self.d / "art" / "single.json")
        self.assertEqual(code, 0, summ)
        self.assertEqual((summ["n_events"], summ["duplicate_events"], summ["events_in_csv"]), (60, 0, 60))
        self.assertTrue(all(abs(r["z"]) < 1e-9 for r in summ["comparison"]))  # the fake is event-number deterministic

    def test_reduce_is_byte_reproducible(self):
        self.go(spec())
        csv = self.d / "work" / "r1" / "events.csv"
        a = run(asset("geant4_run.py"), "reduce", "--csv", csv, "--columns", "event", "edep_Pb_MeV", "--out",
                self.d / "a.csv.gz")[1]
        b = run(asset("geant4_run.py"), "reduce", "--csv", csv, "--columns", "event", "edep_Pb_MeV", "--out",
                self.d / "b.csv.gz")[1]
        self.assertEqual(a["sha256"], b["sha256"])
        self.assertTrue(gzip.decompress((self.d / "a.csv.gz").read_bytes()).startswith(b"# SIMULATION\nevent,"))


class ImplementationChecks(_Tmp):
    """Recorded real runs (Geant4 11.4.3 on E2) replayed through geant4_verify.py."""

    def verify(self, check, rid, *extra, work=FIX / "runs"):
        return run(asset("geant4_verify.py"), check, "--run-record", FIX / "records" / f"{rid}.computational-run.json",
                   "--work", work, *extra)

    def test_recorded_records_validate(self):
        for f in (FIX / "records").glob("*.computational-run.json"):
            with self.subTest(record=f.name):
                rec = json.loads(f.read_text(encoding="utf-8"))
                self.assertTrue(validate_artifact(rec).ok)
                self.assertIn("unvalidated", rec["status"])
                self.assertNotIn("validated-in-scope", rec["status"])

    def test_overlaps(self):
        self.assertEqual(self.verify("overlaps", "budget_geantino_testem3")[0], 0)
        code, out = self.verify("overlaps", "overlap_shifted_slab")
        self.assertEqual(code, 1, out)
        self.assertGreater(out["overlap_reports"], 0)
        self.assertIn("not a proof", out["note"])

    def test_material_budget_and_a_tampered_dump(self):
        code, out = self.verify("budget", "budget_geantino_testem3")
        self.assertEqual(code, 0, out)
        self.assertAlmostEqual(out["spec_x_over_X0"], out["scan_x_over_X0"], places=9)
        work = self.d / "w"
        shutil.copytree(FIX / "runs" / "budget_geantino_testem3", work / "budget_geantino_testem3")
        dump = work / "budget_geantino_testem3" / "materials.json"
        d = json.loads(dump.read_text(encoding="utf-8"))
        for m in d["materials"]:
            if m["name"] == "Galactic":
                m["density_g_cm3"] *= 1.1
        dump.write_text(json.dumps(d), encoding="utf-8")
        code, out = self.verify("budget", "budget_geantino_testem3", work=work)
        self.assertEqual(code, 1, out)

    def test_energy_balance_and_its_negative_controls(self):
        code, out = self.verify("balance", "balance_killed_tracks", "--tolerance-mev", "0.001")
        self.assertEqual(code, 0, out)
        self.assertTrue(out["closure_test"])
        self.assertGreater(out["events_with_killed_eplus"], 0)
        for inj in ("omit-positron-mass", "double-count-booked"):
            with self.subTest(inject=inj):
                code, out = self.verify("balance", "balance_killed_tracks", "--tolerance-mev", "0.001", "--inject", inj)
                self.assertEqual(code, 1, out)
                self.assertEqual(out["events_beyond_tolerance"], out["events"])

    def test_an_injection_with_nothing_to_act_on_is_not_a_pass(self):
        code, out = self.verify("balance", "overlap_shifted_slab", "--tolerance-mev", "0.001", "--inject",
                                "omit-positron-mass")  # an e- run without killed tracks
        self.assertEqual(code, 3, out)
        self.assertEqual(out["events_affected_by_injection"], 0)

    def test_mirrors_against_the_local_examples(self):
        for rid, ex in (("mirror-testem3", "TestEm3"), ("mirror-testem5_run0", "TestEm5")):
            with self.subTest(example=ex):
                code, out = self.verify("mirror", rid, "--example", ex, "--local-out",
                                        FIX / "out" / f"{ex}.mirror-reference.out")
                self.assertEqual(code, 0, out)
                self.assertTrue(all(r["verdict"] == "pass" for r in out["rows"]))

    def test_data_paths(self):
        self.assertEqual(self.verify("datapaths", "budget_geantino_testem3")[0], 0)
        code, out = self.verify("datapaths", "dataoverride")
        self.assertEqual(code, 1, out)
        self.assertTrue(any("G4LEDATA" in p for p in out["problems"]))

    def test_check_record_carries_the_input_labels(self):
        rec = self.d / "check.json"
        code, out = self.verify("balance", "balance_killed_tracks", "--tolerance-mev", "0.001", "--record", rec,
                                "--created", "2026-10-21")
        doc = json.loads(rec.read_text(encoding="utf-8"))
        self.assertTrue(validate_artifact(doc).ok, validate_artifact(doc).as_dict())
        self.assertEqual(doc["inputs"][0]["status"], ["unvalidated"])
        self.assertIn("unvalidated", doc["status"])


class Oracle(_Tmp):
    """geant4_run.py oracle calls skills/hep-detector/scripts/geant4_benchmarks.py through a subprocess on the J14
    recorded proton run (stopping power against Bethe) and its negative control."""

    def config(self, csv):
        rec = J14 / "recorded"
        cfg = {"schema": "geant4-benchmarks/1", "study_spec": str(J14 / "study-sp.json"), "benchmarks": [
            {"benchmark": "stopping-power", "csv": str(csv), "particle": "proton", "energy_MeV": 100.0,
             "material": "Si_study", "slab": "Si", "thickness_mm": 0.3, "bootstrap": {"resamples": 50, "seed": 1},
             "tolerance": {"reference_accuracy_relative": 0.03, "k_sigma": 3},
             "negative_control": {"csv": str(rec / "events" / "sp-control.csv.gz"),
                                  **json.loads((rec / "control-sp.json").read_text(encoding="utf-8"))}}]}
        cfg["benchmarks"][0]["negative_control"].pop("detection_limit_relative", None)
        return self.write("cfg.json", cfg)

    def test_recorded_output_passes_and_a_tampered_one_fails(self):
        good = J14 / "recorded" / "events" / "sp-nominal.csv.gz"
        code, out = run(asset("geant4_run.py"), "oracle", "--benchmark-config", self.config(good))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["benchmarks"], {"stopping-power": "pass"})
        lines = gzip.decompress(good.read_bytes()).decode().splitlines()
        cols = lines[1].split(",")
        k = cols.index("primary_eloss_MeV")
        tampered = lines[:2]
        for ln in lines[2:]:
            v = ln.split(",")
            v[k] = repr(float(v[k]) * 1.10)
            tampered.append(",".join(v))
        bad = self.d / "tampered.csv.gz"
        bad.write_bytes(gzip.compress(("\n".join(tampered) + "\n").encode(), mtime=0))
        code, out = run(asset("geant4_run.py"), "oracle", "--benchmark-config", self.config(bad))
        self.assertEqual(code, 1, out)
        self.assertEqual(out["failed"], ["stopping-power"])


@unittest.skipUnless(LIVE, "set HEP_GEANT4_LIVE_TEST=1 and HEP_GEANT4_CONFIG to rerun with Geant4")
class Live(_Tmp):
    def setUp(self):
        super().setUp()
        cfg = json.loads(Path(os.path.expanduser(os.environ["HEP_GEANT4_CONFIG"])).read_text(encoding="utf-8"))
        self.build = os.path.expanduser(cfg["build_record"])
        self.exe = os.path.expanduser(cfg["layered_sim"])

    def go(self, s, rid):
        sp = self.write(f"{rid}.json", s)
        return run(asset("geant4_run.py"), "run", "--spec", sp, "--exe", self.exe, "--build-record", self.build,
                   "--work", self.d / "work", "--run-id", rid, "--record", self.d / f"{rid}.rec.json", timeout=3600)

    def small(self, **over):
        s = json.loads((ASSETS / "layered_sim" / "mirror_testem5_run0.json").read_text(encoding="utf-8"))
        s.pop("source")
        s["run"]["events"] = 2000
        s["physics"]["regions"] = [{"name": "SiRegion", "slabs": ["Si"], "cut_mm": 0.007}]
        s.update(over)
        return s

    def test_build_record_still_matches_the_installation(self):
        code, out = run(asset("geant4_build.py"), "check", "--record", self.build, timeout=3600)
        self.assertEqual(code, 0, out)

    def test_em_commands_exist_between_physics_construction_and_initialization(self):
        code, out = self.go(self.small(ui_commands=["/process/msc/Skin 1",
                                                    "/process/em/AddPAIRegion all SiRegion PAI"]), "ui")
        self.assertEqual(code, 0, out)
        log = (self.d / "work" / "ui" / "log.txt").read_text(encoding="utf-8", errors="replace")
        self.assertIn('LAYERED_SIM_UI "/process/em/AddPAIRegion all SiRegion PAI" 0', log)
        code, out = self.go(self.small(ui_commands=["/process/em/noSuchCommand 1"]), "badui")
        self.assertEqual(code, 2, out)

    def test_mt_run_is_merged_in_event_order(self):
        s = self.small()
        s["run"].update(run_manager="mt", threads=2)
        code, out = self.go(s, "mt")
        self.assertEqual(code, 0, out)
        rows = (self.d / "work" / "mt" / "events.csv").read_text(encoding="utf-8").splitlines()[2:]
        events = [int(r.split(",")[0]) for r in rows]
        self.assertEqual(events, list(range(2000)))

    def test_mirror_run_passes_the_checks(self):
        code, out = self.go(self.small(), "m5")
        self.assertEqual(code, 0, out)
        for check in ("overlaps", "datapaths"):
            c, o = run(asset("geant4_verify.py"), check, "--run-record", self.d / "m5.rec.json")
            self.assertEqual(c, 0, o)


if __name__ == "__main__":
    unittest.main()
