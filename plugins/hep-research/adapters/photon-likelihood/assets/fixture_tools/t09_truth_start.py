#!/usr/bin/env python3
"""Scoring side of T09, D3 stage 3: the truth-start fit and the wrong-minimum and fit-failure readings (t04-values-v4.md section 7,
rows "Truth-start fit", "Wrong minimum", "Fit failure", "Pull population"; cases O-truth-start to O-start0 of the D3 stage 3
report). Readings only: no rate test, no gate verdict of t04-values-v4.md before K09; label shared-model closure.

fit: the truth-start fit is the recipe's joint fit (light_recipe.fit.fit_joint_event: the same rounds, convergence rule, failure
kinds and covariance) started at truth (vertex, direction, E_vis and t0 of the t09-truth/1 file), one start per event. It is
scoring side only: it reads the truth file, its output t09-truth-start/1 (role scoring-comparator, JSON Lines) is never a
data-side product (the recipe's readers refuse it, and the recipe imports no fixture tool), and it is never reported as a
result.

compare: per stratum, for the one-seed fit (light-likelihood-product/2) and the multistart fit (/3) on the same events:
- fit failures by kind (denominator: all events);
- wrong minimum, over events whose reported fit converged and whose truth-start fit converged (otherwise "comparator
  unavailable", counted apart; inside it, the events whose failed truth-start fit already stopped at a point with ln L at
  least 0.5 above the reported fit's are shown apart, "clause (a) shown by a failed truth-start", and not added to clause (a):
  review F2): clause (a), the truth-start fit's ln L at least CLAUSE_A_LN_L (0.5) above the reported fit's;
  clause (b), any of the 7 parameters more than CLAUSE_B_SIGMAS (5) truth-start uncertainties from truth (x, y, z, E_vis, t0
  directly; the direction residuals (d_fit - d_true) . e_k at section 7's truth frame, with the truth-start tangent covariance
  projected there by J_kj = e_k(truth) . e_j(truth-start)). Clause (b) counts where v4 gates pulls (B2-B4, and the dead and
  saturation controls, both B3); in B1 it is reported only, and B1's wrong-minimum total is clause (a) alone. Clause (b) as v4
  defines it is blind to an exactly reversed direction: with d_fit = -d_true the residuals (d_fit - d_true) . e_k vanish, so the
  B2-B4 clause (b) counts are not direction-complete (such a fit shows in clause (a), the vertex or t0; v4 9.4's reversed rate
  covers it at the topology stage) (review N4);
- beside them the pull widths of the reported fits (t09_readings' pulls, wrong minima included: v4's pull population);
- the products are read for their structure only (check-product recomputes them before);
- two gates, deterministic: start 0 of /3 is the one-seed fit of /2 (seed, prefit, status, failure, ln L, end point, iterations,
  rounds) on every event; wherever the one-seed fit converged, the multistart ln L is at least the one-seed ln L minus the
  budget's tie tolerance.
Usage: t09_truth_start.py fit --readout R --truth T --out F
       t09_truth_start.py compare --one-seed P2 --multistart P3 --truth T --truth-start F --label L
Exit codes are core/status.py's: 0 ok (compare: both gates pass), 1 a gate fails, 2 refused input or an unexpected error (an
ERROR line).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[3]
for _entry in (str(PLUGIN), str(HERE.parent), str(HERE)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import numpy  # noqa: E402

from core.status import exit_code  # noqa: E402

from light_recipe import LABEL, configuration, fit, joint, likelihood, multistart, product, readout  # noqa: E402
from light_recipe.likelihood import frame  # noqa: E402
import t09_fixture_files  # noqa: E402
import t09_readings  # noqa: E402

FORMAT = "t09-truth-start/1"
ROLE = "scoring-comparator"
RULE = ("the recipe's joint fit (fit_joint_event) started at truth, one start; scoring side only, never on the data side, never "
        "reported as a result (t04-values-v4.md section 7)")
CLAUSE_A_LN_L = 0.5            # section 7, wrong minimum (a): the truth-start ln L at least 0.5 higher
CLAUSE_B_SIGMAS = 5.0          # section 7, wrong minimum (b): more than 5 truth-start uncertainties from truth
NAMES = t09_readings.PULL_NAMES_JOINT
HEADER_KEYS = {"format", "role", "label", "rule", "readout_sha256", "truth_sha256", "configuration_sha256", "events"}
EVENT_KEYS = {"event", "status", "failure", "ln_likelihood", "vertex", "direction", "e_vis", "t0", "frame", "covariance",
              "iterations", "rounds"}


class TruthStartError(ValueError):
    """A truth-start file or a comparator input is refused."""


def truth_start_fit(model, tev, vertex, direction, e_vis, t0):
    start = fit.JointSeed(numpy.asarray(vertex, float), numpy.asarray(direction, float), float(e_vis), float(t0))
    return fit.fit_joint_event(model, tev, start)


def _vec(v):
    return None if v is None else [float(c) for c in v]


def event_document(index: int, res) -> dict:
    return {"event": index, "status": res.status, "failure": res.failure,
            "ln_likelihood": None if res.ln_likelihood is None else float(res.ln_likelihood), "vertex": _vec(res.vertex),
            "direction": _vec(res.direction), "e_vis": None if res.e_vis is None else float(res.e_vis),
            "t0": None if res.t0 is None else float(res.t0),
            "frame": None if res.e1 is None else {"e1": _vec(res.e1), "e2": _vec(res.e2)},
            "covariance": None if res.covariance is None else [[float(x) for x in row] for row in res.covariance],
            "iterations": int(res.iterations), "rounds": int(res.rounds)}


def read_truth_start(path):
    """(header, event documents) of a t09-truth-start/1 file; refuses any other format, role or an incomplete file."""
    try:
        text = Path(path).read_text(encoding="utf-8")
        docs = [json.loads(line) for line in text.splitlines()]
    except (OSError, UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise TruthStartError(f"truth-start file cannot be read: {exc}") from None
    if len(docs) < 2 or not isinstance(docs[0], dict) or set(docs[0]) != HEADER_KEYS or docs[0]["format"] != FORMAT \
            or docs[0]["role"] != ROLE:
        raise TruthStartError(f"not a {FORMAT} file of role {ROLE}")
    header, events, end = docs[0], docs[1:-1], docs[-1]
    if end != {"end": FORMAT, "events": len(events)} or header["events"] != len(events):
        raise TruthStartError("the truth-start file is incomplete")
    for i, doc in enumerate(events):
        if not isinstance(doc, dict) or set(doc) != EVENT_KEYS or doc["event"] != i:
            raise TruthStartError(f"truth-start event {i} malformed")
    return header, events


def run_fit(args) -> int:
    out = Path(args.out)
    if out.exists():
        print(f"REFUSED truth-start: {out} exists, never overwritten")
        return exit_code("rejected")
    try:
        cfg = configuration.load()
        model = likelihood.Model(cfg)
        rd = readout.read_file(args.readout)
        head, truth = t09_fixture_files.read_truth(args.truth)
    except (configuration.ConfigurationError, readout.ReadoutError, t09_fixture_files.FixtureError) as exc:
        print(f"REFUSED truth-start: {exc}")
        return exit_code("rejected")
    if head["readout_sha256"] != rd.sha256 or head["events"] != rd.events:
        print("REFUSED truth-start: the truth file belongs to another readout")
        return exit_code("rejected")
    header = {"format": FORMAT, "role": ROLE, "label": LABEL, "rule": RULE, "readout_sha256": rd.sha256,
              "truth_sha256": hashlib.sha256(Path(args.truth).read_bytes()).hexdigest(), "configuration_sha256": cfg.sha256,
              "events": rd.events}
    partial = out.with_name(out.name + ".partial")
    counts: dict = {}
    try:
        with open(partial, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(header, sort_keys=True) + "\n")
            for i in range(rd.events):
                tev = joint.TimedEvent.from_readout(rd, i)
                res = truth_start_fit(model, tev, truth["vertex"][i], truth["direction"][i], truth["e_vis"][i], truth["t0"][i])
                counts[res.failure or "converged"] = counts.get(res.failure or "converged", 0) + 1
                stream.write(json.dumps(event_document(i, res), sort_keys=True, allow_nan=False) + "\n")
            stream.write(json.dumps({"end": FORMAT, "events": rd.events}, sort_keys=True) + "\n")
        os.replace(partial, out)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    print(f"READING truth-start fits events {rd.events} by outcome {dict(sorted(counts.items()))} (scoring side, never a result)")
    return exit_code("ok")


# --- the clauses -------------------------------------------------------------------------------------------------------

def clause_a(ln_l_reported: float, ln_l_truth_start: float) -> bool:
    return ln_l_truth_start - ln_l_reported >= CLAUSE_A_LN_L


def clause_b_ratios(point: dict, truth: dict, ts: dict) -> dict:
    """|theta_fit - theta_true| / sigma_truth-start per parameter; the direction at section 7's truth frame."""
    cov = numpy.array(ts["covariance"], float)
    sigma = numpy.sqrt(numpy.diag(cov))
    vertex = numpy.asarray(point["vertex"], float)
    tv = numpy.asarray(truth["vertex"], float)
    out = {name: float(abs(vertex[k] - tv[k]) / sigma[k]) for k, name in enumerate(("x", "y", "z"))}
    out["e_vis"] = float(abs(point["e_vis"] - truth["e_vis"]) / sigma[5])
    out["t0"] = float(abs(point["t0"] - truth["t0"]) / sigma[6])
    d_true = numpy.asarray(truth["direction"], float)
    t1, t2 = frame(d_true)
    f1, f2 = numpy.asarray(ts["frame"]["e1"], float), numpy.asarray(ts["frame"]["e2"], float)
    jac = numpy.array([[t1 @ f1, t1 @ f2], [t2 @ f1, t2 @ f2]])
    tangent = jac @ cov[3:5, 3:5] @ jac.T
    d_fit = numpy.asarray(point["direction"], float)
    for name, axis, k in (("u1", t1, 0), ("u2", t2, 1)):
        out[name] = float(abs((d_fit - d_true) @ axis) / math.sqrt(tangent[k, k]))
    return out


