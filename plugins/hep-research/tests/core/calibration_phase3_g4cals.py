"""The Geant4 version of the section 8.7 row 2004 calibration, P6 part (simcal phase 3, WP-L): the false-alarm rate of
P6 with a correct surrogate (v = 0, approval A13) on Geant4-produced observables, the RICH replica
(`ams02-rich-replica`, FTFP_BERT_EMZ with optical physics, g4sim_run build 28). Not a unit test module; no Slurm here
(the main session registers the configuration in the card and submits the arrays).

  python3 calibration_phase3_g4cals.py --cards ROOT              run cards, manifest, check-spec (login host)
  python3 calibration_phase3_g4cals.py --list [--root ROOT]      the task table (Geant4 tasks, then the P6 tasks)
  python3 calibration_phase3_g4cals.py --task K --out DIR [--root ROOT]   one task (Geant4 tasks: conda env `geant4`)
  python3 calibration_phase3_g4cals.py --merge DIR --out FILE [--root ROOT]   merge and judge (exit 0 passed, else 1)
  python3 calibration_phase3_g4cals.py --local --out DIR         the whole path on STAND-IN products (`smoke`)

Design (the toy version's, campaign p3-cals-p6, with Geant4 events; Part B section 8.7 row 2004 and note 4, section
8.2 note 4, A13): per repetition r, at H held-out points of the RICH design box, a FULL simulation and a known-error
SURROGATE that is an independent Geant4 simulation at the same point (weight 1, v = 0: no error beyond MC noise; v = 1
adds an error drawn N(0, V_emu), V_emu = cov_Delta, reported); observables: the mean per-event plane radius
(calibration_phase3_g4.plane_radius, the p3-g4 observable) of the two beta samples R_p100 and R_p2.4, N = 2000 events per
side and sample (the p3-g4 design's events per point); sigma_Delta from the per-event contributions (paired = False);
the pull chi2 (H >= 30) referenced to its exact null distribution under the joint covariance of the held-out points
(A13); P6 at alpha = 0.01 (emulator.p6). H = 32 Sobol points (seed DESIGN_SEED) and H = 8 (the first 8 of them: P6's
|Delta m| part alone, the p3-g4 production's held-back count), 2000 repetitions each. Rule (the toy's, registered for
p3-cals-p6): per configuration with v = 0, P6 failures <= 29 of 2000; v = 1 reported.

Seeds (sections 6.6, 14.1): one seed block per beta sample, S_b = H(simcal-p3g, rich, p6cal, held-out, b, t), shared by
the 32 points (common random numbers across points, one seed per side as in the toy); repetition r takes members 2r
(full) and 2r + 1 (surrogate) of N events: events [2rN, (2r + 1)N) and [(2r + 1)N, (2r + 2)N), the same at every point.
A Geant4 task runs one (sample, point) over a chunk of consecutive repetitions, reduces photons.csv to the per-event
plane radius (plane_radii, equal to calibration_phase3_g4.plane_radius) and deletes photons.csv and conservation.csv
(their SHA-256 recorded). The e-draws of v = 1: default_rng([cal_seed(4, r), j, 3]) (calibration_phase3_cals.cal_seed;
c = 4 is not used by the toy families). Everything is `synthetic` and `provisional-thresholds`.

Cost (2026-11-13, local timing on the login host of one task per sample at 10,000 events, cards preflighted): R_p100
637 CPU s (0.064 s/event), max RSS 1.51 GB for 1.34 M photons.csv rows; R_p2.4 579 CPU s (0.058 s/event), 0.26 GB for
0.21 M rows; the reduction 5.6 s and 0.9 s; the p3-g4 workers ran 0.045 and 0.042 s/event. A registered task: R_p100 5
repetitions = 20,000 events (~2.7 M rows, ~3 GB), R_p2.4 25 = 100,000 events (~2.1 M rows, ~2.3 GB); 15,360 Geant4
tasks, 5.12e8 events, ~6200 core-hours at the workers' rate (~8500 at the login host's); 20 P6 tasks of 100
repetitions, ~0.3 s per repetition."""
from __future__ import annotations

