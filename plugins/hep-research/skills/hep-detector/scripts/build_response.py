#!/usr/bin/env python3
"""Build a response (migration) artifact from matched truth, reco, weight and selection flag (D9).

Purpose: one place where a response matrix is made with its conventions written down: direction (rows reco, columns
truth), normalization, where the inefficiency and the acceptance live, and how events outside the reco axis are kept
(explicit under/overflow per truth bin). The artifact must pass contracts/validate.py (strict) and
contracts/response_adapter.py --validate, or nothing is written. See
<plugin root>/skills/hep-detector/references/response-and-forward-folding.md.

Method: events with a truth value inside the truth axis are the generated events of their truth bin; a selected event
lands in the reco bin of its reco value, or in the underflow or overflow of its truth bin. With weights w (no negative
weights; those are hep-statistics' to handle):
  conditional_on_generated  M_ij = sum_sel(i, j) w / sum_gen(j) w; column sums with the flows equal the selection
                            efficiency (inefficiency inside the matrix)
  conditional_on_selected   M_ij = sum_sel(i, j) w / sum_sel(j) w; columns with the flows sum to 1 (inefficiency
                            outside, listed under applied_separately)
The artifact's mc_stat carries the generated (or, outside, selected) event counts per truth bin for unit weights, or
the per-cell sum of w^2 for weights; correction_space puts separately applied corrections in truth space.
MC uncertainty of each entry: the delta-method variance of the weighted multinomial fraction,
  var(P_ij) = (S2_ij (1 - P_ij)^2 + (S2_j - S2_ij) P_ij^2) / W_j^2,  S2 = sums of w^2, W_j the column denominator,
which is P(1 - P)/N for unit weights. Per truth bin, resolution of the declared residual (reco - truth, reco/truth - 1,
or 1/reco - 1/truth) over selected events: weighted median, sigma68 = (q84 - q16)/2, MAD and sigma_mad = 1.4826 MAD,
and the tail fraction (|r - median| > 3 sigma68). Events with truth outside the truth axis are counted, not used.
--fold folds a truth spectrum through the artifact with contracts/response_adapter.py.

Assumptions: the events are a matched sample (each row one generated event, its reco value present when selected);
the truth axis is the fiducial phase space; the acceptance placement is declared by the user (--acceptance).

Input: CSV with a header, JSON Lines or a JSON list; empty or non-numeric reco for unselected events is ignored.
Usage:
  build_response.py build EVENTS --truth-col C --reco-col C (--weight-col C | --unweighted)
      (--selected-col C | --all-selected) (--truth-edges E ... --reco-edges E ... | --bins BINS.json)
      --variable NAME --unit U [--reco-variable NAME --reco-unit U --variable-conversion TEXT]
      --normalization {conditional_on_generated,conditional_on_selected} --acceptance {inside_matrix,outside_matrix}
      --residual {difference,ratio,inverse} --intended-use {forward_folding,unfolding,parametric_fit}
      --artifact-id ID --objective TEXT --out ARTIFACT.json [--created YYYY-MM-DD] [--provenance TEXT]
      [--applied-separately TERM ...] [--fold TRUTH.json] [--status LABEL] [--also-status LABEL ...]
      [--input-record ARTIFACT.json ... [--project-root DIR]]   (inputs with sha256 and status; their propagating
      labels are carried)
  BINS.json: {"truth_edges": [...], "reco_edges": [...]}; TRUTH.json: {"truth": [...]} or a list.
Output JSON: status (ok, refused, rejected), status_label, inputs, defaults_used, out, selection_efficiency per truth
bin, counts, validation (contracts_validate, response_validation) and, with --fold, the folded reco spectrum.
Exit codes: 0 written; 1 refused (the artifact fails its validation; nothing written); 2 bad input. Standard library
only.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import bisect
import csv
import hashlib
import io
import json
import math
import sys
from datetime import date
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True  # importing core and contracts leaves no __pycache__ (F-10)
sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts import trace  # noqa: E402
from contracts.identity import plugin_release  # noqa: E402
from contracts.response_adapter import fold as adapter_fold  # noqa: E402
from contracts.response_adapter import to_validator_input  # noqa: E402
from contracts.validate import Vocabulary, validate_artifact  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402
from core.status import ARTIFACT_LABELS as STATUSES_ALL, add_status_argument, exit_code  # noqa: E402

RESIDUALS = {"difference": lambda r, t: r - t, "ratio": lambda r, t: r / t - 1.0, "inverse": lambda r, t: 1.0 / r - 1.0 / t}
TAIL_SIGMAS = 3.0


class InputError(ValueError):
    pass


def _float(value, where: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise InputError(f"{where}: {value!r} is not a number") from None
    if not math.isfinite(x):
        raise InputError(f"{where}: {value!r} is not finite")
    return x


def _edges(values, name: str) -> list[float]:
    out = [_float(v, name) for v in values]
    if len(out) < 2 or any(b <= a for a, b in zip(out, out[1:])):
        raise InputError(f"{name} needs at least two strictly increasing edges")
    return out


def _flag(value, where: str) -> bool:
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "1.0"):
        return True
    if text in ("0", "false", "no", "0.0"):
        return False
    raise InputError(f"{where}: selection flag {value!r} is not 0/1 or true/false")


def read_rows(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc.strerror or exc}") from None
    s = text.lstrip()
    try:
        if path.suffix == ".csv" or not s.startswith(("{", "[")):
            # '#' lines are comments (a SYNTHETIC label header), as in the other hep-detector scripts
            rows = list(csv.DictReader(line for line in io.StringIO(text) if not line.startswith("#")))
        elif s.startswith("["):
            rows = json.loads(text)
        else:
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    except ValueError as exc:
        raise InputError(f"{path}: not CSV, JSON Lines or a JSON list ({exc})") from None
    if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
        raise InputError(f"{path}: no event records")
    return rows


def _quantile(pairs: list[tuple[float, float]], q: float) -> float:
    """Weighted quantile of sorted (value, weight) pairs, interpolating between midpoints of the cumulative weight."""
    total = sum(w for _, w in pairs)
    acc, mids = 0.0, []
    for v, w in pairs:
        mids.append((acc + 0.5 * w) / total)
        acc += w
    k = bisect.bisect_left(mids, q)
    if k == 0:
        return pairs[0][0]
    if k >= len(pairs):
        return pairs[-1][0]
    f = (q - mids[k - 1]) / (mids[k] - mids[k - 1])
    return pairs[k - 1][0] + f * (pairs[k][0] - pairs[k - 1][0])


def resolution(values: list[tuple[float, float]]) -> dict:
    if not values:
        return {"n": 0, "sum_w": 0.0, "median": None, "sigma68": None, "mad": None, "sigma_mad": None,
                "tail_fraction": None}
    pairs = sorted(values)
    med = _quantile(pairs, 0.5)
    s68 = 0.5 * (_quantile(pairs, 0.84134474606854293) - _quantile(pairs, 0.15865525393145707))
    dev = sorted((abs(v - med), w) for v, w in pairs)
    mad = _quantile(dev, 0.5)
    sw = sum(w for _, w in pairs)
    tail = sum(w for v, w in pairs if abs(v - med) > TAIL_SIGMAS * s68) / sw if s68 > 0 else 0.0
    return {"n": len(pairs), "sum_w": sw, "median": med, "sigma68": s68, "mad": mad, "sigma_mad": 1.482602218505602 * mad,
            "tail_fraction": tail, "tail_definition": f"|r - median| > {TAIL_SIGMAS:g} sigma68"}


def build(args, rows: list[dict]) -> tuple[dict, dict]:
    te, re_ = args.truth_edges, args.reco_edges
    nt, nr = len(te) - 1, len(re_) - 1
    w_cell = [[0.0] * nt for _ in range(nr)]
    w2_cell = [[0.0] * nt for _ in range(nr)]
    under, over, under2, over2 = [0.0] * nt, [0.0] * nt, [0.0] * nt, [0.0] * nt
    gen, gen2, sel, sel2 = [0.0] * nt, [0.0] * nt, [0.0] * nt, [0.0] * nt
    n_gen, n_sel_bin = [0] * nt, [0] * nt
    resid: list[list[tuple[float, float]]] = [[] for _ in range(nt)]
    outside, n_sel = 0, 0
    res_f = RESIDUALS[args.residual]
    for i, row in enumerate(rows):
        where = f"event {i + 1}"
        if args.truth_col not in row:
            raise InputError(f"{where}: no column {args.truth_col!r}")
        t = _float(row[args.truth_col], f"{where} truth")
        w = 1.0 if args.unweighted else _float(row.get(args.weight_col), f"{where} weight")
        if w < 0:
            raise InputError(f"{where}: negative weight {w}; negative weights are handled in hep-statistics, not here")
        selected = True if args.all_selected else _flag(row.get(args.selected_col), f"{where} {args.selected_col}")
        if not te[0] <= t < te[-1]:
            outside += 1
            continue
        j = bisect.bisect_right(te, t) - 1
        gen[j] += w
        gen2[j] += w * w
        n_gen[j] += 1
        if not selected:
            continue
        r = _float(row.get(args.reco_col), f"{where} reco (a selected event needs a reco value)")
        n_sel += 1
        n_sel_bin[j] += 1
        sel[j] += w
        sel2[j] += w * w
        if r < re_[0]:
            under[j] += w
            under2[j] += w * w
        elif r >= re_[-1]:
            over[j] += w
            over2[j] += w * w
        else:
            i_r = bisect.bisect_right(re_, r) - 1
            w_cell[i_r][j] += w
            w2_cell[i_r][j] += w * w
        try:
            resid[j].append((res_f(r, t), w))
        except ZeroDivisionError:
            raise InputError(f"{where}: residual {args.residual!r} is undefined at zero") from None
    denom, denom2 = (gen, gen2) if args.normalization == "conditional_on_generated" else (sel, sel2)
    empty = [j for j in range(nt) if denom[j] <= 0]

    def frac(x, j):
        return x / denom[j] if denom[j] > 0 else 0.0

    def unc(s1, s2, j):
        if denom[j] <= 0:
            return 0.0
        p = s1 / denom[j]
        return math.sqrt(max(s2 * (1 - p) ** 2 + (denom2[j] - s2) * p * p, 0.0)) / denom[j]

    matrix = [[frac(w_cell[i][j], j) for j in range(nt)] for i in range(nr)]
    mc = [[unc(w_cell[i][j], w2_cell[i][j], j) for j in range(nt)] for i in range(nr)]
    inside = args.normalization == "conditional_on_generated"
    applied = list(args.applied_separately or [])
    for term, needed in (("efficiency", not inside), ("acceptance", args.acceptance == "outside_matrix")):
        if needed and term not in applied:
            applied.append(term)
    ext = {"truth_axis": {"name": args.variable, "unit": args.unit, "edges": te},
           "reco_axis": {"name": args.reco_variable or args.variable, "unit": args.reco_unit or args.unit, "edges": re_},
           "orientation": "rows_reco_cols_truth", "normalization": args.normalization,
           "inefficiency": "inside_matrix" if inside else "outside_matrix", "acceptance": args.acceptance,
           "includes": ["migration", "efficiency"] if inside else ["migration"], "applied_separately": applied,
           "underflow_overflow": "explicit_bins", "intended_use": args.intended_use,
           "conditions": f"built by build_response.py from {Path(args.events).name}: {len(rows)} events, "
                         f"{outside} with truth outside the truth axis (not used)",
           "provenance": args.provenance or "matched truth/reco sample supplied by the user",
           "form": "matrix", "matrix": matrix,
           "underflow": [frac(u, j) for j, u in enumerate(under)], "overflow": [frac(o, j) for j, o in enumerate(over)],
           "generated_per_truth_bin": gen,
           "build_diagnostics": {"mc_uncertainty": mc, "mc_uncertainty_method": "delta-method weighted multinomial",
                                 "underflow_uncertainty": [unc(under[j], under2[j], j) for j in range(nt)],
                                 "overflow_uncertainty": [unc(over[j], over2[j], j) for j in range(nt)],
                                 "residual": args.residual, "resolution": [resolution(v) for v in resid],
                                 "effective_entries": [(denom[j] ** 2 / denom2[j]) if denom2[j] > 0 else 0.0
                                                       for j in range(nt)],
                                 "empty_truth_bins": empty}}
    if applied:
        ext["correction_space"] = {t: {"space": "truth"} for t in applied}
    if args.unweighted:
        ext["mc_stat"] = {"kind": "generated_counts", "weighted": False,
                          "events_per_truth_bin": n_gen if inside else n_sel_bin}
    else:
        ext["mc_stat"] = {"kind": "sumw2", "weighted": True, "signed_weights": False, "sumw2": w2_cell}
    if args.variable_conversion:
        ext["variable_conversion"] = args.variable_conversion
    counts = {"events": len(rows), "truth_outside_axis": outside, "selected_in_axis": n_sel, "empty_truth_bins": empty}
    efficiency = [sel[j] / gen[j] if gen[j] > 0 else None for j in range(nt)]
    return ext, {"counts": counts, "selection_efficiency": efficiency}


def envelope(args, ext: dict) -> dict:
    plugin_version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": args.artifact_id, "artifact_type": "response",
            "objective": args.objective, "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": plugin_version, "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release(),
                         "profiles": {}},
            "provenance": {"producer_skill": "hep-detector", **trace.provenance(), "created": args.created, "evidence_ids": []},
            "inputs": linked_inputs(args), "outputs": [], "status": labels(args), "unresolved_inputs": [],
            "extension": ext}


STICKY = ("failed", "unvalidated", "preliminary", "synthetic", "asimov", "user-supplied")


def linked_inputs(args) -> list[dict]:
    """--input-record: artifacts the events came from (for example Geant4 run records), as inputs with sha256 and
    their status, refs relative to --project-root (default the folder of --out)."""
    root = Path(args.project_root or Path(args.out).parent).resolve()
    out = []
    for path in args.input_record or []:
        p = Path(path).resolve()
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InputError(f"cannot read --input-record {path}: {exc}") from None
        if not isinstance(doc, dict) or "artifact_type" not in doc:
            raise InputError(f"--input-record {path} is not a contract artifact")
        try:
            ref = p.relative_to(root).as_posix()
        except ValueError:
            raise InputError(f"--input-record {path} is outside the project root {root}") from None
        out.append({"ref": ref, "artifact_type": doc.get("artifact_type"), "artifact_id": doc.get("artifact_id"),
                    "version": doc.get("contract_version"), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "status": list(doc.get("status", []))})
    return out


def labels(args) -> list[str]:
    """--status, every --also-status, and every propagating label the linked inputs carry."""
    out = [args.status] + list(args.also_status or [])
    out += [s for i in linked_inputs(args) for s in i["status"] if s in STICKY]
    return list(dict.fromkeys(out))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build", help="build and validate a response artifact")
    p.add_argument("events")
    p.add_argument("--truth-col", required=True)
    p.add_argument("--reco-col", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--weight-col")
    g.add_argument("--unweighted", action="store_true")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--selected-col")
    g.add_argument("--all-selected", action="store_true")
    p.add_argument("--truth-edges", nargs="+")
    p.add_argument("--reco-edges", nargs="+")
    p.add_argument("--bins")
    p.add_argument("--variable", required=True)
    p.add_argument("--unit", required=True)
    p.add_argument("--reco-variable")
    p.add_argument("--reco-unit")
    p.add_argument("--variable-conversion")
    p.add_argument("--normalization", required=True, choices=("conditional_on_generated", "conditional_on_selected"))
    p.add_argument("--acceptance", required=True, choices=("inside_matrix", "outside_matrix"))
    p.add_argument("--residual", required=True, choices=sorted(RESIDUALS))
    p.add_argument("--intended-use", required=True, choices=("forward_folding", "unfolding", "parametric_fit"))
    p.add_argument("--artifact-id", required=True)
    p.add_argument("--objective", required=True)
    p.add_argument("--created", default=date.today().isoformat())
    p.add_argument("--provenance")
    p.add_argument("--applied-separately", action="append")
    p.add_argument("--fold")
    p.add_argument("--out", required=True)
    p.add_argument("--input-record", action="append",
                   help="an artifact the events came from (repeatable): linked as an input with sha256 and status")
    p.add_argument("--project-root", help="refs of --input-record are relative to this folder (default: --out's)")
    p.add_argument("--also-status", action="append", choices=STATUSES_ALL,
                   help="a further status label of the response (repeatable)")
    add_status_argument(p)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    report: dict = {"status_label": args.status, "inputs": {k: v for k, v in vars(args).items()},
                    "defaults_used": [k for k in ("created", "status") if f"--{k}" not in given]}
    out = Path(args.out)
    try:
        if args.bins:
            if args.truth_edges or args.reco_edges:
                raise InputError("give --bins or --truth-edges/--reco-edges, not both")
            try:
                bins = json.loads(Path(args.bins).read_text(encoding="utf-8"))
                args.truth_edges, args.reco_edges = bins["truth_edges"], bins["reco_edges"]
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise InputError(f"cannot read the bins {args.bins}: {exc}") from None
        if not args.truth_edges or not args.reco_edges:
            raise InputError("the truth and reco edges are required (--truth-edges/--reco-edges or --bins)")
        args.truth_edges = _edges(args.truth_edges, "truth edges")
        args.reco_edges = _edges(args.reco_edges, "reco edges")
        if bool(args.reco_variable) != bool(args.reco_unit):
            raise InputError("--reco-variable and --reco-unit go together")
        if args.reco_variable and args.reco_variable != args.variable and not args.variable_conversion:
            raise InputError("a reco variable different from the truth variable needs --variable-conversion")
        ext, extra = build(args, read_rows(Path(args.events)))
        doc = envelope(args, ext)
        rep = validate_artifact(doc, Vocabulary(), strict=True).as_dict()
        conv = to_validator_input(ext, contract_version=CONTRACTS_VERSION)
        val = validate_response(conv["input"]) if conv["ok"] else {"status": "fail", "errors": conv["errors"]}
        report.update(extra)
        report["validation"] = {"contracts_validate": "ok" if rep.get("ok") else "fail",
                                "contracts_findings": [f for f in rep.get("findings", []) if f.get("severity") == "error"],
                                "response_validation": val.get("status"),
                                "response_errors": val.get("errors", []), "response_warnings": val.get("warnings", [])}
        if not rep.get("ok") or val.get("status") == "fail":
            report.update(status="refused", error="the response fails its validation; nothing was written")
        else:
            if args.fold:
                try:
                    tdoc = json.loads(Path(args.fold).read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise InputError(f"cannot read the truth spectrum {args.fold}: {exc}") from None
                truth = tdoc.get("truth") if isinstance(tdoc, dict) else tdoc
                if not isinstance(truth, list) or len(truth) != len(args.truth_edges) - 1:
                    raise InputError(f"the truth spectrum needs {len(args.truth_edges) - 1} values")
                truth = [_float(x, "truth spectrum") for x in truth]
                report["folded"] = {"truth": truth, "reco": adapter_fold(conv["input"], truth),
                                    "method": "contracts/response_adapter.py fold"}
            text = json.dumps(doc, indent=1) + "\n"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            report.update(status="ok", out=str(out))
    except InputError as exc:
        report.update(status="rejected", error=str(exc))
    except OSError as exc:
        report.update(status="rejected", error=f"cannot write {out}: {exc.strerror or exc}")
    print(json.dumps(report, indent=1, default=str))
    if report["status"] != "ok":
        print(f"build_response.py: error: {report.get('error')}", file=sys.stderr)
    return exit_code(report["status"])


if __name__ == "__main__":
    sys.exit(main())
