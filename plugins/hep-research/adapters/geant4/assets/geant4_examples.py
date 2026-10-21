#!/usr/bin/env python3
"""Build and run four official Geant4 examples and compare them with the upstream reference outputs (WP1 M1).

Purpose: verification of an installation, not validation of physics. B1, TestEm3 run 0 and TestEm5 (five runs) are
compared statistically, each quantity with its own standard error; B4a gets a smoke comparison only. The reference
outputs ship with the Geant4 source (<example>/<name>.out) and were produced by a Geant4 test build in serial mode
with FPE detection, so local results agree only statistically, never bit for bit.

What each printed "rms" or "+-" means (Geant4 11.4.3 sources; extractors follow the actual .out format):
- B1 (basic/B1/src/RunAction.cc): "rms" is sqrt(sum E^2 - (sum E)^2/N) / mass, the standard deviation of the run
  total, which grows as sqrt(N); the total dose is compared with SE = rms.
- TestEm3 run 0 (Run.cc): the value after the Edep and track-length columns is the single-event RMS; SE = RMS/sqrt(N);
  the RMS itself is compared with SE = RMS/sqrt(2N) (Gaussian approximation); the "+- x %" of the resolution column
  is the resolution divided by sqrt(N), not a standard error, and the resolution is not compared separately (it is the
  RMS over the mean). Edep and Eleak are anti-correlated (their sum is the beam energy), so they are one test. Run 1
  uses secondary biasing (the deposit is weighted, the leakage is not) and is not compared.
- TestEm5 (Run.cc): the "+-" after deposit, leakage, track length and steps is the error on the mean; the transmitted
  and reflected percentages get SE = sqrt(p(1-p)/N); "rms proj angle" has no uncertainty and is reference-only.
- Printed values are rounded: each standard error is combined with the rounding of the printed value, a uniform
  error of one unit in the last significant digit, at the precision the example's Run.cc sets for that field
  (TestEm3: Edep 5, RMS 4, track length 3, total 4 digits; TestEm5 4; B1 6), or the digits shown if more.
- B4a: three runs of one event each; histogram means count in-range entries only, so values are not compared: the
  smoke test checks that three runs complete and that the material table and the physics-list name match.

Comparison rule (declared before any run, written into every table): z = (local - reference) / sqrt(SE_local^2 +
SE_ref^2); family-wise alpha (default 0.05) with a Bonferroni threshold z_crit = Phi^-1(1 - alpha / (2 m)) over the m
compared quantities of all examples together. A quantity beyond z_crit is rerun with another seed and the rerun is
pooled with the original (inverse-variance weighted mean; counts pooled for fractions), never substituted.

Subcommands:
  build    configure and build the examples against the installation of a build record
  run      run one example unchanged through a wrapper macro (/random/setSeeds, then /control/execute <name>.in),
           always serial (G4FORCE_RUN_MANAGER_TYPE=Serial), and write a computational-run record of the run;
           --run0-events N runs only the commands up to the first /run/beamOn, with N events (mirror reference)
  extract  quantities of a .out file, tagged by Geant4 run ID
  compare  local outputs against the references -> comparison table JSON (with pooled reruns)
  smoke    the B4a smoke comparison
Usage (from the plugin root):
  python3 adapters/geant4/assets/geant4_examples.py build --build-record BUILD.json --work DIR
  python3 adapters/geant4/assets/geant4_examples.py run --build-record BUILD.json --work DIR --example NAME --seeds A B --tag T --record OUT.json
  python3 adapters/geant4/assets/geant4_examples.py extract --example NAME --out-file FILE.out
  python3 adapters/geant4/assets/geant4_examples.py compare --source SRC --local NAME=FILE[,RERUN] ... [--alpha 0.05] --out TABLE.json
  python3 adapters/geant4/assets/geant4_examples.py smoke --source SRC --local FILE.out
Every subcommand takes --status LABEL (default unvalidated), echoed as status_label.
Exit codes: 0 ok (every comparison within the threshold after pooling); 1 a comparison failed or a run failed; 2 bad
input; 3 cmake or the installation missing. Standard library only.
"""
from __future__ import annotations

