#!/usr/bin/env python3
"""T12 stage 5: A13, the T10 destriper's baseline solve on the GPU against the CPU recipe (T12-16), with its execution fields (T12-22).

A harness-side transcription of destripe_recipe/solver.py in PyTorch, not a recipe and not a change to one: the same conjugate gradient
on the reduced baseline system D a = F^T Z y from a = 0, every residual and direction projected onto the zero-sum subspace, the stopping
test on the recomputed residual, the restart when the recurrence collapses, the budget of BUDGET_PER_BASELINE per baseline and the
recipe's NotConverged; then the map by binning. The input is read by the recipe's reader (destripe_recipe.timestream.read), the product
written by the recipe's writer (destripe_recipe.product.build with a destripe_recipe.solver.Solution) and read back by its reader and
contracts.reconstruction.read_sidecar. Precision float64 (T10's frozen tolerance is a float64 derivation); float32 is a reading only,
never built into a product and never compared. Every rule is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 5").
Synthetic inputs only; no quality claim.

- Quality: on the frozen pointing (t10-destripe/1, seed 20260) the stage 4 numerical comparator (t12_comparators.compare_numerical, T10's
  frozen records, the OI-8 ruling); on any other pointing the answer is incomplete (OI-12), with differences as readings, and no product
  is written (OI-13).
- Quality before speed: every timing is sealed to its run (t12_benchmark.SealedTimings) and released only against the quality record
  this harness makes from that run's products, and only when it passed; otherwise it goes to sealed-timings.json, which no report reads.
- T12-22: execution_fields("gpu-subchain") describes the subchain; the CPU recipe gets none.

Operations:
  write --size S --out FILE
      the size's timestream (destriper-timestream/1); never overwrites. Exit 0 written, 2 rejected.
  run --size S|custom --device cuda|cpu --timestream T [--reference P] --out DIR [--warm N] [--launched-at EPOCH] [--float32-reading]
      one repetition in this process: read, solve once (first) and N more times (warm), check, gate, release or seal. --reference is the
      CPU recipe's product of T (destriper.py solve), required for the frozen sizes; for any other pointing the CPU side is the recipe's
      solver in this process. Writes DIR/run.json (and DIR/gpu.product.json, DIR/sealed-timings.json). Exit (core/status.py): 0 passed;
      1 failed, not-converged or refused; 2 rejected (DIR exists, an input that is not the size's, a missing reference); 3 incomplete (OI-12,
      or no CUDA device: never a silent CPU run).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy  # noqa: E402
import torch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tests.contracts import t12_benchmark as bench  # noqa: E402
from tests.contracts import t12_comparators as cmp  # noqa: E402  (its import puts the destriper's assets and fixture tools on the path)
from contracts.reconstruction import read_sidecar  # noqa: E402
from core.status import exit_code  # noqa: E402
from destripe_recipe import BUDGET_PER_BASELINE  # noqa: E402
from destripe_recipe import product as destripe_product  # noqa: E402
from destripe_recipe import solver as destripe_solver  # noqa: E402
from destripe_recipe import timestream as destripe_timestream  # noqa: E402
import t10_fixture  # noqa: E402
_IMPORTED = time.time()   # M3 (fix round 1): after every import of this module, the plugin's and the recipe's included

DESTRIPER = cmp.DESTRIPER
SUBCHAIN = "a13-gpu-destriper/1 (harness-side transcription of reco.scan.destriper/1's solver; not a recipe)"
SIZES = {
    "frozen-noisy": {"fixture": "t10-destripe/1", "variant": "noisy", "seed": 20260, "pixels": 16, "baselines": 32, "length": 8,
                     "samples": 256, "stopping": 1e-10, "frozen": True},
    "frozen-noiseless": {"fixture": "t10-destripe/1", "variant": "noiseless", "seed": 20260, "pixels": 16, "baselines": 32, "length": 8,
                         "samples": 256, "stopping": 1e-13, "frozen": True},
    "scan-1m": {"pixels": 4096, "baselines": 8192, "length": 128, "samples": 1048576, "seed": 20261, "stopping": 1e-10, "frozen": False},
    "scan-16m": {"pixels": 16384, "baselines": 65536, "length": 256, "samples": 16777216, "seed": 20262, "stopping": 1e-10, "frozen": False},
}
CUSTOM = "custom"
OPEN_ITEMS = {
    "OI-12": ("A13 on a pointing other than T10's record (t10-destripe/1, seed 20260): T10's frozen tolerance holds only on its pointing "
              "(OI-8 ruling) and no tolerance is frozen for another, so the GPU-against-CPU answer is incomplete, with the differences as "
              "readings; a tolerance for a larger scan would need its own derivation and the user's freeze"),
    "OI-13": ("destriper-product/1 embeds a dense design matrix (samples x (pixels + baselines)), so no product of a larger scan can be "
              "written; the larger sizes are compared in memory, the CPU side by the recipe's solver in the same process"),
}
DTYPES = {"float64": torch.float64, "float32": torch.float32}
SCALARS_PER_ITERATION = 4     # curvature, |r|^2, |r_new|^2 and the recomputed residual's norm: the algorithm's own host reads


class DeviceUnavailable(RuntimeError):
    """The device asked for is not there, or unknown (incomplete, exit 3): never a silent run elsewhere."""


class PrecisionError(ValueError):
    """A precision the comparison does not accept (rejected, exit 2)."""


# ================================================================ inputs

def dumps_timestream(document: dict) -> bytes:
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def input_sha256(document: dict) -> str:
    return hashlib.sha256(dumps_timestream(document)).hexdigest()


scan_timestream = bench.scan_timestream


def timestream_for(size: str) -> dict:
    spec = SIZES[size]
    if spec["frozen"]:
        return t10_fixture.generate(spec["variant"], spec["seed"])[0]
    return scan_timestream(spec["pixels"], spec["baselines"], spec["length"], spec["seed"])


def read_stream(document: dict):
    """The recipe's own reader: a scan it refuses (an unobserved pixel, two components) is refused before any device work."""
    return destripe_timestream.read(document)


