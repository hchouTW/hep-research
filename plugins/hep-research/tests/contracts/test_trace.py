"""contracts/trace.py (contracts 3.5.0; sci-fix improvement plan A1 change 2): the execution trace an envelope records.
code_paths is a snapshot of the plugin modules a process had loaded (the test suite left out); code_tags are per
envelope, so a second artifact written by the same process does not carry the first one's tags; a producer run as a
subprocess records its own script; the schema accepts the fields and refuses malformed ones."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import trace  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

FIXTURE = json.loads((ROOT / "contracts/fixtures/artifacts/valid/computational_run.json").read_text())


class CodePaths(unittest.TestCase):
    def test_loaded_plugin_modules_only(self):
        paths = trace.code_paths()
        self.assertIn("contracts/trace.py", paths)
        self.assertIn("contracts/validate.py", paths)
        self.assertFalse([p for p in paths if p.startswith("tests/")], "the test suite is left out")
        self.assertFalse([p for p in paths if p.startswith("/") or not p.endswith(".py")])
        self.assertEqual(paths, sorted(set(paths), key=lambda p: p.encode("utf-8")))

    def test_another_root_sees_nothing_of_this_plugin(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(trace.code_paths(Path(td)), [])


class CodeTags(unittest.TestCase):
    def setUp(self):
        trace.provenance()  # start from no tags

    def test_tags_belong_to_one_envelope(self):
        trace.tag("species-masses")
        trace.tag("species-masses")
        trace.tag("bethe-dedx")
        first = trace.provenance()
        self.assertEqual(first["code_tags"], ["bethe-dedx", "species-masses"])
        trace.tag("log-cls")
        self.assertEqual(trace.provenance()["code_tags"], ["log-cls"])
        self.assertEqual(trace.provenance()["code_tags"], [])

    def test_tag_names_are_checked(self):
        for bad in ("", "Species", "a b", "-x", "x_y"):
            with self.subTest(tag=bad), self.assertRaises(ValueError):
                trace.tag(bad)


class EnvelopeSchema(unittest.TestCase):
    def test_fields_are_optional_and_checked(self):
        doc = copy.deepcopy(FIXTURE)
        self.assertTrue(validate_artifact(doc).ok)  # older artifacts have neither field
        doc["provenance"].update(trace.provenance())
        self.assertTrue(validate_artifact(doc).ok)
        for field, bad in (("code_paths", ["/abs/x.py"]), ("code_paths", ["core/x.txt"]),
                           ("code_paths", ["../outside.py"]), ("code_tags", ["Bad Tag"]), ("code_tags", "x")):
            with self.subTest(field=field, value=bad):
                broken = copy.deepcopy(doc)
                broken["provenance"][field] = bad
                self.assertFalse(validate_artifact(broken).ok)


class ProducerSubprocess(unittest.TestCase):
    def test_a_producer_records_its_own_script(self):
        lm = ROOT / "skills/hep-statistics/scripts/li_ma_significance.py"
        ra = ROOT / "skills/hep-statistics/scripts/result_artifact.py"
        with tempfile.TemporaryDirectory() as td:
            out = subprocess.run([sys.executable, str(lm), "--on", "30", "--off", "100", "--alpha", "0.1"],
                                 capture_output=True, text=True, timeout=120)
            (Path(td) / "lm.json").write_text(out.stdout)
            cp = subprocess.run([sys.executable, str(ra), "--cli-output", str(Path(td) / "lm.json"), "--poi", "s",
                                 "--construction", "asymptotic", "--test-statistic", "li-ma", "--label", "synthetic",
                                 "--artifact-id", "trace-probe", "--out", str(Path(td) / "r.json")],
                                capture_output=True, text=True, timeout=120)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            prov = json.loads((Path(td) / "r.json").read_text())["provenance"]
        self.assertIn("skills/hep-statistics/scripts/result_artifact.py", prov["code_paths"])
        self.assertNotIn("skills/hep-statistics/scripts/li_ma_significance.py", prov["code_paths"])  # its own process
        self.assertEqual(prov["code_tags"], [])


class TraceForwarding(unittest.TestCase):
    """A core/stats CLI prints its own trace; result_artifact.py, which wraps that output in another process, joins it,
    so a statistical-result shows which core/stats code produced its numbers."""
    PD = ROOT / "core/stats/poisson_diagnostics.py"
    RA = ROOT / "skills/hep-statistics/scripts/result_artifact.py"

    def wrap(self, td, cli):
        (Path(td) / "cli.json").write_text(json.dumps(cli))
        cp = subprocess.run([sys.executable, str(self.RA), "--cli-output", str(Path(td) / "cli.json"), "--poi", "s",
                             "--construction", "feldman-cousins", "--test-statistic", "likelihood-ratio-ordering",
                             "--label", "synthetic", "--artifact-id", "trace-forward", "--out", str(Path(td) / "r.json")],
                            capture_output=True, text=True, timeout=120)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return json.loads((Path(td) / "r.json").read_text())

    def test_the_cli_trace_reaches_the_artifact(self):
        out = subprocess.run([sys.executable, str(self.PD), "fc-interval", "--n", "3", "--b", "1.0"],
                             capture_output=True, text=True, timeout=120)
        cli = json.loads(out.stdout)
        self.assertIn("core/stats/poisson_diagnostics.py", cli["trace"]["code_paths"])
        with tempfile.TemporaryDirectory() as td:
            doc = self.wrap(td, cli)
        paths = doc["provenance"]["code_paths"]
        self.assertIn("core/stats/poisson_diagnostics.py", paths)
        self.assertIn("skills/hep-statistics/scripts/result_artifact.py", paths)
        self.assertEqual(paths, sorted(set(paths), key=lambda p: p.encode("utf-8")))
        self.assertNotIn("trace", doc["extension"]["results"])
        self.assertTrue(validate_artifact(doc).ok)

    def test_malformed_cli_trace_entries_are_dropped(self):
        cli = {"status": "ok", "upper": 4.2, "trace": {"code_paths": ["/etc/x.py", "../out.py", "core/a.txt", 7,
                                                                      "core/stats/x.py"],
                                                       "code_tags": ["Bad Tag", "fc-monotone"]}}
        with tempfile.TemporaryDirectory() as td:
            prov = self.wrap(td, cli)["provenance"]
        self.assertIn("core/stats/x.py", prov["code_paths"])
        self.assertFalse([p for p in prov["code_paths"] if p.startswith(("/", "..")) or not p.endswith(".py")])
        self.assertEqual(prov["code_tags"], ["fc-monotone"])
        with tempfile.TemporaryDirectory() as td:
            prov = self.wrap(td, {"status": "ok", "upper": 4.2, "trace": "not a trace"})["provenance"]
        self.assertNotIn("core/stats/poisson_diagnostics.py", prov["code_paths"])


if __name__ == "__main__":
    unittest.main()
