"""Tests for scripts/fetch_papers.py and data/papers_manifest.json.

Network access is never used: the HTTP layer is replaced by a fake that maps URLs to
responses. Covers the shipped manifest (schema, unique keys and DOIs, ledger
cross-check), manifest-row construction from INSPIRE and OpenAlex records, the
download rules (PDF magic, bot-verification and 401/403/429 recorded as blocked and
never retried, one retry for transient errors only, size cap, preprint and repository
labels, idempotent re-fetch, dry run), opt-in APS supplement discovery and download, safe file names, adopting
user-downloaded files, hash verification, and the command-line exit codes.
Run from the skill directory with `python3 -m unittest discover -s tests -v`."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root: core/, contracts/
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_papers as fp  # noqa: E402

PDF = b"%PDF-1.5\n" + b"x" * 200
DOI = "10.1103/PhysRevLett.110.141102"
KEY = "10.1103_PhysRevLett.110.141102"


class FakeHttp:
    def __init__(self, table):
        self.table, self.calls = table, []

    def get(self, url, max_bytes):
        self.calls.append(url)
        r = self.table.get(url, fp.Response(404, "text/html", b"not found", url))
        return fp.Response(r.status, r.content_type, r.data[: max_bytes + 1], r.url)


def ok(data=PDF, url=""):
    return fp.Response(200, "application/pdf", data, url)


def entry(candidates=None, supp=None, key=KEY, doi=DOI):
    return {"key": key, "doi": doi, "inspire_id": 1, "title": "t", "journal_ref": "PRL", "date": "2013-04-03",
            "generation": "ams-02", "publisher": "aps", "source_ids": [], "arxiv": [],
            "pdf_candidates": candidates if candidates is not None else
            [{"url": "https://journals.aps.org/prl/pdf/" + doi, "kind": "publisher"}],
            "supplement_pages": supp or []}


def fetcher(table, tmp, **kw):
    cache = fp.Cache(Path(tmp) / "cache")
    return fp.Fetcher(cache, http=FakeHttp(table), delay=0, sleep=lambda s: None, log=lambda s: None, **kw), cache


def run_cli(argv, http=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = fp.main(argv, http=http)
    return code, out.getvalue()


class ShippedManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / "evidence" / "papers_manifest.json").read_text(encoding="utf-8"))
        self.ledger = fp.ledger_dois()

    def test_manifest_passes_its_own_check(self):
        self.assertEqual(fp.check_manifest(self.manifest, self.ledger), [])

    def test_known_papers_present_and_linked_to_ledger(self):
        by = {p["doi"]: p for p in self.manifest["papers"] if p["doi"]}
        # M2: ledger source IDs are profile-qualified (legacy "S02" is now "ams02:S02")
        self.assertEqual(by[DOI]["source_ids"], ["ams02:S02"])
        self.assertEqual(sorted(by["10.1103/PhysRevLett.121.051101"]["source_ids"]), ["ams02:S16", "ams02:S41"])
        self.assertEqual(by["10.1016/j.physrep.2020.09.003"]["source_ids"], ["ams02:S01"])
        self.assertGreaterEqual(len(self.manifest["papers"]), 50)

    def test_every_candidate_is_https_and_labeled(self):
        for p in self.manifest["papers"]:
            for c in p["pdf_candidates"]:
                self.assertTrue(c["url"].startswith("https://"), p["key"])
                self.assertIn(c["kind"], fp.CANDIDATE_KINDS)

    def test_supplement_pages_only_for_aps_prl_entries(self):
        for p in self.manifest["papers"]:
            pages = p["supplement_pages"]
            aps = p["pdf_candidates"] and p["pdf_candidates"][0]["url"].startswith("https://journals.aps.org/prl/pdf/")
            self.assertEqual(pages, [f"https://journals.aps.org/prl/supplemental/{p['doi']}"] if aps else [], p["key"])

    def test_no_pdf_is_shipped_and_manifest_is_metadata_only(self):
        text = json.dumps(self.manifest)
        self.assertNotIn("%PDF", text)
        self.assertEqual(list((ROOT / "evidence").glob("*.pdf")), [])


class CheckManifestTests(unittest.TestCase):
    def base(self):
        return {"papers": [entry()]}, {DOI.lower(): ["S02"]}

    def test_detects_defects(self):
        m, led = self.base()
        m["papers"][0]["source_ids"] = ["S02"]
        self.assertEqual(fp.check_manifest(m, led, {"S02"}), [])
        bad = copy.deepcopy(m)
        bad["papers"][0]["key"] = "../evil"
        self.assertTrue(any("safe file name" in x for x in fp.check_manifest(bad, led)))
        bad = copy.deepcopy(m)
        bad["papers"].append(copy.deepcopy(bad["papers"][0]))
        probs = fp.check_manifest(bad, led)
        self.assertTrue(any("duplicate key" in x for x in probs) and any("duplicate doi" in x for x in probs))
        bad = copy.deepcopy(m)
        bad["papers"][0]["pdf_candidates"] = [{"url": "http://x/y.pdf", "kind": "publisher"}]
        self.assertTrue(any("bad candidate" in x for x in fp.check_manifest(bad, led)))
        bad = copy.deepcopy(m)
        bad["papers"][0]["source_ids"] = []
        self.assertTrue(any("differ from the ledger" in x for x in fp.check_manifest(bad, led)))
        bad = copy.deepcopy(m)
        bad["papers"][0]["supplement_pages"] = ["https://evil.example/x"]
        self.assertTrue(any("bad supplement page" in x for x in fp.check_manifest(bad, led)))
        bad = copy.deepcopy(m)
        bad["papers"][0]["source_ids"] = []
        del bad["papers"][0]["title"]
        self.assertTrue(any("missing field title" in x for x in fp.check_manifest(bad, led)))
        self.assertEqual(fp.check_manifest({}, led), ["manifest has no 'papers' list"])

    def test_ledger_prl_missing_from_manifest(self):
        m, _ = self.base()
        led = {DOI.lower(): [], "10.1103/physrevlett.999.000001": ["S99"]}
        self.assertTrue(any("not in the manifest" in x for x in fp.check_manifest(m, led)))


class BuildEntryTests(unittest.TestCase):
    HIT = {"metadata": {"control_number": 42, "titles": [{"title": "First   Result  AMS-02"}],
                        "dois": [{"value": DOI}], "earliest_date": "2013-04-03",
                        "publication_info": [{"journal_title": "Phys.Rev.Lett.", "journal_volume": "110",
                                              "artid": "141102", "year": 2013}],
                        "arxiv_eprints": [{"value": "1303.0001"}]}}
    OA = {"open_access": {"oa_status": "bronze"},
          "locations": [{"pdf_url": "http://link.aps.org/pdf/" + DOI}, {"pdf_url": "http://hal.example/x.pdf"},
                        {"pdf_url": None}, {"pdf_url": "http://hal.example/x.pdf"}]}

    def test_row(self):
        e = fp.build_entry(self.HIT, self.OA, {DOI.lower(): ["S02"]})
        self.assertEqual((e["key"], e["publisher"], e["generation"], e["source_ids"], e["oa_status"]),
                         (KEY, "aps", "ams-02", ["S02"], "bronze"))
        self.assertEqual(e["title"], "First Result AMS-02")
        urls = [(c["url"], c["kind"]) for c in e["pdf_candidates"]]
        self.assertEqual(urls[0], ("https://journals.aps.org/prl/pdf/" + DOI, "publisher"))
        self.assertIn(("https://link.aps.org/pdf/" + DOI, "publisher"), urls)
        self.assertIn(("https://hal.example/x.pdf", "repository"), urls)
        self.assertEqual(urls[-1], ("https://arxiv.org/pdf/1303.0001", "arxiv"))
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(e["supplement_pages"], ["https://journals.aps.org/prl/supplemental/" + DOI])
        self.assertEqual(fp.check_manifest({"papers": [e]}, {DOI.lower(): ["S02"]}), [])

    def test_no_doi_and_generation_rules(self):
        h = copy.deepcopy(self.HIT)
        h["metadata"].pop("dois")
        e = fp.build_entry(h, None, {})
        self.assertEqual((e["key"], e["doi"], e["publisher"], e["pdf_candidates"][0]["kind"]), ("inspire-42", None, "unknown", "arxiv"))
        self.assertEqual(fp.generation_of("2002", "AMS on the International Space Station: test flight"), "ams-01-or-earlier")
        self.assertEqual(fp.generation_of("2011-06", "Results from AMS-01"), "ams-01-or-earlier")
        self.assertEqual(fp.generation_of("2005", "Hardware", "10.1109/TNS.2005.862781"), "ams-02")
        self.assertEqual(fp.generation_of("2010", "Test beam of AMS-02 ECAL"), "ams-02")


class ClassifyTests(unittest.TestCase):
    def test_outcomes(self):
        mb = 1 << 20
        self.assertEqual(fp.classify(ok(), mb)[0], "ok")
        for code in (401, 403, 429):
            self.assertEqual(fp.classify(fp.Response(code, "", b"", ""), mb)[0], "blocked")
        self.assertEqual(fp.classify(fp.Response(404, "", b"", ""), mb)[0], "http-error")
        self.assertEqual(fp.classify(fp.Response(0, "", b"", ""), mb)[0], "http-error")
        for page in (b"<html>Just a moment...</html>", b"<title>Making sure you're not a bot!</title>",
                     b"<h1>Human Verification</h1>"):
            self.assertEqual(fp.classify(fp.Response(200, "text/html", page, ""), mb)[0], "blocked")
        self.assertEqual(fp.classify(fp.Response(200, "text/html", b"<html>landing page</html>", ""), mb)[0], "not-a-pdf")
        self.assertEqual(fp.classify(fp.Response(200, "application/pdf", PDF + b"y" * mb, ""), mb)[0], "too-large")


class FetchTests(unittest.TestCase):
    def test_fetch_labels_version_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            url = "https://journals.aps.org/prl/pdf/" + DOI
            f, cache = fetcher({url: ok(url=url)}, d)
            self.assertEqual(f.fetch_article(entry()), "fetched (publisher)")
            cache.save()
            meta = fp.Cache(Path(d) / "cache").article(KEY)
            self.assertEqual((meta["version"], meta["bytes"], meta["url"]), ("publisher", len(PDF), url))
            self.assertEqual(len(meta["sha256"]), 64)
            before = len(f.http.calls)
            self.assertEqual(f.fetch_article(entry()), "cached")
            self.assertEqual(len(f.http.calls), before)

    def test_blocked_candidate_falls_through_but_is_not_bypassed(self):
        with tempfile.TemporaryDirectory() as d:
            c1, c2 = "https://a.example/x.pdf", "https://arxiv.org/pdf/1303.0001"
            f, cache = fetcher({c1: fp.Response(401, "", b"", c1), c2: ok(url=c2)}, d)
            e = entry([{"url": c1, "kind": "publisher"}, {"url": c2, "kind": "arxiv"}])
            self.assertEqual(f.fetch_article(e), "fetched (arxiv)")
            self.assertEqual(f.http.calls, [c1, c2])
            self.assertNotIn(KEY, cache.index["blocked"])

    def test_all_blocked_is_recorded_and_not_retried_within_a_run(self):
        with tempfile.TemporaryDirectory() as d:
            c1 = "https://a.example/x.pdf"
            wall = fp.Response(200, "text/html", b"<html>Just a moment...</html>", c1)
            f, cache = fetcher({c1: wall}, d)
            self.assertEqual(f.fetch_article(entry([{"url": c1, "kind": "publisher"}])), "blocked")
            self.assertEqual(f.http.calls, [c1])
            self.assertIn("bot-verification", cache.index["blocked"][KEY]["reason"])
            self.assertIsNone(cache.article(KEY))

    def test_failed_and_no_candidate_and_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            f, _ = fetcher({}, d)
            self.assertEqual(f.fetch_article(entry()), "failed")
            self.assertEqual(f.fetch_article(entry(candidates=[])), "no-candidate")
            n = len(f.http.calls)
            self.assertEqual(f.fetch_article(entry(), dry_run=True), "would-fetch")
            self.assertEqual(len(f.http.calls), n)

    def test_size_cap(self):
        with tempfile.TemporaryDirectory() as d:
            url = "https://a.example/big.pdf"
            f, cache = fetcher({url: ok(PDF + b"z" * (2 << 20), url)}, d, max_mb=1)
            self.assertEqual(f.fetch_article(entry([{"url": url, "kind": "publisher"}])), "failed")
            self.assertIsNone(cache.article(KEY))

    def test_polite_delay_between_requests(self):
        with tempfile.TemporaryDirectory() as d:
            sleeps = []
            cache = fp.Cache(Path(d) / "cache")
            f = fp.Fetcher(cache, http=FakeHttp({}), delay=5.0, sleep=sleeps.append, log=lambda s: None)
            f.fetch_article(entry([{"url": "https://a.example/1.pdf", "kind": "publisher"},
                                   {"url": "https://a.example/2.pdf", "kind": "publisher"}]))
            self.assertEqual(len(sleeps), 1)
            self.assertGreater(sleeps[0], 0)

    def test_http_layer_refuses_plain_http(self):
        with self.assertRaises(ValueError):
            fp.Http().get("http://example.org/x.pdf", 10)


class SeqHttp:
    """url -> list of responses, consumed in order (the last one repeats)."""

    def __init__(self, table):
        self.table, self.calls = {u: list(v) for u, v in table.items()}, []

    def get(self, url, max_bytes):
        self.calls.append(url)
        seq = self.table.get(url, [fp.Response(404, "text/html", b"not found", url)])
        return seq.pop(0) if len(seq) > 1 else seq[0]


class RetryTests(unittest.TestCase):
    URL = "https://arxiv.org/pdf/hep-ex/0406065"

    def make(self, seq, tmp, **kw):
        sleeps = []
        cache = fp.Cache(Path(tmp) / "cache")
        f = fp.Fetcher(cache, http=SeqHttp({self.URL: seq}), delay=0, sleep=sleeps.append, log=lambda s: None, **kw)
        return f, cache, sleeps

    def cand(self):
        return entry([{"url": self.URL, "kind": "arxiv"}])

    def test_transient_error_is_retried_once_after_the_wait(self):
        for code in (406, 500, 502, 503, 504, 0):
            with tempfile.TemporaryDirectory() as d:
                f, cache, sleeps = self.make([fp.Response(code, "", b"", self.URL), ok(url=self.URL)], d, retry_wait=7.5)
                self.assertEqual(f.fetch_article(self.cand()), "fetched (arxiv)", code)
                self.assertEqual(f.http.calls, [self.URL, self.URL], code)
                self.assertEqual(sleeps, [7.5], code)

    def test_gives_up_after_the_configured_retries(self):
        with tempfile.TemporaryDirectory() as d:
            f, cache, sleeps = self.make([fp.Response(503, "", b"", self.URL)], d, retries=2, retry_wait=1)
            self.assertEqual(f.fetch_article(self.cand()), "failed")
            self.assertEqual(len(f.http.calls), 3)  # first try plus two retries
            self.assertEqual(sleeps, [1, 1])
            self.assertIsNone(cache.article(KEY))

    def test_blocks_and_not_found_are_never_retried(self):
        for code in (401, 403, 429, 404, 410):
            with tempfile.TemporaryDirectory() as d:
                f, _, sleeps = self.make([fp.Response(code, "", b"", self.URL), ok(url=self.URL)], d)
                self.assertNotEqual(f.fetch_article(self.cand()), "fetched (arxiv)", code)
                self.assertEqual(len(f.http.calls), 1, code)
                self.assertEqual(sleeps, [], code)

    def test_bot_verification_page_is_not_retried(self):
        with tempfile.TemporaryDirectory() as d:
            wall = fp.Response(200, "text/html", b"<html>Just a moment...</html>", self.URL)
            f, cache, sleeps = self.make([wall, ok(url=self.URL)], d)
            self.assertEqual(f.fetch_article(self.cand()), "blocked")
            self.assertEqual((len(f.http.calls), sleeps), (1, []))

    def test_retries_zero_disables_it(self):
        with tempfile.TemporaryDirectory() as d:
            f, _, sleeps = self.make([fp.Response(503, "", b"", self.URL), ok(url=self.URL)], d, retries=0)
            self.assertEqual(f.fetch_article(self.cand()), "failed")
            self.assertEqual((len(f.http.calls), sleeps), (1, []))
            f2 = fp.Fetcher(fp.Cache(Path(d) / "c2"), http=SeqHttp({}), retries=-3)
            self.assertEqual(f2.retries, 0)

    def test_supplement_requests_are_retried_too(self):
        with tempfile.TemporaryDirectory() as d:
            page = "https://journals.aps.org/prl/supplemental/" + DOI
            link = ('<a href="/prl/supplemental/%s/SM-a.pdf">a</a>' % DOI).encode()
            table = {page: [fp.Response(503, "", b"", page), fp.Response(200, "text/html", link, page)],
                     page + "/SM-a.pdf": [ok(url=page + "/SM-a.pdf")]}
            sleeps = []
            f = fp.Fetcher(fp.Cache(Path(d) / "cache"), http=SeqHttp(table), delay=0, sleep=sleeps.append,
                           log=lambda s: None, retry_wait=2)
            self.assertEqual(f.fetch_supplements(entry(supp=[page])), ["fetched SM-a.pdf"])
            self.assertEqual(sleeps, [2])

    def test_dry_run_makes_no_request_and_no_retry(self):
        with tempfile.TemporaryDirectory() as d:
            f, _, sleeps = self.make([fp.Response(503, "", b"", self.URL)], d)
            self.assertEqual(f.fetch_article(self.cand(), dry_run=True), "would-fetch")
            self.assertEqual((f.http.calls, sleeps), ([], []))

    def test_cli_options(self):
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "m.json"
            m.write_text(json.dumps({"papers": [entry([{"url": self.URL, "kind": "arxiv"}])]}), encoding="utf-8")
            base = ["--manifest", str(m), "--cache", str(Path(d) / "cache"), "fetch", "--all", "--delay", "0",
                    "--retry-wait", "0"]
            http = SeqHttp({self.URL: [fp.Response(406, "", b"", self.URL), ok(url=self.URL)]})
            code, out = run_cli(base, http=http)
            self.assertEqual((code, len(http.calls)), (0, 2))
            self.assertEqual(json.loads(out)["results"][0]["article"], "fetched (arxiv)")
            m.write_text(json.dumps({"papers": [entry([{"url": self.URL, "kind": "arxiv"}], key="K2", doi="10.1/x")]}),
                         encoding="utf-8")
            http = SeqHttp({self.URL: [fp.Response(406, "", b"", self.URL), ok(url=self.URL)]})
            code, _ = run_cli(base + ["--retries", "0"], http=http)
            self.assertEqual((code, len(http.calls)), (1, 1))


class SupplementTests(unittest.TestCase):
    PAGE = ('<a href="/prl/supplemental/%s/SM-a.pdf">a</a> <a href="/prl/supplemental/%s/SM-a.pdf">dup</a> '
            '<a href="/prl/supplemental/%s/tables.zip">z</a> <a href="/prl/supplemental/%s/../../evil.pdf">e</a> '
            '<a href="/other/page.pdf">no</a>') % ((DOI,) * 4)

    def test_discovery_and_download(self):
        with tempfile.TemporaryDirectory() as d:
            page = "https://journals.aps.org/prl/supplemental/" + DOI
            base = "https://journals.aps.org/prl/supplemental/%s/" % DOI
            table = {page: fp.Response(200, "text/html", self.PAGE.encode(), page),
                     base + "SM-a.pdf": ok(url=base + "SM-a.pdf"),
                     base + "tables.zip": fp.Response(200, "application/zip", b"PK\x03\x04zz", "")}
            f, cache = fetcher(table, d)
            out = f.fetch_supplements(entry(supp=[page]))
            self.assertIn("fetched SM-a.pdf", out)
            self.assertIn("fetched tables.zip", out)
            self.assertFalse(any("evil" in u for u in f.http.calls))  # links leaving /prl/supplemental/ are ignored
            self.assertTrue(cache.has(f"supp/{KEY}/SM-a.pdf"))
            self.assertTrue(all(".." not in r for r in cache.index["files"]))
            n = len(f.http.calls)
            self.assertIn("cached SM-a.pdf", f.fetch_supplements(entry(supp=[page])))
            self.assertEqual(len(f.http.calls), n + 1)  # only the page is fetched again

    def test_supplement_page_blocked_gives_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            page = "https://journals.aps.org/prl/supplemental/" + DOI
            f, _ = fetcher({page: fp.Response(403, "", b"", page)}, d)
            self.assertEqual(f.fetch_supplements(entry(supp=[page])), [])

    def test_supplement_that_is_not_a_pdf_or_is_blocked_is_not_stored(self):
        with tempfile.TemporaryDirectory() as d:
            page = "https://journals.aps.org/prl/supplemental/" + DOI
            link = '<a href="/prl/supplemental/%s/SM-a.pdf">a</a><a href="/prl/supplemental/%s/SM-b.pdf">b</a>' % (DOI, DOI)
            table = {page: fp.Response(200, "text/html", link.encode(), page),
                     page + "/SM-a.pdf": fp.Response(200, "text/html", b"<html>Just a moment</html>", ""),
                     page + "/SM-b.pdf": fp.Response(429, "", b"", "")}
            f, cache = fetcher(table, d)
            self.assertEqual(f.fetch_supplements(entry(supp=[page])),
                             ["SM-a.pdf: not a PDF", "SM-b.pdf: blocked or error HTTP 429"])
            self.assertEqual(cache.index["files"], {})

    def test_size_cap_and_file_limit(self):
        with tempfile.TemporaryDirectory() as d:
            page = "https://journals.aps.org/prl/supplemental/" + DOI
            names = [f"SM-{i:02d}.pdf" for i in range(fp.MAX_SUPP_FILES + 5)]
            html = "".join('<a href="/prl/supplemental/%s/%s">x</a>' % (DOI, n) for n in names)
            table = {page: fp.Response(200, "text/html", html.encode(), page)}
            for n in names:
                table[page + "/" + n] = ok(PDF + b"z" * (2 << 20) if n == "SM-00.pdf" else PDF)
            f, cache = fetcher(table, d, max_mb=1)
            out = f.fetch_supplements(entry(supp=[page]))
            self.assertEqual(len(out), fp.MAX_SUPP_FILES)
            self.assertIn("SM-00.pdf: too large", out)
            self.assertFalse(cache.has(f"supp/{KEY}/SM-00.pdf"))

    def test_dry_run_lists_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            f, _ = fetcher({}, d)
            out = f.fetch_supplements(entry(supp=["https://journals.aps.org/prl/supplemental/" + DOI]), dry_run=True)
            self.assertEqual(out, ["would-list https://journals.aps.org/prl/supplemental/" + DOI])
            self.assertEqual(f.http.calls, [])


class SafeNameAndCacheTests(unittest.TestCase):
    def test_safe_name(self):
        self.assertEqual(fp.safe_name("../../etc/passwd"), "passwd")
        self.assertEqual(fp.safe_name("a b%20c.pdf"), "a_b_c.pdf")
        self.assertEqual(fp.safe_name(".hidden"), "hidden")
        self.assertEqual(fp.safe_name(""), "file")

    def test_cache_refuses_escape(self):
        with tempfile.TemporaryDirectory() as d:
            c = fp.Cache(Path(d) / "cache")
            with self.assertRaises(ValueError):
                c.put("../outside.pdf", PDF, kind="article")

    def test_default_cache_from_environment(self):
        import os
        old = os.environ.get("AMS_PAPERS_CACHE")
        try:
            os.environ["AMS_PAPERS_CACHE"] = "/tmp/somewhere"
            self.assertEqual(fp.default_cache(), Path("/tmp/somewhere"))
            del os.environ["AMS_PAPERS_CACHE"]
            self.assertTrue(str(fp.default_cache()).endswith(".cache/ams-analysis/papers"))
        finally:
            if old is not None:
                os.environ["AMS_PAPERS_CACHE"] = old


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.manifest = self.d / "m.json"
        self.manifest.write_text(json.dumps({"papers": [entry()]}), encoding="utf-8")
        self.base = ["--manifest", str(self.manifest), "--cache", str(self.d / "cache")]

    def tearDown(self):
        self.tmp.cleanup()

    def test_help_exits_zero(self):
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(io.StringIO()):
            fp.main(["--help"])
        self.assertEqual(cm.exception.code, 0)

    def test_check_manifest_shipped(self):
        code, out = run_cli(["check-manifest"])
        self.assertEqual((code, json.loads(out)["status"]), (0, "pass"))

    def test_supplements_are_opt_in_and_reported(self):
        page = "https://journals.aps.org/prl/supplemental/" + DOI
        pdf_url = "https://journals.aps.org/prl/pdf/" + DOI
        self.manifest.write_text(json.dumps({"papers": [entry(supp=[page])]}), encoding="utf-8")
        link = '<a href="/prl/supplemental/%s/SM-a.pdf">a</a>' % DOI
        table = {pdf_url: ok(url=pdf_url), page: fp.Response(200, "text/html", link.encode(), page),
                 page + "/SM-a.pdf": ok(url=page + "/SM-a.pdf")}
        http = FakeHttp(table)
        code, out = run_cli(self.base + ["fetch", "--keys", "PhysRevLett.110.141102", "--delay", "0"], http=http)
        self.assertEqual(code, 0)
        self.assertNotIn("supplements", json.loads(out)["results"][0])
        self.assertNotIn(page, http.calls)  # off by default: no supplement request at all
        code, out = run_cli(self.base + ["fetch", "--keys", "PhysRevLett.110.141102", "--supplements", "--delay", "0"],
                            http=http)
        self.assertEqual(json.loads(out)["results"][0]["supplements"], ["fetched SM-a.pdf"])
        code, out = run_cli(self.base + ["status"])
        self.assertEqual(json.loads(out)["papers"][0]["supplements"], 1)
        code, out = run_cli(self.base + ["fetch", "--all", "--supplements", "--dry-run"], http=FakeHttp({}))
        self.assertEqual(json.loads(out)["results"][0]["supplements"], ["would-list " + page])

    def test_fetch_requires_selection_and_known_key(self):
        self.assertEqual(run_cli(self.base + ["fetch"])[0], 2)
        self.assertEqual(run_cli(self.base + ["fetch", "--keys", "nope"])[0], 2)

    def test_fetch_exit_codes_and_status(self):
        url = "https://journals.aps.org/prl/pdf/" + DOI
        code, out = run_cli(self.base + ["fetch", "--keys", "PhysRevLett.110.141102", "--delay", "0"],
                            http=FakeHttp({url: ok(url=url)}))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["results"][0]["article"], "fetched (publisher)")
        code, out = run_cli(self.base + ["status"])
        self.assertEqual(json.loads(out)["counts"], {"cached": 1})
        self.assertEqual(run_cli(self.base + ["verify"])[0], 0)
        (self.d / "cache" / "pdf" / f"{KEY}.pdf").write_bytes(PDF + b"tampered")
        code, out = run_cli(self.base + ["verify"])
        self.assertEqual(code, 1)
        self.assertIn("hash differs", out)

    def test_fetch_blocked_exit_one_with_hint(self):
        url = "https://journals.aps.org/prl/pdf/" + DOI
        code, out = run_cli(self.base + ["fetch", "--all", "--delay", "0"],
                            http=FakeHttp({url: fp.Response(401, "", b"", url)}))
        self.assertEqual(code, 1)
        j = json.loads(out)
        self.assertEqual(j["not_fetched"], 1)
        self.assertIn("adopt", j["hint"])
        code, out = run_cli(self.base + ["status"])
        self.assertEqual(json.loads(out)["counts"], {"blocked": 1})

    def test_adopt_matches_by_file_name(self):
        dl = self.d / "dl"
        dl.mkdir()
        (dl / "PhysRevLett.110.141102.pdf").write_bytes(PDF)
        (dl / "PhysRevLett.110.141102 (1).pdf").write_bytes(PDF + b"dup")
        (dl / "PhysRevLett.81.1562.pdf").write_bytes(PDF)
        (dl / "notes.pdf").write_bytes(b"<html>")
        code, out = run_cli(self.base + ["adopt", str(dl)])
        j = json.loads(out)
        self.assertEqual(j["adopted"], [KEY])
        self.assertTrue(any("already cached" in s for s in j["skipped"]))
        self.assertTrue(any("PhysRevLett.81.1562" in s and "no manifest entry" in s for s in j["skipped"]))
        self.assertTrue(any("notes.pdf" in s for s in j["skipped"]))
        meta = fp.Cache(self.d / "cache").article(KEY)
        self.assertEqual(meta["version"], "publisher")
        self.assertTrue(meta["url"].startswith("adopted:"))

    def test_adopt_rejects_non_pdf(self):
        f = self.d / "PhysRevLett.110.141102.pdf"
        f.write_bytes(b"<html>Just a moment</html>")
        code, out = run_cli(self.base + ["adopt", str(f)])
        self.assertEqual(code, 1)
        self.assertIn("not a PDF", out)

    def test_refresh_manifest_with_fake_services(self):
        hit = copy.deepcopy(BuildEntryTests.HIT)
        inspire = json.dumps({"hits": {"total": 1, "hits": [hit]}}).encode()
        oa = json.dumps(BuildEntryTests.OA).encode()
        calls = {}

        class H:
            def get(self, url, max_bytes):
                calls[url] = True
                if "inspirehep.net" in url:
                    return fp.Response(200, "application/json", inspire, url)
                return fp.Response(200, "application/json", oa, url)

        sources = self.d / "s.json"
        sources.write_text(json.dumps([{"id": "S02", "dois": [DOI]}]), encoding="utf-8")
        out_path = self.d / "new.json"
        code, out = run_cli(["--manifest", str(out_path), "--sources", str(sources), "refresh-manifest", "--delay", "0"],
                            http=H())
        self.assertEqual(code, 0, out)
        new = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(new["papers"][0]["source_ids"], ["S02"])
        self.assertIn("No PDFs are stored", new["note"])

    def test_refresh_manifest_inspire_failure_is_exit_two(self):
        class H:
            def get(self, url, max_bytes):
                return fp.Response(503, "", b"", url)

        code, out = run_cli(["--manifest", str(self.d / "n.json"), "refresh-manifest"], http=H())
        self.assertEqual(code, 2)
        self.assertFalse((self.d / "n.json").exists())

    def test_unreadable_manifest_is_exit_two(self):
        code, _ = run_cli(["--manifest", str(self.d / "missing.json"), "--cache", str(self.d / "c"), "status"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
