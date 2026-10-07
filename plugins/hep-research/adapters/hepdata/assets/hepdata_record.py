#!/usr/bin/env python3
"""Turn a HEPData table (and its covariance or correlation table, when the record has one) into a `dataset-record`.

Purpose: give the "compare a model with published data" journey a real data source without retyping numbers. A
HEPData table (submission format, as exported in JSON or YAML) carries bins, values and labelled errors, but not the
level, normalization or bin semantics of the observable: those come from the user in --observable, read from the
paper. The record keeps the HEPData identifiers in `observable.external_ids` and cites a ledger claim for provenance.

What it does:
- reads `independent_variables[0]` (bin `low`/`high`, or `value` for points) and `dependent_variables[--dependent]`;
- maps each error label to an uncertainty component (`stat...` -> statistical, everything else systematic), percent
  errors ("5%") to absolute values; asymmetric errors are kept as two components (`+` and `-`) and marked non-Gaussian;
- with --covariance (entries placed by their row and column labels, sorted numerically, so the file order does
  not matter; labels must be increasing with the record's bins, as HEPData indices, centres or ranges are), --covariance-of names the error labels the matrix describes (read from the record): a
  covariance table is used as is; a correlation table is multiplied by the quadrature sum of those labels'
  symmetric errors, never by a silent guess; the matrix is written next to the record and checked to be symmetric
  and positive semidefinite; only the named components point at it;
- an error label missing in some bins is recorded with 0 there and a note naming those bins (not given, not zero);
- without a covariance table the record says `covariance.status: absent`; the errors are never assumed uncorrelated;
- validates the result with `contracts/validate.py` and exits 1 on any contract error.

Usage: hepdata_record.py --table T.json --observable OBS.json --record ins1234567 --table-name "Table 5"
       [--covariance C.json --covariance-of "stat[;sys]"] [--dependent 0] [--status published|synthetic]
       [--evidence-id ns:C01] [--dataset-id ns:name] --out DIR
Exit 0 written and valid, 1 refused input or contract errors, 2 bad arguments. Needs PyYAML only for .yaml input.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402


def read_table(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        import yaml  # optional dependency, only for YAML exports
        return yaml.safe_load(text)
    return json.loads(text)


def _num(x, ref: float) -> float:
    if isinstance(x, str) and x.strip().endswith("%"):
        return abs(ref) * float(x.strip()[:-1]) / 100.0
    return float(x)


def bins(table: dict) -> tuple[list[float], str, str]:
    iv = table["independent_variables"][0]
    vals = iv["values"]
    if all("low" in v and "high" in v for v in vals):
        edges = [float(vals[0]["low"])]
        for prev, v in zip(vals, vals[1:]):
            if abs(float(prev["high"]) - float(v["low"])) > 1e-12 * max(1.0, abs(float(v["low"]))):
                raise ValueError("bins are not contiguous; a record with gaps needs one table per contiguous range")
        edges += [float(v["high"]) for v in vals]
        return edges, iv["header"]["name"], iv["header"].get("units", "")
    raise ValueError("points without bin edges are not supported: bin semantics would be invented")


def uncertainties(dep: dict) -> tuple[list[float], list[dict]]:
    values = [float(v["value"]) for v in dep["values"]]
    comps: dict[str, list] = {}
    for i, v in enumerate(dep["values"]):
        for e in v.get("errors", []):
            label = e.get("label", "unlabelled")
            if "symerror" in e:
                comps.setdefault((label, ""), [0.0] * len(values))[i] = _num(e["symerror"], values[i])
            elif "asymerror" in e:
                comps.setdefault((label, "+"), [0.0] * len(values))[i] = abs(_num(e["asymerror"]["plus"], values[i]))
                comps.setdefault((label, "-"), [0.0] * len(values))[i] = abs(_num(e["asymerror"]["minus"], values[i]))
    out = []
    for (label, side), vals in comps.items():
        given = [i for i, v in enumerate(dep["values"]) if any(e.get("label", "unlabelled") == label for e in v.get("errors", []))]
        kind = "statistical" if label.lower().startswith("stat") else "systematic"
        c = {"name": label + (f" ({side})" if side else ""), "kind": kind, "values": vals, "correlation": "unknown"}
        if side:
            c["gaussian"] = False
        if len(given) != len(values):
            c["note"] = f"not given in bins {[i for i in range(len(values)) if i not in given]} (0 there means not given)"
        out.append(c)
    return values, out


def covariance(cov_table: dict, n: int, comps: list[dict], uses: list[str]) -> tuple[list[list[float]], str]:
    dep = cov_table["dependent_variables"][0]
    entries = [float(v["value"]) for v in dep["values"]]
    if len(entries) != n * n:
        raise ValueError(f"covariance table has {len(entries)} entries for {n} bins (expected {n * n})")
    ivs = cov_table.get("independent_variables", [])
    if len(ivs) >= 2:  # place entries by their (row, column) labels, not by file order
        def key(v):  # a bin index or a bin centre ("value"), or a bin range (low, high): sorted numerically
            return float(v["value"]) if "value" in v else (float(v["low"]), float(v["high"]))
        keys = [[key(v) for v in iv["values"]] for iv in ivs[:2]]
        order = sorted(set(keys[0]))
        if len(order) != n or set(keys[1]) != set(order) or len(set(zip(*keys))) != n * n:
            raise ValueError("covariance table rows and columns do not form one entry per pair of the record's bins")
        pos = {k: i for i, k in enumerate(order)}
        m = [[0.0] * n for _ in range(n)]
        for r, c, x in zip(keys[0], keys[1], entries):
            m[pos[r]][pos[c]] = x
    else:
        m = [entries[i * n:(i + 1) * n] for i in range(n)]
    name = dep["header"]["name"].lower()
    chosen = [c for c in comps if c["name"] in uses]
    if not uses or len(chosen) != len(uses) or any(c.get("gaussian") is False for c in chosen):
        raise ValueError("--covariance-of must name the symmetric error labels of the table that the matrix describes")
    if "correlation" in name:
        sig = [math.sqrt(sum(c["values"][i] ** 2 for c in chosen)) for i in range(n)]
        m = [[m[i][j] * sig[i] * sig[j] for j in range(n)] for i in range(n)]
        how = f"correlation table times the quadrature sum of {'; '.join(uses)}"
    elif "covariance" in name:
        how = "covariance table as published"
    else:
        raise ValueError(f"dependent variable '{dep['header']['name']}' is neither a covariance nor a correlation")
    for i in range(n):
        for j in range(n):
            if abs(m[i][j] - m[j][i]) > 1e-9 * max(1.0, abs(m[i][j])):
                raise ValueError("covariance is not symmetric")
    _require_psd(m)
    return m, how


def _require_psd(m):
    """Cholesky with a relative tolerance: a non-PSD published matrix is reported, never repaired."""
    n = len(m)
    low = [[0.0] * n for _ in range(n)]
    scale = max(abs(m[i][i]) for i in range(n)) or 1.0
    for i in range(n):
        for j in range(i + 1):
            s = m[i][j] - sum(low[i][k] * low[j][k] for k in range(j))
            if i == j:
                if s < -1e-9 * scale:
                    raise ValueError("covariance is not positive semidefinite")
                low[i][i] = math.sqrt(max(s, 0.0))
            else:
                low[i][j] = s / low[j][j] if low[j][j] > 0 else 0.0


def build(opts) -> tuple[dict, dict | None]:
    table = read_table(opts.table)
    observable = json.loads(opts.observable.read_text(encoding="utf-8"))
    edges, var_name, var_unit = bins(table)
    dep = table["dependent_variables"][opts.dependent]
    values, comps = uncertainties(dep)
    if len(values) != len(edges) - 1:
        raise ValueError("number of values does not match the bins")
    if opts.status == "published" and not opts.evidence_id:
        raise ValueError("a published record needs --evidence-id (a ledger claim citing the HEPData record)")
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", opts.table_name).strip("-")
    dataset_id = opts.dataset_id or f"hepdata:{opts.record}-{slug}" + ("-synthetic" if opts.status == "synthetic" else "")
    observable.setdefault("variables", [{"name": var_name, "unit": var_unit}])
    observable["variables"][0]["edges"] = edges
    observable.setdefault("unit", dep["header"].get("units", ""))
    observable.setdefault("external_ids", {})["hepdata"] = f"{opts.record} / {opts.table_name}"
    cov_doc = None
    covariance_block = {"status": "absent", "note": "the record has no covariance table for these bins; errors are "
                                                    "not assumed uncorrelated"}
    if opts.covariance:
        m, how = covariance(read_table(opts.covariance), len(values), comps, opts.covariance_of or [])
        ref = f"{slug}-covariance.json"
        cov_doc = {"label": opts.status.upper(), "source": f"HEPData {opts.record}", "how": how,
                   "unit": f"({observable['unit']})^2", "edges": edges, "matrix": m}
        covariance_block = {"status": "present", "ref": ref, "note": how}
        for c in comps:
            if c["name"] in opts.covariance_of:
                c["correlation"] = "covariance"
                c["covariance_ref"] = ref
    status_label = {"published": "observed", "synthetic": "synthetic"}[opts.status]
    doc = {
        "contract_version": CONTRACTS_VERSION, "artifact_id": dataset_id.split(":", 1)[1],
        "artifact_type": "dataset-record",
        "objective": f"{opts.status} values of HEPData {opts.record} {opts.table_name}",
        "provenance": {"producer_skill": "hep-theory", "created": opts.created,
                       "tool": "adapters/hepdata/assets/hepdata_record.py"},
        "status": [status_label], "bindings": {"experiments": [], "theory": []},
        "versions": {"plugin": json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"],
                     "contracts": CONTRACTS_VERSION, "profiles": {}},
        "inputs": [], "outputs": [], "unresolved_inputs": [],
        "extension": {"dataset_id": dataset_id, "source_evidence_ids": [opts.evidence_id] if opts.evidence_id else [],
                      "observable": observable,
                      "data": {"edges": edges, "values": values, "unit": observable["unit"], "uncertainties": comps},
                      "covariance": covariance_block, "period": "not-provided", "status": opts.status},
    }
    return doc, cov_doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--table", type=Path, required=True)
    ap.add_argument("--covariance", type=Path)
    ap.add_argument("--covariance-of", type=lambda s: [x.strip() for x in s.split(";") if x.strip()],
                    help="error labels the covariance/correlation table describes, separated by ';'")
    ap.add_argument("--observable", type=Path, required=True, help="observable_spec JSON read from the paper")
    ap.add_argument("--record", required=True, help="HEPData record, e.g. ins1748602")
    ap.add_argument("--table-name", required=True)
    ap.add_argument("--dependent", type=int, default=0)
    ap.add_argument("--status", choices=["published", "synthetic"], default="published")
    ap.add_argument("--evidence-id")
    ap.add_argument("--dataset-id")
    ap.add_argument("--created", default=date.today().isoformat(), help="YYYY-MM-DD (default today)")
    ap.add_argument("--out", type=Path, required=True)
    opts = ap.parse_args(argv)
    try:
        doc, cov = build(opts)
    except (ValueError, KeyError, IndexError) as exc:
        print(json.dumps({"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}))
        return 1
    rep = validate_artifact(doc)
    if rep.errors:
        print(json.dumps({"status": "failed", "contract_errors": [f.__dict__ for f in rep.errors]}, default=str, indent=1))
        return 1
    opts.out.mkdir(parents=True, exist_ok=True)
    (opts.out / "dataset-record.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    if cov:
        (opts.out / doc["extension"]["covariance"]["ref"]).write_text(json.dumps(cov, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "dataset_id": doc["extension"]["dataset_id"], "bins": len(doc["extension"]["data"]["values"]),
                      "covariance": doc["extension"]["covariance"]["status"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
