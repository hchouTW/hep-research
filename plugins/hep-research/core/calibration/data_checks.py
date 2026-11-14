"""The locking-stage and fit-point checks that `calib_data.py` owns (Part B sections 2.1, 9.2, 14; phase 2, WP4):
computed here, called by `calib_contract.py check` at the evaluation points and by `calib_fit.py` at the fit point
(section 17, "Locking-stage checks that need quantities produced by the model are added in phase 2").

- `resolution`: the representation resolution rho_i of a released value from the declared format, the magnitude taken
  as the largest within the predicted +-5 sigma_i^(0) window (section 2.1 "Rounding").
- `rounding_ratio`: max_u u^T R u / u^T C~(0) u with R = diag((rho_i / sigma_i^(0))^2), on N_d,c^perp when constraints
  are declared; <= 1/25 required; observables with sigma^(0) = 0 and rho = 0 are removed first, sigma^(0) = 0 with
  rho > 0 rejected; a direction with zero denominator and non-zero R gives infinity (section 2.1).
- `evaluation_points`: the Sobol scan points of P5 and all vertices of the theta prior box (a local maximization from
  the worst scan point when dim theta > 10), each with the nuisances nominal and at +-2 sigma one axis at a time (D36).
- `n_min_and_merging`, `n_exp_check`, `block_conversion`: the shape and count conditions, worst case over the points.
- `enclosure` and `constraint_check`: the data-side constraint check of section 9.2 with guaranteed enclosures (outward
  rounded interval arithmetic intersected with the mean-value form); a lineage step that divides by or takes the log of
  a box containing 0 is rejected at locking when the declared format admits such a box (D4, A8).
"""
from __future__ import annotations

from typing import Any

import math

import numpy as np

from . import likelihood as L

ROUNDING_BOUND = 1.0 / 25.0
N_MIN = 20
N_TOTAL_MIN = 10
BLOCK_MIN = 5


class CheckError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ------------------------------------------------------------------ resolution (section 2.1)
def unit(value: float, fmt: dict) -> float:
    """The last-digit unit of `value` in the declared format: float64 (0: double precision has no rounding issue),
    float32 (its ulp), fixed decimals (10^-decimals), significant digits (10^(floor(log10|v|) - digits + 1)),
    integer counts (0)."""
    kind = fmt.get("kind")
    v = abs(float(value))
    if kind in ("float64", "count"):
        return 0.0
    if kind == "float32":
        if v == 0:
            return float(np.finfo(np.float32).tiny)
        return float(np.spacing(np.float32(v)))
    if kind == "fixed":
        return 10.0 ** (-int(fmt["decimals"]))
    if kind == "significant":
        if v == 0:
            return 0.0
        return 10.0 ** (math.floor(math.log10(v)) - int(fmt["digits"]) + 1)
    raise CheckError("data.format", f"unknown representation format {kind!r}")


def resolution(mu: float, sigma0: float, fmt: dict) -> float:
    """rho_i: the largest last-digit unit within the predicted +-5 sigma_i^(0) window, so that rho is not
    underestimated near 0 or in a significant-digits format (section 2.1)."""
    if fmt.get("kind") in ("float64", "count"):
        return 0.0
    lo, hi = mu - 5 * sigma0, mu + 5 * sigma0
    m = max(abs(lo), abs(hi))
    return unit(m, fmt)


