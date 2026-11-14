#!/usr/bin/env python3
"""T12 stage 5: T12-14, the CPU engineering benchmark (stage 4 part B; plan v9.2 Section 14.2), and the sealed timings A13 shares.

A harness on synthetic and block-1 development inputs; numbers are records, not gates (K12: no targets); no quality claim. Every rule is
fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 5", C1-C8). It lives under tests/ because it imports the recipes'
modules and the stage 4 comparator.

- RECIPE_FILES, check_identity (C5): each recipe's files by SHA-256 at d1f6fc30 (Freeze B's bytes; calo_cluster.py and
  photon_likelihood.py with exactly the recorded post-D4 bytecode line); a different byte is rejected and nothing is timed.
- QUALITY_RECORDS, gate_recipe, SealedTimings (C6; quality before speed, stage 4 M3): a timing is sealed to its run and released only
  against a record this harness issued for that very SealedTimings object (identity), and only when the record says passed.
- bench_destriper (C1, C2), bench_t08 (C3), bench_t09 (C4): each component timed apart; the command line's total wall measured
  separately, never a sum; success and failure denominators; peak memory per process (wait4); the in-process product byte-equal to the
  command line's (the same work).
- NOT_MEASURED (C8): what is not measured, and why.

Operations:
  destriper --timestream T --out DIR [--repetitions N] [--stopping EPS] [--no-product]
  t08 --cells C --pedestal P --gain G --out DIR [--repetitions N]
  t09 --readout R --out DIR [--repetitions N] [--no-topology]
  not-measured
Each writes DIR/bench.json (and DIR/sealed-timings.json when the timings are withheld) and prints a summary line with "status": ok 0 (the
timings released), failed 1 (a repetition failed, or the gate did not pass: timings withheld), rejected 2 (an input or a recipe file is
not the approved one, or DIR exists: nothing timed), incomplete 3 (the benchmark could not run).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
DESTRIPER_ASSETS = ROOT / "adapters" / "destriper" / "assets"
CALO_ASSETS = ROOT / "adapters" / "calo-cluster" / "assets"
LIGHT_ASSETS = ROOT / "adapters" / "photon-likelihood" / "assets"
for _path in (ROOT, DESTRIPER_ASSETS, CALO_ASSETS, LIGHT_ASSETS):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
from contracts.reconstruction import read_sidecar  # noqa: E402
from core.status import exit_code  # noqa: E402
from destripe_recipe import product as destripe_product  # noqa: E402
from destripe_recipe import solver as destripe_solver  # noqa: E402
from destripe_recipe import timestream as destripe_timestream  # noqa: E402
from tests.contracts import t12_comparators as comparators  # noqa: E402

DESTRIPER, T08, T09 = "reco.scan.destriper/1", "reco.calo.cell-cluster/1", "reco.light.channel-likelihood/1"
T07 = "reco.track.acts-ckf-planar/1"
SUBPROCESS_ENV_THREADS = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}

# C5: the recipes' files at d1f6fc30. T08 and T09: Freeze B's bytes (jobs/evaluation/SOURCES.sha256), except calo_cluster.py (31b362e5 ->
# 4119bf47) and photon_likelihood.py (8a4f4fd0 -> 532260bd), each with exactly the recorded post-D4 bytecode line (decisions.md, "The held
# bytecode line"). The destriper is in no evaluation manifest: its bytes are the T10 replay's of record (job 7596623; destriper.py 2a8a0a04,
# solver.py 85ca7de7, as t10-closeout.md and the replay tree record them).
RECIPE_FILES = {
    DESTRIPER: {
        "adapters/destriper/assets/destriper.py": "2a8a0a047c508019e82807ec3573d9ed2f385ea7eb6c7abd38c35e6416fc5593",
        "adapters/destriper/assets/destriper.method-card.json": "e0edb3b363d174be9bfb2e32690aa9cd1f28dfffac3a414d75c5429202d6f418",
        "adapters/destriper/assets/destripe_recipe/__init__.py": "87fbe374d65d8884bd456d5bbd7f4cdcef8a4b455d5ec7875c2380f02d485e08",
        "adapters/destriper/assets/destripe_recipe/product.py": "f4bbbbe37cc24a677765f7e5b59329f970738c5e398f9cb97986495f4bcaa116",
        "adapters/destriper/assets/destripe_recipe/solver.py": "85ca7de737ef3608cbb50819ed9951cd7374e578d5bc24eadfc08672d31df4fb",
        "adapters/destriper/assets/destripe_recipe/timestream.py": "a30039dd5ea60299cdbf1e30645ee06b90e5df0305bffa43cecfced807fc237b",
    },
    T08: {
        "adapters/calo-cluster/assets/calo_cluster.py": "4119bf47dfb68a33c0568c79a48be86b520fb36d03935547f94405680aaddf18",
        "adapters/calo-cluster/assets/calo_recipe/__init__.py": "a0e23ddcfa478f2fa3922c554f1b2448f721faf4d8a0261ed26ed9f41941e683",
        "adapters/calo-cluster/assets/calo_recipe/cell_chain.py": "7a7c7ee5a1b713aa3de08ae9af4c3dbfcd3bec66748e78fc5cb924adeeccbc5d",
        "adapters/calo-cluster/assets/calo_recipe/cell_input.py": "b09a2e9c541682790dfa0ec9d344d10e680d3480671f4c9c6d3fd1ad8facf768",
        "adapters/calo-cluster/assets/calo_recipe/clustering.py": "f59c804245d7e7295878fa5276438e3165f8c099d84ec4f80554d46883b066d5",
        "adapters/calo-cluster/assets/calo_recipe/configuration.py": "5e28a4b67f6ebc90faf2d12431a5c7d5dfecdfc39e2f0267063395b782af68ec",
        "adapters/calo-cluster/assets/calo_recipe/gain_payload.py": "3ef05a562096e3530c04adeaedb57874958a8e35d49df3d12f8e38dc8169bea1",
        "adapters/calo-cluster/assets/calo_recipe/product.py": "73c2414c0cde4f56e77fb42df6a4b9abdf652dd004154beedd10f90871e78f69",
        "adapters/calo-cluster/assets/calo_recipe/profile.py": "a732993a4065d3922d70822f7444aaaf4b69921624fa858e3d37ca60d099d3b1",
        "adapters/calo-cluster/assets/calo_recipe/recalibration.py": "a3a73ed578c6e6bf81043568d49fb9f708d0e436cb175d84cbfdefda7e321fc1",
        "adapters/calo-cluster/assets/t08-grid-1.configuration.json": "5fbbea3b4ca81d962c5ca70fa024ddc82dd6e1d2f06e39b354fda56d26483723",
    },
    T09: {
        "adapters/photon-likelihood/assets/photon_likelihood.py": "532260bd261dff01aed4a2455ce391da7e365563a8ee4f68d1632b1088978608",
        "adapters/photon-likelihood/assets/light_recipe/__init__.py": "9d16d3ba5ba96a7c0bb2a919b2b9db9ce48020e3f4ef0ccafd358472ac3dbe60",
        "adapters/photon-likelihood/assets/light_recipe/arrival_response.py": "fcbb347d6bb3c04e366a0f28cd0a6f95749ffe71213ab25898d370a170feb14a",
        "adapters/photon-likelihood/assets/light_recipe/charge_response.py": "d619b7411ec8b70c24074d2a6fe9ab98c0ab404f4469f70b6f9bbcc5d4d4cda8",
        "adapters/photon-likelihood/assets/light_recipe/configuration.py": "1a3cf42d34a3acd081cc5a15af531b42a900844f112ee999b15ce583b619022f",
        "adapters/photon-likelihood/assets/light_recipe/fit.py": "30d92e448e461084556364e4d2fd4e036c69142dc88b91f08dbf8acfff71a476",
        "adapters/photon-likelihood/assets/light_recipe/joint.py": "aa67f3c5d35f5eac7f7cf5ec4522fb7379ce705822c3ef61e4d80b89e324806e",
        "adapters/photon-likelihood/assets/light_recipe/light_model.py": "c716d4fccb73b75a711033f8cd45f2fbe9640e4483e3339fa74064fc2814552b",
        "adapters/photon-likelihood/assets/light_recipe/likelihood.py": "1e839b9dbbbe04e5867547b3eb8d86b6cbaef06a2ba2025d41d9acb580e1a084",
        "adapters/photon-likelihood/assets/light_recipe/multistart.py": "5953620f7aa3b3b886b67e440a4b1235f983b2c6dc663e03aaed2ce862461449",
        "adapters/photon-likelihood/assets/light_recipe/product.py": "8642c59a3bb7f4ca65a671ff388b7826b3c906e8e8ebe15e0974169051f1cee7",
        "adapters/photon-likelihood/assets/light_recipe/readout.py": "605debd51cb66dc266e16b56be08df7ef28479df577476d2ad531ea805d205ce",
        "adapters/photon-likelihood/assets/light_recipe/single_photon.py": "dad0238dafeecdfb5ee75e884f540930f3ad512606b06dd6305d7e75beb8b889",
        "adapters/photon-likelihood/assets/light_recipe/topology.py": "79dc45a9b800936dd3f8288ffbca040fa6ed0487eb38da55d290be8ee8ae802e",
        "adapters/photon-likelihood/assets/t09-sphere-1.configuration.json": "ce4f430756f8ea0be1ab1b08eb638f9c38bf305968aa2d6d4e743d5fc68a1508",
        "adapters/photon-likelihood/assets/t09-multistart-1.budget.json": "70220b7ddf1679d01d4a9c5397d1fdf124c6f0bd8ed4dca562d9c18e04180307",
        "adapters/photon-likelihood/assets/t09-topology-2.budget.json": "104262a1bfb0f5403a075884d9acd5f5ccbf1fc012d5237b578297f4d98ed7df",
    },
}

# C6: each recipe's quality record at its frozen bytes (the gate its CPU timings are released on).
QUALITY_RECORDS = {
    DESTRIPER: {"status": "passed", "source": "T10 replay, job 7596623 (attempt 3, PASS) under the tolerance the user froze (t10-closeout.md)"},
    T08: {"status": "passed", "source": "evaluation attempt 1 on block 11, summary of record 7620411: passed, 8 of 8 gates (STATE.md, decisions.md)"},
    T09: {"status": "passed", "source": "evaluation attempt 1 on block 11, summary 7613459: passed, 13 of 13 gates (STATE.md, decisions.md)"},
    T07: {"status": "failed", "source": "failed at attempt 1 on block 11, summary 7613452 (STATE.md; the user, 2026-11-13): no speed number (A50)"},
}

NOT_MEASURED = {
    T07: ("failed at attempt 1 (STATE.md): no speed number may be released for it (A15, A50), so a measurement would stay sealed; it also "
          "needs the native ACTS build"),
    "reco.vertex.acts-amvf/1": "part of T07's chain (the vertexer runs in the finder): as T07",
    "reco.track.acts-kf-refit/1": "part of T07's chain: as T07",
    "reco.timing.time-chain/1": "not named by stage 4 part B's workload list (events for T07-T09, samples and baselines for the destriper); no A13 role",
    "destriper conditions": "the recipe consumes no conditions (conditions_ref \"none\"): not applicable",
    "destriper output and checks on the larger scans": "OI-13: destriper-product/1 embeds a dense design matrix; no product of a larger scan can be written",
    "T09 reading, conversion, compute and output apart": ("done inside one command-line call per event; separating them means instrumenting a "
                                                          "frozen file; the calls are timed whole, initialization by a fresh-process import probe"),
    "queue wait per recipe": "the job's own queue wait is read once from sacct (Submit to Start); recipes run in one job",
}

# M4 (fix round 1): what each timed part contains, per recipe; the in-process parts do not overlap one another, the command-line walls
# overlap them (each wall holds its own interpreter start, imports and reading), and no number is a sum of others.
_PROBE = "initialization is a separate fresh-process probe (interpreter start and the recipe's imports)"
OVERLAP = {
    DESTRIPER: ("io, reading, compute, output and checks run one after another in one thread (no overlap among them); total_wall is the "
                "command line's own separate run (interpreter start, imports, reading, solve, writing): it overlaps all of them and the "
                "initialization probe, and is never their sum; on the larger scans total_wall is measured around the in-process sequence "
                "(io, reading, compute) instead; " + _PROBE),
    T08: ("configuration, io, reading, conditions, conversion, compute and output run in one thread in process (no overlap among them); "
          "checks is the check-product command line's wall and includes its own interpreter start, imports and reading of the product; "
          "total_wall is the reconstruct command line's own separate run and overlaps every in-process part; " + _PROBE),
    T09: ("each part is a whole command line's wall (fit_multistart, check_multistart, topology, check_topology): each includes its own "
          "interpreter start and imports (overlapping the initialization probe) and its own reading; the parts run one after another; " + _PROBE),
}


class IdentityError(ValueError):
    """A recipe file is not the pinned one, or the recipe is unknown (rejected, exit 2)."""


class BenchInputError(ValueError):
    """An input or output the benchmark cannot use (rejected, exit 2)."""


class Withheld(RuntimeError):
    """A timing asked for before, or without, a passed quality record of its own run."""


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def check_identity(recipe: str, root: Path = ROOT) -> dict:
    if recipe not in RECIPE_FILES:
        raise IdentityError(f"no pinned files for {recipe!r}")
    for relative, expected in RECIPE_FILES[recipe].items():
        try:
            found = sha256_bytes((Path(root) / relative).read_bytes())
        except OSError as exc:
            raise IdentityError(f"{relative} cannot be read: {exc.strerror}") from exc
        if found != expected:
            raise IdentityError(f"{relative} is not the pinned file (SHA-256 {found}, expected {expected})")
    return {"recipe": recipe, "files": len(RECIPE_FILES[recipe]), "pinned_at": "d1f6fc30"}


# ================================================================ sealed timings (quality before speed)

class _Record:
    """A quality record; only issue() makes one, and a timing is released only against this very object (stage 4, M3)."""
    __slots__ = ("owner", "status", "basis", "__weakref__")

    def __init__(self, owner, status: str, basis: dict):
        self.owner, self.status, self.basis = owner, status, basis


_ISSUED: dict = {}


def issue(owner, status: str, basis: dict) -> _Record:
    """The harness's own quality record for one SealedTimings object (the A13 gate and gate_recipe call it)."""
    record = _Record(owner, status, basis)
    _ISSUED[id(record)] = record
    return record


