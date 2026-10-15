"""adapters/literature-lookup: identifier -> metadata record from INSPIRE-HEP, arXiv and ADS (WP5).

Offline tests replay responses in tests/adapters/fixtures/literature_lookup/ and never open a connection (urlopen is
patched to fail):
- recorded/: real INSPIRE and arXiv responses recorded on 2026-10-15 with `literature_lookup.py --record`
  (arXiv 1007.1727, INSPIRE record 860907; a nonexistent arXiv id 2501.99999 and INSPIRE record 999999999);
- rate-limit/: a real arXiv HTTP 429 ("Rate exceeded.", recorded 2026-10-15) and a constructed INSPIRE 429;
- constructed/: an ADS search response in the documented layout (no ADS token was available to record one).
The live smoke test runs only with HEP_LIVE_LOOKUP_TEST=1 (two requests: INSPIRE and arXiv; ADS only with a token).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "adapters" / "literature-lookup" / "assets" / "literature_lookup.py"
FX = Path(__file__).resolve().parent / "fixtures" / "literature_lookup"
SPEC = importlib.util.spec_from_file_location("literature_lookup", SCRIPT)
ll = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ll)
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FAKE_CRED = "fake-ads-credential-0123456789"


def no_network(*args, **kwargs):
    raise AssertionError("offline test tried to open a network connection")


class CountingLive:
    """Stands in for the live transport: records calls, answers from a replay transport (or 401)."""

    name = "live"

    def __init__(self, replay=None, status=None):
        self.calls, self.replay, self.status = [], replay, status

    def fetch(self, url, headers, source):
        self.calls.append((url, dict(headers), source))
        if self.status:
            return {"url": url, "recorded_at": "2026-10-15T00:00:00Z", "http_status": self.status, "headers": {},
                    "body": ""}
        return self.replay.fetch(url, headers, source)


class OfflineBase(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("urllib.request.urlopen", side_effect=no_network)
        patcher.start()
        self.addCleanup(patcher.stop)
        env = mock.patch.dict(os.environ, {k: "" for k in ll.TOKEN_ENV})
        env.start()
        self.addCleanup(env.stop)
        self.recorded = ll.ReplayTransport(FX / "recorded")

    def by_source(self, rec):
        return {r["source"]: r for r in rec["results"]}


class IdentifierTests(unittest.TestCase):
    def test_kinds(self):
        cases = {"arxiv:1007.1727v1": ("arxiv", "1007.1727", "v1"), "1007.1727": ("arxiv", "1007.1727", None),
                 "arXiv:hep-ph/0511063v2": ("arxiv", "hep-ph/0511063", "v2"),
                 "doi:10.1140/epjc/s10052-011-1554-0": ("doi", "10.1140/epjc/s10052-011-1554-0", None),
                 "https://doi.org/10.1140/epjc/s10052-011-1554-0": ("doi", "10.1140/epjc/s10052-011-1554-0", None),
                 "inspire:860907": ("inspire", "860907", None),
                 "bibcode:2011EPJC...71.1554C": ("bibcode", "2011EPJC...71.1554C", None)}
        for text, want in cases.items():
            with self.subTest(text=text):
                got = ll.parse_identifier(text)
                self.assertEqual((got["kind"], got["value"], got["version"]), want)

    def test_invalid_identifiers_are_refused(self):
        for text in ("arxiv:not-an-id", "inspire:abc", "doi:11.1/x", "bibcode:short", "860907", "", "isbn:123"):
            with self.subTest(text=text), self.assertRaises(ll.InvalidIdentifier):
                ll.parse_identifier(text)


class FoundTests(OfflineBase):
    def test_arxiv_id_found_in_inspire_and_arxiv(self):
        rec = ll.lookup("arxiv:1007.1727", ["inspire", "arxiv"], self.recorded)
        self.assertEqual((rec["outcome"], rec["exit_code"]), ("pass", 0))
        r = self.by_source(rec)
        for src in ("inspire", "arxiv"):
            self.assertEqual(r[src]["status"], "found")
            self.assertEqual(r[src]["read_level"], "metadata-only")
            self.assertEqual(r[src]["transport"], "replay")
            self.assertRegex(r[src]["retrieved_at"], UTC)
            self.assertTrue(r[src]["source_url"].startswith("https://"))
            self.assertEqual(r[src]["metadata"]["title"], "Asymptotic formulae for likelihood-based tests of new physics")
            self.assertIn("10.1140/epjc/s10052-011-1554-0", r[src]["metadata"]["doi"])
        self.assertEqual(r["inspire"]["metadata"]["inspire_recid"], 860907)
        self.assertIn("Cowan:2010js", r["inspire"]["metadata"]["texkeys"])
        self.assertEqual(r["inspire"]["metadata"]["arxiv_id"], "1007.1727")
        self.assertEqual(r["inspire"]["metadata"]["author_count"], 4)
        self.assertEqual(r["arxiv"]["metadata"]["latest_version"], "v3")
        self.assertEqual(r["arxiv"]["metadata"]["journal_ref"], "Eur.Phys.J.C71:1554,2011")
        self.assertIsNone(r["arxiv"]["version_check"]["requested"])
        # the retrieval time is the recording time of the replayed response, not the replay time
        self.assertEqual(r["arxiv"]["retrieved_at"], "2026-10-15T02:32:11Z")

    def test_inspire_record_id_skips_the_erratum(self):
        rec = ll.lookup("inspire:860907", None, self.recorded)
        r = self.by_source(rec)
        self.assertEqual([x["source"] for x in rec["results"]], ["inspire"])
        self.assertEqual(r["inspire"]["status"], "found")
        self.assertEqual(r["inspire"]["metadata"]["journal_ref"], "Eur.Phys.J.C 71 1554 2011")
        self.assertEqual(rec["exit_code"], 0)


class VersionMismatchTests(OfflineBase):
    def test_older_version_requested(self):
        rec = ll.lookup("arxiv:1007.1727v1", ["inspire", "arxiv"], self.recorded)
        r = self.by_source(rec)
        self.assertEqual(r["arxiv"]["version_check"], {
            "requested": "v1", "latest": "v3", "match": False,
            "note": "cites v1; arXiv now has v3: check what changed before citing"})
        self.assertTrue(rec["version_mismatch"])
        self.assertEqual((rec["outcome"], rec["exit_code"]), ("incomplete", 3))
        self.assertTrue(any("does not record arXiv versions" in n for n in r["inspire"]["notes"]))

    def test_latest_version_requested(self):
        rec = ll.lookup("arxiv:1007.1727v3", ["arxiv"], self.recorded)
        self.assertTrue(rec["results"][0]["version_check"]["match"])
        self.assertEqual(rec["exit_code"], 0)

    def test_version_that_does_not_exist(self):
        rec = ll.lookup("arxiv:1007.1727v9", ["arxiv"], self.recorded)
        vc = rec["results"][0]["version_check"]
        self.assertFalse(vc["match"])
        self.assertIn("does not exist", vc["note"])
        self.assertEqual(rec["exit_code"], 3)


class NotFoundTests(OfflineBase):
    def test_unknown_arxiv_id_in_inspire(self):
        rec = ll.lookup("arxiv:2501.99999", ["inspire"], self.recorded)
        r = rec["results"][0]
        self.assertEqual((r["status"], r["read_level"], r["http_status"]), ("not-found", "not-verified", 200))
        self.assertEqual((rec["outcome"], rec["exit_code"]), ("fail", 1))

    def test_unknown_inspire_record_is_a_404(self):
        rec = ll.lookup("inspire:999999999", None, self.recorded)
        self.assertEqual((rec["results"][0]["status"], rec["results"][0]["http_status"]), ("not-found", 404))
        self.assertEqual(rec["exit_code"], 1)

    def test_found_in_one_source_is_enough(self):
        both = ll.ReplayTransport(FX / "recorded" / "arxiv-1007.1727.json")
        rec = ll.lookup("arxiv:1007.1727", ["inspire", "arxiv"], both)  # no INSPIRE response recorded here
        r = self.by_source(rec)
        self.assertEqual(r["inspire"]["status"], "error")
        self.assertIn("no recorded response for this URL", r["inspire"]["notes"])
        self.assertEqual(rec["exit_code"], 0)


class RateLimitTests(OfflineBase):
    def test_429_is_reported_and_not_retried(self):
        counting = CountingLive(ll.ReplayTransport(FX / "rate-limit"))
        rec = ll.lookup("arxiv:2501.99999", ["inspire", "arxiv"], counting)
        self.assertEqual(len(counting.calls), 2)  # one request per source, no retry
        r = self.by_source(rec)
        for src in ("inspire", "arxiv"):
            self.assertEqual((r[src]["status"], r[src]["read_level"], r[src]["http_status"]),
                             ("rate-limited", "not-verified", 429))
        self.assertEqual(r["inspire"]["retry_after"], "5")
        self.assertTrue(any("constructed response" in n for n in r["inspire"]["notes"]))
        self.assertFalse(any("constructed response" in n for n in r["arxiv"]["notes"]))  # the arXiv 429 is real
        self.assertEqual((rec["outcome"], rec["exit_code"]), ("incomplete", 3))


class AdsTests(OfflineBase):
    def test_without_token_no_request_and_not_verified(self):
        counting = CountingLive(self.recorded)
        rec = ll.lookup("bibcode:2011EPJC...71.1554C", None, counting)
        self.assertEqual(counting.calls, [])
        r = rec["results"][0]
        self.assertEqual((r["source"], r["status"], r["read_level"]), ("ads", "not-verified", "not-verified"))
        self.assertEqual(rec["exit_code"], 3)

    def test_token_only_in_the_header_never_in_the_output(self):
        counting = CountingLive(ll.ReplayTransport(FX / "constructed"))
        with mock.patch.dict(os.environ, {"ADS_API_TOKEN": FAKE_CRED}):
            rec = ll.lookup("arxiv:1007.1727", ["ads"], counting)
        self.assertEqual(counting.calls[0][1], {"Authorization": f"Bearer {FAKE_CRED}"})
        r = rec["results"][0]
        self.assertEqual((r["status"], r["metadata"]["bibcode"]), ("found", "2011EPJC...71.1554C"))
        self.assertTrue(any("constructed response" in n for n in r["notes"]))
        self.assertNotIn(FAKE_CRED, json.dumps(rec))

    def test_rejected_token_is_not_verified_and_not_echoed(self):
        with mock.patch.dict(os.environ, {"ADS_TOKEN": FAKE_CRED}):
            rec = ll.lookup("doi:10.1140/epjc/s10052-011-1554-0", ["ads"], CountingLive(status=401))
        self.assertEqual(rec["results"][0]["status"], "not-verified")
        self.assertNotIn(FAKE_CRED, json.dumps(rec))

    def test_record_mode_never_writes_request_headers(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"ADS_API_TOKEN": FAKE_CRED}):
            class Resp(io.BytesIO):
                status = 200
                headers = {"content-type": "application/json"}

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False
            body = json.loads((FX / "constructed" / "ads-arxiv-1007.1727.json").read_text())["body"].encode()
            with mock.patch("urllib.request.urlopen", return_value=Resp(body)) as op:
                rec = ll.lookup("arxiv:1007.1727", ["ads"], ll.LiveTransport(record_dir=Path(d)))
            self.assertEqual(op.call_args[0][0].get_header("Authorization"), f"Bearer {FAKE_CRED}")
            self.assertIn("hep-research", op.call_args[0][0].get_header("User-agent"))
            written = "".join(p.read_text() for p in Path(d).glob("*.json"))
            self.assertTrue(written)
            self.assertNotIn(FAKE_CRED, written)
            self.assertNotIn(FAKE_CRED, json.dumps(rec))
            self.assertEqual(rec["results"][0]["transport"], "live")


class EdgeTests(OfflineBase):
    def test_unsupported_source_for_kind(self):
        rec = ll.lookup("bibcode:2011EPJC...71.1554C", ["inspire", "arxiv"], self.recorded)
        self.assertEqual([r["status"] for r in rec["results"]], ["unsupported", "unsupported"])
        self.assertEqual(rec["exit_code"], 3)

    def test_network_error_is_incomplete(self):
        import urllib.error
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("unreachable")):
            rec = ll.lookup("arxiv:1007.1727", ["arxiv"], ll.LiveTransport(timeout=1))
        self.assertEqual(rec["results"][0]["status"], "error")
        self.assertRegex(rec["results"][0]["retrieved_at"], UTC)
        self.assertEqual(rec["exit_code"], 3)

    def test_main_in_process(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ll.main(["arxiv:1007.1727v1", "--source", "arxiv", "--replay", str(FX / "recorded")])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out.getvalue())["results"][0]["version_check"]["latest"], "v3")


class CliTests(unittest.TestCase):
    """Subprocess runs in replay mode (no network) and with bad input."""

    def run_cli(self, *args):
        with tempfile.TemporaryDirectory() as cwd:
            env = {k: v for k, v in os.environ.items() if k not in ll.TOKEN_ENV}
            return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True,
                                  timeout=60, cwd=cwd, env=env)

    def test_replay_json_and_text(self):
        res = self.run_cli("arxiv:1007.1727", "--source", "inspire", "--source", "arxiv",
                           "--replay", str(FX / "recorded"))
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout)["outcome"], "pass")
        res = self.run_cli("arxiv:1007.1727v1", "--source", "arxiv", "--replay", str(FX / "recorded"), "--format", "text")
        self.assertEqual(res.returncode, 3, res.stderr)
        self.assertIn("requested v1, latest v3", res.stdout)

    def test_bad_identifier_and_missing_replay_exit_2(self):
        res = self.run_cli("arxiv:nope", "--replay", str(FX / "recorded"))
        self.assertEqual(res.returncode, 2)
        self.assertEqual(json.loads(res.stdout)["outcome"], "input-error")
        res = self.run_cli("arxiv:1007.1727", "--replay", "/nonexistent/literature-lookup")
        self.assertEqual(res.returncode, 2)
        self.assertNotIn("Traceback", res.stderr)


@unittest.skipUnless(os.environ.get("HEP_LIVE_LOOKUP_TEST") == "1", "live lookup not requested (HEP_LIVE_LOOKUP_TEST=1)")
class LiveSmokeTests(unittest.TestCase):
    """One live lookup of a public identifier: two requests (INSPIRE, arXiv), plus ADS when a token is set. Setting
    HEP_LIVE_LOOKUP_TEST=1 is the approval to use the network. First run: E2, 2026-10-15 (VALIDATION LITERATURE-LOOKUP)."""

    def test_live_arxiv_v1_against_inspire_and_arxiv(self):
        sources = ["inspire", "arxiv"] + (["ads"] if ll.ads_token() else [])
        rec = ll.lookup("arxiv:1007.1727v1", sources, ll.LiveTransport(timeout=60))
        print(json.dumps({r["source"]: {k: r.get(k) for k in ("status", "http_status", "retrieved_at", "source_url")}
                          for r in rec["results"]}, indent=1), file=sys.stderr)
        r = {x["source"]: x for x in rec["results"]}
        self.assertEqual(r["inspire"]["status"], "found")
        self.assertEqual(r["inspire"]["metadata"]["inspire_recid"], 860907)
        self.assertEqual(r["arxiv"]["status"], "found")
        self.assertFalse(r["arxiv"]["version_check"]["match"])  # v1 cited, a later version exists
        for x in rec["results"]:
            self.assertRegex(x["retrieved_at"], UTC)
            self.assertEqual(x["transport"], "live")


if __name__ == "__main__":
    unittest.main()
