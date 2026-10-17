#!/usr/bin/env python3
"""Propagate a calibration residual (scale, inverse offset, resolution, user plugin) into binned yields and ratios.

Purpose: turn a residual of the momentum or rigidity calibration (or of any positive variable x) into per-bin yield
shifts, {nominal, up, down} variations for check_systematic_variations.py, a correlated covariance block and, for an
opposite-sign ratio, the ratio shift. See "Propagating a calibration residual" in
<plugin root>/skills/hep-detector/references/calibration-and-alignment.md.

Modes (each needs its parameter; there is no default delta or s):
- scale: x_m = (1 + s) x. On a power law dN/dx ~ x^-gamma every bin shifts by (1+s)^(gamma-1) - 1 ~ (gamma-1) s;
- inverse-offset: 1/x_m = 1/x + q delta, with q the charge sign (an offset of the signed curvature, as from a
  misalignment). The measured density is x^-gamma (1 - q x delta)^(gamma-2), first order (2-gamma) q x delta; the
  shift grows with x and has opposite signs for the two charge signs, so in an opposite-sign ratio the signed shifts
  subtract and their magnitudes add (no cancellation);
- resolution: x_m = x (1 + eps), eps a core Gaussian (core-sigma) plus a fraction tail-fraction of a wider Gaussian
  (tail-sigma), relative widths; up and down scale both widths by (1 +/- resolution-shift);
- plugin: a user file defining distort(x, charge_sign, variation) -> x_m (x > 0, variation "up" or "down"); it runs
  only with --allow-plugin, its path is resolved relative to the input file, and its errors give status failed.
"up" uses +s, +delta, wider resolution; "down" the opposite.

Subcommands:
- response INPUT.json: analytic yields for power-law components (infinite power law norm * x^-gamma; mapped bin edges
  integrated exactly; resolution: the folding factor E[(1+eps)^(gamma-1)] by numerical integration, valid while
  8 x the widest relative width stays below 1; plugin: bin edges inverted by bisection, the map must increase).
  INPUT: {"variable", "unit", "edges": [...], "components": [{"name", "charge_sign": +1|-1,
  "spectrum": {"kind": "power-law", "index", "norm"}}], "ratio": {"numerator", "denominator"} (optional)};
- events EVENTS.csv: the same distortions applied to each event (lines starting with # are skipped), binned by |x|
  per charge sign (components "positive" and "negative"); the sign comes from --signed (x carries it) or
  --sign-column; an inverse offset can flip the sign of an event (charge confusion). resolution needs --seed (up is
  extra smearing, down the mirror image 2 nominal - up). Output adds up_diff_sumw2/down_diff_sumw2, the variance of the
  difference from the events that change bin, which check_systematic_variations.py uses for correlated variations.

Warnings and refusals: a missing charge sign is refused; |q x delta| > 0.3 at a bin edge warns (the first-order form
fails); 1 - q x delta <= 0 at an edge is refused in response (the mapping is not one-to-one there).
Optional --validation-record PATH (with --effect NAME and a ratio): a validation record
(contracts/schemas/validation_record.json) stating that the residual is fully correlated between the two operands
and whether it cancels in the ratio. Written only on request.

Output: JSON with status, status_label (--status, default unvalidated), inputs, defaults_used, warnings, edges,
components (nominal, up, down, relative shifts, systematic_variations, covariance) and ratio. Exit codes: 0 ok;
1 the plugin failed (status failed); 2 invalid input or arguments (status rejected).
Run: python3 <plugin root>/skills/hep-detector/scripts/propagate_scale_distortion.py response model.json --mode inverse-offset --delta 1e-4
"""
import argparse
import bisect
import csv
import hashlib
import importlib.util
import json
import math
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # sibling imports leave no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from contracts.schema import validate  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

WARN_QXD = 0.3
MODES = ("scale", "inverse-offset", "resolution", "plugin")


class InputError(ValueError):
    """Invalid input or arguments (status rejected, exit 2)."""


