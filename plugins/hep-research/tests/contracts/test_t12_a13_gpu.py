"""T12 stage 5: A13, the T10 destriper's baseline solve on the GPU against the CPU recipe (T12-16, T12-22; plan v9.2 A13, R30, Section 10.4,
Section 14.2).

Every expectation is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 5": G1-G8, the A13 comparison, T12-22) before
this file was written. The module needs PyTorch and is skipped as a whole without it (the required units skip it; the torch-cpu extra and
the venv run it); the CUDA cases are skipped without a CUDA device. Fixtures are synthetic; no quality claim.

Run from the plugin root with the venv's interpreter: python -m unittest tests.contracts.test_t12_a13_gpu -v
"""
from __future__ import annotations

import copy
import io
import json
import math
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    import torch
except ImportError:  # the required units have no PyTorch: the whole module is skipped (tools/optional_modules.json, torch-cpu)
    torch = None

if torch is not None:
    from tests.contracts import t12_a13_gpu as a13  # noqa: E402
    from tests.contracts import t12_comparators as cmp  # noqa: E402

CUDA = torch is not None and torch.cuda.is_available()
DESTRIPER = "reco.scan.destriper/1"


def frozen(variant: str = "noisy") -> dict:
    return a13.timestream_for(f"frozen-{variant}")


