"""Tests of the shipped AMS-02 evidence ledger with core/evidence/ledger.py and render_index.py.
IDs are profile-qualified (ams02:S04), the date a source was read is verification_date, the
index is evidence/index.md and the modules are modules/*.md, and the CLIs take explicit paths.
The shipped ledger must pass; each mutation test starts from the shipped data,
introduces one controlled defect, and asserts the intended diagnostic. Also covers
ledger content retention (IDs, scope and limitation text) and index rendering.
Run from the profile folder with `python3 -m unittest discover -s tests -t tests -v`."""
import contextlib
import copy
import io
import json
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root
from core.evidence import ledger as vel  # noqa: E402
from core.evidence import render_index as rsi  # noqa: E402

NS = "ams02"
SOURCES, CLAIMS, INDEX = ROOT / "evidence" / "sources.json", ROOT / "evidence" / "claims.json", ROOT / "evidence" / "index.md"


def q(*ids):
    """Profile-qualified form of a bare ID: q(q("S04")) == "ams02:S04"."""
    out = [f"{NS}:{i}" for i in ids]
    return out[0] if len(ids) == 1 else out

TODAY = date(2026, 10, 2)


def ledger():
    sources, claims = vel.load_ledger(SOURCES, CLAIMS)
    return copy.deepcopy(sources), copy.deepcopy(claims)


def find(items, item_id):
    return next(i for i in items if i["id"] == item_id)


def codes(report, kind="errors"):
    return {e["code"] for e in report[kind]}


def run(sources, claims, today=TODAY, stale_days=365):
    return vel.check_ledger(sources, claims, today, stale_days, NS)


class ShippedLedgerTests(unittest.TestCase):
    def test_shipped_ledger_is_valid(self):
        report = run(*ledger())
        self.assertEqual(report["status"], "pass", report["errors"] + report["warnings"])
        self.assertEqual(report["counts"], {"sources": 60, "claims": 184})

    def test_c184_is_the_s06_break_fit(self):
        # transcribed from the cached S06 PDF, page 171103-6
        sources, claims = ledger()
        c = [x for x in claims if x["id"] == q("C184")][0]
        self.assertEqual(c["source_ids"], [q("S06")])
        self.assertEqual(c["scope"]["range"], "45 GV-1.8 TV")
        for value in ("R0 = 336 +68/-44 (fit) +66/-28 (sys) +- 1 (sol) GV", "chi2/d.f. = 25/26", "gamma = -2.849"):
            self.assertIn(value, c["claim"])

    def test_cosmic_ray_database_rows_stay_secondary_and_unverified_where_unread(self):
        sources, claims = ledger()
        by = {s["id"]: s for s in sources}
        for sid in (q("S50"), q("S51"), q("S52"), q("S53")):
            self.assertEqual(by[sid]["tier"], 6, sid)
        self.assertEqual(by[q("S52")]["verification_level"], "page")
        self.assertEqual(by[q("S52")]["verification_date"], "2026-10-02")
        self.assertEqual([c["id"] for c in claims if q("S52") in c["source_ids"]], [q("C183")])
        for cid in (q("C125"), q("C126"), q("C127"), q("C128"), q("C129"), q("C130"), q("C183")):
            c = find(claims, cid)
            self.assertEqual(c["support_kind"], "third_party_context", cid)
            self.assertNotEqual(c["verification_strength"], "full-text", cid)
        self.assertIn("not a primary AMS source", find(claims, q("C125"))["limitations"])

    def test_namespace_is_required(self):
        sources, claims = ledger()
        find(sources, q("S04"))["id"] = "S04"
        self.assertIn("source.bad_id", codes(run(sources, claims)))

    def test_ledger_ids_are_contiguous(self):
        sources, claims = ledger()
        self.assertEqual([s["id"] for s in sources], [q(f"S{n:02d}") for n in range(1, 61)])
        self.assertEqual(sorted(c["id"] for c in claims), sorted(q(f"C{n:02d}") for n in range(1, 185)))

    def test_scope_and_limitation_text_are_kept(self):
        _, claims = ledger()
        for c in claims:
            self.assertTrue(c["scope"]["text"], c["id"])
        self.assertIn("Supplemental cuts not read", find(claims, q("C20"))["limitations"])
        self.assertIn("Supplemental Material not read", find(claims, q("C27"))["limitations"])
        self.assertIn("Gaussian-core widths only", find(claims, q("C28"))["limitations"])
        self.assertIn("search-limited", find(claims, q("C14"))["scope"]["text"])
        self.assertIn("re-read in the paper before quoting a breakdown", find(claims, q("C23"))["limitations"])

    def test_source_qualifications_are_kept(self):
        sources, _ = ledger()
        self.assertEqual(find(sources, q("S10"))["verification_note"], "downloaded; only its data period was read")
        self.assertEqual(find(sources, q("S27"))["verification_level"], "not-opened")
        self.assertIn("main article only", find(sources, q("S04"))["verification_note"])
        self.assertEqual(find(sources, q("S26"))["tier_range"], [5, 6])
        # a source whose read date is not known carries the explicit marker "unknown"
        self.assertEqual(find(sources, q("S19"))["verification_date"], "unknown")
        self.assertEqual(find(sources, q("S02"))["superseded_by"], [q("S03")])
        self.assertEqual(find(sources, q("S03"))["supersedes"], [q("S02")])

    def test_publication_date_and_data_period_are_separate_fields(self):
        s15 = find(ledger()[0], q("S15"))
        self.assertEqual(s15["publication_date"], "2026-06-17")
        self.assertEqual(s15["data_taking_period"]["end"], "2024-11-26")

    def test_every_cited_source_id_in_references_exists(self):
        sources, claims = ledger()
        known = {s["id"] for s in sources}
        for path in (ROOT / "modules").glob("*.md"):
            # module prose cites short IDs; each must exist in this profile's namespace
            for sid in set(re.findall(r"\bS\d\d\b", path.read_text(encoding="utf-8"))):
                self.assertIn(q(sid), known, f"{path.name}: {sid}")
            for cid in set(re.findall(r"\bC\d\d\d?\b", path.read_text(encoding="utf-8"))):
                self.assertIn(q(cid), {c["id"] for c in claims}, f"{path.name}: {cid}")