class PluginError(RuntimeError):
    """The user plugin raised or returned an unusable value (status failed, exit 1)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(exit_code("rejected"), f"{self.prog}: error: {message}\n")


def _finite(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise InputError(f"{name} must be a finite number")
    if positive and value <= 0:
        raise InputError(f"{name} must be greater than zero")
    return float(value)


def _edges(values):
    edges = [_finite(v, "edge", positive=True) for v in values]
    if len(edges) < 2 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise InputError("edges must be at least two positive, strictly increasing numbers")
    return edges


# ----------------------------------------------------------------------------------------------- distortions
class Distortion:
    """The mode and its parameter; forward(x, q, variation) -> signed measured value (sign = charge sign)."""

    def __init__(self, args, base_dir):
        self.mode = args.mode
        self.params = {}
        if self.mode == "scale":
            if args.scale is None:
                raise InputError("--scale is required for mode scale (no default)")
            s = _finite(args.scale, "--scale")
            if not 0 < abs(s) < 1:
                raise InputError("--scale must satisfy 0 < |s| < 1")
            self.params = {"scale": s}
        elif self.mode == "inverse-offset":
            if args.delta is None:
                raise InputError("--delta is required for mode inverse-offset (no default)")
            d = _finite(args.delta, "--delta")
            if d == 0:
                raise InputError("--delta must be nonzero")
            self.params = {"delta": d}
        elif self.mode == "resolution":
            missing = [n for n in ("core_sigma", "tail_fraction", "tail_sigma", "resolution_shift")
                       if getattr(args, n) is None]
            if missing:
                raise InputError("mode resolution needs " + ", ".join("--" + m.replace("_", "-") for m in missing)
                                 + " (no defaults)")
            core = _finite(args.core_sigma, "--core-sigma", positive=True)
            tail = _finite(args.tail_sigma, "--tail-sigma", positive=True)
            frac = _finite(args.tail_fraction, "--tail-fraction")
            r = _finite(args.resolution_shift, "--resolution-shift", positive=True)
            if not 0 <= frac <= 1 or r >= 1:
                raise InputError("--tail-fraction must be in [0, 1] and --resolution-shift in (0, 1)")
            if 8 * max(core, tail) * (1 + r) >= 1:
                raise InputError("relative widths too large: 8 x the widest width (after the up shift) must stay "
                                 "below 1 for x(1+eps) to stay positive")
            self.params = {"core_sigma": core, "tail_fraction": frac, "tail_sigma": tail, "resolution_shift": r}
        else:
            if args.plugin is None:
                raise InputError("mode plugin needs --plugin PATH")
            if not args.allow_plugin:
                raise InputError("a plugin runs user code: pass --allow-plugin to run it")
            path = Path(args.plugin)
            if not path.is_absolute():
                path = (base_dir / path).resolve()
            if not path.is_file():
                raise InputError(f"plugin {path} does not exist")
            try:
                spec = importlib.util.spec_from_file_location("distortion_plugin", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.plugin = module.distort
            except Exception as exc:  # user code: any failure is the plugin's
                raise PluginError(f"plugin {path.name} could not be loaded: {exc}") from None
            self.params = {"plugin": str(path), "plugin_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def sign(self, variation):
        return 1.0 if variation == "up" else -1.0

    def forward(self, x, q, variation):
        """Measured signed value for magnitude x > 0 and charge sign q; None when it leaves the representable range."""
        v = self.sign(variation)
        if self.mode == "scale":
            return q * x * (1 + v * self.params["scale"])
        if self.mode == "inverse-offset":
            rho = q / x + v * self.params["delta"]
            return None if rho == 0 else 1.0 / rho
        if self.mode == "plugin":
            try:
                out = self.plugin(x, int(q), variation)
            except Exception as exc:
                raise PluginError(f"plugin failed: {exc}") from None
            if isinstance(out, bool) or not isinstance(out, (int, float)) or not math.isfinite(out) or out <= 0:
                raise PluginError(f"plugin returned {out!r} for x={x!r}; it must return a finite positive number")
            return q * float(out)
        raise AssertionError(self.mode)


# ----------------------------------------------------------------------------------------------- response
def power_integral(lo, hi, gamma):
    if abs(gamma - 1.0) < 1e-12:
        return math.log(hi / lo)
    e = 1.0 - gamma
    return (hi ** e - lo ** e) / e


def gaussian_moment(sigma, k, n=4000):
    """E[(1 + eps)^k] for eps ~ N(0, sigma), by Simpson's rule on [-8 sigma, 8 sigma]."""
    lo, hi = -8 * sigma, 8 * sigma
    h = (hi - lo) / n
    total = 0.0
    for i in range(n + 1):
        e = lo + i * h
        w = 1 if i in (0, n) else (4 if i % 2 else 2)
        total += w * math.exp(-0.5 * (e / sigma) ** 2) * (1 + e) ** k
    return total * h / 3 / (sigma * math.sqrt(2 * math.pi))


