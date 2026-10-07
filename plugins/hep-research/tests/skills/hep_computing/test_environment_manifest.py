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
