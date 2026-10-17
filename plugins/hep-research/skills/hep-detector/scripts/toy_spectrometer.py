#!/usr/bin/env python3
"""Fast synthetic simulation of a magnetic spectrometer: events and data-taking periods from a declared configuration.

Purpose: a reproducible test bed for tools that consume spectrometer-like data (scale distortions, response
construction, stability monitoring, charge and velocity selections) without real data. Every output is labeled
synthetic and carries its seed.

Method (no tracking, no geometry beyond the declared numbers):
- rigidity resolution: sigma(1/R)^2 = a^2 + (b / (beta R))^2 in GV^-1. a is the Gluckstern intrinsic slope and b the
  Highland scattering term, both from multiple_scattering.py for the same layers, field and lever arm (a: point
  resolution of the measuring layers, combined as (mean of 1/sigma_i^2)^(-1/2), their number, B and L; b: the summed
  x/X0 of all layers, x/X0 = grammage / radiation length). The measured 1/R is the true 1/R plus a Gaussian of that
  width, so charge-sign flips occur naturally at high rigidity;
- charge: each layer with "charge_resolution" [c0, c1] measures Z + N(0, sqrt(c0^2 + (c1 Z)^2)), plus, with
  probability tail_fraction, an exponential tail of mean tail_scale * Z (a Landau-like upper tail); the estimator is
  the mean after dropping the drop_highest largest samples (truncated mean);
- velocity: beta + N(0, sigma_beta);
- species: charge Z, mass number A, mass (GeV, user-supplied), a fraction, and a power-law spectrum dN/dR ~ R^-index
  between r_min_gv and r_max_gv, sampled by inverse CDF; beta = Z R / sqrt((Z R)^2 + m^2);
- periods: count, duration_s, rate_hz, live_fraction; the number of events in a period is Poisson with mean
  rate * duration * live fraction, event times are uniform within the period;
- eras: from first_period on, an era may add layers ("add_layers") and override field values ("field"); each era is
  applied to the base configuration, not to the previous era.

Assumptions and validity: Gaussian 1/R smearing (no non-Gaussian tracking tails, no energy loss, no interactions,
no acceptance), independent layers, a uniform field. It is a design-level toy, not a detector simulation; the
configuration supplies every number (no experiment defaults; masses and radiation lengths come from the user).

Reproducibility: NumPy's PCG64 generator seeded with --seed; tables are written with %.10g. The same seed, config
and NumPy version give byte-identical files (sha256 in the output); the NumPy version is recorded.

Input: a JSON configuration (see <plugin root>/skills/hep-detector/assets/toy-spectrometer.fictional.json): "field"
{field_tesla, lever_arm_m}; "layers" [{name, z_m, resolution_um (null for a passive layer), grammage_g_cm2,
radiation_length_g_cm2, composition, measuring, charge_resolution?}]; "charge" {estimator "truncated-mean",
drop_highest, tail_fraction, tail_scale}; "velocity" {sigma_beta}; "species" [{name, Z, A, mass_gev, fraction,
spectrum {kind "power-law", index, r_min_gv, r_max_gv}}]; "periods" {count, duration_s, rate_hz, live_fraction};
"eras" (optional) [{name, first_period, add_layers?, field?}].

Usage:
  toy_spectrometer.py generate CONFIG --seed N --events-out EVENTS.csv --periods-out PERIODS.csv
  toy_spectrometer.py resolution CONFIG --species NAME --rigidity R [R ...] [--era NAME]

Output: JSON with status, status_label (always synthetic), inputs, defaults_used, warnings and, for generate, the
table paths and their sha256. Exit codes: 0 ok; 2 invalid input or configuration (status rejected); 3 NumPy is
missing (generate only; status missing-dependency).
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # sibling imports leave no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import exit_code  # noqa: E402
from multiple_scattering import intrinsic_resolution_slope, scattering_resolution_term  # noqa: E402

LABEL = "synthetic"
EVENT_COLUMNS = ("event", "period", "era", "time_s", "species", "z_true", "mass_number", "rigidity_true_gv",
                 "beta_true", "inv_rigidity_meas_per_gv", "sigma_inv_rigidity_per_gv", "rigidity_meas_gv", "z_meas",
                 "beta_meas")
PERIOD_COLUMNS = ("period", "era", "start_s", "duration_s", "live_fraction", "livetime_s", "n_events")


class ConfigError(ValueError):
    """The configuration or the arguments cannot be used."""


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that prints the reason as JSON on stdout (status rejected, exit 2). Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "status_label": LABEL, "error": message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(exit_code("rejected"), f"{self.prog}: error: {message}\n")


def _number(value, name, low=None, low_open=False, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ConfigError(f"{name} must be a finite number")
    if low is not None and (value < low or (low_open and value == low)):
        raise ConfigError(f"{name} must be {'>' if low_open else '>='} {low:g}")
    if high is not None and value > high:
        raise ConfigError(f"{name} must be <= {high:g}")
    return float(value)


def _require(block, key, where):
    if not isinstance(block, dict) or key not in block:
        raise ConfigError(f"{where} is missing {key!r}")
    return block[key]


def _check_layer(layer, where):
    if not isinstance(layer, dict):
        raise ConfigError(f"{where} must be an object")
    _number(_require(layer, "grammage_g_cm2", where), f"{where}.grammage_g_cm2", 0.0)
    _number(_require(layer, "radiation_length_g_cm2", where), f"{where}.radiation_length_g_cm2", 0.0, low_open=True)
    measuring = layer.get("measuring", False)
    if not isinstance(measuring, bool):
        raise ConfigError(f"{where}.measuring must be true or false")
    if measuring:
        _number(_require(layer, "resolution_um", where), f"{where}.resolution_um", 0.0, low_open=True)
    if "charge_resolution" in layer:
        cr = layer["charge_resolution"]
        if not isinstance(cr, list) or len(cr) != 2:
            raise ConfigError(f"{where}.charge_resolution must be [c0, c1]")
        _number(cr[0], f"{where}.charge_resolution[0]", 0.0)
        _number(cr[1], f"{where}.charge_resolution[1]", 0.0)


def load_config(path):
    """Read and check a configuration; returns (config, sha256 of the file, defaults_used)."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise ConfigError(f"cannot read configuration {path}: {exc.strerror or exc}") from None
    try:
        config = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"configuration is not JSON: {exc}") from None
    if not isinstance(config, dict):
        raise ConfigError("configuration must be a JSON object")
    defaults_used = []
    field = _require(config, "field", "configuration")
    _number(_require(field, "field_tesla", "field"), "field.field_tesla", 0.0, low_open=True)
    _number(_require(field, "lever_arm_m", "field"), "field.lever_arm_m", 0.0, low_open=True)
    layers = _require(config, "layers", "configuration")
    if not isinstance(layers, list) or not layers:
        raise ConfigError("layers must be a non-empty list")
    for i, layer in enumerate(layers):
        _check_layer(layer, f"layers[{i}]")
    charge = _require(config, "charge", "configuration")
    if _require(charge, "estimator", "charge") != "truncated-mean":
        raise ConfigError("charge.estimator must be 'truncated-mean'")
    drop = _require(charge, "drop_highest", "charge")
    if isinstance(drop, bool) or not isinstance(drop, int) or drop < 0:
        raise ConfigError("charge.drop_highest must be a non-negative integer")
    _number(_require(charge, "tail_fraction", "charge"), "charge.tail_fraction", 0.0, high=1.0)
    _number(_require(charge, "tail_scale", "charge"), "charge.tail_scale", 0.0)
    _number(_require(_require(config, "velocity", "configuration"), "sigma_beta", "velocity"),
            "velocity.sigma_beta", 0.0)
    species = _require(config, "species", "configuration")
    if not isinstance(species, list) or not species:
        raise ConfigError("species must be a non-empty list")
    names = set()
    for i, s in enumerate(species):
        where = f"species[{i}]"
        name = _require(s, "name", where)
        if not isinstance(name, str) or not name or name in names:
            raise ConfigError(f"{where}.name must be a unique non-empty string")
        names.add(name)
        for key in ("Z", "A"):
            v = _require(s, key, where)
            if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                raise ConfigError(f"{where}.{key} must be a positive integer")
        _number(_require(s, "mass_gev", where), f"{where}.mass_gev", 0.0, low_open=True)
        _number(_require(s, "fraction", where), f"{where}.fraction", 0.0, high=1.0)
        spec = _require(s, "spectrum", where)
        if _require(spec, "kind", f"{where}.spectrum") != "power-law":
            raise ConfigError(f"{where}.spectrum.kind must be 'power-law'")
        _number(_require(spec, "index", f"{where}.spectrum"), f"{where}.spectrum.index")
        low = _number(_require(spec, "r_min_gv", f"{where}.spectrum"), f"{where}.spectrum.r_min_gv", 0.0, low_open=True)
        high = _number(_require(spec, "r_max_gv", f"{where}.spectrum"), f"{where}.spectrum.r_max_gv", 0.0, low_open=True)
        if high <= low:
            raise ConfigError(f"{where}.spectrum.r_max_gv must exceed r_min_gv")
    total = math.fsum(s["fraction"] for s in species)
    if abs(total - 1.0) > 1e-9:
        raise ConfigError(f"species fractions sum to {total:.12g}, not 1")
    periods = _require(config, "periods", "configuration")
    count = _require(periods, "count", "periods")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ConfigError("periods.count must be a positive integer")
    _number(_require(periods, "duration_s", "periods"), "periods.duration_s", 0.0, low_open=True)
    _number(_require(periods, "rate_hz", "periods"), "periods.rate_hz", 0.0)
    _number(_require(periods, "live_fraction", "periods"), "periods.live_fraction", 0.0, high=1.0)
    if "eras" not in config:
        config["eras"] = [{"name": "single-era", "first_period": 0}]
        defaults_used.append("eras: one era 'single-era' covering every period")
    eras = config["eras"]
    if not isinstance(eras, list) or not eras:
        raise ConfigError("eras must be a non-empty list")
    previous = -1
    for i, era in enumerate(eras):
        where = f"eras[{i}]"
        first = _require(era, "first_period", where)
        if isinstance(first, bool) or not isinstance(first, int) or first <= previous or first >= count:
            raise ConfigError(f"{where}.first_period must be an integer, increasing, below periods.count")
        if i == 0 and first != 0:
            raise ConfigError("the first era must start at period 0")
        previous = first
        if not isinstance(_require(era, "name", where), str):
            raise ConfigError(f"{where}.name must be a string")
        for j, layer in enumerate(era.get("add_layers", [])):
            _check_layer(layer, f"{where}.add_layers[{j}]")
        override = era.get("field", {})
        if not isinstance(override, dict) or set(override) - {"field_tesla", "lever_arm_m"}:
            raise ConfigError(f"{where}.field may override only field_tesla and lever_arm_m")
        for key, value in override.items():
            _number(value, f"{where}.field.{key}", 0.0, low_open=True)
    if len({e["name"] for e in eras}) != len(eras):
        raise ConfigError("era names must be unique")
    return config, hashlib.sha256(raw).hexdigest(), defaults_used


