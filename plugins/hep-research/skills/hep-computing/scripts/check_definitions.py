#!/usr/bin/env python3
"""Check definitions for research deliverables: roles, types, four-valued results, decision rules, multiple testing,
cross-round error control and the criteria freeze record (reconstruction v12 A2; VAL-01..VAL-05). Standard library only.

Purpose: the method-layer definitions a check program and its caller share, so that a check result is decided by a
rule frozen before the result was seen, never by the text written afterwards. The rules follow Methods §2 of the
reconstruction v12.1 spec copy (evals/reconstruction-v12/spec/ in the source repository); the statistical choices
themselves (intervals, covariance, power estimates) are made with hep-statistics, this module only applies them.
Definitions:
- check roles: closure (internal consistency, never confirmation), confirmation-holdout, confirmation-independent;
  check types: threshold (a requirement with an acceptance region) and performance-estimate (value ± uncertainty with
  validity checks under a frozen tolerance; no threshold is invented).
- results are four-valued: pass, fail, inconclusive, not-applicable, each with a reason; not-applicable needs the task
  type and a reason and is allowed only where the contract allowed it in advance.
- threshold decision (three regions): interval entirely inside the acceptance region -> pass, entirely outside -> fail,
  straddling -> inconclusive; when the frozen power design was not met before execution, a pass becomes inconclusive
  (a fail stays fail: power is never used after the fact to change a decision).
- tolerance decision: |deviation| < max(k*sigma_stat, delta_phys) with tolerance <= the claimed total uncertainty;
  a deviation incompatible with zero inside the tolerance is a pass with a transferred systematic; a check whose own
  precision is not below the claimed uncertainty raises the non-closure systematic to at least that precision.
- multiple testing over bins: when pass rejects "non-compliant" (intersection-union), per-bin alpha is unchanged; when
  fail rejects "compatible", per-bin alpha/n (Bonferroni) or Sidak; inconclusive counts as not passed unless the freeze
  says otherwise.
- cross-round error control: a frozen ceiling on the overall false-pass rate. Threshold: (a) sum of alpha_r <= alpha
  with each round at level 1 - alpha_r, or (b) a cap R whose implied rate 1-(1-alpha)^R (independent fresh samples) or
  min(1, R*alpha) (any reused sample) stays within the ceiling. Compatibility: alpha is never split (a later round would
  pass more easily); the budget p_total is split as per-round pass probabilities under the unfavourable alternative.
- freeze record (DEC-03 default: append-only JSON lines, each carrying the SHA-256 of the previous line, canonical
  JSON): closed fields, validated before it is written.
Usage:
  check_definitions.py validate-freeze FILE.json         one freeze record (JSON object) -> problems
  check_definitions.py decide SPEC.json                   {"rule": "threshold"|"tolerance"|"combine"|"rounds", ...}
  check_definitions.py verify-chain FREEZES.jsonl         the digest chain of an append-only freeze log
Output JSON: status (ok, refused, rejected) and the result. Exit codes: 0 ok, 1 refused (the record or rule does not
conform), 2 bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
from core.status import exit_code  # noqa: E402

RESULTS = ("pass", "fail", "inconclusive", "not-applicable")
ROLES = ("closure", "confirmation-holdout", "confirmation-independent")
TYPES = ("threshold", "performance-estimate")
DEFAULT_POWER = {"min_pass_favourable": 0.8, "max_pass_unfavourable": 0.2}
HEX64 = frozenset("0123456789abcdef")


class RuleError(ValueError):
    """The input does not conform to a frozen rule (refused, exit 1)."""


def _hex64(x) -> bool:
    return isinstance(x, str) and len(x) == 64 and set(x) <= HEX64


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _prob(x) -> bool:
    return _num(x) and 0 < x < 1


def canonical(document) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def result(value: str, reason: str, *, task_type: str | None = None, transferred_systematic: float | None = None) -> dict:
    """A four-valued check result. not-applicable needs the task type and a reason (never a waiver after a failure)."""
    if value not in RESULTS:
        raise RuleError(f"result {value!r} is not one of {RESULTS}")
    if not isinstance(reason, str) or not reason.strip():
        raise RuleError("every result carries a reason")
    if value == "not-applicable" and not (isinstance(task_type, str) and task_type.strip()):
        raise RuleError("not-applicable needs the task type and a reason")
    out = {"result": value, "reason": reason}
    if task_type:
        out["task_type"] = task_type
    if transferred_systematic is not None:
        out["transferred_systematic"] = transferred_systematic
    return out


def threshold_decision(interval: tuple[float, float], region: tuple[float | None, float | None], *,
                       power_met: bool) -> dict:
    """Three-region rule for threshold validation. region = (low, high) of the acceptance region; None = unbounded."""
    lo, hi = interval
    a, b = region
    if not (_num(lo) and _num(hi) and lo <= hi) or (a is None and b is None) or \
            not all(v is None or _num(v) for v in (a, b)) or (a is not None and b is not None and a > b):
        raise RuleError("an interval (low <= high) and an acceptance region with at least one finite bound")
    inside = (a is None or lo >= a) and (b is None or hi <= b)
    outside = (a is not None and hi < a) or (b is not None and lo > b)
    if outside:
        return result("fail", "interval entirely outside the acceptance region")
    if inside:
        if not power_met:
            return result("inconclusive", "the frozen power design was not met before execution: at most inconclusive")
        return result("pass", "interval entirely inside the acceptance region")
    return result("inconclusive", "interval straddles the acceptance boundary")


def tolerance(k: float, sigma_stat: float, delta_phys: float) -> float:
    if not all(_num(v) and v >= 0 for v in (k, sigma_stat, delta_phys)):
        raise RuleError("k, sigma_stat and delta_phys are finite and >= 0")
    return max(k * sigma_stat, delta_phys)


def tolerance_decision(deviation: float, deviation_sigma: float, *, k: float, sigma_stat: float, delta_phys: float,
                       claimed_total: float, check_precision: float, zero_compat_z: float = 2.0) -> dict:
    """Validity check of a performance estimate: pass, pass with a transferred systematic, or fail."""
    if not all(_num(v) for v in (deviation, deviation_sigma, claimed_total, check_precision, zero_compat_z)) or \
            deviation_sigma < 0 or claimed_total <= 0 or check_precision < 0 or zero_compat_z <= 0:
        raise RuleError("finite deviation, its sigma >= 0, claimed total uncertainty > 0, check precision >= 0")
    tol = tolerance(k, sigma_stat, delta_phys)
    if tol > claimed_total:
        raise RuleError(f"the tolerance {tol:g} exceeds the claimed total uncertainty {claimed_total:g}")
    floor = check_precision if check_precision >= claimed_total else 0.0  # non-closure systematic >= check precision
    if abs(deviation) >= tol:
        return result("fail", f"|deviation| {abs(deviation):g} >= tolerance {tol:g}")
    incompatible = deviation_sigma == 0 and deviation != 0 or \
        deviation_sigma > 0 and abs(deviation) / deviation_sigma > zero_compat_z
    transfer = max(abs(deviation) if incompatible else 0.0, floor)
    if transfer > 0:
        return result("pass", "within tolerance; the non-zero deviation (or the check precision) becomes a systematic",
                      transferred_systematic=transfer)
    return result("pass", f"|deviation| {abs(deviation):g} < tolerance {tol:g}")


def per_bin_alpha(alpha: float, n: int, rejection: str, method: str = "bonferroni") -> float:
    """Per-bin level for n bins. rejection: 'pass-rejects-noncompliant' (intersection-union: unchanged) or
    'fail-rejects-compatible' (Bonferroni alpha/n or Sidak)."""
    if not _prob(alpha) or not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise RuleError("alpha in (0, 1) and n >= 1 bins")
    if rejection == "pass-rejects-noncompliant":
        return alpha
    if rejection != "fail-rejects-compatible":
        raise RuleError("rejection is pass-rejects-noncompliant or fail-rejects-compatible")
    if method == "bonferroni":
        return alpha / n
    if method == "sidak":
        return 1 - (1 - alpha) ** (1 / n)
    raise RuleError("method is bonferroni or sidak")


def combine(results: list[str], *, inconclusive_as: str = "not-passed") -> dict:
    """All-bins rule: pass only if every bin passes; any fail -> fail; otherwise inconclusive (as frozen)."""
    if not results or any(r not in RESULTS for r in results):
        raise RuleError("a non-empty list of four-valued results")
    if inconclusive_as not in ("not-passed", "fail"):
        raise RuleError("inconclusive counts as not-passed or fail")
    if any(r == "fail" for r in results):
        return result("fail", "a bin failed")
    if any(r in ("inconclusive", "not-applicable") for r in results):
        return result("fail" if inconclusive_as == "fail" else "inconclusive",
                      "a bin is inconclusive or not applicable (counted as frozen)")
    return result("pass", "every bin passed")


def rounds_check(kind: str, ceiling: float, rounds: list[dict], *, option: str | None = None) -> dict:
    """Cross-round error control. kind 'threshold': rounds [{alpha, level, fresh}] with option 'allocation' (a) or 'cap'
    (b); kind 'compatibility': rounds [{p_unfav, alpha, tolerance}], never splitting alpha nor widening the tolerance.
    Returns {"overall": implied rate, "within_ceiling": bool}; raises RuleError on a malformed or splitting plan."""
    if not _prob(ceiling) or not isinstance(rounds, list) or not rounds:
        raise RuleError("a ceiling in (0, 1) and at least one round")
    if kind == "threshold":
        if any(not _prob(r.get("alpha")) for r in rounds):
            raise RuleError("each round has alpha in (0, 1)")
        if option == "allocation":
            if any(not _num(r.get("level")) or abs(r["level"] - (1 - r["alpha"])) > 1e-12 for r in rounds):
                raise RuleError("under allocation each round's one-sided interval level is 1 - alpha_r")
            overall = sum(r["alpha"] for r in rounds)
        elif option == "cap":
            alpha = rounds[0]["alpha"]
            if any(r["alpha"] != alpha for r in rounds):
                raise RuleError("under a cap every round uses the same alpha")
            n = len(rounds)
            overall = 1 - (1 - alpha) ** n if all(r.get("fresh") is True for r in rounds) else min(1.0, n * alpha)
        else:
            raise RuleError("option is allocation or cap")
    elif kind == "compatibility":
        first = rounds[0]
        for r in rounds:
            if not _prob(r.get("p_unfav")) or not _prob(r.get("alpha")) or not _num(r.get("tolerance")):
                raise RuleError("each round has p_unfav and alpha in (0, 1) and a tolerance")
            if r["alpha"] < first["alpha"] or r["tolerance"] > first["tolerance"]:
                raise RuleError("a later round may not split alpha or widen the tolerance")
        overall = sum(r["p_unfav"] for r in rounds)
    else:
        raise RuleError("kind is threshold or compatibility")
    return {"overall": overall, "within_ceiling": overall <= ceiling + 1e-12}


def rule_of_three(n: int) -> float:
    """95% CL upper limit on a rate when 0 events are seen in n (about 3/n)."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise RuleError("n >= 1")
    return 1 - 0.05 ** (1 / n)