# ------------------------------------------------------------------ the rounding condition (section 2.1)
def rounding_ratio(C0: np.ndarray, rho: np.ndarray, sigma0: np.ndarray, constraints: list | None = None) -> dict:
    """The largest generalized eigenvalue of R against C~(0) on N_d,c^perp (standardized coordinates). Rows with
    sigma0 = rho = 0 are removed; sigma0 = 0 with rho > 0 is rejected (section 5.2)."""
    C0, rho, s = np.asarray(C0, float), np.asarray(rho, float), np.asarray(sigma0, float)
    bad = np.flatnonzero((s == 0) & (rho > 0))
    if bad.size:
        raise CheckError("data.sigma0_zero_rounded", f"observables {bad.tolist()} have sigma^(0) = 0 and rho > 0 "
                         "(section 5.2)")
    keep = np.flatnonzero(s > 0)
    C0, rho, s = C0[np.ix_(keep, keep)], rho[keep], s[keep]
    cons = [np.asarray(c, float)[keep] for c in (constraints or [])]
    Ct = C0 / np.outer(s, s)
    R = np.diag((rho / s) ** 2)
    U = L.complement_basis([s * c for c in cons if np.any(c)], s.size) if cons else np.eye(s.size)
    Cp, Rp = U.T @ Ct @ U, U.T @ R @ U
    w, V = np.linalg.eigh(0.5 * (Cp + Cp.T))
    tol = 1e-12 * max(w.max(), 1.0)
    null = V[:, w <= tol]
    if null.size and np.abs(null.T @ Rp @ null).max() > 1e-300:
        return {"ratio": math.inf, "passed": False}
    pos = V[:, w > tol] / np.sqrt(w[w > tol])
    lam = float(np.linalg.eigvalsh(pos.T @ Rp @ pos).max()) if pos.size else 0.0
    return {"ratio": lam, "passed": lam <= ROUNDING_BOUND * (1 + 1e-12)}


def evaluation_points(theta_box: list, scan_points: np.ndarray, nuisance_sigmas: dict, max_vertices_dim: int = 10):
    """The evaluation points of section 2.1: Sobol scan points and every vertex of the theta prior box (dim > 10: the
    scan only; the caller adds a local maximization from the worst point), each with nuisances nominal and at +-2
    sigma one axis at a time (D36). Returns a list of (theta, {nuisance: value})."""
    box = np.asarray(theta_box, float)
    d = box.shape[0]
    pts = [np.asarray(p, float) for p in scan_points]
    if d <= max_vertices_dim:
        for mask in range(2 ** d):
            pts.append(np.array([box[i, (mask >> i) & 1] for i in range(d)]))
    out: list = []
    for p in pts:
        out.append((p, {}))
        for nm, sg in nuisance_sigmas.items():
            out.append((p, {nm: 2 * sg}))
            out.append((p, {nm: -2 * sg}))
    return out


def worst_over_points(points, fn) -> dict:
    """fn(theta, nuisances) -> dict with `value` (larger is worse) and `passed`; the worst point decides."""
    worst: Any = None
    for th, nu in points:
        r = fn(th, nu)
        if worst is None or r["value"] > worst["value"]:
            worst = {**r, "theta": np.asarray(th).tolist(), "nuisances": nu}
    return worst


# ------------------------------------------------------------------ shapes, totals, block conversion (section 2.1)
def merge_adjacent(expected: np.ndarray, n_min: float = N_MIN) -> list:
    """The declared merging rule applied to the worst expectation over the points: repeatedly merge the bin with the
    smallest worst expected count with its smaller adjacent neighbour until every merged bin is >= n_min (fixed at
    locking; never from observed counts). Returns the groups of original bins."""
    groups = [[k] for k in range(len(expected))]
    e = [float(x) for x in expected]
    while len(groups) > 1 and min(e) < n_min:
        i = int(np.argmin(e))
        if i == 0:
            j = 1
        elif i == len(e) - 1:
            j = i - 1
        else:
            j = i - 1 if e[i - 1] <= e[i + 1] else i + 1
        a, b = min(i, j), max(i, j)
        groups[a] = groups[a] + groups[b]
        e[a] = e[a] + e[b]
        del groups[b], e[b]
    return groups


def n_min_and_merging(expected_by_point: np.ndarray, n_min: float = N_MIN, shared_events: bool = True) -> dict:
    """Expected count per bin >= n_min at every evaluation point, merging adjacent bins by the declared rule using the
    worst expectation per bin; a shape that must be a Gaussian summary statistic (shared events) and still fails
    after merging is rejected (no further merging, section 2.1)."""
    E = np.asarray(expected_by_point, float)
    worst = E.min(axis=0)
    groups = merge_adjacent(worst, n_min)
    merged = np.stack([E[:, g].sum(axis=1) for g in groups], axis=1)
    ok = bool(np.all(merged >= n_min))
    return {"groups": groups, "K": len(groups), "passed": ok or not shared_events,
            "finding": None if ok or not shared_events else "data.n_min", "worst": float(merged.min())}


