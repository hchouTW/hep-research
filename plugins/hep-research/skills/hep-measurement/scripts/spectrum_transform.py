#!/usr/bin/env python3
"""Spectral-variable transformation of a bin-averaged flux with an isotope-composition model (M7).

Purpose: turn an element's bin-averaged differential flux in one variable (for example rigidity) into the bin-averaged
flux in another (for example kinetic energy per nucleon) by the Jacobian and bin averaging, never by relabeling the
bin edges. When the element has several isotopes, each isotope maps the variables differently (A and mass differ),
so the result depends on the isotope composition; its uncertainty is propagated as a separate covariance.

Method: the source flux Phi(x) is known as bin averages. The target bin [y1, y2] receives
    Phi_y = (1 / (y2 - y1)) * sum_i  integral over x_i(y1)..x_i(y2) of f_i(x) Phi(x) dx,
where x_i(y) maps the target variable back to the source variable for isotope i (core/kinematics/relativistic.py) and
f_i(x) is the isotope fraction at the same source-variable value. With one isotope and no --to-edges the target edges
are the mapped source edges and the result is exact: Phi_y = Phi_x * (x2 - x1) / (y2 - y1). Otherwise a within-bin
shape must be declared: `constant` (Phi constant in each source bin) or `powerlaw` (Phi = c x^-g in each source bin,
with c fixed by the bin integral and g the local log-slope between neighbouring bin averages; exact for a pure power
law on log-uniform bins). Statistical covariance: Cov_y = J C J^T with the Jacobian J of the transform (numerical,
central differences, for the power-law shape). Composition covariance: one nuisance per isotope fraction with a stated
uncertainty; shifting fraction i rescales the other fractions to keep the sum at 1; nuisances are independent.

Assumptions and validity: fractions are defined at equal source-variable value; a target bin must map inside the
source range for every isotope (no extrapolation); nuclear masses come from core/constants (AME2020 atomic mass x
m_u c^2 - Z m_e c^2, CODATA 2022) or from a stated `mass_gev` with its `mass_source`. No default Z, A, mass,
composition or shape.

Input JSON: {"variable": "rigidity", "unit": "GV" (optional), "edges": [...], "values": [...],
             "covariance": [[...]] (optional) or "uncertainties": [...] (optional), "Z": 2,
             "composition": {"kind": "fixed", "isotopes": [{"A": 3, "fraction": 0.2, "fraction_uncertainty": 0.03},
                                                         {"A": 4, "fraction": 0.8}]}
                          | {"kind": "table", "x": [...], "isotopes": [{"A": 3, "fractions": [...],
                                                                       "fraction_uncertainty": 0.03}, ...]}
                          | {"kind": "plugin", "path": "fractions.py"}   (needs --allow-plugin; the module defines
                            fractions(x) -> {A: fraction}; the path is read relative to the input file)}
  Isotope entries may carry "mass_gev" and "mass_source". Variables: rigidity, momentum, total_energy,
  kinetic_energy, kinetic_energy_per_nucleon (units GV, GeV/c, GeV, GeV, GeV/n).
Output JSON: "status" (run status, core/status.py), "status_label" (--status, default unvalidated), "inputs",
"defaults_used", "variable", "edges", "values", "covariance" (statistical, when given), "composition_covariance",
"total_covariance", "within_bin_shape", "transformation_record" (variables, Z, isotopes with masses and their
sources, composition kind, shape, sha256 of the input) for the comparison gate, "warnings", "label".
Exit codes: 0 ok; 1 a composition plugin failed; 2 bad input (missing Z, A, mass or composition, fractions not
summing to 1, a target bin outside the source range, a needed shape not declared, a plugin without --allow-plugin).
Run: python3 <plugin root>/skills/hep-measurement/scripts/spectrum_transform.py flux.json --to kinetic_energy_per_nucleon
     python3 <plugin root>/skills/hep-measurement/scripts/spectrum_transform.py flux.json --to kinetic_energy_per_nucleon \\
         --to-edges 0.5 1 2 5 10 --within-bin-shape powerlaw
Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core import constants  # noqa: E402
from core.kinematics.relativistic import UNITS, VARIABLES, KinematicsError, Species, check_unit, convert  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
SUM_TOL = 1e-9
RANGE_TOL = 1e-12
GL_NODES = (  # 8-point Gauss-Legendre on [-1, 1]
    (-0.9602898564975363, 0.1012285362903763), (-0.7966664774136267, 0.2223810344533745),
    (-0.5255324099163290, 0.3137066458778873), (-0.1834346424956498, 0.3626837833783620),
    (0.1834346424956498, 0.3626837833783620), (0.5255324099163290, 0.3137066458778873),
    (0.7966664774136267, 0.2223810344533745), (0.9602898564975363, 0.1012285362903763))


class InputError(ValueError):
    """A refused input (exit 2)."""


class PluginError(RuntimeError):
    """A composition plugin that failed (exit 1)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _num(x, name):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise InputError(f"{name} must be a finite number")
    return float(x)