FREEZE_KEYS = {"step", "validation_identity", "criteria_version", "confirmation_samples", "independent_samples",
               "controls", "report_all_confirmations", "feasibility", "multiple_testing", "cross_round", "checks",
               "power", "created"}
CHECK_KEYS = {"check_digest", "criterion_digest", "role", "type", "rule"}


def freeze_problems(rec) -> list[str]:
    """Problems of one freeze record (empty list = conforms). The record is frozen before the results it judges."""
    if not isinstance(rec, dict):
        return ["a freeze record is a JSON object"]
    p = []
    missing, extra = FREEZE_KEYS - set(rec), set(rec) - FREEZE_KEYS
    if missing:
        p.append(f"missing fields {sorted(missing)}")
    if extra:
        p.append(f"unknown fields {sorted(extra)}")
    if p:
        return p
    if not isinstance(rec["step"], str) or not rec["step"]:
        p.append("step is a step name")
    vid = rec["validation_identity"]
    if not isinstance(vid, list) or not vid or not all(isinstance(x, list) and len(x) == 2 and all(map(_hex64, x))
                                                       for x in vid):
        p.append("validation_identity is a non-empty list of [check digest, criterion digest]")
    if not isinstance(rec["criteria_version"], str) or not rec["criteria_version"]:
        p.append("criteria_version is a string")
    cs, ind = rec["confirmation_samples"], rec["independent_samples"]
    if not isinstance(cs, list) or not all(isinstance(s, str) for s in cs) or len(set(cs)) != len(cs):
        p.append("confirmation_samples is a list of distinct sample names")
    elif not isinstance(ind, list) or not set(ind) <= set(cs):
        p.append("independent_samples lists only confirmation samples")
    if not isinstance(rec["controls"], list) or not all(isinstance(s, str) for s in rec["controls"]):
        p.append("controls is a list of names")
    if rec["report_all_confirmations"] is not True:
        p.append("the commitment to report every confirmation result is required")
    fz = rec["feasibility"]
    if not isinstance(fz, dict) or not isinstance(fz.get("independent_feasible"), bool) or \
            not isinstance(fz.get("reason"), str) or not fz.get("reason"):
        p.append("feasibility states independent_feasible (boolean) and a reason")
    elif fz["independent_feasible"] is False and not fz.get("conditions"):
        p.append("an infeasible independent confirmation states under which conditions it would be feasible")
    mt = rec["multiple_testing"]
    if not isinstance(mt, dict) or mt.get("error_type") not in ("false-pass", "false-fail") or \
            mt.get("combination") not in ("all-pass", "any-fail", "global-statistic") or \
            not isinstance(mt.get("correlations"), str) or not mt.get("correlations"):
        p.append("multiple_testing states error_type, combination and the treatment of correlations")
    cr = rec["cross_round"]
    if not isinstance(cr, dict) or cr.get("kind") not in ("threshold", "compatibility") or not _prob(cr.get("ceiling")):
        p.append("cross_round states kind (threshold or compatibility) and a ceiling in (0, 1)")
    elif cr["kind"] == "threshold" and cr.get("option") not in ("allocation", "cap"):
        p.append("threshold cross_round option is allocation or cap")
    pw = rec["power"]
    if not isinstance(pw, dict) or not _prob(pw.get("min_pass_favourable", DEFAULT_POWER["min_pass_favourable"])) \
            or not isinstance(pw.get("alternative"), str) or not pw.get("alternative") \
            or not isinstance(pw.get("evaluated_on_combined_rule"), bool):
        p.append("power states the declared alternative, the targets and whether they are evaluated on the combined rule")
    elif pw["evaluated_on_combined_rule"] is not True:
        p.append("the power target is evaluated on the combined decision rule actually used")
    checks = rec["checks"]
    if not isinstance(checks, list) or not checks:
        p.append("checks is a non-empty list")
        checks = []
    pairs = []
    for i, c in enumerate(checks):
        if not isinstance(c, dict) or set(c) != CHECK_KEYS:
            p.append(f"checks[{i}] has exactly {sorted(CHECK_KEYS)}")
            continue
        pairs.append([c["check_digest"], c["criterion_digest"]])
        if c["role"] not in ROLES or c["type"] not in TYPES:
            p.append(f"checks[{i}] role in {ROLES} and type in {TYPES}")
        r = c["rule"] if isinstance(c["rule"], dict) else {}
        if c["type"] == "threshold":
            if not r.get("basis") or r.get("interval") not in ("one-sided", "two-sided") or \
                    not _prob(r.get("level")) or not r.get("systematics"):
                p.append(f"checks[{i}] threshold rule states basis, interval form, level and systematics")
        elif c["type"] == "performance-estimate":
            ok = all(_num(r.get(k)) and r.get(k) >= 0 for k in ("k", "delta_phys", "claimed_total"))
            if not ok or not r.get("method"):
                p.append(f"checks[{i}] performance rule states method, k, delta_phys and claimed_total")
            elif r.get("sigma_stat") is not None and tolerance(r["k"], r["sigma_stat"], r["delta_phys"]) > r["claimed_total"]:
                p.append(f"checks[{i}] tolerance exceeds the claimed total uncertainty")
        if c["role"] == "confirmation-independent" and not ind:
            p.append(f"checks[{i}] is a method-independent confirmation but no independent sample is frozen")
    if isinstance(vid, list) and sorted(map(tuple, pairs)) != sorted(map(tuple, (x for x in vid if isinstance(x, list)))):
        p.append("the checks are exactly the effective validation identity")
    if not isinstance(rec["created"], str) or not rec["created"]:
        p.append("created is a timestamp string")
    return p


