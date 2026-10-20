"""T18: blinded values must not reach plots, ratios, logs, tables or caches. SYNTHETIC histogram values."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-computing" / "scripts"))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-measurement" / "scripts"))
from core.blinding import blinding as bl  # noqa: E402

try:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE = True
except ImportError:
    HAVE = False

EDGES = [100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0, 135.0, 140.0]
DATA = [812.0, 701.0, 615.0, 548.0, 1234.567, 1180.25, 431.0, 389.0]  # synthetic; bins 4 and 5 are in the SR
MC = [800.0, 705.0, 610.0, 552.0, 1101.5, 1050.75, 428.0, 392.0]
SR = {"variable": "mass", "low": 120.0, "high": 130.0}


class MaskTests(unittest.TestCase):
    def test_mask_binned(self):
        m = bl.mask_binned(EDGES, DATA, SR)
        self.assertEqual(m["blinded_bins"], [False] * 4 + [True, True] + [False] * 2)
        self.assertEqual(m["values"][4:6], [None, None])
        self.assertEqual(m["values"][:4], DATA[:4])

    def test_partial_overlap_is_blinded(self):
        self.assertEqual(bl.blinded_mask([110, 121, 140], SR), [True, True])

    def test_ratio_masked_in_blinded_bins(self):
        m = bl.mask_binned(EDGES, DATA, SR)
        r = bl.mask_ratio(DATA, MC, m["blinded_bins"])
        self.assertEqual(r[4:6], [None, None])
        self.assertAlmostEqual(r[0], 812 / 800)

    def test_seal_contains_bins_sums_and_ratios(self):
        s = bl.seal(EDGES, DATA, SR, [MC])
        for v in (1234.567, 1180.25, 1234.567 + 1180.25, sum(DATA), 1234.567 / 1101.5, 1234.567 - 1101.5):
            self.assertTrue(any(abs(x - v) < 1e-9 * abs(v) for x in s), v)
        self.assertNotIn(812.0, s)


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "outputs"
        self.out.mkdir()
        self.sealed = bl.seal(EDGES, DATA, SR, [MC])

    def tearDown(self):
        self.tmp.cleanup()

    def write_clean(self):
        m = bl.mask_binned(EDGES, DATA, SR)
        (self.out / "hist.json").write_text(json.dumps(m))
        (self.out / "run.log").write_text("sidebands: 812 701 615 548 | 431 389\nSR: blinded\n")
        (self.out / "table.csv").write_text("bin,data\n0,812\n1,701\n4,blinded\n")
        if HAVE:
            np.savez(self.out / "cache.npz", data=np.array([v if v is not None else np.nan for v in m["values"]]))

    def test_clean_outputs_pass(self):
        self.write_clean()
        rep = bl.scan_paths([self.out], self.sealed)
        self.assertTrue(rep["ok"], rep["leaks"])

    def test_leak_in_log_full_precision(self):
        self.write_clean()
        (self.out / "run.log").write_text("SR count 1234.567\n")
        self.assertFalse(bl.scan_paths([self.out], self.sealed)["ok"])

    def test_leak_at_printed_precision(self):
        self.write_clean()
        (self.out / "table.csv").write_text("bin,data\n4,1234.6\n")
        leaks = bl.scan_paths([self.out], self.sealed)["leaks"]
        self.assertEqual([lk["token"] for lk in leaks], ["1234.6"])
        (self.out / "table.csv").write_text("bin,data\n4,1.235e+03\n")
        self.assertFalse(bl.scan_paths([self.out], self.sealed)["ok"])

    def test_leak_through_ratio_and_total(self):
        self.write_clean()
        (self.out / "ratio.json").write_text(json.dumps({"ratio": [DATA[4] / MC[4]]}))
        self.assertFalse(bl.scan_paths([self.out], self.sealed)["ok"])
        (self.out / "ratio.json").write_text(json.dumps({"total": sum(DATA)}))
        self.assertFalse(bl.scan_paths([self.out], self.sealed)["ok"])

    @unittest.skipUnless(HAVE, "numpy required")
    def test_leak_in_cache(self):
        self.write_clean()
        np.savez(self.out / "cache.npz", raw=np.array(DATA))
        leaks = bl.scan_paths([self.out], self.sealed)["leaks"]
        self.assertTrue(any(lk.get("array") == "raw" for lk in leaks))

    def test_leak_through_cumulative_sum(self):
        # integrated yield above 125: the last three bins, one of them blinded
        (self.out / "integral.txt").write_text(f"N(m > 125) = {1180.25 + 431.0 + 389.0:.2f}\n")
        self.assertFalse(bl.scan_paths([self.out], self.sealed)["ok"])

    def test_leak_with_thousands_separator(self):
        (self.out / "table.md").write_text("| SR bin | 1,234.57 |\n")
        self.assertFalse(bl.scan_paths([self.out], self.sealed)["ok"])

    def test_seal_refuses_masked_values(self):
        with self.assertRaises(ValueError):
            bl.seal(EDGES, bl.mask_binned(EDGES, DATA, SR)["values"], SR)

    def test_short_numbers_are_not_false_positives(self):
        (self.out / "x.txt").write_text("bins 12 epochs 1.2 seed 7\n")
        self.assertTrue(bl.scan_paths([self.out], self.sealed)["ok"])

    def test_cli_seal_then_scan(self):
        import audit_blinded_outputs as audit
        private = Path(self.tmp.name) / "private"
        private.mkdir()
        (private / "h.json").write_text(json.dumps({"edges": EDGES, "values": DATA}))
        (private / "mc.json").write_text(json.dumps({"edges": EDGES, "values": MC}))
        self.write_clean()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(["seal", "--hist", str(private / "h.json"), "--low", "120", "--high", "130",
                                         "--reference", str(private / "mc.json"), "--out", str(private / "sealed.json")]), 0)
            self.assertEqual(audit.main(["scan", "--sealed", str(private / "sealed.json"), str(self.out)]), 0)
            (self.out / "run.log").write_text("1180.25\n")
            self.assertEqual(audit.main(["scan", "--sealed", str(private / "sealed.json"), str(self.out)]), 1)
            self.assertEqual(audit.main(["scan", "--sealed", str(private / "sealed.json"), str(private)]), 2)


@unittest.skipUnless(HAVE, "numpy required")
class ScanCompletenessAuditT04(unittest.TestCase):
    """Audit T04: .npy caches are read, and a scan that could not read every output is not a pass."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.sealed = bl.seal(EDGES, DATA, SR, [MC])

    def tearDown(self):
        self.tmp.cleanup()

    def test_sealed_value_in_npy_detected(self):
        np.save(self.out / "cache.npy", np.array(DATA))
        rep = bl.scan_paths([self.out / "cache.npy"], self.sealed)
        self.assertEqual(rep["status"], "fail")
        self.assertFalse(rep["ok"])
        self.assertTrue(any(lk["sealed_value"] == 1234.567 for lk in rep["leaks"]))

    def test_clean_npy_scans_to_completion(self):
        m = bl.mask_binned(EDGES, DATA, SR)["values"]
        np.save(self.out / "cache.npy", np.array([v if v is not None else np.nan for v in m]))
        rep = bl.scan_paths([self.out / "cache.npy"], self.sealed)
        self.assertEqual((rep["status"], rep["ok"], rep["unscanned"]), ("pass", True, []))
        self.assertEqual(len(rep["scanned"]), 1)

    def test_unsupported_only_is_incomplete_not_ok(self):
        (self.out / "hist.root").write_bytes(b"root")
        rep = bl.scan_paths([self.out / "hist.root"], self.sealed)
        self.assertEqual(rep["status"], "incomplete")
        self.assertFalse(rep["ok"])
        strict = bl.scan_paths([self.out / "hist.root"], self.sealed, strict=True)
        self.assertEqual(strict["status"], "fail")
        self.assertIn("incomplete", " ".join(strict["reasons"]))

    def test_named_exemption_with_reason(self):
        (self.out / "table.csv").write_text("bin,data\n0,812\n")
        (self.out / "plot.png").write_bytes(b"png")
        ex = {str(self.out / "plot.png"): "drawn from masked data; checked with check_figure in make_plots.py"}
        rep = bl.scan_paths([self.out], self.sealed, strict=True, exemptions=ex)
        self.assertEqual(rep["status"], "pass", rep)
        self.assertEqual([e["file"] for e in rep["exempted"]], [str(self.out / "plot.png")])
        rep = bl.scan_paths([self.out], self.sealed, strict=True, exemptions={str(self.out / "plot.png"): ""})
        self.assertEqual(rep["status"], "fail", "an exemption needs a reason")

    def test_exemption_cannot_hide_a_scannable_leak(self):
        (self.out / "run.log").write_text("SR 1234.567\n")
        rep = bl.scan_paths([self.out], self.sealed, strict=True, exemptions={str(self.out / "run.log"): "trust me"})
        self.assertEqual(rep["status"], "fail")
        self.assertTrue(rep["leaks"])

    def test_publication_manifest_needs_a_record_for_every_output(self):
        (self.out / "table.csv").write_text("bin,data\n0,812\n")
        missing = str(self.out / "fit.json")
        rep = bl.scan_paths([self.out], self.sealed, strict=True, outputs=[str(self.out / "table.csv"), missing])
        self.assertEqual(rep["status"], "fail")
        self.assertEqual(rep["outputs_without_record"], [missing])

    def test_cli_exit_codes(self):
        import audit_blinded_outputs as audit
        private = Path(self.tmp.name) / "private"
        private.mkdir()
        (private / "sealed.json").write_text(json.dumps({"sealed": self.sealed}))
        outd = self.out / "outputs"
        outd.mkdir()
        (outd / "a.csv").write_text("x\n812\n")
        (outd / "b.root").write_bytes(b"x")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(["scan", "--sealed", str(private / "sealed.json"), str(outd)]), 3)
            self.assertEqual(audit.main(["scan", "--strict", "--sealed", str(private / "sealed.json"), str(outd)]), 1)
            self.assertEqual(audit.main(["scan", "--strict", "--exempt", f"{outd / 'b.root'}=made from masked arrays by make_hist.py",
                                         "--sealed", str(private / "sealed.json"), str(outd)]), 0)


