#!/usr/bin/env python3
"""LaTeX macros and result tables from statistical-result and dataset-record artifacts, each number annotated with
the artifact it came from (Com7).

Purpose: numbers in a paper are copied from artifacts, never retyped. Every macro is preceded by a comment naming the
artifact id, its sha256, the key the value came from and the rounding rule, and a JSON manifest (--manifest) records
the same, so a reviewer can trace each printed digit back.
Rounding: --rounding pdg (default; Review of Particle Physics, Introduction 5.3: the three highest digits of the
uncertainty 100-354 keep two significant digits, 355-949 one, 950-999 round up to 1000 and keep two; the value
keeps the uncertainty's precision), or decimals:n / significant:n applied to both.
Watermarks: values from an artifact labelled synthetic or asimov are wrapped in \\hepSynthetic{...}, preliminary or
unvalidated ones in \\hepPreliminary{...}. Both print the value in a draft; a final build defines \\hepfinalbuild
before \\input-ing this file, and then they stop the build with an error. Observed and user-supplied values are not
wrapped.
HEPData: hepdata_export.py takes dataset-records, not statistical-results, so --hepdata-record NAME=OUT.json writes a
single value as a one-bin dataset-record (unrounded value and uncertainty, status labels kept), with the observable
fields the caller declares (--record-quantity NAME=TERM with a quantity_types term such as parameter, --record-level,
--record-normalization JSON (kind and value, as in any dataset-record), --record-process, --record-uncertainty-kind).
Usage:
  render_results.py --quantity NAME=RESULT.json:VALUE_KEY[:UNC_KEY] [...] [--table NAME=RECORD.json [...]]
      --out numbers.tex [--manifest M.json] [--rounding pdg|decimals:n|significant:n]
      [--hepdata-record NAME=OUT.json --record-quantity NAME=TEXT --record-level LEVEL
       --record-normalization KIND --record-process TEXT] [--status LABEL]
  VALUE_KEY and UNC_KEY are keys of a statistical-result's extension.results (for example mu_hat:sigma_mu); NAME is
  letters only and becomes \\NAMEValue, \\NAMEUnc and \\NAME (value \\pm uncertainty), and \\NAMETable for a table.
Output JSON: status (ok, rejected), status_label, inputs, defaults_used, out, manifest, quantities, tables, records.
Exit codes: 0 written; 2 bad input (missing artifact or key, bad name, invalid record). Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(HERE))
from communication_lib.claims import _round, parse_rounding, pdg_round  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

NAME_RE = re.compile(r"^[A-Za-z]+$")
SYNTHETIC = {"synthetic", "asimov"}
PRELIMINARY = {"preliminary", "unvalidated"}
PREAMBLE = r"""% render_results.py (hep-research Com7): generated from artifacts; do not edit by hand.
% A final build defines \hepfinalbuild before \input-ing this file; synthetic or preliminary values then stop it.
\providecommand{\hepSynthetic}[1]{\ifdefined\hepfinalbuild\errmessage{render_results: a SYNTHETIC value in a final build}\fi#1}
\providecommand{\hepPreliminary}[1]{\ifdefined\hepfinalbuild\errmessage{render_results: a PRELIMINARY value in a final build}\fi#1}
% ---
"""


class InputError(ValueError):
    pass


def _artifact(path: str) -> tuple[dict, str]:
    p = Path(path)
    try:
        raw = p.read_bytes()
        doc = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    if not isinstance(doc, dict) or "artifact_type" not in doc:
        raise InputError(f"{path} is not a contract artifact")
    return doc, hashlib.sha256(raw).hexdigest()


def _labels(doc: dict) -> list[str]:
    st = doc.get("status")
    return [st] if isinstance(st, str) else list(st or [])


def _wrap(text: str, labels: list[str]) -> str:
    if SYNTHETIC & set(labels):
        return "\\hepSynthetic{" + text + "}"
    if PRELIMINARY & set(labels):
        return "\\hepPreliminary{" + text + "}"
    return text


def _display(value, unc, rounding: str) -> tuple[str, str]:
    if rounding == "pdg":
        return pdg_round(value, unc)
    v, u = _round(str(value), rounding), _round(str(unc), rounding)
    if v is None or u is None:
        raise InputError(f"cannot round {value} +- {unc} under {rounding}")
    return v, u


def _pair(spec: str, what: str) -> tuple[str, str]:
    if "=" not in spec:
        raise InputError(f"{what} {spec!r}: use NAME=...")
    name, rest = spec.split("=", 1)
    if not NAME_RE.match(name):
        raise InputError(f"{what} name {name!r}: letters only (it becomes a LaTeX macro)")
    return name, rest


def render_quantity(spec: str, rounding: str) -> tuple[str, dict]:
    name, rest = _pair(spec, "--quantity")
    path, _, keys = rest.rpartition(".json:")
    path += ".json"
    parts = keys.split(":")
    if not path or not parts[0]:
        raise InputError(f"--quantity {spec!r}: use NAME=RESULT.json:VALUE_KEY[:UNC_KEY]")
    doc, sha = _artifact(path)
    results = (doc.get("extension") or {}).get("results")
    if not isinstance(results, dict):
        raise InputError(f"{path}: extension.results is not an inline object (a ref cannot be rendered)")
    try:
        value = results[parts[0]]
        unc = results[parts[1]] if len(parts) > 1 else None
    except KeyError as exc:
        raise InputError(f"{path}: no results key {exc}") from exc
    for x in (value, unc):
        if x is not None and (isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)):
            raise InputError(f"{path}: {parts} must be finite numbers")
    labels = _labels(doc)
    if unc is None:
        if rounding == "pdg":
            raise InputError(f"--quantity {name}: the PDG rule needs an uncertainty key")
        shown_v, shown_u = _round(str(value), rounding), None
    else:
        shown_v, shown_u = _display(value, unc, rounding)
    lines = [f"% {name}: artifact {doc.get('artifact_id')} sha256 {sha} results.{parts[0]}"
             + (f" +- results.{parts[1]}" if unc is not None else "") + f"; rounding {rounding}; labels {labels}",
             f"\\newcommand{{\\{name}Value}}{{{shown_v}}}"]
    if shown_u is not None:
        lines.append(f"\\newcommand{{\\{name}Unc}}{{{shown_u}}}")
        with_unc = _wrap(shown_v + " \\pm " + shown_u, labels)  # outside the f-string: Python 3.9 grammar
        lines.append(f"\\newcommand{{\\{name}}}{{{with_unc}}}")
    else:
        lines.append(f"\\newcommand{{\\{name}}}{{{_wrap(shown_v, labels)}}}")
    entry = {"artifact": path, "artifact_id": doc.get("artifact_id"), "artifact_sha256": sha, "value_key": parts[0],
             "uncertainty_key": parts[1] if unc is not None else None, "source_value": value, "source_uncertainty": unc,
             "value": shown_v, "uncertainty": shown_u, "rounding": rounding, "labels": labels,
             "macros": [f"\\{name}Value"] + ([f"\\{name}Unc"] if shown_u else []) + [f"\\{name}"]}
    return "\n".join(lines), entry


def render_table(spec: str, rounding: str) -> tuple[str, dict]:
    name, path = _pair(spec, "--table")
    doc, sha = _artifact(path)
    if doc.get("artifact_type") != "dataset-record":
        raise InputError(f"--table {name}: {path} is a {doc.get('artifact_type')}, not a dataset-record")
    data = doc["extension"]["data"]
    edges, values = data["edges"], data["values"]
    comps = data.get("uncertainties") or []
    totals = [math.sqrt(sum(float(c["values"][i]) ** 2 for c in comps)) if comps else None for i in range(len(values))]
    labels = _labels(doc)
    var = doc["extension"]["observable"]["variables"][0]
    rows, cells = [], []
    for i, v in enumerate(values):
        if totals[i]:
            sv, su = _display(v, totals[i], rounding)
            cell = _wrap(f"${sv} \\pm {su}$", labels)
        else:
            sv, su = str(v), None
            cell = _wrap(f"${sv}$", labels)
        rows.append(f"{edges[i]} -- {edges[i + 1]} & {cell} \\\\")
        cells.append({"low": edges[i], "high": edges[i + 1], "source_value": v, "source_uncertainty": totals[i],
                      "value": sv, "uncertainty": su})
    head = f"{var['name']} [{var.get('unit', '')}] & {doc['extension']['observable'].get('quantity', 'value')} \\\\"
    tex = [f"% {name}: artifact {doc.get('artifact_id')} sha256 {sha}; total uncertainty = components in quadrature; "
           f"rounding {rounding}; labels {labels}",
           f"\\newcommand{{\\{name}Table}}{{\\begin{{tabular}}{{lc}}\n{head}\n\\hline\n" + "\n".join(rows) + "\n\\end{tabular}}"]
    return "\n".join(tex), {"artifact": path, "artifact_id": doc.get("artifact_id"), "artifact_sha256": sha,
                            "rounding": rounding, "labels": labels, "rows": cells, "macro": f"\\{name}Table"}


def one_bin_record(name: str, entry: dict, out: str, args) -> dict:
    """A single value as a one-bin dataset-record for hepdata_export.py (unrounded; labels kept)."""
    sys.path.insert(0, str(PLUGIN))
    from contracts.validate import validate_artifact
    src, _ = _artifact(entry["artifact"])
    need = {"--record-quantity": args.record_quantity, "--record-level": args.record_level,
            "--record-normalization": args.record_normalization, "--record-process": args.record_process}
    missing = [k for k, v in need.items() if not v]
    if missing:
        raise InputError(f"--hepdata-record needs {missing} (the observable is declared, never guessed)")
    quantity = dict(_pair(q, "--record-quantity") for q in args.record_quantity).get(name, name)
    if entry["source_uncertainty"] is not None and not args.record_uncertainty_kind:
        raise InputError("--hepdata-record needs --record-uncertainty-kind (statistical, systematic, ...: what the "
                         "source uncertainty is)")
    try:
        norm = json.loads(args.record_normalization)
    except ValueError as exc:
        raise InputError(f"--record-normalization must be a JSON object (kind, value, unit or convention): {exc}") from exc
    if not isinstance(norm, dict):
        raise InputError("--record-normalization must be a JSON object")
    rec = {k: src[k] for k in ("contract_version", "bindings", "versions", "provenance", "status") if k in src}
    unc = entry["source_uncertainty"]
    rec.update({"artifact_id": f"{entry['artifact_id']}-{name.lower()}-record", "artifact_type": "dataset-record",
                "objective": f"single value {name} of {entry['artifact_id']} as a one-bin record for HEPData",
                "inputs": [{"ref": Path(entry["artifact"]).name, "sha256": entry["artifact_sha256"],
                            "role": "statistical-result"}],
                "outputs": [], "unresolved_inputs": [],
                "extension": {"dataset_id": f"render:{entry['artifact_id']}.{name}", "source_evidence_ids": [],
                              "observable": {"quantity": quantity, "process": args.record_process,
                                             "variables": [{"name": "parameter", "unit": "1", "edges": [0.0, 1.0]}],
                                             "phase_space": {"definition": f"single value of {entry['artifact_id']}",
                                                             "fiducial": False},
                                             "level": args.record_level,
                                             "normalization": norm,
                                             "bin_semantics": "point", "unit": "1"},
                              "data": {"edges": [0.0, 1.0], "values": [entry["source_value"]], "unit": "1",
                                       "uncertainties": ([{"name": entry["uncertainty_key"],
                                                           "kind": args.record_uncertainty_kind,
                                                           "correlation": "uncorrelated", "values": [unc]}]
                                                         if unc is not None else [])},
                              "covariance": ({"status": "present",
                                              "ref": f"{Path(entry['artifact']).name}#extension.results.{entry['uncertainty_key']}",
                                              "note": "one bin: the uncertainty is the whole covariance"}
                                             if unc is not None else {"status": "absent"}),
                              "period": "not-applicable", "status": _labels(src)[0] if _labels(src) else "unvalidated"}})
    rep = validate_artifact(rec)
    if not rep.ok:
        raise InputError(f"the one-bin record for {name} does not validate: {rep.as_dict()['findings'][:3]}")
    Path(out).write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    return {"name": name, "out": out, "artifact_id": rec["artifact_id"]}


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quantity", action="append", default=[])
    ap.add_argument("--table", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifest")
    ap.add_argument("--rounding", default="pdg")
    ap.add_argument("--hepdata-record", action="append", default=[])
    ap.add_argument("--record-quantity", action="append", default=[])
    ap.add_argument("--record-level")
    ap.add_argument("--record-normalization")
    ap.add_argument("--record-process")
    ap.add_argument("--record-uncertainty-kind", help="uncertainty_kinds term of the source uncertainty")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    head = {"status_label": args.status, "inputs": {k: v for k, v in vars(args).items() if k != "status"},
            "defaults_used": [k for k in ("rounding", "status") if f"--{k}" not in given]}
    try:
        parse_rounding(args.rounding)
        if not args.quantity and not args.table:
            raise InputError("give at least one --quantity or --table")
        blocks, quantities, tables, records = [PREAMBLE.rstrip("\n")], {}, {}, []
        for spec in args.quantity:
            tex, entry = render_quantity(spec, args.rounding)
            name = spec.split("=", 1)[0]
            if name in quantities:
                raise InputError(f"quantity {name} given twice")
            blocks.append(tex)
            quantities[name] = entry
        for spec in args.table:
            tex, entry = render_table(spec, args.rounding)
            blocks.append(tex)
            tables[spec.split("=", 1)[0]] = entry
        for spec in args.hepdata_record:
            name, out = _pair(spec, "--hepdata-record")
            if name not in quantities:
                raise InputError(f"--hepdata-record {name}: no --quantity {name}")
            records.append(one_bin_record(name, quantities[name], out, args))
    except (InputError, KeyError, ValueError, IndexError) as exc:
        print(json.dumps({"status": "rejected", **head, "error": f"{type(exc).__name__}: {exc}"}, indent=1))
        return exit_code("rejected")
    Path(args.out).write_text("\n".join(blocks) + "\n", encoding="utf-8")
    manifest = {"tool": "render_results.py", "rounding": args.rounding, "quantities": quantities, "tables": tables,
                "records": records}
    if args.manifest:
        Path(args.manifest).write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", **head, "out": args.out, "manifest": args.manifest, **manifest}, indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())
