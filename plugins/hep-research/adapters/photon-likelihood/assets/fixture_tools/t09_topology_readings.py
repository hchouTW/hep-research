#!/usr/bin/env python3
"""Scoring side of T09, D3 stage 4: the topology readings of a light-likelihood-product/4 against its truth file
(t04-values-v4.md section 7, rows "Reversed, mirrored", "Topology hypotheses", "Mis-ID", "D_bar"; sections 9.3 and 9.4; cases
O-misid, O-mirror-reversed and O-dbar of the D3 stage 4 report). Readings only: no rate test, no limit of t04-values-v4.md is
compared and no verdict is given before K09; label shared-model closure.

stratum (a main stratum, H1 truth): mis-ID, H2 chosen, over all events (events with no choice, where H1 failed, apart); the
statistic 2 (lnL_2 - lnL_1) (largest, quantiles, counts above 15, 20, 25, 30); H2's start outcomes; from H1's reported fit,
the reversed fits (cosine of fitted to truth direction below -0.5) over converged fits, and the mirrored fits (fitted vertex
closer to -x_true than to x_true) over converged fits with |x_true| / R_s >= 0.4.
two-source (the two-source control, H2 truth): mis-ID, H1 chosen, over all events; the statistic (smallest, quantiles, counts
below 30) overall and by separation; H2's reported point against the nearer truth source; D_bar, a reported design figure
(section 7: "No rule reads it"), on the first --d-bar-events events: the charge-only Poisson count ln L on the expected means,
truth H2 against the best H1 fit from 8 starts taken from truth, each by Nelder-Mead.
pool: the reversed and mirrored readings pooled over the B2-B4 main strata (main strata 3 to 11; v4 9.4 tests them pooled).

Two gates, deterministic, in stratum and two-source: the per-channel probability sum at H2's points (the T09 stop; recomputed
by check-product before, read here); and the /4 carries its /3 unchanged (header but for format, hypothesis, product id and the
topology fields; every event line but its topology record; the /3's SHA-256 and product id as the /4 header records them).
Products are read for their structure only (check-product recomputes them before).

Every run this tool controls ends with RESULT {json} (re-review N-A). Usage:
  t09_topology_readings.py stratum --product P4 --multistart P3 --truth T --label L
  t09_topology_readings.py two-source --product P4 --multistart P3 --truth T2 --label L [--d-bar-events N]
  t09_topology_readings.py pool --label L --pair P4 T [--pair P4 T ...]
Exit codes are core/status.py's: 0 ok (both gates pass), 1 a gate fails, 2 refused input or an unexpected error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[3]
for _entry in (str(PLUGIN), str(HERE.parent), str(HERE)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import numpy  # noqa: E402
from scipy import optimize  # noqa: E402

from core.status import exit_code  # noqa: E402

from light_recipe import LABEL, configuration, light_model, likelihood, multistart, product, topology  # noqa: E402
import t09_fixture_files  # noqa: E402

REVERSED_COSINE = -0.5        # section 7, "Reversed, mirrored": cosine of fitted to truth direction below -0.5
MIRROR_RADIUS = 0.4           # section 7: mirrored is read for r / R_s at least 0.4
POOLED_STRATA = range(3, 12)  # B2-B4: main stratum 3 x bin + radial, bins 1 to 3 (v4 9.4, pooled over B2-B4)
D_BAR_STARTS = 8              # section 7, "D_bar": the best H1 fit from 8 starts
DOMAIN = 1.0 - likelihood.DOMAIN_MARGIN


class ReadingError(ValueError):
    """An input of the readings is refused."""


# --- the definitions of section 7 -------------------------------------------------------------------------------------------

def reversed_fit(direction_fit, direction_true) -> bool:
    return float(numpy.asarray(direction_fit, float) @ numpy.asarray(direction_true, float)) < REVERSED_COSINE


def mirrored_fit(vertex_fit, vertex_true) -> bool:
    x, t = numpy.asarray(vertex_fit, float), numpy.asarray(vertex_true, float)
    return float(numpy.linalg.norm(x + t)) < float(numpy.linalg.norm(x - t))


def in_mirror_population(vertex_true, r_s: float) -> bool:
    return float(numpy.linalg.norm(numpy.asarray(vertex_true, float))) / r_s >= MIRROR_RADIUS


def pooled_stratum(stratum: int) -> bool:
    return stratum in POOLED_STRATA


def mirror_reversed(fits, vertices, directions, r_s: float) -> dict:
    """Reversed and mirrored counts of H1's reported fits (converged fits; failures apart)."""
    out = {"events": len(fits), "converged": 0, "failed": 0, "reversed": 0, "mirror_population": 0, "mirrored": 0,
           "reversed_events": [], "mirrored_events": []}
    for i, f in enumerate(fits):
        if f["status"] != "converged":
            out["failed"] += 1
            continue
        out["converged"] += 1
        if reversed_fit(f["direction"], directions[i]):
            out["reversed"] += 1
            out["reversed_events"].append(i)
        if in_mirror_population(vertices[i], r_s):
            out["mirror_population"] += 1
            if mirrored_fit(f["vertex"], vertices[i]):
                out["mirrored"] += 1
                out["mirrored_events"].append(i)
    return out