import datetime
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4common import (JsonArgumentParser, SpecError, UNITS, build_record_ok, data_env, expand,  # noqa: E402
                      install_prefix, record_skeleton, sha256_file, tilde, write_json)
from core.status import add_status_argument, exit_code  # noqa: E402

EXAMPLES = {  # name: (folder under examples/, executable, macro, reference output, macro flag, declared precision)
    "B1": ("basic/B1", "exampleB1", "exampleB1.in", "exampleB1.out", None, 6),
    "B4a": ("basic/B4/B4a", "exampleB4a", "exampleB4.in", "exampleB4a.out", "-m", 6),
    "TestEm3": ("extended/electromagnetic/TestEm3", "TestEm3", "TestEm3.in", "TestEm3.out", None, 4),
    "TestEm5": ("extended/electromagnetic/TestEm5", "TestEm5", "TestEm5.in", "TestEm5.out", None, 4),
}
NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
QTY = rf"({NUM})\s*([A-Za-z]+)"
RULE = ("z = (local - reference) / sqrt(SE_local^2 + SE_ref^2), each SE combined with the rounding of its printed "
        "value (fractions: two-proportion test with the pooled fraction); a value printed as zero with zero error is not "
        "tested; Bonferroni threshold over all compared quantities; an exceedance is rerun with another seed and pooled")


def _q(value: str, unit: str, category: str) -> float:
    if unit not in UNITS[category]:
        raise ValueError(f"unknown {category} unit {unit!r}")
    return float(value) * UNITS[category][unit]


def rounding_se(text_value: str, factor: float, declared: int) -> float:
    """SE of the rounding of a printed value: one unit in the last significant digit, uniform (unit / sqrt(12))."""
    digits = re.sub(r"[eE].*", "", text_value).lstrip("+-").replace(".", "").lstrip("0")
    shown = max(len(digits), 1)
    x = abs(float(text_value))
    if x == 0:
        return 0.0
    unit = 10 ** (math.floor(math.log10(x)) - max(shown, declared) + 1)
    return unit * factor / math.sqrt(12)


def split_runs(text: str) -> dict[int, str]:
    parts = re.split(r"^### Run (\d+) starts\.", text, flags=re.M)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def extract_b1(text: str) -> list[dict]:
    out = []
    blocks = text.split("--------------------End of Global Run-----------------------")[1:]
    for run_id, b in enumerate(blocks):
        m = re.search(r"The run is (\d+) (\S+) of ([^\n]+)", b)
        d = re.search(rf"edep/mass = {QTY}\s*;?\s*rms = {QTY}", b)  # reference .out: "  rms ="; source: "; rms ="
        if not (m and d):
            raise ValueError(f"B1 run {run_id}: summary lines not found")
        n = int(m.group(1))
        f = UNITS["dose"][d.group(2)]
        val, rms = _q(d.group(1), d.group(2), "dose"), _q(d.group(3), d.group(4), "dose")
        out.append({"run": run_id, "quantity": "dose_total_Gy", "value": val, "n": n,
                    "se": math.hypot(rms, rounding_se(d.group(1), f, 6)),
                    "se_formula": "rms printed (SD of the run total) combined with rounding", "compared": True,
                    "condition": f"{n} {m.group(2)} of {m.group(3).strip()}"})
    return out