def folding_factor(params, gamma, variation):
    scale = {"nominal": 1.0, "up": 1 + params["resolution_shift"], "down": 1 - params["resolution_shift"]}[variation]
    k = gamma - 1.0
    f = params["tail_fraction"]
    core = gaussian_moment(params["core_sigma"] * scale, k)
    tail = gaussian_moment(params["tail_sigma"] * scale, k) if f > 0 else 0.0
    return (1 - f) * core + f * tail


def _invert(dist, edge, q, variation):
    """True magnitude x with |forward(x)| = edge (bisection in log x); the map must increase."""
    def g(x):
        out = dist.forward(x, q, variation)
        return abs(out) - edge
    lo, hi = edge / 1e3, edge * 1e3
    if not (g(lo) < 0 < g(hi)):
        raise PluginError(f"plugin map does not bracket the edge {edge:g} within a factor 1000")
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if g(mid) < 0:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def response_yields(dist, comp, edges, warnings):
    q, gamma, norm = comp["charge_sign"], comp["spectrum"]["index"], comp["spectrum"]["norm"]
    nominal = [norm * power_integral(lo, hi, gamma) for lo, hi in zip(edges, edges[1:])]
    out = {"nominal": nominal}
    for variation in ("up", "down"):
        if dist.mode == "resolution":
            ratio = folding_factor(dist.params, gamma, variation) / folding_factor(dist.params, gamma, "nominal")
            out[variation] = [n * ratio for n in nominal]
            continue
        if dist.mode == "scale":
            f = 1 + dist.sign(variation) * dist.params["scale"]
            true_edges = [e / f for e in edges]
        elif dist.mode == "inverse-offset":
            qd = q * dist.sign(variation) * dist.params["delta"]
            if any(1 - qd * e <= 0 for e in edges):
                raise InputError(f"component {comp['name']!r}: 1 - q x delta <= 0 inside the bins ({variation}); "
                                 "the inverse offset is not one-to-one there (charge-sign flips)")
            worst = max(abs(qd * e) for e in edges)
            if worst > WARN_QXD:
                warnings.append(f"component {comp['name']!r} ({variation}): |q x delta| reaches {worst:.3g} > "
                                f"{WARN_QXD} at the highest edge; the first-order form (2-gamma) q x delta fails there")
            true_edges = [e / (1 - qd * e) for e in edges]
        else:
            true_edges = [_invert(dist, e, q, variation) for e in edges]
            if any(b <= a for a, b in zip(true_edges, true_edges[1:])):
                raise PluginError("plugin map is not increasing over the bins")
        out[variation] = [norm * power_integral(lo, hi, gamma) for lo, hi in zip(true_edges, true_edges[1:])]
    if dist.mode == "scale":
        out["first_order_shift_up"] = [(gamma - 1) * dist.params["scale"]] * len(nominal)
    elif dist.mode == "inverse-offset":
        out["first_order_shift_up"] = [(2 - gamma) * q * math.sqrt(lo * hi) * dist.params["delta"]
                                       for lo, hi in zip(edges, edges[1:])]
    return out


