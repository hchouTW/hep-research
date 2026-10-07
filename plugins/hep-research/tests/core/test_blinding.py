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
sys.path.insert(0, str(PLUGIN / "skills" / "hep-analysis" / "scripts"))
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


if __name__ == "__main__":
    unittest.main()