def misid(topologies, truth: str) -> dict:
    """Choice counts over all events; mis-ID is the other hypothesis chosen (H1 truth: H2; H2 truth: H1)."""
    out = {"events": len(topologies), "decided": 0, "none": 0, "H1": 0, "H2": 0}
    for t in topologies:
        if t["choice"] is None:
            out["none"] += 1
        else:
            out["decided"] += 1
            out[t["choice"]] += 1
    out["misid"] = out["H2" if truth == "H1" else "H1"]
    return out


def d_bar_starts(vertices, directions) -> list:
    """The 8 H1 starts of D_bar (case O-dbar): each source's vertex with its own direction and with the other's, the midpoint with
    each direction, each source's vertex with its reversed direction."""
    mid = 0.5 * (vertices[0] + vertices[1])
    starts = [(vertices[0], directions[0]), (vertices[0], directions[1]), (vertices[1], directions[1]), (vertices[1], directions[0]),
              (mid, directions[0]), (mid, directions[1]), (vertices[0], -directions[0]), (vertices[1], -directions[1])]
    return starts[:D_BAR_STARTS]


def d_bar(model, vertices, directions, e_vis, live) -> float:
    """Section 7's D_bar: charge-only Poisson count ln L on the expected means m2 (both truth sources and dark), truth H2
    against the best H1 fit from 8 starts taken from truth (case O-dbar)."""
    live = numpy.asarray(live, bool)
    m2 = (sum(model.scale * e_vis[j] * light_model.shape(model, vertices[j], directions[j]) for j in range(2)) + model.dark)[live]
    best_possible = float((m2 * numpy.log(m2) - m2).sum())
    limit = model.cfg.sphere_radius_m * DOMAIN

    def minus_ln_l(p):
        x = p[:3]
        v = p[3:6]
        norm = numpy.linalg.norm(v)
        if not (numpy.linalg.norm(x) < limit and norm > 0 and math.isfinite(p[6])):
            return 1e300
        m1 = (model.scale * math.exp(p[6]) * light_model.shape(model, x, v / norm) + model.dark)[live]
        return float(-(m2 * numpy.log(m1) - m1).sum())

    best = math.inf
    for x, d in d_bar_starts(vertices, directions):
        e = float((m2 - model.dark).sum() / (model.scale * light_model.shape(model, x, d)[live].sum()))
        res = optimize.minimize(minus_ln_l, numpy.r_[x, d, math.log(e)], method="Nelder-Mead",
                                options={"maxiter": 6000, "maxfev": 6000, "xatol": 1e-7, "fatol": 1e-7, "adaptive": True})
        best = min(best, float(res.fun), minus_ln_l(numpy.r_[x, d, math.log(e)]))
    return best_possible + best


# --- reading the products ---------------------------------------------------------------------------------------------------

