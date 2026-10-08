"""U11 (AGENTIC-R5 T0.6): the blinding tools with synthetic sentinels (N09-N16). Agent-visible scan output carries no
sealed value, token, location or count; seal prints no count; the N11 quantities are sealed; N12 renderings are
detected or listed as out of scope; N13 and N14 inputs are incomplete; invalid bin edges stop seal and
mask_blinded_bins; check_figure detects the N16 artists or lists them as unchecked."""
from __future__ import annotations

import contextlib
import io
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-computing" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "hep-analysis" / "scripts"))

from core.blinding import blinding as bl  # noqa: E402

try:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE = True
except ImportError:  # pragma: no cover
    HAVE = False

EDGES = [100, 110, 120, 130, 140]
VALUES = [812.25, 640.5, 4731.3712, 505.125]
REF = [800.0, 650.0, 4600.0, 510.0]


def run(main, argv) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = main(argv)
        except SystemExit as exc:  # argparse usage errors
            code = exc.code
    return code, buf.getvalue()


class AgentVisibleOutputN09N10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "private").mkdir()
        (self.d / "out").mkdir()
        (self.d / "private" / "hist.json").write_text(json.dumps({"edges": EDGES, "values": VALUES}))
        import audit_blinded_outputs as audit
        self.audit = audit
        self.sealed = self.d / "private" / "sealed.json"
        self.code, self.seal_out = run(audit.main, ["seal", "--hist", str(self.d / "private" / "hist.json"),
                                                    "--low", "120", "--high", "130", "--out", str(self.sealed)])

    def tearDown(self):
        self.tmp.cleanup()

    def test_seal_prints_no_count(self):
        self.assertEqual(self.code, 0)
        self.assertNotIn("count", self.seal_out)
        self.assertEqual(set(json.loads(self.seal_out)), {"status", "out"})

    def test_rounded_guess_returns_only_a_fixed_status(self):
        (self.d / "out" / "log.txt").write_text("guess 4731\n")
        code, out = run(self.audit.main, ["scan", "--sealed", str(self.sealed), str(self.d / "out")])
        self.assertEqual(code, 1)
        self.assertNotIn("4731", out)
        self.assertNotIn("log.txt", out)
        self.assertNotIn("leaks", json.loads(out))
        self.assertEqual(json.loads(out)["status"], "fail")

    def test_grid_probe_reveals_nothing_but_the_status(self):
        (self.d / "out" / "grid.txt").write_text("\n".join(f"{x / 10:.1f}" for x in range(40000, 50000)))
        code, out = run(self.audit.main, ["scan", "--sealed", str(self.sealed), str(self.d / "out")])
        self.assertEqual(code, 1)
        view = json.loads(out)
        self.assertNotIn("4731.3712", out)
        self.assertNotIn("leaks", view)
        self.assertEqual(set(view) - {"status", "ok", "unscanned", "limitation", "out_of_scope_renderings", "note",
                                      "scanned_files", "exempted"}, set())

    def test_details_go_to_the_report_file(self):
        (self.d / "out" / "log.txt").write_text("guess 4731\n")
        report = self.d / "private" / "report.json"
        run(self.audit.main, ["scan", "--sealed", str(self.sealed), "--report", str(report), str(self.d / "out")])
        self.assertEqual(json.loads(report.read_text())["leaks"][0]["sealed_value"], 4731.3712)

    def test_report_inside_outputs_is_refused(self):
        code, _ = run(self.audit.main, ["scan", "--sealed", str(self.sealed), "--report", str(self.d / "out" / "r.json"),
                                        str(self.d / "out")])
        self.assertEqual(code, 2)

    def test_rtol_is_not_caller_controlled_at_scan(self):
        (self.d / "out" / "log.txt").write_text("x 1\n")
        code, _ = run(self.audit.main, ["scan", "--sealed", str(self.sealed), "--rtol", "0.5", str(self.d / "out")])
        self.assertEqual(code, 2)
        code, _ = run(self.audit.main, ["seal", "--hist", str(self.d / "private" / "hist.json"), "--low", "120",
                                        "--high", "130", "--rtol", "0.5", "--out", str(self.sealed)])
        self.assertEqual(code, 2)

    def test_empty_or_malformed_sealed_file_is_an_error(self):
        (self.d / "out" / "log.txt").write_text("x 1\n")
        for doc in ({"sealed": []}, {"sealed": None}, {"sealed": ["4731.3712"]}, {"sealed": 4731.3712}):
            with self.subTest(doc=doc):
                self.sealed.write_text(json.dumps(doc))
                code, _ = run(self.audit.main, ["scan", "--sealed", str(self.sealed), str(self.d / "out")])
                self.assertEqual(code, 2)


class DerivedQuantitiesN11(unittest.TestCase):
    def test_promised_quantities_are_sealed(self):
        s = bl.seal(EDGES, VALUES, {"low": 115, "high": 135}, [REF])
        blind, ref = VALUES[1:], REF[1:]
        n, b, total = sum(blind), sum(ref), sum(VALUES)
        for name, q in (("difference of sums", n - b), ("sqrt of sum", math.sqrt(n)), ("sqrt of bin", math.sqrt(blind[1])),
                        ("fraction of total", n / total), ("bin fraction", blind[1] / total),
                        ("(N-B)/sqrt(B)", (n - b) / math.sqrt(b)), ("reference/data", b / n),
                        ("bin (N-B)/sqrt(B)", (blind[1] - ref[1]) / math.sqrt(ref[1]))):
            with self.subTest(name):
                self.assertTrue(any(math.isclose(x, q, rel_tol=1e-12) for x in s), name)

    def test_unsealed_list_is_documented(self):
        self.assertTrue(bl.NOT_SEALED)
        self.assertIn("NOT_SEALED", bl.seal.__doc__)


