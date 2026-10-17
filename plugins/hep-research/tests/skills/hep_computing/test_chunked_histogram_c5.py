"""C5: assets/chunked_histogram.py, a weighted histogram accumulated chunk by chunk. Oracle: chunked processing
equals one pass bit for bit (each bin sum is exact, so the chunking cannot change the rounding), for CSV (standard
library), ROOT trees through uproot.iterate (E2 venv) and Parquet through pyarrow (when installed). A missing
backend exits 3; a missing column is bad input. All inputs are SYNTHETIC."""
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
ASSET = PLUGIN / "skills" / "hep-computing" / "assets" / "chunked_histogram.py"
REF = PLUGIN / "skills" / "hep-computing" / "references" / "columnar-and-large-scale-data.md"
EDGES = ["0", "1", "2", "5", "10"]


def run(*args, env=None):
    p = subprocess.run([sys.executable, "-B", str(ASSET), *map(str, args)], capture_output=True, text=True,
                       timeout=600, env=env)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else None), p.stderr


def rows(n=5000, seed=3):
    rng = random.Random(seed)
    return [(rng.expovariate(0.3) - 0.5, rng.uniform(0.1, 3.0) * (1e-3 if i % 7 == 0 else 1.0)) for i in range(n)]


class CsvChunks(unittest.TestCase):
    def test_chunked_equals_one_pass_bit_for_bit(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ev.csv"
            f.write_text("x,w\n" + "".join(f"{x!r},{w!r}\n" for x, w in rows()), encoding="utf-8")
            common = ["--source", "csv", "--column", "x", "--weight", "w", "--edges", *EDGES]
            code1, one, err1 = run(f, *common, "--chunk-size", "0")
            code2, many, err2 = run(f, *common, "--chunk-size", "333")
        self.assertEqual((code1, code2), (0, 0), (err1, err2))
        self.assertEqual(one["chunks"], 1)
        self.assertGreater(many["chunks"], 10)
        self.assertEqual(json.dumps(one["values"]), json.dumps(many["values"]))
        self.assertEqual(json.dumps(one["sumw2"]), json.dumps(many["sumw2"]))
        self.assertEqual(one["n_rows"], 5000)
        self.assertEqual(one["status"], "ok")
        self.assertEqual(one["status_label"], "unvalidated")
        # flow bins: values has len(edges) + 1 entries (underflow first, overflow last)
        self.assertEqual(len(one["values"]), len(EDGES) + 1)
        self.assertGreater(one["values"][0], 0)

    def test_missing_column_is_bad_input(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ev.csv"
            f.write_text("x,w\n1,1\n", encoding="utf-8")
            code, out, _ = run(f, "--source", "csv", "--column", "y", "--edges", *EDGES)
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")


class RootChunks(unittest.TestCase):
    def setUp(self):
        try:
            import numpy  # noqa: F401
            import uproot  # noqa: F401
        except ImportError:
            self.skipTest("uproot is not installed (optional extra root-uproot)")

    def test_uproot_iterate_equals_one_pass(self):
        import numpy as np
        import uproot
        data = rows()
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ev.root"
            with uproot.recreate(f) as out:
                out["t"] = {"x": np.array([x for x, _ in data]), "w": np.array([w for _, w in data])}
            common = ["--source", "root", "--tree", "t", "--column", "x", "--weight", "w", "--edges", *EDGES]
            code1, one, e1 = run(f, *common, "--chunk-size", "0")
            code2, many, e2 = run(f, *common, "--chunk-size", "700")
        self.assertEqual((code1, code2), (0, 0), (e1, e2))
        self.assertGreater(many["chunks"], 5)
        self.assertEqual(json.dumps(one["values"]), json.dumps(many["values"]))


class ParquetChunks(unittest.TestCase):
    def setUp(self):
        try:
            import pyarrow  # noqa: F401
            import pyarrow.parquet  # noqa: F401
        except ImportError:
            self.skipTest("pyarrow is not installed (optional extra columnar)")

    def test_iter_batches_equals_one_pass(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        data = rows()
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ev.parquet"
            pq.write_table(pa.table({"x": [x for x, _ in data], "w": [w for _, w in data]}), f, row_group_size=500)
            common = ["--source", "parquet", "--column", "x", "--weight", "w", "--edges", *EDGES]
            code1, one, e1 = run(f, *common, "--chunk-size", "0")
            code2, many, e2 = run(f, *common, "--chunk-size", "450")
        self.assertEqual((code1, code2), (0, 0), (e1, e2))
        self.assertGreater(many["chunks"], 5)
        self.assertEqual(json.dumps(one["values"]), json.dumps(many["values"]))


class Missing(unittest.TestCase):
    def test_hidden_uproot_exits_3(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "uproot.py").write_text("raise ImportError('uproot hidden for this test')\n", encoding="utf-8")
            f = Path(d) / "x.root"
            f.write_bytes(b"x")
            env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
            code, out, _ = run(f, "--source", "root", "--tree", "t", "--column", "x", "--edges", *EDGES, env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "missing-dependency")


class Reference(unittest.TestCase):
    def test_reference_covers_the_card(self):
        text = REF.read_text(encoding="utf-8")
        for term in ("Parquet", "Arrow", "HDF5", "uproot.iterate", "Dask", "partition", "memory budget",
                     "root_to_parquet.py", "chunked_histogram.py"):
            with self.subTest(term=term):
                self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
