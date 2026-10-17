#!/usr/bin/env python3
"""Geomagnetic cutoff rigidities by backtracing with OTSO, run as a separate program (D12).

Purpose: a cutoff grid and its penumbra for declared locations, date and field model, from a particle tracer
instead of the analytic Stormer estimate of <plugin root>/skills/hep-measurement/scripts/geomagnetic_cutoff.py.
The results are backtraced cutoffs in the declared field model: not any experiment's official cutoff.

Tool and licence boundary: OTSO (Larsen, Mishev and Usoskin, JGR Space Physics 128, e2022JA031061, 2023;
https://github.com/NLarsen15/OTSOpy, `pip install otso`) is GPL-3.0; this plugin is Apache-2.0. The adapter never
imports, copies or bundles OTSO: it writes a small driver script and runs it with an interpreter the user installed
OTSO into (`--otso-python`), exchanging JSON files. Without OTSO in that interpreter the run exits 3 with a hint.

Method: OTSO `cutoff` for every location (vertical or apparent cutoff, OTSO's rigidity scan), giving the upper,
effective and lower cutoffs Ru, Rc, Rl and the penumbral transmission (PTF); the penumbra width is Ru - Rl. Large
grids run in slices (`--start/--stop`, a core/partition or local_partition.py worker each) and `merge` joins them,
refusing duplicates and slices of another spec. OTSO's network retrieval of solar-wind and geomagnetic indices is
never used: give the indices in `otso_params` (geomagnetic_params, solar_wind_params, tsyganenko_params).

Spec (JSON; no defaults except `cores`): {"locations": [{"id", "latitude_deg", "longitude_deg"}] | "grid":
{"latitudes_deg": [...], "longitudes_deg": [...]}, "altitude_km": h (geodetic, OTSO's GDZ input), "datetime": {year,
month, day, hour}, "field": {"internal": "IGRF"|"Dipole"|"Custom Gauss"|"CHAOS"|"NONE", "external": OTSO name or
"NONE", "magnetopause": OTSO name, optional "spheresize", "g", "h", "max_degree"}, "rigidity": {"start_gv",
"end_gv", "step_gv"}, "particle": {"atomic_number", "anti": "YES"|"NO"}, "cutoff": "Vertical"|"Apparent",
optional "cores" and "otso_params" {group: {...}}}.

Oracle (`dipole-check`): in an axial dipole (custom Gauss coefficient g10 only, no external field, a spherical
boundary) the lowest allowed vertical rigidity Rl is never below the Stormer vertical cutoff (Stormer theory forbids
every rigidity below it) and equals it at the geomagnetic equator; the Stormer value comes from geomagnetic_cutoff.py
with M = |g10| a^3 (a = 6371.2 km, the IGRF reference radius) at the geocentric latitude and radius of the geodetic
input (WGS84). `--replay` re-checks a run recorded with `--record`.

Usage (from the plugin root):
  python3 adapters/geomagnetic-backtracing/assets/otso_cutoff.py run --spec SPEC.json --otso-python PY --out OUT.json [--start I --stop J]
  python3 adapters/geomagnetic-backtracing/assets/otso_cutoff.py merge PART.json [PART.json ...] --out OUT.json
  python3 adapters/geomagnetic-backtracing/assets/otso_cutoff.py dipole-check (--otso-python PY --g10-nt G --latitudes L ... --altitude-km H [--record RAW.json] | --replay RAW.json)
Every subcommand takes --status LABEL (default unvalidated), echoed as status_label.
Output JSON: status, status_label, label, inputs, defaults_used, tool (name, version, licence), field_model,
records (id, latitude_deg, longitude_deg, altitude_km, Ru_gv, Rc_gv, Rl_gv, penumbra_width_gv,
penumbral_transmission), spec_sha256, slice, warnings.
Exit codes: 0 ok; 1 the oracle failed or OTSO failed; 2 bad input; 3 OTSO missing, or a location without a cutoff
(incomplete). Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
from core.status import add_status_argument, exit_code  # noqa: E402

STORMER = PLUGIN / "skills" / "hep-measurement" / "scripts" / "geomagnetic_cutoff.py"
LABEL = "[General method] backtraced cutoffs in the declared field model; not any experiment's official cutoff"
INSTALL = ("OTSO is not importable by the given interpreter: install it in a separate environment "
           "(`python3 -m venv otso && otso/bin/pip install otso`; OTSO is GPL-3.0 and is never bundled with this "
           "plugin) and pass that interpreter with --otso-python")
IGRF_RADIUS_KM = 6371.2
WGS84_A_KM, WGS84_F = 6378.137, 1 / 298.257223563
OTSO_GROUPS = ("solar_wind_params", "geomagnetic_params", "tsyganenko_params", "integration_params",
               "asymptotic_params", "transmission_params", "coordinate_params")

DRIVER = '''import json, sys, warnings
warnings.filterwarnings("ignore")
from OTSO import cutoff


def main():
    job = json.load(open(sys.argv[1], encoding="utf-8"))
    res = cutoff(Stations=[], customlocations=job["customlocations"], cutoff_comp=job["cutoff_comp"], **job["params"])
    info = res[-1] if isinstance(res[-1], str) else str(res[-1])
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        json.dump({"table": res[0].to_dict(), "info": info}, fh)


if __name__ == "__main__":
    main()
'''


class SpecError(ValueError):
    """A spec the adapter refuses (exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _num(x, name):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise SpecError(f"{name} must be a finite number")
    return float(x)


def locations(spec: dict) -> list[dict]:
    if "locations" in spec and "grid" in spec:
        raise SpecError("give locations or grid, not both")
    if "locations" in spec:
        out = []
        for i, loc in enumerate(spec["locations"]):
            if not isinstance(loc, dict) or not str(loc.get("id", "")).strip():
                raise SpecError(f"locations[{i}] needs an id")
            out.append({"id": str(loc["id"]), "latitude_deg": _num(loc.get("latitude_deg"), f"locations[{i}].latitude_deg"),
                        "longitude_deg": _num(loc.get("longitude_deg"), f"locations[{i}].longitude_deg")})
    elif "grid" in spec:
        g = spec["grid"]
        lats = [_num(x, "grid.latitudes_deg") for x in g.get("latitudes_deg") or []]
        lons = [_num(x, "grid.longitudes_deg") for x in g.get("longitudes_deg") or []]
        if not lats or not lons:
            raise SpecError("grid needs latitudes_deg and longitudes_deg")
        out = [{"id": f"lat{la:+.3f}_lon{lo:.3f}", "latitude_deg": la, "longitude_deg": lo} for la in lats for lo in lons]
    else:
        raise SpecError("the spec needs locations or grid")
    for loc in out:
        if not -90 <= loc["latitude_deg"] <= 90:
            raise SpecError(f"{loc['id']}: latitude outside [-90, 90]")
    if len({loc["id"] for loc in out}) != len(out):
        raise SpecError("location ids must be unique")
    return out


def otso_job(spec: dict, locs: list[dict]) -> tuple[dict, list[str]]:
    """The OTSO call for these locations, and the spec keys that took a default."""
    for key in ("altitude_km", "datetime", "field", "rigidity", "particle", "cutoff"):
        if key not in spec:
            raise SpecError(f"missing {key} (no defaults: field model, date and scan are part of the result)")
    f, r, p = spec["field"], spec["rigidity"], spec["particle"]
    for key in ("internal", "external", "magnetopause"):
        if not isinstance(f.get(key), str) or not f[key]:
            raise SpecError(f"field.{key} is required")
    start, end, step = (_num(r.get(k), f"rigidity.{k}") for k in ("start_gv", "end_gv", "step_gv"))
    if not (start > end >= 0 and step > 0):
        raise SpecError("rigidity scan must run down: start_gv > end_gv >= 0, step_gv > 0")
    if spec["cutoff"] not in ("Vertical", "Apparent"):
        raise SpecError("cutoff must be Vertical or Apparent")
    if p.get("anti") not in ("YES", "NO"):
        raise SpecError("particle.anti must be YES or NO (OTSO's backtracing convention)")
    dt = spec["datetime"]
    for key in ("year", "month", "day", "hour"):
        if not isinstance(dt.get(key), int):
            raise SpecError(f"datetime.{key} must be an integer")
    defaults = []
    cores = spec.get("cores")
    if cores is None:
        cores = 1
        defaults.append("cores")
    mag = {"internalmag": f["internal"], "externalmag": f["external"], "magnetopause": f["magnetopause"]}
    if "spheresize" in f:
        mag["spheresize"] = _num(f["spheresize"], "field.spheresize")
    params = {"magfield_params": mag, "datetime_params": dict(dt),
              "rigidity_params": {"startrigidity": start, "endrigidity": end, "rigiditystep": step},
              "particle_params": {"Anum": int(_num(p.get("atomic_number"), "particle.atomic_number")), "anti": p["anti"]},
              "computation_params": {"corenum": int(cores), "Verbose": False}}
    if f["internal"] == "Custom Gauss":
        if not f.get("g") or not f.get("h"):
            raise SpecError("field.internal 'Custom Gauss' needs field.g and field.h")
        params["custom_field_params"] = {"g": f["g"], "h": f["h"], "max_degree": int(f.get("max_degree", 13))}
    extra = spec.get("otso_params") or {}
    for group, values in extra.items():
        if group not in OTSO_GROUPS:
            raise SpecError(f"otso_params.{group} is not passed through (allowed: {', '.join(OTSO_GROUPS)}); OTSO's "
                            "network data retrieval is never used: give indices explicitly")
        params.setdefault(group, {}).update(values)
    params.setdefault("integration_params", {})["startaltitude"] = _num(spec["altitude_km"], "altitude_km")
    job = {"customlocations": [[loc["id"], loc["latitude_deg"], loc["longitude_deg"]] for loc in locs],
           "cutoff_comp": spec["cutoff"], "params": params}
    return job, defaults


def has_otso(python: str) -> bool:
    p = subprocess.run([python, "-c", "import OTSO"], capture_output=True, text=True, timeout=600)
    return p.returncode == 0


def call_otso(python: str, job: dict) -> dict:
    with tempfile.TemporaryDirectory() as d:
        drv, jin, jout = Path(d) / "otso_driver.py", Path(d) / "job.json", Path(d) / "out.json"
        drv.write_text(DRIVER, encoding="utf-8")
        jin.write_text(json.dumps(job), encoding="utf-8")
        p = subprocess.run([python, str(drv), str(jin), str(jout)], capture_output=True, text=True, timeout=86400, cwd=d)
        if p.returncode != 0 or not jout.exists():
            raise RuntimeError(f"OTSO failed (exit {p.returncode}): {p.stderr[-800:]}")
        return json.loads(jout.read_text(encoding="utf-8"))


def otso_version(info: str) -> str | None:
    for line in info.splitlines():
        if line.strip().startswith("OTSO Version:"):
            return line.split(":", 1)[1].strip()
    return None


def _finite(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def records(raw: dict, locs: list[dict], altitude_km: float) -> list[dict]:
    out = []
    for loc in locs:
        row = raw["table"].get(loc["id"], {})
        ru, rc, rl, ptf = (_finite(row.get(k)) for k in ("Ru", "Rc", "Rl", "PTF"))
        out.append({**loc, "altitude_km": altitude_km, "Ru_gv": ru, "Rc_gv": rc, "Rl_gv": rl,
                    "penumbra_width_gv": None if ru is None or rl is None else ru - rl, "penumbral_transmission": ptf})
    return out


def spec_digest(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def cmd_run(args) -> tuple[str, dict]:
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    locs_all = locations(spec)
    start = args.start or 0
    stop = len(locs_all) if args.stop is None else args.stop
    if not 0 <= start < stop <= len(locs_all):
        raise SpecError(f"--start/--stop must select within 0..{len(locs_all)}")
    locs = locs_all[start:stop]
    job, defaults = otso_job(spec, locs)
    if not has_otso(args.otso_python):
        return "missing-dependency", {"install": INSTALL, "otso_python": args.otso_python}
    raw = call_otso(args.otso_python, job)
    recs = records(raw, locs, spec["altitude_km"])
    missing = [r["id"] for r in recs if r["Rc_gv"] is None]
    doc = {"label": LABEL, "defaults_used": defaults,
           "tool": {"name": "OTSO", "version": otso_version(raw["info"]),
                    "licence": "GPL-3.0; run as a separate program, never bundled"},
           "field_model": dict(spec["field"]), "datetime": spec["datetime"], "cutoff": spec["cutoff"],
           "records": recs, "spec_sha256": spec_digest(spec),
           "slice": {"start": start, "stop": stop, "n_locations": len(locs_all)},
           "warnings": [f"no cutoff found within the scan for {missing}"] if missing else []}
    return ("incomplete" if missing else "ok"), doc


def cmd_merge(args) -> tuple[str, dict]:
    parts = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.parts]
    digests = {p.get("spec_sha256") for p in parts}
    if len(digests) != 1:
        raise SpecError("the slices come from different specs")
    seen, recs = set(), []
    for p in sorted(parts, key=lambda d: d["slice"]["start"]):
        for r in p["records"]:
            if r["id"] in seen:
                raise SpecError(f"location {r['id']} appears in more than one slice")
            seen.add(r["id"])
            recs.append(r)
    n = parts[0]["slice"]["n_locations"]
    doc = {k: parts[0][k] for k in ("label", "tool", "field_model", "datetime", "cutoff", "spec_sha256")}
    doc.update(records=recs, complete=len(recs) == n, slice={"start": 0, "stop": len(recs), "n_locations": n},
               defaults_used=[], warnings=[w for p in parts for w in p.get("warnings", [])])
    status = "ok" if doc["complete"] and not doc["warnings"] else "incomplete"
    return status, doc


def geocentric(lat_deg: float, h_km: float) -> tuple[float, float]:
    """Geocentric latitude (degrees) and radius (km) of a WGS84 geodetic point."""
    phi = math.radians(lat_deg)
    e2 = WGS84_F * (2 - WGS84_F)
    n = WGS84_A_KM / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    x, z = (n + h_km) * math.cos(phi), (n * (1 - e2) + h_km) * math.sin(phi)
    return math.degrees(math.atan2(z, x)), math.hypot(x, z)


def stormer(lat_deg: float, h_km: float, g10_nt: float) -> float:
    lat_c, r_km = geocentric(lat_deg, h_km)
    moment = abs(g10_nt) * 1e-5 * (IGRF_RADIUS_KM * 1e5) ** 3  # G cm^3
    p = subprocess.run([sys.executable, "-B", str(STORMER), "--latitude", repr(lat_c), "--radius-re",
                        repr(r_km / IGRF_RADIUS_KM), "--dipole-moment", repr(moment), "--epoch", "synthetic axial dipole"],
                       capture_output=True, text=True, timeout=600)
    return json.loads(p.stdout)["vertical_cutoff_rigidity_gv"]


def cmd_dipole(args) -> tuple[str, dict]:
    if args.replay:
        rec = json.loads(Path(args.replay).read_text(encoding="utf-8"))
        g10, lats, h, raw = rec["g10_nt"], rec["latitudes_deg"], rec["altitude_km"], rec["otso"]
    else:
        if args.g10_nt is None or not args.latitudes or args.altitude_km is None or not args.otso_python:
            raise SpecError("a live dipole-check needs --otso-python, --g10-nt, --latitudes and --altitude-km")
        g10, lats, h = args.g10_nt, args.latitudes, args.altitude_km
        spec = {"locations": [{"id": f"L{i}", "latitude_deg": la, "longitude_deg": 0.0} for i, la in enumerate(lats)],
                "altitude_km": h, "datetime": {"year": 2000, "month": 1, "day": 1, "hour": 0},
                "field": {"internal": "Custom Gauss", "external": "NONE", "magnetopause": "Sphere", "spheresize": 25,
                          "g": [0.0, g10, 0.0], "h": [0.0, 0.0, 0.0], "max_degree": 1},
                "rigidity": {"start_gv": 20.0, "end_gv": 0.0, "step_gv": 0.01},
                "particle": {"atomic_number": 1, "anti": "YES"}, "cutoff": "Vertical"}
        job, _ = otso_job(spec, locations(spec))
        if not has_otso(args.otso_python):
            return "missing-dependency", {"install": INSTALL}
        raw = call_otso(args.otso_python, job)
        if args.record:
            Path(args.record).write_text(json.dumps({"g10_nt": g10, "latitudes_deg": lats, "altitude_km": h,
                                                     "spec": spec, "otso": raw}, indent=1) + "\n", encoding="utf-8")
    rows, ok = [], True
    for i, la in enumerate(lats):
        t = raw["table"][f"L{i}"]
        st = stormer(la, h, g10)
        rl, rc = _finite(t.get("Rl")), _finite(t.get("Rc"))
        bound = rl is not None and rl >= st * (1 - 0.01)
        equator = abs(la) > 1e-9 or (rc is not None and abs(rc / st - 1) <= 0.01)
        ok = ok and bound and equator
        rows.append({"latitude_deg": la, "stormer_gv": st, "Rl_gv": rl, "Rc_gv": rc, "Ru_gv": _finite(t.get("Ru")),
                     "Rl_at_least_stormer": bound, "ratio_Rc_to_stormer": None if rc is None else rc / st})
    doc = {"comparison": rows, "tool": {"name": "OTSO", "version": otso_version(raw["info"])},
           "rule": "Rl >= Stormer (1 - 0.01) at every latitude; Rc within 1% of Stormer at the equator",
           "field": f"axial dipole, g10 = {g10} nT, no external field, spherical boundary 25 Re"}
    return ("ok" if ok else "failed"), doc


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run", help="cutoffs for the locations of a spec (or a slice of them)")
    p.add_argument("--spec", required=True)
    p.add_argument("--otso-python", required=True, help="an interpreter with OTSO installed")
    p.add_argument("--out", required=True)
    p.add_argument("--start", type=int)
    p.add_argument("--stop", type=int)
    p = sub.add_parser("merge", help="join slices of one spec")
    p.add_argument("parts", nargs="+")
    p.add_argument("--out", required=True)
    p = sub.add_parser("dipole-check", help="the axial-dipole oracle against the Stormer cutoff")
    p.add_argument("--otso-python")
    p.add_argument("--g10-nt", type=float)
    p.add_argument("--latitudes", type=float, nargs="+")
    p.add_argument("--altitude-km", type=float)
    p.add_argument("--record")
    p.add_argument("--replay")
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    try:
        status, doc = {"run": cmd_run, "merge": cmd_merge, "dipole-check": cmd_dipole}[args.command](args)
    except (SpecError, OSError, KeyError, json.JSONDecodeError) as exc:
        status, doc = "rejected", {"error": str(exc)}
    except RuntimeError as exc:
        status, doc = "failed", {"error": str(exc)}
    out = {"status": status, "status_label": args.status, "inputs": inputs, **doc}
    out.setdefault("defaults_used", [])
    if status in ("ok", "incomplete") and getattr(args, "out", None):
        Path(args.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
