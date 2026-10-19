#!/usr/bin/env python3
"""Spectrum plot from dataset-records: E^gamma weighting, a stated bin position, status labels, overlays that are not
combinations (Com5).

Purpose: draw a differential spectrum (for example a cosmic-ray flux) so that every point can be traced back to the
record it came from and the reader cannot mistake its status or an overlay for a combination. See
<plugin root>/skills/hep-authoring/references/physics-plots.md, "Spectrum plots".
Method:
- data come only from dataset-record artifacts (`--record`, repeatable): bin edges, bin averages and the listed
  uncertainties added in quadrature (or the covariance diagonal when the record has one), all stated in the sidecar;
- bin position (required, no default): `lafferty-wyatt` places a point where the declared power law Phi ~ x^-g
  (`--lw-index g`) equals its bin average, x_lw = [(x1^(1-g) - x2^(1-g)) / ((g-1)(x2-x1))]^(-1/g) (g = 1 uses the
  logarithmic form); `center` the arithmetic and `log-center` the geometric bin centre. The rule and its parameter
  are printed in the caption;
- `--weight-power G` plots x^G * Phi at the plotted position (errors scaled the same way);
- `--to VARIABLE --Z Z --composition FILE` converts each record to another spectral variable through hep-measurement's
  `spectrum_transform.py` (M7: Jacobian and bin averaging, not a relabeling), run as a separate process; its
  transformation record and total covariance (statistical plus composition) are kept;
- the legend gives each series its record id and status labels; the caption lists every record with its status and
  says that overlaid series are not combined.
Output: the figure (--out, .png or .pdf) and a JSON sidecar (--sidecar, default FIGURE.json) with one entry per point
(artifact_id, record_sha256, bin, edges, x, y, y_err, status) and the caption; JSON on stdout with status,
status_label (--status, default unvalidated), inputs, defaults_used, figure, sidecar and caption.
Exit codes: 0 written; 2 bad input (not a dataset-record, no bin rule, a missing parameter, a failed conversion);
3 matplotlib missing (pip install matplotlib).
Usage: spectrum_plot.py --record A.json [--record B.json ...] --bin-position lafferty-wyatt --lw-index 2.7
           [--weight-power 2.7] [--to kinetic_energy_per_nucleon --Z 2 --composition comp.json] --out spectrum.png
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True  # the import below leaves no __pycache__ (F-10)
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
from core.status import add_status_argument, exit_code  # noqa: E402

TRANSFORM = PLUGIN / "skills" / "hep-measurement" / "scripts" / "spectrum_transform.py"


class InputError(ValueError):
    pass


def load_record(path: Path) -> dict:
    try:
        raw = path.read_bytes()
        doc = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise InputError(f"{path}: not readable JSON ({exc})") from exc
    if not isinstance(doc, dict) or doc.get("artifact_type") != "dataset-record":
        raise InputError(f"{path}: not a dataset-record (artifact_type {doc.get('artifact_type') if isinstance(doc, dict) else None!r}); "
                         "plots take data only from dataset-records")
    ext = doc.get("extension") or {}
    data = ext.get("data") or {}
    edges, values = data.get("edges"), data.get("values")
    if not isinstance(edges, list) or not isinstance(values, list) or len(edges) != len(values) + 1:
        raise InputError(f"{path}: data.edges and data.values do not match")
    cov = ext.get("covariance") or {}
    if isinstance(cov.get("matrix"), list):
        errs = [math.sqrt(cov["matrix"][i][i]) for i in range(len(values))]
        err_rule = "square root of the covariance diagonal"
    else:
        uncs = data.get("uncertainties") or []
        errs = [math.sqrt(sum(float(u["values"][i]) ** 2 for u in uncs)) for i in range(len(values))]
        err_rule = "the listed uncertainties (" + ", ".join(u.get("name", "?") for u in uncs) + ") added in quadrature"
    var = ((ext.get("observable") or {}).get("variables") or [{}])[0]
    status = doc.get("status") or []
    status = status if isinstance(status, list) else [status]
    return {"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "artifact_id": doc.get("artifact_id"),
            "status": status, "edges": [float(e) for e in edges], "values": [float(v) for v in values],
            "errors": errs, "error_rule": err_rule, "variable": var.get("name"), "x_unit": var.get("unit"),
            "y_unit": data.get("unit"), "dataset_id": ext.get("dataset_id")}


def convert(rec: dict, to: str, z: int, composition: dict) -> dict:
    doc = {"variable": rec["variable"], "unit": rec["x_unit"], "edges": rec["edges"], "values": rec["values"],
           "uncertainties": rec["errors"], "Z": z, "composition": composition}
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "flux.json"
        f.write_text(json.dumps(doc), encoding="utf-8")
        p = subprocess.run([sys.executable, "-B", str(TRANSFORM), str(f), "--to", to], capture_output=True, text=True,
                           timeout=600)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = {}
    if p.returncode != 0 or out.get("status") != "ok":
        raise InputError(f"{rec['artifact_id']}: spectrum_transform.py failed ({out.get('error') or p.stderr[-300:]})")
    cov = out.get("total_covariance") or out.get("covariance")
    errs = [math.sqrt(cov[i][i]) for i in range(len(out["values"]))] if cov else [0.0] * len(out["values"])
    return dict(rec, edges=out["edges"], values=out["values"], errors=errs, variable=out["variable"],
                x_unit=None, transformation_record=out.get("transformation_record"),
                error_rule="square root of the total covariance diagonal (statistical and composition) from spectrum_transform.py")


def position(lo: float, hi: float, rule: str, g: float | None) -> float:
    if rule == "center":
        return 0.5 * (lo + hi)
    if lo <= 0:
        raise InputError(f"bin [{lo}, {hi}]: {rule} needs positive edges")
    if rule == "log-center":
        return math.sqrt(lo * hi)
    if abs(g - 1.0) < 1e-12:
        mean = math.log(hi / lo) / (hi - lo)  # bin average of 1/x
    else:
        mean = (lo ** (1 - g) - hi ** (1 - g)) / ((g - 1) * (hi - lo))
    return mean ** (-1.0 / g)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--record", type=Path, action="append", required=True, help="a dataset-record JSON (repeatable)")
    ap.add_argument("--bin-position", choices=("lafferty-wyatt", "center", "log-center"),
                    help="where a bin's point is drawn (required)")
    ap.add_argument("--lw-index", type=float, help="power-law index g of the Lafferty-Wyatt rule")
    ap.add_argument("--weight-power", type=float, default=0.0, help="plot x^G * flux (default 0: no weighting)")
    ap.add_argument("--to", help="convert to this spectral variable through spectrum_transform.py")
    ap.add_argument("--Z", type=int, help="charge number for --to")
    ap.add_argument("--composition", type=Path, help="isotope-composition JSON for --to (spectrum_transform format)")
    ap.add_argument("--out", type=Path, required=True, help="figure file (.png or .pdf)")
    ap.add_argument("--sidecar", type=Path, help="JSON sidecar (default: the figure path with .json)")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    base = {"status_label": args.status,
            "inputs": {k: ([str(x) for x in v] if isinstance(v, list) else (str(v) if isinstance(v, Path) else v))
                       for k, v in vars(args).items() if k != "status"},
            "defaults_used": [k for k in ("weight-power", "sidecar", "status") if f"--{k}" not in given]}

    def refuse(msg: str) -> int:
        print(json.dumps({"status": "rejected", **base, "error": msg}, indent=1))
        return exit_code("rejected")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        print(json.dumps({"status": "missing-dependency", **base, "error": f"matplotlib is not importable ({exc})",
                          "install": "pip install matplotlib"}, indent=1))
        return exit_code("missing-dependency")
    if args.bin_position is None:
        return refuse("--bin-position is required: lafferty-wyatt (with --lw-index), center or log-center")
    if args.bin_position == "lafferty-wyatt" and args.lw_index is None:
        return refuse("--bin-position lafferty-wyatt needs --lw-index (the power-law index of the spectrum)")
    if args.out.suffix.lower() not in (".png", ".pdf"):
        return refuse("--out must end in .png or .pdf")
    try:
        records = [load_record(p) for p in args.record]
        if args.to:
            if args.Z is None or args.composition is None:
                raise InputError("--to needs --Z and --composition")
            comp = json.loads(args.composition.read_text(encoding="utf-8"))
            records = [convert(r, args.to, args.Z, comp) for r in records]
        variables = {r["variable"] for r in records}
        if len(variables) != 1:
            raise InputError(f"records are in different variables {sorted(map(str, variables))}; convert them first (--to)")
        points, series = [], []
        fig, ax = plt.subplots(figsize=(6.4, 4.4))
        g = args.weight_power
        for k, r in enumerate(records):
            xs, ys, es = [], [], []
            for i, (lo, hi) in enumerate(zip(r["edges"], r["edges"][1:])):
                x = position(lo, hi, args.bin_position, args.lw_index)
                w = x ** g if g else 1.0
                xs.append(x)
                ys.append(r["values"][i] * w)
                es.append(r["errors"][i] * w)
                points.append({"artifact_id": r["artifact_id"], "record_sha256": r["sha256"], "bin": i, "edges": [lo, hi],
                               "x": x, "y": r["values"][i] * w, "y_err": r["errors"][i] * w, "status": r["status"]})
            legend = f"{r['artifact_id']} [{', '.join(r['status'])}]"
            ax.errorbar(xs, ys, yerr=es, fmt="o", ms=4, capsize=2, label=legend)
            s = {"artifact_id": r["artifact_id"], "record": str(r["path"].name), "record_sha256": r["sha256"],
                 "status": r["status"], "legend": legend, "variable": r["variable"], "edges": r["edges"],
                 "error_rule": r["error_rule"]}
            if r.get("transformation_record"):
                s["transformation_record"] = r["transformation_record"]
            series.append(s)
        var = records[0]["variable"]
        unit = records[0]["x_unit"]
        ax.set_xscale("log")
        if all(p["y"] > 0 for p in points):
            ax.set_yscale("log")
        ax.set_xlabel(f"{var}" + (f" [{unit}]" if unit else ""))
        ax.set_ylabel((f"x^{g:g} x " if g else "") + "flux" + (f" [{records[0]['y_unit']}]" if records[0]["y_unit"] and not args.to else ""))
        ax.legend(fontsize=8)
        if args.bin_position == "lafferty-wyatt":
            rule = f"Lafferty-Wyatt position for a power law of index {args.lw_index:g}"
        else:
            rule = {"center": "arithmetic bin centre", "log-center": "geometric bin centre"}[args.bin_position]
        caption = ("Spectrum from dataset-records: " + "; ".join(f"{s['artifact_id']} ({', '.join(s['status'])})"
                                                                 for s in series)
                   + f". Points at the {rule}" + (f"; flux weighted by {var}^{g:g}" if g else "")
                   + ("; converted to " + args.to + " with spectrum_transform.py (Jacobian and bin averaging)" if args.to else "")
                   + ". Error bars: " + "; ".join(sorted({s["error_rule"] for s in series})) + ".")
        if len(series) > 1:
            caption += " Overlaid series are not combined: no average or fit across them is shown or implied."
        fig.tight_layout()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.out)
        plt.close(fig)
        sidecar = args.sidecar or args.out.with_suffix(".json")
        sidecar.write_text(json.dumps({"figure": args.out.name, "caption": caption, "bin_position":
                                       {"rule": args.bin_position, "lw_index": args.lw_index},
                                       "weight_power": g, "series": series, "points": points}, indent=1) + "\n",
                           encoding="utf-8")
    except (InputError, OSError, ValueError) as exc:
        return refuse(str(exc))
    print(json.dumps({"status": "ok", **base, "figure": str(args.out), "sidecar": str(sidecar), "caption": caption,
                      "points": len(points)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
