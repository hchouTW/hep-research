#!/usr/bin/env python3
"""PDF uncertainty of one observable from its values on every member of a PDF set, by the set's own error type.

Purpose: apply the combination formula that matches the set (the most common PDF-uncertainty error is using the
Hessian formula on replicas or the reverse). Formulas (see <plugin root>/skills/hep-theory/references/pdfs-and-lhapdf.md):
  symmhessian  members 0, 1..N: delta = sqrt(sum_k (X_k - X_0)^2)                      (symmetric eigenvectors)
  hessian      members 0, (1,2), (3,4) ... pairs (+, -) along each eigenvector:
               delta+ = sqrt(sum_k max(X_2k-1 - X_0, X_2k - X_0, 0)^2), delta- likewise with min (asymmetric)
  replicas     members 0 (average), 1..N replicas: central = mean, delta = sample standard deviation, and the
               central 68% interval of the replicas
  <type>+as    the same, after splitting off the LAST TWO members as alpha_s down and alpha_s up; their half
               difference (X_up - X_down) / 2 is reported as a separate `alphas` object, never folded in silently
The error type and the confidence level of the set come from the set's metadata (LHAPDF `ErrorType`, `ErrorConfLevel`).
The type itself fixes only the parity of a `hessian` set and the minimum size of a `replicas` set; the total member
count is checked only when `num_members` (LHAPDF `NumMembers`) is supplied, so pass it: a `symmhessian` set with two
extra alpha_s members is otherwise indistinguishable from one with two more eigenvectors.
A Hessian set quoted at 90% CL is not rescaled silently: pass --rescale-to-68 to divide by 1.645 (Gaussian
assumption, stated in the output; the alpha_s half difference is not rescaled).
--combine-alphas quadrature adds the PDF and alpha_s uncertainties in quadrature, labelled as a prescription.
--symmetrize (hessian only) also reports 1/2 sqrt(sum_k (X_+ - X_-)^2), an alternative prescription.

Input JSON: {"error_type": "symmhessian" | "hessian" | "replicas" (optionally with "+as"),
             "conf_level_percent": 68 | 90, "num_members": int (optional), "alphas_values": [down, up] (optional),
             "members": [X_0, X_1, ...]}
Run: python3 pdf_uncertainty.py input.json [--rescale-to-68] [--combine-alphas quadrature] [--symmetrize] [--status LABEL].
Output JSON: "status" (run status, core/status.py) and "status_label" (the inputs' artifact label, default unvalidated).
Exit 0 ok, 1 refused input, 2 bad arguments or unreadable input.
Standard library only. This combines member values; it does not evaluate PDFs (that needs LHAPDF).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # sibling imports leave no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument  # noqa: E402

BASE_TYPES = ("symmhessian", "hessian", "replicas")
QUADRATURE_CITATION = "PDF4LHC21 recommendation, arXiv:2203.05506v2, Sec. 6.3.3, Eqs. (6.7)-(6.8) (read 2026-10-13)"


def _finite(name: str, x) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError(f"{name} must be a number, got {x!r}")
    v = float(x)
    if not math.isfinite(v):
        raise ValueError(f"{name} is not finite ({v})")
    return v


def combine(error_type: str, members: list[float], conf_level_percent: float = 68.0, rescale_to_68: bool = False,
            *, num_members: int | None = None, alphas_values: list[float] | None = None,
            combine_alphas: str | None = None, symmetrize: bool = False) -> dict:
    if not isinstance(error_type, str):
        raise ValueError(f"error_type must be a string, got {error_type!r}")
    base, _, suffix = error_type.partition("+")
    if base not in BASE_TYPES or suffix not in ("", "as"):
        raise ValueError(f"unknown error_type {error_type!r}; known: {', '.join(BASE_TYPES)}, each optionally '+as'")
    if not isinstance(members, list):
        raise ValueError("members must be a list of numbers")
    members = [_finite(f"member {k}", x) for k, x in enumerate(members)]
    conf_level_percent = _finite("conf_level_percent", conf_level_percent)
    if not 0.0 < conf_level_percent < 100.0:
        raise ValueError(f"conf_level_percent must lie in (0, 100), got {conf_level_percent}")
    if num_members is not None:
        if isinstance(num_members, bool) or not isinstance(num_members, int):
            raise ValueError(f"num_members must be an integer, got {num_members!r}")
        if num_members != len(members):
            raise ValueError(f"num_members {num_members} (NumMembers) does not match the {len(members)} members supplied")
    alphas = None
    if suffix == "as":
        if len(members) < 5:
            raise ValueError("a '+as' set needs the central member, at least two error members and two alpha_s members")
        members, (x_down, x_up) = members[:-2], members[-2:]
        alphas = {"member_values": {"down": x_down, "up": x_up}, "delta": (x_up - x_down) / 2,
                  "rule": "(X_up - X_down) / 2 from the last two members (alpha_s down, then up)"}
        if alphas_values is not None:
            if not isinstance(alphas_values, list) or len(alphas_values) != 2:
                raise ValueError("alphas_values must be [alpha_s down, alpha_s up]")
            a_down, a_up = (_finite("alphas_values", a) for a in alphas_values)
            if not a_down < a_up:
                raise ValueError(f"alphas_values must be ordered down < up, got {alphas_values}")
            alphas["alphas_values"] = {"down": a_down, "up": a_up}
    elif alphas_values is not None:
        raise ValueError("alphas_values given but the error type has no '+as' members")
    if len(members) < 3:
        raise ValueError("need the central member and at least two error members")
    x0, rest = members[0], members[1:]
    if base == "symmhessian":
        up = down = math.sqrt(sum((x - x0) ** 2 for x in rest))
        central = x0
    elif base == "hessian":
        if len(rest) % 2:
            raise ValueError(f"asymmetric Hessian set needs pairs of error members, got {len(rest)}")
        pairs = list(zip(rest[0::2], rest[1::2]))
        up = math.sqrt(sum(max(a - x0, b - x0, 0.0) ** 2 for a, b in pairs))
        down = math.sqrt(sum(max(x0 - a, x0 - b, 0.0) ** 2 for a, b in pairs))
        central = x0
    else:
        if len(rest) < 20:
            raise ValueError(f"{len(rest)} replicas are too few for a standard deviation or a 68% interval")
        central = statistics.fmean(rest)
        up = down = statistics.stdev(rest)
        ordered = sorted(rest)
        lo_i, hi_i = int(round(0.16 * (len(ordered) - 1))), int(round(0.84 * (len(ordered) - 1)))
        interval = [ordered[lo_i], ordered[hi_i]]
    out = {"error_type": error_type, "n_error_members": len(rest), "central": central,
           "delta_up": up, "delta_down": down, "conf_level_percent": conf_level_percent}
    if num_members is not None:
        out["num_members_checked"] = num_members
    if base == "replicas":
        out["replica_68_interval"] = interval
        out["member_0_vs_replica_mean"] = x0 - central
    if symmetrize:
        if base != "hessian":
            raise ValueError("--symmetrize applies to an asymmetric 'hessian' set only")
        out["symmetrized"] = {"delta": 0.5 * math.sqrt(sum((a - b) ** 2 for a, b in pairs)),
                              "prescription": "alternative prescription: 1/2 sqrt(sum_k (X_+ - X_-)^2); "
                                              "not the set's own asymmetric rule"}
    if rescale_to_68 and conf_level_percent != 68.0:
        if abs(conf_level_percent - 90.0) > 1e-9:
            raise ValueError("only 90% to 68% rescaling is supported")
        up, down = up / 1.645, down / 1.645
        out.update(delta_up=up, delta_down=down, conf_level_percent=68.0,
                   rescaling="divided by 1.645 (assumes a Gaussian; a prescription, not a property of the set; "
                             "the alpha_s half difference is not rescaled)")
    if alphas is not None:
        out["alphas"] = alphas
    if combine_alphas is not None:
        if combine_alphas != "quadrature":
            raise ValueError(f"--combine-alphas supports 'quadrature' only, got {combine_alphas!r}")
        if alphas is None:
            raise ValueError("--combine-alphas needs a '+as' error type (no alpha_s members to combine)")
        out["pdf_plus_alphas"] = {"delta_up": math.hypot(up, alphas["delta"]),
                                  "delta_down": math.hypot(down, alphas["delta"]),
                                  "prescription": "quadrature", "citation": QUADRATURE_CITATION,
                                  "note": "a prescription for combining two uncertainty sources, not a property "
                                          "of the set"}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", help="JSON file with error_type, conf_level_percent and members")
    ap.add_argument("--rescale-to-68", action="store_true")
    ap.add_argument("--combine-alphas", choices=["quadrature"], default=None)
    ap.add_argument("--symmetrize", action="store_true", help="hessian only: also report the symmetrized delta")
    add_status_argument(ap)
    opts = ap.parse_args(argv)
    try:
        text = open(opts.input, encoding="utf-8").read()
    except OSError as exc:  # a missing or unreadable input: JSON status, exit 2
        print(json.dumps({"status": "rejected", "error": f"cannot read {opts.input}: {exc}"}))
        return 2
    try:
        doc = json.loads(text)
        if not isinstance(doc, dict):
            raise ValueError("input must be a JSON object")
        out = combine(doc["error_type"], doc["members"], doc.get("conf_level_percent", 68), opts.rescale_to_68,
                      num_members=doc.get("num_members"), alphas_values=doc.get("alphas_values"),
                      combine_alphas=opts.combine_alphas, symmetrize=opts.symmetrize)
    except (ValueError, KeyError, TypeError) as exc:
        reason = f"missing field {exc}" if isinstance(exc, KeyError) else str(exc)
        print(json.dumps({"status": "failed", "status_label": opts.status, "reason": reason}))
        return 1
    print(json.dumps(dict(out, status="ok", status_label=opts.status), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