class SealedTimings:
    """Timings of one run, sealed when the run starts; released only against a passed record issued for this object."""

    def __init__(self, subject: str):
        self.subject = subject
        self._values: dict = {}

    def record(self, component: str, seconds: float) -> None:
        self._values.setdefault(component, []).append(float(seconds))

    def _check(self, record) -> None:
        if _ISSUED.get(id(record)) is not record:
            raise Withheld("no speed number before the quality gate: only a record the harness issued releases a timing")
        if record.owner is not self:
            raise Withheld("a quality record of another run cannot release these timings")
        if record.status != "passed":
            raise Withheld(f"the quality answer is {record.status}: the timings are withheld")

    def release(self, record) -> dict:
        self._check(record)
        return {name: list(values) for name, values in self._values.items()}

    def withheld_reason(self, record) -> str:
        try:
            self._check(record)
        except Withheld as exc:
            basis = getattr(record, "basis", {}) or {}
            item = basis.get("open_item")
            return f"{exc}" + (f" ({item})" if item else "")
        return ""

    def sealed_document(self, record) -> dict:
        """The withheld values, for the sealed file no report reads."""
        return {"label": "withheld: no passed quality record; not to be read or reported (quality before speed)", "subject": self.subject,
                "reason": self.withheld_reason(record), "values": {name: list(values) for name, values in self._values.items()}}