def append_line(log: Path, rec: dict) -> dict:
    """Append a validated freeze record to an append-only JSON-lines log with a digest chain (DEC-03 default)."""
    probs = freeze_problems(rec)
    if probs:
        raise RuleError("; ".join(probs))
    lines = log.read_bytes().splitlines() if log.is_file() else []
    prev = hashlib.sha256(lines[-1]).hexdigest() if lines else None
    line = {"seq": len(lines) + 1, "prev_sha256": prev, "freeze": rec}
    with log.open("ab") as fh:
        fh.write(canonical(line) + b"\n")
    return line


def verify_chain(log: Path) -> list[str]:
    problems, prev = [], None
    for i, raw in enumerate(log.read_bytes().splitlines(), 1):
        try:
            line = json.loads(raw)
        except ValueError:
            return problems + [f"line {i} is not JSON"]
        if line.get("seq") != i or line.get("prev_sha256") != prev:
            problems.append(f"line {i}: sequence or previous digest broken")
        if raw != canonical(line):
            problems.append(f"line {i}: not in canonical form")
        problems += [f"line {i}: {x}" for x in freeze_problems(line.get("freeze"))]
        prev = hashlib.sha256(raw).hexdigest()
    return problems


def decide(spec: dict) -> dict:
    rule = spec.get("rule")
    if rule == "threshold":
        return threshold_decision(tuple(spec["interval"]), tuple(spec["region"]), power_met=spec["power_met"])
    if rule == "tolerance":
        return tolerance_decision(spec["deviation"], spec["deviation_sigma"], k=spec["k"], sigma_stat=spec["sigma_stat"],
                                  delta_phys=spec["delta_phys"], claimed_total=spec["claimed_total"],
                                  check_precision=spec["check_precision"])
    if rule == "combine":
        return combine(spec["results"], inconclusive_as=spec.get("inconclusive_as", "not-passed"))
    if rule == "rounds":
        return rounds_check(spec["kind"], spec["ceiling"], spec["rounds"], option=spec.get("option"))
    raise RuleError("rule is threshold, tolerance, combine or rounds")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate-freeze", "decide", "verify-chain"):
        sub.add_parser(name).add_argument("file", type=Path)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "verify-chain":
            probs = verify_chain(args.file)
            out = {"status": "refused" if probs else "ok", "problems": probs}
        else:
            doc = json.loads(args.file.read_text(encoding="utf-8"))
            if args.cmd == "validate-freeze":
                probs = freeze_problems(doc)
                out = {"status": "refused" if probs else "ok", "problems": probs}
            else:
                out = {"status": "ok", "decision": decide(doc)}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        status = "refused" if isinstance(exc, RuleError) else "rejected"
        out = {"status": status, "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(out, indent=1, sort_keys=True))
    return exit_code(out["status"])


if __name__ == "__main__":
    sys.exit(main())