def n_exp_check(totals_by_point) -> dict:
    """N_exp of an absolute-count validation shape: the minimum over the evaluation points >= 10 (section 2.1 (ii))."""
    m = float(np.min(totals_by_point))
    return {"N_exp_min": m, "passed": m >= N_TOTAL_MIN, "finding": None if m >= N_TOTAL_MIN else "data.n_exp"}


def block_conversion(counts_by_point=None, binomial_by_point=None) -> dict:
    """Conversion to a Gaussian summary statistic: expected count per bin >= 5, and n eps, n (1 - eps) >= 5, worst
    case over the points (section 2.1 "Block rules")."""
    ok = True
    if counts_by_point is not None and np.min(counts_by_point) < BLOCK_MIN:
        ok = False
    if binomial_by_point is not None:
        n, e = np.asarray(binomial_by_point, float).T
        if np.min(n * e) < BLOCK_MIN or np.min(n * (1 - e)) < BLOCK_MIN:
            ok = False
    return {"passed": ok, "finding": None if ok else "data.block_conversion"}


# ------------------------------------------------------------------ guaranteed enclosures (section 9.2, D4)
class Box:
    """A closed interval with outward rounding."""

    __slots__ = ("lo", "hi")

    def __init__(self, lo, hi=None):
        hi = lo if hi is None else hi
        self.lo, self.hi = float(lo), float(hi)

    @staticmethod
    def _out(lo, hi):
        return Box(np.nextafter(lo, -np.inf), np.nextafter(hi, np.inf))

    def __add__(self, o):
        o = _box(o)
        return Box._out(self.lo + o.lo, self.hi + o.hi)

    __radd__ = __add__

    def __sub__(self, o):
        o = _box(o)
        return Box._out(self.lo - o.hi, self.hi - o.lo)

    def __rsub__(self, o):
        return _box(o) - self

    def __mul__(self, o):
        o = _box(o)
        p = [self.lo * o.lo, self.lo * o.hi, self.hi * o.lo, self.hi * o.hi]
        return Box._out(min(p), max(p))

    __rmul__ = __mul__

    def __truediv__(self, o):
        o = _box(o)
        if o.lo <= 0.0 <= o.hi:
            raise CheckError("data.enclosure_unbounded", "a lineage step divides by a box containing 0 (D4)")
        return self * Box._out(1.0 / o.hi, 1.0 / o.lo)

    def __rtruediv__(self, o):
        return _box(o) / self

    def log(self):
        if self.lo <= 0.0:
            raise CheckError("data.enclosure_unbounded", "a lineage step takes the log of a box containing 0 (D4)")
        return Box._out(math.log(self.lo), math.log(self.hi))

    def exp(self):
        return Box._out(math.exp(self.lo), math.exp(self.hi))

    def sqrt(self):
        if self.lo < 0:
            raise CheckError("data.enclosure_domain", "sqrt of a box with negative values")
        return Box._out(math.sqrt(self.lo), math.sqrt(self.hi))

    def intersect(self, o):
        return Box(max(self.lo, o.lo), min(self.hi, o.hi))

    @property
    def mid(self):
        return 0.5 * (self.lo + self.hi)


def _box(x):
    return x if isinstance(x, Box) else Box(x)


def enclosure(f, values, units, grad=None) -> dict:
    """The guaranteed enclosure of f over the rounding box prod [x_k - u_k/2, x_k + u_k/2]: the natural interval
    extension of f (called with Box arguments, outward rounding) intersected with the mean-value form
    f(x) + sum_k G_k [-u_k/2, u_k/2] when `grad` (Box-valued partial derivatives over the box) is given. Returns
    rho_obs / 2 = max(hi - f(x), f(x) - lo), rounded up (section 9.2)."""
    x = [float(v) for v in values]
    boxes = [Box(v - u / 2, v + u / 2) for v, u in zip(x, units)]
    nat = f(*boxes)
    fx = f(*[Box(v) for v in x]).mid
    enc = nat
    if grad is not None:
        G = grad(*boxes)
        mv = Box(fx)
        for g, u in zip(G, units):
            mv = mv + _box(g) * Box(-u / 2, u / 2)
        enc = nat.intersect(mv)
    half = max(enc.hi - fx, fx - enc.lo)
    return {"value": fx, "lo": enc.lo, "hi": enc.hi, "half": float(np.nextafter(half, np.inf))}