def clause_b(ratios: dict) -> bool:
    return any(r > CLAUSE_B_SIGMAS for r in ratios.values())


def bin_of(truth_header: dict) -> int:
    """The stratum's N_exp bin: main stratum s is B(s // 3 + 1) (3 x bin + radial); the dead and saturation controls are B3."""
    return truth_header["stratum"] // 3 + 1 if truth_header["fixture"] == "main" else 3


def clause_b_counts(truth_header: dict) -> bool:
    """Clause (b) counts where v4 gates pulls: B2-B4 and the B3 controls; in B1 it is reported only (section 7)."""
    return bin_of(truth_header) >= 2


def tally(fits, ts_docs, truth: dict, counted: bool) -> dict:
    """Failure, wrong-minimum and comparator counts of one fit's event documents against the truth-start documents."""
    out = {"events": len(fits), "converged": 0, "failures": {}, "evaluated": 0, "unavailable": 0, "clause_a": 0, "clause_b": 0,
           "wrong_minimum": 0, "unavailable_shows_a": 0, "largest_gain": None, "largest_ratio": None, "wrong_events": []}
    for i, (f, ts) in enumerate(zip(fits, ts_docs)):
        if f["status"] != "converged":
            out["failures"][f["failure"]] = out["failures"].get(f["failure"], 0) + 1
            continue
        out["converged"] += 1
        if ts["status"] != "converged":
            out["unavailable"] += 1
            if ts["ln_likelihood"] is not None and clause_a(f["ln_likelihood"], ts["ln_likelihood"]):
                out["unavailable_shows_a"] += 1      # trust-exact only accepts steps that raise ln L (review F2)
            continue
        out["evaluated"] += 1
        t = {"vertex": truth["vertex"][i], "direction": truth["direction"][i], "e_vis": float(truth["e_vis"][i]), "t0": float(truth["t0"][i])}
        a = clause_a(f["ln_likelihood"], ts["ln_likelihood"])
        ratios = clause_b_ratios(f, t, ts)
        b = clause_b(ratios)
        gain = ts["ln_likelihood"] - f["ln_likelihood"]
        out["largest_gain"] = gain if out["largest_gain"] is None else max(out["largest_gain"], gain)
        top = max(ratios.values())
        out["largest_ratio"] = top if out["largest_ratio"] is None else max(out["largest_ratio"], top)
        out["clause_a"] += a
        out["clause_b"] += b
        wrong = a or (b and counted)
        out["wrong_minimum"] += wrong
        if wrong:
            out["wrong_events"].append(i)
    out["failures"] = dict(sorted(out["failures"].items()))
    return out