# ================================================================ the subchain

@dataclass(frozen=True)
class TorchSolution:
    map: numpy.ndarray
    baselines: numpy.ndarray
    iterations: int
    relative_residual: float
    stopping: float
    max_iterations: int
    dtype: str
    device: str
    timings: dict = field(default_factory=dict)
    transfers: dict = field(default_factory=dict)
    peak_device_bytes: int | None = None


def _device(name: str) -> torch.device:
    if name == "cpu":
        return torch.device("cpu")
    if name == "cuda":
        if not torch.cuda.is_available():
            raise DeviceUnavailable("no CUDA device is visible: the GPU subchain does not run elsewhere in its place")
        return torch.device("cuda")
    raise DeviceUnavailable(f"unknown device {name!r}; cuda or cpu")


def _sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def torch_solve(stream, *, stopping: float, max_iterations: int | None = None, device: str = "cpu", dtype: str = "float64",
                probe: dict | None = None) -> TorchSolution:
    """destripe_recipe.solver.solve, transcribed: same start, projections, stopping test, restart, budget and NotConverged.

    probe (tests only; fix round 1, I1): a dict that receives "restarts" (the iteration count at each restart) and "means" (per step,
    the largest |mean| / max|v| of a, direction, residual and image after the projections); with probe["offset"] = c, c times the
    ones vector (the null mode) is injected into the start of a, the start of the direction and every application of D, so a test can
    show that every projection removes it. Probe reads are not counted as transfers."""
    if dtype not in DTYPES:
        raise PrecisionError(f"precision {dtype!r}: float64 (compared) or float32 (a reading)")
    target, kind = _device(device), DTYPES[dtype]
    budget = BUDGET_PER_BASELINE * stream.baselines if max_iterations is None else max_iterations
    baselines, length, pixels = stream.baselines, stream.length, stream.pixels
    scalars = 0
    if target.type == "cuda":
        torch.cuda.reset_peak_memory_stats(target)

    def scalar(tensor) -> float:
        nonlocal scalars
        scalars += 1
        return float(tensor)

    _sync(target)
    started = time.perf_counter()
    pixel = torch.as_tensor(stream.pixel, dtype=torch.int64).to(target)
    value = torch.as_tensor(stream.value, dtype=torch.float64).to(target).to(kind)
    _sync(target)
    host_to_device = time.perf_counter() - started
    h2d_bytes = pixel.numel() * pixel.element_size() + value.numel() * value.element_size()

    started = time.perf_counter()
    hits = torch.bincount(pixel, minlength=pixels).to(kind)

    def binned(samples):                       # M^-1 P^T v
        return torch.zeros(pixels, dtype=kind, device=target).index_add_(0, pixel, samples) / hits

    def project_out_sky(samples):               # Z v
        return samples - binned(samples)[pixel]

    def sum_baselines(samples):                 # F^T v
        return samples.reshape(baselines, length).sum(dim=1)

    offset = float(probe.get("offset", 0.0)) if probe is not None else 0.0
    if probe is not None:
        probe["restarts"], probe["means"] = [], []

    def reduced(vector):                        # D a = F^T Z F a
        return sum_baselines(project_out_sky(vector.repeat_interleave(length))) + offset

    def drift(vector) -> float:
        largest = float(vector.abs().max())
        return abs(float(vector.mean())) / largest if largest > 0.0 else 0.0

    def zero_sum(vector):
        return vector - vector.mean()

    right = zero_sum(sum_baselines(project_out_sky(value)))
    size = scalar(torch.linalg.norm(right))
    a = torch.zeros(baselines, dtype=kind, device=target) + offset
    iterations, relative = 0, 1.0
    if size == 0.0:                              # M1 (fix round 1): the recipe's zero right side: 0 iterations, residual 0.0
        relative = 0.0
        a = torch.zeros(baselines, dtype=kind, device=target)
    else:
        residual = right.clone()
        direction = residual.clone() + offset
        while relative > stopping:
            if iterations >= budget:
                raise destripe_solver.NotConverged(iterations, relative)
            image = zero_sum(reduced(direction))
            curvature = scalar(direction @ image)
            squared = scalar(residual @ residual)
            if not curvature > 0.0 or not squared > 0.0:
                # the recurrence has collapsed above the stopping value: restart from the recomputed residual, within the budget
                if probe is not None:
                    probe["restarts"].append(iterations)
                residual = zero_sum(right - reduced(a))
                direction = residual.clone()
                iterations += 1
                image = zero_sum(reduced(direction))
                curvature = scalar(direction @ image)
                if not curvature > 0.0:
                    raise destripe_solver.NotConverged(iterations, relative)
                squared = scalar(residual @ residual)
            step = squared / curvature
            a = zero_sum(a + step * direction)
            updated = zero_sum(residual - step * image)
            direction = zero_sum(updated + (scalar(updated @ updated) / squared) * direction)
            residual = updated
            iterations += 1
            if probe is not None:
                probe["means"].append(max(drift(a), drift(direction), drift(residual), drift(image)))
            relative = scalar(torch.linalg.norm(zero_sum(right - reduced(a)))) / size
    sky = binned(value - a.repeat_interleave(length))
    _sync(target)
    compute = time.perf_counter() - started

    started = time.perf_counter()
    sky_host, a_host = sky.cpu(), a.cpu()
    device_to_host = time.perf_counter() - started
    d2h_bytes = sky_host.numel() * sky_host.element_size() + a_host.numel() * a_host.element_size()
    peak = torch.cuda.max_memory_allocated(target) if target.type == "cuda" else None
    return TorchSolution(sky_host.to(torch.float64).numpy(), a_host.to(torch.float64).numpy(), iterations, relative, stopping, budget, dtype,
                         target.type, {"host_to_device": host_to_device, "compute": compute, "device_to_host": device_to_host},
                         {"host_to_device_bytes": h2d_bytes, "device_to_host_bytes": d2h_bytes, "scalars": scalars}, peak)