def era_model(config, era):
    """Resolution and charge parameters of one era (the base configuration plus that era's overrides)."""
    layers = list(config["layers"]) + list(era.get("add_layers", []))
    field = {**config["field"], **era.get("field", {})}
    measuring = [x for x in layers if x.get("measuring", False)]
    if len(measuring) < 3:
        raise ConfigError(f"era {era['name']!r} has {len(measuring)} measuring layers; a curvature fit needs 3")
    total_x0 = math.fsum(x["grammage_g_cm2"] / x["radiation_length_g_cm2"] for x in layers)
    sigma_eff_um = (math.fsum(1.0 / x["resolution_um"] ** 2 for x in measuring) / len(measuring)) ** -0.5
    a = intrinsic_resolution_slope(sigma_eff_um, len(measuring), field["field_tesla"], field["lever_arm_m"])
    b = scattering_resolution_term(total_x0, field["field_tesla"], field["lever_arm_m"], 1.0)
    charge_layers = [x["charge_resolution"] for x in layers if "charge_resolution" in x]
    drop = config["charge"]["drop_highest"]
    if len(charge_layers) <= drop:
        raise ConfigError(f"era {era['name']!r} has {len(charge_layers)} charge layers; drop_highest={drop} needs more")
    return {"name": era["name"], "first_period": era["first_period"], "layers": len(layers),
            "measuring_layers": len(measuring), "point_resolution_eff_um": sigma_eff_um,
            "field_tesla": field["field_tesla"], "lever_arm_m": field["lever_arm_m"], "total_x_over_x0": total_x0,
            "a_per_gv": a, "b": b, "charge_layers": charge_layers}


