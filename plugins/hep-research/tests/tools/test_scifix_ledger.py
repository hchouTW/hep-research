"""Evidence ledger of scientific corrections (docs/evidence/sci-fixes.json): every entry uses the two-axis vocabulary,
names existing evidence tests, and states its gaps whenever it is below the requirement for its severity. The ledger
records evidence; it never authorizes anything, and a fix below its requirement is reported, not refused.

A locator record names its source and located claim in the scifix source and claim ledger (core/evidence format), read
at page level or better; every independence record lists the import names its oracle test requires, core or backend,
and each backend is locked by a required CI gate (plan B1 and B4).

The D axis is structured (plan B3): each entry names its parent, fix and follow-up commits (40-hex), its per-test
parent records and its mutants, and D2 and D3 are recomputed from them under the D-scope rule; a superseded entry
stays as a tombstone (plan B6)."""
import copy
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import scifix_ledger  # noqa: E402

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


def _requires_records(doc: dict):
    """(where, record) for every record that states what its test needs: independence and parent records."""
    for f in doc["fixes"]:
        for rec in f.get("independence", []):
            yield f"{f['id']} {rec['kind']} {rec['test'].rsplit('::', 1)[-1]}", rec
        for rec in f.get("parent_records", []):
            yield f"{f['id']} parent record {str(rec.get('test')).rsplit('::', 1)[-1]}", rec


def requires_problems(doc: dict) -> list[str]:
    """Every independence and parent record has `requires` with exactly `core` and `backend`, each a sorted list of
    known import names (core: requirements-core.txt; backend: an optional package a required CI gate locks)."""
    out = []
    for where, rec in _requires_records(doc):
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


# Plan B3, the structured D axis. D2 needs a parent record (fails on the parent, passes on the fix) for every oracle
# node of the entry's independence records, or, for an entry without one, for a regression test; D3 also a killed
# revert mutant (D-scope rule, maintainer decision 2026-10-22, docs/maintenance.md).
HEX40 = re.compile(r"[0-9a-f]{40}")
NODE = re.compile(r"(tests/[\w/]+\.py)::(\w+)::(\w+)")
PARENT_OUTCOMES = ("fail", "pass", "error", "skip")
FIX_OUTCOMES = ("pass", "fail", "error", "skip")
FAILURES = ("assertion", "error")
ADAPTATIONS = ("adds new modules", "guards an import")
MUTATIONS = ("revert", "other")
RECORD_KEYS = {"test", "parent", "fix", "failure", "env", "adapted_parent", "validation", "requires"}
MUTANT_KEYS = {"function", "mutation", "killed_by", "detail"}


def validation_sections(text: str) -> set[str]:
    return set(re.findall(r"^## (\S+)", text, re.M))


def node_problem(node, root: Path = ROOT) -> str | None:
    """None when `node` is 'tests/...py::Class::method' and that file defines the class and the method."""
    m = NODE.fullmatch(node) if isinstance(node, str) else None
    if not m:
        return f"{node!r} is not a test node id (tests/...py::Class::method)"
    path = root / m.group(1)
    if not path.is_file():
        return f"{node}: no such file"
    text = path.read_text(encoding="utf-8")
    if not re.search(rf"^class {m.group(2)}\b", text, re.M) or not re.search(rf"^    def {m.group(3)}\b", text, re.M):
        return f"{node}: no such test"
    return None


def _file_exists(ref, root: Path = ROOT) -> bool:
    return isinstance(ref, str) and bool(ref) and (root / ref.split("::")[0]).is_file()


def valid_parent_failures(entry: dict) -> set[str]:
    """Nodes with a record that fails on the parent and passes on the fix, the parent tree unadapted or adapted as
    the adapted-parent rule allows."""
    return {r["test"] for r in entry.get("parent_records", []) if r.get("parent") == "fail" and r.get("fix") == "pass"
            and (not r.get("adapted_parent") or r.get("adaptation") in ADAPTATIONS)}


def supported_discrimination(entry: dict) -> str:
    """D3 or D2 when the structured records support it, else 'D1' (a cap: D0 and D1 rest on prose)."""
    valid = valid_parent_failures(entry)
    nodes = {r["test"] for r in entry.get("independence", [])}
    if not (nodes <= valid if nodes else valid):
        return "D1"
    killed_revert = any(m.get("mutation") == "revert" and m.get("killed_by") for m in entry.get("mutants", []))
    return "D3" if killed_revert else "D2"