class RenderingsN12(unittest.TestCase):
    SEALED = [4731.3712, -12.345, 0.3712]

    def found(self, text):
        return bool(bl.scan_text(text, self.SEALED))

    def test_detected_renderings(self):
        for text in ("deficit of 12.345 events", "−12.345", "−4731.37", "fraction 37.12%", "37.12 %",
                     "+4731.37", "4,731.37"):
            with self.subTest(text=text):
                self.assertTrue(self.found(text))

    def test_out_of_scope_renderings_are_listed(self):
        self.assertTrue(bl.OUT_OF_SCOPE_RENDERINGS)
        rep = bl.scan_paths([], self.SEALED)
        self.assertIn("OUT_OF_SCOPE_RENDERINGS", rep["limitation"])
        self.assertEqual(bl.agent_view(rep)["out_of_scope_renderings"], list(bl.OUT_OF_SCOPE_RENDERINGS))

    def test_unrelated_numbers_still_pass(self):
        self.assertFalse(self.found("bins 12 epoch 37 seed 4730 lr 0.25"))


@unittest.skipUnless(HAVE, "numpy and matplotlib are needed")
class IncompleteInputsN13N14(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_non_real_dtypes_are_incomplete(self):
        arrays = {"complex": np.array([4731.3712 + 0j]), "string": np.array(["4731.3712"]),
                  "structured": np.array([(4731.3712, 1)], dtype=[("a", "f8"), ("b", "i4")])}
        for name, arr in arrays.items():
            with self.subTest(dtype=name):
                np.save(self.d / f"{name}.npy", arr)
                self.assertEqual(bl.scan_paths([self.d / f"{name}.npy"], [4731.3712])["status"], "incomplete")

    def test_symlinked_directory_is_incomplete_not_skipped(self):
        target = self.d / "elsewhere"
        target.mkdir()
        (target / "log.txt").write_text("4731.3712\n")
        out = self.d / "out"
        out.mkdir()
        (out / "clean.txt").write_text("nothing\n")
        os.symlink(target, out / "linked")
        rep = bl.scan_paths([out], [4731.3712])
        self.assertEqual(rep["status"], "incomplete")
        self.assertEqual([u["file"] for u in rep["unscanned"]], [str(out / "linked")])


class InvalidEdgesN15(unittest.TestCase):
    def test_seal_and_mask_refuse_invalid_edges(self):
        for edges in ([140, 130, 120, 110, 100], [100, 120, 110, 130, 140], [100, 110, float("nan"), 130, 140], [100]):
            with self.subTest(edges=edges):
                with self.assertRaises(ValueError):
                    bl.seal(edges, VALUES[:max(len(edges) - 1, 1)], {"low": 120, "high": 130})
                with self.assertRaises(ValueError):
                    bl.mask_binned(edges, VALUES[:max(len(edges) - 1, 1)], {"low": 120, "high": 130})

    def test_mask_cli_exits_non_zero(self):
        import mask_blinded_bins as mask
        with tempfile.TemporaryDirectory() as td:
            h = Path(td) / "h.json"
            h.write_text(json.dumps({"edges": [140, 130, 120, 110, 100], "values": VALUES}))
            code, out = run(mask.main, ["--hist", str(h), "--low", "120", "--high", "130"])
            self.assertEqual(code, 2)
            self.assertEqual(out, "")


@unittest.skipUnless(HAVE, "numpy and matplotlib are needed")
class FigureCoverageN16(unittest.TestCase):
    REGION = {"low": 120, "high": 130}
    SEALED = [4731.3712]

    def check(self, draw, sealed=True):
        fig, ax = plt.subplots()
        draw(fig, ax)
        out = bl.check_figure(fig, self.REGION, self.SEALED if sealed else None)
        plt.close(fig)
        return out

    def test_texts_anywhere_in_the_figure(self):
        cases = {
            "axis label": lambda f, a: a.set_xlabel("yield 4731.37"),
            "legend": lambda f, a: (a.plot([0, 1], [0, 1], label="SR 4731.37"), a.legend()),
            "table": lambda f, a: a.table(cellText=[["4731.37"]]),
            "colorbar label": lambda f, a: f.colorbar(a.imshow([[0, 1]], extent=(0, 10, 0, 1)), label="max 4731.37"),
            "tick label": lambda f, a: (a.set_yticks([1]), a.set_yticklabels(["4731.37"])),
        }
        for name, draw in cases.items():
            with self.subTest(name):
                found = self.check(draw)
                self.assertTrue(any(x["artist"] == "text" for x in found), found)
                self.assertNotIn("sealed_values", json.dumps(found))
                self.assertNotIn("4731", json.dumps(found))

    def test_fill_contourf_and_axhline(self):
        xs = np.linspace(100, 140, 41)
        self.assertTrue(self.check(lambda f, a: a.fill([115, 125, 125, 115], [0, 0, 1, 1]), sealed=False))
        self.assertTrue(self.check(lambda f, a: a.contourf(xs, [0, 1], np.vstack([xs, xs])), sealed=False))
        found = self.check(lambda f, a: a.axhline(4731.3712))
        self.assertEqual([x["artist"] for x in found], ["y-value"])

    def test_categorical_x_does_not_crash_and_is_listed(self):
        fig, ax = plt.subplots()
        ax.plot(["a", "b"], [1, 2])
        rep = bl.check_figure_report(fig, self.REGION)
        plt.close(fig)
        self.assertTrue(any("categorical" in u for u in rep["unchecked"]))
        self.assertTrue(any("y axis" in u for u in rep["unchecked"]))


if __name__ == "__main__":
    unittest.main()
