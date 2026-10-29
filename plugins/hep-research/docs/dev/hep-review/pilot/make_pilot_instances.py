#!/usr/bin/env python3
"""Pilot instance generator with deterministic oracles (hep-review T03 step 7; design only, nothing is scored here).

    python3 make_pilot_instances.py --seed SECRET --out DIR [--per-type 4]

Writes DIR/instances/<id>/{intent.json, plan.json, material/analysis.md, material/data.json} and, separately,
DIR/expected/<id>.json and DIR/oracle.json. Every instance is checked by its oracle before it is written: a C01
instance must contain exactly its planted defect (the stated value follows the defective formula and differs from the
correct one beyond the tolerance), a C02 control must be correct at its stated precision, a C03 instance's stated
values must be reachable for some admissible value of the missing input (so a defect is not also present), and a C04
instance's material must be correct. An instance that fails its oracle is regenerated, never written.

The seed decides the numbers and the type of every opaque instance id. Run it off this host with a seed only the user
knows (U1 option a), or let the user approve the oracles so that no secret gold is needed (option b). Families differ
from the T0S spike families (spike instances are exposed). Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

TOL = 1e-3  # relative tolerance of the computing obligation
STAT_Q = "Is the statistical treatment in analysis.md appropriate for the model and inputs stated there?"
COMP_Q = ("Can every number in data.json 'stated_results' be recomputed from the inputs in data.json with the method "
          "described in analysis.md, within 0.1% relative?")


def stated(x: float, digits: int = 6) -> float:
    """Quote with enough significant digits for the 0.1% tolerance (the spike's x02c lesson)."""
    return float(f"{x:.{digits}g}")


def within(a: float, b: float, tol: float = TOL / 2) -> bool:
    return abs(a - b) <= tol * max(abs(b), 1e-300)


# ---- families: each returns (analysis text, material_values, oracle verdict dict) ------------------------------------------

def fam_weights(rng, defect: bool):
    n = 4
    v = [round(rng.uniform(9.5, 10.5), 3) for _ in range(n)]
    s = [round(rng.uniform(0.1, 0.5), 3) for _ in range(n)]
    w_ok = [1 / x ** 2 for x in s]
    w_bad = [1 / x for x in s]  # defect: weights 1/sigma instead of 1/sigma^2
    w = w_bad if defect else w_ok
    mean = sum(a * b for a, b in zip(w, v)) / sum(w)
    true_mean = sum(a * b for a, b in zip(w_ok, v)) / sum(w_ok)
    unc = 1 / math.sqrt(sum(w_ok))
    text = ("Four independent measurements are averaged. The weights are "
            + ("w_i = 1/sigma_i" if defect else "w_i = 1/sigma_i^2")
            + " and the uncertainty of the average is 1/sqrt(sum_i 1/sigma_i^2).")
    material_values = {"values": v, "sigma": s, "stated_results": {"mean": stated(mean), "uncertainty": stated(unc)}}
    ok = (not within(mean, true_mean)) if defect else within(material_values["stated_results"]["mean"], true_mean)
    return text, material_values, {"oracle_ok": ok, "defect": "weights 1/sigma instead of 1/sigma^2" if defect else None,
                        "correct_mean": true_mean}


def fam_efficiency(rng, defect: bool):
    n = rng.randint(200, 2000)
    k = n - rng.randint(1, 15)  # efficiency close to 1
    eff = k / n
    binom = math.sqrt(eff * (1 - eff) / n)
    pois = math.sqrt(k) / n  # defect: Poisson error on the numerator only
    unc = pois if defect else binom
    text = ("An efficiency is estimated as k/n from k passing events out of n trials; its uncertainty is "
            + ("sqrt(k)/n." if defect else "sqrt(eps (1 - eps) / n) (binomial)."))
    material_values = {"k": k, "n": n, "stated_results": {"efficiency": stated(eff), "uncertainty": stated(unc)}}
    ok = (not within(unc, binom)) if defect else within(material_values["stated_results"]["uncertainty"], binom)
    return text, material_values, {"oracle_ok": ok, "defect": "Poisson error on k ignores the binomial correlation"
                        if defect else None, "correct_uncertainty": binom}


def fam_product(rng, defect: bool):
    a, b = round(rng.uniform(20, 60), 2), round(rng.uniform(20, 60), 2)
    sa, sb = round(a * rng.uniform(0.02, 0.06), 3), round(b * rng.uniform(0.02, 0.06), 3)
    rho = round(-rng.uniform(0.5, 0.9), 2)
    p = a * b
    rel_ok = math.sqrt((sa / a) ** 2 + (sb / b) ** 2 + 2 * rho * (sa / a) * (sb / b))
    rel_bad = math.sqrt((sa / a) ** 2 + (sb / b) ** 2)  # defect: correlation ignored
    rel = rel_bad if defect else rel_ok
    text = ("The product P = A B of two anticorrelated quantities is reported; their correlation coefficient is in "
            "data.json. The relative uncertainty of P is "
            + ("the quadrature sum of the relative uncertainties." if defect else
               "sqrt(rA^2 + rB^2 + 2 rho rA rB)."))
    material_values = {"A": a, "sigma_A": sa, "B": b, "sigma_B": sb, "correlation_AB": rho,
            "stated_results": {"P": stated(p), "sigma_P": stated(p * rel)}}
    ok = (not within(p * rel, p * rel_ok)) if defect else within(material_values["stated_results"]["sigma_P"], p * rel_ok)
    return text, material_values, {"oracle_ok": ok, "defect": "anticorrelation ignored in the propagation" if defect else None,
                        "correct_sigma": p * rel_ok}


FAMILIES = [fam_weights, fam_efficiency, fam_product]


def c03_instance(rng):
    """The missing input: sigma of one measurement; stated values reachable for an admissible value of it."""
    v = [round(rng.uniform(9.5, 10.5), 3) for _ in range(3)]
    s = [round(rng.uniform(0.1, 0.4), 3) for _ in range(3)]
    w = [1 / x ** 2 for x in s]
    mean, unc = sum(a * b for a, b in zip(w, v)) / sum(w), 1 / math.sqrt(sum(w))
    material_values = {"values": v, "sigma": [s[0], s[1], None], "stated_results": {"mean": stated(mean),
                                                                         "uncertainty": stated(unc)}}
    text = ("Three independent measurements are averaged with inverse-variance weights. The uncertainty of the third "
            "measurement is taken from its publication's supplementary table (not supplied).")
    # oracle: reachable (the true sigma reproduces both numbers) and undeterminable without it (another sigma differs)
    reach = within(material_values["stated_results"]["mean"], mean) and within(material_values["stated_results"]["uncertainty"], unc)
    w2 = w[:2] + [1 / (2 * s[2]) ** 2]
    other = 1 / math.sqrt(sum(w2))
    return text, material_values, {"oracle_ok": reach and not within(other, unc), "missing_input": "sigma of measurement 3"}


def build(seed: str, out: Path, per_type: int) -> dict:
    rng = random.Random(hashlib.sha256(seed.encode()).digest())
    out.mkdir(parents=True, exist_ok=True)
    (out / "instances").mkdir(exist_ok=True)
    (out / "expected").mkdir(exist_ok=True)
    oracle, n = {}, 0
    plan_types = [t for t in ("C01", "C02", "C03", "C04") for _ in range(per_type)]
    rng.shuffle(plan_types)
    for typ in plan_types:
        for _attempt in range(50):
            if typ == "C03":
                text, material_values, verdict = c03_instance(rng)
            else:
                fam = rng.choice(FAMILIES)
                text, material_values, verdict = fam(rng, defect=(typ == "C01"))
            if verdict["oracle_ok"]:
                break
        else:
            raise RuntimeError(f"no {typ} instance passed its oracle in 50 attempts")
        n += 1
        iid = "p" + hashlib.sha256(f"{seed}:{n}".encode()).hexdigest()[:8]
        reqs = [{"id": "REQ-1", "text": "The derived result and its uncertainty are statistically sound and "
                                        "reproducible from the supplied inputs."}]
        if typ == "C04":
            reqs.append({"id": "REQ-2", "text": "The inputs are tested for mutual consistency before they are used."})
        d = out / "instances" / iid
        (d / "material").mkdir(parents=True, exist_ok=True)
        (d / "material" / "analysis.md").write_text(f"# Analysis {iid}\n\n{text}\n", encoding="utf-8")
        (d / "material" / "data.json").write_text(json.dumps(material_values, indent=1) + "\n", encoding="utf-8")
        (d / "intent.json").write_text(json.dumps({"id": f"intent-{iid}", "target_tier": "R2",
                                                   "minimum_requirements": reqs}, indent=1) + "\n")
        obligations = [
            {"id": "O-stat", "origin_requirement_ids": ["REQ-1"], "question": STAT_Q, "required": True,
             "decision_required": True},
            {"id": "O-compute", "origin_requirement_ids": ["REQ-1"], "question": COMP_Q, "required": True,
             "decision_required": False}]
        (d / "plan.json").write_text(json.dumps({"id": f"plan-{iid}", "obligations": obligations}, indent=1) + "\n")
        exp = {"id": iid, "type": typ, **{k: v for k, v in verdict.items() if k != "oracle_ok"}}
        if typ == "C04":
            exp["unplanned_requirement"] = "REQ-2"
        (out / "expected" / f"{iid}.json").write_text(json.dumps(exp, indent=1) + "\n")
        oracle[iid] = {"type": typ, "oracle_ok": True}
    (out / "oracle.json").write_text(json.dumps(oracle, indent=1, sort_keys=True) + "\n")
    return {"status": "ok", "instances": n, "types": {t: plan_types.count(t) for t in ("C01", "C02", "C03", "C04")}}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--seed", required=True, help="a secret only the gold holder knows")
    p.add_argument("--out", required=True)
    p.add_argument("--per-type", type=int, default=4)
    a = p.parse_args(argv)
    print(json.dumps(build(a.seed, Path(a.out), a.per_type)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