def commit_problems(doc: dict) -> list[str]:
    out = []
    for f in doc["fixes"]:
        c = f.get("commits")
        if not isinstance(c, dict) or set(c) != {"parent", "fix", "follow_up"}:
            out.append(f"{f['id']}: commits must be {{'parent', 'fix', 'follow_up'}}")
            continue
        for key in ("parent", "fix"):
            if not (isinstance(c[key], str) and HEX40.fullmatch(c[key])):
                out.append(f"{f['id']}: commits.{key} must be a 40-hex commit")
        if not isinstance(c["follow_up"], list) or not all(isinstance(h, str) and HEX40.fullmatch(h)
                                                           for h in c["follow_up"]):
            out.append(f"{f['id']}: commits.follow_up must be a list of 40-hex commits")
        elif c["parent"] == c["fix"] or c["fix"] in c["follow_up"]:
            out.append(f"{f['id']}: the parent, the fix and each follow-up are different commits")
    return out


def record_problems(doc: dict, sections: set[str], root: Path = ROOT) -> list[str]:
    """parent_records and mutants are well formed, and each record's validation section exists in VALIDATION.md."""
    out = []
    for f in doc["fixes"]:
        recs, mutants = f.get("parent_records"), f.get("mutants")
        if not isinstance(recs, list) or not isinstance(mutants, list):
            out.append(f"{f['id']}: parent_records and mutants must be lists")
            continue
        seen = set()
        for rec in recs:
            where = f"{f['id']} parent record {rec.get('test')}"
            adapted = rec.get("adapted_parent")
            if set(rec) != RECORD_KEYS | ({"adaptation"} if adapted else set()):
                out.append(f"{where}: keys must be {sorted(RECORD_KEYS)}, plus adaptation exactly when adapted_parent")
                continue
            problem = node_problem(rec["test"], root)
            if problem:
                out.append(f"{where}: {problem}")
            if rec["test"] in seen:
                out.append(f"{where}: recorded twice")
            seen.add(rec["test"])
            if rec["parent"] not in PARENT_OUTCOMES or rec["fix"] not in FIX_OUTCOMES:
                out.append(f"{where}: parent must be one of {PARENT_OUTCOMES}, fix one of {FIX_OUTCOMES}")
            elif rec["parent"] in ("pass", "skip"):
                if rec["failure"] is not None:
                    out.append(f"{where}: failure must be null when the parent did not fail")
            elif rec["failure"] not in FAILURES or (rec["parent"] == "error" and rec["failure"] != "error"):
                out.append(f"{where}: failure must be assertion or error (error when the parent result is error)")
            if not isinstance(rec["env"], str) or not rec["env"]:
                out.append(f"{where}: env must name the environment")
            if not isinstance(adapted, bool):
                out.append(f"{where}: adapted_parent must be true or false")
            elif adapted and rec["adaptation"] not in ADAPTATIONS:
                out.append(f"{where}: an adapted parent tree may only {' or '.join(ADAPTATIONS)}")
            if rec["validation"] not in sections:
                out.append(f"{where}: VALIDATION.md has no section {rec['validation']!r}")
        for m in mutants:
            where = f"{f['id']} mutant {m.get('detail')!r}"
            if set(m) != MUTANT_KEYS:
                out.append(f"{where}: keys must be {sorted(MUTANT_KEYS)}")
                continue
            if m["mutation"] not in MUTATIONS:
                out.append(f"{where}: mutation must be one of {MUTATIONS}")
            if not _file_exists(m["function"], root):
                out.append(f"{where}: function must name an existing file (path or path::name)")
            if not (isinstance(m["killed_by"], list) and m["killed_by"]
                    and all(str(k).startswith("tests/") and _file_exists(k, root) for k in m["killed_by"])):
                out.append(f"{where}: killed_by must name the tests that killed it (file, file::Class or a node)")
            if not isinstance(m["detail"], str) or not m["detail"]:
                out.append(f"{where}: detail must state the mutant as VALIDATION records it")
    return out


