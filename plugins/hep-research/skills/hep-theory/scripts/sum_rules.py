#!/usr/bin/env python3
"""Numerical sum-rule integrals of tabulated parton distributions, with a convergence report and the contributions
outside the tabulated x range kept separate (Th14).

Purpose: check a PDF table (or a toy) against the sum rules it must satisfy, or report the integral a sum rule
constrains. See <plugin root>/skills/hep-theory/references/dis-structure-functions.md, "Sum rules".
Rules (--rule), with the integrand built from the table:
  momentum      int_0^1 x [sum_q (q + qbar) + g] dx          (needs every quark and antiquark flavour and g)
  number:<q>    int_0^1 (q - qbar) dx for q in d, u, s, c, b  (proton: u 2, d 1, s c b 0 by its quantum numbers)
  adler-lo      int_0^1 (F_2^{W-} - F_2^{W+}) / x dx = 2 int [(u - ubar) - (d - dbar) - (s - sbar) + (c - cbar)] dx
  gls-lo        (1/2) int_0^1 (F_3^{W+} + F_3^{W-}) dx = int sum_{q=u,d,s,c} (q - qbar) dx
  g1-moment:p|n int_0^1 g_1 dx with g_1 = (1/2) sum_q e_q^2 (Dq + Dqbar) at LO, q = u, d, s (polarized columns Du, Dubar,
                Dd, Ddbar, Ds, Dsbar, optionally Dc, Dcbar, Db, Dbbar; neutron by isospin)
  bjorken-lo    int_0^1 (g_1^p - g_1^n) dx = (1/6) int [(Du + Dubar) - (Dd + Ddbar)] dx (LO; QCD corrections not
                included: the coefficient series is in Kuhn, Chen, Leader, arXiv:0812.3535, Eq. 89)
  ff-momentum   sum_h int_0^1 z D_i^h(z) dz for one parton i, hadron columns "h:<hadron>" on the grid "x" (= z); 1 when
                every hadron is included (PDG 2026 "Fragmentation Functions", Eq. 19.3), a bound otherwise
  gpd-integral:<F>  int_-1^1 F(x, xi, t) dx for F in H, E, Ht, Et, from columns "F+" (F(x) at x > 0) and "F-"
                (F(-x), the value at -x, stored at the same positive grid point x; with "xf" the columns hold x F(x) and
                x F(-x), both with the positive x) at one (xi, t) given as "xi" and "t" in the table: the form factors
                F_1, F_2, G_A, G_P (Ji, hep-ph/9603249v1, Eq. 18). The power-law extrapolation below the first grid
                point has no basis in the ERBL region |x| < xi: tabulate down to x = 0 there.
  gpd-ji        (1/2) int_-1^1 x [H + E] dx = J^q (PDG 2026 Eq. 18.41; Ji, Eqs. 13 and 19)
  ellis-jaffe:p|n  the g_1 moment and, from --gA and --a8, the Ellis-Jaffe value Gamma_1 = +-gA/12 + 5 a8/36 (Delta s = 0
                and SU(3) symmetry assumed: heuristic-argument), from their Eq. 43
adler-lo and gls-lo are the LO quark-parton forms built from PDG 2026 "Structure Functions" Eq. (18.19) (read
2026-10-23; derived here, analytic-derivation at LO); for a proton they give 2 and 3. QCD corrections to them are not
included and not stated. The script reports integrals; it ships no expected value: pass --expected (and --tolerance)
for a check.
Integration: the integrand h(x) is integrated in ln x with the trapezoid rule on the given grid (x_1 < ... < x_n in
(0, 1]); the convergence estimate is the difference to the same rule on every second point. Below x_1 the integrand is
extrapolated as a power law h ~ x^p through the first two points (integral h(x_1) x_1 / (p + 1), divergent if p <= -1);
above x_n < 1 as h ~ (1 - x)^q through the last two (integral h(x_n) (1 - x_n) / (q + 1)). Both extrapolations are
reported as separate objects and added only in "total_with_extrapolation"; their form is an assumption, not a result,
and the convergence estimate does not cover them.
Input JSON (--table FILE): {"representation": "xf" | "f", "x": [...], "<flavour>": [...], ...} with flavours from
d u s c b dbar ubar sbar cbar bbar g (helicity densities: the same names with a D prefix); "xf" means the columns hold
x f(x).
Output JSON: status, status_label, inputs, rule, integrand, outputs (tabulated_range, integral_in_range,
convergence_estimate, below_xmin, above_xmax, total_with_extrapolation), checks.
Exit codes (core/status.py): 0 ok; 1 failed (the total lies outside --expected +/- --tolerance); 3 incomplete (a check
was requested but the total it needs is undefined); 2 rejected (unreadable
or missing input, missing flavour, non-finite value, a grid not strictly increasing in (0, 1], fewer than 3 points).
Standard library only.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

QUARKS = ("d", "u", "s", "c", "b")
ALL = QUARKS + tuple(q + "bar" for q in QUARKS) + ("g",)
POL = tuple("D" + f for f in ALL)  # helicity densities Delta q, Delta qbar, Delta g
GPD = tuple(n + s for n in ("H", "E", "Ht", "Et") for s in ("+", "-"))  # GPD at x (+) and at -x (-), x > 0
SOURCE_LO = "LO quark-parton form from PDG 2026 'Structure Functions' Eq. (18.19), read 2026-10-23 (derived here)"


class RuleError(ValueError):
    """Input the integration cannot use (run status rejected, exit 2)."""


def load_table(path: str) -> tuple[list[float], dict, str]:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuleError(f"cannot read --table {path}: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("representation") not in ("xf", "f") or not isinstance(doc.get("x"), list):
        raise RuleError('--table must be {"representation": "xf" | "f", "x": [...], flavour: [...]}')
    xs = [_num("x", v) for v in doc["x"]]
    if len(xs) < 3:
        raise RuleError("need at least 3 grid points")
    if any(not 0 < v <= 1 for v in xs) or any(b <= a for a, b in zip(xs, xs[1:])):
        raise RuleError("x must be strictly increasing in (0, 1]")
    cols = {}
    for k in doc:
        if k.startswith("h:"):
            if not isinstance(doc[k], list) or len(doc[k]) != len(xs):
                raise RuleError(f"hadron column {k} must be a list as long as x")
            cols[k] = [_num(k, v) for v in doc[k]]
    for f in ALL + POL + GPD:
        if f in doc:
            col = doc[f]
            if not isinstance(col, list) or len(col) != len(xs):
                raise RuleError(f"column {f} must be a list as long as x")
            cols[f] = [_num(f, v) for v in col]
    return xs, cols, doc["representation"]


def _num(name, v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        raise RuleError(f"{name}: every value must be a finite number, got {v!r}")
    return float(v)


def integrand(rule: str, xs: list[float], cols: dict, rep: str) -> tuple[list[float], str]:
    """h(x) for the rule, from columns holding f (rep 'f') or x f (rep 'xf')."""
    def need(*fl):
        miss = [f for f in fl if f not in cols]
        if miss:
            raise RuleError(f"rule {rule} needs the columns {miss}")
    def f(name, i):  # number density f(x_i)
        return cols[name][i] / xs[i] if rep == "xf" else cols[name][i]
    n = len(xs)
    if rule == "momentum":
        need(*ALL)
        return [xs[i] * sum(f(k, i) for k in ALL) for i in range(n)], "x [sum_q (q + qbar) + g]"
    if rule.startswith("number:"):
        q = rule.split(":", 1)[1]
        if q not in QUARKS:
            raise RuleError(f"number:<q> takes q in {QUARKS}")
        need(q, q + "bar")
        return [f(q, i) - f(q + "bar", i) for i in range(n)], f"{q} - {q}bar"
    if rule == "adler-lo":
        need("u", "ubar", "d", "dbar", "s", "sbar", "c", "cbar")
        return [2.0 * ((f("u", i) - f("ubar", i)) - (f("d", i) - f("dbar", i)) - (f("s", i) - f("sbar", i))
                       + (f("c", i) - f("cbar", i))) for i in range(n)], \
            "(F_2^{W-} - F_2^{W+}) / x = 2[(u - ubar) - (d - dbar) - (s - sbar) + (c - cbar)] (LO)"
    if rule == "gls-lo":
        need("u", "ubar", "d", "dbar", "s", "sbar", "c", "cbar")
        return [sum(f(q, i) - f(q + "bar", i) for q in ("u", "d", "s", "c")) for i in range(n)], \
            "(F_3^{W+} + F_3^{W-}) / 2 = sum_{q=u,d,s,c} (q - qbar) (LO)"
    if rule.startswith("gpd-integral:"):
        name = rule.split(":", 1)[1]
        if name not in ("H", "E", "Ht", "Et"):
            raise RuleError("gpd-integral:<F> takes F in H, E, Ht, Et")
        need(name + "+", name + "-")
        return [f(name + "+", i) + f(name + "-", i) for i in range(n)], \
            f"{name}(x) + {name}(-x): int_-1^1 {name} dx (Ji, Eq. 18: F_1, F_2, G_A, G_P for H, E, Ht, Et)"
    if rule == "gpd-ji":
        need("H+", "H-", "E+", "E-")
        return [0.5 * xs[i] * ((f("H+", i) + f("E+", i)) - (f("H-", i) + f("E-", i))) for i in range(n)], \
            "(1/2) x [(H + E)(x) - (H + E)(-x)]: (1/2) int_-1^1 x (H + E) dx = J (PDG Eq. 18.41; Ji, Eqs. 13, 19)"
    if rule == "ff-momentum":
        hadrons = sorted(k for k in cols if k.startswith("h:"))
        if not hadrons:
            raise RuleError('ff-momentum needs hadron columns "h:<hadron>" holding D_i^h(z) ("f") or z D_i^h(z) ("xf") of one parton i')
        return [xs[i] * sum(f(h, i) for h in hadrons) for i in range(n)], \
            f"z sum_h D_i^h(z) over {', '.join(h[2:] for h in hadrons)} (PDG 2026 Fragmentation Functions Eq. 19.3)"
    if rule in ("g1-moment:p", "g1-moment:n", "bjorken-lo") or rule.startswith("ellis-jaffe:"):
        need("Du", "Dubar", "Dd", "Ddbar", "Ds", "Dsbar")
        def plus(q, i):
            if "D" + q not in cols and "D" + q + "bar" not in cols:
                return 0.0  # optional heavy flavours (c, b) absent: taken as zero, stated in the integrand text
            need("D" + q, "D" + q + "bar")
            return f("D" + q, i) + f("D" + q + "bar", i)
        def g1(i, target):
            up, dn = (plus("u", i), plus("d", i)) if target == "p" else (plus("d", i), plus("u", i))
            return 0.5 * (4 / 9 * (up + plus("c", i)) + 1 / 9 * (dn + plus("s", i) + plus("b", i)))
        if rule == "bjorken-lo":
            return [g1(i, "p") - g1(i, "n") for i in range(n)], \
                "g_1^p - g_1^n = (1/6)[(Du + Dubar) - (Dd + Ddbar)] (LO)"
        target = rule.split(":", 1)[1]
        if target not in ("p", "n"):
            raise RuleError("the target is p or n")
        return [g1(i, target) for i in range(n)], \
            f"g_1^{target} = (1/2) sum_q e_q^2 (Dq + Dqbar), q = u, d, s and c, b if given (LO; neutron by isospin)"
    raise RuleError(f"unknown rule {rule!r}")


def trapezoid_lnx(xs: list[float], h: list[float]) -> float:
    return sum(0.5 * (xs[i] * h[i] + xs[i + 1] * h[i + 1]) * math.log(xs[i + 1] / xs[i]) for i in range(len(xs) - 1))


def integrate(xs: list[float], h: list[float]) -> dict:
    full = trapezoid_lnx(xs, h)
    idx = list(range(0, len(xs), 2))
    if idx[-1] != len(xs) - 1:
        idx.append(len(xs) - 1)
    coarse = trapezoid_lnx([xs[i] for i in idx], [h[i] for i in idx])
    out = {"tabulated_range": [xs[0], xs[-1]], "integral_in_range": full, "convergence_estimate": abs(full - coarse),
           "convergence_method": "|trapezoid(all points) - trapezoid(every second point)| in ln x"}
    below = {"x_range": [0.0, xs[0]], "model": "power law h ~ x^p through the first two points"}
    if h[0] == 0 and h[1] == 0:
        below.update(p=None, integral=0.0)
    elif h[0] * h[1] <= 0:
        below.update(p=None, integral=None, note="a zero or a sign change at the lowest points: no power law; "
                                                 "not extrapolated")
    else:
        p = math.log(h[1] / h[0]) / math.log(xs[1] / xs[0])
        below.update(p=p, integral=(h[0] * xs[0] / (p + 1.0)) if p > -1 else None,
                     note=None if p > -1 else "p <= -1: the integral below x_1 diverges")
    out["below_xmin"] = below
    above = {"x_range": [xs[-1], 1.0], "model": "h ~ (1 - x)^q through the last two points"}
    if xs[-1] >= 1.0:
        above.update(q=None, integral=0.0)
    elif h[-1] == 0 and h[-2] == 0:
        above.update(q=None, integral=0.0)
    elif h[-1] * h[-2] <= 0:
        above.update(q=None, integral=None, note="a zero or a sign change at the highest points: not extrapolated")
    else:
        q = math.log(h[-1] / h[-2]) / math.log((1 - xs[-1]) / (1 - xs[-2]))
        above.update(q=q, integral=(h[-1] * (1 - xs[-1]) / (q + 1.0)) if q > -1 else None,
                     note=None if q > -1 else "q <= -1: not integrable at x = 1")
    out["above_xmax"] = above
    parts = [below["integral"], above["integral"]]
    out["total_with_extrapolation"] = None if None in parts else full + sum(parts)
    return out


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = input the tool cannot use."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--table", required=True, help="JSON table of f(x) or x f(x)")
    ap.add_argument("--rule", required=True, help="momentum | number:<q> | adler-lo | gls-lo | g1-moment:p|n | bjorken-lo | ellis-jaffe:p|n | ff-momentum | gpd-integral:<F> | gpd-ji")
    ap.add_argument("--expected", type=float, help="value to check the total against (the user's, with its source)")
    ap.add_argument("--tolerance", type=float, help="absolute tolerance of the check")
    ap.add_argument("--gA", type=float, help="ellis-jaffe: g_A (= a_3) with its source")
    ap.add_argument("--a8", type=float, help="ellis-jaffe: a_8 from hyperon beta decays, with its source")
    ap.add_argument("--check-on", choices=("in_range", "with_extrapolation"), default="with_extrapolation")
    add_status_argument(ap)
    a = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    base = {"status_label": a.status, "inputs": inputs}
    try:
        if (a.expected is None) != (a.tolerance is None):
            raise RuleError("--expected and --tolerance go together")
        if a.tolerance is not None and not (math.isfinite(a.tolerance) and a.tolerance > 0):
            raise RuleError("--tolerance must be > 0")
        xs, cols, rep = load_table(a.table)
        h, desc = integrand(a.rule, xs, cols, rep)
        out = integrate(xs, h)
        if not a.rule.startswith("ellis-jaffe:") and (a.gA is not None or a.a8 is not None):
            raise RuleError("--gA and --a8 belong to the ellis-jaffe rules")
        if a.rule.startswith("ellis-jaffe:"):
            if a.gA is None or a.a8 is None or not (math.isfinite(a.gA) and math.isfinite(a.a8)):
                raise RuleError("ellis-jaffe needs --gA and --a8 (inputs with their source)")
            sign = 1.0 if a.rule.endswith(":p") else -1.0
            # Gamma_1 = (1/9)(+-3/4 a3 + a8/4 + a0) (Kuhn, Chen, Leader Eq. 43, neutron by isospin) with a0 = a8 (Ds = 0)
            out["ellis_jaffe_prediction"] = sign * a.gA / 12.0 + 5.0 * a.a8 / 36.0
            out["ellis_jaffe_status"] = ("heuristic-argument: assumes Delta s + Delta sbar = 0 and SU(3) flavour symmetry "
                                         "for a8; contradicted by the measured Gamma_1^p (Kuhn, Chen, Leader, Sec. 2.1, Eqs. 47-49)")
    except RuleError as exc:
        print(json.dumps({"status": "rejected", **base, "reason": str(exc)}, indent=1))
        return exit_code("rejected")
    status, checks = "ok", []
    if a.expected is not None:
        value = out["integral_in_range"] if a.check_on == "in_range" else out["total_with_extrapolation"]
        if value is None:
            checks.append({"name": "sum_rule", "result": "not run: the extrapolated total is undefined"})
            status = "incomplete"  # a requested check that cannot run is not a pass
        else:
            dev = value - a.expected
            passed = abs(dev) <= a.tolerance
            checks.append({"name": "sum_rule", "result": "pass" if passed else "fail", "value": value,
                           "expected": a.expected, "deviation": dev, "tolerance": a.tolerance, "on": a.check_on})
            if not passed:
                status = "failed"
    print(json.dumps({"status": status, **base, "rule": a.rule, "integrand": desc,
                      "source": SOURCE_LO if a.rule in ("adler-lo", "gls-lo") else "definition of the integral",
                      "outputs": out, "checks": checks}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
