"""adapters/geant4 0.6.0: registering an existing Geant4 installation (geant4_build.py register) and using it.

Offline tests build a fake installation: a geant4-config shell script, Geant4Config.cmake and Geant4ConfigVersion.cmake
with dataset descriptions, and dataset folders in Geant4's layout (G4EMLOW8.8) or conda-forge's (EMLOW8.8, without
the G4 prefix). They cover the dataset sources (environment variable, geant4-config path, auto), the refusals (a
dataset found nowhere, a folder of another version or name, a prefix without Geant4Config.cmake, a version or prefix
that disagrees), check on a registered record, the record shape the downstream helpers read, a run with the fake
layered_sim of test_geant4.py and the explicit example source. No test links, imports or needs Geant4.

Set HEP_GEANT4_REGISTER_TEST to a real installation's geant4-config (or its prefix) to register it into a temporary
folder and check it (the dataset variables of the current environment are used as with --dataset-source auto); without
it those tests skip, which is unverified, not passing."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.adapters.test_geant4 import FAKE_SIM, run, spec

PLUGIN = Path(__file__).resolve().parents[2]
ASSETS = PLUGIN / "adapters" / "geant4" / "assets"
BUILD = ASSETS / "geant4_build.py"
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(ASSETS))
from contracts.validate import validate_artifact  # noqa: E402
import g4common  # noqa: E402
import geant4_build  # noqa: E402

REAL = os.environ.get("HEP_GEANT4_REGISTER_TEST")
# name, variable, version, tarball file name (as Geant4Config.cmake's dataset descriptions write them)
DATASETS = (("G4EMLOW", "G4LEDATA", "8.8", "G4EMLOW"), ("PhotonEvaporation", "G4LEVELGAMMADATA", "6.1.2",
                                                       "G4PhotonEvaporation"))


def clean_env(**extra):
    """The test process environment without any Geant4 dataset variable, plus extra."""
    env = {k: v for k, v in os.environ.items() if k not in g4common.DATA_VARS}
    env.update({k: str(v) for k, v in extra.items()})
    return env


class FakeInstall:
    """A fake Geant4 11.4.3 installation under root/prefix; layout 'geant4' (G4EMLOW8.8) or 'conda' (EMLOW8.8)."""

    def __init__(self, root: Path, layout="geant4", cmake=True, cmake_version="11.4.3", reported_prefix=None):
        self.prefix = root / "prefix"
        self.data_dir = self.prefix / "share" / "Geant4" / "data"
        self.data_dir.mkdir(parents=True)
        self.folders = {}
        for name, _var, ver, _tar in DATASETS:
            folder = f"{name}{ver}" if layout == "geant4" or not name.startswith("G4") else f"{name[2:]}{ver}"
            d = self.data_dir / folder
            d.mkdir()
            (d / "table.dat").write_text(f"{name} {ver}\n")
            self.folders[name] = d
        bindir = self.prefix / "bin"
        bindir.mkdir()
        lines = "\n".join(f"{n} {v} {self.data_dir / (n + ver)}" for n, v, ver, _t in DATASETS)
        self.config = bindir / "geant4-config"
        self.config.write_text(f"""#!/bin/sh
case "$1" in
  --version) echo 11.4.3 ;;
  --prefix) echo "{reported_prefix or self.prefix}" ;;
  --cxxstd) echo 17 ;;
  --tls-model) echo global-dynamic ;;
  --features) printf ' staticlibs[no]\\n multithreading[yes]\\n gdml[no]\\n' ;;
  --datasets) cat <<'EOF'
{lines}
EOF
  ;;
  --check-datasets) echo "information only" ;;
  *) exit 1 ;;