def extract_testem3(text: str) -> list[dict]:
    runs = split_runs(text)
    out = []
    for run_id, b in runs.items():
        nm = re.search(r"Number of events processed : (\d+)", b)
        if not nm:
            continue
        n = int(nm.group(1))
        compared = run_id == 0
        why = None if compared else "secondary biasing: deposit weighted, leakage not (energy balance fails)"
        rows = re.findall(rf"^\s*(\S+): {QTY}\s*:\s*{QTY}\s+({NUM}) \+- ({NUM}) %\s+{QTY}\s+\+- {QTY}", b, re.M)
        for mat, ev, eu, rv, ru, res, _res_err, lv, lu, lrv, lru in rows:
            fe, fl = UNITS["energy"][eu], UNITS["length"][lu]
            rms = _q(rv, ru, "energy")
            lrms = _q(lrv, lru, "length")
            out += [
                {"run": run_id, "quantity": f"edep_{mat}_MeV", "value": _q(ev, eu, "energy"), "n": n,
                 "se": math.hypot(rms / math.sqrt(n), rounding_se(ev, fe, 5)), "se_formula": "RMS/sqrt(N) (+) rounding",
                 "compared": compared, "not_compared_reason": why},
                {"run": run_id, "quantity": f"edep_rms_{mat}_MeV", "value": rms, "n": n,
                 "se": math.hypot(rms / math.sqrt(2 * n), rounding_se(rv, UNITS["energy"][ru], 4)),
                 "se_formula": "RMS/sqrt(2N) (Gaussian) (+) rounding", "compared": compared,
                 "not_compared_reason": why},
                {"run": run_id, "quantity": f"tracklen_{mat}_mm", "value": _q(lv, lu, "length"), "n": n,
                 "se": math.hypot(lrms / math.sqrt(n), rounding_se(lv, fl, 3)), "se_formula": "RMS/sqrt(N) (+) rounding",
                 "compared": compared, "not_compared_reason": why},
                {"run": run_id, "quantity": f"resolution_{mat}_percent", "value": float(res), "n": n, "se": None,
                 "se_formula": "printed '+-' is resolution/sqrt(N), not a standard error", "compared": False,
                 "not_compared_reason": "RMS over mean: the RMS and the mean are compared instead"}]
        t = re.search(rf"Total energy deposited = {QTY} \+- {QTY}", b)
        if t:
            rms = _q(t.group(3), t.group(4), "energy")
            out.append({"run": run_id, "quantity": "edep_total_MeV", "value": _q(t.group(1), t.group(2), "energy"),
                        "n": n, "se": math.hypot(rms / math.sqrt(n), rounding_se(t.group(1), UNITS["energy"][t.group(2)], 4)),
                        "se_formula": "RMS/sqrt(N) (+) rounding", "compared": compared, "not_compared_reason": why})
        lk = re.search(rf"Energy leakage = {QTY} \+- {QTY}", b)
        if lk:
            out.append({"run": run_id, "quantity": "eleak_MeV", "value": _q(lk.group(1), lk.group(2), "energy"), "n": n,
                        "se": None, "se_formula": "RMS/sqrt(N)", "compared": False,
                        "not_compared_reason": "anti-correlated with edep_total (sum = beam energy): one test"})
        for part, cnt in re.findall(rf"Mean number of (gamma|e-|e\+)\s+({NUM})", b):
            out.append({"run": run_id, "quantity": f"mean_number_{part}", "value": float(cnt), "n": n, "se": None,
                        "se_formula": "no uncertainty printed", "compared": False,
                        "not_compared_reason": "reference only (no uncertainty printed)"})
    return out