def _sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_pair(p4_path, p3_path, cfg, budget, tb):
    four = product.read_product(p4_path, None, cfg, budget, tb)
    if four.header["format"] != product.FORMAT_TOPOLOGY:
        raise ReadingError("--product must be light-likelihood-product/4")
    three = product.read_product(p3_path, None, cfg, budget) if p3_path is not None else None
    if three is not None and (three.header["format"] != product.FORMAT_MULTISTART
                              or three.header["input"]["sha256"] != four.header["input"]["sha256"]
                              or len(three.events) != len(four.events)):
        raise ReadingError("--multistart must be the light-likelihood-product/3 of the /4's readout")
    return four, three


def carry_defects(four, three, sha3: str) -> list:
    """The /4 carries its /3 unchanged (gate)."""
    defects = []
    keep = lambda h, drop: {k: v for k, v in h.items() if k not in drop}  # noqa: E731
    if keep(four.header, {"format", "hypothesis", "product_id", "topology", "h1_product"}) != keep(three.header, {"format", "hypothesis", "product_id"}):
        defects.append("the header differs from the /3's beyond format, hypothesis, product id and the topology fields")
    if four.header["h1_product"] != {"sha256": sha3, "product_id": three.header["product_id"]}:
        defects.append("the header's h1_product is not this /3's SHA-256 and product id")
    for a, b in zip(four.events, three.events):
        if {k: v for k, v in a.items() if k != "topology"} != b:
            defects.append(f"event {a['event']}: the event line differs from the /3's")
    return defects


def h2_check_line(label, events) -> tuple:
    checks = [d["topology"]["probability_check"] for d in events if d["topology"]["probability_check"] is not None]
    bad = sum(c["failures"] for c in checks)
    channels = sum(c["channels"] for c in checks)
    largest = max((c["max_abs_deviation"] for c in checks), default=0.0)
    ok = bad == 0
    return ok, (f"GATE {label} per-channel probability sum at H2's points (T09 stop): points {len(checks)}, channels {channels}, "
                f"failures {bad}, largest deviation {largest:.3e}: {'PASS' if ok else 'FAIL'}")


def _quantiles(values, qs) -> str:
    if not values:
        return "-"
    return ", ".join(f"{q:g} % {numpy.quantile(values, q / 100):.2f}" for q in qs)


def _common(label, four, three, sha3) -> tuple:
    defects = carry_defects(four, three, sha3)
    for line in defects[:10]:
        print(f"DEFECT {label} {line}")
    carry_ok = not defects
    sum_ok, sum_line = h2_check_line(label, four.events)
    print(sum_line)
    print(f"GATE {label} the topology product carries its multistart product unchanged, events {len(four.events)}, defects "
          f"{len(defects)}: {'PASS' if carry_ok else 'FAIL'}")
    return sum_ok and carry_ok


def _h2_outcomes(label, events) -> None:
    outcomes, reported, converged, with_point = {}, {}, 0, 0
    for d in events:
        h2 = d["topology"]["h2"]
        if h2 is None:
            continue
        for s in h2["starts"]:
            key = f"{s['name']}: {s['failure'] or 'converged'}"
            outcomes[key] = outcomes.get(key, 0) + 1
        idx = h2["reported"]["index"]
        name = "none" if idx is None else h2["starts"][idx]["name"]
        reported[name] = reported.get(name, 0) + 1
        if h2["fit"] is not None:
            with_point += 1
            converged += h2["fit"]["status"] == "converged"
    print(f"READING {label} H2 starts by outcome {dict(sorted(outcomes.items()))}; reported start {dict(sorted(reported.items()))}; "
          f"reported H2 fit converged {converged} of {with_point}")