def admits_unbounded(f, value_ranges: list, units_fn, max_boxes: int = 4096) -> bool:
    """At locking: whether the declared format admits a rounding box on which a lineage step divides by, or takes the
    log of, a box containing 0, over the declared value ranges (a read value 0 in fixed decimals, or a difference
    straddling 0). D4 (A8): such a contract is rejected. A guarantee (F17): f is evaluated by outward-rounded interval
    arithmetic on the full ranges widened by half a unit; a box on which a step fails is bisected along its widest
    side until either the failure persists on a box no wider than the rounding units (the format admits it: True), or
    every sub-box evaluates (False). When `max_boxes` is exhausted the answer is True (conservative)."""
    def half_unit(lo, hi):
        cands = [lo, hi] + ([0.0] if lo <= 0 <= hi else [])
        return 0.5 * max(units_fn(c) for c in cands)

    stack = [[(float(lo), float(hi)) for lo, hi in value_ranges]]
    seen = 0
    while stack:
        box = stack.pop()
        seen += 1
        if seen > max_boxes:
            return True
        try:
            f(*[Box(lo - half_unit(lo, hi), hi + half_unit(lo, hi)) for lo, hi in box])
            continue
        except CheckError as exc:
            if exc.code != "data.enclosure_unbounded":
                continue
        widths = [hi - lo for lo, hi in box]
        k = int(np.argmax(widths))
        lo, hi = box[k]
        if widths[k] <= 2 * half_unit(lo, hi):            # a single rounding box: the format admits the failure
            return True
        mid = 0.5 * (lo + hi)
        for part in ((lo, mid), (mid, hi)):
            nb = list(box)
            nb[k] = part
            stack.append(nb)
    return False


_ALLOWED_CALLS = {"log": Box.log, "exp": Box.exp, "sqrt": Box.sqrt}


def relation_function(expression: str, inputs: list):
    """A derivation relation of the release (`derivation_relations`: {quantity, inputs, expression, ranges}) as a
    function of Box arguments: + - * / and log, exp, sqrt of the inputs and numeric constants only (no other names,
    attributes or calls; parsed, never evaluated as Python)."""
    import ast
    tree = ast.parse(expression, mode="eval")
    names = list(inputs)

    def ev(node, env):
        if isinstance(node, ast.Expression):
            return ev(node.body, env)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = ev(node.left, env), ev(node.right, env)
            return {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b,
                    ast.Div: lambda: a / b}[type(node.op)]()
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return Box(0.0) - ev(node.operand, env)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return Box(float(node.value))
        if isinstance(node, ast.Name) and node.id in env:
            return env[node.id]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_CALLS \
                and len(node.args) == 1 and not node.keywords:
            return _ALLOWED_CALLS[node.func.id](_box(ev(node.args[0], env)))
        raise CheckError("data.relation_syntax", f"unsupported element in the derivation relation {expression!r}")

    def f(*boxes):
        return _box(ev(tree, dict(zip(names, boxes))))
    for node in ast.walk(tree):                            # reject unknown names at parse time
        if isinstance(node, ast.Name) and node.id not in names and node.id not in _ALLOWED_CALLS:
            raise CheckError("data.relation_syntax", f"unknown name {node.id!r} in {expression!r}")
    return f


def unbounded_relations(release_declarations: dict, constrained: set) -> list:
    """D4 at locking (A8): the derivation relations of quantities that a declared constraint covers, whose formats
    admit an unbounded enclosure. Returns findings `data.enclosure_unbounded` (remedy level contract)."""
    out = []
    fmts = release_declarations.get("representation_format", "float64")
    for rel in release_declarations.get("derivation_relations") or []:
        if not isinstance(rel, dict) or rel.get("quantity") not in constrained or "expression" not in rel:
            continue
        ins = list(rel.get("inputs") or [])
        f = relation_function(rel["expression"], ins)
        fm = [_formats({"representation_format": fmts}, ins)[n] for n in ins]
        ranges = rel.get("ranges")
        if not ranges or len(ranges) != len(ins):
            raise CheckError("data.relation_ranges", f"the relation of {rel['quantity']} needs a value range per input")
        units = lambda v, _fm=fm: max(unit(v, x) for x in _fm)
        if admits_unbounded(f, ranges, units):
            out.append({"code": "data.enclosure_unbounded", "quantity": rel["quantity"], "remedy": "contract",
                        "expression": rel["expression"]})
    return out


