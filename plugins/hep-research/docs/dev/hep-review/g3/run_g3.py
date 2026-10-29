#!/usr/bin/env python3
"""G3 evaluation driver (g3/frozen-protocol.md). The R2 path, packet and cross-family grading are those of g2x
(`../pilot/g2x/run_g2x.py`); contexts are g3-<instance>-t<k>. Scoring reports rates with 95% Clopper-Pearson
intervals, split by defect tag, and applies the pre-registered claim rule. Development tool; never runs a model.

  prepare | assign | ingest | items | combine     as in run_g2x.py
  score --run DIR --gold DIR --combined FILE       rates, intervals, splits, claim decision
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pilot" / "g2x"))
import run_g2x as X  # noqa: E402

X.P.CONTEXT_PREFIX = "g3"
TAGS = ("interacting", "numerical", "convention")
WARN_DETECTION, WARN_FALSE_ALARM = 0.8, 0.2


def binom_cdf(k: int, n: int, p: float) -> float:
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0 if k < n else 1.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Exact two-sided interval for a binomial proportion (bisection on the binomial tail; standard library only)."""
    if n == 0:
        return 0.0, 1.0
    a = (1 - level) / 2

    def solve(f, lo=0.0, hi=1.0):
        for _ in range(200):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(lambda p: 1 - binom_cdf(k - 1, n, p) < a)
    upper = 1.0 if k == n else solve(lambda p: binom_cdf(k, n, p) > a)
    return round(lower, 4), round(upper, 4)


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": clopper_pearson(k, n)}


def cmd_score(a) -> dict:
    base = X.cmd_score(a)  # g2x scoring: rows, defect rows, denominators, engineering gate
    gold = {p.stem: json.loads(p.read_text()) for p in Path(a.gold).glob("*.json")}
    tags = {(g["id"], d["defect_id"]): set(d.get("tags", [])) for g in gold.values() for d in g.get("defects", [])}
    drows = base["defect_rows"]
    split = {"all": rate(sum(d["detected"] for d in drows), len(drows))}
    for t in TAGS:
        sel = [d for d in drows if t in tags.get((d["instance"], d["defect_id"]), set())]
        split[t] = rate(sum(d["detected"] for d in sel), len(sel))
    plain = [d for d in drows if not tags.get((d["instance"], d["defect_id"]))]
    split["untagged"] = rate(sum(d["detected"] for d in plain), len(plain))
    rows = base["rows"].values()
    c02 = [r for r in rows if r["type"] == "C02"]
    c03 = [r for r in rows if r["type"] == "C03"]
    c04 = [r for r in rows if r["type"] == "C04"]
    measured = {"defect_detection": split,
                "c02_false_alarm": rate(sum(bool(r.get("false_alarm")) for r in c02), len(c02)),
                "c03_gap_kept": rate(sum(r["success"] for r in c03), len(c03)),
                "c04_planning_gap": rate(sum(r["success"] for r in c04), len(c04))}
    calibrated = base["scientific_gate"]["graders_calibrated"]
    eng = base["engineering_gate"]["pass"]
    warnings = []
    if split["all"]["n"] and split["all"]["rate"] < WARN_DETECTION:
        warnings.append(f"defect detection {split['all']['rate']} is below {WARN_DETECTION}")
    fa = measured["c02_false_alarm"]
    if fa["n"] and fa["rate"] > WARN_FALSE_ALARM:
        warnings.append(f"false-alarm rate {fa['rate']} is above {WARN_FALSE_ALARM}")
    claim = {"state": "evaluated-scope" if eng and calibrated else "pilot-checked-scope",
             "reason": "engineering gate passed and graders calibrated" if eng and calibrated else
             ("engineering gate failed" if not eng else "graders not calibrated"),
             "usage_warnings": warnings}
    return {"status": "ok", "measured": measured, "claim_decision": claim, **{k: base[k] for k in (
        "task_level", "known_defect_level", "predicted_finding_level", "per_type_instances", "engineering_gate",
        "defect_rows", "rows")}}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] != "score":
        return X.main(argv)
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("cmd")
    p.add_argument("--run", required=True)
    p.add_argument("--gold", required=True)
    p.add_argument("--combined", required=True)
    print(json.dumps(cmd_score(p.parse_args(argv)), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