class SourceDefectTests(unittest.TestCase):
    def test_duplicate_source_id(self):
        sources, claims = ledger()
        sources.append(copy.deepcopy(sources[0]))
        self.assertIn("source.duplicate_id", codes(run(sources, claims)))

    def test_invalid_verification_state(self):
        sources, claims = ledger()
        find(sources, q("S04"))["verification_level"] = "fully-verified"
        self.assertIn("source.bad_verification_level", codes(run(sources, claims)))

    def test_missing_required_field(self):
        sources, claims = ledger()
        del find(sources, q("S06"))["title"]
        self.assertIn("source.missing_field", codes(run(sources, claims)))

    def test_bad_tier_and_dates(self):
        sources, claims = ledger()
        find(sources, q("S04"))["tier"] = 9
        find(sources, q("S06"))["verification_date"] = "20-09-2026"
        find(sources, q("S08"))["publication_date"] = "Sept 2016"
        report = run(sources, claims)
        self.assertTrue({"source.bad_tier", "source.bad_date"} <= codes(report))

    def test_future_access_date_and_published_after_access(self):
        sources, claims = ledger()
        find(sources, q("S04"))["verification_date"] = "2027-01-01"
        find(sources, q("S06"))["year"] = 2030
        report = run(sources, claims)
        self.assertIn("source.future_access_date", codes(report))
        self.assertIn("source.published_after_access", codes(report))

    def test_read_level_without_access_date(self):
        sources, claims = ledger()
        find(sources, q("S04"))["verification_date"] = None
        self.assertIn("source.level_without_access_date", codes(run(sources, claims)))

    def test_broken_supersession_target(self):
        sources, claims = ledger()
        find(sources, q("S04"))["superseded_by"] = [q("S99")]
        self.assertIn("source.broken_relation", codes(run(sources, claims)))

    def test_asymmetric_supersession(self):
        sources, claims = ledger()
        find(sources, q("S03"))["supersedes"] = []
        self.assertIn("source.asymmetric_relation", codes(run(sources, claims)))

    def test_self_supersession(self):
        sources, claims = ledger()
        find(sources, q("S06"))["supersedes"] = [q("S06")]
        find(sources, q("S06"))["superseded_by"] = [q("S06")]
        self.assertIn("source.self_supersession", codes(run(sources, claims)))

    def test_supersession_cycle(self):
        sources, claims = ledger()
        for a, b in ((q("S04"), q("S05")), (q("S05"), q("S04"))):
            find(sources, a)["supersedes"].append(b)
            find(sources, b)["superseded_by"].append(a)
        self.assertIn("source.supersession_cycle", codes(run(sources, claims)))


