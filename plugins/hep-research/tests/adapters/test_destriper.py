"""adapters/destriper, T10 replay stage 2 (docs/dev/detector-reconstruction/t10-replay-stage-plan.md, section 3): the timestream
reader, the conjugate-gradient destriper with the zero-sum baseline constraint, the product destriper-product/1 with its embedded
reconstruction:scan-v1 global block, the method card and the CLI. Hand-made systems of at most 8 baselines only; the fixture is run
in the stage 4 job.

Expectations S1-S11 are fixed in the stage plan. Reference values come from a second coding here: the joint KKT system in NumPy, a
different method from the recipe's reduced conjugate-gradient solve.
Run from the plugin root: python -m unittest tests.adapters.test_destriper -v
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "destriper"
ASSETS = ADAPTER / "assets"
CLI = ASSETS / "destriper.py"
CARD = ASSETS / "destriper.method-card.json"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS / "fixture_tools"))
sys.path.insert(0, str(ASSETS))

from destripe_recipe import DEFAULT_STOPPING, LABEL, RECIPE, product, solver, timestream  # noqa: E402
import t10_fixture  # noqa: E402
import t10_replay  # noqa: E402
from contracts.reconstruction import read_sidecar  # noqa: E402

PY = sys.executable


def hand_made(values=None, pixels=4, length=4, baselines=8, pointing=None) -> dict:
    """A small connected scan: baseline b sweeps pixels (b + j // 2) mod 4, j = 0..3 (two pixels, two samples each)."""
    pixel = pointing if pointing is not None else [(b + j // 2) % pixels for b in range(baselines) for j in range(length)]
    if values is None:
        sky = [3.0, -5.0, 7.0, 2.0]
        offsets = [1.0, -2.0, 4.0, -3.0, 2.0, -1.0, 3.0, -4.0]
        values = [sky[p] + offsets[t // length] for t, p in enumerate(pixel)]
    return {"format": "destriper-timestream/1", "role": "reconstruction-input", "unit": "artificial-unit", "pixels": pixels,
            "baseline_length": length, "noise_premise": "white", "pixel": list(pixel), "value": [float(v) for v in values]}


def noisy_values(document: dict, seed=7) -> list[float]:
    rng = numpy.random.default_rng(seed)
    return [v + float(n) for v, n in zip(document["value"], rng.normal(0, 1, len(document["value"])))]


def design(document: dict):
    pixel = numpy.array(document["pixel"])
    samples, length, pixels = pixel.size, document["baseline_length"], document["pixels"]
    A = numpy.zeros((samples, pixels + samples // length))
    A[numpy.arange(samples), pixel] = 1
    A[numpy.arange(samples), pixels + numpy.arange(samples) // length] = 1
    return A


def kkt_reference(document: dict):
    """Second coding: the zero-sum constrained least-squares solution from the joint KKT system (NumPy)."""
    A, y = design(document), numpy.array(document["value"])
    pixels, width = document["pixels"], A.shape[1]
    c = numpy.r_[numpy.zeros(pixels), numpy.ones(width - pixels)]
    K = numpy.block([[A.T @ A, c[:, None]], [c[None, :], numpy.zeros((1, 1))]])
    x = numpy.linalg.solve(K, numpy.r_[A.T @ y, 0.0])[:width]
    return x[:pixels], x[pixels:]


def numbers(document: dict):
    """kappa of the reduced operator on 1-perp, and G = ||M^-1 P^T F||_2, written here from the stage plan."""
    A = design(document)
    pixels = document["pixels"]
    P, F = A[:, :pixels], A[:, pixels:]
    M = P.T @ P
    Z = numpy.eye(len(A)) - P @ numpy.linalg.inv(M) @ P.T
    w = numpy.sort(numpy.linalg.eigvalsh(F.T @ Z @ F))
    return w[-1] / w[1], numpy.linalg.norm(numpy.linalg.inv(M) @ P.T @ F, 2)


def run(*args):
    proc = subprocess.run([PY, "-I", "-B", str(CLI), *map(str, args)], capture_output=True, text=True, timeout=120)
    return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else None, proc.stderr


def write_json(folder: Path, name: str, document) -> Path:
    path = folder / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


class ReaderTests(unittest.TestCase):
    """S1: malformed input is rejected (exit 2); an undetermined map is refused (exit 1); no product either way."""

    def test_s1_malformed_timestreams_are_rejected(self):
        good = hand_made()
        cases = {"format": dict(good, format="destriper-timestream/2"), "extra key": dict(good, seed=1),
                 "missing key": {k: v for k, v in good.items() if k != "unit"},
                 "length": dict(good, pixel=good["pixel"][:-1], value=good["value"][:-1]),
                 "pixel range": dict(good, pixel=[9] + good["pixel"][1:]), "pixel type": dict(good, pixel=[0.5] + good["pixel"][1:]),
                 "non-finite": dict(good, value=[float("nan")] + good["value"][1:]),
                 "lengths differ": dict(good, value=good["value"][:-4])}
        for name, document in cases.items():
            with self.subTest(case=name), self.assertRaises(timestream.InputError):
                timestream.read(document)
        with tempfile.TemporaryDirectory() as folder:
            path = write_json(Path(folder), "bad.json", cases["extra key"])
            code, out, _ = run("solve", "--timestream", path, "--product", Path(folder) / "p.json", "--product-id", "product.t")
            self.assertEqual((code, out["status"]), (2, "rejected"))
            self.assertFalse((Path(folder) / "p.json").exists())

    def test_s1_unobserved_pixel_and_disconnected_scan_are_refused(self):
        unobserved = hand_made(pointing=[(b + j // 2) % 3 for b in range(8) for j in range(4)])
        with self.assertRaises(timestream.Refusal) as caught:
            timestream.read(unobserved)
        self.assertIn("pixel 3", str(caught.exception))
        split = hand_made(pointing=[(b % 2) * 2 + (j // 2) for b in range(8) for j in range(4)])
        with self.assertRaises(timestream.Refusal) as caught:
            timestream.read(split)
        self.assertEqual(len(caught.exception.components), 2)
        self.assertIn("null mode", str(caught.exception))
        with tempfile.TemporaryDirectory() as folder:
            path = write_json(Path(folder), "split.json", split)
            code, out, _ = run("solve", "--timestream", path, "--product", Path(folder) / "p.json", "--product-id", "product.t")
            self.assertEqual((code, out["status"]), (1, "refused"))
            self.assertEqual(len(out["components"]), 2)
            self.assertFalse((Path(folder) / "p.json").exists())

    def test_s1_fixture_disconnected_variant_is_refused(self):
        document, _ = t10_fixture.generate("disconnected", 20260)
        with self.assertRaises(timestream.Refusal) as caught:
            timestream.read(document)
        self.assertEqual(sorted(len(part["pixels"]) for part in caught.exception.components), [8, 8])


class SolverTests(unittest.TestCase):
    def test_s2_consistent_system_gives_the_constrained_solution(self):
        document = hand_made()
        solution = solver.solve(timestream.read(document), stopping=1e-14)
        sky, offsets = kkt_reference(document)
        numpy.testing.assert_allclose(solution.map, sky, rtol=0, atol=1e-12)
        numpy.testing.assert_allclose(solution.baselines, offsets, rtol=0, atol=1e-12)

    def test_s3_noisy_system_within_the_stopping_bound(self):
        document = hand_made()
        document["value"] = noisy_values(document)
        eps = 1e-10
        solution = solver.solve(timestream.read(document), stopping=eps)
        sky, offsets = kkt_reference(document)
        kappa, gain = numbers(document)
        size = numpy.linalg.norm(offsets)
        self.assertLessEqual(numpy.linalg.norm(solution.baselines - offsets), 10 * kappa * eps * size)
        self.assertLessEqual(numpy.linalg.norm(solution.map - sky), 10 * gain * kappa * eps * size)

    def test_s4_recorded_residual_and_budget(self):
        document = hand_made()
        document["value"] = noisy_values(document)
        stream = timestream.read(document)
        solution = solver.solve(stream, stopping=1e-10)
        self.assertLessEqual(solution.iterations, 10 * stream.baselines)
        A, y = design(document), numpy.array(document["value"])
        pixels = document["pixels"]
        P, F = A[:, :pixels], A[:, pixels:]
        Z = numpy.eye(len(A)) - P @ numpy.linalg.inv(P.T @ P) @ P.T
        b = F.T @ Z @ y
        r = b - F.T @ Z @ F @ solution.baselines
        r -= r.mean()
        self.assertLessEqual(numpy.linalg.norm(r) / numpy.linalg.norm(b), 1e-10)
        self.assertAlmostEqual(solution.relative_residual, numpy.linalg.norm(r) / numpy.linalg.norm(b), delta=1e-12)
        with self.assertRaises(solver.NotConverged):
            solver.solve(stream, stopping=1e-10, max_iterations=1)
        # the iteration stops at the first iterate whose recomputed residual is at most eps, never one above it: eps is set below
        # the first iterate's residual (this hand-made system needs two), so that iterate is not accepted
        with self.assertRaises(solver.NotConverged) as caught:
            solver.solve(stream, stopping=1e-30, max_iterations=1)
        eps = caught.exception.relative_residual / 5
        stopped = solver.solve(stream, stopping=eps)
        self.assertLessEqual(stopped.relative_residual, eps)
        self.assertGreater(stopped.iterations, 1)
        # found in stage 3 (stage3-green-1.log): once the Krylov space is exhausted the recurrence residual is zero while the
        # recomputed one is still above a stopping value below rounding; the solver restarts, and then runs out of budget
        with self.assertRaises(solver.NotConverged):
            solver.solve(stream, stopping=1e-30)

    def test_s5_zero_sum_held_and_the_operator_has_the_offset_null_mode(self):
        document = hand_made()
        document["value"] = noisy_values(document)
        stream = timestream.read(document)
        solution = solver.solve(stream, stopping=1e-10)
        self.assertLessEqual(abs(solution.baselines.sum()), 1e-13 * numpy.abs(solution.baselines).sum())
        self.assertLessEqual(numpy.linalg.norm(solver.reduced_operator(stream, numpy.ones(stream.baselines))), 1e-12)


class ProductTests(unittest.TestCase):
    def build(self, constraint="zero-sum", noisy=True, stopping=1e-10):
        document = hand_made()
        if noisy:
            document["value"] = noisy_values(document)
        stream = timestream.read(document)
        solution = solver.solve(stream, stopping=stopping)
        return document, product.build(stream, solution, constraint=constraint, product_id="product.hand-made", input_sha256="0" * 64,
                                       card_path=CARD)

    def test_s6_constrained_product_passes_the_contract(self):
        document, built = self.build()
        scan_product = built["reconstruction_product"]
        report = read_sidecar(scan_product)
        self.assertTrue(report.ok, [f.as_dict() for f in report.errors])
        scan = scan_product["scan"]
        self.assertEqual(scan["subcase"], "global")
        self.assertEqual(scan["unidentifiable"], [])
        self.assertEqual(scan["constraint"]["weights"], [0] * 4 + [1] * 8)
        self.assertEqual(scan["constraint"]["value"], 0)
        self.assertTrue(scan["uniqueness_claim"])
        self.assertEqual((scan["regularization"], scan["merging"]["kind"]), ("none", "joint-model"))
        self.assertEqual(len(scan["reported"]), 12)
        self.assertEqual([item["value"] for item in scan["reported"]], built["map"] + built["baselines"])
        self.assertEqual(scan["model"]["design"], design(document).astype(int).tolist())
        self.assertIn("reconstruction:scan-v1", scan_product["required_extensions"])
        self.assertEqual((built["recipe"], built["label"]), (RECIPE, LABEL))
        self.assertIn("not native", LABEL)

    def test_s6_unconstrained_product_names_every_parameter(self):
        _, built = self.build(constraint="none")
        scan = built["reconstruction_product"]["scan"]
        report = read_sidecar(built["reconstruction_product"])
        self.assertTrue(report.ok, [f.as_dict() for f in report.errors])
        self.assertEqual(scan["unidentifiable"], scan["model"]["parameters"])
        self.assertIsNone(scan["constraint"])
        self.assertFalse(scan["uniqueness_claim"])
        self.assertEqual(len(scan["reported"]), 3 + 7 + 1)
        m, a = built["map"], built["baselines"]
        self.assertAlmostEqual(scan["reported"][-1]["value"], m[0] + a[0], delta=1e-12)

    def test_s7_negative_variants_on_the_solver_product_are_refused(self):
        for constraint in ("none", "zero-sum"):
            _, built = self.build(constraint=constraint)
            for name, (_, code) in t10_fixture.NEGATIVE_VARIANTS.items():
                with self.subTest(constraint=constraint, variant=name):
                    bad = t10_fixture.negative_variant(built["reconstruction_product"], name)
                    self.assertIn(code, {f.code for f in read_sidecar(bad).errors})

    def test_s7_the_contract_value_check_runs_on_a_noiseless_product(self):
        _, built = self.build(noisy=False, stopping=1e-14)
        self.assertTrue(read_sidecar(built["reconstruction_product"]).ok)
        moved = copy.deepcopy(built["reconstruction_product"])
        moved["scan"]["reported"][0]["value"] += 1e-6
        self.assertIn("reconstruction.scan.reported_mismatch", {f.code for f in read_sidecar(moved).errors})

    def test_s7_a_disconnected_design_claimed_determined_is_refused(self):
        bad = t10_replay.claimed_disconnected_product()
        codes = {f.code for f in read_sidecar(bad).errors}
        self.assertTrue({"reconstruction.scan.unidentifiable_unnamed", "reconstruction.scan.unique_claim"} <= codes, codes)

    def test_s8_method_card_names_the_mode_and_its_constraint(self):
        card = json.loads(CARD.read_text(encoding="utf-8"))
        self.assertEqual(card["format"], "method-card/1")
        self.assertEqual(card["recipe"], RECIPE)
        mode = card["unconstrained_modes"][0]
        self.assertEqual(set(mode), {"mode", "constrained_by", "constraining_data", "independent_observables", "precondition"})
        self.assertIn("m + c", mode["mode"])
        self.assertIn("zero-sum", mode["constrained_by"])
        self.assertIn("connected", mode["precondition"])
        self.assertIn("not a native backend", card["binding"])
        _, built = self.build()
        self.assertEqual(built["method_card"]["sha256"], hashlib.sha256(CARD.read_bytes()).hexdigest())

    def test_s9_data_side_imports_no_scoring_side_module(self):
        files = [CLI] + sorted((ASSETS / "destripe_recipe").rglob("*.py"))
        forbidden = {"t10_fixture", "t10_replay", "t10_exact_reference", "t10_comparator", "fixture_tools"}
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            names = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
            names |= {(node.module or "").split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
            self.assertFalse(names & forbidden, f"{path.name}: {names & forbidden}")
            self.assertNotIn("truth", path.read_text(encoding="utf-8").lower().replace("truth-reference", ""), path.name)


class NullModeDriftTests(unittest.TestCase):
    """S13: without the zero-sum projection, conjugate gradient leaves the offset where its start put it (the null mode)."""

    def test_s13_the_start_sets_the_offset_without_the_constraint(self):
        document = hand_made()
        document["value"] = noisy_values(document)
        drift = t10_replay.null_mode_drift(document, stopping=1e-10, offset=7.0)
        self.assertAlmostEqual(drift["mean_difference"], 7.0, delta=1e-9)
        self.assertLessEqual(drift["demeaned_difference_relative"], 1e-8)
        self.assertTrue(all(r <= 1e-10 for r in drift["relative_residuals"]))
        self.assertLessEqual(abs(drift["recipe_mean"]), 1e-13 * drift["recipe_sum_abs"])
        self.assertTrue(drift["passed"])


class CommandLineTests(unittest.TestCase):
    def test_s10_solve_and_check_product(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            document = hand_made()
            document["value"] = noisy_values(document)
            source = write_json(folder, "t.json", document)
            target = folder / "p.json"
            code, out, err = run("solve", "--timestream", source, "--product", target, "--product-id", "product.hand-made")
            self.assertEqual((code, out["status"]), (0, "written"), err)
            self.assertEqual(out["stopping"], DEFAULT_STOPPING)
            code, out, _ = run("solve", "--timestream", source, "--product", target, "--product-id", "product.hand-made")
            self.assertEqual((code, out["status"]), (2, "rejected"))
            code, out, _ = run("check-product", "--product", target)
            self.assertEqual((code, out["status"]), (0, "ok"))
            built = json.loads(target.read_text(encoding="utf-8"))
            bad = copy.deepcopy(built)
            t10_fixture.NEGATIVE_VARIANTS["chunk-average"][0](bad["reconstruction_product"]["scan"])
            code, out, _ = run("check-product", "--product", write_json(folder, "bad.json", bad))
            self.assertEqual((code, out["status"]), (1, "failed"))
            self.assertIn("reconstruction.scan.chunk_average", out["errors"])
            incomplete = {k: v for k, v in built.items() if k != "solver"}
            code, out, _ = run("check-product", "--product", write_json(folder, "incomplete.json", incomplete))
            self.assertEqual((code, out["status"]), (2, "rejected"))
            other_card = copy.deepcopy(built)
            other_card["method_card"]["sha256"] = "f" * 64
            code, out, _ = run("check-product", "--product", write_json(folder, "card.json", other_card))
            self.assertEqual((code, out["status"]), (2, "rejected"))
            malformed = {"map not a list": dict(built, map=5.0), "stopping not a number": dict(built, solver=dict(built["solver"], stopping="small")),
                         "residual not a number": dict(built, solver=dict(built["solver"], relative_residual=None)),
                         "method card not an object": dict(built, method_card="destriper.method-card.json"),
                         "map holds a string": dict(built, map=["x"] + built["map"][1:])}
            for name, document in malformed.items():
                with self.subTest(malformed=name):
                    code, out, err = run("check-product", "--product", write_json(folder, "malformed.json", document))
                    self.assertEqual((code, out["status"] if out else None), (2, "rejected"), err)
                    self.assertNotIn("Traceback", err)
            code, out, _ = run("solve", "--timestream", source, "--product", folder / "n.json", "--product-id", "product.n",
                               "--stopping", "1e-10", "--max-iterations", "1")
            self.assertEqual((code, out["status"]), (1, "not-converged"))
            self.assertFalse((folder / "n.json").exists())

    def test_s12_top_level_values_must_be_the_embedded_reported_values(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            document = hand_made()
            document["value"] = noisy_values(document)
            source = write_json(folder, "t.json", document)
            for constraint in ("zero-sum", "none"):
                with self.subTest(constraint=constraint):
                    target = folder / f"{constraint}.json"
                    self.assertEqual(run("solve", "--timestream", source, "--product", target, "--product-id", "product.h",
                                         "--constraint", constraint)[0], 0)
                    self.assertEqual(run("check-product", "--product", target)[0], 0)
                    built = json.loads(target.read_text(encoding="utf-8"))
                    for key in ("map", "baselines"):
                        moved = copy.deepcopy(built)
                        moved[key][1] += 100.0
                        code, out, _ = run("check-product", "--product", write_json(folder, "moved.json", moved))
                        self.assertEqual((code, out["status"]), (2, "rejected"), key)

    def test_s11_records_pass_validate(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = write_json(folder, "t.json", hand_made())
            target = folder / "p.json"
            self.assertEqual(run("solve", "--timestream", source, "--product", target, "--product-id", "product.hand-made")[0], 0)
            artifacts = folder / "artifacts"
            t10_replay.write_records(artifacts, products=[target], inputs=[source], commands=["destriper.py solve"], seeds={"fixture": None},
                                     tolerances={"stopping": DEFAULT_STOPPING}, exit_status=0)
            proc = subprocess.run([PY, "-B", str(ROOT / "contracts" / "validate.py"), str(artifacts)], capture_output=True, text=True, timeout=120)
            result = json.loads(proc.stdout)
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertTrue(result["ok"])
            self.assertEqual(result["sidecars"], ["p.scan-product.json"])
            sidecar = json.loads((artifacts / "p.scan-product.json").read_text(encoding="utf-8"))
            self.assertTrue(read_sidecar(sidecar).ok)


if __name__ == "__main__":
    unittest.main()
