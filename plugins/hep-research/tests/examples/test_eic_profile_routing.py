"""experiment:eic usage example: a project config selects the profile, each routing scenario reads only the files
the index names, a wrong version pin is rejected, no other profile's file is opened, the detector atlas reaches the
profile (bound rows for ePIC and EIC, see_profile for unbound names), and the run is reproducible."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._outputs import without_writer_versions

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "eic-profile-routing" / "run.py"
COMMITTED = PLUGIN / "examples" / "eic-profile-routing" / "output" / "results.json"


class EicRoutingExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.proc = subprocess.run([sys.executable, str(SCRIPT), "--out", str(cls.out)], capture_output=True, text=True, timeout=1200)
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

    def test_bound_epic_atlas_query_returns_profile_rows(self):
        by = {(q["binding"], q["experiment"]): q for q in self.r["atlas_queries"]}
        rows = [r for r in by[("bound", "ePIC")]["rows"] if r["origin"] == "bound experiment profile"]
        self.assertGreaterEqual(len(rows), 1)

    def test_bound_eic_atlas_query_matches_the_ledger(self):
        ledger = json.loads((PLUGIN / "profiles" / "experiments" / "eic" / "evidence" / "claims.json").read_text(encoding="utf-8"))
        has_eic = any(c.get("atlas", {}).get("experiment") == "EIC" for c in ledger)
        by = {(q["binding"], q["experiment"]): q for q in self.r["atlas_queries"]}
        rows = [r for r in by[("bound", "EIC")]["rows"] if r["origin"] == "bound experiment profile"]
        if has_eic:
            self.assertGreaterEqual(len(rows), 1)
        else:
            self.assertEqual(rows, [])
            self.skipTest("blocked: no eic claim carries an atlas block with experiment EIC")

    def test_unbound_atlas_queries_point_to_the_profile(self):
        unbound = [q for q in self.r["atlas_queries"] if q["binding"] == "unbound"]
        self.assertEqual(sorted(q["experiment"] for q in unbound), ["EIC", "Electron-Ion Collider", "ePIC"])
        for q in unbound:
            self.assertEqual(q.get("see_profile"), "experiment:eic", q)

    def test_committed_output_is_reproduced(self):
        fresh = json.loads((self.out / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(without_writer_versions(fresh), without_writer_versions(json.loads(COMMITTED.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    unittest.main()