# ---------------------------------------------------------------- source flux and its within-bin shape

class SourceFlux:
    def __init__(self, edges, values, shape):
        self.e, self.v, self.shape = edges, values, shape
        self.n = len(values)
        self.g = self._indices() if shape == "powerlaw" else None

    def _indices(self):
        if any(v <= 0 for v in self.v) or self.e[0] <= 0:
            raise InputError("the power-law shape needs positive bin values and edges")
        if self.n == 1:
            raise InputError("the power-law shape needs at least two source bins")
        c = [math.sqrt(a * b) for a, b in zip(self.e, self.e[1:])]
        g = []
        for k in range(self.n):
            lo, hi = max(k - 1, 0), min(k + 1, self.n - 1)
            g.append(-math.log(self.v[hi] / self.v[lo]) / math.log(c[hi] / c[lo]))
        return g

    @staticmethod
    def _pl(a, b, g):
        if abs(g - 1.0) < 1e-12:
            return math.log(b / a)
        return (b ** (1 - g) - a ** (1 - g)) / (1 - g)

    def density(self, k, x):
        lo, hi = self.e[k], self.e[k + 1]
        if self.shape == "constant":
            return self.v[k]
        g = self.g[k]
        return self.v[k] * (hi - lo) / self._pl(lo, hi, g) * x ** (-g)

    def integral(self, a, b, k):
        """Integral of Phi over [a, b] inside source bin k."""
        lo, hi = self.e[k], self.e[k + 1]
        if self.shape == "constant":
            return self.v[k] * (b - a)
        g = self.g[k]
        return self.v[k] * (hi - lo) * self._pl(a, b, g) / self._pl(lo, hi, g)

    def pieces(self, a, b):
        """(lo, hi, k) sub-intervals of [a, b] by source bin."""
        out = []
        for k in range(self.n):
            lo, hi = max(a, self.e[k]), min(b, self.e[k + 1])
            if hi > lo:
                out.append((lo, hi, k))
        return out


# ---------------------------------------------------------------- composition

def _mass(z, iso):
    a = iso["A"]
    if "mass_gev" in iso:
        if not iso.get("mass_source"):
            raise InputError(f"isotope A={a}: a stated mass_gev needs its mass_source")
        return _num(iso["mass_gev"], "mass_gev"), str(iso["mass_source"])
    if (z, a) == (1, 1):
        return constants.constant("proton_mass_energy", unit="GeV").value, "CODATA 2022 proton mass (core/constants)"
    try:
        return constants.nuclear_mass_gev(z, a), ("AME2020 atomic mass x m_u c^2 - Z m_e c^2 with CODATA 2022 "
                                                  "(core/constants); electron binding neglected")
    except constants.ConstantsError as exc:
        raise InputError(f"no tabulated mass for Z={z}, A={a}: give mass_gev and mass_source ({exc})") from exc


