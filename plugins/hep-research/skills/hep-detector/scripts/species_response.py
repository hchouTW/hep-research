#!/usr/bin/env python3
"""Species-migration response: blocks of standard responses tied by a block manifest (D2).

Purpose: when a particle of one species can be reconstructed as another (charge-sign confusion, charge-ladder
leakage, fragmentation into a lighter nucleus), the reco spectrum of each species is a fold of every true species:
reco_s' = sum_s R(s -> s') truth_s. Each nonzero block R(s -> s') is a standard response (rows reco, columns truth);
the manifest ties them together, with no contract change. See
<plugin root>/skills/hep-detector/references/response-and-forward-folding.md, "Species migration".

Manifest (JSON): {"manifest_version": "0.1.0", "species": [...], "variable": {"name", "unit"},
  "inefficiency_location": "outside", "blocks": [{"true", "reco", "response", "source", "effects"?: [...]}]}
  response: a path to a response artifact (build_response.py writes them; normalization conditional_on_generated,
  orientation rows_reco_cols_truth), relative to the manifest, or an inline object {"matrix", "truth_edges",
  "reco_edges"} with the same conventions. effects: what the block models (default "migration" on the diagonal,
  "species_migration" off it); check compares them with the correction chain.
Subcommands:
  assemble   check the blocks (same truth and reco axes everywhere, conditional_on_generated, column sums over the
             reco species of every true species <= 1: the losses are outside the blocks) and report the flattened
             matrix size; above 60 flattened bins it recommends parametrized forward folding.
  fold       sparse forward fold of the truth spectra {"truth": {SPECIES: [per truth bin]}} into reco spectra.
  check      exit 1 when an effect a block models is also in the correction chain (a measurement-spec's
             corrections[].effect_id, a recipe's steps[].effect_keys and input.applied_effects, or the recipe_steps of
             survival_feeddown.py): the same effect would be corrected twice.
  from-rates turn sign rates ({"sign_rates": {...}} of charge_confusion_rate.py, or the inner object) into a manifest
             with inline blocks: diag(1 - r) on the diagonal and diag(r) off it (the confused track keeps its bin: the
             rigidity response of confused tracks is not modelled; add a response per species for that).
Output JSON: status (ok, failed, rejected), status_label, inputs, defaults_used, warnings and the result.
Exit codes: 0 ok; 1 check found a double count; 2 bad input. Standard library only.
Usage:
  species_response.py assemble --manifest M.json [--status LABEL]
  species_response.py fold --manifest M.json --truth T.json [--status LABEL]
  species_response.py check --manifest M.json --chain CHAIN.json [--status LABEL]
  species_response.py from-rates --rates R.json --out M.json [--status LABEL]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(PLUGIN))
from core.status import add_status_argument, exit_code  # noqa: E402

MANIFEST_VERSION = "0.1.0"
MAX_FLAT_BINS = 60
COLUMN_TOL = 1e-9
LABEL = "[General method]"


class InputError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _json(path: Path) -> dict:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read {path}: {exc}") from None
    if not isinstance(doc, dict):
        raise InputError(f"{path}: expected a JSON object")
    return doc


def _finite_matrix(m, where: str) -> list[list[float]]:
    if not isinstance(m, list) or not m or not all(isinstance(r, list) and r for r in m):
        raise InputError(f"{where}: matrix must be a non-empty list of rows")
    out = []
    for r in m:
        row = []
        for v in r:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
                raise InputError(f"{where}: matrix entries must be finite and >= 0")
            row.append(float(v))
        out.append(row)
    if len({len(r) for r in out}) != 1:
        raise InputError(f"{where}: ragged matrix")
    return out


def _block_response(block: dict, base: Path) -> tuple[list[list[float]], list[float], list[float]]:
    resp = block.get("response")
    where = f"block {block.get('true')}->{block.get('reco')}"
    if isinstance(resp, str):
        doc = _json(base / resp if not Path(resp).is_absolute() else Path(resp))
        ext = doc.get("extension", {})
        if ext.get("normalization") != "conditional_on_generated":
            raise InputError(f"{where}: normalization must be conditional_on_generated (a cross-species block is a "
                             "probability per generated true particle)")
        if ext.get("orientation", "rows_reco_cols_truth") != "rows_reco_cols_truth":
            raise InputError(f"{where}: orientation must be rows_reco_cols_truth")
        m = _finite_matrix(ext.get("matrix"), where)
        te, re_ = ext.get("truth_axis", {}).get("edges"), ext.get("reco_axis", {}).get("edges")
    elif isinstance(resp, dict):
        m = _finite_matrix(resp.get("matrix"), where)
        te, re_ = resp.get("truth_edges"), resp.get("reco_edges")
    else:
        raise InputError(f"{where}: response must be a path or an inline object")
    if not (isinstance(te, list) and isinstance(re_, list)) or len(m) != len(re_) - 1 or len(m[0]) != len(te) - 1:
        raise InputError(f"{where}: matrix shape does not match the axes")
    return m, [float(x) for x in te], [float(x) for x in re_]


def load_manifest(path: Path) -> tuple[dict, dict, list[float], list[float]]:
    man = _json(path)
    if man.get("manifest_version") != MANIFEST_VERSION:
        raise InputError(f"manifest_version must be {MANIFEST_VERSION}")
    if man.get("inefficiency_location") != "outside":
        raise InputError("inefficiency_location must be 'outside' (losses are not a block)")
    species = man.get("species")
    if not isinstance(species, list) or len(set(species)) != len(species) or len(species) < 1:
        raise InputError("species must be a list of distinct names")
    blocks, axes = {}, None
    for b in man.get("blocks") or []:
        t, r = b.get("true"), b.get("reco")
        if t not in species or r not in species:
            raise InputError(f"block {t}->{r}: both species must be listed")
        if (t, r) in blocks:
            raise InputError(f"block {t}->{r} appears twice")
        if not b.get("source"):
            raise InputError(f"block {t}->{r}: a source is required")
        m, te, re_ = _block_response(b, Path(path).parent)
        if axes is None:
            axes = (te, re_)
        elif (te, re_) != axes:
            raise InputError(f"block {t}->{r}: truth or reco axis differs from the other blocks")
        effects = b.get("effects") or (["migration"] if t == r else ["species_migration"])
        blocks[(t, r)] = {"matrix": m, "effects": list(effects), "source": b["source"]}
    if not blocks:
        raise InputError("the manifest has no blocks")
    return man, blocks, axes[0], axes[1]


def assemble(man: dict, blocks: dict, te: list, re_: list) -> tuple[dict, list[str]]:
    warnings = []
    species = man["species"]
    nt, nr = len(te) - 1, len(re_) - 1
    sums = {}
    for t in species:
        col = [0.0] * nt
        for (bt, _br), b in blocks.items():
            if bt == t:
                for j in range(nt):
                    col[j] += sum(b["matrix"][i][j] for i in range(nr))
        if any(c > 1 + COLUMN_TOL for c in col):
            raise InputError(f"true species {t}: a column sums to {max(col):.6g} > 1 over the reco species "
                             "(a particle is counted more than once)")
        sums[t] = col
    flat = {"reco": nr * len(species), "truth": nt * len(species)}
    if max(flat.values()) > MAX_FLAT_BINS:
        warnings.append(f"{max(flat.values())} flattened bins > {MAX_FLAT_BINS}: use parametrized forward folding "
                        "instead of one flattened matrix")
    return {"species": species, "blocks": [{"true": t, "reco": r, "effects": b["effects"], "source": b["source"]}
                                           for (t, r), b in blocks.items()],
            "column_sums": sums, "flattened_bins": flat, "truth_edges": te, "reco_edges": re_}, warnings


def fold(man: dict, blocks: dict, te: list, re_: list, truth: dict) -> dict:
    nt, nr = len(te) - 1, len(re_) - 1
    reco = {s: [0.0] * nr for s in man["species"]}
    for t in man["species"]:
        x = truth.get(t)
        if x is None:
            raise InputError(f"no truth spectrum for species {t}")
        if not isinstance(x, list) or len(x) != nt or any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0
                                                           for v in x):
            raise InputError(f"truth spectrum of {t} must list {nt} finite values >= 0")
        for (bt, br), b in blocks.items():
            if bt != t:
                continue
            for i in range(nr):
                reco[br][i] += math.fsum(b["matrix"][i][j] * x[j] for j in range(nt))
    return {"reco": reco, "reco_edges": re_, "method": "sparse fold over the nonzero blocks"}


def chain_effects(doc: dict) -> set[str]:
    eff = set()
    ext = doc.get("extension") if isinstance(doc.get("extension"), dict) else {}
    for c in ext.get("corrections") or []:
        if isinstance(c, dict) and c.get("effect_id"):
            eff.add(c["effect_id"])
    for steps in (doc.get("steps"), doc.get("recipe_steps")):
        for s in steps or []:
            eff.update((s.get("effect_keys") or {}).keys())
    eff.update(((doc.get("input") or {}).get("applied_effects")) or [])
    return eff


def from_rates(doc: dict) -> dict:
    sr = doc.get("sign_rates", doc)
    edges = sr.get("edges")
    rates = sr.get("rates")
    if not isinstance(edges, list) or len(edges) < 2 or not isinstance(rates, list) or not rates:
        raise InputError("sign rates need edges and a non-empty rates list")
    n = len(edges) - 1
    species = []
    for r in rates:
        for s in (r.get("true"), r.get("reco")):
            if s not in species:
                species.append(s)
    blocks = []
    for r in rates:
        rate = r.get("rate")
        if not isinstance(rate, list) or len(rate) != n or any(v is None or not 0 <= v <= 1 for v in rate):
            raise InputError(f"rates {r.get('true')}->{r.get('reco')}: one rate in [0, 1] per bin is required")
        diag = lambda vals: [[vals[i] if i == j else 0.0 for j in range(n)] for i in range(n)]  # noqa: E731
        src = sr.get("source", "charge_confusion_rate.py sign rates")
        blocks.append({"true": r["true"], "reco": r["true"], "source": src, "effects": ["migration"],
                       "response": {"matrix": diag([1 - v for v in rate]), "truth_edges": edges, "reco_edges": edges}})
        blocks.append({"true": r["true"], "reco": r["reco"], "source": src, "effects": ["species_migration"],
                       "response": {"matrix": diag(rate), "truth_edges": edges, "reco_edges": edges}})
    have = {b["true"] for b in blocks}
    for s in species:
        if s not in have:
            blocks.append({"true": s, "reco": s, "source": "identity: no rate given for this sign", "effects": ["migration"],
                           "response": {"matrix": [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)],
                                        "truth_edges": edges, "reco_edges": edges}})
    return {"manifest_version": MANIFEST_VERSION, "species": species,
            "variable": {"name": sr.get("variable") or "x", "unit": sr.get("unit")}, "inefficiency_location": "outside",
            "blocks": blocks,
            "note": "confused tracks keep their bin: the rigidity response of confused tracks is not modelled"}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("assemble", "fold", "check"):
        p = sub.add_parser(name)
        p.add_argument("--manifest", type=Path, required=True)
        if name == "fold":
            p.add_argument("--truth", type=Path, required=True)
        if name == "check":
            p.add_argument("--chain", type=Path, required=True)
        add_status_argument(p)
    p = sub.add_parser("from-rates")
    p.add_argument("--rates", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    add_status_argument(p)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    head = {"status_label": args.status, "inputs": inputs,
            "defaults_used": [k for k in ("status",) if f"--{k}" not in given]}
    status, warnings = "ok", []
    try:
        if args.command == "from-rates":
            man = from_rates(_json(args.rates))
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(man, indent=1) + "\n", encoding="utf-8")
            result = {"out": str(args.out), "species": man["species"], "blocks": len(man["blocks"]), "note": man["note"]}
        else:
            man, blocks, te, re_ = load_manifest(args.manifest)
            result, warnings = assemble(man, blocks, te, re_)
            if args.command == "fold":
                truth = _json(args.truth).get("truth")
                if not isinstance(truth, dict):
                    raise InputError("truth file must be {\"truth\": {SPECIES: [...]}}")
                result = fold(man, blocks, te, re_, truth)
            elif args.command == "check":
                chain = chain_effects(_json(args.chain))
                double = [{"block": f"{t}->{r}", "effect": e} for (t, r), b in blocks.items() for e in b["effects"]
                          if e in chain]
                result = {"chain_effects": sorted(chain), "double_counted": double,
                          "verdict": "double count" if double else "no overlap"}
                if double:
                    status = "failed"
    except InputError as exc:
        print(json.dumps({"status": "rejected", **head, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": status, **head, "warnings": warnings, "label": LABEL, **result}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
