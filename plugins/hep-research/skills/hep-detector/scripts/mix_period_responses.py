#!/usr/bin/env python3
"""Era (period) responses: mix them per truth bin with exposure weights, or stack them for a joint fit (D5).

Purpose: a detector whose configuration changes (an added layer, a new calibration era) has one response per era.
A measurement over several eras folds a prediction through each era with that era's exposure; this tool builds the
equivalent single response, or the stacked matrix a joint fit over eras uses. See
<plugin root>/skills/hep-detector/references/response-and-forward-folding.md, "Time-dependent responses".

Method:
  mix:   R_eff[:, j] = sum_t w_tj R_t[:, j] / sum_t w_tj, with w_tj = A_tj T_tj (acceptance x collection time per truth
         bin, or a declared weight), the same for the under/overflow vectors. Then R_eff (sum_t w_tj Phi_j) equals
         sum_t R_t (w_tj Phi_j): folding the mixed response with the summed weights equals the sum of the per-era folds.
         mc_stat: with every era carrying generated counts N_tj, the effective count 1 / sum_t (f_tj^2 / N_tj),
         f_tj = w_tj / sum_t w_tj (the multinomial variance with the era probabilities taken equal); otherwise none.
  stack: S = [R_1 diag(w_1); R_2 diag(w_2); ...], an (n_era x n_reco) x n_truth matrix, so that the expected reco
         counts of every era are S Phi (rows in era order; diag(w) omitted without --weights).
Checks: the truth axes, the reco axes, orientation, normalization (conditional_on_generated or
conditional_on_selected), inefficiency, acceptance, underflow_overflow and intended use agree across eras; every weight
is finite and >= 0, given for every era and truth bin, and sum_t w_tj > 0 for every truth bin. The sha256 of the
weight source and of every response file is recorded. A mixed artifact must pass contracts/validate.py (strict) and
contracts/response_adapter.py --validate, or nothing is written.

Input: response artifacts with an inline matrix (build_response.py writes them); weights JSON
  {"source": TEXT, "periods": {ERA: {"weight": [per truth bin]} | {"acceptance": X, "collection_time": Y}}}
  where X and Y are a number or a list per truth bin (e.g. collection_time.py output for that era).
Usage:
  mix_period_responses.py mix --period ERA=RESPONSE.json [--period ...] --weights W.json --artifact-id ID
      --objective TEXT --out MIXED.json [--created YYYY-MM-DD] [--status LABEL]
  mix_period_responses.py stack --period ERA=RESPONSE.json [--period ...] [--weights W.json] --out STACK.json
      [--status LABEL]
Output JSON: status (ok, refused, rejected), status_label, inputs, defaults_used, out, weights_sha256, responses
(era, path, sha256) and, for mix, validation.
Exit codes: 0 written; 1 refused (the mixed artifact fails its validation; nothing written); 2 bad input.
Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
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
from contracts.response_adapter import to_validator_input  # noqa: E402
from contracts.validate import Vocabulary, validate_artifact  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

SAME = ("truth_axis", "reco_axis", "orientation", "normalization", "inefficiency", "acceptance", "underflow_overflow",
        "intended_use")
NORMALIZATIONS = ("conditional_on_generated", "conditional_on_selected")


class InputError(ValueError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_periods(items: list[str]) -> list[dict]:
    out, seen = [], set()
    for item in items:
        era, sep, path = item.partition("=")
        if not sep or not era or not path:
            raise InputError(f"--period {item!r}: expected ERA=RESPONSE.json")
        if era in seen:
            raise InputError(f"era {era!r} is given twice")
        seen.add(era)
        p = Path(path)
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InputError(f"cannot read the response {p}: {exc}") from None
        ext = doc.get("extension") if isinstance(doc, dict) else None
        if not isinstance(ext, dict) or doc.get("artifact_type") != "response":
            raise InputError(f"{p} is not a response artifact")
        if not isinstance(ext.get("matrix"), list):
            raise InputError(f"{p}: an inline matrix is required (matrix_ref is not read here)")
        if ext.get("normalization") not in NORMALIZATIONS:
            raise InputError(f"{p}: normalization {ext.get('normalization')!r} is not a probability; mixing needs "
                             f"{' or '.join(NORMALIZATIONS)}")
        out.append({"era": era, "path": str(p), "sha256": _sha(p), "doc": doc, "ext": ext})
    first = out[0]["ext"]
    for per in out[1:]:
        for key in SAME:
            if per["ext"].get(key) != first.get(key):
                what = "reco axis" if key == "reco_axis" else "truth axis" if key == "truth_axis" else key
                raise InputError(f"era {per['era']!r} differs from era {out[0]['era']!r} in its {what}: responses of "
                                 "different conventions cannot be mixed")
    return out


def _vector(value, nt: int, where: str) -> list[float]:
    vals = [value] * nt if isinstance(value, (int, float)) and not isinstance(value, bool) else value
    if not isinstance(vals, list) or len(vals) != nt:
        raise InputError(f"{where} needs a number or a list of {nt} values (one per truth bin)")
    out = []
    for v in vals:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise InputError(f"{where}: {v!r} is not a finite weight >= 0")
        out.append(float(v))
    return out


def load_weights(path: Path, eras: list[str], nt: int) -> tuple[dict, str, str]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read the weights {path}: {exc}") from None
    per = doc.get("periods") if isinstance(doc, dict) else None
    if not isinstance(per, dict):
        raise InputError("the weights file needs an object 'periods' keyed by era")
    weights = {}
    for era in eras:
        spec = per.get(era)
        if not isinstance(spec, dict):
            raise InputError(f"no weights for era {era!r}")
        if "weight" in spec:
            weights[era] = _vector(spec["weight"], nt, f"periods.{era}.weight")
        elif "acceptance" in spec and "collection_time" in spec:
            a = _vector(spec["acceptance"], nt, f"periods.{era}.acceptance")
            t = _vector(spec["collection_time"], nt, f"periods.{era}.collection_time")
            weights[era] = [x * y for x, y in zip(a, t)]
        else:
            raise InputError(f"periods.{era} needs 'weight', or 'acceptance' and 'collection_time'")
    totals = [sum(weights[e][j] for e in eras) for j in range(nt)]
    zero = [j for j, w in enumerate(totals) if w <= 0]
    if zero:
        raise InputError(f"the total weight is zero in truth bins {zero}: no era contributes there")
    return weights, _sha(path), str(doc.get("source", ""))


def mix(periods: list[dict], weights: dict) -> dict:
    first = periods[0]["ext"]
    nr, nt = len(first["matrix"]), len(first["matrix"][0])
    eras = [p["era"] for p in periods]
    tot = [sum(weights[e][j] for e in eras) for j in range(nt)]
    frac = {e: [weights[e][j] / tot[j] for j in range(nt)] for e in eras}
    matrix = [[math.fsum(frac[p["era"]][j] * p["ext"]["matrix"][i][j] for p in periods) for j in range(nt)]
              for i in range(nr)]
    ext = {k: first[k] for k in SAME if k in first}
    ext.update({"includes": first.get("includes", ["migration"]), "form": "matrix", "matrix": matrix,
                "conditions": "mixed over eras " + ", ".join(eras) + " with per-truth-bin weights (mix_period_responses.py)",
                "provenance": "exposure-weighted mixture of the era responses " + ", ".join(
                    f"{p['era']} (sha256 {p['sha256'][:12]})" for p in periods)})
    for key in ("applied_separately", "correction_space"):
        if key in first:
            ext[key] = first[key]
    for key in ("underflow", "overflow"):
        if all(isinstance(p["ext"].get(key), list) for p in periods):
            ext[key] = [math.fsum(frac[p["era"]][j] * p["ext"][key][j] for p in periods) for j in range(nt)]
    stats = [p["ext"].get("mc_stat") or {} for p in periods]
    if all(s.get("kind") == "generated_counts" and isinstance(s.get("events_per_truth_bin"), list) for s in stats):
        n_eff = []
        for j in range(nt):
            terms = [frac[p["era"]][j] ** 2 / s["events_per_truth_bin"][j] for p, s in zip(periods, stats)
                     if frac[p["era"]][j] > 0]
            if any(s["events_per_truth_bin"][j] <= 0 and frac[p["era"]][j] > 0 for p, s in zip(periods, stats)):
                n_eff = None
                break
            n_eff.append(1.0 / math.fsum(terms))
        if n_eff is not None:
            ext["mc_stat"] = {"kind": "effective_counts", "weighted": True, "events_per_truth_bin": n_eff}
    ext["mixing"] = {"rule": "R_eff[:, j] = sum_t w_tj R_t[:, j] / sum_t w_tj", "eras": eras,
                     "weights": {e: weights[e] for e in eras}, "total_weight": tot,
                     "fold_identity": "R_eff (W_j Phi_j) = sum_t R_t (w_tj Phi_j)"}
    return ext


def stack(periods: list[dict], weights: dict | None) -> dict:
    first = periods[0]["ext"]
    nr, nt = len(first["matrix"]), len(first["matrix"][0])
    rows, blocks = [], []
    for p in periods:
        w = weights[p["era"]] if weights else [1.0] * nt
        blocks.append({"era": p["era"], "rows": [len(rows), len(rows) + nr]})
        rows += [[p["ext"]["matrix"][i][j] * w[j] for j in range(nt)] for i in range(nr)]
    return {"kind": "stacked-response", "eras": [p["era"] for p in periods], "n_reco": nr, "n_truth": nt,
            "row_blocks": blocks, "matrix": rows, "weights_applied": weights is not None,
            "truth_axis": first["truth_axis"], "reco_axis": first["reco_axis"],
            "orientation": "rows (era, reco) in era order, columns truth",
            "normalization": first["normalization"], "inefficiency": first["inefficiency"],
            "model": "expected reco counts of era e = S[block e] Phi (with weights: R_e diag(A_e T_e) Phi)"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("mix", "stack"):
        p = sub.add_parser(name)
        p.add_argument("--period", action="append", required=True, metavar="ERA=RESPONSE.json")
        p.add_argument("--weights", required=name == "mix")
        p.add_argument("--out", required=True)
        add_status_argument(p)
        if name == "mix":
            p.add_argument("--artifact-id", required=True)
            p.add_argument("--objective", required=True)
            p.add_argument("--created", default=date.today().isoformat())
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    report: dict = {"status_label": args.status, "inputs": dict(vars(args)),
                    "defaults_used": [k for k in ("created", "status") if k in vars(args) and f"--{k}" not in given]}
    out = Path(args.out)
    try:
        periods = load_periods(args.period)
        nt = len(periods[0]["ext"]["matrix"][0])
        weights, wsha, wsource = (load_weights(Path(args.weights), [p["era"] for p in periods], nt)
                                  if args.weights else (None, None, None))
        report["responses"] = [{"era": p["era"], "path": p["path"], "sha256": p["sha256"]} for p in periods]
        report["weights_sha256"] = wsha
        if args.command == "stack":
            doc = stack(periods, weights)
            doc["weights_sha256"], doc["weights_source"] = wsha, wsource
            doc["responses"] = report["responses"]
            doc["status_label"] = args.status
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
            report.update(status="ok", out=str(out), shape=[len(doc["matrix"]), nt])
        else:
            ext = mix(periods, weights)
            ext["mixing"]["weights_sha256"], ext["mixing"]["weights_source"] = wsha, wsource
            base = periods[0]["doc"]
            doc = {"contract_version": CONTRACTS_VERSION, "artifact_id": args.artifact_id, "artifact_type": "response",
                   "objective": args.objective, "bindings": base.get("bindings", {"experiments": [], "theory": []}),
                   "versions": {"plugin": json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"],
                                "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release(),
                                "profiles": (base.get("versions") or {}).get("profiles", {})},
                   "provenance": {"producer_skill": "hep-detector", **trace.provenance(), "created": args.created, "evidence_ids": []},
                   "inputs": [], "outputs": [], "unresolved_inputs": [],
                   "status": sorted({args.status, *[s for p in periods for s in p["doc"].get("status", [])]}),
                   "extension": ext}
            rep = validate_artifact(doc, Vocabulary(), strict=True).as_dict()
            conv = to_validator_input(ext, contract_version=CONTRACTS_VERSION)
            val = validate_response(conv["input"]) if conv["ok"] else {"status": "fail", "errors": conv["errors"]}
            report["validation"] = {"contracts_validate": "ok" if rep.get("ok") else "fail",
                                    "contracts_findings": [f for f in rep.get("findings", []) if f.get("severity") == "error"],
                                    "response_validation": val.get("status"), "response_errors": val.get("errors", [])}
            if not rep.get("ok") or val.get("status") == "fail":
                report.update(status="refused", error="the mixed response fails its validation; nothing was written")
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
                report.update(status="ok", out=str(out))
    except InputError as exc:
        report.update(status="rejected", error=str(exc))
    except OSError as exc:
        report.update(status="rejected", error=f"cannot write {out}: {exc.strerror or exc}")
    print(json.dumps(report, indent=1, default=str))
    if report["status"] != "ok":
        print(f"mix_period_responses.py: error: {report.get('error')}", file=sys.stderr)
    return exit_code(report["status"])


if __name__ == "__main__":
    sys.exit(main())
