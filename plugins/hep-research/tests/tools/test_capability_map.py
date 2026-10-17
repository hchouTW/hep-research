"""X3: docs/capability-map.json lists each capability with its owner, its state (tool, documentation or none) and
whether it is in v1; tools/capability_map.py validates it and writes the table in docs/capability-map.md; and
tools/check_routing_static.py requires every domain outside v1 to have a limited-support routing case owned by the
domain's closest skill. Cases added later that the map does not name are ignored by the rule."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools import capability_map as cm  # noqa: E402
from tools import check_routing_static as crs  # noqa: E402


def entry(**kw):
    e = {"id": "x", "capability": "X", "owner": "hep-theory", "state": "none", "v1": False, "cases": ["c1"]}
    e.update(kw)
    return e


def case(cid, expected="hep-theory", limited=True, also=None):
    c = {"id": cid, "expected_primary": expected, "kind": "out-of-v1", "lang": "en"}
    if limited:
        c["limited_support"] = True
    if also:
        c["also_accept"] = also
    return c


class ScopeRule(unittest.TestCase):
    def test_v1_out_domain_without_case_fails(self):
        errs = crs.scope_errors({"capabilities": [entry(cases=[])]}, [case("c1")])
        self.assertTrue(errs and "no limited-support routing case" in errs[0], errs)

    def test_missing_case_id_fails(self):
        errs = crs.scope_errors({"capabilities": [entry(cases=["gone"])]}, [case("c1")])
        self.assertTrue(any("gone" in e for e in errs), errs)

    def test_case_that_is_not_limited_support_fails(self):
        errs = crs.scope_errors({"capabilities": [entry()]}, [case("c1", limited=False)])
        self.assertTrue(any("not a limited-support case" in e for e in errs), errs)

    def test_case_routed_to_another_owner_fails_unless_accepted(self):
        m = {"capabilities": [entry()]}
        self.assertTrue(crs.scope_errors(m, [case("c1", expected="hep-statistics")]))
        self.assertEqual(crs.scope_errors(m, [case("c1", expected="hep-statistics", also=["hep-theory"])]), [])

    def test_v1_rows_and_unnamed_new_cases_are_ignored(self):
        m = {"capabilities": [entry(), entry(id="y", v1=True, state="tool", cases=[])]}
        cases = [case("c1"), case("new-case-from-another-batch", limited=False)]
        self.assertEqual(crs.scope_errors(m, cases), [])

    def test_repository_map_passes(self):
        cases = json.loads((ROOT / "tests" / "routing" / "cases.json").read_text(encoding="utf-8"))["cases"]
        self.assertEqual(crs.scope_errors(cm.load(), cases), [])
        r = subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "check_routing_static.py")],
                           capture_output=True, text=True, timeout=120)
        rep = json.loads(r.stdout)
        self.assertEqual(rep["scope_errors"], [])
        self.assertEqual(r.returncode, 0, rep)


class MapFile(unittest.TestCase):
    def test_schema(self):
        self.assertEqual(cm.validate(cm.load()), [])

    def test_schema_refusals(self):
        bad = {"capabilities": [entry(state="half"), entry(owner="hep-nobody"), entry(id="x", v1=True, cases=[])]}
        errs = cm.validate(bad)
        self.assertTrue(any("state" in e for e in errs), errs)
        self.assertTrue(any("owner" in e for e in errs), errs)
        self.assertTrue(any("duplicate id" in e for e in errs), errs)

    def test_every_v1_out_domain_named_by_the_work_order_is_on_the_map(self):
        ids = {e["id"] for e in cm.load()["capabilities"] if not e["v1"]}
        for d in ("lattice-qcd", "eft-global-fits", "propagation-global-fits", "heavy-ions", "nuclear-structure",
                  "relic-density-solvers", "dark-matter-phenomenology"):
            self.assertIn(d, ids)

    def test_markdown_table_is_generated_from_the_map(self):
        r = subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "capability_map.py"), "--check"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_check_detects_a_stale_table(self):
        md = (ROOT / "docs" / "capability-map.md").read_text(encoding="utf-8")
        self.assertEqual(cm.render_into(md, cm.load()), md)
        stale = md.replace("| lattice-qcd |", "| lattice-qcd-old |")
        self.assertNotEqual(cm.render_into(stale, cm.load()), stale)


class ScopeDeclaration(unittest.TestCase):
    """X1: docs/routing-contract.md lists what v1 covers and what it does not, generated from the map."""

    def test_contract_lists_the_map_scope(self):
        text = (ROOT / "docs" / "routing-contract.md").read_text(encoding="utf-8")
        self.assertIn(cm.SCOPE_BEGIN, text)
        self.assertEqual(cm.render_scope_into(text, cm.load()), text)
        block = text.split(cm.SCOPE_BEGIN, 1)[1].split(cm.SCOPE_END, 1)[0]
        for e in cm.load()["capabilities"]:
            self.assertIn(e["id"], block)

    def test_stale_declaration_is_detected(self):
        text = (ROOT / "docs" / "routing-contract.md").read_text(encoding="utf-8")
        stale = text.replace("(heavy-ions)", "(heavy-ion-old)")
        self.assertNotEqual(cm.render_scope_into(stale, cm.load()), stale)

    def test_neutrino_in_v1_since_th4_and_ckm_outside_with_its_case(self):
        rows = {e["id"]: e for e in cm.load()["capabilities"]}
        self.assertTrue(rows["neutrino-oscillations"]["v1"])
        self.assertEqual(rows["neutrino-oscillations"]["state"], "tool")
        self.assertIn("Th4", rows["neutrino-oscillations"]["items"])
        self.assertFalse(rows["ckm-global-fits"]["v1"])
        self.assertEqual(rows["ckm-global-fits"]["cases"], ["th-flavour-2"])

    def test_x1_routing_cases(self):
        cases = {c["id"]: c for c in json.loads((ROOT / "tests" / "routing" / "cases.json").read_text(
            encoding="utf-8"))["cases"]}
        c = cases["th-flavour-2"]
        self.assertEqual((c["lang"], c["kind"], c["prompt"], c["expected_primary"]),
                         ("zh-Hant", "out-of-v1", "幫我做 CKM 全域擬合。", "hep-theory"))
        self.assertTrue(c["limited_support"])
        c = cases["th-scope-2"]  # a direct case since Th4 put neutrino oscillations in v1
        self.assertEqual((c["lang"], c["kind"], c["prompt"], c["expected_primary"]),
                         ("zh-Hant", "direct", "幫我推導微中子振盪機率在物質中的修正。", "hep-theory"))
        self.assertFalse(c.get("limited_support", False))

    def test_skill_outside_v1_rows_point_to_the_declaration(self):
        for skill in ("hep-theory", "hep-statistics"):
            text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            row = next(line for line in text.splitlines() if line.startswith("| Outside v1"))
            self.assertIn("docs/routing-contract.md", row)


if __name__ == "__main__":
    unittest.main()