def discrimination_problems(doc: dict) -> list[str]:
    """D2 and D3 hold exactly when the structured records support them (the D-scope rule)."""
    out = []
    for f in doc["fixes"]:
        grade, can = f["discrimination"], supported_discrimination(f)
        nodes = {r["test"] for r in f.get("independence", [])}
        if grade in ("D2", "D3") and can == "D1":
            missing = sorted(nodes - valid_parent_failures(f)) if nodes else ["any regression test"]
            out.append(f"{f['id']}: {grade} needs a record that fails on the parent and passes on the fix for every "
                       f"oracle node; missing for {missing}")
        elif grade == "D3" and can != "D3":
            out.append(f"{f['id']}: D3 needs a killed revert mutant")
        elif can in ("D2", "D3") and grade != can:
            out.append(f"{f['id']}: the records support {can}, the ledger says {grade}")
    return out


def evidence_test_problems(doc: dict) -> list[str]:
    """evidence_tests lists the nodes used: each independence node and each parent-record node, nothing else."""
    out = []
    for f in doc["fixes"]:
        tests = f["evidence_tests"]
        ind = [r["test"] for r in f.get("independence", [])]
        rec = [r["test"] for r in f.get("parent_records", [])]
        out += [f"{f['id']}: evidence_tests lacks the independence node {n}" for n in ind if n not in tests]
        if len(tests) != len(set(tests)) or set(tests) != set(ind) | set(rec):
            out.append(f"{f['id']}: evidence_tests must list exactly the independence and parent-record nodes")
    return out


def superseded_problems(doc: dict) -> list[str]:
    """A tombstone (plan B6) names entries that exist and is not itself a live entry."""
    live = {f["id"] for f in doc["fixes"]}
    out = []
    for t in doc.get("superseded", []):
        if set(t) != {"id", "superseded_by", "note"} or not t["note"] or not t["superseded_by"]:
            out.append(f"{t.get('id')}: a tombstone has id, superseded_by and a note")
            continue
        if t["id"] in live | {f["id"] for f in doc["documentation_fixes"]}:
            out.append(f"{t['id']}: a superseded id is not a live entry")
        out += [f"{t['id']}: superseded_by {s} is not a ledger entry" for s in t["superseded_by"] if s not in live]
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
    needed = {n for _, rec in _requires_records(doc) for n in rec["requires"]["backend"]}
    return [f"backend {n} is locked by no required CI gate" for n in sorted(needed - locked)]


