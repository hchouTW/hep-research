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
(through a temporary name, renamed when complete). Exit codes: 0 done; 3 ROOT or a Garfield++ library cannot be
loaded; 4 the table cannot be loaded; 5 the pressure or temperature differs; 6 a query failed; 2 bad arguments.
"""
import argparse
import ctypes
import json
import math
import os
import sys

FORMAT = "garfield-gas-table-query-output/1"
LIBRARIES = ("libGarfieldRandom", "libHeed", "libMagboltz", "libDegrade", "libneBEM", "libGarfield")


def fail(code, message):
    sys.stderr.write("gas_table_query: " + message + "\n")
    sys.exit(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--query", required=True, help="the rendered query (JSON)")
    parser.add_argument("--table", required=True, help="the gas table (.gas)")
    parser.add_argument("--garfield-lib", required=True, help="the folder of the Garfield++ libraries")
    parser.add_argument("--out", required=True, help="the raw output file")
    args = parser.parse_args()
    with open(args.query, encoding="utf-8") as handle:
        query = json.load(handle)
    try:
        import ROOT
    except ImportError as err:
        fail(3, f"ROOT's Python bindings cannot be imported: {err}")
    ROOT.gROOT.SetBatch(True)
    extension = ".dylib" if sys.platform == "darwin" else ".so"
    for name in LIBRARIES:
        if ROOT.gSystem.Load(os.path.join(args.garfield_lib, name + extension)) < 0:
            fail(3, f"cannot load {name}{extension} from the Garfield++ library folder")
    gas = ROOT.Garfield.MediumMagboltz()
    try:
        loaded = gas.LoadGasFile(args.table)
    except Exception as err:  # Garfield++ throws for an unreadable file or an unknown mixture
        fail(4, f"LoadGasFile raised {type(err).__name__}: {err}")
    if not loaded:
        fail(4, "LoadGasFile returned false")
    pressure, temperature = gas.GetPressure(), gas.GetTemperature()
    if pressure != float(query["pressure_torr"]) or temperature != float(query["temperature_k"]):
        fail(5, f"the medium has pressure {pressure!r} Torr and temperature {temperature!r} K, the plan "
                f"{query['pressure_torr']} Torr and {query['temperature_k']} K")
    settings = query["interpolation"]
    gas.SetInterpolationMethodVelocity(int(settings["order"]))
    gas.SetExtrapolationMethodVelocity(settings["low"], settings["high"])
    lines = ["format " + FORMAT, "pressure_torr " + repr(pressure), "temperature_k " + repr(temperature),
             f"interpolation {int(settings['order'])} {settings['low']} {settings['high']}"]
    for point in query["points"]:
        field = float(point["field_v_per_cm"])
        vx, vy, vz = ctypes.c_double(0.0), ctypes.c_double(0.0), ctypes.c_double(0.0)
        ok = gas.ElectronVelocity(field, 0.0, 0.0, 0.0, 0.0, 0.0, vx, vy, vz)
        if not ok:
            fail(6, f"ElectronVelocity failed at point {point['index']}")
        magnitude = math.sqrt(vx.value * vx.value + vy.value * vy.value + vz.value * vz.value)
        lines.append(f"point {point['index']} {point['field_v_per_cm']} {vx.value!r} {vy.value!r} {vz.value!r} "
                     f"{magnitude!r}")
    lines.append(f"end {len(query['points'])}")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    partial = args.out + ".partial"
    with open(partial, "w", encoding="ascii") as handle:
        handle.write("\n".join(lines) + "\n")
    os.replace(partial, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