@unittest.skipIf(torch is None, "PyTorch not installed (the required units); the torch-backend job and the torch-cpu extra run this module")
class Subchain(unittest.TestCase):
    """G1-G7 on the CPU device: the same algorithm, the recipe's reader and writer, the stage 4 comparator."""

    @classmethod
    def setUpClass(cls):
        cls.noisy = frozen("noisy")
        cls.reference = cmp.solve_destriper(cls.noisy, product_id="a13-cpu-recipe")
        cls.solution = a13.torch_solve(a13.read_stream(cls.noisy), stopping=1e-10, device="cpu")
        cls.product = a13.build_product(a13.read_stream(cls.noisy), cls.solution, "a13-torch-cpu", a13.input_sha256(cls.noisy))

    def test_g1_the_product_is_the_recipes_format_and_passes_the_stage4_comparator(self):
        a13.destripe_product.read(copy.deepcopy(self.product), cmp.DESTRIPER_ASSETS)
        sidecar = a13.read_sidecar(self.product["reconstruction_product"])
        self.assertTrue(sidecar.ok, [finding.code for finding in sidecar.errors])
        result = cmp.compare_numerical(DESTRIPER, self.reference, self.product)
        self.assertEqual(result["status"], "passed", result["failed"])
        self.assertEqual(result["ruling"], "OI-8")
        self.assertEqual(result["tolerance"]["sha256"], "217a38bc40769da9c750ac347228b120476008b0227f025f4fcbc02ce9d3c35e")
        # test bounds on readings (the probe read 2.4e-16 and 1.7e-16), not tolerances
        self.assertLess(result["readings"]["baselines_relative"], 1e-12)
        self.assertLess(result["readings"]["map_relative"], 1e-12)

    def test_g1_iterations_and_residual_follow_the_recipe(self):
        self.assertEqual(self.solution.iterations, self.reference["solver"]["iterations"])     # fix round 1, I1: exact
        self.assertLessEqual(self.solution.relative_residual, 1e-10)
        self.assertEqual(self.solution.max_iterations, 10 * 32)
        self.assertEqual(self.product["solver"]["stopping"], 1e-10)
        self.assertEqual(self.solution.dtype, "float64")
        self.assertEqual(self.solution.device, "cpu")

    def test_g1_the_a13_comparison_on_the_frozen_pointing(self):
        result = a13.a13_compare("frozen-noisy", self.reference, self.product)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["form"], "numerical")
        self.assertEqual(result["size"], "frozen-noisy")

    def test_g2_noiseless_at_1e13(self):
        noiseless = frozen("noiseless")
        reference = cmp.solve_destriper(noiseless, product_id="a13-cpu-recipe", stopping=1e-13)
        solution = a13.torch_solve(a13.read_stream(noiseless), stopping=1e-13, device="cpu")
        product = a13.build_product(a13.read_stream(noiseless), solution, "a13-torch-cpu", a13.input_sha256(noiseless))
        result = a13.a13_compare("frozen-noiseless", reference, product)
        self.assertEqual(result["status"], "passed", result.get("failed"))
        self.assertEqual(result["tolerance"]["sha256"], "12738ebce579ae83057b69d8dca56cd3a626d5c5afe323863a56275de16da698")
        self.assertEqual(solution.iterations, reference["solver"]["iterations"])

    def test_g3_the_budget_raises_the_recipes_not_converged_on_both_paths(self):
        stream = a13.read_stream(self.noisy)
        with self.assertRaises(a13.destripe_solver.NotConverged) as cpu:
            a13.destripe_solver.solve(stream, stopping=1e-10, max_iterations=3)
        with self.assertRaises(a13.destripe_solver.NotConverged) as gpu_path:
            a13.torch_solve(stream, stopping=1e-10, max_iterations=3, device="cpu")
        self.assertEqual(cpu.exception.iterations, 3)
        self.assertEqual(gpu_path.exception.iterations, 3)

    def test_g3_a_product_above_its_stopping_value_is_refused_by_the_recipes_reader(self):
        planted = copy.deepcopy(self.product)
        planted["solver"]["relative_residual"] = 2e-10
        with self.assertRaises(a13.destripe_product.ProductError):
            a13.destripe_product.read(planted, cmp.DESTRIPER_ASSETS)

    def test_g4_a_scan_the_recipe_refuses_is_refused_before_any_device_work(self):
        disconnected = a13.t10_fixture.generate("disconnected", 20260)[0]
        with self.assertRaises(a13.destripe_timestream.Refusal):
            a13.read_stream(disconnected)
        unobserved = copy.deepcopy(self.noisy)
        unobserved["pixels"] += 1
        with self.assertRaises(a13.destripe_timestream.Refusal):
            a13.read_stream(unobserved)

    @unittest.skipIf(CUDA, "a CUDA device is present: the no-device case cannot be shown here")
    def test_g5_cuda_without_a_device_is_unavailable_never_a_cpu_run(self):
        with self.assertRaises(a13.DeviceUnavailable):
            a13.torch_solve(a13.read_stream(self.noisy), stopping=1e-10, device="cuda")

    def test_g5_an_unknown_device_or_precision_is_rejected(self):
        with self.assertRaises(a13.DeviceUnavailable):
            a13.torch_solve(a13.read_stream(self.noisy), stopping=1e-10, device="tpu")
        with self.assertRaises(a13.PrecisionError):
            a13.torch_solve(a13.read_stream(self.noisy), stopping=1e-10, device="cpu", dtype="float16")

    def test_g6_float32_is_a_reading_only(self):
        stream = a13.read_stream(self.noisy)
        reading = a13.float32_reading(stream, stopping=1e-10, device="cpu")
        self.assertEqual(reading["dtype"], "float32")
        self.assertIn(reading["outcome"], ("not-converged", "converged"))
        self.assertNotIn("status", reading)          # never a comparator verdict
        solution = a13.torch_solve(stream, stopping=1e-5, device="cpu", dtype="float32")
        with self.assertRaises(a13.PrecisionError):
            a13.build_product(stream, solution, "a13-float32", a13.input_sha256(self.noisy))

    def test_g7_products_of_different_inputs_are_rejected(self):
        other = cmp.solve_destriper(cmp.permute_baselines(self.noisy), product_id="a13-cpu-recipe")
        with self.assertRaises(cmp.ComparatorInputError):
            a13.a13_compare("frozen-noisy", other, self.product)


