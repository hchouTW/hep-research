"""experiment:eic usage example: a project config selects the profile, each routing scenario reads only the files
the index names, a wrong version pin is rejected, no other profile's file is opened, and the run is reproducible."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "eic-profile-routing" / "run.py"
COMMITTED = PLUGIN / "examples" / "eic-profile-routing" / "output" / "results.json"


class EicRoutingExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.proc = subprocess.run([sys.executable, str(SCRIPT), "--out", str(cls.out)], capture_output=True, text=True)
        cls.r = json.loads((cls.out / "results.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_exit_zero_and_pass(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stdout + self.proc.stderr)
        self.assertTrue(self.r["pass"], self.r)

    def test_project_config_selects_eic_only(self):
        self.assertEqual(self.r["project_config"]["experiments"], [{"profile": "experiment:eic", "version": self.r["profile"]["version"]}])
        self.assertEqual(self.r["project_config"]["theory"], [])

    def test_each_scenario_reads_only_its_expected_files(self):
        for s in self.r["scenarios"]:
            with self.subTest(s["id"]):
                self.assertTrue(s["pass"], s)
                self.assertEqual(s["files_read"], s["expected_files"])

    def test_no_other_profile_module_is_opened(self):
        self.assertEqual(self.r["foreign_profile_files_read"], [])
        for p in self.r["profile_files_read"]:
            self.assertTrue(p.startswith("profiles/experiments/eic/") or p == "profiles/registry.json" or p.endswith("/profile.json"), p)

    def test_generic_dis_and_ambiguous_read_nothing(self):
        by = {s["id"]: s for s in self.r["scenarios"]}
        self.assertEqual(by["generic-dis"]["files_read"], [])
        self.assertEqual(by["ambiguous-detector"]["decision"], "ask")
        self.assertEqual(by["ambiguous-detector"]["files_read"], [])

    def test_wrong_version_pin_is_rejected(self):
        self.assertTrue(self.r["wrong_pin_rejected"])

    def test_project_config_selects_the_profile_when_the_request_names_none(self):
        sel = self.r["project_config_selection"]
        self.assertEqual(sel["decision"], "use")
        self.assertEqual(sel["source"], "project-config")
        self.assertEqual(sel["experiments"], ["experiment:eic"])

    def test_committed_output_is_reproduced_byte_for_byte(self):
        self.assertEqual((self.out / "results.json").read_bytes(), COMMITTED.read_bytes())


if __name__ == "__main__":
    unittest.main()
