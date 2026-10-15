"""adapters/crdb: CRDB (LPSC) REST query, offline.

No network: `urllib.request.urlopen` is patched to fail in every test, and the HTTP layer is replaced by a fake
that serves either the CRDB exports recorded live on 2026-10-15 (tests/adapters/fixtures/crdb/, with the sidecars
the adapter wrote and recording.json) or synthetic responses for the request rules (blocks, retries, size cap).
Covers: no default experiment filter (exit 2), every output row and group labelled secondary, the sidecar
(request, UTC retrieval time, CRDB version, export date, SHA-256 of the saved file), replay of the recorded exports
byte for byte, parsing and summarizing real exports (two sub-experiments, an empty export), URL building against the
URLs that worked live, and the layering rule (no experiment name in the adapter's code or declaration).
Run from the plugin root: python -m unittest tests.adapters.test_crdb_query -v
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import re
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[2]
ADAPTER = PLUGIN / "adapters" / "crdb"
SCRIPT = ADAPTER / "assets" / "crdb_query.py"
FIX = PLUGIN / "tests" / "adapters" / "fixtures" / "crdb"
RECORDED = ("ratio_ekn_filtered.csv", "flux_r_filtered.csv", "positron_ek_filtered.csv", "no_match.csv")

_spec = importlib.util.spec_from_file_location("crdb_query_adapter", SCRIPT)
cq = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cq  # dataclasses look the module up by name
_spec.loader.exec_module(cq)

sys.path.insert(0, str(PLUGIN))
from tools.check_layering import EXPERIMENT_NAMES  # noqa: E402


def no_network(*a, **k):
    raise AssertionError("network access in an offline test")


class Offline(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(urllib.request, "urlopen", no_network)
        p.start()
        self.addCleanup(p.stop)
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.tmp = Path(self.td.name)


def meta(name):
    return json.loads((FIX / (name + ".meta.json")).read_text(encoding="utf-8"))


class FakeHttp:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, max_bytes):
        self.calls.append(url)
        r = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        return cq.Response(r.status, r.content_type, r.data[: max_bytes + 1], r.url or url)


def resp(status=200, data=None, ctype="application/json", url=""):
    return cq.Response(status, ctype, (FIX / "flux_r_filtered.csv").read_bytes() if data is None else data, url)


def run(argv, http=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cq.main(argv, http=http)
        except SystemExit as e:  # argparse errors
            code = e.code
    return code, out.getvalue(), err.getvalue()


def argv_from_params(p):
    """CLI arguments that rebuild a recorded request."""
    a = ["--num", p["num"], "--energy-type", p["energy_type"], "--den", p["den"]]
    a += ["--exp-dates", p["exp_dates"]] if "exp_dates" in p else ["--all-experiments"]
    for k in ("energy_start", "energy_stop"):
        if k in p:
            a += ["--" + k.replace("_", "-"), p[k]]
    return a


class NoDefaultExperimentTests(Offline):
    BASE = ["--num", "H", "--energy-type", "R"]

    def test_cli_without_experiment_filter_exits_2(self):
        for cmd in ("url", "fetch"):
            with self.subTest(cmd=cmd):
                extra = ["--out", str(self.tmp / "x.csv")] if cmd == "fetch" else []
                http = FakeHttp(resp())
                code, _, err = run([cmd] + self.BASE + extra, http=http)
                self.assertEqual(code, 2)
                self.assertIn("--exp-dates", err)
                self.assertEqual(http.calls, [])

    def test_empty_filter_and_both_flags_exit_2(self):
        self.assertEqual(run(["url"] + self.BASE + ["--exp-dates", " "])[0], 2)
        self.assertEqual(run(["url"] + self.BASE + ["--exp-dates", "X", "--all-experiments"])[0], 2)

    def test_python_api_has_no_default(self):
        with self.assertRaises(TypeError):
            cq.build_params("H", "R")
        with self.assertRaises(cq.UsageError):
            cq.build_params("H", "R", "")
        self.assertNotIn("exp_dates", cq.build_params("H", "R", None))

    def test_all_experiments_is_explicit(self):
        code, out, _ = run(["url"] + self.BASE + ["--all-experiments"])
        self.assertEqual(code, 0)
        self.assertNotIn("exp_dates", out)

    def test_source_declares_no_default_filter(self):
        src = SCRIPT.read_text(encoding="utf-8")
        for line in src.splitlines():
            if "exp_dates" in line or "exp-dates" in line:
                self.assertNotRegex(line, r"default\s*=\s*['\"][^'\"]+['\"]", line)
                self.assertIsNone(re.search(r"exp_dates\s*(:\s*[^=,)]+)?=\s*['\"]", line), line)


class LayeringTests(unittest.TestCase):
    def test_no_experiment_name_in_adapter_code_or_declaration(self):
        example = re.compile(r"#\s*example-begin.*?#\s*example-end", re.S)
        for f in sorted(ADAPTER.rglob("*")):
            if f.suffix in (".py", ".json", ".md"):
                with self.subTest(file=f.name):
                    text = example.sub("", f.read_text(encoding="utf-8"))
                    self.assertIsNone(re.search(EXPERIMENT_NAMES, text), f"experiment name in {f}")
                    self.assertIsNone(re.search(r"\b(experiment|theory):[a-z0-9][a-z0-9-]*\b", text))


class RecordedFixtureTests(Offline):
    def test_recording_is_documented_and_hashes_match(self):
        rec = json.loads((FIX / "recording.json").read_text(encoding="utf-8"))
        self.assertIn("V4.2", rec["crdb_version"])
        self.assertEqual({r.get("file") for r in rec["requests"]} - {None}, set(RECORDED))
        for name in RECORDED:
            with self.subTest(name=name):
                m = meta(name)
                data = (FIX / name).read_bytes()
                self.assertEqual(m["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(m["bytes"], len(data))
                self.assertEqual(m["source_role"], "secondary")
                self.assertRegex(m["retrieved_utc"], r"^2026-10-15T\d\d:\d\d:\d\dZ$")
                self.assertTrue(m["crdb_version"].startswith("V4.2"))
                self.assertTrue(m["final_url"].startswith("https://lpsc.in2p3.fr/crdb/"))
                parsed = cq.parse_export(data.decode("utf-8"))
                self.assertEqual(parsed["export_date"], m["crdb_export_date"])
                self.assertEqual(len(parsed["rows"]), m["n_rows"])

    def test_url_building_reproduces_the_urls_that_worked_live(self):
        for name in RECORDED:
            with self.subTest(name=name):
                m = meta(name)
                p = m["request"]["params"]
                rebuilt = cq.build_params(p["num"], p["energy_type"], p.get("exp_dates"), den=p["den"],
                                          energy_start=p.get("energy_start"), energy_stop=p.get("energy_stop"))
                self.assertEqual(rebuilt, p)
                self.assertEqual(cq.build_url(rebuilt), m["request"]["url"])
        self.assertIn("num=e%2B", meta("positron_ek_filtered.csv")["request"]["url"])

    def test_replay_writes_the_same_bytes_and_a_complete_sidecar(self):
        for name in ("ratio_ekn_filtered.csv", "flux_r_filtered.csv", "positron_ek_filtered.csv"):
            with self.subTest(name=name):
                m = meta(name)
                data = (FIX / name).read_bytes()
                http = FakeHttp(cq.Response(200, "application/json", data, m["final_url"]))
                out = self.tmp / name
                code, text, _ = run(["fetch"] + argv_from_params(m["request"]["params"])
                                    + ["--out", str(out), "--crdb-version", m["crdb_version"]], http=http)
                self.assertEqual(code, 0, text)
                self.assertEqual(http.calls, [m["request"]["url"]])
                self.assertEqual(out.read_bytes(), data)
                side = json.loads(out.with_name(name + ".meta.json").read_text())
                for k in ("request", "retrieved_utc", "crdb_version", "crdb_export_date", "sha256"):
                    self.assertIn(k, side)
                self.assertEqual(side["request"]["params"], m["request"]["params"])
                self.assertEqual(side["sha256"], hashlib.sha256(out.read_bytes()).hexdigest())
                self.assertEqual(side["crdb_export_date"], m["crdb_export_date"])
                self.assertEqual(side["crdb_version"], m["crdb_version"])
                self.assertEqual(side["final_url"], m["final_url"])
                self.assertEqual(json.loads(text)["label"], cq.LABEL)

    def test_every_summarized_row_and_group_is_secondary(self):
        for name in ("ratio_ekn_filtered.csv", "flux_r_filtered.csv", "positron_ek_filtered.csv"):
            with self.subTest(name=name):
                code, text, _ = run(["summarize", str(FIX / name), "--rows"])
                self.assertEqual(code, 0)
                s = json.loads(text)
                self.assertEqual(s["source_role"], "secondary")
                self.assertIn("HEPData", s["primary_sources"])
                self.assertTrue(s["rows"])
                self.assertTrue(all(r["secondary"] is True for r in s["rows"]))
                self.assertTrue(all(g["secondary"] is True for g in s["sub_experiments"]))
                self.assertTrue(s["sha256_matches_sidecar"])
                self.assertEqual(s["sidecar"]["sha256"], meta(name)["sha256"])

    def test_real_export_keeps_sub_experiments_apart(self):
        parsed = cq.parse_export((FIX / "flux_r_filtered.csv").read_text(encoding="utf-8"))
        s = cq.summarize(parsed)
        self.assertEqual(len(s["sub_experiments"]), 2)
        self.assertEqual(sorted(g["n_rows"] for g in s["sub_experiments"]), [3, 3])
        self.assertEqual(len({g["data_taking_dates"] for g in s["sub_experiments"]}), 2)
        self.assertEqual(len(parsed["columns"]), 24)
        self.assertTrue(all(float(r["DATA-E_BIN_L"]) >= 0 for r in parsed["rows"]))

    def test_filter_can_match_more_than_one_experiment(self):
        # recorded behaviour: the short filter returned rows of two experiments; the summary keeps them apart
        parsed = cq.parse_export((FIX / "ratio_ekn_filtered.csv").read_text(encoding="utf-8"))
        self.assertEqual(len({r["EXP-NAME"] for r in parsed["rows"]}), 2)
        self.assertEqual(len(cq.summarize(parsed)["sub_experiments"]), 2)

    def test_empty_export_exits_1(self):
        data = (FIX / "no_match.csv").read_bytes()
        self.assertEqual(cq.parse_export(data.decode())["rows"], [])
        m = meta("no_match.csv")
        out = self.tmp / "e.csv"
        code, text, _ = run(["fetch"] + argv_from_params(m["request"]["params"]) + ["--out", str(out)],
                            http=FakeHttp(cq.Response(200, "application/json", data, m["final_url"])))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(text)["status"], "no-data-rows")
        self.assertEqual(run(["summarize", str(FIX / "no_match.csv")])[0], 1)


class FetchRuleTests(Offline):
    def fetcher(self, *responses, **kw):
        self.http = FakeHttp(*responses)
        self.sleeps = []
        return cq.Fetcher(http=self.http, sleep=self.sleeps.append, clock=lambda: "T", **kw)

    def test_content_type_is_not_trusted(self):
        # the live endpoint labels its csv export application/json; the header text decides
        self.assertEqual(self.fetcher(resp(ctype="application/json")).fetch("https://x")[0], "ok")
        self.assertEqual(self.fetcher(resp(data=b"<html>hi</html>", ctype="text/csv")).fetch("https://x")[0], "not-an-export")

    def test_blocks_are_never_retried(self):
        for status in (401, 403, 429):
            with self.subTest(status=status):
                outcome, detail, _ = self.fetcher(resp(status, b"")).fetch("https://x")
                self.assertEqual(outcome, "blocked")
                self.assertEqual(len(self.http.calls), 1)
                self.assertEqual(self.sleeps, [])
                self.assertIn("not bypassed", detail)

    def test_transient_error_is_retried_once(self):
        outcome, _, _ = self.fetcher(resp(503, b""), resp()).fetch("https://x")
        self.assertEqual((outcome, len(self.http.calls), self.sleeps), ("ok", 2, [10.0]))
        outcome, _, _ = self.fetcher(resp(0, b"")).fetch("https://x")
        self.assertEqual((outcome, len(self.http.calls)), ("http-error", 2))
        outcome, _, _ = self.fetcher(resp(503, b""), resp(429, b"")).fetch("https://x")
        self.assertEqual(outcome, "blocked")

    def test_client_error_is_not_retried(self):
        outcome, _, _ = self.fetcher(resp(404, b"")).fetch("https://x")
        self.assertEqual((outcome, len(self.http.calls)), ("http-error", 1))

    def test_size_cap(self):
        big = resp().data + b"#" * (2 * (1 << 20))
        self.assertEqual(self.fetcher(resp(data=big), max_mb=1).fetch("https://x")[0], "too-large")

    def test_plain_http_is_refused(self):
        with self.assertRaises(cq.UsageError):
            cq.Http().get("http://lpsc.in2p3.fr/crdb/rest.php", 10)

    def test_refusal_writes_nothing_and_exits_1(self):
        out = self.tmp / "p.csv"
        code, text, _ = run(["fetch", "--num", "H", "--energy-type", "R", "--exp-dates", "X", "--out", str(out)],
                            http=FakeHttp(resp(429, b"")))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(text)["status"], "blocked")
        self.assertFalse(out.exists())

    def test_no_overwrite_without_flag_and_version_only_when_given(self):
        out = self.tmp / "p.csv"
        out.write_text("keep")
        http = FakeHttp(resp())
        args = ["fetch", "--num", "H", "--energy-type", "R", "--exp-dates", "X", "--out", str(out)]
        self.assertEqual(run(args, http=http)[0], 2)
        self.assertEqual((out.read_text(), http.calls), ("keep", []))
        self.assertEqual(run(args + ["--overwrite"], http=http)[0], 0)
        side = json.loads(out.with_name("p.csv.meta.json").read_text())
        self.assertIsNone(side["crdb_version"])
        self.assertIn("not recorded", side["crdb_version_note"])


class ParamTests(unittest.TestCase):
    def test_cross_check_defaults(self):
        p = cq.build_params("H", "R", "X")
        self.assertEqual(p, {"num": "H", "den": "", "energy_type": "R", "exp_dates": "X",
                             "combo_level": "0", "energy_convert_level": "0"})
        self.assertNotIn("time_series", p)

    def test_bad_values_are_rejected(self):
        bad = [dict(num=" "), dict(energy_type="GeV"), dict(combo_level=3), dict(energy_convert_level=-1),
               dict(time_series="yes"), dict(fmt="json"), dict(modulation="X"), dict(time_start="2011-05"),
               dict(time_stop="11"), dict(energy_start="abc"), dict(flux_rescaling="x")]
        for kw in bad:
            args = dict(num="H", energy_type="R", exp_dates="X")
            args.update(kw)
            with self.subTest(kw=kw), self.assertRaises(cq.UsageError):
                cq.build_params(**args)

    def test_summarize_unreadable_file_exits_2(self):
        self.assertEqual(run(["summarize", "/nonexistent/x.csv"])[0], 2)


if __name__ == "__main__":
    unittest.main()
