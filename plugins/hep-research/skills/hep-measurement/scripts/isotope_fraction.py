#!/usr/bin/env python3
"""Isotope fractions per rigidity bin from mass (or 1/beta) templates built from a resolution model (M8).

Purpose: separating isotopes of one element needs a mass, m = Z R sqrt(1/beta^2 - 1), from rigidity and velocity;
the mass resolution, (sigma_m/m)^2 = (sigma_R/R)^2 + gamma^4 (sigma_beta/beta)^2, grows as gamma^2 when beta -> 1, so
the separation has a limited energy range set by the resolution (see
<plugin root>/skills/hep-measurement/references/correction-chain.md, "Nuclei and isotopes").

Method:
- templates: for each rigidity bin and isotope, seeded MC (NumPy PCG64): R drawn from a power law within the bin,
  beta_true from R, Z and the nuclear mass (core/constants: AME2020 atomic mass minus Z electrons, or a stated
  mass); measured R with a Gaussian relative resolution, measured beta with a Gaussian core plus an optional wider
  tail (fraction, scale); events outside the declared beta range of the velocity detector are dropped; the variable
  (mass or 1/beta) is histogrammed. Optional background templates are added as given;
- fit: the data histogram of each bin is fitted with the isotope (and background) templates by the extended Poisson
  likelihood with the full Barlow-Beeston treatment of the finite template statistics (core/stats/template_fit.py,
  at most 6 templates and 60 bins). The generated MC count normalizes each template, so a yield is an arriving
  (generated-equivalent) count and the fractions f_i = Y_i / sum Y are of the isotopes arriving in the bin, corrected
  for the beta-range acceptance. Errors from the fit covariance (delta method);
- diagnostics: the Bhattacharyya overlap of each pair of normalized templates, and for each declared resolution
  nuisance the shift of every fraction when the parameter moves by +-1 sigma (templates rebuilt with the same seed);
- MC-only templates whose tails were not validated on data (tails_validated_on_data false or missing) label the
  output unvalidated whatever --status says.
Output also carries "composition_table": the fractions in the {"kind": "table", ...} composition format of
skills/hep-measurement/scripts/spectrum_transform.py (M7), and the per-bin yields for a species-migration fit
(skills/hep-detector/scripts/species_response.py).

Configuration JSON: {"variable": "mass"|"inverse_beta", "charge": Z, "isotopes": [{"name": "7Be", "mass_gev"?}],
  "rigidity_edges": [...], "rigidity_spectrum_index": g, "resolution": {"sigma_r_rel", "sigma_beta",
  "beta_tail"?: {"fraction", "scale"}, "beta_range": [lo, hi]}, "variable_edges": [...], "variable_unit"?,
  "mc_events_per_isotope": N, "tails_validated_on_data": bool, "nuisances"?: [{"name", "parameter", "relative_uncertainty"}],
  "backgrounds"?: {NAME: [[counts per variable bin] per rigidity bin]}}
Data JSON: {"bins": [[counts per variable bin] per rigidity bin]}.
Usage:
  isotope_fraction.py fit --config CFG.json --data DATA.json --seed N [--no-nuisances] [--status LABEL]
  isotope_fraction.py templates --config CFG.json --seed N [--status LABEL]
  isotope_fraction.py resolution --sigma-r-rel S --sigma-beta S --beta B [B ...] [--status LABEL]
Output JSON: status (ok, failed, rejected, missing-dependency), status_label, inputs, defaults_used, warnings, and
the result. Exit codes: 0 ok; 1 a fit failed; 2 bad input; 3 NumPy missing (fit, templates).
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
from core.stats import template_fit  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
VARIABLES = ("mass", "inverse_beta")


class InputError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _num(x, where: str, lo: float | None = None, hi: float | None = None, strict: bool = False) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise InputError(f"{where}: {x!r} is not a finite number")
    if lo is not None and (x < lo or (strict and x == lo)):
        raise InputError(f"{where}: must be {'>' if strict else '>='} {lo}")
    if hi is not None and x > hi:
        raise InputError(f"{where}: must be <= {hi}")
    return float(x)


def sigma_m_over_m(sigma_r_rel: float, sigma_beta: float, beta: float) -> float:
    """(sigma_m/m)^2 = (sigma_R/R)^2 + gamma^4 (sigma_beta/beta)^2."""
    g2 = 1.0 / (1.0 - beta * beta)
    return math.sqrt(sigma_r_rel ** 2 + (g2 * sigma_beta / beta) ** 2)


def isotope_masses(cfg: dict) -> dict:
    z = int(_num(cfg.get("charge"), "charge", 1))
    out = {}
    for iso in cfg.get("isotopes") or []:
        name = iso.get("name")
        if "mass_gev" in iso:
            out[name] = (_num(iso["mass_gev"], f"{name}.mass_gev", 0, strict=True), "stated", None)
            continue
        try:
            rec = constants.nuclide(name)
        except constants.ConstantsError as exc:
            raise InputError(f"isotope {name!r}: {exc}; give mass_gev") from None
        if rec["Z"] != z:
            raise InputError(f"isotope {name} has Z = {rec['Z']}, the config says {z}")
        out[name] = (constants.nuclear_mass_gev(rec["Z"], rec["A"]), "AME2020 via core/constants", rec["A"])
    if not 1 <= len(out) <= template_fit.MAX_TEMPLATES:
        raise InputError(f"give 1 to {template_fit.MAX_TEMPLATES} isotopes")
    return out


def check_config(cfg: dict) -> dict:
    if cfg.get("variable") not in VARIABLES:
        raise InputError(f"variable must be one of {VARIABLES}")
    edges = [_num(e, "rigidity_edges", 0, strict=True) for e in cfg.get("rigidity_edges") or []]
    vedges = [_num(e, "variable_edges") for e in cfg.get("variable_edges") or []]
    for name, e in (("rigidity_edges", edges), ("variable_edges", vedges)):
        if len(e) < 2 or any(b <= a for a, b in zip(e, e[1:])):
            raise InputError(f"{name}: at least two strictly increasing values")
    if len(vedges) - 1 > template_fit.MAX_BINS:
        raise InputError(f"at most {template_fit.MAX_BINS} variable bins")
    res = cfg.get("resolution") or {}
    _num(res.get("sigma_r_rel"), "resolution.sigma_r_rel", 0)
    _num(res.get("sigma_beta"), "resolution.sigma_beta", 0, strict=True)
    rng = res.get("beta_range")
    if not (isinstance(rng, list) and len(rng) == 2 and 0 < _num(rng[0], "beta_range") < _num(rng[1], "beta_range") <= 1):
        raise InputError("resolution.beta_range must be [lo, hi] with 0 < lo < hi <= 1")
    tail = res.get("beta_tail") or {}
    if tail:
        _num(tail.get("fraction"), "beta_tail.fraction", 0, 1)
        _num(tail.get("scale"), "beta_tail.scale", 1)
    n = _num(cfg.get("mc_events_per_isotope"), "mc_events_per_isotope", 1)
    if n != int(n) or n > 5e6:
        raise InputError("mc_events_per_isotope must be an integer up to 5e6")
    _num(cfg.get("rigidity_spectrum_index"), "rigidity_spectrum_index")
    return {"edges": edges, "vedges": vedges, "masses": isotope_masses(cfg)}


def build_templates(cfg: dict, seed: int, scale: dict | None = None) -> dict:
    import numpy as np  # optional: exit 3 in main when missing
    chk = check_config(cfg)
    res = dict(cfg["resolution"])
    for k, v in (scale or {}).items():
        res[k] = res[k] * v
    z, gidx, n = int(cfg["charge"]), float(cfg["rigidity_spectrum_index"]), int(cfg["mc_events_per_isotope"])
    tail = res.get("beta_tail") or {"fraction": 0.0, "scale": 1.0}
    lo_b, hi_b = res["beta_range"]
    rng = np.random.default_rng(seed)
    templates = []
    for k in range(len(chk["edges"]) - 1):
        r1, r2 = chk["edges"][k], chk["edges"][k + 1]
        row = {}
        for iso, (m, _src, _a) in chk["masses"].items():
            u = rng.random(n)
            if abs(gidx - 1.0) < 1e-12:
                r = r1 * (r2 / r1) ** u
            else:
                a = 1.0 - gidx
                r = (r1 ** a + u * (r2 ** a - r1 ** a)) ** (1.0 / a)
            beta = z * r / np.sqrt((z * r) ** 2 + m * m)
            rm = r * (1.0 + res["sigma_r_rel"] * rng.standard_normal(n))
            sb = np.where(rng.random(n) < tail["fraction"], res["sigma_beta"] * tail["scale"], res["sigma_beta"])
            bm = beta + sb * rng.standard_normal(n)
            keep = (bm > lo_b) & (bm < hi_b) & (rm > 0)
            if cfg["variable"] == "mass":
                x = z * rm[keep] * np.sqrt(1.0 / bm[keep] ** 2 - 1.0)
            else:
                x = 1.0 / bm[keep]
            counts, _ = np.histogram(x, bins=chk["vedges"])
            row[iso] = counts.astype(float).tolist()
        templates.append(row)
    return {"templates": templates, "generated": {iso: float(n) for iso in chk["masses"]},
            "masses": {iso: {"mass_gev": m, "source": s, "A": a} for iso, (m, s, a) in chk["masses"].items()}}


def bhattacharyya(p: list[float], q: list[float]) -> float:
    sp, sq = sum(p), sum(q)
    if sp <= 0 or sq <= 0:
        return 0.0
    return math.fsum(math.sqrt((a / sp) * (b / sq)) for a, b in zip(p, q))


def fit_bin(data: list[float], tmpl: dict, generated: dict, backgrounds: dict) -> dict:
    names = list(tmpl) + list(backgrounds)
    m = [tmpl[n] for n in tmpl] + [backgrounds[n] for n in backgrounds]
    mc = [generated[n] for n in tmpl] + [max(sum(backgrounds[n]), 1e-300) for n in backgrounds]
    for n, row in zip(names, m):
        if sum(row) <= 0:
            raise InputError(f"template {n} is empty in this bin (no MC inside the accepted beta range)")
    total = sum(data)
    start = [max(total / len(names), 1.0)] * len(names)
    y0 = template_fit._fit_yields_full(data, m, mc, "naive", start)[0]
    y, cov, _, diag = template_fit._fit_yields_full(data, m, mc, "bb", [max(v, 1.0) for v in y0])
    iso = list(tmpl)
    s = sum(y[i] for i in range(len(iso)))
    fr = {}
    for i, name in enumerate(iso):
        val = y[i] / s if s > 0 else float("nan")
        err = None
        if cov is not None and s > 0:
            grad = [((s if j == i else 0.0) - y[i]) / s ** 2 for j in range(len(iso))]
            var = sum(grad[a] * grad[b] * cov[a][b] for a in range(len(iso)) for b in range(len(iso)))
            err = math.sqrt(var) if var > 0 else None
        fr[name] = {"value": val, "error": err}
    overlap = {f"{a}|{b}": bhattacharyya(tmpl[a], tmpl[b]) for i, a in enumerate(iso) for b in iso[i + 1:]}
    return {"fractions": fr, "yields": {n: y[k] for k, n in enumerate(names)}, "overlap": overlap,
            "fit_outcome": diag["outcome"]}


def fit_all(cfg: dict, data: dict, seed: int, nuisance_shifts: bool = True) -> dict:
    chk = check_config(cfg)
    nb, nv = len(chk["edges"]) - 1, len(chk["vedges"]) - 1
    bins = data.get("bins") if isinstance(data, dict) else None
    if not isinstance(bins, list) or len(bins) != nb or any(not isinstance(b, list) or len(b) != nv for b in bins):
        raise InputError(f"data.bins must list {nb} histograms of {nv} counts")
    for b in bins:
        for v in b:
            _num(v, "data count", 0)
    bkg = cfg.get("backgrounds") or {}
    for name, rows in bkg.items():
        if not isinstance(rows, list) or len(rows) != nb or any(len(r) != nv for r in rows):
            raise InputError(f"background {name}: {nb} histograms of {nv} counts")
    if len(chk["masses"]) + len(bkg) > template_fit.MAX_TEMPLATES:
        raise InputError(f"at most {template_fit.MAX_TEMPLATES} templates in all")
    base = build_templates(cfg, seed)
    rows = []
    for k in range(nb):
        row = fit_bin([float(v) for v in bins[k]], base["templates"][k], base["generated"],
                      {n: bkg[n][k] for n in bkg})
        row["rigidity_bin"] = [chk["edges"][k], chk["edges"][k + 1]]
        rows.append(row)
    if nuisance_shifts:
        for nu in cfg.get("nuisances") or []:
            par = nu.get("parameter")
            if par not in ("sigma_beta", "sigma_r_rel"):
                raise InputError(f"nuisance {nu.get('name')}: parameter must be sigma_beta or sigma_r_rel")
            rel = _num(nu.get("relative_uncertainty"), f"nuisance {nu.get('name')}", 0, 1)
            fits = {}
            for sgn in (1, -1):
                t = build_templates(cfg, seed, {par: 1.0 + sgn * rel})
                fits[sgn] = [fit_bin([float(v) for v in bins[k]], t["templates"][k], t["generated"],
                                     {n: bkg[n][k] for n in bkg}) for k in range(nb)]
            for k, row in enumerate(rows):
                row.setdefault("nuisance_shifts", {})[nu["name"]] = {
                    iso: 0.5 * (fits[1][k]["fractions"][iso]["value"] - fits[-1][k]["fractions"][iso]["value"])
                    for iso in base["masses"]}
    centers = [math.sqrt(a * b) for a, b in zip(chk["edges"], chk["edges"][1:])]
    table = {"kind": "table", "x": centers,
             "isotopes": [{"A": base["masses"][iso]["A"], "name": iso, "mass_gev": base["masses"][iso]["mass_gev"],
                           "mass_source": base["masses"][iso]["source"],
                           "fractions": [r["fractions"][iso]["value"] for r in rows],
                           "fraction_uncertainty": max((r["fractions"][iso]["error"] or 0.0) for r in rows)}
                          for iso in base["masses"]]}
    return {"bins": rows, "masses": base["masses"], "composition_table": table, "variable": cfg["variable"],
            "fraction_definition": "fractions of the isotopes arriving in each rigidity bin (the beta-range acceptance "
                                   "is corrected through the generated MC count)"}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fit", help="fit isotope fractions per rigidity bin")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--no-nuisances", action="store_true", dest="no_nuisances")
    add_status_argument(p)
    p = sub.add_parser("templates", help="build the templates and their overlaps")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True)
    add_status_argument(p)
    p = sub.add_parser("resolution", help="mass resolution from rigidity and velocity resolution")
    p.add_argument("--sigma-r-rel", type=float, required=True, dest="sigma_r_rel")
    p.add_argument("--sigma-beta", type=float, required=True, dest="sigma_beta")
    p.add_argument("--beta", type=float, nargs="+", required=True)
    add_status_argument(p)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    head = {"status_label": args.status, "inputs": inputs, "defaults_used": [k for k in ("status",) if f"--{k}" not in given]}
    warnings: list[str] = []
    status = "ok"
    try:
        if args.command == "resolution":
            _num(args.sigma_r_rel, "--sigma-r-rel", 0)
            _num(args.sigma_beta, "--sigma-beta", 0)
            pts = []
            for b in args.beta:
                _num(b, "--beta", 0, strict=True)
                if b >= 1:
                    raise InputError("--beta must be below 1")
                pts.append({"beta": b, "gamma": 1 / math.sqrt(1 - b * b), "sigma_m_over_m": sigma_m_over_m(args.sigma_r_rel, args.sigma_beta, b)})
            result = {"points": pts, "formula": "(sigma_m/m)^2 = (sigma_R/R)^2 + gamma^4 (sigma_beta/beta)^2"}
        else:
            try:
                import numpy  # noqa: F401
            except ImportError:
                print(json.dumps({"status": "missing-dependency", **head, "error": "NumPy is required for templates",
                                  "install": "pip install numpy"}, indent=1))
                return exit_code("missing-dependency")
            try:
                cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise InputError(f"cannot read {args.config}: {exc}") from None
            if not isinstance(cfg, dict):
                raise InputError("the configuration must be a JSON object")
            if args.command == "templates":
                t = build_templates(cfg, args.seed)
                iso = list(t["masses"])
                result = {"templates": t["templates"], "generated": t["generated"], "masses": t["masses"],
                          "overlap": [{f"{a}|{b}": bhattacharyya(row[a], row[b]) for i, a in enumerate(iso)
                                       for b in iso[i + 1:]} for row in t["templates"]]}
            else:
                try:
                    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise InputError(f"cannot read {args.data}: {exc}") from None
                result = fit_all(cfg, data, args.seed, not args.no_nuisances)
                if any(r["fit_outcome"] in template_fit.FAILED_OUTCOMES for r in result["bins"]):
                    status = "failed"
            if not cfg.get("tails_validated_on_data"):
                warnings.append("MC-only templates: the resolution tails are not validated on data, so the output is "
                                "labelled unvalidated")
                head["status_label"] = "unvalidated"
    except (InputError, template_fit.ToyError) as exc:
        print(json.dumps({"status": "rejected", **head, "error": str(exc)}, indent=1))
        print(f"isotope_fraction.py: error: {exc}", file=sys.stderr)
        return exit_code("rejected")
    print(json.dumps({"status": status, **head, "warnings": warnings, "label": LABEL, **result}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
