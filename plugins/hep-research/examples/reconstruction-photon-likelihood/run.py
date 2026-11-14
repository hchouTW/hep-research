#!/usr/bin/env python3
"""T09 photon likelihood (adapters/photon-likelihood): generate a few synthetic t09-sphere/1 events, fit them, check the product.

ILLUSTRATIVE and SYNTHETIC, a shared-model closure (plan section 11.1): the events and the fit share the stated analytic light model of
t04-values-v4.md section 4.3, so this tests the code, not the model or any instrument. Names no experiment. Makes no photon-likelihood
quality claim: the fits below are what the programs wrote, not a resolution, a wrong-minimum rate or a mis-ID rate, and T09's quality
verdict waits for K09 at Freeze B. Three events of the frozen fixture t09-sphere/1, block 1 (the tuning block):
- main: 2 events of stratum 7 (N_exp bin B3, 200 to 500 photons; r/R_s 0.4 to 0.7), one source each;
- two-source: 1 event of the two-source control (stratum 0: two sources of B3 each, one t0).
Each sample goes through the recipe reco.light.channel-likelihood/1, a development binding in Python (not a native backend):
- the scoring harness (fixture_tools/t09_fixture_files.py) calls the frozen generator, checked by its SHA-256, and writes the readout
  (light-readout/1, role reconstruction-input: per channel the state, charge, first time and saturated flag) and the truth file
  (role truth), apart;
- fit (photon_likelihood.py, data side, its own process) reads the readout alone: the joint charge and first-arrival-time likelihood
  over every live channel, from the eight data-side starts of the budget t09-multistart-1, written as light-likelihood-product/3;
- topology reads the readout and that product alone: the two-source hypothesis H2 (14 parameters, the eight starts of t09-topology-2)
  and the choice of section 7, H2 if and only if 2 (lnL_2 - lnL_1) >= 30, written as light-likelihood-product/4;
- check-product reads the /4 back and recomputes ln L and the per-channel probability check (the T09 stop).
The truth files are not used: only their SHA-256 is recorded.

Modes:
  offline replay (default): reads --recorded (default recorded/: the readouts, the /3 and /4 products, and runs.json with the reports
    and commands, the folders replaced by <work>, <plugin> and <python>), runs the checks below, and writes summary.json and report.md
    to --out (default output/); the result is byte-identical to the committed output/ (tests/examples/
    test_reconstruction_photon_likelihood.py). Needs NumPy and SciPy (the recipe and its reader).
  live (--live --generator GEN, or HEP_T09_GENERATOR): runs the harness, fit, topology and check-product in --work (a temporary folder
    by default, outside the plugin), rewrites --recorded and replays. The frozen generator is outside the repository, so the committed
    recorded/ comes from the T09 job (D3 stage 5), whose recording the coordinator copies after a PASS.

Checks, every one must pass (CHECKS, in this order): each operation ok with exit 0; the recipe's commands name no truth file; each
product names the recorded readout, and each /4 the recorded /3 (SHA-256); the products were made with the configuration and the two
budgets beside the recipe; they read back whole as /3 and /4 of the recipe, label shared-model closure, with ln L, every start and the
per-channel check recomputed by the recipe's reader; each /4 carries its /3 unchanged; no live channel's hit and no-hit probabilities
miss one at H1's or H2's point (the stop); every choice is the frozen rule; and, only when all of these pass, the recipe run again on
the recorded readouts reproduces the recorded /3 and /4 (otherwise recorded as not run, and failed).

Check 9 has two modes (D3 stage 5 review I1). runs.json records the platform of the recording (CPU model, machine, Python, NumPy, SciPy).
On that platform the rerun must write the recorded /3 and /4 byte for byte. On any other the fits run through LAPACK kernels that the CPU
and the library versions choose, so the last bits may differ, and the rerun is compared with the recorded products by compare_products at
the tolerances below, fixed before any run and never moved after a result (TOLERANCES):
- ln L (H1's fit, H2's fit, lnL_1 and lnL_2 of the choice): 1e-6 absolute. A fit converges when its Newton decrement
  d = g^T (-H)^-1 g is at most 1e-8 (light_recipe/fit.py, DECREMENT_TOL); in the quadratic model the ln L left to the maximum is d/2, at
  most 5e-9, so two converged fits of one event differ by at most about 1e-8; 1e-6 adds a factor of 100 for the non-quadratic remainder
  and the rounding of a sum of 1,000 channel terms (about 1e-12 at |ln L| of 1e4).
- the statistic 2 (lnL_2 - lnL_1): 4e-6, twice the sum of the two ln L tolerances.
- each fitted parameter, in the fit's own coordinates (x, y, z, the tangent components u1 and u2 of the direction in the recorded frame,
  E_vis, t0; for H2 the 14 coordinates of both sources): 1e-3 of its own sigma, the square root of the recorded covariance's diagonal. The
  same decrement bound puts each converged point within sqrt(d) <= 1e-4 sigma of the maximum, so two fits differ by at most 2e-4 sigma;
  1e-3 is a factor of 5 above it. A fit without a covariance (uncertainty status not ok) has no sigma: its parameters are not compared,
  its status, ln L and the choices are.
- everything discrete exactly: the header and end lines (except that a /4 header names its own side's /3 by SHA-256: the recorded /3,
  or the rerun's, whose last bits may differ), the data (states, counts, hits), every status, failure kind and uncertainty status,
  the chosen start, H2's reported start where the choice uses H2's point, the source of lnL_2, the choice, the probability
  check's failures. The starts that were not chosen and the seeds are not compared off the platform: the reported fits are the result.
The output (summary.json, report.md) does not depend on the mode; the run's JSON on stdout names it.

Expected readings, stated before the first live run and checked by nobody (the job of record of these events is the T09 stage 4 chain,
jobs 7575617 and 7576269, whose first event lines these events reproduce): main event 0, 136 hit channels, H1 converged from 8 of 8
starts, lnL_1 -650.322, statistic 13.883, choice H1; main event 1, 228 hit channels, H1 converged from 8 of 8, lnL_1 -981.699, statistic
0.000 (lnL_2 at H1's boundary), choice H1; two-source event 0, 384 hit channels, H1 converged from 8 of 8, H2 converged, lnL_1 -2426.155,
lnL_2 -1709.220, statistic 1433.869, choice H2; no probability failure; no dead or saturated channel. A different value is a reading to
explain, not a failed check.

Exit codes (core/status.py): 0 every check passes; 1 a check failed, or the recipe stopped on the probability sum; 2 the recording
or the generator is refused, or a live operation ended in error; 3 NumPy or SciPy is missing.
Usage (from the plugin root): python3 examples/reconstruction-photon-likelihood/run.py [--out DIR] [--recorded DIR]
       python3 examples/reconstruction-photon-likelihood/run.py --live --generator GEN [--work DIR] [--recorded DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
ASSETS = PLUGIN / "adapters" / "photon-likelihood" / "assets"
RECIPE_CLI = ASSETS / "photon_likelihood.py"
for _entry in (str(PLUGIN), str(ASSETS / "fixture_tools"), str(ASSETS)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from core.status import exit_code  # noqa: E402
import platform  # noqa: E402
import t09_fixture_files as fixture_files  # noqa: E402  the scoring harness; NumPy only inside its functions

BLOCK = 1
SAMPLES = (("main", "main", 7, 2), ("two-source", "two-source", 0, 1))   # (stem, fixture, stratum, events)
PRODUCT_ID = "example-reconstruction-photon-likelihood"
RECORDED_FILES = ("runs.json",) + tuple(f"{stem}.{kind}" for stem, *_ in SAMPLES for kind in ("readout", "multistart.product", "topology.product"))
FROZEN_GENERATOR_SHA256 = fixture_files.FROZEN_GENERATOR_SHA256   # freeze-a.md; the harness checks it
DROPPED_FIELDS = ("seconds",)
OPERATIONS = ("generate", "fit", "topology", "check-product")
CHECKS = (
    "every operation is ok with exit 0",
    "the recipe's commands name no truth file",
    "each product names the recorded readout, and the topology product the recorded multistart product",
    "the products were made with the configuration and budgets beside the recipe",
    "the products read back whole as the recipe's /3 and /4, label shared-model closure, ln L and the per-channel check recomputed",
    "the topology product carries its multistart product unchanged",
    "no live channel's hit and no-hit probabilities miss one, at H1's or H2's point (the T09 stop)",
    "the topology choice is the frozen rule: H2 if and only if 2 (lnL_2 - lnL_1) >= 30",
    "the recipe run again on the recorded readouts reproduces the recorded products: byte for byte on the recording's platform, "
    "else within the stated tolerances",
)
TOLERANCES = {"ln_likelihood": 1e-6, "statistic": 4e-6, "parameter_sigmas": 1e-3}   # check 9 off the recording's platform (docstring)


def current_platform() -> dict:
    """The platform that check 9's byte equality holds on: the CPU model, the machine, Python, NumPy and SciPy."""
    import numpy
    import scipy
    cpu = ""
    try:
        cpu = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")), "")
    except OSError:
        pass
    return {"cpu": cpu or platform.processor() or "unknown", "machine": platform.machine(), "python": platform.python_version(),
            "numpy": numpy.__version__, "scipy": scipy.__version__}


