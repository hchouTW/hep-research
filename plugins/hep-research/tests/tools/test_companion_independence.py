"""Companion independence: hep-research installs and updates without a companion plugin (for example ams02-research).

Host-native plugin dependencies are parsed from JSON, never matched as text. Claude Code accepts a dependency as a
bare name, a qualified `name@marketplace` string, or an object with `name` (and optional `version`, `marketplace`),
in `plugin.json` and in a marketplace entry. hep-research must not depend on a plugin its catalogs list, and no
catalog entry owned here may depend on hep-research: compatibility with hep-research belongs to the companion.

The repository cases read the catalogs at the repository root only when this test runs from the source checkout
(the plugin folder sits at <repo>/plugins/hep-research next to a .git folder); a relocated copy skips them rather
than inspecting unrelated parent folders. These are static checks: they do not prove live host install or update
behaviour.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_host_manifests import coupling_problems, dependency_names  # noqa: E402

IN_REPO = (REPO / ".git").exists() and ROOT == (REPO / "plugins" / "hep-research").resolve()


def catalog(*entries: dict) -> dict:
    return {"name": "m", "plugins": [{"name": "hep-research", "source": "./plugins/hep-research"}, *entries]}


class DependencyNames(unittest.TestCase):
    def test_forms(self):
        names, bad = dependency_names(["a", "b@other-market", {"name": "c", "version": "^1.0"},
                                       {"name": "d", "marketplace": "x"}])
        self.assertEqual(names, ["a", "b", "c", "d"])
        self.assertEqual(bad, [])

    def test_absent_is_empty(self):
        self.assertEqual(dependency_names(None), ([], []))

    def test_malformed_is_reported_not_ignored(self):
        names, bad = dependency_names([{"version": "^1"}, 3])
        self.assertEqual(names, [])
        self.assertEqual(len(bad), 2)
        self.assertEqual(dependency_names("hep-research")[0], [])
        self.assertEqual(len(dependency_names("hep-research")[1]), 1)


class Coupling(unittest.TestCase):
    """Synthetic manifests and catalogs: each case adds one edge and expects exactly that edge reported."""

    COMPANION = {"name": "companion", "source": {"source": "github", "repo": "o/companion"}}

    def problems(self, manifests=None, catalogs=None):
        return coupling_problems("hep-research", manifests or {"claude": {"name": "hep-research"}},
                                 catalogs if catalogs is not None else {"claude": catalog(self.COMPANION)})

    def test_clean(self):
        self.assertEqual(self.problems(), [])

    def test_listing_both_plugins_is_not_a_dependency(self):
        self.assertEqual(self.problems(catalogs={"claude": catalog(self.COMPANION), "codex": catalog(self.COMPANION)}), [])

    def test_manifest_depends_on_companion(self):
        for dep in ("companion", "companion@m", {"name": "companion", "version": "^1.0"},
                    {"name": "companion", "marketplace": "elsewhere"}):
            with self.subTest(dep=dep):
                p = self.problems(manifests={"codex": {"name": "hep-research", "dependencies": [dep]}})
                self.assertEqual(len(p), 1, p)
                self.assertIn("codex plugin.json", p[0])

    def test_catalog_entry_of_companion_depends_on_hep(self):
        for dep in ("hep-research", "hep-research@hep-research-dev", {"name": "hep-research", "version": "^0.4.0"}):
            with self.subTest(dep=dep):
                p = self.problems(catalogs={"codex": catalog({**self.COMPANION, "dependencies": [dep]})})
                self.assertEqual(len(p), 1, p)
                self.assertIn("companion", p[0])

    def test_catalog_entry_of_hep_depends_on_companion(self):
        cat = catalog(self.COMPANION)
        cat["plugins"][0]["dependencies"] = ["companion@m"]
        self.assertEqual(len(self.problems(catalogs={"claude": cat})), 1)

    def test_unrelated_dependencies_are_preserved(self):
        cat = catalog({**self.COMPANION, "dependencies": ["third-party", {"name": "tool", "version": "^2"}]})
        self.assertEqual(self.problems(manifests={"claude": {"name": "hep-research", "dependencies": ["some-mcp"]}},
                                       catalogs={"claude": cat}), [])

    def test_malformed_dependency_list_fails(self):
        cat = catalog({**self.COMPANION, "dependencies": [{"version": "^0.4"}]})
        self.assertEqual(len(self.problems(catalogs={"claude": cat})), 1)


@unittest.skipUnless(IN_REPO, "relocated copy: no repository catalogs to check")
class RepositoryFiles(unittest.TestCase):
    """The files shipped from this repository: both host manifests and both catalogs."""

    def setUp(self):
        self.manifests = {h: json.loads((ROOT / f".{h}-plugin" / "plugin.json").read_text()) for h in ("claude", "codex")}
        self.catalogs = {"claude": json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text()),
                         "codex": json.loads((REPO / ".agents" / "plugins" / "marketplace.json").read_text())}

    def test_no_native_coupling(self):
        self.assertEqual(coupling_problems("hep-research", self.manifests, self.catalogs), [])

    def test_catalogs_keep_source_metadata(self):
        for host, cat in self.catalogs.items():
            for entry in cat["plugins"]:
                with self.subTest(host=host, plugin=entry.get("name")):
                    self.assertTrue(entry.get("source"))

    def test_ci_does_not_fetch_a_companion(self):
        """No workflow checks out, clones or authenticates to a companion repository (static text over CI files)."""
        names = {e["name"] for cat in self.catalogs.values() for e in cat["plugins"]} - {"hep-research"}
        for wf in sorted((REPO / ".github" / "workflows").glob("*.y*ml")):
            text = wf.read_text()
            for name in names:
                with self.subTest(workflow=wf.name, companion=name):
                    self.assertIsNone(re.search(rf"\b{re.escape(name)}\b", text))



class InstructionText(unittest.TestCase):
    """Text checks only: they show what the instructions say, not that a model follows them (that needs a live
    routing run; tests/routing case co-companion-ws-1 is the ordinary-work case)."""

    STANZA = (ROOT / "contracts" / "stanzas" / "context-resolution.md").read_text(encoding="utf-8")

    def test_stanza_routes_companion_profiles_through_their_preflight(self):
        for phrase in ("in neither place", "`<plugin>:profile` skill that names it", "after its preflight",
                       "a local path known to be a companion's", "never scan for companions", "the preflight fails",
                       "say it is unavailable", "other work"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.STANZA)

    def test_stanza_is_generic(self):
        """No companion name, package range, dependency declaration or host cache layout in the shared stanza."""
        for pattern in (r"ams", r"\^\d", r"[<>]=?\s*\d+\.\d", r"dependencies", r"plugins/cache", r"\.claude/", r"\.codex/"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.STANZA, re.I))

    def test_docs_do_not_recommend_a_host_dependency(self):
        dep = re.compile(r'"dependencies"\s*:\s*\[\s*(\{\s*"name"\s*:\s*)?"hep-research')
        for rel in ("docs/profile-authoring.md", "README.md", "skills/hep-computing/SKILL.md"):
            with self.subTest(file=rel):
                self.assertIsNone(dep.search((ROOT / rel).read_text(encoding="utf-8")))
        self.assertIn("preflight", (ROOT / "docs" / "profile-authoring.md").read_text(encoding="utf-8"))

    @unittest.skipUnless(IN_REPO, "relocated copy: no repository README")
    def test_readmes_name_every_pinned_companion_commit(self):
        """Every companion commit the catalogs pin is named in the READMEs' notes, so a pin move cannot leave the notes
        describing another release. With no companion listed, the READMEs say none is."""
        cats = [json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text()),
                json.loads((REPO / ".agents" / "plugins" / "marketplace.json").read_text())]
        pins = {e["source"].get("sha") for c in cats for e in c["plugins"]
                if e["name"] != "hep-research" and isinstance(e.get("source"), dict)}
        for path in (REPO / "README.md", ROOT / "README.md"):
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=str(path.relative_to(REPO))):
                for sha in pins:
                    self.assertIn(sha[:7], text)
                if not pins:
                    self.assertIn("not listed", text)


if __name__ == "__main__":
    unittest.main()