def gate_recipe(timings: SealedTimings, recipe: str, comparator: dict | None = None, same_work: dict | None = None) -> _Record:
    """C6: the recipe's quality record, unless this run's comparator or same-work check did not pass (not-applicable is ignored)."""
    base = QUALITY_RECORDS[recipe]
    status = base["status"]
    for extra in (comparator, same_work):
        if status == "passed" and extra is not None and extra.get("status") not in ("passed", "not-applicable"):
            status = extra.get("status") or "failed"
    return issue(timings, status, {"recipe": recipe, "record": base, "comparator": comparator and comparator.get("status"),
                                   "same_work": same_work and same_work.get("status")})


def _release_or_seal(timings: SealedTimings, record: _Record, out: Path) -> dict:
    try:
        return timings.release(record)
    except Withheld:
        (out / "sealed-timings.json").write_text(json.dumps(timings.sealed_document(record), sort_keys=True, indent=1) + "\n", encoding="utf-8")
        return {}


# ================================================================ measuring

def run_measured(argv, cwd=None, env=None) -> dict:
    """One process: wall time, exit code, peak RSS (wait4), user and system CPU seconds, output (stdout and stderr together)."""
    full_env = dict(os.environ if env is None else env)
    full_env.update(SUBPROCESS_ENV_THREADS)
    full_env["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryFile() as out:
        started = time.perf_counter()
        child = subprocess.Popen([str(a) for a in argv], cwd=cwd, env=full_env, stdout=out, stderr=subprocess.STDOUT)
        _, status, usage = os.wait4(child.pid, 0)
        wall = time.perf_counter() - started
        child.returncode = os.waitstatus_to_exitcode(status)
        out.seek(0)
        text = out.read().decode("utf-8", errors="replace")
    return {"wall": wall, "exit": child.returncode, "maxrss_kb": usage.ru_maxrss, "user": usage.ru_utime, "system": usage.ru_stime,
            "stdout": text}


def last_json(text: str) -> dict:
    for line in reversed(text.strip().splitlines()):
        try:
            found = json.loads(line)
        except ValueError:
            continue
        if isinstance(found, dict):
            return found
    return {}


def init_probe(python: str, folder: Path, modules: str) -> dict:
    """Initialization: a fresh interpreter importing the recipe's modules (interpreter start included)."""
    code = f"import sys; sys.dont_write_bytecode = True; sys.path[:0] = [{str(ROOT)!r}, {str(folder)!r}]; import {modules}"
    return run_measured([python, "-B", "-c", code])


def quantiles(values) -> dict:
    seconds = numpy.asarray(values, dtype=float)
    return {"p50": float(numpy.quantile(seconds, 0.5)), "p90": float(numpy.quantile(seconds, 0.9)), "p99": float(numpy.quantile(seconds, 0.99))}


def compare_same_work(in_process: bytes, command_line: bytes) -> dict:
    """C2: the in-process product is the command line's, byte for byte."""
    if in_process == command_line:
        return {"status": "passed", "sha256": sha256_bytes(in_process)}
    first = next((i for i, (a, b) in enumerate(zip(in_process, command_line)) if a != b), min(len(in_process), len(command_line)))
    return {"status": "failed", "first_difference": first, "in_process_sha256": sha256_bytes(in_process),
            "command_line_sha256": sha256_bytes(command_line)}


def _start(out: Path, recipe: str) -> tuple:
    out = Path(out)
    if out.exists():
        raise BenchInputError(f"{out} exists: a benchmark folder is never overwritten")
    identity = check_identity(recipe)
    out.mkdir(parents=True)
    return out, identity, {"attempted": 0, "succeeded": 0, "failed": {}}


def _fail(denominators: dict, category: str) -> None:
    denominators["failed"][category] = denominators["failed"].get(category, 0) + 1


def _finish(out: Path, record: dict, timings: SealedTimings, gate: _Record) -> dict:
    record["quality"] = {"status": gate.status, "basis": gate.basis}
    record["released"] = _release_or_seal(timings, gate, out)
    record["medians"] = {name: statistics.median(values) for name, values in record["released"].items()}
    (out / "bench.json").write_text(json.dumps(record, sort_keys=True, indent=1, default=str) + "\n", encoding="utf-8")
    return record


# ================================================================ C1, C2: the destriper

def scan_timestream(pixels: int, baselines: int, length: int, seed: int) -> dict:
    """A larger synthetic scan, t10-destripe/1's model at scale (stage 5): baseline b sweeps a contiguous arc of length/2 or length pixels
    from a seeded start; map integers 1..19 with a random sign; baselines in pairs (v, -v); white noise sigma 1; streams seed, seed + 1,
    seed + 2. A destriper-timestream/1 document (data side: no truth)."""
    rng = numpy.random.default_rng(seed)
    starts = rng.integers(0, pixels, baselines)
    arcs = rng.choice([length // 2, length], baselines)
    pixel = ((starts[:, None] + (numpy.arange(length)[None, :] * arcs[:, None]) // length) % pixels).ravel()
    signal = numpy.random.default_rng(seed + 1)
    sky = signal.integers(1, 20, pixels) * signal.choice([-1, 1], pixels)
    pairs = signal.integers(1, 10, baselines // 2)
    offsets = numpy.concatenate([pairs, -pairs])[signal.permutation(baselines)]
    value = sky[pixel] + numpy.repeat(offsets, length) + numpy.random.default_rng(seed + 2).normal(0.0, 1.0, pixel.size)
    return {"format": "destriper-timestream/1", "role": "reconstruction-input", "unit": "artificial-unit", "pixels": int(pixels),
            "baseline_length": int(length), "noise_premise": "white noise of one variance per sample, stated by the generator, not estimated",
            "pixel": [int(p) for p in pixel], "value": [float(v) for v in value]}


def bench_destriper(timestream: Path, out: Path, repetitions: int = 3, stopping: float = 1e-10, product: bool = True,
                    python: str = sys.executable) -> dict:
    out, identity, denominators = _start(out, DESTRIPER)
    timestream = Path(timestream)
    timings = SealedTimings(f"T12-14 destriper {timestream.name}")
    record = {"recipe": DESTRIPER, "identity": identity, "input": {"file": timestream.name}, "stopping": stopping, "overlap": OVERLAP[DESTRIPER],
              "not_applicable": {"conditions": NOT_MEASURED["destriper conditions"]}, "same_work": [], "comparator": [], "memory": [],
              "workload": None}
    if not product:
        record["not_applicable"]["output"] = record["not_applicable"]["checks"] = NOT_MEASURED["destriper output and checks on the larger scans"]
    iterations = []
    worst = {"same_work": None, "comparator": None}
    for rep in range(repetitions):
        denominators["attempted"] += 1
        times = {}
        probe = init_probe(python, DESTRIPER_ASSETS, "numpy, destripe_recipe.solver, destripe_recipe.product, destripe_recipe.timestream, "
                                                     "contracts.reconstruction")
        if probe["exit"] != 0:
            _fail(denominators, "initialization")
            continue
        times["initialization"] = probe["wall"]
        whole = time.perf_counter()
        started = time.perf_counter()
        raw = timestream.read_bytes()
        times["io"] = time.perf_counter() - started
        record["input"]["sha256"] = sha256_bytes(raw)
        started = time.perf_counter()
        try:
            stream = destripe_timestream.read(json.loads(raw.decode("utf-8")))
        except destripe_timestream.Refusal:
            _fail(denominators, "refused")
            continue
        except (UnicodeDecodeError, ValueError):
            _fail(denominators, "rejected")
            continue
        times["reading"] = time.perf_counter() - started
        started = time.perf_counter()
        try:
            solution = destripe_solver.solve(stream, stopping=stopping)
        except destripe_solver.NotConverged:
            _fail(denominators, "not-converged")
            continue
        times["compute"] = time.perf_counter() - started
        iterations.append(solution.iterations)
        record["workload"] = {"samples": stream.samples, "baselines": stream.baselines, "pixels": stream.pixels, "iterations": iterations}
        if not product:
            times["total_wall"] = time.perf_counter() - whole       # measured around the whole in-process sequence (no command line)
        else:
            product_id = f"t12-14-destriper-r{rep}"
            started = time.perf_counter()
            built = destripe_product.build(stream, solution, constraint="zero-sum", product_id=product_id, input_sha256=sha256_bytes(raw),
                                           card_path=comparators.CARD)
            text = destripe_product.dumps(built)
            mine = out / f"inprocess-r{rep}.product.json"
            mine.write_text(text, encoding="utf-8")
            times["output"] = time.perf_counter() - started
            started = time.perf_counter()
            try:
                destripe_product.read(json.loads(text), DESTRIPER_ASSETS)
                contract_ok = read_sidecar(built["reconstruction_product"]).ok
            except (destripe_product.ProductError, ValueError):
                contract_ok = False
            times["checks"] = time.perf_counter() - started
            if not contract_ok:
                _fail(denominators, "checks")
                continue
            theirs = out / f"cli-r{rep}.product.json"
            cli = run_measured([python, "-B", DESTRIPER_ASSETS / "destriper.py", "solve", "--timestream", timestream, "--product", theirs,
                                "--product-id", product_id, "--stopping", repr(stopping)])
            record["memory"].append({"command_line_maxrss_kb": cli["maxrss_kb"]})
            if cli["exit"] != 0 or not theirs.is_file():
                _fail(denominators, f"command-line-exit-{cli['exit']}")
                continue
            times["total_wall"] = cli["wall"]
            same = compare_same_work(mine.read_bytes(), theirs.read_bytes())
            record["same_work"].append(same)
            try:
                compared = comparators.compare_numerical(DESTRIPER, json.loads(theirs.read_text()), json.loads(text))
                compared = {"status": compared["status"], "failed": compared["failed"], "ruling": compared["ruling"],
                            "readings": compared["readings"]}
            except comparators.ComparatorInputError as exc:      # another pointing than the record's (OI-8): no frozen tolerance
                compared = {"status": "not-applicable", "reason": str(exc)}
            record["comparator"].append(compared)
            for key, found in (("same_work", same), ("comparator", compared)):
                if worst[key] is None or found["status"] not in ("passed", "not-applicable"):
                    worst[key] = found
            if same["status"] != "passed" or compared["status"] not in ("passed", "not-applicable"):
                _fail(denominators, "same-work" if same["status"] != "passed" else "comparator")
                continue
        for name, seconds in times.items():
            timings.record(name, seconds)
        denominators["succeeded"] += 1
    record["denominators"] = denominators
    if denominators["succeeded"] == 0:
        gate = issue(timings, "failed", {"recipe": DESTRIPER, "reason": "no repetition succeeded"})
    else:
        gate = gate_recipe(timings, DESTRIPER, comparator=worst["comparator"], same_work=worst["same_work"])
    record = _finish(out, record, timings, gate)
    if record["released"] and record["workload"]:
        record["throughput"] = {"samples_per_second_compute": record["workload"]["samples"] / record["medians"]["compute"]}
        (out / "bench.json").write_text(json.dumps(record, sort_keys=True, indent=1, default=str) + "\n", encoding="utf-8")
    return record


# ================================================================ C3: T08

def bench_t08(cells: Path, pedestal: Path, gain: Path, out: Path, repetitions: int = 3, python: str = sys.executable) -> dict:
    """The command line's reconstruct path, step by step in process (calo_cluster.py reconstruct), then the command line itself."""
    out, identity, denominators = _start(out, T08)
    import calo_cluster
    from calo_recipe import cell_chain, cell_input, clustering, configuration, gain_payload
    from calo_recipe import product as calo_product
    timings = SealedTimings(f"T12-14 T08 {Path(cells).name}")
    record = {"recipe": T08, "identity": identity, "input": {"cells": Path(cells).name}, "overlap": OVERLAP[T08], "same_work": [], "latency": [],
              "memory": [], "workload": None, "not_applicable": {}}
    worst = None
    for rep in range(repetitions):
        denominators["attempted"] += 1
        times = {}
        probe = init_probe(python, CALO_ASSETS, "numpy, scipy, calo_recipe.cell_chain, calo_recipe.cell_input, calo_recipe.clustering, "
                                                "calo_recipe.configuration, calo_recipe.gain_payload, calo_recipe.product")
        if probe["exit"] != 0:
            _fail(denominators, "initialization")
            continue
        times["initialization"] = probe["wall"]
        product_id = f"t12-14-t08-r{rep}"
        mine = out / f"inprocess-r{rep}.product.jsonl"
        try:
            started = time.perf_counter()
            cfg = configuration.load(None)
            times["configuration"] = time.perf_counter() - started
            started = time.perf_counter()
            content = Path(cells).read_bytes()
            times["io"] = time.perf_counter() - started
            started = time.perf_counter()
            readout = cell_input.read_cells(content, "cells")
            times["reading"] = time.perf_counter() - started
            started = time.perf_counter()
            pedestal_payload = cell_input.read_file(pedestal, cell_input.read_payload, "pedestal payload")
            gain_document = cell_input.read_file(gain, gain_payload.read_gain, "gain payload")
            chain = cell_chain.chain_record(pedestal_payload, gain_document)
            if (readout.header["nx"], readout.header["ny"]) != (cfg.cells_x, cfg.cells_y):
                raise cell_input.InputError("readout grid is not the configuration's")
            gain_payload.check_channel_map(gain_document, readout.header["nx"], readout.header["ny"], "gain payload")
            calo_cluster.check_label(readout, cfg, gain_document)
            cell_chain.check_units(readout.header["raw_unit"], pedestal_payload, gain_document)
            times["conditions"] = time.perf_counter() - started
        except (configuration.ConfigurationError, cell_input.InputError):
            _fail(denominators, "rejected")
            continue
        header = calo_product.header_document(product_id, cfg.cells_x, cfg.cells_y, readout.sha256, readout.events, cfg.sha256, chain,
                                              label=readout.label, provenance=readout.header.get("provenance"),
                                              unresolved=cfg.unresolved if readout.label is not None else None)
        conversion = compute = writing = 0.0
        latency = []
        started = time.perf_counter()
        with open(mine, "w", encoding="utf-8") as stream:
            writer = calo_product.Writer(stream, header)
            writing += time.perf_counter() - started
            for i in range(readout.events):
                started = time.perf_counter()
                converted = cell_chain.apply(readout.raw[i], readout.live[i], readout.saturated[i], pedestal_payload, gain_document)
                conversion += time.perf_counter() - started
                started = time.perf_counter()
                result = clustering.cluster_event(converted.energy, converted.live, converted.saturated, cfg)
                latency.append(time.perf_counter() - started)
                compute += latency[-1]
                started = time.perf_counter()
                writer.event(calo_product.event_document(i, converted, result, cfg.cells_y))
                writing += time.perf_counter() - started
            started = time.perf_counter()
            writer.finish()
        writing += time.perf_counter() - started
        times.update(conversion=conversion, compute=compute, output=writing)
        check = run_measured([python, "-B", CALO_ASSETS / "calo_cluster.py", "check-product", "--product", mine])
        if check["exit"] != 0:
            _fail(denominators, f"check-product-exit-{check['exit']}")
            continue
        times["checks"] = check["wall"]
        theirs = out / f"cli-r{rep}.product.jsonl"
        cli = run_measured([python, "-B", CALO_ASSETS / "calo_cluster.py", "reconstruct", "--cells", cells, "--pedestal-payload", pedestal,
                            "--gain-payload", gain, "--product", theirs, "--product-id", product_id])
        record["memory"].append({"command_line_maxrss_kb": cli["maxrss_kb"], "check_maxrss_kb": check["maxrss_kb"]})
        if cli["exit"] not in (0, 1) or not theirs.is_file():     # 1: sharing undefined in a component, recorded, product written
            _fail(denominators, f"command-line-exit-{cli['exit']}")
            continue
        times["total_wall"] = cli["wall"]
        same = compare_same_work(mine.read_bytes(), theirs.read_bytes())
        record["same_work"].append(same)
        if worst is None or same["status"] != "passed":
            worst = same
        if same["status"] != "passed":
            _fail(denominators, "same-work")
            continue
        record["latency"].append(quantiles(latency))
        record["workload"] = {"events": readout.events, "command_line_exit": cli["exit"], "objects": last_json(cli["stdout"]).get("objects")}
        for name, seconds in times.items():
            timings.record(name, seconds)
        denominators["succeeded"] += 1
    record["denominators"] = denominators
    gate = gate_recipe(timings, T08, same_work=worst) if denominators["succeeded"] else issue(timings, "failed", {"reason": "no repetition succeeded"})
    record = _finish(out, record, timings, gate)
    if not record["released"]:
        record["latency"] = "withheld with the timings"
        (out / "bench.json").write_text(json.dumps(record, sort_keys=True, indent=1, default=str) + "\n", encoding="utf-8")
    elif record["workload"]:
        record["throughput"] = {"events_per_second_compute": record["workload"]["events"] / record["medians"]["compute"]}
        (out / "bench.json").write_text(json.dumps(record, sort_keys=True, indent=1, default=str) + "\n", encoding="utf-8")
    return record


# ================================================================ C4: T09

def bench_t09(readout: Path, out: Path, repetitions: int = 3, topology: bool = True, python: str = sys.executable) -> dict:
    """The command lines as the evaluation runs them: fit (charge-time, multistart), check-product, topology, check-product."""
    out, identity, denominators = _start(out, T09)
    timings = SealedTimings(f"T12-14 T09 {Path(readout).name}")
    script = LIGHT_ASSETS / "photon_likelihood.py"
    record = {"recipe": T09, "identity": identity, "input": {"readout": Path(readout).name}, "overlap": OVERLAP[T09], "memory": [], "workload": None,
              "not_separated": {name: NOT_MEASURED["T09 reading, conversion, compute and output apart"]
                                for name in ("reading", "io", "conversion", "compute", "output")},
              "not_applicable": {} if topology else {"topology": "not asked for (--no-topology)"}}
    for rep in range(repetitions):
        denominators["attempted"] += 1
        times = {}
        probe = init_probe(python, LIGHT_ASSETS, "numpy, scipy, light_recipe.fit, light_recipe.multistart, light_recipe.topology, "
                                                 "light_recipe.product, light_recipe.readout")
        if probe["exit"] != 0:
            _fail(denominators, "initialization")
            continue
        times["initialization"] = probe["wall"]
        multistart, topo = out / f"r{rep}.multistart.product.jsonl", out / f"r{rep}.topology.product.jsonl"
        steps = [("fit_multistart", [script, "fit", "--readout", readout, "--product", multistart, "--product-id", f"t12-14-t09-r{rep}-multistart",
                                     "--likelihood", "charge-time", "--starts", "multistart"]),
                 ("check_multistart", [script, "check-product", "--product", multistart])]
        if topology:
            steps += [("topology", [script, "topology", "--readout", readout, "--h1-product", multistart, "--product", topo, "--product-id",
                                    f"t12-14-t09-r{rep}-topology"]),
                      ("check_topology", [script, "check-product", "--product", topo])]
        failed = None
        memory = {}
        for name, argv in steps:
            found = run_measured([python, "-B", *argv])
            memory[f"{name}_maxrss_kb"] = found["maxrss_kb"]
            if found["exit"] != 0:
                failed = f"{name}-exit-{found['exit']}"
                break
            times[name] = found["wall"]
            if name == "fit_multistart":
                record["workload"] = {"events": last_json(found["stdout"]).get("events"),
                                      "converged": last_json(found["stdout"]).get("converged")}
        record["memory"].append(memory)
        if failed:
            _fail(denominators, failed)
            continue
        for name, seconds in times.items():
            timings.record(name, seconds)
        denominators["succeeded"] += 1
    record["denominators"] = denominators
    gate = gate_recipe(timings, T09) if denominators["succeeded"] else issue(timings, "failed", {"reason": "no repetition succeeded"})
    record = _finish(out, record, timings, gate)
    if record["released"] and record["workload"] and record["workload"]["events"]:
        record["throughput"] = {"events_per_second_fit": record["workload"]["events"] / record["medians"]["fit_multistart"]}
        (out / "bench.json").write_text(json.dumps(record, sort_keys=True, indent=1, default=str) + "\n", encoding="utf-8")
    return record


# ================================================================ command line

def _summary(record: dict) -> dict:
    failed = record["denominators"]["failed"]
    status = "ok" if record["released"] and not failed else "failed"
    return {"status": status, "recipe": record["recipe"], "quality": record["quality"]["status"], "denominators": record["denominators"],
            "released": sorted(record["released"])}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="operation", required=True)
    d = sub.add_parser("destriper")
    d.add_argument("--timestream", required=True, type=Path)
    d.add_argument("--out", required=True, type=Path)
    d.add_argument("--repetitions", type=int, default=3)
    d.add_argument("--stopping", type=float, default=1e-10)
    d.add_argument("--no-product", action="store_true", help="a larger scan: no product (OI-13), no command-line run")
    c = sub.add_parser("t08")
    c.add_argument("--cells", required=True, type=Path)
    c.add_argument("--pedestal", required=True, type=Path)
    c.add_argument("--gain", required=True, type=Path)
    c.add_argument("--out", required=True, type=Path)
    c.add_argument("--repetitions", type=int, default=3)
    t = sub.add_parser("t09")
    t.add_argument("--readout", required=True, type=Path)
    t.add_argument("--out", required=True, type=Path)
    t.add_argument("--repetitions", type=int, default=3)
    t.add_argument("--no-topology", action="store_true")
    sub.add_parser("not-measured")
    args = parser.parse_args(argv)
    if args.operation == "not-measured":
        print(json.dumps({"status": "ok", "not_measured": NOT_MEASURED}, sort_keys=True))
        return 0
    try:
        if getattr(args, "repetitions", 1) < 1:
            raise BenchInputError("at least one repetition")
        if args.operation == "destriper":
            record = bench_destriper(args.timestream, args.out, args.repetitions, args.stopping, product=not args.no_product)
        elif args.operation == "t08":
            record = bench_t08(args.cells, args.pedestal, args.gain, args.out, args.repetitions)
        else:
            record = bench_t09(args.readout, args.out, args.repetitions, topology=not args.no_topology)
    except (BenchInputError, IdentityError, OSError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, sort_keys=True))
        return 2
    except Exception as exc:  # noqa: BLE001  (the benchmark could not run: incomplete, never a reading)
        print(json.dumps({"status": "incomplete", "reason": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        return 3
    summary = _summary(record)
    print(json.dumps(summary, sort_keys=True))
    return exit_code(summary["status"])


if __name__ == "__main__":
    sys.exit(main())
