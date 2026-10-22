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
                got = sa.affected_releases(adv, manifests)
                # fixed before the first manifest (0.5.0): only the earlier, unmanifested releases are affected
                self.assertTrue(got["releases"] or got["before_first_manifest"], got)

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
        # a nested key ('overlap_check' sits under extension.splits) can never match: the scan reads top-level keys
        self.assertIn("top-level property", broken(lambda a: a["applies_to"].update(extension_keys=["overlap_check"])))
        # a key of a variant extension schema (the communication traceability capability) is a top-level key
        self.assertNotIn("top-level property", broken(lambda a: a["applies_to"].update(
            artifact_types=["communication"], extension_keys=["occurrences"])))


class StricterCheck(unittest.TestCase):
    """Plan A0 and A3 (F-01, F-04, F-05, F-07, F-27): each new rule rejects its broken advisory; expected messages
    are written by hand."""

    def setUp(self):
        self.ledger = json.loads(sa.LEDGER.read_text())
        self.manifests = {"0.3.0": manifest(["contracts/validate.py"])}
        self.good = copy.deepcopy(ADVISORY)
        self.good["affected"][0]["paths"] = ["contracts/validate.py"]

    def problems(self, edit, manifests=None):
        adv = copy.deepcopy(self.good)
        edit(adv)
        return " ".join(sa.check([adv], self.ledger, manifests or self.manifests))

    def events(self, *events):
        return lambda a: a["affected"][0]["ranges"][0].update(events=list(events))

    def test_ranges(self):
        self.assertIn("not above the introduced", self.problems(self.events({"introduced": "0.3.0"}, {"fixed": "0.2.0"})))
        self.assertIn("not above the introduced", self.problems(self.events({"introduced": "0.2.0"},
                                                                            {"last_affected": "0.2.0"})))
        self.assertIn("two events at version 0.3.0", self.problems(self.events(
            {"introduced": "0.2.0"}, {"fixed": "0.3.0"}, {"introduced": "0.3.0"})))
        # a malformed version is a problem, not a ValueError from the range arithmetic
        self.assertIn("X.Y.Z", self.problems(self.events({"introduced": "0.x"}, {"fixed": "0.4.0"})))
        self.assertIn("X.Y.Z", self.problems(self.events({"introduced": "0.2.0"}, {"fixed": "0"})))
        self.assertEqual(self.problems(self.events({"introduced": "0"}, {"fixed": "0.4.0"})), "")

    def test_unknown_artifact_type(self):
        self.assertIn("not in the contracts' vocabulary", self.problems(
            lambda a: a["applies_to"].update(artifact_types=["no-such-type"])))

    def test_extension_keys_must_discriminate(self):
        # 'splits' is required by ext_ml_artifact, so every ml-artifact carries it; no key at all decides nothing
        self.assertIn("splits required for ml-artifact", self.problems(
            lambda a: a["applies_to"].update(extension_keys=["calibration", "splits"])))
        self.assertIn("no extension key", self.problems(lambda a: a["applies_to"].pop("extension_keys")))
        frozen = lambda a: a.update(id="SFA-2026-001", _file="SFA-2026-001.json")  # noqa: E731
        self.assertNotIn("cannot show", self.problems(lambda a: (frozen(a), a["applies_to"].pop("extension_keys"))))
        self.assertIn("remove it from NONDISCRIMINATING_ALLOWED", self.problems(frozen))

    def test_no_artifact_needs_outputs_in_every_block(self):
        def mark(a, outputs="prints JSON on stdout"):
            a["applies_to"]["extension_keys"] = ["tools"]
            a["applies_to"]["artifact_types"] = ["computational-run"]
            a["affected"][0]["database_specific"] = {"no_artifact": True, "outputs": outputs}
        self.assertEqual(self.problems(mark), "")
        self.assertIn("needs database_specific.outputs", self.problems(lambda a: mark(a, "")))
        self.assertIn("every affected block or none", self.problems(
            lambda a: (mark(a), a["affected"].append(copy.deepcopy(self.good["affected"][0])))))

    def test_fixed_release_changes_an_affected_file(self):
        def man(sha):
            return {"digest": "d" * 64, "paths": {"contracts/validate.py"}, "sha256": {"contracts/validate.py": sha}}
        events = self.events({"introduced": "0.2.0"}, {"fixed": "0.4.0"})
        same = {"0.2.0": man("a"), "0.3.0": man("a"), "0.4.0": man("a")}
        self.assertIn("fixed 0.4.0 changes no affected path against 0.3.0", self.problems(events, same))
        changed = dict(same, **{"0.4.0": man("b")})
        self.assertNotIn("changes no affected path", self.problems(events, changed))

    def test_introduced_release_that_already_held_the_file_says_why(self):
        mans = {"0.2.0": manifest(["contracts/validate.py"]), "0.3.0": manifest(["contracts/validate.py"])}
        events = self.events({"introduced": "0.3.0"}, {"fixed": "0.4.0"})
        self.assertIn("introduced_basis", self.problems(events, mans))
        self.assertNotIn("introduced_basis", self.problems(
            lambda a: (events(a), a["affected"][0].update(database_specific={"introduced_basis": "a later change"})),
            mans))
        # the file is new in the introduced release: nothing to explain
        self.assertNotIn("introduced_basis", self.problems(events, {"0.2.0": manifest(["core/other.py"]),
                                                                    "0.3.0": manifest(["contracts/validate.py"])}))

    def test_frozen_allowlist_only_shrinks(self):
        """F-27: no advisory joins the allowlist; PR-5 of the improvement plan empties it."""
        self.assertLessEqual(sa.NONDISCRIMINATING_ALLOWED, {
            "SFA-2026-001", "SFA-2026-002", "SFA-2026-004", "SFA-2026-006", "SFA-2026-010", "SFA-2026-020",
            "SFA-2026-023", "SFA-2026-025", "SFA-2026-030", "SFA-2026-031", "SFA-2026-033"})

    def test_scripts_without_artifacts_are_marked(self):
        """The shipped advisories whose affected scripts print JSON and write no artifact (F-02)."""
        marked = {a["id"] for a in sa.load_advisories() if sa.writes_no_artifact(a)}
        self.assertEqual(marked, {"SFA-2026-014", "SFA-2026-015", "SFA-2026-016", "SFA-2026-017", "SFA-2026-018",
                                  "SFA-2026-019", "SFA-2026-036", "SFA-2026-037"})


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
            "verified.json": ("digest-consistent", "affected"),
            "claimed.json": ("claimed", "affected"),
            "unreleased.json": ("claimed (unreleased build)",
                                "possibly affected (unreleased build: it may hold the fix)"),
            "mismatch.json": ("claimed (plugin_release digest differs from the release manifest)", "affected"),
            "unknown.json": ("unknown", "possibly affected (release unknown)"),
        })
        self.assertEqual(rep["advisories"], {"SFA-2026-901": {"releases_affected": ["0.2.0", "0.3.0"]}})
        legacy = {f["artifact"]: f.get("release_basis_legacy") for f in rep["findings"]}
        self.assertEqual(legacy["verified.json"], "verified")  # the former name, for one release
        self.assertIsNone(legacy["claimed.json"])

    def test_verdict_order_no_artifact_and_manifest_paths(self):
        """Plan A5: an advisory whose code writes no artifact is listed apart and matches nothing (the hadd job of
        F-01 and F-27); a release in range whose manifest lacks every affected path is not affected."""
        quiet = copy.deepcopy(ADVISORY)
        quiet.update(id="SFA-2026-902", applies_to={"artifact_types": ["computational-run"],
                                                    "extension_keys": ["tools"]}, remedy="rerun it")
        quiet["affected"][0]["database_specific"] = {"no_artifact": True, "outputs": "tool.py prints JSON"}
        self.artifact("hadd.json", {"plugin": "0.3.0", "plugin_release": {"release": "0.3.0", "digest": "b" * 64}},
                      artifact_type="computational-run", extension={"tools": [{"name": "hadd", "version": "6.32"}]})
        self.artifact("ml.json", {"plugin": "0.3.0", "plugin_release": {"release": "0.3.0", "digest": "b" * 64}})
        self.artifact("old.json", {"plugin": "0.1.5"})  # no manifest for 0.1.5: judged on the range alone
        manifests = dict(self.manifests, **{"0.2.0": manifest(["core/other.py"], "a" * 64)})
        self.artifact("moved.json", {"plugin": "0.2.0", "plugin_release": {"release": "0.2.0", "digest": "a" * 64}})
        wide = copy.deepcopy(ADVISORY)
        wide["affected"][0]["ranges"][0]["events"] = [{"introduced": "0.1.0"}, {"fixed": "0.4.0"}]
        rep = sa.scan(self.project, [wide, quiet], manifests)
        got = {(f["artifact"], f["advisory"]): f["verdict"] for f in rep["findings"]}
        self.assertEqual(got, {("ml.json", "SFA-2026-901"): "affected", ("old.json", "SFA-2026-901"): "affected"})
        self.assertEqual(rep["outputs_not_artifacts"], [{"advisory": "SFA-2026-902", "severity": "S2",
                                                         "releases_affected": ["0.3.0"],
                                                         "outputs": ["tool.py prints JSON"], "remedy": "rerun it"}])

    def test_shipped_no_artifact_advisories_skip_the_hadd_job(self):
        """F-01 / F-27 reproduction on the shipped advisories and manifests: a 0.21.0 merge job that only ran hadd,
        with a digest-consistent identity, is affected by nothing; SFA-2026-036 is listed apart."""
        manifests = sa.load_manifests()
        self.artifact("run.json", {"plugin": "0.21.0", "plugin_release": {"release": "0.21.0",
                                                                          "digest": manifests["0.21.0"]["digest"]}},
                      artifact_type="computational-run", extension={"tools": [{"name": "hadd", "version": "6.32"}]})
        rep = sa.scan(self.project, sa.load_advisories(), manifests)
        self.assertEqual([f for f in rep["findings"] if f["advisory"] in ("SFA-2026-036", "SFA-2026-014")], [])
        listed = {o["advisory"] for o in rep["outputs_not_artifacts"]}
        self.assertTrue({"SFA-2026-014", "SFA-2026-036", "SFA-2026-037"} <= listed, listed)

    def test_verdict_over_every_combination_of_the_five_steps(self):
        """Exhaustive oracle (sci-fix SCAN-VERDICT-ORDER): every combination of writes-no-artifact, type listed, key
        present and the release (in range and held, in range but the file absent from its manifest, in range without
        a manifest, out of range, unknown), 2 x 2 x 2 x 5 = 40 cases. The expected verdict is the plan's A5 rule
        written out here: listed apart when no artifact; otherwise nothing unless type and key match; then affected
        when the release is in range and its manifest (if any) holds the file, possibly affected when unknown."""
        import itertools
        releases = {"held": ("0.3.0", "b"), "absent": ("0.2.0", "a"), "unmanifested": ("0.2.5", None),
                    "out": ("0.4.0", "c"), "unknown": (None, None)}
        manifests = {"0.2.0": manifest(["core/other.py"], "a" * 64),
                     "0.3.0": manifest(["skills/hep-ml/scripts/tool.py"], "b" * 64),
                     "0.4.0": manifest(["skills/hep-ml/scripts/tool.py"], "c" * 64)}
        for quiet, typed, keyed, rel in itertools.product((False, True), (False, True), (False, True), releases):
            with self.subTest(no_artifact=quiet, type=typed, key=keyed, release=rel):
                for f in self.art.iterdir():
                    f.unlink()
                adv = copy.deepcopy(ADVISORY)
                adv["affected"][0]["ranges"][0]["events"] = [{"introduced": "0.2.0"}, {"fixed": "0.4.0"}]
                if quiet:
                    adv["affected"][0]["database_specific"] = {"no_artifact": True, "outputs": "stdout"}
                version, digest = releases[rel]
                versions = {} if version is None else {"plugin": version}
                if digest:
                    versions["plugin_release"] = {"release": version, "digest": digest * 64}
                self.artifact("a.json", versions, artifact_type="ml-artifact" if typed else "statistical-result",
                              extension={"calibration": {"m": 1}} if keyed else {"other": 1})
                rep = sa.scan(self.project, [adv], manifests)
                verdicts = [f["verdict"] for f in rep["findings"]]
                listed = [o["advisory"] for o in rep.get("outputs_not_artifacts", [])]
                if quiet:
                    self.assertEqual((verdicts, listed), ([], ["SFA-2026-901"]))
                    continue
                self.assertEqual(listed, [])
                if not (typed and keyed) or rel in ("absent", "out"):
                    want = []
                elif rel == "unknown":
                    want = ["possibly affected (release unknown)"]
                else:
                    want = ["affected"]
                self.assertEqual(verdicts, want)

    def test_missing_markers_and_empty_values_do_not_show_the_code_ran(self):
        """Exhaustive oracle (sci-fix SCAN-MISSING-MARKER, plan A4/F-06): every value class a valid extension key can
        hold. A missing marker (contracts/vocab/core.json: unknown, not-applicable, not-provided; written out here),
        null, false and an empty object or list mean the key says nothing; any other value is present. A
        measurement-spec may record blinding as a marker (its schema: anyOf object or missing marker)."""
        values = {"unknown": False, "not-applicable": False, "not-provided": False, None: False, False: False,
                  "{}": False, "[]": False, "object": True, "list": True, "text": True, "Unknown": True, "0": True,
                  "1.5": True, "true": True}
        concrete = {"{}": {}, "[]": [], "object": {"method": "x"}, "list": ["a"], "text": "hidden-box",
                    "0": 0, "1.5": 1.5, "true": True}
        adv = copy.deepcopy(ADVISORY)
        adv["applies_to"] = {"artifact_types": ["measurement-spec"], "extension_keys": ["blinding"]}
        for label, touched in values.items():
            with self.subTest(value=label):
                for f in self.art.iterdir():
                    f.unlink()
                value = concrete.get(label, label)
                self.artifact("spec.json", {"plugin": "0.3.0"}, artifact_type="measurement-spec",
                              extension={"blinding": value})
                rep = sa.scan(self.project, [adv], self.manifests)
                self.assertEqual([f["verdict"] for f in rep["findings"]], ["affected"] if touched else [])

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
