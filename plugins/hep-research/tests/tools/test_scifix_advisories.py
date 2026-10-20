"""tools/scifix_advisories.py (plan PR-7, shadow mode): the shipped advisories against the ledger, the plugin tree and
the release manifests; OSV range semantics; affected releases from manifests (with a skill-folder rename); the
read-only project scan and its release basis. Synthetic manifests and artifacts; the expected verdicts are written
out by hand in each test, not taken from the tool."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "scifix_advisories.py"
sys.path.insert(0, str(ROOT / "tools"))
import scifix_advisories as sa  # noqa: E402


def manifest(paths, digest="d" * 64):
    return {"digest": digest, "paths": set(paths)}


ADVISORY = {"format": sa.FORMAT, "id": "SFA-2026-901", "severity": "S2", "ledger": ["BLINDING-ROUNDING-ZEROS"],
            "summary": "synthetic", "_file": "SFA-2026-901.json",
            "affected": [{"paths": ["skills/hep-ml/scripts/tool.py"],
                          "ranges": [{"type": "SEMVER", "events": [{"introduced": "0.2.0"}, {"fixed": "0.4.0"}]}]}],
            "impact": {"observables": ["x"], "bias": "y", "trigger": "z"},
            "applies_to": {"artifact_types": ["ml-artifact"], "extension_keys": ["calibration"]}}


class ShippedAdvisories(unittest.TestCase):
    def test_every_advisory_passes_the_check_and_affects_a_release(self):
        advisories, manifests = sa.load_advisories(), sa.load_manifests()
        self.assertTrue(advisories)
        self.assertEqual(sa.check(advisories, json.loads(sa.LEDGER.read_text()), manifests), [])
        for adv in advisories:
            with self.subTest(adv=adv["id"]):
                self.assertTrue(sa.affected_releases(adv, manifests)["releases"])

    def test_cli_check_and_affected_exit_zero(self):
        for cmd in (["check"], ["affected"], ["affected", "--id", "SFA-2026-001"]):
            p = subprocess.run([sys.executable, str(TOOL), *cmd], capture_output=True, text=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stdout)
            self.assertEqual(json.loads(p.stdout)["status"], "passed")
        p = subprocess.run([sys.executable, str(TOOL), "affected", "--id", "SFA-1999-000"], capture_output=True,
                           text=True, timeout=120)
        self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"))


class OsvRanges(unittest.TestCase):
    def test_introduced_fixed_and_last_affected(self):
        cases = [
            ([{"introduced": "0"}], {"0.1.0": True, "9.9.9": True}),
            ([{"introduced": "0.2.0"}], {"0.1.9": False, "0.2.0": True, "1.0.0": True}),
            ([{"introduced": "0.2.0"}, {"fixed": "0.4.0"}], {"0.1.0": False, "0.2.0": True, "0.3.9": True,
                                                              "0.4.0": False, "0.5.0": False}),
            ([{"introduced": "0.2.0"}, {"last_affected": "0.3.1"}], {"0.3.1": True, "0.3.2": False}),
            ([{"introduced": "0.1.0"}, {"fixed": "0.2.0"}, {"introduced": "0.5.0"}],  # reintroduced
             {"0.1.5": True, "0.3.0": False, "0.5.0": True, "0.10.0": True}),
            ([{"introduced": "0.9.0"}, {"fixed": "0.10.0"}], {"0.9.5": True, "0.10.0": False, "0.11.0": False}),
        ]
        for events, expected in cases:
            for version, want in expected.items():
                with self.subTest(events=events, version=version):
                    self.assertEqual(sa.in_range(version, events), want)


class AffectedReleases(unittest.TestCase):
    def test_releases_in_range_that_hold_a_path_including_a_renamed_skill_folder(self):
        manifests = {"0.1.0": manifest(["skills/old-ml/scripts/tool.py"]),
                     "0.2.0": manifest(["skills/old-ml/scripts/tool.py"]),       # before the rename
                     "0.3.0": manifest(["skills/hep-ml/scripts/tool.py"]),       # after it
                     "0.3.5": manifest(["core/other.py"]),                       # the file is not in this release
                     "0.4.0": manifest(["skills/hep-ml/scripts/tool.py"])}       # fixed
        got = sa.affected_releases(ADVISORY, manifests)
        self.assertEqual(got["releases"], ["0.2.0", "0.3.0"])
        self.assertFalse(got["before_first_manifest"])
        ambiguous = dict(manifests, **{"0.3.0": manifest(["skills/a/scripts/tool.py", "skills/b/scripts/tool.py"])})
        self.assertEqual(sa.affected_releases(ADVISORY, ambiguous)["releases"], ["0.2.0"])
        early = copy.deepcopy(ADVISORY)
        early["affected"][0]["ranges"][0]["events"][0] = {"introduced": "0"}
        later = {v: m for v, m in manifests.items() if v != "0.1.0"}
        self.assertTrue(sa.affected_releases(early, later)["before_first_manifest"])


class CheckProblems(unittest.TestCase):
    def test_each_kind_of_broken_advisory_is_reported(self):
        ledger = json.loads(sa.LEDGER.read_text())
        manifests = {"0.3.0": manifest(["contracts/validate.py"])}
        good = copy.deepcopy(ADVISORY)
        good["affected"][0]["paths"] = ["contracts/validate.py"]
        self.assertEqual(sa.check([good], ledger, manifests), [])

        def broken(edit):
            adv = copy.deepcopy(good)
            edit(adv)
            return " ".join(sa.check([adv], ledger, manifests))

        self.assertIn("id must be", broken(lambda a: a.update(id="SFA-26-1")))
        self.assertIn("not in", broken(lambda a: a.update(ledger=["NO-SUCH-FIX"])))
        self.assertIn("differs", broken(lambda a: a.update(severity="S1")))
        self.assertIn("observables", broken(lambda a: a["impact"].pop("bias")))
        self.assertIn("not a file", broken(lambda a: a["affected"][0].update(paths=["core/missing.py"])))
        self.assertIn("X.Y.Z", broken(lambda a: a["affected"][0]["ranges"][0]["events"].append({"fixed": "1.0"})))
        self.assertIn("fixed_commit", broken(lambda a: a["affected"][0]["ranges"][0]["events"].pop()))
        self.assertIn("no release", broken(lambda a: a["affected"][0]["ranges"][0].update(
            events=[{"introduced": "0.9.0"}, {"fixed": "1.0.0"}])))
        self.assertIn("duplicate", " ".join(sa.check([good, copy.deepcopy(good)], ledger, manifests)))


class ProjectScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        self.art = self.project / "results"
        self.art.mkdir()
        (self.project / sa.CONFIG_NAME).write_text(json.dumps({"artifacts_dir": "results"}))
        self.manifests = {"0.2.0": manifest(["skills/hep-ml/scripts/tool.py"], "a" * 64),
                          "0.3.0": manifest(["skills/hep-ml/scripts/tool.py"], "b" * 64),
                          "0.4.0": manifest(["skills/hep-ml/scripts/tool.py"], "c" * 64)}

    def tearDown(self):
        self.tmp.cleanup()

    def artifact(self, name, versions, artifact_type="ml-artifact", extension=None):
        doc = {"artifact_type": artifact_type, "versions": versions,
               "extension": {"calibration": {"method": "x"}} if extension is None else extension}
        (self.art / name).write_text(json.dumps(doc))

    def test_release_basis_and_verdicts(self):
        self.artifact("verified.json", {"plugin": "0.3.0", "plugin_release": {"release": "0.3.0", "digest": "b" * 64}})
        self.artifact("claimed.json", {"plugin": "0.2.0"})
        self.artifact("unreleased.json", {"plugin": "0.3.0", "plugin_release": {"release": "unreleased",
                                                                                "digest": "unknown"}})
        self.artifact("mismatch.json", {"plugin": "0.3.0", "plugin_release": {"release": "0.3.0", "digest": "e" * 64}})
        self.artifact("unknown.json", {})
        self.artifact("fixed.json", {"plugin": "0.4.0", "plugin_release": {"release": "0.4.0", "digest": "c" * 64}})
        self.artifact("other_type.json", {"plugin": "0.3.0"}, artifact_type="statistical-result")
        self.artifact("no_key.json", {"plugin": "0.3.0"}, extension={"overlap_check": {"passed": True}})
        (self.art / "table.json").write_text(json.dumps({"rows": [1, 2]}))
        (self.art / "broken.json").write_text("{not json")
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.project.rglob("*") if p.is_file()}
        rep = sa.scan(self.project, [ADVISORY], self.manifests)
        after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.project.rglob("*") if p.is_file()}
        self.assertEqual(before, after)  # read-only
        self.assertEqual((rep["status"], rep["mode"], rep["artifacts_scanned"]), ("passed", "shadow", 8))
        self.assertEqual(rep["unreadable"], ["broken.json"])
        got = {f["artifact"]: (f["release_basis"], f["verdict"]) for f in rep["findings"]}
        self.assertEqual(got, {
            "verified.json": ("verified", "affected"),
            "claimed.json": ("claimed", "affected"),
            "unreleased.json": ("claimed (unreleased build)",
                                "possibly affected (unreleased build: it may hold the fix)"),
            "mismatch.json": ("claimed (plugin_release digest differs from the release manifest)", "affected"),
            "unknown.json": ("unknown", "possibly affected (release unknown)"),
        })
        self.assertEqual(rep["advisories"], {"SFA-2026-901": {"releases_affected": ["0.2.0", "0.3.0"]}})

    def test_default_artifacts_dir_and_cli_exit_codes(self):
        (self.project / sa.CONFIG_NAME).unlink()
        (self.project / "hep-research-artifacts").mkdir()
        rep = sa.scan(self.project, [ADVISORY], self.manifests)
        self.assertTrue(rep["artifacts_dir"].endswith("hep-research-artifacts"))
        self.assertEqual((rep["artifacts_scanned"], rep["findings"]), (0, []))
        p = subprocess.run([sys.executable, str(TOOL), "scan", str(self.project)], capture_output=True, text=True,
                           timeout=120)
        self.assertEqual((p.returncode, json.loads(p.stdout)["mode"]), (0, "shadow"))
        p = subprocess.run([sys.executable, str(TOOL), "scan", str(self.project / "missing")], capture_output=True,
                           text=True, timeout=120)
        self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"))


if __name__ == "__main__":
    unittest.main()