@unittest.skipIf(torch is None, "PyTorch not installed")
class Transcription(unittest.TestCase):
    """Fix round 1, I1: the transcription pinned step by step against the recipe (destripe_recipe.solver.solve), not only at the end."""

    CASES = (("frozen noisy", lambda: frozen("noisy"), 1e-10), ("frozen noiseless", lambda: frozen("noiseless"), 1e-13),
             ("a 2,048-sample scan", lambda: a13.scan_timestream(64, 128, 16, 5), 1e-10))

    def test_the_trajectory_iteration_by_iteration(self):
        """For every budget k = 1 .. n-1 both paths stop with the recipe's NotConverged after k iterations, at the same recomputed
        residual within 1e-6 relative (the two differ only in the order of the additions)."""
        for name, make, stopping in self.CASES:
            stream = a13.read_stream(make())
            converged = a13.destripe_solver.solve(stream, stopping=stopping)
            self.assertEqual(a13.torch_solve(stream, stopping=stopping, device="cpu").iterations, converged.iterations, name)
            for k in range(1, converged.iterations):
                with self.assertRaises(a13.destripe_solver.NotConverged) as cpu:
                    a13.destripe_solver.solve(stream, stopping=stopping, max_iterations=k)
                with self.assertRaises(a13.destripe_solver.NotConverged) as gpu_path:
                    a13.torch_solve(stream, stopping=stopping, max_iterations=k, device="cpu")
                self.assertEqual((cpu.exception.iterations, gpu_path.exception.iterations), (k, k), (name, k))
                self.assertLessEqual(abs(gpu_path.exception.relative_residual - cpu.exception.relative_residual),
                                     1e-6 * cpu.exception.relative_residual, (name, k))

    def test_the_reported_residual_is_the_recomputed_one(self):
        """The stopping test reads the recomputed residual ||Pi (F^T Z y - D a)|| / ||Pi F^T Z y||, recomputed here with the recipe's
        own NumPy operators from the baselines the subchain returns."""
        for name, make, stopping in self.CASES:
            stream = a13.read_stream(make())
            solution = a13.torch_solve(stream, stopping=stopping, device="cpu")
            solver = a13.destripe_solver
            right = solver._zero_sum(solver._sum_baselines(stream, solver._project_out_sky(stream, stream.value)))
            found = math.sqrt(float(((solver._zero_sum(right - solver.reduced_operator(stream, solution.baselines))) ** 2).sum()))
            found /= math.sqrt(float((right ** 2).sum()))
            # Carried minor (stage 5 re-review): the old absolute floor of 1e-13 made this check nearly vacuous for the frozen pointings,
            # whose stopping values (1e-10, 1e-13) end at the rounding floor (both residuals about 2e-16; u kappa about 1e-15 to 1e-14;
            # there the two summation orders differ by about 20 % relative). Now: (a) the recomputed residual itself meets the stopping
            # value, an independent check of convergence; (b) above 1e-12, where the stopping value leaves the residual well above the
            # rounding floor (the 2,048-sample scan ends near 1.3e-11), a purely relative 1e-6 agreement; (c) at the rounding floor, an
            # absolute 1e-14 (u kappa's upper end), not 1e-13. The iteration trajectory test covers the frozen pointings step by step.
            self.assertLessEqual(found, stopping, name)
            if found > 1e-12:
                self.assertLessEqual(abs(found - solution.relative_residual), 1e-6 * found, name)
            else:
                self.assertLessEqual(abs(found - solution.relative_residual), 1e-14, name)

    def test_the_restart_branch_is_reached_alike(self):
        """Stopping 1e-17 on the frozen pointing lies below the rounding floor: the recurrence collapses and both paths restart (the
        recipe's restarts counted from its _zero_sum calls: 1 + 5 per step + 2 per restart) before the budget of 150 ends them."""
        stream = a13.read_stream(frozen("noisy"))
        calls = []
        original = a13.destripe_solver._zero_sum
        with mock.patch.object(a13.destripe_solver, "_zero_sum", side_effect=lambda v: calls.append(1) or original(v)):
            with self.assertRaises(a13.destripe_solver.NotConverged) as cpu:
                a13.destripe_solver.solve(stream, stopping=1e-17, max_iterations=150)
        recipe_restarts = (5 * cpu.exception.iterations + 1 - len(calls)) // 3
        probe = {}
        with self.assertRaises(a13.destripe_solver.NotConverged) as gpu_path:
            a13.torch_solve(stream, stopping=1e-17, max_iterations=150, device="cpu", probe=probe)
        self.assertEqual((cpu.exception.iterations, gpu_path.exception.iterations), (150, 150))
        self.assertGreaterEqual(len(probe["restarts"]), 1)
        self.assertEqual(len(probe["restarts"]), recipe_restarts)
        self.assertLess(gpu_path.exception.relative_residual, 1e-14)

    def test_every_projection_removes_the_null_mode(self):
        """Fault injection: c times the ones vector (D's null vector) put into the start of a, the start of the direction and every
        application of D. The projections of a, direction, residual and image remove it, so the solution is unchanged and every kept
        vector stays zero-sum."""
        stream = a13.read_stream(frozen("noisy"))
        clean = a13.torch_solve(stream, stopping=1e-10, device="cpu")
        for offset in (1.0, 37.5):
            probe = {"offset": offset}
            found = a13.torch_solve(stream, stopping=1e-10, device="cpu", probe=probe)
            norm = float((clean.baselines ** 2).sum()) ** 0.5
            self.assertEqual(found.iterations, clean.iterations, offset)
            self.assertLess(float(((found.baselines - clean.baselines) ** 2).sum()) ** 0.5 / norm, 1e-12, offset)
            self.assertLess(float(((found.map - clean.map) ** 2).sum()) ** 0.5 / norm, 1e-12, offset)
            # a removed projection leaves a mean of order 1e-1 to 1 relative (the injected c against |r_0|); the projections leave rounding of
            # c against a late, small vector (login: 5e-11 at c = 37.5)
            self.assertLess(max(probe["means"]), 1e-8, offset)

    def test_m1_a_zero_right_side_is_the_recipes_answer(self):
        """Fix round 1, M1: data with no baseline signal (every sample its pixel's value): 0 iterations, residual 0.0, as the recipe."""
        document, truth = a13.t10_fixture.generate("noiseless", 20260)
        document = copy.deepcopy(document)
        document["value"] = [float(truth["map"][p]) for p in document["pixel"]]
        stream = a13.read_stream(document)
        recipe = a13.destripe_solver.solve(stream, stopping=1e-10)
        found = a13.torch_solve(stream, stopping=1e-10, device="cpu")
        self.assertEqual((recipe.iterations, recipe.relative_residual), (0, 0.0))
        self.assertEqual((found.iterations, found.relative_residual), (0, 0.0))
        self.assertEqual(list(found.baselines), [0.0] * 32)
        self.assertEqual(list(found.map), [float(v) for v in recipe.map])