def load_model(path):
    try:
        raw = Path(path).read_bytes()
        doc = json.loads(raw)
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc.strerror or exc}") from None
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"{path} is not JSON: {exc}") from None
    if not isinstance(doc, dict):
        raise InputError("the input must be a JSON object")
    edges = _edges(doc.get("edges") or [])
    comps = doc.get("components")
    if not isinstance(comps, list) or not comps:
        raise InputError("components must be a non-empty list")
    names = []
    for i, c in enumerate(comps):
        if not isinstance(c, dict) or not isinstance(c.get("name"), str) or not c["name"] or c["name"] in names:
            raise InputError(f"components[{i}] needs a unique name")
        names.append(c["name"])
        if c.get("charge_sign") not in (1, -1) or isinstance(c.get("charge_sign"), bool):
            raise InputError(f"component {c['name']!r}: charge_sign (+1 or -1) is missing or invalid; the sign of "
                             "the charge decides the direction of an inverse offset")
        spec = c.get("spectrum")
        if not isinstance(spec, dict) or spec.get("kind") != "power-law":
            raise InputError(f"component {c['name']!r}: spectrum must be {{'kind': 'power-law', 'index', 'norm'}}")
        _finite(spec.get("index"), f"{c['name']}.spectrum.index")
        _finite(spec.get("norm"), f"{c['name']}.spectrum.norm", positive=True)
    ratio = doc.get("ratio")
    if ratio is not None:
        if not isinstance(ratio, dict) or ratio.get("numerator") not in names or ratio.get("denominator") not in names \
                or ratio["numerator"] == ratio["denominator"]:
            raise InputError("ratio must name two different components as numerator and denominator")
    return doc, edges, hashlib.sha256(raw).hexdigest()


# ----------------------------------------------------------------------------------------------- events
def read_events(args):
    if not (args.signed or args.sign_column):
        raise InputError("the charge sign is missing: give --signed (the column carries the sign) or --sign-column")
    weights_col = args.weight_column
    try:
        with open(args.events, encoding="utf-8", newline="") as handle:
            raw = handle.read()
    except OSError as exc:
        raise InputError(f"cannot read {args.events}: {exc.strerror or exc}") from None
    lines = [line for line in raw.splitlines() if not line.startswith("#")]
    reader = csv.DictReader(lines)
    needed = [args.column] + ([args.sign_column] if args.sign_column else []) + ([weights_col] if weights_col else [])
    if reader.fieldnames is None or any(n not in reader.fieldnames for n in needed):
        raise InputError(f"column(s) {[n for n in needed if n not in (reader.fieldnames or [])]} not in the header")
    events, skipped = [], 0
    for i, row in enumerate(reader, start=2):
        try:
            x = float(row[args.column])
            w = float(row[weights_col]) if weights_col else 1.0
        except (TypeError, ValueError):
            raise InputError(f"row {i}: not a number in {args.column!r} or the weight column") from None
        if not math.isfinite(w):
            raise InputError(f"row {i}: non-finite weight")
        if args.sign_column:
            try:
                s = float(row[args.sign_column])
            except (TypeError, ValueError):
                raise InputError(f"row {i}: charge sign missing in {args.sign_column!r}") from None
            if not math.isfinite(s) or s == 0:
                raise InputError(f"row {i}: charge sign missing or zero in {args.sign_column!r}")
            q = 1.0 if s > 0 else -1.0
        else:
            if x == 0 or not math.isfinite(x):
                skipped += 1
                continue
            q = 1.0 if x > 0 else -1.0
        if not math.isfinite(x) or x == 0:
            skipped += 1
            continue
        events.append((abs(x), q, w))
    if not events:
        raise InputError("no usable events")
    return events, skipped, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _bin(edges, x):
    i = bisect.bisect_right(edges, x) - 1
    return i if 0 <= i < len(edges) - 1 else None


