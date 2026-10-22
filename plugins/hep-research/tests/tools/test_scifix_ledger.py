"""Evidence ledger of scientific corrections (docs/evidence/sci-fixes.json): every entry uses the two-axis vocabulary,
names existing evidence tests, and states its gaps whenever it is below the requirement for its severity. The ledger
records evidence; it never authorizes anything, and a fix below its requirement is reported, not refused.

A locator record names its source and located claim in the scifix source and claim ledger (core/evidence format), read
at page level or better; every independence record lists the import names its oracle test requires, core or backend,
and each backend is locked by a required CI gate (plan B1 and B4)."""
import copy
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.evidence.ledger import check_ledger  # noqa: E402
from core.evidence.render_index import check_index  # noqa: E402

LEDGER = ROOT / "docs" / "evidence" / "sci-fixes.json"
SOURCES = ROOT / "docs" / "evidence" / "scifix-sources.json"
CLAIMS = ROOT / "docs" / "evidence" / "scifix-claims.json"
INDEX = ROOT / "docs" / "evidence" / "scifix-index.md"
WORKFLOW = ROOT.parents[1] / ".github" / "workflows" / "tests.yml"
CORE_DEPS = {"numpy", "scipy", "sympy", "mpmath", "matplotlib"}  # requirements-core.txt and sympy's mpmath
BACKENDS = {"pyhf", "arviz", "pdg", "torch", "xgboost", "sklearn"}
LOCATOR_LEVELS = ("page", "full-text")  # an abstract read locates no equation, though core/evidence ranks it with page
C = ("C0", "C1", "C2", "C3", "C4")
D = ("D0", "D1", "D2", "D3")
REQUIRED = {"S1": ("C3", "D2"), "S2": ("C2", "D2"), "S4": ("C1", "D2")}
ORACLES = {"exhaustive", "symbolic", "analytic", "published", "independent-implementation", "invariant", "closure",
           "pinned-value", "behavioral"}
INDEPENDENT = {"exhaustive", "symbolic", "analytic", "published", "independent-implementation"}
BASES = {"locator", "third-party", "exhaustive", "person"}  # docs/maintenance.md, oracle independence


def below(entry) -> bool:
    need_c, need_d = REQUIRED[entry["severity"]]
    return C.index(entry["correctness"]) < C.index(need_c) or D.index(entry["discrimination"]) < D.index(need_d)


def _ids(value) -> list:
    return value if isinstance(value, list) else [value] if value else []


def locator_problems(doc: dict, sources: list, claims: list) -> list[str]:
    """A locator record names its source (`source_id`) and its located claim (`locator_id`), each a string or a list:
    every id exists, every source was read at page level or better, every claim rests on one of the record's sources
    and every source carries one of its claims."""
    by_source = {s["id"]: s for s in sources}
    by_claim = {c["id"]: c for c in claims}
    out = []
    for f in doc["fixes"]:
        for rec in f.get("independence", []):
            if rec["basis"] != "locator":
                continue
            where = f"{f['id']} {rec['kind']}"
            sids, cids = _ids(rec.get("source_id")), _ids(rec.get("locator_id"))
            if not sids or not cids:
                out.append(f"{where}: a locator record needs source_id and locator_id")
                continue
            for sid in sids:
                if sid not in by_source:
                    out.append(f"{where}: unknown source {sid}")
                elif by_source[sid].get("verification_level") not in LOCATOR_LEVELS:
                    out.append(f"{where}: source {sid} read at {by_source[sid].get('verification_level')}, below page")
            for cid in cids:
                if cid not in by_claim:
                    out.append(f"{where}: unknown locator {cid}")
                elif not set(by_claim[cid]["source_ids"]) & set(sids):
                    out.append(f"{where}: locator {cid} rests on none of {sids}")
            cited = {s for cid in cids if cid in by_claim for s in by_claim[cid]["source_ids"]}
            out += [f"{where}: source {sid} carries none of the record's locators" for sid in sids
                    if sid in by_source and sid not in cited]
    return out


def requires_problems(doc: dict) -> list[str]:
    """Every independence record has `requires` with exactly `core` and `backend`, each a sorted list of known import
    names (core: requirements-core.txt; backend: an optional package a required CI gate locks)."""
    out = []
    for f in doc["fixes"]:
        for rec in f.get("independence", []):
            where = f"{f['id']} {rec['kind']} {rec['test'].rsplit('::', 1)[-1]}"
            req = rec.get("requires")
            if not isinstance(req, dict) or set(req) != {"core", "backend"}:
                out.append(f"{where}: requires must be {{'core': [...], 'backend': [...]}}")
                continue
            for part, known in (("core", CORE_DEPS), ("backend", BACKENDS)):
                names = req[part]
                if not isinstance(names, list) or names != sorted(set(names)):
                    out.append(f"{where}: requires.{part} must be a sorted list without repeats")
                    continue
                out += [f"{where}: {n} is not a known {part} dependency" for n in names if n not in known]
    return out