class FileAndConfigTests(unittest.TestCase):
    def test_scan_file_text_cache_and_binary(self):
        sealed = [1234.567]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "a.csv").write_text("bin,count\n4,1234.567\n")
            self.assertEqual([(h["line"], h["sealed_value"]) for h in bl.scan_file(d / "a.csv", sealed)], [(2, 1234.567)])
            (d / "clean.txt").write_text("nothing here 12\n")
            self.assertEqual(bl.scan_file(d / "clean.txt", sealed), [])
            (d / "fig.png").write_bytes(b"\x89PNG\r\n")
            res = bl.scan_file(d / "fig.png", sealed)
            self.assertTrue(res[0]["unscanned"])
            self.assertIn("binary format '.png'", res[0]["reason"])
            if HAVE:
                np.save(d / "c.npy", np.array([1.0, 1234.567, 3.0]))
                self.assertEqual(bl.scan_file(d / "c.npy", sealed)[0]["index"], 1)

    def test_load_project_blinding(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "hep-research.project.json"
            block = {"blinded": ["sr-mass"], "allowed_outputs": ["sidebands.json"],
                     "regions": [{"variable": "mass", "low": 120, "high": 130}]}
            cfg.write_text(json.dumps({"blinding": block}))
            self.assertEqual(bl.load_project_blinding(cfg), block)
            cfg.write_text(json.dumps({"profiles": []}))
            self.assertEqual(bl.load_project_blinding(cfg), {"blinded": [], "allowed_outputs": []})


class LowCountAndEncodingTests(unittest.TestCase):
    """Sealed low counts match only standalone numbers; logs in other encodings are read or reported (T06)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_low_counts_need_a_standalone_token(self):
        sealed = [0.0, 3.0]
        unrelated = ("run_3 finished on 2023-10-03 with v3.0.1, 3rd attempt, file h3.root, 1-3 GeV, "
                     "x3 /data/3/ 0x1f item_0\n")
        self.assertEqual(bl.scan_text(unrelated, sealed), [])
        hits = bl.scan_text("events in signal region: 3\nerrors: 0\n", sealed)
        self.assertEqual([(h["line"], h["sealed_value"], h.get("weak")) for h in hits], [(1, 3.0, True), (2, 0.0, True)])
        long_value = bl.scan_text("yield_1234.567", [1234.567])  # a value with 3+ digits still matches inside text
        self.assertEqual(len(long_value), 1)
        self.assertNotIn("weak", long_value[0])

    def test_utf16_and_latin1_logs_are_read(self):
        sealed = [1234.567]
        (self.out / "a.log").write_bytes("caf\u00e9 yield 1234.567\n".encode("utf-16"))  # with a BOM
        (self.out / "b.log").write_bytes("yield 1234.567\n".encode("utf-16-le"))  # no BOM
        (self.out / "c.log").write_bytes("r\u00e9sum\u00e9 1234.567\n".encode("latin-1"))
        rep = bl.scan_paths([self.out], sealed)
        self.assertEqual(rep["status"], "fail")
        self.assertEqual(sorted((Path(h["file"]).name, h["encoding"]) for h in rep["leaks"]),
                         [("a.log", "utf-16"), ("b.log", "utf-16-le"), ("c.log", "latin-1")])

    def test_undecodable_text_is_incomplete_never_pass(self):
        (self.out / "d.log").write_bytes(b"\x00\x01\x02 1234.567 \x00\xff\x00")
        rep = bl.scan_paths([self.out], [1234.567])
        self.assertEqual(rep["status"], "incomplete")
        self.assertFalse(rep["ok"])
        self.assertIn("cannot be decoded", rep["unscanned"][0]["reason"])


class RenderingOracleTests(unittest.TestCase):
    """sci-fix BLINDING-SCANNER, axis C. Independent implementation: the renderings scan_text claims to detect (plain
    decimal and exponent forms with at least 3 significant digits, thousands commas, the Unicode minus, a flipped sign,
    percentages) generated here with Python's own formatting, in every text encoding decode_text claims (UTF-8 with and
    without BOM, UTF-16 and UTF-32 with BOM, UTF-16-LE/BE without, Latin-1), and the printed-precision rule ("the
    token equals the target rounded at the token's own last printed digit") evaluated in exact decimal arithmetic.
    Negative controls emulate the pre-fix scanner (b6334c04^): UTF-8 decoding with replacement, and short sealed
    values matched as any equal token."""

    ENCODINGS = ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "utf-32", "latin-1")

    @staticmethod
    def sealed_values(n, seed):
        import random
        rng = random.Random(seed)
        out = []
        while len(out) < n:  # 12 random significant digits, magnitudes 1e-4 to 1e7, either sign
            t = rng.choice((-1, 1)) * rng.randrange(10 ** 11, 10 ** 12) * 10.0 ** rng.randint(-15, -4)
            if bl._significant_digits(t) >= 3:
                out.append(t)
        return out

    @staticmethod
    def significant(token):
        """Significant digits printed in a token (leading zeros, sign, exponent and separators excluded)."""
        mant = token.replace(",", "").replace("−", "-").lstrip("+-").rstrip("%").lower().split("e")[0]
        return len(mant.replace(".", "").lstrip("0"))

    def renderings(self, t):
        import math
        e = math.floor(math.log10(abs(t)))
        forms = [repr(t), f"{-t:.7g}", f"{100 * t:.6g}%", f"{100 * t:.4g} %"]
        forms += [f"{t:.{k}g}" for k in range(3, 11)] + [f"{t:.{k}e}" for k in range(2, 9)]
        forms += [f"{t:.{d}f}" for d in (max(0, 2 - e), max(0, 2 - e) + 3)]
        if abs(t) >= 1000:
            forms += [f"{t:,.{max(0, 2 - e)}f}", f"{t:,.3f}"]
        forms += [s.replace("-", "−") for s in forms if s.startswith("-")]
        return [s for s in forms if self.significant(s) >= 3]

    def test_every_claimed_rendering_is_found_in_every_claimed_encoding(self):
        missed_before = wide = 0
        for t in self.sealed_values(60, seed=11):
            forms = self.renderings(t)
            for enc in self.ENCODINGS:
                lines = [s for s in forms if enc != "latin-1" or "−" not in s]  # Latin-1 has no U+2212
                body = "".join(f"value: {s} (synthetic)\n" for s in lines)
                if enc == "latin-1":
                    body = "résumé\n" + body  # a non-ASCII character, so the bytes are not UTF-8
                raw = body.encode(enc)
                text, used = bl.decode_text(raw)
                self.assertEqual(used, enc)  # recorded with the hits (scan_file) for a non-UTF-8 file
                hit_lines = {h["line"] for h in bl.scan_text(text, [t])}
                first = 2 if enc == "latin-1" else 1
                want = set(range(first, first + len(lines)))
                with self.subTest(t=t, encoding=enc):
                    self.assertEqual(want - hit_lines, set(), [lines[i - first] for i in sorted(want - hit_lines)])
                if enc in ("utf-16", "utf-16-le", "utf-16-be", "utf-32"):  # pre-fix: UTF-8 with replacement
                    before = {h["line"] for h in bl.scan_text(raw.decode("utf-8", errors="replace"), [t])}
                    missed_before += len(want - before)
                    wide += len(want)
        self.assertGreater(missed_before, 0.9 * wide, (missed_before, wide))  # observed: all 8212 missed

    def test_printed_precision_rule_against_exact_decimal_arithmetic(self):
        """Tokens at k = 3..9 significant digits, j = -2..2 steps from the correctly rounded value, with either sign:
        the scanner flags a token exactly when |token - |t|| <= step/2 (Decimal, exact) or |token - |t|| <= 1e-9 |t|.
        j = +-1, +-2 are the numbers that must not alarm. Cases within 1e-6 step of the boundary are not asserted
        (the scanner compares in floating point with a 1e-9 slack). A step above 1 is printed in exponent form. An
        integer token's trailing zeros count as rounding down to 3 significant digits (5680 is read like 5.68e3), so
        its step is 10^r larger, r = min(trailing zeros, digits - 3), counted here from the token's text."""
        from decimal import Decimal, localcontext

        flagged = silent = 0
        for t in self.sealed_values(80, seed=12):
            exact = abs(Decimal(t))
            for k in range(3, 10):
                with localcontext() as ctx:
                    ctx.prec = k
                    rounded = +exact
                step = Decimal(1).scaleb(rounded.adjusted() - k + 1)
                for j in (-2, -1, 0, 1, 2):
                    value = rounded + j * step
                    if value <= 0:
                        continue
                    diff = abs(value - exact)
                    decimals = max(0, -(rounded.adjusted() - k + 1))
                    fixed = step <= 1 and rounded.adjusted() >= -5
                    text = f"{value:.{decimals}f}" if fixed else f"{value:.{k - 1}e}"
                    eff = step
                    if fixed and "." not in text:  # an integer: trailing zeros may be rounding, down to 3 digits
                        digits = text.lstrip("0")
                        eff = step * 10 ** min(len(digits) - len(digits.rstrip("0")), len(digits) - 3)
                    if abs(diff - eff / 2) < eff * Decimal("1e-6"):
                        continue
                    expected = diff <= eff / 2 or diff <= Decimal("1e-9") * exact
                    for sign in ("", "-"):
                        tok = sign + text
                        with self.subTest(t=t, k=k, j=j, token=tok):
                            self.assertEqual(bool(bl.scan_text(f"x = {tok} ;\n", [t])), expected)
                    flagged += expected
                    silent += not expected
        self.assertGreater(flagged, 500)
        self.assertGreater(silent, 2000)

    def test_low_counts_alarm_only_standalone_and_the_pre_fix_rule_does_not(self):
        """Short sealed values (fewer than 3 significant digits): every standalone rendering is a weak hit, and the
        same digits inside a name, version, date, range or path are not. The pre-fix rule (any equal token) flags
        the embedded ones."""
        embedded = ("run_{v} ok", "v{v}.0.1", "2023-10-{v}", "1-{v} GeV", "/data/{v}/x", "h{v}.root", "{v}rd try",
                    "item_{v}", "x{v} y")
        standalone = ("count: {v}", "{v} events", "n = {v},", "({v})", "[{v}]", "= {v};")
        pre_fix = 0
        for v in ("0", "3", "7", "12", "50", "99", "0.5", "2.5", "100"):
            t = float(v)
            self.assertLess(bl._significant_digits(t), bl.WEAK_DIGITS)
            for form in embedded:
                text = form.format(v=v) + "\n"
                with self.subTest(v=v, text=text):
                    self.assertEqual(bl.scan_text(text, [t]), [])
                pre_fix += any(bl._close(float(m.group(0)), t, 1e-9) for m in bl.NUMBER.finditer(text))
            for form in standalone:
                hits = bl.scan_text(form.format(v=v) + "\n", [t])
                with self.subTest(v=v, form=form):
                    self.assertEqual([(h["sealed_value"], h.get("weak")) for h in hits], [(t, True)])
        self.assertGreater(pre_fix, 40, pre_fix)


@unittest.skipUnless(HAVE, "numpy and matplotlib required")
class FigureTests(unittest.TestCase):
    def centers(self):
        return [0.5 * (a + b) for a, b in zip(EDGES[:-1], EDGES[1:])]

    def test_masked_plot_passes(self):
        m = bl.mask_binned(EDGES, DATA, SR)
        y = [np.nan if v is None else v for v in m["values"]]
        fig, ax = plt.subplots()
        ax.errorbar(self.centers(), y, yerr=np.sqrt(np.nan_to_num(y)), fmt="o")
        ax.stairs(MC, EDGES)  # the prediction may be shown
        ax.stairs(y, EDGES)
        found = bl.check_figure(fig, SR)
        plt.close(fig)
        # only the MC stairs fall in the SR; data artists do not
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["artist"], "steps")

    def test_unmasked_points_and_ratio_panel_are_caught(self):
        fig, (ax, rx) = plt.subplots(2, 1)
        ax.errorbar(self.centers(), DATA, yerr=np.sqrt(DATA), fmt="o", label="data")
        rx.plot(self.centers(), np.array(DATA) / np.array(MC), "o", label="data/MC")
        found = bl.check_figure(fig, SR)
        plt.close(fig)
        self.assertTrue(any(f["axes"] == 0 for f in found))
        self.assertTrue(any(f["axes"] == 1 and f["label"] == "data/MC" for f in found))

    def test_fill_between_hist2d_imshow_and_text_are_caught(self):
        sealed = bl.seal(EDGES, DATA, SR)
        x = np.array(self.centers())
        for draw, artist in ((lambda ax: ax.fill_between(x, np.array(DATA) - 10, np.array(DATA) + 10), "area"),
                             (lambda ax: ax.hist2d(np.repeat(x, 3), np.tile([1.0, 2.0, 3.0], len(x)), bins=[EDGES, 3]), "mesh"),
                             (lambda ax: ax.imshow(np.ones((3, 8)), extent=(EDGES[0], EDGES[-1], 0, 3), aspect="auto"), "image"),
                             (lambda ax: ax.text(102.0, 1.0, f"N(SR) = {DATA[4]}"), "text")):
            fig, ax = plt.subplots()
            draw(ax)
            found = bl.check_figure(fig, SR, sealed)
            plt.close(fig)
            self.assertIn(artist, {f["artist"] for f in found}, artist)

    def test_masked_areas_images_and_a_blinded_label_pass(self):
        m = bl.mask_binned(EDGES, DATA, SR)
        y = np.array([np.nan if v is None else v for v in m["values"]])
        x = np.array(self.centers())
        img = np.ones((3, 8))
        img[:, 4:6] = np.nan  # the blinded columns are not drawn
        fig, ax = plt.subplots()
        ax.fill_between(x, y - 10, y + 10, where=np.isfinite(y))
        ax.imshow(img, extent=(EDGES[0], EDGES[-1], 0, 3), aspect="auto")
        ax.text(125.0, 1.0, "blinded")  # a label inside the region is not a leak
        ax.set_title(f"total outside the SR: {sum(v for v in m['values'] if v is not None):.1f}")
        found = bl.check_figure(fig, SR, bl.seal(EDGES, DATA, SR))
        plt.close(fig)
        self.assertEqual(found, [])

    def test_bar_chart_caught(self):
        fig, ax = plt.subplots()
        ax.bar(self.centers(), DATA, width=5.0)
        found = bl.check_figure(fig, SR)
        plt.close(fig)
        self.assertEqual(sum(f["artist"] == "bar" for f in found), 2)