def _within(a, b, tolerance: float) -> bool:
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= tolerance


def _coordinates(sources: list) -> list:
    """Per source (x, y, z, (u1, u2) as the direction itself, E_vis, t0), with the frame to project direction changes on."""
    return [(s["vertex"], s["direction"], s["frame"], s["e_vis"], s["t0"]) for s in sources]


def _parameter_differences(where: str, kept_sources: list, again_sources: list, covariance) -> list:
    """Each coordinate of each source within TOLERANCES["parameter_sigmas"] of its own sigma; nothing compared without a covariance."""
    if covariance is None:
        return []
    k, out = TOLERANCES["parameter_sigmas"], []
    for j, (a, b) in enumerate(zip(_coordinates(kept_sources), _coordinates(again_sources))):
        (va, da, frame, ea, ta), (vb, db, _, eb, tb) = a, b
        turn = [y - x for x, y in zip(da, db)]
        deltas = [vb[0] - va[0], vb[1] - va[1], vb[2] - va[2], sum(t * e for t, e in zip(turn, frame["e1"])),
                  sum(t * e for t, e in zip(turn, frame["e2"])), eb - ea, tb - ta]
        for i, delta in enumerate(deltas):
            sigma = covariance[7 * j + i][7 * j + i] ** 0.5
            if not abs(delta) <= k * sigma:
                out.append(f"{where}: coordinate {7 * j + i} differs by {abs(delta):.3e}, above {k:g} of its sigma {sigma:.3e}")
    return out