def _pull_widths(fits, truth) -> str:
    pulls = {name: [] for name in NAMES}
    for i, f in enumerate(fits):
        if f["status"] != "converged":
            continue
        for name, value in t09_readings.event_pulls(f, truth["vertex"][i], truth["direction"][i], truth["e_vis"][i],
                                                    float(truth["t0"][i])).items():
            pulls[name].append(value)
    return " ".join(f"{name} {t09_readings.width(v):.4f}" if v else f"{name} -" for name, v in pulls.items())


def _start0_defects(one, many) -> list:
    defects = []
    for a, b in zip(one, many):
        i = a["event"]
        if a["seed"] != b["seed"] or a["prefit"] != b["prefit"]:
            defects.append(f"event {i}: seed or prefit differ")
            continue
        if not b["starts"]:
            if a["fit"]["failure"] != "no-hit-channel" or b["fit"]["failure"] != "no-hit-channel":
                defects.append(f"event {i}: no start in /3 but a one-seed fit")
            continue
        s0, f = b["starts"][0], a["fit"]
        end = None if f["vertex"] is None else {"vertex": f["vertex"], "direction": f["direction"], "e_vis": f["e_vis"], "t0": f["t0"]}
        if (s0["status"], s0["failure"], s0["ln_likelihood"], s0["iterations"], s0["rounds"], s0["end"]) != \
                (f["status"], f["failure"], f["ln_likelihood"], f["iterations"], f["rounds"], end):
            defects.append(f"event {i}: start 0 is not the one-seed fit")
    if len(one) != len(many):
        defects.append(f"{len(one)} one-seed events, {len(many)} multistart events")
    return defects