class ClaimDefectTests(unittest.TestCase):
    def test_duplicate_claim_id(self):
        sources, claims = ledger()
        claims.append(copy.deepcopy(claims[0]))
        self.assertIn("claim.duplicate_id", codes(run(sources, claims)))

    def test_broken_source_reference(self):
        sources, claims = ledger()
        find(claims, q("C20"))["source_ids"] = [q("S08"), q("S99")]
        self.assertIn("claim.broken_source", codes(run(sources, claims)))

    def test_invalid_claim_type_and_strength(self):
        sources, claims = ledger()
        find(claims, q("C20"))["claim_types"] = ["rumour"]
        find(claims, q("C21"))["verification_strength"] = "confirmed"
        report = run(sources, claims)
        self.assertTrue({"claim.bad_type", "claim.bad_verification_strength"} <= codes(report))

    def test_claim_stronger_than_its_source(self):
        sources, claims = ledger()
        find(claims, q("C11"))["source_ids"] = [q("S20")]          # a metadata-only source
        find(claims, q("C11"))["verification_strength"] = "full-text"
        self.assertIn("claim.stronger_than_sources", codes(run(sources, claims)))

    def test_source_downgrade_exposes_over_strong_claims(self):
        sources, claims = ledger()
        find(sources, q("S08"))["verification_level"] = "metadata-only"
        report = run(sources, claims)
        flagged = {e["where"] for e in report["errors"] if e["code"] == "claim.stronger_than_sources"}
        self.assertTrue({q("C20"), q("C22"), q("C23")} <= flagged, flagged)

    def test_numeric_quotation_on_metadata_only_claim(self):
        sources, claims = ledger()
        find(claims, q("C16"))["numeric_quotation_allowed"] = True
        self.assertIn("claim.numeric_without_reading", codes(run(sources, claims)))

    def test_ams_practice_claim_resting_on_third_party_source(self):
        sources, claims = ledger()
        c = find(claims, q("C15"))
        c["support_kind"] = "primary"
        self.assertIn("claim.no_primary_source", codes(run(sources, claims)))

    def test_ams_practice_claim_resting_on_tier_3_source(self):
        sources, claims = ledger()
        c = find(claims, q("C14"))
        c.update({"support_kind": "primary", "source_ids": [q("S24")]})  # thesis/talk, tier 3
        self.assertIn("claim.no_primary_source", codes(run(sources, claims)))

    def test_missing_scope_blocks_a_claim(self):
        sources, claims = ledger()
        find(claims, q("C20"))["scope"] = {"text": ""}
        self.assertIn("claim.missing_scope", codes(run(sources, claims)))

    def test_bad_review_date(self):
        sources, claims = ledger()
        find(claims, q("C20"))["last_reviewed"] = "yesterday"
        self.assertIn("claim.bad_date", codes(run(sources, claims)))

    def test_malformed_ledger(self):
        self.assertIn("ledger.malformed", codes(vel.check_ledger({}, [], TODAY)))


class StalenessTests(unittest.TestCase):
    def test_stale_dates_are_notes_not_errors(self):
        sources, claims = ledger()
        report = run(sources, claims, today=date(2028, 1, 1))
        self.assertEqual(report["status"], "pass")
        self.assertIn("stale.source", codes(report, "notes"))
        note = next(n for n in report["notes"] if n["code"] == "stale.source")
        self.assertIn("does not mean the source is obsolete", note["message"])

    def test_fresh_ledger_has_no_stale_notes(self):
        report = run(*ledger())
        self.assertFalse({"stale.source", "stale.claim"} & codes(report, "notes"))