def build_product(stream, solution: TorchSolution, product_id: str, input_sha: str) -> dict:
    """destriper-product/1 by the recipe's own writer; only a float64 solution (G6)."""
    if solution.dtype != "float64":
        raise PrecisionError(f"a {solution.dtype} solution is a reading only: no product is built from it (T10's tolerance is a float64 derivation)")
    recipe_solution = destripe_solver.Solution(solution.map, solution.baselines, solution.iterations, solution.relative_residual,
                                               solution.stopping, solution.max_iterations)
    built = destripe_product.build(stream, recipe_solution, constraint="zero-sum", product_id=product_id, input_sha256=input_sha, card_path=cmp.CARD)
    return json.loads(destripe_product.dumps(built))


def float32_reading(stream, *, stopping: float, device: str = "cpu", max_iterations: int | None = None) -> dict:
    """G6: float32 at the recipe's stopping value, as a reading; no verdict, no product, no timing. The command line caps its budget at
    twice the float64 iteration count plus 10 (a reading's budget): at 1e-10 float32 does not converge, and the recipe's budget would
    spend 10 iterations per baseline."""
    label = "reading only: float32 is never compared against T10's float64 tolerance"
    try:
        solution = torch_solve(stream, stopping=stopping, device=device, dtype="float32", max_iterations=max_iterations)
    except destripe_solver.NotConverged as exc:
        return {"dtype": "float32", "outcome": "not-converged", "iterations": exc.iterations, "relative_residual": exc.relative_residual,
                "budget": max_iterations, "label": label}
    return {"dtype": "float32", "outcome": "converged", "iterations": solution.iterations, "relative_residual": solution.relative_residual,
            "budget": max_iterations, "label": label}


