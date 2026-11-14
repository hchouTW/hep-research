"""T12 stage 5: T12-14, the CPU engineering benchmark (stage 4 part B; plan v9.2 Section 14.2), and the sealed timings it shares with A13.

Every expectation is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 5": C1-C8) before this file was written. The
tests run the recipes on the tracked block-1 examples and the destriper's synthetic fixture; numbers are records, not gates (K12); no
quality claim.

Run from the plugin root: python -m unittest tests.contracts.test_t12_benchmark -v
"""
from __future__ import annotations

import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.contracts import t12_benchmark as bench  # noqa: E402
from tests.contracts import t12_comparators as cmp  # noqa: E402

DESTRIPER, T08, T09 = "reco.scan.destriper/1", "reco.calo.cell-cluster/1", "reco.light.channel-likelihood/1"
T07 = "reco.track.acts-ckf-planar/1"
CALO = ROOT / "examples" / "reconstruction-calorimetry" / "recorded"
LIGHT = ROOT / "examples" / "reconstruction-photon-likelihood" / "recorded"


class Identity(unittest.TestCase):
    """C5: every recipe file pinned at d1f6fc30 (Freeze B's bytes, with the recorded post-D4 line in the two CLIs)."""

    def test_the_pinned_recipes_are_the_trees(self):
        for recipe in (DESTRIPER, T08, T09):
            found = bench.check_identity(recipe)
            self.assertEqual(found["recipe"], recipe)
            self.assertGreater(found["files"], 3)
        self.assertEqual(bench.RECIPE_FILES[T08]["adapters/calo-cluster/assets/calo_cluster.py"],
                         "4119bf47dfb68a33c0568c79a48be86b520fb36d03935547f94405680aaddf18")
        self.assertEqual(bench.RECIPE_FILES[T09]["adapters/photon-likelihood/assets/photon_likelihood.py"],
                         "532260bd261dff01aed4a2455ce391da7e365563a8ee4f68d1632b1088978608")

    def test_a_changed_byte_is_rejected(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for relative in bench.RECIPE_FILES[DESTRIPER]:
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, root / relative)
            self.assertEqual(bench.check_identity(DESTRIPER, root)["recipe"], DESTRIPER)
            target = root / "adapters/destriper/assets/destripe_recipe/solver.py"
            target.write_bytes(target.read_bytes() + b"\n")
            with self.assertRaises(bench.IdentityError):
                bench.check_identity(DESTRIPER, root)

    def test_an_unknown_recipe_is_rejected(self):
        with self.assertRaises(bench.IdentityError):
            bench.check_identity("reco.nothing/1")


class Release(unittest.TestCase):
    """C6: a recipe's timings are released only on its own quality record; T07 failed at attempt 1."""

    def test_the_quality_records(self):
        self.assertEqual(bench.QUALITY_RECORDS[DESTRIPER]["status"], "passed")
        self.assertIn("7596623", bench.QUALITY_RECORDS[DESTRIPER]["source"])
        self.assertIn("7620411", bench.QUALITY_RECORDS[T08]["source"])
        self.assertIn("7613459", bench.QUALITY_RECORDS[T09]["source"])
        self.assertEqual(bench.QUALITY_RECORDS[T07]["status"], "failed")

    def test_t07_is_never_released(self):
        timings = bench.SealedTimings("t07")
        timings.record("compute", 1.0)
        record = bench.gate_recipe(timings, T07)
        self.assertEqual(record.status, "failed")
        with self.assertRaises(bench.Withheld):
            timings.release(record)

    def test_a_recipe_record_releases_only_its_own_timings(self):
        mine, other = bench.SealedTimings("a"), bench.SealedTimings("b")
        mine.record("compute", 1.0)
        record = bench.gate_recipe(mine, T08)
        self.assertEqual(mine.release(record), {"compute": [1.0]})
        with self.assertRaises(bench.Withheld):
            other.release(record)
        with self.assertRaises(bench.Withheld):
            mine.release(copy.copy(record))

    def test_a_comparator_failure_overrides_the_recipe_record(self):
        timings = bench.SealedTimings("d")
        record = bench.gate_recipe(timings, DESTRIPER, comparator={"status": "failed", "failed": ["baselines"]})
        self.assertEqual(record.status, "failed")
        with self.assertRaises(bench.Withheld):
            timings.release(record)

    def test_the_not_measured_list(self):
        self.assertIn(T07, bench.NOT_MEASURED)
        self.assertIn("reco.timing.time-chain/1", bench.NOT_MEASURED)
        self.assertTrue(all(isinstance(reason, str) and reason for reason in bench.NOT_MEASURED.values()))