class MaskScriptTests(unittest.TestCase):
    def test_mask_script(self):
        import mask_blinded_bins as mb
        with tempfile.TemporaryDirectory() as tmp:
            h = Path(tmp) / "h.json"
            h.write_text(json.dumps({"edges": EDGES, "values": DATA}))
            r = Path(tmp) / "mc.json"
            r.write_text(json.dumps({"edges": EDGES, "values": MC}))
            out = Path(tmp) / "m.json"
            self.assertEqual(mb.main(["--hist", str(h), "--low", "120", "--high", "130", "--reference", str(r), "--out", str(out)]), 0)
            d = json.loads(out.read_text())
            self.assertEqual(d["values"][4:6], [None, None])
            self.assertEqual(d["ratio_to_reference"][4:6], [None, None])
            self.assertTrue(bl.scan_paths([out], bl.seal(EDGES, DATA, SR, [MC]))["ok"])


class RoundingZerosTests(unittest.TestCase):
    """sci-fix BLINDING-ROUNDING-ZEROS: an integer printed with rounding zeros (22010 or 22000 for a sealed 22014) is
    a rendering of the sealed value; before the fix the printed-precision rule read every trailing zero as a printed
    digit (step 1) and passed it. The rule now reads an integer token's trailing zeros as rounding, down to 3
    significant digits: 22000 is matched like 2.20e4, while 2.2e4 (two digits) stays out of scope."""

    @staticmethod
    def renders(token, sealed):
        """Oracle (Decimal, not the scanner's floating-point step): the integer token is a rendering of the sealed
        value when it equals the value rounded half up or half down at a place 10^p its trailing zeros allow, p from
        0 to min(trailing zeros, digits - 3)."""
        from decimal import ROUND_HALF_DOWN, ROUND_HALF_UP, Decimal

        digits = token.lstrip("0")
        places = min(len(digits) - len(digits.rstrip("0")), len(digits) - 3)
        exact = Decimal(repr(sealed))
        return any(Decimal(token) == exact.quantize(Decimal(1).scaleb(p), rounding=mode).quantize(Decimal(1))
                   for p in range(places + 1) for mode in (ROUND_HALF_UP, ROUND_HALF_DOWN))

    @staticmethod
    def pre_fix(token, sealed):
        """The rule before the fix: the step is the last printed digit, 1 for an integer."""
        return abs(int(token) - sealed) <= 0.5 * (1 + 1e-9)

    def test_rounding_zeros_exhaustively_against_decimal_rounding(self):
        """Exhaustive over the stated domain: every sealed value n and n + 0.5 for n = 100 to 4999 (ties included)
        against every integer token ending in zero within 600 of it (1,149,200 pairs); the printed-precision match
        equals the Decimal oracle on every pair. The oracle finds 8679 renderings; the pre-fix rule (negative control)
        finds only the 1470 that are exact or last-digit matches and misses the other 7209."""
        checked = hits = missed_before = 0
        for n in range(100, 5000):
            for sealed in (float(n), n + 0.5):
                low = max(100, (int(sealed) - 600) // 10 * 10)
                for value in range(low, int(sealed) + 601, 10):
                    token = str(value)
                    want = self.renders(token, sealed)
                    if bl._printed_match(token, sealed) != want:
                        self.fail(f"token {token} for sealed {sealed}: scanner {not want}, oracle {want}")
                    checked += 1
                    hits += want
                    missed_before += want and not self.pre_fix(token, sealed)
        self.assertEqual((checked, hits, missed_before), (1_149_200, 8679, 7209))

    def test_rounding_zeros_sampled_beyond_the_exhaustive_domain(self):
        """Beyond the exhaustive domain: 4000 seeded sealed values from 5000 to 10^7 (integers, half-integers and two
        decimals), each against integer tokens near it rounded at 10^1 to 10^5 (the rounded value and two steps either
        side, every token ending in zero), the same Decimal oracle. A sample, not an exhaustive claim."""
        import random

        rng, hits, checked = random.Random(20261022), 0, 0
        for _ in range(4000):
            sealed = rng.randrange(5000, 10 ** 7) + rng.choice((0.0, 0.5, rng.randrange(100) / 100))
            for q in range(1, 6):
                step = 10 ** q
                for j in (-2, -1, 0, 1, 2):
                    value = (round(sealed / step) + j) * step
                    if value < 100:
                        continue
                    token = str(value)
                    want = self.renders(token, sealed)
                    self.assertEqual(bl._printed_match(token, sealed), want, (token, sealed))
                    hits += want
                    checked += 1
        self.assertGreater(hits, 2000, hits)
        self.assertGreater(checked - hits, 10_000, checked)

    def test_scan_text_flags_rounded_integers_and_not_coarser_ones(self):
        """End to end through scan_text, with the sealed 22014: plain and comma-grouped renderings with rounding
        zeros are hits; values outside the half step, two-digit readings and zeros printed before a point or in an
        exponent's mantissa are not."""
        for text, want in (("about 22000 events", True), ("about 22,000 events", True), ("22010 events", True),
                           ("N = 22014", True), ("about 2.20e4", True), ("22050 events", False),
                           ("21900 events", False), ("20000 events", False), ("about 2.2e4", False),
                           ("x 22,010 y", True), ("deficit -22000", True),
                           ("22000.0 events", False), ("2.2010e4", False)):  # a point or exponent: zeros are digits
            with self.subTest(text=text):
                self.assertEqual(bool(bl.scan_text(text, [22014.0])), want)


if __name__ == "__main__":
    unittest.main()