def extract_testem5(text: str) -> list[dict]:
    out = []
    pat = {
        "edep_MeV": (rf"Total energy deposit in absorber per event = {QTY} \+- {QTY}", "energy"),
        "leak_primary_MeV": (rf"Leakage :\s+primary = {QTY} \+- {QTY}", "energy"),
        "leak_secondaries_MeV": (rf"secondaries = {QTY} \+- {QTY}", "energy"),
        "tracklen_charged_mm": (rf"Total track length \(charged\) in absorber per event = {QTY}\s+\+- {QTY}", "length"),
        "tracklen_neutral_mm": (rf"Total track length \(neutral\) in absorber per event = {QTY}\s+\+- {QTY}", "length"),
    }
    for run_id, b in split_runs(text).items():
        nm = re.search(r"The run was (\d+) (\S+) of ([^\n]+?) through ([^\n]+)", b)
        if not nm:
            continue
        n = int(nm.group(1))
        cond = f"{nm.group(2)} {nm.group(3)} through {nm.group(4).strip()}"
        for q, (rx, cat) in pat.items():
            m = re.search(rx, b)
            if m:
                f = UNITS[cat][m.group(2)]
                out.append({"run": run_id, "quantity": q, "value": _q(m.group(1), m.group(2), cat), "n": n,
                            "se": math.hypot(_q(m.group(3), m.group(4), cat), rounding_se(m.group(1), f, 4)),
                            "se_formula": "printed error on the mean (+) rounding", "compared": True,
                            "condition": cond})
        for q, rx in (("steps_charged", r"Number of steps \(charged\) in absorber per event = "),
                      ("steps_neutral", r"Number of steps \(neutral\) in absorber per event = ")):
            m = re.search(rf"{rx}({NUM}) \+- ({NUM})", b)
            if m:
                out.append({"run": run_id, "quantity": q, "value": float(m.group(1)), "n": n,
                            "se": math.hypot(float(m.group(2)), rounding_se(m.group(1), 1.0, 4)),
                            "se_formula": "printed error on the mean (+) rounding", "compared": True, "condition": cond})
        for q, rx in (("transmitted_fraction", r"primary particle transmitted = "),
                      ("reflected_fraction", r"primary particle reflected = ")):
            m = re.search(rf"{rx}({NUM}) %", b)
            if m:
                p = float(m.group(1)) / 100
                out.append({"run": run_id, "quantity": q, "value": p, "n": n,
                            "se": math.hypot(math.sqrt(max(p * (1 - p), 0) / n), rounding_se(m.group(1), 0.01, 4)),
                            "se_formula": "sqrt(p(1-p)/N) (+) rounding", "compared": True, "condition": cond})
        m = re.search(rf"rms proj angle of transmit primary particle = {QTY}", b)
        if m:
            out.append({"run": run_id, "quantity": "rms_proj_angle_rad", "value": _q(m.group(1), m.group(2), "angle"),
                        "n": n, "se": None, "se_formula": "no uncertainty printed (RMS within +-3 theta0)",
                        "compared": False, "not_compared_reason": "reference only", "condition": cond})
    return out


EXTRACTORS = {"B1": extract_b1, "TestEm3": extract_testem3, "TestEm5": extract_testem5}


def pool(rows: list[dict]) -> dict:
    """Inverse-variance pooled local value of several runs of one quantity (counts pooled for fractions)."""
    if rows[0]["quantity"].endswith("_fraction"):
        n = sum(r["n"] for r in rows)
        p = sum(r["value"] * r["n"] for r in rows) / n
        return {"value": p, "se": math.sqrt(max(p * (1 - p), 0) / n), "n": n}
    if any(not r["se"] for r in rows):
        return {"value": statistics.fmean(r["value"] for r in rows), "se": 0.0, "n": sum(r["n"] for r in rows)}
    w = [1 / r["se"] ** 2 for r in rows]
    return {"value": sum(wi * r["value"] for wi, r in zip(w, rows)) / sum(w), "se": 1 / math.sqrt(sum(w)),
            "n": sum(r["n"] for r in rows)}