def constraint_check(n: np.ndarray, c: float, values: np.ndarray, half_rho: np.ndarray) -> dict:
    """|n^T y - c| <= sum_i |n_i| rho_i^obs / 2 + a double-precision error (section 9.2). A strict upper bound: a
    correct release never triggers it."""
    n = np.asarray(n, float)
    y = np.asarray(values, float)
    lhs = abs(float(n @ y) - c)
    eps = 8 * np.finfo(float).eps * float(np.sum(np.abs(n * y)) + abs(c) + 1.0)
    rhs = float(np.sum(np.abs(n) * np.asarray(half_rho, float))) + eps
    return {"deviation": lhs, "tolerance": rhs, "triggered": lhs > rhs}


def residual_identity_check(n: np.ndarray, r: np.ndarray) -> dict:
    """Identities on the residuals (e.g. the sum of a shape's residuals conditioned on its total): |n^T r| <= a
    double-precision error, with no rounding term (D70)."""
    lhs = abs(float(np.asarray(n) @ np.asarray(r)))
    tol = 64 * np.finfo(float).eps * (float(np.sum(np.abs(np.asarray(n) * np.asarray(r)))) + 1.0)
    return {"deviation": lhs, "tolerance": tol, "triggered": lhs > tol}


# ------------------------------------------------------------------ the locking report (section 5.2 clause 9; 17)
def _formats(decl: dict, names: list) -> dict:
    f = decl.get("representation_format", "float64")
    if isinstance(f, str):
        return {n: {"kind": f} for n in names}
    return {n: (f.get(n) if isinstance(f.get(n), dict) else {"kind": f.get(n, "float64")}) for n in names}


def point_quantities(problem, params: dict) -> dict:
    """mu, V_data^unc (natural units) of the calibration observables at one point: the model's per-event covariance
    of the estimators divided by the exposure (the quantity the event-level bootstrap estimates; at the evaluation
    points of locking the model value itself is used)."""
    r = problem.ev.evaluate(params, names=problem.names)
    by = {o.name: o for o in problem.model.observables}
    runs = np.array([by[n].run for n in problem.names], dtype=object)
    V = r["s2"] / problem.exposure * np.equal.outer(runs, runs)
    return {"mu": r["pred"], "V": 0.5 * (V + V.T)}