class RenderTests(unittest.TestCase):
    def test_shipped_index_is_in_sync(self):
        sources, claims = ledger()
        text = INDEX.read_text(encoding="utf-8")
        ok, detail = rsi.check_index(text, sources, claims)
        self.assertTrue(ok, detail)

    def test_changed_claim_is_detected(self):
        sources, claims = ledger()
        find(claims, q("C31"))["claim"] += " (edited)"
        text = INDEX.read_text(encoding="utf-8")
        ok, detail = rsi.check_index(text, sources, claims)
        self.assertFalse(ok)
        self.assertIn(q("C31"), detail)

    def test_write_is_idempotent_and_repairs_drift(self):
        sources, claims = ledger()
        text = INDEX.read_text(encoding="utf-8")
        self.assertEqual(rsi.write_index(text, sources, claims), text)
        drifted = text.replace("| ams02:S06 |", "| ams02:S06 | DRIFT", 1)
        self.assertFalse(rsi.check_index(drifted, sources, claims)[0])
        self.assertTrue(rsi.check_index(rsi.write_index(drifted, sources, claims), sources, claims)[0])

    def test_prose_outside_markers_is_untouched(self):
        sources, claims = ledger()
        text = INDEX.read_text(encoding="utf-8")
        marker = "\n## Failure modes\n"
        self.assertIn(marker, text)
        rewritten = rsi.write_index(text.replace("| ams02:S06 |", "| ams02:S06 | DRIFT", 1), sources, claims)
        self.assertEqual(rewritten.split(marker)[1], text.split(marker)[1])

    def test_missing_markers_reported(self):
        sources, claims = ledger()
        ok, detail = rsi.check_index("# no tables here\n", sources, claims)
        self.assertFalse(ok)
        self.assertIn("missing GENERATED block", detail)
        with self.assertRaises(ValueError):
            rsi.write_index("# no tables here\n", sources, claims)

    def test_pipe_in_cell_is_escaped(self):
        sources, claims = ledger()
        self.assertIn("\\|Z\\|", rsi.render_tables(sources, claims)["claim-ledger"])

    def test_compress_only_long_runs(self):
        self.assertEqual(rsi._compress(["S30", "S31", "S32", "S33", "S34"]), "S30-S34")
        self.assertEqual(rsi._compress(["S08", "S04", "S05", "S06"]), "S08, S04, S05, S06")
        # qualified IDs compress the same way and keep their namespace on both ends
        self.assertEqual(rsi._compress(list(q("S30", "S31", "S32", "S33", "S34"))), "ams02:S30-ams02:S34")
        self.assertEqual(rsi._compress(["a:S01", "a:S02", "b:S03", "b:S04"]), "a:S01, a:S02, b:S03, b:S04")


class CliTests(unittest.TestCase):
    def cli(self, module, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = module.main(list(argv))
        return code, buf.getvalue()

    def test_validator_exit_codes(self):
        ledger_args = ("--sources", str(SOURCES), "--namespace", NS)
        self.assertEqual(self.cli(vel, *ledger_args, "--claims", str(CLAIMS), "--today", "2026-10-02")[0], 0)
        sources, claims = ledger()
        claims.append(copy.deepcopy(claims[0]))
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "claims.json"
            bad.write_text(json.dumps(claims), encoding="utf-8")
            code, out = self.cli(vel, *ledger_args, "--claims", str(bad), "--today", "2026-09-20")
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["status"], "fail")
            self.assertEqual(self.cli(vel, *ledger_args, "--claims", str(Path(tmp) / "absent.json"))[0], 2)
        self.assertEqual(self.cli(vel, *ledger_args, "--claims", str(CLAIMS), "--today", "not-a-date")[0], 2)

    def test_renderer_exit_codes(self):
        paths = ("--sources", str(SOURCES), "--claims", str(CLAIMS))
        self.assertEqual(self.cli(rsi, *paths, "--index", str(INDEX))[0], 0)
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.md"
            index.write_text("# nothing\n", encoding="utf-8")
            self.assertEqual(self.cli(rsi, *paths, "--index", str(index))[0], 1)
            self.assertEqual(self.cli(rsi, *paths, "--index", str(index), "--write")[0], 2)
        self.assertEqual(self.cli(rsi, *paths, "--index", "/nonexistent/index.md")[0], 2)


if __name__ == "__main__":
    unittest.main()