def event_yields(dist, events, edges, seed):
    nb = len(edges) - 1
    names = {1.0: "positive", -1.0: "negative"}
    hist = {v: {n: [0.0] * nb for n in names.values()} for v in ("nominal", "up", "down")}
    diff = {v: {n: [0.0] * nb for n in names.values()} for v in ("up", "down")}
    lost = 0
    rng = random.Random(seed) if dist.mode == "resolution" else None
    if rng:
        p, r = dist.params, dist.params["resolution_shift"]
        extra = math.sqrt((1 + r) ** 2 - 1)
    for x, q, w in events:
        b0, c0 = _bin(edges, x), names[q]
        if b0 is not None:
            hist["nominal"][c0][b0] += w
        variations = ("up",) if rng else ("up", "down")
        for v in variations:
            if rng:
                width = p["tail_sigma"] if rng.random() < p["tail_fraction"] else p["core_sigma"]
                xm = q * x * (1 + width * extra * rng.gauss(0.0, 1.0))
            else:
                xm = dist.forward(x, q, v)
            if xm is None or not math.isfinite(xm):
                lost += 1
                b1 = c1 = None
            else:
                b1, c1 = _bin(edges, abs(xm)), names[1.0 if xm > 0 else -1.0]
                if b1 is not None:
                    hist[v][c1][b1] += w
            if (c0, b0) != (c1, b1):
                if b0 is not None:
                    diff[v][c0][b0] += w * w
                if b1 is not None:
                    diff[v][c1][b1] += w * w
    if rng:  # down: the mirror image of the extra smearing
        for c in names.values():
            hist["down"][c] = [2 * n - u for n, u in zip(hist["nominal"][c], hist["up"][c])]
            diff["down"][c] = list(diff["up"][c])
    comps = {}
    for c in names.values():
        comps[c] = {"charge_sign": 1 if c == "positive" else -1, "nominal": hist["nominal"][c], "up": hist["up"][c],
                    "down": hist["down"][c], "up_diff_sumw2": diff["up"][c], "down_diff_sumw2": diff["down"][c]}
    return comps, lost


# ----------------------------------------------------------------------------------------------- shared output
def _shifts(nominal, varied):
    return [(v / n - 1.0) if n else None for n, v in zip(nominal, varied)]


def _covariance(up, down):
    d = [(u - w) / 2 for u, w in zip(up, down)]
    return [[a * b for b in d] for a in d]


def finish_component(comp):
    comp["relative_shift_up"] = _shifts(comp["nominal"], comp["up"])
    comp["relative_shift_down"] = _shifts(comp["nominal"], comp["down"])
    sv = {"nominal": comp["nominal"], "up": comp["up"], "down": comp["down"]}
    if "up_diff_sumw2" in comp:
        sv["up_diff_sumw2"] = comp.pop("up_diff_sumw2")
        sv["down_diff_sumw2"] = comp.pop("down_diff_sumw2")
    comp["systematic_variations"] = sv
    comp["covariance"] = _covariance(comp["up"], comp["down"])
    comp["covariance_kind"] = "fully correlated (one parameter), rank 1"
    return comp


def ratio_block(comps, numerator, denominator):
    num, den = comps[numerator], comps[denominator]
    out = {"numerator": numerator, "denominator": denominator}
    for v in ("nominal", "up", "down"):
        out[v] = [(a / b) if b else None for a, b in zip(num[v], den[v])]
    for v in ("up", "down"):
        out[f"relative_shift_{v}"] = [(u / n - 1.0) if (u is not None and n) else None
                                      for n, u in zip(out["nominal"], out[v])]
        out[f"signed_shift_difference_{v}"] = [(a - b) if a is not None and b is not None else None for a, b in
                                               zip(num[f"relative_shift_{v}"], den[f"relative_shift_{v}"])]
    if any(v is None for v in out["up"] + out["down"] + out["nominal"]):
        out["covariance"] = None
    else:
        out["covariance"] = _covariance(out["up"], out["down"])
    out["covariance_kind"] = "fully correlated (one parameter), rank 1"
    pairs = [(a, b) for a, b in zip(num["relative_shift_up"], den["relative_shift_up"]) if a is not None and b is not None]
    opposite = bool(pairs) and all(a * b < 0 for a, b in pairs)
    out["cancellation"] = ("none: the signed shifts have opposite signs, so they subtract and their magnitudes add"
                           if opposite else "partial: the signed shifts subtract")
    return out