class Composition:
    def __init__(self, doc, z, base: Path, allow_plugin: bool):
        if not isinstance(doc, dict) or doc.get("kind") not in ("fixed", "table", "plugin"):
            raise InputError("composition must be an object with kind fixed, table or plugin")
        self.kind = doc["kind"]
        self.plugin = None
        if self.kind == "plugin":
            if not allow_plugin:
                raise InputError("a composition plugin runs user code: pass --allow-plugin")
            path = (base / str(doc.get("path", ""))).resolve()
            if not path.is_file():
                raise InputError(f"composition plugin not found: {path}")
            spec = importlib.util.spec_from_file_location("hep_composition_plugin", path)
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
            except Exception as exc:  # user code
                raise PluginError(f"composition plugin failed to load: {exc}") from exc
            if not callable(getattr(mod, "fractions", None)):
                raise InputError("the composition plugin must define fractions(x) -> {A: fraction}")
            self.plugin = mod.fractions
            isotopes = [{"A": int(a)} for a in doc.get("isotopes_A", [])] or None
            if not isotopes:
                raise InputError("a plugin composition must list its isotopes in isotopes_A")
        else:
            isotopes = doc.get("isotopes")
            if not isinstance(isotopes, list) or not isotopes:
                raise InputError("composition.isotopes must be a non-empty list")
        self.iso = []
        for iso in isotopes:
            if "A" not in iso or isinstance(iso["A"], bool) or not isinstance(iso["A"], int) or iso["A"] < z:
                raise InputError(f"every isotope needs an integer mass number A >= Z ({iso})")
            mass, source = _mass(z, iso)
            unc = iso.get("fraction_uncertainty")
            self.iso.append({"A": iso["A"], "mass": mass, "mass_source": source,
                             "sigma": None if unc is None else _num(unc, "fraction_uncertainty"),
                             "raw": iso})
        if len({i["A"] for i in self.iso}) != len(self.iso):
            raise InputError("each isotope A may appear once")
        if self.kind == "fixed":
            for i in self.iso:
                i["f"] = _num(i["raw"].get("fraction"), f"fraction of A={i['A']}")
            if abs(sum(i["f"] for i in self.iso) - 1.0) > SUM_TOL:
                raise InputError(f"fractions sum to {sum(i['f'] for i in self.iso)}, not 1")
        elif self.kind == "table":
            xs = [_num(x, "composition.x") for x in doc.get("x", [])]
            if len(xs) < 2 or any(b <= a for a, b in zip(xs, xs[1:])):
                raise InputError("composition.x must be at least two increasing values")
            self.x = xs
            for i in self.iso:
                fr = i["raw"].get("fractions")
                if not isinstance(fr, list) or len(fr) != len(xs):
                    raise InputError(f"isotope A={i['A']}: fractions must have one value per composition.x")
                i["table"] = [_num(v, "fraction") for v in fr]
            for k in range(len(xs)):
                s = sum(i["table"][k] for i in self.iso)
                if abs(s - 1.0) > SUM_TOL:
                    raise InputError(f"fractions at x = {xs[k]} sum to {s}, not 1")

    @property
    def linear_in_x(self):
        return self.kind == "fixed"

    def nodes(self):
        return self.x if self.kind == "table" else []

    def fractions(self, x, shift=None):
        """{A: f} at x; shift = (index, delta) moves one fraction and rescales the others to keep the sum at 1."""
        if self.kind == "fixed":
            f = [i["f"] for i in self.iso]
        elif self.kind == "table":
            if not self.x[0] - RANGE_TOL * abs(self.x[0]) <= x <= self.x[-1] * (1 + RANGE_TOL):
                raise InputError(f"composition table does not cover x = {x}")
            j = max(0, min(len(self.x) - 2, next((k for k in range(len(self.x) - 1) if x <= self.x[k + 1]), 0)))
            t = (x - self.x[j]) / (self.x[j + 1] - self.x[j])
            f = [i["table"][j] + t * (i["table"][j + 1] - i["table"][j]) for i in self.iso]
        else:
            try:
                got = self.plugin(x)
                f = [float(got[i["A"]]) for i in self.iso]
            except Exception as exc:  # user code
                raise PluginError(f"composition plugin failed at x = {x}: {exc}") from exc
            if abs(sum(f) - 1.0) > SUM_TOL:
                raise PluginError(f"composition plugin fractions at x = {x} sum to {sum(f)}, not 1")
        if shift is not None:
            k, d = shift
            rest = 1.0 - f[k]
            f = [fk + d if j == k else fk * (rest - d) / rest for j, fk in enumerate(f)]
        return f


# ---------------------------------------------------------------- the transform