# ================================================================ the A13 comparison

def a13_compare(size: str, reference: dict, candidate: dict) -> dict:
    """A frozen size: the stage 4 numerical comparator, after checking that both products name the same input and the size's stopping."""
    spec = SIZES.get(size)
    if spec is None or not spec["frozen"]:
        raise cmp.ComparatorInputError(f"{size!r} is not on the record's pointing: compare in memory (OI-12)")
    try:
        same_input = reference["input"]["sha256"] == candidate["input"]["sha256"]
        stoppings = (reference["solver"]["stopping"], candidate["solver"]["stopping"])
    except (TypeError, KeyError) as exc:
        raise cmp.ComparatorInputError(f"not a destriper product: {exc}") from exc
    if not same_input:
        raise cmp.ComparatorInputError("the two products name different inputs (input.sha256): not the same scientific work")
    if stoppings != (spec["stopping"], spec["stopping"]):
        raise cmp.ComparatorInputError(f"the products stopped at {stoppings}; {size} is at {spec['stopping']}")
    return cmp.compare_numerical(DESTRIPER, reference, candidate) | {"size": size, "subchain": SUBCHAIN}


def compare_in_memory(size: str, cpu, gpu) -> dict:
    """Another pointing: incomplete with OI-12; the differences relative to the CPU baselines' 2-norm are readings."""
    if SIZES.get(size, {}).get("frozen"):
        raise cmp.ComparatorInputError(f"{size} is on the record's pointing: it goes through the products and the stage 4 comparator")
    a_c, a_g = numpy.asarray(cpu.baselines, dtype=float), numpy.asarray(gpu.baselines, dtype=float)
    m_c, m_g = numpy.asarray(cpu.map, dtype=float), numpy.asarray(gpu.map, dtype=float)
    if a_c.shape != a_g.shape or m_c.shape != m_g.shape:
        raise cmp.ComparatorInputError("the two solutions do not have the same baselines and pixels")
    norm = float(numpy.linalg.norm(a_c)) or 1.0
    readings = {"baselines_relative": float(numpy.linalg.norm(a_g - a_c)) / norm, "map_relative": float(numpy.linalg.norm(m_g - m_c)) / norm,
                "zero_sum_relative": abs(float(a_g.sum())) / (float(numpy.abs(a_g).sum()) or 1.0),
                "iterations": [cpu.iterations, gpu.iterations], "relative_residual": [cpu.relative_residual, gpu.relative_residual]}
    return {"status": "incomplete", "size": size, "subchain": SUBCHAIN, "open_item": "OI-12", "reason": OPEN_ITEMS["OI-12"],
            "also": {"OI-13": OPEN_ITEMS["OI-13"]}, "readings": readings}


