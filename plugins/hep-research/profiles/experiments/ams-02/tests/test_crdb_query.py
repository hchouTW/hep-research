"""Tests for scripts/crdb_query.py.

No network access: the HTTP layer is replaced by a fake. The export text is a synthetic
file in CRDB's documented layout (comment header with `# Col.N - NAME` lines, then csv
rows) with invented values, so no CRDB data is stored in the repository. Covers parameter
validation against the ranges of ledger claim C128, URL building (positron encoding,
defaults of the cross-check procedure, time series only on request), the request rules
(one retry for transient errors only, none for 401/403/429, size cap, non-export
responses), export parsing and summarizing, the sidecar provenance record, and exit codes.
Run from the skill directory with `python3 -m unittest discover -s tests -v`."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root: core/, contracts/
sys.path.insert(0, str(ROOT / "scripts"))
import crdb_query as cq  # noqa: E402

COLS = ["EXP-NAME", "EXP-TYPE", "EXP-HTML", "EXP-STARTYEAR", "SUBEXP-NAME", "SUBEXP-DESCRIPTION",
        "SUBEXP-ESCALE_RELERR", "SUBEXP-INFO", "SUBEXP-DISTANCE", "SUBEXP-DATES", "PUBLI-HTML",
        "PUBLI-DATAORIGIN", "DATA-QTY", "DATA-EAXIS", "DATA-E_MEAN", "DATA-E_BIN_L", "DATA-E_BIN_U",
        "DATA-VAL", "DATA-VAL_ERRSTAT_L", "DATA-VAL_ERRSTAT_U", "DATA-VAL_ERRSYST_L", "DATA-VAL_ERRSYST_U",
        "DATA-ISUPPERLIM", "phi [MV]"]


def row(sub="FAKE (2000/01-2000/12)", dates="2000/01/01-000000:2000/12/31-000000", qty="H", axis="R", origin="Table 1", val="1.5"):
    f = ["FAKE", "space", "https://example.invalid/", "2000", sub, "invented", "0", "info", "1", dates,
         "pub", origin, qty, axis, "2.0", "1.9", "2.1", val, "0.1", "0.1", "0.2", "0.2", "0", "600"]
    return ",".join('"%s"' % x for x in f)


def export(rows, date="2026/10/02-01:00:01"):
    head = ["# Data export from CRDB [http://lpsc.in2p3.fr/crdb]", "# Please cite CRDB publications:",
            "# Date: " + date, "# Format: CSV code (as import, with extra column for modulation)"]
    head += [f"# Col.{i + 1}  - {n}" for i, n in enumerate(COLS)] + ["#"]
    return ("\n".join(head) + "\n" + "\n".join(rows) + "\n").encode()


GOOD = export([row(), row(val="1.4"), row(sub="FAKE (2001/01-2001/12)", dates="2001/01/01-000000:2001/12/31-000000")])


class FakeHttp:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, max_bytes):
        self.calls.append(url)
        r = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        return cq.Response(r.status, r.content_type, r.data[: max_bytes + 1], r.url or url)


def resp(status=200, data=GOOD, ctype="application/json", url=""):
    return cq.Response(status, ctype, data, url)


def run(argv, http=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cq.main(argv, http=http)
        except SystemExit as e:  # argparse errors
            code = e.code
    return code, out.getvalue(), err.getvalue()


class ParamTests(unittest.TestCase):
    def test_defaults_are_the_cross_check_procedure(self):
        p = cq.build_params("H", "R")
        self.assertEqual(p, {"num": "H", "den": "", "energy_type": "R", "exp_dates": "AMS",
                             "combo_level": "0", "energy_convert_level": "0"})
        self.assertNotIn("time_series", p)

    def test_energy_type_has_no_default_and_is_validated(self):
        with self.assertRaises(cq.UsageError):
            cq.build_params("H", "GeV")
        with self.assertRaises(TypeError):
            cq.build_params("H")

    def test_bad_values_are_rejected(self):
        bad = [dict(num=" "), dict(combo_level=3), dict(energy_convert_level=-1), dict(time_series="yes"),
               dict(fmt="json"), dict(modulation="X"), dict(time_start="2011-05"), dict(time_stop="11"),
               dict(energy_start="abc"), dict(flux_rescaling="x")]
        for kw in bad:
            args = dict(num="H", energy_type="R")
            args.update(kw)
            with self.subTest(kw=kw), self.assertRaises(cq.UsageError):
                cq.build_params(**args)

    def test_optional_values_are_passed_through(self):
        p = cq.build_params("e+", "EK", den="e-", exp_dates="AMS(2011:2013)", time_start="2011/05", time_stop="2013",
                            time_series="only", fmt="csv", modulation="USO17", energy_start=1, energy_stop="50.5")
        self.assertEqual((p["time_start"], p["time_stop"], p["time_series"], p["format"], p["modulation"]),
                         ("2011/05", "2013", "only", "csv", "USO17"))
        self.assertEqual((p["energy_start"], p["energy_stop"]), ("1", "50.5"))

    def test_url_encodes_positron_and_keeps_the_base(self):
        url = cq.build_url(cq.build_params("e+", "EK", den="e-"))
        self.assertTrue(url.startswith("https://lpsc.in2p3.fr/crdb/rest.php?"))
        self.assertIn("num=e%2B", url)
        self.assertIn("den=e-", url)
        self.assertIn("exp_dates=AMS", url)

    def test_exp_dates_filter_can_be_dropped(self):
        self.assertNotIn("exp_dates", cq.build_params("H", "R", exp_dates=None))


class FetchRuleTests(unittest.TestCase):
    def fetcher(self, *responses, **kw):
        self.http = FakeHttp(*responses)
        self.sleeps = []
        return cq.Fetcher(http=self.http, sleep=self.sleeps.append, clock=lambda: "T", **kw)

    def test_ok(self):
        outcome, _, r = self.fetcher(resp()).fetch("https://x")
        self.assertEqual(outcome, "ok")
        self.assertEqual(len(self.http.calls), 1)

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

    def test_client_error_is_not_retried(self):
        outcome, _, _ = self.fetcher(resp(404, b"")).fetch("https://x")
        self.assertEqual((outcome, len(self.http.calls)), ("http-error", 1))

    def test_size_cap(self):
        big = GOOD + b"#" * (2 * (1 << 20))
        self.assertEqual(self.fetcher(resp(data=big), max_mb=1).fetch("https://x")[0], "too-large")

    def test_plain_http_is_refused(self):
        with self.assertRaises(cq.UsageError):
            cq.Http().get("http://lpsc.in2p3.fr/crdb/rest.php", 10)


class ParseTests(unittest.TestCase):
    def test_columns_come_from_the_header_and_rows_are_dicts(self):
        parsed = cq.parse_export(GOOD.decode())
        self.assertEqual(parsed["columns"], COLS)
        self.assertEqual(parsed["export_date"], "2026/10/02-01:00:01")
        self.assertEqual(len(parsed["rows"]), 3)
        self.assertEqual(parsed["rows"][1]["DATA-VAL"], "1.4")

    def test_row_with_wrong_field_count_is_an_error(self):
        with self.assertRaises(ValueError):
            cq.parse_export(export(['"a","b"']).decode())

    def test_quoted_commas_survive(self):
        r = row().replace('"invented"', '"a, b"')
        self.assertEqual(cq.parse_export(export([r]).decode())["rows"][0]["SUBEXP-DESCRIPTION"], "a, b")

    def test_summary_groups_subexperiments_and_labels_secondary(self):
        s = cq.summarize(cq.parse_export(GOOD.decode()))
        self.assertEqual(s["n_rows"], 3)
        self.assertEqual({(g["subexp_name"], g["n_rows"]) for g in s["sub_experiments"]},
                         {("FAKE (2000/01-2000/12)", 2), ("FAKE (2001/01-2001/12)", 1)})
        self.assertIn("secondary", s["label"])
        self.assertTrue(any("do not merge" in n for n in s["notes"]))
        self.assertNotIn("rows", s)
        rows = cq.summarize(cq.parse_export(GOOD.decode()), include_rows=True)["rows"]
        self.assertTrue(all(r["secondary"] is True for r in rows))


class CommandTests(unittest.TestCase):
    ARGS = ["--num", "H", "--energy-type", "R"]

    def test_url_command_is_offline(self):
        code, out, _ = run(["url"] + self.ARGS)
        self.assertEqual(code, 0)
        self.assertIn("combo_level=0", out)
        self.assertIn("energy_convert_level=0", out)

    def test_usage_errors_exit_2(self):
        self.assertEqual(run(["url", "--num", "H", "--energy-type", "R", "--combo-level", "5"])[0], 2)
        self.assertEqual(run(["url", "--num", "H"])[0], 2)

    def test_fetch_writes_export_and_provenance_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "sub" / "p.csv"
            http = FakeHttp(resp(url="https://lpsc.in2p3.fr/crdb/_dialog_result.php?x=1"))
            code, text, _ = run(["fetch"] + self.ARGS + ["--out", str(out)], http=http)
            self.assertEqual(code, 0, text)
            self.assertEqual(out.read_bytes(), GOOD)
            meta = json.loads(out.with_name("p.csv.meta.json").read_text())
            self.assertEqual(meta["http_status"], 200)
            self.assertEqual(meta["n_rows"], 3)
            self.assertEqual(meta["crdb_export_date"], "2026/10/02-01:00:01")
            self.assertEqual(len(meta["sha256"]), 64)
            self.assertIsNone(meta["crdb_version"])
            self.assertIn("not recorded", meta["crdb_version_note"])
            self.assertTrue(meta["requested_url"].startswith(cq.BASE_URL))
            self.assertEqual(meta["final_url"], "https://lpsc.in2p3.fr/crdb/_dialog_result.php?x=1")
            self.assertEqual(len(http.calls), 1)

    def test_fetch_records_a_version_only_when_given(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "p.csv"
            run(["fetch"] + self.ARGS + ["--out", str(out), "--crdb-version", "V4.2"], http=FakeHttp(resp()))
            meta = json.loads(out.with_name("p.csv.meta.json").read_text())
            self.assertEqual(meta["crdb_version"], "V4.2")
            self.assertIsNone(meta["crdb_version_note"])

    def test_fetch_refusal_writes_nothing_and_exits_1(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "p.csv"
            code, text, _ = run(["fetch"] + self.ARGS + ["--out", str(out)], http=FakeHttp(resp(429, b"")))
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(text)["status"], "blocked")
            self.assertFalse(out.exists())

    def test_fetch_does_not_overwrite_without_flag(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "p.csv"
            out.write_text("keep")
            http = FakeHttp(resp())
            self.assertEqual(run(["fetch"] + self.ARGS + ["--out", str(out)], http=http)[0], 2)
            self.assertEqual(out.read_text(), "keep")
            self.assertEqual(http.calls, [])
            self.assertEqual(run(["fetch"] + self.ARGS + ["--out", str(out), "--overwrite"], http=http)[0], 0)

    def test_fetch_with_no_data_rows_exits_1(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "p.csv"
            self.assertEqual(run(["fetch"] + self.ARGS + ["--out", str(out)], http=FakeHttp(resp(data=export([]))))[0], 1)

    def test_summarize_reads_a_saved_export_and_its_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "p.csv"
            run(["fetch"] + self.ARGS + ["--out", str(out)], http=FakeHttp(resp()))
            code, text, _ = run(["summarize", str(out)])
            self.assertEqual(code, 0)
            s = json.loads(text)
            self.assertEqual(s["n_rows"], 3)
            self.assertEqual(s["sidecar"]["n_rows"], 3)
            self.assertNotIn("rows", s)
            self.assertIn("rows", json.loads(run(["summarize", str(out), "--rows"])[1]))

    def test_summarize_errors(self):
        self.assertEqual(run(["summarize", "/nonexistent/x.csv"])[0], 2)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.csv"
            p.write_text(export(['"a","b"']).decode())
            self.assertEqual(run(["summarize", str(p)])[0], 2)


if __name__ == "__main__":
    unittest.main()