@unittest.skipIf(torch is None, "PyTorch not installed")
class LargerSizes(unittest.TestCase):
    """The generator at scale, OI-12 (no frozen tolerance off the record's pointing) and OI-13 (no product of a larger scan)."""

    def test_the_declared_sizes(self):
        self.assertEqual(set(a13.SIZES), {"frozen-noisy", "frozen-noiseless", "scan-1m", "scan-16m"})
        self.assertEqual(a13.SIZES["scan-1m"]["samples"], 1048576)
        self.assertEqual(a13.SIZES["scan-16m"]["samples"], 16777216)
        self.assertEqual(a13.SIZES["frozen-noiseless"]["stopping"], 1e-13)

    def test_the_generator_is_deterministic_connected_and_the_recipes_format(self):
        first = a13.scan_timestream(64, 128, 16, 5)
        self.assertEqual(first, a13.scan_timestream(64, 128, 16, 5))
        self.assertNotEqual(first["value"], a13.scan_timestream(64, 128, 16, 6)["value"])
        stream = a13.read_stream(first)          # the recipe's reader: every pixel observed, one component
        self.assertEqual((stream.pixels, stream.baselines, stream.length), (64, 128, 16))

    def test_a_larger_size_is_incomplete_never_passed(self):
        document = a13.scan_timestream(64, 128, 16, 5)
        stream = a13.read_stream(document)
        cpu = a13.destripe_solver.solve(stream, stopping=1e-10)
        gpu = a13.torch_solve(stream, stopping=1e-10, device="cpu")
        result = a13.compare_in_memory("scan-1m", cpu, gpu)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["open_item"], "OI-12")
        self.assertIn("OI-13", result["also"])
        self.assertLess(result["readings"]["baselines_relative"], 1e-12)
        self.assertEqual(result["readings"]["iterations"], [cpu.iterations, gpu.iterations])

    def test_a_frozen_size_is_never_compared_in_memory(self):
        stream = a13.read_stream(frozen())
        cpu = a13.destripe_solver.solve(stream, stopping=1e-10)
        with self.assertRaises(cmp.ComparatorInputError):
            a13.compare_in_memory("frozen-noisy", cpu, cpu)

    def test_the_stage4_comparator_rejects_another_pointing(self):
        document = a13.scan_timestream(16, 32, 8, 5)
        reference = cmp.solve_destriper(document, product_id="a13-cpu-recipe")
        with self.assertRaises(cmp.ComparatorInputError):
            cmp.compare_numerical(DESTRIPER, reference, reference)


