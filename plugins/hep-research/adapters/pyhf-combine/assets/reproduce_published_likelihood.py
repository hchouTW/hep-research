#!/usr/bin/env python3
"""Reproduce a published result from an open full likelihood (background-only workspace + signal patchset).

Purpose: turn "the pyhf adapter works on synthetic workspaces" into a checked statement about
one published analysis. Inputs are the files as released on HEPData (BkgOnly.json and a patchset.json) and a
published-values file the user fills from the paper or the HEPData record, citing where each number comes from.

What it does:
- verifies the patchset digest against the background-only workspace (pyhf PatchSet.verify) and refuses a mismatch;
- applies the named patch, fits (best-fit mu; its error needs the minuit optimizer, not used here), and computes CLs at mu = 1 (qtilde, asymptotic)
  with the expected band;
- compares each published value given with the reproduced one under the tolerance stated next to it, and writes a
  comparison table (JSON and Markdown); a published value marked "not-provided" makes the result `incomplete`.
It never decides a tolerance: each comparison needs {"abs": ..} or {"rel": ..} in the published-values file.

Published-values file:
  {"record": "ins1748602", "analysis": "...", "status": "published" | "synthetic", "patch": "<patch name>",
   "source": "<paper table / HEPData table the numbers are read from>",
   "values": {"CLs_obs": x | "not-provided", "CLs_exp": [-2s, -1s, med, +1s, +2s] | x | "not-provided",
              "mu_hat": x | "not-provided"},
   "tolerances": {"CLs_obs": {"abs": 0.01}, ...}}

Usage: reproduce_published_likelihood.py --bkgonly BkgOnly.json --patchset patchset.json --published P.json --out DIR
Exit 0 every given value reproduced, 1 a value outside tolerance or refused input, 3 incomplete (a value
not provided). Needs pyhf (tested with 0.7.6).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pyhf


def reproduce(bkg_doc, patchset_doc, patch):
    ws = pyhf.Workspace(bkg_doc)
    ps = pyhf.PatchSet(patchset_doc)
    ps.verify(ws)  # raises PatchSetVerificationError on a digest mismatch
    names = [p.name for p in ps.patches]
    if patch not in names:
        raise ValueError(f"patch {patch!r} not in the patchset ({len(names)} patches, e.g. {names[:3]})")
    patched = pyhf.Workspace(ps.apply(ws, patch))
    model = patched.model()
    data = patched.data(model)
    pyhf.set_backend("numpy", pyhf.optimize.scipy_optimizer(tolerance=1e-10))
    try:
        pars = np.asarray(pyhf.infer.mle.fit(data, model))
        poi = model.config.poi_index
        obs, exp = pyhf.infer.hypotest(1.0, data, model, test_stat="qtilde", return_expected_set=True)
    finally:
        pyhf.set_backend("numpy", "scipy")
    return {"mu_hat": float(pars[poi]), "CLs_obs": float(obs),
            "CLs_exp": [float(e) for e in exp], "poi": model.config.poi_name, "patch": patch,
            "channels": model.config.channels, "parameters": len(model.config.suggested_init())}


def compare(published, got):
    rows, incomplete = [], []
    for key, val in published.get("values", {}).items():
        if val == "not-provided":
            incomplete.append(key)
            continue
        tol = published.get("tolerances", {}).get(key)
        if not isinstance(tol, dict) or not ({"abs", "rel"} & set(tol)):
            raise ValueError(f"no tolerance stated for {key}: give {{\"abs\": ..}} or {{\"rel\": ..}}")
        mine = got[key]
        if key == "CLs_exp" and not isinstance(val, list):
            mine = got["CLs_exp"][2]  # the median
        pv, mv = np.atleast_1d(np.asarray(val, float)), np.atleast_1d(np.asarray(mine, float))
        if pv.shape != mv.shape:
            raise ValueError(f"{key}: published has {pv.size} values, reproduced {mv.size}")
        limit = tol.get("abs", 0.0) + tol.get("rel", 0.0) * np.abs(pv)
        diff = np.abs(mv - pv)
        rows.append({"quantity": key, "published": val, "reproduced": mine, "abs_difference": diff.tolist(),
                     "tolerance": tol, "pass": bool(np.all(diff <= limit))})
    return rows, incomplete


def markdown(published, got, rows, status):
    lines = [f"# Reproduction of {published.get('record', '?')} ({published.get('status', '?')})", "",
             f"Analysis: {published.get('analysis', 'not-provided')}. Patch: `{got['patch']}`. Published values from: "
             f"{published.get('source', 'not-provided')}. POI `{got['poi']}`, {got['parameters']} parameters.", "",
             "| Quantity | Published | Reproduced | abs difference | Tolerance | Pass |", "|---|---|---|---|---|---|"]
    fmt = lambda v: ", ".join(f"{x:.4g}" for x in np.atleast_1d(v))  # noqa: E731
    for r in rows:
        lines.append(f"| {r['quantity']} | {fmt(r['published'])} | {fmt(r['reproduced'])} | {fmt(r['abs_difference'])} | "
                     f"{json.dumps(r['tolerance'])} | {'yes' if r['pass'] else 'NO'} |")
    lines += ["", f"Result: **{status}**. Asymptotic CLs with qtilde at mu = 1; the paper may use another test statistic "
              "or toys, which the tolerance has to allow for. Agreement shows the released likelihood reproduces the "
              "quoted numbers; it does not validate the analysis.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bkgonly", type=Path, required=True)
    ap.add_argument("--patchset", type=Path, required=True)
    ap.add_argument("--published", type=Path, required=True)
    ap.add_argument("--patch", help="patch name (default: the published file's \"patch\")")
    ap.add_argument("--out", type=Path, required=True)
    opts = ap.parse_args(argv)
    published = json.loads(opts.published.read_text(encoding="utf-8"))
    try:
        got = reproduce(json.loads(opts.bkgonly.read_text(encoding="utf-8")),
                        json.loads(opts.patchset.read_text(encoding="utf-8")), opts.patch or published["patch"])
        rows, incomplete = compare(published, got)
    except (ValueError, KeyError, pyhf.exceptions.PatchSetVerificationError,
            pyhf.exceptions.InvalidSpecification, pyhf.exceptions.InvalidPatchSet) as exc:
        print(json.dumps({"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}))
        return 1
    status = "fail" if any(not r["pass"] for r in rows) else "incomplete" if incomplete or not rows else "reproduced"
    out = {"status": status, "record": published.get("record"), "label": published.get("status", "unknown").upper(),
           "pyhf": pyhf.__version__, "reproduced": got, "comparison": rows, "not_provided": incomplete}
    opts.out.mkdir(parents=True, exist_ok=True)
    (opts.out / "reproduction.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    (opts.out / "reproduction.md").write_text(markdown(published, got, rows, status), encoding="utf-8")
    print(json.dumps({"status": status, "comparisons": len(rows), "not_provided": incomplete}))
    return {"reproduced": 0, "fail": 1, "incomplete": 3}[status]


if __name__ == "__main__":
    sys.exit(main())