def beta_of(rigidity, z, mass):
    momentum = z * rigidity
    return momentum / math.hypot(momentum, mass)


def resolution_point(model, rigidity, z, mass):
    beta = beta_of(rigidity, z, mass)
    scattering = model["b"] / (beta * rigidity)
    sigma = math.hypot(model["a_per_gv"], scattering)
    return {"rigidity_gv": rigidity, "beta": beta, "sigma_inv_rigidity_per_gv": sigma,
            "relative_resolution": sigma * rigidity,
            "dominant_term": "scattering" if scattering > model["a_per_gv"] else "intrinsic"}


def _public(model):
    return {k: v for k, v in model.items() if k != "charge_layers"} | {"charge_layers": len(model["charge_layers"])}


def cmd_resolution(args):
    config, sha, defaults_used = load_config(args.config)
    species = {s["name"]: s for s in config["species"]}
    if args.species not in species:
        raise ConfigError(f"species {args.species!r} is not in the configuration ({sorted(species)})")
    models = [era_model(config, e) for e in config["eras"]]
    if args.era is None:
        model = models[0]
        defaults_used.append(f"era: the first era {model['name']!r}")
    else:
        found = [m for m in models if m["name"] == args.era]
        if not found:
            raise ConfigError(f"era {args.era!r} is not in the configuration")
        model = found[0]
    s = species[args.species]
    for r in args.rigidity:
        _number(r, "rigidity", 0.0, low_open=True)
    points = [resolution_point(model, r, s["Z"], s["mass_gev"]) for r in args.rigidity]
    if not all(math.isfinite(v) for pt in points for v in pt.values() if isinstance(v, float)):
        raise ConfigError("a rigidity is outside the range where sigma(1/R) is representable in floating point")
    return {"status": "ok", "status_label": LABEL,
            "method": "sigma(1/R)^2 = a^2 + (b/(beta R))^2 (Gluckstern a, Highland b; multiple_scattering.py)",
            "inputs": {"config": str(args.config), "config_sha256": sha, "species": args.species, "era": model["name"],
                       "rigidity_gv": args.rigidity},
            "defaults_used": defaults_used, "warnings": [],
            "eras": [_public(m) for m in models],
            "points": points}