def run_stratum(args) -> int:
    label = args.label
    cfg = configuration.load()
    four, three = read_pair(args.product, args.multistart, cfg, multistart.load(), topology.load())
    head, truth = t09_fixture_files.read_truth(args.truth)
    if head["readout_sha256"] != four.header["input"]["sha256"] or head["events"] != len(four.events):
        raise ReadingError("the truth file belongs to another readout")
    print(f"READING {label} label {LABEL}; development reading, no rate test and no gate of t04-values-v4.md before K09")
    topologies = [d["topology"] for d in four.events]
    m = misid(topologies, "H1")
    print(f"READING {label} mis-ID (H1 truth): events {m['events']}, decided {m['decided']}, no choice (H1 failed) {m['none']}, "
          f"H1 {m['H1']}, H2 {m['H2']}; H2 chosen {m['misid']} of {m['events']} ({m['misid']} of {m['decided']} decided)")
    stats = [t["statistic"] for t in topologies if t["statistic"] is not None]
    boundary = sum(t["ln_likelihood_2_from"] == topology.FROM_BOUNDARY for t in topologies)
    above = " ".join(f">{c}: {sum(s > c for s in stats)}" for c in (15, 20, 25)) + f" >=30: {sum(s >= topology.PENALTY for s in stats)}"
    print(f"READING {label} statistic 2 (lnL_2 - lnL_1): n {len(stats)}, largest {max(stats) if stats else float('nan'):.2f}, "
          f"quantiles {_quantiles(stats, (50, 90, 99))}; {above}; lnL_2 at H1's boundary {boundary}")
    _h2_outcomes(label, four.events)
    r_s = cfg.sphere_radius_m
    mr = mirror_reversed([d["fit"] for d in four.events], truth["vertex"], truth["direction"], r_s)
    print(f"READING {label} reversed (H1 fit, cosine to truth below {REVERSED_COSINE}): {mr['reversed']} of {mr['converged']} converged "
          f"(failed {mr['failed']}); events {mr['reversed_events'][:20]}")
    print(f"READING {label} mirrored (H1 fit closer to -x_true than x_true, |x_true|/R_s >= {MIRROR_RADIUS}): {mr['mirrored']} of "
          f"{mr['mirror_population']} in the population; events {mr['mirrored_events'][:20]}")
    return 0 if _common(label, four, three, _sha256(args.multistart)) else 1


def run_two_source(args) -> int:
    label = args.label
    cfg = configuration.load()
    model = likelihood.Model(cfg)
    four, three = read_pair(args.product, args.multistart, cfg, multistart.load(), topology.load())
    head, truth = t09_fixture_files.read_truth_two_source(args.truth)
    if head["readout_sha256"] != four.header["input"]["sha256"] or head["events"] != len(four.events):
        raise ReadingError("the truth file belongs to another readout")
    print(f"READING {label} label {LABEL}; development reading, no rate test and no gate of t04-values-v4.md before K09")
    topologies = [d["topology"] for d in four.events]
    m = misid(topologies, "H2")
    print(f"READING {label} mis-ID (H2 truth): events {m['events']}, decided {m['decided']}, no choice (H1 failed) {m['none']}, "
          f"H1 {m['H1']}, H2 {m['H2']}; H1 chosen {m['misid']} of {m['events']} ({m['misid']} of {m['decided']} decided)")
    stats = [t["statistic"] for t in topologies if t["statistic"] is not None]
    # Review F5: the events with no choice (H1 failed) in a line of their own, and the mis-ID with them counted as misses.
    print(f"READING {label} undecided (H1 failed, no H2 fit, no choice): {m['none']} of {m['events']}; mis-ID (H2 truth) with the "
          f"undecided counted as misses: {m['misid'] + m['none']} of {m['events']}")
    print(f"READING {label} statistic 2 (lnL_2 - lnL_1): n {len(stats)}, smallest {min(stats) if stats else float('nan'):.2f}, "
          f"quantiles {_quantiles(stats, (1, 5, 50))}; below 30: {sum(s < topology.PENALTY for s in stats)}")
    r_s = cfg.sphere_radius_m
    edges = (0.4, 0.4 + 0.8 / 3, 0.4 + 1.6 / 3, 1.2 + 1e-12)
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = [t["statistic"] for t, s in zip(topologies, truth["separation"]) if lo * r_s <= s < hi * r_s and t["statistic"] is not None]
        print(f"READING {label} statistic by separation [{lo:.3f}, {min(hi, 1.2):.3f}) R_s: n {len(sel)}, smallest "
              f"{min(sel) if sel else float('nan'):.2f}, below 30: {sum(s < topology.PENALTY for s in sel)}")
    _h2_outcomes(label, four.events)
    distances = []
    for d, vs in zip(four.events, truth["vertex"]):
        h2 = d["topology"]["h2"]
        if h2 is None or h2["fit"] is None:
            continue
        fitted = [numpy.array(s["vertex"]) for s in h2["fit"]["sources"]]
        direct = max(numpy.linalg.norm(fitted[0] - vs[0]), numpy.linalg.norm(fitted[1] - vs[1]))
        swapped = max(numpy.linalg.norm(fitted[0] - vs[1]), numpy.linalg.norm(fitted[1] - vs[0]))
        distances.append(float(min(direct, swapped)))
    print(f"READING {label} H2 reported vertices against truth (larger of the two distances, best pairing, m): n {len(distances)}, "
          f"quantiles {_quantiles(distances, (50, 90, 99))}")
    count = min(args.d_bar_events, len(four.events))
    values = []
    for i in range(count):
        live = numpy.array([c in "HU" for c in four.events[i]["states"]])
        values.append(d_bar(model, truth["vertex"][i], truth["direction"][i], truth["e_vis"][i], live))
    print(f"READING {label} D_bar (section 7, a reported design figure, no rule reads it; charge-only, expected data, 8 starts) on "
          f"the first {count} events: quantiles {_quantiles(values, (0, 1, 5, 50))}")
    return 0 if _common(label, four, three, _sha256(args.multistart)) else 1


