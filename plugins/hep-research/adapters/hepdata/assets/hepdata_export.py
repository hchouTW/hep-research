#!/usr/bin/env python3
"""Write a HEPData submission (submission.yaml and table YAML files) from a binned contract artifact.

Purpose: the reverse of hepdata_record.py. A dataset-record (or a prediction with binned values) already carries the
numbers, their uncertainty components, the covariance file and the observable's definition; this writes them in the
HEPData submission format so they can be uploaded or shared without retyping.

What it writes into --out:
- `submission.yaml`: a submission-wide comment, then one entry per table (name, description, keywords, data file);
- `<table>.yaml`: the bin edges of the observable's first variable as the independent variable, the values as the
  dependent variable with the quantity and unit as header, qualifiers from the observable (process, level, phase
  space, normalization and the record's conditions), and each uncertainty component as a labelled error: per-bin
  values as `symerror`, a "(+)"/"(-)" pair of non-Gaussian components as `asymerror`, and a component that exists only
  as a covariance as the square root of its diagonal (labelled "..., from the covariance diagonal");
- `<table>-covariance.yaml`, when the artifact's covariance is present: the full matrix, one entry per pair of bins,
  each bin given by its range, so hepdata_record.py reads it back by labels.
Status labels are never dropped: a synthetic, asimov, preliminary or unvalidated artifact says so in the submission
comment, every table description and a `phrases` keyword ("status: synthetic").

With --engine hepdata_lib (when the package is installed) the files are written by hepdata_lib instead of the
standard-library writer (YAML written as JSON documents, which YAML reads). Check the result with hepdata-validator.

Usage: hepdata_export.py --artifact RECORD.json --out DIR [--table-name "Table 1"] [--description TEXT]
       [--engine plain|hepdata_lib]
Exit 0 written, 1 refused (invalid artifact, unsupported shape, missing covariance file), 2 bad arguments.
Standard library only for the plain engine.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
from contracts.validate import validate_artifact  # noqa: E402

FLAGGED = ("synthetic", "asimov", "preliminary", "unvalidated", "failed")


class Refused(ValueError):
    """The artifact cannot be written as a HEPData table."""


def _payload(doc: dict) -> dict:
    ext = doc["extension"]
    if doc["artifact_type"] == "dataset-record" and isinstance(ext.get("data"), dict):
        return ext["data"]
    if doc["artifact_type"] == "prediction" and isinstance(ext.get("values"), dict):
        return ext["values"]
    raise Refused(f"no binned values in this {doc['artifact_type']} (dataset-record data or prediction values)")


def _status(doc: dict) -> list[str]:
    labels = set(doc.get("status") or [])
    ext_status = doc["extension"].get("status")
    if isinstance(ext_status, str):
        labels.add({"published": "observed"}.get(ext_status, ext_status))
    return sorted(labels)


def _qualifiers(doc: dict) -> list[dict]:
    obs = doc["extension"].get("observable") or {}
    out = []
    for name, value in (("Process", obs.get("process")), ("Level", obs.get("level")),
                        ("Phase space", (obs.get("phase_space") or {}).get("definition")),
                        ("Normalization", (obs.get("normalization") or {}).get("kind")),
                        ("Conditions", doc["extension"].get("conditions"))):
        if value:
            out.append({"name": name, "value": str(value)})
    return out


def _errors(payload: dict, n: int, base: Path) -> tuple[list[list[dict]], dict | None]:
    """Per-bin error lists, and the covariance matrix with its file name when one is referenced."""
    errors: list[list[dict]] = [[] for _ in range(n)]
    comps = payload.get("uncertainties") or []
    paired = {}
    for c in comps:
        m = re.fullmatch(r"(.*) \(([+-])\)", c["name"])
        if m and c.get("gaussian") is False and "values" in c:
            paired.setdefault(m.group(1), {})[m.group(2)] = c["values"]
    cov = None
    for c in comps:
        m = re.fullmatch(r"(.*) \(([+-])\)", c["name"])
        if m and m.group(1) in paired:
            if m.group(2) == "+" and "-" in paired[m.group(1)]:
                for i in range(n):
                    errors[i].append({"asymerror": {"plus": paired[m.group(1)]["+"][i],
                                                    "minus": -abs(paired[m.group(1)]["-"][i])}, "label": m.group(1)})
            continue
        if "values" in c:
            if len(c["values"]) != n:
                raise Refused(f"uncertainty '{c['name']}' has {len(c['values'])} values for {n} bins")
            for i in range(n):
                errors[i].append({"symerror": c["values"][i], "label": c["name"]})
        elif c.get("covariance_ref"):
            ref = base / c["covariance_ref"]
            if not ref.is_file():
                raise Refused(f"covariance file {c['covariance_ref']} not found next to the artifact")
            matrix = json.loads(ref.read_text(encoding="utf-8"))["matrix"]
            if len(matrix) != n or any(len(r) != n for r in matrix):
                raise Refused(f"covariance {c['covariance_ref']} is not {n} x {n}")
            cov = {"matrix": matrix, "label": c["name"], "file": c["covariance_ref"]}
            for i in range(n):
                errors[i].append({"symerror": math.sqrt(max(matrix[i][i], 0.0)),
                                  "label": f"{c['name']}, from the covariance diagonal"})
        else:
            raise Refused(f"uncertainty '{c['name']}' has neither per-bin values nor a covariance; nothing to write")
    return errors, cov


def build_tables(doc: dict, base: Path, table_name: str, description: str) -> tuple[str, list[tuple[dict, dict]]]:
    rep = validate_artifact(doc)
    if not rep.ok:
        raise Refused("the artifact does not validate: " + "; ".join(f"{f.path} {f.code}" for f in rep.errors[:5]))
    obs = doc["extension"].get("observable") or {}
    variables = obs.get("variables") or []
    if len(variables) != 1:
        raise Refused(f"only one-dimensional observables are written (this one has {len(variables)} variables)")
    payload = _payload(doc)
    edges, values = payload.get("edges") or variables[0].get("edges"), payload.get("values")
    if not edges or not values or len(values) != len(edges) - 1:
        raise Refused("binned values need edges with one more entry than values (point values are not written)")
    statuses = _status(doc)
    flagged = [s for s in statuses if s in FLAGGED]
    note = f"{' and '.join(s.upper() for s in flagged)} values, not a measurement. " if flagged else ""
    n = len(values)
    errors, cov = _errors(payload, n, base)
    var = variables[0]
    unit = payload.get("unit") or obs.get("unit", "")
    keywords = [{"name": "observables", "values": [obs.get("quantity", "")]},
                {"name": "phrases", "values": [f"status: {x}" for x in statuses]}]  # HEPData allows only four keyword names
    table = {"independent_variables": [{"header": {"name": var["name"], "units": var.get("unit", "")},
                                        "values": [{"low": edges[i], "high": edges[i + 1]} for i in range(n)]}],
             "dependent_variables": [{"header": {"name": obs.get("quantity", "value"), "units": unit},
                                      "qualifiers": _qualifiers(doc),
                                      "values": [{"value": values[i], "errors": errors[i]} for i in range(n)]}]}
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", table_name).strip("_") or "table"
    entries = [({"name": table_name, "description": note + (description or doc.get("objective", "")),
                 "keywords": keywords, "data_file": f"{slug}.yaml"}, table)]
    if cov:
        cells = [(i, j) for i in range(n) for j in range(n)]
        rng = [{"low": edges[i], "high": edges[i + 1]} for i in range(n)]
        cov_table = {"independent_variables": [
            {"header": {"name": f"{var['name']} (row)", "units": var.get("unit", "")}, "values": [rng[i] for i, _ in cells]},
            {"header": {"name": f"{var['name']} (column)", "units": var.get("unit", "")}, "values": [rng[j] for _, j in cells]}],
            "dependent_variables": [{"header": {"name": f"Covariance of {cov['label']}", "units": f"({unit})^2"},
                                     "values": [{"value": cov["matrix"][i][j]} for i, j in cells]}]}
        entries.append(({"name": f"{table_name} covariance", "keywords": keywords,
                         "description": note + f"Covariance matrix of '{cov['label']}' for {table_name}, one entry per pair of bins.",
                         "data_file": f"{slug}-covariance.yaml"}, cov_table))
    comment = note + f"{doc.get('objective', '')} Written from {doc['artifact_type']} {doc.get('artifact_id', '')} " \
                     f"by hep-research adapters/hepdata/assets/hepdata_export.py; status: {', '.join(statuses)}."
    return comment, entries


def write_plain(out: Path, comment: str, entries) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    docs = [json.dumps({"comment": comment}, indent=1)] + [json.dumps(meta, indent=1) for meta, _ in entries]
    (out / "submission.yaml").write_text("---\n".join(d + "\n" for d in docs), encoding="utf-8")
    for meta, table in entries:
        (out / meta["data_file"]).write_text(json.dumps(table, indent=1) + "\n", encoding="utf-8")
    return ["submission.yaml"] + [meta["data_file"] for meta, _ in entries]


def write_hepdata_lib(out: Path, comment: str, entries) -> list[str]:
    from hepdata_lib import Submission, Table, Uncertainty, Variable
    sub = Submission()
    sub.comment = comment
    for meta, table in entries:
        t = Table(meta["name"])
        t.description = meta["description"]
        for kw in meta["keywords"]:
            t.keywords[kw["name"]] = kw["values"]
        for iv in table["independent_variables"]:
            v = Variable(iv["header"]["name"], is_independent=True, is_binned=True, units=iv["header"]["units"])
            v.values = [(x["low"], x["high"]) for x in iv["values"]]
            t.add_variable(v)
        for dv in table["dependent_variables"]:
            v = Variable(dv["header"]["name"], is_independent=False, is_binned=False, units=dv["header"]["units"],
                         zero_uncertainties_warning=False)
            v.values = [x["value"] for x in dv["values"]]
            for q in dv.get("qualifiers", []):
                v.add_qualifier(q["name"], q["value"])
            labels = [e["label"] for e in dv["values"][0].get("errors", [])] if dv["values"] else []
            for k, label in enumerate(labels):
                sym = "symerror" in dv["values"][0]["errors"][k]
                u = Uncertainty(label, is_symmetric=sym)
                u.values = [x["errors"][k]["symerror"] if sym else
                            (x["errors"][k]["asymerror"]["minus"], x["errors"][k]["asymerror"]["plus"]) for x in dv["values"]]
                v.add_uncertainty(u)
            t.add_variable(v)
        sub.add_table(t)
    sub.create_files(str(out), validate=False, remove_old=True)
    return sorted(p.name for p in out.iterdir() if p.suffix == ".yaml")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--artifact", type=Path, required=True, help="a dataset-record or binned prediction artifact")
    ap.add_argument("--out", type=Path, required=True, help="directory for submission.yaml and the tables")
    ap.add_argument("--table-name", default="Table 1")
    ap.add_argument("--description", default="", help="table description (default: the artifact's objective)")
    ap.add_argument("--engine", choices=("plain", "hepdata_lib"), default="plain")
    args = ap.parse_args(argv)
    try:
        doc = json.loads(args.artifact.read_text(encoding="utf-8"))
        comment, entries = build_tables(doc, args.artifact.parent, args.table_name, args.description)
        if args.engine == "hepdata_lib":
            try:
                import hepdata_lib  # noqa: F401
            except ImportError:
                print(json.dumps({"status": "failed", "reason": "hepdata_lib is not installed: pip install hepdata_lib"}))
                return 1
            files = write_hepdata_lib(args.out, comment, entries)
        else:
            files = write_plain(args.out, comment, entries)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}))
        return 1
    print(json.dumps({"status": "written", "out": str(args.out), "files": files, "engine": args.engine}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
