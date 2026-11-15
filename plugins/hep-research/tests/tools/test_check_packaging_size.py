"""tools/check_packaging.py size statement: the README's "about N files, X MB uncompressed" must stay within 10% of
the upload zip it describes (`git archive HEAD:plugins/hep-research`, which leaves out every path marked export-ignore);
a drift fails, and so does a zip over the documented upload limits (5,000 files, 200 MB)."""
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("check_packaging", PLUGIN / "tools" / "check_packaging.py")
cp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cp)


class SizeStatementTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.old = cp.ROOT
        cp.ROOT = self.root
        self.files = []
        for i in range(20):
            p = self.root / f"f{i}.txt"
            p.write_bytes(b"x" * 50_000)  # 20 files, 1.0 MB
            self.files.append(p)

    def tearDown(self):
        cp.ROOT = self.old
        self.td.cleanup()

    def readme(self, text):
        (self.root / "README.md").write_text(text, encoding="utf-8")
        return self.files + [self.root / "README.md"]

    def test_matching_statement_passes(self):
        self.assertEqual(cp.size_drift(self.readme("The plugin (about 21 files, 1.0 MB\n   uncompressed) fits.")), [])

    def test_drift_fails_for_count_and_size(self):
        problems = cp.size_drift(self.readme("The plugin (about 15 files, 0.6 MB uncompressed) fits."))
        self.assertEqual(len(problems), 2, problems)

    def test_missing_statement_fails(self):
        self.assertTrue(cp.size_drift(self.readme("No size here.")))

    def test_the_plugin_readme_is_within_margin(self):
        cp.ROOT = self.old
        self.assertEqual(cp.size_drift(cp.files()), [])

    def test_export_ignored_paths_are_not_counted(self):
        # 20 shipped files plus 30 under tests/ and docs/dev/: the README describes the 21 that git archive keeps
        for folder in ("tests", "docs/dev/notes"):
            for i in range(15):
                p = self.root / folder / f"t{i}.txt"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"y" * 50_000)
                self.files.append(p)
        (self.root / ".gitattributes").write_text("* text eol=lf\n/tests/ export-ignore\ndocs/dev/ export-ignore\n")
        fl = self.readme("The plugin (about 22 files, 1.0 MB uncompressed) fits.") + [self.root / ".gitattributes"]
        self.assertEqual(cp.size_drift(fl), [])
        kept = {p.relative_to(self.root).as_posix() for p in cp.upload_files(fl)}
        self.assertNotIn("tests/t0.txt", kept)
        self.assertNotIn("docs/dev/notes/t0.txt", kept)
        self.assertIn(".gitattributes", kept)

    def test_unanchored_directory_pattern_matches_at_any_depth(self):
        rels = ["tests/a.py", "x/tests/b.py", "x/y.py", "docs/dev/c.md", "z/docs/dev/d.md", "e.log", "f/g.log"]
        for rel in rels:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text("x")
        (self.root / ".gitattributes").write_text("# comment\ntests/ export-ignore\ndocs/dev/ export-ignore\n*.log export-ignore\n"
                                                  "x/y.py -export-ignore\n")
        fl = [self.root / r for r in rels] + [self.root / ".gitattributes"]
        kept = {p.relative_to(self.root).as_posix() for p in cp.upload_files(fl)}
        # git: a pattern with no inner slash matches at any depth; one with an inner slash is anchored to its folder
        self.assertEqual(kept, {"x/y.py", "z/docs/dev/d.md", ".gitattributes"})

    def test_nested_gitattributes_apply_below_their_folder(self):
        rels = ["a/b/c.txt", "a/d.txt", "b/c.txt"]
        for rel in rels:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text("x")
        (self.root / "a" / ".gitattributes").write_text("/b/ export-ignore\n")
        fl = [self.root / r for r in rels] + [self.root / "a" / ".gitattributes"]
        kept = {p.relative_to(self.root).as_posix() for p in cp.upload_files(fl)}
        self.assertEqual(kept, {"a/d.txt", "b/c.txt", "a/.gitattributes"})

    def test_upload_limits_fail_even_when_the_statement_matches(self):
        old = (cp.MAX_UPLOAD_ENTRIES, cp.MAX_UPLOAD_BYTES)
        try:
            cp.MAX_UPLOAD_ENTRIES, cp.MAX_UPLOAD_BYTES = 10, 500_000
            problems = cp.size_drift(self.readme("The plugin (about 21 files, 1.0 MB uncompressed) fits."))
        finally:
            cp.MAX_UPLOAD_ENTRIES, cp.MAX_UPLOAD_BYTES = old
        self.assertEqual(len(problems), 2, problems)
        self.assertTrue(any("5,000" in p or "entries" in p for p in problems), problems)

    def test_documented_limits(self):
        self.assertEqual((cp.MAX_UPLOAD_ENTRIES, cp.MAX_UPLOAD_BYTES), (5000, 200 * 10**6))

    def test_folder_entries_count_toward_the_entry_limit(self):
        # git archive writes one entry per folder too: 3 files in 2 nested folders are 5 zip entries
        rels = ["p/q/r.txt", "p/q/s.txt", "p/t.txt"]
        for rel in rels:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text("x")
        self.assertEqual(cp.zip_entries([self.root / r for r in rels]), 5)