def transform(src: SourceFlux, comp: Composition, z, src_var, dst_var, target, shift=None):
    out = []
    for lo, hi in zip(target, target[1:]):
        total = 0.0
        for idx, iso in enumerate(comp.iso):
            sp = Species(Z=z, A=iso["A"], mass=iso["mass"])
            a, b = convert(lo, dst_var, src_var, sp), convert(hi, dst_var, src_var, sp)
            for plo, phi, k in src.pieces(a, b):
                if comp.linear_in_x:
                    total += comp.fractions(plo, shift)[idx] * src.integral(plo, phi, k)
                else:
                    cuts = [plo] + [x for x in comp.nodes() if plo < x < phi] + [phi]
                    for c0, c1 in zip(cuts, cuts[1:]):
                        mid, half = 0.5 * (c0 + c1), 0.5 * (c1 - c0)
                        for t, w in GL_NODES:
                            x = mid + half * t
                            total += w * half * comp.fractions(x, shift)[idx] * src.density(k, x)
        out.append(total / (hi - lo))
    return out


def check_range(src_edges, comp, z, src_var, dst_var, target):
    bad = []
    lo_src, hi_src = src_edges[0], src_edges[-1]
    for iso in comp.iso:
        sp = Species(Z=z, A=iso["A"], mass=iso["mass"])
        a, b = convert(target[0], dst_var, src_var, sp), convert(target[-1], dst_var, src_var, sp)
        if a < lo_src * (1 - RANGE_TOL) or b > hi_src * (1 + RANGE_TOL):
            bad.append({"A": iso["A"], "needs": [a, b], "source_range": [lo_src, hi_src]})
    if bad:
        raise InputError(f"target bins outside the source range (no extrapolation): {bad}")


def matmul_cov(jac, cov):
    m, n = len(jac), len(cov)
    jc = [[sum(jac[i][k] * cov[k][l] for k in range(n)) for l in range(n)] for i in range(m)]
    return [[sum(jc[i][l] * jac[j][l] for l in range(n)) for j in range(m)] for i in range(m)]


