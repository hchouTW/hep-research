"""v6.3 D11b: content-addressed definition snapshots and historical reproduction (V57), and the migration dispatcher
contracts/migrate.py (V19). A complete old snapshot reproduces the old subject's semantics after new definitions
are installed; a missing snapshot never falls back to the latest definitions; a rewritten snapshot is invalid. A
migration updates leaf to root into a new folder and writes its completion marker only after validation."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import v63_cases as cases  # noqa: E402

NEEDS_AMS = unittest.skipUnless(cases.HAVE_AMS, "the AMS example is not in this copy")


def ac():
    from contracts import analysis_check
    return analysis_check


def states(rep):
    return {o["obligation_id"]: (o["state"], o["reason"]) for o in rep["obligations"]}


def install_new_definitions(view):
    """Stand-in for a newer plugin: another coverage contract and a changed catalog entry."""
    cov = view["coverage"]["differential-flux"]["doc"] = copy.deepcopy(view["coverage"]["differential-flux"]["doc"])
    next(o for o in cov["operators"] if o["operator_id"] == "correct_efficiency")["class_coverage"]["efficiency"]["members"] = []
    view["catalog"] = copy.deepcopy(view["catalog"])
    next(e for e in view["catalog"]["effects"] if e["effect_id"] == "acceptance")["definition"] = "redefined in a newer catalog"


@NEEDS_AMS
class V57Snapshots(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.base = Path(self.td.name)
        self.store = self.base / "snapshots"

    def frozen(self):
        def keep(c):
            pass
        c = cases.positive_case(self.base / "c", None, freeze=False)
        c.write()
        bundle = ac().freeze(c.root, "v57", c.items, c.context, snapshots=self.store)
        (c.root / "bundle.json").write_text(json.dumps(bundle))
        return c.root / "bundle.json", c.root

    @unittest.expectedFailure  # V57 (D11b)
    def test_reproduced_from_the_old_snapshot(self):
        b, root = self.frozen()
        view, diags = ac().load_subject(b, root)
        original = ac().evaluate(copy.deepcopy(view), diags)
        install_new_definitions(view)
        without = ac().evaluate(copy.deepcopy(view), diags)
        self.assertIn("check.semantics_unreproducible", {o["reason"] for o in without["obligations"]})
        rep = ac().evaluate(view, diags, snapshots=self.store)
        self.assertEqual(states(rep), states(original))
        self.assertEqual(rep["semantics_source"], "snapshot")
        self.assertTrue(rep["installed_differences"])
        self.assertEqual(rep["lock_differences"], [])

    @unittest.expectedFailure  # V57 (D11b): no fallback to the latest definitions
    def test_missing_snapshot(self):
        b, root = self.frozen()
        view, diags = ac().load_subject(b, root)
        install_new_definitions(view)
        lock_cov = next(d for d in view["lock"]["definitions"] if d["kind"] == "coverage-contract")
        (self.store / f"{lock_cov['digest']}.json").unlink()
        rep = ac().evaluate(view, diags, snapshots=self.store)
        self.assertEqual(rep["semantics_source"], "installed")
        self.assertIn(lock_cov["digest"], rep["snapshot_missing"])
        self.assertIn("check.semantics_unreproducible", {o["reason"] for o in rep["obligations"]})

    @unittest.expectedFailure  # V57 (D11b): a rewritten snapshot is a digest failure
    def test_rewritten_snapshot(self):
        b, root = self.frozen()
        view, diags = ac().load_subject(b, root)
        install_new_definitions(view)
        lock_cov = next(d for d in view["lock"]["definitions"] if d["kind"] == "coverage-contract")
        path = self.store / f"{lock_cov['digest']}.json"
        doc = json.loads(path.read_text())
        doc["operators"][0]["stage"] = "calibration"
        path.write_text(json.dumps(doc))
        rep = ac().evaluate(view, diags, snapshots=self.store)
        self.assertEqual(rep["input_validity"], "invalid")
        self.assertIn("snapshot.digest", {d["code"] for d in rep["input_diagnostics"]})

    @unittest.expectedFailure  # V57 (D11b): unchanged definitions need no snapshot
    def test_unchanged_definitions(self):
        b, root = self.frozen()
        view, diags = ac().load_subject(b, root)
        rep = ac().evaluate(view, diags, snapshots=self.store)
        self.assertEqual((rep["semantics_source"], rep["installed_differences"]), ("installed", []))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@NEEDS_AMS
class V19Migration(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.base = Path(self.td.name)
        self.bundle = cases.positive_case(self.base / "src")
        self.before = {p: sha(p) for p in sorted((self.base / "src").rglob("*")) if p.is_file()}

    @unittest.expectedFailure  # V19 (D11b)
    def test_leaf_to_root(self):
        from contracts import migrate
        res = migrate.migrate(self.base / "src", self.bundle, self.base / "dst",
                              [{"item": "flux-reduced", "converter": "recipe-1.0.0-to-1.1.0"}])
        self.assertEqual(res["status"], "complete", res)
        self.assertEqual({p: sha(p) for p in self.before}, self.before, "original files unchanged")
        marker = json.loads((self.base / "dst" / "MIGRATION-COMPLETE.json").read_text())
        new = json.loads((self.base / "dst" / "bundle.json").read_text())
        self.assertEqual(marker["to_bundle"], new["bundle_digest"])
        self.assertNotEqual(marker["from_bundle"], marker["to_bundle"])
        self.assertEqual(json.loads((self.base / "dst" / "recipe.json").read_text())["recipe_version"], "1.1.0")
        self.assertEqual(ac().verify(new, self.base / "dst")["status"], "identical")
        view, diags = ac().load_subject(self.base / "dst" / "bundle.json", self.base / "dst")
        self.assertFalse([d for d in diags if d["kind"] == "input-invalid"])
        self.assertEqual([c["item"] for c in marker["conversions"]], ["flux-reduced"])

    @unittest.expectedFailure  # V19 (D11b): no completion marker on failure; originals kept
    def test_failure_leaves_no_marker(self):
        from contracts import migrate

        def broken(doc):
            return dict(doc, steps=[])
        res = migrate.migrate(self.base / "src", self.bundle, self.base / "dst",
                              [{"item": "flux-reduced", "converter": "broken"}], converters={"broken": broken})
        self.assertEqual(res["status"], "refused")
        self.assertTrue(res["diagnostics"])
        self.assertFalse((self.base / "dst" / "MIGRATION-COMPLETE.json").exists())
        self.assertEqual({p: sha(p) for p in self.before}, self.before)
        res = migrate.migrate(self.base / "src", self.bundle, self.base / "dst2",
                              [{"item": "flux-reduced", "converter": "no-such-converter"}])
        self.assertEqual(res["status"], "refused")


if __name__ == "__main__":
    unittest.main()