@unittest.skipUnless(shutil.which("git"), "needs git")
class AgreesWithGitTests(unittest.TestCase):
    def test_export_ignore_reading_agrees_with_git_check_attr(self):
        """The plugin's own reading of .gitattributes leaves out exactly the files git marks export-ignore (the file
        itself or one of its folders), on the real plugin tree."""
        fl = [p for p in cp.files() if p.is_file()]
        rels = [p.relative_to(PLUGIN).as_posix() for p in fl]
        probe = sorted({r for rel in rels for r in [rel] + [str(Path(*Path(rel).parts[:k])) + "/" for k in range(1, len(Path(rel).parts))]})
        res = subprocess.run(["git", "check-attr", "-z", "--stdin", "export-ignore"], cwd=PLUGIN, input="\0".join(probe),
                             capture_output=True, text=True, timeout=300)
        if res.returncode != 0:
            self.skipTest("not a git checkout")
        out = res.stdout.split("\0")
        ignored = {out[i] for i in range(0, len(out) - 2, 3) if out[i + 2] == "set"}
        git_kept = {rel for rel in rels if rel not in ignored
                    and not any(str(Path(*Path(rel).parts[:k])) + "/" in ignored for k in range(1, len(Path(rel).parts)))}
        ours = {p.relative_to(PLUGIN).as_posix() for p in cp.upload_files(fl)}
        self.assertEqual(ours, git_kept)
        kept_tests = {r for r in ours if r.startswith("tests/")}
        self.assertIn("tests/examples/test_qed_prediction.py", kept_tests)       # a test a profile capability cites
        self.assertIn("tests/adapters/batch_shims/sbatch", kept_tests)          # run by examples/batch-partition
        self.assertNotIn("tests/tools/test_check_packaging_size.py", kept_tests)
        self.assertLess(len(kept_tests), 100)                                   # most of tests/ is left out
        self.assertTrue(any(r.startswith("docs/dev/") for r in ours))           # docs/dev ships
        self.assertTrue(any(r.startswith("adapters/geant4/tests/") for r in ours))  # only the top-level tests/ is left out

    def test_the_plugin_has_no_unresolved_shipped_reference(self):
        fl = cp.files()
        self.assertEqual(cp.unresolved_references(fl, cp.upload_files(fl)), [])