def run(doc, args, base: Path, raw: bytes):
    warnings = []
    src_var = doc.get("variable")
    if src_var not in VARIABLES or args.to not in VARIABLES:
        raise InputError(f"variables must be among {list(VARIABLES)}")
    try:
        check_unit(src_var, doc.get("unit"))
    except KinematicsError as exc:
        raise InputError(str(exc)) from exc
    if "Z" not in doc:
        raise InputError("Z (the element's charge number) is required: no default")
    z = doc["Z"]
    if isinstance(z, bool) or not isinstance(z, int) or z < 1:
        raise InputError("Z must be a positive integer")
    edges = [_num(e, "edge") for e in doc.get("edges", [])]
    values = [_num(v, "value") for v in doc.get("values", [])]
    if len(edges) < 2 or len(values) != len(edges) - 1 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise InputError("edges must increase strictly and values need one entry per bin")
    if edges[0] <= 0:
        raise InputError("edges must be positive")
    n = len(values)
    cov = doc.get("covariance")
    if cov is None and "uncertainties" in doc:
        u = [_num(x, "uncertainty") for x in doc["uncertainties"]]
        if len(u) != n:
            raise InputError("uncertainties need one entry per bin")
        cov = [[u[i] ** 2 if i == j else 0.0 for j in range(n)] for i in range(n)]
    if cov is not None:
        if len(cov) != n or any(len(r) != n for r in cov):
            raise InputError("covariance must be n x n")
        cov = [[_num(x, "covariance") for x in r] for r in cov]
    else:
        warnings.append("no statistical covariance given: only the composition covariance is reported")
    if "composition" not in doc:
        raise InputError("composition is required (fixed, table or plugin): no default")
    comp = Composition(doc["composition"], z, base, args.allow_plugin)

    exact = len(comp.iso) == 1 and not args.to_edges
    if exact:
        sp = Species(Z=z, A=comp.iso[0]["A"], mass=comp.iso[0]["mass"])
        target = [convert(e, src_var, args.to, sp) for e in edges]
        shape = "exact (mapped edges)"
        src = SourceFlux(edges, values, "constant")  # integrals over whole source bins: shape-free
    else:
        if not args.within_bin_shape:
            raise InputError("several isotopes or --to-edges need a declared --within-bin-shape (constant or "
                             "powerlaw): the transform integrates inside source bins")
        target = [_num(e, "--to-edges") for e in (args.to_edges or [])]
        if not target:
            raise InputError("several isotopes map the edges differently: give --to-edges")
        if len(target) < 2 or any(b <= a for a, b in zip(target, target[1:])):
            raise InputError("--to-edges must increase strictly")
        shape = args.within_bin_shape
        src = SourceFlux(edges, values, shape)
    check_range(edges, comp, z, src_var, args.to, target)
    y = transform(src, comp, z, src_var, args.to, target)
    m = len(y)

    out_cov = None
    if cov is not None:
        jac = [[0.0] * n for _ in range(m)]
        for k in range(n):
            h = 1e-6 * max(abs(values[k]), 1e-300)
            up, dn = list(values), list(values)
            up[k] += h
            dn[k] -= h
            if shape == "powerlaw" and dn[k] <= 0:
                dn[k] = values[k]
                h2 = h
            else:
                h2 = 2 * h
            yu = transform(SourceFlux(edges, up, src.shape), comp, z, src_var, args.to, target)
            yd = transform(SourceFlux(edges, dn, src.shape), comp, z, src_var, args.to, target)
            for i in range(m):
                jac[i][k] = (yu[i] - yd[i]) / h2
        out_cov = matmul_cov(jac, cov)

    comp_cov = [[0.0] * m for _ in range(m)]
    for idx, iso in enumerate(comp.iso):
        s = iso["sigma"]
        if not s:
            continue
        if len(comp.iso) == 1:
            raise InputError("a single isotope has fraction 1: no fraction uncertainty applies")
        d = 1e-4 * max(s, 1e-12)
        yu = transform(src, comp, z, src_var, args.to, target, (idx, d))
        yd = transform(src, comp, z, src_var, args.to, target, (idx, -d))
        g = [(a - b) / (2 * d) for a, b in zip(yu, yd)]
        for i in range(m):
            for j in range(m):
                comp_cov[i][j] += s * s * g[i] * g[j]
    total = [[comp_cov[i][j] + (out_cov[i][j] if out_cov else 0.0) for j in range(m)] for i in range(m)]
    if comp.kind == "plugin":
        warnings.append("plugin composition: no fraction uncertainty is propagated")
    record = {
        "from": {"variable": src_var, "unit": UNITS[src_var]}, "to": {"variable": args.to, "unit": UNITS[args.to]},
        "Z": z, "isotopes": [{"A": i["A"], "mass_gev": i["mass"], "mass_source": i["mass_source"],
                              "fraction_uncertainty": i["sigma"]} for i in comp.iso],
        "composition_kind": comp.kind, "within_bin_shape": shape,
        "fraction_convention": "fractions at equal source-variable value",
        "input_sha256": hashlib.sha256(raw).hexdigest(),
    }
    return {"variable": args.to, "unit": UNITS[args.to], "edges": target, "values": y, "covariance": out_cov,
            "composition_covariance": comp_cov, "total_covariance": total, "within_bin_shape": shape,
            "transformation_record": record, "warnings": warnings, "label": LABEL,
            "note": "bin-averaged flux by Jacobian and bin averaging, not a relabeling of the edges"}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="JSON flux in the source variable, with Z and the composition")
    ap.add_argument("--to", required=True, choices=VARIABLES, help="target variable")
    ap.add_argument("--to-edges", nargs="+", type=float, help="target bin edges (needed for several isotopes)")
    ap.add_argument("--within-bin-shape", choices=("constant", "powerlaw"),
                    help="shape of the flux inside a source bin; required unless one isotope and mapped edges")
    ap.add_argument("--allow-plugin", action="store_true", help="allow a composition plugin (runs user code)")
    ap.add_argument("--out", help="also write the JSON result to this path")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    defaults = [k for k in ("status", "within_bin_shape", "to_edges")
                if f"--{k.replace('_', '-')}" not in given]
    status, body = "ok", {}
    try:
        path = Path(args.input)
        raw = path.read_bytes()
        doc = json.loads(raw)
        if not isinstance(doc, dict):
            raise InputError("the input must be a JSON object")
        body = run(doc, args, path.resolve().parent, raw)
    except OSError as exc:
        status, body = "rejected", {"error": f"cannot read {args.input}: {exc}"}
    except (InputError, KinematicsError, ValueError) as exc:
        status, body = "rejected", {"error": str(exc)}
    except PluginError as exc:
        status, body = "failed", {"error": str(exc)}
    result = {"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults, **body}
    text = json.dumps(result, indent=1)
    if status != "ok":
        print(f"spectrum_transform.py: error: {body['error']}", file=sys.stderr)
    if args.out and status == "ok":
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
