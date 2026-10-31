#!/usr/bin/env python3
"""Running of the strong coupling alpha_s in MS-bar at 1-4 loops, with matching at the heavy-quark thresholds (Th10).

Purpose: alpha_s at the scales of a prediction from a stated alpha_s(m_Z), with the order, the scheme, the flavour
thresholds and the input's source recorded. See <plugin root>/skills/hep-theory/references/particle-physics-essentials.md.

Method:
- the renormalization group equation mu^2 d alpha_s / d mu^2 = -(b0 alpha_s^2 + b1 alpha_s^3 + b2 alpha_s^4 +
  b3 alpha_s^5), integrated numerically (fourth-order Runge-Kutta in ln mu^2) at fixed nf between thresholds;
- b0 = (33 - 2 nf)/(12 pi), b1 = (153 - 19 nf)/(24 pi^2), b2 = (2857 - 5033 nf/9 + 325 nf^2/27)/(128 pi^3) (PDG Review
  2026, QCD, Eq. 9.3); b3 = beta3 / (4 pi)^4 with beta3 = 149753/6 + 3564 zeta3 - (1078361/162 + 6508 zeta3/27) nf +
  (50065/162 + 6472 zeta3/81) nf^2 + 1093 nf^3/729 (van Ritbergen, Vermaseren, Larin, Phys. Lett. B 400 (1997) 379,
  Eq. 11; the PDG review's Ref. [12]); b2 and b3 are MS-bar;
- at mu_th = factor x m_h the coupling of nf + 1 flavours is alpha(nf) (1 + c11 alpha L + (c22 L^2 + c21 L + c20)
  alpha^2) with L = ln(mu_th^2 / m_h^2), c11 = 1/(6 pi), c10 = 0, c22 = c11^2, c21 = 11/(24 pi^2), and c20 =
  -11/(72 pi^2) for an MS-bar mass m_h(m_h) or 7/(24 pi^2) for a pole mass (Eq. 9.4); downward it is inverted exactly.
  Matching order: none at 1 loop, alpha^1 at 2 loops, alpha^2 at 3 and 4 loops (the three-loop c3 terms are not
  included: a stated truncation).
Assumptions and validity: perturbative QCD; the run stops where alpha_s exceeds 0.5 (status incomplete, exit 3), since
the perturbative expansion is not trustworthy there. nf at the starting scale counts the thresholds below it (or
--nf-start). No built-in quark masses or alpha_s: the user gives them; m_Z defaults to the PDG 2026 value of
core/constants, recorded with its edition.
Usage: running_coupling.py --alphas-mz A --alphas-source TEXT --loops {1,2,3,4} --mc M --mb M --mt M
         --mass-scheme {msbar,pole} --to Q [Q ...] [--mz GEV] [--threshold-factor 1] [--status LABEL]
Output JSON: status, status_label, inputs, defaults_used, conventions, mz (value, source, edition), points
[{scale_gev, alpha_s, nf, thresholds_crossed}], warnings, label [General method].
Exit codes: 0 ok; 2 bad input; 3 stopped where alpha_s > 0.5 (incomplete). Standard library only.
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
from core import constants  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

ZETA3 = 1.2020569031595942853997381615114499907649862923405
ALPHA_MAX = 0.5
LABEL = "[General method]"
FLAVOURS = ("c", "b", "t")


class CouplingError(ValueError):
    """An input outside the domain of the calculation."""


def beta_coefficients(nf: int, loops: int) -> list[float]:
    """[b0, ..., b_{loops-1}] in the normalization mu^2 d alpha / d mu^2 = -sum b_i alpha^(i+2)."""
    if loops not in (1, 2, 3, 4):
        raise CouplingError("loops must be 1, 2, 3 or 4")
    pi = math.pi
    b = [(33 - 2 * nf) / (12 * pi), (153 - 19 * nf) / (24 * pi ** 2),
         (2857 - 5033 / 9 * nf + 325 / 27 * nf ** 2) / (128 * pi ** 3)]
    beta3 = (149753 / 6 + 3564 * ZETA3 - (1078361 / 162 + 6508 / 27 * ZETA3) * nf
             + (50065 / 162 + 6472 / 81 * ZETA3) * nf ** 2 + 1093 / 729 * nf ** 3)
    b.append(beta3 / (4 * pi) ** 4)
    return b[:loops]


def _deriv(a: float, b: list[float]) -> float:
    return -sum(bi * a ** (i + 2) for i, bi in enumerate(b))


def run_fixed_nf(alpha: float, mu0: float, mu1: float, nf: int, loops: int) -> float:
    """alpha_s(mu1) from alpha_s(mu0) at fixed nf (RK4 in t = ln mu^2); raises CouplingError above ALPHA_MAX."""
    b = beta_coefficients(nf, loops)
    t0, t1 = math.log(mu0 ** 2), math.log(mu1 ** 2)
    n = max(400, math.ceil(abs(t1 - t0) * 400))
    h = (t1 - t0) / n
    a = alpha
    for _ in range(n):
        k1 = _deriv(a, b)
        k2 = _deriv(a + 0.5 * h * k1, b)
        k3 = _deriv(a + 0.5 * h * k2, b)
        k4 = _deriv(a + h * k3, b)
        a += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        if not math.isfinite(a) or a > ALPHA_MAX or a <= 0:
            raise CouplingError(f"alpha_s exceeds {ALPHA_MAX} between {mu0:g} and {mu1:g} GeV (nf = {nf})")
    return a


def _factor(a: float, L: float, order: int, scheme: str) -> float:
    pi = math.pi
    c11 = 1 / (6 * pi)
    c20 = -11 / (72 * pi ** 2) if scheme == "msbar" else 7 / (24 * pi ** 2)
    f = 1.0
    if order >= 1:
        f += c11 * a * L  # c10 = 0
    if order >= 2:
        f += (c11 ** 2 * L ** 2 + 11 / (24 * pi ** 2) * L + c20) * a ** 2
    return f


def match(alpha: float, mu: float, m_h: float, up: bool, order: int, scheme: str) -> float:
    """Eq. (9.4): alpha(nf+1) = alpha(nf) x factor(alpha(nf)); downward, solved for alpha(nf)."""
    if scheme not in ("msbar", "pole"):
        raise CouplingError("mass scheme must be msbar or pole")
    L = math.log(mu ** 2 / m_h ** 2)
    if up:
        return alpha * _factor(alpha, L, order, scheme)
    a = alpha
    for _ in range(100):
        new = alpha / _factor(a, L, order, scheme)
        if abs(new - a) < 1e-17:
            break
        a = new
    return a


def evolve(alpha0: float, mu0: float, targets: list[float], loops: int, thresholds: dict, scheme: str,
           factor: float = 1.0, nf_start: int | None = None) -> dict:
    """alpha_s at each target scale from alpha0 at mu0; stops at the first target the run cannot reach."""
    for name, v in (("alpha_s", alpha0), ("scale", mu0), ("threshold factor", factor)):
        if not math.isfinite(v) or v <= 0:
            raise CouplingError(f"{name} must be > 0")
    if alpha0 > ALPHA_MAX:
        raise CouplingError(f"alpha_s input above {ALPHA_MAX}")
    beta_coefficients(3, loops)  # validates loops
    if sorted(thresholds) != sorted(FLAVOURS):
        raise CouplingError("give the c, b and t masses")
    masses = [thresholds[q] for q in FLAVOURS]
    if not all(math.isfinite(m) and m > 0 for m in masses) or not masses[0] < masses[1] < masses[2]:
        raise CouplingError("quark masses must be > 0 with m_c < m_b < m_t")
    mu_th = [factor * m for m in masses]
    order = {1: 0, 2: 1, 3: 2, 4: 2}[loops]

    def nf_at(mu):
        return 3 + sum(1 for x in mu_th if x < mu)

    nf0 = nf_at(mu0) if nf_start is None else nf_start
    points, stopped = [], None
    for q in targets:
        if not math.isfinite(q) or q <= 0:
            raise CouplingError("target scales must be > 0")
        a, mu, nf, crossed = alpha0, mu0, nf0, []
        try:
            while True:
                up = q > mu
                nxt = [(x, i) for i, x in enumerate(mu_th) if (mu < x < q if up else q < x < mu)]
                if not nxt:
                    a = run_fixed_nf(a, mu, q, nf, loops)
                    break
                x, i = min(nxt) if up else max(nxt)
                a = run_fixed_nf(a, mu, x, nf, loops)
                a = match(a, x, masses[i], up=up, order=order, scheme=scheme)
                nf += 1 if up else -1
                crossed.append({"quark": FLAVOURS[i], "scale_gev": x, "direction": "up" if up else "down"})
                mu = x
                if a > ALPHA_MAX:
                    raise CouplingError(f"alpha_s exceeds {ALPHA_MAX} at the {FLAVOURS[i]} threshold")
        except CouplingError as exc:
            if "exceeds" not in str(exc):
                raise
            stopped = f"{exc}; stopped before {q:g} GeV (alpha_s > {ALPHA_MAX}: outside perturbative QCD)"
            break
        points.append({"scale_gev": q, "alpha_s": a, "nf": nf, "thresholds_crossed": crossed})
    return {"status": "incomplete" if stopped else "ok", "points": points, "stopped": stopped,
            "matching_order": order}


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--alphas-mz", type=float, required=True, help="alpha_s(m_Z) in MS-bar, nf = 5")
    ap.add_argument("--alphas-source", required=True, help="where the input comes from (paper, PDG edition)")
    ap.add_argument("--mz", type=float, help="m_Z in GeV (default: PDG 2026 from core/constants)")
    ap.add_argument("--loops", type=int, required=True)
    for q in FLAVOURS:
        ap.add_argument(f"--m{q}", type=float, required=True, help=f"m_{q} in GeV, in --mass-scheme")
    ap.add_argument("--mass-scheme", choices=("msbar", "pole"), required=True,
                    help="msbar: m_h(m_h); pole: pole masses (changes c20 of the matching)")
    ap.add_argument("--threshold-factor", type=float, default=1.0, help="mu_th = factor x m_h (default 1)")
    ap.add_argument("--to", type=float, nargs="+", required=True, help="target scales in GeV")
    add_status_argument(ap)
    a = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    defaults = [k for k in ("mz", "threshold_factor", "status") if "--" + k.replace("_", "-") not in given]
    base = {"status_label": a.status, "inputs": inputs, "defaults_used": defaults}
    if not a.mb < (a.mz or 91.0) < a.mt * a.threshold_factor or not a.mb * a.threshold_factor < (a.mz or 91.0):
        print(json.dumps({"status": "rejected", **base, "error": "alpha_s(m_Z) is an nf = 5 input: the b threshold must lie "
                                                                 "below m_Z and the t threshold above"}, indent=1))
        return exit_code("rejected")
    if a.mz is None:
        q = constants.particle("Z", "mass", unit="GeV")
        mz = {"value": q.value, "source": q.source, "edition": q.edition}
    else:
        mz = {"value": a.mz, "source": "user", "edition": "user"}
    try:
        r = evolve(a.alphas_mz, mz["value"], a.to, a.loops, {"c": a.mc, "b": a.mb, "t": a.mt}, a.mass_scheme,
                   a.threshold_factor, nf_start=5)
    except CouplingError as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    conventions = {
        "scheme": "MS-bar", "loops": a.loops, "input": f"alpha_s(m_Z) = {a.alphas_mz} (nf = 5), source: {a.alphas_source}",
        "beta": "PDG Review 2026 QCD Eq. 9.3 (b0-b2); b3 from van Ritbergen, Vermaseren, Larin (1997) Eq. 11",
        "matching": (f"Eq. 9.4 at mu_th = {a.threshold_factor} x m_h, order alpha_s^{r['matching_order']} "
                     f"({a.mass_scheme} masses); three-loop matching terms not included"),
        "stop": f"the run stops where alpha_s > {ALPHA_MAX}",
    }
    warnings = [r["stopped"]] if r["stopped"] else []
    print(json.dumps({"status": r["status"], **base, "label": LABEL, "conventions": conventions, "mz": mz,
                      "points": r["points"], "warnings": warnings}, indent=1))
    return exit_code(r["status"])


if __name__ == "__main__":
    sys.exit(main())
