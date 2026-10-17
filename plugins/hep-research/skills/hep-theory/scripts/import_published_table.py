#!/usr/bin/env python3
"""Turn a user-downloaded published table into a dataset-record with a provenance sidecar (Th8).

Purpose: compare a model with an experiment's published data without retyping numbers. The user downloads the table
(CSV, FITS, or a HEPData table export in JSON or YAML) and declares, in a spec read from the paper, what each column
means: the bin edges, the value, the unit and the uncertainty breakdown. The tool reads the file as it is, keeps every
value, and records where it came from. It never accesses the network.

Method:
- CSV: a header row; lines starting with '#' are comments. FITS: a binary table HDU (`hdu`, default 1; needs astropy).
  HEPData: `independent_variables[0]` bins (`low`/`high`) and `dependent_variables[dependent]` (default 0); error
  labels are matched by `label`; percent errors ("2%") become absolute; YAML needs PyYAML.
- Bins must be contiguous and increasing (edges = lows plus the last high).
- Uncertainty components: `column` (symmetric) or `plus` and `minus` (asymmetric, kept as two components and marked
  non-Gaussian); `relative: true` multiplies by the value. A HEPData label missing in a bin is 0 there with a note.
- Total check: when the spec names a total (`total.column`, or `total.label` for HEPData), the components are combined
  by the declared rule (`combination`: "quadrature", the default, or "linear" when the source says so) and compared
  bin by bin; a symmetric total is compared with the larger of the up and down combinations. A relative difference
  above `total_tolerance` (default 1e-3, for rounded tables) is reported as a warning and in total_check; the record is
  still written, since the published values are what they are.
- Correlations are not invented: every component is `correlation: unknown` and the covariance `absent`.

Spec (JSON): {"dataset_id": "ns:name", "observable": observable_spec (quantity, variables, level, normalization,
  bin_semantics, unit; read from the paper), "format": "csv" | "fits" | "hepdata", "columns": {"low", "high", "value"}
  (csv, fits), "hdu": 1, "dependent": 0, "uncertainties": [{"name", "kind" (statistical, systematic, ...),
  "column" | "plus"+"minus" | "label", "relative": false}], "total": {"column" | "label"} (optional),
  "combination": "quadrature", "total_tolerance": 1e-3, "evidence_id": "ns:C01" (optional),
  "source": {"url", "downloaded" (YYYY-MM-DD, the user's download date), "citation" (how the source asks to be cited)}}
Usage: import_published_table.py --table FILE --spec SPEC.json --out DIR [--created YYYY-MM-DD] [--status LABEL]
Output: DIR/dataset-record.json and DIR/provenance.json (sha256 of the file, URL, download date, citation request);
JSON on stdout with status, status_label (default user-supplied), inputs, defaults_used, total_check, warnings.
Exit codes: 0 written; 1 the record fails contracts/validate.py (nothing written); 2 bad input; 3 astropy or PyYAML
missing for a FITS or YAML file.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True  # importing plugin packages leaves no __pycache__ (F-10)
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.identity import plugin_release  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

RULES = ("quadrature", "linear")
HINTS = {"fits": "pip install astropy (FITS tables)", "yaml": "pip install PyYAML (HEPData YAML exports)"}


class InputError(ValueError):
    """A spec or table that cannot be read as declared."""


class MissingDependency(RuntimeError):
    def __init__(self, what: str):
        super().__init__(f"{what} is needed to read this file")
        self.install = HINTS[what]


def _num(x, ref: float = 0.0) -> float:
    if isinstance(x, str) and x.strip().endswith("%"):
        return abs(ref) * float(x.strip()[:-1]) / 100.0
    v = float(x)
    if not math.isfinite(v):
        raise InputError(f"non-finite number {x!r}")
    return v


def read_columns(path: Path, sp: dict) -> dict[str, list[float]]:
    """name -> column of floats, for CSV or FITS."""
    if sp["format"] == "csv":
        text = path.read_text(encoding="utf-8")
        rows = list(csv.DictReader(io.StringIO("\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#")))))
        if not rows:
            raise InputError(f"{path.name}: no data rows")
        try:
            return {k: [_num(r[k]) for r in rows] for k in rows[0]}
        except (TypeError, ValueError) as exc:
            raise InputError(f"{path.name}: {exc}") from exc
    try:
        from astropy.io import fits
    except ImportError as exc:
        raise MissingDependency("fits") from exc
    with fits.open(path) as hdul:
        data = hdul[int(sp.get("hdu", 1))].data
        return {n: [float(v) for v in data[n]] for n in data.columns.names}


def _col(cols: dict, name, what: str) -> list[float]:
    if not isinstance(name, str) or name not in cols:
        raise InputError(f"{what}: column {name!r} not in the table (columns: {sorted(cols)})")
    return cols[name]


def from_columns(cols: dict, sp: dict) -> tuple:
    c = sp.get("columns") or {}
    lows, highs, values = (_col(cols, c.get(k), k) for k in ("low", "high", "value"))
    comps = []
    for u in sp["uncertainties"]:
        rel = bool(u.get("relative"))
        scale = (lambda arr: [a * abs(v) for a, v in zip(arr, values)]) if rel else (lambda arr: list(arr))
        if "column" in u:
            comps.append({"name": u["name"], "kind": u["kind"], "values": scale(_col(cols, u["column"], u["name"])),
                          "correlation": "unknown"})
        elif "plus" in u and "minus" in u:
            for side, key in (("+", "plus"), ("-", "minus")):
                comps.append({"name": f"{u['name']} ({side})", "kind": u["kind"], "gaussian": False,
                              "values": [abs(x) for x in scale(_col(cols, u[key], u["name"]))], "correlation": "unknown"})
        else:
            raise InputError(f"uncertainty {u.get('name')!r}: give 'column', or 'plus' and 'minus'")
    total = _col(cols, sp["total"]["column"], "total") if sp.get("total") else None
    return lows, highs, values, comps, total


def from_hepdata(path: Path, sp: dict):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise MissingDependency("yaml") from exc
        table = yaml.safe_load(text)
    else:
        table = json.loads(text)
    try:
        ind = table["independent_variables"][0]["values"]
        dep = table["dependent_variables"][int(sp.get("dependent", 0))]["values"]
        lows, highs = [_num(b["low"]) for b in ind], [_num(b["high"]) for b in ind]
        values = [_num(v["value"]) for v in dep]
    except (KeyError, IndexError, TypeError) as exc:
        raise InputError(f"{path.name}: not a HEPData table with binned independent variables ({exc})") from exc

    def errors_for(label):
        sym, plus, minus, missing = [0.0] * len(values), [0.0] * len(values), [0.0] * len(values), []
        asym = False
        for i, v in enumerate(dep):
            found = [e for e in v.get("errors", []) if e.get("label") == label]
            if not found:
                missing.append(i)
                continue
            e = found[0]
            if "symerror" in e:
                sym[i] = plus[i] = minus[i] = abs(_num(e["symerror"], values[i]))
            else:
                asym = True
                plus[i], minus[i] = abs(_num(e["asymerror"]["plus"], values[i])), abs(_num(e["asymerror"]["minus"], values[i]))
        return asym, sym, plus, minus, missing

    comps = []
    for u in sp["uncertainties"]:
        if "label" not in u:
            raise InputError(f"uncertainty {u.get('name')!r}: a HEPData table needs 'label' (the error label)")
        asym, sym, plus, minus, missing = errors_for(u["label"])
        if len(missing) == len(values):
            raise InputError(f"error label {u['label']!r} is not in the table")
        note = {"note": f"not given in bins {missing} (0 there means not given)"} if missing else {}
        if asym:
            comps += [{"name": f"{u['name']} (+)", "kind": u["kind"], "gaussian": False, "values": plus,
                       "correlation": "unknown", **note},
                      {"name": f"{u['name']} (-)", "kind": u["kind"], "gaussian": False, "values": minus,
                       "correlation": "unknown", **note}]
        else:
            comps.append({"name": u["name"], "kind": u["kind"], "values": sym, "correlation": "unknown", **note})
    total = None
    if sp.get("total"):
        _, total, _, _, missing = errors_for(sp["total"].get("label"))
        if missing:
            raise InputError(f"total label {sp['total'].get('label')!r} missing in bins {missing}")
    return lows, highs, values, comps, total


def total_check(comps: list[dict], total: list[float], rule: str, tol: float) -> dict:
    def combine(vals):
        return math.sqrt(sum(v * v for v in vals)) if rule == "quadrature" else sum(vals)
    up = [c for c in comps if not c["name"].endswith("(-)")]
    down = [c for c in comps if not c["name"].endswith("(+)")]
    rel, differing = [], []
    for i, t in enumerate(total):
        comb = max(combine([c["values"][i] for c in up]), combine([c["values"][i] for c in down]))
        r = abs(comb - t) / abs(t) if t else abs(comb)
        rel.append(r)
        if r > tol:
            differing.append(i)
    return {"rule": rule, "tolerance": tol, "max_relative_difference": max(rel) if rel else 0.0,
            "bins_differing": differing, "consistent": not differing,
            "note": "a symmetric total is compared with the larger of the up and down combinations"}


def build(path: Path, sp: dict, created: str, status: str) -> tuple[dict, dict, dict]:
    for key in ("dataset_id", "observable", "format", "uncertainties", "source"):
        if key not in sp:
            raise InputError(f"spec: '{key}' is required")
    if sp["format"] not in ("csv", "fits", "hepdata"):
        raise InputError("spec: format must be csv, fits or hepdata")
    src = sp["source"]
    for key in ("url", "downloaded", "citation"):
        if not isinstance(src.get(key), str) or not src[key].strip():
            raise InputError(f"spec.source: '{key}' is required (provenance travels with the values)")
    rule = sp.get("combination", "quadrature")
    if rule not in RULES:
        raise InputError(f"spec: combination must be one of {list(RULES)}")
    if sp["format"] == "hepdata":
        lows, highs, values, comps, total = from_hepdata(path, sp)
    else:
        lows, highs, values, comps, total = from_columns(read_columns(path, sp), sp)
    n = len(values)
    if not n or len(lows) != n or len(highs) != n:
        raise InputError("the table has no bins, or the edge and value columns differ in length")
    for i in range(n):
        if not lows[i] < highs[i] or (i and lows[i] != highs[i - 1]):
            raise InputError(f"bins must be contiguous and increasing (bin {i}: [{lows[i]}, {highs[i]}])")
    edges = lows + [highs[-1]]
    observable = json.loads(json.dumps(sp["observable"]))
    observable["variables"][0]["edges"] = edges
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    check = total_check(comps, total, rule, float(sp.get("total_tolerance", 1e-3))) if total else None
    doc = {
        "contract_version": CONTRACTS_VERSION, "artifact_id": sp["dataset_id"].split(":", 1)[-1],
        "artifact_type": "dataset-record",
        "objective": f"user-supplied values of a published table ({src['url']})",
        "provenance": {"producer_skill": "hep-theory", "created": created,
                       "tool": "skills/hep-theory/scripts/import_published_table.py"},
        "status": [status], "bindings": {"experiments": [], "theory": []},
        "versions": {"plugin": json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"],
                     "contracts": CONTRACTS_VERSION, "profiles": {}, "plugin_release": plugin_release()},
        "inputs": [], "outputs": [], "unresolved_inputs": [],
        "extension": {"dataset_id": sp["dataset_id"],
                      "source_evidence_ids": [sp["evidence_id"]] if sp.get("evidence_id") else [],
                      "observable": observable,
                      "data": {"edges": edges, "values": values, "unit": observable["unit"], "uncertainties": comps},
                      "covariance": {"status": "absent", "note": "the table gives no covariance; components are not "
                                                                 "assumed uncorrelated"},
                      "period": "not-provided", "status": "user-supplied"},
    }
    prov = {"file": path.name, "sha256": sha, "format": sp["format"], "url": src["url"], "downloaded": src["downloaded"],
            "citation_request": src["citation"], "network_access": False,
            "spec_sha256": hashlib.sha256(json.dumps(sp, sort_keys=True).encode()).hexdigest(),
            "note": "values as in the downloaded file; read by import_published_table.py without network access"}
    return doc, prov, check


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--table", type=Path, required=True)
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--created", default=date.today().isoformat(), help="YYYY-MM-DD (default today)")
    add_status_argument(ap, default="user-supplied")
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {"table": str(args.table), "spec": str(args.spec), "out": str(args.out), "created": args.created}
    base = {"status_label": args.status, "inputs": inputs}
    try:
        sp = json.loads(args.spec.read_text(encoding="utf-8"))
        doc, prov, check = build(args.table, sp, args.created, args.status)
    except MissingDependency as exc:
        print(json.dumps({"status": "missing-dependency", **base, "error": str(exc), "install": exc.install}, indent=1))
        return exit_code("missing-dependency")
    except (InputError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "rejected", **base, "error": f"{type(exc).__name__}: {exc}"}, indent=1))
        return exit_code("rejected")
    defaults = [k for k in ("created", "status") if f"--{k}" not in given]
    defaults += [k for k in ("combination", "total_tolerance") if k not in sp and sp.get("total")]
    rep = validate_artifact(doc)
    if rep.errors:
        print(json.dumps({"status": "refused", **base, "defaults_used": defaults,
                          "contract_errors": [f.__dict__ for f in rep.errors]}, default=str, indent=1))
        return exit_code("refused")
    warnings = []
    if check and not check["consistent"]:
        warnings.append(f"the breakdown combined by {check['rule']} differs from the total in bins "
                        f"{check['bins_differing']} (max relative difference {check['max_relative_difference']:.3g})")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "dataset-record.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    (args.out / "provenance.json").write_text(json.dumps(prov, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", **base, "defaults_used": defaults, "dataset_id": sp["dataset_id"],
                      "bins": len(doc["extension"]["data"]["values"]), "sha256": prov["sha256"],
                      "total_check": check, "warnings": warnings,
                      "out": [str(args.out / "dataset-record.json"), str(args.out / "provenance.json")]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