def _strings(np, values, fmt="%.10g"):
    return np.char.mod(fmt, values).tolist()


def _write_table(path, header_comment, columns, cols):
    lines = [header_comment, ",".join(columns)]
    lines.extend(",".join(row) for row in zip(*cols))
    data = ("\n".join(lines) + "\n").encode("utf-8")
    Path(path).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def cmd_generate(args):
    config, sha, defaults_used = load_config(args.config)
    if args.seed < 0:
        raise ConfigError("--seed must be a non-negative integer")
    events_out, periods_out = Path(args.events_out), Path(args.periods_out)
    if events_out.resolve() == periods_out.resolve():
        raise ConfigError("--events-out and --periods-out must differ")
    for path in (events_out, periods_out):
        if not path.parent.is_dir():
            raise ConfigError(f"output folder {path.parent} does not exist")
    models = [era_model(config, e) for e in config["eras"]]
    try:
        import numpy as np
    except ImportError:
        return {"status": "missing-dependency", "status_label": LABEL,
                "error": "generate needs NumPy: python3 -m pip install numpy (requirements-core.txt)"}
    rng = np.random.Generator(np.random.PCG64(args.seed))
    p = config["periods"]
    n_periods = p["count"]
    era_of_period = np.zeros(n_periods, dtype=np.int64)
    for i, m in enumerate(models):
        era_of_period[m["first_period"]:] = i
    counts = rng.poisson(p["rate_hz"] * p["duration_s"] * p["live_fraction"], size=n_periods)
    n = int(counts.sum())
    period = np.repeat(np.arange(n_periods), counts)
    era = era_of_period[period]
    time_s = period * p["duration_s"] + rng.random(n) * p["duration_s"]
    species = config["species"]
    cumulative = np.cumsum([s["fraction"] for s in species])
    cumulative[-1] = 1.0
    sp = np.minimum(np.searchsorted(cumulative, rng.random(n), side="right"), len(species) - 1)
    u = rng.random(n)
    rigidity = np.empty(n)
    z = np.empty(n)
    mass = np.empty(n)
    mass_number = np.empty(n, dtype=np.int64)
    for i, s in enumerate(species):
        sel = sp == i
        spec = s["spectrum"]
        g, lo, hi = spec["index"], spec["r_min_gv"], spec["r_max_gv"]
        if abs(g - 1.0) < 1e-12:
            rigidity[sel] = lo * (hi / lo) ** u[sel]
        else:
            e = 1.0 - g
            rigidity[sel] = (lo ** e + u[sel] * (hi ** e - lo ** e)) ** (1.0 / e)
        z[sel], mass[sel], mass_number[sel] = s["Z"], s["mass_gev"], s["A"]
    momentum = z * rigidity
    beta = momentum / np.hypot(momentum, mass)
    a = np.array([m["a_per_gv"] for m in models])[era]
    b = np.array([m["b"] for m in models])[era]
    sigma_inv = np.hypot(a, b / (beta * rigidity))
    inv_meas = 1.0 / rigidity + sigma_inv * rng.standard_normal(n)
    with np.errstate(divide="ignore"):
        rigidity_meas = np.where(inv_meas != 0.0, 1.0 / np.where(inv_meas != 0.0, inv_meas, 1.0), np.inf)
    charge = config["charge"]
    z_meas = np.empty(n)
    for i, m in enumerate(models):
        sel = np.flatnonzero(era == i)
        cl = np.array(m["charge_layers"], dtype=float)
        zz = z[sel][:, None]
        sigma_z = np.sqrt(cl[None, :, 0] ** 2 + (cl[None, :, 1] * zz) ** 2)
        samples = zz + sigma_z * rng.standard_normal((sel.size, len(cl)))
        tail = rng.random((sel.size, len(cl))) < charge["tail_fraction"]
        samples += tail * rng.exponential(1.0, (sel.size, len(cl))) * charge["tail_scale"] * zz
        samples.sort(axis=1)
        keep = len(cl) - charge["drop_highest"]
        z_meas[sel] = samples[:, :keep].mean(axis=1)
    beta_meas = beta + config["velocity"]["sigma_beta"] * rng.standard_normal(n)

    names = np.array([m["name"] for m in models])
    sp_names = np.array([s["name"] for s in species])
    comment = (f"# synthetic: toy_spectrometer.py seed={args.seed} config_sha256={sha} numpy={np.__version__}; "
               "not real data")
    cols = [_strings(np, np.arange(n), "%d"), _strings(np, period, "%d"), names[era].tolist(), _strings(np, time_s),
            sp_names[sp].tolist(), _strings(np, z, "%d"), _strings(np, mass_number, "%d"), _strings(np, rigidity),
            _strings(np, beta), _strings(np, inv_meas), _strings(np, sigma_inv), _strings(np, rigidity_meas),
            _strings(np, z_meas), _strings(np, beta_meas)]
    events_sha = _write_table(events_out, comment, EVENT_COLUMNS, cols)
    starts = np.arange(n_periods) * p["duration_s"]
    pcols = [_strings(np, np.arange(n_periods), "%d"), names[era_of_period].tolist(), _strings(np, starts),
             [f"{p['duration_s']:.10g}"] * n_periods, [f"{p['live_fraction']:.10g}"] * n_periods,
             [f"{p['duration_s'] * p['live_fraction']:.10g}"] * n_periods, _strings(np, counts, "%d")]
    periods_sha = _write_table(periods_out, comment, PERIOD_COLUMNS, pcols)
    per_species = {s["name"]: int((sp == i).sum()) for i, s in enumerate(species)}
    return {"status": "ok", "status_label": LABEL,
            "method": "toy spectrometer: Gaussian 1/R smearing (Gluckstern a, Highland b), truncated-mean charge, "
                      "Gaussian beta, power-law species, Poisson periods",
            "inputs": {"config": str(args.config), "config_sha256": sha, "seed": args.seed},
            "defaults_used": defaults_used, "warnings": [],
            "n_events": n, "events_per_species": per_species,
            "eras": [_public(m) for m in models],
            "outputs": {"events": str(events_out), "events_sha256": events_sha,
                        "periods": str(periods_out), "periods_sha256": periods_sha},
            "environment": {"numpy": np.__version__, "bit_generator": "PCG64"},
            "note": "Synthetic data from a fictional or user-declared configuration; not a detector simulation."}


