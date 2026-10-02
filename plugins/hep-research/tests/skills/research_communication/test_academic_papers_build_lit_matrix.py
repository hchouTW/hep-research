"""Unit tests for skills/research-communication/scripts/build_lit_matrix.py.

Run with:
    python -m unittest discover -s tests -t .

from the plugin root (plugins/hep-research).
"""
from __future__ import annotations

import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills" / "research-communication"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import build_lit_matrix as blm  # noqa: E402


class TestBuildLitMatrix(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def _write_csv(self, name: str, content: str) -> Path:
        p = self.tmpdir / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_read_rows_basic(self):
        csv_path = self._write_csv(
            "notes.csv",
            "key,year,method\nA:2020,2020,cut-based\nB:2019,2019,BDT\n",
        )
        fieldnames, rows = blm.read_rows(csv_path)
        self.assertEqual(fieldnames, ["key", "year", "method"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["key"], "A:2020")

    def test_sort_by_numeric_column_ascending(self):
        rows = [{"year": "2021"}, {"year": "2019"}, {"year": "2020"}]
        sorted_rows = blm.sort_rows(rows, "year", descending=False)
        self.assertEqual([r["year"] for r in sorted_rows], ["2019", "2020", "2021"])

    def test_sort_by_numeric_column_descending(self):
        rows = [{"year": "2021"}, {"year": "2019"}, {"year": "2020"}]
        sorted_rows = blm.sort_rows(rows, "year", descending=True)
        self.assertEqual([r["year"] for r in sorted_rows], ["2021", "2020", "2019"])

    def test_sort_by_text_column(self):
        rows = [{"method": "unfolding"}, {"method": "BDT"}, {"method": "cut-based"}]
        sorted_rows = blm.sort_rows(rows, "method", descending=False)
        self.assertEqual([r["method"] for r in sorted_rows], ["BDT", "cut-based", "unfolding"])

    def test_no_sort_preserves_order(self):
        rows = [{"year": "2021"}, {"year": "2019"}]
        result = blm.sort_rows(rows, None, descending=False)
        self.assertEqual(result, rows)

    def test_escape_cell_handles_pipe_and_newline(self):
        self.assertEqual(blm.escape_cell("125.3 | 0.4"), "125.3 \\| 0.4")
        self.assertEqual(blm.escape_cell("line one\nline two"), "line one line two")

    def test_to_markdown_table_shape(self):
        table = blm.to_markdown_table(
            ["key", "year"],
            [{"key": "A", "year": "2020"}, {"key": "B", "year": "2019"}],
        )
        lines = table.splitlines()
        self.assertEqual(lines[0], "| key | year |")
        self.assertEqual(lines[1], "| --- | --- |")
        self.assertEqual(lines[2], "| A | 2020 |")
        self.assertEqual(lines[3], "| B | 2019 |")

    def test_main_writes_output_file(self):
        csv_path = self._write_csv(
            "notes.csv",
            "key,year,method\nA:2020,2020,cut-based\nB:2019,2019,BDT\n",
        )
        out_path = self.tmpdir / "out.md"
        code = blm.main([str(csv_path), "--sort-by", "year", "-o", str(out_path)])
        self.assertEqual(code, 0)
        content = out_path.read_text(encoding="utf-8")
        self.assertIn("| key | year | method |", content)
        # 2019 (B) should sort before 2020 (A) with ascending sort
        self.assertLess(content.index("B:2019"), content.index("A:2020"))

    def test_main_rejects_unknown_sort_column(self):
        csv_path = self._write_csv("notes.csv", "key,year\nA,2020\n")
        code = blm.main([str(csv_path), "--sort-by", "not_a_column"])
        self.assertEqual(code, 2)

    def test_main_rejects_missing_file(self):
        code = blm.main([str(self.tmpdir / "does_not_exist.csv")])
        self.assertEqual(code, 2)

    # Malformed-CSV cases found with a realistic 18-paper notes file (2026-09-26).

    def test_excel_bom_is_not_part_of_first_column(self):
        p = self.tmpdir / "bom.csv"
        p.write_text("key,year\nA,2020\n", encoding="utf-8-sig")
        fieldnames, _ = blm.read_rows(p)
        self.assertEqual(fieldnames[0], "key")

    def test_short_row_gives_empty_cells(self):
        _, rows = blm.read_rows(self._write_csv("short.csv", "key,year,method\nB,2019\n"))
        self.assertEqual(rows, [{"key": "B", "year": "2019", "method": ""}])
        self.assertIn("| B | 2019 |  |", blm.to_markdown_table(["key", "year", "method"], rows))

    def test_extra_cells_dropped_with_warning(self):
        p = self._write_csv("extra.csv", "key,year\nA,2020,surplus\n")
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            _, rows = blm.read_rows(p)
        self.assertEqual(rows, [{"key": "A", "year": "2020"}])
        self.assertIn("more than the header", err.getvalue())

    def test_empty_and_non_utf8_files_exit_2_without_traceback(self):
        empty = self._write_csv("empty.csv", "")
        latin1 = self.tmpdir / "latin1.csv"
        latin1.write_bytes("key\nMüller\n".encode("latin-1"))
        for p in (empty, latin1):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                self.assertEqual(blm.main([str(p)]), 2)
            self.assertTrue(err.getvalue().startswith("error:"))

    def test_semicolon_file_warns(self):
        p = self._write_csv("semi.csv", "key;year\nA;2020\n")
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            blm.read_rows(p)
        self.assertIn("semicolon", err.getvalue())

    def test_pipe_in_header_and_carriage_return_escaped(self):
        table = blm.to_markdown_table(["in|out"], [{"in|out": "a\r\nb"}])
        self.assertEqual(table.splitlines()[0], "| in\\|out |")
        self.assertEqual(table.splitlines()[2], "| a  b |")


if __name__ == "__main__":
    unittest.main()