def _fit_differences(where: str, kept: dict, again: dict, h2: bool) -> list:
    out = [f"{where}: {key} {kept.get(key)!r} against {again.get(key)!r}" for key in ("status", "failure", "uncertainty_status")
           if kept.get(key) != again.get(key)]
    a, b = kept.get("ln_likelihood"), again.get("ln_likelihood")
    if (a is None) != (b is None) or (a is not None and not _within(a, b, TOLERANCES["ln_likelihood"])):
        out.append(f"{where}: ln L {a!r} against {b!r}")
    if out:
        return out
    if h2:
        kept_sources, again_sources = kept["sources"], again["sources"]
        if (kept_sources is None) != (again_sources is None):
            return [f"{where}: a point on one side only"]
        if kept_sources is None:
            return []
    else:
        if (kept["vertex"] is None) != (again["vertex"] is None):
            return [f"{where}: a point on one side only"]
        if kept["vertex"] is None:
            return []
        kept_sources, again_sources = ([{**fit, "frame": fit["frame"] or {"e1": [0, 0, 0], "e2": [0, 0, 0]}}] for fit in (kept, again))
    covariance = kept["covariance"] if kept["uncertainty_status"] == "ok" else None
    return _parameter_differences(where, kept_sources, again_sources, covariance)


def compare_products(kept_text: str, again_text: str, h1_sha256: tuple | None = None) -> list:
    """Check 9 off the recording's platform: the differences between a recorded /3 or /4 and the recipe's rerun beyond TOLERANCES
    (docstring); an empty list when the rerun reproduces the recorded product. h1_sha256, for a /4: the SHA-256 of the recorded /3
    and of the rerun's own /3. Off the platform the rerun's /3 differs in its last bits, so the rerun's /4 names another /3: each
    /4 header must name its own side's /3, and the rest of the header is equal (CI fix round, PR #411)."""
    kept, again = ([json.loads(line) for line in text.splitlines()] for text in (kept_text, again_text))
    if len(kept) != len(again):
        return [f"{len(kept)} lines recorded, {len(again)} rerun"]
    out = []
    headers = [kept[0], again[0]]
    if h1_sha256 is not None:
        named = [(header.get("h1_product") or {}).get("sha256") for header in headers]
        if named != list(h1_sha256):
            out.append("the header does not name its own multistart product")
        headers = [{**header, "h1_product": {**(header.get("h1_product") or {}), "sha256": None}} for header in headers]
    if headers[0] != headers[1]:
        out.append("the header differs")
    if kept[-1] != again[-1]:
        out.append("the end line differs")
    for a, b in zip(kept[1:-1], again[1:-1]):
        where = f"event {a.get('event')}"
        for key in ("event", "states", "counts", "hits"):
            if a.get(key) != b.get(key):
                out.append(f"{where}: {key} differs")
        if a["choice"]["chosen"] != b["choice"]["chosen"]:
            out.append(f"{where}: chosen start {a['choice']['chosen']} against {b['choice']['chosen']}")
        if a["probability_check"]["failures"] != b["probability_check"]["failures"]:
            out.append(f"{where}: probability failures differ")
        out += _fit_differences(f"{where} H1 fit", a["fit"], b["fit"], False)
        if "topology" in a or "topology" in b:
            ta, tb = a.get("topology") or {}, b.get("topology") or {}
            for key in ("choice", "ln_likelihood_2_from", "penalty"):
                if ta.get(key) != tb.get(key):
                    out.append(f"{where}: topology {key} {ta.get(key)!r} against {tb.get(key)!r}")
            for key, tolerance in (("ln_likelihood_1", TOLERANCES["ln_likelihood"]), ("ln_likelihood_2", TOLERANCES["ln_likelihood"]),
                                   ("statistic", TOLERANCES["statistic"])):
                if not _within(ta.get(key), tb.get(key), tolerance):
                    out.append(f"{where}: topology {key} {ta.get(key)!r} against {tb.get(key)!r}")
            check_a, check_b = ta.get("probability_check"), tb.get("probability_check")
            if (check_a or {}).get("failures") != (check_b or {}).get("failures"):
                out.append(f"{where}: H2's probability failures differ")
            h2a, h2b = ta.get("h2"), tb.get("h2")
            if (h2a is None) != (h2b is None):
                out.append(f"{where}: an H2 record on one side only")
            elif h2a is not None:
                if ta.get("ln_likelihood_2_from") == "h2" and h2a["reported"]["index"] != h2b["reported"]["index"]:
                    out.append(f"{where}: H2's reported start {h2a['reported']['index']} against {h2b['reported']['index']}")
                out += _fit_differences(f"{where} H2 fit", h2a["fit"], h2b["fit"], True)
    return out


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def outcome(status: str, **fields) -> int:
    """Print this run's JSON and return its exit code, core/status.py's for the status."""
    code = exit_code(status)
    print(json.dumps({"example": "reconstruction-photon-likelihood", "status": status, "exit_code": code, **fields}, sort_keys=True))
    return code