def run_compare(args) -> int:
    label = args.label
    try:
        cfg = configuration.load()
        budget = multistart.load()
        # Structure only: check-product has recomputed both products' ln L and probability checks already.
        one = product.read_product(args.one_seed, None, cfg)
        many = product.read_product(args.multistart, None, cfg, budget)
        head, truth = t09_fixture_files.read_truth(args.truth)
        ts_head, ts_docs = read_truth_start(args.truth_start)
    except (configuration.ConfigurationError, multistart.BudgetError, product.ProductError, t09_fixture_files.FixtureError,
            TruthStartError) as exc:
        print(f"REFUSED {label}: {exc}")
        return exit_code("rejected")
    if one.header["format"] != product.FORMAT_JOINT or many.header["format"] != product.FORMAT_MULTISTART:
        print(f"REFUSED {label}: --one-seed must be light-likelihood-product/2 and --multistart /3")
        return exit_code("rejected")
    sha = {one.header["input"]["sha256"], many.header["input"]["sha256"], head["readout_sha256"], ts_head["readout_sha256"]}
    if len(sha) != 1 or not (len(one.events) == len(many.events) == head["events"] == len(ts_docs)):
        print(f"REFUSED {label}: the products, the truth file and the truth-start file do not belong to one readout")
        return exit_code("rejected")
    if ts_head["truth_sha256"] != hashlib.sha256(Path(args.truth).read_bytes()).hexdigest() or \
            {ts_head["configuration_sha256"], one.header["configuration"]["sha256"], many.header["configuration"]["sha256"]} != {cfg.sha256}:
        print(f"REFUSED {label}: the truth-start file was made from another truth file or configuration (review N5)")
        return exit_code("rejected")
    counted = clause_b_counts(head)
    bin_ = bin_of(head)
    print(f"READING {label} label {LABEL}; development reading, no rate test and no gate of t04-values-v4.md before K09")
    ts_counts: dict = {}
    for d in ts_docs:
        ts_counts[d["failure"] or "converged"] = ts_counts.get(d["failure"] or "converged", 0) + 1
    print(f"READING {label} truth-start fits (scoring side, never a result) events {len(ts_docs)} by outcome {dict(sorted(ts_counts.items()))}")
    where_b = "clause (b) counted" if counted else "clause (b) reported only, B1 (t04-values-v4.md section 7)"
    tallies = {}
    for name, read in (("one-seed", one), ("multistart", many)):
        fits = [doc["fit"] for doc in read.events]
        t = tally(fits, ts_docs, truth, counted)
        tallies[name] = t
        print(f"READING {label} {name} fits events {t['events']} converged {t['converged']} failed {t['events'] - t['converged']} "
              f"by kind {t['failures']}")
        gain = "-" if t["largest_gain"] is None else f"{t['largest_gain']:.3f}"
        ratio = "-" if t["largest_ratio"] is None else f"{t['largest_ratio']:.2f}"
        print(f"READING {label} {name} wrong minimum (B{bin_}): evaluated {t['evaluated']}, comparator unavailable {t['unavailable']} (of which "
              f"clause (a) shown by a failed truth-start {t['unavailable_shows_a']}, not counted), "
              f"clause (a) {t['clause_a']}, clause (b) {t['clause_b']} [{where_b}], wrong minima {t['wrong_minimum']}; largest "
              f"truth-start ln L gain {gain}, largest |residual| / sigma_ts {ratio}; events {t['wrong_events'][:20]}")
        print(f"READING {label} {name} pull widths (beside; converged fits, wrong minima included): {_pull_widths(fits, truth)}")
    chosen: dict = {}
    for doc in many.events:
        c = doc["choice"]
        key = "none" if c["chosen"] is None else doc["starts"][c["chosen"]]["name"]
        chosen[key] = chosen.get(key, 0) + 1
    rescued = sum(a["fit"]["status"] != "converged" and b["fit"]["status"] == "converged" for a, b in zip(one.events, many.events))
    better = sum(a["fit"]["status"] == "converged" and b["fit"]["status"] == "converged"
                 and b["fit"]["ln_likelihood"] > a["fit"]["ln_likelihood"] + CLAUSE_A_LN_L for a, b in zip(one.events, many.events))
    rules: dict = {}
    for doc in many.events:
        rules[doc["choice"]["rule"]] = rules.get(doc["choice"]["rule"], 0) + 1
    print(f"READING {label} multistart effect: one-seed failures rescued {rescued}; ln L above the one-seed fit's by at least "
          f"{CLAUSE_A_LN_L}: {better}; chosen start {dict(sorted(chosen.items()))}; rule {dict(sorted(rules.items()))}")
    defects = _start0_defects(one.events, many.events)
    for line in defects[:10]:
        print(f"DEFECT {label} {line}")
    print(f"GATE {label} start 0 of the multistart fit is the one-seed fit (seed, prefit, outcome, end point), events "
          f"{len(one.events)}, defects {len(defects)}: {'PASS' if not defects else 'FAIL'}")
    tie = many.header["budget"]["tie_tolerance"]
    lower = [a["event"] for a, b in zip(one.events, many.events) if a["fit"]["status"] == "converged"
             and not (b["fit"]["status"] == "converged" and b["fit"]["ln_likelihood"] >= a["fit"]["ln_likelihood"] - tie)]
    print(f"GATE {label} multistart ln L at least the one-seed ln L where the one-seed fit converged (tie tolerance {tie:g}), "
          f"events {tallies['one-seed']['converged']}, below {len(lower)}: {'PASS' if not lower else 'FAIL'}")
    return exit_code("ok" if not defects and not lower else "failed")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    f = sub.add_parser("fit", help="the truth-start fit of every event (scoring side)")
    f.add_argument("--readout", required=True)
    f.add_argument("--truth", required=True)
    f.add_argument("--out", required=True)
    c = sub.add_parser("compare", help="failure, wrong-minimum and pull readings, one-seed against multistart")
    c.add_argument("--one-seed", required=True)
    c.add_argument("--multistart", required=True)
    c.add_argument("--truth", required=True)
    c.add_argument("--truth-start", required=True)
    c.add_argument("--label", required=True)
    args = ap.parse_args(argv)
    try:
        return run_fit(args) if args.operation == "fit" else run_compare(args)
    except Exception as exc:  # noqa: BLE001 - a defect of the tool or the recipe: status error, never a gate failing
        print(f"ERROR truth-start {args.operation}: unexpected {type(exc).__name__}: {exc}", flush=True)
        return exit_code("error")


if __name__ == "__main__":
    sys.exit(main())