def compare(local: dict[str, list[Path]], source: Path, alpha: float) -> tuple[str, dict]:
    tables, keyed = {}, []
    for name, files in local.items():
        if name not in EXTRACTORS:
            raise SpecError(f"{name}: compare takes B1, TestEm3 or TestEm5 (B4a has the smoke subcommand)")
        folder, _, _, ref_name, _, _ = EXAMPLES[name]
        ref = {(r["run"], r["quantity"]): r for r in EXTRACTORS[name]((source / "examples" / folder / ref_name)
                                                                      .read_text(encoding="utf-8", errors="replace"))}
        runs = [{(r["run"], r["quantity"]): r for r in EXTRACTORS[name](f.read_text(encoding="utf-8", errors="replace"))}
                for f in files]
        for key, r in sorted(ref.items()):
            if r["compared"] and not r["se"] and not key[1].endswith("_fraction"):
                r.update(compared=False, not_compared_reason="printed with zero uncertainty: no statistical test")
            if r["compared"] and all(key in lr for lr in runs):
                keyed.append((name, key, r, [lr[key] for lr in runs]))
        tables[name] = {"reference": tilde(source / "examples" / folder / ref_name),
                        "local_outputs": [tilde(f) for f in files],
                        "not_compared": [{"run": k[0], "quantity": k[1], "reason": r.get("not_compared_reason")}
                                         for k, r in sorted(ref.items()) if not r["compared"]],
                        "rows": []}
    m = len(keyed)
    if m == 0:
        raise SpecError("no comparable quantities found")
    z_crit = statistics.NormalDist().inv_cdf(1 - alpha / (2 * m))
    exceed = []
    def z_of(loc_value, loc_se, loc_n, q):
        if q.endswith("_fraction"):  # two-proportion test with the pooled fraction
            pp = (loc_value * loc_n + r["value"] * r["n"]) / (loc_n + r["n"])
            se = math.sqrt(max(pp * (1 - pp), 0) * (1 / loc_n + 1 / r["n"]))
        else:
            se = math.hypot(loc_se or 0, r["se"] or 0)
        return (loc_value - r["value"]) / se if se > 0 else 0.0

    for name, (run_id, q), r, lrs in keyed:
        first = lrs[0]
        z1 = z_of(first["value"], first["se"], first["n"], q)
        row = {"run": run_id, "quantity": q, "condition": r.get("condition"), "reference": r["value"],
               "se_reference": r["se"], "local": first["value"], "se_local": first["se"],
               "se_formula": r["se_formula"], "z": z1, "z_crit": z_crit, "verdict": "pass" if abs(z1) <= z_crit else "exceeds"}
        if len(lrs) > 1:
            pl = pool(lrs)
            zp = z_of(pl["value"], pl["se"], pl["n"], q)
            row.update(pooled={"local": pl["value"], "se_local": pl["se"], "n": pl["n"], "z": zp,
                               "runs": len(lrs)}, verdict="pass" if abs(zp) <= z_crit else "fail")
        elif row["verdict"] == "exceeds":
            row["verdict"] = "rerun-required"
        if row["verdict"] != "pass":
            exceed.append(f"{name} run {run_id} {q}")
        tables[name]["rows"].append(row)
    verdicts = [x["verdict"] for t in tables.values() for x in t["rows"]]
    status = "failed" if "fail" in verdicts else "rerun-required" if "rerun-required" in verdicts else "ok"
    return status, {"rule": RULE, "alpha_family": alpha, "m_compared": m, "z_crit": z_crit,
                    "expected_exceedances_without_correction": round(m * alpha, 3),
                    "not_passing": exceed, "examples": tables}


def smoke_b4a(local: Path, source: Path) -> tuple[str, dict]:
    folder, _, _, ref_name, _, _ = EXAMPLES["B4a"]
    ref = (source / "examples" / folder / ref_name).read_text(encoding="utf-8", errors="replace")
    loc = local.read_text(encoding="utf-8", errors="replace")

    def materials(t):
        return [re.sub(r"\s+", " ", ln.strip()) for ln in t.splitlines() if ln.strip().startswith("Material:")]

    def physics(t):
        m = re.search(r"Geant4 Physics List simulation engine: (\S+)", t)
        return m.group(1) if m else None
    runs = len(re.findall(r"^### Run \d+ starts\.", loc, re.M))
    ends = len(re.findall(r"^\s*EAbs : mean =", loc, re.M))  # B4a RunAction prints its histogram summary per run
    checks = {"three_runs_started": runs == 3, "three_runs_ended": ends == 3,
              "material_table_matches": materials(loc) == materials(ref) and bool(materials(ref)),
              "physics_list_matches": physics(loc) == physics(ref) == "FTFP_BERT"}
    return ("ok" if all(checks.values()) else "failed"), {
        "checks": checks, "runs_started": runs, "runs_ended": ends, "physics_list": physics(loc),
        "note": "smoke only: B4a runs one event per run and its histogram means count in-range entries only"}


def _build(args) -> dict:
    rec = json.loads(expand(str(args.build_record)).read_text(encoding="utf-8"))
    why = build_record_ok(rec)
    if why:
        raise SpecError(f"--build-record: {why}")
    return rec