def placeholders(text: str, work: Path) -> str:
    for real, name in ((str(work.resolve()), "<work>"), (str(work), "<work>"), (str(PLUGIN), "<plugin>"), (sys.executable, "<python>")):
        text = text.replace(real, name)
    return text


def placeholders_in(value, work: Path):
    """placeholders in every string of a decoded report. Not on its JSON text: json.dumps escapes a non-ASCII or backslashed folder
    name (a folder named with Chinese characters becomes \\u escapes), which then no longer matches (hostile-paths, CI fix round of PR #411)."""
    if isinstance(value, str):
        return placeholders(value, work)
    if isinstance(value, list):
        return [placeholders_in(item, work) for item in value]
    if isinstance(value, dict):
        return {key: placeholders_in(item, work) for key, item in value.items()}
    return value


def product_paths(folder: Path, stem: str) -> tuple:
    return folder / f"{stem}.multistart.product", folder / f"{stem}.topology.product"


def recipe_arguments(folder: Path, stem: str) -> dict:
    """The recipe's arguments of one sample, by operation: the readout and the recipe's own products, never a truth file."""
    readout, (h1, h2) = folder / f"{stem}.readout", product_paths(folder, stem)
    return {"fit": ["fit", "--readout", str(readout), "--product", str(h1), "--product-id", f"{PRODUCT_ID}-{stem}-multistart",
                    "--likelihood", "charge-time", "--starts", "multistart"],
            "topology": ["topology", "--readout", str(readout), "--h1-product", str(h1), "--product", str(h2),
                         "--product-id", f"{PRODUCT_ID}-{stem}-topology"],
            "check-product": ["check-product", "--product", str(h2)]}