def write_validation_record(args, ratio, sha, edges, variable, unit, dist):
    shifts = [abs(v) for v in ratio["relative_shift_up"] + ratio["relative_shift_down"] if v is not None]
    biggest = max(shifts) if shifts else float("nan")
    param = ", ".join(f"{k}={v:g}" for k, v in dist.params.items() if isinstance(v, float))
    cancels = ratio["cancellation"].startswith("none")
    record = {
        "validation_record_version": "1.0.0",
        "claim": {"effect": args.effect, "relation": "fully_correlated"},
        "subjects": [{"root": ratio["numerator"], "version": f"sha256:{sha[:16]}"},
                     {"root": ratio["denominator"], "version": f"sha256:{sha[:16]}"}],
        "method": f"propagate_scale_distortion.py {args.command} --mode {dist.mode}: one parameter drives both "
                  "operands; the ratio shift is computed per bin from the varied yields",
        "tolerance": ("exact for the stated power-law model (analytic integrals; numerical folding below 1e-9)"
                      if args.command == "response" else "statistical: the events that change bin"),
        "scope": f"{variable} bins {edges[0]:g}-{edges[-1]:g} {unit}; {dist.mode} {param}".strip(),
        "conclusion": (f"The residual is fully correlated between the operands but its effects do not cancel in the "
                       f"ratio: the signed shifts subtract and their magnitudes add; largest |ratio shift| "
                       f"{biggest:.3g}." if cancels else
                       f"The residual is fully correlated between the operands and partially cancels in the ratio; "
                       f"largest |ratio shift| {biggest:.3g}."),
    }
    report = validate(record, "validation_record.json")
    if not report.ok:
        raise PluginError(f"internal: the validation record does not validate: {report.as_dict()}")
    Path(args.validation_record).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def run(args):
    if args.validation_record:
        if not args.effect:
            raise InputError("--validation-record needs --effect NAME (the effect the residual belongs to)")
        if not Path(args.validation_record).resolve().parent.is_dir():
            raise InputError(f"folder of {args.validation_record} does not exist")
    warnings, defaults_used = [], []
    if args.command == "response":
        doc, edges, sha = load_model(args.input)
        dist = Distortion(args, Path(args.input).resolve().parent)
        variable, unit = doc.get("variable", "x"), doc.get("unit", "")
        comps = {}
        for c in doc["components"]:
            comps[c["name"]] = {"charge_sign": c["charge_sign"], "spectral_index": c["spectrum"]["index"],
                                **response_yields(dist, c, edges, warnings)}
        ratio_names = (doc["ratio"]["numerator"], doc["ratio"]["denominator"]) if doc.get("ratio") else None
        inputs = {"input": str(args.input), "input_sha256": sha, "mode": dist.mode, **dist.params}
    else:
        edges = _edges(args.edges)
        if args.mode == "resolution" and args.seed is None:
            raise InputError("mode resolution on events needs --seed (the extra smearing is random)")
        events, skipped, sha = read_events(args)
        dist = Distortion(args, Path(args.events).resolve().parent)
        variable, unit = args.column, ""
        comps, lost = event_yields(dist, events, edges, args.seed)
        if lost:
            warnings.append(f"{lost} varied events reached infinite |x| (curvature exactly zero) and left the bins")
        for name, q in (("positive", 1.0), ("negative", -1.0)):
            if dist.mode == "inverse-offset":
                worst = max(abs(q * e * dist.params["delta"]) for e in edges)
                if worst > WARN_QXD:
                    warnings.append(f"|q x delta| reaches {worst:.3g} > {WARN_QXD} at the highest edge")
                    break
        ratio_names = None
        if args.ratio:
            ratio_names = ("negative", "positive") if args.ratio == "negative-over-positive" else ("positive", "negative")
        inputs = {"events": str(args.events), "events_sha256": sha, "column": args.column,
                  "sign": "signed column" if args.signed else f"column {args.sign_column}",
                  "weight_column": args.weight_column, "events_used": len(events), "events_skipped": skipped,
                  "seed": args.seed, "mode": dist.mode, **dist.params}
    for comp in comps.values():
        finish_component(comp)
    result = {"status": "ok", "status_label": args.status, "method": f"calibration residual, mode {dist.mode}",
              "inputs": inputs, "defaults_used": defaults_used, "warnings": warnings,
              "variable": variable, "unit": unit, "edges": edges, "components": comps}
    if ratio_names:
        result["ratio"] = ratio_block(comps, *ratio_names)
    if args.validation_record:
        if not ratio_names:
            raise InputError("--validation-record needs a ratio (two operands)")
        write_validation_record(args, result["ratio"], sha, edges, variable, unit, dist)
        result["validation_record"] = str(args.validation_record)
    return result


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--mode", choices=MODES, required=True)
    common.add_argument("--scale", type=float, help="s of x_m = (1+s) x (mode scale; required there)")
    common.add_argument("--delta", type=float, help="delta of 1/x_m = 1/x + q delta, in 1/unit (inverse-offset)")
    common.add_argument("--core-sigma", type=float, help="relative core width (mode resolution)")
    common.add_argument("--tail-fraction", type=float, help="fraction of the tail Gaussian (mode resolution)")
    common.add_argument("--tail-sigma", type=float, help="relative tail width (mode resolution)")
    common.add_argument("--resolution-shift", type=float, help="relative change of both widths (mode resolution)")
    common.add_argument("--plugin", help="python file with distort(x, charge_sign, variation) (mode plugin)")
    common.add_argument("--allow-plugin", action="store_true", help="allow running the plugin's code")
    common.add_argument("--validation-record", help="write a validation record here (needs --effect and a ratio)")
    common.add_argument("--effect", help="effect name for the validation record")
    add_status_argument(common)
    parser = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    rsp = sub.add_parser("response", parents=[common], help="analytic yields for power-law components")
    rsp.add_argument("input", help="JSON model: edges, components (charge_sign, power-law spectrum), ratio")
    evt = sub.add_parser("events", parents=[common], help="apply the residual to events and bin them")
    evt.add_argument("events", help="CSV of events (# lines skipped)")
    evt.add_argument("--column", required=True, help="column of x (e.g. rigidity)")
    evt.add_argument("--signed", action="store_true", help="the column carries the charge sign")
    evt.add_argument("--sign-column", help="column whose sign is the charge sign")
    evt.add_argument("--weight-column", help="column of event weights (default: unit weights)")
    evt.add_argument("--edges", type=float, nargs="+", required=True, help="bin edges of |x|")
    evt.add_argument("--ratio", choices=("negative-over-positive", "positive-over-negative"))
    evt.add_argument("--seed", type=int, help="seed of the extra smearing (mode resolution)")
    args = parser.parse_args(argv)
    try:
        result = run(args)
    except InputError as exc:
        result = {"status": "rejected", "status_label": args.status, "error": str(exc)}
    except PluginError as exc:
        result = {"status": "failed", "status_label": args.status, "error": str(exc)}
    except (OverflowError, ZeroDivisionError) as exc:
        result = {"status": "rejected", "status_label": args.status, "error": f"numerical range: {exc}"}
    try:
        text = json.dumps(result, indent=2, allow_nan=False)
    except ValueError:
        result = {"status": "rejected", "status_label": args.status,
                  "error": "a result is not finite; the inputs are outside the representable range"}
        text = json.dumps(result, indent=2)
    print(text)
    return exit_code(result["status"])


if __name__ == "__main__":
    raise SystemExit(main())