def source_dir(rec: dict) -> Path:
    return expand(rec["extension"]["environment"]["work"]) / "src"


def cmd_build(args) -> tuple[str, dict]:
    rec = _build(args)
    if not shutil.which("cmake"):
        return "missing-dependency", {"error": "cmake not found on PATH"}
    g4dir = install_prefix(rec) / "lib" / "cmake" / "Geant4"
    if not g4dir.is_dir():
        return "missing-dependency", {"error": f"no Geant4 CMake configuration at {tilde(g4dir)}"}
    work, src = expand(str(args.work)), source_dir(rec)
    built = {}
    for name in args.examples:
        folder, exe, *_ = EXAMPLES[name]
        bld = work / "examples" / name / "build"
        bld.mkdir(parents=True, exist_ok=True)
        with (bld / "build.log").open("w", encoding="utf-8") as fh:
            codes = [subprocess.run(c, stdout=fh, stderr=subprocess.STDOUT, timeout=3600).returncode for c in (
                ["cmake", "-S", str(src / "examples" / folder), "-B", str(bld), f"-DGeant4_DIR={g4dir}",
                 "-DCMAKE_BUILD_TYPE=Release"], ["cmake", "--build", str(bld), "--parallel", str(args.jobs)])]
        built[name] = {"exe": tilde(bld / exe), "ok": not any(codes) and (bld / exe).is_file()}
    return ("ok" if all(b["ok"] for b in built.values()) else "failed"), {"examples": built}


def cmd_run(args) -> tuple[str, dict]:
    rec = _build(args)
    folder, exe_name, macro, _, flag, _ = EXAMPLES[args.example]
    bld = expand(str(args.work)) / "examples" / args.example / "build"
    exe = bld / exe_name
    if not exe.is_file():
        return "missing-dependency", {"error": f"{tilde(exe)} not built (run the build subcommand)"}
    wrapper = bld / f"wrapper-{args.tag}.mac"
    if args.run0_events:
        # mirror reference: the example's own commands up to its first /run/beamOn, with the event count replaced
        lines, body = (bld / macro).read_text(encoding="utf-8").splitlines(), []
        for ln in lines:
            if ln.strip().startswith("/run/beamOn"):
                body.append(f"/run/beamOn {args.run0_events}")
                break
            body.append(ln)
        else:
            raise SpecError(f"{macro} has no /run/beamOn")
        run0 = bld / f"run0-{args.tag}.mac"
        run0.write_text("\n".join(body) + "\n", encoding="utf-8")
        macro = run0.name
    wrapper.write_text(f"/random/setSeeds {args.seeds[0]} {args.seeds[1]}\n/control/execute {macro}\n",
                       encoding="utf-8")
    out = bld / f"local-{args.tag}.out"
    env = data_env(rec)
    env["G4FORCE_RUN_MANAGER_TYPE"] = "Serial"
    cmd = [str(exe)] + ([flag] if flag else []) + [wrapper.name]
    with out.open("w", encoding="utf-8") as fh:
        p = subprocess.run(cmd, cwd=bld, stdout=fh, stderr=subprocess.STDOUT, env=env, timeout=args.timeout)
    ok = p.returncode == 0
    created = args.created or datetime.date.today().isoformat()
    b = rec["extension"]["build"]
    run_rec = record_skeleton(f"geant4-example-{args.example}-{args.tag}",
                              f"Geant4 {b['tag']} official example {args.example} run unchanged in serial mode "
                              f"(verification of the installation, not validation)", created,
                              ["unvalidated"] if ok else ["unvalidated", "failed"])
    run_rec["extension"] = {
        "input_manifest": [{"path": f"geant4@{b['commit']}/examples/{folder}/{EXAMPLES[args.example][2]}",
                            "sha256": sha256_file(source_dir(rec) / "examples" / folder / EXAMPLES[args.example][2])},
                           {"path": tilde(bld / macro), "sha256": sha256_file(bld / macro)},
                           {"path": tilde(wrapper), "sha256": sha256_file(wrapper)}],
        "tools": [{"name": "Geant4", "version": f"{b['tag']} ({b['commit']})"},
                  {"name": exe_name, "version": sha256_file(exe)[:16]}],
        "commands": [f"G4FORCE_RUN_MANAGER_TYPE=Serial {' '.join(cmd)}"],
        "environment": {"G4FORCE_RUN_MANAGER_TYPE": "Serial",
                        "dataset_variables": {d["envvar"]: d["path"] for d in b["datasets"]}},
        "seeds": {"random_setSeeds": args.seeds}, "tolerances": {}, "exit_status": p.returncode,
        "output_hashes": {tilde(out): sha256_file(out)}}
    write_json(expand(str(args.record)), run_rec)
    return ("ok" if ok else "failed"), {"out": tilde(out), "exit": p.returncode, "record": tilde(expand(str(args.record)))}


