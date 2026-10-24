"""v6.3 D05b: bundle v2 (per-mode roles, unique IDs, dual digests), check context, the deterministic obligation
generator and its inventory, and the semantic lock (record and compare). V14, V50, V58 (M2a part), V67, V68 (D05b
part). Cases are built by tests/contracts/analysis_check_cases.py in temporary folders."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import analysis_check_cases as cases  # noqa: E402

NEEDS_AMS = unittest.skipUnless(cases.HAVE_AMS, "the AMS example is not in this copy")


def ac():
    from contracts import analysis_check
    return analysis_check


class Tmp(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)


@NEEDS_AMS
class BundleV2(Tmp):
    def test_freeze_and_verify(self):
        path = cases.chain_case(self.root / "c")
        bundle = json.loads(path.read_text())
        self.assertEqual((bundle["format"], bundle["mode"]), ("hep-research-analysis-bundle/2", "chain"))
        roles = {i["role"] for i in bundle["items"]}
        self.assertTrue({"context", "semantic-lock", "response", "dataset-record"} <= roles)
        spec = next(i for i in bundle["items"] if i["id"] == "spec")
        self.assertEqual(spec["digest_kind"], "canonical-json")
        self.assertRegex(spec["bytes_sha256"], "^[0-9a-f]{64}$")
        env = next(i for i in bundle["items"] if i["id"] == "env")
        self.assertNotIn("bytes_sha256", env)
        self.assertEqual(ac().verify(bundle, self.root / "c")["status"], "identical")

    def test_v1_reader_refuses_v2_and_v1_is_unchanged(self):
        from contracts import analysis_bundle as ab
        bundle = json.loads(cases.chain_case(self.root / "c").read_text())
        self.assertEqual(ab.verify(bundle, self.root / "c")["status"], "invalid")

    def test_roles_and_ids(self):
        def no_recipe(c):
            c.remove("flux-from-counts")
        with self.assertRaises(ac().BundleRefused) as ctx:
            cases.chain_case(self.root / "a", no_recipe)
        self.assertEqual(ctx.exception.code, "bundle.roles")

        def twin(c):
            c.add("response", "response-proton-p1", "artifacts/twin.json", {"x": 1})
        with self.assertRaises(ac().BundleRefused) as ctx:
            cases.chain_case(self.root / "b", twin)
        self.assertEqual(ctx.exception.code, "bundle.duplicate_id")

    def test_context_and_lock_are_items(self):
        path = cases.chain_case(self.root / "c")
        bundle = json.loads(path.read_text())
        ctx = json.loads((self.root / "c" / next(i["ref"] for i in bundle["items"] if i["role"] == "context")).read_text())
        lock = json.loads((self.root / "c" / next(i["ref"] for i in bundle["items"] if i["role"] == "semantic-lock")).read_text())
        self.assertNotIn(bundle["bundle_digest"], json.dumps(ctx) + json.dumps(lock))
        self.assertTrue(ctx["obligations"]["items"])
        self.assertEqual(lock["suite"], {"id": "counting-chain", "version": "1.0.0"})


@NEEDS_AMS
class Inventory(Tmp):
    def test_regeneration_is_byte_identical_and_order_free(self):
        from contracts.analysis_checks.obligations import generate
        c = cases.chain_case(self.root / "c", freeze=False)
        view = ac().draft_view(c.root, c.items, c.context, c.files)
        a = generate(ac().load_suite("counting-chain", "1.0.0"), view)
        shuffled = copy.deepcopy(c.context)
        for key in ("roots", "recipe_instances", "declarations"):
            shuffled[key].reverse()
        b = generate(ac().load_suite("counting-chain", "1.0.0"), ac().draft_view(c.root, c.items, shuffled, c.files))
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        ids = [o["obligation_id"] for o in a["items"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_a_differing_inventory_is_invalid_input(self):
        path = cases.chain_case(self.root / "c")
        bundle = json.loads(path.read_text())
        view, diags = ac().load_subject(path, self.root / "c")
        self.assertEqual([d for d in diags if d["kind"] == "input-invalid"], [])
        view["context"]["obligations"]["items"].pop()
        self.assertIn("inventory.mismatch", {d["code"] for d in ac().check_inventory(view)})
        self.assertTrue(bundle["bundle_digest"])

    def test_inventory_ignores_bindings_and_declarations(self):
        from contracts.analysis_checks.obligations import generate
        c = cases.chain_case(self.root / "c", freeze=False)
        suite = ac().load_suite("counting-chain", "1.0.0")
        full = generate(suite, ac().draft_view(c.root, c.items, c.context, c.files))
        masked = copy.deepcopy(c.context)
        masked["declarations"], masked["bindings"] = [], []
        self.assertEqual(generate(suite, ac().draft_view(c.root, c.items, masked, c.files)), full)


@NEEDS_AMS
class SemanticLock(Tmp):
    def test_definition_change_is_a_lock_difference(self):
        from contracts.analysis_checks.lock import compare
        path = cases.chain_case(self.root / "c")
        view, _ = ac().load_subject(path, self.root / "c")
        current = ac().current_lock(view)
        self.assertEqual(compare(view["lock"], current), [])
        view["coverage"]["differential-flux"]["doc"]["operators"][0]["stage"] = "calibration"
        diffs = compare(view["lock"], ac().current_lock(view))
        self.assertEqual([(d["kind"], d["id"]) for d in diffs], [("coverage-contract", "differential-flux")])

    def test_member_sets(self):
        from contracts.analysis_checks.lock import compare
        path = cases.chain_case(self.root / "c")
        view, _ = ac().load_subject(path, self.root / "c")
        self.assertIn("efficiency", {m["class"] for m in view["lock"]["member_sets"]})
        unrelated = copy.deepcopy(view)
        unrelated["catalog"]["effects"].append({"effect_id": "dead_time", "class": None, "definition": "synthetic"})
        self.assertEqual(compare(view["lock"], ac().current_lock(unrelated)), [])
        grown = copy.deepcopy(view)
        grown["catalog"]["effects"].append({"effect_id": "tracking_efficiency", "class": "efficiency", "definition": "s"})
        next(c for c in grown["catalog"]["classes"] if c["class_id"] == "efficiency")["members"].append("tracking_efficiency")
        self.assertIn(("member-set", "efficiency"), {(d["kind"], d["id"]) for d in compare(view["lock"], ac().current_lock(grown))})


@NEEDS_AMS
class Subjects(Tmp):
    def test_deleting_a_root(self):
        from contracts.analysis_checks.obligations import diff
        a = json.loads(cases.chain_case(self.root / "a").read_text())

        def drop_root(c):
            c.context["roots"] = [r for r in c.context["roots"] if r["root_id"] != "flux-helium-p2"]
        b = json.loads(cases.chain_case(self.root / "b", drop_root).read_text())
        self.assertNotEqual(a["bundle_digest"], b["bundle_digest"])
        va, _ = ac().load_subject(self.root / "a" / "bundle.json", self.root / "a")
        vb, _ = ac().load_subject(self.root / "b" / "bundle.json", self.root / "b")
        d = diff(va["context"]["obligations"]["items"], vb["context"]["obligations"]["items"])
        self.assertEqual(d["added"], [])
        self.assertTrue(d["removed"])
        self.assertTrue(all("flux-helium-p2" in o for o in d["removed"]))

    def test_new_suite_version(self):
        from contracts.analysis_checks.obligations import diff, generate
        c = cases.chain_case(self.root / "c", freeze=False)
        view = ac().draft_view(c.root, c.items, c.context, c.files)
        v1 = ac().load_suite("counting-chain", "1.0.0")
        v2 = copy.deepcopy(v1)
        v2["version"] = "1.1.0"
        v2["rules"].append({"rule_id": "r-inv.extra", "version": "1.0.0", "subject": "root"})
        d = diff(generate(v1, view)["items"], generate(v2, view)["items"])
        self.assertEqual(d["removed"], [])
        self.assertEqual(sorted(d["added"]), sorted(f"r-inv.extra:{r['root_id']}" for r in c.context["roots"]))


if __name__ == "__main__":
    unittest.main()