def run_recipe(arguments: list) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(RECIPE_CLI), *arguments], capture_output=True, text=True, timeout=1800)


def recipe_run(stem: str, arguments: list, work: Path) -> dict:
    finished = run_recipe(arguments)
    try:
        report = json.loads(finished.stdout)
    except ValueError:
        report = {"operation": arguments[0], "status": "error", "reason": f"the recipe wrote no report: {finished.stderr[-500:]}"}
    kept = {key: value for key, value in report.items() if key not in DROPPED_FIELDS}
    kept = json.loads(json.dumps(placeholders_in(kept, work), sort_keys=True))
    kept["sample"] = stem
    kept["exit_code"] = finished.returncode
    kept["command"] = [placeholders(str(token), work) for token in [sys.executable, "-I", "-B", str(RECIPE_CLI), *arguments]]
    return kept


# ---- live: harness, fit, topology, check-product.

def live(generator, generator_sha256, work: Path, recorded: Path) -> int:
    """generator: the frozen module (loaded by the harness, hash checked) or a stand-in with its interface (tests). Returns the exit
    code of core/status.py: 0, or the failed operation's (1 the recipe's probability-sum stop, 2 any other failure)."""
    work.mkdir(parents=True, exist_ok=True)
    runs, files_sha256 = [], {}
    for stem, fixture, stratum, count in SAMPLES:
        try:
            files = fixture_files.stratum_files(generator, fixture, BLOCK, stratum, count, work, stem)
        except fixture_files.FixtureError as exc:            # the harness refused the generator's events (review N4)
            print(json.dumps({"sample": stem, "operation": "generate", "status": "rejected", "reason": str(exc)}), file=sys.stderr)
            return exit_code("rejected")
        files_sha256[stem] = {name: entry["sha256"] for name, entry in sorted(files.items())}
        runs.append({"sample": stem, "operation": "generate", "status": "ok", "exit_code": 0, "harness": "fixture_tools/t09_fixture_files.py",
                     "data_side_files": [f"{stem}.readout"]})
        for operation, arguments in recipe_arguments(work, stem).items():
            runs.append(recipe_run(stem, arguments, work))
            if runs[-1]["exit_code"] != 0 or runs[-1].get("status") != "ok":
                print(json.dumps(runs[-1], indent=1, sort_keys=True), file=sys.stderr)
                return exit_code("failed" if runs[-1].get("status") == "failed" else "error")
    recorded.mkdir(parents=True, exist_ok=True)
    for name in RECORDED_FILES[1:]:
        shutil.copyfile(work / name, recorded / name)
    write_json(recorded / "runs.json", {"generator": generator.GENERATOR, "generator_sha256": generator_sha256, "block": BLOCK,
                                        "platform": current_platform(),
                                        "samples": [{"sample": stem, "fixture": fixture, "stratum": stratum, "events": count}
                                                    for stem, fixture, stratum, count in SAMPLES],
                                        "files_sha256": files_sha256, "runs": runs})
    return 0