def gate(size: str, timings, reference: dict, candidate: dict):
    """The quality record of a frozen-size run, made here from that run's products (never passed in)."""
    try:
        result = a13_compare(size, reference, candidate)
    except cmp.ComparatorInputError as exc:
        return bench.issue(timings, "rejected", {"size": size, "reason": str(exc)})
    return bench.issue(timings, result["status"], {"size": size, "failed": result["failed"], "ruling": result["ruling"],
                                                   "readings": result["readings"], "tolerance": result["tolerance"]["record"]})


def gate_in_memory(size: str, timings, cpu, gpu):
    result = compare_in_memory(size, cpu, gpu)
    return bench.issue(timings, result["status"], {"size": size, "open_item": result["open_item"], "readings": result["readings"]})


# ================================================================ T12-22: execution fields

def execution_fields(backend: str, measured: dict | None = None) -> dict:
    """Section 10.4: written for the backend that has them. The CPU recipe's command line gets none."""
    if backend == "cpu-recipe":
        return {"backend": "cpu-recipe"}
    if backend != "gpu-subchain":
        raise ValueError(f"unknown backend {backend!r}: gpu-subchain or cpu-recipe")
    measured = measured or {}
    return {
        "backend": "gpu-subchain",
        "layout": "structure of arrays: contiguous 1-D tensors, pixel int64 and value float64 per sample; baselines and map float64",
        "residence": "host: reading, product, checks; device: the whole solve (operators, CG vectors, binning)",
        "ownership": "PyTorch's caching allocator on the device, released at process end; host arrays owned by the harness",
        "async_completion": "one CUDA stream; synchronized at every stopping test (the algorithm's host reads) and at every timing boundary",
        "transfer_edges": {"host_to_device_bytes_per_sample": 16, "host_to_device": "once per solve: pixel and value",
                           "device_to_host_bytes_per_parameter": 8, "device_to_host": "once per solve: map and baselines",
                           "scalars_per_iteration": SCALARS_PER_ITERATION, "measured": measured.get("transfers")},
        "zero_copy": "not claimed: every host-device copy is a copy, and measured",
        "precision": {"compared": "float64", "reading": "float32 (never compared, never a product)"},
        "batch": "one timestream per solve; no batching across timestreams",
        "memory_limits": {"device_total_mib": measured.get("device_total_mib"), "device_peak_bytes": measured.get("device_peak_bytes"),
                          "host_peak_rss_kb": measured.get("host_peak_rss_kb")},
        "streaming_queues": "not applicable: an offline solve, no queue, in-flight limit or drop policy (Section 10.4)",
    }


# ================================================================ command line

def _process_start() -> float | None:
    """This process's start (epoch seconds, 10 ms resolution) from /proc, when the shell gave no launch time."""
    try:
        stat = Path("/proc/self/stat").read_text()
        ticks = int(stat[stat.rindex(")") + 2:].split()[19])
        uptime = float(Path("/proc/uptime").read_text().split()[0])
        return time.time() - (uptime - ticks / os.sysconf("SC_CLK_TCK"))
    except (OSError, ValueError, IndexError):
        return None


def _environment(device: torch.device | None) -> dict:
    found = {"python": "%d.%d.%d" % sys.version_info[:3], "torch": torch.__version__, "cuda": torch.version.cuda, "numpy": numpy.__version__,
             "threads": torch.get_num_threads()}
    if device is not None and device.type == "cuda":
        properties = torch.cuda.get_device_properties(device)
        found.update(device=properties.name, capability=[properties.major, properties.minor],
                     device_total_mib=round(properties.total_memory / 2 ** 20))
    return found