import argparse
import functools
import itertools
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT / "adapters" / "geant4" / "assets"
for _p in (str(ROOT), str(HERE), str(ASSETS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import calibration_phase3_cals as X  # noqa: E402
import calibration_phase3_g4 as G  # noqa: E402
import calibration_rich_fixture as R  # noqa: E402

from core.calibration import design as D  # noqa: E402
from core.calibration import design_g4sim as DG  # noqa: E402
from core.calibration import emulator as EM  # noqa: E402

SERIES = "simcal-p3g"
OUT_ROOT = Path("/ceph/sharedfs/work/AMS/hsinyichou/simcal-p3g")
CAMPAIGN = "rich-p6cal"
SAMPLES = G.RICH_SAMPLES
LABEL = "synthetic"
FLAGS = ["synthetic", "provisional-thresholds"]
DESIGN_SEED = 20261314                   # the 32 held-out points (the toy's P6 design used 20261313)
CAL = 4                                  # seed index c of the v = 1 error draws (toy families use 1-3)
VEMU = X.P6_VEMU                         # (0.0, 1.0)
MAX_FALSE_ALARMS = X.P6_MAX_FALSE_ALARMS          # 29 of 2000 (the registered rule of row 2004)
CONFIG = {"events": 2000,                # N per side and sample (the p3-g4 design's events per point)
          "reps": 2000,                  # repetitions per configuration (the toy's, the rule's 2000)
          "points": 32,                  # held-out points: the pull chi2 needs >= 30 (section 8.1)
          "h_configs": [8, 32],          # H = 8 (|Delta m| only) is the first 8 of the 32 points
          "chunk": {"R_p100": 5, "R_p2.4": 25},        # repetitions per Geant4 task (g4sim's thread merge holds
          "p6_reps": 100}                # every photons.csv row in memory: ~1 kB per row, ~2.8 M rows per task)
# measured rate (p3-g4 production, jobs 7596359/7596402, 2000 events per run, set-up included); local timing in the card
CPU_S_PER_EVENT = {"R_p100": 89.7 / 2000, "R_p2.4": 83.8 / 2000}


@functools.lru_cache(maxsize=1)
def _provenance() -> str:
    return json.dumps(G.provenance())


def provenance() -> dict:
    """calibration_phase3_g4.provenance, once per process (a task, the merge, or the whole --local path)."""
    return json.loads(_provenance())


def _sha(path: Path) -> str:
    return G._sha(path)


def _write(path: Path, value) -> None:
    G._write(path, value)


# ------------------------------------------------------------------ design: points, seeds, tasks
def box() -> dict:
    c = G.rich_contract()
    return {q["name"]: [float(x) for x in q["sampling_bounds"]] for q in c["parameters"]}


def points(cfg: dict = CONFIG) -> list:
    """The held-out points: cfg['points'] scrambled Sobol points of the design box (a power of two; the first 8 are
    themselves a balanced Sobol set, the H = 8 configuration)."""
    return D.sobol_points(box(), int(cfg["points"]), DESIGN_SEED)


def registered_seeds() -> list:
    """The p3-g4 production's seed blocks (ZDC nominal and reference, RICH design per sample): never reused."""
    zs = [s for s, _ in G.calo_seeds().values()]
    rs = [DG.block_seed(G.SERIES, "rich", "design", "surrogate", b)[0] for b in range(len(SAMPLES))]
    return zs + rs


def seeds() -> dict:
    reg = registered_seeds()
    out = {}
    for b, smp in enumerate(SAMPLES):
        s, t = DG.block_seed(SERIES, "rich", "p6cal", "held-out", b, registered=reg + [v[0] for v in out.values()])
        out[smp["name"]] = (s, t)
    return out


def _name(sample: str, i: int, c: int | None = None) -> str:
    return f"{sample}-{i:02d}" + ("" if c is None else f"-c{c:03d}")


def tasks(cfg: dict = CONFIG) -> list:
    """The task table: Geant4 tasks (sample-major, then chunk, then point), then the P6 tasks, each listing the Geant4
    tasks it reads (`after`)."""
    n, reps, H = int(cfg["events"]), int(cfg["reps"]), int(cfg["points"])
    sd = seeds()
    out = []
    holder: dict = {}
    for smp in SAMPLES:
        C = int(cfg["chunk"][smp["name"]])
        if reps % C:
            raise ValueError(f"reps {reps} not a multiple of the chunk {C}")
        for c in range(reps // C):
            for i in range(H):
                k = len(out)
                out.append({"task": k, "kind": "geant4", "sample": smp["name"], "point": i, "chunk": c,
                            "reps": [c * C, (c + 1) * C], "logical_run_seed": sd[smp["name"]][0],
                            "first_event": 2 * c * C * n, "events": 2 * C * n, "name": _name(smp["name"], i, c),
                            "cpu_seconds_estimate": round(2 * C * n * CPU_S_PER_EVENT[smp["name"]], 1)})
                holder[(smp["name"], i, c)] = k
    P = int(cfg["p6_reps"])
    if reps % P:
        raise ValueError(f"reps {reps} not a multiple of p6_reps {P}")
    for r0 in range(0, reps, P):
        after = sorted({holder[(smp["name"], i, r // int(cfg["chunk"][smp["name"]]))]
                        for smp in SAMPLES for i in range(H) for r in range(r0, r0 + P)})
        out.append({"task": len(out), "kind": "p6", "reps": [r0, r0 + P], "after": after})
    return out


# ------------------------------------------------------------------ cards and manifest
def write_cards(root: Path, cfg: dict = CONFIG, check: bool = True) -> dict:
    """Per (sample, point): detector.json, request.json, claims.json and run.json (the first chunk's card) after R.ask's
    documents at the point; run-cCCC.json per chunk (the same card, its own event interval). check-spec and the simulate
    preflight on run.json of every (sample, point); every chunk card is the first one but for first_event and events."""
    camp = root / CAMPAIGN
    pts = points(cfg)
    docs = R.documents()
    sd = seeds()
    tbl = [t for t in tasks(cfg) if t["kind"] == "geant4"]
    problems: dict = {}
    sha: dict = {}
    for smp in SAMPLES:
        for i, theta in enumerate(pts):
            d = R.apply(docs, theta, smp)
            folder = camp / "cards" / _name(smp["name"], i)
            folder.mkdir(parents=True, exist_ok=True)
            card = d["run"]
            card["run"].update(threads=1, logical_run_seed=sd[smp["name"]][0], first_event=0,
                               events=2 * int(cfg["chunk"][smp["name"]]) * int(cfg["events"]))
            for k, doc in (("detector", d["detector"]), ("request", d["request"]), ("run", card)):
                (folder / f"{k}.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
            (folder / "claims.json").write_text(json.dumps(list(R.CLAIMS)) + "\n", encoding="utf-8")
            sha[folder.name] = {f: _sha(folder / f) for f in ("detector.json", "request.json", "claims.json")}
            if check:
                row = {"claims": list(R.CLAIMS), "documents": {"detector": d["detector"], "request": d["request"],
                                                               "run": card}}
                bad = G.preflight(row, folder)
                if bad:
                    problems[folder.name] = bad
    runs = []
    for t in tbl:
        folder = camp / "cards" / _name(t["sample"], t["point"])
        card = json.loads((folder / "run.json").read_text())
        card["run"].update(first_event=int(t["first_event"]), events=int(t["events"]))
        f = folder / f"run-c{t['chunk']:03d}.json"
        f.write_text(json.dumps(card, indent=1) + "\n", encoding="utf-8")
        base = json.loads((folder / "run.json").read_text())
        for k in ("first_event", "events"):
            base["run"].pop(k)
            card["run"].pop(k)
        if base != card:
            problems[t["name"]] = ["the chunk card differs from the checked card beyond the event interval"]
        runs.append({**t, "theta": pts[t["point"]], "card": str(f.relative_to(root)),
                     "sha256": {**sha[folder.name], "run": _sha(f)}})
    man = {"schema": "simcal-p3g-p6cal-manifest/1", "program": str(G.PROGRAM), "program_sha256": G.PROGRAM_SHA256,
           "build": G.BUILD, "series": SERIES, "campaign": CAMPAIGN, "label": LABEL, "config": cfg,
           "design_seed": DESIGN_SEED, "points": pts, "seeds": {k: list(v) for k, v in sd.items()},
           "registered_seeds": registered_seeds(), "provenance": provenance(), "runs": runs, "checked": bool(check),
           "problems": problems}
    _write(root / CAMPAIGN / "manifest.json", man)
    man["manifest_sha256"] = _sha(root / CAMPAIGN / "manifest.json")
    return man


def load_manifest(root: Path) -> dict:
    return json.loads((root / CAMPAIGN / "manifest.json").read_text())


# ------------------------------------------------------------------ the per-event plane radius, streamed
def plane_radii(photons: Path, primaries: Path, detector: dict, first: int, n: int, block: int = 500_000) -> np.ndarray:
    """calibration_phase3_g4.plane_radius on files, vectorized and streamed in blocks of rows (a 20,000-event R_p100
    run has ~2.8 M photons.csv rows): per event the median over the primary's aerogel photons of their radius on the
    detection plane about the primary's crossing; NaN for an event without such photons."""
    prm = detector["params"]
    h, f, t = (float(prm[k]) for k in ("height_mm", "foil_mm", "aero_mm"))
    ea, na = G._rindex(detector, "aerogel")
    ef, nf = G._rindex(detector, "foil_pmma")
    z0, z1 = h + f, h + f + t
    pr = np.atleast_2d(np.loadtxt(primaries, delimiter=",", ndmin=2)) if primaries.stat().st_size else np.zeros((0, 8))
    cross = {}
    for row in pr:
        p0, pd = row[2:5], row[5:8]
        cross[int(row[0])] = p0[:2] + (0.0 - p0[2]) * pd[:2] / pd[2] if abs(pd[2]) > 0 else p0[:2]
    ev_all, rad_all = [], []
    cols = (0, 5, 6, 7, 8, 9, 10, 11, 12)
    with photons.open(encoding="utf-8") as fh:
        while True:
            lines = list(itertools.islice(fh, block))
            if not lines:
                break
            a = np.loadtxt(lines, delimiter=",", usecols=cols, ndmin=2)
            ev, en, x, y, z, dx, dy, dz, par = a.T
            ev = ev.astype(np.int64)
            norm = np.sqrt(dx * dx + dy * dy + dz * dz)
            dx, dy, dz = dx / norm, dy / norm, dz / norm
            keep = (par == 1) & (z >= z0) & (z <= z1) & np.isin(ev, list(cross)) & (dz < 0)
            s_out = np.hypot(dx, dy)
            sa = s_out / np.interp(en, ea, na)
            sf = s_out / np.interp(en, ef, nf)
            keep &= (sa < 1) & (sf < 1)
            if not keep.any():
                continue
            ev, x, y, z, dx, dy, dz, s_out, sa, sf = (v[keep] for v in (ev, x, y, z, dx, dy, dz, s_out, sa, sf))
            with np.errstate(invalid="ignore", divide="ignore"):
                ux = np.where(s_out > 0, dx / s_out, 0.0)
                uy = np.where(s_out > 0, dy / s_out, 0.0)
            lateral = (z - z0) * sa / np.sqrt(1 - sa * sa) + f * sf / np.sqrt(1 - sf * sf) + h * s_out / np.abs(dz)
            cx = np.array([cross[int(e)][0] for e in ev])
            cy = np.array([cross[int(e)][1] for e in ev])
            ev_all.append(ev)
            rad_all.append(np.hypot(x + lateral * ux - cx, y + lateral * uy - cy))
    out = np.full(n, np.nan)
    if ev_all:
        ev = np.concatenate(ev_all)
        rad = np.concatenate(rad_all)
        o = np.lexsort((rad, ev))
        ev, rad = ev[o], rad[o]
        starts = np.flatnonzero(np.r_[True, ev[1:] != ev[:-1]])
        ends = np.r_[starts[1:], len(ev)]
        for s, e in zip(starts, ends):
            k = int(ev[s]) - first
            if 0 <= k < n:
                m = e - s
                out[k] = rad[s + m // 2] if m % 2 else 0.5 * (rad[s + m // 2 - 1] + rad[s + m // 2])
    return out


# ------------------------------------------------------------------ the Geant4 task
G4_TIMEOUT_S = 3 * 3600 + 40 * 60     # inside the 3 h 55 min Slurm limit (the slowest pilot took 58 min)


def _simulate(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=G4_TIMEOUT_S)


def run_geant4_task(k: int, root: Path, out: Path, runner=None, program: Path = G.PROGRAM,
                    program_sha256: str = G.PROGRAM_SHA256, keep_photons: bool = False) -> dict:
    """One g4sim_run.py simulate of the registered card (SHA-256 against the manifest, the program's against the build
    record); the products' event list checked against the asked interval; the per-event plane radius written to
    ROOT/rich-p6cal/reduced/<name>.npy; photons.csv and conservation.csv deleted after their SHA-256 is recorded.
    runner(cmd) -> CompletedProcess (tests pass a stand-in)."""
    man = load_manifest(root)
    row = man["runs"][k]
    folder = root / CAMPAIGN / "cards" / _name(row["sample"], row["point"])
    card = root / row["card"]
    work = root / CAMPAIGN / "runs" / row["name"]
    files = {"detector": folder / "detector.json", "request": folder / "request.json",
             "claims": folder / "claims.json", "run": card}
    problems = [f"{n}: sha256 differs from the manifest" for n, h in row["sha256"].items()
                if _sha(files[n.removesuffix(".json")]) != h]
    if _sha(program) != program_sha256:
        problems.append(f"{program}: sha256 is not the build's {program_sha256[:16]}")
    rec = {"task": k, "kind": "geant4", "name": row["name"], "sample": row["sample"], "point": row["point"],
           "chunk": row["chunk"], "reps": row["reps"], "logical_run_seed": row["logical_run_seed"],
           "first_event": row["first_event"], "events": row["events"], "program": str(program),
           "provenance": provenance(), "started": time.time(), "label": LABEL}
    if problems:
        rec.update(status="refused", problems=problems)
        _write(out / f"task_{k:05d}.json", rec)
        return rec
    if work.exists():
        shutil.rmtree(work)
    cmd = [sys.executable, "-I", str(ASSETS / "g4sim_run.py"), "simulate", "--detector", str(files["detector"]),
           "--request", str(files["request"]), "--run", str(card), "--program", str(program), "--work", str(work),
           "--claims", str(files["claims"])]
    import resource
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.perf_counter()
    cp = (runner or _simulate)(cmd)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        result = json.loads(cp.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        result = {"status": "error", "stdout": cp.stdout[-2000:], "stderr": cp.stderr[-2000:]}
    rec.update(exit=cp.returncode, wall_seconds=round(time.perf_counter() - t0, 1),
               cpu_seconds=round(after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime, 1),
               max_rss_kb=after.ru_maxrss, result={x: result.get(x) for x in ("status", "rows", "geometry_id",
                                                                             "request_id", "findings", "reason")})
    status = result.get("status")
    if status == "ok":
        prim = work / "primaries.csv"
        evs = np.loadtxt(prim, delimiter=",", usecols=(0,), ndmin=1).astype(np.int64) if prim.stat().st_size \
            else np.zeros(0, np.int64)
        if sorted(evs.tolist()) != list(range(row["first_event"], row["first_event"] + row["events"])):
            status = "refused"
            rec["problems"] = ["primaries.csv does not hold exactly the asked events"]
        else:
            t1 = time.process_time()
            det = json.loads(files["detector"].read_text())
            x = plane_radii(work / "photons.csv", prim, det, row["first_event"], row["events"])
            red = root / CAMPAIGN / "reduced" / f"{row['name']}.npy"
            red.parent.mkdir(parents=True, exist_ok=True)
            np.save(red, x)
            rec["reduce_cpu_seconds"] = round(time.process_time() - t1, 1)
            rec["products_sha256"] = {n: _sha(work / n) for n in ("photons.csv", "primaries.csv", "cells.csv",
                                                                   "conservation.csv") if (work / n).exists()}
            rec["reduced"] = {"path": str(red.relative_to(root)), "sha256": _sha(red), "events": int(len(x)),
                              "finite": int(np.isfinite(x).sum())}
            if not keep_photons:
                for n in ("photons.csv", "conservation.csv"):
                    if (work / n).exists():
                        (work / n).unlink()
                rec["deleted"] = ["photons.csv", "conservation.csv"]
    rec["status"] = status
    _write(out / f"task_{k:05d}.json", rec)
    return rec


# ------------------------------------------------------------------ the P6 task
def _result(x: np.ndarray, sample: str, names: list) -> dict:
    """One side's evaluator-like result at one point for one sample (as calibration_phase3_g4.RichRunsEvaluator):
    the mean over events with a radius, s2, n, the per-event contribution (x - m)/n (0 for NaN events)."""
    ok = np.isfinite(x)
    n = int(ok.sum())
    m = float(np.mean(x[ok])) if n else float("nan")
    s2 = float(np.var(x[ok], ddof=1)) if n > 1 else float("nan")
    infl = np.where(ok, (np.nan_to_num(x) - m) / max(n, 1), 0.0)
    return {"name": sample, "mean": m, "s2": s2, "n": n, "influence": infl}


def _combine(parts: list) -> dict:
    """The per-sample parts of one side at one point as one result over the samples (one run per sample)."""
    nm = [p["name"] for p in parts]
    return {"names": nm, "pred": np.array([p["mean"] for p in parts]), "runs": nm,
            "s2": np.diag([p["s2"] for p in parts]), "V_MC": np.diag([p["s2"] / max(p["n"], 1) for p in parts]),
            "influence": {p["name"]: {j: (p["influence"], 1.0)} for j, p in enumerate(parts)}}


def p6_rep(full: list, sur: list, contract: dict, r: int, h_configs, shift=None) -> dict:
    """One repetition from the per-event radii: full[h], sur[h] = {sample: radii (N,)} at the held-out points h. Per H
    (the first H points) the toy's p6_rep: Delta m, cov_Delta per point (paired = False), the joint covariance
    (H >= 30), V_data from the contract's exposure, P6 at v in VEMU (v = 1: e ~ N(0, cov_Delta)). shift (H, k): a bias
    added to the surrogate (tests only)."""
    names = [s["name"] for s in SAMPLES]
    k = len(names)
    F = [_combine([_result(np.asarray(f[s]), s, names) for s in names]) for f in full]
    S = [_combine([_result(np.asarray(x[s]), s, names) for s in names]) for x in sur]
    out = {}
    for j, H in enumerate(h_configs):
        fu, su = F[:H], S[:H]
        dm = np.array([s["pred"] - f["pred"] for f, s in zip(fu, su)])
        if shift is not None:
            dm = dm + np.asarray(shift, float)[:H]
        cd = np.array([EM.delta_covariance(f, [s], np.array([1.0]), k, paired=False) for f, s in zip(fu, su)])
        cj = EM.joint_delta_covariance(fu, su, np.eye(H), k, paired=False) if H >= EM.MIN_PULL_POINTS else None
        vd = np.array([EM.v_data_unc(contract, f) for f in fu])
        g = np.random.default_rng([X.cal_seed(CAL, r), j, 3])
        z = g.standard_normal((H, k))
        row = {"r": r}
        for v in VEMU:
            ve = v * cd
            e = np.array([X._sqrt_psd(ve[h]) @ z[h] if v else np.zeros(k) for h in range(H)])
            res = EM.p6(dm + e, cd, ve, vd, cov_joint=cj)
            sig = np.sqrt(np.einsum("hkk->hk", cd))
            zonly = bool(np.any(np.abs(dm + e) > EM.bonferroni_z(H * k) * sig))
            pc = res["parts"]["pull_chi2"]
            row[str(v)] = {"failed": res["status"] == "failed", "delta_m_failed": res["parts"]["delta_m"]["status"] ==
                           "failed", "z_only_failed": zonly, "max_ratio": res["parts"]["delta_m"]["max_ratio"],
                           "chi2": pc.get("chi2"), "dof": pc.get("dof"), "p_value": pc.get("p_value"),
                           "chi2_failed": pc["status"] == "failed" if pc["status"] != "not-executed" else None}
        row["data_term_over_sigma_delta"] = float(np.median(0.3 * np.sqrt(vd) / np.sqrt(np.einsum("hkk->hk", cd))))
        row["finite_fraction"] = float(np.mean([np.isfinite(np.asarray(x[s])).mean() for x in full[:H]
                                                for s in names]))
        if cj is not None:
            sd = np.sqrt(np.diag(cj))
            corr = cj / np.outer(sd, sd)
            off = [corr[a * k + q, b * k + q] for q in range(k) for a in range(H) for b in range(a + 1, H)]
            row["cross_point_corr_median"] = float(np.median(off))
        out[str(H)] = row
    return out


def _radii(root: Path, man: dict, sample: str, point: int, r: int) -> tuple:
    """(full, surrogate) per-event radii of repetition r at one (sample, point), from the chunk's reduced file."""
    cfg = man["config"]
    n, C = int(cfg["events"]), int(cfg["chunk"][sample])
    c = r // C
    x = np.load(root / CAMPAIGN / "reduced" / f"{_name(sample, point, c)}.npy")
    o = 2 * (r - c * C) * n
    return x[o:o + n], x[o + n:o + 2 * n]


def run_p6_task(k: int, root: Path, out: Path) -> dict:
    man = load_manifest(root)
    cfg = man["config"]
    t = tasks(cfg)[k]
    t0 = time.process_time()
    contract = G.rich_contract(SAMPLES)
    contract["exposure"] = {s["name"]: int(cfg["events"]) for s in SAMPLES}
    reduced = {}
    for a in t["after"]:
        g4 = man["runs"][a]
        f = root / CAMPAIGN / "reduced" / f"{g4['name']}.npy"
        reduced[g4["name"]] = _sha(f) if f.exists() else None
    missing = sorted(n for n, h in reduced.items() if h is None)
    rec = {"task": k, "kind": "p6", "reps": t["reps"], "provenance": provenance(), "label": LABEL, "flags": FLAGS,
           "reduced_sha256": reduced}
    if missing:
        rec.update(status="incomplete", missing=missing[:20], n_missing=len(missing))
        _write(out / f"task_{k:05d}.json", rec)
        return rec
    rows: dict = {str(H): [] for H in cfg["h_configs"]}
    H = int(cfg["points"])
    for r in range(*t["reps"]):
        full, sur = [], []
        for i in range(H):
            pair = {s["name"]: _radii(root, man, s["name"], i, r) for s in SAMPLES}
            full.append({s: v[0] for s, v in pair.items()})
            sur.append({s: v[1] for s, v in pair.items()})
        rep = p6_rep(full, sur, contract, r, cfg["h_configs"])
        for h, v in rep.items():
            rows[h].append(v)
    rec.update(status="ok", rows=rows, cpu_seconds=round(time.process_time() - t0, 1))
    _write(out / f"task_{k:05d}.json", rec)
    return rec


def run_task(k: int, root: Path, out: Path, runner=None) -> dict:
    man = load_manifest(root)
    if k < len(man["runs"]):
        return run_geant4_task(k, root, out, runner=runner)
    return run_p6_task(k, root, out)


# ------------------------------------------------------------------ merge and judge
def interval_check(man: dict, g4: list) -> dict:
    """Section 6.6 on the Geant4 tasks' records: one set per sample (its points share each interval: common random
    numbers), the chunks disjoint; the seed blocks against each other and the registered p3-g4 seeds; every run on its
    sample's block seed; and the coverage of [0, 2 reps N) at every (sample, point)."""
    cfg = man["config"]
    evs = [{"run_id": r["name"], "use": "P6-calibration", "set": f"p6cal-{r['sample']}",
            "logical_run_seed": r["logical_run_seed"], "first_event": r["first_event"], "events": r["events"],
            "run_seed": r["logical_run_seed"], "replica": 0} for r in g4]
    blocks = [{"block": f"{CAMPAIGN}/{s}", "logical_run_seed": v[0], "t": v[1], "m_blk": 2 * int(cfg["reps"]),
               "N_ev": int(cfg["events"])} for s, v in man["seeds"].items()]
    blocks += [{"block": f"p3-g4/{i}", "logical_run_seed": s, "t": 0, "m_blk": 1, "N_ev": 1}
               for i, s in enumerate(man["registered_seeds"])]
    chk = DG.interval_findings({"evaluations": evs, "seed_blocks": blocks})
    cover = {}
    for r in g4:
        cover.setdefault((r["sample"], r["point"]), []).append((r["first_event"], r["events"]))
    full = 2 * int(cfg["reps"]) * int(cfg["events"])
    gaps = []
    for key, iv in cover.items():
        iv.sort()
        pos = 0
        for a, n in iv:
            if a != pos:
                gaps.append(f"{key}: events [{pos}, {a})")
            pos = a + n
        if pos != full:
            gaps.append(f"{key}: ends at {pos}, not {full}")
    chk["coverage_gaps"] = gaps[:20]
    seed_of = {s: int(v[0]) for s, v in man["seeds"].items()}
    wrong = [r["name"] for r in g4 if int(r["logical_run_seed"]) != seed_of.get(r["sample"])]
    chk["wrong_seed"] = wrong[:20]
    if gaps or wrong:
        chk["status"] = "failed"
    return chk


def judge(rows_by_h: dict, reps: int, max_false_alarms: int = MAX_FALSE_ALARMS) -> dict:
    """The toy's decision (calibration_phase3_cals.p6_judge: judged at v = 0, v = 1 reported) on the Geant4 rows."""
    by = {f"{H}|{v}": rows for H, rows in rows_by_h.items() for v in VEMU}
    res = X.p6_judge(by, reps, max_false_alarms)
    res["rule"] = (f"per configuration (H held-out points x 2 observables: the mean plane radius of R_p100 and R_p2.4; "
                   f"v = 0), P6 fails (either part) in <= {max_false_alarms} of {reps} repetitions with a correct "
                   "surrogate (an independent Geant4 simulation at the point, no error beyond MC noise; A13); the pull "
                   "chi2 referenced to its exact null distribution under the joint covariance of the held-out points "
                   "(A13); v = 1 (an error drawn at V_emu = cov_Delta) reported, not judged")
    for key, rows in by.items():
        c = res["configurations"][key]
        cc = [x["cross_point_corr_median"] for x in rows if "cross_point_corr_median" in x]
        if cc:
            c["cross_point_corr_median"] = float(np.median(cc))
        ps = [x[key.split("|")[1]]["p_value"] for x in rows if x[key.split("|")[1]].get("p_value") is not None]
        if ps:
            c["pull_p_value_deciles"] = np.quantile(ps, np.linspace(0.1, 0.9, 9)).tolist()
        c["finite_fraction_min"] = float(min(x["finite_fraction"] for x in rows)) if rows else None
    return res


def merge(out_dir: Path, out: Path, root: Path, max_false_alarms: int = MAX_FALSE_ALARMS) -> dict:
    man = load_manifest(root)
    cfg = man["config"]
    tbl = tasks(cfg)
    recs = {}
    for t in tbl:
        f = out_dir / f"task_{t['task']:05d}.json"
        recs[t["task"]] = json.loads(f.read_text()) if f.exists() else None
    missing = [k for k, v in recs.items() if v is None]
    g4 = [v for v in recs.values() if v and v["kind"] == "geant4"]
    p6 = [v for v in recs.values() if v and v["kind"] == "p6"]
    bad = sorted(v["task"] for v in recs.values() if v and v.get("status") != "ok")
    commits = {v["provenance"]["commit"] for v in recs.values() if v}
    dirty = any(v["provenance"].get("dirty") for v in recs.values() if v)
    chk = interval_check(man, g4)
    rows: dict = {str(H): [] for H in cfg["h_configs"]}
    for v in p6:
        for h, rr in (v.get("rows") or {}).items():
            rows[h].extend(rr)
    for h in rows:
        rows[h].sort(key=lambda x: x["r"])
    res = judge(rows, int(cfg["reps"]), max_false_alarms)
    complete = not missing and not bad and len(commits) == 1 and not dirty and chk["status"] == "passed"
    cpu = {"geant4": round(sum(v.get("cpu_seconds") or 0 for v in g4) / 3600, 1),
           "p6": round(sum(v.get("cpu_seconds") or 0 for v in p6) / 3600, 2)}
    rep = {"array": "simcal phase 3, section 8.7 row 2004 (P6 part), Geant4 version on the RICH replica (WP-L)",
           "complete": complete, "missing_tasks": missing[:50], "n_missing": len(missing), "not_ok_tasks": bad[:50],
           "commits": sorted(c for c in commits if c), "dirty": dirty, "interval_check": chk, "result": res,
           "passed": bool(complete and res["passed"]), "cpu_hours": cpu, "manifest_sha256":
           _sha(root / CAMPAIGN / "manifest.json"), "provenance": provenance(), "label": LABEL, "flags": FLAGS}
    _write(out, rep)
    return rep


# ------------------------------------------------------------------ --local: the path on STAND-IN products
SMOKE = {"events": 12, "reps": 4, "points": 32, "h_configs": [8, 32], "chunk": {"R_p100": 2, "R_p2.4": 4},
         "p6_reps": 2}


def standin_runner(root: Path, photons_per_event: float = 12.0):
    """A runner that writes calibration_phase3_g4.standin_rich_products (analytic Cherenkov emission, labelled
    `analytic-stand-in`, never Geant4) for the card the command names."""
    def run(cmd):
        args = dict(zip(cmd[4::2], cmd[5::2]))
        work, card = Path(args["--work"]), json.loads(Path(args["--run"]).read_text())
        det = json.loads(Path(args["--detector"]).read_text())
        req = json.loads(Path(args["--request"]).read_text())
        e_mev = float(req["source"]["energy"]["mono"]["energy_MeV"])
        smp = min(SAMPLES, key=lambda s: abs(1000.0 * s["kinetic_per_nucleon_GeV"] - e_mev))
        row = {"sample": smp["name"], "logical_run_seed": card["run"]["logical_run_seed"],
               "first_event": card["run"]["first_event"], "events": card["run"]["events"]}
        G.standin_rich_products(work, row, det, photons_per_event)
        (work / "conservation.csv").write_text("event,residual_MeV,accounting_errors\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, json.dumps({"status": "ok", "rows": {}}) + "\n", "")
    return run


def smoke_run(out: Path, cfg: dict = SMOKE) -> dict:
    """Every task of a tiny configuration on stand-in products (check-spec on one card), then the merge: label
    `smoke`, never evidence. The rule at these sizes is 0 failures of cfg['reps'] (structure only)."""
    root = out / "root"
    if root.exists():
        shutil.rmtree(root)
    man = write_cards(root, cfg, check=False)
    first = root / CAMPAIGN / "cards" / _name(SAMPLES[0]["name"], 0)
    row = {"claims": list(R.CLAIMS), "documents": {k: json.loads((first / f"{k}.json").read_text())
                                                   for k in ("detector", "request", "run")}}
    pre = G.preflight(row, first)
    t0 = time.process_time()
    run = standin_runner(root)
    for t in tasks(cfg):
        if t["kind"] == "geant4":
            run_geant4_task(t["task"], root, out / "tasks", runner=run, program=Path(__file__),
                            program_sha256=_sha(Path(__file__)))
        else:
            run_p6_task(t["task"], root, out / "tasks")
    rep = merge(out / "tasks", out / "merged.json", root, max_false_alarms=0)
    return {"label": "smoke", "preflight": pre, "merged": rep, "manifest_runs": len(man["runs"]),
            "cpu_seconds": round(time.process_time() - t0, 1)}


# ------------------------------------------------------------------ CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cards")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--task", type=int)
    ap.add_argument("--merge")
    ap.add_argument("--root")
    ap.add_argument("--local", dest="smoke", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    root = Path(a.root) if a.root else OUT_ROOT
    if a.cards:
        m = write_cards(Path(a.cards))
        print(json.dumps({"runs": len(m["runs"]), "problems": m["problems"], "manifest_sha256": m["manifest_sha256"]}))
        return 1 if m["problems"] else 0
    if a.list:
        cfg = load_manifest(root)["config"] if (root / CAMPAIGN / "manifest.json").exists() else CONFIG
        print(json.dumps(tasks(cfg), indent=0))
        return 0
    if not a.out:
        ap.error("--out is required with --task, --merge and --local")
    if a.task is not None:
        r = run_task(a.task, root, Path(a.out))
        print(json.dumps({k: r.get(k) for k in ("task", "kind", "name", "status", "cpu_seconds", "problems")}))
        return 0 if r["status"] == "ok" else 1
    if a.merge:
        r = merge(Path(a.merge), Path(a.out), root)
        print(json.dumps({"complete": r["complete"], "passed": r["passed"], "missing": r["n_missing"]}))
        return 0 if r["passed"] else 1
    if a.smoke:
        r = smoke_run(Path(a.out))
        print(json.dumps({"label": "smoke", "complete": r["merged"]["complete"], "cpu": r["cpu_seconds"]}))
        return 0
    ap.error("one of --cards, --list, --task, --merge, --local")
    return 2


if __name__ == "__main__":
    sys.exit(main())