def required_gate_backends(workflow: str) -> dict[str, set]:
    """The import names each required CI job locks through `run_required_backends.py --require` (optional-* jobs are
    not required)."""
    gates = {}
    for m in re.finditer(r"(?ms)^  ([A-Za-z0-9_-]+):\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", workflow):
        if m.group(1).startswith("optional"):
            continue
        for spec in re.findall(r"run_required_backends\.py --require (\S+)", m.group(2)):
            gates.setdefault(m.group(1), set()).update(x.split("==")[0] for x in spec.split(",") if x)
    return gates


def backend_gate_problems(doc: dict, gates: dict[str, set]) -> list[str]:
    locked = set().union(*gates.values()) if gates else set()
    needed = {n for f in doc["fixes"] for rec in f.get("independence", []) for n in rec["requires"]["backend"]}
    return [f"backend {n} is locked by no required CI gate" for n in sorted(needed - locked)]


class SciFixLedger(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_vocabulary_tests_and_unique_ids(self):
        ids = [f["id"] for f in self.doc["fixes"]] + [f["id"] for f in self.doc["documentation_fixes"]]
        self.assertEqual(len(ids), len(set(ids)))
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                self.assertIn(f["severity"], REQUIRED)
                self.assertIn(f["correctness"], C)
                self.assertIn(f["discrimination"], D)
                self.assertTrue(f["evidence_tests"])
                for t in f["evidence_tests"]:
                    self.assertTrue((ROOT / t).is_file(), t)
                self.assertTrue(set(f["oracle_kinds"]) <= ORACLES, f["oracle_kinds"])
                self.assertIsInstance(f["negative_control_emulates_pre_fix"], bool)

    def test_grades_are_consistent_with_the_oracles(self):
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                kinds = set(f["oracle_kinds"]) & INDEPENDENT
                if f["correctness"] in ("C2", "C3"):
                    self.assertTrue(kinds, "C2 or above needs an independent oracle kind")
                if f["correctness"] == "C3":
                    self.assertGreaterEqual(len(kinds), 2)
                    self.assertIn("invariant", f["oracle_kinds"])
                    self.assertTrue(f["negative_control_emulates_pre_fix"])
                if f["correctness"] == "C4":
                    self.assertTrue({"exhaustive", "symbolic"} & set(f["oracle_kinds"]))

    def test_every_counted_kind_has_a_qualifying_basis(self):
        """The maintainer's rule (docs/maintenance.md, oracle independence): an independent kind counts only with a
        record naming its test and a basis, locator, third-party, exhaustive or person; C2 needs one such kind, C3
        two distinct ones, C4 an exhaustive or symbolic one."""
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                records = f.get("independence", [])
                for rec in records:
                    self.assertIn(rec["kind"], INDEPENDENT, rec)
                    self.assertIn(rec["basis"], BASES, rec)
                    self.assertTrue(rec["detail"], rec)
                    self.assertTrue((ROOT / rec["test"].split("::")[0]).is_file(), rec["test"])
                qualified = {rec["kind"] for rec in records}
                self.assertEqual(set(f["oracle_kinds"]) & INDEPENDENT, qualified,
                                 "an independent kind is listed exactly when a record qualifies it")
                need = {"C1": 0, "C2": 1, "C3": 2, "C4": 1}[f["correctness"]] if f["correctness"] != "C0" else 0
                self.assertGreaterEqual(len(qualified), need, (f["correctness"], qualified))
                if f["correctness"] == "C4":
                    self.assertTrue({"exhaustive", "symbolic"} & qualified, qualified)

    def test_changelog_names_the_release_that_shipped_the_fix(self):
        """C5 (plan F-19): the release is a CHANGELOG section and the fixed release of every advisory naming the entry;
        an unreleased entry's advisory range is open, and without an advisory the CHANGELOG still has `Unreleased`."""
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        sections = set(re.findall(r"^## (\d+\.\d+\.\d+) \(", changelog, re.M))
        unreleased_open = re.search(r"^## Unreleased$", changelog, re.M) is not None
        fixed: dict[str, set] = {}
        open_ranges: dict[str, bool] = {}
        for path in sorted((ROOT / "docs" / "evidence" / "advisories").glob("SFA-*.json")):
            adv = json.loads(path.read_text(encoding="utf-8"))
            for ref in adv["ledger"]:
                for block in adv["affected"]:
                    for rng in block["ranges"]:
                        closing = [e["fixed"] for e in rng["events"] if "fixed" in e]
                        fixed.setdefault(ref, set()).update(closing)
                        if not any("fixed" in e or "last_affected" in e for e in rng["events"]):
                            open_ranges[ref] = True
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                cl = f["changelog"]
                self.assertIn(cl["kind"], ("release", "audit", "unreleased"))
                self.assertLessEqual(set(cl), {"kind", "release", "name", "detail"})
                if cl["kind"] == "unreleased":
                    self.assertNotIn("release", cl)
                    if f["id"] in fixed or f["id"] in open_ranges:
                        self.assertTrue(open_ranges.get(f["id"]), "an advisory with a fixed release names it")
                    else:
                        self.assertTrue(unreleased_open, "no Unreleased section left in CHANGELOG.md")
                    continue
                self.assertIn(cl["release"], sections)
                if cl["kind"] == "audit":
                    self.assertTrue(cl.get("name"))
                if f["id"] in fixed:
                    self.assertIn(cl["release"], fixed[f["id"]], "the advisory's fixed release")

    def test_scifix_source_and_claim_ledger_is_valid_and_indexed(self):
        sources, claims = json.loads(SOURCES.read_text(encoding="utf-8")), json.loads(CLAIMS.read_text(encoding="utf-8"))
        res = check_ledger(sources, claims, date(2026, 10, 22), 365, namespace="scifix")
        self.assertEqual((res["errors"], res["warnings"]), ([], []))
        ok, diff = check_index(INDEX.read_text(encoding="utf-8"), sources, claims)
        self.assertTrue(ok, diff)
        bad = copy.deepcopy(claims)
        bad[0]["verification_strength"] = "full-text"
        self.assertTrue(check_ledger(sources, bad, date(2026, 10, 22), 365, namespace="scifix")["errors"])
        self.assertFalse(check_index(INDEX.read_text(encoding="utf-8"), sources, bad[1:])[0])

    def test_locator_records_name_a_source_read_at_page_level_and_a_located_claim(self):
        sources, claims = json.loads(SOURCES.read_text(encoding="utf-8")), json.loads(CLAIMS.read_text(encoding="utf-8"))
        self.assertEqual(locator_problems(self.doc, sources, claims), [])
        self.assertTrue(any(r["basis"] == "locator" for f in self.doc["fixes"] for r in f.get("independence", [])))

    def test_locator_check_rejects_missing_unknown_and_unread(self):
        sources, claims = json.loads(SOURCES.read_text(encoding="utf-8")), json.loads(CLAIMS.read_text(encoding="utf-8"))
        rec = next(r for f in self.doc["fixes"] for r in f["independence"] if r["basis"] == "locator")
        for change, expect in ((lambda r, s, c: r.pop("source_id"), "needs source_id and locator_id"),
                               (lambda r, s, c: r.update(locator_id="scifix:C99"), "unknown locator"),
                               (lambda r, s, c: r.update(source_id="scifix:S99"), "unknown source"),
                               (lambda r, s, c: next(x for x in s if x["id"] == _ids(r["source_id"])[0]).update(
                                   verification_level="abstract+metadata"), "below page"),
                               (lambda r, s, c: next(x for x in s if x["id"] == _ids(r["source_id"])[0]).update(
                                   verification_level="metadata-only"), "below page"),
                               (lambda r, s, c: r.update(source_id="scifix:S10"), "rests on none")):
            with self.subTest(expect=expect):
                doc, s, c = copy.deepcopy(self.doc), copy.deepcopy(sources), copy.deepcopy(claims)
                r = next(r for f in doc["fixes"] for r in f["independence"] if r["test"] == rec["test"]
                         and r["kind"] == rec["kind"])
                change(r, s, c)
                problems = locator_problems(doc, s, c)
                self.assertTrue(any(expect in p for p in problems), problems)

    def test_every_independence_record_states_what_its_oracle_requires(self):
        self.assertEqual(requires_problems(self.doc), [])
        for change, expect in ((lambda r: r.pop("requires"), "requires must be"),
                               (lambda r: r.update(requires={"core": ["sympy"]}), "requires must be"),
                               (lambda r: r.update(requires={"core": ["sympy", "numpy"], "backend": []}), "sorted"),
                               (lambda r: r.update(requires={"core": ["pyhf"], "backend": []}), "not a known core"),
                               (lambda r: r.update(requires={"core": [], "backend": ["jax"]}), "not a known backend")):
            with self.subTest(expect=expect):
                doc = copy.deepcopy(self.doc)
                change(doc["fixes"][0]["independence"][0])
                self.assertTrue(any(expect in p for p in requires_problems(doc)), requires_problems(doc))

    @unittest.skipUnless(WORKFLOW.is_file(), "repository checkout only (an installed plugin tree has no .github)")
    def test_every_backend_is_locked_by_a_required_gate(self):
        gates = required_gate_backends(WORKFLOW.read_text(encoding="utf-8"))
        self.assertTrue({"stats-backends", "pdg-cross-check", "torch-backend", "bdt-backend"} <= set(gates), gates)
        self.assertEqual(backend_gate_problems(self.doc, gates), [])
        without_pdg = {job: names - {"pdg"} for job, names in gates.items()}
        self.assertEqual(backend_gate_problems(self.doc, without_pdg), ["backend pdg is locked by no required CI gate"])
        optional_only = required_gate_backends("jobs:\n  optional-pdg:\n    run: python tools/run_required_backends.py "
                                               "--require pdg==2026.0\n")
        self.assertEqual(optional_only, {})

    def test_entries_below_their_requirement_state_their_gaps(self):
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                if below(f):
                    self.assertTrue(f["gaps"], "an entry below its requirement must list what is missing")


if __name__ == "__main__":
    unittest.main()