def locking_report(contract: dict, release_declarations: dict, problem, n_scan: int = 64, seed: int = 20261112,
                   points: list | None = None, hashes: dict | None = None) -> dict:
    """The locking-stage decisions of calib_data for the calibration observables of the problem at the evaluation
    points of section 2.1 (or at the given points, e.g. the fit point): rounding negligibility on N_d,c^perp with the
    release's formats, sigma^(0) > 0, the N_d,c declaration check (a)(b)(c) in standardized coordinates, the value
    conventions against the declared constraints; n_min, block conversion and N_exp where the contract has such blocks
    (Gaussian summary statistics of scalar observables have none: recorded as not applicable; other blocks need the
    problem's `expected_counts(params)`, else the report is incomplete); D4 on the release's derivation relations of
    constrained quantities. Each point varies theta, the profiled phi (nu) at +-2 sigma and each eta at +-2 one axis at
    a time (section 2.1, D36). `hashes` {contract, plan, release} bind the report to its inputs (F18)."""
    from . import design as Dz
    from . import validate as Vd
    names = problem.names
    fmts = _formats(release_declarations or {}, names)
    val = contract.get("validation") or {}
    cons = []
    for nd in val.get("N_dc", []):
        cons.append(np.array([float(nd["n"].get(n, 0.0)) for n in names]))
    if points is None:
        box = {t: v["prior"] for t, v in problem.theta_spec.items()}
        scan = [np.array([pt[t] for t in box]) for pt in Dz.sobol_points(box, n_scan, seed)]
        nus = {n: s for n, (_, s) in problem.phi_spec.items()}
        nus.update({f"eta:{j}": 1.0 for j in range(len(getattr(problem, "eta_spec", []) or []))})
        pts = evaluation_points(list(box.values()), np.array(scan), nus)
        thetas = list(box)
        points = []
        for th, nu in pts:
            p = dict(zip(thetas, th))
            p.update({n: c + nu.get(n, 0.0) for n, (c, _) in problem.phi_spec.items()})
            p.update({k: v for k, v in nu.items() if k.startswith("eta:")})
            points.append(p)
    worst: dict[str, Any] = {"ratio": 0.0, "point": None}
    findings = []
    for p in points:
        q = point_quantities(problem, {k: v for k, v in p.items() if not k.startswith("eta:")})
        etas = {int(k[4:]): v for k, v in p.items() if k.startswith("eta:")}
        if etas:                                   # the eta shift in link space (relative on the mean)
            cols = problem.eta_columns(q["mu"])
            z = problem._to_link(q["mu"]) + cols[:, list(etas)] @ np.array(list(etas.values()))
            q["mu"] = np.array([L.inv_link(np.array([zk]), problem.links[n])[0] for zk, n in zip(z, names)])
        s = np.sqrt(np.clip(np.diag(q["V"]), 0.0, None))
        zero = [n for n, v in zip(names, s) if v <= 0]
        if zero:
            findings.append({"code": "data.sigma0_zero", "observables": zero, "point": p})
            continue
        rho = np.array([resolution(m, sg, fmts[n]) for m, sg, n in zip(q["mu"], s, names)])
        rr = rounding_ratio(q["V"], rho, s, cons)
        if rr["ratio"] > worst["ratio"]:
            worst = {"ratio": rr["ratio"], "point": p}
        if cons:
            dc = Vd.declaration_check(q["V"], s, cons)
            if dc["status"] != "passed":
                findings.append({"code": "data.ndc_declaration", "failures": dc["failures"], "point": p})
    if worst["ratio"] > ROUNDING_BOUND * (1 + 1e-12):
        findings.append({"code": "data.rounding", "ratio": worst["ratio"], "point": worst["point"]})
    conv = (contract.get("estimators") or {}).get("conventions") or {}
    for nd in val.get("N_d", []) + val.get("N_dc", []):
        obs = [n for n, v in nd["n"].items() if v]
        if obs and all(o in conv and "zero_events" in conv[o] for o in obs):
            lhs = sum(float(nd["n"][o]) * float(conv[o]["zero_events"]) for o in obs)
            if abs(lhs - float(nd.get("c", 0.0))) > 1e-12:
                findings.append({"code": "data.convention_violates_constraint", "observables": obs})
    constrained = {n for nd in val.get("N_d", []) + val.get("N_dc", []) for n, v in nd["n"].items() if v}
    findings += unbounded_relations(release_declarations or {}, constrained)
    status, na = ("failed" if findings else "passed"), []
    counts: dict[str, Any] = {}
    if all(b.kind == "gaussian-scalar" for b in problem.layout.blocks):
        na = ["n_min", "block_conversion", "N_exp"]
    elif not hasattr(problem, "expected_counts"):
        status = "failed" if findings else "incomplete"      # never leave the count rules silently deferred
        counts = {"status": "incomplete", "code": "data.counts_unavailable",
                  "reason": "the problem gives no expected counts at the evaluation points"}
    else:
        per = [problem.expected_counts({k: v for k, v in p.items() if not k.startswith("eta:")}) for p in points]
        counts = {"blocks": {}}
        for bi in per[0]:
            e = per[0][bi]
            res = {}
            if "counts" in e:
                E = np.array([x[bi]["counts"] for x in per], float)
                res["n_min"] = n_min_and_merging(E, shared_events=bool(e.get("shared_events", True)))
                res["block_conversion"] = block_conversion(counts_by_point=E)
                if e.get("absolute"):
                    res["N_exp"] = n_exp_check(E.sum(axis=1))
            if "n_eps" in e:
                res["block_conversion"] = block_conversion(binomial_by_point=np.array([x[bi]["n_eps"] for x in per]))
            for item in res.values():
                if item.get("finding") and (item.get("passed") is False):
                    findings.append({"code": item["finding"], "block": bi})
            counts["blocks"][bi] = res
        status = "failed" if findings else "passed"
    return {"status": status, "points": len(points), "rounding_worst": worst, "findings": findings,
            "not_applicable": na, "counts": counts, "hashes": dict(hashes or {}),
            "reading": "V_data^unc at the evaluation points: the model's per-event covariance / exposure"}