# ---- offline replay.

def rerun_products(recorded: Path, same_platform: bool) -> bool:
    """fit and topology run again on each recorded readout, in a temporary folder: True if every /3 and /4 equals the recorded one byte
    for byte (same_platform), or within TOLERANCES (compare_products)."""
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name)
        for stem, *_ in SAMPLES:
            shutil.copyfile(recorded / f"{stem}.readout", folder / f"{stem}.readout")
            arguments = recipe_arguments(folder, stem)
            for operation in ("fit", "topology"):
                if run_recipe(arguments[operation]).returncode != 0:
                    return False
            (h1_again, h2_again), (h1_kept, h2_kept) = product_paths(folder, stem), product_paths(recorded, stem)
            for again, kept in ((h1_again, h1_kept), (h2_again, h2_kept)):
                if not again.is_file():
                    return False
                if same_platform and again.read_bytes() != kept.read_bytes():
                    return False
            if not same_platform:
                h1_sha256 = (sha256_bytes(h1_kept.read_bytes()), sha256_bytes(h1_again.read_bytes()))
                if compare_products(h1_kept.read_text(encoding="utf-8"), h1_again.read_text(encoding="utf-8")) or \
                        compare_products(h2_kept.read_text(encoding="utf-8"), h2_again.read_text(encoding="utf-8"), h1_sha256):
                    return False
    return True