class SameWork(unittest.TestCase):
    """C2: the in-process product is byte-equal to the command line's."""

    def test_equal_and_different_bytes(self):
        self.assertEqual(bench.compare_same_work(b"abc", b"abc")["status"], "passed")
        found = bench.compare_same_work(b"abc", b"abd")
        self.assertEqual(found["status"], "failed")
        self.assertEqual(found["first_difference"], 2)


NEEDS_WAIT4 = unittest.skipUnless(bench.MEASURABLE, "needs os.wait4 (peak RSS per process; not on native Windows)")


class Measured(unittest.TestCase):
    @NEEDS_WAIT4
    def test_a_measured_process_has_wall_exit_and_peak_memory(self):
        found = bench.run_measured([sys.executable, "-c", "print('x')"])
        self.assertEqual(found["exit"], 0)
        self.assertGreater(found["wall"], 0.0)
        self.assertGreater(found["maxrss_kb"], 0)
        self.assertEqual(found["stdout"].strip(), "x")
        self.assertEqual(bench.run_measured([sys.executable, "-c", "raise SystemExit(4)"])["exit"], 4)

    def test_without_wait4_the_benchmark_is_incomplete_and_says_why(self):
        with mock.patch.object(bench, "MEASURABLE", False):
            with self.assertRaisesRegex(RuntimeError, "needs os.wait4"):
                bench.run_measured([sys.executable, "-c", "print('x')"])
            with tempfile.TemporaryDirectory() as scratch:
                source = Path(scratch) / "noisy.timestream.json"
                source.write_bytes((json.dumps(cmp.destriper_fixture(), sort_keys=True, separators=(",", ":")) + "\n").encode())
                out = io.StringIO()
                with redirect_stdout(out):
                    code = bench.main(["destriper", "--timestream", str(source), "--out", str(Path(scratch) / "run"), "--repetitions", "1"])
        self.assertEqual(code, 3, out.getvalue())
        self.assertEqual(json.loads(out.getvalue()), {"status": "incomplete", "reason": f"RuntimeError: {bench.NOT_MEASURABLE}"})

    def test_quantiles(self):
        found = bench.quantiles([float(v) for v in range(1, 101)])
        self.assertEqual(set(found), {"p50", "p90", "p99"})
        self.assertAlmostEqual(found["p50"], 50.5)