@unittest.skipIf(torch is None, "PyTorch not installed")
class QualityBeforeSpeed(unittest.TestCase):
    """Timings sealed to a run; released only against the harness's own quality record of that run, and only when it passed."""

    @classmethod
    def setUpClass(cls):
        cls.noisy = frozen("noisy")
        cls.reference = cmp.solve_destriper(cls.noisy, product_id="a13-cpu-recipe")
        stream = a13.read_stream(cls.noisy)
        cls.product = a13.build_product(stream, a13.torch_solve(stream, stopping=1e-10, device="cpu"), "a13-torch-cpu",
                                        a13.input_sha256(cls.noisy))

    def sealed(self):
        timings = a13.bench.SealedTimings("a13 frozen-noisy cpu")
        timings.record("compute", 0.25)
        return timings

    def test_a_passed_gate_releases_its_own_timings(self):
        timings = self.sealed()
        record = a13.gate("frozen-noisy", timings, self.reference, self.product)
        self.assertEqual(record.status, "passed")
        self.assertEqual(timings.release(record)["compute"], [0.25])

    def test_no_release_before_the_gate_or_from_a_forged_record(self):
        timings = self.sealed()
        with self.assertRaises(a13.bench.Withheld):
            timings.release({"status": "passed", "owner": timings})
        genuine = a13.gate("frozen-noisy", self.sealed(), self.reference, self.product)
        with self.assertRaises(a13.bench.Withheld):
            timings.release(copy.copy(genuine))
        with self.assertRaises(a13.bench.Withheld):     # another run's record
            timings.release(genuine)

    def test_a_failed_gate_withholds(self):
        planted = cmp.plant_baselines(self.product, 1e-6)
        timings = self.sealed()
        record = a13.gate("frozen-noisy", timings, self.reference, planted)
        self.assertEqual(record.status, "failed")
        with self.assertRaises(a13.bench.Withheld):
            timings.release(record)

    def test_an_incomplete_answer_withholds(self):
        document = a13.scan_timestream(64, 128, 16, 5)
        stream = a13.read_stream(document)
        cpu = a13.destripe_solver.solve(stream, stopping=1e-10)
        gpu = a13.torch_solve(stream, stopping=1e-10, device="cpu")
        timings = self.sealed()
        record = a13.gate_in_memory("scan-1m", timings, cpu, gpu)
        self.assertEqual(record.status, "incomplete")
        with self.assertRaises(a13.bench.Withheld):
            timings.release(record)
        self.assertIn("OI-12", timings.withheld_reason(record))