def replay(recorded: Path) -> tuple:
    from light_recipe import LABEL, RECIPE, configuration, likelihood, multistart, product, topology  # noqa: E402

    runs = json.loads((recorded / "runs.json").read_text(encoding="utf-8"))
    content = {name: (recorded / name).read_bytes() for name in RECORDED_FILES}
    cfg, budget, topology_budget = configuration.load(), multistart.load(), topology.load()
    model = likelihood.Model(cfg)
    read, refusals = {}, {}
    for stem, *_ in SAMPLES:
        for kind in ("multistart", "topology"):
            want = product.FORMAT_MULTISTART if kind == "multistart" else product.FORMAT_TOPOLOGY
            try:
                got = product.read_text(content[f"{stem}.{kind}.product"].decode("utf-8"), model, cfg, budget, topology_budget)
            except (product.ProductError, UnicodeDecodeError) as exc:
                refusals[f"{stem}.{kind}.product"] = str(exc)
                continue
            if got.header["format"] != want:
                refusals[f"{stem}.{kind}.product"] = f"{got.header['format']}, not {want}"
                continue
            read[stem, kind] = got
    whole = not refusals
    recipe_commands = [token for run in runs["runs"] if run["operation"] != "generate" for token in run.get("command", [])]
    names, carried, sums, rule = [], [], [], []
    if whole:
        for stem, *_ in SAMPLES:
            h1, h2 = read[stem, "multistart"], read[stem, "topology"]
            names.append(h1.header["input"]["sha256"] == sha256_bytes(content[f"{stem}.readout"]) == runs["files_sha256"][stem]["readout"]
                         and h2.header["input"]["sha256"] == h1.header["input"]["sha256"]
                         and h2.header["h1_product"]["sha256"] == sha256_bytes(content[f"{stem}.multistart.product"]))
            carried.append(len(h1.events) == len(h2.events) and all({k: v for k, v in b.items() if k != "topology"} == a
                                                                     for a, b in zip(h1.events, h2.events)))
            for doc in h2.events:
                h2_check = doc["topology"].get("probability_check")
                sums.append(doc["probability_check"]["failures"] == 0 and (h2_check is None or h2_check["failures"] == 0))
                top = doc["topology"]
                statistic = 2.0 * (top["ln_likelihood_2"] - top["ln_likelihood_1"])
                rule.append(top["penalty"] == topology.PENALTY and abs(statistic - top["statistic"]) <= 1e-9 * max(1.0, abs(statistic))
                            and top["choice"] == ("H2" if top["statistic"] >= topology.PENALTY else "H1"))
    checks_run = [
        [(run["sample"], run["operation"]) for run in runs["runs"]] == [(stem, op) for stem, *_ in SAMPLES for op in OPERATIONS]
        and all(run["status"] == "ok" and run["exit_code"] == 0 for run in runs["runs"]),
        not any("truth" in token for token in recipe_commands),
        whole and all(names),
        whole and all(r.header["configuration"]["sha256"] == cfg.sha256 and r.header["budget"]["sha256"] == budget.sha256 for r in read.values())
        and all(read[stem, "topology"].header["topology"]["sha256"] == topology_budget.sha256 for stem, *_ in SAMPLES),
        whole and all((r.header["format"], r.header["recipe"], r.header["label"]) == (fmt, RECIPE, LABEL)
                      for (stem, kind), r in read.items() for fmt in [product.FORMAT_MULTISTART if kind == "multistart" else product.FORMAT_TOPOLOGY]),
        whole and all(carried),
        whole and all(sums) and all(run.get("probability_failures") == 0 for run in runs["runs"] if run["operation"] != "generate"),
        whole and all(rule),
    ]
    rerun_ran = all(checks_run)
    same_platform = runs.get("platform") == current_platform()
    checks_run.append(rerun_ran and rerun_products(recorded, same_platform))
    events = []
    for stem, *_ in SAMPLES:
        for doc in (read[stem, "topology"].events if whole else []):
            top = doc["topology"]
            events.append({"sample": stem, "event": doc["event"], "fit_status": doc["fit"]["status"], "hit_channels": doc["counts"]["hit"],
                           "dead_channels": doc["counts"]["dead"], "saturated_channels": doc["counts"]["saturated"],
                           "converged_h1_starts": sum(s["status"] == "converged" for s in doc["starts"]),
                           "ln_likelihood_1": round(top["ln_likelihood_1"], 6), "ln_likelihood_2": round(top["ln_likelihood_2"], 6),
                           "ln_likelihood_2_from": top["ln_likelihood_2_from"], "statistic": round(top["statistic"], 6), "choice": top["choice"]})
    header = read["main", "topology"].header if whole else {}
    summary = {
        "example": "reconstruction-photon-likelihood", "data": "synthetic", "label": header.get("label"),
        "quality_claim": "none: fits the programs wrote, not a resolution, a wrong-minimum rate or a mis-ID rate (K09 at Freeze B)",
        "generator": runs["generator"], "generator_sha256": runs["generator_sha256"], "block": runs["block"], "samples": runs["samples"],
        "files_sha256": runs["files_sha256"], "recipe": header.get("recipe"), "product_format": header.get("format"),
        "configuration_sha256": cfg.sha256, "multistart_budget_sha256": budget.sha256, "topology_budget_sha256": topology_budget.sha256,
        "penalty": topology.PENALTY, "product_refused": refusals, "events": events,
        "recorded_sha256": {name: sha256_bytes(body) for name, body in content.items()},
        "checks": [{"check": name, "passed": bool(passed)} for name, passed in zip(CHECKS, checks_run)],
    }
    summary["checks"][-1]["run"] = rerun_ran
    mode = ("byte for byte" if same_platform else "within the tolerances") if rerun_ran else "not run"
    return summary, all(checks_run), mode


