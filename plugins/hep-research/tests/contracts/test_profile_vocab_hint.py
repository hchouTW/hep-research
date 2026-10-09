"""Profile-prefixed vocabulary terms: without the profile bound, validate.py says which flag is missing; with it, the
shipped AMS example artifacts validate (they use the profile's 'crflux:' level terms)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATE = ROOT / "contracts" / "validate.py"
ARTIFACTS = ROOT / "examples" / "ams-flux-ratio" / "output" / "artifacts"
AMS_PROFILE = ROOT / "profiles" / "experiments" / "ams-02" / "profile.json"


def run(*args):
    r = subprocess.run([sys.executable, str(VALIDATE), *map(str, args)], capture_output=True, text=True, timeout=120)
    return r.returncode, json.loads(r.stdout)


@unittest.skipUnless(ARTIFACTS.is_dir() and AMS_PROFILE.is_file(),
                     "the AMS profile and its example are optional (tools/check_ams_optional.py removes them)")
class ProfileVocabHint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = Path(self.tmp.name) / "hep-research.project.json"
        self.config.write_text(json.dumps({"schema_version": "1.1.0", "plugin_version": ">=0.1.0",
                                           "experiments": [{"profile": "experiment:ams-02", "version": "2.0.0"}]}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_prefixed_term_without_profile_names_the_flag(self):
        rc, rep = run(ARTIFACTS / "measurement_spec.json")
        self.assertEqual(rc, 1)
        msgs = [f["message"] for f in rep["findings"] if f["code"] == "vocab.unknown_term"]
        self.assertTrue(msgs)
        self.assertTrue(all("--profiles-from" in m and "'crflux:'" in m for m in msgs))

    def test_unprefixed_unknown_term_has_no_profile_hint(self):
        doc = json.loads((ARTIFACTS / "measurement_spec.json").read_text())
        doc["extension"]["observable"]["level"] = "no-such-level"
        p = Path(self.tmp.name) / "bad.json"
        p.write_text(json.dumps(doc))
        rc, rep = run(p, "--profiles-from", self.config)
        msgs = [f["message"] for f in rep["findings"] if f["code"] == "vocab.unknown_term"]
        self.assertEqual(rc, 1)
        self.assertTrue(msgs and not any("--profiles-from" in m for m in msgs))

    def test_shipped_ams_example_artifacts_validate_with_the_profile(self):
        for art in sorted(ARTIFACTS.glob("*.json")):
            with self.subTest(artifact=art.name):
                rc, rep = run(art, "--profiles-from", self.config)
                self.assertEqual(rc, 0, rep["findings"])


if __name__ == "__main__":
    unittest.main()