@unittest.skipIf(torch is None, "PyTorch not installed")
class ExecutionFields(unittest.TestCase):
    """T12-22: execution fields for the GPU subchain only; the CPU recipe's command line gets none."""

    GPU_KEYS = {"layout", "residence", "ownership", "async_completion", "transfer_edges", "zero_copy", "precision", "batch", "memory_limits",
                "streaming_queues"}

    def test_the_gpu_subchain_has_every_field(self):
        fields = a13.execution_fields("gpu-subchain")
        self.assertEqual(set(fields), self.GPU_KEYS | {"backend"})
        self.assertEqual(fields["precision"]["compared"], "float64")
        self.assertEqual(fields["transfer_edges"]["host_to_device_bytes_per_sample"], 16)
        self.assertEqual(fields["transfer_edges"]["scalars_per_iteration"], 4)
        self.assertIn("not applicable", fields["streaming_queues"])
        self.assertIn("not claimed", fields["zero_copy"])

    def test_the_cpu_recipe_gets_no_gpu_field(self):
        fields = a13.execution_fields("cpu-recipe")
        self.assertEqual(fields, {"backend": "cpu-recipe"})
        with self.assertRaises(ValueError):
            a13.execution_fields("other")

    def test_measured_transfers_are_counted(self):
        solution = a13.torch_solve(a13.read_stream(frozen()), stopping=1e-10, device="cpu")
        self.assertEqual(solution.transfers["host_to_device_bytes"], 256 * 16)
        self.assertEqual(solution.transfers["device_to_host_bytes"], (16 + 32) * 8)
        self.assertEqual(solution.transfers["scalars"], 1 + 4 * solution.iterations)
        self.assertEqual(set(solution.timings), {"host_to_device", "compute", "device_to_host"})