class _Run:
    def __init__(self, out: Path, size: str, device: str):
        self.out, self.size, self.device_name = out, size, device
        self.timings = bench.SealedTimings(f"a13 {size} {device} {out.name}")
        self.document = {"size": size, "device": device, "dtype": "float64", "subchain": SUBCHAIN, "released": {},
                         "denominators": {"attempted": 1, "succeeded": 0, "failed": {}}}

    def finish(self, status: str, category: str | None = None, record=None, **fields) -> dict:
        self.document.update(fields)
        if record is not None:
            self.document["released"] = bench._release_or_seal(self.timings, record, self.out)
        if status == "passed" and self.document["released"]:
            self.document["denominators"]["succeeded"] = 1
        else:
            self.document["denominators"]["failed"] = {category or status: 1}
        self.document["status"] = status
        (self.out / "run.json").write_text(json.dumps(self.document, sort_keys=True, indent=1, default=str) + "\n", encoding="utf-8")
        summary = {"status": status, "size": self.size, "device": self.device_name, "out": str(self.out)}
        for key in ("open_item", "reason"):
            if key in fields:
                summary[key] = fields[key]
        return summary


def run(args) -> dict:
    out = Path(args.out)
    if out.exists():
        return {"status": "rejected", "reason": f"{out} exists: a run folder is never overwritten"}
    if args.size != CUSTOM and SIZES[args.size]["frozen"] and args.reference is None:
        return {"status": "rejected", "reason": f"{args.size} needs --reference, the CPU recipe's product of the same timestream"}
    if not Path(args.timestream).is_file():
        return {"status": "rejected", "reason": f"no such timestream {args.timestream}"}
    launched = args.launched_at if args.launched_at is not None else _process_start()
    out.mkdir(parents=True)
    current = _Run(out, args.size, args.device)
    if launched is not None:
        current.timings.record("process_to_import", _IMPORTED - launched)
    started = time.perf_counter()
    try:
        target = _device(args.device)
        if target.type == "cuda":
            torch.cuda.init()
        torch.zeros(1, device=target).add_(1)
        _sync(target)
    except DeviceUnavailable as exc:
        return current.finish("incomplete", "device-unavailable", reason=str(exc), environment=_environment(None))
    current.timings.record("device_init", time.perf_counter() - started)
    current.document["environment"] = _environment(target)

    started = time.perf_counter()
    raw = Path(args.timestream).read_bytes()
    try:
        document = json.loads(raw.decode("utf-8"))
        stream = read_stream(document)
    except destripe_timestream.Refusal as exc:
        return current.finish("refused", reason=str(exc))
    except (UnicodeDecodeError, ValueError) as exc:
        return current.finish("rejected", reason=str(exc))
    current.timings.record("reading", time.perf_counter() - started)
    sha = hashlib.sha256(raw).hexdigest()
    current.document["input"] = {"file": Path(args.timestream).name, "sha256": sha, "samples": stream.samples, "baselines": stream.baselines,
                                 "pixels": stream.pixels}
    if args.size != CUSTOM:
        spec = SIZES[args.size]
        if (stream.pixels, stream.baselines, stream.length) != (spec["pixels"], spec["baselines"], spec["length"]) or \
                (spec["frozen"] and sha != input_sha256(timestream_for(args.size))):
            return current.finish("rejected", reason=f"the timestream is not {args.size}'s")
        stopping = spec["stopping"]
    else:
        stopping = args.stopping

    try:
        first = torch_solve(stream, stopping=stopping, device=args.device)
        for name in ("host_to_device", "device_to_host"):
            current.timings.record(name, first.timings[name])
        current.timings.record("compute_first", first.timings["compute"])
        warm = []
        for _ in range(args.warm):
            again = torch_solve(stream, stopping=stopping, device=args.device)
            current.timings.record("compute_warm", again.timings["compute"])
            warm.append({"iterations": again.iterations, "byte_equal_to_first": bool(numpy.array_equal(again.baselines, first.baselines)
                                                                                     and numpy.array_equal(again.map, first.map))})
    except destripe_solver.NotConverged as exc:
        return current.finish("not-converged", reason=str(exc))
    measured = {"transfers": first.transfers, "device_peak_bytes": first.peak_device_bytes,
                "device_total_mib": current.document["environment"].get("device_total_mib"),
                "host_peak_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    current.document.update(iterations=first.iterations, relative_residual=first.relative_residual, warm=warm,
                            execution_fields=execution_fields("gpu-subchain", measured))
    if args.float32_reading:
        current.document["float32_reading"] = float32_reading(stream, stopping=stopping, device=args.device,
                                                               max_iterations=2 * first.iterations + 10)

    started = time.perf_counter()
    if args.size != CUSTOM and SIZES[args.size]["frozen"]:
        product = build_product(stream, first, f"a13-{args.size}-{args.device}", sha)
        (out / "gpu.product.json").write_text(destripe_product.dumps(product), encoding="utf-8")
        try:
            destripe_product.read(json.loads((out / "gpu.product.json").read_text()), cmp.DESTRIPER_ASSETS)
            contract = read_sidecar(product["reconstruction_product"])
            reference = json.loads(Path(args.reference).read_text(encoding="utf-8"))
        except (destripe_product.ProductError, OSError, ValueError) as exc:
            return current.finish("rejected", reason=f"a product cannot be read: {exc}")
        if not contract.ok:
            return current.finish("failed", "contract", reason="contracts.reconstruction refuses the embedded product")
        record = gate(args.size, current.timings, reference, product)
        current.timings.record("checks", time.perf_counter() - started)
        quality = {"status": record.status, **record.basis}
        return current.finish(record.status, record=record, quality=quality,
                              **({"reason": record.basis["reason"]} if "reason" in record.basis else {}))
    # another pointing: the CPU side is the recipe's solver in this process (its own timing, released on the recipe's record, C6)
    cpu_timings = bench.SealedTimings(f"a13 {args.size} cpu-recipe {out.name}")
    began = time.perf_counter()
    try:
        cpu = destripe_solver.solve(stream, stopping=stopping)
    except destripe_solver.NotConverged as exc:
        return current.finish("not-converged", "cpu-not-converged", reason=f"the CPU recipe: {exc}")
    cpu_timings.record("compute", time.perf_counter() - began)
    started = time.perf_counter()               # M2 (fix round 1): the checks exclude the CPU recipe's solve, timed apart above
    record = gate_in_memory(args.size, current.timings, cpu, first)
    current.timings.record("checks", time.perf_counter() - started)
    cpu_side = {"execution_fields": execution_fields("cpu-recipe"), "iterations": cpu.iterations,
                "released": cpu_timings.release(bench.gate_recipe(cpu_timings, DESTRIPER)),
                "note": "the recipe's solver in this process (the venv's NumPy), single-threaded as the job sets it"}
    return current.finish(record.status, record=record, quality={"status": record.status, **record.basis}, cpu_side=cpu_side,
                          open_item=record.basis["open_item"], reason=OPEN_ITEMS["OI-12"])


