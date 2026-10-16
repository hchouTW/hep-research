"""v6.3 D02: core/evidence/query.py. Rows are faithful to the ledger records they cite; paging is stable, bound to the
ledger snapshot and the query, capped by rows and bytes; a row larger than the cap is never cut but fetched on its own;
a ledger with errors serves nothing. Uses the public ledgers in the checkout (the ams-02 one only when present: the
AMS-optional copy removes it) and small synthetic ledgers."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.evidence import query as q  # noqa: E402

LEDGER = ROOT / "docs" / "evidence" / "statistics"
PUBLIC_LEDGERS = [d for d in (LEDGER, ROOT / "profiles" / "experiments" / "eic" / "evidence",
                              ROOT / "profiles" / "experiments" / "ams-02" / "evidence") if (d / "claims.json").is_file()]
TODAY = date(2026, 10, 16)
FILES = {"sources": "sources.json", "claims": "claims.json"}


def source(sid, **kw):
    return dict({"id": sid, "title": f"title {sid}", "authors": "synthetic", "tier": 1, "verification_level": "full-text",
                 "verification_date": "2026-01-01", "supersedes": [], "superseded_by": []}, **kw)


def claim(cid, sids, text="synthetic claim", **kw):
    return dict({"id": cid, "claim": text, "claim_types": ["general_method"], "support_kind": "general_method",
                 "source_ids": sids, "location": f"section of {cid}", "scope": {"text": f"scope of {cid}"},
                 "verification_strength": "full-text", "numeric_quotation_allowed": False,
                 "last_reviewed": "2026-01-01"}, **kw)


def enc(obj) -> bytes:
    return json.dumps(obj).encode()


def cli(*argv) -> tuple[int, dict]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = q.main([str(a) for a in argv])
    return code, json.loads(buf.getvalue())


class PublicLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sb, cls.cb = (LEDGER / "sources.json").read_bytes(), (LEDGER / "claims.json").read_bytes()
        cls.sources, cls.claims = json.loads(cls.sb), json.loads(cls.cb)

    def pages(self, sb=None, cb=None, **kw):
        out, cursor = [], None
        while True:
            page = q.query_ledger(sb or self.sb, cb or self.cb, FILES, cursor=cursor, today=TODAY, **kw)
            self.assertEqual(page["status"], "ok", page)
            out.append(page)
            cursor = page["next_cursor"]
            if cursor is None:
                return out

    def test_every_field_equals_the_ledger_record(self):
        for d in PUBLIC_LEDGERS:
            with self.subTest(ledger=d.relative_to(ROOT).as_posix()):
                self.check_fidelity((d / "sources.json").read_bytes(), (d / "claims.json").read_bytes())

    def check_fidelity(self, sb, cb):
        sources, claims = json.loads(sb), json.loads(cb)
        rows = [r for p in self.pages(sb, cb, page_size=q.PAGE_SIZE_MAX) for r in p["rows"]]
        self.assertEqual(len(rows), sum(len(c["source_ids"]) for c in claims))
        for r in rows:
            c, s = claims[r["record"]["claim_index"]], sources[r["record"]["source_index"]]
            self.assertEqual((r["claim_id"], r["claim"], r["scope"], r["location"], r["verification_strength"]),
                             (c["id"], c["claim"], c["scope"], c["location"], c["verification_strength"]))
            self.assertIn(r["source_id"], c["source_ids"])
            self.assertEqual((r["source_id"], r["source_title"], r["verification_level"]),
                             (s["id"], s["title"], s["verification_level"]))
            self.assertEqual(r["verification_date"], s.get("verification_date", s.get("access_date")))
            self.assertEqual(r["record"]["claims_file"], "claims.json")

    def test_paging_is_complete_stable_and_capped(self):
        pages = self.pages(page_size=5, max_bytes=4000)
        rows = [(r["claim_id"], r["source_id"]) for p in pages for r in p["rows"]]
        self.assertEqual(rows, sorted(rows))
        self.assertEqual(len(rows), len(set(rows)))
        self.assertEqual({p["total_matches"] for p in pages}, {len(rows)})
        self.assertEqual({p["index_digest"] for p in pages}, {q.index_digest(self.sb, self.cb)})
        for p in pages:
            self.assertLessEqual(p["returned"], 5)
            self.assertLessEqual(len(q._dumps(p).encode()), 4000)
        self.assertGreater(len(pages), 3)
        self.assertEqual(rows, [(r["claim_id"], r["source_id"]) for p in self.pages(page_size=5, max_bytes=4000)
                                for r in p["rows"]])

    def test_default_page_respects_the_byte_cap(self):
        code, page = cli("--sources", LEDGER / "sources.json", "--claims", LEDGER / "claims.json", "--today", "2026-10-16")
        self.assertEqual(code, 0)
        self.assertLessEqual(page["returned"], q.PAGE_SIZE)
        self.assertLessEqual(len(q._dumps(page).encode()), q.MAX_BYTES)
        self.assertEqual(page["limits"]["max_bytes"], 16384)

    def test_filters(self):
        cid = self.claims[0]["id"]
        rows = [r for p in self.pages(claim=cid) for r in p["rows"]]
        self.assertEqual({r["claim_id"] for r in rows}, {cid})
        everything = [r for p in self.pages() for r in p["rows"]]
        strong = [r for p in self.pages(min_strength="full-text") for r in p["rows"]]
        self.assertEqual(strong, [r for r in everything if r["verification_strength"] == "full-text"])

    def test_changed_ledger_refuses_the_cursor(self):
        first = q.query_ledger(self.sb, self.cb, FILES, page_size=5, today=TODAY)
        with self.assertRaises(q.QueryRefused) as ctx:
            q.query_ledger(self.sb, self.cb + b"\n", FILES, page_size=5, cursor=first["next_cursor"], today=TODAY)
        self.assertEqual(ctx.exception.code, "query.stale_cursor")

    def test_another_query_refuses_the_cursor(self):
        first = q.query_ledger(self.sb, self.cb, FILES, page_size=5, today=TODAY)
        with self.assertRaises(q.QueryRefused) as ctx:
            q.query_ledger(self.sb, self.cb, FILES, page_size=5, match="fit", cursor=first["next_cursor"], today=TODAY)
        self.assertEqual(ctx.exception.code, "query.cursor_mismatch")


class SyntheticLedger(unittest.TestCase):
    def test_a_row_over_the_cap_is_fetched_on_its_own(self):
        big = "x" * 5000
        sources = [source("S01")]
        claims = [claim("C01", ["S01"]), claim("C02", ["S01"], text=big), claim("C03", ["S01"])]
        with tempfile.TemporaryDirectory() as td:
            sp, cp = Path(td) / "sources.json", Path(td) / "claims.json"
            sp.write_bytes(enc(sources))
            cp.write_bytes(enc(claims))
            files = {"sources": str(sp), "claims": str(cp)}
            p1 = q.query_ledger(sp.read_bytes(), cp.read_bytes(), files, page_size=20, max_bytes=2048, today=TODAY)
            self.assertEqual([r["claim_id"] for r in p1["rows"]], ["C01"])
            p2 = q.query_ledger(sp.read_bytes(), cp.read_bytes(), files, page_size=20, max_bytes=2048,
                                cursor=p1["next_cursor"], today=TODAY)
            self.assertEqual(p2["rows"], [])
            self.assertEqual((p2["overflow"]["row_offset"], p2["overflow"]["claim_id"]), (1, "C02"))
            self.assertGreater(p2["overflow"]["bytes"], 2048)
            p3 = q.query_ledger(sp.read_bytes(), cp.read_bytes(), files, page_size=20, max_bytes=2048,
                                cursor=p2["next_cursor"], today=TODAY)
            self.assertEqual([r["claim_id"] for r in p3["rows"]], ["C03"])
            fetch = p2["overflow"]["fetch"]
            self.assertEqual(fetch[:2], ["python3", "core/evidence/query.py"])
            code, row = cli(*fetch[2:], "--today", "2026-10-16")
        self.assertEqual(code, 0, row)
        self.assertEqual([(r["claim_id"], r["claim"]) for r in row["rows"]], [("C02", big)])

    def test_a_ledger_with_errors_serves_nothing(self):
        sb, cb = enc([source("S01")]), enc([claim("C01", ["S99"])])
        out = q.query_ledger(sb, cb, FILES, today=TODAY)
        self.assertEqual(out["status"], "ledger_invalid")
        self.assertNotIn("rows", out)
        self.assertIn("claim.broken_source", {e["code"] for e in out["errors"]})
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "s.json").write_bytes(sb)
            (Path(td) / "c.json").write_bytes(cb)
            code, _ = cli("--sources", Path(td) / "s.json", "--claims", Path(td) / "c.json", "--today", "2026-10-16")
        self.assertEqual(code, 1)

    def test_access_date_fallback_is_named(self):
        s = source("S01")
        s["access_date"] = s.pop("verification_date")
        out = q.query_ledger(enc([s]), enc([claim("C01", ["S01"])]), FILES, today=TODAY)
        self.assertEqual((out["rows"][0]["verification_date"], out["rows"][0]["verification_date_field"]),
                         ("2026-01-01", "access_date"))

    def test_bad_arguments_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "s.json").write_bytes(enc([source("S01")]))
            (Path(td) / "c.json").write_bytes(enc([claim("C01", ["S01"])]))
            base = ["--sources", Path(td) / "s.json", "--claims", Path(td) / "c.json"]
            for extra, code_expected in ((["--page-size", "0"], "query.bad_page_size"),
                                         (["--max-bytes", "100"], "query.bad_max_bytes"),
                                         (["--min-strength", "strong"], "query.bad_strength"),
                                         (["--cursor", "%%%"], "query.bad_cursor")):
                with self.subTest(extra=extra):
                    code, out = cli(*base, *extra)
                    self.assertEqual((code, out["status"], out["code"]), (2, "refused", code_expected))
            code, out = cli("--sources", Path(td) / "missing.json", "--claims", Path(td) / "c.json")
            self.assertEqual((code, out["status"]), (2, "unreadable"))

    def test_no_match_is_an_empty_ok_page(self):
        out = q.query_ledger(enc([source("S01")]), enc([claim("C01", ["S01"])]), FILES, match="absent", today=TODAY)
        self.assertEqual((out["status"], out["total_matches"], out["rows"], out["next_cursor"]), ("ok", 0, [], None))


if __name__ == "__main__":
    unittest.main()