esac
""")
        self.config.chmod(self.config.stat().st_mode | stat.S_IEXEC)
        if cmake:
            cdir = self.prefix / "lib" / "cmake" / "Geant4"
            cdir.mkdir(parents=True)
            desc = ";".join(f"{n}|{v}|{self.data_dir / (n + ver)}|{t}.{ver}.tar.gz|{'0' * 32}" for n, v, ver, t in DATASETS)
            (cdir / "Geant4Config.cmake").write_text(
                f'set(Geant4_CXX_STANDARD "17")\nset(Geant4_DATASET_DESCRIPTIONS "{desc}")\n')
            (cdir / "Geant4ConfigVersion.cmake").write_text(f'set(PACKAGE_VERSION "{cmake_version}")\n')


class _TempDirCase(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def register(self, inst, *extra, env=None, record="reg.json"):
        code, out = run(BUILD, "register", "--geant4-config", inst.config, "--record", self.d / record,
                        "--no-cmake-probe", "--created", "2026-10-30", *extra, env=env or clean_env())
        return code, out, self.d / record


class Register(_TempDirCase):
    def test_dataset_variables_of_a_conda_layout_are_used_and_reported(self):
        inst = FakeInstall(self.d, layout="conda")
        env = clean_env(G4LEDATA=inst.folders["G4EMLOW"], G4LEVELGAMMADATA=inst.folders["PhotonEvaporation"])
        code, out, rec_path = self.register(inst, env=env)
        self.assertEqual(code, 0, out)
        got = {d["name"]: d for d in out["datasets"]}
        self.assertEqual((got["G4EMLOW"]["resolved_from"], got["G4EMLOW"]["folder_name_match"]),
                         ("environment", "without-G4-prefix"))
        self.assertEqual(got["PhotonEvaporation"]["folder_name_match"], "exact")
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        self.assertTrue(validate_artifact(rec).ok, validate_artifact(rec).as_dict())
        b = rec["extension"]["build"]
        self.assertEqual((b["origin"], b["tag"], b["commit"]), ("registered", None, None))
        self.assertEqual(b["geant4_config"]["version"], "11.4.3")
        self.assertEqual(b["multithreaded"], "ON")
        self.assertTrue(any("commit" in u for u in b["unknown"]) and any("MD5" in u for u in b["unknown"]))
        for d in b["datasets"]:
            self.assertEqual(d["content_sha256"], geant4_build.tree_hash(Path(os.path.expanduser(d["path"])))[0])
            self.assertIsNone(d["md5_verified"])
            self.assertEqual(d["md5_expected"], "0" * 32)
        self.assertEqual(rec["status"], ["unvalidated"])
        self.assertTrue(rec["artifact_id"].startswith("geant4-registered-11.4.3-"))

    def test_the_geant4_config_path_is_used_when_no_variable_is_set(self):
        inst = FakeInstall(self.d)
        code, out, _ = self.register(inst)
        self.assertEqual(code, 0, out)
        self.assertEqual({d["resolved_from"] for d in out["datasets"]}, {"geant4-config"})
        self.assertEqual({d["folder_name_match"] for d in out["datasets"]}, {"exact"})

    def test_config_source_ignores_a_set_variable_and_records_it(self):
        inst = FakeInstall(self.d)
        other = self.d / "elsewhere" / "G4EMLOW8.8"
        other.mkdir(parents=True)
        (other / "x").write_text("another copy\n")
        code, out, rec_path = self.register(inst, "--dataset-source", "config", env=clean_env(G4LEDATA=other))
        self.assertEqual(code, 0, out)
        d = next(x for x in json.loads(rec_path.read_text())["extension"]["build"]["datasets"] if x["name"] == "G4EMLOW")
        self.assertEqual(d["resolved_from"], "geant4-config")
        self.assertEqual(Path(os.path.expanduser(d["path"])), inst.folders["G4EMLOW"])
        self.assertEqual(Path(os.path.expanduser(d["environment_value"])), other)

    def test_a_dataset_found_nowhere_is_refused_and_no_record_is_written(self):
        inst = FakeInstall(self.d, layout="conda")  # folders without the G4 prefix and no variable set
        code, out, rec_path = self.register(inst)
        self.assertEqual(code, 1, out)
        self.assertEqual(out["status"], "refused")
        self.assertEqual(len(out["refused"]), 1, out["refused"])  # PhotonEvaporation has no prefix: found
        self.assertIn("G4EMLOW: not found", out["refused"][0])
        self.assertIn("EMLOW8.8 exists next to it", out["refused"][0])
        self.assertFalse(rec_path.exists())

    def test_env_source_needs_the_variable(self):
        inst = FakeInstall(self.d)
        code, out, _ = self.register(inst, "--dataset-source", "env")
        self.assertEqual(code, 1, out)
        self.assertTrue(all("is not set" in r for r in out["refused"]), out["refused"])

    def test_a_variable_pointing_to_another_version_or_dataset_is_refused(self):
        inst = FakeInstall(self.d)
        old = self.d / "old" / "G4EMLOW8.7"
        old.mkdir(parents=True)
        (old / "x").write_text("8.7\n")
        for value, word in ((old, "G4EMLOW8.7"), (inst.folders["PhotonEvaporation"], "PhotonEvaporation6.1.2")):
            with self.subTest(value=word):
                code, out, rec_path = self.register(inst, env=clean_env(G4LEDATA=value))
                self.assertEqual(code, 1, out)
                self.assertIn(f"folder {word} is not the expected", out["refused"][0])
                self.assertIn("G4LEDATA is set to a folder that is not the dataset", out["refused"][0])
                self.assertFalse(rec_path.exists())

    def test_an_empty_dataset_folder_is_refused(self):
        inst = FakeInstall(self.d)
        (inst.folders["G4EMLOW"] / "table.dat").unlink()
        code, out, _ = self.register(inst)
        self.assertEqual(code, 1, out)
        self.assertIn("holds no file", out["refused"][0])

    def test_skip_dataset_leaves_it_out_on_purpose(self):
        inst = FakeInstall(self.d, layout="conda")
        code, out, rec_path = self.register(inst, "--skip-dataset", "G4EMLOW")
        self.assertEqual(code, 0, out)
        b = json.loads(rec_path.read_text())["extension"]["build"]
        self.assertEqual([d["name"] for d in b["datasets"]], ["PhotonEvaporation"])
        self.assertEqual(b["datasets_skipped"][0]["name"], "G4EMLOW")
        code, out, _ = self.register(inst, "--skip-dataset", "G4NOSUCH", record="r2.json")
        self.assertEqual(code, 2, out)

    def test_a_prefix_without_geant4config_cmake_is_refused(self):
        inst = FakeInstall(self.d, cmake=False)
        code, out = run(BUILD, "register", "--prefix", inst.prefix, "--record", self.d / "r.json", "--no-cmake-probe",
                        env=clean_env())
        self.assertEqual(code, 1, out)
        self.assertTrue(any("no Geant4Config.cmake" in r for r in out["refused"]), out["refused"])
        self.assertFalse((self.d / "r.json").exists())

    def test_a_cmake_version_or_prefix_that_disagrees_is_refused(self):
        inst = FakeInstall(self.d / "a", cmake_version="11.4.2")
        code, out, _ = self.register(inst)
        self.assertEqual(code, 1, out)
        self.assertTrue(any("Geant4ConfigVersion.cmake says 11.4.2" in r for r in out["refused"]), out["refused"])
        inst = FakeInstall(self.d / "b", reported_prefix=self.d / "somewhere-else")
        code, out = run(BUILD, "register", "--prefix", inst.prefix, "--record", self.d / "r.json", "--no-cmake-probe",
                        env=clean_env())
        self.assertEqual(code, 1, out)
        self.assertTrue(any("geant4-config --prefix is" in r for r in out["refused"]), out["refused"])

    def test_not_a_geant4_installation_is_bad_input(self):
        (self.d / "empty").mkdir()
        code, out = run(BUILD, "register", "--prefix", self.d / "empty", "--record", self.d / "r.json", env=clean_env())
        self.assertEqual((code, out["status"]), (2, "rejected"))
        code, out = run(BUILD, "register", "--geant4-config", self.d / "nothing", "--record", self.d / "r.json",
                        env=clean_env())
        self.assertEqual((code, out["status"]), (2, "rejected"))
        code, out = run(BUILD, "register", "--record", self.d / "r.json", env=clean_env())  # neither option
        self.assertEqual(code, 2, out)

    def test_cmake_probe_failure_is_recorded_not_fatal(self):
        inst = FakeInstall(self.d)
        fake_cmake = self.d / "bin" / "cmake"
        fake_cmake.parent.mkdir()
        fake_cmake.write_text("#!/bin/sh\nif [ \"$1\" = --version ]; then echo 'cmake version 3.26.5'; exit 0; fi\n"
                              "echo 'CMake Error at Geant4Config.cmake:277 (find_dependency):'\n"
                              "echo '  Could NOT find EXPAT (missing: EXPAT_LIBRARY EXPAT_INCLUDE_DIR) (Required'\n"
                              "echo '  is at least version \"2.8.5\")'\necho ''\nexit 1\n")
        fake_cmake.chmod(0o755)
        env = clean_env(PATH=f"{fake_cmake.parent}{os.pathsep}{os.environ.get('PATH', '')}")
        code, out = run(BUILD, "register", "--geant4-config", inst.config, "--record", self.d / "r.json", env=env)
        self.assertEqual(code, 0, out)
        probe = out["cmake_probe"]
        self.assertEqual((probe["ran"], probe["find_package_ok"]), (True, False))
        self.assertIn('Could NOT find EXPAT (missing: EXPAT_LIBRARY EXPAT_INCLUDE_DIR) (Required is at least version '
                      '"2.8.5")', probe["errors"])
        self.assertTrue(any("--configure-with geant4-config" in w for w in out["warnings"]))


class CheckAndDownstream(_TempDirCase):
    def setUp(self):
        super().setUp()
        self.inst = FakeInstall(self.d)
        code, out, self.rec_path = self.register(self.inst)
        self.assertEqual(code, 0, out)
        self.rec = json.loads(self.rec_path.read_text(encoding="utf-8"))

    def test_check_rehashes_datasets_and_rereads_the_configuration(self):
        code, out = run(BUILD, "check", "--record", self.rec_path, env=clean_env())
        self.assertEqual(code, 0, out)
        self.assertEqual((out["origin"], out["differences"]), ("registered", []))
        (self.inst.folders["G4EMLOW"] / "table.dat").write_text("changed\n")
        cfg = self.inst.prefix / "lib" / "cmake" / "Geant4" / "Geant4Config.cmake"
        cfg.write_text(cfg.read_text() + "# edited\n")
        code, out = run(BUILD, "check", "--record", self.rec_path, env=clean_env())
        self.assertEqual(code, 1, out)
        self.assertTrue(any(x.startswith("dataset G4EMLOW") for x in out["differences"]), out["differences"])
        self.assertTrue(any("Geant4Config.cmake: sha256" in x for x in out["differences"]), out["differences"])

    def test_the_helpers_read_a_registered_record(self):
        self.assertIsNone(g4common.build_record_ok(self.rec))
        self.assertEqual(g4common.build_origin(self.rec), "registered")
        ident = g4common.geant4_identity(self.rec)
        self.assertEqual((ident["origin"], ident["version"], ident["commit"]), ("registered", "11.4.3", None))
        self.assertEqual(g4common.geant4_label(self.rec), "11.4.3 (registered installation, source commit unknown)")
        self.assertEqual(g4common.geant4_config_path(self.rec), self.inst.config.resolve())
        self.assertEqual(g4common.geant4_cmake_dir(self.rec), (self.inst.prefix / "lib" / "cmake" / "Geant4").resolve())
        env = g4common.data_env(self.rec)
        self.assertEqual(Path(env["G4LEDATA"]), self.inst.folders["G4EMLOW"].resolve())
        bad = json.loads(json.dumps(self.rec))
        bad["extension"]["build"]["origin"] = "downloaded"
        self.assertIn("unknown origin", g4common.build_record_ok(bad))
        old = json.loads((PLUGIN / "tests" / "adapters" / "fixtures" / "geant4" / "records" /
                          "geant4-build.computational-run.json").read_text(encoding="utf-8"))
        self.assertEqual(g4common.build_origin(old), "built-from-source")  # a record from before 0.6.0
        self.assertEqual(g4common.geant4_label(old), "v11.4.3 (2ee379e6843e55b9c6bbb835d2a2b03cc998fef0)")

    def test_a_run_on_a_registered_installation_carries_the_origin(self):
        exe = self.d / "fake_layered_sim"
        exe.write_text(f"#!{sys.executable}\n" + FAKE_SIM.split("\n", 1)[1].replace("@PLUGIN@", str(PLUGIN)))
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
        sp = self.d / "s.json"
        sp.write_text(json.dumps(spec()), encoding="utf-8")
        code, out = run(ASSETS / "geant4_run.py", "run", "--spec", sp, "--exe", exe, "--build-record", self.rec_path,
                        "--work", self.d / "work", "--run-id", "r1", "--record", self.d / "r1.json",
                        env=clean_env(G4LEDATA=self.d / "not-used"))
        self.assertEqual(code, 0, out)
        rec = json.loads((self.d / "r1.json").read_text(encoding="utf-8"))
        self.assertTrue(validate_artifact(rec).ok, validate_artifact(rec).as_dict())
        g = rec["extension"]["simulation"]["geant4"]
        self.assertEqual((g["origin"], g["tag"], g["commit"], g["installation_version"]),
                         ("registered", None, None, "11.4.3"))
        self.assertTrue(g["unknown"])
        self.assertEqual(rec["extension"]["tools"][0]["version"],
                         "11.4.3 (registered installation, source commit unknown)")
        self.assertTrue(all(d["path_match"] and d["content_match"] for d in rec["extension"]["simulation"]["datasets"]))
        sys.path.insert(0, str(PLUGIN / "skills" / "hep-detector" / "scripts"))
        import geant4_benchmarks
        inst = geant4_benchmarks.geant4_installation(rec)
        self.assertEqual(inst["origin"], "registered")
        self.assertIn("weaker", inst["provenance"])
        rec["extension"]["simulation"]["geant4"] = {"version": "11.4.3", "tag": "v11.4.3", "commit": "2ee379e6"}
        self.assertIsNone(geant4_benchmarks.geant4_installation(rec))  # before 0.6.0: not reported, output unchanged

    def test_examples_need_an_explicit_source_of_the_installed_version(self):
        ex = ASSETS / "geant4_examples.py"
        code, out = run(ex, "build", "--build-record", self.rec_path, "--work", self.d / "w", env=clean_env())
        self.assertEqual(code, 2, out)
        self.assertIn("registered installation has no source tree", out["error"])
        src = self.d / "src"
        (src / "examples").mkdir(parents=True)
        vh = src / "source" / "global" / "management" / "include" / "G4Version.hh"
        vh.parent.mkdir(parents=True)
        vh.write_text("#define G4VERSION_NUMBER 1142\n")
        code, out = run(ex, "build", "--build-record", self.rec_path, "--work", self.d / "w", "--source", src,
                        env=clean_env())
        self.assertEqual(code, 2, out)
        self.assertIn("G4Version.hh gives Geant4 11.4.2, the installation is 11.4.3", out["error"])
        import geant4_examples
        vh.write_text("#define G4VERSION_NUMBER 1143\n")
        got, info = geant4_examples.example_source(self.rec, str(src))
        self.assertEqual((got, info["version_checked"], info["version"]), (src, True, "11.4.3"))
        vh.unlink()
        self.assertFalse(geant4_examples.example_source(self.rec, str(src))[1]["version_checked"])


class RecordedE5(unittest.TestCase):
    """The recorded E5 registration (conda-forge Geant4 11.4.3 on RHEL 9, 2026-10-30, paths as ~) and its official
    example comparison (local work folder written as <work>); VALIDATION GEANT4-REGISTER."""
    FIX = PLUGIN / "tests" / "adapters" / "fixtures" / "geant4" / "records"

    def test_the_registration_is_a_valid_registered_record(self):
        rec = json.loads((self.FIX / "geant4-registered-e5.computational-run.json").read_text(encoding="utf-8"))
        self.assertTrue(validate_artifact(rec).ok, validate_artifact(rec).as_dict())
        self.assertIsNone(g4common.build_record_ok(rec))
        b = rec["extension"]["build"]
        self.assertEqual((b["origin"], b["commit"], b["geant4_config"]["version"]), ("registered", None, "11.4.3"))
        self.assertEqual(len(b["datasets"]), 12)
        self.assertEqual({d["resolved_from"] for d in b["datasets"]}, {"environment"})
        self.assertEqual(sum(d["folder_name_match"] == "without-G4-prefix" for d in b["datasets"]), 9)
        self.assertFalse(b["registration"]["cmake_probe"]["find_package_ok"])
        self.assertNotIn("/" + "Users/", json.dumps(rec))
        e2 = json.loads((self.FIX / "geant4-build.computational-run.json").read_text(encoding="utf-8"))
        e2_hash = {d["name"]: d["content_sha256"] for d in e2["extension"]["build"]["datasets"]}
        shared = {d["name"]: d["content_sha256"] for d in b["datasets"] if d["name"] in e2_hash}
        self.assertEqual(len(shared), 11)  # every E2 dataset (no G4NDL there): same content as the MD5-checked downloads
        self.assertEqual(shared, e2_hash)

    def test_the_example_comparison_passes(self):
        t = json.loads((self.FIX / "examples-compare-e5-s1.json").read_text(encoding="utf-8"))
        self.assertEqual((t["status"], t["m_compared"]), ("ok", 48))
        rows = [r for ex in t["examples"].values() for r in ex["rows"]]
        self.assertEqual(len(rows), 48)
        self.assertTrue(all(r["verdict"] == "pass" and abs(r["z"]) <= t["z_crit"] for r in rows))


class GeantConfigBuild(unittest.TestCase):
    """--configure-with geant4-config: the CMake helper and its use (static: no compiler or Geant4 here)."""

    def test_both_programs_and_the_examples_can_take_geant4_config_explicitly(self):
        cmake_text = (ASSETS / "g4sim" / "Geant4FromConfig.cmake").read_text(encoding="utf-8")
        for needle in ("--cflags-without-gui", "--libs-without-gui", "LINKER:-rpath,", "set(Geant4_LIBRARIES g4sim_geant4)",
                       "G4SIM_GEANT4_MIN_VERSION"):
            self.assertIn(needle, cmake_text)
        for prog in ("layered_sim", "element_sim"):
            text = (ASSETS / prog / "CMakeLists.txt").read_text(encoding="utf-8")
            with self.subTest(program=prog):
                self.assertIn("if(G4SIM_GEANT4_CONFIG)", text)
                self.assertIn("find_package(Geant4 11.4 REQUIRED)", text)  # the default stays find_package
        import geant4_examples
        text = geant4_examples.EXAMPLE_CMAKE.format(exe="exampleB1", helper="/h/Geant4FromConfig.cmake")
        self.assertIn('include("/h/Geant4FromConfig.cmake")', text)
        self.assertIn("set(G4SIM_GEANT4_CONFIG_GUI ON)", text)
        self.assertIn('add_executable(exampleB1 "${EXAMPLE_DIR}/exampleB1.cc"', text)

    def test_build_sim_refuses_a_missing_geant4_config(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            inst = FakeInstall(d)
            code, out = run(BUILD, "register", "--geant4-config", inst.config, "--record", d / "r.json",
                            "--no-cmake-probe", env=clean_env())
            self.assertEqual(code, 0, out)
            inst.config.unlink()
            code, out = run(ASSETS / "geant4_run.py", "build-sim", "--build-record", d / "r.json", "--work", d / "w",
                            "--configure-with", "geant4-config", env=clean_env())
            if out.get("error") == "cmake not found on PATH":
                self.skipTest("cmake not found on PATH")
            self.assertEqual(code, 3, out)
            self.assertIn("no geant4-config", out["error"])


@unittest.skipUnless(REAL, "set HEP_GEANT4_REGISTER_TEST to a Geant4 installation's geant4-config or prefix")
class RealInstallation(unittest.TestCase):
    """Registers the installation HEP_GEANT4_REGISTER_TEST names (with the dataset variables of this environment) and
    checks it; a refusal fails the test with its reasons."""

    def test_register_and_check(self):
        target = Path(os.path.expanduser(REAL))
        opt = "--geant4-config" if target.is_file() else "--prefix"
        with tempfile.TemporaryDirectory() as t:
            rec_path = Path(t) / "registered.json"
            code, out = run(BUILD, "register", opt, target, "--record", rec_path, timeout=3600)
            self.assertEqual(code, 0, out.get("refused") or out)
            rec = json.loads(rec_path.read_text(encoding="utf-8"))
            self.assertTrue(validate_artifact(rec).ok, validate_artifact(rec).as_dict())
            self.assertIsNone(g4common.build_record_ok(rec))
            b = rec["extension"]["build"]
            self.assertEqual(b["origin"], "registered")
            self.assertTrue(b["datasets"])
            self.assertTrue(all(d["n_files"] > 0 and len(d["content_sha256"]) == 64 for d in b["datasets"]))
            code, out = run(BUILD, "check", "--record", rec_path, timeout=3600)
            self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
