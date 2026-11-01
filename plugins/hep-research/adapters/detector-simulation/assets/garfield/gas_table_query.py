"""Garfield++ gas-table query of the detsim capability garfield.gas-table-query 1.0.0 (a data file of the adapter).

Rendered into the plan's ExecutionSpec and run by detsim as ENV_ROOT/bin/python3 -B -s ATTEMPT_ROOT/query/
gas_table_query.py --query Q --table T --garfield-lib L --out O, in the environment's Python with ROOT's Python
bindings (docs/dev/detector-simulation/card-GF-QUERY.md). It is never imported by the adapter's own code.

Steps, all in one process: load the Garfield++ libraries from --garfield-lib with ROOT's gSystem.Load (neBEM before
Garfield, which links it through @rpath); MediumMagboltz().LoadGasFile(table); assert that the medium's pressure
and temperature equal the plan's (the table's PGAS and TGAS, so the density ratio is exactly 1); set the velocity
interpolation order and the low and high extrapolation methods explicitly (SetInterpolationMethodVelocity,
SetExtrapolationMethodVelocity), so the run does not depend on the file's footer; for each query point call
ElectronVelocity with E = (E, 0, 0) V/cm and B = 0; write every double with repr (round-trip exact) to --out
(through a temporary name, renamed when complete).

Output (R-07 (a)): the last line of stdout is one JSON object with a "status" key, and the exit code is 0 ok;
1 failed (the table cannot be loaded, the pressure or temperature differs, a query fails); 2 rejected (bad
arguments or an unreadable query); 3 missing-dependency (ROOT's bindings or a Garfield++ library do not load).
Garfield++'s own messages go to stdout before it; detsim's collect reads the last JSON line.
"""
import argparse
import ctypes
import json
import math
import os
import sys

FORMAT = "garfield-gas-table-query-output/1"
LIBRARIES = ("libGarfieldRandom", "libHeed", "libMagboltz", "libDegrade", "libneBEM", "libGarfield")
EXIT_CODES = {"ok": 0, "failed": 1, "rejected": 2, "missing-dependency": 3}


class Stop(Exception):
    def __init__(self, status, error_code, message):
        super().__init__(message)
        self.status, self.error_code, self.message = status, error_code, message


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop("rejected", "usage", message)


def flush_garfield_messages(root):
    """Flush C++ std::cout so Garfield++'s messages precede the JSON answer."""
    if root is not None:
        try:
            root.gInterpreter.ProcessLine("std::cout << std::flush;")
        except Exception:  # noqa: BLE001 - best effort only
            pass


def query(args):
    try:
        with open(args.query, encoding="utf-8") as handle:
            plan = json.load(handle)
    except (OSError, ValueError) as err:
        raise Stop("rejected", "query-unreadable", f"cannot read the query: {err}") from None
    try:
        import ROOT
    except ImportError as err:
        raise Stop("missing-dependency", "missing-dependency",
                   f"ROOT's Python bindings cannot be imported: {err}") from None
    ROOT.gROOT.SetBatch(True)
    extension = ".dylib" if sys.platform == "darwin" else ".so"
    for name in LIBRARIES:
        if ROOT.gSystem.Load(os.path.join(args.garfield_lib, name + extension)) < 0:
            raise Stop("missing-dependency", "missing-dependency", f"cannot load {name}{extension} from the "
                       "Garfield++ library folder")
    gas = ROOT.Garfield.MediumMagboltz()
    try:
        loaded = gas.LoadGasFile(args.table)
    except Exception as err:  # Garfield++ throws for an unreadable file or an unknown mixture
        raise Stop("failed", "table-load", f"LoadGasFile raised {type(err).__name__}: {err}") from None
    if not loaded:
        raise Stop("failed", "table-load", "LoadGasFile returned false")
    pressure, temperature = gas.GetPressure(), gas.GetTemperature()
    if pressure != float(plan["pressure_torr"]) or temperature != float(plan["temperature_k"]):
        raise Stop("failed", "condition-mismatch", f"the medium has pressure {pressure!r} Torr and temperature "
                   f"{temperature!r} K, the plan {plan['pressure_torr']} Torr and {plan['temperature_k']} K")
    settings = plan["interpolation"]
    gas.SetInterpolationMethodVelocity(int(settings["order"]))
    gas.SetExtrapolationMethodVelocity(settings["low"], settings["high"])
    lines = ["format " + FORMAT, "pressure_torr " + repr(pressure), "temperature_k " + repr(temperature),
             f"interpolation {int(settings['order'])} {settings['low']} {settings['high']}"]
    for point in plan["points"]:
        field = float(point["field_v_per_cm"])
        vx, vy, vz = ctypes.c_double(0.0), ctypes.c_double(0.0), ctypes.c_double(0.0)
        if not gas.ElectronVelocity(field, 0.0, 0.0, 0.0, 0.0, 0.0, vx, vy, vz):
            raise Stop("failed", "query-failed", f"ElectronVelocity failed at point {point['index']}")
        magnitude = math.sqrt(vx.value * vx.value + vy.value * vy.value + vz.value * vz.value)
        lines.append(f"point {point['index']} {point['field_v_per_cm']} {vx.value!r} {vy.value!r} {vz.value!r} "
                     f"{magnitude!r}")
    lines.append(f"end {len(plan['points'])}")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    partial = args.out + ".partial"
    with open(partial, "w", encoding="ascii") as handle:
        handle.write("\n".join(lines) + "\n")
    os.replace(partial, args.out)
    return len(plan["points"])


def main(argv=None):
    parser = Parser(description=__doc__.splitlines()[0])
    parser.add_argument("--query", required=True, help="the rendered query (JSON)")
    parser.add_argument("--table", required=True, help="the gas table (.gas)")
    parser.add_argument("--garfield-lib", required=True, help="the folder of the Garfield++ libraries")
    parser.add_argument("--out", required=True, help="the raw output file")
    try:
        answer = {"status": "ok", "points": query(parser.parse_args(argv))}
    except Stop as stop:
        answer = {"status": stop.status, "error_code": stop.error_code, "message": stop.message}
    except Exception as err:  # noqa: BLE001 - every failure is answered in JSON
        answer = {"status": "failed", "error_code": "internal", "message": f"{type(err).__name__}: {err}"}
    flush_garfield_messages(sys.modules.get("ROOT"))
    sys.stdout.flush()
    print(json.dumps(answer, sort_keys=True), flush=True)
    return EXIT_CODES[answer["status"]]


if __spec__ is None:  # executed as a file (never imported by the adapter)
    sys.exit(main())
