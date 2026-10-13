"""environment_manifest.py (T23): records the environment in the computational-run shape, never records unlisted
variables, and reports drift."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-computing" / "scripts" / "environment_manifest.py"
sys.path.insert(0, str(SCRIPT.parent))
import environment_manifest as em  # noqa: E402


class EnvironmentManifestTests(unittest.TestCase):
    def test_record_shape_and_absent_package(self):
        m = em.record(["pip", "surely-not-installed-pkg"])
        env = m["environment"]
        self.assertEqual(env["python"], ".".join(map(str, sys.version_info[:3])))
        self.assertIsNone(env["packages"]["surely-not-installed-pkg"])
        self.assertIn({"name": "pip", "version": env["packages"]["pip"]}, m["tools"])
        self.assertNotIn("surely-not-installed-pkg", [t["name"] for t in m["tools"]])

    def test_only_listed_variables_and_origin(self):
        with mock.patch.dict(os.environ, {"LCG_VERSION": "LCG_106", "MY_SECRET_TOKEN": "x"}, clear=False):
            for k in ("APPTAINER_CONTAINER", "SINGULARITY_CONTAINER"):
                os.environ.pop(k, None)
            env = em.record([])["environment"]
        self.assertEqual(env["variables"].get("LCG_VERSION"), "LCG_106")
        self.assertNotIn("MY_SECRET_TOKEN", json.dumps(env))
        self.assertEqual(env["origin"], "lcg-view")
        with mock.patch.dict(os.environ, {"APPTAINER_CONTAINER": "/x.sif"}):
            self.assertEqual(em.record([])["environment"]["origin"], "container")

    def test_git_project(self):
        env = em.record([], project=ROOT)["environment"]
        if "error" in env["project"]:  # a copy of the plugin outside git (the no-AMS check runs one)
            self.assertEqual(env["project"]["error"], "not a git repository")
        else:
            self.assertRegex(env["project"]["commit"], r"^[0-9a-f]{40}$")
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("error", em._git(Path(d)))

    def test_check_round_trip_and_drift(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "env.json"
            r = subprocess.run([sys.executable, "-I", str(SCRIPT), "record", "--packages", "pip", "--out", str(out)],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr)
            same = subprocess.run([sys.executable, "-I", str(SCRIPT), "check", "--manifest", str(out)],
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(same.returncode, 0, same.stdout)
            self.assertEqual(json.loads(same.stdout)["status"], "same")
            doc = json.loads(out.read_text())
            doc["environment"]["packages"]["pip"] = "0.0.1"
            doc["environment"]["python"] = "2.7.18"
            out.write_text(json.dumps(doc))
            moved = subprocess.run([sys.executable, "-I", str(SCRIPT), "check", "--manifest", str(out)],
                                   capture_output=True, text=True, timeout=120)
            self.assertEqual(moved.returncode, 1)
            drift = json.loads(moved.stdout)["drift"]
            self.assertTrue(any(x.startswith("package pip: '0.0.1'") for x in drift), drift)
            self.assertTrue(any(x.startswith("python: '2.7.18'") for x in drift), drift)
            out.write_text("{not json")
            bad = subprocess.run([sys.executable, "-I", str(SCRIPT), "check", "--manifest", str(out)],
                                 capture_output=True, text=True, timeout=120)
            self.assertEqual(bad.returncode, 2)

    def test_manifest_fits_a_computational_run(self):
        m = em.record(["pip"])
        schema = json.loads((ROOT / "contracts" / "schemas" / "ext_computational_run.json").read_text())
        props = schema.get("properties", {})
        self.assertEqual(props.get("environment", {}).get("type"), "object")
        tool_req = props.get("tools", {}).get("items", {}).get("required", ["name", "version"])
        for t in m["tools"]:
            self.assertTrue(set(tool_req) <= set(t), t)


class EnvironmentManifestRemediationTests(unittest.TestCase):
    """CMP-07: drift compared platform.platform() (kernel release on Linux), ignored executable, machine, project and
    inputs; record --out into a missing folder was a traceback; record printed no status."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)

    def cli(self, *args):
        p = subprocess.run([sys.executable, "-I", str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=120)
        self.assertNotIn("Traceback", p.stderr)
        return p.returncode, json.loads(p.stdout)

    def recorded(self, *extra):
        out = self.d / "m.json"
        code, doc = self.cli("record", "--packages", "pip", "--out", out, *extra)
        self.assertEqual((code, doc["status"]), (0, "recorded"))
        return out, json.loads(out.read_text())

    def test_kernel_release_alone_is_a_note(self):
        out, doc = self.recorded()
        doc["environment"]["system"]["kernel"] = "0.0.0-other"
        doc["environment"]["platform"] = "Linux-0.0.0-other-x86_64-with-glibc2.28"
        out.write_text(json.dumps(doc))
        code, res = self.cli("check", "--manifest", out)
        self.assertEqual((code, res["status"]), (0, "same"), res)
        self.assertTrue(any("kernel release" in n for n in res["notes"]), res)

    def test_executable_libc_and_arch_are_compared(self):
        out, doc = self.recorded()
        doc["environment"]["executable"] = "/elsewhere/python"
        doc["environment"]["system"]["libc"] = "glibc 2.17"
        out.write_text(json.dumps(doc))
        code, res = self.cli("check", "--manifest", out)
        self.assertEqual(code, 1)
        self.assertTrue(any(x.startswith("executable:") for x in res["drift"]), res)
        self.assertTrue(any(x.startswith("system libc:") for x in res["drift"]), res)

    def test_changed_and_missing_inputs_are_drift(self):
        a, b = self.d / "a.dat", self.d / "b.dat"
        a.write_text("one")
        b.write_text("two")
        out, doc = self.recorded("--inputs", a, b)
        self.assertEqual([e["size"] for e in doc["input_manifest"]], [3, 3])
        self.assertEqual(self.cli("check", "--manifest", out)[0], 0)
        a.write_text("ONE")
        b.unlink()
        code, res = self.cli("check", "--manifest", out)
        self.assertEqual(code, 1)
        self.assertIn(f"input changed: {a}", res["drift"])
        self.assertIn(f"input missing: {b}", res["drift"])

    def test_dirty_or_moved_project_is_drift(self):
        repo = self.d / "repo"
        repo.mkdir()
        git = ["git", "-C", str(repo), "-c", "user.email=synthetic-test", "-c", "user.name=t"]
        if subprocess.run(git[:3] + ["init", "-q"], capture_output=True, timeout=60).returncode:
            self.skipTest("git not available")
        (repo / "f.txt").write_text("x")
        subprocess.run(git + ["add", "f.txt"], check=True, timeout=60)
        subprocess.run(git + ["commit", "-qm", "c1"], check=True, timeout=60)
        out, _ = self.recorded("--project", repo)
        self.assertEqual(self.cli("check", "--manifest", out, "--project", repo)[0], 0)
        code, res = self.cli("check", "--manifest", out)
        self.assertTrue(any("--project" in n for n in res["notes"]))
        (repo / "f.txt").write_text("changed")
        code, res = self.cli("check", "--manifest", out, "--project", repo)
        self.assertEqual(code, 1)
        self.assertTrue(any("dirty" in x for x in res["drift"]), res)
        subprocess.run(git + ["commit", "-qam", "c2"], check=True, timeout=60)
        code, res = self.cli("check", "--manifest", out, "--project", repo)
        self.assertEqual(code, 1)
        self.assertTrue(any(x.startswith("project commit:") for x in res["drift"]), res)

    def test_out_creates_folders_and_unwritable_out_is_exit_2(self):
        out = self.d / "new" / "dir" / "m.json"
        code, doc = self.cli("record", "--packages", "pip", "--out", out)
        self.assertEqual(code, 0)
        self.assertTrue(out.is_file())
        blocker = self.d / "file"
        blocker.write_text("x")
        code, doc = self.cli("record", "--packages", "pip", "--out", blocker / "m.json")
        self.assertEqual((code, doc["status"]), (2, "error"))

    def test_printed_record_has_status_and_round_trips(self):
        p = subprocess.run([sys.executable, "-I", str(SCRIPT), "record", "--packages", "pip"], capture_output=True,
                           text=True, timeout=120)
        doc = json.loads(p.stdout)
        self.assertEqual(doc["status"], "recorded")
        (self.d / "printed.json").write_text(p.stdout)
        self.assertEqual(self.cli("check", "--manifest", self.d / "printed.json")[0], 0)

    def test_manifest_with_inputs_validates_as_a_computational_run(self):
        a = self.d / "in.dat"
        a.write_text("data")
        _, doc = self.recorded("--inputs", a)
        fixture = json.loads((ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "computational_run.json").read_text())
        fixture["extension"].update(input_manifest=doc["input_manifest"], tools=doc["tools"], environment=doc["environment"])
        art = self.d / "run.json"
        art.write_text(json.dumps(fixture))
        p = subprocess.run([sys.executable, str(ROOT / "contracts" / "validate.py"), str(art)], capture_output=True,
                           text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


class EnvironmentTemplateTests(unittest.TestCase):
    ADAPTER = ROOT / "adapters" / "environments"

    def test_declared_documented(self):
        doc = json.loads((self.ADAPTER / "adapter.json").read_text())
        self.assertEqual(doc["status"], "documented")
        self.assertTrue(all(t["status"] == "documented" and not t["tested_versions"] for t in doc["tools"]))
        for a in doc["assets"]:
            self.assertTrue((self.ADAPTER / a).is_file(), a)

    def test_lcg_setup_is_valid_sh_and_refuses_missing_view(self):
        sh = self.ADAPTER / "assets" / "lcg_view_setup.sh"
        self.assertEqual(subprocess.run(["sh", "-n", str(sh)], timeout=60).returncode, 0)
        r = subprocess.run(["sh", "-c", '. "$1"', "sh", str(sh)], capture_output=True, text=True, timeout=60)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stderr)

    def test_apptainer_def_sections(self):
        text = (self.ADAPTER / "assets" / "hep-research.def").read_text()
        self.assertIn("TEMPLATE", text)
        self.assertRegex(text, r"(?m)^Bootstrap: docker$")
        self.assertRegex(text, r"(?m)^From: rootproject/root:<ROOT_IMAGE_TAG>$")
        for section in ("%files", "%post", "%environment", "%labels", "%runscript"):
            self.assertRegex(text, rf"(?m)^{section}$")
        self.assertIn("requirements-ci.lock", text)
        self.assertTrue((ROOT / "requirements-ci.lock").is_file())


if __name__ == "__main__":
    unittest.main()