def cmd_extract(args) -> tuple[str, dict]:
    if args.example not in EXTRACTORS:
        raise SpecError("extract takes B1, TestEm3 or TestEm5")
    text = expand(str(args.out_file)).read_text(encoding="utf-8", errors="replace")
    rows = EXTRACTORS[args.example](text)
    if not rows:
        raise SpecError(f"no {args.example} summary found in {args.out_file}")
    return "ok", {"example": args.example, "quantities": rows}


def cmd_compare(args) -> tuple[str, dict]:
    local = {}
    for item in args.local_files:
        name, _, files = item.partition("=")
        if not files:
            raise SpecError("--local takes NAME=FILE[,RERUN...]")
        paths = [expand(f) for f in files.split(",")]
        for p in paths:
            if not p.is_file():
                raise FileNotFoundError(f"{p} not found")
        local[name] = paths
    status, table = compare(local, expand(str(args.source)), args.alpha)
    if args.out:
        write_json(expand(str(args.out)), {"status": status, **table})
    return status, table


def cmd_smoke(args) -> tuple[str, dict]:
    p = expand(str(args.local_file))
    if not p.is_file():
        raise FileNotFoundError(f"{p} not found")
    return smoke_b4a(p, expand(str(args.source)))


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build", help="build the examples")
    p.add_argument("--build-record", required=True)
    p.add_argument("--work", required=True)
    p.add_argument("--examples", nargs="+", default=list(EXAMPLES), choices=list(EXAMPLES))
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    p = sub.add_parser("run", help="run one example through a wrapper macro (serial)")
    p.add_argument("--build-record", required=True)
    p.add_argument("--work", required=True)
    p.add_argument("--example", required=True, choices=list(EXAMPLES))
    p.add_argument("--seeds", type=int, nargs=2, required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--record", required=True)
    p.add_argument("--created")
    p.add_argument("--timeout", type=float, default=86400.0)
    p.add_argument("--run0-events", type=int,
                   help="run only the example's first run with this many events (the mirror comparison reference)")
    p = sub.add_parser("extract", help="quantities of a .out file")
    p.add_argument("--example", required=True)
    p.add_argument("--out-file", required=True)
    p = sub.add_parser("compare", help="local outputs against the references")
    p.add_argument("--source", required=True, help="the Geant4 source folder (holds examples/)")
    p.add_argument("--local", dest="local_files", action="append", required=True, help="NAME=FILE[,RERUN,...]")
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--out")
    p = sub.add_parser("smoke", help="B4a smoke comparison")
    p.add_argument("--source", required=True)
    p.add_argument("--local", dest="local_file", required=True)
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("examples", "jobs", "alpha", "created", "timeout", "status")
                if hasattr(args, k) and f"--{k}" not in given]
    handlers = {"build": cmd_build, "run": cmd_run, "extract": cmd_extract, "compare": cmd_compare, "smoke": cmd_smoke}
    try:
        status, doc = handlers[args.command](args)
    except (SpecError, FileNotFoundError, KeyError, ValueError, IsADirectoryError) as exc:
        status, doc = "rejected", {"error": str(exc)}
    except (OSError, subprocess.TimeoutExpired) as exc:
        status, doc = "failed", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **doc}, indent=1, default=str))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