@NEEDS_WAIT4
class Destriper(unittest.TestCase):
    """C1, C2, C6, C8 on the frozen fixture; one repetition."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory()
        folder = Path(cls.scratch.name)
        cls.source = folder / "noisy.timestream.json"
        cls.source.write_bytes((json.dumps(cmp.destriper_fixture(), sort_keys=True, separators=(",", ":")) + "\n").encode())
        cls.record = bench.bench_destriper(cls.source, folder / "run", repetitions=1, stopping=1e-10)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def test_c1_components_apart_and_the_total_measured(self):
        record = self.record
        self.assertEqual(record["recipe"], DESTRIPER)
        self.assertEqual(set(record["released"]), {"initialization", "io", "reading", "compute", "output", "checks", "total_wall"})
        self.assertIn("conditions", record["not_applicable"])
        self.assertIn("no overlap", record["overlap"])
        self.assertIn("total_wall is the command line's own separate run", record["overlap"])   # fix round 1, M4
        self.assertEqual(record["workload"], {"samples": 256, "baselines": 32, "pixels": 16, "iterations": [15]})

    def test_c2_c6_same_work_comparator_and_release(self):
        self.assertEqual(self.record["same_work"][0]["status"], "passed")
        self.assertEqual(self.record["comparator"][0]["status"], "passed")
        self.assertEqual(self.record["quality"]["status"], "passed")
        self.assertEqual(self.record["denominators"], {"attempted": 1, "succeeded": 1, "failed": {}})
        self.assertIn("identity", self.record)

    def test_c8_a_rejected_input_is_a_failure_and_nothing_is_released(self):
        with tempfile.TemporaryDirectory() as scratch:
            bad = Path(scratch) / "bad.json"
            bad.write_text("{}\n")
            record = bench.bench_destriper(bad, Path(scratch) / "run", repetitions=1, stopping=1e-10)
            self.assertEqual(record["denominators"], {"attempted": 1, "succeeded": 0, "failed": {"rejected": 1}})
            self.assertEqual(record["released"], {})

    def test_c1_a_larger_scan_has_no_product_and_no_command_line_run(self):
        with tempfile.TemporaryDirectory() as scratch:
            source = Path(scratch) / "scan.json"
            source.write_bytes((json.dumps(bench.scan_timestream(64, 128, 16, 5), sort_keys=True, separators=(",", ":")) + "\n").encode())
            record = bench.bench_destriper(source, Path(scratch) / "run", repetitions=1, stopping=1e-10, product=False)
            self.assertEqual(set(record["released"]), {"initialization", "io", "reading", "compute", "total_wall"})
            self.assertIn("output", record["not_applicable"])
            self.assertIn("OI-13", record["not_applicable"]["output"])
            self.assertEqual(record["denominators"]["succeeded"], 1)


@NEEDS_WAIT4
class CaloCluster(unittest.TestCase):
    """C3 on the tracked block-1 example (2 events)."""

    def test_c3_components_same_work_and_release(self):
        with tempfile.TemporaryDirectory() as scratch:
            record = bench.bench_t08(CALO / "events.cells", CALO / "events.pedestal.json", CALO / "events.gain.json", Path(scratch) / "run",
                                     repetitions=1)
        self.assertEqual(record["recipe"], T08)
        self.assertEqual(set(record["released"]), {"initialization", "configuration", "io", "reading", "conditions", "conversion", "compute",
                                                   "output", "checks", "total_wall"})
        self.assertEqual(record["same_work"][0]["status"], "passed")
        self.assertEqual(record["workload"]["events"], 2)
        self.assertIn("check-product command line's wall", record["overlap"])      # fix round 1, M4
        self.assertEqual(set(record["latency"][0]), {"p50", "p90", "p99"})
        self.assertEqual(record["denominators"], {"attempted": 1, "succeeded": 1, "failed": {}})


@NEEDS_WAIT4
class PhotonLikelihood(unittest.TestCase):
    """C4 on the tracked block-1 example (2 events): command-line level, the inner components recorded as not separated."""

    def test_c4_command_lines_and_release(self):
        with tempfile.TemporaryDirectory() as scratch:
            record = bench.bench_t09(LIGHT / "main.readout", Path(scratch) / "run", repetitions=1)
        self.assertEqual(record["recipe"], T09)
        self.assertEqual(set(record["released"]), {"initialization", "fit_multistart", "check_multistart", "topology", "check_topology"})
        self.assertIn("reading", record["not_separated"])
        self.assertIn("own interpreter start", record["overlap"])                  # fix round 1, M4
        self.assertEqual(record["workload"]["events"], 2)
        self.assertEqual(record["denominators"], {"attempted": 1, "succeeded": 1, "failed": {}})


class CommandLine(unittest.TestCase):
    def test_not_measured_prints_the_list(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = bench.main(["not-measured"])
        self.assertEqual(code, 0)
        self.assertIn(T07, json.loads(out.getvalue())["not_measured"])

    @NEEDS_WAIT4
    def test_destriper_command_writes_bench_json_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch)
            source = folder / "noisy.timestream.json"
            source.write_bytes((json.dumps(cmp.destriper_fixture(), sort_keys=True, separators=(",", ":")) + "\n").encode())
            out = io.StringIO()
            with redirect_stdout(out):
                code = bench.main(["destriper", "--timestream", str(source), "--out", str(folder / "run"), "--repetitions", "1"])
            self.assertEqual(code, 0, out.getvalue())
            self.assertEqual(json.loads((folder / "run" / "bench.json").read_text())["quality"]["status"], "passed")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(bench.main(["destriper", "--timestream", str(source), "--out", str(folder / "run"), "--repetitions", "1"]), 2)


if __name__ == "__main__":
    unittest.main()