def write(args) -> dict:
    target = Path(args.out)
    if target.exists():
        return {"status": "rejected", "reason": f"{target} exists: never overwritten"}
    if not target.parent.is_dir():
        return {"status": "rejected", "reason": f"no such folder {target.parent}"}
    content = dumps_timestream(timestream_for(args.size))
    target.write_bytes(content)
    return {"status": "written", "size": args.size, "out": str(target), "sha256": hashlib.sha256(content).hexdigest()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="operation", required=True)
    w = sub.add_parser("write")
    w.add_argument("--size", required=True, choices=sorted(SIZES))
    w.add_argument("--out", required=True)
    r = sub.add_parser("run")
    r.add_argument("--size", required=True, choices=sorted(SIZES) + [CUSTOM])
    r.add_argument("--device", required=True)
    r.add_argument("--timestream", required=True)
    r.add_argument("--reference")
    r.add_argument("--out", required=True)
    r.add_argument("--warm", type=int, default=2)
    r.add_argument("--stopping", type=float, default=1e-10, help="--size custom only; a named size has its own")
    r.add_argument("--launched-at", type=float, help="the shell's launch time (epoch seconds) of this process")
    r.add_argument("--float32-reading", action="store_true")
    args = parser.parse_args(argv)
    try:
        summary = write(args) if args.operation == "write" else run(args)
    except cmp.ComparatorInputError as exc:
        summary = {"status": "rejected", "reason": str(exc)}
    except Exception as exc:  # noqa: BLE001  (the run could not complete: incomplete, never a verdict)
        summary = {"status": "incomplete", "reason": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(summary, sort_keys=True))
    return exit_code(summary["status"])


if __name__ == "__main__":
    sys.exit(main())