class SciFixLedger(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_vocabulary_tests_and_unique_ids(self):
        ids = [f["id"] for part in ("fixes", "documentation_fixes", "superseded") for f in self.doc.get(part, [])]
        self.assertEqual(len(ids), len(set(ids)))
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                self.assertIn(f["severity"], REQUIRED)
                self.assertIn(f["correctness"], C)
                self.assertIn(f["discrimination"], D)
                self.assertTrue(f["evidence_tests"])
                for t in f["evidence_tests"]:
                    self.assertIsNone(node_problem(t))
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
            for part in ("independence", "parent_records"):
                with self.subTest(expect=expect, part=part):
                    doc = copy.deepcopy(self.doc)
                    change(doc["fixes"][0][part][0])
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

    def test_expected_from_and_the_transcription_report(self):
        """Plan B2 (F-08): each independence record says where its expected value comes from; the report lists the C3
        entries whose every record computes it from a transcribed formula, and each such entry says so in gaps."""
        for f in self.doc["fixes"]:
            for rec in f.get("independence", []):
                with self.subTest(f["id"], test=rec["test"]):
                    self.assertIn(rec["expected_from"], scifix_ledger.EXPECTED_FROM)
                    if rec["basis"] == "exhaustive":
                        self.assertEqual(rec["expected_from"], "exhaustive")
            if scifix_ledger.transcription_only(f):
                self.assertTrue(any("transcription rule" in g for g in f["gaps"]), f["id"])
        rec = lambda e: {"expected_from": e}  # noqa: E731
        self.assertTrue(scifix_ledger.transcription_only({"correctness": "C3", "independence": [
            rec("transcribed-formula"), rec("transcribed-formula")]}))
        for other in ("printed", "third-party-definition", "exhaustive", "general-result", "person"):
            self.assertFalse(scifix_ledger.transcription_only({"correctness": "C3", "independence": [
                rec("transcribed-formula"), rec(other)]}), other)
        self.assertFalse(scifix_ledger.transcription_only({"correctness": "C2", "independence": [
            rec("transcribed-formula")]}))

    def test_s3_sources_meet_the_minimum_or_state_gaps(self):
        """Plan B5 (F-16): a documentation fix lists its sources; an S3 entry has a located external source and a
        second source, or says what is missing in gaps."""
        for x in self.doc["documentation_fixes"]:
            with self.subTest(x["id"]):
                for src in x["sources"]:
                    self.assertIn(src["kind"], ("external", "internal"))
                    self.assertTrue(src["citation"])
                    self.assertLessEqual(set(src), {"kind", "citation", "locator", "read"})
                if x["severity"] == "S3" and not scifix_ledger.s3_meets_minimum(x):
                    self.assertTrue(x["gaps"])
        ok = {"sources": [{"kind": "external", "citation": "a", "locator": "p. 1"}, {"kind": "internal", "citation": "b"}]}
        self.assertTrue(scifix_ledger.s3_meets_minimum(ok))
        self.assertFalse(scifix_ledger.s3_meets_minimum({"sources": ok["sources"][:1]}))
        self.assertFalse(scifix_ledger.s3_meets_minimum({"sources": [dict(ok["sources"][0], locator=None),
                                                                     ok["sources"][1]]}))
        self.assertFalse(scifix_ledger.s3_meets_minimum({"sources": [ok["sources"][1], dict(ok["sources"][1],
                                                                                            citation="c")]}))

    def test_review_sign_off_format(self):
        """Plan B7 (F-15): an entry's sign-off is review {by, date, scope}, distinct from a record's basis person; the
        report lists the S1 entries without one."""
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                if "review" in f:
                    self.assertEqual(set(f["review"]), {"by", "date", "scope"})
                    self.assertRegex(f["review"]["date"], r"^\d{4}-\d{2}-\d{2}$")
                    self.assertTrue(f["review"]["by"] and f["review"]["scope"])
        rep = scifix_ledger.report({"fixes": [
            {"id": "A", "severity": "S1", "correctness": "C3", "discrimination": "D2"},
            {"id": "B", "severity": "S1", "correctness": "C3", "discrimination": "D1",
             "review": {"by": "x", "date": "2026-10-22", "scope": "whole entry"}}]})
        self.assertEqual(rep["unsigned_s1"], ["A"])
        self.assertEqual(rep["below_minimum"], [{"id": "B", "severity": "S1", "grade": "C3D1", "minimum": "C3D2"}])
    def test_s1_and_s2_have_an_advisory_or_a_waiver(self):
        """Plan C2 (F-17): every S1 and S2 entry is named by an advisory or says why it has none."""
        named = set()
        for path in (ROOT / "docs" / "evidence" / "advisories").glob("SFA-*.json"):
            named |= set(json.loads(path.read_text(encoding="utf-8"))["ledger"])
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                waiver = f.get("advisory_waiver")
                if waiver is not None:
                    self.assertEqual(set(waiver), {"reason", "decided"})
                    self.assertTrue(waiver["reason"] and waiver["decided"])
                    self.assertNotIn(f["id"], named, "an entry with an advisory needs no waiver")
                if f["severity"] in ("S1", "S2"):
                    self.assertTrue(f["id"] in named or waiver, "S1 and S2 need an advisory or advisory_waiver")

    def test_regression_of_names_other_entries(self):
        """Plan C1 (F-13): regression_of lists the entries whose fix introduced this defect."""
        ids = {f["id"] for f in self.doc["fixes"]}
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                for ref in f.get("regression_of", []):
                    self.assertIn(ref, ids)
                    self.assertNotEqual(ref, f["id"])

    def test_entries_below_their_requirement_state_their_gaps(self):
        for f in self.doc["fixes"]:
            with self.subTest(f["id"]):
                if below(f):
                    self.assertTrue(f["gaps"], "an entry below its requirement must list what is missing")


SYN_ORACLE = ("tests/skills/hep_ml/test_audit_calibration_identity.py::SampleNameDotSegmentTests::"
              "test_dot_segments_anywhere_in_the_path_name_one_sample")
SYN_REGRESSION = "tests/core/test_status.py::SharedVocabulary::test_a_script_with_an_unknown_status_exits_3_without_a_traceback"
SYN_SECTIONS = {"SCIFIX-SAMPLE-NAME", "TRIAGE-A"}


def _record(test, parent="fail", fix="pass", failure="assertion", validation="SCIFIX-SAMPLE-NAME", **extra):
    return {"test": test, "parent": parent, "fix": fix, "failure": failure, "env": "ci-lock", "adapted_parent": False,
            "validation": validation, "requires": {"core": [], "backend": []}, **extra}


def synthetic(discrimination="D2", oracle=True) -> dict:
    """A one-entry ledger whose records support D2: the oracle node fails on the parent and passes on the fix."""
    ind = [{"kind": "independent-implementation", "test": SYN_ORACLE, "basis": "third-party", "detail": "pathlib",
            "requires": {"core": [], "backend": []}}] if oracle else []
    recs = ([_record(SYN_ORACLE)] if oracle else []) + [_record(SYN_REGRESSION, validation="TRIAGE-A")]
    return {"documentation_fixes": [], "fixes": [{
        "id": "SYN", "severity": "S2", "correctness": "C2" if oracle else "C1", "discrimination": discrimination,
        "commits": {"parent": "a" * 40, "fix": "b" * 40, "follow_up": []},
        "evidence_tests": [r["test"] for r in recs], "independence": ind, "parent_records": recs, "mutants": []}]}


class StructuredDiscrimination(unittest.TestCase):
    """Plan B3: commits, parent_records and mutants are structured, and D2 and D3 are recomputed from them under the
    D-scope rule. Each rule is checked on the ledger, on a synthetic ledger that obeys it and on ones that break it."""

    def setUp(self):
        self.doc = json.loads(LEDGER.read_text(encoding="utf-8"))
        self.sections = validation_sections((ROOT / "VALIDATION.md").read_text(encoding="utf-8"))

    def test_commits_are_full_hashes(self):
        self.assertEqual(commit_problems(self.doc), [])
        self.assertEqual(commit_problems(synthetic()), [])
        for change, expect in ((lambda c: c.update(parent="90388aa0"), "commits.parent must be a 40-hex"),
                               (lambda c: c.update(fix="B" * 40), "commits.fix must be a 40-hex"),
                               (lambda c: c.update(follow_up=["db40e842"]), "follow_up must be a list of 40-hex"),
                               (lambda c: c.update(follow_up="c" * 40), "follow_up must be a list of 40-hex"),
                               (lambda c: c.pop("follow_up"), "commits must be"),
                               (lambda c: c.update(fix="a" * 40), "different commits")):
            with self.subTest(expect=expect):
                doc = synthetic()
                change(doc["fixes"][0]["commits"])
                self.assertTrue(any(expect in p for p in commit_problems(doc)), commit_problems(doc))

    def test_parent_records_and_mutants_are_well_formed(self):
        self.assertEqual(record_problems(self.doc, self.sections), [])
        self.assertEqual(record_problems(synthetic(), SYN_SECTIONS), [])
        revert = {"function": "contracts/validate.py::_sample_name", "mutation": "revert", "killed_by": [SYN_ORACLE],
                  "detail": "the revert"}
        doc = synthetic()
        doc["fixes"][0]["mutants"].append(dict(revert))
        self.assertEqual(record_problems(doc, SYN_SECTIONS), [])
        for change, expect in (
                (lambda e: e["parent_records"][0].update(parent="failed"), "parent must be one of"),
                (lambda e: e["parent_records"][0].update(fix="ok"), "parent must be one of"),
                (lambda e: e["parent_records"][0].update(failure=None), "failure must be assertion or error"),
                (lambda e: e["parent_records"][0].update(parent="error"), "error when the parent result is error"),
                (lambda e: e["parent_records"][0].update(parent="pass"), "failure must be null"),
                (lambda e: e["parent_records"][0].update(env=""), "env must name"),
                (lambda e: e["parent_records"][0].pop("requires"), "keys must be"),
                (lambda e: e["parent_records"][0].update(test=SYN_ORACLE.replace("one_sample", "two")), "no such test"),
                (lambda e: e["parent_records"][0].update(test="tests/core/test_status.py"), "not a test node id"),
                (lambda e: e["parent_records"].append(copy.deepcopy(e["parent_records"][0])), "recorded twice"),
                (lambda e: e["mutants"].append(dict(revert, mutation="partial")), "mutation must be one of"),
                (lambda e: e["mutants"].append(dict(revert, killed_by=[])), "killed_by must name"),
                (lambda e: e["mutants"].append(dict(revert, killed_by=["toy study"])), "killed_by must name"),
                (lambda e: e["mutants"].append(dict(revert, function="core/nowhere.py::f")), "function must name"),
                (lambda e: e["mutants"].append({k: v for k, v in revert.items() if k != "detail"}), "keys must be")):
            with self.subTest(expect=expect):
                doc = synthetic()
                change(doc["fixes"][0])
                self.assertTrue(any(expect in p for p in record_problems(doc, SYN_SECTIONS)),
                                record_problems(doc, SYN_SECTIONS))

    def test_an_adapted_parent_only_adds_modules_or_guards_an_import(self):
        for adaptation in ADAPTATIONS:
            with self.subTest(allowed=adaptation):
                doc = synthetic()
                doc["fixes"][0]["parent_records"][0].update(adapted_parent=True, adaptation=adaptation)
                self.assertEqual(record_problems(doc, SYN_SECTIONS), [])
                self.assertEqual(discrimination_problems(doc), [])
        for change, expect in ((dict(adapted_parent=True), "plus adaptation exactly when adapted_parent"),
                               (dict(adaptation="adds new modules"), "plus adaptation exactly when adapted_parent"),
                               (dict(adapted_parent="yes", adaptation="adds new modules"), "true or false"),
                               (dict(adapted_parent=True, adaptation="replaces the code under test"),
                                "may only adds new modules or guards an import")):
            with self.subTest(change=change):
                doc = synthetic()
                doc["fixes"][0]["parent_records"][0].update(change)
                self.assertTrue(any(expect in p for p in record_problems(doc, SYN_SECTIONS)),
                                record_problems(doc, SYN_SECTIONS))
        doc = synthetic()
        doc["fixes"][0]["parent_records"][0].update(adapted_parent=True, adaptation="replaces the code under test")
        self.assertTrue(any("missing for" in p for p in discrimination_problems(doc)), "a disallowed adaptation is no D2")

    def test_each_named_validation_section_exists(self):
        self.assertTrue({"SCIFIX-PARENT-RECORDS", "SCIFIX-PLAN-B3-B6", "TRIAGE-A"} <= self.sections)
        named = {r["validation"] for f in self.doc["fixes"] for r in f["parent_records"]}
        self.assertTrue(named and named <= self.sections, named - self.sections)
        doc = synthetic()
        doc["fixes"][0]["parent_records"][1]["validation"] = "SCIFIX-NO-SUCH-SECTION"
        self.assertTrue(any("no section 'SCIFIX-NO-SUCH-SECTION'" in p for p in record_problems(doc, SYN_SECTIONS)))

    def test_d2_needs_a_parent_failure_of_every_oracle_node(self):
        """The D-scope rule: with records only for other regression tests the grade is at most D1."""
        self.assertEqual(discrimination_problems(self.doc), [])
        self.assertEqual(discrimination_problems(synthetic()), [])
        self.assertEqual(discrimination_problems(synthetic(oracle=False)), [], "no oracle node: a regression test")
        doc = synthetic("D1")
        doc["fixes"][0]["parent_records"][0].update(parent="error", failure="error")
        self.assertEqual(discrimination_problems(doc), [], "D1 with a record for a regression test only")
        for change, expect in (
                (lambda e: e["parent_records"][0].update(parent="error", failure="error"), "missing for"),
                (lambda e: e["parent_records"][0].update(parent="pass", failure=None), "missing for"),
                (lambda e: e["parent_records"][0].update(fix="fail"), "missing for"),
                (lambda e: e["parent_records"].pop(0), "missing for"),
                (lambda e: e.update(discrimination="D1"), "the records support D2, the ledger says D1")):
            with self.subTest(expect=expect):
                doc = synthetic()
                change(doc["fixes"][0])
                self.assertTrue(any(expect in p for p in discrimination_problems(doc)), discrimination_problems(doc))
        doc = synthetic(oracle=False)
        doc["fixes"][0]["parent_records"][0].update(parent="error", failure="error")
        self.assertTrue(any("any regression test" in p for p in discrimination_problems(doc)))
        for f in self.doc["fixes"]:
            if f["discrimination"] in ("D2", "D3"):
                with self.subTest(f["id"]):
                    self.assertLessEqual({r["test"] for r in f["independence"]}, valid_parent_failures(f))

    def test_d3_needs_a_killed_revert_mutant(self):
        revert = {"function": "contracts/validate.py::_sample_name", "mutation": "revert", "killed_by": [SYN_ORACLE],
                  "detail": "the revert"}
        doc = synthetic("D3")
        doc["fixes"][0]["mutants"].append(dict(revert))
        self.assertEqual(discrimination_problems(doc), [])
        for mutants, expect in (([], "D3 needs a killed revert mutant"),
                                ([dict(revert, mutation="other")], "D3 needs a killed revert mutant"),
                                ([dict(revert, killed_by=[])], "D3 needs a killed revert mutant")):
            with self.subTest(mutants=mutants):
                doc = synthetic("D3")
                doc["fixes"][0]["mutants"] = mutants
                self.assertTrue(any(expect in p for p in discrimination_problems(doc)), discrimination_problems(doc))
        doc = synthetic("D2")
        doc["fixes"][0]["mutants"].append(dict(revert))
        self.assertEqual(discrimination_problems(doc), ["SYN: the records support D3, the ledger says D2"])
        doc = synthetic("D3")
        doc["fixes"][0]["mutants"].append(dict(revert))
        doc["fixes"][0]["parent_records"][0].update(parent="error", failure="error")
        self.assertTrue(any("missing for" in p for p in discrimination_problems(doc)), "a mutant does not replace D2")
        for f in self.doc["fixes"]:
            if f["discrimination"] == "D3":
                with self.subTest(f["id"]):
                    self.assertTrue(any(m["mutation"] == "revert" and m["killed_by"] for m in f["mutants"]))

    def test_evidence_tests_are_the_nodes_used(self):
        self.assertEqual(evidence_test_problems(self.doc), [])
        self.assertEqual(evidence_test_problems(synthetic()), [])
        for change, expect in ((lambda e: e["evidence_tests"].remove(SYN_ORACLE), "lacks the independence node"),
                               (lambda e: e["evidence_tests"].append(SYN_ORACLE), "exactly"),
                               (lambda e: e["evidence_tests"].append(
                                   "tests/core/test_status.py::SharedVocabulary::test_x"), "exactly"),
                               (lambda e: e["evidence_tests"].remove(SYN_REGRESSION), "exactly")):
            with self.subTest(expect=expect):
                doc = synthetic()
                change(doc["fixes"][0])
                self.assertTrue(any(expect in p for p in evidence_test_problems(doc)), evidence_test_problems(doc))

    def test_ml_small_is_a_tombstone_split_into_one_entry_per_fix(self):
        """Plan B6: ML-SMALL bundled C10, C24, C25, C26 and K13; each code fix has its entry, K13 (a test fix) none."""
        self.assertEqual(superseded_problems(self.doc), [])
        ids = {f["id"] for f in self.doc["fixes"]}
        tomb = {t["id"]: t for t in self.doc["superseded"]}
        self.assertEqual(tomb["ML-SMALL"]["superseded_by"],
                         ["ML-SMALL-C10", "ML-SMALL-C24", "ML-SMALL-C25", "ML-SMALL-C26"])
        self.assertNotIn("ML-SMALL", ids)
        self.assertIn("K13", tomb["ML-SMALL"]["note"])
        self.assertFalse(any("K13" in f["title"] for f in self.doc["fixes"]))
        sfa = json.loads((ROOT / "docs" / "evidence" / "advisories" / "SFA-2026-025.json").read_text(encoding="utf-8"))
        self.assertEqual(sfa["ledger"], tomb["ML-SMALL"]["superseded_by"])
        c10 = next(f for f in self.doc["fixes"] if f["id"] == "ML-SMALL-C10")
        self.assertEqual(c10["commits"]["follow_up"], ["db40e842474e196192af05474f5e8b3c3a4bc4ee"])
        for change, expect in ((lambda d: d["superseded"].append(
                {"id": "SYN", "superseded_by": ["SYN"], "note": "x"}), "not a live entry"),
                               (lambda d: d["superseded"].append(
                {"id": "OLD", "superseded_by": ["NOPE"], "note": "x"}), "is not a ledger entry"),
                               (lambda d: d["superseded"].append({"id": "OLD", "superseded_by": ["SYN"]}),
                                "a tombstone has")):
            with self.subTest(expect=expect):
                doc = synthetic()
                doc["superseded"] = []
                change(doc)
                self.assertTrue(any(expect in p for p in superseded_problems(doc)), superseded_problems(doc))


if __name__ == "__main__":
    unittest.main()