def run_pool(args) -> int:
    label = args.label
    cfg = configuration.load()
    budget, tb = multistart.load(), topology.load()
    strata, totals = [], {"converged": 0, "failed": 0, "reversed": 0, "mirror_population": 0, "mirrored": 0}
    for p4, t in args.pair:
        four, _ = read_pair(p4, None, cfg, budget, tb)
        head, truth = t09_fixture_files.read_truth(t)
        if head["readout_sha256"] != four.header["input"]["sha256"] or head["fixture"] != "main":
            raise ReadingError(f"{t}: not the main-fixture truth file of {p4}")
        if not pooled_stratum(head["stratum"]):
            continue
        strata.append(head["stratum"])
        mr = mirror_reversed([d["fit"] for d in four.events], truth["vertex"], truth["direction"], cfg.sphere_radius_m)
        for key in totals:
            totals[key] += mr[key]
    print(f"READING {label} label {LABEL}; development reading, no rate test and no gate of t04-values-v4.md before K09")
    print(f"READING {label} pooled B2-B4 strata {sorted(strata)}: reversed {totals['reversed']} of {totals['converged']} converged "
          f"(failed {totals['failed']}); mirrored {totals['mirrored']} of {totals['mirror_population']} in the population")
    return 0


def _result(operation: str, status: str, reason: str) -> int:
    code = exit_code(status)
    print("RESULT " + json.dumps({"operation": operation, "status": status, "exit_code": code, "reason": reason}, sort_keys=True),
          flush=True)
    return code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    s = sub.add_parser("stratum")
    w = sub.add_parser("two-source")
    for p in (s, w):
        p.add_argument("--product", required=True)
        p.add_argument("--multistart", required=True)
        p.add_argument("--truth", required=True)
        p.add_argument("--label", required=True)
    w.add_argument("--d-bar-events", type=int, default=100)
    q = sub.add_parser("pool")
    q.add_argument("--label", required=True)
    q.add_argument("--pair", nargs=2, action="append", required=True, metavar=("P4", "TRUTH"))
    args = ap.parse_args(argv)
    run = {"stratum": run_stratum, "two-source": run_two_source, "pool": run_pool}[args.operation]
    try:
        code = run(args)
    except (ReadingError, product.ProductError, t09_fixture_files.FixtureError, configuration.ConfigurationError,
            multistart.BudgetError, topology.BudgetError, OSError) as exc:
        print(f"REFUSED {args.label}: {exc}")
        return _result(args.operation, "rejected", str(exc))
    except Exception as exc:  # noqa: BLE001 - a defect of the tool: status error, never a gate failing
        print(f"ERROR {args.label}: unexpected {type(exc).__name__}: {exc}", flush=True)
        return _result(args.operation, "error", f"unexpected {type(exc).__name__}: {exc}")
    return _result(args.operation, "ok" if code == 0 else "failed", "" if code == 0 else "a gate failed (its GATE line ends FAIL)")


if __name__ == "__main__":
    sys.exit(main())