def main(argv=None):
    parser = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="write event and period tables")
    gen.add_argument("config", help="JSON configuration")
    gen.add_argument("--seed", type=int, required=True, help="random seed (required; recorded in every output)")
    gen.add_argument("--events-out", required=True, help="CSV path of the event table")
    gen.add_argument("--periods-out", required=True, help="CSV path of the period table")
    res = sub.add_parser("resolution", help="sigma(1/R) per era at given rigidities")
    res.add_argument("config", help="JSON configuration")
    res.add_argument("--species", required=True, help="a species name from the configuration")
    res.add_argument("--rigidity", type=float, nargs="+", required=True, help="rigidities in GV")
    res.add_argument("--era", default=None, help="era name (default: the first era)")
    args = parser.parse_args(argv)
    try:
        result = cmd_generate(args) if args.command == "generate" else cmd_resolution(args)
    except (ConfigError, OverflowError, ZeroDivisionError) as exc:
        result = {"status": "rejected", "status_label": LABEL, "error": str(exc)}
    except OSError as exc:
        result = {"status": "rejected", "status_label": LABEL, "error": f"cannot write output: {exc}"}
    print(json.dumps(result, indent=2, allow_nan=False))
    return exit_code(result["status"])


if __name__ == "__main__":
    raise SystemExit(main())