def report_text(summary: dict) -> str:
    lines = ["# T09 photon-likelihood example: generate, fit, choose the topology, check (synthetic)", "",
             f"Generator {summary['generator']}, block {summary['block']} (tuning); "
             + "; ".join(f"{s['sample']}: fixture {s['fixture']}, stratum {s['stratum']}, {s['events']} event(s)" for s in summary["samples"])
             + f". Recipe {summary['recipe']} (a development binding), product {summary['product_format']}, penalty {summary['penalty']:g}. "
             f"Label {summary['label']}: the events and the fit share the analytic light model, so this tests the code, not the model. "
             "Synthetic data only. No photon-likelihood quality claim: these are the fits the programs wrote, not a resolution, a "
             "wrong-minimum rate or a mis-ID rate; T09's quality verdict waits for K09 at Freeze B.", "",
             "| Sample | Event | H1 fit | Hit | Dead | Saturated | Converged H1 starts | lnL_1 | lnL_2 (from) | 2 (lnL_2 - lnL_1) | Choice |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in summary["events"]:
        lines.append(f"| {e['sample']} | {e['event']} | {e['fit_status']} | {e['hit_channels']} | {e['dead_channels']} | {e['saturated_channels']} | "
                     f"{e['converged_h1_starts']} | {e['ln_likelihood_1']:.3f} | {e['ln_likelihood_2']:.3f} ({e['ln_likelihood_2_from']}) | "
                     f"{e['statistic']:.3f} | {e['choice']} |")
    lines += ["", "| Check | Result |", "|---|---|"]
    lines += [f"| {item['check']} | {'pass' if item['passed'] else ('not run' if item.get('run') is False else 'FAIL')} |"
              for item in summary["checks"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--out", default=str(HERE / "output"))
    parser.add_argument("--recorded", default=str(HERE / "recorded"))
    parser.add_argument("--live", action="store_true", help="run the harness, fit, topology and check-product, and rewrite --recorded")
    parser.add_argument("--generator", default=os.environ.get("HEP_T09_GENERATOR", ""), help="the frozen gen_t09_sphere.py (live)")
    parser.add_argument("--work", help="work folder of the live run (default: a temporary folder)")
    arguments = parser.parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError as exc:
        return outcome("missing-dependency", reason=f"{exc.name} is not installed")
    recorded, out = Path(arguments.recorded), Path(arguments.out)
    if arguments.live:
        if not arguments.generator:
            return outcome("rejected", reason="the live mode needs the frozen generator: --generator or HEP_T09_GENERATOR")
        try:
            generator = fixture_files.load_generator(arguments.generator)
        except fixture_files.FixtureError as exc:
            return outcome("rejected", reason=f"the generator is refused: {exc}")
        with tempfile.TemporaryDirectory() as temporary:
            code = live(generator, FROZEN_GENERATOR_SHA256, Path(arguments.work) if arguments.work else Path(temporary), recorded)
        if code != 0:
            return outcome("failed" if code == exit_code("failed") else "error", reason="a live operation did not end ok (stderr)")
    missing = [name for name in RECORDED_FILES if not (recorded / name).is_file()]
    if missing:
        return outcome("rejected", reason=f"no recorded run in {recorded}: missing {', '.join(missing)}; the live mode (--live) writes it")
    summary, passed, mode = replay(recorded)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "summary.json", summary)
    (out / "report.md").write_text(report_text(summary), encoding="utf-8")
    return outcome("ok" if passed else "failed", checks_passed=sum(item["passed"] for item in summary["checks"]), checks=len(summary["checks"]),
                   check_9=mode, out=str(out))


if __name__ == "__main__":
    sys.exit(main())