@unittest.skipIf(torch is None, "PyTorch not installed")
class CommandLine(unittest.TestCase):
    """t12_a13_gpu.py run: one process, one repetition record; exit 0 passed, 1 failed, 2 rejected, 3 incomplete."""

    def run_cli(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = a13.main(argv)
        return code, json.loads(out.getvalue().strip().splitlines()[-1])

    def test_a_frozen_run_on_cpu_passes_and_releases(self):
        noisy = frozen("noisy")
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch)
            source = folder / "noisy.timestream.json"
            source.write_bytes(a13.dumps_timestream(noisy))
            reference = folder / "reference.product.json"
            reference.write_bytes(cmp.dumps_product(cmp.solve_destriper(noisy, product_id="a13-cpu-recipe")))
            code, summary = self.run_cli(["run", "--size", "frozen-noisy", "--device", "cpu", "--timestream", str(source), "--reference",
                                          str(reference), "--warm", "2", "--out", str(folder / "run")])
            self.assertEqual((code, summary["status"]), (0, "passed"), summary)
            record = json.loads((folder / "run" / "run.json").read_text())
            self.assertEqual(record["quality"]["status"], "passed")
            self.assertEqual(set(record["released"]), {"process_to_import", "device_init", "reading", "host_to_device", "compute_first",
                                                       "compute_warm", "device_to_host", "checks"})
            self.assertEqual(len(record["released"]["compute_warm"]), 2)
            self.assertEqual(record["denominators"], {"attempted": 1, "succeeded": 1, "failed": {}})
            self.assertEqual(record["execution_fields"]["backend"], "gpu-subchain")
            self.assertFalse((folder / "run" / "sealed-timings.json").exists())
            self.assertTrue((folder / "run" / "gpu.product.json").is_file())
            # the run never overwrites its folder
            code, summary = self.run_cli(["run", "--size", "frozen-noisy", "--device", "cpu", "--timestream", str(source), "--reference",
                                          str(reference), "--out", str(folder / "run")])
            self.assertEqual((code, summary["status"]), (2, "rejected"))

    def test_another_pointing_is_incomplete_and_its_timings_sealed(self):
        """--size custom: any pointing but the record's (a larger scan's in the jobs); the CPU side is the recipe's solver in process."""
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch)
            source = folder / "small.timestream.json"
            source.write_bytes(a13.dumps_timestream(a13.scan_timestream(64, 128, 16, 5)))
            code, summary = self.run_cli(["run", "--size", "custom", "--device", "cpu", "--timestream", str(source), "--out", str(folder / "run")])
            self.assertEqual((code, summary["status"], summary["open_item"]), (3, "incomplete", "OI-12"))
            record = json.loads((folder / "run" / "run.json").read_text())
            self.assertEqual(record["released"], {})
            sealed = json.loads((folder / "run" / "sealed-timings.json").read_text())
            self.assertIn("withheld", sealed["label"])
            self.assertEqual(record["denominators"]["succeeded"], 0)
            self.assertEqual(record["denominators"]["failed"], {"incomplete": 1})

    def test_m2_the_checks_exclude_the_cpu_recipes_solve(self):
        """Fix round 1, M2: on another pointing the CPU recipe's solve is timed apart (cpu_side), never inside the GPU run's checks."""
        original = a13.destripe_solver.solve

        def slow(*args, **kwargs):
            time.sleep(0.5)
            return original(*args, **kwargs)
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch)
            source = folder / "small.timestream.json"
            source.write_bytes(a13.dumps_timestream(a13.scan_timestream(64, 128, 16, 5)))
            with mock.patch.object(a13.destripe_solver, "solve", side_effect=slow):
                code, summary = self.run_cli(["run", "--size", "custom", "--device", "cpu", "--timestream", str(source), "--out", str(folder / "run")])
            self.assertEqual(code, 3)
            sealed = json.loads((folder / "run" / "sealed-timings.json").read_text())
            self.assertLess(sealed["values"]["checks"][0], 0.4)
            self.assertGreaterEqual(json.loads((folder / "run" / "run.json").read_text())["cpu_side"]["released"]["compute"][0], 0.5)

    def test_a_timestream_of_another_shape_than_the_size_is_rejected(self):
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch)
            source = folder / "small.timestream.json"
            source.write_bytes(a13.dumps_timestream(a13.scan_timestream(64, 128, 16, 5)))
            code, summary = self.run_cli(["run", "--size", "scan-1m", "--device", "cpu", "--timestream", str(source), "--out", str(folder / "run")])
            self.assertEqual((code, summary["status"]), (2, "rejected"))

    def test_a_frozen_run_needs_its_reference_product(self):
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch)
            source = folder / "noisy.timestream.json"
            source.write_bytes(a13.dumps_timestream(frozen("noisy")))
            code, summary = self.run_cli(["run", "--size", "frozen-noisy", "--device", "cpu", "--timestream", str(source), "--out", str(folder / "run")])
            self.assertEqual((code, summary["status"]), (2, "rejected"))

    @unittest.skipIf(CUDA, "a CUDA device is present")
    def test_cuda_without_a_device_is_incomplete_exit_3(self):
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch)
            source = folder / "noisy.timestream.json"
            source.write_bytes(a13.dumps_timestream(frozen("noisy")))
            reference = folder / "reference.product.json"
            reference.write_bytes(cmp.dumps_product(cmp.solve_destriper(frozen("noisy"), product_id="a13-cpu-recipe")))
            code, summary = self.run_cli(["run", "--size", "frozen-noisy", "--device", "cuda", "--timestream", str(source), "--reference",
                                          str(reference), "--out", str(folder / "run")])
            self.assertEqual((code, summary["status"]), (3, "incomplete"))
            record = json.loads((folder / "run" / "run.json").read_text())
            self.assertEqual(record["denominators"]["failed"], {"device-unavailable": 1})

    def test_write_frozen_writes_the_fixture_file(self):
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch) / "f.json"
            code, summary = self.run_cli(["write", "--size", "frozen-noisy", "--out", str(target)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(target.read_text()), frozen("noisy"))
            self.assertEqual(summary["sha256"], a13.input_sha256(frozen("noisy")))


@unittest.skipUnless(CUDA, "no CUDA device (G8 runs in the B6000 jobs)")
class OnTheDevice(unittest.TestCase):
    """G8: the frozen sizes on CUDA pass the stage 4 comparator against the CPU recipe."""

    def test_g8_frozen_sizes_pass_on_cuda(self):
        for variant, stopping in (("noisy", 1e-10), ("noiseless", 1e-13)):
            document = frozen(variant)
            reference = cmp.solve_destriper(document, product_id="a13-cpu-recipe", stopping=stopping)
            stream = a13.read_stream(document)
            solution = a13.torch_solve(stream, stopping=stopping, device="cuda")
            self.assertEqual(solution.device, "cuda")
            product = a13.build_product(stream, solution, "a13-cuda", a13.input_sha256(document))
            self.assertEqual(a13.a13_compare(f"frozen-{variant}", reference, product)["status"], "passed", variant)


if __name__ == "__main__":
    unittest.main()