class ShippedReferenceTests(unittest.TestCase):
    """Every runtime reference from a shipped file into tests/ (or docs/dev/) resolves inside the upload zip."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.old = cp.ROOT
        cp.ROOT = self.root

    def tearDown(self):
        cp.ROOT = self.old
        self.scratch.cleanup()

    def tree(self, files, attributes="/tests/** export-ignore\n"):
        files = dict(files, **{".gitattributes": attributes})
        for rel, body in files.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(body, encoding="utf-8")
        fl = [self.root / rel for rel in files]
        return cp.unresolved_references(fl, cp.upload_files(fl))

    def profile(self, tests):
        return json.dumps({"id": "experiment:x", "capabilities": [{"name": "c", "status": "demonstrated", "tests": tests}]})

    def test_a_profile_capability_test_left_out_is_reported(self):
        found = self.tree({"profiles/experiments/x/profile.json": self.profile(["../../../tests/examples/test_x.py"]),
                           "tests/examples/test_x.py": "pass\n"})
        self.assertEqual(len(found), 1, found)
        self.assertEqual(found[0][0], "profiles/experiments/x/profile.json")
        self.assertIn("tests/examples/test_x.py", found[0][1])

    def test_a_kept_profile_capability_test_passes(self):
        found = self.tree({"profiles/experiments/x/profile.json": self.profile(["../../../tests/examples/test_x.py", "tests/own.py"]),
                           "profiles/experiments/x/tests/own.py": "pass\n", "tests/examples/test_x.py": "pass\n"},
                          "/tests/** export-ignore\n/tests/examples -export-ignore\n/tests/examples/test_x.py -export-ignore\n")
        self.assertEqual(found, [])

    def test_a_plugin_root_path_constant_into_tests_is_resolved(self):
        code = ("from pathlib import Path\nHERE = Path(__file__).resolve().parent\nADAPTER = HERE.parent\n"
                "PLUGIN_ROOT = ADAPTER.parents[1]\nDEFAULT = PLUGIN_ROOT / \"tests\" / \"fixtures\" / \"model.json\"\n")
        files = {"adapters/a/assets/provider.py": code, "tests/fixtures/model.json": "{}"}
        found = self.tree(files)
        self.assertEqual([(f, "tests/fixtures/model.json" in d) for f, d in found], [("adapters/a/assets/provider.py", True)])
        self.assertEqual(self.tree(files, "/tests/** export-ignore\n/tests/fixtures -export-ignore\n"
                                          "/tests/fixtures/model.json -export-ignore\n"), [])

    def test_a_folder_constant_and_a_glob_string_resolve_when_anything_below_is_kept(self):
        code = ("from pathlib import Path\nPLUGIN = Path(__file__).resolve().parents[2]\nSHIMS = PLUGIN / \"tests\" / \"shims\"\n"
                "SOURCES = {\"m\": \"tests/records/mirror-*\"}\n")
        files = {"examples/e/run.py": code, "tests/shims/sbatch": "x", "tests/records/mirror-a.json": "{}"}
        self.assertEqual(len(self.tree(files)), 2)
        self.assertEqual(self.tree(files, "/tests/** export-ignore\n/tests/shims -export-ignore\n/tests/shims/** -export-ignore\n"
                                          "/tests/records -export-ignore\n/tests/records/mirror-* -export-ignore\n"), [])

    def test_a_root_that_is_not_the_plugin_root_is_not_read_as_one(self):
        # a profile's own tests use ROOT for the profile folder: ROOT / "tests" is inside the profile, which ships
        code = "from pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\nFIX = ROOT / \"tests\" / \"fixtures\"\n"
        self.assertEqual(self.tree({"profiles/experiments/x/scripts/s.py": code}), [])

    def test_markdown_links_into_left_out_paths_are_reported(self):
        files = {"skills/s/references/guide.md": "See [the test](../../../tests/a.py), [notes](../../../docs/dev/n.md), "
                                                 "[web](https://example.org/tests/x) and [anchor](#tests).\n",
                 "tests/a.py": "pass\n", "docs/dev/n.md": "n\n"}
        found = self.tree(files, "/tests/** export-ignore\n/docs/dev/ export-ignore\n")
        self.assertEqual(sorted(d.split()[0] for _, d in found), ["docs/dev/n.md", "tests/a.py"], found)
        self.assertEqual(self.tree(files, "/tests/** export-ignore\n/tests/a.py -export-ignore\n"), [])

    def test_maintainer_tools_and_test_code_are_not_checked(self):
        code = "from pathlib import Path\nPLUGIN = Path(__file__).resolve().parents[1]\nX = PLUGIN / \"tests\" / \"routing\" / \"cases.json\"\n"
        files = {"tools/run_all_checks.py": code, "adapters/g/tests/gate.py": code.replace("parents[1]", "parents[3]"),
                 "tests/routing/cases.json": "{}"}
        self.assertEqual(self.tree(files), [])


if __name__ == "__main__":
    unittest.main()


class ArchiveRuleTests(unittest.TestCase):
    def test_archives_are_refused(self):
        for name in ("submission.tar.gz", "x.zip", "a/b.tgz"):
            self.assertTrue(cp.ARCHIVE.search(name), name)
        for name in ("tar_reader.py", "zipped.md", "notes.txt"):
            self.assertFalse(cp.ARCHIVE.search(name), name)
